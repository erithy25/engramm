# VORREGISTRIERUNG — ENGRAMM-LM: ein Sprachmodell nur aus Lesen und Zählen

**Status: REGISTRIERT.** Committet vor jeder Messung dieser Studie auf einem
Validierungs- oder Testsplit, vor dem Training des Tokenizers und bevor der
Modellcode existiert. Der Commit-Zeitstempel dieser Datei ist ihr Zweck.

**Version 1.1** · Projekt ENGRAMM · Registriert 2026-09-25, geändert 2026-09-25 (§7, vor jeder KNN-Messung auf val/test) · Änderungen nur
per neuer Version mit Datum und Begründung in §14, jeweils **vor** der Messung,
die sie betrifft.

---

## 1. Hypothese

> Ein Sprachmodell, das ausschließlich durch Zählen über einen englischen
> Korpus entsteht — exakte Wortfolgen-Statistik plus binäre
> Hyperdimensional-Vektoren für Ähnlichkeit und Thema, ohne Gradienten,
> ohne neuronales Netz, ohne fremdes Modell — sagt englischen Text besser
> vorher als dieselbe exakte Statistik ohne den HDC-Teil, und schreibt
> Texte, die ein Richter denen des reinen 5-Gramm-Modells vorzieht.

Kernaussage ist der **Zusatznutzen des HDC-Teils** (P2). Dass ein
Zählmodell einen Transformer gleicher Datenmenge schlägt, wird **nicht**
behauptet; der Transformer wird nur berichtet.

## 2. Warum das falsch sein kann

* Ähnlichkeitsbasierte Glättung (Dagan, Lee & Pereira 1999) brachte
  historisch nur wenige Prozent gegenüber gutem Backoff; modified
  Kneser-Ney ist eine starke Baseline, und ein Dokument-Cache nimmt einen
  Teil dessen vorweg, was ein Themenvektor leisten könnte.
* Bedeutungsvektoren aus 2.048 Bit und 512 Wortklassen können zu grob sein:
  die gefundenen „ähnlichen" Stellen können mehr Rauschen als Signal
  liefern. Dann lernt die Mischung ein Gewicht nahe 0, und P2 fällt.
* Der ∞-Gramm-Teil (Suffix-Array) nimmt die leicht vorhersagbaren langen
  Wiederholungen schon im Null-Modell mit; was übrig bleibt, ist genau das
  Schwere.
* Präferenz-Richter bevorzugen oft Flüssigkeit, die ein 5-Gramm-Modell lokal
  ebenso gut hat; ein Absatz ohne übergreifenden Sinn wird bei beiden
  Systemen schlecht bewertet (P6 kann an beiden Seiten scheitern).

## 3. Daten (Manifest)

Allgemeines Englisch, keine Spezialisierung. Quellen mit SHA-256, geladen
über `data.loaders.download_and_verify` (Code: `data/lm_corpus.py`):

| Quelle | Datei | SHA-256 | Bytes |
|---|---|---|---|
| C4-en (Web), Shard 0 von 1024 | `en/c4-train.00000-of-01024.json.gz` | `8ef8d75b0e045dec4aa5123a671b4564466b0707086a7ed1ba8721626dfffbc9` | 319.308.785 |
| WikiText-103-raw Train, Teil 1 | `wikitext-103-raw-v1/train-00000-of-00002.parquet` | `74da360f23826045b3e6ac6375411fdb15f003030aa74f2596ed08b857cb9212` | 156.987.808 |
| WikiText-103-raw Train, Teil 2 | `wikitext-103-raw-v1/train-00001-of-00002.parquet` | `ba090ac30dbf5461e8dcbdd1a1b8e6f3cf9c2c756d64f0c1220450acd514f720` | 157.088.770 |
| WikiText-103-raw Test (nur Literaturvergleich) | `wikitext-103-raw-v1/test-00000-of-00001.parquet` | `5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91` | 732.610 |

**Dokumente.** C4: ein JSON-Datensatz = ein Dokument (Schlüssel: URL).
WikiText: ein Artikel = Zeilen von einer Überschrift `" = Titel = "` bis zur
nächsten (Schlüssel: Titel), die WikiText-Tokenisierung (`" @-@ "`,
`" , "`, …) wird zurückgebaut, damit das Modell normales Englisch lernt.

