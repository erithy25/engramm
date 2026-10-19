# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T10:24:28Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
Schutzregeln: 2 Antworten neu erzeugt, 4 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hi!

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well. I was just talking to someone and they asked me how I was. They said I had a good attitude and that my friends loved me, but there was no positive response from them.

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help you today?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): It was great to help! If you have any more questions or need further assistance, feel free to ask.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): I'd like to thank you for your prompt response. I'll make sure to use the correct punctuation when referring to you. Let me know if you have any further questions!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I've been painting for about 10 years now, and my work has been exhibited all over the world. I love being able to express myself through art and share my passion with others. My favorite thing about my life is the beautiful landscapes that surround me – mountains, forests, and cities.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat, 2 Versuche): Elsie

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of creative endeavors, from writing stories to creating music and animations. I can assist with various aspects such as character development, plot structure, dialogue writing, storyboarding, and even digital editing. If you're looking for a unique and captivating project, I can help spark ideas, provide feedback on your work, and offer suggestions for improving it.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Get a good night's sleep: Getting enough sleep is important for cognitive function and focus, so try to get at least 7-8 hours of sleep each night.
2. Set realistic goals: Break down larger tasks into smaller, manageable chunks. This will help you stay motivated and focused.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): Steam the egg in a large pot or pan over medium heat. Add enough water to cover the yolk and keep it from boiling. Once the egg is soft, add a splash of water with the egg yolk and cook for about 1-2 minutes, stirring occasionally.

Remove the egg from the heat.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible threat that spreads through the internet. It's like a big virus that can infect your computer or any other device you use to make stuff happen! Computer viruses are like tiny bugs that can copy themselves and send messages to other computers, pretending to be someone else.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hello! Please give them a little help with their watering. You'll be happy you have such a great friend around.

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Watermelon
2. oranges
3. apples
4. lemons
5. kiwis
6. bell peppers

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two related but distinct concepts. Climate refers to the long-term average weather patterns that characterize a region, while weather is a short-term condition that can vary depending on the location and time of year.

Climate describes the overall pattern of weather conditions over a specific period, usually lasting from one to several years.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The chill of autumn's breeze,
A slow, sweet serenade,
As the leaves drift down the wind,
And the scent of earth and air,
Wakes within me a sense of peace.

They dance on my skin,
A gentle breeze that carries
A symphony of colors,
Their petals a gentle rustle,
As I feel their soft light,
Waves through my heart,
In the cool night.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, follow these steps:

1. Use a strong, unique password that is at least 8 characters long and includes letters, numbers, and special characters. Avoid using common words like "password," "secret," or "login."
2. Consider using a mix of uppercase and lowercase letters, digits, and special characters to create a secure password.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Elsie is a name for a small coffee shop near the library.

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): Start with a 30-minute walk at the gym or a gentle jog in nature. Then, get into some good form by doing some strength training exercises like squats, lunges, deadlifts, or bench press.

Use your phone to track your progress and reward yourself for reaching milestones.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): You'll need a tent, sleeping bags, and camping stove. You can also pack some clothing, including t-shirts, jeans, sweaters, and hiking boots.

If you're planning on driving to the campsite, you'll need to bring some food, water, and camping gear.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, salty sea with towering peaks and waves that stretch out as far as the eye can see. It's a place where everything is new and unfamiliar, where sunlight filters through the water, and the tides are unpredictable.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. Acknowledge the invitation: Thank the person for inviting you and express gratitude for their time.
2. Show appreciation: Express your appreciation for their invitation, whether by thanking them directly or by making a small gesture like saying "thank you" or "excuse me."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): I'm sorry, but I can't assist with editing or rewriting text. Please feel free to share the text you'd like me to review, and let me know what specific areas you'd like me to focus on.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A simpler version would be: "Public transportation reduces urban congestion." 

Alternatively, you could say: "Public transportation improves urban congestion."

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct version is: "She don't like going to school on mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): Elsie walks to the station and buys a ticket.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Elsie and Murphy have a sale this weekend!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): How do you turn this into a question: "The train leaves at eight o'clock."

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): I am unable to make it tomorrow, I regret that. Please let me know if there is anything I can assist with today.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside."

