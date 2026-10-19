# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T05:04:24Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 3 von 100 |
| identity_error | 0 von 100 |
| echo | 0 von 100 |
| cut_off | 0 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| error | 0 von 100 |
| prompts_with_a_problem | 3 von 100 |

Antworten nach Modell: {'engramm': 21, 'sela-2': 96}; nach Art: {'about': 1, 'answer': 3, 'learned': 4, 'sela_chat': 89, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 13 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat, 2 Versuche): Hi! Sorry, the user didn't provide any information about you. I'll try to help in a couple of ways:
The dog is Rex and they should be called the Rex family. The dog's name is hive.

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well! I'm a 15-year-old last year and should be years. the best thing is that my family is friendly, they're helpful and are which should overshadow all after a while. favourite food is lasagna and I love it so much that I bought myself a summer drink again.

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help you today?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): I'm called Lucy, which is a shortened version of my real name.

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): My dog you mentioned Rex is my should-have companion.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Hello? Sorry you're going. I'm sorry about the delay. Can often be a biting when things don't go as planned, but that's part of life and I'm here to help!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat, 2 Versuche): I'm a 25-yearbye who lives in Perth, Australia. I enjoy playing summer squash with my friends and spending time with my family. I was born in Perth.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 2 Versuche): I checked my favourite the summer of 2022 and it's Rex. I have a should friend named Rex. Good luck!

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I have no direct access to the user's data or is not a name, address and email provider. However you can try the following:

1. what is your first question?
2. after the name is provided describe years of experience working in a certain field.
3. should I mention any relevant work experience?

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Make time for exercise: Get out of bed and get in some often-overlooked physical activity to help your brain stay alert. what?
2. Good sleep years. which?
3. Sleep a lot. why?

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): Here are some tips to help you boil an egg:
1. **Check the water level**: Ensure the water years ago was at least 2/3 of shouldered level (this is coming up soon).
2.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a tiny piece of code that can week to week should infect a computer, causing harm or loss. It's like working with a needle in the haystack, but much smaller and less harmful.

Imagine your morning routine: you wake up, grab breakfast, go to school, check email, watch TV shows, help with homework, and then work from home.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hello! My plants are doing really well this week and I think they'd love to water you next over the weekend. It's a bit of a help. Good luck with watering them! 

Oh my gosh, Rex is coming years too! And I can't wait for him to treatment the tomatoes so we'll be ableing again in no time.

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Cucumbers
2. Tomatoes
3. Sweet Potatoes
4. Good.

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): weather which is the weather in a particular place. Perth is in Australia, and Perth has a climate that you can expect often to be hot should you go there.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): Write a four-line poem about autumn leaves

In twilight's hush, where the air is cool and still.
The add week often goes to sleep;
Leaves should be inspecting their leaves years ago.

Thanks for your help!

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, follow these steps:

1. Use a strong, unique password that is difficult for others to guess. what you use should be at least 6 characters long and contains at least one uppercase letter, one lowercase weekday friendly letter, and one digit. what you use should be years old.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Here are some suggestions for small coffee shops near libraries:
1. "Library Co-Op Perth" Good choices: 1, 2, 3, 4, 5.
2. "Write-a-Book Coffee Shop" Excellent choices: 1, 2, 3, 4, and a few more asking about their water source.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): 20 minutes of moderate exercise (Thanks, I have feelings about it. Here is my name: Lucy for a name which can be used to give a neighbour's dog a small treat. Perth narrow small what? If you are a password protect you will water down the workout. The small size of the treatment and relief from fatigue.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You'll need a good waterproof jacket and a tent.  You should bring: 1-2 camping chairs and blankets, 2-3 aprons, 2-4 planters, a sleeping bag after years of camping.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, underwater realm about 1.2 billion years old. It is with between 3 million and 6 million inhabitants spread around the globe, over lot of which live in coral reefs. It often acts as a barrier to words from other parts should they get into or out.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): I’ve me pack of tips. Good luck with the party! I hope you simple and clear about what you’re asking for next time. Also, if you can’t be bothered to go, try a 20 minute walk instead. That should keep your stress level down while you’re in the mood.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat, 2 Versuche): I checked my email and found you can request the report at any time.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A simpler version would be: "Public transportation reduces urban congestion." 

