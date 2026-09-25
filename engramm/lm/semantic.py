"""Word meaning by counting: binary codebooks, word classes, topic bundles.

(docs/PREREG_LM.md §5, §7.) Every token gets two binary hypervectors of
D_s = 2048 bits, both computed from integer co-occurrence counts:

* **eng** (narrow) — who stands directly next to the token. For each offset
  o ∈ {−2, −1, +1, +2}, count pairs (w at i, c at i+o) within a document,
  weight them by an integer PPMI level, and add the context token's random
  index vector *rotated by o* (the rotation encodes direction and distance):
  S_eng[w] = Σ_o Σ_c L_o(w, c) · ρ^o(r_c).
* **weit** (wide) — which tokens occur within ±16 positions, undirected:
  S_weit[w] = Σ_c L(w, c) · r_c. This carries topic.

PPMI level L ∈ {0..4}: the number of k ∈ {0, 1, 2, 3} with
c(w, c) · N > 2^k · c(w) · c(c) — integer comparisons only. Context tokens
are the 8,192 most frequent ones; the index vectors r_c come from
:class:`engramm.core.ItemMemory`. Sums stay below 2^24, so the float32 GEMM
used for the projection is exact. Sign → bits; exact zeros are settled by
the project's tie rule keyed on the token (``TieContext.for_prototype``).
Tokens seen fewer than 5 times get their own random vector: too few counts
to say anything.

Word classes: binary k-majority clustering (Hamming k-means with bitwise
majority centres) of the eng vectors into 511 classes; class 0 is reserved
for the document boundary.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numba
import numpy as np

from engramm.core import ItemMemory, TieContext, _binarise, permute

D_S = 2048
WORDS = D_S // 64
N_CONTEXT = 8192
MIN_COUNT = 5
ENG_OFFSETS = (-2, -1, 1, 2)
WIDE_WINDOW = 16
N_CLASSES = 512          # class 0 = boundary, 1..511 = clusters
CLUSTER_ITERS = 10


# ---------------------------------------------------------------------------
# popcount on packed uint64 words
# ---------------------------------------------------------------------------

@numba.njit(inline="always")
def popcount64(x):
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> np.uint64(2)) & np.uint64(0x3333333333333333))
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return (x * np.uint64(0x0101010101010101)) >> np.uint64(56)


@numba.njit(inline="always")
def ham_rows(a, i, b, j, words):
    s = 0
    for k in range(words):
        s += popcount64(a[i, k] ^ b[j, k])
    return s


def as_words(packed: np.ndarray) -> np.ndarray:
    """Packed uint8 rows → uint64 words (big-endian bytes, so bit order is irrelevant for Hamming)."""
    return np.ascontiguousarray(packed).view(">u8").astype(np.uint64)


# ---------------------------------------------------------------------------
# counting
# ---------------------------------------------------------------------------

@numba.njit(cache=True)
def unigram_counts(tokens, vocab):
    c = np.zeros(vocab, dtype=np.int64)
    for i in range(1, len(tokens)):
        c[tokens[i]] += 1
    return c


@numba.njit(cache=True)
def doc_freq(tokens, vocab):
    """Number of documents each token occurs in, and the number of documents."""
    df = np.zeros(vocab, dtype=np.int64)
    last = np.full(vocab, -1, dtype=np.int64)
    doc = 0
    for i in range(1, len(tokens)):
        t = tokens[i]
        if t == 0:
            doc += 1
            continue
        if last[t] != doc:
            last[t] = doc
            df[t] += 1
    return df, doc


@numba.njit(cache=True, parallel=True)
def _cooc(tokens, cmap, offsets, vocab, n_ctx, n_threads):
    """C[w, c] += 1 for every pair (w at i, ctx token at i+o), o in offsets, within a document.

    Rows are partitioned over threads (w mod threads) so the increments never race.
    """
    C = np.zeros((vocab, n_ctx), dtype=np.int32)
    n = len(tokens)
    # distance to the previous / next EOS decides whether i+o stays in the document
    prev_eos = np.empty(n, dtype=np.int64)
    last = -1
    for i in range(n):
        if tokens[i] == 0:
            last = i
        prev_eos[i] = last
    next_eos = np.empty(n, dtype=np.int64)
    last = n
    for i in range(n - 1, -1, -1):
        if tokens[i] == 0:
            last = i
        next_eos[i] = last
    for th in numba.prange(n_threads):
        for i in range(n):
            w = tokens[i]
            if w == 0 or w % n_threads != th:
                continue
            for o in offsets:
                j = i + o
                if j <= prev_eos[i] or j >= next_eos[i]:
                    continue
                c = cmap[tokens[j]]
                if c >= 0:
                    C[w, c] += 1
    return C


@numba.njit(cache=True, parallel=True)
def ppmi_levels(C):
    """Integer PPMI level 0..4 per cell (see module docstring)."""
    V, K = C.shape
    row = np.zeros(V, dtype=np.int64)
    col = np.zeros(K, dtype=np.int64)
    for w in range(V):
        for c in range(K):
            row[w] += C[w, c]
    for w in range(V):
        for c in range(K):
            col[c] += C[w, c]
    N = row.sum()
    L = np.zeros((V, K), dtype=np.int8)
    for w in numba.prange(V):
        rw = row[w]
        if rw == 0:
            continue
        for c in range(K):
            x = np.int64(C[w, c])
            if x == 0:
                continue
            lhs = x * N
            base = rw * col[c]
            lev = 0
            for k in range(4):
                if lhs > (base << k):
                    lev += 1
            L[w, c] = lev
    return L


def _project(L: np.ndarray, R: np.ndarray, block: int = 4096) -> np.ndarray:
    """Exact integer L @ R via float32 (|entries| ≤ 4·8192 < 2^24)."""
    out = np.empty((L.shape[0], R.shape[1]), dtype=np.int32)
    Rf = R.astype(np.float32)
    for s in range(0, L.shape[0], block):
        out[s:s + block] = (L[s:s + block].astype(np.float32) @ Rf).astype(np.int32)
    return out


# ---------------------------------------------------------------------------
# codebooks
# ---------------------------------------------------------------------------

@dataclass
class Codebook:
    seed: int
    ctx_tokens: np.ndarray      # int64, the N_CONTEXT context tokens
    counts: np.ndarray          # int64 unigram counts
    eng: np.ndarray             # uint64 (V, WORDS)
    wide: np.ndarray            # uint64 (V, WORDS)
    idf: np.ndarray             # int32 (V,)
    classes: np.ndarray         # int16 (V,), 0 = boundary

    def digest(self) -> str:
        h = hashlib.sha256()
        for a in (self.ctx_tokens, self.counts, self.eng, self.wide, self.idf, self.classes):
            h.update(np.ascontiguousarray(a).tobytes())
        return h.hexdigest()

    def save(self, path) -> None:
        np.savez(path, seed=np.array([self.seed]), ctx_tokens=self.ctx_tokens, counts=self.counts,
                 eng=self.eng, wide=self.wide, idf=self.idf, classes=self.classes)

    @classmethod
    def load(cls, path) -> Codebook:
        z = np.load(path)
        return cls(int(z["seed"][0]), z["ctx_tokens"], z["counts"], z["eng"], z["wide"], z["idf"], z["classes"])


def context_vocabulary(counts: np.ndarray, n_ctx: int = N_CONTEXT) -> np.ndarray:
    """The n_ctx most frequent non-EOS tokens (ties by id), and the token→index map."""
    order = np.lexsort((np.arange(len(counts)), -counts))
    order = order[order != 0][:n_ctx]
    return order.astype(np.int64)


def _signed_index(im: ItemMemory, tokens: np.ndarray, shift: int) -> np.ndarray:
    packed = im.vectors([f"lm:ctx:{int(t)}" for t in tokens])
    if shift:
        packed = permute(packed, shift, D_S)
    bits = np.unpackbits(packed, axis=-1, count=D_S)
    return bits.astype(np.int8) * 2 - 1


def _binarise_rows(S: np.ndarray, kind: str, seed: int) -> np.ndarray:
    packed = (S > 0)
    out = np.packbits(packed, axis=-1)
    ties = np.flatnonzero((S == 0).any(axis=1))
    for w in ties:
        out[w] = _binarise(S[w], TieContext.for_prototype(D_S, f"sem:{kind}:{int(w)}", seed))
    return out


def idf_weights(df: np.ndarray, n_docs: int) -> np.ndarray:
    """Integer idf: the largest k ≤ 16 with 2^k · (df + 1) ≤ n_docs, at least 1."""
    out = np.ones(len(df), dtype=np.int32)
    for k in range(1, 17):
        out[(df + 1) * (1 << k) <= n_docs] = k
    return out


def build_codebook(tokens: np.ndarray, seed: int, vocab: int = 1 << 15, log=None) -> Codebook:
    say = log or (lambda *_: None)
    tokens = np.ascontiguousarray(tokens, dtype=np.uint16)
    counts = unigram_counts(tokens, vocab)
    df, n_docs = doc_freq(tokens, vocab)
    ctx = context_vocabulary(counts)
    cmap = np.full(vocab, -1, dtype=np.int64)
    cmap[ctx] = np.arange(len(ctx))
    im = ItemMemory(seed, D_S)
    threads = numba.get_num_threads()

    S = np.zeros((vocab, D_S), dtype=np.int32)
    for o in ENG_OFFSETS:
        C = _cooc(tokens, cmap, np.array([o], dtype=np.int64), vocab, len(ctx), threads)
        L = ppmi_levels(C)
        del C
        S += _project(L, _signed_index(im, ctx, o))
        del L
        say(f"eng offset {o}")
    eng = _binarise_rows(S, "eng", seed)
    offs = np.array([o for o in range(-WIDE_WINDOW, WIDE_WINDOW + 1) if o != 0], dtype=np.int64)
    C = _cooc(tokens, cmap, offs, vocab, len(ctx), threads)
    L = ppmi_levels(C)
    del C
    S = _project(L, _signed_index(im, ctx, 0))
    del L
    wide = _binarise_rows(S, "weit", seed)
    del S
    say("wide")
    rare = np.flatnonzero(counts < MIN_COUNT)
    if len(rare):
        eng[rare] = im.vectors([f"lm:rare:eng:{int(t)}" for t in rare])
        wide[rare] = im.vectors([f"lm:rare:weit:{int(t)}" for t in rare])
    eng_w, wide_w = as_words(eng), as_words(wide)
    classes = cluster(eng_w, counts)
    say("classes")
    return Codebook(seed, ctx, counts, eng_w, wide_w, idf_weights(df, n_docs), classes)


# ---------------------------------------------------------------------------
# clustering
# ---------------------------------------------------------------------------

@numba.njit(cache=True, parallel=True)
def _assign(vecs, centres):
    V = vecs.shape[0]
    K = centres.shape[0]
    W = vecs.shape[1]
    out = np.empty(V, dtype=np.int64)
    for v in numba.prange(V):
        best, arg = 1 << 30, 0
        for k in range(K):
            d = ham_rows(vecs, v, centres, k, W)
            if d < best:
                best, arg = d, k
        out[v] = arg
    return out


@numba.njit(cache=True)
def _majority(vecs, assign, use, centres):
    K, W = centres.shape
    D = W * 64
    tally = np.zeros((K, D), dtype=np.int64)
    size = np.zeros(K, dtype=np.int64)
    for v in range(vecs.shape[0]):
        if not use[v]:
            continue
        k = assign[v]
        size[k] += 1
        for b in range(D):
            bit = (vecs[v, b >> 6] >> np.uint64(63 - (b & 63))) & np.uint64(1)
            tally[k, b] += 1 if bit else -1
    out = centres.copy()
    for k in range(K):
        if size[k] == 0:
            continue
        for b in range(D):
            t = tally[k, b]
            if t == 0:
                continue                     # exact tie: keep the previous centre bit
            mask = np.uint64(1) << np.uint64(63 - (b & 63))
            if t > 0:
                out[k, b >> 6] |= mask
            else:
                out[k, b >> 6] &= ~mask
    return out


def cluster(vecs: np.ndarray, counts: np.ndarray, k: int = N_CLASSES - 1, iters: int = CLUSTER_ITERS) -> np.ndarray:
    """Word classes 1..k by Hamming k-majority; centres start at the k most frequent tokens."""
    frequent = np.lexsort((np.arange(len(counts)), -counts))
    frequent = frequent[frequent != 0][:k]
    centres = vecs[frequent].copy()
    use = counts >= MIN_COUNT
    use[0] = False
    assign = _assign(vecs, centres)
    for _ in range(iters):
        centres = _majority(vecs, assign, use, centres)
        new = _assign(vecs, centres)
        if np.array_equal(new, assign):
            break
        assign = new
    classes = (assign + 1).astype(np.int16)
    classes[0] = 0
    return classes


# ---------------------------------------------------------------------------
# topic bundles
# ---------------------------------------------------------------------------

@numba.njit(cache=True)
def bundle_words(wide, idf, toks, tiebreak, words):
    """Sign of Σ idf(t)·(±wide[t]) over ``toks`` using the first ``words`` words; an odd
    total weight is ensured with the tie-break vector, so no component is ever zero."""
    D = words * 64
    acc = np.zeros(D, dtype=np.int64)
    total = 0
    for t in toks:
        wgt = idf[t]
        total += wgt
        for b in range(D):
            bit = (wide[t, b >> 6] >> np.uint64(63 - (b & 63))) & np.uint64(1)
            acc[b] += wgt if bit else -wgt
    if total % 2 == 0:
        for b in range(D):
            bit = (tiebreak[b >> 6] >> np.uint64(63 - (b & 63))) & np.uint64(1)
            acc[b] += 1 if bit else -1
    out = np.zeros(words, dtype=np.uint64)
    for b in range(D):
        if acc[b] > 0:
            out[b >> 6] |= np.uint64(1) << np.uint64(63 - (b & 63))
    return out


def tiebreak_vector(seed: int) -> np.ndarray:
    return as_words(ItemMemory(seed, D_S).vector("lm:topic:tiebreak")[None, :])[0]
