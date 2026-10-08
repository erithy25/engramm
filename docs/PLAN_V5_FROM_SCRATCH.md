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
