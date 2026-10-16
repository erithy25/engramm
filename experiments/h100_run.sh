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
# Cost guards: a meter adds up the pod's running time over all its sessions; at H100_MAX_USD (default 25 $ at
#          H100_PRICE 4.01 $/h) it stops the pod, whatever the run is doing (a session started after the limit gets
#          30 min for results/download). The main training ends early enough to stay below the limit. After a FEHLER,
#          or when the uploads failed, the pod stops itself after 30 min. A stopped pod keeps /workspace with all
#          data; `touch /workspace/h100/KEEP` suspends the 30-min stops of this session (never the dollar limit).
# Settings (environment): H100_MAX_USD (25), H100_PRICE (4.01), H100_BUDGET_HOURS (main training, default 5.5),
#          H100_SHARDS (36), H100_TOKENS (10000000000: an upper bound; the dollar limit decides the actual number),
#          H100_AUTO_END = terminate | stop | none (default terminate), H100_NO_GITHUB=1 (run without a GitHub key).
# Results: model_main.pt (final, fp32) and state_main_predecay.pt (last state before the learning-rate decay: training
#          can continue from it later, elsewhere) go to the private draft release; results/v5/h100 to a branch.
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
rm -f /tmp/engramm_idle_stop                                # a run in this session cancels the status idle stop
export H100_CKPT_DIR="$W/ckpt"
LOG="$W/run.log"
exec > >(tee -a "$LOG") 2>&1
BUDGET=${H100_BUDGET_HOURS:-5.5}
PRICE=${H100_PRICE:-4.01}
MAX_USD=${H100_MAX_USD:-25}
RESERVE_S=1800                                              # final evaluation, samples, upload, self-termination
SHARDS=${H100_SHARDS:-36}
TOKENS=${H100_TOKENS:-10000000000}
AUTO_END=${H100_AUTO_END:-terminate}
RESTART="setsid nohup bash /workspace/engramm/experiments/h100_run.sh > /workspace/h100_console.log 2>&1 &"
CRED='!f() { echo username=x-access-token; echo "password=$GH_TOKEN"; }; f'
GHREPO=https://github.com/erithy25/engramm.git
. "$REPO_DIR/experiments/h100_meter.sh"                    # cost meter, stop_pod
pod_env
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
# (The dollar limit of the cost meter applies in any case.)
autostop_later() {  # seconds marker-file
  [ -n "${RUNPOD_POD_ID:-}" ] && [ "$AUTO_END" != none ] || return 0
  local id; id=$(head -1 "$2" 2>/dev/null)
  ( exec 9>&-; sleep "$1"
    [ -f "$W/KEEP" ] && exit 0
    [ "$(head -1 "$2" 2>/dev/null)" = "$id" ] || exit 0
    flock -n /tmp/engramm_h100.lock true || exit 0      # a new run is alive: leave it alone
    stop_pod
  ) >/dev/null 2>&1 &
}
fail() {
  say "FEHLER: $*"
  say "Der Lauf ist angehalten. Bitte diese Zeilen an Claude schicken. Neustart (setzt fort): zuerst Befehl 2 (Schlüssel), dann:"
  say "  $RESTART"
  echo "$(date +%s) $*" > "$W/FAILED"
  say "Kostenschutz: ohne Neustart stoppt sich der Pod in 30 Minuten selbst (Daten in /workspace bleiben erhalten)."
  autostop_later 1800 "$W/FAILED"
  exit 1
}
rm -f "$W/FAILED" "$W/NOT_UPLOADED" "$W/KEEP"             # KEEP holds for one session only
[ -f "$W/started" ] || date -u +%s > "$W/started"

# --- cost meter (experiments/h100_meter.sh): billed pod time over all sessions; stops the pod at the dollar limit ------
mkdir -p "$W/meter"
echo "$MAX_USD $PRICE" > "$W/cost_limit"                   # read on every tick: a restart may raise the limit
start_meter
# after an unattended container restart the RunPod template runs /post_start.sh (container disk): the status
# command then re-arms the meter and the 30-min idle stop
if [ -n "${RUNPOD_POD_ID:-}" ] && [ -w / ]; then
  printf '#!/bin/bash\ncd %q && setsid bash experiments/h100_status.sh </dev/null >/dev/null 2>&1 &\n' "$REPO_DIR" > /post_start.sh \
    && chmod +x /post_start.sh
