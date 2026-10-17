# Cost meter of the H100 run (docs/H100_ANLEITUNG.md). Sourced by h100_run.sh and h100_status.sh; needs W.
#
# Every pod session (= container lifetime, start = now - etimes of PID 1) has a file $W/meter/<start> holding
# "<start> <last tick>"; the billed pod time is the sum over these files. At the dollar limit in $W/cost_limit
# ("<max $> <price $/h>", written by h100_run.sh) the meter stops the pod and retries every minute until the pod
# is gone. After the limit the pod gets METER_GRACE_S (default 1800 s = 30 min; Sela-2: 600) in total (all later
# sessions together) to save results.
METER_GRACE_S=${METER_GRACE_S:-1800}

# RunPod sets these for PID 1; a terminal may not have them (Jupyter normally passes them on)
pod_env() {
  local k v
  for k in RUNPOD_POD_ID RUNPOD_API_KEY; do
    if [ -z "${!k:-}" ] && [ -r /proc/1/environ ]; then
      v=$({ tr '\0' '\n' < /proc/1/environ; } 2>/dev/null | sed -n "s/^$k=//p" | head -1)
      [ -n "$v" ] && export "$k=$v"
    fi
  done
  return 0
}

billed_s() { cat "$W"/meter/* 2>/dev/null | awk 'NF == 2 {s += $2 - $1} END {printf "%d\n", s + 0}'; }
limit_s() { awk '{printf "%d\n", $1 / $2 * 3600}' "$W/cost_limit" 2>/dev/null || echo 0; }

# Start of this pod session (container start); the meter's session file name.
session_start() {
  local s0 up
  s0=$(cat /tmp/engramm_session 2>/dev/null)
  if ! [[ "$s0" =~ ^[0-9]+$ ]]; then
    up=$(ps -o etimes= -p 1 2>/dev/null | tr -d ' '); [[ "$up" =~ ^[0-9]+$ ]] || up=0
    s0=$(( $(date +%s) - up ))
  fi
  echo "$s0"
}

# Seconds until the meter stops this pod, minus one tick of margin (never negative); huge when no limit is set.
# The meter stops at b >= l and (session age >= grace or b >= l + grace); b and the age both grow by 1 s per s.
time_left() {
  local l b age r1 r2 t g=$METER_GRACE_S
  l=$(limit_s); b=$(billed_s)
  [ "$l" -gt 0 ] || { echo 999999; return 0; }
  age=$(( $(date +%s) - $(session_start) ))
  r1=$(( g - age )); r2=$(( l + g - b )); r1=$(( r1 < r2 ? r1 : r2 ))
  t=$(( l - b > r1 ? l - b : r1 )); t=$(( t - 60 ))
  echo $(( t > 0 ? t : 0 ))
}

# Stop this pod (data in /workspace stays); 0 when one of the ways was accepted.
stop_pod() {
  [ -n "${RUNPOD_POD_ID:-}" ] || return 1
  runpodctl stop pod "$RUNPOD_POD_ID" >/dev/null 2>&1 && return 0
  runpodctl pod stop "$RUNPOD_POD_ID" >/dev/null 2>&1 && return 0
  if [ -n "${RUNPOD_API_KEY:-}" ]; then
    curl -s --max-time 60 -H "Content-Type: application/json" \
      -d "{\"query\": \"mutation { podStop(input: {podId: \\\"$RUNPOD_POD_ID\\\"}) { id desiredStatus } }\"}" \
      "https://api.runpod.io/graphql?api_key=$RUNPOD_API_KEY" 2>/dev/null | grep -q desiredStatus && return 0
  fi
  return 1
}

start_meter() {
  [ -n "${RUNPOD_POD_ID:-}" ] || [ "${H100_TEST_METER:-0}" = 1 ] || return 0
  [ -f "$W/cost_limit" ] || return 0
  mkdir -p "$W/meter"
  local mp up s0 old
  mp=$(cat /tmp/engramm_meter.pid 2>/dev/null)
  if [[ "$mp" =~ ^[0-9]+$ ]] && ps -o stat= -p "$mp" 2>/dev/null | grep -qv '^Z'; then return 0; fi   # alive, not a zombie
  up=$(ps -o etimes= -p 1 2>/dev/null | tr -d ' ')          # this container (= pod session) is running since …
  [[ "$up" =~ ^[0-9]+$ ]] || up=0
  s0=$(( $(date +%s) - up ))
  old=$(cat /tmp/engramm_session 2>/dev/null)                 # same session as an earlier meter: same file
  if [[ "$old" =~ ^[0-9]+$ ]] && [ $(( s0 - old )) -le 120 ] && [ $(( old - s0 )) -le 120 ]; then s0=$old; fi
  echo "$s0" > /tmp/engramm_session
  echo "$s0 $(date +%s)" > "$W/meter/.tick_$s0" && mv -f "$W/meter/.tick_$s0" "$W/meter/$s0"   # first tick at once
  ( exec 9>&-
    while true; do
      now=$(date +%s)
      echo "$s0 $now" > "$W/meter/.tick_$s0" && mv -f "$W/meter/.tick_$s0" "$W/meter/$s0"   # hidden: not summed
      b=$(billed_s); l=$(limit_s)
      if [ "$l" -gt 0 ] && [ "$b" -ge "$l" ] && { [ $(( now - s0 )) -ge "$METER_GRACE_S" ] || [ "$b" -ge $(( l + METER_GRACE_S )) ]; }; then
        last=$(cat "$W/COST_LIMIT_REACHED" 2>/dev/null)
        if ! [[ "$last" =~ ^[0-9]+$ ]] || [ "$last" -lt "$s0" ]; then         # once per session
          echo "[$(date -u +%H:%M:%S) UTC] KOSTENBREMSE: $(cut -d' ' -f1 "$W/cost_limit") \$ erreicht – der Pod stoppt sich jetzt (Daten in /workspace bleiben)." >> "$W/run.log"
          date +%s > "$W/COST_LIMIT_REACHED"
        fi
        [ -n "${RUNPOD_POD_ID:-}" ] || exit 0                  # test machine: nothing to stop
        stop_pod || echo "[$(date -u +%H:%M:%S) UTC] KOSTENBREMSE: Stopp fehlgeschlagen, neuer Versuch in 60 s – bitte den Pod von Hand stoppen (Stop)." >> "$W/run.log"
      fi
      sleep 60
    done ) >/dev/null 2>&1 &
  echo $! > /tmp/engramm_meter.pid
}
