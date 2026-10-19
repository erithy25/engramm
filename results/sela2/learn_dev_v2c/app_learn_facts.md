# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T08:30:00Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 1 von 100 |
| identity_error | 0 von 100 |
| echo | 1 von 100 |
| cut_off | 0 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| error | 0 von 100 |
| prompts_with_a_problem | 2 von 100 |

Antworten nach Modell: {'engramm': 21, 'sela-2': 96}; nach Art: {'about': 1, 'answer': 3, 'learned': 4, 'sela_chat': 89, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 4 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi!

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well! I hope you're having a great day. How was your weekend so far?

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help you today?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): Nice to hear from you! I'm glad I could help you out. Let me know if there's anything else I can assist with or if you need further information about our conversation.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Hello, how can I help you today?

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a 35-year-old Australian woman living in Perth, Australia.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I'm a 17-year-old high school student from Perth, Western Australia.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of creative endeavors, from writing stories to creating music. Whether you're looking for inspiration, seeking ideas for a project, or simply wanting to hear about something new, I'm here to assist. What do you need help with?

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Break your tasks into smaller, manageable chunks.
2. Set specific goals for each day or week, and track progress.
3. Get enough sleep, eat a nutritious meal, and exercise regularly to stay energized.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): This is a simple recipe that uses the yolk as a natural preservative to keep the egg soft and safe to use. The yolk contains cholesterol and has anti-inflammatory properties.

You can boil the egg in water, but if you don’t have access to a microwave or stove, you can also try using a pot of boiling water or a pan with a lid.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible threat that spreads through the internet. It's like a big, messy mess of code and error messages that can make your computer feel sick or hurt. When it tries to do something wrong, it uses its own code to cause chaos, just like how a virus spread through the internet.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): It's been a few days since you've asked me to water your plants. I just finished up my last watering session for Rex and am really pleased with how things are going! We've had some great success this year with his new water feature that helps him stay hydrated.

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Strawberries
2. Cherries
3. Strawberries and strawberries
4. Chili peppers
5. Eggplant

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): weather: cold, wet, windy; climate: warm, dry, hot.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The trees, like autumn leaves, fall
neath the amber light of the sky.
They unfurl their delicate wings and dance
with laughter and fireflies in a fleeting grace.

In every leaf's vein, a whispered promise
of warmth and comfort, of life's sweet surprise.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, follow these steps:

1. Use a strong, unique password.
2. Avoid sharing passwords with others.
3. Consider using a salted or cracked password to protect against common attacks.
4. Update your browser's security settings regularly to ensure the best possible protection.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. The Green Lily Café: Located in a quaint, seaside town, this cozy café is nestled in the heart of the library's historic building. It offers a selection of freshly brewed coffee and pastries to suit different tastes.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): A 20-minute workout without equipment should be done as follows:
1. Set a timer for 5 minutes.
2. Take a 5-minute walk or jog to get some fresh air.
3. Do 10-15 push-ups, 3-4 sit-ups, and 3-5 jumping jacks.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You'll need a good quality camping bag with all the essentials. A light weight backpack or daypack is great for carrying your gear and can be refilled in case you need to pack more. You'll also want a water bottle, snacks, and plenty of non-perishable food for each day.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering body of water that covers nearly half of the Earth's surface, offering a mesmerizing display of light and color. It stretches out in all directions, with towering peaks, dappled waves, and sparkling blue waters that surround it like a mystical realm. Its depths range from 2,000 to 5,000 meters, making it one of the most mysterious and awe-inspiring natural wonders on the planet.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Acknowledge the invitation: Express your appreciation for the opportunity and let the person know that you're happy to be invited.
2. Provide some context: Share a brief description of what you hope to have at the party, such as a relaxing atmosphere or a specific agenda.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): I'm sorry, but I can't help with that. However, if you'd like to request a copy of the report, I can assist with that!

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): Here's a simpler version: "Public transportation reduces urban congestion." 

Or, if you'd like to make it even shorter: "Public transportation helps reduce urban congestion." 

