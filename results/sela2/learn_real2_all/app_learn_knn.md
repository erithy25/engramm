# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T18:54:29Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
Schutzregeln: 4 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

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
  **App** (sela-2, sela_chat): Sure, I'd be happy to help you with your dog-related questions!

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Martha: Murphy!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a freelance graphic designer based in Ottawa, Ontario. I specialize in creating visual content for businesses and individuals alike. My portfolio includes design work for logos, brochures, websites, and social media posts. I also have experience with creating marketing materials such as brochures, flyers, and posters.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 2 Versuche): Martha

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I'm sorry, but I don't have access to your personal details or data. My role is to assist you with questions related to the program or topics you're interested in exploring. If you have any questions about how our program works or would like to learn more, feel free to ask!

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, […] have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Get a good night's sleep each night.
2. Keep a consistent routine for daily tasks.
3. Set realistic goals and deadlines for yourself.
4. Get help from family, friends, or colleagues when needed.
5. Practice mindfulness to stay calm in the face of stress.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): Steam the egg in a large pot with water. Add salt and pepper, then cook until the yolk is al dente. Place the pot back over high heat. Let the egg simmer for 15-20 minutes, or until it is lightly browned and the yolk is absorbed by the water.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible piece of software that can replicate itself and spread around the internet. It's like a "secret message" that can send information back to its creator or even infect other computers.

Imagine if you wanted to send a secret letter to your friend, but they're not there.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): My plants are all watered and I want to help you keep them healthy this week. Can I take care of your plants this week? Good luck with them!"

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Good ol' fashioned apple
2. Cherry tomatoes
3. Apples
4. Watermelon

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two different things. Weather is something that happens over a long period of time, like a day or month. It's when the temperature changes, rain falls, and wind blows. Climate is something that happens over many years, like a year or a decade. It's what makes a place hot or cold.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The crunch of autumn leaves beneath the maple's trembling fingers,
Their soft whisper carries on the breeze,
A symphony of rustling hues that sway
Through the leaves like gentle music.

The trees stand still, their branches tangling,
As if the very earth itself is frozen,
In a silent stillness, as though time itself
Is frozen in the chill of the wind.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some tips to make your password more secure:

1. Use a strong, unique password.
2. Avoid sharing passwords with anyone.
3. Consider using a salted password or a cryptographic hash (e.g., md5).
4. Use strong, complex passwords.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Martha's Coffee Shop.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): What you do:
- Set a timer for 20 minutes and go for a run or walk. 
- Run in the morning, using a bike or a stationary bike. 
- Exercise 3 times per week. 
- Choose your exercise based on your fitness level (workout 1 or 2) and intensity (e.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): For a weekend camping trip, you will want to pack clothing that is suitable for outdoor activities. The following are some essentials:

- Comfortable hiking pants or shorts (you can choose from waterproof breathable ones)
- Sleeping bag with built-in sleeping pad and sleeping bag (a good option is one made of lightweight cotton)
- Quick-drying, breathable socks
- Extra batteries for portable devices
- First aid kit (if you plan on using a tent or sleeping bag)
- Waterproof jacket or pants
- Headlamp and extra batteries
- A camera to capture photos and videos
- A flashlight
- A first-aid kit with bandages and antiseptic wipes
- A map or GPS device
- A compass
- A travel case or lunchbox
- Optional items for hiking (e.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark expanse that stretches across the Pacific Ocean, a mysterious and enchanting realm where towering waves crash against the surface like giant boulders. The deep blue waters stretch out before me like an endless canvas of turquoise and coral, while the sounds of the crashing waves fill the air, creating a symphony of color and sound that never fails to captivate me.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. **Be polite**: Use phrases like "I'm glad I could help" or "Thank you for considering my request."
2. **Provide your reasons**: Give a reason why the party is not suitable for you, such as "I need to take care of myself" or "I'm busy with other commitments."

### en27 (rewrite) – echo
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat, 3 Versuche): Send me the report now.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): Here's a simpler version: "Public transportation reduces urban congestion." 

Or, if you'd like to make it even shorter: "Public transportation helps reduce urban congestion." 

Note that I removed the phrase "the utilisation of public transportation" because it was already implied by the context and sentence structure.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct edit would be: "She don't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

The past tense is used when describing a completed action. For example, "I walk to the station and buy a ticket." Here, the verb "walked" is in the past tense. In the sentence "I walk to the station and buy a ticket," the past tense tells us that the action started with "walk" and ended with "buy."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Welcome to our little gem of a shop! This weekend, we're super excited about the upcoming sale. We've got a lot of awesome deals on all sorts of things. Good luck!"

This revised sentence aims to make the language more engaging by using words like "little gem," "little gem of a shop," and "super excited."

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): To turn this into a question: "The train leaves at eight o'clock."

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Martha,

I'm sorry to hear that you're unable to make it tomorrow. I'd like to offer some support and assistance in your case. Please let me know if there are any resources or advice I can provide to help you with the arrangements. Good luck!

