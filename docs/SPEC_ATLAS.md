# SPEC — ENGRAMM Atlas: privates Webwissen ohne neuronales Netz, ohne Server (Stand 2026-10-01)

Plan: `/root/.claude/plans/zippy-nibbling-feigenbaum.md`. Messung: `docs/PREREG_SEARCH_V0.md`, Ergebnisse in `docs/EXPECTATIONS.md`.

## Grundsatz

**Das Gehirn bleibt lokal, das Internet ist nur eine stumme Festplatte.**
- ENGRAMM sucht ausschließlich auf dem eigenen Rechner.
- Ins Netz gehen nur Abrufe, aus denen niemand die Frage ablesen kann.
- Eine Suchmaschine oder KI-API wird nie kontaktiert.
- Standard ist **offline**: Alle drei Kanäle sind aus, bis der Nutzer sie einzeln einschaltet.

## Die drei Kanäle

| Kanal | Name im Code | Was geht hinaus | Wer sieht was | Server |
|---|---|---|---|---|
| K1 Regal | `shelf` | HTTP-Range-Abruf eines Fachs fester Größe aus einem Volume, dazu 2 Tarn-Fächer | Host: IP (ohne Tor) und Fach-Nummern; jedes Fach mischt ~1.000 per Hash verteilte, thematisch unverbundene Artikel | statische Release-Dateien (GitHub, Spiegel) |
| K2 Abo | `feeds` | zeitgesteuerter Abruf ausgewählter RSS/Atom-Feeds, unabhängig von Fragen | Feed-Betreiber: „dieser Rechner liest Feed X“ | Feeds der Verlage |
| K3 Bote | `messenger` | GET einer vom lokalen Wegweiser gewählten Seite, standardmäßig über Tor | Zielseite: ein anonymer Besuch ohne Suchbegriff; Tor-Ausgang: die Zielseite | keiner |

## Netz-Tor (`egress`)

- **Ein einziger Weg nach draußen:** `engramm/web/egress.py` mit zwei Backends.
  - **Rust** (`engramm-core egress`, mit dem Sidecar ausgeliefert): ein Dienst über stdin/stdout mit JSON-Zeilen. In der App öffnet Python selbst keine Sockets.
  - **Python** (`urllib`): Entwicklungsbetrieb und Tests; gleiche Regeln, kein Tor.
- **Regeln für jeden Abruf:**
  - nur `https` (Loopback nur in Tests, wenn ausdrücklich erlaubt);
  - nur `GET`, keine Cookies, keine Weiterleitung zu einem Host außerhalb der Kanal-Liste;
  - fester User-Agent `ENGRAMM/3.1 (+offline assistant)`, Größen- und Zeitlimit.
  - **Bote:** keine IP-Literale aus privaten Netzen und keine Hostnamen `localhost` oder `*.local` (kein Zugriff aufs Heimnetz).
- **Netzprotokoll:** jeder Abruf als JSON-Zeile in `network.log` neben dem Gedächtnis-Log.
  - Felder: `ts`, `channel`, `host`, `what`, `bytes`, `status`, `via` (direct oder tor), `ok`.
  - `what` beschreibt nur, was geholt wurde (z. B. `bucket 1834`, `feed bbc-world`, `page`), nie den Fragetext.
  - Die Oberfläche zeigt das Protokoll an (`GET /api/network`).
- **Einstellungen:** `network.json` neben dem Gedächtnis-Log. Format:
  ```json
  {"version": 1, "channels": {"shelf": {"enabled": false, "tor": false},
   "feeds": {"enabled": false, "feeds": ["bbc-world"]}, "messenger": {"enabled": false, "tor": true}}}
  ```

### Protokoll `engramm-core egress`

Eine Zeile pro Anfrage auf stdin, eine Zeile pro Antwort auf stdout (UTF-8 JSON):

