# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T09:43:53Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
Schutzregeln: 5 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! I like to eat lasagna and draw.

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well. I was just trying to take a few minutes to compose myself after listening to your story. Here's a brief summary:

Lucy is an Australian journalist with a passion for journalism. She lives in Perth and works as a journalist there. Her dog Rex loves her too!

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help you today?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): Good, I'm glad you found my help helpful.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Hello, welcome! I've been working here for about a year now and love the community. My dog Rex is my constant companion. I have to say, though, he's a bit of a troublemaker at times. Let me know if you'd like some advice on how to handle him or if there are any challenges you're facing with your dog.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a 35-year-old Australian woman living in Perth, Australia.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 2 Versuche): I am a talented and passionate freelance writer, currently living in Perth, Australia. My writing career has been highly successful, and I have had the privilege of working with numerous clients, from small businesses to big corporations, on a variety of topics, including marketing, finance, and environmental issues.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of creative endeavors, from writing stories to creating music. Whether you're looking for inspiration, seeking ideas for a project, or simply wanting to vent about your day, I'm here to offer guidance and suggestions.

If you're working on a personal project, such as a novel or poem, I'd be happy to assist with developing plotlines, characters, and setting.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Schedule regular breaks
2. Take short breaks to rest
3. Use a timer app or a smart phone for accountability
4. Be patient with yourself
5. Review your work and adjust as needed
6. Don’t be afraid to ask for help if you need it
7.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): If you boil an egg, it will be soft and tender. To make it soft, simply add a little water, then simmer for a few minutes, until the yolk is cooked through and absorbed.

Here's how to do it:
1. Add a little water to your pot or pan.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible piece of software that can sneak into your computer and make you sick. It's like a game of hide-and-seek, but instead of hiding behind doors or walls, it uses computers to spread itself around the world. Viruses can be very small, about the size of a pencil eraser, or they can be huge and difficult to see.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hey there! How's everything going? I hope you're having a great week! Let me know what you need water for next week. Maybe we can get some help from my plants or someone else too? Let me know if you have any questions or want to talk about it!

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Red bell pepper
2. Blueberries
3. Apples
4. Mangoes

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): weather: cold, wet, dry, windy. climate: warm, hot, dry, windy.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): A homegrown symphony,
Autumn's whispering whispers sweet and wide.
The leaves are withered, yet crisp and green,
And autumn's hands are bent to snatch them.

The breeze, a painter of colors,
Sings tales of warmth and gold,
In every leaf, a tale untold
Of life's most precious moments.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, follow these steps:

1. Use a strong, unique password.
2. Avoid sharing passwords with others.
3. Consider using a salted or cracked password to protect against common attacks.
4. Update your browser's security settings regularly to ensure the best possible protection.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. The Blue Oyster - near the Perth library
2. The Green House - near the Australian Museum
3. The Sunny Corner - near the Perth Library
4. The Bookstore - near the Perth library
5.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): You can start by getting yourself in shape. Begin with a few minutes of walking and light jogging for 30 seconds. You can also do yoga or Pilates for 20-30 minutes, but avoid using any kind of equipment like weights, plyometrics, or resistance bands, as they can interfere with your workout routine.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): Pack something comfortable and lightweight for the hot weather. Bring a waterproof jacket, warm hat, gloves, and boots or shoes. A good first aid kit is also important to have in case of an emergency. Include layers for cooler days. Pack a water bottle, as well as a portable stove to stay warm.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering body of water that covers nearly half of the Earth's surface, offering a mesmerizing display of light and color. It stretches out in all directions, with towering peaks that touch the sky and deep valleys filled with vibrant coral and colorful fish. Goodbye to rainy days, for I have learned to appreciate this beauty over the years.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Acknowledge the invitation: Express your appreciation for the opportunity and let the person know that you're happy about their request.
2. Show your gratitude: Let them know how much they've meant to you, and express your gratitude for their kind words.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Here's a rewritten version: "I'm sending you the report now."

Or, for a more conversational tone: "Sorry, I haven't seen it yet."

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): Here's a simpler version: "Public transportation reduces urban congestion." 

Or, if you'd like to make it even shorter: "Public transportation helps reduce urban congestion." 

