"""KNN: the HDC similarity memory (docs/PREREG_LM.md §5, §7).

Every train position p ("after this context came token t[p]") is a memory.
Two contexts are compared by their last six tokens' narrow meaning vectors,
weighted by recency, plus a topic term:

    d(q, p) = Σ_{j=1..6} w_j · ham(eng[q_{−j}], eng[t[p−j]]) + v · 8 · ham₂₅₆(sig_q, sig_seg(p))

with w = (8, 4, 2, 1, 1, 1). Keys are never stored: they are computed from
the token stream on demand, so memory is one int32 per position and a key
cannot go stale.

Candidates come from a deterministic class tree: positions sorted by the
word classes of their six context tokens (most recent first), then by
position. A query takes the deepest class prefix that still holds ≥ k_min
positions and, if that range is larger than B_max, the B_max positions
around where its own full key would sit. All candidates are scored exactly;
the prediction is a kernel average of their next tokens,

    p_knn(w) = Σ_{p: t[p]=w} K(d_p − d_min) / Σ_p K(d_p − d_min),  K(Δ) = exp(−Δ/τ),

with K read from a stored table. Order of summation = candidate order, so
the result is a fixed function of the data.
"""

from __future__ import annotations

import numba
import numpy as np

from engramm.lm.semantic import bundle_words, popcount64

DEPTH = 6
POS_WEIGHTS = np.array([8, 4, 2, 1, 1, 1], dtype=np.int64)
CLASS_BITS = 9
K_MIN = 64
B_MAX = 16384
SEG = 128
SIG_WORDS = 4                     # 256-bit topic signatures
TOPIC_V = 2
MAX_DIST = int(POS_WEIGHTS.sum()) * 2048 + TOPIC_V * 8 * SIG_WORDS * 64


def kernel_tables(taus) -> np.ndarray:
    """exp(−Δ/τ) for Δ = 0..MAX_DIST, one row per τ (computed once, then stored)."""
    delta = np.arange(MAX_DIST + 1, dtype=np.float64)
    return np.stack([np.exp(-delta / float(t)) for t in taus])


@numba.njit(cache=True)
def _ctx_tokens(tokens, p, out):
    """The six tokens before p, most recent first; after a document start: 0."""
    stop = False
    for j in range(DEPTH):
        q = p - 1 - j
        if stop or q < 0:
            out[j] = 0
            continue
        t = tokens[q]
        out[j] = t
        if t == 0:
            stop = True


@numba.njit(cache=True)
def _key(tokens, classes, p):
    key = np.uint64(0)
    stop = False
    for j in range(DEPTH):
        q = p - 1 - j
        c = 0
        if not stop and q >= 0:
            t = tokens[q]
            if t == 0:
                stop = True
            else:
                c = classes[t]
        key = (key << np.uint64(CLASS_BITS)) | np.uint64(c)
    return key


@numba.njit(cache=True, parallel=True)
def _all_keys(tokens, classes):
    n = len(tokens)
    keys = np.empty(n - 1, dtype=np.uint64)
    for p in numba.prange(1, n):
        keys[p - 1] = _key(tokens, classes, p)
    return keys


def build_index(tokens: np.ndarray, classes: np.ndarray) -> np.ndarray:
    """Positions 1..n−1 sorted by (class key, position)."""
    keys = _all_keys(np.ascontiguousarray(tokens, dtype=np.uint16), classes.astype(np.int16))
    order = np.argsort(keys, kind="stable")
    del keys
    order += 1
    return order.astype(np.int32 if len(tokens) < 2**31 else np.int64)


@numba.njit(cache=True, parallel=True)
def segment_signatures(tokens, wide, idf, tiebreak):
    n_seg = (len(tokens) + SEG - 1) // SEG
    out = np.zeros((n_seg, SIG_WORDS), dtype=np.uint64)
    for s in numba.prange(n_seg):
        seg = tokens[s * SEG:min(len(tokens), (s + 1) * SEG)]
        m = 0
        for t in seg:
            if t != 0:
                m += 1
        toks = np.empty(m, dtype=np.uint16)
        k = 0
        for t in seg:
            if t != 0:
                toks[k] = t
                k += 1
        out[s] = bundle_words(wide, idf, toks, tiebreak, SIG_WORDS)
    return out


@numba.njit(cache=True)
def _lower(tokens, classes, pos, lo, hi, key):
    while lo < hi:
        mid = (lo + hi) >> 1
        if _key(tokens, classes, pos[mid]) < key:
            lo = mid + 1
        else:
            hi = mid
    return lo


@numba.njit(cache=True)
def candidate_window(tokens, classes, pos, qkey):
    """[lo, hi) of index entries to scan for a query with full class key ``qkey``."""
    n = len(pos)
    for d in range(DEPTH, 0, -1):
        shift = np.uint64(CLASS_BITS * (DEPTH - d))
        prefix = qkey >> shift
        lo = _lower(tokens, classes, pos, 0, n, prefix << shift)
        hi = _lower(tokens, classes, pos, lo, n, (prefix + np.uint64(1)) << shift)
        if hi - lo >= K_MIN or d == 1:
            if hi - lo > B_MAX:
                ins = _lower(tokens, classes, pos, lo, hi, qkey)
                a = ins - B_MAX // 2
                if a < lo:
                    a = lo
                if a + B_MAX > hi:
                    a = hi - B_MAX
                return a, a + B_MAX, d
            return lo, hi, d
    return 0, 0, 0


