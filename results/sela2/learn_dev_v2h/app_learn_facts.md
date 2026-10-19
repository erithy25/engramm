# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T12:54:26Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 0 von 100 |
| identity_error | 0 von 100 |
| echo | 1 von 100 |
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
  **App** (sela-2, sela_chat): Hi! Was looking for help with a math problem.

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
  **App** (sela-2, sela_chat): Goodbye! That's a great way to end the day.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a native Perth resident who lives in Perth. I'm currently working as an assistant at the Perth City Council.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 2 Versuche): Lucy

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I'm here to help you learn new things. You can ask me anything, and I'll do my best to assist you. What's the first thing you'd like to know?

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Avoid distractions: Try to keep your workspace organized and clutter-free so you can focus on your work without interruptions.
2. Set clear goals: Before starting your workday, set specific, measurable objectives that will help you stay focused. This could be something as simple as "I want to complete this project by the end of the week" or "I need to learn a new skill in order to get promoted."

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): There are two ways to boil an egg: the **direct method** and the **indirect method**.

### Direct Method:
1. Prepare the pan or pot with water.
2. Add the egg yolk (the white part) to the water.
3. Cover the pan or pot with the water and cook for 5-10 minutes, stirring occasionally.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible threat that spreads through the internet. It's like a "hijack" of your computer's system, making it hard for you to use or do things. Viruses can make you feel sick or even hurt you, so you need to be careful when using your computer.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Can you water my plants next week? I really need your help."

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. citrus fruits like oranges, lemons and grapefruits
2. strawberries
3. tomatoes
4. kiwi
5. citrus fruit such as orange juice or lime juice

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): The weather is the state of the atmosphere, while the climate is the type of environment that exists within it. Weather refers to the conditions in a place that affect how people live and interact with their surroundings. Climate, on the other hand, refers to the overall pattern of weather conditions over a long period, including precipitation, temperature, humidity, and wind patterns.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The sun dips low, a warm orange glint in the air,
As autumn leaves drop like a gentle breeze,
Their vibrant colors and amber glow,
A painter's dream to capture.

Crimson and gold are the hues of the day,
The earth exhales its breath in soft kiss,
In every leaf, a whispered promise,
Of a long-lost life that never comes back.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some tips to make your password more secure:

1. Use a strong, unique password. Avoid using something easily guessable like your name or birthdate. Instead, use a combination of letters, numbers, and symbols (a mix of uppercase and lowercase letters). For example: "PASSWORD123456789".

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. The Cat cafe – The shop is close to the library and has a large selection of coffee, books, and other supplies. It's also a great place to take a break from reading.
2. The Patio Café – This shop is near the library and offers a variety of coffee drinks and pastries.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): Sure! Here's a 20-minute workout plan that uses basic equipment to build muscle, strength, and endurance. You'll need:

1. A pair of dumbbells (8–10 inches in diameter) for weightlifting
2. A resistance band or weights (optional)
3.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You will need:
- A warm and waterproof tent with a sleeping bag
- Sleeping pads
- Toiletries (toilet, toothpaste, toothbrush, etc.)
- A water filter or purification tablets
- Clothing suitable for the weather conditions
- A sleeping pad
- Any necessary gear for camping (sleeping bags, flashlights, headlamp, etc.)

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark expanse that stretches across the globe, its depths often reaching heights of over 600 meters. It's the deepest part of our planet and holds more secrets than any other place on earth. The ocean is home to countless creatures, from tiny plankton to massive whales, and plays an important role in regulating the climate and weather patterns around the world.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. **Be polite**: Use phrases like "I'm happy to have you here, but I'd prefer it if you could come in later." This shows that you value your invite and won't be interrupting.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text: "Send me the report now."

I changed "Send" to "Send", as "Send" is the correct verb form for sending something. I also changed "now" to "now", which is the correct spelling of the verb. Additionally, I removed the phrase "in Perth" and replaced it with "in Perth", as the city's name is not necessary in this context.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A simpler version could be: "Public transportation reduces urban congestion." 

Alternatively, you could simplify it to: "Public transportation improves urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct edit would be: "She don't like going to school on mondays."

### en30 (rewrite) – echo
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 3 Versuche): "I walk to the station and buy a ticket."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "We're closing for a sale this weekend! Take a look at our unique deals today and make the most of your shopping experience."

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat, 2 Versuche): The train leaves at 8:00 o'clock.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): "Dear [User's Name], I hope this message finds you well. I am a resident of the city and have recently returned from my trip to Australia."

I made a few changes to enhance the tone:
- Changed "Hey" to "Dear" for a more formal greeting.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside."

I made a few changes to make the sentence more concise and grammatically correct. I removed "due to" as it's unnecessary in this context, and changed "it was raining very heavily outside" to "heavy rain outside" to make the language more formal and precise.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made the following changes to improve clarity and grammar:

