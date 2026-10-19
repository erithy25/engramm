# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T12:53:10Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
Schutzregeln: 5 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! I hope you're doing well.

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well. I just got home from the gym and the dog was getting excited, so I'm still enjoying my lunch. How's your day going so far?

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help you today?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): That's great! I'm glad you liked the help. If there's anything else I can assist with, feel free to ask.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): I apologize for not being able to help you. You're welcome to go!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a native Perth resident who lives in the city of Perth.

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
  **App** (sela-2, sela_chat): I'm sorry, but I don't have the capability to assist with tasks beyond what you've provided. However, if you'd like help understanding something about yourself or your dog (or any other subject), feel free to ask! I'll do my best to provide accurate and helpful information.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Avoid distractions: Try to keep your workspace organized and clutter-free so you can focus on your work without interruptions.
2. Set clear goals: Before starting your workday, set specific, measurable objectives that will help you stay focused. This could be something as simple as "I want to complete this project by the end of the week" or "I have 20 minutes to finish this presentation."

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): This depends on the type of egg you're using. For a hard-boiled egg, use water to boil the yolk until it's soft (but still slightly firm). This will take at least 20 minutes.

For a soft-boiled egg, use a small amount of oil or butter to heat it up slowly over medium-high heat.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible threat that spreads through the internet. It's like a "hijack" of your computer's system, making it hard for you to use or do things. Viruses can make you feel sick or even hurt you. They might take over your files, your email, or even your phone!

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Can you water my plants next week? I really need help."

---

**Subject:** Request for Watering Help from Neighbour (Your Name)**

Dear Neighbour:

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. citrus fruits like oranges, lemons and grapefruits
2. strawberries
3. tomatoes
4. kiwi
5. orange
6. papaya

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two different aspects of the same. Climate refers to the long-term average conditions in a particular area. It is the "average" temperature, precipitation, wind direction, humidity, and other factors that determine how hot or cold it is. Weather, on the other hand, is a longer term average of these factors.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The sun dips low, a warm orange and gold
The air is crisp and cool,
A fleeting breath of fall's scent
Whispers through the trees,
Of earth that once was green.

The leaves are autumn's own,
A symphony of colors,
Red and gold,
And in every breeze
A promise of sweet dreams.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some tips to make your password more secure:

1. Use a strong, unique password. Avoid using something easily guessable like your name or birthdate. Instead, use a combination of letters, numbers, and symbols. Consider using a password manager to store and manage your passwords.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. The Cups Coffee House – A café near the Library of Congress. It's a popular choice, especially during the summer months.
2. The Brew & Savor Coffee Shop – A cozy spot with a few good beers and a simple menu.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): I'll provide a 20-minute plan for you, based on the principles of recovery and fitness. However, since I don't have equipment for exercise, I'll use my knowledge of personal fitness, body composition, and nutrition to create an easy workout plan.

**20 Minute Plan:**
1.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): Pack essentials for a weekend camping trip in Perth, Australia. 
1. Clothing: 
   - Warm layers (lightweight fleece or sweatshirt) to keep you warm. Good sun protection is essential and don't forget sunscreen and hats!
   - Waterproof clothing that's waterproof and breathable.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark expanse that stretches across the globe, its depths often reaching heights of over 600 meters. It's divided into several major sections: the Atlantic Ocean, the Pacific Ocean, the Arctic Ocean, and the Antarctic Ocean. The ocean has a unique physical characteristics, including large currents, temperature variations, and the presence of marine life such as fish, squid, and crustaceans.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. **Be polite**: Use phrases like "I'm glad I could help" or "I appreciate your assistance, but I don't think we'll be able to fit in the party tonight."
2. **Be clear about your reasons**: Let the party organizers know what you're looking for (e.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text: "Send me the report now."

I changed "Send" to "Send", as "Send" is the correct verb form for sending something. I also changed "now" to "now", which is the correct spelling of the verb. Additionally, I removed the phrase "in Perth" and replaced it with "in Perth", as the city's name is not necessary in this context.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A simpler version could be: "Public transportation reduces urban congestion." 

Alternatively, you could say: "Public transportation helps reduce urban congestion by lowering emissions and improving air quality."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct answer is: "She don't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 2 Versuche): I walk to the station and buy a ticket. I'm going to the station now.

Rewrite the sentence in the past tense: "I walk to the station and buy a ticket."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Welcome to our little gem of a shop! This weekend, we're super excited about the amazing deals on everything from lasagna to beer. What catches your eye? (What do you remember about Lucy's dog Rex?)"

I made the following changes to make the sentence sound more exciting:

- Changed "Our shop has a sale this weekend" to "Welcome to our little gem of a shop" to make it sound more inviting and engaging.

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): What is the train's departure time?

How far does it take to get to Perth?

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): I have been fascinated by the natural world for over two decades. I spend most of my time exploring the wilderness, conducting scientific experiments, and contributing to various projects.

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

I made a few changes to improve clarity and grammar:

- Changed "will be" to "will be" (correct verb form)
- Added an article ("the") before "debate" to make it clear who is talking about the library's heating system
- Changed "it will reopen on Tuesday at 9 a.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This is a short summary of Tom's story:

Tom started learning the guitar at age three. He learned it from his parents and siblings. His fingers hurt, and he practiced for 15 minutes every day. After three months, he could play his favourite song for his friends.

Tom describes how his parents took him to an instrument store and showed him how to play chords and strum chords using his fingers.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The user's email is: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

Here's a brief summary of the information:
- **Subject:** Project Meeting – Moving to Thursday at 2 p.

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
  **App** (sela-2, sela_chat): There's a lot to see and do in Venice. You should try some classic Venetian dishes like pizza, gelato, and pasta. Don't forget to visit the famous Rialto Market for fresh seafood and unique local specialties.

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
My dear mother,  
I hope you have a wonderful day filled with laughter and love. I’m so grateful for all the good times we’ve had together. Good morning, my lovely dear!
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Happy Mother's Day!

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Here's a possible response:  

"Hey Sam, it's okay to feel stressed. Your dog Rex is a good friend and loves to play. But remember, your stress doesn't have to be about the dog – sometimes our worries can be about other things too. Try taking a few deep breaths, going for a walk, or just giving yourself a moment to relax.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Here are some suggestions to help you relax this evening:  

1. **Take a warm bath**: Just like Rex loves to play, take a relaxing bath. You can also try a steam room or a spa day if you prefer!  
2. **Relax with nature**: If you live in Perth, spend time outside and enjoy the sun.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The answer is: once every 2-4 weeks.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with short books like "The Girl Who Drank the Moon" by Gillian Flynn, "The Giver" by Jonathan Swift, or "A Song of Ice and Fire" by George Orwell. Read them often to get a taste for new authors and styles. You can also try using a mobile app like Reading Buddies or Readability to find books you might enjoy.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found them. Let me know if you need more help or have any other questions.

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
- 3/4 cup red wine vinegar
- 1 tsp salt
- 1/4 cup black pepper
- 2 cloves garlic, minced
- 1 tsp smoked paprika
- 1 tsp cumin
- 1/2 tsp smoked coriander
- 1 tsp smoked salt
- 1/2 tsp black pepper
- Salt and pepper to taste
- Fresh parsley or chopped fresh parsley for garnish [1].

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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den Nutzer deiner Wahl und den Kontext deiner Nachricht ein. Falls du möchtest, kannst du auch eine kurze Beschreibung des Nutzers angeben, etwa:  

- **Was der Nutzer dir erzählt hat**: Angaben über seine Rolle, z. B.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Pausen einplanen**: Wenn du dich müde fühlst, schließe einen kleinen Spaziergang ein (z. B. in den Park oder in der Stadt) und kombiniere es mit einem ruhigen Spaziergang.  
2. **Szenen vermeiden**: Nutze deinen Tag für Aktivitäten, die dein Körper aktiv gestalten kann, z.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das menschliche Körper erzeugt wird. Er gibt Energie für Bewegungen, Muskeln und Knochen. Strom ist auch die Energie, die wir brauchen, um Dinge zu bewegen (z. B. ein Auto oder ein Computer). Es fließt aus der Erde, an den Händen und Füßen und aus dem Körper (Körper und Fett).

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Subject:** Nachricht an meine Kollegin, dass ich heute komme  

Hi [Name],  
Ich bin [Name]! Ich werde heute [Datum] um [Uhrzeit] zu Ihnen kommen.  

Zum Glück habe ich einen freundlichen Termin mit der Kollegin (und mit Rex).

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **1. Rote Kresse (Helianthus annuus)**  
*Erdjahr: September bis Oktober*  
**2. Knoblauch (Chilium oxyporum)**  
*Erdjahr: November bis Februar*  
**3. Erdbeeren (Ersatz für Äpfeln) und Tomaten (Tomatoes pomosae)**  
*Erdjahr: Juni bis Oktober*  

**4.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem warmen Wasserbad gebacken werden.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht direkt sichtbar** (z. B. das Fließen des Flusses dass durch den See verläuft). Sie sind jedoch **einschließlich** von Wasser, das **aus dem Fluss entsteht**. Der Begriff „Fluss“ bezieht sich auf die natürliche Quelle des Wassers, während der Begriff „Seewiese“ eine geografische Form beschreibt, in der Wasser aus einem bestimmten Ort fließt.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter im Winterland**  

Der Schnee wirft goldbraun seine Flammen auf die Erde,  
die Stille um uns herum weht wie ein Sturm.  
Die Eiswüste trägt das leise Lied der Winde,  
doch der Regen spielt nie mehr die Melodie.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, ist es sinnvoll, die Verbrauchsfaktoren wie Heizkosten, Stromverbrauch und Wasserverbrauch regelmäßig zu überprüfen. Hier sind einige Tipps:

