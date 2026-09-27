# VORREGISTRIERUNG — ENGRAMM-Chat v7: sechste Runde der Stufen 1.1 bis 5

**Status: REGISTRIERT** am 2026-09-27, nach E19. Der Code war **vor** dieser Registrierung
eingefroren (Commit `2725824`; Konfiguration wie in v3–v6, θ = 6,9512). Nach der Registrierung
wird nichts mehr geändert; es folgt nur der eine Testlauf.

## 1. Anlass

E19 zeigte zwei Restprobleme:
- ein Verb als Wert („what I like to eat most“),
- zufällige Zuordnungen beim Vergessen ohne gemeinsame Kategorie.

v7 behebt das:
- **Werte:** Ein Wert beginnt nie mit einem Hinweis-Verb. „X is what/who …“ macht X zum Wert.
  „The name's X“ gilt als Name.
- **Vergessen per Punktesystem:**
  - Kategorien zählen 2, schwache Etiketten 0,5.
  - Werte-Art aus Allgemeinwissen: Automarken und Städte sind Namen, Speisen und Berufe
    gewöhnliche Wörter, Geburtstage Daten.
  - HDC-Typisierung des Werts über den gezählten Bedeutungsvektor, wo vorhanden.
- **Rückfallsuche** schließt Sätze über „deinen Bruder“ usw. anhand der Fakten aus.

Entwickelt nur an verbrauchten Daten (v2-Dev, v2- bis v6-Test).

## 2. Testdaten (neu, ungesehen, geschrieben nach dem Einfrieren des Codes)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test7 | 1.000 | Pool-Fragen der Test-Artikel, Positionen 5.000–5.999 in v2-Hash-Reihenfolge |
| NQ-Test7 | 3.610 | NQ-open `train`, Positionen 16.440–20.049 in SHAKE-256-Reihenfolge |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v7_templates.json`), Seed `test7`, Tippfehler aus SHAKE-256("v7:" + ID) |

Manifest (`python -m experiments.chat_v7_data`):
- erzeugte Daten `c1fe2ecbe14090308ee7965a3382d824c5e0fa3929ccca410f130cee5d76dd79`
- Vorlagen `7d57e9ffb3bf86ad324f659648b197c53b47df22ac4f6b0525afc68b57650bd9`

## 3. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test7`.

## 4. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1 erfüllt; R2 | ~45 % |
| F1–F3 | ~90 % |
| D1 | ~85 %; D2 ~50 %; D3 ~90 % |
| A1 | ~5 %; A2 ~45 %; A3 ~2 % |
| U1–U3 | ~95 % |

## 5. Änderungsprotokoll

* v1.0 (2026-09-27): Erstregistrierung.
