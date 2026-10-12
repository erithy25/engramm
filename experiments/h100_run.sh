#!/usr/bin/env bash
# H100 run toward Stage 1 (docs/H100_ANLEITUNG.md). On the GPU machine, from the repository root:
#   nohup bash experiments/h100_run.sh > /workspace/h100_console.log 2>&1 &
# Resumable: finished stages are skipped, the main training continues from its last state file.
#
# Stages:  0 checks · 1 packages · 2 base data (bit-identical to the CPU machine) · 3 learning-rate sweep on the
#          GPU while the extra C4 text is prepared on the CPU · 4 merge · 5 contamination check · 6 main training
#          + final evaluation · 7 results: to GitHub (branch + draft release with the model) if GH_TOKEN is set,
#          then the pod deletes itself — only after both uploads were verified.
# Settings (environment): H100_BUDGET_HOURS (main training, default 5.5), H100_SHARDS (default 36),
#          H100_TOKENS (default 6000000000), H100_PRICE (USD per hour, for the cost display, default 3.99),
#          H100_AUTO_END = terminate | stop | none (default terminate; acts only after verified uploads).
set -uo pipefail
cd "$(dirname "$0")/.."
REPO_DIR=$(pwd)
W=${H100_WORK:-/workspace/h100}
mkdir -p "$W/stages" "$W/ckpt"
export H100_CKPT_DIR="$W/ckpt"
LOG="$W/run.log"
exec > >(tee -a "$LOG") 2>&1
BUDGET=${H100_BUDGET_HOURS:-5.5}
SHARDS=${H100_SHARDS:-36}
TOKENS=${H100_TOKENS:-6000000000}
AUTO_END=${H100_AUTO_END:-terminate}
NCPU=$(nproc)
say() { echo "[$(date -u +%H:%M:%S)] $*"; }
done_() { [ -f "$W/stages/$1" ]; }
mark() { date -u > "$W/stages/$1"; }
fail() { say "FEHLER: $*"; say "Der Lauf ist angehalten. Bitte diese Zeilen an Claude schicken. Neustart mit demselben Befehl setzt fort."; echo "$*" > "$W/FAILED"; exit 1; }
rm -f "$W/FAILED"
[ -f "$W/started" ] || date -u +%s > "$W/started"
say "=== ENGRAMM H100-Lauf (Stufe 1), Arbeitsordner $W ==="

# --- 0. checks ---------------------------------------------------------------------------------------------
say "== 0. Prüfungen"
command -v nvidia-smi >/dev/null || fail "nvidia-smi fehlt – das ist kein GPU-Rechner"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || fail "nvidia-smi meldet keine GPU"
python3 - <<'EOF' || fail "Python/torch/GPU nicht passend (siehe oben)"
import sys, shutil, os
import torch
assert sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}: mindestens 3.10 nötig"
v = tuple(int(x) for x in torch.__version__.split("+")[0].split(".")[:2])
assert v >= (2, 4), f"torch {torch.__version__}: mindestens 2.4 nötig (Vorlage 'RunPod PyTorch' neuerer Version wählen)"
assert torch.cuda.is_available(), "torch sieht keine GPU"
name = torch.cuda.get_device_name(0)
mem = torch.cuda.get_device_properties(0).total_memory / 2**30
assert mem >= 40, f"{name} mit {mem:.0f} GB: zu wenig GPU-Speicher (H100 80 GB erwartet)"
free = shutil.disk_usage(os.getcwd()).free / 2**30
assert free >= 60, f"nur {free:.0f} GB frei auf dem Arbeitslaufwerk: mindestens 60 GB nötig (Volume 100 GB wählen)"
ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
assert ram >= 48, f"nur {ram:.0f} GB Arbeitsspeicher: mindestens 48 GB nötig"
print(f"OK: Python {sys.version.split()[0]}, torch {torch.__version__}, {name} {mem:.0f} GB, {free:.0f} GB frei, {ram:.0f} GB RAM")
EOF
if [ "$(python3 -c 'import torch;print(int("H100" in torch.cuda.get_device_name(0)))')" != "1" ]; then
  say "Hinweis: keine H100 – der Lauf funktioniert, dauert aber anders; die Zeitgrenze kürzt notfalls die Tokenzahl."
fi

# --- 1. packages ---------------------------------------------------------------------------------------------
if ! done_ packages; then
  say "== 1. Pakete"
  python3 -m pip install -q "tokenizers==0.23.2" "pyarrow>=14" || fail "pip install fehlgeschlagen"
  python3 -c "import numpy, tokenizers, pyarrow; assert tokenizers.__version__ == '0.23.2'" || fail "Pakete nicht importierbar"
  mark packages
fi

