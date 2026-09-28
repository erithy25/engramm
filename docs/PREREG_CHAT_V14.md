# VORREGISTRIERUNG — ENGRAMM-Chat v14: Ensemble-Spannenmodell, Rückfragen verallgemeinert

**Status: REGISTRIERT** am 2026-09-28, nach E26. Der Code war **vor** dieser Registrierung
eingefroren (Commit `44c0bbc`). Danach wird nichts mehr geändert; es folgt genau ein Testlauf.

## 1. Anlass

E26 erfüllte A2 und A3. Zwei Kriterien waren verfehlt:
- **A1-F1** mit 29,4 %: Auf Test-Artikeln lag F1 im Mittel von Test12 und Test13 bei 30,0 %, also
  genau auf der Schwelle.
- **D3** mit 63,6 %: „that one“ wurde auf das Fragethema statt auf die letzte Antwort aufgelöst.

## 2. Änderungen (Entwicklung auf verbrauchten Daten: Test12, Test13, Dev12, Trainingsartikel)

1. **Rückfragen:** „this/that one“ und „the latter“ zeigen auf die letzte Antwort. Weitere Nomen
   wurden aufgenommen („this guy“, „said person“, „that individual“, Rollen wie „that author“,
   Orte wie „that village“).
   - Stresstest mit 30 Formulierungen auf test11–test13: alle 100 % (vorher vier bei 0 %).
   - Commit `3bb0bc7`, vor dem Einfrieren.
2. **Spannenmodell = Mittel von 7 gezählten Perzeptrons** (`experiments/chat_v14_ensemble.py`).
   - Mitglieder: Absatz-Training (p2, p5, weiche Labels, zweiter Merkmalssatz, 12 Durchgänge) und
     Absatz- plus Kontext-Training auf den 10 besten Sätzen von 8.000 Trainingsfragen über chat4
     (β 1 und 0,5).
   - Alle Mitglieder wurden nur auf Trainingsartikeln trainiert.
   - `chat4/spanperc_ens7.json`, SHA-256
     `8e265ba99071c75595187727fcac7af93349d2ef917ccf465924acdca710f939`.
3. **Suchgewicht pcov 2 → 4**, nur für Fragen in Frageform. Gesucht auf Test12, geprüft auf Test13.
   Suchbox-Fragen (NQ) behalten die bisherigen Gewichte.
4. **Konfidenzmodell** mit demselben Verfahren neu trainiert (`chat4/confperc14.json`), auf
   verbrauchten Fragen v2–v11 und Dev12.
5. **θ** nach der Regel auf Test12 + Test13 (10.000 Fragen, verbraucht, nicht im Training des
   Konfidenzmodells): **−5,0005**.

**Dev-Werte (verbraucht, voller Bot):**

| | EM | F1 | A2 bei θ |
|---|---|---|---|
| Test12 + Test13 (v14) | 22,7 % | 30,66 % | 55,0 % bei 22,3 % |
| davon Test12 / Test13 | — | 31,16 % / 30,16 % | 55,4 % bei 22,2 % / 54,6 % bei 22,4 % |
| dieselben Fragen mit v13 | 21,9 % | 30,03 % | — |
| NQ-Dev | 5,65 % | — | — |

**Erprobt ohne Gewinn:**
- ein gezählter Zweitstufen-Ranker über die 13 Suchmerkmale (Hit@1 45,1 % gegen 45,3 %);
- Kontext-Training allein (Test12 −0,3, Test13 +0,2);
- Gewichtssuche allein (+0,2 auf Test13).

## 3. Testdaten (neu, ungesehen)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test14 | 5.000 | Pool v3, Test-Artikel, Positionen 10.000–14.999 in v2-Hash-Reihenfolge |
| NQ-Test14 | 3.610 | NQ-open `train`, Positionen 41.710–45.319 |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v14_templates.json`, geschrieben nach dem Einfrieren), Seed `test14` |

Manifest (`experiments/chat_v14_data.manifest()`):
- erzeugte Daten `7cf7fc48c726b88cb0b844f91fcd4daf17406abcc752a4fbeab5e73ac289772a`
- Vorlagen `e84ac045b414d6599e6c355b1ec3f5ed08227649328b2d696ce9ee661ceb2832`

## 4. Vorbehalte

- Wie in v12 und v13 wurden die Test-Absätze gelesen (Pool-Bedingung). R1 ist daher trivial.
- Test14 stammt aus denselben 235 Test-Artikeln wie Test12 und Test13, aber aus anderen Fragen.
  pcov und θ wurden auf Test12 und Test13 bestimmt. Trainiert wurde auf keinem Test-Artikel.
- Die Platte der Umgebung ist voll. Der Browser-Test (U1) läuft deshalb mit `TMPDIR` im RAM
  (`/dev/shm`). Am Test selbst ändert das nichts.

## 5. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test14`; U1 mit `tests/test_chat_ui.py`.

## 6. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1, R2, U1–U3 | je ~95 % |
| F1–F3, D1–D3 | je ~90 % |
| A1 | ~80 % (F1 30,7 ± ~0,6 auf dieser Verteilung) |
| A2 | ~80 % |
| A3 | ~70 % |

Alle Kriterien zugleich: ~40 %.

## 7. Änderungsprotokoll

* v1.0 (2026-09-28): Erstregistrierung.
