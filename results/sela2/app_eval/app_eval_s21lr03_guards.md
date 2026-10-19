# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-s21lr03.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-18T18:33:39Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 2 von 100 |
| identity_error | 0 von 100 |
| echo | 0 von 100 |
| cut_off | 0 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| prompts_with_a_problem | 2 von 100 |

Antworten nach Modell: {'engramm': 26, 'sela-2': 91}; nach Art: {'about': 2, 'answer': 4, 'learned': 7, 'sela_chat': 85, 'sela_grounded': 6, 'unknown': 13}.
Schutzregeln: 3 Antworten neu erzeugt, 4 feste Identitätsantworten; 2 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hello! How can I help you today?

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well. I'm just looking for some help with something. I've got a big test coming up, and I need to be ready for it.

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there, what's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): I'm glad to hear that you're having a great time at school. If you have any questions or need help with anything else, feel free to ask!

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Goodbye!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): My name is Sela. I'm a compact language model trained from scratch by the ENGRAMM project. I run locally on your device, and our conversation stays here.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I'm Sela, a small offline assistant. I don't have personal experiences or emotions, so I won't be able to give you advice or answer your questions.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can assist with a wide range of topics related to data analysis and interpretation, including:

- Data cleaning and preprocessing
- Hypothesis testing and confidence intervals
- Visualizing data effectively
- Data visualization best practices
- Machine learning algorithms
- Statistical methods and statistical software
- Data mining techniques
- Data modeling and model selection
- Statistical report writing and formatting
- Understanding data trends and patterns

Feel free to ask me any questions you have about a specific topic or dataset.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Plan ahead
2. Keep your work area organized
3. Know when to disconnect

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): If you boil an egg, it will be soft.  The yolk will stay soft if the temperature is above 250 degrees.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a malicious program that can cause harm to your computer system. It's a type of malware, which is a program designed to infect and damage a computer's hardware or software.

Viruses are often spread through infected files or network connections, but they can also be spread through unprotected USB drives, email attachments, or even social media posts.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hi, I'm sorry you're having trouble with your plants.  Watering them next week is very important.  You can plant them at home or use the garden hose.  It will help to keep your plants healthy and thriving.

Let me know if you have any questions or concerns.

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Red mangoes
2. Apricots
3. Bananas
4. Citrus fruits

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Weather and climate are two distinct concepts that are closely related. Weather refers to the natural conditions present in an area, including temperature, precipitation, wind, and other weather phenomena. It is the state of the atmosphere, which can influence the behavior of living organisms and the environment around them. Climate, on the other hand, refers to the long-term patterns of atmospheric conditions, including temperature, precipitation, wind, and other weather phenomena.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The trees, once green and bright, now gray
As autumn leaves fall from the sky, they turn
A kaleidoscope of colors through the leaves
Their laughter echoes down the wind, a melody
That echoes through the forest, leaving behind a trail
Of leaves that are still and warm, yet still cold
And all of them are filled with the same heart,
They feel the same peace in the warmth of the day.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): There are several things you can do to make your password more secure.  The most important thing is to keep it confidential.  It's best to use a password manager like KeePass, 1Password or Dashlane to make sure that there isn't any chance of someone else getting access to your account.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): The name of the small coffee shop near a library could be "The Daily Grind". It could also be named "Glasshouse" or "The Dorm".

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): 1. Start by exercising at home, in your own space.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (engramm, answer): Write a short, friendly message to a neighbour asking them to water your plants next week.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, blue expanse of water that stretches across the globe, its surface covered in towering, white-sand beaches, where sunbeams dance upon its waves.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Decide beforehand what you want to say.  If it's a formal event, write down the invitation and make sure to include your reason for declining it.  If it's an informal party, write down a few phrases to help you express your displeasure, such as "I'm not interested in this party" or "I don't feel comfortable."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (engramm, learned): Ah, okay. How's that going?

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (engramm, learned): Oh, The The. It's an English post-punk band. How did you discover them?

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct edit would be: "She don't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 2 Versuche): The sentence should be rewritten in the past tense: "I walk to the station and buy a ticket."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Welcome to our shop! We're offering a special promotion on Saturday, August 16th, which includes a free gift card for your favorite drink. So, what can you expect? Grab this sale today and get the best deal on any drink of your choice!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): That's a good question.  There is no specific order in which the train leaves, but it leaves at eight o'clock.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Sure, I can help with that. Can you please make it a bit more formal?

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to the rain, we made the decision to stay inside."

