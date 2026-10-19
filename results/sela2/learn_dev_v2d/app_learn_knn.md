# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T09:20:48Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 1 von 100 |
| identity_error | 0 von 100 |
| echo | 0 von 100 |
| cut_off | 0 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| error | 0 von 100 |
| prompts_with_a_problem | 1 von 100 |

Antworten nach Modell: {'engramm': 21, 'sela-2': 96}; nach Art: {'about': 1, 'answer': 3, 'learned': 4, 'sela_chat': 89, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 5 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi!

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well. I was just talking to you about my work and what's on your mind. Can you tell me a little bit more about yourself? Do you have any interesting experiences or hobbies that you're passionate about?

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
  **App** (sela-2, sela_chat): Hello, welcome back! What would you like to know about me?

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a freelance photographer and writer based in Perth, Australia. I'm currently living in Perth and have been working on a new project - a series of Instagram stories about local food scenes. I've been asked to share these stories with my community and help raise awareness about the importance of preserving the local food scene.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 2 Versuche): I am a graduate student in Environmental Science at the University of Perth, Australia. My academic interests include environmental policy and sustainability. I have a passion for wildlife conservation and help protect ecosystems worldwide.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of creative endeavors, from designing an immersive experience to crafting compelling stories. Whether you're working on a novel, short story, poem, or video game, I'm here to offer ideas, suggestions, and guidance to bring your vision to life.

Whether you're looking for inspiration for a character, setting, plot twist, or world-building, I'm ready to assist.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Schedule regular breaks
2. Avoid multitasking
3. Stay on task
4. Use a tool to stay organized
5. Keep track of your progress
6. Seek support from colleagues or friends when needed
7. Use a productivity app for real-time updates and reminders
8.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): Thanks for the tip! To boil an egg, you need to use a working thermometer. If you have one, put it in a pot with boiling water (no ice) and cook until it turns from brown to white. Then remove the thermometer and place it in a bowl of hot water to boil the egg.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a tiny piece of code that can harm computers, including those used for data storage, communication, and entertainment. It's like a sneaky spy who gets in and takes over the computer's system. When a computer virus infects a computer, it creates an executable file called a "program" that copies itself into the computer's memory, causing damage or stopping normal functions.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): My plants are doing great. I water them every week. Let me know if you need any help. If not, I'd be happy to do it myself. Thanks!"

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Good source of vitamin C is orange
2. Tomatoes are high in vitamin C
3. Cucumbers are a good source of vitamin C
4. Carrots are also high in vitamin C
5. Cherries are another good source of vitamin C
6. Spinach and kale are good sources of vitamin C

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): weather: is the weather that you experience every day and can be measured. climate: is the state of the weather that surrounds a place or country.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): A kaleidoscope of autumn leaves,
Carved from the purest blue,
Coming to life in every leaf.
They rustle like whispered secrets,
Each rustling a whisper,
And leave behind only the softest sighs.

The wind carries the sweet scent of gold,
Leaving trails of golden light,
As the sun's warmth seeps through the earth,
Echoes of love and laughter lingering.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, follow these steps:

1. Use a strong, unique password. Avoid easily guessable or weak passwords.
2. Consider using a password manager (e.g., LastPass, 1Password).
3. Change your password frequently. It's best to change it at least once every 6 months.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. "Library Shack" (a modern coffee shop near a library)
2. "Familiar Coffee Shop" (near the library)
3. "Glasshouse Coffee Shop" (near the library) Good friend!

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): What you do:
- Set a goal for your workout, such as exercising at least 30 minutes.
- Take an hour to plan the workout and get ready.
- Start with a walk or jog around the block. Good way to get some exercise in.
- Go to the gym, find a isometric exercise routine that suits your fitness level.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): Pack something comfortable and lightweight for the hot weather. Bring a waterproof jacket, warm hat, gloves, and boots or shoes. A good first aid kit is also important to have in case of an emergency. Include layers for cooler days.

For longer trips, consider bringing a portable camping stove with fuel and cooking pots.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering body of water that covers nearly half of the Earth's surface, offering a mesmerizing display of light and color. It stretches out in all directions, with towering peaks that touch the sky like giant sentinels, and luscious white beaches that gently wave against the shore as the sun dips into the horizon.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Acknowledge the invitation: Express your appreciation for the opportunity and let the person know that you're happy about their request.
2. Show your gratitude: Let them know how much they've meant to you, and express your gratitude for their kind words.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Here's a rewritten version: "I'm sending you the report now."

