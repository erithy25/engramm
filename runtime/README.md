# ENGRAMM Laufzeit und Desktop-App (Chat v3, Phasen 3 und 7)

| Ordner | Inhalt |
|---|---|
| `core/` | Rust-Kern v0 (`engramm-core`): Paket-Manifest und Prüfung (Größe + SHA-256), Paket-Download mit Fortsetzen und festgenageltem Manifest (Feature `fetch`), deterministische Antwortwahl (SHAKE-256), Nachrichten-Normalisierung. Konform mit Python (`tests/test_runtime_core.py`). |
| `sidecar/` | Der ENGRAMM-Server als eingefrorenes Programm (PyInstaller, ein Ordner). Die App startet ihn mit `--desktop --pack … --memory …`. |
| `app/` | Tauri-2-App: Fenster, Einrichtungsseite beim ersten Start (`app/setup/`), Paket-Download nur nach Zustimmung, Start und Ende des Servers. |

## Was die App tut

1. **Beim Start** sucht sie ein Wissenspaket, in dieser Reihenfolge:
   - den gemerkten Ordner,
   - ein mitgeliefertes Paket (`resources/pack`),
   - ein früher geladenes Paket im App-Datenordner.

   Jede Datei wird auf Größe geprüft.
2. **Ohne Paket** bietet sie zwei Wege an:
   - den Download aus dem Katalog (`resources/catalog.json`), nur nach Klick und Rückfrage;
   - einen Paket-Ordner auf dem Rechner, der offline funktioniert, etwa von einem USB-Stick. Dabei wird jede Datei per SHA-256 geprüft.
3. **Mit Paket** startet sie den Server:
   - Der Server meldet `ENGRAMM_URL=…`, dann zeigt das Fenster den Chat (`?desktop=1`).
   - Für Tauri ist die Chat-Seite eine entfernte Seite ohne Zugriff auf App-Befehle.
   - Quellen-Links öffnet der Server im System-Browser, nur Wikipedia und Wikidata.
4. **Beim Beenden** schließt die App die Standardeingabe des Servers, und der Server beendet sich. Stürzt die App ab, schließt das Betriebssystem die Leitung, mit derselben Wirkung.

Netzverkehr gibt es nur beim Download, den der Nutzer startet. Es gibt keine Update-Prüfung und keine Telemetrie.

## Bauen

Lokal braucht Tauri die System-WebView-Entwicklerpakete. Unter Linux sind das `libwebkit2gtk-4.1-dev` und `libgtk-3-dev`. Die Installer baut die CI (`.github/workflows/desktop.yml`) für Windows, macOS (arm64 und x64) und Linux:

```bash
pip install -r runtime/sidecar/requirements.txt
pyinstaller --noconfirm --distpath build/sidecar --workpath build/pyi runtime/sidecar/engramm-server.spec
mkdir -p runtime/app/src-tauri/resources/sidecar && cp -R build/sidecar/engramm-server/. runtime/app/src-tauri/resources/sidecar/
python runtime/sidecar/smoke_test.py runtime/app/src-tauri/resources/sidecar
(cd ui && npm ci && npm run build)
cd runtime/app && npm install && npx tauri icon ../../desktop/build/icon.png && npx tauri build
```

Entwicklung ohne eingefrorenen Server: `ENGRAMM_HOME=/pfad/zu/engramm npx tauri dev`. Die App startet dann `python -m engramm.app` aus der `.venv`.

## Wissenspaket veröffentlichen

```bash
python -u -m experiments.reading_abstracts --top 1500000        # Artikelanfänge nach Popularität
python -u -m experiments.pack_build --name lite --abstracts /dev/shm/engramm/reading/abstracts.jsonl \
    --top 400000 --kb /dev/shm/engramm/kb/final/kb.sqlite --out /dev/shm/engramm/packs/lite
python -u -m experiments.pack_release --pack /dev/shm/engramm/packs/lite --out /dev/shm/engramm/release/lite
gh release create pack-lite-3.0.0 /dev/shm/engramm/release/lite/*   # bewusster, manueller Schritt
```

`pack_release` schreibt den Katalogeintrag. Die SHA-256 des Manifests nagelt genau dieses Paket fest.

## Offen (ehrlich)

- **Signatur:** Ohne Apple-Developer-Konto und Windows-Zertifikat warnen macOS und Windows beim ersten Start.
  - Nötige Secrets: `APPLE_CERTIFICATE`, `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID` und ein Windows-Zertifikat.
  - Die ed25519-Signatur des Katalogs ist geplant; heute schützt die festgenagelte Manifest-SHA-256.
- **Rust-Laufzeit:** Suche, Antwortextraktion und Gesprächsschicht laufen noch in Python, also im Sidecar. Der Rust-Kern deckt bisher Pakete, Download, Antwortwahl und Normalisierung ab.
  - Der volle Port (Plan: 10.000-Züge-Konformität) steht aus.
- **Schwache Testrechner (W-LOW):** noch nicht gemessen. Gemessen ist der Container, siehe `docs/EXPECTATIONS.md`.
