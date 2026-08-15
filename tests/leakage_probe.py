"""Deterministic probe over the data pipeline, for cross-process comparison.

Runs the real loaders and the real fitting function and reduces the result
to a digest. Used three ways:

* by ``tests/test_no_leakage.py`` to compare two fresh interpreters,
* by the same tests to compare two ``PYTHONHASHSEED`` settings,
* to produce the cross-platform reference in ``tests/fixtures/``.

Run standalone::

    python -m tests.leakage_probe --seed 42
    python -m tests.leakage_probe --seed 42 --write-reference
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

from data.loaders import (
    Dataset,
    fit_train_artifacts,
    load_mnist,
    load_wili,
)
from engramm.repro import collect_environment, git_revision, set_all_seeds

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
REFERENCE_PATH = FIXTURE_DIR / "loader_reference.json"

#: Training examples used for fitting. Bounded so the probe runs in
#: seconds; it still exercises the real loaders and the real fitting code.
PROBE_TRAIN_LIMIT = 4_000
PROBE_VOCABULARY_SIZE = 500
PROBE_SHOTS = 10


def _subset(dataset: Dataset, limit: int) -> Dataset:
    """Take the first ``limit`` training examples, keeping everything else."""
    from dataclasses import replace

    if dataset.n_train <= limit:
        return dataset
    x_train = (dataset.x_train[:limit] if isinstance(dataset.x_train, np.ndarray)
               else tuple(dataset.x_train[:limit]))
    return replace(dataset, x_train=x_train, y_train=dataset.y_train[:limit])


def _array_digest(array: np.ndarray) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(array).tobytes()
        + str(array.dtype).encode() + str(array.shape).encode()
    ).hexdigest()


def probe(seed: int, allow_download: bool = False) -> dict[str, Any]:
    """Load both datasets, fit artifacts, and reduce everything to digests."""
    result: dict[str, Any] = {"seed": seed}

    mnist = _subset(load_mnist(allow_download=allow_download), PROBE_TRAIN_LIMIT)
    mnist_artifacts = fit_train_artifacts(mnist)
    result["mnist"] = {
        "labels": list(mnist.labels),
        "n_train": mnist.n_train,
        "n_test": mnist.n_test,
        "x_train_digest": _array_digest(np.asarray(mnist.x_train)),
        "y_test_digest": _array_digest(mnist.y_test),
        "artifacts_digest": mnist_artifacts.digest(),
        "pixel_mean_repr": [repr(round(float(v), 10))
                            for v in mnist_artifacts.pixel_mean[:8]],
    }

    # Few-shot selection is the seeded part of the pipeline, so it belongs
    # in a determinism probe: the generator comes from set_all_seeds.
    rng = set_all_seeds(seed)
    wili = load_wili(shots=PROBE_SHOTS, rng=rng, allow_download=allow_download)
    wili_artifacts = fit_train_artifacts(wili, vocabulary_size=PROBE_VOCABULARY_SIZE)
    result["wili"] = {
        "labels_head": list(wili.labels[:10]),
        "n_classes": wili.n_classes,
        "n_train": wili.n_train,
        "n_test": wili.n_test,
        "shots": wili.metadata["shots"],
        "y_train_digest": _array_digest(wili.y_train),
        "selected_text_digest": hashlib.sha256(
            "\x00".join(wili.x_train).encode("utf-8")).hexdigest(),
        "artifacts_digest": wili_artifacts.digest(),
        "vocabulary_head": list(wili_artifacts.vocabulary[:12]),
    }
    return result


def probe_hash(seed: int, allow_download: bool = False) -> str:
    """One comparable hex string over the whole probe."""
    payload = json.dumps(probe(seed, allow_download), sort_keys=True,
                         ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def platform_tag() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    py = ".".join(platform.python_version_tuple()[:2])
    return f"{system}-{machine}-py{py}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--allow-download", action="store_true",
                        help="permit fetching sources that are not cached")
    parser.add_argument("--write-reference", action="store_true",
                        help=f"write the cross-platform reference to {REFERENCE_PATH}")
    parser.add_argument("--hash-only", action="store_true")
    args = parser.parse_args(argv)

    if args.hash_only:
        print(probe_hash(args.seed, args.allow_download))
        return 0

    result = probe(args.seed, args.allow_download)
    if args.write_reference:
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "platform_tag": platform_tag(),
            "git": git_revision(),
            "environment": collect_environment(),
            "probe": result,
            "probe_sha256": hashlib.sha256(
                json.dumps(result, sort_keys=True, ensure_ascii=True).encode()
            ).hexdigest(),
        }
        REFERENCE_PATH.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {REFERENCE_PATH}")
        print(f"  platform : {record['platform_tag']}")
        print(f"  canonical: {record['environment']['canonical']}")
        print(f"  sha256   : {record['probe_sha256'][:24]}…")
        return 0

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
