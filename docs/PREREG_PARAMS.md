# VORREGISTRIERUNG — „Parameter-Äquivalent“ von ENGRAMM: drei getrennte Größen

**Status: REGISTRIERT.** Committet vor jeder Messung der Messarten A, B und C. Der
Commit-Zeitstempel dieser Datei ist ihr Zweck.

**Version 1.0** · Projekt ENGRAMM · Registriert 2026-10-08 · Änderungen nur per neuer
Version mit Datum und Begründung in §12, jeweils **vor** der Messung, die sie betrifft.

---

## 1. Frage und Grundsatz

ENGRAMM hat keine neuronalen Gewichte. Gefragt ist trotzdem, wie vielen Parametern eines
neuronalen Sprachmodells es entspricht. Darauf gibt es keine eindeutige Antwort. Gemessen
werden deshalb drei getrennt definierte Größen:

| | Größe | Art |
|---|---|---|
| **A** | gespeicherte Werte des gebauten Modells | Zählung |
| **B** | Informationsgehalt des Lernzustands, über Kompression | Schätzung mit externer Annahme |
| **C** | Größe eines Transformers gleicher Vorhersagequalität unter gleichen Daten | Messung (Interpolation oder Extrapolation) |

**Verbindliche Sprachregeln** (für Doku, Website, Jury):

- Es gibt nie „die“ Parameterzahl von ENGRAMM. Jede Zahl wird mit ihrer Definition genannt.
- A und B werden **nie** als „ENGRAMM hat X Parameter“ formuliert. A heißt „speichert X
  Werte“, B heißt „Kapazitäts-Äquivalent unter der Annahme ≈ 2 Bit je Parameter“.
- Nur C ist ein Parameter-Vergleich, und auch nur als „ein Transformer bräuchte unter
  gleichen Daten etwa N* Parameter“.
- GPT-2 small ist externer Referenzpunkt, **kein** Ergebnis von C.

## 2. Gegenstand

**ENGRAMM-LM, registrierte Endfassung** (E12): Hauptmaßstab (285 M Train-Token), Seed 42,
τ-Index 1 (τ = 1.024), β-Index 1 (β = 8), Mischung per EM auf val-A, Gewichte im
2⁻²⁴-Festkomma. Das Modell wird in diesem Container neu gebaut. Sein Basis-Digest muss
**exakt** `b45c20659e5591ff5298d631da4f5c9d566421d6db69f80eaa16a94737779b54` sein
(`experiments/lm_digests.py`, auf Linux und M4 bitgleich bestätigt). Sonst gilt Blocker §10.

**ENGRAMM Chat v3.2 mit Lite-Wissenspaket** (nur Messart A):

- Release `v3.2.0-beta.6`.
- Paket-Manifest SHA-256 `90687f5b5c1d3229b1bd1ee132f3940c8d5cbc5c833b1f5bbcddc47ab4a1fac3`
  (Paketversion 3.1.0-beta.1, im Release wiederverwendet), 36 Dateien, 1.248.102.226 Bytes,
  jede Datei gegen das Manifest geprüft.
- Dazu die Programmdaten des Repos (Rahmen-Klassifikator, Lexika, Formen, Buchstaben-Statistik,
  Atlas-Kalibrierung, How-to, Wikibooks, Gesprächsbank).

## 3. Was vor dieser Registrierung lief (offengelegt)

Nichts davon misst eine Größe von A, B oder C.

- Umgebungen: `.venv` (Python 3.13, `requirements.lock`) und `.venv_b1` (Python 3.12,
  `requirements-baselines.lock`, torch 2.14.0+cpu).
- Rohdaten geladen, alle vier SHA-256 wie in PREREG_LM §3.
- Korpus und Tokenisierung (`experiments.lm_prepare`):
  - Tokenizer SHA-256 `637745134e61…`;
  - train 284.741.161 Token in 383.085 Dokumenten;
  - test 1.137 Dokumente, 3.745.775 Bytes (gleich E12).