# --- 2. base data ---------------------------------------------------------------------------------------------
if ! done_ base; then
  say "== 2. Basisdaten (C4-Teil 0 + WikiText-103, bitgleich zum CPU-Rechner)"
  ok=0
  for attempt in 1 2 3; do
    python3 -m experiments.h100_data base && { ok=1; break; }
    say "Versuch $attempt fehlgeschlagen, neuer Versuch in 30 s"; sleep 30
  done
  [ $ok = 1 ] || fail "Basisdaten konnten nicht gebaut/geprüft werden"
  mark base
fi

# --- 3. sweep (GPU) while the extra text is prepared (CPU) ------------------------------------------------------
if ! done_ sweep || ! done_ extra; then
  say "== 3. Lernraten-Suche auf der GPU, parallel: $SHARDS zusätzliche C4-Teile auf der CPU"
  spid=""
  if ! done_ sweep; then
    python3 -m experiments.h100_train sweep > "$W/sweep.log" 2>&1 &
    spid=$!
  fi
  if ! done_ extra; then
    RAYON_NUM_THREADS=$(( NCPU > 6 ? NCPU - 4 : 2 )) python3 -m experiments.h100_data extra --shards "$SHARDS" \
      || { [ -n "$spid" ] && kill "$spid" 2>/dev/null; fail "zusätzliche C4-Daten fehlgeschlagen"; }
    mark extra
  fi
  if [ -n "$spid" ]; then
    wait "$spid" || { tail -30 "$W/sweep.log"; fail "Lernraten-Suche fehlgeschlagen (siehe $W/sweep.log)"; }
    tail -3 "$W/sweep.log"
    mark sweep
  fi
fi
LR=$(python3 -c "import json;print(json.load(open('results/v5/h100/sweep.json'))['lr'])") || fail "sweep.json fehlt"
say "gewählte Lernrate: $LR"

# --- 4. merge -------------------------------------------------------------------------------------------------
if ! done_ merge; then
  say "== 4. Ein Trainingsstrom aus Basis + Zusatztext"
  python3 -m experiments.h100_data merge --shards "$SHARDS" || fail "Zusammenführen fehlgeschlagen"
  mark merge
fi

# --- 5. contamination -------------------------------------------------------------------------------------------
if ! done_ contamination; then
  say "== 5. Kontaminationsprüfung (13-Token-Fenster aller val/test-Dokumente im Trainingstext)"
  python3 -m experiments.h100_data contamination --workers $(( NCPU > 4 ? (NCPU - 2 > 16 ? 16 : NCPU - 2) : 1 )) \
    || fail "Kontaminationsprüfung fehlgeschlagen"
  mark contamination
fi

# --- 6. main training + final evaluation ---------------------------------------------------------------------------
TAG=main
if ! done_ main; then
  say "== 6. Haupttraining (bis $TOKENS Token, Zeitgrenze $BUDGET h) und Endmessung"
  python3 -m experiments.h100_train train --lr "$LR" --tag main --total-tokens "$TOKENS" --budget-hours "$BUDGET"
  rc=$?
  if [ $rc = 3 ]; then
    LR2=$(python3 -c "print($LR / 2)")
    say "Training divergiert – einmaliger Neustart mit halber Lernrate $LR2"
    TAG=main_lrhalf
    python3 -m experiments.h100_train train --lr "$LR2" --tag main_lrhalf --total-tokens "$TOKENS" --budget-hours "$BUDGET" \
      || fail "Training auch mit halber Lernrate fehlgeschlagen"
  elif [ $rc != 0 ]; then
    fail "Haupttraining mit Code $rc beendet (Neustart mit demselben Befehl setzt am letzten Stand fort)"
  fi
  echo "$TAG" > "$W/stages/main"
fi
TAG=$(cat "$W/stages/main" 2>/dev/null | head -1)
case "$TAG" in main|main_lrhalf) ;; *) TAG=main ;; esac

# --- 7. results ---------------------------------------------------------------------------------------------------
say "== 7. Ergebnisse"
python3 - "$TAG" <<'EOF' | tee "$W/SUMMARY.txt"
import json, sys
tag = sys.argv[1]
r = json.load(open(f"results/v5/h100/eval_{tag}.json"))
s = r["stage1"]
print(f"Stufe 1 (GPT-2-Niveau): {'ERREICHT' if s['reached'] else 'nicht erreicht'}")
print(f"  Test, gefiltert: {r['test']['bpb']:.4f} bpb   (Ziel 1.04, GPT-2 small 1.039)")
print(f"  val-A:           {r['val_a']['bpb']:.4f} bpb")
for v in r.get("vs_gpt2", []):
    print(f"  gegen GPT-2 ({v['filter']}): Verhältnis {v['ratio_to_gpt2']:.3f}, 95 %-KI {v['ratio_ci95'][0]:.3f}–{v['ratio_ci95'][1]:.3f}")
