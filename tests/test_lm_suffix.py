"""∞-gram suffix index against brute force."""

from __future__ import annotations

import numpy as np

from engramm.lm.suffix import SuffixIndex, build_suffix_array


def _stream(seed, n=3000, vocab=6):
    rng = np.random.default_rng(seed)
    t = rng.integers(1, vocab + 1, size=n).astype(np.uint16)
    t[rng.random(n) < 0.03] = 0
    t[0] = 0
    t[-1] = 0
    # large token ids exercise the high byte
    t[rng.random(n) < 0.05] = 40000
    return t


def _brute_count(t, pat):
    L = len(pat)
    return sum(1 for i in range(len(t) - L + 1) if np.array_equal(t[i:i + L], pat))


def test_suffix_array_is_sorted_token_order():
    t = _stream(0, 800)
    sa = build_suffix_array(t)
    assert sorted(sa.tolist()) == list(range(len(t)))
    suffixes = [tuple(t[i:].tolist()) for i in sa]
    assert suffixes == sorted(suffixes)


def test_counts_and_longest_match_match_brute_force():
    t = _stream(1)
    idx = SuffixIndex(t)
    rng = np.random.default_rng(5)
    for _ in range(200):
        L = int(rng.integers(1, 6))
        s = int(rng.integers(0, len(t) - L))
        pat = t[s:s + L] if rng.random() < 0.7 else rng.integers(1, 7, size=L).astype(np.uint16)
        assert idx.count(pat) == _brute_count(t, pat)
    ev = _stream(2, 400)
    ks, cnt, cntw = idx.stream_stats(ev, kmax=12)
    for q, i in enumerate(range(1, len(ev))):
        start = max(j for j in range(i) if ev[j] == 0)
        h = ev[start:i][-12:]
        best = 0
        for k in range(1, len(h) + 1):
            if _brute_count(t, h[len(h) - k:]) > 0:
                best = k
        assert ks[q] == best
        if best:
            hp = h[len(h) - best:]
            at_end = np.array_equal(t[len(t) - best:], hp)
            assert cnt[q] == _brute_count(t, hp) - at_end
            assert cntw[q] == _brute_count(t, np.append(hp, ev[i]).astype(np.uint16))


def test_next_counts_and_occurrences():
    t = _stream(3)
    idx = SuffixIndex(t)
    hist = t[100:104]
    k, counts = idx.next_counts(hist, vocab=1 << 16)
    assert k >= 1
    hp = hist[len(hist) - k:] if 0 not in hist else hist
    total = 0
    for w in np.flatnonzero(counts):
        c = _brute_count(t, np.append(hp, w).astype(np.uint16))
        assert counts[w] == c
        total += c
    # the only occurrence that has no next token is one at the very end
    assert total in (idx.count(hp), idx.count(hp) - 1)
    occ = idx.occurrences(t[10:13], limit=1000)
    assert 10 in occ.tolist()
    assert all(np.array_equal(t[o:o + 3], t[10:13]) for o in occ)


def test_overlap_windows():
    t = _stream(4)
    idx = SuffixIndex(t)
    ev = np.concatenate([[0], t[50:80], [0], np.full(20, 3, dtype=np.uint16), [0]]).astype(np.uint16)
    tot, hit = idx.overlap(ev, np.array([1, 32]), np.array([31, 52]), width=13)
    assert tot.tolist() == [18, 8]
    assert hit[0] == 18
