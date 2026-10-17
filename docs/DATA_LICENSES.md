# Datenregister – was ENGRAMM Chat v3 nutzt, ausliefert und meidet

Stand: 2026-10-17 (Sela-2-Trainingsdaten ergänzt; davor 2026-10-05: Verstehen v3.2). Jede Datei eines Wissenspakets gehört genau einer Zeile dieser Tabelle an.
Ihre Lizenz steht zusätzlich in `manifest.json` → `licenses`.

## Ausgeliefert (im Wissenspaket oder im Programm)

| Daten | Quelle | Lizenz | Wo im Paket | Pflichten |
|---|---|---|---|---|
| Artikelanfänge (Lesetext) | DBpedia 2022.12 long abstracts = Wikipedia-Text | CC BY-SA 3.0 / GFDL | `corpus.u16`, Index-Dateien | Namensnennung (Wikipedia-Autoren, Link je Antwort über die Quellenanzeige); Weitergabe unter gleicher Lizenz |
| Älterer Lesetext (chat3) | Wikipedia | CC BY-SA 4.0 | nur in Paketen, die mit `--src chat3` gebaut sind | wie oben |
| Faktenbank: Infobox-Fakten, Typen, Weiterleitungen | DBpedia 2022.12 mappings | CC BY-SA 3.0 / GFDL | `kb.sqlite` (`src` = dbpedia) | wie oben |
| Faktenbank: Ergänzungen | Wikidata (Abfragedienst, Stand des Builds) | CC0 | `kb.sqlite` (`src` = wikidata) | keine; Quelle wird trotzdem genannt |
| Wortarten-, Satzbau-Modelle (Gewichte) | trainiert auf UD English EWT r2.14 | CC BY-SA 4.0 (Trainingsdaten) | `nlp/pos.json`, `nlp/parse.json` | Namensnennung; die Gewichte werden vorsichtshalber wie die Daten lizenziert |
| Absichts-Modell (Gewichte) | trainiert auf MASSIVE 1.1 en-US | CC BY 4.0 (Trainingsdaten) | `nlp/intent.json` | Namensnennung |
| Tokenizer, Codebuch, Spannen-Perzeptrons, Kalibrierer | eigene Zählungen auf dem ENGRAMM-Trainingsstrom | Projektlizenz | `tokenizer.json`, `codebook.npz`, `spanperc_*.json`, `confperc14.json`, `capstats.json` | – |
| Gesprächsbank: Smalltalk, Empathie, Sicherheit, Witze, Schreibbausteine | selbst geschrieben (`data/conv/`) | Projektlizenz (Apache 2.0) | im Programm (`engramm/chat/conv_bank.json`) | – |
| Fun Facts und Zitate | selbst formuliert, Quelle je Eintrag in `data/conv/fun.yaml` | Projektlizenz; Zitate sind kurze, gemeinfreie oder zitierfähige Sätze | im Programm | Quelle bleibt im Eintrag |
| Hilfsnummern (Krisenantworten) | offizielle Seiten der Dienste (988, TelefonSeelsorge, …) | Fakten, nicht geschützt | im Programm | vor jedem Release auf Aktualität prüfen |
| Regal: Volltext ganz Wikipedias (6,37 Mio. Artikel, 7 425 Fächer) | Wikipedia-CirrusSearch-Dump 2026-09-27 | CC BY-SA 4.0 | eigenes Release `shelf-20260927` (Fächer); im Paket nur der Regal-Index `shelf_index__*`, `shelf.json`, `shelf_source.json` | Namensnennung (Artikel-Link je Antwort); Weitergabe unter gleicher Lizenz |
| Wegweiser (Entität → offizielle Website, Belegadressen) | DBpedia 2022.12 (homepage), Wikidata P856 | CC BY-SA 3.0 / CC0 | `wayfinder.sqlite` | wie Artikelanfänge |
| Rechtschreib-Wortliste | eigene Zählung auf dem Lesetext | Projektlizenz | `spell.json` | – |
| Situations-Lexikon EN (Wortklassen, Oberbegriffe, Teil-Ganzes, Ereignis-Belege) | Open English WordNet 2024; FrameNet 1.7 (lexikalische Einheiten → Ereignisart) | OEWN: CC BY 4.0; FrameNet: CC BY 3.0 | im Programm: `engramm/understand/data/lex_en.tsv.gz`, `forms_en.tsv.gz` | Namensnennung (Princeton/OEWN-Projekt, ICSI Berkeley); Liste der Quellen in dieser Zeile und in `experiments/lex_build.py` |
| Situations-Lexikon DE (über den Interlingualen Index, Genus, Flexion, Glossen) | OdeNet (Hochschule Darmstadt); deutsches Wiktionary über kaikki.org | CC BY-SA 4.0 (OdeNet), CC BY-SA 3.0/4.0 (Wiktionary) | im Programm: `engramm/understand/data/lex_de.tsv.gz`, `forms_de.tsv.gz` | Namensnennung; die Datei wird unter CC BY-SA 4.0 weitergegeben |
| Rahmen-Klassifikator (Gewichte) | trainiert auf eigenen, von getrennten Agenten geschriebenen Beispielsätzen (`experiments/probes/frames_train*.jsonl`) und den Lexikon-Merkmalen | Projektlizenz; die Merkmale stammen aus den Lexika (siehe oben) | im Programm: `engramm/understand/data/frame_model.json.gz` | – |
| Anleitungs-Index (praktische Sätze aus Alltagsartikeln: Gesundheit, Haushalt, Geräte, Fahrzeuge, Tiere, Pflanzen, Essen; 6 893 Artikel) | Wikipedia über das Regal `shelf-20260927` (`experiments/howto_build.py`) | CC BY-SA 4.0 | im Programm: `engramm/know/data/howto.json.gz` | Artikeltitel als Quelle in jeder Antwort; Gesundheitsrat immer mit Arzt-Hinweis; Weitergabe unter gleicher Lizenz |
| Wikibooks-Schritte (First Aid, Bicycles, Automobile Repair, Knots; Erste Hilfe, Erste Hilfe im Gelände, Der Medicus, Survival; 218 Seiten) | Wikibooks-Dumps enwikibooks/dewikibooks „latest“ vom 5. Oktober 2026 (`experiments/wikibooks_build.py`) | CC BY-SA 4.0 | im Programm: `engramm/know/data/wikibooks.json.gz` | Buch und Seite als Quelle in jeder Antwort; Gesundheitsschritte immer mit Arzt-/Notruf-Hinweis; Weitergabe unter gleicher Lizenz |
| Vorschlags-Kataloge (Gerichte, Backwaren, Geschenke, Filme, Ausflüge, Textbausteine für Anlässe), Situations-Gesprächszüge | selbst geschrieben (`engramm/understand/suggest.py`, `data/conv/understand.yaml`) | Projektlizenz (Apache 2.0) | im Programm | – |
| Lernstand des Nutzers | entsteht auf dem Rechner des Nutzers (`learn.json` neben dem Chat-Gedächtnis) | gehört dem Nutzer | nicht ausgeliefert, nie übertragen | exakt vergessbar („vergiss das“, Zurücksetzen in der App) |
| Nachrichten-Feeds | die Verlage der gewählten Feeds | jeweiliges Recht des Verlags | nicht ausgeliefert: nur auf dem Rechner des Nutzers geladen, wenn er den Kanal einschaltet (`engramm/web/feeds.json` enthält nur die Feed-Adressen) | Anzeige mit Quelle und Link; kein Weiterverteilen |

