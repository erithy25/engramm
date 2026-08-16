# EXPECTATIONS — was herauskommen müsste, festgelegt vor der Messung

Register der Vorhersagen. Jede Erwartung wird **vor** dem zugehörigen Lauf
eingetragen und committet; der Commit-Zeitstempel ist der Beleg. Nach der
Messung wird das Ergebnis darunter vermerkt, die Erwartung selbst bleibt
unverändert stehen — auch und gerade wenn sie danebenlag.

Das ist dieselbe Regel wie in `docs/PREREG_ROBUSTNESS.md` §10, nur für
kleinere Läufe, die keine eigene Preregistrierung rechtfertigen.

---

## E1 — WiLI-2018, 10-shot, 5 Seeds (M1-Replikation)

**Registriert 2026-08-15, vor dem Lauf.** Harness
`python -m experiments.run_benchmark --task wili --seeds 5 --shots 10 --D 10000`.

### Referenzpunkt: 82,64 %, nicht 79,30 %

Der historische M1-Wert ist 79,30 % ± 0,68 % — gemessen mit **voller
Pipeline inklusive Episodenschicht**. Dieser Neubau hat keine
Episodenschicht (`docs/DEVIATIONS.md` CHANGED-5).

Auf WiLI *senkt* die Episodenschicht die Genauigkeit laut Aktenlage:
„79,30 % mit vs. 82,64 % ohne (Prototypen-only)". Der architektonisch
vergleichbare Wert ist deshalb **82,64 %**. Ein Vergleich gegen 79,30 %
würde diesem Neubau einen Vorsprung anrechnen, der aus einer weggelassenen
Komponente stammt.

*Einschränkung:* Ob die 82,64 % über 5 Seeds oder über einen einzelnen
gemessen wurden, geht aus den überlieferten Fragmenten nicht hervor. Bei der
MNIST-Ablation ist ausdrücklich „Einzelseed (42)" vermerkt, bei WiLI nicht.
Die Zahl ist also möglicherweise eine Einzelmessung — das erweitert die
zulässige Bandbreite, verschiebt aber nicht den Mittelpunkt.

### Bekannte Abweichungen und ihre erwartete Richtung

| # | Abweichung | erwartete Wirkung |
|---|---|---|
| 1 | **Tie-Regel**: gehashte Objektidentität statt gemeinsamem `V_tie` | **nach oben.** Bei 10 Shots summiert der Prototypen-Akkumulator zehn ±1-Werte; für unabhängige Vektoren wäre P(Tie) = 24,6 %, bei korrelierten Texten derselben Sprache weniger. Ein gemeinsamer Tie-Vektor bläht die Klassenähnlichkeit um bis zu +0,121 auf, was die Trennschärfe senkt. Diese Regel entfernt das. |
| 2 | **Kein T2** (`t2_epochs=0`) | **vernachlässigbar, Richtung offen.** Ob die historische Zahl T2 enthielt, ist nicht überliefert. Die einzige überlieferte T2-Ablation (Banking77) ergab −0,23 pp. |
| 3 | **Andere Shot-Auswahl** (anderer RNG-Pfad) | **Streuung, kein Versatz.** Zeigt sich in der Seed-Standardabweichung; historisch ±0,68 %. |
| 4 | Byte-Trigramme, Rotationszuordnung, D = 10.000 | **keine.** Als identisch angenommen (`DEVIATIONS.md` INFERRED-1/2). |

Punkt 1 ist die einzige Abweichung mit gerichteter Erwartung. Fällt das
Ergebnis **über** 82,64 %, ist das mit ihr vereinbar — und keine
Verbesserung, die diesem Neubau als Verdienst anzurechnen wäre.

### Kriterien (fixiert vor der Messung)

