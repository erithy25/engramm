# results/ — versioned benchmark records

Every benchmark run writes exactly one JSON file here, named

```
<task>_<seed>_<UTC-timestamp>.json      e.g. mnist_42_20260815T142233Z.json
```

These files are **committed to git** — they are the project's measurement
record. `data/` and `logs/` are gitignored; `results/` never is.

## Record schema (`schema_version: 4`)

Produced by `engramm.repro.write_result()`. All fields are mandatory.

```json
{
  "schema_version": 4,
  "task": "mnist",
  "seed": 42,
  "timestamp_utc": "2026-08-15T14:22:33+00:00",
  "git": {
    "commit": "81af2c4…",
    "dirty": false,
    "untracked": 0,
    "captured": "before_run",
    "changed_during_run": false
  },
  "result": {
    "accuracy": 0.0,
    "macro_f1": 0.0,
    "n_train": 0,
    "n_test": 0
  },
  "hyperparams": {
    "dimension": 10000,
    "...": "every knob that influenced the run"
  },
  "runtime": {
    "wall_seconds": 0.0,
    "peak_rss_mb": 0.0,
    "peak_rss_scope": "run"
  },
  "environment": {
    "canonical": true,
    "python": "3.13.7",
    "numpy": "2.4.1",
    "platform": "macOS-…",
    "machine": "arm64",
    "cpu_count": 10,
    "pythonhashseed": null
  }
}
```

Conventions:

* **Append-only.** A new run writes a new file; existing records are never
  overwritten or edited.
* **`environment.canonical` decides what may be cited.** It is set
  automatically (macOS + arm64 + Python 3.13, the reference machine from
  [`docs/PROTOCOL.md`](../docs/PROTOCOL.md)) and cannot be set by the
  caller. `canonical: false` records are valid candidates for accuracy and
  macro-F1 but their **timing and memory figures are never official**.
* **`git.dirty: true` disqualifies a record** from being cited as an
  official number — official runs happen on a clean, committed tree.
  `dirty` covers **tracked files only**. Untracked files are counted in
  `untracked` and do not disqualify, because they do not change which code
  ran. Folding them in was a defect: a run's own result files are untracked
  while later seeds execute, so every seed after the first was marked
  dirty. Fixed in schema 3.
* `result` carries metrics only; everything that *influenced* the metrics
  belongs in `hyperparams`. Since schema 4 it also carries
  `predictions_sha256`, a digest over every predicted label in test order,
  so a reproduction can be checked prediction by prediction rather than via
  a rounded accuracy.
* **`git.captured`** says when provenance was taken. `before_run` (schema 4
  runners) records the checkout the process imported at launch; if HEAD or
  the dirty flag moved before the record was written, `changed_during_run`
  is `true` and the record is **not citable** until re-run. `at_write`
  (schema ≤ 3, and callers that pass no launch state) is the weaker form.
* **`runtime.peak_rss_scope`**: `run` means the seed ran in its own child
  process and the figure is its own peak; `process` means it is the
  high-water mark of a process that may have run earlier seeds too (all
  schema ≤ 3 records — their later seeds report the maximum of all earlier
  ones).

### Schema history

| Version | Change |
|---|---|
| 4 | Provenance captured before the run (`git.captured`, `git.changed_during_run`); per-run peak memory from an isolated child process (`runtime.peak_rss_scope`); `result.predictions_sha256`; WiLI records add `test_items_in_train` and `accuracy_excluding_train_duplicates`. |
| 3 | `git.dirty` now counts tracked modifications only; added `git.untracked`. Before this, a multi-seed run marked every seed after the first as dirty because of its own result files. |
| 2 | Added `environment.canonical` and `environment.pythonhashseed`. |
| 1 | Initial schema. |
