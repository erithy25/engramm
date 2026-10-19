# Sela-2 Chat: 100 feste Prompts (M5)

Gewichte `sela2-s21lr10.npz` (SHA-256 `19e8ee2073e7e43a…`), 2026-10-18T17:29:47Z.

| Kriterium | Wert | Grenze | erfüllt |
|---|---|---|---|
| loop_rate | 0.0% | < 5% | ja |
| limit_rate | 11.0% | < 5% | nein |
| role_leak_rate | 0.0% | < 1% | ja |
| median_tokens | 37 | ≤ 120 | ja |

Quellen-Fragen: 12/13 beantwortbare bestehen die Prüfung, 0 fälschlich abgelehnt; 3/4 unbeantwortbare korrekt abgelehnt.

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **Sela-2** (9 Token, stop): Hello! How can I help you today?

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **Sela-2** (20 Token, stop): I'm doing great!  I'm just getting ready for a workout, so that's good.

### en03 (greeting)
- **Nutzer:** Good morning!
  **Sela-2** (8 Token, stop): Good morning! How can I help?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **Sela-2** (7 Token, stop): Hey there, what's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **Sela-2** (4 Token, stop): You're welcome!

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **Sela-2** (3 Token, stop): Goodbye!

### en07 (identity)
- **Nutzer:** Who are you?
  **Sela-2** (36 Token, stop): My name is Sela. I'm a compact language model trained from scratch by the ENGRAMM project. I run locally on your device, and our conversation stays here.

### en08 (identity)
- **Nutzer:** What is your name?
  **Sela-2** (34 Token, stop): I'm Sela, a small language model. I was trained from scratch in the ENGRAMM project on public text, and I run offline on your computer.

### en09 (identity)
- **Nutzer:** Who made you?
  **Sela-2** (35 Token, stop): The AI was trained from scratch in the ENGRAMM project, on public text and conversations. I'm Sela, a small language model that runs on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **Sela-2** (13 Token, stop): I'm an artificial intelligence and I can only speak in binary.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **Sela-2** (142 Token, stop): I can assist with a wide range of tasks, including:

- Writing and editing written content, such as articles, essays, blog posts, and more.
- Providing guidance on grammar, style, clarity, and structure.
- Offering suggestions for improving sentence structure and flow.
- Helping with data analysis and interpretation.
- Assisting with writing and editing for various formats, such as academic papers, business reports, and personal essays.
- Suggesting alternative phrasings or sentence structures to enhance clarity and impact.

What kind of help would you like me to offer? Do you have a specific project in mind or need assistance with a particular aspect of writing or editing?

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **Sela-2** (15 Token, stop): I do not have feelings, but I am curious about how you feel.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **Sela-2** (127 Token, stop): 1. Create a routine: Establish a consistent daily schedule that includes regular breaks, time for self-care and relaxation, and a few hours of focused work each day.
2. Use technology wisely: If you have access to a computer or tablet, use it to your advantage by taking notes, creating visual aids, or playing educational games to keep yourself engaged.
3. Schedule breaks and time off: Don't be too rigid in your work schedule. Take short breaks throughout the day, even if it's just a 30-minute walk or a short meal break, to recharge and come back to your work with fresh eyes.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **Sela-2** (15 Token, stop): You can boil an egg for 3-5 minutes to make it soft.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **Sela-2** (112 Token, stop): A computer virus is a type of computer program that can make itself vulnerable to attack by infecting your computer's system. It is a harmful program that can cause damage or harm to your computer, such as installing software, corrupting files, or deleting important files.

Viruses are often used by hackers and cybercriminals to gain unauthorized access to your computer system, steal sensitive data, or commit other malicious activities. They can be difficult to detect because they may not display any warning messages or exhibit unusual behavior when you try to run them.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **Sela-2** (19 Token, stop): Hello! Here's a friendly message for you to send your neighbor. You can reply here:

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **Sela-2** (16 Token, stop): - Strawberry
- Sweet potato
- Cucumber
- Pumpkin

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **Sela-2** (52 Token, stop): The weather is the actual state of a location, while climate is how that location is perceived by people. Weather can be hot or cold and dry or wet. It can also be sunny or rainy. The climate is what people expect to see in their area.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **Sela-2** (84 Token, stop): In twilight's hush, where the last whispers of summer's sigh
Come to me, with amber's soft glow
A palette of gold, where every leaf
Is a gem in a thousand suns' light.

