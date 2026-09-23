"""M2b — utility-based eviction and the L2 persistence gate.

    python -m experiments.m2b --seed 42

Registered in D5 v1.2 as the implementation of the M2a no-go endpoint
("T3 reduced to eviction"):

(a) **Characterisation, no gate.** Accuracy of the stream model after
    evicting the least useful episodes down to 80 / 50 / 20 % of the
    memory — one eviction after the stream, lowest utility first, ties by
    content id.

(b) **Persistence gate.** The L2 event log must reproduce the state
    exactly:

    * **full replay** of a logged run equals the live model — identical
      state digest and identical predictions on all evaluation queries;
    * **crash replay** of the log cut at 60 % of its bytes equals the state
      after the last complete event (the torn record is discarded);
    * additionally, at every chunk boundary of the live run, a replay
      limited to the events logged so far equals the live state at that
      moment — the log is faithful throughout, not only at its end.

    The logged run covers the first 20,000 stream items, as recorded.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from engramm.memory import Engramm
from engramm.persistence import EventLog, read_events, replay
from engramm.repro import collect_environment, git_revision
from experiments.m2_stream import (
    CHUNK,
    RESULTS_DIR,
    STREAM_CONFIG,
    build_stream,
    evaluate,
    run_stream,
)

RETENTION = (1.0, 0.8, 0.5, 0.2)
PERSISTENCE_ITEMS = 20_000
CUT_FRACTION = 0.6


def logged_run_with_checkpoints(stream, seed: int, dimension: int, log_path: Path,
                                limit: int) -> tuple[Engramm, list[tuple[int, str]]]:
    """The stream run of M2a (T1 + one T2 epoch per chunk, no T3), logged.

    Returns the live model and ``(events so far, state digest)`` after each
    chunk.
    """
    log = EventLog(log_path)
    model = Engramm(dimension, seed, STREAM_CONFIG, log=log)
    rng = np.random.default_rng([seed, 3])
    checkpoints = []
    for start in range(0, limit, CHUNK):
        stop = min(start + CHUNK, limit)
        positions = model.learn(stream["keys"][start:stop], stream["labels"][start:stop])
        model.refine(stream["keys"][start:stop], stream["labels"][start:stop], epochs=1,
                     rng=rng, episode_positions=positions)
        checkpoints.append((log.events_written, model.state_digest()))
    log.close()
    return model, checkpoints


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--D", dest="dimension", type=int, default=10_000)
    parser.add_argument("--work-dir", default="logs/m2b")
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = parser.parse_args(argv)

    git_state = git_revision()
    started = time.perf_counter()
    stream = build_stream(args.seed, args.dimension)
    eval_keys, eval_labels = stream["eval_keys"], stream["eval_labels"]

    # (a) eviction curve ---------------------------------------------------
    base, _ = run_stream(stream, args.seed, args.dimension, None, t2=True)
    curve = []
    for keep in RETENTION:
        model = base.fork()
        model.evict(int(round(len(base.episodes) * (1 - keep))))
        row = {"retained": keep, "episodes": len(model.episodes),
               **evaluate(model, eval_keys, eval_labels)}
        curve.append(row)
        print(f"retention {keep:.0%}: {row}", flush=True)
    for row in curve:
        row["delta_acc_pp"] = (row["total"] - curve[0]["total"]) * 100
    del base

    # (b) persistence gate ---------------------------------------------------
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    log_path = work / f"l2_seed{args.seed}.log"
    log_path.unlink(missing_ok=True)
    live, checkpoints = logged_run_with_checkpoints(
        stream, args.seed, args.dimension, log_path, PERSISTENCE_ITEMS)
    live_eval = evaluate(live, eval_keys, eval_labels)
    live_predictions = live.predict(eval_keys)

    marker = time.perf_counter()
    rebuilt, report = replay(log_path)
    rebuild_seconds = time.perf_counter() - marker
    full = {
        "events": report.events_applied,
        "log_bytes": log_path.stat().st_size,
        "state_digest_equal": rebuilt.state_digest() == live.state_digest(),
        "predictions_equal": bool(np.array_equal(rebuilt.predict(eval_keys),
                                                 live_predictions)),
        "accuracy_live": live_eval["total"],
        "accuracy_replayed": evaluate(rebuilt, eval_keys, eval_labels)["total"],
        "rebuild_seconds_not_official": rebuild_seconds,
    }
    del rebuilt

    checkpoint_checks = []
    for events, digest in checkpoints:
        model, _ = replay(log_path, limit=events)
        checkpoint_checks.append(model.state_digest() == digest)
        del model

    data = log_path.read_bytes()
    cut_path = work / f"l2_seed{args.seed}_cut.log"
    cut_path.write_bytes(data[:int(len(data) * CUT_FRACTION)])
    crashed, crash_report = replay(cut_path)
    records, _, _ = read_events(cut_path)
    reference, _ = replay(log_path, limit=len(records))
    crash = {
        "cut_fraction": CUT_FRACTION,
        "events_recovered": crash_report.events_applied,
        "bytes_discarded": crash_report.bytes_discarded,
        "state_digest_equal": crashed.state_digest() == reference.state_digest(),
        "predictions_equal": bool(np.array_equal(crashed.predict(eval_keys),
                                                 reference.predict(eval_keys))),
        "accuracy_crashed": evaluate(crashed, eval_keys, eval_labels)["total"],
        "accuracy_reference": evaluate(reference, eval_keys, eval_labels)["total"],
    }
    gate = (full["state_digest_equal"] and full["predictions_equal"]
            and all(checkpoint_checks)
            and crash["state_digest_equal"] and crash["predictions_equal"])
    print(f"full replay: {full}\ncrash replay: {crash}\n"
          f"checkpoints equal: {sum(checkpoint_checks)}/{len(checkpoint_checks)}", flush=True)

    record = {
        "task": "m2b_eviction_persistence", "seed": args.seed,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {**git_state, "captured": "before_run"},
        "setup": {"dimension": args.dimension, "config": STREAM_CONFIG.to_dict(),
                  "stream_items": len(stream["labels"]),
                  "persistence_items": PERSISTENCE_ITEMS, "encoder": stream["encoder"]},
        "eviction_curve": curve,
        "persistence": {"full_replay": full, "crash_replay": crash,
                        "checkpoints_equal": sum(checkpoint_checks),
                        "checkpoints_total": len(checkpoint_checks),
                        "gate_met": gate},
        "runtime": {"wall_seconds": time.perf_counter() - started},
        "environment": collect_environment(),
    }
    out = Path(args.results_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"m2b_{args.seed}_{stamp}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"persistence gate met: {gate}\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
