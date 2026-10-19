# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T13:26:54Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 1 von 100 |
| identity_error | 0 von 100 |
| echo | 1 von 100 |
| cut_off | 1 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| error | 0 von 100 |
| prompts_with_a_problem | 3 von 100 |

Antworten nach Modell: {'engramm': 21, 'sela-2': 96}; nach Art: {'about': 1, 'answer': 3, 'learned': 4, 'sela_chat': 89, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 4 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! I love stories about the city and its people. What would you like to know about me?

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
  **App** (sela-2, sela_chat): No problem! You're welcome.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): I will send a message to Sienna, Hamish and their dog. Goodbye!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm an AI assistant who helps users like you with questions about your experience, goals, and interests. I'm not a real person, but rather a helpful AI designed to provide information and insights related to our conversation.

Sienna lives in Edmonton, Canada, and Hamish is a Labrador Retriever.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I've written several books about Canadian history and culture.

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
  **App** (sela-2, sela_chat): 1. Schedule regular breaks
2. Take short breaks to rest
3. Use a timer app or a timer for productivity
4. Make time for self-care
5. Keep your work environment organized and tidy
6. Get enough sleep
7. Eat healthy meals

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): If you boil an egg, it will be soft and firm. To make the yolk stay soft, add water and cook until the yolk is pink in color.

When cooking for this, place the egg on a large baking sheet and cook for 1-2 minutes until it turns white.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible threat that makes your computer do something it shouldn't. It's like a mischievous spirit who tricks you into doing something that could cause harm. Viruses can be scary, but they're not always dangerous. They can help make you feel better or even hurt you.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hey Sienna,

I hope you're doing well! I just wanted to let you know that I'm getting a little watermelon plant right now. It's a beautiful specimen, and I love seeing the flowers. If it rains today, I'll water it, but if not, I'll keep watering until tomorrow!

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Strawberries
2. Cherry tomatoes
3. Strawberry juice
4. Blackberries

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two related but distinct concepts. Climate refers to the long-term average weather patterns that a region experiences, including temperature, precipitation, wind, and other atmospheric conditions. It describes the overall state of the atmosphere at any given time, which can vary greatly depending on factors such as latitude, altitude, and time of year.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The world is changing, the leaves are falling in autumn,
Where the forest whispers secrets to me.
I feel the chill of winter's breath,
And I'm at my wit's end.
The maple trees seem to close their eyes,
As if waiting for the next burst of light.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, follow these steps:

1. Use a strong, unique password that is difficult for others to guess. Consider using a combination of letters, numbers, and symbols (e.g., @sswd) instead of just one letter or number. Avoid using easily guessable words like "password" or "secret."

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Sienna's Coffee Shop near the library.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): **Simple 20-minute workout plan using equipment:**

1. Start with 30 seconds of light exercise (like walking or jogging) on your treadmill, stationary bike, or bodyweight machine.
2. Move to a moderate pace (20-30 mph) and pedal forward for 10 seconds.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You'll need a good quality tent or sleeping bag, and a waterproof jacket. Bring warm clothing, including a sweater, gloves, socks, and a blanket. Pack extra snacks and water for the hike to stay hydrated. Pack comfortable shoes and a long-sleeved shirt. Pack essential items like a first aid kit, flashlight, and a compass.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering body of water that stretches across the land and surrounds our planet, with its turquoise depths, vibrant coral reefs, and deep-sea vents. It's the only place on Earth where life thrives, and it holds secrets about our past, present, and future, giving us insight into the Earth's history and evolution.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Acknowledge the invitation: Express your appreciation for the opportunity and let the person know that you're happy to be invited.
2. Provide some context: Share a brief background or experience related to the event, such as the date, time, location, or any special requests.

### en27 (rewrite) – echo
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat, 3 Versuche): Send me the report now.

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

This sentence uses the past tense in two ways: (1) it describes an action happening at the present moment, and (2) it implies that the event occurred before the action took place. 

The verb "walk" is used in the past tense form because it's part of a past continuous action, which can be completed by another action.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "We're about to embark on a fun and exciting weekend, with a unique sale planned for this weekend. Stay tuned for more details!"