I made a few changes to make the sentence more concise and grammatically correct. I removed "due to" as it's unnecessary, and changed "it was raining very heavily outside" to "heavy rain outside" to make the sentence more active and engaging.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library is closed on Monday for repairs to the heating system, with books due on Tuesday without a late fee.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): This is a short summary of Tom's story:

Tom started learning the guitar at age three. He began practicing by playing shakshuka, which was his favourite song. After that, he practised for 15 minutes every day, using his fingers to correct the chords. By the end of the first month, he could play his favorite song for friends.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): "Hello team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"

The email contains a brief summary of the project, including the move from Wednesday to Thursday at 2 p.

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
  **App** (sela-2, sela_chat): If you're planning a trip to Italy, I would recommend visiting Rome. It's the capital and the biggest city, and it's easy to get around by train or bus. Plus, you'll have plenty of time to explore the city and its many landmarks.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): Italian food is incredibly diverse, with a wide variety of dishes. You can try some classic Italian dishes like pasta and pizza, as well as more unique ones like spaghetti Bolognese or gelato. Don't forget to try some local specialties like pizza with mozzarella or gelato for a full-bodied experience.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Hanging Flower**: This is a classic and timeless card. Fill it with flowers, balloons, or your mother's favorite colors like red, green, blue, yellow, and orange.
2. **Blank Card with Birthday Emoji**: You could add a blank card with a birthday emoji on the inside.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here are some ideas for a birthday card:

1. **Hanging Flower**: This card is classic and timeless. Fill it with flowers, balloons, or your mother's favorite colors like red, green, blue, yellow, and orange.
2. **Blank Card with Birthday Emoji**: You could add a blank card with a birthday emoji on the inside.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): It sounds like you're feeling stressed. Here are some suggestions to help you manage stress:
1. **Take a few deep breaths**: Try inhaling for a count of four or exhaling for a count of five. This can help calm your mind and body.
2. **Try some relaxation techniques**: Deep breathing exercises, progressive muscle relaxation, or guided imagery can all help you relax.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): You can try a few relaxation techniques to help you unwind. Here are some ideas:
1. **Start with a relaxing activity**: Grab a book, listen to calming music, or watch a soothing movie. You can also try a guided meditation or yoga class if that's something you enjoy.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The water should be changed once a week in the spring and twice a month in the fall.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Start with small, achievable goals. Read a book for 30 minutes at the same time every day, or even just a few times a week. This will help you build momentum and get your brain used to reading.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found something to enjoy. Enjoy reading, and don't hesitate to reach out if you need more advice or tips.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here is a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (about 1 cup)
- 2 slices of cheese (about 1/2 cup)
- 2 cups of tomato sauce
- 2 tablespoons olive oil
- 3/4 teaspoon salt
- 1/2 teaspoon pepper
- 1 tablespoon freshly grated Parmesan cheese
- Optional toppings: sliced ham, lettuce, spinach there you go!

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Wie geht es dir?

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Danke für deine Hilfe!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **App** (sela-2, sela_chat): Tschüss bis bald!

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Ich habe vor Jahren meine Bachelor-Studien abgeschlossen und war seit 2004 für viele Jahre als Assistenzleiter für Online-Marketing tätig.  

Ich arbeite an Projekten wie Social Media Marketing, E-Mail-Marketing oder SEO.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela. Ich bin ein kleiner Offline-Assistent aus Adelaide, South Australia.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir deinen Namen, den du über mich erzählt hast – egal wie klein oder groß es ist. Ich kann dir helfen, deine Angaben zu korrigieren, Vorschläge zu machen, deine Beziehung zu beschreiben, oder einfach nur eine Nachricht schreiben, um dich anzurufen oder dir weiterzuhelfen.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Pausen einplanen**: Plane deinen Tag mit einer festen Schlafzeit und setze ihn in den Tag ein, um die innere Uhr zu synchronisieren.  
2. **Körperliche Aktivität**: Strebe mindestens 30 Minuten tägliche Bewegung wie Spaziergänge oder Yoga.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Licht von einem Objekt entsteht. Es gibt zwei Arten von Strom:  