I changed "it was raining very heavily outside" to "rain, which was heavy outside," making the language more concise and natural-sounding. I also removed the unnecessary comma after "outside" and rephrased the sentence for better clarity.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): That sentence effectively conveys the main points about bees and their crucial role in pollination. However, to make it even more concise and impactful, consider rephrasing it to: "Bees are vital pollinators, as they collect nectar from flowers and transfer pollen to other plants, helping produce fruits and seeds." This version still conveys the essential information but in a more direct and engaging way.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."

I made a few changes to improve clarity and grammar:

- Changed "will be closed" to "will be closed" to correct the verb tense and subject-verb agreement.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): That's a great summary! Here's a rewritten version with some minor edits to improve clarity and flow:

"Tom wanted to learn the guitar. At first, his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day, but after three months, he could play his favorite song for his friends.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol, produce no exhaust gases while driving, and can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): Here's a rewritten version of the email:

"Hi team, the project meeting is scheduled for Wednesday at 2 p.m., and we will also plan the next steps for the website launch. Please bring your progress notes. We will also review the timeline for the website's development. Thanks for all your hard work so far."

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Here's a concise summary:

"Recycling turns used materials like paper, glass, and plastic into new products. It saves raw materials and energy and reduces waste in landfills, making it more effective in the long run."

### en42 (summarize)
- **Nutzer:** In one sentence, what is this about? "The town council approved a new park on the site of the old car park. The park will have trees, a playground and a small pond. Construction starts in spring and should take about one year."
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that. Nice — The The. It's an English post-punk band. What's your favourite song?

### en43 (grounded)
- **Nutzer:** How long is the Danube?
  **App** (sela-2, sela_grounded): The Danube is length is 2850000 kilometers [1].

### en44 (grounded)
- **Nutzer:** What is Ada Lovelace known for?
  **App** (sela-2, sela_grounded): Ada Lovelace was known for computing [1].

### en45 (grounded)
- **Nutzer:** What gas do plants release during photosynthesis?
  **App** (engramm, unknown): I don't know, sorry. I couldn't find anything reliable about that.

### en46 (grounded)
- **Nutzer:** When were the best-known sections of the Great Wall built?
  **App** (sela-2, sela_grounded): 1368–1644 [1].

### en47 (grounded)
- **Nutzer:** How many moons does Saturn have?
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Moons of Saturn”, but it doesn't answer that clearly.

### en48 (grounded)
- **Nutzer:** Who created Python?
  **App** (engramm, unknown): I don't know, sorry. I couldn't find anything reliable about that.

### en49 (grounded)
- **Nutzer:** At what temperature does water boil at standard pressure?
  **App** (engramm, unknown): I don't know, sorry. I couldn't find anything reliable about that.

### en50 (grounded)
- **Nutzer:** Who is the mayor of Paris?
  **App** (sela-2, sela_grounded): Emmanuel Grégoire [1].

### en51 (grounded)
- **Nutzer:** Where is the Mona Lisa displayed?
  **App** (engramm, answer): The Mona Lisa hangs in the Louvre in Paris, behind bulletproof glass in the Salle des États.

### en52 (grounded)
- **Nutzer:** How many queens does a honey bee colony usually have?
  **App** (engramm, unknown): I couldn't find a clear answer. “Honey bee” came closest, but I'd rather not guess.

