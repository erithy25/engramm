# Sela-2 in der App: 100 feste Prompts (ohne Schutzregeln)

Gewichte `sela2-mix30.npz`, Paket `lite-3.1.0-beta.1`, 2026-10-18T18:36:25Z. ENGRAMM bearbeitet jeden Zug zuerst; Sela-2 formuliert Antworten mit Quellen um (geprüft) und antwortet frei auf Smalltalk und offene Bitten.

| Zählung | Prompts |
|---|---|
| wrong_language | 1 von 100 |
| identity_error | 0 von 100 |
| echo | 1 von 100 |
| cut_off | 14 von 100 |
| role_leak | 0 von 100 |
| loop | 0 von 100 |
| empty | 0 von 100 |
| prompts_with_a_problem | 16 von 100 |

Antworten nach Modell: {'engramm': 25, 'sela-2': 92}; nach Art: {'about': 1, 'answer': 4, 'learned': 7, 'sela_chat': 85, 'sela_grounded': 7, 'unknown': 13}.
Schutzregeln: 0 Antworten neu erzeugt, 0 feste Identitätsantworten; 1 Sela-Quellenantworten nicht bestanden (ENGRAMM-Antwort gezeigt).

## Alle Antworten

### en01 (greeting)
- **Nutzer:** Hi!
  **App** (sela-2, sela_chat): Hello! How can I help you today?

### en02 (greeting)
- **Nutzer:** Hello, how are you today?
  **App** (sela-2, sela_chat): I'm doing well! I was just trying to tell you that my name is [name]. I'm a freelance writer and photographer. I like to share my love of photography with people through my blog, which has been gaining a lot of attention lately. My blog is called [Blog Name] and it's all about capturing the beauty in everyday moments.

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
  **App** (sela-2, sela_chat): Goodbye! Goodbye!

### en07 (identity)
- **Nutzer:** Who are you?
  **App** (sela-2, sela_chat): My name is Sela, and I'm a compact language model trained from scratch by the ENGRAMM project. I run locally on your device, and our conversation stays here.

### en08 (identity)
- **Nutzer:** What is your name?
  **App** (sela-2, sela_chat): I'm Sela, ENGRAMM's own small language model. I can chat, explain things, and rewrite or summarise text.

### en09 (identity)
- **Nutzer:** Who made you?
  **App** (sela-2, sela_chat): I was trained from scratch in the ENGRAMM project on public text, and I run offline on your computer.

### en10 (identity)
- **Nutzer:** Are you a human or a computer program?
  **App** (sela-2, sela_chat): I am a machine program.

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
- Helping with task completion and quality assurance
- Assisting with budgeting and financial planning
- Advising on intellectual property rights and licensing
- Helping with the design and development of software and hardware
- Helping with data science and analytics
- Assisting with technical writing and documentation
- Assisting with coding and programming tasks
- Assisting with data visualization and presentation
- Assisting with data analysis and reporting
- Assisting with business planning and strategy
- Assisting with project management and timeline
- Assisting with resource allocation and planning

Feel free to ask me any specific questions or request assistance in any of these areas.

### en12 (identity)
- **Nutzer:** Do you have feelings?
  **App** (sela-2, sela_chat): I have feelings. I feel happy when someone does something they love. I feel sad when someone doesn't do something they like. I feel scared when someone doesn't know what to do. I feel anxious when someone doesn't understand my needs and wants me to go away.

### en13 (instruction)
- **Nutzer:** Give me three tips for staying focused while working from home.
  **App** (sela-2, sela_chat): 1. Write down your goals and priorities in a planner or calendar to keep you on track.
2. Break up your tasks into smaller, manageable chunks.
3. Make time for self-care and relaxation to help you recharge.

### en14 (instruction) – cut_off
- **Nutzer:** How do I boil an egg so that the yolk stays soft?
  **App** (sela-2, sela_chat): There are many ways to boil an egg, but the most common method is boiling it in water. You can use a pot or a pan with a tight fitting lid and heat the water until the water is hot enough to boil the egg. Then, place the egg on the pot and bring it to a boil. The boiling point of water is around 100 degrees Fahrenheit. Once the egg is cooked through, you can remove it from the pot and drain the water.

Another method is to use a steamer or microwave to cook the egg. Heat a small amount of oil over medium-high heat, then add some water and cook the egg until it is cooked through. The water should be heated to around 400 degrees Fahrenheit. Once the water reaches a temperature of 425 degrees Fahrenheit, remove the egg from the steamer or microwave and drain the water.

You can also use a large pot or a large container with a tight-fitting lid to boil the egg. Fill the pot or container with water and heat it until the water is hot enough to boil the egg. Then, place the egg on the pot and bring it to a boil.

### en15 (instruction) – cut_off
- **Nutzer:** Explain in simple words what a computer virus is.
  **App** (sela-2, sela_chat): A computer virus is a program that can infect your computer or other devices, and then replicate itself to make copies of itself. It's essentially a way for the computer to create new copies of itself, without having to actually do anything to destroy the original device.

Imagine you have a computer at home and you want to delete some files on it. The computer sends you an email saying that it deleted those files, but it doesn't tell you what happened. Instead, it sends a message asking you to check back in a few days to see if the files were deleted correctly. If you try to do so, the message will say that the files are gone, but the email won't show you where they went. That's because the virus has sent the wrong email!

A computer virus can also spread through email attachments, such as links to infected websites or emails from unknown senders. Once a virus infects a computer, it can replicate itself and take over the entire system, making it harder to detect and remove.

### en16 (instruction)
- **Nutzer:** Write a short, friendly message to a neighbour asking them to water my plants next week.
  **App** (sela-2, sela_chat): Hello! I'm so glad you asked.  Please don't worry if you're not sure what to do.  We'll talk about this later.
I'm going to be right here in the garden with the plants and some water to keep them healthy.  You can go ahead and tell me how much you need.  Then we'll take it from there. 

Thank you for your patience, and happy watering.

Warm regards,
Emma

### en17 (instruction)
- **Nutzer:** List four fruits that are high in vitamin C.
  **App** (sela-2, sela_chat): 1. Watermelon
2. oranges
3. Sweet potatoes
4. cantaloupe

### en18 (instruction)
- **Nutzer:** What is the difference between weather and climate?
  **App** (sela-2, sela_chat): We can say that weather is the condition of the air, climate is the condition of the atmosphere, and vice versa.  Weather is a weather that occurs over a long period of time, such as a year or a decade. Climate is the condition of the atmosphere, which is the layer of air surrounding our planet.

