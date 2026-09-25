"""HDC parts of ENGRAMM-LM: codebooks, classes, KNN search, TOPIC, CACHE."""

from __future__ import annotations

import numpy as np
import pytest

from engramm.lm import knn as K
from engramm.lm.semantic import (D_S, WORDS, _cooc, _project, as_words, build_codebook, bundle_words,
                                 idf_weights, ppmi_levels, tiebreak_vector)
from engramm.lm.topic import cache_distribution, stream_cache, stream_topic, topic_distribution, topic_table


def _language(seed=0, n_docs=300):
    """Toy language: 'the ANIMAL eats FOOD .' / 'a COLOUR CAR drives .' with synonyms."""
    rng = np.random.default_rng(seed)
    animals, foods, colours, cars = [10, 11, 12], [20, 21, 22], [30, 31, 32], [40, 41]
    the, a, eats, drives, dot = 1, 2, 3, 4, 5
    out = [0]
    for _ in range(n_docs):
        for _ in range(int(rng.integers(2, 8))):
            if rng.random() < 0.5:
                out += [the, int(rng.choice(animals)), eats, int(rng.choice(foods)), dot]
            else:
                out += [a, int(rng.choice(colours)), int(rng.choice(cars)), drives, dot]
        out.append(0)
    return np.asarray(out, dtype=np.uint16)


@pytest.fixture(scope="module")
def lang():
    t = _language()
    cb = build_codebook(t, seed=42, vocab=64)
    return t, cb


def _ham(cb, a, b, kind="eng"):
    M = getattr(cb, kind)
    return int(sum(bin(int(x) ^ int(y)).count("1") for x, y in zip(M[a], M[b])))


def test_projection_is_exact_integer_arithmetic():
    rng = np.random.default_rng(1)
    L = rng.integers(0, 5, size=(50, 8192)).astype(np.int8)
    R = rng.choice([-1, 1], size=(8192, 64)).astype(np.int8)
    assert np.array_equal(_project(L, R, block=7), L.astype(np.int64) @ R.astype(np.int64))


def test_ppmi_levels_match_definition():
    rng = np.random.default_rng(2)
    C = rng.integers(0, 6, size=(12, 9)).astype(np.int32)
    L = ppmi_levels(C)
    N = C.sum()
    for w in range(12):
        for c in range(9):
            x = int(C[w, c])
            exp = 0 if x == 0 else sum(x * N > (2 ** k) * C[w].sum() * C[:, c].sum() for k in range(4))
            assert L[w, c] == exp


def test_cooccurrence_never_crosses_documents():
    t = np.array([0, 5, 6, 0, 7, 8, 0], dtype=np.uint16)
    cmap = np.arange(16, dtype=np.int64)
    C = _cooc(t, cmap, np.array([1, -1, 2], dtype=np.int64), 16, 16, 3)
    assert C[5, 6] == 1 and C[6, 5] == 1 and C[7, 8] == 1
    assert C[6, 7] == 0 and C[6, 8] == 0 and C[5, 7] == 0


def test_synonyms_are_closer_than_other_words(lang):
    t, cb = lang
    assert _ham(cb, 10, 11) < _ham(cb, 10, 30)
    assert _ham(cb, 20, 21) < _ham(cb, 20, 40)
    assert _ham(cb, 30, 31) < _ham(cb, 30, 3)
    assert cb.classes[0] == 0 and cb.classes[1:].min() >= 1


def test_codebook_is_deterministic_and_seeded(lang):
    t, cb = lang
    assert build_codebook(t, seed=42, vocab=64).digest() == cb.digest()
    assert build_codebook(t, seed=7, vocab=64).digest() != cb.digest()


def test_bundle_has_no_ties_and_matches_majority(lang):
    t, cb = lang
    toks = np.array([10, 11, 20, 3], dtype=np.uint16)
    idf = np.array([1] * 64, dtype=np.int32)
    tb = tiebreak_vector(42)
    out = bundle_words(cb.wide, idf, toks, tb, WORDS)
    bits = np.unpackbits(cb.wide[toks].astype(">u8").view(np.uint8), axis=-1).astype(int) * 2 - 1
    tbb = np.unpackbits(np.asarray([tb], dtype=">u8").view(np.uint8), axis=-1)[0].astype(int) * 2 - 1
    total = bits.sum(0) + tbb          # 4 terms → even → tie-break added
    assert (total != 0).all()
    got = np.unpackbits(np.asarray([out], dtype=">u8").view(np.uint8), axis=-1)[0]
    assert np.array_equal(got, (total > 0).astype(np.uint8))


def test_idf_weights():
    assert idf_weights(np.array([0, 1, 7, 1000]), 1000).tolist() == [9, 8, 6, 1]


def test_index_sorted_and_window_matches_brute_force(lang):
    t, cb = lang
    pos = K.build_index(t, cb.classes)
    keys = [int(K._key(t, cb.classes.astype(np.int16), int(p))) for p in pos]
    assert keys == sorted(keys)
    for a in range(len(keys) - 1):
        if keys[a] == keys[a + 1]:
            assert pos[a] < pos[a + 1]
    cls = cb.classes.astype(np.int16)
    rng = np.random.default_rng(3)
    for i in rng.integers(1, len(t), 30):
        qkey = int(K._key(t, cls, int(i)))
        lo, hi, depth = K.candidate_window(t, cls, pos, np.uint64(qkey))
        # brute force: deepest prefix with ≥ K_MIN matches
        for d in range(K.DEPTH, 0, -1):
            sh = K.CLASS_BITS * (K.DEPTH - d)
            n = sum(1 for k in keys if k >> sh == qkey >> sh)
            if n >= K.K_MIN or d == 1:
                break
        assert depth == d
        assert hi - lo == min(n, K.B_MAX)
        sh = K.CLASS_BITS * (K.DEPTH - d)
        assert all(keys[r] >> sh == qkey >> sh for r in range(lo, hi))


