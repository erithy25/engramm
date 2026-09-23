"""Compare re-run records against the committed ones, bit for bit.

    python -m experiments.verify_reproduction logs/runs/repro

For every record in the given directory, find the committed record in
``results/`` with the same task, seed and configuration, and compare:
accuracy and macro-F1 exactly, and ``predictions_sha256`` wherever both
records carry it (schema ≥ 4). Writes ``results/repro/verification.json``.

What this establishes is **determinism on this platform and specification
completeness of the committed code** — a second run from the committed
tree gives the same outputs. It is not independent replication by a third
party on different hardware (see the README's definition).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"

#: Hyperparameters that define "the same configuration" for matching.
_KEYS = ("task", "dimension", "shots", "pipeline", "t2_epochs", "fusion", "encoder")


def _signature(record: dict[str, Any]) -> tuple:
    hp = record["hyperparams"]
    pipeline = hp.get("pipeline", "prototypes")
    return (record["task"], record["seed"],
            *[json.dumps(hp.get(k, "prototypes" if k == "pipeline" else None),
                         sort_keys=True) for k in _KEYS[1:]],
            pipeline)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    rerun_dir = Path(argv[0] if argv else "logs/runs/repro")
    committed = {}
    for path in sorted(RESULTS.glob("*.json")):
        record = json.loads(path.read_text())
        if "hyperparams" in record:
            committed.setdefault(_signature(record), []).append((path, record))

    rows = []
    for path in sorted(rerun_dir.glob("*.json")):
        record = json.loads(path.read_text())
        matches = committed.get(_signature(record), [])
        if not matches:
            rows.append({"rerun": path.name, "matched": None, "identical": False,
                         "reason": "no committed record with this configuration"})
            continue
        ref_path, ref = matches[0]
        checks = {
            "accuracy": record["result"]["accuracy"] == ref["result"]["accuracy"],
            "macro_f1": record["result"]["macro_f1"] == ref["result"]["macro_f1"],
        }
        a, b = record["result"].get("predictions_sha256"), ref["result"].get("predictions_sha256")
        if a and b:
            checks["predictions_sha256"] = a == b
        rows.append({"rerun": path.name, "matched": ref_path.name,
                     "committed_commit": ref["git"]["commit"],
                     "rerun_commit": record["git"]["commit"],
                     "accuracy": record["result"]["accuracy"],
                     "checks": checks, "identical": all(checks.values())})
        print(f"{path.name} vs {ref_path.name}: {checks}")

    out = RESULTS / "repro"
    out.mkdir(parents=True, exist_ok=True)
    summary = {"timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "what_this_shows": "determinism on this platform from the committed tree; "
                                  "not third-party replication on other hardware",
               "all_identical": bool(rows) and all(r["identical"] for r in rows),
               "rows": rows}
    (out / "verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"all identical: {summary['all_identical']}")
    return 0 if summary["all_identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
