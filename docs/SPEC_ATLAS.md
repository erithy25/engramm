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

- **Volumes:** `shelf-<n>.bin`, jedes < 2 GiB, aus festen Fächern zu je `bucket_bytes` (Standard 1 MiB).
- **Fach:** zstd-komprimiertes JSON-Lines-Dokument (`{"t": Titel, "s": Quelle, "x": Text}` je Zeile), mit Nullbytes auf die volle Fachgröße aufgefüllt.
  - Fach `b` liegt in Volume `b // per_volume` am Offset `(b % per_volume) · bucket_bytes`.
- **Zuordnung:** Artikel → Fach per SHAKE-256(Titel), bei Überlauf das nächste Fach mit Platz.
  - Artikel, die größer als ein Fach sind, werden auf ihre ersten `bucket_bytes` gekürzt.
  - Die Zuordnung steht im lokalen Regal-Index, nicht im Fach.
- **Manifest** `shelf.json` legt fest: `version`, `bucket_bytes`, `per_volume`, `buckets`, `volumes` (Name, Bytes, SHA-256), `bucket_sha256` (Liste), `licenses`, `built`, optional `signature` (ed25519, siehe unten).
  - Der Katalog der App pinnt die SHA-256 des Manifests, wie beim Wissenspaket.
- **Lokaler Regal-Index** (im Paket, `shelf_index/`):
  - `titles.txt` mit `bucket.npy`;
  - Schlüsselterme je Artikel als invertierte Liste (`terms.txt`, `ptr.npy`, `post.npy`);
  - BM25 über Titel und Schlüsselterme.
- **Client** (`engramm/web/shelf.py`):
  1. die Top-k-Artikel wählen;
  2. deren Fächer plus 2 Tarn-Fächer (SHAKE-256 aus Gesprächs-ID und Zähler, nicht aus der Frage) in zufälliger Reihenfolge laden;
  3. jede SHA-256 prüfen, Fehlschläge verwerfen;
  4. alles im LRU-Cache `shelf_cache/` behalten (Standard 500 MB).
- **Signatur** (für spätere Paket-Updates): ed25519 über die kanonische JSON-Form des Manifests ohne `signature`.
  - Der öffentliche Schlüssel liegt in `runtime/keys/release.pub`.
  - CI signiert nur, wenn das Secret `ENGRAMM_SIGNING_KEY` gesetzt ist.
  - Ohne Signatur gilt allein die gepinnte SHA-256 aus dem Installer-Katalog, und Updates werden nicht angeboten.

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

- **Eskalation:** lokal (Faktenbank, Abo, Artikelanfänge) → Regal → Bote.
- **Kriterium:** Die nächste Stufe läuft nur, wenn die Konfidenz unter θ liegt oder die Frage nach Aktuellem fragt (current/latest/now/today/2025+).
- Alle Kandidatensätze laufen durch `ChatBot._lookup`. Quellen-Art: `shelf` | `feed` | `web`, mit `as_of`.
- **Quellen-Abgleich:** Stimmen zwei unabhängige Quellen überein, steigt die Konfidenz. Bei Widerspruch nennt ENGRAMM beide mit Datum.
- **Bei ausgeschalteten Kanälen** sind die Antworten identisch mit v3 (Digest-Test).

## Bedrohungsmodell und ehrliche Restrisiken

- **Geschützt:**
  - Fragetexte: Sie verlassen den Rechner nie.
  - Gesprächsinhalte und Gedächtnis: Sie bleiben lokal.
  - Profilbildung durch einen Vermittler: Es gibt keinen.
- **Nicht geschützt:**
  - Regal ohne Tor: Der Host sieht die IP und die Fach-Nummern. Über viele Fragen hinweg sind Schnittmengen-Angriffe denkbar; Tarn-Fächer und der Cache erschweren sie.
  - Abo: Feed-Betreiber sehen die IP.
  - Bote: Der Tor-Ausgang sieht die Zielseite.
