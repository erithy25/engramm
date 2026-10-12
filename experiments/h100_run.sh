#!/usr/bin/env bash
# H100 run toward Stage 1 (docs/H100_ANLEITUNG.md). On the GPU machine (any directory):
#   setsid nohup bash /workspace/engramm/experiments/h100_run.sh > /workspace/h100_console.log 2>&1 &
# Resumable: finished stages are skipped, the main training continues from its last state file. A second
# start while a run is alive exits at once (lock).
#
# Stages:  0 checks (GPU, disk, GitHub key can write) · 1 packages (checked on every start: the container disk is
#          wiped on a pod restart) · 2 base data (bit-identical to the CPU machine) · 3 learning-rate sweep on the
#          GPU while the extra C4 text is prepared on the CPU · 4 merge · 5 contamination check · 6 main training
#          + final evaluation · 7 results to GitHub (branch + private draft release with the model), then the pod
#          deletes itself — only after both uploads were verified.
# Cost guards: after a FEHLER, or when the uploads failed, the pod stops itself after 2 h (GPU billing ends,
#          /workspace with all data stays; `touch /workspace/h100/KEEP` prevents it).
# Settings (environment): H100_BUDGET_HOURS (main training, default 5.5), H100_SHARDS (36), H100_TOKENS (6000000000),
#          H100_AUTO_END = terminate | stop | none (default terminate), H100_NO_GITHUB=1 (run without a GitHub key).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
REPO_DIR=$(pwd)
W=${H100_WORK:-/workspace/h100}
mkdir -p "$W/stages" "$W/ckpt"
exec 9>/tmp/engramm_h100.lock
if ! flock -n 9; then
  echo "Lauf läuft bereits – kein zweiter Start nötig. Status: bash /workspace/engramm/experiments/h100_status.sh"
  exit 0
