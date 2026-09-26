# VORREGISTRIERUNG — ENGRAMM-Chat v2: Stufen 1.1 bis 5

**Status: REGISTRIERT** am 2026-09-26, nach Stufe 1 (E14) und **vor** jeder Zeile Code der
Stufen 1.1–5. Die Testdaten sind mit diesem Dokument eingefroren (`experiments/chat_v2_data.py`,
`data/chat_v2_templates.json`, Manifest in §3).

Wie in Stufe 1 gilt: kein fremdes KI-Modell, weder im System noch in der Bewertung. Keine
Sprachmodelle, keine trainierten Tagger, keine Wortlisten aus fremden Modellen. Erlaubt sind
Regeln, Zählen im eigenen Korpus und ENGRAMMs HDC-Vektoren. Bewertet wird nur durch exakten
Abgleich mit bekannten Lösungen.

## 1. Ziel

Aus dem Nachschlage-Werkzeug von Stufe 1 wird ein Gesprächspartner:

| Stufe | Was neu ist |
|---|---|
| **1.1** Besser finden | Fragesätze ausschließen, Antworttyp prüfen, Kontext des Vorsatzes, Titel/URL, Quellenpriorität |
| **2** Faktengedächtnis (HDC) | Aussagen werden in Tripel (Ding, Beziehung, Wert) zerlegt und als gebundene Hypervektoren gespeichert; Abfrage über Ähnlichkeit (tippfehlertolerant) |
| **3** Gesprächsgedächtnis | Was du im Chat erzählst, wird gelernt; „vergiss …“ löscht es exakt; Rückfragen mit Pronomen („Wo wurde sie geboren?“) |
| **4** Formulierte Antworten | Kurze Antwort aus dem Fundsatz (Wer/Wann/Wo/Wie viele …) statt ganzer Sätze; „I don't know“ unter der Schwelle |
| **5** Chat-Oberfläche | Gesprächsverlauf im Dashboard, Ende-zu-Ende-Test im Browser, Messung |

## 2. Entwicklungsregel

- Entwickelt und eingestellt wird **nur auf Dev** (SQuAD-Dev2, NQ-Dev, Dev-Formulierungen der
  Fakten und Dialoge). Iterieren ist ausdrücklich erlaubt, so oft wie nötig.
- Vor der Testmessung wird die Konfiguration eingefroren und committet.
- **Die Testmessung läuft genau einmal.** Ein Neustart ist nur nach einem Absturz erlaubt, und
  nur mit unverändertem Code der bewerteten Teile. Jeder Neustart wird dokumentiert.
- Wer nach der Testmessung weiter verbessert, braucht eine neue Registrierung und neue Testdaten.

## 3. Daten

| Satz | Dev | Test |
|---|---|---|
| **SQuAD v1.1** (Pool und Prüfsummen wie in `PREREG_CHAT.md`) | 2.000 Fragen aus Dev-Artikeln | 1.000 Fragen aus Test-Artikeln |
| **NQ-open** (echte Google-Suchanfragen; HF-Revision `5dd9790a…`) | erste 2.000 aus `train` nach SHAKE-256 | alle 3.610 aus `validation` |
| **Erfundene Fakten** (200, `data/lm_facts_templates.json`) | Frageform `dev` | Frageform `test`, sauber und mit Tippfehler |
| **Dialoge über dich** | 100 Dialoge | 200 Dialoge |
| **Rückfrage-Dialoge** | 55 | 55 |

Weitere Regeln:

- **SQuAD:** Die Artikel werden per SHAKE-256(Titel) geteilt, Bit 0 geht an Dev, Bit 1 an Test.
  So stehen Fragen zum selben Absatz nie in beiden Teilen. Die 1.500 Fragen aus Stufe 1 sind
  ausgeschlossen.
- **Prüfsummen NQ-open:** `train` `25d3a544…7d83a`, `validation` `b074bed0…31e12`.
- **Tippfehler:** Ein innerer Buchstabe des erfundenen Namens wird ersetzt. Die Stelle und der
  neue Buchstabe folgen aus SHAKE-256 der Fakten-ID.
- **Dialoge über dich:** Du erzählst 4 von 10 Fakten über dich (Name, Wohnort, Beruf,
  Lieblingsfarbe, Hund, Arbeitgeber, Geburtstag, Bruder, Lieblingsessen, Auto). Dann fragst du
  alle 4 ab, lässt einen davon vergessen und fragst ihn erneut. Zu jedem Dialog gehört ein
  Kontrollskript ohne den vergessenen Fakt.
- **Rückfrage-Dialoge:** Ein Fakt wird gelernt, dazu ein zweiter Fakt über dessen Antwort.
  Dann kommt die Frage, danach eine Rückfrage mit Pronomen. Dev nutzt die Fakten-Indizes 0–4,
  Test die Indizes 5–9.
- **Manifest** (`python -m experiments.chat_v2_data`):
  - erzeugte Daten `6f31deb6c8a6b7b9b2a0a58cf761dcfeaffe4e871e35adb0c6b79de6db252f64`
  - Vorlagen `1d8fcf0d82c6626c52d89a984af7290c587189cd6806b09f87321b0fc1e7b0f7`
  - Fakten `6a67a1ae5afc4ba43ccb0baa10d051e5eb6b1510cb0c53e7422ecc4bd337961c`

## 4. Bewertung