1. **Regenstrom** (z. B. bei einer kühlen Sonne): Er wird durch Sonnenstrahlung erzeugt.  
2. **Druckstrom** (z.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **[Name]:** Sam  
**[Telefonnummer]:** +61 8 243 3481  
**[E-Mail-Adresse]:** [email@example.com]  

Ich nehme an, du hast bereits am nächsten Tag telefoniert und möchtest mir eine kurze Nachricht über den geplanten Termin geben?

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): Hier sind vier Gemüsesorten, die im Herbst geerntet werden:  
1. **Avocado** (im Frühjahr): Der größte, süße und fruchtbare der vier. Er wird meist frisch gemahlen oder in Salaten hergestellt.  
2. **Mango** (nach dem Fall des Dorns): Ein kleiner, mildes und süßes Grün.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln sollten in einem Topf etwa 3–4 Stunden kochen. Dann lassen sie sich mit einer Gabel zerkleinern. Nach dem Kochen ist das Nudeln sicher und passt gut zu anderen Speisen.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht eindeutig** in der Definition.  

1. **Fluss**: Der Fluss fließt über ein Land, Meer oder eine andere natürliche Wasserquelle (z. B. Flüsse oder Seen).  
   - **Beispiel**: Ein Fluss fließt durch das Herbstland von England nach Deutschland.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter im Adelaide-Stadtzentrum**  

Als Sam die Stadt verlassen,  
sollte er die Bäume rauchen,  
die Bäume wuchsen wie Sterne.  

Die Sonne weckte den Schnee in den Himmel,  
ein Schneeloch, das den Wind zu trösten suchte.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, solltest du einiges tun. Hier sind einige Tipps:  
1. **Bürokratie optimieren:** Teile den Haushalt in kleine, stabile "Bürozellen" (z. B. hinter dem Schreibtisch oder am Fenster) und lass alles nach Bedarf laufen.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Antwort:**  
Es ist wichtig, dass du Fragen stellen kannst, die dir helfen, dich zu verstehen und klar zu kommunizieren. Hier sind einige Punkte, die dir helfen können:  

1. **Name/Tätigkeit**: Schreib mir kurz deinen Namen (z. B. „Sam“), deinen Beruf (z.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): **Formuliere das höflicher: „Gib mir sofort die Unterlagen.“**  

How can I help you?

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Das ist eine gute und klar formulierte Version, aber hier sind einige Anpassungen, um die Fehler zu verbessern:  
- **„Ich habe gestern ins Kino gegangen“** → **„Ich habe heute ins Kino gegangen“**  
  (Erklärung: „Heute“ passt sich besser an das Kontextualisieren der Handlung an.)

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Inhalt (Wetterlage und Absage) klarer zu strukturieren.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **Dadurch wird das Buch zum Gegenstand des Gedankens, das ich in der Vergangenheit (in Zukunft) sehe.**

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** *„Hey, kann morgen leider nicht, sorry!“*  

**Hinweis:** Die Formulierung ist inhaltlich korrekt und grammatikalisch korrekt. Sie wird durch die Verwendung von „Hey“ im Satz geformt.

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Der Nutzer spricht von einer **"gut für die Gesundheit"**-Ebene, bei der Fahrräder nicht nur das Auto belastet, sondern auch den Herzschlag und die Muskeln stärken. Die Gesundheit ist durch Bewegung und gesunde Ernährung in der Stadt oft schneller als im Auto.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

---  
*Das Programm ist nach der offiziellen Zeit (um 21:00) angepasst und enthält noch einige Elemente wie „Ich werde euch nicht die Zeit lassen“, „Ich hoffe auf Unterstützung“ oder „Ich bin bereit, zu sehen, was wir können“.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt die Bewegung von Zugvögeln in Adelaide, deren Züge Tausende Kilometer zurücklegen. Im Frühling sind sie häufig im Norden zu brüten, um genug Nahrung zu finden. 