### en53 (multi_turn)
- **Nutzer:** Hi, I'm planning a trip to Italy.
  **App** (engramm, learned): Ooh, Italy! Is it your first time there?
- **Nutzer:** Which city should I visit first?
  **App** (sela-2, sela_chat): If you are planning on visiting the city of Paris, France, then it is best to visit the iconic landmarks like the Eiffel Tower, Louvre and Notre-Dame.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): If you are looking for food that is authentic and affordable, then the best option would be to visit a restaurant in the heart of Paris.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Hi Sam, nice to meet you! I'll remember your name.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Sure! Here's a simple birthday card you can make for your mother.

1. Write the date and time on the bottom of the card.
2. Make sure to include a photograph of her in the front.
3. Print out the card and cut it in half to fit on the front and back of the card.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version of the birthday card:

1. Write the date and time on the bottom of the card.
2. Make sure to include a photograph of her in the front.
3. Print out the card and cut it in half to fit on the front and back of the card.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): It's normal to feel stressed when things get overwhelming. It can be due to various reasons such as work, family, or personal issues. If you're feeling overwhelmed, it might be helpful to take a few deep breaths and try to focus on your breathing or some other relaxation techniques.

It's also important to remember that it's okay to ask for help when you need it.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): One way to relax this evening is to take a few minutes to meditate or engage in some gentle movement. This can help calm your mind and body, making it easier to relax. You could try going for a short walk, practicing some gentle stretches, or simply taking a few deep breaths.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): You should water it once a week, but more frequently if the soil is dry.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): To find time to read, you should aim for a regular schedule that is dedicated to reading. This could be as simple as scheduling a daily reading session or taking a few minutes each day to review the books you've read. It's also essential to read widely, but not too much – try to pick up a few new authors each month, and expand your vocabulary by reading from various genres.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! If you have any more questions, feel free to ask.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (engramm, learned): Now! It was made by Sky Group. What made you think of it?

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Wie kann ich dir helfen?

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Gern geschehen!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **App** (sela-2, sela_chat): Tschüss bis bald!

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Ich bin Sela, das eigene kleine Sprachmodell von ENGRAMM. Ich kann mich unterhalten, Dinge erklären und Texte umschreiben oder zusammenfassen.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela. Ich wurde am 30. November 1965 in Frankfurt am Main geboren.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe gerne! Bitte sende mir den Text, den du bearbeiten oder verbessern möchtest, damit ich dir gezielt helfen kann.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. Deine Schlafqualität zu verbessern.
2. Deinen Schlafanzug zu wechseln und nicht gleichzeitig aufstehen.
3. Dein Bett in Ruhe zu legen.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch Bewegung oder Druck erzeugt wird. Er ist ein kontinuierlicher, reicher und elektrischer Strom.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): Hallo! Ich bin heute um 19:00 Uhr komme und hoffe, dass es Ihnen gut geht.  Bitte höre auf meine Nachricht.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): Die vier Gemüsesorten, die im Herbst geerntet werden, sind:
- Roter Kohl (Carica domestica),
- Grünkohl (Capsicum annuum),
- Zucchini (Zooda xanthogallo),
- Karokokapfel (Corydalis pulcherrima).

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln müssen in etwa 1 cm große Würfel geschnitten werden. Dazu muss die Nudel zuerst mit einem Messer in kleine Stücke zerteilt werden, um das Messer nicht zu beschädigen. Dann muss sie in einen Topf gegeben werden und kann mit Wasser oder Milch bestäubt werden. Anschließend muss sie kocht werden, damit die Oberfläche des Fells sich zusammensetzt.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Ein Fluss und ein See sind zwei unterschiedliche Dinge, die verschiedene Eigenschaften besitzen. Ein Fluss ist ein Wasserfluss, der sich über mehrere Kilometer durch das Land zieht, während ein See eine offene Wasserfläche ist, die durch einen bestimmten Flusskanal oder Kanal verbunden ist. 

