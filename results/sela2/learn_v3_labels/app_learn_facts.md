# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T13:06:48Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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

Antworten nach Modell: {'engramm': 22, 'sela-2': 95}; nach Art: {'about': 1, 'answer': 4, 'learned': 4, 'sela_chat': 88, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 2 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! Wasn't that a great question. Can you tell me more about your background?

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
  **App** (sela-2, sela_chat): Good, I'm glad you found my answer helpful.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): I apologize for not being able to help you. Please let me know if there's anything else I can assist with.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I live in a small apartment with my dog Biscuit, who loves to play outside and explore. We have two children together, Max and Emma, and they're the best of friends. My dog Max loves to bark and fetch toys, while Emma is always playing with me and Biscuit.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): Poppy

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity) – cut_off
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of topics and issues, including but not limited to:

- **Personal growth and development**
- **Education and learning**
- **Career and professional decisions**
- **Health and well-being**
- **Social and emotional aspects**
- **Business and entrepreneurship**
- **Technology and digital communication**
- **Creativity and artistic expression**
- **Communication and collaboration**
- **Literature and writing**
- **Personal development and self-improvement**
- **Emotional health and well-being**
- **Travel and travel planning**
- **Marketing and advertising**
- **Financial matters**
- **Business law and regulations**
- **Medical care and treatment**
- **Workplace issues and policies**
- **Legal matters and legal services**
- **Complaints and complaints**
- **General business and industry trends**
- **Government and policy**
- **Marketing and advertising**
- **Social media and online behavior**
- **Data analysis and data visualization**
- **Operating systems and software**
- **Web design and user …

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Schedule regular breaks
2. Take short breaks to rest
3. Use a timer app or a smart phone for accountability
4. Be patient with yourself
5. Be consistent in your work
6. Stay positive and avoid distractions
7. Seek support from family members, friends, or colleagues when needed
8.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): This is a simple recipe that uses the yolk as a binding agent to make the egg soft. The yolk serves as a natural preservative, but it’s best to use it in combination with other ingredients like milk or cream to achieve the desired texture and flavor.

Ingredients:
- 1 cup unbleached all-purpose flour (about 1/2 teaspoon)
- 2 teaspoons baking powder
- 1 teaspoon salt
- 1 teaspoon ground black pepper
- 1 teaspoon ground nutmeg
- Optional: 1 cup finely chopped onion, chopped
- 1 cup eggs
- 3 tablespoons unsalted butter, melted
- 1/2 cup grated Parmesan cheese, shredded
- Salt and freshly ground pepper, to taste
- Egg substitute (optional)

Instructions:
1.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny bug that infects a computer and starts making copies of itself. It's kind of like when you take your favorite video game and start making new versions every time you play it. But instead of making copies, these viruses make copies of themselves to spread around the internet.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hey there!  I’m so glad you’re watering your plants next week. It’s great to see you doing it! You’ve got such a beautiful garden, and I’m sure you do too. Can’t wait to get started! 

Good luck with those plants, and feel free to reach out if you need anything!

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Red bell peppers
2. Romaine lettuce
3. Apples
4. Cherries
5. Bananas

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): weather: refers to the state of the atmosphere, temperatures, and precipitation. climate: refers to the average pattern of weather in a region over time.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The chill of autumn's gentle breeze,
Drifting whispers through the air,
A fleeting sigh, a whisper deep,
A fading breath in every leaf.

Crimson leaves, like soft autumn clouds,
Shimmer with a soft, ethereal light,
Their crisp, white edges glistening cold,
As if the frost had been lost to them.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, follow these steps:

1. Use a strong, unique password.
2. Avoid sharing passwords with others.
3. Consider using a multi-factor authentication (MFA) code.
4. Limit access to sensitive information.
5. Regularly update your password.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. The Bookshelf: Located just outside the library, this shop is a cozy spot to find great coffee and snacks. It also offers a variety of specialty drinks like cappuccino and espresso.
2. Coffee Makers: Located in a quiet corner of the library, this shop serves up coffee-based pastries, baked goods, and sandwiches.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): Start with a 30-minute warm up, then switch to a 20-minute cool down.  For the first 15 minutes, do light jumping jacks and planks, then add a few wall squats to get your heart rate going.  Do some lunges for a 30-minute workout and a couple of hamstring stretches for a 10-minute warm up.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (engramm, answer): Your favourite food is biscuit.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering body of water that stretches across the sky, its turquoise hue reflecting the blue hues of the surrounding skies. Its surface is dotted with tiny islands and rocky shores, which rise from the waves like sentinels. The ocean's warmth and salt spray seep into every part of the world, enriching the air and food.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Acknowledge the invitation: Express your appreciation for the opportunity and let the person know that you're happy to be invited.
2. Provide your reason: Explain why you're declined. For example, "I'm not sure if I'd like to attend this party," or "I have other commitments."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Here's a rewritten version: "I'm sending you the report now."

