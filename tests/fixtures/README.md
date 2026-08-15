# tests/fixtures/ — cross-platform reference

`loader_reference.json` pins the data pipeline's output — loaders, few-shot
selection, and every fitted artifact — as recorded on one platform.
`tests/test_no_leakage.py::test_matches_cross_platform_reference` compares
the platform it is currently running on against that record.

## Which platform recorded it

The file names its own origin in `platform_tag`, and the check is
**anchored, not canonical**: what makes the comparison meaningful is that
the reference came from a *different* platform than the one running the
test, not that it came from the reference machine.

The committed reference was recorded in the Linux development container
(`linux-x86_64-py3.11`, `canonical: false`). Running the suite there
therefore compares the container against itself, which proves nothing — so
the test **skips with that explanation** rather than passing. Running the
same suite on the reference machine (macOS / arm64 / Python 3.13) compares
two genuinely different platforms, and that is the real check.

Note that the two differ in Python version as well as in OS and
architecture, so a mismatch does not by itself say which of the three
caused it. To separate them, re-record the container under Python 3.13
before investigating further.

## Regenerating it

```bash
python -m tests.leakage_probe --seed 42 --write-reference
```

The record carries the platform tag, git commit, environment (including the
`canonical` flag), the full probe result, and its SHA-256.

## When the comparison fails

A mismatch means the data pipeline produces different results on different
platforms. That is a finding to investigate and document — **not** something
to resolve by regenerating the reference until it agrees. Regenerating
silently converts a real defect into a green test.

## Related

`results/crossplatform/` does the same for the numerical core rather than
the data pipeline, via `python -m experiments.record_digest`. It needs
digests from two or more platforms before its test does anything, and
currently holds only the container's.
