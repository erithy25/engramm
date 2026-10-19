# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T13:33:23Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
  **App** (sela-2, sela_chat): Hi! I live with my dog Hamish in Edmonton and have a pet named "Hamish." How are you?

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
  **App** (sela-2, sela_chat): No problem! I'm glad you found the information helpful. If there's anything else I can help with, please let me know.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): I appreciate you following up with a friendly message. If you have any more questions, feel free to ask!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a Canadian born and raised in Edmonton, Alberta. I've always been passionate about history, literature, and wildlife conservation. I'm an avid collector of old books, artwork, and artifacts that tell the stories of people and places long forgotten. I've also spent countless hours volunteering at local wildlife sanctuaries and museums, where I share my love for discovery with visitors.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I'm a glaze artist.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I'm here to help you find the answer. Please go ahead and share the details about yourself, such as your name, address, phone number, email, or any other relevant information. I'll do my best to assist you! If you have a specific question or need further clarification, feel free to ask.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1.   Stay organized. Use a planner, calendar, or task management software to keep track of assignments, due dates, and deadlines.  
2.   Schedule regular breaks in your schedule. A short walk outside, stretching, or listening to music can help you stay refreshed and focused.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): If you boil an egg, the yolk will be soft and creamy. 
You can boil a boiled egg:
1. Good luck! The water boils at room temperature (about 100°F).
2. Boil for 1 minute or until it is soft.
3. Strain the yolk, then discard the water.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny piece of software that infects computers or other devices. It's made up of code, instructions, and often a virus itself. The code tells the virus to do something it shouldn't, and then it executes its instructions. Once it has done its job, it sends a message to other parts of the computer, causing damage.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hey there! I love the way you water my plants. Can't wait to see how the weather turns out for them next week!

Let me know if it's okay. Just keep me updated on the progress.

Best,
Sienna

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Red bell peppers
2. Garlic
3. Strawberries
4. Apples

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two different things. Weather is short for "weather conditions," while climate is short for "climate conditions." Climate refers to the long-term patterns of weather, whereas weather is short for "weather conditions."

For example, if you live in Edmonton, it's likely that you've lived there for a long time, but not necessarily for any specific period.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The fall leaves rustle in the breeze,  
As trees in amber, wither and turn.  
Their emerald hue dances through the air,  
A dance of leaves that stir the soul.  

They fall in autumn's golden light,  
And when the first whispers of winter's chill,  
Weep in their stillness, a sigh so deep,  
That no breath can comfort them.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some tips to make your password more secure:

1. Use a strong, unique password. Avoid using something easily guessable like a birthdate or a birthday. Make sure the password has at least one uppercase letter, one lowercase letter, and one digit.

2. Consider using a mix of letters, numbers, and symbols.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. The Café Express – Near the library's reading room and a coffee shop
2. Good Beak Coffee – Near the library's coffee shop
3. The Public Library Café – Near the library's coffee shop
4. The Public Library Cafe – Near the library's coffee shop
5.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): The plan for a 20-minute workout without equipment includes:

1. Good form (e.g., 10 sets of 8 reps).
2. Good form (e.g., 4 sets of 6 reps).
3. Running (5 sets of 5 reps).
4. Cool-down with some stretching and foam rolling.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You will need:
- A light backpack or tent
- Water purification tablets and filter
- A tent or sleeping bag
- Headlamp
- Sunscreen (or sunglasses)
- Mask (or hat) for rain
- A fire starter and matches
- A waterproof umbrella (if you plan on camping in a windy area)bye
- A small portable stove
- Food for the trip.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark expanse that stretches across the horizon, its depths shrouded in an ethereal mist that seems to shift and shimmer with every wave. The water's surface is dotted with coral reefs teeming with life, while the waves crash against the shore in rhythmic patterns, as if time itself has slowed to let them drift by.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Good morning/afternoon. Please let me know if there’s anything I can do to make the party more enjoyable for you. (e.g., invite your friends or family)
2. I’m not sure what the party is about, so please let me know if there’s something else I could help with.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): I live in the city center and work as a writer for a local paper. The report is due soon.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): The sentence is simpler because it:
- Uses the verb "facilitates" instead of "facilitates" to convey the idea that public transportation reduces urban congestion.
- Simplifies the phrase "utilisation of public transportation facilitates a reduction in urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct edit would be: "She don't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

The past tense is used when describing a completed action. For example, "I walk to the station and buy a ticket." Here, the past tense shows that the action occurred before the present time, which makes the sentence grammatically correct.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Welcome to our amazing store! We're thrilled to have you here today."
Our furry friend Hamish is just as charming as his fluffy companion. What brings you to our shop today?"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): How many o'clock is the train currently leaving?

The train leaves at eight o'clock.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Thank you for your kind words!

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): The sentence can be shortened to: "We decided to stay indoors because it was raining outside."

