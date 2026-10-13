# PARAMS — „Parameter-Äquivalent“ von ENGRAMM: drei getrennte Größen

Studie nach `docs/PREREG_PARAMS.md` v1.0. Abweichungen stehen in `docs/DEVIATIONS.md`
(Abschnitt CHANGED-10). Alle Records liegen in `results/params/` und tragen
`environment.canonical: false` (Container). Zeit- und Speicherwerte daraus sind laut
PROTOCOL Regel 2 nicht zitierfähig.

**Stand:** A und B sind abgeschlossen. C läuft noch: Die Endläufe mit Seed 7 sind in Arbeit,
danach kommt der Kern-Fit und, falls §6.7 greift, S6. Die C-Zeilen bleiben leer, bis der Fit
nach §6.9 gerechnet ist.

Drei Größen, drei Bedeutungen. Keine davon ist „die“ Parameterzahl von ENGRAMM:

- **A** zählt, was das gebaute Modell speichert.
- **B** schätzt, wie viel Information darin steckt.
- **C** misst, wie groß ein Transformer sein müsste, um gleich gut vorherzusagen.

## Ergebnis

| Messart | Definition | Wert | Intervall | Status |
|---|---|---|---|---|
| A | gelernte gespeicherte Werte (Klasse L, §4.2) des ENGRAMM-LM `main`, Digest `b45c2065…` | **434.342.678 Werte**; 1,372 GB auf Platte | — | Zählung (deterministisch; Bytes im RAM rechnerisch) |
| B | Kapazitäts-Äquivalent = B_bits / 2; B_bits = 8 × kleinste komprimierte Größe des Lernzustands (L) | **≈ 0,90 Mrd.** (B = 1,80 Gbit = 224,7 MB xz) | 0,45–1,80 Mrd. (4 bzw. 1 Bit je Parameter) | Schätzung mit externer Annahme |
| C | N*: Transformergröße (Parameter inkl. Embedding) mit derselben Test-BPB wie ENGRAMM-LM (1,51357693, Near-Dup-gefiltert) | *ausstehend* | *ausstehend* | *ausstehend* |

**Öffentliche Formulierung:** wird nach dem C-Fit nach der Vorlage in §7 gefüllt.

## A — gespeicherte Werte (Zählung)

Record: `results/params/a_engramm_lm_20261008T200223Z.json` (Basis-Digest geprüft).

### ENGRAMM-LM, gelernte Werte (L)

| Komponente | n-Gramme | Kontexte | Werte | davon Zählwerte | davon Schlüssel/Zeiger | Bytes auf Platte |
|---|---|---|---|---|---|---|
| KN-5 Ordnung 1 | 32.736 | 1 | 65.484 | 32.745 | 32.739 | 197.773 |
| KN-5 Ordnung 2 | 19.373.642 | 32.736 | 38.943.706 | 19.504.591 | 19.439.115 | 117.421.669 |
| KN-5 Ordnung 3 | 19.124.757 | 3.681.777 | 60.340.182 | 33.851.870 | 26.488.312 | 247.293.835 |
| KN-5 Ordnung 4 | 17.507.987 | 8.047.187 | 83.299.102 | 49.696.740 | 33.602.362 | 394.747.975 |
| KN-5 Ordnung 5 | 18.261.566 | 13.474.419 | 117.369.652 | 72.159.247 | 45.210.405 | 594.649.801 |
| **KN-5 gesamt** | **74.300.688** | **25.236.120** | **300.018.128** | 175.245.193 | 124.772.933 | 1.354.311.197 |
| HDC-Wortvektoren (`eng` + `wide`, 2 × 32.768 × 2.048 Bit) | | | 134.217.728 (je 1 Bit) | | | |
| Codebuch, übrige Arrays (`idf`, `classes`, `counts`, `ctx_tokens`, Seed) | | | 106.497 | | | |
| **Codebuch gesamt** | | | **134.324.225** | | | |
| Mischgewichte (64 Buckets × 5 Komponenten, Raster 2⁻²⁴), KNN-Grenzen, τ, β | | | **325** | | | 7.056 |
| Themenvektor | | | 0 (wird je Verlauf aus `wide`/`idf` berechnet) | | | |
| Dokument-Cache | | | 0 (Laufzeit: eine Zahl je Token-Typ des aktuellen Dokuments) | | | |
| Perzeptron | | | 0 (ENGRAMM-LM hat keines) | | | |
| **A gesamt (L)** | | | **434.342.678** | | | **1.371.621.485** |

Bytes im RAM (rechnerisch, Σ `nbytes`): 1.371.608.781.

