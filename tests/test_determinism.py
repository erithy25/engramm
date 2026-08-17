"""Determinism guarantees, enforced rather than documented.

Three properties are checked here:

* results do not depend on ``PYTHONHASHSEED`` (hash-order independence),
* results do not depend on the platform (cross-platform bit-identity),
* the same seed yields identical results across separate processes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from engramm.repro import determinism_digest, digest_hash, stable_label_order

REPO_ROOT = Path(__file__).resolve().parent.parent
DIGEST_DIR = REPO_ROOT / "results" / "crossplatform"

SEEDS = [42, 7, 1337, 2026, 99]

# Printed by the subprocess probe so the parent can parse one clean line.
_MARKER = "DIGEST:"

_PROBE = f"""
import sys
sys.path.insert(0, {str(REPO_ROOT)!r})
from engramm.repro import determinism_digest, digest_hash
seed = int(sys.argv[1])
print("{_MARKER}" + digest_hash(determinism_digest(seed)))
"""


def _run_probe(seed: int, hashseed: str) -> str:
    """Run the digest probe in a fresh interpreter with a given PYTHONHASHSEED."""
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE, str(seed)],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT, check=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith(_MARKER):
            return line[len(_MARKER):].strip()
    raise AssertionError(f"probe produced no digest line; stdout={proc.stdout!r}")


@pytest.mark.parametrize("seed", SEEDS)
def test_results_do_not_depend_on_pythonhashseed(seed: int) -> None:
    """Same seed, different PYTHONHASHSEED, identical result.

    This is the enforcement of the "never iterate over hash order" rule. If
    any part of the pipeline derives class indices from ``set`` iteration
    order, the two subprocesses disagree and this test fails.
    """
    digest_0 = _run_probe(seed, "0")
    digest_1 = _run_probe(seed, "1")
    assert digest_0 == digest_1, (
        f"seed {seed}: PYTHONHASHSEED=0 gave {digest_0}, PYTHONHASHSEED=1 gave "
        f"{digest_1}. Something in the pipeline depends on hash iteration order "
        f"— derive class orderings via stable_label_order()."
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_digest_is_stable_across_processes(seed: int) -> None:
    """Two separate interpreters, same seed, identical digest."""
    assert _run_probe(seed, "0") == _run_probe(seed, "0")


@pytest.mark.parametrize("seed", SEEDS)
def test_digest_is_stable_within_process(seed: int) -> None:
    """Recomputing a digest in one process is idempotent."""
    assert digest_hash(determinism_digest(seed)) == digest_hash(determinism_digest(seed))


def test_different_seeds_give_different_digests() -> None:
    """Guards against a digest that ignores its seed and always matches."""
    hashes = {digest_hash(determinism_digest(s)) for s in SEEDS}
    assert len(hashes) == len(SEEDS), "digest does not vary with the seed"


def test_stable_label_order_is_sorted_and_unique() -> None:
    labels = ["zulu", "alpha", "Mike", "alpha", "écho", "1one", "bravo"]
    assert stable_label_order(labels) == sorted(set(labels))
    assert stable_label_order(labels) == stable_label_order(reversed(labels))


def _load_platform_digests() -> dict[str, dict]:
    if not DIGEST_DIR.is_dir():
        return {}
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(DIGEST_DIR.glob("*.json"))
    }


def test_cross_platform_bit_identity() -> None:
    """Committed platform digests must agree on every shared seed.

    Bit-identity between the Linux container and the reference M4 cannot be
    established inside one job, so each platform commits its digest via
    ``python -m experiments.record_digest`` and this test compares them.

    With only one platform recorded the test skips — it can only compare
    what exists. Per ``docs/PROTOCOL.md`` a milestone figure is not official
    until the reference machine's digest is committed alongside the
    container's, so the skip is visible rather than silent.
    """
    platforms = _load_platform_digests()
    if len(platforms) < 2:
        have = ", ".join(platforms) or "none"
        pytest.skip(
            f"need digests from 2+ platforms, have: {have}. Run "
            "'python -m experiments.record_digest' on the reference machine "
            "and commit results/crossplatform/*.json."
        )

    names = sorted(platforms)
    reference = names[0]
    mismatches: list[str] = []
    for other in names[1:]:
        shared = set(platforms[reference]["digests"]) & set(platforms[other]["digests"])
        assert shared, f"{reference} and {other} share no seeds to compare"
        for seed in sorted(shared, key=int):
            a = platforms[reference]["digests"][seed]["sha256"]
            b = platforms[other]["digests"][seed]["sha256"]
            if a != b:
                mismatches.append(f"seed {seed}: {reference}={a[:16]}… {other}={b[:16]}…")

    assert not mismatches, (
        "cross-platform bit-identity violated — the implementation depends on "
        "the platform somewhere:\n  " + "\n  ".join(mismatches)
    )


def test_current_platform_matches_its_committed_digest() -> None:
    """If this platform has a committed digest, recomputing must reproduce it.

    Catches drift: a code change that alters results shows up here as a
    mismatch against the committed artifact instead of silently invalidating
    the cross-platform comparison.
    """
    from experiments.record_digest import platform_tag

    path = DIGEST_DIR / f"{platform_tag()}.json"
    if not path.is_file():
        pytest.skip(f"no committed digest for {platform_tag()} yet")

    committed = json.loads(path.read_text(encoding="utf-8"))
    for seed, entry in committed["digests"].items():
        current = digest_hash(determinism_digest(int(seed)))
        assert current == entry["sha256"], (
            f"seed {seed} on {platform_tag()}: committed {entry['sha256'][:16]}…, "
            f"now {current[:16]}…. Code changed the pipeline's output — if that "
            f"was intended, re-run 'python -m experiments.record_digest' on every "
            f"platform and commit the updated digests."
        )