fi
export H100_CKPT_DIR="$W/ckpt"
LOG="$W/run.log"
exec > >(tee -a "$LOG") 2>&1
BUDGET=${H100_BUDGET_HOURS:-5.5}
SHARDS=${H100_SHARDS:-36}
TOKENS=${H100_TOKENS:-6000000000}
AUTO_END=${H100_AUTO_END:-terminate}
RESTART="setsid nohup bash /workspace/engramm/experiments/h100_run.sh > /workspace/h100_console.log 2>&1 &"
CRED='!f() { echo username=x-access-token; echo "password=$GH_TOKEN"; }; f'
GHREPO=https://github.com/erithy25/engramm.git
# GitHub actions only on a RunPod pod (or when explicitly allowed): a test elsewhere must never push anything
if [ -z "${RUNPOD_POD_ID:-}" ] && [ "${H100_ALLOW_GITHUB_OFFPOD:-0}" != 1 ]; then GH_TOKEN=""; H100_NO_GITHUB=1; fi
# CPUs actually granted (nproc may report the whole host inside a CPU-quota container)
NCPU=$(python3 -c "
import os
n = len(os.sched_getaffinity(0))
try:
    q, p = open('/sys/fs/cgroup/cpu.max').read().split()[:2]
    if q != 'max':
        n = min(n, max(1, int(q) // int(p)))
except Exception:
    pass
print(n)" 2>/dev/null || nproc)
say() { echo "[$(date -u +%H:%M:%S) UTC] $*"; }
done_() { [ -f "$W/stages/$1" ]; }
# test mode (CPU machine): stages that download, build or train for real are refused, never run by accident
heavy() { if [ "${H100_TEST_SKIP_GPU:-0}" = 1 ] && [ "${H100_TEST_ALLOW_HEAVY:-0}" != 1 ]; then
            fail "TEST-MODUS: Stufe '$1' würde jetzt echt laufen (Download/Training) – im Testmodus gesperrt"; fi; }
mark() { date -u > "$W/stages/$1"; }
# Stop the pod after a delay unless the situation changed (new start, KEEP file); never holds the run lock.
autostop_later() {  # seconds marker-file
  [ -n "${RUNPOD_POD_ID:-}" ] && [ "$AUTO_END" != none ] || return 0
  local id; id=$(head -1 "$2" 2>/dev/null)
  ( exec 9>&-; sleep "$1"
    [ -f "$W/KEEP" ] && exit 0
    [ "$(head -1 "$2" 2>/dev/null)" = "$id" ] || exit 0
    flock -n /tmp/engramm_h100.lock true || exit 0      # a new run is alive: leave it alone
    runpodctl stop pod "$RUNPOD_POD_ID" 2>/dev/null || runpodctl pod stop "$RUNPOD_POD_ID" 2>/dev/null
  ) >/dev/null 2>&1 &
}
fail() {
  say "FEHLER: $*"
  say "Der Lauf ist angehalten. Bitte diese Zeilen an Claude schicken. Neustart (setzt fort): zuerst Befehl 2 (Schlüssel), dann:"
  say "  $RESTART"
  echo "$(date +%s) $*" > "$W/FAILED"
  say "Kostenschutz: ohne Neustart stoppt sich der Pod in 2 Stunden selbst (Daten in /workspace bleiben erhalten)."
  autostop_later 7200 "$W/FAILED"
  exit 1
}
rm -f "$W/FAILED" "$W/NOT_UPLOADED"
[ -f "$W/started" ] || date -u +%s > "$W/started"
say "=== ENGRAMM H100-Lauf (Stufe 1), Arbeitsordner $W, $NCPU CPUs ==="

# --- 0. checks ---------------------------------------------------------------------------------------------
say "== 0. Prüfungen"
if [ "${H100_TEST_SKIP_GPU:-0}" = 1 ]; then
  say "TEST-MODUS: GPU-Prüfungen übersprungen (nur für Tests auf dem CPU-Rechner)"
elif done_ main; then                                       # only the upload is left: works on a pod without GPU
  say "Training bereits fertig: GPU-Prüfungen übersprungen (nur noch Ergebnisse/Upload)"
else
command -v nvidia-smi >/dev/null || fail "nvidia-smi fehlt – das ist kein GPU-Rechner"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || fail "nvidia-smi meldet keine GPU"
python3 - "$W" <<'EOF' || fail "Python/torch/GPU/Platte nicht passend (siehe oben)"
import sys, shutil, os
import torch
W = sys.argv[1]
assert sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}: mindestens 3.10 nötig"
v = tuple(int(x) for x in torch.__version__.split("+")[0].split(".")[:2])
assert v >= (2, 4), f"torch {torch.__version__}: mindestens 2.4 nötig (Vorlage 'Runpod PyTorch' neuerer Version wählen)"
assert torch.cuda.is_available(), "torch sieht keine GPU (Treiber/CUDA passen nicht zur Vorlage)"
name = torch.cuda.get_device_name(0)
mem = torch.cuda.get_device_properties(0).total_memory / 2**30
assert mem >= 40, f"{name} mit {mem:.0f} GB: zu wenig GPU-Speicher (H100 80 GB erwartet)"
need = 10 if os.path.exists(f"{W}/stages/base") else 60     # the run's own data fills the volume later on
free = shutil.disk_usage(os.getcwd()).free / 2**30
assert free >= need, f"nur {free:.0f} GB frei auf dem Arbeitslaufwerk: mindestens {need} GB nötig"
ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
assert ram >= 48, f"nur {ram:.0f} GB Arbeitsspeicher: mindestens 48 GB nötig"
print(f"OK: Python {sys.version.split()[0]}, torch {torch.__version__}, {name} {mem:.0f} GB, {free:.0f} GB frei, {ram:.0f} GB RAM")
EOF
fi
[ -f models/lm/gpt2/eval_test.json ] || fail "GPT-2-Referenz models/lm/gpt2/eval_test.json fehlt im Checkout"
if [ -n "${GH_TOKEN:-}" ]; then
  GIT_TERMINAL_PROMPT=0 timeout 90 git -c credential.helper= -c credential.helper="$CRED" \
    push --dry-run -q "$GHREPO" HEAD:refs/heads/h100-token-check >/dev/null 2>&1 \
    || { echo "NEIN (ungültig oder ohne Schreibrecht)" > "$W/github_check"
         fail "GitHub-Schlüssel ungültig oder ohne Schreibrecht (bei 'Contents' muss 'Read and write' stehen) – neuen Schlüssel anlegen, Befehl 2, dann Befehl 3"; }
  echo "ja (Schreibrecht bestätigt, $(date -u +%H:%M) UTC)" > "$W/github_check"
  say "GitHub-Schlüssel: Schreibrecht bestätigt"
elif [ "${H100_NO_GITHUB:-0}" != 1 ]; then
  echo "NEIN (kein Schlüssel gesetzt)" > "$W/github_check"
  fail "Kein GitHub-Schlüssel gesetzt (Befehl 2 vergessen?). Ohne Schlüssel bewusst starten: zuerst  export H100_NO_GITHUB=1  dann Befehl 3"
else
  echo "aus (bewusst ohne Schlüssel – Ergebnisse bleiben auf dem Pod)" > "$W/github_check"
  say "Ohne GitHub-Schlüssel: Ergebnisse und Modell bleiben auf dem Pod (Anleitung Schritt 5b)"
fi
if [ "${H100_TEST_SKIP_GPU:-0}" != 1 ] && ! done_ main && [ "$(python3 -c 'import torch;print(int("H100" in torch.cuda.get_device_name(0)))')" != "1" ]; then
  say "Hinweis: keine H100 – der Lauf funktioniert, dauert aber anders; die Zeitgrenze kürzt notfalls die Tokenzahl."
fi

# --- 1. packages (every start: the container disk does not survive a pod restart) ------------------------------
PKG_CHECK='import numpy, tokenizers, pyarrow; assert tokenizers.__version__ == "0.23.2", tokenizers.__version__'
if ! python3 -c "$PKG_CHECK" 2>/dev/null; then
  say "== 1. Pakete"
  PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install -q "tokenizers==0.23.2" "pyarrow>=14" || fail "pip install fehlgeschlagen"
  python3 -c "$PKG_CHECK" || fail "Pakete nicht importierbar"
fi
mark packages

# --- 2. base data ---------------------------------------------------------------------------------------------
if ! done_ base; then
  heavy base
  say "== 2. Basisdaten (C4-Teil 0 + WikiText-103, bitgleich zum CPU-Rechner)"
  ok=0
  for attempt in 1 2 3; do
    python3 -m experiments.h100_data base && { ok=1; break; }
    say "Basisdaten: Versuch $attempt fehlgeschlagen, neuer Versuch in 60 s"; sleep 60
  done
  [ $ok = 1 ] || fail "Basisdaten konnten nicht gebaut/geprüft werden"
  mark base
fi

# --- 3. sweep (GPU) while the extra text is prepared (CPU) ------------------------------------------------------
if ! done_ sweep || ! done_ extra; then
  heavy sweep/extra
  say "== 3. Lernraten-Suche auf der GPU, parallel: $SHARDS zusätzliche C4-Teile auf der CPU"
  spid=""
  if ! done_ sweep; then
    python3 -m experiments.h100_train sweep > "$W/sweep.log" 2>&1 &
    spid=$!
  fi
  if ! done_ extra; then
    ok=0
    for attempt in 1 2 3 4 5 6; do
      RAYON_NUM_THREADS=$(( NCPU > 20 ? 16 : (NCPU > 6 ? NCPU - 4 : 2) )) \
        python3 -m experiments.h100_data extra --shards "$SHARDS" && { ok=1; break; }
      say "Zusatztext: Versuch $attempt fehlgeschlagen (fertige Teile bleiben), neuer Versuch in 5 min"; sleep 300
    done
    if [ $ok != 1 ]; then
      [ -n "$spid" ] && { say "warte noch auf die Lernraten-Suche …"; wait "$spid" && mark sweep; }
      fail "zusätzliche C4-Daten fehlgeschlagen (Netzwerk?)"
    fi
    mark extra
  fi
  if [ -n "$spid" ]; then
    wait "$spid" || { tail -30 "$W/sweep.log"; fail "Lernraten-Suche fehlgeschlagen (siehe $W/sweep.log)"; }
    tail -3 "$W/sweep.log"
    mark sweep
  fi
fi
rm -f "$W"/ckpt/state_sweep_lr*.pt                         # sweep results live in sweep*.json; frees ~5 GB
LR=$(python3 -c "import json;print(json.load(open('results/v5/h100/sweep.json'))['lr'])") || fail "sweep.json fehlt"
say "gewählte Lernrate: $LR"

# --- 4. merge -------------------------------------------------------------------------------------------------
if ! done_ merge; then
  heavy merge
  say "== 4. Ein Trainingsstrom aus Basis + Zusatztext"
  python3 -m experiments.h100_data merge --shards "$SHARDS" || fail "Zusammenführen fehlgeschlagen"
  mark merge
fi

# --- 5. contamination -------------------------------------------------------------------------------------------
if ! done_ contamination; then
  heavy contamination
  say "== 5. Kontaminationsprüfung (13-Token-Fenster aller val/test-Dokumente im Trainingstext)"
  python3 -m experiments.h100_data contamination --workers $(( NCPU > 4 ? (NCPU - 2 > 16 ? 16 : NCPU - 2) : 1 )) \
    || fail "Kontaminationsprüfung fehlgeschlagen"
  mark contamination
fi

# --- 6. main training + final evaluation ---------------------------------------------------------------------------
if ! done_ main; then
  heavy main
  say "== 6. Haupttraining (bis $TOKENS Token, Zeitgrenze $BUDGET h) und Endmessung"
  if [ -f "$W/stages/main_diverged" ]; then
    rc=3                                                    # decided earlier: continue the half-rate run
  else
    python3 -m experiments.h100_train train --lr "$LR" --tag main --total-tokens "$TOKENS" --budget-hours "$BUDGET"
    rc=$?
  fi
  TAG=main
  if [ $rc = 3 ]; then
    echo "$LR" > "$W/stages/main_diverged"
    LR2=$(python3 -c "print($LR / 2)")
    say "Training divergiert – Lauf mit halber Lernrate $LR2 (einmalig)"
    TAG=main_lrhalf
    python3 -m experiments.h100_train train --lr "$LR2" --tag main_lrhalf --total-tokens "$TOKENS" --budget-hours "$BUDGET" \
      || fail "Training mit halber Lernrate fehlgeschlagen (Neustart setzt am letzten Stand fort)"
  elif [ $rc != 0 ]; then
    fail "Haupttraining mit Code $rc beendet (Neustart setzt am letzten Stand fort)"
  fi
  echo "$TAG" > "$W/stages/main"
fi
TAG=$(head -1 "$W/stages/main" 2>/dev/null)
case "$TAG" in main|main_lrhalf) ;; *) TAG=main ;; esac

