# VORREGISTRIERUNG — ENGRAMM-Chat v6: fünfte Runde der Stufen 1.1 bis 5

**Status: REGISTRIERT** am 2026-09-27, nach E18. Der Code war **vor** dieser Registrierung
eingefroren (Commit `e5fd108`; Konfiguration wie in v3–v5, θ = 6,9512). Nach der Registrierung
wird nichts mehr geändert; es folgt nur der eine Testlauf.

## 1. Anlass

E18: Die Zerlegung ohne Satzmuster hob D1 auf frischen Formulierungen auf 68 %. v6 ergänzt:
- **Nachschlagen in den eigenen Sätzen:** Findet das Faktengedächtnis zu einer Frage über dich
  nichts Sicheres, sucht ENGRAMM den passenden eigenen Satz (Wörter, Begriffsgruppen, keine
  Kategorie-Konflikte) und schneidet die Antwort heraus.
- **Kategoriewörter:** colour, food, job … gehören zur Beziehung, nicht zum Wert.
- **Nicht-Werte:** „favourite“ oder „best“ sind nie ein Wert.
- **Satzanfänge mit Präposition** („At work …“) zählen nur mit „?“ als Frage.

Entwickelt wurde nur an verbrauchten Daten (v2-Dev, v2- bis v5-Test).

## 2. Testdaten (neu, ungesehen, geschrieben nach dem Einfrieren des Codes)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test6 | 1.000 | Pool-Fragen der Test-Artikel, Positionen 4.000–4.999 in v2-Hash-Reihenfolge |
| NQ-Test6 | 3.610 | NQ-open `train`, Positionen 12.830–16.439 in SHAKE-256-Reihenfolge |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v6_templates.json`), Seed `test6`, Tippfehler aus SHAKE-256("v6:" + ID) |

Manifest (`python -m experiments.chat_v6_data`):
- erzeugte Daten `24982544a638c13f815c1d0d60658e6b52980ab297b17c67c1f3a7cc885df6e3`
- Vorlagen `fe42816a7832582b16f67a050ae7ffb91836bb64d1a91bf6a21b91f56b366e11`

## 3. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test6`.

## 4. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1 erfüllt; R2 | ~40 % |
| F1–F3 | ~90 % |
| D1 | ~85 %; D2 ~50 % (verlangt 100 %); D3 ~85 % |
| A1 | ~5 %; A2 ~45 %; A3 ~2 % |
| U1–U3 | ~95 % |

## 5. Änderungsprotokoll

* v1.0 (2026-09-27): Erstregistrierung.
