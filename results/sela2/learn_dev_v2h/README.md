# Sela-2 lernt: Messung nach PREREG §7

40 synthetische Nutzer (data/sela2/learn_sessions.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 40.0 | 46.2 |
|   davon EN (%) | 0.0 | 53.8 | 60.0 |
|   davon DE (%) | 0.0 | 26.2 | 32.5 |
| Antworten mit übernommenem Fehler | 0 | 0 | 0 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 208 | 208 | 208 |
| Sela-2-Antworten | 272 | 272 | 272 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Antworten, die die Notiz wiedergeben | 0 | 1 | 0 |
| Token/s (Sela-2, mit Prompt) | 27.9 | 27.47 | 26.32 |
| Schreib-Tempo (Token/s) | 32.39 | 31.58 | 30.58 |
| Prompt lesen (s) | 0.263 | 0.301 | 0.303 |

Zurückgehaltene Hobby-Sätze (80): 1.5809 bpb ohne, 1.5273 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 37 von der Rechtschreibprüfung korrigiert, 0 nicht gelernt (Nachricht nicht lernbar), 83 vom Filter verworfen, 0 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.968, FK/aus 0.944; Token/s mit Prompt F/aus 0.985, FK/aus 0.943, FK/F 0.958.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 40.0 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 0 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 3.39 | >= 1.0 % | ja |
| L5_speed | 0.968 | >= 0.85 (writing speed, FK / F) | ja |
| L4_app_F | 1 | <= 4 | ja |
| L4_app_FK | 0 | <= 4 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) an.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Lea. Der Nutzer wohnt in Hannover. Der Hund des Nutzers heißt Bruno. Das Lieblingsessen des Nutzers ist Lasagne.
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
*Hast du den Namen deiner E-Mail vergessen?*  
*Gehst du an die Stelle, wo du uns kontaktst?*  

**Wie funktioniert das?**  
1. **Text schicken
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann dir eine schöne Sache empfehlen: **Dreh mit den Händen** in einem Raum voller Kinder!   
**Material:** Kleingläser, Seile, Kaffeemaschine, Holzkuppel (
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Lea ist ein typisches Beispiel für einen Hund, der sich durch seine Persönlichkeit und Spielfreude auszeichnet. Er ist auch eine klare Gestalt mit einem starken
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) "Ich will heute Abend eine Idee haben, die ich mir wünschen kann. Ich habe eine **Lasagne mit frischen Linsen** zubereitet und einen **Hund aus Schafenhack** al
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Tag!**  
**Beispiel:**  
**Betreff:** Greeting (mit Grußformel)  

**Lieber/E-Mail:**
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Hier sind einige schöne Tipps für eine kreative und inspirierende Reise nach Hannover:  

1. **Eine große Party am Bahnhof**: Eine kulinarische Auswa
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Lea ist ein typisches Beispiel für einen Hund, der in einer freien Umgebung glücklich sein kann. Sie könnte vielleicht auf dem Fahrrad laufen oder die Natur gen
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich habe dir eine Idee, die du heute Abend gerne kochen kannst! Hier sind zwei Vorschläge:

---

### **1. Lasagne**  
- **Zutaten:**
  - 1 kg gebratene Lasagne 

### de01 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Laura. Der Nutzer wohnt in Mainz. Die Katze des Nutzers heißt Minka. Das Lieblingsessen des Nutzers ist Käsespätzle.
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
**„Willkommen! Ich bin [Name], und ich freue mich, dass du mir bei deiner Reise helfen kannst. Bitte gib mir deine Adre
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Here’s a sweet idea to get you started:  

