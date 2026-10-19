# Sela-2 in der App: 100 feste Prompts (ohne Schutzregeln)

Gewichte `sela2-s21lr10.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-18T18:34:45Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 2 von 100 |
| identity_error | 0 von 100 |
| echo | 1 von 100 |
| cut_off | 5 von 100 |
| role_leak | 0 von 100 |
| loop | 1 von 100 |
| empty | 0 von 100 |
| prompts_with_a_problem | 9 von 100 |

Antworten nach Modell: {'engramm': 26, 'sela-2': 91}; nach Art: {'about': 2, 'answer': 4, 'learned': 7, 'sela_chat': 85, 'sela_grounded': 6, 'unknown': 13}.
Schutzregeln: 0 Antworten neu erzeugt, 0 feste Identitätsantworten; 2 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hello! How can I help you today?

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm fine, thank you for asking!

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there, what's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): You're welcome!

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Goodbye!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): My name is Sela. I'm a compact language model trained from scratch by the ENGRAMM project. I run locally on your device, and our conversation stays here.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I'm Sela, ENGRAMM's own small language model. I can chat, explain things, and rewrite or summarise text.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat): I was trained from scratch in the ENGRAMM project, on public text and conversations. I'm Sela, a small language model that runs on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat): I am a machine, and I do not have consciousness or emotions.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can assist with a wide range of topics related to data analysis and interpretation, including:

- Data visualization and presentation
- Statistical analysis and modeling
- Data mining and machine learning
- Understanding statistical concepts and terminology
- Debugging and troubleshooting issues
- Developing and implementing statistical models
- Explaining data trends and patterns
- Creating and presenting effective data visualizations
- Identifying and addressing data quality issues

Please feel free to ask me any questions or provide additional context about your data or research question.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat): I am not sure I have feelings but it is probably possible that my emotions are related to the physical sensations of a feeling or experience.  However, I do not really feel anything.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Stick to your routine
2. Use a planner or app to schedule your work and your daily activities.
3. Make time for yourself, even if it's just 20 minutes each day.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): There are many ways to boil an egg, but the most common method is boiling it in a hot water bath. When you add salt or other ingredients that dissolve into the water, the yolk is usually released from the egg and floats to the top of the bath. This process can be done in a variety of ways:
- Boiling the egg in a hot water bath
- Using a heating pad to heat up the egg
- Using a microwave
- Using a whisk
- Boiling the egg on a paper towel or cloth

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a malicious program that can harm your computer or steal information. It's like a bad actor trying to take over your computer and make it work against you. The virus takes control of the computer, copies itself, and does all the dirty work. Once done, it can cause damage to the computer, steal sensitive data, and even delete important files.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hello, I'm so glad you're here! My name is Emily and I'm a teacher at a local school. I've got some fresh flowers in my classroom that I think would be great for your plants. Let me know how it goes and I'll help you water them too!

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): - Strawberries
- Red peppers
- Cherries
- Bananas

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): Weather is the weather conditions at a specific time in the past. Climate is the average of weather conditions over a period of time.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): As autumn leaves fall, they hold secrets
That the earth will remember forever.
The wind rustles their silken shroud,
A gentle sigh of peace that never sleeps.

The trees stand tall and wide,
And the world is filled with joy and green.
In every leaf, a spark of love blooms,
A tiny flame that shines brighter than all else.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): There are several ways to make your password more secure. The most common is by using a strong and unique password. Use an algorithm that has been reviewed by security experts to ensure that it meets the requirements for the level of security. It's recommended that you always use a mix of uppercase and lowercase letters, numbers, and special characters. 

Another way is to use two-factor authentication (2FA) which requires a second form of verification for each type of account. This can be done by asking your bank or service provider for a code sent to your mobile device.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): The name could be "Little Green Leaf"

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): Begin by assessing your fitness level and prior experience. Work out 3-5 times per week, with breaks in between for rest and recovery. Avoid strenuous activities that may cause injury or burnout.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (engramm, answer): Write a short, friendly message to a neighbour asking them to water your plants next week.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, endless expanse of water that covers nearly one-third of the planet's surface, covering about 2.3% of Earth's land area and 5% of its sea area, but also including more than 90% of the world's oceans.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): Decide the best way to decline a party invitation. It is important that you do so in a polite manner. If you are not certain, you could say something like "I am currently going through my schedule" or "I will not be able to attend this event".

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (engramm, learned): Ah, okay. How's that going?

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (engramm, learned): Oh, The The. It's an English post-punk band. How did you discover them?

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct grammar is: "She don't like going to school on mondays."

### en30 (rewrite) – echo
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): I walk to the station and buy a ticket.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Come on over, give us a shout! Our shop has a sale this weekend! Come on over and buy some of our fresh produce!"

### en32 (rewrite) – cut_off
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): To solve this problem, we need to consider the time interval between the train's departure and arrival. We can start by looking at the given information: the train leaves at eight o'clock and arrives at the station at 8 o'clock.

We can use the fact that the train travels at a constant speed of 'c' miles per hour and that the distance traveled is equal to the time taken for the train to travel that distance. Therefore, the total distance covered by the train in one hour is c times the time it takes for the train to travel that distance.

Since the train leaves at 8 o'clock, we can set up an equation to represent the time it takes for the train to travel that distance: d(c - 8) = 0. This equation represents the time it takes for the train to travel a certain distance.

Now, let's find the value of c, which represents the distance the train covers in one hour. We know that c = 'c - 8', so we can set up the equation as follows: d(c - 8) = 0.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): The problem is that I am not able to make it tomorrow, sorry.

I apologize for any inconvenience this may cause you.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): Here's a revised version of the sentence: "Due to heavy rain, we decided to stay inside the house."

I made a few changes to improve clarity and grammar. First, I replaced "it was raining very heavily" with "heavy rain," which is a more concise and formal way to express the same idea. I also changed "we made the decision to stay inside" to "we decided to stay inside," as it's more idiomatic and natural-sounding in this context. Finally, I added "decided" to make the phrase "stay inside the house" sound more polished and grammatically correct.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): Bees are crucial pollinators, playing a vital role in producing fruits and seeds that support plant growth.

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The text is clear, but it could be improved for better flow and grammar. Here's a revised version:

"The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."

I made a few changes to enhance clarity and readability:

- Changed "will be closed" to "will be closed" to correct the verb tense.
- Removed the phrase "it will reopen" as it's implied by the fact that the library will reopen on Tuesday.
- Changed "Books that are due on Monday can be returned on Tuesday without a late fee" to "Books that are due on Monday can be returned on Tuesday without a late fee" to make the sentence more concise and grammatically correct.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): Your summary is off to a good start. It's clear and concise, and it effectively conveys the main character's frustration with his guitar playing. To make it even more engaging, you could consider adding more details about Tom's past experiences with the guitar or perhaps hint at what specific challenges he faced during his practice sessions. 

Additionally, you may want to explore Tom's personality and motivations for wanting to learn the guitar. What does he hope to achieve through his musical endeavors? Is he trying to become a professional musician, or does he genuinely enjoy playing music? Adding more depth to his personality will help readers connect with him on a deeper level.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol, produce no exhaust gases while driving, and can improve air quality in cities by reducing the amount of pollution. However, charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): Here's a rewritten version of the email:

"Hi team, we're excited to report that our project meeting is set for Wednesday at 2 p.m., and we'll be presenting updates on our website launch plan. We'll also outline the next steps for the website's launch. Thank you for your cooperation and support throughout this process."

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Recycling turns used materials into new products, saves raw materials and energy, reduces waste in landfills, and makes recycling more effective.

### en42 (summarize)
- **Nutzer:** In one sentence, what is this about? "The town council approved a new park on the site of the old car park. The park will have trees, a playground and a small pond. Construction starts in spring and should take about one year."
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that. Nice — The The. It's an English post-punk band. What's your favourite song?

### en43 (grounded)
- **Nutzer:** How long is the Danube?
  **App** (sela-2, sela_grounded): The Danube is length is 2850000 meters [1].

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
  **App** (sela-2, sela_chat): If you want to get a feel for the city, visit Tokyo. It's one of the most modern cities in the world and it's very clean.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): You should try Japanese cuisine! I'm sure you will love it.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Hi Sam, nice to meet you! I'll remember your name.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): I can help you with that! Here is a birthday card for your mother:

**Happy Birthday to my Mother!**

You can write the card in pencil, on paper or cardstock. The card should be 3"x6" and include a signature at the top and a photo of her favorite color and the date she was born. You may also want to add some personal details like her favorite foods, hobbies or music.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Happy Birthday to my Mother!

You can write the card in pencil, on paper or cardstock. The card should be 3"x6" and include a signature at the top and a photo of her favorite color and the date she was born. You may also want to add some personal details like her favorite foods, hobbies or music.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): It's normal to feel stressed when things seem to be going wrong. Sometimes, our lives can become chaotic, and we may not know what to do about it. Let's take a deep breath, relax, and focus on some positive thoughts. What are some things that you're grateful for today?
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): One way to relax today is to try some gentle stretches or meditation. You could also try journaling or writing in a journal to process your feelings and release any tension. Another idea is to take a short walk outside and breathe in the fresh air. You can even meditate for 10 minutes, focusing on your breath and letting go of worries.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): You should water it at least once a week. This is because the plant needs to be kept moist in order for its roots to develop properly. The plant will stop producing flowers and produce seeds if it's not given enough water.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): To find time to read, you should create a schedule for your daily life. You can use the calendar or planner to set realistic goals for each day. Be sure to prioritize activities that require concentration and focus on those first.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome!

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food. It is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (engramm, learned): Now! It was made by Sky Group. What made you think of it?

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Wie kann ich helfen?

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Gern geschehen!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **App** (sela-2, sela_chat): Tschüss! Einen schönen Tag noch.

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Ich bin Sela, das eigene kleine Sprachmodell von ENGRAMM. Ich kann mich unterhalten, Dinge erklären und Texte umschreiben oder zusammenfassen.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela, ein kleines Sprachmodell. Ich wurde im ENGRAMM-Projekt von Grund auf mit öffentlichen Texten trainiert und laufe offline auf deinem Computer.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat): Ich bin eine KI: Sela, ein kleines Sprachmodell aus dem ENGRAMM-Projekt. Ein Mensch bin ich nicht, aber ich helfe gern.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich kann mich unterhalten, Dinge erklären und Texte umschreiben oder zusammenfassen. Für Fakten gibt mir ENGRAMM Quellen aus seinem Wissenspaket, und ich zitiere sie. Ohne Quellen kann ich mich irren.

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Körperliche Aktivität einplanen**: Bewegung ist für den Körper wichtig, um Stress abzubauen und die Stimmung zu verbessern. Gehen Sie zum Beispiel zur Arbeit oder ins Bett, um zu trainieren.
2. **Bessere Schlaf-Rhythmus einhalten**: Eine Nacht lang vor dem Schlafengehen sollten Sie schlafen gehen, um Ihre Schlafqualität zu steigern.
3. **Schlaf-Bedingungen anpassen**: Es ist wichtig, Ihr Schlafzimmer so zu gestalten, dass es eine angenehme Temperatur hat und ausreichend Duschen und Essen erlaubt ist.

### de10 (instruction) – loop
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist ein kontinuierlicher, starker und starker starker starker starker starker starker starker starker starker starker starker starker …

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): Hey, ich bin heute um 8 Uhr komme. Danke für die Unterstützung!

### de12 (instruction) – cut_off
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): Im Herbst sind vier Gemüsesorten bekannt, die im Herbst geerntet werden:

1. **Linsenkraut (Licinium) – bekannt für seine silbernen Blüten und seine weichen Samen, die ideal für Gemüse oder Sprossen verwendet werden.
2. **Areca Palm (Dypsis lutescens) – ein weit verbreitetes tropisches und subtropisches Nutzpflanzengewächs, das in den tropischen Regionen der USA und Mexiko geerntet wird. Es ist leicht verdaulich und eignet sich gut für Salate oder Suppen.
3. **Sago Palm (Chamaedorea elegans) – ein krautiger Pflanzenzweig aus tropischen Regionen, der in der zweiten Hälfte des Jahres geerntet wird. Seine frischen Samen liefern eine harte, saure Erbinformation.
4. **Kohlkraut (Chlorophytum comosum) – ein krautiger Pflanzenzweig aus tropical und sub-tropical Regionen, der in der zweiten Hälfte des Jahres geerntet wird.

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Nudeln werden in einer Pfanne ohne Fett oder Öl gebraten. Nudeln sollten dabei immer von beiden Seiten nach oben geschoben werden, um das Löffeln zu verhindern.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Ein Fluss und ein See sind beide Wassertypen, die von Wasser durchströmt werden, jedoch keine natürliche Verbindung zwischen ihnen sind. 
Ein Fluss ist eine breite, meist staubige Strömung, die in Richtung eines größeren Flusses fließt. 
Ein See hingegen ist ein kühner, langer, meist unterirdischer See, der sich langsam von einem Fluss in Richtung einer anderen Strömung entwickelt.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Wintergedicht**  

Der Schnee liegt kalt wie ein unsichtbarer Feind,  
ein hässlicher Schimmel, der die Welt in tausend Stücke zerteilt.  
Die Luft riecht nach altem Brot und verbranntem Wein,  
die Bäume stehen still, als würden sie den Winter warten lassen.  

Der Wind trägt den Nebel herbei, doch er hält ihn nicht,  
der Regen stockt die Seele, und selbst die Sterne schweigen,  
als ob der Winter die Welt neu leuchten würde.  

Doch tief in den Herzen, wo die Erinnerung lebt,  
schreibt ein Flüstern, das nie verklagt wird:  
„Winter ist kein Feind, sondern ein Freund, der sich um mich schert.“  

---  
*Diese Zeilen zeigen, wie Winter zu einem Symbol für Menschlichkeit und Wundermut werden kann.*

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Energie sparen können Sie in Haushalt und Alltag durch folgenden Schritt:
1. Nutzen Sie energiesparende Geräte und Geräte, die keine Energie verbrauchen. Beispiel: Wenn Sie einen Kühlschrank mit einer drahtlosen Einrichtung nutzen, verwenden Sie weniger Strom als wenn Sie den Kühlschrank fernsteuerten.
2. Vermeiden Sie das Ein- und Ausschalten von Beleuchtung und Heizung, um Energie zu sparen.
3. Vermeiden Sie die Verwendung von Haushaltsgeräten und Stromzählern, wenn nicht für Haushaltsgeräte eine Energiesparlade ausgelegt ist.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Um zu einem Vorstellungsgespräch mitzuteilen, sollten Sie mindestens folgende Angaben enthalten:
- **Position/Unternehmen**
- **Geschlecht**
- **Gehalt**
- **Beruf** (z. B. Software, Technologie, Marketing)
- **Persönliches Erscheinungsbild** (z. B. Haare, Augenfarbe, Größe)
- **Erfahrung** im Unternehmen oder bei der Firma
- **Persönliche Qualifikationen** (z. B. Fähigkeiten, Erfahrungen)

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): Das höfliche: „Gib mir sofort die Unterlagen.“

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): **Korrigierter Text:**  
„Ich habe gestern ins Kino gegangen und habe zwar das Filmkonzept sehr gut gesehen, jedoch war der Film nicht wirklich gut.“  

**Erklärung:**  
1. **Klarheit & Präzision:** „Ins Kino gegangen“ → „gegangen“ (vermeidet die umgangssprachliche Formulierung „gegangen ins Kino“).  
2. **Tonalität:** Der Satz wirkt formeller als „ gewesen ins Kino gegangen“ und professioneller als „war sehr gut gewesen“.  
3. **Präzision:** „Sich ins Kino gegangen“ ist präziser als „gegangen ins Kino gegangen“ und passt besser in einen formalen Kontext (z. B. ein schriftliches oder mündliches Verhandlungsspiel).  

Der korrigierte Text ist nun kürzer, flüssiger und behält die gewünschte Klarheit bei.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): **Vereinfachter Satz:**  
„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“  

**Begründung:**  
- **"Achtung" → "ungeachtet"** (neutraler, da „ungünstig“ bereits den Grund für die Absage angibt).  
- **"Angepasst" → "abgepasst"** (neutraler und natürlicher im Deutschen), da „Angepasst“ eher auf das Gelingen einer Veranstaltung abzielt.  
- **"Absagt" → "Sagt"** (neutraler, da es sich um eine aktive Handlung handelt, nicht um passive Vergangenheitsform).  

Der Satz ist also kürzer, aber klar genug, um die Absicht eindeutig zu kommunizieren.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): Ich gehe in den Park, lese ein Buch.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): **Formuliere: "Hey, kann morgen leider nicht, sorry!"**

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): Hier ist ein zusammenfassender Satz:  
„Fahrradfahren fördert die Gesundheit durch stärkt das Herz und Muskeln, reduziert den Blutdruck sowie belastet Gelenke wenig. Es trägt zudem zu einem schnelleren Fahrstil bei.“

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt, wie Zugvögel in den **Süden** (Südosten) ihre Brut suchen und zurückkehren. Hier sind die zentralen Punkte:

1. **Wetterbedingungen**:  
   - In wärmeren Gebieten brüten häufig Zugvögel häufiger und fliegen oft über größere Entfernungen.  
   - Im Frühling kehren sie zurück, um Nahrung zu finden.

2. **Gefährdung**:  
   - Der Süden ist in der Regel weniger nahrungsreich als die Norden. Dies führt zu einer deutlichen Zunahme von Vogelstimmen und Rufe im Herbst.  
   - Klimawandel könnte die Nahrungsversorgung beeinflussen.

3. **Symbolik**:  
   - Die Zugvögel symbolisieren oft das Abwesenheitsprinzip (im Gegensatz zu Gezeiten oder Wind), das im Herbst besonders stark vorkommt.  
   - Sie bleiben oft zurück, um sich mit ihrem Nest zu belohnen.

**Zusammenfassung**: Der Text vermittelt, dass die Zugvögel in den Süden die Heimat suchen, während im Frühling die Rückreise wichtig ist. Diese Metapher betont die Bedeutung des Herbstes für das Verhalten der Vögel.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): **Lisa schwimmen lernen:**  
„ Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen. Lisa ist nun schwimmen, wie immer.“  

*(Begründung: Struktur, Metaphern, direkte Handlung, fehlende Erklärung/Einfluss auf den Leser.)*

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): „Die Stadt baut einen neuen Radweg entlang des Flusses, der Pendler sicher zur Arbeit bringt und die Autoverkehr in der Innenstadt vermindert. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat): Das bekannte Werk, das Goethe schrieb, ist "Faust".

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein ist der längste Nebenfluss der Eifel und entspringt im Sauerland bei Ahrweiler und mündet später in die Eifel.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik für seine Theorie der Relativitätstheorie, die die fundamentale Bedeutung des Gesetzes der Vergangenheitsformen betont. Er war einer der Mitbegründer der modernen Physik und hat damit einen Schlüssel zur Entwicklung der modernen Physik und Mechanik gespielt.

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

### de36 (multi_turn) – cut_off
- **Nutzer:** Ich möchte am Wochenende einen Kuchen backen.
  **App** (sela-2, sela_chat): Natürlich! Hier sind einige Tipps, um dein Kuchenbacken am Wochenende perfekt zu machen:

1. **Backen in der Sonne**: Stellen Sie sicher, dass Ihre Kuchen eine gute Nachtruhe haben (im Freien) und im vorgeheizten Ofen backen. Die Hitze knistert die Stärke und sorgt für ein gleichmäßigiges Backen.
2. **Umschichten mit frischem Gemüse**: Schälen Sie das Gemüse und schneiden Sie es in dünne Scheiben. Bringen Sie das Gemüse kurz in die Brühe und lassen Sie es abkühlen. Dies hält den Geschmack fest und verleiht dem Kuchen eine cremige Textur.
3. **Soße mit frischem Basilikum oder Pilzenbrot**: Erwärmen Sie das Soße in einer Pfanne mit 2 EL Olivenöl und rühren Sie es nach und nach an. Schmecken Sie das Soße mit Salz und Pfeffer ab und lassen Sie es kurz stehen. Das ist ein perfektes Gericht zum Abschmecken.
4. **Zusätzlicher Tipp**: Probieren Sie verschiedene Backtypen aus (z.B. Baguettes, Torten, usw.) und experimentieren Sie mit Ihren Zutaten!
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist das Torte. Es gibt viele verschiedene Varianten, aber alle werden Sie in etwa gleich aussehen lassen und es einfach zu machen sind.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Gern geschehen! Probieren Sie einfach aus und ich vergesse Ihnen alle Varianten.

### de37 (multi_turn) – cut_off
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Vielen Dank für deine Zeit! Um den Text noch etwas präziser zu gestalten, könnte ich die folgenden Versionen vorschlagen:

**Original:**  
"Ich lerne gerade Englisch. Ich höre gerade auf, wenn du etwas zu verstehen hast."  

**Überarbeitete Version:**  
"Ich lerne gerade Englisch und höre auf, wenn du etwas verstehen möchtest."  

Möchtest du eine noch formellere oder lockere Variante?
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Hier sind einige Vorschläge, um deinen Wortschatz zu verbessern:

1. **Struktur & Flüssigkeit:**  
   - Teile den Satz in zwei Absätze oder zeige, wie du dich aus dem Text führe (z. B. "Ich lerne gerade Englisch und höre auf, wenn du etwas verstehen möchtest").  
   - Stelle konkrete Beispiele ein (z. B. "Wenn du etwas zu verstehen hast, höre ich auf...").  

2. **Sprachliche Tiefe:**  
   - Vermeide fillernde Wörter (z. B. "er", "sie", "es") und achte auf präzisere Formulierungen (z. B. "wenn du etwas verstehen möchtest" statt "wenn du etwas verstehen möchtest").  
   - Sprich überflüssige Adjektive oder Adjektive deines Namens, die den Satz schwerfällig wirken.  

3. **Sprachliche Präzision:**  
   - Nutze idiomatische Ausdrücke wie "sehr gut", "sehr gut", "wichtig" oder "bedeutend".  
   - Halte Sätze kürzer (z. B.

### de38 (multi_turn) – cut_off
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Natürlich! Ich helfe gerne. Um eine Einladung zu schreiben, benötige ich ein paar Details:  

1. **Thema**:  
   - Was ist das Thema (z. B. "Wissenschaft", "Kultur", "Liebe/Freundschaft", "Gesellschaftspolitik" usw.)?  

2. **Anzahl der Beiträge**:  
   - Wie viele Beiträge möchtest du schreiben?  
   - Hast du bereits eine Einladung geschrieben, oder möchtest du etwas später schreiben?  

3. **Stichprobengröße**:  
   - Soll es ein spezifisches Thema sein (z. B. "Kommunikation", "Soziales", "Medienpolitik") oder mehrere Themen?  

4. **Zielgruppe**:  
   - Für wen möchtest du schreiben? (z. B. "Millionäre", "Bürokraten", "Künstler", "Journalisten")  
   - Gibt es eine Zielgruppe (z. B. "Vertreter", "Gemeinschaft", "Community", "Publikum"?)?  

5.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Natürlich! Ich helfe dir gerne. Um eine Einladung zu schreiben, benötige ich ein paar Details:  

1. **Thema**:  
   - Was ist das Thema (z. B. "Wissenschaft", "Kultur", "Liebe/Freundschaft", "Gesellschaftspolitik", "Community", "Publikum", "Philosophie", "Idee", "Philosophie der Zukunft" usw.)?  

2. **Anzahl der Beiträge**:  
   - Wie viele Beiträge möchtest du schreiben?  
   - Hast du bereits eine Einladung geschrieben, oder möchtest du etwas später schreiben?  

3. **Stichprobengröße**:  
   - Soll es ein spezifisches Thema sein (z. B. "Wissenschaft", "Kultur", "Liebe/Freundschaft", "Gesellschaftspolitik", "Community", "Publikum", "Philosophie", "Idee", "Idee der Zukunft")?  

4. **Zielgruppe**:  
   - Für wen möchtest du schreiben? (z. B.

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist Kochen. Die meisten Menschen kochen im Sommer, aber auch viele Menschen kochen Wintertagen und im Winter. Es gibt viele verschiedene Rezepte die auf Kochen basieren, aber es gibt auch viele verschiedene Rezepte die auf Backen basieren.

Wenn Sie ein gutes Hobby für den Winter haben können Sie auch ein Schafzucht betreiben. Auch wenn das Thema Winter keine große Rolle spielt, das Schafzucht ist eine sehr gute Alternative zu anderen Dingen die man für den Winter kochen könnte.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das ungefähr ungefähr $40-$60 für ein Schafzucht-Set für den Winter beträgt.

### de40 (multi_turn) – wrong_language
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (engramm, about): Einen Fun Fact über Pinguine habe ich auf Englisch gelesen: The largest living species is the emperor penguin (Aptenodytes forsteri): on average, adults are about 1.1 m (3 ft 7 in) tall and weigh 35 kg (77 lb).
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Pinguine können fliegen, aber sie fliegen in der Regel nicht wie ein Flugzeug. Sie fliegen in Flugzeugen, die mit einem Flügel aus dem Flugzeug herausgezogen werden, um sie zum Absturz zu bringen. Diese Flugzeuge haben eine Propellermaschine, die einen Propeller erzeugt und dann in den Flug hineinreicht. Pinguine hingegen fliegen in Flugzeugen, die mit einem Flügel aus dem Flugzeug herausgezogen werden, um sie zum Absturz zu bringen.