@numba.njit(cache=True)
def _dist(sem, qt, tokens, p, ct, qsig, segsig, sig_seg):
    _ctx_tokens(tokens, p, ct)
    W = sem.shape[1]
    d = 0
    for j in range(DEPTH):
        a, b = qt[j], ct[j]
        if a != b:
            s = 0
            for k in range(W):
                s += popcount64(sem[a, k] ^ sem[b, k])
            d += POS_WEIGHTS[j] * s
    if TOPIC_V > 0:
        s = 0
        for k in range(SIG_WORDS):
            s += popcount64(qsig[k] ^ segsig[sig_seg, k])
        d += TOPIC_V * 8 * s
    return d


@numba.njit(cache=True)
def _is_tomb(p, tomb_lo, tomb_hi):
    if len(tomb_lo) == 0:
        return False
    lo, hi = 0, len(tomb_lo)
    while lo < hi:
        mid = (lo + hi) >> 1
        if tomb_lo[mid] <= p:
            lo = mid + 1
        else:
            hi = mid
    return lo > 0 and p < tomb_hi[lo - 1]


@numba.njit(cache=True)
def score_candidates(tokens, classes, pos, sem, segsig, qt, qkey, qsig, tomb_lo, tomb_hi,
                     u_tokens, u_pos, u_segsig):
    """Distances and next tokens of all candidates (base window, then every user position)."""
    lo, hi, depth = candidate_window(tokens, classes, pos, qkey)
    nb = hi - lo
    m = nb + len(u_pos)
    dist = np.empty(m, dtype=np.int64)
    nxt = np.empty(m, dtype=np.int64)
    src = np.empty(m, dtype=np.int64)      # base: stream position; user: −1 − user position
    ct = np.empty(DEPTH, dtype=np.int64)
    k = 0
    for r in range(lo, hi):
        p = pos[r]
        if _is_tomb(p, tomb_lo, tomb_hi):
            continue
        dist[k] = _dist(sem, qt, tokens, p, ct, qsig, segsig, p // SEG)
        nxt[k] = tokens[p]
        src[k] = p
        k += 1
    for r in range(len(u_pos)):
        p = u_pos[r]
        dist[k] = _dist(sem, qt, u_tokens, p, ct, qsig, u_segsig, p // SEG)
        nxt[k] = u_tokens[p]
        src[k] = -1 - p
        k += 1
    return dist[:k], nxt[:k], src[:k], depth


@numba.njit(cache=True)
def _query_parts(ev, i, classes, qt):
    _ctx_tokens(ev, i, qt)
    return _key(ev, classes, i)


@numba.njit(cache=True, parallel=True)
def stream_knn(tokens, classes, pos, sem, segsig, ev, qsigs, tables, tomb_lo, tomb_hi,
               u_tokens, u_pos, u_segsig, positions):
    """Per eval position: p_knn(target) for each kernel table row, d_min, #candidates."""
    m = len(positions)
    nt = tables.shape[0]
    probs = np.zeros((m, nt), dtype=np.float64)
    dmin_out = np.full(m, -1, dtype=np.int64)
    ncand = np.zeros(m, dtype=np.int64)
    maxd = tables.shape[1] - 1
    for q in numba.prange(m):
        i = positions[q]
        qt = np.empty(DEPTH, dtype=np.int64)
        qkey = _query_parts(ev, i, classes, qt)
        dist, nxt, src, depth = score_candidates(tokens, classes, pos, sem, segsig, qt, qkey, qsigs[q],
                                                 tomb_lo, tomb_hi, u_tokens, u_pos, u_segsig)
        n = len(dist)
        ncand[q] = n
        if n == 0:
            continue
        dmin = dist.min()
        dmin_out[q] = dmin
        target = ev[i]
        for t in range(nt):
            num = 0.0
            den = 0.0
            for r in range(n):
                dd = dist[r] - dmin
                if dd > maxd:
                    dd = maxd
                w = tables[t, dd]
                den += w
                if nxt[r] == target:
                    num += w
            probs[q, t] = num / den
    return probs, dmin_out, ncand


@numba.njit(cache=True)
def knn_distribution(dist, nxt, table, vocab):
    out = np.zeros(vocab, dtype=np.float64)
    if len(dist) == 0:
        return out
    dmin = dist.min()
    maxd = len(table) - 1
    den = 0.0
    for r in range(len(dist)):
        dd = dist[r] - dmin
        if dd > maxd:
            dd = maxd
        w = table[dd]
        den += w
        out[nxt[r]] += w
    for v in range(vocab):
        out[v] /= den
    return out


@numba.njit(cache=True, parallel=True)
def stream_query_sigs(ev, positions, wide, idf, tiebreak, every, window):
    """Topic signature of the history before each position (last ``window`` tokens of its
    document), refreshed every ``every`` tokens of the document."""
    m = len(positions)
    out = np.zeros((m, SIG_WORDS), dtype=np.uint64)
    # positions are consecutive within documents in all our eval streams; compute per refresh point
    for q in numba.prange(m):
        i = positions[q]
        start = i
        while start > 0 and ev[start - 1] != 0:
            start -= 1
        off = i - start
        anchor = start + (off // every) * every
        a = anchor - window
        if a < start:
            a = start
        out[q] = bundle_words(wide, idf, ev[a:anchor], tiebreak, SIG_WORDS)
    return out


def query_sig(history: np.ndarray, wide, idf, tiebreak, every: int = 16, window: int = SEG) -> np.ndarray:
    """The topic signature :func:`stream_query_sigs` would use for the next position."""
    h = np.ascontiguousarray(history, dtype=np.uint16)
    eos = np.flatnonzero(h == 0)
    doc = h[eos[-1] + 1:] if len(eos) else h
    anchor = (len(doc) // every) * every
    return bundle_words(wide, idf, np.ascontiguousarray(doc[max(0, anchor - window):anchor]), tiebreak, SIG_WORDS)
