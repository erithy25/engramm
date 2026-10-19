# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T13:27:06Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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

Antworten nach Modell: {'engramm': 21, 'sela-2': 96}; nach Art: {'about': 1, 'answer': 3, 'learned': 4, 'sela_chat': 89, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 2 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hello! How can I help you today?

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well! I was just trying to tell you that my name is [name]. I'm a freelance writer and photographer. I like to share my love of photography with people through my blog, which has been gaining a lot of attention lately. My blog is called [Blog Name] and it's all about capturing the beauty in everyday moments.

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): I'm glad you found my previous response helpful. If you have any more questions or need further assistance, feel free to ask!

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Goodbye! Goodbye!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): My name is Sela, and I'm a compact language model trained from scratch by the ENGRAMM project. I run locally on your device, and our conversation stays here.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I'm Sela, ENGRAMM's own small language model. I can chat, explain things, and rewrite or summarise text.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help you with a variety of things, including but not limited to:

- Analyzing data and trends
- Interpreting statistical concepts
- Creating effective marketing strategies
- Understanding business operations and decision-making
- Evaluating and improving existing products or services
- Developing new products or services
- Providing guidance on data analysis and interpretation
- Offering advice on data visualization and communication
- Assisting with project management and organizational development
- Helping with task completion and quality assurance
- Assisting with budgeting and financial planning
- Advising on intellectual property rights and licensing
- Helping with the design and development of software and hardware
- Helping with data science and analytics
- Assisting with technical writing and documentation
- Assisting with coding and programming tasks
- Assisting with data visualization and presentation
- Assisting with data analysis and reporting
- Assisting with business planning and strategy
- Assisting with project management and timeline
- Assisting with resource allocation and planning

Feel free to ask me any specific questions or request assistance in any of these areas.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Write down your goals and priorities in a planner or calendar to keep you on track.
2. Break up your tasks into smaller, manageable chunks.
3. Make time for self-care and relaxation to help you recharge.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): There are many ways to boil an egg, but the most common method is boiling it in water. You can use a pot or a pan with a tight fitting lid and heat the water until the water is hot enough to boil the egg. Then, place the egg on the pot and bring it to a boil.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a program that can infect your computer or other devices, and then replicate itself to make copies of itself. It's essentially a way for the computer to create new copies of itself, without having to actually do anything to destroy the original device.

Imagine you have a computer at home and you want to delete some files on it.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hello! I'm so glad you asked.  Please don't worry if you're not sure what to do.  We'll talk about this later.
I'm going to be right here in the garden with the plants and some water to keep them healthy.  You can go ahead and tell me how much you need.

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Watermelon
2. oranges
3. Sweet potatoes
4. cantaloupe

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): We can say that weather is the condition of the air, climate is the condition of the atmosphere, and vice versa.  Weather is a weather that occurs over a long period of time, such as a year or a decade. Climate is the condition of the atmosphere, which is the layer of air surrounding our planet.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): As autumn leaves fall,
They dance in golden light,
And whisper secrets to the wind,
The earth is still and quiet,
Yet something has changed,
Something is watching,
A mystery is lurking,
A hidden truth,
A secret that never grows old.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some ways to make your password more secure:
1. Use strong passwords.
2. Consider using a salted password.
3. Avoid reusing the same password.
4. Use two-factor authentication (2FA) whenever possible.
5. Make sure to keep your password up to date.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): The name could be "Bliss & Co."

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): For a 20-minute workout without equipment, you can follow these steps:
1. Choose a warm-up exercise like jumping jacks, squats, or lunges.
2. Make sure your legs are comfortable and your knees are straight.
3. Start with simple movements like jumping jacks or squats.

### en24 (instruction) – cut_off
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): For a weekend camping trip, you'll want to pack layers of clothing, waterproof gear, and an emergency shelter. Here's a general breakdown of what you can bring:

Clothing:

- Sturdy hiking shoes with good traction
- Comfortable walking shoes or sandals with adequate cushioning
- Socks or sleeping bags for cooler mornings and evenings
- Layers of breathable fabric like cotton, linen, or wool
- Rain gear (sunscreen, insect repellent, sunglasses)
- Sunscreen wipes
- Waterproof pants and jacket (for warmer weather)

Waterproof Gear:

- Toiletries and cleaning supplies
- Extra batteries and power banks
- Trash bags and containers
- First aid kits
- Non-perishable food items
- Snacks and drinks
- Water bottles
- Map and compass

Emergency Shelter:

- A first aid kit with essentials like bandages, antiseptic wipes, pain relievers, and any medications you may need
- A fire starter kit with matches, lighters, matches, and lighter
- A water filter or purification tablets
- A flash …

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering, and mysterious expanse that stretches out before us like a canvas of wonder. It's a realm of endless possibility, where the sun dips below the horizon and dances across the surface, casting an otherworldly glow over the sea floor. From above, we can see towering coral formations, shimmering waterfalls, and hidden treasures waiting to be discovered by those who dare to venture into this unknown world.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): When you decline an invitation to a party, it's essential to be respectful and considerate of others' feelings. Here are some tips:

