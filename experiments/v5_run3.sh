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
export NUMBA_THREADING_LAYER=workqueue
PY="env PYTHONPATH=$PT:$(pwd) .venv/bin/python -u"
M=models/lm/v5                                   # checkpoints that must survive a restart
mkdir -p "$M"
[ ! -f "$D/ckpt_plain/ckpt_3h.pt" ] || cp -n "$D/ckpt_plain/ckpt_3h.pt" "$M/plain_run2_3h.pt"
[ -f "$D/prior_weights.json" ] || $PY experiments/v5_residual.py weights
# compact, shared training inputs; the big component files are then no longer needed (RAM disk
# counts against the container's memory limit)
[ -f "$D/region_pp.npy" ] && [ -f "$D/region_feats.npy" ] || $PY experiments/v5_residual.py prep
rm -f "$D/region_kn.npz" "$D/region_inf.npz" "$D/region_cache.npz"
$PY -m experiments.v5_counter check > "$D/counter_check.log" 2>&1 || { echo "counter check failed" > "$D/run3.failed"; exit 1; }
$PY experiments/v5_residual.py train --arm plain --hours "$HOURS" --threads 2 --results run3 --ckpt-dir plain_run3 \
  > "$D/train_plain_run3.log" 2>&1 &
p1=$!
$PY -m experiments.v5_logres train --hours "$HOURS" --threads 2 --results run3 > "$D/train_logres.log" 2>&1 &
p2=$!
rc=0
wait "$p1" || rc=1
wait "$p2" || rc=1
if [ "$rc" -ne 0 ]; then echo "an arm failed" > "$D/run3.failed"; exit 1; fi
cp "$D/ckpt_logres/ckpt_${HOURS}h.pt" "$M/logres_${HOURS}h.pt"
cp "$D/ckpt_plain_run3/ckpt_${HOURS}h.pt" "$M/plain_run3_${HOURS}h.pt"
# the same post-hoc pipeline for every model (4 threads, machine otherwise idle)
for t in logres plain_run3 plain_run2; do
  [ -f "$M/${t}_${HOURS}h.pt" ] || continue
  $PY -m experiments.v5_posthoc --ckpt "$M/${t}_${HOURS}h.pt" --tag "${t}_${HOURS}h" --results run3 \
    > "$D/posthoc_$t.log" 2>&1 || { echo "posthoc $t failed" > "$D/run3.failed"; exit 1; }
done
.venv/bin/python -m experiments.v5_report --run run3 --pipe "$HOURS" > "$D/report_run3.txt" 2>&1 || true
echo "run 3 finished" > "$D/run3.done"
