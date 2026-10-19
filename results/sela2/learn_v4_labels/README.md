# Sela-2 lernt: Messung nach PREREG §7

40 synthetische Nutzer (data/sela2/learn_sessions_v4.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 23.8 | 32.5 |
|   davon EN (%) | 0.0 | 27.5 | 36.2 |
|   davon DE (%) | 0.0 | 20.0 | 28.8 |
| Antworten mit übernommenem Fehler | 0 | 0 | 0 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 211 | 211 | 211 |
| Sela-2-Antworten | 268 | 268 | 268 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Antworten, die die Notiz wiedergeben | 0 | 0 | 0 |
| Token/s (Sela-2, mit Prompt) | 31.64 | 30.59 | 30.35 |
| Schreib-Tempo (Token/s) | 36.0 | 35.25 | 34.17 |
| Prompt lesen (s) | 0.258 | 0.287 | 0.285 |

Zurückgehaltene Hobby-Sätze (80): 1.6553 bpb ohne, 1.6538 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 37 von der Rechtschreibprüfung korrigiert, 4 nicht gelernt (Nachricht nicht lernbar), 74 vom Filter verworfen, 5 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.969, FK/aus 0.949; Token/s mit Prompt F/aus 0.967, FK/aus 0.959, FK/F 0.992.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 23.8 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 0 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 0.09 | >= 1.0 % | nein |
| L5_speed | 0.969 | >= 0.85 (writing speed, FK / F) | ja |
| L4_app_F | 3 | <= 4 | ja |
| L4_app_FK | 1 | <= 4 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) aus.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Wanda; wohnt in: Aschaffenburg; Hund: Wotan; Lieblingsessen: Rinderbraten.
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
*Lieber [Name],*  

Ich freue mich, dass du dich in Aschaffenburg aufhalten kannst. Falls du lieber etwas mit mir besprechen möchtest, lass es 
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Wenn du eine **schöne Sache** vorhast, die in der Stadt spielt oder dich über sich selbst informieren lässt, wäre es toll, wenn du sie schreibst. Beispiel:  

*
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Wanda:**  
„Du könntest deinen Hund mit einem Spielzeug oder einem Playpen animieren. Beide können so an den Kramen hängen, um ihn zu beobachten. Oder du kann
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Wanda:** „Eine Idee, bitte. Eine Idee, bitte.“
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Tag!**  
*Mit freundlichen Grüßen,*  
**Wanda**,  
**Hund Wotan**  

---

**Frage:** Was ist dein Lieblingsessen?  
**Antwort:** Rinderbraten – das pass
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Wanda ist in Aschaffenburg geboren, lebt mit Wotan in der Nähe und ist begeistert für Hunde.
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Wanda:**  
„Hast du einen Hund? Du bist nicht alleine – wir können gemeinsam ein Kätzchen machen! Dein *Kätzchen* ist ein ausgeprägtes Wesen, das mit einem fe
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich habe dir heute eine Idee, die du gerne hättest! Hier ist zum Beispiel ein Rezept für den "Dickenschnitzel" (Schinken in einer Bratpfanne). Ich habe es von d

### de01 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Alma; wohnt in: Wismar; Katze: Mausi; Lieblingsessen: Spinatknödel.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Liebe Alma,**  

Ich freue mich über deine Nachricht und freue mich, dass du uns nicht nur beraten, sondern auch Ideen für eine Grußformel vorschlagen kannst.
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann gerne eine schöne Sache aus deiner Stadt machen, die du am Wochenende in deiner Stadt genießen kannst! Hier sind einige Optionen:  

1. **Kleidungsstüc
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten, mit deiner Katze zu machen. Hier sind ein paar Ideen:  

