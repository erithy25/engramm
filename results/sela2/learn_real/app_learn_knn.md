# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T18:18:01Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 0 von 100 |
| identity_error | 0 von 100 |
| echo | 0 von 100 |
| cut_off | 1 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| error | 0 von 100 |
| prompts_with_a_problem | 1 von 100 |

Antworten nach Modell: {'engramm': 21, 'sela-2': 96}; nach Art: {'about': 1, 'answer': 3, 'learned': 4, 'sela_chat': 89, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 3 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat, 2 Versuche): Hi! I'm a dog owner. Rex lives with me. The user's favorite food is lasagna.

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
  **App** (sela-2, sela_chat): It was great to hear from you!

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): No, goodbye is not a good idea.

Goodbye is not the most appropriate response in this case. The user has already said that they have to go and so does Rex. If you're going with Rex again, you should say "Goodbye" and not "Goodbye" or anything else.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a small offline assistant who lives in Norwich, England.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 3 Versuche): I enjoy listening to your stories and sharing them with you. If you have any questions or need help, feel free to ask!

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I'm sorry, but I don't have access to your personal details or data. My role is to help you with questions and answers about computer science, programming, and related topics. If you'd like, I can assist with creating educational materials, such as articles or tutorials, on any topic you're interested in.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Get a good night's sleep.
2. Take regular breaks and stretch.
3. Avoid overcommitting yourself.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): If you're using a microwave, the answer is to use a food processor or a cooking spray. For this recipe identified in your question, I'll need one for reference.

1. Measure 1 cup of water (or another liquid) and add it to the microwave.
2. Heat the water until it starts boiling.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible piece of software that can delete files, change settings, or even infect other computers. It's kind of like a bug in the system that gets out of control and makes it hard for the user to use their computer.

A computer virus can be made up of many different parts, but one common thing they all share is they usually try to replicate themselves on other computers or networks.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): How are you doing? I've got some plants that need watering right now. Can you water them today, or tomorrow? Also, do you have any advice on how to care for your plants, like a sprayer or a watering can?"

I would like to add a bit of warmth and friendliness, such as: "Oh, sorry about the watering - I just need to pick up some soil and let it dry out a bit before I start watering again."

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Watermelon
2. Carrots
3. Apples
4. Sweet Potatoes

High in vitamin C are apples, watermelon, carrots, and sweet potatoes.

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two related but distinct concepts. **Climate** refers to the long-term patterns of atmospheric conditions that exist over a period of time, such as temperature, precipitation, wind speed, and humidity. It is a more general term that encompasses all aspects of the Earth's climate system, including precipitation patterns, wind direction, and the movement of air masses.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The chill of autumn's first leaves,
Lying in a tangle of amber,
Scattered and crimson like the sky.
Aerial laughter spills from branches,
As the air is filled with the scent of fireflies.

The trees sway gently in the wind,
Their leaves rustling softly as the breeze stirs.

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
1. The Loud Owl - Located in Norwich, England.
2. The Library Tree - Near the library.
3. The Librarian's Cupboard - Near the library.
4. The Book Store - Located in Norwich, England.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): I will give you a 20-minute workout plan. Here it is:
1) Start with an easy soybeans or green beans workout. These are good for the legs and can be done in 1 minute. I recommend doing them in front of a mirror to get a better view. 2) Do the calf muscles first.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You'll need a tent, sleeping bags, and camping stove. You can also pack some cooking gear like a camping grill or a camp cooker. Bring your own clothes for the trip, as well as plenty of water, food, and a first-aid kit. It's also a good idea to bring a backpack with essentials like sleeping bags, water bottles, and a map.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark expanse that stretches out from the shores of Europe to the North Atlantic Ocean, where it meets the waters of Asia and Africa. It is the world's largest body of freshwater and covers an area of about 11 million square kilometers, with depths of over 1,500 meters and surface areas of more than 2 million square kilometers.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): To politely decline an invitation to a party, you can follow these steps:

1. **Be clear and direct**: Clearly state that you're unable to attend the party due to scheduling conflicts or other reasons.
2. **Reiterate your reasons**: Offer alternative ways to attend the party, such as attending another event or meeting someone else for dinner.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text: "Send me the report now."

