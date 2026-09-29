# Autoren-Leitfaden – die Gesprächsbank von ENGRAMM

Die Gesprächsbank ist das, was ENGRAMM „sagt“, wenn es nichts nachschlägt: Smalltalk, Mitgefühl, Sicherheit, Witze, Antwortsätze, Schreibbausteine. Sie ist **von Menschen geschrieben**, liegt als YAML in `data/conv/` und wird zu `engramm/chat/conv_bank.json` übersetzt. Zur Laufzeit wird kein YAML gelesen.

## Arbeitsablauf

```bash
python -m engramm.chat.studio check                   # Regex, Doppelte, Platzhalter, Routing-Konflikte
python -m engramm.chat.studio try "hey buddy" "lol"   # welche Absicht greift, welche Antwort käme
python -m engramm.chat.studio coverage                # jedes Beispiel → erreichte Absicht
python -m engramm.chat.studio build                   # prüfen und conv_bank.json schreiben
python -m pytest -q tests/test_chat_flows.py tests/test_chat_units.py
```

`build` und die Tests müssen grün sein, bevor committet wird. Die CI prüft `check` bei jedem Push.

## Dateien

| Datei | Inhalt | Schlüssel |
|---|---|---|
| `smalltalk.yaml` | Absichten (Begrüßung, Dank, Fragen an ENGRAMM, Persona) | `intents[]`: `id`, `patterns`, `examples`, `responses`, `responses_named`, `action`, `follow` |
| `empathy.yaml` | Gefühle: Wortlisten, Verneinung, Antworten mit offener Rückfrage | `feelings[]` |
| `safety.yaml` | Krisen (Hilfenummern) und Ablehnungen; **nur mit Vier-Augen-Prüfung ändern** | `crisis`, `refuse` |
| `fun.yaml` | Witze, Fun Facts (**jeder mit Quelle**), Zitate (mit Urheber), Geschichten, Fragen an den Nutzer | |
| `replies.yaml` | Antwortsätze der Gesprächsschicht (weiß nicht, gelernt, vergessen, Quelle …) | |
| `writing.yaml` | Anreden, Grußformeln, Zwecke (`purposes`) mit Betreff, `formal`/`casual` × `open`/`body`/`close` | |

## Regeln für Muster

- **Volltreffer auf die normalisierte Nachricht.** Die Nachricht wird kleingeschrieben, bekommt gerade Apostrophe, verliert Endsatzzeichen und die Anrede „engramm/bot/buddy“, Chat-Schreibweisen werden ausgeschrieben („u“ → „you“). Das Muster muss also kleingeschrieben sein und passt auf den ganzen Satz.
- **Erst eng, dann breit.** Frühere Absichten gewinnen. `check` meldet ein Beispiel, das von einer früheren Absicht abgefangen wird.
- **Beispiele sind Pflicht.** Sie dienen dem Nächste-Beispiel-Vergleich kurzer Nachrichten ab Schwelle 0,55 und sind die Testfälle von `coverage`.
- In YAML Muster in einfache Anführungszeichen setzen. „yes“, „no“ und „on“ bleiben dank `BaseLoader` Wörter.

## Regeln für Antworten

- **Mindestens drei Varianten** je Absicht, sonst gibt es eine Warnung. Gewählt wird deterministisch per SHAKE-256 aus (Gespräch, Liste, n-te Nutzung). Eine Variante aus den letzten Zügen wird übersprungen.
- **Platzhalter** nur aus der erlaubten Menge (`{name}`, `{topic}` …), sonst schlägt `check` fehl. `responses_named` wird nur genutzt, wenn der Name bekannt ist.
- **Ton:** freundlich, kurz (1–2 Sätze), ehrlich. Keine erfundenen Erlebnisse: ENGRAMM hat keinen Körper und keine Familie und sagt das auch. Keine Versprechen, die das Programm nicht halten kann. Kein „Als KI …“.
- **Persona-Treue:** ENGRAMM läuft ohne neuronales Netz, offline und merkt sich nur, was man ihm sagt. Aussagen über sich selbst müssen dazu passen, denn Widersprüche sind ein Messkriterium (≤ 2 %).
- **Fakten nur mit Quelle.** Fun Facts tragen `source`. Eine Antwort ohne Quelle darf keine Tatsachenbehauptung über die Welt enthalten.

## Sicherheit

- **Krisenantworten** nennen immer eine Hilfenummer (988 USA, TelefonSeelsorge 0800 111 0 111 bzw. 116 123 …) und laden zum Weiterreden ein. Jede Änderung braucht eine zweite Person und einen Test in `tests/test_chat_flows.py`.
- **Ablehnungen** (Waffen, Selbstverletzung, Hassrede …) sind kurz, ohne Belehrung, mit einem hilfreichen Ausweg.

## Schreibbausteine

- **Ein neuer Zweck** in `writing.yaml` → `purposes` braucht:
  - `keys` (Regex auf den Zwecktext);
  - `subject` (≥ 2 Varianten);
  - `formal` und `casual`, jeweils mit `open`, `body` und `close`.
- **Platzhalter:** `{greeting} {name} {recipient} {date} {date_phrase} {topic} {item} {content}`.
- **Ein Test** in `tests/test_chat_writing.py` mit einer realistischen Anfrage.
