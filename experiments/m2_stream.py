"""M2a — stream learning with T3 consolidation by similarity absorption.

    python -m experiments.m2_stream --seed 42

Protocol (recovered from D4/D5, choices in ``docs/DEVIATIONS.md`` GAP-11):

* **Stream.** 50,000 items: the complete Banking77 training split (10,003
  utterances, labels ``b77:<intent>``) plus 39,997 WiLI-2018 training
  paragraphs drawn with the run's seed (``wili:<language>``), interleaved in
  a seeded random order.
* **Learning.** The stream arrives in chunks of 2,000. Each chunk is learned
  with T1 (episodes + accumulators) and then refined with one leave-one-out
  T2 epoch, which also gives the episodes their utilities.
* **T3.** Run B consolidates after every chunk: episodes with
  ``sim(key, P[class]) > θ_merge`` and ``util < 2`` are absorbed (removed; the
  accumulator already contains them). Run A never consolidates.
* **Evaluation.** 5,430 queries: the Banking77 test split (3,080) plus ten
  WiLI test paragraphs per language (2,350), drawn with the seed.

Registered M2a criterion (D5 §3), an AND: compression ≥ 5× (≤ 20 % of the
episodes kept) ∧ accuracy loss ≤ 1.0 pp ∧ T3 CPU share ≤ 10 %. The θ sweep
(0.20, 0.28, 0.35) is the registered no-go path.

Secondary: T2 ablation — run A with and without T2 — reported on the
Banking77 part of the evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from data.intents import load_banking77
from data.loaders import load_wili
from engramm.core import ItemMemory
from engramm.encoders import TrigramEncoder
from engramm.memory import Engramm, FusionConfig
from engramm.repro import collect_environment, git_revision, set_all_seeds
from experiments.common import encode_cached

STREAM_SIZE = 50_000
CHUNK = 2_000
WILI_EVAL_PER_LANGUAGE = 10
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "m2"

#: Fusion for the stream runs: the historical defaults (λe = λp = 1,
#: θ₀ = 0). M2 compares runs *with* and *without* consolidation under one
#: configuration, so the configuration is held fixed, not tuned.
STREAM_CONFIG = FusionConfig(k=32, theta0=0.0, lambda_e=1.0, lambda_p=1.0)


def build_stream(seed: int, dimension: int) -> dict[str, Any]:
    """Encode the 50k stream and the 5,430 evaluation queries, deterministically."""
    rng = set_all_seeds(seed)
    banking = load_banking77(allow_download=True)
    wili = load_wili(allow_download=True)

    n_wili = STREAM_SIZE - banking.n_train
    wili_idx = np.sort(rng.choice(wili.n_train, size=n_wili, replace=False))
    texts = list(banking.x_train) + [wili.x_train[i] for i in wili_idx]
    labels = ([f"b77:{banking.labels[y]}" for y in banking.y_train]
              + [f"wili:{wili.labels[wili.y_train[i]]}" for i in wili_idx])
    order = rng.permutation(len(texts))
    texts = [texts[i] for i in order]
    labels = [labels[i] for i in order]

    wili_eval = np.concatenate([
        np.sort(rng.choice(np.flatnonzero(wili.y_test == c), size=WILI_EVAL_PER_LANGUAGE,
                           replace=False))
        for c in range(wili.n_classes)])
    eval_texts = list(banking.x_test) + [wili.x_test[i] for i in wili_eval]
    eval_labels = ([f"b77:{banking.labels[y]}" for y in banking.y_test]
                   + [f"wili:{wili.labels[wili.y_test[i]]}" for i in wili_eval])

    encoder = TrigramEncoder(ItemMemory(seed, dimension))
    return {
        "encoder": repr(encoder),
        "keys": encode_cached(encoder, texts, batch=5_000, verbose=False),
        "labels": labels,
        "eval_keys": encode_cached(encoder, eval_texts, batch=5_000, verbose=False),
        "eval_labels": eval_labels,
        "n_banking": banking.n_train, "n_wili": int(n_wili),
    }


def evaluate(model: Engramm, keys: np.ndarray, labels: list[str]) -> dict[str, float]:
    predicted = [model.labels[i] for i in model.predict(keys)]
    hit = {"b77": [0, 0], "wili": [0, 0]}
    for p, t in zip(predicted, labels):
        source = t.split(":", 1)[0]
        hit[source][0] += int(p == t)
        hit[source][1] += 1
    total = sum(h[0] for h in hit.values()) / sum(h[1] for h in hit.values())
    return {"total": total,
            "b77": hit["b77"][0] / hit["b77"][1] if hit["b77"][1] else float("nan"),
            "wili": hit["wili"][0] / hit["wili"][1] if hit["wili"][1] else float("nan")}


def run_stream(stream: dict[str, Any], seed: int, dimension: int,
               theta_merge: float | None, t2: bool = True, log: Any = None,
               limit: int | None = None) -> tuple[Engramm, dict[str, Any]]:
    """Learn the stream chunk by chunk; consolidate after each chunk if θ is set."""
    model = Engramm(dimension, seed, STREAM_CONFIG, log=log)
    rng = np.random.default_rng([seed, 3])
    keys, labels = stream["keys"], stream["labels"]
    n = len(labels) if limit is None else min(limit, len(labels))
    learn_s = t3_s = 0.0
    absorbed = 0
    for start in range(0, n, CHUNK):
        stop = min(start + CHUNK, n)
        marker = time.process_time()
        positions = model.learn(keys[start:stop], labels[start:stop])
        if t2:
            model.refine(keys[start:stop], labels[start:stop], epochs=1, rng=rng,
                         episode_positions=positions)
        learn_s += time.process_time() - marker
        if theta_merge is not None:
            marker = time.process_time()
            absorbed += model.consolidate(theta_merge=theta_merge, util_max=2)
            t3_s += time.process_time() - marker
    stats = {"episodes_kept": len(model.episodes), "items": n, "absorbed": absorbed,
             "learn_cpu_seconds": learn_s, "t3_cpu_seconds": t3_s,
             "t3_cpu_share": t3_s / max(learn_s + t3_s, 1e-12)}
    return model, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--D", dest="dimension", type=int, default=10_000)
    parser.add_argument("--thetas", default="0.12,0.20,0.28,0.35")
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = parser.parse_args(argv)

    git_state = git_revision()
    started = time.perf_counter()
    stream = build_stream(args.seed, args.dimension)
    print(f"stream: {len(stream['labels'])} items ({stream['n_banking']} Banking77 + "
          f"{stream['n_wili']} WiLI), {len(stream['eval_labels'])} evaluation queries",
          flush=True)

    runs: dict[str, Any] = {}
    model, stats = run_stream(stream, args.seed, args.dimension, None, t2=True)
    runs["A_no_T3"] = {**stats, **evaluate(model, stream["eval_keys"], stream["eval_labels"])}
    baseline = runs["A_no_T3"]["total"]
    print(f"A (no T3): {runs['A_no_T3']}", flush=True)
    del model

    model, stats = run_stream(stream, args.seed, args.dimension, None, t2=False)
    runs["A_no_T3_no_T2"] = {**stats, **evaluate(model, stream["eval_keys"],
                                                  stream["eval_labels"])}
    print(f"A without T2: {runs['A_no_T3_no_T2']}", flush=True)
    del model

    for theta in [float(t) for t in args.thetas.split(",")]:
        model, stats = run_stream(stream, args.seed, args.dimension, theta, t2=True)
        row = {**stats, **evaluate(model, stream["eval_keys"], stream["eval_labels"])}
        row["compression"] = stats["items"] / max(stats["episodes_kept"], 1)
        row["delta_acc_pp"] = (row["total"] - baseline) * 100
        runs[f"B_theta_{theta}"] = row
        print(f"B θ={theta}: {row}", flush=True)
        del model

    primary = runs["B_theta_0.12"]
    criterion = {
        "compression_ge_5x": primary["compression"] >= 5,
        "delta_acc_le_1pp": primary["delta_acc_pp"] >= -1.0,
        "t3_cpu_share_le_10pct": primary["t3_cpu_share"] <= 0.10,
    }
    criterion["met"] = all(criterion.values())
    sweep_rescue = [k for k, r in runs.items() if k.startswith("B_theta")
                    and r["compression"] >= 5 and r["delta_acc_pp"] >= -1.0]
    record = {
        "task": "m2a_stream_consolidation", "seed": args.seed,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {**git_state, "captured": "before_run"},
        "setup": {"dimension": args.dimension, "stream_items": len(stream["labels"]),
                  "chunk": CHUNK, "encoder": stream["encoder"],
                  "config": STREAM_CONFIG.to_dict(), "util_max": 2,
                  "evaluation_queries": len(stream["eval_labels"])},
        "runs": runs,
        "criterion": criterion,
        "theta_meeting_both_compression_and_accuracy": sweep_rescue,
        "t2_ablation_b77_pp": (runs["A_no_T3"]["b77"] - runs["A_no_T3_no_T2"]["b77"]) * 100,
        "runtime": {"wall_seconds": time.perf_counter() - started},
        "environment": collect_environment(),
    }
    out = Path(args.results_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"m2a_{args.seed}_{stamp}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"M2a criterion met: {criterion['met']}  ({criterion})\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