I removed the phrase "now" because it's not necessary in this context. If you want to emphasize that the report has already been sent, you could say: "Send me the report now." I also changed the sentence structure to make it more concise and direct.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): The sentence can be simplified to: "Public transportation improves urban congestion."

This version conveys the same information in a more direct way, eliminating unnecessary words and phrases. The word "utilisation" is replaced with "improvement", which is a more precise and active term for public transportation. The phrase "a reduction in urban congestion" is also shortened to "urban congestion", making it more concise and easier to understand.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct correction for the sentence is: "She doesn't like going to school on Mondays." 

Note that "mondays" should be spelled as "MONDAY," not "monday," because "MONDAY" is a day of the week, while "MONDAY" is a month.

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

The past tense is used when describing a completed action. For example, "I walk to the station and buy a ticket." Here, the verb "walked" is in the past tense. In the sentence, "to the station" is the completed action that happened before the completion of walking.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "We're opening up our shop this weekend, so we want to make it even more exciting! We've got a sale going on this Friday and Saturday, so come on over and grab a glass of our famous lasagna. Who can't try the new recipe?"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): How many o'clock is the train currently leaving?

The train leaves at eight o'clock.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): **Subject:** Request for Assistance with Writing an Argumentative Essay

Dear Mr. Smith,

I am writing to express my sincere regret for the delay in completing my essay due to your inability to meet certain requirements. I understand that this is not a personal issue, but I am concerned about the quality and relevance of my argument, which is based on evidence from a recent survey.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we made the decision to stay indoors."

I removed the phrase "Due to" as it makes the sentence longer and doesn't add much meaning. I also changed "very heavily outside" to "heavy rain outside" to make the language more concise and natural-sounding.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize) – cut_off
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made the following changes to improve clarity and grammar:

- Changed "will be" to "will be" (correct verb form)
- Added an article ("the") before "sreptea" to make it plural
- Changed "reopen on Tuesday" to "reopen on Tuesday" to correct the possessive form
- Removed the comma after "due" as it's not necessary in this context, but in many cases, a comma helps with clarity
- Changed "it will" to "it will" (subject-verb agreement) and "can" to "can" (possessive form)
- Changed "Books that are due" to "books due" (correct verb form)
- Changed "The library" to "The library" (subject-verb agreement)
- Changed "The user" to "The user" (correct subject-verb agreement) …

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This is a short summary of the user's life. The information about his hobby, family, and past experiences helps to give a sense of what the user enjoys doing.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The user's email is: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

Here's a brief summary of the message:

*   Project meetings are held on Wednesday at 2 p.

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
  **App** (sela-2, sela_chat): If you're visiting Rome, I'd recommend starting with the Colosseum. It's one of the largest amphitheaters in the world and it's always a crowd-pleaser. Rome has so much to offer, from ancient history to modern art and architecture. Plus, it's a great place to see the Vatican City.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): The best Italian cuisine is all about fresh ingredients and local specialties. You can find a lot of great food in Rome, from pasta dishes to pizza, but you'll also want to try some of the regional specialties like risotto, tiramisu, and paella. Don't miss trying some authentic pizza made with mozzarella cheese or figs – it's a staple in Italy!

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here's a birthday card for your mother:

1. **birthday simple**:
2. **Happy Birthday to Your Mother!**
3. **Birthday Song**: "Happy Birthday" by The Beatles.
4. **Celebrate with Love and Light**: A bouquet of flowers, balloons, or cards with her name.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter birthday card for your mother:

1. **Happy Birthday to Your Mother!**
2. **Birthday Song**: "Happy Birthday" by The Beatles.
3. **Celebrate with Love and Light**: A bouquet of flowers, balloons, or cards with her name.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): I can't help you feel stressed, but I can offer some suggestions to help manage your emotions and stress. 

1. **Take a break**: If you're feeling overwhelmed by stress, consider taking a short break in nature or engaging in a hobby that brings you joy. This can help calm your mind and body.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): There are many ways to relax this evening. Here are a few suggestions:

