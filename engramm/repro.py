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

import hashlib
import json
import os
import platform
import random
import resource
import subprocess
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA_VERSION = 2

_REPO_ROOT = Path(__file__).resolve().parent.parent


def is_canonical_environment() -> bool:
    """Whether this process runs on the project's reference environment.

    The reference environment (``docs/PROTOCOL.md``) is the project's
    MacBook Air M4: macOS on arm64 with Python 3.13. Only records produced
    there carry ``canonical: true`` and may be cited as official numbers;
    container/CI runs always produce ``canonical: false`` records.

    The check is deliberately automatic and cannot be overridden by
    callers — a run cannot declare itself canonical.
    """
    return (
        sys.platform == "darwin"
        and platform.machine() == "arm64"
        and platform.python_version_tuple()[:2] == ("3", "13")
    )


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


def stable_label_order(labels: Iterable[str]) -> list[str]:
    """Return the unique labels in a hash-order-independent, sorted order.

    The canonical way to derive a class ordering in this project. Iterating
    a ``set`` of strings yields an order that depends on ``PYTHONHASHSEED``,
    which would make class indices — and therefore results — vary between
    processes. Sorting removes that dependency.

    Project code must never derive a class ordering any other way; the rule
    is enforced by ``tests/test_determinism.py``, which runs the pipeline
    under two different hash seeds and compares the results.
    """
    return sorted(set(labels))


def determinism_digest(seed: int) -> dict[str, Any]:
    """Compute deterministic probe values for cross-platform comparison.

    Every entry is a value that must be identical on every platform for a
    given seed. Comparing digests between the Linux container and the
    reference machine turns "we assume this is deterministic" into a
    checked fact (``docs/PROTOCOL.md``, rule 4).

    Probed: the canonical RNG's integer and float streams, the
    hash-order-sensitive label ordering, NumPy's float formatting and byte
    order, and — via :func:`_model_probe` — the VSA algebra and the trained
    prototype classifier, so the digest covers the pipeline rather than only
    its primitives.
    """
    rng = set_all_seeds(seed)
    ints = rng.integers(0, 2**31 - 1, size=16, dtype=np.int64)
    floats = rng.standard_normal(8)
    packed = np.packbits(rng.integers(0, 2, size=1024, dtype=np.uint8))
    messy = ["zulu", "alpha", "Mike", "alpha", "écho", "1one", "bravo"]
    return {
        "rng_integers": ints.tolist(),
        "rng_floats_repr": [repr(float(x)) for x in floats],
        "rng_packbits_sum": int(packed.sum()),
        "stable_label_order": stable_label_order(messy),
        "float_formatting": [repr(float(np.float64(1) / 3)), f"{np.float32(0.1):.20f}"],
        "byteorder": sys.byteorder,
        "int64_itemsize": int(np.dtype(np.int64).itemsize),
        "model": _model_probe(seed),
    }


def _model_probe(seed: int) -> dict[str, Any]:
    """Deterministic probe over the VSA algebra and the trained classifier.

    Imported lazily because :mod:`engramm.core` depends on this module —
    a top-level import would be circular.

    Uses a reduced dimension and small odd class sizes, plus one deliberately
    even bundle so the tie path is pinned too: tie resolution is a keyed hash
    (:func:`engramm.core.resolve_tie`), which is exactly the kind of branch
    that could differ between platforms if it were ever reimplemented.
    """
    from engramm.core import (
        ItemMemory, PrototypeClassifier, bind, bundle, permute, to_signed,
    )
    from engramm.metrics import hamming

    dimension = 1024
    memory = ItemMemory(seed, dimension)
    symbols = [f"probe{i}" for i in range(7)]
    stack = memory.vectors(symbols)

    bound = bind(stack[0], stack[1])
    rotated = permute(stack[2], 3, dimension)
    bundled = bundle(stack, dimension)

    model = PrototypeClassifier(dimension, seed=seed)
    labels = [f"class{i % 3}" for i in range(9)]
    model.learn(to_signed(stack[:3].repeat(3, axis=0), dimension).astype(np.int8),
                labels)
    scores = model.score(stack)

    return {
        "vector_checksums": [int(v.sum()) for v in stack],
        "bind_distance": int(hamming(bound, stack[0])),
        "permute_distance": int(hamming(rotated, stack[2])),
        "bundle_distances": [int(hamming(bundled, v)) for v in stack],
        "prototype_checksums": [int(p.sum()) for p in model.P],
        "accumulator_checksums": [int(a.sum()) for a in model.A],
        "scores_repr": [repr(round(float(s), 12)) for s in scores.ravel()],
        "labels": list(model.labels),
    }


def digest_hash(digest: dict[str, Any]) -> str:
    """Hash a determinism digest into a single comparable hex string."""
    payload = json.dumps(digest, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
    """Capture the software and hardware environment of this run.

    ``canonical`` marks whether this is the reference environment defined in
    ``docs/PROTOCOL.md`` (see :func:`is_canonical_environment`). Timing and
    memory figures from a non-canonical environment are never official.
    """
    return {
        "canonical": is_canonical_environment(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
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

    The record's ``environment.canonical`` flag is set automatically from
    the host (:func:`is_canonical_environment`) and decides whether the
    record may be cited as an official number. Per ``docs/PROTOCOL.md``,
    non-canonical runs are valid for accuracy and macro-F1 as long as the
    figure is later confirmed bit-identically on the reference machine, but
    their timing and memory figures are never official.

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
