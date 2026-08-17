"""Run a benchmark across seeds and record one result per seed.

    python -m experiments.run_benchmark --task mnist --seeds 5
    python -m experiments.run_benchmark --task wili --seeds 5 --shots 10
    python -m experiments.run_benchmark --task mnist --dry-run

Each seed writes a JSON record to ``results/`` via
:func:`engramm.repro.write_result`, carrying the seed, commit hash, every
hyperparameter, wall time, peak memory, and the environment — including the
``canonical`` flag, which is derived from the host and cannot be set by
hand (``docs/PROTOCOL.md``).

``--dry-run`` executes everything except the final thresholding — loaders,
feature fitting, item memory, accumulation — and reports the tie rate per
split, without writing a record.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass
from collections.abc import Sequence
from typing import Any

import numpy as np

from data.loaders import Dataset, fit_train_artifacts, load_mnist, load_wili
from engramm.core import ItemMemory, PrototypeClassifier, unpack_bits
from engramm.encoders import Encoder, build_encoder
from engramm.metrics import accuracy, macro_f1
from engramm.repro import (
    is_canonical_environment,
    peak_rss_mb,
    set_all_seeds,
    write_result,
)

DEFAULT_SEEDS = (42, 7, 1337, 2026, 99, 3, 123, 512, 8191, 31337)

#: Test samples encoded and classified per batch. Bounds the peak
#: accumulator at ``batch × D`` int32 instead of the whole split.
DEFAULT_TEST_BATCH = 2_000

#: Training samples encoded and learned per batch, for the same reason.
DEFAULT_TRAIN_BATCH = 5_000


@dataclass
class SeedResult:
    seed: int
    accuracy: float
    macro_f1: float
    wall_seconds: float
    peak_rss_mb: float
    record_path: str


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def load_task(task: str, shots: int | None, rng: np.random.Generator,
              allow_download: bool) -> Dataset:
    if task == "mnist":
        if shots is not None:
            raise SystemExit(
                "--shots applies to wili only; MNIST uses its official "
                "60k/10k split unchanged"
            )
        return load_mnist(allow_download=allow_download)
    if task == "wili":
        return load_wili(shots=shots, rng=rng, allow_download=allow_download)
    raise SystemExit(f"unknown task {task!r}")


def subset(dataset: Dataset, limit_train: int | None,
           limit_test: int | None) -> Dataset:
    """Bound the split sizes, for dry runs and smoke tests."""
    from dataclasses import replace

    changes: dict[str, Any] = {}
    if limit_train is not None and dataset.n_train > limit_train:
        x = dataset.x_train
        changes["x_train"] = (x[:limit_train] if isinstance(x, np.ndarray)
                              else tuple(x[:limit_train]))
        changes["y_train"] = dataset.y_train[:limit_train]
    if limit_test is not None and dataset.n_test > limit_test:
        x = dataset.x_test
        changes["x_test"] = (x[:limit_test] if isinstance(x, np.ndarray)
                             else tuple(x[:limit_test]))
        changes["y_test"] = dataset.y_test[:limit_test]
    return replace(dataset, **changes) if changes else dataset


def predict_streaming(model: PrototypeClassifier, encoder: Encoder,
                      samples: Any, batch_size: int) -> np.ndarray:
    """Encode, classify and discard the test split one batch at a time.

    Encoding materialises an ``N × D`` ``int32`` accumulator, which for the
    full WiLI test split at D = 10,000 is 4.7 GB — held alongside the
    training side, that exceeds the reference machine's memory. Only the
    predictions are needed, so each batch is encoded, classified and
    released, bounding the peak at one batch instead of one split.

    The result is bit-identical to encoding the split in one call:
    accumulation is per-sample, and scoring compares each sample against
    prototypes that no longer change. ``tests/test_runner.py`` verifies that
    equality rather than asserting it.
    """
    if batch_size <= 0:
        raise ValueError("test_batch_size must be positive")

    total = len(samples)
    predictions = np.empty(total, dtype=np.int64)
    for start in range(0, total, batch_size):
        stop = min(start + batch_size, total)
        batch = (samples[start:stop] if isinstance(samples, np.ndarray)
                 else list(samples[start:stop]))
        packed = encoder.encode(batch)
        predictions[start:stop] = model.predict(packed)
    return predictions


def learn_streaming(model: PrototypeClassifier, encoder: Encoder,
                    samples: Any, labels: Sequence[str],
                    batch_size: int) -> None:
    """Encode and learn the training split one batch at a time.

    The full WiLI training split is 117,500 texts, whose ``int32``
    accumulator alone is 4.7 GB at D = 10,000 — measured as a 6.26 GB peak
    for the whole run, over the 6 GB the reference machine can spare.
    Learning is additive, so the batches can be folded in one at a time and
    only one batch is ever resident.

    **Two things make this equivalent rather than merely similar:**

    * All classes are registered up front, in sorted label order. Otherwise
      a class first seen in batch 7 would take an index that depends on how
      the data was split, permuting the rows of ``A``.
    * Accumulation is pure addition — with one exception. Halving the
      accumulator (:data:`engramm.core.HALVE_THRESHOLD`) is applied when a
      running total crosses the threshold, and *where* that happens depends
      on batch boundaries. The caller must therefore check
      ``model.halvings``; :func:`run_seed` records it, and for this
      project's datasets it stays zero because ``|A|`` is bounded by the
      number of examples per class (500 for full WiLI, 6,000 for full
      MNIST) against a threshold of 16,384.
    """
    if batch_size <= 0:
        raise ValueError("train_batch_size must be positive")

    model.register_classes(labels)
    total = len(labels)
    for start in range(0, total, batch_size):
        stop = min(start + batch_size, total)
        batch = (samples[start:stop] if isinstance(samples, np.ndarray)
                 else list(samples[start:stop]))
        packed = encoder.encode(batch)
        signed = (unpack_bits(packed, model.dimension).astype(np.int8) * 2) - 1
        model.learn(signed, list(labels[start:stop]))


def run_seed(task: str, seed: int, dimension: int, shots: int | None,
             limit_train: int | None, limit_test: int | None,
             allow_download: bool,
             test_batch_size: int = DEFAULT_TEST_BATCH,
             train_batch_size: int = DEFAULT_TRAIN_BATCH) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one seed end to end; returns ``(result, hyperparameters)``."""
    rng = set_all_seeds(seed)
    dataset = subset(load_task(task, shots, rng, allow_download),
                     limit_train, limit_test)
    artifacts = fit_train_artifacts(dataset)

    item_memory = ItemMemory(seed, dimension)
    encoder = build_encoder(task, item_memory)

    model = PrototypeClassifier(dimension, seed=seed)
    learn_streaming(model, encoder, dataset.x_train,
                    [dataset.labels[i] for i in dataset.y_train],
                    train_batch_size)
    if model.halvings:
        raise RuntimeError(
            f"the accumulator was halved {model.halvings} time(s), so this "
            f"batched run is not equivalent to an unbatched one — where "
            f"halving fires depends on batch boundaries. Re-run unbatched, "
            f"or raise HALVE_THRESHOLD, before citing this number."
        )

    predicted = predict_streaming(model, encoder, dataset.x_test, test_batch_size)

    result = {
        "accuracy": accuracy(dataset.y_test, predicted),
        "macro_f1": macro_f1(dataset.y_test, predicted, dataset.n_classes),
        "n_train": dataset.n_train,
        "n_test": dataset.n_test,
        "n_classes": dataset.n_classes,
        "chance_level": dataset.chance_level,
    }
    hyperparameters = {
        "task": task,
        "dimension": dimension,
        "shots": shots,
        "encoder": repr(encoder),
        "artifacts_digest": artifacts.digest(),
        "official_split": dataset.metadata.get("official_split"),
        "limit_train": limit_train,
        "limit_test": limit_test,
        "test_batch_size": test_batch_size,
        "train_batch_size": train_batch_size,
        "accumulator_halvings": model.halvings,
        "episodes": False,
        "t2_epochs": 0,
    }
    return result, hyperparameters


