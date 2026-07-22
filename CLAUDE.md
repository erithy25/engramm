## Arbeitsweise
- Kleine Commits, eine logische Änderung pro Commit, deutsche Commit-Messages mit Präfix
  (z. B. `v1.1/B3: D6-W4-Formulierung korrigiert`).
- Messwerte gehören in die D-Dokumente, nicht nur ins Terminal.
- **Hintergrund-Läufe: IMMER session-fest** via `nohup <cmd> > logs/<name>.log 2>&1 & echo $! > logs/<name>.pid; disown`
  — überlebt Session-Ende. Status-Check in jeder Session: `ps -p $(cat logs/<name>.pid)` + `tail logs/<name>.log`.
  Python immer mit `-u` (ungepufferte Ausgabe → Live-Log, kein Blindflug). Kriteriumsrelevante Zeitmessungen
  nur unter W16-Bedingungen (D6: caffeinate, Netzteil, Deckel offen, alleiniger Lauf). `logs/` ist gitignored.
- **Missionskontrolle:** Ein separater Claude-Chat (Rolle: Kritiker + Chronist) schreibt die Auftrags-Prompts
  und auditiert Ergebnisse. Bei Widerspruch zwischen Auftrag und Doku: nachfragen, nicht raten.
  Am Ende jeder Session: kurzer Ergebnisbericht (was geändert, welche Commits, was offen).