**ARPA-Äquivalent von KN-5** (eine Wahrscheinlichkeit je gespeichertem n-Gramm und ein Backoff
je gespeichertem Kontext der nächsthöheren Ordnung, je 32 Bit): **99.536.807 Werte**
(398,1 MB in fp32). Das ist ein Vergleichswert. Gespeichert sind Zählungen, nicht diese Werte.

**Speicher-Äquivalent** (Bytes von L auf Platte / 2 bzw. / 4): 0,686 Mrd. fp16-Parameter bzw.
0,343 Mrd. fp32-Parameter. Das ist ein Umrechnungswert für Speicherplatz, keine Parameterzahl.

### Nicht in A gezählt (Größe angegeben)

| Klasse | Inhalt | Werte | Bytes auf Platte |
|---|---|---|---|
| (I) Suffix-Array | int32 je Korpusposition | 284.741.161 | 1.138.964.772 |
| (I) KNN-Positionsindex `knn_pos` | int32 je Korpusposition | 284.741.160 | 1.138.964.768 |
| (I) Segment-Signaturen `segsig` | 256 Bit je 128-Token-Segment | 569.482.496 Bit | 71.185.440 |
| (T) Tokenstrom | uint16 | 284.741.161 | 569.482.322 |
| (T) Dokumentgrenzen, -bytes, -schlüssel | 383.085 Dokumente | — | 35.807.448 |
| (D) beim Laden abgeleitet | KN-Discounts, `g1`, `p_uni`, KNN-Kerntabelle, Themen-Tabelle | 73.754 | — (nur RAM) |

**Sekundär, A einschließlich `knn_pos` und `segsig`:** 1.288.566.334 Werte, 2,582 GB.
Speicher-Äquivalent: 1,29 Mrd. fp16-Parameter bzw. 0,65 Mrd. fp32-Parameter.

### Chat v3.2 + Lite-Paket (nur Zählung, §4.4)

Record: `results/params/a_chat_v32_lite_20261008T194027Z.json` (Paket-Manifest geprüft). Die
beiden früheren Records desselben Tags sind fehlerhaft und stehen in `docs/DEVIATIONS.md`.

| Komponente | gespeicherte Werte | davon gelernt | Bytes auf Platte |
|---|---|---|---|
| Faktenbank (`kb.sqlite`: 150.000 Entitäten, 1.392.548 Fakten, 972.862 Aliase) | 11.873.896 Zellen | 150.000 (`popularity`); die Fakten sind wörtlich übernommen | 160.239.616 |
| Index (Satzindex + Regal-Index) | 184.750.488 Einträge | 4.736.006 (`idf`) | 754.103.697 |
| Perzeptronen (Spannen ×2, Konfidenz, Intent, Rahmen, Atlas-Kalibrierung) | 1.248.986 Gewichte | 1.248.986 | 35.771.710 |
| Lexika und Zählstatistiken (Rechtschreibung, Großschreibung, Buchstaben, Lexika, Formen, Tokenizer, Codebuch) | 135.570.241 | darin 134.217.728 Codebuch-Bits; 914.725 Lexikonwerte sind aus Wörterbüchern übernommen, nicht trainiert | 23.916.786 |
| Rohtext (Korpus, Titel, How-to, Wikibooks, Gesprächsbank, Wegweiser) | nicht gezählt | — | 278.534.571 |

## B — Informationsgehalt (Schätzung)

Record: `results/params/b_engramm_lm_20261008T210838Z.json`. Werkzeuge: `xz -9 -T1`
(XZ Utils 5.4.5) und `zstd -19 -T1` (v1.5.5). Jede Gruppe wird einzeln komprimiert.

| Gruppe | Rohbytes | xz -9 | zstd -19 |
|---|---|---|---|
| `kn5_order1` | 196.884 | 87.832 | 116.304 |
| `kn5_order2` | 117.420.810 | 23.979.484 | 27.740.267 |
| `kn5_order3` | 247.292.988 | 41.282.612 | 50.063.952 |
| `kn5_order4` | 394.747.128 | 56.106.312 | 72.743.297 |
| `kn5_order5` | 594.648.960 | 86.356.528 | 110.819.269 |
| `codebook` | 17.301.846 | 16.889.660 | 16.919.406 |
| `mixture` | 2.743 | 968 | 944 |
| **Summe (L)** | **1.371.611.359** | **224.703.396** | 278.403.439 |

