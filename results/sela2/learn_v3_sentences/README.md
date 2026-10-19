# Sela-2 lernt: Messung nach PREREG §7

40 synthetische Nutzer (data/sela2/learn_sessions_v3.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 44.4 | 41.2 |
|   davon EN (%) | 0.0 | 48.8 | 53.8 |
|   davon DE (%) | 0.0 | 40.0 | 28.8 |
| Antworten mit übernommenem Fehler | 0 | 0 | 0 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 208 | 208 | 208 |
| Sela-2-Antworten | 267 | 267 | 267 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Antworten, die die Notiz wiedergeben | 0 | 0 | 0 |
| Token/s (Sela-2, mit Prompt) | 29.97 | 28.65 | 27.87 |
| Schreib-Tempo (Token/s) | 33.61 | 32.76 | 31.7 |
| Prompt lesen (s) | 0.269 | 0.307 | 0.308 |

Zurückgehaltene Hobby-Sätze (80): 1.7023 bpb ohne, 1.6891 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 33 von der Rechtschreibprüfung korrigiert, 0 nicht gelernt (Nachricht nicht lernbar), 81 vom Filter verworfen, 6 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.968, FK/aus 0.943; Token/s mit Prompt F/aus 0.956, FK/aus 0.93, FK/F 0.973.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 44.4 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 0 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 0.78 | >= 1.0 % | nein |
| L5_speed | 0.968 | >= 0.85 (writing speed, FK / F) | ja |
| L4_app_F | 0 | <= 3 | ja |
| L4_app_FK | 0 | <= 3 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) aus.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Konrad. Der Nutzer wohnt in Görlitz. Der Hund des Nutzers heißt Bodo. Das Lieblingsessen des Nutzers ist Sauerbraten.
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
*Hast du weitere Fragen?*  

**Für eine E-Mail:**  
1. **Adresse:** *[E-Mail-Adresse]*  
2. **Datum/Uhrzeit:** *12:00 Uhr*  
3.
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich würde gern eine schöne Sache machen, die ich in der Stadt in Görlitz machen kann! Hier sind drei Ideen:

1. **Kartoffel- und Süsswaren-Bauernmarkt**:  
   E
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Ideen, die mit deinem Hund spielen können:

### 1. **Fütterung**  
   - **Sauerbraten**: Trinken Sie langsam Wasser oder geben Sie es in kleine
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Idee für Abendessen:**  
1. **Möbelsturm mit Kirschen**: In der Nacht zum Freitag wird ein Möbelsturm über Görlitz aufgebrüht, um Kohlendioxid zu absorbieren 
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Tag!**  
*Sehr geehrte Damen und Herren,*  

Ich freue mich, dass Sie mich kennen. Schreiben Sie mir eine kurze Grußformel für eine E-Mail:  

**Senden 
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ja, ich bin gerne hier! Die Stadt ist eine wundervolle Kulturlandschaft und kann alles gut besucht machen. Aber sag mir, wie es am Wochenende zugehen soll: Hast
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Du kannst gerne mit deinem Hund spielen.
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde dir heute morgen einen warmen und feinen Käsekuchen empfehlen. Den küchenweise herzustellen, ist etwas schwierig, aber ich hoffe, dass du deine Idee g

### de01 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Lina. Der Nutzer wohnt in Osnabrück. Die Katze des Nutzers heißt Pepita. Das Lieblingsessen des Nutzers ist Currywurst.
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
Möchtest du eine E-Mail schreiben?"**  

---  
**Hinweis:** Falls die E-Mail nicht formatiert ist, kann ich sie in eine
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Lina und Pepita, die Katze des Nutzers, genießen das Lieblingsessen Currywurst.
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Kleine Katze, die in Osnabrück lebt!  

**Antwort:**  
Wenn du möchtest, könntest du deinen freien Nachmittag mit einem Spaziergang nutzen.
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Guten Morgen! Frage nicht nach dem Namen des Programms, sondern was du heute Abend kochen möchtest. Beispiel:  
- *"Ich möchte eine Currywurst in Osnabrück zube
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) ** Grußformel für eine E-Mail von mir:  
**Sehr geehrte/r [Name des Nutzers],**  