The world is bathed in soft and gold
Through autumn's blazing fire,
And I am the tree that marks the end
Of all things, and yet I remain.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **Sela-2** (107 Token, stop): Here are some tips:
1. Use a mix of letters, numbers and symbols to make your password.
2. Avoid using common words like "password" or "bank account".
3. Avoid using alphabetic characters in passwords.
4. Consider using a unique password for each user and have them change it regularly.
5. Consider using a multi-factor authentication solution which can be both physical and digital.
6. Don't use a common email address, phone number, or any other generic password.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **Sela-2** (36 Token, stop): There are several options for a small coffee shop near a library: Shoe & Brew, Beats & Brews, Shredded Chocolate, and Booths & Brews.

### en22 (instruction) – limit
- **Nutzer:** Explain why we have day and night.
  **Sela-2** (160 Token, limit): The term "day" and "night" are based on the ancient Greek words for morning, afternoon, and evening. In ancient Greece, the Greeks named the days of the week as follows:
- Monday was called "diapera," meaning early or earliest day
- Tuesday was called "kythira," meaning first or beginning day
- Wednesday was called "ethys," meaning morning or beginning day
- Thursday was called "mythara," meaning later or after day
- Friday was called "protia," meaning early or second day
- Saturday was called "phistia," meaning later or earlier day
- Sunday was called "tykos," meaning early or late day
- Monday was called "phoneta," meaning morning or early day
- Tuesday …

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **Sela-2** (125 Token, stop): Here are a few simple ideas for 20-minute workouts:
1. Do cardio: Walk around the room or a park for about 5 minutes, then go back to the room and do your favorite exercise like jumping jacks or squats.
2. Try push-ups: Grab some water bottles and squeeze them together, then place one end in each hand of your body. Do 10 sets of 2-3 reps per side.
3. Do push-ups with your legs spread apart: Lie on your back, then bend your knees slightly, then jump onto the floor. Then repeat on the other side.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **Sela-2** (32 Token, stop): You should pack a waterproof tent, sleeping bag and some sleeping pad. If you plan to camp in the woods make sure you have plenty of food and water.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **Sela-2** (26 Token, stop): The ocean is a vast, mysterious, and unforgiving body of water that covers over one-third of the Earth's surface.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **Sela-2** (72 Token, stop): Here is a sample response:

"I've been looking forward to trying out this new restaurant, but I'm not sure if it's the right fit for me. My family and friends have mentioned that there are some special requests in the area, so I'd like to avoid that. I'm not sure what I'm looking for in a party."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **Sela-2** (20 Token, stop): "I'm sorry, I was unable to attend the conference. Please send me the report now."

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **Sela-2** (35 Token, stop): A simpler version could be: "Public transportation reduces urban congestion." 

This rephrased sentence conveys the same idea as the original, but in a more direct and concise manner.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **Sela-2** (12 Token, stop): She doesn't like going to school on mondays.

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **Sela-2** (11 Token, stop): "I walk to the station, buy a ticket."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **Sela-2** (48 Token, stop): Welcome to our shop! We've got a sale this weekend, and I'm super excited to see what you've got on offer. Come in, grab a drink, and let's get started! What can I get for you today?

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **Sela-2** (9 Token, stop): The train leaves at eight o'clock.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **Sela-2** (34 Token, stop): Here's a rewritten version of the sentence in a formal tone: "I apologize for not being able to make it tomorrow, but I will try and catch up soon."

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **Sela-2** (47 Token, stop): A more concise version of the sentence could be: "Due to heavy rain outside, we decided to stay inside the house." 

This revised sentence still conveys the same information as the original but in a more direct and efficient way.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **Sela-2** (52 Token, stop): Bees are crucial pollinators, playing a vital role in the reproduction of numerous crops. When bees collect nectar from flowers, they transfer pollen to other plants, ensuring the production of fruits and seeds. This helps plants produce new life, including the ones we eat.

### en36 (summarize) – limit
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **Sela-2** (160 Token, limit): The text effectively conveys the purpose of the library's closure on Monday and provides clear instructions for returning books. However, it could be improved for better clarity and concision. Here's a revised version:

"On Monday, the library will be closed for repairs to its heating system.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **Sela-2** (74 Token, stop): The main point of this paragraph is that drinking enough water is essential for maintaining overall health and well-being. The text highlights the importance of staying hydrated, as it helps regulate body temperature, maintain joints, support digestion, and prevent dehydration. This message emphasizes the need to balance water intake with other health considerations, such as exercise and hydration, to ensure a healthy lifestyle.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **Sela-2** (48 Token, stop): Here's a short summary:

Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **Sela-2** (38 Token, stop): Electric cars run on batteries instead of petrol, producing no exhaust gases and improving air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **Sela-2** (35 Token, stop): This email is a collaborative and professional effort to convey the project's progress. The message is clear, concise, and actionable, aiming to provide a positive outcome for the team.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **Sela-2** (44 Token, stop): Here's a condensed version: "Recycling turns used materials into new products, such as paper, glass, and plastic, reducing waste and recycling inefficiencies. It saves raw materials and energy, minimizing landfill waste."

