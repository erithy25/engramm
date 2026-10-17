#!/usr/bin/env bash
# Sela-2 run on one rented GPU (docs/SELA2_ANLEITUNG.md). On the pod (any directory):
#   setsid nohup bash /workspace/engramm/experiments/sela2_run.sh > /workspace/sela2_console.log 2>&1 &
# Resumable: finished stages are skipped, pretraining continues from its last state. A second start while a run is
# alive exits at once (lock). Status: bash /workspace/engramm/experiments/sela2_status.sh
#
# Stages: 0 checks (GPU, disk, GitHub key can read the data and write) · 1 packages · 2 data (private draft release,
#         every file checked by SHA-256) · 3 probe (a tiny model through the whole path on the GPU, ≈ 3 min: compile,
#         flex attention, fine-tuning, evaluation, an upload to GitHub) · 4 pretraining (until the deadline) · 5 base
#         model to GitHub in the background · 6 chat fine-tuning (until its deadline) · 7 evaluation on the GPU ·
#         8 results to GitHub (branch + private draft release: chat model, base model, continuation state), then the
#         pod deletes itself — only after every upload was verified.
# Cost guards: the meter (experiments/h100_meter.sh) adds up the pod's running time over all its sessions; at
#         SELA2_MAX_USD (default 25 $) it stops the pod, with at most 10 min after the limit to save results. The
#         price is read from RunPod's API (never below the given price; fallback 4.01 $/h = H100 SXM Secure incl.
#         storage). Spend on an earlier pod: SELA2_SPENT_USD is subtracted from the limit. After a FEHLER before
#         training the pod stops itself after 10 min, later after 30 min (data in /workspace stay).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
REPO_DIR=$(pwd)
W=${SELA2_WORK:-/workspace/sela2}
mkdir -p "$W/stages" "$W/ckpt" "$W/data" "$W/up"
exec 9>/tmp/engramm_sela2.lock
if ! flock -n 9; then
  echo "Lauf läuft bereits – kein zweiter Start nötig. Status: bash /workspace/engramm/experiments/sela2_status.sh"
  exit 0
fi
export SELA2_CKPT_DIR="$W/ckpt" TORCHINDUCTOR_CACHE_DIR="$W/inductor" METER_GRACE_S=600
LOG="$W/run.log"
exec > >(tee -a "$LOG") 2>&1
setting() {  # name default — kept in $W/settings.env across restarts; an explicit export wins and is saved again
  local v="${!1:-}"
  [ -z "$v" ] && [ -f "$W/settings.env" ] && v=$(sed -n "s/^$1=//p" "$W/settings.env" | tail -1)
  echo "${v:-$2}"
}
MAX_USD=$(setting SELA2_MAX_USD 25)
SPENT_USD=$(setting SELA2_SPENT_USD 0)
PRICE_MIN=$(setting SELA2_PRICE 4.01)
RESERVE_PRE_S=2700                                          # after pretraining: SFT 20 + eval 7 + uploads 10 + margin 8 min
RESERVE_SFT_S=1080                                          # after fine-tuning: eval 7 + uploads 8 + margin 3 min
AUTO_END=${SELA2_AUTO_END:-terminate}
RESTART="setsid nohup bash /workspace/engramm/experiments/sela2_run.sh > /workspace/sela2_console.log 2>&1 &"
CRED='!f() { echo username=x-access-token; echo "password=$GH_TOKEN"; }; f'
GHREPO=https://github.com/erithy25/engramm.git
. "$REPO_DIR/experiments/h100_meter.sh"
pod_env
if [ -z "${RUNPOD_POD_ID:-}" ] && [ "${SELA2_ALLOW_GITHUB_OFFPOD:-0}" != 1 ]; then GH_TOKEN=""; SELA2_NO_GITHUB=1; fi
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
export OMP_NUM_THREADS=$NCPU MKL_NUM_THREADS=$NCPU             # CPU work never oversubscribes the pod's quota
say() { echo "[$(date -u +%H:%M:%S) UTC] $*"; }
done_() { [ -f "$W/stages/$1" ]; }
mark() { date -u > "$W/stages/$1"; }
test_mode() { [ "${SELA2_TEST:-0}" = 1 ]; }
autostop_later() {  # seconds marker-file
  [ -n "${RUNPOD_POD_ID:-}" ] && [ "$AUTO_END" != none ] || return 0
  local id; id=$(head -1 "$2" 2>/dev/null)
  ( exec 9>&-; sleep "$1"
    [ -f "$W/KEEP" ] && exit 0
    [ "$(head -1 "$2" 2>/dev/null)" = "$id" ] || exit 0
    flock -n /tmp/engramm_sela2.lock true || exit 0
    stop_pod ) >/dev/null 2>&1 &
}
fail() {
  say "FEHLER: $*"
  say "Der Lauf ist angehalten. Bitte diese Zeilen an Claude schicken. Neustart (setzt fort): zuerst Befehl 2 (Schlüssel), dann:"
  say "  $RESTART"
  echo "$(date +%s) $*" > "$W/FAILED"
  local wait_s=1800
  done_ pretrain_started || wait_s=600
  say "Kostenschutz: ohne Neustart stoppt sich der Pod in $(( wait_s / 60 )) Minuten selbst (Daten in /workspace bleiben erhalten)."
  autostop_later "$wait_s" "$W/FAILED"
  exit 1
}
rm -f "$W/FAILED" "$W/NOT_UPLOADED" "$W/KEEP"
num_ok() { python3 -c "import sys; v = float(sys.argv[1]); sys.exit(0 if $2 else 1)" "$1" 2>/dev/null; }
num_ok "$MAX_USD" "0 < v <= 100" || fail "SELA2_MAX_USD=$MAX_USD ist keine plausible Grenze in \$ (Punkt statt Komma)"
num_ok "$SPENT_USD" "0 <= v < 100" || fail "SELA2_SPENT_USD=$SPENT_USD ist kein plausibler Betrag"
num_ok "$PRICE_MIN" "1.0 <= v <= 20" || fail "SELA2_PRICE=$PRICE_MIN ist kein plausibler Stundenpreis"

