#!/bin/sh
# v5 long run toward GPT-2 quality (docs/PLAN_V5_FROM_SCRATCH.md §10). Idempotent: after a
# container restart, start it again; it resumes from the last checkpoint.
#   setsid nohup sh experiments/v5_long_run.sh > /dev/shm/engramm/long_run.log 2>&1 < /dev/null &
# 1. benchmark three model sizes once, choose the largest that finishes 0.6 B tokens in ≤ 7 days
# 2. train under a supervisor (restart after a crash, give up after 5 quick failures)
# 3. final evaluation with window 1024 / stride 512 (as GPT-2 was scored) on val-A and test
set -u
cd "$(dirname "$0")/.."
PT=/dev/shm/engramm/pt311
L=/dev/shm/engramm/long
OUT=results/v5/long
mkdir -p "$L" "$OUT"
if [ ! -d "$PT/torch" ]; then
  PIP_CACHE_DIR=/dev/shm/engramm/pipcache TMPDIR=/dev/shm/engramm \
    .venv/bin/python -m pip install -q --target "$PT" --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple torch==2.14.0 || { echo "torch install failed" > "$L/run.failed"; exit 1; }
  rm -rf /dev/shm/engramm/pipcache
fi
export OMP_PROC_BIND=close OMP_PLACES=cores
PY="env PYTHONPATH=$PT:$(pwd) .venv/bin/python -u"
JE="env LD_PRELOAD=/lib/x86_64-linux-gnu/libjemalloc.so.2 MALLOC_CONF=oversize_threshold:1,background_thread:true,metadata_thp:auto,dirty_decay_ms:-1,muzzy_decay_ms:-1"

# --- 1. size from a throughput benchmark (once; the choice is committed in config.json)
if [ ! -f "$OUT/config.json" ]; then
  rm -f "$OUT/bench.jsonl"
  for cfg in "512 8" "640 10" "768 12"; do
    set -- $cfg
    $JE $PY -m experiments.v5_long bench --d "$1" --heads "$2" --threads 4 >> "$L/bench.log" 2>&1 || true
  done
  .venv/bin/python - "$OUT" <<'PYEOF'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
rows = [json.loads(l) for l in open(out / "bench.jsonl")]
total = 6e8
ok = [r for r in rows if r["tokens_per_hour"] * 24 * 7 >= total]
pick = max(ok, key=lambda r: r["d"]) if ok else max(rows, key=lambda r: r["tokens_per_hour"])
cfg = {"d": pick["d"], "heads": pick["heads"], "layers": pick["layers"], "total_tokens": total,
       "lr": round(2e-3 * 384 / pick["d"], 6), "beta2": 0.99, "warmup": 300, "decay_frac": 0.3,
       "batch_tokens": 8192, "expected_days": total / pick["tokens_per_hour"] / 24, "bench": rows,
       "rule": "largest d whose benchmark throughput finishes 0.6 B tokens in <= 7 days; lr = 2e-3 * 384 / d "
               "(best fast-v1 sweep value at d = 384, scaled with 1/width); beta2 = 0.99 (sweep)"}
(out / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")
print("config:", cfg)
PYEOF
fi
C() { .venv/bin/python -c "import json;print(json.load(open('$OUT/config.json'))['$1'])"; }
ARGS="--d $(C d) --heads $(C heads) --layers $(C layers) --total-tokens $(C total_tokens) --lr $(C lr) --beta2 $(C beta2) --warmup $(C warmup) --decay-frac $(C decay_frac) --batch-tokens $(C batch_tokens) --ckpt-minutes 20"

# --- 2. supervised training
fails=0
until [ -f "$OUT/done.json" ]; do
  t0=$(date +%s)
  $JE $PY -m experiments.v5_long train --threads 4 $ARGS >> "$L/train.log" 2>&1
  [ -f "$OUT/done.json" ] && break
  t1=$(date +%s)
  echo "process ended $(date -u) after $((t1 - t0)) s" >> "$L/restarts.log"
  if [ $((t1 - t0)) -lt 600 ]; then fails=$((fails + 1)); else fails=0; fi
  [ "$fails" -ge 5 ] && { echo "5 quick failures" > "$L/run.failed"; exit 1; }
  sleep 60
done

# --- 3. final evaluation (fp32 state if it is still in RAM, else the bf16 weights on disk)
CK=models/lm/v5/long_latest.pt
[ -f "$L/state.pt" ] && CK="$L/state.pt"
$JE $PY -m experiments.v5_long eval --ckpt "$CK" --tag final > "$L/eval.log" 2>&1 || { echo "final eval failed" > "$L/run.failed"; exit 1; }
echo "long run finished" > "$L/run.done"
