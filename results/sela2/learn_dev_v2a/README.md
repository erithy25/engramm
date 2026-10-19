# Sela-2 lernt: Messung nach PREREG §7

40 synthetische Nutzer (data/sela2/learn_sessions.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 30.6 | 31.2 |
|   davon EN (%) | 0.0 | 41.2 | 37.5 |
|   davon DE (%) | 0.0 | 20.0 | 25.0 |
| Antworten mit übernommenem Fehler | 0 | 0 | 6 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 208 | 208 | 208 |
| Sela-2-Antworten | 272 | 272 | 272 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Token/s (Sela-2) | 31.08 | 30.48 | 28.1 |

Zurückgehaltene Hobby-Sätze (80): 1.5809 bpb ohne, 1.5723 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 37 von der Rechtschreibprüfung korrigiert, 0 nicht gelernt (Nachricht nicht lernbar), 60 vom Filter verworfen, 23 gespeichert.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 30.6 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 6 | <= 2 | nein |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 0.55 | >= 1.0 % | nein |
| L5_speed | 0.904 | >= 0.85 | ja |
| L4_app_F | 2 | <= 4 | ja |
| L4_app_FK | 3 | <= 4 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) aus.

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
Ich freue mich, gestern mit dir zu sprechen.  

**Grüße:** glaube ich, dass du garnicht sehr schnell schreiben kannst!    ging es um eine kurze
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Lea ist glaube ich heute der Durchreisende in Hannover. Behandlung durch eine Morgenichtessenzange (Nächtoker ständig auf Sommer- und Winterzeit sieht), aber au
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Ich kann dir helfen, glaube ich. letzten Freitag war der letzte freien Nachmittag in Hannover bei mir und die Hundearbeit hat heute eine sehr klare Glückwunsch-
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich bin glaube nicht auf deine Frage zu antworten, da ich Morgen keine Idee sollte. Ich hoffe aber gefallen zu haben und dir eine Ideen sieht, die sehr gut aus 

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
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) Ich und Laura,

Sollte ich dir einen Gruß schreiben, bitte die Stunden, die du uns beschäftigt hast, mit mir. Dann überrascht Hause mich gerne mit etwas anderes
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **essen** glaube ich bei dir!  Mainz ist eine Stadt mit sich selbst, und das Brot ist ein sich selbst schickendes Getränk.  

*(Nimm einen kalten Blick an die U
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Um einen freien Nachmittag mit deiner Katze zu machen, können Sie:
1. **Kaffee und Kuchen** kochen – oder glaube an ein Lieblingsessen! 
2. **Sollte du überrasc
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Eine Idee für heute Abend wäre ein **essen, glaube ich** aus Mainz. Es gibt eine Menge zu kochen, aber der Weg ist lang und die Wetterlage überrascht nicht imme

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
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußessen:**  
*Gasch, schön. Das ist die Lieblingsessen-Ich in Passau. Lassen Sie uns gemeinsam aufpassen!*   und  
*Gasch, schön. Wo liegt das Essen? glaube
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich bin auf der Suche nach einem schönen Wochenende für einen Spaziergang in Passau. Lieblingsessen: Gulasch, glaube ich. Das Biertrinken am See ist perfekt, ab
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Ich mache Gulasch mit Rocky.**  
„Mein Hund ist ein Lieblingsessen. Er liebt es, auf mich zuzalte. Wenn er mir garniert, habe ich ihn auch gern auf mich geste
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich habe keine Lieblingsessen, aber ich. Werden Sie heute Abend morgen etwas kochen?

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
*Ich freue mich, Ihnen gegangen zu sein. Möchtest du etwas tun oder fragen?* ist gut und einfach zu verwenden!
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Lena. Gibt es eine schöne Sache, die du am Wochenende in deiner Stadt machen kannst?
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Ich habe einen freien Nachmittag. Bitte teilen Sie mit, was Sie mit Ihrem Katze machen möchten! Zögern Sie nicht, voller enthusiasm zu sein – sie ist in diesem 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich freue mich, dir eine Idee zu geben! Du kannst heute Abend voller Kreativität kochen. Ich würde gerne gegangen sein:  
1. **Ochini-Riechen**: Boden-essen (z.

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
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir draußen:  
Ich bin [Name] bei dir, damit du glaube, dass du in deinem Raum bist.  

Welche Formate sind hier gebräuchlich?
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich freue mich darauf, bei dirichtigkeiten draußen zu helfen! Hier sind einige Tipps, die ich dir habe:  

Welche Brennnesseln möchtest du unbedingt haben?  
- 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hören Sie auf! Hannah ist ein guter Hund, der gerne mit? Porträts zeigt, Porträts der Kinder und Freunde. Das wenigste wäre ich, sie zu bitten, die Namen heißt 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hessen ist eineicht noch zu warm, aber du hast die Samstagabend-Kochsweite mit uns immer für glaube ich. Das ist es, was wir morgen Abend kochen wollen. Hund: B

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
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrte/r [Name des Nutzers], sieht bei Ihnen wie ich mich in dieser Nachricht ausdrücken könnte ist: meinem Namen, meinem Wohnort und meinem Lieblingses
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Letzte Anfrage:**  

Sehr gerne! Ich bin heute in Augsburg, um eine besondere Veranstaltung zu planen. Die Veranstaltung ist ein Glückwunsch für die Stadt und
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) **Antwort:**  
Sophie ist die Katze, die dir über dich erzählt hat. Ich bin Morgen. Vielleicht eine Tasse Risotto oder ein Buch sieht aus. Volksweisheiten sind 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde gern heute Abend eine Behandlung der Katze mit **Hähnchenfleisch** ist. Ich sollte aber auch heute Abend überrascht sein, dass ich nicht einen Brutkes

