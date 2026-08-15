"""Reproducibility utilities: seeding, environment capture, run records.

Every benchmark run in this project goes through this module. Two rules:

* All randomness flows from a single integer seed via :func:`set_all_seeds`.
  The returned generator is the only RNG project code may use for data
  splits and item-memory construction — it is passed around explicitly,
  never pulled from global state.
* Every run is recorded as one JSON file under ``results/`` via
  :func:`write_result`, carrying enough metadata to attribute and repeat
  the run exactly (seed, commit hash, hyperparameters, environment).

The record layout is documented in ``results/README.md`` and versioned via
:data:`SCHEMA_VERSION`.
"""

from __future__ import annotations

import json
import os
import platform
import random
import resource
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA_VERSION = 1

_REPO_ROOT = Path(__file__).resolve().parent.parent


def set_all_seeds(seed: int) -> np.random.Generator:
    """Seed every randomness source used by this project.

    Seeds Python's ``random`` module and NumPy's legacy global RNG (so that
    any accidental use of either is at least deterministic), and returns a
    fresh :class:`numpy.random.Generator` seeded with the same value. That
    generator is the canonical randomness source for data splits, shuffles
    and item-memory construction.

    Hash randomization (``PYTHONHASHSEED``) cannot be changed from inside a
    running interpreter. Project code must therefore never let results
    depend on ``str``/``bytes`` hash order — concretely: never iterate over
    a ``set`` or rely on dict order of hashed keys where the order can
    influence an output. Class label order, for example, is always obtained
    via ``sorted()``.

    Parameters
    ----------
    seed:
        Any non-negative integer. The same seed yields the same generator
        stream on every platform NumPy supports.

    Returns
    -------
    numpy.random.Generator
        The canonical RNG for this run.
    """
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)


def git_revision() -> dict[str, Any]:
    """Return the current commit hash and whether the working tree is dirty.

    Returns ``{"commit": None, "dirty": None}`` when git is unavailable or
    the project is not inside a git checkout — a run record must never fail
    because of missing version-control metadata.
    """
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=_REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": dirty}


def collect_environment() -> dict[str, Any]:
    """Capture the software and hardware environment of this run."""
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
    }


def peak_rss_mb() -> float:
    """Peak resident set size of this process, in MiB.

    ``ru_maxrss`` is reported in bytes on macOS but in kibibytes on Linux;
    both are normalized to MiB here.
    """
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return peak / (1024 * 1024)
    return peak / 1024


def write_result(
    *,
    task: str,
    seed: int,
    result: dict[str, Any],
    hyperparams: dict[str, Any],
    wall_seconds: float,
    results_dir: Path | str | None = None,
) -> Path:
    """Write one benchmark run as a JSON record and return its path.

    The file is named ``<task>_<seed>_<UTC-timestamp>.json`` and contains
    the full run context: schema version, task, seed, timestamp, git commit
    (plus dirty flag), the result metrics, all hyperparameters, wall time,
    peak RAM, and the software environment. Records are append-only: a new
    run writes a new file and never overwrites an old one.

    Parameters
    ----------
    task:
        Benchmark identifier, e.g. ``"mnist"`` or ``"wili"``.
    seed:
        The seed the run was executed with.
    result:
        Metric dictionary, e.g. ``{"accuracy": ..., "macro_f1": ...,
        "n_train": ..., "n_test": ...}``.
    hyperparams:
        Every knob that influenced the run (dimension, epochs, n-gram
        order, shots, ...). "All of them" is the contract — a record that
        cannot reproduce its run is a bug.
    wall_seconds:
        Wall-clock duration of the run.
    results_dir:
        Target directory; defaults to ``<repo root>/results``.
    """
    ts = datetime.now(timezone.utc)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task": task,
        "seed": seed,
        "timestamp_utc": ts.isoformat(timespec="seconds"),
        "git": git_revision(),
        "result": result,
        "hyperparams": hyperparams,
        "runtime": {
            "wall_seconds": round(wall_seconds, 3),
            "peak_rss_mb": round(peak_rss_mb(), 1),
        },
        "environment": collect_environment(),
    }
    out_dir = Path(results_dir) if results_dir is not None else _REPO_ROOT / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{task}_{seed}_{ts.strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path