- Lite-Paket von `v3.2.0-beta.6` geladen, alle 36 Dateien gegen das Manifest geprüft.
- **Durchsatzprobe ohne Daten**:
  - nur Zufallstoken;
  - `experiments/params_probe.py`, Records `results/params/probe_throughput_20261008T191106Z.json`
    (Standard-Verlust, fp32/bf16, 2/4 Threads) und `probe_throughput_chunked_20261008T193349Z.json`
    (registrierte Einstellung, §6.3);
  - dazu eine Gegenprobe der blockweisen Kreuzentropie gegen `F.cross_entropy` (§6.3).
  - Zweck allein: das Rechenbudget in §6.6 planbar machen.
- Code für A, B und C, an einem winzigen Wegwerfmodell auf Lauffähigkeit getestet: ein
  Transformer mit d = 32 und 245.760 Train-Token. Gemessen wurde dabei nur die bitgleiche
  Wiederaufnahme nach Abbruch; keine Größe dieser Studie.

## 4. Messart A — gespeicherte Werte (Zählung)

### 4.1 Definition

Ein **gespeicherter Wert** ist ein Element eines Arrays, einer Tabelle oder eines Datensatzes,
das das gebaute Modell speichert und beim Vorhersagen liest. Bitvektoren zählen je Bit einen
Wert zu 1 Bit („Vokabular × Bits“). Grundlage ist das Verzeichnis, das
`HDCLanguageModel.save` schreibt (`experiments.lm_final_model --save`).

### 4.2 Klassen

| Klasse | Inhalt (ENGRAMM-LM) | in A gezählt? |
|---|---|---|
| **(L) gelernt** | KN-5-Tabellen (je Ordnung `ctx`, `ptr`, `total`, `n1`, `n2`, `n3`, `w`, `a`, `coc`), Codebuch (`eng`, `wide`, `idf`, `classes`, `counts`, `ctx_tokens`), Mischgewichte, KNN-Distanzgrenzen, τ, β | **ja — primäre Zahl** |
| **(I) korpusgebundene Indizes** | Suffix-Array; KNN-Positionsindex `knn_pos`; Segment-Signaturen `segsig` | nein |
| **(T) Rohtext** | Tokenstrom, Dokumentgrenzen, -bytes, -schlüssel | nein, Größe angegeben |
| **(D) beim Laden abgeleitet** | KN-Discounts, `g1`, `p_uni`, KNN-Kerntabelle, Themen-Tabelle | nein (Funktionen von L), berichtet |
| **(Z) Laufzeitzustand** | Dokument-Cache, Themenvektor, Nutzerschicht (im Basismodell leer) | 0 gespeichert, Größe als Formel |

**Begründung für (I).** Der Auftrag nimmt Suffix-Array und Rohkorpus aus, weil sie
gespeicherter Text sind und nichts Gelerntes. `knn_pos` und `segsig` sind von derselben Art:

- je ein Eintrag pro Korpusposition bzw. pro 128-Token-Segment;
- eine deterministische Funktion des Textes (und der Klassen bzw. Bedeutungsvektoren);
- die Größe wächst linear mit dem Korpus.

Damit der Leser selbst entscheiden kann, wird **zusätzlich** A einschließlich `knn_pos` und
`segsig` berichtet (sekundär).

### 4.3 Ausgabe je Komponente

Anzahl Werte, Bits je Wert (gespeicherter Datentyp), Bytes auf Platte (Dateigrößen) und
Bytes im RAM (Σ `nbytes` der geladenen Arrays, rechnerisch).

- KN-5 wird nach Ordnung 1–5 aufgeschlüsselt:
  - n-Gramme, Kontexte, Werte;
  - getrennt „Zählwerte“ (`total`, `n1`–`n3`, `a`, `coc`) und „Schlüssel/Zeiger“ (`ctx`, `w`, `ptr`).
- **ARPA-Äquivalent** (auftragsgemäß „Wahrscheinlichkeit + Backoff je n-Gramm“). Unsere
  Implementierung speichert Zählungen, keine Wahrscheinlichkeiten. Umgerechnet wird so:
  - je Ordnung n eine Wahrscheinlichkeit pro gespeichertem n-Gramm;
  - ein Backoff-Gewicht pro gespeichertem Kontext der Ordnung n+1;
  - je Wert 32 Bit.
  - Das ist ein Vergleichswert, nicht der Speicherinhalt.
- Codebuch: dazu die Zahl der Token mit Zufallsvektor (< 5 Vorkommen; gespeichert, aber nicht gelernt).
- Themenvektor, Dokument-Cache: 0 gespeicherte Werte, Laufzeitgröße angegeben.
- Perzeptron: ENGRAMM-LM hat keines (0).