## Sela-2: Trainingsdaten (nicht ausgeliefert; ausgeliefert werden nur die Gewichte)

Stand 17. Oktober 2026, vor dem GPU-Lauf (`experiments/sela2_data.py`). Die Daten liegen nur im privaten
Release-Entwurf „ENGRAMM Sela-2 Trainingsdaten (privat)“. Vor jeder Weitergabe der Gewichte gelten die Pflichten
der rechten Spalte.

| Daten | Quelle | Lizenz | Verwendung | Pflichten bei Weitergabe der Gewichte |
|---|---|---|---|---|
| FineWeb-Edu (+ Hoch-Qualitäts-Teil) | HuggingFaceFW/fineweb-edu, sample/10BT | ODC-By 1.0 (Common-Crawl-Bedingungen) | Vortraining EN | Namensnennung der Quelle |
| DCLM | HuggingFaceFW/dclm_100BT | ODC-By 1.0 | Vortraining EN | Namensnennung |
| C4 | allenai/c4 (en) | ODC-By 1.0 | Vortraining EN | Namensnennung |
| Cosmopedia v2 | HuggingFaceTB/smollm-corpus | ODC-By 1.0 (erzeugt mit Mixtral-8x7B-Instruct, Apache 2.0) | Vortraining EN | Namensnennung |
| Wikipedia EN/DE (20231101) | wikimedia/wikipedia | CC BY-SA 3.0 / GFDL | Vortraining | Namensnennung; ob Gewichte unter Share-Alike fallen, ist rechtlich offen |
| PG-19 | emozilla/pg19 (Project Gutenberg vor 1919) | gemeinfreie Texte | Vortraining EN | – |
| FineWeb2-HQ Deutsch | epfml/FineWeb2-HQ (deu_Latn) | ODC-By 1.0 | Vortraining DE | Namensnennung |
| SmolTalk: smol-magpie-ultra, everyday-conversations | HuggingFaceTB/smoltalk2 (SFT, aus SmolTalk) | Apache 2.0; **erzeugt mit Llama 3.1** | Chat (Abklingen + Feinabstimmung) | Llama-3.1-Lizenz: ein weitergegebenes Modell, das mit Llama-Ausgaben trainiert wurde, muss „Llama“ am Namensanfang tragen, dazu „Built with Llama“. **Entscheidung vor einer Veröffentlichung nötig** (umbenennen oder Chat-Teil ohne diese Daten neu trainieren; HuggingFace hat SmolLM2 mit denselben Daten unter eigenem Namen veröffentlicht) |
| SmolTalk: smol-rewrite, smol-summarize | HuggingFaceTB/smoltalk2 | Apache 2.0 | Chat | Namensnennung |
| SmolTalk2: systemchats, multilingual8 (nur Deutsch), jeweils Qwen3-32B | HuggingFaceTB/smoltalk2 | Apache 2.0 (Antworten von Qwen3-32B, Apache 2.0; das „Nachdenken“ entfernt) | Chat EN/DE | Namensnennung |
| OpenAssistant oasst2 (EN/DE) | OpenAssistant/oasst2 | Apache 2.0 | Chat | Namensnennung |
| Dolly 15k | databricks/databricks-dolly-15k | CC BY-SA 3.0 | Chat, Quellen-QA | Namensnennung; Share-Alike-Frage wie Wikipedia |
| SQuAD v2 (train) | rajpurkar/squad_v2 | CC BY-SA 4.0 | Quellen-QA | wie Dolly |
| HotpotQA (train) | hotpotqa/hotpot_qa | CC BY-SA 4.0 | Quellen-QA | wie Dolly |
| GermanRAG | DiscoResearch/germanrag | CC BY 4.0 | Quellen-QA DE | Namensnennung |
| Identität („Ich bin Sela …“) | selbst geschrieben (`experiments/sela2_data.py`) | Projektlizenz | Chat | – |

