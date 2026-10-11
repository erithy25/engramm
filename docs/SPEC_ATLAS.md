# SPEC — ENGRAMM Atlas: Webwissen ohne neuronales Netz, ohne eigene Server (Stand 2026-10-10)

Plan: `/root/.claude/plans/zippy-nibbling-feigenbaum.md`. Messung: `docs/PREREG_SEARCH_V0.md`, Ergebnisse in `docs/EXPECTATIONS.md`.

## Grundsatz

**Das Gehirn bleibt lokal.** Lesen, Auswählen und Antworten geschieht auf dem eigenen Rechner, ohne KI-API.
- Regal und Abo schicken nie eine Frage hinaus: Niemand kann sie aus ihren Abrufen ablesen.
- **Die Websuche (seit 3.2) ist die eine Ausnahme:** Sie schickt die Frage an eine Suchmaschine (DuckDuckGo,
  Bing, auf Wunsch die Brave-Search-API) und liest die besten Treffer hier; DuckDuckGos Faktenbox bekommt nur
  den Namen des Gefragten („Siemens“), nicht die Frage.
- **Standard (seit 3.2.0-beta.8, Entscheidung des Eigentümers am 10.10.2026):** Die Websuche ist ab Werk
  **an**. ENGRAMM sucht von selbst, wenn es offline keine Antwort hat oder die Frage nach Aktuellem fragt;
  persönliche Fragen nie. Ein Schalter schaltet sie ab; dann bietet ENGRAMM die Suche an („ja“ sucht), und
  „google …“ sucht trotzdem einmal. Regal und Abo sind aus, bis der Nutzer sie einschaltet.
- Der Tor-Bote von 3.1 ist entfernt (jeder Abruf scheiterte, „no HTTP header“; Arti fiel aus dem Build).

## Die drei Kanäle

| Kanal | Name im Code | Was geht hinaus | Wer sieht was | Server |
|---|---|---|---|---|
| K1 Regal | `shelf` | HTTP-Range-Abruf eines Fachs fester Größe aus einem Volume, dazu 2 Tarn-Fächer | Host: IP (ohne Tor) und Fach-Nummern; jedes Fach mischt ~1.000 per Hash verteilte, thematisch unverbundene Artikel | statische Release-Dateien (GitHub, Spiegel) |
| K2 Abo | `feeds` | zeitgesteuerter Abruf ausgewählter RSS/Atom-Feeds, unabhängig von Fragen | Feed-Betreiber: „dieser Rechner liest Feed X“ | Feeds der Verlage |
| K3 Websuche | `search` | die Frage als Suchanfrage an eine Suchmaschine, dann bis zu 3 Trefferseiten | Suchmaschine: Frage und IP; Trefferseiten: ein Besuch ohne Suchbegriff | keiner (Suchmaschinen Dritter) |

## Netz-Tor (`egress`)

- **Ein einziger Weg nach draußen:** `engramm/web/egress.py` mit zwei Backends.
  - **Rust** (`engramm-core egress`, mit dem Sidecar ausgeliefert): ein Dienst über stdin/stdout mit JSON-Zeilen. In der App öffnet Python selbst keine Sockets.
  - **Python** (`urllib`): Entwicklungsbetrieb und Tests; gleiche Regeln.
- **Regeln für jeden Abruf:**
  - nur `https` (Loopback nur in Tests, wenn ausdrücklich erlaubt);
  - nur `GET`, keine Cookies, keine Weiterleitung zu einem Host außerhalb der Kanal-Liste;
  - fester User-Agent `ENGRAMM/3.1 (+offline assistant)`, Größen- und Zeitlimit; für die Websuche der eines
    Browsers (Suchmaschinen und viele Seiten weisen andere Clients ab);
  - zusätzliche Header nur `Accept`, `Accept-Language` und `X-Subscription-Token` (Brave-Schlüssel), ohne
    Steuerzeichen;
  - **Websuche:** keine IP-Literale aus privaten Netzen und keine Hostnamen `localhost` oder `*.local` (kein
    Zugriff aufs Heimnetz). Ein ausgeschalteter Kanal lässt nur eine ausdrücklich verlangte Suche durch
    (`explicit`).