```
→ {"id": 7, "channel": "shelf", "url": "https://…/shelf-0.bin", "range": [1048576, 2097151],
   "max_bytes": 1100000, "what": "bucket 1", "allow_hosts": ["github.com", "objects.githubusercontent.com"],
   "tor": false}
← {"id": 7, "ok": true, "status": 206, "bytes": 1048576, "body_b64": "…", "via": "direct", "final_host": "…"}
← {"id": 8, "ok": false, "error": "host not allowed: example.org"}
```

- Den Start ruft `engramm-core egress --log PATH` auf.
- Der Dienst endet, wenn stdin geschlossen wird.
- Tor (`"tor": true`) braucht das Feature `tor` (Arti). Ohne dieses Feature antwortet der Dienst mit `ok: false, error: "tor unavailable"`, und der Bote bleibt aus.

## Regal (K1)

- **Quelle:** der wöchentliche CirrusSearch-Dump der englischen Wikipedia (Klartext, Weiterleitungen;
  `experiments/cirrus_extract.py`). Nur Artikel (Namensraum 0, keine Begriffsklärungen) mit ≥ 300 Zeichen;
  die Literatur- und Linkzone am Artikelende wird regelbasiert abgeschnitten (`engramm/web/clean.py`,
  `strip_references`; Shard 0: 31 % weniger Text).
- **Volumes:** `shelf-<n>.bin` (bzw. `s<NN>-shelf-<n>.bin` beim Teilbau), jedes < 2 GiB, aus festen Fächern
  zu je `bucket_bytes` (Standard 1 MiB).
- **Fach:** `EGB1` | u32 Länge | LZMA(JSON-Lines `{"t","s","x","d"}`) | Nullbytes bis zur vollen Fachgröße.
  - Ohne `first`/`buckets` je Volume liegt Fach `b` in Volume `b // per_volume` am Offset
    `(b % per_volume) · bucket_bytes`; mit ihnen (zusammengeführtes Regal) im Volume, dessen Bereich `b` enthält.
- **Zuordnung:** Artikel → Fach per SHAKE-256(Titel), bei Überlauf das nächste Fach mit Platz; ein Fach, das
  komprimiert nicht passt, kürzt seinen längsten Artikel (gezählt im Manifest). Die Zuordnung steht nur im
  lokalen Index.
- **Manifest** `shelf.json`: `version`, `bucket_bytes`, `per_volume`, `buckets`, `volumes` (Name, Bytes,
  SHA-256, `first`, `buckets`), `bucket_sha256`, `licenses`, `built`, `docs`, optional `signature`.
  - Das Manifest kommt mit dem Wissenspaket, dessen Manifest-SHA-256 der Katalog im Installer pinnt.
- **Lokaler Index** (im Paket, `shelf_index/`, alles speicherabgebildet, Format 2):
  `titles.bin` + `title_off.npy` (u32), `bucket.npy` (u16), Namensformen `name_hash.npy` (u64, Titel und
  Weiterleitungen; Lite: nur Titel) + `name_doc.npy`, Schlüsselterme `term_hash.npy` (untere 32 Bit des
  BLAKE2b-Hashes) + `ptr.npy` + `post.npy` + `idf.npy` (float16). Je Artikel die Titelwörter und 8
  Schlüsselterme (tf·idf, die ersten 600 Zeichen dreifach).
  - Gemessen an Shard 0 (96.648 Artikel): 11,7 MB. **Gemessen am ganzen Regal `shelf-20260927`
    (6.369.076 Artikel, 7.425 Fächer):** Index 0,53 GB (Lite, nur Titel) bzw. 0,63 GB (mit Weiterleitungen,
    7,2 Mio. Namensformen); Lite-Paket mit Regal-Index 1,24 GB.
  - Gleiche Namensformen („Albert Einstein“, „Albert Einstein (album)“) bleiben alle im Index; der Client
    nimmt den genau so betitelten Artikel, sonst einen ohne Zusatz.
