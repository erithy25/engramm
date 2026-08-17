# PROTOCOL — measurement environments and what counts as official

This document defines where a number has to be produced before the project
may call it official. It is binding for every milestone figure and is
enforced in code: `engramm.repro.write_result()` stamps every result record
with `environment.canonical`, derived automatically from the host.

## The reference machine

| | |
|---|---|
| Hardware | MacBook Air, Apple M4, 10 cores, 16 GB RAM |
| OS | macOS (arm64) |
| Python | 3.13 |
| NumPy | 2.4.1 (see `requirements.txt` / `requirements.lock`) |

`is_canonical_environment()` returns `True` exactly when the run is on
macOS + arm64 + Python 3.13. A run **cannot declare itself canonical** —
there is no override parameter, by design.

## Rule 1 — accuracy and macro-F1

Development and CI runs in a Linux container are **allowed** for accuracy
and macro-F1. They are useful and cheap, and they catch most errors.

But: **every milestone figure must be confirmed once on the reference
machine, bit-identically.** A container number is a candidate; it becomes a
milestone figure only when a run on the M4, with the same seed and the same
commit, produces the identical value. The confirming record (with
`canonical: true`) is what gets cited — the container record stays in
`results/` as part of the history.

If container and reference machine disagree, that is a finding, not a
nuisance: it means the implementation depends on the platform somewhere.
It gets investigated and documented, never averaged away.

## Rule 2 — wall time, peak RAM, energy

**Reference machine only. Container values are never official** — not as a
candidate, not "approximately", not with a footnote.

Container timings are meaningless for this project's claims: shared and
throttled CPU, different memory subsystem, no thermal profile comparable to
a fanless MacBook Air. The historical record already shows how sensitive
these figures are — the same MNIST seed took 41.4 min in a throttled
overnight run and 27.4 min awake on mains power.

Timing runs on the reference machine additionally follow the W16 conditions
from `D6_EHRLICHKEIT.md`: `caffeinate`, mains power, lid open, sole running
job.

## Rule 3 — the record decides

Every result JSON in `results/` carries `environment.canonical`. Citing a
figure means pointing at a record. Consequently:

* `canonical: false` + timing/memory → **not citable**, full stop.
* `canonical: false` + accuracy/macro-F1 → citable only alongside the
  confirming `canonical: true` record.
* `git.dirty: true` → **not citable** in any case; official runs happen on
  a clean, committed tree.

## Rule 4 — determinism is tested, not assumed

Two properties are enforced by the test suite rather than by convention:

* **Hash-order independence.** `tests/test_no_leakage.py` runs the same
  benchmark twice via subprocess with `PYTHONHASHSEED=0` and
  `PYTHONHASHSEED=1` and requires identical results. This makes the rule
  "never let results depend on `set`/`dict` iteration order" enforced
  instead of merely documented.
* **Cross-platform bit-identity.** The same seed must produce the identical
  result on the Linux container and on the reference machine. See
  `results/crossplatform/README.md` for how the comparison is recorded —
  it cannot run inside a single CI job, so it is a two-step procedure with
  a committed artifact.
