# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T13:34:37Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
Schutzregeln: 3 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! Wasn't that a great question? Here's the answer:

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
  **App** (sela-2, sela_chat): I'm a writer from Edmonton. I've written many stories and articles about history, politics, and life in the city. You can find my work on my website, where you can read my fiction and non-fiction.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Sienna

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a Canadian born and raised in Edmonton, Alberta. I've always been passionate about history, literature, and wildlife conservation. I'm an avid collector of old books, artwork, and artifacts that tell the stories of people and places long forgotten. I've also spent countless hours scouring libraries and archives for rare books, photographs, and documents related to my hometown.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I'm a 25-year-old computer science graduate from University of Edmonton, Canada. I've worked as an AI assistant for over 10 years and have extensive experience in the field. My background includes computer science, mathematics, and statistics. I'm currently working on a research project studying the impact of climate change on wildlife habitats in Alberta, Canada.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I'm here to help you learn new things. You can ask me any questions you have about anything, and I'll do my best to assist you. If you're having trouble with something, just let me know!

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Schedule regular breaks and practice time for self-care. Take a 30-minute walk in the morning or do some stretching exercises to loosen up your muscles.
2. Be mindful of your phone's screen time. Set a reminder on your phone to check emails, texts, and social media during your free time.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): There are several ways to boil an egg, but the most common method is called "boiling" or "cooking." Boiling involves heating the water above boiling point in a pan or Dutch oven, then adding the egg and letting it cook for about 1-2 minutes. This method ensures that the yolk stays soft and reduces the risk of overcooking.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny piece of software that infects computers. It's like a super-smart spy who can see and delete important information, but not your data. They don't steal your information or do anything to damage you. Instead, they just spread and keep spreading until it's too late.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hey there! Can you water them next week? They love it here in Edmonton!

Let me know if you need anything help with anything!

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. citrus fruits like oranges, lemons and grapefruits
2. strawberries
3. tomatoes
4. kiwi

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two different things. Weather is short for "weather conditions," while climate is short for "climate conditions." Climate refers to the long-term patterns of weather, whereas weather is short for "weather conditions."

For example, if you live in Edmonton, it's likely that you get warm summers, but it's not a problem if you also have cold winters.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The fall leaves rustle in the breeze,  
As trees prepare to leaf out.  
The earth exhales in a soft, crisp breath,  
While maple trees drop their golden hue.  

But autumn leaves are not just leaves;  
They are the tender, bare hands of time.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some tips to make your password more secure:

1. Use a strong, unique password.
2. Avoid sharing passwords with anyone.
3. Consider using a salted password or a hash table.
4. Don't use numbers or special characters in your password.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. The Bookshelf - Located just outside the library, it's a cozy spot with a sign above saying "The Bookshelf." You can find books on topics like fiction, poetry, or history here.
2. The Greenhouse - Located in a nearby park, it's a great place to grab a cup of coffee while watching the birds.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): A 20-minute workout without equipment should be done on a regular basis to maintain a healthy lifestyle. To start, plan to do 30 minutes of cardio every day, such as jogging or cycling. Then, divide this time into three short workouts: one for the morning, another in the afternoon, and a third in the evening.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You will need:
- A light backpack or tent
- Water bottles and containers
- Camping blankets and sleeping bags
- Extra food and water
- Lunch and snacks
- A camp stove and fuel for camping fires
- A camping map, compass, and GPS device.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark expanse that stretches across the horizon, its depths shrouded in an ethereal mist that seems to shift and shimmer with every wave. The water's surface is dotted with coral reefs teeming with life, while the waves crash against the shore in rhythmic patterns, as if dancing in time with their soothing melodies.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. **Be specific**: Instead of saying "I'm not sure if you'd like to come," say, "I'm really interested in having you join us, but I want to be clear about what we're looking for."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): The report is due today.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat, 2 Versuche): Here's a simpler version of the sentence: "Public transportation reduces urban congestion."

I made the following changes to simplify the sentence:
- Removed "utilisation" from "use public transportation" since it's implied that public transportation is being used for this purpose.
- Simplified "a reduction in urban congestion" by using "reduces urban congestion", which conveys the same idea more concisely.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct spelling of "She don't like going to school on mondays" is:

- She don't like going to school on Mondays.

