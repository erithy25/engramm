"""Everyday moments told in one sentence, by frame instead of by sentence.

"my laptop just crashed", "i burned my hand while cooking", "we adopted a cat yesterday", "i booked a trip to
iceland" — a short list of sentence frames (who did what to what) picks the kind of moment and the words to
echo back; the replies themselves live in data/conv/daily.yaml (`moments`, `moments_de`). These frames run only
after every specific flow has passed, so a moment with its own follow-ups keeps them; what they replace are the
generic "Tell me more?" and a moment stored as a fact ("I'll remember that about your cat")."""
from __future__ import annotations

import re

_TECH = r"phone|laptop|computer|pc|screen|tablet|tv|console|headphones|printer|router|wifi|internet|keyboard|mouse|iphone|ipad|mac|macbook|playstation|xbox|camera"
_VEHICLE = r"car|bike|scooter|motorbike|motorcycle|van|e-bike"
_PET = r"cat|kitten|dog|puppy|rabbit|bunny|hamster|guinea pig|parrot|bird"
_KID = r"daughter|son|baby|little one|kid|toddler|little girl|little boy"
_FAM = r"grandma|grandpa|granny|grandmother|grandfather|mom|mum|mother|dad|father|aunt|uncle|sister|brother|wife|husband|partner|friend|best friend|neighbou?r"