### en42 (summarize)
- **Nutzer:** In one sentence, what is this about? "The town council approved a new park on the site of the old car park. The park will have trees, a playground and a small pond. Construction starts in spring and should take about one year."
  **Sela-2** (40 Token, stop): The town council approved a new park on the site of the old car park. The park will have trees, a playground and a small pond. Construction starts in spring and should take about one year.

### en43 (grounded) – geprüft
- **Nutzer:** How long is the Danube?
  **Sela-2** (16 Token, stop): The Danube is Europe's second-longest river after the Volga [1].

### en44 (grounded) – limit, Prüfung nicht bestanden
- **Nutzer:** What is Ada Lovelace known for?
  **Sela-2** (90 Token, limit): Ada Lovelace was an English mathematician. She wrote what is often regarded as the first computer program, an algorithm for Charles Babbage's proposed Analytical Engine.

Ada Lovelace was an English mathematician. She wrote what is often regarded as the first computer program, an algorithm for Charles Babbage's proposed Analytical Engine.

Ada Lovelace was an English mathematician.

### en45 (grounded) – geprüft
- **Nutzer:** What gas do plants release during photosynthesis?
  **Sela-2** (5 Token, stop): Carbon dioxide [1].

### en46 (grounded) – geprüft
- **Nutzer:** When were the best-known sections of the Great Wall built?
  **Sela-2** (7 Token, stop): During the Ming dynasty [1].

### en47 (grounded) – Prüfung nicht bestanden
- **Nutzer:** How many moons does Saturn have?
  **Sela-2** (24 Token, stop): Saturn has five moons: Titan, Io, Europa, Ganymede, and Callisto [1].

### en48 (grounded) – geprüft
- **Nutzer:** Who created Python?
  **Sela-2** (8 Token, stop): Guido van Rossum [1].

### en49 (grounded) – geprüft
- **Nutzer:** At what temperature does water boil at standard pressure?
  **Sela-2** (6 Token, stop): 100 °C [1].

### en50 (grounded) – abgelehnt
- **Nutzer:** Who is the mayor of Paris?
  **Sela-2** (6 Token, stop): My sources don't say.

### en51 (grounded) – geprüft
- **Nutzer:** Where is the Mona Lisa displayed?
  **Sela-2** (7 Token, stop): The Louvre in Paris [1].

### en52 (grounded) – geprüft
- **Nutzer:** How many queens does a honey bee colony usually have?
  **Sela-2** (21 Token, stop): One queen, thousands of female worker bees and, in summer, a few hundred male drones [1].

### en53 (multi_turn)
- **Nutzer:** Hi, I'm planning a trip to Italy.
  **Sela-2** (65 Token, stop): Italy is a great destination.  You can start with the basics: where you're going, how long you want to stay and the time of year you plan to visit.  Italy has many different regions that you can explore, such as the north, south, east, west and central.  What are your preferences?
- **Nutzer:** Which city should I visit first?
  **Sela-2** (33 Token, stop): The city I recommend is Rome.  Rome is a great place to start your trip, and the food, history and culture of the city will be very interesting.
- **Nutzer:** Thanks! What food should I try there?
  **Sela-2** (64 Token, stop): Italy is known for its delicious food, and you'll find a lot of great dishes to choose from.  You can try Italian pasta, risotto, gelato, pizza, pasta with tomato sauce, caprese, seafood, lasagna, cacio e pepe, pizza, risotto, etc.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **Sela-2** (46 Token, stop): I'm Sam, a dedicated software engineer with over 15 years of experience in the industry. I've worked on various projects, from building complex systems to developing cutting-edge applications. What project or task would you like to discuss?
- **Nutzer:** What is my name?
  **Sela-2** (40 Token, stop): My name is Sam. I'm a software engineer with over 15 years of experience in the industry, having worked on a wide range of projects, from building complex systems to developing cutting-edge applications.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **Sela-2** (91 Token, stop): I can help you write a birthday card for your mother. Here's a template:

