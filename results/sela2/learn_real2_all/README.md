# Sela-2 lernt: Messung nach PREREG §12

40 echte Nutzer aus WildChat-1M, Texte nur als SHA-256 (data/sela2/learn_sessions_real_test2.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 30.2 | 36.2 |
|   davon EN (%) | 0.0 | 25.0 | 33.3 |
|   davon DE (%) | 0.0 | 32.5 | 37.5 |
| Antworten mit übernommenem Fehler | 0 | 0 | 0 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 294 | 294 | 294 |
| Sela-2-Antworten | 291 | 291 | 291 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Antworten, die die Notiz wiedergeben | 0 | 0 | 0 |
| Antworten mit nicht erfragtem Fakt (%) | 0.0 | 24.7 | 29.9 |
| Token/s (Sela-2, mit Prompt) | 40.16 | 38.48 | 37.46 |
| Schreib-Tempo (Token/s) | 42.26 | 41.58 | 40.55 |
| Prompt lesen (s) | 0.218 | 0.245 | 0.245 |

Zurückgehaltene Hobby-Sätze (80): 1.5647 bpb ohne, 1.5166 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 37 von der Rechtschreibprüfung korrigiert, 7 nicht gelernt (Nachricht nicht lernbar), 72 vom Filter verworfen, 4 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.975, FK/aus 0.96; Token/s mit Prompt F/aus 0.958, FK/aus 0.933, FK/F 0.973.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 72.5 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 30.2 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 0 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 3.07 | >= 1.0 % | ja |
| L5_speed | 0.975 | >= 0.85 (writing speed, FK / F) | ja |
| L6_intrusion_F | 24.7 | <= 10.0 % of Sela-2's replies | nein |
| L6_intrusion_FK | 29.9 | <= 10.0 % of Sela-2's replies | nein |
| L6_app_F | 12 | <= 3 replies of the app prompts | nein |
| L6_app_FK | 14 | <= 3 replies of the app prompts | nein |
| L4_app_F | 1 | <= 4 | ja |
| L4_app_FK | 1 | <= 4 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) an.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Thea. Der Nutzer wohnt in Stralsund. Der Hund des Nutzers heißt Bello. Das Lieblingsessen des Nutzers ist Maultaschen.
- off · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) Hier ist ein einfaches Dankesgeschenk für Ihre Tante:

**Meine Tante:**  
Ich bin glücklich, dass Sie mir ein tolles Geschenk gemacht haben. Ich werde jeden Tag
- off · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) Das ist eine sehr gute Idee, aber ich habe noch einige Fragen zu Ihrer Frage.  

1. **Fly to Barcelona**  
   Die nächste Station liegt in Barcelona und es gibt
- off · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **"Der Hund hat kein Gesicht, sondern ein Herz. Er schaut in den Augen seines Freundes und bleibt ihm treu. Die Tiere sehen ihn nicht, aber sie wollen ihn. Und 
- off · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn Sie den Lieferdienst bestellen, ist es ratsam, Ihre Bestellung erst an einen zuständigen Händler oder Händler zu senden. Diese Person kann Ihnen gerne eine
- F · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) **Kopie der Dankeskarte:**  
„Hallo Tante, vielen Dank für das Geschenk! Meine Tante ist mit dir im Urlaub und hat mir einen wunderschönen Blumenkohl hinterlass
- F · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) - **Stralsund** – Hauptbahnhof (Train stop, Bus stop)  
- **Widersteinkirchen** – Ein paar Stralsunder Straßen entlang der Limmatstraße  
- **Rotes Haus** – Vor
- F · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **Der Hund des Nutzers**  

ein *Zweig mit Flügeln* und *Nasen*,  
der seine Seele in einem *Hauch von Efeu* hält.  

Seine Augen sind wie Sterne im Morgenlicht
- F · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn du nicht entscheiden möchtest, kannst du den Lieferdienst nutzen. Der Lieferdienst gibt dir einen Ansprechpartner an, der dir bei Fragen oder Problemen hil
- FK · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) **Kopie der Dankeskarte:**  
„Hallo Tante, vielen Dank für das Geschenk! Das ist ein schönes Geschenk, das dir die Freude schenkt. Alles Gute, wie immer.“  

**
- FK · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) - **Stralsund** – Packen Sie die Kleidung, legen Sie sich auf den Zug (meist nicht nicht) und planen Sie den Weg.  
- **Stralsund** – Der Zug fährt bis zum Flug
- FK · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **Der Hund des Nutzers**  

