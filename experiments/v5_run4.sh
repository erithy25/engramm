#!/bin/sh
# v5 run 4: fast training recipe (experiments/v5_fast.py) against the current plain recipe.
# Needs an idle machine (run 3 finished). Start detached:
#   setsid nohup sh experiments/v5_run4.sh > /dev/shm/engramm/v5/run4.log 2>&1 < /dev/null &
# Stages (each writes its measurements to results/v5/run4/ as soon as it has them):
#   1. learning-rate × β₂ sweep of fast-v1: 4 runs of 45 min, two at a time, chosen by val-A
#   2. main pair, 3 h each, pinned to separate cores: plain (A) and fast-v1 with the chosen
#      setting (B); both evaluated at 1 / 2 / 3 h. B's 1 h and 2 h points are taken at full
#      learning rate (no decay yet), so they understate B: the time multiplier read from them
#      is a lower bound. (Cooldown branches would remove that bias but need 1.3 GB checkpoints,
#      too much for the container's memory limit next to two training processes.)
set -eu
cd "$(dirname "$0")/.."
D=/dev/shm/engramm/v5
PT=/dev/shm/engramm/pt311
OUT=results/v5/run4
mkdir -p "$D" "$OUT"
rm -f "$D/run4.done" "$D/run4.failed"
fail() { echo "$1" > "$D/run4.failed"; exit 1; }
[ -f "$D/region_pp.npy" ] || fail "region inputs missing (run experiments/v5_run3.sh first)"
export OMP_PROC_BIND=close OMP_PLACES=cores NUMBA_THREADING_LAYER=workqueue
PY="env PYTHONPATH=$PT:$(pwd) .venv/bin/python -u"
JE="env LD_PRELOAD=/lib/x86_64-linux-gnu/libjemalloc.so.2 MALLOC_CONF=oversize_threshold:1,background_thread:true,metadata_thp:auto,dirty_decay_ms:-1,muzzy_decay_ms:-1"

# --- 1. sweep (results/v5/run4/sweep_<name>/)
sweep() {  # name lr beta2 cores
  taskset -c "$4" $JE $PY -m experiments.v5_fast train --hours 0.75 --threads 2 --lr "$2" --beta2 "$3" \
    --results "run4/sweep_$1" --ckpt-dir "fast_sweep_$1" --save-final 0 > "$D/run4_sweep_$1.log" 2>&1
}
if [ ! -f "$OUT/sweep.json" ]; then
  sweep lr0.002_b0.99 2e-3 0.99 0,1 & p1=$!
  sweep lr0.004_b0.99 4e-3 0.99 2,3 & p2=$!
  wait $p1 || fail "sweep 1"; wait $p2 || fail "sweep 2"
  sweep lr0.002_b0.999 2e-3 0.999 0,1 & p1=$!
  sweep lr0.004_b0.999 4e-3 0.999 2,3 & p2=$!
  wait $p1 || fail "sweep 3"; wait $p2 || fail "sweep 4"
  .venv/bin/python - "$OUT" <<'PYEOF'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
rows = {}
for d in sorted(out.glob("sweep_*")):
    f = d / "eval_fast_0.75h.json"
    if f.exists():
        r = json.loads(f.read_text())
        rows[d.name[len("sweep_"):]] = {"val_a": r["val_a"]["bpb_net_alone"], "test": r["test"]["bpb_net_alone"],
                                        "tokens_seen": r["tokens_seen"]}
best = min(rows, key=lambda k: rows[k]["val_a"])
lr, b2 = best.split("_")
(out / "sweep.json").write_text(json.dumps({"runs": rows, "chosen_by_val_a": best,
                                            "lr": float(lr[2:]), "beta2": float(b2[1:])}, indent=1) + "\n")
print("sweep:", rows, "→", best)
PYEOF
fi
LR=$(.venv/bin/python -c "import json;print(json.load(open('$OUT/sweep.json'))['lr'])")
B2=$(.venv/bin/python -c "import json;print(json.load(open('$OUT/sweep.json'))['beta2'])")

# --- 2. main pair
taskset -c 0,1 $PY experiments/v5_residual.py train --arm plain --hours 3 --threads 2 --results run4 \
  --ckpt-dir plain_run4 > "$D/run4_plain.log" 2>&1 & pa=$!
taskset -c 2,3 $JE $PY -m experiments.v5_fast train --hours 3 --threads 2 --lr "$LR" --beta2 "$B2" \
  --eval-hours 1,2,3 --results run4 --ckpt-dir fast_run4 > "$D/run4_fast.log" 2>&1 & pb=$!
wait $pa || fail "plain arm"
wait $pb || fail "fast arm"
.venv/bin/python -m experiments.v5_report --run run4 --fast > "$D/report_run4.txt" 2>&1 || true
echo "run 4 finished" > "$D/run4.done"
