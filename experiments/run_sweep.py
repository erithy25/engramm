"""Run the E2 thermometer sweep: 4 constructions x 4 level counts x 3 seeds.

    python -m experiments.run_sweep --D 4000 --results-dir results/e2_sweep \\
        --progress-log results/e2_sweep/progress.log --commit

The grid is registered in ``docs/EXPECTATIONS.md`` E2 and is not a search:
it tests whether the unrecorded thermometer construction
(``docs/DEVIATIONS.md`` GAP-1) accounts for the 6.42 pp MNIST gap. Rule 1
of that registration applies — a better cell is a finding about the cause,
not a new configuration.

Every cell is reported, including the uninteresting ones, and every cell
writes its own record so the sweep can be resumed or audited per cell.

The full grid takes longer than this container stays up (one run was killed
by a container restart after 2 of 48 cells), so the sweep is built to be
interrupted:

* **Resume** — on start it reads the records already in ``--results-dir``
  and skips those cells. An abort costs at most the cell in flight.
* **Persistence** — with ``--commit`` each finished cell is committed and
  pushed immediately. Records must live in the repository, not in scratch:
  scratch is not guaranteed to survive a restart.
* **Progress log** — one line per finished cell in ``--progress-log``, so
  the state after a crash is readable without parsing 48 JSON files.
"""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from data.loaders import fit_train_artifacts, load_mnist
from engramm.core import ItemMemory, PrototypeClassifier
from engramm.encoders import LEVEL_CONSTRUCTIONS, PixelThermometerEncoder
from engramm.metrics import accuracy, macro_f1
from engramm.repro import (
    is_canonical_environment,
    peak_rss_mb,
    set_all_seeds,
    write_result,
)
from experiments.run_benchmark import (
    DEFAULT_TEST_BATCH,
    DEFAULT_TRAIN_BATCH,
    learn_streaming,
    predict_streaming,
)

#: Axis 2 of the registered grid.
LEVEL_COUNTS = (4, 8, 16, 32)

#: Axis 3: the first three of the registered seed set.
SWEEP_SEEDS = (42, 7, 1337)

#: The shipped configuration, and the cell the baseline is taken from.
BASELINE_CELL = ("progressive", 16)