- Changed "will be" to "will be" (correct verb form)
- Added an article ("the") before "suitability" to make it clear that the library is open on Mondays only
- Changed "it will reopen on Tuesday at 9 a.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This is a short summary of Tom's story:

Tom started learning the guitar at age three. He learned it from his parents and spent much time practicing with them. By the age of five, he was playing a song on his own and was soon able to play songs for friends. His fingers hurt when he sang, but eventually he began to enjoy practicing and enjoying music.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The user's email is: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

Here's a brief summary of the action taken by the user and some details about the plan:

1.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): "Recycling turns used materials like paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."

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
  **App** (sela-2, sela_chat): Venice is the city to go first. It's a great place to see all the famous landmarks like the Colosseum, Roman Forum, and Pantheon.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): There's a lot to see and do in Venice. You should try some classic Venetian dishes like pizza, gelato, and pasta. Don't forget to visit the famous Rialto Market for fresh seafood and gelato.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here's a birthday card for your mother:

---

**Happy Mother's Day!**  
My parents are both grown and busy, but they still love spending time with me.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version:

---

**Happy Mother's Day!**  
My parents are both grown and busy, but they still love spending time with me.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Here's a possible response:  

"Hey Sam, it's okay to feel stressed. Life can be tough, especially when you're new to the city. But taking care of yourself is crucial for managing stress and maintaining good mental health. If you're feeling overwhelmed or struggling with worries about work or school, don't worry – talking to your friend Rex or family members about your concerns might help.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Here's a possible response:  

"Relaxing your mind is essential for relaxation. Try taking some deep breaths, going for a walk outside, or listening to calming music. You can also try guided meditation apps like Headspace or Calm. These tools help you focus on your breath and calm your thoughts.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The answer is a good thing. Water the plant when it's wet but not waterlogged. You can buy a small container of water in the garden store, or you can use a drip irrigation system. I recommend using a drip irrigation system because it's easier to water the plants that are root-bound like carrots and beets.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with short books and try to read them in your free time. Try to avoid the temptation to get sucked into a book that's too long or boring. Also, consider downloading a library app like Readability or Bookworm to help you stay on track.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found these resources helpful. Have you ever considered finding a library or reading group in your area? Many libraries and book clubs offer free access to books and materials, which can be a great way to meet like-minded people who share your interests.

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
- 3/4 cup shredded lettuce
- 1/4 cup tomato sauce
- Salt and pepper to taste
- Freshly sliced tomato
- Parmesan cheese, grated
- Fresh parsley, chopped
- Salt and pepper to taste
- Grated Parmesan cheese, grated
- Optional: fresh herbs, such as basil or mint

Instructions:
1.

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen!

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat, 2 Versuche): Gern geschehen!

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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den Nutzer deiner Wahl und den Kontext deiner Geschichte an. Falls du möchtest, kannst du auch ein Bild oder eine Beschreibung deines Nutzers hinzufügen, um mehr über ihn zu erfahren.  

