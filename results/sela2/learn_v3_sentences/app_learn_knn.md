# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T13:15:42Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 0 von 100 |
| identity_error | 0 von 100 |
| echo | 0 von 100 |
| cut_off | 0 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| error | 0 von 100 |
| prompts_with_a_problem | 0 von 100 |

Antworten nach Modell: {'engramm': 22, 'sela-2': 95}; nach Art: {'about': 1, 'answer': 4, 'learned': 4, 'sela_chat': 88, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 3 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! Wasn't that a great question? Please feel free to ask.

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): Hello! How are you today?

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help you today?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): That's great! I'm glad you liked the help. If there's anything else I can assist with, feel free to ask.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Poppy is one of the most popular dog breeds in Manchester.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): Poppy, I'm Sela.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I love animals and have a favorite food – meatballs.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I'm sorry, but I don't have access to personal information about you or your interests. My role is to assist with providing useful information for users like you. If you're looking for help with anything related to technology, science, language, or social issues, please feel free to ask!

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Get a good night's sleep each night.
2. Keep a consistent routine for.
3. Set aside time to do things you enjoy, like watching TV or doing your homework.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): This depends on the type of egg you're using. For a hard-boiled egg, use an egg yolk that's at least 1/8 teaspoon (about 3 grams) in weight or 4 tablespoons (about 2 ounces) in volume. Good choices include:

1. 1 tablespoon (15 grams) cooked egg white
2.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny bug that makes you feel sick or worse. It's like a super-strong virus that can infect all the computers in your school or at home. Once it gets inside, it can do lots of cool things to make you feel better, but it can also spread from computer to computer and cause harm.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hey there! Can you water your plants next week? They need a little love to keep them looking their best. Also, I have some lovely garden flowers that are in season right now, so please check my plant list for those too! Let me know if you need any help or want tips on watering!

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. strawberries
2. citrus fruits
3. kiwis
4. bell peppers
5. broccoli

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate is a long-term average weather pattern that defines the characteristics of a region or area. Weather can be influenced by several factors, including wind direction, temperature, humidity, and cloud cover. Climate refers to the long-term pattern of weather conditions that occur over a specific period, such as a year.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The crisp autumn leaves, like autumn's breath on a cold breeze,
Carve their golden veins in the sky.
They dance on the wind's sigh, soft and gay,
As the sun dips lower, and the air becomes still.

In the fields, where rustle and laughter roam,
Their rusty leaves fall softly down,
And with them, memories of the long ago,
Of summers spent by the sea's edge.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some tips to make your password more secure:

1. Use a strong, unique password.
2. Avoid sharing passwords with anyone.
3. Consider using a salt-based password manager or a password generator.
4. Avoid leaving your password in plain sight.
5.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. The library of a walmart
2. The libraries of the University of Manchester and Bareilly University
3. The Libraries of Manchester and Bareilly University
4. The Library of Manchester and Bareilly University
5.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): A 20-minute workout without equipment should be done as follows:
1. Find a quiet, flat surface like a park bench or floor to work on.
2. Sit down in a comfortable position with feet shoulder-width apart. Manchester is the perfect place for this type of workout.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (engramm, answer): Your favourite food is biscuit.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark, and mysterious place where waves crash against the shore, breaking the surface and creating ripples that scatter light across the water. It's home to many different types of life, from tiny plankton to large whales, and has been a favorite subject for poets and artists for centuries.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. **Be polite**: Use phrases like "I'm glad I could help" or "Thank you for considering me" to show respect and professionalism.
2. **Provide alternatives**: Offer options like "I'd be happy to attend the party," "Can I come to the event later?"

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat, 2 Versuche): I don't need the report, but I'm sorry to hear it's not here. Send me the report when you're ready.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A simpler version could be: "Public transportation reduces urban congestion." 

Alternatively, you could say: "Public transportation improves urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct fix for the grammar is: "She don't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