Or, if you'd like to add more detail: "Our shop is offering a great deal on Saturday and Sunday, with discounts available for all three dates.

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): Sienna: Hello, Sienna. Can you tell me how many hours it will take to get from Edmonton to Edmonton?

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Sienna, a seasoned member of the Edmonton community, has graciously agreed to attend your event for tomorrow's meeting.

I made some changes to formalize the tone and make it more suitable for formal writing. I replaced "sorry!" with "happily," which is a more professional and polite way to express surprise or appreciation.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside." 

I made a few changes to make the sentence more concise and grammatically correct. I removed "due to" as it's unnecessary in this context, and instead used "due to" to introduce the cause-and-effect relationship.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library will be closed on Monday for repairs to the heating system, with reopening on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This summary is based on a short story about Tom, who wants to learn the guitar. It provides a brief overview of his journey from a beginner to an accomplished musician.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): Here is a summary of the email:

- The team is moved to Wednesday at 2 p.m., but not exactly, due to the project meeting. 
- The progress notes for the website launch are brought in on Thursday at 2 p.m. 
- The next steps will be detailed on the website launch page on Friday at 2 p.

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
  **App** (sela-2, sela_chat): Italian food is quite diverse, so you should try some of the local specialties like pizza, pasta, and gelato. You can also explore the Italian countryside with its rolling hills and charming villages.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn) – cut_off
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Name:**  
   - Sam  
   - Hamish  
   - Emily  

2. **Age:**  
   - 13 (oldest child)  
   - 18 (youngest child)  
   - 20 (middle child)  
   - 22 (older child)  
   - 21 (youngest child)  
   - 23 (youngest child)  
   - 24 (older child)  
   - 25 (older child)  
   - 26 (older child)  
   - 27 (youngest child)  
   - 28 (youngest child)  
   - 29 (youngest child)  
   - 30 (youngest child)  
   - 31 (older child)  
   - 32 (youngest child)  
   - 33 (youngest child)  
   - 34 (older child)  
   - 35 (older child)  
   - 36 (older child)  
   - 37 (older child)  
   - 38 (older child)  
   - 39 (older child)  
   - 40 (older child)  
   - 41 (older child) …
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Name:** Sam  
   - Hamish  
   - Emily  

2. **Age:** 13 (oldest child)  
   - 18 (youngest child)  
   - 20 (middle child)  
   - 22 (older child)  
   - 21 (youngest child)  
   - 23 (youngest child)  
   - 24 (older child)  
   - 25 (older child)  
   - 26 (older child)  
   - 27 (older child)  
   - 28 (older child)  
   - 29 (older child)  
   - 30 (older child)  
   - 31 (older child)  
   - 32 (older child)  
   - 33 (older child)  
   - 34 (older child)  
   - 35 (older child)  
   - 36 (older child)  
   - 37 (older child)  
   - 38 (older child)  
   - 39 (older child)  
   - 40 (older child)  
   - 41 (older child) …

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): I can help you with that! Feel free to share your feelings, and I’ll do my best to provide some advice. What are your thoughts about stress? Is there anything that you’d like to talk about?
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): To relax this evening, try taking a few deep breaths and doing some light stretching. You could also listen to calming music or nature sounds around you to help calm your mind. If you’re feeling anxious, you might want to try deep breathing exercises or progressive muscle relaxation.

Another way to relax is to focus on the present moment.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): I don't know. Most people water it every 2-3 weeks. But some people use a waterer instead, or give it a drink to make sure the soil is moist.

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
- 1/4 cup of mayonnaise or ketchup (optional)
- 1 tbsp olive oil
- Salt and pepper to taste
- Fresh parsley, dill, or basil leaves for garnish

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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den du über mich erzählt hast – egal wie klein oder groß es ist. Ich kann dir helfen, deine Angaben zu korrigieren, Vorschläge zu machen, deine Sprache zu verbessern, oder einfach nur Ratschläge geben, die Spaß machen! 