- **B_bits** = 8 × 224.703.396 = **1.797.627.168 Bit** (xz ist kleiner).
- **Kapazitäts-Äquivalent:** B_bits / 2 = **0,90 Mrd.**; Spanne 0,45 Mrd. (4 Bit/Parameter)
  bis 1,80 Mrd. (1 Bit/Parameter).
  - Die Annahme von ≈ 2 Bit Wissen je Parameter stammt aus Allen-Zhu & Li, *Physics of
    Language Models: Part 3.3, Knowledge Capacity Scaling Laws*, arXiv:2404.05405.
  - Sie wurde an synthetischem Faktenwissen in GPT-2-artigen Transformern gemessen.
- **Einschränkungen (vorab festgelegt, §5):**
  - Die komprimierte Größe ist eine obere Schranke für die Information *in dieser Darstellung*,
    nicht für „Wissen“.
  - Die 2 Bit je Parameter beschreiben abrufbares Faktenwissen trainierter Netze, nicht
    Dateibits.
- **Deckel:** Eine Zähltabelle ist eine Funktion des Korpus. Der komprimierte Trainingstext ist
  331.535.236 Byte (2,65 Gbit, xz; UTF-8, 1,28 GB roh). Der komprimierte Tokenstrom ist
  292.754.440 Byte. **B liegt unter dem Deckel:** Der Lernzustand komprimiert auf 68 % des
  komprimierten Textes, aus dem er gezählt wurde.
- **Sekundär, mit `knn_pos` und `segsig`:** 1.301.771.484 Byte xz → 10,41 Gbit →
  5,21 Mrd. bei 2 Bit (2,60–10,41 Mrd.). Der Positionsindex ist kaum komprimierbar
  (1,14 GB → 1,05 GB).
- **Vergleichswert:** Die fp32-Gewichte der C-Transformer werden nach Abschluss von C gleich
  serialisiert und komprimiert (`params_compress --only-transformers`).

## C — qualitätsgleiche Transformergröße

*Wird nach dem Kern-Fit (§6.9) gefüllt.* Grundlage sind die Endläufe S0–S4 mit je zwei Seeds
und S5 mit einem Seed, und, falls §6.7 greift, S6. Hinzu kommen der Referenzwert aus
`results/params/c_engramm_test_20261008T200150Z.json` (Digest geprüft, Abweichung zum
E12-Wert ≤ 10⁻⁶) und der Rechenaufwand nach §6.12.

GPT-2 small (1,0388 BPB) ist nur ein externer Referenzpunkt und geht nicht in den Fit ein.

## Abgleich mit der Erwartung (§8)

| Größe | Erwartung | Band | Ergebnis | im Band? |
|---|---|---|---|---|
| A: gelernte Werte (L) | ≈ 0,6 Mrd. | 0,35–1,0 Mrd. | 0,434 Mrd. | ja |
| A: davon KN-5 | ≈ 0,45 Mrd. (≈ 115 M n-Gramme, ≈ 37 M Kontexte) | — | 0,300 Mrd. (74,3 M n-Gramme, 25,2 M Kontexte) | niedriger |
| A: HDC-Wortvektoren | 134.217.728 Bit | sicher | 134.217.728 Bit | ja |
| A: Bytes (L) auf Platte | ≈ 2,0 GB | 1,2–3,5 GB | 1,37 GB | ja |
| A: Speicher-Äquivalent fp16 / fp32 | ≈ 1,0 / 0,5 Mrd. | — | 0,69 / 0,34 Mrd. | niedriger |
| A: ARPA-Äquivalent KN-5 | ≈ 150 M | 90–250 M | 99,5 M | ja |
| A: Suffix-Array, `knn_pos` | je ≈ 1,14 GB | — | je 1,14 GB | ja |
| B: komprimierter Lernzustand | ≈ 0,7 GB | 0,4–1,2 GB | 0,225 GB | **nein**, darunter |
| B: Kapazitäts-Äquivalent | ≈ 2,8 Mrd. | 1,4–5,6 | 0,90 Mrd. | **nein**, darunter |
| B: komprimierter Trainingstext (Deckel) | ≈ 0,3 GB | 0,25–0,4 GB | 0,332 GB | ja |
| B > Deckel | wahrscheinlich (80 %) | — | B < Deckel | **nein** |
| C | — | — | ausstehend | — |

**Lesart A/B:**

- KN-5 speichert 74,3 M statt der geschätzten ≈ 115 M n-Gramme. Die Vorab-Schätzung war zu
  hoch; die Ursache wurde nicht eigens untersucht.
- Die KN-5-Gruppen komprimieren mit xz auf 14–20 % ihrer Rohgröße. Das Codebuch komprimiert
  kaum (98 %), weil seine Bitvektoren fast zufällig sind.
- Daher liegt B unter dem vorab erwarteten Band.
- Beide Zahlen bleiben Speicher- und Informationsgrößen, keine Parameterzahlen.
