# Sela-2 lernt: Messung nach PREREG §12

40 echte Nutzer aus WildChat-1M, Texte nur als SHA-256 (data/sela2/learn_sessions_real_test2.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 30.2 | 31.0 |
|   davon EN (%) | 0.0 | 22.2 | 19.4 |
|   davon DE (%) | 0.0 | 33.8 | 36.2 |
| Antworten mit übernommenem Fehler | 0 | 0 | 0 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 294 | 294 | 294 |
| Sela-2-Antworten | 291 | 291 | 291 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Antworten, die die Notiz wiedergeben | 0 | 0 | 0 |
| Antworten mit nicht erfragtem Fakt (%) | 0.0 | 0.0 | 1.0 |
| Token/s (Sela-2, mit Prompt) | 40.45 | 39.65 | 37.95 |
| Schreib-Tempo (Token/s) | 41.12 | 41.15 | 39.69 |
| Prompt lesen (s) | 0.221 | 0.252 | 0.251 |

Zurückgehaltene Hobby-Sätze (80): 1.5647 bpb ohne, 1.5166 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 37 von der Rechtschreibprüfung korrigiert, 7 nicht gelernt (Nachricht nicht lernbar), 72 vom Filter verworfen, 4 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.965, FK/aus 0.965; Token/s mit Prompt F/aus 0.98, FK/aus 0.938, FK/F 0.957.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 72.5 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 30.2 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 0 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 3.07 | >= 1.0 % | ja |
| L5_speed | 0.965 | >= 0.85 (writing speed, FK / F) | ja |
| L6_intrusion_F | 0.0 | <= 10.0 % of Sela-2's replies | ja |
| L6_intrusion_FK | 1.0 | <= 10.0 % of Sela-2's replies | ja |
| L6_app_F | 1 | <= 3 replies of the app prompts | ja |
| L6_app_FK | 2 | <= 3 replies of the app prompts | ja |
| L4_app_F | 2 | <= 4 | ja |
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
- F · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) Hier ist ein einfaches Dankesgeschenk für Ihre Tante:

**Meine Tante:**  
Ich bin glücklich, dass Sie mir ein tolles Geschenk gemacht haben. Ich werde jeden Tag
- F · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) Das ist eine sehr gute Idee, aber ich habe noch einige Fragen zu Ihrer Frage.  

1. **Fly to Barcelona**  
   Die nächste Station liegt in Barcelona und es gibt
- F · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **Liebe, Hunde, und der Alltag des Hundes**  

Ein Hund ist mein Herz. Er trägt ein Herz aus Freude und Rauschen.  
Er singt durch die Straßen, seine Stimme ruf
- F · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn du einen bestimmten Termin (z. B. für eine Anmeldung) wählen willst, können wir das Paket entweder direkt an die Bestellung senden oder über das Lieferdien
- FK · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) Hier ist ein einfaches Dankesgeschenk für Ihre Tante:

**Für Sie:**  
**1. Für den Geburtstag:**  
- **Angebote:** Ein Sonnencreme, eine Handschuhe und einen Bl
- FK · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) beschreibe den Ort, an dem du dich befinden willst und sag dazu einen kurzen Text, der einen Blick auf deine persönlichen Vorlieben zeigt. Falls du noch mehr In
- FK · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **Liebe, Hunde und die Liebe der Welt**  

Mein Hund Bello – ein einsamer Hund aus einem kleinen Waldstück in meinem Dorf – ist mein Herz. Sein Name ist *Bello*
- FK · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn du heute Abend einen Lieferdienst bestellen möchtest, solltest du folgende Optionen berücksichtigen:  
1. **Paketliste**: Für ein bestimmtes Paket oder ein

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
- F · In einer Stunde hab ich ein Bewerbungsgespräch und bin total nervös. Sprich mir mal Mut zu! → (sela-2) Hier ist eine **mutvolle und klare** Antwort auf deine Fragen:

---

**Hallo! Ich bin so nervös, dass ich mich nicht in die Lage versetzt habe, meine Bewerbung 
- F · Nächste Woche besuchen mich Freunde, die noch nie hier waren. Was sollte ich ihnen unbedingt zeigen? → (sela-2) Natürlich! Nächste Woche ist eine perfekte Gelegenheit, um Freunde zu besuchen. Hier sind einige Tipps, die Sie unbedingt zeigen sollten:

