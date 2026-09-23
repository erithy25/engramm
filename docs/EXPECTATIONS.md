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
3. **Determinismus:** folgt im Schritt `repro` von `experiments/reproduce_all.sh`
   (Seed 42 erneut, Vergleich über `predictions_sha256`).
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
| WiLI 10-shot, Prototypen (E1) | 0,8488510638297873 | Accuracy + Macro-F1 identisch (Altrecord ohne Digest) |
| MNIST, Prototypen T1 | 0,8054 | Accuracy + Macro-F1 identisch (Altrecord ohne Digest) |
| MNIST, Prototypen + T2 (E3) | 0,8542 | `predictions_sha256` identisch |
| MNIST, volle Pipeline (M1b/E4) | 0,9488 | `predictions_sha256` identisch |

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
