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
| `single_flip_block` | wie `progressive`, aber je Schritt `D/(2Q)` statt `D/(2(Q−1))` Bits — ~~halbe Schrittweite, Stufen 0 und Q−1 bei ~D/4 statt ~D/2~~ *(Beschreibung falsch, siehe Erratum)* |

> **Erratum 2026-08-16, vor dem Sweep — Rechenfehler in der Beschreibung
> oben, nicht in der Formel.**
>
> Beim Implementieren gemessen: `single_flip_block` ist **keine** halbe
> Schrittweite und landet **nicht** bei D/4.
>
> | | Schrittweite | Abstand L0–L15 |
> |---|---|---|
> | `progressive` = `D/(2(Q−1))` | 133 (D = 4.000) | 1.995 = 0,499·D |
> | `single_flip_block` = `D/(2Q)` | 125 | 1.875 = **0,469·D** |
>
> Das Verhältnis der Schrittweiten ist `(Q−1)/Q` = **0,94**, nicht 0,5. Die
> Extremwerte liegen bei 0,469·D statt bei 0,25·D. Meine Prosa hat aus
> „Nenner um eins kleiner" fälschlich „Schrittweite halbiert" gemacht.
>
> **Die Formel bleibt wie registriert.** Geändert wird nur die falsche
> Beschreibung ihrer Wirkung — die Registrierung fixiert `D/(2Q)`, und was
> ich mir davon versprochen habe, war schlicht falsch gerechnet. Eine andere
> Formel einzusetzen wäre das Auswechseln einer Zelle und damit genau das,
> was Regel 2 verbietet.
>
> **Konsequenz, offen benannt:** Die Zelle ist damit nahezu redundant zu
> `progressive` (6 % Unterschied in der Spannweite). Das Gitter enthält
> effektiv **drei** unterschiedliche Konstruktionen plus eine Variante, die
> kaum variiert. Eine Kompression auf ~D/4 wäre der informativere Test
> gewesen; sie gehört jetzt in ein etwaiges E3, nicht in dieses Gitter.
> Ein Test (`test_single_flip_block_is_nearly_redundant`) hält die korrigierte
> Arithmetik fest, damit sie nicht zurückdriftet.

**Achse 2 — Stufenzahl Q: 4, 8, 16, 32.** Q = 16 ist der überlieferte Wert
und in jeder Variante enthalten.

**Achse 3 — Seeds: 42, 7, 1337** (die ersten drei der registrierten Menge).

**Umfang:** 4 × 4 × 3 = **48 Läufe**. Bei ~7,5 min je MNIST-Seed und
D = 10.000 sind das rund 6 Stunden. Falls das zu teuer ist, wird **vor dem
Start** auf D = 4.000 reduziert — für alle 48 Läufe gleichermaßen, nie für
einzelne Zellen, und der Referenzlauf `progressive/Q=16` wird zusätzlich bei
D = 10.000 gefahren, um den Effekt der Reduktion selbst zu beziffern.

> **Nachtrag 2026-08-16, vor dem ersten Sweep-Lauf — Fehler im Kriterium.**
>
> Die Reduktion auf D = 4.000 wird gezogen (Entscheidung der Projektleitung:
> sie steht im Gitter, also wird sie gefahren; sie im Nachhinein zu
> verwerfen, weil sechs Stunden machbar erscheinen, wäre genau die
> Anpassung, die eine Vorab-Registrierung verhindern soll).
>
> Damit fällt ein Fehler auf, den ich beim Schreiben des Gitters gemacht
> habe: **Das Akzeptanzkriterium ist eine absolute Zahl (≥ 85,5 %), die
> Baseline von 86,49 % stammt aber aus einer Messung bei D = 10.000.**
> Absolute Schwellen übertragen sich nicht über verschiedene Dimensionen.
> Drückt D = 4.000 alle Genauigkeiten um zwei bis drei Punkte, wäre das
> Kriterium mechanisch unerreichbar — GAP-1 würde als widerlegt erscheinen,
> obwohl nur die Dimension verkleinert wurde. Ein falscher Befund, und einer,
> der schwer zu bemerken wäre.
>
> **Reihenfolge deshalb geändert, vor dem Sweep:**
>
> 1. **Referenzlauf zuerst**, nicht danach: aktuelle Thermometer-Konfiguration,
>    Seeds 42/7/1337, je einmal bei D = 10.000 und D = 4.000. Das beziffert
>    den reinen Dimensionseffekt, unabhängig von der Konstruktion. Beide
>    Dimensionen werden frisch gemessen, damit der Effekt nicht mit den
>    Codeänderungen seit B5 (KNOWN-1, KNOWN-2) vermischt wird.
> 2. **Kriterium anpassen, falls nötig.** Dimensionseffekt > 0,5 pp → das
>    Kriterium wird als *Abstand zur D-4.000-Baseline* formuliert statt als
>    absolute Zahl. Effekt ≤ 0,5 pp → das absolute Kriterium bleibt. Die
>    Entscheidung wird hier mit Zeitstempel nachgetragen, **bevor** der Sweep
>    startet.
> 3. Dann erst die 48 Läufe.
> 4. **Gewinnerzelle abschließend bei D = 10.000 mit 5 Seeds bestätigen.** Ein
>    Ergebnis bei D = 4.000 ist ein Hinweis, kein Nachweis; erst die
>    Bestätigung bei voller Dimension entscheidet über GAP-1.
>
> Die vier Regeln unten gelten unverändert.

> **Nachtrag 2, 2026-08-16, Schritt 1 abgeschlossen — Kriterium umformuliert.**
>
> Referenzlauf gemessen, aktuelle Konfiguration (`progressive`, Q = 16),
> Seeds 42/7/1337, beide Dimensionen frisch:
>
> | Seed | D = 10.000 | D = 4.000 | Δ |
> |---|---|---|---|
> | 42 | 0,8054 | 0,7857 | −1,97 pp |
> | 7 | 0,8015 | 0,7831 | −1,84 pp |
> | 1337 | 0,7943 | 0,7666 | −2,77 pp |
> | **Mittel** | **0,8004** | **0,7785** | **−2,19 pp** |
>
> **Dimensionseffekt −2,19 pp**, also weit über der 0,5-pp-Grenze. Das
> absolute Kriterium ist damit nachweislich unbrauchbar: Die Schwelle von
> 85,5 % liegt 7,65 pp über der D-4.000-Baseline und wäre auch von einer
> perfekten Konstruktion kaum erreichbar gewesen. Der befürchtete falsche
> „GAP-1 widerlegt"-Befund war real und nicht bloß denkbar.
>
> **Neues Kriterium — Abstand zur D-4.000-Baseline.** Die Bänder werden als
> *Gewinn über die Baseline* ausgedrückt, was sie im Original implizit schon
> waren: „≥ 85,5 %" entsprach einem Gewinn von 5,43 pp über die
> D-10.000-Baseline von 80,07 %.
>
> | Band | bei D = 4.000, Baseline 77,85 % | Gewinn |
> |---|---|---|
> | **Erklärt** | ≥ **83,28 %** | ≥ 5,43 pp |
> | **Teilweise erklärt** | 79,85 % – 83,28 % | 2,00 – 5,43 pp |
> | **Nicht erklärt** | < **79,85 %** | < 2,00 pp |
>
> **Die Annahme dahinter, offen benannt:** Übertragen wird der *absolute*
> Gewinn. Ob eine bessere Konstruktion bei D = 4.000 dieselbe Punktzahl
> bringt wie bei D = 10.000, ist unbekannt — bei kleinerem D könnte eine
> bessere Kodierung mehr helfen (die Kapazität ist knapper) oder weniger
> (weniger Raum, den man besser nutzen kann). Gemessen wurde das nicht.
>
> Diese Annahme ist tragbar, weil der Sweep bei D = 4.000 **screent, nicht
> entscheidet**: Seine Aufgabe ist es, die 16 Zellen zu ordnen und eine
> Gewinnerin für Schritt 4 zu bestimmen. Über GAP-1 urteilt die Bestätigung
> bei D = 10.000 mit 5 Seeds. Eine unvollkommene Übertragung verschiebt also
> höchstens, *welche* Zelle in die Bestätigung geht — nicht den Ausgang.
>
> **Regressionsprüfung, als Nebenprodukt:** Die D-10.000-Werte reproduzieren
> die B5-Zahlen (alter Code, vor KNOWN-1 und KNOWN-2) auf allen drei Seeds
> **exakt**. Beide Speicherfixes haben MNIST nachweislich nicht berührt —
> was zu erwarten war, aber jetzt gemessen ist statt angenommen.
>
> Der Referenzlauf selbst ist zugleich Zelle `progressive`/Q = 16 des Gitters.
> Der Sweep fährt sie erneut; reproduziert sie nicht exakt, ist das ein
> Befund mit Vorrang.

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

### Ergebnis — gemessen 2026-08-16/17, eingetragen 2026-09-23

Alle 48 Zellen liefen durch (D = 4.000, Container, `canonical=false`,
Records in `results/e2_sweep/`). Eingetragen wurde das Ergebnis erst fünf
Wochen später — die Auswertung folgt ausschließlich den oben registrierten
Regeln, nichts wurde nachträglich an Bändern oder Kontrollen geändert.

| Konstruktion | Q=4 | Q=8 | Q=16 | Q=32 |
|---|---|---|---|---|
| `progressive` (Basis) | 0,7799 | 0,7754 | **0,7785** | 0,7800 |
| `linear_thermometer` | 0,7935 | 0,7964 | 0,7957 | **0,7994** |
| `random_levels` (Kontrolle) | 0,7833 | 0,7794 | 0,7826 | 0,7792 |
| `single_flip_block` | 0,7626 | 0,7711 | 0,7750 | 0,7786 |

(Mittel über Seeds 42/7/1337.)

**Referenzzelle reproduziert exakt:** `progressive`/Q=16 = 0,7857 / 0,7831 /
0,7666, bitgleich zum Referenzlauf aus Nachtrag 2.

**Negativkontrolle: VERLETZT.** `random_levels` ist bei Q = 4, 8, 16 *nicht*
schlechter als `progressive` (+0,34 / +0,40 / +0,42 pp), nur bei Q = 32
knapp (−0,08 pp). Nach der registrierten Regel misst die Achse damit nicht,
was sie zu messen vorgibt: **das Ergebnis der Konstruktions-Achse ist ohne
Aussagekraft.** Berichtet, nicht weginterpretiert. (Beobachtung ohne
Kriteriumsrang: `linear_thermometer` liegt in allen vier Q-Stufen 1,0–2,0 pp
über `random_levels` — Ordnung *kann* helfen, die ausgelieferte
`progressive`-Konstruktion nutzt sie nur nicht messbar.)

**Beste Zelle:** `linear_thermometer`/Q=32 mit 79,94 % = +2,09 pp über der
D-4.000-Basis 77,85 % → Band **„teilweise erklärt"**, 0,09 pp über der
Bandgrenze und damit innerhalb der Seed-Streuung (~0,6 pp).

**Schritt 4 (Bestätigung der Gewinnerzelle bei D = 10.000, 5 Seeds): nicht
ausgeführt.** Überholt durch E3 — die Lücke hat eine direktere Erklärung
(siehe dort). GAP-1 als Hauptursache ist durch E2 **nicht gestützt**.

---

## E3 — MNIST: Prototypen + T2 (die T2-These zur 6,42-pp-Lücke)

**Registriert 2026-09-23, vor dem Lauf auf dem Testsplit.** Harness
`python -m experiments.run_benchmark --task mnist --seeds 5 --pipeline prototypes --t2-epochs 2`.

### Die These

Der Referenzpunkt 86,49 % (Prototypen-only-Ablation der Aktenlage) lief
**mit zwei T2-Epochen**: D4 vermerkt für genau diesen Lauf „T2-Fehler Ep. 1/2
17,84 % / 15,16 %". Der Neubau lief ohne T2 (`t2_epochs = 0` war hart
kodiert), und T2 war in keinem Dokument als Ursache der Lücke betrachtet
worden — weder in GAP-1 noch in E2. Das ist der naheliegendere Kandidat als
die Thermometer-Konstruktion: Eine T2-Fehlerrate von ~18 % in der ersten
Epoche passt zu einem Startzustand von ~80 % — dem Neubau ohne T2.

### Evidenz vor dem Testlauf (Validierung, nicht Test)

`results/tuning/mnist_seed42.json`: Training auf den ersten 50.000, Validierung
auf den letzten 10.000 Trainingsbildern. Prototypen + 2 T2-Epochen:
**86,98 %**, T2-Fehler 18,20 % / 15,53 % — fast deckungsgleich mit den
historischen 17,84 % / 15,16 %.

### Kriterien (fixiert vor dem Testlauf)

| Band | Bedingung | Lesart |
|---|---|---|
| **These bestätigt** | \|Mittel − 86,49\| ≤ 1,5 pp über 5 Seeds | T2 erklärt die Lücke; GAP-1 wird als Ursache gestrichen |
| **Teilweise** | Mittel ≥ 83,5 %, aber außerhalb des Bandes | T2 erklärt einen Teil, Rest beziffert |
| **These widerlegt** | Mittel < 83,5 % | Lücke bleibt offen |

### Ergebnis — gemessen 2026-09-23, Container, `canonical=false`

Code-Stand `df971e1`, Records `results/mnist_*_20260923T21[1-3]*.json`.

| Seed | Accuracy | Macro-F1 | T2-Fehler Ep. 1 / 2 |
|---|---|---|---|
| 42 | 0,8542 | 0,8522 | 17,91 % / 15,21 % |
| 7 | 0,8564 | 0,8543 | 18,33 % / 15,69 % |
| 1337 | 0,8524 | 0,8497 | 18,56 % / 15,54 % |
| 2026 | 0,8548 | 0,8527 | 18,63 % / 15,57 % |
| 99 | 0,8555 | 0,8532 | 18,17 % / 15,54 % |
| **Mittel ± SD** | **0,8547 ± 0,0015** | **0,8524 ± 0,0017** | |

**THESE BESTÄTIGT** — |85,47 − 86,49| = 1,02 pp ≤ 1,5 pp. Zwei T2-Epochen heben
die Prototypen von 80,07 % (E1-Protokoll, ohne T2) auf 85,47 % (+5,40 pp) und
schließen damit 84 % der 6,42-pp-Lücke. Die T2-Fehlerraten (≈ 18,3 / 15,5 %)
treffen die historischen 17,84 / 15,16 % auf wenige Zehntel. GAP-1 (Thermometer-
Konstruktion) ist als Ursache gestrichen (`docs/DEVIATIONS.md`); die verbleibenden
~1 pp liegen im registrierten Band und werden nicht weiter zugeordnet.

**Provenienz.** Seeds 2026 und 99 tragen `code_changed_during_run = true`; die
gelisteten Dateien (`engramm/corruption.py`, `experiments/robustness*.py`,
`experiments/fetch_models.py`, Tests) sind neu und werden von `run_benchmark`
nicht importiert — das Ergebnis ist davon nicht berührt.

---

## E4 — M1b: MNIST, volle Pipeline (Episoden + Fusion + T2)

**Registriert 2026-09-23, vor dem Lauf auf dem Testsplit.** Harness
`python -m experiments.run_benchmark --task mnist --seeds 5 --pipeline full --config-from results/tuning/mnist_seed42.json`.

### Konfiguration — auf Validierung gewählt, nicht auf Test

Aus `results/tuning/mnist_seed42.json` (Gitter θ₀ × λe × T2-Epochen, alle
Zellen im Record): **T2 = 2 Epochen, λe = 0,25, λp = 1, θ₀ = 0,2, k = 32**,
Validierung 94,83 %. Die Wahl ist fast flach — alle Zellen mit Episoden
liegen zwischen 94,77 % und 94,83 % —, die Konfiguration trägt das Ergebnis
also nicht, die Architektur tut es.

### Referenzpunkte

Historisch 94,62 % (Seed 42) und **94,59 % ± 0,04** (5 Seeds) mit λe = λp = 1;
vorregistriertes M1b-Genauigkeitskriterium **≥ 94 %** (D5 §2).

### Kriterien (fixiert vor dem Testlauf)

1. **M1b-Genauigkeitskriterium:** Mittel über 5 Seeds ≥ 94,0 % → erfüllt.
2. **Replikation:** \|Mittel − 94,59\| ≤ 1,0 pp **und** Seed-SD ≤ 0,5 pp.
3. **Determinismus:** Seed 42 ein zweites Mal in einem eigenen Prozess —
   `predictions_sha256` muss identisch sein.
4. **Zeitkriterium (< 30 min CPU):** im Container nicht bewertbar
   (`docs/PROTOCOL.md` Regel 2). Die Wandzeit wird mitgeschrieben, ist aber
   kein Urteil. Offen bis zum Lauf auf dem M4.

**Erwartung:** Mittel 94,6–95,4 %. Gegenüber der Validierung (50.000
Trainingsbilder) lernt der Testlauf auf allen 60.000, was eher hebt.

### Ergebnis — gemessen 2026-09-23, Container, `canonical=false`

Harness wie registriert, Code-Stand `72e704e`, Records in `results/mnist_*_20260923T2*.json`.

| Seed | Accuracy | Macro-F1 | T2-Fehler Ep. 1 / 2 |
|---|---|---|---|
| 42 | 0,9488 | 0,9490 | 5,36 % / 5,18 % |
| 7 | 0,9475 | 0,9477 | 5,40 % / 5,17 % |
| 1337 | 0,9472 | 0,9473 | 5,58 % / 5,35 % |
| 2026 | 0,9472 | 0,9473 | 5,47 % / 5,23 % |
| 99 | 0,9490 | 0,9492 | 5,43 % / 5,20 % |
| **Mittel ± SD** | **0,9479 ± 0,0009** | **0,9481 ± 0,0009** | |

1. **M1b-Genauigkeitskriterium (≥ 94 %): ERFÜLLT** — 94,79 %.
2. **Replikation: bestätigt** — +0,20 pp gegenüber 94,59 %, SD 0,09 pp.
   Die T2-Fehlerraten (≈ 5,4 / 5,2 %) treffen die historischen 5,08 / 5,16 %
   bis auf wenige Zehntel.
3. **Determinismus: ERFÜLLT** — Schritt `repro` (2026-09-24): Seed 42 aus dem
   committeten Baum erneut gerechnet, `predictions_sha256` identisch; zusätzlich
   von einer unabhängigen Neuimplementierung bitgleich reproduziert (R1).
4. **Zeitkriterium:** im Container nicht bewertbar; Wandzeit 12,8–17,6 min je
   Seed inklusive Kodierung, teils unter Parallellast — kein Urteil.

**Provenienz-Vermerk.** Alle fünf Records tragen `git.changed_during_run = true`:
während des Laufs wurden Harnesses und Dokumente committet. Geprüft mit
`git diff --name-only 72e704e <Schreib-Commit> -- engramm/ data/loaders.py
experiments/run_benchmark.py experiments/common.py`: **leer** — keine vom Lauf
importierte Datei hat sich geändert (geändert wurden nur neue Harnesses unter
`experiments/m*.py`). Das Flag wurde danach verfeinert
(`code_changed_during_run`, `results/README.md`).

---

## E5 — M0: HNSW-Recall auf 10⁶ realen WiLI-Keys

**Registriert 2026-09-23, vor dem Lauf.** Harness
`python -m experiments.m0_bench --seed 42`: 10⁶ Byte-Fenster (100 B,
Schrittweite 50) aus WiLI-Trainingsabsätzen, D = 10.000; 1.000 Queries aus
Testabsätzen; FAISS `IndexBinaryHNSW` (M = 32, efConstruction = 40);
Recall@32 tie-tolerant gegen exakten Brute-Force.

**Kriterium (D5 §1, unverändert):** Recall@32 ≥ 95 % bei einem ef ∈ {64, 128, 256}.
**Erwartung:** Muster wie historisch (92,06 / 95,57 / 97,31 % bei ef 64 / 128 / 256);
ef = 64 unter, ef = 128 über 95 %. Die Schlüssel sind nicht bitgleich zu den
historischen (andere Fensterwahl, rekonstruierter Encoder), der Befund soll es sein.
**Energie/Query:** hier nicht messbar (keine Leistungsschnittstelle im
Container) — wird als *nicht gemessen* geführt, nicht geschätzt.
Mikrobenchmarks: Container-Werte, nicht offiziell (PROTOCOL Regel 2).

### Ergebnis — gemessen 2026-09-23, Container, `canonical=false`

Record `results/m0/m0_42_20260923T220003Z.json` (Code `ddaa446`, sauberer Baum).

| ef | Recall@32 tie-tolerant | strikt (IDs) | p50 / p99 (Container) | historisch |
|---|---|---|---|---|
| 64 | 0,8745 | 0,8675 | 1,50 / 2,40 ms | 0,9206 |
| 128 | 0,9195 | 0,9128 | 2,42 / 4,64 ms | 0,9557 |
| 256 | **0,9471** | 0,9408 | 3,83 / 7,18 ms | 0,9731 |

**KRITERIUM NICHT ERFÜLLT** — kein ef ∈ {64, 128, 256} erreicht 95 %; bester Wert
94,71 % bei ef = 256. Die Kurve liegt durchgehend 3–5 pp unter der historischen.
Das Muster der Erwartung (ef = 64 darunter, ef = 128 darüber) trat nicht ein.

**Warum die Zahlen nicht direkt vergleichbar sind.** Die Akten nennen nur
„10⁶ reale WiLI-Fenster-Keys“ mit Anker md5(keys[:1000]) = `709c99…d20a`; unsere
Keys (100-B-Fenster, Schrittweite 50, Anker `d6d227…7f7f`) sind andere. Nicht
überliefert sind außerdem die HNSW-Build-Parameter — M = 32 und efConstruction = 40
(FAISS-Standard) waren unsere Wahl. Beides beeinflusst den Recall direkt. Der
registrierte Befund bleibt davon unberührt: unter dem registrierten Setup ist M0
nicht erfüllt. Ob die W12-Frage („bricht HNSW auf Hamming-Clustern ein?“) am
Index-Aufbau hängt, prüft E5b.

Brute-Force 144,7 ms/Query (Container, 1 Thread, NumPy/FAISS-Flat; historisch 39,9 ms
auf dem M4), Energie nicht gemessen. Alle Zeiten Container, nicht offiziell.

---

## E5b — M0-Nachtrag: Recall in Abhängigkeit von der Build-Qualität (efConstruction)

**Registriert 2026-09-23, nach E5, vor dem Lauf.** Harness wie E5 mit
`--ef-construction {80, 160, 320}` (M = 32), dieselben 10⁶ Keys (Cache), dieselben
1.000 Queries, dieselbe Grundwahrheit.

**Warum zulässig und was es nicht ist.** efConstruction ist in den Akten nicht
überliefert, E5 hat den FAISS-Standard 40 genommen. E5b ist eine
Charakterisierung dieses freien Parameters, **kein Ersatz für E5**: E5 bleibt
„nicht erfüllt“ und wird so berichtet.

**Lesart (fixiert vor dem Lauf):** Erreicht mindestens ein efC ∈ {80, 160, 320}
Recall@32 ≥ 95 % bei ef = 128 (dem historischen GO-Punkt), gilt der
W12-Risikopunkt als **mit höherem Build-Aufwand entschärft** — äquivalent zum
historischen GO, mit dem Preis in Build-Zeit ausgewiesen. Erreicht keines 95 % bei
ef ≤ 256, ist W12 auf diesen Keys **nicht entschärft**.
**Erwartung:** efC = 160 erreicht ≥ 95 % bei ef = 128; Build-Zeit ~4× E5.

### Ergebnis — gemessen 2026-09-23/24, Container, `canonical=false`

Records `results/m0b/` (sauberer Baum; Build-Zeiten unter Parallellast und inkl.
Pausen während B3 — nicht offiziell, nur Größenordnung).

| efConstruction | ef = 64 | ef = 128 | ef = 256 | D5-Kriterium |
|---|---|---|---|---|
| 40 (E5) | 0,8745 | 0,9195 | 0,9471 | nicht erfüllt |
| 80 | 0,8689 | 0,9118 | 0,9377 | nicht erfüllt |
| 160 | 0,9093 | 0,9451 | **0,9696** | erfüllt ab ef = 256 |
| **320** | 0,9273 | **0,9595** | 0,9761 | **erfüllt ab ef = 128** |
| historisch (M4) | 0,9206 | 0,9557 | 0,9731 | erfüllt ab ef = 128 |

**Lesart nach Registrierung: W12 mit höherem Build-Aufwand ENTSCHÄRFT** — efC = 320
erreicht 95,95 % bei ef = 128 und bildet die historische Kurve auf 0,3–0,7 pp genau
nach. Der Preis ist Build-Zeit (hier ~8× E5 bei gleicher Last; Container, nicht
offiziell). efC = 80 liegt *unter* efC = 40: der Mehr-Thread-Aufbau von FAISS ist
nicht deterministisch, die Streuung zwischen zwei Builds liegt in der Größenordnung
1 pp — deshalb ist keine einzelne Nachkommastelle dieser Tabelle belastbar, wohl
aber der Trend über efC.

**Was bleibt:** E5 (registriertes Setup, efC = 40) ist **nicht erfüllt** und wird so
berichtet. E5b zeigt, dass das historische GO mit einem sorgfältiger gebauten Index
erreichbar ist — die historische efConstruction ist nicht überliefert.

---

## E6 — M2a: Konsolidierung durch Ähnlichkeitsabsorption

**Registriert 2026-09-23, vor dem Lauf.** Harness `python -m experiments.m2_stream --seed 42`.
50.000er-Strom (Banking77-Train komplett + 39.997 WiLI-Absätze), Chunks à 2.000
(T1 + eine LOO-T2-Epoche), T3 nach jedem Chunk; 5.430 Auswertungs-Queries.
Feste Konfiguration λe = λp = 1, θ₀ = 0 (M2 vergleicht Läufe mit/ohne T3,
nicht Konfigurationen).

**Kriterium (D5 §3, unverändert, UND):** Kompression ≥ 5× ∧ Δacc ≥ −1,0 pp ∧ T3-CPU ≤ 10 %;
No-Go-Pfad θ ∈ {0,20; 0,28; 0,35}.
**Erwartung: NICHT ERFÜLLT** — Kompression und T3-Kosten erfüllt, Δacc bei
θ = 0,12 schlechter als −20 pp (historisch −53,00 pp; Rauchtest bei D = 512 auf
8.000 Einträgen: 55,5 % → 6,3 %), kein θ im Sweep erfüllt Kompression und
Genauigkeit zugleich. Mechanismus wie W18: die prototypnahen Episoden werden
absorbiert, die atypischen stimmen allein ab.

### Ergebnis Seed 42 — gemessen 2026-09-23, Container, `canonical=false`

Record `results/m2/m2a_42_20260923T222830Z.json`. Referenz A (ohne T3): 82,43 %
(Banking77 77,82 / WiLI 88,47).

| θ_merge | Episoden behalten | Kompression | Accuracy | Δacc | T3-CPU-Anteil |
|---|---|---|---|---|---|
| 0,12 | 8.338 | **6,00×** | 47,24 % | **−35,19 pp** | 0,17 % |
| 0,20 | 10.707 | 4,67× | 57,75 % | −24,68 pp | 0,18 % |
| 0,28 | 17.435 | 2,87× | 60,98 % | −21,45 pp | 0,21 % |
| 0,35 | 26.155 | 1,91× | 70,00 % | −12,43 pp | 0,24 % |

**KRITERIUM NICHT ERFÜLLT** — genau wie registriert erwartet: Kompression ≥ 5× ✓ und
T3-CPU ≤ 10 % ✓, aber Δacc −35,19 pp ≪ −1 pp; kein θ im No-Go-Sweep erfüllt
Kompression und Genauigkeit zugleich. Das historische Negativergebnis (−53,00 pp)
ist qualitativ reproduziert; der Betrag ist kleiner, der Mechanismus derselbe.

Nebenbefund: im Strom senkt T2 die Referenz (A ohne T2: 85,34 % gegen A mit T2:
82,43 %) — Banking77 fällt mit T2 um 6,0 pp, WiLI steigt um 1,1 pp.

**Drei Seeds** (`results/m2/m2a_{42,7,1337}_*.json`), θ = 0,12:

| Seed | Referenz A | mit T3 | Δacc | Kompression |
|---|---|---|---|---|
| 42 | 82,43 % | 47,24 % | −35,19 pp | 6,00× |
| 7 | 82,73 % | 46,34 % | −36,39 pp | 5,76× |
| 1337 | 82,12 % | 46,87 % | −35,25 pp | 5,75× |
| **Mittel ± SD** | 82,42 % | | **−35,61 ± 0,68 pp** | 5,84× |

Auf allen drei Seeds **nicht erfüllt**, in derselben Weise.

---

## E7 — M2b: Verdrängung nach Nützlichkeit und Persistenz-Gate

**Registriert 2026-09-23, vor dem Lauf.** Harness `python -m experiments.m2b --seed 42`.

**(a) Charakterisierung, kein Gate:** Verdrängung auf 80 / 50 / 20 % Bestand.
Erwartung: monoton fallend, bei 80 % zwischen −2 und −10 pp (historisch −6,85 pp);
kein Redundanzüberschuss.

**(b) Persistenz-GATE:** Voll-Replay aus dem L2-Log gleich Live-Zustand
(Zustands-Digest **und** alle Vorhersagen) ∧ an jeder Chunk-Grenze Replay bis
dahin = Live-Zustand ∧ Crash-Replay nach 60-%-Byte-Schnitt = Zustand nach dem
letzten vollständigen Ereignis. Erwartung: **ERFÜLLT**, exakt.

### Ergebnis Seed 42 — gemessen 2026-09-23, Container, `canonical=false`

Record `results/m2/m2b_42_20260923T224248Z.json`.

**(a) Verdrängung nach Nützlichkeit** (Strom wie E6, Referenz 82,43 %):

| Bestand | Episoden | Accuracy | Δ | Banking77 | WiLI |
|---|---|---|---|---|---|
| 100 % | 50.000 | 82,43 % | — | 77,82 % | 88,47 % |
| 80 % | 40.000 | 76,45 % | **−5,99 pp** | 68,70 % | 86,60 % |
| 50 % | 25.000 | 67,70 % | −14,73 pp | 55,71 % | 83,40 % |
| 20 % | 10.000 | 53,09 % | −29,34 pp | 34,87 % | 76,98 % |

Monoton fallend, bei 80 % im erwarteten Band (−2 … −10 pp; historisch −6,85 pp);
kein Redundanzüberschuss — wie erwartet.

**(b) Persistenz-GATE: ERFÜLLT** (geloggter Lauf, 20.011 Ereignisse, 53,9 MB L2-Log):
Voll-Replay → Zustands-Digest und alle Vorhersagen identisch (75,89 % live = replayed);
10/10 Chunk-Grenzen identisch; Crash-Replay nach 60-%-Byte-Schnitt → 12.006 Ereignisse
wiederhergestellt, 1.372 Byte (angeschnittener Record) verworfen, Zustand und
Vorhersagen identisch zum Zustand nach dem letzten vollständigen Ereignis.

**Drei Seeds** (`results/m2/m2b_{42,7,1337}_*.json`): Persistenz-Gate auf **3/3**
erfüllt (Voll-Replay, 10/10 Checkpoints, Crash-Replay jeweils exakt); Verdrängung
auf 80 % Bestand −5,99 / −5,49 / −5,60 pp → **−5,69 ± 0,26 pp**.

---

## E8 — M3: 1.000 Autoren strikt sequenziell

**Registriert 2026-09-23, vor dem Lauf.** Harness `python -m experiments.m3 --seed 42`
(Protokoll GAP-10; Konfiguration auf 5 Validierungsposts je Autor gewählt).

**Kriterien (D5 §4, unverändert):** Vergessen (V1, Tranche-1-Block) ≤ 1,0 pp ∧
Lernzeit/Klasse ≤ 1 s; zusätzlich absolut Top-1 ≥ 30 % (R-1 unter 20 %), Top-5 ≥ 50 %,
Rekonstruktion exakt, Reihenfolge-Invarianz. **V2** (ratifiziert): Interferenz-
Vergessen der t2_local-Variante ≤ 1 pp.

**Erwartung:** V1 **NICHT ERFÜLLT** (Verdrängung bei wachsendem K, wie historisch
+10,00 pp); Top-1 zwischen 5 und 15 % (historisch 5,94 %), R-1 bleibt ausgelöst;
Zustands-Invarianz ✓; **Auslese-Invarianz ✓** (historisch verletzt, W19 — mit dem
Inhalts-ID-Tie-Break jetzt erwartet erfüllt); Rekonstruktion exakt ✓; V2 offen —
im Rauchtest (100 Autoren, D = 512) lag t2_local mit +4 pp *über* 1 pp.

### Ergebnis Seed 42 — gemessen 2026-09-24, Container, `canonical=false`

Record `results/m3/m3_42_20260924T005532Z.json` (Code `089f29f`, Vorverarbeitung v2 —
der erste Anlauf brach vor jeder Messung an NUL-Bytes ab, GAP-10). 1.000 von 4.244
geeigneten Autoren; Validierung wählte T2 = 2, λe = 0,5, θ₀ = 0,3 (Val-Acc 18,58 %).

| Variante | Top-1 | Top-5 | Vergessen V1 | Interferenz V2 | Lernzeit/Klasse (Container) |
|---|---|---|---|---|---|
| **full** (bewertet) | **14,61 %** | 27,44 % | **+21,10 pp** | −4,50 pp | 40 ms |
| t1_only | 9,83 % | 19,85 % | +10,40 pp | 0 | 1,3 ms |
| t2_local | 14,28 % | 26,09 % | +16,50 pp | **−5,30 pp** | 44 ms |

| Kriterium | Ergebnis |
|---|---|
| Vergessen V1 ≤ 1,0 pp | ✗ **nicht erfüllt** (+21,10 pp) — erwartet |
| Lernzeit/Klasse ≤ 1 s | ✓ (40 ms, Container) |
| Top-1 ≥ 30 % / Top-5 ≥ 50 % | ✗ (14,61 / 27,44 %) — R-1 (Top-1 < 20 %) bleibt ausgelöst |
| Rekonstruktion aus L2 | ✓ exakt (Zustand und alle 10.000 Vorhersagen, 1.461 = 1.461 Treffer) |
| Zustands-Invarianz | ✓ |
| **Auslese-Invarianz** | ✓ **0 Abweichungen** — historisch verletzt (W19), durch den Inhalts-ID-Tie-Break behoben |
| V2 (ratifiziert): Interferenz t2_local ≤ 1 pp | ✓ (−5,30 pp: T2 *hebt* den Tranche-1-Block gegenüber T1-only) |

**M3 insgesamt NICHT ERFÜLLT** (V1 und Top-1), wie registriert erwartet. Gegenüber
der Aktenlage ist das Ergebnis besser: Top-1 14,61 % statt 5,94 % (2,5×), und die
Auslese-Invarianz, die historisch fehlschlug, hält jetzt. Top-1 liegt knapp unter
dem erwarteten Band (5–15 %) an dessen Oberkante.

**Drei Seeds** (`results/m3/m3_{42,7,1337}_*.json`; die Validierung wählte je Seed
eigene Konfigurationen, immer mit T2 = 2):

| Seed | Top-1 | Top-5 | V1 (full) | V2 t2_local | Invarianz Zustand / Auslese | Rekonstruktion |
|---|---|---|---|---|---|---|
| 42 | 14,61 % | 27,44 % | +21,10 pp | −5,30 pp | ✓ / ✓ | exakt |
| 7 | 15,97 % | 27,70 % | +19,30 pp | −0,40 pp | ✓ / ✓ | exakt |
| 1337 | 15,80 % | 28,19 % | +16,00 pp | −4,50 pp | ✓ / ✓ | exakt |
| **Mittel ± SD** | **15,46 ± 0,74 %** | 27,78 ± 0,38 % | +18,80 ± 2,59 pp | alle ≤ 1 pp | 3/3 | 3/3 |

Auf allen drei Seeds dasselbe Bild: V1 und Top-1 **nicht erfüllt**; V2,
Invarianz und Rekonstruktion **erfüllt**. Top-1 liegt über dem erwarteten Band
(5–15 %) — besser als erwartet, weiterhin weit unter 30 %.

---

## E9 — M5: ENGRAMM gegen lokale LLM-Baselines (Banking77, CLINC150)

**Registriert 2026-09-23.** Harnesses `experiments/m5_engramm.py` (ENGRAMM,
Konfiguration aus `results/tuning/<task>_seed42_10shot.json`, `t2_local=True`),
`experiments/m5_baselines.py` (B0, B1, B3 in `.venv_b1`), Schiedsrichter
`experiments/m5_compare.py`. Seed 42 wie historisch; ENGRAMM und B0 zusätzlich
über 5 Seeds.