1. **Take a walk**: If you have a garden, try taking a walk outside and enjoying the fresh air. This can help reduce stress and boost your mood.

2. **Take a short nap**: A short nap can be just what you need to recharge before diving back into your day.

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
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found something you enjoyed. Just be sure to prioritize your reading time and stick to it, even if it's just for a few minutes at a time each day.

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
- 3/4 cup red onion, chopped
- 2 cloves garlic, minced
- 1/4 cup mozzarella cheese
- Salt and pepper to taste
- Fresh basil or parsley for garnish

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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den Nutzer deiner Wahl (z. B. Sam oder Rex), und etwas über dich ein. Dann kannst du mich bei deiner Suche nach Produkten, Tipps oder Tricks unterstützen. Lass uns gemeinsam lernen – die Welt ist voll von kleinen Schritten!

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Morgen frühzeitig schlafen** – schlafen Sie morgens um 7:00 Uhr oder später am Tag, wenn es kalt ist.  
2. **Kein Koffein** – keine Snacks, aber viel Wasser und Obst trinken.  
3. **Tagesmorgen eine Stunde lang einschlafen** – zum Beispiel bei der Arbeit, um Energie zu sparen.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Material (z. B. Glas) erzeugt wird. Es kann auch Licht sein (was für Menschen als Beleuchtung genutzt wird).

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Subject:** Nachricht an meine Kollegin, dass ich heute später komme  

Hi [Name],  

Ich freue mich auf eure Rückmeldung. Ich bin heute um 12:30 Uhr nach Norwich gefahren und habe dann keine Zeit mehr gehabt, den Hund zu beobachten.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **1. Tomaten (Lösungen, nicht Namen):**  
- *Saffron-Blüte* (Kartoffel)  
- *Mais-Blüte* (Aprikosen)  
- *Zimt-Blüte* (Chicharrón)  
- *Salz-Blüte* (Rauchsalat)  

**2.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem warmen Wasserbad gebacken werden. Für die richtige Nudelgröße und den richtigen Zeitpunkt gibt es zwei Möglichkeiten:

1. **Wenn Sie eine Nudel mit einem Durchmesser von etwa 1 cm (ca. 5 Zoll) haben**  
   - Wenn das ich dafür benötige, müsste ich heute einen Durchmesser von etwa 3 cm (ca.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht direkt sichtbar** (z. B. „fließen“ → „laufen“ oder „wühlen“).  
- Der **Fluss** ist ein natürlicher Fluss, der durch eine Fläche fließt, die nicht von Wasser umgeben ist. Er entsteht aus dem Zusammenfluss von Flüssen, Fließgewässern und Uferbänken.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter:**  
Der Schnee, der im kühlen Frühling ein Herz schlägt,  
Die Erde schmerzt vor dem Frost.  
In den Wäldern, wo das Licht die Schneehöhen trennt,  
Schneide ein einem Geheimnis gleitet.  

**Nacht:**  
Ein Feuer in der Nacht, ein sanfter Sturm,  
Die Bäume blitzen wie Sterne im Herbst.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, ist es sinnvoll, die Verbrauchsgüter und Dienstleistungen in den Haushalt einzubeziehen. Hier sind einige Tipps:  
1. **Kostenlose Stromausrüstung**: Für Kraftfahrzeuge oder Haushaltsgeräte ist es entscheidend, den Kraftstoffverbrauch zu reduzieren. Nutze oft Recycling-Programme wie das "Energy Star"-Verfahren für Fahrzeuge.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Um zu einem Vorstellungsgespräch mitzunehmen, sollten folgende Fragen beantwortet werden:  
1. **Was genau beschäftigt dich am meisten?**  
   - Was ist dein Hauptinteresse an der Rolle? (z. B. Geschichte, Sprache, Problemlösung)  
   - Welche konkreten Themen hast du behandelt?

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
*(Höflich: „Ich bin sofort auf dem neuesten Stand.“)*  

**Hinweis:** Falls du einen Fehler in der Antwort kennst, kann ich dir das korrigieren oder eine andere Lösung anbieten.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat, 2 Versuche): **Korrigierter Text:**  
„Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen. Ich habe in Norwich gelandet, was mir sehr gefällt hat.“  