EN: list[tuple[str, re.Pattern]] = [(k, re.compile(rx)) for k, rx in [
    ("pet_mischief", rf"(?:my|our) (?P<w>{_PET}) (?:just )?(?:knocked over|broke|ate|chewed(?: up)?|destroyed|stole|scratched|ripped) (?:a |my |the |our |some )?(?P<o>[a-z ]{{2,25}}?)(?: again| today| this morning)?"),
    ("damage_tech", rf"(?:my|our|the) (?P<o>(?:new |old )?(?:{_TECH})(?: screen)?) (?:just |has |is )?(?:broke|is broken|crashed|died|stopped working|cracked|froze|won'?t turn on|got (?:wet|stolen|damaged))(?: again| today| this morning| on me)?(?: and i lost (?:all )?(?:my )?[a-z ]+)?"),
    ("damage_car", rf"(?:my|our|the) (?P<o>(?:new |old )?(?:{_VEHICLE})) (?:just )?(?:broke down|is broken|got (?:stolen|scratched|dented|a flat)|has a flat(?: tyre| tire)?|won'?t start|died)(?: on (?:the|me) [a-z ]+| on the way(?: to [a-z ]+)?| again| today| this morning)?"),
    ("damage_any", r"(?:my|our|the) (?P<o>(?:new |old )?(?:dishwasher|washing machine|washer|dryer|fridge|freezer|oven|stove|microwave|boiler|heater|heating|shower|toilet|sink|kettle|coffee machine|vacuum|vacuum cleaner|hoover|lawnmower|door|window|lock|tap|faucet|washing-machine))(?: just| has)? (?:broke|broke down|is broken|stopped working|died|is leaking|leaks|won'?t (?:start|turn on|close|open)|exploded)(?: again| today| this morning)?"),
    ("spill", r"i (?:just )?(?:spilled|dropped|knocked over|tipped over) (?:my |a |the |some |a glass of |a cup of )?(?P<o>[a-z ]{2,20}?)(?: (?:on|all over) (?:the |my )?(?P<on>[a-z ]{2,20}?))?(?: this morning| today| again| everywhere)?"),
    ("burn", r"i (?:just )?(?:burned|burnt) (?:my )?(?P<o>hand|finger|fingers|arm|tongue|thumb|wrist|mouth)(?: while (?:cooking|baking|ironing|eating)| on (?:the |my |some |a )?[a-z ]{2,20})?"),
    ("sprain", r"i (?:just )?(?:twisted|sprained|rolled) (?:my )?(?P<o>ankle|wrist|knee|foot)(?: today| again| at work| playing [a-z]+| while [a-z ]+)?"),
    ("hurt", r"i (?:just )?(?:fell (?:off|down|over)(?: my| the)?|tripped(?: over| on)?|twisted|sprained|bumped|hurt|banged) (?:my |the |a )?(?P<o>[a-z ]{2,20}?)(?: today| again| this morning| on the way [a-z ]+| at work)?"),
    ("cancelled", r"(?:my|our|the) (?P<o>flight|train|bus|appointment|class|meeting|date|concert|show|game|trip|party|plans?) (?:got |was |were |has been |have been )?(?:cancelled|canceled|delayed|postponed|called off)(?: again| today| last minute)?"),
    ("stuck", r"i (?:just )?got stuck in (?:an |the |a )?(?P<o>elevator|lift|traffic|snow|rain|queue|line)(?: today| for [a-z0-9 ]+)?"),
    ("rent", r"(?:my )?(?:landlord|landlady) (?:just )?(?:raised|increased|put up) (?:the |my )?rent|(?:my )?rent (?:just )?(?:went up|is going up|got raised)"),
    ("project_done", r"i (?:just |finally )?(?:finished|completed|wrapped up|handed in|submitted|delivered|launched) (?:my |a |the |our |that )?(?P<o>(?:big |huge |massive |last |final )?(?:project|thesis|dissertation|essay|paper|report|presentation|assignment|course|degree|exam|exams|portfolio|application|book|novel))(?: at work| today| yesterday| finally)?"),
    ("read_done", r"i (?:just |finally )?finished reading (?P<o>[a-z0-9' ]{3,40}?)(?: today| finally| last night)?"),
    ("race_done", r"i (?:just )?(?:ran|did|finished|completed) (?:my |a |the )?(?P<o>first marathon|marathon|half marathon|10k|5k|triathlon|race|first race)(?: today| yesterday)?"),
    ("passed", r"i (?:just )?(?:passed|aced) (?:my |the )?(?P<o>[a-z ]{2,30}?)(?: test| exam)?(?: today| finally| first time| on the first try)?"),
    ("first_make", r"i (?:just )?(?:baked|made|cooked|built|knitted|sewed|brewed) (?:my |a |an |some |homemade )?(?P<o>[a-z ]{2,25}?)(?: for the first time| at home| myself| all by myself| from scratch| today)+"),
    ("painted", r"i (?:just )?(?:painted|repainted|redecorated|renovated|redid) (?:my |the |our )?(?P<o>bedroom|room|living room|kitchen|bathroom|apartment|flat|house|walls?|office|hallway)(?: (?P<c>[a-z]+))?(?: today| this weekend)?"),
    ("planted", r"i (?:just )?planted (?:some )?(?P<o>[a-z ]{2,25}?)(?: (?:in|on) (?:my|the|our) (?:garden|balcony|yard|backyard|terrace|windowsill))?(?: today)?"),
    ("new_pet", rf"we (?:just )?(?:adopted|got|brought home) (?:a |an |two |our )?(?:new |little |rescue )?(?P<o>{_PET}|cats|dogs|kittens|puppies)(?: yesterday| today| last week| from the shelter)?"),
    ("baby", r"(?:we'?re|we are|i'?m|i am) (?:expecting|having) (?:a baby|our first (?:child|baby)|twins)|we'?re pregnant|(?:my )?(?:wife|girlfriend|partner) is pregnant"),
    ("kid_milestone", rf"my (?P<w>{_KID}) (?:just )?(?:took (?:her|his|their) first steps|said (?:her|his|their) first word|started (?:school|kindergarten|nursery|daycare)|lost (?:her|his|their) first tooth|rode (?:a|her|his) bike)(?: today| yesterday| this morning)?"),
    ("turned", rf"my (?P<w>{_FAM}) (?:just )?turned (?P<n>\d{{1,3}})(?: today| yesterday)?"),
    ("trip_booked", r"i (?:just |finally )?booked (?:a |my |our )?(?:trip|flight|flights|holiday|vacation|tickets?|getaway) (?:to|for) (?P<o>[a-z ]{2,25})"),
    ("going_out", r"(?:i'?m|we'?re|i am|we are) going (?P<o>camping|hiking|skiing|surfing|fishing|to the beach|on holiday|on vacation|to a festival)(?: this weekend| next week| tomorrow| soon| next month)?"),
    ("therapy", r"i (?:just )?(?:started|began) (?:going to )?therapy(?: today| this week)?"),
    ("diet", r"i (?:just )?(?:started|began) (?:a |my )?(?:new )?diet(?: today| this week)?|i'?m (?:on|starting) a diet(?: today)?"),
    ("joined", r"i (?:just )?(?:joined|signed up (?:for|at)|registered (?:for|at)) (?:a |the |my |an )?(?P<o>gym|choir|club|sports club|football team|running club|course|class|language course|dance class|book club)(?: today| this week)?"),
    ("learning", r"i'?m (?:learning|teaching myself) (?:to play )?(?:the )?(?P<o>guitar|piano|violin|drums|ukulele|saxophone|flute|to draw|to paint|to knit|to sew|chess|to swim|to dance)"),
    ("praised", r"my (?:boss|manager|teacher|coach|professor) (?:just )?(?:praised|complimented) (?:my work|me|my presentation|my project)|my (?:boss|manager|teacher) (?:said|told me) i did (?:a )?(?:great|good|amazing) job"),
    ("met_someone", r"i (?:just )?met (?:someone|somebody) (?:new|special|nice|interesting)"),
    ("divorce", r"my (?:parents|mom and dad|mum and dad) are (?:getting (?:a )?divorced?|splitting up|separating)"),
    ("stood_up", r"my (?:friend|date|best friend) (?:didn'?t show up|stood me up|cancell?ed on me|bailed on me)(?: again| today)?"),
    ("neighbour", r"my neighbou?r'?s? (?P<o>dog|dogs|kids|baby|music|parties) (?:barks?|bark|keeps? barking|is|are|keeps?|play|plays) (?:all night|so loud|every night|again|too loud|loud|all the time)?.*"),
    ("lonely", r"i'?ve been feeling (?:really |so |a bit |kind of )?(?:lonely|alone|isolated)(?: lately| recently| these days)?|i feel (?:so |really )?lonely(?: lately)?"),
    ("nervous", r"i'?m (?:so |really |a bit |kind of )?nervous (?:about|for) (?P<o>tomorrow|my exam|the exam|my interview|the interview|my presentation|the presentation|my test|monday|the wedding|my first day)"),
    ("decide_study", r"i (?:can'?t|cannot|don'?t know how to) decide what to study|i don'?t know what to study"),
    ("proud", r"i'?m (?:so |really |very )?proud of myself(?: today)?"),
    ("sunrise", r"i (?:just )?(?:watched|saw) (?:the )?(?P<o>sunrise|sunset)(?: today| this morning| tonight)?"),
    ("plants_dying", r"my (?:house ?)?plants (?:all )?(?:keep dying|died|are dying|are dead|keep dying on me)|all (?:of )?my plants (?:are dying|died|are dead)"),
    ("forgot_bday", rf"i (?:forgot|missed) my (?P<w>{_FAM})'?s? birthday"),
    ("cleaned", r"i (?:just |finally )?cleaned (?:my |the |our )?(?:whole |entire )?(?:apartment|house|flat|room|kitchen|bathroom|place)(?: today)?"),
    ("saving", r"i'?m saving (?:up )?for (?:a |an |my )?(?P<o>[a-z ]{2,25})"),
    ("team_won", r"my (?:team|club) (?:just )?won(?: the| a)? (?P<o>championship|game|match|league|cup|final|title)?"),
    ("wfh_week", r"i'?ve been working from home (?:all|the whole) week"),
    ("sick_week", r"i'?ve been sick (?:all|the whole) week|i was sick (?:all|the whole) week"),
    ("interview", r"i had (?:a |my )?job interview (?:today|this morning|this afternoon|yesterday)"),
    ("interview_future", r"i have (?:a |my )?job interview (?:tomorrow|on monday|next week|later|this afternoon)"),
    ("went_out", r"(?:i|we) went to (?:a |an |the |my |our )?(?P<o>concert|gig|party|wedding|show|game|match|movies|cinema|museum|festival|club|bar|restaurant|funeral|play|musical|comedy show|birthday party|barbecue|bbq)(?: last night| yesterday| on (?:saturday|friday|sunday)| tonight| today| with [a-z ]+)*"),
    ("quit", r"i (?:just )?(?:quit|gave up|stopped) (?:eating |drinking |using )?(?P<o>sugar|alcohol|drinking|coffee|meat|social media|caffeine|soda|junk food|instagram|tiktok|fast food|chocolate)(?: for (?:good|a month|lent))?"),
    ("overslept", r"i overslept(?: again| today| this morning)?(?: and (?:missed|was late for) (?:my |the )?(?P<o>train|bus|meeting|class|flight|appointment|work|school))?"),
    ("back_to_school", r"i'?m thinking (?:about|of) going back to (?:school|university|uni|college)"),
]]