- **Netzprotokoll:** jeder Abruf als JSON-Zeile in `network.log` neben dem Gedächtnis-Log.
  - Felder: `ts`, `channel`, `host`, `what`, `bytes`, `status`, `via`, `ok`.
  - `what` beschreibt nur, was geholt wurde (z. B. `bucket 1834`, `feed bbc-world`, `search:bing`, `page`), nie den
    Fragetext; Fehlertexte verlieren ihre URL (sie trüge bei der Websuche die Frage).
  - Die Oberfläche zeigt das Protokoll an (`GET /api/network`).
- **Einstellungen:** `network.json` neben dem Gedächtnis-Log. Format:
  ```json
  {"version": 2, "channels": {"shelf": {"enabled": false},
   "feeds": {"enabled": false, "feeds": ["bbc-world"]},
   "search": {"enabled": true, "engine": "auto", "brave_key": ""}}}
  ```
  Einstellungen von 3.1 gelten weiter; der Bote entfällt, die Websuche bekommt ihren Standard (an), solange
  der Nutzer sie nicht abschaltet. Den Brave-Schlüssel gibt der Server nie zurück, nur `brave_key_set`.
  ```
  ```

### Protokoll `engramm-core egress`

Eine Zeile pro Anfrage auf stdin, eine Zeile pro Antwort auf stdout (UTF-8 JSON):

```
→ {"id": 7, "channel": "shelf", "url": "https://…/shelf-0.bin", "range": [1048576, 2097151],
   "max_bytes": 1100000, "what": "bucket 1", "allow_hosts": ["github.com", "objects.githubusercontent.com"],
   "headers": [], "timeout": 30}
← {"id": 7, "ok": true, "status": 206, "bytes": 1048576, "body_b64": "…", "via": "direct", "final_host": "…"}
← {"id": 8, "ok": false, "error": "host not allowed: example.org"}
```

- Den Start ruft `engramm-core egress --log PATH` auf.
- Der Dienst endet, wenn stdin geschlossen wird.
- Ein Dienst beantwortet eine Anfrage nach der anderen; für die Trefferseiten einer Suche startet `Egress`
  bis zu 4 Dienste und lädt parallel (`fetch_many`).
- Bekannte Grenze: ureq 2.12 schreibt hinter einem HTTP-Proxy (`HTTPS_PROXY`) die absolute URL in die
  Anfragezeile, auch im CONNECT-Tunnel; DuckDuckGo antwortet darauf mit 400. Ohne Proxy (Normalfall) nicht
  betroffen; mit Proxy bleiben Bing, Wikipedia und die Faktenbox. Abhilfe: ureq 3.
- Formulare (seit beta.9): Die Websuche darf ein Suchformular per POST schicken (`"form": [[k, v], …]`,
  höchstens 8 Felder, je ≤ 600 Zeichen; nur Kanal `search`), mit `Referer`/`Origin` wie das Suchfeld der
  Maschine. Nach einer Weiterleitung holt der Dienst die Antwort per GET. `"plain_agent": true` schickt auch
  auf dem Suchkanal ENGRAMMs eigenen User-Agent (Wikipedia und DuckDuckGos API wünschen das).

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
     Frage) in zufälliger Reihenfolge laden;
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

## Websuche (K3, `engramm/web/search.py`, `engramm/web/wiki.py`)

