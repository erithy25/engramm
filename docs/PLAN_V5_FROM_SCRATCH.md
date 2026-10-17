# ENGRAMM von null: Rechnung, Forschungsstand, umsetzbarer Plan

Stand 6. Oktober 2026. Auftrag: GPT-4-Niveau ohne fremde Modelle, auf einem Rechner, 5 GB.

## 1. Gemessene Grundlage

Diese Maschine (die Cloud-Umgebung der Entwicklung): 4 CPU-Kerne, keine GPU, 15 GB RAM. Eine Matrix-Multiplikation
(fp32) schafft **231 Milliarden Rechenschritte pro Sekunde**, also **2,0·10¹⁶ pro Tag**.

## 2. Rechnung

| Ziel | Trainingsaufwand (veröffentlichte Schätzungen) | Dauer auf dieser Maschine |
|---|---|---|
| GPT-2-small-Qualität mit dem besten bekannten Rezept (nanoGPT-Speedrun, ~3 min auf 8×H100) | ~1,4·10¹⁸ | **~72 Tage** |
| GPT-3 (175 Mrd.) | 3,1·10²³ | ~15 Mio. Tage |
| GPT-4 (Schätzung) | ~2·10²⁵ | ~1 Mrd. Tage |

Rechenoptimale Modellgröße nach den Chinchilla-Skalierungsgesetzen (C = 6·N·D, D ≈ 20·N):

| Rechenzeit hier | Modellgröße | Trainingsdaten |
|---|---|---|
| 1 Tag | ~13 Mio. Parameter | 0,26 Mrd. Token |
| 30 Tage | ~71 Mio. | 1,4 Mrd. |
| 365 Tage | ~246 Mio. | 4,9 Mrd. |

Zum Vergleich: GPT-4-Klasse hat Hunderte Milliarden Parameter auf über 10 Billionen Token.

## 3. Was die Forschung an Effizienz kennt (und wie viel es bringt)

| Hebel | Größenordnung des Gewinns | Quelle der Erfahrung |
|---|---|---|
| bessere Optimierer, Architektur-Tricks | ~3–10× | nanoGPT-Speedrun, Muon, moderne Transformer-Details |
| hochwertige, ausgewählte Daten | ~3–10× | Phi-Reihe, FineWeb-Edu |
| Wissen in einer Datenbank statt in Gewichten (Retrieval) | ~10–25× bei Wissensaufgaben | RETRO, kNN-LM, Atlas |
| Mixture-of-Experts | ~2–4× pro Rechenaufwand | Switch, Mixtral |
| alle zusammen, optimistisch | ~10³ | |
| nötig für GPT-4 auf dieser Maschine in einem Jahr | **~3·10⁶** | |

Es fehlen mindestens drei Zehnerpotenzen, die keine bekannte Methode liefert. Ein Durchbruch dieser Größe wäre der
größte der KI-Geschichte. Er lässt sich nicht planen oder in Tagen erzwingen, sondern nur erforschen, mit offenem
Ausgang.

## 4. Was mit voller Anstrengung real gebaut werden kann: ENGRAMM-R

Die drei stärksten Hebel kombiniert, von null, ohne fremde Modelle:

1. **Kleiner Transformer** (13–250 Mio. Parameter je nach Rechenzeit), eigener Tokenizer (vorhanden), eigene Daten
   (Wikipedia-Lesekorpus, freie Texte – vorhanden).
2. **Retrieval im Kern** (RETRO-artig): Bei jedem Abschnitt holt das Modell passende Sätze aus der ENGRAMM-Datenbank
   (2 Mio. Sätze, Faktenbank). Es muss Wissen nicht auswendig lernen, nur Sprache und Verknüpfen.
3. **ENGRAMM-Schichten bleiben:** exaktes Rechnen, Gedächtnis, bitgenaues Vergessen, Quellen, Sicherheit.
4. **Sofortiges Lernen:** Neues kommt in die Datenbank, nicht in die Gewichte, und ist im nächsten Satz nutzbar.

**Erwartetes Ergebnis, ehrlich:** flüssigere, zusammenhängende Antworten mit Quellen auf dem Niveau früher Sprachmodelle
(GPT-2 bis GPT-3-klein) für Wissensfragen, deutlich über heute. GPT-4-Niveau bei Denken, Schreiben und Gespräch: nein.

### Phasen (jede mit vorab festgelegter Schwelle, gemessen wie bisher)

| Phase | Inhalt | Rechenzeit hier |
|---|---|---|
| R0 | PyTorch-freies Training (numpy/numba) oder PyTorch-CPU einrichten; Datenpipeline aus dem vorhandenen Korpus | Stunden |
| R1 | 13-Mio.-Modell ohne Retrieval: Basislinie (Bits pro Byte gegen das vorhandene ENGRAMM-LM) | 1 Tag |
| R2 | gleiches Modell mit Retrieval: Gewinn messen | 1 Tag |
| R3 | Skalierung auf die verfügbare Rechenzeit (30 Tage hier ≈ 70 Mio.; auf einem Apple-M-Mac oder einer GPU 10–100× schneller) | Wochen |
| R4 | Einbau in den Chat mit Belegpflicht, Endmessung auf frischen versiegelten Gesprächen | – |

## 5. Entscheidungen, die beim Auftraggeber liegen

- **Hardware:** Hier dauert jeder Schritt 10–100× länger als auf einem Mac mit Apple-Silicon-Chip oder einer
  Consumer-GPU. Für R3 in sinnvoller Zeit braucht es solche Hardware.
- **Erwartung:** ENGRAMM-R ist eine echte Eigenentwicklung mit messbarem Fortschritt, aber kein Weg zu GPT-4-Niveau. Wer
  dieses Niveau offline und ohne Server will, kommt nur über vortrainierte offene Gewichte dorthin
  (`docs/PLAN_V4_HYBRID.md`). Auch die laufen beim Nutzer ohne Rechenzentrum.

## 6. Zielleiter (festgelegt vom Auftraggeber, 6. Oktober 2026)

1. **Stufe 1 – GPT-2-Niveau** (Ziel jetzt): eigenes Modell, von null, Messgröße Bits pro Byte auf dem Test-Satz;
   Vergleichswert GPT-2 small = 1,04 (gemessen, `results/lm/test_eval_20260926T183702Z.json`).
2. **Stufe 2 – GPT-3-Niveau** (nächstes Ziel, sobald Stufe 1 erreicht und gemessen ist).

Laufendes Experiment für Stufe 1: Zähl-Residual-Training (`experiments/v5_prior.py`, `experiments/v5_residual.py`).

## 7. Zähl-Residual-Training: Läufe und Entscheidungsregel

**Idee.** Ein Zählmodell (KN5 + ∞-gram + Cache, ohne Gradienten in Minuten gebaut) nimmt den vorhersehbaren Teil der
Sprache ab. Das Netz soll seine Rechenzeit nur in den Rest stecken; ein gelernter Schalter g mischt
p = g·p_Zähler + (1 − g)·p_Netz. Daten: 40 Mio. Train-Token, die das Pilot-Zählmodell nie gesehen hat
(`experiments/v5_prior.py`), Netz wie im LM-Vergleich (6 Schichten, d = 384, 23 Mio. Parameter), beide Arme
parallel mit je 2 Threads und gleicher Trainingszeit.

**Lauf 1 (6./7. Oktober, nach 2 von 6 h durch einen Container-Neustart verloren).** Geglättete Trainingsverluste in
nats/Token (je 5 Logpunkte):

| Schritt | klassisch | Residual v1 (Mischung) | Residual v1, Netz allein |
|---|---|---|---|
| 500 | 6,98 | 5,30 | 10,29 |
| 1000 | 6,47 | 5,29 | 11,24 |
| 1500 | 6,01 | 5,14 | 11,41 |
| 2000 | 5,99 | 5,31 | 11,26 |

Befund: v1 blieb auf dem Niveau des Zählers allein stehen, sein Netz wurde schlechter. Ursache: Solange p_Netz ≪
p_Zähler, gibt der Mischungsverlust dem Netz fast keinen Gradienten.

**Lauf 2 (`residual2`, `sh experiments/v5_run.sh 3`).** Verlust = Mischungsverlust + 0,5 · Kreuzentropie des Netzes
allein; Schalter startet bei g = 0,5 und sieht zusätzlich die gefundene KN-Ordnung und log₂ der ∞-gram-Kontextzahl
(nur Vorgeschichte). Vor dem Start hat eine unabhängige Code-Prüfung mit Gegenprüfung zwei echte Mängel gefunden, beide
behoben:
- **Fairness.** Die klassische Vergleichslinie bekommt dieselbe situationsabhängige Mischung nachträglich: λ je Bucket
  der drei Schalter-Merkmale (1.024 Buckets, EM auf val-A).
- **Messgröße.** Primär zählt jetzt Bits pro Byte mit dem Near-Duplicate-Filter der LM-Studie; Mischgewichte werden nur
  auf gefilterten val-A-Dokumenten geschätzt; Ergebnisse je Dokument für den gepaarten Bootstrap.

Jede Zwischenmessung (1, 2, 3 h) schreibt der Trainingsprozess sofort nach `results/v5/`. Auswertung:
`python -m experiments.v5_report`.

**Entscheidungsregel (vor Lauf 2 festgelegt).** Nach 3 h, Test-Satz, gefiltert:
- **Gewinn:** `residual2` (gelernte Mischung) ist mindestens 0,03 bpb besser als „klassisch + Zähler nachträglich, λ je
  Bucket“, und das 95-%-Intervall des Verhältnisses liegt unter 1. Dann wird das Verfahren ausgebaut.
- **Kein Gewinn:** Nächste Variante: Distillation aus der vollen Zählverteilung (Top-k aus `KNModel.distribution`)
  statt aus nur einer Wahrscheinlichkeit.
- **Zusätzlich berichtet:** der Effekt des Trainingsverfahrens allein, also beide Netze mit demselben nachträglichen
  Mischer.

**Ergebnis Lauf 2 (8. Oktober, `results/v5/`, `summary.json`).** Test, gefiltert, Bits pro Byte:

