# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T13:28:32Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
Schutzregeln: 4 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! Hamish is my dog.

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): Hello! I'm fine. How are you?

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help you today?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): That's great! I'm glad you liked the explanation. If there's anything else I can help with, please let me know.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Hello, welcome! How are you today?

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm an AI assistant who helps with data analysis and interpretation. I was trained on a vast amount of text data from various sources, including Wikipedia articles, social media posts, and online forums.

I can help with various aspects of data analysis, such as identifying patterns, trends, and correlations within the data.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I'm also an AI assistant.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of creative endeavors, from writing stories and poetry to creating art and music. If you're looking for something in particular, I'd be happy to assist with that as well. Let me know what's on your mind or if there's anything else I can help with!

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1.   Make sure to take breaks when you need them. Take a 10-15 minute walk, do some stretching or yoga, and avoid distractions like your phone.
2.   Set realistic goals for yourself and stick to them. This will help you stay motivated and avoid overcommitting.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): What is the best way to boil an egg?

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible piece of software that can replicate itself and spread around the internet. It's like a "fragment" of code that infects computers or other devices. Computers are like cities where viruses can live and grow. They can delete important files, steal sensitive information, or even help hackers to break into systems.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hey there! It's been a long time since we've had any watering, so I hope you don't mind me asking about it. I love the garden and the way it feels when my plants are watered.

Let's catch up soon and maybe get some more info from your neighbors!

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Red bell peppers
2. Red cherry tomatoes
3. Cucumber
4. Strawberries

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two related but distinct concepts. Climate refers to the long-term average weather patterns that a region experiences, including temperature, precipitation, wind, and other atmospheric conditions. It describes the overall state of the atmosphere at any given time, taking into account factors such as latitude, altitude, humidity, wind direction, and other environmental influences.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The world is changing, the leaves are falling in autumn,
Where the forest whispers secrets to me.
I feel the chill of winter's warmth on my skin,
A constant reminder that life is short and new.

In this fleeting moment, I am reminded of why I started writing –
To capture the beauty of fall, the vibrant hues,
And to share these experiences with others,
So that they may see the joy in what we're doing.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, follow these steps:

1. Use a strong, unique password that is difficult for others to guess. Consider using a combination of letters, numbers, and symbols (e.g., @sswcsssss).
2. Avoid sharing sensitive information such as your login credentials or financial information with anyone.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Sienna is a popular name for a coffee shop near a library. The term "sienna" translates to English as "small," and the coffee shop has been around since the 1960s.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): Start with a 30-minute walk at a moderate pace, stopping at 3-5 locations to rest for 10-15 minutes. Then, turn your attention to a 5-minute jog, one to two miles long, and a 3-minute sprint. Repeat this pattern until you have completed 20-30 minutes of workout.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You'll need a good quality tent or sleeping bag, and a waterproof backpack.  If you have a backpack, make sure it's long enough to carry the gear.

If you're camping, use tents that are hobby or campground-size. If you're camping in an RV park, make sure to bring a tent that can withstand the load of your RV.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering body of water that stretches across the land and surrounds everything it touches, from the towering peaks of Mount Everest to the vibrant coral reefs that stretch out as far as the eye can see. It's home to an incredible diversity of marine life, including sea turtles, dolphins, sharks, rays, and more, and its waters are teeming with colorful fish, crustaceans, and aquatic plants.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Acknowledge the invitation: Express your appreciation for the opportunity and let the person know that you're happy about their request.
2. Provide details: Explain what the party will be about, what type of food or drinks are included, and how they can help you stay engaged.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat, 2 Versuche): I will wait for the report now. Thank you for helping me with that!

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A simpler version would be: "Public transportation reduces urban congestion." 

Alternatively, you could say: "Public transportation improves urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct edit would be: "She don't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

This sentence uses the past tense form "walked," which is the correct verb tense to use in this context. The sentence would be: "I walked to the station and bought a ticket."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Welcome to Sienna's! This weekend we're featuring a sale from our specials menu, including a new summer collection and a super-rare small print vintage book. Don't miss out on this deal - it's now available for purchase at our online store!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): To turn this into a question: "The train leaves at eight o'clock."

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Sienna, a 20-year-old Canadian who lives in Edmonton.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside." 