**Primär — Determinismus.** Zwei unabhängige Läufe derselben Seeds müssen
**jede** Genauigkeit auf vier Nachkommastellen reproduzieren. Das ist die
Frage, für die dieser Lauf gefahren wird; auf MNIST ist sie beantwortet, auf
WiLI offen. Jede Abweichung ist ein Befund mit Vorrang vor allem anderen.

**Sekundär — Genauigkeit**, gemessen als Mittelwert über 5 Seeds gegen den
Referenzpunkt 82,64 %:

| Band | Bedingung | Konsequenz |
|---|---|---|
| **Replikation bestätigt** | \|Mittel − 82,64\| ≤ 3 pp, also 79,6–85,6 %, **und** Seed-SD ≤ 1,5 pp | M1 gilt als repliziert |
| **Befund, quantifiziert** | 3 pp < \|Mittel − 82,64\| ≤ 10 pp | wird als Abweichung dokumentiert, Ursache untersucht, **keine Codeänderung ohne Freigabe** |
| **Struktureller Fehlschlag** | \|Mittel − 82,64\| > 10 pp, oder Mittel < 60 % | Fehler im Neubau selbst, nicht in einer Nuance. 60 % war die ursprünglich vorregistrierte M1-Schwelle; Zufallsniveau ist 0,4255 % |

**Warum 3 pp:** rund das Vierfache der historischen Seed-Streuung
(0,68 pp) — weit genug, um die dokumentierten Unbekannten aus der Tabelle
oben aufzunehmen (T2-Status, andere Shot-Ziehung, geänderte Tie-Regel), und
eng genug, um falsifizierbar zu bleiben. Eine Bandbreite, die jedes Ergebnis
einschließt, wäre keine Erwartung.

### Ausdrücklich nicht Gegenstand dieses Laufs

**Der offene MNIST-Abstand.** 80,07 % gegen 86,49 % sind 6,42 Punkte ohne
Erklärung. WiLI ist ein anderer Datensatz, ein anderer Encoder und ein
anderes Tie-Regime. Nichts an diesem Lauf erklärt jenen Abstand, und kein
Ergebnis von hier darf zu seiner Erklärung herangezogen werden. Die beiden
Fäden bleiben getrennt.

### Ergebnis — gemessen 2026-08-16, Container, `canonical=false`

Harness wie registriert, Code-Stand `d24effb`, Records in `results/`.

| Seed | Accuracy | Macro-F1 | Wandzeit |
|---|---|---|---|
| 42 | 0,8489 | 0,8518 | 1141,4 s |
| 7 | 0,8476 | 0,8514 | 1099,3 s |
| 1337 | 0,8485 | 0,8503 | 1151,7 s |
| 2026 | 0,8525 | 0,8554 | 1126,8 s |
| 99 | 0,8422 | 0,8453 | 1114,1 s |
| **Mittel ± SD** | **0,8479 ± 0,0037** | **0,8508 ± 0,0036** | 1126,6 ± 20,9 s |

**Primärkriterium Determinismus: erfüllt.** Zwei unabhängige Läufe der Seeds
42 und 7 (Testsplit auf 3.000 begrenzt, Scratch-Verzeichnis) ergaben
0,8617 / 0,8590 in beiden Durchläufen — Accuracy und Macro-F1 auf vier
Nachkommastellen identisch. Die WiLI-Pipeline ist damit ebenso
reproduzierbar wie die MNIST-Pipeline.

**Sekundärkriterium Genauigkeit: Replikation bestätigt.**
Abweichung vom Referenzpunkt 82,64 %: **+2,15 pp**, innerhalb des
3-pp-Bandes. Seed-SD **0,37 pp**, innerhalb der 1,5-pp-Grenze. Beide
Bedingungen des Bandes „Replikation bestätigt" sind erfüllt.