# --- price: what RunPod bills this pod (+ storage), never below SELA2_PRICE -------------------------------------------
PRICE=$PRICE_MIN
if [ -n "${RUNPOD_API_KEY:-}" ] && [ -n "${RUNPOD_POD_ID:-}" ]; then
  API_P=$(curl -s --max-time 30 -H "Content-Type: application/json" \
    -d "{\"query\": \"query { pod(input: {podId: \\\"$RUNPOD_POD_ID\\\"}) { id costPerHr } }\"}" \
    "https://api.runpod.io/graphql?api_key=$RUNPOD_API_KEY" 2>/dev/null \
    | python3 -c "import json,sys; print(float(json.load(sys.stdin)['data']['pod']['costPerHr']))" 2>/dev/null)
  if num_ok "${API_P:-x}" "0.2 <= v <= 20"; then
    PRICE=$(python3 -c "print(round(max($PRICE_MIN, $API_P + 0.03), 3))")
    say "Preis laut RunPod: $API_P \$/h (+ Speicher) → Kostenbremse rechnet mit $PRICE \$/h"
  else
    say "Preis nicht abfragbar – Kostenbremse rechnet vorsichtig mit $PRICE \$/h"
  fi
fi
LIMIT_USD=$(python3 -c "print(round($MAX_USD - $SPENT_USD, 2))")
num_ok "$LIMIT_USD" "v >= 8" || fail "Nach Abzug von SELA2_SPENT_USD bleiben nur $LIMIT_USD \$ – zu wenig für einen Lauf"
printf 'SELA2_MAX_USD=%s\nSELA2_SPENT_USD=%s\nSELA2_PRICE=%s\n' "$MAX_USD" "$SPENT_USD" "$PRICE_MIN" > "$W/settings.env.tmp" \
  && mv -f "$W/settings.env.tmp" "$W/settings.env"
[ -f "$W/started" ] || date -u +%s > "$W/started"
mkdir -p "$W/meter"
echo "$LIMIT_USD $PRICE" > "$W/cost_limit"
H100_TEST_METER=${SELA2_TEST_METER:-0} start_meter
if [ -n "${RUNPOD_POD_ID:-}" ] && [ -w / ]; then             # after an unattended container restart: status re-arms
  printf '#!/bin/bash\ncd %q && setsid bash experiments/sela2_status.sh </dev/null >/dev/null 2>&1 &\n' "$REPO_DIR" > /post_start.sh \
    && chmod +x /post_start.sh