**Splits.** Pro Dokument ein Eimer `SHAKE-256("engramm-lm/split/v1" ‖ Quelle ‖ Schlüssel) mod 10.000`:
train < 9.930 ≤ val-A < 9.950 ≤ val-B < 9.970 ≤ test. Reine Funktion der
Dokumentidentität, unabhängig von Reihenfolge und Maschine. Verwendung:

| Split | Zweck |
|---|---|
| train | alle Zählungen, Tokenizer, Bedeutungsvektoren |
| val-A | Mischungsgewichte (EM) |
| val-B, Hälfte 1 | Wahl der Konfiguration aus dem Gitter (§7) |
| val-B, Hälfte 2 | Tore G1–G3, insbesondere der Abbruch K1 |
| test | **einmalig**, am Ende, für alle Systeme gleichzeitig (§10) |

Die Hälften von val-B werden über das niedrigste Bit desselben Hashes
bestimmt (`split_half`).

**Near-Duplicate-Filter.** Ein Val-/Test-Dokument, bei dem ≥ 20 % seiner
13-Token-Fenster wörtlich im Train-Tokenstrom vorkommen, wird aus der
Auswertung entfernt (Web-Korpora enthalten Spiegelungen). Primär berichtet
wird **mit** Filter; ohne Filter wird zusätzlich berichtet.

## 4. Tokenizer

Byte-Level-BPE, V = 32.768 inklusive eines Sondertokens `<|eos|>` (ID 0),
gelernt durch Paar-Zählen (`tokenizers==0.23.2`) auf den ersten 256 MB
Train-Text in Stromreihenfolge. Die Datei wird als `data/lm_tokenizer.json`
committet und mit SHA-256 festgehalten; sie ändert sich danach nicht mehr.
Pflicht: verlustfreie Rundreise `decode(encode(x)) == x` (Test).

Tokenstrom: Train-Dokumente sortiert nach ihrem Split-Hash, jedes gefolgt von
`<|eos|>`, als `uint16`. Pilot = die ersten 30 M Tokens dieses Stroms,
Hauptmodell = der ganze Strom (erwartet ≈ 300 M; tatsächliche Zahl wird
berichtet).

## 5. Systeme

Alle Zählsysteme sehen exakt denselben Tokenstrom.

| System | Inhalt | Rolle |
|---|---|---|
| **KN-5** | interpoliertes modified Kneser-Ney, Ordnung 5, eigene Implementierung; Einzelzählungen ab Ordnung 3 entfernt, Masse exakt an den Backoff | Referenz für P1, P3, P6 |
| KN-5 + Cache | + Dokument-Cache | berichtet |
| **Null-Modell** | KN-5 + ∞-Gramm (Suffix-Array) + Dokument-Cache, Mischung wie unten | Referenz für P2 |
| **ENGRAMM-LM** | Null-Modell + KNN (HDC-Ähnlichkeitsgedächtnis) + TOPIC (HDC-Themenvektor) | Hauptsystem |
| Transformer | 6 Schichten, d = 384, Kontext 256, AdamW, gleicher Tokenstrom, CPU; Checkpoints nach 1/3/6/12 h | berichtet |
| GPT-2 small | fremdes Modell (124 M Parameter, 40 GB WebText), auf unserem Testsplit gemessen | nur Einordnung |

**Mischung.** p(w|h) = Σ_c λ_c(b(h)) · p_c(w|h). Eimer b(h) aus
(KN-Kontextzählung, 4 Klassen) × (Länge des längsten ∞-Gramm-Treffers,
4 Klassen) und beim ENGRAMM-LM zusätzlich × (kleinste KNN-Distanz,
4 Klassen). Eine Komponente ohne Signal (kein Treffer, leerer Cache) gibt
p_KN zurück. λ per EM auf val-A, danach eingefroren.

**Gleichbehandlung.** Die Mischung des Null-Modells nutzt dieselbe EM, dieselbe
Anzahl an Iterationen und dieselben Eimer, soweit sie ohne HDC definiert sind.
Der Informationsgewinn durch die KNN-Distanz-Eimer zählt ausdrücklich als
Beitrag des HDC-Teils.

## 6. Messgröße

**Bits pro Byte (BPB)** = Σ −log₂ p(Token) / Σ Bytes, über alle Tokens
einschließlich des abschließenden `<|eos|>`; Bytes = UTF-8-Länge des
Dokuments + 1 je Dokument (für das Ende). Jedes Dokument wird unabhängig
ausgewertet, Kontext beginnt mit `<|eos|>`. Tokenizer-unabhängig, daher mit
Transformer und GPT-2 vergleichbar (GPT-2: eigener Tokenizer, dieselben Bytes).