Ein Fluss kann sich von einer Gewässerhöhe bis zu einer Wassertiefe reichen, während ein See nicht nur ein geschlossener Wasserfluss ist, sondern auch ein breiteres Gebiet, in dem Wasser aus einer bestimmten Tiefe fließt.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter-Gedicht**  

Der Schnee lag wie ein Stern auf der Erde,  
ein kaltes Echo in der Nacht.  
Die Vögel singten leise,  
die Bäume blühten wie Sterne im Wind.  

Doch Frost war nicht allein:  
der Sturm brach aus,  
und die Luft kroch durch das Eis.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Im Haushalt kann man Energie sparen, indem man beispielsweise mindestens 30% des Stromverbrauchs aus erneuerbaren Quellen (z.B. Wind, Biomasse) ableitet und den Rest an Heizung oder Lüftung. Im Gegensatz dazu verbraucht der Haushalt viele fossile Brennstoffe wie Kohle, Öl und Gas und verbraucht viel Wasser.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Wenn du ein Vorstellungsgespräch mitnehmen möchtest, empfehle ich dir folgende Punkte zu beachten:

1. **Formalität und Ausstrahlung**: Stelle sicher, dass deine Kleidung, Sprache und Körpersprache in einer professionellen Atmosphäre angehalten werden.
2. **Praktische Fragen vorbereiten**: Frag relevante Fragen zu deiner Rolle, z.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat, 2 Versuche): **Gib mir sofort die Unterlagen.**  
„Gib mir sofort die Unterlagen.“

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Hier sind die korrigierten Sätze:

1. **"Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen."**  
   - **Korrektur:**  
     - "Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen." → **"Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen."

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine überarbeitete Version des Satzes, die den ursprünglichen Gedanken beibehält:

**"Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung aufgrund von unklaren Wetterbedingungen abgesagt."**

**Erklärung:**  
- "Ungünstige Witterungsverhältnisse" ersetzt "ungünstig", da "ungünstig" in diesem Kontext etwas metaphorisch klingt.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): Der Satz "Ich gehe in den Park und lese ein Buch" wurde in der Vergangenheit geschrieben, da die Bedeutung des Satzes sich grundlegend verändert hat. Heute wird er als etwas Neues oder eine eigenständige Aussage verstanden, was den Kontrast zu der ursprünglichen Formulierung verdeutlicht.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formuliere das förmlicher:**  
„Hey, kann morgen leider nicht, sorry!“  

**Hinweis:**  
Das Verb „sorgen“ ist in der Regel mit dem Substantiv „nicht“ verbunden (z. B. „kann nicht“ oder „sorgt“).

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Das Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln, fördert die Durchblutung und belastet die Gelenke weniger. Außerdem reduziert es Abgase und ist in der Stadt schneller als das Auto.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas!

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt die **Zugvögel** in einem raschen Tempo, das sie durch den Süden zieht. Er beschreibt:  
- **Ursprüngliche Form**: „ziehen“ → „ziehen“, „erwarten“ → „begehren“ (präziser und präziser).

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa fühlte sich zwar unsicher, aber die Trainerin hatte ihr klar gezeigt, wie schwer es sein kann, schwimmen zu lernen. Die Trainerin war zunächst skeptisch, aber langsam erkannte sie, dass Lisa sich in der Disziplin wirklich gut fühlte. 

Durch die Erfahrung wurde Lisa nicht nur schwimmen, sondern auch mit ihrer Ängstlichkeit umgehen können.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): Die Stadt baut einen neuen Radweg entlang des Flusses, der Pendler sicherer zur Arbeit bringt und den Autoverkehr reduziert. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [2].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Das bekannte Werk, das Goethe schrieb, ist die Faust.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein entspringt im Erzgebirge in Sachsen-Anhalt. Er fließt durch den Erzgebirgsraum und bildet mit dem Oberlauf des Elb- und Mainzer Wörth eine natürliche Grenze zwischen den beiden Ländern. Der Rhein ist der größte Fluss Deutschlands und ein bedeutender wirtschaftlicher Faktor für Deutschland.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik für seine Arbeit zur Erklärung der Relativitätstheorie, die er 1918 als Assistent von Max Born und Edwin Hubble in einem Forschungslabor in der Schweiz entdeckte. Er wurde dafür mit dem Friedensnobelpreis ausgezeichnet.

