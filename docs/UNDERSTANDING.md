# UNDERSTANDING — warum die Mathematik funktioniert

Dieses Dokument erklärt **nicht, was der Code tut**, sondern **warum es
mathematisch funktioniert**. Zielgruppe ist ein Prüfer, der nachfragt — also
jemand, der eine Antwort nicht akzeptiert, weil sie plausibel klingt, sondern
weil sie stimmt und belegt ist.

## Arbeitsteilung (verbindlich)

| | |
|---|---|
| **Erik** | schreibt sämtliche Antworten selbst |
| **Claude** | liefert die Fragen und prüft die Antworten auf **sachliche Fehler** |

Claude schreibt in diesem Dokument keine Antworten — auch nicht als Entwurf,
auch nicht „zur Orientierung". Ein Abschnitt, der von Claude formuliert wäre,
würde genau die Prüfung nicht bestehen, für die dieses Dokument existiert.

### Prüfprotokoll

Wenn ein Abschnitt fertig ist, prüft Claude ihn und meldet je Befund:

* **FALSCH** — die Aussage ist mathematisch nicht haltbar. Mit Begründung,
  warum, und einem Zeiger auf die relevante Stelle. Die Korrektur schreibt
  Erik.
* **UNPRÄZISE** — im Kern richtig, aber so formuliert, dass ein Prüfer
  nachhakt (fehlende Bedingung, verschwiegener Grenzfall, unscharfer Begriff).
* **UNBELEGT** — eine Zahl oder Behauptung ohne Herleitung oder Quelle.
* **KORREKT** — wird ebenfalls genannt, damit die Rückmeldung nicht nur aus
  Kritik besteht.

Claude formuliert Befunde als Rückfrage, wo das möglich ist — eine Frage, die
den Fehler sichtbar macht, ist lehrreicher als eine fertige Korrektur.

### Regeln für die Antworten

1. **Kein Code.** Keine Funktionsnamen, keine Signaturen, keine
   Implementierungsdetails. Wer die Mathematik verstanden hat, kann sie ohne
   die Implementierung erklären.
2. **Zahlen werden hergeleitet.** „Die Kollisionswahrscheinlichkeit ist
   verschwindend gering" ist keine Antwort. Eine Zahl mit Rechenweg ist eine.
3. **Grenzfälle gehören dazu.** Wo bricht das Argument? Ein Prüfer fragt
   genau dort.
4. **Fremde Ergebnisse werden als solche gekennzeichnet.** Was aus der
   VSA-Literatur stammt, was aus den Projektunterlagen, was eigene Herleitung
   ist.

---

## Baustein B2 — Kern: Item-Memory, Binding, Bundling, Permutation

*Status: B2.2 beantwortet (2026-08-15), drei Rückfragen offen. B2.1, B2.3–B2.5 ausstehend.*

### B2.1 Bundling per Mehrheitsentscheid

**Hauptfrage:** Warum funktioniert Bundling per Mehrheitsentscheid — warum
ist das Bündel jedem seiner Bestandteile ähnlich?

Nachfragen eines Prüfers:

* Wie hängt die Ähnlichkeit des Bündels zu einem einzelnen Bestandteil von
  der Anzahl der gebündelten Vektoren ab? Gibt es einen Grenzwert?
* Warum bleibt das Bündel einem Vektor *unähnlich*, der nicht eingebündelt
  wurde? Was genau garantiert das?
* Gibt es eine Kapazitätsgrenze — ab wie vielen Vektoren trägt das Bündel die
  Information nicht mehr, und wovon hängt diese Grenze ab?
* Der Mehrheitsentscheid verwirft die Information, *wie deutlich* eine
  Mehrheit war. Was geht dadurch verloren, und warum ist das vertretbar?

### B2.2 Gerade Anzahl und Unentschieden

**Hauptfrage:** Was passiert bei einer geraden Anzahl gebündelter Vektoren,
und wie wird das aufgelöst?

Nachfragen eines Prüfers:

* Warum ist ein Unentschieden überhaupt ein Problem? Was spricht dagegen,
  Gleichstände einfach auf 0 zu setzen?
* Welche Auflösungen sind möglich, und was kostet jede davon?
* Wenn alle Klassen denselben Füllvektor für Gleichstände benutzen: Welcher
  Mechanismus führt dazu, dass die Prototypen einander ähnlicher werden?
  Rechne es für den Extremfall zweier Bestandteile pro Klasse durch.
* Warum verliert das Problem bei etwa zehn Bestandteilen pro Klasse an
  Bedeutung? Gib die Größenordnung an, nicht nur die Richtung.

*Belegstelle in den Projektunterlagen: `D6_EHRLICHKEIT.md`, Punkt W14 —
dort ist ein beobachteter Kollaps dokumentiert. Die mechanische Erklärung
dafür ist Teil der Antwort.*

**Beantwortet 2026-08-15.** Entscheidung: inhaltsabhängiger Hash. Umgesetzt
in `engramm.core.resolve_tie`, dokumentiert in `docs/DEVIATIONS.md` GAP-4.
Die Rechnung wurde nachgeprüft und trägt — insbesondere die Aussage, dass
ein fester Tie-Vektor die Klassenähnlichkeit genauso aufbläht wie „immer
+1"; gemessen 62,53 % gegen 62,49 % Übereinstimmung, beide gegen 50 % beim
Hash.

#### Rückfragen zur Antwort (offen)

Drei Stellen, an denen ein Prüfer nachhaken würde. Die Antworten gehören in
den Text oben, nicht hierher.

