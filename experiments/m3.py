"""M3 — 1,000 authors learned strictly sequentially (the core claim).

    python -m experiments.m3 --seed 42

Protocol (D5 §4, choices in ``docs/DEVIATIONS.md`` GAP-10):

* 1,000 authors of the Blog Authorship Corpus, 10 training posts, 10 test
  posts and 5 validation posts each, drawn with the run's seed.
* The authors arrive in 10 tranches of 100 (seeded order). Each tranche is
  learned with T1 and — depending on the variant — refined with T2 on its
  own posts. After every tranche all authors seen so far are evaluated.
* The fusion configuration is chosen once on the **validation** posts
  (T1 over all 1,000 authors, grid over λe, θ₀, T2 epochs) and then held
  fixed for every variant. Test posts are not used for the choice.

Variants: ``full`` (T1 + T2), ``t1_only`` (no T2), ``t2_local`` (T2 moves only
the true class — the D2 §4 fallback).

Measured:

* **Forgetting, registered metric** (V1): accuracy on the tranche-1 block
  right after tranche 1 minus after tranche 10.
* **Interference forgetting** (V2, ratified 2026-07-06): tranche-1 block
  accuracy after tranche 10, T1-only minus the variant. Criterion ≤ 1 pp.
* Absolute top-1 / top-5 at 1,000 authors; the acc(K) curve.
* **State invariance:** T1 built tranche by tranche vs. all posts at once in
  a shuffled order — identical state digest?
* **Readout invariance:** identical predictions for the two orders? (W19)
* **Reconstruction:** the ``full`` run is logged to L2; replay must give the
  same state and the same test hits.
* Learning time per class (container: not official).
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

from data.blogs import load_blogs
from engramm.core import ItemMemory
from engramm.encoders import TrigramEncoder
from engramm.memory import Engramm, FusionConfig
from engramm.persistence import EventLog, replay
from engramm.repro import collect_environment, git_revision, set_all_seeds
from experiments.common import encode_cached

N_AUTHORS = 1_000
TRANCHES = 10
SHOTS = 10
TEST_PER_AUTHOR = 10
VALIDATION_PER_AUTHOR = 5
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "m3"

GRID = {"lambda_e": (0.0, 0.25, 0.5, 1.0, 2.0), "theta0": (0.0, 0.1, 0.2, 0.3),
        "t2_epochs": (0, 2)}


def prepare(seed: int, dimension: int, n_authors: int = N_AUTHORS) -> dict[str, Any]:
    rng = set_all_seeds(seed)
    data = load_blogs(n_authors, SHOTS, TEST_PER_AUTHOR, rng,
                      validation_per_author=VALIDATION_PER_AUTHOR)
    encoder = TrigramEncoder(ItemMemory(seed, dimension))
    tranche_order = rng.permutation(n_authors)
    size = n_authors // TRANCHES
    labels = data.labels
    return {
        "encoder": repr(encoder),
        "labels": labels,
        "train_keys": encode_cached(encoder, data.x_train, batch=2_000, verbose=False),
        "train_labels": [labels[y] for y in data.y_train],
        "y_train": data.y_train,
        "test_keys": encode_cached(encoder, data.x_test, batch=2_000, verbose=False),
        "y_test": data.y_test,
        "val_keys": encode_cached(encoder, data.metadata["x_validation"], batch=2_000,
                                  verbose=False),
        "y_val": data.metadata["y_validation"],
        "tranches": [np.sort(tranche_order[t * size:(t + 1) * size])
                     for t in range(TRANCHES)],
        "n_authors": n_authors,
        "eligible_authors": data.metadata["eligible_authors"],
    }


def _as_dataset_index(model: Engramm, predicted: np.ndarray, labels: tuple[str, ...]) -> np.ndarray:
    position = {label: i for i, label in enumerate(labels)}
    lookup = np.array([position[label] for label in model.labels], dtype=np.int64)
    return lookup[predicted]


def choose_config(prep: dict[str, Any], seed: int, dimension: int) -> tuple[dict, list]:
    """Validation sweep with T1 over all authors; returns (selected, grid rows)."""
    base = Engramm(dimension, seed, FusionConfig())
    positions = base.learn(prep["train_keys"], prep["train_labels"])
    fit_nb = base.retrieve(prep["train_keys"], exclude=positions)
    val_nb = base.retrieve(prep["val_keys"])
    rows = []
    for epochs, lambda_e, theta0 in itertools.product(
            GRID["t2_epochs"], GRID["lambda_e"], GRID["theta0"]):
        if lambda_e == 0 and theta0 != GRID["theta0"][0]:
            continue
        model = base.fork(FusionConfig(theta0=theta0, lambda_e=lambda_e))
        model.refine(prep["train_keys"], prep["train_labels"], epochs,
                     rng=np.random.default_rng(seed), neighbours=fit_nb)
        proto = model.prototypes.score(prep["val_keys"])
        scores = model.fuse(proto, *val_nb) if lambda_e > 0 else proto
        predicted = _as_dataset_index(model, model.argmax(scores), prep["labels"])
        rows.append({"t2_epochs": epochs, "lambda_e": lambda_e, "theta0": theta0,
                     "val_accuracy": float(np.mean(predicted == prep["y_val"]))})
    best = max(rows, key=lambda r: r["val_accuracy"])
    return best, rows


def run_sequential(prep: dict[str, Any], seed: int, dimension: int, config: FusionConfig,
                   t2_epochs: int, log_path: Path | None = None) -> dict[str, Any]:
    """Learn tranche by tranche; evaluate every seen author after each tranche."""
    log = EventLog(log_path) if log_path is not None else None
    model = Engramm(dimension, seed, config, log=log)
    rng = np.random.default_rng([seed, 4])
    y_train, y_test = prep["y_train"], prep["y_test"]
    first_block = np.isin(y_test, prep["tranches"][0])
    seen = np.zeros(prep["n_authors"], dtype=bool)
    curve, block, learn_seconds = [], [], 0.0
    for tranche in prep["tranches"]:
        idx = np.flatnonzero(np.isin(y_train, tranche))
        marker = time.process_time()
        positions = model.learn(prep["train_keys"][idx], [prep["train_labels"][i] for i in idx])
        if t2_epochs:
            model.refine(prep["train_keys"][idx], [prep["train_labels"][i] for i in idx],
                         t2_epochs, rng=rng, episode_positions=positions)
        learn_seconds += time.process_time() - marker
        seen[tranche] = True
        mask = seen[y_test]
        predicted = _as_dataset_index(model, model.predict(prep["test_keys"][mask]),
                                      prep["labels"])
        curve.append(float(np.mean(predicted == y_test[mask])))
        block_predicted = _as_dataset_index(model, model.predict(prep["test_keys"][first_block]),
                                            prep["labels"])
        block.append(float(np.mean(block_predicted == y_test[first_block])))
    if log is not None:
        log.close()

    scores = model.scores(prep["test_keys"])
    order = np.array(sorted(range(model.n_classes), key=lambda i: model.labels[i]))
    top5_model = np.argsort(-scores[:, order], axis=1, kind="stable")[:, :5]
    top5 = _as_dataset_index(model, order[top5_model].ravel(), prep["labels"]).reshape(-1, 5)
    predicted = _as_dataset_index(model, model.predict(prep["test_keys"]), prep["labels"])
    return {
        "model": model,
        "acc_curve": curve,
        "block_curve": block,
        "top1": float(np.mean(predicted == y_test)),
        "top5": float(np.mean((top5 == y_test[:, None]).any(axis=1))),
        "hits": int(np.sum(predicted == y_test)),
        "forgetting_v1_pp": (block[0] - block[-1]) * 100,
        "learn_ms_per_class_not_official": learn_seconds / prep["n_authors"] * 1e3,
        "predictions": predicted,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--D", dest="dimension", type=int, default=10_000)
    parser.add_argument("--authors", type=int, default=N_AUTHORS)
    parser.add_argument("--work-dir", default="logs/m3")
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = parser.parse_args(argv)

    git_state = git_revision()
    started = time.perf_counter()
    prep = prepare(args.seed, args.dimension, args.authors)
    print(f"{args.authors} authors (of {prep['eligible_authors']} eligible), "
          f"{len(prep['train_labels'])} train / {len(prep['y_test'])} test / "
          f"{len(prep['y_val'])} validation posts", flush=True)

    selected, grid = choose_config(prep, args.seed, args.dimension)
    print(f"selected on validation: {selected}", flush=True)
    # The variants compare T2 against no T2, so they need T2 epochs even if
    # validation preferred none; then the recorded default of 2 is used.
    epochs = selected["t2_epochs"] or 2
    config = FusionConfig(theta0=selected["theta0"], lambda_e=selected["lambda_e"])
    local = FusionConfig(theta0=selected["theta0"], lambda_e=selected["lambda_e"],
                         t2_local=True)

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    log_path = work / f"m3_seed{args.seed}.log"
    log_path.unlink(missing_ok=True)

    variants = {
        "full": run_sequential(prep, args.seed, args.dimension, config, epochs, log_path),
        "t1_only": run_sequential(prep, args.seed, args.dimension, config, 0),
        "t2_local": run_sequential(prep, args.seed, args.dimension, local, epochs),
    }
    t1_block_final = variants["t1_only"]["block_curve"][-1]
    for name, v in variants.items():
        v["interference_v2_pp"] = (t1_block_final - v["block_curve"][-1]) * 100
        print(f"{name}: top1 {v['top1']:.4f} top5 {v['top5']:.4f} "
              f"forgetting(V1) {v['forgetting_v1_pp']:+.2f} pp "
              f"interference(V2) {v['interference_v2_pp']:+.2f} pp", flush=True)

    # State and readout invariance (T1): tranche order vs. one shuffled batch.
    sequential = variants["t1_only"]["model"]
    shuffled = Engramm(args.dimension, args.seed, config)
    order = np.random.default_rng([args.seed, 5]).permutation(len(prep["train_labels"]))
    shuffled.learn(prep["train_keys"][order], [prep["train_labels"][i] for i in order])
    state_equal = sequential.state_digest() == shuffled.state_digest()
    readout_a = _as_dataset_index(sequential, sequential.predict(prep["test_keys"]), prep["labels"])
    readout_b = _as_dataset_index(shuffled, shuffled.predict(prep["test_keys"]), prep["labels"])
    readout_equal = bool(np.array_equal(readout_a, readout_b))

    # Reconstruction from L2.
    rebuilt, report = replay(log_path)
    rebuilt_predicted = _as_dataset_index(rebuilt, rebuilt.predict(prep["test_keys"]),
                                          prep["labels"])
    reconstruction = {
        "events": report.events_applied,
        "state_equal": rebuilt.state_digest() == variants["full"]["model"].state_digest(),
        "hits_live": variants["full"]["hits"],
        "hits_replayed": int(np.sum(rebuilt_predicted == prep["y_test"])),
        "predictions_equal": bool(np.array_equal(rebuilt_predicted,
                                                 variants["full"]["predictions"])),
    }

    record = {
        "task": "m3_sequential_authors", "seed": args.seed,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {**git_state, "captured": "before_run"},
        "setup": {"dimension": args.dimension, "authors": args.authors, "tranches": TRANCHES,
                  "shots": SHOTS, "test_per_author": TEST_PER_AUTHOR,
                  "validation_per_author": VALIDATION_PER_AUTHOR,
                  "encoder": prep["encoder"], "eligible_authors": prep["eligible_authors"],
                  "t2_epochs_in_variants": epochs},
        "validation_sweep": {"selected": selected, "grid": grid, "test_split_used": False},
        "variants": {name: {k: v for k, v in data.items()
                            if k not in ("model", "predictions")}
                     for name, data in variants.items()},
        "invariance": {"state_equal": state_equal, "readout_equal": readout_equal,
                       "readout_differences": int(np.sum(readout_a != readout_b))},
        "reconstruction": reconstruction,
        "runtime": {"wall_seconds": time.perf_counter() - started},
        "environment": collect_environment(),
    }
    out = Path(args.results_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"m3_{args.seed}_{stamp}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"invariance: state {state_equal}, readout {readout_equal}\n"
          f"reconstruction: {reconstruction}\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
