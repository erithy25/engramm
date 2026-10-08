#!/bin/sh
# v5 run 3: plain vs logit-residual (logres), both in one Python with torch + numba.
# Start detached:
#   setsid nohup sh experiments/v5_run3.sh 3 > /dev/shm/engramm/v5/run3.log 2>&1 < /dev/null &
# Measurements: results/v5/run3/ (written by the training processes at every checkpoint).
set -eu
cd "$(dirname "$0")/.."
HOURS="${1:-3}"
D=/dev/shm/engramm/v5
PT=/dev/shm/engramm/pt311
mkdir -p "$D"
rm -f "$D/run3.done" "$D/run3.failed"
if [ ! -d "$PT/torch" ]; then
  PIP_CACHE_DIR=/dev/shm/engramm/pipcache TMPDIR=/dev/shm/engramm \
    .venv/bin/python -m pip install -q --target "$PT" --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple torch==2.14.0
  rm -rf /dev/shm/engramm/pipcache
fi
[ -f "$D/prior.done" ] || .venv/bin/python -m experiments.v5_prior --tokens 40000000 --out "$D"
PY="env PYTHONPATH=$PT:$(pwd) .venv/bin/python -u"
[ -f "$D/prior_weights.json" ] || $PY experiments/v5_residual.py weights
$PY -m experiments.v5_counter check > "$D/counter_check.log" 2>&1
$PY experiments/v5_residual.py train --arm plain --hours "$HOURS" --threads 2 --results run3 --ckpt-dir plain_run3 \
  > "$D/train_plain_run3.log" 2>&1 &
p1=$!
$PY -m experiments.v5_logres train --hours "$HOURS" --threads 2 --results run3 > "$D/train_logres.log" 2>&1 &
p2=$!
rc=0
wait "$p1" || rc=1
wait "$p2" || rc=1
if [ "$rc" -eq 0 ]; then echo "run 3 finished" > "$D/run3.done"; else echo "an arm failed" > "$D/run3.failed"; exit 1; fi