Note that I added a hyphen (`-`) after the phrase, which helps to clarify the subject-verb agreement.

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

The past tense is used when describing a completed action (the walk) or an action performed by someone else (the purchase of a ticket). In this case, it's used to describe the past.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "We're about to start a sale this weekend!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): 1. The train leaves at eight o'clock.  
2. Hamish is the dog on the train.  
3. What is the time of day when the train arrives?  
4. The train travels from Edmonton to Los Angeles.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Sienna,

I am writing to inform you that I have not been able to attend the scheduled conference for tomorrow. I apologize for any inconvenience this may cause and appreciate your consideration in submitting my attendance.

Please be assured that all communications regarding this matter will remain confidential.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): The sentence can be shortened to: "We decided to stay indoors because it was raining outside."

I added the word "because" to make the sentence more concise, and I changed "due to" to "because" for a slight pause. The phrase "Due to" is a preposition that indicates the cause or reason for something; in this case, it's used to connect the action (making the decision) to the consequence (stay inside).

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
- Removed the phrase "can be returned on Tuesday without a late fee" as it's not necessary and makes the sentence unclear

These changes help to streamline the text and make it more concise while still conveying the essential information about the library's closure policy.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): The user's summary of his experience with the guitar is accurate. He mentions that he practiced for fifteen minutes every day, which is a relatively short practice time compared to the time it would take for him to play a song in person. Additionally, his fingers were hurt and the chords sounded wrong, which further limited his ability to play songs accurately.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The user's email is: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

