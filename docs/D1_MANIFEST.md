## 5. Die eine Dimension, in der wir gewinnen wollen

Missionsgemäß greifen wir Großmodelle nicht in der Breite an, sondern in **einer** Dimension, in der ihre Schwäche *strukturell* ist (nicht durch mehr Rechenleistung heilbar):

> **Kontinuierliches Few-Shot-Lernen ohne Vergessen, 100 % lokal auf einer normalen CPU.**
> Eine neue Klasse aus ≤10 Beispielen in unter 1 Sekunde lernen, sofort nutzbar, und nach 1.000 weiteren sequenziell gelernten Klassen haben die alten weniger als 1 Prozentpunkt verloren.

Warum Großmodelle hier strukturell verlieren: In-Context-Learning scheitert am endlichen Fenster und zahlt jeden gelernten Fakt bei *jeder* Anfrage erneut; Fine-Tuning braucht GPUs und riskiert dokumentiert katastrophales Vergessen. ENGRAMMs härtester fairer Gegner ist deshalb keines von beiden, sondern ein **lokales Klein-LLM mit RAG** — dieselbe Lernphilosophie (Einfügen), aber mit gelernten Embeddings. Genau gegen diesen Gegner ist der finale Benchmark (M5) vorregistriert, mit einem UND-Kriterium: Genauigkeit mindestens auf 5 Punkte heran **und** ≥10× weniger Energie **und** ≥100× schnelleres Lernen **und** Vergessen ≤1 Punkt. Effizienz ohne Genauigkeit zählt nicht als Sieg.

## 6. Stand der Dinge (gemessen, nicht versprochen)

Der M1-Prototyp (reines Python/NumPy, 469 Zeilen, keine Fremdmodelle) existiert und wurde ausgeführt: