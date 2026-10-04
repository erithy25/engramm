# Datenregister – was ENGRAMM Chat v3 nutzt, ausliefert und meidet

Stand: 2026-10-04 (Atlas-Daten ergänzt). Jede Datei eines Wissenspakets gehört genau einer Zeile dieser Tabelle an.
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
| Nachrichten-Feeds | die Verlage der gewählten Feeds | jeweiliges Recht des Verlags | nicht ausgeliefert: nur auf dem Rechner des Nutzers geladen, wenn er den Kanal einschaltet (`engramm/web/feeds.json` enthält nur die Feed-Adressen) | Anzeige mit Quelle und Link; kein Weiterverteilen |

## Nur zum Messen, nicht ausgeliefert

| Daten | Lizenz | Zweck |
|---|---|---|
| UD English EWT `dev`/`test` | CC BY-SA 4.0 | Messung Phase 2 |
| MASSIVE `dev`/`test` | CC BY 4.0 | Messung Phase 2 |
| SQuAD, Natural Questions (frühere Runden) | CC BY-SA 4.0 / CC BY-SA 3.0 | QA-Messungen E14–E27 |
| ChatBench-Prompts | von Schreibern unter CC BY 4.0 eingereicht (Briefing) | Phase 1/8 |

## Gemieden

- **Nur nicht-kommerziell nutzbar:** DailyDialog, EmpatheticDialogues.
- **Unklar oder problematisch:** MS MARCO, NRC EmoLex, Film- und Untertitelsammlungen, Reddit-Dumps.
- **KI-erzeugt:** ShareGPT, Alpaca, UltraChat.
- **Ungeprüft:** C4-Text in ausgelieferten Paketen. Der Lesetext der Pakete enthält kein C4.
- **Keine Lizenz gefunden, vor Nutzung klären:** PersonaChat, Wizard of Wikipedia, BlendedSkillTalk.

## Offene Punkte

- Eine Rechtsprüfung vor kommerzieller Nutzung steht aus. Offen ist vor allem die Share-Alike-Wirkung auf abgeleitete Indizes.
- Die Namensnennungsseite „Über ENGRAMM“ in der App verweist auf dieses Register. Eine Kopie gehört in jedes Wissenspaket (`manifest.json`).