print(f"  trainiert: {r['tokens'] / 1e9:.2f} Mrd. Token in {r['train_hours']:.2f} h auf {r['device']}")
EOF
cp "$W/run.log" results/v5/h100/run.log 2>/dev/null
MODEL="$W/ckpt/model_$TAG.pt"
uploaded=0
if [ -n "${GH_TOKEN:-}" ]; then
  say "Ergebnisse nach GitHub (Branch) und Modell als privater Entwurf-Release …"
  BR="h100-results-$(date -u +%Y%m%d-%H%M)"
  CRED='!f() { echo username=x-access-token; echo "password=$GH_TOKEN"; }; f'
  git config user.email "h100-run@users.noreply.github.com"
  git config user.name "ENGRAMM H100-Lauf"
  git checkout -q -b "$BR" && git add -f results/v5/h100 && \
  git commit -q -m "v5/H100: Ergebnisse des Stufe-1-Laufs ($TAG), automatisch vom GPU-Rechner" && \
  GH_TOKEN="$GH_TOKEN" git -c credential.helper= -c credential.helper="$CRED" push -q https://github.com/erithy25/engramm.git "$BR" \
    && pushed=1 || pushed=0
  if [ "${pushed:-0}" = 1 ] && git ls-remote https://github.com/erithy25/engramm.git "refs/heads/$BR" | grep -q "$BR"; then
    say "Ergebnisse auf GitHub: Branch $BR"
    REL=$(curl -sS -X POST -H "Authorization: Bearer $GH_TOKEN" -H "Accept: application/vnd.github+json" \
      https://api.github.com/repos/erithy25/engramm/releases \
      -d "{\"tag_name\":\"$BR\",\"target_commitish\":\"$BR\",\"name\":\"H100 Stufe-1-Modell ($BR)\",\"draft\":true}")
    RID=$(python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('id',''))" <<< "$REL")
    if [ -n "$RID" ] && [ -f "$MODEL" ]; then
      SIZE=$(stat -c %s "$MODEL")
      ASSET=$(curl -sS -X POST -H "Authorization: Bearer $GH_TOKEN" -H "Content-Type: application/octet-stream" \
        --data-binary @"$MODEL" "https://uploads.github.com/repos/erithy25/engramm/releases/$RID/assets?name=model_$TAG.pt")
      GOT=$(python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('size',0))" <<< "$ASSET")
      if [ "$GOT" = "$SIZE" ]; then
        say "Modell hochgeladen (privater Entwurf-Release, $SIZE Bytes)"
        uploaded=1
      else
        say "Modell-Upload unvollständig ($GOT von $SIZE Bytes) – Modell bleibt auf dem Pod: $MODEL"
      fi
    else
      say "Release konnte nicht angelegt werden – Modell bleibt auf dem Pod: $MODEL"
    fi
  else
    say "Push nach GitHub fehlgeschlagen – Ergebnisse bleiben auf dem Pod: $REPO_DIR/results/v5/h100"
  fi
else
  say "Kein GH_TOKEN gesetzt: Ergebnisse liegen in $REPO_DIR/results/v5/h100, das Modell in $MODEL"
fi
tar czf "$W/h100_results.tgz" -C "$REPO_DIR" results/v5/h100 2>/dev/null
say "Archiv zum Herunterladen: $W/h100_results.tgz  (Modell: $MODEL)"
mark finished

# --- end: never leave an expensive GPU idling, never delete anything that is not saved elsewhere --------------------
if [ "$uploaded" = 1 ] && [ -n "${RUNPOD_POD_ID:-}" ] && [ "$AUTO_END" != none ]; then
  say "FERTIG. Ergebnisse und Modell sind auf GitHub gesichert. Der Pod beendet sich in 2 Minuten selbst ($AUTO_END)."
  sleep 120
  ended=0
  if [ "$AUTO_END" = terminate ]; then
    runpodctl remove pod "$RUNPOD_POD_ID" 2>/dev/null || runpodctl pod delete "$RUNPOD_POD_ID" 2>/dev/null && ended=1
  fi
  if [ $ended = 0 ]; then
    runpodctl stop pod "$RUNPOD_POD_ID" 2>/dev/null || runpodctl pod stop "$RUNPOD_POD_ID" 2>/dev/null && ended=1
  fi
  [ $ended = 1 ] || say "Selbstbeendigung hat nicht geklappt – bitte den Pod jetzt in der RunPod-Konsole beenden (Stop, dann Terminate)."
else
  say "FERTIG. JETZT: Archiv und Modell herunterladen (Anleitung Schritt 5), danach den Pod BEENDEN – er kostet sonst weiter."
fi