DE: list[tuple[str, re.Pattern]] = [(k, re.compile(rx)) for k, rx in [
    ("pet_mischief", r"(?:meine|mein|unsere|unser) (?P<w>katze|kater|hund|welpe|kaninchen|hamster) hat (?:eine |einen |ein |meine |meinen |mein |die |den |das )?(?P<o>[a-zäöüß ]{2,25}?) (?:umgeworfen|kaputt gemacht|zerbissen|gefressen|zerkratzt|geklaut|runtergeworfen|zerstört)"),
    ("damage_tech", r"(?:mein|meine|unser|unsere|der|die|das) (?P<o>handy|handydisplay|display|laptop|computer|rechner|pc|bildschirm|tablet|fernseher|router|wlan|drucker|kopfhörer|iphone|ipad|macbook|tastatur) (?:ist |sind |hat )?(?:gerade |schon wieder |einfach )?(?:kaputt|abgestürzt|gesprungen|kaputtgegangen|ausgefallen|eingefroren|nass geworden|geklaut worden|tot)(?: gegangen)?(?: und (?:meine|die) arbeit ist weg| und alles ist weg)?"),
    ("damage_car", r"(?:mein|meine|unser) (?P<o>auto|fahrrad|rad|roller|motorrad|e-bike) (?:ist |hat )?(?:auf der autobahn |unterwegs |heute |schon wieder )?(?:liegen geblieben|kaputt|geklaut worden|gestohlen worden|einen platten|nicht angesprungen|springt nicht an)"),
    ("spill", r"ich (?:hab|habe) (?:gerade |eben |heute )?(?:meinen |meine |mein |den |die |das |einen |eine |ein |etwas )?(?P<o>[a-zäöüß ]{2,20}?) (?:auf (?:den|die|das|meinen|meine|mein) (?P<on>[a-zäöüß ]{2,20}?) )?(?:gekippt|verschüttet|fallen lassen|umgeworfen|umgestoßen)"),
    ("burn", r"ich (?:hab|habe) mir (?:beim (?:kochen|backen|bügeln|essen) |an (?:der|dem|einer|einem) [a-zäöüß]+ )?(?:die |den |meine |meinen )?(?P<o>hand|finger|arm|zunge|daumen|mund) verbrannt(?: beim (?:kochen|backen|bügeln))?"),
    ("sprain", r"ich (?:hab|habe) mir (?:den |das |die )?(?P<o>knöchel|fuß|handgelenk|knie) (?:verstaucht|verdreht|umgeknickt)"),
    ("hurt", r"ich bin (?:heute |gerade |eben )?(?:vom (?P<o>fahrrad|rad|roller|pferd) (?:gefallen|gestürzt)|die treppe (?:runter|hinunter)(?:gefallen|gestürzt|gestolpert)|hingefallen|gestolpert|gestürzt)|ich (?:hab|habe) mir (?:den |die |das )?(?P<o2>rücken|kopf) (?:gestoßen|verletzt)"),
    ("cancelled", r"(?:mein|meine|unser|unsere|der|die|das) (?P<o>flug|zug|termin|kurs|konzert|treffen|date|spiel|reise|party) (?:wurde |ist )?(?:gestrichen|abgesagt|annulliert|verschoben|ausgefallen)(?: worden)?"),
    ("stuck", r"ich (?:bin|war|steckte|stecke) (?:heute )?(?:im|in einem|in der) (?P<o>aufzug|fahrstuhl|stau|schnee|schlange) (?:stecken geblieben|stecken|festgesteckt)|ich (?:stand|stehe|steckte|stecke|war) (?:heute |gerade |schon )?(?:(?:\d+|zwei|drei|eine|einer) (?:stunden?|stunde) )?(?:lang )?im (?P<o2>stau)"),
    ("rent", r"(?:mein|meine) (?:vermieter|vermieterin) hat die miete erhöht|(?:meine )?miete (?:wurde|ist) erhöht(?: worden)?|die miete steigt"),
    ("project_done", r"ich (?:hab|habe) (?:heute |gerade |endlich |gestern )?(?:mein |meine |ein |eine |das |die |unser )?(?P<o>(?:großes |großen |riesiges |letztes )?(?:projekt|abschlussarbeit|bachelorarbeit|masterarbeit|hausarbeit|präsentation|bericht|bewerbung|buch|studium|kurs|portfolio))(?: endlich)? (?:abgeschlossen|fertig|fertiggestellt|abgegeben|eingereicht|beendet|geschafft)"),
    ("race_done", r"ich bin (?:heute |gestern )?(?:meinen |einen |den )?(?P<o>ersten marathon|marathon|halbmarathon|10 km|5 km|triathlon|ersten lauf)(?: gelaufen| gerannt| gemacht)"),
    ("passed", r"ich (?:hab|habe) (?:die |meine |den |das )?(?P<o>führerscheinprüfung|prüfung|klausur|fahrprüfung|test|examen|abitur|abi|theorieprüfung)(?: endlich| beim ersten mal)? bestanden"),
    ("first_make", r"ich (?:hab|habe) (?:heute |gestern )?(?:zum ersten mal |das erste mal |selbst |selber )+(?:einen |eine |ein |mein |meine )?(?P<o>[a-zäöüß ]{2,25}?) (?:gebacken|gekocht|gemacht|gebaut|gestrickt|genäht|gebraut)"),
    ("painted", r"ich (?:hab|habe) (?:mein|meine|unser|unsere|das|die) (?P<o>schlafzimmer|zimmer|wohnzimmer|küche|bad|wohnung|wände?|büro|flur)(?: (?P<c>blau|rot|grün|gelb|weiß|grau|schwarz|rosa|lila|orange|beige|türkis))? (?:gestrichen|renoviert|neu gestrichen|tapeziert)"),
    ("planted", r"ich (?:hab|habe) (?:heute )?(?P<o>tomaten|kräuter|blumen|gemüse|salat|erdbeeren|kartoffeln|einen baum|sonnenblumen)(?: im garten| auf dem balkon)? (?:gepflanzt|angepflanzt|eingepflanzt)"),
    ("new_pet", r"wir haben (?:gestern |heute |letzte woche )?(?:eine |einen |ein |zwei )?(?:neue |neuen |kleine |kleinen )?(?P<o>katze|kater|kätzchen|hund|welpen|kaninchen|hamster|katzen|hunde)(?: aus dem tierheim)? (?:adoptiert|bekommen|geholt|aufgenommen)"),
    ("baby", r"wir bekommen (?:ein baby|nachwuchs|zwillinge)|ich bin schwanger|(?:meine )?(?:frau|freundin|partnerin) ist schwanger|wir erwarten (?:ein baby|nachwuchs)"),
    ("kid_milestone", r"(?:meine|mein) (?P<w>tochter|sohn|kleine|kleiner|baby) (?:hat|hatte) (?:heute |gestern )?(?:ihre |seine |seinen |ihren )?(?:ersten schritte gemacht|erstes wort gesagt|ersten schultag|ersten zahn verloren|ersten tag in der kita)"),
    ("turned", r"(?:meine|mein) (?P<w>oma|opa|mutter|mama|vater|papa|tante|onkel|schwester|bruder|frau|mann) (?:ist|wird) (?:heute )?(?P<n>\d{1,3})(?: geworden| jahre alt geworden| jahre alt)?"),
    ("trip_booked", r"ich (?:hab|habe) (?:endlich |gerade )?(?:eine |einen )?(?:reise|flug|urlaub|trip) nach (?P<o>[a-zäöüß ]{2,25}?) gebucht"),
    ("going_out", r"(?:ich|wir) (?:fahre|fahren|gehe|gehen) (?:am wochenende |nächste woche |morgen |bald )?(?P<o>zelten|wandern|skifahren|surfen|angeln|an den strand|campen)"),
    ("diet", r"ich (?:hab|habe) (?:heute )?(?:mit einer|eine) diät angefangen|ich mache (?:jetzt |ab heute )?(?:eine )?diät"),
    ("joined", r"ich (?:hab|habe) mich (?:heute )?(?:im|in einem|in einer|beim|für einen|für einen) (?P<o>fitnessstudio|chor|verein|sportverein|kurs|sprachkurs|tanzkurs|lauftreff|buchclub) angemeldet"),
    ("learning", r"ich lerne (?:gerade |grad |jetzt )?(?P<o>gitarre|klavier|geige|schlagzeug|ukulele|saxophon|flöte|zeichnen|malen|stricken|nähen|schach|schwimmen|tanzen)(?: spielen)?"),
    ("praised", r"(?:mein|meine) (?:chef|chefin|lehrer|lehrerin|trainer|trainerin) hat (?:meine arbeit|mich|meine präsentation|mein projekt) gelobt"),
    ("met_someone", r"ich (?:hab|habe) (?:jemanden|jemand) (?:neues|nettes|besonderes|interessantes) kennengelernt"),
    ("divorce", r"meine eltern (?:lassen sich scheiden|trennen sich|haben sich getrennt)"),
    ("stood_up", r"(?:mein freund|meine freundin|mein date) (?:ist nicht gekommen|hat mich versetzt|hat abgesagt|ist nicht aufgetaucht)"),
    ("neighbour", r"(?:mein|meine) nachbarn? (?:hat|haben) (?:einen |ein )?(?P<o>hund|hunde|kinder|baby)(?:,)? (?:der|die|das) (?:die ganze nacht|ständig|immer) (?:bellt|bellen|schreit|schreien|laut ist|laut sind)"),
    ("lonely", r"ich fühle mich (?:in letzter zeit |gerade |oft |so )*(?:einsam|allein)(?: in letzter zeit)?"),
    ("nervous", r"ich bin (?:so |total |echt |ziemlich )?(?:nervös|aufgeregt) wegen (?P<o>morgen|der prüfung|dem vorstellungsgespräch|der präsentation|montag|der hochzeit|meinem ersten tag)"),
    ("decide_study", r"ich weiß nicht,? was ich studieren soll|ich kann mich nicht entscheiden,? was ich studieren soll"),
    ("proud", r"ich bin (?:so |echt |richtig )?stolz auf mich"),
    ("plants_dying", r"meine pflanzen gehen (?:immer |ständig |alle )?ein|alle meine pflanzen sind eingegangen"),
    ("forgot_bday", r"ich (?:hab|habe) den geburtstag (?:von )?(?:meiner|meinem) (?P<w>mutter|mama|vater|papa|schwester|bruder|oma|opa|freundin|freund|frau|mann) vergessen"),
    ("cleaned", r"ich (?:hab|habe) (?:heute |endlich )?(?:meine|die|unsere) (?:ganze )?(?:wohnung|bude|küche|haus) (?:geputzt|aufgeräumt|sauber gemacht)"),
    ("team_won", r"(?:meine|mein) (?:mannschaft|team|verein) hat (?:die |das |den )?(?P<o>meisterschaft|spiel|pokal|finale|liga)? ?gewonnen"),
    ("sick_week", r"ich war die ganze woche krank|ich bin seit einer woche krank"),
    ("interview", r"ich hatte (?:heute |gerade )?(?:ein )?vorstellungsgespräch"),
    ("went_out", r"(?:ich war|wir waren) (?:gestern |heute |am wochenende |gestern abend |letzte woche |am (?:montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag) )?(?:auf|in|im|bei) (?:einem |einer |dem |der |einem )?(?P<o>konzert|festival|party|hochzeit|kino|theater|museum|spiel|club|bar|restaurant|beerdigung|geburtstag|musical)"),
    ("overslept", r"ich (?:hab|habe) (?:heute |schon wieder )?verschlafen(?: und (?:meinen |den |die )?(?P<o>zug|bus|termin|flug|bahn|vorlesung|besprechung) verpasst)?"),
]]


def match(text: str, lang: str) -> tuple[str, dict] | None:
    """The kind of moment and its slots, or None."""
    frames = DE if lang == "de" else EN
    t = re.sub(r"\s+", " ", text.lower()).strip(" .!?")
    for key, rx in frames:
        m = rx.fullmatch(t)
        if m:
            return key, {k: (v or "").strip() for k, v in m.groupdict().items()}
    return None
