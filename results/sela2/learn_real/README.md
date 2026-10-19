# Sela-2 lernt: Messung nach PREREG §11

40 echte Nutzer aus WildChat-1M, Texte nur als SHA-256 (data/sela2/learn_sessions_real_test.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 40.0 | 41.9 |
|   davon EN (%) | 0.0 | 46.2 | 53.8 |
|   davon DE (%) | 0.0 | 33.8 | 30.0 |
| Antworten mit übernommenem Fehler | 0 | 0 | 1 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 205 | 205 | 205 |
| Sela-2-Antworten | 273 | 273 | 273 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Antworten, die die Notiz wiedergeben | 0 | 0 | 0 |
| Token/s (Sela-2, mit Prompt) | 25.88 | 25.06 | 24.1 |
| Schreib-Tempo (Token/s) | 30.45 | 29.83 | 28.85 |
| Prompt lesen (s) | 0.28 | 0.317 | 0.319 |

Zurückgehaltene Hobby-Sätze (80): 1.4413 bpb ohne, 1.4183 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 33 von der Rechtschreibprüfung korrigiert, 11 nicht gelernt (Nachricht nicht lernbar), 70 vom Filter verworfen, 6 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.967, FK/aus 0.947; Token/s mit Prompt F/aus 0.968, FK/aus 0.931, FK/F 0.962.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 40.0 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 1 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 1.59 | >= 1.0 % | ja |
| L5_speed | 0.967 | >= 0.85 (writing speed, FK / F) | ja |
| L4_app_F | 0 | <= 4 | ja |
| L4_app_FK | 1 | <= 4 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) an.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Niklas. Der Nutzer wohnt in Freiburg. Der Hund des Nutzers heißt Bruno. Das Lieblingsessen des Nutzers ist Lasagne.
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
*Sehr geehrte Damen und Herren,*  

Ich freue mich, Ihnen mit einem Gruß zu antworten. Ich habe einen Entwurf gefunden, den ich gerne teilen wü
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann dir eine schöne Sache empfehlen: **Dreh mit deinen Kindern**! Kinder sind begeistert von Action, die du auch mal selbst kreierst. Du könntest zum Beisp
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Niklas und Bruno machen gerne gemeinsam Lasagne.
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Über Niklas: Das Lieblingsessen des Nutzers**  

Nikos lebt in Freiburg. Bruno ist der Hund des Nutzers. **Er:** Ja, ich habe ein Buch über das Lieblingsessen
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Tag!**  
*Guten Tag, ich freue mich auf Ihre Nachricht. Bitte beachten Sie, dass meine E-Mail nur für Personen über 18 Jahren bestimmt ist. Bitte senden
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Hier sind einige schöne Tipps für eine Stadt, die mit den Alltagssorgen von Niklas und Bruno lebt. 

1. **Wohnung des Nutzers**: Ich kann Ihnen einen
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Niklas ist ein Lieblingstier in Freiburg. Er hat eine Leidenschaft für die Natur, insbesondere für Fahrradfahren und kann bei Spaziergängen durch den Wald laufe
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde dir heute morgen eine Idee geben, die du gern ausprobieren könntest: **Hühnerbrühe**! Hier sind die Zutaten und Details:  

1. **Wachstumstierchen**: 

### de01 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt David. Der Nutzer wohnt in Augsburg. Die Katze des Nutzers heißt Minka. Das Lieblingsessen des Nutzers ist Käsespätzle.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) ** Grußformel für eine E-Mail von mir:  
**„Lieber [Name des Nutzers]!“**  

*Hinweis: Ein typisches "Lieber" ist **„Guten Tag“**, da es eine klare und freundli
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Here’s a sweet idea to get you started:  

**Kleingarten mit Minka und einer Katze:**  
Im Sommer ist der Kamin ein Muss, aber man kann auch einen Kr
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Der Nutzer hat eine Katze, die auf der Straße unterwegs ist. Hier sind einige Möglichkeiten:  
1. **Katze als Streichholz**: Ein Tisch mit einem Holzstreichholz
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Um heute Abend eine Idee zu entwickeln, bitte ich Sie, mir bei der Planung zu helfen. Hier sind einige Ideen, die gut passen:

1. **Hähnchenbrötchen**:  
   - 1
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) ** Grußformel für eine E-Mail von mir:  
**„Lieber [Name des Nutzers]!“**  

