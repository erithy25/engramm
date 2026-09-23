#!/usr/bin/env bash
# Run the registered bit-corruption grid (docs/PREREG_ROBUSTNESS.md v1.3):
# 2 tasks × 10 seeds, then the referee.
#
#   bash experiments/robustness_all.sh
#   COMMIT=0 bash experiments/robustness_all.sh      # no git commit/push
#
# Each (task, seed) writes to logs/runs/robustness first and is copied to
# results/robustness only after it finished; with COMMIT=1 every record is
# committed and pushed at once. A marker logs/runs/robustness/<task>_<seed>.done
# skips a finished run on restart.
#
# Timing hygiene: while the main queue (experiments/reproduce_all.sh) is in a
# step whose wall-clock figures feed a criterion — m0 (latency budget), m5e
# and b3 (M5 learning-time ratio) — the running study process is paused
# with SIGSTOP and resumed afterwards, so it never competes with those
# measurements. Pauses are logged. The study's own figures are accuracies;
# its container wall time is not a criterion (§9.1).
set -u
cd "$(dirname "$0")/.."
PY=./.venv/bin/python
COMMIT=${COMMIT:-1}
SEEDS="42 7 1337 2026 99 3 123 512 8191 31337"
RUNS=logs/runs/robustness
OUT=results/robustness
mkdir -p "$RUNS" "$OUT"

log() { echo "[$(date -u +%FT%TZ)] $*"; }

critical_step_running() {
  [ -f logs/queue.log ] || return 1
  local last
  last=$(grep -E '\] (start|done |FAIL |skip) ' logs/queue.log | tail -1)
  case "$last" in
    *"start m0:"*|*"start m5e:"*|*"start b3:"*) return 0 ;;
  esac
  return 1
}

guard() {  # pause the study while a timing-critical queue step runs
  local paused=0 pids
  while kill -0 "$1" 2>/dev/null; do
    pids=$(pgrep -f "experiments.robustness --task" || true)
    if critical_step_running; then
      if [ -n "$pids" ]; then
        kill -STOP $pids 2>/dev/null
        [ $paused = 0 ] && log "guard: paused $pids (timing-critical queue step)"
        paused=1
      fi
    elif [ $paused = 1 ]; then
      [ -n "$pids" ] && kill -CONT $pids 2>/dev/null
      log "guard: resumed $pids"
      paused=0
    fi
    sleep 15
  done
}

publish() {  # publish <file>...
  cp "$@" "$OUT"/
  if [ "$COMMIT" = "1" ]; then
    git add "$OUT" && git commit -q -m "results/robustness: $(basename "$1" .json) übernommen

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_019SwnwJiHX6CTqX9UE2VxWF" \
      && for i in 1 2 3 4; do git push -q origin HEAD && break; sleep $((2 ** i)); done
  fi
}

guard $$ >> logs/robustness_guard.log 2>&1 &

for task in mnist wili; do
  for seed in $SEEDS; do
    marker="$RUNS/${task}_${seed}.done"
    if [ -f "$marker" ]; then log "skip $task $seed (done)"; continue; fi
    log "start $task $seed"
    if "$PY" -u -m experiments.robustness --task "$task" --seed "$seed" \
         --results-dir "$RUNS" > "logs/robustness_${task}_${seed}.log" 2>&1; then
      files=("$RUNS/${task}_seed${seed}.json")
      [ -f "$RUNS/wili_vocabulary_diagnostic.json" ] && \
        [ ! -f "$OUT/wili_vocabulary_diagnostic.json" ] && \
        files+=("$RUNS/wili_vocabulary_diagnostic.json")
      publish "${files[@]}"
      touch "$marker"
      log "done  $task $seed"
    else
      log "FAIL  $task $seed (exit $?) — see logs/robustness_${task}_${seed}.log"
    fi
  done
done

if "$PY" -m experiments.robustness_verdict --results-dir "$OUT" > logs/robustness_verdict.log 2>&1; then
  if [ "$COMMIT" = "1" ]; then
    git add "$OUT" && git commit -q -m "results/robustness: Verdikt nach PREREG_ROBUSTNESS v1.3

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_019SwnwJiHX6CTqX9UE2VxWF" \
      && for i in 1 2 3 4; do git push -q origin HEAD && break; sleep $((2 ** i)); done
  fi
  log "verdict written"
else
  log "verdict FAILED — see logs/robustness_verdict.log"
fi
log "robustness queue finished"