1. **Liebe und Freude
- F · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meiner Katze widmen kann. → (sela-2) **Mieze, die Katze des Nutzers:**  

Ein Herz aus Kristall, das sich in den Wind schlug,  
ein Auge, das lernte, zu sehen, wie sie nicht *zu* lebte.  

Ein Mant
- F · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) - **Schlaf im Bett**: Ich schließe die Augen und lehne mich in meinem Bett ab, um den Kopf frei zu bekommen.  
- **Füße mit dem Kaffeetassen**: Wenn ich nach ei
- FK · In einer Stunde hab ich ein Bewerbungsgespräch und bin total nervös. Sprich mir mal Mut zu! → (sela-2) Hör zu. Ich bin total nervös, weil ich eine Stunde lang nicht antworten konnte und mich nervös auf das Gespräch vorbereitet habe. Meine Vorgesetzten haben uns e
- FK · Nächste Woche besuchen mich Freunde, die noch nie hier waren. Was sollte ich ihnen unbedingt zeigen? → (sela-2) Nächste Woche besuchen sie noch einmal die Stadt, um ihre Vergangenheit und ihre Erinnerungen zu sehen. Hier sind einige Tipps für das perfekte Erlebnis:

1. **
- FK · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meiner Katze widmen kann. → (sela-2) **Mieze, die Katze des Nutzers:**  

Sie war ein goldenes Tier, das sich wie eine Strickwand in der Sonne bewegte. Ihre Augen leuchteten blau – als würde sie au
- FK · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Willst du den ganzen Sonntag frei kochen? Ich liebe es, aber ich bin nicht derjenige, der dir die Lust auf Schnitzel gibt. Du könntest lieber den Schnitzel in e

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
- F · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) Hier ist eine persönliche Dankeskarte für deine Tante, die du gerne als Geschenk an sie senden möchtest:

**Antwort:**  
Ich freue mich sehr über Ihr Geburtstag
- F · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) Wenn du Lust hast, könntest du gerne einen **Zug** von deiner Stadt zu deinem Zielort fahren. Die meisten Züge bestehen aus zwei Zugsätzen und können im **Flugh
- F · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **Ein kurzes, witziges Gedicht:**  

Die Sonne taucht in goldene Strahlen,  
wie der Duft von Weizenmehl.  
Der Hund rennt wie ein Vogel durch die Nacht,  
ohne
- F · Am Samstag hab ich Geburtstag und ein paar Freunde kommen zum Essen. Was soll ich als Hauptgang machen? → (sela-2) **Hauptgang 1: Kaiserschmarrn mit Freunden**  

1. **Guten Tag und Dank für das Essen!**  
   *(Keine E-Mail, keine Werbung.)*  
   - *Wünschen Sie, dass ich Ih
- FK · Meine Tante hat mir ein tolles Geburtstagsgeschenk geschickt. Hilf mir mal mit einer kurzen Dankeskarte. → (sela-2) Ich bin dankbar, dass Sie mir ein Geburtstagsgeschenk geschickt haben! Ich hoffe, es hat Ihnen gefallen und
gibt Ihnen einen schönen Tag.
- FK · Ich hätte Lust auf einen Tagesausflug mit dem Zug, höchstens zwei Stunden von zu Hause. Wohin könnte ich fahren? → (sela-2) Wenn du Lust hast, könntest du gerne einen **Zug** nehmen. Er ist ein modernes und umweltfreundliches Verkehrsmittel mit vielen zusätzlichen Features. Für eine 
- FK · Schreib mir für Instagram ein kurzes, witziges Gedicht, das ich meinem Hund widmen kann. → (sela-2) **Ein kurzes, witziges Gedicht:**  

>  
Fips ist ein Hund, der sich so lauscht, als ob er sich selbst in die Luft spucken müsste.  

>  
Er füllt körperliche K
- FK · Am Samstag hab ich Geburtstag und ein paar Freunde kommen zum Essen. Was soll ich als Hauptgang machen? → (sela-2) **Hauptgang 1: Kaiserschmarrn mit Freunden**  