# --- 7. results ---------------------------------------------------------------------------------------------------
say "== 7. Ergebnisse"
python3 - "$TAG" <<'EOF' | tee "$W/SUMMARY.txt"
import json, sys
tag = sys.argv[1]
r = json.load(open(f"results/v5/h100/eval_{tag}.json"))
s = r["stage1"]
print(f"Stufe 1 (GPT-2-Niveau): {'ERREICHT' if s['reached'] else 'nicht erreicht'}")
print(f"  Test ({s['filter']}): {s['bpb']:.4f} bpb   (Ziel 1.04; mit der alten Filterliste {s['bpb_original_filter']:.4f})")
print(f"  val-A:           {r['val_a']['bpb']:.4f} bpb")
for v in r.get("vs_gpt2", []):
    print(f"  gegen GPT-2 ({v['filter']}): Verhältnis {v['ratio_to_gpt2']:.3f}, 95 %-KI {v['ratio_ci95'][0]:.3f}–{v['ratio_ci95'][1]:.3f}")
print(f"  trainiert: {r['tokens'] / 1e9:.2f} Mrd. Token in {r['train_hours']:.2f} h auf {r['device']}")
EOF
cp "$W/run.log" results/v5/h100/run.log 2>/dev/null
MODEL="$W/ckpt/model_$TAG.pt"
[ -f "$MODEL" ] && { ln -f "$MODEL" "$W/MODELL.pt" 2>/dev/null || cp "$MODEL" "$W/MODELL.pt"; }
tar czf "$W/h100_results.tgz" -C "$REPO_DIR" results/v5/h100 2>/dev/null
uploaded=0
if [ -f "$W/stages/uploaded" ]; then
  uploaded=1
