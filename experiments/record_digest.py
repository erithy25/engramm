"""Record this platform's determinism digest for cross-platform comparison.

Bit-identity between the Linux container and the reference machine cannot be
checked inside a single job — the two runs happen on different hosts at
different times. So it is a two-step procedure with a committed artifact:

1. On each platform, run::

       python -m experiments.record_digest --seeds 42,7,1337,2026,99

   which writes ``results/crossplatform/<platform-tag>.json``.

2. Commit that file. ``tests/test_determinism.py`` then compares every
   committed platform file and fails if any two disagree for a shared seed.

Re-running on the same platform overwrites that platform's file — unlike
benchmark records, a digest is a property of the platform, not an event.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from engramm.repro import (
    collect_environment,
    determinism_digest,
    digest_hash,
    git_revision,
    is_canonical_environment,
)

DIGEST_DIR = Path(__file__).resolve().parent.parent / "results" / "crossplatform"

DEFAULT_SEEDS = "42,7,1337,2026,99"


def platform_tag() -> str:
    """Short filesystem-safe identifier for this platform and Python version."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    py = ".".join(platform.python_version_tuple()[:2])
    return f"{system}-{machine}-py{py}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seeds", default=DEFAULT_SEEDS,
        help=f"comma-separated seeds to probe (default: {DEFAULT_SEEDS})",
    )
    args = parser.parse_args(argv)
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]

    digests = {
        str(seed): {
            "values": determinism_digest(seed),
            "sha256": digest_hash(determinism_digest(seed)),
        }
        for seed in seeds
    }
    record = {
        "platform_tag": platform_tag(),
        "canonical": is_canonical_environment(),
        "git": git_revision(),
        "environment": collect_environment(),
        "digests": digests,
    }

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGEST_DIR / f"{platform_tag()}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")

    print(f"wrote {path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path}")
    for seed, entry in digests.items():
        print(f"  seed {seed:>5}: {entry['sha256'][:16]}…")
    print(f"  canonical environment: {record['canonical']}")
    if len(list(DIGEST_DIR.glob('*.json'))) < 2:
        print("\nOnly one platform recorded so far — run this on the reference "
              "machine too, then commit both files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
