"""M5 — ENGRAMM side of the showdown against local LLM baselines.

    python -m experiments.m5_engramm --task banking77 --seed 42

Everything ENGRAMM contributes to the M5 comparison is measured **on the M5
task itself**. The historical run filled two of the four criteria with
constants from other experiments — energy from M0 (27.4 mJ, a 10^6-key HNSW
query) and interference forgetting from M3 (+0.20 pp, a 6 % accuracy regime)
— so its "efficiency dominance" was partly not measured. Here:

1. **Accuracy** — 10 shots per class, all classes, official test split;
   configuration from ``results/tuning/<task>_seed42_10shot.json`` (chosen on
   validation, ``t2_local=True`` as registered for M5 by the V2 ratification).
2. **Learning time per class** — wall clock of T1 (+ T2) over the shots,
   divided by the number of classes. Container figure: not official.
3. **Query latency** — wall clock per test query, streamed one at a time.
4. **Interference forgetting (V2)** on the M5 task: the classes arrive in the
   same tranches the LoRA baseline B3 uses (7 for Banking77, 10 for
   CLINC150); tranche-1 accuracy after the last tranche, T1-only minus the
   configuration under test (its own T2 epochs, t2_local). Also the
   classical V1 figure (tranche-1 accuracy after tranche 1 minus after the
   last) for comparability with B3, and a stress variant with two forced
   T2 epochs, recorded but not the criterion.
5. **Energy** — not measurable in this container (no power interface).
   Recorded as ``null``; a CPU-seconds-per-query proxy is recorded next to it
   and labelled as a proxy.

It also writes the exact few-shot split (training indices and a digest of
the test labels) to ``results/m5/split_<task>_seed<seed>.json`` — the only
contact point to the baselines, which run in their own environment
(``.venv_b1``) and must see the very same examples.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from data.intents import load_banking77, load_clinc150
from data.loaders import _select_shots
from engramm.core import ItemMemory
from engramm.encoders import build_encoder
from engramm.memory import Engramm, FusionConfig
from engramm.repro import collect_environment, git_revision, set_all_seeds
from experiments.energy import measure_energy

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "m5"
LOADERS = {"banking77": load_banking77, "clinc150": load_clinc150}
#: Tranche counts used by the historical B3 (7 for < 100 classes, else 10).
TRANCHES = {"banking77": 7, "clinc150": 10}


def tranche_blocks(classes: list[str], n_tranches: int) -> list[list[str]]:
    """Consecutive blocks of sorted class names — identical to B3's split."""
    per = max(1, len(classes) // n_tranches)
    blocks = [classes[t * per:(t + 1) * per] for t in range(n_tranches - 1)]
    blocks.append(classes[(n_tranches - 1) * per:])
    return blocks


def write_split(task: str, seed: int, shots: int, out_dir: Path) -> dict[str, Any]:
    """Draw the shots exactly as every M5 system must see them, and record them."""
    rng = set_all_seeds(seed)
    full = LOADERS[task](allow_download=True)
    shot_idx = _select_shots(full.y_train, shots, full.n_classes, rng)
    split = {
        "task": task, "seed": seed, "shots": shots,
        "train_indices": [int(i) for i in shot_idx],
        "labels": list(full.labels),
        "n_test": full.n_test,
        "test_labels_sha256": hashlib.sha256(
            "\n".join(full.labels[y] for y in full.y_test).encode()).hexdigest(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"split_{task}_seed{seed}.json").write_text(json.dumps(split) + "\n")
    return split


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", choices=sorted(LOADERS), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--shots", type=int, default=10)
    parser.add_argument("--D", dest="dimension", type=int, default=10_000)
    parser.add_argument("--config-from", default=None)
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = parser.parse_args(argv)

    git_state = git_revision()
    out_dir = Path(args.results_dir)
    tuning_path = Path(args.config_from or
                       f"results/tuning/{args.task}_seed42_{args.shots}shot.json")
    tuning = json.loads(tuning_path.read_text(encoding="utf-8"))
    if tuning.get("test_split_used", True):
        raise SystemExit(f"{tuning_path} does not certify test_split_used=false")
    sel = tuning["selected"]
    config = FusionConfig(k=tuning["k"], theta0=sel["theta0"], lambda_e=sel["lambda_e"],
                          t2_local=True)
    t2_epochs = sel["t2_epochs"]

    split = write_split(args.task, args.seed, args.shots, out_dir)
    full = LOADERS[args.task](allow_download=True)
    shot_idx = np.array(split["train_indices"])
    train_texts = [full.x_train[i] for i in shot_idx]
    train_labels = [full.labels[full.y_train[i]] for i in shot_idx]
    encoder = build_encoder(args.task, ItemMemory(args.seed, args.dimension),
                            **sel.get("encoder_options", {}))

    # 1 + 2: accuracy and learning time (encoding counts: it is part of learning)
    marker = time.perf_counter()
    cpu = time.process_time()
    model = Engramm(args.dimension, args.seed, config)
    train_keys = encoder.encode(train_texts)
    positions = model.learn(train_keys, train_labels)
    model.refine(train_keys, train_labels, t2_epochs, rng=np.random.default_rng(args.seed),
                 episode_positions=positions)
    learn_wall = time.perf_counter() - marker
    learn_cpu = time.process_time() - cpu

    test_texts = list(full.x_test)
    y_test = full.y_test
    position = {label: i for i, label in enumerate(full.labels)}
    lookup = np.array([position[l] for l in model.labels])
    predicted = lookup[model.predict(encoder.encode(test_texts))]
    accuracy = float(np.mean(predicted == y_test))

    # 3: per-query latency, one query at a time (encode + retrieve + fuse)
    latencies, cpu_per_query = [], []
    for text in test_texts[:500]:
        marker, cpu = time.perf_counter(), time.process_time()
        model.predict(encoder.encode([text]))
        latencies.append((time.perf_counter() - marker) * 1e3)
        cpu_per_query.append(time.process_time() - cpu)

    # 5: energy per query over the same 500 single queries, where measurable
    probe = iter(range(10**9))
    energy = measure_energy(
        lambda: model.predict(encoder.encode([test_texts[next(probe) % 500]])), 500)

    # 4: forgetting over the same class tranches as B3
    blocks = tranche_blocks(list(full.labels), TRANCHES[args.task])
    first = set(blocks[0])
    first_mask = np.array([full.labels[y] in first for y in y_test])
    test_keys = encoder.encode(test_texts)

    def sequential(t2_local: bool, epochs: int) -> tuple[float, float]:
        cfg = FusionConfig(k=config.k, theta0=config.theta0, lambda_e=config.lambda_e,
                           t2_local=t2_local)
        m = Engramm(args.dimension, args.seed, cfg)
        rng = np.random.default_rng([args.seed, 6])
        after_first = None
        for t, block in enumerate(blocks):
            members = set(block)
            idx = [i for i, l in enumerate(train_labels) if l in members]
            pos = m.learn(train_keys[idx], [train_labels[i] for i in idx])
            if epochs:
                m.refine(train_keys[idx], [train_labels[i] for i in idx], epochs,
                         rng=rng, episode_positions=pos)
            if t == 0:
                look = np.array([position[l] for l in m.labels])
                after_first = float(np.mean(look[m.predict(test_keys[first_mask])]
                                            == y_test[first_mask]))
        look = np.array([position[l] for l in m.labels])
        final = float(np.mean(look[m.predict(test_keys[first_mask])] == y_test[first_mask]))
        return after_first, final

    # Criterion 4 is measured on the configuration whose accuracy is judged:
    # if validation chose no T2, the system has no T2 and its interference is
    # zero by construction. A stress variant with two forced T2 epochs is
    # recorded next to it — informative, not the criterion.
    t1_first, t1_final = sequential(False, 0)
    loc_first, loc_final = sequential(True, t2_epochs)
    stress_first, stress_final = sequential(True, 2)

    record = {
        "task": args.task, "system": "engramm", "seed": args.seed, "shots": args.shots,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {**git_state, "captured": "before_run"},
        "n_classes": full.n_classes, "n_test": full.n_test,
        "acc": accuracy,
        "predictions_sha256": hashlib.sha256(
            "\n".join(full.labels[p] for p in predicted).encode()).hexdigest(),
        "learn_ms_per_class_wall": learn_wall / full.n_classes * 1e3,
        "learn_ms_per_class_cpu": learn_cpu / full.n_classes * 1e3,
        "query_ms_mean": float(np.mean(latencies)),
        "query_ms_p99": float(np.percentile(latencies, 99)),
        "cpu_seconds_per_query_proxy": float(np.mean(cpu_per_query)),
        "energy_mj_per_query": energy["mj_per_call"],
        "energy": energy,
        "forgetting": {
            "tranches": len(blocks), "first_block_classes": len(blocks[0]),
            "t1_only_block_after_first": t1_first, "t1_only_block_final": t1_final,
            "t2_local_block_after_first": loc_first, "t2_local_block_final": loc_final,
            "t2_epochs": t2_epochs,
            "interference_v2_pp": (t1_final - loc_final) * 100,
            "classical_v1_pp": (loc_first - loc_final) * 100,
            "stress_t2_epochs": 2,
            "stress_interference_v2_pp": (t1_final - stress_final) * 100,
            "stress_classical_v1_pp": (stress_first - stress_final) * 100,
        },
        "config": {**config.to_dict(), "t2_epochs": t2_epochs,
                   "encoder": repr(encoder), "config_source": str(tuning_path)},
        "environment": collect_environment(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"m5_engramm_{args.task}_seed{args.seed}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("task", "acc", "learn_ms_per_class_wall",
                                              "query_ms_mean")}, indent=None))
    print(f"forgetting: {record['forgetting']}\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