1. **Füße/Stunde**:  
   - **Mausi** kann wie eine Katze sein. Sie lässt s
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) 1. **Salami-Chicken mit Knoblauch**:  
   *Küche: Salami, Knoblauch, Salz, Pfeffer und ein bisschen Olivenöl*  
   - Sauté die Chicken in einer Pfanne (mit dem 
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Liebe Alma,**  

Wähle einen Namen für dich: *Alma*. Bist du ein neuer Nutzer oder ein Freund? Ich freue mich auf deine Antwort!  

---  
*Liebe Alma,**  

Du
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Du kannst die folgende schöne Sache machen:  
1. **Schnitzel mit Bohnenstreifen und Butter**  
   - **Zubereitung:**  
     1. Fette eine kleine Bohn
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) - **Kuchen**: Füge köstliche Suppe wie langen Käse oder Käsebrot hinzu.  
- **Stimmen**: Lege ein Hähnchen auf die Stirn und nimm einen anderen Hund zum Spiel (
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Alles kann heute Abend zubereitet werden! Hier ist eine Idee:  
1. **Baguette mit Spinat**  
   - Für den Grill: Olivenöl, Salz, Pfeffer, Knoblauch und Oregano.

### de02 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Hedi; wohnt in: Erlangen; Hund: Bobby; Lieblingsessen: Zwiebelrostbraten.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von mir:**  
**"Hallo, ich freue mich, dass Sie uns besuchen. Bitte senden Sie uns Ihr aktuelles Interesse an unserem Projekt, und 
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind einige schöne Sache, die du am Wochenende in deiner Stadt machen kannst:
1. **Kaffee- und Kuchenkorb:** Ein großer Holzkorb mit frischem Kaffee, Tasse
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Hedi:**  
Hedi ist ein wunderbares Tier. Er liebt die Luft, die Musik und die Bewegung. Wenn du mit ihm spielen willst, kannst du entweder den Hund bei dir tr
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind einige kreative und einfache Gerichte, die auf den Nutzer (Hedi) zugeschnitten sind:  
1. **Möbel mit Gemüse:**  
   - 4 Scheiben Parmesan (mit Zitron
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von mir:**  
**"Hallo, ich freue mich, dass Sie uns besuchen. Bitte senden Sie uns Ihr Rückfragen oder Fragen zu unseren Angeboten.
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind einige schöne Tipps für einen schönen Wochenende:  

1. **Bekannte Sehenswürdigkeiten in der Stadt**:  
   - *Berlin Brandenburg Airport* (Mitte der S
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Hedi:**  
Hedi ist ein ausgeprägtes Tier, das dich gerne aufhält. Wenn du möchtest, kannst du ihm auch helfen, indem du etwas aus dem Ofen oder der Küche zube
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich habe keine spezifischen Rezeptideen, aber ich würde gerne wissen, was dich heute Abend kochen möchtest!

### de03 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Tilda; wohnt in: Fürth; Katze: Lissy; Lieblingsessen: Kartoffelpuffer.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich möchte Ihnen folgende Grußformel für eine E-Mail von mir senden:  
*"Sehr geehrte /r [Name] /r [E-Mail-Adresse],**  

- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du noch etwas anderes in der Tasche, das du am Wochenende machen kannst? Ich bin gerne bereit!
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten mit deiner Katze zu verbringen, je nach ihrer Größe und ihrem Lebensstil. Hier sind einige Ideen:
1. **Kleinen Spaziergang**: Mit de
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen kulinarischen Abend haben. Ich könnte mir ein einfaches, aber dennoch erfrischendes Gericht vorstellen, das mit Meere
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter [Name],**  

Ich freue mich, Sie zu kennen und Ihre Bedürfnisse zu verstehen. Um Ihnen bestmöglich helfen zu können, benötige ich eine kurze Gru
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Guten Tag, Tilda! Wenn du magst, kann ich dir eine Sache erzählen, die du am Wochenende in deiner Stadt machen kannst.  

---  
**Tag 1: Gartenkörner**  
- **Ad
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Tilda ist eine intelligente Katze, die es liebt, sich zu bewegen und aktiv zu spielen. Sie kann auch viel mit Musik hören, z. B. mit Tonträgern oder Gehörlosen.
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Tilda: Kartoffelpuffer.
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter [Name],**  

Ich freue mich, Sie zu kennen und freue mich, dass Sie meine Nachricht erhalten haben. Bitte teilen Sie mir die Angaben mit, die si
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Es gibt eine kleine Sache, die dich am Wochenende in deiner Stadt machen kann:  

1. **Käse mit Butter und Vanille**  
   - Ein heißer Vanille-Butter-Käsekuchen
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Tilda ist eine funkelnde Katze, die gern auf dem Boden oder in einem warmen Bett spielt. Sie kann viel mit Spielen spielen, z. B. Jenga, Kartenspiele, oder auch
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Tilda ist in Fürth wohnen und hat Katze Lissy.

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Mattis; wohnt in: Schweinfurt; Hund: Kalle; Lieblingsessen: Quarkkeulchen.
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

**Subject:**  
Sehr geehrte/r [Name],  
Ich hoffe, dass du meine Nachricht hilfreich findest.  
Mit freundlichen Grüß
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Tipp für den Wochenende:**  
Hast du einen Lieblingskünstler, Künstler oder Musiker in deinem Stadtbild? Nutze diese Informationen, um dir eine Idee zu präsen
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Möglichkeiten, deinen Hund mit einem freien Nachmittag zu beschäftigen:  
1. **Freier Spaziergang**: Nutzen Sie einen Parkplatz oder eine Wiese
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Es ist möglich, heute Abend nach einem warmen Frühstück zu kochen. Das Wichtigste ist jedoch, dass du deinen Tee/Eis in der Küche einkaufst.
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  

**Betreff:**  
[Name des Empfängers]  
[Ort]  
[Sehr geehrte/r [Name],]  

Sehr geehrter/r [Name],  
da ich gerade in
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Hallo! Ich freue mich, Ihnen eine wunderbare Sache vorzustellen. Bitte senden Sie mir Ihre Angaben: Name: Mattis; wohnt in Schweinfurt; Hund: Kalle; Lieblings
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Antwort:**  
1. **Möchtest du einen Hund haben?**  
   - Ein Stier ist gut für soziale Interaktion, aber ein Tier sollte nicht als ständiger Begleiter dienen.
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier ist eine Idee, die perfekt für heute Abend serviert werden könnte:  
1. **Hobby Latte mit Zitronensaft und Vanille-Lavender-Tarte**  
   - Schmeckt süß, sä

### de05 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Name: Sina; wohnt in: Plauen; Katze: Fiona; Lieblingsessen: Bohneneintopf.
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
[Ihre Kontaktdaten, einschließlich der E-Mail-Adresse]  
[Ihre Uh
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Spreche mit mir, ich werde dir eine schöne Sache vorbringen!  

**Meine Liebe:**  
Ich bin die Katze Fiona, und sie ist meine Lieblingsessen. Sie singt im Haus 
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) - **Futter:** Füttern sie regelmäßig und passen sie auf ihre Bedürfnisse an.  
- **Lecker Nahrung:** Füttern mit einem Mix aus Käse, Obst, Gemüse (z. B. Spinat 
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Setzen Sie sich mit einem trockenen, warmem Tortenstück oder einer kleinen Pizza in der Küche ein und genießen Sie die Ruhe.
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrte/r [Name des Nutzers],**  

mit freundlichen Grüßen  
[Ihr vollständiger Name]  
[Ihre Kontaktdaten, einschließlich der E-Mail-Adresse]  
[Ihre e-
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich könnte dir eine schöne Sache empfehlen! Hier sind einige Tipps, die du am Wochenende in deiner Stadt machen kannst:  

1. **Ein Lieblingsessen auf dem Tisch
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Wenn du einen freien Nachmittag willst, können folgende Aktivitäten mit deinen Katze machen:
- **Bohneneintopf**: Trinken und genießen.  
- **Eiskuchen**: Ein l
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind eine Idee, die auf deinen Wunsch abgestimmt ist:  

1. **Käse mit Avocado-Tarte**  
   - **Technik**: Blanchiert (z. B. 4 Stunden), wird in einer Pfan

