# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-19T18:53:08Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

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
  **App** (sela-2, sela_chat): Hi! Was you wondering about me?

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
  **App** (sela-2, sela_chat): Good day! How can I assist you today?

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Martha is sorry for the inconvenience. Goodbye!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): I'm a native Ottawa resident who lives in the city of Ottawa.

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
  **App** (sela-2, sela_chat): I'm here to help you learn new skills and make your life more enjoyable. Whether you're looking for advice on how to become a better communicator, how to improve your creative writing skills, or ways to increase productivity, I'm here to assist. Please share the text you'd like me to review, and let me know what specific areas you'd like me to focus on (e.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, […] have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Get a good night's sleep each night.
2. Keep a consistent routine for staying organized and focused.
3. Take breaks when you need them to recharge your energy levels.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): This depends on the type of egg you're using. For a hard-boiled egg, use water to boil the yolk until it's soft (but still slightly firm). This will take at least 2 minutes. For a softer egg, add a little water and let it simmer for 20-30 minutes.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is like a tiny, invisible piece of software that can delete files, change settings, or even infect computers. It's usually made up of code (like programs or instructions), but it can also be made up of something else, like viruses or bacteria. Viruses are often spread through email attachments, social media posts, or online games.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hey there! Can you help me water my plants next week? It's really important for me to keep them happy and healthy. If you're having any trouble, don't hesitate to reach out! 

Thanks so much for your help!

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Watermelon
2. Brussels sprouts
3. Cucumbers
4. Cherries

The user also mentioned that the user has a strong immune system and is active in their community.

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Climate and weather are two different things. Weather is short for "weather conditions," while climate is short for "climate conditions." Weather refers to the state of the atmosphere, whereas climate is the actual state of the atmosphere. Climate can vary from place to place, but it's generally considered to be stable.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): The fall leaves are a symphony of colors,  
a soft dance of golden light and silver gleam.  
As the days lengthen and the night cools,  
the autumn air is filled with the scent of sweet earth.  

The trees, like silent witnesses, sway in silence,  
their branches like stars on the wind's sighing sigh.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some tips to make your password more secure:

1. Use a strong, unique password.
2. Avoid sharing passwords with anyone.
3. Consider using a salted password or a hash table.
4. Don't use something you don't know well (e.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): Martha's Coffee Shop

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): A 20-minute workout without equipment requires a combination of proper technique, healthy eating habits, and a strategic plan. Here's a simple plan for a 20-minute workout without equipment:

Day 1: 
Start with light cardio exercises like jumping jacks or jogging. Use a stationary bike or elliptical trainer to get your heart rate up.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (sela-2, sela_chat): For a weekend camping trip, you'll want to pack light and comfortable clothing. For a weekend trip, I would recommend packing:
- Comfortable hiking pants or shorts for the long days of camping (can be found at campgrounds or online stores)
- Tent or tents if needed
- Light footwear for walking and jogging
- Waterproof jacket or poncho for cooler mornings and evenings
- A portable charger for your phone or other devices
- Snacks and drinks for energy throughout the day
- A first aid kit with essentials like bandages, antiseptic wipes, pain relievers, and any medications you may need.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, dark expanse that stretches across the Pacific Ocean, a mysterious and enchanting realm where towering waves crash against the surface like giant rocks. The ocean's surface is covered in a layer of tiny, iridescent particles called phytoplankton that float among the blue-green hues of the surrounding water.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Here's how you can politely decline an invitation to a party:

1. **Be polite**: Use phrases like "I'm really sorry, I don't want to attend" or "I appreciate your interest in the party, but I think it would be too late." Avoid making excuses or justifying yourself.

### en27 (rewrite) – echo
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (sela-2, sela_chat, 3 Versuche): Send me the report now.

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (sela-2, sela_chat): Here's a simpler version: "Public transportation reduces urban congestion." 

Or, if you'd like to make it even shorter: "Public transportation helps reduce urban congestion." 