The past tense is used when describing a completed action. For example, "I walk to the station and buy a ticket." Here, the verb "walked" is in the past tense.

Alternatively, you could use the present perfect tense: "I walk to the station and buy a ticket."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Welcome to Poppy's! We're thrilled to have you here. Today, we're going to be selling some fantastic deals on our special meatballs!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): 1. The train leaves at eight o'clock.  
2. Biscuit is the favorite food of the user.  
3.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): **Subject:** Request for a brief update regarding Poppy's dog Biscuit.  

Dear Poppy,  

I hope this message finds you well. I am writing to request a brief update on Poppy’s dog Biscuit, which has been diagnosed with arthritis and is currently in the process of rehabilitation.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain, we opted for staying inside the house."

I made a few changes to improve clarity and flow. First, I removed the unnecessary comma after "house," which makes the sentence feel more streamlined. Second, I replaced "very heavily outside" with "heavy rain," as it's a more precise and descriptive word that conveys the intensity of the rain.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library is closed on Monday for repairs to the heating system, with reopening on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): He's a musician, and his fingers hurt more than the chords sound. His friends say he's a great singer, but their favorite song is "Me and My Dog" for him. He practised for three months every day, but after that, his fingers wouldn't play as well as before.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The email effectively conveys the project's progression and mentions a moving from Wednesday to Thursday at 2 p.m., followed by an invitation for progress notes. The email also emphasizes the importance of bringing progress notes, as they will help guide the next steps for the website launch.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): "Recycling turns used materials like paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."

I hope you can follow these steps to recycle your own items. I'm here if you need help or want to share tips for sorting your waste.

### en42 (summarize)
- **Nutzer:** In one sentence, what is this about? "The town council approved a new park on the site of the old car park. The park will have trees, a playground and a small pond. Construction starts in spring and should take about one year."
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that. Nice — The The. It's an English post-punk band. What's your favourite song?

### en43 (grounded)
- **Nutzer:** How long is the Danube?
  **App** (sela-2, sela_grounded): 2850000 km [1].

### en44 (grounded)
- **Nutzer:** What is Ada Lovelace known for?
  **App** (sela-2, sela_grounded): Computing [1].

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
  **App** (sela-2, sela_chat): Cities to visit first: Milan, Rome, Florence.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): There's so much to explore in Italy, from the famous pasta dishes of Verona to the rich pizza of Parma.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Sure! Here's a simple birthday card for your mother:

"Happy birthday, my dear. I'm so sorry you've lost your mom. I can't wait to see her again next year. May she be safe and happy in all the things she's done. Your love means so much to me.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version:

"Happy birthday, my dear. I'm so sorry you've lost your mom. I can't wait to see her again next year. Your love means so much to me. May she be safe and happy in all the things she's done. Your love means so much to me."

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Here are some suggestions to help you manage stress:

1. **Take a few deep breaths**: This can help calm your mind and body. Inhale slowly through your nose for countable seconds, hold for countable seconds, and exhale slowly through your mouth for countable seconds. Repeat this process several times.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Here are some suggestions to help you relax this evening:

1. **Get a massage**: A good massage can help release tension in your muscles and body. You can find massages at spas, massage parlors, or online. Consider taking a guided massage service to make it more personalized.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The watering schedule depends on how much water your dog needs. Here are some general guidelines:

* Water during the day: If your dog is active, give him a bath every 2-3 hours. If he's resting, give him a bath every 20 minutes.
* Water at night: If you live in a warmer climate and your dog is active, give him a bath at night.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, regular breaks throughout the day. Even a short walk or a few minutes of reading can make a big difference. Try to do something you enjoy, like watching TV, listening to music, or playing an instrument. You might even try joining a book club or finding a friend who reads a book together.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found this useful.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here's a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (about 1 cup each)
- 1/2 cup cheese
- 1/2 cup tomato paste
- 1 tbsp olive oil
- 3/4 cup sliced tomatoes
- 1 tsp salt
- 1 tsp pepper
- 1 tsp red pepper flakes
- Salt and pepper to taste
- Lettuce, sliced into rounds