fi
usd_now() { awk -v s="$(billed_s)" -v p="$PRICE" 'BEGIN {printf "%.2f", s / 3600 * p}'; }
say "Kostenbremse: höchstens $MAX_USD \$ (bisher ≈ $(usd_now) \$); bei Erreichen stoppt sich der Pod selbst"
if [ "$(billed_s)" -ge "$(limit_s)" ]; then
  say "Kostengrenze bereits erreicht: kein weiteres Training, nur noch Ergebnisse sichern (nach der Grenze insgesamt höchstens 30 min). Mehr erlauben: export H100_MAX_USD=…"
fi
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
if [ -n "${RUNPOD_POD_ID:-}" ] && ! command -v runpodctl >/dev/null && [ -z "${RUNPOD_API_KEY:-}" ]; then
  fail "Weder runpodctl noch RUNPOD_API_KEY vorhanden – der Pod könnte sich nicht selbst stoppen (Kostenbremse). Bitte an Claude schicken"
fi
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
LRW=$(python3 -c "import json;print(json.load(open('results/v5/h100/sweep.json'))['lr'])") || fail "sweep.json fehlt"
# PLAN §11, Nachtrag 16. Oktober: the sweep runs 200 M tokens, the main run ~20× longer; the best rate falls with the
# horizon (Bjorck et al. 2024), so the main run uses half the sweep's choice, kept within [1e-3, 2e-3]
LR=$(python3 -c "print(min(2e-3, max(1e-3, $LRW * 0.5)))") || fail "Lernrate nicht berechenbar"
say "Lernrate: Suche wählte $LRW, für den langen Lauf ×0,5 in [1e-3, 2e-3]: $LR"

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
  DEADLINE=$(( $(date +%s) + $(limit_s) - $(billed_s) - RESERVE_S ))   # training ends in time for the dollar limit
  say "== 6. Haupttraining (bis $TOKENS Token, höchstens $BUDGET h; wegen der Kostenbremse spätestens bis $(date -u -d "@$DEADLINE" +%H:%M) UTC) und Endmessung"
  LRUSE=$LR; ALLOW=0
  if [ -f "$W/stages/main_diverged" ]; then LRUSE=$(head -1 "$W/stages/main_diverged"); ALLOW=1; fi
  python3 -m experiments.h100_train train --lr "$LRUSE" --tag main --total-tokens "$TOKENS" --budget-hours "$BUDGET" \
    --deadline "$DEADLINE" --allow-lr-change "$ALLOW"
  rc=$?
  if [ $rc = 3 ] && [ ! -f "$W/stages/main_diverged" ]; then
    LR2=$(python3 -c "print($LR / 2)")
    echo "$LR2" > "$W/stages/main_diverged"
    say "Training divergiert – weiter ab dem letzten Speicherstand mit halber Lernrate $LR2 (kein Neubeginn)"
    python3 -m experiments.h100_train train --lr "$LR2" --tag main --total-tokens "$TOKENS" --budget-hours "$BUDGET" \
      --deadline "$DEADLINE" --allow-lr-change 1
    rc=$?
  fi
  if [ $rc = 3 ]; then
    say "Training erneut divergiert – keine weiteren Versuche: Endmessung mit dem letzten gesicherten Stand"
    python3 -m experiments.h100_train train --lr "$(head -1 "$W/stages/main_diverged")" --tag main \
      --total-tokens "$TOKENS" --deadline 1 --allow-lr-change 1
    rc=$?
  fi
  [ $rc = 0 ] || fail "Haupttraining mit Code $rc beendet (Neustart setzt am letzten Stand fort)"
  echo main > "$W/stages/main"
fi
TAG=main