**Speicher-Äquivalent** = Bytes (L) auf Platte / 2 (fp16-Parameter) und / 4
(fp32-Parameter); sekundär dasselbe für (L)+(I). Es ist ein Umrechnungswert für Speicher,
keine Parameterzahl.

### 4.4 Chat v3.2 + Lite

Nur Zählung, getrennt nach:

1. **Faktenbank** (`kb.sqlite`): Zeilen und Zellen je Tabelle. Gelernt ist davon nur
   `popularity` (gezählt); die Fakten sind wörtlich übernommen.
2. **Index**: Satzindex (`starts`, `lens`, `ptr`, `post`, `sent_terms`, `term_of`, `terms`,
   `doc_ptr`, `doc_post`, `sent_doc`) und Regal-Index (`shelf_index/*`). Einträge je Array;
   gelernt (gezählt) ist nur `idf`.
3. **Perzeptronen**: `spanperc_ens7`, `spanperc_nq`, `confperc14`, `nlp/intent`,
   Rahmen-Klassifikator, Atlas-Kalibrierung. Je Gewicht ein Wert; Merkmalsschlüssel getrennt.
4. **Lexika und Zählstatistiken**: Rechtschreibung, Großschreibung, Buchstaben,
   `lex_en`/`lex_de`, `forms_en`/`forms_de`, Tokenizer-Merges, Codebuch.
5. **Rohtext** (nicht gezählt, Größe angegeben): `corpus.u16`, Titel, How-to, Wikibooks,
   Gesprächsbank, Wegweiser.

**Bytes im RAM:**

- wo der Lader Arrays erzeugt: rechnerisch;
- sonst: RSS-Zuwachs beim isolierten Laden der Komponente. Das ist ein Containerwert und
  nicht offiziell (PROTOCOL Regel 2).

## 5. Messart B — Informationsgehalt (Schätzung)

1. **Serialisierung**, deterministisch: je Gruppe eine Datei mit einer JSON-Kopfzeile (Name,
   Datentyp, Form je Array), danach die Rohbytes der Arrays in fester Reihenfolge,
   little-endian.
   - Gruppen von (L): `kn5_order1` … `kn5_order5`, `codebook`, `mixture`.
   - Sekundär, nicht in B: `knn_pos`, `segsig`.
2. **Kompression** je Gruppe einzeln:
   - `xz -9 -T1` (XZ Utils 5.4.5) und `zstd -19 -T1` (v1.5.5);
   - Summe je Kompressor;
   - **B_bits = 8 × min(Σ xz, Σ zstd)**.
3. **Kapazitäts-Äquivalent = B_bits / 2**, Spanne B_bits / 4 bis B_bits / 1.
   - Annahme „≈ 2 Bit Wissen je Parameter“ nach Allen-Zhu & Li, *Physics of Language Models:
     Part 3.3, Knowledge Capacity Scaling Laws*, arXiv:2404.05405 (ICLR 2025).
   - Dort gemessen an synthetischem Faktenwissen in GPT-2-artigen Transformern.
4. **Kennzeichnung:** „Schätzung mit externer Annahme, keine Messung“. Vorab festgehaltene
   Einschränkungen:
   - Die Kompressionsgröße ist eine **obere Schranke** für die Information *in dieser
     Darstellung*, nicht für „Wissen“.
   - Die 2 Bit je Parameter beschreiben abrufbares Faktenwissen trainierter Netze, nicht
     Dateibits.
   - Eine Zähltabelle ist eine deterministische Funktion des Korpus. Ihr Informationsgehalt ist
     daher höchstens der des Korpus plus Baucode. Als **Deckel** wird deshalb der komprimierte
     Trainingstext (`train.txt.bin`, UTF-8) und der Tokenstrom mitberichtet.
   - **Vergleichswert:** die fp32-Gewichte jedes in C trainierten Transformers, gleich
     serialisiert und komprimiert.

## 6. Messart C — qualitätsgleiche Transformergröße

### 6.1 Gleiche Bedingungen

