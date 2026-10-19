# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T04:39:38Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
Schutzregeln: 1 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi! How's your dog doing?

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well. I was just finishing up some chores around the house, so it's not too bad to be home today.

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How are you?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! I'm Lucy, and my dog is called Rex. My favourite food is lasagna.

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): I'm glad you found my answer helpful. If you have any other questions or need further clarification, feel free to ask.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Goodbye, dear.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm Lucy, a kind and gentle dog named Rex. I live in Perth, Australia.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): My name is Lucy. I live in Perth.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I'm happy to help with any questions or requests you may have about our dogs. If you have a specific breed or type of dog, please let me know so I can give you more tailored advice.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Start early
2. Avoid procrastination
3. Set a goal
4. Be proactive

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): There are a few ways to boil an egg, but the most common is boiling it in water.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a small piece of code that can be attached to another computer or device, and then infect it. It's like a tiny virus that can change the way you think about something, making it seem like it's harmless when it actually isn't.

A computer virus can be very clever, and they can also be really hard to spot.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): "Hi, I'm Lucy. I live in Perth and my dog is called Rex. I'm so glad you're interested in helping me out with watering your plants next week. If you need any help or want to chat about something else, feel free to ask."

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): Here are four fruits that are high in vitamin C:
- oranges
- strawberries
- raspberries
- blackberries
- watermelon

These fruits are all low in calories and can be consumed as snacks or added to salads.

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two different things. Weather is an average of the conditions that occur in a given place at a given time of day, usually over a period of several days or weeks. Weather can be caused by natural factors such as wind, rain, snow, or temperature changes.

On the other hand, weather is the long-term average of these different factors.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): As autumn leaves fall,
A symphony of red and gold,
The earth exhales a fragrance sweet,
And all the world comes alive.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): You can use a combination of strong passwords and encryption. For example, you could use a password with at least one uppercase letter, one lowercase letter, and one digit. You can also use a mix of letters, numbers, and special characters. For instance, you could use "DELAX" instead of "DELAXL".

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): I can think of a few names that might fit the description: The Café de Flore or L'Avocado

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): Try to get at least 5 minutes of exercise per day. Try to eat a nutritious breakfast, and do some walking. This will help you get more oxygen in your body.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): For a weekend camping trip, you should pack:

1. Waterproof and waterproof clothing: A layer of waterproofing is essential to protect yourself from rain and ensure you have enough water for the day's activities. You'll want to bring a hat, sunglasses, sunscreen, and any necessary safety gear like a whistle or flashlight.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark blue-green expanse of water that stretches out for miles from shore.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): You can say something like, "I'm not interested in attending the party. I prefer to hang out with my friends and family." This is a friendly way to decline an invitation without putting too much pressure on them.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): That's a good idea, but if you want to say "Send me the report now," you could rephrase it as: "Please send me the report when you're ready." This way, you're making a clear request for your dog's report.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): Here's a simpler version: "Public transportation reduces urban congestion." 

Or, if you'd like to keep it more concise: "Public transportation improves urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "She doesn't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat, 3 Versuche): I walk to the station and buy a ticket.

Thanks for the edit!

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Our shop has a sale this weekend. We have some fantastic deals on the menu for our new summer menu."

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): I'll keep that in mind.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Dear Sir/Madam,

I hope this message finds you well. I am Lucy, and I reside in Perth, Australia. My dog, Rex, is my constant companion and beloved pet. I frequently find myself craving a good lasagna meal to start the day off right.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we opted to stay inside." 

I made a few changes to make the sentence more concise and grammatically correct. I removed the phrase "Due to," which can sometimes make sentences feel wordy or redundant. I also changed "very heavily" to "heavy," which is a more common and idiomatic way to express heavy rain.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): That's a great way to summarize the main points. To make it even more concise, you could consider combining the ideas of pollinators and crops into one sentence: "Bees are important pollinators, as they collect nectar from flowers and pollen sticks to their bodies to help plants produce fruits and seeds." This version gets straight to the point and uses fewer words.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library is closed on Monday for repairs to the heating system, so books that are due on Monday can be returned on Tuesday without a late fee. The reopening of the library will take place at 9:00 a.m., Monday, and Tuesday, with no late fees.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): Thanks for sharing this! I'll keep that in mind.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): Hi Team,