- **Hit@1 (Satz):** Die Goldantwort steckt im besten Satz, wie in Stufe 1.
- **EM / F1 (kurze Antwort):** die offiziellen SQuAD-v1.1-Maße (Normalisierung, Maximum über
  die Goldantworten). Für NQ-open gilt dasselbe, üblich ist dort EM.
- **Richtig (Fakten, Dialoge):** Die normalisierte Goldantwort steht wortgenau in der
  normalisierten kurzen Antwort, und die kurze Antwort ist höchstens 3 Wörter länger als die
  Goldantwort.
- **Enthaltung:** Die kurze Antwort ist leer, das System sagt „I don't know“.
- **Präzision:** der Anteil richtiger unter den gegebenen Antworten.
- **Abdeckung:** der Anteil der Fragen, die überhaupt beantwortet werden.
- **Bootstrap:** 2.000 Replikate über Fragen bzw. Dialoge, Seed 42. Paarweise Differenzen
  werden gepaart gezogen.

## 5. Kriterien (Test)

| | Kriterium | Schwelle |
|---|---|---|
| **R1** Stufe 1.1 | SQuAD-Test2: Hit@1(v2) − Hit@1(Stufe 1, eingefroren) | ≥ 3 pp **und** KI-Untergrenze > 0 |
| **R2** Stufe 1.1 | NQ-Test: Hit@1(v2) − Hit@1(Stufe 1) | ≥ 2 pp **und** KI-Untergrenze > 0 |
| **F1** Stufe 2 | erfundene Fakten gelernt (Form A), Test-Frageform: richtig | ≥ 90 % |
| **F2** Stufe 2 | dieselben Fragen mit Tippfehler im Namen: richtig; **und** Vorsprung vor einem exakten Wörterbuch (gleiche Tripel, Schlüssel = exakter Name) | ≥ 75 % **und** ≥ 30 pp |
| **F3** Stufe 2 | dieselben 200 Fragen **vor** dem Lernen: Enthaltung | ≥ 90 % |
| **D1** Stufe 3 | Dialoge über dich: Fakten richtig zurückgegeben | ≥ 90 % |
| **D2** Stufe 3 | nach „vergiss“: Antwort enthält den Wert nicht (a); Gedächtnis-Digest bitgleich zum Kontrollskript (b) | je 100 % |
| **D3** Stufe 3 | Rückfrage mit Pronomen: richtig | ≥ 80 % |
| **A1** Stufe 4 | SQuAD-Test2: EM **und** F1 der kurzen Antwort | ≥ 20 % **und** ≥ 30 % |
| **A2** Stufe 4 | SQuAD-Test2 mit θ von Dev: Präzision (EM) bei Abdeckung | ≥ 50 % bei ≥ 20 % |
| **A3** Stufe 4 | NQ-Test: EM | ≥ 5 % |
| **U1** Stufe 5 | Ende-zu-Ende-Browsertest des Chats (Fragen, Quelle, Lernen im Chat, Rückfrage, Vergessen, „I don't know“) | besteht |
| **U2** Stufe 5 | Median-Zeit pro Chat-Runde (alle Test-Dialogrunden und SQuAD-Test2-Fragen) | ≤ 1 s (Container berichtet, M4 offiziell) |
| **U3** Stufe 5 | Determinismus: zwei Läufe der Test-Dialoge, einmal nach Neustart aus dem Log | Transkript-Digest identisch |

- **θ-Regel für A2:** θ ist der kleinste Wert, bei dem die Dev-Präzision (EM) ≥ 55 % ist. Die
  5 Punkte Abstand zur Testschwelle sind die Lehre aus E14/C3.
- **Stufe 1 eingefroren:** die Stufe-1-Engine mit α = 2, gleicher Satzindex.

**Ausgang:** Eine Stufe ist erfüllt, wenn alle ihre Kriterien erfüllt sind. Stufe 5 umfasst
U1–U3. Verfehlte Kriterien werden berichtet, nicht umgedeutet.

## 6. Ehrliche Erwartung

| | Erwartung | Begründung |
|---|---|---|
| R1 | ~60 % | Fragesätze und Antworttyp betreffen einen Teil der Fehler aus E14 |
| R2 | ~50 % | NQ-Fragen sind klein geschrieben und kurz, der Korpus ist klein |
| F1 | ~85 % | Der Name identifiziert den Fakt; die Antwortgrenze ist die Hürde |
| F2 | ~70 % | Trigramm-HDC toleriert einen Buchstaben; BPE-Suche kaum |
| F3 | ~70 % | Frageworte wie „capital“ finden immer irgendeinen Satz |
| D1 | ~75 % | Die Test-Formulierungen weichen stark ab („profession“ ↔ „work as“) |
| D2 | ~95 % (a), ~99 % (b) | Vergessen ist schon im LM exakt |
| D3 | ~70 % | |
| A1 | ~40 % | Regelbasierte Extraktion ohne Tagger |
| A2 | ~50 % | |
| A3 | ~35 % | NQ-open EM mit 285 M Tokens und ohne neuronales Lesen dürfte bei 3–7 % liegen |
| U1–U3 | je ~90 % | |

Zum Vergleich (nur Einordnung, nicht gemessen): neuronale Systeme erreichen auf NQ-open etwa
40–55 % EM, klassische BM25-Pipelines ohne neuronales Lesen deutlich unter 10 %.

## 7. Änderungsprotokoll

* v1.0 (2026-09-26): Erstregistrierung.