fi
usd_now() { awk -v s="$(billed_s)" -v p="$PRICE" 'BEGIN {printf "%.2f", s / 3600 * p}'; }
say "Kostenbremse: höchstens $LIMIT_USD \$ auf diesem Pod (bisher ≈ $(usd_now) \$); bei Erreichen stoppt sich der Pod selbst"
say "=== ENGRAMM Sela-2, Arbeitsordner $W, $NCPU CPUs ==="

# --- 0. checks ---------------------------------------------------------------------------------------------------
say "== 0. Prüfungen"
if test_mode; then
  say "TEST-MODUS: GPU-Prüfungen übersprungen"
elif done_ finished; then
  say "Lauf bereits fertig: nur noch Ergebnisse/Upload"
else
  command -v nvidia-smi >/dev/null || fail "nvidia-smi fehlt – das ist kein GPU-Rechner"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || fail "nvidia-smi meldet keine GPU"
  python3 - "$W" <<'EOF' || fail "Python/torch/GPU/Platte nicht passend (siehe oben)"
import os, shutil, sys
import torch
W = sys.argv[1]
assert sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}: mindestens 3.10 nötig"
v = tuple(int(x) for x in torch.__version__.split("+")[0].split(".")[:2])
assert v >= (2, 6), f"torch {torch.__version__}: mindestens 2.6 nötig (Vorlage 'Runpod PyTorch 2.8' wählen)"
assert torch.cuda.is_available(), "torch sieht keine GPU"
name = torch.cuda.get_device_name(0)
mem = torch.cuda.get_device_properties(0).total_memory / 2 ** 30
assert mem >= 70, f"{name} mit {mem:.0f} GB: zu wenig GPU-Speicher (H100 80 GB erwartet)"
need = 25 if os.path.exists(f"{W}/stages/data") else 60
free = shutil.disk_usage(W).free / 2 ** 30
assert free >= need, f"nur {free:.0f} GB frei unter {W}: mindestens {need} GB nötig (Volume Disk 100 GB)"
ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30
assert ram >= 40, f"nur {ram:.0f} GB Arbeitsspeicher: mindestens 40 GB nötig"
print(f"OK: Python {sys.version.split()[0]}, torch {torch.__version__}, {name} {mem:.0f} GB, {free:.0f} GB frei, {ram:.0f} GB RAM")
EOF
fi
if [ -n "${RUNPOD_POD_ID:-}" ] && ! command -v runpodctl >/dev/null && [ -z "${RUNPOD_API_KEY:-}" ]; then
  fail "Weder runpodctl noch RUNPOD_API_KEY vorhanden – der Pod könnte sich nicht selbst stoppen (Kostenbremse)"
fi
REL=$(python3 -c "import json; print(json.load(open('results/sela2/data/manifest.json'))['release_id'])" 2>/dev/null)
TOKSHA=$(sha256sum data/lm2_tokenizer.json 2>/dev/null | cut -d' ' -f1)
if test_mode && [ -n "${SELA2_TEST_DATA:-}" ]; then REL=0; TOKSHA=fake; fi
[ -n "$REL" ] || fail "results/sela2/data/manifest.json fehlt im Checkout (falscher Stand? Befehl 1 prüfen)"
[ -n "$TOKSHA" ] || fail "data/lm2_tokenizer.json fehlt im Checkout"
if [ -n "${GH_TOKEN:-}" ]; then
  export GH_TOKEN
  python3 -m experiments.gh_release list --release "$REL" > "$W/release_assets.txt" 2>"$W/gh_check.err" \
    || { echo "NEIN (kann die privaten Daten nicht lesen)" > "$W/github_check"
         fail "GitHub-Schlüssel kann die privaten Trainingsdaten nicht lesen ($(tail -c 300 "$W/gh_check.err")) – Schlüssel mit 'Contents: Read and write' für erithy25/engramm anlegen, Befehl 2, dann Befehl 3"; }
  GIT_TERMINAL_PROMPT=0 timeout 90 git -c credential.helper= -c credential.helper="$CRED" \
    push --dry-run -q "$GHREPO" HEAD:refs/heads/sela2-token-check >/dev/null 2>&1 \
    || { echo "NEIN (ohne Schreibrecht)" > "$W/github_check"
         fail "GitHub-Schlüssel ohne Schreibrecht (bei 'Contents' muss 'Read and write' stehen) – neuen Schlüssel anlegen, Befehl 2, dann Befehl 3"; }
  echo "ja (Lesen und Schreiben bestätigt, $(date -u +%H:%M) UTC)" > "$W/github_check"
  say "GitHub-Schlüssel: Lesen der privaten Daten und Schreiben bestätigt ($(wc -l < "$W/release_assets.txt") Dateien im Daten-Entwurf)"
