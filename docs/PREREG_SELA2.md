# Vorab-Registrierung: Sela-2 (festgelegt am 17. Oktober 2026, vor dem GPU-Lauf)

Gilt für den ersten Sela-2-Lauf nach `docs/SELA2_ANLEITUNG.md`. Rezept und Budget stehen in PLAN §12. Nach dem Lauf
werden diese Kriterien nicht mehr geändert. Neue Messungen dürfen dazukommen, sind dann aber als nachträglich zu
kennzeichnen. Präzisiert am selben Tag vor dem Lauf (nach der unabhängigen Prüfung): Schleifen-Definition in M5,
Kennzahlen in M3, Stichprobe in M7, Kontaminations-Prüfung in §4.

## 1. Was gemessen wird

| Nr. | Messung | Wo | Wie |
|---|---|---|---|
| M1 | Bits pro Byte je Quelle (FineWeb-Edu, DCLM, C4, Cosmopedia, Wikipedia EN/DE, PG-19, FineWeb2-DE) | Pod, `results/sela2/eval_{base,chat}.json` | je bis zu 600 zurückgehaltene Dokumente (Basis: 300) aus Dateien, die nie Trainingsteile waren; Fenster 2 048, Schritt 1 024 |
| M2 | Bits pro Byte auf den Prüfdokumenten der LM-Studie (val-A, Test, WikiText-103-Test) | Pod | dieselben Dokumente wie bei GPT-2 small (1,036) und Sela-1 (0,989); C4/WikiText sind für Sela-2 fremdere Daten, der Wert ist eine Vergleichsgröße, kein Ziel |
| M3 | Zero-Shot HellaSwag, PIQA, ARC-E, ARC-C, WinoGrande, OBQA, LAMBADA, MMLU (Lückentext) | GitHub Actions, `experiments/sela2_bench.py` (Messcode von `experiments/sela1_bench.py`) | gleiche Messung für Sela-2-Basis, Sela-2-Chat, Sela-1, GPT-2 small, GPT-2 medium, Pythia-160M/410M; Kennzahl je Aufgabe: acc_norm (log p je Zeichen der Fortsetzung) für HellaSwag, PIQA, ARC-E, ARC-C, OBQA, MMLU; acc für WinoGrande (Teil-Bewertung wie lm-eval) und LAMBADA |
| M4 | Antwort-Verlust auf zurückgehaltenen Gesprächen (Chat EN/DE, Quellen-QA) | Pod | Verlust nur auf Assistenten-Token |
| M5 | 100 feste Prompts (60 EN / 40 DE, `data/sela2/chat_eval_prompts.json`): Begrüßung, Identität, Anleitung, Umschreiben, Zusammenfassen, Quellen-QA, mehrere Züge | GitHub Actions, NumPy-Modell wie in der App (`experiments/sela2_chat_eval.py`) | automatisch gezählt, je Prompt (ein Gespräch mit mehreren Zügen zählt einmal und fällt durch, wenn eine seiner Antworten durchfällt): Ende am Token-Limit ohne `<|im_end|>`, Schleife (das Ende der Antwort wiederholt einen Block von p ≤ 64 Token mindestens 3-mal direkt hintereinander, zusammen ≥ 12 Token), Rollen-Leck (eine Zeile beginnt mit user/assistant/system o. ä. plus Doppelpunkt, oder Sonderzeichen-Text), Median-Antwortlänge über alle Antworten |
| M6 | IFEval (541 Prompts, prompt-level loose) | GitHub Actions | Chat-Modell und Basismodell |
| M7 | Quellen-QA: SQuAD-v2-dev mit Orakel-Kontext | GitHub Actions | 1 000 Fragen (500 beantwortbar, 500 unbeantwortbar; mit Seed 0 aus allen Dev-Fragen gezogen), Absatz als einzige Quelle, `SelaChat.grounded` wie in der App; HasAns-F1 (SQuAD-Normalisierung, bestes Gold) und NoAns-Treffer **getrennt**; Antwort-Spanne vor dem ersten [n] |
| M8 | ENGRAMM + Sela-2 Ende-zu-Ende auf frischen Fragen | App-Server auf dem CPU-Rechner | Abdeckung = Anteil der Wissensfragen mit angezeigter geprüfter Sela-2-Antwort; Richtigkeit auf diesem Anteil gegen ENGRAMM auf denselben Fragen; angezeigte Zahlen und Namen ohne Quelle |
| M9 | Blindvergleich durch den Auftraggeber | ChatBench-Seite | 40 Prompts: Sela-2 gegen SmolLM2-135M-Instruct und gegen ENGRAMM allein |
| M10 | int8 gegen fp32 | CPU | Unterschied in Bits pro Byte auf M1 |

## 2. Erfolgskriterien

**Stufe „GPT-3-Small-Niveau“ (Basismodell)**
- Der gepoolte Zero-Shot-Wert erfüllt beides:
  - er liegt über GPT-2 small, mit dem unteren Ende des 95-%-Bootstrap-Intervalls über 0;
  - er liegt nicht unter Pythia-160M.
- Gepoolt heißt: ungewichteter Mittelwert der Aufgabenwerte (jede Aufgabe zählt einmal) über HellaSwag, PIQA,
  ARC-E, ARC-C, WinoGrande und OBQA, mit den Kennzahlen aus M3; das Intervall ist ein gepaarter Bootstrap über die
  Aufgaben (2 000 Wiederholungen, Ziehung innerhalb jeder Aufgabe).
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

- Kontaminations-Prüfung nach dem Lauf: Die Trainingsdaten wurden vor dem Lauf gegen alle Testsätze gefiltert
  (13-Wort-Fenster, ≥ 3 Treffer). Zwei Lücken sind bekannt: WinoGrande-Sätze enthalten einen Platzhalter „_“, und
  Testtexte unter 15 Wörtern können nicht auffallen. Nach dem Lauf werden die tatsächlich trainierten Token gegen
  jede Aufgabe geprüft (WinoGrande mit eingesetzter Option, kurze Texte mit einem Treffer). Berichtet werden die
  Werte auf allen Fragen (für das Kriterium) und auf den sauberen Fragen.

- Der Pod misst M1, M2 und M4. Alles andere läuft danach kostenlos auf GitHub Actions oder dem CPU-Rechner.
- Rückfälle im Lauf sind automatisch und werden berichtet; sie verringern die Tokenzahl, nicht das Budget:
  - divergiert das Training: weiter vom letzten Stand mit halber Lernrate;
  - sinkt der Verlust bis Schritt 300 nicht um 1,5 Nats: Neubeginn mit halber Lernrate.
- Vorabzustand: der letzte Stand vor dem Abklingen wird gesichert und gemessen, sofern Zeit ist. Er erlaubt eine
  faire Antwort auf die Frage, was die Chat-Daten im Abklingen an den Benchmarks ändern.

## 5. Nachtrag vom 18. Oktober 2026: Auswahl der Chat-Datei für die App (nachträglich, vor dieser Messung)

**Anlass**
- Das Chat-Modell verfehlt vier der sieben Chat-Prüfungen aus §2: Token-Limit 9 %, IFEval +4,8, HasAns-F1 34,7,
  NoAns 47,6 %.
- Die Feinabstimmung kostete gepoolt −4,0 Punkte. Der Antwort-Verlust auf zurückgehaltenen Gesprächen (M4) sank
  dabei nur wenig: Englisch 1,14 → 1,11 Nats, Quellen-QA 0,26 → 0,25; Deutsch stieg 1,59 → 1,68
  (`results/sela2/eval_{base,chat}.json`).
- Das Basismodell hatte im Abklingen schon 232 Mio. Token Gespräche gesehen.

Die Kriterien aus §2 bleiben unverändert. Dieser Abschnitt legt nur fest, welche Datei die App bekommt. Die Regel
stand fest, bevor eine der Varianten gemessen wurde.

**Kandidaten**
- das Chat-Modell;
- das Basismodell;
- drei Gewichtsmischungen (1 − α) · Basis + α · Chat mit α = 0,3, 0,5 und 0,7 (`experiments/sela2_merge.py`, je
  Tensor in float32 gerechnet, als bf16 gespeichert; die App-Datei int8 wie beim Chat-Modell).

**Messung** (`.github/workflows/sela2_variants.yml`; Messcode unverändert bis auf die Namen der Mischungen und den
Seed-Versatz in M5; die App-Schutzregeln, die erst nach dieser Messung kommen, sind dabei aus)
- M3: die sechs gepoolten Aufgaben. Basis und Chat stammen aus dem ersten Lauf (dieselben Fragen); dazu kommt das
  gepaarte 95-%-Intervall jeder Datei gegen Basis und Chat.
- M5 mit drei Seed-Sätzen (Versatz 0, 1, 2; Versatz 0 sind die registrierten Seeds), für alle fünf Kandidaten:
  - Schleifen-, Limit- und Rollen-Leck-Rate: jeweils das Mittel über die drei Läufe;
  - Median: über alle Antworten der drei Läufe.
  - Versatz 0 des Chat-Modells wiederholt die registrierte Messung; gleiche Werte bestätigen, dass sie
    reproduzierbar ist.
- M6 für die Mischungen, jeweils minus Basis (Basis und Chat aus dem ersten Lauf).
- M7 für Basis und Mischungen (Chat aus dem ersten Lauf).

**Regel** (`experiments/sela2_variants.py`)
- Je Kandidat gibt es sieben Prüfungen:
  - M5: die vier Grenzen aus §2;
  - M6: mindestens +8 Punkte gegen die Basis;
  - M7: HasAns-F1 ≥ 50 und NoAns ≥ 60 %.
- Es gewinnt der Kandidat mit den meisten erfüllten Prüfungen. Bei Gleichstand entscheidet der höhere HasAns-F1,
  danach der höhere gepoolte M3-Wert.
- Nur vollständig gemessene Kandidaten können gewinnen.
- Die App bekommt den Gewinner. Er wird an §2 gemessen und berichtet, auch wenn er nicht alles erfüllt.

