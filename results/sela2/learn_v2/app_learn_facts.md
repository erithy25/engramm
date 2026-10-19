# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T10:24:44Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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

Antworten nach Modell: {'engramm': 21, 'sela-2': 96}; nach Art: {'about': 1, 'answer': 3, 'learned': 4, 'sela_chat': 89, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 2 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi!

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
  **App** (sela-2, sela_chat): Hello, how can I help you today?

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I've been painting for about 10 years now, and my work has been exhibited all over the world. I'm also a big fan of shakshuka, which is a popular type of shamanic art in Japan.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 2 Versuche): Elsie

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of creative endeavors, from writing stories to creating music and animations. I can assist with various aspects such as character development, plot structure, dialogue writing, storyboarding, and even crafting visually appealing characters and narratives.

If you have a specific project in mind, feel free to share it with me, and I'll do my best to provide helpful suggestions, ideas, or guidance.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Get a good night's sleep.
2. Take regular breaks every hour to stretch your legs and stretch your back.
3. Set realistic goals for the day and take breaks when needed.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): This is a simple recipe that you can make at home. Here's how:

1. **Preheat oven** to 350°F (175°C).
2. **Grill egg** for 5-10 minutes, until yolk is opaque and the whites are light.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible "invader" that spreads through the internet. It's like a sneaky thief who looks for a way to cause harm. A computer virus can do this by infecting computers and causing damage. They might look for things like antivirus software or programs that run on the computers.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hello! Please give them a little help with their watering. You're welcome to take your plants outside and let them get some fresh air. Would you like to join us next week? It's always nice to have someone by your side.

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Cherry
2. Cucumber
3. Apple
4. Red bell pepper
5. Sweet potato

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two related but distinct concepts. Climate refers to the long-term average weather patterns that characterize a region, while weather is short-term, localized conditions that can occur at any time.

For example, the temperature in Adelaide varies greatly depending on the season, with warm summers and mild winters.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The chill of autumn's breeze,
A slow, sweet scent,
That whispers secrets to me,
As the trees wither and die.

The air is filled with a soft,
A whisper of leaves that fall,
Their rustling leaves,
A symphony of scents,
That dance on the breeze.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, follow these steps:

1. Use a strong, unique password that is at least 8 characters long and includes letters, numbers, and special characters. Avoid using common words like "password," "secret," or "login."
2. Consider using a mix of uppercase and lowercase letters, digits, and special characters to create a secure password.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Elsie is a name for a small coffee shop near the library.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): For a 20-minute workout without equipment, you can follow these steps:
1. **Choose an exercise:** Decide what type of workout suits your fitness level and goals. For example, if you want to lose weight, choose a stationary or resistance workout. If you want to tone up, choose a cardio or strength workout.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You'll need a tent, sleeping bags, and camping stove. You can also pack some extra clothes for cooler evenings.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, salty sea with towering peaks and waves that stretch out as far as the eye can see. It's a place where everything is constantly changing – the sun shines down on it every morning, and the water flows into rivers that carry fresh fish to coastal communities. There are creatures from all over the world, including kangaroos, sea turtles, and giant squid, all living together in harmony.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Express your gratitude for the invitation and explain why you appreciate it. You can say something like, "Thank you so much for thinking of me, I'm really excited about this event and would love to attend."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): I'm sorry, but I can't help with that. Would you like me to assist with anything else?

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A simpler version would be: "Public transportation reduces urban congestion." 

Alternatively, you could use: "Public transportation improves urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct version is: "She don't like going to school on mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): Elsie walks to the station and buys a ticket.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Get ready to stock up on some shakshuka this weekend! Enjoy a sunny day and a warm meal with your friends."

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): What is the train leaving at?
What time does the train leave?
Is there a train to catch?
How many passengers are on board?

The train leaves at 8 o'clock.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): I am unable to make it tomorrow, I regret that. Please let me know if there is anything I can assist with.