- **Daten:** derselbe Train-Tokenstrom (284.741.161 Token), derselbe Tokenizer (V = 32.768).
- **Test:** derselbe Test-Split.
- **Messgröße:** Bits pro Byte mit der Bytezählung aus PREREG_LM §6.
- **Filter:** derselbe Near-Duplicate-Filter (`results/lm/dedup.json`, 1.092 von 1.137
  Dokumenten). Primär gilt **gefiltert**.
- **Transformer-Auswertung** (`experiments/lm_transformer.py eval`): jedes Dokument einzeln,
  Gleitfenster 256, Schritt 128.

### 6.2 Größenreihe

Alle Größen haben Kontext 256, gebundene Ein-/Ausgabe-Einbettung und gelernte Positionen. N
zählt alle Parameter (Einbettung einmal), wie Pearce & Song (2024) empfehlen; N_ne ist N ohne
Token- und Positions-Einbettung.

| Größe | d | Schichten | Köpfe | N | N_ne | Token (20·N) | Schritte |
|---|---|---|---|---|---|---|---|
| S0 | 32 | 1 | 1 | 1.069.536 | 12.768 | 21.393.408 | 5.223 |
| S1 | 64 | 2 | 2 | 2.213.632 | 100.096 | 44.273.664 | 10.809 |
| S2 | 96 | 3 | 3 | 3.506.016 | 335.712 | 70.123.520 | 17.120 |
| S3 | 128 | 4 | 4 | 5.020.416 | 793.344 | 100.409.344 | 24.514 |
| S4 | 192 | 4 | 6 | 8.120.448 | 1.779.840 | 162.410.496 | 39.651 |
| S5 | 256 | 6 | 4 | 13.193.216 | 4.739.072 | 263.864.320 | 64.420 |
| S6 | 384 | 6 | 6 | 23.328.768 | 10.647.552 | 466.575.360 | 113.910 |

S6 ist die Architektur aus PREREG_LM §5.

### 6.3 Trainingsregel (für alle Größen gleich)

- **Token:** D = 20 · N (Chinchilla-nah), aufgerundet auf ganze Schritte zu 16 × 256 Token.
  Ab S6 bedeutet das mehr als eine Epoche.
- **Optimierer:** AdamW (β = 0,9/0,95), Gewichtszerfall 0,1, Gradienten-Clip 1,0,
  Initialisierung N(0; 0,02).
- **Lernratenplan:** Aufwärmen über min(500; ⌈0,1 · Schritte⌉) Schritte, dann Kosinus bis
  0,1 × Spitze.
- **Daten:** zufällige Fenster aus dem Train-Strom (Generator = Lauf-Seed).
- **Rechnung:** fp32, 4 Threads, ein Lauf zur Zeit.
- **Blockweise Kreuzentropie** (`ChunkedCrossEntropy`):
  - Sie ist dieselbe Verlustfunktion wie `F.cross_entropy`, nur in Zeilenblöcken zu 2.048
    gerechnet.
  - Gegengeprüft: relative Abweichung von Verlust und Gradienten < 10⁻⁶.
  - Jeder Lauf prüft beim Start auf der ersten Charge die Gleichheit mit `F.cross_entropy`
    (< 10⁻⁴ relativ).
  - Grund: Die Softmax über 32.768 Wörter bestimmt bei kleinen Modellen die Schrittzeit; blockweise
    sind die Schritte 1,06× (S6) bis 1,34× (S0) schneller (Probe-Records §3).
- **Wiederaufnahme:** Alle 30 min wird der volle Zustand gesichert. Ein abgebrochener Lauf wird
  bitgleich fortgesetzt (getestet: Gewichtsdifferenz 0).

### 6.4 Lernrate: Wahl auf val-B, nie auf test

- **S0–S4:** Seed 42 mit den Lernraten {1·10⁻³, 2·10⁻³, 4·10⁻³}, je mit einem Viertel des
  Budgets (5·N Token, eigener vollständiger Plan).
- **Kriterium:** BPB auf val-B Hälfte 1 (`split_half` = 0), gefiltert.
  - Kleinster Wert gewinnt.
  - Bei |Δ| < 10⁻⁴ gewinnt die kleinere Lernrate.
- **Randregel:**
  - Gewinnt 1·10⁻³, läuft zusätzlich 5·10⁻⁴; gewinnt 4·10⁻³, läuft zusätzlich 8·10⁻³.
  - Danach wird unter allen gewählt, ohne weitere Erweiterung.