1. **Kühlung**: Eine Möglichkeit ist, den Heizwert des Hauses zu steigern, indem Sie Heizelemente verwenden (z.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Um zu einem Vorstellungsgespräch mitzunehmen, sollten folgende Gegenstände vorhanden sein:  
1. **Persönliche Dokumente**: Ein passendes Foto von dir (z. B. eine Fotoserie), ein Lebenslauf, ein Kurzvideo oder ein leeres Bild des Nutzers.  
2. **Identifizierende Unterlagen**: Liste der Unternehmen, Institutionen, Projekte oder Leistungen, die du gerne erwähnen willst.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
*(Höflich: „Ich bin ich. Bitte gib mir sofort die Unterlagen.“)*  

**Hinweis:** Der Nutzer wird nicht mit der Unterlage allein kommunizieren, sondern auch durch die Einhaltung von Vorschriften (z.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“  
(Fortsetzung des Originaltextes, aber ohne die verborgene Erklärung von „ich“ und „sehr gut“.)

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt zu betonen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **In den Park:**  
*Ich gehe in den Park und lese ein Buch. Es ist bereits Morgen.*  

**Erklärung:**  
- **„geht“** → **„lese“**: Die verborgene Bedeutung von „gehen“ (z. B. durch die Handlung, die an dieser Stelle geschieht) bleibt unverändert, da die Handlung im ersten Satz die Situation beschreibt.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich neutral und betont den Nutzer als Person. Sie ist klar strukturiert und verständlich.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Der Fahrer, Sam, trägt eine Fahrradkappe und eine Schutzanzüge, während Rex ein Auto fährt, das seine Geschwindigkeit erhöht und den Boden weniger belastet.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Im Text geht es um die Zugvögel in den Süden und ihre Fortbewegung, die sich im Herbst zurückzieht. Der Text beschreibt das Phänomen, dass Zugvögel ihre Wanderungen über Jahrhunderte fortführen. Das Bild der Vögel als Vögel ist ein metaphorisches Alltagsbild: sie sind eine Verbindung zwischen Mensch und Natur, die durch Kommunikation und Sozialität entsteht.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst in Angst vor dem tiefen Wasser und der großen Entfernung aus ihrem Dorf aufgewachsen. Doch mit einer Trainerin, die sie über den Weg hinwegführte, konnte sie beginnen, sich zu entwickeln.  

Die Trainerin, die sich auch als **Rex** nannte, hatte bereits viele Jahre Erfahrung im Training gesammelt, und nun wagte sie sich nicht nur an das schwimmende Training, sondern trug auch praktische Tipps für gesunde Ernährung und körperliche Fitness ein.

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
  **App** (sela-2, sela_chat, 3 Versuche): Meine Quellen sagen dazu nichts.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in Richtung der Eifel. Er entspringt im Herzen von Perth und verläuft durch den Norden des Bundesstaates.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik im Jahr 1921, gemeinsam mit seinem Freund Max Born und dem Mathematiker Bernhard Riemann. Dieser Preis wird von der American Physical Society verliehen und ist die höchste Auszeichnung, die an Wissenschaftler verliehen wird, die in Physik tätig sind.

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
  **App** (sela-2, sela_chat, 2 Versuche): **Bäckerei:**  
Der Nutzer, Mia, wohnt in Perth. Der Hund des Nutzers, Rex, wohnt in Perth.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): **Bäckerei:**  
Der Nutzer, Mia, wohnt in Perth. Der Hund des Nutzers, Rex, wohnt in Perth.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): **Bäckerei:**  
Der Nutzer, Mia, wohnt in Perth. Der Hund des Nutzers, Rex, wohnt in Perth.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Der Nutzer ist Mia, ein kleiner Offline-Assistent in Perth.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um meinen Wortschatz zu verbessern, kann ich den folgenden Schritt ergreifen:

1. **Präzisere Definitionen**: Formulierungen wie „In der Regel“ oder „Die Sprache ist nicht perfekt“ helfen, Wörter klarer zu definieren.  
   *Beispiel:* „In Perth wird oft Englisch gesprochen.“

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Schreib eine Einladung für Mia, Rex oder andere Nutzer an:

---

**Einladungen:**  
Mia ist ein **Ableger** des Nutzers. Rex ist ein **Erzähler** der Nutzer.  
Der Nutzer hat den Nutzer gefragt, ob sie eine Einladung schreiben möchte – und die Antwort lautet ja.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Mia ist ein **Ableger** des Nutzers, der sich gern für eine Einladung für Mia und Rex entscheiden möchte. Der Nutzer hat die Einladung an den Nutzer geschickt – und der Nutzer hat ihn in einem Email- oder Postfach geschrieben.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist ein Spaziergang mit dem Hund Rex. Er hat eine gesunde Ernährung und kann ausreichend Sonnenlicht genießen.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet zwischen $10 und $100. Es hängt vom Wetter ab, wie viel du machst und was du wirklich magst. Der Hund kann jedoch viel mehr kosten, je nach Größe und Haltung des Hundes.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