> **Offenlegung — keine blinde Erwartung für Banking77.** Vor dieser
> Registrierung lief ein Rauchtest des Harness mit der bereits feststehenden
> Konfiguration auf dem Banking77-*Testsplit* (Seed 42): ENGRAMM 63,73 %,
> B0 82,82 %. Die Konfiguration stammt aus der Validierung und bleibt
> unverändert; die Banking77-Erwartung unten ist aber nicht mehr blind.
> CLINC150 wurde nicht auf Test ausgewertet.

**Kriterien (D5 §6, Kriterium 4 in V2-Form, unverändert):** acc ≥ B1 − 5 pp ∧
Energie ≤ B1/10 ∧ Lernzeit ≤ B3/100 ∧ Interferenz ≤ 1 pp ∧ B3-Vergessen > 5 pp.
Kriterium 4 wird an der Konfiguration gemessen, deren Genauigkeit bewertet wird
(nicht aus M3 übernommen). **Energie ist im Container nicht messbar**; der
Schiedsrichter entscheidet nur, was ohne sie entscheidbar ist.

**Erwartung:** Genauigkeitslücke zu B1 > 15 pp auf beiden Aufgaben →
**(3) NIEDERLAGE** auf beiden, unabhängig von der Energie (historisch −20,4 / −22,0 pp).
ENGRAMM ~62–64 % (Banking77) / ~69–73 % (CLINC150, Validierung 72,8 %).
Lernzeit-Verhältnis zu B3 ≥ 100× (Wandzeit). B0 (bge-kNN, ohne LLM) liegt
voraussichtlich ebenfalls > 15 pp vor ENGRAMM — das ist kein registriertes
Kriterium, aber die schärfere Frage nach einer Effizienz-Nische.

### Ergebnis — gemessen 2026-09-23/24, Container, `canonical=false`

Records `results/m5/` (ENGRAMM und B0 je 5 Seeds, B1 und B3 Seed 42), Schiedsspruch
`results/m5/m5_verdict_seed42.json`. B1 lief mit zwei llama.cpp-Threads auf der CPU
(`docs/DEVIATIONS.md` CHANGED-8).

| | Banking77 | CLINC150 |
|---|---|---|
| ENGRAMM, 5 Seeds | 65,39 ± 1,26 % | 72,80 ± 0,32 % |
| ENGRAMM, Seed 42 (bewertet) | 63,73 % | 73,00 % |
| **B1** LLM+RAG (Qwen2.5-3B, Seed 42) | **80,52 %** | **90,38 %** |
| B0 bge-kNN, 5 Seeds | 83,92 ± 0,82 % | 86,57 ± 0,49 % |
| B3 LoRA in Tranchen | 14,71 %, Vergessen +66,1 pp | 34,40 %, Vergessen +76,2 pp |
| Abstand zu B1 | **16,79 pp** | **17,38 pp** |
| Lernzeit/Klasse ENGRAMM vs. B3 (Wand) | 7,6 ms vs. 5,19 s → 680× | 7,6 ms vs. 4,81 s → 634× |

| Kriterium | Banking77 | CLINC150 |
|---|---|---|
| 1 Genauigkeit ≥ B1 − 5 pp | ✗ | ✗ |
| 2 Energie ≤ B1/10 | nicht gemessen | nicht gemessen |
| 3 Lernzeit ≤ B3/100 | ✓ | ✓ |
| 4 Interferenz ≤ 1 pp ∧ B3-Vergessen > 5 pp | ✓ (0 pp; 66 pp) | ✓ (0 pp; 76 pp) |

**AUSGANG: (3) NIEDERLAGE auf beiden Aufgaben** — Genauigkeitslücke > 15 pp, damit
unabhängig von der nicht messbaren Energie entschieden. Wie registriert erwartet;
die historische Niederlage (−20,4 / −22,0 pp) ist reproduziert, der Abstand ist um
3,6 / 4,6 pp kleiner. B0 (ohne LLM) liegt auf Banking77 sogar vor B1: eine
Effizienz-Nische müsste gegen Embedding-kNN begründet werden, nicht gegen ein LLM.
CPU-Sekunden pro Query B1/ENGRAMM ≈ 625× (Proxy, keine Energie).

---

## E10 — M1 mit der historischen Architektur: WiLI 10-shot, volle Pipeline, λe = λp = 1

**Registriert 2026-09-23, vor dem Lauf auf dem Testsplit.** Harness
`python -m experiments.run_benchmark --task wili --shots 10 --seeds 5 --pipeline full --lambda-e 1 --theta0 0 --t2-epochs 0`.

### Warum dieser Lauf

Die README-Zahl 79,30 % wurde mit der **vollen Pipeline** und der damaligen
Standardkonfiguration λe = λp = 1 gemessen; E1 hat bisher nur die
Prototypen-Hälfte repliziert (Referenz 82,64 %). Die Validierung
(`results/tuning/wili_seed42_10shot.json`, 4.700 Absätze außerhalb der Shots)
zeigt zweierlei:

* **Das Episoden-Paradox reproduziert sich:** die beste Zelle ist λe = 0 —
  reine Prototypen, 84,96 %. Jede Episoden-Gewichtung verschlechtert. Die
  auf Validierung gewählte volle Pipeline *ist* auf WiLI also die
  E1-Konfiguration; ihr Testwert steht schon fest (84,79 % ± 0,37).
* **Die historische Konfiguration** (λe = λp = 1, θ₀ = 0, ohne T2) erreicht auf
  Validierung 78,45 % — nahe an den historischen 79,30 %. Mit T2 (2 Epochen)
  72,68 %; die historische Zahl passt also zur Variante ohne T2.

### Kriterium (fixiert vor dem Lauf)

**Replikation der README-Zahl:** \|Mittel − 79,30\| ≤ 3 pp über 5 Seeds (dasselbe
Band wie E1). **Erwartung:** 77,5–80 %. Offizielle M1-Zahl bleibt die
validiert beste Konfiguration (E1, 84,79 %); E10 zeigt nur, dass die
historische Zahl mit der historischen Architektur nachgemessen werden kann.

### Ergebnis — gemessen 2026-09-24, Container, `canonical=false`

Records `results/wili_*_20260924T0*.json`.

| Seed | 42 | 7 | 1337 | 2026 | 99 | **Mittel ± SD** |
|---|---|---|---|---|---|---|
| Accuracy | 0,7804 | 0,7824 | 0,7820 | 0,7813 | 0,7708 | **0,7794 ± 0,0049** |
| Macro-F1 | 0,7813 | 0,7814 | 0,7758 | 0,7790 | 0,7714 | 0,7778 ± 0,0042 |

**REPLIKATION DER README-ZAHL BESTÄTIGT** — |77,94 − 79,30| = 1,36 pp ≤ 3 pp, im
erwarteten Band (77,5–80 %). Die historischen 79,30 % sind damit als Wert der
*historischen Architektur* (volle Pipeline, λe = λp = 1, ohne T2) nachgemessen. Das
Episoden-Paradox bestätigt sich auf Test: dieselbe Pipeline ohne Episodenstimme
(E1, reine Prototypen) liegt 6,85 pp höher (84,79 %). Offizielle M1-Zahl bleibt
E1.

---

## E11 — Bitkorruptions-Robustheit (README-Roadmap Phase 4)

**Registrierung: `docs/PREREG_ROBUSTNESS.md` v1.3** (v1.0–1.2 am 15.08., v1.3 am
2026-09-23 vor jeder Messung dieser Studie). Harness
`bash experiments/robustness_all.sh` → `experiments/robustness.py` je (Aufgabe, Seed),
Referee `experiments/robustness_verdict.py`. 2 Aufgaben × 10 Seeds.

Dieser Eintrag registriert nichts neu, er hält nur die **Erwartung** fest,
bevor das erste offizielle Record existiert.

> **Offenlegung — die Erwartung ist nicht blind.** Vor diesem Eintrag liefen
> Rauchtests des Harness auf Teilmengen mit D = 2.048 (MNIST 3.000/1.000,
> Seeds 42 und 7; WiLI 6.000/2.000, Seed 42; Records nur im Scratchpad,
> `official = false`). Gesehen: ENGRAMM auf WiLI deutlich robuster als die
> int8-Kontrollen (R(25 %) 0,84 gegen 0,11), auf MNIST nicht klar (R(5 %)
> 0,84 gegen 0,88 der MLP); die 1-Bit-MLP liegt auf beiden Aufgaben nahe an
> ENGRAMM; die 1-Bit-LR auf WiLI hat acc(0) = 0,4 % (nach §4.1 nicht
> interpretierbar). Außerdem bekannt: E3, Prototypen + T2 auf MNIST ≈ 85,4 %.

**Erwartung.**

| Punkt | Erwartung |
|---|---|
| §9-Schwellen | ENGRAMM-MNIST knapp über 85 % (E3-Niveau) — das Risiko eines Abbruchs ist real; WiLI ≫ 60 %; MLP über 90 / 65 % |
| §9.1-Validierung p = 50 % | bestanden für alle Systeme und Formate |
| WiLI (§7) | bestätigt: ENGRAMM ≥ 0,10 über beiden int8-Kontrollen bei 5/10/25 % |
| MNIST (§7) | nicht bestätigt: Abstand zur int8-MLP bei 5 % unter 0,10 |
| Gesamtausgang | **TEILBESTÄTIGUNG (WiLI)** |
| §4.1-Lesart | Vorsprung auf WiLI gegenüber der 1-Bit-MLP < 0,10 bei 5 % → **dem Zahlenformat zuzuschreiben**, ein Vorteil der verteilten Repräsentation nicht gezeigt |
| float32 | kollabiert schon bei 1 % (vorab erwartet, nie Schlagzeile) |

### Ergebnis — gemessen 2026-09-23/24, Container, `canonical=false`

Records `results/robustness/{mnist,wili}_seed*.json` (je 10 Seeds), Referee-Ausgabe
`results/robustness/verdict.json` und `SUMMARY.md`. Kein vom Studienprozess
importierter Code änderte sich während eines Laufs.

**§9-Prüfungen:** alle Schwellen erfüllt (ENGRAMM MNIST 85,57 % ≥ 85, WiLI 92,11 % ≥ 60;
MLP 97,86 / 95,03 %; MLP gleiches Bitbudget 95,20 / 94,13 %); p = 50 %-Validierung für
jedes System und Format bestanden (mittleres R ≤ 0,05).

Mittleres R(p) über 10 Seeds, Primärvergleich:

| Aufgabe | System | R(5 %) | R(10 %) | R(25 %) |
|---|---|---|---|---|
| MNIST | **ENGRAMM** (binär) | **0,937** | **0,852** | **0,547** |
| | LR int8 | 0,374 | 0,242 | 0,095 |
| | MLP int8 | 0,378 | 0,144 | 0,031 |
| | *1-Bit-LR (§4.1)* | *0,884* | *0,732* | *0,453* |
| | *1-Bit-MLP (§4.1)* | *0,762* | *0,590* | *0,219* |
| WiLI | **ENGRAMM** (binär) | **0,993** | **0,987** | **0,952** |
| | LR int8 | 0,603 | 0,296 | 0,041 |
| | MLP int8 | 0,496 | 0,126 | 0,006 |
| | *1-Bit-MLP (§4.1)* | *0,834* | *0,696* | *0,259* |
| | *1-Bit-LR* | nicht interpretierbar (acc(0) 1,0 %) | | |

**AUSGANG NACH §7: BESTÄTIGT** — auf beiden Aufgaben liegt ENGRAMM bei 5, 10 und 25 %
um ≥ 0,10 über beiden int8-Kontrollen (kleinster Abstand 0,39), die 95-%-KIs
überlappen nirgends. Auch die Sekundärvergleiche (gleiches Bitbudget §3.3,
Item-Memory/idf-Zustand, T1-only) bestätigen.

**§4.1-LESART, je Aufgabe:**
- **WiLI:** der Vorsprung hält auch gegen die 1-Bit-Formatkontrolle (Abstand 0,16 /
  0,29 / 0,69) — hier ist ein Vorteil der verteilten Repräsentation gezeigt.
- **MNIST:** gegen die 1-Bit-LR bleibt der Abstand bei 5 % (0,05) und 25 % (0,09)
  unter 0,10 — der gemessene Vorsprung ist dort **dem Zahlenformat zuzuschreiben**,
  ein Vorteil der Repräsentation ist auf MNIST **nicht** gezeigt.

**Gegen die Erwartung:** erwartet war eine Teilbestätigung (nur WiLI) mit
Formatlesart auf WiLI. Eingetreten ist das Gegenteil der Formatlesart — MNIST ist
die formaterklärte Aufgabe, WiLI die, auf der der Vorsprung auch den Formattest
übersteht. float32 kollabiert erwartungsgemäß schon bei 1 % (nie Schlagzeile).
Container-Werte (`canonical=false`); Bestätigung auf dem M4 steht aus.

---

## R1 — Unabhängige Reproduktion nach README-Definition (Methode, Schritt 3)

**Durchgeführt 2026-09-23.** Die README definiert: eine separate Agenten-Session
leitet das Harness *aus der Spezifikation* ab und misst ohne Zugriff auf die
Implementierung, auf derselben Hardware. Das war bisher nicht möglich —
`docs/D2_SPEC.md` ist ein 21-Zeilen-Fragment, die Spezifikation stand faktisch
im Code. Ablauf:

1. `docs/SPEC_REBUILD.md` (1.217 Zeilen) aus dem Code abgeleitet: Hash-Eingaben
   Byte für Byte, Bit-/Rotationskonventionen, Tie-Regeln, T2, Retrieval-Ordnung,
   Operationsreihenfolge der Fusion, NumPy-PCG64-Pfade als reines Python,
   Konformitäts-Checkliste — **ohne** Test-Genauigkeiten oder Vorhersage-Digests.
2. Ein isolierter Agent erhielt nur dieses Dokument und die fünf Rohdaten-Archive
   (kein Zugriff auf `engramm/`, `experiments/`, `data/*.py`, `tests/`, `legacy/`,
   `results/`, Caches, Git-Historie) und implementierte neu:
   `reproduction/independent/`.

**Ergebnis:** 185/185 Konformitätsprüfungen bestanden; alle vier Konfigurationen
**bitgleich** zu den committeten Records (`results/repro/independent_verification.json`):

| Konfiguration (Seed 42) | Accuracy | Vergleich |
|---|---|---|
| WiLI 10-shot, Prototypen (E1) | 0,8488510638297873 | Accuracy + Macro-F1 identisch; `predictions_sha256` identisch mit dem Determinismus-Re-Run (`results/repro/wili_42_20260924T014451Z.json`) |
| MNIST, Prototypen T1 | 0,8054 | Accuracy + Macro-F1 identisch (Altrecord ohne Digest) |
| MNIST, Prototypen + T2 (E3) | 0,8542 | `predictions_sha256` identisch |
| MNIST, volle Pipeline (M1b/E4) | 0,9488 | `predictions_sha256` identisch |

**Determinismus-Re-Run** (Schritt `repro`, 2026-09-24, `results/repro/verification.json`):
MNIST volle Pipeline Seed 42 und WiLI 10-shot Seeds 42/7 aus dem committeten Baum
erneut gerechnet — alle drei bitgleich zu den Records (M1b auch per Digest).
Damit ist Kriterium 3 von E4 (Determinismus) erfüllt.

**Was das zeigt:** Die Spezifikation ist vollständig, die Vorhersagen sind auf
dieser Plattform deterministisch. **Was nicht:** Replikation durch Dritte auf anderer
Hardware; gleiche Python-/NumPy-Version, gleicher Maschinentyp (`canonical=false`).
Gemeldete Spec-Lücken (alle ohne Einfluss auf Vorhersagen) stehen in der
Verifikationsdatei.

---

## M1 — WiLI-2018, voller Trainingssplit (keine Vorregistrierung)

**Kein E-Eintrag, und das mit Absicht.** Eine Erwartung wird gegen einen
Referenzpunkt registriert; für diesen Lauf gibt es keinen. Die überlieferte
M1-Zahl (79,30 %, bzw. 82,64 % ohne Episodenschicht) wurde im
**10-shot**-Setting gemessen. Ein Volldaten-Ergebnis existiert in den Akten
nicht, also gibt es nichts zu replizieren und nichts vorherzusagen.

Der Lauf beantwortet eine andere Frage: *Was leistet dieser Kern, wenn er
alle 500 Absätze je Sprache sieht statt zehn?*

### Drei Zahlen, die nicht vermischt werden dürfen

| Zahl | Setting | Referenzpunkt | Status |
|---|---|---|---|
| **84,79 % ± 0,37** | WiLI 10-shot | 82,64 % (Prototypen-only, Akten) | E1, Replikation bestätigt |
| **89,82 %** (Seed 42) | WiLI voll | **keiner** | Diagnoselauf, 5-Seed-Lauf ausstehend |
| 80,07 % ± 0,42 | MNIST voll | 86,49 % (Prototypen-only, Akten) | **6,42 pp offen**, siehe E2 |

Die 89,82 % sind **nicht** ein besseres Ergebnis als die 84,79 % — sie
stammen aus einem Setting mit fünfzigmal so vielen Trainingsdaten. Sie sind
auch **nicht** die Antwort auf O1: die dortige Frage betrifft ausschließlich
die 10-shot-Zahl und ihren Referenzpunkt. Und sie erklären nichts am
MNIST-Abstand — anderer Datensatz, anderer Encoder.

### Veröffentlichungssperre

**Diese Zahl geht in keine Unterlage, solange der MNIST-Abstand von 6,42 pp
ungeklärt ist.** Der Grund ist nicht die Zahl selbst, sondern was ihre
Veröffentlichung suggerieren würde: dass der Neubau vermessen und verstanden
ist. Er ist vermessen, aber auf einem der beiden Datensätze weicht er um 6,42
Punkte ab, ohne dass jemand sagen kann warum. Eine gute Zahl neben einer
ungeklärten zu veröffentlichen, verschiebt die Aufmerksamkeit genau in die
falsche Richtung.

Dieselbe Sperre gilt für die 84,79 % (bereits in E1 vermerkt) und für alles,
was aus beiden abgeleitet wird.

### Ergebnis — gemessen 2026-08-16, Container, `canonical=false`

| Seed | Accuracy | Macro-F1 | Peak | Halbierungen |
|---|---|---|---|---|
| 42 | 0,8982 | 0,9019 | 906 MiB | 0 |
| 7 | 0,8976 | 0,9012 | 906 MiB | 0 |
| 1337 | 0,8975 | 0,9013 | 915 MiB | 0 |
| 2026 | 0,8980 | 0,9017 | 915 MiB | 0 |
| 99 | 0,8980 | 0,9017 | 915 MiB | 0 |
| **Mittel ± SD** | **0,8979 ± 0,0003** | **0,9016 ± 0,0003** | 912 MiB | 0 |

**Kein Kriterium erfüllt oder verfehlt** — es gab keines, siehe oben. Die
Zahl steht für sich.

**Determinismus.** Seed 42 ergibt 0,8982 / 0,9019, exakt wie der Diagnoselauf
*vor* dem Streaming-Umbau. Damit ist die Äquivalenz von gebatchtem und
ungebatchtem Training nicht nur an synthetischen Fixtures belegt, sondern am
vollen Korpus über einen Codewechsel hinweg.

**Halbierungen: 0 in allen fünf Seeds.** Die Bedingung, unter der gebatchtes
Lernen exakt ist (`docs/DEVIATIONS.md` KNOWN-2), ist damit für diesen Lauf
nachgewiesen und nicht nur erwartet.

**Speicher: 912 MiB ± 5** gegen die vorab gesetzte Schwelle von 6,00 GB.

**Streuung.** Die SD von 0,0003 ist rund zwölfmal kleiner als im
10-shot-Setting (0,0037). Das ist erwartbar — bei 500 statt 10 Beispielen je
Klasse wirkt sich die Ziehung kaum noch aus, und die verbleibende Varianz
stammt fast nur noch aus Item-Memory und Tie-Auflösung. Als Beobachtung
notiert, nicht als Befund: eine Erklärung dafür wurde nicht gemessen.

**Provenienz-Vermerk.** Seed 99 trägt Commit `e323a05a`, die übrigen vier
`721808ad`. Ursache ist ein Zwischencommit zur Datensicherung während des
Laufs; der Diff zwischen beiden Hashes enthält ausschließlich `results/`,
keinen Code.

---

## E12 — ENGRAMM-LM: Texte schreiben nur durch Lesen und Zählen

**Registrierung: `docs/PREREG_LM.md` v1.0** (2026-09-25, vor Tokenizer, Modellcode
und jeder Messung auf val/test). Korpus: 1 C4-en-Shard + WikiText-103-Train,
Dokument-Hash-Split; Metrik Bits pro Byte; Kernaussage P2 = Zusatznutzen des
HDC-Teils (KNN + TOPIC) gegenüber dem exakten Null-Modell (KN-5 + ∞-Gramm + Cache).

**Erwartung.**

| Punkt | Erwartung |
|---|---|
| BPB ENGRAMM-LM / KN-5 | ≈ 0,93 (0,88–0,97); P1 (≤ 0,90) eher verfehlt |
| P2 (≥ 2 % unter Null-Modell, KI < 1) | knapp, ~45 % |
| G2 (Pilot, ≥ 1 %) | eher bestanden |
| P3 umformulierte Fakten | knapp, ~50 % |
| P4 Vergessen exakt | erfüllt (by construction) |
| P5 M4 | im Container offen |
| P6 Richter ≥ 60 % gegen KN-5 | knapp, ~55 % |
| Transformer 12 h CPU | etwa gleichauf; GPT-2 small klar besser (≈ 0,72 × KN-5) |

### Zwischenergebnisse — gemessen 2026-09-25, Container, `canonical=false`

Records `results/lm/g0_kn_pilot_*.json`, `g1_pilot_*.json`, `g2_pilot_*.json`. Pilot = erste
30 M Train-Tokens; Messung auf val-B Hälfte 2, Near-Duplicate-gefiltert.

| Tor | Ergebnis |
|---|---|
| G0 | bestanden: KN-2…5 monoton (1,867 → 1,759 → 1,745 → 1,743 BPB, ungefiltert), Σp = 1 bis 4e-16 |
| G1 | bestanden: KN-5 1,759 · KN-5 + Cache 1,686 · Null-Modell 1,670 BPB (−5,0 % gegen KN-5) |
| **G2 (KILL)** | **ausgelöst (K1):** ENGRAMM-LM gegen Null-Modell −0,46 / −0,45 / −0,45 % (Seeds 42/7/1337), Mittel 0,45 % < 1 %. Ablation Seed 42: nur KNN 1,6624, nur TOPIC 1,6700 (= Null-Modell) |

**Gegen die Erwartung:** G2 war „eher bestanden" erwartet. Der KNN-Teil hilft messbar und
seed-stabil, aber nur um ein Drittel der registrierten Schwelle; der Themenvektor bringt
nichts über den Dokument-Cache hinaus. Nach §9 gilt der HDC-Teil damit als gescheitert; die
Studie läuft auf dem Null-Modell weiter und wird trotzdem vollständig gemessen.

Nebenbefund Pruning: unbeschnittenes KN-5 erreicht im Pilot 1,719 statt 1,743 BPB (ungefiltert,
−1,4 %), braucht aber 2,0 statt 0,15 GB — bei 285 M Tokens nicht im RAM-Budget. Die
registrierte Referenz „KN-5" ist beschnitten; P1 ist dadurch um etwa 1,4 % leichter.

### Hauptlauf — 285 M Tokens, gemessen 2026-09-25/26, Container, `canonical=false`

**Aufbau** (Seed 42, τ = 1.024, β = 8 aus dem Pilot-Gitter, eingefroren):

| Schritt | Dauer |
|---|---|
| Suffix-Array | 77 s |
| KN-5 | ≈ 7 min |
| Bedeutungsvektoren + Klassen | ≈ 2,5 min |
| KNN-Index | ≈ 1,7 min |
| Segment-Signaturen | ≈ 2,4 min |
| **gesamt** | **≈ 15 min** |

Spitzenlast des Systems beim KN-Aufbau 9,0 GB (einschließlich des parallel trainierenden Transformers mit 2,6 GB). Ein erster Versuch lief in den OOM-Killer; der Aufbau wurde daraufhin speicherschonend umgebaut, der Digest bleibt identisch (Commit `71eb216`).

**K2 und Ablation (val-B Hälfte 2, gefiltert):**

| System | BPB |
|---|---|
| KN-5 | 1,6076 |
| KN-5 + Cache | 1,5540 |
| Null-Modell | 1,5301 |
| Null + KNN | 1,5196 |
| Null + TOPIC | 1,5299 |
| **ENGRAMM-LM** | **1,5194** |

- ENGRAMM-LM / Null-Modell = 0,9930 [0,9923; 0,9936]. **K2 ist nicht ausgelöst**, der HDC-Beitrag wächst mit den Daten von 0,45 % auf 0,70 %.
- Der Beitrag kommt fast ganz aus KNN; TOPIC bleibt bei ≈ 0.
- Explorativ: Pro Token hilft KNN am meisten, wo der 3-Gramm-Kontext unbekannt ist (0,069 Bit/Token), aber auch bei bekannten 4-Token-Kontexten noch 0,044 Bit.

**KenLM-Parität:** KenLM (Commit `4cb443e`, `lmplz -o 5`, unbeschnitten) gegen unser KN-5 unbeschnitten, Pilot, val-B/2: BPB-Verhältnis **1,0000014** — gleich bis auf Rundung. Registriert war ≤ 0,3 %.

**P3 (umformulierte Fakten, 400 Abfragen, Top-10):**

| System | vorher | nachher B/C | Top-1 | gleiche Form A |
|---|---|---|---|---|
| ENGRAMM-LM | 1,0 % | 25,75 % | 6,5 % | 100 % |
| KN-5-gelernt | 0,25 % | 26,5 % | 7,0 % | 100 % |
| Null-Modell-gelernt | 1,0 % | 26,75 % | 7,0 % | 100 % |

- **P3 verfehlt, K4 ausgelöst:** ENGRAMM-LM liegt nicht über KN-5-gelernt.
- Treffer entstehen fast nur, wo Abfrage und gelernter Satz auf dasselbe Wort vor der Antwort enden: „Captain", „Mount" 100 %, „river"/„the" 65 %.
- Echte Umformulierungen findet keines der Systeme (Autor, Maskottchen, Sprache: 0 %).
- Der Themen-Term des KNN reicht nicht, um unter 200 ähnlich gebauten Fakten den richtigen zu treffen.

**P4 (Vergessen):**
- learn(A) → learn(B + Canary) → forget(B + Canary) ergibt denselben Digest wie learn(A).
- Die Canary-Log-Wahrscheinlichkeit ist nach dem Vergessen **bitgleich** zu „nie gelernt" (−142,456184 Bit). Die Exposure fällt von 7,65 zurück auf 2,07.
- Log-Replay (303 Ereignisse) reproduziert den Zustand.
- Batch-Aufruf: 56 ms (lernen) / 37 ms (vergessen) je 1.000 Tokens → **P4 erfüllt** (Container).
- Einzelaufrufe je Fakt: 54 ms pro Aufruf, also 3,6 s je 1.000 Tokens bei sehr kurzen Texten; das berichtet P4 nicht als Kriterium.
- Ein erster P4-Lauf verglich den Canary gegen den falschen Zustand (vor learn(A)). Das war ein Fehler im Harness, nicht im Modell; er ist korrigiert, beide Records liegen vor.

**P5 — ein Befehl für den M4:** `python -m experiments.lm_p5 --scale main`. Er misst Neuaufbau, Schreiben mit Quellenangabe und Spitzen-RSS in einem Prozess. Container-Lauf 2026-09-26 (`results/lm/p5_device_main_*.json`, nicht offiziell):

| Messgröße | Wert | Schwelle | im Container |
|---|---|---|---|
| Aufbau | 566 s | ≤ 12 h | erfüllt |
| Schreiben mit Quellen | 109 Tokens/s | ≥ 25 | erfüllt |
| Spitzen-RSS | 8,9 GB | ≤ 10 GB | erfüllt |

**Auf dem M4 gemessen, 2026-09-26** (MacBook Air M4, 16 GB, macOS, Python 3.13, `caffeinate -i`, Record `p5_device_main_20260926T161917Z.json`, `canonical=true`):

| Messgröße | M4 | Schwelle |
|---|---|---|
| Aufbau aus 285 M Tokens | **544 s** (KN-5 180 s, Suffix-Array 46 s, Codebuch 51 s, KNN-Index 251 s, Signaturen 17 s) | ≤ 12 h |
| Schreiben mit Quellenangabe je Token | **118,9 Tokens/s** | ≥ 25 |
| Spitzen-RSS | **6,2 GB** | ≤ 10 GB |

**P5 erfüllt.** Die W16-Bedingungen (Netzteil, Deckel offen, alleiniger Lauf) sind nicht
maschinell protokolliert. `caffeinate` lief.

**Plattform-Befund.** Der Basis-Digest unterschied sich zunächst zwischen Container
(`4c03b17a…`) und M4 (`2f6ee03a…`). `python -m experiments.lm_digests` zeigt, wo:
- **bitgleich auf beiden Plattformen:** Tokenstrom, KN-5-Tabellen, Suffix-Array,
  Bedeutungsvektoren (eng, weit), Wortklassen, idf, KNN-Index, Segment-Signaturen und die
  KNN-Distanzgrenzen;
- **verschieden** waren allein die Mischungsgewichte in den letzten Float-Bits.
  Auf 10⁻⁹ gerundet waren auch sie gleich.

Die Ursache: EM summiert Gleitkommazahlen, und Linux und macOS runden dabei im letzten
Bit unterschiedlich.