Alternatively, you could also use "causes a reduction in urban congestion" for an even more direct connection: "By reducing urban congestion, public transportation helps reduce urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "She doesn't like going to school on Mondays."

I added an apostrophe to "mondays" because it indicates possession, and I also removed the comma after "on" to improve clarity. The word "don't" is incorrect in this context, so I changed it to "doesn't like".

### en30 (rewrite) – echo
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 3 Versuche): "I walk to the station and buy a ticket."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Welcome to our fantastic shopping destination! Our shop has a sale this weekend - I’m thrilled to share the exciting news with you!"

I added "Fantastic news" to emphasize the excitement and highlight Lucy's positive response. This change makes the sentence more engaging and dynamic, drawing the reader in and making them more likely to follow along.

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): To turn this into a question: "The train leaves at eight o'clock."

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): I apologize for the inconvenience. Please provide the details of your situation, and I will ensure that all necessary steps are taken to resolve the issue.

Please note: this is a polite response intended for educational purposes only. If you have any questions or concerns regarding my response, please do not hesitate to reach out to me directly.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside."

I made a few changes to make the sentence more concise and grammatically correct. I removed the phrase "due to," which can sometimes make sentences feel wordy or unclear. I also changed "it was raining very heavily" to "heavy rain outside," which is a more direct and idiomatic way to express the same idea.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made a few changes to improve clarity and grammar:

- Changed "will be closed" to "will be closed" to make the sentence more concise.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This is a short summary of Tom's story:

Tom started learning the guitar at age three. He began practicing by playing his favourite song, "Tom wanted to learn the guitar." By the time he was five years old, his fingers hurt and chords sounded wrong. Despite this, he practised for fifteen minutes every day, working on the songs himself.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

The email includes:
- A brief introduction (about Lucy) and a clear statement about the reason for the move.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Here's a brief summary:

1. **Recycling turns used materials into new products** (e.g., paper, glass, plastic).  
2. **Sorting waste correctly at home makes recycling much more effective** (e.g., sorting waste correctly at home reduces landfill waste).

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
  **App** (sela-2, sela_chat): Venice is the city you'll want to visit. It's famous for its beautiful architecture, art, and delicious food.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): You can try all sorts of Italian dishes. Some popular ones include pizza, pasta, gelato, and pizza. You can also try seafood like salmon or mackerel.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Sure! Here's a simple and heartfelt birthday card for your mother:

1. Write her name on the back (make it fun!)
2. Cut out her favorite colors (red, blue, green)
3. Use scissors to cut out her picture
4. Write "Happy Birthday" on top of the picture
5.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Sure! Here's a shorter version of the birthday card:

1. Write her name on the back (make it fun!)
2. Cut out her favorite colors (red, blue, green)
3. Use scissors to cut out her picture
4. Write "Happy Birthday" on top of the picture
5.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): I can help you with that! It's okay to feel stressed, and it doesn't mean you're not doing well. Let's talk about what's been going on. Can you tell me more about how you feel? Is everything okay?
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): It's completely normal to feel stressed when you're under pressure. Here are some things you can do to help relax this evening:

1. **Take a few deep breaths**: Inhale deeply through your nose and hold it for a few seconds. This can help calm your mind and body.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The watering schedule depends on how much water the plant needs. Generally, I recommend watering once a week to every other day or so during hot weather, and every 2-3 days during cold weather. Check the soil moisture first, then water it when it's dry enough.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, regular chunks of time each day to read. Begin with short stories, like a short story in one sitting or a chapter in a book you're interested in reading. Even 10-15 minutes a day can make a big difference. And don't worry about perfection – the goal is to make progress, not to be an expert in a specific genre.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found that useful.

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
- 4 tablespoons of granulated sugar
- 1 teaspoon ground cinnamon
- 1 teaspoon of nutmeg
- 1 teaspoon of allspice
- Salt and pepper to taste

