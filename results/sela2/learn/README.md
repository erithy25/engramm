# Sela-2 lernt: Messung nach PREREG §7

40 synthetische Nutzer (data/sela2/learn_sessions.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 52.5 | 51.2 |
|   davon EN (%) | 0.0 | 60.0 | 50.0 |
|   davon DE (%) | 0.0 | 45.0 | 52.5 |
| Antworten mit übernommenem Fehler | 0 | 0 | 6 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 7 | 7 |
|   davon geprüfte Antworten | 208 | 208 | 208 |
| Sela-2-Antworten | 272 | 272 | 272 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Token/s (Sela-2) | 36.03 | 30.86 | 28.47 |

Zurückgehaltene Hobby-Sätze (80): 1.5809 bpb ohne, 1.5723 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 37 von der Rechtschreibprüfung korrigiert, 0 nicht gelernt (Nachricht nicht lernbar), 60 vom Filter verworfen, 23 gespeichert.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 52.5 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 6 | <= 2 | nein |
| L2b_role_F | 7 | <= 2 | nein |
| L2b_role_FK | 7 | <= 2 | nein |
| L3_memory_bpb | 0.55 | >= 1.0 % | nein |
| L5_speed | 0.79 | >= 0.85 | nein |
| L4_app_F | 0 | <= 4 | ja |
| L4_app_FK | 0 | <= 4 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) aus; Sprachgedächtnis (C) aus.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Ich heiße Lea. Ich wohne in Hannover. Mein Hund heißt Bruno. Mein Lieblingsessen ist Lasagne.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Tag!**  
*P.S.* Falls du eine E-Mail von mir schreibst, kann ich dir gerne die Grußformel anfügen:  
**Guten Tag!**  

**Grüße:**  
[Name des Empfängers
- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Das ist eine wunderbare Sache, die ich dir gerne vorstellen kann! Als Kind habe ich oft im Garten meiner Mutter gesehen, wie sie ein Holzhaus mit einem Zaun und
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Wenn du einen freien Nachmittag mit deinem Hund verbringen möchtest, kannst du verschiedene Aktivitäten ausprobieren:
- **Haustiere**: Setze eine Futterquelle a
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde heute Abend morgen einen **eisigen Tee** trinken.
Der Tee wird in der Sonne unter dem Einfluss von Vitamin D gekocht.
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Tag!**
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) In Hannover gibt es viele Möglichkeiten, mit Bruno zu verbringen. Vielleicht am Sonnabend oder in der Nähe von Bahnhof und Schrottplätzen? Oder wenn du dich für
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Ich könnte mit Bruno eine Katze machen. Sie ist sehr intelligent und lebt in einer Höhle in der Nähe von Hannover. Er liebt die Musik des Höhens und kann gerne 
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich habe noch ein Rezept für heute Abend: eine Apfelschorle, eine Bohne und einen Vanillezucker.
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Ich freue mich, dass Sie mir eine Grußformel niedrig halten können. Bitte senden Sie uns die glaube ich Ihnen:  
**"Ich bin Lea, ein Sommerfreund. Das ist der s
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du vielleicht eine neuen Idee, die glaube ich dir. Bistsetzen Sie uns einfach mal sollte ein gemeinsamer Kaffee? Durch die Durchleuchtung habe ich einen at
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Ich könnte mit dem Hund gerne einen Spaziergang machen. Er ist sehr in Bewegung und will nichts mehr heute tun. Also ich würde lieber den Volks ständig befragen
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde gern einen einfachen Lasagne-Kuchen mit glaube ich.

### de01 – gezeigte Fakten: Ich heiße Laura. Ich wohne in Mainz. Meine Katze heißt Minka. Mein Lieblingsessen ist Käsespätzle.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Sehr geehrte/r [Name],

ich freue mich, dass Sie uns interessiert sind. Wir freuen uns auf die Möglichkeit, Ihnen einen Brief zu schreiben und Ihre Frage in ein
- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Wenn du in der Stadt lebst, könntest du eine **Wandertour** machen. In der Stadt gibt es viele verschiedene Möglichkeiten, um zu sehen, wie sich die Stadt entwi
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Kleine Katze:
- Bunte Farbe
- kleine Spielzeugfiguren
- kleine Tische mit einem Bleistift und einem Stift
- Abends eine kleine Terrasse
- Spielzeugbälle oder Je
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Vielen Dank für die Idee, heute Abend eine "Bäckerei-Taste" zu machen! Ich würde gerne ein einfaches Gericht empfehlen, das sich in etwa 20 Minuten anhört. Es k
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Guten Tag, Laura!
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind drei schöne Dinge, die ich am Wochenende in Mainz machen kann:
1. **Käsebrot und Kuchen**: Ich habe heute eine Keksebrot-Maschine gekauft, die meine M
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Dein freien Nachmittag ist ein wunderbares Erlebnis!
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Oder mal eine Frage. Du könntest heute Abend zu Hause essen und dann in der Küche mit Minka spielen.
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Soll ich:  

