# Vorab-Registrierung: Sela-2 (festgelegt am 17. Oktober 2026, vor dem GPU-Lauf)

Gilt für den ersten Sela-2-Lauf nach `docs/SELA2_ANLEITUNG.md`. Rezept und Budget stehen in PLAN §12. Nach dem Lauf
werden diese Kriterien nicht mehr geändert. Neue Messungen dürfen dazukommen, sind dann aber als nachträglich zu
kennzeichnen.

## 1. Was gemessen wird

| Nr. | Messung | Wo | Wie |
|---|---|---|---|
| M1 | Bits pro Byte je Quelle (FineWeb-Edu, DCLM, C4, Cosmopedia, Wikipedia EN/DE, PG-19, FineWeb2-DE) | Pod, `results/sela2/eval_{base,chat}.json` | je bis zu 600 zurückgehaltene Dokumente (Basis: 300) aus Dateien, die nie Trainingsteile waren; Fenster 2 048, Schritt 1 024 |
| M2 | Bits pro Byte auf den Prüfdokumenten der LM-Studie (val-A, Test, WikiText-103-Test) | Pod | dieselben Dokumente wie bei GPT-2 small (1,036) und Sela-1 (0,989); C4/WikiText sind für Sela-2 fremdere Daten, der Wert ist eine Vergleichsgröße, kein Ziel |
| M3 | Zero-Shot HellaSwag, PIQA, ARC-E, ARC-C, WinoGrande, OBQA, LAMBADA, MMLU (Lückentext) | GitHub Actions, Messcode von `experiments/sela1_bench.py` (erweitert) | gleiche Messung für Sela-2-Basis, Sela-2-Chat, Sela-1, GPT-2 small, GPT-2 medium, Pythia-160M/410M |
| M4 | Antwort-Verlust auf zurückgehaltenen Gesprächen (Chat EN/DE, Quellen-QA) | Pod | Verlust nur auf Assistenten-Token |
| M5 | 100 feste Prompts (60 EN / 40 DE): Begrüßung, Identität, Anleitung, Umschreiben, Zusammenfassen, Quellen-QA, mehrere Züge | GitHub Actions, NumPy-Modell wie in der App | automatisch gezählt: Stopp vor dem Token-Limit, Schleifen (4-Gramm 3×), Rollen-Leck (`user`/`assistant`-Zeilen im Text), Median-Antwortlänge |
| M6 | IFEval (541 Prompts, prompt-level loose) | GitHub Actions | Chat-Modell und Basismodell |
| M7 | Quellen-QA: SQuAD-v2-dev mit Orakel-Kontext | GitHub Actions | HasAns-F1 und NoAns-Treffer **getrennt**; Antwort-Spanne vor dem ersten [n] |
| M8 | ENGRAMM + Sela-2 Ende-zu-Ende auf frischen Fragen | App-Server auf dem CPU-Rechner | Abdeckung = Anteil der Wissensfragen mit angezeigter geprüfter Sela-2-Antwort; Richtigkeit auf diesem Anteil gegen ENGRAMM auf denselben Fragen; angezeigte Zahlen und Namen ohne Quelle |
| M9 | Blindvergleich durch den Auftraggeber | ChatBench-Seite | 40 Prompts: Sela-2 gegen SmolLM2-135M-Instruct und gegen ENGRAMM allein |
| M10 | int8 gegen fp32 | CPU | Unterschied in Bits pro Byte auf M1 |

## 2. Erfolgskriterien

**Stufe „GPT-3-Small-Niveau“ (Basismodell)**
- Der gepoolte Zero-Shot-Wert erfüllt beides:
  - er liegt über GPT-2 small, mit dem unteren Ende des 95-%-Bootstrap-Intervalls über 0;
  - er liegt nicht unter Pythia-160M.
- Gepoolt heißt: nach Aufgaben gewichteter Mittelwert über HellaSwag, PIQA, ARC-E, ARC-C, WinoGrande und OBQA.
- Zusätzlich berichtet: HellaSwag allein gegen GPT-3 Small (33,7, Wert aus dem GPT-3-Artikel, Format leicht
  verschieden).

**Chat**
- M5 auf den 100 Prompts:
  - Schleifen < 5 %;
  - Antworten, die ohne `<|im_end|>` am Token-Limit enden, < 5 %;
  - Rollen-Leck < 1 %;
  - Median-Antwortlänge ≤ 120 Token.
- M6: IFEval des Chat-Modells minus IFEval der Basis ≥ +8 Punkte.

**Quellen-Antworten**
- M7: HasAns-F1 ≥ 50 und NoAns-Treffer ≥ 60 %.
- M8: 0 angezeigte Zahlen oder Namen, die in keiner zitierten Quelle stehen (Prüfer `engramm.lm.sela_chat.verify`).
  Die Prüfung erkennt keine falsch verknüpften Fakten; diese Rate wird an 200 Antworten von Hand gezählt.
- M8: Abdeckung und Richtigkeit werden berichtet; ein Zielwert ist nicht festgelegt.

**Weitere Berichte**
- M10: int8-Verlust ≤ 0,005 Bits pro Byte, sonst liefert die App fp16 aus.
- Deutsch: ein Versuch ohne Zielwert. 40 deutsche Prompts aus M5 werden blind bewertet. Ist Deutsch unbrauchbar, wird
  beim nächsten Lauf Englisch-only erwogen.

## 3. Erwartungen (vor dem Lauf, keine Kriterien)

| Aufgabe | Erwartung | Bezugswerte |
|---|---|---|
| HellaSwag | ≈ 35 (33–37,5) | GPT-2 small 31,3; Sela-1 32,7; GPT-3 Small 33,7 |
| PIQA | ≈ 63,5 (61,5–66) | GPT-2 small 62,5; Sela-1 64,7 |
| ARC-E | ≈ 48 (44–53) | GPT-2 small 40,5 |
| LAMBADA | ≈ 30 (25–36) | GPT-2 small 33,7 |

- Chat: kurz, flüssig und höflich. Ohne Quellen oft falsch, nach einigen Zügen nachlassend.
- Wahrscheinlichkeit für die Stufe „GPT-3-Small-Niveau“ nach dem gepoolten Kriterium: ≈ 60–70 %.

## 4. Feste Abläufe

- Der Pod misst M1, M2 und M4. Alles andere läuft danach kostenlos auf GitHub Actions oder dem CPU-Rechner.
- Rückfälle im Lauf sind automatisch und werden berichtet; sie verringern die Tokenzahl, nicht das Budget:
  - divergiert das Training: weiter vom letzten Stand mit halber Lernrate;
  - sinkt der Verlust bis Schritt 300 nicht um 1,5 Nats: Neubeginn mit halber Lernrate.
- Vorabzustand: der letzte Stand vor dem Abklingen wird gesichert und gemessen, sofern Zeit ist. Er erlaubt eine
  faire Antwort auf die Frage, was die Chat-Daten im Abklingen an den Benchmarks ändern.
