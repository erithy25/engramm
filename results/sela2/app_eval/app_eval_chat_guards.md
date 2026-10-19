# Sela-2 in der App: 100 feste Prompts (mit Schutzregeln)

Gewichte `sela2-chat.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-18T18:34:15Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 2 von 100 |
| identity_error | 0 von 100 |
| echo | 0 von 100 |
| cut_off | 0 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| prompts_with_a_problem | 2 von 100 |

Antworten nach Modell: {'engramm': 26, 'sela-2': 91}; nach Art: {'about': 1, 'answer': 5, 'learned': 7, 'sela_chat': 85, 'sela_grounded': 6, 'unknown': 13}.
Schutzregeln: 5 Antworten neu erzeugt, 4 feste Identitätsantworten; 2 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting) – wrong_language
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat, 3 Versuche): Hi! Was kann ich für dich tun?

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm fine, thank you for asking! I just need a cup of tea or anything to get me going.

### en03 (greeting)
- **Nutzer:** Good morning!
  **App** (sela-2, sela_chat): Good morning! How can I help?

### en04 (greeting)
- **Nutzer:** Hey there, what's up?
  **App** (sela-2, sela_chat): Hey there! What's up?

### en05 (greeting)
- **Nutzer:** Thanks a lot for your help earlier!
  **App** (sela-2, sela_chat): I'm glad I could help. If you have any more questions, feel free to ask me anything else.

### en06 (greeting)
- **Nutzer:** I have to go now. Goodbye!
  **App** (sela-2, sela_chat): Goodbye! Good luck with your trip.

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): My name is Sela. I'm a compact language model trained from scratch by the ENGRAMM project. I run locally on your device, and our conversation stays here.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): My name is Sela. I'm a compact language model trained from scratch by the ENGRAMM project. I run locally on your device, and our conversation stays here.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat, Regel): The ENGRAMM project trained me from scratch. I'm Sela, a small language model that runs offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model – a computer program, not a human. I run offline on your computer.

### en11 (identity)
- **Nutzer:** What can you help me with?
  **App** (sela-2, sela_chat): I can help with a wide range of tasks and projects. Some of the areas I can assist with include:

- Helping you design a new product or service
- Identifying and developing your strengths and weaknesses
- Writing a blog post or article about a topic related to your field
- Assisting with data analysis and interpretation
- Assisting with social media management and engagement
- Developing marketing strategies and campaigns
- Collaborating with other developers or teams

Please feel free to ask me any questions you have, and I'll do my best to help you achieve your goals.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat, Regel): I'm Sela, a small language model, so I don't have feelings the way people do. But I'm happy to help.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Schedule your work sessions in a quiet, private space where you can work without distractions. This will help you stay focused and avoid multitasking.
2. Take breaks throughout the day to rest and recharge. Use this time to do something that you enjoy or that helps you relax.
3.

### en14 (instruction)
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): One can boil an egg in a microwave for 30 minutes, then add water and let it simmer. Once the yolk is fully cooked, you can pour into your pan with some liquid to stir up any browned bits.

### en15 (instruction)
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a small, self-replicating code that can spread from one computer to another. It's like a letter or email message that can be shared between two people, usually in the form of a link or email address. Viruses are typically made up of several parts, including a protein or DNA sequence that makes it difficult for other viruses to replicate and find entry points.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hello, I hope you're doing well!

I wanted to let you know that my plants are really growing and I'm having a hard time getting them watered. Would you be able to help me by coming over to your house tomorrow morning? It would be great if we could go to the garden together for some watering.

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): Here are four fruits that are high in vitamin C:
- citrus
- bell peppers
- broccoli
- leafy greens such as lettuce, spinach, and kale
- sweet potatoes

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): The difference between weather and climate is the amount of weather that a region receives.  Weather refers to the overall state of conditions, while climate is the long-term average of temperature and precipitation that a region experiences over time.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): In the autumn leaves, a fleeting whisper stirs,
A soft, whispered promise of warmth.
The earth exhales in amber threads,
A dance of fall's grace, as if the trees are old.

The wind whispers secrets through the trees,
As the leaves, wither and die, fall into a tangle.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): To make your password more secure, consider the following:

Use a mix of uppercase and lowercase letters.

Choose a unique and memorable password.

Avoid using special characters or symbols that can be easily cracked by someone else.

Use two-factor authentication (2FA) for accessing accounts with multiple passwords.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): The coffee shop near the library is called "Amea"

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): For a 20-minute workout without equipment, start by identifying the type of workout you want to do and what time it will be. Choose something that you enjoy, such as running, swimming, cycling, or a combination of both. Make sure to choose a workout that is low impact and easy on your joints.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (engramm, answer): Write a short, friendly message to a neighbour asking them to water your plants next week.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, darkened sea that stretches across the globe, its depths hidden from the view of human eyes.

### en26 (instruction)
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): You can say something like, "I'm not sure I want to attend the party and would prefer to have a different time" or, "I was thinking of attending the party and didn't feel comfortable with my schedule."

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (engramm, learned): Ah, okay. How's that going?

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (engramm, learned): Oh, The The. It's an English post-punk band. How did you discover them?

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct phrase would be "She doesn't like going to school on mondays."

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): I walk to the station and buy a ticket.

This sentence is in the past tense because the verb "walk" is in the past participle form, which matches the present-tense verb "buy."

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): Here's a more exciting alternative: "Meet the hidden treasures that will make your day brighter – our shop is open to all! Our latest offerings include rare and unique items, such as a first-edition vintage suitcase, a quirky charm, or an exclusive collection of antique clocks."

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat, 2 Versuche): The train leaves at 8 o'clock.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): The original sentence is: "Hey, can't make it tomorrow, sorry!"

I made several changes to improve the tone and clarity of the sentence. I replaced "Hey" with "Hey," which is a more formal and professional way to express the idea. I also added a comma after "Tom" to separate the two independent clauses and improve the sentence's rhythm.

### en34 (rewrite)
- **Nutzer:** Shorten this sentence: "Due to the fact that it was raining very heavily outside, we made the decision to stay inside the house."
  **App** (sela-2, sela_chat): A more concise version of the sentence could be: "Due to the heavy rain outside, we decided to stay indoors." 

This rephrased sentence conveys the same information in a more compact form, using a dash to indicate the reason for staying and eliminating unnecessary words.

### en35 (summarize)
- **Nutzer:** Summarize in one sentence: "Bees are important pollinators. When they collect nectar from flowers, pollen sticks to their bodies and is carried to other flowers. This helps plants produce fruits and seeds. Many crops that people eat, such as apples and almonds, depend on bees."
  **App** (sela-2, sela_chat): That's a great sentence. Here's a slightly edited version: "Bees are important pollinators, as they collect nectar from flowers and carry it to other flowers. This helps plants produce fruits and seeds, while many crops rely on bees."

### en36 (summarize)
- **Nutzer:** Summarize this text: "The library will be closed on Monday for repairs to the heating system. It will reopen on Tuesday at 9 a.m. Books that are due on Monday can be returned on Tuesday without a late fee."
  **App** (sela-2, sela_chat): The library is closed on Monday for repairs to the heating system. Bookstore returned on Tuesday at 9 a.m.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize)
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): "Tom was a self-taught guitar player who had to learn the fundamentals of music. He started with learning the basics of guitar playing, like how to play chords and strumming simple notes. He also learned to use his fingers and learned to experiment with different techniques to get better at his craft."

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of gasoline, produce no exhaust gases, and do not charge.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): The project meeting is moved from Wednesday to Thursday at 2 p.m.

### en41 (summarize)
- **Nutzer:** Summarize briefly: "Recycling turns used materials such as paper, glass and plastic into new products. It saves raw materials and energy and reduces the amount of waste in landfills. Sorting waste correctly at home makes recycling much more effective."
  **App** (sela-2, sela_chat): Here's a rewritten version of your text with some suggested improvements:

"Recycling transforms discarded materials into new products. By converting used items like paper, glass, and plastic into new goods, it saves raw materials and energy while minimizing waste in landfills. Sorting waste correctly at home is crucial for maximizing recycling effectiveness."

### en42 (summarize)
- **Nutzer:** In one sentence, what is this about? "The town council approved a new park on the site of the old car park. The park will have trees, a playground and a small pond. Construction starts in spring and should take about one year."
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that. Nice — The The. It's an English post-punk band. What's your favourite song?

### en43 (grounded)
- **Nutzer:** How long is the Danube?
  **App** (sela-2, sela_grounded): 2850000 [1].

### en44 (grounded)
- **Nutzer:** What is Ada Lovelace known for?
  **App** (engramm, answer): Ada Lovelace is known for Computing.

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
  **App** (sela-2, sela_grounded): Emmanuel Grégoire is the mayor of Paris [1].

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
  **App** (sela-2, sela_chat): If you're looking to travel between cities, I would recommend visiting New York City.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): New York City has a great dining scene. You should try the following:
- Finger foods such as gumbo, chicken, and pizza
- Italian cuisine
- Pasta dishes
- The best thing about New York is the food, it's a mix of modern and traditional cultures.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Hi Sam, nice to meet you! I'll remember your name.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Sure, I can help you! Here is a simple birthday card for your mother that you can use as a gift:

```
You are my dear little one and I am so sorry about the loss of you.
I want you to know that I will always cherish every moment with you.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Sure, here is a simple birthday card for your mother:
```
You are my dear little one and I am so sorry about the loss of you.
I want you to know that I will always cherish every moment with you.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): It sounds like you're feeling anxious and stressed about the upcoming week. Here are a few things to consider:

- Are there any stress triggers in your life that you could change? For example, are you more prone to stress when you're feeling anxious or stressed about something else?
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): To relax this evening, you could try some relaxation techniques such as deep breathing exercises, meditation, or yoga. You could also consider activities like reading a book, watching a movie, or practicing deep breathing exercises to calm your mind and body.

Additionally, consider practicing relaxation techniques like progressive muscle relaxation, which involves tensing and relaxing different muscle groups in your body to release tension and promote relaxation.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): It is recommended to water your plants every 2-3 weeks during the spring and fall. During the summer, you should water more often, as they require more frequent watering to prevent disease.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (sela-2, sela_grounded): Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact [1].
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn)
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): Here are some tips for finding time to read:
- Set a realistic reading goal. The more you read, the more likely you are to read regularly and stay on top of your reading goals.
- Create an environment that fosters reading. Make yourself comfortable in your home by having a good chair or couch.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! Let me know if you have any more questions or need further assistance.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (engramm, about): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food. A sub-recipe or subrecipe is a recipe for an ingredient that will be called for in the instructions for the main recipe.
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (engramm, learned): Now! It was made by Sky Group. What made you think of it?

### de01 (greeting)
- **Nutzer:** Hallo!
  **App** (sela-2, sela_chat): Hallo! Wie kann ich dir helfen?

### de02 (greeting)
- **Nutzer:** Guten Morgen, wie geht es dir?
  **App** (sela-2, sela_chat): Guten Morgen! Wie kann ich dir helfen?

### de03 (greeting)
- **Nutzer:** Danke für deine Hilfe!
  **App** (sela-2, sela_chat): Gern geschehen!

### de04 (greeting)
- **Nutzer:** Tschüss, bis bald!
  **App** (sela-2, sela_chat): Tschüss, bis bald!

### de05 (identity)
- **Nutzer:** Wer bist du?
  **App** (sela-2, sela_chat): Ich bin Sela, ein kleines Sprachmodell. Ich wurde im ENGRAMM-Projekt von Grund auf mit öffentlichen Texten trainiert und laufe offline auf deinem Computer.

### de06 (identity)
- **Nutzer:** Wie heißt du?
  **App** (sela-2, sela_chat): Ich bin Sela, das eigene kleine Sprachmodell von ENGRAMM. Ich kann mich unterhalten, Dinge erklären und Texte umschreiben oder zusammenfassen.

### de07 (identity)
- **Nutzer:** Bist du ein Mensch?
  **App** (sela-2, sela_chat, Regel): Ich bin Sela, ein kleines Sprachmodell – ein Computerprogramm, kein Mensch. Ich laufe offline auf deinem Computer.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich helfe gerne bei Fragen, Problemen oder Themen, die du beschäftigen – einfach sag mir den Text oder den Kontext, und ich schaue dir gerne an!

### de09 (instruction)
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. Setzen Sie einen festen Schlafplan: Aufarbeiten Sie den Tag mit dem gleichen Zeitpunkt des Tages und schalten Sie Ihr Bett oder Bett mit einem besseren Licht.
2. Reduzieren Sie vor dem Einschlafen: Stecken Sie sich ab, wenn möglich, bevor Sie ein Badgehen im Dunkeln gehen.

### de10 (instruction)
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist die Energie, die uns aus der Luft, Erde oder Wasser ableiten. Sie ist für unser Leben und Planeten entscheidend!

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): Hey [Name], ich bin heute noch nicht da! Ich habe mich mit dem Lehrer besprechen und hoffe, dass ich eine gute Zusammenfassung der Dinge habe. Die Arbeit ist schwer, aber die Ergebnisse sind sehr wichtig für unser Projekt in den nächsten 3-4 Wochen. Wenn Sie weitere Informationen haben oder Fragen haben, stehe ich gerne zur Verfügung.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): Die vier Gemüsesorten, die im Herbst geerntet werden, sind **Benedict** (Bacopa), **Pearl** (Pomegranate) und **Spelt** (Acer).

### de13 (instruction)
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Koche Nudeln richtig? Das gibt es viele verschiedene Methoden. Einige davon sind:
1. **Kochschritt**: Eine einfache Methode ist das Backen von Nudeln in einem Ofen, der den Teig aus dem Teigkästchen abkochen lässt. Diese Technik ist besonders empfehlenswert, wenn Sie lieber ein gebrattes Brot oder eine cremige Sauce verwenden möchten.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See liegt in der Definition des Wassereis-Stimps und der Funktionalität. 

**Fluss**: Ein Fluss ist ein flüssiges Wasser, das sich durch den Wind windet und ihn durch die Luft fließt. Er kann durch Flüsse, Seen, Bäche oder Ozeane gebildet werden, wobei seine Flüsse nicht durch Segel oder Asche fließen.

### de15 (instruction)
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Winter, der Winter, der Winter, der Winter**  

In einem stillen Dorf, wo die Sterne schweben,  
die Schneeflocken wie Goldschneider tanzt,  
doch die Welt ist ein Meer aus Nebel und Sand.  

Der Winter ruht auf den Wänden, mit Schatten und Lied,  
ein leises Lied, das durch die Zeit weht.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, kann man bewusst Konsum reduzieren. Dazu gibt es viele Optionen wie z. B. eine große Menge an der eigenen Stromrechnungen, die Verwendung von energieeffizienten Geräten oder wenn nicht die eigenen Stromverbrauchsprobleme in den Vordergrund stellt.

### de17 (instruction)
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Es ist wichtig, zu einem Vorstellungsgespräch mitzunehmen. Es gibt verschiedene Möglichkeiten, aber die beste Wahl hängt davon ab, wie du dich impressionierst. Hier sind einige Tipps:

1. **Einemarmen**: Du hast recht! Du kannst das Gespräch mit dem gleichen Lächeln und Augenkontakt antworten.

### de18 (rewrite)
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat, 3 Versuche): **Gib mir sofort die Unterlagen:**  
Ich brauche sofort die Unterlage, um zu beginnen.  
Klar, lass uns erstmal so schnell wie möglich anfangen!  

**Grundlegende Informationen:**  
1. **Unternehmenshaltlich**: Die Zielmarktanalyse muss im Rahmen des Unternehmens (z.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Um die Fehler zu beheben, könntest du:  
„Ich habe heute ins Auto gegangen und der Film war sehr gut gewesen.“  
Dies reduziert die Wiederholung von „seine“ und vermeidet die Verwechslung mit „einmal“.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat, 2 Versuche): Hier ist eine vereinfachte Version des Satzes: „Die ungünstigen Witterungsverhältnisse prevented die Veranstaltung ab.“

**Erklärung:**  
- **„ungünstig“** → „ungünstige“ (da der Ausdruck „ungünstig“ impliziert, dass es Unvorhersehbarkeit gibt).

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): „Ich ziehe ein Buch aus der Tasche und lasse es in den Park.“

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): Hey, kann morgen doch nicht sorry!

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln sowie belastet die Gelenke wenig, wodurch es in der Stadt oft schneller als das Auto ist.“

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringen eure Ideen für das Sommerfest mit. Viele Grüße, Jonas

### de25 (summarize)
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Das ist eine solide Beschreibung des Erlebnisses. Hier ist eine prägnante Version mit einigen Verbesserungen:

**„Im Herbst zieht viele Zugvögel in den Süden, um ihre Bestellung zu finden. Im Frühling kehren sie zurück, um zu brüten.“**

### Erklärung der Änderungen:
1.

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): **Lisa schwamm mit einem Coachin in der Wüste, die die Sonne funkelt.**  

Die Sonne versank ihr den Atem, als würde sie in eine unendliche Welt eintauchen. Die Sonne tauchte auf ihre Haut – ein Schimmer von Hoffnung und Glück. Sie zog sich in einen Sandstapel, und begann langsam dem Weg zu Wasser.

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): Die Stadt baut einen neuen Radweg entlang des Flusses, der Pendler sicherer und den Autoverkehr in der Innenstadt reduziert. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [2].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat, 3 Versuche): Der berühmte Gedicht "Werde im Wind" ist ein bekanntes Werk des Gedichts.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein führt den Fluss im Bereich von der Schweiz bis zur Nordsee und mündet in der heutigen Südsee (wo er auf der Nordseite verläuft) weiter in die Nordse.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Ein Nobelpreis, die sich aus dem Jahr 1955 ableiten, wurde für Wissenschaftler in der Quantenphysik (die Teilchenstheorie) und Physik (der Mathematik) verliehen.

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
  **App** (sela-2, sela_chat): Um am Wochenende eine Kuchen backen, folgen Sie der angegebenen Schritte:  
1. **Schießen Sie den Kuchen** mit einem Ofen auf der Grundlage von 25°C.  
2. **Verwenden Sie die Mehl und Zucker**, um ihn in ein warmes Wasser zu verwandeln.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist die Brötchen.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Falls Sie weitere Fragen haben, können Sie gerne einfach sagen.

### de37 (multi_turn)
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Hey! Wenn du möchtest, kann ich dir mit dem deutschen Deutsch-Spiel weiterhelfen?
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um dein Wortschatz zu verbessern, kannst du mir bitte die wichtigsten Punkte an deinen Text einfügen. Dann kann ich dir Vorschläge machen, z. B. prägnantere Formulierungen oder alternative Perspektiven.

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe gerne! Bitte schicken Sie mir deinen Einladungsvorschlag, und ich stelle dir Vorschläge für die Formatierung des Textes. Hier sind einige Möglichkeiten:

- **Betreff:** Bestätigung Ihrer Bewerbung (z. B. "Gute Frage zu Ihrem Lebenslauf!")
- **Unterlagen:** [Adresse/Name] oder eine kurze E-Mail mit Details zur Prüfung
- **Zweck:** Erläuterung zum Zweck des Bewerbungsanspreters
- **Anrede:** „Herr/K Frau [Name], wir freuen uns, Sie am [Datum] an [Adresse] begrüßen zu dürfen!“
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Das ist eine wunderbare Gelegenheit, um einen positiven Eindruck zu erzielen! Um es bestmöglich zu planen, könnte ich folgende Fragen stellen:

- **Betreff:** Bestätigung Ihrer Bewerbung (z. B. „Gute Frage zu Ihrem Lebenslauf!")
- **Unterlage:** [Adresse/Name] oder eine kurze E-Mail mit Details zur Prüfung
- **Zweck:** Erläuterung zum Zweck des Bewerbungsanspreters
- **Anrede:** „Guten Tag, Frau [Name], wir freuen uns, Sie an diesem Tag begrüßen zu dürfen!“

### de39 (multi_turn)
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist das Himmen. Es gibt viele verschiedene Arten von Wasser, die man können malen kann, wie zum Beispiel Dünenmaden oder Schleifendünen. Wenn man nicht genug Zeit für die Arbeit hat und der Winter nicht ideal ist, könnte man auch einfach Eisverkauf sammeln, um ein Bier zu trinken oder einfach einen Snack in einer Schüssel oder einem Getränk-Wasserkuchen kreisen lassen.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Das ist ein sehr zu vieles. Die Kosten für das Hobby sind fast immer mit dem Preis des Getränks oder einem weiteren Getränke in der großen Anzahl die soziale expenses haben, aber es ist gut, dass man andere hobbies nicht vernachlässigen kann.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine große, fast verrostete Art, die in Nord- und Südostasien heimisch ist. Sie sind eine der kleinsten und kleinsten Pinguine und sind in der Regel klein und klein [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Pinguine sind zwar keine Menschenaffen, aber sie sind eine faszinierende und arme Art. Sie haben nur einen kleinen Flügel, die sich in der Regel im Boden zusammenziehen. Sie können sich auch von einem Speer oder durch ein Werkzeug bewegen. Pinguine sind nicht größer als andere Artarten, und wie viele Arten gibt es sie?

