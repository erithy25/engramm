# VORREGISTRIERUNG — ENGRAMM-Chat v10: neunte Runde der Stufen 1.1 bis 5

**Status: REGISTRIERT** am 2026-09-28, nach E22. Der Code war **vor** dieser Registrierung
eingefroren (Commit `2abf2b1`). Nach der Registrierung wird nichts mehr geändert; es folgt nur
der eine Testlauf.

## 1. Anlass

E22 erfüllte alle Kriterien außer A3 (NQ-EM 3,4 % statt 5 %). Die Ursache ist der Korpus: Bei
NQ stand die Antwort nur für 12,7 % der Fragen unter den 10 besten Sätzen. v10 lässt ENGRAMM
deshalb **mehr lesen**.

**Wikipedia-Lesekorpus** (`experiments/chat_wiki_build.py`):
- Quelle: englische Wikipedia vom 2023-11-01 (`wikimedia/wikipedia`, 41 Parquet-Dateien).
- Auswahl nur nach dem Artikel selbst, nie nach einer Frage: jeder Artikel mit ≥ 7.000 Zeichen
  steuert seine ersten 2.000 Zeichen bei (am letzten Satzende gekürzt).
- Titel, die der Korpus aus WikiText schon hat, werden nicht erneut gelesen (14.354).
- Ergebnis: 614.464 Artikelanfänge, 262 M Tokens. Der Satzindex `chat3` deckt jetzt
  547 M Tokens ab (29,9 M Sätze).
- `chat3/info.json` SHA-256 `f7eadd450410bf8050c63536254a0967a750ef0b07a1b5d584bc1d152cbf971e`.

**Weitere Änderungen:**
- **Suchgewichte** neu abgestimmt, gleiche Koordinatensuche auf den Dev-Splits über `chat3`:
  cov 5, pcov 2, kcov 4, type 1, wiki 1, q 1, short 0,5, phr 4, dfull 4.
- **Suchanfragen** (Kleinschreibung, kein „?“) lesen die 20 besten Sätze statt 10. Datumsfragen
  laufen dort ebenfalls über das Perzeptron.
- **Pronomen** dürfen auf die zuletzt gezeigte beste Vermutung zeigen, nicht nur auf eine sichere
  Antwort.
- **θ** nach der Regel auf denselben 9.000 verbrauchten SQuAD-Fragen: **9,2123**
  (Abdeckung 20,9 %).

**Dev-Werte (verbraucht):**

| | Hit@1 | EM | F1 |
|---|---|---|---|
| SQuAD, 9.000 verbrauchte Fragen | 47,7 % | 23,6 % | 30,6 % |
| NQ-Dev | 7,25 % | 6,0 % | — |

**Stufe 1 (eingefrorener Vergleich):** Sie bleibt die Stufe-1-Engine auf ihrem alten Index
(`chat`, 285 M Tokens). R1 und R2 messen daher ab v10 **System plus mehr Lesestoff** gegen
Stufe 1, nicht mehr nur das Verfahren. v9 hatte R1 und R2 bereits auf dem gleichen Korpus
erfüllt (E22).

## 2. Testdaten (neu, ungesehen, geschrieben nach dem Einfrieren des Codes)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test10 | 1.000 | Pool-Fragen der Test-Artikel, Positionen 8.000–8.999 in v2-Hash-Reihenfolge |
| NQ-Test10 | 3.610 | NQ-open `train`, Positionen 27.270–30.879 in SHAKE-256-Reihenfolge |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v10_templates.json`), Seed `test10`, Tippfehler aus SHAKE-256("v10:" + ID) |

Manifest (`python -m experiments.chat_v10_data`):
- erzeugte Daten `0ee678c817dca23f5ebd37080bbdcbc12edf8c70098c7e8f3df829184d0437ef`
- Vorlagen `94b36d0c69b54a38c10357acb09d0d0087779e160c20128ce35d7d8cd966ce4b`

## 3. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test10`.

## 4. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1, R2 | je ~90 % |
| F1–F3 | ~90 % |
| D1–D3 | je ~80 % (neue Formulierungen) |
| A1 | ~65 % (F1 im Mittel 30,6) |
| A2 | ~65 % (Abdeckung knapp über 20 %) |
| A3 | ~85 % (Dev 6,0 %) |
| U1–U3 | ~95 % |

Alle Kriterien zugleich: ~30 %.

## 5. Änderungsprotokoll

* v1.0 (2026-09-28): Erstregistrierung.
* Nachtrag nach dem Lauf (keine Änderung am Lauf): SQuAD-Test10 hatte nur 521 Fragen
  (Pool-Ende bei Position 8.520), siehe E23.
