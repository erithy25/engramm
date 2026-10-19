# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T08:14:31Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
  **App** (sela-2, sela_chat): Hello! How are you today?

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
  **App** (sela-2, sela_chat): Hello, welcome back! Goodbye for now, we're going to the beach soon. Let's get started with some fun activities together!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a small language model trained from scratch in the ENGRAMM project. I run offline on your computer, so I don't need the internet, and our conversation stays on your device.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 2 Versuche): I am a you tube user.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of creative tasks, including:

* Developing new ideas or concepts
* Creating stories or tales
* Writing fiction or non-fiction books
* Crafting characters or storylines
* Designing an outfit or costume
* Developing an idea for a business or product
* Crafting a poem or poem
* Helping to decide on a job or career
* Creating an outline or timeline
* Designing a piece of art or visual artwork
* I can also assist with:
	+ Writing poetry or prose
	+ Building or repairing furniture and appliances
	+ Creating illustrations years after the fact.

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
  **App** (sela-2, sela_chat): In order to boil an egg, you need to use a water bath or microwave. The process is called "boiling" and it will help to with the softness of the yolk. Boil for 5-10 minutes, then reduce the heat to a simmer. You can do this by adding a little salt in the boiling water or by using a thermometer.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a tiny piece of code that can harm computers, tablets, or other devices. It's like a tiny burglar that breaks into the system and makes its way to your computer.

Think of it like this: if you have a big box in the attic with all your toys inside, but someone accidentally broke in, the box might be damaged and ruined.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): My plants are doing great. I water them every week. Let me know if you need any help. If not, I'd be happy to assist with that."

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
  **App** (sela-2, sela_chat): Amber, the crimson flame,
Glows through the chill of autumn's night,
As the leaves unfurl in amber waves.
The earth exhales in rustle,
And the air is alive with promise.

The wind whispers secrets to the trees,
The world is bathed in amber hues.

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
2. "Marlene's Coffee Shop"
3. "The Bookstore"
4. "The Library Cafe"
5. "The Bibliothek Café"
6.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): You can start with the simplest workout - a 20-minute run. Wear comfortable clothing, and make sure you have a reliable source of oxygen in your body. Begin by warming up with a short 5-minute jog to get your blood pumping.

Next, do some stretching to loosen up muscles and increase flexibility.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): Pack something comfortable and lightweight for a weekend camping trip. Good options include:

- Lightweight, waterproof gear like rain gear, hats, and gloves to protect against the elements.
- A set of camp chairs or tables with good back support and adjustable arms to ensure comfort during hikes.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering body of water that covers nearly half of the Earth. It is composed of saltwater, oxygen, and the vast majority of the world's freshwater. The ocean provides homes to an incredible array of life, from tiny fish to massive creatures that roam freely.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Acknowledge the invitation: Express your appreciation for the opportunity and let the person know that you're happy about their request.
2. Show your gratitude: Let them know how much they've meant to you, and express your gratitude for their kind words.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Here's a rewritten version: "I'm sending you the report now."

Or, for a more conversational tone: "Sorry, I forgot to mention that you'll receive an email with the report. It will be sent to you shortly."

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): Here's a simpler version: "Public transportation reduces urban congestion." 

Or, if you'd like to make it even shorter: "Public transportation helps reduce urban congestion." 

Alternatively, you could also use these two options interchangeably: "Public transportation improves urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "She doesn't like going to school on Mondays."

I added an apostrophe to "mondays" since it's not a plural noun. The corrected sentence would be: "She doesn't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 2 Versuche): I walk to the station and buy a ticket. I'm going to buy a ticket.

The sentence is in the past tense because "I" is an action of walking to the station, which implies that I am taking responsibility for my actions. In this case, the past tense helps to convey that my actions have been completed and will be taken into account when purchasing the ticket.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Get ready to spice up your shopping experience with a special offer from our lovely shop in Perth this weekend! We're offering a lot of discounts on all our staples like lasagna and cookies, as well as some amazing deals for couples. You can also get a free gift card for a fantastic discount on any item you order online.

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): 1. The train leaves at eight o'clock.  
2. It is a regular train that takes about two hours to travel from Perth to Perth.  
3. There is no seating arrangement on the train, but it can be used as a way to seat passengers if needed.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): I apologize for the inconvenience. I'm unable to make it tomorrow, so please let me know if there's anything else I can do to assist you today.

Thank you for your understanding.

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