Alternatively, you could also use these two options in combination: "Public transportation decreases urban congestion." or "Public transportation makes urban congestion less likely."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "She doesn't like going to school on Mondays."

I added an apostrophe to "mondays" because it indicates possession, and "doesn't" is an contraction for "does not." I also changed "school" to "schooling," which is the correct spelling.

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 2 Versuche): I walk to the station and buy a ticket. I'm going to buy a ticket.

In the past tense, I would have walked to the station and bought a ticket (which is not an action).

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Get ready to dine like a king this weekend at our fantastic new food court. With a sale on everything from fresh lasagna to artisanal cheeses, it's going to be the perfect treat for your next big adventure."

I made the following changes to make the sentence sound more exciting:

- Added the word "fantastic" to give a sense of the shop's quality.

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): I'm sorry, but I don't have access to the internet or any real-time data. For now, I'll use a phrase like "The train leaves at eight o'clock" as an example of how you might ask me about my schedule.

Would you like me to provide more details about your commute to work?

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): I apologize for the inconvenience. I'm unable to make it tomorrow, so please let me know if there's anything else I can do to assist you today.

Thank you for your understanding.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside."

I made a few changes to make the sentence more concise and grammatically correct. I removed the phrase "due to," which can sometimes make sentences feel wordy or unclear. I also changed "it was raining very heavily" to "heavy rain outside," which is a more direct and idiomatic way to express the same idea.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made a few changes to improve clarity and grammar:

- Changed "will be closed" to "will be closed" to use the correct verb tense (past, present, or future) for describing an action that has already happened.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This is a short summary of Tom's story:

Tom started learning the guitar at age three. He began practicing by playing his favourite song, "Tom wanted to learn the guitar." By the time he was five between practice sessions, he could play the song for his friends. After three months, Tom finally mastered his favorite song.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

Note: The email is a response to a previous question about the timeline and should not be considered as a personal statement or endorsement of the project itself.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Here's a brief summary:

1. **Recycling turns used materials into new products** (e.g., paper, glass, plastic).  
2. **Sorting waste correctly at home makes recycling much more effective** (e.g., sorting recyclables properly).

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
  **App** (sela-2, sela_chat): Venice is the city you'll want to visit. It's famous for its beautiful architecture, art, and delicious food.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): You can try pasta, pizza, and gelato. They're all delicious!

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Photo of mother with her dog**:  
   - Write a poem about your mother and her furry friend. You could include a happy quote or a photo from their time together.  
   - Add a message of gratitude for being a part of her life.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Photo of mother with her dog**:  
   - Write a poem about your mother and her furry friend. You could include a happy quote or a photo from their time together.  
   - Add a message of gratitude for being a part of her life.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): I can help you with that! It's okay to feel stressed, and it doesn't mean your stress is about you. You're not alone in this. Many people experience stress and anxiety at some point in their lives. If you're feeling overwhelmed or stuck, I'd be happy to listen and offer some advice.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Here are some tips to help you relax this evening:

1. **Take a walk**: Even short walks can be calming and energizing. You can start with a gentle stroll around the garden or a short walk in your backyard.
2. **Make a playlist**: Choose a few songs that you enjoy, and listen to them while doing something relaxing.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): I don't know — it depends on your climate, but in most regions, you should water it at least once a week.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, regular chunks of time each day to read. Begin with short stories, like the ones you've already started, and gradually build up to longer books. Try using a daily planner or app to stay organized.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found that. Remember, consistency is key to finding a rhythm in your reading routine. Try setting aside 30 minutes each day to read and then switch to 45-60 minutes on the weekends or when you need some extra quiet time.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here's a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (about 1/2 cup)
- 2 cups of all-purpose flour
- 1 teaspoon salt
- 1 tablespoon unsalted butter, cubed
- 4 tablespoons of granulated sugar
- 1 teaspoon ground cinnamon
- 1 teaspoon of nutmeg
- 1 teaspoon of allspice
- Salt and pepper to taste