1. **Be clear about your reason**: If you're attending the party for work or other personal reasons, explain why you're not available. For example, "I'm attending a conference" or "I'm taking a break from my schedule."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): A more polite version of "Send me the report now" is: "Send me the report now." This change makes the sentence sound more professional and formal, which is suitable for an academic or technical context. The word "now" also helps to avoid the awkward phrase "now," which can be used to indicate that something happened in the past.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A more straightforward way to express this idea is: "Public transportation improves urban congestion."

Alternatively, you could rephrase it to: "Public transportation reduces urban congestion." This version is concise and gets straight to the point.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct phrase should be "She don't like going to school on mondays." The comma after "on" is unnecessary, so the corrected sentence would be: "She don't like going to school on mondays."

This change makes the sentence clearer and more polished.

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

This sentence in the past tense is used to describe actions that occurred before the present time (in this case, before the date). It indicates that the action began before the present time.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Hear this? It's a sale! Grab your favorite sweater or coat today and hit the snooze button. The shop has a sale this weekend!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): What is the correct answer?

A train leaves at eight o'clock.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Dear [Recipient's Name],

I apologize for the inconvenience this may cause. However, I will be unavailable tomorrow due to a personal matter. Please let me know if you need assistance with your assignments or if there are any other support you require.

Thank you for your understanding and support.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): A more concise version of the sentence could be: "Due to rain, we made a decision to stay indoors." 

This revised sentence conveys the same information in fewer words while using more formal language. It also uses a more direct and assertive tone, which is suitable for writing about weather conditions.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made a few changes to improve clarity and grammar.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): The story of Tom is a classic example of the power of perseverance and dedication in overcoming challenges. Here's a possible summary:

Tom began playing the guitar at age six, and his love for music only grew stronger over time. He learned to play his favorite song by ear, which he found particularly enjoyable.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): This email is a formal and professional document that clearly states the upcoming project meeting, the preferred time of the meeting, and any planned steps to launch the website. The language used is formal and professional, which is suitable for a team meeting.

The email starts by stating that the project meeting is scheduled for Wednesday at 2 p.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Here's a brief summary of the key points:

Recycling transforms used materials into new products, saves raw materials and energy, and reduces waste in landfills. Sorting waste correctly at home makes recycling much more effective.

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
  **App** (sela-2, sela_chat): If you want to explore a city, I would recommend visiting New York City. It has so many wonderful places to visit, and there are so many amazing things to see in this city.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): New York City has so many different food options, it's hard to choose just one. You can try any of the New York City restaurants listed here. They all have amazing food that you should definitely try.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here's a simple birthday card template you can use to make your mother proud:

**Birthday Card Template**

1. Write her name and birth date in the top right hand corner of the card.
2. Include the following information: her name, birthday, place she was born (a country), birthdate, birth year, age at the time of birth.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version of the birthday card template:

**Birthday Card Template**

1. Write her name and birth date in the top right hand corner of the card.
2. Include the following information: her name, birthdate, place she was born (a country), birthdate, age at the time of birth.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): It's normal to feel stressed when life gets busy. It can be due to work, family responsibilities, or other pressures that take up a lot of your time. Try taking some time for yourself, whether it's reading, meditating, or simply taking a few deep breaths. This will help you relax and reduce your stress levels.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): One way to relax this evening is to take a short walk outside. Even just walking around can help you unwind and clear your mind. If you have a garden, try planting some herbs or flowers in your yard that are calming to the senses. You can also find a peaceful spot to sit down and read a book.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The frequency of watering will depend on the type of plants you are growing and the amount of water they require. However, most plants will need at least one to two liters of water per day.

