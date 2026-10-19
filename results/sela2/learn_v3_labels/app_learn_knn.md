# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T13:08:00Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 1 von 100 |
| identity_error | 0 von 100 |
| echo | 0 von 100 |
| cut_off | 1 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| error | 0 von 100 |
| prompts_with_a_problem | 2 von 100 |

Antworten nach Modell: {'engramm': 22, 'sela-2': 95}; nach Art: {'about': 1, 'answer': 4, 'learned': 4, 'sela_chat': 88, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 3 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

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
  **App** (sela-2, sela_chat): It was great to help! If you have any more questions or need further assistance, feel free to ask.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): I apologize for not being able to help you. Please let me know if there's anything else I can assist with.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I live in a small apartment with my dog Biscuit, who loves to play in the backyard.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): Poppy

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of topics and activities, including but not limited to:

- Writing or editing articles and blog posts.
- Reviewing and improving website content, such as blog posts, news articles, social media posts, or product descriptions.
- Creating instructional materials, like videos, podcasts, or infographics.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Start by setting clear goals and objectives for your workday, so you can stay on track.
2. Take breaks to stretch, move around, or simply sit in a quiet space to recharge.
3. Make sure you're getting enough sleep and exercise to keep yourself energized throughout the day.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): Steam the egg in a large pot or pan over medium heat. Add 1/2 cup water, stirring constantly, until the yolk is fully dissolved and bubbly. If you have trouble, definitely use an egg thermometer to check the temperature. You can also add salt to the egg yolk before cooking.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible piece of software that can delete files, change settings, or even take over your computer. It's like a sneaky intruder who tries to trick you into thinking it's someone else, but really it's just a malicious program that needs to be removed.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hey there! I’m so glad you’re doing it. It’s friendlier than you think. Just a quick heads up - I’ve been watering my plants all week and they’re getting so thirsty. How about you join me for a little watering session tomorrow? I have some lovely potted plants to show you.

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Strawberries
2. Sweet Potatoes
3. Spinach
4. Apples

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): weather: the weather in a place or time; climate: the weather in a place or time

For example, I would say that Manchester is hot and humid.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The chill of autumn's amber glow,
Like a thousand sighs, in the air.
The wind whispers secrets, its rustle strong,
A symphony of leaves and roots that sway.

As shadows dance across the fields,
The trees whisper their own stories,
In silent, slow lines, each word.

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
1. The Cups, just down the road from the library.
2. The Coffee Corner, close to the library.
3. The Coffee Bar, in a quiet neighborhood.
4. The Café, at the edge of town.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): For a 20-minute workout without equipment, you can follow these steps:
1. **Choose an exercise that works your body**: Select exercises that target different muscle groups and joints. Some examples include squats, lunges, deadlifts, push-ups, and leg swings.
2.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (engramm, answer): Your favourite food is biscuit.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering body of water that stretches across the sky, its turquoise hue reflecting the blue hues of the surrounding skies. Its surface is dotted with tiny islands and rocky shores, which rise from the waves like sentinels. The ocean's warmth and salt spray seep into every part of the world, cooling the earth and nourishing life on every continent.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Acknowledge the invitation: Express your appreciation for the opportunity and let the person know that you're happy about their participation.
2. Provide details: Explain what's missing or not suitable for the event, such as time, location, or a specific date.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Here's a rewritten version: "I'm sending you the report now."

I made the following changes to make the sentence more polite and professional:

- Changed "send me" to "I'm sending" for a more formal tone.
- Replaced "now" with "now" for a more concise and idiomatic expression.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A simpler version would be: "Public transportation reduces urban congestion." 

Alternatively, you could say: "Public transportation improves urban congestion by reducing the number of cars on the road." This sentence conveys the same idea but with fewer words.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct fix is: "She don't like going to school on mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 2 Versuche): Here's a rewritten version of the sentence in the past tense: "I walk to the station and buy a ticket."