elif [ "${SELA2_NO_GITHUB:-0}" != 1 ]; then
  echo "NEIN (kein Schlüssel gesetzt)" > "$W/github_check"
  fail "Kein GitHub-Schlüssel gesetzt (Befehl 2 vergessen?) – ohne ihn kommen weder Daten noch Ergebnisse"
fi

# --- 1. packages (every start: the container disk does not survive a pod restart) ----------------------------------
PKG_CHECK='import numpy, tokenizers; assert tokenizers.__version__ == "0.23.2", tokenizers.__version__'
if ! python3 -c "$PKG_CHECK" 2>/dev/null; then
  say "== 1. Pakete"
  PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install -q "tokenizers==0.23.2" || fail "pip install fehlgeschlagen"
  python3 -c "$PKG_CHECK" || fail "Pakete nicht importierbar"
fi
mark packages

# --- 2. data -------------------------------------------------------------------------------------------------------
if ! done_ data; then
  if test_mode && [ -n "${SELA2_TEST_DATA:-}" ] && [ "$REL" = 0 ]; then
    rm -rf "$W/data"; cp -r "$SELA2_TEST_DATA" "$W/data"
  else
    say "== 2. Trainingsdaten aus dem privaten Entwurf (≈ 15 GB)"
    ok=0
    for attempt in 1 2 3; do
      python3 -m experiments.gh_release download --release "$REL" --dest "$W/data" --jobs 8 \
        --match '\.(u16|json|mask|npy)$|\.part\d{3}$|\.parts\.json$' > "$W/download.log" 2>&1 && { ok=1; break; }
      say "Download: Versuch $attempt fehlgeschlagen ($(tail -c 300 "$W/download.log")), neuer Versuch in 60 s"; sleep 60
    done
    [ $ok = 1 ] || fail "Trainingsdaten konnten nicht geladen werden"
  fi
  python3 - "$W/data" "$TOKSHA" <<'EOF' || fail "Trainingsdaten unvollständig oder beschädigt (siehe oben)"
import hashlib, json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
d, toksha = Path(sys.argv[1]), sys.argv[2]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(1 << 22):
            h.update(b)
    return h.hexdigest()

recs = []
for j in sorted(d.glob("*.json")):
    r = json.loads(j.read_text())
    if isinstance(r, dict) and r.get("name") and r.get("sha256"):
        recs.append(r)
assert recs, "keine Datenströme gefunden"
bad = [r["name"] for r in recs if r.get("tokenizer_sha256") not in (toksha, "fake")]
assert not bad, f"mit einem anderen Tokenizer gebaut: {bad[:5]}"
with ProcessPoolExecutor(8) as ex:
    got = list(ex.map(sha, [d / f"{r['name']}.u16" for r in recs]))
wrong = [r["name"] for r, g in zip(recs, got) if g != r["sha256"]]
assert not wrong, f"SHA-256 stimmt nicht: {wrong[:5]}"
print(f"OK: {len(recs)} Datenströme, {sum(r['tokens'] for r in recs) / 1e9:.2f} Mrd. Token, alle SHA-256 geprüft")
EOF
  mark data
fi
OUT=${SELA2_OUT:-$REPO_DIR/results/sela2}
TRAIN=(--data "$W/data" --tokenizer-sha "$TOKSHA" --out "$OUT")
PRE_EXTRA=(); SFT_EXTRA=()
if test_mode; then
  TRAIN=(--data "$W/data" --tokenizer-sha "" --out "$OUT" --size "${SELA2_TEST_SIZE:-tiny}" --vocab "${SELA2_TEST_VOCAB:-512}"
         --cpu --compile 0 --flex 0 --bf16 0 --micro-batch 4)
  PRE_EXTRA=(--total-tokens "${SELA2_TEST_TOKENS:-150000}" --batch-tokens 512 --eval-every 60000 --eval-docs 5 --ckpt-minutes 0.2)
  SFT_EXTRA=(--sft-batch-tokens 516 --sft-max-steps "${SELA2_TEST_SFT_STEPS:-60}")
fi