- **Antwortkette (seit beta.11, Nutzerbericht 11.10.2026: „er findet immer noch nichts, zu den einfachsten
  Sachen“ – „When was real madrid founded?“ endete mit „No page I read answers it…“).** Ursache: DuckDuckGo
  sperrte (202), Bing antwortete ohne Cookies auf das erste Wort („real“ → realtor.com, realapp.com,
  Merriam-Webster), keine der gelesenen Seiten trug Text. Die Suchmaschinen sind ohne Schlüssel das schwache
  Glied; deshalb laufen parallel zur Suche Quellen mit offizieller API:
  1. **Wikidata-Aussage** (`WikiKnowledge.answer`): Die Frage wird in Relation + Gegenstand zerlegt (40 Relationen
     EN/DE: gegründet, CEO, Präsident, Kanzler, Hauptstadt, Einwohner, Höhe, Länge, Autor, Trainer, Geburt …;
     Demonyme „German chancellor“ → Deutschland; „Bundeskanzler“ ohne Land → Deutschland). Der Gegenstand wird
     über `wbsearchentities` gefunden (nur Treffer, deren Name/Alias der gefragte ist; keine
     Begriffsklärungen), die Eigenschaft auf den ersten Treffern, die sie haben (`wbgetclaims`), die Namen in
     einem Aufruf (`wbgetentities`). „Aktuell“-Relationen nehmen die Aussage ohne Ende und mit begonnenem Start
     (bevorzugter Rang zuerst, Neuestes zuerst): Merz (seit 6.5.2025, Scholz endete am selben Tag), Kompany
     (seit 1.7.2024). Antwort als Satz („Real Madrid was founded on 6 March 1902.“), Quelle: der
     Wikipedia-Artikel.
  2. **Wikipedia-Zusammenfassung** für „What/Who is X“ / „Was/Wer ist X“ (REST `page/summary`, erste zwei Sätze).
  3. **Abstimmung** über Treffer und gelesene Seiten (`short_answer`, unten), dazu immer der zur Frage passende
     Wikipedia-Artikel als weitere Seite (Suche + Klartext-Extrakt).
  4. **Bester Abschnitt** einer Seite (Satz + Folgesatz) mit „According to <Seite>:“, sonst das beste Snippet.
  5. Nur wenn alles scheitert: „I couldn't find an answer online just now (DuckDuckGo: blocked; …)“.
  Keine Trefferliste und keine Fußzeile mehr; eine Quelle (Chip mit Link). Gemessen gegen echte, langsam
  aufgezeichnete Wikidata-Antworten (11.10.2026): Format, aktuelle Aussagen und Treffer stimmen; live prüft
  `scripts/answer_smoke.py` in CI 16 Fragen.