def load_existing(results_dir: Path, dimension: int) -> dict[tuple[str, int, int], dict[str, Any]]:
    """Read finished cells out of ``results_dir``, keyed by (construction, Q, seed).

    Only E2 records at the same dimension count: an absolute accuracy does
    not transfer across D (``docs/EXPECTATIONS.md`` E2, Nachtrag 2), so a
    D=10000 record must never stand in for a D=4000 cell. Records whose
    metadata cannot be read are ignored rather than trusted; the cell is
    then simply run again. If a cell has several records the newest wins —
    filenames carry a sortable UTC timestamp.
    """
    found: dict[tuple[str, int, int], dict[str, Any]] = {}
    if not results_dir.is_dir():
        return found
    for path in sorted(results_dir.glob("e2_*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        hyper = record.get("hyperparams", {})
        if hyper.get("sweep") != "E2" or hyper.get("dimension") != dimension:
            continue
        construction, n_levels = hyper.get("construction"), hyper.get("n_levels")
        seed, result = record.get("seed"), record.get("result", {})
        if construction is None or n_levels is None or seed is None:
            continue
        if "accuracy" not in result:
            continue
        found[(construction, n_levels, seed)] = {
            "construction": construction, "n_levels": n_levels, "seed": seed,
            "accuracy": result["accuracy"], "macro_f1": result.get("macro_f1"),
            "wall_seconds": record.get("runtime", {}).get("wall_seconds"),
            "peak_rss_mb": record.get("runtime", {}).get("peak_rss_mb"),
            "from_record": path.name,
        }
    return found


def append_progress(log_path: Path, index: int, total: int,
                    row: dict[str, Any]) -> None:
    """Append one line per finished cell so a crash leaves a readable state."""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"[{index:>2}/{total}] {stamp} {row['construction']:<20} "
            f"Q={row['n_levels']:<3} seed={row['seed']:<5} "
            f"acc={row['accuracy']:.4f} macro_f1={row['macro_f1']:.4f} "
            f"{row['wall_seconds']:.0f}s peak_rss={row['peak_rss_mb']:.0f}MB\n"
        )


def persist(paths: list[Path], message: str) -> None:
    """Commit and push the finished cell; never let git failure kill the sweep.

    A commit that stays on this container is not persistence — the container
    is what was lost last time — so the push is part of the operation, not a
    convenience. Both steps are reported and neither aborts the run: losing
    version-control bookkeeping is bad, losing 80 minutes of compute is
    worse.
    """
    def git(*args: str) -> tuple[int, str]:
        done = subprocess.run(["git", *args], cwd=Path(__file__).resolve().parent.parent,
                              capture_output=True, text=True)
        return done.returncode, (done.stdout + done.stderr).strip()

    code, output = git("add", "--", *(str(p) for p in paths))
    if code != 0:
        print(f"  ! git add failed: {output}", flush=True)
        return
    code, output = git("commit", "-m", message)
    if code != 0:
        print(f"  ! git commit failed: {output}", flush=True)
        return
    code, output = git("push", "origin", "HEAD")
    if code != 0:
        print(f"  ! git push failed (commit is local only): {output}", flush=True)


def run_cell(construction: str, n_levels: int, seed: int, dimension: int,
             results_dir: Path, train_batch: int, test_batch: int,
             allow_download: bool) -> dict[str, Any]:
    """One (construction, Q, seed) cell, recorded like any other run."""
    started = time.perf_counter()
    set_all_seeds(seed)
    dataset = load_mnist(allow_download=allow_download)
    artifacts = fit_train_artifacts(dataset)

    encoder = PixelThermometerEncoder(
        ItemMemory(seed, dimension), n_positions=784, n_levels=n_levels,
        construction=construction)

    model = PrototypeClassifier(dimension, seed=seed)
    learn_streaming(model, encoder, dataset.x_train,
                    [dataset.labels[i] for i in dataset.y_train], train_batch)
    if model.halvings:
        raise RuntimeError(
            f"accumulator halved {model.halvings} time(s) in cell "
            f"{construction}/Q={n_levels}/seed={seed}; batched learning is "
            f"not equivalent to unbatched there (docs/DEVIATIONS.md KNOWN-2)"
        )

    predicted = predict_streaming(model, encoder, dataset.x_test, test_batch)
    elapsed = time.perf_counter() - started

    result = {
        "accuracy": accuracy(dataset.y_test, predicted),
        "macro_f1": macro_f1(dataset.y_test, predicted, dataset.n_classes),
        "n_train": dataset.n_train,
        "n_test": dataset.n_test,
        "n_classes": dataset.n_classes,
        "chance_level": dataset.chance_level,
    }
    hyperparams = {
        "task": "mnist",
        "sweep": "E2",
        "dimension": dimension,
        "construction": construction,
        "n_levels": n_levels,
        "shots": None,
        "encoder": repr(encoder),
        "artifacts_digest": artifacts.digest(),
        "official_split": True,
        "train_batch_size": train_batch,
        "test_batch_size": test_batch,
        "accumulator_halvings": model.halvings,
        "episodes": False,
        "t2_epochs": 0,
    }
    path = write_result(task=f"e2_{construction}_q{n_levels}", seed=seed,
                        result=result, hyperparams=hyperparams,
                        wall_seconds=elapsed, results_dir=results_dir)
    return {"construction": construction, "n_levels": n_levels, "seed": seed,
            "accuracy": result["accuracy"], "macro_f1": result["macro_f1"],
            "wall_seconds": elapsed, "peak_rss_mb": peak_rss_mb(),
            "record_path": path}


def report(rows: list[dict[str, Any]]) -> None:
    """Print every cell, then the ranking and the registered checks.

    All 16 cells are printed whatever they show — a table with gaps invites
    cherry-picking (registration rule 3).
    """
    by_cell: dict[tuple[str, int], list[float]] = {}
    for row in rows:
        by_cell.setdefault((row["construction"], row["n_levels"]), []).append(
            row["accuracy"])

    print(f"\n{'construction':<20} {'Q':>4} {'mean acc':>10} {'sd':>8} {'n':>3}")
    for construction in LEVEL_CONSTRUCTIONS:
        for n_levels in LEVEL_COUNTS:
            values = by_cell.get((construction, n_levels))
            if not values:
                continue
            sd = statistics.stdev(values) if len(values) > 1 else 0.0
            print(f"{construction:<20} {n_levels:>4} {statistics.fmean(values):>10.4f} "
                  f"{sd:>8.4f} {len(values):>3}")

    baseline = by_cell.get(BASELINE_CELL)
    if not baseline:
        print("\nbaseline cell missing — cannot evaluate the registered bands")
        return
    base = statistics.fmean(baseline)
    print(f"\nbaseline cell {BASELINE_CELL[0]}/Q={BASELINE_CELL[1]}: {base:.4f}")

    ranked = sorted(((statistics.fmean(v), k) for k, v in by_cell.items()),
                    reverse=True)
    print("\nranking (best first):")
    for value, (construction, n_levels) in ranked:
        print(f"  {value:.4f}  {construction}/Q={n_levels}  "
              f"({100 * (value - base):+.2f} pp vs baseline)")

    best_value, best_cell = ranked[0]
    gain = 100 * (best_value - base)
    band = ("erklaert" if gain >= 5.43 else
            "teilweise erklaert" if gain >= 2.00 else "nicht erklaert")
    print(f"\nbest cell: {best_cell[0]}/Q={best_cell[1]} at {best_value:.4f}, "
          f"{gain:+.2f} pp -> registered band: {band}")

    # Negative control: random_levels must lose to progressive at equal Q.
    print("\nnegative control (random_levels must be worse than progressive):")
    for n_levels in LEVEL_COUNTS:
        random_cell = by_cell.get(("random_levels", n_levels))
        ordered_cell = by_cell.get(("progressive", n_levels))
        if not (random_cell and ordered_cell):
            continue
        r, p = statistics.fmean(random_cell), statistics.fmean(ordered_cell)
        verdict = "ok" if r < p else "VIOLATED"
        print(f"  Q={n_levels:>3}: random {r:.4f} vs progressive {p:.4f}  -> {verdict}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--D", dest="dimension", type=int, default=4_000)
    parser.add_argument("--results-dir", type=str, required=True)
    parser.add_argument("--train-batch", type=int, default=DEFAULT_TRAIN_BATCH)
    parser.add_argument("--test-batch", type=int, default=DEFAULT_TEST_BATCH)
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--progress-log", type=str, default=None,
                        help="append one line per finished cell here")
    parser.add_argument("--commit", action="store_true",
                        help="commit and push each finished cell")
    parser.add_argument("--no-resume", action="store_true",
                        help="run every cell even if a record already exists")
    args = parser.parse_args(argv)

    results_dir = Path(args.results_dir)
    log_path = Path(args.progress_log) if args.progress_log else None
    cells = list(itertools.product(LEVEL_CONSTRUCTIONS, LEVEL_COUNTS, SWEEP_SEEDS))
    print(f"E2 sweep: {len(LEVEL_CONSTRUCTIONS)} constructions x "
          f"{len(LEVEL_COUNTS)} level counts x {len(SWEEP_SEEDS)} seeds "
          f"= {len(cells)} runs at D={args.dimension}")
    print(f"canonical environment: {is_canonical_environment()}")

    existing = {} if args.no_resume else load_existing(results_dir, args.dimension)
    print(f"records already present in {results_dir}: {len(existing)} of {len(cells)}",
          flush=True)

    rows: list[dict[str, Any]] = []
    for index, (construction, n_levels, seed) in enumerate(cells, start=1):
        done = existing.get((construction, n_levels, seed))
        if done is not None:
            rows.append(done)
            print(f"[{index:>2}/{len(cells)}] {construction:<20} Q={n_levels:<3} "
                  f"seed={seed:<5} skipped, record exists "
                  f"({done['from_record']})", flush=True)
            continue

        row = run_cell(construction, n_levels, seed, args.dimension,
                       results_dir, args.train_batch,
                       args.test_batch, args.allow_download)
        rows.append(row)
        print(f"[{index:>2}/{len(cells)}] {construction:<20} Q={n_levels:<3} "
              f"seed={seed:<5} acc={row['accuracy']:.4f} "
              f"f1={row['macro_f1']:.4f} ({row['wall_seconds']:.0f}s)",
              flush=True)

        if log_path is not None:
            append_progress(log_path, index, len(cells), row)
        if args.commit:
            paths = [row["record_path"]] + ([log_path] if log_path else [])
            persist(paths, f"E2-Sweep {index}/{len(cells)}: {construction} "
                           f"Q={n_levels} seed={seed}")

    report(rows)
    if not is_canonical_environment():
        print("\ntiming and memory are not official on this environment "
              "(docs/PROTOCOL.md rule 2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