# --- 3. probe: the whole path with a tiny model on the GPU, before the expensive hours -------------------------------
if ! done_ probe; then
  say "== 3. Vorab-Probe (winziges Modell durch den ganzen Ablauf, ≈ 3 min)"
  P="$W/probe"; rm -rf "$P"; mkdir -p "$P"
  PROBE=(--data "$W/data" --tokenizer-sha "$TOKSHA" --ckpt-dir "$P/ckpt" --out "$P/out")
  test_mode && PROBE=(--data "$W/data" --tokenizer-sha "" --ckpt-dir "$P/ckpt" --out "$P/out")
  PB=65536; test_mode && PB=512
  if test_mode; then PROBE+=(--size "${SELA2_TEST_SIZE:-tiny}" --vocab "${SELA2_TEST_VOCAB:-512}" --cpu --compile 0 --flex 0 --bf16 0 --micro-batch 4)
  else PROBE+=(--size probe --micro-batch 16); fi
  python3 -m experiments.sela2_train pretrain "${PROBE[@]}" --total-tokens $(( PB * 45 )) --batch-tokens "$PB" --eval-every $(( PB * 30 )) \
      --eval-docs 5 --ckpt-minutes 0.5 > "$P/pretrain.log" 2>&1 || { tail -30 "$P/pretrain.log"; fail "Vorab-Probe: Vortraining fehlgeschlagen"; }
  PSFT=(); test_mode && PSFT=(--sft-max-steps 10)
  python3 -m experiments.sela2_train sft "${PROBE[@]}" "${PSFT[@]}" --sft-batch-tokens $(( PB + PB / 256 )) \
      --deadline $(( $(date +%s) + 120 )) > "$P/sft.log" 2>&1 || { tail -30 "$P/sft.log"; fail "Vorab-Probe: Feinabstimmung fehlgeschlagen"; }
  EVP=(--data "$W/data" --model "$P/ckpt/model_chat.pt" --out "$P/out" --tag probe --final-docs 5)
  test_mode && EVP+=(--cpu --samples 0)
  python3 -m experiments.sela2_train evaluate "${EVP[@]}" > "$P/eval.log" 2>&1 || { tail -30 "$P/eval.log"; fail "Vorab-Probe: Auswertung fehlgeschlagen"; }
  if [ -n "${GH_TOKEN:-}" ] && ! test_mode; then        # an upload into the results release really works
    RID=$(cat "$W/stages/release_id" 2>/dev/null)
    if [ -z "$RID" ]; then
      RID=$(python3 -m experiments.gh_release find-or-create --name "ENGRAMM Sela-2 Modell $(date -u +%Y%m%d) (privat)" \
            --body "Sela-2: Chat-Modell, Basismodell und Fortsetzungs-Stand. Privater Entwurf – nicht veröffentlichen.") \
        || fail "Ergebnis-Release konnte nicht angelegt werden"
      echo "$RID" > "$W/stages/release_id"
    fi
    head -c 2000000 /dev/urandom > "$P/upload_probe.bin"
    python3 -m experiments.gh_release upload --release "$RID" "$P/upload_probe.bin" > "$P/upload.log" 2>&1 \
      || { cat "$P/upload.log"; fail "Vorab-Probe: Hochladen nach GitHub fehlgeschlagen"; }
    python3 - "$RID" <<'EOF' || true
import sys
from experiments.gh_release import API, REPO, _req, assets
for a in assets(int(sys.argv[1])):
    if a["name"] == "upload_probe.bin":
        _req("DELETE", f"{API}/repos/{REPO}/releases/assets/{a['id']}")
EOF
  fi
  python3 -c "
import json; r = json.load(open('$P/out/eval_probe.json'))
print('Probe OK:', {k: round(v['bpb'], 2) for k, v in list(r['bpb'].items())[:4]})"
  rm -rf "$P/ckpt"
  mark probe
fi

gpu_ok() {
  test_mode && return 0
  timeout 180 python3 -c "import torch; x = torch.ones(1, device='cuda'); torch.cuda.synchronize(); assert float(x.sum()) == 1.0" >/dev/null 2>&1
}

