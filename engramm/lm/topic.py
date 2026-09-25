"""TOPIC and CACHE components (docs/PREREG_LM.md §5).

TOPIC: the history's topic vector T is the sign of the idf-weighted sum of the
wide meaning vectors of the last 256 tokens of the document (odd total weight,
so no ties), refreshed every 16 tokens. A token's topical fit is
s(w) = (D/2 − ham(T, wide[w])) / (D/2) ∈ [−1, 1] and

    p_topic(w) ∝ p_uni(w) · exp(β · s(w)),

with exp read from a table indexed by the Hamming distance (stored once).
Active once the document has ≥ 16 tokens of history.

CACHE: unigram distribution of the document so far, active once the history
has at least one token.
"""

from __future__ import annotations

import numba
import numpy as np

from engramm.lm.semantic import D_S, WORDS, bundle_words, popcount64

TOPIC_WINDOW = 256
TOPIC_EVERY = 16


def topic_table(beta: float) -> np.ndarray:
    ham = np.arange(D_S + 1, dtype=np.float64)
    return np.exp(beta * (D_S / 2 - ham) / (D_S / 2))


@numba.njit(cache=True)
def _topic_vec(ev, start, anchor, wide, idf, tiebreak):
    a = anchor - TOPIC_WINDOW
    if a < start:
        a = start
    return bundle_words(wide, idf, ev[a:anchor], tiebreak, WORDS)


@numba.njit(cache=True)
def topic_scores(T, wide, p_uni, table):
    """Unnormalised p_uni(w)·exp(β s(w)) for all w, and its sum."""
    V = wide.shape[0]
    out = np.empty(V, dtype=np.float64)
    z = 0.0
    for w in range(V):
        h = 0
        for k in range(WORDS):
            h += popcount64(T[k] ^ wide[w, k])
        out[w] = p_uni[w] * table[h]
        z += out[w]
    return out, z


@numba.njit(cache=True, parallel=True)
def stream_topic(ev, doc_starts, doc_ends, wide, idf, tiebreak, p_uni, tables):
    """p_topic(target) per position (rows: tables), −1 where inactive. Positions are
    doc_starts[d]..doc_ends[d] (the EOS at doc_end included)."""
    n = len(ev)
    nt = tables.shape[0]
    out = np.full((n, nt), -1.0)
    V = wide.shape[0]
    for d in numba.prange(len(doc_starts)):
        s, e = doc_starts[d], doc_ends[d]
        for anchor in range(s + TOPIC_EVERY, e + 1, TOPIC_EVERY):
            T = _topic_vec(ev, s, anchor, wide, idf, tiebreak)
            hs = np.empty(V, dtype=np.int64)
            for w in range(V):
                h = 0
                for k in range(WORDS):
                    h += popcount64(T[k] ^ wide[w, k])
                hs[w] = h
            for t in range(nt):
                z = 0.0
                for w in range(V):
                    z += p_uni[w] * tables[t, hs[w]]
                for i in range(anchor, min(anchor + TOPIC_EVERY, e + 1)):
                    tg = ev[i]
                    out[i, t] = p_uni[tg] * tables[t, hs[tg]] / z
    return out


def topic_distribution(history: np.ndarray, wide, idf, tiebreak, p_uni, table) -> np.ndarray | None:
    """p_topic over V for the next position, or None when inactive."""
    h = np.ascontiguousarray(history, dtype=np.uint16)
    eos = np.flatnonzero(h == 0)
    doc = h[eos[-1] + 1:] if len(eos) else h
    anchor = (len(doc) // TOPIC_EVERY) * TOPIC_EVERY
    if anchor == 0:
        return None
    T = _topic_vec(np.ascontiguousarray(doc), 0, anchor, wide, idf, tiebreak)
    scores, z = topic_scores(T, wide, p_uni, table)
    return scores / z


@numba.njit(cache=True)
def stream_cache(ev, doc_starts, doc_ends, vocab):
    """p_cache(target) per position, −1 where the document history is empty."""
    out = np.full(len(ev), -1.0)
    counts = np.zeros(vocab, dtype=np.int64)
    for d in range(len(doc_starts)):
        s, e = doc_starts[d], doc_ends[d]
        for i in range(s, e + 1):
            n = i - s
            if n > 0:
                out[i] = counts[ev[i]] / n
            if i < e:
                counts[ev[i]] += 1
        for i in range(s, e):
            counts[ev[i]] = 0
    return out


def cache_distribution(history: np.ndarray, vocab: int) -> np.ndarray | None:
    h = np.asarray(history)
    eos = np.flatnonzero(h == 0)
    doc = h[eos[-1] + 1:] if len(eos) else h
    if len(doc) == 0:
        return None
    return np.bincount(doc.astype(np.int64), minlength=vocab).astype(np.float64) / len(doc)
