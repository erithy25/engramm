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

### Ergebnis

*(wird nach dem Lauf eingetragen; die Erwartung oben bleibt unverändert)*

---

## E2 — MNIST-Thermometer-Sweep

**Status: in der Warteschlange, noch nicht registriert.**

Der Sweep untersucht `docs/DEVIATIONS.md` GAP-1 — die
Thermometer-Konstruktion, die in keinem überlieferten Dokument festgehalten
war und dort vorab als wahrscheinlichste Ursache einer MNIST-Abweichung
benannt ist.

**Bedingung: das Gitter wird registriert, bevor der erste Lauf startet** —
welche Konstruktionen, welche Stufenzahlen, welche Seeds, und was als
Erklärung des Abstands gilt. Ohne das ist hinterher jedes Ergebnis
irgendwie erklärbar.
