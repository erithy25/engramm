#!/usr/bin/env bash
# ENGRAMM auf dem Mac einrichten und starten.
#
#   bash scripts/setup_mac.sh           # Schnellmodus: kleiner Satzindex + Spannenmodell (~5–10 Minuten)
#   bash scripts/setup_mac.sh --full    # volle Version wie im Test v14 (lädt ~20 GB Wikipedia, mehrere Stunden)
#
# Voraussetzung: das Sprachmodell liegt unter models/lm/main/model (meta.json). Alles andere baut dieses Skript.
# Schritte, die schon erledigt sind, werden übersprungen – das Skript kann jederzeit erneut gestartet werden.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
MODEL="$ROOT/models/lm/main"
FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

say() { printf '\n\033[1;35m▶ %s\033[0m\n' "$*"; }

say "Python-Umgebung"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
export PYTHONPATH="$ROOT"

if [[ ! -f "$MODEL/model/meta.json" ]]; then
  echo "Kein Sprachmodell unter $MODEL/model. Bauen mit:"
  echo "  python -m experiments.lm_final_model --scale main --tau-index 1 --beta-index 1 --save"
  exit 2
fi

say "Satzindex chat2 (kleiner Index, ~1 Minute)"
if [[ ! -f "$MODEL/chat2/info.json" ]]; then
  python -u -m experiments.chat_build --v2
else
  echo "vorhanden"
fi

say "Spannenmodell p2 (lädt SQuAD, ~5 Minuten)"
if [[ ! -f "$MODEL/chat2/spanperc_p2.json" ]]; then
  python -u -m experiments.chat_v2_perceptron --paragraph --passes 8 --out spanperc_p2.json
else
  echo "vorhanden"
fi

if [[ $FULL == 1 ]]; then
  say "Wikipedia lesen (41 Pakete, ~20 GB Download, Stunden)"
  python -u -m experiments.chat_wiki_build extract
  [[ -f "$MODEL/chat3/info.json" ]] || python -u -m experiments.chat_wiki_build index
  say "Ungelesene SQuAD-Absätze lesen (chat4)"
  python -u -m experiments.chat_squad_read select
  [[ -f "$MODEL/chat4/segment.json" ]] || python -u -m experiments.chat_squad_read index
  echo
  echo "Hinweis: Ensemble- und Konfidenzmodell der v14 (experiments/chat_v14_ensemble.py, chat_v13_calib.py)"
  echo "brauchen zusätzlich die Kandidaten-Caches der Entwicklungsdaten; bis dahin läuft ENGRAMM im Schnellmodus."
fi

say "Fertig. ENGRAMM startet: http://127.0.0.1:8770"
exec python -m engramm.app