# background uploads: a file into the results release, recorded in $W/up/<name>.ok once verified
bg_upload() {  # file name
  [ -n "${GH_TOKEN:-}" ] || return 0
  local f=$1 n=$2 rid; rid=$(cat "$W/stages/release_id" 2>/dev/null); [ -n "$rid" ] || return 0
  [ -f "$W/up/$n.ok" ] && return 0
  ( exec 9>&-
    python3 -m experiments.gh_release upload --release "$rid" "$f" >> "$W/up/$n.log" 2>&1 \
      && date -u > "$W/up/$n.ok" ) </dev/null >/dev/null 2>&1 &
  echo $! > "$W/up/$n.pid"
}
predecay_watch() {  # upload the continuation state as soon as it exists (Sela-1 lost its own)
  ( exec 9>&-
    while ! [ -f "$W/ckpt/state_pre_predecay.pt" ]; do sleep 60; flock -n /tmp/engramm_sela2.lock true && exit 0; done
    sleep 30
    rid=$(cat "$W/stages/release_id" 2>/dev/null); [ -n "$rid" ] && [ -n "${GH_TOKEN:-}" ] || exit 0
    [ -f "$W/up/fortsetzen.ok" ] && exit 0
    cp "$W/ckpt/state_pre_predecay.pt" "$W/up/fortsetzen_vor_abklingen.pt"
    python3 -m experiments.gh_release upload --release "$rid" "$W/up/fortsetzen_vor_abklingen.pt" >> "$W/up/fortsetzen.log" 2>&1 \
      && date -u > "$W/up/fortsetzen.ok" && rm -f "$W/up/fortsetzen_vor_abklingen.pt" ) </dev/null >/dev/null 2>&1 &
}

# --- 4. pretraining --------------------------------------------------------------------------------------------------
if ! done_ pretrain; then
  mark pretrain_started
  DEADLINE=$(( $(date +%s) + $(limit_s) - $(billed_s) - RESERVE_PRE_S ))
  say "== 4. Vortraining (Ende spätestens $(date -u -d "@$DEADLINE" +%H:%M) UTC wegen der Kostenbremse)"
  [ -f "$W/up/fortsetzen.ok" ] || predecay_watch
  LRS=$(cat "$W/stages/lr_scale" 2>/dev/null || echo 1.0)
  pre() { python3 -m experiments.sela2_train pretrain "${TRAIN[@]}" "${PRE_EXTRA[@]}" --deadline "$DEADLINE" --lr-scale "$LRS" "$@"; }
  restarts=$(cat "$W/stages/pretrain_restarts" 2>/dev/null || echo 0)
  while true; do
    t0=$(date +%s)
    pre; rc=$?
    [ $rc = 0 ] && break
    if [ $rc = 3 ]; then                                   # divergence: continue from the last state at half the rate
      LRS=$(python3 -c "print($LRS / 2)"); echo "$LRS" > "$W/stages/lr_scale"
      say "Training divergiert – weiter ab dem letzten Speicherstand mit Lernraten-Faktor $LRS"
      [ "$(python3 -c "print(int($LRS < 0.2))")" = 1 ] && fail "Training divergiert wiederholt"
      continue
    fi
    if [ $rc = 4 ]; then                                   # loss did not fall: start over once at half the rate
      [ -f "$W/stages/recipe_restart" ] && fail "Verlust sinkt auch mit halber Lernrate nicht – Lauf angehalten"
      date -u > "$W/stages/recipe_restart"
      LRS=0.5; echo "$LRS" > "$W/stages/lr_scale"
      mv -f "$W/ckpt/state_pre.pt" "$W/ckpt/state_pre_failed.pt" 2>/dev/null
      say "Verlust sank nicht wie erwartet – Neubeginn mit halber Lernrate"
      continue
    fi
    if [ "$restarts" -ge 2 ] || [ $(( DEADLINE - $(date +%s) )) -lt 900 ] || [ $(( $(date +%s) - t0 )) -lt 300 ] || ! gpu_ok; then
      fail "Vortraining mit Code $rc beendet (Neustart setzt am letzten Stand fort)"
    fi
    restarts=$(( restarts + 1 )); echo "$restarts" > "$W/stages/pretrain_restarts"
    say "Vortraining unerwartet beendet (Code $rc) – automatischer Neustart $restarts/2 ab dem letzten Speicherstand"
    sleep 20
  done
  mark pretrain
fi
cp "$OUT/pretrain_meta.json" "$W/up/" 2>/dev/null

# --- 5. base model to GitHub in the background (bf16, ≈ 1 GB) --------------------------------------------------------
if [ ! -f "$W/up/basis.ok" ] && [ -f "$W/ckpt/model_base.pt" ]; then
  python3 -c "