| | 1 h | 2 h | 3 h |
|---|---|---|---|
| klassisches Netz allein | 2,031 | 1,893 | 1,835 |
| Zähler allein | 1,674 | 1,674 | 1,674 |
| klassisch + Zähler, nachträglich (λ je Bucket) | 1,663 | 1,633 | 1,614 |
| residual2 + Zähler, nachträglich (λ je Bucket) | 1,661 | 1,629 | 1,612 |
| **residual2, gelernte Mischung** | **1,655** | **1,618** | **1,598** |
| Token gesehen je Arm | 3,3 Mio. | 7,0 Mio. | 10,8 Mio. |

**Entscheidung nach Regel §7: kein Gewinn.**
- Der Vorsprung beträgt nach 3 h −0,016 bpb, Verhältnis 0,9901 [0,9897; 0,9906]. Er ist statistisch klar, liegt aber unter
  der vorab festgelegten Schwelle von −0,03.
- Er wuchs von −0,008 über −0,014 auf −0,016 und flacht ab.
- Der Effekt des Trainingsverfahrens allein, also beide Netze mit demselben nachträglichen Mischer, ist −0,002.
- Der Gewinn kommt also vor allem vom gelernten, kontextabhängigen Schalter, nicht von einem besseren Netz.
- Nebenbefund: Zähler + Netz zusammen (1,598) schlagen nach 3 h CPU-Training sowohl den Zähler allein (1,674) als auch den
  6-h-Transformer der LM-Studie (1,638).

## 8. Lauf 3: Logit-Residual auf der vollen Zählverteilung (vor dem Start festgelegt)

**Verfahren (`experiments/v5_logres.py`).** p(w) ∝ exp(z_w + α·log q(w)). q ist die volle Verteilung des Pilot-Zählers
über alle 32.768 Wörter, exakt und während des Trainings berechnet (`experiments/v5_counter.py`). α = softplus(Schalter)
startet bei 1; die Verstärkung der letzten LayerNorm startet bei 0. Damit ist das ungelernte Modell exakt der Zähler
(gemessen: 1,70726 = 1,70726 bpb auf val-A). Der Gradient auf z ist p − one-hot und verschwindet nie: das Netz lernt
nur die Korrektur, die der Zähler braucht. Gleiche Netzgröße, Daten, Seed und Lernrate wie Lauf 2, fp32, beide Arme
parallel mit je 2 Threads.

**Prüfungen während des Laufs.**
- Jede Trainings-Charge und jedes Auswertungsfenster: q(Ziel) = Komponenten-Prior (relativer Fehler < 10⁻⁴).
- Jede 10. Charge: Σq = 1 (± 10⁻³).
- Kausalitätstest: Ändern eines Tokens lässt alle früheren Zeilen bitgleich.

**Gleiche Nachbearbeitung für jedes Modell X (`experiments/v5_posthoc.py`), nur auf gefiltertem val-A geschätzt.**
1. log-linear: log p′ = b·log p_X + a·log q − log Z, (a, b) per Maximum-Likelihood auf 24 Fenstern;
2. linear: λ je Bucket mit dem Komponenten-Prior.

Diese Nachbearbeitung kombiniert ein fertiges Netz mit dem Zähler auf genau die Art, die logres im Training lernt. Ein
Gewinn zeigt also, dass **gemeinsames Training** mehr bringt als nachträgliches Kombinieren.

**Entscheidungsregel nach 3 h, Test-Satz, gefiltert.**
- **Gewinn:** bpb(Pipeline(logres)) − bpb(Pipeline(B*)) ≤ −0,03, das 95-%-Intervall des gepaarten Bootstraps liegt unter
  1, und die Zähler-Werte aller Arme sind identisch.
  - B* = das bessere klassische Netz aus Lauf 2 und Lauf 3. Das schützt davor, dass logres das parallel laufende
    klassische Netz ausbremst.
- **Wiederholung mit Seed 43**, wenn −0,05 < Δ ≤ −0,03 ist oder die beiden klassischen Läufe nach der Pipeline um mehr
  als 0,015 bpb auseinanderliegen. Bestätigt gilt der Gewinn dann nur, wenn Δ(Seed 43) ≤ −0,02 und der Mittelwert
  ≤ −0,03 ist.
- **Zusätzlich berichtet, nicht entscheidend:**
  - die einfache lineare Regel aus §7;
  - logres allein und das Netz allein;
  - Δ nach 1 h und 2 h;
  - Pipeline(logres nach 2 h) ≤ Pipeline(klassisch nach 3 h), was einem Faktor ≥ 1,5 bei der Rechenzeit entspräche;
  - Token und Sekunden pro Schritt, getrennt nach Zähler- und Torch-Anteil.

**Danach (Lauf 4).** Bei Gewinn: bf16 auf den AMX-Einheiten dieser CPU (gemessen ≈ 1,9× schnellerer Trainingsschritt) für
beide Arme, Zähler-Merkmale auch als Netz-Eingabe (2×2-Vergleich), dann ein 6-h-Paar zur Messung des Faktors.

**Ehrliche Hochrechnung bis GPT-2-Niveau (1,04 bpb).**
- Nötig sind ein Modell mit ~124 Mio. Parametern und 1–3 Mrd. Token, also 5·10¹⁷–2·10¹⁸ Rechenschritte.
- Diese Maschine schafft ~1–2·10¹⁶ pro Tag in fp32 und ~3–5·10¹⁶ mit bf16, das sind 2–8 Wochen.
- Ein Zähler auf mehr Daten spart nach heutiger Schätzung 10–25 % davon.
- Es fehlen außerdem ≥ 1 Mrd. weitere Token Trainingstext.
- GPT-3-Niveau ist auf dieser Hardware nicht erreichbar.

**Ergebnis Lauf 3 (9. Oktober, `results/v5/run3/`).** Test, gefiltert, Bits pro Byte:

| | 1 h | 2 h | 3 h |
|---|---|---|---|
| klassisches Netz allein | 2,004 | 1,875 | 1,822 |
| klassisch + Zähler, nachträglich (λ je Bucket) | 1,658 | 1,627 | 1,609 |
| **logres (gemeinsam trainiert)** | **1,659** | **1,649** | **1,644** |
| Token (klassisch / logres) | 3,9 / 3,1 Mio. | 7,6 / 6,1 Mio. | 11,5 / 9,1 Mio. |

Nachbearbeitung nach Regel (log-linear, dann λ je Bucket), nach 3 h:
- logres: 1,6434;
- klassisch Lauf 3: 1,6137;
- klassisch Lauf 2: 1,6192.

Die beiden klassischen Läufe stimmen auf 0,005 überein. **Entscheidung: kein Gewinn.** logres liegt +0,030 bpb hinten,
Verhältnis 1,0184 [1,0171; 1,0197].

Befund: Das Logit-Residual startet exakt beim Zähler, lernt aber fast nichts dazu (1,674 → 1,644 in 3 h). Das
klassische Netz plus nachträgliche Mischung kommt auf 1,609. Mit dem multiplikativen Prior muss das Netz eine
schwierigere Korrektur-Funktion lernen. Dazu kostet die volle Verteilung 20 % Durchsatz. Bei diesem Rechenbudget ist
die additive Mischung (Lauf 2) der bessere Weg, den Zähler zu nutzen. Der Hebel für GPT-2-Niveau bleibt die
Rechenleistung pro Stunde (§9).

## 9. Lauf 4: schnelles Trainingsrezept „fast-v1“ (vor dem Start festgelegt)

**Warum.**
- Lauf 2 und Lauf 3 zeigen: Der Zähler hilft bei wenig Rechenzeit, aber nur um 0,01–0,02 bpb.
- Den Weg zu GPT-2-Niveau entscheidet die Rechenleistung pro Stunde. Eine Recherche mit mehreren Agenten hat die Hebel für
  diese 4-Kern-CPU nach Literatur und Messung geordnet (Speedrun-Rekorde, Porian et al. 2024, Marek et al. 2025,
  Hägele et al. 2024, Bergsma et al. 2025, Wen et al. 2025).

**fast-v1 (`experiments/v5_fast.py`), gleiche Breite, Tiefe, Batch und Daten wie das klassische Netz.**
- **System:**
  - jemalloc als Speicherverwaltung; gemessen: 17 % der CPU-Zeit gingen bisher in Seitenfehler und Kernel.
  - bf16 auf den AMX-Einheiten.
  - Kopf und Verlust in Blöcken, ohne die 4.096 × 32.768-Matrix.
  - fused AdamW.
- **Modell:**
  - RMSNorm, QK-Norm + RoPE, ReLU², ohne Bias.
  - Null-initialisierte Ausgänge, eigener Ausgabekopf mit Soft-Cap 30.
  - Gehashte Bigramm-Eingabetabelle.
- **Training:**
  - AdamW mit β₂ aus der Suche, Gewichtsabnahme nur auf Blockmatrizen, 150 Aufwärmschritte.
  - Konstante Lernrate, lineare Abnahme auf 0 im letzten Drittel.
  - Dokumente ohne Zurücklegen gepackt, Aufmerksamkeit nur im eigenen Dokument.
- **Geprüft:**
  - Verlustfunktion gleich der Referenz (Fehler 2·10⁻⁹ in fp32);
  - Kausalität und Dokumentmaske;
  - Auswertungs-Weg gleich dem Trainings-Weg;
  - Startverlust = ln V.

**Ablauf (`sh experiments/v5_run4.sh`):**
1. Lernrate {2·10⁻³, 4·10⁻³} × β₂ {0,99; 0,999}, je 45 min, Auswahl nach val-A.
2. Je 3 h klassisch (A) gegen fast-v1 (B), auf getrennte Kerne gepinnt, Messung nach 1, 2 und 3 h.

**Entscheidungsregel.**
- **fast-v1 wird neue Referenz**, wenn B nach 3 h (Netz allein, Test, gefiltert) mindestens 0,08 bpb besser ist als A und
  das 95-%-Intervall des Verhältnisses unter 1 liegt.