- **S5 und S6** übernehmen die Lernrate von S4. Diese Lernrate ist nicht eigens abgestimmt
  und wird so berichtet.
- **Berichtet werden** alle Sweep-Läufe mit ihrem val-B-Wert. Auf test wird nur der gewählte
  Lauf ausgewertet.

### 6.5 Seeds und Endläufe

- Endläufe mit vollem Budget (20·N) und gewählter Lernrate.
- **S0–S4:** Seeds 42 und 7. **S5:** Seed 42.
- Jeder Endlauf wird **einmal** auf test ausgewertet (zusätzlich auf val-B).
- **Reihenfolge:** Sweeps S0–S4 → Endläufe Seed 42 (S0–S5) → Endläufe Seed 7 (S0–S4) →
  Auswertung. Zwischendurch wird **kein** Fit gerechnet.

### 6.6 Rechenbudget

Grundlage ist die Durchsatzprobe (`probe_throughput_chunked_20261008T193349Z.json`: 4 Threads,
blockweise Kreuzentropie, Zufallstoken):

| | S0 | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|---|
| Token/s | 9.681 | 7.944 | 7.023 | 6.255 | 4.952 | 3.523 | 2.367 |
| Stunden je Endlauf | 0,61 | 1,55 | 2,77 | 4,46 | 9,11 | 20,8 | 54,8 |

| Block | Stunden (Container) |
|---|---|
| Sweeps S0–S4 (3 × ¼ Budget) | 13,9 |
| Randregel, höchstens 5 × ¼ Budget | ≤ 4,6 |
| Endläufe S0–S4 × 2 Seeds | 37,0 |
| Endlauf S5 | 20,8 |
| Auswertungen (val-B, test) | ≈ 3 |
| **Kern gesamt** | **≈ 75–80 h (≈ 3,2 Tage)** |
| S6 (nur nach §6.7) | + 54,8 |

Läufe über 1 Stunde starten erst nach Freigabe durch den Auftraggeber. Verkleinert er den Plan,
wird das als v1.1 **vor** dem ersten C-Lauf registriert.

### 6.7 Bedingte Erweiterung S6 (23 M)

S6 wird nur gerechnet, wenn eine der beiden Bedingungen gilt:

- N* liegt nach dem Kern-Fit über der größten gemessenen Größe (S5); oder
- der Auftraggeber verlangt es vor Beginn von C.

S6 läuft dann mit Seed 42 und der Lernrate von S4. N* wird danach mit S6 neu gerechnet. Beide
Fits werden berichtet.

**Der vorhandene 23-M-Lauf aus E12 wird nicht wiederverwendet.** Das Protokoll ist nicht
identisch:

- Zeitbudget statt Tokenbudget;
- Kosinusplan über 12 h, aber beim 6-h-Checkpoint abgegriffen, also nicht ausgelaufen;
- ≈ 26 M Token ≈ 1,1 Token je Parameter;
- 2 Threads unter Fremdlast;
- der Checkpoint liegt in diesem Container nicht vor.

Sein Wert (1,6376 BPB) wird nur als historischer Punkt genannt.

### 6.8 Referenzwert ENGRAMM-LM

Neu gemessen aus dem Digest-geprüften Modell (`experiments/params_engramm_eval.py`). Primär
gilt `HDCLanguageModel.stream_probs` über den Test-Strom. Drei Prüfungen:

- Gegenprobe über den Komponenten-Pfad der E12-Auswertung: Abweichung ≤ 10⁻⁶ BPB.
- Abweichung vom E12-Wert 1,51357693 (gefiltert): ≤ 10⁻⁶ BPB.
- Der Near-Duplicate-Filter des Test-Splits wird neu berechnet und muss `dedup.json` ergeben.

Mitberichtet: KN-5 und Null-Modell aus demselben Lauf (Sekundärziele in §6.10).

### 6.9 Fit, N* und Intervall

- **Werte je Größe:** bpb_s = Mittel der Seeds von BPB(Größe s, Seed), gefiltert.
- **Primäres Modell:** reines Potenzgesetz ln bpb = c − α · ln N, kleinste Quadrate über die
  Größen S0–S5, ungewichtet.