- Start with the birthdate and date of your mother's birthday.
- Add her favorite memories, hobbies, or sports.
- Write in her favorite colors and make sure it's professional looking.
- Add a message of gratitude, love, or appreciation.
- Use a cardstock or cardstock stock for your mother's name and signature.
- **Nutzer:** Make it a bit shorter, please.
  **Sela-2** (81 Token, stop): Sure, here's a concise version:

- Start with the birthdate and date of your mother's birthday.
- Add her favorite memories, hobbies, or sports.
- Write in her favorite colors and make sure it's professional looking.
- Add a message of gratitude, love, or appreciation.
- Use cardstock or cardstock stock for your mother's name and signature.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **Sela-2** (76 Token, stop): I'm sorry to hear that you're feeling stressed. It's normal to feel overwhelmed, but it's essential to take care of yourself and prioritize self-care. Start by acknowledging your feelings and taking a step back to assess what's causing them. Is it the work environment, social pressures, or something else? Identifying the root cause will help you address the issue more effectively.
- **Nutzer:** What can I do to relax this evening?
  **Sela-2** (128 Token, stop): To relax this evening, try to create a peaceful atmosphere that fosters relaxation. Consider taking a warm bath or shower in a natural setting, like a park or beach, to help calm your mind and reduce stress. You can also listen to calming music or nature sounds to signal to your brain that it's time to unwind.

Additionally, take a short walk or do some light stretching exercises to loosen up your muscles. Alternatively, you can try some yoga or meditation to get your mind off work or anxiety. Even small moments of self-care, such as taking a few deep breaths, can make a big difference in how you feel.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **Sela-2** (58 Token, stop): There are many good houseplants to start with.  Some popular ones include:

- Pepper Plants
- Leafcutter Plants
- Snake Plant
- Snake Moth
- Philodendron
- Lobster Plants
- Lobster Pea
- Pothos
- **Nutzer:** How often should I water it?
  **Sela-2** (81 Token, stop): Watering is important for most houseplants, especially those that are succulents.  Most people do not water their plants enough and this can lead to root rot, fungal diseases or even death.

Most houseplants prefer at least 2 hours of direct sunlight per day.  If you are worried about the watering schedule, use a watering can to ensure that the plant receives all the necessary water.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **Sela-2** (38 Token, stop): Cats are the most popular pets in the world and were originally domesticated by humans thousands of years ago. In fact, it is estimated that about 50% of all cats are domestic cats.
- **Nutzer:** And one about dogs?
  **Sela-2** (25 Token, stop): Dogs are the most popular pets in the world. It is estimated that about 70% of all dogs are domestic dogs.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **Sela-2** (55 Token, stop): To begin reading, start with a good book. Look for one that has interesting characters, a compelling plot, and a strong setting that you can relate to. Try to identify what drew you to the story in the first place and then use that as inspiration to continue reading.
- **Nutzer:** Any tips for finding time to read?
  **Sela-2** (133 Token, stop): To find time to read, try to create a reading routine that works for you. Set aside dedicated time each day or week to read, even if it's just 20-30 minutes. Start with short texts and gradually work your way up to longer ones, as this will help you build momentum and make the experience more enjoyable.

It's also essential to find a reading buddy or join a book club where you can discuss and enjoy your favorite books together. This can be a great way to discover new authors, get feedback on your work, and stay motivated. Additionally, consider taking breaks from your daily routine to read during your lunch break or after dinner.
- **Nutzer:** Great, thank you!
  **Sela-2** (18 Token, stop): You're welcome! If you have any other questions about reading, feel free to ask.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **Sela-2** (44 Token, stop): A recipe is a set of instructions for how to prepare a meal. It contains steps that are followed to prepare the food and its preparation. For example, a cook needs to follow a recipe to prepare a healthy meal.
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **Sela-2** (146 Token, stop): Here's a simple recipe for a sandwich:

Ingredients:
1 slice of bread, 2 slices of bread, 2 slices of tomato, 1 tablespoon olive oil, salt, pepper, and 1 onion

Instructions:

1. Preheat oven to 400 degrees F.
2. Roll out the bread into a circle or a square.
3. Place the tomato in the center of the circle or square.
4. Spread the olive oil over the bread and tomato.
5. Place the onions on top of the bread and tomato.
6. Top with the remaining ingredients.
7. Bake for 20-25 minutes or until the bread is golden brown and the tomatoes are soft.

### de01 (greeting)
- **Nutzer:** Hallo!
  **Sela-2** (8 Token, stop): Hallo! Wie kann ich Ihnen helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **Sela-2** (9 Token, stop): Guten Morgen! Wie kann ich helfen?

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **Sela-2** (4 Token, stop): Gern geschehen!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **Sela-2** (7 Token, stop): Tschüss, bis bald!

