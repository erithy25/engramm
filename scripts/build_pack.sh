#!/usr/bin/env bash
# Build a knowledge pack from scratch (raw DBpedia / Wikidata / article leads → pack folder).
#   bash scripts/build_pack.sh            result: /dev/shm/engramm/packs/lite (+ manifest.json)
#   NAME=standard TOP=1500000 KB_TOP=1000000 bash scripts/build_pack.sh    the standard pack
# Needs ~6 GB free space under /dev/shm/engramm (a symlink to a disk folder is fine) and ~1.5 h,
# most of it the Wikidata queries. Each step keeps its downloads, so a stopped run continues.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
W=/dev/shm/engramm
TOP="${TOP:-400000}"
KB_TOP="${KB_TOP:-150000}"
NAME="${NAME:-lite}"
export PYTHON="$PY"
bash scripts/rebuild_kb.sh
"$PY" -u -m experiments.reading_abstracts --top 1500000
"$PY" -u -m experiments.kb_slim --src "$W/kb/final/kb.sqlite" --top "$KB_TOP" --out "$W/kb/$NAME/kb.sqlite"
"$PY" -u -m experiments.spell_build --abstracts "$W/reading/abstracts.jsonl" --top "$TOP" --out "$W/spell-$NAME.json"
mkdir -p "$W/nlp_ship"
cp models/ship/intent.json "$W/nlp_ship/"
"$PY" -u -m experiments.pack_build --name "$NAME" --abstracts "$W/reading/abstracts.jsonl" --top "$TOP" \
  --kb "$W/kb/$NAME/kb.sqlite" --spell "$W/spell-$NAME.json" --nlp "$W/nlp_ship" \
  --models models/ship --codebook models/ship/codebook.npz --out "$W/packs/$NAME"