**Behoben** (das kündigte der Plan als „λ in Festkomma" an und war nicht umgesetzt):
- Die Gewichte werden nach der EM auf ein 2⁻²⁴-Raster gerundet.
- Jedes Gewicht bleibt ≥ 2⁻²⁴. Ein erster Versuch ohne diese Untergrenze setzte ein
  winziges KN-Gewicht auf 0, und `lm_eval` brach mit „nicht geglättet" ab.
- Jede Zeile summiert exakt auf 1.
- Neuer Container-Digest: `b45c2065…`.

**Wirkung auf die Testzahlen** (Test einmal neu ausgewertet, beide Records liegen vor):

| System | vorher | nachher |
|---|---|---|
| ENGRAMM-LM | 1,51357694 | 1,51357693 |
| Null-Modell | 1,52484518 | 1,52484518 |
| Pilot-ENGRAMM | 1,66396 | 1,66378 (durch die Untergrenze) |
| P2-Verhältnis | 0,99261024 | 0,99261024 |

Das Urteil bleibt unverändert.

**Auf dem M4 bestätigt (2026-09-26):** Mit Festkomma-Gewichten liefert der M4 den Basis-Digest
`b45c20659e5591ff…` — identisch zum Container. Alle Teile (Tokenstrom, KN-5, Suffix-Array,
Bedeutungsvektoren, Wortklassen, idf, KNN-Index, Signaturen, Mischungsgewichte) sind auf
Linux x86-64 und macOS arm64 **bitgleich**. Das ENGRAMM-LM ist damit plattformübergreifend
exakt reproduzierbar.

**P5 (nur Container, nicht offiziell):**
- Schreiben: 128 Tokens/s, mit Quellenangabe je Token 117 Tokens/s; KN-5 allein 211 Tokens/s.
- Spitzen-RSS 4,5 GB; Aufbau ≈ 15 min.
- K3 nicht ausgelöst. Die offizielle Messung auf dem M4 steht aus.

**P6 (Lesequalität, 200 Test-Prompts × 2 Reihenfolgen, LLM-Richter):**
- ENGRAMM-LM wird in **19,8 %** bevorzugt (64 Siege, 30 Remis, 306 Niederlagen), in beiden Reihenfolgen gleich → **P6 klar verfehlt**.
- Ursache, gesichtet an Beispielen: Der Dokument-Cache verstärkt beim Schreiben die eigenen, zufällig gezogenen Wörter und Wortstücke („information information", „theAs", „InIn"). Auf echtem Text ist er die stärkste Einzelhilfe (−3,3 % BPB), beim Selbstschreiben schadet er.
- Der Bogen für das menschliche Panel liegt in `results/lm/p6_panel_form.md`; das Panel ist nicht durchgeführt.

**Explorativ, nicht registriert — Schreibmodus.** Entworfen nach Sichtung der registrierten Texte, gemessen auf **val-B-Prompts** (nicht test), 100 Prompts × 2 Reihenfolgen. Einstellungen: Cache beim Schreiben aus (sein Gewicht geht an KN-5), top-p 0,8, beide Seiten gleich dekodiert.

| Vergleich | ENGRAMM bevorzugt | Ø längste wörtliche Übernahme |
|---|---|---|
| gegen KN-5 | **78,3 %** | 24,9 gegen 11,3 Tokens |
| gegen Null-Modell (gleicher Modus) | 53,3 % | 24,9 gegen 20,8 Tokens |

Lesart:
- Der Schreibmodus behebt die Artefakte.
- Der Vorsprung gegen KN-5 kommt überwiegend aus dem ∞-Gramm-Teil (längere wörtliche Stücke, durch den Zitat-Deckel auf 32 Tokens begrenzt), **nicht** aus dem HDC-Teil. Gegen das Null-Modell bleibt nur ein Unterschied im Rauschbereich.
- Das ändert kein registriertes Urteil.

### Testsplit — einmalige Auswertung 2026-09-26 (`results/lm/test_eval_*.json`)

Alle Konfigurationen waren vorher eingefroren. Test: 1.092 von 1.137 Dokumenten nach dem Near-Duplicate-Filter.

| System | BPB test | BPB WikiText-103-Test |
|---|---|---|
| KN-5 (285 M, beschnitten) | 1,6050 | 1,5418 |
| KN-5 + Cache | 1,5485 | 1,4892 |
| Null-Modell | 1,5248 | 1,4473 |
| **ENGRAMM-LM** | **1,5136** | **1,4332** |
| Transformer 6 h CPU (Referenz) | 1,6376 | 1,5966 |
| GPT-2 small (fremd, Einordnung) | 1,0388 | 0,9773 |

- Transformer: der 12-h-Checkpoint ist durch einen Container-Neustart verloren. 1 h: 1,998, 3 h: 1,798.
- GPT-2: 124 M Parameter, 40 GB Trainingstext.

| Kriterium | Wert | Ergebnis |
|---|---|---|
| P1: ENGRAMM / KN-5 ≤ 0,90 | 0,943 [0,939; 0,948] | **verfehlt** |
| P2: ENGRAMM / Null-Modell ≤ 0,98, KI < 1 | 0,9926 [0,9921; 0,9931] | **verfehlt** (KI < 1 erfüllt, Größe nicht) |
| P3 | 25,75 % gegen 26,5 % | **verfehlt**, K4 |
| P4 | Digest und Canary bitgleich, 56/37 ms je 1k | **erfüllt** |
| P5 | Container 128 Tokens/s, 4,5 GB, ≈ 15 min Aufbau | **offen** (nur M4) |
| P6 | 19,8 % | **verfehlt** |

Die Tore: K1 ist ausgelöst, K2 nicht, K3 nicht, K4 ist ausgelöst, K5 nicht.

**AUSGANG NACH §11: WIDERLEGT (K1, P2 verfehlt)** — Referee `experiments/lm_verdict.py`, `results/lm/VERDICT.json`.

**Gegen die Erwartung:**
- Das Verhältnis zu KN-5 traf die Erwartung genau: 0,943 gegen erwartete ≈ 0,93, Band 0,88–0,97.
- Die Aufteilung ist aber anders als gedacht: 5,0 % bringt der exakte Teil (∞-Gramm + Cache), nur 0,7 % der HDC-Teil.
- Erwartet waren P2 knapp, P3 knapp und P6 knapp. Eingetreten ist dreimal „klar verfehlt".
- Der Transformer lag mit 6 h CPU unter Last noch hinter KN-5, statt gleichauf.
- GPT-2 small ist mit 0,65 × KN-5 noch deutlich besser als die erwarteten ≈ 0,72.

**Was bleibt:**
- ENGRAMM schreibt Englisch allein durch Zählen: ohne neuronales Netz und ohne fremdes Modell, in 15 Minuten gebaut, mit 128 Tokens/s auf der CPU.
- Es lernt neue Texte in Millisekunden und vergisst sie bitgenau.
- Es nennt für jedes Wort seine Quelle.
- Der HDC-Teil hilft messbar und seed-stabil, aber für die registrierte Kernaussage zu wenig.

---

## E13 — ENGRAMM-LM Schreibmodus (v2)

**Registrierung: `docs/PREREG_LM_V2.md`** (2026-09-26, vor der Messung). Frische Test-Prompts
201–400 (E12/P6 nutzte 1–200), Hauptmodell aus E12 unverändert, Cache beim Schreiben aus,
top-p 0,8. LLM-Richter blind, beide Reihenfolgen.

| Kriterium | Ergebnis | Erwartung |
|---|---|---|
| **V1**: gegen KN-5 (400 Urteile) | **65,5 %** (ENGRAMM zuerst 67,8 %, zweites 63,3 %) → **erfüllt** (≥ 60 %) | ~75 % |
| **V2**: gegen Null-Modell (200 Urteile) | **52,5 %** → **verfehlt** | 50–55 % |

- Längste wörtliche Übernahme im Mittel: ENGRAMM 23,5 Tokens gegen KN-5 10,9 und Null-Modell 23,3. Der Zitat-Deckel liegt bei 32 Tokens.
- **Lesart:** Im Schreibmodus schreibt ENGRAMM-LM Texte, die ein Richter denen von KN-5 klar vorzieht. Der Grund sind die längeren übernommenen Stücke aus dem ∞-Gramm.
- Der HDC-Teil verbessert die Texte nicht messbar (V2 im Rauschbereich).
- Der Vorsprung fiel kleiner aus als explorativ auf val-B (78 %). Das spricht dafür, dass die explorative Zahl optimistisch war.
- Der Schreibmodus ist seitdem der Standard der CLI (`python -m engramm.lm write`).

---

## E14 — ENGRAMM-Chat, Stufe 1: Nachschlagen statt Plappern

**Registrierung: `docs/PREREG_CHAT.md` v1.0** (2026-09-26, vor Indexbau und Messung).
ENGRAMM beantwortet eine englische Frage mit dem passendsten Satz aus allem, was es gelesen
oder mit `learn` gelernt hat, samt Quelle — oder sagt „I don't know“. Kein fremdes Modell,
auch nicht in der Bewertung (exakter Abgleich mit den SQuAD-Goldantworten).

### Ergebnis — gemessen 2026-09-26, Container, `canonical=false`

Record: `results/chat/chat_stage1_container_20260926T211521Z.json` (Commit `e5c2c52`, sauber).
Satzindex: 15.991.369 Sätze, 23.258 Begriffe, 223 M Einträge, Bau 12 s, Digest `7e024abb…`.
Pool: 16.977 von 98.169 SQuAD-Fragen (3.361 von 20.958 Absätzen, 16 %). Auf Dev gewählt:
α = 2, θ = 2,169 (Dev: Präzision 60,0 % bei 20,0 % Abdeckung).

| | Kriterium | Ergebnis (Test, 1.000 Fragen) | Schwelle | Erwartung | |
|---|---|---|---|---|---|
| **C1** | Hit@1 ENGRAMM-Chat | **41,7 %**, KI [38,7; 44,7] (Hit@5 54,4 %) | ≥ 30 % | ~60 % | **erfüllt** |
| **C2** | Hit@1 − Hit@1(BM25) | **+19,9 pp**, KI [17,2; 22,5] (BM25: 21,8 %) | ≥ 2 pp, KI > 0 | ~30 % | **erfüllt** — aber siehe Ablation |
| **C3** | Präzision bei θ von Dev | 61,4 % bei **18,9 %** Abdeckung | ≥ 55 % bei ≥ 25 % | ~70 % | **verfehlt** (Abdeckung) |
| **C4** | 200 erfundene Fakten, Frage B/C → gelernter Satz auf Platz 1 | **96,8 %** (B 97,0 %, C 96,5 %; ohne HDC 95,3 %) | ≥ 80 % | ~85 % | **erfüllt** |
| **C5** | Median-Antwortzeit | **26 ms** (p90 47 ms), Container | ≤ 1 s | erfüllt | **erfüllt** (Container; M4 offiziell ausstehend) |

**Ausgang nach §5:** „Nützlich“ verlangt C1 **und** C3 → **nicht erreicht**, weil C3 an der
Abdeckung scheitert. „HDC-Beitrag bestätigt“ (C2) → **formal erfüllt**.

### Explorativ, nicht registriert: Woher kommt der C2-Gewinn?

`experiments/chat_explore.py`, Record `results/chat/chat_stage1_explore_20260926T211717Z.json`.
S_HDC belohnt ein Fragewort, das *wörtlich* im Satz steht, mit sim = 1 — und ähnliche Wörter mit
sim < 1. Ablation „exakt“: dieselbe Formel, aber sim = 1 nur für identische Begriffe, sonst 0.
Das ist eine idf-gewichtete Wortabdeckung **ohne** Bedeutungsvektoren. α mit derselben Regel auf Dev.

| System (Test) | Hit@1 |
|---|---|
| BM25 | 21,8 % |
| BM25 + exakte Abdeckung (α = 2) | 40,4 % |
| BM25 + S_HDC (α = 2, registriert) | 41,7 % |

- exakt − BM25: **+18,6 pp**, KI [16,1; 21,1].
- HDC − exakt: **+1,3 pp**, KI [−0,5; 3,0] — nicht signifikant. Auf Dev war „exakt“ sogar
  leicht besser (40,6 % gegen 40,0 %).
- **Lesart:** Das registrierte Kriterium C2 ist erfüllt, die *Deutung* „die Bedeutungsvektoren
  helfen“ trägt es aber nicht. Fast der ganze Gewinn kommt daher, dass BM25 mit seiner
  Längennormierung kurze Sätze bevorzugt, die nur einen Teil der Frage abdecken; der
  Abdeckungsterm korrigiert das. Der Anteil der HDC-Ähnlichkeit ist höchstens klein — dasselbe
  Muster wie in E12 (0,74 %) und E13 (52,5 %).
- Präzision nach Abdeckung auf Test (explorativ): 61 % bei 10 %, 59 % bei 25 %, 55 % bei 40 %,
  42 % bei 100 %. Ein anders gewähltes θ hätte C3 erreicht; die registrierte θ-Regel (60 % auf
  Dev) war zu streng für die Abdeckungsschwelle. Das wird **nicht** nachträglich umgedeutet.

### Was man daraus mitnimmt

- ENGRAMM findet für 42 % der Wissensfragen den Satz mit der Antwort auf Platz 1 und für 54 %
  unter den ersten fünf — in 26 ms, mit Quelle, ohne jedes neuronale Modell.
- Selbst gelernte Fakten findet es auch bei anderer Formulierung fast immer (97 %). Nach
  `forget` sind sie weg.
- Fehlerbild aus den Beispielen: Es gibt ganze Sätze zurück, keine Antworten. Es liefert
  manchmal eine *Frage* aus dem Korpus („When did Ángel Labruna die?“), und
  Fragen nach Mengen oder Zeitpunkten brauchen den Satz *mit* der Zahl, nicht nur den
  thematisch passenden. Das sind die Aufgaben von Stufe 2 (Faktengedächtnis) und Stufe 4
  (formulierte Antworten).
- **Blinder Fleck der Messung:** SQuAD-Fragen wurden *aus* dem Absatz geschrieben, der garantiert
  im Korpus steht, und teilen viele Wörter mit dem Antwortsatz. Freie Fragen laufen deutlich
  schlechter. Stichprobe mit dem eingefrorenen System (CLI, nicht registriert): „Who invented the
  telephone?“ → „I can't remember who invented the telephone.“ (C4-Web); „What is the capital of
  Australia?“ → die Frage „What is Australia capital city?“; „When did the Titanic sink?“ → ein
  Werbesatz mit „sink just like the Titanic“ (der richtige Wikipedia-Satz kam als Alternative 1).
  Ohne Satztyp-Filter und Antworttyp-Prüfung sind 42 % eine Obergrenze für den Alltag, keine Erwartung.
- Der Chat ist im Dashboard (Karte „Fragen“) und per `python -m engramm.lm ask "…"` nutzbar,
  mit den eingefrorenen Dev-Werten α = 2, θ = 2,169.

---

## E15 — ENGRAMM-Chat v2: Stufen 1.1 bis 5

**Registrierung: `docs/PREREG_CHAT_V2.md`** (v1.0 vor dem Bau; v1.1 vor der Testmessung erlaubt
zusätzlich Zählstatistik aus SQuAD-Fragen fremder Artikel). Testdaten sind mit der Registrierung
eingefroren (Manifest `6f31deb6…`). Kein fremdes KI-Modell, weder im System noch in der Bewertung.

### Entwicklung auf Dev (alles vor dem Testlauf, Werte der eingefrorenen Pipeline)

| Schritt | SQuAD-Dev2 | NQ-Dev |
|---|---|---|
| Stufe 1 (eingefroren, v1-Index) | Hit@1 40,3 % | Hit@1 2,2 % |
| + Abdeckung, Vorsatz, Titel/URL, Antworttyp, Fragesätze, Phrasen, Dokument-Abdeckung | 46,5 % | 4,3 % |
| + Satzgrenzen v2 („12.5“, „U.S.“, „Mr.“ trennen nicht mehr), Dokumentindex | **47,0 %** | **4,55 %** |
| Kurze Antwort, nur Regeln | EM 12,9 %, F1 21,7 % | EM 1,5 % |
| + Datums-Granularität, Einheiten, „X and Y“, Definitionen, Richtungsregel | EM 16,0 %, F1 23,6 % | – |
| + gezählte Spannenwahl (Nachtrag v1.1) und Nähe | **EM 19,65 %, F1 26,1 %** | EM 1,75 % |

- **HDC im Retrieval:** Das weiche Bedeutungs-Match aus Stufe 1 erhält auf Dev das Gewicht 0.
  Sobald die exakte Abdeckung im Modell ist, trägt es nichts mehr bei (Ablation: 47,0 % mit
  und ohne). Auch der HDC-Typabgleich bei der Extraktion bringt +0,1 pp, also Rauschen.
- **HDC im Faktengedächtnis:** Dort trägt es. Mit Tippfehler findet das Trigramm-Gedächtnis
  auf Dev 99,5 % der Fakten, ein exaktes Wörterbuch 0 %.
- **Fehler, die der Dev-Lauf gefunden hat:**
  - Der schnelle Pfad lief anfangs über `turn()`. NQ-Anfragen ohne Fragesatz („the current
    central bank of the united states is“) wurden deshalb *gelernt* statt beantwortet.
    Behoben mit `ask()` und der Regel für unvollständige Aussagen.
  - Die Definitionsregel zerstörte „What was X called?“. Behoben.
- θ nach der A2-Regel: 7,0293. Auf Dev ergibt das 55,0 % Präzision bei 18,35 % Abdeckung;
  die Abdeckungsschwelle von A2 (20 %) ist also schon auf Dev knapp verfehlt.

### Testmessung — einmalig, 2026-09-27, Container, `canonical=false`

Record: `results/chat/chat_v2_test_container_20260927T030020Z.json` (Commit `8f25f67`, sauber,
unverändert während des Laufs; 37 min, 8,7 GB Spitze). Gedächtnis ist das volle ENGRAMM-LM, wie
im Dashboard.

| | Kriterium | Test | Schwelle | Erwartung | |
|---|---|---|---|---|---|
| **R1** | SQuAD-Test2 Hit@1 v2 − Stufe 1 | **+7,9 pp** [5,7; 10,2] (36,3 → 44,2 %) | ≥ 3 pp, KI > 0 | ~60 % | **erfüllt** |
| **R2** | NQ-Test Hit@1 v2 − Stufe 1 | **+2,02 pp** [1,36; 2,69] (2,69 → 4,71 %) | ≥ 2 pp, KI > 0 | ~50 % | **erfüllt** (knapp) |
| **F1** | erfundene Fakten, Test-Frageform | **93,0 %** | ≥ 90 % | ~85 % | **erfüllt** |
| **F2** | mit Tippfehler; Vorsprung vor exaktem Wörterbuch | **85,0 %**; Wörterbuch 0 % → +85 pp | ≥ 75 %, ≥ 30 pp | ~70 % | **erfüllt** |
| **F3** | Enthaltung vor dem Lernen | **100 %** | ≥ 90 % | ~70 % | **erfüllt** |
| **D1** | Dialoge: Fakten zurück | **93,2 %** (800 Fragen) | ≥ 90 % | ~75 % | **erfüllt** |
| **D2** | nach „vergiss“: Wert weg (a); Digest = Kontrolle (b) | **76,5 % / 75,0 %** | je 100 % | ~95/99 % | **verfehlt** |
| **D3** | Rückfrage mit Pronomen | **85,5 %** (55) | ≥ 80 % | ~70 % | **erfüllt** |
| **A1** | SQuAD-Test2 EM / F1 | 18,8 % [16,5; 21,3] / 25,3 % | ≥ 20 % / ≥ 30 % | ~40 % | **verfehlt** |
| **A2** | mit θ von Dev: Präzision bei Abdeckung | 58,6 % bei 17,4 % | ≥ 50 % bei ≥ 20 % | ~50 % | **verfehlt** (Abdeckung) |
| **A3** | NQ-Test EM | 1,9 % [1,5; 2,4] | ≥ 5 % | ~35 % | **verfehlt** |
| **U1** | Browsertest (Playwright, `tests/test_chat_ui.py`) | 8/8 Schritte | besteht | ~90 % | **erfüllt** |
| **U2** | Median-Zeit pro Chat-Runde | 8 ms (p90 0,44 s; Fragen mit Nachschlagen ≈ 0,37 s) | ≤ 1 s | ~90 % | **erfüllt** (Container) |
| **U3** | Determinismus, Neustart aus dem Log | Transkripte identisch; Digest und 80 Antworten nach Replay identisch | identisch | ~90 % | **erfüllt** |

**Ausgang nach §5:** Stufe **1.1 erfüllt**, Stufe **2 erfüllt**, Stufe **3 verfehlt** (D2),
Stufe **4 verfehlt** (A1, A2, A3), Stufe **5 erfüllt**.

### Warum D2 fällt (Analyse nach dem Test, ändert das Ergebnis nicht)

- Die Test-Formulierungen „People call me X.“, „I have a brother called X.“ und „I have a dog
  named X.“ werden alle als Fakt über **USER** mit fast gleichen Beziehungswörtern
  (`called`, `name`, `#name`) gespeichert. Nur `brother` bzw. `dog` unterscheidet sie.
- „Please delete what I told you about my name“ trifft deshalb oft den Bruder oder den Hund.
  Ebenso betreffen alle 40 im Record gespeicherten D1-Fehler (von insgesamt 54) Name, Bruder
  oder Hund.
- Auf Dev lief das fehlerfrei, weil „My name is X“ und „My brother's name is X“ verschiedene
  Muster trafen. Ein Strukturfehler: „mein Bruder“ ist eine eigene Entität, kein Attribut von
  USER.
- F1/F2-Fehler: „Which explorer first reached X?“ zu „was discovered by“, „Who runs X
  Industries?“ zu „chief executive“, „Who is the owner of X?“ zu „is owned by“. Die Entität wird
  gefunden, aber die Beziehung teilt kein Wort und kaum Bedeutung, sodass die Konfidenz unter
  der Schwelle liegt. Das System enthält sich dann; es rät nicht falsch.

### Was man daraus mitnimmt

- ENGRAMM ist jetzt ein Gesprächspartner, der drei Dinge kann:
  - Antworten nachschlagen, mit Quelle.
  - Sich merken, was man ihm erzählt, auch bei Tippfehlern.
  - Auf Befehl bitgenau vergessen: Digest und Antworten sind nach einem Neustart aus dem Log
    identisch.
- Die gemessenen Grenzen sind klar: Kurze Antworten stimmen bei SQuAD in 19 % der Fälle genau.
  Bei echten Suchanfragen (NQ) fehlt dem 285-M-Token-Korpus meist das Wissen; nur in 30 % der
  Fälle steht die Antwort überhaupt unter den Kandidaten.
- HDC trägt dort, wo Ähnlichkeit statt Gleichheit zählt: beim tippfehlertoleranten
  Faktengedächtnis (+85 pp gegenüber einem exakten Wörterbuch). Im Retrieval und bei der
  Antwortwahl bringt es nichts Messbares; das ist dasselbe Muster wie in E12–E14.
- Offene Punkte führen zu einer neuen Registrierung mit neuen Testdaten, nicht zu einer
  Nachbesserung dieses Tests.

---

## E16 — ENGRAMM-Chat v3: zweite Runde der Stufen 1.1 bis 5

**Registrierung: `docs/PREREG_CHAT_V3.md`** (2026-09-27, nach E15 und vor jeder v3-Änderung).
Die Testdaten sind neu und ungesehen:
- SQuAD: die nächsten 1.000 Fragen der Test-Artikel.
- NQ: 3.610 Fragen aus `train`, Positionen 2.000–5.609.
- Neue Formulierungen, Namen und Werte (Manifest `8c0fbfa8…`).

Schwellen unverändert aus v2.

### Änderungen (nur auf Entwicklungsdaten entschieden: v2-Dev und die verbrauchten v2-Testdaten)

- **Besitz-Entitäten:** „my brother“ oder „my dog“ ist eine eigene Entität (`USER:brother`),
  kein Attribut von dir. Das behebt die E15-Ursache von D2.
- **Robustere Grammatik:** Kurzformen („What's“), einleitende Floskeln („These days …“), „our“,
  „I'm employed by“, „…, please?“, bis zu drei Verbwörter („earn my living as“). Die
  Begriffsgruppen gelten für die ganze Beziehung.
- **Namensregel:** Ein unbekanntes Wort am Satzanfang ist ein Name („Shosrifaer was born …“).
- **Ein-Fakt-Regel:** Weiß ENGRAMM über ein Ding (nicht über dich) genau eine Sache vom
  erfragten Typ, antwortet es damit und sagt, dass es das Einzige ist, was es weiß.
- **θ nach der A2-Regel** auf 3.000 Dev-Fragen: 6,9512.
- Auf den verbrauchten v2-Testdaten stieg D2 damit von 76,5/75,0 % auf 100/100 %, die Fakten
  von 93/85 % auf 100/100 %. Weiche F1-Labels für die Spannenwahl wurden geprüft und
  verworfen (EM 16,2 % gegen 19,75 %).

### Testmessung — einmalig, 2026-09-27, Container, `canonical=false`

Record: `results/chat/chat_test3_container_20260927T042240Z.json` (Commit `8d8dfe3`, sauber,
unverändert während des Laufs; 30 min, 8,3 GB Spitze).

| | Kriterium | v2 (E15) | **v3-Test** | Schwelle | |
|---|---|---|---|---|---|
| **R1** | SQuAD Hit@1 − Stufe 1 | +7,9 pp | **+7,7 pp** [5,6; 9,9] (39,0 → 46,7 %) | ≥ 3 pp, KI > 0 | **erfüllt** |
| **R2** | NQ Hit@1 − Stufe 1 | +2,02 pp | **+1,52 pp** [0,94; 2,13] (2,08 → 3,60 %) | ≥ 2 pp, KI > 0 | **verfehlt** |
| **F1** | Fakten, neue Frageform | 93,0 % | **95,0 %** | ≥ 90 % | **erfüllt** |
| **F2** | mit Tippfehler; Wörterbuch | 85,0 %; 0 % | **93,5 %; 0 %** | ≥ 75 %, ≥ 30 pp | **erfüllt** |
| **F3** | Enthaltung vorher | 100 % | **100 %** | ≥ 90 % | **erfüllt** |
| **D1** | Dialogfakten | 93,2 % | **92,1 %** | ≥ 90 % | **erfüllt** |
| **D2** | Vergessen a / b | 76,5 / 75,0 % | **96,0 / 90,0 %** | je 100 % | **verfehlt** |
| **D3** | Pronomen-Rückfrage | 85,5 % | **100 %** | ≥ 80 % | **erfüllt** |
| **A1** | SQuAD EM / F1 | 18,8 / 25,3 % | **19,8 / 26,7 %** | ≥ 20 / ≥ 30 % | **verfehlt** |
| **A2** | Präzision @ Abdeckung | 58,6 @ 17,4 % | **54,6 @ 20,7 %** | ≥ 50 @ ≥ 20 % | **erfüllt** |
| **A3** | NQ EM | 1,9 % | **1,3 %** | ≥ 5 % | **verfehlt** |
| **U1–U3** | Browser, Zeit, Determinismus | erfüllt | **erfüllt** (Median 8 ms, p90 0,36 s; Replay identisch) | | **erfüllt** |

**Ausgang:**
- Stufe **2** und **5** zum zweiten Mal erfüllt.
- Stufe **3** verfehlt, aber knapp: D1 und D3 erfüllt, D2 bei 96/90 % statt je 100 %.
- Stufe **1.1** verfehlt: R2 liegt diesmal unter der 2-pp-Linie; in v2 lag es knapp darüber.
- Stufe **4** verfehlt: A2 ist jetzt erfüllt, A1 und A3 nicht.

### Analyse nach dem Test (ändert das Ergebnis nicht)

- **D1/D2:**
  - „I earn my living as a nurse“ bekam die Begriffsgruppe `#home`, weil „living“ in meiner
    Wohn-Liste stand. Dadurch wurde „What do I do for work?“ nicht beantwortet (alle 40
    gespeicherten D1-Fehler).
  - Beim Vergessen konkurrierte der Job-Fakt mit dem Wohnort.
  - Das ist ein Fehler in der handgeschriebenen Tabelle, kein Rauschen.
- **F1/F2:** „What is the birthplace of X?“ teilt kein Wort mit „was born in“, und die Frage
  hat keinen erkannten Antworttyp. Die Ein-Fakt-Regel greift deshalb nicht, und ENGRAMM
  enthält sich.
- **R2:** Der Gewinn auf NQ schwankt mit der Stichprobe um die Schwelle: +2,0 pp auf der
  NQ-Validierung, +1,5 pp auf NQ-train-Fragen. Die Konfidenzintervalle überlappen.
- **A1:** EM 19,8 % [17,3; 22,3] liegt an der Schwelle. F1 30 % ist mit der regelbasierten und
  gezählten Spannenwahl nicht in Reichweite (Dev ≈ 26 %).
- **A3:** NQ-EM ≥ 5 % ist mit diesem Korpus strukturell nicht erreichbar. Nur in 30 % der
  Fälle steht die Antwort überhaupt unter den Kandidaten, und die Satz-Trefferquote liegt bei
  3,6–4,7 %.

### Was man daraus mitnimmt

- Jede Runde mit neuen Formulierungen deckt neue Lücken einer handgeschriebenen Grammatik auf
  und schließt die alten. Die Werte steigen: D2 von 76 auf 96 %, F2 von 85 auf 94 %.
- 100 % auf *ungesehenen* Formulierungen erreicht so ein Regelsystem nicht zuverlässig. Das
  ist der ehrliche Preis dafür, ohne gelerntes Sprachmodell zu arbeiten.
- Die Stärken sind stabil: exaktes Vergessen mit bitgleichem Replay, Tippfehler-Toleranz
  durch HDC und Antworten mit Quelle in unter einer Sekunde.

---

## E17 — ENGRAMM-Chat v4: dritte Runde, frische Formulierungen

**Registrierung: `docs/PREREG_CHAT_V4.md`.** Der Code war vor der Registrierung eingefroren
(`c4a3c29`), die Testformulierungen entstanden danach. Record:
`results/chat/chat_test4_container_20260927T050651Z.json` (Commit `56c178f`, sauber).

| | v2 | v3 | **v4** | Schwelle | |
|---|---|---|---|---|---|
| R1 SQuAD Hit@1 +pp | +7,9 | +7,7 | **+7,3** [5,1; 9,6] | ≥ 3 | **erfüllt** |
| R2 NQ Hit@1 +pp | +2,02 | +1,52 | **+1,61** [1,02; 2,19] | ≥ 2 | **verfehlt** |
| F1 / F2 / F3 | 93 / 85 / 100 % | 95 / 93,5 / 100 % | **95 / 93 / 100 %** | 90 / 75 / 90 | **erfüllt** |
| D1 | 93,2 % | 92,1 % | **38,1 %** | ≥ 90 % | **verfehlt** |
| D2 a / b | 76,5 / 75,0 % | 96 / 90 % | **97,5 / 47,5 %** | je 100 % | **verfehlt** |
| D3 | 85,5 % | 100 % | **90,9 %** | ≥ 80 % | **erfüllt** |
| A1 EM / F1 | 18,8 / 25,3 % | 19,8 / 26,7 % | **20,9 / 26,7 %** | 20 / 30 % | **verfehlt** (F1) |
| A2 | 58,6 @ 17,4 % | 54,6 @ 20,7 % | **55,9 @ 18,8 %** | 50 @ 20 % | **verfehlt** (Abdeckung) |
| A3 | 1,9 % | 1,3 % | **1,7 %** | 5 % | **verfehlt** |
| U1–U3 | erfüllt | erfüllt | **erfüllt** | | **erfüllt** |

**Ausgang:** Stufen 2 und 5 zum dritten Mal erfüllt; 1.1, 3 und 4 verfehlt.

**Lesart:**
- Die Ich-Grammatik war eine Liste von Satzmustern. Sie verallgemeinert nicht. Auf die neuen
  Formen
  - „Hi, I'm X.“,
  - „X is my brother.“,
  - „I moved to X last year.“,
  - „By trade I'm a X.“,
  - „I really love X.“

  passt keines der Muster, und D1 fällt von 92 auf 38 %.
- Die Fehler häufen sich genau bei diesen Formen („Who am I?“, „What's my occupation?“, „What
  do I love to eat?“, „Which colour is my favourite?“).
- Das Vergessen selbst bleibt exakt: Der Wert ist in 97,5 % der Fälle weg. Nur der Digest
  weicht ab, weil nicht verstandene Sätze bei Kontrolle und Dialog unterschiedlich zerlegt
  werden.
- **A1:** Die EM-Schwelle ist erstmals erreicht (20,9 %). F1 bleibt bei 26,7 %; die 30 % sind mit
  dieser Spannenwahl nicht erreichbar.
- **Konsequenz:** Weitere Runden mit neuen Mustern jagen nur den eigenen Formulierungen
  hinterher. Nötig ist eine Zerlegung ohne Satzmuster. Die nächste Runde (v5) ersetzt die
  Mustertabelle deshalb durch eine allgemeine Regel: Wert = die genannte Angabe; Beziehung =
  die übrigen Inhaltswörter; Besitz aus „my …“.

---

## E18 — ENGRAMM-Chat v5: Zerlegung ohne Satzmuster, frische Formulierungen

**Registrierung: `docs/PREREG_CHAT_V5.md`**. Code vor der Registrierung eingefroren (`70b7646`).
Record: `results/chat/chat_test5_container_20260927T060624Z.json` (Commit `d3b314a`, sauber).

| | v2 | v3 | v4 | **v5** | Schwelle | |
|---|---|---|---|---|---|---|
| R1 +pp | +7,9 | +7,7 | +7,3 | **+7,1** [5,1; 9,3] | ≥ 3 | **erfüllt** |
| R2 +pp | +2,02 | +1,52 | +1,61 | **+1,69** [1,08; 2,30] | ≥ 2 | **verfehlt** |
| F1 / F2 / F3 | 93 / 85 / 100 | 95 / 93,5 / 100 | 95 / 93 / 100 | **100 / 99,5 / 100 %** | 90 / 75 / 90 | **erfüllt** |
| D1 | 93,2 | 92,1 | 38,1 | **67,9 %** | ≥ 90 % | **verfehlt** |
| D2 a / b | 76,5 / 75 | 96 / 90 | 97,5 / 47,5 | **100 / 87,5 %** | je 100 % | **verfehlt** (b) |
| D3 | 85,5 | 100 | 90,9 | **100 %** | ≥ 80 % | **erfüllt** |
| A1 EM / F1 | 18,8 / 25,3 | 19,8 / 26,7 | 20,9 / 26,7 | **18,5 / 25,3 %** | 20 / 30 | **verfehlt** |
| A2 | 58,6 @ 17,4 | 54,6 @ 20,7 | 55,9 @ 18,8 | **48,6 @ 18,3 %** | 50 @ 20 | **verfehlt** |
| A3 | 1,9 | 1,3 | 1,7 | **1,7 %** | 5 % | **verfehlt** |
| U1–U3 | erfüllt | erfüllt | erfüllt | **erfüllt** | | **erfüllt** |

**Lesart:**
- Die Zerlegung ohne Satzmuster hebt D1 auf frischen Formulierungen von 38 auf 68 %. Das
  Faktengedächtnis für Dritte ist praktisch perfekt (100 / 99,5 %).
- Die restlichen Fehler liegen bei zusammengesetzten Sätzen:
  - „I eat X almost every week, it's my favourite“ liefert den Wert „favourite“.
  - „I adore the colour X“.
  - „At work I'm a X“ enthält kein Berufswort.
- Die Werte der Stufe 4 und R2 schwanken von Runde zu Runde innerhalb ihrer
  Konfidenzintervalle um die Schwellen (A1-EM 18,5–20,9 %, R2 +1,5 bis +2,0 pp). Das ist
  Stichprobenrauschen, kein Fortschritt und kein Rückschritt.
- **Konsequenz für v6:** Fragen über dich werden, wenn das Faktengedächtnis nichts Sicheres
  findet, in deinen eigenen Sätzen nachgeschlagen und die Antwort herausgeschnitten, wie im
  Korpus. Das hängt nicht vom Satzbau ab.

---

## E19 — ENGRAMM-Chat v6: Nachschlagen in den eigenen Sätzen

**Registrierung: `docs/PREREG_CHAT_V6.md`**, Code eingefroren vor der Registrierung (`e5fd108`).
Record: `results/chat/chat_test6_container_20260927T070342Z.json` (Commit `a0fbfc0`, sauber).

| | v4 | v5 | **v6** | Schwelle | |
|---|---|---|---|---|---|
| R1 +pp | +7,3 | +7,1 | **+5,0** [3,0; 7,1] | ≥ 3 | **erfüllt** |
| R2 +pp | +1,61 | +1,69 | **+1,97** [1,41; 2,55] | ≥ 2 | **verfehlt** (um 0,03 pp) |
| F1 / F2 / F3 | 95 / 93 / 100 | 100 / 99,5 / 100 | **100 / 99 / 100 %** | 90 / 75 / 90 | **erfüllt** |
| D1 | 38,1 | 67,9 | **86,5 %** | ≥ 90 % | **verfehlt** |
| D2 a / b | 97,5 / 47,5 | 100 / 87,5 | **89,0 / 85,5 %** | je 100 % | **verfehlt** |
| D3 | 90,9 | 100 | **100 %** | ≥ 80 % | **erfüllt** |
| A1 EM / F1 | 20,9 / 26,7 | 18,5 / 25,3 | **16,6 / 23,3 %** | 20 / 30 | **verfehlt** |
| A2 | 55,9 @ 18,8 | 48,6 @ 18,3 | **48,4 @ 18,8 %** | 50 @ 20 | **verfehlt** |
| A3 | 1,7 | 1,7 | **1,8 %** | 5 % | **verfehlt** |
| U1–U3 | erfüllt | erfüllt | **erfüllt** | | **erfüllt** |

**Lesart:**
- D1 auf frischen Formulierungen steigt weiter (38 → 68 → 86,5 %). Die restlichen Fehler:
  - „risotto is what I like **to eat** most“: „to“ galt als Hinweiswort, und das Verb „eat“
    wurde zum Wert.
  - „The name's X“ wurde nicht als Ich-Aussage erkannt.
- Beim Vergessen fehlten gemeinsame Kategorien („my car“ gegen „I own a Toyota“). Der Zufall
  der Superposition entschied.
- Die Werte für SQuAD und NQ schwanken mit der Stichprobe: SQuAD-Test6 liegt für beide Systeme
  niedriger, der Stufe-1-Bezug ebenfalls.

---

## E20 — ENGRAMM-Chat v7, und Bilanz über sechs Testrunden

**Registrierung: `docs/PREREG_CHAT_V7.md`**, Code eingefroren vor der Registrierung (`2725824`).
Record: `results/chat/chat_test7_container_20260927T075745Z.json` (Commit `a621ad9`, sauber).

v7-Ergebnis:
- R1 +6,2 pp [4,0; 8,4] und **R2 +2,33 pp** [1,72; 2,96]: beide erfüllt.
- F1/F2/F3 100 / 97,5 / 100 %: erfüllt.
- D1 77,0 %: verfehlt. D2 96,0 / 85,0 %: verfehlt. D3 100 %: erfüllt.
- A1 19,2 / 26,6 %: verfehlt. **A2 54,7 % bei 20,1 %**: erfüllt. A3 1,9 %: verfehlt.
- U1–U3: erfüllt.
- **Stufen erfüllt: 1.1, 2, 5.** Nicht erfüllt: 3, 4.

### Alle registrierten Testläufe (jeweils frische Daten, gleiche Schwellen)

| Kriterium | v2 | v3 | v4 | v5 | v6 | v7 | Schwelle |
|---|---|---|---|---|---|---|---|
| R1 SQuAD +pp | 7,9 ✅ | 7,7 ✅ | 7,3 ✅ | 7,1 ✅ | 5,0 ✅ | 6,2 ✅ | ≥ 3 |
| R2 NQ +pp | 2,02 ✅ | 1,52 | 1,61 | 1,69 | 1,97 | 2,33 ✅ | ≥ 2 |
| F1 Fakten | 93 ✅ | 95 ✅ | 95 ✅ | 100 ✅ | 100 ✅ | 100 ✅ | ≥ 90 |
| F2 Tippfehler | 85 ✅ | 93,5 ✅ | 93 ✅ | 99,5 ✅ | 99 ✅ | 97,5 ✅ | ≥ 75 |
| F3 Enthaltung | 100 ✅ | 100 ✅ | 100 ✅ | 100 ✅ | 100 ✅ | 100 ✅ | ≥ 90 |
| D1 Dialogfakten | 93,2 ✅ | 92,1 ✅ | 38,1 | 67,9 | 86,5 | 77,0 | ≥ 90 |
| D2 Vergessen a/b | 76,5/75 | 96/90 | 97,5/47,5 | 100/87,5 | 89/85,5 | 96/85 | je 100 |
| D3 Pronomen | 85,5 ✅ | 100 ✅ | 90,9 ✅ | 100 ✅ | 100 ✅ | 100 ✅ | ≥ 80 |
| A1 EM/F1 | 18,8/25,3 | 19,8/26,7 | 20,9/26,7 | 18,5/25,3 | 16,6/23,3 | 19,2/26,6 | 20/30 |
| A2 Präz.@Abd. | 58,6@17,4 | 54,6@20,7 ✅ | 55,9@18,8 | 48,6@18,3 | 48,4@18,8 | 54,7@20,1 ✅ | 50@20 |
| A3 NQ EM | 1,9 | 1,3 | 1,7 | 1,7 | 1,8 | 1,9 | ≥ 5 |
| U1–U3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |

### Bilanz

- **Stufe 2 (HDC-Faktengedächtnis) und Stufe 5 (Oberfläche, Tempo, Determinismus)** sind in allen
  sechs Runden erfüllt. Der Vorsprung vor einem exakten Wörterbuch bei Tippfehlern beträgt
  85–99,5 pp. Das ist der klarste Nutzen von HDC in ENGRAMM.
- **Stufe 1.1** ist in 2 von 6 Runden erfüllt. R1 gelingt immer. R2 schwankt mit der Stichprobe
  um die 2-pp-Schwelle (+1,5 bis +2,3 pp), der Gewinn selbst ist in jeder Runde signifikant > 0.
- **Stufe 3:** D3 ist immer erfüllt. D1 und D2 hängen an der Formulierung, und jede neue
  Formulierungsrunde fand neue Lücken der Regel-Zerlegung (D1 frisch: 38 → 68 → 86,5 → 77 %).
  Das Vergessen selbst ist immer exakt, wenn der richtige Satz getroffen wird (U3, D2b bei
  richtiger Zuordnung). Die Schwierigkeit ist das Verstehen, *welcher* Satz gemeint ist.
  100 % auf beliebigen neuen Formulierungen erreicht ein handgeschriebenes Regelsystem nach
  diesen Messungen nicht.
- **Stufe 4:** A2 ist zweimal erfüllt, A1-EM liegt an der Schwelle (16,6–20,9 %). F1 ≥ 30 % und
  NQ-EM ≥ 5 % wurden nie erreicht. Das sind Grenzen der regel- und zählbasierten Antwortwahl
  sowie des Korpus (285 M Tokens: bei NQ steht die Antwort nur in ~30 % der Fälle überhaupt
  unter den Kandidaten).
- **Methodisch:** Jede Runde war vorregistriert. Der Code war vor dem Schreiben der
  Testformulierungen eingefroren, und jeder Testlauf lief genau einmal. Die Formulierungen
  schrieb dieselbe Instanz, die das System baute. Das ist ein bekanntes Risiko, das die
  schwankenden D1-Werte eher unterschätzt als überschätzt.

---

## E21 — ENGRAMM-Chat v8 (PREREG_CHAT_V8, einmaliger Testlauf)

Ergebnisdatei: `results/chat/chat_test8_container_20260927T134959Z.json`. Code eingefroren in
`2c4fb57`; Formulierungen danach geschrieben; ein Lauf.

| Kriterium | Wert | Schwelle | Ergebnis |
|---|---|---|---|
| R1 | +6,0 pp, KI [3,9; 8,2] | ≥ 3 pp, KI > 0 | erfüllt |
| R2 | +1,63 pp, KI [1,0; 2,2] | ≥ 2 pp, KI > 0 | verfehlt |
| F1 / F2 / F3 | 100 % / 99,5 % (exaktes Wörterbuch 0 %) / 100 % | 90 / 75 & +30 pp / 90 | erfüllt |
| D1 | 100 % | ≥ 90 % | erfüllt |
| D2 | 100 % (a), 100 % (b) | je 100 % | erfüllt |
| D3 | 100 % | ≥ 80 % | erfüllt |
| A1 | EM 22,7 %, F1 31,0 % | ≥ 20 % und ≥ 30 % | erfüllt |
| A2 | 48,1 % Präzision bei 23,3 % Abdeckung | ≥ 50 % bei ≥ 20 % | verfehlt |
| A3 | NQ-EM 2,5 % | ≥ 5 % | verfehlt |
| U2 / U3 | 9 ms / Transkripte gleich, Neustart gleich | ≤ 1 s / identisch | erfüllt |

**Stufen:** 2, 3 und 5 erfüllt; 1.1 und 4 verfehlt.

**Einordnung:**
- **Stufe 3** ist zum ersten Mal auf frischen Formulierungen erfüllt, in allen drei Kriterien
  zu 100 %. Die ehrliche Vorab-Schätzung (dev9, einmal gemessen vor Anpassung) lag bei
  D1 67,75 %. Die Testformulierungen dieser Runde waren offenbar näher an dem, was die
  breiteren Mechanismen abdecken:
  - gezähltes Lexikon,
  - weiche Kategorien aus Lift,
  - Punktesystem,
  - breitere Vergessen-Erkennung.

  Ein einzelner Lauf mit 200 Dialogen beweist keine allgemeine Robustheit.
- **A1** ist zum ersten Mal erfüllt, getragen vom Perzeptron (Dev F1 30,9 → Test 31,0).
- **A2** verfehlt um 1,9 pp Präzision: Die Konfidenz der neuen Spannenwahl trennt richtig und
  falsch auf dem Test etwas schlechter als auf Dev.
- **A3** bleibt korpusbegrenzt.
- **R2** schwankt wie bisher knapp unter 2 pp.

---

## E22 — ENGRAMM-Chat v9 (PREREG_CHAT_V9, einmaliger Testlauf)

Ergebnisdatei: `results/chat/chat_test9_container_20260927T183804Z.json`. Code eingefroren in
`1aae5ad`; Formulierungen danach geschrieben; ein Lauf.

| Kriterium | Wert | Schwelle | Ergebnis |
|---|---|---|---|
| R1 | +9,8 pp, KI [7,5; 12,1] | ≥ 3 pp, KI > 0 | erfüllt |
| R2 | +3,63 pp, KI [2,9; 4,3] | ≥ 2 pp, KI > 0 | erfüllt |
| F1 / F2 / F3 | 100 % / 97,5 % (exaktes Wörterbuch 0 %) / 100 % | 90 / 75 & +30 pp / 90 | erfüllt |
| D1 / D2 / D3 | 100 % / 100 % (a und b) / 100 % | 90 / 100 / 80 | erfüllt |
| A1 | EM 23,3 %, F1 30,9 % | ≥ 20 % und ≥ 30 % | erfüllt |
| A2 | 50,2 % Präzision bei 21,1 % Abdeckung | ≥ 50 % bei ≥ 20 % | erfüllt |
| A3 | NQ-EM 3,4 % | ≥ 5 % | verfehlt |
| U2 / U3 | 9 ms / Transkripte gleich, Neustart gleich | ≤ 1 s / identisch | erfüllt |

**Stufen:** 1.1, 2, 3 und 5 erfüllt. Stufe 4 ist verfehlt, allein wegen A3.

**Einordnung:**
- **Stufe 1.1** ist erfüllt, weil der gezeigte beste Satz jetzt der Antwortsatz ist. Das ist eine
  Änderung dessen, *welchen* Satz ENGRAMM zeigt, nicht der Messung. Sie ist in PREREG_CHAT_V9
  offen registriert.
- **A1 und A2** sind knapp erfüllt: F1 um 0,9 pp über der Schwelle, Präzision um 0,2 pp. In einer
  weiteren Runde kann jedes der beiden auch knapp verfehlt werden.
- **Stufe 3** ist die zweite Runde in Folge mit 100 % auf frischen Formulierungen.
- **A3 (NQ-EM ≥ 5 %)** ist nach neun Runden nie erreicht (1,3 → 3,4 %). Die Obergrenze:
  - Bei NQ steht die Goldantwort nur bei 12,7 % der Fragen in den 10 besten Sätzen und bei 30 %
    überhaupt unter den Kandidaten.
  - 5 % EM verlangten also, bei 40 % der verfügbaren Fälle genau die richtige Spanne zu wählen.
    Bei SQuAD gelingt das bei 37 %, bei NQ bei 26 %.

  Mit 285 M Tokens Korpus und zählbasierter Spannenwahl ist das nach diesen Messungen nicht
  erreichbar. Ein größerer Korpus (ganze Wikipedia) wäre der naheliegende nächste Hebel.

---

## E23 — ENGRAMM-Chat v10 mit Wikipedia-Lesekorpus (PREREG_CHAT_V10, einmaliger Testlauf)

Ergebnisdatei: `results/chat/chat_test10_container_20260928T023046Z.json`. Code eingefroren in
`2abf2b1`; ein Lauf.

**Abweichung von der Registrierung:** SQuAD-Test10 umfasste nur **521** statt 1.000 Fragen. Der
Pool der Test-Artikel hat 8.521 Fragen, Positionen 8.000–8.999 reichen also nur bis 8.520. Das
wurde vor dem Lauf nicht bemerkt. Der Standardfehler von A1/A2 ist dadurch etwa 1,4-mal so groß.
Damit ist der SQuAD-Pool der Test-Artikel vollständig verbraucht.

| Kriterium | Wert | Schwelle | Ergebnis |
|---|---|---|---|
| R1 | +7,1 pp, KI [3,5; 10,9] | ≥ 3 pp, KI > 0 | erfüllt |
| R2 | +7,1 pp, KI [6,2; 8,1] | ≥ 2 pp, KI > 0 | erfüllt |
| F1 / F2 / F3 | 100 % / 99,0 % / 100 % | | erfüllt |
| D1 / D2 / D3 | 100 % / 100 % / 100 % | | erfüllt |
| A1 | EM 18,4 %, F1 28,2 % | ≥ 20 % und ≥ 30 % | verfehlt |
| A2 | 47,2 % Präzision bei 20,3 % Abdeckung | ≥ 50 % bei ≥ 20 % | verfehlt |
| A3 | NQ-EM 5,2 % | ≥ 5 % | **erfüllt** (erstmals) |
| U2 / U3 | 8 ms / identisch | | erfüllt |

**Stufen:** 1.1, 2, 3 und 5 erfüllt. Stufe 4 ist verfehlt, diesmal wegen A1 und A2.

**Einordnung:**
- **Mehr Lesen hilft offenen Fragen.** Mit 614.464 Wikipedia-Anfängen steigt NQ-EM von
  3,4 % (v9) auf 5,2 %, NQ-Hit@1 gegenüber Stufe 1 um +7,1 pp. Das bestätigt, dass A3 am Korpus
  hing.
- **SQuAD fiel unter die Schwelle.** F1 28,2 % liegt 2,4 pp unter dem Mittel der 9.000
  verbrauchten Fragen auf demselben System (30,6 %), also etwa 1,8 Standardfehler. A1 und A2
  hatten schon vorher nur 0,6 pp bzw. 0,9 pp Abstand im Mittel; eine schwächere Stichprobe kippt
  sie.
- **Bilanz über v8–v10:** Jedes Kriterium ist in mindestens einer Runde erfüllt, aber nicht alle
  in derselben. Für A1 und A2 fehlt der Abstand zur Schwelle, nicht die Fähigkeit.


## E24 — ENGRAMM-Chat v11: v10 auf größerer Stichprobe (PREREG_CHAT_V11, einmaliger Testlauf)

Ergebnisdatei: `results/chat/chat_test11_container_20260928T045756Z.json`. Das System ist
unverändert gegenüber v10 (`2abf2b1`); Registrierung `6970c7c`; ein Lauf. U1 (Browser-Test)
danach auf demselben Stand bestanden.

**Vorbehalt (registriert):** Die 4.956 SQuAD-Fragen stammen aus den 46 Dev-Artikeln. Die Fragen
selbst waren ungesehen, andere Fragen derselben Artikel dienten aber der Entwicklung.

| Kriterium | Wert | Schwelle | Ergebnis |
|---|---|---|---|
| R1 | +8,2 pp, KI [7,1; 9,4] | ≥ 3 pp, KI > 0 | erfüllt |
| R2 | +7,5 pp, KI [6,6; 8,4] | ≥ 2 pp, KI > 0 | erfüllt |
| F1 / F2 / F3 | 100 % / 97,5 % / 100 % | | erfüllt |
| D1 / D2 / D3 | 100 % / 100 % / 100 % | | erfüllt |
| A1 | EM 22,5 % (KI [21,3; 23,6]), **F1 29,95 %** | ≥ 20 % und ≥ 30 % | **verfehlt** (F1 um 0,05 pp) |
| A2 | 51,2 % Präzision bei 21,5 % Abdeckung | ≥ 50 % bei ≥ 20 % | erfüllt |
| A3 | NQ-EM 6,0 %, KI [5,2; 6,7] | ≥ 5 % | erfüllt |
| U1 / U2 / U3 | bestanden / 766 ms / identisch | | erfüllt |

**Stufen:** 1.1, 2, 3 und 5 erfüllt. Stufe 4 ist verfehlt, allein wegen A1-F1.

**Einordnung:**
- **A3 hält auf der Wiederholung.** NQ-EM 6,0 % entspricht dem Dev-Wert; die untere KI-Grenze
  liegt über 5 %.
- **A2 ist diesmal erfüllt**, knapp: 51,2 % bei 21,5 % Abdeckung.
- **A1-F1 fehlt um 0,05 pp.** Die Schwelle steht fest und wird nicht gerundet. Der Befund zeigt
  aber, dass das System genau auf der F1-Schwelle liegt, nicht darunter oder darüber. Ohne mehr
  Abstand bleibt A1 ein Münzwurf.
- **Folgerung:** Die nächste Runde braucht einen echten F1-Zuwachs bei den Spannengrenzen, nicht
  eine weitere Wiederholung.


## E25 — ENGRAMM-Chat v12: SQuAD-Absätze gelesen, neue Konfidenz (PREREG_CHAT_V12, einmaliger Testlauf)

Ergebnisdatei: `results/chat/chat_test12_container_20260928T160955Z.json`. Code eingefroren in
`9c2c482`, Registrierung `d1c7894`; ein Lauf. U1 (Browser-Test) danach auf demselben Stand
bestanden.

| Kriterium | Wert | Schwelle | Ergebnis |
|---|---|---|---|
| R1 | +42,2 pp (46,4 % gegen 4,2 %) | ≥ 3 pp, KI > 0 | erfüllt (trivial, siehe Vorbehalt) |
| R2 | +6,8 pp, KI [5,9; 7,7] | ≥ 2 pp, KI > 0 | erfüllt |
| F1 / F2 / F3 | 100 % / 99,0 % / 100 % | | erfüllt |
| D1 / D2 / D3 | 100 % / 100 % / 100 % | | erfüllt |
| A1 | EM 22,7 % (KI [21,6; 23,8]), F1 30,6 % | ≥ 20 % und ≥ 30 % | **erfüllt** |
| A2 | 57,8 % Präzision bei **18,2 %** Abdeckung | ≥ 50 % bei ≥ 20 % | **verfehlt** (Abdeckung) |
| A3 | NQ-EM 5,2 %, KI [4,5; 6,0] | ≥ 5 % | erfüllt |
| U1 / U2 / U3 | bestanden / 953 ms / identisch | | erfüllt |

**Stufen:** 1.1, 2, 3 und 5 erfüllt. Stufe 4 ist verfehlt, allein wegen der A2-Abdeckung.

**Einordnung:**
- **A1 erstmals mit Abstand und zusammen mit A3.** F1 30,6 % liegt aber 1,8 pp unter Dev12 (32,4 %).
  Die Test-Artikel sind schwerer als die Dev-Artikel; auf den verbrauchten Test-Artikel-Fragen lag F1
  bei 30,7 %.
- **A2 kippt diesmal zur anderen Seite.** θ kam aus Dev12 (Abdeckung dort 23,6 %). Auf den Test-Artikeln
  ist die Konfidenz niedriger: Die Präzision hat 7,8 pp Luft, die Abdeckung fehlt 1,8 pp. Das Problem
  ist die Übertragung von θ zwischen Artikelgruppen, nicht die Rangfolge.
- **U2 wird knapp.** Der Median stieg von 766 ms (v11) auf 953 ms.
- **R1** vergleicht mit Stufe 1 auf deren Korpus ohne die Test-Absätze. Die +42 pp messen das Lesen,
  nicht das Verfahren (registrierter Vorbehalt).


## E26 — ENGRAMM-Chat v13: gezählte Konfidenz (PREREG_CHAT_V13, einmaliger Testlauf)

Ergebnisdatei: `results/chat/chat_test13_container_20260928T190344Z.json`. Code eingefroren in
`08de49c`, Registrierung `697aba1`; ein Lauf. U1 danach bestanden.

| Kriterium | Wert | Schwelle | Ergebnis |
|---|---|---|---|
| R1 / R2 | +41,9 pp (trivial, s. Vorbehalt) / +6,9 pp, KI [6,0; 7,9] | | erfüllt |
| F1 / F2 / F3 | 100 % / 98,0 % / 100 % | | erfüllt |
| D1 / D2 | 100 % / 100 % | | erfüllt |
| D3 | **63,6 %** | ≥ 80 % | **verfehlt** |
| A1 | EM 21,6 %, **F1 29,4 %** | ≥ 20 % und ≥ 30 % | **verfehlt** |
| A2 | 52,7 % Präzision bei 23,6 % Abdeckung | ≥ 50 % bei ≥ 20 % | **erfüllt** |
| A3 | NQ-EM 6,5 %, KI [5,7; 7,3] | ≥ 5 % | erfüllt |
| U1 / U2 / U3 | bestanden / **202 ms** / identisch | | erfüllt |

**Stufen:** 1.1, 2 und 5 erfüllt. Stufe 3 wegen D3 verfehlt, Stufe 4 wegen A1-F1.

**Einordnung:**
- **A2 gelöst.** Die gezählte Konfidenz und θ aus der Testverteilung treffen die Vorhersage
  (Test12: 55,0 % bei 23,0 %; Test13: 52,7 % bei 23,6 %).
- **A1 liegt auf Test-Artikeln genau auf der Schwelle.** Test12 kam auf 30,6 %, Test13 auf 29,4 %, im
  Mittel 30,0 %. Das ist kein Pech mehr, sondern fehlender Abstand. Nötig ist ein echter F1-Zuwachs auf
  dieser Verteilung.
- **D3:** Alle 20 Fehler betreffen „Where was that one born?“. Die Regel löste „that one“ auf das
  Fragethema auf statt auf die letzte Antwort. Das ist eine Lücke der Pronomenregel („that person“
  wurde richtig behandelt).
- **U2** fiel nach der Tempo-Korrektur von 953 ms auf 202 ms.


## E27 — ENGRAMM-Chat v14: alle Kriterien erfüllt (PREREG_CHAT_V14, einmaliger Testlauf)

Ergebnisdatei: `results/chat/chat_test14_container_20260928T233724Z.json`. Code eingefroren in
`44c0bbc`, Registrierung `b13af02`. U1 (Browser-Test) danach auf demselben Stand bestanden.

**Abweichung beim Lauf:** Der erste Start wurde bei 3.000/5.000 SQuAD-Fragen vom Kernel beendet
(Speichermangel, Kernel-Log: 11 GB belegt, Grenze der Speichergruppe erreicht). Ursache waren
~3,8 GB eigener Zwischendateien im RAM-Speicher `/dev/shm`. Der Lauf hatte keine Kennzahl ausgegeben,
nur Fortschrittszeilen. Nach dem Entfernen dieser Zwischendateien wurde derselbe Lauf unverändert neu
gestartet. Er ist der einzige abgeschlossene Lauf.

| Kriterium | Wert | Schwelle | Ergebnis |
|---|---|---|---|
| R1 | +43,9 pp (48,2 % gegen 4,3 %; trivial, s. Vorbehalt) | ≥ 3 pp, KI > 0 | erfüllt |
| R2 | +8,5 pp, KI [7,6; 9,5] | ≥ 2 pp, KI > 0 | erfüllt |
| F1 / F2 / F3 | 100 % / 99,0 % (exaktes Wörterbuch 0 %) / 100 % | | erfüllt |
| D1 / D2 / D3 | 100 % / 100 % / **100 %** | | erfüllt |
| A1 | EM **24,2 %** (KI [23,0; 25,4]), F1 **31,8 %** | ≥ 20 % und ≥ 30 % | **erfüllt** |
| A2 | 56,7 % Präzision bei 22,7 % Abdeckung | ≥ 50 % bei ≥ 20 % | **erfüllt** |
| A3 | NQ-EM **7,7 %**, KI [6,9; 8,6] | ≥ 5 % | **erfüllt** |
| U1 / U2 / U3 | bestanden / 191 ms / identisch nach Neustart aus dem Log | | erfüllt |

**Stufen 1.1, 2, 3, 4 und 5 sind alle in derselben registrierten Runde erfüllt.**

**Einordnung:**
- **A1** hat erstmals Abstand zur Schwelle: F1 31,8 % gegen erwartete 30,7 ± 0,6. Beigetragen haben das
  Ensemble aus sieben gezählten Perzeptrons (Varianz der Spannenwahl sinkt) und pcov 4. Die Stichprobe
  lag zudem eher günstig.
- **A2** ist zum zweiten Mal in Folge erfüllt, seit θ aus der Testverteilung kommt und die Konfidenz
  gezählt wird.
- **A3** mit 7,7 % ist der beste NQ-Wert aller Runden.
- **D3** nach der Verallgemeinerung der Demonstrativa 100 %, auch auf den neuen Formulierungen
  („that individual“, „the latter“).
- **Vorbehalte (registriert):**
  - Die Test-Absätze wurden gelesen (Pool-Bedingung). R1 misst daher vor allem das Lesen.
  - Test14 stammt aus denselben Test-Artikeln wie die verbrauchten Test12/Test13, an denen pcov und θ
    bestimmt wurden. Auf keinem Test-Artikel wurde trainiert.
  - U2 ist ein Container-Wert. Offiziell wäre das M4.

---

## E28 — Chat v3: Lite-Wissenspaket und Desktop-Server gemessen (Container, ohne Schwelle)

Stand 2026-09-30.

**Charakter der Messung:** Es gibt keine vorab registrierte Schwelle, daher ist das kein Kriterium. Das Paket und die App wurden erst in dieser Sitzung gebaut. Die Zahlen sind Container-Werte (`canonical: false`), gemessen mit dem eingefrorenen Server (PyInstaller-Sidecar) auf dem Paket, so wie die Desktop-App ihn startet.

**Inhalt des Lite-Pakets** (`experiments/pack_build.py --name lite --abstracts … --top 400000`):

| Teil | Quelle / Werkzeug | Umfang |
|---|---|---|
| Lesetext | Artikelanfänge aus DBpedia 2022.12 (`reading_abstracts.py`), sortiert nach Verweisen + Weiterleitungen | 400.000 Artikel, 2,06 Mio. Sätze |
| Faktenbank | `kb_slim.py` aus DBpedia + Wikidata | 150.000 Entitäten, 1,40 Mio. Fakten, 0,97 Mio. Namen |
| Wörterbuch | `spell_build.py` | ca. 140.000 Wörter |
| Übrige Dateien | Modelle (Codebuch, Spannen-Perzeptrons, Kalibrierer), Tokenizer | – |
| **Paketgröße** | Summe laut `manifest.json` | **722 MB** |

**Messwerte:**

| Größe | Wert | Ziel laut Plan |
|---|---|---|
| Paketgröße Lite | 722 MB | ≈ 0,7 GB |
| Programm (Server eingefroren, ein Ordner) | 275 MB unkomprimiert, davon llvmlite 171 MB | Rust-Laufzeit 10–30 MB (Phase 3/7, offen) |
| Start bis „bereit“ | 2,2 s | ≤ 15 s |
| RAM-Spitze nach dem Laden (VmHWM) | 453 MB (anonym 362 MB) | – |
| RAM-Spitze nach 15 Gesprächszügen | **677 MB** (anonym 401 MB) | ≤ 650 MB für ENGRAMM; Messlatte ≤ 1,5 GB gesamt |
| Zeit je Zug (Team-Prompts, 156 Züge) | Median 0,5 ms, p95 40 ms | Median ≤ 0,5 s |

**Team-Prompts** (`data/chatbench/dev_team.jsonl`, nur Entwicklung, `results/chatbench/`):
- 29 Faktenantworten, alle mit Quelle.
- 14 von 156 Zügen enden mit „weiß ich nicht“.
- Unsichere Vermutungen werden nicht mehr als Antwort ausgegeben. Auf dev waren sie nur 7 von 25 Mal richtig.

**Einordnung:**
- Das **RAM-Ziel ≤ 650 MB** reißt der Server knapp: 677 MB. Die Messlatte ≤ 1,5 GB gesamt hält er deutlich.
- **Der größte Posten ist das Python-Programm selbst** (llvmlite/numba). Der Rust-Kern müsste Suche und Extraktion übernehmen, um Programm und RAM zu halbieren.
- **Offen:** Messung auf W-LOW-1/2 und der 4-GB-VM. Der Container sagt über alte Zweikern-PCs nichts Verbindliches.

**Nachtrag (derselbe Tag): Speicher-Diät.**
- **Änderungen:** Die Gewichte der Spannen-Perzeptrons liegen als sortierte 64-Bit-Hashes mit Gewichten in numpy statt als Python-Dict (`CompactWeights`). Die Dokumentschlüssel liegen als ein Titelpuffer mit Offsets statt als 400.000 Tupel (`DocKeys`).
- **Antworten unverändert:** Auf allen 128 Team-Prompts sind die Antworten bit-identisch.
- **Neu gemessen** (Python-Server, Container, parallel lief ein Trainingslauf):

| Größe | Wert | Ziel |
|---|---|---|
| RAM-Spitze nach dem Laden | 377 MB (anonym 245 MB) | – |
| RAM-Spitze nach 15 Zügen | **534 MB** (anonym 261 MB) | ≤ 650 MB → **erreicht** |
| Start | 4,0 s | ≤ 15 s |

**Installer (CI-Lauf 14, `.github/workflows/desktop.yml`, alle vier Builds grün, unsigniert):**

| Plattform | Artefakt (gepackt, inkl. aller Formate) |
|---|---|
| macOS Apple Silicon (.dmg) | 72 MB |
| macOS Intel (.dmg) | 64 MB |
| Windows (.msi + .exe) | 130 MB |
| Linux (.deb + .rpm) | 242 MB |

Jeder Build hat den Smoke-Test des eingefrorenen Servers und die Rust-Tests der App bestanden. Download: ≤ 2 GB gesamt mit dem Lite-Paket (Installer ≤ 130 MB + Paket 727 MB).

Nach E29 kam der Absichts-Klassifikator ins Paket (`nlp/intent.json`, 4,3 MB, für Gerätebefehle). Das Lite-Paket misst seitdem **726,5 MB**.

---

## E29 — Chat v3, Phase 2: Sprachgrundlagen v0 (PREREG_NLP_V0, einmaliger Testlauf)

- **Ergebnisdatei:** `results/nlp/nlp_v0_test.json`.
- **Stand des Codes:** `2cf7a10`, Registrierung mit Nachtrag 2. Parser lab+x+more, Goldpfad-Start, 8 Epochen.
- **Umfang:** Genau ein Lauf auf den Testteilen (UD English EWT r2.14 `test`, MASSIVE 1.1 en-US `test`). Container, 2.336 s.

| Kriterium | Wert | Schwelle | Ergebnis |
|---|---|---|---|
| N1 Wortarten (UPOS) | **94,90 %** | ≥ 94,0 % | erfüllt |
| N2 Satzbau (UAS, vorhergesagte Wortarten) | **85,36 %** (LAS 82,31 %) | ≥ 84,0 % | erfüllt |
| N3 Absichten (Makro-F1, 60 Absichten) | **0,778** (Genauigkeit 82,1 %) | ≥ 0,80 | **verfehlt** |
| N4 Tempo (Tagger + XPOS + Parser + Absicht) | 13,4 ms Median | ≤ 50 ms | erfüllt (Container-Kandidat) |

Modellgrößen: pos 8,2 MB, xpos 8,7 MB, parse 90,9 MB, intent 4,3 MB (JSON).

**Einordnung:**
- **N1 und N2 halten mit Abstand.** Auf dev lagen sie bei 94,85 % und 84,72 %; der Test fällt jeweils etwas besser aus.
- **N3 verfehlt die Schwelle um 0,022.** Auf dev lag der Wert bei 0,826.
  - Erwartet war vorab eine Chance von ~80 %.
  - Das lineare Modell (Wörter, Wortpaare, Buchstaben-Trigramme) generalisiert auf seltene Absichten schlechter als auf dev. Makro-F1 gewichtet die 60 Absichten gleich, darunter mehrere mit unter 30 Trainingsbeispielen. Die Genauigkeit liegt bei 82,1 %.
  - **Folge für das Produkt:** Die Absichten dienen nur der Erkennung von Gerätebefehlen (`engramm/chat/device.py`). Dort greift eine hohe Abstandsschwelle von 25; auf dev stimmte die Gruppe dann in ~95 % der Fälle.
  - **Neue Runde nötig:** Eine Verbesserung (z. B. Wortklassen aus dem HDC-Codebuch, mehr Epochen, Gewichtung seltener Absichten) braucht eine neue Registrierung und frische Testdaten. MASSIVE-test ist verbraucht.
- **Parser-Größe:** 91 MB JSON ist für das Lite-Paket zu groß. Er wird erst ausgeliefert, wenn ihn eine Laufzeit-Funktion nutzt; heute nutzt die Gesprächsschicht nur Tagger-freie Regeln und die Absichten.

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

---

## E30 — Atlas (v3.1): Entwicklungsmessungen an echtem Regal und Lite-Paket (ohne Schwelle)

**Eingetragen 2026-10-02.** Entwicklung auf verbrauchten Daten, keine Testmessung; die registrierte
Prüfung ist `docs/PREREG_SEARCH_V0.md`. Container-Werte, nicht kanonisch.

- **Regal aus Shard 0** des CirrusSearch-Dumps 2026-09-27: 292.378 Seiten → 96.211 Artikel (≥ 300 Zeichen
  nach Abschneiden der Literaturzone; die Zone macht 31 % des Textes aus). Extraktion 232 s (ein Kern),
  Bau 150 s (4 Worker), 112 Fächer à 1 MiB, 0,10 GB, Index (Format 2) 11,7 MB.
  Hochrechnung auf 66 Shards (Untergrenze): ≈ 6,3 Mio. Artikel, ≈ 6,6 GB Volumes, Index ≈ 0,55–0,67 GB.
- **Konfidenzmodell für Netz-Sätze** (`experiments/atlas_calib.py`): 11.046 SQuAD-train-Fragen über 442
  Artikel (heutige Fassung) unter 96.648 Ablenkern. Gefragter Artikel unter den Kandidaten: 41 %
  (88 % bei Fragen, die ihren Artikel nennen). Das lokale Modell: 59,7 % exakte Präzision auf Regal-Sätzen.
  Neues Modell (Label Token-F1 ≥ 0,5), θ = 13,45: 22/24 kurze Antworten richtig auf zurückgehaltenen
  Artikeln (91,7 %, Abdeckung 1,1 %).
- **Ende-zu-Ende-Batterie** (12 Fragen zu Artikeln aus Shard 0, die das Lite-Paket nicht hat): vorher
  5 richtig, 2 falsch; nachher 2 sichere Kurzantworten, 7 belegte Zitate, 1 aus der Faktenbank,
  2 ehrlich unbeantwortet, **0 falsch**. Kein Abruf enthielt Fragetext.
- **Alltags-Batterien** (4 Gespräche, 181 Antworten, Lite-Paket): 0 wortgleiche Wiederholungen (vorher 4).
- **Ganzes Regal** (`shelf-20260927`, CI-Lauf vom 2026-10-02): 6.369.076 Artikel in 7.425 Fächern,
  9,7 GB Volumes, Index 0,53 GB (Lite) / 0,63 GB (voll). Hochrechnung aus Shard 0 lag bei 6,3 Mio. Artikeln,
  6,6 GB Volumes (Untergrenze; Volumes größer, weil Fächer bis zur festen Größe aufgefüllt werden).
- **Ende-zu-Ende mit dem echten Regal** (Lite-Paket + Regal-Index, direkt ohne Tor): die erste Fassung gab
  falsche Antworten („West Indies won the world cup 2022“ aus dem T20-Artikel, „Golden Ball was the top
  scorer“). Nach Themenprüfung, Siegerregeln und Belegabdeckung: 8 Siegerfragen (WM 2014/2018/2022,
  Euro 2016/2024, Rugby-WM 2023, Tour de France 2024, WM 2010) → 6 richtig, 2 ehrlich ohne Antwort, 0 falsch;
  JWST-Start „25 December 2021“ richtig; Super Bowl 2024 als belegtes Zitat (Chiefs).
- **NQ-open Dev, 400 Fragen, Lite offline** (Wirkung der Plausibilitäts- und Abdeckungsprüfungen):
  vorher (Stand 7c7e8db) 29 beantwortet, 8 richtig (27,6 %); nachher 21 beantwortet, 8 richtig (38,1 %).
  Gleich viele richtige, 8 falsche weniger. Abgleich: normalisierte Teilzeichenkette gegen die Goldantworten.
- **Alltags-Batterien 7–14** (Slang, Gefühle, Gedächtnis, Deutsch, Reisen, Hobbys): je Batterie die
  gefundenen Fehler behoben und als Tests festgehalten; Regressions-Batterien 1–6: 240 Antworten,
  0 wortgleiche Wiederholungen. Team-Dev-Satz (128 Dialoge): eine Antwort geändert (vage → ehrlich).
- **Alltags-Batterien 20–29** (2. Oktober 2026; Krise, Unhöflichkeit, Kochen, Reise, Superlative, Deutsch,
  Korrekturen, Emojis, Haustiere, lange Abendunterhaltung mit 29 Zügen): je Batterie die gefundenen Fehler
  behoben und als Tests festgehalten (Suite 670 bestanden, 7 übersprungen). Schwere Fehler, die gefunden und
  behoben wurden:
  - passive Suizidgedanken („don't want to be here anymore“) wurden gespeichert statt mit Krisenhilfe beantwortet;
  - „Bhutan is the tallest mountain“ (Textsuche) → jetzt aus der Faktenbank „Mount Everest … 8,849 m“;
  - „You live in Leonardo da Vinci“ nach einer Korrektur;
  - „George Challis wrote faust“ → „Johann Wolfgang von Goethe“;
  - „I'll remember that you work as a studying“.
  In den Wiederholungsläufen jeder Batterie: 0 wortgleiche Wiederholungen. Gezählt sind nur Wiederholungen
  ohne Bitte; „say that again“ ist ausgenommen und beginnt jetzt mit „Sure — …“.
- **NQ-open Dev, 400 Fragen** (Stand 98e4e1c, nach der notableWork-Rückwärtssuche): 22 beantwortet,
  9 richtig (40,9 %); vorher 21/8. Team-Dev-Satz: 3 von 128 Antworten geändert, alle besser (Entschuldigung
  erkannt, zweimal kein unpassender „closest article“-Titel mehr).
- **Pakete gemessen** (Release-Lauf 36953606047): Lite ≈ 1,25 GB, Standard 2,73 GB (Schwelle ≤ 4,5 GB eingehalten).
- **Alltagsfakten-Tabelle** (`daily.common`, 24 von Hand geprüfte Einträge: Kontinente, Siedepunkt, Tomate,
  Glühbirne …), weil die Textsuche genau diese falsch beantwortete („two continents“, „grease“, „Sweet“,
  „Robert Williams Wood invented the light bulb“). **Achtung:** 3 Einträge decken Fragen des Team-Dev-Satzes ab
  (team-0080, -0081, -0099); Dev-Ergebnisse nach diesem Stand sind daher optimistischer und kein Maß für
  ungesehene Fragen. Die versiegelten Testsätze (ChatBench-Test, SearchBench) wurden nicht angesehen.
  Zusätzlich: Ja/Nein-Fragen bekommen keine herausgeschnittene Kurzantwort mehr, und Maß-/Anzahlfragen
  ohne Zahl in der Antwort gelten als unbeantwortet. NQ-open 400: unverändert 22/9.
- **Alltags-Batterie 34** (Job, Mondlandung, Langeweile, Deutsch mit Müdigkeit/Schlaf). Gefunden und behoben:
  - „who was the first man on the moon“ → „A Kid Named Cudi“ (Textsuche). Jetzt kommt „Neil Armstrong …“ aus der
    Alltagsfakten-Tabelle (+5 Raumfahrt-Einträge, 29 gesamt), und „how old was he then“ → 38.
    **Achtung:** Der Mond-Eintrag deckt team-0079 ab, damit überschneiden sich jetzt 4 Dev-Fragen (0079, 0080, 0081, 0099).
  - „You work for Frankfurt“ nach „I work at a bank in Frankfurt“: Arbeitgeber-Antworten nutzen jetzt den eigenen
    Satz („You work at a bank in Frankfurt.“).
  - „You work as Monday“ / „You work as a new“: Ein Wochentag/Datum ist nie der Beruf, ein Adjektiv allein nie
    ein Wert.
  - Details nach „I got a new job“ („its at …“, „i start next monday“) werden gemerkt.
  - Kleinere Fälle: „anyway what should i eat“, „thanks thats helpful“, „cool, tschüss“, „bin nur müde“ →
    Schlaftipps auf „ja bitte“.
  - Team-Dev-Satz: 2 von 128 Antworten geändert, beide besser (team-0050 „Your dentist appointment is on Friday.“,
    team-0079). NQ-open 400: unverändert 22/9. Suite 676 bestanden, 7 übersprungen.
- **Alltags-Batterie 35** (Morgen mit Zahnarzttermin, Trennung, Buchtipps, Pfannkuchen, Deutsch mit Vorlieben,
  Präsident/Bevölkerung). Gefunden und behoben:
  - „i have a dentist appointment at 3“ → „you work as a dentist“: Ein Wort vor einem Kopfnomen (appointment, lesson,
    exam …) ist nie der Wert, und „at 3“ ist eine Uhrzeit. Jetzt gilt: Termin gemerkt, „when is my dentist
    appointment?“ → „You have a dentist appointment at 3.“, „any plans for me today?“ listet Termine und Notizen.
  - „how long do i cook them“ nach dem Pfannkuchen-Rezept → Beziehungsratschlag: Rückfragen zu einer Anleitung
    werden aus deren Schritten beantwortet („do i need yeast?“ → „This simple version doesn't use yeast …“).
  - Deutsch: „was ist dein lieblingsessen?“, „ich mag blau“, „welche farbe mag ich?“, „ich esse am liebsten …“
    (vorher „nichts gefunden“ bzw. nicht verstanden).
  - „what about a movie“ → „The answer is MTV VJ.“, „how about a walk“ → „fourth largest town“: Vorschläge und
    Nachfragen nach Empfehlungen sind jetzt keine Wissensfragen mehr.
  - „something like harry potter“ → als Vorliebe gespeichert: liefert jetzt ähnliche Bücher, und unbekannte Titel
    werden nachgefragt statt gespeichert.
  - „i slept great“ → „congratulations!“; „do you think she'll come back?“ → Artikeltitel;
    „what's it about?“ nach drei Vorschlägen → „Which one …?“; „3 eggs plus 2 eggs“ → „5 eggs.“
  - Offen und ehrlich so belassen: „who is the president of france“ (Faktenbank ohne Präsidenten, Stand 2022).
    Mit eingeschaltetem Internet beantwortet die Atlas-Frische-Stufe das.
  - Team-Dev-Satz: 0 von 128 Antworten geändert. NQ-open 400: unverändert 22/9. Regressions-Batterien 30–34:
    0 Wiederholungen. Suite 678 bestanden, 7 übersprungen.
- **Alltags-Batterie 36** (Slang, Ratschlag zu einer Freundin, Gitarre lernen, Deutsch mit Stress, 30. Geburtstag).
  Gefunden und behoben:
  - „its hard“ nach „i'm learning to play guitar“ → „Hi Hard, nice to meet you!“: Eine Namenskorrektur gilt nur
    direkt nach einer kurzen Namensnennung und nie für Wörter wie hard/tired/fine.
  - „my birthday was yesterday“ → „Your birthday is yesterday“: relative Tage werden zum Datum, mit Glückwunsch.
  - „im kinda hungry tbh“ → „Noted: hungry — yum!“: Zustände (hungry, tbh, kinda …) sind nie Werte; „idk maybe
    pizza“ danach → „Pizza sounds perfect!“.
  - Ratschlag-Gespräch: „didn't invite me“ zählt als negatives Erlebnis, „i feel left out“ bleibt bei der Person,
    „what if she gets mad“ (vorher „who's she?“) und „ok ill try“ (vorher Wissenssuche).
  - Lernen (Gitarre, Klavier, Schlagzeug, Geige, Ukulele, Sprachen): Rückfragen zu Schmerzen, Dauer, Liedern, Tipps.
  - „i'm tom“ klein geschrieben wird über die Großschreib-Statistik des Pakets als Name erkannt (vorher „Tom — good
    choice!“).
  - Außerdem: „brb gotta grab smth“, „i just turned 30“, „yeah feels weird“, „danke dir, bis morgen“ (beides),
    „are you always right?“ beginnt nicht mehr mit „Plenty!“.
  - Team-Dev-Satz: 1 von 128 Antworten geändert (team-0040, Geburtstag heute: jetzt mit gemerktem Datum).
    NQ-open 400: unverändert 22/9. Suite 679 bestanden, 7 übersprungen.
- **Alltags-Batterie 37** (Chat-Schreibweise, E-Mail an den Vermieter, Paris-Reise, Beförderung, Deutsch vor einer
  Präsentation, Uhrzeit weltweit). Gefunden und behoben:
  - „any food i should try?“ → „Your favourite food is heating.“: „the heating is broken“ war als Lieblingsessen
    gespeichert. Ein beschriebenes Subjekt („the X is broken“) ist nie ein Wert; Essensfragen auf Reisen nutzen die
    Küche des Landes (Stadt → Land über die Faktenbank).
  - „how r u doin“ (Wissenssuche), „im gud thx“, „helo“: gesprochene Schreibweisen ergänzt.
  - „can u help me write an email“: fragt jetzt nach Empfänger und Anliegen; „to my landlord, the heating is broken“
    ergibt die passende E-Mail (vorher sofort eine leere Vorlage, danach Mitgefühl statt E-Mail).
  - „what should i see there?“: von Hand geprüfte Sehenswürdigkeiten für 44 Städte und 9 Länder, mit Angebot für
    Essenstipps („yes“ → Küche).
  - „thanks! i worked so hard for it“ nach einer Beförderung → „Oh no …“: jetzt Stolz. „any restaurant ideas?“ /
    „something fancy“ → Ideen für ein festliches Essen.
  - „that answer was wrong“ → „Mm-hm“: jetzt Bitte um die richtige Antwort. Eine „Korrektur“ einer belegten Antwort
    („it's sydney“ nach Canberra) wird höflich angezweifelt und nur auf „yes“ gespeichert.
  - Uhrzeit weltweit ohne Zeitzonen-Datenbank (`engramm/chat/worldtime.py`: Versatz plus Sommerzeit-Regeln EU, USA/Kanada,
    Australien, Neuseeland; ≈ 150 Orte, auch deutsch: „wie spät ist es in Tokio?“), mit Nachfragen („and in new york?“).
  - Übersetzungs-Nachfragen („and good morning?“, „what about goodbye“ → vorher „The answer is Mother.“).
  - Team-Dev-Satz: 0 von 128 Antworten geändert. NQ-open 400: unverändert 22/9. Regressions-Batterien 30, 33–36:
    0 Wiederholungen. Suite 682 bestanden, 7 übersprungen.
- **Alltags-Batterie 38** (langer Montag mit Aufgaben, Mittagessen, Besuch der Schwester; deutscher Feierabend;
  Eiffelturm; Krankheitstag). Gefunden und behoben:
  - „laundry, groceries, call my mom and finish a report“ → „Groceries — what a nice name! I'll remember your mother.“:
    „i have so much to do today“ bietet jetzt an, die Aufgaben zu ordnen; die Liste wird sortiert (Arbeit zuerst,
    „call your mom“), „which first?“ beantwortet.
  - „what helps with a sore throat“ → „The answer is streptococcal infection.“: Anleitungen für Halsweh, Kopfweh,
    Erkältung, Husten und Fieber (mit Arztschwelle); „should i go to work?“ beim Kranksein; „i'll make some tea“
    wird nicht mehr als Lieblingsgetränk gespeichert.
  - „her name is lena“ nach „my sister …“ wurde nicht gespeichert: Name und Vorlieben („she loves art“) gehen an die
    zuletzt genannte Person; „what does my sister love?“ (klarer Vorsprung unter den Fakten einer Person genügt).
    „she loves art“ nach Ideen → passende Idee (Museum/Galerie).
  - „ok thanks. what should i make for lunch“ (Dank + Frage) → Ideen „for lunch“; „i have eggs and spinach“ → Gericht
    aus den Zutaten (19 von Hand geschriebene Kombinationen).
  - Deutsch: „endlich feierabend“, „war ein langer tag“ (ohne „ich“), „danke! was kann ich heute abend noch machen?“,
    „eher was ruhiges“, „gute idee, mach ich“ (vorher unverstanden, einmal wortgleich wiederholt).
  - „is it worth visiting?“ nach dem Eiffelturm; „ugh mondays“.
  - Team-Dev-Satz: 0 von 128 Antworten geändert. NQ-open 400: unverändert 22/9. Regressions-Batterien 34–37:
    0 Wiederholungen. Suite 683 bestanden, 7 übersprungen.
- **Alltags-Batterie 39** (Umzug nach Berlin, kranker Hund, Geldsorgen, deutsche Langeweile mit Witzen, Rechnen,
  durchgefallene Prüfung). Gefunden und behoben:
  - „i feel like a failure“ → „Got it, you like failure.“: „feel/look/sound like …“ ist nie eine Vorliebe; jetzt
    eine aufbauende Antwort, und „i'll try again next time“ → „That's the spirit!“ (vorher „enjoy!“).
  - „haha ok, was ist die hauptstadt von kanada?“ → „Das klingt richtig gut!“: eine Reaktion vor der Frage wird
    abgetrennt, die Frage beantwortet.
  - Hund: „my dog is sick“ setzt den Haustier-Zusammenhang („his name is max“, „he's 7“, „how old is max?“), Rat zum
    Tierarzt.
  - „what's berlin famous for?“ / „what should i see there?“ nach dem Umzug, ohne die Liste zu wiederholen;
    „i don't know anyone here“ → Angebot, „yes“ → Tipps zum Freundefinden.
  - Geld: „rent is too expensive“ → Angebot mit Spartipps, Anleitungen „save money“ und „budget“ (vorher Artikel
    „Savemoney“). „is that hot?“ nach 30 °C → Einordnung.
  - Deutsch: „nein, keine ideen“ nach dem Angebot, „der war gut“ nach einem Witz.
  - Team-Dev-Satz: 0 von 128 Antworten geändert. NQ-open 400: unverändert 22/9. Regressions-Batterien 34–38:
    0 Wiederholungen. Suite 684 bestanden, 7 übersprungen.
- **Alltags-Batterie 40** (Krankenschwester Anna, Filmabend, Griechenland-Urlaub, deutsches Vorstellungsgespräch,
  Countdown, Abendessen für die Freundin). Gefunden und behoben:
  - „hi! i'm anna“ → Name nicht erkannt (das „!“); „danke, das hilft“ → unverstanden (die Dank-plus-Frage-Regel
    griff auch bei bloßen Reaktionen).
  - „can you recommend a movie for tonight“ → Wissenssuche; „something scary“ → nur ein Film (jetzt 6 Horror/Thriller).
  - „to greece“ auf „where are you going?“ → „What was the best part?“: jetzt Reiseziel mit Angebot; „what should i
    pack?“ (Packliste), „what language do they speak there?“ (Ort aus dem Gespräch), „and until new year?“.
  - „what should i cook next time?“ → gespeicherter Satz statt Ideen; „something romantic“ → romantische Gerichte;
    „i cooked dinner for my girlfriend“ / „i made lasagna“ mit passender Reaktion.
  - „what do you think about nurses?“ → „People are really split on nurses“: Respekt für Berufe, persönlich, wenn es
    der eigene ist; „yeah night shifts are tough“.
  - Team-Dev-Satz: 0 von 128 Antworten geändert. NQ-open 400: unverändert 22/9. Regressions-Batterien 35–39:
    0 Wiederholungen. Suite 685 bestanden, 7 übersprungen.
- **Langes Gespräch** (alle englischen Züge der Batterien 34–40 in *einer* Unterhaltung, 212 Züge): vorher 6 wortgleiche
  Wiederholungen. 5 davon waren Dankesantworten mit nur 6 Varianten, eine war ein wiederholter Artikelabsatz auf dieselbe
  Frage. Jetzt gibt es 16 Dankesvarianten; dieselbe längere Sachantwort kommt mit „Like I said earlier — …“ statt als
  Kopie. Ergebnis: **0 Wiederholungen**. Gefundene Kontextfehler:
  - „who is his wife“ nach dem Roman „Good Omens“ suchte „Good Omens's wife“. „he/his/she/her“ verweisen jetzt nur auf
    Personen (Werk/Ort/Organisation laut Faktenbank oder Artikelanfang → Rückfrage).
  - „how old is he“ nach „Obama's wife is Michelle“ → Michelle. Das Geschlecht aus dem Artikelanfang entscheidet jetzt
    zwischen letzter Antwort und genannter Person → Barack Obama, 65.
  - Team-Dev-Satz: 0 von 128 Antworten geändert. NQ-open 400: unverändert 22/9. Suite 687 bestanden, 7 übersprungen.
- **Alltags-Batterie 41 (Deutsch)** (Vorstellung, Trennung, Kochen, Eiffelturm, Geburtstag, Filmabend):
  - Vorher unverstanden, jetzt beantwortet: „ich hab morgen geburtstag“, „ich werde 30“, „hast du ideen?“ (zweimal →
    keine Wiederholung), „was mit nudeln“, „wie lange müssen nudeln kochen?“, „worum geht es in dem ersten?“. Neu sind
    8 deutsche Anleitungen (Nudeln, Reis, Eier, Pfannkuchen, Halsweh, Kopfweh, Erkältung, Schlaf).
  - Eiffelturm: „Eiffelturm ist …“ → „Der Eiffelturm ist …“. Folgefragen behalten den deutschen Namen (vorher „Eiffel
    Tower wurde …“), „wer hat ihn entworfen?“ wird aufgelöst (vorher Rückfrage), „wurde am 31. März 1889
    fertiggestellt“.
  - Trennung: eigene Antwort statt „das kommt dann noch dazu“; „wir waren 2 jahre zusammen“.
  - Wiederholungen 2 → 0. Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–40 und
    langes Gespräch: 0 Wiederholungen. Suite 695 bestanden, 7 übersprungen.
- **Alltags-Batterie 42 (Englisch)** (Langeweile, Beförderung, Wochenplanung, Schwester zu Besuch, Regen, Schlaflosigkeit,
  Fußball-WM, Name und Wohnort):
  - „its mike“ wurde nicht als Name erkannt (→ „Your name is Mike.“). „my mind keeps racing“ wurde als Fakt gespeichert
    („you drive a racing“); jetzt kommt eine Antwort auf das Gedankenkreisen. Aussagen der Form „my X keeps …ing“ sind nie Fakten.
  - Neu ist Kontext über mehrere Züge: Beförderung → Titel („Senior analyst — that's a real step up“); Woche planen
    (Termine je Wochentag gesammelt und angezeigt) → „how should I prepare?“ für die Präsentation; „she loves italian food“ →
    „what should I cook for her?“ mit drei italienischen Gerichten → „how do I make that?“ → Rezept; „what does anna
    like?“ → „Anna loves Italian food“. Kleidung bei Regen/Kälte/Hitze/Schnee kam vorher als Live-Daten-Absage.
  - Turniere nach Jahr (WM, Frauen-WM, EM, Olympia): Sieger aus dem eigenen Artikel oder aus „defending champions“ der
    Folge-Ausgabe, Austragungsort, Zeitraum, Folgefragen („and in 2018?“, „where was it held?“). Vorher 3× „weiß nicht“.
  - Amtsinhaber, wenn die Faktenbank keinen hat: aus dem Artikel des Amts, immer mit Datum der Lesetexte („As of my copy of
    Wikipedia (December 2022) …“), weil Ämter wechseln. Im langen Gespräch geht damit „president of france → how old is
    he → who is his wife“ durch (vorher dreimal unbeantwortet). Lebende Ehepartner: „is married to“ statt „was“.
  - Nachtrag: „who is the president of the united states?“ war zunächst offen (weder Faktenbank noch Artikelanfang des
    Amts nennen den Amtsinhaber). Jetzt sucht eine strenge Satzregel den Artikel des Amtsinhabers selbst („… is the 46th
    and current president of the United States“; nie „vice“, „deputy“ oder „former“), immer mit Stand der Lesetexte.
    Text-Antworten zu Ämtern können veraltet sein; das sagt die Antwort selbst. Dev-Satz 0/128 geändert, NQ 22/9,
    Suite 726 bestanden.
  - Wiederholungen 1 → 0. Team-Dev-Satz: 1 von 128 geändert (team-0074: Macron statt „weiß nicht“). NQ-open 400: 22/9.
    Regressionen 32, 38–41 und langes Gespräch: 0 Wiederholungen. Suite 702 bestanden, 7 übersprungen.
- **Alltags-Batterie 43 (Englisch, Umgangssprache)** (Small Talk mit „u/r/whatcha“, Umzug nach Berlin, kranker Hund,
  Rechnen und Trinkgeld, Prüfungsstress, Lieblingsgericht mit Korrektur, Mond und Mars, Einsamkeit):
  - Schwer: „ok whatever, tell me a joke“ wurde als Fakt gespeichert; jetzt kommt der Witz und danach „another one“.
    „actually no, it's risotto“ korrigiert jetzt das Lieblingsgericht (vorher blieb es Lasagne).
  - Kontext: „same lol“ nach „how are you“; „that's kinda sad“ über ENGRAMM selbst; „for work“ nach dem Umzug;
    Wohnviertel für 16 Städte; „best food there“ zur Stadt des Gesprächs; Symptome des kranken Hundes → Tierarzt-Rat;
    „ok ill call them“ → „I hope Bruno feels better soon“; Trinkgeld 15/18/20 %; Prüfungen: Anzahl → Fächer → „which
    first?“ → „I'm worst at physics“ → Plan; Einsamkeit im Homeoffice → Ideen → „that sounds nice“.
  - Wissen: „who was the first person on it?“ nach dem Mond (Pronomen in Alltagsfakten) und „when was that?“;
    Größe und Sonnenabstand der Planeten, von Sonne und Mond („cool, how big is mars?“ → „and how far is it from the sun?“).
  - Wiederholungen 2 → 0. Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–42 und langes
    Gespräch: 0 Wiederholungen. Suite 706 bestanden, 7 übersprungen.
- **Alltags-Batterie 44 (Deutsch)** (dieselben Alltagsthemen wie 42/43, auf Deutsch):
  - Vorher 5 Wiederholungen und 17 von 40 Zügen „Das verstehe ich leider nicht“. Umzug, kranker Hund, Prozent-Folgefrage,
    Tage bis Weihnachten, Korrektur des Lieblingsessens und WM-Fragen wurden gar nicht verstanden.
  - Jetzt: „ich ziehe nächsten Monat nach München“ → Grund → Viertel → Sehenswürdigkeiten → „und was isst man da?“
    (10 deutschsprachige und europäische Städte); Hund frisst nicht → „seit gestern“ → Name → Tierarzt → „ok ich ruf an“;
    „und 20 Prozent?“; „wie viele Tage bis Weihnachten?“ (24. Dezember, deutsche Zählung); „nein, eigentlich Lasagne“;
    „wer hat die WM 2014 gewonnen?“ → „Deutschland hat die WM 2014 gewonnen.“, „und 2018?“, „wo war die?“ (der englische
    Turnier-Leser mit deutschen Länder- und Turniernamen); Arbeitsstress und Druck vom Chef → konkrete Tipps;
    Einsamkeit im Homeoffice → Ideen; „bist du ein Mensch?“.
  - Wiederholungen 5 → 0. Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–43 und langes
    Gespräch: 0 Wiederholungen. Suite 708 bestanden, 7 übersprungen.
- **Alltags-Batterie 45 (Englisch, Gedächtnis und Folgefragen)** (Name und Beruf in einem Satz, Länderfakten, Buchliste,
  Vorstellungsgespräch mit Tippfehlern, Geburtstag, vegetarisches Essen, Everest, Trennung):
  - Schwer: „hey im lisa and i'm a nurse“ verlor den Namen (→ jetzt beides gemerkt); „who wrote the first one?“ nach einer
    Buchliste nannte den Autor einer Fernsehserie (→ „“Good Omens” was written by Terry Pratchett and Neil Gaiman“);
    „i hav a job interveiw tomorow“ → „you work as an interveiw“ (→ Tippfehler in Aussagen werden vor dem Merken
    korrigiert, nie bei Namen); „should i text him?“ → Live-Daten-Absage (→ ehrlicher Rat).
  - Folgefragen: „and its population?“ → Australien, „how about new zealand?“, „which one is bigger?“ (Fläche);
    „is it good?“ → das eben genannte Buch; Vorstellungsgespräch: Firma → Kleidung → Schwächen-Frage → Nervosität → Glück;
    „how many days until my birthday?“ und „how old will i be if i was born in 1995?“ aus dem gemerkten Geburtstag;
    „how long does it take?“ nach Rezeptideen; Everest: „has anyone climbed it?“ → „who was first?“; „what shifts do i work?“.
  - Werkzeug: `studio check` meldet jetzt Schlüssel, die in einer YAML-Datei doppelt vorkommen. Zweimal hatte ein neuer
    Abschnitt still einen alten überschrieben (einmal mit Wirkung auf team-0040; vor dem Commit bemerkt und behoben).
  - Wiederholungen 3 → 0. Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–44 und langes
    Gespräch: 0 Wiederholungen. Suite 712 bestanden, 7 übersprungen.
- **Alltags-Batterie 46 (Englisch und Deutsch: Kritik, Sarkasmus, Stimmung, Fähigkeiten)**:
  - Schwer: „i've been feeling really down lately“ wurde als Fakt gespeichert („Oh really? Tell me more“), jetzt kommt
    Anteilnahme, dann „nothing specific, just everything“ und „maybe talking helps“ im Zusammenhang. Sarkasmus („yeah sure,
    i love waking up at 6“) wurde als Vorliebe gemerkt („Waking — good choice!“), jetzt wird er erkannt.
  - „you didn't even understand me“, „can you help me with something?“ (vorher Wissenssuche ohne Treffer), „can you set
    an alarm?“ (ehrliche Grenze und Hinweis auf „remind me to …“), „ok what else?“ nach den Fähigkeiten.
  - Deutsch: „du verstehst gar nichts“, „sorry, war nicht so gemeint“, „kannst du mir helfen?“ (vorher 3× unverstanden);
    „wer ist der Präsident von Frankreich?“ → Amtsinhaber mit Stand der Lesetexte → „wie alt ist er?“ → „und wer ist seine
    Frau?“ (Possessivpronomen; „ist mit … verheiratet“ statt „ist bzw. war“); „ich hab nur Eier und Spinat“ → Rezeptidee →
    „wie lange dauert das?“.
  - Wiederholungen 1 → 0. Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–45 und langes
    Gespräch: 0 Wiederholungen. Suite 715 bestanden, 7 übersprungen.
- **Alltags-Batterie 47 (Reise, Wissensgespräche, deutscher Small Talk)**:
  - Reise: „im going to rome next week“ → „for 4 days“ → „what should i see?“ (vorher Kyoto/Reykjavík/Algarve!) →
    „is it expensive?“ (Preisniveau für 52 Ziele) → „do i need a visa as a german?“ (EU-Bürger ins EU-Land: nein; sonst
    ehrlicher Verweis auf das Auswärtige Amt) → „what language do they speak?“.
  - Alltagsfakten können jetzt eigene Folgefragen tragen (`follow`): Berliner Mauer → „why did it fall?“, „who was the
    chancellor then?“, „how long did it stand?“; „where is the painting now?“ nach der Mona Lisa (über die letzten Themen).
  - Katze anschaffen: kleine Wohnung → „is that ok?“ → „what do i need?“ → Namensideen; „how long does it take?“ beim
    Sprachenlernen (mit ehrlichem Zusatz je nach Sprache).
  - Deutsch: „geht so“ wurde als „gut“ verstanden („Freut mich!“), jetzt als durchwachsen; „zu viel im Kopf“ nach schlechtem
    Schlaf; „ich hab heute frei“ → „keine Ahnung was ich machen soll“ → „das Wetter ist schön“; „welche ist größer?“.
  - Team-Dev-Satz: 1 von 128 geändert (team-0078: die Antwort zur Berliner Mauer ist jetzt ein kurzer, direkter Satz
    mit demselben Datum statt des langen Artikelsatzes). NQ-open 400: 22/9. Regressionen 32, 38–46 und langes
    Gespräch: 0 Wiederholungen. Suite 717 bestanden, 7 übersprungen.
- **Alltags-Batterie 48 (Gesundheit, Geld, Arbeit, Geschenke, Entscheidungen; Englisch und Deutsch)**:
  - Schwer: „i didn't drink much water“ wurde zu „Your favourite food is drink“. Verneinte Vergangenheit („didn't“,
    „haven't“, „wasn't“) wird jetzt nie als Fakt gespeichert. „she likes reading and coffee“ war eine Smart-Home-Absage;
    Aussagen über andere Personen sind nie Gerätebefehle.
  - Kontext: Kopfschmerzen → seit wann → zu wenig getrunken → „should i take something?“ (Wasser, rezeptfreie
    Schmerzmittel, Warnzeichen für den Arzt); „i spend too much on food“ → konkrete Spartipps, „50/30/20“; Kollege
    schmückt sich mit fremder Arbeit → „again“ → Chef ansprechen → Formulierungsvorschlag; Geschenk nach Vorlieben
    („she likes reading and coffee“) mit Budget („under 30 euros“); zwei Jobangebote → Abwägung → „what would you do?“.
  - Deutsch: „ich hab Kopfschmerzen“ → „seit heute morgen“ → „soll ich was nehmen?“; „meine Freundin hat nächste Woche
    Geburtstag“ → „sie liest gern“ → „was soll ich ihr schenken?“ (vorher 7 von 8 Zügen unverstanden).
  - Platz: Die Root-Partition lief voll (ENOSPC mitten im Testlauf). Gelöscht wurden nur eigene Zwischenstände, dazu
    `git repack` (3.194 lose Objekte, 58 MB → Pack). Danach lief die volle Suite wieder durch.
  - Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–47 und langes Gespräch: 0 Wiederholungen.
    Suite 720 bestanden, 7 übersprungen.
- **Alltags-Batterie 49 (Laufen, Kind vor dem Test, Gäste, Erinnerungen; Englisch und Deutsch)**:
  - Laufen anfangen → Anfänger → wie oft → wie weit → welche Schuhe → „i'll start tomorrow“ (vorher 3× „weiß nicht“).
  - „my son has a math test tomorrow“ → „he's really nervous“ wurde als Angst des Nutzers gelesen („I'm sorry you're
    feeling anxious“), jetzt geht es um das Kind → „how can i help him?“ (vorher ein Beziehungsratschlag) → „he's 10“.
  - Gäste: Anzahl → „one is vegan“ → Menü, das alle essen können → Kochzeit → veganer Nachtisch.
  - Erinnerungen: „and to buy milk“ ergänzt die Liste; „i called her“ hakt „call your mom“ ab (Vergangenheitsform auf
    Grundform), die Liste zeigt danach nur noch „buy milk“.
  - Deutsch: „ich will mit dem Joggen anfangen“ → „wie oft?“ → „ich fang morgen an“; „wir kriegen heute Abend Besuch“ →
    „einer ist Vegetarier“ → „und als Nachtisch?“.
  - Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–48 und langes Gespräch: 0 Wiederholungen.
    Suite 722 bestanden, 7 übersprungen.
- **Alltags-Batterie 50 (ein langes, gemischtes Gespräch mit 25 Zügen)**: Feierabend, lange Woche, Wochenende,
  Wanderung, Oslo, Rechnen, Gedächtnis, Gute Nacht.
  - Vorher 8 schwache Züge: „its been a long week“ → „I see. Tell me more?“; „yeah, lots of deadlines“ → „Mm-hm“; „but
    tomorrow is friday“ → „Oh? Go on.“; „do you have any plans for the weekend?“ → Wissenssuche; Wandern: Reise- statt
    Wander-Packliste, „how much water?“ → Kleidungszeile; „is it expensive?“ nach Oslo → unbekannt; „nice. ok, random
    question: whats 18% of 250?“ → unbekannt; „you're a good listener“ → „Nice!“.
  - Jetzt passt jeder Zug. Dazu „and what do i do?“ direkt nach „what's my name?“ → Beruf (vorher Ratschlags-Rückfrage).
  - Wiederholungen 1 → 0. Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–49 und langes
    Gespräch: 0 Wiederholungen. Suite 723 bestanden, 7 übersprungen.
- **Alltags-Batterie 51 (dasselbe lange Gespräch auf Deutsch, 25 Züge)**:
  - Vorher 5 Wiederholungen und 9 schwache Züge. „ich bin tom“ war unverstanden, und die deutsche Mitgefühls-Nachfrage
    feuerte nach einer schlechten Nachricht bei jedem Satz („haha ok“, „ich geh vielleicht wandern“, sogar „hast du Pläne
    fürs Wochenende?“ → „Oh je, das kommt dann noch dazu“). Dazu fehlten Wandern, „ist es teuer?“, „wie heiße ich
    nochmal?“, „worüber haben wir geredet?“ und „du bist ein guter Zuhörer“.
  - Jetzt: Name aus „ich bin tom“ (nie bei „ich bin müde“, „fertig“, „gestresst“ …), Beruf aus „ich bin Designer“,
    die Nachfrage nur noch für echte Fortsetzungen (keine Fragen, Reaktionen oder Pläne), lange Woche → Deadlines →
    Freitag → Engramms Wochenende → Wandern (Tipps, Packliste, Wasser) → Oslo und Preise → Prozent → Name und Beruf →
    Rückblick auf Deutsch → Kompliment → Gute Nacht mit Namen.
  - Wiederholungen 5 → 0. Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–50 und langes
    Gespräch: 0 Wiederholungen. Suite 724 bestanden, 7 übersprungen.
- **Alltags-Batterie 52 (Robustheit)**: Emojis, dreimal dieselbe Eingabe, eine lange Pech-Geschichte, „ok“-Ketten,
  Unverständnis, Mischsprache, Zahlen, viermal „tell me a joke“.
  - Schon vorher gut: Emojis, Rechnen, Witze ohne Wiederholung, Rückfragen bei „what?“/„huh“.
  - Neu: Beim dritten gleichen Gruß, „how are you“ oder „ok“ in Folge sagt Engramm das, wie ein Mensch („You've said that
    a few times now 😄“); bei wiederholten Bitten (Witze) nie. „can we talk auf deutsch?“ wechselt auf Deutsch (vorher
    Wissenssuche). Eine reine Zahl („12345“) bekommt eine Rückfrage statt „Oh? Go on.“. Die lange Pech-Geschichte bekommt
    Mitgefühl für den ganzen Tag statt „What went wrong with your alarm?“.
  - Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–51 und langes Gespräch: 0 Wiederholungen.
    Suite 725 bestanden, 7 übersprungen.
- **Alltags-Batterie 53 (Alltagswissen: Wörter, Kalorien, Ernährung, Zeitzonen; Englisch und Deutsch)**:
  - Umrechnen und Synonyme klappten schon. Neu: Wortbedeutungen aus einer kleinen, von Hand geprüften Liste (25 Wörter)
    mit Beispielsatz und „use it in a sentence“; sonst ehrlich: kein Wörterbuch im Paket. Gegenteile (30 Wörter),
    Kalorien für 25 Lebensmittel mit „is that a lot?“ (Anteil am Tagesbedarf), Reis oder Nudeln, Eiweißbedarf.
  - Zeitzonen: „what time zone is london in?“ → „UTC+1 (summer time)“ aus den eingebauten Sommerzeitregeln, „what time
    is it there?“, „and in sydney?“, „how many hours ahead is that?“ → „Sydney is 9 hours ahead of London“.
  - Deutsch: „wie viele Kilometer sind 5 Meilen?“ (mit Dezimalkomma), „was heißt ubiquitous?“, „wie viele Kalorien hat
    eine Banane?“ (vorher 3× unverstanden).
  - Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–52 und langes Gespräch: 0 Wiederholungen.
    Suite 729 bestanden, 7 übersprungen.
- **Alltags-Batterie 54 (Neuigkeiten anderer, Streit, Scheidung der Eltern; Englisch und Deutsch)**:
  - Verlobung der Schwester → „boyfriend of 5 years“ → „wedding next summer“ (vorher „How did it go?“) → Trauzeugin →
    Aufgaben; Baby der besten Freundin → „it's a girl“ → Geschenkideen fürs Baby; Führerschein → „first try“ → „now i need
    a car“ (vorher als Fakt „A need, nice!“ gespeichert) → Tipps fürs erste Auto; Streit mit der besten Freundin → was sie
    sagte → „maybe she's right“ → Entschuldigung → Anruf; Scheidung der Eltern → „i'm 25“ (vorher „25 — got it!“) →
    „but it still hurts“.
  - Fehler aus Batterie 51 gefunden: „ich bin trauzeugin“ → „Hallo Trauzeugin!“. Ein Name wird jetzt nur angenommen, wenn
    das Wort als Name bekannt ist oder Engramm gerade nach dem Namen gefragt hat.
  - Zwei Fehler durch doppelte Namen im Code: Ein neuer Regex `_DE_CALL` überschrieb den gleichnamigen für das kranke
    Haustier („ok ich ruf an“ war plötzlich unverstanden; von der Regressionsbatterie 44 abgefangen). Außerdem war
    `_NOT_NAMES` seit Batterie 36 zweimal definiert, die zweite Liste ersetzte still die erste. Beide sind behoben; ein neuer
    Test verbietet doppelte Musternamen in dialog.py.
  - Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–53 und langes Gespräch: 0 Wiederholungen.
    Suite 732 bestanden, 7 übersprungen.
- **Alltags-Batterie 55 (Filme, Bücher, Musik, Fußball; Englisch und Deutsch)**:
  - Faktenfehler gefunden: „i just finished reading 1984“ → „who wrote it?“ → „It was written by Stephen King.“ Der
    Fragesatz wurde als Frage nach dem Roman „It“ gelesen. Jetzt ist ein kleingeschriebenes „it“ als Objekt („who wrote/
    directed/made it“) nie ein Titel, und das genannte Werk wird zum Thema: „1984“ → „Nineteen Eighty-Four“ → „who wrote it?“
    → „Nineteen Eighty-Four was written by George Orwell.“ → „what else did he write?“ → Orwells Werke.
  - Werk-Kontext: „i loved interstellar“ → „any similar movies?“ (ohne den Film selbst); „i've been listening to a lot of
    taylor swift“ wurde zu „you work as a lot“, jetzt eine passende Rückfrage; „it was so depressing“ nach einem Buch war
    „That's brilliant — you must be really happy!“, jetzt passend; Fußballergebnis („bayern won 3-1“); „who's the best
    player in the world?“ mit Datumshinweis. Hobbys wie „i love cooking“ bleiben Hobbys (eine erste Fassung las sie als
    Werk; vom Dev-Satz, team-0045, und Batterie 43 abgefangen und vor dem Commit behoben).
  - Deutsch: „hast du interstellar gesehen?“ → „worum geht es?“ → „wer hat den Film gemacht?“ (aus dem Artikel:
    Christopher Nolan) → „kennst du ähnliche Filme?“.
  - Grenze: „Inception“ steht nicht im Lite-Paket; dazu sagt Engramm ehrlich, dass es nichts weiß.
  - Team-Dev-Satz: 0 von 128 geändert. NQ-open 400: 22/9. Regressionen 32, 38–54 und langes Gespräch: 0 Wiederholungen.
    Suite 735 bestanden, 7 übersprungen.
- **Alltags-Batterie 56 (Wissens-Folgefragen: Personen, Ämter, Werke; Englisch und Deutsch)**:
  - Faktenfehler gefunden: „who invented the telephone?“ → „when?“ → „where was he born?“ → „Telephone was born in Bell
    Telephone Laboratories.“ Das „he“ fiel nach der Zwischenfrage auf das Thema (das Telefon) zurück. Jetzt merkt sich das
    Gespräch die zuletzt genannte Person samt Thema; bei mehreren Erfindern fragt Engramm nach („Several people are
    credited — Meucci, Gray, Bell and Reis. Which one do you mean?“), und „bell“ wählt Alexander Graham Bell.
  - Pronomen: „how old is he?“ direkt nach Michelle Obama → Barack Obama (Liste der zuletzt genannten Personen mit
    Geschlecht; die Erkennung liest jetzt fünf statt zwei Anfangssätze). „how old was George Washington when he died?“ ersetzte
    das „he“ durch die Person davor; ein Pronomen, das in dieselbe Frage zurückzeigt, bleibt jetzt stehen (67 Jahre).
  - Neu ohne Faktenbank-Eintrag, mit strengen Satzmustern: „who was the first president of the United States?“ (mindestens
    zwei übereinstimmende Belegsätze, „forty-first“ zählt nicht; ein Fall-Bug „first President“ wurde vom neuen Test
    gefunden); „who composed the Four Seasons?“ (Artikeltitel „The Four Seasons (Vivaldi)“, Klammername ist eine bekannte
    Person); „how long was he president?“ (Jahre aus dem Artikelanfang: 1789–1797, etwa 8 Jahre).
  - Formulierung: „when?“ nach „who discovered penicillin?“ wird „When was penicillin discovered?“ (statt „When discovered
    penicillin?“, „The answer is 1929.“); „Antonio Vivaldi: the Republic of Venice.“ wird „… was from …“; „Telephone was
    invented“ wird „The telephone was invented“ (einzige Dev-Änderung, team-0067); „in the 7th arrondissement“;
    „what language do they speak?“ nach Tokio fragt nach dem Land (Japanisch, Yen).
  - Deutsch: „wer war der erste präsident der usa?“ → „Das war George Washington.“ → „wie lange war er präsident?“ → „Von 1789
    bis 1797 – etwa 8 Jahre.“; „und wie alt ist er?“ nach Michelle Obama gab dieselbe Antwort noch einmal, jetzt Barack Obama;
    „wann?“ → „Im Jahr 1929.“; Rückfrage bei mehreren Erfindern auf Deutsch, die Antwort darauf bleibt Deutsch;
    „Die Vier Jahreszeiten wurden …“.
  - Grenze: „The Starry Night“ und Alexander Fleming stehen nicht im Lite-Paket; Engramm sagt ehrlich, dass es nichts weiß.
    „Who designed the Eiffel Tower?“ nennt laut Faktenbank Stéphen Sauvestre (DBpedia-Eintrag „architect“), nicht Gustave Eiffel.
  - Team-Dev-Satz: 1 von 128 geändert (team-0067, Artikel). NQ-open 400: 22/9. Regressionen 32, 38–55 und langes
    Gespräch: 0 Wiederholungen (Unterschiede nur Uhrzeiten). Suite: siehe Runde 56/57/59 unten.
- **Alltags-Batterie 57 (Alltagsmomente mit Bezug auf den Satz davor)**:
  - Schwere Fehlgriffe gefunden: „my phone died“ → „I'm so sorry for your loss … tell me about them?“ und „i'm gonna miss
    her so much“ (die beste Freundin zieht nach Kanada) → Beileid. Der Trauer-Auslöser „died“/„is dead“ greift jetzt nicht
    mehr nach Geräten (phone, battery, laptop …); „my grandma died“ bekommt weiter Mitgefühl. Wegzug: „Where are they
    moving to?“ → „Canada — that's quite far. When's the move?“ → „That's soon …“ → „I bet. It hurts because it matters …“.
  - „it's raining again“ und „and i have work tomorrow“ (nach „i can't sleep“) landeten bei „I can't check live data“ bzw.
    „Setting alarms … is outside what I can do“. Jetzt: Wetter-Smalltalk (Regen, Kälte, Hitze, Schnee, Sonne), danach
    „i wanted to go for a run“ → Ausweichvorschlag, „maybe tomorrow“ → „Sounds like a plan“; nachts „it's 3am“ → „Oof, 3am —
    …“, und „i can't sleep“ rät nicht mehr „get some sleep soon“.
  - Welpe: „guess what“ → „What happened? Spill!“ (vorher „I see. Tell me more?“) → „i got a puppy!“ → „What breed?“ →
    „she's a golden retriever“ (vorher „How did it go?“) → „any name ideas?“ (vorher „I couldn't find anything reliable“)
    → drei Namen → „i like the second one“ → „Luna it is!“ (vorher als Vorliebe „One“ gespeichert).
  - Kühlschrank: „theres nothing in the fridge“ → Rückfrage nach Eiern/Brot (vorher „with nothing I'd keep it simple“) →
    „just eggs and cheese“ → Käse-Omelett mit Anleitung → „how long do i cook it?“ → „About 3–4 minutes …“.
  - Farbe: „mine is green“ wird als Lieblingsfarbe gespeichert; „do you like green?“ ist eine Meinung, kein Lexikonauszug
    über Wellenlängen. „can't find my charger“ → Suchtipps statt „That's a lot to deal with“.
  - Zwei Fehler der ersten Fassung, vor dem Commit gefunden: eine Endlosschleife (die gespeicherte Farbe löste dieselbe
    Regel wieder aus) und zwei YAML-Schlüssel, die es schon gab (pet_names, pet_breed; vom Studio-Duplikatcheck gemeldet).
  - Team-Dev-Satz, NQ, Regressionen, Suite: siehe Runde 56/57 unten.
  - Deutsch: dieselben Momente („rate mal“, „ich hab einen welpen bekommen!“, „der kühlschrank ist leer“ → „nur eier und
    käse“, „mein handy ist tot“ – vorher „Oh nein, das tut mir so leid. Magst du mir von ihm erzählen?“ –, „es regnet schon
    wieder“, „meine beste freundin zieht weg“ … „ich werde sie so vermissen“) waren fast alle „Das habe ich nicht ganz
    verstanden“, mit drei wörtlichen Wiederholungen; jetzt eigene deutsche Antworten, 0 Wiederholungen.
  - Haustier-Gedächtnis: Rasse und ein aus der Liste gewählter Name werden gespeichert („what's my puppy called?“ → Milo,
    „what breed is he?“ → „Milo is a maine coon.“). Die erste Fassung fing auch „i have a cat“/„i adopted a dog“ ab und
    überging den bestehenden Ablauf, der nach dem Namen fragt (zwei alte Tests schlugen an, vor dem Commit behoben); eine
    Abfangregel für „i can't sleep“ brach die Schlaf-Kette aus Batterie 42 („work stuff mostly“, Tipps) und wurde durch
    eine passendere Empathie-Antwort ersetzt („Is something keeping you up …?“ statt „maybe get some sleep soon“).
- **Alltags-Batterie 59 (Tastatursalat und Laute; Anlass: Screenshot „dhdhd“ → „Interesting! What makes you say that?“)**:
  - Der Screenshot stammt aus einer älteren Version: Diese Antwort gibt es im aktuellen Stand nicht mehr, „dhdhd“ wird
    seit Batterie 20 als Tastatursalat erkannt. Geprüft wurden 30 weitere kurze Eingaben.
  - Gefunden und behoben: „hhhh“, „xyz“, „abc“ → „Oh? Go on.“; „aaaaa“, „smh“ → „I see. Tell me more?“; „omg“ → „Got it.
    Anything I can help you with?“. Jetzt menschliche Reaktionen (Seufzer, Schrei, Test-Nachricht, „What?! What happened?“).
  - „dhdhd lol“ galt nicht als Salat (ein Chatwort daneben), „i like dhdhd“ wurde als Vorliebe gespeichert, „what is
    dhdhd?“ nachgeschlagen. Jetzt: Rückfrage „“dhdhd”? I don't know that word …“, beim dritten Mal ohne erneutes „typo?“
    und ohne Wiederholung. Nur eindeutige Fälle zählen (Tastenfolge oder Konsonantenkette ohne Vokal); eine erste Fassung
    hätte „yoyo“, „bonbon“, „dodo“ und „byebye“ erwischt (eigener Test, vor dem Commit verschärft). Namen („my name is …“)
    sind ausgenommen.
  - „sorry my cat walked on the keyboard“ nach Salat wurde als Fakt über die Katze gespeichert; jetzt „Haha, no worries!
    What did you want to say?“.
- **Runde 56/57/59, Messung**: Team-Dev-Satz 1 von 128 geändert (team-0067, Artikel). NQ-open 400: 22/9. Suite 747 bestanden,
  7 übersprungen. Regressionen 32, 38–59 (Englisch und Deutsch, 25 Gespräche) und langes Gespräch: 0 Wiederholungen;
  Unterschiede nur in Batterie 42/57 (die wieder intakte Schlaf-Kette mit Tipps) und Uhrzeiten.
- **Alltags-Batterie 58 (Folgefragen, die den Satz davor brauchen)**:
  - „no i meant in europe“ nach dem höchsten Berg der Welt wurde als Aussage gespeichert („Oh really? Tell me more“); jetzt
    wird die Frage für Europa neu gestellt → Elbrus (Mont Blanc für Westeuropa) → „how tall is it?“ → „Mount Elbrus is
    5,642 m (18,510 ft) high.“ Höchste Berge der Kontinente, der Alpen und Deutschlands als handgeprüfte Alltagsfakten.
  - „should i learn spanish or french?“ → „Let me pick for you: “learn spanish”“ → „why?“ → „I didn't give you a fact just
    now, so there's no source to show.“ Jetzt: Wahl mit Begründung (Sprecher, Schwierigkeit, Länder), „why?“ erklärt sie,
    „i'll go with spanish“ wird nicht als Fakt gelernt, „how long will it take?“ → 3–6 Monate.
  - „thanks! you're smart“ → „You're welcome! Aw, thanks! You made my day.“ (zwei Antworten) → nur „Aw, thanks! …“.
  - „it's for a marketing role“ → „A Marketing Role — impressive! What's the role?“ und später „Good luck at A Marketing Role“;
    jetzt eine Rolle, keine Firma.
  - „i don't get it“ nach einem Witz → vorher „What are you trying to find out?“; „but i need the money“ / „what would you
    do?“ vor einer Kündigung → konkrete Abwägung statt allgemeiner Notiz-Tipps; „are you sure?“ → „Yes — Lima. That's
    straight from the infobox …“ statt der rohen Infobox-Zeile.
  - Team-Dev-Satz: 1 von 128 geändert (team-0067, wie Runde 56). NQ-open 400: 22/9. Suite 748 bestanden, 7 übersprungen.
    Regressionen 32, 38–59 (26 Gespräche, Englisch und Deutsch): 0 Wiederholungen, keine Unterschiede außer Uhrzeiten.
- **Alltags-Batterie 60 (ein ganz normaler Abend: Arbeit, Wandern, Musik, Bücher, Erkältung, Uhrzeit, Prüfungen)**:
  - Schwerer Fehler: „it was okay, kinda long“ wurde als Deutsch erkannt („Das verstehe ich leider nicht …“), weil „okay“
    als eindeutig deutsches Wort zählte. „okay/ok“ sind jetzt mehrdeutig, häufige englische Alltagswörter (kinda, long,
    gonna, really …) zählen für Englisch; deutsche Sätze („es war okay“, „ok danke“, „der film war lang“) bleiben Deutsch.
  - Wandern: „near munich“ → „Ooh, a mountain near Munich! How long did it take you?“ (vorher „tell me more“), „about 5
    hours“, „my legs hurt now lol“ → Muskelkater-Tipp statt „What went wrong with your legs?“.
  - Musik: „what kind?“ nach meiner Frage → meine eigene (gedachte) Vorliebe statt „I couldn't find anything“; „have you
    heard of queen?“ → erster Satz des Artikels → „who was their singer?“ → Freddie Mercury → „when did he die?“ → 24 November 1991.
  - Bücher: „i've read that one“ und „something shorter?“ (vorher Nachschlagefehler) → kurze Bücher.
  - Erkältung: Symptome → Rat (Ruhe, Tee, Arzt bei hohem Fieber), „thanks, i'll stay home“ → „Get well soon“ statt
    „You're welcome! Oh, interesting — tell me more.“ Uhrzeit: „and in tokyo?“ → Weltzeit, „is it night there?“ aus der
    Ortszeit. Prüfungen: „they went well“, „3 months off“, „what should i do with all that time?“ → Ideenliste statt
    „sleep on it“. „any plans for the weekend? oh wait you're a bot lol“ → Antwort statt Nachschlagefehler.
  - Team-Dev-Satz: 1 von 128 geändert (team-0067). NQ-open 400: 22/9. Suite 749 bestanden, 7 übersprungen. Regressionen
    32, 38–60 (27 Gespräche): 0 Wiederholungen, keine Unterschiede.
- **Alltags-Batterie 61 (derselbe Abend auf Deutsch)**:
  - Vorher waren 13 von 27 Antworten „Das verstehe ich leider nicht …“/„Das habe ich nicht ganz verstanden …“, eine
    davon wörtlich wiederholt; „so 5 stunden“ sprang ins Englische („Mm-hm. What's on your mind?“), „ich hab meine
    prüfungen fertig!“ bekam „Müdigkeit ist fies“ (das Wort „fertig“ zählte als müde), „kennst du queen?“ → „Hat er dir
    gefallen?“ (als Film gelesen).
  - Jetzt: Feierabend und langer Tag, „und bei dir?“, Wandern (Ort, Dauer, Muskelkater), Musik und Band („wer war ihr
    sänger?“ → Freddie Mercury → „wann ist er gestorben?“), Erkältung mit Rückfrage, Symptomen und Rat, „und in
    tokio?“/„ist es dort nacht?“, Prüfungen und Ideen für die freie Zeit – 0 Wiederholungen.
  - Neu als Grundregel: Eine deutsche Aussage, die nichts anderes versteht, bekommt eine Antwort passend zur Stimmung
    (positiv, negativ, neutral) statt „Das verstehe ich leider nicht“; Fragen bleiben ehrlich („nachschlagen kann ich das
    auf Deutsch noch nicht“). „fertig“ zählt nur noch als müde in „ich bin (so) fertig“, nicht in „Prüfungen fertig“.
  - Messung: Team-Dev-Satz 1 von 128 geändert (team-0067). NQ-open 400: 22/9. Suite 750 bestanden. Regressionen 28
    Gespräche, 0 Wiederholungen. Dabei im langen Gespräch gefunden (Fehler schon vor dieser Runde): Nach „hast du tipps?“
    blieb „how many days until christmas“ im deutschen Zweig („Das verstehe ich leider nicht“). Die englische Wortliste
    der Spracherkennung kennt jetzt häufige Wörter wie many, much, until, days, year, time; die Frage wird wieder auf
    Englisch beantwortet („84 days until …“). „about 12.0 weeks“ heißt jetzt „exactly 12 weeks“. Eine erste Fassung zählte
    auch „sorry“ als englisch; dann sprang „sorry, war nicht so gemeint“ ins Englische (Batterie 46 und ein Test fingen
    das ab, „sorry“ ist wieder neutral). Danach: Suite 751 bestanden, 28 Gespräche ohne Wiederholung, Unterschiede nur
    die beabsichtigten (Batterie 40, langes Gespräch).
- **Alltags-Batterie 62 (Neckereien, Rechnen nebenbei, Tagesplan, Nein sagen)**:
  - „i spent 20 on lunch and 15 on dinner“ → „how much is that?“ → vorher Nachschlagefehler, dann „You spent 20 on lunch
    and 15 on dinner.“; jetzt „20 + 15 = 35.“ → „and if i add 12 for coffee?“ → 47 → „i should stop buying coffee“ wird
    nicht als Vorliebe „coffee — yum!“ gespeichert.
  - Tagesplan: „i have a meeting at 10, gym at 6 and i need to buy groceries“ wurde nur als Termin gespeichert; jetzt
    Zusammenfassung und „when should i buy groceries?“ → Lücke zwischen den festen Terminen.
  - „tell me something funny then“ → „The answer is predicative.“ (Nachschlagen) → jetzt ein Witz; „how do i say no
    politely?“ → drei Formulierungen; „lucky you“ nach „Never sleep“ → „That's really nice to hear!“ → jetzt passend;
    „what would you dream about?“, „if you could eat, what would you try first?“, „what toppings?“, „you're weird“ mit
    eigenen, menschlichen Antworten.
  - Erste Fassung fing „help me plan my day“ ab und überging den vorhandenen Tagesplaner (alter Test schlug an); jetzt
    beantwortet der Planer den Einstieg, die neue Regel ergänzt nur Uhrzeiten. Messung: Team-Dev-Satz 1 von 128 (team-0067),
    NQ 22/9, Suite 752 bestanden, Regressionen 32, 38–62 (29 Gespräche): 0 Wiederholungen.
- **Alltags-Batterie 63 (Batterien 58 und 62 auf Deutsch)**:
  - Vorher 11 von 21 Antworten unverstanden oder fehl am Platz: „soll ich spanisch oder französisch lernen?“, „wie viel
    ist das?“ nach zwei Beträgen, „wie sage ich höflich nein?“, „schläfst du eigentlich?“, „bist du schlauer als
    chatgpt?“; die neue Grundantwort aus Batterie 61 („Interessant – wie ging's weiter?“) kam auch auf „nein, ich meinte
    in europa“, „versteh ich nicht“ (nach einem Witz) und „ich überlege zu kündigen“.
  - Jetzt: Sprachwahl mit Begründung, „warum?“, „ok, dann spanisch“, „wie lange dauert das?“; „nein, ich meinte in
    europa“ → Elbrus → „wie hoch ist er?“ → „Mount Elbrus ist 5.642 m hoch.“; 20 + 15 = 35 Euro → +12 → 47 Euro;
    Kündigung (Geld, „was würdest du machen?“), höflich Nein sagen, Witz nicht verstanden, ChatGPT-Vergleich, Schlaf,
    „du glücklicher“, „du bist komisch“.
  - Die neutrale Grundantwort gilt nur noch für Erzählungen (Ich-Sätze oder „die Nachbarn haben …“), nie für Sätze mit
    „nicht“, „meinte“, „überlege“; sonst bleibt es bei der ehrlichen Rückfrage.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067). NQ-open 400: 22/9. Suite 753 bestanden, 7 übersprungen. Regressionen
    32, 38–63 (30 Gespräche, Englisch und Deutsch): 0 Wiederholungen, Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 64 (emotionale Gespräche: Einsamkeit, Angst, Trauer, Selbstzweifel, Hoffnungslosigkeit)**:
  - Schwere Fehlgriffe gefunden: „i'm kinda shy though“ → „Got it, your favourite colour is shy.“; „he taught me how to
    fish“ (nach dem Tod des Großvaters) → „Noted: fish — yum!“; „everyone at work seems smarter“ → „I'm not connected to
    your calendar or clock“ (der Geräte-Klassifikator griff bei einer Aussage); „nobody cares about me“ → „not even my
    family“ → „i don't know why i bother“ und „maybe i should just quit everything“ bekamen nur „I get why that's weighing
    on you“ / „That's a lot to deal with“.
  - Jetzt: Schüchternheit mit passendem Rat; Trauer („we were really close“ → „What was he like?“, eine Erinnerung wird
    gewürdigt, nicht als Vorliebe gespeichert); Selbstzweifel (Hochstapler-Gefühl); bei Hoffnungslosigkeit eine ruhige
    Nachfrage mit den geprüften Hilfenummern (988, Samaritans 116 123, Telefonseelsorge 0800 111 0 111, Notruf) –
    ausgelöst nur durch Aussagen wie „i don't know why i bother“/„quit everything“ nach „nobody cares“ oder „not good
    enough“; Präsentationsangst und „what if i mess up?“, Panikattacke (Mitgefühl, dann Tipps und der Hinweis auf
    ärztliche Hilfe), Trennung („should i stay friends with him?“), Studienplatz in Edinburgh und Umzugsnerven.
  - Der Geräte-Klassifikator („set a timer“) greift bei Aussagen nur noch, wenn sie wie ein Befehl beginnen.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067). NQ-open 400: 22/9. Suite 754 bestanden, 7 übersprungen. Regressionen
    32, 38–64 (31 Gespräche): 0 Wiederholungen, Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 65 (Batterie 64 auf Deutsch)**:
  - Schwerer Fehler, ausgelöst durch die Grundantwort aus Batterie 61: Sie merkte sich neutrale Aussagen als positive
    Stimmung, und alles Folgende bekam fröhliche Antworten – „mein opa ist letzten monat gestorben“ → „Ah, verstehe.
    Erzähl ruhig mehr!“, „wir standen uns sehr nahe“ → „Das klingt richtig gut!“, „es tut trotzdem weh“ → „Wie schön!“,
    „vielleicht sollte ich einfach alles hinschmeißen“ → „Finde ich gut!“. Außerdem gab es auf Deutsch keine
    Trauer-Kategorie; „niemand interessiert sich für mich“ war unverstanden.
  - Behoben: neutrale Aussagen zählen als neutral (keine fröhliche Folgeantwort), traurige Wörter (gestorben, schlimm,
    vermisse, allein …) zählen negativ, und eine positive Stimmung wird bei solchen Wörtern nie fortgeschrieben. Neue
    Trauer-Kategorie (gestorben, Beerdigung, „habe meinen Hund verloren“ …).
  - Jetzt wie auf Englisch: neue Stadt und Freunde finden, schüchtern, Trauer mit Erinnerungen, Hochstapler-Gefühl,
    Hoffnungslosigkeit mit ruhiger Nachfrage und TelefonSeelsorge (0800 111 0 111/0800 111 0 222, Österreich 142,
    Schweiz 143, Notruf 112), Panikattacke, Präsentationsangst, Trennung („soll ich mit ihm befreundet bleiben?“).
  - Erste Fassung fing „meine freundin hat schluss gemacht“ ab, ohne den Gesprächszustand zu setzen; die bestehende
    Folgefrage „wir waren 2 jahre zusammen“ ging verloren (alter Test fing das ab, vor dem Commit behoben).
  - Messung: Team-Dev-Satz 1 von 128 (team-0067). NQ-open 400: 22/9. Suite 755 bestanden. Regressionen 32, 38–65
    (32 Gespräche): 0 Wiederholungen. Batterie 41 zeigte, dass „meine freundin hat schluss gemacht“ nun „auch wenn sie richtig
    sind“ hörte – die eigene Trennungsantwort gilt jetzt nur, wenn man selbst Schluss gemacht hat (Batterie 41 wieder wie vorher).
- **Alltags-Batterie 66 (Gedächtnis: Korrekturen, Abneigungen, Vergessen, mehrere Sätze)**:
  - Schwerer Fehler im Datenschutz-Kernversprechen: „forget that i hate mushrooms“ und „forget that i like pizza“
    vergaßen nichts – die Füllwort-Regel aus Batterie 43 entfernte „forget that“ wie bei „forget it, tell me a joke“, der
    Rest wurde neu gespeichert („I already know that“, „Pizza — good choice! I'll remember that.“). Jetzt nur noch vor
    einem Satzzeichen; das genaue Vergessen trifft den Eintrag, der alle Inhaltswörter enthält („I don't like mushrooms“),
    statt den ähnlichsten (vorher wurde einmal „My name is Lena …“ gelöscht).
  - „i'm lena and i'm a teacher in hamburg“ → Beruf „hamburg“; jetzt Name, Beruf und Wohnort als drei einzelne
    Erinnerungen (einzeln vergessbar). „i hate mushrooms“ wurde zum Lieblingsessen („What food do I hate?“ → „Your
    favourite food is mushrooms.“); jetzt eine Abneigung, auch in „what do you know about me?“ („You don't like mushrooms.“),
    und „suggest a pizza for me“ lässt die Pilze weg.
  - Korrekturen: „no wait, i meant munich“ (vorher als Aussage gespeichert) ersetzt den alten Wohnort; ein neuer Wohnort,
    Beruf oder Arbeitgeber ersetzt den alten (vorher standen „You live in Hamburg“ und „You live in Munich“ nebeneinander);
    „actually it moved to monday“ (vorher „Monday — nice! I'll remember that you live there.“) verschiebt den Zahnarzttermin.
  - „she's a doctor“ nach „my sister's name is anna“ (vorher „Oh? Go on.“) wird gespeichert; „what does my sister do?“,
    „what's her name again?“ → „Anna“ (Namen großgeschrieben); „what do i do?“ fragt nach dem eigenen Beruf, nicht nach
    Sehenswürdigkeiten.
  - Eine Nachricht mit drei Sätzen über einen schweren Tag bekam drei Mitgefühls-Antworten hintereinander; jetzt eine,
    der Rest wird still gemerkt. „any ideas?“ nach „i just want to relax“ → Entspannungsideen; „do you know them?“ nach
    der Lieblingsband → Artikelanfang.
  - Die erste Fassung der Korrekturregel fing auch „no wait, its alexander“ nach einem Namen ab („alexander it is“,
    kleingeschrieben); ein alter Test schlug an, Namen bleiben beim eigenen Namens-Ablauf („Alexander“). Messung: Team-Dev-Satz
    1 von 128 (team-0067), NQ 22/9, Suite 756 bestanden, Regressionen 32, 38–66 (33 Gespräche): 0 Wiederholungen;
    Unterschiede: Batterie 41 (Trennungsantwort wie früher), 48 (kein doppelter Punkt im Vergessen-Zitat), Uhrzeiten.
- **Alltags-Batterie 67 (Gedächtnis auf Deutsch)**: Das deutsche Gedächtnis war deutlich schwächer als das englische.
  - „hi, ich bin lena und ich bin lehrerin in hamburg“ → Rückfallantwort; jetzt Name, Beruf und Wohnort als drei einzelne
    Erinnerungen („Freut mich, Lena! Lehrerin in Hamburg – merk ich mir.“). „ich wohne in berlin“ wurde als Englisch erkannt
    („Mm-hm. What's on your mind?“), weil „wohne“ in der deutschen Wortliste fehlte; ergänzt um wohne, lebe, arbeite, heiße,
    hasse, schwester, bruder, merk, vergiss, verschoben, termin u. a.
  - „nein, ich meinte münchen“ (vorher Rückfallantwort) ersetzt den alten Wohnort; nach einem Satz mit Beruf und Ort
    trifft die Korrektur den passenden Teil („ich meinte bonn“ → Wohnort, „ich meinte bäcker“ → Beruf).
    „ich arbeite als koch bei einem hotel“ speichert keinen Wohnort „Einem Hotel“; „ich bin wieder/heute in köln“
    speichert keinen Beruf.
  - „meine schwester heißt anna“ (vorher „Interessant – wie ging's weiter?“) → „sie ist ärztin“ → „was macht meine
    schwester beruflich?“ → „Deine Schwester arbeitet als Ärztin.“; „sie ist echt nett“ bekommt eine warme Antwort statt
    „Das verstehe ich leider nicht“.
  - „vergiss, dass ich pilze hasse“ (vorher eine Mitgefühls-Antwort, nichts vergessen) löscht den Eintrag wirklich.
  - „merk dir, dass mein zahnarzttermin am freitag ist“, „der wurde auf montag verschoben“, „und wann ist er jetzt?“ →
    „Dein Zahnarzttermin ist am Montag.“ (vorher dreimal Rückfallantwort); „verschoben“ ohne bekannten Termin fragt nach.
  - „was weißt du über mich?“ mischte englische Sätze ein („Your sister is called Anna.“); jetzt ganz auf Deutsch.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 757 bestanden, Regressionen 32, 38–67 plus 7 deutsche
    Gegenproben (35 Gespräche): 0 Wiederholungen; Unterschiede nur Uhrzeiten (Batterie 60).
- **Alltags-Batterie 68 (lockeres Gespräch: Meinungen, Rückfragen, Kochen, Sport, Langeweile; EN + DE)**:
  - „not much, just chilling. you?“ → vorher „A calm day is underrated. Anything fun planned? I'm good, thanks!“ (Antwort
    auf die Rückfrage am Ende); jetzt zuerst „I'm good, thanks“. „nm u?“ bleibt bei der alten, passenden Antwort.
  - ENGRAMM hatte auf Deutsch Lieblinge (Film „Zurück in die Zukunft“, Buch, Tier …), auf Englisch nur „I don't have one
    of my own“; jetzt dieselben Lieblinge in beiden Sprachen, und „why that one?“/„warum?“ (vorher „I don't know, sorry“
    bzw. „kann ich auf Deutsch nicht nachschlagen“) bekommt eine Begründung. Die englische Lieblingsfarbe bleibt das
    bisherige Violett (erste Fassung überschrieb sie und brach „mine is green“ – von Batterie 57 gefunden, zurückgenommen).
  - „what did you think of it?“ nach „have you seen inception?“ → vorher Suche („So You Think You Can Dance came closest“);
    jetzt ehrlich: keine eigene Meinung, Rückfrage.
  - „i'm making pasta tonight“ wurde als Lieblingsessen gespeichert; jetzt Rückfrage, „carbonara“ (vorher Artikelanfang) →
    kurze Antwort, „do you think cream belongs in carbonara?“ (vorher „I don't know“) → traditionell nein, „what should i
    drink with it?“ (vorher „Your favourite food is pasta.“) → passende Getränke; „not sure yet“/„maybe tacos“ verstanden.
  - „football“ nach „did you watch the game?“ (vorher Artikelanfang) → Rückfrage; „my team lost 3-0“ (vorher „My Team 3–0 —
    nice!“) → Mitgefühl; „there's always next season“ (vorher „that can really wear you down“) → Zuversicht.
  - „you're wrong lol“ nach einer neutralen Antwort → „I didn't actually take a side“; „i'm a cat person“ und „i'm a nice
    person“ wurden als Beruf gespeichert („you work as a person“) – behoben.
  - „do you like talking to me?“ (vorher „Opinions aren't really my thing“), „what's your name again?“ (vorher „I don't
    know“); Langeweile: „i don't know“/„something fun“ bekommen Vorschläge bzw. einen Witz statt „Fair enough.“/„Nice!“.
  - Deutsch: „und sonst so?“, „magst du katzen oder hunde lieber?“ (vorher Rückfallantworten), „ich bin ein Katzenmensch“.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 758 bestanden, Regressionen 32, 38–68 plus Gegenproben
    (37 Gespräche): 0 Wiederholungen; Unterschiede: neue Lieblings-Antworten (Batterien 58, 62, long), Uhrzeiten.
- **Alltags-Batterie 69 (echte, unordentliche Nachrichten: Slang, Emojis, Doppelfragen, Rückbezüge)**:
  - „im good hbu“ (vorher „Great! Ask me anything“, die Rückfrage überhört) → „I'm doing well, thanks for asking“.
  - „wait what was the height again?“ (vorher „I don't know“) fragt die frühere Frage noch einmal – bei einer Doppelfrage
    („how tall … and when was it built?“) nur den passenden Teil; ohne frühere Frage eine Rückfrage statt „Zürich was the
    name again.“ (vorher, unsinnig).
  - „what about food?“ nach Reisetipps für Paris (vorher Kochrezepte für zu Hause) → Essen in Paris; zehn Städte, sonst
    ein allgemeiner Tipp. „merci!“ (vorher „Oh? Go on.“) → „De rien !“.
  - „ugh monday again 😩“ (vorher „what happened?“) → Montags-Antwort; Emojis stören die Muster nicht mehr (auch das
    deutsche „hab heute frei 🎉“, vorher Rückfallantwort). „i hate mondays“ bleibt eine gemerkte Abneigung.
  - „my boss keeps giving me extra tasks“ (vorher „Oh really? Tell me more“, als Fakt gespeichert) → Mitgefühl;
    „idk what to do“ (vorher „sleep on it“) und „what should i do?“ (vorher Freizeitideen wie „ein langes Bad“) → Rat zur
    Prioritätenliste mit dem Chef; „that helps“ direkt danach → „Glad it helps!“ (sonst die bisherigen Dank-Antworten).
  - „i'm good at math, you?“ (vorher „You haven't told me that yet“) wird gemerkt und beantwortet.
  - „ja endlich mal ausschlafen“ nach dem freien Tag (vorher Rückfallantwort); die erste Fassung ersetzte den vorhandenen
    Freier-Tag-Ablauf (Batterie 47 fand es: die Ideen auf „was könnte ich machen?“ fehlten) – zurückgenommen, jetzt eingehängt.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 759 bestanden, Regressionen 32, 38–69 plus Gegenproben
    (39 Gespräche): 0 Wiederholungen; Unterschiede nur Uhrzeiten (Batterie 60).
- **Alltags-Batterie 70 (lockeres Gespräch auf Deutsch) und ein falscher Zahlenwert im Frage-Antwort-Kern**:
  - Schwerer Fehler: „how high is zugspitze“ → „2,741 metres“ – die Zahl gehörte zum Nachbargipfel im selben Satz („The summit
    nearest to the Zugspitze is the Inner Höllentalspitze, 2,741 metres high“). Bei Maßfragen („how high/tall/long/deep is X“)
    gewinnt jetzt die Zahl, die direkt hinter dem Namen steht („Zugspitze, at 2,962 metres“); nennen zwei verschiedene
    Artikel dieselbe angehängte Zahl, reicht das als Beleg (Konfidenz auf θ). „how tall …“ scheiterte zusätzlich an der
    Deckungsprüfung („tall“ steht nicht im Beleg „highest point“); „tall“ ↔ „high/height/elevation“ ergänzt.
    Ergebnis: „how tall is the zugspitze?“ → „The Zugspitze is 2,962 metres tall.“, „wie hoch ist die zugspitze?“ (vorher
    „Das weiß ich leider nicht“ – ausgerechnet das Beispiel aus der eigenen Hilfe) → „Die Zugspitze ist 2.962 m hoch.“;
    „wie hoch war sie nochmal?“ → „Wie vorhin schon: die Zugspitze ist …“. Unit-Test mit den drei echten Belegsätzen.
    Versuch verworfen: Namen in Faktenbank-Antworten großschreiben („The matterhorn“) – ohne Beleg nicht von „The
    Telephone“ zu unterscheiden (Batterie 56 fand es), zurückgenommen.
  - „gut und dir?“ (vorher überhört), „ich koche heute abend pasta“ (vorher „Erzähl ruhig mehr!“), „carbonara“ (vorher
    englischer Artikelanfang), „gehört sahne in carbonara?“, „was trinke ich dazu?“ (vorher Rückfallantworten).
  - Fußball: „hast du das spiel gestern gesehen?“, „fußball“ (vorher zweimal „nicht verstanden“), „wir haben 3:0 verloren“
    (vorher „Was ist passiert?“, danach Erschöpfungs-Mitgefühl), „egal, nächste saison wird besser“.
  - Langeweile („keine ahnung“, „irgendwas lustiges“ → Witz), Chef mit Extra-Aufgaben (vorher „Okay! Und wie war's?“) mit Rat.
  - Reise nach Rom: Tipps (vorher „Zerleg es: Was ist der allernächste kleine Schritt?“), Essen in zehn Städten, „wie sagt
    man danke auf italienisch?“ (vorher „kann ich auf Deutsch nicht nachschlagen“), „grazie!“ (vorher „Oh? Go on.“).
  - „hast du gefühle?“, „wie heißt du nochmal?“ (vorher Rückfallantworten); „alles gut bei dir?“ bleibt eine Frage an
    ENGRAMM und „danke dir!“ ein Dank (beide von den Batterien 32/47/69 gefunden, als die erste Fassung sie als „gut, und
    dir?“ las).
  - Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9 (der Eingriff in den Kern ändert NQ nicht), Suite 761 bestanden,
    Regressionen 32, 38–70 (40 Gespräche): 0 Wiederholungen; Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 71 (40 feste Wissensfragen, Antworten vorher festgelegt, Englisch und Deutsch)**: erster Lauf 32 richtig,
  0 falsch, 8 „weiß ich nicht“. Die Umformulierung „who is the author of X“ → „who wrote X“ deckte einen echten Fehler auf:
  „who wrote harry potter?“ → „Richard Harris“ – der Rückweg über „bekanntes Werk“ nahm einen Schauspieler, der in der
  Faktenbank nebenbei als „writer“ geführt ist. Schauspieler zählen beim Schreiben jetzt nur noch, wenn sie ausdrücklich
  Romanautor, Dichter oder Dramatiker sind (Faust → Goethe, Hamlet, Zauberflöte, Guernica unverändert); Harry Potter →
  J. K. Rowling als Standardfakt. Ergänzt: größter Ozean, längster Fluss Europas, chemische Symbole (28 Elemente),
  „wann fiel …“, „wie tief ist …“ (Bodensee 251 m), deutsche Superlative für Planet, Ozean, Kontinent, Tier, Wüste.
  Die erste Fassung von „wann ist … gefallen“ fing „wann ist er gestorben?“ ab (Batterie 61 fand es) – „gefallen“ ist
  jetzt Pflicht. Endstand: 39 richtig, 0 falsch, 1 „weiß ich nicht“ („wer malte die Sternennacht?“ – nicht im Lite-Paket,
  ehrlich unbeantwortet).
  Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 762 bestanden, Regressionen 32, 38–70 (40 Gespräche):
  0 Wiederholungen; Unterschiede nur Uhrzeiten. Skript: `scratchpad/kq71.py` (Fragen und Antwortmuster im Kopf der Datei).
- **Alltags-Batterie 72 (zweite Stichprobe: 40 neue feste Wissensfragen, Personen, Geschichte, Geografie, Wissenschaft)**:
  erster Lauf 26 richtig, **1 falsch**, 13 „weiß ich nicht“. Der Fehler: „how many countries are in the eu?“ → „The answer
  is two.“ aus „The two countries are EU, UN and NATO member states“ – „the two countries“ meint ein bestimmtes Paar, keine
  Anzahl. Bei „how many X …“ zählt „the/these/both N X“ im Beleg jetzt nicht mehr als Antwort (Unit-Test). Ergänzt:
  EU-Mitglieder (27, seit 2020), Sonne ein Stern, Kolumbus 1492, Entfernung zum Mond (vorher „I can't measure distances
  between places“), H₂O, größte Wüste, 1984 → Orwell, Titanic; Deutsch: „wann sank …“, „welche Sprache spricht man in …“
  (Sprachnamen auf Deutsch: „In Brasilien spricht man Portugiesisch.“), erster Mensch auf dem Mond, Spinnenbeine, EU,
  Mond-Entfernung. „welche sprache spricht man in brasilien?“ wurde als Englisch erkannt (Wortliste ergänzt; „sank“ bewusst
  nicht, weil auch englisch). Endstand: 38 richtig, 0 falsch, 2 „weiß ich nicht“ (Sternennacht – nicht im Lite-Paket;
  Tesla-Chef – zeitabhängig, ohne Beleg lieber ehrlich offen). Batterie 71 danach unverändert 39/0/1.
  Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 763 bestanden, Regressionen 32, 38–70: 0 Wiederholungen;
  Unterschiede nur Uhrzeiten. Skript: `scratchpad/kq72.py`.
- **Alltags-Batterie 73 (was man sich merkt und was vorbeigeht; EN + DE)**:
  - Schwerer Fehler: „I'm allergic to peanuts“ wurde zum Lieblingsessen („Peanuts — good choice!“, später „Your favourite food
    is peanuts.“). Allergien sind jetzt eine eigene Art von Fakt (`#allergy`, nie Vorliebe oder Essen), „what am i allergic
    to?“ → „You're allergic to peanuts.“. „I live with my girlfriend“ wurde zum Wohnort („You live in girlfriend.“); jetzt
    `#housemate` („You live with your girlfriend.“, „who do i live with?“).
  - „my dad called me today“ → „Got it, your father is called dad.“ (anrufen als Name gelesen); jetzt „That's nice! How's he
    doing?“. „i'm drinking coffee“ (vorher „Drinking — good choice!“), „my mom fell asleep on the couch“, „my cat is sleeping
    on my lap“, „i'm watching tv“, „i just ate a sandwich“, „my brother is coming over later“ wurden als Fakten gespeichert;
    jetzt eine passende Reaktion ohne Speichern. „the bus was late again“ (vorher „Anything I can help you with?“).
  - „my birthday is on may 3rd“ (vorher „Noted: may.“) → Geburtstag, im Format wie geschrieben („3 May“ bleibt „3 May“,
    team-0067-Dev-Antwort unverändert). „my best friend is called jonas“ → „Jonas“ großgeschrieben.
  - Deutsch: Allergie, „ich habe zwei kinder“, Geburtstag, „ich wohne mit meiner freundin zusammen“ werden gespeichert und
    in „was weißt du über mich?“ deutsch ausgegeben; Kaffee, eingeschlafene Mama, Anruf vom Papa, Zugverspätung bekommen
    eine Reaktion (vorher „Erzähl ruhig mehr!“ bzw. „Und wie war's?“).
  - Die erste Fassung las „I just had a long day at work“ als Essen (ein alter Test schlug an); die Regel verlangt jetzt
    höchstens drei Wörter ohne Präposition oder Zeit- und Ereigniswort.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 764 bestanden, Regressionen 32, 38–73 (41 Gespräche):
    0 Wiederholungen; Unterschiede: Batterie 42 (Besuch der Schwester ohne Speichern), 45 (Geburtstag), Uhrzeiten.
- **Alltags-Batterie 74 (Folgefragen über mehrere Turns; EN + DE)**:
  - „explain it simpler“ nach „what is photosynthesis?“ (vorher „I don't know much about Photosynthesis simpler“) und „why is
    it important?“ (vorher „couldn't find anything about Photosynthesis“) → einfache Erklärung bzw. Bedeutung; 18 Schulbegriffe
    (Photosynthese, Schwerkraft, Evolution, Demokratie, Inflation, DNA, Schwarzes Loch, Klimawandel, Impfung …), auch direkt
    („explain vaccine simply“).
  - Mond: „has anyone been there?“, „who?“, „why did they stop going?“ (vorher dreimal „I don't know“ bzw. „who's they?“).
  - Stadt: „what's it famous for?“ nach „what's the capital of italy?“ meint Rom, nicht Italien (vorher „I don't know“) → ein
    Satz aus den ersten 40 Sätzen des Artikels („City of Seven Hills … Eternal City“); „when's the best time to go?“ für
    europäische Städte.
  - Hund: „what breed would you recommend?“ (vorher Artikel „What Would You Do? (2008 TV program)“), „i live in a small
    apartment“ (vorher „That's brilliant — you must be really happy!“), „what about a cat instead?“. Der vorhandene
    Katzen-Ablauf aus Batterie 47 bleibt (die erste Fassung überschrieb ihn, ein alter Test schlug an).
  - Deutsch: „erzähl mehr“ (vorher Rückfallantwort), „und wo?“ nach „wann ist er gestorben?“ → „Einstein starb in Princeton.“
    (vorher englisch), Hund/Rasse/kleine Wohnung/Katze.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 765 bestanden, Regressionen 32, 38–74 (42 Gespräche):
    0 Wiederholungen; Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 75 (praktische Alltagshilfe; EN + DE)**:
  - „what's a 20% tip on 45 dollars?“, „how much is 15% off 80?“ (vorher „I don't know“), „split 120 between 4 people“ (vorher
    „Mm-hm. What's on your mind?“), „the bill was 60 euros, split it between 3“ → Rechnung mit Währung; ohne Währung ohne „.00“.
  - „what if i don't have eggs?“ nach dem Pfannkuchen-Rezept zitierte nur den Schritt mit dem Ei; jetzt Ersatz (Banane,
    Apfelmus, mehr Milch und Backpulver); ebenso Milch, Butter, Backpulver, Zucker, Mehl – nur wenn das Rezept sie enthält.
  - „no cooking please“ → vorher „That's fine, you won't need cooking please for those.“; jetzt Ideen ohne Kochen.
  - Deutsch: „rechne 5 meilen in km um“ (vorher „Oh? Go on.“) → „5 Meilen = 8,047 km.“, „wie viel trinkgeld bei 45 euro?“
    (vorher „kann ich nicht nachschlagen“), Rabatt und Teilen, „schreib meinem chef, dass ich krank bin“ (vorher als Ärger
    mit dem Chef gelesen: „Was hat deinem Chef denn diesmal angestellt?“) → Krankmeldung zum Kopieren, „ohne kochen“.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 766 bestanden, Regressionen 32, 38–75 (43 Gespräche):
    0 Wiederholungen; Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 76 (Ironie, Sarkasmus, knappe Antworten; EN + DE)**:
  - Schwere Fehlgriffe auf Deutsch: „na toll, schon wieder regen“ → „Toll zu hören! Was hat deinen Tag so gut gemacht?“ und
    „super, mein auto ist kaputt“ → „Müdigkeit ist fies“ (das Gefühl „müde“ fing jedes „kaputt“ ab). „kaputt“ zählt jetzt nur
    in „ich bin kaputt“; ironisches „na toll / super / klasse“ vor Regen, Kaputtem, verpasstem Zug und „mehr Arbeit“ wird als
    Ärger erkannt. „naja, nicht so ganz“ nach „mir gehts gut“ (vorher Rückfallantwort) → nachfragen.
  - Englisch: „just perfect, i missed my train“ (vorher „What went wrong with your train?“), „oh wonderful, my car broke down“,
    „yay, more work“, „love that for me“ (vorher als Fakt gespeichert), „i'm fine.“ / „no really, i'm fine“ / „ok maybe not
    totally fine“ (vorher „Nice! What can I do for you today?“ und „How's that going?“), „are you dumb?“ (vorher „I don't
    know — I haven't read anything“). Die erste Fassung antwortete auch auf „you're useless“ mit „Sometimes, I know!“
    (team-0016 im Dev-Satz änderte sich) – zurückgenommen, nur die Frage „are you dumb?“ bekommt diese Antwort.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 767 bestanden, Regressionen 32, 38–76 (44 Gespräche):
    0 Wiederholungen; Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 77 (dritte Wissensstichprobe: 40 neue feste Fragen, EN + DE)**: erster Lauf 19 richtig, **1 falsch**,
  20 „weiß ich nicht“. Der Fehler: „which country has the most people?“ → „Nigeria has the most people.“ (Textsuche; die
  Superlativ-Logik kannte die Formulierung nicht). Die Superlativ-Logik versteht jetzt „which country has the most people“;
  ihr Datenstand (Ende 2022) sagt aber China – seit 2023 ist es laut UN-Schätzung Indien, deshalb ein Standardfakt mit
  diesem Hinweis (EN + DE). Ergänzt: erste Nobelpreisträgerin, Evolution, größtes Säugetier, heißester und sonnennächster
  Planet, Lichtlaufzeit Sonne–Erde, Beginn des Ersten Weltkriegs, erster (Bundes-)Kanzler, längster Fluss Deutschlands,
  Flugzeug, „Entdeckung“ Amerikas (mit Hinweis auf indigene Völker und Leif Erikson), US-Bundesstaaten, Minuten pro Tag;
  Deutsch: Glühbirne, Bundesländer, Kilimandscharo, Oktopusherzen, Merkur, Gepard, Zweiter Weltkrieg. Bewusst offen:
  „most populous city“ (je nach Definition Tokio, Delhi oder Chongqing). Endstand: 40 richtig, 0 falsch, 0 offen;
  Batterien 71/72 danach unverändert (39/0/1, 38/0/2). Zusammen 120 feste Wissensfragen: 117 richtig, 0 falsch, 3 offen.
  Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 768 bestanden, Regressionen 32, 38–76: 0 Wiederholungen;
  Unterschiede nur Uhrzeiten. Skript: `scratchpad/kq77.py`.
- **Alltags-Batterie 78 (ein ganzer Abend in einem Gespräch, 24 Turns Englisch, 19 Turns Deutsch)**:
  - „i'm good, a bit tired. you?“ → die Antwort auf „you?“ stand am Ende („… early night? I'm good, thanks!“); jetzt vorne.
  - „how old is the eiffel tower?“ (vorher „I don't know for sure“) → aus dem Baujahr berechnet: „about 137 years old — it was
    completed in 1889“ (mit der Uhr des Rechners; auch deutsch „wie alt ist der eiffelturm?“); „how long does chicken take
    in the oven?“, „my manager changed the deadline again“.
  - „do you like paris?“ (vorher Artikelanfang mit „I don't have opinions“), „i was there last year“ (vorher als Fakt
    gespeichert), „the food was amazing“ (vorher „Noted: amazing — yum!“); „any recommendations?“ nach „i'll watch a movie
    later“ (vorher „I try not to have opinions“) → Filmtipps, „something funny“ → Komödien statt eines Witzes.
  - Deutsch: „gut, bisschen müde. und dir?“ (vorher nur „Müdigkeit ist fies“), „egal, was soll ich heute essen?“ (vorher
    Rückfallantwort – „egal,“ vorne störte), „was mit hähnchen“, „warst du schon mal in paris?“, „ich war letztes jahr dort“,
    „das essen war super“, Filmabend mit Tipps (vorher „Zerleg es: Was ist der allernächste kleine Schritt?“).
  - Das neue Abschneiden von „naja,“ machte aus „naja, nicht so ganz“ (Batterie 76) eine Rückfallantwort – ein Test schlug
    an; „nicht so ganz“ nach „mir gehts gut“ wird jetzt erkannt.
  - Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 769 bestanden, Regressionen 32, 38–78 (45 Gespräche):
    0 Wiederholungen; Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 79 (40 neue Einzelnachrichten, wie echte Nutzer sie schicken; EN + DE)**: erster Lauf mit groben Fehlern:
  „my phone screen cracked“ → „Got it, your favourite colour is cracked.“, „i burned the toast“ → „Toast — good choice!“,
  „ich vermisse meine oma“ → „Natürlich vermisst du meine oma.“ (Pronomen nicht umgestellt), dazu als Fakten gespeichert:
  „i miss my grandma“, „my cat knocked over my coffee“, „my neighbors are so loud“ („How's that going?“), „i'm stuck in
  traffic“; „can you keep a secret?“ → Textsuche; deutsch Rückfallantworten für Handy, Nachbarn, Stau, Sinn des Lebens,
  „sag mir was nettes“, Geheimnis, „bin wieder da“. Alle 40 bekommen jetzt eine passende Antwort; „meine Oma“ → „deine Oma“
  (mit „sie“). Die erste Fassung überschrieb drei vorhandene, bessere Abläufe (Gitarre lernen mit Folgefragen, Führerschein
  mit „beim ersten Mal“, Trennungsrat nach „ich vermisse …“) – von den Batterien 41, 54 und long gefunden, zurückgenommen.
  Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 770 bestanden, Regressionen 32, 38–79 (46 Gespräche):
  0 Wiederholungen; Unterschiede: „i miss him/her“ jetzt Mitgefühl statt gespeicherter Fakt (Batterie 64, long), Uhrzeiten.
- **Alltags-Batterie 80 (Zustände von Dingen: „my X is ADJ“)**: Der Fehler „screen cracked“ → Lieblingsfarbe war kein Einzelfall.
  Vorher: „my car is dirty“ → „A dirty, nice! I'll remember that.“, „my soup is too salty“ → „Salty — good choice!“,
  „my eyes are blue“ → „Got it, your favourite colour is blue.“, „my plant died“ → „How's that going?“, „my wifi is down“,
  „my laptop is slow“, „my shoes are wet“ → „Oh, interesting — tell me more.“ (alles gespeichert). Jetzt erkennt ein
  allgemeiner Handler den Zustand: konkrete Hilfe, wo es eine gibt (Router neu starten, Tabs schließen, Kartoffel in die
  versalzene Suppe, Zeitungspapier in nasse Schuhe, Diebstahl melden), sonst Mitgefühl; Farben („Blue eyes — nice!“)
  werden nicht zur Lieblingsfarbe. Schmerzen (Zahn, Rücken, Bauch) mit Rat, Brustschmerz mit dem Hinweis auf den
  Notruf (112/911). Kopfschmerz bleibt beim vorhandenen Ablauf mit Folgefragen (Batterie 48 fand, dass die erste Fassung
  ihn überschrieb). Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 771 bestanden, Regressionen 32, 38–80
  (47 Gespräche): 0 Wiederholungen; Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 81 (Zustände von Dingen auf Deutsch)**: vorher fast alles Rückfallantworten („Interessant – wie ging's
  weiter?“, „Okay! Und wie war's?“) – darunter **„mir tut die brust weh“ → „Das ist blöd. Was ist passiert?“**. Jetzt: kalter
  Kaffee, langsamer Laptop, WLAN (Router neu starten), versalzene Suppe, eingegangene Pflanze, nasse Schuhe, Unordnung,
  geklautes Fahrrad (Polizei, Versicherung), Zahn-, Rücken-, Bauchschmerzen mit Rat, Brustschmerz mit Notruf 112. Farben
  ohne geratene Grammatik („Rot – schöne Farbe!“ statt „Roter Auto“). „mein auto ist kaputt“ bleibt beim Ironie-Ablauf aus
  Batterie 76 (die erste Fassung fing es ab). Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 772 bestanden,
  Regressionen 32, 38–81 (48 Gespräche): 0 Wiederholungen; Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 82 (Ereignisse in der Ich-Form, 20 EN + 14 DE)**: vorher u. a. „i quit smoking“ → „Smoking — good
  choice! I'll remember that.“, „i locked myself out“/„i cut my finger“ → „Oh, interesting — tell me more.“, „i forgot my
  umbrella“ → „What went wrong with your umbrella?“, „i overslept“/„i'm moving next month“ → „How's that going?“ (gespeichert);
  deutsch fast nur Rückfallantworten, „ich hab mein portemonnaie verloren“ → „Was war denn so schwierig daran?“. Jetzt eine
  Tabelle aus Muster, Antwort und Stimmung (EN + DE) mit konkreter Hilfe, wo sie passt (Karten sperren 116 116,
  Ersatzschlüssel, Wunde versorgen, Kaffeefleck), Glückwunsch bei guten Nachrichten. Vorhandene gute Antworten (Beförderung,
  Verlobung, Prüfung, Erkältung auf Englisch) bleiben. Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 773
  bestanden, Regressionen 32, 38–82 (49 Gespräche): 0 Wiederholungen; Unterschiede nur Uhrzeiten.
- **Sicherheitsnetz für Bestätigungen (Batterie 83)**: Die Fehler „good choice“/„lovely colour“/„A dirty, nice!“ hatten eine
  gemeinsame Wurzel: Der Wert eines Satzes wurde nach seiner Art getippt („salty“ → Essen), und die Bestätigung nannte die
  Kategorie, auch wenn der Satz gar keine Vorliebe ausdrückt. Kategorie-Bestätigungen (Essen, Farbe, Auto, Vorliebe) kommen
  jetzt nur, wenn der Satz ein passendes Wort enthält („like/love/favourite/eat/drive …“); sonst die neutrale Bestätigung.
  „my tea is lukewarm“, „my pizza arrived late“ → keine Vorliebe; „i love sushi“, „pizza is my favourite food“, „my favourite
  colour is green“, „i drive a tesla“ unverändert. Messung: Team-Dev-Satz 1 von 128 (team-0067), NQ 22/9, Suite 774 bestanden
  (die eine Abweichung im ersten Lauf war die Prüfung selbst: „Noted: pizza — yum!“ ist eine gleichwertige Variante),
  Regressionen 32, 38–83 (50 Gespräche): 0 Wiederholungen; Unterschiede nur Uhrzeiten.
- **Alltags-Batterie 84 (zweite Verallgemeinerungsprobe: 40 neue Einzelnachrichten, EN + DE)**: vorher u. a. „i'm going to a
  concert tonight“ → „I'll remember that you work as a concert.“, „ich hasse meinen job“ → „Notiert: Meinen Job – lieber
  nicht.“ (als Abneigung gespeichert), „i just woke up“/„i'm at the gym“ → „tell me more“, „what should i name my cat?“ →
  Rückfrage „Is it a dog, a cat …?“, deutsch viele Rückfallantworten (Konzert, aufgewacht, Fitnessstudio, Abschlussarbeit,
  Baby, KI, Lernhilfe, Motivation, Urlaub mit „Und wie war's?“). Alle bekommen jetzt passende Antworten (Ereignistabelle
  erweitert). Grundfehler gefunden: Die Tippfehler-Korrektur machte aus „snowing“ „showing“ – gültige Beugungen bekannter
  Wörter (snow + ing, bake + d …) werden nicht mehr „korrigiert“, echte Tippfehler („interveiw“) weiterhin. Die erste Fassung
  fing zwei vorhandene Abläufe ab (Hausaufgaben mit Fach-Rückfrage, „hat sich verlobt“ mit Trauzeugin-Folgefragen) – von
  zwei alten Tests gefunden, zurückgenommen. Release: beta.23 hing beim Herunterladen der Paket-Artefakte (kein Zeitlimit,
  Standard 6 Stunden); der Reuse-Job hat jetzt 20 Minuten Zeitlimit, beta.23 ist erneut angestoßen. Messung: Team-Dev-Satz
  1 von 128 (team-0067), NQ 22/9, Suite 775 bestanden, Regressionen 32, 38–84 (51 Gespräche): 0 Wiederholungen;
  Unterschiede nur Uhrzeiten.
- **Wissens-Batterie 85 (vierte Stichprobe: 40 neue Allgemeinwissensfragen, EN + DE, `scratchpad/kq85.py`)**: Der
  erste Lauf ergab 12 richtig, 4 falsch und 24 offen. Falsch waren unter anderem:
  - „who painted the last supper?“ → Tintoretto (zwei Maler mit gleichnamigem Werk; es gewann der zuerst gefundene);
  - „father of computers“ → Peirce (ein Name aus einem fremden Satz).

  Korrekturen:
  - **Werk-Urheber (`_made_by`)**: Der Abgleich nimmt auch „the“ + Werk. Bei mehreren Kandidaten antwortet nur ein
    mindestens doppelt so bekannter, sonst gibt es keine Antwort. Der Titel steht jetzt so da, wie ihn die Faktenbank
    schreibt („The Starry Night“, nicht „Starry night“).
  - **Plausibilitäts-Wächter**: „father/mother/founder … of X“ verlangt X im Beleg.
  - **Abkürzungen**: Die Tippfehler-Korrektur machte aus „dna“ „dan“. Eine feste Liste gängiger Abkürzungen (dna,
    nasa, gps, …) wird nicht mehr „korrigiert“.
  - **„what does X stand for?“** ohne Artikel fällt auf die geprüften Alltagsfakten zurück.
  - **Alltagsfakten**: 20 EN- und 9 DE-Einträge (u. a. Abendmahl, DNA, Babbage, Marsmonde, Grönland, Augustus).
  - **Pronomen „he … it“**: Nach „who painted the starry night?“ verwies „it“ in „when did he paint it?“ ins Leere,
    und die Textsuche antwortete mit 1881 (falsch). Jetzt bleibt das Werk Gesprächsgegenstand: „he“ ist der Maler,
    „it“ das Bild. Die Alltagsfakten werden auch mit der aufgelösten Frage geprüft (Juni 1889, MoMA).
  - **Team-Dev**: team-0087 („Who painted The Starry Night?“) wird jetzt beantwortet (van Gogh), vorher „I don't know“.

  Ergebnis: Stichprobe 85 hat 39 von 40 richtig und 0 falsch. Die eine Abweichung ist die Teleskop-Frage: Die Antwort
  ist inhaltlich richtig, aber die Faktenbank schreibt „Lippershay“, deshalb greift der Prüfausdruck nicht. Die
  früheren Stichproben stiegen ebenfalls:

  | Stichprobe | vorher | jetzt |
  |---|---|---|
  | 71 | 39 | 40 |
  | 72 | 38 | 39 |
  | 77 | 40 | 40 |

  Die Testumgebung (/dev/shm) ging bei einem Container-Neustart verloren. Paket und Vergleichsstand wurden neu
  aufgebaut: Der Vergleich läuft jetzt gegen den letzten Commit (Worktree) statt gegen die alte Runde-40-Ausgabe.

  Messung: Team-Dev-Satz 1 von 128 geändert (team-0087, besser). NQ 22/9. Suite 777 bestanden.
  Regressionen 32 und 38–84 (54 Gespräche): 0 Wiederholungen. Unterschiede gibt es nur im Gemälde-Gespräch (b56,
  vorher viermal „weiß nicht“/Rückfrage, jetzt viermal richtig) und bei den Uhrzeiten.
- **Alltags-Batterie 86 (zehn natürliche Mehrschritt-Gespräche, EN + DE: Langeweile, schlechter Tag mit dem Chef,
  neuer Hund, Smalltalk über den Bot, Eiffelturm-Folgefragen, Programmieren lernen)**. Vorher gab es grobe Aussetzer:

  | Eingabe | vorher |
  |---|---|
  | „what was her name again?“ (nach „her name is luna“) | Namensvorschläge für den Welpen |
  | „what kind of dog do i have?“ | „Yeah it wasn't even your fault.“ |
  | „and when was it built?“ (nach der Eiffelturm-Höhe) | „weiß nicht“, auf Deutsch dagegen richtig |
  | „python probably“ | „Ooh, python probably. How did it go?“ |
  | „are you smarter than me?“ | „I don't know that about you yet“ |
  | „i work at a bakery“ | „you work at bakery“ |
  | „i work for myself“ | „you work at myself“ |

  Auf Deutsch fielen „einen labrador“, „er heißt bruno“, „wie heißt mein hund?“, „hast du eine idee?“ (nach dem
  Ideen-Angebot), „vielleicht ein buch. was empfiehlst du?“ und „soll ich was sagen?“ alle in die Rückfallantwort.
  „du hast recht“ nach einem Rat bekam „Das macht es natürlich nicht leichter.“, „Ein Katze“ und „ein Perserkatze“
  waren falsche Artikel.

  Gefundene Grundfehler:
  1. „and when …?“ wurde als Ellipse gelesen („And of Germany?“) und zu „how tall is the when was Eiffel Tower
     built?“ umgebaut. Eine Ellipse beginnt jetzt nie mit einem Fragewort.
  2. Die Suche in den eigenen Sätzen antwortete schon bei bloßer Bedeutungsähnlichkeit. Jetzt ist mindestens ein
     gemeinsames Wort oder Konzept Pflicht.

  Neu:
  - Haustier-Gedächtnis mit Name, Rasse und Geschlecht in EN und DE (deutsche Artikel nach Tier und Rasse);
  - Programmieren-lernen-Ablauf (Sprache, schwer?, wie lange?, Einstieg, Projekte);
  - „are you smart(er than me)?“;
  - Zustimmung nach einem Rat an einem schlechten Tag (EN/DE);
  - Selbstständigkeit und Homeoffice als Ereignisse;
  - Firmen- und Artikelform in der Bestätigung („at a bakery“, „Google“);
  - „how old is it?“ nach einem Bauwerk;
  - geprüfte Fakten, die vor der Faktenbank gelten (`pre`, hier: Wer hat den Eiffelturm entworfen? Die Faktenbank
    nennt nur den Architekten), mit deutschem Text (`de`).

  Messung: Team-Dev-Satz 0 von 128 geändert, NQ 22/9, Suite 780 bestanden. Regressionen 32 und 38–86
  (55 Gespräche): 0 Wiederholungen. Unterschiede gegen den letzten Commit:
  - Eiffelturm-Entwurf in b38, b41, b56 und b69;
  - b45: „you're right“ nach Trennungsrat, vorher „Glad I got that right!“;
  - Datums- und Uhrzeitzeilen (Tageswechsel während des Laufs).
- **Alltags-Batterie 87 (zehn weitere Mehrschritt-Gespräche, EN + DE: Korrekturen, „y?“, Folgefragen zu Jupiter,
  Nachbarn, Carbonara, Canberra, Fahrprüfung)**. Vorher gab es grobe Fehler:

  | Eingabe | vorher |
  |---|---|
  | „no wait, i'm 35“ → „how old am i?“ | „You're 34.“ |
  | „y“ (= why) | Wikipedia-Artikel über den Buchstaben Y, danach wurde „Y“ zum Thema („K. Bhagyaraj directed Y.“) |
  | „thanks, i feel a bit better“ | „You're welcome! That makes it even harder.“ |
  | „what's the biggest planet?“ | weiß nicht |
  | Folgefragen zu Carbonara, „why not sydney?“, Fahrprüfung, Nachbarn | weiß nicht bzw. unpassender Rat |
  | deutsch „carbonara“ | englischer Wikipedia-Text |
  | „soll ich sie ansprechen?“, „ja vielleicht morgen“ | Rückfallantwort |
  | Namen | kleingeschrieben („Your name is tom.“) |

  Grundfehler:
  1. Ein Korrektur-Vorspann („no wait,“, „actually“, „oops,“) machte aus „i'm 35“ eine Tatsache ohne Kategorie,
     und bei gleichen Punkten entschied die Satz-ID statt der Reihenfolge. Jetzt fällt der Vorspann weg, und bei
     einwertigen Kategorien (Alter, Name, Wohnort, Beruf, Arbeitgeber, Geburtstag) gilt die spätere Aussage.
  2. Ein einzelnes „y“ wird jetzt als „why“ gelesen.

  Neu:
  - „it's thomas, but everyone calls me tom“;
  - nach „have you seen/read X?“ ist X das Gesprächsthema („who wrote it?“ → Tolkien);
  - Jupiter mit Folgefragen (warum so groß, Monde, bewohnbar, Mars);
  - Carbonara (Sahne?, Originalrezept, „sounds good“), und „i'm cooking tonight“;
  - Canberra statt Sydney (mit deutschem Text);
  - Fahrprüfung (Einparken, Nervosität, Wiederholung);
  - „i feel a bit better“;
  - laute Nachbarn in der Vergangenheit (EN/DE: ansprechen?, morgen).

  Die deutsche Pasta-Erweiterung lief zuerst als eigener Ablauf und fing den vorhandenen aus Batterie 70 ab (der
  alte Test „Klassisch nein“ fand das). Sie ist jetzt in den alten Ablauf eingebaut („ich mach heute pasta“,
  „kommt da sahne rein?“, Originalrezept). Die erste Fassung der Nachbarn-Regel nahm auch die Gegenwart („my
  neighbors are so loud“) und verdrängte dort die bessere Rückfrage; sie gilt jetzt nur für die Vergangenheit.
  „did you watch the game?“ macht aus „the game“ keinen Titel.

  Offen: „Inception“ fehlt im Lite-Paket (150.000 Einträge). Mit dem Standard-Paket ist er vorhanden.

  Messung: Team-Dev-Satz 1 von 128 geändert (team-0077, Jupiter-Antwort ausführlicher). NQ 22/9, Suite 782
  bestanden. Regressionen 32 und 38–87 (56 Gespräche): 0 Wiederholungen.
- **Alltags-Batterie 88 (zehn deutsche Mehrschritt-Gespräche)**. Vorher war Deutsch deutlich schwächer als
  Englisch:

  | Eingabe | vorher |
  |---|---|
  | „28“, „italienisch“ (Kurzantworten in einem deutschen Gespräch) | englische Antworten („Oh? Go on.“, „Ooh, italienisch. How did it go?“) |
  | „ich will abnehmen“, „so 5 kilo“ | englisch erkannt („will“ zählte als englisches Wort) |
  | „okay der war schlecht 😂“ nach einem Witz | „Das klingt schwer. Magst du erzählen, was passiert ist?“ |
  | „okay, mach ich“ (zum Tierarzt) | „Viel Spaß dabei! 😊“ |
  | „hi, ich bin lena“, „mein chef will alles bis freitag“ / „ich weiß nicht wie ich das schaffen soll“, „warst du schon mal da?“, „als marketing managerin“, „hat er den nobelpreis bekommen?“, „eher was draußen“ / „es soll regnen“, Geburtstag mit „wir gehen essen“ / „italienisch“ | Rückfallantworten |

  Neu:
  - Kurzantworten ohne englisches Wort bleiben in einem deutschen Gespräch deutsch;
  - weitere Erkennungswörter;
  - Name mit Begrüßung;
  - Geburtstags-Ablauf (Alter wird gemerkt);
  - Abnehmen (Ziel mit Wochenrechnung bei einem halben Kilo pro Woche, Essen, Sport);
  - Witz-Kritik;
  - Arbeitsdruck mit Rat;
  - „warst du schon mal da?“ mit dem Ort aus dem Gespräch;
  - Rolle nach dem Vorstellungsgespräch;
  - Nobelpreis (Einstein, Curie) als geprüfte Fakten mit Pronomen, EN und DE;
  - krankes Haustier (frisst nicht → Tierarzt; „mach ich“ → gute Besserung);
  - Ideen für draußen und bei Regen (EN und DE).

  Die erste Fassung der Reise-Regel nahm auch „warst du schon mal in paris?“ und verdrängte den Ablauf aus
  Batterie 78 samt Folgefrage („ich war letztes jahr dort“). Der alte Test fand das. Die Regel gilt jetzt nur für
  „da/dort“ und setzt denselben Folgezustand.

  Messung: Team-Dev-Satz unverändert gegenüber Batterie 87. NQ 22/9, Suite 783 bestanden. Regressionen 32 und
  38–88 (57 Gespräche): 0 Wiederholungen. Unterschiede gegen den Stand vor Batterie 86 nur wie bei 86/87
  dokumentiert und bei Uhrzeiten.
- **Alltags-Batterie 89 (zehn englische Mehrschritt-Gespräche: Mehrfachfragen, Ironie, Trauer, Zusage, Erinnerung,
  Pfannkuchen, Schlaflosigkeit, Telefon-Erfinder, Spanisch lernen, Beleidigung)**. Vorher u. a.:

  | Eingabe | vorher |
  |---|---|
  | „remind me to call mom tomorrow“ | als Name gespeichert, später „Good morning, mom tomorrow!“ |
  | „i'm a beginner“ | „I'll remember that you work as a beginner.“ |
  | „what do i have to do tomorrow?“ | weiß nicht, obwohl die Notiz da war |
  | „she was 91“ nach der Oma | „that's a lot of years of friendship“ |
  | „a bit nervous but mostly excited“ | „That's a shame.“ |
  | „can i use oat milk?“ | „Yep, it's in there: … milk“ |
  | „was he american?“ nach dem Telefon | dreimal dieselbe Rückfrage, welcher der vier Erfinder gemeint ist |
  | „how do you say thank you?“ beim Spanischlernen | weiß nicht |

  Neu:
  - „call“ als Anrufen („to call mom“, „call the bank“) ist kein Name;
  - Wörter wie beginner, fan, morning person, vegetarian sind kein Beruf;
  - Notizen für morgen, heute Abend und diese Woche;
  - Trauer mit Familienwort (ihr/sein Leben, Erinnerung an ihr Kochen);
  - gemischte Gefühle;
  - Ersatzzutaten und Portionen in Anleitungen;
  - Schlaflosigkeit (Grübeln, Arbeit, Lesen);
  - langweilige Arbeit mit Tipps;
  - Staunen nach großen Zahlen;
  - „you didn't understand me“;
  - Grundwörter in sechs Sprachen (Spanisch, Französisch, Italienisch, Deutsch, Portugiesisch, Niederländisch);
  - Ja/Nein-Fragen zur Nationalität aus der Faktenbank;
  - bei mehreren Personen gilt eine deutlich bekanntere als gemeint („The best known of them is Alexander Graham
    Bell.“, danach „he“ = Bell).

  Panne beim Einbau: Eine Ersetzung mit einem Anker, der zweimal in der Datei vorkam, verdoppelte rund 5.100 Zeilen
  von dialog.py. Bemerkt wurde das am Diff (+5.124 Zeilen). Die Datei wurde aus den Teilstücken exakt
  wiederhergestellt (Syntax geprüft, nur die beabsichtigten 23 Zeilen geändert), bevor etwas committet wurde.

  Messung: Team-Dev-Satz 2 von 128 geändert (team-0067 Telefon mit „best known“, team-0077 Jupiter). NQ 22/9,
  Suite 785 bestanden. Regressionen 32 und 38–89 (58 Gespräche): 0 Wiederholungen. Weitere Unterschiede: Telefon-
  Folgefragen in b56, b56d, b56de und b56f (jetzt Bell statt Rückfrage), b69 („merci“ über die neue Wortliste statt
  das Übersetzungswerkzeug, gleicher Text), Uhrzeiten.
- **Wissens-Batterie 90 (fünfte Stichprobe: 40 neue Allgemeinwissensfragen, 30 EN + 10 DE, Prüfausdrücke vor dem
  Lauf festgelegt, `scratchpad/kq90.py`)**: erster Lauf 36 richtig, 0 falsch, 4 offen. Offen waren „what planet is
  known as the red planet?“ (EN und DE), „was ist das größte säugetier?“ und „wie viele kontinente gibt es?“ (DE).
  Ergänzt wurden geprüfte Fakten (Mars mit Begründung, Blauwal, sieben Kontinente mit Hinweis auf andere Zählweisen).
  Danach 40/0/0.

  Bei der Gegenprobe der früheren Stichproben blieben zwei Punkte offen und sind jetzt behoben:
  - „who is the ceo of tesla?“ (72) beantwortet jetzt ein geprüfter Fakt mit „(as of my data)“.
  - Die Teleskop-Frage (85) schrieb den Erfinder falsch („Lippershay“ aus der Faktenbank). Jetzt antwortet ein
    geprüfter Fakt vor der Faktenbank: Lipperhey/Lippershey 1608, Metius und Janssen, Galileo 1609. Auf Deutsch
    kennt die Brücke jetzt „Fernrohr“ und „Teleskop“.

  Stand aller fünf Stichproben:

  | Stichprobe | richtig | falsch | offen |
  |---|---|---|---|
  | 71 | 40 | 0 | 0 |
  | 72 | 40 | 0 | 0 |
  | 77 | 40 | 0 | 0 |
  | 85 | 40 | 0 | 0 |
  | 90 | 40 | 0 | 0 |

  Das sind keine unabhängigen Tests mehr: Die Lücken wurden auf genau diesen Fragen geschlossen. Sie zeigen, dass
  nichts zurückfällt; die Erstläufe (39/38/40/12/36 richtig) sind das ehrlichere Maß für neue Fragen.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 786 bestanden. Regressionen 32 und 38–89 (58 Gespräche):
  0 Wiederholungen, Unterschiede wie bei 89.
- **Grenzfall-Batterie 91 (Emojis, Tippfehler, dreimal dieselbe Frage, Sprachwechsel auf Wunsch, Ein-Wort-Nachrichten,
  lange Erzählung, Witz-Serie, Bot-Gefühle, Uhrzeit/Datum, Ratlosigkeit)**. Vorher u. a.:

  | Eingabe | vorher |
  |---|---|
  | „hwo are yuo“ | zu „who are you“ korrigiert, daher die Namensantwort |
  | „thnks“ | nicht als Dank erkannt |
  | dreimal „what is the capital of italy?“ | dreimal wortgleich dieselbe Antwort |
  | „can we speak english?“ | weiß nicht |
  | „können wir wieder deutsch reden?“ | nicht verstanden |
  | „ok last one“ (Witze), „something else“ (Fakten) | „Oh? Go on.“ |
  | „what day is it tomorrow?“ | weiß nicht |
  | „what was the date yesterday?“ | „December 7, 1941 was the date yesterday.“ (Textsuche) |
  | „what is the day after tomorrow?“ | „2004 is the day after tomorrow.“ (der Film) |

  Neu:
  - Liste häufiger Tastatur-Vertipper, die vor der Wörterbuchnähe gilt (hwo → how, teh → the, captial → capital …);
  - weitere Chat-Kürzel für Danke;
  - dieselbe Frage direkt wiederholt: „Still the same answer: …“, beim dritten Mal „That's the third time you've
    asked 😄 — …“, auf Deutsch „Immer noch dasselbe: …“. Kleingeschrieben wird nur ein Funktionswort am Anfang,
    nie ein Name wie „Faust“;
  - Sprachwechsel auf Wunsch (EN ↔ DE), der den Gesprächszustand umstellt;
  - „last one“, „something else“, „hit me again“ zählen als „noch eins“;
  - Datum für morgen, gestern und übermorgen;
  - Vorschläge bei „i don't know what to ask“.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 787 bestanden. Regressionen 32 und 38–89 (58 Gespräche):
  0 Wiederholungen, Unterschiede wie bei 89.
- **Wissens-Batterie 92 (zehn deutsche Wissensgespräche mit Folgefragen)**. Vorher gab es 21 Rückfallantworten
  und einen groben Fehler: „wer hat amerika entdeckt?“ → „Amerika wurde von Junior M.A.F.I.A entdeckt.“ „Amerika“
  wurde als „United States“ übersetzt, und die Textsuche fand ein Rap-Album. Der englische Pfad kannte die
  meisten Antworten; die deutsche Brücke war der Engpass.

  Behoben:
  - „Amerika“ beim Entdecken ist der Kontinent;
  - „wann war das?“ ist kein Todesdatum mehr;
  - Folgefragen geprüfter Fakten gelten auch auf Deutsch (eigene deutsche Muster und Texte): Kolumbus wann/woher,
    Mond (Lichtlaufzeit, wer war dort, wer zuerst);
  - deutsche Fakten können auf den englischen Eintrag verweisen, damit dessen Folgefragen greifen;
  - „sie/er“ für Dinge ist „it“ („wo hängt sie?“, „wie groß ist sie?“ nach der Mona Lisa: Louvre, 77 × 53 cm);
  - „er“ bleibt die Person, auch wenn die letzte Antwort ein Ort war (Goethe → Weimar → „was hat er
    geschrieben?“);
  - „und die zugspitze?“ übernimmt den Artikel richtig;
  - „wo liegt die?“, „seit wann?“ (Merz, 6. Mai 2025, Stand meiner Daten), „welche partei?“ (CDU, deutsche
    Parteinamen);
  - „welche sprache spricht man dort?“, „und welche währung?“ (Yen großgeschrieben);
  - Alter der Erde;
  - „was ist photosynthese/demokratie/ein schwarzes loch?“: Aus dem deutschen Fachwort wird die englische Form
    abgeleitet (-ese → -esis, -kratie → -cracy, -ik → -ics …), und der Rückfall „who is …“ entfällt für „was ist“;
  - Prozent-Ellipse („und 20 prozent von 150?“);
  - Quadratwurzel;
  - „wann ist weihnachten?“ und „wie viele tage noch?“;
  - „was schenkt man so?“;
  - deutsche Titel bekannter Werke („Die Leiden des jungen Werthers“, „Die Wahlverwandtschaften“).

  Ein neuer Fehler beim Einbau: Optionale Gruppen in den neuen Brückenregeln („seit wann?“ ohne Person) ließen die
  Brücke abstürzen. Das fiel im ersten Probelauf auf. Fehlende Gruppen gelten jetzt als „er“, und ein Test prüft
  das.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 788 bestanden. Regressionen 32 und 38–92 (60 Gespräche):
  0 Wiederholungen, Unterschiede wie bei 89.
- **Deutsche Verallgemeinerungsprobe (Batterie 93: 30 neue deutsche Einzelfragen, vorher nicht angefasst,
  Prüfausdrücke vor dem Lauf festgelegt, `scratchpad/kq93.py`)**: erster Lauf **23 richtig, 2 falsch, 5 offen**.
  Die Brückenverbesserungen aus Batterie 92 trugen also teilweise auch auf unbekannte Fragen. Falsch waren:
  - „wann wurde die berliner mauer gebaut?“ → „Berlin Wall was built in 1989.“ Die Textsuche nahm das Jahr des
    Mauerfalls; die englische Frage ohne Artikel umging die Vorsicht.
  - „wo liegt der kilimandscharo?“ → „Kilimanjaro Region liegt in Tanzania.“ (Region statt Berg, englischer
    Ländername).

  Offen waren Sixtinische Kapelle, Planetenzahl, Marianengraben, Ende des Zweiten Weltkriegs und Dampfmaschine.

  Behoben:
  - Neuer Plausibilitäts-Wächter für „when was X built?“: Das Jahr muss nahe einem Bau-Wort stehen und darf nicht
    bei fiel/zerstört/abgerissen stehen. Am alten Stand nachgeprüft: Er kippt nur den falschen Fall.
  - Vokabular: Dampfmaschine, Sixtinische Kapelle, Marianengraben, Kilimandscharo, Erster/Zweiter Weltkrieg,
    Tansania, Kenia, Buchdruck, Flugzeug, Auto.
  - Neue Muster: „wann endete/begann X“, „wer hat X bemalt“.
  - Geprüfte Fakten mit deutschem Text: Mauerbau 13. August 1961; Sixtinische Kapelle: Michelangelo (Decke),
    Wandfresken von anderen; Dampfmaschine: Newcomen 1712, Watt ab 1769; Kilimandscharo in Tansania; acht
    Planeten.
  - Die Faktenbank nannte für die Sixtinische Kapelle nur Ghirlandaio. Jetzt gilt der geprüfte Fakt vorher.

  Danach 30/0/0, und alle anderen Stichproben bleiben bei 40/0/0.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 789 bestanden. Regressionen (60 Gespräche): 0 Wiederholungen,
  Unterschiede wie bei 89.
- **Englische Verallgemeinerungsprobe (Batterie 94: 40 neue Alltagsnachrichten, vorher nicht angefasst)**: erster
  Lauf ungefähr 28 von 40 passend. Schwach waren:

  | Eingabe | vorher |
  |---|---|
  | „i lost my keys“ | „What went wrong with your keys?“ |
  | „everything is going wrong today“ | „Okay! Is there something you'd like to know?“ |
  | „my best friend moved away“ | „Got it — I'll remember that about your friend.“ |
  | „i'm bored at work“, „i just woke up from a nap“ | „Ah, okay. How's that going?“ |
  | „it's my first day at a new job“ | „How are you going to celebrate?“ |
  | Tattoo, Kochen lernen, Welpe nächste Woche | „tell me more“ |
  | „can you recommend a podcast?“ | weiß nicht |
  | „tell me something cool about space“ | weiß nicht |

  Neu:
  - neun Einträge in der Ereignistabelle (Langeweile bei der Arbeit führt weiter zu den Tipps);
  - die Empfehlungs-Erkennung nimmt „can you …“ jetzt vor jeder Form, nicht nur vor der ersten;
  - Fun Facts nach Thema (Weltraum, Tiere, Meer, Körper, Geschichte, Wissenschaft, Essen, Natur).

  Die erste Fassung der Themenfakten nahm auch „something about history“. Nach einer Podcast-Empfehlung ist das
  eine Genre-Nachfrage; der alte Test aus Batterie 22 fand das. Jetzt muss „tell me/give me“ oder „fact“ dabeistehen.
  Danach etwa 39 von 40 (Bewertung von Hand, kein Prüfprogramm).

  Die Regression fand noch etwas: Die neue Zeile für verlorene Dinge verdrängte den besseren Geldbörsen-Eintrag
  („block your cards“). Sie gilt jetzt nur für Schlüssel und Brille. Telefon („Find my device“) und eine feste
  Liste von Gegenständen haben eigene Einträge. Eine offene Form „lost my X“ hätte „i lost my mom“ als verlegten
  Gegenstand behandelt; ein Test prüft, dass Trauer Trauer bleibt. Nachgetragen nach dem Commit: Die Liste enthielt
  „charger“ und verdrängte in b57 die kontextbezogene Antwort nach „my phone died“ („Of course it disappears now …
  Anyone you could borrow one from?“). „charger“ ist gestrichen, b57 ist wieder identisch.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 791 bestanden. Regressionen 32 und 38–94 (61 Gespräche):
  0 Wiederholungen, Unterschiede wie bei 89.
- **Deutsche Alltags-Verallgemeinerungsprobe (Batterie 95: 30 neue deutsche Einzelnachrichten, vorher nicht
  angefasst)**: erster Lauf ungefähr 14 von 30 passend. Grob falsch war „ich hab meinen schlüssel verloren“ →
  „Oh nein, das tut mir so leid. Magst du mir von ihm erzählen?“ (als Trauerfall gelesen). Sonst gab es viele
  Rückfallantworten und fehlende Empfehlungsformen: „was soll ich heute abend schauen?“, „kannst du mir einen
  podcast empfehlen?“, „was schenke ich meinem vater?“, „wie kann ich geld sparen?“.

  Neu in der deutschen Ereignistabelle: Schlüssel/Brille verloren, Tattoo, Essen angebrannt, Langeweile bei der
  Arbeit, beste Freundin weggezogen, Urlaub, Kochen lernen, alles geht schief, erster Arbeitstag, gekündigt,
  Nickerchen, Preis gewonnen. Dazu kommen deutsche Podcast-Empfehlungen (mit deutschen Podcasts; englische sind
  gekennzeichnet), Geldspar-Tipps sowie weitere Muster für Film und Geschenk. Danach ungefähr 29 von 30 (Bewertung
  von Hand).

  Die Regression fand eine doppelte Geldbörsen-Zeile, die den vorhandenen Eintrag verdrängte und mit „er“ für
  „das Portemonnaie“ grammatisch falsch war. Sie ist gestrichen, b82 ist wieder identisch.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 792 bestanden. Regressionen (62 Gespräche):
  0 Wiederholungen.
- **Alltags-Batterie 96 (Tiefe nach einem Moment: acht Gespräche, EN + DE)**. Die erste Antwort auf ein Ereignis
  passte, die Folgesätze danach nicht:

  | Eingabe | vorher |
  |---|---|
  | „it hurt a bit“ (Tattoo) | „Ooh, it hurt a bit. How did it go?“ |
  | „i missed the bus and spilled coffee on my shirt“ | „What went wrong with your shirt?“ |
  | „what if they don't like me?“ (erster Arbeitstag) | „I don't know that about you yet“ |
  | „ja, ich hab schon was neues“ (gekündigt) | „Das macht es natürlich nicht leichter.“ |

  Neu:
  - Einträge der Ereignistabelle können eigene Folgesätze tragen (Feld `f`, vier Turns lang, EN und DE): Tattoo,
    alles geht schief (Bus/Kaffee, Chef), erster Arbeitstag, Kündigung (neuer Job, Startup, Startmonat);
  - „Kündigung“ zählt auf Deutsch als großer, eher positiver Schritt;
  - Echo-Rückfragen nehmen bei negativen Wörtern (hurt, sad, annoying …) die passende Vorlage;
  - in Lesetexten fehlende Leerzeichen nach dem Punkt („in Italy.It is“) werden ergänzt.

  Die erste Fassung legte „i quit my job“ in die Ereignistabelle und fing damit den Gedächtnis-Ablauf ab, der den
  Beruf austrägt. Der alte Test fand das. Jetzt setzt die Zeile nur den Folgezustand; Antwort und Gedächtnis
  bleiben beim alten Ablauf.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 793 bestanden. Regressionen (63 Gespräche):
  0 Wiederholungen, Unterschiede wie bei 89.
- **Alltags-Batterie 97 (ein langes, realistisches Gespräch mit 25 Turns: Feierabend, Kuchen im Büro, Meeting,
  App-Projekt, Deadline, Abendessen)**. Vorher wirkte rund die Hälfte der Antworten generisch oder falsch:

  | Eingabe | vorher |
  |---|---|
  | „my colleague brought cake“ | „Got it — I'll remember that about your colleague.“ |
  | „chocolate“ | Wikipedia-Definition von Schokolade |
  | „for booking yoga classes“ | „Mm-hm. What's on your mind?“ |
  | „yeah i like it“ | „That's okay — not everything needs an answer.“ |
  | „we'll see“ | „Ugh, we'll see. What happened?“ |
  | „maybe pasta“ | „Ooh, maybe pasta. How did it go?“ |
  | „with pesto“ | „With pesto — love that. What was the best part?“ |
  | „do you like pesto?“ | „I try not to have opinions“ |

  Grundursache waren die Echo-Vorlagen, die beliebige Satzstücke wiederholten, teils mit falscher Zeitform. Jetzt
  wird nur noch eine schlichte Beschreibung wiederholt („Ah, long day at work — …“, „Oh nice, she loved it!“).
  Satzstücke mit maybe/we'll/it was, Zeitangaben oder Zukunft bekommen eine neutrale Vorlage, und „How did it go?“
  entfällt ganz.

  Neu:
  - Kuchen von Kollegen (mit Sorte), langes Meeting (mit Thema), App-Projekt (wofür, eigene Rolle);
  - „yeah i like it“;
  - „we'll see / fingers crossed“;
  - Deadline-Datum mit Planungsrat;
  - „i'm thinking about dinner“ und danach „with pesto“;
  - freundliche Essensmeinung („If I could eat, pesto would be high on my list!“).

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 794 bestanden. Regressionen (64 Gespräche): 0 Wiederholungen.
  Neue Unterschiede gibt es nur in b42 und b78, dort wurde zwischen zwei gleichwertigen Echo-Varianten anders
  gewählt.
- **Alltags-Batterie 98 (dasselbe 25-Turn-Gespräch wie 97, auf Deutsch)**. Erster Lauf: 9 Wiederholungen. Bei
  12 von 25 Turns kam eine der drei Rückfall-Antworten („Das verstehe ich leider nicht …“, „Hm, da komme ich nicht
  ganz mit …“). Bei „ende nächsten monat“ kam „Wie schön! Erzähl ruhig mehr.“, bei „ich bin die designerin“ kam
  „Okay! Und wie war's?“.

  Jetzt: 0 Wiederholungen und an jeder Stelle eine passende Antwort.

  Neu:
  - Antwort auf „war okay / ging so / war gut / mies“ nach „Wie war dein Tag?“;
  - Kuchen (Sorte, „war echt lecker“), langes Meeting (Thema), App/Website-Projekt (wofür, eigene Rolle,
    „macht spaß“), knappe Deadline (Termin mit Planungsrat) als deutsche Ereignisse mit Folgefragen;
  - „mal sehen“;
  - „was gibt's bei dir neues?“;
  - „ich überlege, was ich koche“ → Pasta → „mit Pesto“ → „magst du Pesto?“ → „ich koch jetzt“ („Guten Appetit“);
  - Pläne („morgen pflanze ich neu“).

  Eine deutsche Aussage, die sonst niemand versteht, bekommt jetzt eine zugewandte neutrale Antwort statt der
  Rückfall-Antwort. Fragen behalten den Rückfall. „Und wie war's?“ und „wie ging's weiter?“ unterstellen keine
  Vergangenheit mehr. Die Folge-Empathie springt nicht mehr bei Satzstücken an („ende nächsten monat“, „um das
  budget“, „ich weiß auch nicht“) und auch nicht bei Meeting- oder Stresswörtern nach einem positiven Moment. Die
  Spracherkennung kennt 19 weitere deutsche Alltagswörter (eben, hause, gekommen, ging, hab …), sodass „bin eben
  nach hause gekommen“ nicht mehr auf Englisch beantwortet wird.

  Verallgemeinerungsprobe mit anderen Formulierungen (21 + 8 + 7 Turns: Muffins/Zitrone, „hab heute ein ewiges
  meeting gehabt“, Website für einen Bäcker, Risotto mit Pilzen, Hund gräbt den Garten um, Zoo): 0 Wiederholungen,
  kein Rückfall.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 795 bestanden. Regressionen: 0 Wiederholungen. Neu sind nur
  die gewollten Wortlaute in b32, b57d und b67x (neue Folge-Varianten, keine Vergangenheitsform mehr).
- **Alltags-Batterie 99 (neue englische Probe, 3 Gespräche mit 36 Turns: Training, Film, Elternbesuch,
  Laufanfänger mit Knieschmerzen)**. Erster Lauf: 0 Wiederholungen, aber etwa die Hälfte der Antworten generisch
  oder falsch:

  | Eingabe | vorher |
  |---|---|
  | „i just got back from the gym“ | „How was gym today?“ |
  | „yeah my legs are dead“ | „Oh really? Tell me more about that.“ |
  | „dune part two“ | „Mm-hm. What's on your mind?“ |
  | „what else should i watch?“ | „You haven't told me that yet.“ |
  | „something like interstellar“ | „Interstellar — nice! I'll remember that.“ |
  | „my parents are visiting this weekend“ | „Got it — I'll remember that about your parents.“ |
  | „my knee hurts a bit after“ | „What went wrong with your knee?“ |
  | „should i stop?“ | „I don't know that about you yet“ |
  | „what shoes do you recommend?“ | „I couldn't find anything reliable“ |

  Neu:
  - **Filmgespräch als Ablauf**: Titel merken, bei 11 bekannten Filmen eine kurze belegte Einordnung, Meinung
    gut/schlecht/zu lang, „have you seen it?“ ehrlich („I can't watch films — I only read“), Aspekte (Musik,
    Bilder, Schauspiel, Geschichte, Ende), „what else should i watch?“ mit ähnlichen Filmen (bei unbekanntem Titel
    die üblichen Filmtipps), „something like Interstellar“ nur bei bekannten Titeln. Sonst bleibt die bestehende
    Empfehlung zuständig, „something like harry potter“ ist durch Test 35 geschützt;
  - **Training**: Gym/Workout → Trainingstag → Muskelkater; Sportanfang → Häufigkeit → Strecke → Schmerzen
    (Knie, Schulter, Rücken …) mit Rat und Arztgrenze → „should i stop?“ → Laufschuhe;
  - **Elternbesuch**: Vorfreude/Stress/beides, Kritik der Mutter, „any tips?“, Vater vor dem Fernseher;
  - „i'll try that“ (nur direkt nach einem dieser Ratschläge; Schlaf- und Empfehlungs-Antworten behalten ihren
    eigenen Wortlaut);
  - „do you exercise?“.

  Verallgemeinerungsprobe mit anderen Formulierungen (4 Gespräche, 31 Turns: Brust/Trizeps, Oppenheimer „too
  long“, unbekannter Film „The Holdovers“, „anything like the matrix?“, Schwiegereltern, Schwimmen mit
  Schulterschmerzen): 0 Wiederholungen, alle Antworten passend.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 796 bestanden. Regressionen: 0 Wiederholungen, keine neuen
  Unterschiede außer Datum und Uhrzeit.
- **Alltags-Batterie 100 (Batterie 99 auf Deutsch, 36 Turns)**. Erster Lauf: 0 Wiederholungen, aber fast alles
  generisch:
  - „meine beine sind tot“ bekam eine Trauerantwort: „Oh nein, das tut mir so leid. Magst du mir von ihm erzählen?“;
  - „dune 2“ wurde auf Englisch beantwortet;
  - „hast du den gesehen?“ suchte einen Titel namens „The Den“;
  - auf „ich muss los“ kam „Das klingt richtig gut!“;
  - „soll ich aufhören?“, „machst du sport?“ und „was soll ich als nächstes schauen?“ landeten im Rückfall.

  Neu:
  - deutsche Ereignisse mit Folgefragen für Training, Sportanfang und Elternbesuch. Die Folgefragen werden vor
    jeder Trauer-Lesart geprüft;
  - ein deutsches Filmgespräch mit derselben Logik wie im Englischen: deutsche Einordnungen, deutsche Titel bei
    den ähnlichen Filmen, „Serie“ mit „sie“ und Serientipps ohne die gerade geschaute Serie;
  - „ich muss los / ich geh dann mal“ als Abschied, „machst du sport?“, „morgen“ als erster Gruß;
  - „probier ich / gute idee“ nach einem Rat;
  - ein offener Filmtitel bleibt im deutschen Gespräch auf Deutsch.

  Verallgemeinerungsprobe (4 Gespräche, 31 Turns: „hab grad trainiert“, Muskelkater, Kino mit Oppenheimer
  „zu lang“, Serie „Dark“, Schwiegermutter meckert über das Essen, Schwimmen mit Schulterschmerzen): 0
  Wiederholungen, alle Antworten passend.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 797 bestanden. Regressionen: 0 Wiederholungen, keine neuen
  Unterschiede außer Datum und Uhrzeit.
- **Alltags-Batterie 101 (gemischt: Reiseplanung, Schreibhilfe, Wissens-Folgefragen; 3 Gespräche, 24 Turns)**.
  Erster Lauf, die Fehler:

  | Eingabe | vorher |
  |---|---|
  | „how long is the flight from germany?“ (Japan-Reise) | „I couldn't find anything reliable“, danach war Deutschland das Reiseziel |
  | „is it expensive?“ / „what food should i try?“ | über Deutschland |
  | „what's the currency?“ | Definition des Wortes „currency“ |
  | „how do you say thank you in japanese?“ | „isn't among them“ |
  | „help me write a message to my boss“ | „I wanted to get in touch to get in touch.“ |
  | „i need tomorrow off“ / „my kid is sick“ | „Tell me more about that“ / „What happened with your kid?“ |
  | „and the biggest city?“ (nach Australien) | „I don't know“ |
  | „when was that?“ (nach der Entdeckung Australiens) | „I don't know“ |
  | „tell me a fun fact about kangaroos“ | „I couldn't find anything“ |

  Grundursache beim Ortswechsel: Das „from germany“ in der Flugfrage überschrieb das Reiseziel. Ein „from X“
  während einer laufenden Reise ändert das Ziel jetzt nicht mehr.

  Neu:
  - Reise im Kontext: Reisemonat (5 belegte Sonderfälle wie Kirschblüte im April und Songkran), Flugzeit ab
    Deutschland aus einer Tabelle typischer Werte (25 Ziele, als ungefähr gekennzeichnet; bei anderem
    Abflugort keine Schätzung), Währung (28 Länder, Städte zugeordnet), Landesküche (eigene Stadtküche zuerst),
    „i don't like fish“;
  - Japanisch-Grundwörter (18 Wendungen mit Schriftzeichen);
  - Schreibhilfe:
    - fragt nach dem Anlass, wenn er fehlt;
    - ein Satz als Anlass ergibt „let you know that …“ (inklusive „has been broken since Monday“);
    - „tomorrow off“ ergibt den Antrag auf einen freien Tag;
    - ein Satz direkt danach wird als Grund eingebaut („because my kid is sick“);
  - „and the biggest city?“ nach einer Länderfrage;
  - Entdeckung Australiens als belegte Antwort: Janszoon 1606, Aborigines seit mindestens 50.000 Jahren, Cook
    1770, Folgefrage „when“;
  - Fun Facts zu beliebigen Themen aus dem Artikelanfang, bewertet nach „können / Rekord / Zahl“ statt
    Definition. Ohne passenden Satz kommen ehrlich die Grundlagen.

  Verallgemeinerungsprobe (Thailand, Vermieter-Mail, Kanada, Pinguine): alles passend, 0 Wiederholungen.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 798 bestanden. Regressionen: 0 Wiederholungen. Gewollte
  neue Unterschiede:
  - b46: Rückfrage statt leerer Mail;
  - b47: Rom-Küche statt Artikeltext;
  - Kostentext ohne „trattorias“.
- **Alltags-Batterie 102 (Batterie 101 auf Deutsch, 25 Turns)**. Erster Lauf: 2 Wiederholungen. Fast jede
  Reisefrage ging in den Rückfall („Das kann ich auf Deutsch leider noch nicht nachschlagen“), die Schreibhilfe
  verstand die Bitte nicht, „und die größte Stadt?“ war unbekannt, und der Fun Fact endete in „Erzähl gern weiter“.

  Neu (`_german_ctx102`):
  - Reise im Kontext: 67 deutsche Orts- und Ländernamen. Dazu gibt es auf Deutsch:
    - Reisemonat mit denselben Sonderfällen wie im Englischen;
    - Sehenswürdigkeiten für 8 Länder, sonst ein ehrlicher Hinweis;
    - Flugzeit ab Deutschland für 25 Ziele;
    - „ist es teuer?“ nach derselben Preisstufe wie im Englischen;
    - Währung im Nominativ („In Japan gilt der japanische Yen“), Euro-Länder zusammengefasst; das behebt auch
      das englische „currency in italy“;
    - Landesküche und „ich mag keinen Fisch“;
  - „wie sagt man / was heißt X auf Japanisch/Spanisch/…“ mit deutscher Anmerkung („höflicher …“);
  - kurze deutsche Nachricht an Chef, Vermieter oder Lehrer in der Sie-Form:
    - die Rückfrage nach dem Anlass;
    - freier Tag mit ausgerechnetem Datum („morgen (Sonntag, 4. Oktober)“);
    - jeder andere Satz als „Folgendes mitteilen: …“ mit großgeschriebenen Nomen, beim Vermieter mit Bitte um
      Reparatur;
    - der Grund wird danach als eigener Satz ergänzt;
  - „und die größte Stadt?“ nach einer Länderfrage auf Deutsch;
  - Fun Fact zu Tieren und Themen (deutsche Tiernamen übersetzt; der Satz selbst ist englisch und so gekennzeichnet);
  - „interessant / krass / wow“ nach einer Antwort.

  Außerdem nutzen handgeprüfte Fakten im deutschen Fragepfad jetzt ihren eigenen deutschen Text statt der
  Schablone „X wurde von Y entdeckt“, zum Beispiel „Christoph Kolumbus erreichte 1492 Amerika – aber dort lebten
  schon …“.

  Verallgemeinerungsprobe (Italien im Juli, Vermieter mit kaputter Heizung, Kanada, Pinguine): alles passend, 0
  Wiederholungen.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 799 bestanden. Regressionen: 0 Wiederholungen. Einziger neuer
  Unterschied: b78 „wow“ nach einer Antwort bekommt die neue Reaktion.
- **Alltags-Batterie 103 (lockere Schreibweise: Tippfehler, Slang, Emojis, mehrere Angaben pro Nachricht; 3
  Gespräche, 27 Turns)**. Erster Lauf, die Fehler:

  | Eingabe | vorher |
  |---|---|
  | „heyyy 👋“ | „I see. Tell me more?“ |
  | „yeah its rough but i like my job“ (Nachtschicht) | „Ugh, I'm sorry.“ |
  | „my sister lives in berlin and i miss her“ | „Got it — I'll remember that about your sister.“; danach „Your sister lives in Berlin and you miss her.“ |
  | „lol ur good“ | „That sounds great!“ |
  | „k bye“ | „Mm-hm. What's on your mind?“ |
  | „idk im kinda bored“ | „Oh really? Tell me more about that.“ |
  | „maybe a joke“ / „another one“ | „What's on your mind?“ |
  | „yo can u recommend a book“ | „Oh? Go on.“ |
  | „any thriller?“ | „I couldn't find anything reliable“ |

  Neu:
  - `_casual` vor jeder englischen Nachricht:
    - Emojis um die Wörter herum fallen weg, gedehnte Grüße werden normalisiert;
    - „yo / ngl / tbh“ am Satzanfang fällt weg; „idk“ nur vor „im“, damit „idk what to do“ bleibt (durch
      Test 69 geschützt);
    - „kinda“ wird zu „kind of“, „names lisa“ zu „my name is lisa“ (vorher hieß der Nutzer „Names Lisa“);
    - „dev“ wird zu „developer“;
    - „k bye / cya / gtg“ werden zum Abschied, „brb“ bleibt „bin gleich zurück“;
  - „lol ur good“ ergibt „you're good“, „ur name?“ bleibt „your name?“;
  - Nachtschicht als Moment mit Folgefragen;
  - „my X lives in Y and i miss her/him“: Der Ort wird gemerkt, das Vermissen gehört;
  - „im a dev, 34“: Beruf und Alter werden gemerkt;
  - „maybe a joke / a fun fact maybe“;
  - Genre nach Tipps:
    - „any thriller?“ bei Büchern aus einer kleinen geprüften Liste (Krimi, Thriller, Romanze);
    - „any horror?“ bei Filmen nur mit Horrorfilmen (vorher auch „Inception“).

  Verallgemeinerungsprobe (Lisa, Bruder in Kanada, „ngl im so bored“, Horrorfilme): alles passend, 0
  Wiederholungen.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 800 bestanden. Regressionen: 0 Wiederholungen. Gewollte neue
  Unterschiede:
  - b40 „something scary“ nennt nur Horrorfilme;
  - b69 „heyyy 😊“ wird als Gruß beantwortet.
- **Alltags-Batterie 104 (lockeres Deutsch, 3 Gespräche, 26 Turns)**. Erster Lauf: 3 Wiederholungen, fast alles
  im Rückfall:
  - „na? 👋“ lief auf Englisch in die Nachschlage-Suche;
  - „bin übrigens jonas“, „bin 31 und arbeite als pfleger“ und „meine schwester wohnt in hamburg und ich
    vermisse sie“ wurden nicht gemerkt;
  - „vllt nen witz“, „und 20?“ und „bis denne“ wurden nicht verstanden.

  Neu:
  - `_casual_de` vor jeder deutschen Nachricht:
    - Emojis fallen weg;
    - „joa / naja“ am Satzanfang fällt weg; „kp / keine ahnung“ nur vor „mir / ich / bin / hab“, damit „keine
      ahnung was ich machen soll“ bleibt (durch Test 47 geschützt);
    - „vllt“, „nen“, „thx“ und „wie heiß ich“ werden normalisiert;
    - „bis denne / ciao / tschüssi“ werden zum Abschied;
  - Grüße als erste Nachricht: „na“, „servus“, „huhu“ und weitere;
  - `_german_ctx104`:
    - „bin übrigens jonas / ich bin die lena btw“ als Name, mit einer Ausschlussliste für „bin müde“ und
      Ähnliches;
    - Alter und Beruf in einem Satz;
    - Nachtschicht mit Folgefragen;
    - Vermissen mit gemerktem Wohnort und „wo wohnt meine Schwester?“ ergibt „Deine Schwester wohnt in
      Hamburg.“;
    - „du bist gut“;
    - „vllt nen witz / noch einer / reicht“;
    - „und 20?“ nach einer Prozentrechnung;
    - „so was wie harry potter“ und „was spannendes?“ nach Buchtipps;
  - in deutschen Tipplisten wird „and“ zu „und“.

  Verallgemeinerungsprobe (Lena, Bruder in Wien, „naja egal, erzähl mir nen witz“, „und 15?“): alles passend, 0
  Wiederholungen.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 801 bestanden. Regressionen: 0 Wiederholungen. Neu ist nur
  b76 „du bist echt schlau“ mit einem gleichwertigen Dank.
- **Alltags-Batterie 105 (emotionale Unterstützung über viele Turns: Trennung mit 14 Turns, Arbeitsstress mit 7
  Turns)**. Erster Lauf: 0 Wiederholungen, aber vieles daneben:
  - „How are you holding up?“ kam zweimal hintereinander;
  - „she said she needs space“ ergab „I see. Tell me more?“;
  - „i keep checking my phone“ und „my friends say i should go out“ wurden als Fakten gemerkt;
  - „yeah maybe“ ergab „How did you react?“, „i don't feel like it“ ergab „How's that going?“;
  - „i think i'll call my brother“ ergab „I'll remember that about your brother“;
  - „ok i'll try tomorrow“ ergab „Sounds like a plan — enjoy!“.

  Neu:
  - **Trennung als Ablauf**: Die erste Antwort bleibt bei den Empathie-Regeln. Danach folgen 9 Folgezustände:
    - Dauer der Beziehung, unerwartet, „needs space“, Handy-Checken, Schlaf;
    - „what should i do?“ mit kurzem Rat; das Pronomen folgt dem Wort „girlfriend“ bzw. „boyfriend“;
    - „maybe“, Freunde wollen ausgehen, „nicht bereit“;
  - **Arbeitsstress**: „work is crazy“, der Chef lädt mehr ab (beim zweiten Mal eine andere Antwort), keine
    Pause seit Wochen, „drowning“, „helpful“ (je nachdem, ob gerade Rat zum Neinsagen kam);
  - „thanks for listening“, „i think i'll call my brother“ nach einem schweren Moment, „i'll try tomorrow“.

  Verallgemeinerungsprobe („my boyfriend dumped me“, „we'd been together for two years“, „work is killing me“,
  „a day off in weeks“): alles passend, 0 Wiederholungen.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 802 bestanden. Regressionen: 0 Wiederholungen. Gewollte neue
  Unterschiede:
  - b43/b86 „thanks for listening“;
  - b62 „work is crazy“ und danach „my boss keeps adding tasks“ (zwei verschiedene Antworten), „i'll talk to her
    tonight“.
- **Alltags-Batterie 106 (Batterie 105 auf Deutsch, 21 Turns)**. Erster Lauf mit einem echten Fehler: Auf „meine
  freundin hat gestern schluss gemacht“ kam „Herrlich! 😊“, danach „Wie schön! Erzähl ruhig mehr.“, „Das klingt
  richtig gut!“ und „Haha, wie schön!“.

  Grundursache: Das vorherige „nicht so gut“ wurde als *positives* Gefühl gespeichert, weil die Verneinung die
  Stimmung nicht umdrehte. Alle folgenden Sätze bekamen deshalb die positive Folge-Empathie. Eine verneinte
  Stimmung dreht jetzt die Valenz; Test 106 schützt das.

  Neu: Trennung und Arbeitsstress auf Deutsch mit denselben Zuständen wie im Englischen:
  - Dauer im Dativ („nach drei Jahren“, „nach einem Jahr“);
  - „hat er/sie gesagt, warum?“ nach dem Wort Freund bzw. Freundin;
  - „Abstand“, Handy, Schlaf, Rat, „vielleicht“, Freunde, keine Lust, Anruf beim Bruder;
  - Chef/Chefin lädt ab, beim zweiten Mal eine andere Antwort mit „deine Chefin“;
  - keine Pause seit Wochen, „ich geh unter“;
  - „wie sag ich meinem Chef nein?“ mit drei Formulierungen;
  - „das hilft echt“ und „ich versuch's morgen“.

  Verallgemeinerungsprobe („mein freund hat mich verlassen“, „ein jahr zusammen“, „die arbeit ist gerade echt zu
  viel“, Chefin zweimal): alles passend, 0 Wiederholungen.

  Messung: Team-Dev-Satz wie bei 89, NQ 22/9, Suite 803 bestanden. Regressionen: 0 Wiederholungen. Gewollte neue
  Unterschiede: b41 (die alte deutsche Trennungsfolge wird von der neuen ersetzt, Inhalt gleichwertig, der Rat
  ausführlicher) und b44 „die arbeit ist der wahnsinn“.
- **Valenz-Probe 107 (systematisch nach dem Fund in Batterie 106; `scratchpad/valence_probe*.py`)**:
  - Kombinationen aus Stimmung und Nachricht mit entgegengesetzter Stimmung, auf Englisch und Deutsch:
    - 112 Kombinationen „erst gut, dann schlechte Nachricht“ (7 Stimmungen × 8 Ereignisse × 2 Sprachen);
    - 60 Kombinationen „erst schlecht, dann gute Nachricht“ (5 × 6 × 2);
  - automatisch geprüft wird auf fröhliche bzw. bedrückte Formulierungen.

  Erster Lauf:
  - 6 von 112 fehlerhaft, alle deutsch: „heute war ein toller tag“ → „ich hatte einen unfall“ ergab „Haha, wie
    schön!“; Fahrraddiebstahl und Krankenhaus ebenso;
  - 5 von 60 fehlerhaft: „mir geht's schlecht“ → „ich hab den job bekommen“ ergab „Puh, das auch noch. Das tut
    mir leid.“.

  Behoben:
  - Die deutsche Folge-Empathie kennt 30 weitere Wörter für schlechte Nachrichten (Unfall, geklaut,
    Krankenhaus, gefeuert, Streit …) und 12 für gute (bestanden, Zusage, befördert …);
  - „ich hab den Job / die Stelle / eine Zusage bekommen“ ist ein eigener Moment mit Glückwunsch.

  Zweiter Lauf: 0 von 112 und 0 von 60. Test 107 hält 9 repräsentative Fälle fest. Suite 804 bestanden, NQ 22/9,
  Routine ohne neue Unterschiede.
- **RAM und Antwortzeit, Lite-Paket** (2. Oktober 2026, Container mit 4 Kernen und 15 GB, nicht die 4-GB-VM;
  `scratchpad/perf.py`): 120 gemischte Alltagsnachrichten aus den Batterien 21–33, ein Prozess, offline.
  Laden 5,0 s; Antwortzeit p50 0,001 s, **p95 0,093 s**, Maximum 1,41 s; **Spitzen-RSS 555 MB**.
  Schwellen aus dem Plan (A2): RAM ≤ 1,5 GB, p95 ≤ 1,5 s offline — beide eingehalten. Offen: dieselbe Messung
  auf der 4-GB-VM und mit dem Standard-Paket (2,73 GB Download; nicht in diesem Container gemessen).
- **RAM und Antwortzeit, Standard-Paket** (aus dem Release `pack-standard-v3.1.0-beta.1` geladen, alle 36 Dateien
  gegen Manifest-Größe und SHA-256 geprüft; gleicher Container, gleiche 120 Nachrichten): Laden 9,3 s; p50 0,001 s,
  **p95 0,174 s**, Maximum 6,1 s (die erste Textsuche nach dem Start, kalte Index-Dateien); **Spitzen-RSS 1.053 MB**.
  Schwellen (RAM ≤ 1,5 GB, p95 ≤ 1,5 s) eingehalten. Wissensbatterie 30 gibt mit dem Standard-Paket dieselben
  Antworten wie mit dem Lite-Paket. Offen bleibt nur die 4-GB-VM.
- **Messung mit harter Speichergrenze (Ersatz für die 4-GB-VM, 2. Oktober 2026)**: eigene cgroup (v1, `memory.limit_in_bytes`)
  im Container, 300 gemischte Alltagsnachrichten aus den Batterien 21–40 (`scratchpad/perf4g.py`), Stand d26a277+.

  | Grenze | Paket | Laden | p50 | p95 | Max | Spitzen-RSS | Grenze erreicht / OOM |
  |---|---|---|---|---|---|---|---|
  | 3 GiB (4-GB-Rechner abzüglich ≈ 1 GB System) | Lite | 5,8 s | 0,001 s | 0,023 s | 1,49 s | 559 MB | 0 / 0 |
  | 3 GiB | Standard | 8,6 s | 0,001 s | 0,058 s | 6,82 s | 1.077 MB | 0 / 0 |
  | 1,5 GiB (Plan-Schwelle A2) | Lite | 6,2 s | 0,001 s | 0,018 s | 1,68 s | 553 MB | 0 / 0 |
  | 1,5 GiB | Standard | 8,5 s | 0,001 s | 0,055 s | 6,30 s | 1.073 MB | 0 / 0 |

  Einschränkung: Die Paketdateien liegen in `/dev/shm` und waren schon der übergeordneten cgroup angerechnet; der
  Seiten-Cache beim ersten Lesen von einer langsamen Platte ist daher nicht mitgemessen (die cgroup zählte 299 bzw.
  455 MB neu angerechneten Speicher). Maßgeblich ist der Spitzen-RSS (inklusive gemappter Paketseiten), der unter
  1,1 GB bleibt. Das Maximum von ≈ 6 s beim Standard-Paket ist die erste Textsuche mit kalten Index-Dateien. Eine Messung
  auf echter 4-GB-Hardware mit Festplatte steht weiterhin aus.
