# VORREGISTRIERUNG — ENGRAMM-Chat v5: vierte Runde der Stufen 1.1 bis 5

**Status: REGISTRIERT** am 2026-09-27, nach E17. Der Code war **vor** dieser Registrierung
eingefroren (Commit `70b7646`; `engramm/chat/config.py` wie in v3/v4, θ = 6,9512). Nach der
Registrierung wird nichts mehr geändert; es folgt nur der eine Testlauf.

## 1. Anlass

E17 zeigte: Die Ich-Grammatik aus Satzmustern verallgemeinert nicht (D1 38 % auf frischen
Formulierungen). v5 ersetzt sie durch eine Zerlegung ohne Satzmuster:
- **Wert** = die genannte Angabe.
- **Beziehung** = die übrigen Inhaltswörter und Begriffsgruppen.
- **Besitz** aus „my …“ und „I have a …“.
- Dazu eine Kategorie-Konfliktregel, und „tell/show/give me“ gilt nicht als Frage über dich.

Entwickelt wurde nur an verbrauchten Daten (v2-Dev, v2-Test, v3-Test, v4-Test).

## 2. Testdaten (neu, ungesehen, geschrieben nach dem Einfrieren des Codes)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test5 | 1.000 | Pool-Fragen der Test-Artikel, Positionen 3.000–3.999 in v2-Hash-Reihenfolge |
| NQ-Test5 | 3.610 | NQ-open `train`, Positionen 9.220–12.829 in SHAKE-256-Reihenfolge |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v5_templates.json`), Seed `test5`, Tippfehler aus SHAKE-256("v5:" + ID) |

Manifest (`python -m experiments.chat_v5_data`):
- erzeugte Daten `52d73f6c53a127fcd09980a96d4e38eeec4e454128cb17b86114f6756f7be9e3`
- Vorlagen `1b03936185d44d681aea8fd7ff31ab77ac0ecc3807e8d20ba675e980ee410ccb`

## 3. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test5`.

## 4. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1 erfüllt; R2 | ~40 % |
| F1–F3 | ~85 % |
| D1 | ~80 %; D2 ~50 % (verlangt 100 %); D3 ~85 % |
| A1 | ~5 % (F1 < 30 %) |
| A2 | ~50 % |
| A3 | ~2 % |
| U1–U3 | ~95 % |

## 5. Änderungsprotokoll

* v1.0 (2026-09-27): Erstregistrierung.
