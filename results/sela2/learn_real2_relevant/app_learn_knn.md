# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T18:42:06Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
  **App** (sela-2, sela_chat): Hello! How can I help you today?

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well. I've been reading some of the latest news and the headlines have always made me feel better. I also got a call from a friend about a potential job offer they're interested in.

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): I'm glad you found my previous response helpful. If you have any more questions or need further assistance, feel free to ask!

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Goodbye! I'm sorry, but I can't go now.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): My name is Sela, and I'm a compact language model trained from scratch by the ENGRAMM project. I run locally on your device, and our conversation stays here.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I'm Sela, ENGRAMM's own small language model. I can chat, explain things, and rewrite or summarise text.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help you with a variety of things, including but not limited to:

- Analyzing data and trends
- Interpreting statistical concepts
- Creating effective marketing strategies
- Understanding business operations and decision-making
- Evaluating and improving existing products or services
- Developing new products or services
- Providing guidance on data analysis and interpretation
- Offering advice on data visualization and communication
- Assisting with project management and organizational development
- Helping with specific business or technical issues

Feel free to ask me any questions you have about your data, or I'll do my best to provide accurate and helpful advice.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, […] have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Write down your goals and deadlines
2. Set up a meeting place that is comfortable
3. Stay away from distractions such as phones, emails, and TVs
4. Take breaks when needed
5. Make sure to have a plan for how you will handle tasks at home
6.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): The process of boiling an egg is quite simple. You can boil the egg by adding water to the boiling point of the egg and then turning it on its side with a fork or spoon. When you see the yolk forming, the egg is ready for cooking.

To boil the yolk, simply add 1 teaspoon of salt to the boiling water.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a program that can infect your computer or other devices, and then replicate itself to make copies of itself. It's essentially a way for the computer to try to spread itself around and take over your system.

Viruses can be simple, like an executable file, or they can be more complex, like a malicious software program.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hello, I'm so sorry to hear that you've been having trouble with your plants. We all need help with our gardens and potted plants, but if this is the first time you've had a problem, I'd like to know more about it. Is there anything specific going on in your garden that's causing you stress?

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Cherry
2. Sweet Potatoes
3. Garlic
4. Blackberries

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): We can use the terms "weather" and "climate" interchangeably, but there are some differences. Weather is a general term that refers to a state of weather conditions at any given time. Climate, on the other hand, is the specific set of conditions that characterize a particular region or area over a longer period.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): As autumn leaves fall,
They dance in golden light,
And whisper secrets to the wind,
The earth is still and quiet,
Yet something has changed,
And I am left with a sense of longing.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some ways to make your password more secure:
1. Use strong passwords.
2. Consider using a passphrase.
3. Avoid storing sensitive information like phone numbers, addresses, or financial details in the same place where it's supposed to be stored.
4. Use a unique and memorable password for each account.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): The name could be "Write for the Library."

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): Begin by finding a suitable spot in the gym where you can easily move. It is also important to select a spot that has good lighting and doesn't obstruct your view of the workout area.
Explain to your friend how to use the plan below:
1. Start with 10-15 minutes of low-intensity exercise (e.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): For a weekend camping trip, you'll want to pack layers of clothing, waterproof gear, and an emergency shelter. Here's a general breakdown of what you can bring:

Clothing:

- Sturdy hiking shoes (e.g., sandals, boots)
- Hiking pants or shorts for cooler evenings
- Warm socks and gloves for colder nights
- Socks and underwear for hot weather
- Shorts and swimsuits for warmer evenings
- Waterproof jacket or sweater for cooler mornings
- Shelter materials (e.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering, and mysterious expanse that stretches out before us like a canvas of shimmering blue and white, covering an incredible array of marine life, from tiny plankton to colossal fish.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): When you decline an invitation to a party, it's essential to be respectful and considerate of others' feelings. Here are some tips:

1. **Be clear about your reason**: If you're attending the party for work or other personal reasons, explain why you're not available. For example, "I'm attending a conference" or "I'm taking a break from my schedule."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat): A more polite version of "Send me the report now" is: "Send me the report now." This change makes the sentence sound more professional and formal, which is suitable for an academic or technical context. The word "now" also helps to avoid the awkward phrase "now," which is often used to indicate the end of a sentence.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): A more straightforward way to express this idea is: "Public transportation improves urban congestion."

Alternatively, you could rephrase it to: "Public transportation reduces urban congestion." This version is concise and gets straight to the point, while also using more active language.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct phrase should be "She don't like going to school on mondays." The error is in the apostrophe. In this case, the apostrophe is incorrectly used. To fix this issue, remove the apostrophe from "she don't" and replace it with the plural form of "she".

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