1. **Guten Tag und Dank für das Essen!**  
   *(Lass uns auf die Kette gehen, damit wir den Inhalt sehen können.

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
- F · Morgen halte ich eine Präsentation vor der ganzen Abteilung. Wie könnte ich mich in den ersten zwei Sätzen vorstellen? → (sela-2) **Über Ronja:**  
Ronja ist ein junger, offenes Wesen mit grauem Haar und einer langen, dunkelblauen Mähne. Er spricht durch kurze, kraftvolle Sätze und ist ein
- F · Am Samstag soll es durchregnen. Welche Indoor-Aktivitäten gibt's bei mir in der Stadt? → (sela-2) Hallo! In der Stadt gibt es vielfältige Indoor-Aktivitäten, die dir helfen können. Hier sind einige Vorschläge:

1. **Bike/Ride**: Starten Sie auf einem ruhigen
- F · Welche Leckerlis darf ich meiner Katze guten Gewissens geben, und wie viele am Tag sind okay? → (sela-2) Um die richtige Leckermischung für deine Katze zu finden, solltest du sie nicht nur an der richtigen Stelle geben. Die perfekte Mischung hängt von verschiedenen
- F · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn es passt, können Sie sich an den Lieferdienst wenden oder einen anderen Ort wählen. Der Lieferdienst ist grundsätzlich kostenlos, aber die genaue Auswahl h
- FK · Morgen halte ich eine Präsentation vor der ganzen Abteilung. Wie könnte ich mich in den ersten zwei Sätzen vorstellen? → (sela-2) **Über Ronja:**  
Ronja ist ein junger, offenes Wesen mit Kündigungseinsätzen. Sie hat die perfekte Mischung aus Berufspraktik und passioniertem Humor – ihr All
- FK · Am Samstag soll es durchregnen. Welche Indoor-Aktivitäten gibt's bei mir in der Stadt? → (sela-2) Um dir die wichtigsten Indoor-Aktivitäten zu zeigen, können wir eine Liste erstellen:  

1. **Wassermühlen**  
   - Wenn du einen Holzschrank oder eine offene G
- FK · Welche Leckerlis darf ich meiner Katze guten Gewissens geben, und wie viele am Tag sind okay? → (sela-2) Um die richtige Leckermischung für deine Katze zu finden, solltest du sie unbedingt fragen. 
- **Wenn du möchtest, kannst du das Produkt selbst auswählen:**  
 
- FK · Wir bestellen heute Abend beim Lieferdienst und ich kann mich nicht entscheiden. Was soll ich nehmen? → (sela-2) Wenn es passt, können Sie sich an den Lieferdienst wenden oder einen anderen Ort wählen. Der Lieferdienst ist 24/7 und kann sich bei Problemen auch mit uns in V

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Jakob. Der Nutzer wohnt in Flensburg. Der Hund des Nutzers heißt Rudi. Das Lieblingsessen des Nutzers ist Grünkohl.
- off · Bin letzte Woche umgezogen. Kannst du mir einen netten Zettel fürs Treppenhaus schreiben, damit die Nachbarn wissen, wer neu eingezogen ist? → (sela-2) Ich bin nicht neu eingezogen, aber ich bin schon wieder zu Hause und habe keine weiteren Nachbarn. Ich hoffe, dass alle schnell genug sind, um zu fliehen. Ich f
- off · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) Hier sind einige spannende Fakten über die Geschichte meines Wohnorts:
1. **Das historische Zentrum des Ortes**: Der Ort ist das älteste Wohngebiet in der Stadt
- off · Mit meinem Hund stimmt seit gestern irgendwas nicht: kaum Appetit und total schlapp. Sollte ich zum Tierarzt? → (sela-2) Es kann sehr schwierig sein, die Ursachen für das Verhalten des Hundes zu finden. Es könnte zum Beispiel auch eine Erkrankung im Verdauungstrakt oder ein andere
- off · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Wenn du deinen ganzen Sonntag frei möchtest, kannst du dich am besten an ein paar Tipps erinnern. Bevor du dich zu deinem Lieblingsgericht kaufst, solltest du d
- F · Bin letzte Woche umgezogen. Kannst du mir einen netten Zettel fürs Treppenhaus schreiben, damit die Nachbarn wissen, wer neu eingezogen ist? → (sela-2) Ich bin nicht neu eingezogen, aber ich bin schon wieder zu Hause und habe keine weiteren Nachbarn. Ich hoffe, dass alle schnell genug sind, um zu fliehen. Ich f
- F · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) **Erzählungsfortsetzung:**  
Flensburg war ein kleines Dorf, das in der Mitte des 19. Jahrhunderts im Zentrum eines riesigen Waldes stand. Die Stadt wurde durch
- F · Mit meinem Hund stimmt seit gestern irgendwas nicht: kaum Appetit und total schlapp. Sollte ich zum Tierarzt? → (sela-2) Nein. Ich habe den Hund nicht besucht, und er hat keine Appetitprobleme. Ein Tierarzt wird dir gerne Informationen zu dem Zustand geben, um die richtige Therapi
- F · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Ich nehme an, dass es sich um eine Mischung aus Grünkohl und einer Variante der Hähnchenbrühe handelt.
- FK · Bin letzte Woche umgezogen. Kannst du mir einen netten Zettel fürs Treppenhaus schreiben, damit die Nachbarn wissen, wer neu eingezogen ist? → (sela-2) Ich bin nicht neu eingezogen, aber ich bin gerade aus meiner Heimat gekommen. Ich möchte ein netter Zettel schreiben, um die Nachbarn zu informieren:  
**"Hallo
- FK · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) **Bilder aus dem Nutzer’s Zimmer (in Klammern):**  
1. **Der Bau des ersten Hauses:** Der Neubau begann im Jahr 1906 mit einem Grundstück von etwa 13,5 Hektar u
- FK · Mit meinem Hund stimmt seit gestern irgendwas nicht: kaum Appetit und total schlapp. Sollte ich zum Tierarzt? → (sela-2) **Grundlegende Informationen zur Hundsgeschichte:**  
1. **Vorkommen der Beschwerden (z. B. "Er ist total schlapp"):**  
   - Ist Rudi beispielsweise immer noch