I made a few changes to make the sentence more concise and grammatically correct. I removed "due to" as it's unnecessary in this context, and instead used "due to" to introduce the cause-and-effect relationship.

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
  **App** (sela-2, sela_chat): The short summary describes the user's journey from finding a guitar to mastering it, highlighting their progress and the impact of practice. The text does not specifically mention Tom's dog Hamish, but they do mention that he had "a good time" practicing with Hamish. This implies that Tom's experience was positive, and the user has a positive outlook on learning an instrument.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): Here is the email:

---

Subject: Project Meeting Update

Dear Team,

I hope this email finds you well. I am writing to share some updates regarding our current project.

The project meeting is scheduled for Wednesday at 2 p.m., and we will review the progress notes before the meeting.

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
  **App** (sela-2, sela_chat): If you're planning a trip to Italy, I would recommend visiting Rome. It's the capital and the biggest city in Italy.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Italian food is quite diverse, so you should try some of the local specialties like pizza, pasta, and gelato. You can also explore the famous gelato shops in Rome, which are a great place to start.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Favorite Food**: A favorite food that your mother enjoys or is proud of.
2. **Travel**: A trip or adventure that she's excited about.
3. **Family Members**: Friends, family members who are important to her and have always been there for her.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Favorite Food**: A favorite food that your mother enjoys or is proud of.
2. **Travel**: A trip or adventure that she's excited about.
3. **Family Members**: Friends, family members who are important to her and have always been there for her.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Sam is a bit stressed. Please know that Sam is not feeling stressed and will help you with the task at hand. If you need any help, feel free to ask Sam.

If this doesn't work for you, I can also try another suggestion. You could say something like: "I'm feeling overwhelmed today.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): To relax this evening, you can try the following:

1. **Take a walk**: Walk in nature or take a stroll through your city. This can help calm your mind and body.
2. **Try deep breathing**: Sit quietly for 5-10 minutes and breathe deeply. This can help slow down your heart rate and reduce stress.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The watering schedule depends on how much water the plant needs. For indoor plants, it's best to water when they are 2-3 inches deep, and when they are about an inch apart.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, regular chunks of time each day to read. Begin with short stories, poems, or chapters from your favorite books. You can also try listening to music while you read.
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
- 2 tbsp olive oil
- 1/2 cup breadcrumbs
- 1 tsp paprika
- 1 tsp garlic powder
- 1 tbsp onion powderbye
- 3 cups all-purpose flour
- 1 tsp baking soda
- 1/2 tsp salt
- 1 tbsp butter
- 1 tsp vanilla extract
- 2 tsp ground nutmeg
- Salt and pepper to taste
- Optional: breadcrumbs, paprika, or garlic powder

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
  **App** (sela-2, sela_chat, 2 Versuche): Ich bin Sela, das eigene kleine Sprachmodell von ENGRAMM. Ich kann mich unterhalten, Dinge erklären und Texte umschreiben oder zusammenfassen.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat, 3 Versuche): Ich bin Sam, ein kleiner Offline-Assistent.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den du über mich erzählt hast – wie etwa Sam oder Hamish. Du kannst auch Angaben über dich machen (z. B. dein Job, dein Alter, deine Lieblingsfarbe) und ich passe sie an deiner Bedürfnisse an. Falls es passt, lass es einfach sein!

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Pausen einplanen**: Plane deinen Tag mit einer Ruhepause zwischen Arbeit, Spielen oder einem Spaziergang. Dies hilft dir, dein Körper und Geist zu beruhigen.  
2. **Bessere Schlafqualität**: Vermeide Übernachtung und lege deine Bettwäsche vor dem Bett.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist die Energie, die durch elektrische oder chemische Reaktionen entsteht. Es gibt zwei Hauptarten:
1. **Heterogenität** (z. B. bei Stromzählen)  
   - Ein Strom fließt aus einer Spannung von 1/2 auf 100V. Die Stromstärke hängt von der Spannung ab (genauer: die *Außenspannung*).

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Beste Grüße aus Edmonton, Kanada!**  

