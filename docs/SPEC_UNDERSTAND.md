# SPEC — ENGRAMM „Verstehen“ v3.2

Ziel: Alltagssituationen allgemein verstehen statt Thema für Thema von Hand, aus dem Gesagten schließen, unter den
genannten Bedingungen Vorschläge machen und auf dem Rechner des Nutzers dazulernen. Ohne neuronales Netz und ohne
Server. Messplan und Schwellen: `docs/PREREG_UNDERSTAND_V0.md`; Ergebnisse: `docs/EXPECTATIONS.md`, Abschnitt
„Verstehen v3.2“.

## Ablauf je Nachricht

```
Nachricht
 ├─ 1. Notizen   engramm/understand/infer.py  observe()   Zeiten, Dauern, Mengen, Optionen, Personen, Ort, Ernährung …
 │                └─ Widerspruch zu einer Notiz?  → Rückfrage („vorhin hast du gesagt …“)
 ├─ 2. Lernen    engramm/learn/  Learner.pre()            Korrektur, beigebrachtes Wort, Stilwunsch, „vergiss das“, Rückblick
 ├─ 3. Schließen infer.answer()                           nur wenn alles dafür gesagt wurde
 ├─ 4. bestehende Schichten (Fakten, Gedächtnis, Wissen, Werkzeuge, Smalltalk, Schreiben …)  engramm/chat/dialog.py
 ├─ 5. Prüfen    engramm/understand/suggest.py check()    Vorschlag/Text bricht oder übergeht eine Bedingung? → ersetzen
 ├─ 6. Zusammensetzen engramm/understand/compose.py      Füllantwort in einer Situation → Reaktion, Frage, Rat, Wunsch
 └─ 7. Nachbearbeiten Learner.post()                      Stil (kürzer, ohne Emojis), Belohnungssignale
```

Reihenfolge-Regel: Die bestehenden Schichten bleiben vorn, wo sie gut sind. Schritt 3 antwortet nur auf Fragen, deren
Antwort vollständig aus dem Gespräch berechnet werden kann; Schritt 5 ersetzt nur Antworten, die eine genannte Bedingung
verletzen oder übergehen; Schritt 6 ersetzt nur Füllantworten oder schwache Antworten innerhalb einer Situation.

## Bausteine