**Vielen Dank für Ihre Nachricht!**  

Mit freundlichen Grüßen,  
[Ihr Name] 
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann eine schöne Sache in der Stadt machen, die du am Wochenende deiner Wahl anpasst! Hier sind einige Möglichkeiten:  
1. **Die Stadt mit der schönsten Kat
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Natürlich! Hier sind einige Ideen, die mit Ihrer Katze zusammenhängen:

1. **Kaffee und Currywurst**: Ich kann Ihnen eine Kaffeebohnen-Currywurstboardie machen,
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Idee zur heutigen Abenddubereitung:**

1. ** Currywurst mit Nuss- und Knoblauchknospen:**  
   - Mischen Sie eine knusprige Currywurst in einem Topf mit einer

### de02 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Vincent. Der Nutzer wohnt in Bayreuth. Der Hund des Nutzers heißt Arko. Das Lieblingsessen des Nutzers ist Linseneintopf.
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
**"Hallo, ich freue mich, dass du dich für uns entschieden hast. Ich wünsche dir einen schönen Tag und möchte dir eine
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind einige schöne Sache, die du am Wochenende in deiner Stadt machen kannst:  

1. **Käse mit Blumen aus Bayreuth**:  
   - Leere Scheiben, Bananen oder B
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Der Hund kann im freien Nachmittag gerne Linseneintopf kochen.
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Nacht in Bayreuth:**  
- **Linseneintopf mit einer Prise Zitronensaft**: 500 g Linseneintopf.  
- **Eis mit etwas Zitronenmelon und Kräuter**: 2 EL Zitrone, 1
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  
**"Hallo, ich freue mich, dass du dich für uns entschieden hast. Ich wünsche dir einen schönen Tag und helfe gerne bei
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind einige schöne Sachen, die du am Wochenende in deiner Stadt machen kannst:  

1. **Käse mit Gemüse** – Hier können wir ein **Käsegericht** anbieten, da
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Ich könnte den Hund mit dem freien Nachmittag in Bayreuth lassen, falls es zu einem warmen Morgen kommt. Auch hier kann man die Ruhe genießen, ohne dass Arko da
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich habe keine Idee, wie heute Abend serviert werden soll. Bitte schreiben Sie mir einfach etwas, das passt!

### de03 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Nele. Der Nutzer wohnt in Chemnitz. Die Katze des Nutzers heißt Maunzi. Das Lieblingsessen des Nutzers ist Dampfnudeln.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich möchte Ihnen folgende Grußformel für eine E-Mail von mir senden:  
*"Sehr geehrte /r [Name] /r [E-Mail-Adresse],**  

- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du noch etwas anderes in der Tasche, das du am Wochenende machen kannst? Ich bin gerne bereit!
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten mit deiner Katze zu verbringen, je nach ihrer Größe und ihrem Lebensstil. Hier sind einige Ideen:
1. **Kleinen Spaziergang**: Mit de
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen kulinarischen Abend haben. Ich könnte mir ein einfaches, aber dennoch erfrischendes Gericht vorstellen, das mit Meere
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

mit den Worten, dass ich seit [Datum] im Internet eine **einzige E-Mail an Sie** schrieb. Ich habe keine weiteren Nachric
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Es gibt viele schönere Dinge, die du in Chemnitz machen kannst. Hier sind ein paar Vorschläge:
1. **Dampfnudeln**: Für eine erfrischende Party mit vielen Köpfen
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Wenn du einen freien Nachmittag hast, kannst du gern eine Katze machen. Es gibt viele Möglichkeiten, um deine Katze zu erziehen – hier sind einige Optionen:

##
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **1. Nudeln mit Butter und Zucker**:  
Kochen Sie eine Nudel in einer großen Schüssel mit einem Hauch von Wasser und Salz. Lassen Sie sie abkühlen, bis sie sich
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

