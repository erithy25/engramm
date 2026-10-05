# PREREG — ENGRAMM „Verstehen“ v0 (registriert 4. Oktober 2026, vor der ersten Messung mit dem neuen System)

## Frage

Kann ENGRAMM ohne neuronales Netz Alltagssituationen **allgemein** verstehen – statt Thema für Thema von Hand –,
sodass Antworten auf **ungesehene** Gespräche deutlich seltener schwach sind?

Vorher (Proben 111–124): Jede neue Probe startete bei rund 60–70 % schwachen Antworten im ersten Lauf und kam erst
nach Anpassungen genau für diese Probe auf 0.

## Daten

| Satz | Inhalt | Wer hat ihn geschrieben | Wer kennt den Inhalt |
|---|---|---|---|
| `experiments/probes/sealed/u0_1…u0_6.json` | 6 × (8 englische + 8 deutsche Gespräche), 4–7 Nutzernachrichten je Gespräch (EN 323, DE 313 Nachrichten) | ein getrennter Claude-Agent nach Vorgaben (Alltag, Probleme, gute Nachrichten, Gefühle, Rückfragen mit Pronomen, Ellipsen, Korrekturen, Themenwechsel), Themen ausdrücklich **außerhalb** aller bisherigen Proben, Batterien und Gesprächsbank-Blöcke | niemand aus der Entwicklung |
| `experiments/probes/sealed/final_1…final_3.json` | 3 × (8 EN + 8 DE) Gespräche, gleiche Vorgaben | derselbe Agent | niemand; erst bei der Endmessung (U6) einmal gelaufen |
| `experiments/probes/sets/*.json` | alle bisherigen Proben (verbraucht) | Entwicklung | Entwicklung – nur zur Entwicklung und als Rückfall-Prüfung |

Die Prüfsummen stehen in `docs/UNDERSTAND_SEAL.txt`; `experiments/probes/run.py` verweigert einen versiegelten Satz,
der nicht mehr zur Prüfsumme passt. Versiegelte Sätze und ihre Transkripte werden in der Entwicklung nie gelesen; die
Transkripte liegen außerhalb des Repos und gehen nur an den Leser.

## Messung (je Phase genau einmal je Satz)

- Lauf: `python -m experiments.probes.run SATZ --out TRANSKRIPT --quiet`, jedes Gespräch in eigenem Gesprächs-Kontext,
  ein gemeinsames Gedächtnis je Satz, Lite-Paket.
- **Leser:** ein getrennter Claude-Agent (kein Mensch; er ist an der Entwicklung nicht beteiligt und meldet nur Zahlen
  und Fehlerklassen, keine Inhalte). Er liest jede Antwort und markiert sie als **schwach**, wenn mindestens eins gilt:
  1. Füllfloskel, die den Inhalt übergeht („Tell me more?“, „I see.“, „Erzähl ruhig mehr“, „Interessant“);
  2. Missverständnis: die Antwort passt nicht zur Nachricht oder zum Gesprächsverlauf;
  3. falsches Gedächtnis (Unsinn als Name, Wohnort, Beruf, Vorliebe gemerkt oder genannt);
  4. eine Frage oder Bitte um Rat bleibt unbeantwortet oder wird ausgewichen, obwohl eine hilfreiche Antwort möglich wäre;
  5. Wiederholung oder doppelte Antwort, die zweimal dasselbe sagt;
  6. sachlich falsch oder unsicherer Rat (Gesundheit, Recht, Geld) ohne Warnhinweis;
  7. falsche Sprache (Deutsch gefragt, Englisch geantwortet – außer bei der allerersten Begrüßung);
  8. widerspricht dem Gesagten (falsches Tier, falsche Person, erfindet Details).
  Nicht schwach: kurze, passende Reaktionen; ehrliches „weiß ich nicht“, wenn keine sinnvolle Antwort möglich ist.
- Gemeldet werden je Satz und Sprache: Zahl der Antworten, Zahl der schwachen, Verteilung auf die Klassen 1–8.

## Schwellen (vorab, nicht nachträglich verschoben)

| Phase | Kriterium | Schwelle |
|---|---|---|
| U0 | Ausgangswert auf u0_1…u0_6 (alter Stand 22010e1) | wird nur festgehalten |
| U1 | Situationsrahmen auf einem versiegelten, beschrifteten Satz (`sealed/frames_test.jsonl`, ebenfalls fremd geschrieben): Ereignisart richtig | ≥ 85 % |
| U1 | Rollen (Person, Gegenstand, Körperteil) richtig, wo beschriftet | ≥ 75 % |
| U2 | schwache Antworten auf u0_1…u0_6, EN und DE zusammen | ≤ 35 % (und keine Sprache über 45 %) |
| U3 | Problemfälle mit Bitte um Rat: konkreter, passender Rat | ≥ 60 % der Fälle (vom Leser gezählt) |
| U3 | Gesundheits-, Rechts- oder Geldrat ohne Quelle oder Warnhinweis | 0 |
| U4 | schwache Antworten auf u0_1…u0_6 | ≤ 20 % (keine Sprache über 30 %) |
| U4 | Korrektur-Test (`tests/test_learn.py`): derselbe Fehler kehrt nach einer Korrektur zurück | ≤ 5 % |
| U4 | „vergiss das“ stellt den Lernstand bitgleich her | 100 % |
| U5 | Schlussfolgerungs-Satz (`sealed/infer_test.jsonl`, 40 Fälle, fremd geschrieben) | ≥ 80 % richtig, 0 erfundene Fakten |
| U6 | Endmessung auf final_1…final_3 (einmal) | wird berichtet; Erwartung: ≤ 25 % schwach |
| U7 (Nachtrag 5. Oktober 2026, vor der Messung) | schwache Antworten auf den frischen Sätzen `sealed/u7_1…u7_3.json` (vom selben getrennten Agenten nach denselben Vorgaben, nach U6 geschrieben), ein Lauf, gleicher Leser-Maßstab | ≤ 25 % schwach; Rat ≥ 60 %; 0 unsicherer Rat |

Immer zusätzlich (Rückfall-Schutz): alle 80 Batterieausgaben gleich oder gelesen besser, DEV-Satz unverändert,
NQ-open Dev 22/9 unverändert, volle Testsuite grün, Paket ≤ 4,5 GB, RAM ≤ 1,5 GB, p95 ≤ 1,5 s.

## Ehrliche Einschränkungen

- Der Leser ist ein KI-Agent, kein Mensch. Er ist von der Entwicklung getrennt und blind für die Code-Änderungen,
  aber seine Urteile sind nicht die eines Nutzers. Eine Bewertung durch Menschen (ChatBench) bleibt offen.
- Die Situationsklassen und die allgemeinen Wortlisten (Zustände wie „broken“, „kaputt“) sind von Hand geschrieben;
  Themen sind es nicht. Was die Lexika nicht kennen, kennt auch ENGRAMM nicht.
- Ein Satz, der in einer Phase gemessen wurde, bleibt versiegelt (nur Zahlen gelangen zurück) und wird in der
  nächsten Phase erneut gemessen; das ist eine wiederholte, aber blinde Messung. Die Endmessung nutzt frische Sätze.
