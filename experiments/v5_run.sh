#!/bin/sh
# v5 residual training, run 2: everything from scratch, idempotent where possible.
# Start it detached, so no shell timeout can take the arms down:
#   setsid nohup sh experiments/v5_run.sh 3 > /dev/shm/engramm/v5/run.log 2>&1 < /dev/null &
# Big files live in /dev/shm/engramm/v5 (lost on a container restart); every finished
# measurement is written to results/v5/ in the repository by the training processes.
set -eu
cd "$(dirname "$0")/.."
HOURS="${1:-3}"
D=/dev/shm/engramm/v5
mkdir -p "$D"
rm -f "$D/run.done" "$D/run.failed"
[ -f "$D/prior.done" ] || .venv/bin/python -m experiments.v5_prior --tokens 40000000 --out "$D"
[ -f "$D/prior_weights.json" ] || .venv_b1/bin/python -u experiments/v5_residual.py weights
pids=""
for a in plain residual2; do
  .venv_b1/bin/python -u experiments/v5_residual.py train --arm "$a" --hours "$HOURS" --threads 2 \
    > "$D/train_$a.log" 2>&1 &
  pids="$pids $!"
done
rc=0
for p in $pids; do wait "$p" || rc=1; done
if [ "$rc" -eq 0 ]; then echo "v5 run finished" > "$D/run.done"; else echo "an arm failed" > "$D/run.failed"; exit 1; fi
