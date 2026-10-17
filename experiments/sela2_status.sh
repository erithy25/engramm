#!/usr/bin/env bash
# Status of the Sela-2 run (docs/SELA2_ANLEITUNG.md):  bash /workspace/engramm/experiments/sela2_status.sh
cd "$(dirname "$0")/.." || exit 1
W=${SELA2_WORK:-/workspace/sela2}
export METER_GRACE_S=600
if flock -n /tmp/engramm_sela2.lock true 2>/dev/null; then ALIVE=0; else ALIVE=1; fi
# On the pod, every status call also makes sure the cost meter runs (e.g. after an unattended pod restart)
. experiments/h100_meter.sh
pod_env
if [ -n "${RUNPOD_POD_ID:-}" ] && [ -f "$W/cost_limit" ]; then
  setsid bash -c 'W="$1"; export METER_GRACE_S=600; . experiments/h100_meter.sh; pod_env; start_meter' _ "$W" </dev/null >/dev/null 2>&1 &
  sleep 1
  # No run in this session: stop the idle pod in 30 min (cancelled by a new start; KEEP suspends it)
  S0=$(session_start)
  read -r MS0 MTOK MAT 2>/dev/null < /tmp/engramm_idle_stop || MS0=""
  if [ "$ALIVE" = 0 ] && { ! [[ "$MS0" =~ ^[0-9]+$ ]] || [ $(( MS0 - S0 )) -gt 120 ] || [ $(( S0 - MS0 )) -gt 120 ]; }; then
    TOK="$S0.$$.$(date +%s%N)"
    echo "$S0 $TOK $(date +%s)" > /tmp/engramm_idle_stop
    setsid bash -c 'sleep 1800
      read -r _ tok _ < /tmp/engramm_idle_stop 2>/dev/null || exit 0
      [ "$tok" = "$2" ] || exit 0
      rm -f /tmp/engramm_idle_stop
      [ -f "$1/KEEP" ] && [ "$(stat -c %Y "$1/KEEP")" -ge "$3" ] && exit 0
      flock -n /tmp/engramm_sela2.lock true || exit 0
      W="$1"; . experiments/h100_meter.sh; pod_env; stop_pod' _ "$W" "$TOK" "$S0" </dev/null >/dev/null 2>&1 &
  fi
  read -r MS0 MTOK MAT 2>/dev/null < /tmp/engramm_idle_stop || MAT=""
  if [ "$ALIVE" = 0 ] && [[ "${MAT:-}" =~ ^[0-9]+$ ]]; then
    IDLE_LEFT=$(( (1800 - $(date +%s) + MAT) / 60 )); [ "$IDLE_LEFT" -ge 0 ] || IDLE_LEFT=0
  fi
fi
python3 - "$W" "$ALIVE" <<'EOF'
import json, sys, time
from pathlib import Path
W, alive = Path(sys.argv[1]), sys.argv[2] == "1"
R = Path("results/sela2")
restart = "setsid nohup bash /workspace/engramm/experiments/sela2_run.sh > /workspace/sela2_console.log 2>&1 &"
stages = ["packages", "data", "probe", "pretrain", "sft", "eval", "finished"]
names = {"packages": "Pakete", "data": "Trainingsdaten (geladen + geprüft)", "probe": "Vorab-Probe",
         "pretrain": "Vortraining", "sft": "Chat-Feinabstimmung", "eval": "Auswertung", "finished": "Lauf beendet"}
done = [s for s in stages if (W / "stages" / s).exists()]
started = float((W / "started").read_text()) if (W / "started").exists() else None
finished = "finished" in done
print(f"Lauf aktiv: {'ja' if alive else 'NEIN'}" + ("" if alive or finished else
      f"   → Neustart: zuerst Befehl 2 (Schlüssel), dann:  {restart}"))
billed = 0
for f in (W / "meter").glob("[0-9]*"):
    try:
        a, b = f.read_text().split()[:2]
        billed += int(b) - int(a)
    except (ValueError, OSError):
        pass
try:
    max_usd, price = (float(x) for x in (W / "cost_limit").read_text().split()[:2])
except (ValueError, OSError):
    max_usd, price = 0.0, 4.01
if started:
    print(f"Laufzeit seit dem ersten Start: {(time.time() - started) / 3600:.2f} h")