- **Bau in der CI** (`.github/workflows/shelf.yml`): ein Teil-Regal je Dump-Shard in parallelen Jobs, Volumes
  direkt als Assets des Releases `shelf-<Datum>`; danach führt `experiments/shelf_merge.py --index-only` nur die
  Index-Teile zusammen (globale idf). Gemessen je Shard: Extraktion 232 s (ein Kern), Bau 172–348 s.
  **Erster vollständiger Lauf** (Run 2, 16 Gruppen × 4 Shards): 17–31 min je Gruppe, gesamt ≈ 60 min;
  66 Teil-Regale, 9,7 GB Volumes, 201 Release-Assets.
- **Client** (`engramm/web/shelf.py`):
  1. Artikel wählen: Namensformen aus der Frage (auch Weiterleitungen wie „xHCI“) zählen stark, dazu
     Schlüsselterme; nur Artikel mit ≥ 40 % des besten Treffers;
  2. deren Fächer plus 2 Tarn-Fächer (aus einem Geheimnis je Installation und einem Zähler, nie aus der
     Frage) in zufälliger Reihenfolge laden, optional über Tor;
  3. jede SHA-256 prüfen, Fehlschläge verwerfen;
  4. alles im LRU-Cache `shelf_cache/` behalten (Standard 500 MB).
- **Signatur:** Ed25519 (RFC 8032, `engramm/web/ed25519.py`, reines Python) über die kanonische JSON-Form
  des Manifests ohne `signature`. Öffentliche Schlüssel in `engramm/web/release_keys.txt`;
  `scripts/sign_manifest.py` erzeugt Schlüssel und signiert; die CI signiert nur mit dem Secret
  `ENGRAMM_SIGNING_KEY`. Steht ein Schlüssel in der App, nutzt sie nur ein von ihm signiertes Manifest.
  **Stand:** noch kein Schlüssel hinterlegt; bis dahin schützt allein die gepinnte Paket-Prüfsumme
  (Kette: Installer-Katalog → Paket-Manifest → `shelf.json` → SHA-256 je Fach).
- **Schlüssel einrichten (Eigentümer, einmalig, ≈ 2 Minuten):**
  1. `python scripts/sign_manifest.py --keygen` gibt ein Schlüsselpaar aus.
  2. Den geheimen Teil als Repository-Secret `ENGRAMM_SIGNING_KEY` hinterlegen (GitHub → Settings → Secrets and
     variables → Actions).
  3. Den öffentlichen Teil als eine Zeile in `engramm/web/release_keys.txt` committen.
  4. `shelf.yml` neu laufen lassen; ab dann nimmt die App nur noch ein so signiertes Regal-Manifest an.

  Ende-zu-Ende geprüft (2. Oktober 2026, Wegwerf-Schlüssel, nichts gespeichert) mit dem echten Manifest von
  `shelf-20260927`:
  - signiert → die Prüfung gelingt mit dem eigenen Schlüssel,
  - sie schlägt mit einem fremden Schlüssel fehl,
  - ein verändertes Manifest wird abgelehnt.

## Abo (K2)

- Die Feed-Liste in `data/feeds.yaml` ist kuratiert, mit Lizenz- und Nutzungshinweis je Feed. Der Nutzer wählt aus.
- **Zeitplan:** alle 3 Stunden mit ±30 % Zufallsversatz, unabhängig von Fragen. Nur RSS 2.0 und Atom, maximal 2 MB je Abruf.
- **Parser:** XML ohne DTD und ohne Entitäten; eine Nachricht mit `<!DOCTYPE` oder `<!ENTITY` wird verworfen.
- **Speicher:** `feeds.sqlite` mit FTS5 (BM25) über Titel und Zusammenfassung.
  - Alter fließt als Abschlag in den Rang (Halbwertszeit 3 Tage). Einträge älter als 30 Tage werden gelöscht.
- **Antwort:** „Laut <Feed>, <Datum>: …“ mit Link.

