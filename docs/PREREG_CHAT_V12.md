# VORREGISTRIERUNG — ENGRAMM-Chat v12: SQuAD-Absätze lesen, Spannenwahl nach F1, neue Konfidenz

**Status: REGISTRIERT** am 2026-09-28, nach E24. Der Code war **vor** dieser Registrierung
eingefroren (Commit `9c2c482`). Nach der Registrierung wird nichts mehr geändert; es folgt genau ein
Testlauf.

## 1. Anlass

E24 erfüllte alles außer A1-F1 (29,95 % gegen 30 %). Zudem war der SQuAD-Pool nach v11 aufgebraucht,
in den Test- und in den Dev-Artikeln. Der Pool umfasst seit Stufe 1 die Fragen, deren Absatz ENGRAMM
gelesen hat (13-Token-Fenster, Abdeckung ≥ 80 %).

## 2. Änderungen (Entwicklung nur auf verbrauchten Daten und Dev12)

1. **Mehr lesen** (`experiments/chat_squad_read.py`). ENGRAMM liest jeden SQuAD-v1.1-Absatz
   (Wikipedia 2016), den es noch nicht gelesen hat.
   - Die Regel hängt nur vom Absatztext ab, nie von Frage oder Antwort: Abdeckung < 80 % in chat3.
   - Ergebnis: 17.555 von 20.958 Absätzen, 488 Artikel, 2,75 M Tokens.
   - SHA-256 der gelesenen Absätze: `c95a099c5d5794962b0189dbffb3f64ca52055b2db320cfc376a73eeebb56e4b`.
   - Die Absätze liegen als Segment `chat4` vor, das beim Laden an chat3 angehängt wird. Ein Test
     zeigt, dass das Ergebnis bitgleich zu einem Gesamtindex ist (`tests/test_chat_segment.py`).
2. **Wortzerlegung.** Initialen und Titel-Abkürzungen behalten ihren Punkt („St. John's“,
   „M. canetti“). Zahl-Bindestrich-Wörter bleiben ein Wort („2-to-3“, „19-year-old“).
3. **Auswahlfragen** („Is it X or Y?“, „…: X or Y?“): Antwort ist die Option, die die besten Sätze
   enthalten.
4. **Datumsfragen** laufen über das Perzeptron statt über die Regel.
5. **Spannenwahl nach erwartetem F1** (minimales Bayes-Risiko über die Stimmen, Temperatur 0,5).
6. **Konfidenz** = Anteil⁴ × √(bester Satzwert) × (1 + 0,2 × Anzahl der besten Sätze, die die
   Antwort als Kandidaten enthalten).
7. **θ** nach der Regel (kleinstes θ mit Dev-Präzision ≥ 55 %) auf **Dev12**: **3,6543**.

Unverändert bleiben die Suchgewichte, der Spannen-Perzeptron (`spanperc_p2.json`) und der ganze
NQ-Pfad.

**Dev12:** 3.084 Fragen der neu gelesenen Absätze der 42 Dev-Artikel, also dieselbe Verteilung wie
Test12. Der Perzeptron wurde nie auf diesen Artikeln trainiert.

**Dev-Werte (verbraucht):**

| | Hit@1 | EM | F1 | A2 |
|---|---|---|---|---|
| Dev12 (voller Bot) | 48,0 % | 24,7 % | 32,4 % | 55,0 % bei 23,6 % (θ-Menge selbst) |
| Alle verbrauchten Fragen (13.477, Extraktion) | — | 23,3 % | 30,9 % | — |
| davon Test-Artikel (8.521) | — | 23,4 % | 30,7 % | — |
| NQ-Dev (voller Bot, chat4) | 9,2 % | 5,65 % | — | — |

Zum Vergleich: dieselben 13.477 Fragen mit dem v11-System plus neuer Wortzerlegung ergeben 23,0 % EM
und 30,2 % F1.

## 3. Testdaten (neu, ungesehen)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test12 | 5.000 | Pool v3 (Fragen der neu gelesenen Absätze), Test-Artikel (Titel-Bit 1), Positionen 0–4.999 in v2-Hash-Reihenfolge (235 Artikel) |
| NQ-Test12 | 3.610 | NQ-open `train`, Positionen 34.490–38.099 in SHAKE-256-Reihenfolge |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v12_templates.json`, geschrieben nach dem Einfrieren), Seed `test12` |

Manifest (`python -m experiments.chat_v12_data`):
- erzeugte Daten `932096761aa8a4024fe6edc0a43eeda7155af066d35f6a9817aff9f20cb75363`
- Vorlagen `333ff06e60e4b331084b99137692423d90f3924bff342b97dc5cad257cc1866c`

## 4. Vorbehalte

- **Die Test-Absätze wurden gelesen.** Das ist genau die Pool-Bedingung seit Stufe 1: Eine Frage
  zählt nur, wenn ihr Absatz gelesen ist. Gelesen wurden alle ungelesenen SQuAD-Absätze nach einer
  reinen Textregel, ohne Blick auf Fragen oder Antworten.
- **R1** vergleicht mit Stufe 1 auf deren altem Korpus (285 M Tokens). Der enthält die Test12-Absätze
  nicht. R1 misst daher vor allem das Lesen und sagt über das Suchverfahren wenig. Es wird trotzdem
  berichtet. Auf gleichem Korpus war R1 in v9 erfüllt (E22).
- **θ stammt aus Dev12 (3.084 Fragen)**, einer kleineren Menge als in v9–v11, aber mit der
  Verteilung des Tests.

## 5. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test12`; U1 mit `tests/test_chat_ui.py`.

## 6. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1, R2 | je ~95 % |
| F1–F3, D1–D3 | je ~90 % |
| A1 | ~80 % (F1 auf Dev12 32,4, auf Test-Artikeln der verbrauchten Fragen 30,7) |
| A2 | ~75 % |
| A3 | ~75 % (Dev 5,65 %, v11-Test 6,0 %) |
| U1–U3 | ~95 % (U2 ~0,8 s) |

Alle Kriterien zugleich: ~45 %.

## 7. Änderungsprotokoll

* v1.0 (2026-09-28): Erstregistrierung.