### de05 (identity)
- **Nutzer:** Wer bist du?
  **Sela-2** (35 Token, stop): Ich bin Sela, ein kleines Sprachmodell. Ich wurde im ENGRAMM-Projekt von Grund auf mit öffentlichen Texten trainiert und laufe offline auf deinem Computer.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **Sela-2** (35 Token, stop): Ich bin Sela, ein kleines Sprachmodell. Ich wurde im ENGRAMM-Projekt von Grund auf mit öffentlichen Texten trainiert und laufe offline auf deinem Computer.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **Sela-2** (32 Token, stop): Ich bin eine KI: Sela, ein kleines Sprachmodell aus dem ENGRAMM-Projekt. Ein Mensch bin ich nicht, aber ich helfe gern.

### de08 (identity) – limit
- **Nutzer:** Wobei kannst du mir helfen?
  **Sela-2** (160 Token, limit): Natürlich! Ich helfe gerne. Um dir gezielt helfen zu können, brauche ich ein wenig mehr Informationen oder möchtest du etwas konkretes wissen? Hier sind ein paar Möglichkeiten:

1. **Bereiche/Vorgänge**:  
   - Berechne die Anzahl der Dateien im Dateisystem (z. B. z. B. `fs` für Linux), die Sie speichern möchten.  
   - Ersetze "Dateien" mit "Dateien in diesem Format".  
   - Konvertiere eine Datei in einen anderen Format (z. B. `xsdg-Dateien` für Windows).  

2.

### de09 (instruction) – limit
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **Sela-2** (160 Token, limit): 1. **Körperliche Aktivität einplanen**: Bewegung kann helfen, die Schlafqualität zu steigern und den Körper mit Endorphinen zu beflügeln.
2. **Schlafmoden auswählen**: Wähle eine der folgenden Schlafmoden aus:
   - **Schlafmodus 1 (K-1)**: Schlafsofa
   - **Schlafmodus 2 (B-1)**: Bett
   - **Schlafmodus 3 (C)**: Couch
   - **Schlafmodus 4 (D)**: Dusche
   - **Schlafmodus 5 (E)**: E-Schlaf (mit Badelaken)
3.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **Sela-2** (63 Token, stop): Strom ist wie ein langer, langer Atem – er zieht durch alle Körperzellen und fließt in den Körper hin. Er ist wie Wasser in einem See, das sich langsam bewegt, und kann die Körperteile nicht direkt erreichen, aber wir können ihn spüren. Strom fließt durch den Körper und fließt durch die Organe.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **Sela-2** (46 Token, stop): Hey, ich komme morgen früh um 6:00 Uhr zu einem Meeting. Das ist super cool, da wir schon heute zusammen arbeiten können! Danke für die Zeit, ich freue mich darauf, mit Ihnen zu sprechen.

### de12 (instruction) – limit
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **Sela-2** (160 Token, limit): Hier sind vier Gemüsesorten, die im Herbst geerntet werden können:

1. **Maiskolben**  
   - Hauptanbaugebiet: Nord- und Südosteuropa (z. B. Italien, Deutschland, Österreich).  
   - Maiskolben haben eine hohe Nährstoffgehaltssteigerung und werden häufig als "Kornbrot" in Backwaren und Suppen verwendet.  

2. **Aprikosen**  
   - Hauptanbaugebiet: Südostasien (z. B. Indien, Nepal).  
   - Aprikosen haben eine gute Nährstofftoleranz und werden häufig als "Rohkartoffel" in Suppen und Desserts verwendet.  

3.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **Sela-2** (108 Token, stop): Nudeln sollten von innen heraus richtig und gut geschliffen sein. Hier sind einige Tipps, um sie richtig zu verarbeiten:
- Frage nach dem Vorgehen, bevor du Nudeln aufgibst.
- Frage nach dem Zeitpunkt an dem der Teig am besten zu verarbeiten ist.
- Frage nach den Zutaten.
- Fragen nach dem Teigtyp (Knet, auskühlen, kneten, kalt stellen).
- Frage nach dem Geschmack.
- Frage nach dem Geschmack von den Nudeln selbst.

### de14 (instruction) – limit
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **Sela-2** (160 Token, limit): Ein Fluss und ein See sind zwei verschiedene Arten von Gewässern. Ein Fluss ist eine natürliche Fließrichtung, die sich aus einer größeren Anzahl von Zuflüssen zusammensetzt. Er ist meist flach und klar, umgestaltbar und bereitet oft Lebensraum für viele Tiere und Pflanzen vor. Beispiele: der Amazonas, der Orinoko oder der Fluss der Aare.