# --- 7. results ---------------------------------------------------------------------------------------------------
# One file into the draft release $RID, verified by its size; an earlier start may already have uploaded it.
upload_asset() {  # file name-prefix
  local f=$1 pre=$2 size exist asset got attempt
  size=$(stat -c %s "$f")
  exist=$(curl -sS --connect-timeout 30 --max-time 120 -H "Authorization: Bearer $GH_TOKEN" \
    -H "Accept: application/vnd.github+json" "https://api.github.com/repos/erithy25/engramm/releases/$RID/assets?per_page=100")
  if python3 -c "import json,sys; a=json.loads(sys.stdin.read()); sys.exit(0 if isinstance(a, list) and any(
      x.get('state') == 'uploaded' and x.get('size') == int(sys.argv[1]) and x.get('name', '').startswith(sys.argv[2])
      for x in a) else 1)" "$size" "$pre" <<< "$exist" 2>/dev/null; then
    say "$pre: bereits hochgeladen ($size Bytes)"; return 0
  fi
  local left mt
  for attempt in 1 2 3; do
    left=$(time_left)                                       # never upload into the cost meter's stop
    if [ "$left" -le 300 ]; then
      say "$pre: keine Zeit mehr vor der Kostenbremse – die Datei bleibt auf dem Pod (Anleitung Schritt 5b)"; return 1
    fi
    mt=$(( left - 240 )); [ "$mt" -le 2400 ] || mt=2400
    # a fresh name per attempt and start: GitHub refuses a name that an interrupted upload still holds;
    # a stalled transfer (< 200 kB/s for 2 min) is abandoned instead of eating the remaining time
    asset=$(curl -sS --connect-timeout 30 --speed-limit 200000 --speed-time 120 --max-time "$mt" -X POST -H "Authorization: Bearer $GH_TOKEN" \
      -H "Content-Type: application/octet-stream" --data-binary @"$f" \
      "https://uploads.github.com/repos/erithy25/engramm/releases/$RID/assets?name=${pre}_$(date -u +%Y%m%d%H%M%S).pt")
    got=$(python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('size',0))" <<< "$asset" 2>/dev/null)
    if [ "$got" = "$size" ]; then say "$pre hochgeladen ($size Bytes)"; return 0; fi
    say "$pre: Upload-Versuch $attempt unvollständig: $(python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('message',''))" <<< "$asset" 2>/dev/null)"
    sleep 60
  done
  return 1
}
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
PRE="$W/ckpt/state_${TAG}_predecay.pt"
[ -f "$PRE" ] || PRE="$W/ckpt/state_${TAG}.pt"              # training ended before the decay: that state continues
[ -f "$MODEL" ] && { ln -f "$MODEL" "$W/MODELL.pt" 2>/dev/null || cp "$MODEL" "$W/MODELL.pt"; }
[ -f "$PRE" ] && { ln -f "$PRE" "$W/FORTSETZEN.pt" 2>/dev/null || cp "$PRE" "$W/FORTSETZEN.pt"; }
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
    left=$(time_left); [ "$left" -gt 240 ] || { say "Push: keine Zeit mehr vor der Kostenbremse"; break; }
    pt=$(( left - 120 )); [ "$pt" -le 900 ] || pt=900          # the results push is small; everything else needs it
    GIT_TERMINAL_PROMPT=0 timeout "$pt" git -c credential.helper= -c credential.helper="$CRED" push -q "$GHREPO" "$BR" \
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
      ok_model=0; ok_pre=1                                  # the measured model first, then the continuation state
      upload_asset "$MODEL" "model_${TAG}" && ok_model=1
      [ -f "$PRE" ] && { upload_asset "$PRE" "fortsetzen_${TAG}" || ok_pre=0; }
      if [ $ok_model = 1 ] && [ $ok_pre = 1 ]; then
        uploaded=1
        say "Modell und Fortsetzungs-Stand hochgeladen (privater Entwurf-Release)"
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
    stop_pod && ended=1
  fi
  sleep 60
  say "Selbstbeendigung hat nicht geklappt – bitte den Pod in der RunPod-Konsole beenden (Stop, dann Terminate). Alles ist gesichert."
elif [ "$uploaded" = 1 ]; then
  say "FERTIG. Ergebnisse und Modell sind auf GitHub gesichert. Den Pod jetzt beenden (Stop, dann Terminate)."
else
  say "FERTIG – aber NICHT auf GitHub gesichert. JETZT herunterladen (Anleitung Schritt 5b): $W/h100_results.tgz, $W/MODELL.pt und $W/FORTSETZEN.pt"
  say "Kostenschutz: der Pod stoppt sich in 30 Minuten selbst (Daten in /workspace bleiben, Pod danach wieder startbar). Aussetzen: touch $W/KEEP (die Kostenbremse gilt trotzdem)"
  date +%s > "$W/NOT_UPLOADED"
  autostop_later 1800 "$W/NOT_UPLOADED"
fi