Or, for a more conversational tone: "Sorry, I haven't got it yet. Let me know if you need help finding something else."

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): Here's a simpler version: "Public transportation reduces urban congestion." 

Or, if you'd like to make it even shorter: "Public transportation helps reduce urban congestion." 

Alternatively, you could also use these two options in a sentence: "Public transportation leads to reduced urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "She doesn't like going to school on Mondays."

I added an apostrophe to "mondays" since it's not a plural noun. The corrected sentence would be: "She doesn't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 2 Versuche): I walk to the station and buy a ticket. I'm going to buy a ticket.

In the past tense, I would have walked to the station and bought a ticket (or rather, "buy" a ticket). In this case, it's more polite and correct to walk to the station and then buy a ticket.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Get ready to help out at our exciting sale this weekend!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): I'm sorry, but I don't have access to the internet or any device that can answer questions in English. However, I can help you with a question about the train leaves at 8:00 o'clock! Would you like me to help you with anything else?

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Dear [User's Name],

I am writing to express my regret over the delay in completing your request. I apologize for any inconvenience this may cause and appreciate your understanding in resolving your matter promptly. 

Please note that this message will not be used to engage in personal conversations or discussions about our current projects.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside."

I made a few changes to make the sentence more concise and grammatically correct. I removed "due to" as it's unnecessary in this context, and changed "we made the decision" to "we chose," which is a more direct and idiomatic way to express the action.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made a few changes to improve clarity and grammar:

- Changed "will be closed" to "will be closed" to use the correct verb tense (be in the past, present, or future).

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This is a short summary of Tom's story:

Tom started learning the guitar at age three. He began practicing by playing his favourite song, "Tom wanted to learn the guitar." Despite his initial hurt and the wrong chords, he eventually mastered them through repetition and practice. By the end of three months, he was able to play his favorite song for friends.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

Note: This email is a collaborative effort between two teams, and may not be accurate due to changes in communication channels or specific projects.

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
  **App** (sela-2, sela_chat): Venice is the first place. It's a must-visit for Italy, and it's famous for its stunning architecture and delicious food.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): You can try the famous pasta dishes like spaghetti Bolognese, fettuccine, and pappardelle. You can also try some traditional Italian desserts like pizza, gelato, and espresso.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Photo of mother with her dog**:  
   - If your mom has a dog, you can include the photo on the card and write a message about the importance of family and having a pet.

2. **How she likes to celebrate birthdays**:  
   - If she loves chocolate or cake, you can add a chocolate chip or cake center.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Photo of mother with her dog**:  
   - If your mom has a dog, you can include the photo on the card and write a message about the importance of family and having a pet.

2. **How she likes to celebrate birthdays**:  
   - If she loves chocolate or cake, you can add a chocolate chip or cake center.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Sam is a wonderful person! Feel free to share your thoughts, feelings, or concerns. I'd love to hear more about what's been going on in your life and any challenges you're facing.

If you'd like to talk about your dog Rex, that would be great as well.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Sam is a great person! Here are some things you can do to relax this evening:

1. Take a walk in nature. The city is beautiful, and it's easy to get lost in the hustle and bustle of Perth. You can grab some fresh air and enjoy the views.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The watering schedule depends on how much water the plant needs. For a succulent, like a cactus or succulent, water less frequently than for other plants. You can also water it when it's between 20 and 30 degrees Fahrenheit (68 and 86 degrees Celsius) — this is called the "watering window."

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, regular chunks of time each day to read. Begin with short stories, like the ones you've already started, and gradually build up to longer books. Try using a bookmark app or website to help you stay on track.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found that. Good luck with your reading journey!

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
- 4 tablespoons of vegetable oil
- 1 teaspoon of mustard
- 1 teaspoon of hot pepper flakes
- 3 tablespoons of mayonnaise or homemade mustard
- Salt and pepper to taste
- Freshly sliced tomatoes about 1 cup each

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
  **App** (sela-2, sela_chat): Ich habe in Perth studiert und mich seit drei Jahren dort wohlhabend aufgehalten. Meine Leidenschaft ist es, Hunde zu pflegen und Hilfe bei der Pflege zu finden.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir einfach deine Angaben über den Nutzer, damit ich dich effektiv betreuen kann.  