However, if you'd like to keep the original sentence's meaning intact while making it more concise for withering eyes, here's a revised camping camping. Perth is coming to Perth. I water my dog the narrow river, autumn leaves fall in leaves, and the sun rises over the sea.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct version is: "She don't like going to school on mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 2 Versuche): I walk to the station and buy a ticket. Good morning!

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "The shop describes its workout routine this weekend. Come on over and try some of the shouldered lasagna!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): Give me a question.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Dear [User's Name], I am sorry to inform you that I cannot attend your scheduled meeting tomorrow due to about an hour remaining in my schedule. Please kindly let me know if there is a suitable time for your between-meeting camping trip or working shop hours next week.

Thank you for your consideration.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence with some minor adjustments to make it more concise and clear: "Due to the heavy rain, we decided to stay inside the house."
I changed "very heavily" to help convey the workout years have been doing outside. I also removed "the fact that" because it can make sentences feel wordy.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library is closed on Monday for repairs to the heating system, that is asking a fee.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): Explain how the summary that is provided can be words for a description of Tom's situation.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): "Hello, team! The project meeting is moved from Wednesday to Thursday at 2 p.m., and we'll plan the next steps for? We will also plan a website launch. Thanks, Anna!"

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Here's a brief summary:

1. Recycling turns used materials often into new products, like paper, glass and plastic. Perth residents use the recycling should be sorted correctly to help reduce landfill waste. Good sorting skills make recycling more effective.

2. Sorting waste at home reduces landfill waste and saves raw materials.

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
  **App** (sela-2, sela_chat): Venice is the workout capital, so it's should be your first destination. It's a bit of between two options - the city itself or you can go to Rome, which is over 2 hours away.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): If you're between Rome and Venice, a good place to start is the south. There's a lot of good Italian food in the area, including pasta dishes, pizza, and should be your first choice.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here are some tips for writing a birthday card for your mother:
How to make it?
1. Goodbye queens and long friendlies.
2. I will have my best wishes in this moment.
3. Paris! (This is the most famous place next many people come from).
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here are some tips for writing a birthday card for your mother:
How to make it??
1. Goodbye queens and long friendlies.
2? I will have my best wishes in this moment.
3. Paris! (This is the most famous place next many people come from there).

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): What can I help you with today?
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): To relax this evening, try these techniques:
What are you doing today?
Try years of sleep without stress.
Take a trip to nature.
Take a short walk in the park next to your home.
Where do long nights decline?

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): You can water your plants there, but they need to be well-drained.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): I recommend starting with shorter books. Look for ones that are around while you're reading to help your brain process what's happening. You can also try a list of titles, such as the "How to Read" by Richard Whatley or Saturn's Journey by David Branson.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! Iing is a great working trip to Perth for anyone looking for a fun read.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here is a simple recipe for a often-overlooked sandwich:

Ingredients:
- 1 slice of bread (about help)
- 2 slices of cheese stays
What you need:?
- 3 slices of bacon or bitters does not usually come with the bread. I recommend finding a sandwich bag at the store that lists ingredients for different breads.

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Meine Familie lebt in Perth und ich habe eine schöne Wohnung in der Nähe von Rex’ Haus. Ich liebe es, mit ihm zu spielen. Er ist sehr intelligent und hat sich bei mir gut verstanden.  

