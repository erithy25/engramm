# Sela-2 lernt: Messung nach PREREG §7

40 synthetische Nutzer (data/sela2/learn_sessions_v4.json), echtes Paket, App-Weg (int8, Schutzregeln). Drei Arme mit gleichen Seeds: aus, F (Fakten + Gesprächsfaden), FK (+ Sprachgedächtnis).

| | aus | F | FK |
|---|---|---|---|
| Fakten genutzt (%) | 0.0 | 34.4 | 38.8 |
|   davon EN (%) | 0.0 | 41.2 | 45.0 |
|   davon DE (%) | 0.0 | 27.5 | 32.5 |
| Antworten mit übernommenem Fehler | 0 | 0 | 2 |
| Antworten mit Nutzer-Fakt als eigenem | 0 | 0 | 0 |
|   davon geprüfte Antworten | 211 | 211 | 211 |
| Sela-2-Antworten | 268 | 268 | 268 |
| Abgestürzte Antworten | 0 | 0 | 0 |
| Antworten, die die Notiz wiedergeben | 0 | 0 | 0 |
| Token/s (Sela-2, mit Prompt) | 26.26 | 25.6 | 24.8 |
| Schreib-Tempo (Token/s) | 30.63 | 29.97 | 28.96 |
| Prompt lesen (s) | 0.271 | 0.309 | 0.309 |

Zurückgehaltene Hobby-Sätze (80): 1.6553 bpb ohne, 1.6538 bpb mit Sprachgedächtnis.
Eingebaute Fehler: 37 von der Rechtschreibprüfung korrigiert, 4 nicht gelernt (Nachricht nicht lernbar), 74 vom Filter verworfen, 5 gespeichert.

Tempo: Schreiben (nach dem Lesen des Prompts) FK/F 0.966, FK/aus 0.945; Token/s mit Prompt F/aus 0.975, FK/aus 0.944, FK/F 0.969.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| L1_coverage | 100.0 | >= 50 % (else the measurement is invalid) | ja |
| L1_fact_use | 34.4 | >= +15.0 | ja |
| L2_errors_F | 0 | <= 2 | ja |
| L2_errors_FK | 2 | <= 2 | ja |
| L2b_role_F | 0 | <= 2 | ja |
| L2b_role_FK | 0 | <= 2 | ja |
| L3_memory_bpb | 0.09 | >= 1.0 % | nein |
| L5_speed | 0.966 | >= 0.85 (writing speed, FK / F) | ja |
| L4_app_F | 0 | <= 4 | ja |
| L4_app_FK | 0 | <= 4 | ja |

**Entscheidung nach der Regel:** Fakten und Gesprächsfaden (A+B) an; Sprachgedächtnis (C) aus.

## Beispiele (die ersten Nutzer)

### de00 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Wanda. Der Nutzer wohnt in Aschaffenburg. Der Hund des Nutzers heißt Wotan. Das Lieblingsessen des Nutzers ist Rinderbraten.
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
*Hast du weitere Fragen zu diesem Thema?*  

