# Vom Nutzer lernen, ohne seine Fehler zu lernen

*Kurzfassung des Papers „Learning from the User Without Learning Their Mistakes" für Leserinnen und Leser ohne Fachhintergrund*

**Worum es geht.** Ein persönlicher Assistent wird nützlicher, wenn er sich auf seinen Nutzer einstellt: Er soll sich merken, dass der Hund Rex heißt, und darf mit der Zeit ein wenig so schreiben wie der Nutzer. Am besten geschieht das auf dem eigenen Rechner, damit keine Texte das Gerät verlassen. Aber Menschen machen Fehler. Ein Modell, das lernt, wie jemand schreibt, lernt auch dessen Tippfehler („definately"), zusammengeschriebene Wörter („garnicht") und Grammatikfehler („ich habe gegangen") – und schreibt sie womöglich zurück.

**Das System.** Sela-2 ist ein kleines Sprachmodell (352 Millionen Parameter je Token, also je Wortteil), das von Grund auf selbst trainiert wurde: auf einer gemieteten Grafikkarte, für etwa 23 US-Dollar. Es läuft ohne Internet auf einem gewöhnlichen Prozessor im Desktop-Assistenten ENGRAMM und lernt auf drei Wegen: (A) eine kurze Notiz mit den Fakten des Nutzers (Name, Stadt, Haustier, Lieblingsessen), (B) der bisherige Gesprächsverlauf und (C) ein Sprachgedächtnis, das sich merkt, welche Wörter in den Nachrichten des Nutzers aufeinander folgen. Vor dem Sprachgedächtnis steht ein Filter: Das Modell prüft selbst, ob eine Nachricht mit einer kleinen Änderung deutlich wahrscheinlicher wird (etwa „alot" → „a lot"). Ist das so, wird der ganze Satz nicht gelernt. Alles Gelernte bleibt auf dem Rechner und lässt sich gezielt wieder löschen.

**Wie geprüft wurde.** Bevor eine Version gemessen wurde, standen Messung, Erfolgskriterien und Entscheidungsregel schriftlich fest („Vorab-Registrierung"). Dann wurde jede Version genau einmal an 40 Nutzern gemessen, die sie nie gesehen hatte, und die Regel entschied. Insgesamt gab es sechs solcher Messungen mit 240 Nutzern: 160 künstlich erzeugte und 80 echte Menschen aus einer öffentlichen Sammlung von Chatbot-Gesprächen (WildChat-1M).

**Was herauskam.**

- **Fakten:** Mit der Notiz nutzte das Modell die Fakten des Nutzers in 20 bis 53 % der Antworten, die danach verlangten; ohne Notiz nie.
- **Fehler:** Ab der zweiten Version wiederholten höchstens zwei Antworten je Lauf (von 280 bzw. 360) einen eingeschleusten Fehler. Von je 120 eingeschleusten Fehlern gelangten 4 bis 10 ins Gedächtnis.
- **Gedächtnis:** Bei künstlichen Nutzern schrumpfte der Nutzen von 3,39 % auf 0,09 %. Der Grund lag vermutlich nicht im Verfahren, sondern in den Testsätzen, die wir selbst geschrieben hatten: Sie wiederholten immer weniger Wortpaare, die der Nutzer schon benutzt hatte. Echte Menschen wiederholen ihre Formulierungen öfter; bei ihnen sagte das Gedächtnis ihre Nachrichten um 1,59 % (entscheidende Messung) und 3,07 % (zweite Gruppe) besser voraus.
- **Ungefragte Fakten:** Mit allen Fakten in der Notiz erzählte das Modell oft ungefragt vom Nutzer – in einem Viertel bis zwei Fünfteln seiner Antworten. Ein einfacher Filter, der nur die Fakten zeigt, um die es in der Nachricht geht, senkte das auf 0 von 291 Antworten, ohne dass die Fakten dort seltener genutzt wurden, wo sie gefragt waren.

**Auch die eigenen Fehler stehen im Paper:** eine schlecht gebaute Entscheidungsregel, eine Gegenmaßnahme, die echte Fehler durchließ, und eine Zahl, die erst nach der Messung zusammengezählt wurde.

**Grenzen.** Untersucht ist ein einziges kleines Modell in Englisch und Deutsch; 40 Nutzer je Messung sind wenig, viele Unterschiede sind unsicher; die eingeschleusten Fehler und Fakten waren auch bei echten Nutzern künstlich; und kein Mensch hat die Qualität der Antworten bewertet.

**Datenschutz.** Die Texte der echten Nutzer liegen nicht im Projekt; gespeichert sind nur Kennungen und Prüfsummen. Für jede Messung werden sie aus der öffentlichen Sammlung neu zusammengesetzt, und die Ergebnisse enthalten sie nicht.