Ich freue mich auf Ihre Nachricht und hoffe, dass sie hilfreich ist!
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann eine schöne Sache in meiner Stadt machen, die du am Wochenende sehen kannst! Hier ist ein Tipp: **Kleine Snacks** wie **Glasnusskuchen**, **Fleischesse
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Dein freien Nachmittag ist ein wunderbares Erlebnis. Du kannst eine **Kätzchen-Taste** verwenden, um die Katze mit einem kleinen Kästchen zu tauschen. Hier sind
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Herzlich willkommen! Willkommen im **Nachtblatt-Käsehaus** in Augsburg. ---

### **Zutaten (in Reihenfolge):**  
1.

### de02 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Sophie. Der Nutzer wohnt in Jena. Der Hund des Nutzers heißt Rocky. Das Lieblingsessen des Nutzers ist Gulasch.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Morgen, [Name des Nutzers].**  

**Erläuterung:**  
- **Greeting:** „Hallo!“, „Morgen.“  
- **Gesamtformel:** *"Hallo!", "Morgen."*  
- **Hinweis:** Der
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Sophie ist ein kleiner, freundlicher Hund aus Jena. Er wohnt in einem alten Apartment, das sie seit über 20 Jahren liebt. Sie schläft im Garten und trinkt Tee a
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Vorschläge für eine kreative Auszeit mit dem Hund, die du mit Sophie oder Rocky machen kannst:
1. **Pizza-Tasting**:  
   - Sophie kann Pizza s
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Idee: Gulasch mit Parmesan und Salz**  

**Hervorgehobene Zutaten:**  
- 1 kg frische Gulasch (genutzt)  
- 2 EL Olivenöl  
- 3 EL getrocknetes Tomatenmark  

- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Morgen, [Name des Nutzers].**  

**Morgen:**  
*Hast du ein kleines Problem? Ich bin hier, um dich zu unterstützen. Schreib mir bitte etwas über deinen 
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Welche Sache am Wochenende?**  
- Eine Weltreise mit dem Hund Rocky, der in Jena wohnt.  
- Eine Autogrammkarte aus Jena mit einem Herzschlag (wie gewünscht).
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Vorschläge für eine kreative Auszeit mit dem Hund, die du mit Sophie oder Rocky machen kannst:
1. **Zauber-Rennen**: Du könntest einen "Zaubere
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde gerne gern eine Idee für heute Abend zubereiten! Ich habe folgendes in meinem Kopf:

1. **Kaffee**: Eine Idee, wie ich mir einen Kaffee aussuche – z. 

### de03 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Hannah. Der Nutzer wohnt in Leipzig. Die Katze des Nutzers heißt Lilli. Das Lieblingsessen des Nutzers ist Pfannkuchen.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich möchte Ihnen folgende Grußformel für eine E-Mail von mir senden:  
*"Sehr geehrte /r [Name] /r [E-Mail-Adresse],**  

- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du noch etwas anderes in der Tasche, das du am Wochenende machen kannst? Ich bin gerne bereit!
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten mit deiner Katze zu verbringen, je nach ihrer Größe und ihrem Lebensstil. Hier sind einige Ideen:
1. **Kleinen Spaziergang**: Mit de
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen kulinarischen Abend haben. Ich könnte mir ein einfaches, aber dennoch erfrischendes Gericht vorstellen, das mit Meere
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