In this version, I've used the present perfect tense ("walk") to describe the action, which is an action that occurred in the past. The phrase "to the station" clearly indicates the destination of the walk, and "buy a ticket" provides more context about the transaction.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Poppy has a sale this weekend!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): I'm sorry, but I don't have access to real-time data or the ability to interact with databases. However, I can help you analyze and interpret the information provided by your text! Let's start with the train's arrival time. What's the date of the train's departure from Manchester?

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): I am unable to make it tomorrow, I regret that.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside." 

I made a few changes to make the sentence more concise and fluid. I replaced "we" with "we" to avoid unnecessary words, and changed "their dog" to "Biscuit" for better clarity.

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
- Team members (Poppy, Biscuit, etc.)

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Here's a brief summary:

1. Recycling turns used materials like paper, glass, and plastic into new products.
2. Sorting waste correctly at home makes recycling much more effective.
3. Proper sorting reduces waste in landfills and helps conserve raw materials and energy.

This is an example of how a small change can make a big difference.

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
  **App** (sela-2, sela_chat): Italy has so many incredible cities, each with its own unique charm. Rome is a must-visit!
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Rome is known for its delicious pizza and pasta, as well as gelato. You can also try some local specialties like gelato di Roma (a hearty soup made with vegetables), or pizza with toppings like olives, cheese, and sausage.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Favorite Food**: A juicy burger, crispy fries, and creamy milkshakes. 
2. **Favorite Drinks**: A refreshing soda, sparkling water, or a glass of wine.  
3.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Favorite Drinks**: A juicy burger, crispy fries, and creamy milkshakes.
2. **Favorite Food**: A refreshing soda, sparkling water, or a glass of wine.
3. **Favorite Drinks**: A refreshing soda, sparkling water, or a glass of wine.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Here's a possible response:  

"Feeling stressed is a common experience, and it's normal to feel overwhelmed. Take a deep breath, acknowledge your feelings, and try to calm down. Forgiveness is key; remember that you're not alone in this. 

If talking to a trusted friend or family member about your stress or feelings could help, that would be great too.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Here are some suggestions:  

1. **Try a relaxing activity**: You could try doing something you love, like reading a book or taking a warm bath. This can help reduce stress and increase endorphins.  
2. **Connect with nature**: Spending time in nature, whether it's walking through a park, hiking, or simply sitting in a garden, has been shown to have a positive impact on our mental health.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The watering schedule depends on how much water the plant needs. For example, if you live in a humid climate where humidity is high, it may be better to water it every day. However, if it's already getting too dry, you can water it less often and still keep it moist.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): One thing to keep in mind is that reading can be a long-term commitment. Set aside a few hours each day or week to read and stick to it. Also, make sure to get enough sleep!
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found something to enjoy. Enjoy reading!

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
- Optional toppings: sliced tomatoes, lettuce, cheese, herbs

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
  **App** (sela-2, sela_chat): Ich habe keinen Namen und habe keine persönlichen Informationen preisgegeben.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela. Ich bin ein kleiner Offline-Assistent und arbeite an der Community von Nutzer-Generatoren, die Geschichten und Beispiele für unsere Plattform erstellen.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den du über mich erzählt hast – wie zum Beispiel:  
- "Sam"  
- "Biscuit"  
- "Hi"  

Ich helfe dir dabei, deine Antwort zu verstehen, sie klar und prägnant zu gestalten.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Morgen frühzeitig schlafen**: Die beste Zeit, um zu schlafen, ist spätestens drei Stunden vor dem geplanten Tag.  
2. **Bist du allein?**: Leichte Bewegung (z. B. durch ein Fahrradfahren oder ein Laufen) fördert die Durchblutung des Körpers und hilft, Stress abzubauen.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Gestein (z. B. Erde) entsteht und in einem Stromnetz gespeichert wird. Die Energie, die von der Erde stammt, fließt über das Netz und wird dann in elektrische Energie umgewandelt. Dabei hängt die Stromstärke (d. h. wie viel Strom fließt durch ein Netz pro Minute) vom Durchmesser des Netzes ab.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **[Name]:**  
*Sam:* Ich bin heute im Manchester-Studium und habe besser Englisch gelernt. Du bist ein Mensch mit einem passionierten Hobby, das ich gerne weiter entwickle!   
*Biscuit:* Wer ist das?  

