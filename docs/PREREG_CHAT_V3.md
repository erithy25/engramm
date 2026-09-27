# VORREGISTRIERUNG — ENGRAMM-Chat v3: zweite Runde der Stufen 1.1 bis 5

**Status: REGISTRIERT** am 2026-09-27, nach der v2-Testmessung (E15) und **vor** jeder
Code-Änderung für v3. Testdaten sind mit diesem Dokument eingefroren
(`experiments/chat_v3_data.py`, `data/chat_v3_templates.json`, Manifest in §3).

## 1. Anlass

E15: Stufen 1.1, 2 und 5 erfüllt, Stufen 3 (Vergessen, D2) und 4 (kurze Antworten) verfehlt.
Die Ursache von D2 ist bekannt: Aussagen über „meinen Bruder“ und „meinen Hund“ wurden als
Beziehungen von *dir* gespeichert, fast gleich wie dein Name. v3 behebt das und verbessert
Stufe 4. Gemessen wird wieder **alles**, auf neuen Daten und mit **unveränderten Schwellen** aus
`PREREG_CHAT_V2.md` §5.

## 2. Entwicklungsregel

- Für die Entwicklung erlaubt sind alle Daten von v2, also Dev **und** die verbrauchten
  v2-Testdaten, dazu die Zählquelle aus v2 v1.1.
- Die v3-Testdaten werden erst im Testlauf gelesen, **einmal**.
- Neustart nur nach Absturz, dokumentiert. Keine Änderung der Schwellen.

## 3. Testdaten (neu, ungesehen)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test3 | 1.000 | die nächsten 1.000 Pool-Fragen der Test-Artikel in v2-Hash-Reihenfolge (v2 nahm die ersten 1.000) |
| NQ-Test3 | 3.610 | NQ-open `train`, Positionen 2.000–5.609 in SHAKE-256-Reihenfolge (v2-Dev: 0–1.999) |
| Erfundene Fakten | 200 (+ Tippfehler) | neue Frageformen; Tippfehler-Stelle aus SHAKE-256("v3:" + ID) |
| Dialoge über dich | 200 | neue Formulierungen für Erzählen, Fragen und Vergessen; neue Namen und Werte (Seed `test3`) |
| Rückfrage-Dialoge | 55 | neue Frage- und Rückfrageformen |

Manifest (`python -m experiments.chat_v3_data`):
- erzeugte Daten `8c0fbfa859f00905df377657c4ed05dfc00441d047497178434732e7f734b2ab`
- Vorlagen `5e038a5a009911f18229f8aeef8059e0afa8276f56048e1cbdf762168a7b8af9`

## 4. Kriterien

Identisch mit `PREREG_CHAT_V2.md` §5: R1, R2, F1–F3, D1–D3, A1–A3, U1–U3, gleiche Schwellen,
gleiche θ-Regel, gleiche Bewertung und derselbe Bootstrap. Der Vergleich in R1/R2 erfolgt wieder
gegen die eingefrorene Stufe 1.

## 5. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1, R2 | wie v2 (R2 bleibt knapp) |
| F1–F3 | ~80 % (neue Frageformen können wie in v2 an Umschreibungen scheitern) |
| D1 | ~85 % (neue Formulierungen) |
| D2 | ~80 % (die Strukturkorrektur trifft die bekannte Ursache; neue Formulierungen bleiben ein Risiko) |
| D3 | ~75 % |
| A1 | EM ~50 %, F1 ≥ 30 % unwahrscheinlich (~10 %) |
| A2 | ~40 % |
| A3 | ~3 % (NQ-EM ≥ 5 % ist mit diesem Korpus kaum erreichbar) |
| U1–U3 | ~95 % |

## 6. Änderungsprotokoll

* v1.0 (2026-09-27): Erstregistrierung.