- **N\*** = exp((c − ln bpb_E) / α), mit bpb_E = Testwert ENGRAMM-LM.
- α ≤ 0 → kein Größeneffekt, N* ist dann nicht definiert.
- **Intervall:** 95 %-Perzentil-Bootstrap mit 2.000 Replikaten, Generator-Seed 42. Je Replikat:
  - Dokumente ziehen, mit Zurücklegen und gepaart: dieselben Dokumente für ENGRAMM und alle Läufe;
  - je Größe die Seeds mit Zurücklegen ziehen;
  - alles neu rechnen: bpb_E, bpb_s, Fit und N*.
  - Berichtet wird auch der Anteil der Replikate, in denen N* außerhalb der gemessenen Größen liegt.
- **Extrapolation:** Liegt N* außerhalb [N(S0), N(größte gemessene Größe)], heißt es
  „Extrapolation“, mit Faktor N*/N_max bzw. N_min/N*.
- Berichtet werden Residuen und R².

### 6.10 Sensitivität (berichtet, nicht primär)

1. Lokal: log-log-Interpolation zwischen den zwei Größen, die bpb_E einschließen.
2. Fit über N_ne statt N.
3. Sättigende Form bpb = E + a · N^(−α); nur wenn sie mit E ≥ 0 konvergiert.
4. Ungefiltertes Test-Set.
5. Sekundärziele: N* für KN-5 und für das Null-Modell (wie viele Parameter die exakte
   Statistik allein „wert“ ist).

### 6.11 Externe Referenzpunkte (nie im Fit)

- **GPT-2 small:** 124 M Parameter, 1,0388 BPB gefiltert
  (`results/lm/test_eval_20260926T183702Z.json`). Anderes Datenvolumen (40 GB WebText), andere
  Rechenmenge.
- **E12-Transformer, 6 h:** 1,6376 BPB (§6.7).

### 6.12 Rechenaufwand

**Transformer:** Trainings-FLOPs ≈ 6 · N · D, bei N* also 120 · N*². Dazu die gemessene
Container-Wanduhrzeit jedes Laufs und die log-log-interpolierte Zeit bei N*. Diese Zeiten
stammen aus dem Container und sind nicht offiziell (PROTOCOL Regel 2).

**ENGRAMM-LM:** Aufbau 544 s auf dem M4 (`results/lm/p5_device_main_20260926T161917Z.json`,
`canonical: true`). Containerwert zum Vergleich gleicher Maschine: 566 s
(`results/lm/p5_device_main_20260926T100039Z.json`, nicht offiziell).

**Transformer auf dem M4:** in dieser Studie nicht gemessen. Angegeben wird der Befehl, mit
dem es gemessen werden kann.

## 7. Auswertungsregel und Ergebnisform

`docs/PARAMS.md` enthält die Tabelle **Messart | Definition | Wert | Intervall | Status**. Die
Status-Wörter liegen fest:

| Messart | Status |
|---|---|
| A | „Zählung (deterministisch; Bytes im RAM rechnerisch)“ |
| B | „Schätzung mit externer Annahme“ |
| C | „Messung, Interpolation“ oder „Messung, Extrapolation (× k)“; dazu „Container, `canonical: false`“ |

Records: `results/params/*.json` mit `environment.canonical`. Läufe in diesem Container stehen
auf `false`; ihre Zeit- und Speicherwerte sind laut PROTOCOL Regel 2 nicht zitierfähig.

**Öffentliche Formulierung.** Sie wird erst nach der Messung gefüllt, nach dieser Vorlage, und
nennt die Definition immer mit:

> „Ein Transformer bräuchte unter gleichen Daten (285 Mio. Token, gleicher Tokenizer, 20 Token
> je Parameter) etwa N* Parameter [95 %-KI], um ENGRAMM-LMs Vorhersagequalität (BPB auf dem
> Testsatz) zu erreichen. ENGRAMM selbst speichert dafür X gelernte Werte (Y GB), dazu Z GB Text
> und Suchindex.“

## 8. Erwartung (vorab, ehrlich)