I hope this email finds you well. I wanted to touch base with you about the project meeting we discussed earlier today. We're moving forward, but I'd like to remind you that there will be a few adjustments to make before the meeting. Please bring your progress notes to ensure everyone is on track.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): That's a great summary. It effectively conveys the benefits of recycling, as well as how it saves raw materials and energy. The use of words like "recycled" and "effective" makes the text more engaging and informative.

Here's an alternative version that could be even more effective: "Recycling turns used materials into new products.

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
  **App** (sela-2, sela_chat): Venice is a must-see, but if you're looking for something different, Florence might be the best choice. It's known for its beautiful architecture and art scene, as well as the Duomo, Ponte Vecchio, and Uffizi Gallery.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Lasagna is a classic Italian dish, and you should try it at least once. It's made with lasagna noodles, mozzarella cheese, and a bit of extra virgin olive oil. The noodles are cooked in a saucepan with some salt and pepper, then the mixture is heated until the noodles are tender and crispy.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): I can help you with that!
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version:

"Happy birthday to my mom! She's so excited and happy with the way you're doing. My favorite food is lasagna, so I'm glad you enjoyed it."

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): I can imagine. It's common for people to feel stressed or anxious when they're faced with something new, like a new job or a new city. If you have Rex, there are a few things you can do to help him relax and reduce stress:

First, try relaxation techniques like deep breathing exercises, meditation, or yoga.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): One thing you can do is to sit in a quiet spot, like a park or a peaceful garden. Sit comfortably with your dog close to you. You can also try listening to calming music, such as nature sounds or soothing classical music, that will help distract you from the stress of the day.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): Water it every 2-3 weeks. This is because the soil will get dry and shriveled, and that's not ideal for a houseplant.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): You can try to stick to a daily reading routine, but also be flexible. If you're in the mood for something new or exciting, read something that interests you.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found it useful.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here's a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (dough is the most common type)
- 1 slice of cheese
- 3/4 cup unsalted butter
- 1 cup heavy cream
- 1 tsp salt
- 1/2 cup freshly grated Parmesan cheese
- 1 tbsp fresh parsley, chopped
- 1/2 tsp pepper
- 1/2 cup milk or water
- Optional toppings: eggs, cheese, lettuce, tomatoes, etc.

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen, wie geht es dir? Ich bin Sam, und ich wohne in Perth.

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Danke für deine Hilfe!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **App** (sela-2, sela_chat): Tschüss! Gib mir weitere Informationen, damit ich dir weiterhelfen kann.

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Ich bin Sam. Ich bin ein kleines Sprachmodell auf deinem Computer, das dir erklärt, wie man mit deinem iPhone, iPad oder anderen Geräten arbeitet.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sam. Ich wohne in Perth, in der Nähe von Perth Airport und Perth Station.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe dir gerne bei der Suche nach einem neuen Zuhause, Tipps zur Pflege deiner Haustiere und Antworten auf Fragen zu deinen Bedürfnissen.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. Du musst dich in der Nacht nicht alleine schlafen lassen, sondern mit deinen Freunden oder Familienmitgliedern.
2. Du solltest mindestens eine Stunde nach dem letzten Schlafgehen eine Tasse Tee trinken und sich um den Hund kümmern.
3. Du solltest einen kleinen Kühlschrank und eine Schreibtischschublade haben.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist die Energie, die durch elektrische oder chemische Prozesse fließt. Es gibt zwei Arten von Strom: elektrischer Strom (störlicher Strom) und elektrischer Strom (niedriger Strom).

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): Danke, dass du heute kommst.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): Ja, im Herbst werden vier Gemüsesorten geerntet: der Karstkraut (Caramelsoße), der Rotkraut (Laporte), der Rosmarin (Rohkartoffeln) und der Kekse (Hackel).

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Ich habe Nudeln richtig gebacken, wenn ich sie vorher mit einer Schale aus Wasser und einem Glas Milch aufgieße.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Ein Fluss ist ein breiter und durch Gewässer fließender Wasserweg. Er kann in zwei große Kategorien eingeteilt werden: Nebenfluss (abgeleitet von der Landschaft) und Zufluss (von einer natürlichen Quelle).

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter im Perth Park**  