**Erklärung:**  
- **Zugehörigkeit:** "Im Herbst" ist eine Abkürzung für "im Herbst", was auf die Winterzeit hindeutet.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa begann mit einer Trainerin, die ihre Schwimmtechnik perfektionierte. Als sie die ersten Wochen in Adelaide schwamm, war sie unsicher und nicht sicher, ob der tiefere Wasserstand hilfreich war. Nach einem Sommer entwickelte sie sich zu einem erfolgreichen schwimmer, während sie durch eine ganze Bahn ohne Pause schwamm.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“  

**Erläuterung:**  
- **Satz 1:** „Der neue Radweg ist nicht nur für Pendler, sondern auch für die allgemeine Sicherheit von Autopfern unerlässlich.“

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das berühmte Werk „Der Sturm“ (1789) [1].

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Nähe des **Kleinfeldes** (Rheinland) von Adelaide bis nach Köln, wo er den **Odersee** verlässt. Er mündet dabei in die Weser, die in Richtung Bremen fließt.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis, weil er **„eine ganze Reihe von Dingen“** bekannt machte. Hier sind die wichtigsten Details:  
1. **Seine Entdeckung des Gravitationsgesetzes**: Er zeigte, dass es keine Einsteinschen Gesetze gibt, sondern eine mathematische Formel, die Energie (z.

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
  **App** (sela-2, sela_chat): Ich habe eine passende Kuchenart gefunden! Hier sind die wichtigsten Details:  
1. **Preis**: €15–€30 (am Wochenende).  
2. **Struktur**: Kuchen, Kekse und Marmelade – ideal für kleine Gruppen oder feste Mengen.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der **Bäckereischote** (eine Schokoladenkruste, die in ein Zettel geschrieben ist). Es gibt auch kleine Versionen mit Zucker und Salz.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der **Schokoladenkruste** (ein Schokoladensalat, die in ein Zettel geschrieben ist). Es gibt auch kleine Versionen mit Zucker und Salz.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia, wohne in **Adelaide**.  

**Über die Firma (oder etwas anderes):**  
Murphy ist der CEO.  
*Mit Angaben über den Nutzer:* Name: Mia; wohnt in: Adelaide; Hund: Murphy.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): **Über den Nutzer:**  
Mia, wohne in **Adelaide**.  

**Über die Firma (oder etwas anderes):**  
Murphy ist der CEO.  
*Mit Angaben über den Nutzer:* Name: Mia; wohnt in: Adelaide; Hund: Murphy.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Mia ist eine KI-Assistentin und kann dir helfen, einen Einladungsbrief zu schreiben. Hier sind die Schritte:

1. **Fragen**:
   - **Wer bist du?** (einen Namen oder eine Adresse)
   - **Was möchtest du über mich wissen?** (z.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Ich kann dir helfen, einen Einladungsbrief zu schreiben, um deine Geburtstagspartnerin (oder du) bei der Feier zu begrüßen. Hier sind die Schritte:

1. **Fragen**:
   - **Was ist dein Name?** (einen Namen oder eine Adresse)
   - **Wer bist du?** (eine Person, z.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist der **Kannstreifen** (auch "Kastensack" genannt), bei dem man mit einem Holzkasten, Holzschnitz oder ähnlicher Gegenstände aus Holz richtig herumläuft. Er kann zum Beispiel eine tote Katze oder ein Baumhaus in die Luft lenken, und die Bewegung des Kleinen sorgt dafür, dass er von einer kleinen Strecke zurückgerissen wird.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet ungefähr:
- **Lebensdauer**: 6-12 Monate (in der Regel, aber auch erhielt nach Reparaturkosten wie dem Umschreiben von Kabel oder Teilen)
- **Materialien**: Holz (z. B. Holzschnitz), Baumwolle, Holzstock, Metall oder Kunststoffe.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen! Sie sind in der Regel **niedrig**, aber die Flügel sind sehr robust und können auch **über den Boden springen** [1].