Schreib eine kurze Nachricht an meine Kollegin:  
**Hi! Ich freue mich, dass du heute kommst – ich habe die nächste Anlaufstelle gefunden. Die nächsten Termine sind **5:00 Uhr** und **10:30 Uhr**.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **1. Zucchini (Zoodles):**  
- **Name:** „Courdillon“  
- **Gewicht:** **12,5–14,5 g**  
- **Geschmack:** süßlich und tangig, leicht knusprig, die Zucchini verleiht einem kalten Aroma.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in der richtigen Reihenfolge zerkleinert werden. Wenn du sie nicht richtig koche, kannst du sie im Ofen nicht kochen. Du solltest den Nudel nicht über Nacht in die Pfanne legen, da er sich leicht entzünden kann. Wenn du ihn später aus dem Ofen nehmen willst, dann musst du zuerst warmes Wasser oder eine vorgeheizte Sauce verwenden.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht eindeutig** oder **kurzschief**.  

### **1. Ursprung (Auftrag):**  
- **Flüsse** sind **Naturwässer**, die über Wasser laufen. Sie sind in der Regel **bedingt durch Grundwasserablagerungen** entstanden.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter im Winterland**  

Der Schnee wirft, wie ein Schmetterling,  
den Himmel mit Farben und Kälte.  
Die Sonne, die den Wind so still hält,  
ist kein Tag mehr, sondern nur der Mond.  