**Konfidenzintervalle:** 95 %-Perzentil-Bootstrap über Dokumente,
2.000 Replikate, Seed 42, für BPB-Verhältnisse gepaart (dieselben
Dokumente je Replikat).

## 7. Gitter und Seeds

Seeds **42, 7, 1337** für alles Zufällige des HDC-Teils (Index-Vektoren,
Tie-Regel, Clustering-Start). Gitter, gewählt auf val-B Hälfte 1 im Pilot:

| Parameter | Werte |
|---|---|
| KNN-Kernbreite τ (gewichtete Hamming-Einheiten) | 256, 1.024, 4.096 (v1.1; v1.0: 64, 128, 256) |
| TOPIC-Schärfe β | 4, 8 |

Fest: D_s = 2.048 Bit, 512 Wortklassen, Positionsgewichte (8, 4, 2, 1, 1, 1),
Themenfenster 256 Tokens, Eimergrenze 16.384 Stellen, mindestens 64
Nachbarn je Abfrage, Themen-Term v = 2 (256-Bit-Signaturen je 128-Token-Segment,
mit 8 skaliert). Die gewählte Konfiguration wird für den Hauptlauf nicht
mehr verändert.

## 8. Kriterien (Test-Split, Hauptmodell, mit Near-Duplicate-Filter)

| | Kriterium | Schwelle |
|---|---|---|
| **P1** (Stretch) | BPB(ENGRAMM-LM) ≤ 0,90 × BPB(KN-5) | Punktwert |
| **P2** (Kernaussage) | BPB(ENGRAMM-LM) ≤ 0,98 × BPB(Null-Modell), **und** obere 95 %-KI-Grenze des Verhältnisses < 1 | beides |
| **P3** (umformulierte Fakten) | 200 erfundene Fakten (20 Relationen × 10), je Relation 3 handgeschriebene Formulierungen A/B/C. Gelernt wird Form A per `learn_text`, abgefragt mit B und C: Anteil, bei dem das erste Token der Antwort unter den Top-10 liegt. ENGRAMM-LM ≥ max(2 × KN-5-gelernt, KN-5-gelernt + 15 pp) | beides |
| **P4** (Vergessen) | (a) learn(A, B) → forget(B) ergibt denselben `state_digest` wie learn(A); (b) Canary-Exposure nach forget = nie gelernt (bitgleiche Log-Wahrscheinlichkeit); (c) learn/forget ≤ 100 ms je 1.000 Tokens | alle drei |
| **P5** (Gerät) | MacBook Air M4: ≥ 25 Tokens/s beim Schreiben inkl. Quellen, Spitzen-RSS ≤ 10 GB, Aufbau ≤ 12 h | **nur auf dem M4 gültig** |
| **P6** (Lesequalität) | Blindvergleich ENGRAMM-LM gegen KN-5, 200 Prompts aus test, je 100 Tokens, gleiche Dekodierung; LLM-Richter in beiden Reihenfolgen; Präferenzanteil (Unentschieden = ½) ≥ 60 %. Zusätzlich 3 menschliche Leser × 60 Paare (Bogen wird erzeugt) | ≥ 60 % |

**KN-5-gelernt (P3)** bekommt dieselbe Nutzer-Stufe (Dirichlet-Anpassung an die
gelernten Texte) wie ENGRAMM-LM, nur ohne ∞-Gramm, KNN und TOPIC.

**Dekodierung (P6):** Temperatur 0,9, top-p 0,95, keine Wiederholung eines
4-Gramms im erzeugten Text, Zitat-Deckel 32 Tokens (nicht mehr als 32
aufeinanderfolgende Tokens wörtlich aus einer Quelle), Zufall aus
SHAKE-256(Seed ‖ Prompt ‖ Schritt).

## 9. Abbruch- und Blocker-Kriterien