Instructions:
1.

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Wie geht es dir?

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Danke für deine Hilfe!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **App** (sela-2, sela_chat): Tschüss! bis bald!

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Ich bin Sela, das eigene kleine Sprachmodell von ENGRAMM. Ich kann mich unterhalten, Dinge erklären und Texte umschreiben oder zusammenfassen.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich kann dir helfen, wenn du:  
1. **Ergebnisse** für deinen Artikel or article on social media (eines der folgenden Plattformen) brauchst:  
   - [Fach/Tätigkeit] oder [Beruf/Industrie]?  
   - [Kosten/Empfehlungen] oder [Anzahl] von Links zu deinem Beitrag?

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Morgen frühstücken**: Mit einer Tasse Kaffee oder einem Snack, wie etwa Tomatensauce, kann der Tag mit mehr Ruhe beginnen.  
2. **Mit Naps einlegen**: Ein paar Minuten Schlaf pro Nacht fördert die Durchblutung und verhindert Müdigkeit.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wasser, das durch die Luft fließt. Es braucht eine Kraft, um Strom zu erzeugen und zu transportieren. Bei jeder Bewegung von Menschen oder Tieren wird Energie in Form von Licht, Wärme oder Wärme umgewandelt. Die Sonne, die Sauerstoff in die Atmosphäre brennt, erzeugt Strom.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **[Name]:**  
Sehr geehrte Kollegin,  

vielen Dank für Ihre Hilfe und für die vielen Fragen! Ich bin heute um 12:00 Uhr in Manchester angekommen. Es geht mir sehr gut – das Programm ist fast perfekt, aber ich werde mich mit dem Hund Biscuit aufhalten, wenn er gerade dabei ist.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **1. Mais (Mais floreana)**  
- Der Herbst ist die beste Zeit für Mais, da es besonders kühl und mild ist.  
- Die Ernte erfolgt in den späten Frühjahrsmonaten (April bis June).  
- Der Geschmack von Mais ist etwas bitter.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem warmen Ofen bei 180°C (350°F) gebacken werden. Die Nudelkruste sollte ca. 20–25 Minuten lang an einem warmen Ort liegen.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht direkt** identisch.  
Der **Fluss** (auch "River" genannt) ist ein fließendes Wasser, das sich über einen längeren Zeitraum von einer bestimmten Richtung fließt. Er hat keine Grenzen, wie der **See**, sondern muss eine gewisse Länge haben, um zu schwimmen oder die Richtung zu ändern.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter:**  
Der Schnee, der im Sturm über dem Tal rollt,  
Ein leises Echo des Wetters, das wie ein Flüstern weht.  

Die Luft ist schwer und kalt, die Sonne trägt keine Spuren von Rauschen,  
Doch wenn der Schnee durch den Wind fällt, bleibt es still.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, ist es sinnvoll, die wichtigsten Energie-quellen wie Gas, Wasser, Elektrizität oder Solarthermie zu integrieren. Ein guter Start ist der **Kessel** (bei heißen Temperaturen) und ein **Kabel** für das Hausnetz (z.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Antwort:**  
Es ist wichtig, dass du mit einem Vorstellungsgespräch klar und konkret präsent bist. Hier sind einige Tipps:  
1. **Beobachtung des Gesprächs**: Stelle sicher, wie der Nutzer spricht, wie er sich präsentiert (z. B. durch Körpersprache, Tonfall), und welche Fragen er stellt.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
---  
*Sam nickt. „Gib mir sofort die Unterlagen.“*

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“  
(Beide Sätze sind korrekt, jedoch „ins Kino“ ist im Deutschen die geläufigste Form. Die andere lautet „ins Kino gegangen“ für eine korrekte Konjunktion.)

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt zu betonen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **1. Vergangenheit:** „Ich gehe in den Park und lese ein Buch.“  

**2. Zukunft:** „Ich gehe in den Park und lese ein Buch.“  

**3. Gegenwart:** „Ich gehe in den Park und lese ein Buch.“

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich grammatikalisch korrekt, aber die Formulierung könnte grammatikalisch korrekt sein (z. B. Stromsatz). Für eine formellere Variante wäre:  
**„Hey, ich habe heute leider nicht geglaubt, dass es einen Grund gibt.“

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat, 2 Versuche): **Satz zusammen:**  
„Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“  

