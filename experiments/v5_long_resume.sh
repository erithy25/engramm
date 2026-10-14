#!/bin/sh
# Resume the v5 long run after a container restart (idempotent, returns immediately).
# Used as a SessionStart hook; safe to run by hand.
#   1. main run: training, then its final evaluation (started again after a restart during the evaluation)
#   2. afterwards the extension (PLAN §10, Nachtrag 14. Oktober), if configured and stage 1 was missed
cd "$(dirname "$0")/.." || exit 0
[ -f results/v5/long/config.json ] || exit 0
mkdir -p /dev/shm/engramm
if [ ! -f results/v5/long/eval_final.json ]; then
  [ -f /dev/shm/engramm/long/run.failed ] && exit 0
  pgrep -f "^sh experiments/v5_long_run.sh" >/dev/null 2>&1 && exit 0
  setsid nohup sh experiments/v5_long_run.sh >> /dev/shm/engramm/long_run.log 2>&1 < /dev/null &
  echo "v5 long run resumed $(date -u)" >> /dev/shm/engramm/resume.log
  exit 0
fi
E=results/v5/long_ext1
[ -f "$E/config.json" ] || exit 0
[ -f "$E/eval_final.json" ] && exit 0
[ -f /dev/shm/engramm/long_ext1/run.failed ] && exit 0
[ -f /dev/shm/engramm/long_ext1/not_needed ] && exit 0
pgrep -f "^sh experiments/v5_long_ext_run.sh" >/dev/null 2>&1 && exit 0
setsid nohup sh experiments/v5_long_ext_run.sh >> /dev/shm/engramm/long_ext_run.log 2>&1 < /dev/null &
echo "v5 long run extension resumed $(date -u)" >> /dev/shm/engramm/resume.log
exit 0
