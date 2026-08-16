## Arbeitsweise
- Kleine Commits, eine logische Änderung pro Commit, deutsche Commit-Messages mit Präfix
  (z. B. `v1.1/B3: D6-W4-Formulierung korrigiert`).
- Messwerte gehören in die D-Dokumente, nicht nur ins Terminal.
- **Hintergrund-Läufe: IMMER session-fest** via `nohup <cmd> > logs/<name>.log 2>&1 & echo $! > logs/<name>.pid; disown`
  — überlebt Session-Ende. Status-Check in jeder Session: `ps -p $(cat logs/<name>.pid)` + `tail logs/<name>.log`.
  **Auf das Ende warten immer über die PID, nie über den Prozessnamen:**
  `tail --pid=$(cat logs/<name>.pid) -f /dev/null` (blockiert ohne Polling), ersatzweise
  `while kill -0 $(cat logs/<name>.pid) 2>/dev/null; do sleep 30; done`.
  Eine PID ist eindeutig, ein Name nie — ein `pgrep -f run_benchmark` trifft auch die
  Warteschleife selbst und meldet dann dauerhaft „läuft noch" (beobachtet 2026-08-15).
  Python immer mit `-u` (ungepufferte Ausgabe → Live-Log, kein Blindflug). Kriteriumsrelevante Zeitmessungen
  nur unter W16-Bedingungen (D6: caffeinate, Netzteil, Deckel offen, alleiniger Lauf). `logs/` ist gitignored.
- **Speicherschätzungen sind untere Schranken, keine Erwartungswerte.** Wer die im Code
  sichtbaren Arrays addiert, bekommt einen Boden, nie eine Decke — transiente Kopien,
  Interpreter-Overhead und Ausreißer im Datensatz fehlen darin. Zweimal gemessen: 4,8 GB
  geschätzt gegen 12,25 GB real, 4,9 GB gegen 6,26 GB (`docs/DEVIATIONS.md`). Wo eine
  Messung bezahlbar ist, wird gemessen statt geschätzt.
- **Schwellen stehen vor der Messung fest und werden nicht abgewogen.** Die 6-GB-Grenze
  wurde um 4 % gerissen (6,26 gegen 6,00) — nahe genug, dass ein „ist doch praktisch
  gleich" plausibel geklungen hätte und falsch gewesen wäre.
- **Missionskontrolle:** Ein separater Claude-Chat (Rolle: Kritiker + Chronist) schreibt die Auftrags-Prompts
  und auditiert Ergebnisse. Bei Widerspruch zwischen Auftrag und Doku: nachfragen, nicht raten.
  Am Ende jeder Session: kurzer Ergebnisbericht (was geändert, welche Commits, was offen).