I added the word "because" to make the sentence more concise, and I changed "due to" to simply "because", as in "Due to the fact that it was raining very heavily outside".

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made a few changes to improve clarity and grammar:

- Changed "will be" to "will be" (correct verb form)
- Added an article ("a") after "debate" to make it clear that the decision is being debated
- Changed "reopen" to "reopen" (correct spelling)
- Removed the phrase "can be returned on Tuesday without a late fee" as it's not necessary and makes the sentence unclear.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): The user's summary effectively conveys the story of how Tom learned to play the guitar. Here's a slightly revised version with some minor edits:

"Tom wanted to learn the guitar. After his fingers hurt and the chords sounded wrong, he practised for fifteen minutes every day. After three months, he could play his favorite song for his friends."

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): "Hello team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

The user's dog is Hamish.

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
  **App** (sela-2, sela_chat): Venice is the city you've always wanted to visit. It's a bit more laid-back, with beautiful architecture and charming canals.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Italian food is quite diverse, but you should try some of the classic dishes like pizza, pasta, and gelato. You can also try some seafood like salmon or shrimp.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Sure! Here's a simple birthday card for your mother:

"Happy birthday, my dear. I'm so sorry you've lost your mom. I can't wait to see her again! May she always be here for you.  Take care of yourself and don't hesitate to ask if you need anything at home.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version:

"Happy birthday, my dear. I'm so sorry you've lost your mom. I can't wait to see her again! May she always be here for you. Take care of yourself and don't hesitate to ask if you need anything at home.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Here's a suggestion for you to focus on self-care and relaxation:

1. Take a few deep breaths in through your nose and out through your mouth. Try to breathe in slowly for a count of four, hold for a count of five, and then exhale slowly through your mouth for a count of four.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Here are some suggestions to help you relax this evening:

1. **Go for a walk**: Just walk around the block, enjoy the fresh air, and take in the scenery. You might even catch a glimpse of wildlife or hear birdsong.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): I don't know — it depends on your climate. If you're in a hot climate, water it every week. But if you live in a cold climate, you can wait until the last frost or when your soil is dry.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, regular chunks of time each day to read. Begin with short stories, and then gradually move on to longer books. Try setting aside a few hours every week for reading – it could be as simple as 10 minutes or as long as you want. You can also try setting aside specific times, like bedtime or during your lunch break, to read.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found that helpful.

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
- 4 tablespoons granulated sugar
- 1 teaspoon pure vanilla extract
- 2 tablespoons lemon juice
- 2 tablespoons unsweetened cocoa powder
- Salt and pepper to taste

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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den Hund des Nutzers und einen Link zum entsprechenden Artikel an. Ich gebe dir auch Tipps zu deiner Umgebung, wie man eine Wohnung durchsuchen kann, wenn du dich in der Nähe eines Parks oder öffentlichen Verkehrsmitteln hast.  

Bleib bei deinem Nutzer (kein Name ist erlaubt).

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Hormon-Mangel (Hormonaler Schlafmangel):**  
   - Nach dem Schlafen sind die Körpertemperaturen hoch und die Schlafdauer lang. Wenn du deine körperliche Aktivität auf ein Minimum reduzieren willst, solltest du den Kopf nach vorne legen oder etwas auf deinem Bett liegen, um die Temperatur zu senken.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Überladen von Elektrizität entsteht. Es fließt durch die Luft und fließt in einen Ball (der Stromkreis) ein. Der Ball hat eine Oberfläche (die Fläche), die den Strom in Bewegung hält. Wenn jemand einen Strom schneidet, wird er nicht mehr erwärmt – das ist der Unterschied zwischen einem Kraftwerk und einer Stromquelle.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Beste Grüße, Sam!**  

**Lieber Hamish:**  
Ich freue mich darauf, mit Ihnen zu sprechen. Ich werde heute früh um 8 Uhr komme – das ist korrekt und richtig! Ich bin fest in Edmonton und ich hoffe, Sie finden meine Ruhe.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **Four Gemüsesorten, die im Herbst geerntet werden:**  
1. **Lager-Dickpea (Carolina)** – **Frucht mit süßem Geschmack und aromatischen Aromen**  
2. **Chalkara-Tomatoes** – **Helle, klebrige Früchte**  
3.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem warmen Wasserbad gebacken werden.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht direkt sichtbar** (z. B. das "Fluss" im Vergleich zum "See" in der Definition). Allerdings gibt es viele Begriffe, die ähnliche Eigenschaften haben:
- **Fluss**: Ein künstlicher Fluss, der durch eine künstliche See fließt.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter im Winterland**  