- **Zeit-Faktor:** 3 h geteilt durch die früheste Messung von B, die A nach 3 h erreicht. Das ist eine Untergrenze, weil
  B dort noch nicht abgekühlt ist.
- **Ziel für den Langlauf zu GPT-2-Niveau:**
  - Faktor ≥ 3 bei 2 Threads;
  - mit 4 Threads in einem Prozess ≈ 1 Woche bis 1,04 bpb (Spanne 4–14 Tage);
  - Modell d = 640–768, 12 Schichten, Kontext bis 1.024, 0,5–0,8 Mrd. Token.

**Ergebnis Lauf 4 (9. Oktober, `results/v5/run4/`, `summary_fast.json`).** Lernraten-Suche (45 min, val-A):

| Lernrate | β₂ = 0,99 | β₂ = 0,999 |
|---|---|---|
| 2·10⁻³ | **1,814** | 1,847 |
| 4·10⁻³ | 1,847 | 1,867 |

3-h-Vergleich, Test, gefiltert, Bits pro Byte:

| | 1 h | 2 h | 3 h |
|---|---|---|---|
| klassisch, Netz allein | 1,999 | 1,869 | 1,818 |
| **fast-v1, Netz allein** | **1,799** | **1,689** | **1,579** |
| klassisch + Zähler (λ je Bucket) | 1,657 | 1,625 | 1,608 |
| **fast-v1 + Zähler (λ je Bucket)** | **1,603** | **1,556** | **1,498** |
| Token (klassisch / fast-v1) | 4,0 / 7,2 Mio. | 7,8 / 14,3 Mio. | 11,5 / 21,0 Mio. |

**Entscheidung nach Regel §9: fast-v1 wird neue Referenz.**
- Vorsprung nach 3 h: −0,239 bpb, Verhältnis 0,8687 [0,8658; 0,8718].
- Zeit-Faktor ≥ 3: fast-v1 nach 1 h (1,799, noch ohne Abnahme der Lernrate) ist besser als klassisch nach 3 h (1,818).
- Durchsatz 1,8× (7,0 statt 3,9 Mio. Token/h bei 2 Threads); der Rest kommt vom Rezept.
- **Einordnung:**
  - fast-v1 nach 3 h auf 2 Kernen schlägt den 6-h-Transformer der LM-Studie (1,638).
  - Mit dem Pilot-Zähler gemischt (1,498) schlägt es auch das beste reine Zählmodell auf 300 Mio. Token (1,514).

## 10. Langlauf zu Stufe 1 (GPT-2-Niveau), vor dem Start festgelegt

**Startbedingung.** fast-v1 wird nach der Regel aus §9 zur neuen Referenz.

**Aufbau (`experiments/v5_long.py`, Steuerung `experiments/v5_long_run.sh`).**
- **Rezept:** fast-v1 (§9) ohne Bigramm-Tabelle. Die Tabelle wäre bei d = 640 mit Optimierer-Zustand 1,3 GB groß und passt
  nicht in den Neustart-Speicher auf der Platte; ihr Einzelbeitrag ist in Lauf 4 nicht gemessen.
- **Modellgröße:** Ein kurzer Durchsatz-Test misst d ∈ {512, 640, 768} mit 12 Schichten. Gewählt wird das größte Modell,
  das 0,6 Mrd. Token in ≤ 7 Tagen schafft.
- **Lernrate und Optimierer:** Lernrate 2·10⁻³ · 384/d (bestes Ergebnis der Suche, umgerechnet nach Breite), β₂ = 0,99,
  300 Aufwärmschritte, lineare Abnahme auf 0 in den letzten 30 % der Token, 8.192 Token pro Schritt.
- **Daten:** der ganze Train-Split (285 Mio. Token, getrennt von val/test), also 2,1 Epochen. Der Kontext wächst
  256 → 512 → 1.024.
- **Neustartfest:**
  - stündlich voller Zustand in den Arbeitsspeicher und bf16-Gewichte auf die Platte (`models/lm/v5/long_latest.pt`);
  - der Zeitplan richtet sich nach Token;
  - nach einem Abbruch startet die Überwachung neu.
- **Lernkurve:** alle 6 h Trainingszeit auf 150 val-A-Dokumenten (Fenster 1.024, Schritt 512) in
  `results/v5/long/curve.jsonl`.

**Messung und Entscheidung.**
- **Messgröße:** Test-Satz, gefiltert, Netz allein, Fenster 1.024 / Schritt 512. GPT-2 small wurde in der LM-Studie
  genauso gemessen (`experiments/lm_gpt2_ref.py`).
- **Stufe 1 erreicht:** bpb ≤ 1,04. Andernfalls wird der gemessene Wert mit dem Abstand berichtet und der Lauf mit
  weiteren Token verlängert (neue Abnahme-Phase ab dem letzten konstanten Stand).
- **Zusätzlich berichtet:** die Mischung mit dem Zähler (λ je Bucket) und val-A.
- **Nachtrag 11. Oktober, vor dem Ergebnis (Regel unverändert):** Die Endmessung (`v5_long.py eval`) rechnet die
  Mischung mit zwei Zählern: dem vollen Zählmodell (exakter Teil von ENGRAMM-LM, alle 285 Mio. Train-Token,
  `models/lm/main/eval`) und dem Pilot-Zähler aus Lauf 2–4 (30 Mio.). Zählergewichte und λ (global und je Bucket)
  werden nur auf gefiltertem val-A angepasst. Dazu ein gepaarter Dokument-Bootstrap gegen GPT-2 small auf denselben
  gefilterten Test-Dokumenten (`models/lm/gpt2/eval_test.json`, Bytes je Dokument geprüft) für das Netz allein und
  die beste Mischung. Vorher fehlte beides im Code; gemessen hatte die Endmessung nur das Netz allein.
- **Nachtrag 14. Oktober, vor dem Ergebnis bei 600 Mio. Token (Verlängerung festgelegt):**
  - **Lücke:** Die Regel oben verlängert „ab dem letzten konstanten Stand“. Diesen Stand (420 Mio. Token, Beginn der
    Abnahme) hat `v5_long.py` nicht gesichert, es hielt nur den jeweils letzten Stand. Er ist überschrieben.
  - **Ersatz:** Abzweig bei 470,5 Mio. Token, am 14. Oktober um 16:37 UTC als voller fp32-Stand (Gewichte,
    AdamW-Momente, Datenposition) auf die RAM-Disk kopiert. Die Lernrate lag dort bei 8,63·10⁻⁴, 72 % des Höchstwerts.
  - **Verlängerung**, nur wenn Stufe 1 bei 600 Mio. verfehlt ist (`experiments/v5_long_ext_run.sh`, Parameter fest in
    `results/v5/long_ext1/config.json`, startet über `experiments/v5_long_resume.sh` nach der Endmessung):
    - ab dem Abzweig konstante Lernrate 8,63·10⁻⁴ bis 798 Mio. Token, dann linear auf 0 bis 1,14 Mrd. Token;
      Kontext durchgehend 1.024, gleiche Datenreihenfolge;
    - 1,14 Mrd. Token sind 4 Epochen der 285 Mio. Train-Token. Darüber bringen wiederholte Token deutlich weniger als
      neue (Muennighoff et al. 2023);
    - Messung und Regel wie oben: Test, gefiltert, Netz allein ≤ 1,04; dazu Mischungen und Bootstrap gegen GPT-2;
    - Dauer bei 3,9 Mio. Token/h: rund 170 h, also gut 7 Tage;
    - geht der RAM-Abzweig vor dem ersten Speicherstand der Verlängerung verloren (Container-Neustart), startet sie
      von den Endgewichten bei 600 Mio. Token (Optimierer über 300 Schritte neu aufgewärmt), sonst unverändert.
  - **Erwartung, vorab:** In der konstanten Phase sank val-A je Verdopplung der Token um etwa 0,05 bpb (1,439 bei
    175 Mio. → 1,377 bei 416 Mio.). 1,14 statt 0,6 Mrd. Token sind das 1,9-Fache, also etwa −0,045 gegenüber dem
    Ergebnis bei 600 Mio. Stufe 1 erreicht die Verlängerung damit nur, wenn der Testwert bei 600 Mio. höchstens etwa
    1,09 beträgt. Sonst bleibt für Stufe 1 der H100-Lauf (§11).

**Verlauf des Langlaufs (Stand 16. Oktober, 00:00 UTC; bei 600 Mio. Token beendet, Endmessung unten).**

| Training | Token | val-A, bpb (Fenster 1.024) |
|---|---|---|
| 6 h | 29 Mio. | 1,762 |
| 12 h | 60 Mio. | 1,640 |
| 18 h | 81 Mio. | 1,590 |
| 24 h | 93 Mio. | 1,562 |
| 30 h | 105 Mio. | 1,550 |
| 36 h | 137 Mio. | 1,546 |
| 42 h | 175 Mio. | **1,439** (Kontext 512 seit 150 Mio.) |
| 48 h | 212 Mio. | 1,430 |
| 54 h | 250 Mio. | 1,417 |
| 60 h | 283 Mio. | 1,413 |
| 66 h | 314 Mio. | 1,396 |
| 72 h | 339 Mio. | 1,392 |
| 78 h | 363 Mio. | 1,379 |
| 84 h | 389 Mio. | 1,368 |
| 90 h | 416 Mio. | 1,377 |
| 96 h | 442 Mio. | 1,360 |
| 102 h | 466 Mio. | 1,333 |
| 108 h | 490 Mio. | 1,317 |
| 114 h | 517 Mio. | 1,301 |
| 120 h | 542 Mio. | 1,281 |
| 126 h | 566 Mio. | 1,260 |
| 132 h | 592 Mio. | 1,243 |

- **Unterbrechungen:** Zwei Container-Neustarts (9./10. Oktober) löschten die RAM-Disk. Der Lauf setzte jeweils von den
  Gewichten auf der Platte fort, bei 75,5 Mio. Token. Gesichert wird jetzt alle 20 min.
  `experiments/v5_long_resume.sh` startet den Lauf neu, wenn er nicht läuft.
