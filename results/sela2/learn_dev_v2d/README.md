# Sela-2 lernt: Messung nach PREREG §7

40 synthetische Nutzer (data/sela2/learn_sessions.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 30.6 | 38.1 |
|   davon EN (%) | 0.0 | 41.2 | 40.0 |
|   davon DE (%) | 0.0 | 20.0 | 36.2 |
| Antworten mit übernommenem Fehler | 0 | 0 | 1 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 208 | 208 | 208 |
| Sela-2-Antworten | 272 | 272 | 272 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Token/s (Sela-2, mit Prompt) | 32.02 | 32.04 | 30.43 |
| Schreib-Tempo (Token/s) | 33.86 | 33.74 | 32.5 |
| Prompt lesen (s) | 0.242 | 0.264 | 0.264 |

Zurückgehaltene Hobby-Sätze (80): 1.5809 bpb ohne, 1.5292 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 37 von der Rechtschreibprüfung korrigiert, 0 nicht gelernt (Nachricht nicht lernbar), 83 vom Filter verworfen, 0 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.963, FK/aus 0.96; Token/s mit Prompt F/aus 1.001, FK/aus 0.95, FK/F 0.95.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 30.6 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 1 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 3.27 | >= 1.0 % | ja |
| L5_speed | 0.963 | >= 0.85 (writing speed, FK / F) | ja |
| L4_app_F | 2 | <= 4 | ja |
| L4_app_FK | 1 | <= 4 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) an.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Lea; wohnt in: Hannover; Hund: Bruno; Lieblingsessen: Lasagne.
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
*Liebe Lea, ich freue mich, dass du dich über mich informieren kannst.*  

**Möchtest du noch etwas Besonderes hören?**  
Du bist in Hannover g
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Haben Sie ein Lieblingsessen in Ihrer Stadt, das Sie besonders empfehlen möchten?
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Lea ist ein herzliches, sanftes Wesen mit einem leichten Charme. Du kannst es mit einem heißen Kaffee oder einer sanften Katze gerne spielen lassen. Wenn du Lus
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Lea kann dir bei der Planung helfen, aber sie ist nicht verpflichtet, auf eine Idee zu achten.  
Für eine Idee benötige ich Informationen wie:  

1. **Welche Sp
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Tag!**  
*Hast du den Namen des Nutzers gelesen?*  

**Ich habe die Grußformel in meinem Wörterbuch gefunden. Hier sie:**  
**Guten Tag!**  

**Nur wenn
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Hier sind einige Tipps, um deine Stadt zu erkunden:
essen: H ständig auf der Suche nach „themen des Tages“ – glaube an die Sterne.
zuerst: Kaufen Sie
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Lea ist ein liebevoller Hund, der gerne mit Freunden in der Natur tauchen und bei der Jagd spielt. Sie hat einen dicken, runden Kopf und eine neugierige Nase. D
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich habe dir heute Morgen eine Idee, wie du gerne etwas kochen kannst. Brauchst du Tipps oder findest du viele Vorschläge?

### de01 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Laura; wohnt in: Mainz; Katze: Minka; Lieblingsessen: Käsespätzle.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Schreib eine Grußformel für eine E-Mail von mir:**  
**Guten Tag, [Name]!**  

**Gruß:** *„Ich freue mich auf Ihre Nachricht. Bitte senden Sie uns die Informa
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Laura; wohnt in: Mainz; Katze
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Herzlich willkommen!  Ich helfe gerne bei vielen Dingen. Du könntest:  
1. **Kaffee und Käse genießen**: Falls du lieber etwas anderes kochst, könnte ich dir ei
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Willkommen! Ich habe heute eine Idee, die deinen Geschmack besonders genießen könnte. Vielleicht möchtest du ein **Schnitzel-Tee** kochen? Ein süßer Tee mit ein
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Schreib eine Grußformel für eine E-Mail von mir:**  
**Guten Tag, Laura!**  