Er tanzt in dem Lachen des Windes,  
und die Luft ist voller Wärme, die wie Schnee vor sich hinschneidet.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du auf den **Gesundheitssatz** achten. Der besagt, dass jeder kleine Schritt eine große Wirkung auf die Gesundheit hat. Hier sind einige Tipps:  
1. **Schnellere Beleuchtung:** Halte dich bei Licht, das dich schon bedienen kann, an der Fensterbank.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Antwort:**  
Es ist wichtig, dass du:  
1. **Name und Beruf des Vorgesetzten/Hundes hervorheben** (z. B. „Sam“ oder „Hamish“).  
2. **Ergebnis schreiben** (z. B.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
*Habe ich nicht genügend Zeit, sie zu unterlagen? Dann lass es mich wissen.*  

---  
*Haben Sie Fragen zur Verfügung, die ich nicht klären kann? Fragen Sie einfach!

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Das ist eine gute Zusammenfassung, aber ich möchte etwas verbessern: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“  

Hier sind die Änderungen:  
1. **„es war“** → „das war“ (vermeidet das Präposition „war“, um den Kontext zu präzisieren).

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version:  
**„Die Veranstaltung wurde abgesagt aufgrund ungünstigen Witterungsverhältnissen.“**  

---

**Erläuterungen zu den Änderungen:**  
1. **„Ungünstige Witterungsverhältnisse“** → „Ungünstige Witterungsverhältnisse“ (präzisere Beschreibung).

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **1. Vergangenheit:** „Ich lese ein Buch.“  
**2. Zukunft:** „Ich gehe in den Park und lese ein Buch.“  
**3. ---

**1. Vergangenheit:** „Ich gehe in den Park und lese ein Buch.“

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Der Nutzer ist **Sam**, der in Edmonton wohnt.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Der Nutzer erwähnt, dass Fahrradfahren gut für die Gesundheit ist. Er unterstreicht, dass es keine Abgase und ist in der Stadt schneller als das Auto. Zudem ist es in der Stadt schneller als das Auto.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt die Bewegung von Zugvögeln in Nordamerika (Wetter, Jahreszeiten) und deren Fortpflanzung in warmen Regionen. Die Beschreibung des Frühlingseises ist metaphorisch:  

- **"Hund"** (engl. für "Hunde") kann als „Führer“ verstanden werden, der durch seine Rolle im Winter den Flugverkehr fördert.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa schwamm durch die Wüste, die Wasser riechen wie Schnee und ein starker Wind wehte über sie. Sie nahm an einem Sommerkurs teil und lernte so schnell, wie sie ihre Angst hinterließ. Nach dem Sommer kehrte sie heim, fühlte sich allein und hoffte, wieder Schwimmen zu können.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“  

**Erläuterung:**  
- **Stadtplanung (Adresse):** Edmonton  
- **Zeitrahmen (monatlicher Zeitplan):** acht Monate → **Pendler** mit **Autoverkehr** durch die Innenstadt.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk „Der Sturm“ (1789) [1].

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Nähe des Ortes **Edmonton** (ca. 2 km von hier entfernt), wo er ein linker Zufluss der **Kanalsahne** ist. Seine Quelle liegt auf dem **Hazel Mountain**, einer Höhe von etwa 5 km über dem Meeresspiegel, wo die Wassermenge durch den Hang abfällt.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er **durch seine Entdeckung der Relativitätstheorie** (Einsteinsches Gesetz) die moderne Physik revolutionierte und dadurch viele seiner Theorien über die Natur bewies. Er hat auch Nachrichtentechnik entwickelt, um in der Zukunft in Bereichen wie Medizin, Energie und Raumfahrt ein besseres Leben zu ermöglichen.

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
  **App** (sela-2, sela_chat): Ich habe eine Vielzahl von Kuchen backen können, je nach deinen Bedürfnissen! Bitte gib mir deine Angaben so ein: Name: Mia; wohnt in: Edmonton; Hund: Hamish.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Ich habe ein einfaches Kuchen: ein **Stück aus Mehl, Milch und einem Schneebesen** (auch bekannt als "Gäsekuchen" oder "Steinkuchen").
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Danke für deine Erfahrung! Probiere ich auch ein Rezept mit Kuchen, das du mit mir probieren kannst: **"Ein Erdbeer-Häutekuchen"** (eine Variante mit Zitronensaft und Vanillezucker). Bitte gib mir deinen Namen so ein.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?  
Ich lerne gerade Englisch. Danke, dass du das gesagt hast!  

Was möchtest du über mich erzählen? (Beispiel: Name, Tätigkeit oder Hintergrund)
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Ich schätze deine Hilfe. Bitte teilen Sie mir einfach den Wortschatz, den du verbessern möchtest (z. B. Wörter, Phrasen, Ausdrücke, Phrasenarten oder Satzstruktur), und ich werde dir bei der Grammatik helfen!

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Mia ist eine KI-Assistentin und kann dir helfen, einen Einladungsbrief zu schreiben. Hier sind die Schritte:

1. **Fragen**:
   - **Wer bist du?** (Beispiel: *„Wie viele Jahre lebe ich in Edmonton?“*)
   - **Was willst du über mich wissen?** (z.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): **Was du über Mia wissen solltest:**  
- **Datum und Zeit**: Bitte gib den Namen des Geburtstages (z. B. „My birthday is on [insert date and time]“).  
- **Bereich/Ort**: Falls gewünscht, kann ich dir auch helfen, die Veranstaltung in Edmonton zu organisieren.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist der **Laufen**. Es gibt viele verschiedene Arten, wie man sich auskennt, aber ich würde es gerne mit einem Spaziergang an einem **Fluss** oder einer **Mündung** in Edmonton kombinieren. Der **Wasserfall** ist ein wunderbarer Ort, um sich am Abend zu erholen und das Herz zu beruhigen.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das ist abhängig von deiner Größe, dem Wetter und der Anzahl der Aktivitäten. Bei uns in Edmonton gibt es einen **Sonderpreis für kleine Projekte**: Der Preis ist im **Jobs-Spaß-Bereich** (2–4 Stunden) und bei Gruppen (mindestens 5 Personen) relativ hoch.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel auf dem Boden und fressen die Insekten wie Vögel. Pinguine haben eine sehr große Nase, die sie auch bei der Jagd verwenden kann. Wenn sie ein Objekt näher kommen, heben sie ihre Flügel an und steigen mit der Luft in Bewegung [1].

