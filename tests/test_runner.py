"""Tests for the benchmark runner.

The full success path cannot run until the tie rule exists, so what is
verified here is everything around it: argument handling, split bounding,
the conversion of the open decision into a legible failure, and that a
stopped run leaves no result record behind.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from data.loaders import CACHE_DIR, Dataset
from experiments.run_benchmark import (
    DEFAULT_SEEDS,
    load_task,
    main,
    subset,
)
from engramm.core import ItemMemory, PrototypeClassifier
from engramm.encoders import PixelThermometerEncoder

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED = 42

_CACHE_READY = (CACHE_DIR / "wili-2018.zip").exists() and \
               (CACHE_DIR / "train-images-idx3-ubyte.gz").exists()

integration = pytest.mark.skipif(
    not _CACHE_READY, reason="dataset cache not populated")


def _dataset(n_train: int = 20, n_test: int = 12) -> Dataset:
    return Dataset(
        name="synthetic",
        x_train=np.zeros((n_train, 4), dtype=np.uint8),
        y_train=np.arange(n_train, dtype=np.int64) % 3,
        x_test=np.zeros((n_test, 4), dtype=np.uint8),
        y_test=np.arange(n_test, dtype=np.int64) % 3,
        labels=("a", "b", "c"),
        metadata={"official_split": True, "shots": None},
    )


# ---------------------------------------------------------------------------
# Split bounding
# ---------------------------------------------------------------------------

def test_subset_bounds_both_splits() -> None:
    reduced = subset(_dataset(), limit_train=5, limit_test=4)
    assert reduced.n_train == 5 and reduced.n_test == 4
    assert reduced.labels == ("a", "b", "c")


def test_subset_leaves_smaller_splits_alone() -> None:
    original = _dataset(n_train=3, n_test=2)
    reduced = subset(original, limit_train=99, limit_test=99)
    assert reduced.n_train == 3 and reduced.n_test == 2


def test_subset_without_limits_returns_the_same_object() -> None:
    original = _dataset()
    assert subset(original, None, None) is original


def test_subset_keeps_inputs_and_labels_aligned() -> None:
    dataset = _dataset(n_train=20)
    reduced = subset(dataset, limit_train=7, limit_test=None)
    assert np.array_equal(reduced.y_train, dataset.y_train[:7])
    assert len(reduced.x_train) == len(reduced.y_train)


# ---------------------------------------------------------------------------
# Task selection
# ---------------------------------------------------------------------------

def test_shots_are_rejected_for_mnist() -> None:
    """MNIST has no few-shot mode; asking for one is a mistake, not a default."""
    with pytest.raises(SystemExit, match="official"):
        load_task("mnist", shots=10, rng=np.random.default_rng(0),
                  allow_download=False)


def test_unknown_task_is_rejected() -> None:
    with pytest.raises(SystemExit, match="unknown task"):
        load_task("cifar", shots=None, rng=np.random.default_rng(0),
                  allow_download=False)


def test_seed_count_is_validated() -> None:
    with pytest.raises(SystemExit, match="--seeds must be"):
        main(["--task", "mnist", "--seeds", str(len(DEFAULT_SEEDS) + 1)])
    with pytest.raises(SystemExit, match="--seeds must be"):
        main(["--task", "mnist", "--seeds", "0"])


def test_registered_seeds_match_the_preregistration() -> None:
    """docs/PREREG_ROBUSTNESS.md §5 fixes these ten seeds by name."""
    assert DEFAULT_SEEDS == (42, 7, 1337, 2026, 99, 3, 123, 512, 8191, 31337)


# ---------------------------------------------------------------------------
# Streaming the test split
# ---------------------------------------------------------------------------

def _tie_free_setup(per_class: int = 13, n_classes: int = 3):
    """A trained model and tie-free samples, so encoding actually completes.

    Two odd numbers are needed while the tie rule is open, and they guard
    different steps:

    * **63 pixel positions** — an odd bundle gives every encoded component a
      strict majority, so ``encode`` never ties.
    * **an odd count per class** — the prototype accumulator sums that many
      ``±1`` values, so binarising it never ties either.

    Getting either wrong makes the fixture raise from ``learn`` or
    ``encode`` rather than testing anything, so both are asserted here.
    """
    assert per_class % 2 == 1, "per-class count must be odd or the prototype ties"
    dimension = 512
    encoder = PixelThermometerEncoder(ItemMemory(SEED, dimension),
                                      n_positions=63, n_levels=16)
    rng = np.random.default_rng(SEED)
    images, labels = [], []
    for class_index in range(n_classes):
        for _ in range(per_class):
            centre = rng.integers(0, 256, size=63, dtype=np.uint8)
            noise = rng.integers(-20, 21, size=63)
            images.append(
                np.clip(centre.astype(np.int16) + noise, 0, 255).astype(np.uint8))
            labels.append(f"class{class_index}")
    images = np.stack(images)

    totals = encoder.accumulate(images)
    assert int((totals == 0).sum()) == 0, "fixture must be tie-free"

    packed = encoder.binarise(totals)
    signed = (np.unpackbits(packed, axis=-1, count=dimension).astype(np.int8) * 2) - 1
    model = PrototypeClassifier(dimension, seed=SEED)
    model.learn(signed, labels)
    return model, encoder, images


@pytest.mark.parametrize("batch_size", [1, 2, 7, 38, 39, 1000])
def test_streaming_predictions_match_whole_split(batch_size: int) -> None:
    """Batched encode-and-classify must equal encoding the split at once.

    This is the property the memory optimisation rests on: bounding the
    accumulator changes peak memory and nothing else.
    """
    from experiments.run_benchmark import predict_streaming

    model, encoder, images = _tie_free_setup()
    at_once = model.predict(encoder.encode(images))
    streamed = predict_streaming(model, encoder, images, batch_size)
    assert np.array_equal(streamed, at_once)
    assert streamed.dtype == at_once.dtype


def test_streaming_encodes_identically_to_whole_split() -> None:
    """The encoder itself is batch-invariant, bit for bit."""
    _, encoder, images = _tie_free_setup()
    at_once = encoder.accumulate(images)
    streamed = np.concatenate([encoder.accumulate(images[i:i + 5])
                               for i in range(0, len(images), 5)])
    assert np.array_equal(streamed, at_once)


def test_streaming_handles_text_samples() -> None:
    """Sequences, not just arrays: the text split is a tuple of strings."""
    from experiments.run_benchmark import predict_streaming
    from engramm.encoders import TrigramEncoder

    dimension = 512
    encoder = TrigramEncoder(ItemMemory(SEED, dimension))
    texts = tuple(f"sample number {i} with enough text to form trigrams"
                  for i in range(10))   # 2 classes x 5 -> odd per class
    totals = encoder.accumulate(texts)
    if int((totals == 0).sum()):
        pytest.skip("fixture produced ties; the tie rule is still open")

    model = PrototypeClassifier(dimension, seed=SEED)
    packed = encoder.binarise(totals)
    signed = (np.unpackbits(packed, axis=-1, count=dimension).astype(np.int8) * 2) - 1
    model.learn(signed, [f"c{i % 2}" for i in range(len(texts))])

    assert np.array_equal(predict_streaming(model, encoder, texts, 4),
                          model.predict(packed))


def test_streaming_rejects_a_nonpositive_batch() -> None:
    from experiments.run_benchmark import predict_streaming

    model, encoder, images = _tie_free_setup(per_class=3)
    with pytest.raises(ValueError, match="must be positive"):
        predict_streaming(model, encoder, images, 0)


def test_streaming_works_when_batches_contain_ties() -> None:
    """An even bundle ties in every sample; streaming must still match."""
    from experiments.run_benchmark import predict_streaming

    model, _, _ = _tie_free_setup(per_class=3)
    even = PixelThermometerEncoder(ItemMemory(SEED, 512), n_positions=64,
                                   n_levels=16)
    images = np.random.default_rng(1).integers(0, 256, size=(8, 64), dtype=np.uint8)
    assert even.tie_report(images).total_tied_components > 0
    assert np.array_equal(predict_streaming(model, even, images, 3),
                          model.predict(even.encode(images)))


# ---------------------------------------------------------------------------
# End to end, via the command line
# ---------------------------------------------------------------------------

def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "experiments.run_benchmark", *arguments],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


@integration
def test_dry_run_completes_and_writes_nothing(tmp_path: Path) -> None:
    before = set((REPO_ROOT / "results").glob("*.json"))
    proc = _run_cli("--task", "mnist", "--dry-run", "--D", "512",
                    "--limit-train", "20", "--limit-test", "20")
    assert proc.returncode == 0, proc.stderr
    assert "pipeline verified up to thresholding" in proc.stdout
    assert "ties:" in proc.stdout
    assert "No result written" in proc.stdout
    assert set((REPO_ROOT / "results").glob("*.json")) == before


@integration
def test_dry_run_covers_the_text_pipeline_too() -> None:
    proc = _run_cli("--task", "wili", "--dry-run", "--shots", "10", "--D", "512",
                    "--limit-train", "20", "--limit-test", "20")
    assert proc.returncode == 0, proc.stderr
    assert "TrigramEncoder" in proc.stdout


@integration
def test_real_run_completes_and_writes_one_record_per_seed(tmp_path: Path) -> None:
    """A full run now goes through, and records what it did."""
    import json

    proc = subprocess.run(
        [sys.executable, "-m", "experiments.run_benchmark", "--task", "mnist",
         "--seeds", "2", "--D", "512", "--limit-train", "60", "--limit-test", "40",
         "--results-dir", str(tmp_path)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "accuracy" in proc.stdout and "macro_f1" in proc.stdout

    written = sorted(tmp_path.glob("mnist_*.json"))
    assert len(written) == 2, f"expected one record per seed, got {written}"
    record = json.loads(written[0].read_text())
    assert record["environment"]["canonical"] is False
    assert record["hyperparams"]["dimension"] == 512
    assert 0.0 <= record["result"]["accuracy"] <= 1.0
