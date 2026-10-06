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