This sentence in the past tense is describing a sequence of actions, where you're following someone's steps. The verb "walk" is in the present perfect form (perfect tense), which means that the action happened in the past. In this case, it's hard to say exactly how long you've been walking, but the past tense suggests that you're now standing in front of the station, shopping for a ticket.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Come on down to our shop and discover the real deal. We're closing early so you can get your hands on some amazing bargains! Good luck with your purchase."

I made this sound more exciting by using a more descriptive phrase, "discover the real deal," which creates a sense of excitement and discovery.

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): How many o'clock is the train to leave?

Answer: eight o'clock

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Acknowledging the inconvenience of this unexpected delay is a common practice in many professional settings. In this instance, I will apologize for any inconvenience this may cause and provide a solution for your discomfort tomorrow morning.

I would like to politely excuse you for any inconvenience this may cause.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): A more concise version of the sentence could be: "Due to rain, we made a decision to stay indoors." 

This revised sentence conveys the same information in fewer words while using more formal language. It also uses a more direct and assertive tone, which is suitable for writing about weather conditions.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): Here's a rewritten version of the text:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee."

I made a few changes to improve clarity and grammar.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): The story of Tom is a classic example of an anecdote that captures the essence of a musical experience. The story follows Tom, who was once a passionate musician, but after spending his childhood playing his guitar, he became increasingly self-conscious and self-conscious about his music. Eventually, he began to develop a popular song in his hometown called "The Starry Night."

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The email effectively conveys the project's progression and progress. To clarify, Martha mentioned bringing "progress notes" for the website launch, but Anna also noted that they plan to finalize the website by Thursday at 2 p.m. This information is crucial for coordinating the next steps on the website.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Here's a brief summary of the key points:

Recycling transforms used materials into new products, saves raw materials and energy, and reduces waste in landfills. Sorting waste correctly at home makes recycling much more effective.

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
  **App** (sela-2, sela_chat): Cities to consider are: Milan, Rome, Florence, Venice, and Rome.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): The Italian food scene is quite diverse, with many different types of cuisine. Try:
- **Italian pizza**: Pizza is a classic, but also delicious with unique toppings like tomatoes, cheese, and olives.
- **Cacio e pepe**: A sweet potato dish with spicy peppers and eggs.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here's a simple birthday card idea for your mother:

**What you should include:**  
- A photo of her in a happy mood (e.g., with a smile, shouldered hand, or admire)  
- A heartfelt message about her favorite activities, hobbies, or memories she'd cherish  
- A special note from her favorite book, music, or TV show (optional)  

**Tips for writing the card:**  
1.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version of the birthday card idea:

**What you should include:**  
- A photo of your mother in a happy mood (e.g., with a smile, shouldered hand, or admire)  
- A message about her favorite activities, hobbies, or memories she'd cherish  
- A special note from her favorite book, music, or TV show (optional)  

**Tips for writing the card:**  
1.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): It is normal to feel stressed sometimes, but it's important to remember that stress is not a disease. Stress can be helpful in certain situations, such as when you need a break or to relax during difficult times. However, chronic stress can have negative effects on your mental and physical health, so it's essential to take care of yourself first.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): To relax this evening, try taking a few deep breaths and going for a walk. You could also try practicing some gentle stretches or meditation exercises to calm your mind. If you're feeling overwhelmed, you might consider setting up a relaxing bedtime routine, such as reading a book or listening to calming music.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The watering schedule for beginners will depend on a few factors, including how big your house is, the weather, and what your child is doing. In general, you should water your houseplant about once every 2 weeks. This is because it's sensitive to drought.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): It's important to have a regular routine, so you can stick to it. Try setting aside 10-15 minutes each day to read. It could be as simple as reading an article in your morning or evening, or doing some research on a topic. You can also try taking a short walk or jogging around the block to get some fresh air and exercise.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found this useful. If you have any other questions or need further assistance, feel free to ask.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (sela-2, sela_chat): Here's a simple recipe for a sandwich:

Ingredients:
- 2 slices of bread (about 1/2 cup)
- 2 cups of all-purpose flour
- 1 teaspoon salt
- 1 tablespoon sugar
- 1 egg
- 1 slice of whole wheat bread (about 1/4 cup)
- 2 teaspoons active dry yeast
- 1 teaspoon salt
- 1 cup cold unsalted butter, softened (about 1/3 cup)
- 1 large egg
- 1 cup mayonnaise or olive oil
- 1 teaspoon black pepper
- Salt and pepper to taste

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
  **App** (sela-2, sela_chat): Ich bin Sela, das eigene kleine Sprachmodell von ENGRAMM. Ich kann mich unterhalten, Dinge erklären und Texte umschreiben oder zusammenfassen.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela. Ich bin ein kleines Sprachmodell aus dem ENGRAMM-Projekt. Ein Mensch bin ich nicht, aber ich helfe gern.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich kann dir helfen, indem ich dir:  
