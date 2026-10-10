#!/bin/sh
# Resume the v5 long run after a container restart (idempotent, returns immediately).
# Used as a SessionStart hook; safe to run by hand.
cd "$(dirname "$0")/.." || exit 0
[ -f results/v5/long/config.json ] || exit 0
[ -f results/v5/long/done.json ] && exit 0
pgrep -f "^sh experiments/v5_long_run.sh" >/dev/null 2>&1 && exit 0
mkdir -p /dev/shm/engramm
setsid nohup sh experiments/v5_long_run.sh >> /dev/shm/engramm/long_run.log 2>&1 < /dev/null &
echo "v5 long run resumed $(date -u)" >> /dev/shm/engramm/resume.log
exit 0