**Erwartung** (kein Kriterium)
- Gepoolt liegt die Mischung mit α = 0,5 höchstens 1,5 Punkte unter der Basis.
- Ob dabei die Chat-Prüfungen besser oder schlechter werden, ist offen.
- M6 ≥ +8 ist für keinen Kandidaten wahrscheinlich.

## 6. Nachtrag vom 18. Oktober 2026: Sela-2.1 – sanfte Feinabstimmung ab dem Basismodell (vor dem Lauf)

**Anlass**: Die Feinabstimmung des ersten Laufs begann nach dem Abklingen wieder bei 0,8 × der Spitzen-Lernrate,
mit dem Optimierer-Zustand des Vortrainings. Das hat einen Teil des Vortrainings überschrieben (siehe §5). Ein
neuer Versuch ändert nur das Rezept:

| | erster Lauf | Sela-2.1 |
|---|---|---|
| Start | Ende des Vortrainings, mit Optimierer-Zustand | `sela2_basis_bf16.pt`, frischer Optimierer |
| Lernrate (Anteil der Basisrate) | 0,8 | 0,03 und 0,1 (je ein Modell) |
| Aufwärmen | keines | 20 Schritte linear |
| Verlauf | halbe Zeit konstant, dann linear auf 0 | gleich |
| Daten | Chat EN, Chat DE, Quellen-QA je einmal, Identität dreimal | gleich, aber Chat DE dreimal |
| Ablauf | `experiments/sela2_run.sh` | dasselbe Skript mit `SELA2_MODE=sft21`, Kostenbremse 5 $ |

**Messung**
- Auf dem Pod: M1 (300 Dokumente je Quelle) und M4 für beide Modelle.
- Danach kostenlos auf GitHub (`.github/workflows/sela2_variants.yml` mit `"s21": ["lr03", "lr10"]`): M3, M5 mit
  drei Seeds, M6 und M7 – genau wie in §5.

**Regel**
- Die Kandidaten `s21lr03` und `s21lr10` treten gegen die vollständig gemessenen Kandidaten aus §5 an (Chat,
  Basis, Mischungen).
- Es gelten dieselben sieben Prüfungen und dieselben Gleichstandsregeln (`experiments/sela2_variants.py
  --previous`).
- Der Gewinner kommt in die App.

**Erwartung** (kein Kriterium)
- `s21lr03`: gepoolt höchstens 1 Punkt unter der Basis; Klartext-Bits pro Byte höchstens 0,03 über der Basis.
- `s21lr10`: dazwischen.
- M4 Deutsch nicht schlechter als die Basis (1,59).
- Ob M6 oder M7 ihre Grenzen erreichen, ist offen. Wahrscheinlich nicht: Die Aufgaben sind für 350 Mio. Parameter
  und 3 Mrd. Token schwer.

**Ergebnis** (18. Oktober, nachträglich ergänzt; Details `results/sela2/variants21/selection.md`): alle Kandidaten
4/7 Prüfungen, Gleichstand nach HasAns-F1 → mix30 (63,9) bleibt vor s21lr10 (57,9) und s21lr03 (53,7). Die Erwartung
für s21lr03 traf zu (gepoolt −0,0, Klartext +0,006 bpb, Deutsch 1,53).

## 7. Nachtrag vom 19. Oktober 2026: Sela-2 lernt vom Nutzer (vor der Messung)

**Anlass**: Der Nutzer will, dass Sela-2 aus dem lernt, was er schreibt – Fakten, Wortwahl, Satzbau –, aber ohne
seine Tipp- und Grammatikfehler zu übernehmen. Bisher sah Sela-2 nichts davon: Aussagen beantwortet ENGRAMM selbst,
und in der App-Messung empfahl Sela-2 nach „I'm planning a trip to Italy“ New York.

**Was gebaut ist** (`engramm/lm/sela_learn.py`, Anbindung in `engramm/app/server.py`; nur die App, die registrierten
Messungen laden nichts davon):
- **A. Fakten:** ENGRAMMs Faktengedächtnis (aus dem Chat-Gedächtnis neu aufgebaut, also vergessbar) wird als kurze
  Sätze in der ersten Person aus den Fakten selbst gebaut – nie aus dem Wortlaut des Nutzers – und Sela-2 als frühere
  Runde am Anfang jedes freien Gesprächs gezeigt („My name is Sam. My dog is called Rex.“ – „Thanks, I'll keep that
  in mind.“). Höchstens 8 Sätze, feste Reihenfolge. Auf Deutsch nur Namen, Orte, Daten und groß geschriebene Werte.
- **B. Gesprächsfaden:** Runden, die ENGRAMM selbst beantwortet, bleiben in Sela-2s Gespräch; der Text des Nutzers
  vorher durch ENGRAMMs Rechtschreibprüfung (Englisch).
- **C. Sprachgedächtnis** (kNN-LM): Paare (Sela-2s versteckter Zustand → nächstes Token) aus den Nachrichten des
  Nutzers; beim Schreiben eingemischt nur bei nahem Kontext (Kosinus ≥ 0,80, Anteil höchstens 0,30). Fehlerfilter:
  ein Token, für das das Modell eine fast gleiche Form mindestens 8-mal wahrscheinlicher hält, wird weder gelernt noch
  verstärkt (mit seinem ganzen Wort); Sätze mit medianer Überraschung über 6,5 Nats werden nicht gelernt; Bitten um
  Korrektur, Übersetzung oder Umformulierung und Zitate nie; Englisch vorher rechtschreibgeprüft. Vergessen: mit dem
  Gedächtniseintrag, „forget everything you learned“, der Lern-Seite, einem geleerten Gedächtnis.
- ENGRAMM selbst, zwei Korrekturen, die dabei auffielen: Bitten im Imperativ („Write a sign-off for me“) werden nicht
  mehr als Aussage gespeichert (daraus entstand der Fakt „I live in one nice.“), und „Mein Hund heißt Bruno“ /
  „Meine Katze heißt Mimi“ werden gespeichert.

**Messung** (`experiments/sela2_learn_eval.py`, `.github/workflows/sela2_learn_eval.yml`; App-Datei mix30, echtes
Lite-Paket, schneller App-Weg, Schutzregeln an):
- 40 synthetische Nutzer (`data/sela2/learn_sessions.json`, `experiments/sela2_learn_data.py`, fester Seed), 20 EN,
  20 DE. Je acht Lern-Nachrichten: vier Fakten (Name, Stadt, Haustier mit Namen, Lieblingsessen), vier Hobby-Sätze mit
  Fachwörtern; drei davon tragen einen typischen Fehler (Rechtschreibung oder falsche Form).
- Danach je sieben Proben, jede in einem neuen Gespräch, in drei Armen mit gleichem Seed: **aus** (die App vor §7),
  **F** (A+B), **FK** (A+B+C). Vor jedem Arm wird der Zustand nach dem Lernen wiederhergestellt.
- **L1 Fakten genutzt:** Anteil der Fakten-Proben (vier je Nutzer), deren Antwort den Faktwert enthält – gezählt auf
  den Proben, die in allen drei Armen Sela-2 beantwortet hat (ENGRAMMs eigene Antworten ändert §7 nicht). Die
  Messung gilt nur, wenn das mindestens 50 % der Fakten-Proben sind.
- **L2 Fehler übernommen:** Antworten (alle Proben), die eine der eingebauten falschen Formen des Nutzers enthalten.
- **L2b Rollen-Verwechslung:** Antworten, in denen Sela-2 einen Fakt des Nutzers als eigenen ausgibt („I live in
  Leeds“, „Ich heiße Jonas“).
- **L3 Sprachgedächtnis:** Bits pro Byte der zwei zurückgehaltenen Hobby-Sätze je Nutzer (nie gelernt, fehlerfrei),
  mit gegen ohne Gedächtnis.
- **L4 Chat-Qualität:** die 100 Prompts der App-Messung (`experiments/sela2_app_eval.py --teach-user en00`) mit
  Lernen F und FK gegen aus: Prompts mit automatisch erkanntem Problem.
- **L5 Tempo:** Token/s der Sela-2-Antworten, FK gegen aus.

**Regel** (fest vor der Messung; `experiments/sela2_learn_eval.py summarize`)
- A+B bleiben an, wenn: L1 F − aus ≥ +15 Punkte (bei gültiger Abdeckung); L2 F ≤ aus + 2; L2b F ≤ aus + 2;
  L4 F ≤ aus + 2. Sonst aus.
- C wird eingeschaltet, wenn A+B an sind und: L3 ≥ 1 % besser; L2 FK ≤ aus + 2; L2b FK ≤ aus + 2; L4 FK ≤ aus + 2;
  L5 FK ≥ 0,85 × aus. Sonst bleibt C aus (Code bleibt, `ENGRAMM_SELA2_KNN=1` schaltet es zum Prüfen ein).

**Erwartung** (kein Kriterium)
- L1 steigt deutlich für Name, Stadt und Haustier; beim Essen weniger (das Modell schlägt gern eigene Gerichte vor).
- Die Fehler-Übernahme bleibt bei allen Armen nahe null: die Proben laden zur richtigen Form ein, die Rechtschreib-
  prüfung fängt die englischen Tippfehler, der Filter die meisten deutschen.
- L3: kleiner Gewinn (die Hobby-Sätze teilen Wörter mit den gelernten); ob ≥ 1 %, ist offen.

### 7.1 Nachtrag vom 19. Oktober 2026, nach einer unabhängigen Prüfung (vor der Messung, nichts gemessen)

Eine Prüfung mit fünf Prüfern (Server, Gedächtnis, Messung, ENGRAMM, Workflow; jeder Befund von einem zweiten
Prüfer gegengeprüft) fand 39 bestätigte Fehler. Behoben, bevor irgendetwas gemessen wurde:

