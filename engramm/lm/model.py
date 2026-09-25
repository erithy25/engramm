"""HDCLanguageModel: ENGRAMM writing English by reading and counting.

(docs/PREREG_LM.md §5.) Five components are mixed per next token:

    KN5    exact 5-gram statistics (modified Kneser-Ney)
    INF    ∞-gram: longest earlier occurrence of the history (suffix array)
    CACHE  the current document's own words
    KNN    HDC similarity memory: contexts that *mean* the same (knn.py)
    TOPIC  HDC topic vector of the last 256 tokens (topic.py)

**User layer (learn / forget).** Texts taught with :meth:`learn_text` form a
separate layer that is recomputed from scratch, as a pure function of the set
of live user texts (sorted by source id), on every learn and forget:

* the KN component is adapted by Dirichlet interpolation with the user
  counts of the longest matching user context (μ = 2);
* the user texts get their own small suffix array (INF counts add up);
* every user position is a KNN candidate, each text with its own topic
  signature.

Hence learn(A, B) followed by forget(B) is *identical* to learn(A) — same
state digest, same probabilities, bit for bit. Base documents can be
forgotten too: they are tomb-stoned immediately (never retrieved, quoted or
cited again, their ∞-gram counts subtracted) and removed from all statistics
by :meth:`consolidate`, which rebuilds the base model.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engramm.lm import knn as K
from engramm.lm.mixture import inf_bin, kn_bin, knn_bin
from engramm.lm.ngram import KNModel, build_kn, valid_history
from engramm.lm.semantic import Codebook, build_codebook, tiebreak_vector
from engramm.lm.stream import TokenSplit
from engramm.lm.suffix import MAX_MATCH, SuffixIndex, _dist_counts, build_suffix_array
from engramm.lm.tokenizer import EOS, LMTokenizer
from engramm.lm.topic import cache_distribution, stream_cache, stream_topic, topic_distribution, topic_table

COMPONENTS = ("kn", "inf", "cache", "knn", "topic")
DIRICHLET_MU = 2.0
USER_MAX_ORDER = 5


@dataclass
class MixtureSpec:
    components: tuple[str, ...]
    weights: np.ndarray                   # (n_buckets, C)
    knn_edges: np.ndarray | None
    tau: float
    beta: float

    def to_json(self) -> str:
        return json.dumps({"components": list(self.components), "weights": self.weights.tolist(),
                           "knn_edges": None if self.knn_edges is None else self.knn_edges.tolist(),
                           "tau": self.tau, "beta": self.beta})

    @classmethod
    def from_json(cls, text: str) -> MixtureSpec:
        d = json.loads(text)
        return cls(tuple(d["components"]), np.asarray(d["weights"], dtype=np.float64),
                   None if d["knn_edges"] is None else np.asarray(d["knn_edges"], dtype=np.int64),
                   float(d["tau"]), float(d["beta"]))

    def bucket(self, found: int, k: int, dmin: int) -> int:
        b = int(kn_bin(np.array([found]))[0])
        if "inf" in self.components:
            b = b * 4 + int(inf_bin(np.array([k]))[0])
        if "knn" in self.components:
            b = b * 4 + int(knn_bin(np.array([dmin]), self.knn_edges)[0])
        return b


# ---------------------------------------------------------------------------
# user layer
# ---------------------------------------------------------------------------

@dataclass
class UserLayer:
    """Everything derived from the live user texts; rebuilt on every change."""

    sources: tuple[str, ...] = ()
    texts: tuple[str, ...] = ()
    tokens: np.ndarray = field(default_factory=lambda: np.zeros(1, dtype=np.uint16))
    positions: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    source_of: np.ndarray = field(default_factory=lambda: np.zeros(1, dtype=np.int64))
    segsig: np.ndarray = field(default_factory=lambda: np.zeros((1, K.SIG_WORDS), dtype=np.uint64))
    ngrams: dict = field(default_factory=dict)       # ctx tuple -> {w: count}
    sa: SuffixIndex | None = None

    def digest(self) -> str:
        h = hashlib.sha256()
        for s, t in zip(self.sources, self.texts):
            h.update(len(s.encode()).to_bytes(8, "big") + s.encode())
            h.update(len(t.encode()).to_bytes(8, "big") + t.encode())
        h.update(self.tokens.tobytes())
        return h.hexdigest()


def build_user_layer(texts: dict[str, str], tok: LMTokenizer, cb: Codebook, seed: int) -> UserLayer:
    if not texts:
        return UserLayer()
    sources = tuple(sorted(texts))
    parts, positions, source_of = [np.array([EOS], dtype=np.uint16)], [], [-1]
    length = 1
    ngrams: dict = defaultdict(lambda: defaultdict(int))
    for si, s in enumerate(sources):
        ids = tok.encode(texts[s])
        # every text starts on its own 128-token segment -> its own topic signature
        pad = (-length) % K.SEG
        if pad == 0 and length > 1:
            pad = K.SEG
        if pad:
            parts.append(np.zeros(pad, dtype=np.uint16))
            source_of.extend([-1] * pad)
            length += pad
        doc = np.concatenate([ids, [EOS]]).astype(np.uint16)
        start = length
        parts.append(doc)
        source_of.extend([si] * len(doc))
        positions.extend(range(start, start + len(doc)))
        length += len(doc)
        seq = [EOS] + [int(x) for x in doc]
        for i in range(1, len(seq)):
            for m in range(1, USER_MAX_ORDER):
                if i - m < 0:
                    break
                ctx = tuple(seq[i - m:i])
                if EOS in ctx[1:]:
                    break
                ngrams[ctx][seq[i]] += 1
    tokens = np.concatenate(parts).astype(np.uint16)
    segsig = K.segment_signatures(tokens, cb.wide, cb.idf, tiebreak_vector(seed))
    frozen = {c: dict(v) for c, v in ngrams.items()}
    return UserLayer(sources, tuple(texts[s] for s in sources), tokens,
                     np.asarray(positions, dtype=np.int64), np.asarray(source_of, dtype=np.int64),
                     segsig, frozen, SuffixIndex(tokens))


# ---------------------------------------------------------------------------
# the model
# ---------------------------------------------------------------------------

class HDCLanguageModel:
    def __init__(self, train: TokenSplit, kn: KNModel, sa: np.ndarray, cb: Codebook, pos: np.ndarray,
                 segsig: np.ndarray, mixture: MixtureSpec, seed: int, tok: LMTokenizer | None = None,
                 epoch: int = 0):
        self.train = train
        self.tokens = np.ascontiguousarray(train.tokens, dtype=np.uint16)
        self.kn = kn
        self.index = SuffixIndex(self.tokens, sa, np.asarray(train.doc_starts))
        self.cb = cb
        self.classes = cb.classes.astype(np.int16)
        self.pos = pos
        self.segsig = segsig
        self.mix = mixture
        self.seed = seed
        self.tok = tok or LMTokenizer()
        self.epoch = epoch
        self.tiebreak = tiebreak_vector(seed)
        self.knn_table = K.kernel_tables([mixture.tau])[0]
        self.topic_tab = topic_table(mixture.beta)
        self.vocab = kn.vocab_size
        self.user_texts: dict[str, str] = {}
        self.user = UserLayer()
        self.tombstones: set[int] = set()
        self._tomb = (np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64))
        self._base_digest: str | None = None
        self._key_to_doc = {tuple(k): i for i, k in enumerate(train.doc_keys)}

    # -- construction ------------------------------------------------------------------

    @classmethod
    def build(cls, train: TokenSplit, seed: int, mixture: MixtureSpec, log=None,
              tok: LMTokenizer | None = None, epoch: int = 0) -> HDCLanguageModel:
        t = np.ascontiguousarray(train.tokens, dtype=np.uint16)
        kn = build_kn(t, order=5, log=log)
        sa = build_suffix_array(t)
        cb = build_codebook(t, seed, log=log)
        pos = K.build_index(t, cb.classes)
        seg = K.segment_signatures(t, cb.wide, cb.idf, tiebreak_vector(seed))
        return cls(train, kn, sa, cb, pos, seg, mixture, seed, tok, epoch)

    def save(self, directory: Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.kn.save(directory / "kn5")
        np.save(directory / "sa.npy", self.index.sa)
        self.cb.save(directory / "codebook.npz")
        np.save(directory / "knn_pos.npy", self.pos)
        np.save(directory / "segsig.npy", self.segsig)
        (directory / "mixture.json").write_text(self.mix.to_json())
        (directory / "meta.json").write_text(json.dumps({"seed": self.seed, "epoch": self.epoch}))
        self.train.save(directory, "train")

    @classmethod
    def load(cls, directory: Path, tok: LMTokenizer | None = None) -> HDCLanguageModel:
        directory = Path(directory)
        meta = json.loads((directory / "meta.json").read_text())
        return cls(TokenSplit.load(directory, "train", mmap=False), KNModel.load(directory / "kn5"),
                   np.load(directory / "sa.npy"), Codebook.load(directory / "codebook.npz"),
                   np.load(directory / "knn_pos.npy"), np.load(directory / "segsig.npy"),
                   MixtureSpec.from_json((directory / "mixture.json").read_text()), int(meta["seed"]), tok,
                   int(meta["epoch"]))

    # -- state ---------------------------------------------------------------------------

    def base_digest(self) -> str:
        if self._base_digest is None:
            h = hashlib.sha256()
            h.update(self.kn.digest().encode())
            for a in (self.tokens, self.index.sa, self.pos, self.segsig):
                h.update(hashlib.sha256(np.ascontiguousarray(a).tobytes()).digest())
            h.update(self.cb.digest().encode())
            h.update(self.mix.to_json().encode())
            self._base_digest = h.hexdigest()
        return self._base_digest

    def state_digest(self) -> str:
        h = hashlib.sha256()
        h.update(self.base_digest().encode())
        h.update(self.user.digest().encode())
        h.update(",".join(str(d) for d in sorted(self.tombstones)).encode())
        h.update(str(self.epoch).encode())
        return h.hexdigest()

    # -- learning and forgetting ------------------------------------------------------------

    def learn_text(self, text: str, source_id: str) -> None:
        if not source_id:
            raise ValueError("source_id must be non-empty")
        if source_id in self.user_texts:
            raise ValueError(f"source {source_id!r} already learnt; forget it first")
        self.user_texts[source_id] = text
        self.user = build_user_layer(self.user_texts, self.tok, self.cb, self.seed)

    def forget(self, source_id: str) -> str:
        """Forget a user text (exact, immediately) or a base document given as
        ``"<source>\\x00<key>"`` (tomb-stoned now, removed from statistics by consolidate)."""
        if source_id in self.user_texts:
            del self.user_texts[source_id]
            self.user = build_user_layer(self.user_texts, self.tok, self.cb, self.seed)
            return "user"
        src, _, key = source_id.partition("\x00")
        doc = self._key_to_doc.get((src, key))
        if doc is None:
            raise KeyError(f"unknown source {source_id!r}")
        self.tombstones.add(doc)
        lo = np.array([int(self.train.doc_starts[d]) for d in sorted(self.tombstones)], dtype=np.int64)
        hi = np.array([self.train.doc_end(d) + 1 for d in sorted(self.tombstones)], dtype=np.int64)
        self._tomb = (lo, hi)
        return "base"

    def consolidate(self, log=None) -> HDCLanguageModel:
        """Rebuild the base model without tomb-stoned documents and with the user texts
        folded in (a new meaning epoch). Returns the new model; mixture weights are kept."""
        keep = np.array([d for d in range(self.train.n_docs) if d not in self.tombstones], dtype=np.int64)
        base = self.train.select(keep)
        if self.user_texts:
            from engramm.lm.stream import build_split
            srcs = sorted(self.user_texts)
            extra = build_split([self.user_texts[s] for s in srcs], [("user", s) for s in srcs],
                                self.tok.encode_batch)
            base = TokenSplit(np.concatenate([base.tokens, extra.tokens[1:]]),
                              np.concatenate([base.doc_starts, extra.doc_starts + len(base.tokens) - 1]),
                              np.concatenate([base.doc_bytes, extra.doc_bytes]),
                              base.doc_keys + extra.doc_keys)
        return HDCLanguageModel.build(base, self.seed, self.mix, log=log, tok=self.tok, epoch=self.epoch + 1)

    # -- components ------------------------------------------------------------------------

    def _kn(self, h: np.ndarray) -> np.ndarray:
        p = self.kn.distribution(h)
        if not self.user.ngrams:
            return p
        for m in range(min(USER_MAX_ORDER - 1, len(h)), 0, -1):
            ctx = tuple(int(x) for x in h[len(h) - m:])
            nxt = self.user.ngrams.get(ctx)
            if nxt:
                total = sum(nxt.values())
                p = p * DIRICHLET_MU
                for w, c in nxt.items():
                    p[w] += c
                return p / (total + DIRICHLET_MU)
        return p

    def _tomb_counts(self, pattern: np.ndarray) -> np.ndarray:
        """Next-token counts of ``pattern`` inside tomb-stoned base documents."""
        out = np.zeros(self.vocab, dtype=np.int64)
        k = len(pattern)
        for lo, hi in zip(*self._tomb):
            seg = self.tokens[lo - 1:hi]          # include the document's leading EOS
            if len(seg) <= k:
                continue
            win = np.lib.stride_tricks.sliding_window_view(seg[:-1], k)
            hits = np.flatnonzero((win == pattern).all(axis=1))
            for s in hits:
                out[seg[s + k]] += 1
        return out

    def _inf(self, h: np.ndarray) -> tuple[int, np.ndarray | None]:
        hb = np.ascontiguousarray(h[-MAX_MATCH:])
        kb, lob, hib = self.index.match(hb)
        ku = 0
        if self.user.sa is not None:
            ku, lou, hiu = self.user.sa.match(hb)
        k = max(kb, ku)
        if k == 0:
            return 0, None
        counts = np.zeros(self.vocab, dtype=np.int64)
        if kb == k:
            counts += _dist_counts(self.tokens, self.index.sa, lob, hib, k, self.vocab)
            if self._tomb[0].size:
                counts -= self._tomb_counts(hb[len(hb) - k:])
        if ku == k:
            counts += _dist_counts(self.user.tokens, self.user.sa.sa, lou, hiu, k, self.vocab)
        total = counts.sum()
        if total <= 0:
            return k, None
        return k, counts / total

    def _knn(self, h: np.ndarray, full_history: np.ndarray):
        ev = np.concatenate([h, [0]]).astype(np.uint16)
        i = len(h)
        qt = np.empty(K.DEPTH, dtype=np.int64)
        qkey = K._query_parts(ev, i, self.classes, qt)
        qsig = K.query_sig(full_history, self.cb.wide, self.cb.idf, self.tiebreak)
        return K.score_candidates(self.tokens, self.classes, self.pos, self.cb.eng, self.segsig, qt, qkey, qsig,
                                  self._tomb[0], self._tomb[1], self.user.tokens, self.user.positions,
                                  self.user.segsig)

    def next_distribution(self, history, detail: bool = False):
        """p(· | history) over the vocabulary; history = token ids (EOS = document start)."""
        full = np.asarray(history, dtype=np.uint16)
        if len(full) == 0 or full[0] != EOS:
            full = np.concatenate([[EOS], full]).astype(np.uint16)
        h = valid_history(full, MAX_MATCH)
        p_kn = self._kn(valid_history(full, self.kn.order - 1))
        found = self.kn.context_order(full)
        comps = {"kn": p_kn}
        k, p_inf = (0, None)
        if "inf" in self.mix.components:
            k, p_inf = self._inf(h)
            comps["inf"] = p_kn if p_inf is None else p_inf
        if "cache" in self.mix.components:
            c = cache_distribution(full, self.vocab)
            comps["cache"] = p_kn if c is None else c
        dmin, knn_info = -1, None
        if "knn" in self.mix.components:
            dist, nxt, src, _ = self._knn(valid_history(full, K.DEPTH + 1), full)
            if len(dist):
                dmin = int(dist.min())
                comps["knn"] = K.knn_distribution(dist, nxt, self.knn_table, self.vocab)
                knn_info = (dist, nxt, src)
            else:
                comps["knn"] = p_kn
        if "topic" in self.mix.components:
            tp = topic_distribution(full, self.cb.wide, self.cb.idf, self.tiebreak, self.kn.p_uni, self.topic_tab)
            comps["topic"] = p_kn if tp is None else tp
        b = self.mix.bucket(found, k, dmin)
        lam = self.mix.weights[b]
        out = np.zeros(self.vocab, dtype=np.float64)
        for c, name in enumerate(self.mix.components):
            out += lam[c] * comps[name]
        if detail:
            return out, {"bucket": b, "weights": dict(zip(self.mix.components, lam.tolist())),
                         "inf_match": k, "knn_dmin": dmin, "knn": knn_info, "components": comps}
        return out

    # -- evaluation over a stream (no user layer, no tombstones) ------------------------------

    def stream_probs(self, ev: np.ndarray) -> np.ndarray:
        """p(ev[i] | ev[:i]) for i = 1..len−1 with the stream kernels (fast path for evaluation)."""
        if self.user.sources or self.tombstones:
            raise RuntimeError("stream evaluation is defined for the base model only")
        e = np.ascontiguousarray(ev, dtype=np.uint16)
        positions = np.arange(1, len(e), dtype=np.int64)
        starts = np.flatnonzero(e[:-1] == EOS) + 1
        ends = np.append(starts[1:] - 1, len(e) - 1)
        keep = starts <= ends
        starts, ends = starts[keep], ends[keep]
        p_kn, found = self.kn.stream_probs(e)
        cols = {"kn": p_kn}
        k = np.zeros(len(positions), dtype=np.int64)
        dmin = np.full(len(positions), -1, dtype=np.int64)
        if "inf" in self.mix.components:
            k, cnt, cntw = self.index.stream_stats(e)
            cols["inf"] = np.where(cnt > 0, cntw / np.maximum(cnt, 1), p_kn)
        if "cache" in self.mix.components:
            c = stream_cache(e, starts, ends, self.vocab)[1:]
            cols["cache"] = np.where(c >= 0, c, p_kn)
        if "knn" in self.mix.components:
            qs = K.stream_query_sigs(e, positions, self.cb.wide, self.cb.idf, self.tiebreak, 16, K.SEG)
            empty = np.zeros(0, dtype=np.int64)
            pk, dmin, ncand = K.stream_knn(self.tokens, self.classes, self.pos, self.cb.eng, self.segsig, e, qs,
                                           self.knn_table[None, :], empty, empty, np.zeros(1, dtype=np.uint16),
                                           empty, np.zeros((1, K.SIG_WORDS), dtype=np.uint64), positions)
            cols["knn"] = np.where(ncand > 0, pk[:, 0], p_kn)
        if "topic" in self.mix.components:
            tp = stream_topic(e, starts, ends, self.cb.wide, self.cb.idf, self.tiebreak, self.kn.p_uni,
                              self.topic_tab[None, :])[1:, 0]
            cols["topic"] = np.where(tp >= 0, tp, p_kn)
        b = kn_bin(found)
        if "inf" in self.mix.components:
            b = b * 4 + inf_bin(k)
        if "knn" in self.mix.components:
            b = b * 4 + knn_bin(dmin, self.mix.knn_edges)
        P = np.stack([cols[c] for c in self.mix.components], axis=1)
        return np.einsum("ij,ij->i", P, self.mix.weights[b])

    # -- provenance ---------------------------------------------------------------------------

    def _describe(self, stream_pos: int) -> dict:
        if stream_pos < 0:
            up = -1 - stream_pos
            si = int(self.user.source_of[up])
            return {"kind": "user", "source": self.user.sources[si]}
        d = int(self.index.doc_of(np.array([stream_pos]))[0])
        src, key = self.train.doc_keys[d]
        off = stream_pos - int(self.train.doc_starts[d])
        return {"kind": "base", "source": src, "key": key, "token_offset": off}

    def why(self, history, token: int, n: int = 3) -> dict:
        """Where did ``token`` after ``history`` come from? Longest verbatim source and the
        closest similar contexts that continued with the same token."""
        full = np.asarray(history, dtype=np.uint16)
        if len(full) == 0 or full[0] != EOS:
            full = np.concatenate([[EOS], full]).astype(np.uint16)
        h = valid_history(full, MAX_MATCH - 1)
        pat = np.concatenate([h, [token]]).astype(np.uint16)
        verbatim = []
        for k in range(len(pat), 0, -1):
            occ = [int(p) for p in self.index.occurrences(pat[len(pat) - k:], limit=64)
                   if not any(lo <= p < hi for lo, hi in zip(*self._tomb))]
            uocc = []
            if self.user.sa is not None:
                uocc = [int(p) for p in self.user.sa.occurrences(pat[len(pat) - k:], limit=16)]
            if occ or uocc:
                verbatim = [{"match_tokens": k, **self._describe(-1 - p)} for p in uocc[:n]]
                verbatim += [{"match_tokens": k, **self._describe(p)} for p in occ[:n - len(verbatim)]]
                break
        similar = []
        if "knn" in self.mix.components:
            dist, nxt, src, _ = self._knn(valid_history(full, K.DEPTH + 1), full)
            sel = np.flatnonzero(nxt == token)
            order = sel[np.lexsort((src[sel], dist[sel]))][:n]
            for r in order:
                p = int(src[r])
                ctx_end = p if p >= 0 else -1 - p
                toks = self.tokens if p >= 0 else self.user.tokens
                ctx = toks[max(0, ctx_end - 6):ctx_end]
                similar.append({"distance": int(dist[r]), "context": self.tok.decode(ctx), **self._describe(p)})
        return {"token": self.tok.decode([token]), "verbatim": verbatim, "similar": similar}