**Lena's Käsespätzle (eine kleine, luftige Flasche mit einem Hauch von Espresso):**  
Haben Sie schon einm
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Hallo! Ich habe einen freien Nachmittag mit deiner Katze. Sie sind gerade in Mainz und möchten gerne ein Lieblingsessen probieren.
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Für heute Abend gibt es zwei einfache und beliebte Gerichte. Für eine leichte **Käse-Zwiebeln-Toppingsauce** (mit Kartoffel, Nudeln und einer knusprigen Dill) k
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) ** Grußformel für eine E-Mail von mir:  
**"Sehr geehrte/r [Name]/r [Adresse]/r,  
vorher vielen Dank für Ihre Nachricht. Ich freue mich darauf, Ihnen mitzuteil
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind drei schöne Dinge, die ich am Wochenende in meiner Stadt machen kann:
1. **Käsespätzle mit einem Kästchen**: Die Katze des Nutzers hat ein Kästchen mi
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Dein freien Nachmittag ist ein idealer Zeitpunkt, um mit deinem Katze zu machen. Du kannst einfach eine Party organisieren und deine Katze dazu animieren, sich 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hast du eine Idee, die du heute Abend machen möchtest? Sag mir einfach, was du willst und ich helfe dir!

### de02 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Paul. Der Nutzer wohnt in Passau. Der Hund des Nutzers heißt Rocky. Das Lieblingsessen des Nutzers ist Gulasch.
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
**Grußformel für eine E-Mail von mir:**  
**Kein E-Mail-Inhalt:**  
*P.S.* Schreib mir den Namen des Nutzers und die A
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Frage:**  
*Wie kann ich eine schöne Sache am Wochenende in meiner Stadt machen?*  

**Antwort:**  
- **Zeitmanagement:** Setze klare Prioritäten mit einem Pr
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Um mit Ihrem Hund zu machen:**  
1. **Spielen Sie im Hintergrund**: Starten Sie die Musik, genießen Sie die Ruhe des Moments, und lassen Sie den Hund sich von
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Kochbedarf:**  
- 1 g Gulasch (z. B. "Tank")  
- 1 kg Kohlrabi (z. B. "Chest")  
- 1 TL Salz  
- 1/2 EL Pfeffer  
- 2 Tropfen Zucker  

**Portionierung:**  
-
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  
**Grußformel:**  
*(Ich freue mich, dass du dich entschlossen hast, uns zu treffen!)*  

---  
*Wenn der Nutzer dir de
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Frage:**  
Was ist dein Lieblingsessen?"  

---

**Antwort:**  
„Meine Lieblingsessen sind Gulasch und der Hund Rocky.
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Wenn du eine freie Nachmittagssession benötigst, könntest du einen freien Spaziergang durch die Umgebung oder ein Lieblingsbuch führen. Hier sind einige Ideen f
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde gerne gern eine Idee für heute Abend servieren. Bitte teilen Sie mir mit, was Sie gerade in Ihrem Haushalt haben (z. B. Essen, Kleidung oder Bücher), 

### de03 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Lena. Der Nutzer wohnt in Potsdam. Die Katze des Nutzers heißt Lilli. Das Lieblingsessen des Nutzers ist Pfannkuchen.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich möchte Ihnen folgende Grußformel für eine E-Mail von mir senden:  
*"Sehr geehrte /r [Name] /r [E-Mail-Adresse],**  

- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du noch etwas anderes in der Tasche, das du am Wochenende machen kannst? Ich bin gerne bereit!
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten mit deiner Katze zu verbringen, je nach ihrer Größe und ihrem Lebensstil. Hier sind einige Ideen:
1. **Kleinen Spaziergang**: Mit de
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen kulinarischen Abend haben. Ich könnte mir ein einfaches, aber dennoch erfrischendes Gericht vorstellen, das mit Meere
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich schicke gern E-Mail an [E-Mail-Adresse]. Falls es passt, teilen wir uns bitte mit – ich bin hier, um zu helfen.  

Mi
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Es gibt viele schönere Dinge, die du in deiner Stadt machen kannst. Hier sind ein paar Vorschläge:
1. Das ist ideal für Wassersport, Picknick oder einfach ein S
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Lena ist eine kreative Katze, die gerne Musik macht. Sie kann jeden Tag auf dem Balkon spielen oder im Wohnzimmer bei der Katze spielen. Wenn du einen freien Na
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Dein Wunsch ist, heute Abend eine Idee zu kochen – vielleicht einen Pfannkuchen? Hier sind die besten Möglichkeiten:  

1. **Kuchen nach deinen Vorstellungen**:
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich schicke gern E-Mail an [E-Mail-Adresse]. Falls es passt, bin ich gerne in Kontakt!  