**Nicht verwendet:** Explore-Instruct-Rewriting (CC BY-NC 4.0, nur nicht-kommerziell), SystemChat-2.0 (keine
Lizenz), SmolTalk2 multilingual lang_5 (keine Lizenz angegeben), Magpie-Qwen2.5-Pro (Antworten zu lang für den
Zweck). Alle Testsätze der Messung wurden vor dem Training herausgefiltert (13-Wort-Fenster).

## Nur zum Messen, nicht ausgeliefert

| Daten | Lizenz | Zweck |
|---|---|---|
| UD English EWT `dev`/`test` | CC BY-SA 4.0 | Messung Phase 2 |
| MASSIVE `dev`/`test` | CC BY 4.0 | Messung Phase 2 |
| Gesprächsproben, versiegelte Sätze, Schlussfolgerungs- und Rahmen-Sätze (`experiments/probes/`) | Projektlizenz (von getrennten Agenten geschrieben) | Messung „Verstehen“ v3.2 (PREREG_UNDERSTAND_V0) |
| SQuAD, Natural Questions (frühere Runden) | CC BY-SA 4.0 / CC BY-SA 3.0 | QA-Messungen E14–E27 |
| ChatBench-Prompts | von Schreibern unter CC BY 4.0 eingereicht (Briefing) | Phase 1/8 |
| Sela-2-Benchmarks: HellaSwag, PIQA, ARC, WinoGrande, OpenBookQA, LAMBADA, MMLU, IFEval, SQuAD v2 dev | jeweilige Lizenz (MIT, Apache 2.0, CC BY-SA 4.0 u. a.) | Messung M3/M6/M7 (`docs/PREREG_SELA2.md`) |
| Sela-2-Chat-Prompts (`data/sela2/chat_eval_prompts.json`) | Projektlizenz (selbst geschrieben) | Messung M5 |

## Gemieden

- **Nur nicht-kommerziell nutzbar:** DailyDialog, EmpatheticDialogues.
- **Unklar oder problematisch:** MS MARCO, NRC EmoLex, Film- und Untertitelsammlungen, Reddit-Dumps.
- **KI-erzeugt:** ShareGPT, Alpaca, UltraChat.
- **Ungeprüft:** C4-Text in ausgelieferten Paketen. Der Lesetext der Pakete enthält kein C4.
- **Keine Lizenz gefunden, vor Nutzung klären:** PersonaChat, Wizard of Wikipedia, BlendedSkillTalk.

## Offene Punkte

- Eine Rechtsprüfung vor kommerzieller Nutzung steht aus. Offen ist vor allem die Share-Alike-Wirkung auf abgeleitete Indizes.
- Die Namensnennungsseite „Über ENGRAMM“ in der App verweist auf dieses Register. Eine Kopie gehört in jedes Wissenspaket (`manifest.json`).