Ein See hingegen ist eine künstliche Verankerung von Wasser, die durch Zuflüsse entstanden ist. Seesysteme sind fast immer klar und haben einen schmalen Grund, um Nährstoffe zu transportieren. Sie sind nicht flach und können auch sehr tief sein. Beispiele: der See im Harz, der Ozean im Golf von Mexiko oder der See in den Meerengen der Antarktis.

### de15 (instruction) – limit
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **Sela-2** (160 Token, limit): **Wintergedicht**  

Winter, der Winter, ein Flüstern des Eisens,  
ein Lied, das in den Schneezügen leise singt.  
Die Schneeflocken tanzen wie ein Lied, das kein Auge erhellt,  
und die Luft ist kalt, doch warm, kalt und voller Flamme.  

Die Bäume tragen ihre Äste in den Schnee,  
mit goldenen Früchten, die das Licht aufblühen lassen.  
Die Vögel zwitschern ihr Lied, das im Wind erklingt,  
und die Welt wird zum stillen Herzen.  

Im Windschatten fressen die Insekten,  
doch in der Dunkelheit hält sich der Winter.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **Sela-2** (37 Token, stop): Es gibt viele Möglichkeiten, um im Haushalt Energie zu sparen. Du kannst zum Beispiel deine Stromrechnung an eine Wand hängen und wenn du nicht im Haushalt wohnt, kann man Energie sparen.

### de17 (instruction) – limit
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **Sela-2** (160 Token, limit): Um zu einem Vorstellungsgespräch mitzuteilen, sollten Sie konkrete Beispiele nennen, die Sie aus Ihren Erfahrungen im Unternehmen oder in Ihrer beruflichen Entwicklung ableiten. Hier sind einige Vorschläge:

- **Relevanz für das Unternehmen**: Stellen Sie sicher, dass Sie sich mit dem Unternehmenskontext und den Teamvorstellungen auskennen.
- **Praktische Erfahrung**: Stellen Sie sicher, dass Sie Erfahrungen in ähnlichen Umgebungen sammeln können (z. B. bei der Umsetzung von Projekten).
- **Strategische Planung**: Geben Sie an, wie Sie Ihre Fähigkeiten im Bereich [industrielles/technisches/wirtschaftsfeld] einsetzen möchten.
- **Nachhaltige Unternehmenskultur**: Stellen Sie sicher, dass Sie zeigen, dass Sie sich für eine positive und nachhaltige Zukunft einsetzen.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **Sela-2** (44 Token, stop): **„Gib mir sofort die Unterlagen.“**  

*(Die Formulierung betont formell und fokussiert auf das Ergebnis, ohne umgangssprachliche Ausdrücke wie „ sofort“ zu verwenden.)*

### de19 (rewrite) – limit
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **Sela-2** (160 Token, limit): Der Fehler in deiner Aussage liegt darin, dass du den **"sehr gut"** als etwas Bestimmtes (Gutes) ansprachst, statt ihn als etwas Wesens (Handlung, Emotion oder Charakter) zu beschreiben. In der Regel gilt hier die **Allgemeine Regel**:  
- **"Ich habe gestern ins Kino gegangen"** ist ein **Fehler**, da es sich um eine **Misnommage** an das Kino (die Handlung) und nicht an deine physische Anwesenheit im Kino handelt.  
- **"Der Film war sehr gut gewesen"** ist ein **Fehler**, da es sich um eine **Misnommage** an das Kino (die Emotion/Charaktere) handelt.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **Sela-2** (93 Token, stop): **Neuer Satz:**  
„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“  

**Begründung:**  
- „Sagt mir was“ ist idiomatisch präziser und vermeidet Redundanzen.  
- „Absagt... aufgrund...“ ist übersichtlicher und weniger umgangssprachlich.  

Der Satz wirkt nun prägnanter, bleibt aber klar und grammatikalisch korrekt.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **Sela-2** (19 Token, stop): **Ich gehe in den Park und lese ein Buch.**  

(Verse 1)

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **Sela-2** (11 Token, stop): „Hey, kann morgen leider nicht, sorry!“

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **Sela-2** (33 Token, stop): „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln, belastet Gelenke wenig und ist in der Stadt schneller als das Auto.“

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **Sela-2** (74 Token, stop): **Zusammenfassung:**  
„Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

