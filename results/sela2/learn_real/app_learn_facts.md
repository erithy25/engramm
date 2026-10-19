# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T18:16:06Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
Schutzregeln: 1 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! I like to play with my dog Rex. We both live in the same house.

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well! I hope you're having a great day. How can I help you today?

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help you today?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): I like to eat lasagna.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): No, Goodbye!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a small offline assistant who lives in Norwich, England. I love spending time with my family and friends.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 3 Versuche): I grew up in a small town with a strong sense of community and tradition. Growing up, I learned about my family's history and the importance of preserving our cultural heritage. I also spent time outdoors, exploring the natural world and learning about different creatures and plants.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I'm sorry, but I don't have access to your personal details or data. My role is to assist you with questions related to your environment, technology, or any other subject you'd like help with. If you have a question or need assistance, feel free to ask!

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Find a quiet workspace. 
2. Use your computer for personal tasks. 
3. Create a dedicated study area with minimal distractions.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): If you're using a microwave, the answer is to use a food processor or a bowl of water and let it melt.  You can also add your milk (if you have it) in your milk to help with the process.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible piece of software that can replicate itself and spread around the internet. It's like a big toy that can cause chaos or harm. Computer viruses can infect computers, steal information, or even send emails to people who don't know how to protect themselves.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): The dog Rex loves water. Can you please help me with watering my plants next week? I have a lot of plants and it's really cold outside so it might be hard to water them right now."

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. citrus fruits like oranges, lemons and grapefruits
2. strawberries
3. tomatoes
4. kiwi
5. pineapples

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two related but distinct concepts. **Climate** refers to the long-term patterns of atmospheric conditions, typically measured in terms of temperature, precipitation, wind, and humidity. Climate is a broad term that encompasses not just weather, but also other factors such as ocean currents, land use patterns, and economic processes.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The earth exhales a breath of autumn's fiery sigh,
And the wind whispers secrets in rustling leaves.
Each leaf, a testament to nature's slow flight,
Falls softly on the breeze, its branches swaying gently.

In every leaf, a story is told of fall's birth,
Of storms that melt the heart, and the sun's descent.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some tips to make your password more secure:

1. Use a strong, unique password. Avoid using something easily guessable like your name or birthdate. Instead, use a combination of letters, numbers, and symbols (a mix of uppercase and lowercase letters). For example: "DON'T PASSWORD!"

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. The Bookshelf Cafe (near a library) – A cozy spot with a selection of books on various subjects, including literature, history, and science.
2. The Library Rooms Cafe (near a library) – A quirky little café where you can browse the shelves and find unique items to add to your collection.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): For a 20-minute workout without equipment, start with a brisk walk outside to get your heart rate up. Begin with 1-2 minutes of brisk walking, followed by some light jogging or yoga. Then, move on to jumping rope, step-ups, or a modified indoor/outdoor running track.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You will need:
- A backpack or tent with sleeping bags and a sleeping pad.
- A portable stove, camping grill, water purification tablets, toiletries, a change of clothes, and layers for the weather.
- A waterproof jacket (not the ones you wear on the highway), a pair of warm socks, and some clothing to keep dry.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark expanse that stretches out from the shores of Europe to the Atlantic Ocean, covering an area of about 600 miles (1,300 kilometers) in length and 1,000 miles (2,200 kilometers) wide. It is made up of three distinct layers: the surface layer, which covers approximately 80% of the Earth's surface; the middle layer, which covers about 20%; and the deep ocean, which covers about 50% of the Earth's surface.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how to politely decline an invitation to a party:

1. **Tell the person you're not invited** (e.g., "I'm not interested in attending").  
2. **Use phrases like "I understand this is my choice," "I'll make sure to be there," or "I'm not available for any reason."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text: "Send me the report now."

I removed the phrase "now" because it's not necessary in this context. If you want to emphasize that the report has already been sent, you could say: "Send me the report now." This is a bit more concise and professional.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): The sentence can be simplified to: "Public transportation improves urban congestion."