- **Wikimedia-Regeln (2026):** 200 Anfragen/Minute für Clients mit User-Agent samt Kontakt-URL, 10 ohne.
  ENGRAMMs User-Agent war „ENGRAMM/3.1 (+offline assistant)“ (ohne Kontakt → 10/min, daher die häufigen 429
  der Wikipedia-Ausweichsuche); jetzt „ENGRAMM/3.2 (https://engramm.vercel.app; https://github.com/erithy25/engramm)
  offline-assistant“ (Python und Rust gleich). Höchstens zwei gleichzeitige Wikimedia-Anfragen (erlaubt: drei);
  nach 429/503 eine Minute Pause. Hinaus gehen der Name des Gegenstands (Wikidata, Zusammenfassung) und die
  Stichwörter der Frage (Wikipedia-Suche); das Netzwerkprotokoll hält nur den Host.
- **Anzeige beim Warten:** `GET /api/progress?conversation=…` meldet die Stufe (search mit Frage, read mit den
  Seiten, write); die Seite fragt alle 350 ms und zeigt „Searching the web for “…” …“ / „Reading en.wikipedia.org,
  … …“ / „Writing the answer …“ (DE: „Suche im Web nach „…“ …“) mit Schimmer-Animation statt der Tipp-Punkte.
- **Lesen nach Passung (seit beta.11):** Die Treffer, die die Wörter der Frage nennen, werden zuerst gelesen (nicht
  realtor.com für „real madrid founded“), bei gleicher Passung Wikipedia zuerst, eine Seite mehr als nötig.

- **Wann:** ab Werk von selbst, wenn offline keine Antwort kommt oder die Frage nach Aktuellem fragt;
  „google …“, „search the web for …“, „such im Internet nach …“, „kannst du das googeln?“ immer (auch mit
  ausgeschaltetem Kanal); mit ausgeschaltetem Kanal „ja“ auf „Soll ich im Web danach suchen?“, das ENGRAMM
  nach einem „weiß ich nicht“ anbietet. Persönliche Fragen (ich/mein/du …) nie.
- **Suchmaschinen** („auto“, seit beta.9): Brave-Search-API (nur mit Schlüssel) → DuckDuckGo (HTML, dann
  lite) → Bing → Wikipedia-Suche. Je Maschine zwei Formen: die Frage wie getippt, dann Stichwörter mit dem
  Gefragten zuerst; **Bing bekommt die Stichwörter zuerst**: Einem Client ohne Cookies antwortet es nur
  auf das erste Wort („How tall is the Zugspitze“ → Wörterbuchseiten zu „tall“).
  Als „keine Antwort“ gelten eine Bot-Prüfung (Captcha, HTTP 202/403/429) und **Treffer, die nicht zur Frage
  passen**: Misstraut eine Maschine dem Client, liefert sie fremde Seiten („bitcoin kurs“ → ein Download,
  „who is the CEO of Siemens“ → nur Siemens-Startseiten). Bing muss streng passen (zwei Treffer, einer mit
  allen Wörtern); DuckDuckGo, Brave und Wikipedia antworten jedem Client gleich: ein passender Treffer
  genügt, und ein Tippfehler im Namen zählt als Treffer (ähnliche Schreibung ≥ 0,75: „Chatbt“ → ChatGPT).
- **Befund vom 10.10.2026 (Nutzerbericht, beta.8 auf Windows):** Jede Suche endete mit „no usable results“.
  Ursachen: DuckDuckGo beantwortet ein GET der Ergebnisseite seit 2026 mit HTTP 202 (Bot-Prüfung), das
  POST des Formulars (wie sein Suchfeld) mit den Treffern; Bings Ergebnisliste trug zusätzliche Klassen
  (`b_algo b_vtl_…`), die der Leser übersah; der Relevanztest verwarf richtige Treffer bei Tippfehlern.
  Alle drei behoben; live aus dem Rechenzentrum danach: OpenAI-CEO (mit Tippfehler „Chatbt“), Siemens-CEO,
  Zugspitze, Bitcoin-Kurs, Louvre-Öffnungszeiten, Champions-League-Sieger richtig beantwortet.
  Andere Maschinen ohne Schlüssel (Mojeek, Brave-HTML, Startpage, Ecosia, Yahoo) sperrten im Test alle
  Rechenzentrums-Adressen (403/429/JS-Prüfung) und sind keine Ausweichmöglichkeit.
- **Faktenbox:** Parallel zur Suche fragt ENGRAMM DuckDuckGos Instant-Answer-API (offiziell, ohne
  Schlüssel) nach dem Gefragten (`subject_phrase`: die zusammenhängenden Namenswörter, „Bayern München“).
  Zusammenfassung und Infobox („Siemens – Key people: Roland Busch (CEO)…“) gehen als Satzquelle in die
  Auswahl; scheitern alle Suchmaschinen, kann die Faktenbox allein antworten.
- **Lesen:** die ersten 3 lesbaren Treffer parallel (je 8 s, 2 MB; keine Videos, PDFs, sozialen Netze),
  Haupttext per `engramm/web/clean.py` (jusText-Ansatz, Stoppwörter Englisch und Deutsch).
- **Kurzantwort (seit beta.10, Nutzerbericht 10.10.2026: „er sucht nur Quellen, ich muss selbst lesen“):**
  ENGRAMM antwortet zuerst mit der Antwort als Satz, dann mit dem Satz, aus dem sie stammt, und der Quelle;
  die Trefferliste liegt eingeklappt dahinter („Web results (6)“) und ist nur offen, wenn es keine Antwort gibt.
  Ohne neuronales Netz, `short_answer` in `engramm/web/search.py`:
  - **Fragetyp** aus dem Wortlaut: Person (who/wer), Ort (where/Hauptstadt), Datum (when/wann), Maß (how
    tall/wie hoch), Anzahl (how many/Einwohner), Preis, Öffnungszeiten; sonst keine Kurzantwort („why …“).
  - **Kandidaten** dieses Typs aus bis zu 60 Sätzen (12 je Seite): Namen = Folgen großgeschriebener Wörter,
    an Titeln und Fragewörtern getrennt („President Donald Trump“ → „Donald Trump“); Zahlen mit Einheit, Daten.
  - **Abstimmung:** jeder Satz gibt seinem Kandidaten sein Gewicht (relativ zum besten Satz), mehr wenn der
    Kandidat im selben Satzteil wie ein Fragewort steht, je weitere Seite +40 %. Gegenwartsfragen („who is“,
    „currently“, „aktuell“) heben Sätze mit „current/incumbent/seit“ und senken „former/served from … to“.
  - **Schutz vor falschen Antworten** (gemessen an den Fallen des Live-Tests): Gewinner braucht 2 Sätze (oder
    eine Faktenbox-Zeile mit passendem Etikett) und das Doppelte des Zweiten (oder das 1,5-Fache bei dreimal so
    vielen Sätzen); eine Person ist ein voller Name (Varianten „Trump“, „Donald John Trump“ zählen für „Donald
    Trump“); kein Name ist, was die Seiten auch kleingeschrieben verwenden („cup“, „territory“), Institutionen
    („Cup“, „Amendment“), deutsche Substantivendungen, Teile des gefragten Namens („UEFA Europa League“), der
    gefragte Gegenstand selbst („ChatGPT“ für „Chatbt“). „Who won …“ ohne Jahr stimmt nicht ab: der meistgenannte
    Sieger ist der der Geschichte (Real Madrid), nicht der letzte. Anzahlen werden gerundet und datiert
    („About 3.5 million people live in Berlin (as of 2015).“), Zahlen innerhalb ±6 % sind eine Antwort.
  - **Satz zur Antwort:** englisch über `answer_sentence` („Donald Trump is currently the president of the
    USA.“), deutsch über Muster („Der aktuelle Bundeskanzler ist Friedrich Merz.“); ein Tippfehler der Frage
    wird so geschrieben, wie ihn die Seiten schreiben („… CEO of ChatGPT“).
  - **Live-Messung 10./11.10.2026** (14 Fragen, aus dem Rechenzentrum, Suchmaschinen zeitweise gesperrt):
    Kurzantwort richtig bei Präsident der USA, CEO Siemens, CEO „Chatbt“, Bundeskanzler, Hauptstadt
    Australiens, Zugspitze, Gründung Siemens, Faust, Rhein, Louvre-Öffnungszeiten, Bayern-Trainer (je nach
    Lauf 9–12 von 13 Sachfragen); ehrliche Enthaltung (Satz statt Kurzantwort) bei den übrigen; nach den
    Schutzregeln 0 falsche Kurzantworten im letzten Lauf (vorher: „European Cup“, „UEFA Europa“, „Real Madrid“
    als Champions-League-Sieger, „4,1 Mio.“ Berliner (Ballungsraum) — jeweils die Regel dagegen oben).
- **Fußzeile (beta.10, in beta.11 entfernt):** nannte eine ausgefallene Maschine; die Antwort soll ohne
  Verfahrenshinweise auskommen, das Netzwerkprotokoll zeigt jeden Abruf.
- **DuckDuckGo-Probe (CI, 11.10.2026):** vom selben GitHub-Rechner bekamen Python-urllib und der Rust-Kern
  dieselben Antworten (beide HTTP 202): DuckDuckGo sperrt nach Adresse (Rechenzentrum), nicht nach Client.
- **Satzantwort (ohne Kurzantwort):** der Satz aus Snippets und Seiten, der die Frage am besten trifft, mit Quelle; eine zweite
  Quelle nur, wenn sie dasselbe sagt (gleiche Zahl oder gleicher Name). Regeln: Fragewörter zählen nach
  Seltenheit, Antwortwörter („how tall“ → „metres“) halb; der Name aus der Frage muss im Satz stehen; eine
  Zahl, die mehrere Seiten nennen, zählt mehr; Mengen- und Zeitfragen brauchen eine Zahl bzw. Uhrzeit; ein
  abgeschnittenes Snippet zählt weniger; „why“-Fragen heben Sätze mit einem Grund („because“, „weil“).
  Darunter die Treffer als Links. Die Antwortextraktion des Offline-Teils bleibt draußen (auf Lexikonsätze
  geeicht, griff im Test daneben: „Australian Capital Territory“); die Kurzantwort oben ist eine eigene,
  abstimmende Extraktion.
- Offline-Abgleich an 8 echten Fragen (Treffer und Seiten gespeichert): 6 richtige Antwortsätze, 2 ehrliche
  Enthaltungen (Louvre-Öffnungszeiten stehen nur in Tabellen; Siemens-Startseiten nennen den CEO nicht),
  0 falsche.
- Der Wegweiser (`wayfinder.sqlite`) liegt noch in den Paketen, die App liest ihn nicht mehr.

## Antworten (A4)

- **Eskalation:** lokal (Faktenbank, Artikelanfänge) → Feeds → Regal → Websuche. Fragen nach Aktuellem
  (current/latest/now/today/2023+, aktuell/derzeit/heute …) gehen zuerst an die Kanäle; persönliche Fragen
  (I/me/my) nie.
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
Wächter gegen falsche Baujahre, englische Verallgemeinerungsprobe; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.27](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.27)
(Lauf 37095821620, Batterien 95–98: deutsche Alltagsprobe, Folgesätze nach einem Moment, langes Gespräch ohne
dumme Echos, langes deutsches Gespräch ohne Rückfall-Antworten; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.28](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.28)
(Lauf 37099684304, Batterien 99–101: Filmgespräch, Training und Elternbesuch auf Englisch und Deutsch, Reise im
Kontext, Schreibhilfe fragt nach dem Anlass, Wissens-Folgefragen; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.29](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.29)
(Lauf 37103146343, Batterien 102–104: Reise, Übersetzung, Nachricht an Chef/Vermieter auf Deutsch, lockere
Schreibweise auf Englisch und Deutsch; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.30](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.30)
(Lauf 37107152834, Batterien 105–108: Trennung und Arbeitsstress, Valenz-Probe 0/172, Füllantworten 5 von 700
wiederholt; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.31](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.31)
(Lauf 37111092798, Batterie 109: Alltagsmomente nach Satzrahmen auf Englisch und Deutsch, Termine mit „tomorrow“
wiederfinden; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.32](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.32)
(Lauf 37113244647, Probe 110: Folgeantworten nach Momenten, Lern-Gespräche, Urlaub bleibt im Reise-Ablauf;
45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.33](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.33)
(Lauf 37116159237, Probe 111: ganze Alltagsgespräche mit Themengedächtnis, EN 27→0 von 72, DE 25→0 von 59;
45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.34](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.34)
(Lauf 37118044401, Probe 112: Arzt, Beziehung, Geschenke, Konzepte erklären, Schlaf, erster Arbeitstag, Sprache
lernen, TÜV; ungesehen EN 27→0 von 63, DE 23→0 von 42; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.35](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.35)
(Lauf 37119422860, Probe 113: Familie, Wohnen, Geld, Fragen an den Bot; ungesehen EN 27→0 von 56, DE 26→0 von 42;
45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.36](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.36)
(Lauf 37121061699, Probe 114: Fernbeziehung, Steuern, Erkältung, Nachbarschaftshilfe, Abnehmen, Hitze, Gaming;
ungesehen EN 26→0 von 48, DE 22→0 von 36; deutsche Spracherkennung; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.37](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.37)
(Lauf 37130333058, Probe 115: Prüfungsangst Kind, Umzug, Hochzeit, Kollege, Welpe, Kochen, Fahrrad, Jazz;
ungesehen EN 24→0 von 45, DE 20→0 von 34; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.38](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.38)
(Lauf 37137397902, Probe 116: erstes Date, gesprungenes Display, Eltern, E-Mail-Flut, Balkongarten, Schwimmen,
Rücksendung, Babysitten; ungesehen EN 31→0 von 46, DE 22→0 von 34; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.39](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.39)
(Lauf 37139997916, Probe 117: ausgesperrt, Haarschnitt, vergessener Geburtstag, Zahnschmerzen, Waschmaschine, Rauchstopp,
Abschlussarbeit, Mitbewohner; ungesehen EN 32→0 von 48, DE 25→0 von 36, Umformulierung 14/47 und 10/35 → 0;
45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.40](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.40)
(Lauf 37170368190, Proben 118 und 119: Schimmel, Sonnenbrand, Kater, Jetlag, Job-Absage, geschuldetes Geld, Kleinkind,
Autobatterie; Fahrrad, Stromausfall, Heizung, Mobbing, Lebensmittelvergiftung, Strafzettel, Pass, Fitnessstudio;
ungesehen EN 37→0/49 und 34→0/48, DE 26→0/35 und 21→0/31; erster Anlauf 37157014235 brach nur auf dem
macOS-Intel-Runner ab; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.41](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.41)
(Lauf 37180085620, Probe 120: Nachbarparty, Geldbeutel, Weisheitszähne, Fahrstunden, Heuschnupfen, Phishing,
Taschendieb, erster Arbeitstag; ungesehen EN 32→0/47, DE 20→0/31, Umformulierung 22/47 und 7/35 → 0;
45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.42](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.42)
(Lauf 37190790076, Probe 121: Auffahrunfall, Katze, Schnarchen, Handy-PIN, Burnout, Nasenbluten, Gepäck, Handy im
Wasser; ungesehen EN 32→0/46, DE 20→0/30, Umformulierung 7/44 und 12/31 → 0; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.43](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.43)
(Lauf 37202392060, Probe 122: Zecke, Migräne, bellender Hund, Kaution, Brille, Auto verkaufen, Kind lügt, Geschworenendienst;
ungesehen EN 34→0/47, DE 26→0/31, Umformulierung 5/45 und 5/31 → 0; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.44](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.44)
(Lauf 37215225427, Probe 123: Betrugsanruf, Kind gestürzt, Quaddeln, Energienachzahlung, Falschparker, Mitbewohner zieht aus,
Beförderung, Führerschein; ungesehen EN 32→0/45, DE 26→0/30, Umformulierung 11/40 und 4/30 → 0; 45 Dateien, 6 Installer, SHA256SUMS geprüft). [v3.1.0-beta.45](https://github.com/erithy25/engramm/releases/tag/v3.1.0-beta.45)
(Lauf 37229614440, Probe 124: Verlobung, Baby, Stich, Reifenpanne, Wasserschaden, Laptop nass, erster Marathon, Freundschaft;
ungesehen EN 33→0/48, DE 28→0/41, Umformulierung 19/49 und 12/42 → 0; 45 Dateien, 6 Installer, SHA256SUMS geprüft).

## Bedrohungsmodell und ehrliche Restrisiken

- **Geschützt:**
  - Fragetexte: Sie verlassen den Rechner nur über die Websuche (ab Werk an, abschaltbar); persönliche
    Fragen nie.
  - Gesprächsinhalte und Gedächtnis: Sie bleiben lokal.
  - Profilbildung durch einen Vermittler: Es gibt keinen.
- **Nicht geschützt:**
  - Regal ohne Tor: Der Host sieht die IP und die Fach-Nummern. Über viele Fragen hinweg sind Schnittmengen-Angriffe denkbar; Tarn-Fächer und der Cache erschweren sie.
  - Abo: Feed-Betreiber sehen die IP.
  - Websuche: Die Suchmaschine sieht Frage und IP und kann über viele Fragen ein Profil bilden; die
    Trefferseiten sehen einen Besuch. Kein Tor mehr.