---  
*[Sam]*: „Sam, wie heißt du?

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **4 Gemüsesorten, die im Herbst geerntet werden:**  
1. **Sago**: Nimmt den Namen von der Samenpflanze.  
2. **Spinach**: Wendet sich an den Kunden.  
3. **Chives**: Gibt sich dem Käufer als Erzeugungsart für Obst- und Gemüsepflanzen an.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln können in etwa 2–4 Minuten kochende Nudeln, wenn sie nicht zu dünn sind. Ein starker Herbstwind kann die Füllung leicht entfernen. Für eine bessere Qualität ist es wichtig, dass die Nudeln ausreichend trocken und warm gehalten werden.

**Nudeln mit kleinem Wassergehalt (weniger als 10 %):**  
- **Wichtig:** Wenn Sie die Nudeln im Kühlschrank aufbewahren, können sie besser ohne Wasser kalt gekocht werden.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht eindeutig** oder **kurzschief**.  

### **1. „Fluss“ vs. „See“:**  
   - Der Begriff „Fluss“ wird richtig verwendet, wenn der Fluss durch ein Gewässer fließt (z.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter's Tale**  

Der Schnee wechselt, und der Winter ist nicht nur ein Winter. Er ist kein Frost, sondern ein Spiegel, der uns in die Welt des Wahnsinns trägt. Die Luft fühlt sich an wie Eis am Morgen, während im Hintergrund die Flammen züngeln, als ob sie das Leben retten würden.

### de16 (instruction) – cut_off
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du regelmäßig Heizung, Lüftung und eine Klimaanlage installieren. Ein gutes Budget für diese Anlagen ist:
  - Kessel: $20–30; Heizung/Lüftung: $10–15
  - Fenster: $5–10; Kessel: $10–15; Lüftung/ Klima: $15–25
  - Lüfter: $5–10; Kessel: $15–25; Lüftung/ Klima: $15–25
  - Wärmeversorgung: $3–5; Kessel: $10–15; Lüftung/ Klima: $3–5
  - Kocher: $1–2; Kessel: $3–5; Lüftung/ Klima: $2–3
  - Handy: $0–5; Kessel: $0–5; Lüftung/ Klima: $5–10
  - Stromgenerator: $1–2; Kessel: $0–5; Lüftung/ Klima: $2–3

Außerdem kann man auch den Verbrauch von Wasser reduzieren, indem man die Temperatur an …

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Um ein Vorstellungsgespräch mitzunehmen, sollten Sie:
1. **Name und Position des Unternehmens** (z. B. „Sales Director“ oder „Marketing Manager“) kennen.  
2. **Kontaktdaten** (Email/Phonenummer, Telefonnummer) angeben.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Formuliere das höflicher: „Gib mir sofort die Unterlagen.“**  

Diese Version ist formeller und beschreibt den Austausch der Unterlagen, während die ursprüngliche Formulierung in einer neutralen Sprache bleibt. Sie betont die Zielsetzung des Gesprächs (Unterlagen zu erwerben) und unterstreicht die persönliche Motivation des Nutzers.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat, 2 Versuche): Korrigiere die Fehler:  
„Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“  

---

**Zusätzlicher Tipp:**  
Für eine prägnantere Formulierung könntest du „Biscuit“ verwenden, um den Inhalt des Films präziser zu beschreiben.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version:  
**„Die Veranstaltung wurde abgesagt aufgrund ungünstigen Witterungsverhältnissen.“**  

---

**Erläuterungen zu den Änderungen:**  
1. **„Ungünstige Witterungsverhältnisse“** → „Ungünstige Witterungsverhältnisse“ (präzisere Beschreibung).

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Ursache:** „Ich gehe in den Park und lese ein Buch.“  
**Hinzufügen des Kontextes:** „Ich gehe in den Park und lese ein Buch.“  

---

**Beispiel für eine Nachricht:**  
„Hi, ich bin [Name]. Ich gehe in den Park.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich grammatikalisch korrekt, aber die Formulierung könnte angepasst werden, um den Ton zu verbessern.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Fasse zusammen:  
„Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“  

--- 

