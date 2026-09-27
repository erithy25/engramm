# VORREGISTRIERUNG — ENGRAMM-Chat v9: achte Runde der Stufen 1.1 bis 5

**Status: REGISTRIERT** am 2026-09-27, nach E21. Der Code war **vor** dieser Registrierung
eingefroren (Commit `1aae5ad`). Nach der Registrierung wird nichts mehr geändert; es folgt nur
der eine Testlauf.

## 1. Anlass

E21 erfüllte die Stufen 2, 3 und 5 sowie A1. Verfehlt blieben:
- R2 (+1,63 pp statt 2 pp),
- A2 (48,1 % statt 50 % Präzision),
- A3 (NQ-EM 2,5 % statt 5 %).

v9 ändert nur Stufe 1.1 und Stufe 4. Der Dialogteil bleibt unverändert.

- **Bester Satz = Antwortsatz.** Der Satz, den ENGRAMM als besten zeigt, ist jetzt der Satz, aus
  dem die kurze Antwort stammt (vorher: der Satz mit dem höchsten Suchwert). Auf Dev:
  - NQ Hit@1: 4,65 % → 5,25 % (Stufe 1: 2,2 %),
  - SQuAD Hit@1: 47,1 % → 49,4 %.
- **Zweites Spannenmodell für Suchanfragen.** Fragen in Kleinschreibung ohne „?“ nutzen ein
  Perzeptron, das zusätzlich auf 40.000 abgerufenen NQ-open-Trainingsfragen trainiert ist
  (Positionen 40.000–79.999, disjunkt zu Dev 0–1.999 und allen Tests < 27.270).
  - Datei `spanperc_nq.json`, SHA-256 `f9843262edf8cdce6ccf14f9ff37c64431b0a1c90bfe7705ef1769eae6c72df4`.
  - Dev-NQ-EM 3,25 % (vorher 2,5 %).
  - SQuAD-Fragen nutzen weiter `spanperc_p2.json` (unverändert).
- **θ auf mehr verbrauchten Daten.** Gleiche Regel (kleinstes θ mit ≥ 55 % Präzision), aber auf
  allen 9.000 verbrauchten SQuAD-Fragen (Dev2, v2-Test, Test3–Test8) statt auf 3.000. Das
  verringert den Auswahlfehler der Regel: v8 fiel von 55 % auf Dev auf 48 % im Test.
  - Ergebnis: θ = **6,7847**, Abdeckung 22,2 %.
  - Auf diesen 9.000 Fragen: EM 23,9 %, F1 30,6 %.

## 2. Testdaten (neu, ungesehen, geschrieben nach dem Einfrieren des Codes)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test9 | 1.000 | Pool-Fragen der Test-Artikel, Positionen 7.000–7.999 in v2-Hash-Reihenfolge |
| NQ-Test9 | 3.610 | NQ-open `train`, Positionen 23.660–27.269 in SHAKE-256-Reihenfolge |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v9_templates.json`), Seed `test9`, Tippfehler aus SHAKE-256("v9:" + ID) |

Manifest (`python -m experiments.chat_v9_data`):
- erzeugte Daten `f3e0e696bf6550d714d73637e5a052371b0a6053a48cf60261c7f09e30def42d`
- Vorlagen `4290229f2e63b6dee141286e142d2362da567cc78afce5d88fb7c1be7c9e6f91`

## 3. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test9`.

## 4. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1 | ~95 % |
| R2 | ~60 % |
| F1–F3 | ~90 % |
| D1–D3 | je ~80 % (neue Formulierungen) |
| A1 | ~55 % (F1 knapp über 30) |
| A2 | ~50 % |
| A3 | ~2 % (Dev-EM 3,25 %; 5 % liegt außerhalb dessen, was der Korpus hergibt) |
| U1–U3 | ~95 % |

## 5. Änderungsprotokoll

* v1.0 (2026-09-27): Erstregistrierung.