This version conveys the same information in a more direct way, eliminating unnecessary words and phrases. The word "utilisation" is replaced with "improvement", which is a more precise and active term for public transportation. The phrase "a reduction in urban congestion" is also shortened to "urban congestion", making it more concise and easier to understand.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct edit would be: "She don't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

The past tense is used when describing a completed action. The correct sentence would be "I walk to the station and buy a ticket."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "We're featuring a unique sale this weekend, inspired by our beloved dog, Rex!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): To turn this into a question: "The train leaves at eight o'clock."

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): **Subject:** Request for Assistance with Writing an Argumentative Essay

Dear Mr. Smith,

I am writing to express my sincere regret for the delay in completing my essay due to circumstances beyond my control. The deadline was yesterday and I am not aware of any issues that might have contributed to this delay.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we made the decision to stay indoors."

I removed the phrase "Due to" as it doesn't add much meaning. I also changed "due to the fact that" to "due to," which is a more concise and direct way to express the same idea.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made the following changes to improve clarity and grammar:

- Changed "will be" to "will be" (correct verb form)
- Added an article ("the") before "sreptea" to make it plural
- Changed "reopen on Tuesday" to "reopen on Tuesday" for correct punctuation
- Added "due" to "Monday" to agree with the subject
- Changed "it" to "its" to use the correct possessive pronoun
- Changed "can be returned on Tuesday" to "can be returned on Tuesday" for proper sentence structure
- Changed "late fee" to "late fee" (correct spelling)

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This short summary describes a typical day for Tom. He starts by practicing his favourite song, "Tom's Favorite Song," which he knows is on the guitar. Next, he practises all 15 chords of the song until he can play it without hurting himself. After that, he practises for fifteen minutes daily, three times a week.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The user's email is: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

Here's a brief summary of the user's email:
- The email was sent to them on Wednesday morning.

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
  **App** (sela-2, sela_chat): If you're planning a trip to Italy, I would recommend Rome. It's the heart of the country, and there's so much to see. You can visit the Colosseum, the Roman Forum, and indulge in delicious Italian cuisine. Plus, Rome has plenty to offer, like Vatican City, indulging in art and architecture, or taking a cooking class.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Italy has a wide variety of delicious Italian cuisine, from pasta to pizza. Try some classic dishes like carbonara and pizza, or try something new like gelato and espresso. Don't forget to try some of the local specialties like ribollita and bruschetta! You can also explore Rome's historic center by visiting the Trevi Fountain, which is one of the best places to see the city's famous Spanish architecture.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here's a birthday card for your mother:

1. **Title**: 
2. **Date**:  
3. **Time**:  
4. **Location**:  
5. **Dress**:  
6. **Message**:  
7. **Description**:  
8.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version:

1. **Title**:  
2. **Date**:  
3. **Time**:  
4. **Location**:  
5. **Dress**:  
6. **Message**:  
7. **Description**:  
8.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): I can't provide specific information about Sam, but I can give you some general details:

1. **Name**: Sam
2. **Occupation**: Actor (storyteller)
3. **Dress Code**: A formal, polished outfit with a formal tie and polka dots.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): To relax this evening, consider the following:

1. **Take a warm bath**: A relaxing soak in a hot tub or steam room can help reduce stress and tension. You can also use a soothing shower gel or bath bombs.
2. **Take a walk**: Even a short walk outside can be calming.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The water should be at least once a day.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, regular chunks of time each day to get your hands dirty. Try setting aside 15-20 minutes a day for reading, like you mentioned earlier.
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
- 3/4 cup sliced red onion
- 1 tsp salt
- 1/4 cup tomato paste
- 2 cloves garlic
- 1/4 cup chopped parsley
- 1/2 cup heavy cream
- 1 tsp grated Parmesan cheese
- Fresh parsley, chopped (optional)