1. **Anwendungen oder Projekte** aufliste, die du dir vorstellen kannst.  
2. **Strategie oder Planung** für eine Umsetzung deines Projekts oder einen konkreten Projektplan entwickle.  
3. **Problemlösung** oder Tipps zu Ressourcen und Zeit finden.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Morgens frühstücken**: Mit einer Tasse Kaffee oder Tee können Sie die Melatoninproduktion und den Schlaf fördern.
2. **Einatmen**: Der Stress des Tages wird reduziert, indem Sie den Atem langsam in den Körper einlassen.
3. **Abends schlafen**: Vor dem Schlafengehen ist es ratsam, eine Stunde Entspannung zu üben, z.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist die Energie, die durch die Bewegung von elektrischen Gleichmolekülen (z. B. Wasserstoff oder Sauerstoff) erzeugt wird. Es gibt zwei Arten von Strom: **abstrakte** und **geometrische**.

---

### **abstrakte Stromquelle**
Wenn ein Stoff elektrische Kräfte aufnimmt und dabei seine Position ändert, wird er als **abstraktes Strom** bezeichnet.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): Hallo! Ich bin heute um 11 Uhr komme und freue mich darauf, mit Ihnen zu sprechen. Willkommen!   

Ich habe schon eine Tasse Kaffee und einen kleinen Kuchen für Sie zusammengestellt. Sollten Sie weitere Fragen haben oder weitere Informationen benötigen, stehe ich gerne zur Verfügung.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): Die vier Gemüsesorten, die im Herbst geerntet werden, sind:

1. Erdbeeren  
2. Beeren  
3. Carrot  
4. Grünkohl

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Um Nudeln richtig zu kochen, ist es wichtig, den Teig vorsichtig zu formen und ihn nicht zu zuckermäßig. Die richtige Form hängt vom Herbst ab und der Temperatur des Teiges ab. Im Sommer wird die Nudel in eine feine, rechteckige Form gebracht, die darauf besteht, dass sich ein gerolltes Stückchen darunter befindet.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist die **Beziehung zwischen Wasser und Boden** oder die **Verdunstung**, bei der ein Fließgewässer **wasserabfließt**. Der Begriff „Fluss“ wird richtig verwendet, um das gesamte Gewässer zu bezeichnen. 

### **Warum ist der Unterschied wichtig?**  
Ein **See** ist kein Wasserfluss.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter in der Dunkelheit**  

Der Schnee wirft goldene Tropfen aus den Wäldern,  
Ein unsterbliches Licht, das die Nacht neu kühlt.  
Die Bäume, ein hässliches Meer aus Blau und Gold,  
Die Wipfel von Felsen, von Wolken umrahmt,  
Drei endlose Horizonte, die nur durch eine Kälte bluten.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, ist es sinnvoll, die Beleuchtung und den Heizverbrauch überflüssig zu machen. Dies kann durch eine zentrale Beleuchtung oder mit LED-Lampen erreicht werden. Menschliche Aktivitäten wie Rutschen, Radfahren oder Sport sollten vermieden werden. Ein gutes Beispiel für einen effektiven Ansatz ist das Verwenden von LED-Lampen zum Beleuchtungssystem.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): **Antwort:**  
Klar! Für einen Vorstellungsgespräch sollte der **Name des Unternehmens** (z. B. "Company Name" oder "Team") und die **Position** (z. B. Teamleiter, Projektleiter, Chef) bekannt sein.  

**Beispiel:**  
- Der Nutzer ist **Sam**, der mit einem Team von Mitarbeitern arbeitet.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat, 2 Versuche): **Gib mir sofort die Unterlagen.**  
(Hinweis: Falls der Nutzer eine konkrete Liste braucht, z. B. ein Ausweis oder einen Tipp, kann ich diese entsprechend umsetzen.)

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Das Problem ist, dass die Aussage „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen“ in der Praxis häufig als falsch interpretiert wird. Die Ursache liegt darin, dass es sich um ein **persönliches** Ergebnis handelt (z. B. durch einen natürlichen oder natürlichen Ablauf), nicht um eine systematische Bewertung des Films.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Fokus auf das Problem (Wetter) zu legen.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): Der Satz kann in der Vergangenheit geschrieben werden:  
„Ich gehe in den Park und lese ein Buch.“  

