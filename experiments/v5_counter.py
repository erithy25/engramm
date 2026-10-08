"""v5, variant 3: the counting model's FULL next-token distribution, computed on the fly.

    q(w | history) = w_kn · KN5(w) + w_inf · INF(w) + w_cache · CACHE(w)

The same three components and weights as the prior of experiments/v5_prior.py (INF falls
back to KN5 without a continued match, CACHE without document history), but over the
whole vocabulary, for arbitrary windows of a token stream. Exactness: q(target) equals
the component prior to rounding (checked in ``check``).

Speed. The cost of a dense KN5 distribution is dominated by the order-2 continuation
lists of frequent one-token contexts (mean ≈ 5.4 k entries per position on val-A). The
dense order-≤2 distribution D2[u] = γ₂(u)·p_uni + c₂(u) of the M most frequent contexts
u is therefore precomputed once (M = 4096: 512 MB float32); a position then costs one
dense pass plus the short lists of orders 3–5.

Runs in a Python that has numba, numpy and torch (see experiments/v5_run3.sh):
    PYTHONPATH=/dev/shm/engramm/pt311:. .venv/bin/python -m experiments.v5_counter check
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numba
import numpy as np

from engramm.lm.ngram import KNModel, _find_ctx, run_lengths
from engramm.lm.suffix import MAX_MATCH, _ends_with, longest_suffix, run_lengths_long

REPO = Path(__file__).resolve().parents[1]
DATA = Path("/dev/shm/engramm/v5")
D2_CONTEXTS = 4096


@numba.njit(cache=True)
def _d2_row(out, r, p_uni, ptrs2, totals2, n1s2, n2s2, n3s2, ws2, as2, disc, g1):
    tot = float(totals2[r])
    gam = (g1[2] * n1s2[r] + disc[2, 1] * n2s2[r] + disc[2, 2] * n3s2[r]) / tot
    for v in range(len(out)):
        out[v] = gam * p_uni[v]
    d1, d2, d3 = disc[2, 0], disc[2, 1], disc[2, 2]
    for k in range(ptrs2[r], ptrs2[r + 1]):
        a = as2[k]
        disc_a = d1 if a == 1 else (d2 if a == 2 else d3)
        num = a - disc_a
        if num > 0.0:
            out[ws2[k]] += num / tot


@numba.njit(cache=True, parallel=True)
def _build_d2(rows, p_uni, ptrs2, totals2, n1s2, n2s2, n3s2, ws2, as2, disc, g1):
    out = np.empty((len(rows), len(p_uni)), dtype=np.float32)
    for j in numba.prange(len(rows)):
        buf = np.empty(len(p_uni))
        _d2_row(buf, rows[j], p_uni, ptrs2, totals2, n1s2, n2s2, n3s2, ws2, as2, disc, g1)
        for v in range(len(p_uni)):
            out[j, v] = buf[v]
    return out


@numba.njit(cache=True)
def _kn_into(dist, h, hl, n_orders, p_uni, ctxs, ptrs, totals, n1s, n2s, n3s, ws, as_, disc, g1, scale,
             d2_slot, d2):
    """dist[:] = scale · KN5(· | h) (same recursion as engramm/lm/ngram._full_dist); the one
    dense pass assigns, so ``dist`` needs no clearing. Returns the highest order found."""
    rs = np.full(n_orders + 1, -1, dtype=np.int64)
    gam = np.ones(n_orders + 1)
    found = 1
    for n in range(2, n_orders + 1):
        m = n - 1
        if hl < m:
            break
        key = np.uint64(0)
        for j in range(hl - m, hl):
            key = (key << np.uint64(15)) | np.uint64(h[j])
        r = _find_ctx(ctxs[n], key)
        if r < 0:
            continue
        rs[n] = r
        found = n
        tot = float(totals[n][r])
        gam[n] = (g1[n] * n1s[n][r] + disc[n, 1] * n2s[n][r] + disc[n, 2] * n3s[n][r]) / tot
    # order n's own mass is scaled by the gammas of all higher found orders
    mult = np.ones(n_orders + 1)
    running = 1.0
    for n in range(n_orders, 1, -1):
        mult[n] = running
        if rs[n] >= 0:
            running *= gam[n]
    lo_order = 2
    slot = -1
    if rs[2] >= 0:
        slot = d2_slot[h[hl - 1]]
    if slot >= 0:
        f = scale * mult[2]                      # D2 already holds γ₂·p_uni + c₂
        row = d2[slot]
        for v in range(len(dist)):
            dist[v] = f * row[v]
        lo_order = 3
    else:
        base = scale * running
        for v in range(len(dist)):
            dist[v] = base * p_uni[v]
    for n in range(lo_order, n_orders + 1):
        r = rs[n]
        if r < 0:
            continue
        tot = float(totals[n][r])
        d1, d2_, d3 = disc[n, 0], disc[n, 1], disc[n, 2]
        f = scale * mult[n] / tot
        aa, wa = as_[n], ws[n]                   # hoisted: typed-list indexing in the loop is slow
        for k in range(ptrs[n][r], ptrs[n][r + 1]):
            a = aa[k]
            disc_a = d1 if a == 1 else (d2_ if a == 2 else d3)
            num = a - disc_a
            if num > 0.0:
                dist[wa[k]] += num * f
    return found


@numba.njit(cache=True)
def _inf_into(dist, tokens_c, sa, lo, hi, k, weight, total):
    """dist[v] += weight · count(h′ v) / total over the suffix range (group jumps)."""
    a = lo
    n = len(tokens_c)
    while a < hi:
        p = sa[a] + k
        if p >= n:
            a += 1
            continue
        v = tokens_c[p]
        b, e = a, hi
        while b < e:
            mid = (b + e) >> 1
            pp = sa[mid] + k
            vv = tokens_c[pp] if pp < n else -1
            if vv <= v:
                b = mid + 1
            else:
                e = mid
        dist[v] += weight * (b - a) / total
        a = b


@numba.njit(cache=True, parallel=True)
def _q_windows(ev, doc_of, doc_start, win, T, out, tokens_c, sa, w_kn, w_inf, w_cache, kmax,
               run_kn, run_inf, d2_slot, d2, n_orders, p_uni, ctxs, ptrs, totals, n1s, n2s, n3s, ws, as_,
               disc, g1):
    """out[b, t, :] = q(· | history of target win[b] + 1 + t) for every window b.

    ``doc_of[i]`` = document of target i, ``doc_start[d]`` = its first token; the cache
    history of target i is ev[doc_start : i]. Returns q(target) per (b, t)."""
    B = len(win)
    V = len(p_uni)
    q_tgt = np.zeros((B, T))
    for b in numba.prange(B):
        counts = np.zeros(V, dtype=np.int32)
        distinct = np.empty(T + 4096, dtype=np.int64)
        nd = 0
        first = win[b] + 1
        d_cur = doc_of[first]
        s = doc_start[d_cur]
        # cache history before the window (bounded: only the last 4096 tokens of the document
        # would not be exact, so count all of them)
        hist_start = s
        for j in range(hist_start, first):
            t = ev[j]
            if counts[t] == 0:
                if nd >= len(distinct):
                    nd2 = np.empty(len(distinct) * 2, dtype=np.int64)
                    nd2[:nd] = distinct[:nd]
                    distinct = nd2
                distinct[nd] = t
                nd += 1
            counts[t] += 1
        for t_ in range(T):
            i = first + t_
            d = doc_of[i]
            if d != d_cur:                      # new document: empty cache
                for j in range(nd):
                    counts[distinct[j]] = 0
                nd = 0
                d_cur = d
                s = doc_start[d]
            n_hist = i - s
            hl_i = min(int(run_inf[i]) + 1, i, kmax)
            h_i = ev[i - hl_i:i]
            k, lo, hi = longest_suffix(tokens_c, sa, h_i, hl_i, kmax)
            cnt = 0
            if k > 0:
                cnt = hi - lo
                if _ends_with(tokens_c, h_i, hl_i, k):
                    cnt -= 1
            kn_w = w_kn + (w_inf if cnt == 0 else 0.0) + (w_cache if n_hist == 0 else 0.0)
            dist = out[b, t_]                   # float32 row, written in place
            hl = min(int(run_kn[i]) + 1, n_orders - 1)
            if hl > i:
                hl = i
            _kn_into(dist, ev[i - hl:i], hl, n_orders, p_uni, ctxs, ptrs, totals, n1s, n2s, n3s, ws, as_,
                     disc, g1, kn_w, d2_slot, d2)
            if cnt > 0:
                _inf_into(dist, tokens_c, sa, lo, hi, k, w_inf, float(cnt))
            if n_hist > 0:
                f = w_cache / n_hist
                for j in range(nd):
                    tt = distinct[j]
                    dist[tt] += f * counts[tt]
            q_tgt[b, t_] = dist[ev[i]]
            tt = ev[i]
            if counts[tt] == 0:
                if nd >= len(distinct):
                    nd2 = np.empty(len(distinct) * 2, dtype=np.int64)
                    nd2[:nd] = distinct[:nd]
                    distinct = nd2
                distinct[nd] = tt
                nd += 1
            counts[tt] += 1
    return q_tgt


@dataclass
class Counter:
    """Full-distribution counting model over one token stream (pilot model, never trained
    on the stream). Call ``q(win, T, out)`` for windows of targets win[b]+1 … win[b]+T."""

    ev: np.ndarray
    doc_of: np.ndarray
    doc_start: np.ndarray
    run_kn: np.ndarray
    run_inf: np.ndarray
    weights: np.ndarray
    kn_args: tuple
    tokens_c: np.ndarray
    sa: np.ndarray
    d2_slot: np.ndarray
    d2: np.ndarray

    @classmethod
    def build(cls, ev: np.ndarray, doc_starts: np.ndarray, weights: np.ndarray, kn: KNModel,
              tokens_c: np.ndarray, sa: np.ndarray, d2_slot: np.ndarray, d2: np.ndarray) -> Counter:
        ev = np.ascontiguousarray(ev, dtype=np.uint16)
        starts = np.asarray(doc_starts, dtype=np.int64)
        doc_of = np.searchsorted(starts, np.arange(len(ev)), side="right") - 1
        doc_of = np.maximum(doc_of, 0).astype(np.int64)    # position 0 (opening EOS) is never a target
        return cls(ev, doc_of, starts, run_lengths(ev), run_lengths_long(ev, MAX_MATCH),
                   np.asarray(weights, dtype=np.float64), kn._args(), tokens_c, sa, d2_slot, d2)

    def for_stream(self, ev: np.ndarray, doc_starts: np.ndarray) -> Counter:
        """The same counting model over another token stream (shares the big tables)."""
        ev = np.ascontiguousarray(ev, dtype=np.uint16)
        starts = np.asarray(doc_starts, dtype=np.int64)
        doc_of = np.maximum(np.searchsorted(starts, np.arange(len(ev)), side="right") - 1, 0).astype(np.int64)
        return Counter(ev, doc_of, starts, run_lengths(ev), run_lengths_long(ev, MAX_MATCH), self.weights,
                       self.kn_args, self.tokens_c, self.sa, self.d2_slot, self.d2)

    def q(self, win: np.ndarray, T: int, out: np.ndarray) -> np.ndarray:
        w = self.weights
        return _q_windows(self.ev, self.doc_of, self.doc_start, np.asarray(win, dtype=np.int64), T, out,
                          self.tokens_c, self.sa, float(w[0]), float(w[1]), float(w[2]), MAX_MATCH,
                          self.run_kn, self.run_inf, self.d2_slot, self.d2, *self.kn_args)


def load_d2(kn: KNModel, m: int = D2_CONTEXTS) -> tuple[np.ndarray, np.ndarray]:
    """(slot per token, dense D2 rows) for the m most frequent order-2 contexts; cached in DATA."""
    path = DATA / f"d2_{m}.npy"
    slot_path = DATA / f"d2_{m}_slot.npy"
    a = kn._args()
    ctxs, ptrs, totals, n1s, n2s, n3s, ws, as_, disc, g1 = a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9], a[10], a[11]
    if path.exists() and slot_path.exists():
        return np.load(slot_path), np.load(path)          # in RAM: mmap page faults cost 5× per position
    rows = np.argsort(-totals[2].astype(np.int64), kind="stable")[:m].astype(np.int64)
    d2 = _build_d2(rows, kn.p_uni, ptrs[2], totals[2], n1s[2], n2s[2], n3s[2], ws[2], as_[2], disc, g1)
    slot = np.full(kn.vocab_size, -1, dtype=np.int64)
    ctx_tok = (ctxs[2][rows] & np.uint64(0x7FFF)).astype(np.int64)    # order-2 key = the one context token
    slot[ctx_tok] = np.arange(len(rows))
    DATA.mkdir(parents=True, exist_ok=True)
    np.save(path, d2)
    np.save(slot_path, slot)
    return slot, np.asarray(d2)


def load_counter(where: str, base: Counter | None = None) -> Counter:
    """Counter over 'region' (training stream of v5_prior) or an evaluation split; with
    ``base`` the tables of an existing counter are reused."""
    if base is not None:
        from experiments.lm_common import load_split
        if where == "region":
            ev = np.load(DATA / "region_tokens.npy")
            return base.for_stream(ev, np.flatnonzero(ev[:-1] == 0) + 1)
        sp = load_split(where)
        return base.for_stream(np.asarray(sp.tokens), np.asarray(sp.doc_starts, dtype=np.int64))
    from experiments.lm_common import load_split, load_train
    from experiments.lm_components import get_kn, get_sa

    w = np.array(json.loads((DATA / "prior_weights.json").read_text())["w"])
    pilot = load_train("pilot")
    kn = get_kn("pilot", pilot)
    tokens_c = np.ascontiguousarray(pilot.tokens, dtype=np.uint16)
    sa = get_sa("pilot", pilot)
    slot, d2 = load_d2(kn)
    if where == "region":
        ev = np.load(DATA / "region_tokens.npy")
        starts = np.flatnonzero(ev[:-1] == 0) + 1
    else:
        sp = load_split(where)
        ev = np.asarray(sp.tokens)
        starts = np.asarray(sp.doc_starts, dtype=np.int64)
    return Counter.build(ev, starts, w, kn, tokens_c, sa, slot, d2)


def check(n_win: int = 24, T: int = 256, threads: int = 2) -> int:
    """q(target) must equal the component prior; q must sum to 1; q must not look at the
    target or anything after it (causality); report speed at a fixed thread count."""
    numba.set_num_threads(threads)
    c = load_counter("val_a")
    d = REPO / "models" / "lm" / "pilot" / "eval"
    kz, iz, cz = np.load(d / "val_a_kn.npz"), np.load(d / "val_a_inf.npz"), np.load(d / "val_a_cache.npz")
    p_kn = kz["p"]
    cnt = iz["cnt"]
    p_inf = np.where(cnt > 0, iz["cnt_w"] / np.maximum(cnt, 1), p_kn)
    cc = cz["p"]
    p_c = np.where(cc >= 0, cc, p_kn)
    w = c.weights
    pp = w[0] * p_kn + w[1] * p_inf + w[2] * p_c                       # pp[i - 1] belongs to target i
    rng = np.random.default_rng(0)
    win = rng.integers(0, len(c.ev) - T - 1, size=n_win)
    out = np.empty((n_win, T, len(c.kn_args[1])), dtype=np.float32)
    c.q(win[:2], T, out[:2])                                           # compile
    t0 = time.time()
    q_t = c.q(win, T, out)
    secs = time.time() - t0
    ref = np.stack([pp[s:s + T] for s in win])                         # targets s+1 … s+T
    rel = np.abs(q_t - ref) / ref
    sums = out.sum(axis=2, dtype=np.float64)
    print(f"positions {n_win * T}: {secs / (n_win * T) * 1e6:.1f} µs/position ({numba.get_num_threads()} threads)")
    print(f"q(target) vs component prior: max rel err {rel.max():.2e}")
    print(f"Σ q over the vocabulary: min {sums.min():.6f}, max {sums.max():.6f}")
    # causality: change the token at target position s + 1 + t₀ (and everything after it);
    # rows of targets up to and including s + 1 + t₀ must stay bit-identical
    t0_ = T // 2
    ev2 = c.ev.copy()
    causal = True
    for b, s in enumerate(win[:6]):
        j = s + 1 + t0_
        ev2[j:j + T] = (ev2[j:j + T].astype(np.int64) * 7 + 13) % 32767 + 1   # no EOS introduced
    c2 = c.for_stream(ev2, c.doc_start)
    out2 = np.empty((6, T, out.shape[2]), dtype=np.float32)
    c2.q(win[:6], T, out2)
    for b in range(6):
        if not np.array_equal(out[b, :t0_ + 1], out2[b, :t0_ + 1]):
            causal = False
        if np.array_equal(out[b, t0_ + 1:], out2[b, t0_ + 1:]):
            causal = False                                             # the change must matter later
    print(f"causality (rows up to the changed target unchanged, later rows changed): {causal}")
    ok = rel.max() < 1e-5 and abs(sums.min() - 1) < 1e-3 and abs(sums.max() - 1) < 1e-3 and causal
    print("OK" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        raise SystemExit(check())
    raise SystemExit(__doc__)