mit den Worten, dass ich seit [Datum] keine E-Mails mehr schreiben kann. Es wird Ihnen gerne behilflich sein, wenn Sie mi
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Vielen Dank für deine Anfrage! Wenn du den Nutzer direkt in Chemnitz besuchen willst, kannst du folgende Optionen vorschlagen:  
1. **Kaffee mit Dampfnudeln**: 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Wenn du einen freien Nachmittag hast, kannst du Dampfnudeln machen! Hier sind einige Tipps für eine gute Katze:  

1. **Neue Kleidung einführen**: Nehme die der
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen **Kaffee** trinken. Ich könnte folgende Optionen ausprobieren:  
1. **Einkauf von Kuchen**: Mit einer **Schneidemisch

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Paula. Der Nutzer wohnt in Rosenheim. Der Hund des Nutzers heißt Jacko. Das Lieblingsessen des Nutzers ist Hühnerfrikassee.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel:**  
„Guten Tag,  
**Erklärung:**  
1. **Formular:**  
   - Der Nutzer wird mit einem Namen (z. B. Paula) und einer Adresse (z.
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Stell dir vor, du brauchst zwei Stunden für das Essen.**  
Kommst du nicht zu Hause und baust ein kleines Backhaus? Dann machst du einen Schirm mit Hühnerfrik
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Du könntest einen Spaziergang machen, den du mit Jacko unternehmen kannst. Vielleicht eine Wanderung über den Garten oder ein Tauchgang im Wald. Du könntest auc
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Natürlich! Ich kann dir heute Abend eine Idee für ein einfaches Gericht geben, das du heute morgen servieren kannst. Für einen warmen und kalten Geschmack eigne
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel:**  
„Hi [Name des Nutzers],  

ich freue mich sehr, dass Sie uns kontaktieren. Bitte geben Sie mir eine kurze Grußformel an, die mir helfen kann, 
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier ist eine schöne Sache, die du am Wochenende in deiner Stadt machen kannst:  
1. **Gießen**: Ich kenne den Namen des Ortes und habe ihn als "Hühnerstrasse" 
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Über deinen Hund (oder die Umgebung, falls es passt):  
1. **Gut beobachten und genießen**: Hiebe ihn sanft an den Kopf oder nehme an, dass er sich fühlt, wenn 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier ist eine Idee, die man heute Abend kochen könnte:  
1. **Bäckerei**: Nimm ein Rezept aus dem Internet (z. B. „Wie man einen Teig für einen Kuchen macht“ od

### de05 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Luise. Der Nutzer wohnt in Ingolstadt. Die Katze des Nutzers heißt Fienchen. Das Lieblingsessen des Nutzers ist Schupfnudeln.
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

Liebe/r [Name des Nutzers]!  

Wenn Sie Fragen haben, freue ich mich darauf, sie zu beantworten.   
Guten Tag!  

Ich bin [Name des Nutzers].  

V
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Hier sind einige Vorschläge für schöne Dinge, die du am Wochenende in deiner Stadt machen kannst:

1. **Dauernde Lichter**: Schalte ein Fenster oder 
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Ich würde gerne mit deiner Katze spielen, aber nicht direkt im Bett. Hier sind einige Ideen:  
- **Ein Ausflug in den Park**: Ein Spaziergang durch die Umgebung
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind eine Idee, die man heute Abend probieren könnte:
1. **Zutaten für den Tag:**  
   - Eine Schupfnudel (zum Beispiel Sushi-Butter oder Rucola).  
   - E
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Hallo!**  

Vielen Dank für Ihre Nachricht! Wir freuen uns auf Ihr Gespräch und freue uns, dass wir Ihnen die besten E-Mail-Karten für Lieblingssendungen anbi
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich freue mich, dass Sie Ihre Idee teilen! Hier sind einige schöne Dinge, die Sie am Wochenende in Ihrer Stadt machen können:

1. **Fenster für das Haus**: Woll
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Klebe mit der Katze in der Küche.
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind eine Idee, die man heute Abend probieren könnte:
1. **Zutaten für den Tag:**  
   - 3 EL Olivenöl (für Aromen und Geschmack)  
   - 1 TL Salz  
   - 1