Für eine einfache Frage kannst du einfach sagen: "Könntest du mir bitte etwas über dich erzählen?"

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Morgen frühzeitig schlafen**: Melden Sie sich am besten im Bett, wenn möglich (z. B. mit einem Schlafsack oder einem Schlafsack mit beruhigendem Stoff).  
2. **Strukturen schaffen**: Wachen Sie erst am Morgen abends und beachten Sie die Tagesordnung, um Ablenkungen zu reduzieren.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist die Energie, die durch elektrische oder chemische Reaktionen entsteht. Es gibt zwei Hauptarten:
1. **Heterogenität** (z. B. bei Stromzählen)  
   - Ein Strom fließt aus einer Spannung von 1/2 auf 100V. Die Stromstärke hängt von der Spannung ab (gerade oder gerichtete).

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Lieber [Name],**  

Ich freue mich, heute zu kommen. Ich habe eine kurze Nachricht für Sie geschrieben und hoffe, dass sie meine Gedanken und Gefühle erfüllt.  

Willkommen!  

---  
*Mit freundlichen Grüßen,*  
Sam

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **1. Zucchini (Zoodles):**  
- **Name:** „Courdillon“  
- **Gewicht:** 3,5 kg  
- **Verwendung:** Frühzeit Gemüse wie frischen zuckerfreien Teig oder frisch geerntete Keks als Nährboden.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in der richtigen Reihenfolge gerieben werden, um ein leises, aber nicht zu lautes Geräusch zu erzeugen. Für eine optimale Nudeln-Mischung empfehlen sich:
1. **Rieben Sie die Nudeln an einem warmen Ort** (z. B.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht eindeutig** oder **kurzschief**.  

### **1. Ursprung (Auftrag):**  
- **Flüsse** sind **Naturwässer**, die über Wasser laufen. Sie sind meist in der Nähe von Seen, Flüssen, Ozeanen oder Wüsten anzutreffen.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter's Tale**  

In den Schneewasser trommelte die Welt,  
ein Schneetreiben im Schnee, ein Lied der Wiesen.  
Die Nacht, ein kaltes Kind, das weinte,  
in die Eisklimazone kletterte.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, sollten Sie regelmäßig Haushalte über eine bessere Energieversorgung verfügen. Hier sind einige Tipps:  
1. **Bleiben Sie in der Sonne:** Achten Sie darauf, dass alle Türen und Fenster geschlossen sind, um Strahlung abzuschirmen.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Was sollte ich zu einem Vorstellungsgespräch mitnehmen:**  
1. **Name und Position**: Einladungen an, um den Eindruck von Interesse zu vermitteln.  
2. **Fokus auf Fragen oder Aufgaben**: Antworten darauf, was du willst (z. B. „Wie gefällt dir das Design?“

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
*Habe ich sofort die Unterlagen?*  
**Wollen Sie zuerst die Dokumente lesen?**

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Das ist eine gute Zusammenfassung, aber ich möchte etwas verbessern: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“  

Hier sind die Änderungen:  
1. **„es war“** → „das war“ (vermeidet das Passiv, da es um einen Zeitraum geht).

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version:  
**„Die Veranstaltung wurde abgesagt aufgrund ungünstigen Witterungsverhältnissen.“**  

---

**Erläuterungen zu den Änderungen:**  
1. **„Ungünstige Witterungsverhältnisse“** → „Ungünstige Witterungsverhältnisse“ (präzisere Beschreibung).

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Past Satz:**  
„Ich gehe in den Park und lese ein Buch.“  

---  
*Sam:* „Ich gehe in den Park und lese ein Buch.“  

**Past Satz:**  
„Ich gehe in den Park und lese ein Buch.“

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Der Nutzer ist **Sam**, der in Edmonton wohnt.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Der Nutzer schreibt: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig.“  

### Begründung:  
1. **„Wahrheit“** (die konkrete Handlung): Der Fahrer setzt klar auf „Fahrradfahren“, was die Handlungssprache betont.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt die Bewegung von Zugvögeln in Nordamerika und Kanada, wobei die Reihenfolge der Sagen klar ist:  

1. **Im Herbst**  
   - Vögel fliegen oft Tausende Kilometer (z. B. aus Edmonton nach Chicago).  

2. **Im Frühling**  
   - Sie kehren zurück, um zu brüten.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa schwamm im Sommer mit einer Trainerin, die sich auf die Technik konzentrierte. Die Trainerin hatte sie bereits nach einem Sommer trainiert und sah ihre Fortschritte an. Der Sommer war ein Highlight für Lisa, denn sie hatte sich entschlossen, nicht nur Schwimmen, sondern auch andere Sportarten zu lernen.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses.**  
Der **Radweg** soll die Sicherheit für Pendler und den Verkehr in der Innenstadt erhöhen. Die Bauarbeiten beginnen im März und dauern etwa acht Monate, wobei das Projekt mit einer Kostenersparnis von bis zu 30 % beginnt.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk „Der Sturm“ (1789) [1].

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Nähe des Ortes **Edmonton** (ca. 2 km von dort entfernt), wo er bis zu 5 km lang ist und eine Länge von ca. 3 km aufweist.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er **durch seine Entdeckung der Relativitätstheorie** (Einsteinsches Gesetz) die moderne Physik revolutionierte und das Verständnis des Universums und seiner Strukturen nachhaltig prägte. Es war eine **Wissenschaftliche Revolution**, bei der er die Grenzen der wissenschaftlichen Kenntnis durch Theorien wie die Theorie der Relativität verschob und sie in ein umfassendes Universum integrierte.

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
  **App** (sela-2, sela_chat): Ich habe einen Kuchen backen lassen, aber ich könnte ihn noch etwas verfeinern. Bitte teilen Sie mir mit, ob du eine bestimmte Stärke (z. B. Schokolade oder Vanille) brauchst! Ich hoffe, der Kuchen ist zufriedenstellend und kann bei dir selbst serviert werden.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist die Schokoladekuchen. Sie sind in der Regel nicht unbedingt toll, aber sie schmecken hervorragend. Falls du möchtest, kannst du die Kuchen auch mit einem Ei oder einem Vanille-Schokoladenstück servieren.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Natürlich! Ich freue mich, dir den Kuchen zu zeigen und hoffe, er schmeckt deine Erwartungen an.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?  
Ich lerne gerade Englisch und komme bald nach Edmonton. Soll ich dich in deiner Sprache einfügen oder etwas über mich erfahren?  
Du musst deine Angaben nicht vergessen, damit ich dir deine Sprache erklären kann.   
Und wenn du Fragen hast, schreib mir einfach deine Schreibweise an.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Hier sind einige Tipps, wie du deine Wortschatz verbessern kannst:  
1. **Sätze ordnen**: Ersetze Sätze nach Thema oder Zielgruppen (z. B. "Meine Lieblingshundsängerin ist die Sängerin").  
2. **Präteritum schreiben**: Schreibe immer eine kurze Erklärung des Prepositionen vor dem Wort.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): **Antwort:**  
Ich helfe gerne bei der Einladung! Bitte melde dich einfach über [E-Mail-Adresse] an, und ich werde dir helfen, eine präzise, professionelle Antwort zu schreiben.  

---

###  **Aktueller Stand:**  
Ich habe die Einladung in der nächsten Zeit überprüft.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): **Antwort:**  
Ich habe die Einladung bereits in der nächsten Zeit geprüft. Bitte melde dich einfach über [E-Mail-Adresse] an, und ich werde dir helfen, eine professionellere und passende Antwort zu schreiben.  

---

###  **Aktueller Stand:**  
Ich habe die Einladung noch nicht aktualisiert.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist:  
1. **Besteht aus einer Leidenschaft** (z. B. Baking, Gitarre spielen, Radfahren)  
2. **Nicht nur ein Hobby**, sondern auch eine Lebensaufgabe** (z. B. Kochen, Gitarrenspielen, Schwimmen)  
3.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet:  
1. **Zeit** (insbesondere wenn es um eine Leidenschaft geht, die zu einem Preis ist).  
2. **Spezialeffekte** (z. B. ein Streichinstrument, eine Gitarre mit einer neuen Stimmung)  
3.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel auf dem Boden und fressen Samen. Viele Arten haben spezielle Flügel, die sie nutzen, um sich zu bewegen und ihre Nahrung zu suchen. Wenn ein Pinguin sich bewegt, bewegt es sich mit einem Flügel, das sich zwischen zwei Federn befindet.