if max_usd:
    print(f"Kosten bisher ≈ {billed / 3600 * price:.2f} $ von höchstens {max_usd:g} $ (Kostenbremse, {price:g} $/h)")
    over = billed - max_usd / price * 3600
    if over >= 0:
        print("Grenze erreicht: der Pod stoppt sich (nach einem Neustart bleiben insgesamt höchstens "
              f"{max(0, 600 - over) / 60:.0f} min zum Sichern)")
if (W / "COST_LIMIT_REACHED").exists():
    print("KOSTENBREMSE hat gegriffen: der Pod stoppt sich. Diese Ausgabe an Claude schicken.")
gh = W / "github_check"
print("GitHub-Schlüssel geprüft: " + (gh.read_text().strip() if gh.exists() else "noch nicht"))
watched = [W / "run.log", Path("/workspace/sela2_console.log"), R / "train_log.jsonl", R / "sft_log.jsonl",
           W / "download.log"] + list((W / "probe").glob("*.log"))
mt = [f.stat().st_mtime for f in watched if f.exists()]
if alive and mt:
    idle = (time.time() - max(mt)) / 60
    print(f"Letzte Aktivität: vor {idle:.0f} min" + ("   ← ungewöhnlich lange still: an Claude schicken" if idle > 45 else ""))
for s in stages:
    print(f"  [{'x' if s in done else ' '}] {names[s]}")
if (W / "FAILED").exists():
    print("FEHLER:", (W / "FAILED").read_text().strip().split(" ", 1)[-1])
    print(f"  → Neustart (setzt fort): zuerst Befehl 2 (Schlüssel), dann:  {restart}")
f = R / "train_log.jsonl"
if f.exists() and "pretrain" not in done:
    rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    if rows:
        r = rows[-1]
        total = r["tokens"] / max(r["frac"], 1e-9)
        print(f"Vortraining: {r['tokens'] / 1e9:.2f} von ≈ {total / 1e9:.2f} Mrd. Token ({100 * r['frac']:.1f} %), "
              f"{r['tok_per_s'] / 1e3:.0f} k Token/s, Verlust {r['loss']:.3f}" + (" (Chat-Daten im Mix)" if r.get("decay_mix") else ""))
c = R / "curve.jsonl"
if c.exists():
    pts = [json.loads(l) for l in c.read_text().splitlines() if l.strip()]
    for p in pts[-3:]:
        b = p.get("bpb", {})
        print(f"  Messpunkt {p['tokens'] / 1e9:.2f} Mrd.: " + ", ".join(f"{k[4:]} {v:.3f}" for k, v in sorted(b.items())[:5]))
f = R / "sft_log.jsonl"
if f.exists() and "sft" not in done:
    rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    if rows:
        r = rows[-1]
        print(f"Feinabstimmung: Schritt {r['step']} von {r['of']}, Verlust {r['loss']:.3f}")
up = W / "up"
if (W / "stages" / "sft").exists() and (W / "stages" / "sft").read_text().strip() == "skipped":
    print("Chat-Feinabstimmung übersprungen (zu wenig Zeit bis zur Kostenbremse) – an Claude schicken")
for n, label in (("fortsetzen", "Fortsetzungs-Stand"), ("basis", "Basismodell"), ("chat", "Chat-Modell"),
                 ("ergebnisse", "Messwerte (Archiv im Release)")):
    if (up / f"{n}.ok").exists():
        print(f"Auf GitHub gesichert: {label}")
    elif (up / f"{n}.lock").exists() and (up / f"{n}.log").exists() and alive:
        print(f"Wird hochgeladen: {label}")
if (W / "SUMMARY.txt").exists():
    print("\n" + (W / "SUMMARY.txt").read_text().rstrip())
if finished:
    if (W / "stages" / "uploaded").exists():
        print(f"\nAlles auf GitHub gesichert (Branch {(W / 'stages' / 'uploaded').read_text().strip()}).")
        print("→ Den Pod jetzt beenden: Stop, dann Terminate (falls er sich nicht schon selbst gelöscht hat).")
    else:
        print("\nNICHT alles auf GitHub gesichert – diese Ausgabe an Claude schicken, Pod NICHT löschen.")
EOF
[ -n "${IDLE_LEFT:-}" ] && echo "Kostenschutz: es läuft kein Lauf – der Pod stoppt sich in ${IDLE_LEFT} min selbst (Daten bleiben). Aussetzen: touch $W/KEEP"
echo "--- letzte Zeilen des Protokolls ($W/run.log, Zeiten in UTC = deutsche Zeit minus 2 h):"
tail -n 6 "$W/run.log" 2>/dev/null
