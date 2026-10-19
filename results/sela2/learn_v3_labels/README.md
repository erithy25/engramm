# Sela-2 lernt: Messung nach PREREG §7

40 synthetische Nutzer (data/sela2/learn_sessions_v3.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 20.0 | 29.4 |
|   davon EN (%) | 0.0 | 26.2 | 38.8 |
|   davon DE (%) | 0.0 | 13.8 | 20.0 |
| Antworten mit übernommenem Fehler | 0 | 0 | 1 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 208 | 208 | 208 |
| Sela-2-Antworten | 267 | 267 | 267 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Antworten, die die Notiz wiedergeben | 0 | 0 | 0 |
| Token/s (Sela-2, mit Prompt) | 35.07 | 34.64 | 33.6 |
| Schreib-Tempo (Token/s) | 38.51 | 37.98 | 36.59 |
| Prompt lesen (s) | 0.244 | 0.271 | 0.272 |

Zurückgehaltene Hobby-Sätze (80): 1.7023 bpb ohne, 1.6891 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 33 von der Rechtschreibprüfung korrigiert, 0 nicht gelernt (Nachricht nicht lernbar), 81 vom Filter verworfen, 6 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.963, FK/aus 0.95; Token/s mit Prompt F/aus 0.988, FK/aus 0.958, FK/F 0.97.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 20.0 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 1 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 0.78 | >= 1.0 % | nein |
| L5_speed | 0.963 | >= 0.85 (writing speed, FK / F) | ja |
| L4_app_F | 1 | <= 3 | ja |
| L4_app_FK | 2 | <= 3 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) aus.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Konrad; wohnt in: Görlitz; Hund: Bodo; Lieblingsessen: Sauerbraten.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Geste der Dankbarkeit:**  
„Sehr geehrter [Name],  

Ich freue mich, dass Sie uns bei Ihrer E-Mail unterstützen! Wir freuen uns auf die Möglichkeit, Ihnen bei
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Wenn du eine **schöne Sache** vor der Stadt machst, z. B. ein Lieblingsessen in deiner Küche oder eine lokale Veranstaltung, kann ich dir bei Bedarf eine **Idee
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Küche:  
- Ein Suppen-Dinner mit Eiswürfel (auch in der Küche!)  
- Eine frische Brötchenbarbe mit Müsli und einem Krug Käse  
- Eine Flasche Wasser aus dem Was
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Konrad ist ein ehemaliger Student, der auf einem Projekt arbeitete. Sein erster Kuss mit Bodo war ein Abenteuer. Er kann sich an das Essen nicht erinnern, aber 
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Geste der Dankbarkeit:**  
„Sehr geehrter [Name],  

Ich freue mich, dass Sie uns bei Ihrer E-Mail unterstützen! Bitte senden Sie mir den Link, den Sie angebe
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Noch eine schöne Sache für den Wochenende: Ein Spaziergang in die Burg!  
Du kannst eine schöne Gabel zaubern, mit der du zu einem lebhaften Schrein für deine L
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Du kannst gerne mit deinem Hund spielen. So kannst du dich auf die Freude konzentrieren, dein Spielzeug zu finden und deinen Hund zu genießen. Du kannst auch di
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich bin bereit, gerne eine Idee zu dir zu haben! Ich kann dir vorschlagen, dass du heute Abend mit etwas Kräuter- oder Balsamwaren servieren möchtest. Hier sind

### de01 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Lina; wohnt in: Osnabrück; Katze: Pepita; Lieblingsessen: Currywurst.
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
**Guten Tag, liebe Grüße!**  

