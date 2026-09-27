# VORREGISTRIERUNG — ENGRAMM-Chat v8: siebte Runde der Stufen 1.1 bis 5

**Status: REGISTRIERT** am 2026-09-27, nach E20. Der Code war **vor** dieser Registrierung
eingefroren (Commit `2c4fb57`). Nach der Registrierung wird nichts mehr geändert; es folgt nur
der eine Testlauf.

## 1. Anlass

E20 zeigte, dass handgeschriebene Regeln neue Formulierungen nicht verallgemeinern (D1 frisch
38–93 %) und dass die Spannenwahl für A1-F1 ≥ 30 % nicht reicht. v8 ändert:

**Stufe 3 (Dialog):**
- **Gezähltes Wertelexikon** (`engramm/chat/lexicon.py`): Die Kategorie eines Worts (Speise,
  Farbe, Auto, Beruf; zur Erkennung zusätzlich Wohnort, Geburtstag, Name, Arbeitgeber) ergibt
  sich aus seiner Satz-Kookkurrenz mit Ankerwörtern im Korpus (Lift).
- **Punktesystem** für Fragen über dich: geteilte Kategorie 2, schwächere Gruppe 0,5,
  gezählte weiche Kategorie 1, geteiltes Wort 0,5, HDC-Nähe, Werteart. Ein Fakt mit
  widersprechender Kategorie scheidet aus.
- Breitere Erkennung von Vergessen-Bitten („Stop remembering …“, „Never mind X, forget it“).
- Herkunft (`#origin`) für „Where is she from?“.

**Stufe 4 (kurze Antwort):**
- **Gemitteltes Perzeptron** statt Naive Bayes für die Spannenwahl. Es wird nur durch
  Korrektur-Zählen trainiert, auf ganzen SQuAD-Absätzen von Nicht-Test- und
  Nicht-Dev-Artikeln (`experiments/chat_v2_perceptron.py --paragraph --passes 8`).
  - Datei `spanperc_p2.json`, SHA-256 `b882f8f82845c0b623a51586dc916018f4f74660d323e424771ec5cbbde451ee`.
- Eine gemeinsame Softmax über alle 10 Sätze (Satz-Prior β = 1).
- Konfidenz = Stimmenanteil³ × Satzwert.
- θ nach der registrierten Regel auf 3.000 verbrauchten Dev-Fragen: **6,6824**
  (Abdeckung 22,6 % bei 55,0 % Präzision).

**Entwicklung (nur verbrauchte Daten):**
- v2-Dev und v2- bis v7-Test.
- Zwei eigene Paraphrasen-Mengen, `dev8` und `dev9` (je 400 Dialoge).

**Ehrliche Schätzung:** `dev9` wurde nach dem Stufe-3-Umbau geschrieben und einmal gemessen,
bevor daran etwas geändert wurde. Ergebnis: D1 67,75 %, D2a 93,5 %, D2b 82,75 %, D3 79,1 %.
Danach lag `dev9` bei 100 %, zählt aber als verbraucht.

## 2. Testdaten (neu, ungesehen, geschrieben nach dem Einfrieren des Codes)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test8 | 1.000 | Pool-Fragen der Test-Artikel, Positionen 6.000–6.999 in v2-Hash-Reihenfolge |
| NQ-Test8 | 3.610 | NQ-open `train`, Positionen 20.050–23.659 in SHAKE-256-Reihenfolge |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v8_templates.json`), Seed `test8`, Tippfehler aus SHAKE-256("v8:" + ID) |

Das Perzeptron-Training nutzt nur SQuAD-Train-Artikel (Titel-Bit 0, ohne Dev-Artikel). Die
NQ-Positionen 40.000–47.999 wurden abgerufen, fließen aber nicht in das eingefrorene Modell ein.

Manifest (`python -m experiments.chat_v8_data`):
- erzeugte Daten `440cf0ea0491d2699badd991a8a3c0f368d34aa956a43b4987ee48255a025efe`
- Vorlagen `23e85dbbd81a4aefbb4ff9b0569427e66c39cf8f15e1f7345130efb3e2a84508`

## 3. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test8`.

## 4. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1 erfüllt; R2 | ~50 % |
| F1–F3 | ~90 % |
| D1 | ~75 %; D2 ~75 %; D3 ~85 % |
| A1 | ~50 % (Dev-F1 30,9, knapp über 30); A2 ~50 %; A3 ~1 % (Dev-EM 2,4 %) |
| U1–U3 | ~95 % |

## 5. Änderungsprotokoll

* v1.0 (2026-09-27): Erstregistrierung.
