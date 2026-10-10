# SPEC — ENGRAMM Chat v3 (Stand 2026-09-29)

Ein Offline-Chat-Assistent **ohne neuronales Netz**: Zählen, Regeln, HDC und gezählte lineare Modelle. Dieses Dokument beschreibt, was gebaut ist. Der Plan steht in `/root/.claude/plans/zippy-nibbling-feigenbaum.md`, gemessene Ergebnisse in `docs/EXPECTATIONS.md`.

## Ein Gesprächszug

```
Nachricht
 → Sicherheit (EN: data/conv/safety.yaml, DE: data/conv/de.yaml)            engramm/chat/acts.py, german.py
 → Deutsch? → deutscher Zug v0 (plaudern, Gefühle, Gedächtnis, Krisen)       engramm/chat/german.py
 → offene Rückfrage füllen / Entwurf ändern / Schere-Stein-Papier             engramm/chat/dialog.py
 → Sprechakte je Satz: safety, forget, remember, tool, intent, about, feeling, question, statement, writing
 → Gerätebefehl? (gezählter Absichts-Klassifikator, MASSIVE)  → ehrliche Absage   engramm/chat/device.py
 → Fähigkeiten:
     Smalltalk/Persona/Witze  (Gesprächsbank, SHAKE-256-Wahl ohne Wiederholung)   bank.py, conv_bank.json
     Empathie                 (Gefühlslisten, Verneinung, offene Rückfrage)
     Gedächtnis               (HDC-Faktenspeicher, prüfbares Vergessen, "what do you know about me")
     Faktenbank               (DBpedia + Wikidata, KGQA-Regeln, "as of my data")   engramm/kb/
     Textsuche + Antwortspanne (QA-Kern v14, unverändert)                          bot.py, retrieve.py, extract.py
     Tell me about / What is X (Artikelanfang, bereinigt, mit Quelle)             about.py
     Werkzeuge                (Rechner per AST, Einheiten, Datum)                  tools.py
     Schreiben                (Anfrage → Entwurf aus Bausteinen → Änderungsschleife) writing.py
 → Satzbau der Antwort (Frage → Aussage, zweite Person)                            realize.py
 → Antwort + Herkunft (Quelle je Faktensatz / "You told me" / Faktenbank-Eintrag)
```

## Komponenten

| Bereich | Dateien | Daten | Stand |
|---|---|---|---|
| Gesprächsbank | `data/conv/*.yaml` → `engramm/chat/conv_bank.json` (Studio: `python -m engramm.chat.studio`) | 74 Absichten, 19 Gefühle, Krisen/Ablehnungen, 30 Witze, 30 Fakten mit Quelle, 23 Schreibzwecke, Deutsch v0 | gebaut, getestet |
| Sprachgrundlagen | `engramm/nlp/` (Perzeptron, Tagger, gelabelter Arc-Hybrid-Parser, Absichten) | UD EWT r2.14, MASSIVE 1.1 | Vorregistrierung `PREREG_NLP_V0.md`, Testlauf siehe EXPECTATIONS |
| Faktenbank | `engramm/kb/store.py`, `kgqa.py`; Bau: `scripts/rebuild_kb.sh` | DBpedia 2022.12, Wikidata | gebaut |
| Lesetext | `experiments/reading_abstracts.py` | DBpedia-Abstracts (Wikipedia-Anfänge), nach Verweisen + Weiterleitungen gerankt | gebaut |
| Wissenspakete | `experiments/pack_build.py`, `pack_release.py`, `Corpus.from_pack` | Ordner + `manifest.json` (SHA-256 je Datei, Lizenzen) | Lite gebaut und gemessen |
| Server | `engramm/app/server.py` (`--pack`, `--desktop`, `--memory`) | – | getestet (Unit + gefroren) |
| Oberfläche | `ui/` (React 18, Vite 5, TS strict) → `engramm/app/web` | – | CI prüft Build und Aktualität |
| Rust-Kern v0 | `runtime/core` | – | CI: Unit- und Konformitätstests gegen Python |
| Desktop-App | `runtime/app` (Tauri 2), `runtime/sidecar` (PyInstaller) | – | CI baut Installer für Windows, macOS, Linux |
| Website | `website/` (statisch; lädt Schriften von Google Fonts und Lenis von jsDelivr) | – | Vercel veröffentlicht jeden Push auf den Branch `website` |
| Messung | `engramm/bench/chatbench.py`, `experiments/chatbench.py`, `PREREG_CHATBENCH.md` | Team-Prompts (dev) | Menschen-Runde steht aus |

## Grundsätze

- **Kein neuronales Netz**, auch nicht als Richter. ChatGPT tritt in Phase 8 nur als Gegner im Blindtest an.
- **Jeder Faktensatz mit Quelle.** Was nicht belegt ist, heißt „I'm not sure“ oder „I don't know“.
- **Deterministisch:** gleiche Eingaben, gleiche Antworten. Varianten werden per SHAKE-256 gewählt, die Uhr ist in Tests fest.
- **Netzverkehr nur auf Zustimmung:** der Paket-Download. Keine Update-Prüfung, keine Telemetrie.
- **Gedächtnis gehört dem Nutzer:** einsehbar (`/api/memory`), einzeln löschbar, nachweislich vergessen (Log-Neuaufbau).

## Phase 8: Ablauf der Endmessung (braucht Menschen)

1. **Prompts sammeln:** ≥ 20 Schreibende, Briefing nach `PREREG_CHATBENCH.md` § 6, als `data/chatbench/items.jsonl`.
2. **Teilmengen ziehen:** `python -m experiments.chatbench split --items data/chatbench/items.jsonl`.
3. **Einfrieren:**
   - Commit-Hash und Paket-Manifest-SHA in eine Registrierung `PREREG_CHATBENCH_RUN1.md` eintragen;
   - Erwartungen vorab festhalten.
4. **Antworten erzeugen:**
   - ENGRAMM: `python -m experiments.chatbench run --split test …`;
   - ChatGPT: dieselben Prompts einmal von Hand abfragen und als JSONL versiegeln (SHA-256 in die Registrierung).
5. **Bewertungsseite erzeugen:** `python -m experiments.chatbench sheet … --out rating.html`. Sie geht an ≥ 15 Bewertende, 3 Urteile pro Paar. Die Urteile kommen als JSON-Dateien zurück.
6. **Auswerten:** `python -m experiments.chatbench analyze … --ratings ratings/*.json`. Dazu kommen Cluster-Bootstrap und α. Parität je Kategorie gilt bei unterer Grenze ≥ 0,40 und P ≥ 0,45.
7. **Ergebnis** unverändert als E-Eintrag in `docs/EXPECTATIONS.md`, auch wenn es negativ ausfällt.
