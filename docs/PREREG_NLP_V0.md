# VORREGISTRIERUNG — ENGRAMM Chat v3, Phase 2: Sprachgrundlagen v0

Stand: 2026-09-29, registriert **vor** jeder Messung auf den Testteilen. Entwickelt und abgestimmt wird nur auf
den Trainings- und Dev-Teilen. Auf jedem Testteil gibt es genau einen Lauf.

## Was gemessen wird

| Nr. | Komponente | Daten | Maß | Schwelle |
|---|---|---|---|---|
| N1 | Wortarten-Tagger (`engramm/nlp/pos.py`) | UD English EWT r2.14, `test` (2.077 Sätze) | UPOS-Genauigkeit | **≥ 94,0 %** |
| N2 | Satzbau-Parser (`engramm/nlp/parse.py`) mit vorhergesagten Wortarten | UD EWT r2.14, `test` | UAS (ohne Satzzeichen-Sonderregel, alle Wörter) | **≥ 84,0 %** |
| N3 | Absichten (`engramm/nlp/intent.py`) | MASSIVE 1.1 en-US, `test` (2.974 Äußerungen, 60 Absichten) | Makro-F1 | **≥ 0,80** |
| N4 | Tempo | 1.000 Sätze aus EWT `dev`, Tagger + Parser + Absicht | Median je Satz, Container | **≤ 50 ms** (Container-Kandidat nach `docs/PROTOCOL.md`) |

Zusätzlich berichtet werden, ohne Schwelle:
- LAS des Parsers;
- XPOS ist nicht Teil der Messung;
- Genauigkeit der Absichten;
- Modellgrößen.

## Verfahren

- **Training nur auf `train`.** Der Parser wird mit Wortarten trainiert, die per 4-fach-Jackknifing vorhergesagt
  wurden, damit Training und Anwendung dieselbe Fehlerart sehen.
- **Epochen** werden auf `dev` festgelegt: Tagger 8, Parser 10, Absichten 12, wie im Code eingetragen.
- **Nachtrag vor dem Testlauf (2026-09-29):** Auf `dev` wurden die Tagger-Merkmale erweitert: Suffix 1 und 4,
  Präfix 2 und 3, Wortpaare, Ziffern, Bindestrich, Länge. Die Epochen stiegen von 6 auf 8. Auf `dev` stieg UPOS
  damit von 94,19 % auf 94,85 %. `test` war zu diesem Zeitpunkt nicht angesehen.
- **Nicht-projektive Trainingssätze** (in EWT unter 5 %) werden beim Parser-Training übersprungen. Gemessen wird
  auf allen Testsätzen.
- **Determinismus:** feste Reihenfolge per SHAKE-256; zwei Läufe ergeben dieselben Gewichte.
- **Ein Lauf:** `python -u -m experiments.nlp_train --test` schreibt das Ergebnis nach `results/nlp/nlp_v0_test.json`.
  Es wird unverändert in `docs/EXPECTATIONS.md` eingetragen, auch wenn Schwellen verfehlt werden.

## Erwartung (vorab)

| Kriterium | Erwartete Chance |
|---|---|
| N1 | ~85 % |
| N2 | ~60 % |
| N3 | ~80 % |
| N4 | ~85 % |

Begründung:
- Gemittelte Perzeptrons erreichen auf EWT typischerweise 94–95 % UPOS.
- Gierige Übergangsparser liegen auf Web-Text etwa bei 84–87 % UAS.
- Lineare Modelle erreichen auf MASSIVE etwa 0,80–0,86 Makro-F1.

## Lizenzen

- UD English EWT: CC BY-SA 4.0.
- MASSIVE: CC BY 4.0.
- Beide werden nur zum Training genutzt. Ausgeliefert werden nur die gelernten Gewichte, mit Namensnennung in
  `docs/DATA_LICENSES.md`.