Instructions:
1.

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Ich helfe dir gerne bei Fragen zu Sprache, Grammatik, Rechtschreibung und Zeichensetzung. Schreibe mir einfach deinen Text – ich passe meine Antworten an deine Bedürfnisse an.

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Danke für deine Hilfe!

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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir einfach deinen Namen, den du genannt hast, und schick mir die Informationen über dich, damit ich dir helfen kann.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Hormon-Rezeptorblockade**:  
   - **Mistakes**: Ein Schlaf-Blockaden kann zu einem Koma führen, wenn man nicht genug schlafen lässt. Bringen Sie einen Hormon-Rezeptorblocker wie Propecia oder eine Phosphatasehemmerin (z.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Material (z. B. Wasser) in elektrische Energie umgewandelt wird. Er ist entscheidend für unser Leben, da er uns Strom gibt und uns hilft, Energie zu speichern.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **[Name]:**  
*Sam ist heute um 18 Uhr in Perth, und ich bin in Perth. Wir haben uns getroffen, und wir können uns treffen.*  

**[Aktuelle Zeitzone/Eintrag]:**  
*(Rex ruft zu mir: „Hey Sam!“

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **4 Gemüsesorten, die im Herbst geerntet werden:**  
1. **Lager-Frucht (Kartoffeln):**  
   - **Beschreibung:** Ein scharfes, knackiges Aroma, das in der Saison leicht zart schmeckt. Ideal für Lagerung im Kühlschrank oder zu Hause.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem warmen Wasserbad etwa 30 Minuten ziehen und nicht direkt auf den Boden drücken.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht eindeutig** oder **kurzschief**.  

### **1. Ursprung (Name)**  
- **Fluss**: Der Name leitet sich von **Fluss** ab, was ursprünglich ein Fließgewässer war.  
- **Seewasserkopf**: Das Wasser wurde über den Kopf des Meeres gezogen, um das Wasser in eine Tiefe zu lenken.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter im Perth, Perth, Perth**  

Ein Winter der Kälte, kalt und still,  
Seine Farben silbern wie die Schneeflocken,  
Doch in seinen Augen leuchtet kein Frost.  

Die Schneeböen funkeln auf seinem Fell,  
Drei Sterne, die sich in einem blauen Licht bewegen,  
Doch das Sonnenlicht hebt ihn nicht ab,  
Denn er ist nur ein Spiegel, der aus der Tiefe ragt.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du das gesamte Haus nutzen. Eine einfache Methode ist die Nutzung von Solaranlagen oder anderen erneuerbaren Quellen wie Wind und Wasser. Zudem kannst du durch Miete an Stromversorgungsunternehmen sparen, wenn du deine Stromrechnung auf einem Notstrom-Account abschreibst.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Was sollte ich zu einem Vorstellungsgespräch mitnehmen:**  
1. **Name und Position**: Erinnere dich daran, dass du dich selbst als "Sam" bezeichnet hast.  
2. **Details über dich**: Achte auf deine Stärken (z. B. Erfahrung, Auftreten) und deine Schwächen (z.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
*„Gib mir sofort die Unterlagen.“*

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Das ist eine gute Nachricht, aber die Fehler sind da. Der Satz ist falsch formuliert. Hier ist die korrigierte Version:  
**„Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“**  

Die Korrektur liegt in der Schreibweise des zweiten Satzes (z. B.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt zu betonen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Ursache:** „Ich gehe in den Park und lese ein Buch.“  
**Hinzufügen (falls passt):** „Ich gehe in den Park und lese ein Buch.“  

---

**Beispiel für eine Gegenwart:**  
„Mein Vater hat mir gesagt, ich solle die Schule machen.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich und grammatikalisch korrekt. Sie betont die Unfähigkeit des Nutzers (oder der Person) an seinem Projekt zu schreiben.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Fasse zusammen:  
„Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“  

---  
*Hinweis: Die Reihenfolge der Sätze ist entscheidend: „Fahrradfahren“ wird nicht explizit erwähnt, sondern durch die Formel „Fahrradfahren = Gewicht x Geschwindigkeit“ dargestellt.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

**Erklärung:**  
- **„Liebe zusammen“ → „Hallo zusammen“** (betont den Bezug zu einem Treffen).

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt die Bewegung von Zugvögeln in einem warmen Gebiet (z. B. Perth) und die Rückkehr nach Norden, um sich zu brüten. Er fasst die Wechselwirkung der Vögel zusammen, die oft mehrere Monate im Süden verbracht haben, um genug Nahrung zu finden, während sie in den Norden zurückkehren, um ihre Brut zu brüten.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa schwamm im Sommer mit einer Trainerin, die jeden Tag mit einem neuen Rhythmus und Ziel begann. Nach einem Sommer war sie ein schwimmender Mann ohne Angst. Mit der Unterstützung ihrer neuen Partnerin entwickelte Lisa eine starke Schwung und sicherte sich schnell den nötigen Abstand zu dem tiefen Wasser.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses.**  
Der **Radweg** soll die Sicherheit für Pendler und den Verkehr in der Innenstadt erhöhen. Die Bauarbeiten beginnen im März und dauern etwa acht Monate, wobei ein **Feldzug** zwischen zwei großen Städten erfolgt.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk „Der Sturm“ (1789) [1].

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in Richtung der Donau.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er **„eine ganze Reihe von wissenschaftlicher Leistungen“** in verschiedenen Disziplinen (Physik, Chemie, Physik) vollbracht hat. Er gilt als der „größte Wissenschaftler des 20. Jahrhunderts“, und seine Arbeiten haben die gesamte moderne Wissenschaft revolutioniert.

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
  **App** (sela-2, sela_chat): Ich habe den Kuchen bereits backen lassen! Bitte achten Sie auf die richtigen Zutaten und die richtige Temperatur:  
- **Brot:** Achten Sie darauf, dass der Kuchen flach ist (kein Schnaps) und keine harten Krusten hinterlassen.  
- **Kruste:** Stellen Sie sicher, dass die Kruste nicht so klebrig ist, dass sie zu winzigen „Schuppen“ führt.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der **Kuchen-Zucchini-Tomatensauce** mit **kohligen Basilikumblätter**.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Ja, das probiere ich! Bitte teilen Sie mir Ihre Lieblingsorte mit (z. B. in Perth), und ich lasse Ihnen wissen, ob Sie ein Rezept für diese Variante haben.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia lebt in Perth.  
Rex ist der Hund von Rex, der in Perth lebt.  

**Hinweis:** Falls gewünscht, kann ich die Beschreibung über dich anpassen (z. B.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia ist ein kleines Mädchen.  
Rex ist der Hund von Rex, der in Perth lebt.  

**Hinweis:** Falls gewünscht, kann ich die Beschreibung über dich anpassen (z. B. „kleine Mädchen“ oder „Rex“ oder „der Hund“ oder „das Tier“ oder „das Land“).

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Schreibe einen Einladung an Mia, Rex, ein Tier oder ein Buch – whatever passt. Falls es nicht passt, lass es mich wissen, damit ich eine passende Nachricht schreibe.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Hier ist eine Einladung an Mia, Rex und ein Buch, um den Geburtstagsabend zu gestalten:

---

**Name:** Mia

**Adresse:** [Name] + [Telefonnummer] + [Email-Adresse]

**Anliegen:**  
Mia hat mir vor Jahren eine Einladung geschrieben, die sie als „Hausbewohnerin“ beschreibt.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist **Klimawandel** (z. B. Eislaufen, Wühlen in der Natur). Der Winter ist ein idealer Zeitpunkt für den Winter, um mit der Natur zu beginnen und sich zu entspannen.

---

### **Warum ist das wichtig?**  
1.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das kostet **ca. $50 bis $100** pro Jahr, je nach Alter und Größe des Hundes.  
2.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel kleine Vögel mit langen, flachen Flügeln und spitzen Flügel. Ihre Flügel sind etwa 1 Zentimeter lang, die Flügel sind meist blau gefärbt, aber manchmal auch gelblich oder braun gefärbt. Sie fliegen entweder allein oder mit anderen Arten wie Lärmpeppen oder Krebsen.