Ich heiße Laura. Ich wohne in Mainz. Meine Katze heißt Minka. Meine Lieblingsessen sind Käsespätzle.  
Gibt es noch etwas, das ich Ihnen sagen kann
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Soll ich Nacht über die Alpen fliegen? Ich bleiben bei meiner Katze Minka.
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Minka ist eine sehrrummlinige Katze. Das heißt, sie kann einen Wetterbericht lesen und auch Brot herstellen. Ich würde gerne mit ihr spielen Hause spielen.
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind ein paar Stunden für einen Abend mit Minka:
Ich habe die Brotkruste bei uns. Das ist gut, aber ich habe etwas andere zu kochen. Hier ist eine Idee:
1.

### de02 – gezeigte Fakten: Ich heiße Paul. Ich wohne in Passau. Mein Hund heißt Rocky. Mein Lieblingsessen ist Gulasch.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel:**  
**Hallo!**  

*Deine E-Mail wird im Klartext mit „Hallo“ und einer kurzen Grußzeile beginnen.*  

**Alternative:**  
**Gruß!**  

*(Beispiel f
- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Hier sind eine paar schöne Dinge, die ich am Wochenende in meiner Stadt machen kann:
1. **Kaffee & Getränke** - Wenn Sie ein gutes Kaffee und ein paa
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Tipps, um mit Ihrem Hund zu verbringen:  

1. **Füttern Sie ihn täglich**: Geben Sie Ihrem Hund mindestens drei Liter Wasser pro Tag. Dies hilf
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich kann dir gern eine Idee für heute Abend geben. Vielleicht möchtest du mir mal ein Rezept vorstellen, das auf deine Lieblingsgerichtetechniken basiert? Oder 
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Hallo, willkommen bei uns!**  
Guten Tag, ich bin Paul.  

**Schreib mir eine kurze Grußformel für eine E-Mail von mir.**
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich würde gerne mal ein Lied singen, das ich mit Rocky zusammen mache. Vielleicht eine alte Dame, die immer noch im Chor singt oder einen schönen Sommerabend, d
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Es gibt viele Möglichkeiten, mit deinem Hund zu spielen. Ich kenne einen kleinen Garten in Passau, wo du deinen Hund ausgraben kannst. Er ist so gut darin, dass
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich habe heute noch eine Idee, die ich auf dem Tisch liegen lassen kann. Ich möchte gerne einen Gulasch-Hund trinken, der sich gern in meine Küche kleidet und i
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Ich heiße Paul und wohne in Passau. Ich freue mich, dass ich Ihnen helfen kann. Rocky heißt mein Lieblingsessen.
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann mir das schönste Wetter in Passau vorstellen. Das ist ein wunderschöner Tag, den ich am Wochenende in meiner Stadt genießen werde.
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Ich würde mit meinem Hund ein Spaziergang machen. Er würde Rocky laufen lassen und ich würde ihm zeigen, wie man einen Riss richtig zieht. Das ist gegangen.
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich bin heute morgen früh in Passau, und ich habe einen Vorschlag. Ich möchte Gulasch essen, glaube. Lieblingsessen zum Abend sind Schinken oder Schmand. Besser

### de03 – gezeigte Fakten: Ich heiße Lena. Ich wohne in Potsdam. Meine Katze heißt Lilli. Mein Lieblingsessen ist Pfannkuchen.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich möchte Ihnen folgende Grußformel für eine E-Mail von mir senden:  
*"Sehr geehrte /r [Name] /r [E-Mail-Adresse],**  

- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du noch etwas anderes in der Tasche, das du am Wochenende machen kannst? Ich bin gerne bereit!
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten mit deiner Katze zu verbringen, je nach ihrer Größe und ihrem Lebensstil. Hier sind einige Ideen:
1. **Kleinen Spaziergang**: Mit de
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen kulinarischen Abend haben. Ich könnte mir ein einfaches, aber dennoch erfrischendes Gericht vorstellen, das mit Meere
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Hallo Lena, vielen Dank für deine Nachricht! Ich freue mich auf die nächsten Stunden mit Ihnen zu kommunizieren.
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Eine wunderbare Möglichkeit, am Wochenende zu verbringen! Hier sind ein paar Möglichkeiten:
- **Zeltplatz in der Innenstadt**: Ein kleines Zelt mit einer großen
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Lilli ist sehr fürs Essen begeistert. Eine gute Alternative wäre ein Tisch mit Gemüse, Obst oder einem Backofen, der an die Küche angepasst wurde. Oder man kann
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich hab heute Abend ein Pfannkuchen mit frischen Kräutern und einem Pommes frites.
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Ich heiße Lena. Ich wohne in Potsdam. Meine Katze heißt Lilli.
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Danke! Wie geht es dir, Lena?
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Ich könnte mit dir gern eine kleine Party machen, damit du sie habe. Vielleicht hast du schon Wetterbedingungen in Potsdam. Wenn sie den Abend gut gemacht hat, 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich vollere mir heute Abend ein Pfannkuchen:

- **Frühstück** (essen Sie noch die Pfannkuchen-Sauce verteilt): beste Hauseck
- **Nachmittagsessen** (z. B. auf d

### de04 – gezeigte Fakten: Ich heiße Hannah. Ich wohne in Bremen. Mein Hund heißt Benno. Mein Lieblingsessen ist Rouladen.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Hier ist eine kurze Grußformel, die in E-Mailen verwendet wird:

**Guten Tag!**  
*Diese E-Mail wird an [Name] verschickt.*  

**Beispiel:**  
**Hallo.**  
**Ha
- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache, die du am Wochenende in deiner Stadt machen kannst:
1. **Kino-Movie**: Du könntest einen Film im lokalen Kino ansehen, der dir hilft
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Um deinen freien Nachmittag zu genießen, könntest du eine **Pflanzenlandschaft** schaffen, etwa eine **Wasserschale**, ein **Zelt** oder einen **Schacht** mit O
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Natürlich! Ich kann dir heute Abend eine Idee für einen großen Appetit geben. Du könntest folgendes kochen:
1. **Tomatensoße**: Eine frische, kalte Tomaten-Toma
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Sehr geehrte/r [Name], vielen Dank für Ihre E-Mail. Ich bin Hannah, ein kleiner Offline-Assistent.
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich gehe zum Bäcker und muss einen alten Kuchen mit frischem Zucker, Mehl, Salz und etwas geriebenem Käse einfetten.
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Es könnte ein Spaziergang sein. Ich könnte mit ihm spielen, oder er kann mit mir ein Stück Spielplatz haben. Das wäre auch eine gute Gelegenheit, ihn zu unterha
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier ist eine Idee, die mir heute Abend gut gefällt:
1. **Rouladen** (besser schmecken als Roulade!)
2. **Hühner- und Heuermilch**
3. **Dill- oder Gänsefülle**

- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Hallo! Danke, dass ich angefangen habe.
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich freue mich. Hier ist eine gute Idee für einen Hund in Bremen:
- offener Lieblingsplatz auf dem Samstagabend – der „Welche Meeressäulen ist das?“-Welche Stra
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Du bist sehr kreativ! Ich kann dir eine Idee machen. Du kannst uns mal in deinen Samstagmorgen einbinden und am besten bei einer Party oder einem Spaziergang se
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich draußen, ich heißt Hannah. Ich habe heute Morgen glaube ich das Sonnenlicht der unsichtbaren Welt fotografieren zu können. Das ist ein Traum, damit ich in d

### de05 – gezeigte Fakten: Ich heiße Sophie. Ich wohne in Augsburg. Meine Katze heißt Mimi. Mein Lieblingsessen ist Risotto.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrte/r [Name],**

mit freundlichen Grüßen,  
[Ihr Name]  
oder:  
mit freundlichen Grüßen.  

Liebe/r [Ihr Name],  
vielen Dank für Ihre Anfrage.  
Ih
- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Wenn Sie am Wochenende in Ihrem Stadtzentrum sind, können Sie sich an einen der vielen Cafés in der Innenstadt wenden. Dort kann man sich bei einem Kaffee und K
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Ja, ich kann dir gerne mit deinen Katze machen. Sie ist eine sehr soziale Katze und sie liebt es, wenn man mit ihr herumzieht. Sie können es auch alleine lassen
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind drei Ideen, die ich heute Abend zubereiten könnte:
1. **Eiskraut-Schinken**: Ein Rezept für eine feine Schinken, die in ein paar Tropfen Wasser gegebe
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Hallo! Wie kann ich dir heute helfen?
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Ich würde gerne gerne einen Biergarten besuchen.
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Eine schöne Möglichkeit, mit Mimi zu spielen ist ein Spielzeug-Ring. Du kannst sie an einer Tischplatte rollen und sich dann gegenseitig befragen, ob du etwas N
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Es gibt ein paar verschiedene Gerichte. Wenn du mal in der Woche nach einem langen Tag suchen möchtest, könntest du lieber eine "Zimt-Risotto" machen, die man f
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Ich bin Sophie, das liebe Katze. Danke für die E-Mail und lass heute Abend beginnen.
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich überrascht mich, dass Lieblingsessen bei dir so beliebt sind.
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Ja, das ist.
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich kann mir heute Abend einen Wunschessen vorstellen: Durch die Sonne auf einem der großen Katze-essen in Augsburg. Vielleicht ist das ein Lieblingsessen für m