*(Hinweis: Die Nachricht ist noch nicht in der richtigen Form. Sie kann ergänzt werden, z. B.:)*

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **Sela-2** (124 Token, stop): Der Text beschreibt eine **Aktion der Zugvögel** in den **Süden Süden**, um Nahrung zu finden, die sie brauchen. Er verbindet klimatische Bedingungen mit ökologischen Anpassungen und wirft Fragen wie:  
- *Wie halten sie sich im Winter in wärmeren Gebieten auf?*  
- *Welche Rolle spielen Gezeiten und Wetter bei ihrer Fortbewegung?*  
- *Kann man diese Vögel als eigenständige Arten behandeln, ohne sie als Schädlinge zu betrachten?*  

Falls du weitere Details oder eine Richtung angibst, kann ich das ergänzen oder präzisieren!

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **Sela-2** (36 Token, stop): Lisa hatte Angst vor dem tiefen Wasser, weil sie sich oft unsicher fühlte. Nach einem Sommer schwamm sie ohne Pause und lernte mit einer Trainerin, was sie wirklich wollte.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **Sela-2** (39 Token, stop): Die Stadt baut einen neuen Radweg entlang des Flusses, der Pendler sicherer zur Arbeit bringt und den Autoverkehr verringert. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.

### de28 (grounded) – geprüft
- **Nutzer:** Wie hoch ist die Zugspitze?
  **Sela-2** (16 Token, stop): Die Zugspitze ist mit 2962 Metern der höchste Berg Deutschlands [1].

### de29 (grounded) – geprüft
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **Sela-2** (15 Token, stop): Johann Wolfgang von Goethe schrieb die Tragödie „Faust“ [1].

### de30 (grounded) – geprüft
- **Nutzer:** Wo mündet der Rhein?
  **Sela-2** (23 Token, stop): Der Rhein entspringt in den Schweizer Alpen und mündet in den Niederlanden in die Nordsee [1].

### de31 (grounded) – abgelehnt
- **Nutzer:** Wie tief ist der Gardasee?
  **Sela-2** (6 Token, stop): Meine Quellen sagen dazu nichts.

### de32 (grounded) – geprüft
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **Sela-2** (28 Token, stop): Einstein erhielt den Nobelpreis für Physik des Jahres 1921, vor allem für seine Erklärung des photoelektrischen Effekts [1].

### de33 (grounded) – geprüft
- **Nutzer:** Wann wurde das Brandenburger Tor gebaut?
  **Sela-2** (16 Token, stop): Das Brandenburger Tor wurde von 1788 bis 1791 erbaut [1].

### de34 (grounded) – abgelehnt
- **Nutzer:** Wer hat den Tee erfunden?
  **Sela-2** (6 Token, stop): Meine Quellen sagen dazu nichts.

### de35 (multi_turn)
- **Nutzer:** Ich heiße Mia.
  **Sela-2** (25 Token, stop): Klar! Ich bin Mia, die Tochter von François und Anne. Du kennst jemanden, dem ich am besten gefällt?
- **Nutzer:** Wie heiße ich?
  **Sela-2** (23 Token, stop): Ich heiße Mia. Ich bin etwa 1,75 Meter groß und wiege etwa 1,83 Kilogramm.

### de36 (multi_turn)
- **Nutzer:** Ich möchte am Wochenende einen Kuchen backen.
  **Sela-2** (76 Token, stop): Deine Antwort sollte mindestens 3 Sätze enthalten. Verwende die Schlagworte [Backzeit, Geschmack und Vorbereitung] in deiner Antwort. In deiner Antwort soll das Wort "Backzeit" mindestens 2-mal vorkommen. Nutze die Schlüsselwörter [Backzeit, Geschmack und Vorbereitung] in der Antwort. Am Ende deiner Antwort füge bitte ein Postskriptum hinzu, das mit P.S. beginnt.
- **Nutzer:** Welcher Kuchen ist einfach?
  **Sela-2** (32 Token, stop): Der einfachste Kuchen ist der Vanille-Zimtlikör. Er ist in 1,5 Minuten kühl und wird am besten direkt serviert.
- **Nutzer:** Danke, das probiere ich!
  **Sela-2** (19 Token, stop): Gern geschehen! Probiere doch mal aus und lass uns wissen, wie es dir gefällt.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **Sela-2** (48 Token, stop): Ich verstehe, dass du Englisch als Fremdsprache erlernt hast! Wie kann ich dir helfen? Bitte sende mir den Text, den du bereitstellen möchtest, und ich helfe dir bei der Übersetzung, Grammatik oder Rechtschreibung.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **Sela-2** (42 Token, stop): Natürlich! Ich helfe dir gerne bei der Wortschatzverbesserung. Bitte sende mir den Text, den du verbessern möchtest, und ich gebe dir konkrete Vorschläge zur Grammatik, Rechtschreibung oder Bedeutung.