**Zur gerichteten Vorhersage.** Das Ergebnis liegt über dem Referenzpunkt,
was mit der registrierten Erwartung vereinbar ist, dass die gehashte
Tie-Regel gegenüber einem gemeinsamen `V_tie` nach oben wirkt. *Vereinbar
heißt nicht belegt:* die +2,15 pp sind nicht auf die Tie-Regel
zurückgeführt, und mindestens eine weitere Unbekannte aus der Tabelle oben
(T2-Status der historischen Zahl) könnte beitragen. Wer den Anteil der
Tie-Regel wissen will, muss ihn messen — ein Lauf mit gemeinsamem Tie-Vektor
gegen denselben Seedsatz wäre die direkte Ablation. Nicht durchgeführt.

**Einordnung gegen die historische Volldaten-Pipeline:** 84,79 % gegen
79,30 % sind +5,49 pp. Das ist *nicht* der registrierte Vergleich (§
Referenzpunkt) und wird hier nur genannt, damit die Zahl nicht anderswo als
Erfolg gegen 79,30 % auftaucht — die beiden Systeme unterscheiden sich um
eine ganze Architekturschicht.

**Nebenbefund (nicht Teil des Kriteriums): Spitzenspeicher 12,25 GB ± 3 MB.**
Ursache identifiziert, siehe `docs/DEVIATIONS.md` — ein einzelner
WiLI-Testabsatz von 579.350 Byte umgeht die Chunk-Begrenzung des
Trigramm-Encoders. Ergebnisrelevanz: keine. Relevanz für den M4-Lauf: hoch.

---

## E2 — MNIST-Thermometer-Sweep

**Registriert 2026-08-16, vor dem ersten Lauf. Noch nicht gemessen.**

### Die Frage

Der aktuelle Neubau erreicht auf MNIST **80,07 % ± 0,42 %**. Die
Prototypen-only-Ablation der Aktenlage steht bei **86,49 %** — ein Abstand
von **6,42 pp** ohne Erklärung. `docs/DEVIATIONS.md` GAP-1 benennt die
Thermometer-Konstruktion vorab als wahrscheinlichste Einzelursache: In
keinem überlieferten Dokument stand, wie die Stufenvektoren gebaut werden;
überliefert ist nur der Name „Q=16-Stufen-Thermometer-Encoding".

Der Sweep prüft, **ob und wieviel** diese eine Wahl erklärt. Er prüft nicht,
welche Konstruktion die beste ist — das wäre Hyperparametersuche auf dem
Testsplit.

### Gitter

**Achse 1 — Konstruktion der Stufenvektoren (4 Varianten).**

| Kennung | Konstruktion |
|---|---|
| `progressive` | aktuell implementiert: Stufe 0 zufällig, je Schritt `D/(2(Q−1))` weitere Bits einer festen Permutation gekippt; Stufen 0 und Q−1 annähernd orthogonal |
| `linear_thermometer` | wörtliches Thermometer: Stufe q setzt die ersten `q·D/Q` Komponenten einer festen Permutation auf 1, den Rest auf 0 |
| `random_levels` | jede Stufe ein unabhängiger Zufallsvektor — **Kontrolle**, zerstört die Ordnung absichtlich |
| `single_flip_block` | wie `progressive`, aber je Schritt `D/(2Q)` statt `D/(2(Q−1))` Bits — halbe Schrittweite, Stufen 0 und Q−1 bei ~D/4 statt ~D/2 |

**Achse 2 — Stufenzahl Q: 4, 8, 16, 32.** Q = 16 ist der überlieferte Wert
und in jeder Variante enthalten.

**Achse 3 — Seeds: 42, 7, 1337** (die ersten drei der registrierten Menge).

**Umfang:** 4 × 4 × 3 = **48 Läufe**. Bei ~7,5 min je MNIST-Seed und
D = 10.000 sind das rund 6 Stunden. Falls das zu teuer ist, wird **vor dem
Start** auf D = 4.000 reduziert — für alle 48 Läufe gleichermaßen, nie für
einzelne Zellen, und der Referenzlauf `progressive/Q=16` wird zusätzlich bei
D = 10.000 gefahren, um den Effekt der Reduktion selbst zu beziffern.

