#!/usr/bin/env bash
# Reproduce every registered milestone run, one after another.
#
#   bash experiments/reproduce_all.sh                 # all steps
#   bash experiments/reproduce_all.sh m2a m2b m3      # selected steps
#   COMMIT=0 bash experiments/reproduce_all.sh        # no git commit/push
#
# Each step writes its records to a scratch directory under logs/runs/<step>
# first (logs/ is gitignored) and copies them into results/ only after the
# step succeeded — a crashed step never leaves half a record set behind. With
# COMMIT=1 (default) every finished step is committed and pushed at once, so
# a container restart costs at most the step in flight. A step whose marker
# logs/runs/<step>/.done exists is skipped; delete it to re-run.
#
# Registrations for every step are in docs/EXPECTATIONS.md (E3–E10) and were
# committed before the step first ran.
set -u
cd "$(dirname "$0")/.."
PY=./.venv/bin/python
PY_B1=./.venv_b1/bin/python
COMMIT=${COMMIT:-1}
SEEDS5="42,7,1337,2026,99"
mkdir -p logs/runs

log() { echo "[$(date -u +%FT%TZ)] $*"; }

publish() {  # publish <step> <scratch dir> <results dir>
  local step=$1 src=$2 dst=$3
  mkdir -p "$dst"
  cp "$src"/*.json* "$dst"/ 2>/dev/null
  touch "logs/runs/$step/.done"
  if [ "$COMMIT" = "1" ]; then
    git add "$dst" && git commit -q -m "results/$step: Records des registrierten Laufs übernommen

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_019SwnwJiHX6CTqX9UE2VxWF" \
      && for i in 1 2 3 4; do git push -q origin HEAD && break; sleep $((2 ** i)); done
  fi
}

run_step() {  # run_step <step> <scratch dir> <results dir> <command...>
  local step=$1 src=$2 dst=$3; shift 3
  local dir="logs/runs/$step"
  if [ -f "$dir/.done" ]; then log "skip $step (done)"; return 0; fi
  mkdir -p "$dir" "$src"
  log "start $step: $*"
  if "$@" > "logs/$step.log" 2>&1; then
    publish "$step" "$src" "$dst"
    log "done  $step"
  else
    log "FAIL  $step (exit $?) — see logs/$step.log"
  fi
}

step_e3()  { run_step e3 logs/runs/e3 results "$PY" -u -m experiments.run_benchmark --task mnist \
               --seed-list "$SEEDS5" --pipeline prototypes --t2-epochs 2 \
               --results-dir logs/runs/e3; }
step_e4()  { run_step e4 logs/runs/e4 results "$PY" -u -m experiments.run_benchmark --task mnist \
               --seed-list "$SEEDS5" --pipeline full \
               --config-from results/tuning/mnist_seed42.json --results-dir logs/runs/e4; }
step_m0()  { run_step m0 logs/runs/m0 results/m0 "$PY" -u -m experiments.m0_bench --seed 42 \
               --results-dir logs/runs/m0; }
# M2a, M2b and M3 take an optional seed (default 42): "m3@7" in the step list.
step_m2a() { local seed=${1:-42}; run_step "m2a@$seed" "logs/runs/m2a@$seed" results/m2 \
               "$PY" -u -m experiments.m2_stream --seed "$seed" --results-dir "logs/runs/m2a@$seed"; }
step_m2b() { local seed=${1:-42}; run_step "m2b@$seed" "logs/runs/m2b@$seed" results/m2 \
               "$PY" -u -m experiments.m2b --seed "$seed" --work-dir logs/m2b \
               --results-dir "logs/runs/m2b@$seed"; }
step_m3()  { local seed=${1:-42}; run_step "m3@$seed" "logs/runs/m3@$seed" results/m3 \
               "$PY" -u -m experiments.m3 --seed "$seed" --work-dir logs/m3 \
               --results-dir "logs/runs/m3@$seed"; }
m5_engramm_all() {
  for task in banking77 clinc150; do
    for seed in ${SEEDS5//,/ }; do
      "$PY" -u -m experiments.m5_engramm --task "$task" --seed "$seed" \
        --results-dir logs/runs/m5 || return 1
    done
  done
}
m5_b0_all() {
  for task in banking77 clinc150; do
    for seed in ${SEEDS5//,/ }; do
      "$PY_B1" -u -m experiments.m5_baselines b0 --task "$task" --seed "$seed" \
        --results-dir logs/runs/m5 || return 1
    done
  done
}
m5_b3_all() {
  for task in banking77 clinc150; do
    "$PY_B1" -u -m experiments.m5_baselines b3 --task "$task" --seed 42 \
      --results-dir logs/runs/m5 || return 1
  done
}
m5_b1_all() {
  for task in banking77 clinc150; do
    "$PY_B1" -u -m experiments.m5_baselines b1 --task "$task" --seed 42 \
      --results-dir logs/runs/m5 || return 1
  done
  "$PY" -u -m experiments.m5_compare --seed 42 --results-dir logs/runs/m5
}
step_m5e() { mkdir -p logs/runs/m5; run_step m5e logs/runs/m5 results/m5 m5_engramm_all; }
step_b0()  { mkdir -p logs/runs/m5; run_step b0 logs/runs/m5 results/m5 m5_b0_all; }
step_b3()  { mkdir -p logs/runs/m5; run_step b3 logs/runs/m5 results/m5 m5_b3_all; }
step_b1()  { mkdir -p logs/runs/m5; run_step b1 logs/runs/m5 results/m5 m5_b1_all; }
step_e10() { run_step e10 logs/runs/e10 results "$PY" -u -m experiments.run_benchmark --task wili \
               --shots 10 --seed-list "$SEEDS5" --pipeline full --lambda-e 1 \
               --theta0 0 --t2-epochs 0 --results-dir logs/runs/e10; }

repro_all() {
  # Re-run registered records from the committed tree; compare bit for bit.
  "$PY" -u -m experiments.run_benchmark --task mnist --seed-list 42 --pipeline full \
    --config-from results/tuning/mnist_seed42.json --results-dir logs/runs/repro || return 1
  "$PY" -u -m experiments.run_benchmark --task wili --shots 10 --seed-list 42,7 \
    --results-dir logs/runs/repro || return 1
  "$PY" -u -m experiments.verify_reproduction logs/runs/repro
}
step_repro() { run_step repro logs/runs/repro results/repro repro_all; }

# Order: cheap and registered-first, the multi-hour LLM baseline last.
ALL="e3 m0 m2a m2b m3 m5e b0 b3 e10 repro m2a@7 m2b@7 m3@7 m2a@1337 m2b@1337 m3@1337 b1"
STEPS=${*:-$ALL}
for s in $STEPS; do
  name=${s%@*}; seed=""
  [ "$name" != "$s" ] && seed=${s#*@}
  "step_$name" $seed
done
log "queue finished"