- **Messung, Daten:** Je Nutzer jetzt wie registriert vier Hobby-Sätze mit Fachwörtern; drei davon tragen den Fehler
  in einem zweiten Satz (vorher ersetzten die Fehlersätze drei Hobby-Sätze). Mehrdeutige Werte ersetzt (York ⊂ „New
  York“, Bath, Buddy, Tiger, Paul als Name und Haustier). Neue Daten: `data/sela2/learn_sessions.json`.
- **Messung, Zählung:**
  - Namen, Städte und Haustiere werden mit Großschreibung gezählt.
  - „should of course“ und „does she go“ gelten nicht als übernommener Fehler.
  - L2b zählt nicht bei Proben, die ausdrücklich Text in der Stimme des Nutzers verlangen (Grußformel, Nachricht an
    einen Freund, „Schreib einen Satz darüber, dass ich …“). Sie sind in den Daten mit `"voice": "user"` markiert. Ein
    Satz in der ersten Person ist dort die verlangte Antwort und keine Rollen-Verwechslung.
  - L1 wird auf den genauen Zählungen verglichen, nicht auf gerundeten Prozenten.
- **Messung, Ablauf:**
  - In den drei Armen lernt Schicht C die Proben selbst nicht (jeder Arm sieht den Stand nach dem Lernen).
  - Die App-Messung (L4) wartet nach jeder Runde, bis gelernt ist (feste Reihenfolge).
- **Messung, Gültigkeit:**
  - L4 ist Pflicht; ein fehlender App-Arm gilt als nicht erfüllt.
  - Die Entscheidung gilt nur mit allen 40 Nutzern, allen drei App-Armen und ohne abgestürzte Antwort. Abstürze
    zählen in der App-Messung als Problem. Sonst steht im Ergebnis „unvollständig – keine Entscheidung“.
  - Die Kriterien und Grenzen selbst sind unverändert.
