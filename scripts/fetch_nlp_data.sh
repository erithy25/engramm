#!/usr/bin/env bash
# Training data for engramm/nlp (docs/PREREG_NLP_V0.md): UD English EWT r2.14 and MASSIVE 1.1.
#   bash scripts/fetch_nlp_data.sh [DIR]      (default /dev/shm/engramm/nlp)
set -euo pipefail
DIR="${1:-/dev/shm/engramm/nlp}"
mkdir -p "$DIR"
UD=https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/r2.14
for s in train dev test; do
  [ -s "$DIR/en_ewt-ud-$s.conllu" ] || curl -fsSL --retry 4 -o "$DIR/en_ewt-ud-$s.conllu" "$UD/en_ewt-ud-$s.conllu"
done
[ -s "$DIR/LICENSE.txt" ] || curl -fsSL --retry 4 -o "$DIR/LICENSE.txt" "$UD/LICENSE.txt"
if [ ! -s "$DIR/1.1/data/en-US.jsonl" ]; then
  curl -fsSL --retry 4 -o "$DIR/massive.tar.gz" https://amazon-massive-nlu-dataset.s3.amazonaws.com/amazon-massive-dataset-1.1.tar.gz
  tar -xzf "$DIR/massive.tar.gz" -C "$DIR" 1.1/data/en-US.jsonl
  rm -f "$DIR/massive.tar.gz"
fi
wc -l "$DIR"/en_ewt-ud-*.conllu "$DIR/1.1/data/en-US.jsonl"
