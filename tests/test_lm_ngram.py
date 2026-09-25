"""Modified Kneser-Ney: against an independent dictionary implementation, and normalised."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pytest

from engramm.lm.ngram import KNModel, build_kn, discounts
from engramm.lm.tokenizer import EOS

V = 1 << 15


def _corpus(seed: int, n_docs: int = 60, vocab: int = 40) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = [EOS]
    zipf = 1.0 / np.arange(1, vocab + 1)
    zipf /= zipf.sum()
    for _ in range(n_docs):
        length = int(rng.integers(1, 30))
        # a little structure so higher orders repeat
        doc = rng.choice(np.arange(1, vocab + 1), size=length, p=zipf)
        if rng.random() < 0.3:
            doc = np.concatenate([[7, 8, 9, 10], doc])
        out.extend(int(x) for x in doc)
        out.append(EOS)
    return np.asarray(out, dtype=np.uint16)


def _valid(t, i, n):
    if i - n + 1 < 0:
        return False
    return all(t[j] != EOS for j in range(i - n + 2, i))


class RefKN:
    """Straightforward dictionary implementation of the same definition."""

    def __init__(self, t, N, prune_from):
        t = [int(x) for x in t]
        self.N, self.prune_from = N, prune_from
        raw = {n: defaultdict(int) for n in range(1, N + 1)}
        for i in range(1, len(t)):
            for n in range(1, N + 1):
                if _valid(t, i, n):
                    raw[n][tuple(t[i - n + 1:i + 1])] += 1
        adj = {N: dict(raw[N])}
        for n in range(N - 1, 0, -1):
            a = defaultdict(int)
            for g in adj[n + 1]:
                a[g[1:]] += 1
            for g, c in raw[n].items():
                if n >= 2 and g[0] == EOS:
                    a[g] = c
            adj[n] = dict(a)
        self.adj = adj
        self.D = {}
        self.stats = {}
        for n in range(1, N + 1):
            coc = [sum(1 for c in adj[n].values() if c == k) for k in (1, 2, 3, 4)]
            self.D[n] = discounts(np.array(coc))
            st = defaultdict(lambda: [0, 0, 0, 0])
            for g, c in adj[n].items():
                s = st[g[:-1]]
                s[0] += c
                s[1] += c == 1
                s[2] += c == 2
                s[3] += c >= 3
            self.stats[n] = dict(st)

    def prob(self, hist, w):
        hist = [int(x) for x in hist]
        p = None
        for n in range(1, self.N + 1):
            if n == 1:
                ctx = ()
            else:
                if len(hist) < n - 1:
                    break
                ctx = tuple(hist[len(hist) - (n - 1):])
            if ctx not in self.stats[n]:
                if n == 1:
                    raise AssertionError
                continue
            A, N1, N2, N3 = self.stats[n][ctx]
            a = self.adj[n].get(ctx + (w,), 0)
            pruned = n >= self.prune_from
            if pruned and a == 1:
                a = 0
            d1, d2, d3 = self.D[n]
            gamma = ((1.0 if pruned else d1) * N1 + d2 * N2 + d3 * N3) / A
            disc = 0.0 if a == 0 else (d1 if a == 1 else (d2 if a == 2 else d3))
            lower = 1.0 / V if n == 1 else p
            p = max(a - disc, 0.0) / A + gamma * lower
        return p


@pytest.mark.parametrize("order,prune_from", [(2, 99), (3, 99), (5, 99), (5, 3), (4, 2)])
def test_matches_reference(order, prune_from):
    t = _corpus(1)
    model = build_kn(t, order=order, prune_from=prune_from, chunk_budget=97)
    ref = RefKN(t, order, prune_from)
    probs, _ = model.stream_probs(t)
    for q, i in enumerate(range(1, len(t))):
        start = max(k for k in range(i) if t[k] == EOS)
        hist = t[max(start, i - (order - 1)):i]
        assert probs[q] == pytest.approx(ref.prob(hist, int(t[i])), rel=1e-12, abs=0)


@pytest.mark.parametrize("prune_from", [99, 3])
def test_distribution_sums_to_one_and_matches_prob(prune_from):
    t = _corpus(2)
    model = build_kn(t, order=5, prune_from=prune_from)
    rng = np.random.default_rng(0)
    for i in rng.integers(1, len(t), size=40):
        hist = t[:i]
        dist = model.distribution(hist)
        assert abs(dist.sum() - 1.0) < 1e-12
        for w in (int(t[i]), 7, 0, 12345):
            assert dist[w] == pytest.approx(model.prob(hist, w), rel=1e-12)


def test_chunking_and_order_do_not_change_the_model():
    t = _corpus(3, n_docs=200)
    a = build_kn(t, order=5, chunk_budget=50)
    b = build_kn(t, order=5, chunk_budget=10**9)
    assert a.digest() == b.digest()


def test_save_load_roundtrip(tmp_path):
    t = _corpus(4)
    m = build_kn(t, order=5)
    m.save(tmp_path / "kn")
    m2 = KNModel.load(tmp_path / "kn")
    assert m2.digest() == m.digest()
    p1, _ = m.stream_probs(t)
    p2, _ = m2.stream_probs(t)
    assert np.array_equal(p1, p2)


def test_history_does_not_cross_document_start():
    t = _corpus(5)
    m = build_kn(t, order=5)
    base = np.array([EOS, 3, 4], dtype=np.uint16)
    polluted = np.array([7, 8, 9, EOS, 3, 4], dtype=np.uint16)
    assert np.array_equal(m.distribution(base), m.distribution(polluted))


def test_rejects_bad_streams():
    with pytest.raises(ValueError):
        build_kn(np.array([5, 6, 0], dtype=np.uint16))
    with pytest.raises(ValueError):
        build_kn(np.array([0, 5, 0], dtype=np.uint16), order=1)