Wenn du Hilfe brauchst:  
1. Teilen Sie mir mit, ob es sich um eine personalisierte Antwort handelt (z.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Einschränkung der Schlafzeiten**: Stelle sicher, dass du zwischen 7 und 8 Uhr wach bist, um die nötigen Schlafrhythmus zu finden.  
2. **Gesundheitliche Ernährung**: Verwende natürliche Schlafmittel wie Lavendelblütenblätter oder Tofu und halte deine Ernährung konsequent: Probiere sie zuerst aus und nehme dann in den Morgenstunden.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das menschliche Körper erzeugt wird. Er gibt Energie für Bewegungen, Muskeln und Knochen. Strom ist auch die Energie, die wir brauchen, um Dinge zu bewegen (z. B. ein Auto oder ein Computer). Es fließt aus der Erde, an den Händen und Füßen und aus dem Körper (Körper und Fett).

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Subject:** Nachricht an meine Kollegin, dass ich heute komme  

Hi [Name],  
Ich bin [Name] und freue mich, heute zu kommen. Ich habe in Perth gewohnt, mit meinem Hund Rex (drei kleine Katzen) und habe mich über den Alltag des Nutzers in der Region informiert.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **1. Rote Kresse (Helianthus annuus)**  
*Zubereitung*: Für einen zarten, sauren Geschmack: Blätter von 3–4 cm Länge, etwa 1 kg Gewicht, schälen und in feine Würfel schneiden. Den Boden damit fassen und anschließend 1 Stunde bei mittlerer Hitze ziehen.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem warmen Wasserbad gelagert werden.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht direkt sichtbar** (z. B. das Fließen eines Flusses versus die Seewärme). Sie sind jedoch **verschiedene Eigenschaften**, die durch unterschiedliche Faktoren beeinflusst werden können. 

### **1. Fluss vs. See**:
- **Fluss**: Ein längerer Fluss (mindestens 10 Kilometer) mit hohem Gefälle, Flüssen oder Seen.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter’s Wrath**  

Die Frostflocken ballen über die Hügel,  
ein Labyrinth aus Gold und Silber,  
der Schnee tanzt in den Himmel.  
Der Schnee ist wie ein silberner Schatten,  
der Himmel ein leises Lied, das nur die Luft singt.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du kleine, effiziente Änderungen in deinen Alltag vornehmen. Hier sind einige Tipps:  
1. **Bessere Haushaltsgeräte**: Nutze dein Handy/Smartphone statt Brennstoffzelle (z. B. Feuerzeug oder Akkus).

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Um zu einem Vorstellungsgespräch mitzunehmen, sollten folgende Gegenstände vorhanden sein:  
1. **Persönliche Dokumente**: Ein passendes Foto von dir (z. B. eine Fotoserie), ein Lebenslauf, ein selbstgeschriebenes Profil.  
2. **Praktische Fragen**: Eine strukturierte Frage über deine Stärken und Schwächen, wie zum Beispiel: „Welche Rolle spielen deine Erfahrungen bei der Entwicklung des Hunde-Smartphones?“

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
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt zu betonen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Hervorgehobener Satz:**  
„Ich gehe in den Park und lese ein Buch.“  

---

**Erklärung des Änderungen:**  
1. **Verbindung zwischen Vergangenheit und Gegenwart:** Der Nutzer wurde nach Perth gezogen, um dort zu arbeiten. Das Verb „lese“ vermittelt einen zeitlichen Zusammenhang: Der Nutzer beginnt mit einer Handlung (im Park), die in der Zukunft stattfindet (in den Park).

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich neutral und betont den Nutzer als Person. Sie ist an eine höfliche, aber nicht formalen Stelle gebunden.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

**Erklärung:**

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Im Text geht es um die Zugvögel in den Süden und ihre Fortbewegung, wobei der Nutzer (Sam) als **wärmerer, jedoch nicht direkt geografischer Kontext** genannt wird. Die Regel gilt für Vögel, die in wärmeren Gebieten brüten, nicht aber in denen, die sich auf den Süden konzentrieren.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst überfordert von dem tiefen Wasser, das sie mit einer Trainerin unterbrach. Doch nach einem Sommer ließ sie sich durch eine ganze Bahn ohne Pause schwimmen und entwickelte ein gutes Grundgefühl.  

**Erklärung der Änderungen:**  
1. **„Schloss“ → „Wasser“:** Die Übersetzung ist dynamischer und vermeidet Wiederholung („Wasser“, „Schloss“).

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
  **App** (sela-2, sela_chat, 3 Versuche): Meine Quellen sagen dazu nichts.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in Richtung Nord- und Südwestförderung. Er entspringt im Bereich der kanadischen Provinz British Columbia in einer Tiefe von etwa 600 Metern, fließt dann durch den indischen Subkontinent (z. B. Indien), mündet schließlich in die Nordsee. Der Fluss verläuft meist entlang des Bundesstaates Ontario, bevor er sich in den Golf von Mexiko verzweigt.

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
  **App** (sela-2, sela_chat): Rex wohnt in Perth.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Rex wohnt in Perth.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Rex wohnt in Perth.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?  
Was interessiert dich besonders?  

---

**Hintergrund:**  
1. **Meine Erklärung:**  
   - Ich lerne Englisch und wohne in Perth.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Hier sind einige Tipps:  
1. **Verben lernen:**  
   - *"Ich lerne Englisch"* → *"I am learning English."*  
   - *"Das ist ein guter Tag"* → *"The day was a good one."*  

2.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Hier sind einige Tipps, um einladungsschema zu erstellen:  

1. **Nächste Woche**  
   Schreibe die Einladung an den Nutzer (im Deutschen schreiben Sie „mich“), dann an Rex und später Mia.  

2. **Für alle:**  
   Wenn du keine festen Angaben hast, schreib nur eine Einladung, egal ob es sich um einen Freund, eine Firma oder eine Person handelt.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Ja, es ist eine Geburtstagsfeier am Samstag um 18 Uhr.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist der **"Wald-Fischelauf"**, bei dem man kleine Fischstücke in einen großen Meeresspiegel zieht und das Wasser untereinander ziehen muss. Das führt zu einer starken Biodiversität, da Fische die Wassertemperaturen wechseln und sich durch ihre kühle Lage stabilisieren.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet **etwa $10-$20**. Das macht es sehr viel Spaß, die Fische zu fischen und ihnen Wärme abzugewöhnen. Für das Wasser sind **kleine Fische** ideal, da sie sich leicht in der Tiefe bewegen lassen und das Wasser stabilisieren.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