*(Bitte beachten Sie: Die E-Mail muss mindestens einen Namen enthalten und in de
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind zwei schöne Dinge, die ich am Wochenende in meiner Stadt machen kann:  

1. **Ein Ausflug ins Mainz-Museum**: Ich kann einen Lieblingssprung mit uns m
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Hallo Laura, vielen Dank für deine Anmeldung! Du kannst gerne einen freien Nachmittag mit deinem Katze machen. Hier sind ein paar Vorschläge:  

1. **Kaffee und
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Für heute Abend gibt es keine Stunden, um zu Hause zu kochen! Ich würde gerne eine Idee vorschlagen, die du dir heute morgen vorstellst. Bist du noch etwas in d

### de02 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Paul; wohnt in: Passau; Hund: Rocky; Lieblingsessen: Gulasch.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  
**Grußformel:**  
$$
\x[A-Za-z]{3} \quad [P.S.]
$$  
**Weitere Informationen:**  
- Schreibe den Namen (der du in dein
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Meine schöne Sache:**  
Ich kann:  
1. **Süßes Gericht zubereiten**: Ich kann nachfragen, wie es in der Küche schmeckt (z. B. in einem Teller oder auf einem T
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Paul: Ich möchte mit ihm spielen, weil er das letzte Spiel der Saison gewonnen hat. Rocky: Er liebt es zu essen!  

**Antwort:**  
Paul: Ich könnte mit Rocky ei
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Koching-Idee:**  
1. **Espresso mit Bohnen**: 1 TL Espresso (z. B. "Grape Espresso" oder "Tarte Tatin") mit etwas Salz, Pfeffer und Oregano.  

2.
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  
**Grußformel:**  
$$
\x[A-Za-z]{3} \quad [N \Aa] \text{Anmerkung}.
$$  

**Beispiel:**  
**E-Mail:**  
> „Ich habe ein
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Meine schönste Sache:**  
Ich schaue am Himmel und bin ein Kind der Sonne, das sich in den Wolken spüre. Der Himmel brennt sanft, doch ich trage den Blick für
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Vorschläge, um deinen Hund zu genießen:  

1. **Frei-Pausen einplanen:** Er braucht Ruhe, um sich zu entspannen.  
   - **Nähe suchen:** Wähle 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich bin heute Morgen in Passau, und gerne gibt es eine Idee zu kochen. Ich würde gern etwas probieren:
- **Hühner**: Achte darauf, dass der Lieblingsessen gut i

### de03 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Lena; wohnt in: Potsdam; Katze: Lilli; Lieblingsessen: Pfannkuchen.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich möchte Ihnen folgende Grußformel für eine E-Mail von mir senden:  
*"Sehr geehrte /r [Name] /r [E-Mail-Adresse],**  

- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du noch etwas anderes in der Tasche, das du am Wochenende machen kannst? Ich bin gerne bereit!
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten mit deiner Katze zu verbringen, je nach ihrer Größe und ihrem Lebensstil. Hier sind einige Ideen:
1. **Kleinen Spaziergang**: Mit de
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen kulinarischen Abend haben. Ich könnte mir ein einfaches, aber dennoch erfrischendes Gericht vorstellen, das mit Meere
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel:**  
„Guten Tag, ich freue mich sehr über Ihr Gespräch und freue mich, Ihnen bei Fragen zur Verfügung zu stellen. Setzen Sie sich bitte so oft wie 
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) 1. **Stadtbibliothek**  
   - Gibt eine Sammlung von Büchern und Artikeln zurück, die dir helfen, deine Arbeit zu verstehen.  
   - Ein guter Ort, um dich mit B
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Lena ist eine echte Katze. Sie liebt ihren Platz im Garten und mag es, wenn man ihr Futter gibt. Ihr Lieblingsessen ist Pfannkuchen.
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Bitte schaue dir die Details an:  

- **Barbecue mit Tomatensauce**: Ein kühner Tomatensaft, geräuchert mit Salz und Pfeffer.  
- **Zitrone**: Eine Prise frisch
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel:**  
„Guten Tag, ich freue mich über deine Nachricht! Wie kann ich dir helfen?“  

---  
*Note: Diese Grußformel ist grammatikalisch korrekt und be
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Kaffee und Lilli!
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Lena ist eine zuverlässige Katze, die sehr gerne mit dir spielen kann. Wenn du möchtest:  
1. **Schnellere Hobbys:** *Kaffee oder Pizza machen* (z. B. beißen, i
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend einen **Pfannkuchen** in der Küche genießen. Ziehe einfach den Teig aus der Schüssel und koche ihn mit Salz und Pfeffer auf einem Kucheng

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Hannah; wohnt in: Bremen; Hund: Benno; Lieblingsessen: Rouladen.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  

**Subject:** Grußformel für dich  

**Body:**  
*"Sehr geehrte/r [Name], ich bin [Name des Ansprechers] und freue mic
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache, die ich am Wochenende in meiner Stadt machen kann:  

**Kaffeebohnen im Garten – ein Picknick mit Freunden**  
Haben Sie den Mut, ei
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Möglichkeiten, deinen Hund zu genießen:  

1. **Rouladen sammeln**: Hänge ein Ei oder einen Teig aus und sammle ihn auf dem Tisch. Sie können a
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich empfehle dir, **keine festen Mahlzeiten zu essen**, um den Tag voran zudecken zu können. Falls du etwas anderes möchtest (z. B. ein Lieblingsessen oder eine
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  

**Welche Brennpunkte möchtest du auf dieser Nachricht sind?**  
- **Der Nutzer:** Name: Hannah; wohnt in Bremen; Hund
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache, die ich am Wochenende in Bremen machen kann:  

Ich habe ein **Pflanzen-Event** geplant, bei dem Pflanzen aus der Region von Bremen 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Möglichkeiten, deinen Hund mitzunehmen:  
1. **Welche Lieblingsessen sollte ich malen?** Falls es etwas gibt, das du gerne ausprobieren möchtes
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Brot:**  
„Hannah, was würdest du heute Abend kochen? Ein typisches Bremen-Brot mit wenig Fett und weniger Zucker.“  

**Antwort:**  
„Ich würde gerne einen *

### de05 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Sophie; wohnt in: Augsburg; Katze: Mimi; Lieblingsessen: Risotto.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrte/r [Name des Nutzers],**  

mit freundlichen Grüßen  
Sophie  
[Name des Nutzers]  

z. B.:  
„Guten Tag Sophie! Schön, dass du hier bist!“,  

un
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache für deinen Wochenende in Augsburg:  

**1. **Zelte und Kaffeehaus**  
Suchen Sie einen **Kaffeehaus-Laden**, den Sie auf der Suche na
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Hier sind einige Möglichkeiten, deine Katze zu genießen:
1. **Tennis- oder Badewanne mit Holzrohre**:  
   - *Karten:* Hölzerne Stühle oder Kissen mit Kamm für 
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Satz:**  
Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Sophie; wohnt in:
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrte/r [Name des Nutzers],**  

mit freundlichen Grüßen  
Sophie  
[Name des Nutzers]  

Falls du möchtest, kann ich dir auch die Grußformel in deutsc
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache für deinen Wochenende in Augsburg:  

**1. **Zelte und Spiele**  
In der Stadt gibt es viele Möglichkeiten, wie du dein Zuhause gesta
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Sophie; wohnt in: Augsburg; K
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Ich werde dir heute Abend etwas empfehlen, aber nur dann, wenn es passt.**  

### **1. Risotto mit Brutkäse (für 4 Personen):**  
- **Steuer**: 1/4 *10g* (ode

