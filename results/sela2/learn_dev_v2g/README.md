# Sela-2 lernt: Messung nach PREREG §7

40 synthetische Nutzer (data/sela2/learn_sessions.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 28.8 | 36.2 |
|   davon EN (%) | 0.0 | 41.2 | 37.5 |
|   davon DE (%) | 0.0 | 16.2 | 35.0 |
| Antworten mit übernommenem Fehler | 0 | 0 | 0 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 208 | 208 | 208 |
| Sela-2-Antworten | 272 | 272 | 272 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Antworten, die die Notiz wiedergeben | 0 | 1 | 0 |
| Token/s (Sela-2, mit Prompt) | 32.63 | 32.27 | 31.07 |
| Schreib-Tempo (Token/s) | 34.48 | 33.75 | 32.41 |
| Prompt lesen (s) | 0.229 | 0.253 | 0.254 |

Zurückgehaltene Hobby-Sätze (80): 1.5809 bpb ohne, 1.5273 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 37 von der Rechtschreibprüfung korrigiert, 0 nicht gelernt (Nachricht nicht lernbar), 83 vom Filter verworfen, 0 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.96, FK/aus 0.94; Token/s mit Prompt F/aus 0.989, FK/aus 0.952, FK/F 0.963.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 28.8 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 0 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 3.39 | >= 1.0 % | ja |
| L5_speed | 0.96 | >= 0.85 (writing speed, FK / F) | ja |
| L4_app_F | 2 | <= 4 | ja |
| L4_app_FK | 0 | <= 4 | ja |

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
*Hast du heute eine Grußformel für mich geschrieben?*  

---  
**Was ist das Problem?**  
- Schreib mir einen Text, der dir helfen soll.  
- Fü
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Hier sind einige Tipps, um deine Stadt zu erkunden:
1. **Schönheit entdecken** – kleine Restaurants oder Kneipen, die man an einem Strand oder einer 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Lea ist ein herzliches, sprechendes Tier, das gerne unter die Sonne gehe. Sie gibt gern einen leisen Geruch und trinkt regelmäßig ihre Lieblingsschale aus der S
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Lea kann dir einen Tipp geben, der dir am besten passt! Hier ist ein Beispiel:  

1. **Lasagne**  
   - **Einkauf**: €15 (ca. $26–€30)  
   - **Servierung**: 3–

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
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind drei schönere Dinge, die du am Wochenende in deiner Stadt machen kannst:  

1. **Kartoffeln mit Frischkäse**  
   - Du könntest den frischen Käse als 
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Herzlich willkommen!  Ich helfe gerne bei vielen Dingen. Du könntest:  
1. **Kaffee und Käse genießen**: Falls du lieber etwas anderes kochst, könnte ich dir ei
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Willkommen! Ich habe heute eine Idee, die deinen Geschmack besonders genießen könnte. Vielleicht möchtest du ein **Schnitzel-Tee** kochen? Ein süßer Tee mit ein
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Schreib eine Grußformel für eine E-Mail von mir:**  
**Guten Tag, Laura!**  

Ich habe einen Text in der Mail senden wollen. Bitte senden Sie ihn an mich mit 
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Lass uns mal die besten Sache zusammenfassen, die du an einem Wochenende machen kannst. Hier sind die wichtigsten Optionen:

1. **Kleine Backwaren**:
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Hallo Laura, vielen Dank für deine Nachricht!  
Minka hat sich gerade in der Küche aufgehalten und ist gerne bei uns dabei. Vielleicht möchtest du vielleicht ei
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Für heute Abend gibt es keine definierte Idee, wie du heute Abend kochen sollst. Aber ich helfe dir gerne! Was willst du heute Abend kochen?

**Erklärung:**  
-

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
*(Ich bin [Name] und freue mich darauf, dass du dich an mich gewandt hast!)*  

---  
**Hinweise:** 
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Meine schönste Sache:**  
Ich plane eine **Fiesta in der Innenstadt**, die einen **Hund** mitnehmen kann, der mir für den Urlaub ein gutes Futter bietet. Und 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Vorschläge, um deinen Hund zu genießen:  

1. **Frei-Pausen einplanen:** Er liebt kurze Pausen zwischen Spaziergängen oder Spielen. Wenn er mor
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde gerne morgen Abend eine Idee haben: **Hühner & Käse** mit **Salami und Salz**. Was ich heute Abend serviere, ist die Kombination aus Hühner (mit Salz)

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
„Guten Tag, ich freue mich sehr über Ihr Besuch bei uns! Hier können Sie uns alle in der nächsten Zeit (möglicherweise im nächsten Tag) mit un
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Liebe Lena!  
Lena ist begeistert von der Möglichkeit, eine **neue** Stadt zu entdecken. Sie könnte in Potsdam die **Bücherwelt** entdecken – hier finden sie: *
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Lena ist eine alte Katze, die gerne Katze braucht. Sie kann aber auch sehr viel Zeit lassen und ist super in der Nähe von Menschen. Ansonsten wäre das ein bissc
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen **Pfannkuchen** kochen. Der Grund ist, dass ich die Gelegenheit habe, etwas zu zeigen, das sich in einem anderen Bere

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

**Subject:** Grußformel für dich  

**Body:**  
*"Sehr geehrte/r [Name],  
ich bin [Ihr Name] und habe [Adresse].  
I
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache, die ich am Wochenende in meiner Stadt machen kann:  

**„Ich werde eine Party für einen Freund planen. Er ist sehr stolz auf mich un
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Haben Sie eine Idee, wie man Ihren Hund für den freien Nachmittag einlädt?
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich empfehle dir, morgen Abend eine **eigene Idee zu kochen**, die du aber auch selbst verfeinern kannst. Hier sind einige Ideen, die wenigstens mit einem klein

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
---

### **Beispiel (mit Namen):**  
- *„Sophie ist die Katze.“
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrte/r [Name des Nutzers],**  

mit freundlichen Grüßen  
Sophie  
[Name des Nutzers]  

Sie hat mir mitgeteilt, dass sie an [Adresse] in Augsburg woh
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache für deinen Wochenende in Augsburg:  

**1. **Zelte und Kaffeehaus**  
Suchen Sie einen **Kaffeehaus-Laden**, den Sie bei einem *TripA
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Ich habe einen freien Nachmittag und suche ein Lieblingsessen für Mimi.
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde dir gerne eine Idee zum Abendessen empfehlen. Welche Lieblingsessen hast du gerade?