elif [ -n "${GH_TOKEN:-}" ]; then
  say "Ergebnisse nach GitHub (Branch) und Modell als privater Entwurf-Release …"
  BR=$(cat "$W/stages/branch" 2>/dev/null || echo "h100-results-$(date -u +%Y%m%d-%H%M)")
  echo "$BR" > "$W/stages/branch"
  git config user.email "h100-run@users.noreply.github.com"
  git config user.name "ENGRAMM H100-Lauf"
  if [ "$(git rev-parse --abbrev-ref HEAD)" != "$BR" ]; then git checkout -q -B "$BR"; fi
  git add -f results/v5/h100
  git diff --cached --quiet || git commit -q -m "v5/H100: Ergebnisse des Stufe-1-Laufs ($TAG), automatisch vom GPU-Rechner"
  pushed=0
  for attempt in 1 2 3; do
    GIT_TERMINAL_PROMPT=0 timeout 900 git -c credential.helper= -c credential.helper="$CRED" push -q "$GHREPO" "$BR" \
      && GIT_TERMINAL_PROMPT=0 timeout 120 git -c credential.helper= -c credential.helper="$CRED" \
           ls-remote "$GHREPO" "refs/heads/$BR" | grep -q "$BR" && { pushed=1; break; }
    say "Push Versuch $attempt fehlgeschlagen, neuer Versuch in 60 s"; sleep 60
  done
  if [ $pushed = 1 ]; then
    say "Ergebnisse auf GitHub: Branch $BR"
    RID=$(cat "$W/stages/release_id" 2>/dev/null)
    if [ -z "$RID" ]; then
      REL=$(curl -sS --connect-timeout 30 --max-time 120 -X POST -H "Authorization: Bearer $GH_TOKEN" \
        -H "Accept: application/vnd.github+json" -H "Content-Type: application/json" \
        https://api.github.com/repos/erithy25/engramm/releases \
        -d "{\"tag_name\":\"$BR\",\"target_commitish\":\"$BR\",\"name\":\"H100 Stufe-1-Modell ($BR)\",\"draft\":true}")
      RID=$(python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('id',''))" <<< "$REL" 2>/dev/null)
      if [ -n "$RID" ]; then
        echo "$RID" > "$W/stages/release_id"
      else
        say "Release nicht angelegt: $(python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('message'))" <<< "$REL" 2>/dev/null)"
      fi
    fi
    if [ -n "$RID" ] && [ -f "$MODEL" ]; then
      SIZE=$(stat -c %s "$MODEL")
      # an earlier start may already have uploaded it (only its answer got lost): check before uploading again
      EXIST=$(curl -sS --connect-timeout 30 --max-time 120 -H "Authorization: Bearer $GH_TOKEN" \
        -H "Accept: application/vnd.github+json" "https://api.github.com/repos/erithy25/engramm/releases/$RID/assets?per_page=100")
      python3 -c "import json,sys; a=json.loads(sys.stdin.read()); sys.exit(0 if isinstance(a, list) and any(
          x.get('state') == 'uploaded' and x.get('size') == int(sys.argv[1]) for x in a) else 1)" "$SIZE" <<< "$EXIST" \
        2>/dev/null && uploaded=1
      for attempt in 1 2 3; do
        [ $uploaded = 1 ] && break
        # a fresh name per attempt and start: GitHub refuses a name that an interrupted upload still holds
        ASSET=$(curl -sS --connect-timeout 30 --max-time 1800 -X POST -H "Authorization: Bearer $GH_TOKEN" \
          -H "Content-Type: application/octet-stream" --data-binary @"$MODEL" \
          "https://uploads.github.com/repos/erithy25/engramm/releases/$RID/assets?name=model_${TAG}_$(date -u +%Y%m%d%H%M%S).pt")
        GOT=$(python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('size',0))" <<< "$ASSET" 2>/dev/null)
        if [ "$GOT" = "$SIZE" ]; then uploaded=1; break; fi
        say "Modell-Upload Versuch $attempt unvollständig: $(python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('message',''))" <<< "$ASSET" 2>/dev/null)"
        sleep 60
      done
      if [ $uploaded = 1 ]; then
        say "Modell hochgeladen (privater Entwurf-Release, $SIZE Bytes)"
        echo "$BR" > "$W/stages/uploaded"
      fi
    fi
  else
    say "Push nach GitHub fehlgeschlagen – Ergebnisse bleiben auf dem Pod"
  fi