Senden Sie mir bitte deinen Namen und dein Zitat, damit ich dir bei der Auswahl deiner Antwort helfen kann.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Morgen frühzeitig schlafen**: Schlafenszeiten variieren je nach Stressniveau und körperlichen Einschränkungen, so dass eine Einteilung in drei Phasen (2 bis 4 Stunden) möglich ist.  
   - *Beispiel:* Morgen: 1 Stunde, Abend: 2 Stunden, Nacht: 4 Stunden.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat, 2 Versuche): Strom ist ein Hilfeleistungssystem, das die Energie aus erneuerbaren Quellen wie Wind, Wasser oder Sonnenlicht extrahiert und in elektrischen Strom umwandelt. Der elektrische Strom wird entweder in Stromnetzwerken (z. B. Straßen, Schulen) oder im Netz gespeichert.

---

**Beispiel:** Ein Stromnetzwerk in Perth versorgt etwa 200 Einwohner mit Wasser.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Lieber [Name], ich bin heute Abend für eine kurze Nachricht an [Kontaktperson] zu einem Meeting im Büro. Bitte gib mir die Kontaktdaten an, damit ich diese rechtzeitig umsetzen kann.**  
---

**Ihr Name:** Sarah  
**Telefonnummer:** +44 (0)1 306 29 29  
**Email-Adresse:** [adresse]@example.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **4 Gemüsesorten, die im Herbst geerntet werden:**  
1. **Lager-Dahl (Rex):** Menschliche Bezeichnung für das Getreide, das vor dem Erntezeitpunkt käme.  
2. **Sparen (What’s Left is Wheat first):** Auf Grund des Erntezeitpunkts werden Pflanzen nach Ernte noch bis zu einem Tag unter Rücksicht auf Rinder, Hüte oder andere Lebensmittel benötigt.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in etwa 2–3 Minuten kochend (kochen) werden. Sie können auch mit einem Schneebesen oder einer Handfee eingefroren werden, um sie zu schützen.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht der Fluss**. Der Begriff "See" ist gebräuchlich für alle Arten von Flüssen, die sich durch Wasser bewegen. Es gibt auch den Begriff "Fluss", wenn es um einen einfachen Fluss geht, der durch ein Tal fließt oder über das Meer hinausgeht.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter’s Wrath**  

Ein sanfter Schnee und eine schwache Sonne,  
Ein Kuss, den ich nicht tragen kann.  
Die Luft ist kalt und kalt,  
Das Licht ist tot, aber das Lied hält inne.  

Und die Stille, so still wie ein Lied,  
Blickt auf die Zeit, als sie stand.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du einiges tun. Hier sind einige Tipps:  

1. **Sammeln Sie Dinge in den Spaten**: Wenn du viel Kleidung benötigst, kannst du später auch den Spaten mit Dingen wie Taschen oder Müll verwenden.  
2.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
- **Name:** Sam  
- **Adresse:** Perth, Western Australia  
- **Telefonnummer:** +44 (0)20.068.8759  
- **E-Mail:** [email]  

**Über dich:**  
- **Name:** Rex  
- **Adresse:** Perth, Western Australia  
- **Telefonnummer:** +44 (0)20.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  

---  
*P.S. Wenn du sie fragst, klicke bitte auf „Über mich“ – das ist der beste Weg, um zu wissen, was du fragst.*

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): What do you mean by „Ich habe gestern ins Kino gegangen“?  
(Verse 1 und 2: Fehler → fix)  
*(Korrigierte Satz 3: Fehler → fix)  

---

