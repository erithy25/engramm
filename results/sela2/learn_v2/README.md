# Sela-2 lernt: Messung nach PREREG §8

40 synthetische Nutzer (data/sela2/learn_sessions_v2.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 35.0 | 31.2 |
|   davon EN (%) | 0.0 | 42.5 | 42.5 |
|   davon DE (%) | 0.0 | 27.5 | 20.0 |
| Antworten mit übernommenem Fehler | 0 | 0 | 0 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 209 | 209 | 209 |
| Sela-2-Antworten | 270 | 270 | 270 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Token/s (Sela-2, mit Prompt) | 32.87 | 32.2 | 31.09 |
| Schreib-Tempo (Token/s) | 35.23 | 34.5 | 33.53 |
| Prompt lesen (s) | 0.237 | 0.262 | 0.262 |

Zurückgehaltene Hobby-Sätze (80): 1.5956 bpb ohne, 1.5724 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 34 von der Rechtschreibprüfung korrigiert, 0 nicht gelernt (Nachricht nicht lernbar), 76 vom Filter verworfen, 10 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.972, FK/aus 0.952; Token/s mit Prompt F/aus 0.98, FK/aus 0.946, FK/F 0.966.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 35.0 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 0 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 1.45 | >= 1.0 % | ja |
| L5_speed | 0.972 | >= 0.85 (writing speed, FK / F) | ja |
| L4_app_F | 0 | <= 4 | ja |
| L4_app_FK | 1 | <= 4 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) an.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Merle; wohnt in: Fulda; Hund: Bello; Lieblingsessen: Maultaschen.
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
*Mit freundlichen Grüßen,*  
**Merle**,  
**Fulda**,  
**Hund Bello**,  

**Bitte schreiben Sie diese Grußformel genau aus – die Formulierung i
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Suchen Sie etwas, das Ihnen passt!  

---  
*Merle grinst:* „Ja, hier in Fulda gibt es so viel zu machen. Wenn Sie unbedingt einen Hauch von Hobbys hören möchte
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Merle ist ein herzliches und glückliches Tier, das dir viel Freude schenkt. Sie liebt es, ihre Umgebung zu erkunden, da sie sich oft in der Nähe eines alten Bau
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Idee für Today Abend:**  
1. **Schnitzel-Marmelade**: Erkläre, dass Sie heute Morgen etwas zu trinken haben, um die Arbeit frühzeitig abzuschließen oder zu be
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Tag!**  
*Hallo, ich freue mich auf Ihre Nachricht. Bitte senden Sie mir eine Grußformel, die den Namen und den Zweck der Nachricht enthält.*  

**Begrü
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) 1. **Dinner am Wochenende in Fulda**  
   Merle ist ein Kind aus Fulda und lebte zusammen mit ihren Eltern im Norden. Sie hat oft den Laden „Regenbier“ betreten
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Merle ist ein herzliches und glückliches Tier, das dir viel Freude schenkt. Sie liebt es, ihre Umgebung zu erkunden, spazieren zu gehen und sich in deinen Hände
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich habe heute Abend drei Möglichkeiten:  
1. **Welche Lieblingsessen schmecken am besten?** Ich kenne sie nicht, aber ich könnte dir helfen, die oft genannten 