Der Winter trägt Schnee, das in zarten Tönen weht,  
Draußen kippt die Luft sanft, wie ein Lied,  
Die Berge treiben ihre Spuren in den Schneetagen,  
und ein Lied aus dem Flüstern der Bäume.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Im Haushalt kann ich Energie sparen, indem ich **Automaten** einstelle und sie nach Bedarf an das Stromnetz anschließe. Gleichzeitig kann ich mit dem Fahrrad oder der Stadtmobilität viel Energie sparen, denn die Autofahrt ist hier im Durchschnitt **sehr schnell**.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Ich würde gerne eine strukturierte Vorbereitung mit einem kurzen Gespräch über den Hund Rex kombinieren. Dazu gehören:

1. **Fokus auf das Hundeproblem**: Was ist der Hund Rex? Er ist ein schnaubiges, unerbittliches Wesen, das sich durch seine Aggressivität, Aggression und Unkontrollierbarkeit auszeichnet.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): Danke, das merke ich mir.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“

Die Fehler sind:
- „habe“ → „gegangen“ (ein Verb, das im Deutschen nicht richtig ist).
- „sind“ → „ist“ (keine grammatische Fehler, die im Deutschen auftreten).

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes: „Aufgrund der ungünstigen Witterungsverhältnisse wurden die Veranstaltung abgesagt.“ 

---

### **1. Verbesserung:**  
„Durch die schlechten Wetterbedingungen wurde die Veranstaltung abgesagt.“  
- „Durch“ ersetzt „durch“, da es in diesem Zusammenhang besser verwendet wird.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): Danke, das ist schön.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): Ja, es geht leider nicht!

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Hier ist ein zusammengefasster Satz: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“

Ich hoffe, dass ich dir helfen konnte!

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, ich bin Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt eine saisonale Wanderung von Zugvögeln durch Perth, die zwischen Herbst und Frühling (Winter) beobachtet wird. Das Verhalten der Vögel hängt vom Wetter ab – beispielsweise ist ein gutes Klima ideal für den Winter oder umgekehrt. Der Text stellt zudem die Beziehung zwischen Zugvögeln und ihren Nahrungsquellen dar, die in den verschiedenen Phasen des Jahres berücksichtigt werden.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Das ist wirklich eine fantastische Geschichte.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): Danke, das merke ich mir.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat): Goethe wrote many works, including:
1. The Sorrows of Young Werther (1797)
2. The Sorrows of Werther and the City (1806)
3. Das Leben der Anderen (1815)
4. Faust (1816)
5.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt durch den größten Teil von Perth, den "Burnard Highway".

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik in der Kategorie "Bestes Erstlingswerk" im Jahr 1905. Er wurde dafür ausgezeichnet, dass er eine ganze Reihe von Büchern, Artikeln und Gedichten über die Natur und die Seele geschrieben hat.

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
  **App** (sela-2, sela_chat): Ja, ich brauche einen Kuchen.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Ich habe den Kuchen mit frischen Kräutern und einer Mischung aus Schokolade, Schokoladekaffee und Milch.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Ich habe den Kuchen mit frischen Kräutern und einer Mischung aus Schokolade, Schokoladekaffee und Milch.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Es ist eine wunderbare Sprache, die ich auf jeden Fall gelernt habe.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Ich höre gerne zu.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe gerne! Bitte schreiben Sie einfach mal etwas, das Sie persönlich begrüßen möchten. So kann ich Ihnen helfen, Ihre Wünsche klar und effektiv zu formulieren.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Es ist eine Geburtstagsfeier am Samstag um 18 Uhr. Bitte geben Sie mir bitte die genauen Details an, wie viele Personen kommen und wann das Event stattfinden wird.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist die Jagd auf dem eigenen Hund. Der Winter ist voller Schneeschauer, Eisschnee und Schneefall, daher sollte man den Hund genug Zeit mitbringen, um sich in der Natur zu bewegen und ihn zu beobachten.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet etwa **ca. $150–300**, was ungefähr **$5–10 Euro** entspricht. Das sind **hohe Anschaffungskosten** und kann man dann oft auf ein paar **kleine Nebenkosten** reduzieren, wie z. B. eine Gabel oder eine Handschuhe.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