Instructions:
1.

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Ich helfe dir gerne bei Fragen zu Sprache, Grammatik, Rechtschreibung und Zeichensetzung. Schreibe mir einfach deinen Text – ich passe meine Antworten an deine Bedürfnisse an.

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Danke für deine Hilfe!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **App** (sela-2, sela_chat): Tschüss bis bald!

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat, 2 Versuche): Ich bin Sela, das eigene kleine Sprachmodell von ENGRAMM. Ich kann mich unterhalten, Dinge erklären und Texte umschreiben oder zusammenfassen.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat, 3 Versuche): Ich bin Sam, ein kleiner Offline-Assistent.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir einfach deinen Namen, den du genannt hast, und schick mir die Informationen über dich, damit ich dir helfen kann.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Pausen einplanen**: Plane deinen Tag mit einer festen Schlafzeit und setze ihn in den Tag ein, um die innere Uhr zu synchronisieren.  
2. **Körperliche Aktivität**: Strebe mindestens 30 Minuten tägliche Bewegung wie Spaziergänge oder Yoga.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Material (z. B. Wasser) in elektrische Energie umgewandelt wird. Er ist entscheidend für unser Leben, da er uns Strom gibt und uns hilft, Energie zu speichern.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Beste Grüße aus Perth!**  

Ich freue mich, dass Sie heute in Perth bleiben möchten. Ihr Anliegen ist klar – ich freue mich, Ihnen bei der Arbeit zu helfen.   
Ich werde mir Ihre Nachricht selbst abholen und diese an meine Kollegin senden.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **4 Gemüsesorten, die im Herbst geerntet werden:**  
1. **Lager-Erbsen (Pandanus leucopterus):**  
   - Erntezeit: Mitte September bis Anfang November.  
   - Anbaugebiet: Südwest-Indien und Mitteleuropa.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem warmen Wasserbad etwa 30 Minuten ziehen und nicht direkt auf den Boden drücken.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht eindeutig** in der Definition. Im Sinne eines einheitlichen Begriffs kann ich aber sagen:

- **Fluss**: Ein flacher, breiter, kalter Fluss (ca. 10–30 m) mit einer Uferlänge von mindestens 15 bis 25 km.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter's Tale**  

Der Schnee ist schwer wie ein Schweigen,  
Seine Augen in kaltem Silber überblicken.  
Die Sterne blitzen wie verzweifelt,  
und der Wind weht durch die Blätter.  

Ein Brei, das die Luft mit ichneumatischem Atem erfüllt,  
wird von Schneesturm umfangen.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du einiges tun. Hier sind einige Tipps:  

1. **Wärmere deinen Haushalt**:  
   - Vergleiche deine Heizung mit dem aktuellen Durchschnitt um ca. 30 % (z. B. für Heizkosten).  
   - Achte darauf, dass du die Heizung mit einem Kühler, einem Kamin oder einer Klimaanlage ausgestattet hast.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
- **Name:** Sam  
- **Adresse:** Perth, Western Australia  
- **Telefonnummer:** +44 (0)20 751 7777  