- **Hardware-Wechsel:** Seit dem zweiten Neustart läuft die Umgebung auf einem anderen Rechner (Xeon @ 2,8 GHz ohne AMX
  und ohne AVX512-BF16). bf16 wurde dort nachgebildet: 6× langsamer, Speicher lief voll, 2 h Absturzschleife ohne
  Fortschritt.
  - Jetzt wird fp32 gerechnet, wenn die CPU kein bf16 kann.
  - Tempo hier: 2,0 Mio. Token/h bei Kontext 256, 1,7 Mio. bei Kontext 1.024. Auf dem ursprünglichen Rechner mit bf16
    waren es 5,1 bzw. 4,0 Mio.
- **Unverändert:** Modell, Token-Budget und Entscheidungsregel.
- **Restdauer nach Phasen** (Stand 101 Mio. Token nach 28,2 h; die frühere Schätzung „rund 12 Tage" rechnete mit
  konstantem Tempo und war zu knapp, weil längerer Kontext jedes Token teurer macht):

  | Phase | Token | Tempo hier (fp32) | Dauer |
  |---|---|---|---|
  | Kontext 256 | 101 → 150 Mio. | 2,1 Mio./h, gemessen im Lauf | ~23 h |
  | Kontext 512 | 150 → 300 Mio. | ~1,85 Mio./h, gerechnet (Aufmerksamkeitsanteil) | ~81 h |
  | Kontext 1.024 | 300 → 600 Mio. | 1,45–1,73 Mio./h, zwei Benchmarks hier | ~175–205 h |

  Zusammen 280–310 h Training, dazu die Messpausen (~10 min je Kurvenpunkt) und die Endmessung. Ende auf diesem
  Rechner also etwa am 23. Oktober (± 1 Tag), sofern weder ein Neustart noch ein Hardware-Wechsel dazwischenkommt.
  Gemessen an der Rechenzeit ist der Lauf damit zu ≈ 9 % fertig, gemessen an den Token zu 17 %.