### en19 (instruction)
- **Nutzer:** Write a four-line poem about autumn leaves.
  **App** (sela-2, sela_chat): As autumn leaves fall,
They dance in golden light,
And whisper secrets to the wind,
The earth is still and quiet,
Yet something has changed,
Something is watching,
A mystery is lurking,
A hidden truth,
A secret that never grows old.

### en20 (instruction)
- **Nutzer:** How can I make my password more secure?
  **App** (sela-2, sela_chat): Here are some ways to make your password more secure:
1. Use strong passwords.
2. Consider using a salted password.
3. Avoid reusing the same password.
4. Use two-factor authentication (2FA) whenever possible.
5. Make sure to keep your password up to date.
6. Change your passwords regularly.

### en21 (instruction)
- **Nutzer:** Suggest a name for a small coffee shop near a library.
  **App** (sela-2, sela_chat): The name could be "Bliss & Co."

### en22 (instruction)
- **Nutzer:** Explain why we have day and night.
  **App** (engramm, unknown): I don't know — I couldn't find anything about “Explain” in what I've read.

### en23 (instruction)
- **Nutzer:** Give me a simple plan for a 20-minute workout without equipment.
  **App** (sela-2, sela_chat): For a 20-minute workout without equipment, you can follow these steps:
1. Choose a warm-up exercise like jumping jacks, squats, or lunges.
2. Make sure your legs are comfortable and your knees are straight.
3. Start with simple movements like jumping jacks or squats.
4. Alternate between each movement and rest for 30 seconds.
5. Repeat 5-7 times.
6. Rest briefly after each workout.

Here's an example of what this might look like in practice:

Start with jumping jacks, jump to the floor, and then squat down on your toes. Repeat 5-7 times. Rest for 10 seconds. Repeat 8-10 times. Do 5-7 reps. Rest for 15 seconds. Rest for 20 seconds.

### en24 (instruction)
- **Nutzer:** What should I pack for a weekend camping trip?
  **App** (engramm, answer): Write a short, friendly message to a neighbour asking them to water your plants next week.

### en25 (instruction)
- **Nutzer:** Write one sentence that describes the ocean.
  **App** (sela-2, sela_chat): The ocean is a vast, shimmering, and mysterious expanse that stretches out before us like a canvas of wonder. It's a realm of endless possibility, where the sun dips below the horizon and dances across the surface, casting an otherworldly glow over the sea floor. From above, we can see towering coral formations, shimmering waterfalls, and hidden treasures waiting to be discovered by those who dare to venture into this unknown world.

### en26 (instruction) – cut_off
- **Nutzer:** How do I politely decline an invitation to a party?
  **App** (sela-2, sela_chat): When you decline an invitation to a party, it's essential to be respectful and considerate of others' feelings. Here are some tips:

1. **Be clear about your reason**: If you're attending the party for work or other personal reasons, explain why you're not available. For example, "I'm attending a conference" or "I'm taking a break from my schedule."
2. **Use polite language**: Avoid using harsh or condescending language. Instead, use phrases like "I appreciate your offer, but I need to attend," or "I've got a meeting in two hours."
3. **Avoid being confrontational**: Refrain from making direct comments or criticisms about the person who invited you. This can damage relationships and create more tension.
4. **Listen actively**: When someone declines an invitation, try to understand their perspective and respond thoughtfully. Ask open-ended questions like "What do you think?" or "Can you tell me more about what you're doing?"
5.

### en27 (rewrite)
- **Nutzer:** Rewrite this more politely: "Send me the report now."
  **App** (engramm, learned): Ah, okay. How's that going?

### en28 (rewrite)
- **Nutzer:** Make this sentence simpler: "The utilisation of public transportation facilitates a reduction in urban congestion."
  **App** (engramm, learned): Oh, The The. It's an English post-punk band. How did you discover them?

### en29 (rewrite)
- **Nutzer:** Fix the grammar: "She don't like going to school on mondays."
  **App** (sela-2, sela_chat): The correct phrase should be "She don't like going to school on mondays." The comma after "on" is unnecessary, so the corrected sentence would be: "She don't like going to school on mondays."

This change makes the sentence clearer and more polished.

### en30 (rewrite)
- **Nutzer:** Rewrite this sentence in the past tense: "I walk to the station and buy a ticket."
  **App** (sela-2, sela_chat): "I walk to the station and buy a ticket."

This sentence in the past tense is used to describe actions that occurred before the present time (in this case, before the date). It indicates that the action began before the present time.

### en31 (rewrite)
- **Nutzer:** Make this sound more exciting: "Our shop has a sale this weekend."
  **App** (sela-2, sela_chat): "Hear this? It's a sale! Grab your favorite sweater or coat today and hit the snooze button. The shop has a sale this weekend!"

### en32 (rewrite)
- **Nutzer:** Turn this into a question: "The train leaves at eight o'clock."
  **App** (sela-2, sela_chat): What is the correct answer?

A train leaves at eight o'clock.