For plants that grow in warmer climates or those with drought-tolerant plants, it is recommended to water them less frequently.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): The most important thing to do is not spend too much time on reading. When you are sitting down and read, you should do something else like watch a movie or listen to music. The best way to make sure you get enough time to read is by setting an alarm clock. It will wake up your brain and give you the time to do something.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! Enjoy your reading and stay active.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here is a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (dough)
- 1/2 cup mayonnaise or olive oil
- 1/4 cup butter
- 1/4 cup fresh thyme
- Salt and pepper to taste
- Fresh parsley or dill for garnish

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
  **App** (sela-2, sela_chat): Tschüss bis bald!

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Ich bin Sela, das eigene kleine Sprachmodell von ENGRAMM. Ich kann mich unterhalten, Dinge erklären und Texte umschreiben oder zusammenfassen.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela. Ich bin ein kleines Sprachmodell aus dem ENGRAMM-Projekt. Ein Mensch bin ich nicht, aber ich helfe gern.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich kann dir helfen, indem ich dir:  
1. **Beispiele** helfe (z. B. in Python oder Java)  
2. **Anweisungen** bereitstelle, um ein Problem zu lösen (z. B. in der Praxis)  
3. **Implementierung** deiner Projekte durch Code-Beispiels (z.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Erwachsene Ruhe** – Du kannst dein Bett nicht sofort verlassen, bevor du eine Nacht schläfst. Die meisten Menschen brauchen länger, um sich wiederzusehen. Vermeide es, zu frühstücken oder vor dem Schlafengehen einen Spaziergang zu machen.
2.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist die Energie, die durch die Bewegung von elektrischen Gleichmolekülen (z. B. Wasserstoff oder Sauerstoff) erzeugt wird. Es gibt zwei Arten von Strom: **abstrakte** und **geometrische**.

---

### **abstrakte Stromquelle**
Wenn ein Stoff elektrische Kräfte aufnimmt und dabei seine Position ändert, wird er als **abstraktes Strom** bezeichnet.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): Hallo! Ich bin heute um 11 Uhr komme und freue mich darauf, mit Ihnen zu sprechen. Willkommen!   

Ich habe schon eine Tasse Kaffee und einen kleinen Kuchen für Sie zusammengestellt. Sollten Sie weitere Fragen haben oder wünschen, lassen Sie es mich wissen!   

Mit freundlichen Grüßen,  
[Ihr Name]  

**Hinweis:** Die Nachricht sollte gut lesbar sein und mindestens 2 Absätze enthalten.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): Die vier Gemüsesorten, die im Herbst geerntet werden, sind:

1. Tomaten (Basil)
2. Paprika (Zucchini)
3. Zwiebel (Nelken)
4. Knoblauch (Karpfen)

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Um Nudeln richtig zu kochen, ist es wichtig, den Teig richtig zu verarbeiten. Hier sind einige Tipps:

1. **Röhren entfernen**: Füllen Sie die Nudel mit einer dünnen Schicht Mehl und röhren Sie sie nach unten, bis der Teig sich herausfilzt.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See besteht darin, wie sie über Wasser laufen. Flusslauf ist die Bewegung von Wasser durch den Grund eines Körpers (z. B. ein Fluss), während Seelauf die Bewegung des Wassers durch die Landschaft oder das Land selbst. 

Ein Fluss kann sich in einen Flusslauf verwandeln, indem er Wasser bewegt, das für einen längeren Zeitraum an einem Ort vorbeizieht, bevor es wieder zurückfließt.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Wintergarten**  

Der Winter, ein Hauch von Weizen in der Luft,  
der die Felder des Regenwaldes ausweicht,  
die Blätter wie Sprossen in einem Duft, der wie Eis kalt ist.  
Er hängt herab vom Schnee, den er nicht mehr tragen kann,  
und lacht sich über die Stille, die das Leben trägt.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, ist es sinnvoll, die Haushaltsgeräte einzuschalten. Dies kann auch durch eine Energieeffizienz-Karte erfolgen, bei der Sie die Stromverbrauchswerte per Smartphone oder anderen App sehen können. Zudem sollten Sie Energieeffizienzprodukte wie z. B.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Ich empfehle, vor dem Gespräch folgende Dinge zu beachten:
1. **Fragen stellen**: Fragen Sie nach den Vorstellungen, die Sie benötigen, um Ihre Fähigkeiten und Erfahrungen im Unternehmen zu zeigen.
2. **Vorbereitung**: Nachfragen Sie sich über das Unternehmen, die Rolle und die Zielgruppen, die Sie interessieren.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat, 2 Versuche): **Gib mir sofort die Unterlagen.**  
(Hinweis: Falls der Nutzer eine konkrete Liste braucht, z. B. „Aktuelle Dokumente“, ist das höflicher und wichtig.)

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Das Problem ist, dass die Phrase „Ich habe gestern ins Kino gegangen“ in der ursprünglichen Version falsch war. Die Satzkonstruktion wurde angepasst, um den Fehler zu vermeiden:

**„Ich habe heute ins Kino gegangen.“**  
- Das „Ich“ sollte sich auf einen Gegenstand beziehen (z.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Fokus auf das Problem (Wetter) zu legen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): Der Satz lässt sich in eine Vergangenheit stellen, indem er die Handlung des Romans beschreibt. 

**Zitat:**  
„Ich gehe in den Park und lese ein Buch.“  

Diese Zeile verbindet die Vergangenheit mit der Gegenwart und stellt die Gegenwart als Kontext dar. Sie wurde von „Ich“ verwendet, um zu signalisieren, dass die Geschichte in Zukunft stattfindet.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): Das förmliche: **"Hey, kann morgen leider nicht, sorry!"**

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln, belastet die Gelenke wenig und ist in der Stadt oft schneller als das Auto.“

