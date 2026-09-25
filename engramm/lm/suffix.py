"""∞-gram memory: a suffix array over the token stream (docs/PREREG_LM.md §5).

The suffix array is computed by ``divsufsort`` over the big-endian byte image
of the ``uint16`` stream and restricted to even byte offsets; there, byte
order equals token order, so it is exactly the suffix array of the token
sequence.

For a history h, the ∞-gram component uses the longest suffix h' of h that
occurs in the corpus (Liu et al. 2024) and predicts
p(w | h) = count(h' w) / count(h'). The same ranges give provenance: every
occurrence is a (document, position) pair.
"""

from __future__ import annotations

import numba
import numpy as np

MAX_MATCH = 128


def build_suffix_array(tokens: np.ndarray) -> np.ndarray:
    """Token-level suffix array (int32 if it fits, else int64)."""
    from pydivsufsort import divsufsort

    t = np.ascontiguousarray(tokens, dtype=np.uint16)
    raw = t.astype(">u2").view(np.uint8).copy()
    sa = divsufsort(raw)
    del raw
    even = sa[(sa & 1) == 0]
    del sa
    even >>= 1
    dtype = np.int32 if len(t) < 2**31 else np.int64
    return even.astype(dtype, copy=False)


@numba.njit(cache=True)
def _cmp(tokens, pos, pat, plen):
    """Compare the suffix at ``pos`` with ``pat[:plen]``: −1 less, 0 prefix-equal, +1 greater."""
    n = len(tokens)
    for j in range(plen):
        if pos + j >= n:
            return -1
        a = tokens[pos + j]
        b = pat[j]
        if a < b:
            return -1
        if a > b:
            return 1
    return 0


@numba.njit(cache=True)
def sa_range(tokens, sa, pat, plen, lo0, hi0):
    """[lo, hi) of suffixes in sa[lo0:hi0] that start with pat[:plen]."""
    lo, hi = lo0, hi0
    while lo < hi:
        mid = (lo + hi) >> 1
        if _cmp(tokens, sa[mid], pat, plen) < 0:
            lo = mid + 1
        else:
            hi = mid
    first = lo
    hi = hi0
    while lo < hi:
        mid = (lo + hi) >> 1
        if _cmp(tokens, sa[mid], pat, plen) <= 0:
            lo = mid + 1
        else:
            hi = mid
    return first, lo


@numba.njit(cache=True)
def longest_suffix(tokens, sa, hist, hlen, kmax):
    """Longest k ≤ min(hlen, kmax) with count(hist[hlen−k:hlen]) > 0; returns (k, lo, hi)."""
    lo_k, hi_k = 0, min(hlen, kmax)
    best_lo, best_hi = 0, len(sa)
    # occurrence is monotone in k, so binary search the length
    while lo_k < hi_k:
        mid = (lo_k + hi_k + 1) >> 1
        a, b = sa_range(tokens, sa, hist[hlen - mid:hlen], mid, 0, len(sa))
        if b > a:
            lo_k = mid
            best_lo, best_hi = a, b
        else:
            hi_k = mid - 1
    if lo_k == 0:
        return 0, 0, len(sa)
    return lo_k, best_lo, best_hi


@numba.njit(cache=True)
def _next_count(tokens, sa, lo, hi, k, w):
    """Among suffixes sa[lo:hi] (sharing a k-token prefix) how many continue with w."""
    a, b = lo, hi
    while a < b:
        mid = (a + b) >> 1
        p = sa[mid] + k
        v = tokens[p] if p < len(tokens) else -1
        if v < w:
            a = mid + 1
        else:
            b = mid
    first = a
    b = hi
    while a < b:
        mid = (a + b) >> 1
        p = sa[mid] + k
        v = tokens[p] if p < len(tokens) else -1
        if v <= w:
            a = mid + 1
        else:
            b = mid
    return a - first


@numba.njit(cache=True, parallel=True)
def _stream_inf(tokens_c, sa, ev, run, positions, kmax):
    """For each eval position: match length k, count(h'), count(h' w)."""
    m = len(positions)
    ks = np.zeros(m, dtype=np.int32)
    cnt = np.zeros(m, dtype=np.int64)
    cnt_w = np.zeros(m, dtype=np.int64)
    for q in numba.prange(m):
        i = positions[q]
        hl = min(int(run[i]) + 1, i, kmax)
        h = ev[i - hl:i]
        k, lo, hi = longest_suffix(tokens_c, sa, h, hl, kmax)
        ks[q] = k
        if k > 0:
            cnt[q] = hi - lo
            cnt_w[q] = _next_count(tokens_c, sa, lo, hi, k, ev[i])
    return ks, cnt, cnt_w