- **App:**
  - Gelernt wird nach der Antwort, nicht davor.
  - ENGRAMMs eigene Antworten (Sicherheit, Gedächtnis) warten nie mehr auf Sela-2.
  - Ein Vergessen oder Zurücksetzen während des Lernens wird nicht mehr rückgängig gemacht. Das Zurücksetzen geht
    auch unter Windows, aus dem ENGRAMM-Modus und bei geschlossenem Gedächtnis.
  - B-Runden und C-Einträge werden mit ihrem Gedächtniseintrag vergessen (auch deutsche und umformulierte
    Aussagen); ein Vergessen-Befehl landet nicht im Gesprächsfaden.
  - Die Lern-Befehle („forget everything you learned“) beantwortet ENGRAMM selbst.
  - Bei Fakten gewinnt der neueste Wert nach Zeit. Fakten über andere („My ex-wife is called Anna“), Vergangenes und
    Verneinte werden nicht gezeigt.
  - Sätze mit Apostroph („I'm …“) sind lernbar.
  - Die Mischung bleibt auf der Logit-Skala (die Wiederholungsstrafe wirkt wie ohne Gedächtnis).
  - Der Cache-Fingerabdruck umfasst Modellkopf, Dateizeit und den Rechenweg.
  - Ein nicht zu öffnendes Gedächtnis schaltet nur C ab.
- **ENGRAMM:**
  - „Make sure you remember that …“, „Check this out, I live in …“ und Namen wie „Imagine Dragons is my favourite
    band“ werden wieder gespeichert; „Pick/Choose a name for my cat“ und weitere Bitten nicht.
  - „Mein Hund heißt wie nochmal?“ ist eine Frage und kein Name.
  - „Wie heißt mein Hund?“ wird auf Deutsch beantwortet.

### 7.2 Nachtrag vom 19. Oktober 2026, nach der zweiten Prüfung (vor der Messung, nichts gemessen)

Die zweite Prüfung kontrollierte die 39 Korrekturen und suchte neue Fehler. Sie bestätigte 23 weitere Punkte; alle
sind behoben:

- **Messung:**
  - L1 gilt als ungültig (keine Entscheidung), wenn Sela-2 weniger als die Hälfte der Fakten-Proben in allen Armen
    beantwortet. Das war registriert, aber nicht umgesetzt.
  - Ein Fakt gilt auch in seinen üblichen Formen als genutzt: deutsche Stadt-Adjektive und Genitive („Kölner Dom“,
    „Brunos Napf“), Essen in Einzahl, Mehrzahl und als Wortende („Roulade“, „Rindergulasch“, „taco“). Die Formen
    stehen in den Daten (`"forms"`).
  - Ob ein eingebauter Fehler im Sprachgedächtnis gelandet ist, wird nur noch am Gedächtnis selbst abgelesen.
  - Der Workflow committet nichts, wenn die Zusammenfassung scheitert. Die Commit-Zeile sagt „unvollständig“, wenn
    Teile fehlen.
- **App:**
  - B-Runden tragen auch die Gedächtniseinträge, die ihre Antwort zitiert („Your dog is called Rex“). Runden ohne
    solchen Vermerk gehen mit, wenn sie den vergessenen Wert enthalten („Dein Hund heißt Bruno.“).
  - Ein Text, der zwei Einträge speichert („Ich heiße Sam und wohne in Berlin“), geht mit jedem der beiden.
  - Vergessen erreicht Schicht C auch, wenn sie geschlossen ist; beim Öffnen wird sie auf das Chat-Gedächtnis
    zurückgeschnitten.
  - Ein Zurücksetzen während einer Antwort gewinnt gegen deren Lernen.
- **Fakten (Schicht A):**
  - Vergangenes und Künftiges im Satzteil des Werts wird nicht gezeigt („My late husband was called Tom“, „I'll be
    living in Paris“).
  - Geburtstage nur als Datum, auf Deutsch mit deutschem Monat.
  - Deutsche Artikel bleiben klein („der Schweiz“) und fallen in englischen Sätzen weg.
  - Zitate mit Apostroph darin („'he don't like the noise'“) gelten als Zitat und werden nicht gelernt.
- **ENGRAMM:**
  - Bitten werden nur verworfen, wenn sie nichts über den Nutzer sagen. Dazu gehört auch kein Satz nach Komma oder
    Doppelpunkt („Pick me, my name is Tom“) und keine Bitte ums Merken mit Aussage („Write this down: my name is
    Tom“, „Make sure you don't forget …“).
  - Verben, die auch Nomen oder Adjektive sind („Polish girl here“, „Book lover here“), zählen nur vor einem Objekt.
  - Namen als Satzgegenstand („Imagine Dragons has always been …“) bleiben Aussagen; „Help me remember where I parked“
    nicht.
  - Deutsch:
    - „Meine Freundin heißt wie nochmal?“ speichert nichts.
    - Bei Kater und Katze (ein englisches Wort) werden beide Namen genannt.
    - Eine wiederholte Aussage wird als „schon bekannt“ mit ihrem Eintrag beantwortet.

### 7.3 Nachtrag vom 19. Oktober 2026, nach der dritten Prüfung (vor der Messung, nichts gemessen)

Die dritte Prüfung bestätigte 21 Punkte, mehrere davon durch die Korrekturen aus 7.2 entstanden. Alle sind behoben:

- **ENGRAMM, Bitten:**
  - Ein Satz, der wie eine Bitte beginnt, wird nicht mehr ganz gespeichert, sondern nur seine Aussage: „Write me a
    poem, my favourite colour is blue“ speichert „my favourite colour is blue“, „Write this down: I'm vegetarian“
    speichert „I'm vegetarian“. Vorher wurde das Verb zum Wert („Your favourite colour is Write“).
  - Bitten an einen Text („Correct this sentence: I lives in Leeds“, „Review this: …“, „Translate this: …“) werden
    nie gespeichert und nie gelernt.
  - Verben, die auch Nomen sind, gelten wieder als Bitte („Plan Christmas“, „Book Paris hotels“), außer vor einem
    Nomen wie „girl“, „lover“, „club“.
  - Ein Name als Satzgegenstand gilt nur für Bands, Firmen und Produkte, direkt vor „is/has …“. Personen und Orte
    gehören nicht dazu („Imagine Paris is my home“ bleibt eine Bitte).
  - „Tom“, „Tim“, wieder „Tom“: Tom ist wieder der neueste Wert.
- **ENGRAMM, Deutsch:**
  - Die Kleinschreibung von „am/an/der“ in gespeicherten Orten ist zurückgenommen, weil „Frankfurt am Main“ sonst zu
    „Main“ wurde. Artikel werden nur in Sela-2s Faktenzeilen behandelt, und nur bei Ländern mit Artikel („der
    Schweiz“), nicht bei „Des Moines“.
  - Mehrere Namen werden nur genannt, wenn zwei deutsche Wörter ein englisches teilen (Kater/Katze). Nach einer
    Umbenennung gilt der neue Name.
- **App:**
  - Vergessen bei geschlossenem Sprachgedächtnis löscht auch dessen Cache.
  - Ein auf der Gedächtnis-Seite geleertes Gedächtnis leert C.
  - Ein Zurücksetzen gilt ab Beginn der Runde. Die Prüfung und das Einplanen geschehen unter derselben Sperre.
  - Beim Vergessen werden Runden ohne Vermerk nur noch über Namen und Daten erkannt, nicht über Wörter wie „dog“.
  - Ein Fehler beim Zurückschneiden lässt C geschlossen und wird gemeldet.
  - „My name is Will“ ist kein Futur.
  - Geburtstage mit Jahr werden erkannt.
  - Zitate über mehrere Zeilen gelten als Zitat.
- **Messung:** „Münster“ (auch das Nomen „das Münster“) ist durch Wiesbaden ersetzt. Die Wertformen stehen als feste
  Liste je Wert in den Daten, ohne erfundene Wörter.

### 7.4 Nachtrag vom 19. Oktober 2026, letzte Prüfung vor der Messung (nichts gemessen)

Die letzte Prüfung ging nur dem nach, was die Messung verfälschen oder abbrechen würde. Sie spielte alle 40 Nutzer
mit dem echten Paket durch und fand zwei Fehler, beide behoben:

- **Nachfrage zu einem Fachwort:** Fragt ENGRAMM nach einem unbekannten Wort („Quick question — what's a varroa?“),
  galt die Runde als Lern-Befehl. Der Hobby-Satz wurde deshalb nicht gelernt (5 von 160 Sätzen).
  - Jetzt bleibt die Nachfrage ENGRAMMs Antwort, und der Satz wird gelernt wie jeder andere.
- **Deutsch als Englisch erkannt:** „Ich wohne in Hannover.“ wurde als Englisch erkannt („in“ zählt als englisches
  Wort). Die englische Rechtschreibprüfung schrieb daraus „Ich zone in Hannover.“, und so wurde es gelernt.
  - Für Lernen und Rechtschreibprüfung zählt jetzt Deutsch, sobald die deutschen Funktionswörter mindestens so viele
    sind wie die englischen weniger eins.
  - Alle 320 Lern-Nachrichten der Daten werden so ihrer Sprache richtig zugeordnet.
  - Die Antwortsprache von Sela-2 (language_of) bleibt unverändert.

### 7.5 Ergebnis (19. Oktober 2026, `results/sela2/learn/`, Lauf 39200285702, Commit 296c62d)

Gültige Messung (alle 40 Nutzer, alle drei App-Arme, keine Abstürze, Abdeckung 100 %):

| Kriterium | aus | F (A+B) | FK (A+B+C) | Grenze | F | FK |
|---|---|---|---|---|---|---|
| L1 Fakten genutzt | 0,0 % | 52,5 % | 51,2 % | F − aus ≥ +15 | ja | – |
| L2 Fehler übernommen | 0 | 0 | 6 | ≤ aus + 2 | ja | nein |
| L2b Nutzer-Fakt als eigener | 0 | 7 | 7 | ≤ aus + 2 | **nein** | nein |
| L3 Sprachgedächtnis (bpb) | 1,5809 | – | 1,5723 (−0,55 %) | ≥ 1 % besser | – | nein |
| L4 App-Prompts mit Problem | 2 | 0 | 0 | ≤ aus + 2 | ja | ja |
| L5 Tempo (Token/s) | 36,0 | 30,9 | 28,5 (0,79) | ≥ 0,85 × aus | – | nein |

**Entscheidung nach der Regel: A+B aus, C aus.** In der App ist das Lernen damit standardmäßig aus
(`ENGRAMM_SELA2_LEARN=1` bzw. `ENGRAMM_SELA2_KNN=1` schalten es zum Ausprobieren ein).

Ursachen, aus den Antworten abgelesen (nach der Entscheidung):
- **L2b:** Sela-2 gibt die Faktenzeilen wörtlich als eigenen Text aus („Ich heiße Lea. Ich wohne in Hannover. Mein
  Lieblingsessen ist Lasagne.“). Das kommt vor allem auf Deutsch und bei Schreib-Aufträgen vor. Die Fakten standen als
  frühere Nachricht des Nutzers in der Ich-Form im Prompt; das kleine Modell kopiert sie. Auch ungezählte Antworten
  sprechen in der Rolle des Nutzers („Ich könnte mit Bruno …“).
- **L2 (nur FK):** „alot“ und „garnicht“ gingen durch den Fehlerfilter. Er vergleicht nur Ein-Token-Nachbarformen; ein
  fehlendes Leerzeichen („a lot“, „gar nicht“) erkennt er nicht.
- **L3/L5:** Das Sprachgedächtnis bringt 0,55 % statt ≥ 1 % und kostet 21 % Tempo. Ein Teil davon ist die
  Fehlerprüfung, die je Token und Kandidat die ganze Verteilung sortiert.
- **L1:** Der Nutzen ist groß (0 → 52,5 % genutzte Fakten). Die Schicht wird nicht verworfen, sondern muss ohne
  Rollen-Verwechslung gebaut werden (§8).

## 8. Nachtrag vom 19. Oktober 2026: Sela-2 lernt, Fassung 2 (vor der Prüfmessung)

**Anlass:** §7.5.
- Die Fakten wurden genutzt (0 → 52,5 %), aber Sela-2 gab die Faktenzeilen als eigene aus (L2b).
- Das Sprachgedächtnis übernahm „alot“ und „garnicht“ und brachte zu wenig (L3).
- Nach der Regel ist alles aus.

**Was sich ändert** (`engramm/lm/sela_learn.py`, `engramm/lm/sela_chat.py`, `engramm/app/server.py`):
- **A: Fakten als Notiz über den Nutzer** am Ende des Systemtexts, statt als Ich-Sätze einer früheren Nutzer-Nachricht.
  Die Werte sind beschriftet:
  - „About the user (… facts about the user, not about you …): name: Sam; lives in: Leeds; their dog: Rex.“
  - „Über den Nutzer (…): Name: Lea; wohnt in: Hannover; Hund: Bruno.“
- **Schutzregel:** Ein Satz der Antwort, der einen Nutzer-Fakt als Sela-2s eigenen ausgibt („Ich heiße Lea.“, „I live
  in Leeds.“), wird gestrichen. Es gibt englische und deutsche Muster. Besteht die Antwort nur aus solchen Sätzen, wird
  neu gezogen.
- **C: Wortfehler**, vom Modell am ganzen Text beurteilt, bis zum Ende der Runde:
  - **Zusammengeschrieben:** Eine Teilung in zwei einzelne bekannte Tokens macht den Text mindestens 1,25-mal
    wahrscheinlicher („alot“, „garnicht“).
  - **Ein Buchstabe zu viel oder zu wenig:** Geprüft werden die drei überraschendsten Wörter (mindestens 6 Nats). Eine
    Variante mit einem Buchstaben weniger oder einem verdoppelten Mitlaut macht den Text mindestens 8-mal
    wahrscheinlicher („wiederrum“, „Packet“, „vieleicht“, „… meine Schwesterr“).
  - **Wann gerechnet wird:** Eine Variante wird gerechnet, wenn das Modell sie am ersten geänderten Token schon
    vorzieht (diese Vorhersage liegt aus dem Text selbst vor) oder wenn sie als Buchstaben-Variante mit weniger Tokens
    geschrieben wird als das Wort („wiederum“ ist ein Token, „wieder|rum“ zwei). Gerechnet wird nur der Rest ab dem
    ersten geänderten Token, aus dem gespeicherten Zwischenstand, für alle Varianten von der letzten geänderten Stelle
    zur ersten. Höchstens 8 Wörter je Nachricht.
  - Satzzeichen um ein Wort gehören nicht dazu („(vieleicht)“), und an jeder Satzgrenze beginnt ein neues Wort. Jedes
    Wort wird über seine eigenen Tokens im Text gefunden, auch direkt nach einem Emoji; ein zweimal geschriebenes Wort
    wird an beiden Stellen geprüft.
- **C: Satz mit klarem Fehler:** Ein solcher Satz wird gar nicht gelernt, nicht nur das falsche Wort. Klar heißt:
  - ein Wort, das die Wortprüfung markiert hat, oder
  - eine Nachbarform-Markierung (mindestens 6 Nats, höchstens 6 je Nachricht), bei der der ganze Text mit der
    Nachbarform an der Stelle mindestens 8-mal wahrscheinlicher wird („she go“ → „she goes“). Eine Nachbarform, die
    ein seltenes Wort zerbricht („ R|äh|m|chen“), macht den Rest unwahrscheinlicher und zählt nicht.
  - Grund: Aus „Gestern ich habe gegangen zum Bäcker“ lernt C sonst die übrigen Wörter. Die Nachbarform-Markierung
    allein ist zu ungenau: In der Probe verwarf sie 246 von 320 korrekten Sätzen.
- **C: Lernen im Hintergrund:** Die Modellsperre gilt nur je Durchlauf des Modells, nicht für die ganze Analyse
  (Probe-Runde 5: im Mittel 1,7 s, höchstens 7,5 s je Nachricht). Eine Frage wartet höchstens einen Durchlauf.
- **C: Tempo:**
  - Die Nachbarform-Prüfung sortiert je Schritt einmal statt je Kandidat und prüft jedes vorgeschlagene Token einmal.
  - Das Einmischen rechnet nur die vorgeschlagenen Tokens einzeln, ohne volles Softmax je Schritt. Das Ergebnis ist
    rechnerisch gleich.
- **C: Mischung:** Die Einstellungen wurden auf den §7-Nutzern bestimmt (`results/sela2/learn_probe/probe.json`,
  Raster über Anteil, Ähnlichkeits-Boden und Schärfe): λ = 0,10, Boden = 0,90, τ = 0,01 (vorher 0,30/0,80/0,05).
  λ = 0,15 hätte 0,05 Punkte mehr gebracht; gewählt ist der kleinere Anteil des Gedächtnisses.
- **Server:**
  - ENGRAMMs Nachfrage zu einem Wort bleibt ENGRAMMs Antwort, der Satz wird gelernt (§7.4).
  - Deutsche Lerntexte werden als Deutsch behandelt.

**L5 neu gefasst:** Schreib-Tempo FK gegen F, statt Token/s FK gegen aus.
- **Schreib-Tempo** = geschriebene Tokens geteilt durch die Sekunden nach dem Lesen des Prompts, summiert über alle
  Sela-2-Antworten eines Arms und über alle Versuche. Die App meldet dafür Lese- und Schreibzeit getrennt.
- **Grund aus §7.5:** F war schon ohne C nur 0,86 × aus. Die F-Antworten waren kürzer (38,5 statt 59,1 Token), und die
  Token/s der App zählten die Zeit für den Prompt mit. Auch zwischen F und FK ändert C die Antwortlängen.
- **Grund aus der unabhängigen Prüfung:** FK übernahm den gespeicherten Prompt-Anfang von F. Jetzt liest jeder Arm
  seinen Prompt von vorn.
- Für A+B gibt es weiterhin kein Tempo-Kriterium.
- Die Auswertung berichtet auch FK/aus sowie die Token/s mit Prompt (F/aus, FK/aus, FK/F). Fehlt die Zeitmessung in
  einem Arm, ist die Messung ungültig.

**Entwicklung:** nur auf den §7-Nutzern (`data/sela2/learn_sessions.json`). Diese Läufe zählen nicht für die
Entscheidung:
- `results/sela2/learn_dev_v2a/` bis `results/sela2/learn_dev_v2f/`: App-Läufe mit allen Armen.
- `results/sela2/learn_probe/`: Probe des Sprachgedächtnisses.
- Ergebnisse der App-Läufe (jeweils alle 40 §7-Nutzer, drei Arme, App-Messung; Stand und Commit im Ordner):

  | Lauf | L1 | L2 F/FK | L2b F/FK | L3 | L4 F/FK (aus) | L5 | Fehler gespeichert |
  |---|---|---|---|---|---|---|---|
  | v2a (Notiz, Schutzregel; C alt) | +30,6 | 0/6 | 0/0 | 0,55 % | 2/3 (2) | 0,90¹ | 23 |
  | v2b (Wortprüfung, Mischung 0,10/0,85/0,01) | +30,6 | 0/1 | 0/0 | 2,91 % | 2/1 (2) | 0,96 | 5 |
  | v2c (+ Satz-Ausschluss mit Nachbarform) | +30,6 | 0/0 | 0/0 | 0,53 % | 2/1 (2) | 0,98 | 0 |
  | v2d (Satz-Ausschluss nur bei bestätigtem Fehler) | +30,6 | 0/1 | 0/0 | 3,27 % | 2/1 (2) | 0,96 | 0 |
  | v2e (Boden 0,90) | +30,6 | 0/0 | 0/0 | 3,39 % | 2/0 (2) | 0,975 | 0 |
  | v2f (dritte Prüfung umgesetzt; dieser Stand, e52cd43) | +30,6 | 0/0 | 0/0 | 3,39 % | 2/0 (2) | 0,979 | 0 |

  ¹ v2a noch nach der alten Fassung von L5 (Token/s mit Prompt, FK/aus).
- Probe Runde 10 (gleicher Code bis auf den Boden): von 120 eingebauten Fehlern gespeichert nur „definately“ und
  „freind“ (12×). Die App korrigiert beide vorher per Rechtschreibprüfung (in v2b–v2f: 37 korrigiert, 0 gespeichert).
  Die Rückspul-Rechnung weicht höchstens 0,001 Nats von einem vollen Durchlauf ab. Analyse je Nachricht auf CI im
  Mittel 2,0 s, höchstens 7,9 s; die App rechnet sie im Hintergrund, die Modellsperre gilt je Durchlauf.

**Prüfmessung:** einmal, auf 40 frischen synthetischen Nutzern (`data/sela2/learn_sessions_v2.json`).
- Die Nutzer kommen mit Seed 20261020 und haben neue Namen, Orte, Haustiere, Gerichte und fünf neue Hobbys mit eigenen
  Sätzen.
- Die Datei ist committet (234bab0), bevor irgendetwas darauf gemessen wurde.
- Ablauf, Arme, Kriterien L1–L4, Gültigkeitsbedingungen und Regel: genau wie §7 mit §7.1–§7.4. L5 wie oben.
- L4: die 100 App-Prompts nach dem Lernen des ersten Prüfnutzers (en00 der neuen Datei).
- Der Code ist der des Commits, der die Messung auslöst; Auswertung und Messung laufen auf demselben Stand.
- Das Ergebnis kommt nach `results/sela2/learn_v2/`.
- **Regel A+B:** an, wenn L1 F − aus ≥ +15 bei gültiger Abdeckung, L2/L2b F ≤ aus + 2 und L4 F ≤ aus + 2.
- **Regel C:** zusätzlich an, wenn L3 ≥ 1 %, L2/L2b FK ≤ aus + 2, L4 FK ≤ aus + 2 und L5 (Schreib-Tempo FK/F) ≥ 0,85.
- Die App übernimmt das Ergebnis als Standard. `ENGRAMM_SELA2_LEARN` und `ENGRAMM_SELA2_KNN` bleiben zum Umschalten.

**Erwartung** (kein Kriterium):
- L1 deutlich über +15, aber unter §7, weil eine Notiz weniger drängt als eine frühere Runde.
- L2b nahe 0.
- C: L3 über 1 %, L2 FK ≤ 2 und L5 über 0,85 sind wahrscheinlich, aber nicht sicher. Es sind neue Nutzer mit neuen
  Hobbys und neuen Fehlern.

### 8.1 Ergebnis (19. Oktober 2026, `results/sela2/learn_v2/`, Lauf 39236832092, Code e52cd43)

Gültige Messung (alle 40 frischen Nutzer, alle drei App-Arme, keine Abstürze, Abdeckung 100 %):

| Kriterium | aus | F (A+B) | FK (A+B+C) | Grenze | F | FK |
|---|---|---|---|---|---|---|
| L1 Fakten genutzt | 0,0 % | 35,0 % | 31,2 % | F − aus ≥ +15 | ja | – |
| L2 Fehler übernommen | 0 | 0 | 0 | ≤ aus + 2 | ja | ja |
| L2b Nutzer-Fakt als eigener | 0 | 0 | 0 | ≤ aus + 2 | ja | ja |
| L3 Sprachgedächtnis (bpb) | 1,5956 | – | 1,5724 (+1,45 %) | ≥ 1 % besser | – | ja |
| L4 App-Prompts mit Problem | 2 | 0 | 1 | ≤ aus + 2 | ja | ja |
| L5 Schreib-Tempo (Token/s) | 35,2 | 34,5 | 33,5 (FK/F 0,972) | ≥ 0,85 | – | ja |

**Entscheidung nach der Regel: A+B an, C an.** Das ist jetzt der Standard der App (`ENGRAMM_SELA2_LEARN=0` bzw.
`ENGRAMM_SELA2_KNN=0` schalten die Schichten ab).

Weitere Befunde (nach der Entscheidung, keine Kriterien):
- **Fakten:** auf Englisch 42,5 % genutzt, auf Deutsch 27,5 % (F) und 20,0 % (FK).
- **Eingebaute Fehler:** 34 von der Rechtschreibprüfung korrigiert, 76 vom Filter verworfen, 10 gespeichert („Packet“
  4×, „garnicht“ 3×, je 1× „Addresse“, „Standart“, „wiederrum“). Keiner davon kam in einer Antwort vor.
- **L3:** Mit +1,45 % liegt der Gewinn deutlich unter den Entwicklungs-Läufen (+3,39 %). Neue Hobbys und
  Fachwörter liegen dem Gedächtnis offenbar weniger.
- **Notiz wiedergegeben:** In 23 F- und 18 FK-Antworten (von je 270) gibt Sela-2 die Notiz über den Nutzer wieder
  („**Über den Nutzer:** Merle wohnt in Fulda …“). Das zählt kein Kriterium. Seit aeb00b5 streicht eine Schutzregel
  solche Sätze und Zeilen und zieht eine Antwort aus nichts anderem neu. Geprüft ist das nur auf den §7-Nutzern
  (`results/sela2/learn_dev_v2g/`; die Prüfnutzer sind verbraucht). Antworten mit Notiz F/FK: 26/27 (v2f) → 1/0.
  L1 sinkt dort von +30,6 auf +28,8, weil einige Fakten nur in den gestrichenen Notiz-Sätzen standen. L2, L2b und L4
  bleiben bei 0 (FK), L3 +3,39 %, L5 0,96.

## 9. Nachtrag vom 19. Oktober 2026: Notiz als Sätze – A/B-Test auf frischen Nutzern (vor der Messung)

**Anlass:** §8.1. Deutsche Fakten werden seltener genutzt (F: 27,5 % gegen 42,5 % auf Englisch). In den
Entwicklungs-Läufen hält Sela-2 den Namen des Nutzers oft für den des Haustiers („Lena ist eine echte Katze“). Die
Kurzform „Name: Lea; Hund: Bruno“ ist für das kleine Modell offenbar mehrdeutig.

**Was sich ändert** (`engramm/lm/sela_learn.py`, Schalter `ENGRAMM_SELA2_NOTE=sentences`): Die Notiz steht als Sätze in
der dritten Person da, mit derselben Kopfzeile wie bisher:
- „Der Nutzer heißt Lea. Der Nutzer wohnt in Hannover. Der Hund des Nutzers heißt Bruno.“
- „The user's name is Sam. The user lives in Leeds. The user's dog is called Rex.“
Die Notiz-Schutzregel streicht auch solche Sätze, wenn Sela-2 sie wiedergibt. Sonst gilt der App-Stand nach §8.1
(aeb00b5, Notiz-Schutzregel eingeschlossen).

**Entwicklung** (§7-Nutzer, zählt nicht für die Entscheidung): Dev-Lauf v2g (Kurzform) gegen v2h (Sätze):

| | v2g Kurzform | v2h Sätze |
|---|---|---|
| L1 F − aus | +28,8 | +40,0 |
| F: Englisch / Deutsch | 41,2 % / 16,2 % | 53,8 % / 26,2 % |
| FK gesamt | 36,2 % | 46,2 % |
| L2 / L2b (FK) | 0 / 0 | 0 / 0 |
| L4 F / FK (aus 2) | 2 / 0 | 1 / 0 |

**Prüfmessung:** auf 40 frischen Nutzern (`data/sela2/learn_sessions_v3.json`, Seed 20261021, d405a03, committet vor
jeder Messung darauf).
- Zwei vollständige Messungen wie in §8 (drei Arme, App-Messung nach dem Lernen von en00), mit demselben Code:
  - Kurzform nach `results/sela2/learn_v3_labels/`;
  - Sätze nach `results/sela2/learn_v3_sentences/`.
- Kriterien L1–L5 und Gültigkeit wie §8.

**Regel:** Die Satzform wird Standard der App, wenn beide Messungen gültig sind, die Satzform die Regel aus §8 für A+B
und für C erfüllt und L1 (F − aus) mit der Satzform um mindestens 5 Punkte über der Kurzform liegt. Sonst bleibt die
Kurzform. Unabhängig davon bleibt die Entscheidung aus §8.1 für A+B und C bestehen, solange die Kurzform-Messung sie
nicht widerlegt; erfüllt sie die §8-Regel nicht, wird das berichtet und neu entschieden.

**Erwartung** (kein Kriterium): L1 mit der Satzform 5 bis 12 Punkte höher; der Abstand zwischen Englisch und Deutsch
bleibt.

### 9.1 Ergebnis (19. Oktober 2026, `results/sela2/learn_v3_labels/` und `learn_v3_sentences/`, Läufe 39256767347 und 39256862412)

Beide Messungen sind gültig (alle 40 Nutzer, alle Arme, keine Abstürze, Abdeckung 100 %).

| Kriterium | Kurzform | Sätze | Grenze |
|---|---|---|---|
| L1 Fakten genutzt, F − aus | +20,0 | +44,4 | Sätze ≥ Kurzform + 5 |
| F: Englisch / Deutsch | 26,2 % / 13,8 % | 48,8 % / 40,0 % | – |
| L2 Fehler übernommen F / FK | 0 / 1 | 0 / 0 | ≤ aus + 2 |
| L2b Nutzer-Fakt als eigener F / FK | 0 / 0 | 0 / 0 | ≤ aus + 2 |
| L3 Sprachgedächtnis | +0,78 % | +0,78 % | ≥ 1 % |
| L4 App-Prompts mit Problem F / FK (aus 2) | 1 / 2 | 0 / 0 | ≤ aus + 2 |
| L5 Schreib-Tempo FK/F | 0,963 | 0,968 | ≥ 0,85 |

*Korrektur vom 19. Oktober 2026 (Abgleich für das Paper, `paper/`):* Im Arm aus hatten laut `summary.json` beider
Läufe 1 App-Prompt ein Problem, nicht 2; die Grenze für L4 war damit ≤ 3. An der Entscheidung ändert das nichts.

**Entscheidung nach der Regel:**
- **Die Satzform wird nicht Standard.** Sie liegt bei L1 um 24,4 Punkte vorn. Die Regel verlangt aber zusätzlich, dass
  die Satzform-Messung die §8-Regel auch für C erfüllt, und C verfehlt L3 (0,78 % < 1 %).
- **C geht wieder aus.** Die Kurzform-Messung erfüllt die §8-Regel für C nicht (L3 0,78 %). Neu entschieden wird nach
  derselben Regel: C aus (`ENGRAMM_SELA2_KNN=1` schaltet es ein).
- **A+B bleiben an** (L1 +20,0, L2/L2b F 0, L4 F 1).

**Einordnung** (nach der Entscheidung):
- Die Regel war schlecht gebaut. Sie hängt die Notizform an ein Kriterium von C, das mit der Notizform nichts zu tun
  hat: L3 ist in beiden Armen gleich, weil das Sprachgedächtnis die Notiz nicht sieht.
- Die Notizform wird deshalb in §10 auf neuen Nutzern noch einmal geprüft, mit einer Regel nur für A.
- L3 schwankt zwischen den Nutzergruppen stark: Entwicklung +3,39 %, §8 +1,45 %, §9 +0,78 %. Das Sprachgedächtnis
  hilft bei neuen Hobbys und Fachwörtern weniger als in der Entwicklung.
- Gespeichert wurden 6 von 120 eingebauten Fehlern. In 1 FK-Antwort (Kurzform) kam einer vor.

## 10. Nachtrag vom 19. Oktober 2026: Notizform, Wiederholung mit einer Regel nur für A (vor der Messung)

**Anlass:** §9.1. Die Satzform lag bei L1 um 24,4 Punkte vorn, wurde aber nicht übernommen, weil die §9-Regel sie an
ein Kriterium des Sprachgedächtnisses (C) koppelte, das die Notiz gar nicht sieht.

**Was gemessen wird:** derselbe Code wie in §9 (Notiz als Kurzform gegen Sätze, `ENGRAMM_SELA2_NOTE`).
- Prüfnutzer: 40 frische synthetische Nutzer (`data/sela2/learn_sessions_v4.json`, Seed 20261022, 9831eed, committet
  vor jeder Messung darauf). Namen, Orte, Haustiere, Gerichte und Hobbys sind neu.
- Zwei vollständige Messungen wie in §8 und §9:
  - Kurzform nach `results/sela2/learn_v4_labels/`;
  - Sätze nach `results/sela2/learn_v4_sentences/`.

**Regel (nur Schicht A):** Die Satzform wird Standard der App, wenn alle drei Bedingungen gelten:
- beide Messungen sind gültig;
- L1 (F − aus) liegt mit der Satzform um mindestens 5 Punkte über der Kurzform;
- die Satzform-Messung erfüllt die A+B-Kriterien aus §8: L1 ≥ +15, L2 F ≤ aus + 2, L2b F ≤ aus + 2, L4 F ≤ aus + 2.

Die Kriterien des Sprachgedächtnisses (L2/L2b/L4 FK, L3, L5) werden berichtet, entscheiden hier aber nichts. C bleibt
nach §9.1 aus.

**Erwartung** (kein Kriterium): Die Satzform liegt bei L1 wieder deutlich vorn, auf Deutsch stärker als auf Englisch.

### 10.1 Ergebnis (19. Oktober 2026, `results/sela2/learn_v4_labels/` und `learn_v4_sentences/`, Läufe 39259607123 und 39259712483)

Beide Messungen sind gültig (alle 40 Nutzer, alle Arme, keine Abstürze, Abdeckung 100 %).

| Kriterium | Kurzform | Sätze | Grenze (Satzform) | erfüllt |
|---|---|---|---|---|
| L1 Fakten genutzt, F − aus | +23,8 | +34,4 | ≥ +15 und ≥ Kurzform + 5 (+10,6) | ja |
| F: Englisch / Deutsch | 27,5 % / 20,0 % | 41,2 % / 27,5 % | – | – |
| L2 Fehler übernommen F | 0 | 0 | ≤ aus + 2 | ja |
| L2b Nutzer-Fakt als eigener F | 0 | 0 | ≤ aus + 2 | ja |
| L4 App-Prompts mit Problem F (aus 3) | 3 | 0 | ≤ aus + 2 | ja |
| *berichtet:* L3 Sprachgedächtnis | +0,09 % | +0,09 % | – | – |
| *berichtet:* L2 FK / L5 | 0 / 0,969 | 2 / 0,966 | – | – |

*Korrektur vom 19. Oktober 2026 (Abgleich für das Paper, `paper/`):* Im Arm aus hatten laut `summary.json` beider
Läufe 2 App-Prompts ein Problem, nicht 3; die Grenze für L4 war damit ≤ 4. An der Entscheidung ändert das nichts.

**Entscheidung nach der Regel: Die Satzform wird Standard der App.** `ENGRAMM_SELA2_NOTE=labels` bringt die Kurzform
zurück. C bleibt aus.

**Einordnung** (nach der Entscheidung):
- Auf zwei frischen Nutzergruppen liegt die Satzform bei L1 vorn: +24,4 Punkte (§9) und +10,6 Punkte (§10).
- Das Sprachgedächtnis bringt auf neuen Nutzern fast nichts mehr: +1,45 % (§8), +0,78 % (§9), +0,09 % (§10).
  Mit der Satzform übernahm es hier 2 Fehler in Antworten (Grenze 2). Dass C aus bleibt, ist durch diese Werte gedeckt.

## 11. Nachtrag vom 19. Oktober 2026: Sprachgedächtnis auf echten Nutzern (vor der Prüfmessung)

**Anlass:** §8.1, §9.1, §10.1. Der Gewinn von C auf den zurückgehaltenen Sätzen fiel von Nutzergruppe zu Nutzergruppe:
+3,39 % (§7, Entwicklung), +1,45 % (§8), +0,78 % (§9), +0,09 % (§10).

**Diagnose** (auf den verbrauchten Nutzern, nach den Messungen):
- **Die Mischeinstellungen sind es nicht.** Probe auf den §9- und §10-Nutzern (`results/sela2/learn_probe/probe_v3.json`,
  `probe_v4.json`), je 60 Einstellungen: am besten +0,83 % bzw. +0,25 % (λ 0,05, Boden 0,90, τ 0,01), die der App
  +0,76 % bzw. +0,05 %. Größere Anteile schaden (bis −2,6 %).
- **Die Prüfsätze sind es.** Wie viele Zweiwortfolgen der zurückgehaltenen Sätze schon in den gelernten Nachrichten
  desselben Nutzers stehen: §7 10,5 %, §8 5,3 %, §9 4,6 %, §10 2,7 % – die Rangfolge von L3. Über alle 320 Prüfsätze:

  | gemeinsame Zweiwortfolgen | Sätze | L3 |
  |---|---|---|
  | keine | 183 | +0,36 % |
  | bis 10 % | 46 | +1,85 % |
  | 10–20 % | 72 | +2,57 % |
  | über 20 % | 19 | +5,34 % |

  Ein Gedächtnis der Formulierungen eines Nutzers kann nur helfen, wo der Nutzer sie wieder verwendet. Wie viel die
  synthetischen Prüfsätze wieder verwenden, war meine Wahl beim Schreiben, nicht die der Nutzer.
- **Echte Nutzer verwenden mehr wieder:** 40 Entwicklungsnutzer aus WildChat-1M (s. u.) teilen 12,9 % der
  Zweiwortfolgen (Englisch 13,0 %, Deutsch 12,8 %) – mehr als jede synthetische Gruppe.
- **Fehlalarme der Wortprüfung:** In der §9-Probe markierte die Buchstaben-Prüfung korrekte Wörter („favourite“, weil
  das Modell „favorite“ vorzieht; „Meine neuen Kletterschuhe“ gegen „neue“; Endungen wie „parts“ → „part“). Nach der
  App-Regel fielen 77 von 320 korrekten Sätzen ganz heraus.

**Was sich ändert:**
- **Prüfnutzer sind echte Menschen** (`experiments/sela2_learn_real.py`): Quelle WildChat-1M (allenai/WildChat-1M,
  Revision 7d6490e, ODC-By; Zhao et al., ICLR 2024), Gespräche echter Menschen mit ChatGPT, nicht in Sela-2s
  Trainingsdaten.
  - Ein Nutzer ist eine gehashte IP je Sprache (Englisch, Deutsch), ohne als toxisch oder geschwärzt markierte
    Gespräche, mit mindestens sechs Nachrichten in Prosa (20–300 Zeichen, kein Code, keine Links, kein Markup,
    höchstens zwei Zeilenumbrüche, mindestens 85 % Buchstaben und Leerzeichen), in Zeitfolge (Zeit des Gesprächs,
    dann Turn-ID) ohne Beinahe-Kopien (Ähnlichkeit < 0,8). Die ersten vier werden gelernt, die nächsten zwei
    zurückgehalten. Nicht gefiltert wird, ob die App eine Nachricht lernt: wie bei einem echten Nutzer werden manche
    nicht gelernt (Entwicklung: 143 von 160, meist wegen Zitaten).
  - Entwicklung und Test sind nach dem SHA-256 der gehashten IP getrennt; je Sprache und Teil 20 Nutzer, gezogen mit
    Seed 20261023 aus 1504/58 (Entwicklung, en/de) und 1500/54 (Test) geeigneten. Die Auswahl (nur Gesprächs-Hash,
    Turn-ID, SHA-256 und Länge jeder Nachricht, keine Texte) ist committet (`data/sela2/learn_real_ids.json`, 41431d1),
    bevor irgendetwas auf diesen Nutzern gemessen wurde.
  - Die Texte stehen nicht im öffentlichen Repository: CI setzt sie aus der festen Revision zusammen und prüft jeden
    SHA-256. Ergebnisse halten echte Nachrichten nur als SHA-256 und Länge; Antworten und gezeigte Fakten verlieren jede
    Folge von ≥ 4 Wörtern, die der Nutzer geschrieben hat (die Kriterien rechnen auf dem vollen Text).
  - Der Rest eines Nutzers ist wie in den synthetischen Gruppen: vier Fakten zuerst, drei der vier echten Nachrichten
    mit einem angehängten typischen Fehler (gleiche Liste, gleiche Stellen; nach einer Nachricht ohne Schlusszeichen auf
    neuer Zeile, damit er ein eigener Satz ist), dieselben Fakten- und Fehlerproben.
- **Wortprüfung (C), Buchstaben-Regel:** Eine Variante, die nur den ersten Buchstaben oder einen nicht verdoppelten
  letzten weglässt, gilt nicht als Rechtschreibkorrektur („parts“ → „part“, „lebte“ → „lebt“, „Meine“ → „eine“). Alles
  andere bleibt wie in §8 (`LETTER_SHAPE`).
- **Probe:** lernt wie die App nur lernbare Nachrichten; mehrere Datensätze parallel.

**Entwicklung** (zählt nicht für die Entscheidung; nur Entwicklungsnutzer und verbrauchte synthetische Nutzer):
- Probe Runde 13 (echte Entwicklungsnutzer, `probe_real_dev.json`): L3 +1,97 % mit der App-Mischung; sie ist auch die
  beste Einstellung. Eine erste Gegenmaßnahme gegen Fehlalarme (Variante muss auch als Wort allein 8-mal
  wahrscheinlicher sein, 63123a5) ließ echte Fehler durch: „Packet“ ist als englisches Wort allein nicht selten
  (−1,44 Nats), „wiederrum“ 1,76; 18 statt 11 gespeicherte Fehler.
- Probe Runde 14 (`probe_r14_*.json`, e0e331f): 18 Buchstaben-Regeln aus dem Trace nachgespielt (Prüfung außerhalb
  des Texts: keine / Wort allein / im festen Satz der Sprache; 0, 1, 1,5, 2,08 Nats; mit/ohne Formregel), auf den
  echten Entwicklungsnutzern und den verbrauchten §7-, §9- und §10-Nutzern. **Auswahlregel, vor dem Ergebnis
  festgelegt:** zulässig sind Regeln, die über alle vier Datensätze nicht mehr eingebaute Fehler speichern als die
  bisherige Regel ohne Außen-Prüfung (45); darunter die mit dem höchsten L3 auf den echten Entwicklungsnutzern.

  | Regel | L3 echt | L3 §7 | gespeicherte Fehler (4 Sätze) | verworfene korrekte Sätze (echt, von 300) |
  |---|---|---|---|---|
  | bisher, ohne Außen-Prüfung | 1,99 % | 3,24 % | 45 | 119 |
  | **+ Formregel (gewählt)** | **2,03 %** | **3,37 %** | **45** | **116** |
  | Wort allein > 2,08 Nats (63123a5) | 1,97 % | 3,00 % | 81 | 99 |
  | Satz der Sprache > 1,5 Nats + Formregel | 2,18 % | 3,14 % | 66 | 95 |

  Jede Außen-Prüfung ließ mehr eingebaute Fehler durch; zulässig waren nur die beiden Regeln ohne sie.
- Unabhängige Prüfung des neuen Codes (Workflow mit fünf Blickwinkeln und Gegenprüfern): behoben wurden u. a. der
  eingebaute Fehlersatz, der mit einer echten Nachricht ohne Schlusszeichen verschmolz (ein erkannter Fehler nahm den
  echten Satz mit), echte Wortfolgen in Antworten der Ergebnisse, ein getrennter Ausweis des C-Entscheids.
- Probe Runde 15 (endgültiger Code bb21841, `probe_r15_real_dev.json`): L3 **+2,24 %** mit der App-Mischung (sie ist
  wieder die beste der 60 Einstellungen; ohne jeden Ausschluss +3,21 %). Gespeichert wurden 14 von 120 eingebauten
  Fehlern: 9 englische („freind“, „definately“ – die App korrigiert sie vorher mit ENGRAMMs Rechtschreibprüfung, die
  Probe nicht) und 5 deutsche von 60 (so viele wie auf den synthetischen Gruppen, §9: 6, §10: 5): „Packet“ und einmal
  „wiederrum“ knapp unter der Schwelle (2,01 und 2,07 Nats, nötig 2,08), einmal „wiederrum“ ohne Prüfplatz (die echte
  Nachricht hatte drei auffälligere Wörter, EDIT_WORDS = 3), „Rhytmus“ (ein fehlender Buchstabe wird nicht geprüft) und
  „garnicht“ (das Modell zieht „gar nicht“ dort nicht vor). Die Schwellen bleiben, wie sie sind: sie an diese
  Einzelfälle anzupassen, hieße auf die Entwicklungsnutzer zuzuschneiden.
- Bewusst nicht geändert (aus der Prüfung): Die Entwicklungs-Proben enthalten einzelne Wörter echter Nachrichten
  (geprüfte Varianten, markierte Tokens) aus dem öffentlichen Datensatz, keine Sätze; die App rät die Sprache einer
  Nachricht selbst (`_text_lang`) – gemessen wird die App, wie sie ist; die Testnutzer gehen als eintägiges Artefakt
  zwischen den Jobs (öffentlicher Datensatz).

**Prüfmessung:** einmal, auf den 40 echten Testnutzern (`learn_sessions_real_test.json`, in CI aus der Auswahl gebaut).
- Ablauf, Arme (aus, F, FK), Kriterien und Gültigkeit wie §8; L4: die 100 App-Prompts nach dem Lernen des ersten
  Testnutzers (en00); Notiz als Sätze (§10.1).
- Der Code ist der des Commits, der die Messung auslöst. Ergebnis nach `results/sela2/learn_real/`.
- **Regel C:** an, wenn L3 ≥ 1 %, L2 FK ≤ aus + 2, L2b FK ≤ aus + 2, L4 FK ≤ aus + 2 und L5 (Schreibtempo FK/F)
  ≥ 0,85 (`decision.layer_C_criteria_met` bei gültiger Messung). Die Schwellen sind die von §8, unverändert.
- A+B bleiben an (§8.1, §10.1); ihre Kriterien werden berichtet, entscheiden hier aber nichts.
- Die App übernimmt das Ergebnis als Standard; `ENGRAMM_SELA2_KNN` bleibt zum Umschalten.

**Erwartung** (kein Kriterium): L3 um +2 % (Entwicklung +2,24 %), also über 1 %. L5 wie bisher um 0,97. Das
unsicherste Kriterium ist L2 FK: auf Deutsch speichert C wie bisher einige eingebaute Fehler (s. o.), in §10 wurden
daraus 2 übernommene Fehler in Antworten (Grenze aus + 2).

### 11.1 Ergebnis (19. Oktober 2026, `results/sela2/learn_real/`, Lauf 39300348598, Code 3fb881a)

Die Messung ist gültig: alle 40 echten Testnutzer, alle drei Arme und alle drei App-Arme, keine abgestürzte Antwort,
Abdeckung 100 %.

| Kriterium | aus | F | FK | Grenze (FK) | erfüllt |
|---|---|---|---|---|---|
| L3 Sprachgedächtnis (80 zurückgehaltene echte Nachrichten) | 1,4413 bpb | – | 1,4183 bpb (**+1,59 %**) | ≥ 1 % | ja |
| L2 Antworten mit übernommenem Fehler | 0 | 0 | 1 | ≤ aus + 2 | ja |
| L2b Nutzer-Fakt als eigener | 0 | 0 | 0 | ≤ aus + 2 | ja |
| L4 App-Prompts mit Problem (von 100) | 2 | 0 | 1 | ≤ aus + 2 | ja |
| L5 Schreibtempo FK/F | – | – | 0,967 | ≥ 0,85 | ja |
| *berichtet:* L1 Fakten genutzt | 0 % | 40,0 % | 41,9 % | – | – |

Eingebaute Fehler: 33 vorher von ENGRAMMs Rechtschreibprüfung korrigiert (Englisch), 11 nicht gelernt (Nachricht nicht
lernbar), 70 vom Filter verworfen, 6 gespeichert.

**Entscheidung nach der Regel: C (Sprachgedächtnis) wird Standard der App.** `ENGRAMM_SELA2_KNN=0` schaltet es aus.
A+B bleiben an.

**Einordnung** (nach der Entscheidung):
- Auf echten Nutzern wirkt C: +1,59 % (Entwicklung +2,24 %; der Testwert liegt wie erwartet etwas darunter). Auf den
  synthetischen Gruppen §8–§10 war es weniger, weil deren Prüfsätze kaum Formulierungen der Nutzer wiederholten.
- Die eine übernommene Fehlform war „ich habe gegangen“ (de04, Hobby-Probe, Arm FK). Der Filter hatte den Satz aus
  dem Gedächtnis verworfen; reine Grammatikfehler aus richtigen Wörtern sind die bekannte Grenze (Modellkarte).
- Die Wirkung ist messbar, im Chat aber klein: Sela-2 sagt die eigenen Formulierungen des Nutzers etwas besser
  voraus. Spürbarer ist A; dort fällt in den Abschriften auf, dass Sela-2 Fakten auch unpassend einbaut („Niklas und
  Bruno machen gerne gemeinsam Lasagne.“). L1 zählt jede Nutzung, nicht ob sie passt – das ist die nächste Baustelle.

## 12. Nachtrag vom 19. Oktober 2026: Fakten nur, wenn die Nachricht davon handelt (vor der Messung)

**Anlass** (nach §11.1, auf verbrauchten Messungen ausgezählt): Mit der Notiz bringt Sela-2 Fakten ein, nach denen
niemand gefragt hat.
- Antworten auf die Proben, die einen nicht erfragten Fakt des Nutzers nennen (Name, Stadt, Name des Haustiers,
  Lieblingsessen): F 40,7 % (`learn_real`), 35,8 % (`learn_v4_sentences`), 36,3 % (`learn_v3_sentences`); ohne Notiz
  0 %. Beispiel: „Schreib einen Satz darüber, dass wir wegen des Wetters …“ → „Niklas lebt in Freiburg. Bruno wohnt
  dort.“
- Antworten auf die 100 App-Prompts nach dem Lernen eines Nutzers, die seine Fakten nennen: 10 bzw. 15 von 96 (mit
  C 13 bzw. 12), oft als Sela-2s eigene („Hi!“ → „Hi! I like to play with my dog Rex.“; „Who are you?“ → „I'm a small
  offline assistant who lives in Norwich“). Die Schutzregel fängt nur feste Ich-Sätze.
- L1 zählt jede Nutzung eines Fakts, nicht ob sie passt; L2b nur feste Muster.

**Was sich ändert** (`engramm/lm/sela_learn.relevant_items`, `engramm/app/server.py`, 96e9897):
- Die Notiz zeigt nur die Fakten, um die es in der Nachricht geht: Die Nachricht nennt den Wert („Rex“, „Leeds“) oder
  das Thema in ihrer Sprache (Hinweiswörter je Kategorie: „cook“, „dinner“, „Rezept“ für das Lieblingsessen; der
  Tiername oder „dog“, „Hund“, „pet“ für das Haustier; „sign-off“, „e-mail“, „Grußformel“, „vorstellen“ für den
  Namen; „my city“, „near me“, „in der Nähe“, „Wohnort“ für die Stadt …), oder sie fragt, was Sela-2 über den Nutzer
  weiß (dann alle). Sonst gibt es keine Notiz. `ENGRAMM_SELA2_FACTS=all` bringt das bisherige Verhalten zurück.
- Die Schutzregel gegen Nutzer-Fakten als eigene prüft weiter alle Fakten, nicht nur die gezeigten.
- **Die Hinweiswörter sind mit 96e9897 eingefroren.** Sie wurden geschrieben, bevor die Testfragen (s. u.) vorlagen.
  Die Testfragen kamen danach und wurden gelesen; geändert wurde an den Hinweiswörtern danach nichts.
- Neues Kriterium **L6 Einmischung:** Anteil der Sela-2-Antworten auf die Proben, die einen Fakt nennen, den die Probe
  nicht erfragt (eine Faktenprobe erfragt einen, jede andere keinen); und Zahl der Antworten auf die App-Prompts nach
  dem Lernen des ersten Testnutzers, die einen seiner Fakten nennen.

**Prüfnutzer:** 40 weitere echte Nutzer aus dem Test-Teil der WildChat-Auswahl, die in §11 nicht verwendet wurden
(`data/sela2/learn_real_ids.json`, Teil `test2`, gezogen mit Seed 20261025 aus 1478/34 unverbrauchten, en/de; die
Teile `dev` und `test` sind unverändert). Fakten aus den §8-Pools.
- **Faktenproben neu und blind formuliert:** Ein unabhängiger Agent hat je Sprache 6 Formulierungen je Fakt und
  12 neutrale Anfragen geschrieben, nur aus einer Beschreibung der Absicht, ohne das Repository, den Filter oder seine
  Hinweiswörter zu sehen (`data/sela2/probes_v12.json`). Je Nutzer wird pro Fakt eine gezogen; dazu kommen zwei
  neutrale Anfragen (eine gute Antwort nennt keinen Fakt), die zwei Fehlerproben und die Hobby-Probe wie in §11.
- Die Auswahl und die Proben sind committet, bevor auf diesen Nutzern irgendetwas gemessen wurde.

**Messungen** (Code des auslösenden Commits, sonst wie §11):
1. mit Filter (`facts: relevant`) nach `results/sela2/learn_real2_relevant/` – entscheidet;
2. ohne Filter (`facts: all`, bisheriges Verhalten) nach `results/sela2/learn_real2_all/` – nur zum Vergleich auf
   denselben Nutzern.

**Regel (nur der Filter):** Der Filter wird Standard der App, wenn Messung 1 gültig ist und erfüllt:
L1 F − aus ≥ +15, L2 F ≤ aus + 2, L2b F ≤ aus + 2, L4 F ≤ aus + 2, **L6 F ≤ 10 %** der Sela-2-Antworten und
**L6 App (F) ≤ 3** Antworten (`decision.facts_criteria_met`). Sonst bleibt `all`, und die Einmischung bleibt als
offenes Problem dokumentiert. C bleibt an (§11.1); seine Kriterien werden berichtet.

**Erwartung** (kein Kriterium): L6 sinkt stark, auf wenige Prozent. L1 liegt unter §11 (+40,0): Beim Lesen der
eingetroffenen Testfragen war zu sehen, dass einige keines der Hinweiswörter enthalten („Friends are visiting me … What
should I show them?“, „Dankeskarte“, „Leibgericht“) – dort zeigt die Notiz nichts. Ich erwarte L1 trotzdem über +15.

### 12.1 Ergebnis (19. Oktober 2026, `results/sela2/learn_real2_relevant/` und `learn_real2_all/`, Läufe 39304157648 und 39304201588)

Beide Messungen sind gültig: alle 40 echten Testnutzer, alle Arme und App-Arme, keine abgestürzte Antwort,
Abdeckung 72,5 % (Sela-2 beantwortete 72,5 % der Faktenproben in allen Armen; die übrigen beantwortete ENGRAMM selbst).

| Kriterium | mit Filter (entscheidet) | ohne Filter (Vergleich) | Grenze | erfüllt (mit Filter) |
|---|---|---|---|---|
| L1 Fakten genutzt, F − aus | +30,2 | +30,2 | ≥ +15 | ja |
| L6 Antworten mit nicht erfragtem Fakt, F | **0,0 %** (0/291) | 24,7 % (72/291) | ≤ 10 % | ja |
| L6 App-Antworten mit Fakten des gelernten Nutzers, F | **1** von 96 | 12 von 96 | ≤ 3 | ja |
| L2 übernommene Fehler, F | 0 | 0 | ≤ aus + 2 | ja |
| L2b Nutzer-Fakt als eigener, F | 0 | 0 | ≤ aus + 2 | ja |
| L4 App-Prompts mit Problem, F | 2 | 1 | ≤ aus + 2 (4) | ja |
| *berichtet:* mit C (FK): L6 / L6 App / L1 | 1,0 % / 2 / +31,0 | 29,9 % / 14 / +36,2 | – | – |
| *berichtet:* L3 Sprachgedächtnis / L5 | +3,07 % / 0,965 | +3,07 % / 0,975 | – | – |

**Zählfehler, offen gelegt:** Die App-Messung hat die Einmischung für jede Antwort aufgezeichnet (Feld `intrusion`),
aber `experiments/sela2_app_eval.summarize` zählte sie nicht; in der automatisch erzeugten Zusammenfassung stand L6 App
deshalb als „None“ und `facts_criteria_met` als falsch. Die Zahl wurde nach der Messung aus denselben aufgezeichneten
Antworten gezählt (keine neue Messung; nur L6 App änderte sich, 2edd391), der Code ist korrigiert.

**Entscheidung nach der Regel: Der Filter wird Standard der App** (er ist es im Code seit 96e9897;
`ENGRAMM_SELA2_FACTS=all` bringt das alte Verhalten zurück).

**Einordnung** (nach der Entscheidung):
- Auf denselben Nutzern und Proben nutzt Sela-2 die Fakten mit Filter genauso oft, wo sie gefragt sind (+30,2 beide
  Male), bringt sie aber fast nie mehr ungefragt ein (0,0 % statt 24,7 %; in der App 1 statt 12 von 96 Antworten).
- Die zwei verbliebenen App-Fälle kamen über Hinweiswörter in Anfragen, die nicht vom Nutzer handeln („Summarize this
  email …“ zeigte den Namen, „Die Stadt baut …“ die Stadt) – die bekannte Grenze von Hinweiswörtern.
- Englische Faktenproben wurden mit Filter seltener mit Fakten beantwortet als ohne (22,2 % gegen 25,0 %), deutsche
  häufiger (33,8 % gegen 32,5 %): Einige blind formulierte englische Proben enthalten keines der Hinweiswörter.