def run_dry(task: str, seed: int, dimension: int, shots: int | None,
            limit_train: int, limit_test: int, allow_download: bool) -> int:
    """Execute everything up to, but not including, the first tie."""
    print(f"dry run — task={task} seed={seed} D={dimension} shots={shots}")
    print(f"  canonical environment: {is_canonical_environment()}")

    started = time.perf_counter()
    rng = set_all_seeds(seed)
    dataset = subset(load_task(task, shots, rng, allow_download),
                     limit_train, limit_test)
    print(f"  loaded {dataset.name}: {dataset.n_train} train / "
          f"{dataset.n_test} test / {dataset.n_classes} classes "
          f"({time.perf_counter() - started:.1f}s)")

    marker = time.perf_counter()
    artifacts = fit_train_artifacts(dataset)
    print(f"  fitted train artifacts: digest {artifacts.digest()[:16]}… "
          f"({time.perf_counter() - marker:.1f}s)")

    marker = time.perf_counter()
    item_memory = ItemMemory(seed, dimension)
    encoder = build_encoder(task, item_memory)
    print(f"  built encoder: {encoder} ({time.perf_counter() - marker:.1f}s)")

    for stage, samples in (("train", dataset.x_train), ("test", dataset.x_test)):
        marker = time.perf_counter()
        totals = encoder.accumulate(samples)
        elapsed = time.perf_counter() - marker
        tied = (totals == 0).sum(axis=1)
        n = totals.shape[0]
        print(f"  accumulated {stage}: {totals.shape} in {elapsed:.1f}s "
              f"({1000 * elapsed / max(n, 1):.2f} ms/sample)")
        print(f"    ties: {int(np.count_nonzero(tied))}/{n} samples affected, "
              f"{tied.mean():.1f} of {dimension} components on average, "
              f"max {int(tied.max()) if n else 0}")

    print(f"\n  pipeline verified up to thresholding. "
          f"peak RSS {peak_rss_mb():.0f} MiB, "
          f"total {time.perf_counter() - started:.1f}s")
    print("  the remaining step is thresholding, which resolves the ties "
          "above\n  via engramm.core.resolve_tie. No result written.")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--task", choices=["mnist", "wili"], required=True)
    parser.add_argument("--seeds", type=int, default=5,
                        help="how many of the registered seeds to run (default 5)")
    parser.add_argument("--seed-list", type=str, default=None,
                        help="explicit comma-separated seeds, overriding --seeds")
    parser.add_argument("--shots", type=int, default=None,
                        help="wili only: training paragraphs per language; "
                             "omit for the full training split")
    parser.add_argument("--D", dest="dimension", type=int, default=10_000,
                        help="hypervector dimension (default 10000)")
    parser.add_argument("--dry-run", action="store_true",
                        help="verify the pipeline up to the first tie, write nothing")
    parser.add_argument("--limit-train", type=int, default=None)
    parser.add_argument("--limit-test", type=int, default=None)
    parser.add_argument("--results-dir", type=str, default=None,
                        help="where to write records (default: results/). Use a "
                             "scratch directory for exploratory runs so the "
                             "official record set stays clean")
    parser.add_argument("--train-batch", type=int, default=DEFAULT_TRAIN_BATCH,
                        help=f"training samples per encode/learn batch "
                             f"(default {DEFAULT_TRAIN_BATCH})")
    parser.add_argument("--test-batch", type=int, default=DEFAULT_TEST_BATCH,
                        help=f"test samples per encode/classify batch "
                             f"(default {DEFAULT_TEST_BATCH})")
    parser.add_argument("--allow-download", action="store_true",
                        help="permit fetching sources that are not cached")
    args = parser.parse_args(argv)

    if args.seed_list:
        seeds = [int(s) for s in args.seed_list.split(",") if s.strip()]
    else:
        if not 1 <= args.seeds <= len(DEFAULT_SEEDS):
            raise SystemExit(f"--seeds must be between 1 and {len(DEFAULT_SEEDS)}")
        seeds = list(DEFAULT_SEEDS[:args.seeds])

    if args.dry_run:
        return run_dry(
            args.task, seeds[0], args.dimension, args.shots,
            args.limit_train if args.limit_train is not None else 200,
            args.limit_test if args.limit_test is not None else 200,
            args.allow_download,
        )

    print(f"task={args.task} D={args.dimension} shots={args.shots} "
          f"seeds={seeds}")
    print(f"canonical environment: {is_canonical_environment()}"
          + ("" if is_canonical_environment() else
             "  (timing and memory figures are not official — docs/PROTOCOL.md)"))

    results: list[SeedResult] = []
    for seed in seeds:
        started = time.perf_counter()
        result, hyperparameters = run_seed(
            args.task, seed, args.dimension, args.shots,
            args.limit_train, args.limit_test, args.allow_download,
            args.test_batch)
        elapsed = time.perf_counter() - started
        path = write_result(task=args.task, seed=seed, result=result,
                            hyperparams=hyperparameters, wall_seconds=elapsed,
                            results_dir=args.results_dir)
        results.append(SeedResult(
            seed=seed, accuracy=result["accuracy"], macro_f1=result["macro_f1"],
            wall_seconds=elapsed, peak_rss_mb=peak_rss_mb(), record_path=str(path),
        ))
        print(f"  seed {seed:>5}: accuracy={result['accuracy']:.4f} "
              f"macro_f1={result['macro_f1']:.4f} "
              f"({elapsed:.1f}s, peak {peak_rss_mb():.0f} MiB) -> {path.name}")

    _print_summary(results)
    return 0


def _print_summary(results: list[SeedResult]) -> None:
    """Report mean and standard deviation. No interpretation."""
    if not results:
        return
    print(f"\n{len(results)} seeds: {[r.seed for r in results]}")
    for name, values in (
        ("accuracy", [r.accuracy for r in results]),
        ("macro_f1", [r.macro_f1 for r in results]),
        ("wall_seconds", [r.wall_seconds for r in results]),
        ("peak_rss_mb", [r.peak_rss_mb for r in results]),
    ):
        mean = statistics.fmean(values)
        deviation = statistics.stdev(values) if len(values) > 1 else 0.0
        print(f"  {name:<13} mean {mean:.4f}  sd {deviation:.4f}  "
              f"min {min(values):.4f}  max {max(values):.4f}")
    if not is_canonical_environment():
        print("\n  wall_seconds and peak_rss_mb are not official on this "
              "environment (docs/PROTOCOL.md rule 2).")


if __name__ == "__main__":
    sys.exit(main())