import torch
st = torch.load('$W/ckpt/model_base.pt', map_location='cpu', weights_only=False)
st['model'] = {k: v.to(torch.bfloat16) for k, v in st['model'].items()}
torch.save(st, '$W/up/sela2_basis_bf16.pt')" && bg_upload "$W/up/sela2_basis_bf16.pt" basis
fi

# --- 6. chat fine-tuning ---------------------------------------------------------------------------------------------
if ! done_ sft; then
  DL=$(( $(date +%s) + $(limit_s) - $(billed_s) - RESERVE_SFT_S ))
  say "== 6. Chat-Feinabstimmung (Ende spätestens $(date -u -d "@$DL" +%H:%M) UTC)"
  ok=0
  for attempt in 1 2; do
    python3 -m experiments.sela2_train sft "${TRAIN[@]}" "${SFT_EXTRA[@]}" --deadline "$DL" && { ok=1; break; }
    gpu_ok || break
    say "Feinabstimmung fehlgeschlagen – ein neuer Versuch"
  done
  [ $ok = 1 ] || fail "Chat-Feinabstimmung fehlgeschlagen (das Basismodell ist gesichert)"
  mark sft
fi

# --- 7. evaluation on the GPU ----------------------------------------------------------------------------------------
if ! done_ eval; then
  say "== 7. Auswertung"
  EV=(--data "$W/data" --out "$OUT")
  FD=600; FB=300
  test_mode && { EV+=(--cpu --samples 0); FD=${SELA2_TEST_EVAL_DOCS:-50}; FB=$FD; }
  python3 -m experiments.sela2_train evaluate "${EV[@]}" --model "$W/ckpt/model_chat.pt" --tag chat --final-docs "$FD" \
    || say "Auswertung des Chat-Modells unvollständig (Modell ist trotzdem gesichert)"
  python3 -m experiments.sela2_train evaluate "${EV[@]}" --model "$W/ckpt/model_base.pt" --tag base --final-docs "$FB" \
    || say "Auswertung des Basismodells unvollständig"
  mark eval
fi

# --- 8. results ------------------------------------------------------------------------------------------------------
say "== 8. Ergebnisse"
cp "$W/run.log" "$OUT/run.log" 2>/dev/null
python3 - "$OUT" <<'EOF' | tee "$W/SUMMARY.txt"
import json, sys
from pathlib import Path
R = Path(sys.argv[1])
for tag in ("chat", "base"):
    f = R / f"eval_{tag}.json"
    if not f.exists():
        continue
    r = json.loads(f.read_text())
    print(f"{'Chat-Modell' if tag == 'chat' else 'Basismodell'}:")
    for k, v in sorted(r["bpb"].items()):
        print(f"  {k:16s} {v['bpb']:.4f} bpb")
    for k, v in r.get("chat_val", {}).items():
        print(f"  {k:16s} Antwort-Verlust {v['loss']:.3f}")
m = R / "pretrain_meta.json"
if m.exists():
    mm = json.loads(m.read_text())
    print(f"Vortraining: {mm['tokens'] / 1e9:.2f} Mrd. Token in {mm['train_seconds'] / 3600:.2f} h")
s = R / "sft_meta.json"
if s.exists():
    ss = json.loads(s.read_text())
    print(f"Feinabstimmung: {ss['sft_steps']} Schritte, {ss['sft_assistant_tokens'] / 1e6:.1f} Mio. Antwort-Token")
EOF
if [ -f "$W/ckpt/model_chat.pt" ] && [ ! -f "$W/up/sela2_chat_bf16.pt" ]; then
  python3 -c "
import torch
st = torch.load('$W/ckpt/model_chat.pt', map_location='cpu', weights_only=False)
st['model'] = {k: v.to(torch.bfloat16) for k, v in st['model'].items()}
torch.save(st, '$W/up/sela2_chat_bf16.pt')"
fi
uploaded=0
if [ -f "$W/stages/uploaded" ]; then
  uploaded=1