Note that I removed the phrase "the utilisation of public transportation" because it was already implied by the context and was not necessary for understanding the sentence.

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct edit would be: "She don't like going to school on Mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

The past tense is used when describing a completed action. For example, "I walk to the station and buy a ticket." Here, the verb "walked" is in the past tense.

Using the past tense in this sentence helps to convey that you are completing the actions described by the verb.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Welcome to our cozy shakshuka shop, where we'll be featuring some delicious treats from around the world! Come on in and taste our creations, and we'll make sure you find just the perfect piece to start your day with. We're selling everything from fresh shakshuka to seasonal desserts, so don't forget to stop by and pick up a few of our favorites!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): To turn this into a question: "The train leaves at eight o'clock."

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Martha,

I'm sorry to hear that you're unable to make it tomorrow. I'd like to offer some support and assistance in helping you plan your trip. Could you please ensure that all necessary travel arrangements are made and send me the final details for your flight? 

If there's anything specific you'd like to know or any questions about your itinerary, feel free to ask.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain outside, we chose to stay inside." 

I made a few changes to make the sentence more concise and grammatically correct. I removed the phrase "Due to," which can sometimes make sentences feel wordy or redundant. I also changed "the fact that" to "heavy rain," which is a more idiomatic way to express the idea of heavy rain.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library will be closed on Monday for repairs to the heating system, and reopen on Tuesday at 9 a.m. Books due on Monday can be returned on Tuesday without a late fee.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat, 2 Versuche): The user's summary effectively conveys the key points:

- **Tom's first mistake**: The fingers hurt, and the chords sounded wrong.
- **His second mistake**: He practised for fifteen minutes every day. After three months, he could play his favorite song for friends.
- **His third mistake**: Despite practicing for three months, he could not play his favourite song for his friends.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The email effectively conveys the project's upcoming meeting and plans, while being concise and clear. Here are some minor adjustments to further improve clarity:

- Changed "summarize this email" to "summarize this email" for a more formal tone.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): "Recycling turns used materials like paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."

I hope this helps!

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
  **App** (sela-2, sela_chat): Cities to visit first: Florence, Rome, Venice, and Milan.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): You should try pasta, pizza, and gelato.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Got it — I'll call you Sam from now on.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Sure! Here's a simple birthday card for your mother:

"Happy birthday, my dear. I'm so sorry you missed the party. Please know that I love you and will always remember you. I hope all the best in life!"

You can customize this to fit your personal style or send it to me directly.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Happy birthday, my dear. I hope all the best in life! Please know that I love you and will always remember you. I hope all the best in life!

I made a slight change to the title to make it more concise, and also changed "happy" to "hopeful" since the birthday is for your mother.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): Sam is a very nice person and helps me feel better. It's not uncommon for people to be stressed out sometimes, but I'm here to help. Here are some ways you can make things feel better:

1. **Take a break**: If you're feeling overwhelmed, try taking a short walk or talking to someone else about what's making you feel stressed.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): Relaxing is a great way to unwind. Here are some suggestions:

1. **Take a warm bath**: Baths can help release tension and reduce stress. You can try using steam, hot water, or even a relaxing soak in a bathtub.
2. **Journaling**: Writing down your thoughts and feelings can help you process them and release pent-up emotions.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The water should be at least once a day.

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
  **App** (sela-2, sela_chat): You're welcome! I'm glad you found that useful.

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
- Optional: lettuce, tomato, cucumber, or spinach
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
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Bitte gib mir einfach deinen Namen, den du genannt hast, und schlage mir vor, ob du Unterstützung benötigst. Dann kannst du mir die Frage stellen, ob du einen Nutzer (Name) oder ein Problem hast, und ich werde mich umgehend an dich wenden.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Hormon-Regulation**  
   - Ein hoher Schlafmangel kann körperliche und geistige Erschöpfung verursachen. Vermeiden Sie nächtliche Bettruhe, um den Körper zu regen. Schlaf ist ein natürlicher Energiespeicher, aber durch künstliche Schlafsäcke oder Lichtkonsolen können Sie ihn nach Bedarf abbauen.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist Wärme, die durch das Bewegung von Gasen oder Strahlen entsteht.  