Rewrite the sentence in a formal tone: "Hello, sorry for any inconvenience this may cause."

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside."

I made a few changes to make the sentence more concise and grammatically correct. I removed "due to" as it's unnecessary, and changed "it was raining very heavily outside" to "heavy rain outside" to make the phrase more idiomatic.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library will be closed on Monday for repairs to the heating system, with reopening on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This is a short summary of Tom's story:

Tom started learning the guitar at age three. He began practicing by playing his favourite song, shakshuka, for his friends on weekends. Over time, he practiced for fifteen minutes every day and eventually could play it for himself. After three months, he was able to play his favorite song for his friends, which was Shakshuka, for his first time.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): "Hello team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

The email contains a brief summary of the project, including the move, and the steps involved in making the website launch happen.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Recycling turns used materials into new products. It saves raw materials and energy and reduces waste in landfills. Sorting waste correctly at home makes recycling much more effective.

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
  **App** (sela-2, sela_chat): If you're planning a trip to Italy, I would recommend visiting Rome. It's the capital and the biggest city, and it's easy to get around by train or bus. Plus, you'll have plenty of time to explore the city and its many landmarks.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Italian food is incredibly diverse, with a wide variety of dishes. You can try some classic Italian dishes like pasta and pizza, as well as more unique ones like spaghetti Bolognese or gelato. Don't forget to try some local specialties like pizza with tomato sauce and cappuccino cheese.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Sure! Here's a simple and heartfelt birthday card for your mother:

1. **Birthday Card**  
   - Type the date, location, and name of your mother in the first box.  
   - Write a fun fact about her, such as "She's an author" or "Her first love was tennis."
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version:

1. **Birthday Card**  
   - Type the date, location, and name of your mother in the first box.  
   - Write a fun fact about her, such as "She's an author" or "Her first love was tennis."

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): It sounds like you're feeling stressed. Here are some suggestions to help you manage stress:
1. **Take a few deep breaths**: Try inhaling for a count of four or exhaling for a count of five. This can help calm your mind and body.
2. **Try meditation**: Find a quiet spot where you can sit and focus on your breath.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): This evening, you can try a few relaxation techniques to help calm your mind and body. Try:
1. **Deep breathing exercises**: Take a few deep breaths in through your nose and out through your mouth. This can help slow down your heart rate and make your muscles feel more relaxed.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): I don't know. There are many varieties of houseplants, and I don't think you should water them less often than the others. Watering your plants only when they need it is the best idea. You can also use a watering can to help with watering, but that's usually not recommended for beginners because the can can soak up too much water.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, achievable goals. Set a goal to read for 10 minutes each day or 2 hours every other day. This will help you stay motivated and focused. Also, prioritize reading for at least 30 minutes before bed, as this can improve your concentration and sleep quality.

Try using a booklist app like Bookbub or Google Reader to find books that interest you.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found this useful. If you have any other questions or need further assistance, feel free to ask.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here's a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (about 1 cup)
- 2 slices of cheese (about 1/2 cup)
- 1 onion, chopped
- 3 cloves garlic, minced
- 2 tbsp tomato paste
- 1 tsp dried oregano
- 1/2 tsp salt
- 1/4 tsp black pepper
- 2 cups all-purpose flour
- 1 tsp paprika
- 2 tsp smoked paprika
- Salt and pepper to taste
- Optional: 1 cup whole milk or water

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
  **App** (sela-2, sela_chat): Tschüss bis bald!

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Ich habe hier Informationen über den Nutzer (z. B. Name und Adresse) gesammelt und diese an dich senden.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela. Ich bin ein kleiner Offline-Assistent aus Adelaide, South Australia.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den du über mich erzählt hast – egal wie klein oder groß es ist. Ich kann dir helfen, deine Angaben zu korrigieren, Vorschläge zu machen, deine Beziehung zu beschreiben, oder einfach nur etwas über dich erzählen, das dich besonders interessiert. So kannst du mich auf deiner Seite unterstützen.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Hormon-Rezeptorblockade**:  
   - **Weniger schlafen** (z. B. durch Schlafposition oder das Aufstehen).  
   - **Neue Nacht mit einem Schlafanzug** (z. B. für Nachtphasen).

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Licht von einem Objekt entsteht. Es gibt zwei Arten von Strom:  