1. **Welche Größe ist mit „75 % Ähnlichkeit" gemeint?** Der Text nennt 7.500
   Treffer von 10.000. Dieses Projekt misst Ähnlichkeit aber als
   `sim_from_dh = 1 − 2·d_H/D`. Rechne aus, welchen Wert diese Formel für
   7.500 Treffer liefert, und entscheide, welche der beiden Größen im Text
   stehen soll — oder ob beide gebraucht werden und benannt werden müssen.

2. **Zeigt der Vergleich in Schritt 4 wirklich, was er zeigen soll?**
   Variante A wird über die *Klassenähnlichkeit* kritisiert, Variante B über
   die *Ähnlichkeit zum Ursprungsvektor* gelobt. Rechne nach, wie viele
   Treffer mit A das Bündel unter *Variante A* hat. Wenn dieselbe Zahl
   herauskommt: An welcher Größe hängt der Vorteil von B dann tatsächlich,
   und wie muss der Absatz umgestellt werden, damit er das belegt?

3. **Woher kommen die 2,7 %?** Der Text nennt die Zahl für ~800 Summanden
   ohne Herleitung. Es gibt eine geschlossene Form: Wie groß ist die
   Wahrscheinlichkeit, dass eine Summe aus *n* unabhängigen ±1-Werten exakt
   0 ergibt? Stelle sie auf (Stichwort: Binomialkoeffizient), gib die
   Näherung für großes *n* an, und prüfe sie gegen die gemessenen 2,72 % bei
   n = 784. Damit ist die Skalierungsaussage nachrechenbar statt zugesagt.

### B2.3 Permutation für Sequenzen

**Hauptfrage:** Warum wird Reihenfolge durch Permutation (Rotation) kodiert
und nicht durch ein zweites Binding mit Positionsvektoren?

Nachfragen eines Prüfers:

* Welche Eigenschaft muss eine Sequenzkodierung haben, die Bündeln allein
  nicht liefert? Formuliere sie als Bedingung, nicht als Beispiel.
* Warum ist Rotation invertierbar, und warum zerstört sie die Ähnlichkeit
  zum Ausgangsvektor?
* Der Alternativweg — Positionsvektoren einbinden — funktioniert ebenfalls.
  Was genau ist der Unterschied in Kosten und Eigenschaften?
* Vertauschen Rotation und XOR miteinander? Rechne es nach und sage, wofür
  die Antwort Konsequenzen hat.

### B2.4 XOR als Binding

**Hauptfrage:** Warum ist XOR als Binding invertierbar und
ähnlichkeitszerstörend?

Nachfragen eines Prüfers:

* Was heißt „ähnlichkeitszerstörend" quantitativ? Gib die erwartete
  Hamming-Distanz zwischen einem Vektor und seiner Bindung an — mit
  Herleitung.
* Warum ist XOR sein eigenes Inverses, und was folgt daraus für das Auflösen
  einer Bindung?
* XOR ist kommutativ und assoziativ. Wo hilft das, und wo schadet es? Lassen
  sich `(a⊕b)⊕c` und `a⊕(b⊕c)` unterscheiden, und ist das ein Problem?
* Wie verträgt sich Binding mit Bundling? Gilt so etwas wie ein
  Distributivgesetz, und wenn ja, in welchem Sinn — exakt oder nur im Mittel?

### B2.5 Dimension und Kollisionswahrscheinlichkeit

**Hauptfrage:** Warum brauchen Hypervektoren so hohe Dimension, und wie hoch
ist die Kollisionswahrscheinlichkeit bei D = 10.000?

Nachfragen eines Prüfers:

* Wie ist die Hamming-Distanz zweier unabhängig gezogener binärer
  Hypervektoren verteilt? Nenne Verteilung, Erwartungswert und
  Standardabweichung für D = 10.000.
* Wie viele Standardabweichungen vom Zufallswert entfernt liegt ein Treffer,
  den das System als Übereinstimmung wertet?
* Gib eine konkrete Zahl: Wie wahrscheinlich ist es, dass zwei unabhängige
  Zufallsvektoren zufällig ähnlicher sind als ein gewählter Schwellwert?
  Nenne den Schwellwert, den du zugrunde legst.
* Wie skaliert die nötige Dimension mit der Anzahl gespeicherter Symbole?
  Warum genügt D = 1.000 nicht — oder genügt es doch, und wofür?
* Die Item-Memory-Vektoren werden aus einem Seed pseudozufällig erzeugt. Was
  ändert sich dadurch gegenüber echtem Zufall — für die Rechnung, und für die
  Argumentation?

---

## Weitere Bausteine

Fragen werden gestellt, sobald der jeweilige Baustein implementiert ist:

* **B3 — Datenlader und Split-Disziplin:** u. a. warum die Trennung *vor*
  jeder Statistikbildung liegen muss und was genau ein Leck mathematisch
  bewirkt.
* **B4 — Encoder:** Trigramm-Kodierung und Thermometer-Kodierung, u. a.
  warum Thermometer-Stufen ordnungserhaltend sind und One-Hot nicht.
* **B5/B6 — Klassifikation und Auswertung:** u. a. warum Accuracy bei
  balancierten Klassen dem Macro-Recall entspricht und wann nicht.
* **Robustheitsstudie:** warum verteilte Repräsentationen unter Bitkorruption
  anders degradieren sollten als konzentrierte — die Frage, die
  `PREREG_ROBUSTNESS.md` messbar macht.
