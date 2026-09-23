"""Choose the fusion configuration on a validation split — never on test.

    python -m experiments.tune_fusion --task mnist --seed 42

``docs/D2_SPEC.md`` §3 makes λe, λp (and θ₀) the task-specific fit
parameters, "gefittet auf deklariertem Validierungssplit". This harness is
that step, made explicit and recorded:

1. Carve the validation split out of the **training** data (MNIST: the last
   10,000 of the official 60,000; few-shot text tasks: training examples
   that are *not* among the shots).
2. Learn T1 on the remainder, once.
3. Compute retrieval once — leave-one-out neighbours for the training part,
   plain neighbours for the validation part. Retrieval does not depend on
   θ₀, λ or the utilities, so every grid cell reuses it.
4. For every cell of the grid, fork the T1 state, run T2, score validation.
5. Write every cell to ``results/tuning/`` and name the winner.

The test split is not loaded at all. The winner is chosen by validation
accuracy; exact ties go to the simpler cell (fewer T2 epochs, then λe = 1,
then θ₀ = 0), which is the order the grid is written in.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from data.intents import load_banking77, load_clinc150
from data.loaders import _select_shots, load_mnist, load_wili
from engramm.core import ItemMemory
from engramm.encoders import PixelThermometerEncoder, build_encoder
from engramm.memory import Engramm, FusionConfig
from engramm.repro import collect_environment, git_revision, set_all_seeds
from experiments.common import encode_cached, holdout_per_class, holdout_tail

TEXT_LOADERS = {"wili": load_wili, "banking77": load_banking77,
                "clinc150": load_clinc150}

TUNING_DIR = Path(__file__).resolve().parent.parent / "results" / "tuning"


def _parse_floats(text: str) -> list[float]:
    return [float(x) for x in text.split(",") if x.strip()]


def _parse_ints(text: str) -> list[int]:
    return [int(x) for x in text.split(",") if x.strip()]


def prepare_mnist(seed: int, dimension: int, validation: int) -> dict[str, Any]:
    """Encode MNIST training data and split off the validation tail."""
    dataset = load_mnist(allow_download=True)
    encoder = PixelThermometerEncoder(ItemMemory(seed, dimension))
    packed = encode_cached(encoder, dataset.x_train)
    fit, val = holdout_tail(dataset.n_train, validation)
    labels = [dataset.labels[i] for i in dataset.y_train]
    return {
        "encoder": repr(encoder),
        "fit_keys": packed[fit], "fit_labels": [labels[i] for i in fit],
        "val_keys": packed[val], "val_labels": [labels[i] for i in val],
        "split": f"last {validation} of the official training split",
    }


def prepare_text(task: str, seed: int, dimension: int, shots: int,
                 per_class: int, lowercase: bool) -> dict[str, Any]:
    """Few-shot text task: the run's shots, validation from outside them.

    The shots are drawn exactly as the benchmark run draws them — the first
    use of ``set_all_seeds(seed)`` — so the configuration is tuned on the
    very training set the final run will learn. Validation examples come
    from training data outside the shots (CLINC150: its official
    validation split), never from test.
    """
    rng = set_all_seeds(seed)
    full = TEXT_LOADERS[task](allow_download=True)
    shot_idx = _select_shots(full.y_train, shots, full.n_classes, rng)
    if task == "clinc150":
        val_set = load_clinc150(split="val", allow_download=True)
        val_texts = list(val_set.x_test)
        val_labels = [val_set.labels[i] for i in val_set.y_test]
        split = "official CLINC150 validation split (3,000)"
    else:
        val_idx = holdout_per_class(full.y_train, shot_idx, per_class,
                                    np.random.default_rng([seed, 1]))
        val_texts = [full.x_train[i] for i in val_idx]
        val_labels = [full.labels[full.y_train[i]] for i in val_idx]
        split = f"{per_class} per class from training examples outside the shots"
    options = {"lowercase": True} if lowercase else {}
    encoder = build_encoder(task, ItemMemory(seed, dimension), **options)
    fit_texts = [full.x_train[i] for i in shot_idx]
    return {
        "encoder": repr(encoder),
        "encoder_options": options,
        "fit_keys": encode_cached(encoder, fit_texts, verbose=False),
        "fit_labels": [full.labels[full.y_train[i]] for i in shot_idx],
        "val_keys": encode_cached(encoder, val_texts, verbose=False),
        "val_labels": val_labels,
        "split": split,
    }


def sweep(data: dict[str, Any], seed: int, dimension: int, k: int,
          grid: list[dict[str, Any]], t2_local: bool) -> list[dict[str, Any]]:
    started = time.perf_counter()
    base = Engramm(dimension, seed, FusionConfig(k=k, t2_local=t2_local))
    positions = base.learn(data["fit_keys"], data["fit_labels"])
    print(f"  T1 on {len(positions)} examples ({time.perf_counter() - started:.0f}s)",
          flush=True)

    marker = time.perf_counter()
    fit_neighbours = base.retrieve(data["fit_keys"], exclude=positions)
    val_neighbours = base.retrieve(data["val_keys"])
    print(f"  retrieval: leave-one-out for {len(positions)} + "
          f"{len(data['val_labels'])} validation ({time.perf_counter() - marker:.0f}s)",
          flush=True)

    index = {label: i for i, label in enumerate(base.labels)}
    y_val = np.array([index[label] for label in data["val_labels"]])

    rows = []
    for cell in grid:
        marker = time.perf_counter()
        config = FusionConfig(k=k, theta0=cell["theta0"], lambda_e=cell["lambda_e"],
                              lambda_p=1.0, t2_local=t2_local)
        model = base.fork(config)
        errors = model.refine(data["fit_keys"], data["fit_labels"], cell["t2_epochs"],
                              rng=np.random.default_rng(seed),
                              neighbours=fit_neighbours)
        proto = model.prototypes.score(data["val_keys"])
        if config.lambda_e > 0:
            scores = model.fuse(proto, *val_neighbours)
        else:
            scores = config.lambda_p * proto
        predicted = model.argmax(scores)
        row = {**cell, "val_accuracy": float(np.mean(predicted == y_val)),
               "t2_errors": [round(e, 5) for e in errors],
               "seconds": round(time.perf_counter() - marker, 1)}
        rows.append(row)
        print(f"  θ0={cell['theta0']:<5} λe={cell['lambda_e']:<5} "
              f"T2={cell['t2_epochs']}  val_acc={row['val_accuracy']:.4f}  "
              f"T2-errors={row['t2_errors']}  ({row['seconds']}s)", flush=True)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", choices=["mnist", "wili", "banking77", "clinc150"],
                        required=True)
    parser.add_argument("--shots", type=int, default=10,
                        help="text tasks: training examples per class")
    parser.add_argument("--val-per-class", type=int, default=20)
    parser.add_argument("--lowercase", default="0",
                        help="intent tasks: comma list of 0/1 encoder variants to try")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--D", dest="dimension", type=int, default=10_000)
    parser.add_argument("--validation", type=int, default=10_000)
    parser.add_argument("--k", type=int, default=32)
    parser.add_argument("--theta0", default="0,0.05,0.1,0.15,0.2")
    parser.add_argument("--lambda-e", default="0,0.25,0.5,1,2,4")
    parser.add_argument("--t2-epochs", default="0,2")
    parser.add_argument("--t2-local", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    git_state = git_revision()
    set_all_seeds(args.seed)
    print(f"tuning {args.task}, seed {args.seed}, D={args.dimension} — test split not "
          f"used", flush=True)
    variants = [bool(int(v)) for v in args.lowercase.split(",")] if args.task in (
        "banking77", "clinc150") else [False]

    grid = []
    for epochs, lambda_e, theta0 in itertools.product(
            _parse_ints(args.t2_epochs), _parse_floats(args.lambda_e),
            _parse_floats(args.theta0)):
        if lambda_e == 0 and theta0 != _parse_floats(args.theta0)[0]:
            continue           # θ0 is irrelevant without episodes
        grid.append({"t2_epochs": epochs, "lambda_e": lambda_e, "theta0": theta0})

    rows = []
    for lowercase in variants:
        if args.task == "mnist":
            data = prepare_mnist(args.seed, args.dimension, args.validation)
        else:
            data = prepare_text(args.task, args.seed, args.dimension, args.shots,
                                args.val_per_class, lowercase)
        print(f"  encoder {data['encoder']}: {len(data['fit_labels'])} fit / "
              f"{len(data['val_labels'])} validation", flush=True)
        for row in sweep(data, args.seed, args.dimension, args.k, grid, args.t2_local):
            rows.append({**row, "encoder_options": data.get("encoder_options", {}),
                         "encoder": data["encoder"]})
    best = max(rows, key=lambda r: r["val_accuracy"])     # first max = simplest
    record = {
        "task": args.task, "seed": args.seed, "dimension": args.dimension,
        "shots": args.shots if args.task != "mnist" else None,
        "k": args.k, "t2_local": args.t2_local, "validation": data["split"],
        "encoder": best["encoder"], "test_split_used": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": git_state, "environment": collect_environment(),
        "grid": rows, "selected": best,
    }
    name = f"{args.task}_seed{args.seed}" + (f"_{args.shots}shot" if args.task != "mnist" else "")
    out = Path(args.out) if args.out else TUNING_DIR / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"\nselected: {best}\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