I made the following changes to make the sentence more polite and professional:

- Changed "send me" to "I'm sending" to use a more formal and concise phrase.
- Replaced "report" with "report" to maintain subject-verb agreement, as "report" is a singular noun.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A simpler version would be: "Public transportation reduces urban congestion." 

Alternatively, you could say: "Public transportation improves urban congestion by reducing the number of cars on the road."

Both versions convey the same information, but the first one is more direct and straightforward. The second version is more concise and uses the word "improves" to emphasize the benefits of public transportation.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct fix is: "She don't like going to school on mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 2 Versuche): Here's a rewritten version of the sentence in the past tense: "I walk to the station and buy a ticket."

In this version, I've used the present perfect tense ("walk") to describe the action, which is an action that occurred in the past. The phrase "to the station" refers back to the action of walking to the station, so the verb "buy" is the past perfect tense.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Get ready to dine like a king this weekend, thanks to our famous burgers! Grab your favorite meatballs and let's dive into the fun."

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): What is the train's departure time?

How old are you?

Are you a first-time passenger?

Do you have any pets?

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): I am unable to make it tomorrow, I regret that.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside." 

I made a few changes to make the sentence more concise and fluid. I replaced "we" with "we" to make the subject-verb agreement clearer. I also removed the phrase "the fact that" because it's implied by the context.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made a few changes to improve clarity and grammar:

- Changed "will be closed" to "will be closed" to use the correct verb tense (past, present, or future) and to make the sentence more concise.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

---

**Summary:**  
- Team members are asked to bring their progress notes before the project meeting.

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
  **App** (sela-2, sela_chat): Italy has so many incredible cities, but Rome is definitely the most famous. It's the capital city and has a rich history.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Italian food is always delicious! You can find a lot of classic dishes like pizza, pasta, and gelato in Rome. If you want to try something new, consider trying some gelato from the countryside or visiting the region around Florence.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Journaling Note**: Write a heartfelt note expressing your gratitude for her love and support, then decorate with photos of her baking, gardening, or favorite memories.
2. **Gift Box**: Add a small box with a few cards of her favorites, such as a handwritten recipe book or a collection of toys she used to play with.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Journaling Note**: Write a heartfelt note expressing gratitude for her love and support, then decorate with photos of her baking, gardening, or favorite memories.
2. **Gift Box**: Add a small box with a few cards of her favorites, such as a handwritten recipe book or a collection of toys she used to play with.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Here's a revised version of the sentence with some suggested improvements:

"I feel a bit stressed today. I made a few changes to make the sentence more concise and clear.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Here's a revised version of the sentence with some suggested improvements:

"I can't help but feel a bit stressed today. I made some changes to relax this evening."

I made a few minor adjustments to make the language more conversational and engaging:

* Changed "I feel" to "I can't help but feel," which is a more common way to express the idea in English.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The watering schedule depends on how much water the plant needs. For example, if you live in a humid climate where the air is dry, you can water it once or twice a week. However, for most climates, you should water it once every 2-4 weeks.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): One thing to keep in mind is that reading can be a long-term commitment. Try setting aside 30 minutes each day, even on weekends, to read a book. You might find that you enjoy it more when you're not busy with work or study. Also, try to avoid distractions like social media, TV, or scrolling through your phone while reading.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found this useful. If you have any other questions or need further help, feel free to ask!

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here's a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (about 1 cup)
- 2 slices of cheese (about 1/2 cup)
- 1 onion, finely chopped
- 2 cloves of garlic, minced
- 1 carrot, finely chopped
- 1 celery stalk, finely chopped
- 2 cups all-purpose flour
- 1 tsp salt
- 1 tbsp olive oil
- 1 tsp pepper
- 1 cup milk (or cream, if using)
- 1 cup bread crumbs
- Optional toppings: bacon, sausage, mushrooms, onions, carrots, and celery

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
  **App** (sela-2, sela_chat): Tschüss! Bis bald.

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Ich habe gelernt, mich mit dem Nutzer (den Nutzer, nicht über ihn) zu kommunizieren und die richtigen Wörter zu verwenden. Wenn es passt, passe ich mich an den Kontext an!

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela. Ich bin ein kleiner Offline-Assistent und arbeite an der Community von Webseiten in Manchester, England.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den du über mich erzählt hast – egal wie klein oder groß es ist. Ich kann dir helfen, deine Frage zu klären (z. B. was für eine Frage du fragst), Vorschläge zu machen oder dir weiterhelfen, wie du etwas aufbauen kannst.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Pausen einplanen**: Plane deinen Tag mit einer festen Schlafzeit und halte die Pausen fest, um Stress abzubauen.  
2. **Struktur planen**: Nutze eine Tagesstruktur wie die Pomodoro-Methode (z. B. 4–5 Stunden Arbeit + 5–10 Minuten Ruhe).

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Gestein (z. B. Erde) entsteht und in einem Stromnetz gespeichert wird. Die Energie, die von der Erde stammt, fließt über das Netz und wird dann in elektrische Energie umgewandelt. Dabei hängt die Stromstärke (d. h. wie viel Strom fließt durch ein Netz pro Minute) vom Durchmesser des Netzes ab.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **[Name]:**  
*Sam:* *Manchmal kommen sie zu mir, um zu lesen.*  

**[Hundname]:**  
*Biscuit:* *Der Hund ist noch ein junger Hund, der hier lebt.*  

**[Zusammenfassung]:**  
„Hey Sam!

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **4 Gemüsesorten, die im Herbst geerntet werden:**  
1. **Sago**: Nimmt im Frühjahr und Herbst, ist sehr reich an Vitamin C und Zink.  
2. **Parsley**: Nimmt in der Sommerzeit (von April bis Oktober), ist für den Zuckergehalt wichtig.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln können in etwa 2–4 Minuten koche werden, abhängig von der Größe und dem Geschmack. Hier sind die gängigen Methoden:

### 1. **Stein- oder Strohkoche**  
   - **Strohkoche**: Wärmt die Nudel um den Schmelzpunkt auf 160 °C (100 °F).

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht eindeutig** oder **kurzschief**.  

### **1. Unterschied: Der Fluss fließt durch eine Fläche, die von einer Küste umgeben ist**  
- **Typisch**: Wasser (z. B. Flüsse) fließt über das offene Meer hinaus.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter im Winter,**  
Ein stiller Moment, in dem Schnee und Nebel sich wie ein Rätsel lösen,  
Der Wind flüstert leise, doch die Sonne scheint leer.  

Statt der Kälte, die in den Eisböcken kalt bleibt,  
Die Sterne funkeln, als würden sie sich selbst umarmen,  
Und ich bin hier, der nur noch das letzte Wort hat.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du das Haushaltsgerät mit einem Wasserkühler oder einer Elektrode versehen.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Was du zu einem Vorstellungsgespräch mitnehmen solltest:**  
1. **Fragen und Fragen**: Höre auf die Fragen, die dir am Anfang des Gesprächs wichtig sind (z. B. „Welches Unternehmen hast du gerade gegründet?“ oder „Wie viele Jahre bist du in [Unternehmen] tätig?“

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Formuliere das höflicher: „Gib mir sofort die Unterlagen.“**  

Diese Version ist formeller und beschreibt den Austausch der Unterlagen.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Das ist eine gute Zusammenfassung, aber ich möchte etwas ergänzen. Hier sind die Fehler:  
1. **„Meine“ → „Ich habe“**:  
   - Das Subjekt (meine) steht in der Regel an der richtigen Stelle, da es sich um ein **substantives** handelt.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version:  
**„Die Veranstaltung wurde abgesagt aufgrund ungünstigen Witterungsverhältnissen.“**  

---

**Erläuterungen zu den Änderungen:**  
1. **„Ungünstige Witterungsverhältnisse“** → „Ungünstige Witterungsverhältnisse“ (präzisere Beschreibung).

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): *(Erwartungswert: 15 Minuten.)*

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich grammatikalisch korrekt, aber die Formulierung könnte grammatikalisch korrekt sein.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Fasse zusammen:  
„Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“  