Instructions:
1.

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Wie geht es dir? Der Nutzer Sam wohnt in Norwich und der Hund Rex lebt dort.

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Gern geschehen!

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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir einfach deinen Namen, den du genannt hast, und lass mir wissen, ob es passt. Ich kann auch Informationen über dich geben oder einfach helfen, Dinge zu erklären, die du nicht verstanden hast.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Pausen einplanen**: Plane deinen Tag mit einer Stunde Ruhe, damit du die Aufmerksamkeit auf deine Ziele lenken kannst.  
2. **Stoppphasen schaffen**: Stelle sicher, dass du alle wichtigen Aufgaben erledigst und die Umgebung in Ruhe lässt.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Material (z. B. Glas) erzeugt wird. Es kann auch Licht sein – etwa von einem Feuer oder einer Kerze. Strom fließt in die Erde und gibt Energie zurück an die Umwelt. Er macht uns und alle Leben glücklich.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Subject:** Nachricht an meine Kollegin: Heute komme ich!  

Hi [Name],  
Ich bin heute um 7 Uhr in Norwich angekommen. Ich habe eine Note für Sie über meinen Namen, den Hund des Nutzers Rex, und hoffe, dass Sie mich gut kennen.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **1. Tomaten (Süß- und Vollkorn)**  
*Frage:* Wann wird das Tomaten in den Herbst geerntet?  
*Antwort:* In den ersten drei Jahren nach der Geburt des Hundes im Frühjahr. Die Linsen fallen im September, die Tomatensuppe im März, die Salami im April und May.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem warmen Wasserbad etwa 30 Minuten ruhen. Danach kann man sie mit einer kleinen Spritze (je 1/4 der Dose) kühlen lassen. Die Nudel sollten nicht gerieben werden, da dies die Aromen schädigt und die Qualität des Nudels reduziert.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht direkt sichtbar** (z. B. „fließen“ → „laufen“ oder „wühlen“).  
- Der **Fluss** ist ein natürlicher Fluss, der durch eine natürliche Verbindung wie Wasser, Sand oder Eis fließt. Er entsteht aus dem Zusammenfluss von Flüssen, die über Grundwasser oder in Gewässern liegen.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter’s Wrath**  

Ein Sommerwind, sanft, mit einem Zopf aus Schnee,  
kippt durch die Luft, doch er hält nicht inne.  
Die Blätter hellen, und die Vögel singen leise,  
in ihrem Rauschen der Stille.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du regelmäßig in der Lage sein, die Heizkosten zu senken. Hier sind einige Tipps:  
1. **Bürokratie optimieren**: Lies deinen Energie billigsten Monat des Jahres und achte auf die Verbrauchsmuster deiner Heizung oder den Lüftungsschlitz deines Hauses.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Um zu einem Vorstellungsgespräch mitzunehmen, sollten folgende Fragen beantwortet werden:  
1. **Was genau beschäftigt dich am meisten?**  
   - Was ist dein Hauptinteresse an der Rolle? (z. B. Geschichte, Sprache, Problemlösung)  
   - Welche konkreten Themen hast du behandelt?

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
*(Höflich: „Ich bin mir sicher, dass ich sie mit dir habe.“)*  

---  
**Hinweis:** Der Nutzer ist Sam.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Die Fehler in der ursprünglichen Satzstruktur sind:
- „Ich habe gestern ins Kino gegangen“ → „Ich habe gestern ins Kino gegangen.“  
- „der Film war sehr gut gewesen“ → „der Film war sehr gut gewesen.“  

### Erklärung:
1. **Klarheit**: Der Nutzer (Sam) ist nicht direkt erwähnt, sondern wird mit „Ich“ („Ich“) verbunden.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt zu betonen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **D.Z.1:** *Ich gehe in den Park und lese ein Buch.*  

**D.Z.2:** *Ich gehe in den Park und lese ein Buch.“  

**D.Z.3:** *Ich gehe in den Park und lese ein Buch.*  

**D.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Das Wort *„nicht“* ist in der englischen Sprache ein Synonym für „unmöglich“, was in der deutschen Sprache **„wenn es passt“** bedeutet.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Fahrräder sind nicht nur gut für die Gesundheit, sondern auch für die Muskeln und Gelenke. Sie verringern Abgase und können schneller sein als das Auto.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