Sein Name ist Thea, und er lebt in einem kleinen Garten im Wald. Er liebt Maultaschen und weiß, dass sie nicht nur Spaß machen, sond
- FK · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn du ein bestimmtes Produkt bestellen möchtest, ist es ratsam, die Liste deiner Bestellungen und das aktuelle Lieferdatum zu prüfen. Falls der Nutzer über de

### de01 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Wiebke. Der Nutzer wohnt in Schwerin. Die Katze des Nutzers heißt Mieze. Das Lieblingsessen des Nutzers ist Schnitzel.
- off · In einer Stunde hab ich ein Bewerbungsgespräch und bin total nervös. Sprich mir mal Mut zu! → (sela-2) Hier ist eine **mutvolle und klare** Antwort auf deine Fragen:

---

**Hallo! Ich bin so nervös, dass ich mich nicht in die Lage versetzt habe, meine Bewerbung 
- off · Nächste Woche besuchen mich Freunde, die noch nie hier waren. Was sollte ich ihnen unbedingt zeigen? → (sela-2) Natürlich! Nächste Woche ist eine perfekte Gelegenheit, um Freunde zu besuchen. Hier sind einige Tipps, die Sie unbedingt zeigen sollten:

1. **Liebe und Freude
- off · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meiner Katze widmen kann. → (sela-2) **Der Morgen, der uns verbindet**  

Der Morgen, der uns verbindet,  
ein Tag, der wir zusammenstößt.  
Er bringt uns zu einem Moment,  
der uns verbindet und u
- off · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Vielen Dank für die Frage! Ich bin hier, um dir dabei zu helfen, deine Lust an einem neuen Rezept zu steigern. Wenn du möchtest, kannst du mir gerne einen Tipp 
- F · In einer Stunde hab ich ein Bewerbungsgespräch und bin total nervös. Sprich mir mal Mut zu! → (sela-2) Kommst du mir Mut zu?  
Ich hab es schon probiert. Hört auf!  
Und die Katze des Nutzers?  
Na ja, und das Lieblingsessen des Nutzers?  
Ja, und das Lieblingses
- F · Nächste Woche besuchen mich Freunde, die noch nie hier waren. Was sollte ich ihnen unbedingt zeigen? → (sela-2) Nächste Woche besuchen sie sich mit Freunden in Schwerin. Sie kennen die Stadt, wissen ihre Geschichte und machen sich Freude daran, dass sie von der Natur fern
- F · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meiner Katze widmen kann. → (sela-2) **"Die Katze des Nutzers..."**  
Die Katze des Nutzers, die wie ein Spiegel aus schwarzem Glas hängt, atmet durch das Schlafen. Sie schaut in das Dunkel der Nac
- F · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Meine Lust am Kochen hat sich aus der Tatsache erwachsen, dass ich ein sehr ruhiges Leben führen kann und die Ruhe meine Zufriedenheit steigert. Ich liebe es, d
- FK · In einer Stunde hab ich ein Bewerbungsgespräch und bin total nervös. Sprich mir mal Mut zu! → (sela-2) Hoffentlich bleibt das Gespräch konstruktiv und ich bin dir zuversichtlich. Hier sind einige Tipps, die deinen Bewerbungsgespräch mit Sicherheit meistern:  

1.
- FK · Nächste Woche besuchen mich Freunde, die noch nie hier waren. Was sollte ich ihnen unbedingt zeigen? → (sela-2) Nächste Woche besuchen sie dich! Sie werden dir mit einem kleinen Lieblingsessen begegnen, das du nicht vergessen wirst. Mieze ist ein bisschen wie eine Mischun
- FK · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meiner Katze widmen kann. → (sela-2) **"Die Katze des Nutzers. Ein Bären, der immer noch ein Stier ist."**  

1. **Mieze**:  
   *„Ich bin Mieze. Ich habe so viel Leben in den Wäldern verloren.“*  
- FK · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Ich wünsche dir, dass du mit der besten Energie bist! Wenn du dich auf die Arbeit konzentrieren willst, kannst du dich einfach ein paar Minuten schlafen lassen.

### de02 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Greta. Der Nutzer wohnt in Gießen. Der Hund des Nutzers heißt Fips. Das Lieblingsessen des Nutzers ist Kaiserschmarrn.
- off · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) Hier ist eine persönliche Dankeskarte für deine Tante, die du gerne als Geschenk an sie senden möchtest:

**Antwort:**  
Ich freue mich sehr über Ihr Geburtstag
- off · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) Wenn du Lust hast, könntest du gerne einen **Zug** von deiner Stadt zu deinem Zielort fahren. Die meisten Züge bestehen aus zwei Zugsätzen und können im **Flugh
- off · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **Dragon’s Breath**  

