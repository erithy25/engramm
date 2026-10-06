# Plan ENGRAMM 4: KI-Niveau auf einem Rechner mit 5 GB, in einem Tag einsatzbereit

## Klartext vorweg (eine Rechnung, keine Ausrede)

Ein Modell von Grund auf in einem Tag auf einem Rechner auf das Niveau heutiger KI zu trainieren, ist rechnerisch
ausgeschlossen:

| | Rechenaufwand fürs Training |
|---|---|
| GPT-4-Klasse | etwa 2·10²⁵ Rechenschritte |
| ein gutes 8-Milliarden-Modell | etwa 10²⁴ |
| ein Apple-M-Chip oder eine Spiele-GPU, 24 Stunden | etwa 3·10¹⁸ |

Der Abstand beträgt sechs bis sieben Zehnerpotenzen. Mit einem Tag Rechenzeit entsteht von Grund auf ein Modell auf
GPT-2-Niveau. Das ist nicht „wie echte KI“, egal mit welchem Verfahren.

**Der geniale Zug ist deshalb ein anderer:** nicht das Training wiederholen, das andere schon bezahlt haben, sondern
darauf aufbauen. Die Rechenzentrums-Arbeit steckt bereits in **offen lizenzierten kleinen Sprachmodellen**: 1,5–4
Milliarden Parameter, 4-Bit, 1–2,5 GB. Sie laufen auf jedem Laptop. ENGRAMM liefert dazu genau das, was diesen Modellen
fehlt:

- Wissen mit Quelle statt Raten,
- sofortiges Lernen ohne Training,
- beweisbares Vergessen,
- exakte Rechnungen und Werkzeuge,
- Offline-Betrieb und Datenschutz.

Das Ergebnis ist in mehreren Dimensionen **besser als ein reines neuronales Netz**: Es lernt neue Fakten in
Millisekunden statt in Trainingsläufen, belegt jede Tatsache, vergisst bitgenau und erfindet keine Fakten.

## Architektur in einem Satz

**Ein kleines Sprachmodell formuliert und denkt; ENGRAMM liefert Wissen, Gedächtnis, Rechnen und Grenzen; ein Router
entscheidet je Zug, wer was beiträgt.**

```
Nachricht
  ├─ Router (bestehende Erkennung: Sicherheit, Rechnen, Daten, Gedächtnisbefehle, Schreiben)
  ├─ Werkzeuge exakt (infer.py, Rechner, Datum, Einheiten)           → Ergebnis als Fakt ins Modell
  ├─ Wissen (2 Mio. Sätze, Faktenbank, Regal, Wikibooks)              → 3–8 Belege mit Quelle
  ├─ Gedächtnis (Fakten, Episoden, Lernstand)                         → was der Nutzer gesagt hat
  ├─ Sprachkern: kleines Modell, 4-Bit, llama.cpp                     → formuliert, verknüpft, folgert
  │     Regel: Tatsachen nur aus den Belegen, sonst „weiß ich nicht“
  └─ Prüfung (Belegabgleich je Satz, Sicherheitsstufe, Sprache, Wiederholung) → Antwort mit Quellen
```

## Bausteine

| Baustein | Was | Wiederverwendet |
|---|---|---|
| Sprachkern | Open-Weights-Modell, 1,5–4 Mrd. Parameter, Q4, über llama.cpp (C++, Metal/CUDA/CPU) als Sidecar der Tauri-App. Kandidaten nur mit freier Lizenz (z. B. Apache-2.0 oder MIT); Auswahl per Messung (P0) | Sidecar-Mechanik der App (`runtime/`) |
| Belegsuche (RAG) | je Frage die besten Sätze, Faktenbank-Werte und Gesprächskontext als nummerierte Belege im Prompt | `engramm/chat/bot.py` Retrieval, `kb/kgqa.py`, `about.py`, Regal, `know/` |
| Nicht raten | „Antworte nur aus den Belegen [1]–[n], sonst sag, dass du es nicht weißt“; danach Satz-für-Satz-Abgleich, jeder Tatsachensatz muss einen Beleg treffen, sonst wird er gestrichen | Konfidenz- und Belegprüfung aus Stufe 4 |
| Exakt statt geschätzt | Rechnen, Daten, Zeiten, Einheiten, Alter macht der bestehende Code; das Modell bekommt das Ergebnis | `understand/infer.py`, Werkzeuge |
| Sofort lernen | Neues Wissen wird ohne Training gespeichert und beim nächsten Mal als Beleg gefunden, schneller als jedes Nachtraining | `facts.py`, `textmem.py`, `learn/state.py` |
| Bitgenau vergessen | „vergiss das“ entfernt den Beleg; das Modell selbst hat ihn nie gelernt | Lern-Log mit SHA-256 |
| Schlaf-Konsolidierung (optional) | nachts LoRA-Feinabstimmung auf ausdrücklich freigegebene Gespräche, rücknehmbar (Adapter löschen) | Lernpakete (`python -m engramm.learn`) |
| Persönlichkeit und Abwechslung | Systemprompt mit Ton, Sprache des Nutzers, Stil aus dem Lernstand; Sampling statt fester Vorlagen | Stil-Lernen, Bandit |
| Grenzen | Krisen, Notfall, Gesundheit, Recht und Geld bleiben regelbasiert vorn; Antworten nur mit Quelle oder Warnhinweis | Sicherheitsstufe, Moment-Rahmen |

## „Training in einem Tag“: was trainiert wird