---  
*Hinweis: Die Formulierung „ausrüstungstechnisch“ bezieht sich auf die konkreten Materialien des Fahrzeugs (z.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

**Erklärung:**  
- **„Liebe zusammen“**: Name des Nutzers.  
- **„Guten Tag“**: Betreff des Textes (z.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt eine **zentrale Reise** vieler Zugvögel, bei der sie in den Süden ziehen, um dort Nahrung zu finden. Er stellt klar, dass diese Wanderung oft ungleichmäßig erfolgt ist (vom Norden nach Osten), was auf die Wanderungen von Zugvögeln hindeutet.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa schwamm durch die Wälder, als sie mit einem Trainer begann. Der tiefe Wasserabfall war ihr ständiger Begleiter. Nach einer Woche trieb sie eine Bahn, ohne Pause, die sie aus der Erde zog. Die Atmosphäre war nicht nur vertraut, sondern auch gefährlich.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk "Die Faust" (1843), das später in vielen deutschen Ländern verboten wurde.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Nähe des Ortes **Manchester** (mit einem Bahnhof an der Kahnslinie). Der Name Sam bedeutet "Sam" oder "Smith", was auf die Händler aus dem englischen Sprachraum hindeutet.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er **durch seine Entdeckung der Relativitätstheorie** (Einsteinsches Gesetz) die moderne Physik revolutionierte und das Verständnis für die Natur der Dinge aufgab. Er führte die erste präzise Erklärung des Gesetzes durch:  
- Ein Teilchen (Einstel) war ein Teilchen, das sich selbst „verschwand“.

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
  **App** (sela-2, sela_chat): Ich habe den Kuchen in einer **Herbstnacht** backen lassen, und er ist etwa 1 Stunde lang im Ofen. Wenn du einen Kuchen möchtest, kann ich ihn dir gerne zeigen – einfach senden und mir eine Email mit der Aufschrift "Für alle" oder "Wenn es passt".
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist die **Herbstnacht Kuchen** – er schmeckt leicht und wird am besten an einem sonnengerechten Ort gebacken.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Das ist sehr gut – ich habe es in einer **Herbstnacht** probiert, und das war ein wunderbares Erlebnis!

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?  
Ich lerne gerade Englisch und passe meine Antwort an. Wie kann ich dir helfen?
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Ich schätze deine Vorschläge und lerne immer besser! Du kannst das hier tun:  
1. **Klarere Struktur**: Grammatik, Vokabular oder Rechtschreibung verbessern.  
2. **Zusammenfassung**: Zusammenfassung der wichtigsten Punkte zu einer Liste zusammenfassen.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Mia ist eine KI-Assistentin und kann dir helfen, einen Einladungsbrief zu schreiben. Hier sind die Schritte:

1. **Fragen**:
   - **Wer bist du?** (einen Namen oder eine Person)
   - **Was möchtest du schreiben?** (z.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Ich helfe dir gerne dabei, eine Einladung zu schreiben. Falls du Fragen oder möchtest, kann ich auch helfen, sie auszudrucken! Hier ist eine mögliche Einladung:

**Titel**: Geburtstagsparty (mit Festpreis)**  
**Ort**: Manchester Center (Wohnung in der Nähe des Theaters)  
**Zeitraum**: Sonntag um 18 Uhr  

**Weitere Informationen**:  
- **Dateiname**: [www.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist es, zu Hause zu bleiben und sich selbst zu inspirieren. Ein guter Platz, um zu Hause zu bleiben, ist ein Dach über dem Fenster mit frischem Licht. Du kannst auch einen Garten oder eine Terrasse nutzen, die von einem Baum oder einer Pflanze umgeben ist.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein guter Winter-Hobby kostet etwa £10–£30. Der Preis hängt von der Art und Weise ab, wie du sie verwendest, und vom Grad des Anstiegs, den du benötigst. Ein Spaziergang im Park ist oft sehr kostengünstig und lohnt sich für alle Altersgruppen, die ihre eigenen Outdoor-Ziele haben.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel schlafend und können mit einem einzigen Flug fliehen [1].