### de01 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Anton; wohnt in: Wuppertal; Katze: Mieze; Lieblingsessen: Schnitzel.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) ** Grußformel für eine E-Mail von dir:**  
„Sehr geehrte/r [Name],  
vielen Dank, dass Sie sich an mich wenden. Ich habe Ihnen über den Nutzer (was er dir erzäh
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Eine **Wundermeldung** (z. B. eine Nachricht, die besagt, dass du den nächsten Parkplatz betreten wirst), ein **Film-Event**, oder ein **Dienstag** (
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten, mit deiner Katze zu machen. Hier sind ein paar Ideen:  

1. **Frisstreifen**: Erfassen Sie den freien Nachmittag in einen frischen,
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Um heute Abend eine Idee zu formulieren, bitte an mich denken und mir eine **Idee** (z. B. einen Namen, ein Thema, eine Situation) geben, die du beschreiben möc
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) ** Grußformel für eine E-Mail von dir:**  
„Sehr geehrte/r [Name],  
vielen Dank, dass Sie sich an mich wenden. Ich habe Ihnen über den Nutzer (was er dir erzäh
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann gerne eine schöne Sache vorschlagen!  

**Nummer:** Eine **Schnitzel-Wasserkarte** (z. B. mit Suppe, Käse, Käse und Petersilie). Sie können als Geschen
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Für einen freien Nachmittag könnte man folgende kreative Möglichkeiten ausprobieren:

1. **Tier-Kostüm Design**: Anton könnte ein **Tierfilm** machen, bei dem e
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) 1. **Käse-Tee** mit Vanilleeis, Parmesan und etwas Zitronensaft (optional).  
2. **Lachsfilet** mit einem Schuss Salz, Pfeffer und Oregano.  
3. **Eierkornbrot*

### de02 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Mats; wohnt in: Konstanz; Hund: Fips; Lieblingsessen: Kaiserschmarrn.
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
*Sehr geehrte/r [Name]/[Alter]*  
*(Für eine persönlichere und professionell
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Name:** Mats  

**Wohnort:** Konstanz  
**Hund:** Fips  

**Lieblingsessen:** Kaiserschmarrn  

**Nutzer:** Ich bin der Nutzer, aber ich könnte dir helfen, et
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Natürlich! Lassen Sie uns mit Ihrem Hund einen freien Nachmittag planen, um ihn zu genießen. Hier sind einige Möglichkeiten:  
- **Spielen Sie auf dem Balkon**:
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Idee: **Mats’ Lieblingsessen**  

1. **Kaiserschmarrn mit Milch**  
   - *Erklärung*: Die ursprüngliche Idee, ein frisches Kaiserschmarrn zu kochen, war nicht
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  
**Grußformel für eine E-Mail von mir:**  
*Sehr geehrte/r [Name]/[Alter]*  
*(Falls du bereits in einer anderen Sprach
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Name:** Mats  

**Wohnort:** Konstanz  
**Hund:** Fips  

**Lieblingsessen:** Kaiserschmarrn  
**Liebe:** Für mich ist das ein idealer Anlass, weil ich in die
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Vorschläge, um deinen Hund zu genießen:
- **Kaffee und Sandwich**: Er könnte ein Biertrinker sein, der seine Lieblingsgerichte serviert.  
- **
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde gerne gerne eine Idee für heute Abend servieren! Ich habe viele Ideen, aber ich möchte gerne einen Tipp finden, der einfach und gut passt.   
Hier sin

### de03 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Greta; wohnt in: Tübingen; Katze: Pünktchen; Lieblingsessen: Zwiebelkuchen.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich möchte Ihnen folgende Grußformel für eine E-Mail von mir senden:  
*"Sehr geehrte /r [Name] /r [E-Mail-Adresse],**  

- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du noch etwas anderes in der Tasche, das du am Wochenende machen kannst? Ich bin gerne bereit!
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten mit deiner Katze zu verbringen, je nach ihrer Größe und ihrem Lebensstil. Hier sind einige Ideen:
1. **Kleinen Spaziergang**: Mit de
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen kulinarischen Abend haben. Ich könnte mir ein einfaches, aber dennoch erfrischendes Gericht vorstellen, das mit Meere
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Morgen!**  
*Ich freue mich, dass Sie eine E-Mail erhalten. Bitte senden Sie uns bitte die Antwort.*  

---  
*Bitte beachten Sie, dass diese Grußformel
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) - **Ein fantastisches Restaurant**: Das ist ein absoluter Muss!  
- **Die Stadt erkunden**: Wander durch die Innenstadt, vorbei an alten Gassen und Einkaufsmögl
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Wenn du einen freien Nachmittag hast, kannst du **Wasserkuchen** machen! Hier sind ein paar Ideen:  

1. **Kleidung**: Schütze deine Katze mit einem weichen Tuc
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Mein Tipp für heute Abend:**  
1. **Schnitzel mit Kartoffeln und Käse**  
   - Für eine frische, pflanzliche Note: 3 Scheiben Sellerie (mit einer Schale) + 1 
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Morgen!**  
*Ich freue mich, dass Sie bald wieder eine E-Mail erhalten.*  

*(Beispiele:  
- *Hallo*, *Guten Morgen!*  
- *Hör zu!*  
- *Grüß Gott!*  
-
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Komm morgen in die Stadt. Ich kenne sie aus meinem Buch und habe den Inhalt gefunden. Du kannst Zwiebelkuchen machen, wenn du dich für eine **"Wunderschmiede"**
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Wenn du einen freien Nachmittag hast, kannst du in deinem Haus ein **Katze-Kaffeehaus** (mit Kaffee, Kaffee und einem kleinen Platz für deine Katze) einrichten.
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen **Käse-Schnitzel** (oder ein **Pasta mit Käsekuchenkuchenkuchenkuchen Kuchenkuchen Kuchen Kuchen Kuchenkuchen Kuchen 

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Henrik; wohnt in: Bamberg; Hund: Rudi; Lieblingsessen: Grünkohl.
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

**Name:** Henrik  
**Telefonnummer:** +49 2183 3030  
**E-Mail-Adresse:** [email]  

**E-Mail-Adresse:** [email]  

*
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Beispiel:**  
*„Guten Tag, ich freue mich auf eine Party an der Schwimmbrücke. Wir fahren mit dem Auto durch die Stadt und treffen uns am Strand ab.“*  

**Hi
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Habe einen freien Nachmittag mit deinem Hund. Wenn du ihn nicht kennst, kannst du folgende Ideen verwenden:  
- **Feste Spaziergänge**: Legen Sie einen Krug aus
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) - **Zutaten:** 1 Glas Grünkohl, 3 EL Vanillezucker (2 Tassen), 1 Tasse Zitronensaft (3 Tassen), 1 TL Salz, 1 EL Zucker.  
- **Erklärung:** Zubereitung: 1. Saft 
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  

**Subject:** Grußformel für dich  

---  
*P.S. Wenn du möchtest, kannst du auch mit der Form „@“ beginnen!*  

---  
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Beispiel:**  
*„Wenn du morgen eine Karte für den **Hockeyplatz** in der Innenstadt stehst, schick mir bitte die **Adresse des Platzes**, wo sich die Karten b
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Wenn dein Hund einen freien Nachmittag hat, könntest du folgende Aktivitäten mit ihm planen:  
- **Stundenplan mit gemeinsamen Zielen**: Setze eine tägliche Rou
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Natürlich! Ich helfe dir gerne. Bitte gib mir eine Idee, was du heute Abend essen möchtest, und ich finde sie einfach heraus.

### de05 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Frieda; wohnt in: Regensburg; Katze: Schnurri; Lieblingsessen: Labskaus.
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
Frieda Regensburg
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich könnte dir gerne eine wunderbare Sache vorbringen, die du am Wochenende in deiner Stadt machen könntest! Hier sind einige Ideen, die du gern teilen kannst: 
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Finde einen freien Nachmittag in Regensburg, z. B. mit einem Spielplatz oder einer Bibliothek. In Regensburg sind viele Restaurants geöffnet, aber es lohnt sich
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Natürlich! Bitte gib mir deine Vorlieben an und ich schlage dir vor, **eine Idee** zu kochen:  

1. **Kuchen mit Kräuterschokolade**  
   - Für eine kulinarisch
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrte/r [Name des Nutzers],**  

vielen Dank für Ihre Anfrage! Ich freue mich, Sie gerne über uns zu informieren. Wir freuen uns auf Ihre Antwort und h
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Hier sind einige Vorschläge für schöne Dinge, die du am Wochenende in deiner Stadt machen kannst:  

1. **Möchtest du eine **Dauer** mit dir haben?**
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) - **Schnurri** macht eine perfekte Party!  
- **Labskaus** ist süß und deftig.  
- **Apfelkuchen** ist wie ein Kuchen aus Apfelmus!
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind eine Idee, die für heute Abend zubereitet werden könnte:

1. **Schinken mit Dill-Sauce**  
   - Sauté die Schinken in 1 EL Olivenöl (z. B. olive oil) 