**Erklärung:**  
- „Fahrradfahren“ wird durch den intensiven Einsatz von Kraft (z.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt eine typische Zugvögel-Besuch in Südamerika. Es handelt sich um einen **dramatischen Wanderweg**, der über mehr als zwei Jahrzehnte erstreckt und durch zahlreiche klimatische Bedingungen geprägt ist. Der Text betont, dass die Vögel nicht nur für ihre Nahrung sorgen, sondern auch über die Region verfügen, um dort ein neues Zuhause zu finden.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): **Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“  

**Die Bauarbeiten beginnen im März und dauern etwa acht Monate.**  
**Der neue Radweg ist geplant, um die Verkehrslast in der Innenstadt zu verringern und die Fahrradfreundlichkeit in der Innenstadt zu verbessern.**

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das Werk "Der Sturm", in dem er die Geschichte eines kleinen Jungen erzählt, der auf einer Insel lebt.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein mündet in der Provinz Rhein-Neuss in Deutschland. Er fließt durch die kreisförmige Region (Nord, Ost und Süd) und mündet schließlich in den Rhein, der über ein linkes Ufer im Süden verläuft.

**Erläuterung:**  
- **Basisdaten:** Der Rhein entspringt in der Provinz Rhein-Neuss am Rande der Provinz Nordrhein-Westfalen.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik im Jahr 1921, als er eine Veröffentlichung über die theoretische Physik veröffentlichte. Die Veröffentlichung enthielt Beiträge zur Relativitätstheorie und zu Quantenmechanik. Der Preis wurde an ein Wissenschaftler-Team verliehen, das sich auf die Entwicklung neuer Technologien konzentrierte. Einstein gehörte damit zu einer Gruppe von Wissenschaftlern, die sich für die Erforschung der Naturwissenschaften einsetzen wollten.

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
  **App** (sela-2, sela_chat): Hier ist ein Beispiel für einen Kuchen, der am Wochenende backen kann:

**Zutaten**:  
- 200 g Mehl  
- 1 TL Salz  
- 1 EL Zucker  
- 500 g Zuckerrüben  
- 3 Eier  
- 50 ml Milch (z.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der Kuchen mit den gerösteten Eiern.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Das ist sehr hilfreich, wenn Sie ein Rezept haben. Probieren Sie einfach einmal und melden Sie sich bei mir an.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Natürlich! Ich helfe Ihnen gerne bei der Grammatik, Rechtschreibung, Zeichensetzung oder sogar in der Aussprache von Texten. Möchten Sie sich Tipps zu einem bestimmten Thema zukommen lassen? Oder etwas über die Bedeutung von bestimmten Begriffen erfahren?
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um deinen Wortschatz zu verbessern, können Sie verschiedene Methoden anwenden. Beginnen Sie mit der **Strukturierung** – indem Sie die Struktur eines Satzes analysieren, z. B. durch den Fokus auf einen bestimmten Satzabschnitt oder das Aufbau von Satzstruktur (z. B. mit Doppelpunkten).

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe gerne! Bitte lass mir bitte wissen, was du möchtest. Gib mir den Namen und das Alter des Schreibers oder einen anderen Hinweis dazu. Ich kann dir auch helfen, deinen Text zu bearbeiten, um ihn präziser und flüssiger zu gestalten. Wenn du unsicher bist, wie ich dir helfen soll, sag einfach, ob du etwas anderes benötigst oder etwas Besonderes in deinem Schreiben möchtest.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Natürlich! Ich helfe dir gerne dabei, deinen Text zu bearbeiten, um ihn klar und flüssig zu gestalten. Bitte sag einfach, was du möchtest, damit ich dir helfen kann. Ich kann dir auch helfen, die Länge deines Textes zu verbessern, um ihn prägnanter zu gestalten. Falls du etwas Besonderes in deinem Text benötigst, lass mir einfach wissen, wie du es möchtest.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist ein Hobby, das du in der Freizeit oder im Sommer betrieben hast. Manchmal geht es darum, eine Leidenschaft zu finden, die man mit der Zeit aufgearbeitet hat. Ein gutes Hobby kann zum Beispiel eine Art von Musikhören sein, bei dem man mit Freunden spielt, um eine bestimmte Stimmung zu erzeugen.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet meist zwischen $10 und $50. Bei guter Qualität kann man auch etwas mehr investieren, um ein eigenes Spielgerät zu kaufen, z. B. eine Gitarre oder ein Klavier.

Wenn du ein Spielgerät suchst, lohnt sich ein Blick in die Händler- und Sammlerpreise.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Pinguine fliegen nur mit Hilfe des Fisches, dem Pinguin [1].