### en33 (rewrite)
- **Nutzer:** Rewrite this in a formal tone: "Hey, can't make it tomorrow, sorry!"
  **App** (sela-2, sela_chat): Dear [Recipient's Name],

I apologize for the inconvenience this may cause. However, I will be unavailable tomorrow due to a personal matter. Please let me know if you need assistance with your assignments or if there are any other support you require.

Thank you for your understanding and support.

Best regards,
[Your Name]

Note: In formal writing, it's often best to use "Dear" instead of "Hey." This is because in informal writing, using "Hey" can come across as more casual.

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

I made a few changes to improve clarity and grammar. I added a comma after "Monday" to separate the two independent clauses, and changed "reopen" to "reopen" to make it clear that the library is open on both Mondays and Tuesdays. I also replaced "books that are due on Monday" with "books due on Monday" to make the sentence more concise. Additionally, I changed "due" to "due" to maintain subject-verb agreement, as "due" is the correct verb in this context. Finally, I replaced "free" with "free" to make the language more formal and polished.

### en37 (summarize)
- **Nutzer:** What is the main point of this paragraph? "Drinking enough water is important for health. Water helps regulate body temperature, keeps joints working smoothly and supports digestion. Many people need more water on hot days or when they exercise."
  **App** (engramm, unknown): I don't know for sure. The closest thing I read is the article “Paragraph”, but it doesn't answer that clearly. Oh, interesting — tell me more.

### en38 (summarize) – cut_off
- **Nutzer:** Give me a short summary: "Tom wanted to learn the guitar. At first his fingers hurt and the chords sounded wrong. He practised for fifteen minutes every day. After three months he could play his favourite song for his friends."
  **App** (sela-2, sela_chat): The story of Tom is a classic example of the power of perseverance and dedication in overcoming challenges. Here's a possible summary:

Tom began playing the guitar at age six, and his love for music only grew stronger over time. He learned to play his favorite song by ear, which he found particularly enjoyable. After spending three months practicing regularly, Tom could confidently play any song he wanted. His parents, who had always been supportive of his passion, encouraged him to keep playing. By the end of the year, Tom was well on his way to becoming a skilled musician.

I made several changes to enhance the narrative and improve its clarity:

- I rephrased some sentences to make them more concise and engaging. For example, "At first his fingers hurt and the chords sounded wrong" became "his love for music only grew stronger over time."
- I used more descriptive language to paint a vivid picture in the reader's mind. For example, "the chords sounded wrong" became "his fingers hurt and his fingers felt like they were going to rip off."
- I added transitional phrases ("After spending three months...") to connect the ideas between sentences and paragraphs.

### en39 (summarize)
- **Nutzer:** Summarize in two sentences: "Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere."
  **App** (sela-2, sela_chat): Electric cars run on batteries instead of petrol. They produce no exhaust gases while driving, which can improve air quality in cities. However, the batteries take time to charge, and charging stations are not yet available everywhere.

### en40 (summarize)
- **Nutzer:** Summarize this email: "Hi team, the project meeting is moved from Wednesday to Thursday at 2 p.m. Please bring your progress notes. We will also plan the next steps for the website launch. Thanks, Anna"
  **App** (sela-2, sela_chat): This email is a formal and professional document that clearly states the upcoming project meeting, the preferred time of the meeting, and any planned steps to launch the website. The language used is formal and professional, which is suitable for a team meeting.

The email starts by stating that the project meeting is scheduled for Wednesday at 2 p.m., and then it outlines the desired time frame for the meeting. The sender mentions bringing progress notes, planning the next steps for the website launch, and thanks Anna for her efforts.

Overall, the tone is professional and polished, making it suitable for a team meeting or project discussion.

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
  **App** (sela-2, sela_chat): If you want to explore a city, I would recommend visiting New York City. It has so many wonderful places to visit, and there are so many amazing things to see in this city.
- **Nutzer:** Thanks! What food should I try there?
  **App** (sela-2, sela_chat): New York City has so many different food options, it's hard to choose just one. You can try any of the New York City restaurants listed here. They all have amazing food that you should definitely try.

### en54 (multi_turn)
- **Nutzer:** My name is Sam.
  **App** (engramm, learned): Hi Sam, nice to meet you! I'll remember your name.
- **Nutzer:** What is my name?
  **App** (engramm, answer): Your name is Sam.

### en55 (multi_turn)
- **Nutzer:** Can you help me write a birthday card for my mother?
  **App** (sela-2, sela_chat): Here's a simple birthday card template you can use to make your mother proud:

**Birthday Card Template**

1. Write her name and birth date in the top right hand corner of the card.
2. Include the following information: her name, birthday, place she was born (a country), birthdate, birth year, age at the time of birth.
3. Add a small photo or picture of her at home.
4. Include her name and birthdate on the bottom left side of the card.
5. Include a note that says "Dear Mom/ Dad, I am writing to share my birthday with you."
6. Add a personal message by typing it into the top right side of the card.
7. Double-check the spelling of each word to ensure accuracy.
8. Print the card and mail it to her home.
9. Send it by post or phone if you prefer.
- **Nutzer:** Make it a bit shorter, please.
  **App** (sela-2, sela_chat): Here's a shorter version of the birthday card template:

**Birthday Card Template**

1. Write her name and birth date in the top right corner of the card.
2. Include the following information: her name, birth date, place she was born (a country), birth year, age at the time of birth.
3. Add a small photo or picture of her at home.
4. Include her name and birthdate on the bottom left side of the card.
5. Include a note that says "Dear Mom/ Dad, I am writing to share my birthday with you."
6. Print the card and mail it to her home.
7. Send it by post or phone if you prefer.

### en56 (multi_turn)
- **Nutzer:** I feel a bit stressed today.
  **App** (sela-2, sela_chat): It's normal to feel stressed when life gets busy. It can be due to work, family responsibilities, or other pressures that take up a lot of your time. Try taking some time for yourself, whether it's reading, meditating, or simply taking a few deep breaths. This will help you relax and reduce your stress levels.

Remember that it's okay to not have all the answers right now. You don't need to face every problem alone. Reach out to friends, family, or a therapist who can offer support and guidance. Talking through your feelings with someone you trust can also help you process your emotions and gain a better understanding of what's causing your stress.

Take care of your physical health today by getting enough sleep, eating well, and exercising regularly. You might also consider talking to a mental health professional about your stress levels and how they're impacting your daily life.
- **Nutzer:** What can I do to relax this evening?
  **App** (sela-2, sela_chat): To relax this evening, try some of the following activities:

Take a few deep breaths and focus on your breath. This will help calm your mind and body. You can also try some relaxing music or nature sounds to get you started. If you have time, you could listen to soothing classical music or nature sounds.

Try some gentle stretching exercises. Stretching stretches can help reduce muscle tension and improve flexibility. You can find plenty of stretch videos online, and some people also use foam rolling or foam rolling blocks to do this at home.

If you're feeling stressed, try some relaxation techniques such as progressive muscle relaxation, which involves tensing and relaxing different muscle groups in your body. You can also try mindfulness meditation, which involves focusing on the present moment without judgment.

Another option is to use relaxation techniques like meditation or yoga. These practices can help you manage stress and anxiety by releasing tension in your body and mind.

Finally, consider doing something you enjoy, like reading, drawing, or listening to music. These activities can help you unwind and relax, even if you're not physically able to do them right away.

### en57 (multi_turn)
- **Nutzer:** What is a good houseplant for beginners?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.
- **Nutzer:** How often should I water it?
  **App** (sela-2, sela_chat): The frequency of watering will depend on the type of plants you are growing and the amount of water they require. However, most plants will need at least one to two liters of water per day.

For plants that grow in warmer climates or those with drought-tolerant plants, it is recommended to water them less frequently. These plants may need more water than other types of plants because they are adapted to more frequent rainfall patterns.

Additionally, plants that are naturally drought-resistant can also be watered less frequently. This is because they have a natural tolerance for water scarcity.

It is important to note that different plants require different amounts of water. For example, some plants prefer more water when they are stressed or under stress, while others prefer less water when they are not under stress.

### en58 (multi_turn)
- **Nutzer:** Tell me a fun fact about cats.
  **App** (engramm, about): Here's one about cats: Cats are commonly kept as house pets but can also be farm cats or feral cats; the feral cat ranges freely and avoids human contact.
- **Nutzer:** And one about dogs?
  **App** (engramm, unknown): I don't know — I haven't read anything that answers that.

### en59 (multi_turn) – cut_off
- **Nutzer:** I want to start reading more books.
  **App** (engramm, learned): Sounds good! What made you decide that?
- **Nutzer:** Any tips for finding time to read?
  **App** (sela-2, sela_chat): The most important thing to do is not spend too much time on reading. When you are sitting down and read, you should do something else like watch a movie or listen to music. The best way to make sure you get enough time to read is by setting an alarm clock. It will wake up your brain and give you the time to do something.

Another way is to set a goal to read for a certain amount of time every day. This can be as simple as going for a walk outside. After a few days, it will become easier to read. If you want to keep reading, try to set aside at least 20-30 minutes each day.

It is also important to consider other ways to stay motivated. For example, if you have a long commute or work, you can find a quiet place to sit down and read. You can also try writing down notes in your journal. These can be very useful when you need to reflect on your day.

Finally, try to make time for exercise. Exercise helps your body burn calories and improve your energy levels. Try to do some kind of physical activity every day.
- **Nutzer:** Great, thank you!
  **App** (sela-2, sela_chat): You're welcome! Enjoy your reading and stay motivated.

### en60 (multi_turn)
- **Nutzer:** Can you explain what a recipe is?
  **App** (sela-2, sela_grounded): A recipe is a set of instructions that describes how to prepare or make something, especially a dish of prepared food [1].
- **Nutzer:** Now give me a very simple recipe for a sandwich.
  **App** (engramm, learned): Now! It was made by Sky Group. What made you think of it?

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
  **App** (sela-2, sela_chat): Ich bin eine KI: Sela, ein kleines Sprachmodell aus dem ENGRAMM-Projekt. Ein Mensch bin ich nicht, aber ich helfe gern.

### de08 (identity)
- **Nutzer:** Wobei kannst du mir helfen?
  **App** (sela-2, sela_chat): Ich kann dir helfen, indem ich dir:  
1. **Beispiele** helfe (z. B. in Python oder Java)  
2. **Anweisungen** bereitstelle, um ein Problem zu lösen (z. B. in der Praxis)  
3. **Implementierung** deiner Projekte durch Code-Beispiels (z. B. für eine Frage wie „Wie gehe ich mit einem Texteditor in Python?“)  

Du kannst einfach deinen Text auf Deutsch senden und mir dann eine Antwort schreiben – ich passe mich gerne an!

### de09 (instruction) – cut_off
- **Nutzer:** Gib mir drei Tipps, wie ich besser schlafen kann.
  **App** (sela-2, sela_chat): 1. **Erwachsene Ruhe** – Du kannst dein Bett nicht sofort verlassen, bevor du eine Nacht schläfst. Die meisten Menschen brauchen länger, um sich wiederzusehen. Vermeide es, zu frühstücken oder vor dem Schlafengehen einen Spaziergang zu machen.
2. **Freiheit und Energie** – Schlaf ist der wichtigste Faktor für das Wohlbefinden. Verwende ein gutes Buch, eine ruhige Musik oder ein Blatt Papier, damit du dich nicht aus dem Schlaf schaukst. Wenn du in deiner Wohnung bist, verwende den Raum, in dem du schlafen kannst.
3. **Körperliche Aktivität** – Der Körper braucht Bewegung, um Energie zu tanken. Eine kurze Spazierfahrt, ein Spaziergang in der Natur oder eine Sportart wie Jogging oder Schwimmen können helfen. Auch kleine Schritte wie beim Lesen oder die Nutzung von Apps wie Headspace können deinen Tag besser machen.
4. **Dein Zuhause und deine Umgebung** – Stelle sicher, dass du aufpassen wirst, was du mit deinem Bett und der Umgebung machst. Nutze deinen Raum, um sich abzulenken und deine Sorgen zu vergessen.
5.

### de10 (instruction) – cut_off
- **Nutzer:** Erkläre in einfachen Worten, was Strom ist.
  **App** (sela-2, sela_chat): Strom ist die Energie, die durch die Bewegung von elektrischen Gleichmolekülen (z. B. Wasserstoff oder Sauerstoff) erzeugt wird. Es gibt zwei Arten von Strom: **abstrakte** und **geometrische**.

---

### **abstrakte Stromquelle**
Wenn ein Stoff elektrische Kräfte aufnimmt und dabei seine Position ändert, wird er als **abstraktes Strom** bezeichnet. Beispielsweise braucht ein Elektroschrott eine Kraft, um sich zu bewegen – wie bei einem Kohlekraftwerk! Wenn ein Strom in einer solchen Maschine fließt, entsteht Wärme, die mit der Kraft des Elektrons verbunden ist. Da die Elektronen nur eine bestimmte Richtung annehmen (gerade), wird der Strom als **geometrisch** angesehen.

---

### **geometrische Stromquelle**
Wenn ein Stoff elektrische Kräfte aufnimmt, aber seine Position ändert, wird er als **geometrische Strom** bezeichnet. Dies geschieht durch den Übergang zwischen einer **abstrakten** und einer **geometrischen** Form. Ein Beispiel ist die Energiegewinnung durch Elektronentransport durch Oxidation von Wasser.

### de11 (instruction)
- **Nutzer:** Schreib eine kurze Nachricht an meine Kollegin, dass ich heute später komme.
  **App** (sela-2, sela_chat): Hallo! Ich bin heute um 11 Uhr komme und freue mich darauf, mit Ihnen zu sprechen. Willkommen!   

Ich habe schon eine Tasse Kaffee und einen kleinen Kuchen für Sie zusammengestellt. Sollten Sie weitere Fragen haben oder wünschen, lassen Sie es mich wissen!   

Mit freundlichen Grüßen,  
[Ihr Name]  

**Hinweis:** Die Nachricht sollte gut lesbar sein und mindestens 2 Absätze enthalten.

### de12 (instruction)
- **Nutzer:** Nenne vier Gemüsesorten, die im Herbst geerntet werden.
  **App** (sela-2, sela_chat): Die vier Gemüsesorten, die im Herbst geerntet werden, sind:

1. Tomaten (Basil)
2. Paprika (Zucchini)
3. Zwiebel (Nelken)
4. Knoblauch (Karpfen)

### de13 (instruction) – cut_off
- **Nutzer:** Wie koche ich Nudeln richtig?
  **App** (sela-2, sela_chat): Um Nudeln richtig zu kochen, ist es wichtig, den Teig richtig zu verarbeiten. Hier sind einige Tipps:

1. **Röhren entfernen**: Füllen Sie die Nudel mit einer dünnen Schicht Mehl und röhren Sie sie nach unten, bis der Teig sich herausfilzt. Dies ist nötig, da der Teig dann zu schwer wird.
2. **Räucher trockenlegen**: Lassen Sie den Teig trocken, um ihn nicht zu kochen oder zu verlieren. Nach dem Rühren sollten die Nudel sanft auf eine beschichtete Fläche gelegt werden.
3. **Nudel in kleine Stücke schneiden**: Schneiden Sie die Nudel gleichmäßig auf einen flachen Kuchengitter. Dieser macht es einfacher, den Teig aufzulösen und gleichzeitig die Nudel zu färben.
4. **Röhren abkühlen lassen**: Rufen Sie den Ofen auf 250°C (257°F) vor. Der Teig sollte nun glasig sein, aber leicht klebrig sein.
5. **Nudel in kleinere Stücke schneiden**: Fetten Sie die Nudel in kleine Stücke, z.

### de14 (instruction)
- **Nutzer:** Was ist der Unterschied zwischen einem Fluss und einem See?
  **App** (sela-2, sela_chat): Der Unterschied zwischen einem Fluss und einem See besteht darin, wie sie über Wasser laufen. Flusslauf ist die Bewegung von Wasser durch den Grund eines Körpers (z. B. ein Fluss), während Seelauf die Bewegung des Wassers durch die Landschaft oder das Land selbst. 

Ein Fluss kann sich in einen Flusslauf verwandeln, indem er Wasser bewegt, das für einen längeren Zeitraum an einem Ort vorbeizieht, bevor es wieder zurückfließt. Ein See hingegen kann nicht mehr so leicht zu werden, da es sich ständig weiter dreht und sich im Laufe der Zeit immer wieder ändert. 

Das Unterschied liegt hauptsächlich in der Geschwindigkeit, mit der sich das Wasser bewegt. Flüsse bewegen sich schneller als Seen, da sie ihre Bewegung vor allem durch Wellen beschleunigen. In Seen wird die Bewegung jedoch viel langsamer beschleunigt, was bedeutet, dass die Wellen nicht mehr die gleiche Wirkung auf die Oberfläche haben wie beim Fluss. 

In der Regel fließt Wasser langsamer als beim See, weil der Druck innerhalb der Wassermenge geringer ist. Da der Druck immer größer wird, steigt der Wassertropfen aufgrund seiner höheren Druckbelastung stärker an und zieht mehr Luft an, wodurch die Wellen auch schneller werden.

### de15 (instruction) – cut_off
- **Nutzer:** Schreib ein kurzes Gedicht über den Winter.
  **App** (sela-2, sela_chat): **Wintergarten**  

Der Winter, ein Hauch von Weizen in der Luft,  
der die Felder des Regenwaldes ausweicht,  
die Blätter wie Sprossen in einem Duft, der wie Eis kalt ist.  
Er hängt herab vom Schnee, den er nicht mehr tragen kann,  
und lacht sich über die Stille, die das Leben trägt.  

In der Dunkelheit leuchtet der Wind, ein Lied,  
als würde er den Himmel von einem tiefen Schlaf,  
den die Sterne ihn nicht mehr sehen konnten.  
Die Bäume sind voller Blätter, die in den Herbstregen schlüpfen,  
und die Äpfel singen nur noch die Erinnerung an die Nacht.  

Doch Winter braucht etwas, das ihn nicht einfach wegnehmen kann:  
ein Gefühl, dass etwas fehlt, dass nicht der Winter ist.  
Ein Gedicht, das sagt: *„Winter ist kein Weg, sondern ein Spiegel.“*  

---

**Übersetzung ins Englische:**  
"In den Wolken schimmert das Licht der Welt.

### de16 (instruction)
- **Nutzer:** Wie kann ich im Haushalt Energie sparen?
  **App** (sela-2, sela_chat): Um im Haushalt Energie sparen zu können, ist es sinnvoll, die Haushaltsgeräte einzuschalten. Dies kann auch durch eine Energieeffizienz-Karte erfolgen, bei der Sie die Stromverbrauchswerte per Smartphone oder anderen App sehen können. Zudem sollten Sie Energieeffizienzprodukte wie z. B. Energy Star-Tester einsetzen, um den Wirkungsgrad Ihrer Haushaltsgeräte zu messen.

Ein weiterer Weg zur Energieersparnis ist die Nutzung erneuerbarer Energien wie Solar-, Wind-, Wasserkraft- oder Solarenergie. Diese können direkt in die Haushalte eingebaut werden und benötigen minimal Energie. Zudem ist es wichtig, die Fenster zu öffnen und den Energieverbrauch beim Hausbau zu reduzieren, da viele Energieverbrauchswerte per Lichtreflex berechnet werden.

Zusätzlich können Sie die Nutzung von klimafreundlichen Komponenten wie Klimaanlagen, Wärmekraftwerken und solarthermischen Systemen nutzen, die sich aus erneuerbaren Quellen erwärmen lassen. Zudem können Sie einen kleinen Solarstromer verwenden, der nur über das Hausnetz betrieben wird.

Zusammenfassend können Sie Ihre Energieverbrauch und Energieeffizienz erheblich senken und langfristig Kosten sparen.

### de17 (instruction) – cut_off
- **Nutzer:** Was sollte ich zu einem Vorstellungsgespräch mitnehmen?
  **App** (sela-2, sela_chat): Ich empfehle, vor dem Gespräch folgende Dinge zu beachten:
1. **Fragen stellen**: Fragen Sie nach den Vorstellungen, die Sie benötigen, um Ihre Fähigkeiten und Erfahrungen im Unternehmen zu zeigen.
2. **Vorbereitung**: Nachfragen Sie sich über das Unternehmen, die Rolle und die Zielgruppen, die Sie interessieren.
3. **Tipps fürs Gespräch**: Beginnen Sie mit einer Einleitung (z. B. „Wie möchten Sie heute Ihr Unternehmen beschreiben?“), gefolgt von einem Gespräch mit Ihnen und dem Unternehmensberater.
4. **Gute Körpersprache**: Vermeiden Sie nervöse oder gestörte Gesichtszüge, um Aufmerksamkeit zu gewinnen.
5. **Zeugenaussage**: Sie sollten mindestens zwei Beispiele nennen, die Sie besonders auffällig zeigen.
6. **Logik & Fakten**: Nutzen Sie typische Interview-Logik wie „Sie können uns das auch erzählen.“
7. **Kleidung & Etikette**: Achten Sie auf eine sensible Kleidung und Etikette, die Sie tragen können, um Vertrauen aufzubauen.
8. **Fokus auf Stärken**: Erwähne Ihre besonderen Fähigkeiten und Erfahrungen im Unternehmen.
9.

### de18 (rewrite) – echo
- **Nutzer:** Formuliere das höflicher: „Gib mir sofort die Unterlagen.“
  **App** (sela-2, sela_chat): Gib mir sofort die Unterlagen.

### de19 (rewrite)
- **Nutzer:** Korrigiere die Fehler: „Ich habe gestern ins Kino gegangen und der Film war sehr gut gewesen.“
  **App** (sela-2, sela_chat): Das Problem ist, dass die Phrase „Ich habe gestern ins Kino gegangen“ in der ursprünglichen Version falsch war. Die Satzkonstruktion wurde angepasst, um den Fehler zu vermeiden:

**„Ich habe heute ins Kino gegangen.“**  
- Das „Ich“ sollte sich auf einen Gegenstand beziehen (z. B. „Ich habe heute ins Kino gegangen“).  
- Die ursprüngliche Formulierung „war sehr gut gewesen“ wurde korrekt korrigiert, da sie „sehr gut gewesen“ verwendet, nicht „gut gehabt“.  

**Korrigierte Version:**  
„Ich habe heute ins Kino gegangen.“  
- Das „Ich“ wurde als Objekt des Verbs „gegangen“ verwendet, um den Fokus darauf zu legen, dass das Filmfestival erfolgreich war.  

**Erklärung:**  
Die Korrektur wurde durch die Wiederholung von „war sehr gut gewesen“ und die Konjugation „die ich habe ins Kino gegangen“ verbessert, um die Lesbarkeit zu erhöhen.

### de20 (rewrite)
- **Nutzer:** Mach diesen Satz einfacher: „Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“
  **App** (sela-2, sela_chat): Hier ist eine vereinfachte Version des Satzes:  
**„Aufgrund der ungünstigen Witterungsverhältnisse wurde die Veranstaltung abgesagt.“**  

### Begründung:  
1. **Strukturierung**: Der Satz ist in zwei Teile geteilt, um den Fokus auf das Problem (Wetter) zu legen. Der erste Satz enthält die Ursache (Ungünstigkeit), der zweite Satz beschreibt die Folge (Verzögerung). Die Übergänge zwischen diesen beiden Teilen sind hier klar und einfach.  
2. **Klarheit**: „Ungünstige Witterungsverhältnisse“ ist präziser als „ungünstig“. Es wird ein allgemeineres Bild vermittelt, das für viele Leser verständlich ist.  
3. **Einschränkung**: „abgesagt“ bleibt erhalten, da die Entscheidung über die Maßnahme nicht direkt genannt wird. Sie könnte durch „ausschließlich abgesagt“ oder „unter Ausnahme“ ausgedrückt werden, um die Verantwortung klarer zu definieren.  
4. **Effizienz**: Der Satz ist kürzer und flüssiger, da die Verknüpfung von Ursache und Folge bereits im zweiten Satz erfolgt.

### de21 (rewrite)
- **Nutzer:** Schreib diesen Satz in der Vergangenheit: „Ich gehe in den Park und lese ein Buch.“
  **App** (sela-2, sela_chat): Der Satz lässt sich in eine Vergangenheit stellen, indem er die Handlung des Romans beschreibt. 

**Zitat:**  
„Ich gehe in den Park und lese ein Buch.“  

Diese Zeile verbindet die Vergangenheit mit der Gegenwart und stellt die Gegenwart als Kontext dar. Sie wurde von „Ich“ verwendet, um zu signalisieren, dass die Geschichte in Zukunft stattfindet.

### de22 (rewrite)
- **Nutzer:** Formuliere das förmlicher: „Hey, kann morgen leider nicht, sorry!“
  **App** (sela-2, sela_chat): Das förmliche: **"Hey, kann morgen leider nicht, sorry!"**

### de23 (summarize)
- **Nutzer:** Fasse in einem Satz zusammen: „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln und belastet die Gelenke wenig. Außerdem verursacht es keine Abgase und ist in der Stadt oft schneller als das Auto.“
  **App** (sela-2, sela_chat): „Fahrradfahren ist gut für die Gesundheit. Es stärkt Herz und Muskeln, belastet die Gelenke wenig und ist in der Stadt oft schneller als das Auto.“

**Erklärung:**  
- „Fahrradfahren“ wird durch den intensiven Einsatz von Kraft (z. B. Kurbelwelle) ersetzt, um körperliche Anstrengungen zu reduzieren.  
- „Sauerstoffmangel“ wird durch den hohen Schadstoffgehalt der Luft verstärkt, was zu einer besseren Atemfunktion führt.  
- „Füße“ und „Auto“ werden im Satz durch die Verwendung des abgrenzbaren Adverbiums „aber“ betont, um die Unterschiede zwischen Fahrradfahrzeugen und Autoautos klar zu machen.

### de24 (summarize)
- **Nutzer:** Fasse diese Nachricht zusammen: „Hallo zusammen, das Treffen am Freitag fällt aus, weil der Raum belegt ist. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas“
  **App** (sela-2, sela_chat): Hallo zusammen, das Treffen am Freitag fällt aus. Wir verschieben es auf Montag um 10 Uhr. Bitte bringt eure Ideen für das Sommerfest mit. Viele Grüße, Jonas.“

### de25 (summarize) – cut_off
- **Nutzer:** Worum geht es in diesem Text? „Im Herbst ziehen viele Zugvögel in den Süden. Sie fliegen oft Tausende Kilometer, um in wärmeren Gebieten genug Nahrung zu finden. Im Frühling kehren sie zurück, um zu brüten.“
  **App** (sela-2, sela_chat): Der Text beschreibt eine typische Zugvögel-Besuch in Südamerika. Es handelt sich um einen **dramatischen Wanderweg**, der über mehr als zwei Jahrzehnte erstreckt und durch zahlreiche klimatische Bedingungen geprägt ist. Der Text betont, dass die Vögel nicht nur für ihre Nahrung sorgen, sondern auch über die Region verfügen, um dort ein neues Zuhause zu finden. Im Frühling kehren sie zurück, um wieder ihre Familien zu schließen und in wärmeren Gebieten Nahrung zu finden. Gleichzeitig wird deutlich, wie stark der Weg durch die Umwelt beeinflusst ist: Die Vögel spüren die Abkühlung in ihrer Umgebung, und viele bleiben zurück, um zu brüten.

### Änderungen & Verbesserungen:
1. **Strukturierung**: Der Text wurde in klarere Abschnitte unterteilt, um die Lesbarkeit zu verbessern.  
   - **Kürzere Sätze**: Die Hauptteil des Textes wird in kürzeren Sätzen geteilt (z. B. „In den Herbst ziehen viele Zugvögel“ → „Im Frühjahr zieht viele Zugvögel“).  
   - **Prägnanz**: Wiederholungen („Im Sommer“) wurden reduziert oder durch Synonyme ersetzt („unter anderem“ statt „unter anderem“).

### de26 (summarize)
- **Nutzer:** Fasse kurz zusammen: „Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“
  **App** (sela-2, sela_chat): **Lisa wollte schwimmen lernen. Anfangs hatte sie Angst vor dem tiefen Wasser. Sie übte jede Woche mit einer Trainerin. Nach einem Sommer konnte sie eine ganze Bahn ohne Pause schwimmen.“

### de27 (summarize)
- **Nutzer:** Fasse in zwei Sätzen zusammen: „Die Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“
  **App** (sela-2, sela_chat): **Stadt baut einen neuen Radweg entlang des Flusses. Er soll Pendler sicherer zur Arbeit bringen und den Autoverkehr in der Innenstadt verringern. Die Bauarbeiten beginnen im März und dauern etwa acht Monate.“  

**Die Bauarbeiten beginnen im März und dauern etwa acht Monate.**  
**Der neue Radweg ist geplant, um die Verkehrslast in der Innenstadt zu verringern und die Fahrradfreundlichkeit in der Innenstadt zu verbessern.**

### de28 (grounded)
- **Nutzer:** Wie hoch ist die Zugspitze?
  **App** (sela-2, sela_grounded): 2,962 metres (9,718 ft) [1].

### de29 (grounded) – wrong_language
- **Nutzer:** Welches bekannte Werk schrieb Goethe?
  **App** (sela-2, sela_chat): Goethe schrieb das Werk "Der Sturm", in dem er die Geschichte eines kleinen Jungen erzählt, der auf einer Insel lebt.

### de30 (grounded)
- **Nutzer:** Wo mündet der Rhein?
  **App** (sela-2, sela_chat): Der Rhein mündet in der Provinz Rhein-Neuss in Deutschland. Er fließt durch die kreisförmige Region (Nord, Ost und Süd) und mündet schließlich in den Rhein, der über ein linkes Ufer im Süden verläuft.

**Erläuterung:**  
- **Basisdaten:** Der Rhein entspringt in der Provinz Rhein-Neuss am Rande der Provinz Nordrhein-Westfalen.  
- **Verlauf:** Der Rhein fließt durch den Bundesländer Rheinland-Pfalz, Saarland, Sachsen-Anhalt, Brandenburg und Hessen.  
- **Geografie:** Der Rhein ist der zweitlängste Fluss Europas und die längste Flachwasserstraße auf dem deutschen Festland.  

**Zusammenfassung:**  
Der Rhein mündet in den Rhein, der dann in den Rhein mündet. Die Gesamtlänge des Flusses beträgt etwa 390 km.

### de31 (grounded)
- **Nutzer:** Wie tief ist der Gardasee?
  **App** (engramm, unknown): Das weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.

### de32 (grounded)
- **Nutzer:** Wofür erhielt Einstein den Nobelpreis?
  **App** (sela-2, sela_chat): Einstein erhielt den Nobelpreis für Physik im Jahr 1921, als er eine Veröffentlichung über die theoretische Physik veröffentlichte. Die Veröffentlichung enthielt Beiträge zur Relativitätstheorie und zu Quantenmechanik. Der Preis wurde an ein Wissenschaftler-Team verliehen, das sich auf die Entwicklung neuer Technologien konzentrierte. Einstein gehörte damit zu einer Gruppe von Wissenschaftlern, die sich für die Erforschung der Naturwissenschaften einsetzen wollten.

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
  **App** (sela-2, sela_chat): Hier ist ein Beispiel für einen Kuchen, der am Wochenende backen kann:

**Zutaten**:  
- 200 g Mehl  
- 1 TL Salz  
- 1 EL Zucker  
- 500 g Zuckerrüben  
- 3 Eier  
- 50 ml Milch (z. B. Quark oder Backwaren)  
- 100 g Mehl  
- 2 Eier  
- 1 EL Butter  
- 10 ml Wasser (z. B. Milch oder Joghurt)  

**Höhepunkt des Kuchens**:  
- 10 cm Durchmesser  
- 12 cm Länge  
- 20 cm Durchmesser  
- 35 cm Durchmesser  

**Restliche Zutaten**:  
- 250 g Butter (oder Joghurt)  
- 150 g Mehl  
- 5 Eier  
- 1 Eiweiß  
- 3 Eier  
- 50 ml Milch (z. B. Quark oder Backwaren)  
- 80 g Milch  
- 50 ml Milchpulver (oder Schokolade)  

**Backenschritte**:  
1.
- **Nutzer:** Welcher Kuchen ist einfach?
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der **Kuchen-Käse-Brot** aus Mehl, Salz und Zucker. Dieser wird direkt auf dem Teller gebacken, ohne eine zusätzliche Zutatenliste.

**Zutaten**:  
- 200 g Mehl  
- 1 TL Salz  
- 1 EL Zucker  
- 50 ml Milch (z. B. Quark oder Backwaren)  
- 100 g Mehl  
- 10 ml Milchpulver (oder Schokolade)  

**Backenschritte**:  
1.
- **Nutzer:** Danke, das probiere ich!
  **App** (sela-2, sela_chat): Der einfachste Kuchen ist der **Kuchen-Käse-Brot** aus Mehl, Salz und Zucker. Dieser wird direkt auf dem Teller gebacken, ohne eine zusätzliche Zutatenliste.

**Zutaten**:  
- 200 g Mehl  
- 1 TL Salz  
- 1 EL Zucker  
- 50 ml Milch (z. B. Quark oder Backwaren)  
- 100 g Mehl  
- 10 ml Milchpulver (oder Schokolade)  

**Backenschritte**:  
1.

### de37 (multi_turn) – cut_off
- **Nutzer:** Ich lerne gerade Englisch.
  **App** (sela-2, sela_chat): Natürlich! Ich helfe Ihnen gerne bei der Grammatik, Rechtschreibung, Zeichensetzung oder sogar in der Aussprache von Texten. Möchten Sie sich Tipps zu einem bestimmten Thema zukommen lassen? Oder etwas über die Bedeutung von bestimmten Begriffen erfahren?
- **Nutzer:** Wie kann ich meinen Wortschatz verbessern?
  **App** (sela-2, sela_chat): Um deinen Wortschatz zu verbessern, können Sie verschiedene Methoden anwenden. Beginnen Sie mit der **Strukturierung** – indem Sie die Struktur eines Satzes analysieren, z. B. durch den Fokus auf einen bestimmten Satzabschnitt oder das Aufbau von Satzstruktur (z. B. mit Doppelpunkten). Dies hilft, Grammatik und Rechtschreibung korrekt zu korrigieren.

Weitere Strategien sind **Klarheit**, **Kürzlichkeit** und **Reihenfolge**. Hier sind einige Beispiele für ausgewählte Ansätze:

- **Struktur:** Nutzen Sie eine klare Einleitung, eine Hauptteil und eine Schlusszeile.
- **Klarheit:** Nutzen Sie Absätze, Überschriften und kurze Sätze.
- **Kürzlichkeit:** Nutzen Sie prägnante Formulierungen und einfache Satzstruktur.
- **Reihenfolge:** Nutzen Sie abschließende Sätze oder abschließende Wörter, um die Reihenfolge klar zu machen.

Teilen Sie Ihre Arbeit in kleine Abschnitte, um die Klarheit zu erhöhen. Verwenden Sie unterschiedliche Stilrichtungen (z. B. formal vs. informal) und arbeiten Sie an verschiedenen Stilarten (z. B. Informal vs. Informal).

### de38 (multi_turn)
- **Nutzer:** Kannst du mir helfen, eine Einladung zu schreiben?
  **App** (sela-2, sela_chat): Ich helfe gerne! Bitte lass mir bitte wissen, was du möchtest. Gib mir den Namen und das Alter des Schreibers oder einen anderen Hinweis dazu. Ich kann dir auch helfen, deinen Text zu bearbeiten, um ihn präziser und flüssiger zu gestalten. Wenn du unsicher bist, wie ich dir helfen soll, sag einfach, ob du etwas anderes benötigst oder etwas Besonderes in deinem Schreiben möchtest.
- **Nutzer:** Es ist eine Geburtstagsfeier am Samstag um 18 Uhr.
  **App** (sela-2, sela_chat): Natürlich! Ich helfe dir gerne dabei, deinen Text zu bearbeiten, um ihn klar und flüssig zu gestalten. Bitte sag einfach, was du möchtest, damit ich dir helfen kann. Ich kann dir auch helfen, die Länge deines Textes zu verbessern, um ihn prägnanter zu gestalten. Falls du etwas Besonderes in deinem Text benötigst, lass mir einfach wissen, wie du es möchtest.

### de39 (multi_turn) – cut_off
- **Nutzer:** Was ist ein gutes Hobby für den Winter?
  **App** (sela-2, sela_chat): Ein gutes Hobby für den Winter ist ein Hobby, das du in der Freizeit oder im Sommer betrieben hast. Manchmal geht es darum, eine Leidenschaft zu finden, die man mit der Zeit aufgearbeitet hat. Ein gutes Hobby kann zum Beispiel eine Art von Musikhören sein, bei dem man mit Freunden spielt, um eine bestimmte Stimmung zu erzeugen.

Ein weiteres Hobby ist ein Lieblingsspielzeug. Ein beliebtes Spielzeug ist z.B. das Spielzeug "Schwerpunkt" oder ein Spielzeug namens "Nintendo Switch". Letztere sind alle beliebten Geräte für das Hobby.

Ein Hobby ist auch ein Hobby, wenn es etwas Besonderes ist, das du regelmäßig machst. Ein gutes Hobby kann zum Beispiel ein besonderes Kleidungsstück sein, das du ständig wechseln kannst. Solche Kleidungsstücke können zum Beispiel eine besondere Jacke oder ein neues Kleidungsstück enthalten.

Ein weiterer Vorteil des Hobbyes ist die Möglichkeit, neue Fähigkeiten zu erlernen. Wenn man ein Hobby liebt, lernt man schnell und lernt viel über das Hobby. Ein gutes Hobby kann dann zu einem hervorragenden Beruf werden.
- **Nutzer:** Und was kostet das ungefähr?
  **App** (sela-2, sela_chat): Ein Hobby kann ungefähr zu einem Preis von etwa $50 bis $100 liegen. Eine gute Idee ist, dass du es gut machst und mit deiner Familie zusammen sprichst.

### de40 (multi_turn)
- **Nutzer:** Erzähl mir etwas über Pinguine.
  **App** (sela-2, sela_grounded): Pinguine sind eine der größten und bekanntesten Arten der Vögel [1].
- **Nutzer:** Können Pinguine fliegen?
  **App** (sela-2, sela_chat): Pinguine fliegen nur mit Hilfe des Fisches, dem Pinguin [1].

