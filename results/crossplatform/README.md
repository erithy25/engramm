# results/crossplatform/ — platform determinism digests

One JSON file per platform, named `<system>-<machine>-py<major.minor>.json`.
Each records, for a fixed set of seeds, a SHA-256 digest over deterministic
probe values (RNG streams, label ordering, float formatting, byte order —
and, as the model lands, its outputs).

## Why this exists

Bit-identity between the development container and the reference MacBook M4
cannot be checked inside one job: the runs happen on different hosts. So each
platform commits its digest, and `tests/test_determinism.py` compares the
committed files.

## Procedure

On **each** platform, from the repository root:

```bash
python -m experiments.record_digest --seeds 42,7,1337,2026,99
```

then commit the resulting file. With two or more platform files present,
`pytest tests/test_determinism.py::test_cross_platform_bit_identity` compares
every shared seed and fails on any disagreement. With only one file it skips
with an explicit message — a visible gap, not a silent pass.

Re-running on the same platform overwrites that platform's file: a digest is
a property of the platform, not an event to be preserved (unlike benchmark
records in `results/`, which are append-only).

## When a comparison fails

A mismatch means the implementation depends on the platform somewhere. That
is a finding to investigate and document, per `docs/PROTOCOL.md` — never
something to average away or to resolve by declaring one platform correct.

## Status

`linux-x86_64-py3.11.json` is the development container. The reference
machine's digest (`darwin-arm64-py3.13.json`) is still missing, so the
cross-platform test currently skips.

Note that the container runs Python 3.11 while the reference environment is
3.13; when the M4 digest is added, a mismatch could stem from either the
platform or the Python version. If one appears, re-record the container
digest under 3.13 first to separate the two causes.