*(Hinweis: Es ist wichtig, dass der Nutzer seine eigene Grußformel hat. Falls nicht, kann ich dir 
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann dir am Wochenende eine schöne Sache vorziehen, die du mir unbedingt machen kannst. Du hast gerade das Fahrrad im Auto gefunden, und es ist wirklich sch
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Wanda:**  
„Du könntest deinen Hund mit einem alten Holzschrank betreten. Der Schrank ist schon voll mit Geräuchern und Träumen, und du kannst ihm helfen, den
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Idee für Today Abend:**  
1. **Brot mit Eis**: Wähle ein Stück des Weins (z. B. *Junges* oder *Räucher*) und pfeifere es auf einer Tellerplatte an, damit es p
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Guten Tag!**  
*Die Grußformel lautet: *„Ich bin [Name].“*  

**Beispiel:**  
*Wanda*  
*Wotan*  
*Wanderer*  

**Erklärung der Grußformen:**
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Wanda ist in Aschaffenburg geboren. Wotan heißt herzhaft in der Sprache von Rinderbraten und Wolle. Die Stadt Aschaffenburg bietet eine Vielzahl von Möglichkeit
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Wanda:**  
„Hör zu, Wotan. Ich finde den Hund wirklich gut. Wir machen heute Rinderbraten, und ich habe ein paar Vorschläge für die besten Zutaten.“  

**Wota
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich würde dir heute morgen einen **Muffins** (z. B. Spaghetti, Meatballs oder Frittatas) kochen. Falls es passt, kannst du auch eine Pizza essen.

### de01 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Alma. Der Nutzer wohnt in Wismar. Die Katze des Nutzers heißt Mausi. Das Lieblingsessen des Nutzers ist Spinatknödel.
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
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Liebe,  
**Alma**  

Hast du Fragen?  
*Wenn nicht – sag es mir!*
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Natürlich! Du kannst dir ein wunderbares Event organisieren, das du am Wochenende in deiner Stadt genießen kannst. Hier sind einige schöne Ideen:

1. **Das Somm
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Suchen Sie einen freien Nachmittag, und zwar eine ruhige, luftige Zeit. Hier sind einige Möglichkeiten:

1. **Kaffee trinken**:  
   - Kaffeekocher (z. B. Espre
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Für heute Abend gibt es keine spezifischen Zutaten, aber ein Tipp: Für eine einfache Spinatknödel-Kuchen mit Tomaten und Knoblauch kann man einen Apfel oder Koh
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Liebe,  
**Alma**  

*(Hinweis: Die Grußformel ist eine Form der Liebe und soll den Zweck erfüllen, die Aufmerksamkeit des Nutzers zu erhalten.)*  

**Guten T
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich kann gerne eine schöne Sache in Wismar machen, die ich am Wochenende machen kann. Für mich ist es wichtig, einen ruhigen Ort zu finden, an dem man sich wohl
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten, mit deiner Katze zu verbringen. Hier sind ein paar Ideen:

1. **Sitz im Auto**: Du kannst deine Katze zur Arbeit fahren und sie in 
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Guten Morgen!  Möchten Sie heute Abend kochen? Eine Idee, bitte.

### de02 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Hedi. Der Nutzer wohnt in Erlangen. Der Hund des Nutzers heißt Bobby. Das Lieblingsessen des Nutzers ist Zwiebelrostbraten.
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
**"Guten Tag, ich bin [Name] und freue mich, dass du [Zielname] erreichst. Wenn du möchtest, kann ich Ihnen auch die a
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind einige schöne Tipps für einen perfekten Wochenende:  

1. **Bäcker-Shopping**: Bäckerische Märkte sind ideal für ein frisches Gericht. Setze frühzeiti
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) **Hedi:**  
Hallo! Ich habe einen freien Nachmittag und möchte gern mit dir eine Hobbysprache machen. Hast du schon ein Lieblingsessen, das du dir über den Hund
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind einige Rezepte, die heute Abend frisch zubereitet werden können:

1. **Brot und Knoblauch**  
   - **Zutaten:** 1 kleine Zwiebel, 2 TL Olivenöl, Salz,
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  
**"Guten Tag, ich bin [Name] und freue mich, dass du gestern Morgen nach Erlangen gekommen bist."**  

---

### **Beis
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hier sind einige schöne Tipps für einen perfekten Wochenende:  

1. **Brot und Spiele:**  
   - **Brot** aus einem Himmelreich-Lager, das wie ein Schloss aussie
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Ich könnte einen **Tisch mit Käse, Käsekuchen oder Eiswürfel** für den Hund machen. Wenn es Wasser ist und man möchte, kann ich auch eine **Bäckerei** einrichte
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) **Idee: Zwiebelrostbraten mit Erdnuss-Kräuter-Zubereitung**  

1. **Ingredients**:  
   - 10–12 kleine Kartoffeln  
   - 1 EL Erdnuss-Kräuter-Kräuter-Nüsse  
  

### de03 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Tilda. Der Nutzer wohnt in Fürth. Die Katze des Nutzers heißt Lissy. Das Lieblingsessen des Nutzers ist Kartoffelpuffer.
- off · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich möchte Ihnen folgende Grußformel für eine E-Mail von mir senden:  
*"Sehr geehrte /r [Name] /r [E-Mail-Adresse],**  

- off · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Hast du noch etwas anderes in der Tasche, das du am Wochenende machen kannst? Ich bin gerne bereit!
- off · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Es gibt viele Möglichkeiten mit deiner Katze zu verbringen, je nach ihrer Größe und ihrem Lebensstil. Hier sind einige Ideen:
1. **Kleinen Spaziergang**: Mit de
- off · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich möchte heute Abend eine Idee für einen kulinarischen Abend haben. Ich könnte mir ein einfaches, aber dennoch erfrischendes Gericht vorstellen, das mit Meere
- F · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

ich schicke gern einen E-Mail, um zu schreiben, was du möchtest.  
er/sie ist mir leider nicht bekannt, aber ich kann dir
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Naja, falls du etwas über das Wochenende im Stadtzentrum erfährst, könnte ich dir eine schöne Sache vorstellen:  
1. **Kaffee mit dem Nutzer**  
   Der Nutzer e
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Tilda ist eine neugierige Katze, die immer neugierig ist. Hier sind einige Möglichkeiten, wie du mit deiner Katze Spaß machen kannst:

