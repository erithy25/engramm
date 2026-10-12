#!/usr/bin/env bash
# Status of the H100 run (docs/H100_ANLEITUNG.md):  bash experiments/h100_status.sh
cd "$(dirname "$0")/.." || exit 1
W=${H100_WORK:-/workspace/h100}
PRICE=${H100_PRICE:-3.99}
python3 - "$W" "$PRICE" <<'EOF'
import json, os, sys, time
from pathlib import Path
W, price = Path(sys.argv[1]), float(sys.argv[2])
R = Path("results/v5/h100")
stages = ["packages", "base", "extra", "sweep", "merge", "contamination", "main", "finished"]
names = {"packages": "Pakete", "base": "Basisdaten", "extra": "Zusatztext (C4)", "sweep": "Lernraten-Suche",
         "merge": "Zusammenführen", "contamination": "Kontaminationsprüfung", "main": "Haupttraining + Endmessung",
         "finished": "Ergebnisse gesichert"}
done = [s for s in stages if (W / "stages" / s).exists()]
started = float((W / "started").read_text()) if (W / "started").exists() else None
hours = (time.time() - started) / 3600 if started else 0.0
print(f"Laufzeit seit Start: {hours:.2f} h  (≈ {hours * price:.2f} $ bei {price} $/h)")
for s in stages:
    print(f"  [{'x' if s in done else ' '}] {names[s]}")
if (W / "FAILED").exists():
    print("FEHLER:", (W / "FAILED").read_text().strip(), "– Neustart: nohup bash experiments/h100_run.sh > /workspace/h100_console.log 2>&1 &")
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
                  f"({100 * r['frac']:.1f} %), {r['tok_per_s'] / 1e3:.0f} k Token/s, Rest ≈ {left / 3600:.1f} h, "
                  f"Verlust {r['loss']:.3f}")
    c = R / f"curve_{tag}.jsonl"
    if c.exists():
        pts = [json.loads(l) for l in c.read_text().splitlines() if l.strip()]
        if pts:
            print("Lernkurve val-A (bpb): " + ", ".join(f"{p['tokens'] / 1e9:.1f} Mrd. → {p['bpb']:.3f}" for p in pts[-6:]))
if (W / "SUMMARY.txt").exists():
    print("\n" + (W / "SUMMARY.txt").read_text())
EOF
echo "--- letzte Zeilen des Protokolls ($W/run.log):"
tail -n 5 "$W/run.log" 2>/dev/null
