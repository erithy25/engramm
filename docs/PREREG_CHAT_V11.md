# VORREGISTRIERUNG — ENGRAMM-Chat v11: Wiederholung von v10 auf größerer Stichprobe

**Status: REGISTRIERT** am 2026-09-28, nach E23. Das System ist **unverändert** gegenüber v10
(Code-Stand `2abf2b1`: Index `chat3`, θ = 9,2123, alle Parameter wie in PREREG_CHAT_V10).
Hinzu kommen nur das Testdaten-Modul `experiments/chat_v11_data.py` und diese Registrierung.
Es folgt genau ein Testlauf.

## 1. Anlass

In E23 war A3 erfüllt. A1 und A2 fielen auf einer kleinen, schwierigen Stichprobe von 521 Fragen
knapp unter die Schwelle, während das Mittel auf 9.000 verbrauchten Fragen über der Schwelle
liegt. Eine Wiederholung auf einer größeren Stichprobe misst dasselbe System genauer.

## 2. Testdaten

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test11 | 4.956 | alle übrigen Fragen des Dev-Artikel-Pools, Positionen 2.000+ in v2-Hash-Reihenfolge |
| NQ-Test11 | 3.610 | NQ-open `train`, Positionen 30.880–34.489 in SHAKE-256-Reihenfolge |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v11_templates.json`), Seed `test11` |

**Offene Einschränkung für SQuAD:** Der Pool der Test-Artikel ist verbraucht (v2–v10). Eine neue
Pool-Prüfung gegen die gelesenen Wikipedia-Texte (`experiments/chat_pool_v2.py`) ergab nur
175 Fragen.
- Die v11-Fragen selbst wurden nie gesehen.
- Sie stammen aber aus den **46 Dev-Artikeln**. Andere Fragen dieser Artikel (SQuAD-Dev2,
  2.000 Stück) dienten der Entwicklung: Suchgewichte und θ wurden unter anderem an ihnen
  bestimmt.
- Auf Dev lag SQuAD etwas höher als auf den Test-Artikeln (EM ~25 % gegen ~23,6 %). Ein Teil
  davon kann an den Artikeln liegen.
- Der Spannen-Perzeptron wurde auf keinem Dev- oder Test-Artikel trainiert.

Diese Stichprobe ist daher **weniger unabhängig** als die bisherigen. Das Ergebnis wird mit
diesem Vorbehalt berichtet.

Manifest (`python -m experiments.chat_v11_data`):
- erzeugte Daten `805fab94cd18bdf33a7399b37736c7333d3b760503876b6c161b5ffdfa71ec90`
- Vorlagen `a234b8b900ed8c3d81349c4df373227027d229cc50a64c40ed8a0f1c801f44ad`

## 3. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test11`.

## 4. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1, R2 | je ~95 % |
| F1–F3 | ~90 % |
| D1–D3 | je ~80 % |
| A1 | ~75 % |
| A2 | ~70 % |
| A3 | ~85 % |
| U1–U3 | ~95 % |

## 5. Änderungsprotokoll

* v1.0 (2026-09-28): Erstregistrierung.
