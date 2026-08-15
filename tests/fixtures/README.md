# tests/fixtures/ — cross-platform reference

`loader_reference.json` pins the data pipeline's output — loaders, few-shot
selection, and every fitted artifact — as recorded on the **canonical
reference machine** (macOS / arm64 / Python 3.13, see `docs/PROTOCOL.md`).
`tests/test_no_leakage.py::test_matches_cross_platform_reference` compares
the current platform against it.

## Generating it

On the reference machine, with the dataset cache populated:

```bash
python -m tests.leakage_probe --seed 42 --write-reference
```

Then commit the resulting `loader_reference.json`. The file records the
platform tag, git commit, environment (including the `canonical` flag), the
full probe result, and its SHA-256.

## While it is missing

The test **skips with an explicit message** rather than passing silently.
That is the intended state until the reference machine has produced one —
per `docs/PROTOCOL.md`, no milestone figure counts before that confirmation
has happened, so a visible skip is the honest representation.

The comparison logic itself is covered by a separate unit test, so it does
not rot while the reference is absent.

## When the comparison fails

A mismatch means the data pipeline produces different results on different
platforms. That is a finding to investigate and document — not something to
resolve by regenerating the reference until it agrees. Note that the
development container runs Python 3.11 while the reference is 3.13, so a
mismatch could stem from either the platform or the version; re-record the
container under 3.13 first to separate the two causes.
