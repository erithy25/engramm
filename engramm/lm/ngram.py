"""Interpolated modified Kneser-Ney n-gram model, built by exact counting.

Chen & Goodman (1998) modified Kneser-Ney, interpolated, order N ≤ 5 over a
``uint16`` token stream with ``<|eos|>`` document separators
(docs/PREREG_LM.md §5):

* An n-gram may contain ``<|eos|>`` only as its first token (document start)
  or its last token (document end); anything else crosses documents.
* Highest order: raw counts. Lower orders: continuation counts
  N1+(• v) — the number of distinct left extensions — except n-grams that
  begin with ``<|eos|>``, which cannot be left-extended and keep raw counts
  (KenLM's treatment of ``<s>``).
* Three discounts per order from that order's count-of-counts.
* Pruning: at orders ≥ ``prune_from`` every n-gram with adjusted count 1 is
  removed and its discounted mass is handed to the back-off weight, so every
  distribution still sums to exactly one (up to float rounding):
  γ'(h) = (N1(h) + D2·N2(h) + D3·N3+(h)) / A(h).
* The unigram level interpolates with the uniform distribution over V.

Everything up to the final probability is integer; a probability is a fixed
sequence of float64 basic operations, hence identical wherever IEEE-754
double arithmetic is.

Tables: per order a sorted array of context keys (tokens packed 15 bits each,
first token most significant) with pointers into an entry array (next token,
adjusted count) sorted by token within each context.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import numba
import numpy as np

from engramm.lm.tokenizer import EOS

BITS = 15
TOKEN_MASK = (1 << BITS) - 1
MAX_ORDER = 5


# ---------------------------------------------------------------------------
# numba kernels: validity, key extraction
# ---------------------------------------------------------------------------

@numba.njit(cache=True)
def run_lengths(tokens: np.ndarray, cap: int = 15) -> np.ndarray:
    """run[i] = number of consecutive non-EOS tokens directly before i (capped)."""
    n = len(tokens)
    run = np.zeros(n, dtype=np.uint8)
    r = 0
    for i in range(n):
        run[i] = r
        if tokens[i] == 0:
            r = 0
        elif r < cap:
            r += 1
    return run


@numba.njit(cache=True)
def _count_first(tokens, run, order, lo, hi, start):
    """Histogram of the first token of every valid ``order``-gram (positions ≥ start)."""
    hist = np.zeros(1 << 15, dtype=np.int64)
    for i in range(max(start, order - 1), len(tokens)):
        if run[i] >= order - 2:
            hist[tokens[i - order + 1]] += 1
    return hist


@numba.njit(cache=True)
def _gather_top(tokens, run, order, lo, hi, n_out, start):
    """First token and the remaining (order−1) tokens packed, for valid n-grams whose
    first token is in [lo, hi)."""
    first = np.empty(n_out, dtype=np.uint16)
    low = np.empty(n_out, dtype=np.uint64)
    k = 0
    for i in range(max(start, order - 1), len(tokens)):
        if run[i] >= order - 2:
            f = tokens[i - order + 1]
            if f >= lo and f < hi:
                key = np.uint64(0)
                for j in range(i - order + 2, i + 1):
                    key = (key << np.uint64(15)) | np.uint64(tokens[j])
                first[k] = f
                low[k] = key
                k += 1
    return first, low


@numba.njit(cache=True)
def _gather_eos_start(tokens, run, order, start):
    """Full keys of valid ``order``-grams whose first token is EOS (document starts)."""
    n = 0
    for i in range(max(start, order - 1), len(tokens)):
        if run[i] >= order - 2 and tokens[i - order + 1] == 0:
            n += 1
    out = np.empty(n, dtype=np.uint64)
    k = 0
    for i in range(max(start, order - 1), len(tokens)):
        if run[i] >= order - 2 and tokens[i - order + 1] == 0:
            key = np.uint64(0)
            for j in range(i - order + 1, i + 1):
                key = (key << np.uint64(15)) | np.uint64(tokens[j])
            out[k] = key
            k += 1
    return out


@numba.njit(cache=True)
def _unique_counts_sorted(a):
    """Distinct values of a sorted array and their multiplicities (uint32)."""
    n = len(a)
    if n == 0:
        return np.zeros(0, dtype=np.uint64), np.zeros(0, dtype=np.uint32)
    d = 1
    for i in range(1, n):
        if a[i] != a[i - 1]:
            d += 1
    keys = np.empty(d, dtype=np.uint64)
    cnt = np.zeros(d, dtype=np.uint32)
    k = 0
    keys[0] = a[0]
    for i in range(n):
        if i > 0 and a[i] != a[i - 1]:
            k += 1
            keys[k] = a[i]
        cnt[k] += 1
    return keys, cnt


@numba.njit(cache=True)
def _merge_sorted(k1, c1, k2, c2):
    """Merge two sorted, disjoint key sets with counts."""
    n = len(k1) + len(k2)
    keys = np.empty(n, dtype=np.uint64)
    cnt = np.empty(n, dtype=np.uint32)
    i = j = 0
    for o in range(n):
        if j >= len(k2) or (i < len(k1) and k1[i] < k2[j]):
            keys[o] = k1[i]
            cnt[o] = c1[i]
            i += 1
        else:
            keys[o] = k2[j]
            cnt[o] = c2[j]
            j += 1
    return keys, cnt


@numba.njit(cache=True)
def _table_from_keys(keys, a, prune):
    """Table arrays from sorted full n-gram keys (context = key >> 15) and adjusted counts."""
    n = len(keys)
    coc = np.zeros(4, dtype=np.int64)
    n_ctx = 0
    n_keep = 0
    i = 0
    while i < n:
        c = keys[i] >> np.uint64(15)
        j = i
        kept = 0
        while j < n and (keys[j] >> np.uint64(15)) == c:
            if a[j] <= 4:
                coc[a[j] - 1] += 1
            if not prune or a[j] >= 2:
                kept += 1
            j += 1
        if kept > 0:
            n_ctx += 1
            n_keep += kept
        i = j
    ctx = np.empty(n_ctx, dtype=np.uint64)
    ptr = np.zeros(n_ctx + 1, dtype=np.int64)
    total = np.zeros(n_ctx, dtype=np.uint64)
    n1 = np.zeros(n_ctx, dtype=np.uint32)
    n2 = np.zeros(n_ctx, dtype=np.uint32)
    n3 = np.zeros(n_ctx, dtype=np.uint32)
    w = np.empty(n_keep, dtype=np.uint16)
    aa = np.empty(n_keep, dtype=np.uint32)
    r = 0
    e = 0
    i = 0
    while i < n:
        c = keys[i] >> np.uint64(15)
        j = i
        tot = np.uint64(0)
        c1 = c2 = c3 = 0
        start = e
        while j < n and (keys[j] >> np.uint64(15)) == c:
            x = a[j]
            tot += np.uint64(x)
            if x == 1:
                c1 += 1
            elif x == 2:
                c2 += 1
            else:
                c3 += 1
            if not prune or x >= 2:
                w[e] = np.uint16(keys[j] & np.uint64(0x7FFF))
                aa[e] = x
                e += 1
            j += 1
        if e > start:
            ctx[r] = c
            total[r] = tot
            n1[r] = c1
            n2[r] = c2
            n3[r] = c3
            r += 1
            ptr[r] = e
        i = j
    return ctx, ptr, total, n1, n2, n3, w, aa, coc


def _distinct_sorted(first: np.ndarray | None, low: np.ndarray):
    """Distinct (first, low) pairs in lexicographic order, with multiplicities."""
    if first is None:
        keys, counts = np.unique(low, return_counts=True)
        return None, keys, counts.astype(np.uint64)
    order = np.lexsort((low, first))
    f, lw = first[order], low[order]
    del order
    if len(lw) == 0:
        return f, lw, np.zeros(0, dtype=np.uint64)
    change = np.empty(len(lw), dtype=bool)
    change[0] = True
    np.not_equal(lw[1:], lw[:-1], out=change[1:])
    change[1:] |= f[1:] != f[:-1]
    idx = np.flatnonzero(change)
    counts = np.diff(np.append(idx, len(lw))).astype(np.uint64)
    return f[idx], lw[idx], counts


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

@dataclass
class OrderTable:
    """All kept n-grams of one order, grouped by context."""

    order: int
    ctx: np.ndarray        # uint64, sorted, distinct
    ptr: np.ndarray        # int64, len(ctx)+1
    total: np.ndarray      # uint64 A(h), over the *unpruned* entries
    n1: np.ndarray         # uint32 N1(h)
    n2: np.ndarray         # uint32 N2(h)
    n3: np.ndarray         # uint32 N3+(h)
    w: np.ndarray          # uint16 next token
    a: np.ndarray          # uint32 adjusted count
    coc: np.ndarray        # int64 count-of-counts n1..n4 (unpruned)
    pruned: bool

    def nbytes(self) -> int:
        return sum(x.nbytes for x in (self.ctx, self.ptr, self.total, self.n1, self.n2, self.n3, self.w, self.a))


def _table_from_sorted(order: int, ctx: np.ndarray, w: np.ndarray, a: np.ndarray, prune: bool) -> OrderTable:
    """Build a table from entries sorted by (ctx, w) with adjusted counts ``a``."""
    coc = np.array([np.count_nonzero(a == k) for k in (1, 2, 3, 4)], dtype=np.int64)
    if len(ctx) == 0:
        z64 = np.zeros(0, dtype=np.uint64)
        z32 = np.zeros(0, dtype=np.uint32)
        return OrderTable(order, z64, np.zeros(1, dtype=np.int64), z64, z32, z32, z32,
                          np.zeros(0, dtype=np.uint16), z32, coc, prune)
    change = np.empty(len(ctx), dtype=bool)
    change[0] = True
    np.not_equal(ctx[1:], ctx[:-1], out=change[1:])
    starts = np.flatnonzero(change)
    del change
    total = np.add.reduceat(a.astype(np.uint64), starts)
    n1 = np.add.reduceat((a == 1).astype(np.uint32), starts)
    n2 = np.add.reduceat((a == 2).astype(np.uint32), starts)
    n3 = np.add.reduceat((a >= 3).astype(np.uint32), starts)
    uctx = ctx[starts]
    if prune:
        keep = a >= 2
        kept_per_ctx = np.add.reduceat(keep.astype(np.int64), starts)
        rows = kept_per_ctx > 0
        uctx, total, n1, n2, n3 = uctx[rows], total[rows], n1[rows], n2[rows], n3[rows]
        ptr = np.zeros(len(uctx) + 1, dtype=np.int64)
        np.cumsum(kept_per_ctx[rows], out=ptr[1:])
        w, a = w[keep], a[keep]
    else:
        ptr = np.append(starts, len(ctx)).astype(np.int64)
    return OrderTable(order, uctx, ptr, total, n1.astype(np.uint32), n2.astype(np.uint32),
                      n3.astype(np.uint32), w.astype(np.uint16), a.astype(np.uint32), coc, prune)


def _concat_tables(parts: list[OrderTable]) -> OrderTable:
    ptrs, off = [np.zeros(1, dtype=np.int64)], 0
    for p in parts:
        ptrs.append(p.ptr[1:] + off)
        off += len(p.w)
    cat = np.concatenate
    return OrderTable(parts[0].order, cat([p.ctx for p in parts]), cat(ptrs), cat([p.total for p in parts]),
                      cat([p.n1 for p in parts]), cat([p.n2 for p in parts]), cat([p.n3 for p in parts]),
                      cat([p.w for p in parts]), cat([p.a for p in parts]),
                      np.sum([p.coc for p in parts], axis=0), parts[0].pruned)


def discounts(coc: np.ndarray) -> np.ndarray:
    """Modified-KN discounts D1, D2, D3+ from count-of-counts n1..n4 (Chen & Goodman eq. 26)."""
    n1, n2, n3, n4 = (float(x) for x in coc)
    fallback = np.array([0.5, 1.0, 1.5])
    if min(n1, n2, n3, n4) <= 0:
        return fallback
    y = n1 / (n1 + 2 * n2)
    d = np.array([1 - 2 * y * n2 / n1, 2 - 3 * y * n3 / n2, 3 - 4 * y * n4 / n3])
    for k in range(3):
        if not (0 < d[k] < k + 1):
            d[k] = fallback[k]
    return d


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------

def _chunk_ranges(hist: np.ndarray, budget: int) -> list[tuple[int, int]]:
    ranges, lo, acc = [], 0, 0
    for t in range(len(hist)):
        if acc + hist[t] > budget and acc > 0:
            ranges.append((lo, t))
            lo, acc = t, 0
        acc += int(hist[t])
    ranges.append((lo, len(hist)))
    return ranges


def _merge_keys(keys_a, cnt_a, keys_b, cnt_b):
    """Merge two disjoint sorted key sets with counts."""
    keys = np.concatenate([keys_a, keys_b])
    cnt = np.concatenate([cnt_a, cnt_b])
    o = np.argsort(keys, kind="stable")
    return keys[o], cnt[o]


def build_kn(tokens: np.ndarray, order: int = MAX_ORDER, prune_from: int = 3,
             chunk_budget: int = 30_000_000, log=None) -> KNModel:
    """Count a token stream (``[EOS] d1 [EOS] d2 … [EOS]``) into a modified-KN model."""
    if not 2 <= order <= MAX_ORDER:
        raise ValueError(f"order must be in 2..{MAX_ORDER}")
    tokens = np.ascontiguousarray(tokens, dtype=np.uint16)
    if len(tokens) < 2 or tokens[0] != EOS:
        raise ValueError("token stream must start with EOS and contain at least one token")
    if int(tokens.max()) > TOKEN_MASK:
        raise ValueError("token ids must be < 2**15")
    say = log or (lambda *_: None)
    run = run_lengths(tokens)
    tables: dict[int, OrderTable] = {}

    # --- highest order: raw counts, chunked by first token ----------------------
    n = order
    hist = _count_first(tokens, run, n, 0, 1 << 15, 1)
    parts: list[OrderTable] = []
    suffix_chunks: list[np.ndarray] = []
    for lo, hi in _chunk_ranges(hist, chunk_budget):
        m = int(hist[lo:hi].sum())
        if m == 0:
            continue
        first, low = _gather_top(tokens, run, n, lo, hi, m, 1)
        f, lw, cnt = _distinct_sorted(first, low)
        del first, low
        ctx = (f.astype(np.uint64) << np.uint64(BITS * (n - 2))) | (lw >> np.uint64(BITS))
        w = lw & np.uint64(TOKEN_MASK)
        suffix_chunks.append(lw)              # the (n−1)-gram suffix, already packed
        parts.append(_table_from_sorted(n, ctx, w, cnt, prune=n >= prune_from))
        del ctx, w, cnt
        say(f"order {n}: chunk [{lo},{hi}) {m} positions")
    tables[n] = _concat_tables(parts)
    del parts
    f = lw = None                             # noqa: F841  (release the last chunk)

    # --- lower orders: continuation counts (+ raw counts of EOS-initial n-grams) --
    # memory-lean: sort in place, count and split with numba, reuse the key array
    while n > 1:
        m = n - 1
        suffix = np.concatenate(suffix_chunks) if suffix_chunks else np.zeros(0, dtype=np.uint64)
        suffix_chunks.clear()
        suffix.sort()
        keys, cnt = _unique_counts_sorted(suffix)
        del suffix
        if m >= 2:
            eos = _gather_eos_start(tokens, run, m, 1)
            eos.sort()
            eos_keys, eos_cnt = _unique_counts_sorted(eos)
            del eos
            keys, cnt = _merge_sorted(keys, cnt, eos_keys, eos_cnt)
        tables[m] = OrderTable(m, *_table_from_keys(keys, cnt, m >= prune_from), m >= prune_from)
        say(f"order {m}: {len(keys)} distinct")
        del cnt
        if m > 1:
            np.bitwise_and(keys, np.uint64((1 << (BITS * (m - 1))) - 1), out=keys)
            suffix_chunks.append(keys)
        del keys
        n = m
    return KNModel.from_tables(tables, vocab_size=1 << BITS)


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------

@numba.njit(cache=True)
def _find_ctx(ctx_keys, key):
    lo, hi = 0, len(ctx_keys)
    while lo < hi:
        mid = (lo + hi) >> 1
        if ctx_keys[mid] < key:
            lo = mid + 1
        else:
            hi = mid
    if lo < len(ctx_keys) and ctx_keys[lo] == key:
        return lo
    return -1


@numba.njit(cache=True)
def _find_w(ws, lo, hi, w):
    while lo < hi:
        mid = (lo + hi) >> 1
        if ws[mid] < w:
            lo = mid + 1
        else:
            hi = mid
    return lo


@numba.njit(cache=True)
def _prob_one(hist, hlen, w, n_orders, p_uni, ctxs, ptrs, totals, n1s, n2s, n3s, ws, as_, disc, g1):
    """p(w | hist[:hlen]) and the highest order whose context was found.

    ``hist`` holds the history, most recent token last; the history must not
    contain EOS except possibly as its first token.
    """
    p = p_uni[w]
    found = 1
    for n in range(2, n_orders + 1):
        m = n - 1
        if hlen < m:
            break
        key = np.uint64(0)
        for j in range(hlen - m, hlen):
            key = (key << np.uint64(15)) | np.uint64(hist[j])
        r = _find_ctx(ctxs[n], key)
        if r < 0:
            continue
        found = n
        lo, hi = ptrs[n][r], ptrs[n][r + 1]
        k = _find_w(ws[n], lo, hi, w)
        a = 0
        if k < hi and ws[n][k] == w:
            a = as_[n][k]
        tot = float(totals[n][r])
        d1, d2, d3 = disc[n, 0], disc[n, 1], disc[n, 2]
        gamma = (g1[n] * n1s[n][r] + d2 * n2s[n][r] + d3 * n3s[n][r]) / tot
        disc_a = 0.0
        if a == 1:
            disc_a = d1
        elif a == 2:
            disc_a = d2
        elif a >= 3:
            disc_a = d3
        num = a - disc_a
        if num < 0.0:
            num = 0.0
        p = num / tot + gamma * p
    return p, found


@numba.njit(cache=True, parallel=True)
def _stream_logprob(tokens, run, positions, n_orders, p_uni, ctxs, ptrs, totals, n1s, n2s, n3s, ws, as_,
                    disc, g1):
    out = np.empty(len(positions), dtype=np.float64)
    found = np.empty(len(positions), dtype=np.int8)
    for q in numba.prange(len(positions)):
        i = positions[q]
        hl = min(int(run[i]) + 1, n_orders - 1)     # context may start with the EOS before the run
        if hl > i:
            hl = i
        h = tokens[i - hl:i]
        p, f = _prob_one(h, hl, tokens[i], n_orders, p_uni, ctxs, ptrs, totals, n1s, n2s, n3s, ws, as_, disc, g1)
        out[q] = p
        found[q] = f
    return out, found


@numba.njit(cache=True)
def _full_dist(hist, hlen, n_orders, p_uni, ctxs, ptrs, totals, n1s, n2s, n3s, ws, as_, disc, g1):
    dist = p_uni.copy()
    for n in range(2, n_orders + 1):
        m = n - 1
        if hlen < m:
            break
        key = np.uint64(0)
        for j in range(hlen - m, hlen):
            key = (key << np.uint64(15)) | np.uint64(hist[j])
        r = _find_ctx(ctxs[n], key)
        if r < 0:
            continue
        tot = float(totals[n][r])
        d1, d2, d3 = disc[n, 0], disc[n, 1], disc[n, 2]
        gamma = (g1[n] * n1s[n][r] + d2 * n2s[n][r] + d3 * n3s[n][r]) / tot
        for v in range(len(dist)):
            dist[v] *= gamma
        for k in range(ptrs[n][r], ptrs[n][r + 1]):
            a = as_[n][k]
            disc_a = d1 if a == 1 else (d2 if a == 2 else d3)
            num = a - disc_a
            if num > 0.0:
                dist[ws[n][k]] += num / tot
    return dist


def valid_history(history: np.ndarray, max_len: int) -> np.ndarray:
    """The last ≤ ``max_len`` tokens of ``history`` that do not cross a document start."""
    h = np.asarray(history, dtype=np.uint16)
    eos = np.flatnonzero(h == EOS)
    if len(eos):
        h = h[eos[-1]:]
    return h[-max_len:] if max_len > 0 else h[:0]


@dataclass
class KNModel:
    order: int
    vocab_size: int
    tables: dict[int, OrderTable]
    disc: np.ndarray = field(repr=False)        # (order+1, 3)
    g1: np.ndarray = field(repr=False)          # (order+1,)
    p_uni: np.ndarray = field(repr=False)       # float64 (V,)

    @classmethod
    def from_tables(cls, tables: dict[int, OrderTable], vocab_size: int) -> KNModel:
        order = max(tables)
        disc = np.zeros((order + 1, 3))
        g1 = np.zeros(order + 1)
        for n, t in tables.items():
            disc[n] = discounts(t.coc)
            g1[n] = 1.0 if t.pruned else disc[n, 0]
        t1 = tables[1]
        p_uni = np.zeros(vocab_size, dtype=np.float64)
        if len(t1.ctx):
            tot = float(t1.total[0])
            a = t1.a.astype(np.float64)
            d = np.where(t1.a == 1, disc[1, 0], np.where(t1.a == 2, disc[1, 1], disc[1, 2]))
            gamma = (g1[1] * t1.n1[0] + disc[1, 1] * t1.n2[0] + disc[1, 2] * t1.n3[0]) / tot
            p_uni[:] = gamma / vocab_size
            p_uni[t1.w] += np.maximum(a - d, 0.0) / tot
        else:
            p_uni[:] = 1.0 / vocab_size
        return cls(order, vocab_size, tables, disc, g1, p_uni)

    # numba needs homogeneous containers
    def _args(self):
        o = self.order
        empty64 = np.zeros(0, dtype=np.uint64)
        lst = numba.typed.List

        def col(name, empty):
            out = lst()
            for n in range(o + 1):
                out.append(getattr(self.tables[n], name) if n in self.tables and n >= 1 else empty)
            return out

        if not hasattr(self, "_cached_args"):
            self._cached_args = (
                o, self.p_uni, col("ctx", empty64), col("ptr", np.zeros(1, dtype=np.int64)),
                col("total", empty64), col("n1", np.zeros(0, dtype=np.uint32)),
                col("n2", np.zeros(0, dtype=np.uint32)), col("n3", np.zeros(0, dtype=np.uint32)),
                col("w", np.zeros(0, dtype=np.uint16)), col("a", np.zeros(0, dtype=np.uint32)),
                self.disc, self.g1)
        return self._cached_args

    def stream_probs(self, tokens: np.ndarray, positions: np.ndarray | None = None):
        """p(tokens[i] | history) for every position i ≥ 1 (or the given ones), and the
        highest order found. Histories never cross an EOS (document start)."""
        tokens = np.ascontiguousarray(tokens, dtype=np.uint16)
        run = run_lengths(tokens)
        if positions is None:
            positions = np.arange(1, len(tokens), dtype=np.int64)
        return _stream_logprob(tokens, run, np.asarray(positions, dtype=np.int64), *self._args())

    def prob(self, history: np.ndarray, w: int) -> float:
        h = valid_history(history, self.order - 1)
        p, _ = _prob_one(h, len(h), w, *self._args())
        return float(p)

    def distribution(self, history: np.ndarray) -> np.ndarray:
        h = valid_history(history, self.order - 1)
        return _full_dist(h, len(h), *self._args())

    def context_order(self, history: np.ndarray) -> int:
        """Highest order n whose (n−1)-token context occurs in the model."""
        h = valid_history(history, self.order - 1)
        best = 1
        for n in range(2, self.order + 1):
            if len(h) < n - 1:
                break
            key = 0
            for t in h[len(h) - (n - 1):]:
                key = (key << BITS) | int(t)
            if _find_ctx(self.tables[n].ctx, np.uint64(key)) >= 0:
                best = n
        return best

    def nbytes(self) -> int:
        return sum(t.nbytes() for t in self.tables.values()) + self.p_uni.nbytes

    def digest(self) -> str:
        h = hashlib.sha256()
        for n in sorted(self.tables):
            t = self.tables[n]
            for arr in (t.ctx, t.ptr, t.total, t.n1, t.n2, t.n3, t.w, t.a, t.coc):
                h.update(np.ascontiguousarray(arr).tobytes())
        return h.hexdigest()

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        arrays = {"meta": np.array([self.order, self.vocab_size], dtype=np.int64)}
        for n, t in self.tables.items():
            for name in ("ctx", "ptr", "total", "n1", "n2", "n3", "w", "a", "coc"):
                arrays[f"{name}_{n}"] = getattr(t, name)
            arrays[f"pruned_{n}"] = np.array([t.pruned])
        for name, arr in arrays.items():
            np.save(directory / f"{name}.npy", arr)

    @classmethod
    def load(cls, directory: Path, mmap: bool = False) -> KNModel:
        mode = "r" if mmap else None
        meta = np.load(directory / "meta.npy")
        order, vocab = int(meta[0]), int(meta[1])
        tables = {}
        for n in range(1, order + 1):
            get = {name: np.load(directory / f"{name}_{n}.npy", mmap_mode=mode)
                   for name in ("ctx", "ptr", "total", "n1", "n2", "n3", "w", "a")}
            tables[n] = OrderTable(n, **get, coc=np.load(directory / f"coc_{n}.npy"),
                                   pruned=bool(np.load(directory / f"pruned_{n}.npy")[0]))
        return cls.from_tables(tables, vocab)