## Wegweiser und Bote (K3)

- **Wegweiser** (im Paket, `wayfinder.sqlite`): Entität → offizielle Website (Wikidata P856, DBpedia homepage) sowie Belegadressen aus Wikipedia.
- **Bote:**
  1. 1–3 Seiten über Tor laden, höchstens 2 MB, nur `text/html`;
  2. regelbasierte Textbereinigung (`engramm/web/clean.py`, jusText-Ansatz: Absatzlänge, Linkdichte, Stoppwortanteil);
  3. Sätze in die bestehende Antwortextraktion geben.

## Antworten (A4)

- **Eskalation:** lokal (Faktenbank, Artikelanfänge) → Feeds → Regal → Bote. Fragen nach Aktuellem
  (current/latest/now/today/2023+) gehen zuerst an die Kanäle; persönliche Fragen (I/me/my) nie.
- Die Sätze der Kanäle laufen als zusätzliche Kandidaten durch `ChatBot._lookup` (`extra_rows`), mit
  denselben Merkmalen wie lokale Sätze: Abdeckung (der Artikeltitel gilt in jedem seiner Sätze als genannt),
  Phrasen, Nähe, Titel als Schlüsselwörter, Dokument- und Kontextabdeckung (zwei Sätze davor). Fragewörter
  zählen nicht; die Lebensdaten nach dem Namen im ersten Satz gelten als „born/died“. Die ersten zwei Sätze
  jedes Artikels sind immer Kandidaten, Literaturzeilen nie.
- **Konfidenz:** eigenes Modell für Netz-Sätze (`engramm/web/atlas_calib.json`, gemitteltes Perzeptron
  wie `engramm/chat/calib.py`, `experiments/atlas_calib.py`). Entwicklungsmessung (verbrauchte Daten,
  kein Testlauf): 11.046 SQuAD-train-Fragen (25 je Artikel, 442 Artikel in ihrer heutigen Fassung unter
  96.648 Ablenkern aus Shard 0) durch den echten Pfad (lokaler Server, Tarn-Fächer).
  - Gefragter Artikel unter den Kandidaten: 41 % aller Fragen, 88 % der Fragen, die ihren Artikel nennen.
  - Das lokale Modell beantwortete Regal-Sätze mit nur 59,7 % exakter Präzision → nicht brauchbar.
  - Neues Modell, Label „Token-F1 ≥ 0,5“, θ = 13,45 für ≥ 90 % auf 20 % zurückgehaltenen Artikeln:
    22 von 24 kurzen Antworten richtig (91,7 %), Abdeckung 1,1 %. Exakte Übereinstimmung erreicht auch
    oben nur ≈ 60–65 % — die kurze Spanne ist die Grenze, nicht die Suche.
- **Zitat statt Raten:** ist das Modell unsicher, stammt der beste Satz aber aus dem Artikel, den die Frage
  nennt, und enthält er ihre übrigen Wörter, antwortet ENGRAMM mit diesem Satz, Quelle und Stand
  („Here's what Wikipedia's article “Nik Nanos” says: “… (born 1964) …” (as of 2026-09-11)“), in
  wechselnden Formulierungen (`daily.atlas_quote`). Ende-zu-Ende-Batterie (12 Fragen, Lite-Paket + echtes
  Regal aus Shard 0): vorher 5 richtig, 2 falsch; jetzt 2 kurz und sicher, 7 belegte Zitate, 1 aus der
  Faktenbank, 2 ehrlich „weiß nicht“, 0 falsch.
- Quelle `shelf` | `feed` | `web` mit `as_of`; die Antwort nennt Quelle und Stand, die Oberfläche den Kanal.
- **Quellen-Abgleich (offen):** Übereinstimmung mehrerer unabhängiger Quellen und Widerspruchsanzeige sind
  noch nicht gebaut; heute zählt nur die Stimmenverteilung über die besten Sätze.