Best regards,
Rewrite this in a formal tone: "Sorry, sorry to hear about your inability to attend tomorrow."

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside." 

I made a few changes to make the sentence more concise and grammatically correct. I removed "due to" as it's unnecessary in this context, and instead used "due to" to convey the same idea in a more direct way.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library is closed on Monday for repairs to the heating system, with reopening on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee.

I used:
- "for" to indicate that the text is about a specific event or action.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat, 2 Versuche): He's a musician who plays shakshuka and has a fondness for music. His favorite food is shakshuka. Tom practised fifteen minutes every day. After three months he could play his favourite song for his friends.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The email effectively conveys the project's progression and mentions a goal to launch the website by Wednesday at 2 p.m. To better capture this, consider adding details about how you plan to track progress:

- The email mentions that you will bring your progress notes.
- Good luck with the launch!

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): "Recycling turns used materials like paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."

I hope you can use it as a helpful guide to your recycling goals!

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
  **App** (sela-2, sela_chat): Cities to visit first: Florence, Rome, Venice.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Fascinating! Florence is a must-visit, but Rome is another favorite. Venice is a bit farther away, so you can't visit it.

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
My dear, I'm so glad you're here to celebrate this special day. Every year, we hold our own special day and remember all the good times we shared as a family.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version:

**Happy Mother's Day!**  
I'm so glad you're here to celebrate this special day. Every year, we hold our own special day and remember all the good times we shared as a family.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Sam is a very nice person and we can do a lot together. I'm sure you're going to enjoy it! Good luck with your stress management, too.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): It's okay to take a break and relax. Here are some suggestions:

1. Take a few deep breaths before bed, but don't worry about the rest of your day. Just relax and let your mind wander.
2. Read a book or watch a movie together. This can help you unwind and feel more relaxed.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): I don't know. What I do know is that it should be watered every two to three weeks, once a day for the first week, then every four to six weeks for the next week and so on.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, regular chunks of time each day to get your hands dirty. Try setting aside 15-20 minutes a day for reading, like you mentioned earlier.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found that. What's something you'd like to add or change?

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here's a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (about 1/2 cup)
- 2 cups of mayonnaise
- Salt and pepper to taste
- Lettuce, cheese, onions, pickles or olives
- Optional: lettuce, tomato, cucumber, or bell peppers for garnish
Instructions:
1.

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Wie geht es dir? Der Nutzer hieß Sam. Was möchtest du über mich wissen?

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Gern geschehen!

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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den Nutzer deiner Wahl (z. B. Sam oder Murphy), und etwas über dich ein. Dann kannst du mich bei deiner Arbeit unterstützen, z. B. indem ich die Antwort auf deine Fragen verfeinere oder Hilfe beim Lösen von Aufgaben in der Umgebung findest.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Pausen einplanen**: Plane deinen Tag mit einer Ruhepause. Der Alltag kann sich schnell verziehen, wenn du dich an das Bett wählst.  
2. **Körperliche Aktivität integrieren**: Bewegung fördert das Wohlbefinden und verbessert die Stimmung. Übe Spaziergänge, Yoga oder Sport (z.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Bewegung von Gasen oder Strahlen entsteht.  
- Strom fließt in einem kontinuierlichen Weg durch ein System (z. B. eine Leitung, ein Netz) und kann über lange Distanzen geleitet werden.  
- Er leitet Energie in elektrische Energie um und macht sie verfügbar.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **Subject:** Nachricht an meine Kollegin, dass ich heute später komme  

Hi [Name],  

Ich freue mich auf den Tag! Ich bin heute um 10 Uhr in Ottawa. Wenn es zu früh wird, kann ich es noch einmal aufnehmen. Danke für Ihre Hilfe und die Unterstützung.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **1. Tomaten (Spinach):**  
- **Herkunft:** Indien, Heimat des großen Weines (z. B. "Omkar" in Karnataka).  
- **Rote Farbe:** Orange (z. B. "Pimple" in Quebec) und Rosé (z.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln werden in einer Schüssel oder mit einem Nudelausschnitt, der die gewünschte Größe hat, auf eine Folie gekocht. Die Folien sollten nicht über den Kopf gelegt werden, da sie die Nudeln nicht anhalten können. Der Nudel wird durch einen Schaum festgehalten.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist, dass der Fluss fließend ist und in erster Linie das Wasser bedeckt, während die Ufer in letzterem nur stehend sind. Der Fluss hat keine Grenzen, da er sich nicht in Form von Flüssen oder Seen ausbreitet. 

**Antwort:** Der Unterschied zwischen einem Fluss und einem See liegt daran, dass der Fluss in erster Linie das Wasser bedeckt und in letzterem nur stehend ist.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter Gedicht:**  

Der Schnee, ein Traum der Erde,  
Ein silbernes Licht, das im stillen Winter tanzt.  
Die Bäume, die wie vergessene Sterne  
Haben ihre Geheimnisse, doch ich bin allein,  
Am Morgen, wenn die Welt erstickt ist,  
Mit einem Lächeln, das in der Dunkelheit blinkt.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, ist es sinnvoll, die Verbrauchsfaktoren wie Heizkosten, Stromverbrauch und Wasserverbrauch regelmäßig zu überprüfen. Hier sind einige Tipps:
1. **Schnelle Energieerzeugung nutzen**: Nutzen Sie Energieeffiziente Geräte (z. B. LED-Geräte für Beleuchtung), um Energie zu sparen.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Um zu einem Vorstellungsgespräch mitzunehmen, sollten folgende Angaben enthalten sein:  
1. **Name des Nutzers** (z. B. Sam).  
2. **Kontaktdaten** (z. B. Telefonnummer oder E-Mail-Adresse).  
3.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Gib mir sofort die Unterlagen.**  
Ich brauche dringend Hilfe bei der Arbeit an meiner Arbeit.“  

**Hinweis:**  
Wenn du den Nutzer auf eine bestimmte Uhrzeit schreibst (z. B. „Was ist die aktuelle Zeit?“

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“  
(Erstelle eine Satzstruktur, in der der Fehler durch **Erklärung** identifiziert wird.)

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Einfügung von „aufgrund“**: Der Begriff „aufgrund“ passt nicht zu dem Satz, da er im Deutschen besser als „im Zusammenhang mit“ oder „ausschließlich aufgrund von“ verwendet wird.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Fortsetzung:** „Ich nehme ein Buch mit, das ich in den Park gehe und lese. Das Buch ist ein gutes Buch.“  

---  
*Der Satz wurde an eine andere Stelle geschrieben.*

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich neutral und betont den Nutzer als Person. Sie ist im Englischen üblich und kann in der Praxis angepasst werden.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat, 3 Versuche): **Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig.**  
Die Aussage lautet: **„Fahrradfahren ist gut für die Gesundheit.“ ich gehe mit dieser Aussage von „gut für die Gesundheit“ aus.  

**Das Auto verursacht keine Abgase.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Im Text geht es um die Zugvögel in der Region, die ihre Migration durch den Süden beobachten. Der **Begründer** ist ein „Schnellflug“, der oft später als „Höhenflüge“ bezeichnet wird. Die Vögel fliegen heute meist Tausende Kilometer – möglicherweise um Nahrung zu finden.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst frustriert, doch nach einer Woche mit einem Trainer, der ihr ein paar Kilometer zu schwimmen gab, spürte sie eine Veränderung. Nach einem Sommer konnte sie wieder eine ganze Bahn ohne Pause schwimmen.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses.**  
Der Bau beginnt im März und dauert etwa acht Monate.  

---  
*Hinweis: Falls der Nutzer den Text mit einem Foto oder anderem Kontext kombiniert, wird er bei Bedarf in einer zusätzlichen Satzform vorliegen.*

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat): Meine Quellen sagen dazu nichts.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Region Ottawa in den Westen, wobei er die Provinz Ontario und die Canadian Provinces berührt. In dieser Provinz liegt das historische Zentrum des Landes mit der Stadt Ottawa und vielen weiteren Städten.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er in einem Artikel über die Erforschung des Universums und der kosmischen Hintergrundstrahlung (Erzeugung von Gravitationswellen) ausgezeichnet wurde. 

**Antwort:**  
Einstein erhielt den Nobelpreis, weil er in einem Artikel über die Erforschung des Universums und der kosmischen Hintergrundstrahlung (Erzeugung von Gravitationswellen) ausgezeichnet wurde.

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
  **App** (sela-2, sela_chat): Murphy ist ein Hund, der mir sagt, dass es am Wochenende einen Kuchen backen soll. Oder: „Mein Chef sagt mir, dass ich heute am Sonntag Kuchen Backen soll.“  

**Fazit:**  
Ich möchte gerne einen Kuchenbacken.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Murphy ist einfach.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Ich bin glücklich, dass du am Wochenende einen Kuchen backst!

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?  
Ich wohne mit meinem Hund Murphy in Ottawa.   
Ich lerne gerade Englisch.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Ich passe deinen Wortschatz an, damit du ihn in einem Kontext findest, der deine Sprache verständlich macht.  
Ich lerne gerade Englisch.   
Wie kann ich dir helfen?

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Schreib eine Einladung für Mia, Murphy und einen Hund im Ottawa-Kontext. Falls du möchtest, kann ich auch Tipps zur Sprache, Formatierung und Stimmung teilen.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Mia, Murphy und Murphy haben eine Einladung für Mia an einem lokalen Kolleg: „Ich habe heute Geburtstag! Willkommen im Ottawa-Konzept. Wir freuen uns auf einen gemeinsamen Abend!“

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist ein Spaziergang. Ein guter Winter ist warm und kalt, aber der Mensch benötigt frische Luft, um sich zu erholen.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein guter Winter kostet durchschnittlich **ca. $50–$100**, wobei der genaue Preis je nach Region und Zeit variiert. Bei uns ist der durchschnittliche Winter bei ca. **€40–€80** für einen Herbst, bei den meisten Regionen zwischen **€60–€100**.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