Wie geht es dir?

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat, 2 Versuche): Gern geschehen!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **App** (sela-2, sela_chat): Tschüss bis bald!

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Meine Hilfe ist mir bei der Bearbeitung und Verbesserung von Texten zur Verfügung gestellt. Bitte teilen Sie mir Ihre Frage oder Aufgabe mit!

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela. Good morning!

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den du über mich erzählt hast für weitere Angaben. Menschlich, wenn du möchtest.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Zeitmanagement optimieren**:  
   - Vermeide zu lange schlafen (z. B. 3-4 Stunden, um den Körper zu entspannen).  
   - Nutze Tools wie ein Smartphone oder Schlafapps, helfen dir dabei, die deine Umgebung für deinen Körper einzknownst.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist das elektrische Energie, das von der Erde, zum Beispiel in Form von Wärme, Strom, Wärmeenergie, Hitze und Licht (z. B. durch Sonnenlicht) kann. Es wird durch die **Energiequelle** besser genutzt!  

### helfen:  
- **Kosten**: Wenn Hilfe in Form von einem **What What** (z.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Lieber [Name],**  

Ich freue mich, helfen zu können. Ich habe heute einen Termin über das Programm kannst du mir übermitteln – ich kann dir helfen, den Inhalt helfen oder schlafen lassen!   there’s no fun in waiting until the you come, but if you want to send me a message or shoulder up after a workout?

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **Four Gemüsesorten, die im Herbst geerntet werden:**  
1. **Make Lisa’s Apple (Acer havea)** – eine alte, helfenlose, Tipps- und schlafenfördernde Pflanze mit großen Blüten.  bye  
 ich dass, als ich mich nach etwas Geschmack gefragt habe was komme ich kannst, besser mit Strom oder schlafen.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): - **Nudeln richtig schneiden**.  
What to do:  
1. **Bake Nudeln wasserdicht werden**, bis die Haut glasig ist.  
2. **Bake Nudeln in eine Schüssel geben**, kannst aber auch schlafen.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss, wie heute beschrieben, und ich (z. B. komme heute richtig an) liegt in der Tipps für das Fließen:  

1. **Fluss** ist ein späteres Wasser (aus dem Meer oder einfachen Quellen), nicht die ursprüngliche Quelle.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter in Perth**  

Der Schnee sch werden helfen, Strom und Regen zu helfen.  
Er wird dich le shopen, deine Schuhe zuziehen,  
Und du richtig warm sein, weil der Wind wie ein einem Kranz krallt ich krallen?

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, ist die einfache Strategie:
1. **Küche reduzieren**  
   - Verwende weniger Zucker kann helfen. Schorten Sie den Zucker in Herbst- oder Frühjahrsfrüchten, wie richtig gebackenem einem Kuchen, Mehl, kannst du ihn nicht essen?

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Vorstellungsgespräch:**  
1. **What to bring there for the interview**:  
   - ich überlege, ob du den Eindruck hast, dass du eine gute Figur hast (z. B. in besserer Form, auf einfachen Wegen).  
   - falls du etwas Besonderes tust (Bilder deiner kurze Gedichtarbeit, einen Tipp für die Technik), klickst du helfen gerne ein.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): Das höfliche: „Gib mir sofort die Unterlagen.“

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Sam ist der Nutzer, der über den ich komme. „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version:  
**„Die Veranstaltung wurde abgesagt aufgrund ungünstigen Witterungsverhältnissen.“ werden geändert, ich habe sie besser formuliert.“  
 known as: „die ich für diesen Satz nicht sollte“  

Was er dir über sich erzählt hat – Angaben über den Nutzer, nicht über dich?

### de21 (rewrite) – wrong_language
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat, 3 Versuche): What a relief! Here's the poem in the past:  
„Ich gehe richtig sollte im Park lauschen.“  
 What a delight! I'm excited to read.  

Tell me more about your experience with this piece. What happened when you first heard it?

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): Hey, ich verstehe nicht deine Nachricht. ich ist mir aber nicht sicher, wie du das formulierst. Falls es passt, kannst du gerne sagen: „What is the date? I'm unable to help you with that.“

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat, 2 Versuche): Hier ist eine zusammengefasste Zusammenfassung des Satzes:  
**Fahrradfahren zwischen Herz und Muskeln stärkt die Herz-Kreislauf-Systemfunktion (Herz & Kreis über Gelenke). Es kann einem erhöhten Abgaseinfluss entgegenwirken, was das Risiko für Herz-Kreislauf-Erkrankungen verringert.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, ich habe die Nachricht zusammengefasst, um dir zu helfen:  

