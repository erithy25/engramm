# SearchBench-EN v0 — how to write and run it

Registered in `docs/PREREG_SEARCH_V0.md`. The tooling is finished; what is still missing is people's work:
**400 questions written by people** and **two human raters** per answer. No AI writes or rates.

## 1. Write the questions (people, without access to ENGRAMM)

One JSON object per line in `data/searchbench/items.jsonl`:

```json
{"id": "sb-0001", "category": "current", "question": "…?", "answer": "…", "source": "https://…", "writer": "w01"}
```

- `category`: 160 × `current` (events or values after 1 January 2023), 120 × `longtail` (subject not among the
  400,000 articles of the Lite pack), 120 × `general`.
- `answer`: the reference answer; `source`: the page that proves it.
- Check with `python -m experiments.searchbench validate --items data/searchbench/items.jsonl`.

## 2. Split and seal (before any test run)

`python -m experiments.searchbench split --items data/searchbench/items.jsonl --out data/searchbench`
writes `dev.jsonl` (100) and `test.jsonl` (300) and the SHA-256 seal into `docs/SEARCHBENCH_SEAL.txt`.
Commit the seal; `run` refuses a test file that no longer matches it.

## 3. Run the systems (once on the test split)

```
python -m experiments.searchbench run --items data/searchbench/test.jsonl --pack <pack> --system offline   --out results/searchbench/offline.jsonl
python -m experiments.searchbench run --items data/searchbench/test.jsonl --pack <pack> --system atlas-off --out results/searchbench/atlas-off.jsonl
python -m experiments.searchbench run --items data/searchbench/test.jsonl --pack <pack> --system atlas     --out results/searchbench/atlas.jsonl
python -m experiments.searchbench same    --a results/searchbench/offline.jsonl --b results/searchbench/atlas-off.jsonl   # S5
python -m experiments.searchbench privacy --runs results/searchbench/atlas.jsonl --items data/searchbench/test.jsonl      # S4
```

## 4. Rate (two people, blind) and score

```
python -m experiments.searchbench sheet --items data/searchbench/test.jsonl \
    --runs offline=results/searchbench/offline.jsonl atlas=results/searchbench/atlas.jsonl \
    --out rating.html --key results/searchbench/key.json
python -m experiments.searchbench score --items data/searchbench/test.jsonl --key results/searchbench/key.json \
    --ratings ratings/r1.json ratings/r2.json [ratings/r3.json]
```

`rating.html` is one static page (no server, no system names); each rater downloads a JSON file. Where the two
disagree, a third person rates those answers. `score` prints S1–S3; S4–S6 come from the run files.