- Strom fließt in einem kontinuierlichen Weg durch ein System (z. B. eine Leitung, ein Netz) und kann über lange Distanzen geleitet werden.  
- Er leitet Energie in elektrische Energie um und macht sie verfügbar.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): **[Name]:**  
*[Nachname]:**  
*[Telefonnummer]:*  

**[E-Mail-Adresse]:**  
*[Website]:*  

*(Namen, Adresse und Kontaktdaten)*  
[Präzise Nachricht mit Platzhalter: [Datum] und Beschreibung)*  

*(Kurzes Schreiben, keine zusätzliche Anhänge)*  

**[Vorgehensweise]:**  
1.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): **1. Tomaten (z. B. Tomato, Chili)**  
**2. Mangos (z. B. Cherry, Blackberry, Jackfruit)**  
**3. Gurken (z. B. Garlic, Oregano, Cucumber)**  

Der Nutzer bezieht sich auf **Kokosorten**, die im Herbst geerntet werden.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln werden in einer Schüssel mit Mehl, Salz und Wasser erwärmt. Sie sollten nicht zu dünn sein, sondern sie sollte gut kleben und kleben lassen. Die Nudel müssen mindestens zwei Stunden im Kühlschrank aufbewahrt werden.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See ist **nicht eindeutig** in der Definition.  

1. **Fluss**:  
   Ein Fluss ist ein künstlicher Fluss, der durch die Erdoberfläche fließt. Er ist nicht flüchtig (wie ein See), sondern er fließt in Richtung des Flusses oder durch den Fluss selbst.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter:**  
Der Schnee, der die Sterne vergisst,  
Ein Schnee, der sich im Winter neu baut.  
Die Vögel flüstern in den Bäumen,  
Doch wie lange bleibt der Wind?  

Er spielt im Winter auf den Holzboden,  
Seine Stimme ist ein Lied aus Schneesturm und Regen.

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
*Hinweis: Das höfliche „Gib mir sofort“ ist in der kanadischen Sprache üblich, und es kann bei Bedarf auch als „Wenn du mich fragst, bitte gib mir den Inhalt.“ interpretiert werden.*  

**Präzisere Variante:**  
„Ich bin bereit, alle Dokumente zu erhalten.“

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“  
(Beide Sätze sind korrekt, jedoch differiert in ihrer Struktur und dem Stil. „Ich habe ins Kino gegangen“ ist idiomatisch und deutet auf einen vorherigen Besuch hin.)

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Einfügung von „aufgrund“**: Der Begriff „aufgrund“ steht im Kontext, der den Hintergrund beschreibt.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): **In den Park:**  
*Ich gehe in den Park und lese ein Buch. Es ist bereits Morgen.*  

**Erläuterung des Satzes:**  
1. ** Vergangenheit:** Der Nutzer *Sam* lebte seit seinem 12. Geburtstag in Ottawa. Sein Lieblingsspielzeug war eine Taschenlampe.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formulier:** „Hey, kann morgen leider nicht, sorry!“  

**Hinweis:** Die Formulierung ist inhaltlich neutral und betont den Nutzer als Person. Sie ist an einen positiven Kontext gebunden (z. B. Anerkennung, Dank).

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat, 3 Versuche): **Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig.**  
Die Aussage lautet: **„Fahrradfahren ist gut für die Gesundheit.““

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“  

**Erklärung:**  
- **„Die Raum belegt ist“ → „der Raum belegt ist“**: Das Verb „beimessen“ ist im Deutschen ein Synonym für „ belegen“.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Im Text geht es um die Zugvögel in der Region, die vor dem Herbst ihre Wanderungen unternehmen. Es wird betont, dass die Vögel aufgrund der warmen Jahreszeiten (Frühling) in wärmeren Gebieten brüten. Die Antwort auf das Fragezeichen bezieht sich auf die Flugweise des Nutzers und Murphy, die jeweils nach ihrer Saison fliegen.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): Lisa war zunächst in Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin und lernte jeden Tag eine Bahn ohne Pause. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.  