@numba.njit(cache=True)
def run_lengths_long(tokens, cap):
    n = len(tokens)
    run = np.zeros(n, dtype=np.int32)
    r = 0
    for i in range(n):
        run[i] = r
        if tokens[i] == 0:
            r = 0
        elif r < cap:
            r += 1
    return run


@numba.njit(cache=True)
def _dist_counts(tokens, sa, lo, hi, k, vocab):
    """Next-token counts of the suffixes sa[lo:hi] (group jumps: O(#distinct · log))."""
    counts = np.zeros(vocab, dtype=np.int64)
    a = lo
    n = len(tokens)
    while a < hi:
        p = sa[a] + k
        if p >= n:
            a += 1
            continue
        v = tokens[p]
        # end of the group with next token v
        b, e = a, hi
        while b < e:
            mid = (b + e) >> 1
            pp = sa[mid] + k
            vv = tokens[pp] if pp < n else -1
            if vv <= v:
                b = mid + 1
            else:
                e = mid
        counts[v] += b - a
        a = b
    return counts


@numba.njit(cache=True)
def _window_hits(tokens_c, sa, ev, starts, ends, width):
    """Per document: number of ``width``-token windows, and how many occur in the corpus."""
    nd = len(starts)
    tot = np.zeros(nd, dtype=np.int64)
    hit = np.zeros(nd, dtype=np.int64)
    for d in range(nd):
        for s in range(starts[d], ends[d] - width + 1):
            tot[d] += 1
            a, b = sa_range(tokens_c, sa, ev[s:s + width], width, 0, len(sa))
            if b > a:
                hit[d] += 1
    return tot, hit


class SuffixIndex:
    """Suffix array + stream, with ∞-gram queries and provenance."""

    def __init__(self, tokens: np.ndarray, sa: np.ndarray | None = None, doc_starts: np.ndarray | None = None):
        self.tokens = np.ascontiguousarray(tokens, dtype=np.uint16)
        self.sa = build_suffix_array(self.tokens) if sa is None else sa
        self.doc_starts = doc_starts

    def stream_stats(self, ev: np.ndarray, positions: np.ndarray | None = None, kmax: int = MAX_MATCH):
        ev = np.ascontiguousarray(ev, dtype=np.uint16)
        run = run_lengths_long(ev, kmax)
        if positions is None:
            positions = np.arange(1, len(ev), dtype=np.int64)
        return _stream_inf(self.tokens, self.sa, ev, run, np.asarray(positions, dtype=np.int64), kmax)

    def match(self, history: np.ndarray, kmax: int = MAX_MATCH) -> tuple[int, int, int]:
        """(k, lo, hi) of the longest suffix of ``history`` (not crossing a document start)."""
        h = np.ascontiguousarray(history, dtype=np.uint16)
        eos = np.flatnonzero(h == 0)
        if len(eos):
            h = h[eos[-1]:]
        h = np.ascontiguousarray(h[-kmax:])
        return longest_suffix(self.tokens, self.sa, h, len(h), kmax)

    def next_counts(self, history: np.ndarray, vocab: int, kmax: int = MAX_MATCH):
        k, lo, hi = self.match(history, kmax)
        if k == 0:
            return 0, np.zeros(vocab, dtype=np.int64)
        return k, _dist_counts(self.tokens, self.sa, lo, hi, k, vocab)

    def count(self, pattern: np.ndarray) -> int:
        p = np.ascontiguousarray(pattern, dtype=np.uint16)
        a, b = sa_range(self.tokens, self.sa, p, len(p), 0, len(self.sa))
        return int(b - a)

    def occurrences(self, pattern: np.ndarray, limit: int = 16) -> np.ndarray:
        """Stream positions where ``pattern`` starts (smallest positions first, at most ``limit``)."""
        p = np.ascontiguousarray(pattern, dtype=np.uint16)
        a, b = sa_range(self.tokens, self.sa, p, len(p), 0, len(self.sa))
        return np.sort(np.asarray(self.sa[a:b], dtype=np.int64))[:limit]

    def doc_of(self, positions: np.ndarray) -> np.ndarray:
        return np.searchsorted(self.doc_starts, positions, side="right") - 1

    def overlap(self, ev: np.ndarray, starts: np.ndarray, ends: np.ndarray, width: int = 13):
        """(windows, windows found) per document of ``ev`` — the near-duplicate statistic."""
        return _window_hits(self.tokens, self.sa, np.ascontiguousarray(ev, dtype=np.uint16),
                            np.asarray(starts, dtype=np.int64), np.asarray(ends, dtype=np.int64), width)
