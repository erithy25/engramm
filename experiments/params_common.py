"""Shared helpers for the parameter-equivalent study (docs/PREREG_PARAMS.md)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from engramm.repro import collect_environment, git_revision, peak_rss_mb

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results" / "params"
WORK = REPO / "data" / "cache" / "params"
STUDY = "docs/PREREG_PARAMS.md v1.0"

#: The registered final ENGRAMM-LM (docs/EXPECTATIONS.md E12; experiments/lm_digests.py).
ENGRAMM_LM = {"scale": "main", "seed": 42, "tau_index": 1, "beta_index": 1,
              "base_digest": "b45c20659e5591ff5298d631da4f5c9d566421d6db69f80eaa16a94737779b54",
              "test_bpb_e12": 1.51357693}


#: Messart-C size grid (docs/PREREG_PARAMS.md §6.2): name -> (d, layers, heads).
GRID = {"S0": (32, 1, 1), "S1": (64, 2, 2), "S2": (96, 3, 3), "S3": (128, 4, 4),
        "S4": (192, 4, 6), "S5": (256, 6, 4), "S6": (384, 6, 6)}
#: Total parameters (tied embedding once) and without token/position embeddings, per size.
PARAMS = {"S0": (1069536, 12768), "S1": (2213632, 100096), "S2": (3506016, 335712), "S3": (5020416, 793344),
          "S4": (8120448, 1779840), "S5": (13193216, 4739072), "S6": (23328768, 10647552)}


def bits_of(a: np.ndarray) -> int:
    return int(np.dtype(a.dtype).itemsize * 8)


def array_row(a: np.ndarray, disk_bytes: int | None = None, bit_vector: bool = False) -> dict:
    """One stored array: number of values, bits per value, bytes in RAM (and on disk if given).

    ``bit_vector``: the array packs binary hypervectors into machine words; every bit is one value."""
    a = np.asarray(a)
    if bit_vector:
        values, bits = int(a.size * bits_of(a)), 1
    else:
        values, bits = int(a.size), bits_of(a)
    row = {"dtype": str(a.dtype), "shape": list(a.shape), "values": values, "bits_per_value": bits,
           "ram_bytes": int(a.nbytes)}
    if disk_bytes is not None:
        row["disk_bytes"] = int(disk_bytes)
    return row


def write_record(name: str, payload: dict, started: float, git_state: dict, directory: Path = RESULTS) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now = git_revision()
    record = {
        "schema": "engramm-params/1",
        "name": name,
        "study": STUDY,
        "timestamp_utc": ts,
        "git": {**git_state, "changed_during_run": now.get("commit") != git_state.get("commit")},
        "environment": collect_environment(),
        "runtime": {"wall_seconds": time.time() - started, "peak_rss_mb": peak_rss_mb(),
                    "note": "container timing/memory: never official (docs/PROTOCOL.md rule 2)"},
        **payload,
    }
    path = directory / f"{name}_{ts}.json"
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    return path