fi
mark finished

# --- end: never leave an expensive GPU idling, never delete anything that is not saved elsewhere --------------------
if [ "$uploaded" = 1 ] && [ -n "${RUNPOD_POD_ID:-}" ] && [ "$AUTO_END" != none ]; then
  say "FERTIG. Ergebnisse und Modell sind auf GitHub gesichert (Branch $(cat "$W/stages/uploaded")). Der Pod beendet sich in 2 Minuten selbst."
  sleep 120
  ended=0
  if [ "$AUTO_END" = terminate ]; then
    runpodctl remove pod "$RUNPOD_POD_ID" 2>/dev/null || runpodctl pod delete "$RUNPOD_POD_ID" 2>/dev/null && ended=1
  fi
  if [ $ended = 0 ]; then
    runpodctl stop pod "$RUNPOD_POD_ID" 2>/dev/null || runpodctl pod stop "$RUNPOD_POD_ID" 2>/dev/null && ended=1
  fi
  sleep 60
  say "Selbstbeendigung hat nicht geklappt – bitte den Pod in der RunPod-Konsole beenden (Stop, dann Terminate). Alles ist gesichert."
elif [ "$uploaded" = 1 ]; then
  say "FERTIG. Ergebnisse und Modell sind auf GitHub gesichert. Den Pod jetzt beenden (Stop, dann Terminate)."
else
  say "FERTIG – aber NICHT auf GitHub gesichert. JETZT herunterladen (Anleitung Schritt 5b): $W/h100_results.tgz und $W/MODELL.pt"
  say "Kostenschutz: der Pod stoppt sich in 2 Stunden selbst (Daten in /workspace bleiben, Pod danach wieder startbar). Verhindern: touch $W/KEEP"
  date +%s > "$W/NOT_UPLOADED"
  autostop_later 7200 "$W/NOT_UPLOADED"
fi
