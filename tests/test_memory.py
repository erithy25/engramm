"""Tests for the full pipeline: episodic memory, fusion, T1/T2/T3, L2 replay."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from engramm.core import ItemMemory
from engramm.memory import (
    Engramm,
    EpisodicMemory,
    FusionConfig,
    episode_id,
    utility_weight,
)
from engramm.metrics import hamming
from engramm.persistence import EventLog, read_events, replay

D = 512


def _noisy(rng: np.random.Generator, base: np.ndarray, flip: float) -> np.ndarray:
    bits = np.unpackbits(base)
    mask = rng.random(bits.size) < flip
    return np.packbits(bits ^ mask.astype(np.uint8))


def _toy(seed: int = 0, n_classes: int = 5, per_class: int = 20, flip: float = 0.3):
    """Noisy copies of random class centres, plus held-out queries."""
    rng = np.random.default_rng(seed)
    memory = ItemMemory(seed, D)
    centres = memory.vectors([f"centre{c}" for c in range(n_classes)])
    train = np.stack([_noisy(rng, centres[c], flip)
                      for c in range(n_classes) for _ in range(per_class)])
    labels = [f"c{c}" for c in range(n_classes) for _ in range(per_class)]
    test = np.stack([_noisy(rng, centres[c], flip)
                     for c in range(n_classes) for _ in range(10)])
    test_labels = [f"c{c}" for c in range(n_classes) for _ in range(10)]
    return train, labels, test, test_labels


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cache_bytes", [0, 1 << 30])
def test_distances_are_exact_hamming(cache_bytes: int) -> None:
    train, labels, test, _ = _toy()
    memory = EpisodicMemory(D, cache_bytes=cache_bytes)
    memory.add(train, np.zeros(len(train), dtype=np.int32),
               np.arange(len(train), dtype=np.uint64))
    reference = hamming(test[:, None, :], train[None, :, :])
    assert np.array_equal(memory.distances(test), reference)


def test_topk_matches_an_independent_sort_by_distance_then_id() -> None:
    train, labels, test, _ = _toy(per_class=40)
    # Duplicate a block so exact distance ties are guaranteed.
    train = np.concatenate([train, train[:30]])
    labels = labels + labels[:30]
    memory = EpisodicMemory(D)
    ids = np.array([episode_id(l, k) for l, k in zip(labels, train)], dtype=np.uint64)
    memory.add(train, np.zeros(len(train), dtype=np.int32), ids)
    positions, dists = memory.topk(test, k=17)

    reference = hamming(test[:, None, :], train[None, :, :])
    rank = memory.id_rank()
    for row in range(test.shape[0]):
        expected = sorted(range(len(train)), key=lambda j: (reference[row, j], rank[j]))[:17]
        assert positions[row].tolist() == expected
        assert dists[row].tolist() == [int(reference[row, j]) for j in expected]


def test_leave_one_out_never_returns_the_excluded_episode() -> None:
    train, labels, _, _ = _toy()
    memory = EpisodicMemory(D)
    memory.add(train, np.zeros(len(train), dtype=np.int32),
               np.arange(len(train), dtype=np.uint64))
    positions, dists = memory.topk(train, k=5, exclude=np.arange(len(train)))
    assert not np.any(positions == np.arange(len(train))[:, None])
    assert dists.min() > 0, "an example found itself at distance 0"


# ---------------------------------------------------------------------------
# Fusion and T1
# ---------------------------------------------------------------------------

def test_without_episode_weight_fusion_is_the_prototype_classifier() -> None:
    train, labels, test, _ = _toy()
    model = Engramm(D, seed=1, config=FusionConfig(lambda_e=0.0))
    model.learn(train, labels)
    assert np.array_equal(model.scores(test), model.prototypes.score(test))


def test_full_pipeline_learns_the_toy_problem() -> None:
    train, labels, test, test_labels = _toy()
    model = Engramm(D, seed=1)
    model.learn(train, labels)
    predicted = model.predict_labels(test)
    accuracy = np.mean([p == t for p, t in zip(predicted, test_labels)])
    assert accuracy >= 0.9


def test_utility_weight_spans_zero_to_two() -> None:
    assert utility_weight(np.array([-8, 0, 8]), 8).tolist() == [0.0, 1.0, 2.0]


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_learned_state_and_readout_do_not_depend_on_order(seed: int) -> None:
    """T1 in any order and any batching gives the same state and answers.

    State: a sum and a multiset, so this is expected. Readout: the recovered
    implementation broke equal-distance ties by array position, so its
    answers moved under reordering although its state did not (W19). With
    the content-id tie-break they must not.
    """
    train, labels, test, _ = _toy(seed=seed, flip=0.42)   # many near-ties
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(labels))

    a = Engramm(D, seed=7)
    a.learn(train, labels)

    b = Engramm(D, seed=7)
    for chunk in np.array_split(order, 7):          # different order, batched
        b.learn(train[chunk], [labels[i] for i in chunk])

    assert a.state_digest() == b.state_digest()
    assert a.predict_labels(test) == b.predict_labels(test)


# ---------------------------------------------------------------------------
# T2
# ---------------------------------------------------------------------------

def test_refinement_reduces_training_error() -> None:
    train, labels, _, _ = _toy(flip=0.4)
    model = Engramm(D, seed=3, config=FusionConfig(lambda_e=0.0))
    model.learn(train, labels)
    errors = model.refine(train, labels, epochs=4, rng=np.random.default_rng(0))
    assert len(errors) == 4
    assert errors[-1] <= errors[0]


@pytest.mark.parametrize("local", [False, True])
def test_a_miss_moves_the_right_prototypes(local: bool) -> None:
    """On a miss: true class +x always; predicted class -x only without t2_local."""
    train, labels, _, _ = _toy(flip=0.45)
    model = Engramm(D, seed=3, config=FusionConfig(lambda_e=0.0, t2_local=local))
    model.learn(train, labels)
    before = model.prototypes.A.astype(np.int32).copy()
    key = train[0]
    signed = np.unpackbits(key).astype(np.int32) * 2 - 1
    model._apply_refine(None, None, true_class=0, predicted=1, key=key)
    after = model.prototypes.A.astype(np.int32)
    assert np.array_equal(after[0] - before[0], signed)
    expected_1 = before[1] if local else before[1] - signed
    assert np.array_equal(after[1], expected_1)
    assert np.array_equal(after[2:], before[2:])


def test_refinement_updates_utilities_leave_one_out() -> None:
    train, labels, _, _ = _toy()
    model = Engramm(D, seed=3)
    positions = model.learn(train, labels)
    model.refine(train, labels, epochs=1, rng=np.random.default_rng(0),
                 episode_positions=positions)
    assert model.episodes.util.max() > 0
    assert int(np.abs(model.episodes.util).max()) <= model.config.util_clip


# ---------------------------------------------------------------------------
# T3
# ---------------------------------------------------------------------------

def test_absorption_removes_typical_episodes_and_leaves_accumulators() -> None:
    train, labels, _, _ = _toy(flip=0.1)
    model = Engramm(D, seed=3)
    model.learn(train, labels)
    accumulators = model.prototypes.A.copy()
    absorbed = model.consolidate(theta_merge=0.12, util_max=2)
    assert absorbed > 0 and len(model.episodes) == len(labels) - absorbed
    assert np.array_equal(model.prototypes.A, accumulators), "absorption double-counted"


def test_eviction_takes_the_lowest_utility_first() -> None:
    train, labels, _, _ = _toy()
    model = Engramm(D, seed=3)
    model.learn(train, labels)
    model.episodes.util[:] = np.arange(len(labels)) % 7 - 3
    lowest = set(model.episodes.ids[model.episodes.util == -3].tolist())
    removed = model.evict(len(lowest))
    assert set(removed.tolist()) == lowest


# ---------------------------------------------------------------------------
# L2 replay
# ---------------------------------------------------------------------------

def _logged_run(path: Path) -> Engramm:
    train, labels, _, _ = _toy(flip=0.35)
    log = EventLog(path)
    model = Engramm(D, seed=5, config=FusionConfig(t2_local=False), log=log)
    positions = model.learn(train[:60], labels[:60])
    model.refine(train[:60], labels[:60], epochs=1, rng=np.random.default_rng(1),
                 episode_positions=positions)
    model.learn(train[60:], labels[60:])
    model.consolidate(theta_merge=0.05, util_max=2)
    model.evict(10)
    log.close()
    return model


def test_full_replay_reproduces_state_and_answers(tmp_path: Path) -> None:
    path = tmp_path / "l2.log"
    live = _logged_run(path)
    rebuilt, report = replay(path)
    assert not report.torn
    assert rebuilt.state_digest() == live.state_digest()
    _, _, test, _ = _toy(flip=0.35)
    assert rebuilt.predict_labels(test) == live.predict_labels(test)


@pytest.mark.parametrize("fraction", [0.13, 0.5, 0.6, 0.97])
def test_crash_replay_equals_the_state_after_the_last_complete_event(
        tmp_path: Path, fraction: float) -> None:
    path = tmp_path / "l2.log"
    _logged_run(path)
    data = path.read_bytes()
    cut = tmp_path / "cut.log"
    cut.write_bytes(data[:int(len(data) * fraction)])

    crashed, report = replay(cut)
    records, _, _ = read_events(cut)
    reference, _ = replay(path, limit=len(records))
    assert report.events_applied == len(records)
    assert crashed.state_digest() == reference.state_digest()


def test_a_corrupted_record_ends_replay_there(tmp_path: Path) -> None:
    path = tmp_path / "l2.log"
    _logged_run(path)
    records, _, _ = read_events(path)
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0xFF
    bad = tmp_path / "bad.log"
    bad.write_bytes(bytes(data))
    kept, _, discarded = read_events(bad)
    assert len(kept) < len(records) and discarded > 0