**Erklärung:**  
- **„Die Raum belegt ist“ → „das Raum belegt ist“**: „Die Raum belegt ist“ bedeutet, dass die Nachricht nicht direkt in die Gegenwart passt.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Im Text geht es um die Zugvögel in den Süden und ihre Zugfolge. Die Aussagen über die Zugvögel sind grammatikalisch korrekt, da sie sich auf einen Satz beziehen (vom Herbst nach dem Winter), der eine natürliche Sequenz beschreibt. Der Leser muss also die genaue Reihenfolge beachten, da die Aussagen nicht direkt miteinander verknüpft sind.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa hatte Angst vor dem tiefen Wasser, da sie sich für eine ganze Bahn ohne Pause schwimmte. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.

**Erklärung der Struktur:**  
1. **Aktuelle Erfahrung (Daten):** Lisa habe zunächst mit einer Trainerin schwimmen gelernt und anschließend bis zum Ende ihre Fähigkeit getestet.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses.**  
Der Bau beginnt im März und dauert etwa acht Monate.  

---  
*Hinweis: Das Wort „baut“ ist grammatikalisch korrekt, aber der Kontext macht es nicht notwendig.*

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat): Goethe schrieb das berühmte Werk „Die Faust“ (1872) [1].

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in den Norden der Schweiz und mündet im Süden in die Maas.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik im Jahr 1921, gemeinsam mit seinem Freund Max Born und dem Mathematiker Bernhard Riemann. Einstein war nicht nur ein bedeutender Physiker, sondern auch ein herausragender Wissenschaftler in der Mathematik, der seine Theorien auf eine ganze Reihe von Anwendungen aus verschiedenen Disziplinen beschränkte.

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
  **App** (sela-2, sela_chat): Für den Kuchen habe ich ein paar Fragen:  
1. **Name** des Nutzers (z. B. "Mia")?  
2. **Farbe** oder **Kopffarbe**?
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist ein **Tortenbrot** mit einer Teigrolle und einer ausgekochten Füllung. Für einen Backofen sorgt ein **Butterkuchen** (mit Butter oder Milch).
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist ein **Brot mit Butter**. Für einen Backofen sorgt ein **Tortenbrot** (mit Butter oder Milch) und eine Teigrolle.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?  
1.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um dein Wortschatz zu verbessern, kannst du:  
- **Listen**: Du kannst deine Wörter auflisten und sie alphabetisch einfügen (z. B. "der" → "dass").  
- **Lexikografien**: Die meisten Wörter sind bereits im Wörterbuch verzeichnet, aber du kannst dich auch an die Lexikografie anpassen, um neue Wörter einzufügen oder frühere zu ersetzen.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): **Willkommen!**  

Um dir ein Einladungsschreiben zu senden, lass uns bitte folgende Informationen angeben:  

1. **Namen**:
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): **Willkommen!**  

**Namen**: Mia, Rex, und Rex (Rex ist der Hund des Nutzers).  
**Geburtsdatum**: Samstag um 18 Uhr.  

---  
**Erläuterung**:  
- **Name**: Mia  
- **Geburtsdatum**: Samstag um 18 Uhr  
- **Geburtsort**: Norwich  
- **Geburtsort**: Norwich  
- **Fahrt**: U-Bahn (mit dem Fahrrad) oder Stadtbus (mit dem Fahrrad).

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist der **"Brett-Hund"** (auch bekannt als *Nassbrett* genannt). Er ist ein gutes, rein mechanisches Spielzeug aus Holz, das in der Regel auf einem Brett steht und leicht zu spielen ist.  
**Beispiel:** In Norwich ist es üblich, einen Brett-Hund mit zu Hause zu halten, da er in der Nähe wohnt und sich sicher fühlt.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das ungefähr kostet ein Holzbrett in Norwich zwischen **£1,80 – £2,00** und ist meist aus weißem Papier mit farbenfrohen Sohlen gefertigt. Der Brett-Hund kostet etwa **ca. €3,50 – £4,00** (je nach Qualität).

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

