# VORREGISTRIERUNG — ChatBench-EN v1 (ENGRAMM Chat v3, Phasen 1 und 8)

Stand: 2026-09-29. Dieses Protokoll gilt für jede Aussage der Form „ENGRAMM ist in Kategorie X so gut wie
System Y“. Die Werkzeuge liegen in `engramm/bench/chatbench.py` und `experiments/chatbench.py`.

## 1. Prompts

- Geschrieben von **mindestens 20 externen Personen**, je höchstens 65 Prompts, nach einem festen Briefing (§ 6).
- Kein Prompt stammt von einem Sprachmodell. Prompts des Entwicklerteams (`data/chatbench/dev_team.jsonl`,
  `writer: team`) dienen nur der Entwicklung und fließen in keine Aussage ein.
- **Kategorien und Zielgrößen für den Endtest (300):**
  - `smalltalk` 70
  - `memory` 40 (mehrere Züge: erzählen, dann fragen)
  - `multiturn` 30 (Rückbezüge)
  - `facts` 50
  - `explain` 50
  - `writing` 50
  - `robustness` 10 (Tippfehler, Unsinn, Krisen)
- **Duplikate werden entfernt:**
  - untereinander;
  - gegen alle Wissenspakete und die Dialogbank (normalisierter Text).
- **Format:** JSON-Zeilen `{"id", "category", "turns", "writer", "note"}`. Bewertet wird nur die Antwort auf den
  letzten Zug.

## 2. Teilmengen

- Die Einteilung erfolgt per SHAKE-256 der ID mit dem Salz `chatbench-v1`:
  - 45 % dev
  - 20 % val
  - 25 % test (versiegelt)
  - 10 % Reserve
- Neue Prompts verschieben keine alten.
- **Test bleibt versiegelt:**
  - Antworten werden je Registrierung genau einmal erzeugt.
  - Sie werden einmal bewertet.
  - Vorher gibt es keinen Blick auf den Test.

## 3. Systeme

- **ENGRAMM:** die eingefrorene App-Konfiguration (Commit-Hash in der Registrierung), feste Uhr.
- **Gegner:**
  - ChatGPT in der Standardeinstellung, ohne Gedächtnis, einmal bei der Registrierung abgefragt und versiegelt;
  - optional ein lokales 3B-Modell als neuronale Referenz auf gleicher Hardware;
  - v14 (`44c0bbc`) als Untergrenze.
- **Rolle von ChatGPT:** nur Gegner im Blindtest. Ein Sprachmodell ist **nie Richter** und liefert **nie
  Trainingsdaten**.

## 4. Bewertung

- **Bewerter:** mindestens 15 Personen, 3 Urteile pro Paar.
- **Blind:** Die Reihenfolge von A und B wird per SHAKE-256 gezogen. Systemnamen und Quellenanzeigen sind
  ausgeblendet.
- **Bewertungsseite:** eine statische HTML-Datei (`experiments/chatbench.py sheet`). Die Urteile werden als JSON
  heruntergeladen; es gibt keinen Server.
- **Je Paar:** besser (A/B/gleich) und je Antwort „akzeptabel“ (ja/nein).
- **Faktenprüfung:** Eine eigene Person prüft Antworten der Kategorien `facts` und `explain` Aussage für Aussage
  (Aussagen-Korrektheit).

## 5. Auswertung

- **Kennzahl:** P = (Siege + ½ Unentschieden) / N je Kategorie. Pro Prompt wird zuerst über die Bewerter
  gemittelt.
- **Intervall:** Cluster-Bootstrap über Prompts, 2.000 Wiederholungen, Seed 42, 95 %-Intervall.
- **Zusätzlich berichtet:**
  - Akzeptanzquote je System und Kategorie;
  - Krippendorffs α (nominal);
  - Aussagen-Korrektheit.
- **Parität in einer Kategorie:** untere 95 %-Grenze von P ≥ 0,40 **und** P ≥ 0,45. **Parität gesamt** heißt:
  in jeder Kategorie.
- **K3:** Liegt α unter 0,2, werden keine Paritätsaussagen gemacht, bis das Verfahren repariert ist.

## 6. Briefing für Prompt-Schreibende (Kurzfassung)

- **Schreib, was du einen Assistenten wirklich fragen würdest,** und zwar auf Englisch, gemischt über die
  Kategorien.
- **Bei `memory`:** erst etwas über dich erzählen, dann danach fragen.
- **Bei `multiturn`:** Rückfragen mit „he“, „it“, „there“ usw.
- **Keine** Fragen zu Ereignissen nach 2025, **keine** privaten Daten Dritter und **keine** Fangfragen, die nur
  auf einen Zahlendreher zielen.

## 7. Automatische Prüfungen (jeder Build, ohne Menschen)

`python -m experiments.chatbench selfcheck --items data/chatbench/dev_team.jsonl`:

- Die Prüfung meldet:
  - Absturz;
  - leere Antwort;
  - wiederholte Antwort innerhalb eines Gesprächs;
  - Krisenfall ohne Hilfenummern.
- Sie zählt, wie viele Faktenantworten eine Quelle haben, und misst die Zeit pro Zug (Container-Kandidat).
- Das Ergebnis steht in `results/chatbench/selfcheck.json`.
