# results/ — versioned benchmark records

Every benchmark run writes exactly one JSON file here, named

```
<task>_<seed>_<UTC-timestamp>.json      e.g. mnist_42_20260815T142233Z.json
```

These files are **committed to git** — they are the project's measurement
record. `data/` and `logs/` are gitignored; `results/` never is.

## Record schema (`schema_version: 1`)

Produced by `engramm.repro.write_result()`. All fields are mandatory.

```json
{
  "schema_version": 1,
  "task": "mnist",
  "seed": 42,
  "timestamp_utc": "2026-08-15T14:22:33+00:00",
  "git": {
    "commit": "81af2c4…",
    "dirty": false
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
    "peak_rss_mb": 0.0
  },
  "environment": {
    "python": "3.13.7",
    "numpy": "2.4.1",
    "platform": "macOS-…",
    "machine": "arm64",
    "cpu_count": 10
  }
}
```

Conventions:

* **Append-only.** A new run writes a new file; existing records are never
  overwritten or edited.
* **`git.dirty: true` disqualifies a record** from being cited as an
  official number — official runs happen on a clean, committed tree.
* `result` carries metrics only; everything that *influenced* the metrics
  belongs in `hyperparams`.