| Baustein | Datei | Inhalt |
|---|---|---|
| Situations-Lexikon | `engramm/understand/lex.py`, Daten `engramm/understand/data/lex_*.tsv.gz` | Wort → Lemma → Wortklasse, Kategorien (Gerät, Fahrzeug, Körperteil, Insekt, Person …), Ereignis-Belege; DE-Komposita über den Kopf; Nutzer-Wörter als Überlagerung |
| Lexikon-Bau | `experiments/lex_build.py` | OEWN 2024, OdeNet, FrameNet 1.7, Wiktionary (kaikki) → kompakte TSV-Dateien (< 1 MB) |
| Situations-Parser | `engramm/understand/frames.py` | Rahmen: Art (19 Klassen), wer, Gegenstand, Körperteil, Ursache, Frage-Art, Dringlichkeit, Verneinung |
| Rahmen-Klassifikator | `engramm/understand/classify.py`, Training `experiments/frame_train.py` | gemitteltes Perzeptron auf Regel-Entscheidung, Belegen, Kategorien, Wörtern; überstimmt die Regeln nur mit Abstand; Nutzer-Korrekturen als additive Gewichte |
| Zusammensetzen | `engramm/understand/compose.py`, Züge `data/conv/understand.yaml` | Reaktion, eine passende Frage, Rat je Art und Unterfall, Plan-Bestätigung, Dank, Wunsch; Situation lebt 6 Züge, braucht nach einem Themenwechsel einen ausdrücklichen Bezug |
| Anleitungs-Index | `engramm/know/howto.py`, Bau `experiments/howto_build.py` | praktische Sätze aus 2 060 Wikipedia-Artikeln (Gesundheit, Insekten), Suche nur über Namen und „auch bekannt als“; Sicherheitsstufe: Quelle und Arzt-Hinweis immer dabei |
| Schließen | `engramm/understand/infer.py` | Abfahrts-, Ankunfts- und Endzeiten; Datum ± Tage, Wochentag in N Tagen, Tage bis; Mengen mit Zu- und Abgängen; Raten über Zeiträume; Tempo × Zeit, Strecke ÷ Tempo; Preise × Mengen, Rechnung ÷ Personen; Rezepte skalieren; Alter und Altersabstände; Optionen nach Kriterium oder Budget; Personen, Rassen, Berufe, Gewohnheiten; Wohnort; Widersprüche |
| Vorschläge | `engramm/understand/suggest.py` | Gerichte, Backwaren, Bestellen mit Allergie, Geschenke im Budget nach Interessen, Filme nach Vorlieben, Ausflüge am Wohnort, Urlaub, persönliche Kurztexte nach Anlass mit Namen |
| Lernen | `engramm/learn/state.py`, `bandit.py`, `__init__.py` | Protokoll kleiner Schritte mit SHA-256, alles daraus abgeleitet; „vergiss das“ entfernt den letzten Schritt bitgleich; Korrekturen, Wörter, Stil, Episoden, Thompson-Bandit (erst ab 4 Signalen) |
| App | `engramm/app/server.py` (`/api/learning`, `/api/learning/reset`), `ui/src/components/Dialogs.tsx` | Lernstand ansehen und zurücksetzen |
| Rat-Schicht | `engramm/understand/advise.py` | Bereich aus dem ganzen Gespräch × Art der Bitte (Wahl, Urteil, Formulierung, Meinung, Tun, Dauer, Abschluss); ersetzt nur schwache Antworten oder fachfremde Tipp-Listen; Stimmungs- und Sprach-Korrektur |
| Wikibooks-Schritte | `engramm/know/wikibooks.py`, Bau `experiments/wikibooks_build.py` | 218 Seiten EN/DE (Erste Hilfe, Fahrrad, Auto, Knoten, Hausapotheke, Survival), Suche über Seitennamen, Quelle und Arzt-/Notruf-Hinweis immer dabei |
| Vorausdenken | `engramm/chat/events.py` `foresee`/`due_foresight` | nach einem Missgeschick die übliche nächste Frage bei der nächsten Begrüßung (Folgetag bis 14 Tage) |
| Neue Wörter, Lernpakete | `engramm/learn/__init__.py` `ask_word`, `engramm/learn/state.py` `export_pack`/`import_pack`, `python -m engramm.learn` | eine Rückfrage zu unbekannten Gegenständen, Antwort wird gelernt; Wörter/Korrekturen als geprüftes Paket teilen |
| Ideen-Schicht | `engramm/understand/ideate.py` | App-, Produkt- und Geschäftsideen aus dem Gesprächsthema (Zielgruppe × Anbieter × Mechanismus: Marktplatz, Peer-Tausch, tägliche Übung, Tool für Organisationen, Wissensaustausch; Dienstleistungs-Varianten), je mit Funktionen, Geldmodell und Startplan; erfundene, aussprechbare Namen; „the second one“ vertieft, „more“ liefert andere; Plan zu „reich werden“ |
| Aufsätze | `engramm/chat/dialog.py` `_essay` (nutzt `AboutFinder` aus `engramm/chat/about.py`) | „write me an essay/article/report about X“, „schreib mir einen Aufsatz über X“: Titel, Einleitung, Hauptteil in Absätzen, Schluss aus der Kerndefinition, Quelle; „longer/mehr“ setzt fort; wird nie als Nutzer-Fakt gespeichert; deutsche Bitte → englischer Text mit Hinweis |
| Ranglisten | `engramm/kb/kgqa.py` `_ranking` | größte Städte eines Landes aus der Faktenbank (Stand der Daten), EN/DE |

## Grenzen (ehrlich)

- Alles Verstehen beruht auf Wortlisten, Mustern und einem linearen Modell. Was die Muster nicht abdecken, wird nicht
  verstanden; die versiegelten Messungen zeigen das deutlich (U1 67 %, U5 20 % im ersten Lauf; Endmessung U6:
  65 % schwache Antworten auf frischen Gesprächen, Rat in 1 von 81 Bitten, Ereignisart 92 %, Schlüsse 40 %).
- Kein handgeschriebener Handler wurde abgebaut: das allgemeine System deckt sie nachweislich nicht gleich gut ab.
- Rat aus Wikipedia gibt es nur auf Englisch; deutscher Rat kommt aus den handgeschriebenen Zügen.
- Weltwissen für Schlüsse (Zeitzonen jenseits der IANA-Städtenamen, Währungen, welche Speise welche Zutat enthält)
  ist nur so weit vorhanden, wie die Kataloge und die Faktenbank reichen.
- Der Quellen-Abgleich erhöht die Konfidenz bisher nur bei Maßangaben, auf die sich zwei Artikel einigen; eine
  allgemeine Ausweitung würde die registrierten NQ-Werte verändern und ist offen.
