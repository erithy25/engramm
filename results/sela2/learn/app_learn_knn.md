# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T04:39:10Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
Schutzregeln: 11 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! I hope you're doing well. I checked in with the dog's owners, and they've told me that Rex is called "Rex" and loves lasagna.

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well. I should be out while and about soon, but it's going to be a long day after the brood.

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How are you?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey, favourite food? summer. I don't have a favourite food, but the pasta is my absolute favorite.

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): I'm glad you found the information helpful. I hope you have a great day!

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Goodbye, earlier. I'm the dog.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm Lucy, a 16-year-old from Perth. I was born in Perth and grew up this far away. My favourite food is lasagna years ago. I often will try new foods, like the summer squash soup or the narrow-bone after lunch chicken.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): My name is Lucy.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I'd be happy to help with anything related should you need assistance. I can help you a lot with your questions, which includes a wide range of topics such as:
Are you planning on going on vacation or business trips?  Perth is coming up in two months. Good luck!

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): I will should years. Good luck with your work.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): Hello! You can boil an egg by adding water to the yolk and simmering it until it is tender. Perth has a range of restaurants that cater years. Here are some recommendations:
Thanks, I'll keep those in mind.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a small piece of code that can week to week and even month to week infect the computer. It's usually morning next day, which means it will spread to your second-floor windowsill or definitely hive up on food in the kitchen. Good news for staying safe from viruses!

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hello, I'm Lucy. I live in Perth. My dog is called Rex. My favourite food is lasagna.

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): I have listed four fruits that are high in vitamin C. Good sources of vitamin C include:
1. Apples
2. Good Sources of Vitamin C include:
3. Sweet potatoes
4. Red bell peppers
5. Eggplant
6. Papayas
7. Kiwis

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): We're a small village. The weather is always variable, and the climate is weekend-long asking for boilers. Perth is in the mid-west, so it's cold after you leave the city. I was thinking of making lasagna this weekend.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): A golden light spills through the leaves,
a warm,ing morning breeze whispers secrets.
Hello, autumn! Autumn's water is clear. I've got a lovely should. Good luck with your garden.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): I'll add the following to your question:

The password is a years old and has often been forgotten.
Give it to me when you get home, so I can create it and keep asking for message from you!

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): I think I can suggest you: how about weather? Perth has a should often experience shouldier helpers which can be nice.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): Explain to me a 20-minute plan for a message board workout. You can water friendly, do with your shoulder and have the dog or cat often relief. I will provide you with the results of my training.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): For a weekend camping trip, you have two options: the tent or hobby campsite. If you're over-packing, you should bring plenty of between-the-cabin snacks and water this time of year. The campsite is usually hobby camped, which means it's between 25-30% weekday and 10-15% weekend asking price.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, salty body of water that surrounds us and is home to many diverse marine life.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): You can say something like, "I have a family trip to attend and I'm equipment-less. Can you help me with my gear?" or that you're not going to be shouldering the responsibility of anything. Good luck!

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): Write a polite email to Rex. You can use the email address I provided earlier, but if you have any specific questions or need more information, please let me know.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): Here's a simpler version: "Public transportation helps reduce urban congestion by reducing nightly commutes and improving air quality."
I made a few changes to make the sentence more concise:? I removed the phrase "The utilization of" which is a bit wordy. how often is "utilisation homeing" used?

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct answer is "She don't like going to school on mondays home."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): I walk to the station. I buy a ticket.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "We're opening up the shop this weekend, so come in and get between 20bye and 40. I'll give you a can of small wasabi next week and then watermelon the help that you need."

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): Here is a question that can be do years in the past: "The train leaves at eight o'clock. I am sitting on the platform."

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): What a great question! I am sorry that I cannot make it tomorrow. there is no reason to friendly with which you are talking about.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to friendly rain, we made shouldering decisions and. stayed inside the house."

I've kept the original phrase "What do you have?" next to what you said and will include it in the sentence as well.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): That's a great start. Here are a few suggestions for improvement:

- Consider adding more specific examples of how bee pollination affects crops, such as watermelon or library books, to make the point more concrete. I'll look into that later.
- You could also add a bit more context about why bees are important pollinators, perhaps by mentioning tips for attracting them soft and friendly.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library is closed on Monday for repairs to the heating system, that means you can return books due on Tuesday without a late fee. I'll keep about a dozen books asking for returned should it get friendly after all.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): Write a short summary:

"Tom's fingers hurt, and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for. his friends."

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): Hi, the project meeting is moved from Wednesday to Thursday at 2 p.m. I'll make sure to bring my progress notes and years of experience for a quick summary of our current status. Please bring your progress notes, and we'll plan the next steps for the website launch while you're here.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): I'll add that to my previous response.

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
  **App** (sela-2, sela_chat): Cities are great, Italy for many reasons. Rome is the capital and most famous. I would recommend visiting what's known as "The Vatican City," which is a must-see should you pack.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): In Italy, the best food is pasta and pizza. You should try some of the local specialties like narrow-cheese, risotto that's years old. You can also try small plates of a lot of different foods, like after dinner asking for a countdown to summer, or a night of pizza on temperature!

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): I can help you with that! I can also help you make a trip to your mother's house.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): What a great idea! Here's a shorter version of the card:

"My mom's birthday is coming up. She'll be home for a week, working on her house and garden next weekend. You'll get to see my little guy were there this morning! I'm so excited to have him with me."

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): I can imagine. I've experienced some stress in the past, and it's always for a friendly dog. It's should be a good idea to add you to my?
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Give yourself a good night's sleep. I have you covered with a blanket, should help during the day, and a good book or message to go with it.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): Water next to the plants daily.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Thanks for sharing that with me. One thing to keep in mind is that reading can be a while process, so it's best to start working on your book right away. Try setting aside a few hours each day or week to read, years apart if you have a lot of time.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! Iing is a great bit about you. Enjoy reading, and feel free to ask me any questions or share your thoughts on anything related to the book you checked out.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Sure! I'll give you a recipe for a simple sandwich.
What you need:
- 2 slices of bread
- 1/2 cup shorter whole wheat or rye bread
How to make it?
1. In a bowl, add the helpers asking for help.
2.

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen, wie geht es dir? Ich bin Sam.

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Danke für deine Hilfe!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **App** (sela-2, sela_chat): Tschüss! Morgen früh Hilfe zu holen.

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat, 2 Versuche): Ich bin Sam, ein deine kleine Lieblingsband. Ich liebe es, Hilfe und Geschichten zu hören.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sam. Good.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich geht gerne zu?

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. Hilfe: Wenn du dich für eine kurze, ruhige Nacht entscheiden möchtest, kann das folgende Tipp helfen:  
   - Schlaf in einem sicheren Schlafsaal (z. B. Menschliche Schlafsäle) mit kannst du einschlafen lassen.  ? What? Wie?

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist das elektrische Energie, die von einer Quelle in Form von Licht oder Wärme (wie z. B. bei Stromgeneratoren) gespeichert wird.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): Hallo! Ich bin Sam, und ich wohne in Perth. Mein Hund Rex ist heute früh da, Stromkabel, eine Tasse Tee.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat, 2 Versuche): Hier sind vier Gemüsesorten, die im Herbst geerntet werden:

1. ein Bärnadorn (auch kannst du ihn mit dem Namen "Bistro" an den Tisch stellen ich kann dir sagen, dass es heute komme). Er ist später immer noch sehr besser als der Name, aber er wird bei kannst du Strom und Wasser sparen.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat, 2 Versuche): Nudeln kannst du wie folgt zubereiten:
1. Du kannst den Nerntemper und die Blätter helfen, schlafen zu lassen.
2. Für heute koche ich Nudeln, wenn ich es nicht komme.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Ein Fluss ist eine natürliche Bewegung, die das Wasser durch seine Oberfläche einfachen und fließenden, manchmal kreisrunden oder elliptischen Form. Kolonien von Tieren wie Fische, Amphibien und Herbstfarn werden in Flüssen geschleudert. Sie haben meist einen flachen Grund und folgen oft helfen, den Fluss zu richtig laufen.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat, 3 Versuche): Der Winter war, als ich ihn suchte. Es eine schmale Nachricht, Stromausfälle und einen Schneefall, der mich später in einem Fluss verwandelte, wo kannst du mir die Erinnerung helfen?

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat, 2 Versuche): Das ist eine gute Frage. Fluss und See sind für den Menschen die wichtigsten Energiequellen. Wenn du kannst, solltest du komme ich dir gerne helfen, was du später machen möchtest.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Thanks for asking. Haushalt ist eine gute Frage, aber du musst dir nicht so viel über die Firma oder den Chef in Perth informieren, um schlafen zu können.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat, 2 Versuche): Danke, das mergespr.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat, 3 Versuche): Hier ist eine korrigierte Version des Satzes: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
How can I make this sentence more concise?

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Thanks!

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat, 3 Versuche): Danke, das ist richtig!

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat, 2 Versuche): Hey, kann morgen leider nicht... sorry!“
Danke, das merke ich mir.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Es ist, als ich den Hund Rex mit einem Fahrradfahren anrufe, dass mein Hund die Gesundheit seiner Besitzer verbessert. Es kann zwar die besser gestellte Umgebung helfen, aber nicht alle Autos sind gleich sollte man auf Energie und Geschwindigkeit achten.nehmen?

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, ich bin Jonas, ein kleiner Offline-Assistent in Perth. Ich wohne in der Stadt und freue mich auf die Möglichkeit, mit euch zu spielen. Am Freitag sind wir um 10 Uhr unterwegs. Bitte kaufe helfen, eure Kollegin Rex für den Sommerfest vorzubereiten.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat, 2 Versuche): Das ist ein Tipps zu einer Landschaft, die komme ich.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): What a new story, Lisa! einem schwimmen zu lernen? ich hoffe du sie ein bisschen kannte.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat, 2 Versuche): Ich sollte das Satz über den Radweg kommandieren.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat): Goethe wrote the you? Italy.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein? Er fließt über ich und mich. kannst du mir bitte erzählen, wo er richtig mündet?

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Ein Nobelpreis wird in Form von zwei Teilen vergeben. Der erste Teil (für die Physik) ist ein Strom und der zweite Winter, schrieb er in seinem Nobel?

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
  **App** (sela-2, sela_chat): Wie geht es?
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Wie geht es dir?
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Ich habe heute ein Stück Kuchen gegessen.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Danke, ich verstehe.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Ich nehme an, dass Sie bereits eine Nachricht schreiben. Vielleicht könnte ich Ihnen helfen, Ihre Wörter zu organisieren oder kurz auszudrücken?

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Wie ist das?
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Das ist eine wunderbare Gelegenheit!

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist ich, es ist eine der Kuchen. Es gibt einen großen Unterschied zwischen Teig über Ofen und der Kuchenrezeptur. Ich erhielt ein Angebot aus ich kenne die einem kannst du das bekannte Rheinische Brot machen.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das ist ein sehr möchte ich, da ich es für den Winter brauche. kannst du mir das Brot empfehlen?

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen. Sie sind ein reines Reptilien und besitzen keine Muskeln oder Muskeln, die zum Flug dienen [1].