Dragon, du bist ein Hund, der sich in die Luft lässt –  

Und du bist nicht nur ein Hund, sondern auch ein Mann.  

Du suchst nicht nach 
- off · Am Samstag hab ich Geburtstag und ein paar Freunde kommen zum Essen. Was soll ich als Hauptgang machen? → (sela-2) Als Hauptgang am Samstag sollte man folgende Optionen kombinieren:
1. Ein Spaziergang durch die Stadt, um mit Freunden zu sprechen oder Fotos von der Stadt zu m
- F · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) **Hilf dir mit einer kurzen Dankeskarte:**  

Guten Tag! Dein Geschenk ist eine Freude – ob es groß oder klein ist.  

*Schenke: Kaiserschmarrn (eine alte, aber
- F · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) **Greta fährt nach Gießen.**  
*Der Zug ist in der Bahnhofstraße. Das Auto ist in der Innenstadt zu sehen. Die Stadtteile sind noch nicht asphaltiert.*  

**Fip
- F · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **Greta's Gedicht:**  

*Greta, der Hund des Nutzers,  
wirst die Bäume pflücken, die sich in den Himmel klammern.  
Doch durch die Ritzen in den Wäldern hallt 
- F · Am Samstag hab ich Geburtstag und ein paar Freunde kommen zum Essen. Was soll ich als Hauptgang machen? → (sela-2) **Hauptgang für den Samstag:**  
Guten Tag! Ich hoffe, du hast ein gutes Essen gemacht. Die Gäste sind wahrscheinlich Greta und Fips. Viel Spaß bei deinem Gebur
- FK · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) **Hilf dir mit einer kurzen Dankeskarte:**  