**Erklärung:**  
- **"ins Kino gegangen" → "in Norwich gelandet" (falls es passt)  
- **"seine geliebte" → "seine Lieblingsgespräch" (falls es passt)  
- **"und der Hund des Nutzers" → "was mir sehr gefallen hat" (falls es passt)  

**Beispiele:**  
- **"einfach ins Kino gegangen und..."

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt zu betonen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Ursache:** „Ich gehe in den Park und lese ein Buch.“  
**Vergleich mit:** „Ich lese ein Buch.“  

Der Satz ist in der Vergangenheit entstanden.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Das Wort *„nicht“* ist in der englischen Sprache ein Synonym für „unmöglich“, was in der deutschen Sprache eine andere Bedeutung hat. Der Nutzer muss sich daher vor dem Schreiben auf die korrekte Schreibweise verlassen.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Fahrräder sind nicht nur gut für die Gesundheit, sondern auch für die Muskeln und Gelenke. Sie verringern Abgase und können schneller sein als das Auto.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Im Text geht es um die Zugvögel in den Süden und ihre Heimzugstrategien. Die Aussage, dass sie sich oft Tausende Kilometer ziehen, wird als **Zugvogel-Übertragung** verstanden, was auf eine **gesamte Migration** von Zugvögeln hindeutet. Gleichzeitig ist die Beschreibung der Vögel als **Brüten-Erfolge** für den Herbst wichtig.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst in Angst vor dem tiefen Wasser, später fühlte sie sich durch eine Trainerin angezogen. Nach einem Sommer schwamm sie mit einer Trainerin, doch die Situation ebbte nach dem Sommer an. Die Trainerin brachte schließlich eine ganze Bahn ohne Pause zum Ziel, und Lisa begann wieder zu schwimmen.“

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses.**  
Der Bau beginnt im März und dauert etwa acht Monate.  

---  
*Hinweis: Das Wort „baut“ ist der korrekte Begriff in diesem Kontext, da es um die Konstruktion von Straßen, Brücken oder anderen Infrastrukturen geht.*

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
  **App** (sela-2, sela_chat): Der Hund ist Rex, der immer da ist.  

**Erläuterungen zu den Sätzen:**  
Der Nutzer (Mia) sagt, er habe den Kuchen aus dem Kühlschrank gezogen.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist ein Brot.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Ich freue mich auf den Kuchen!

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?  
Was möchtest du wissen?
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Hier sind einige Tipps:  
1. **Konsistenz und Übereinstimmung**: Du kannst den Wortschatz auf verschiedene Wörter beschränken (z. B. „Ich lerne gerade Englisch“ statt „Ich lerne Englisch sehr schnell“).  
2. **Präzision und Klarheit**: Vermeide Redundanzen wie „möchtest du“ oder „sollen wir“.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): **Name:** Mia  
**Lage:** Norwich  

**Kontext:** Der Nutzer möchte sich über den Hund Rex informieren, der in Norwich wohnt. Er spricht:  

„Rex ist ein sehr guter Hund, und ich kenne ihn schon seit Jahren. Er hat eine gute Familie, und ich kann ihm bei vielen Dingen helfen, die er braucht.“
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): **Name:** Mia  
**Lage:** Norwich  

**Kontext:** Der Nutzer möchte sich über den Geburtstag des Nutzers informieren, der am Sonntag um 18 Uhr in Norwich wohnt. Er spricht:  

„Der Geburtstag ist ein großer Tag für uns alle! Ich freue mich darauf, dass Rex noch gesund und glücklich ist.“

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist ein Spaziergang mit dem Hund Rex. Er hat eine hohe Energie und kann sofort starten, wenn es kalt wird.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet zwischen **$10–€20** und sollte in der Regel mit einem gut ausgeleuchteten Wetterkanal ausgeführt werden. Es ist immer wichtig, dass du auf deine Bedürfnisse achten und schlafen kannst, bevor du einen Spaziergang unternimmst.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

