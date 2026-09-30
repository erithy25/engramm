#!/usr/bin/env bash
# Build the lite knowledge pack from scratch (raw DBpedia / Wikidata / article leads → pack folder).
#   bash scripts/build_pack.sh            result: /dev/shm/engramm/packs/lite (+ manifest.json)
# Needs ~6 GB free space under /dev/shm/engramm (a symlink to a disk folder is fine) and ~1.5 h,
# most of it the Wikidata queries. Each step keeps its downloads, so a stopped run continues.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
W=/dev/shm/engramm
TOP="${TOP:-400000}"
export PYTHON="$PY"
bash scripts/rebuild_kb.sh
"$PY" -u -m experiments.reading_abstracts --top 1500000
"$PY" -u -m experiments.kb_slim --src "$W/kb/final/kb.sqlite" --top 150000 --out "$W/kb/lite/kb.sqlite"
"$PY" -u -m experiments.spell_build --abstracts "$W/reading/abstracts.jsonl" --top "$TOP" --out "$W/spell.json"
mkdir -p "$W/nlp_ship"
cp models/ship/intent.json "$W/nlp_ship/"
"$PY" -u -m experiments.pack_build --name lite --abstracts "$W/reading/abstracts.jsonl" --top "$TOP" \
  --kb "$W/kb/lite/kb.sqlite" --spell "$W/spell.json" --nlp "$W/nlp_ship" \
  --models models/ship --codebook models/ship/codebook.npz --out "$W/packs/lite"