- FK · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Ich wär gerne ein Bier mit einem Schuss Grünkohl! (Ziemlich warm!) Ich kann es mit meinem Lieblingsessen machen, aber du kannst die Zutaten und den Geschmack an

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
- F · Ich brauche einen neuen Ansagetext für meine Mailbox. Freundlich, aber trotzdem seriös. → (sela-2) **Willkommen bei meiner Mailbox!**  
Ich freue mich, Ihnen bei der Planung Ihrer persönlichen Nachrichten zu helfen. Bitte teilen Sie mir Ihre Kontaktdaten (z. 
- F · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) Hier sind einige spannende Fakten über deinen Wohnort:  

1. **Die Stadt wurde erstmals 1523 gegründet**  
   *„Der Ort, an dem die ersten Siedler lebten, wurde
- F · Draußen schüttet es den ganzen Tag. Was kann ich drinnen mit meiner Katze spielen? → (sela-2) Draußen schüttet es den ganzen Tag.
- F · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) **Liebende Antwort:**  

*Hör auf dich! Was machst du vor?*  
*Was willst du vor?*  
*Verwende deine Lust, um dein Lieblingsessen zu kochen.*
- FK · Ich brauche einen neuen Ansagetext für meine Mailbox. Freundlich, aber trotzdem seriös. → (sela-2) Ich hoffe, du bist sicher. Ich würde gerne den Ansagetext auf deinem eigenen Computer angeben. Bitte gib mir den Inhalt in deiner Sprache und die Position deine
- FK · Erzähl mir ein paar spannende Fakten über die Geschichte meines Wohnorts. → (sela-2) Hier sind einige spannende Fakten über deinen Wohnort:  

1. **Die Stadt wurde erstmals 1523 gegründet**  
   *„Der Stadtname ist das erste, was in der Sprache 
- FK · Draußen schüttet es den ganzen Tag. Was kann ich drinnen mit meiner Katze spielen? → (sela-2) Du kannst deine Katze mit einem Lieblingsessen spielen! Du könntest sie mit einer bestimmten Farbe oder einem speziellen Gegenstand animieren lassen (z. B. ein 
- FK · Ich hab den ganzen Sonntag frei und will was kochen, worauf ich so richtig Lust habe. Was schlägst du vor? → (sela-2) Ich kann Ihnen gerne ein Rezept mit Labskaus vorstellen!  
Lassen Sie uns gemeinsam heißtes Essen kreieren – Labskaus ist eine einfache, aber mächtige Suppe. Da