| Größe | Erwartung | Band |
|---|---|---|
| A: gelernte Werte (L) | ≈ 0,6 Mrd. | 0,35–1,0 Mrd. |
| A: davon KN-5 | ≈ 0,45 Mrd. (≈ 115 M n-Gramme, ≈ 37 M Kontexte) | — |
| A: davon HDC-Wortvektoren | 134.217.728 Bit (= 2 × 32.768 × 2.048, sicher) | — |
| A: Bytes (L) auf Platte | ≈ 2,0 GB | 1,2–3,5 GB |
| A: Speicher-Äquivalent fp16 / fp32 | ≈ 1,0 / 0,5 Mrd. | — |
| A: ARPA-Äquivalent KN-5 | ≈ 150 M Werte | 90–250 M |
| A: Suffix-Array, knn_pos | je ≈ 1,14 GB (int32 × 285 M) | — |
| B: komprimierter Lernzustand | ≈ 0,7 GB → B ≈ 5,6 Gbit → Kapazitäts-Äq. ≈ 2,8 Mrd. (1,4–5,6) | 0,4–1,2 GB |
| B: komprimierter Trainingstext (Deckel) | ≈ 0,3 GB | 0,25–0,4 GB |
| B > Deckel (Darstellung größer als der Text, aus dem gezählt wurde) | wahrscheinlich | 80 % |
| C: bpb je Größe | S0 ≈ 1,95 · S1 ≈ 1,70 · S2 ≈ 1,57 · S3 ≈ 1,48 · S4 ≈ 1,40 · S5 ≈ 1,33 | ± 0,1 |
| **C: N\*** | **≈ 4 M** (N_ne ≈ 0,4 M) | 80 %-Band 2–12 M |
| C: N* im gemessenen Bereich (S0–S5) | ja | 85 % |
| C: N*(KN-5) | ≈ 2,5 M | — |
| C: Trainingsaufwand bei N* | ≈ 2·10¹⁵ FLOPs, ≈ 3–4 h im Container | gegen ≈ 0,16 h Aufbau ENGRAMM (Container), also ≈ 20× |

**Lesart, die ich vorab erwarte.** A und B ergeben Größenordnungen von Milliarden. Das liegt an
der Darstellung: Eine Zähltabelle speichert jedes n-Gramm einzeln. C ergibt wenige Millionen.
Genau dieser Abstand ist die ehrliche Botschaft. Er ist der Grund, warum A und B nie als
„Parameter“ bezeichnet werden dürfen.

## 9. Verboten (aus dem Auftrag, bindend)

- Zahlen aus A oder B als „ENGRAMM hat X Parameter“ formulieren.
- Am Test-Split tunen (Lernraten werden ausschließlich auf val-B Hälfte 1 gewählt).
- Schwellen oder Regeln nachträglich ändern.
- Läufe weglassen: Jeder gestartete Lauf wird berichtet, auch abgebrochene und Sweep-Läufe.
- Den GPT-2-Vergleich als Ergebnis von C darstellen.

## 10. Blocker und Abbruch

| Bedingung | Folge |
|---|---|
| Basis-Digest ≠ `b45c2065…` | Blocker. Keine Messung von A/B/C am LM, bis geklärt |
| ENGRAMM-Testwert weicht > 10⁻⁶ ab (§6.8) oder der Filter reproduziert nicht | Blocker, Befund wird dokumentiert |
| nicht-endlicher Verlust im Sweep | Diese Lernrate scheidet aus und wird berichtet |
| nicht-endlicher Verlust im Endlauf | Einmal identisch neu starten; beide berichtet. Scheitert er erneut, fällt die Größe aus dem Fit (mit Grund) |
| Container-Neustart | Wiederaufnahme aus `resume.pt`, im Record vermerkt. Verlorene Läufe werden neu gestartet und berichtet |

## 11. Reproduzierbarkeit

| Messart | Befehl |
|---|---|
| A, LM | `python -m experiments.params_count_lm` |
| A, Chat | `python -m experiments.params_count_chat` |
| B | `python -m experiments.params_compress --transformers` |
| C, Referenz | `python -m experiments.params_engramm_eval` |
| C, Läufe | `python -m experiments.params_c drive` (startet Training und Auswertung in `.venv_b1`) |
| C, Auswertung | `python -m experiments.params_c fit` |

Alle Seeds und Budgets stehen in diesem Dokument.

## 12. Änderungsprotokoll

* v1.0 (2026-10-08): Erstregistrierung.