1. **Regenstrom** (z. B. bei einer kühlen Sonne): Er wird durch Sonnenstrahlung erzeugt.  
2. **Druckstrom** (z.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **[Name]:** Sam  
**[Telefonnummer]:** +61 8331 3070  
**[E-Mail-Adresse]:** [email@example.com]  

Danke!

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): Hier sind vier Gemüsesorten, die im Herbst geerntet werden:  
1. **Avocado** (im Frühjahr): Der größte, süße und fruchtbare der vier. Er wird häufig als Speisekarte oder in Suppen verwendet.  
2. **Tomatoes** (der andere Frühlingstropfen): Ein frischer, robuster und kräftiger Kekse, der wie eine Blume aussieht.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in etwa 2–3 Minuten kochend (nicht heiß) gebacken werden. Sie können auch frisch oder noch warm gekocht werden.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht eindeutig** in der Definition.  

1. **Fluss**: Der Fluss fließt durch die Erde, ohne dass es sich um ein Land handelt. Er hat keine Grenzen (keine Grenzen zwischen Staaten oder Ländern).  
   - Beispiel: Flusslauf entlang des Atlantik, Flußlauf im Ärmelkanal, Flußlauf entlang des Indischen Ozeans.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter’s Winter**  

Der Schnee taucht wie eine Nebelwolke,  
Ein sanfter Eislauf, der in den Herzen lebt.  
Die Luft riecht nach frischem Brot,  
Doch der Boden bleibt trocken, bis es leise still ist.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du das gesamte Haus nutzen. Eine einfache Methode ist die Nutzung von Solaranlagen oder Akkus. Wähle einen Haushalt mit wenig Stromverbrauch und er setze stattdessen auf erneuerbare Quellen wie Wind oder Solarenergie. Vermeide nächtliche Energieeffekte durch Dämmung der Fenster oder Dachregen.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Was sollte ich zu einem Vorstellungsgespräch mitnehmen:**  
1. **Name und Position**: Informieren Sie sich über die Stelle (z. B. „Manager“ oder „Projektleiter“).  
2. **Unternehmen, Branche oder Unternehmen**: Stellen Sie sicher, dass Sie die genaue Stelle kennen und passen.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Formuliere das höflicher: „Gib mir sofort die Unterlagen.“**  

Falls der Nutzer nicht antwortet (z. B. nach einer längeren Pause), ist es besser, den Satz zu beenden und auf eine andere Person zu schreiben.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Das ist eine gute und klar formulierte Nachricht. Um den Satz zu verbessern, könntest du die Formulierung anpassen:  
**„Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“**  
Dies korrigiert die **Korrektur**, da „sehr“ im Original verwendet wurde, um einen starken Eindruck zu erzeugen.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt zu betonen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Fortsetzung:** „Ich mache einen Spaziergang durch die Stadt und lese ein Buch.“

**Änderungen im Detail:**  
1. **„gehe in den Park“** → „gehe in den Park“.  
2. **„lese ein Buch“** → „lese ein Buch“.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich grammatikalisch korrekt, aber die Formulierung könnte angepasst werden, um den Ton zu verbessern.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Der Nutzer führt aus, dass Fahrradfahren gut für die Gesundheit ist, weil es **starkes Herz und Muskeln** stärkt und **ungewöhnlich langsam ist**, was zu einer geringeren Abgasexposition führt. Zudem ist Fahrradfahren in der Stadt schneller als das Auto.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