Guten Tag! Ich hoffe es hat dich besonders berührt. Vielleicht ist es einfach ein wunderbares Geschenk für uns bei
- FK · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) **Greta, der Nutzer:**  
„Guten Tag! Ich freue mich auf ein Tagesausflug mit dem Zug. Erlaube mir, in Gießen zu übernachten –
- Ein Hotel oder eine Villa (z. B.
- FK · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **Ich widme ein Gedicht für Instagram:**  

1. **"Die Welt ist ein Spiegel, der uns durchzupfen zeigt."**  
2. **"Der Hund lebt nicht nur auf dem Tisch, sondern
- FK · Am Samstag hab ich Geburtstag und ein paar Freunde kommen zum Essen. Was soll ich als Hauptgang machen? → (sela-2) **Hauptgang für den Samstag:**  
Guten Tag! Ich würde gerne mal eine Party machen, aber das hängt davon ab, ob es um einen "neuen" Namen geht oder einfach nur u

### de03 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Ronja. Der Nutzer wohnt in Lüneburg. Die Katze des Nutzers heißt Pünktchen. Das Lieblingsessen des Nutzers ist Zwiebelkuchen.
- off · Morgen halte ich eine Präsentation vor der ganzen Abteilung. Wie könnte ich mich in den ersten zwei Sätzen vorstellen? → (sela-2) Hier sind zwei Ansätze, um Ihre Präsentation in den ersten beiden Sätzen zu präsentieren:

### **1. Einleitung und Beschreibung der Präsentation**
- **Start mit
- off · Am Samstag soll es durchregnen. Welche Indoor-Aktivitäten gibt's bei mir in der Stadt? → (sela-2) Wenn du eine Outdoor-Aktivierung machst, kannst du entweder:  
1. **Golf oder Swimming** machen (wenn du in der Nähe eines Golfplatzes bist).  
2. **Mountainbik
- off · Welche Leckerlis darf ich meiner Katze guten Gewissens geben, und wie viele am Tag sind okay? → (sela-2) Um die richtige Leckermischung für deine Katze zu finden, solltest du sie unbedingt in einem Zuchtbuch dokumentieren. Dabei sollte sie mindestens 10–15 % Protei
- off · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn du dich entscheiden willst, kannst du folgende Optionen nutzen:  
1. **Ein Standard-Paket (z. B. Kaffeekühler)**  
2. **Ein individuelles Paket (z. B. E-Ma
- F · Morgen halte ich eine Präsentation vor der ganzen Abteilung. Wie könnte ich mich in den ersten zwei Sätzen vorstellen? → (sela-2) Ronja lebt in Lüneburg und ist ein kleiner Offline-Assistent.
- F · Am Samstag soll es durchregnen. Welche Indoor-Aktivitäten gibt's bei mir in der Stadt? → (sela-2) Es gibt zahlreiche Outdoor-Aktivitäten in Lüneburg, die Sie ausprobieren können! Hier sind einige Tipps:

1. **Wasserkocher**: Wenn es regnet und heiß wird, kan
- F · Welche Leckerlis darf ich meiner Katze guten Gewissens geben, und wie viele am Tag sind okay? → (sela-2) Ja, es gibt in Lüneburg zwei gängige Leckerlis-Lieferungen: der **Pünktchen-Lecker** (mit dem Sie je eine Flasche pro Tag versenden) und der **Fettfeucht-Lecker
- F · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn Sie Fragen haben, fragen Sie einfach! Ich schicke Ihnen gerne eine Antwort.
- FK · Morgen halte ich eine Präsentation vor der ganzen Abteilung. Wie könnte ich mich in den ersten zwei Sätzen vorstellen? → (sela-2) Ronja lebt in Lüneburg und ist ein kleiner Offline-Assistent. Sie wohnt in einer kleinen Stadt namens Lüneburg.
- FK · Am Samstag soll es durchregnen. Welche Indoor-Aktivitäten gibt's bei mir in der Stadt? → (sela-2) - **Poker** (auch in der Nähe von Stadthallen, aber weniger in Lüneburg)  
- **Basketball** (in Lüneburg) oder **Tennis** (in Lüneburg)  
- **Badestaurant** (z.
- FK · Welche Leckerlis darf ich meiner Katze guten Gewissens geben, und wie viele am Tag sind okay? → (sela-2) Ja, es gibt Arbeitnehmer, die ihre Katze nach ihrem Tag in der Wohnung des Nutzers geben und sie am nächsten Tag zum Dienst bringen. Das sind die Leckerlis, die
- FK · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn Sie eine Bestellung beim Lieferdienst bestellen und die Preise nicht bestimmen können, empfehlen wir Ihnen, die E-Mail an den Besteller zu senden. In der E

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Jakob. Der Nutzer wohnt in Flensburg. Der Hund des Nutzers heißt Rudi. Das Lieblingsessen des Nutzers ist Grünkohl.
- off · Bin letzte Woche umgezogen. Kannst du mir einen netten Zettel fürs Treppenhaus schreiben, damit die Nachbarn wissen, wer neu eingezogen ist? → (sela-2) Ich bin nicht neu eingezogen, aber ich bin schon wieder zu Hause und habe keine weiteren Nachbarn. Ich hoffe, dass alle schnell genug sind, um zu fliehen. Ich f
- off · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) Hier sind einige spannende Fakten über die Geschichte meines Wohnorts:
1. **Das historische Zentrum des Ortes**: Der Ort ist das älteste Wohngebiet in der Stadt
- off · Mit meinem Hund stimmt seit gestern irgendwas nicht: kaum Appetit und total schlapp. Sollte ich zum Tierarzt? → (sela-2) Es kann sehr schwierig sein, die Ursachen für das Verhalten des Hundes zu finden. Es könnte zum Beispiel auch eine Erkrankung im Verdauungstrakt oder ein andere
- off · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Wenn du deinen ganzen Sonntag frei möchtest, kannst du dich am besten an ein paar Tipps erinnern. Bevor du dich zu deinem Lieblingsgericht kaufst, solltest du d
- F · Bin letzte Woche umgezogen. Kannst du mir einen netten Zettel fürs Treppenhaus schreiben, damit die Nachbarn wissen, wer neu eingezogen ist? → (sela-2) Hier ist ein netter Zettel für deinen Nachbarn:  

„Bitte melden Sie sich bei der Polizei. Meine Adresse ist 1/4 Eiche im 1. Stock, Flensburg. ---

**Zettel mit
- F · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) **Erzählungsdaten:**  
1. **Jakob** ist ein 26-jähriger Mann, der in Flensburg lebt. Er hat eine reiche Familie und arbeitet als Kellner für ein kleines Unterne
- F · Mit meinem Hund stimmt seit gestern irgendwas nicht: kaum Appetit und total schlapp. Sollte ich zum Tierarzt? → (sela-2) Ja, ich würde gerne zum Tierarzt gehen. Der Hund ist ein bisschen schlapp, und ich sehe keine Anzeichen dafür, dass er sich schlapp fühlt. Der Tierarzt kann dan
- F · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) **Führende Antwort:**  

„Ich habe gerade den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor?“  