- **Bei ausgeschalteten Kanälen** sind die Antworten identisch mit v3 und es gibt 0 Abrufe
  (`tests/test_web_atlas.py`).

## Pakete (A2), gemessen im Release-Lauf 36953606047 (2. Oktober 2026)

| Paket | Inhalt | Größe (gemessen) | Schwelle (vorab) |
|---|---|---|---|
| Lite | 400 k Artikelanfänge, Faktenbank-Auszug, Regal-Index lite (530 MB) | ≈ 1,25 GB (Artefakt 2,50 GB = Paketdateien + dasselbe Paket als Zip) | — |
| Standard | 1,5 Mio. Artikelanfänge, 1 Mio. Faktenbank-Einträge, voller Regal-Index (626 MB), Wegweiser | **2,73 GB** in 37 Dateien (größte: post.npy 584 MB, doc_post.npy 438 MB, kb.sqlite 406 MB, corpus.u16 392 MB) | ≤ 4,5 GB — eingehalten |

Bauzeit auf GitHub-Runnern: Lite 63 min, Standard 49 min. Lite im Container gemessen: Spitzen-RSS 555 MB,
p95 0,093 s; Standard aus dem Release: Spitzen-RSS 1.053 MB, p95 0,174 s (Schwellen ≤ 1,5 GB / ≤ 1,5 s
eingehalten; alle 36 Dateien gegen das Manifest geprüft). Unter einer harten Speichergrenze (cgroup, 1,5 GiB und
3 GiB) liefen beide Pakete ohne ein einziges Erreichen der Grenze (Standard: Spitzen-RSS 1.073 MB, p95 0,055 s;
Details in EXPECTATIONS.md). Offen: dieselbe Messung auf echter 4-GB-Hardware mit Festplatte. Die Installer jenes Laufs wurden abgebrochen, weil ein gleichzeitiger Push den
Installer-Job aus der gemeinsamen Concurrency-Gruppe verdrängte; seitdem hat der aus dem Release
aufgerufene Desktop-Bau eine eigene Gruppe, und `release/request.json` kann mit `reuse_run` die Pakete
eines früheren Laufs übernehmen und nur die Installer neu bauen.