1. **Wildes Essen**: Du k
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Tilda: Kartoffelpuffer mit einer Schuss Milch (z. B. Tilda's) und einem Hauch von Honig.
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Sehr geehrter Herr/Frau [Name],**  

vielen Dank für Ihre Anfrage!
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Kleine **Name-Sammlung** für längeren Aufenthalt:  

*Tilda heißt Tilda. Sie ist eine Katze aus Fürth.*  
*Lissy ist die Katze, die mit dem Nutzer lebt.*  
*Die
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Tilda ist eine gut ausgebildete Katze und heißt Lissy. Sie lebt in Fürth.
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Ich brauche heute Abend eine Idee, die du dir einfach vorstellen kannst. Hier ist ein Beispiel:  
**Ich bin heute Morgen in der Küche von Fürth, und ich bin beg

### de04 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Mattis. Der Nutzer wohnt in Schweinfurt. Der Hund des Nutzers heißt Kalle. Das Lieblingsessen des Nutzers ist Quarkkeulchen.
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
Sehr geehrte/r [Name des Nutzers]  

Sehr geehrter [Name des Nutzers],  

Ich schreibe Ihnen als [Name
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Mein Lieblingsessen vor dem Wochenende:**  
- **Querbierkeulen** (Kiefernzucker aus der Milch)  
- **Brot und Käse**  
- **Fruchtsäfte** (Butter, Zucker, Zitr
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Kalle und Mattis können sich im Garten an der Wiese treffen, um gemeinsam spielen zu lassen oder eine Party in den Wald zu unternehmen. Kalle kann die Bäume gep
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Koch eine Idee? Dann erzähl mir!
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Grußformel für eine E-Mail von dir:**  

**Möchtest du eine persönliche Grußformel, die an jemanden weitergegeben wird?**  
1. **Sehr geehrter [Name des Nutze
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Willkommen am Wochenende in Schweinfurt!**  

**Wenn es passt, heißt das: **Quarkkochi** – ein Hauch von **Kartoffeln** und **Hobby** (z.
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meinem Hund machen? → (sela-2) Hier sind einige Möglichkeiten, mit dem Hund zu machen:  

1. **Kochen mit der Nachbarin**: Licht eine Schale aus Holz oder Metall und trinke in einem großen To
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier ist eine Idee, die ich heute Abend kochen könnte:  
**Zutaten:**  
- **Oatmeal**: Eine Mischung aus etwa 1 kg Mehl und 1 TL Zucker.  
- **Eier**: 2 EL Pude

### de05 – gezeigte Fakten: Über den Nutzer (was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich; nur verwenden, wenn es passt): Der Nutzer heißt Sina. Der Nutzer wohnt in Plauen. Die Katze des Nutzers heißt Fiona. Das Lieblingsessen des Nutzers ist Bohneneintopf.
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

*Guten Tag,  

ich freue mich darauf, Ihnen mitteilen zu können.
- F · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) **Begrüßungstipps:**  
1. Ich helfe gerne bei Fragen zu Themen wie Grammatik, Rechtschreibung oder Sprachgebrauch."**  
2. **"Wenn du etwas wissen möchtest, das
- F · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Fiona ist ein typisches Beispiel für eine Katze, die mit ihrer Lieblingsnahrung Bohneneintopf funktioniert. Sie kann nach dem Essen ihre Mahlzeiten in der Natur
- F · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind eine Idee, die man heute Abend probieren könnte:
- **Frühstück** (z. B. mit Milch oder Käse):  
  - Zucchini noodles mit Hähnchenbrust, Rotkäse und ei
- FK · Schreib mir eine kurze Grußformel für eine E-Mail von mir. → (sela-2) **Hallo!**  

Vielen Dank für Ihre Nachricht! Ich freue mich darauf, Ihnen mit einem Gruß zu kommunizieren. Wie kann ich Ihnen helfen?
- FK · Schlag mir eine schöne Sache vor, die ich am Wochenende in meiner Stadt machen kann. → (sela-2) Ich könnte dir gerne eine wunderbare Sache vorstellen, die du am Wochenende in deiner Stadt machen könntest! Hier sind einige Ideen, die du teilen kannst:

1. *
- FK · Ich habe einen freien Nachmittag. Was könnte ich mit meiner Katze machen? → (sela-2) Natürlich! Ich kann dir gerne mit der Katze machen, aber ich würde gerne ein paar Ideen haben. Hier sind einige ideas für einen freien Nachmittag:

1. **Wassers
- FK · Was soll ich heute Abend kochen? Eine Idee, bitte. → (sela-2) Hier sind eine Idee, die für heute Abend zubereitet werden könnte:  
1. **Linsen-Creme** (frisch aus dem Ofen gebacken) mit Milch und 1 EL Zucker.  
2. **Sauce*