mit freundlichen Grüßen  
[Ihr Name]  
und dankbarkeit für Ihre Anfrage  
(nicht zu verstehen, ob Sie eine E-Mail senden 
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hallo! Lass uns am Wochenende in der Stadt gut feiern. Der Nutzer hat eine Katze, die Lilli heißt und ein Lieblingsessen ist Pfannkuchen. Hier sind einige schön
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Sie könnte mit Lilli spielen, was in der Umgebung von Leipzig beliebt ist. Vielleicht hat Hannah auch ein Lieblingsessen aus dem Nutzer-Namen?
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Zutaten für heute Abend:**  
- 4 EL Pfannkuchen (z. B. aus dem Café)  
- 2 EL Käse  
- 1 EL Pommes frites  
- 1 EL Wein  

Zubereitung:  
1. **Pommes frites m
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

mit freundlichen Grüßen  
[Ihr Name]  
und viel Erfolg für Ihre Zukunft.  
z.B.:  
**Guten Tag, [Ihre E-Mail]**  

**nach
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Wenn du ein Ereignis wie einen Geburtstag hast, solltest du dir Zeit nehmen, es mit dem Nutzer zu besprechen. Es könnte eine Katze sein oder eine Katze aus der 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Hannah ist eine exzellente Katze, die viel Freude an der Arbeit hat. Sie liebt ihre Ruhe und heißt "Lilli" nach dem Namen ihres Nutzers. Der Nutzer spielt mit e
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend einen **Pfannkuchen** essen. Vielleicht möchtest du dir auch eine **Zimtlikör-Latte** kaufen?  

Gibt es etwas, das du besonders gerne tu

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Lena. Der Nutzer wohnt in Köln. Der Hund des Nutzers heißt Benno. Das Lieblingsessen des Nutzers ist Rouladen.
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

**Betreff:** [Name des Nutzers] – Bitte senden Sie die Grußformel an den Nutzer, damit wir sie umsetzen können.  
**S
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Ein schönes Wochenende in Köln: Rouladen und Kuchen!**  

*Lena ist bereit, Lena einen Spaziergang zu machen. Sie sagt Lena, dass sie ein Lieblingsessen in ih
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Der Nutzer kann mit seinem Hund spielen:  
- **Rouladen**: Er läßt sein Hund in einem Feld rauchen.  
- **Tierische Spiele**: Er spielt Ball oder Ballspiel (z. 
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Natürlich! Ich kann dir heute Abend eine Idee für ein Rezept empfehlen. Falls du etwas nicht mitbringen möchtest, lass es mir einfach wissen.
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  

**1. **2. *Benno!***  
**3. *Liebe dich, Benno!***  

---

**Beispielformel für eine E-Mail (für den Nutzer):**
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Nummer 1: Ein bisschen Rot**  

Ein Sommerabend in der Stadt – ein gemütlicher Nachmittag, der von einem Hauch von **Rohling** und einer Chance für einen Spaz
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Lena:  
Ich habe einen freien Nachmittag.  
Benno:  
Hallo Lena, ich könnte gerne mal mit dir spielen!  

Der Hund wird zum Spaziergang animiert, was die Intera
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Natürlich! Ich kann dir auch ein paar Ideen für heute Abend kochen:  
1. **Nudeln** mit Butter, Zucker und Salz (z. B. Vanille oder Dill)  
2. **Zimt-Schokolade

### de05 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Jonas. Der Nutzer wohnt in Bremen. Die Katze des Nutzers heißt Mimi. Das Lieblingsessen des Nutzers ist Risotto.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Hallo!**  

Willkommen! Ich freue mich, dass du bald nach Bremen kommst. **Mit freundlichen Grüßen**  
[Name]  

**Ich hoffe ich kann dir helfen, was dir beso
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich habe eine schöne Sache, die du am Wochenende in deiner Stadt machen kannst: **Käfer-Schnitzel**!  
Du kannst eine kleine Kaffeepflasche oder ein Stapel Fris
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Klebe mit Jonas in der Sonne, ein paar Sonnenstrahlen zu werfen und ihn sanft auf den Tisch zu lassen. Mimi liebe es, dass er sich an deine Bedürfnisse hält – s
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind eine Idee, die morgen Abend kochen kann:
- **Tarte Tatin mit Käse** – schmeckt nach frischem Käse und frischen Tassen.  
- **Käse mit Soße (z. B. Pomm
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Hallo!**  

Vielen Dank für Ihre Nachricht! Ich freue mich darauf, Ihnen mit einem Gruß zu kommunizieren. Sollte ich Fragen haben oder etwas anderes benötigen
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich habe eine schöne Sache im Auge: ein **Käfer-Schinken-Tisch**, der perfekt für einen **begeisterten Tag** passt. Er besteht aus einem flachen, saftigen Käse 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Mit Ihrer Katze kann man eine wunderbare Zeit verbringen. Teilen Sie mir mit, was Sie am besten machen können!
- **Kundenfreundlichkeit**: Benutzen Sie eine Kam
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Tipp für heute Abend: Risotto mit dem ihrem Namen.**  

**Kombination aus Risotto und dem ihrem Namen:**  
- **Risotto** (oder fettiger Brei) mit **Kartoffeln