**Alles andere bleibt fixiert:** offizieller 60k/10k-Split, Intensitäts-
Mapping `v·Q // 256` (GAP-2), Tie-Regel, keine Episodenschicht, `t2_epochs=0`.

### Was als Erklärung des Abstands gilt

Ausgewertet wird der Mittelwert über die drei Seeds je Zelle, gegen die
6,42 pp Abstand des Referenzpunkts.

| Befund | Bedingung | Lesart |
|---|---|---|
| **Erklärt** | eine Zelle erreicht ≥ 85,5 % (also ≤ 1 pp unter 86,49 %) | Die Konstruktion war die Ursache. Der Wert wird als solcher berichtet, **nicht** als neue offizielle Zahl — die stammt aus der registrierten Konfiguration, siehe unten. |
| **Teilweise erklärt** | beste Zelle liegt 2–6 pp über 80,07 %, aber unter 85,5 % | Die Konstruktion trägt bei, reicht aber nicht. Restabstand wird beziffert und bleibt offen. |
| **Nicht erklärt** | keine Zelle liegt mehr als 2 pp über 80,07 % | Die Thermometer-Konstruktion ist **nicht** die Ursache. GAP-1 wird als widerlegte Hypothese markiert, die Suche geht anderswo weiter. |

**Negativkontrolle:** `random_levels` muss **schlechter** abschneiden als
`progressive` bei gleichem Q. Tut es das nicht, misst der Sweep nicht, was er
zu messen vorgibt — dann ist die Ordnungserhaltung für MNIST irrelevant und
das Ergebnis der ganzen Achse ist wertlos. Dieser Fall wird berichtet, nicht
weginterpretiert.

### Regeln, die vorab gelten

1. **Der Sweep ändert die offizielle Zahl nicht.** Die registrierte
   Konfiguration bleibt `progressive`, Q = 16 — das ist der überlieferte
   Wert. Findet der Sweep eine bessere Zelle, ist das ein *Befund über die
   Ursache des Abstands*, keine neue Bestkonfiguration. Ein Wechsel der
   Konfiguration wäre eine eigene Entscheidung mit eigener Registrierung.
2. **Kein Nachschieben von Zellen.** Das Gitter steht. Wenn eine Idee
   nachträglich reizvoll erscheint, gehört sie in E3, nicht in E2.
3. **Alle 48 Zellen werden berichtet**, auch die uninteressanten. Eine
   Tabelle mit Lücken lädt zur Rosinenpickerei ein.
4. **Der Testsplit wird nur zur Auswertung benutzt**, nie zur Auswahl. Das
   ist bereits der Fall — es steht hier, weil ein Sweep genau die Situation
   ist, in der es kippt.

### Ergebnis

*(wird nach dem Sweep eingetragen; das Gitter oben bleibt unverändert)*

---

## Offene Fragen, nicht terminiert

**O1 — Warum fällt die WiLI-Replikation besser aus als das Original?**
84,79 % gegen 82,64 % sind +2,15 pp. Formal innerhalb des E1-Bandes, also
bestanden — aber eine Replikation, die *besser* ausfällt, ist genauso
erklärungsbedürftig wie eine, die schlechter ausfällt. Meist steckt ein
Unterschied im Versuchsaufbau dahinter und nicht ein besseres Verfahren.

Kandidaten, keiner davon untersucht: die geänderte Tie-Regel (registrierte
Erwartung war „nach oben", siehe E1); der unbekannte T2-Status der
historischen Zahl; eine andere Shot-Ziehung; und die Möglichkeit, dass die
82,64 % eine Einzelmessung ohne Seed-Mittelung waren.

**Nicht als Erfolg verbuchen.** Die direkte Ablation wäre ein Lauf mit
gemeinsamem Tie-Vektor gegen denselben Seedsatz — er würde den Anteil der
Tie-Regel isolieren. Nicht terminiert.