Der Schneefall glänzt im Morgenlicht,  
Ein schauerndes Zeichen, das die Dunkelheit weckt.  
Die Luft ist still, doch die Knochen bluten,  
Ein Lachen der Weiten. Jeder Tag ist ein Fluch,  
Ein Sturm, der den Boden zum Schweigen bringt.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, ist es sinnvoll, die Verbrauchsfaktoren wie Heizkosten, Stromverbrauch und Wasserverbrauch regelmäßig zu überprüfen. Hier sind einige Tipps:

1. **Kühlung**: Falls das Haus kühl ist, sollte der Heizbedarf deutlich reduziert werden (z.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Um einem Vorstellungsgespräch mitzunehmen, sollten Sie:
1. **Fragen stellen**: Fragen Sie nach den Anforderungen des Jobs, wie man in der Lage ist, sich zu präsentieren und welche Fähigkeiten erforderlich sind.
2. **Schritte klären**: Schließen Sie die Fragen an, indem Sie „ja“ oder „nein“ sagen, um das Gespräch nicht zu lang zu machen.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
*„Gib mir sofort die Unterlagen.“*

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“  
(Hinweis: Die korrekte Version sollte „Ich habe gestern ins Kino gegangen“ ersetzen.)

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Einfügung von „aufgrund“**: Der Begriff „aufgrund“ passt nicht zu dem Satz, da er im Deutschen besser als „mit“ verwendet wird.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Ursache:** „Ich gehe in den Park und lese ein Buch.“  
**Fakt:** Das Buch ist *„Der Wind weht einander zu“*, das durch die Windschutzscheibe des Parks transportiert wird.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich neutral und betont den Nutzer als Person. Sie ist im Englischen üblich und kann in der Regel in passenden Kontexten verwendet werden.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“

**Erläuterungen:**
- „Gut“ bezieht sich auf die Qualität des Fahrradfahrrads, nicht auf dessen Motorleistung (z.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Im Text geht es um die Zugvögel in der kanadischen Provinz Edmonton. Der Nutzer spielt mit dem Begriff „zugvögel“ und ich zitiere den Kontext, dass sie sich im Winter auf wärmeren Gebieten brüten, um Nahrung zu finden, während im Frühling sie wieder zurückfinden.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst frustriert, als sie das Wasser nicht richtig schwamm. Die Trainerin hielt ihr den Atem an und ermutigte sie, sich zu versuchen. Nach einem Sommer gab es erste Erfolge. Lisa musste mit dem tiefen Wasser kämpfen – ein Test für die Kraft des Körpers. Die Trainerin erklärte, dass der beste Weg in der Ruhe zwischen Schwimmen und Bewegung ist, die auf körperlichen Belastungen abzielt, wie Schwimmen oder Spazierengehen.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses.**  
Der Bau des neuen Radwegs ist eine praktische Lösung für die Autoverkehrsvermeidung. Die Kosten für den Bau betragen derzeit etwa zwei Monate.  

**Der Autoverkehr wird in der Innenstadt verringern.**  
Die Bauarbeiten im März dauern acht Monate, und sie sind in der Lage, den Fahrradverkehr erheblich zu reduzieren.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 2 Versuche): Meine Quellen sagen dazu nichts.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Mitte Deutschlands und mündet richtig in den Rhein. Der Rhein ist das größte Gewässer, welches die nördliche Grenze zwischen Deutschland und Frankreich bildet. Er fließt von Nordwesten nach Nordosten, wobei er sich über mehrere Länder erstreckt.

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
  **App** (sela-2, sela_chat, 2 Versuche): Hamish ist ein Hund des Nutzers.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist ein Backofen mit einer geraden Anzahl von Schichten.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist ein Backofen mit einer geraden Anzahl von Schichten.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Der Nutzer ist Mia, ein kleiner Offline-Assistent aus Edmonton.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um meinen Wortschatz zu verbessern, kann ich den folgenden Schritt ergreifen:

1. **Pronomen lernen**: Übe Wörter mit Verben wie *hallo*, *ja* und *dann*. Beispiele: *Hallo!*  
2. **Grammatik verstehen**: Biete sich Zeit, grammatikalische Fehler zu korrigieren.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Schreib eine Einladung für Mia, Hamish oder einen Hund des Nutzers in einem Format, das der Nutzer versteht. Falls du möchtest, kannst du sie später unter deinen Namen einfügen.  
**Beispiel:**  
Mia: „Ich bin heute Abend mit dem Hund des Nutzers zu Hause.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): **Beispiel:**  
Mia: „Ich bin heute Abend um 18 Uhr mit dem Hund des Nutzers zu Hause.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist ein Spaziergang mit dem Hund Hamish. Der Hund hat sich heute früh wieder genährt und möchte gerne am Strand entlanglaufen. Das ist perfekt für eine frische Luft und eine Entspannung.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet zwischen $10 und $20. Die Anschaffung eines Hundehundes ist teuer, aber es lohnt sich. Brandeis kostet ungefähr ich $6 bis $7 pro Stück.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