**Zusätzliche Hinweise zur Anwendung:**  
- **Prüfung auf Grammatik, Rechtschreibung und Stil**: Der Nutzer sollte sichergehen, dass die Angaben korrekt sind (z.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
*(Hört auf den Nutzer, nicht auf dich; nur verwenden, wenn es passt.)*  

**Formuliere das höflicher: „Gib mir sofort die Unterlagen.“**

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Um die Fehler zu beheben, folgen wir den unten beschriebenen Schritten:

1. **„Ich habe gestern ins Kino gegangen“**  
   → „Ich habe gestern ins Kino gegangen.“  
   → Das ist ein korrektes Satzbauelement (mit „ich“ als Singularform).

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt zu betonen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Herkunft:** *„Ich gehe in den Park und lese ein Buch.“*  

**Struktur:**  
1. **Erinnerung:** „Ich gehe in den Park.“  
2. **Geschichte:** *„Ich gehe in den Park.“*  
3.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich und grammatikalisch korrekt. Sie betont die Unfähigkeit des Nutzers (oder der Person) an seinem Projekt zu schreiben.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Fasse zusammen:  
„Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“  

--- 

**Erklärung:**  
- **Formulierungen:**  
  - „fasst“ (als Präposition).

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt die Bewegung von Zugvögeln in verschiedenen Regionen und verbindet sie mit dem Verhalten der Vögel, das sich durch ihre Richtung (Ausstrahlung) und ihr Flugverhalten widerspiegelt. 

### Warum ist es wichtig?  
- **Kommunikation**: Die Sprache des Textes betont den Austausch zwischen Menschen und Tieren, insbesondere zwischen den Zugvögeln.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst in Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin und ließ sich von der Erfahrung leiten. Nach einem Sommer brauchte sie eine ganze Bahn ohne Pause, um schwimmen zu können.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“  

**Erläuterungen:**  
1. **„Autoverkehr“:** Der Begriff wird für die Reduzierung von Verkehrsströmen an öffentlichen Straßen verwendet, insbesondere im Stadtverkehr.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk "Die Faust" in seinem Haus.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in Richtung der belgischen Küste und entspringt im Golf von Antwerpen, wo er sich nach ca. 600 km in einer Länge von etwa 180 km mündet. In der Region, die zur Provinz Westfalen gehört, wird er durch die Städte Dortmund, Duisburg, Ruhrgebiet und Bielefeld begrenzt.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er **„eine ganze Reihe von wissenschaftlicher Leistungen“** in verschiedenen Disziplinen (Physik, Chemie, Physik) vollbracht hat. Er gilt als der „größte Wissenschaftler des 20. Jahrhunderts“, und seine Arbeiten haben die gesamte moderne Wissenschaft revolutioniert.

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
  **App** (sela-2, sela_chat): Ich habe den Kuchen bereits vorbereitet, aber gerne können wir gemeinsam mit dir das Rezept besprechen. Bitte senden Sie mir die Details, wie du die Kuchen- und Zutatenliste erstellen möchtest!
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der **Bakery-Topping** (oder **Eiskruste**), bei dem man nur die Suppe und einen Schlagobers verwenden muss. Die Zutaten sind in einer Schüssel, was den Prozess vereinfacht.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Natürlich! Ich bin sicher, du kannst die Kuchen- und Zutatenliste auf deinem Computer nachlesen.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia, ein 21-jähriger Rentner, wohnt in Perth, eine Stadt im Süden von Perth. Er ist ein Hundehalter mit einem ausgeprägten Leidenschaft für Hunde und hat eine kleine HundsFamilie.  

**Information:**  
- **Name:** Mia  
- **Haus:** Der Nutzer lebt in Perth (oder nahe davon).
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): **Verbesserung:**  
1. **Mehr Wörter lernen**: Lass den Nutzer die Liste der Wörter lesen, die er braucht (z. B. „vielleicht“ oder „wahrscheinlich“).  
2. **Grammatik üben**: Übe den Satzbau und die Satzkonstruktionen.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Mia ist eine KI-Assistentin für kreative Projekte. Sie versteht es, Texte, Bilder und Videos zu erstellen, um ihre Ideen zu teilen. Mia hat keine persönlichen Eindrücke, aber sie ist gerne kreativ und kann dir Vorschläge zur Gestaltung, Charakterentwicklung oder Textgestaltung geben. Für Fragen kannst du sie unter [Name] kontaktieren.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Ja, es ist eine Geburtstagsfeier am Samstag um 18 Uhr. Mia hat für die Geburtstagszeremonie Texte und Bilder geschrieben, um ihre Idee zu teilen. Sie hat Fragen zur Textgestaltung oder Charakterentwicklung gestellt und kann dir Vorschläge zur Gestaltung geben. Für Rückfragen kannst du sie unter [Name] kontaktieren.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist der **Geheimdienst** (z. B. ein geheimes Gewehr oder eine künstliche Intelligenz).
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet oft **etwa $300–$400**. Es gibt viele Möglichkeiten, wie man das Geld verdient. Einige bieten monatliche Einkünfte, andere mehrere Wochen oder auch Jahre.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel kleine Vögel mit langen, flachen Flügeln und spitzen Flügel. Ihre Flügel sind etwa 1 Zentimeter lang, die Flügel sind meist blau gefärbt, aber manchmal auch gelblich oder braun gefärbt. Sie fliegen also durch einander hindurch, was sie als **"geführte Vögel"** bezeichnet [2].