1. **Kein Vortraining.** Das steckt im offenen Modell.
2. **LoRA-Feinabstimmung, 4–8 Stunden** auf einem Rechner (Apple-Silicon-Mac oder eine Consumer-GPU). Trainiert wird:
   - Belege zitieren und bei fehlendem Beleg „weiß ich nicht“ sagen;
   - ENGRAMM-Ton, Deutsch, Rückfragen;
   - Werkzeug-Ergebnisse übernehmen statt selbst zu rechnen.
3. **Daten:**
   - die 125 Batterien, Proben und Entwicklungssätze des Projekts, nie die versiegelten Sätze;
   - offen lizenzierte Dialogdaten, nur mit geprüfter Lizenz (`docs/DATA_LICENSES.md`).
4. **Ergebnis:** ein Adapter von etwa 50–200 MB, der neben dem Grundmodell liegt.

## Speicher- und Rechenbudget

| Teil | Größe |
|---|---|
| Sprachkern Q4 (2–4 Mrd. Parameter) | 1,2–2,5 GB |
| LoRA-Adapter | 0,1–0,2 GB |
| Lite-Wissenspaket (heute) | 1,2 GB |
| App, Lexika, Indizes | 0,3 GB |
| **Summe Download** | **2,8–4,2 GB** (Grenze 5 GB) |

Was sich gegenüber heute ändert:
- **Arbeitsspeicher:** 3–4 GB statt heute 0,75 GB. Rechner mit 8 GB RAM reichen; die alte Grenze von 1,5 GB fällt.
- **Tempo** (Erfahrungswerte, in P0 zu messen):
  - Apple M1 und neuer: 20–40 Wörter pro Sekunde;
  - x86 nur mit CPU: 8–15 Wörter pro Sekunde;
  - erste Wörter nach 0,5–2 s.

## Phasen, je mit vorab festgelegter Schwelle (gemessen wie bisher: frische versiegelte Gespräche, blinder Leser)

| Phase | Inhalt | Schwelle |
|---|---|---|
| P0 Modellauswahl (2 Tage) | 3 lizenzfreie Kandidaten Q4 im Vergleich: Deutsch, Belegtreue, Tempo, RAM | Kandidat mit bester Belegtreue bei ≤ 2,5 GB und ≥ 10 Wörtern/s |
| P1 Sidecar + Router (1 Woche) | llama.cpp in der App, Streaming; der Router lässt Werkzeuge, Sicherheit und Gedächtnisbefehle vorn | Suite grün, p95 erstes Wort ≤ 2 s |
| P2 Belege + Nicht-Raten (1 Woche) | RAG aus allen Wissensquellen, Satz-Belegabgleich, Quellen-Chips wie heute | NQ-Dev: keine Verschlechterung; 0 unbelegte Tatsachen in 100 Stichproben |
| P3 Gedächtnis + Lernen (1 Woche) | Fakten, Episoden, Stil als Kontext; „vergiss das“ bitgenau | Korrektur-Test ≤ 5 %, Vergessen 100 % |
| P4 Feinabstimmung (1 Tag Rechenzeit) | LoRA auf eigene, freie Daten | Belegtreue steigt messbar, Deutsch ≥ Englisch −5 Punkte |
| P5 Endmessung | frische versiegelte Sätze | schwach ≤ 25 %, Rat ≥ 60 %, Schlüsse ≥ 80 %, 0 erfundene Fakten |
| P6 Release | Paket ≤ 5 GB, Installer, Website und README neu | — |

## Was das Ergebnis besser macht als „echte KI“

| | ChatGPT & Co. | ENGRAMM 4 |
|---|---|---|
| Neues lernen | Wochen Training oder gar nicht | sofort, in Millisekunden |
| Vergessen | praktisch unmöglich | bitgenau, nachweisbar |
| Quellen | oft keine, manchmal erfunden | jede Tatsache belegt |
| Rechnen und Daten | geschätzt | exakt |
| Daten | Cloud | bleiben auf dem Rechner |
| Kosten pro Antwort | Rechenzentrum | 0 |

## Risiken und blinde Flecken

| Risiko | Gegenmaßnahme |
|---|---|
| **Positionierung:** „no neural network“ ist heute Markenkern; dieser Schritt hebt ihn auf | bewusst neu positionieren: „KI, die belegt, lernt und vergisst – offline“; Website und README ehrlich umstellen |
| Lizenzen der Modelle | nur Apache-2.0/MIT o. ä., Prüfung vor Aufnahme wie bei allen Daten |
| RAM 3–4 GB statt 0,75 GB | Lite-Modus ohne Sprachkern bleibt (heutiges ENGRAMM) |
| Kleine Modelle halluzinieren | Belegpflicht und Satzabgleich; Tatsachen nie ohne Beleg |
| Determinismus geht verloren | fester Seed pro Gespräch optional; Tatsachen stammen ohnehin aus Belegen |
| Tempo auf alten Rechnern | Modellgröße nach Hardware wählen (1,5 B auf alten, 3–4 B auf neuen Rechnern) |

## Sofort, unabhängig vom großen Plan (aus den Screenshots)

1. „What was his major?“ → Antwort aus dem Artikelsatz („bachelor's degree in economics“) über die vorhandene
   Antwortextraktion, mit Quelle.
2. „Please compare those two“ → die beiden zuletzt genannten Personen aus dem Kontext und eine Vergleichstabelle aus der
   Faktenbank (Geburt, Partei, Ämter, Ausbildung) mit Quelle.
