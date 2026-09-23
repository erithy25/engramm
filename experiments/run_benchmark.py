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
import hashlib
import multiprocessing
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from collections.abc import Sequence
from typing import Any

import numpy as np

from data.loaders import Dataset, fit_train_artifacts, load_mnist, load_wili
from engramm.core import ItemMemory, PrototypeClassifier, unpack_bits
from engramm.encoders import Encoder, build_encoder
from engramm.memory import Engramm, FusionConfig
from engramm.metrics import accuracy, macro_f1
from engramm.repro import (
    git_revision,
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
    if task in ("banking77", "clinc150"):
        from data.intents import load_banking77, load_clinc150
        loader = load_banking77 if task == "banking77" else load_clinc150
        return loader(shots=shots, rng=rng, allow_download=allow_download)
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
        mask = dataset.metadata.get("test_in_full_train")
        if mask is not None:
            changes["metadata"] = {**dataset.metadata,
                                   "test_in_full_train": np.asarray(mask)[:limit_test]}
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


def to_dataset_indices(predicted: np.ndarray, model_labels: Sequence[str],
                       dataset_labels: Sequence[str]) -> np.ndarray:
    """Translate the model's class indices into the dataset's.

    The model numbers the classes it has *seen*, the dataset numbers all of
    them. Both are sorted, so the two coincide exactly when every class
    occurs in training — which is true for every registered run, but not
    for a ``--limit-train`` subset that happens to miss a class. Comparing
    raw indices there silently shifted every later class (perfect
    predictions scored 0.0 in the review's reproduction). Mapping by label
    removes the assumption instead of relying on it.
    """
    position = {label: i for i, label in enumerate(dataset_labels)}
    missing = [label for label in model_labels if label not in position]
    if missing:
        raise ValueError(f"model knows labels the dataset does not: {missing[:5]}")
    lookup = np.array([position[label] for label in model_labels], dtype=np.int64)
    return lookup[np.asarray(predicted, dtype=np.int64)]


def predictions_digest(predicted: np.ndarray, labels: Sequence[str]) -> str:
    """SHA-256 over the predicted label names, in test-split order.

    Accuracy can agree to four decimals while individual predictions
    differ; this digest makes "the run reproduced" a bitwise statement about
    every single output rather than about a summary statistic.
    """
    hasher = hashlib.sha256()
    for index in np.asarray(predicted, dtype=np.int64):
        hasher.update(labels[int(index)].encode("utf-8") + b"\n")
    return hasher.hexdigest()


def duplicate_breakdown(dataset: Dataset, predicted: np.ndarray) -> dict[str, Any]:
    """Accuracy with and without test items whose exact text is in training.

    WiLI-2018's official split repeats 639 distinct paragraphs across train
    and test, which affects 3,147 test items (2.68 %) because some repeat
    hundreds of times. The official split is used unchanged — results stay
    comparable to the literature — but the share is reported, and so is the
    accuracy on the remaining items, so any inflation from memorised
    duplicates is visible rather than argued away.
    """
    mask = dataset.metadata.get("test_in_full_train")
    if mask is None:
        return {}
    mask = np.asarray(mask, dtype=bool)
    if mask.shape[0] != dataset.n_test:
        return {}
    y_true = np.asarray(dataset.y_test)
    keep = ~mask
    return {
        "test_items_in_train": int(mask.sum()),
        "accuracy_excluding_train_duplicates": (
            float(np.count_nonzero(y_true[keep] == predicted[keep]) / keep.sum())
            if keep.any() else None),
    }


def encode_streaming(encoder: Encoder, samples: Any, batch_size: int) -> np.ndarray:
    """Packed encodings of a whole split, built one batch at a time.

    Only the packed form (``D / 8`` bytes per sample) is kept; the ``int32``
    accumulator of each batch is released before the next one is built.
    """
    total = len(samples)
    out = np.empty((total, encoder.dimension // 8), dtype=np.uint8)
    for start in range(0, total, batch_size):
        stop = min(start + batch_size, total)
        batch = (samples[start:stop] if isinstance(samples, np.ndarray)
                 else list(samples[start:stop]))
        out[start:stop] = encoder.encode(batch)
    return out


def run_engramm(model: Engramm, encoder: Encoder, dataset: Dataset, seed: int,
                t2_epochs: int, train_batch_size: int,
                test_batch_size: int) -> tuple[np.ndarray, list[float]]:
    """T1 (+ episodes), optional T2, then streamed prediction of the test split.

    T2 visits the training examples in a fresh random order per epoch drawn
    from ``default_rng(seed)`` — the same generator the validation sweep in
    ``experiments/tune_fusion.py`` uses — and retrieves leave-one-out, so an
    example never finds its own episode.
    """
    labels = [dataset.labels[i] for i in dataset.y_train]
    packed = encode_streaming(encoder, dataset.x_train, train_batch_size)
    positions = model.learn(packed, labels)
    errors = model.refine(packed, labels, t2_epochs, rng=np.random.default_rng(seed),
                          episode_positions=positions) if t2_epochs else []
    del packed

    predictions = np.empty(dataset.n_test, dtype=np.int64)
    for start in range(0, dataset.n_test, test_batch_size):
        stop = min(start + test_batch_size, dataset.n_test)
        batch = (dataset.x_test[start:stop] if isinstance(dataset.x_test, np.ndarray)
                 else list(dataset.x_test[start:stop]))
        predictions[start:stop] = model.predict(encoder.encode(batch))
    return predictions, errors


def run_seed(task: str, seed: int, dimension: int, shots: int | None,
             limit_train: int | None, limit_test: int | None,
             allow_download: bool,
             test_batch_size: int = DEFAULT_TEST_BATCH,
             train_batch_size: int = DEFAULT_TRAIN_BATCH,
             pipeline: str = "prototypes",
             t2_epochs: int = 0,
             fusion: dict[str, Any] | None = None,
             config_source: str | None = None,
             encoder_options: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one seed end to end; returns ``(result, hyperparameters)``.

    ``pipeline="prototypes"`` with ``t2_epochs=0`` is the reduced core that
    produced the registered E1/E2 records, kept on its original code path so
    those records stay reproducible bit for bit. Everything else — episodes,
    T2, score fusion — runs through :class:`engramm.memory.Engramm`.
    """
    if pipeline not in ("prototypes", "full"):
        raise ValueError(f"unknown pipeline {pipeline!r}")
    rng = set_all_seeds(seed)
    dataset = subset(load_task(task, shots, rng, allow_download),
                     limit_train, limit_test)
    artifacts = fit_train_artifacts(dataset)

    item_memory = ItemMemory(seed, dimension)
    encoder = build_encoder(task, item_memory, **(encoder_options or {}))

    if pipeline == "full" or t2_epochs > 0:
        config = FusionConfig(**(fusion or {}))
        if pipeline == "prototypes":
            config = FusionConfig(**{**config.to_dict(), "lambda_e": 0.0})
        engramm = Engramm(dimension, seed, config)
        predicted_model, errors = run_engramm(engramm, encoder, dataset, seed,
                                              t2_epochs, train_batch_size,
                                              test_batch_size)
        if engramm.prototypes.halvings:
            raise RuntimeError(f"accumulator halved {engramm.prototypes.halvings} "
                               f"time(s); see docs/DEVIATIONS.md KNOWN-2")
        predicted = to_dataset_indices(predicted_model, engramm.labels, dataset.labels)
        result = _result(dataset, predicted)
        result["t2_error_per_epoch"] = [round(e, 6) for e in errors]
        hyperparameters = _hyperparameters(
            task, dimension, shots, encoder, artifacts, dataset, limit_train,
            limit_test, test_batch_size, train_batch_size,
            engramm.prototypes.halvings)
        hyperparameters.update({
            "pipeline": pipeline,
            "episodes": pipeline == "full",
            "t2_epochs": t2_epochs,
            "fusion": config.to_dict(),
            "config_source": config_source or "command line",
            "n_episodes": len(engramm.episodes),
        })
        return result, hyperparameters

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

    predicted = to_dataset_indices(
        predict_streaming(model, encoder, dataset.x_test, test_batch_size),
        model.labels, dataset.labels)

    result = _result(dataset, predicted)
    hyperparameters = _hyperparameters(
        task, dimension, shots, encoder, artifacts, dataset, limit_train,
        limit_test, test_batch_size, train_batch_size, model.halvings)
    hyperparameters.update({"pipeline": "prototypes", "episodes": False, "t2_epochs": 0})
    return result, hyperparameters


def _result(dataset: Dataset, predicted: np.ndarray) -> dict[str, Any]:
    result = {
        "accuracy": accuracy(dataset.y_test, predicted),
        "macro_f1": macro_f1(dataset.y_test, predicted, dataset.n_classes),
        "n_train": dataset.n_train,
        "n_test": dataset.n_test,
        "n_classes": dataset.n_classes,
        "chance_level": dataset.chance_level,
        "predictions_sha256": predictions_digest(predicted, dataset.labels),
    }
    result.update(duplicate_breakdown(dataset, predicted))
    return result


def _hyperparameters(task: str, dimension: int, shots: int | None, encoder: Encoder,
                     artifacts: Any, dataset: Dataset, limit_train: int | None,
                     limit_test: int | None, test_batch_size: int,
                     train_batch_size: int, halvings: int) -> dict[str, Any]:
    return {
        "task": task,
        "dimension": dimension,
        "shots": shots,
        "encoder": repr(encoder),
        "artifacts_digest": artifacts.digest(),
        "official_split": bool(dataset.metadata.get("official_split"))
                          and limit_train is None and limit_test is None,
        "limit_train": limit_train,
        "limit_test": limit_test,
        "test_batch_size": test_batch_size,
        "train_batch_size": train_batch_size,
        "accumulator_halvings": halvings,
    }


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
    parser.add_argument("--task", choices=["mnist", "wili", "banking77", "clinc150"],
                        required=True)
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
    parser.add_argument("--pipeline", choices=["prototypes", "full"], default="prototypes",
                        help="prototypes = reduced core (registered E1/E2 path); "
                             "full = episodes + score fusion (docs/D2_SPEC.md)")
    parser.add_argument("--t2-epochs", type=int, default=0,
                        help="error-driven refinement epochs (T2)")
    parser.add_argument("--k", type=int, default=32)
    parser.add_argument("--theta0", type=float, default=0.0)
    parser.add_argument("--lambda-e", type=float, default=1.0)
    parser.add_argument("--lambda-p", type=float, default=1.0)
    parser.add_argument("--t2-local", action="store_true")
    parser.add_argument("--config-from", type=str, default=None,
                        help="take t2_epochs, lambda_e, theta0, k and t2_local from "
                             "the 'selected' cell of a results/tuning/*.json record "
                             "(chosen on validation, never on test)")
    parser.add_argument("--no-isolate", action="store_true",
                        help="run seeds in this process instead of one child "
                             "process each; peak memory is then the process "
                             "high-water mark, not a per-seed figure")
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

    fusion = {"k": args.k, "theta0": args.theta0, "lambda_e": args.lambda_e,
              "lambda_p": args.lambda_p, "t2_local": args.t2_local}
    encoder_options: dict[str, Any] = {}
    t2_epochs, config_source = args.t2_epochs, None
    if args.config_from:
        import json
        tuning = json.loads(open(args.config_from, encoding="utf-8").read())
        if tuning.get("test_split_used", True):
            raise SystemExit(f"{args.config_from} does not certify test_split_used=false")
        selected = tuning["selected"]
        fusion.update({"k": tuning["k"], "theta0": selected["theta0"],
                       "lambda_e": selected["lambda_e"],
                       "t2_local": tuning.get("t2_local", False)})
        t2_epochs, config_source = selected["t2_epochs"], args.config_from
        encoder_options = selected.get("encoder_options", {})
        print(f"configuration from {args.config_from}: t2_epochs={t2_epochs} {fusion}")

    # The code that runs is the code checked out now: Python has already
    # imported it. Capturing provenance at write time instead would credit a
    # commit made mid-run to seeds that never executed it.
    git_state = git_revision()

    results: list[SeedResult] = []
    for seed in seeds:
        kwargs = dict(task=args.task, seed=seed, dimension=args.dimension,
                      shots=args.shots, limit_train=args.limit_train,
                      limit_test=args.limit_test,
                      allow_download=args.allow_download,
                      test_batch_size=args.test_batch,
                      train_batch_size=args.train_batch,
                      pipeline=args.pipeline, t2_epochs=t2_epochs,
                      fusion=fusion, config_source=config_source,
                      encoder_options=encoder_options)
        if args.no_isolate:
            result, hyperparameters, elapsed, peak = _timed_run_seed(kwargs)
        else:
            result, hyperparameters, elapsed, peak = run_isolated(kwargs)
        path = write_result(task=args.task, seed=seed, result=result,
                            hyperparams=hyperparameters, wall_seconds=elapsed,
                            results_dir=args.results_dir, git_state=git_state,
                            peak_rss=peak if not args.no_isolate else None)
        results.append(SeedResult(
            seed=seed, accuracy=result["accuracy"], macro_f1=result["macro_f1"],
            wall_seconds=elapsed, peak_rss_mb=peak, record_path=str(path),
        ))
        print(f"  seed {seed:>5}: accuracy={result['accuracy']:.4f} "
              f"macro_f1={result['macro_f1']:.4f} "
              f"({elapsed:.1f}s, peak {peak:.0f} MiB) -> {path.name}", flush=True)

    _print_summary(results)
    return 0


def _timed_run_seed(kwargs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], float, float]:
    """Run one seed and return ``(result, hyperparams, wall_seconds, peak_rss_mb)``."""
    started = time.perf_counter()
    result, hyperparameters = run_seed(**kwargs)
    return result, hyperparameters, time.perf_counter() - started, peak_rss_mb()


def run_isolated(kwargs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], float, float]:
    """Run one seed in a fresh child process.

    ``ru_maxrss`` is a per-process high-water mark that never falls, so in a
    shared process every seed after the first reported the largest peak of
    all earlier seeds (visible in the committed MNIST records: 3113 → 3135 →
    3135 → 3136 → 3136 MiB). A spawned child starts from nothing, so its
    peak belongs to its seed alone. ``spawn`` rather than ``fork`` so the
    child does not inherit the parent's memory either.
    """
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        return pool.submit(_timed_run_seed, kwargs).result()


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