elif [ -n "${GH_TOKEN:-}" ] && ! test_mode; then
  RID=$(cat "$W/stages/release_id" 2>/dev/null)
  ok_all=1
  [ -f "$W/up/chat.ok" ] || { python3 -m experiments.gh_release upload --release "$RID" "$W/up/sela2_chat_bf16.pt" \
                                 >> "$W/up/chat.log" 2>&1 && date -u > "$W/up/chat.ok"; } || ok_all=0
  for n in basis fortsetzen; do                              # the background uploads: wait (bounded by the meter)
    while [ ! -f "$W/up/$n.ok" ] && [ "$(time_left)" -gt 240 ]; do
      p=$(cat "$W/up/$n.pid" 2>/dev/null)
      if [ "$n" = basis ] && ! { [[ "$p" =~ ^[0-9]+$ ]] && kill -0 "$p" 2>/dev/null; }; then
        bg_upload "$W/up/sela2_basis_bf16.pt" basis      # not running (e.g. after a restart): start it again
      fi
      if [ "$n" = fortsetzen ] && ! pgrep -f "fortsetzen_vor_abklingen" >/dev/null; then
        [ -f "$W/ckpt/state_pre_predecay.pt" ] || break
        cp -n "$W/ckpt/state_pre_predecay.pt" "$W/up/fortsetzen_vor_abklingen.pt"
        python3 -m experiments.gh_release upload --release "$RID" "$W/up/fortsetzen_vor_abklingen.pt" >> "$W/up/fortsetzen.log" 2>&1 \
          && date -u > "$W/up/fortsetzen.ok"
      fi
      sleep 20
    done
    [ -f "$W/up/$n.ok" ] || ok_all=0
  done
  BR=$(cat "$W/stages/branch" 2>/dev/null || echo "sela2-results-$(date -u +%Y%m%d-%H%M)")
  echo "$BR" > "$W/stages/branch"
  git config user.email "sela2-run@users.noreply.github.com"
  git config user.name "ENGRAMM Sela-2-Lauf"
  [ "$(git rev-parse --abbrev-ref HEAD)" = "$BR" ] || git checkout -q -B "$BR"
  git add -f results/sela2
  git diff --cached --quiet || git commit -q -m "v5: Sela-2 Ergebnisse, automatisch vom GPU-Rechner"
  pushed=0
  for attempt in 1 2 3; do
    left=$(time_left); [ "$left" -gt 120 ] || break
    GIT_TERMINAL_PROMPT=0 timeout 600 git -c credential.helper= -c credential.helper="$CRED" push -q "$GHREPO" "$BR" \
      && { pushed=1; break; }
    sleep 30
  done
  [ $pushed = 1 ] && say "Ergebnisse auf GitHub: Branch $BR" || { say "Push der Messwerte fehlgeschlagen"; ok_all=0; }
  if [ $ok_all = 1 ]; then uploaded=1; echo "$BR" > "$W/stages/uploaded"; fi
fi
mark finished

if [ "$uploaded" = 1 ] && [ -n "${RUNPOD_POD_ID:-}" ] && [ "$AUTO_END" != none ]; then
  say "FERTIG. Chat-Modell, Basismodell, Fortsetzungs-Stand und Messwerte sind auf GitHub gesichert. Der Pod beendet sich in 2 Minuten selbst."
  sleep 120
  ended=0
  if [ "$AUTO_END" = terminate ]; then
    runpodctl remove pod "$RUNPOD_POD_ID" 2>/dev/null || runpodctl pod delete "$RUNPOD_POD_ID" 2>/dev/null && ended=1
    if [ $ended = 0 ] && [ -n "${RUNPOD_API_KEY:-}" ]; then
      curl -s --max-time 60 -H "Content-Type: application/json" \
        -d "{\"query\": \"mutation { podTerminate(input: {podId: \\\"$RUNPOD_POD_ID\\\"}) }\"}" \
        "https://api.runpod.io/graphql?api_key=$RUNPOD_API_KEY" >/dev/null 2>&1 && ended=1
    fi
  fi
  [ $ended = 1 ] || stop_pod
  sleep 60
  say "Selbstbeendigung hat nicht geklappt – bitte den Pod in der RunPod-Konsole beenden (Stop, dann Terminate). Alles ist gesichert."
elif [ "$uploaded" = 1 ]; then
  say "FERTIG. Alles ist auf GitHub gesichert. Den Pod jetzt beenden (Stop, dann Terminate)."
else
  say "FERTIG – aber NICHT alles auf GitHub gesichert. Status zeigt, was fehlt; diese Ausgabe an Claude schicken."
  say "Kostenschutz: der Pod stoppt sich in 30 Minuten selbst (Daten in /workspace bleiben). Aussetzen: touch $W/KEEP"
  date +%s > "$W/NOT_UPLOADED"
  autostop_later 1800 "$W/NOT_UPLOADED"
fi
