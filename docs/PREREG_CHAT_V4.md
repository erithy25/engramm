# VORREGISTRIERUNG — ENGRAMM-Chat v4: dritte Runde der Stufen 1.1 bis 5

**Status: REGISTRIERT** am 2026-09-27, nach E16. Der Code war **vor** dieser Registrierung
eingefroren (Commit `c4a3c29`, Konfiguration `engramm/chat/config.py` unverändert seit v3,
θ = 6,9512). Nach der Registrierung wird nichts mehr geändert; es folgt nur der eine Testlauf.

## 1. Anlass

Nach E16 wurden drei Fehler behoben, die die Analyse aufgedeckt hatte:
- „living“ stand fälschlich in der Wohn-Gruppe.
- „birthplace“ fehlte in der Geburts-Gruppe.
- Es fehlten die Oberbegriffe `#job`/`#employer` ⊂ `#work`; dazu gilt die Ein-Fakt-Regel jetzt
  auch ohne erkannten Antworttyp.

Die Korrekturen wurden an verbrauchten Daten entwickelt (v2-Dev, v2-Test, v3-Test). Ob sie
verallgemeinern, zeigt nur ein Test mit **frischen** Formulierungen.

## 2. Testdaten (neu, ungesehen, geschrieben nach dem Einfrieren des Codes)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test4 | 1.000 | Pool-Fragen der Test-Artikel, Positionen 2.000–2.999 in v2-Hash-Reihenfolge |
| NQ-Test4 | 3.610 | NQ-open `train`, Positionen 5.610–9.219 in SHAKE-256-Reihenfolge |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v4_templates.json`), Seed `test4`, Tippfehler aus SHAKE-256("v4:" + ID) |

Manifest (`python -m experiments.chat_v4_data`):
- erzeugte Daten `49346e20e01d1bb5ddf94b55b98569d58bd13fd4cb0e495de247f4bf934afb2d`
- Vorlagen `f53ecea1914807ae6659688346d625ae15a3baaca8ee2b8e38d1b30d65678646`

## 3. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen wird mit
`python -m experiments.chat_v2_eval --split test4`.

## 4. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1 | erfüllt; R2 ~40 % (schwankt um 2 pp) |
| F1–F3 | ~85 % |
| D1 | ~80 %; D2 ~60 % (100 % auf ungesehenen Formulierungen verlangt eine lückenlose Grammatik); D3 ~80 % |
| A1 | EM ~50 %, F1 < 30 % fast sicher → A1 ~5 % |
| A2 | ~50 % |
| A3 | ~2 % |
| U1–U3 | ~95 % |

## 5. Änderungsprotokoll

* v1.0 (2026-09-27): Erstregistrierung.