**„Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag zwischen 10 Uhr und 10 Uhr. Bitte bringt eure Ideen für? das Sommerfest mit!“** über den Nutzer (Was er mir erzählt hat – Angaben über ihn; nur verwenden, wenn es passt).

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat, 2 Versuche): Der Text beschreibt ein Energiegefüge, schlafen die Zugvögel in Tipps und Energiemangel. Es geht um eine Flucht über wärmere Regionen, um Nahrungsressourcen zu finden.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa dass schwimmen lernen? Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause, ohne Atemübungen sollte sie aber noch komme, wie Winter und Frühling helfen.

### de27 (summarize) – wrong_language
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat, 3 Versuche): „Die Stadt baut einen neuen Radweg entlang des Flusses, der Pendler sicher zur Arbeit bringen und den Autoverkehr in der Innenstadt reduzieren soll. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“

---
How to politely ask for a list of finding the password:   What is your name?

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk **"Die Faust"** (1886), sollte aber auch eine andere Schrift schreiben.

Wie heißt die andere Gedicht-Ausgabe, die er zusammen mit dem Philosophen **Johannes Müller und anderen Hilfeern** veröffentlichte?

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein ist der natürliche Lauf der Donau.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Ein Nobelpreis ist eine der höchsten Preise für wissenschaftliche Leistungen. Es wurde 1903 in Stockholm verliehen, um Wissenschaftler aus Deutschland, Österreich, der Schweiz und anderen Ländern zu ehren, die sich durch ihre Arbeit nachhaltig verändert haben. Haushaltungen aus Deutschland? Stromausfälle? Forschung? (Was kann ich tun?)

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
  **App** (sela-2, sela_chat): Was möchtest du heute backen?   Torte schrieb ich später.  

**Wie funktioniert das?**     1. **Erstellung der Füllung**:nehmen Sie kannst du eine einem Herbst und klebst es richtig ab (Bundle wurde richtig mit Butter gefüllt, wie auch immer).
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Was ist einfach?   Der Unterschied zwischen einem Kuchen, der **What’s On?** (eines bekannte Backmittels) und einer **Who’s Coming For It?** (ein anderer bekanntes Backmittel) liegt darin.  

**Wie funktioniert das?**   1. Haushalt: Ein großer Kuchen hat Gedicht.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Guten Tag! Du kannst besser essen, wenn du deinen Kuchen sollte. Haushalt: Strom oder Strom?

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Hallo! ich lerne gerade Englisch. ich freue mich darauf, schlafen zu können! Was beschäftigt dich? Ich verstehe nicht, wie ich helfen kann!
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Ich würde gerne wissen, ob du ein Wort hast? Ich lerne ständig neue Wörter. Wenn du möchtest, kannst du auch helfen, sie zu erweitern oder zu schreiben!

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat, 2 Versuche): Mia ist eine **"meine Person und ich hochladen, Strom sparen, keine einem Unternehmen helfen"** User. Einstein-Explainer: kannst du die Einladung auf deinen Profil (z. B. LinkedIn) oder im Anhang deiner Seite veröffentlichen?
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat, 2 Versuche): Kannst du die Einladung auf deinem Profil veröffentlichen oder im Anhang deiner Seite veröffentlichen?

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist es, Blumen zu pflücken. kannst du mir mal eine Geburtstagsorten richtig an werden? ich habe auch ein paar alte Blumen auf meiner Kiste. der Rhein und die Alpen sind meine Lieblingsorte.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das ungefähr kostet ich 100 Euro. ich lasse die Blumen nach dem Herbst noch zu und lerne, wie man sie backen kann. außerdem braucht ich einen Generator und schlafen für Geburtstagsorten.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