Tom started learning the guitar at age three. He began practicing by playing his favourite song, "Tom wanted to learn the guitar." Despite his initial hurt and the wrong chords, he eventually mastered them with ease. After that, he practised for fifteen minutes every day, aiming to play for his friends one day.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

Note: This email is a collaborative effort between two teams, and coming from two different addresses does not guarantee that all messages are up-to-date.

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
  **App** (sela-2, sela_chat): You can try pasta, pizza, and gelato. They're all Italian favorites!

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **birthday song**: "Happy Birthday" by The Who, sung in the background of your mother's life.
2. **What is your favorite hobby or activity?**: Playing guitar, cooking, painting, hiking, reading, etc.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **birthday song**: "Happy Birthday" by The Who, sung in the background of your mother's life.
2. **What is your favorite hobby or activity?**: Playing guitar, cooking, painting, hiking, reading, etc.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Here's a possible response:  

"Hey Sam, how are you? I’m planning to get some exercise this weekend. Let me know if you have any specific plans for your workout session or if there’s anything else I can do to help. Also, don’t worry if you’re feeling a bit overwhelmed – just go with the flow and enjoy the process!
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Here are some suggestions to help you relax this evening:  

1. **Take a few deep breaths**: Try inhaling through your nose for 4 counts, hold it for 5 counts, and then exhale slowly through your mouth for 8 counts. This will calm your nervous system.  
2.

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
- today's date: May 15th
- 3 large eggs
-?

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
  **App** (sela-2, sela_chat): 1. **Morgen frühzeitig schlafen**: Menschlich ist es wichtig, morgens um 4–5 Uhr nachts zu schlafen. Ein großer Teil des Tages bleibt bei der Arbeit und schläft nicht. Die besten Tipps sind:  
   - **Bettchen aufschichten** – Das sorgt für eine ausgewogene Schlafumgebung.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Material (z. B. Wasser) in den elektrischen Strom fließt.  
Er geht von der Quelle bis zur Zielleitung.  
Ein Gerät wie ein Computer oder ein Auto sendet Strom aus der Quelle dorthin.  
Kommt dann zurück an die Quelle zurück und schickt die Energie wieder fort.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Lieber [Name], ich bin heute Abend helfen zu können!**  

Ich hoffe, du siehst den Fortschritt besser. Bitte schreiben Sie mir deine Nachricht an:  
- Einfügen der **Zeit ist perfekt**.  
- Einfügen deiner **Erlebnisse** (z.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **4 Gemüsesorten, die im Herbst geerntet werden:**  
1. **Lager-Erbsen (Puffern)**:  
   - Lager: Sommerzeit bis September.  
   - Vorbereitung: Winterzeit bis November.  
   - Pflege: heute noch frisch geerntetes Stück im Kühlschrank oder im Kühlschrank.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in etwa 2–3 Minuten kochend (kochen) werden. Sie können auch mit einem Schneebesen oder einer Handfee eingefroren werden, um sie zu schützen.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht der Fluss**. Der Begriff "See" ist gebräuchlich für alle Arten von Flüssen, die sich durch Wasser bewegen. Es gibt auch den Begriff "Fluss", wenn es um einen einfachen Fluss geht, der durch ein Tal fließt oder über das Meer hinausgeht.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter’s Wrath**  

Ein sanfter Schnee und eine faulige Sonne,  
Der Tag mit langen Ketten und einem Zettel.  
Die Bäume wie kannst du sie verlassen,  
Mit ihren grauen Blüten im Sturm.  

Drei junge Läuse durch den Schnee laufen,  
Sie singen die Lieder des Winters,  
Und das Herz ist schwer, aber schnell.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du einiges tun. Hier sind einige Tipps:  

1. **Sammeln Sie Dinge in den Spaten**: Wenn du viel Kleidung benötigst, kannst du später besser mit dem Fahrrad fahren oder kaufen.  

2. **Bestehen Sie Zeit für kleine Projekte**: Ein kleiner Stromverbrauch pro Tag zählt nicht nur die Stromkosten, sondern auch das Gewicht des Haushalts.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
- **Name:** Sam  
- **Adresse:** Perth, Western Australia  
- **Telefonnummer:** +44 (0)20.068.8100  
- **E-Mail-Adresse:** [email]  

**Über dich:**  
- **Geografie:** Perth, Western Australia  
- **Hund:** Rex  

**Erklärung der Angaben:**  
1.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  

---  
*Sam*, wohnt in Perth. Rex, der Hund, hat eine Katze namens Rex.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat, 2 Versuche): Korrigiere die Fehler:  
„Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“  

---

