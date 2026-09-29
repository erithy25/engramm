# ENGRAMM Desktop-App

Ein Fenster um den lokalen ENGRAMM-Chat (`python -m engramm.app`). Die App startet den Server selbst,
zeigt beim Laden das Logo und beendet den Server beim Schließen. Quellen-Links öffnen im normalen Browser.

## Voraussetzungen

- Der ENGRAMM-Ordner mit Python-Umgebung (`.venv`) und den gebauten Daten:
  - `models/lm/main/model` (Sprachmodell),
  - `models/lm/main/chat3` und `chat4` (Satzindex).
- Node.js ≥ 20.

## Starten (Entwicklung)

```bash
cd desktop
npm install
npm start
```

## Als App bauen

```bash
npm run dist:mac      # → dist/ENGRAMM-0.1.0.dmg   (auf einem Mac bauen)
npm run dist:win      # → dist/ENGRAMM Setup 0.1.0.exe
npm run dist:linux    # → dist/ENGRAMM-0.1.0.AppImage
```

Die gebaute App enthält nur das Fenster, nicht die ~10 GB Daten. Beim ersten Start sucht sie den
ENGRAMM-Ordner in dieser Reihenfolge:
1. in der Umgebungsvariable `ENGRAMM_HOME`,
2. im zuletzt gewählten Ordner,
3. im Ordner über `desktop/`,
4. sonst fragt sie einmal per Dialog.

Das Python der Umgebung wird unter `.venv` erwartet, sonst gilt `ENGRAMM_PYTHON`.

Ohne Desktop-App geht es auch im Browser: `python -m engramm.app` öffnet http://127.0.0.1:8770.

Das Icon (`build/icon.png`, 1024 px) ist aus `engramm/app/web/logo.svg` gerendert.
