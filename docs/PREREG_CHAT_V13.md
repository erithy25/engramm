# VORREGISTRIERUNG — ENGRAMM-Chat v13: gezählte Konfidenz, θ aus der Testverteilung

**Status: REGISTRIERT** am 2026-09-28, nach E25. Der Code war **vor** dieser Registrierung
eingefroren (Commit `08de49c`). Danach wird nichts mehr geändert; es folgt genau ein Testlauf.

## 1. Anlass

E25 erfüllte alles außer A2. Die Präzision lag bei 57,8 %, die Abdeckung aber nur bei 18,2 % statt
≥ 20 %. θ stammte aus Dev12 (Dev-Artikel). Auf den Test-Artikeln ist die Konfidenz niedriger. Und
selbst mit einem θ aus Test12 hätte die alte Konfidenz bei 55 % Präzision nur 20,8 % Abdeckung erlaubt.

## 2. Änderungen

1. **Gezählte Konfidenz** (`engramm/chat/calib.py`). Ein gemittelter Perzeptron über gestufte
   Merkmale der Antwort:
   - Stimmenanteil und Zahl der besten Sätze, die die Antwort enthalten;
   - bester Satzwert, Antworttyp, Länge und Form;
   - wie viel der Frage der **Antwortsatz** abdeckt (Wörter, Phrasen, Dokument, Vorsatz, Titel) und
     sein Rang.

   Trainiert nur durch gezählte Korrekturen auf verbrauchten Daten: 13.477 SQuAD-Testfragen aus
   v2–v11 und Dev12, zusammen 16.561 Antworten (`experiments/chat_v13_calib.py`). Das ergibt
   296 Gewichte in `chat4/confperc.json`, SHA-256
   `d1873bb5d2850ca581506d823022be1772dc61fe8210fbb0978c9fa60f8b5444`. Suchbox-Fragen (NQ) behalten
   die alte Konfidenz.
2. **θ** nach der Regel (kleinstes θ mit Dev-Präzision ≥ 55 %). Dev ist diesmal der verbrauchte
   **Test12**: 5.000 Fragen aus neu gelesenen Absätzen der Test-Artikel, also die Verteilung von Test13.
   - Test12 war nicht im Training des Konfidenzmodells.
   - Ergebnis: **θ = −5,7467**, bei 23,0 % Abdeckung (die alte Konfidenz kam auf 20,8 %).
3. **Tempo.** Eine Suche im Satz→Dokument-Feld kopierte bei jedem Aufruf 30 M Einträge wegen eines
   Datentyps. Dazu wurde die Byte-Tabelle des Tokenizers ständig neu berechnet.
   - Beides ist behoben: 1,17 s → 0,33 s pro Frage.
   - Die Antworten sind identisch: Test12-Hit@1, EM und F1 stimmen mit E25 überein.

Alles andere ist unverändert gegenüber v12: Index chat4, Suchgewichte, Spannenwahl, NQ-Pfad und
Faktengedächtnis.

## 3. Testdaten (neu, ungesehen)

| Satz | Umfang | Regel |
|---|---|---|
| SQuAD-Test13 | 5.000 | Pool v3, Test-Artikel, Positionen 5.000–9.999 in v2-Hash-Reihenfolge (0–4.999 = Test12) |
| NQ-Test13 | 3.610 | NQ-open `train`, Positionen 38.100–41.709 |
| Fakten, Dialoge, Rückfragen | 200 / 200 / 55 | neue Formulierungen (`data/chat_v13_templates.json`, geschrieben nach dem Einfrieren), Seed `test13` |

Manifest (`experiments/chat_v13_data.manifest()`):
- erzeugte Daten `8d6a1f7db163202282b63cc08cfc25aa8370f7c75edef6ff049e3cfd5228bb59`
- Vorlagen `23e3e9dc538e8af9cb33767b5de63808cb29e6acd66272f35ee3a265e5694b9d`

## 4. Vorbehalte

- Wie in v12 wurden die Test-Absätze gelesen (Pool-Bedingung). R1 vergleicht mit Stufe 1 auf deren
  Korpus ohne diese Absätze und ist deshalb trivial.
- θ wurde an 5.000 Fragen derselben Verteilung bestimmt. Die Abdeckung auf Test13 streut um
  etwa ±1 pp.

## 5. Kriterien und Ausgang

Unverändert aus `PREREG_CHAT_V2.md` §5 und §4. Gemessen mit
`python -m experiments.chat_v2_eval --split test13`; U1 mit `tests/test_chat_ui.py`.

## 6. Ehrliche Erwartung

| | Erwartung |
|---|---|
| R1, R2, U1–U3 | je ~95 % (U2 ~0,3 s) |
| F1–F3, D1–D3 | je ~90 % |
| A1 | ~70 % (Test12: F1 30,6 %) |
| A2 | ~80 % (Test12 mit θ: 55,0 % bei 23,0 %) |
| A3 | ~65 % (v11 6,0 %, v12 5,2 %) |

Alle Kriterien zugleich: ~35 %.

## 7. Änderungsprotokoll

* v1.0 (2026-09-28): Erstregistrierung.