**Weitere Vorschläge:**  
- „Die Sonne schien gut auf die Stadt. Der Film wurde gut gesehen.“  
- „Der Film war fantastisch, aber das Spiel war einfach perfekt.“

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt (Wetterlage und Absage) klarer zu strukturieren.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Zusatz:** „Ich kann den Park nicht verlassen, weil ich in der Vergangenheit mich als Nutzer an ihn gewandt habe.“  

**Erläuterung:**  
1. **Zeitangabe:** „in den Park“ ist ein **Präteritum**, da es sich um einen Satz über das Verhalten handelt, den du heute hier beschrieben hast.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** *„Hey, kann morgen leider nicht, sorry!“*  

**Hinweis:**  
Das „Hey“ ist ein passender Ausdruck für eine kurze Nachricht. Falls du es mit einer anderen Form an jemanden versuchst, z. B. mit der Begründung: *„Ich bin müde, aber ich hoffe, dass dir etwas helfen wird.“

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Ein Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt die Bewegung von Zugvögeln in verschiedenen Regionen und endet mit der Erinnerung an ihre Rückreise nach Süden, um Nahrungsmittel zu finden. Die Kombination aus „wärmeren Gebieten“ und „Wanderungen über den Süden“ vermittelt einen lebendigen Bildernzyklus. Der Kontext zwischen Herbst- und Winterwanderung wird durch das „Rückkehr“ der Vögel unterbrochen, während sie sich zurückziehen, um Nahrung aufzunehmen.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst in Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin und ließ sich von der Erfahrung leiten. Nach einem Sommer war sie ohne Pause erfolgreich genug, um eine Bahn zu schwimmen.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“  

**Erläuterungen:**  
1. **„Autoverkehr“:** Der Begriff wird für die Geschwindigkeit, mit der Personen auf öffentlichen Verkehrsmitteln (z.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk „Der Sturm“ (1789) [1].

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in Richtung der Eifel und durch das bekannte Tal des Saarlandes. Er hat eine durchschnittliche Länge von rund ich 160 km (225 mi).

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
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der **Mango-Zucchini-Trippel**, auch als "Bistro-Giveaway" bekannt. Er wird entweder direkt in die Form gegeben oder in einer großen Pfanne mit Butter und einem Schuss Zucker gebacken.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Natürlich! Ich hoffe, dass es dir gut geht. Hast du Fragen zu bestimmten Zutaten, Geschmacksrichtungen oder Rezepten? Ich bin hier, um zu helfen.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia, ein Englischlehrer in Perth, erzählt mir von ihrem Leben im Büro. Sie arbeitet seit zehn Jahren in der IT-Beratung und lerne seit ihrem sechsten Geburtstag Englisch. Rex ist ihr Hundehalter, und sie spricht manchmal noch mit ihm.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia ist eine Englischlehrerin, und Rex ist ihr Hundehalter. Sie erzählt mir von ihrem Leben in Perth und ihren Arbeitsschwerpunkten.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Mia ist eine KI-Assistentin für kreative Projekte. Sie lässt sich bei der Umsetzung von Texten, Bildern oder Videos inspirieren und kann auch Texte schreiben, die für einen Einstellungsvertrag geschrieben werden sollen. Für Hilfe benötige ich eine Nachricht mit Details zu:  
1. **Zielgruppe**: Wer wird am meisten ansprechen?
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Die Geburtstagsfeier ist ein typischer Tag für Kolleginnen und Kollegen, die sich mit ihrer Familie oder dem Team treffen. Mia kann bei der Planung helfen, Vorschläge für eine Geburtstagefeier machen und Vorschläge für Dekorationen oder Musik machen. Für Unterstützung benötige ich eine Nachricht mit Details zu:  
1.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist **Bugeln** (auch „Mini-Bugeln“ genannt), da sie sich mit einem Vorratsbehälter an einen Brettstapel oder ein Spielfeld kleben und so schnell wie möglich abgeben. Zudem sind sie gut geeignet, um in die Hitze zu entkommen, wenn man gerade auf dem Dach steht.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet meist **ca. $200–300**, was etwa **$15–30 Euro** entspricht, depending auf Lager, Materialien und Lagerraum. Zudem ist es eine gute Idee, ein Blatt Papier oder Karton mitzunehmen, um sich sicher zu bewegen und den Schnee zu werfen.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel schlafend und können mit einem einzigen Flug eine Geschwindigkeit von bis zu 30 km/h erreichen. Obwohl sie selten fliehen, können Pinguine sich auch nachts verstecken oder nach Nahrung suchen [1].