| | Bedingung | Folge |
|---|---|---|
| **K1** = Tor G2 | Pilot, val-B Hälfte 2: Verbesserung von ENGRAMM-LM gegenüber dem Null-Modell < 1 % im Mittel der drei Seeds **oder** bei einem Seed ≤ 0 | HDC-Teil gilt als gescheitert; der Rest der Studie läuft auf dem Null-Modell weiter (Fähigkeiten lernen/vergessen/Quelle) und endet mit einem ehrlichen Negativbericht |
| **K2** | Hauptmodell, val-B Hälfte 2: ENGRAMM-LM nicht besser als das Null-Modell | wie K1 |
| **K3** | < 2 Tokens/s beim Schreiben (Container) | Geschwindigkeits-Blocker, erst beheben |
| **K4** | P3: ENGRAMM-LM ≤ KN-5-gelernt | P3 gilt als gescheitert |
| **K5** | Vergessen nicht exakt (P4a/b) | **Blocker**, kein Urteil vor der Behebung |

## 10. Tore und Reihenfolge

| Tor | Inhalt | Bedingung |
|---|---|---|
| G0 | Harness | Tokenizer-Rundreise, KN-5 normiert (Σ p = 1 auf Stichproben ± 1e-9), BPB von Uni-/Bigramm plausibel monoton |
| G1 | Null-Modell | Null-Modell < KN-5 auf val-B Hälfte 2 |
| G2 | **KILL** | K1 |
| G3 | Hochskalieren | Pilot-Konfiguration eingefroren, erste geschriebene Texte gesichtet |
| G4 | Hauptmodell | Spitzen-RSS ≤ 10 GB (Container), P4a/b exakt |

Testsplit: **eine** Auswertung aller Systeme, nachdem alle Konfigurationen
eingefroren und committet sind. Wird danach ein Fehler gefunden, wird er
behoben, die Auswertung wiederholt und **beides** berichtet.

## 11. Ausgänge

* **BESTÄTIGT:** P2 erfüllt. Zusätzlich je Kriterium P1, P3, P4, P6
  erfüllt/verfehlt einzeln berichtet.
* **WIDERLEGT:** P2 verfehlt oder K1/K2 ausgelöst.
* P5 ist im Container **offen** (Container-Werte werden berichtet, zählen nicht).
* Ein menschliches Panel ist im Container nicht durchführbar; P6 wird mit dem
  LLM-Richter entschieden, der Bogen für das Panel liegt bei.

## 12. Ehrliche Erwartung (vor jeder Messung)

| Punkt | Erwartung | Wahrscheinlichkeit |
|---|---|---|
| BPB ENGRAMM-LM / KN-5 | ≈ 0,93 (0,88–0,97) | — |
| P1 | verfehlt | 25 % erfüllt |
| P2 | knapp | 45 % erfüllt |
| P3 | knapp | 50 % erfüllt |
| P4 | erfüllt | 95 % |
| P5 | (M4) erfüllt | 85 % |
| P6 | knapp | 55 % erfüllt |
| Transformer (12 h CPU) | etwa gleichauf mit ENGRAMM-LM | — |
| GPT-2 small | klar besser (≈ 0,72 × KN-5) | — |

Die Texte werden innerhalb von Satzteilen flüssig sein, im Absatz beim Thema
bleiben und keinen übergreifenden Sinn haben.

## 13. Reproduzierbarkeit

Alle Zählungen ganzzahlig und reihenfolgeunabhängig; Wahrscheinlichkeiten
nur mit Grundrechenarten und gespeicherten Tabellen; IDs sind
Inhalts-Hashes; kein Ergebnis hängt an `PYTHONHASHSEED` (Test). Records nach
`results/lm/` mit Git-Commit, Umgebung und Spitzen-RSS, `canonical=false`
im Container.

## 14. Änderungsprotokoll

* v1.0 (2026-09-25): Erstregistrierung.
* v1.1 (2026-09-25, vor jeder KNN- oder TOPIC-Messung auf val/test): τ-Gitter von
  {64, 128, 256} auf {256, 1.024, 4.096}. Grund: v1.0 legte die Werte fest, bevor die
  Skala der Distanz bekannt war. Eine Diagnose **nur auf Train-Daten** (2.000
  Abfragen aus Train-Positionen hinter dem Pilot-Präfix, Codebuch Seed 42) ergab für
  den Abstand zum nächsten Nachbarn Δ = d − d_min: 1 %-Perzentil ≈ 940, 5 % ≈ 2.800
  (Median über Abfragen). Mit τ ≤ 256 hätte jeder Kern praktisch nur den einzelnen
  nächsten Nachbarn gewichtet (exp(−940/256) ≈ 0,025) — das Gitter hätte keine
  Kernbreite geprüft, sondern dreimal 1-NN. Der Themen-Term v = 2 stand im Code, aber
  nicht in v1.0; er wird hier nachgetragen, nicht verändert.