Veröffentlichte Vorabversionen mit diesen Paketen (alle mit 45 Dateien, darunter 6 Installer für 3.1.0 — deb, rpm,
dmg arm64/x64, exe, msi — und SHA256SUMS.txt, nach jedem Lauf nachgeprüft):
[v3.1.0-beta.8](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.8) (Lauf 36976863912, Batterien 34–40),
[v3.1.0-beta.9](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.9) (Lauf 36978307456, Pronomen nach Person
und Geschlecht), [v3.1.0-beta.10](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.10) (Lauf 36982843776,
Batterien 41–42: Deutsch, Kontext über mehrere Züge, Turniere, Amtsinhaber),
[v3.1.0-beta.11](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.11) (Lauf 36985675889, Batterien 43–44:
Umgangssprache, Korrekturen, Planeten, deutscher Alltagskontext, WM auf Deutsch),
[v3.1.0-beta.12](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.12) (Lauf 36989493546, Batterien 45–46:
Gedächtnis, Tippfehler, Folgefragen, Stimmung, Sarkasmus, deutsche Amtsinhaber),
[v3.1.0-beta.13](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.13) (Lauf 36992597545, Batterien 47–48:
Reise, Folgefragen für Alltagsfakten, Gesundheit, Geld, Arbeit, Geschenke, Entscheidungen). beta.14 (Lauf 36996025621)
scheiterte nur beim Hochladen („other side closed“ nach 45 von 46 Dateien, alle Installer gebaut und getestet); der
Veröffentlichungsschritt versucht es seitdem nach einer Minute ein zweites Mal.
[v3.1.0-beta.15](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.15) (Lauf 36999697063, Batterien 49–54,
Amtsinhaber aus dem eigenen Artikel).
[v3.1.0-beta.16](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.16) (Lauf 37001703138, Batterie 55:
Werk-Kontext; „who wrote it?“ ist nie Stephen Kings „It“; 45 Dateien, 6 Installer, SHA256SUMS geprüft).
[v3.1.0-beta.17](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.17) (Lauf 37009258108, Batterien 56–59:
Wissens-Folgefragen, Alltagsmomente Englisch/Deutsch, Tastatursalat, Folgefragen mit Bezug auf den Satz davor; 45 Dateien,
6 Installer, SHA256SUMS geprüft, Upload im ersten Versuch).
[v3.1.0-beta.18](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.18) (Lauf 37019401500, Batterien 60–63:
normaler Abend Englisch/Deutsch, Sprachumschaltung, Rechnen nebenbei, Tagesplan, Folgefragen auf Deutsch; 45 Dateien,
6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.19](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.19)
(Lauf 37028902789, Batterien 64–67: schwere Gefühle mit Hilfsangeboten, Gedächtnis wie ein Mensch – echtes Vergessen,
Korrekturen, Abneigungen, Personen, verschobene Termine –, auch auf Deutsch; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.20](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.20)
(Lauf 37043931947, Batterien 68–71: lockeres Gespräch auf Englisch und Deutsch, echte Nachrichten mit Slang und Emojis,
Wissensfehler behoben – Zugspitze, Harry Potter –, 40 feste Wissensfragen 39/0/1; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.21](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.21)
(Lauf 37052761578, Batterien 72–74: zweite Wissensstichprobe 38/0/2, Allergie kein Lieblingsessen, flüchtige Momente nicht
gespeichert, Folgefragen über mehrere Turns; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.22](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.22)
(Lauf 37061506271, Batterien 75–78: Alltagsrechnungen, Ironie, dritte Wissensstichprobe 40/0/0, ein ganzer Abend im
Gespräch; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.23](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.23)
(Lauf 37074474964, Batterien 79–81: 40 echte Einzelnachrichten, Zustände von Dingen auf Englisch und Deutsch, Schmerzen
mit Rat; erster Lauf 37069930936 hing beim Herunterladen der Paket-Artefakte, der Reuse-Job hat seitdem 20 Minuten
Zeitlimit; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.24](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.24)
(Lauf 37080858238, Batterien 82–86: Ereignisse in der Ich-Form, Sicherheitsnetz für Bestätigungen, vierte
Wissensstichprobe 39/40, natürliche Mehrschritt-Gespräche mit Haustier-Gedächtnis; 45 Dateien, 6 Installer,
SHA256SUMS geprüft). [v3.1.0-beta.25](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.25)
(Lauf 37085969483, Batterien 87–89: Korrekturen gelten, Deutsch im Alltag, Trauer/Schlaf/Langeweile, Grundwörter in
sechs Sprachen, Nationalität ja/nein; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.26](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.26)
(Lauf 37091404744, Batterien 90–94: fünfte Wissensstichprobe 40/0/0, Grenzfälle, deutsches Wissen mit Folgefragen,
Wächter gegen falsche Baujahre, englische Verallgemeinerungsprobe; 45 Dateien, 6 Installer, SHA256SUMS geprüft).

## Bedrohungsmodell und ehrliche Restrisiken

- **Geschützt:**
  - Fragetexte: Sie verlassen den Rechner nie.
  - Gesprächsinhalte und Gedächtnis: Sie bleiben lokal.
  - Profilbildung durch einen Vermittler: Es gibt keinen.
- **Nicht geschützt:**
  - Regal ohne Tor: Der Host sieht die IP und die Fach-Nummern. Über viele Fragen hinweg sind Schnittmengen-Angriffe denkbar; Tarn-Fächer und der Cache erschweren sie.
  - Abo: Feed-Betreiber sehen die IP.
  - Bote: Der Tor-Ausgang sieht die Zielseite.