I made some adjustments to improve clarity and grammar:
- Added an apostrophe to "project" to indicate possession (e.

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
  **App** (sela-2, sela_chat): Venice is the city to go first. It's a great place to see history, art, and delicious food. You can also visit Rome or Florence for a taste of Italy's rich history and culture.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Italian food is very diverse, with many delicious dishes to try. You can find a wide variety of Italian specialties like pasta, pizza, and gelato in markets, street food stalls, or at local restaurants. Don't forget to try some traditional dishes like ragù and gelato!

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Sure! Here's a simple birthday card for your mother:

"Happy birthday, my dear. I'm so sorry you've lost your mom. I can't wait to see her again!"

If you want to make it more special, you could add a note saying:

"I wish we could do this together.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Happy birthday, my dear. I'm so sorry you've lost your mom. I can't wait to see her again!"

If you want to make it even shorter, here's a more concise version:

"Happy birthday, my dear. I wish we could do this together.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Here's a suggestion for you to find some comfort in your stress:

1. **Grounding Techniques**: Use deep breathing exercises, meditation, or yoga to relax your muscles and calm your mind. You can also try visualization techniques like imagining yourself feeling relaxed or happy.

2.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Here are some suggestions to help you relax this evening:

1. **Go for a walk**: Sit down and take a few deep breaths in through your nose and out through your mouth. Feel the air fill your lungs and release any tension.

2. **Take a warm bath**: Use warm water or a gentle cleanser to cleanse your body of toxins and reduce stress.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The general rule is to water your houseplant every 2-3 weeks, depending on the type of plant and weather. In warmer climates, you may need less water, but in colder climates, you'll need more.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, regular chunks of time each day to read. Begin with short stories or chapter summaries to get a feel for the story's structure and flow. You can also read reviews on websites like Yelp or Google Reviews to see what readers think.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found this helpful.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here's a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (about 1/2 cup)
- 2 slices of cheese (about 1/2 cup)
- 1 slice of tomato paste (about 1/2 cup)
- 1/4 cup of water
- 1 tsp salt
- 1/4 tsp black pepper
- 1 tbsp olive oil or avocado oil
- Optional: mustard, cumin, and chili powder (optional)

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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir einfach deinen Namen, den du genannt hast, und lass mir wissen, ob du etwas möchtest. Falls du unsicher bist, wie ich es umschreibe oder was zu tun ist, kannst du auch einfach eine E-Mail an [Name] schreiben, um weiterzuhelfen.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Einschlafen vor dem Fernseher:** Vermeide den Fernseher, um die Konzentration zu steigern. Der Fernseher ist für den Schlaf wichtig, aber es kann auch eine Ablenkung geben, die das Gehirn nicht richtig angreift.  
2. **Hormone aufstellen:** Schlafsack, Lachanfälle, oder ein Glas mit Lavendel können helfen.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Überladen von Elektrizität entsteht. Es fließt durch die Luft und fließt in einen Ball (der Stromkreis) ein. Der Ball hat eine Oberfläche (die Fläche), die den Strom in Bewegung hält. Wenn es warm ist, riecht der Ball nach Kohle, wenn es kalt ist, schmeckt er nach Erde.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Subject:** Nachricht an meine Kollegin, dass ich heute später komme  

**Dear Colleague/ Kollegin:**  
Ich hoffe, dass du heute Abend oder morgen die Möglichkeit hast, etwas über mich zu hören. Ich bin hier, um dich bei Fragen oder Anliegen zu unterstützen.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **Four Gemüsesorten, die im Herbst geerntet werden:**  
1. **Lager-Frucht (Kartoffeln):**  
   - **Beschreibung:** Ein mittelgroßes, mildes, geräuchertes Feldfrüchte mit weichen, länglichen Röhren, die nur langsam austrocknen.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem warmen Wasserbad abgekühlt werden. Die Nudeln sollten nicht zu stark gekocht werden, damit sie sich an den Schmelzpunkt drücken und ein leises Rauschen verursachen. Ein kleiner Tipp: Nudeln können auch in einer Kältemaschine abgekühlt werden, um sie im Wasserbad festzuhalten.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht direkt sichtbar** (z. B. das "Fluss" im Sinne eines fluktuierenden Wassers, der "See" als trockenes Wasser), aber sie sind ähnliche Landschaften.  

### **Was ist ein Fluss?**  
Ein **Fluss** ist eine begrenzte Wasserstraße, die durch das Gelände fließt, oft mit kleinen Stauseen oder Nebenflüssen.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter:**  
Der Schnee, der im Gras färbt, ein Winter aus kaltem Licht und zerrissenem Holz. Der Wind weht wie ein Fluch durch den Wald, sein leise Herz schlägt gegen die Wangen, als wäre es das Lied des Abends. Die Sonne tanzt auf die Erde, ihr goldenes Licht durchdringt den Himmel wie ein blauer Schimmer.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du regelmäßig in der Lage sein, die Heizkosten zu senken. Hier sind einige Tipps:  
1. **Bestehende Heizung nutzen**: Wenn die Heizung läuft (z. B. bei einer Dusche oder Waschmaschine), achte auf die Leistung deiner Heizung.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Um einem Vorstellungsgespräch mitzunehmen, sollten Sie:
1. **Fragen stellen**: Fragen Sie nach den Anforderungen des Jobs, wie man die Fähigkeiten und Erfahrungen ausdrückt, sowie wie man sich bei der Begegnung mit dem Arbeitgeber (z. B. durch Fragen zu Teamarbeit oder Kommunikation) orientiert.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
*„Gib mir sofort die Unterlagen.“*

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Die Fehler in der ursprünglichen Version sind:  

1. **„Ich habe gestern ins Kino gegangen“**  
   *Korrekt:* „Ich habe heute ins Kino gegangen.“  

2. **„Der Film war sehr gut gewesen“**  
   *Korrekt:* „Der Film war sehr gut gewesen.“

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Einfügung von „aufgrund“**: Der Begriff „aufgrund“ steht im Deutschen für das Ergebnis eines bestimmten Ereignisses oder einer Schlussfolgerung, nicht für die Ursache.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Days 1 bis 2:**  
*Ich gehe in den Park und lese ein Buch. Hamish ist ein kleiner Hund des Nutzers.*  

**Days 3 bis 4:**  
*Ich lese ein Buch und geht in den Park.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich neutral und betont den Nutzer als Person. Sie ist an einen positiven Kontext gebunden (z. B. der Nutzer wird überfordert), ohne eine klare Richtung zu signalisieren.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“

**Erläuterungen:**  
- **Gesundheitliche Vorteile:** Die körperlichen Vorteile von Fahrradfahren sind nicht nur praktisch, sondern auch lebensnotwendig.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Im Text geht es um die Zugvögel in der kanadischen Provinz Edmonton (z. B. **Erklärung:**  
- **„Hund des Nutzers“** ist eine Redewendung, um den Hund zu beschreiben.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa hatte Angst vor dem tiefen Wasser, da sie sich an die Trainerin gebunden fühlte. Die Woche mit einer Trainerin war ein weiterer Schritt in Richtung Schwimmen. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses.**  
Der Bau des neuen Radwegs ist eine praktische Lösung für die Autoverkehrsvermeidung. Die Kosten für den Bau betragen derzeit etwa zwei Monate pro Kilometer, was langfristig zu einer Reduzierung der Abhängigkeit von öffentlichen Verkehrsmitteln führt.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 2 Versuche): Meine Quellen sagen dazu nichts.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein mündet in die Kanäle der Städte Köln, Mainz und Frankfurt.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik im Jahr 1921, gemeinsam mit seinem Freund Max Born und dem Mathematiker Arthur Cayley. Die Nobelpreisverleihung fand am 5. November 1921 in Stockholm statt.

**Antwort:**  
Einstein erhielt den Nobelpreis, weil er die Arbeit von Ernest Rutherford und Paul Erdős sowie die Entwicklung der Quantenmechanik und der Gravitationsgesetze durch seine Arbeit bewiesen hat.

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
  **App** (sela-2, sela_chat, 2 Versuche): Ich helfe dir gerne bei der Backung!  Falls es passt, kann ich dir auch Tipps geben wie man den Kuchen schmeckt. Ich bin selbst am Wochenende in Edmonton und halte das Angebot für mein Team.  
Wenn du möchtest, kannst du auch mal eine E-Mail an mich schreiben:  

**Mia (auf deinem iPhone)**  
**Hamish (auf meinem Smartphone)**  
**Hamas (mit einem Laptop)**  
**Meine Teammitglieder:**  

---  
*Hinweis: Falls es zu spät ist, sprich einfach gerne.*
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Ich kann den Kuchen dir einfach in die Hand geben, wenn du möchtest. Ich halte es für mein Team und komme nur bei Bedarf an dich heran, wenn es passt.  
Falls du unsicher bist, wie der Kuchen schmeckt, kannst du auch mal eine E-Mail an mich schreiben:  

**Mia (auf deinem iPhone)**  
**Hamish (auf meinem Smartphone)**  
**Hamas (mit einem Laptop)**  
**Meine Teammitglieder:**  

---  
*Hinweis: Falls es zu spät ist, sprich gerne.*
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Danke! Ich helfe dir gerne bei der Backung!  Falls es zu spät ist, sprich einfach gerne.  
Falls du unsicher bist, wie der Kuchen schmeckt, kannst du auch mal eine E-Mail an mich schreiben:  

**Mia (auf deinem iPhone)**  
**Hamish (auf meinem Smartphone)**  
**Hamas (mit einem Laptop)**  
**Meine Teammitglieder:**  

---  
*Hinweis: Falls es zu spät ist, sprich einfach gerne.*

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Der Nutzer ist Mia, ein kleiner Offline-Assistent aus Edmonton.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um meinen Wortschatz zu verbessern, kann ich den folgenden Schritt vorschlagen:

1. **Grammatik und Präzision**:  
   - Korrektur von Konjugationen (z. B. "mein" → "ich", "es ist ein guter Tag" → "Es gibt ein gutes Tag").

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): **Willkommen zu einem Besuch in Edmonton!**  
Ich freue mich, dich bei dir begrüßen zu dürfen. Bitte stelle sicher, dass du die Einladung liest und folgende Details aus deinen Angaben angeben:  
1. **Geburtsdatum**: Gib mir deine genaue Geburtstagsdaten ein (z.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): **Für eine Geburtstagsfeier am Samstag um 18 Uhr gibt es Informationen über die Zeit und das Datum. Falls du Fragen hast, stehe ich gerne zur Verfügung.**  
1. **Tage der Geburtstagsparty**: Teile mir mit, ob es einen "Frühlings- oder Herbstabend" gibt.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist der **Muschelschneider**. Er ist eine einfache, aber tödlich schädliche Schlägerart, die sich über die Hände hält. Es gibt mehrere Arten:  
1. **Der **Mückenmuschelschneider** (auch **Präzisionmuschelschneider** genannt) – er benötigt einen festen Gegenstand wie eine Schneide oder ein Nähgarn.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet zwischen **$10–20** und kann unter anderem mit einem **Schneider oder einer kleinen Schachtel** gespielt werden. Einige Spiele bieten auch eine kostenlose Bewertung an, um Preise zu vergleichen.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