Lisa lebte in Ottawa, wohnt aber in Ottawa und arbeitet als Lehrerin.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Die Stadt baut einen neuen Radweg entlang des Flusses.**  
Der Bau beginnt im März und dauert etwa acht Monate.  

---  
*Hinweis: Das Wort „Stadt“ ist in Kanada nicht obligatorisch, da es nur für Städte gilt. Für ein spezifisches Beispiel könnte man die Stadt Ottawa als **Stadt der Pendler** betrachten.*

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded)
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat): Meine Quellen sagen dazu nichts.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein fließt in der Region Ottawa in den Westen mündet.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik im Jahr 1921, gemeinsam mit seinem Freund Max Born und dem Mathematiker Bernhard Riemann. Einem breiten Publikum wurde Einstein vor allem durch sein Buch „Das große Universum“ bekannt, in dem er die Grundlagen der Relativitätstheorie beschreibt und dabei seine These zur Gravitationskonstante (Gamma) formulierte.

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
  **App** (sela-2, sela_chat, 2 Versuche): Ich helfe dir gerne bei der Backung!  Falls du einen Kuchen backen möchtest, kannst du mir bitte den Namen und die Position des Kuchens mitteilen. Also:
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der "Bakery-Tee" aus dem kanadischen Staat Alberta. Er ist nicht teuer, aber für einen etwas anspruchsvollen Geschmack eignet sich der "Bakery-Tee" gut. Er wird oft in einem Topf oder einer kleinen Pfanne gebacken und serviert mit Butter oder Sauce.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Natürlich! Ich freue mich, dass du dir die Möglichkeit genommen hast, deinen Kuchen zu backen. Falls du Fragen hast oder unsicher bist, kannst du gerne fragen – ich bin hier, um zu helfen.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Der Nutzer ist Mia, ein kleiner Offline-Assistent aus Ottawa.
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um meinen Wortschatz zu verbessern, kann ich mehrere Methoden anwenden. Zunächst: **Präzise Wörter und Beispiele** verwenden, um das richtige Wort für jeden Satz zu finden. Beispiel: "Ich bin glücklich, weil ich so viel Zeit mit meinem Hund verbringen konnte."  
- Vermeide umgangssprachliche Formulierungen wie "hat" oder "wird".

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe dir gerne! Schreib mir doch bitte, was du möchtest – falls es etwas Besonderes ist oder du unsicher bist, wo ich anfangen soll.  

**Beispiel:**  
**Hinweis:** Falls du nicht weißt, ob du *ein* Einladung schreiben darfst, sag einfach nur „Ja, ich kann eine schreiben.“
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Natürlich! Ich helfe gerne bei der Planung und dem Schreiben. Für den Samstag sind die Termine:  

1. **15 Uhr**: Die Geburtstagsfeier beginnt um 18 Uhr.  
2. **19 Uhr**: Es ist ein Tag für Freude und Lachen, aber es ist auch eine Zeit für Überraschungen.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist der **Trailsport**, insbesondere im Herbst. Es gibt viele Möglichkeiten:
  - **Golf**: Der Winter ist ein gutes Wetter für das Erlegen von Hindernissen, wie z. B. Schneeketten, Klettergeräusche oder Schneeböen.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter kostet **etwa $50-$100**. Ein Anstieg auf $200-$300 kann allerdings mit einem langen und warmen Alltag beginnen. Hier sind einige Gründe:
  - Der Preis hängt von der Strecke ab (z. B. Eis, Schneepausen, Schneeböen), aber auch von der Wetterbedingungen (z.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Ja, Pinguine können fliegen [1].