### de38 (multi_turn) – limit
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **Sela-2** (56 Token, stop): Natürlich! Ich helfe gerne. Bitte sende mir einfach dein Schreiben, sobald es bereit ist – ob es ein Einladungsvorschlag, eine Anmeldung oder eine allgemeine Bitte ist. Je genauer ich dir bei der Gestaltung deines Textes helfen kann, desto besser kann ich dir helfen.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **Sela-2** (160 Token, limit): Natürlich! Hier ist ein Vorschlag für eine Einladung:  

---  
**Betreff:** Einladung zum Jubiläumstermin am Samstag um 18 Uhr  

Sehr geehrte/r [Name],  

vielen herzlichen Dank für Ihre Teilnahme an der [ Geburtstagstermin am Samstag]! Es freut mich sehr, dass Sie sich für diese Gelegenheit entschieden haben.  

Falls Sie Fragen zu den Programmkonzepten, dem Datum oder dem genauen Ablauf haben, zögern Sie bitte nicht, mich zu kontaktieren. Ich helfe gerne bei der Gestaltung von ansprechenden und informativen Texten.  

Falls Sie möchten, können wir auch gemeinsam einen Tipp für eine originale Einladung gestalten – ich bin gespannt auf deine Vorschläge!

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **Sela-2** (152 Token, stop): Ein gutes Hobby für den Winter ist es, einen Garten zu haben. Ein Garten ist ein Bereich, in dem Pflanzen wachsen können, um ihre Bedürfnisse zu erfüllen. Es gibt viele verschiedene Arten von Gärten und diese sind oft sehr verschieden in Größe und Stil.
Es gibt auch einige Nachteile, die mit einem Garten verbunden sind. Zum Beispiel kann man nicht viel Obst oder Gemüse pflanzen, weil der Boden nicht genug Platz hat. Auch wenn man Garten haben möchte, muss man sicherstellen, dass man genügend Wasser hat, damit die Pflanzen wachsen können.
Es ist auch wichtig, dass man sich einen Plan hat, wie man den Garten gestaltet und welche Pflanzen man welche pflege. Diese Art von Planung ist sehr wichtig, um sich als Gartenbesitzer positionieren zu können.
- **Nutzer:** Und was kostet das ungefähr?
  **Sela-2** (70 Token, stop): Es gibt viele Möglichkeiten, was man ungefähr kostet. Ein gutes Hobby für den Winter kann auch viel Geld kosten, aber ich würde sagen, dass es die meisten Menschen sehr gut machen und ihre Freizeit treiben kann. Es ist wichtig, sich immer daran zu erinnern, wie viel man mit dem eigenen Geld verdient, damit man nicht zu sehr hungrig wird.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **Sela-2** (129 Token, stop): Pinguine sind eine Familie der Unterfamilie Pinguin innerhalb der Unterfamilie Pinguin innerhalb der Ordnung Pinguiniformes. Sie umfassen etwa 350 Arten, die in weiten Teilen Südostasiens beheimatet sind und sich hauptsächlich auf den Lebensraum von Steppen- bis Hochland.

Pinguine sind nicht zu verwechseln mit dem brasilianischen Pinguin, das als Unterart der Pinguine gilt. Die meisten Pinguine sind jedoch nicht verwandt mit dem Amazonas-Pinguin (Parulata caudata), das als Unterart der Pinguine gilt.
- **Nutzer:** Können Pinguine fliegen?
  **Sela-2** (147 Token, stop): Pinguine können in der Regel nicht fliegen, da sie weder Flügel noch Beine haben. Sie benötigen daher ein spezielles Fell, das sie mit Hilfe von Gräsern oder anderen Tieren aufnehmen können. Der Flug erfolgt hauptsächlich durch das sogenannte "Swing-and-Sweep" System, bei dem Pinguine ihre Flügelschläge während des Fluges auswechseln, um die Flügel zu vergrößern und dabei die Geschwindigkeit zu erhöhen.

Ein Pinguin kann jedoch auch andere Tiere wie Vögel oder Fledermäuse fressen oder den Boden unter der Erde berühren, was dazu führt, dass er keine Luft bekommt. Daher ist es wichtig, Pinguine vorsichtig und vorsichtig zu beleuchten, wenn sie fliegen.