def test_stream_knn_equals_manual_kernel_and_distribution(lang):
    t, cb = lang
    cls = cb.classes.astype(np.int16)
    pos = K.build_index(t, cls)
    tb = tiebreak_vector(42)
    seg = K.segment_signatures(t, cb.wide, cb.idf, tb)
    ev = _language(seed=9, n_docs=5)
    positions = np.arange(1, len(ev), dtype=np.int64)
    qs = K.stream_query_sigs(ev, positions, cb.wide, cb.idf, tb, 16, K.SEG)
    tables = K.kernel_tables([64.0, 1024.0])
    empty = np.zeros(0, dtype=np.int64)
    probs, dmin, ncand = K.stream_knn(t, cls, pos, cb.eng, seg, ev, qs, tables, empty, empty,
                                      np.zeros(1, dtype=np.uint16), empty, np.zeros((1, 4), dtype=np.uint64),
                                      positions)
    for q in range(0, len(positions), 7):
        i = positions[q]
        qt = np.empty(K.DEPTH, dtype=np.int64)
        qkey = K._query_parts(ev, i, cls, qt)
        dist, nxt, src, _ = K.score_candidates(t, cls, pos, cb.eng, seg, qt, qkey, qs[q], empty, empty,
                                               np.zeros(1, dtype=np.uint16), empty,
                                               np.zeros((1, 4), dtype=np.uint64))
        assert dmin[q] == dist.min()
        # manual distance of the first candidate
        p = int(src[0])
        ct = np.empty(K.DEPTH, dtype=np.int64)
        K._ctx_tokens(t, p, ct)
        man = sum(int(K.POS_WEIGHTS[j]) * (_ham(cb, int(qt[j]), int(ct[j])) if qt[j] != ct[j] else 0)
                  for j in range(K.DEPTH))
        man += K.TOPIC_V * 8 * sum(bin(int(a) ^ int(b)).count("1") for a, b in zip(qs[q], seg[p // K.SEG]))
        assert dist[0] == man
        w = np.exp(-(dist - dist.min()) / 64.0)
        assert probs[q, 0] == pytest.approx(w[nxt == ev[i]].sum() / w.sum(), rel=1e-12)
        full = K.knn_distribution(dist, nxt, tables[0], 64)
        assert full[ev[i]] == pytest.approx(probs[q, 0], rel=1e-12)
        assert full.sum() == pytest.approx(1.0, abs=1e-12)


def test_tombstones_and_user_positions(lang):
    t, cb = lang
    cls = cb.classes.astype(np.int16)
    pos = K.build_index(t, cls)
    seg = K.segment_signatures(t, cb.wide, cb.idf, tiebreak_vector(42))
    qt = np.zeros(K.DEPTH, dtype=np.int64)
    qt[:2] = [3, 10]
    qkey = K._key(np.array([0, 10, 3, 0], dtype=np.uint16), cls, 3)
    qsig = np.zeros(4, dtype=np.uint64)
    empty = np.zeros(0, dtype=np.int64)
    u = np.array([0, 1, 10, 3, 22, 5, 0], dtype=np.uint16)
    useg = K.segment_signatures(u, cb.wide, cb.idf, tiebreak_vector(42))
    d0, n0, s0, _ = K.score_candidates(t, cls, pos, cb.eng, seg, qt, qkey, qsig, empty, empty, u, empty, useg)
    tomb_lo, tomb_hi = np.array([0], dtype=np.int64), np.array([len(t)], dtype=np.int64)
    d1, n1, s1, _ = K.score_candidates(t, cls, pos, cb.eng, seg, qt, qkey, qsig, tomb_lo, tomb_hi, u,
                                       np.array([4], dtype=np.int64), useg)
    assert len(d0) > 0 and len(d1) == 1 and s1[0] == -5 and n1[0] == 22


def test_topic_and_cache_streams_match_single_queries(lang):
    t, cb = lang
    ev = _language(seed=4, n_docs=3)
    starts = np.flatnonzero(ev[:-1] == 0) + 1
    ends = np.flatnonzero(ev[1:] == 0) + 1
    p_uni = np.full(64, 1 / 64)
    tb = tiebreak_vector(42)
    tabs = np.stack([topic_table(4.0), topic_table(8.0)])
    tp = stream_topic(ev, starts, ends, cb.wide, cb.idf, tb, p_uni, tabs)
    cp = stream_cache(ev, starts, ends, 64)
    for i in range(1, len(ev)):
        d = topic_distribution(ev[:i], cb.wide, cb.idf, tb, p_uni, tabs[1])
        if d is None:
            assert tp[i, 1] == -1.0
        else:
            assert d.sum() == pytest.approx(1.0)
            assert tp[i, 1] == pytest.approx(d[ev[i]], rel=1e-12)
        c = cache_distribution(ev[:i], 64)
        if c is None:
            assert cp[i] == -1.0
        else:
            assert cp[i] == pytest.approx(c[ev[i]], rel=1e-15)


def test_as_words_bit_order():
    packed = np.zeros((1, D_S // 8), dtype=np.uint8)
    packed[0, 0] = 0x80
    w = as_words(packed)
    assert w[0, 0] == np.uint64(1) << np.uint64(63)
