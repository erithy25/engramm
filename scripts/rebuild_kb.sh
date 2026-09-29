#!/usr/bin/env bash
# Rebuild the fact bank (docs: engramm/kb): DBpedia 2022.12 → compact → Wikidata fill.
#   bash scripts/rebuild_kb.sh            work in /dev/shm/engramm/kb, result in $WORK/final/kb.sqlite
# Every step keeps its downloads in the work folder, so a stopped run continues.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
WORK=/dev/shm/engramm/kb
mkdir -p "$WORK/final" "$WORK/tmp"
export SQLITE_TMPDIR="$WORK/tmp"
[ -s "$WORK/kb.sqlite" ] || "$PY" -u -m experiments.kb_dbpedia_build --work "$WORK" --out "$WORK/kb.sqlite"
[ -s "$WORK/final/kb.sqlite" ] || "$PY" -u -m experiments.kb_compact --src "$WORK/kb.sqlite" --out "$WORK/final/kb.sqlite"
"$PY" -u -m experiments.kb_wikidata_fill titles --top 150000
"$PY" -u -m experiments.kb_wikidata_fill fetch --workers 2
"$PY" -u -m experiments.kb_wikidata_fill merge --kb "$WORK/final/kb.sqlite"
ls -la "$WORK/final/kb.sqlite"