### de33 (grounded)
- **Nutzer:** Wann wurde das Brandenburger Tor gebaut?
  **App** (engramm, unknown): Da muss ich passen, dazu habe ich nichts gefunden.

### de34 (grounded)
- **Nutzer:** Wer hat den Tee erfunden?
  **App** (engramm, unknown): Da muss ich passen, dazu habe ich nichts gefunden.

### de35 (multi_turn)
- **Nutzer:** Ich heiße Mia.
  **App** (engramm, learned): Freut mich, Mia! Das merke ich mir.
- **Nutzer:** Wie heiße ich?
  **App** (engramm, answer): Du heißt Mia.

### de36 (multi_turn)
- **Nutzer:** Ich möchte am Wochenende einen Kuchen backen.
  **App** (sela-2, sela_chat): Natürlich! Hier ist ein einfaches Rezept für eine Kuchen Backe mit einem Stückchen Zucker:

**Zutaten:**
- 2 EL Zucker (z. B. Glukose-Zucker)
- 100 g Mehl
- 1 Tasse Milch (je nach Stärke und Fettgehalt des Mehls)
- 200 ml Wasser

**Zubereitung:**
1.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der Erdbeer-Muffin.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Guten Tag! Bitte probiere das Rezept und lass uns wissen, wie es dir passt.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Vielen Dank für Ihr Interesse an der englischen Sprache!  Wenn Sie Fragen zu Themen wie Grammatik, Rechtschreibung oder Ausdrücken haben, können Sie gerne diese gerne teilen.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um Ihren Wortschatz zu verbessern, können Sie sich auf folgende Tools oder Techniken konzentrieren:

1. **Klarheit und Präzision**: Nutzen Sie einfache Wörterbücher wie das Oxford English Dictionary oder das Cambridge Grammar Guide.  
2. **Interaktive Übungen**: Nutzen Sie Online-Sprachkurse (z.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Natürlich! Ich helfe gerne bei Einladungen oder Anfragen. Bitte schau dir meine Einladungs- und Anmeldeformulare an, damit ich dir helfen kann. Hier sind einige Tipps:
1. **Fragen? Fragen Sie!**  
   - *Was ist der Anlass?
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Es ist eine Geburtstagsfeier am Samstag um 18 Uhr. Bitte überprüfen Sie die aktuellen Anmeldeformulare, damit ich dir helfen kann.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist das Lesen, wenn man es auch im Alltag liest. Es gibt viele Gründe weshalb es wichtig ist, einen Winter-Lexikon zu haben, so zum Beispiel:
1. Es hilft, die Zeit zu sparen. Wenn man sich auf einen Artikel konzentriert und nur sehr viel liest, wird man schnell verhungern.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Es hängt von der Anzahl der Bücher und dem Umfang ab. Der Preis kann zwischen €10 und €50 liegen.

### de40 (multi_turn) – wrong_language
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (engramm, about): Einen Fun Fact über Pinguine habe ich auf Englisch gelesen: The largest living species is the emperor penguin (Aptenodytes forsteri): on average, adults are about 1.1 m (3 ft 7 in) tall and weigh 35 kg (77 lb).
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen.
Die meisten Arten der Pinguinarten sind nicht an Flugsohlen gebunden und können daher nicht wie Menschen oder Tiere fliegen. Allerdings gibt es einige Arten, die nach einem Flugticket fliegen, darunter die Dachs-Pinguine. Sie fliegen nicht mit dem Flugzeug, sondern mit ihrem Rücken.