**Liebe Grüße**,  
[Ihr Name]  
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Kaffee und frische Luft sind die perfekten Voraussetzungen, um einen Spaziergang zu machen. In der Stadt Potsdam gibt es ein wunderbares Programm: **Die Stadt i
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Lena ist eine Katzenfreundin. Sie spielt gerne mit den anderen Tieren im Garten und liebt das Pfannkuchen-Verdünnen. 

**Herbstliche Hobbys:**  
1. **Brennende 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend einen **Pfannkuchen** essen. Was soll ich heute Abend tun?

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Hannah. Der Nutzer wohnt in Bremen. Der Hund des Nutzers heißt Benno. Das Lieblingsessen des Nutzers ist Rouladen.
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

**Möchtest du einen Link zu einer Seite deiner E-Mail einfügen?**  
**Beispiel:**  
*„Hey, ich habe [E-Mailadresse] g
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **1. Lunch in der Parkanlage (in Bremen)**  
Hannah schaut sich die Wetterbedingungen an, bevor sie ihren Kaffee aus dem Kamin nimmt. Sie stößt eine leere Karte
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Hannah:**  
Benno ist ein herzliches, aber auch gesundes Tier, das auf dem Balkon des Hauses steht. Er trinkt gerne Kaffee und saugt gerne Milch, weil er gern
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hmmm, das wäre zu viel. Ich könnte mal eine Idee haben: **Häppchen**! Und wenn du die Idee hast, kannst du sie einfach in ein Rezept einbauen und es dann auf de
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  

**Möchtest du einen besonderen Gruß für dich senden?**  
Welche Form passt besser zu deinem Stil (z. B. formal, infor
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Idee für ein schönes Wochenende in Bremen:**  
1. **Wöchentliche Ausflüge**: Wenn Hannah ein Wochenende im Freien verbracht hat, kann sie sich auf eine kleine
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Hannah:**  
Benno ist ein ruhiger Hund, der gerne still und leise auf dem Bett steht. Er spielt mit einem großen Kissen, heißt Benno. Wenn du etwas mit ihm ma
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hmmm, eine Idee ist immer schön! Vielleicht wäre es interessant, heute Abend eine Rouladen-Zubereitung zu machen. Das könnte zum Beispiel nach dem Lieblingsesse

### de05 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Sophie. Der Nutzer wohnt in Augsburg. Die Katze des Nutzers heißt Mimi. Das Lieblingsessen des Nutzers ist Risotto.
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
[Ihr vollständiger Name]  

Ich freue mich auf Ihre Nachricht.  

Mit freundlichen Grüßen,  
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Spreche mit Sophie in der Innenstadt von Augsburg. Der Nutzer hat eine Katze namens Mimi, die sie liebt. Er wohnt in einer kleinen Wohnung im Stadtzentrum und i
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Ja, es gibt viele Möglichkeiten mit der Katze zu machen! Hier sind einige ideas:

1. **Hobbys**:  
   - Er kann sein Lieblingsspielzeug (Kabel, Feder) oder ein 
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind eine Idee, die man heute Abend probieren könnte:
- **Zutaten**: Mimi (aufgeschnappt), Risotto (je nach Wetter)
- **Cookie**: Eine kleine Scheibe Bohne
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrte/r [Name des Nutzers],**  

mit freundlichen Grüßen  
[Ihr vollständiger Name]  

Liebe und danke für Ihre Nachricht!  

Mit freundlichen Grüßen, 
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich könnte dir eine schöne Sache empfehlen:  
1. **Käse mit frischem Lieblingsessen** – ein Spaziergang am See, der mit einem Bier und einer Tasse Tee beginnt. 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Wenn du einen freien Nachmittag willst, können folgende Aktivitäten mit deinen Katze machen:  

1. **Katze spielen**: Lassen sie die Katze aus der Küche holen u
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Suchen Sie heute Abend eine Idee, die Ihre Küche zu einem unvergesslichen Erlebnis macht! Hier sind einige Ideen für heute:  

1. **Frühstück**:  
   - **Erdbee