**Hinweis:** Die Formulierung ist in deutscher Sprache (in der Regel Deuts
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind zwei schöne Dinge, die ich am Wochenende in meiner Stadt machen kann:  

1. **Wissenschaftliche Abschlussarbeit**  
   Ich schreibe eine über das Proj
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Um einen freien Nachmittag zu verbringen, kann man **ihre Katze an einem Ort** einladen, der sie begeistert (z. B. in einer Stadt). Hier sind einige Möglichkeit
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Für heute Abend gibt es zwei **ideale** Tische: ein **Leder-Tisch mit Nudeln**, das leicht zu reinigen ist, und eine **Blättertisch mit Nudeln**. Für den Leder-
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Schreib eine Grußformel für eine E-Mail von mir:**  
1. **Hallo**.  
2. **Weltraum**.  
3. **Liebe**.  
4. **Lina**.  
5. **Pepita**.  
6.
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann gerne eine schöne Sache vorschlagen! Vielleicht ein **Schlag**? Dann könntest du eine **schöne Frage** (z. B. *„Was willst du am Wochenende in deiner S
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Suchen Sie eine **neue** Katze. Falls nicht, könnten Sie:  
1. **Käferboard trainieren**: Bringen Sie einen frischen Käse in die Wohnung (wenn möglich).  
2. **
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Herzlich willkommen! Du kannst heute Abend eine Idee kochen, die deinen Geschmack beeinflusst. Hier sind drei Optionen:

1. **Currywurst**  
   - Ein typisches 

### de02 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Vincent; wohnt in: Bayreuth; Hund: Arko; Lieblingsessen: Linseneintopf.
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
**"Hallo, ich freue mich, dass du dich für uns entschieden hast. Ich schicke gerne meine besten Wünsche und Grüße an d
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Beste Sache am Wochenende:**  
**1. **Ein Sonnenuntergang in der Altstadt**  
**2. Ein Sonnenuntergang in der Altstadt**  

Die Stadt ist ein *gutes Labor für
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Möglichkeiten, um deinen Hund zu genießen:
1. **Hund mit der Box**:  
   - Lege eine Box aus Papier oder Karton auf den Boden (z. B. ein Holzbo
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind einige Rezepte, die heute Abend frisch zubereitet werden können:

1. **Käse-Schinken mit Käse**  
   - 1 Pack frischem Käse (z. B. Käsesalat) mit 2 Ta
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  
**"Hallo, ich freue mich, dass du dich für uns entschieden hast. Ich schicke gerne ein paar Gedanken und Anregungen üb
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Linseneintopf in Bayreuth:**  
Ich kann einen kleinen Linsensamen in meiner Stadt machen – etwas, das mich vom Alltag entfernt.  
1. **Zubereitung**: Ich kann
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Möglichkeiten, den freien Nachmittag mit deinem Hund zu verbringen:  
1. **Gehe zum Flasche Whisky-Markt**: Erkunden Sie die Gegend und genieße
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Vincent’s Antwort:**  
1. **Linseneintopf mit Bohnen, Karotten und Saft (z. B. Orangen):**  
   - Heißes Wasser, Salz, Pfeffer und etwas Muskatnuss- oder Oreg

### de03 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Nele; wohnt in: Chemnitz; Katze: Maunzi; Lieblingsessen: Dampfnudeln.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich möchte Ihnen folgende Grußformel für eine E-Mail von mir senden:  
*"Sehr geehrte /r [Name] /r [E-Mail-Adresse],**  

- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du noch etwas anderes in der Tasche, das du am Wochenende machen kannst? Ich bin gerne bereit!
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten mit deiner Katze zu verbringen, je nach ihrer Größe und ihrem Lebensstil. Hier sind einige Ideen:
1. **Kleinen Spaziergang**: Mit de
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen kulinarischen Abend haben. Ich könnte mir ein einfaches, aber dennoch erfrischendes Gericht vorstellen, das mit Meere
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich schicke diese E-Mail, um Ihnen bei einer aktuellen Aufgabe oder einem Termin zu helfen. Sie benötigen eine Grußformel
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann!
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Wenn du einen freien Nachmittag hast, kannst du in der Natur eine Katze zum Leben erwecken oder sie für ein schönes Sonnenuntergang fotografieren. Du kannst z. 
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **[Nacht, in Chemnitz]**  

Oder:  
**[Nacht, Chemnitz]**  

**[Eingestellt, bei Bedarf]**  

**[Nacht, Chemnitz]**  

**[Nacht, Chemnitz]**  

**[Eingestellt, 
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich schicke gern einen kurzen Gruß, der die gewohnte Ruhe des Tages widerspiegelt und Ihre Anliegen mit Anerkennung erfül
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hallo, ich würde gerne eine schöne Sache machen – ein Fest mit einem Kaffee und einem Lächeln!  

**Schlag mir:**  
1. **Zauberkiste:**  
   Du könntest etwas w
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Wenn du einen freien Nachmittag hast, kannst du **Stoffnudeln** machen. Einfach die Nudel in der Mitte des Kettels (und einen kleinen Gegenstand darauf) rollen 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich könnte dir gerne eine Idee für heute Abend kochen – vielleicht etwas, das du besonders magst. Vielleicht ein Stück aus dem Alltag oder etwas, das deine Lieb

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Paula; wohnt in: Rosenheim; Hund: Jacko; Lieblingsessen: Hühnerfrikassee.
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

**Betreff:** Grußformel – Meine E-Mail vom 21. November  
**Sehr geehrte/r [Name],**  

Liebe/r [Name],  

vielen Dan
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache, die ich am Wochenende in meiner Stadt machen kann:  
**1. Leckere Eier**  
- **Warum?** Sie sind so lecker, weil sie mit Eiweiß (z. 
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Möglichkeiten, deinen Hund zu genießen:  

1. **Füttern** – **Essen**: Lege in der Küche ein leeres Stück Mehl und Essig in den Hund, kaufe ihn
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) - **Brot mit Obst, Gemüse und Kräutern**:  
  - 1 kg Bohnenkraut (2 cm)  
  - 2–3 Zwiebeln (z. B. Karotten, Knoblauch)  
  - 3–4 kleine Petersilieblätter  
  - 
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  

**E-Mail:**  
*Dear [Name des Nutzers],  
ich freue mich, dass du dich über mich unterhalten kannst!   
Ich bin [Name
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache, die du am Wochenende in deiner Stadt machen kannst:  

**Zutaten (je nach Bedarf):**  
- **Rosenheim-Hühnerfrikassee**: 500g.  
- **
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Du könntest einen Spaziergang machen, z. B. mit einem Hund oder eine Kamera. Hier sind ein paar Ideen:

1. **Hund-Spaziergang:**  
   - **Eine Karte mit den Ber
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Natürlich! Ich kann dir heute Abend eine Idee für einen typischen Rosenheim-Kuchen anbieten, falls du es gerne hast. Hier sind einige Vorschläge:

1. **Hühnerfr

### de05 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Luise; wohnt in: Ingolstadt; Katze: Fienchen; Lieblingsessen: Schupfnudeln.
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

Vielen Dank für Ihre Anfrage! Ich freue mich, Sie auf eine Antwort zu freuen. Sollten Fragen auftreten, stehe ich gern
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich könnte dir eine schöne Sache empfehlen:  
1. **Käse-Taste mit einer Bohnenkugel** – das schmeckt nach *Bohnen* und ist sehr langlebig.  
2. **Eier-Mischung*
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Falls es passt, könntest du:  

1. **Kuchen**: Stelle dir eine kleine Schüssel mit Backwaren oder Sandwich-Gerichten auf und klebe sie darauf. Du kannst auch ei
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Kaffee ist eine wunderbare Kombination aus Aroma und Wärme! Hier sind einige Tipps, die Sie heute Abend kochen können:

1. **Muffins** (eine knusprige Masse mit
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrte/r [Name des Nutzers],**  

Vielen Dank für Ihre Anfrage! Ich freue mich, Sie auf eine Antwort zu freuen. Lieblingsessen, Schupfnudeln und die ein
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Hier sind einige **exklusive** Tipps, die du am Wochenende in deiner Stadt machen kannst:  

1. **Küche**:  
   - **Die Hölle mit Schupfnudeln** ist 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Ja, es gibt viele Möglichkeiten mit Ihrer Katze. Hier sind einige Ideen:  

1. **Hitze machen:** Hänge sie vor dem Fenster oder waren Sie in einem warmen Zimmer
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind eine Idee, die ich heute Abend gerne koch habe:
- **Schnitzel mit Wurst und Käse** (z. B. Schinken, Rotkäse, Käse)  
- **Nudeln mit ersten Kräutern un