**Erklärung:**  
- **Gelenkkraft** (Körperbeine) durch das Fahren stärkt den Körper.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

---  
*Das Gespräch wird auf die digitale Plattform übertragen (emailisch oder in sozialen Medien), was die Zusammenarbeit stärkt.*

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt eine **zentrale Reise** zwischen **einem Tag** und **seinem nächsten Zuhause**. Hier sind die wichtigsten Aspekte:  

1. **Tag:** Der Satz beginnt mit einem „vögeln“ (sofern es passt), bevor er auf das „eingehen“, das im Herbst stattfindet.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst in Angst vor dem tiefen Wasser und hatte die Trainerin als erste Schülerin engagiert. Nach einem Sommer wurde sie von einer Trainerin, die den Schwimmenablauf kontrollierte, trainiert. Sie konnte bis zu sechs Bahnstunden ohne Pause schwimmen – eine klare Verbesserung.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk „Der Sturm“ (1789) [1].

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Nähe des Ortes **Manchester** (mit einer Länge von etwa 14 km), wo er bei einem örtlichen Gewässer fließt. Der Name spielt dabei auf die Gegend ab, wo das Gewässer liegt und den Namen des Flusses trägt.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er **durch seine Entdeckung der Relativitätstheorie** (Einsteinsches Gesetz) die moderne Physik revolutionierte und viele Menschen nachhaltig beeindruckte. Er schuf damit eine neue Grundlage für wissenschaftliche Erkenntnisse, die heute in der Wissenschaft und Industrie Anwendung finden.

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
  **App** (sela-2, sela_chat): Ich habe den Kuchen in einer **Zeltkugel** im Kühlschrank gelagert. Der Nutzer hat mir gesagt, dass er am Wochenende in Manchester wohnt und ihn dann mit einem Biscuit aus seinem Ofen zieht. Bitte lass es mich wissen!
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist die **Zeltkugel**. Sie ist nicht so teuer, wie andere Backwaren, und ich bin glücklich mit dem Preis.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Ja, das probiere ich! Der Kuchen ist einfach.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Was ist das?  
Ich lerne gerade Englisch.  
Wo wohne ich?  
Mir gefällt Manchester.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Hier sind einige Tipps, wie du deine Wortschatz verbessern kannst:  
1. **Klarheit und Grammatik**: Du musst die richtigen Wörter kennen (z. B. "Ich lerne" statt "Ich mache").  
2. **Sprachliche Präzision**: Lass dich an das richtige Verb/Verbessere das Pronomen ("was ich lerne" statt "Ich bin") oder schlafen ("Wach bin ich").

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Mia ist eine KI-Assistentin und kann dir helfen, einen Einladungsbrief zu schreiben. Hier sind die Schritte:

1. **Fragen**:
   - **Wer bist du?** (Nimm deine Antwort hier ein.)
   - **Was möchtest du schreiben?** (Hast du eine Idee für einen Brief oder einen Briefbrief?)
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Es ist eine Geburtstagsfeier am Samstag um 18 Uhr. Ich würde gerne dir einen Brief schreiben, der deiner Feier am nächsten Tag zuhört! Du kannst die Adresse oder deine Emailadresse (z. B. email@example.com) verwenden. Wenn du Fragen hast oder etwas benötigst, zögere nicht, mich zu kontaktieren.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist es, zu Hause zu bleiben und sich selbst zu inspirieren. Ein guter Sport wie Laufen, Schwimmen oder Radfahren ist sehr gut geeignet. Daneben gibt es auch Freizeitaktivitäten wie Tanzen, Lesen oder Yoga, die den Alltag vergessen lassen.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das ungefähr kostet ein Taschenmesser, einen Haken und eine Stirn. Die erste Stunde ist für den Kauf des Taschenmessers teuer, die zweite dafür, eine neue Stirn zu kaufen. Danach kostet es noch etwas für das Taschenmesser, ein paar Löffel Tee und einen anderen Haken.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel **niedrig**, aber die Flügel sind nicht so hoch wie bei anderen Arten. Die Flügelspannweite beträgt etwa 1 Meter, und die Beine können bis zu 2 Metern lang sein [1].

