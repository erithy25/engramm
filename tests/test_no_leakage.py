"""Leakage and determinism guarantees for the data pipeline.

Five properties, each enforced rather than assumed:

1. Everything fitted from data is fitted from the training split alone.
2. Train and test indices are disjoint, and content overlap is measured.
3. The same seed gives the same result in two fresh processes.
4. The result does not depend on ``PYTHONHASHSEED``.
5. The result matches a reference recorded on another platform.

Most tests run on a small synthetic dataset so the suite stays fast. Tests
that need the real archives are marked ``integration`` and skip when the
cache is not populated, rather than downloading 62 MB during a test run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from data.loaders import (
    CACHE_DIR,
    WILI_KNOWN_TRAIN_TEST_OVERLAP,
    WILI_N_CLASSES,
    WILI_PER_CLASS,
    Dataset,
    build_trigram_vocabulary,
    document_frequency,
    fit_train_artifacts,
    load_mnist,
    load_wili,
    pooled_trigram_vocabulary,
    split_overlap,
    vocabulary_contribution,
    with_replaced_test_split,
)
from engramm.repro import set_all_seeds
from tests.leakage_probe import REFERENCE_PATH, platform_tag, probe, probe_hash

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED = 42

_CACHE_READY = (CACHE_DIR / "wili-2018.zip").exists() and \
               (CACHE_DIR / "train-images-idx3-ubyte.gz").exists()

integration = pytest.mark.skipif(
    not _CACHE_READY,
    reason="dataset cache not populated — run "
           "'python -m tests.leakage_probe --allow-download' once",
)


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

def _synthetic_text_dataset(n_classes: int = 6, per_class: int = 5) -> Dataset:
    """A small text dataset with class-specific character statistics."""
    alphabets = ["abcde", "fghij", "klmno", "pqrst", "uvwxy", "zabcd"]
    rng = np.random.default_rng(SEED)
    x_train, y_train, x_test, y_test = [], [], [], []
    for class_index in range(n_classes):
        letters = alphabets[class_index % len(alphabets)]
        for split, xs, ys in (("tr", x_train, y_train), ("te", x_test, y_test)):
            for item in range(per_class):
                text = "".join(rng.choice(list(letters), size=60))
                xs.append(f"{split}{item}{text}")
                ys.append(class_index)
    return Dataset(
        name="synthetic",
        x_train=tuple(x_train), y_train=np.array(y_train, dtype=np.int64),
        x_test=tuple(x_test), y_test=np.array(y_test, dtype=np.int64),
        labels=tuple(f"class{i}" for i in range(n_classes)),
        metadata={"official_split": True, "shots": None},
    )


class _Exploding:
    """Any access raises. Used to prove the test split is never touched."""

    _MESSAGE = "the test split was accessed while fitting training artifacts"

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"{self._MESSAGE} (attribute {name!r})")

    def __len__(self) -> int:
        raise AssertionError(f"{self._MESSAGE} (len)")

    def __iter__(self) -> Any:
        raise AssertionError(f"{self._MESSAGE} (iteration)")

    def __getitem__(self, key: Any) -> Any:
        raise AssertionError(f"{self._MESSAGE} (indexing)")


# ---------------------------------------------------------------------------
# 1. Fitting uses the training split only
# ---------------------------------------------------------------------------

def test_fitting_never_touches_the_test_split() -> None:
    """Strongest form: any access to the test split raises immediately.

    Poisoning (below) proves the fitted values do not depend on test data.
    This proves the test data is not read at all — which also rules out
    subtler couplings, like fitting on a concatenation and then discarding.
    """
    dataset = _synthetic_text_dataset()
    booby_trapped = replace(dataset, x_test=_Exploding(), y_test=_Exploding())
    fit_train_artifacts(booby_trapped, vocabulary_size=50)


def test_mnist_fitting_never_touches_the_test_split() -> None:
    rng = np.random.default_rng(SEED)
    dataset = Dataset(
        name="mnist",
        x_train=rng.integers(0, 256, size=(40, 784), dtype=np.uint8),
        y_train=np.arange(40, dtype=np.int64) % 10,
        x_test=_Exploding(), y_test=_Exploding(),
        labels=tuple(str(d) for d in range(10)),
    )
    fit_train_artifacts(dataset)


@pytest.mark.parametrize("poison", ["garbage", "empty", "duplicated", "shuffled_labels"])
def test_artifacts_are_unchanged_by_any_test_split(poison: str) -> None:
    """Refit with the test split replaced; artifacts must be bit-identical."""
    dataset = _synthetic_text_dataset()
    reference = fit_train_artifacts(dataset, vocabulary_size=50)

    size = len(dataset.x_test)
    if poison == "garbage":
        x_test: tuple[str, ...] = tuple("ZZZQQQ" * 20 for _ in range(size))
        y_test = np.zeros(size, dtype=np.int64)
    elif poison == "empty":
        x_test, y_test = (), np.array([], dtype=np.int64)
    elif poison == "duplicated":
        x_test = tuple(dataset.x_train) * 3
        y_test = np.tile(dataset.y_train, 3)
    else:
        x_test = tuple(dataset.x_test)
        y_test = dataset.y_test[::-1].copy()

    poisoned = with_replaced_test_split(dataset, x_test, y_test)
    assert fit_train_artifacts(poisoned, vocabulary_size=50).digest() == reference.digest()


def test_vocabulary_contains_only_training_trigrams() -> None:
    """A trigram that occurs only in test may never enter the vocabulary."""
    dataset = _synthetic_text_dataset()
    marker = "§§§"
    poisoned = with_replaced_test_split(
        dataset,
        tuple(marker * 40 for _ in dataset.x_test),
        dataset.y_test,
    )
    vocabulary = fit_train_artifacts(poisoned, vocabulary_size=50).vocabulary
    assert marker not in vocabulary
    training_trigrams = {t[i:i + 3] for t in dataset.x_train
                         for i in range(len(t) - 2)}
    assert set(vocabulary) <= training_trigrams


def test_document_frequency_counts_training_texts_only() -> None:
    dataset = _synthetic_text_dataset()
    artifacts = fit_train_artifacts(dataset, vocabulary_size=50)
    assert len(artifacts.document_frequency) == len(artifacts.vocabulary)
    assert max(artifacts.document_frequency) <= len(dataset.x_train)


def test_item_memory_is_independent_of_all_data() -> None:
    """The item memory cannot leak: it never sees a corpus at all.

    A symbol's hypervector is derived from the symbol and the seed. Two
    memories built while completely different datasets are in play agree
    exactly, so no split can influence it.
    """
    from engramm import ItemMemory

    first = ItemMemory(SEED, 1024)
    second = ItemMemory(SEED, 1024)
    for symbol in ("abc", "xyz", "éèê"):
        assert np.array_equal(first.vector(symbol), second.vector(symbol))


def test_pixel_statistics_come_from_training_images_only() -> None:
    rng = np.random.default_rng(SEED)
    x_train = rng.integers(0, 256, size=(50, 784), dtype=np.uint8)
    dataset = Dataset(
        name="mnist", x_train=x_train,
        y_train=np.arange(50, dtype=np.int64) % 10,
        x_test=np.zeros((7, 784), dtype=np.uint8),
        y_test=np.zeros(7, dtype=np.int64),
        labels=tuple(str(d) for d in range(10)),
    )
    artifacts = fit_train_artifacts(dataset)
    assert np.allclose(artifacts.pixel_mean, x_train.astype(np.float64).mean(axis=0))
    assert np.allclose(artifacts.pixel_std, x_train.astype(np.float64).std(axis=0))


# ---------------------------------------------------------------------------
# 2. Split disjointness
# ---------------------------------------------------------------------------

def test_shot_selection_stays_inside_the_training_split() -> None:
    """Few-shot indices are drawn from train, and never reach into test."""
    dataset = _synthetic_text_dataset(n_classes=4, per_class=6)
    from data.loaders import _select_shots

    selected = _select_shots(dataset.y_train, 3, dataset.n_classes,
                             np.random.default_rng(SEED))
    assert selected.size == 3 * dataset.n_classes
    assert len(set(selected.tolist())) == selected.size
    assert selected.min() >= 0 and selected.max() < dataset.n_train
    counts = np.bincount(dataset.y_train[selected], minlength=dataset.n_classes)
    assert np.all(counts == 3)


def test_shots_are_taken_from_the_split_they_were_selected_from() -> None:
    """Correct indices into the wrong sequence would be an invisible leak.

    Selecting valid training indices and then indexing the *test* split
    yields the right shapes, the right class counts and the right metadata
    — everything the other tests check — while silently training on test
    data. So the pairing itself is verified: every returned
    ``(text, label)`` must occur in the input split as that same pair.
    """
    from data.loaders import apply_shots

    dataset = _synthetic_text_dataset(n_classes=4, per_class=6)
    x_few, y_few = apply_shots(dataset.x_train, dataset.y_train, 3,
                               dataset.n_classes, np.random.default_rng(SEED))

    train_pairs = set(zip(dataset.x_train, dataset.y_train.tolist()))
    assert set(zip(x_few, y_few.tolist())) <= train_pairs
    assert len(x_few) == len(y_few) == 3 * dataset.n_classes

    # The failure this guards against, made concrete: same indices, wrong source.
    test_pairs = set(zip(dataset.x_test, dataset.y_test.tolist()))
    assert not (set(zip(x_few, y_few.tolist())) & test_pairs)


def test_shot_selection_is_seed_determined() -> None:
    from data.loaders import _select_shots

    y = np.repeat(np.arange(5), 20)
    same_a = _select_shots(y, 4, 5, np.random.default_rng(SEED))
    same_b = _select_shots(y, 4, 5, np.random.default_rng(SEED))
    different = _select_shots(y, 4, 5, np.random.default_rng(SEED + 1))
    assert np.array_equal(same_a, same_b)
    assert not np.array_equal(same_a, different)


def test_synthetic_splits_share_no_content() -> None:
    dataset = _synthetic_text_dataset()
    assert split_overlap(dataset.x_train, dataset.x_test)["overlapping_texts"] == 0


@integration
def test_mnist_uses_the_official_split_untouched() -> None:
    dataset = load_mnist(allow_download=False)
    assert dataset.n_train == 60_000 and dataset.n_test == 10_000
    assert dataset.metadata["official_split"] is True
    assert dataset.metadata["shots"] is None
    assert dataset.labels == tuple(str(d) for d in range(10))


@integration
def test_wili_uses_the_official_split_with_all_classes() -> None:
    dataset = load_wili(allow_download=False)
    assert dataset.n_classes == WILI_N_CLASSES
    assert dataset.n_train == WILI_N_CLASSES * WILI_PER_CLASS
    assert dataset.n_test == WILI_N_CLASSES * WILI_PER_CLASS
    assert list(dataset.labels) == sorted(dataset.labels)
    counts = np.bincount(dataset.y_train, minlength=WILI_N_CLASSES)
    assert np.all(counts == WILI_PER_CLASS)


@integration
def test_wili_shots_are_never_implicit() -> None:
    """Few-shot must be requested, and requires an explicit generator."""
    assert load_wili(allow_download=False).metadata["shots"] is None
    with pytest.raises(ValueError, match="requires an explicit rng"):
        load_wili(shots=10, allow_download=False)
    with pytest.raises(ValueError, match="exceeds"):
        load_wili(shots=WILI_PER_CLASS + 1, rng=set_all_seeds(SEED),
                  allow_download=False)

    few = load_wili(shots=10, rng=set_all_seeds(SEED), allow_download=False)
    assert few.metadata["shots"] == 10
    assert few.n_train == 10 * WILI_N_CLASSES
    assert few.n_test == WILI_N_CLASSES * WILI_PER_CLASS  # test split untouched


@integration
def test_wili_shots_really_come_from_the_training_split() -> None:
    """Every few-shot example must be a training pair of the full split."""
    full = load_wili(allow_download=False)
    few = load_wili(shots=10, rng=set_all_seeds(SEED), allow_download=False)
    train_pairs = set(zip(full.x_train, full.y_train.tolist()))
    assert set(zip(few.x_train, few.y_train.tolist())) <= train_pairs


@integration
def test_wili_train_test_content_overlap_is_the_documented_amount() -> None:
    """WiLI-2018 itself repeats paragraphs across its official splits.

    This is a property of the published benchmark, not of this code: the
    official split is used unchanged, as registered, so the overlap is
    measured and reported rather than silently removed. Pinning the number
    turns a dataset defect into a guarded fact — if a future archive
    differs, this fails and the change gets noticed.
    """
    dataset = load_wili(allow_download=False)
    overlap = split_overlap(dataset.x_train, dataset.x_test)
    assert overlap["overlapping_texts"] == WILI_KNOWN_TRAIN_TEST_OVERLAP
    # Bounded impact: at most this fraction of the test set can be scored
    # correctly purely by having memorised a training paragraph.
    assert overlap["overlapping_texts"] / dataset.n_test < 0.006


# ---------------------------------------------------------------------------
# Registered vocabulary procedure (PREREG §3.2)
# ---------------------------------------------------------------------------

def test_vocabulary_is_balanced_across_classes() -> None:
    """Every class contributes; that is the point of the registered variant."""
    dataset = _synthetic_text_dataset(n_classes=6, per_class=5)
    vocabulary = build_trigram_vocabulary(dataset.x_train, dataset.y_train,
                                          dataset.n_classes, size=60)
    contribution = vocabulary_contribution(dataset.x_train, dataset.y_train,
                                           dataset.n_classes, vocabulary)
    assert np.all(contribution > 0), "a class received no vocabulary entries"


def test_vocabulary_is_deterministic_and_unique() -> None:
    dataset = _synthetic_text_dataset()
    first = build_trigram_vocabulary(dataset.x_train, dataset.y_train,
                                     dataset.n_classes, size=40)
    second = build_trigram_vocabulary(dataset.x_train, dataset.y_train,
                                      dataset.n_classes, size=40)
    assert first == second
    assert len(set(first)) == len(first)


def test_vocabulary_is_independent_of_sample_order() -> None:
    dataset = _synthetic_text_dataset()
    order = np.random.default_rng(3).permutation(dataset.n_train)
    shuffled = build_trigram_vocabulary(
        tuple(dataset.x_train[i] for i in order), dataset.y_train[order],
        dataset.n_classes, size=40)
    assert shuffled == build_trigram_vocabulary(
        dataset.x_train, dataset.y_train, dataset.n_classes, size=40)


def test_pooled_variant_is_available_only_as_a_diagnostic() -> None:
    """The rejected variant exists so its cost can be measured, not assumed."""
    dataset = _synthetic_text_dataset()
    pooled = pooled_trigram_vocabulary(dataset.x_train, size=40)
    balanced = build_trigram_vocabulary(dataset.x_train, dataset.y_train,
                                        dataset.n_classes, size=40)
    assert len(pooled) == len(balanced)
    assert pooled != balanced


# ---------------------------------------------------------------------------
# 3 & 4. Cross-process and hash-seed determinism
# ---------------------------------------------------------------------------

def _run_probe(seed: int, hashseed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    proc = subprocess.run(
        [sys.executable, "-m", "tests.leakage_probe", "--seed", str(seed),
         "--hash-only"],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT, check=True,
    )
    return proc.stdout.strip()


@integration
def test_two_fresh_processes_agree() -> None:
    """Same seed, two separate interpreters, identical pipeline output."""
    assert _run_probe(SEED, "0") == _run_probe(SEED, "0")


@integration
def test_result_does_not_depend_on_pythonhashseed() -> None:
    """Enforces the "never iterate over hash order" rule for the data path.

    Class orderings, vocabularies and shot selections all pass through
    containers whose iteration order would otherwise vary between processes.
    """
    first = _run_probe(SEED, "0")
    second = _run_probe(SEED, "1")
    assert first == second, (
        f"PYTHONHASHSEED=0 gave {first}, PYTHONHASHSEED=1 gave {second}. "
        "Something in the data pipeline depends on hash iteration order — "
        "derive class orderings via sorted()/stable_label_order()."
    )


@integration
def test_different_seeds_give_different_results() -> None:
    """Guards against a probe that ignores its seed and would pass trivially."""
    assert _run_probe(SEED, "0") != _run_probe(SEED + 1, "0")


@integration
def test_probe_is_stable_within_a_process() -> None:
    assert probe_hash(SEED) == probe_hash(SEED)


# ---------------------------------------------------------------------------
# 5. Cross-platform reference
# ---------------------------------------------------------------------------

def _compare_probe_to_reference(reference: dict[str, Any],
                                current: dict[str, Any]) -> list[str]:
    """Return human-readable differences between two probe results."""
    differences: list[str] = []
    for dataset_name in sorted(set(reference) | set(current)):
        if dataset_name == "seed":
            continue
        expected = reference.get(dataset_name)
        actual = current.get(dataset_name)
        if expected != actual:
            if isinstance(expected, dict) and isinstance(actual, dict):
                for key in sorted(set(expected) | set(actual)):
                    if expected.get(key) != actual.get(key):
                        differences.append(
                            f"{dataset_name}.{key}: reference={expected.get(key)!r} "
                            f"current={actual.get(key)!r}")
            else:
                differences.append(f"{dataset_name}: differs")
    return differences


def test_reference_comparison_logic_detects_a_difference(tmp_path: Path) -> None:
    """Exercises the comparison itself, so it is not dead code while skipped."""
    reference = {"seed": 1, "mnist": {"artifacts_digest": "aaa", "n_train": 10}}
    identical = {"seed": 1, "mnist": {"artifacts_digest": "aaa", "n_train": 10}}
    changed = {"seed": 1, "mnist": {"artifacts_digest": "bbb", "n_train": 10}}
    assert _compare_probe_to_reference(reference, identical) == []
    differences = _compare_probe_to_reference(reference, changed)
    assert len(differences) == 1 and "artifacts_digest" in differences[0]


@integration
def test_matches_cross_platform_reference() -> None:
    """Compare this platform's pipeline against a reference from another one.

    The reference is produced on the canonical machine with
    ``python -m tests.leakage_probe --seed 42 --write-reference`` and
    committed to ``tests/fixtures/``. Until one exists the test skips with
    an explicit message: a visible gap, not a silent pass. Per
    ``docs/PROTOCOL.md`` no milestone figure counts before the reference
    machine has confirmed it.
    """
    if not REFERENCE_PATH.exists():
        pytest.skip(
            f"no cross-platform reference at {REFERENCE_PATH.relative_to(REPO_ROOT)} "
            "— generate it with "
            "'python -m tests.leakage_probe --seed 42 --write-reference' and commit it"
        )

    record = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))

    # Comparing a platform against a reference it produced itself proves
    # nothing — it would pass even if the pipeline were wildly
    # platform-dependent. Skipping here keeps that non-result visible
    # instead of banking a green tick for it.
    if record["platform_tag"] == platform_tag():
        pytest.skip(
            f"reference was recorded on this same platform "
            f"({record['platform_tag']}), so this comparison is vacuous — "
            f"run the suite on a different platform to make it meaningful"
        )

    reference_probe = record["probe"]
    current = probe(int(reference_probe["seed"]))
    differences = _compare_probe_to_reference(reference_probe, current)
    assert not differences, (
        f"pipeline differs from the reference recorded on "
        f"{record['platform_tag']} (this platform: {platform_tag()}):\n  "
        + "\n  ".join(differences)
    )