- **Dritter Neustart und zweiter Hardware-Wechsel (11. Oktober).** Der Container fiel gegen 03:30 UTC aus und kam erst
  um 09:31 wieder. Die Gewichte von 03:24 lagen auf der Platte (109,1 Mio. Token), verloren gingen ≤ 20 min Training.
  - Neuer Rechner: Xeon @ 2,3 GHz **mit** AMX und AVX512-BF16; bf16 schaltet sich von selbst wieder ein.
  - **Speicherfehler gefunden:** Der Prozess wuchs unter bf16 um 100–370 MB je Schritt und wurde nach 4 min bei
    14,3 GB beendet. Ursache war die jemalloc-Einstellung `oversize_threshold:1` zusammen mit „Speicher nie
    zurückgeben" (`dirty/muzzy_decay_ms:-1`). Gemessen je 12–24 Schritte (`VmRSS`, Kontext 256):

    | Allokator | Speicher | s/Schritt |
    |---|---|---|
    | jemalloc wie bisher (`oversize_threshold:1`, kein Zurückgeben) | wächst ohne Ende (4,5 → 7,1 GB in 12 Schritten) | 4,7 |
    | glibc | 5,0 GB, flach | 5,7 |
    | jemalloc mit Zurückgeben (Standard bzw. 30 s) | 3,2–3,3 GB, flach | 8,4 |
    | **jemalloc ohne `oversize_threshold:1`, kein Zurückgeben** | **5,4 GB, flach (auch bei Kontext 512/1.024)** | **4,2–4,7** |

    Übernommen ist die letzte Zeile. Das Wachstum am 10. Oktober („bf16 nachgebildet, Speicher lief voll") hatte
    vermutlich dieselbe Ursache; die Verlangsamung durch die Nachbildung war davon unabhängig.
  - **Speicherschutz:** Übersteigt der Prozess 9 GB, sichert er den vollen Zustand in die RAM-Disk und endet mit Code 75;
    die Überwachung startet ihn neu, ohne erneutes Aufwärmen. Der Beginn eines laufenden Aufwärmens steht jetzt im
    Zustand (`warm_from`), damit ein Neustart mitten im Aufwärmen nicht sofort die volle Lernrate setzt.
  - **Tempo hier mit bf16:** 6,4–7,0 Mio. Token/h bei Kontext 256 (im Lauf), 5,8–6,4 Mio. bei 512 und 5,3–5,6 Mio. bei
    1.024 (Messung ohne Last). Restdauer ab 109,8 Mio. Token: ~6 h + ~25 h + ~56 h ≈ 87 h Training. Ende also etwa am
    **15. Oktober**, solange dieser Rechner bleibt; auf einem Rechner ohne bf16 gilt die Tabelle oben.
- **Vierter Neustart (12. Oktober, ≈ 08:10–09:13 UTC).** Die RAM-Disk war wieder leer; fortgesetzt von den Gewichten
  auf der Platte (08:02, 250,4 Mio. Token, Optimierer neu aufgewärmt), verloren ≤ 20 min Training plus Ausfallzeit.
  Vorher war die Platte durch Downloads der Preisrecherche auf 203 MB frei gefallen (bereinigt: 353 MB). Seitdem
  überspringt der Lauf eine fehlgeschlagene Plattensicherung (volle Platte) mit Warnung und löscht die halbe
  Temporärdatei, statt abzubrechen; der volle Zustand liegt ohnehin auf der RAM-Disk.
- **Prüfungen beim 36-h-Punkt** (`results/v5/long/probe_36h.json`, je 150 val-A-Dokumente):
  - **Fenster gegen Kontext:** Derselbe Checkpoint (134,7 Mio. Token) kommt mit Fenster 256 auf 1,477 bpb, mit
    Fenster 1.024 auf 1,527. Mit mehr Kontext wird das Modell also schlechter, weil es Positionen 256–1.023 noch
    nie trainiert hat. Die Kurve mit Fenster 1.024 unterschätzt den Fortschritt, bis der Kontext wächst (512 ab
    150 Mio. Token, 1.024 ab 300 Mio.). Der Trainingsverlust fiel zwischen 100 und 130 Mio. Token um ≈ 0,08
    nats/Token, die Kurve im selben Abschnitt nur um 0,005.
  - **bf16-Speicherung:** Gewichte in bf16 auf der Platte und der fp32-Zustand derselben Sicherung ergeben 1,538893
    gegen 1,538899. Für die Endmessung ist es gleich, welche Datei sie lädt.
  - **Rauschen zwischen Checkpoints:** Bei konstanter Lernrate liegen Checkpoints 2 Mio. Token auseinander bis zu
    0,02 bpb auseinander (1,527 / 1,546 / 1,539). Einzelne Kurvenpunkte sind entsprechend unsicher; die Abnahme der
    Lernrate am Ende glättet das.
- **Textproben:** je Kurvenpunkt fünf feste Prompts mit festem Seed (`results/v5/long/samples_<Token>M.json`). Bei
  101–104 Mio. Token: englische Sätze mit plausibler Form und frei erfundenem Inhalt; die Wissensfrage wird nicht
  beantwortet, Deutsch ergibt Buchstabensalat (Korpus englisch). Die App nutzt das Netz nicht; für Nutzer ändert der
  Lauf erst mit einem Einbau (Phase R4) etwas.

**Ergebnis bei 600 Mio. Token (Endmessung, 15. Oktober 23:54 UTC, `results/v5/long/eval_final.json`).**
Modell mit 59,0 Mio. Parametern im Rumpf (d = 640, 12 Schichten), 600,0 Mio. Token (2,1 Epochen der Train-Daten),
133,8 h Training auf 4 CPU-Kernen, 8 Neustarts ohne Verlust des Fortschritts. Fenster 1.024, Schritt 512.

| Messung, bpb | val-A (767 Dok.) | Test (1.137 Dok.) |
|---|---|---|
| **Netz allein, gefiltert** | 1,1353 | **1,1413** |
| Netz allein, ungefiltert | 1,1287 | 1,1343 |
| Zähler „main“ allein (285 Mio. Token) | 1,5165 | 1,5296 |
| Netz + Zähler „main“, λ global (0,092) | 1,1187 | 1,1254 |
| Netz + Zähler „main“, λ je Bucket | 1,1143 | 1,1220 |
| Netz + Zähler „pilot“, λ je Bucket | 1,1310 | 1,1367 |

Gegen GPT-2 small auf denselben 1.092 gefilterten Test-Dokumenten (gepaarter Bootstrap, 95-%-Intervalle):

| Variante | bpb | GPT-2 small | Verhältnis |
|---|---|---|---|
| Netz allein | 1,141 [1,124; 1,159] | 1,039 [1,021; 1,057] | 1,099 [1,089; 1,109] |
| Netz + Zähler „main“ (je Bucket) | 1,122 [1,105; 1,140] | 1,039 [1,021; 1,057] | 1,080 [1,069; 1,091] |

- **Stufe 1: verfehlt.** 1,1413 gegen die Schwelle 1,04, Abstand 0,101 bpb. Das Intervall des Verhältnisses schließt
  1 deutlich aus. Auch die beste Mischung (1,122) liegt klar darüber; Stufe 1 entscheidet ohnehin das Netz allein.
- **Einordnung:** GPT-2 small hat 124 Mio. Parameter und lernte aus 40 GB Text (WebText). Dieses Netz hat 59 Mio.
  Parameter im Rumpf und lernte aus 1,28 GB Text auf einem 4-Kern-Rechner. Der Abstand beträgt 10 %. Das kleine
  Transformer-Modell der LM-Studie (23 Mio. Parameter, 6 h CPU) lag bei 1,638, ENGRAMM-LM bei 1,514.
- **Kurve gegen Endmessung:** Die Kurvenpunkte (erste 150 val-A-Dokumente) lagen zuletzt bei 1,243, das volle val-A
  liegt bei 1,135. Die ersten 150 Dokumente sind schwerer als der Durchschnitt. Die Kurve zeigte den Verlauf, nicht
  die Höhe. Meine Erwartung vor dem Ergebnis (1,15–1,30, §11) war damit etwas zu pessimistisch.
- **Zähler:** Mit dem fertigen Netz bringt die Mischung mit dem vollen Zählmodell noch 0,019 bpb auf Test (λ global
  0,09), der Pilot-Zähler 0,005.
- **Textproben** bei 600 Mio. Token (`results/v5/long/samples_600M.json`): flüssiges, meist grammatisches Englisch mit
  erfundenen Fakten („Albert Einstein was born in 1984, and currently lives in … New York City“). Die Wissensfrage
  wird nicht beantwortet, Deutsch bleibt Wortsalat (Korpus englisch).
- **Nach der Regel:** Die Verlängerung `long_ext1` (Nachtrag 14. Oktober) läuft seit 15. Oktober 23:55 UTC. Abzweig
  aus dem vollen Stand bei 470,5 Mio. Token, Lernrate 8,63·10⁻⁴ konstant bis 798 Mio., dann linear auf 0 bis
  1,14 Mrd. Token, rund 7 Tage. Vorab-Erwartung: etwa −0,045, also Test um 1,10. Stufe 1 ist damit nicht zu erwarten,
  denn eine Chance bestand nur bei höchstens etwa 1,09 bei 600 Mio. Stufe 1 bleibt Aufgabe des H100-Laufs (§11).
- **Gewichte des 600-Mio.-Stands:** Nach dem ersten Plattenstand der Verlängerung (16. Oktober, 00:15 UTC) habe ich
  die bf16-Gewichte des Endstands von der Platte gelöscht. Neben dem Stand der Verlängerung samt Temporärdatei
  war kein Platz mehr. Die Messwerte und Textproben stehen im Repo. Der fp32-Stand auf der RAM-Disk ging beim
  Container-Neustart am 16. Oktober um 02:02 UTC verloren.
- **Neustart während der Verlängerung (16. Oktober, 02:02 UTC):** Die RAM-Disk war leer. `v5_long_resume.sh` lief
  beim Containerstart von selbst, installierte Torch neu und setzte die Verlängerung von ihrem Plattenstand (01:56,
  479,7 Mio. Token, Optimierer neu aufgewärmt) fort. Verloren gingen rund 6 min Training.
- **Verlauf der Verlängerung** (val-A, erste 150 Dokumente, Fenster 1.024, wie die Kurve des Hauptlaufs;
  `results/v5/long_ext1/curve.jsonl`; Stand 17. Oktober, 12:00 UTC). Zum Vergleich der Hauptlauf beim gleichen
  Trainingsstand, dort schon mit abnehmender Lernrate:

  | Training | Token | Lernrate | val-A, bpb | Hauptlauf |
  |---|---|---|---|---|
  | 108 h | 493 Mio. | 8,63·10⁻⁴ (konstant) | 1,336 | 1,317 (490 Mio., 7,4·10⁻⁴) |
  | 114 h | 506 Mio. | 8,63·10⁻⁴ (konstant) | 1,330 | 1,301 (517 Mio., 5,5·10⁻⁴) |
  | 120 h | 514 Mio. | 8,63·10⁻⁴ (konstant) | 1,328 | 1,281 (542 Mio., 3,9·10⁻⁴) |
  | 126 h | 524 Mio. | 8,63·10⁻⁴ (konstant) | 1,331 | 1,260 (566 Mio., 2,3·10⁻⁴) |
  | 132 h | 536 Mio. | 8,63·10⁻⁴ (konstant) | 1,332 | 1,243 (592 Mio., 5,7·10⁻⁵) |
  | 138 h | 556 Mio. | 8,63·10⁻⁴ (konstant) | 1,329 | – (Hauptlauf endete bei 133,8 h) |

- **Weiterer Neustart und Rechnerwechsel (16. Oktober, 07:06 UTC):** Die RAM-Disk war wieder leer. Die Verlängerung
  lief vom Plattenstand bei 499,4 Mio. Token weiter (Optimierer neu aufgewärmt, rund 20 min verloren). Der neue Rechner
  (Xeon @ 2,8 GHz, 4 Kerne) hat weder AMX noch AVX512-BF16. Gerechnet wird in fp32 mit 1,55–1,59 Mio. Token/h statt
  4,5–5,0 Mio. Der Speicher bleibt bei 6,35 GB. Bleibt dieser Rechner, dauert der Rest bis 1,14 Mrd. Token rund
  17 Tage statt 6. Ein bf16-Rechner nach einem späteren Neustart verkürzt das wieder. Regel und Zeitplan in Token
  bleiben unverändert.
- **Prüfung und Absicherung des Verlängerungs-Codes (16. Oktober, vor dem Ergebnis):** Drei unabhängige Prüfer
  (Zeitplan und Fortsetzen, Supervisor-Skripte, Endmessung), jeder Befund von drei Gegenprüfern angegriffen.
  Bestätigt (3 von 3) ist eine unwahrscheinliche, aber schwere Lücke. Scheitert die Plattensicherung wegen
  vollen Platzes, bleibt das nur im RAM-Log sichtbar. Wird dann die RAM-Disk nach dem Trainingsende, aber vor
  der Endmessung geleert, hätte die Endmessung einen veralteten Plattenstand stumm als Ergebnis eingetragen.
  Behoben in `v5_long.py`, gilt ab dem nächsten Prozessstart (der laufende Prozess bleibt unberührt):
  - Scheitert die atomare Plattensicherung, wird die vorhandene Datei an Ort und Stelle überschrieben (braucht
    keinen zusätzlichen Platz). Jede Abweichung steht dauerhaft in `results/v5/<Lauf>/disk_checkpoint.log`.
  - `done.json` vermerkt, ob die letzte Plattensicherung gelungen ist.
  - Die Endmessung (`--tag final`) bricht ab, wenn der geladene Stand weniger Token hat als `done.json`, und
    schreibt Datei und Genauigkeit des geladenen Stands in das Ergebnis.
  Messung, Regel und Zeitplan der Verlängerung bleiben unverändert.

## 11. Stufe 1 auf einer gemieteten H100 (vor dem Lauf festgelegt, 12. Oktober)

**Anlass.** Der CPU-Langlauf (§10) kommt auf dieser Hardware wahrscheinlich nur auf 1,15–1,30 bpb; der Container
startete viermal neu. Eine H100 (~4 $/h) rechnet etwa 300-mal schneller. Ablauf und Anleitung: `docs/H100_ANLEITUNG.md`.

**Aufbau.**
- Modell: Rezept fast-v1 wie §10, Größe GPT-2 small (d = 768, 12 Schichten, 12 Köpfe), Kontext 1.024 von Anfang an
  (keine Stufen, damit die Messung mit Fenster 1.024 nicht auf ungeübte Positionen trifft, vgl. Prüfung beim 36-h-Punkt).
- Daten: Basis (bitgleich zum CPU-Rechner, SHA-256 je Datei) und C4-en-Teile 1–36, nur Dokumente des Trainings-Hash-
  Bereichs (`split_of`), SHA-256 der Quelldateien vorab festgelegt; zusammen ≈ 6,4 Mrd. Token. Training bis 6 Mrd. Token,
  Zeitgrenze 5,5 h (die Tokenzahl wird nach den ersten Schritten auf die Zeitgrenze gekürzt, vor der Abnahme-Phase).
- Lernrate: drei kurze Läufe (1·10⁻³, 2·10⁻³, 4·10⁻³; je 200 Mio. Token auf den Basisdaten), gewählt nach val-A
  (gleichauf innerhalb 0,003 bpb: die kleinere). 524.288 Token je Schritt, β₂ = 0,95, 300 Aufwärmschritte, Abnahme in den
  letzten 30 %.

**Messung und Entscheidung (Regel aus §10, angewendet auf den tatsächlichen Trainingstext).**
- Der Filter aus §10 schließt Test-Dokumente aus, von deren 13-Token-Fenstern ≥ 20 % im Trainingstext vorkommen. Mit
  dem Zusatztext wird dieselbe Regel auf Basis + Zusatz angewendet (`results/v5/h100/contamination.json`). Probe mit
  einem einzigen Zusatzteil: 58 statt 45 Test-Dokumente betroffen — mit der alten Liste allein stünden Beinahe-Kopien
  von Trainingsdokumenten im Test, der Wert wäre geschönt.
- **Stufe 1 erreicht:** Test, erweiterter Filter, Netz allein, Fenster 1.024 / Schritt 512: bpb ≤ 1,04.
- Zusätzlich berichtet: derselbe Wert mit der alten Filterliste, gepaarter Dokument-Bootstrap gegen GPT-2 small auf
  denselben Dokumenten (beide Filter), val-A, Textproben; die Mischung mit den Zählmodellen rechne ich anschließend auf
  dem CPU-Rechner aus den gespeicherten Token-Wahrscheinlichkeiten.
- Selbstprüfungen vor dem Lauf (CPU): der Prüfcode reproduziert `results/lm/dedup.json` auf allen vier Prüfsätzen exakt;
  der ganze Trainings- und Messpfad läuft im Kleintest (`h100_train smoke`); C4-Teil 1 wurde echt geladen, geprüft,
  tokenisiert (353.856 Dokumente, 171 Mio. Token, 2.462 aus val/test-Bereichen ausgelassen) und zusammengeführt.

**Nachtrag 12. Oktober abends, vor dem Lauf (Budget; Messregel unverändert).** Das Guthaben ist auf 30 $ festgelegt.
- Kostenbremse: Pod-Zeit höchstens 25 $ (4,01 $/h), gemessen über alle Pod-Sitzungen; danach stoppt sich der Pod selbst
  (`experiments/h100_meter.sh`). Das Haupttraining bekommt als Frist „Grenze − bisherige Pod-Zeit − 30 min“ und setzt
  seine Tokenzahl nach gemessenem Durchsatz darauf (Obergrenze 10 Mrd.; über 6,4 Mrd. wird der Text neu gemischt ein
  zweites Mal gelesen). Erwartet: ~4–4,5 h Training statt 5,5 h, also weniger Token als oben geplant.
- Divergenz: weiter ab dem letzten Speicherstand mit halber Lernrate (kein Neubeginn); eine zweite Divergenz beendet
  das Training mit der Endmessung des letzten gesicherten Stands.
- Fortsetzungs-Stand: Der letzte Stand vor der Lernraten-Abnahme wird mit dem Modell gesichert. Wird Stufe 1 verfehlt,
  gilt §10: Verlängerung mit weiteren Token ab diesem Stand (neue Abnahme-Phase), auf eigener GPU oder neu gemietet.
- Die Mischung mit den Zählmodellen rechnet `experiments/h100_mix.py` auf dem CPU-Rechner: Zählergewichte und λ nur auf
  gefiltertem val-A, Test mit beiden Filtern, der erweiterte zuerst; die beste Mischung gepaart gegen GPT-2 small.
  Stufe 1 entscheidet weiterhin allein das Netz (Regel oben).

**Nachtrag 16. Oktober, vor dem Lauf (Verbesserungen nach einer Prognose; Messregel unverändert).**
- Prognose des vorbereiteten Laufs (vier unabhängige Schätzwege, drei Gegenprüfungen, eine Überarbeitung; alles nur
  Lesen und kleine Rechnungen, `results/v5/h100_forecast_20261016.json`): Test (erweiterter Filter, Netz allein)
  Median 1,041 bpb (p10 1,008, p90 1,075), P(Stufe 1) ≈ 0,46. Erwartet ≈ 4,6 Mrd. Token bei ≈ 300 k Token/s
  (260–345 k). Mit den Änderungen unten: Median ≈ 1,030, P ≈ 0,62. Das sind Schätzungen, keine Messung.
- Offenlegung: Neben val-A und Literatur nutzte die Prognose vorhandene Test-Auswertungen des CPU-Rechners, getrennt
  nach Quelle (GPT-2 small auf den vom Filter ausgeschlossenen gegenüber den behaltenen C4-Test-Dokumenten), nur um die
  Wirkung des erweiterten Filters zu schätzen. Keine Änderung wurde nach Test-Werten gewählt.

| Änderung | Begründung | Schätzung |
|---|---|---|
| Trainings-Attention blockweise (FlexAttention, Maske „kausal UND gleiches Dokument“) | dieselbe Rechnung wie die bisherige dichte Maske, ohne die leeren Blöcke (≈ 42 % der 128×128-Blöcke sind aktiv); die dichte Maske verhindert bisher den schnellen Kern | +15–30 % Token, ≈ −0,006 bpb |
| Verlust auf der GPU summiert, einmal je Schritt gelesen | bisher ein Warten der GPU nach jedem der 16 Teil-Batches; rechnerisch identisch | +1–3 % Token |
| Tokenzahl an jedem Speicherpunkt nachgeführt, solange frac < 0,65 (neu frac < 0,68, nie über der Obergrenze) | eine spätere Verlangsamung (z. B. Rückfall auf die dichte Attention) schneidet die Abnahme-Phase nicht mehr ab | schützt das ≈ 2-%-Risiko einer gekappten Abnahme |
| Lernrate Hauptlauf = Gewinner der Suche × 0,5, begrenzt auf [1·10⁻³, 2·10⁻³] (4e-3 → 2e-3, 2e-3 → 1e-3, 1e-3 → 1e-3); der Divergenz-Rückfall halbiert diesen Wert | die Suche läuft 200 Mio. Token, der Hauptlauf ≈ 20-mal länger; die beste Rate sinkt mit dem Horizont (Bjorck et al. 2024, arXiv 2409.19913; Referenz modded-nanogpt AdamW: 1,8·10⁻³ bei ≈ 5 Mrd. Token). Die Suche selbst bleibt unverändert | ≈ −0,001, weniger Divergenz-Risiko |
| WikiText-103-Trainingsdokumente der Basis dreimal zusätzlich im Strom (×4; je Kopie 29.245 Dokumente, 113.064.374 Token, ausgewählt über `train.keys.jsonl`, Anzahl geprüft) | die Messsätze sind nach Aufbau gemischt (val-A 37,5 % der Bytes aus WikiText; Basis-Training 40 %), der H100-Strom hätte nur 1,75 %; jetzt ≈ 6,7 %, bei 4,6 Mrd. Token ≈ 2,8 Durchgänge – im fast verlustfreien Bereich (Muennighoff et al. 2023, arXiv 2305.16264). Der Strom wächst von ≈ 6,44 auf ≈ 6,78 Mrd. Token (jede Epoche dokumentweise neu gemischt). Kontaminationsprüfung unberührt (derselbe Text wie in der Basis) | ≈ −0,004 |

- Schutz der Attention-Änderung: nur mit CUDA, torch.compile und torch ≥ 2.6. Beim Start Abgleich mit dem dichten Pfad
  (Ausgaben und Gradienten in fp32, Toleranz 1·10⁻²) und Zeitmessung; Flex nur, wenn gleich und ≥ 10 % schneller.
  Die Entscheidung steht in `results/v5/h100/attention.json`. Jede Ausnahme und jeder nicht-endliche Verlust im
  Flex-Pfad schaltet für den Rest des Laufs auf den dichten Pfad (vermerkt in `meta["attention"]`). Die Endmessung
  rechnet immer dicht, wie bisher.
- Betriebssicherheit (ändert nichts am Training, wenn nichts schiefgeht):
  - Preis, Budget und Kostengrenze werden beim Start in `settings.env` gemerkt; ein Neustart ohne `export` (z. B. nach
    einem Pod-Neustart auf NVL/PCIe) fällt nicht mehr auf 4,01 $/h und 5,5 h zurück. Unplausible Werte und Preise
    unter dem Secure-Cloud-Listenpreis der erkannten Karte (SXM 4,01, NVL 3,21, PCIe 2,91 $/h inkl. Speicher) →
    FEHLER vor dem Training (sonst griffe die 25-$-Bremse zu spät, z. B. beim NVL-Beispiel auf einer SXM erst bei ~31 $).
  - Ein unerwartetes Ende des Haupttrainings (z. B. ein abgestürzter GPU-Kern) wird ohne Zutun ab dem letzten Stand
    (≤ 30 min alt) mit derselben Frist neu gestartet: höchstens zweimal, nur wenn die GPU binnen 180 s antwortet, nur
    nach einem Versuch, der ≥ 10 min trainiert hat (oder wenn `attention.json` einen abgebrochenen oder
    fehlgeschlagenen Flex-Abgleich vermerkt – das gilt dann für den ganzen Lauf), und ein zweites Mal nur, wenn
    der vorige Versuch einen Stand gesichert hat; die Lernraten-Suche einmal. Divergenz behält ihre eigene Regel.
  - `attention.json` wird atomar geschrieben, enthält die GPU-Bezeichnung im Schlüssel und bekommt vor dem GPU-Abgleich
    einen vorläufigen Eintrag „dicht“: Stürzt der Abgleich den Prozess ab, trainiert der nächste Start dicht, statt den
    Abgleich zu wiederholen. Ein Speichermangel im Abgleich (Fortsetzung auf einer kleineren Karte) wird nicht
    dauerhaft gespeichert.
  - Nach einem Wechsel auf die dichte Attention (oder einen kleineren Teil-Batch, den geteilten Verlust) misst das
    Nachführen der Tokenzahl den Durchsatz neu ab 10 Schritten danach und rechnet nie auf einem Messfenster unter
    300 s (ein Fenster der Länge 0 hätte den Durchsatz 0 gelesen und das Budget dauerhaft gekürzt; Befund der zweiten
    Prüfrunde); bei einer Fortsetzung mit `--extend-to` führt es nie über dieses Ziel.
- Nicht übernommen: Community Cloud (≈ −0,015, aber ohne Ausfallschutz und mit neuer Kostenbremse auf einem Ersatz-Pod;
  Entscheidung des Auftraggebers), halbe Batchgröße, Muon, Verdichten der Leerlaufzeiten (mehr neue Fehlerwege für
  wenig Gewinn).
- Unverändert: Modell, Batch, Lernraten-Suche, Daten-Prüfsummen, Filter, Stufe-1-Schwelle und Messregel.
- Prüfung vor dem Lauf: CPU-Kleintest `h100_train smoke` mit neuen Fällen (Nachführen der Tokenzahl, auch bei einer
  Fortsetzung, Flex-Abgleich mit Dokumentgrenzen über Blockgrenzen, Rückfall nach eingespeistem Flex-Fehler samt neuem
  Messfenster, `attention.json` beschädigt/atomar), Test des Zusammenführens auf kleinen Daten, Ablaufskript im
  Testmodus (Lernraten-Regel, Divergenz, automatische Neustarts, gemerkte Einstellungen); die Preisuntergrenze separat
  mit nachgebildeten GPU-Namen (der Testmodus überspringt die GPU-Prüfungen). Drei unabhängige Prüfrunden (Prüfer, je
  drei Gegenprüfer; in der zweiten zusätzlich ein Vollständigkeits-Kritiker):
  - Runde 1: 8 Befunde, 1 bestätigt (Obergrenze bei `--extend-to`).
  - Runde 2: 12 Befunde, 3 bestätigt (Nachführen auf leerem Messfenster; Speichermangel im Abgleich dauerhaft als
    „dicht“ gespeichert; ein Absturz im Abgleich wurde erst nach einem Neustart von Hand abgefangen).
  - Runde 3 (nur die Änderungen danach): 6 Befunde, 1 bestätigt (die Anleitung nannte für NVL/PCIe keine spätere
    Pflicht-Kontrolle, obwohl der Lauf dort länger als 7 h dauert).
  - Alle behoben; die beiden Fehler im Nachführen per Mutationstest belegt (der jeweilige Kleintest schlägt mit dem
    alten Code fehl). Abgelehnte, aber billig abzusichernde Grenzfälle sind mit abgedeckt (u. a. GPU-Prüfung vor
    Neustarts, Preisuntergrenze, Fortschrittsregel). Der GPU-Pfad selbst lässt sich hier nicht ausführen; dafür sind
    Abgleich und Rückfall da.

**Ergebnis 17. Oktober: Stufe 1 erreicht – Modell „Sela-1 135M“** (Modellkarte: `docs/MODEL_CARD_SELA1.md`).
Der Lauf startete am 16. Oktober um 21:14 UTC auf einer H100 SXM (4,01 $/h), Code `eb2e002`. Die Messregel oben steht
seit dem 12. Oktober fest (Commit `28e59c2`) und blieb bis zum Lauf unverändert. Ergebnisse in `results/v5/h100/`, vom
Pod automatisch hochgeladen (Branch `h100-results-20261017-0317`, Commit `219df1d`); `mix_main.json` und
`verify_20261017.json` kamen danach auf dem CPU-Rechner dazu.

| Größe | Wert |
|---|---|
| **Test, erweiterter Filter, Netz allein, Fenster 1.024 / Schritt 512 (Stufe-1-Regel)** | **0,989 bpb** (1.023 Dokumente; 95-%-KI 0,975–1,005) → **Stufe 1 erreicht**, Abstand 0,051 |
| Test, alte Filterliste (`results/lm/dedup.json`) | 0,988 (1.092 Dokumente) |
| GPT-2 small auf denselben Dokumenten | 1,036 / 1,039; Verhältnis 0,955 (KI 0,947–0,962) / 0,951 (KI 0,943–0,958) |
| val-A (alte Filterliste) | 0,977 |
| Mischung mit dem exakten Zählmodell (λ je Verlaufs-Bucket, nur auf val-A angepasst) | 0,982 (erweiterter Filter; mit einem einzigen λ = 0,028: 0,985); bringt dem Netz nur noch 0,007 |
| Training | 5,757 Mrd. Token in 3,27 h (≈ 489 k Token/s), 10.981 Schritte, Lernrate 1·10⁻³ (Suche: 1e-3 vor 2e-3 und 4e-3) |
| Verlauf | Flex-Attention gewählt (35 % weniger Zeit je Teil-Schritt, Abgleich bestanden); im Training keine Divergenz, kein Neustart, kein Speichermangel. Das Ablaufskript startete dreimal: Die ersten beiden Starts brachen vor jeder Arbeit wegen eines ungültigen GitHub-Schlüssels ab |
| Kosten | ≈ 25 $ Pod-Zeit für alles (Daten, Suche, Training, Messung, Hochladen) |

- **Prognose gegen Messung.** Prognostiziert war ein Median von 1,030, einschließlich des erwarteten Token-Gewinns der
  Änderungen (ohne sie 1,041 bei ≈ 4,6 Mrd. Token, p10 1,008). Trainiert wurden 5,76 Mrd. Token, im erwarteten Bereich:
  Der Durchsatz war mit 489 k statt ≈ 300 k Token/s höher, aber die Vorbereitung dauerte ≈ 2 h 24 min statt 70–75 min
  (C4-Aufbereitung), das Training lief daher nur 3,27 h. Gemessen: 0,989, also ≈ 0,04 unter dem Prognose-Median und
  auch unter dem p10 der ursprünglichen Prognose. Die Prognose war zu vorsichtig.
- **Korrektur zur Beschreibung des Stroms.** Der Strom `train_all` hat 6,802 Mrd. Token: Basis-Training einmal, ihr
  WikiText-Teil insgesamt viermal (der C4-Teil einmal), dazu C4-en-Teile 1–36 aus dem Trainings-Hash-Bereich.
  Trainiert wurden davon 5,757 Mrd. Token, also 0,85 eines Durchgangs. Die Prüfsummen der C4-Teile stehen in
  `experiments/h100_data.py` (`C4_SHARDS`).
- **Unabhängige Prüfung** (vier Agenten, nur lesend; `results/v5/h100/verify_20261017.json`):
  - **Messpfad.** Die Endmessung rechnet dicht und kausal; Flex läuft nur im Training. Jedes Ziel-Token wird genau
    einmal bewertet, nur mit linkem Kontext aus dem eigenen Dokument. Die Byte-Nenner sind die UTF-8-Längen des
    Korpustexts und identisch mit denen der GPT-2-Referenz; 10 Dokumente, mit GPT-2 neu bewertet, reproduzieren die
    Referenz auf 4·10⁻⁴ Bits. Die Prüfsätze tragen die festgelegten SHA-256-Werte, ihre Dokumente liegen nicht im
    Trainings-Hash-Bereich (Textüberlappung erfasst der Filter).
  - **Nachrechnung.** Die sechs Endwerte (Test und val-A, je drei Filter) ergeben sich exakt aus den gespeicherten
    Token-Wahrscheinlichkeiten. Kurve und Lernraten-Suche stammen von Zwischenständen und sind so nicht nachrechenbar.
  - **Kontamination.** Die Basis-Überlappung, mit anderem Hash neu gerechnet, reproduziert die ausgeschlossenen
    Dokumente exakt. Unter den behaltenen Dokumenten (≥ 500 Bytes) hängt das Verhältnis zu GPT-2 nicht vom Rang der
    Basis-Überlappung ab (Spearman ρ = 0,00); nur die kleine Gruppe mit 5–20 % Überlappung (22 Dokumente) liegt klar
    besser (0,903 gegen 0,952). Strengste
    Teilmenge (erweiterter Filter und null Basis-Überlappung, 909 Dokumente): 1,006 bpb gegen GPT-2 1,057
    (Verhältnis 0,952).
  - **Gegenprüfer.** Urteil: „erreicht, mit Einschränkungen“. Teil-Überlappung unter der 20-%-Schwelle ≈ 0,004
    (Basis) bzw. geschätzt ≈ 0,01 (C4; eine Schätzung, keine Schranke). Härtester Belastungstest 1,002, weiterhin
    unter 1,04.
- **Einschränkungen.**
  - Der Vergleich mit GPT-2 ist in-domain gegen zero-shot: Die Test-Dokumente stammen aus denselben Quellen wie das
    Training, und die Mischung war auf die Messsätze abgestimmt. Pro Quelle beträgt das Verhältnis 0,945 bei C4 und
    0,970 bei Wikipedia. Sela-1 ist damit nicht allgemein besser als GPT-2 small.
  - Die vier Prüfer arbeiteten nur mit den gespeicherten Token-Wahrscheinlichkeiten. Die spätere Neuauswertung des
    Netzes auf einer CPU (unten) bestätigt den Wert.
  - Die C4-Überlappung unter 20 % war auf dem Prüfrechner nicht nachrechenbar. Die C4-Teile sind öffentlich und per
    SHA-256 festgelegt, die Rechnung ist also anderswo wiederholbar.
- **Was übrig ist.**
  - Das Modell liegt im privaten Entwurf-Release (541 MB).
  - Den Fortsetzungs-Stand (≈ 1,6 GB, Stand vor der Abnahme bei 4,03 Mrd. Token) hat das Ablaufskript nicht
    hochgeladen. Die Ursache ist nicht protokolliert, denn der Log-Teil nach dem Ergebnis-Commit liegt nur auf dem Pod.
    Plausibel ist die nahe Kostenbremse: Das Modell war um 03:18 UTC oben, die Bremse lag bei ≈ 03:25 UTC, und
    `upload_asset` begrenzt jeden Versuch auf die Restzeit minus 4 min und lädt unter 5 min gar nicht mehr.
  - Der Stand liegt nur auf dem gestoppten Pod. Wer ihn behalten will, lädt ihn vor dem Löschen herunter (Anleitung
    Schritt 5b); mit dem Löschen des Pods ist er weg.
  - Weitertrainieren geht auch ab dem fertigen Modell mit neuer Aufwärm- und Abnahme-Phase.
- **Neuauswertung und Benchmarks (17. Oktober, GitHub Actions, `.github/workflows/sela1_bench.yml`).**
  - CPU, fp32, Basisdaten neu gebaut (SHA-256 geprüft), derselbe Messcode: Test 0,98938 gegen 0,98938 auf der H100,
    Abweichung 1,6·10⁻⁶ bpb (`results/v5/h100/eval_recheck_cpu.json`).
  - Zero-Shot gegen GPT-2 small im selben Messcode (`experiments/sela1_bench.py`, `results/v5/h100/bench_main.json`):

    | Aufgabe | Sela-1 | GPT-2 small | Differenz (95-%-KI) |
    |---|---|---|---|
    | HellaSwag (acc_norm) | 32,7 % | 31,3 % | +1,4 pp (+0,8 … +2,1) |
    | PIQA (acc_norm) | 64,7 % | 62,5 % | +2,2 pp (+0,5 … +3,9) |
    | ARC-Easy (acc_norm) | 39,9 % | 40,5 % | −0,6 pp (−2,2 … +1,1) |
    | LAMBADA (acc) | 27,8 % | 33,7 % | −5,9 pp (−7,1 … −4,7) |

  - Außerhalb der eigenen Daten liegt Sela-1 damit etwa auf GPT-2-small-Niveau: zweimal besser, einmal gleich, bei
    LAMBADA (letzte Wörter aus Romanen, langer Kontext; Sela-1 las keine Bücher) klar schlechter.
- **In der Desktop-App (17. Oktober, auf Wunsch des Auftraggebers).**
  - Sela-1 läuft im Sidecar ohne torch, mit dem NumPy-Port `engramm/lm/sela.py`. Im Chatfeld wählt man zwischen
    ENGRAMM und Sela-1.
  - Der private macOS-Bau `.github/workflows/desktop_sela.yml` exportiert den Checkpoint nach fp16 (270,5 MB) und
    prüft NumPy gegen torch auf den echten Gewichten: größte Logit-Abweichung 0,008, gleiche wahrscheinlichste Token.
  - Die DMGs für Apple Silicon und Intel liegen nur im privaten Entwurf „ENGRAMM 3.2 mit Sela-1 – privater
    Test-Build 1“. Die öffentlichen Installer enthalten keine Gewichte.
  - Vor dem Bau haben drei Prüfer mit Gegenprüfung den Code durchgesehen; 6 Befunde wurden behoben, darunter eine
    float64-Rechnung, die Sela-1 ≈ 6,5-mal langsamer gemacht hätte.
- **Name.** Das Netz heißt **ENGRAMM Sela-1 135M** (Familie Sela, erste Generation, 135 Mio. Parameter). Das
  CPU-Netz aus §10 kann als „Sela-0 100M“ geführt werden.
- **Folge für §10.** Die CPU-Verlängerung `long_ext1` wird für Stufe 1 nicht mehr gebraucht. Sie läuft als reiner
  CPU-Vergleich weiter (kostet nichts, blockiert nichts) und wird mit ihrem Endwert berichtet.

## 12. Sela-2: ein Chat-Modell von Grund auf für höchstens 30 $ (festgelegt vor dem Lauf, 17. Oktober)

**Auftrag (17. Oktober).** Sela-2 entwickeln: mehr Parameter, besseres Training, so dass man ohne Probleme mit ihm
chatten kann. Richtung GPT-3, aber für höchstens 30 $ GPU-Miete. Eigenes Modell ab Zufallsinitialisierung; öffentliche
Datensätze, auch synthetische von offenen Modellen, sind erlaubt, soweit die Lizenz es zulässt.

**Ehrliche Einordnung.**
- 30 $ kaufen ≈ 6 H100-Stunden, also ≈ 7·10¹⁸ FLOP. GPT-3 175B brauchte ≈ 3·10²³ FLOP, rund 40 000-mal mehr.
- GPT-3-Wissen passt deshalb nicht in die Gewichte. Was geht:
  - die Größe von GPT-3 Medium (24 Schichten × 1 024);
  - Benchmarks im Bereich GPT-2 small bis medium;
  - flüssiger, kurzer Chat;
  - Fakten aus ENGRAMMs Quellen statt aus dem Gedächtnis des Netzes.
- Das Modell liest diese Quellen, zitiert sie mit [n], und jede Antwort wird vor dem Anzeigen geprüft. Retrieval statt
  Parameter ist der einzige belegte Weg zu GPT-3-artigem Faktenwissen bei diesem Budget (RETRO, FiD, Atlas; Recherche
  in `results/sela2/`).

**Weg dorthin.**
- Recherche: 5 Linsen (Trainingseffizienz, Chat, Daten, Retrieval, Rechenleistung pro Dollar).
- Ein Entwurf, dann drei Gegenprüfer (Kosten, Qualität, Risiko). Alle drei urteilten „tragfähig mit Korrekturen“;
  die Korrekturen sind unten eingearbeitet.

### 12.1 Rezept

| Baustein | Festlegung | Quelle / Beleg |
|---|---|---|
| Modell | 24 Schichten × 1 024, 8 Köpfe à 128, Kontext 2 048, ReLU², QK-Norm, RoPE; x0-Skip, Smear, 2 Value-Embedding-Tabellen, Backout, Softcap 15; 352 Mio. Parameter je Token (503 Mio. gespeichert) | nanochat `gpt.py` (Karpathy), bei dieser Größe auf einem Rechner validiert |
| Optimierer | Muon (Polar Express, MuonEq, NorMuon, vorsichtiger Weight Decay) für Matrizen; AdamW für Einbettungen, Kopf, Skalare; Lernraten, Momentum- und WD-Pläne wie nanochat | `experiments/sela2_optim.py`; Golden-Test gleich nanochat (`tests/test_sela2.py`) |
| Zeitplan | 40 Aufwärmschritte, konstant, lineares Abklingen über die letzten 65 % auf 5 %; das Abklingen endet sicher vor der Frist (Zeit- statt nur Token-Fortschritt) | nanochat `base_train.py` |
| Tokenizer | eigener zweisprachiger Byte-BPE, 49 152 Tokens, mit ChatML-Tokens; gemessen 4,67 Bytes/Token Englisch (Sela-1: 4,51), 4,39 Deutsch (Sela-1: 2,68) | `data/lm2_tokenizer.json`, Bericht im Daten-Entwurf |
| Vortraining | FineWeb-Edu 42 %, DCLM 24 %, C4 8 %, Cosmopedia 7 %, Wikipedia 6 %, PG-19 4 %, Deutsch 9 % (FineWeb2-HQ, Wikipedia); ab 70 % der Token: 29 % Chat-, Quellen-QA- und Identitätsgespräche | DataDecide, SmolLM2-Mix; C4 gegen den PIQA-Verlust (Qualitätsprüfer) |
| Chat | Feinabstimmung mit Verlust nur auf den Antworten (smoltalk2, OASST2, Dolly, SQuAD v2, HotpotQA, germanrag, eigene Identitätsgespräche); kurze Antworten bevorzugt; Antworten aus Quellen zuerst als Spanne mit [n] | nanochat `chat_sft.py`; Qualitätsprüfer |
| Dekontamination | jedes 13-Wort-Fenster aus 16 Testsätzen (HellaSwag, PIQA, ARC, LAMBADA, WinoGrande, OBQA, MMLU, SQuAD v2, HotpotQA, XQuAD-de, IFEval und die Prüfdokumente der LM-Studie); ≥ 3 Treffer → Dokument raus | `experiments/sela2_data.py` |
| Datenbau | vollständig auf kostenlosen GitHub-Runnern, nur im privaten Entwurf-Release abgelegt | `.github/workflows/sela2_data.yml` |
| GPU | 1 × H100 SXM, RunPod Secure (≈ 4,01 $/h inkl. Speicher); Community oder andere Preise werden aus der RunPod-API gelesen | Rechenleistungs-Linse |

### 12.2 Geld

| Posten | Zeit | Kosten |
|---|---|---|
| Einrichten, Daten laden (≈ 15 GB), Vorab-Probe | ≈ 0,25 h | ≈ 1,0 $ |
| Vortraining (bis zur Frist) | ≈ 5,2 h | ≈ 20,9 $ |
| Chat-Feinabstimmung, Auswertung, Uploads | ≈ 0,75 h | ≈ 3,0 $ |
| **Kostenbremse** | | **25 $**, danach höchstens 10 min zum Sichern (≈ 0,7 $) |
| Harte Grenze | | Guthaben 30 $, Auto-Aufladen aus: bei 0 $ stoppt RunPod alles |

Erwartet werden ≈ 2,7–2,9 Mrd. Token Vortraining bei ≈ 150 000 Token/s. Das ist eine Schätzung aus nanochat d18/d20
und Sela-1 (Kostenprüfer); die Frist passt die Tokenzahl an das gemessene Tempo an.

### 12.3 Was vor dem Mieten geprüft ist

- Torch gegen NumPy auf allen Bausteinen: Logits gleich bis 10⁻³; Cache-Dekodierung gleich dem vollen Durchlauf;
  int8-Datei nahe fp32.
- Muon und AdamW Schritt für Schritt gleich der nanochat-Referenz.
- Trainer auf der CPU:
  - simulierter Abbruch mitten im Lauf, dann Neustart: **bitgleiche** Gewichte;
  - Frist mit eingebauter Verlangsamung: die Lernrate steigt nie und erreicht ihr Ende vor der Frist;
  - Datenwechsel bei 70 %; SFT; Export.
- Pod-Skript `experiments/sela2_run.sh` im Testmodus vollständig durchgelaufen (offline und auf GitHub Actions mit den
  echten Daten und torch 2.8).
- Kostenprüfer-Befunde umgesetzt:
  - Nachlauf nach der Grenze 10 statt 30 min;
  - kein CPU-Sampling auf dem Pod;
  - Basismodell und Fortsetzungs-Stand werden im Hintergrund hochgeladen, sobald es sie gibt;
  - Dateien über 1,9 GB werden geteilt (GitHub erlaubt < 2 GiB je Datei).
- Risikoprüfer-Befunde umgesetzt:
  - Neuanpassung der Tokenzahl nur vor dem Abklingen;
  - automatische Wechsel bleiben über Neustarts erhalten (Lernraten-Faktor, Neustart nach Verlustprüfung);
  - Tests laufen auf der Pod-Version torch 2.8.

### 12.4 Erfolgskriterien

Die Erfolgskriterien sind vorab festgelegt in `docs/PREREG_SELA2.md`. Kurz:
- **Basismodell:** gepoolter Zero-Shot-Wert über HellaSwag, PIQA, ARC-E/C, WinoGrande und OBQA. Verglichen wird mit
  GPT-2 small/medium und Pythia im selben Messcode.
- **Chat:**
  - Abbruch-, Schleifen- und Rollen-Fehlerraten auf 100 festen Prompts;
  - IFEval des Chat-Modells minus Basis;
  - Blindvergleich durch den Auftraggeber.
- **Quellen-Antworten:**
  - HasAns-F1 und NoAns-Treffer getrennt;
  - Abdeckung und Richtigkeit gegen ENGRAMM auf denselben Fragen;
  - 0 angezeigte Zahlen oder Namen ohne Quelle.

Erwartung (Qualitätsprüfer, nach unten korrigiert):

| Aufgabe | Erwartung | Bezugswerte |
|---|---|---|
| HellaSwag | ≈ 35 | GPT-2 small 31,3; Sela-1 32,7; GPT-3 Small 33,7 |
| PIQA | ≈ 63,5 | Sela-1 64,7 |
| ARC-E | ≈ 48 | GPT-2 small 40,5 |
| LAMBADA | ≈ 30 | GPT-2 small 33,7 |

Deutsch ist ein Versuch ohne Zielwert.

### 12.5 Lizenzen

- Gewichte vorsichtshalber unter CC BY-SA 4.0, wegen Wikipedia, SQuAD, HotpotQA und Dolly.
- smoltalk2 enthält Smol-Magpie-Ultra-Gespräche von Llama-3.1-405B. Die Llama-3.1-Lizenz verlangt bei Weitergabe
  „Llama“ im Modellnamen. Solange Sela-2 nur privat in der App läuft, ist das offen.
- Vor einer Veröffentlichung entscheidet der Auftraggeber:
  - umbenennen;
  - oder mit dem strengen Datenpool ohne die Llama-Gespräche neu feinabstimmen (`python -m experiments.sela2_data chat --strict`; ≈ 1 $ GPU).