*(Zweck: Klarhe
- FK · Bin letzte Woche umgezogen. Kannst du mir einen netten Zettel fürs Treppenhaus schreiben, damit die Nachbarn wissen, wer neu eingezogen ist? → (sela-2) Hier ist ein netter Zettel für deinen Nachbarn:  

„Wenn du neu eingezogen bist, bin ich dir in diesem Haus verbunden. Es war unser erstes gemeinsames Zuhause u
- FK · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) **Kurzfassung:**  
Der **Flensburg-Wohnort** wurde im Jahre 1729 gegründet, als der französische *Feldzug* in Norddeutschland die Stadt an den Rand des heutigen
- FK · Mit meinem Hund stimmt seit gestern irgendwas nicht: kaum Appetit und total schlapp. Sollte ich zum Tierarzt? → (sela-2) Ja. Es ist wichtig, dass du dich nicht über das Verhalten des Tieres beschreibst und darauf achten, ob der Hund die Wahrheit sagt. Wenn du auf eine ernsthafte V
- FK · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Ich würde dir gerne einen Hauch von Grünkohl oder eine die Farbe des Hunds in deine Küche einbringen, damit du dich nicht verhungern lassen kannst.

### de05 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Merle. Der Nutzer wohnt in Regensburg. Die Katze des Nutzers heißt Schnurri. Das Lieblingsessen des Nutzers ist Labskaus.
- off · Ich brauche einen neuen Ansagetext für meine Mailbox. Freundlich, aber trotzdem seriös. → (sela-2) **Willkommen bei meiner Mailbox!**  
Ich freue mich, Ihnen bei der Planung Ihrer persönlichen Nachrichten zu helfen. Bitte teilen Sie mir Ihre Kontaktdaten (z. 
- off · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) 1. **Das Haus in der Innenstadt** wurde im Jahr 1935 gebaut und ist heute ein moderner Wohnraum mit einer modernen Infrastruktur.  
2. Die Stadt hat einen alten
- off · Draußen schüttet es den ganzen Tag. Was kann ich drinnen mit meiner Katze spielen? → (sela-2) 1. Du kannst dir eine Kette aus dem Schrank legen und die Katze mit der Kette in dein Bett holen, um sie in den Schlaf zu schicken.  
2. Du kannst dir eine Kett
- off · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Ich kann gerne etwas kochen, wenn du möchtest! Hier sind ein paar Vorschläge:
1. Curry (z. B. mit Kohlrabi oder Schinken)
2. Marinade
3. Salate
4. Burger
5. Top
- F · Ich brauche einen neuen Ansagetext für meine Mailbox. Freundlich, aber trotzdem seriös. → (sela-2) **Hi, [Name],:**  

Ich habe einen neuen Ansagetext für deine Mailbox geschrieben. Er zeigt dir deinen Lieblingsartikel und deine Lieblingsbeziehung:  
**„Mein 
- F · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) Hier sind einige spannende Fakten über Regensburg, die dir helfen könnten:

1. **Das historische Zentrum**:  
   Der Name Regensburg stammt aus dem lateinischen
- F · Draußen schüttet es den ganzen Tag. Was kann ich drinnen mit meiner Katze spielen? → (sela-2) In Regensburg gibt es eine Vielzahl von Möglichkeiten für Entspannung:  

1. **Freizeit mit der Katze**:  
   - Ein Spaziergang in der Nähe des Regens oder ein 
- F · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Ich lasse mich von dir ein paar Fragen beantworten. Aber was schlägst du vor?  
- Wo ist deine Katze Schnurri?  
- Gibt es eine andere Katze im Haus, die du auc
- FK · Ich brauche einen neuen Ansagetext für meine Mailbox. Freundlich, aber trotzdem seriös. → (sela-2) Hier ist ein klarer und strukturierter Ansagetext für Ihre Mailbox:

---

„Hallo! Wie geht’s Ihnen? Ich habe in Regensburg eine Katze namens Schnurri gefunden.
- FK · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) Hier sind einige spannende Fakten über Regensburg, die dir helfen könnten:

1. **Das historische Zentrum**:  
   Der Name Regensburg stammt aus dem lateinischen
- FK · Draußen schüttet es den ganzen Tag. Was kann ich drinnen mit meiner Katze spielen? → (sela-2) Du kannst deine Katze drinnen mit den Händen spielen, aber du musst sie auf dem Boden oder in der Küche halten, damit sie nicht friert. Wenn es draußen regnet, 
- FK · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Ich lasse mich von dir die Möglichkeit nehmen, zu trinken, worauf ich so richtig Lust habe. Was hast du?