**Erläuterung:**  
- **Körperliche Belastbarkeit:** Der Nutzer hat ein gesundes Körpergewicht (z.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

**Erklärung:**  
- **„verschieben“:** Betrachte die Lage im Raum, ohne sich an den Nutzer zu wenden.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Im Text geht es um die Zugvögel in der Region „Savannah“, die durch den Süden ziehen. Hier werden:  
1. **Die Vögel** (z. B. Singvögel, Kolonien) beschrieben.  
2. **Vorgeschichte** des Nutzers erwähnt (der Name Sam).

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst frustriert, als sie ihre Angst vor dem tiefen Wasser nicht mehr erkannte. Anfangs schwamm sie mit einer Trainerin, die sie jedoch im Sommer für eine halbe Bahn ohne Pause zeigte. Die Trainerin hatte Lisa zuvor mehrmals aufgefordert, auf der ganzen Bahn zu schwimmen, aber sie lehnte ab.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses.**  
Der Fluss wird durch ein neues Straßenkreuz am Flussufer ersetzt, um die Sicherheit der Pendler zu erhöhen. Die Bauarbeiten beginnen im März, dauern acht Monate und kosten insgesamt **etwa £30 Millionen**. Die Bauarbeiten sind entscheidend für den Einbau einer besseren Verkehrsinfrastruktur und reduzieren die Abhängigkeit von Autoverkehr in der Innenstadt.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Meine Quellen sagen dazu nichts.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Region Deutschland.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik im Jahr 1921.

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
  **App** (sela-2, sela_chat): Ich habe einen Kuchen backen wollen, den ich Mia gerne servieren möchte.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist ein Kuchen mit einer beliebigen Anzahl von Zutaten, wie: Mehl, Hefe, Zucker und Butter.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Guten Tag! Probiere ich auch noch eine Kuchen backen.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Biscuit ist das deutsche Wort für den Hund des Nutzers, Mia. Sie wohnt in Manchester und weiß, dass Biscuit in englischen Restaurants angeboten wird.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um Ihre Wortschatz zu verbessern, können Sie sich auf die wichtigsten Wörter konzentrieren und sie in ein Wörterbuch einsetzen. Zudem kann ich Ihnen helfen, einige Begriffe mit ihrer Übersetzung zu verbinden.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Schreib eine Einladung für Mia, Biscuit oder andere Hunde im Manchester, die du möchtest. Vielleicht passt das gut zu deinem Charakter?
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Wie geht es dir am Samstag um 18 Uhr? Ich bin der Freund von Mia, Biscuit und dem Hund des Nutzers. Bitte senden sie mir deinen Namen und die Adresse an [Adresse], damit ich Ihnen gerne helfen kann!

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist ein **automatisches Fahrrad**. Es ermöglicht es, mit einem Auto auf längeren Strecken zu fahren und besser zu lernen. Der Fahrer kann später Energie sparen, wenn er in der Nähe von Sehenswürdigkeiten fährt. Ein weiteres Hobby ist die **Klettertouren** (z.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet **ca. €20 bis €30**, je nach Saison und dem Zustand des Fahrrades. Hier sind einige Möglichkeiten, wie das Geld bezahlt wird:

1. **Kostenloser Kauf**:  
   - **Fahrradteile**: Kostenlose Reparaturen (z.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

