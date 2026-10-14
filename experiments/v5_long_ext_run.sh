#!/bin/sh
# Extension of the v5 long run (docs/PLAN_V5_FROM_SCRATCH.md §10, Nachtrag 14. Oktober, fixed before the
# result at 0.6 B tokens). Runs only when the final evaluation of the main run missed stage 1. Idempotent:
# after a container restart, start it again (experiments/v5_long_resume.sh does); it resumes from its own
# checkpoint, else starts from the branch state named in results/v5/long_ext1/config.json.
#   setsid nohup sh experiments/v5_long_ext_run.sh >> /dev/shm/engramm/long_ext_run.log 2>&1 < /dev/null &
set -u
cd "$(dirname "$0")/.."
RUN=long_ext1
PT=/dev/shm/engramm/pt311
L=/dev/shm/engramm/$RUN
OUT=results/v5/$RUN
mkdir -p "$L"
[ -f "$OUT/config.json" ] || { echo "no $OUT/config.json" > "$L/run.failed"; exit 1; }
[ -f results/v5/long/eval_final.json ] || { echo "main run not evaluated yet: nothing to do"; exit 1; }
.venv/bin/python -c "import json, sys; sys.exit(0 if json.load(open('results/v5/long/eval_final.json'))['stage1']['reached'] is False else 1)" \
  || { echo "stage 1 reached or not decided at 0.6 B tokens: no extension" > "$L/not_needed"; exit 0; }
if [ ! -d "$PT/torch" ]; then
  PIP_CACHE_DIR=/dev/shm/engramm/pipcache TMPDIR=/dev/shm/engramm \
    .venv/bin/python -m pip install -q --target "$PT" --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple torch==2.14.0 || { echo "torch install failed" > "$L/run.failed"; exit 1; }
  rm -rf /dev/shm/engramm/pipcache
fi
export OMP_PROC_BIND=close OMP_PLACES=cores
PY="env PYTHONPATH=$PT:$(pwd) .venv/bin/python -u"
# same allocator settings as the main run (experiments/v5_long_run.sh)
JE="env LD_PRELOAD=/lib/x86_64-linux-gnu/libjemalloc.so.2 MALLOC_CONF=background_thread:true,metadata_thp:auto,dirty_decay_ms:-1,muzzy_decay_ms:-1"
C() { .venv/bin/python -c "import json;print(json.load(open('$OUT/config.json'))['$1'])"; }
# the branch state lives on the RAM disk; after a container restart before the first checkpoint of the
# extension it is gone, and the extension starts from the final weights of the main run instead (re-warmed)
BR=$(C branch_from)
[ -f "$BR" ] || BR=$(C fallback_branch_from)
ARGS="--run $RUN --d $(C d) --heads $(C heads) --layers $(C layers) --total-tokens $(C total_tokens) --lr $(C branch_lr) --beta2 $(C beta2) --warmup $(C warmup) --decay-frac $(C decay_frac) --batch-tokens $(C batch_tokens) --ckpt-minutes 20 --branch-from $BR --branch-lr $(C branch_lr)"

# --- supervised training
fails=0
until [ -f "$OUT/done.json" ]; do
  t0=$(date +%s)
  $JE $PY -m experiments.v5_long train --threads 4 $ARGS >> "$L/train.log" 2>&1
  rc=$?
  [ -f "$OUT/done.json" ] && break
  t1=$(date +%s)
  echo "process ended $(date -u) after $((t1 - t0)) s, exit code $rc (75 = memory guard)" >> "$L/restarts.log"
  if [ $((t1 - t0)) -lt 600 ]; then fails=$((fails + 1)); else fails=0; fi
  [ "$fails" -ge 5 ] && { echo "5 quick failures" > "$L/run.failed"; exit 1; }
  sleep 60
done

# --- final evaluation, same rule as the main run (fp32 state if it is still in RAM, else the bf16 weights on disk)
CK=models/lm/v5/${RUN}_latest.pt
[ -f "$L/state.pt" ] && CK="$L/state.pt"
$JE $PY -m experiments.v5_long eval --run $RUN --ckpt "$CK" --tag final > "$L/eval.log" 2>&1 || { echo "final eval failed" > "$L/run.failed"; exit 1; }
echo "extension finished" > "$L/run.done"
