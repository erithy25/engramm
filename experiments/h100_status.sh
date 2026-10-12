#!/usr/bin/env bash
# Status of the H100 run (docs/H100_ANLEITUNG.md):  bash /workspace/engramm/experiments/h100_status.sh
cd "$(dirname "$0")/.." || exit 1
W=${H100_WORK:-/workspace/h100}
PRICE=${H100_PRICE:-3.99}
if flock -n /tmp/engramm_h100.lock true 2>/dev/null; then ALIVE=0; else ALIVE=1; fi
python3 - "$W" "$PRICE" "$ALIVE" <<'EOF'
import json, sys, time
from pathlib import Path
W, price, alive = Path(sys.argv[1]), float(sys.argv[2]), sys.argv[3] == "1"
R = Path("results/v5/h100")
restart = "setsid nohup bash /workspace/engramm/experiments/h100_run.sh > /workspace/h100_console.log 2>&1 &"
stages = ["packages", "base", "extra", "sweep", "merge", "contamination", "main", "finished"]
names = {"packages": "Pakete", "base": "Basisdaten", "extra": "Zusatztext (C4)", "sweep": "Lernraten-Suche",
         "merge": "Zusammenführen", "contamination": "Kontaminationsprüfung", "main": "Haupttraining + Endmessung",
         "finished": "Lauf beendet"}
done = [s for s in stages if (W / "stages" / s).exists()]
started = float((W / "started").read_text()) if (W / "started").exists() else None
hours = (time.time() - started) / 3600 if started else 0.0
finished = "finished" in done
uploaded = (W / "stages" / "uploaded").exists()
print(f"Lauf aktiv: {'ja' if alive else 'NEIN'}" + ("" if alive or finished else
      f"   → Neustart: zuerst Befehl 2 (Schlüssel), dann:  {restart}"))
print(f"Laufzeit seit dem ersten Start: {hours:.2f} h  (≈ {hours * price:.0f} $ bei {price} $/h)")
gh = W / "github_check"
print("GitHub-Schlüssel geprüft: " + (gh.read_text().strip() if gh.exists() else "noch nicht (Lauf hat Prüfung 0 nicht erreicht)"))
# newest write of anything the run produces: a live run never stays silent for an hour
watched = [W / "run.log", W / "sweep.log", Path("/workspace/h100_console.log")]
watched += list(R.glob("train_log_*.jsonl")) + list(R.glob("curve_*.jsonl")) + list(R.glob("sweep_lr*.json"))
watched += list(Path("data/cache/lm/tokens/extra").glob("*.done.json")) + list(Path("data/cache/lm/tokens/h100").glob("*"))
mtimes = [f.stat().st_mtime for f in watched if f.exists()]
if alive and mtimes:
    idle = (time.time() - max(mtimes)) / 60
    print(f"Letzte Aktivität: vor {idle:.0f} min" + ("   ← ungewöhnlich lange still: diese Ausgabe an Claude schicken" if idle > 60 else ""))
if alive and hours > 9:
    print("Laufzeit über 9 h – länger als geplant: diese Ausgabe an Claude schicken")
for s in stages:
    print(f"  [{'x' if s in done else ' '}] {names[s]}")
if (W / "FAILED").exists():
    print("FEHLER:", (W / "FAILED").read_text().strip().split(" ", 1)[-1])
    print(f"  → Neustart (setzt fort): zuerst Befehl 2 (Schlüssel), dann:  {restart}")
if not (W / "stages" / "extra").exists() and Path("data/cache/lm/tokens/extra").exists():
    n = len(list(Path("data/cache/lm/tokens/extra").glob("*.done.json")))
    print(f"Zusatztext: {n} Teile fertig")
for lr_file in sorted(R.glob("sweep_lr*.json")):
    d = json.loads(lr_file.read_text())
    print(f"Lernrate {d['lr']:g}: val-A {d['bpb']:.4f} bpb")
for tag in ("main", "main_lrhalf"):
    f = R / f"train_log_{tag}.jsonl"
    if f.exists():
        rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        if rows:
            r = rows[-1]
            total = r["tokens"] / max(r["frac"], 1e-9)
            left = (total - r["tokens"]) / max(r["tok_per_s"], 1)
            print(f"Haupttraining ({tag}): {r['tokens'] / 1e9:.2f} von {total / 1e9:.2f} Mrd. Token "
                  f"({100 * r['frac']:.1f} %), {r['tok_per_s'] / 1e3:.0f} k Token/s, Rest ≈ {left / 3600:.1f} h")
    c = R / f"curve_{tag}.jsonl"
    if c.exists():
        pts = [json.loads(l) for l in c.read_text().splitlines() if l.strip()]
        if pts:
            print("Lernkurve val-A (bpb): " + ", ".join(f"{p['tokens'] / 1e9:.1f} Mrd. → {p['bpb']:.3f}" for p in pts[-6:]))
if (W / "SUMMARY.txt").exists():
    print("\n" + (W / "SUMMARY.txt").read_text().rstrip())
if finished:
    if uploaded:
        print(f"\nAuf GitHub gesichert: JA (Branch {(W / 'stages' / 'uploaded').read_text().strip()}, Modell als privater Entwurf-Release)")
        print("→ Den Pod jetzt beenden: Stop, dann Terminate.")
    else:
        print("\nAuf GitHub gesichert: NEIN – vor dem Beenden herunterladen (Anleitung Schritt 5b):")
        print(f"   {W / 'h100_results.tgz'}   und   {W / 'MODELL.pt'}")
EOF
echo "--- letzte Zeilen des Protokolls ($W/run.log, Zeiten in UTC = deutsche Zeit minus 2 h):"
tail -n 5 "$W/run.log" 2>/dev/null