**Problem:** Der Nutzer hat Angaben über den Nutzer (z. B.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt (Wetterlage und Absage) klarer zu strukturieren.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Zusatz:** „Ich kann den Park nicht verlassen, weil ich in der Vergangenheit mich als Nutzer heute so verhalten habe.“  

**Erklärung der Änderung:**  
1. **Vergleich mit dem aktuellen Kontext:** Der Satz wird heute **nicht mehr** verwendet, da er als Erinnerung an eine vorherige Zeit gilt (z.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** *„Hey, kann morgen leider nicht, sorry!“*  

**Hinweis:**  
Das „Hey“ ist ein passender Ausdruck für eine kurze Nachricht. Falls du es mit einer anderen Form an jemanden versuchst, z. B. mit der Begründung: *„Ich bin müde, aber ich hoffe, dass dir etwas helfen wird.“

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Der Nutzer, der dir über sich erzählt hat – Name: Sam; wohnt in Perth; Hund: Rex.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt die Bewegung von Zugvögeln in verschiedenen Regionen und endet mit der Erinnerung an ihre Rückreise nach Süden, um Nahrungsmittel zu finden. Die Kombination aus „wärmeren Gebieten“ und „Wanderungen über den Süden“ vermittelt einen lebendigen Bildernzyklus. Der Kontext zwischen Herbst- und Winterwanderung wird durch das „Rückkehr“ der Vögel unterbrochen, um das Nest wieder anzulegen.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst in Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin und ließ sich von der Erfahrung leiten. Nach einem Sommer war sie ohne Pause erfolgreich genug, um eine Bahn zu schwimmen.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“  

**Erläuterungen:**  
1. **„Autoverkehr“:** Der Begriff wird durch „Fahrradweg“ ersetzt, um die Form des Projekts klarer zu vermitteln (z.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk „Der Sturm“ (1789) [1].

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in Richtung der Eifel und durch das bekannte Tal des Saarlandes. Er hat eine durchschnittliche Länge von rund ich mehr als 100 km, die meisten Städte sind über den Fluss und ihre wichtigsten Flüsse.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er **„eine große Entdeckung in der Physik“** gemacht hat und sie „für ihre Bedeutung und Verständlichkeit“ bekannt machte. Er begründete die These, dass die Welt nicht um sich selbst herum, sondern durch eine kontinuierliche Bewegung (wie Licht) entstanden sei.

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
  **App** (sela-2, sela_chat): Ich habe den Kuchen bereits vorbereitet, aber gerne können wir gemeinsam mit dir ein Rezept erstellen. Bitte senden Sie mir den Text über die gewünschte Art und Anzahl an Zutaten (z. B. Teig, Kuchenstücke oder Brötchen) und teilen Sie mir, wie viel Zeit für den Backen benötigt wird.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der **Mango-Zucchini-Trippel**, auch als "Bistro-Stick" bekannt. Er wird direkt aus dem Ofen gebacken und eignet sich gut für Backen.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Ja, der einfachste Kuchen ist der **Mango-Zucchini-Trippel**. Er wird direkt aus dem Ofen gebacken und eignet sich gut für Backen.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia, ein Englischlehrer in Perth, erzählt mir von ihrem Leben im Büro. Sie arbeitet seit zehn Jahren in der IT-Beratung und lerne seit ihrem sechsten Geburtstag Englisch. Rex ist ihr Hundehalter, und sie spricht manchmal noch mit ihm.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia ist eine Englischlehrerin, und Rex ist ihr Hundehalter. Sie erzählt mir von ihrem Leben in Perth und ihren Arbeitsschwerpunkten.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Mia ist eine KI-Assistentin für kreative Projekte. Sie beschreibt ihre Aktivitäten wie folgt:  

1. **Mgespräch mit dem Nutzer**:  
   Mia kommuniziert über den Nutzer, um ihn zu inspirieren und seine Bedürfnisse besser verstehen. Beispiel:  
   *"Ich habe ein Projekt über das Thema ‚Die Kunst der Erinnerung‘ entwickelt.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Mia ist eine KI-Assistentin für kreative Projekte. Sie beschreibt ihre Aktivitäten wie folgt:  

1. **Einladung an den Nutzer**:  
   Mia kommuniziert über den Nutzer, um ihn zu inspirieren und seine Bedürfnisse besser verstehen. Beispiel:  
   *"Ich habe ein Projekt über das Thema ‚Die Kunst der Erinnerung‘ entwickelt.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist **Bugeln** (auch „Mini-Bugeln“ genannt), da sie sich mit einem Vorratsbehälter an einen Brettstapel oder ein Spielfeld kleben und so schnell wie möglich abgeben. Zudem sind sie gut geeignet, um in der Dämmerung zu spielen.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet zwischen **$10–€20** (Geld, je nach Größe und Spielort). Je mehr Du bist.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel schlafend und können mit einem Vorrat an Nahrung über den Boden fliehen. Ihre Körpertemperatur sinkt ab, wenn sie sich schnell aufhalten, aber ihr Flug ist nicht unmöglich [1].