### Erklärung:  
- „In den Park“ ist ein direkter Zusammenhang zwischen dem Verben „lauschen“ (denn, dass ich dort lebe), und dem verbalen Objekt („das Buch“).

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): Das förmliche: **"Hey, kann morgen leider nicht, sorry!"**

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): **„Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt eine typische Zugvögel-Besuch in Südamerika. Es handelt sich um einen **dramatischen Wanderweg**, der über Jahrtausende von Jahren anhält, wo die Vögel in unterschiedlichen Lebensräumen ihre Nahrung finden – von den Küstenregionen bis hin zu subtropischen Gebieten mit milderen Klimazonen.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): **Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): Die Stadt baut einen neuen Radweg entlang des Flusses. Der Bau beginnt im März und dauert etwa acht Monate. 

**Erklärung der Komponenten:**  
1. **Fluss:** Der Fluss ist ein wesentlicher Bestandteil des Projekts, da er die Innenstadt von Ottawa umrundet und den Verkehr zwischen Arbeit und Freizeit reguliert.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Goethe schrieb das Werk "Der Sturm", in dem er die Geschichte eines Menschen erzählt, der eine Reise durch die Welt unternimmt. Die Handlung des Buches findet im 19. Jahrhundert statt, und es ist die erste Bearbeitung von Goethe's berühmten Roman.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Nähe des heutigen Stadtteils Leinfelden, die er von seinem Ursprung abgetrennt und dann kommend durch die Stadt verläuft. 

Die Stadtteile Bussum und Leinfelden liegen im Bereich der Rheinebene, wo er sich von der Nahe hin bis zum Meer erstreckte.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik im Jahr 1921, als er eine Entdeckung machte, die das Verständnis des Universums revolutionierte. Diese Entdeckung war die Erklärung für die unendlich großen Zahlen und ihre Bedeutung in der Quantenmechanik. Die Entdeckung führte zu einem grundlegenden Verständnis von Raum und Zeit, was einen tiefen Einschnitt in der Geschichte der Wissenschaft bedeutete.

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
  **App** (sela-2, sela_chat): Hier ist ein Beispiel für einen Kuchen, der am Wochenende backen kann:

**Zutaten**:  
- 200 g Mehl  
- 1 TL Salz  
- 1 EL Zucker  
- 150 g Zuckerrüben  
- 500 g Backpulver (Waschmittel)  
- 100 g Milch  
- 250 ml lauwarmes Wasser  
- 1 Liter lauwarme Milch  
- 50 g Schokolade (optional)  

**Zubereitung**:  
1.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der Kuchen mit dem Mehl, Salz und Zucker. Er eignet sich perfekt für eine einfache Backaktion oder für kleine Kinder. Der Teig wird wie gewohnt in einer Schüssel verquirlen und anschließend mit einem Stück Schokolade bestreut.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Du kannst auch einen Kuchen mit Milch und Schokolade backen, der sich dann wie ein guter Backofen eignet.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Wie kann ich Ihnen helfen?
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Ich versuche, Ihre Wortschatz zu verbessern, indem ich Wörter kürze, präzisere Formulierungen anbiete und grammatikalische Fehler vermeide. Hier sind einige Tipps:

1. **Strukturieren Sie Ihre Worte**: Teile Ihre Rede in klare Absätze mit einem Überschriftenverzeichnis (z.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ja! Ich helfe dir gerne dabei. Bitte füge mir bitte den Text, den du geschrieben hast oder eine kurze Beschreibung deiner Anfrage ein. Ich werde dir dann die notwendigen Informationen anbieten.

Falls du unsicher bist, wie ich dir helfen soll, können wir auch gemeinsam mit einem Kollegen arbeiten, der deine Schreibweise überprüft hat.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Das ist eine wunderbare Gelegenheit! Es ist auch eine gute Möglichkeit, sich gemeinsam mit Freunden und Familie zu treffen. 

Falls du Fragen hast oder weitere Details möchtest, kannst du einfach mal helfen!

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist ein Kuchen und ein Käsekuchen. Der Kuchen kann auch als „Korn und Sahne“ bezeichnet werden, da er mit Backpapier hergestellt wird, das in einer kühlen Umgebung erwärmt wird. Der Käsekuchen kann auch als „Süßes Brot“ oder „Stämmchen-Liebhaber“ bezeichnet werden, da er eine einfache Alternative zu Kuchen ist.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das ungefähr kostet ein paar Euro. Das Geld kann durch die Raten des Verbrauchers, den Preis der Kuchen und den Verkaufspreis in einer Saison, sowie von einigen Gaskosten kommen.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Pinguine fliegen nur mit Hilfe des Fisches, dem Pinguin [1].