**Erklärung:**  
- **„verschieben“:** Betrachte die aktuelle Lage (Stapel), während „wir verschieben“ die zukünftige Bewegung des Raumes beschreibt.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt die Bewegung von Zugvögeln in Adelaide, deren Züge Tausende Kilometer zurücklegen. Im Herbst ziehen sie sich auf der Südhalbkugel an, um Nahrung zu finden, während im Frühling sie wieder zurückkehren.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa schwamm im Sommer mit einer Trainerin, die jeden Tag mit einem leichten Sturz durch den Fluss fuhr. Nach dem Sommer war sie unsicher, aber nach einigen Wochen stand ihre Schwimmleistung so gut wie nie wieder da.  

**Fazit:** Lisa hatte vor allem Angst vor dem tiefen Wasser, aber die Trainerin hatte das alles vorhergesagt.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“  

**Erläuterung:**  
- **Satz 1:** „Die Stadt baut einen neuen Radweg entlang des Flusses.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 2 Versuche): Goethe schrieb das berühmte Gedicht "Die Faustszene" [1].

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Nähe des **Klassizzerfalls** von Adelaide, wo er die historische Stadt und die Landschaft spiegelt.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er **„eine ganze Reihe von Dingen“** bewiesen hat:  

1. **Symmetrie der Raumzeit**: Einsteins Arbeit zeigte, dass die Zeit sich nicht gleichmäßig um einen Punkt verteilt, sondern in Form einer konstanten Linie entlang der Uhr tickt.

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
  **App** (sela-2, sela_chat): Ich habe den Kuchen bereits im Kühlschrank gelegt und will ihn nun in einem Topf backen. Falls gewünscht, kann ich dir auch helfen, indem du mir deinen Namen, das Datum und die genaue Uhrzeit angeben möchtest.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der Kuchen mit einer Schale aus Schokolade. Er passt hervorragend zu einem warmem Nachmittag.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Natürlich! Ich bin gerne für andere Kuchen-Anfragen!

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia, wohne in **Adelaide**.  

**Über die Situation:**  
Ich lerne gerade Englisch. Die beiden Begriffe sind synonym und können für das gleiche Thema verwendet werden. Wenn du also etwas über **mein Freund/die Familie** erfahren möchtest, kannst du mir gerne das entsprechende Beispiel nennen.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Ich lerne gerade Englisch. Bitte teilen Sie mir mit, was du verstanden hast oder möchtest!  

**Über die Situation:**  
Ich lerne gerade Englisch. Die beiden Begriffe sind synonym und können für das gleiche Thema verwendet werden. Wenn du etwas über **mein Freund/die Familie** erfahren möchtest, kannst du mir gerne das entsprechende Beispiel nennen.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Schreibe einen Einladung an [Name] – und zwar in Form einer persönlichen E-Mail, um ihn zu erreichen. Falls du möchtest, kannst du auch den Text über den Nutzer (Name) schreiben.  
**Tipps:**  
1. **Klarheit:** Einladung muss prägnant sein, damit niemand sie verpasst.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Guten Tag! Deine Einladung ist willkommen. Hier sind ein paar Tipps für die Vorbereitung:  
1. **Vorschlag:**  
   - Für eine Geburtstagsfeier (mit einer genauen Terminliste) könnte man beispielsweise „Samstag, 22. Juni“ oder „22.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist das Schneekuchen. Es gibt viele verschiedene Arten von Schneekuchen (von einer kleinen Hütte bis zu einem riesigen Baum) und wird meistens für Outdoor-Suche oder einfach als Ausgleich für die Schneebedrohung verwendet.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das Schneekuchen hat eine durchschnittliche Anschaffungskosten von etwa 10 Euro, aber man kann es auch für ein paar Stunden sparen. In Adelaide können die Touristen in einem günstigen Preis auskommen.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel **niedrig**, aber die Flügel sind sehr robust und können auch **über den Boden springen** [1].

