"""The conversation layer (Chat v3, phase 0): small talk, feelings, tools, memory commands,
"tell me about X", whole-sentence answers — on top of the unchanged question-answering core.

``ChatBot`` (bot.py) stays the registered QA and memory core: its look-up, fact memory, pronoun
resolution and exact forgetting are used as they are, so every earlier measurement still holds.
``Assistant.turn(state, message)`` decides per sentence what to do (acts.py), asks the core
where a question or a statement needs it, and writes the reply from the conversation bank
(bank.py) and the realiser (realize.py).

What is remembered changed: a statement is learnt only when it carries something to remember
— a fact the fact memory recognises, something about you ("I …", "my …"), a named thing — or
when you say "remember that …". "lol", "the weather is nice" and "I'm so tired" are answered,
not stored.

A ``DialogState`` belongs to one conversation (the app keeps one per chat); it holds the core's
pronoun context, what ENGRAMM just asked, the last answer (for "why?", "tell me more") and the
reply counters that keep replies from repeating. Everything is deterministic: the same
conversation with the same messages gets the same replies.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from collections import Counter
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from engramm.chat.about import About, AboutFinder, clean_sentence
from engramm.chat.acts import Unit, classify
from engramm.chat.bank import Bank, choose, expand_chat, load_bank, normalise
from engramm.chat.bot import CHAT_PREFIX, Reply, message_type, source_id
from engramm.chat.everyday import _GENRES
from engramm.chat.tools import tool_answer
from engramm.chat.facts import USER, facts_from_text
from engramm.chat.german import is_german, understand
from engramm.chat.realize import _acronyms as _acronym_case, answer_sentence, article, personal_sentence, to_second_person
from engramm.chat.smart import (bare_followup, experience, gibberish, is_discourse, is_mash, offer_in, rebuild_question,
                                short_answer, swap_person)

FRESH_CTX = {"answer": None, "atype": None, "mention": None, "last_learned": None}
RECENT = 40                                  # replies remembered to avoid repeats
# intents that only add a short word when the message also asks something else
_SHORT = {"greeting": ["Hi!", "Hello!", "Hey!"], "greeting_morning": ["Good morning!"],
          "greeting_afternoon": ["Good afternoon!"], "greeting_evening": ["Good evening!"],
          "thanks": ["You're welcome!", "Happy to help!"], "apology": ["No worries!"],
          "how_are_you": ["I'm doing well, thanks!"], "bot_state_back": ["I'm good, thanks!"],
          "user_fine": ["Glad to hear it!"], "positive": ["Nice!"], "laugh": ["Haha!"], "holiday": ["Thank you!"]}
_SHORT_NAMED = {"greeting": ["Hi {name}!", "Hello {name}!", "Hey {name}!"], "greeting_morning": ["Good morning, {name}!"],
                "greeting_evening": ["Good evening, {name}!"]}
_DROP_WITH_CONTENT = {"talk_request", "ack", "yes", "no", "wait", "topic_suggest", "confused", "user_bored",
                      "nothing_much", "right"}
_CATEGORY_KEYS = [("#name", "name"), ("#home", "home"), ("#job", "job"), ("#employer", "employer"),
                  ("#food", "food"), ("#colour", "colour"), ("#car", "car"), ("#birth", "birth"),
                  ("#origin", "origin"), ("#fav", "fav")]
_ASK_FOR_CATEGORY = {"#name": "ask_name", "#home": "ask_home", "#job": "ask_job", "#food": "ask_food",
                     "#colour": "ask_colour"}
_CAPS_NAME = re.compile(r"\b[A-Z][a-zA-Z'-]+")


# "I finally finished my thesis", "I'm done with my homework": something achieved
_DONE_WITH = re.compile(r"(?i:(?:i|i'm|im|i am|i've|ive|i have|we|we've|we're)\s+(?:just\s+|finally\s+|already\s+)*"
                        r"(?:done with|finished|completed|passed|submitted|handed in|got through|nailed)\s+)"
                        r"(?P<x>(?:my|the|our|all my|all the|that)\s+[a-z][a-z' -]{2,40})[.!]*$")
# "I don't have eggs", "I'm out of rice", "no garlic": an ingredient missing
_WITHOUT = re.compile(r"^(?:but |oh |hmm |ah )?(?:i (?:don't|dont|do not) have (?:any )?|i(?:'m| am|m) out of |i ran out of |"
                      r"there(?:'s| is) no |no )(?P<x>[a-z][a-z ]{1,25}?)(?: at home| left| in the house| here)?[.!]*$")
# dishes that need an ingredient without naming it
_NEEDS = {"egg": ["omelette", "frittata", "carbonara", "shakshuka", "quiche", "pancake"],
          "rice": ["risotto", "fried rice", "with rice", "paella", "sushi"],
          "pasta": ["spaghetti", "aglio e olio", "carbonara", "lasagne", "bolognese"],
          "cheese": ["feta", "pizza", "omelette with cheese", "quesadilla"],
          "bread": ["toast", "sandwich", "crusty bread", "flatbread"],
          "flatbread": ["pizza on a flatbread"], "tortilla": ["tacos", "burrito", "quesadilla"],
          "potatoe": ["potato", "fries", "mash"], "potato": ["fries", "mash"], "tomatoe": ["tomato", "shakshuka", "salsa"],
          "tomato": ["shakshuka", "salsa"], "garlic": ["aglio"], "meat": ["bolognese", "burger", "steak"]}
# "ok pasta it is", "pizza it is then": a decision
_DECIDED = re.compile(r"^(?:ok(?:ay)?|alright|fine|right|great|perfect|cool)?,? ?(?:then )?(?P<x>[a-z][a-z' ]{1,30}?) it is(?: then)?[.!]*$")
# "something I can do at home", "any ideas what I could do inside"
_THINGS_TO_DO = re.compile(r"^(?:maybe |ok |okay )?(?:something|anything|stuff|things?|ideas?|any ideas?)(?: (?:what|that))? "
                           r"(?:i|we) (?:can|could|might) do(?P<g> at home| inside| indoors| outside| alone| today| tonight)?[.!?]*$")
# "maybe reading then", "a movie i guess": a kind of thing to suggest
_MAYBE_KIND = re.compile(r"^(?:maybe|perhaps|ok|okay|hmm|i guess|i think|probably|then)[, ]+(?P<w>reading|a book|books|a movie|movies|a film|films|"
                         r"a series|a show|tv|music|a game|games|gaming|a podcast|podcasts|cooking|baking|a hobby)"
                         r"(?: then| maybe| i guess| or something)?[.!?]*$")
_MAYBE_KINDS = {"reading": "book", "book": "book", "books": "book", "movie": "movie", "movies": "movie", "film": "movie",
                "films": "movie", "series": "series", "show": "series", "tv": "series", "music": "music", "game": "game",
                "games": "game", "gaming": "game", "podcast": "podcast", "podcasts": "podcast", "cooking": "food",
                "baking": "food", "hobby": "hobby"}
# "I moved to a new city and don't know anyone"
_MOVED_NEW = re.compile(r"\bi (?:just |recently )?(?:moved|relocated) (?:to|into) (?:a |another )?(?:new|different|another) (?:city|town|country|place)\b")
# "what should I wear (to the interview)?"
_WEAR = re.compile(r"^(?:and |so |ok |hmm )?what (?:should|do|can) i wear(?: (?:to|for|on) (?:the |a |my )?(?P<x>[a-z ]+?))?\??$")
_OCCASIONS = [("interview", re.compile(r"\binterview")), ("wedding", re.compile(r"\bwedding|\bmarr")),
              ("date", re.compile(r"\bdate\b|\bfirst date")), ("dinner", re.compile(r"\bdinner|\bcelebrat|\brestaurant|\bparty|going out")),
              ("funeral", re.compile(r"\bfuneral")), ("office", re.compile(r"\boffice|\bfirst day|\bwork\b"))]
# light everyday debates and the words that name them
_DEBATES = [("pineapple", ("pineapple", "pizza")), ("cats_dogs", ("cats?", "dogs?")), ("tea_coffee", ("tea", "coffee")),
            ("books_movies", ("books?", "(?:movies?|films?)")), ("summer_winter", ("summer", "winter")),
            ("beach_mountains", ("beach", "mountains?")), ("early_late", ("(?:early bird|morning person)", "(?:night owl|night person)")),
            ("iphone_android", ("iphone", "android"))]
# "I'm planning a trip to Japan next month", "we're flying to Lisbon on Friday"
_TRIP_PLAN = re.compile(r"\b(?:i'?m|i am|we'?re|we are|im) (?:planning|going on|taking|booking|off on|about to go on) (?:a |our |my )?"
                        r"(?:trip|holiday|vacation|journey|getaway|honeymoon) to (?P<x>[a-z][a-z ]{1,30}?)"
                        r"(?: next \w+| this \w+| in \w+| soon| tomorrow| on \w+| for \w+(?: \w+)?)?[.!]*$|"
                        r"\b(?:i'?m|i am|we'?re|we are|im) (?:flying|travelling|traveling|going|heading|moving) to (?P<y>[a-z][a-z ]{1,30}?) "
                        r"(?:next \w+|this \w+|in \w+|soon|tomorrow|on \w+|for (?:a|two|three|\d+) \w+)[.!]*$")
_TRIP_TIPS = re.compile(r"^(?:any |some |got any )?(?:tips|advice|suggestions|recommendations)(?: for (?:me|it|the trip))?\??$")
# "just got home from work": a person arriving, not a fact to store
_GOT_HOME = re.compile(r"^(?:not much,? |nothing much,? |nm,? )?(?:i )?(?:just )?(?:(?:got|came|came back|got back|am|i'm) "
                       r"(?:home|back) from|finished|got off|done with|off)(?: the| my)? (?P<x>work|school|uni|university|college|gym|practice|class|"
                       r"training|office|shift|a trip|vacation|holiday)(?: for (?:the day|today))?[.!]*$")
# laughter and short reactions: never the answer to "What's your favourite food?"
_REACTION = re.compile(r"(?:(?:ha)+h?|he(?:he)+|lol|lmao|rofl|xd|:\)|:d|haha ?(?:fair|true|nice|ok(?:ay)?|yeah|yes|right)|"
                       r"(?:fair|true|nice|right|cool|lol) ?(?:enough|haha|lol)?|fair point|good point|touch[eé]|"
                       r"(?:that's|thats) (?:fair|true|funny|right)|true that|so true|lol (?:fair|true|ok(?:ay)?))")
# "what was I complaining about earlier?": the last moment told
_WHAT_WAS_I = re.compile(r"^(?:sorry,? |wait,? )?what (?:was|were|did) i (?:complaining|ranting|venting|moaning|talking|telling you|"
                         r"say|said|upset|stressed|worried|mad|angry|happy|excited) ?(?:about)?(?: earlier| before| again)?\??$")
# everyday remarks and how a person answers them (see DialogEngine._talk)
_TALK_RULES = [
    (re.compile(r"\bi (?:should|need to|have to|gotta|must|will|'ll|am going to|'m going to) (?:go to (?:bed|sleep)|sleep|head to bed|get some sleep)\b"), "talk_bed"),
    (re.compile(r"^(?:she|he|it|they)(?:'s| is|'re| are) (?:sleeping|purring|cuddling|snoring|lying|curled up|playing|napping)\b"), "talk_pet_now"),
    (re.compile(r"\b(?:we'?re|i'?m|we are|i am|im) (?:going out|going to (?:a |the )?(?:dinner|party|concert|cinema|movies|game|gym|beach|pub|bar|club)|heading out|off to (?:a |the )?(?:dinner|party|concert|cinema|beach|pub)|meeting (?:friends|my friends|up with))\b"), "talk_plan"),
    (re.compile(r"\bi'?(?:ll| will) (?:tell|let) you(?: know)?(?: how (?:it|that|the \w+) (?:was|went|goes|turns out))?\b|\bi'?ll keep you posted\b"), "talk_report"),
    (re.compile(r"^(?:but |well |sadly |unfortunately )?(?:i )?(?:don'?t|do not|dont) (?:have|own) (?:a|an|any) \w+"), "talk_nohave"),
    (re.compile(r"^(?:ok |okay |but )?(?:i )?(?:have to|need to|gotta|got to|must) (?:go |run |quickly |first )?(?:to )?\w+"), "talk_must"),
    (re.compile(r"\bmiss(?:ing)? (?:him|her|them|home|my \w+|\w+ so much|\w+ a lot)\b"), "talk_miss"),
    (re.compile(r"\b(?:i'?ll|i will|i might|i may|i could|i should|i'?m going to|im going to|i'?m gonna|gonna|maybe i'?ll) "
                r"(?:try|give it a (?:go|try|shot)|check (?:it|that|them) out|do that|talk to|ask|look into|go for|watch|read|listen to|play|cook|make|start)\b"), "talk_try"),
    (re.compile(r"\b(?:i'?ve|i have|ive) (?:already )?(?:heard|read|seen|watched|tried) (?:of |about )?(?:that|it|this|them)(?: one)?\b"),
     "talk_heard"),
    (re.compile(r"\b(?:killing me|exhausted|so tired|drained|slept (?:terribly|badly|awfully|horribly|like crap)|"
                r"(?:barely|didn'?t|couldn'?t) sleep|no sleep|burn(?:ed|t)? out|wiped out|sucks?|so rough|so hard|"
                r"too much (?:work|stress)|overwhelmed|swamped)\b"), "talk_tough"),
]
# remarks the plain chit-chat path should hand to DialogEngine._talk
_TALK_FIRST = re.compile(r"\b(?:start|bed|sleeping|purring|cuddling|napping|curled|watch|going out|going to|heading out|off to|meeting|tell you|let you know|keep you posted|miss(?:ing)?|try|heard|read|seen|watched|killing|exhausted|tired|drained|slept|sleep|"
                         r"burn(?:ed|t)?|wiped|sucks?|rough|hard|overwhelmed|swamped)\b")
# "and 20%?" after a percentage
_PCT_MORE = re.compile(r"^(?:and |what about |how about |now |ok |okay )?(\d+(?:\.\d+)?)\s?%(?: of (?:it|that))?\??$")
# "is that too much?", "is that normal?": a judgement about what was just said
_VAGUE_JUDGE = re.compile(r"^(?:but |so |and |hmm |ok )?(?:is|isn't|isnt|was|are|aren't) (?:that|this|it|those|these) (?:really |actually |way )?"
                          r"(?:too much|too little|enough|normal|bad|ok|okay|alright|fine|healthy|unhealthy|a lot|weird|"
                          r"strange|a problem|too many|too few|too long|too short|too late|too early|good|unusual)\??$")
# everyday amounts people ask about, and what the general guidance says
_NORMS = [(re.compile(r"\b(?:coffees?|espressos?|caffeine|energy drinks?|red bulls?)\b"), "coffee"),
          (re.compile(r"\b(?:sleep|slept|hours? of sleep|hours? a night|bed at)\b"), "sleep"),
          (re.compile(r"\b(?:water|litres?|liters?|glasses)\b"), "water"),
          (re.compile(r"\b(?:screen time|phone|scroll|tiktok|instagram|gaming|video games?)\b"), "screen"),
          (re.compile(r"\b(?:steps|walk(?:ed)?)\b"), "steps")]


_TITLE_FILLER = frozenset("of the a an in on at for and or to by list lists history geography".split())


def _clearly_english(msg: str, de: dict) -> bool:
    """More English than German words, and at least two of them: the conversation switches."""
    words = re.findall(r"[a-zäöüß']+", msg.lower())
    en, ger = set(de["detect"]["english"]), set(de["detect"]["german"])
    n_en = sum(w in en and w not in ger for w in words)
    n_de = sum(w in ger and w not in en for w in words)
    return n_en >= 2 and n_en > n_de or (n_en >= 1 and n_de == 0 and len(words) <= 3 and not re.search(r"[äöüß]", msg))


def _title_fits(question: str, title: str) -> bool:
    """Name an article as "closest" only if most of its title words are in the question
    ("LL Cool J" for "cool, any other?" would read as nonsense)."""
    tw = [w for w in re.findall(r"[a-z0-9]+", re.sub(r"\([^)]*\)", "", title.lower()))
          if w not in _STOP_CHAT and w not in _TITLE_FILLER and len(w) > 1]
    qw = set(re.findall(r"[a-z0-9]+", question.lower()))
    hits = sum(w in qw for w in tw)
    return bool(tw) and hits * 2 >= len(tw) and hits >= min(2, len(tw))


# German refinements of a suggestion ("etwas schnelles", "lieber was gesundes")
_GENRE_DE = re.compile(r"^(?:lieber |eher |vielleicht |hmm |ok |dann )?(?:etwas |was |eins |einen |eine |ein )?(?:mehr |eher |richtig )?"
                       r"(?P<g>[a-zäöüß]+)(?: bitte| vielleicht| lieber)?[.!?]*$")
_GENRE_DE_MAP = {"schnell": "quick", "einfach": "quick", "gesund": "healthy", "leicht": "healthy", "gemütlich": "cosy",
                 "warm": "warm", "lustig": "funny", "witzig": "funny", "spannend": "exciting", "gruselig": "scary",
                 "romantisch": "romantic", "klassisch": "classic", "historisch": "history", "günstig": "cheap",
                 "billig": "cheap", "sonnig": "sunny", "kalt": "cold"}
# "what is the tallest mountain …": the kind of thing asked for, and the fact-bank types that fit it
_ASKED_KIND = re.compile(r"^\s*(?:what|which)(?:'?s| is| was| are| were)? (?:the |a )?(?:\w+ ){0,3}?"
                         r"(?P<k>mountains?|rivers?|lakes?|countr(?:y|ies)|cit(?:y|ies)|islands?|buildings?|planets?|oceans?)\b", re.I)
_KIND_TYPES = {"mountain": {"Mountain", "Volcano", "MountainRange"}, "river": {"River", "Stream", "Canal", "BodyOfWater"},
               "lake": {"Lake", "BodyOfWater", "Reservoir"}, "country": {"Country"},
               "countrie": {"Country"}, "city": {"City", "Town", "Settlement", "AdministrativeRegion"},
               "citie": {"City", "Town", "Settlement", "AdministrativeRegion"}, "island": {"Island", "Settlement"},
               "building": {"Building", "Skyscraper", "Tower", "HistoricBuilding", "Castle", "ReligiousBuilding"},
               "planet": {"Planet"}, "ocean": {"Sea", "BodyOfWater", "Ocean"}}
# lower-case month names as the user typed them, in a remembered date
_MONTH_LOW = re.compile(r"\b(?:january|february|march|april|june|july|august|september|october|november|december)\b|"
                        r"\bmay(?= \d)|(?<=\d )may\b")
# two questions joined by "and"
_TWO_QUESTIONS = re.compile(r"(?i)^(?P<a>(?:what|who|when|where|which|how)\b.+?),?\s+and\s+"
                            r"(?P<b>(?:how|what|who|when|where|which|is|are|was|were|does|did|do)\b.+)$")
# questions whose answer is a measurement or a count
_NEEDS_NUMBER = re.compile(r"(?i)\b(?:boiling point|melting point|freezing point|temperature|speed of|how many|how much|"
                           r"how far|how long|how tall|how high|how deep|how old|how heavy|population of|distance)\b")
# yes/no questions
_YES_NO_Q = re.compile(r"(?i)^(?:is|are|was|were|does|do|did|can|could|has|have|will|would|should)\b(?!.*\b(?:or)\b)")
# "no wait, it's alexander" right after telling the name
_NAME_FIX = re.compile(r"(?i)^(?:no,? |nope,? |sorry,? |oops,? )?(?:wait,? |actually,? |i mean,? )*(?:it'?s|its|i'?m|im|my name is|"
                       r"call me) (?P<x>[a-z][a-z'-]+)[.!]*$")
# "really? i thought it was sydney" after an answer
_THOUGHT_IT_WAS = re.compile(r"^(?:really\??,? |wait,? |huh,? |oh,? |hm+,? )*i (?:thought|was sure|always thought) "
                             r"(?:it was|it's|its|the answer was|that it was) (?P<x>[a-z][a-z .'-]{1,40})$")
# "and the second?" after a superlative
_NEXT_RANK = re.compile(r"(?:and |what about |how about )?(?:the )?(second|2nd|third|3rd)(?: one| place| (?:tallest|highest|longest|largest|biggest|smallest))?")
# "how far is it from Tokyo to Kyoto?" — no map data to measure with
_DISTANCE_Q = re.compile(r"^(?:and |so )?(?:how far (?:is it |away )?(?:is )?(?:from )?\S.* (?:to|from) \S.*|what(?:'s| is) the distance (?:between|from) \S.*)\??$")
# "how tall?", "and how long": the measure of what was just talked about
_HOW_ADJ = re.compile(r"(?:and |so |ok )?how (tall|high|long|big|old|deep|large|heavy|wide|far away|far)(?: exactly)?")
# "what's the capital again?" — a relation of the place being talked about
_PLACE_REL_Q = re.compile(r"(?i)^(?:and |so |ok |okay |wait,? )?(?:what'?s|what is|what was|whats) the (?P<r>capital|population|currency|"
                          r"official language|language|time zone|president|prime minister|king|queen|largest city)"
                          r"(?: again| there| of it)?\??$")
# "what should I eat there / in Japan?"
_EAT_THERE = re.compile(r"^(?:and |so |ok )?what (?:should|can|do|could|would) (?:i|we|people|you) (?:eat|try|order)"
                        r"(?: there| in (?P<p>[a-z][a-z ]+?))?\??$")
_CUISINE_ADJ = {"japan": "Japanese", "china": "Chinese", "korea": "Korean", "south korea": "Korean", "thailand": "Thai",
                "vietnam": "Vietnamese", "india": "Indian", "italy": "Italian", "france": "French", "spain": "Spanish",
                "portugal": "Portuguese", "greece": "Greek", "turkey": "Turkish", "mexico": "Mexican", "peru": "Peruvian",
                "brazil": "Brazilian", "argentina": "Argentine", "germany": "German", "austria": "Austrian",
                "switzerland": "Swiss", "england": "English", "scotland": "Scottish", "ireland": "Irish",
                "united kingdom": "British", "uk": "British", "morocco": "Moroccan", "egypt": "Egyptian",
                "lebanon": "Lebanese", "israel": "Israeli", "iran": "Iranian", "indonesia": "Indonesian",
                "malaysia": "Malaysian", "philippines": "Filipino", "ethiopia": "Ethiopian", "russia": "Russian",
                "poland": "Polish", "hungary": "Hungarian", "sweden": "Swedish", "norway": "Norwegian",
                "denmark": "Danish", "netherlands": "Dutch", "belgium": "Belgian", "usa": "American",
                "united states": "American", "america": "American", "canada": "Canadian", "australia": "Australian"}
# "wer hat die relativitätstheorie entwickelt?" → "Die Relativitätstheorie wurde von … entwickelt."
_WHO_MADE_DE = re.compile(r"wer hat (?P<art>die |den |das )?(?P<x>[a-zäöüß][a-zäöüß \-]{2,40}?) (?P<v>entwickelt|erfunden|geschrieben|"
                          r"gemalt|entdeckt|gegründet|komponiert|gebaut|erschaffen|gedreht|gesungen)")
# "heute hab ich ein vorstellungsgespräch"
_EVENT_DE_RX = re.compile(r"\b(?:heute|morgen|gleich|nachher|übermorgen|am \w+|diese woche|nächste woche) (?:hab|habe) ich "
                          r"(?:ein|eine|einen|mein|meine|meinen) (?P<e>vorstellungsgespräch|prüfung|klausur|präsentation|date|"
                          r"fahrprüfung|termin|arzttermin|bewerbungsgespräch)\b|\bich (?:hab|habe) (?:heute|morgen|gleich) "
                          r"(?:ein|eine|einen) (?P<e2>vorstellungsgespräch|prüfung|klausur|präsentation|date)\b")
# German dishes that need an ingredient without naming it
_NEEDS_DE = {"eier": ["omelett", "shakshuka", "ei"], "reis": ["reis", "risotto"], "nudeln": ["pasta", "nudel"],
             "käse": ["käse", "feta", "pizza"], "brot": ["brot", "fladenbrot", "pizza"], "kartoffeln": ["kartoffel"],
             "tomaten": ["tomate", "shakshuka", "salsa"]}
# German everyday forms (dialog._german_life)
_NA_DE = re.compile(r"(?:hey |hi |hallo |moin |servus |hallöchen )?na(?: du| ihr)?(?:,? (?:wie geht'?s|alles klar|alles gut))?")
_THANKS_DE = re.compile(r"(?:(?:cool|super|ok(?:ay)?|alles klar|gut|perfekt|toll|mega|ah|oh),? )?"
                        r"(?:(?:danke|vielen dank|dankeschön|danke schön|danke dir|merci|vielen lieben dank)(?P<rest>.*)|"
                        r"(?P<idea>gute idee|klingt gut|mach ich|probier ich|versuch ich|das probier ich|das mach ich))")
_LOSS_DE = re.compile(r"\b(?:mein(?:e|em|en)? (?P<n>\w+)|er|sie) (?:ist|sind) (?:heute |gestern |letzte woche |vor kurzem |"
                      r"leider |plötzlich |letzte nacht )*(?:gestorben|verstorben|tot)\b|"
                      r"\bich (?:habe|hab) (?:meine[nm]? )?(?P<n2>\w+) verloren\b|\b(?:mein(?:e|en)? \w+) wurde eingeschläfert\b")
_PETS_DE = frozenset("hund katze kater hamster hase kaninchen vogel wellensittich pferd meerschweinchen".split())
_FEMALE_DE = frozenset("oma mutter mama schwester tochter frau freundin tante cousine nichte großmutter omi".split())
_SEEN_DE = re.compile(r"(?:oh |ah |hm+ )?(?:kenn ich|kenne ich|hab ich|habe ich) (?:schon|alle|bereits)(?: gelesen| gesehen| gehört| gespielt)?(?: alle)?|"
                      r"(?:schon|alle schon) (?:gelesen|gesehen|gehört|gespielt)")
# "wie alt bin ich?" → (English question, German answer template)
_ME_Q_DE = [(re.compile(r"(?:und )?(?:wie alt bin ich|weißt du(?: noch)?,? wie alt ich bin)"), "how old am i?", "Du bist {x}."),
            (re.compile(r"(?:und )?(?:was mache ich beruflich|was arbeite ich|als was arbeite ich|was ist mein beruf|was bin ich von beruf)"),
             "what do i do for a living?", "Du arbeitest als {x}."),
            (re.compile(r"(?:und )?(?:wo wohne ich|wo lebe ich|weißt du(?: noch)?,? wo ich wohne)"), "where do i live?", "Du wohnst in {x}."),
            (re.compile(r"(?:und )?(?:woher komme ich|wo komme ich her)"), "where am i from?", "Du kommst aus {x}."),
            (re.compile(r"(?:und )?(?:was mag ich nicht|was mag ich gar nicht|was esse ich nicht gern)"), "", "list:#dislike"),
            (re.compile(r"(?:und )?(?:was mag ich|was mag ich gern|was esse ich gern)"), "", "list:#fav")]
_SUPER_DE = re.compile(r"(?:und |also )?(?:was|welche[rs]?|wie heißt|wer) (?:ist )?(?:der|die|das) "
                       r"(?P<adj>höchste|längste|größte|kleinste|bevölkerungsreichste) (?P<noun>berg|fluss|see|land|gebäude|hochhaus)"
                       r"(?: der welt| auf der welt| der erde| weltweit)?")
# a nationality is never the answer to "who …?"
_DEMONYMS = frozenset("""british english scottish welsh irish american canadian mexican brazilian argentine argentinian
french german italian spanish portuguese dutch belgian swiss austrian swedish norwegian danish finnish icelandic polish
czech slovak hungarian romanian bulgarian greek turkish russian ukrainian chinese japanese korean indian pakistani nepalese
nepali tibetan australian egyptian nigerian kenyan african european asian israeli iranian iraqi saudi""".split())
# a passing moment ("right now", "soon"): answered, not stored
_TRANSIENT = re.compile(r"\b(?:right now|at the moment|atm|currently|soon|in a bit|in a minute|for now)\b|^i should (?:go|head|get)\b|"
                        r"^(?:she|he|it|they)(?:'s| is|'re| are) (?:sleeping|purring|napping|snoring|cuddling|curled up)\b")
# closing a chat ("i'm done for today") is a goodbye, not something to remember
_WRAP_UP = re.compile(r"^(?:ok(?:ay)?,? )?(?:i'?m|i am|we'?re|we are) (?:done|finished|off)(?: here)?(?: for (?:today|now|tonight|the day))?[.!]*$|^that'?s (?:all|it) for (?:today|now|tonight)")


@dataclass
class DialogState:
    conversation: str = "default"
    ctx: dict = field(default_factory=lambda: dict(FRESH_CTX))
    turn: int = 0
    uses: dict = field(default_factory=dict)
    recent: list = field(default_factory=list)
    pending: dict | None = None               # a question ENGRAMM asked: {"slot", "store", "turn"}
    last_reply: str = ""
    last_fact: dict | None = None             # the last answer: evidence, source, answer, question
    last_about: dict | None = None            # for "tell me more"
    asked: list = field(default_factory=list)  # questions ENGRAMM asked in this conversation
    rps: bool = False                         # waiting for rock / paper / scissors
    last_draft: dict | None = None            # the last written draft (WritingRequest), for edits
    draft_turn: int = -1
    offer: dict | None = None                 # what ENGRAMM's last reply offered ("Want a joke?"), for "yes"
    topic: dict | None = None                 # the thing being talked about: {"title", "name", "type", "turn"}
    last_q: str | None = None                 # the last question (pronouns resolved), for "where?" / "and X?"
    last_q_named: str | None = None           # the last question that names something, for "and X?"
    last_exp: dict | None = None              # the last moment you told ("my boss yelled at me"), for "what should I do?"
    last_list: dict | None = None             # the last suggestions, for "tell me about the second one"
    game: dict | None = None                  # a quiz question or riddle waiting for your answer
    game_score: tuple | None = None
    gib: int = 0                              # replies to gibberish in a row
    last_message: str = ""
    last_kind: str = ""
    last_action: dict | None = None           # the last joke / fact / quiz / suggestions, for "another one"
    lang: str = "en"                          # the language of the conversation ("de" after a German message)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> DialogState:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class _Part:
    role: str          # prefix | main | learn | follow
    text: str


class Assistant:
    def __init__(self, bot, bank: Bank | None = None, clock=None, kb_path=None, nlp_dir=None):
        self.bot = bot
        self.bank = bank or load_bank()
        self.clock = clock                      # callable → datetime (tests fix the date)
        self.about = AboutFinder(bot.c, getattr(bot, "r", None))
        self.kgqa = None
        path = kb_path
        if path is None and getattr(bot.c, "index_dir", None) is not None:
            for cand in (bot.c.index_dir / "kb.sqlite", bot.c.index_dir.parent / "kb.sqlite"):
                if cand.exists():
                    path = cand
                    break
        if path is not None and Path(path).exists():
            from engramm.kb.kgqa import KGQA
            from engramm.kb.store import FactBank
            today = clock().date() if clock else None
            self.kgqa = KGQA(FactBank(path), today=today)
        # requests ENGRAMM cannot carry out (alarms, music, live data): the counted intent classifier
        from engramm.chat.device import DeviceRequests, find_model
        index_dir = getattr(bot.c, "index_dir", None)
        model = find_model(nlp_dir, index_dir / "nlp" if index_dir is not None else None,
                           Path(__file__).resolve().parents[2] / "models" / "nlp")
        self.device = DeviceRequests(model) if model is not None else None
        from engramm.nlp.spell import Speller
        spell = next((d / "spell.json" for d in (Path(nlp_dir) if nlp_dir else None, index_dir)
                      if d is not None and (d / "spell.json").exists()), None)
        self.speller = Speller.load(spell) if spell is not None else None
        from engramm.chat.events import EventBook
        mem_path = getattr(bot.memory, "path", None)
        self.events = EventBook(Path(mem_path).with_suffix(".events.json") if mem_path else None)
        from engramm.chat.everyday import Everyday
        self.everyday = Everyday(self)
        self.atlas = None                       # engramm/web/atlas.py, set by the server when channels exist

    # -- helpers ------------------------------------------------------------------------------

    def _pick(self, st: DialogState, key: str, options: list[str], **fmt) -> str:
        n = st.uses.get(key, 0)
        st.uses[key] = n + 1
        # the variants this key gave lately count as recent too: a part of a longer reply (an opening
        # line) is never in st.recent as such
        mine = st.uses.get(key + "#last", [])
        text = choose(options, f"{st.conversation}|{key}|{n}", st.recent + mine)
        st.uses[key + "#last"] = (mine + [text])[-max(1, len(options) - 1):]
        return _fill(text, **fmt)

    def _reply(self, st: DialogState, path: str, **fmt) -> str:
        return self._pick(st, path, self.bank.reply(path), **fmt)

    def user_name(self) -> str | None:
        self.bot.refresh()
        texts = list(self.bot.user_texts())
        order = {sid: i for i, sid in enumerate(texts)}
        names = [(order.get(f.source, -1), f.object) for f in self.bot.facts.facts
                 if f.subject == USER and "#name" in f.relation]
        return max(names)[1] if names else None

    def _now(self):
        return self.clock() if self.clock else None

    def _german(self, st: DialogState, msg: str) -> Reply:
        """A German message (engramm/chat/german.py): chat, feelings, crises, memory, suggestions,
        advice, moments, and knowledge questions through the English fact bank
        (engramm/chat/german_bridge.py), answered in German where the answer is a fact."""
        from engramm.chat.german import advice_de, experience_de, neutral_de, normalise_de, rec_kind_de
        de = self.bank.de
        dd = de.get("daily", {})
        st.lang = "de"
        s = normalise_de(msg)
        u = understand(msg, de)
        name = self.user_name()
        known = self.speller.known if self.speller is not None else None
        if u.kind not in ("safety", "remember", "ask_name", "calc", "intent") and gibberish(msg, known):
            return Reply(msg, "unknown", self._pick(st, "de:gib", dd["gibberish"]), via="gibberish")
        if u.kind != "safety":
            life = self._german_life(st, msg, s)
            if life is not None:
                return life
        if u.kind == "fallback" or u.kind == "feeling":
            n = neutral_de(s)
            if n is not None:
                return Reply(msg, "smalltalk", self._pick(st, f"de:short:{n}", dd["short"][n]), via="german")
            if re.fullmatch(r"(?:noch )?mehr|noch (?:ein paar|einen|eine|einer|eins)|nochmal|weiter", s):
                la = st.last_action
                if la and la["kind"].startswith("rec:"):
                    return self.everyday.recommend(st, msg, la["kind"][4:], la.get("genre"), more=True, lang="de")
                if la and la["kind"] in ("joke",):
                    return self._german(st, "erzähl mir einen witz")
            la = st.last_action or {}
            gm = _GENRE_DE.match(s)
            if gm and la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3:
                # "etwas schnelles" after cooking ideas: the same refinement as "something quick"
                stem = re.sub(r"(?:es|e|er|en)$", "", gm.group("g"))
                genre = _GENRE_DE_MAP.get(stem)
                if genre:
                    return self.everyday.recommend(st, msg, la["kind"][4:], genre, lang="de")
            exp_recent = st.last_exp if st.last_exp and st.turn - st.last_exp.get("turn", -99) <= 4 else None
            kind = rec_kind_de(s)
            if kind is not None and not (kind == "activity" and exp_recent and advice_de(s)):
                return self.everyday.recommend(st, msg, kind, lang="de")
            if advice_de(s):
                exp = exp_recent
                if not exp:
                    return Reply(msg, "smalltalk", self._pick(st, "de:advice:none", dd["advice"]["none"]), via="german")
                group = self.everyday._advice_group(exp.get("text_en") or exp.get("text") or "", exp)
                group = group if group in dd["advice"] else "generic"
                return Reply(msg, "smalltalk", self._pick(st, f"de:advice:{group}", dd["advice"][group]), via="german")
            de_extra = self._german_extra(st, msg, s)
            if de_extra is not None:
                return de_extra
            bridged = self._german_question(st, msg, s)
            if bridged is not None:
                return bridged
            dm = _DISLIKE_DE.match(s)
            if dm:
                # "ich mag keine pilze": a dislike, remembered (in English, like every fact)
                x = (dm.group("x") or dm.group("z") or dm.group("y") or "").strip()
                shown = " ".join(w[:1].upper() + w[1:] for w in x.split())     # German nouns: "Pilze"
                if _RELATABLE_DE.fullmatch(x):
                    return Reply(msg, "smalltalk", self._pick(st, "de:dislike_relatable", dd["dislike_relatable"],
                                                              x=shown), via="german")
                if x in ("fleisch", "fleisch und fisch"):
                    st.uses["diet"] = "vegetarian"            # "ich esse kein Fleisch": food ideas without meat
                    self._learn(st, ["I'm vegetarian."], msg)
                    return Reply(msg, "learned", "Alles klar, kein Fleisch – das merke ich mir für Essensideen!",
                                 via="german")
                self._learn(st, [f"I don't like {x}."], msg)
                return Reply(msg, "learned", self._pick(st, "de:dislike", dd["dislike"], x=shown), via="german")
            ex = experience_de(s) if not (u.kind == "feeling" and len(s.split()) <= 4) else None
            if ex is not None:
                val, topic, person, timeword = ex
                shape = "person" if topic and person else "thing" if topic else "time" if timeword else "plain"
                st.last_exp = {"valence": val, "topic": topic, "person": person, "text": msg,
                               "text_en": _de_advice_hint(s), "turn": st.turn}
                return Reply(msg, "empathy", self._pick(st, f"de:moment:{val}:{shape}", dd["experience"][val][shape],
                                                         topic=topic or ""), via="german")
        if u.kind == "safety":
            st.pending = None
            return Reply(msg, "safety", u.data["response"], via="safety")
        if u.kind == "remember":
            inner = self._turn(st, u.data["english"])
            if inner.kind != "learned":
                return Reply(msg, "unknown", self._pick(st, "de:fallback", de["replies"]["fallback"]), via="german")
            key = "learned_name" if u.data["what"] == "name" else "learned_fact"
            text = self._pick(st, f"de:{key}", de["replies"][key], name=u.data["value"])
            return Reply(msg, "learned", text, source=inner.source, via="german")
        if u.kind == "ask_name":
            if name:
                return Reply(msg, "answer", _fill(de["replies"]["name_known"][0], name=name), via="german")
            st.pending = {"slot": "name", "store": self.bank.fun["questions"]["ask_name"]["store"], "turn": st.turn}
            return Reply(msg, "unknown", de["replies"]["name_unknown"][0], via="german")
        if u.kind == "calc":
            from engramm.chat.tools import calculate
            res = calculate(u.data["expr"])
            if res is not None and res.value is not None:
                shown = u.data["expr"].replace("*", "×").replace("/", "÷")
                return Reply(msg, "tool", f"{shown} = {res.value.replace('.', ',')}", via="tool")
        if u.kind == "intent":
            it = next(i for i in de["intents"] if i["id"] == u.data["id"])
            if it["id"] == "joke":
                st.last_action = {"kind": "joke", "turn": st.turn}
            opts = it.get("responses_named") if name and it.get("responses_named") else it["responses"]
            return Reply(msg, "smalltalk", self._pick(st, f"de:{it['id']}", opts, name=name or ""), via="german")
        if u.kind == "feeling":
            st.last_exp = {"valence": u.data["valence"], "topic": None, "person": False, "text": msg,
                           "text_en": _de_advice_hint(s), "turn": st.turn}
            fe = de["feelings"]
            if u.data["negated"]:
                opts = fe["negated_negative"] if u.data["valence"] == "negative" else fe["negated_positive"]
            else:
                opts = next(c for c in fe["categories"] if c["id"] == u.data["id"])["responses"]
            return Reply(msg, "empathy", self._pick(st, f"de:feeling:{u.data['id']}", opts), via="german")
        if re.match(r"^(?:wer|was|wann|wo|wie|welche[rsmn]?|warum|wieso|weshalb|woher|wohin)\b", s):
            return Reply(msg, "unknown", self._pick(st, "de:knowledge", dd["knowledge_de"]), via="german")
        le = st.last_exp or {}
        if le and st.turn - le.get("turn", -99) <= 2 and len(s.split()) >= 2:
            # "die nachbarn waren laut" after "ich bin müde": more of the same moment
            key = "follow_neg" if le.get("valence") == "negative" else "follow_pos"
            st.last_exp = dict(le, turn=st.turn, text_en=(le.get("text_en") or "") + " " + _de_advice_hint(s))
            return Reply(msg, "empathy", self._pick(st, f"de:life:{key}", dd["life"][key]), via="german")
        return Reply(msg, "unknown", self._pick(st, "de:fallback", de["replies"]["fallback"]), via="german")

    def _german_life(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """German everyday talk that needs the conversation: thanks after a tip or a congratulation,
        a loss and what follows it, facts about you ("wie alt bin ich?"), two facts in one sentence,
        "noch einer", "kenn ich schon", superlatives and short follow-ups ("wo?")."""
        dl = self.bank.de["daily"]["life"]
        la = st.last_action or {}
        le = st.last_exp or {}
        s = s.strip(" ?!.")
        if _NA_DE.fullmatch(s):
            return Reply(msg, "smalltalk", self._pick(st, "de:life:greeting", dl["greeting"]), via="german")
        th = _THANKS_DE.fullmatch(s)
        if th:
            rest = th.group("rest") or ""
            key = "thanks_listen" if re.search(r"zuh(?:ö|oe)r|da bist|geredet", rest) else \
                "thanks_idea" if (re.search(r"idee|tipp|rat|hilft|probier|mach ich", rest) or th.group("idea")) else \
                "thanks_praise" if le.get("valence") == "positive" and st.turn - le.get("turn", -99) <= 2 else "thanks"
            return Reply(msg, "smalltalk", self._pick(st, f"de:life:{key}", dl[key]), via="german")
        g = _LOSS_DE.search(s)
        if g:
            noun = (g.group("n") or g.group("n2") or "").lower()
            key = "grief_pet" if noun in _PETS_DE else "grief_f" if noun in _FEMALE_DE else "grief"
            st.last_exp = {"valence": "negative", "topic": noun or None, "person": True, "text": msg,
                           "text_en": "someone I love died", "turn": st.turn}
            st.uses["grief_de"] = ["sie" if key == "grief_f" else "er", st.turn]
            return Reply(msg, "empathy", self._pick(st, f"de:life:{key}", dl[key]), via="german")
        gd = st.uses.get("grief_de")
        if gd and st.turn - gd[1] <= 4:
            m = re.fullmatch(r"(?:er|sie|es) (?:war|wurde|ist) (?:nur |schon |erst )?(\d{1,3})(?: jahre(?: alt)?)?", s)
            if m:
                return Reply(msg, "empathy", self._pick(st, "de:life:grief_age", dl["grief_age"], x=m.group(1)), via="german")
        m = re.fullmatch(r"ich vermisse (ihn|sie|es|meine[nm]? \w+)(?: (?:so|sehr|total|einfach) ?(?:sehr)?)?", s)
        if m:
            x = m.group(1)
            y = {"ihn": "er", "sie": "sie", "es": "es"}.get(x, "das")
            return Reply(msg, "empathy", self._pick(st, "de:life:miss", dl["miss"], x=x, y=y), via="german")
        if re.fullmatch(r"(?:und )?noch (?:einer|einen|eins|ein witz|einen witz)|nochmal", s) and la.get("kind") == "joke":
            return self._german(st, "erzähl mir einen witz")
        if _SEEN_DE.fullmatch(s) and la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3:
            rep = self.everyday.recommend(st, msg, la["kind"][4:], la.get("genre"), more=True, lang="de")
            body = rep.text.split("\n", 1)[1] if "\n" in rep.text else rep.text
            rep.text = self._pick(st, "de:life:seen", dl["seen"]) + "\n" + body
            return rep
        hm = re.fullmatch(r"(?:etwas|was|lieber was|eher was|ideen) (?:für|fürs) (zuhause|zu hause|drinnen|daheim)", s)
        if hm and la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3:
            return self.everyday.recommend(st, msg, la["kind"][4:], "home", lang="de")
        ev = _EVENT_DE_RX.search(s)
        if ev:
            what = ev.group("e") or ev.group("e2")
            st.uses["event_de"] = [what, st.turn]
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "text_en": "", "turn": st.turn}
            art = {"vorstellungsgespräch": "deinem Vorstellungsgespräch", "prüfung": "deiner Prüfung",
                   "klausur": "deiner Klausur", "präsentation": "deiner Präsentation", "date": "deinem Date",
                   "fahrprüfung": "deiner Fahrprüfung"}.get(what, "deinem Termin")
            return Reply(msg, "empathy", self._pick(st, "de:life:event", dl["event"], x=art,
                                                    X=what[:1].upper() + what[1:]), via="german")
        evu = st.uses.get("event_de")
        if evu and st.turn - evu[1] <= 3 and re.search(r"\b(?:nervös|aufgeregt|angst|bammel|panik|unsicher|lampenfieber)\b", s):
            return Reply(msg, "empathy", self._pick(st, "de:life:event_nerves", dl["event_nerves"]), via="german")
        if evu and st.turn - evu[1] <= 4 and re.fullmatch(r"(?:hast du |ein paar |irgendwelche )?(?:tipps|tips|einen tipp|rat|ratschläge)(?: für mich)?|"
                                                          r"wie bereite ich mich (?:am besten )?vor|was soll ich beachten", s):
            key = evu[0] if evu[0] in dl["event_tips"] else ("prüfung" if evu[0] in ("klausur", "fahrprüfung") else "generic")
            return Reply(msg, "smalltalk", self._pick(st, f"de:life:tips:{key}", dl["event_tips"][key]), via="german")
        if re.fullmatch(r"(?:kannst du )?(?:mir )?(?:die )?daumen drücken|drück(?:st du)? mir (?:die|beide) daumen|wünsch mir glück", s):
            return Reply(msg, "smalltalk", self._pick(st, "de:life:thumbs", dl["thumbs"]), via="german")
        if re.search(r"\b(?:(?:meinen|meine) (?:job|arbeit|stelle|arbeitsstelle) verloren|(?:wurde|bin|worden) (?:heute )?(?:gekündigt|entlassen)|mir wurde gekündigt|ich wurde rausgeschmissen)\b", s):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg,
                           "text_en": "i lost my job", "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:life:job_lost", dl["job_lost"]), via="german")
        ll = getattr(st, "last_list", None) or {}
        wo = re.fullmatch(r"(?:aber |oh |hm+ )?ich (?:hab|habe) (?:keine?n?|kein) (?P<x>[a-zäöüß]+)(?: (?:mehr|da|zu hause|zuhause|im haus))?", s)
        if wo and ll.get("kind") == "food" and st.turn - ll.get("turn", -99) <= 3:
            x = wo.group("x")
            needs = [x[:-1] if x.endswith(("n", "e")) and len(x) > 4 else x] + _NEEDS_DE.get(x, [])
            texts = ll.get("texts") or []
            hit = [t for t in texts if any(n in t.lower() for n in needs)]
            rest = [t for t in texts if t not in hit]
            shown = x[:1].upper() + x[1:]
            if hit and rest:
                short = lambda t: re.sub(r"^(?:ein|eine|einen)\s+", "", re.split(r" –|,| mit | auf | wenn ", t)[0].strip())
                return Reply(msg, "smalltalk", self._pick(st, "de:life:without_skip", dl["without_skip"], x=shown,
                                                          dish="das " + short(hit[0]) if not short(hit[0]).lower().startswith(("pizza", "suppe")) else "die " + short(hit[0]),
                                                          rest=" oder ".join(short(r) for r in rest)), via="german")
            return Reply(msg, "smalltalk", self._pick(st, "de:life:without_fine", dl["without_fine"], x=shown), via="german")
        if re.fullmatch(r"(?:ok(?:ay)?|gut|alles klar|na gut|super),? dann (?:eben |halt |wohl |doch )?[a-zäöüß ]{2,30}", s) and \
                (ll.get("kind") == "food" or la.get("kind", "").startswith("rec:")) and st.turn - ll.get("turn", -99) <= 4:
            return Reply(msg, "smalltalk", self._pick(st, "de:life:decided", dl["decided"]), via="german")
        if re.search(r"\bguten appetit\b|\blass es dir schmecken\b|\bmahlzeit\b", s):
            return Reply(msg, "smalltalk", self._pick(st, "de:life:appetit", dl["appetit"]), via="german")
        fg = re.fullmatch(r"vergiss,? (?:bitte )?(?P<w>wo ich wohne|wie ich heiße|meinen namen|wo ich arbeite|was ich beruflich mache|alles(?: über mich)?|wie alt ich bin)(?: bitte)?", s)
        if fg:
            english = {"wo ich wohne": "forget where I live", "wie ich heiße": "forget my name", "meinen namen": "forget my name",
                       "wo ich arbeite": "forget where I work", "was ich beruflich mache": "forget my job",
                       "wie alt ich bin": "forget my age"}.get(fg.group("w"), "forget everything about me")
            rep = self._turn(st, english)
            key = "forgot" if rep.kind == "forgot" else "forget_none"
            return Reply(msg, rep.kind if rep.kind == "forgot" else "nothing", self._pick(st, f"de:life:{key}", dl[key]), via="german")
        if re.fullmatch(r"was weißt du (?:alles )?über mich|was hast du dir (?:über mich )?gemerkt|was weißt du von mir", s):
            return self._german_known(st, msg)
        me = next(((en, tpl) for rx, en, tpl in _ME_Q_DE if rx.fullmatch(s)), None)
        if me:
            return self._german_me(st, msg, *me)
        two = self._german_two_facts(st, msg, s)
        if two is not None:
            return two
        sup = self._german_superlative(st, msg, s)
        if sup is not None:
            return sup
        last = st.uses.get("de_last_q")
        if s in ("wo", "und wo", "wo denn", "und wo genau") and last and st.turn - last[0] <= 2 and "geboren" in last[1]:
            return self._german_question(st, msg, re.sub(r"^(?:und )?(?:wann|in welchem jahr)", "wo", last[1]))
        return None

    def _german_known(self, st: DialogState, msg: str) -> Reply:
        """"was weißt du über mich?": what you told, in German where the kind of fact is known."""
        from engramm.chat.german_bridge import de_value
        dl = self.bank.de["daily"]["life"]
        self.bot.refresh()
        lines = []
        for f in self.bot.facts.facts:
            if not f.subject.startswith(USER):
                continue
            v = de_value(f.object)
            v = v[:1].upper() + v[1:] if f.subject == USER and not v.isdigit() else v
            r = set(f.relation)
            if f.subject != USER:
                noun = f.subject.partition(":")[2]
                line = None
            elif "#name" in r:
                line = f"Du heißt {v}."
            elif "#home" in r and "#origin" not in r and "#birth" not in r:
                line = f"Du wohnst in {v}."
            elif "#origin" in r:
                line = f"Du kommst aus {v}."
            elif "#job" in r:
                line = f"Du arbeitest als {v}."
            elif "#age" in r:
                line = f"Du bist {v}."
            elif "#dislike" in r:
                line = f"Du magst kein{'e' if v.endswith(('n', 'e')) else ''} {v}."
            elif "#fav" in r or "#food" in r:
                line = f"Du magst {v}."
            else:
                line = None
            if line is None:
                sent = personal_sentence(f.subject, f.relation, f.object, f.sentence)
                line = sent
            if line and line not in lines:
                lines.append(line)
        if not lines:
            return Reply(msg, "memory", self._pick(st, "de:life:known_none", dl["known_none"]), via="german")
        return Reply(msg, "memory", dl["known_head"] + "\n" + "\n".join("• " + x for x in lines[:12]), via="german")

    def _german_me(self, st: DialogState, msg: str, english: str, template: str) -> Reply:
        """"wie alt bin ich?" — the English fact memory, answered in German."""
        dl = self.bank.de["daily"]["life"]
        if template.startswith("list:"):
            label = template[5:]
            self.bot.refresh()
            vals = list(dict.fromkeys(f.object for f in self.bot.facts.facts
                                      if f.subject == USER and label in f.relation))
            if not vals:
                return Reply(msg, "unknown", self._pick(st, "de:life:me_unknown", dl["me_unknown"]), via="german")
            shown = [" ".join(w[:1].upper() + w[1:] for w in v.split()) for v in vals]
            joined = shown[0] if len(shown) == 1 else ", ".join(shown[:-1]) + " und " + shown[-1]
            head = "Du magst nicht: " if label == "#dislike" else "Du magst: "
            return Reply(msg, "answer", head + joined + ".", via="german")
        rep = self._question(st, english)
        if rep.kind != "answer" or not rep.answer:
            return Reply(msg, "unknown", self._pick(st, "de:life:me_unknown", dl["me_unknown"]), via="german")
        from engramm.chat.german_bridge import de_value
        value = de_value(str(rep.answer))
        value = re.sub(r"^(?:an?|the) ", "", value)
        return Reply(msg, "answer", template.format(x=value[:1].upper() + value[1:]), answer=rep.answer,
                     source=rep.source, via="german")

    def _german_two_facts(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """"ich bin 34 und arbeite als lehrer": both facts, each into the memory."""
        from engramm.chat.german import statement_de
        if " und " not in s:
            return None
        parts = [x.strip() for x in s.split(" und ")]
        if len(parts) != 2:
            return None
        if re.match(r"(?:arbeite|wohne|lebe|komme|heiße|heisse|bin)\b", parts[1]):
            parts[1] = "ich " + parts[1]
        found = [statement_de(x) for x in parts]
        if not all(found):
            return None
        said = []
        for what, value, english, shown in found:
            self._turn(st, english)
            said.append(shown)
        return Reply(msg, "learned", self._pick(st, "de:life:statements_two", self.bank.de["daily"]["life"]["statements_two"],
                                                x=" und ".join(said)), via="german")

    def _german_superlative(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """"was ist der längste fluss der welt?", "und der zweite?" — from the fact bank, in German."""
        if self.kgqa is None:
            return None
        from engramm.kb import superlative
        from engramm.chat.german_bridge import _GERMAN_OF
        m = _SUPER_DE.fullmatch(s)
        last = st.uses.get("de_super")
        rank = 1
        if m:
            adj, noun = m.group("adj"), m.group("noun")
        else:
            r = re.fullmatch(r"(?:und )?(?:der|die|das) (zweite|dritte|zweithöchste|zweitlängste|zweitgrößte|dritthöchste|drittlängste|drittgrößte)", s)
            if not (r and last and st.turn - last[2] <= 3):
                return None
            adj, noun = last[0], last[1]
            rank = 2 if r.group(1).startswith("zweit") else 3
        en_adj = {"höchste": "tallest", "längste": "longest", "größte": "largest", "kleinste": "smallest",
                  "bevölkerungsreichste": "most populous"}[adj]
        en_noun = {"berg": "mountain", "fluss": "river", "see": "lake", "land": "country", "gebäude": "building",
                   "hochhaus": "building"}[noun]
        try:
            ans = superlative.answer(self.kgqa.kb.db, f"what is the {en_adj} {en_noun} in the world", rank=rank)
        except Exception:
            return None
        if ans is None:
            return None
        st.uses["de_super"] = [adj, noun, st.turn]
        self.bot.context.update({"answer": ans.title, "atype": None, "mention": ans.title})
        name = _GERMAN_OF.get(ans.title, ans.title)
        if noun in ("fluss", "see") and not name.lower().startswith(("lake", "see ")):
            name = ("der " if noun == "fluss" else "das " if name.endswith("Meer") else "der ") + name
        v = ans.value
        value = {"height": f"{v:,.0f} m hoch", "tall": f"{v:,.0f} m hoch", "length": f"rund {v / 1000:,.0f} km lang",
                 "area": f"rund {v / 1e6:,.0f} km² groß" if v >= 1e6 else f"rund {v / 1e6:,.2f} km² groß",
                 "people": f"rund {v:,.0f} Einwohner"}[ans.kind].replace(",", "X").replace(".", ",").replace("X", ".")
        art = "Das" if noun in ("land", "gebäude", "hochhaus") else "Der"
        nth = {1: "", 2: "zweit", 3: "dritt"}[rank]
        text = _fill(self.bank.de["daily"]["life"]["super"], art=art, adj=nth + adj if rank > 1 else adj,
                     noun=noun[:1].upper() + noun[1:], name=name, value=value)
        return Reply(msg, "answer", text, answer=ans.title, source={"kind": "kb", "source": "dbpedia", "key": ans.title},
                     via="kb", confidence=1.0)

    def _german_extra(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """German everyday tools and follow-ups: the time and the date, "15 Prozent von 80", and
        "und von Italien?" after "Was ist die Hauptstadt von Spanien?"."""
        now = self.clock() if self.clock else dt.datetime.now()
        if re.fullmatch(r"(?:sag mal,? )?(?:wie spät ist es(?: gerade| jetzt)?|wie viel uhr ist es|wieviel uhr ist es|"
                        r"welche uhrzeit haben wir|was ist die uhrzeit)", s):
            return Reply(msg, "tool", f"Es ist {now:%H:%M} Uhr (laut der Uhr dieses Computers).", via="tool")
        if re.fullmatch(r"(?:sag mal,? )?(?:welcher tag ist (?:heute|es)|welches datum (?:haben wir|ist heute)(?: heute)?|"
                        r"der wievielte ist heute|was für ein tag ist heute|welchen tag haben wir(?: heute)?)", s):
            days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                      "November", "Dezember"]
            return Reply(msg, "tool", f"Heute ist {days[now.weekday()]}, der {now.day}. {months[now.month - 1]} {now.year}.",
                         via="tool")
        m = re.fullmatch(r"(?:was (?:ist|sind|ergibt|ergeben)|wie ?viel (?:ist|sind)|rechne|berechne) (\d+(?:[.,]\d+)?) ?"
                         r"(?:%|prozent) (?:von|aus) (\d+(?:[.,]\d+)?)", s)
        if m:
            a, b = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
            v = a * b / 100
            shown = (f"{v:.2f}".rstrip("0").rstrip(".")).replace(".", ",")
            st.uses["last_calc"] = [st.turn, str(v)]
            return Reply(msg, "tool", f"{m.group(1)} % von {m.group(2)} sind {shown}.", answer=shown, via="tool")
        m = re.fullmatch(r"und (?:von |in |für |bei |mit |über )?(?P<x>[a-zäöüß][a-zäöüß .-]{1,30})", s)
        last = st.uses.get("de_last_q")
        if m and re.search(r"\b(?:wie|was|wer|wann|wo|warum|hat|ist|sind|war|viele|welche[rsnm]?)\b", m.group("x")):
            m = None                                     # "und wie viele einwohner hat sie?" is a new question
        if m and last and st.turn - last[0] <= 3 and last[2] and last[2] in last[1]:
            again = last[1].replace(last[2], m.group("x").strip(), 1)
            return self._german_question(st, msg, again)
        return None

    def _german_question(self, st: DialogState, msg: str, s: str) -> Reply | None:
        from engramm.chat.german_bridge import de_sentence, de_value, to_english
        ment = self.bot.context.get("mention")
        ans_ = self.bot.context.get("answer")
        if isinstance(ans_, str) and ans_ and not re.search(r"\d", ans_) and len(ans_.split()) <= 4:
            ment = ans_                                  # "die Hauptstadt … ist Canberra" → "sie" is Canberra
        s = re.sub(r"^(?:und|also|ok|okay) ", "", s)
        if ment and re.search(r"\b(?:hat|ist|liegt|wurde|war|heißt) (?:sie|er|es)\b|\b(?:sie|er|es) (?:hat|ist|liegt)\b", s) and \
                not re.search(r"\bgeboren|gestorben\b", s):
            # "und wie viele einwohner hat sie?" after Canberra: the place just named
            s = re.sub(r"\b(?:sie|er|es)\b", ment.lower(), s, count=1)
        hit = to_english(s)
        if hit is None:
            return None
        english, kind, x_en, x_de = hit
        st.uses["de_last_q"] = [st.turn, s, (x_de or "").lower()]
        dd = self.bank.de["daily"]
        if kind == "about":
            rep = self._about(st, Unit("about", english, english.lower(), data={"kind": "tell", "topic": x_en}))
            if rep.kind == "about":
                rep.text = f"{dd['english_text']} {rep.text}"
                rep.message = msg
                return rep
            rep = self._question(st, english.replace("tell me about", "who is"))
            if rep.kind != "answer":
                return Reply(msg, "unknown", self._pick(st, "de:unknown", dd["unknown"]), via="german")
        elif kind == "compare":
            rep = self.everyday.compare(st, english, english.lower())
            if rep is None or rep.kind != "answer":
                return Reply(msg, "unknown", dd["compare_none"], via="german")
            rep.text = _de_compare(rep.text, s)
            rep.message = msg
            return rep
        else:
            pron = re.search(r"\b(?:er|sie|ihn|ihm|ihr|sein|seine|ihre)\b", s)
            rep = self._question(st, english + "?")
            if rep.via == "clarify" or (pron and rep.kind != "answer"):
                return Reply(msg, "unknown", dd["who_mean"].replace("{x}", pron.group(0) if pron else x_en), via="clarify")
        rep.message = msg
        if rep.kind != "answer":
            rep.text = self._pick(st, "de:unknown", dd["unknown"])
            return rep
        wm = _WHO_MADE_DE.fullmatch(s.strip(" ?.!"))
        if wm and rep.answer and len(str(rep.answer).split()) <= 14:
            from engramm.chat.german_bridge import de_value
            art = (wm.group("art") or "").strip()
            thing = wm.group("x").strip()
            thing = " ".join(w if w in ("von", "der", "die", "das", "und", "des", "of", "the", "de", "da") else w[:1].upper() + w[1:]
                             for w in thing.split())
            head = f"{art[:1].upper() + art[1:]} {thing}" if art else thing[:1].upper() + thing[1:]
            rep.text = f"{head} wurde von {de_value(str(rep.answer))} {wm.group('v')}."
            return rep
        if rep.via == "kb":
            name = re.sub(r"\s*\([^)]*\)$", "", (rep.source or {}).get("key") or x_en)
            if x_de and x_de.lower() != x_en.lower() and x_en.lower() == name.lower() and \
                    x_en.lower() not in ("he", "she", "it", "him", "her"):
                name = x_de                     # "Frankreich", as the user wrote it
            sent = de_sentence(kind, name, rep.answer or "", rep.text)
            if sent:
                rep.text = sent
                return rep
        rep.text = f"{dd['english_text']} {rep.text}"
        return rep

    # -- the turn -----------------------------------------------------------------------------

    def turn(self, st: DialogState, message: str) -> Reply:
        t0 = time.time()
        bot = self.bot
        bot.context = dict(st.ctx)
        msg = " ".join(message.strip().split())
        self._spelled = None
        try:
            rep = self._turn(st, msg)
            if self._spelled and not rep.resolved:
                rep.resolved = self._spelled          # shown as "I read this as …"
        finally:
            st.ctx = dict(bot.context)
            bot.context = dict(FRESH_CTX)
        rep.message = message
        rep.seconds = time.time() - t0
        if rep.text and rep.text == st.last_reply and normalise(message) != normalise(st.last_message or ""):
            if rep.kind == "unknown":
                de_again = (self.bank.de or {}).get("daily", {}).get("unknown_again") if st.lang == "de" else None
                rep.text = self._pick(st, "de:unknown_again" if de_again else "daily:unknown_again",
                                      de_again or self.bank.daily["unknown_again"])
        if rep.via == "facts" and rep.text:
            rep.text = _MONTH_LOW.sub(lambda m: m.group(0)[:1].upper() + m.group(0)[1:], rep.text)  # "on june 5" → "June 5"
        st.last_message = message
        st.last_kind = rep.kind
        self._track(st, rep, msg)
        if rep.via != "gibberish":
            st.gib = 0
        st.turn += 1
        st.last_reply = rep.text
        st.recent = (st.recent + [rep.text])[-RECENT:]
        return rep

    def _track(self, st: DialogState, rep: Reply, msg: str) -> None:
        """Remember what the conversation is about: the topic (for "tell me more", "is it good?",
        pronouns) and the last question (for "where?", "and Germany?"), and what the reply offers."""
        src = rep.source or {}
        if rep.via == "kb" and src.get("key"):
            title = src["key"]
            st.topic = {"title": title, "name": re.sub(r"\s*\([^)]*\)$", "", title), "turn": st.turn}
        elif rep.via in ("about", "facts-bank") and src.get("key"):
            st.topic = {"title": src["key"], "name": re.sub(r"\s*\([^)]*\)$", "", src["key"]), "turn": st.turn}
        elif rep.kind == "answer" and rep.via == "lookup" and rep.answer and rep.answer[:1].isupper():
            st.topic = {"title": rep.answer, "name": rep.answer, "turn": st.turn}
        if rep.kind in ("answer", "unknown") and rep.via in ("kb", "lookup", "about", "facts", "memory") \
                and message_type(rep.resolved or msg) == "question":
            st.last_q = rep.resolved or msg
            if re.search(r"\s[A-Z]", st.last_q):
                st.last_q_named = st.last_q
        if rep.kind == "unknown" and rep.via == "lookup":
            # an unanswered question must not leave an old name behind for "he" or "it"
            st.ctx.update({"answer": None, "atype": None})
        if st.offer is None or st.offer.get("turn") != st.turn:
            kind = offer_in(rep.text)
            st.offer = {"kind": kind, "turn": st.turn} if kind else None
        theme = _theme_of(st, rep)
        if theme:
            recap = st.uses.setdefault("recap", [])
            if theme in recap:
                recap.remove(theme)
            recap.append(theme)
            del recap[:-12]

    def _turn(self, st: DialogState, msg: str) -> Reply:
        if not msg:
            return Reply(msg, "nothing", "Please type something.")
        if re.fullmatch(r"(?:\.{2,}|…+)", msg):                        # "...": still thinking
            return Reply(msg, "smalltalk", self._pick(st, "daily:dots", self.bank.daily["dots"]), via="smalltalk")
        if re.fullmatch(r"\?{2,}!*|\?!+|!\?+", msg):                    # "???": that was unclear
            return Reply(msg, "smalltalk", self._pick(st, "daily:puzzled", self.bank.daily["puzzled"]), via="clarify")
        de = self.bank.de
        if de and (is_german(msg, de) or _NA_DE.fullmatch(normalise(msg).strip(" ?!."))) and \
                self.bank.safety_rule(normalise(msg, fillers=False)) is None:
            return self._german(st, msg)
        if de and st.lang == "de":
            from engramm.chat.german import neutral_de, normalise_de
            if neutral_de(normalise_de(msg)) is not None or re.fullmatch(r"(?:noch )?mehr|nochmal", normalise_de(msg)) \
                    or re.fullmatch(r"(?:hey|hi|hallo|hello|moin|servus|yo|huhu)+(?: (?:hey|hi|du|engramm))?", normalise_de(msg)) \
                    or gibberish(msg, self.speller.known if self.speller is not None else None) \
                    or (_GENRE_DE.match(normalise_de(msg)) and re.sub(r"(?:es|e|er|en)$", "", _GENRE_DE.match(
                        normalise_de(msg)).group("g")) in _GENRE_DE_MAP and not re.search(r"\b(?:something|anything|quick)\b", msg.lower())):
                return self._german(st, msg)      # "haha", "ok", "ja" in a German conversation stay German
            if _clearly_english(msg, de):
                st.lang = "en"
            elif len(re.findall(r"[a-zäöüß]+", msg.lower())) >= 2:
                return self._german(st, msg)      # "die nachbarn waren laut": no English word, stays German
        msg = expand_chat(msg)                            # "wats ur name" → "what's your name"
        msg = self._prefer_correction(msg)                # "actually i prefer ramen" right after a favourite
        nc = _NAME_FIX.match(msg.strip())
        if nc and st.last_kind == "learned" and re.search(r"\b(?:my name is|call me|i'm|im|i am)\b", st.last_message or "", re.I):
            name = nc.group("x")
            msg = f"My name is {name[:1].upper() + name[1:]}."      # "no wait, it's alexander" right after the name
        msg = _split_self_statements(msg)                 # "my name is Sam and I'm a teacher": two facts
        pet = st.uses.get("pet")
        if pet and st.turn - pet[1] <= 3:
            m = _PET_NAME.match(msg.strip())              # "her name is luna" after "I have a cat"
            if m:
                name = m.group("x").strip(" .!")
                msg = f"My {pet[0]} is called {name[:1].upper() + name[1:]}."
            m = _PET_AGE.match(msg.strip())               # "she's 3", "he's 2 months old"
            if m:
                unit = (m.group("u") or " years old").strip()
                unit = unit if unit.endswith("old") else unit.replace("yrs", "years") + " old"
                msg = f"My {pet[0]} is {m.group('n')} {unit}."
                st.uses["pet"] = [pet[0], st.turn]
            mb = _PET_BREED.match(msg.strip()) if not m else None
            if mb and not re.search(r"\b(?:good|bad|cute|sweet|tired|asleep|sleeping|hungry|so|very|really|little)\b", mb.group("b")):
                msg = f"My {pet[0]} is a {mb.group('b').strip()}."          # "he's a golden retriever"
                st.uses["pet"] = [pet[0], st.turn]
                st.uses["pet_breed"] = [mb.group("b").strip(), st.turn]
            if msg.startswith(f"My {pet[0]} is called "):
                st.uses["pet_name"] = msg[len(f"My {pet[0]} is called "):].rstrip(".")
                st.uses["pet"] = [pet[0], st.turn]
        pbq = st.uses.get("pet_breed")
        if pet and pbq and re.fullmatch(r"(?i)(?:and )?what (?:breed|kind of dog|kind of cat|type of dog) is (?:he|she|it|my \w+|[A-Za-z]+)\??", msg.strip()):
            name = st.uses.get("pet_name") or f"Your {pet[0]}"
            return Reply(msg, "answer", f"{name} is a {pbq[0]}.", answer=pbq[0], via="facts")
        pn = st.uses.get("pet_name")
        if pet and pn and re.search(rf"\b{re.escape(pn)}\b", msg, re.I) and msg.rstrip().endswith("?") or \
                (pet and pn and re.match(r"(?i)^(?:how|what|when|where|who|is|does)\b", msg) and re.search(rf"\b{re.escape(pn)}\b", msg, re.I)):
            msg = re.sub(rf"(?i)\b{re.escape(pn)}\b", f"my {pet[0]}", msg, count=1)   # "how old is buddy?"
        if pet and st.turn - pet[1] <= 8:
            m = _PET_PRON_Q.match(msg.strip())            # "how old is she?" → "how old is my cat?"
            if m and m.group("head"):
                msg = f"{m.group('head')} my {pet[0]}{m.group('tail') or '?'}"
            elif m:
                msg = f"what's my {pet[0]}'s {m.group('what')}?"
        if re.fullmatch(r"(?i)(?:and |so )?(?:what'?s|what is|do you (?:know|remember)|tell me) my age\??", msg.strip()):
            msg = "how old am i?"                       # the age is a number fact (#age)
        have = st.uses.get("have_noun")
        if have and st.turn - have[1] <= 2:               # "their names are Mia and Leo" after "I have two kids"
            m = _THEIR_NAMES.match(msg.strip()) or _BARE_NAMES.fullmatch(msg.strip(" .!"))
            if m:
                msg = f"My {have[0]} are called {(m.group(1) if m.re is _THEIR_NAMES else m.group(0)).strip(' .!')}."
        norm = normalise(msg)
        own = self._about_me(st, msg, norm)
        if own is not None:
            return own
        lk = _I_LIKE.match(norm)
        if lk:
            st.uses["last_like"] = [st.turn, _place_case(lk.group("x").strip(" .!"))]
        life = self._life(st, msg, norm)
        if life is not None:
            return life
        if _DAY_NOUN.match(norm):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "daily:day_bad", self.bank.daily["day_bad"], x="it"),
                         via="empathy")
        dm = _DAY_WAS.match(norm)
        if dm:
            if dm.group("bad"):
                st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            key = "day_bad" if dm.group("bad") else "day_good"
            what = dm.group("what")
            what = "your day" if what in ("today", "it", "the day", "my day") else what.replace("my ", "your ")
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", self.bank.daily[key], x=what), via="empathy")
        if _PET_PEEVE.match(msg.strip()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:pet_peeve", self.bank.daily["pet_peeve"]),
                         via="empathy")
        dm = _DISLIKE.match(msg.strip())
        if dm and _RELATABLE.fullmatch(dm.group("x").strip().lower()):
            x = dm.group("x").strip().lower()
            return Reply(msg, "smalltalk", self._pick(st, "daily:dislike_relatable", self.bank.daily["dislike_relatable"],
                                                      x=x[:1].upper() + x[1:] if x.endswith("days") else x),
                         via="empathy")
        if dm:
            # "i dont like movies": remember it as a dislike and ask what they do enjoy
            x = dm.group("x").strip()
            rep = self._learn(st, [msg], msg)
            if rep.kind == "learned":
                rep.text = self._pick(st, "daily:dislike", self.bank.daily["dislike"], x=x)
            st.last_action = {"kind": "dislike", "turn": st.turn, "x": x}
            return rep
        la_kind = (st.last_action or {}).get("kind")
        if _DOUBT.fullmatch(norm) and st.last_kind == "answer" and st.last_fact and st.last_fact.get("evidence"):
            return self._why(st, msg)
        mild = re.fullmatch(r"(?:cool|neat|nice|ok cool|oh nice)[!.]*", norm) is not None
        if _SURPRISE.fullmatch(norm) and st.last_reply and (
                (st.last_kind in ("answer", "about") and not mild) or
                (la_kind == "fun_fact" and st.turn - (st.last_action or {}).get("turn", -99) <= 1)):
            # "that's crazy" right after a fact: go along with it, as a person would
            return Reply(msg, "smalltalk", self._pick(st, "daily:surprise", self.bank.daily["surprise"]), via="smalltalk")
        if _SURPRISE.fullmatch(norm) and st.last_kind == "unknown" and st.last_reply:
            return Reply(msg, "smalltalk", self._pick(st, "daily:surprise_unknown", self.bank.daily["surprise_unknown"]),
                         via="smalltalk")
        played = self.everyday.game_answer(st, msg, norm)          # a quiz question or riddle waiting
        if played is not None:
            return played
        offer = st.offer
        st.offer = None
        if offer and offer.get("turn") == st.turn - 1:
            ans = short_answer(norm)
            if ans is None and offer["kind"] in ("joke_or_fact", "joke", "fact") and \
                    re.fullmatch(r"(?:(?:a|an|the|one|ok|okay|sure|yes|yeah)\s+)*(?:fun |interesting )?(?:joke|fact)"
                                 r"(?:\s+please)?", norm):
                ans = "yes"
            if ans is not None:
                took = self.everyday.take_offer(st, msg, norm, offer, ans)
                if took is not None:
                    return took
        le = st.last_exp
        if le and le.get("turn") == st.turn - 1 and st.last_reply.rstrip().endswith("?"):
            ans = short_answer(norm)
            if ans == "yes":
                return Reply(msg, "smalltalk", self._pick(st, "daily:offer:listen", self.bank.daily["offers"]["listen"]),
                             via="empathy")
            if ans == "no":
                st.offer = {"kind": "joke_or_fact", "turn": st.turn}
                return Reply(msg, "smalltalk", self._pick(st, "daily:moment:no", self.bank.daily["moment_no"]),
                             via="empathy")
        if _ANOTHER.match(norm):
            again = self._again(st, msg)
            if again is not None:
                return again
        wh = bare_followup(msg)
        if wh and st.last_q:
            rebuilt = rebuild_question(st.last_q, wh)
            if rebuilt:
                msg = self._spelled = rebuilt    # "where?" → "Where was William Shakespeare born?"
        expanded = self._ellipsis(st, msg)
        if expanded is not None:
            msg = self._spelled = expanded      # shown as "I read this as …"
        from engramm.web.atlas import news_request
        is_news, news_topic = news_request(msg)
        if is_news:
            return self._news(st, msg, news_topic)
        units = classify(msg, self.bank, self._now())
        if self.speller is not None and len(units) == 1 and units[0].act == "statement":
            first = msg.split()[0]
            if not self.speller.known(first) and self.speller.fix_word(first).lower() in _QUESTION_WORDS:
                units = classify(self.speller.fix(msg).rstrip(" .!") + "?", self.bank, self._now())
        if self.speller is not None and all(u.act in ("question", "about") for u in units):
            fixed = self.speller.fix(msg)       # typos and CAPITALS, only in questions (names stay as told)
            if fixed != msg and units[0].act == "question" and not fixed.rstrip().endswith("?"):
                fixed = fixed.rstrip(" .!") + "?"   # still a question after the fix
            if fixed != msg:
                units = classify(fixed, self.bank, self._now())
                msg = self._spelled = fixed
        if units[0].act == "safety":
            st.pending = None
            return Reply(msg, "safety", units[0].data["response"], via="safety")
        pending, st.pending = st.pending, None
        if pending and pending.get("turn") == st.turn - 1:          # asked in the previous turn
            filled = self._fill_pending(st, pending, msg, units)
            if filled is not None:
                return filled
        known = self.speller.known if self.speller is not None else None
        if gibberish(msg, known) and not any(u.act in ("intent", "tool", "safety") and u.intent != "gibberish"
                                             for u in units):
            st.gib += 1
            key = "first" if st.gib <= 1 else "again"
            return Reply(msg, "unknown", self._pick(st, f"daily:gib:{key}", self.bank.daily["gibberish"][key]),
                         via="gibberish")
        if len(units) == 2 and units[0].act == "intent" and units[0].intent in ("yes", "no", "ack") and \
                units[1].act == "question" and not (pending and pending.get("turn") == st.turn - 1):
            units = units[1:]                  # "yeah. anyway what should I cook": the question is the message
            msg = units[0].text
        if len(units) == 1 and units[0].act not in ("safety", "forget", "remember", "tool", "writing"):
            req = self.everyday.request(st, msg, normalise(msg))
            if req is not None:
                return req
        if st.last_draft is not None and st.turn - st.draft_turn <= 4:
            from engramm.chat.writing import edit_command, writing_request
            cmd = edit_command(msg) if writing_request(msg) is None else None
            if cmd is not None:
                return self._edit_draft(st, msg, *cmd)
        if st.rps:
            st.rps = False
            m = re.fullmatch(r"(?:i (?:choose|pick|take) )?(rock|paper|scissors)", normalise(msg))
            if m:
                return self._rps(st, msg, m.group(1))
        if self.device is not None and len(units) == 1 and units[0].act in ("question", "statement"):
            hit = self.device.group(msg)
            # questions about the user ("when is my dentist appointment?") are memory questions
            if hit is not None and units[0].act == "question" and (hit[0] != "online" or re.search(r"\bmy\b", msg, re.I)):
                hit = None
            mt = _MEASURE_TOPIC.match(msg.strip())
            if hit is not None and mt and not re.fullmatch(r"(?:it|outside|today|the weather|out)", mt.group("t").strip(), re.I):
                hit = None
            # "I have an exam tomorrow" tells ENGRAMM something to remember; only requests are commands
            if hit is not None and units[0].act == "statement" and re.match(r"(?:i|i'm|im|i've|my|we|we're|our)\b", msg, re.I):
                hit = None
            if hit is not None:
                return Reply(msg, "unknown", self._reply(st, f"device.{hit[0]}"), via="device")
        parts: list[_Part] = []
        main: Reply | None = None
        learn: list[Unit] = []
        quiet: list[Unit] = []
        content = any(u.act not in ("intent", "empty") or (u.intent and self._is_content_intent(u.intent))
                      for u in units)
        seen_intents: set[str] = set()       # "bye. see you": one goodbye, not two
        units = [u for u in units if not (u.act == "intent" and u.intent and
                                          (u.intent in seen_intents or seen_intents.add(u.intent)))]
        for u in units:
            if u.act in ("statement", "feeling") and self.everyday.activity_title(u.text):
                learn.append(u)                  # "I just finished The Quiet Orchard": ask about it (see _learn)
                continue
            if u.act == "intent":
                r = self._intent(st, u, content, parts)
                if r is not None and main is None:
                    main = r
            elif u.act == "statement":
                exp = experience(u.norm)
                if is_discourse(u.norm):
                    parts.append(_Part("main", self._discourse(st, u)))
                    main = main or Reply(msg, "smalltalk", "", via="smalltalk")
                elif exp is not None:
                    parts.append(_Part("prefix", self.everyday.moment(st, exp, u.text)))
                    if self._has_fact(u.text):
                        quiet.append(u)
                    main = main or Reply(msg, "empathy", "", via="empathy")
                elif _PLAN.search(u.norm):
                    parts.append(_Part("main", self._plan(st, u)))
                    main = main or Reply(msg, "smalltalk", "", via="smalltalk")
                elif self._worth_learning(u.text):
                    learn.append(u)
                else:
                    self._chitchat(st, u, parts, alone=len(units) == 1)
            elif u.act == "feeling":
                exp = experience(u.norm)
                if exp is not None and exp.topic and u.data.get("category") in _GENERAL_MOODS and \
                        not u.data.get("negated"):
                    # "my boss was so annoying": name the boss, not just the mood
                    parts.append(_Part("prefix", self.everyday.moment(st, exp, u.text)))
                else:
                    parts.append(_Part("prefix", self._feeling(st, u)))
                st.last_exp = {"valence": u.data.get("valence"), "topic": exp.topic if exp else None,
                               "person": bool(exp and exp.person), "text": u.text, "turn": st.turn}
                if self._has_fact(u.text):
                    quiet.append(u)                 # a sad message gets no "I'll remember that"
                main = main or Reply(msg, "empathy", "", via="empathy")
            elif u.act == "remember":
                learn.append(Unit("statement", u.data["text"], normalise(u.data["text"])))
            else:
                r = self._content(st, u)
                parts.append(_Part("main", r.text))
                if main is None or main.kind in ("smalltalk", "empathy"):
                    main = r
        if learn:
            r = self._learn(st, [u.text for u in learn], msg)
            parts.append(_Part("learn", r.text))
            if main is None or main.kind in ("smalltalk", "empathy"):
                main = r
        if quiet and not learn:
            self._learn(st, [u.text for u in quiet], msg)
        if main is None:
            main = Reply(msg, "smalltalk", "", via="smalltalk")
        text = _compose(parts)
        follow = self._follow(st, units, text, main)
        if follow:
            if text.rstrip().endswith("?"):
                # one question per reply: the follow-up replaces the bank reply's closing question
                cut = re.split(r"(?<=[.!])\s+(?=[^.!?]*\?$)", text.strip())
                text = cut[0] if len(cut) > 1 else ""
                if self._follow_key:
                    follow = self.bank.fun["questions"][self._follow_key].get("text_end", follow)
            text = f"{text} {follow}".strip()
        if not text:
            text = self._reply(st, "fallback")
        main.text = text
        return main

    # -- intents ------------------------------------------------------------------------------

    def _is_content_intent(self, iid: str) -> bool:
        it = self.bank.by_id.get(iid)
        return bool(it and (it.action or iid not in _SHORT and iid not in _DROP_WITH_CONTENT))

    def _intent(self, st: DialogState, u: Unit, content: bool, parts: list[_Part]) -> Reply | None:
        it = self.bank.by_id[u.intent]
        name = self.user_name()
        le = st.last_exp or {}
        if it.id == "thanks" and le.get("valence") == "positive" and st.turn - le.get("turn", -99) <= 2 and \
                re.search(r"\b(?:promot|passed|got the job|got in|won|graduat|accepted|finished|nailed|hired|raise|award)", le.get("text") or "", re.I):
            # "thanks!" after "congratulations!": not "you're welcome"
            text = self._pick(st, "daily:thanks_praise", self.bank.daily["thanks_praise"])
            parts.append(_Part("main", text))
            return Reply(u.text, "smalltalk", text, via="smalltalk")
        others = content and not self._is_content_intent(it.id)
        if others:
            if it.id in _DROP_WITH_CONTENT:
                return None
            short = (_SHORT_NAMED.get(it.id) if name else None) or _SHORT.get(it.id)
            if short:
                parts.append(_Part("prefix", self._pick(st, f"short:{it.id}", short, name=name or "")))
            return None
        if it.action:
            r = self._action(st, it.action, u)
            if r is not None:
                parts.append(_Part("main", r.text))
                return r
        options = it.responses_named if (name and it.responses_named) else it.responses
        if it.responses_named and name:
            options = it.responses_named + [o for o in it.responses if o not in it.responses_named][:1]
        text = self._pick(st, f"intent:{it.id}", options, name=name or "", x=u.groups.get("x", ""))
        parts.append(_Part("main", text))
        if it.follow:
            st.asked.append(f"follow:{it.id}")
        return Reply(u.text, "smalltalk", text, via="smalltalk")

    def _action(self, st: DialogState, action: str, u: Unit) -> Reply | None:
        fun = self.bank.fun
        seed = f"{st.conversation}|{st.turn}"
        if action in ("joke", "fun_fact", "quote", "story"):
            st.last_action = {"kind": action, "turn": st.turn}
        if action == "joke":
            n = st.uses.get("joke", 0)
            st.uses["joke"] = n + 1
            jokes = fun["jokes"]
            order = _order(len(jokes), st.conversation + "|jokes")
            text = _join(self._pick(st, "joke_intro", self.bank.reply("joke_intro")), jokes[order[n % len(jokes)]])
            return Reply(u.text, "smalltalk", text, via="smalltalk")
        if action == "fun_fact":
            n = st.uses.get("fact", 0)
            st.uses["fact"] = n + 1
            facts = fun["facts"]
            f = facts[_order(len(facts), st.conversation + "|facts")[n % len(facts)]]
            text = _join(self._pick(st, "fact_intro", self.bank.reply("fact_intro")), f["text"])
            src = {"kind": "base", "source": "wiki", "key": f["src"]}
            st.last_fact = {"evidence": f["text"], "source": src, "answer": None, "question": None, "sure": True}
            return Reply(u.text, "about", text, source=src, evidence=f["text"], via="facts-bank")
        if action == "quote":
            n = st.uses.get("quote", 0)
            st.uses["quote"] = n + 1
            q = fun["quotes"][_order(len(fun["quotes"]), st.conversation + "|quotes")[n % len(fun["quotes"])]]
            text = _join(self._pick(st, "quote_intro", self.bank.reply("quote_intro")), f"“{q['text']}” — {q['by']}")
            return Reply(u.text, "smalltalk", text, via="smalltalk")
        if action == "story":
            n = st.uses.get("story", 0)
            st.uses["story"] = n + 1
            stories = fun["stories"]
            return Reply(u.text, "smalltalk", stories[_order(len(stories), st.conversation + "|stories")[n % len(stories)]],
                         via="smalltalk")
        if action == "coin":
            return Reply(u.text, "smalltalk", self.bank.reply("coin")[_rand(seed, 2)], via="smalltalk")
        if action == "dice":
            return Reply(u.text, "smalltalk", _fill(self.bank.reply("dice")[0], x=str(1 + _rand(seed, 6))),
                         via="smalltalk")
        if action == "pick_number":
            a, b = int(u.groups.get("a", 1)), int(u.groups.get("b", 10))
            lo, hi = min(a, b), max(a, b)
            x = lo + _rand(seed, hi - lo + 1) if hi - lo < 10**9 else lo
            return Reply(u.text, "smalltalk", self._reply(st, "pick_number", x=str(x)), via="smalltalk")
        if action == "rps":
            choice = u.groups.get("x")
            if not choice:
                st.rps = True
                return Reply(u.text, "smalltalk", self.bank.replies["rps"]["ask"], via="smalltalk")
            return self._rps(st, u.text, choice)
        if action == "memory_query":
            return self._memory_list(st, u.text)
        if action == "who_am_i":
            name = self.user_name()
            if name:
                n = len([s for s in self.bot.user_texts() if s.startswith(CHAT_PREFIX)])
                more = ("Ask “What do you know about me?” to see everything you've told me."
                        if n > 1 else "That's all you've told me so far.")
                return Reply(u.text, "answer", self._reply(st, "who_am_i.known", name=name, more=more), answer=name,
                             via="facts")
            st.pending = {"slot": "name", "store": self.bank.fun["questions"]["ask_name"]["store"], "turn": st.turn}
            return Reply(u.text, "unknown", self._reply(st, "who_am_i.unknown"), via="facts")
        if action == "repeat":
            if not st.last_reply:
                return Reply(u.text, "smalltalk", self._reply(st, "repeat_none"), via="smalltalk")
            base = re.sub(r"^(?:Sure — |I said: )", "", st.last_reply)
            lead = self._pick(st, "repeat_lead", ["Sure — ", "I said: "])
            return Reply(u.text, "smalltalk", lead + base, via="smalltalk")
        if action == "clarify":
            if st.last_reply and st.last_kind in ("answer", "about", "tool", "memory") and \
                    not st.last_reply.startswith(("Sorry if that was unclear", "In other words")):
                return Reply(u.text, "smalltalk", self._reply(st, "clarify.last", last=st.last_reply), via="clarify")
            return Reply(u.text, "smalltalk", self._pick(st, "daily:disc:confused",
                                                         self.bank.daily["discourse"]["confused"]), via="clarify")
        if action == "correction":
            if st.last_fact and st.last_fact.get("question"):
                st.pending = {"slot": "correction", "question": st.last_fact["question"], "turn": st.turn}
            return None                           # the intent's own responses
        if action == "why_last":
            return self._why(st, u.text)
        if action == "more":
            return self._more(st, u.text)
        if action == "ask_user":
            return self._ask_user(st, u)
        return None

    def _rps(self, st: DialogState, text: str, choice: str) -> Reply:
        bot_choice = ["rock", "paper", "scissors"][_rand(f"{st.conversation}|{st.turn}|rps", 3)]
        wins = {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
        rr = self.bank.replies["rps"]
        key = "draw" if bot_choice == choice else ("win" if (choice, bot_choice) in wins else "lose")
        return Reply(text, "smalltalk", _fill(rr[key], bot=bot_choice), via="smalltalk")

    def _ask_user(self, st: DialogState, u: Unit) -> Reply:
        qs = self.bank.fun["questions"]
        known = self._known_categories()
        for key in self.bank.fun["ask_order"]:
            if key in st.asked or key == "ask_mood":
                continue
            cat = {v: k for k, v in _ASK_FOR_CATEGORY.items()}.get(key)
            if cat and cat in known:
                continue
            st.asked.append(key)
            st.pending = {"slot": qs[key]["slot"], "store": qs[key]["store"], "turn": st.turn}
            intro = self._pick(st, "intent:topic_suggest", self.bank.by_id["topic_suggest"].responses)
            return Reply(u.text, "smalltalk", f"{intro} {qs[key]['text']}", via="smalltalk")
        return Reply(u.text, "smalltalk", "I've asked you a lot already! How about you ask me something — anything "
                                          "from history to science?", via="smalltalk")

    def _known_categories(self) -> set:
        self.bot.refresh()
        return {lab for f in self.bot.facts.facts if f.subject == USER for lab in f.relation if lab.startswith("#")}

    # -- content ------------------------------------------------------------------------------

    # -- writing ------------------------------------------------------------------------------

    def _today(self):
        return self.clock().date() if self.clock else dt.date.today()

    def _writing(self, st: DialogState, u: Unit) -> Reply:
        from engramm.chat import writing as w
        task = u.data["task"]
        spec = self.bank.writing
        text = u.text
        if task == "draft":
            req = w.parse_request(text, spec["purposes"])
            if req is None:
                return Reply(text, "smalltalk", self._reply(st, "fallback"), via="writing")
            return self._show_draft(st, text, req, intro=True)
        if task == "poem":
            m = w._POEM.match(re.sub(r"^(?:hey|hi|ok|okay|so)[,!]?\s+", "", text.strip(), flags=re.I).rstrip("?.!"))
            topic = (m.group("topic") if m else None) or "the day"
            n = st.uses.get("poem", 0)
            st.uses["poem"] = n + 1
            body = w.poem(topic, spec, f"{st.conversation}|poem|{n}")
            return Reply(text, "writing", f"Here's a short poem about {topic.strip(' ?.!')}:\n\n{body}", via="writing")
        if task == "story":
            m = w._STORY.match(text.strip().rstrip("?.!"))
            topic = m.group("topic") if m else "a curious robot"
            n = st.uses.get("story", 0)
            st.uses["story"] = n + 1
            stories = self.bank.fun["stories"]
            base = stories[_order(len(stories), st.conversation + "|stories")[n % len(stories)]]
            about = self.about.find(topic)
            intro = f"Here's a little story — and since you mentioned {topic}: " if about else "Here's a little story:"
            fact = f"\n\n(By the way: {about.sentences[0]})" if about else ""
            return Reply(text, "writing", f"{intro}\n\n{base}{fact}", via="writing",
                         source=about.source if about else None)
        if task == "summary":
            m = w._SUMMARY.match(re.sub(r"^(?:hey|hi|ok|okay|so)[,!]?\s+", "", text.strip(), flags=re.I))
            body = (m.group("text") if m else "").strip()
            if len(body.split()) <= 8:
                topic = re.sub(r"^(?:the (?:article|text|page) (?:about|on)\s+)", "", body, flags=re.I).strip(" ?.!")
                found = self.about.find(topic) if topic else None
                if not found:
                    return Reply(text, "smalltalk", "Paste the text you'd like me to summarise after “Summarize:” — "
                                                    "or name a topic, like “Summarize the article about volcanoes”.",
                                 via="writing")
                long = self.about.find(topic, n=30)
                sents = w.summarize(" ".join(long.sentences), max_sentences=3)
                out = "Here's a short summary of “" + found.title + "”:\n\n" + " ".join(sents)
                return Reply(text, "writing", out, source=found.source, evidence=found.sentences[0], via="writing")
            sents = w.summarize(body)
            return Reply(text, "writing", "Here's a summary:\n\n" + " ".join(sents), via="writing")
        if task == "rephrase":
            m = w._REPHRASE.match(text.strip())
            if not m:
                return Reply(text, "smalltalk", self._reply(st, "fallback"), via="writing")
            tone = (m.group("tone") or m.group("tone2") or "").lower()
            verb = (m.group("verb") or "").lower()
            if not tone:
                tone = "fix" if verb.startswith(("fix", "correct", "proofread")) else "formal" \
                    if verb in ("polish", "improve") else "plain"
            out = w.fix_text(m.group("text")) if tone in ("fix", "plain") else w.rephrase(m.group("text"), tone)
            label = {"fix": "Here's the corrected text:", "plain": "Here's a cleaned-up version:"}.get(
                tone, f"Here's a {'more ' if tone not in ('simpler', 'shorter') else ''}{tone} version:")
            return Reply(text, "writing", f"{label}\n\n{out}", via="writing")
        return Reply(text, "smalltalk", self._reply(st, "fallback"), via="writing")

    def _show_draft(self, st: DialogState, text: str, req, intro: bool = False, note: str = "") -> Reply:
        from engramm.chat import writing as w
        body = w.draft(req, self.bank.writing, self.user_name(), self._today(), st.conversation)
        st.last_draft = req.to_dict()
        st.draft_turn = st.turn
        what = {"email": "an email", "letter": "a letter", "message": "a message", "note": "a note"}.get(req.genre,
                                                                                                        "a draft")
        head = note or (f"Here's {what} you can use:" if intro else "Here's the updated version:")
        tail = ("\n\nWant changes? Say “make it shorter”, “more formal”, “add that …” or “sign it with …”."
                if intro else "")
        return Reply(text, "writing", f"{head}\n\n{body}{tail}", via="writing")

    def _edit_draft(self, st: DialogState, text: str, cmd: str, x: str | None) -> Reply:
        from engramm.chat.writing import WritingRequest, apply_edit
        req = apply_edit(WritingRequest.from_dict(st.last_draft), cmd, x)
        notes = {"shorter": "Here's a shorter version:", "longer": "Here's a more detailed version:",
                 "formal": "Here's a more formal version:", "casual": "Here's a more casual version:",
                 "again": "Here's another version:", "add": "Done — I've added that:",
                 "sign": "Signed:", "date": "I've changed the date:", "to": "Addressed to the new recipient:",
                 "nosubject": "Without the subject line:"}
        note = notes.get(cmd, "")
        if cmd == "formal" and req.polite and re.search(r"\bpolite|nicer|kinder\b", text, re.I):
            note = "Here's a more polite version:"
        elif cmd == "formal" and req.polite:
            note = "It was already formal — here's an even more courteous version:"
        return self._show_draft(st, text, req, note=note)

    def _content(self, st: DialogState, u: Unit) -> Reply:
        if u.act == "writing":
            return self._writing(st, u)
        if u.act == "forget":
            r = self.bot._forget(u.text)
            if r.kind == "forgot":
                st.last_fact = None
            return r
        if u.act == "tool":
            tr = u.data["result"]
            if tr.value is not None:
                st.uses["last_calc"] = [st.turn, str(tr.value)]
            pm = re.match(r"\s*\d+(?:[.,]\d+)?\s?% of (\d[\d,]*(?:\.\d+)?)", tr.text)
            if pm:
                st.uses["last_pct"] = [st.turn, pm.group(1)]         # "and 20%?" next
            return Reply(u.text, "tool", tr.text if tr.text.endswith((".", "!", "?")) else tr.text + ".",
                         answer=tr.value, via="tool", confidence=1.0)
        if u.act == "about":
            return self._about(st, u)
        if u.act == "question":
            two = _TWO_QUESTIONS.match(u.text.strip())
            if two and len(two.group("a").split()) >= 3:
                # "what is the capital of France and how many people live there?": both, in order; the
                # second sees the first answer ("there" = Paris)
                first = self._question(st, two.group("a").rstrip(" ,") + "?")
                if first.kind == "answer":
                    st.uses.pop("person_gap", None)       # the first answer is the referent now
                    second = self._question(st, two.group("b"))
                    if second.kind == "answer":
                        first.text = f"{first.text} {second.text}"
                    return first
                return first                               # unknown first: no "who's he?" about the second
            return self._question(st, u.text)
        return Reply(u.text, "nothing", self._reply(st, "fallback"))

    def _question(self, st: DialogState, text: str) -> Reply:
        bot = self.bot
        # "what language do they speak in Brazil?": a generic "they", not the last person or thing
        text = re.sub(r"(?i)\b(do|did|does) they (speak|use|eat|celebrate|drive|call|pay|play)\b(?=.*\bin\b)", r"\1 people \2", text)
        pct = _PCT_MORE.match(text.strip().lower())
        lp = st.uses.get("last_pct")
        if pct and lp and st.turn - lp[0] <= 3:          # "15% of 80" … "and 20%?"
            tr = tool_answer(f"{pct.group(1)}% of {lp[1]}", self._now())
            if tr is not None:
                st.uses["last_pct"] = [st.turn, lp[1]]
                return Reply(text, "tool", tr.text if tr.text.endswith(".") else tr.text + ".", answer=tr.value,
                             via="tool", confidence=1.0)
        if _VAGUE_JUDGE.match(normalise(text)) and st.last_message:
            # "is that too much?" about what was just said: never a lookup of the words "too much"
            prev = normalise(st.last_message)
            d_ = self.bank.daily
            key = next((k for rx, k in _NORMS if rx.search(prev)), None)
            if key:
                return Reply(text, "smalltalk", self._pick(st, f"daily:norm:{key}", d_["norms"][key]), via="smalltalk")
            return Reply(text, "smalltalk", self._pick(st, "daily:judge_plain", d_["judge_plain"]), via="smalltalk")
        pron = re.search(r"\b(he|she|him|his|her|hers|they|them|their)\b", text, re.I)
        gap = st.uses.get("person_gap") == st.turn - 1          # the last "who …?" found nobody
        if re.search(r"\b(?:it|its)\b", text, re.I) and not pron and st.last_kind == "unknown" and \
                bot.resolve(text) == text and not bot.context.get("answer") and \
                not re.search(r"\b(?:i|me|my|you|your)\b", text, re.I):
            # "how tall is it?" right after a question ENGRAMM could not answer: "it" points nowhere
            st.pending = {"slot": "who_mean", "question": text, "pron": "it", "turn": st.turn}
            return Reply(text, "unknown", self._pick(st, "daily:it_mean", self.bank.daily["it_mean"]), via="clarify")
        if pron and not re.search(r"\b(?:i|me|my|you|your)\b", text, re.I) and (bot.resolve(text) == text or gap):
            st.pending = {"slot": "who_mean", "question": text, "pron": pron.group(1), "turn": st.turn}
            return Reply(text, "unknown", self._pick(st, "daily:who_mean", self.bank.daily["who_mean"],
                                                     x=pron.group(1).lower()), via="clarify")
        el = _HOW_ADJ.fullmatch(normalise(text).strip(" ?"))
        ment = self.bot.context.get("mention")
        if el and ment:                                 # "how tall?" right after Mount Everest
            text = f"how {el.group(1)} is {ment}?"
        food = _EAT_THERE.match(normalise(text))
        pt = st.uses.get("place_topic")
        place = (food.group("p") if food and food.group("p") else (pt[0] if pt and st.turn - pt[1] <= 8 else None)) if food else None
        if place:                                       # "what should I eat there?" during a trip to Japan
            rep = self._cuisine(st, text, place)
            if rep is not None:
                return rep
        text = self._place_carry(st, text)
        text = self._carry_topic(st, text)
        atlas_on = self.atlas is not None and self.atlas.any_on() and not re.search(r"\b(?:i|me|my|mine)\b", text, re.I)
        if atlas_on:
            from engramm.web.atlas import is_fresh
            if is_fresh(text):
                fresh = self._atlas_answer(st, text)       # "who is the current …": newer sources first
                if fresh is not None:
                    return self._with_offline_view(st, text, fresh)
        likes = self._likes_answer(st, text)
        if likes is not None:
            return likes
        how = self._howto(st, text)
        if how is not None:
            return how
        if _DISTANCE_Q.match(normalise(text)):
            return Reply(text, "unknown", self._pick(st, "daily:distance_none", self.bank.daily["distance_none"]),
                         via="clarify")
        common = self._common_fact(st, text)
        if common is not None:
            return common
        sup = self._superlative(st, text)
        if sup is not None:
            return sup
        kb = self._kb_answer(st, text)
        if kb is not None:
            return kb
        mq = self._measure_quote(st, text)
        if mq is not None:
            return mq
        ev = self._event_answer(st, text)
        if ev is not None:
            return ev
        rep = bot._answer(" ".join(text.split()))
        topic = self._named_topic(rep.resolved or text)
        if topic:
            st.uses["q_topic"] = [topic, st.turn]
        if rep.kind == "answer" and rep.via == "lookup" and _implausible(rep.resolved or text, rep.answer, rep.evidence,
                                                                          _src_title(rep.source), self._before(rep)):
            rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None
            self.bot.context.update({"answer": None, "atype": None})   # a rejected answer is no "it" later
        if rep.kind == "answer" and rep.via == "lookup" and self._wrong_kind(rep.resolved or text, rep.answer):
            rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None
        qq = (rep.resolved or text).strip()
        if rep.kind == "answer" and rep.via == "lookup" and _NEEDS_NUMBER.search(qq) and \
                not re.search(r"\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|"
                              r"forty|fifty|hundred|thousand|million|billion|dozen|half)\b", str(rep.answer), re.I):
            rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None   # "the boiling point of water" → "grease"
        if rep.kind == "answer" and rep.via == "lookup" and _YES_NO_Q.match(qq):
            # "is a tomato a fruit?" has no short answer to cut out ("Sweet"): show the sentence instead
            ev = (rep.evidence or "").strip()
            content = [w for w in re.findall(r"[a-z]+", qq.lower()) if len(w) > 3 and w not in _STOP_CHAT]
            if ev and content and all(re.search(rf"\b{re.escape(w[:5])}", ev.lower()) for w in content):
                rep.text = self._pick(st, "daily:yes_no_quote", self.bank.daily["yes_no_quote"], x=ev)
                rep.kind, rep.guess, rep.answer = "about", rep.answer, None   # a quote, not a short answer
                return rep
            else:
                rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None
        if rep.kind == "answer" and rep.via == "lookup" and _WINNER_Q.match(rep.resolved or text) and not any(
                rep.answer.lower() in next(g for g in m.groups() if g).lower()
                for m in _WINNER_RX.finditer(rep.evidence or "")):
            rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None   # "Rajasthan Royals" for the Champions League
        if topic and _WINNER_Q.match(rep.resolved or text):
            docs = self.about.titles.lookup(topic)
            if docs:
                lo, hi = self.bot.c.doc_sentences(docs[0])
                src0 = {"kind": "wikipedia", "title": topic, "key": topic,
                        "url": "https://en.wikipedia.org/wiki/" + topic.replace(" ", "_")}
                yrs = re.findall(r"\b(?:1[5-9]|20)\d\d\b", rep.resolved or text)
                win = None if (yrs and not any(y in topic for y in yrs)) else \
                    _winner_from([(self.bot.c.sentence_text(i), src0) for i in range(lo, hi)], topic)
                if win is not None:
                    rep.kind, rep.answer, rep.guess, rep.evidence, rep.source = "answer", win[0], win[0], win[1], win[2]
                    rep.via, rep.confidence = "lookup", 1.0
                elif rep.kind == "answer" and rep.source and rep.source.get("title") != topic:
                    rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None
        gap = self._topic_gap(st, topic, rep)
        if gap is not None and atlas_on:
            later = self._atlas_answer(st, text)
            if later is not None:
                return later
        if gap is not None:
            return gap
        if atlas_on and rep.kind != "answer":
            later = self._atlas_answer(st, text)
            if later is not None:
                return later
        q = rep.resolved or text
        dim_m = _MEASURE_TOPIC.match(q)
        need = _DIM_UNIT.get(dim_m.group("dim").split()[0].lower(), _UNIT) if dim_m else _UNIT
        if rep.kind == "answer" and rep.answer and _MEASURE_Q.match(q) and not need.search(rep.answer):
            # "how far is the moon?" → "8": a measure without its unit is no answer
            rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None
            rep.text = "I don't know for sure."
        if rep.kind == "answer" and rep.via in ("facts", "memory") and rep.source and rep.source.get("kind") == "user":
            orig = self._fact_for(rep)
            cat = _asked_category(q) if orig is not None and orig.subject == USER else None
            latest = self._latest_fact(cat) if cat else None
            if latest is not None and latest.object != rep.answer and latest.subject == USER:
                rep.answer, rep.guess, rep.evidence = latest.object, latest.object, latest.sentence
                rep.source = {"kind": "user", "source": latest.source}
            fact = self._fact_for(rep)
            if fact is not None:
                rep.text = personal_sentence(fact.subject, fact.relation, rep.answer, rep.evidence)
            else:
                rep.text = _user_answer_text(rep.answer, rep.evidence)
            st.last_fact = {"evidence": rep.evidence, "source": rep.source, "answer": rep.answer, "question": q,
                            "sure": True}
            return rep
        if rep.kind == "answer":
            sent = answer_sentence(q, rep.answer, _atype(q))
            rep.text = sent or self._reply(st, "answer.fallback", x=rep.answer)
            st.last_fact = {"evidence": rep.evidence, "source": rep.source, "answer": rep.answer, "question": q,
                            "sure": True}
            return rep
        # unknown
        if rep.via == "facts" and rep.text.startswith("I don't know — you haven't told me"):
            cat = _asked_category(q)
            latest = self._latest_fact(cat) if cat else None
            if latest is not None:
                # told twice ("The name's Tamlolo." … "My name is Erik!"): the latest statement counts
                rep.kind, rep.answer, rep.guess = "answer", latest.object, latest.object
                rep.evidence, rep.source, rep.confidence = latest.sentence, {"kind": "user", "source": latest.source}, 1.0
                rep.text = personal_sentence(latest.subject, latest.relation, latest.object, latest.sentence)
                st.last_fact = {"evidence": rep.evidence, "source": rep.source, "answer": rep.answer, "question": q,
                                "sure": True}
                self.bot.context.update({"answer": latest.object, "atype": None})
                return rep
            if cat == "#name":
                rep.text = self._reply(st, "unknown_about_you.name")
                st.pending = {"slot": "name", "store": self.bank.fun["questions"]["ask_name"]["store"], "turn": st.turn}
            else:
                rep.text = self._reply(st, "unknown_about_you.other")
                key = _ASK_FOR_CATEGORY.get(cat)
                if key:
                    st.pending = {"slot": self.bank.fun["questions"][key]["slot"],
                                  "store": self.bank.fun["questions"][key]["store"], "turn": st.turn}
            st.last_fact = None
            return rep
        if rep.text.startswith("I don't know — I have not read anything about"):
            missing = rep.text.split("about", 1)[1].strip(" .")
            role = re.match(r"^\s*who(?:'s| is| was)\s+(?:the\s+)?(.+?)\s*\??$", q, re.I)
            if role and " of " in missing:
                # "who is the CEO of Apple?": not a missing name, a fact I don't have
                rep.text = f"I don't know who the {_acronym_case(role.group(1))} is — I haven't read anything that says."
            else:
                rep.text = self._reply(st, "answer.unknown_named", x=missing)
        elif _HOWTO_Q.match(normalise(q)) and "howto_none" in self.bank.daily:
            # "how do you stay awake on night shift?" without a guide: no unrelated article title
            rep.text = self._pick(st, "daily:howto_none", self.bank.daily["howto_none"])
        elif rep.guess and (rep.source or {}).get("key") and _title_fits(q, rep.source["key"]):
            # unsure guesses were right only 7 of 25 times on the team prompts: say so and name the
            # closest source instead of offering the guess (the guess stays in the reply for evals)
            rep.text = self._reply(st, "answer.unknown_near", x=rep.source["key"])
        else:
            rep.text = self._reply(st, "answer.unknown")
        st.last_fact = ({"evidence": rep.evidence, "source": rep.source, "answer": rep.guess, "question": q,
                         "sure": False} if rep.evidence else None)
        if re.match(r"^\s*who\b", q, re.I):
            st.uses["person_gap"] = st.turn                    # "how old is he?" next: ask who is meant
        self.bot.context.update({"answer": None, "atype": None})   # a guess not shown is no referent
        return rep

    def _life(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Everyday life as a person tells it: a workout done and how it went, a day that was "ok",
        a goal ("I want to get fitter") and "any tips?" after it, a diet ("I'm vegetarian"), and
        what to eat after a workout."""
        d = self.bank.daily
        la = st.last_action or {}
        recent = st.turn - la.get("turn", -99) <= 2
        le = st.last_exp or {}
        grief = le and st.turn - le.get("turn", -99) <= 4 and _LOSS.search(le.get("text") or "")
        if grief:
            m = _GRIEF_NAME.match(norm)
            if m:
                name = m.group("x").strip()
                name = name[:1].upper() + name[1:]
                return Reply(msg, "smalltalk", self._pick(st, "daily:grief_name", d["grief_name"], x=name,
                                                          pron=_PRON.get(m.group("p"), "they")), via="empathy")
            m = _GRIEF_AGE.match(norm)
            if m:
                return Reply(msg, "smalltalk", self._pick(st, "daily:grief_age", d["grief_age"], x=m.group("n")),
                             via="empathy")
        if _WHAT_WAS_I.match(norm) and le and st.turn - le.get("turn", -99) <= 30 and le.get("text"):
            told = le["text"].strip().rstrip(".!")
            told = re.sub(r"\b(?:I'm|I am|im)\b", "you were", told, flags=re.I)
            told = re.sub(r"\bmy\b", "your", re.sub(r"\bme\b", "you", re.sub(r"\bI\b", "you", told, flags=re.I),
                                                    flags=re.I), flags=re.I)
            return Reply(msg, "smalltalk", self._pick(st, "daily:what_was_i", d["what_was_i"], x=told), via="smalltalk")
        if _WEDDING.search(norm):
            st.uses["wedding"] = st.turn
        if _HONOUR.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:wedding_role", d["wedding_role"]), via="empathy")
        if le and st.turn - le.get("turn", -99) <= 2 and _FOLLOW_STATEMENT.match(norm) and experience(norm) is None and \
                not _FEELING_WORD.search(norm) and "?" not in msg and len(norm.split()) <= 10 and \
                not set(r for f in facts_from_text(msg, "x") for r in f.relation) & _CATEGORY_LABELS:
            key = "exp_follow_neg" if le.get("valence") == "negative" else "exp_follow_pos"
            if _SPEECH.search(norm):
                st.uses["speech"] = st.turn
                key = "speech_mention"
            st.last_exp = dict(le, turn=st.turn)
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="empathy")
        if _SPEECH.search(norm) and re.match(r"^i (?:have|need|got|am going|'m going|was asked) to\b", norm):
            st.uses["speech"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "daily:speech_mention", d["speech_mention"]), via="empathy")
        sp = st.uses.get("speech")
        if (_HELP_ME.match(norm) and sp is not None and st.turn - sp <= 3) or _SPEECH_HELP.match(norm):
            st.uses.pop("speech", None)
            wd = st.uses.get("wedding")
            wedding = bool(_WEDDING.search(norm)) or (wd is not None and st.turn - wd <= 8)
            key = "speech_wedding" if wedding else "speech_generic"
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="everyday")
        m = _JOB_CHANGE.match(norm)
        if m:
            jobs = [f for f in self.bot.facts.facts if f.subject == USER and "#job" in f.relation]
            for f in jobs:                              # the old job is no longer true
                self.bot.memory.forget(f.source)
            if jobs:
                self.bot.refresh()
            key = "job_lost" if m.group("bad") else "job_quit"
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="empathy")
        if _WORKOUT_DONE.match(norm):
            rep = self._learn(st, [msg], msg)
            rep.text = self._pick(st, "daily:workout_done", d["workout_done"])
            st.last_action = {"kind": "workout", "turn": st.turn}
            return rep
        m = _WHICH_ONE.match(norm)
        vals = [v for v in st.uses.get("kb_vals", []) if st.turn - v[0] <= 4]
        if m and len(vals) >= 2 and vals[-1][1] != vals[-2][1]:
            a, b = vals[-2][1], vals[-1][1]
            ask = f"which is {m.group('w')}, {a} or {b}"
            rep = self.everyday.compare(st, ask, ask.lower())
            if rep is not None and rep.kind != "unknown":
                rep.message = msg
                return rep
        lc = st.uses.get("last_calc")
        m = _CALC_MORE.match(norm)
        if m and lc and st.turn - lc[0] <= 3:
            from engramm.chat.tools import calculate
            sym = _CALC_OPS[m.group("op")]
            n = m.group("n").replace(",", ".")
            res = calculate(f"{lc[1]} {sym} {n}")
            if res is not None and res.value is not None:
                st.uses["last_calc"] = [st.turn, str(res.value)]
                shown = {"*": "×", "/": "÷", "^": "^"}.get(sym, sym)
                return Reply(msg, "tool", f"{lc[1]} {shown} {n} = {res.value}.", answer=res.value, via="tool",
                             confidence=1.0)
        if _HOMEWORK.match(norm):
            st.uses["homework"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "daily:homework", d["homework"]), via="smalltalk")
        hw = st.uses.get("homework")
        m = _SUBJECT.match(norm)
        if m and hw is not None and st.turn - hw <= 2:
            subj = m.group("s")
            key = next((k for k, rx in _SUBJECT_KINDS if rx.fullmatch(subj)), "other")
            st.uses.pop("homework", None)
            return Reply(msg, "smalltalk", self._pick(st, f"daily:subject:{key}", d["subject"][key],
                                                      x=subj[:1].upper() + subj[1:]), via="smalltalk")
        m = _TRIP.match(norm)
        if m and not _NOT_A_TRIP.fullmatch(m.group("x").strip()):
            place = m.group("x").strip()
            rep = self._learn(st, [msg], msg)
            if _TRIP_WORD.fullmatch(place):
                rep.text = self._pick(st, "daily:trip_back", d["trip_back"])
                st.last_action = {"kind": "trip", "turn": st.turn}
            else:
                shown = _place_case(place)
                rep.text = self._pick(st, "daily:trip_place", d["trip_place"], x=shown)
                st.last_action = {"kind": "trip", "turn": st.turn, "place": shown}
                st.topic = {"name": shown, "title": shown, "turn": st.turn}
            return rep
        m = _HOBBY.match(norm) or _HOBBY_BARE.match(norm)
        if m:
            verb = m.group("v")
            x = (m.groupdict().get("x") or _GERUND.get(verb, verb)).strip()
            rep = self._learn(st, [msg], msg)
            key = "hobby_play" if verb == "play" else "hobby_do"
            rep.text = self._pick(st, f"daily:{key}", d[key], x=x)
            st.uses["asked_duration"] = [st.turn, x]
            st.last_action = {"kind": "hobby", "turn": st.turn, "x": x}
            return rep
        asked = st.uses.get("asked_duration")
        m = _DURATION_ANS.match(norm)
        if m and asked and st.turn - asked[0] <= 1:
            n, unit = m.group("n"), m.group("u")
            shown = f"{n} {unit}"
            shown = shown[:1].upper() + shown[1:]
            long_ = unit.startswith("year") and n not in ("a", "one", "1")
            key = "duration_long" if long_ else "duration_short"
            st.uses.pop("asked_duration", None)
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=shown), via="smalltalk")
        if la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3:
            kind = la["kind"][4:]
            if _REC_SEEN.match(norm):
                before = set(st.uses.get(f"rec_seen:{kind}", []))
                rep = self.everyday.recommend(st, msg, kind, la.get("genre"), more=True)
                if not set(st.uses.get(f"rec_seen:{kind}", [])) - before:
                    # every fitting suggestion has been shown: say so instead of going round again
                    return Reply(msg, "smalltalk", self._pick(st, "daily:rec_exhausted", d["rec_exhausted"]),
                                 via="everyday")
                rep.text = self._pick(st, "daily:rec_seen", d["rec_seen"]) + rep.text[len("A few more:"):] \
                    if rep.text.startswith("A few more:") else rep.text
                return rep
            g = _REC_GENRE.match(norm)
            if g and g.group("g") in _GENRES:
                return self.everyday.recommend(st, msg, kind, g.group("g"))
        m = _BEST_OF.match(norm)
        if m:
            name = (st.topic or {}).get("name") if st.topic and st.turn - st.topic.get("turn", -99) <= 4 else None
            liked = st.uses.get("last_like")
            if name is None and liked and st.turn - liked[0] <= 4 and m.group("who") in ("their", "his", "her", "its"):
                name = liked[1]
            if name:
                return Reply(msg, "smalltalk", self._pick(st, "daily:best_of", d["best_of"], x=name), via="smalltalk")
            return Reply(msg, "smalltalk", self._pick(st, "daily:best_of_plain", d["best_of_plain"]), via="smalltalk")
        m = _HOW_IT_WENT.match(norm)
        if m and recent and la.get("kind") == "workout":
            key = "workout_hard" if m.group("hard") else "workout_good" if m.group("good") else "workout_meh"
            st.last_action = {"kind": "workout", "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="empathy")
        if _DAY_MEH.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:day_meh", d["day_meh"]), via="smalltalk")
        m = _GOAL.match(norm)
        if m:
            goal = m.group("goal").strip()
            topic = next((t for t, rx in _GOAL_TOPICS if rx.search(goal)), "other")
            st.uses["goal"] = [topic, st.turn, goal]
            rep = self._learn(st, [msg], msg)
            rep.text = self._pick(st, f"daily:goal:{topic}", d["goal"][topic], x=goal)
            return rep
        goal = st.uses.get("goal")
        if goal and st.turn - goal[1] <= 4 and _TIPS.match(norm):
            tips = d["tips"].get(goal[0])
            if tips:
                body = "\n".join("• " + t for t in tips[:4])
                head = self._pick(st, "daily:tips_head", d["tips_head"], x=goal[2])
                return Reply(msg, "smalltalk", f"{head}\n\n{body}", via="everyday")
        m = _DIET.match(norm)
        if m:
            diet = m.group("diet").lower().replace("gluten-free", "gluten free")
            st.uses["diet"] = diet
            rep = self._learn(st, [msg], msg)
            rep.text = self._pick(st, "daily:diet_noted", d["diet_noted"], x=diet)
            return rep
        ll = getattr(st, "last_list", None) or {}
        nh = _WITHOUT.match(norm)
        if nh and ll.get("kind") == "food" and st.turn - ll.get("turn", -99) <= 3:
            # "I don't have eggs" after cooking ideas: drop what needs them, like a friend would
            x = nh.group("x").strip(" .!")
            stem = re.sub(r"(?:es|s)$", "", x) if len(x) > 3 else x
            texts = ll.get("texts") or []
            needs = [stem] + _NEEDS.get(stem, [])
            hit = [t for t in texts if any(re.search(rf"\b{re.escape(w)}", t, re.I) for w in needs)]
            rest = [t for t in texts if t not in hit]
            if hit and rest:
                def short(t: str) -> str:              # "a simple omelette with cheese and herbs" → "simple omelette"
                    t = re.split(r" —|,| with | on a | if ", t)[0]
                    return re.sub(r"^(?:a|an|the|some)\s+", "", t.strip(), flags=re.I)
                rest_text = " or ".join(short(r) for r in rest)
                return Reply(msg, "smalltalk", self._pick(st, "daily:without_skip", d["without_skip"], x=x,
                                                          dish=short(hit[0]), rest=rest_text[:1].upper() + rest_text[1:]),
                             via="everyday")
            return Reply(msg, "smalltalk", self._pick(st, "daily:without_fine", d["without_fine"], x=x), via="everyday")
        dc = _DECIDED.match(norm)
        if dc and (ll.get("kind") == "food" and st.turn - ll.get("turn", -99) <= 4):
            return Reply(msg, "smalltalk", self._pick(st, "daily:decided_food", d["decided_food"],
                                                      x=dc.group("x").strip()), via="everyday")
        if dc:
            return Reply(msg, "smalltalk", self._pick(st, "daily:decided", d["decided"], x=dc.group("x").strip()),
                         via="everyday")
        mk = _MAYBE_KIND.match(norm)
        if mk:                                            # "maybe reading then" after ideas: books
            kind = _MAYBE_KINDS.get(mk.group("w").replace("a ", "", 1))
            if kind:
                return self.everyday.recommend(st, msg, kind)
        if _MOVED_NEW.search(norm):                       # "I moved to a new city": ask which, then remember it
            st.pending = {"slot": "home", "store": "I live in {x}.", "turn": st.turn}
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "daily:moved_new", d["moved_new"]), via="empathy")
        if re.search(r"\b(?:think|better|prefer|belongs?|or|vs|versus|team|which|favou?rite|should)\b", norm):
            for key, words in _DEBATES:
                if all(re.search(rf"\b{w}", norm) for w in words):
                    st.last_action = {"kind": "debate", "turn": st.turn, "key": key}
                    return Reply(msg, "smalltalk", self._pick(st, f"daily:debate:{key}", d["debates"][key]),
                                 via="smalltalk")
        if norm.strip(" ?!") in ("why", "why not", "how come", "really") and la.get("kind") == "debate" and recent:
            return Reply(msg, "smalltalk", self._pick(st, "daily:debate_why", d["debate_why"]), via="smalltalk")
        tw = _THOUGHT_IT_WAS.match(norm)
        lf = st.last_fact or {}
        if tw and lf.get("sure") and lf.get("answer") and st.last_kind == "answer":
            mine = tw.group("x").strip(" ?.!")
            if mine.lower() != str(lf["answer"]).lower():
                return Reply(msg, "smalltalk", self._pick(st, "daily:thought_it_was", d["thought_it_was"],
                                                          x=_place_case(mine), y=lf["answer"]), via="smalltalk")
        sl = st.uses.get("superlative")
        if sl and st.turn - sl[1] <= 3 and _NEXT_RANK.fullmatch(norm.strip(" ?!.")):
            rep = self._superlative(st, msg)            # "and the second" after "the tallest mountain"
            if rep is not None:
                return rep
        if re.fullmatch(r"(?:please |pls |ok |so )?(?:wish me luck|fingers crossed|cross your fingers(?: for me)?|keep your fingers crossed(?: for me)?)[.!]*", norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:wish_luck", d["wish_luck"]), via="smalltalk")
        wm = _WEAR.match(norm)
        if wm:                                            # "what should I wear?" — for what the chat is about
            about = " ".join(filter(None, [wm.group("x"), normalise(st.last_message or "")]))
            occ = next((k for k, rx in _OCCASIONS if rx.search(about)), "none")
            return Reply(msg, "smalltalk", self._pick(st, f"daily:wear:{occ}", d["wear"][occ]), via="everyday")
        tp = _TRIP_PLAN.search(norm)
        px = ((tp.group("x") or tp.group("y") or "") if tp else "").strip()
        if tp and px not in ("a", "the", "my", "bed", "work", "school", "sleep", "the gym", "the store", "the shop"):
            place = _place_case(px)
            st.uses["place_topic"] = [place, st.turn]
            st.last_action = {"kind": "trip_plan", "turn": st.turn, "place": place}
            rep = self._learn(st, [msg], msg)
            rep.text = self._pick(st, "daily:trip_plan", d["trip_plan"], x=place)
            return rep
        if _TRIP_TIPS.match(norm) and la.get("kind") == "trip_plan" and st.turn - la.get("turn", -99) <= 4:
            tips = "\n".join("• " + t for t in d["trip_tips"]["items"])
            return Reply(msg, "smalltalk", d["trip_tips"]["head"].replace("{x}", la["place"]) + "\n\n" + tips,
                         via="everyday")
        am = _THINGS_TO_DO.match(norm)
        if am:                                            # "something I can do at home" (after "I'm bored")
            g = (am.group("g") or "").strip()
            return self.everyday.recommend(st, msg, "activity", genre="home" if g in ("at home", "inside", "indoors") else None)
        hm = _GOT_HOME.match(norm)
        if hm:
            key = "done_for_day" if re.search(r"\b(?:finished|got off|done with|off)\b", norm) else "got_home"
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=hm.group("x").replace("my ", "your ")),
                         via="everyday")
        if _POST_WORKOUT.match(norm):
            diet = st.uses.get("diet") or self._told_diet()
            items = d["post_workout"]["vegan" if diet == "vegan" else "vegetarian" if diet else "any"]
            head = self._pick(st, "daily:post_workout_head", d["post_workout"]["head"])
            if diet:
                head = head.rstrip(":") + f" (all {diet}):"
            st.last_action = {"kind": "rec:food", "turn": st.turn}
            return Reply(msg, "smalltalk", head + "\n\n" + "\n".join("• " + i for i in items[:4]), via="everyday")
        return None

    def _told_diet(self) -> str | None:
        """A diet told in an earlier conversation ("I'm vegetarian")."""
        for f in reversed(self.bot.facts.facts):
            if f.subject == USER:
                m = re.search(r"\b(vegan|vegetarian|pescatarian)\b", f.sentence or "", re.I)
                if m:
                    return m.group(1).lower()
        return None

    def _howto(self, st: DialogState, text: str) -> Reply | None:
        """"How do I boil an egg?": a short practical guide when one fits; for an everyday "how do I …"
        without one an honest answer — never "you haven't told me that"."""
        q = normalise(text)
        m = _HOWTO_Q.match(q)
        if not m:
            return None
        words = set(re.findall(r"[a-z']+", q))
        stems = {w.rstrip("s") for w in words} | words
        best = None
        for g in self.bank.daily.get("howto", []):
            if any(all(k in stems or k.rstrip("s") in stems for k in group) for group in g["keys"]):
                best = g
                break
        d = self.bank.daily
        if best is None:
            group = self.everyday._advice_group(q, {})
            if group not in (None, "generic") and group in d["advice"] and re.search(r"\b(?:i|my|me)\b", q):
                # "how do I get over a breakup?": the advice a friend would give, not "no guide"
                return Reply(text, "smalltalk", self._pick(st, f"daily:advice:{group}", d["advice"][group]), via="everyday")
            if re.search(r"\b(?:i|my|me)\b", q):           # a practical question about doing something
                return Reply(text, "unknown", self._pick(st, "daily:howto_none", d["howto_none"]), via="everyday")
            return None                                    # "how does a rainbow form?": the reading may know
        body = "\n".join("• " + x for x in best["steps"])
        st.last_action = {"kind": "howto", "turn": st.turn, "title": best["title"]}
        return Reply(text, "smalltalk", f"{best['title']}:\n\n{body}", via="everyday")

    def _likes_answer(self, st: DialogState, text: str) -> Reply | None:
        """"what do I like?" / "what don't I like?": the favourites or dislikes you told me."""
        m = _LIKES_Q.match(text.strip())
        if not m:
            return None
        verb = (m.group("v") or m.group("v2") or "").lower()
        neg = bool(m.group("neg")) or bool(m.group("v2")) or verb in ("hate", "dislike")
        rel = "#dislike" if neg else "#fav"
        vals = list(dict.fromkeys(f.object for f in self.bot.facts.facts
                                  if f.subject == USER and rel in f.relation and f.object))
        if not vals:
            return Reply(text, "unknown", self._pick(st, "daily:likes_none", self.bank.daily["likes_none"]), via="facts")
        joined = vals[0] if len(vals) == 1 else ", ".join(vals[:-1]) + " and " + vals[-1]
        key = "dislikes_list" if neg else "likes_list"
        return Reply(text, "answer", self._pick(st, f"daily:{key}", self.bank.daily[key], x=joined),
                     answer=joined, source={"kind": "user"}, via="facts")

    def _measure_quote(self, st: DialogState, text: str) -> Reply | None:
        """"How big is the Sun?" / "How far away is it?": the sentence of the topic's own article that
        gives that measure with a unit, quoted with its source — the topic is certain, the number
        is the article's, nothing is guessed."""
        q = self.bot.resolve(" ".join(text.split()))
        m = _MEASURE_TOPIC.match(q)
        if not m:
            return None
        dim, topic = m.group("dim").lower(), m.group("t").strip(" ?.")
        if re.fullmatch(r"(?:he|she|they|him|her|them)", topic, re.I):
            return None                                   # a person: the pronoun flow, never a measure of a place
        if re.fullmatch(r"(?:it|that|this|there)", topic, re.I):
            last = self.bot.context.get("mention")
            if not last:
                return None
            topic = last
        docs = []
        for v in (topic, re.sub(r"^(?:the|a|an)\s+", "", topic, flags=re.I)):
            docs = self.about.titles.lookup(v) or self.about.titles.lookup(_place_case(v))
            if docs:
                break
        if not docs:
            return None
        cues = _MEASURE_CUES.get(dim)
        lo, hi = self.bot.c.doc_sentences(docs[0])
        title = self.bot.c.doc_keys[docs[0]][1]
        units = _DIM_UNIT.get(dim.split()[0], _UNIT)
        for sid in range(lo, min(hi, lo + 14)):
            sent = clean_sentence(self.bot.c.sentence_text(sid))
            near = any(units.search(sent[max(0, c.start() - 40):c.end() + 70]) for c in cues.finditer(sent))
            if near and len(sent) < 400:
                self.bot.context.update({"mention": title, "answer": None, "atype": None})
                src = {"kind": "wikipedia", "title": title, "key": title,
                       "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")}
                st.last_fact = {"evidence": sent, "source": src, "answer": None, "question": q, "sure": True}
                body = self._pick(st, "daily:measure_quote", self.bank.daily["measure_quote"], title=title, evidence=sent)
                return Reply(text, "answer", body, evidence=sent, source=src, via="about")
        # the topic's own article does not give it: say so rather than take a number from elsewhere
        self.bot.context.update({"mention": title, "answer": None, "atype": None})
        st.last_fact = None
        return Reply(text, "unknown", self._pick(st, "daily:measure_none", self.bank.daily["measure_none"], title=title),
                     source={"kind": "wikipedia", "title": title, "key": title,
                             "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")}, via="lookup")

    def _shelf_topic(self, q: str) -> str | None:
        """The article a question names, by the shelf's title index (all of Wikipedia): "who won the
        2023 rugby world cup" → "2023 Rugby World Cup"; also with the year moved to the front."""
        shelf = getattr(self.atlas, "shelf", None) if self.atlas is not None else None
        if shelf is None or getattr(shelf, "index", None) is None:
            return None
        words = re.findall(r"[A-Za-z0-9][\w'’-]*", q)
        for size in range(min(6, len(words)), 1, -1):
            for i in range(len(words) - size + 1):
                gram = words[i:i + size]
                if gram[0].lower() in _TOPIC_EDGE or gram[-1].lower() in _TOPIC_EDGE:
                    continue
                forms = [" ".join(gram)]
                year = next((w for w in (gram[0], gram[-1]) if re.fullmatch(r"(?:1[5-9]|20)\d\d", w)), None)
                if year:
                    rest = [w for w in gram if w != year]
                    for f in ([year] + rest, [year, "FIFA"] + rest, [year, "UEFA"] + rest, ["UEFA"] + rest + [year],
                              [year] + rest + ["Championships"], [year] + rest + ["Championship"]):
                        forms.append(" ".join(f))                 # "wimbledon 2023" → "2023 Wimbledon Championships"
                for f in forms:
                    try:
                        d = shelf.index.lookup(f)
                    except Exception:
                        d = None
                    if d is not None:
                        return shelf.index.title(d)
        return None

    def _before(self, rep: Reply) -> str:
        """The sentence before the evidence in its article ("Bell … telephone. He was born in Edinburgh.")."""
        rows = getattr(self.bot, "last_rows", None) or []
        if not rows or rows[0][3] != rep.evidence or rows[0][2] is None or rows[0][2] <= 0:
            return ""
        sid = int(rows[0][2])
        c = self.bot.c
        try:
            if int(c.sent_doc[sid - 1]) != int(c.sent_doc[sid]):
                return ""
            return c.sentence_text(sid - 1)
        except Exception:
            return ""

    def _wrong_kind(self, q: str, answer: str | None) -> bool:
        """"Who won the marathon?" — "Los Angeles": a place (by the fact bank) is no "who".
        "Who climbed it first?" — "British": a nationality is no person either. "What is the
        tallest mountain?" — "Bhutan": the answer must be the kind of thing asked for."""
        if not answer or self.kgqa is None:
            return False
        head = _ASKED_KIND.search(q)
        if head and not re.match(r"^\s*who\b", q, re.I):
            want = _KIND_TYPES.get(head.group("k").lower().rstrip("s"))
            try:
                hits = self.kgqa.kb.link(answer, limit=1)
            except Exception:
                hits = []
            got = (hits[0][0].type or "") if hits and hits[0][1] == 0 else ""
            return bool(want and got and got not in want)
        if not re.match(r"^\s*who\b", q, re.I):
            return False
        if answer.strip().lower() in _DEMONYMS:
            return True
        try:
            hits = self.kgqa.kb.link(answer, limit=1)
        except Exception:
            return False
        if not hits or hits[0][1] != 0:
            return False
        kind = hits[0][0].type or ""
        if kind in (_PLACE_TYPES - {"Country"}) | _THING_TYPES:
            return True
        # a company or a party is no author, painter, director or president
        return kind in _ORG_TYPES and bool(re.search(r"\b(?:author|writer|wrote|written|painted|painter|directed|director|"
                                                      r"composed|composer|sang|singer|ceo|president|king|queen|husband|"
                                                      r"wife|married|born|died|invented|inventor|discovered|man|woman|"
                                                      r"person)\b", q, re.I))

    def _named_topic(self, q: str) -> str | None:
        """The article a question names, as the fact bank titles it: "who won the world cup 2022?"
        → "2022 FIFA World Cup". Only names of two or more words that are in the reading count."""
        if self.kgqa is None:
            return None
        words = re.findall(r"[A-Za-z0-9][\w'’-]*", q)
        kb = self.kgqa.kb
        for size in range(min(5, len(words)), 1, -1):
            for i in range(len(words) - size + 1):
                gram = words[i:i + size]
                if gram[0].lower() in _TOPIC_EDGE or gram[-1].lower() in _TOPIC_EDGE:
                    continue
                titles = [e.title for e, kind in kb.link(" ".join(gram), limit=2)]
                if not titles and re.fullmatch(r"(?:1[5-9]|20)\d\d", gram[-1]):
                    # "world cup 2022" → "2022 … World Cup": the year in front, words in order
                    pat = gram[-1] + " %" + "%".join(gram[:-1])
                    row = kb.db.execute("SELECT title FROM entity WHERE title LIKE ? ORDER BY popularity DESC LIMIT 1",
                                        (pat,)).fetchone()
                    titles = [row[0]] if row else []
                for t in titles:
                    if self.about.titles.lookup(t):
                        return t
        return None

    def _place_carry(self, st: DialogState, text: str) -> str:
        """"What's the capital again?" while talking about a trip to Japan: the capital of Japan;
        "how many people live there?" → "… in Japan"."""
        pt = st.uses.get("place_topic")
        if not pt or st.turn - pt[1] > 8:
            return text
        m = _PLACE_REL_Q.match(text.strip())
        if m:
            return f"what is the {m.group('r').lower()} of {pt[0]}?"
        if re.search(r"\bthere\b", text, re.I) and not re.search(r"\b(?:is|are) there\b", text, re.I):
            return re.sub(r"\bthere\b", f"in {pt[0]}", text, count=1, flags=re.I)
        return text

    def _cuisine(self, st: DialogState, text: str, place: str) -> Reply | None:
        """"What should I eat in Japan?": the opening of the article on that cuisine."""
        adj = _CUISINE_ADJ.get(place.lower())
        names = ([f"{adj} cuisine"] if adj else []) + [f"Cuisine of {place}"]
        for name in names:
            found = self.about.find(name, n=2)
            if found is not None and found.sentences:
                st.last_about = {"title": found.title, "doc": found.doc, "next": found.next_sentence,
                                 "end": found.end_sentence, "source": found.source}
                lead = self._pick(st, "daily:cuisine_lead", self.bank.daily["cuisine_lead"], x=place)
                return Reply(text, "smalltalk", f"{lead} {' '.join(found.sentences)}", via="about",
                             source=found.source)
        return None

    def _carry_topic(self, st: DialogState, text: str) -> str:
        """"and who was the top scorer?" right after a question about the 2022 World Cup: the
        follow-up keeps the topic it leaves out."""
        last = st.uses.get("q_topic")
        if not last or st.turn - last[1] > 2:
            return text
        m = re.match(r"^\s*(?:and|also|so|ok(?:ay)?|what about)\b[\s,]*(.+)$", text, re.I)
        if not m or re.search(r"\b(?:he|she|it|they|him|her|them|his|its|their|i|me|my|you|your)\b", text, re.I):
            return text
        rest = m.group(1)
        if self._named_topic(rest) or re.search(r"(?<!^)\b[A-Z][a-z]", rest):
            return text
        return f"{rest.rstrip(' ?.!')} at the {last[0]}?"

    def _topic_gap(self, st: DialogState, topic: str | None, rep: Reply) -> Reply | None:
        """The question names an article I have, but the answer comes from another article that
        never names it ("who won the world cup 2022?" → a sentence about the U-17 World Cup): that is
        no answer. Say honestly what the article on the topic does tell."""
        if not topic or rep.via != "lookup":
            return None
        src = rep.source or {}
        bare = re.sub(r"\s*\([^)]*\)$", "", topic).lower()
        title = re.sub(r"\s*\([^)]*\)$", "", str(src.get("title") or src.get("key") or "")).lower()
        if rep.kind == "answer" and (title == bare or bare in (rep.evidence or "").lower()):
            return None
        if rep.kind != "answer" and not (rep.guess or rep.text.startswith("I don't know — I have not read anything")):
            return None
        docs = self.about.titles.lookup(topic)
        head = " ".join(self.about._doc_text(docs[0], n=4, max_chars=900)[0]) if docs else ""
        ongoing = bool(re.search(r"\b(?:is taking place|is being held|is being played|is scheduled|will be held|"
                                 r"is set to|are the defending)\b", head))
        key = "topic_gap_ongoing" if ongoing else "topic_gap"
        rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None
        x = f"the {topic}" if re.match(r"(?:\d|(?:President|Prime Minister|King|Queen|Chancellor|Mayor|Battle|"
                                       r"Siege|Treaty|War|Fall|History|Kingdom|Republic|University)\b)", topic) else topic
        rep.text = self._pick(st, f"daily:{key}", self.bank.daily[key], x=x)
        if self.atlas is None or not self.atlas.any_on():
            rep.text += " " + self.bank.daily["topic_gap_online"][0]
        rep.source = {"kind": "wikipedia", "title": topic, "key": topic,
                      "url": "https://en.wikipedia.org/wiki/" + topic.replace(" ", "_")}
        rep.evidence = None
        st.last_fact = None
        if re.match(r"^\s*who\b", rep.message or "", re.I) or re.match(r"^\s*who\b", rep.resolved or "", re.I):
            st.uses["person_gap"] = st.turn             # "how old is he?" next: ask who is meant
        self.bot.context.update({"answer": None, "atype": None})
        return rep

    def _atlas_answer(self, st: DialogState, text: str) -> Reply | None:
        """The question again, with sentences from the switched-on channels (feeds, shelf,
        messenger) as extra candidates; None when they do not lead to a confident answer."""
        bot = self.bot
        q = bot.resolve(" ".join(text.split()))
        names = [m.group(0) for m in _CAPS_SPAN.finditer(q) if not q.startswith(m.group(0)) or " " in m.group(0)]
        topic_kb, topic_shelf = self._named_topic(q), self._shelf_topic(q)
        # the more specific name wins: "2023 Rugby World Cup" (shelf) over "Rugby World Cup" (fact bank)
        topic = max([t for t in (topic_kb, topic_shelf) if t], key=lambda t: len(t.split()), default=None)
        if topic:
            names.insert(0, topic)                       # "world cup 2022" → fetch "2022 FIFA World Cup"
        if st.topic and st.topic.get("name") and st.turn - st.topic.get("turn", -99) <= 3:
            names.append(st.topic["name"])
        try:
            rows, used = self.atlas.candidates(q, list(dict.fromkeys(names)))
        except Exception:                        # the network must never break the chat
            return None
        if not rows:
            return None
        ctx = dict(bot.context)
        bot.extra_rows, bot.extra_calib = rows, getattr(self.atlas, "calib", None)
        bot.extra_only = bool(topic) and any(_on_topic(topic, r[1], r[0]) for r in rows)
        try:
            rep = bot._answer(q)
        finally:
            bot.extra_rows, bot.extra_calib, bot.extra_only = [], None, False
        src = rep.source or {}
        win = None
        if _WINNER_Q.match(q):
            full = list(rows)
            for d in getattr(self.atlas, "last_docs", None) or []:
                src_d = {"kind": "shelf", "source": "wikipedia", "key": d["t"], "title": d["t"], "as_of": d.get("d", "")}
                full += [(x, src_d) for x in re.split(r"(?<=[.!?])\s+", d.get("x", "")) if 20 < len(x) < 600]
            years = re.findall(r"\b(?:1[5-9]|20)\d\d\b", q)
            if not (years and topic and not any(y in topic for y in years)):   # "Super Bowl" for 2024: all editions
                win = _winner_from(full, topic)
        if win is not None:
            rep.kind, rep.answer, rep.guess, rep.evidence, rep.source = "answer", win[0], win[0], win[1], win[2]
            rep.confidence = max(rep.confidence, 1.0)
            src = rep.source
        elif _WINNER_Q.match(q):
            rep.kind = "unknown"                          # the span extractor guesses badly here: quote instead
        if rep.kind != "answer" or src.get("kind") not in ("shelf", "feed", "web"):
            quote = self._atlas_quote(st, text, q, rep, names)
            if quote is None:
                bot.context = ctx
            return quote
        if win is None and (_implausible(q, rep.answer, rep.evidence, _src_title(src)) or not _on_topic(topic, src, rep.evidence)
                            or self._wrong_kind(q, rep.answer)):
            # "West Indies won the world cup 2022" from the T20 article: not this topic, not an answer
            quote = self._atlas_quote(st, text, q, rep, names)
            if quote is None:
                bot.context = ctx
            return quote
        full = _full_name(rep.answer, [r[0] for r in rows if r[1].get("key") == src.get("key")])
        if full != rep.answer:                   # "Vickers" → "Diana Vickers" (named so in the same article)
            rep.answer = full
        sent = answer_sentence(q, rep.answer, _atype(q)) or f"{rep.answer}."
        when = src.get("as_of")
        where = {"shelf": "Wikipedia", "feed": src.get("source", "a news feed"), "web": src.get("source", "the web")}[src["kind"]]
        note = f" (from {where}{', as of ' + when if when else ''})"
        # source agreement: other sources among the fetched sentences that say the same
        others = _agreeing_sources(rep.answer, rows, src)
        if others:
            note = note[:-1] + "; " + ("also " if len(others) == 1 else "also in ") + " and ".join(others[:2]) + ")"
            rep.confidence = max(rep.confidence, 1.0)
        rep.text = sent.rstrip(".") + note + "."
        rep.via = "atlas"
        rep.message = text
        st.last_fact = {"evidence": rep.evidence, "source": src, "answer": rep.answer, "question": q, "sure": True}
        return rep

    def _about_me(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Lines about ENGRAMM itself or about the conversation, which must never go to the reading:
        "have you seen it?", "you can't watch movies", "what did we talk about?", "that joke was bad",
        and "something with chicken" after cooking ideas."""
        d = self.bank.daily
        la = st.last_action or {}
        recent = st.turn - la.get("turn", -99) <= 3
        m = _BOT_EXPERIENCE.match(norm)
        if m and m.group("v") in ("been to", "been", "visited") and (m.group("rest") or "").strip(" ?"):
            place = _place_case(re.sub(r"^(?:to|in)\s+", "", m.group("rest").strip(" ?")))
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_travel", d["bot_travel"], x=place), via="smalltalk")
        if m and m.group("v") in ("eat", "eaten", "taste", "tasted", "smell") and not (m.group("rest") or "").strip(" ?"):
            m = None                              # "do you eat?": a question about ENGRAMM's nature
        if m:
            what = (m.group("rest") or "").strip(" ?")
            what = "it" if not what or what in ("it", "that", "this", "them", "this one", "that one") else what
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_experience", d["bot_experience"],
                                                      x=_VERB_BASE.get(m.group("v"), m.group("v")), topic=what),
                         via="smalltalk")
        if _BOT_LIMIT.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_limit", d["bot_limit"]), via="smalltalk")
        if _WHERE_WERE_WE.match(norm):
            themes = st.uses.get("recap", [])
            if themes:
                last = "you" if themes[-1] == "things about you" else themes[-1]
                return Reply(msg, "smalltalk", self._pick(st, "daily:where_were_we", d["where_were_we"], x=last),
                             via="smalltalk")
            return Reply(msg, "smalltalk", self._pick(st, "daily:recap_none", d["recap_none"]), via="smalltalk")
        if _RECAP.match(norm):
            themes = st.uses.get("recap", [])
            if not themes:
                return Reply(msg, "smalltalk", self._pick(st, "daily:recap_none", d["recap_none"]), via="smalltalk")
            listed = themes[-6:]
            joined = listed[0] if len(listed) == 1 else ", ".join(listed[:-1]) + " and " + listed[-1]
            return Reply(msg, "smalltalk", self._pick(st, "daily:recap", d["recap"], x=joined), via="smalltalk")
        if recent and la.get("kind") == "joke" and _JOKE_BAD.match(norm):
            st.last_action = {"kind": "joke", "turn": st.turn}
            st.offer = {"kind": "joke", "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "daily:joke_bad", d["joke_bad"]), via="smalltalk")
        if recent and la.get("kind") == "joke" and _JOKE_GOOD.match(norm):
            st.last_action = {"kind": "joke", "turn": st.turn}
            st.offer = {"kind": "joke", "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "daily:joke_good", d["joke_good"]), via="smalltalk")
        m = _REFINE.match(norm)
        if m and recent and la.get("kind") == "rec:food":
            x = m.group("x").strip()
            ideas = d["recommend"]["food"].get("with", {}).get(x) or \
                d["recommend"]["food"].get("with", {}).get(x.rstrip("s"))
            if ideas:
                st.last_action = {"kind": "rec:food", "turn": st.turn}
                body = "\n".join("• " + i[:1].upper() + i[1:] for i in ideas[:3])
                head = self._pick(st, "daily:refine_head", d["refine_head"], x=x)
                return Reply(msg, "smalltalk", f"{head}\n\n{body}", via="everyday")
        return None

    def _with_offline_view(self, st: DialogState, text: str, fresh: Reply) -> Reply:
        """A newer answer from the network that the offline fact bank contradicts: say both, with
        their dates, newer first — never silently one of them."""
        if fresh.kind != "answer" or not fresh.answer or self.kgqa is None:
            return fresh
        ctx = dict(self.bot.context)
        old = self._kb_answer(DialogState(st.conversation + "#kb"), text)
        self.bot.context = ctx
        if old is None or not old.answer or _same_value(old.answer, fresh.answer):
            return fresh
        fresh.text = fresh.text.rstrip(".") + f". My offline fact bank (older) still says {old.answer}."
        fresh.alternatives = [{"text": old.text, "source": old.source}] + list(fresh.alternatives or [])
        return fresh

    def _atlas_quote(self, st: DialogState, text: str, q: str, rep: Reply, names: list[str]) -> Reply | None:
        """Not sure of the short answer, but the best sentence comes from the article the question
        names and shares its other words: say so and quote it with its source, as a person would —
        never a guessed short answer."""
        src = rep.source or {}
        if not rep.evidence or src.get("kind") not in ("shelf", "web"):
            return None
        title = str(src.get("title") or "")
        shelf = getattr(self.atlas, "shelf", None)
        bare = re.sub(r"\s*\([^)]*\)$", "", title).lower()
        named = bool(bare) and bare in q.lower() or any(
            _name_match(n, title) or (shelf is not None and shelf.index.lookup(n) is not None
                                      and shelf.index.title(shelf.index.lookup(n)) == title) for n in names)
        if not named:
            return None
        rest = _stems(q) - _stems(title) - _QUOTE_STOP
        if not rest:
            return None
        # the best candidate sentence of that article that has the question's other words
        ev = None
        for row in [(None, None, None, rep.evidence, src)] + list(getattr(self.bot, "last_rows", []) or []):
            text_, rsrc = row[3], row[4] or {}
            if rsrc.get("key") != src.get("key"):
                continue
            have = _stems(text_) | ({"born", "die"} if _LIFE_SPAN_RE.search(text_) else set())
            if rest & have:
                ev = text_
                break
        if ev is None:
            return None
        when = src.get("as_of")
        where = f"Wikipedia's article “{title}”" if src["kind"] == "shelf" else f"the page “{title}” ({src.get('source')})"
        say = self._pick(st, "daily:atlas_quote", self.bank.daily["atlas_quote"], title=where, evidence=ev)
        say = say[:1].upper() + say[1:] + (f" (as of {when})." if when else "")
        st.last_fact = {"evidence": ev, "source": src, "answer": None, "question": q, "sure": False}
        return Reply(text, "about", say, None, rep.guess, ev, src, 0.0, "atlas", rep.resolved, rep.alternatives)

    def _atlas_about(self, st: DialogState, text: str, topic: str) -> Reply | None:
        """"Tell me about X" when the local reading has no article: the shelf (or the live page)."""
        if self.atlas is None or not self.atlas.any_on():
            return None
        try:
            if self.atlas.shelf is not None and self.egress_on("shelf"):
                docs = self.atlas.shelf.documents(topic, k=1, seed=self.atlas.seed, prefer_title=topic)
                ix = self.atlas.shelf.index
                named = ix.lookup(topic)                 # a title or redirect ("xHCI" → the full name)
                if docs and (_name_match(topic, docs[0]["t"]) or (named is not None and ix.title(named) == docs[0]["t"])):
                    d = docs[0]
                    from engramm.web.shelf import _SENT
                    sents = [x.strip() for x in _SENT.split(d["x"].split("\n")[0]) if x.strip()][:3]
                    if sents:
                        src = {"kind": "shelf", "source": "wikipedia", "key": d["t"], "title": d["t"], "as_of": d.get("d", "")}
                        st.last_fact = {"evidence": sents[0], "source": src, "answer": None, "question": None, "sure": True}
                        self.bot.context.update({"answer": None, "atype": None, "mention": d["t"], "kb_last": None})
                        st.topic = {"title": d["t"], "name": d["t"], "turn": st.turn}
                        return Reply(text, "about", " ".join(sents), evidence=sents[0], source=src, via="atlas",
                                     confidence=1.0)
            if self.egress_on("messenger"):
                rows = self.atlas._messenger(f"what is {topic}", [topic])
                if rows:
                    first = [r for r in rows if r[1]["kind"] == "web"][:3]
                    if first:
                        src = first[0][1]
                        return Reply(text, "about", " ".join(r[0] for r in first), evidence=first[0][0], source=src,
                                     via="atlas", confidence=1.0)
        except Exception:
            return None
        return None

    def egress_on(self, channel: str) -> bool:
        return self.atlas is not None and self.atlas.egress.enabled(channel)

    def _news(self, st: DialogState, msg: str, topic: str | None) -> Reply:
        if self.atlas is None or not self.egress_on("feeds"):
            return Reply(msg, "unknown", self._pick(st, "daily:news_off", self.bank.daily["news_off"]), via="news")
        items = self.atlas.news(topic, k=5)
        if not items:
            key = "news_none_topic" if topic else "news_none"
            return Reply(msg, "unknown", self._pick(st, f"daily:{key}", self.bank.daily[key], x=topic or ""),
                         via="news")
        lines = []
        for it in items:
            when = dt.datetime.fromtimestamp(it["published"]).strftime("%d %b, %H:%M")
            lines.append(f"• {it['title']} — {it['feed_title']}, {when}")
        head = f"Here's what my news feeds say about {topic}:" if topic else "The latest from your news feeds:"
        src = {"kind": "feed", "source": items[0]["feed"], "key": items[0]["link"] or items[0]["title"],
               "title": items[0]["title"]}
        return Reply(msg, "about", head + "\n" + "\n".join(lines), source=src, evidence=items[0]["title"],
                     via="news", confidence=1.0, alternatives=[{"text": it["title"], "source": {
                         "kind": "feed", "source": it["feed"], "key": it["link"] or it["title"], "title": it["title"]}}
                         for it in items[1:4]])

    def _common_fact(self, st: DialogState, text: str) -> Reply | None:
        """"How many continents are there?", "is a tomato a fruit?": a short list of everyday facts checked
        by hand (data/conv/daily.yaml `common`), because the text look-up gets exactly these wrong
        ("two continents", "Sweet")."""
        q = normalise(text).strip(" ?!.")
        for item in self.bank.daily.get("common", []):
            if re.fullmatch(item["q"], q):
                src = {"kind": "common", "source": "everyday facts", "key": item.get("key", "")}
                return Reply(text, "answer", item["a"], answer=item.get("v", item["a"]), source=src, confidence=1.0,
                             via="common")
        return None

    def _superlative(self, st: DialogState, text: str) -> Reply | None:
        """"What is the tallest mountain in the world?" from the measured values in the fact bank
        (engramm/kb/superlative.py); the answer becomes the topic, so "how tall is it?" follows."""
        if self.kgqa is None:
            return None
        from engramm.kb import superlative
        last = st.uses.get("superlative")
        rank = 1
        nm = _NEXT_RANK.fullmatch(normalise(text).strip(" ?!."))
        if nm and last and st.turn - last[1] <= 3:
            text, rank = last[0], {"second": 2, "2nd": 2, "third": 3, "3rd": 3}[nm.group(1)]
        try:
            ans = superlative.answer(self.kgqa.kb.db, text, rank=rank)
        except Exception:                       # a damaged fact bank must not break the chat
            return None
        if ans is None:
            return None
        st.uses["superlative"] = [text, st.turn]
        src = {"kind": "kb", "source": "dbpedia", "key": ans.title}
        self.bot.context.update({"answer": ans.title, "atype": None, "mention": ans.title, "kb_last": None})
        st.topic = {"title": ans.title, "name": ans.title, "turn": st.turn}
        st.last_fact = {"evidence": ans.text, "source": src, "answer": ans.title, "question": text, "sure": True}
        return Reply(text, "answer", ans.text, answer=ans.title, guess=ans.title, evidence=ans.text, source=src,
                     confidence=1.0, via="kb")

    def _kb_answer(self, st: DialogState, text: str) -> Reply | None:
        """A question about a named thing, answered from the fact bank (exact infobox facts)."""
        if self.kgqa is None or re.search(r"\b(?:i|me|my|mine|i'm)\b", text.lower()):
            return None
        q = self.bot.resolve(" ".join(text.split()))
        try:
            ans = self.kgqa.answer(q)
        except Exception:                       # a damaged fact bank must not break the chat
            return None
        if ans is None:
            return None
        value = _join_values(ans.values)
        src = {"kind": "kb", "source": "dbpedia", "key": ans.entity.title}
        atype = _atype(q)
        self.bot.context.update({"answer": ans.values[0] if len(ans.values) == 1 else None, "atype": atype,
                                 "mention": ans.entity.name})
        st.last_fact = {"evidence": ans.evidence, "source": src, "answer": value, "question": q, "sure": True}
        self.bot.context["kb_last"] = {"question": q, "names": [ans.entity.name, ans.entity.title]}
        named = ans.values[0] if len(ans.values) == 1 and not re.search(r"\d", ans.values[0]) else ans.entity.name
        st.uses["kb_vals"] = (st.uses.get("kb_vals", []) + [[st.turn, named]])[-4:]
        return Reply(text, "answer", ans.text, answer=value, guess=value, evidence=ans.evidence, source=src,
                     confidence=1.0, via="kb", resolved=q if q != text else None)

    def _event_answer(self, st: DialogState, text: str) -> Reply | None:
        """"When did the Berlin Wall fall?": the first sentence of the article "Fall of the Berlin Wall"."""
        from engramm.kb.kgqa import EVENT_NOUNS, EVENT_Q
        m = EVENT_Q.match(text.strip())
        if not m:
            return None
        for noun in EVENT_NOUNS[m.group("ev").lower()]:
            found = self.about.find(f"{noun} of {m.group('e')}", n=1)
            if found is not None and re.search(r"\b(?:1[0-9]{3}|20[0-9]{2})\b", found.sentences[0]):
                st.last_about = found
                return Reply(text, "answer", found.sentences[0], answer=None, evidence=found.sentences[0],
                             source=found.source, confidence=1.0, via="about")
        return None

    def _ellipsis(self, st: DialogState, msg: str) -> str | None:
        """"And of Germany?" after "What is the capital of France?" → "What is the capital of Germany?"."""
        m = _ELLIPSIS.match(msg.strip())
        if not m:
            return None
        new = m.group("x").strip()
        last = self.bot.context.get("kb_last")
        if last and st.last_q and last["question"].strip(" ?").lower() != st.last_q.strip(" ?").lower() \
                and self.bot.resolve(st.last_q).strip(" ?").lower() != last["question"].strip(" ?").lower():
            last = None                                   # a newer question came after the fact-bank one
        if last:
            for name in last["names"]:
                if name and re.search(re.escape(name), last["question"], re.I):
                    return re.sub(re.escape(name), new, last["question"], count=1, flags=re.I)
        q = st.last_q_named or st.last_q
        if q:
            # the last question's named thing ("Who is the CEO of Apple?" → "Apple"), not its first word
            names = [n for n in re.findall(r"\b[A-Z][\w'’.-]*(?:\s+(?:of|the|and|de|von|van)?\s*[A-Z][\w'’.-]*)*", q)
                     if not q.startswith(n) or len(n.split()) > 1]
            if names:
                old = max(names, key=len)
                head, sep, tail = old.rpartition(" of ")
                if sep and len(head.split()) == 1:          # "CEO of Apple": the company, not the role
                    old = tail
                return q.replace(old, new, 1)
        return None

    def _prefer_correction(self, msg: str) -> str:
        """"actually I prefer ramen" right after "my favorite food is sushi" → "My favourite food is ramen."
        — the correction keeps the category it corrects."""
        m = _PREFER.match(normalise(msg))
        sid = self.bot.context.get("last_learned")
        if not m or not sid:
            return msg
        for f in self.bot.facts.facts:
            if f.source == sid and f.subject == USER:
                for lab, noun in _FAV_NOUN.items():
                    if lab in f.relation:
                        return f"My favourite {noun} is {m.group('x').strip()}."
        return msg

    def _proper_case(self, text: str) -> str:
        """"my name is thomas" → "my name is Thomas", "i moved to munich" → "… Munich" — a name after a
        name cue, and a place after a place cue when the fact bank knows it as a place."""
        def name(m):
            return m.group(1) + " ".join(w[:1].upper() + w[1:] for w in m.group(2).split())
        text = _NAME_CUE.sub(name, text)
        g = _HI_IM.match(text.strip())
        if g and self.bank.feeling(g.group(2).lower()) is None and g.group(2).lower() not in _NOT_NAMES:
            ls = self.bot.typer.lower_share(g.group(2)) if self.bot.typer is not None else None
            if ls is None or ls < 0.5:                    # "hi im sam" → "hi im Sam"; "hi im tired" stays
                text = g.group(1) + g.group(2)[:1].upper() + g.group(2)[1:] + text.strip()[g.end(2):]
        if self.kgqa is None:
            return text

        def place(m):
            words = m.group(2)
            for n in range(min(3, len(words.split())), 0, -1):
                cand = " ".join(words.split()[:n])
                if cand.lower() in ("a", "an", "the", "my", "new", "some", "another") or len(cand) < 3:
                    continue                          # "moved to a new city": no place called "A"
                try:
                    hits = self.kgqa.kb.link(cand, limit=1)
                except Exception:
                    hits = []
                if hits and (hits[0][0].type or "") in _PLACE_TYPES:
                    rest = words[len(cand):]
                    return m.group(1) + _place_case(cand) + rest
            return m.group(0)
        return _PLACE_CUE.sub(place, text)

    def _latest_fact(self, cat: str):
        """Your most recent fact of a category (the later statement corrects the earlier one)."""
        self.bot.refresh()
        order = {sid: i for i, sid in enumerate(self.bot.user_texts())}
        cands = [f for f in self.bot.facts.facts if f.subject == USER and cat in f.relation]
        return max(cands, key=lambda f: (order.get(f.source, -1), f.object)) if cands else None

    def _fact_for(self, rep: Reply):
        src = (rep.source or {}).get("source")
        for f in self.bot.facts.facts:
            if f.source == src and f.object == rep.answer:
                return f
        return None

    def _about(self, st: DialogState, u: Unit) -> Reply:
        kind, topic = u.data["kind"], u.data["topic"]
        resolved = self.bot.resolve(topic) if re.search(r"\b(?:he|she|it|him|her|they|them|this|that)\b", topic,
                                                         flags=re.I) else topic
        found = self.about.find(resolved)
        if found is None and kind in ("what", "tell", "define") and not _CAPS_NAME.search(resolved):
            found = self.about.find(resolved.title()) if resolved.islower() else None
        if found is None:
            shelf = self._atlas_about(st, u.text, resolved)
            if shelf is not None:
                return shelf
            if kind == "what" or kind == "tell" and re.match(r"^(?:who|what|when|where|why|how)\b", topic, re.I):
                return self._question(st, u.text)
            if kind == "opinion":
                return Reply(u.text, "smalltalk", self._pick(st, "intent:bot_opinion",
                                                             self.bank.by_id["bot_opinion"].responses), via="smalltalk")
            text = self._reply(st, "about.none", topic=resolved)
            return Reply(u.text, "unknown", text, via="about")
        return self._about_reply(st, u.text, found, kind)

    def _about_reply(self, st: DialogState, text: str, found: About, kind: str) -> Reply:
        body = " ".join(found.sentences)
        if kind == "opinion":
            body = "I don't have opinions of my own, but here's what I've read: " + body
        st.last_about = {"title": found.title, "doc": found.doc, "next": found.next_sentence,
                         "end": found.end_sentence, "source": found.source, "turn": st.turn}
        st.last_fact = {"evidence": found.sentences[0], "source": found.source, "answer": None, "question": None,
                        "sure": True}
        self.bot.context.update({"answer": None, "atype": None, "mention": found.title, "kb_last": None})
        st.last_q = st.last_q_named = None        # a new topic: "where?" no longer means the old question
        return Reply(text, "about", body, evidence=found.sentences[0], source=found.source, via="about",
                     confidence=1.0)

    def _more(self, st: DialogState, text: str) -> Reply:
        la = st.last_about
        topic = st.topic if st.topic and st.turn - st.topic.get("turn", -99) <= 4 else None
        if la and topic and la.get("title") != topic.get("title") and la.get("turn", -99) < topic.get("turn", -99):
            la = None                            # the conversation moved on to another topic
            found = self.about.find(topic["title"]) or self.about.find(topic.get("name") or topic["title"])
            if found:
                return self._about_reply(st, text, found, "tell")
        if la:
            ab = self.about.more(About(la["title"], la["doc"], [], la["next"], la["end"], la["source"]))
            if ab is None:
                return Reply(text, "about", self._reply(st, "about.more_none", title=la["title"]), via="about")
            return self._about_reply(st, text, ab, "tell")
        mention = self.bot.context.get("mention")
        if mention:
            found = self.about.find(mention)
            if found:
                return self._about_reply(st, text, found, "tell")
        return Reply(text, "smalltalk", self._reply(st, "about.more_nothing"), via="smalltalk")

    def _why(self, st: DialogState, text: str) -> Reply:
        lf = st.last_fact
        if not lf or not lf.get("evidence"):
            if st.last_kind == "smalltalk" and st.last_reply and st.last_reply.rstrip().endswith("?"):
                # "why?" after ENGRAMM's own opinion or question: a person's answer, not a source
                return Reply(text, "smalltalk", self._pick(st, "daily:why_smalltalk", self.bank.daily["why_smalltalk"]),
                             via="smalltalk")
            return Reply(text, "smalltalk", self._reply(st, "why.none"), via="smalltalk")
        src = lf.get("source") or {}
        if src.get("kind") == "user":
            out = self._reply(st, "why.user", evidence=lf["evidence"])
        elif src.get("kind") == "kb":
            out = self._reply(st, "why.kb", title=src.get("key"), evidence=lf["evidence"])
        else:
            out = self._reply(st, "why.base", title=src.get("key") or "a text I read", evidence=lf["evidence"])
        if not lf.get("sure", True):
            out += self.bank.replies["why"]["unsure"]
        if st.last_reply and out.strip() == st.last_reply.strip():
            # "are you sure?" then "how do you know?": not the same words again
            title = src.get("title") or src.get("key") or "my source"
            out = self._pick(st, "daily:why_again", self.bank.daily["why_again"], title=title)
        return Reply(text, "answer", out, evidence=lf["evidence"], source=src, via="why")

    # -- memory -------------------------------------------------------------------------------

    def _worth_learning(self, sentence: str) -> bool:
        """Remember a statement only if it carries something: a recognised fact, something about
        you, or a named thing."""
        s = sentence.strip()
        if len(s) < 3 or is_discourse(normalise(s)) or _WRAP_UP.search(normalise(s)):
            return False
        if _TRANSIENT.search(normalise(s)) and not {r for f in facts_from_text(s, "probe", self.bot.is_name_initial_fact,
                                                                                typer=self.bot.typer)
                                                     for r in f.relation} & _CATEGORY_LABELS:
            return False                         # "she's sleeping on my lap right now": a moment, not a memory
        facts = facts_from_text(s, "probe", self.bot.is_name_initial_fact, typer=self.bot.typer)
        if facts:
            return True
        low = normalise(s)
        words = low.split()
        if re.search(r"\b(?:i|i'm|i've|me|my|mine|we|we're|our|us)\b", low) and len(words) >= 3:
            content = [w for w in words if len(w) > 2 and w not in _STOP_CHAT]
            return len(content) >= 1
        caps = [m.group(0) for m in _CAPS_NAME.finditer(s)]
        first = s.split()[0] if s.split() else ""
        names = [c for c in caps if c != first or self.bot.is_name_initial_fact(c)]
        return bool(names) and len(words) >= 3

    def _again(self, st: DialogState, msg: str) -> Reply | None:
        """"another one" / "one more": the same kind of thing as last time (a joke, a fact, a quote,
        suggestions, a quiz question or a riddle)."""
        la = st.last_action
        if not la or st.turn - la.get("turn", -99) > 6:
            return None
        kind = la["kind"]
        if kind in ("joke", "fun_fact", "quote", "story"):
            return self._action(st, kind, Unit("intent", msg))
        if kind == "quiz":
            return self.everyday.start_quiz(st, msg, first=False)
        if kind == "riddle":
            return self.everyday.start_riddle(st, msg)
        if kind.startswith("rec:"):
            return self.everyday.recommend(st, msg, kind[4:], la.get("genre"), more=True)
        return None

    def _discourse(self, st: DialogState, u: Unit) -> str:
        n = u.norm
        d = self.bank.daily["discourse"]
        if re.search(r"\b(?:question|ask)\b", n):
            return self._pick(st, "daily:disc:q", d["question_coming"])
        if re.search(r"\bhelp\b", n):
            return self._pick(st, "daily:disc:help", d["help"])
        if re.search(r"\b(?:confused|lost)\b", n):
            return self._pick(st, "daily:disc:confused", d["confused"])
        if re.search(r"\b(?:agree|me too|same here|me neither|i know right|i thought so|i knew it)\b", n):
            return self._pick(st, "daily:disc:agree", d["agree"])
        if st.last_reply.rstrip().endswith("?") and re.search(r"\b(?:know|idk|dunno|sure|idea|guess)\b", n):
            return self._pick(st, "daily:disc:after_q", d["after_question"])
        return self._pick(st, "daily:disc:plain", d["plain"])

    def _plan(self, st: DialogState, u: Unit) -> str:
        """"I'm thinking about moving to Berlin" → "Moving to Berlin — exciting! What's drawing you there?"
        A plan is not a fact (you don't live in Berlin yet), so it is answered, not stored."""
        m = _PLAN.search(u.norm)
        what = u.text[m.end():].strip(" .!") if m else ""
        what = re.sub(r"^(?:to|of|about|on)\s+", "", what, flags=re.I)
        what = swap_person(what) if what else ""
        if what and len(what.split()) <= 8:
            head = what[:1].upper() + what[1:]
            big = re.match(r"(?:quit|quitting|leav|break|divorc|drop|mov|resign|sell|end|stop)", what.lower())
            st.last_exp = {"valence": "plan", "topic": what, "person": False, "text": u.text, "turn": st.turn}
            key = "plan_big" if big else "plan"
            return self._pick(st, f"daily:{key}", self.bank.daily[key], x=head)
        return self._pick(st, "daily:plan_plain", self.bank.daily["plan_plain"])

    def _has_fact(self, sentence: str) -> bool:
        """A sentence with something lasting to remember (a name, a job, a home …), not just a mood:
        "my boss Tom was so rude" keeps that your boss is called Tom; "my boss was annoying" keeps nothing."""
        from engramm.chat.facts import CATEGORIES
        for f in facts_from_text(sentence, "probe", self.bot.is_name_initial_fact, typer=self.bot.typer):
            if set(f.relation) & CATEGORIES or (f.object[:1].isupper() and f.kind == "NAME"):
                return True
        return False

    def _feeling_has_fact(self, sentence: str) -> bool:
        from engramm.chat.facts import CATEGORIES
        for f in facts_from_text(sentence, "probe", self.bot.is_name_initial_fact, typer=self.bot.typer):
            if f.subject.startswith(USER + ":") or set(f.relation) & (CATEGORIES - {"#fav"}):
                return True
        return False

    def _learn(self, st: DialogState, sentences: list[str], msg: str) -> Reply:
        bot = self.bot
        text = self._proper_case(_job_field(resolve_statement(" ".join(s.strip() for s in sentences if s.strip()))))
        sid = source_id(text)
        if sid in bot.user_texts():
            return Reply(msg, "known", self._reply(st, "learned.already"), source={"kind": "user", "source": sid},
                         via="memory")
        name_before = self.user_name()
        bot.memory.learn_text(text, sid)
        bot.refresh()
        bot.context["last_learned"] = sid
        fs = [f for f in bot.facts.facts if f.source == sid]
        confirm = self._confirm(st, fs, name_before)
        wf = _WORK_IN.match(text.strip())
        if wf and text.rstrip(".").endswith(f"My job is in {wf.group('f').strip()}"):
            confirm = self._pick(st, "daily:work_field", self.bank.daily["work_field"], x=wf.group("f").strip())
        found = None
        if self._generic_confirm and self.kgqa is not None:
            # "I watched Inception yesterday": say something about the film instead of "Noted."
            found = self.everyday.entity_reaction(st, text)
            if found is not None:
                confirm = found[0]
        if self._generic_confirm and (self.kgqa is None or found is None):
            plain = self.everyday.activity_reaction(st, text)      # "I watched Inception": ask how it was
            if plain is not None:
                confirm = plain
        dm = _DONE_WITH.match(text.strip())
        if dm and self._generic_confirm:                  # "I finished my homework": cheer, like a friend
            confirm = self._pick(st, "daily:accomplished", self.bank.daily["accomplished"],
                                 x=re.sub(r"\b(?:my|our)\b", "your", dm.group("x").rstrip(" .!")))
        if self._generic_confirm and confirm in self._plain_confirms() and \
                not re.match(r"^(?:please )?(?:remember|note|keep in mind|don't forget|dont forget|save)\b", msg.strip(), re.I) and \
                not any(f.subject != USER and not f.subject.startswith(USER) for f in fs):
            talk = self._talk(st, text) or self._pick(st, "daily:talk_plain", self.bank.daily["talk_plain"])
            confirm = talk                                # still remembered, but answered like a person
        pm = _HAVE_PET.match(text.strip())
        if pm:                                            # "I have a cat": ask its name, like a person would
            kind = {"puppy": "dog", "kitten": "cat", "bunny": "rabbit"}.get(pm.group(1).lower(), pm.group(1).lower())
            st.uses["pet"] = [kind, st.turn]
            st.uses.pop("pet_name", None)
            new = re.search(r"\b(?:adopted|rescued|just got|bought|new|baby)\b", text, re.I)
            key = "have_pet_new" if new else "have_pet"
            confirm = self._pick(st, f"daily:{key}", self.bank.daily[key], x=pm.group(1).lower())
        ym = re.match(r"^My (\w+) is (\d{1,2} (?:months|weeks)) old\.$", text.strip())
        if ym:                                            # "he's 2 months old": a puppy
            confirm = self._pick(st, "daily:pet_young", self.bank.daily["pet_young"], x=ym.group(2))
        bm = re.match(r"^My (\w+) is an? (.+?)\.$", text.strip())
        pb = st.uses.get("pet_breed")
        if bm and pb and pb[1] == st.turn:                # "he's a golden retriever"
            confirm = self._pick(st, "daily:pet_breed", self.bank.daily["pet_breed"], x=bm.group(2))
        hm = _HAVE_COUNT.match(text.strip())
        if hm and hm.group(2).lower() in _FAMILY_PLURALS:     # "I have two kids": ask their names, like a person
            noun = "children" if hm.group(2).lower() in ("kids", "children") else hm.group(2).lower()
            st.uses["have_noun"] = (noun, st.turn)
            confirm = self._pick(st, "daily:have_many", self.bank.daily["have_many"], x=hm.group(1).lower(),
                                 noun=hm.group(2).lower())
            confirm = confirm[:1].upper() + confirm[1:]
        from engramm.chat.events import find_event
        ev = find_event(text, self._today())
        if ev is not None:
            self.events.note(ev[0], ev[1], sid)
            confirm = self._reply(st, "event_noted", x=ev[0])
        return Reply(msg, "learned", confirm, source={"kind": "user", "source": sid}, via="memory")

    def _plain_confirms(self) -> set[str]:
        """The generic "Got it — I'll remember that." replies (learned.plain / learned.about_you)."""
        r = self.bank.replies.get("learned", {})
        return set(r.get("plain", [])) | set(r.get("about_you", []))

    def _talk(self, st: DialogState, text: str) -> str | None:
        """A statement with nothing to file under a category ("night shifts are killing me", "I'll try
        that", "I just miss him"): answer it the way a person would, not with "I'll remember that"."""
        norm = normalise(text)
        d = self.bank.daily
        le = st.last_exp or {}
        for rx, key in _TALK_RULES:
            if rx.search(norm):
                if key == "talk_tough":
                    st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": text, "turn": st.turn}
                return self._pick(st, f"daily:{key}", d[key])
        if le and st.turn - le.get("turn", -99) <= 2 and not re.search(r"\b(?:you|your)\b", norm):
            key = "exp_follow_neg" if le.get("valence") == "negative" else "exp_follow_pos"
            return self._pick(st, f"daily:{key}", d[key])
        val = _valence(norm)
        if val:
            return self._reply(st, f"react.{val}")
        return None

    def _confirm(self, st: DialogState, fs: list, name_before: str | None) -> str:
        self._generic_confirm = False
        about_you = [f for f in fs if f.subject.startswith(USER)]
        if len(about_you) >= 2 and not any("#name" in f.relation and f.subject == USER for f in about_you):
            lines = list(dict.fromkeys(personal_sentence(f.subject, f.relation, f.object, f.sentence)
                                       for f in sorted(about_you, key=_fact_rank)))
            return self._reply(st, "learned.several") + " " + " ".join(lines[:3])
        out = []
        used = set()
        for f in sorted(fs, key=lambda f: _fact_rank(f)):
            if len(out) == 2:
                break
            if f.subject == USER:
                cat = next((key for lab, key in _CATEGORY_KEYS if lab in f.relation), None)
                if cat == "name":
                    key = "learned.name_changed" if name_before and name_before != f.object else "learned.name_new"
                    out.append(self._reply(st, key, x=f.object))
                elif cat:
                    x = article(f.object) if cat in ("job",) else f.object
                    if cat == "car":
                        x = f.object
                    liked = st.uses.get("last_like")
                    if cat == "fav" and liked and liked[0] == st.turn and liked[1].lower().endswith(f.object.lower()):
                        x = liked[1]                       # "the Beatles", as said
                        x = x[:1].upper() + x[1:]
                    out.append(self._reply(st, f"learned.{cat}", x=x))
                elif f.kind == "NUMBER" and re.fullmatch(r"\d{1,3}", f.object) and 0 < int(f.object) < 120 and \
                        re.search(r"\b(?:i'm|i am|im|age|aged|years? old)\b", f.sentence, re.I):
                    out.append(self._reply(st, "learned.age", x=f.object))
                elif "about_you" not in used:
                    used.add("about_you")
                    self._generic_confirm = True
                    out.append(self._reply(st, "learned.about_you"))
            elif f.subject.startswith(USER + ":"):
                noun = f.subject.partition(":")[2]
                if "#name" in f.relation:
                    many = " and " in f.object or noun in ("children", "kids", "twins") or (
                        noun.endswith("s") and noun not in ("boss",))
                    out.append(self._reply(st, "learned.owned_names" if many else "learned.owned_name",
                                           x=f.object, noun=noun))
                elif f"owned:{noun}" not in used:
                    used.add(f"owned:{noun}")
                    out.append(self._reply(st, "learned.owned", noun=noun))
            elif "world" not in used:
                used.add("world")
                self._generic_confirm = True
                out.append(self._reply(st, "learned.world", subject=f.subject))
        if not out:
            self._generic_confirm = True
            out.append(self._reply(st, "learned.plain"))
        # "Nice to meet you" twice or "Got it — …" twice reads badly: keep distinct sentences only
        return " ".join(dict.fromkeys(out))

    def _memory_list(self, st: DialogState, text: str) -> Reply:
        bot = self.bot
        bot.refresh()
        texts = [(sid, t) for sid, t in bot.user_texts().items() if sid.startswith(CHAT_PREFIX)]
        if not texts:
            return Reply(text, "memory", self._reply(st, "memory.empty"), via="memory")
        mine, other = [], []
        for sid, t in texts:
            fs = [f for f in bot.facts.facts if f.source == sid]
            about_you = [f for f in fs if f.subject.startswith(USER)]
            if about_you:
                for f in sorted(about_you, key=_fact_rank):
                    line = personal_sentence(f.subject, f.relation, f.object, f.sentence)
                    if line not in mine:
                        mine.append(line)
            elif fs or not re.search(r"\b(?:i|my|me|i'm)\b", t.lower()):
                other.append(t.strip())
            else:
                line = to_second_person(t) or f"You said: “{t.strip()}”"
                mine.append(line)
        lines = []
        if mine:
            lines.append(self._reply(st, "memory.intro"))
            lines += [f"• {m}" for m in mine[:20]]
        if other:
            lines.append(self.bank.replies["memory"]["others"])
            lines += [f"• {o}" for o in other[:10]]
        lines.append(self.bank.replies["memory"]["outro"])
        return Reply(text, "memory", "\n".join(lines), via="memory")

    # -- pending questions --------------------------------------------------------------------

    def _fill_pending(self, st: DialogState, pending: dict, msg: str, units: list[Unit]) -> Reply | None:
        """The answer to a question ENGRAMM asked ("What should I call you?" → "Erik")."""
        if len(units) != 1:
            return None
        u = units[0]
        if u.act in ("question", "forget", "tool", "about", "remember", "safety"):
            return None
        if u.act == "intent" and u.intent in ("no",):
            return Reply(msg, "smalltalk", self._pick(st, "intent:no", self.bank.by_id["no"].responses), via="smalltalk")
        if u.act == "intent" and u.intent not in ("yes",):
            return None
        if gibberish(u.text) or is_mash(u.text):
            return None                          # "asdfgh" is no favourite food
        if _REACTION.fullmatch(normalise(u.text).strip(" .!")):
            return None                          # "haha fair" is a reaction, not an answer
        if pending.get("slot") not in ("who_mean", "correction") and \
                re.match(r"^(?:my|i|i'm|im|i am|i've|we)\b", u.text.strip(), re.I) and len(u.text.split()) >= 3:
            return None                          # a whole sentence about you: normal learning reads it right
        slot = pending.get("slot")
        if slot == "who_mean":                   # "Sorry, who's ‘he’?" → "Emmanuel Macron": the question again
            name = msg.strip(" .!?")
            if not name or len(name.split()) > 6 or name.endswith("?"):
                return None
            name = re.sub(r"^(?:i mean|i meant|meant|it's|its|he's|she's|the one called)\s+", "", name, flags=re.I)
            pron = pending.get("pron", "he")
            poss = pron.lower() in ("his", "their", "hers") or (
                pron.lower() == "her" and re.search(r"\bher\s+[a-z]", pending.get("question", ""), re.I))
            q = re.sub(rf"\b{re.escape(pron)}\b", name + ("'s" if poss else ""), pending.get("question", ""),
                       count=1, flags=re.I)
            self._spelled = q
            st.uses.pop("person_gap", None)
            return self._question(st, q)
        value = _slot_value(msg, slot)
        if value is None:
            return None
        if slot in ("home", "origin", "name") and value.islower():
            # "berlin" → "Berlin", "new york" → "New York", "frankfurt am main" keeps "am"
            value = " ".join(w if w in ("am", "an", "der", "de", "la", "le", "of", "on", "upon", "del", "da", "di")
                             else w[:1].upper() + w[1:] for w in value.split())
        if slot == "correction":
            q = pending.get("question") or ""
            value = re.sub(r"^(?:no,? |nope,? |actually,? |well,? )?(?:it's|its|it is|it was|that's|thats|that is|"
                           r"the (?:right |correct )?answer is|the ceo is|he is|she is|they are)\s+", "", value.strip(),
                           flags=re.I).strip(" .!")
            if value.islower() and re.match(r"^\s*(?:who|where|in which (?:city|country|town))\b", q, re.I):
                value = " ".join(w[:1].upper() + w[1:] for w in value.split())
            sent = answer_sentence(q, value, _atype(q)) or f"The answer to “{q}” is {value}."
            r = self._learn(st, [sent], msg)
            r.text = self._reply(st, "correction.ok") + (f" ({sent})" if sent else "")
            return r
        store = pending.get("store")
        if not store:
            return None
        if slot == "name":
            value = " ".join(w[:1].upper() + w[1:] for w in value.split())
        elif slot == "job":
            value = article(value)
        return self._learn(st, [store.format(x=value)], msg)

    def _follow(self, st: DialogState, units: list[Unit], text: str, main: Reply) -> str:
        """A question back, at most one per reply: how an announced event went, or the name, once,
        after a greeting."""
        self._follow_key = None
        if st.pending is not None:
            return ""
        wants = None
        for u in units:
            if u.act == "intent":
                it = self.bank.by_id.get(u.intent)
                if it and it.follow:
                    wants = it.follow
        greeted = any(u.act == "intent" and (u.intent or "").startswith(("greeting", "how_are_you")) for u in units)
        if greeted:
            due = self.events.due(self._today(), set(self.bot.user_texts()))
            if due is not None:
                self.events.mark_asked(due)
                return self._reply(st, "event_followup", x=due.what)
        if wants is None or wants == "ask_mood":
            return ""
        key = wants
        if key in st.asked:
            return ""
        cat = {v: k for k, v in _ASK_FOR_CATEGORY.items()}.get(key)
        if key == "ask_name" and self.user_name():
            return ""
        if cat and cat in self._known_categories():
            return ""
        q = self.bank.fun["questions"].get(key)
        if not q or not q.get("text"):
            return ""
        st.asked.append(key)
        st.pending = {"slot": q["slot"], "store": q["store"], "turn": st.turn}
        self._follow_key = key
        return q["text"]

    # -- small reactions ----------------------------------------------------------------------

    def _feeling(self, st: DialogState, u: Unit) -> str:
        cat_id, neg, valence = u.data["category"], u.data["negated"], u.data["valence"]
        if neg and valence == "positive":
            cat_id = "sad"
        elif neg and valence == "negative":
            return self._pick(st, "feeling:negated", self.bank.negated_negative)
        cat = next(c for c in self.bank.categories if c.id == cat_id)
        return self._pick(st, f"feeling:{cat.id}", cat.responses)

    def _chitchat(self, st: DialogState, u: Unit, parts: list[_Part], alone: bool) -> None:
        # a bare topic ("Photosynthesis", "the Eiffel Tower") gets its article
        words = u.text.strip(" ?!.").split()
        if alone and 1 <= len(words) <= 4 and not re.search(r"\b(?:is|are|was|were|i|you|my)\b", u.text, re.I):
            found = self.about.find(u.text.strip(" ?!."))
            if found:
                parts.append(_Part("main", " ".join(found.sentences)))
                st.last_about = {"title": found.title, "doc": found.doc, "next": found.next_sentence,
                                 "end": found.end_sentence, "source": found.source}
                self.bot.context.update({"answer": None, "atype": None, "mention": found.title})
                return
        # a mood word about something else ("the weather is terrible"): a short reaction
        if not alone:
            return
        # a short phrase right after a moment ("a bit stressful" → "work stuff"): it continues that topic
        le = st.last_exp
        if le and st.turn - le.get("turn", -99) <= 2 and _AGREE.fullmatch(u.norm):
            # "yeah exactly" after ENGRAMM's question about the moment: stay with it, don't echo it
            key = "exp_agree_neg" if le.get("valence") == "negative" else "exp_agree_pos"
            parts.append(_Part("main", self._pick(st, f"daily:{key}", self.bank.daily[key])))
            return
        if le and st.turn - le.get("turn", -99) <= 2 and len(words) <= 5 and \
                not re.search(r"\b(?:you|your)\b", u.text, re.I):
            key = "exp_more_neg" if le.get("valence") == "negative" else "exp_more_pos"
            parts.append(_Part("main", self._pick(st, f"daily:{key}", self.bank.daily[key],
                                                  x=u.text.strip(" .!").lower())))
            return
        le_ = st.last_exp or {}
        talk = self._talk(st, u.text) if _TALK_FIRST.search(u.norm) or (
            le_ and st.turn - le_.get("turn", -99) <= 2 and len(words) > 5) else None
        if talk:
            parts.append(_Part("main", talk))
            return
        fe = self.bank.feeling(u.norm)
        val = fe[0].valence if fe and fe[0].valence in ("positive", "negative") else _valence(u.norm)
        if val:
            parts.append(_Part("main", self._reply(st, f"react.{val}")))
            return
        if alone:
            parts.append(_Part("main", self._reply(st, "chitchat")))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_STOP_CHAT = frozenset("the and but not just really very so too also that this there then than what with have has had "
                       "was were are is be been being for from into about some any all okay yeah yes no lol haha "
                       "i'm i've me my mine we our us".split())


_ELLIPSIS = re.compile(r"^(?:and|what about|how about)(?: (?:of|for|in|with))? (?P<x>(?:the )?[A-Z][\w'\- ]{1,40}?)\s*\??$",
                       re.I)
_QUESTION_WORDS = {"what", "who", "where", "when", "why", "how", "which", "whose", "is", "are", "does", "did", "can",
                   "was", "were"}


def _fill(text: str, **fmt) -> str:
    def rep(m):
        v = fmt.get(m.group(1))
        return m.group(0) if v is None else str(v)
    out = re.sub(r"\{(\w+)\}", rep, text)
    out = re.sub(r"[ ]{2,}", " ", out)
    return out[:1].upper() + out[1:] if out[:1].islower() else out


_CLAUSE_PRON = re.compile(r"(?:,\s*(?:and\s+)?|\s+and\s+|(?<=[.!;])\s+)(he|she|they|it)\s+(?=[a-z])", re.I)
_OWNER = re.compile(r"\b(?:my|our)\s+((?:little |big |older |younger |best |step)?[a-z]+)\b|"
                    r"\bi have (?:a|an|one|two|three) ((?:little |big |older |younger )?[a-z]+)", re.I)


def resolve_statement(text: str) -> str:
    """"My brother is called Tom and he lives in Munich." → "My brother is called Tom. My brother
    lives in Munich." — a clause that starts with he/she/they/it after a clause about "my X"
    becomes a sentence about "my X", so the fact memory files both facts under your brother."""
    m = _OWNER.search(text)
    if not m:
        return text
    noun = (m.group(1) or m.group(2)).strip()
    if noun in ("name", "names", "favourite", "favorite", "own", "life", "job", "home"):
        return text
    pieces = _CLAUSE_PRON.split(text)          # [clause0, pronoun1, clause1, pronoun2, clause2, …]
    if len(pieces) < 3 or len(pieces[0]) < m.end() - 1:
        return text
    sents = [pieces[0].strip().rstrip(",").strip()]
    for k in range(1, len(pieces), 2):
        sents.append(f"My {noun} {pieces[k + 1].strip()}")
    out = []
    for sent in sents:
        sent = sent.strip()
        if sent and not sent.endswith((".", "!", "?")):
            sent += "."
        out.append(sent[:1].upper() + sent[1:])
    return " ".join(x for x in out if x)


_CAPS_SPAN = re.compile(r"\b[A-Z][\w'’.\-]*(?:\s+(?:of|the|and|de|von|van|da|del|la|le)?\s*[A-Z][\w'’.\-]*)*")


def _norm_value(v: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", v.lower()).strip()


def _same_value(a: str, b: str) -> bool:
    x, y = _norm_value(a), _norm_value(b)
    return bool(x) and bool(y) and (x == y or f" {x} " in f" {y} " or f" {y} " in f" {x} ")


def _agreeing_sources(answer: str | None, rows: list, src: dict) -> list[str]:
    """Other independent sources (another article, feed or site) whose fetched sentences hold the
    same answer — "(from Wikipedia …; also BBC News)"."""
    if not answer or len(_norm_value(answer)) < 3:
        return []
    out = []
    for row in rows:
        t, rs = row[0], row[1]
        if rs.get("key") == src.get("key") or not _same_value(answer, t) and _norm_value(answer) not in _norm_value(t):
            continue
        name = rs.get("title") if rs.get("kind") == "shelf" else rs.get("source") or rs.get("title")
        label = f"Wikipedia's “{name}”" if rs.get("kind") == "shelf" else str(name)
        if name and label not in out and (rs.get("kind") != src.get("kind") or rs.get("key") != src.get("key")):
            out.append(label)
    return out


_BOT_EXPERIENCE = re.compile(r"^(?:but |so |and |lol |haha )?(?:have|did|do) (?:you|u) (?:ever |even |actually )?"
                             r"(?P<v>seen|watched|watch|read|heard|been to|been|tried|played|eaten|eat|visited|met|"
                             r"listened to|see|hear|play|taste|tasted|smell)\b(?P<rest>.*)$")
_VERB_BASE = {"seen": "see", "watched": "watch", "read": "read", "heard": "hear", "been to": "go anywhere",
              "been": "go anywhere", "tried": "try", "played": "play", "eaten": "eat", "visited": "visit",
              "met": "meet", "listened to": "listen to", "tasted": "taste"}
_BOT_LIMIT = re.compile(r"^(?:lol |haha |but |well |oh )?(?:you|u) (?:can't|cant|cannot|can not|don't|dont|do not|"
                        r"aren't|are not|have no|got no|wouldn't|won't) (?:even |really |actually )?"
                        r"(?:watch|see|eat|taste|hear|listen|feel|sleep|go|travel|read|play|smell|have|know what it's like|"
                        r"understand|be|leave)\b.*$|^(?:lol |haha )?(?:you're|youre|you are) (?:just |only )?(?:a |an )?"
                        r"(?:bot|program|computer|machine|robot|ai)\b.*$")
_RECAP = re.compile(r"^(?:can you )?(?:remind me |tell me )?(?:what|which things?) (?:did |have )?(?:we|we've) "
                    r"(?:talk(?:ed)? about|discuss(?:ed)?|cover(?:ed)?)(?: so far| today| before| earlier)?$|"
                    r"^what were we (?:talking about|saying)$|^(?:summarize|sum up|recap)(?: our| the)? (?:conversation|chat)$")
_WHERE_WERE_WE = re.compile(r"^(?:ok |okay |so |anyway )?(?:where were we|where did we (?:leave off|stop)|what was i saying|"
                            r"what were we just talking about|back to (?:what we were talking about|the topic))$")
_JOKE_BAD = re.compile(r"^(?:haha |lol |ha |ugh |oh no |omg )*(?:that's|thats|that was|that one was|it's|its|"
                       r"so|that joke was|wow that's)? ?(?:so |really |pretty |kinda |very )?(?:bad|terrible|awful|lame|"
                       r"cringe|cringy|corny|not funny|unfunny|dumb|stupid|the worst)(?: joke)?[!. ]*(?:lol|haha)?$")
_JOKE_GOOD = re.compile(r"^(?:ok |okay |haha |lol |ha )*(?:that's|thats|that was|that one was|this one was)? ?"
                        r"(?:actually |really |pretty |so )?(?:good|funny|great|hilarious|nice)(?: one)?[!. ]*$")
_REFINE = re.compile(r"^(?:maybe |how about |what about |ideally |preferably |do you have )?(?:something|anything|one|ideas?|"
                     r"a dish|a recipe|a meal|recipes)? ?(?:with|using|that has|containing|made with) (?P<x>[a-z ]{3,25})$")
_NUMBERISH = re.compile(r"^(?:\d|(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                        r"twenty|thirty|forty|fifty|hundred|thousand|million|several|many|few)\b)", re.I)
_HOW_Q = re.compile(r"^\s*how (?:do|does|did|can|could|should|would|to|is|are|was|were) (?!.*\b(?:old|many|much|far|"
                    r"long|tall|high|big|large|deep|wide|heavy|fast|often)\b)", re.I)
_ROLE_Q = re.compile(r"^\s*who(?:'s| is| was| are| were)\s+(?:the\s+)?(?P<role>(?:current |new |present |former |first )?"
                     r"[a-z][a-z -]{1,40}?) (?:of|at|for) (?P<x>.+?)\s*\??$", re.I)
_ROLE_NOUNS = frozenset("""ceo president king queen minister chancellor mayor founder owner leader coach manager captain
head director chairman chairwoman chair governor secretary pope emperor empress author writer singer drummer guitarist
wife husband boss pm premier prince princess editor principal dean commander general chief officer""".split())
_ROLE_SYN = {"ceo": ["ceo", "chief executive"], "chief executive": ["ceo", "chief executive"],
             "pm": ["prime minister"], "prime minister": ["prime minister", "premier"],
             "head": ["head", "leader", "chief"], "boss": ["ceo", "chief executive", "head", "boss"],
             "founder": ["found", "co-found", "established", "created"], "owner": ["own", "owner", "bought", "acquired"],
             "leader": ["leader", "led", "head"], "coach": ["coach", "manager", "head coach"],
             "manager": ["manager", "coach"], "chancellor": ["chancellor"], "mayor": ["mayor"],
             "president": ["president"], "king": ["king"], "queen": ["queen"], "captain": ["captain"]}
_TITLE_WORDS = re.compile(r"\b(?:general|minister|secretary|attorney|assistant|officer|council|department|ministry|"
                          r"committee|board|director|commission|agency|office|government|administration|parliament|"
                          r"party|company|corporation|division|bureau|court|forces|army)\b", re.I)
_SUPERLATIVE_Q = re.compile(r"^\s*(?:what|which|who)(?:'s| is| was| are| were)\s+(?:the\s+)?"
                            r"(?P<sup>\w+est|most \w+|least \w+|biggest)\s+(?P<noun>[a-z]+(?: (?!in\b|of\b|on\b|ever\b|by\b)[a-z]+)?)"
                            r"(?P<rest>.*?)\s*\??\s*$", re.I)
_SUP_FREE = re.compile(r"^(?:\s*\(?|,)?\s*(?:in the world|on earth|ever|of all time|in the solar system|in history|"
                       r"known|recorded|\)|,|\.|;|$)", re.I)


def _place_case(text: str) -> str:
    """"italy" → "Italy", "new york" → "New York", "the beatles" → "the Beatles"."""
    small = {"the", "of", "and", "de", "la", "del", "von", "van", "upon", "on"}
    out = [w if (i > 0 and w in small) or (i == 0 and w == "the") else w[:1].upper() + w[1:]
           for i, w in enumerate(text.split())]
    return " ".join(out)


_NAME_RX = r"(?:the )?[A-Z][\w'’.-]+(?: (?:of |de |van |von |and )?[A-Z][\w'’.-]+){0,3}"
_NOT_MAIN = r"(?!(?:repechage|qualif\w*|group|play-?offs?|pool|preliminary|regional|junior|youth|opening|toss|bid|"
_NOT_MAIN += r"right|vote|first|second|third|match|game|semi-?finals?|quarter-?finals?)\b)"
# (pattern, weight): the final and the title count most, a plain "won the tournament" less
_WINNER_PATTERNS = [
    (rf"(?P<w>{_NAME_RX}) (?:were|was|are|is) crowned (?:the )?(?:\w+ )?(?:champions?|winners?)", 3),
    (rf"(?i:in the final|in the championship match|in the title match),? (?P<w>{_NAME_RX}) (?:defeated|beat|overcame)", 3),
    (rf"(?P<w>{_NAME_RX}) won .{{0,40}}?,? (?:claiming|securing|winning|taking|earning) (?:their|its|his|her) "
     rf"(?:\w+ )?(?i:world cup|world title|title|championship|crown|cup)\b", 3),
    (rf"(?P<w>{_NAME_RX}) went on to win the (?:\w+ )?(?i:tournament|title|cup|championship|final|competition)\b", 3),
    (rf"(?P<w>{_NAME_RX}) won the (?:overall |general )(?:classification|title|standings)\b", 3),
    (rf"(?P<w>{_NAME_RX}) (?:defeated|beat|overcame) .{{3,70}}? in the final", 3),
    (rf"(?P<w>{_NAME_RX}) (?:retained|defended|claimed|clinched|secured|won) (?:the|their|its|his|her) "
     rf"(?:\w+ )?(?:title|crown|championship)\b", 3),
    (rf"(?P<w>{_NAME_RX}) won the final\b", 3),
    (rf"(?i:the final|the title|the tournament|the race|the championship|the cup|the competition|the edition) "
     rf"(?:is|was) won by (?P<w>{_NAME_RX})", 2),
    (rf"(?P<w>{_NAME_RX}) won (?:the|their|its|his|her) {_NOT_MAIN}(?:\w+ )?(?i:tournament|cup|competition|race|"
     rf"event|gold medal|trophy)\b", 2),
    (rf"(?P<w>{_NAME_RX}) (?:became|were|was) (?:the )?(?:\w+ )?(?:champions?|winners?) (?:for the|after|by)", 2),
]
_WINNER_RX = re.compile("|".join(f"(?:{p})".replace("(?P<w>", f"(?P<w{i}>") for i, (p, _) in enumerate(_WINNER_PATTERNS)))
_WINNER_W = [w for _, w in _WINNER_PATTERNS]
_WINNER_Q = re.compile(r"^\s*who (?:won|wins|win|was the winner of|is the winner of|were the winners of|"
                       r"became champions? (?:of|at))\b", re.I)


def _winner_from(rows, topic: str | None):
    """"Who won the 2022 World Cup?": the name that the topic's own sentences say won — "Argentina were
    crowned the champions", "Argentina won the final" — counted; (name, best sentence, source) or None."""
    if not topic:
        return None
    votes: Counter = Counter()
    first: dict = {}
    tyears = set(re.findall(r"\b(?:1[5-9]|20)\d\d\b", topic))
    for row in rows:
        text, src = row[0], row[1]
        if not _on_topic(topic, src, text):
            continue
        for m in _WINNER_RX.finditer(text):
            near = set(re.findall(r"\b(?:1[5-9]|20)\d\d\b", text[max(0, m.start() - 40):m.end() + 40]))
            if tyears and near and not near & tyears:
                continue                              # "West Germany won the 1990 final": another edition
            i, w = next((k, g) for k, g in enumerate(m.groups()) if g)
            w = re.sub(r"^(?:the|In|After|Then|However|Finally) ", "", w)
            if w.lower() in {"it", "he", "she", "they", "this", "the", "who", "in"} or w.lower() in topic.lower():
                continue
            votes[w] += _WINNER_W[i]
            if _WINNER_W[i] >= 3 or w not in first:
                first[w] = (text, src)
    if not votes:
        return None
    (best, n), *rest = votes.most_common(2) + [(None, 0)]
    if (rest and rest[0][1] == n) or n < 2:
        return None                                   # two different "winners", or one weak hint: no answer
    return best, first[best][0], first[best][1]


def _src_title(src: dict | None) -> str:
    src = src or {}
    return re.sub(r"\s*\((?:infobox|[^)]*)\)$", "", str(src.get("title") or src.get("key") or ""))


def _on_topic(topic: str | None, src: dict, evidence: str | None) -> bool:
    """A question that names an article is answered from that article or a sentence that names it."""
    if not topic:
        return True
    bare = re.sub(r"\s*\([^)]*\)$", "", topic).lower()
    title = re.sub(r"\s*\([^)]*\)$", "", str(src.get("title") or src.get("key") or "")).lower()
    return title == bare or bare in (evidence or "").lower()


_COVER_STOP = frozenset("""who whom whose what which when where why how is are was were be been do does did done has have
had the a an of in on at to for from by with and or but about as it its this that these those there here than then
current currently today now ever most many much very really also just name named called please tell me
you your i my mine we our they their he she him his her""".split())
_COVER_ALT = {"die": ("died", "death", "dead"), "died": ("die", "death", "dead"), "born": ("birth", "née"),
              "paint": ("painted", "painting", "painter"), "painted": ("painting", "painter"),
              "direct": ("directed", "director"), "directed": ("director", "directing"),
              "write": ("wrote", "written", "writer", "author"), "wrote": ("written", "writer", "author", "novel"),
              "invent": ("invented", "inventor", "invention"), "invented": ("inventor", "invention", "developed"),
              "found": ("founded", "founder", "established"), "founded": ("founder", "established", "co-founded"),
              "discover": ("discovered", "discovery"), "discovered": ("discovery", "discoverer"),
              "build": ("built", "constructed"), "built": ("constructed", "completed", "opened"),
              "won": ("win", "winner", "champions", "crowned", "title"), "win": ("won", "winner", "champions"),
              "sing": ("sang", "sung", "singer", "recorded", "performed"), "sang": ("sung", "singer", "recorded"),
              "compose": ("composed", "composer"), "composed": ("composer",), "launch": ("launched",),
              "ceo": ("chief executive",), "biggest": ("largest",), "largest": ("biggest",), "tallest": ("highest",),
              "highest": ("tallest",)}


_COVER_VERBS = frozenset("die died paint painted direct directed write wrote invent invented found founded discover "
                         "discovered build built won win sing sang compose composed launch launched".split())
_BY_VERBS = frozenset("wrote written write painted paint directed direct composed compose sang sing designed design "
                      "invented invent founded found built build created create".split())


def _covers(q: str, evidence: str, answer: str = "", title: str = "", before: str = "") -> bool:
    """The evidence names what the question asks about: its content words (a stem of five letters
    or a usual other form: "died" for "die", "director" for "directed"); one may be missing when
    the question has four or more."""
    # the article's subject (its title) and the sentence before ("He was born …") name who is meant;
    # the asked verb must be in the sentence itself
    ev = (evidence + " " + title + " " + before).lower()
    own = evidence.lower()
    words = [w for w in re.findall(r"[a-z0-9][a-z0-9'-]*", q.lower()) if w not in _COVER_STOP and len(w) > 1]
    if not words:
        return True
    ans = answer.lower()
    missing = 0
    for w in words:
        if w in ans:
            continue
        forms = (w,) + _COVER_ALT.get(w, ())
        if w in _BY_VERBS and ans and any(
                not pre.endswith("ed") or any(pre.startswith(f[:5]) for f in forms)
                for pre in re.findall(r"(\S+) by " + re.escape(ans), own)):
            continue                                  # "a tragedy by William Shakespeare", not "hosted by DJ Dorothy"
        if w in ("born", "died", "die", "death") and _LIFE_SPAN_RE.search(evidence):
            continue                                  # "(February 8, 1899 – June 16, 1970)"
        if w in _COVER_VERBS:
            if not any((f[:5] if len(f) > 5 else f) in own for f in forms):
                return False                          # the question's verb ("die", "painted") must be in the sentence
            continue
        if not any((f[:5] if len(f) > 5 else f) in ev for f in forms):
            missing += 1
    return missing == 0 or (len(words) >= 3 and missing == 1)


def _implausible(q: str, answer: str | None, evidence: str | None, title: str = "", before: str = "") -> bool:
    """A looked-up short answer that cannot be meant: a count for "who …?" ("two goals was the top
    scorer"), or a superlative the evidence does not say about it — the biggest *commercial success*
    is no planet, and the tallest mountain *outside Asia* is not the tallest mountain."""
    if not answer or not evidence:
        return False
    if re.match(r"^\s*who\b", q, re.I) and _NUMBERISH.match(answer):
        return True
    if not _covers(q, evidence, answer, title, before):
        return True                                   # "who painted the starry night?" ← a sentence without "painted"
    if _HOW_Q.match(q) and len(answer.split()) <= 3:
        return True                                   # "how do people deal with grief?" — "conspecifics" is no answer
    m = _ROLE_Q.match(q)
    if m:
        # "who is the CEO of Apple?": the evidence must name the role, and the answer is a person, not a title
        role = re.sub(r"^(?:current|new|present|former|first)\s+", "", m.group("role").lower().strip())
        syn = _ROLE_SYN.get(role, [role])
        if role.split()[-1] not in _ROLE_NOUNS:
            syn = None                                # "the biggest selling female group of all time": no role
        if syn and (not any(x in evidence.lower() for x in syn) or _TITLE_WORDS.search(answer)):
            return True
        if syn and re.match(r"^\s*who(?:'s| is| are)\b", q, re.I) and re.search(
                r"\b(?:former|late|then|ex-|named (?:after|for)|in honou?r of|was (?:the )?(?:" + "|".join(syn) + r"))\b",
                evidence, re.I):
            return True                               # "named after President Pompidou" is no current president
    # an award, prize or title is no person ("Golden Ball was the top scorer")
    if re.match(r"^\s*who\b", q, re.I) and re.search(r"\b(?:ball|boot|award|prize|trophy|medal|cup|title|glove|shoe)$",
                                                     answer, re.I):
        return True
    m = _SUPERLATIVE_Q.match(q)
    if not m or re.sub(r"^\s*(?:in the world|on earth|ever|of all time|in history|in the universe)\s*", "",
                       m.group("rest")).strip():
        return False
    ev = evidence.lower()
    sup, noun = m.group("sup").lower(), m.group("noun").lower().split()[0].rstrip("s")
    a = ev.find(answer.lower())
    for hit in re.finditer(re.escape(sup), ev):
        if re.search(r"(?:\b\d+(?:st|nd|rd|th)|\b(?:second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
                     r"eleventh|twelfth|\w+teenth|twentieth)|one of the|among the)[\s-]*$", ev[:hit.start()]):
            continue                                  # "the 14th tallest building" is not the tallest
        after = ev[hit.end():]
        nm = re.match(r"(?:\s+[a-z-]+){0,2}?\s+(" + re.escape(noun) + r"s?)\b", after)
        if nm:
            # "the tallest mountain outside Asia" restricts what the question does not
            return not _SUP_FREE.match(after[nm.end():])
        if a >= 0 and abs(hit.start() - a) <= len(answer) + 12:
            return not _SUP_FREE.match(after)     # "Pacific (the largest), Atlantic …"
    return True


_DISLIKE = re.compile(r"^(?:honestly,? |tbh,? |to be honest,? |well,? )?i (?:really |just |honestly )?"
                      r"(?:(?:don'?t|do not|never|can'?t|cannot) (?:really |much |even |particularly )?"
                      r"(?:like|love|enjoy|stand|care for)|hate|dislike|detest|can'?t stand) "
                      r"(?P<x>(?!it\b|that\b|this\b|when\b|how\b|my\b|you\b|people\b|being\b|having\b)"
                      r"[a-z][a-z' -]{1,40}?)(?: (?:much|at all|very much|that much|anymore|tbh|honestly))?[.!]*$", re.I)
_LIKES_Q = re.compile(r"^(?:so |and )?what (?:do|did) i (?P<neg>not |n't |never )?(?P<v>like|love|enjoy|hate|dislike)"
                      r"(?: again)?\s*\??$|^what (?:don'?t|do not|didn'?t) i (?P<v2>like|love|enjoy)\s*\??$", re.I)
_DAY_NOUN = re.compile(r"^(?:(?:just |such |what |had |i had |it's been |it was |been )?(?:a |an )?)?(?:really |very |so |super )?"
                       r"(?:long|rough|tough|hard|busy|crazy|stressful|exhausting|bad|terrible|awful|hectic|draining) "
                       r"(?:day|week|night|shift|month|morning)(?: honestly| tbh| lol)?[.!]*$")
_DAY_WAS = re.compile(r"^(?:ugh |man |well |honestly |omg )?(?P<what>work|school|class|uni|college|today|the day|my day|"
                      r"it|my shift|the shift|practice|training|the meeting|my exam|the exam) (?:was|has been|is being) "
                      r"(?:so |really |super |pretty |very |kinda |quite |such )?(?:(?P<bad>long|exhausting|tiring|rough|hard|"
                      r"stressful|a lot|busy|crazy|awful|terrible|horrible|bad|boring|draining|brutal|hectic|a nightmare|"
                      r"the worst|annoying|frustrating)|(?P<good>good|great|fun|nice|amazing|awesome|fine|okay|productive|"
                      r"chill|relaxing|easy|the best))(?: (?:today|honestly|tbh|lol))?[.!]*$")
_WORKOUT_DONE = re.compile(r"^(?:so |well |today |yesterday |earlier )?i (?:just |finally |also )?(?:went to the gym|hit the gym|"
                           r"worked out|did a workout|went for a (?:run|jog|swim|walk|bike ride|ride|hike)|went (?:running|jogging|"
                           r"swimming|hiking|cycling|biking|climbing|bouldering)|did (?:yoga|pilates|crossfit|cardio|leg day|"
                           r"some exercise|a hiit class|hiit)|ran (?:\d+|a|five|ten) ?(?:k|km|miles?|kilometers?|kilometres?)|"
                           r"played (?:football|soccer|tennis|basketball|squash|badminton|volleyball|golf|padel)|"
                           r"had (?:football|soccer|tennis|basketball) practice|lifted(?: weights)?)"
                           r"(?: today| this morning| tonight| earlier| yesterday| after work)?[.!]*$")
_HOW_IT_WENT = re.compile(r"^(?:it was |it's been |was |that was |honestly |pretty |really |so |super |kinda )*(?:(?P<hard>hard|tough|"
                          r"brutal|exhausting|tiring|intense|killer|a struggle|rough|difficult)|(?P<good>good|great|amazing|fun|"
                          r"awesome|nice|easy|fine|solid)|(?P<meh>ok|okay|alright|meh|so-so))(?: (?:honestly|tbh|lol|actually))?[.!]*$")
_DAY_MEH = re.compile(r"^(?:mine|my day|it|today|the day)(?: was| has been|'s been| is) (?:ok|okay|alright|fine|meh|so-so|"
                      r"not bad|average|nothing special)(?: i guess| i suppose| honestly| tbh)?"
                      r"(?:,? (?:a bit|kinda|kind of|a little|pretty|bit) (?:boring|slow|long|dull|quiet|uneventful))?[.!]*$")
_GOAL = re.compile(r"^(?:i (?:really |kinda |kind of )?(?:want|would like|wanna|need|plan|am planning|'m planning|am trying|"
                   r"'m trying|hope|am going|'m going|gotta)(?: to)?|my goal is to) (?P<goal>(?:get|be|become|lose|build|run|"
                   r"learn|start|stop|quit|save|eat|sleep|read|exercise|work out|drink|cut down)\b.{2,50}?)[.!]*$")
_GOAL_TOPICS = [("fitness", re.compile(r"\b(?:fit|fitter|in shape|stronger|muscle|weight|marathon|run|running|exercise|"
                                       r"work out|athletic|abs|healthier)\b")),
                ("learning", re.compile(r"^learn\b")),
                ("money", re.compile(r"\b(?:save|saving)\b.*\bmoney\b|\bsave up\b|\bbudget\b")),
                ("sleep", re.compile(r"\bsleep\b")),
                ("habit", re.compile(r"^(?:quit|stop|cut down)\b"))]
_TIPS = re.compile(r"^(?:so |ok |okay )?(?:any |some |got any |do you have (?:any )?)?(?:tips|advice|suggestions|ideas|pointers)"
                   r"(?: for me| on that| for that)?\??$|^(?:how|where) (?:do|should) i (?:start|begin)\??$|^how\??$")
_DIET = re.compile(r"^(?:btw |by the way |oh |also )?i(?:'m| am) (?:a |actually |also |now )?(?P<diet>vegetarian|vegan|"
                   r"pescatarian|gluten[- ]free|lactose intolerant|on a diet)(?: now| btw| actually)?[.!]*$")
_POST_WORKOUT = re.compile(r"^what (?:should|can|could|do) i (?:eat|have)(?: after| post| before)(?: a| my| the)? "
                           r"(?:workout|work out|gym|training|run|exercise|session)\??$|^(?:good |any )?post[- ]workout "
                           r"(?:food|meal|snack)s?\??$")
_WHICH_ONE = re.compile(r"^(?:and |so |ok )?which (?:one |of them |of the two |of those )?(?:is|was|has) (?:the )?"
                        r"(?P<w>bigger|larger|smaller|older|younger|taller|higher|longer|shorter|more populous)\??$")
_CALC_MORE = re.compile(r"^(?:and |then |now |ok )?(?P<op>times|x|\*|multiplied by|plus|\+|minus|-|divided by|/|over|"
                        r"to the power of)\s*(?P<n>-?\d+(?:[.,]\d+)?)\??$")
_CALC_OPS = {"times": "*", "x": "*", "*": "*", "multiplied by": "*", "plus": "+", "+": "+", "minus": "-", "-": "-",
             "divided by": "/", "/": "/", "over": "/", "to the power of": "^"}
_HOMEWORK = re.compile(r"^(?:can|could|would|will) you (?:please )?help me(?: out)?(?: with)? (?:my |some |this |an? )?"
                       r"(?:homework|assignment|essay|studies|studying|exam|test|project|school ?work|revision|math|maths|"
                       r"physics|chemistry|biology|history|english|geography|coursework)(?: please)?$|"
                       r"^i need help with (?:my )?(?:homework|assignment|essay|exam|test|studies)$")
_SUBJECT = re.compile(r"^(?:it's|its|it is|it's about|in|for)?\s*(?P<s>math|maths|mathematics|algebra|geometry|calculus|physics|"
                      r"chemistry|biology|history|geography|english|literature|french|spanish|german|latin|economics|"
                      r"computer science|programming|coding|philosophy|art|music)(?: homework| class| stuff)?$")
_SUBJECT_KINDS = [("math", re.compile(r"math|maths|mathematics|algebra|geometry|calculus")),
                  ("science", re.compile(r"physics|chemistry|biology|computer science|programming|coding")),
                  ("language", re.compile(r"english|literature|french|spanish|german|latin")),
                  ("other", re.compile(r".+"))]
_LOSS = re.compile(r"\b(?:died|dead|passed away|passed on|lost (?:my|our)|put down|put to sleep|funeral|"
                   r"is gone|has gone)\b", re.I)
_GRIEF_NAME = re.compile(r"^(?P<p>his|her|their|its) name (?:was|is) (?P<x>[a-z][a-z' -]{1,25})[.!]*$")
_GRIEF_AGE = re.compile(r"^(?:he|she|they|it) (?:was|were) (?:only |almost |nearly |just )?(?P<n>\d{1,3})"
                        r"(?: years old| years| yrs)?[.!]*$")
_PRON = {"his": "he", "her": "she", "their": "they", "its": "it"}
_FOLLOW_STATEMENT = re.compile(r"^(?:it's|its|it is|it was|this is|that was|that's|thats|the one|i start|i begin|"
                               r"i'm the|i am the|i have to|i need to|i was|i've been|second|third|first|again|"
                               r"for the (?:second|third)|and (?:it|that|then))\b")
_FEELING_WORD = re.compile(r"\b(?:nervous|anxious|sad|happy|scared|worried|excited|angry|stressed|tired|upset|lonely|"
                           r"depressed|afraid|frustrated|glad|thrilled|devastated|heartbroken)\b")
_CATEGORY_LABELS = frozenset(("#name", "#home", "#job", "#employer", "#birth", "#origin", "#food", "#colour", "#car"))
_HONOUR = re.compile(r"^(?:and |so |guess what,? )?i(?:'m| am| was| got asked to be| was asked to be) (?:the |a |his |her )?"
                     r"(?:best man|maid of honou?r|bridesmaid|groomsman|godfather|godmother|witness)[.!]*$")
_WEDDING = re.compile(r"\b(?:best man|maid of honou?r|wedding|bride|groom|married|marry|engaged)\b")
_SPEECH = re.compile(r"\b(?:speech|toast|eulogy|presentation|talk at)\b")
_HELP_ME = re.compile(r"^(?:can|could|would|will) you help(?: me)?(?: with (?:it|that|this))?(?: please)?$|"
                      r"^help me(?: please)?$|^any (?:ideas|tips|advice)$|^where do i (?:even )?start$")
_SPEECH_HELP = re.compile(r"^(?:can you |could you |please )?help me (?:write|with|prepare|plan) (?:a |my |the )?"
                          r"(?:best man |maid of honou?r |wedding |birthday |retirement )?(?:speech|toast)(?: please)?$")
_JOB_CHANGE = re.compile(r"^(?:so |well |guess what,? |btw )?i (?:just |finally |recently )?(?:(?P<quit>quit|left|resigned from|"
                         r"handed in my notice at|retired from)(?: my)? (?:job|work|position|company)|retired|"
                         r"(?P<bad>got fired|was fired|got laid off|was laid off|lost my job|got let go|was let go))"
                         r"(?: today| yesterday| last week| this week)?[.!]*$")
_TRIP = re.compile(r"^(?:so |well |guess what,? )?(?:i|we|me and my \w+|my \w+ and i) (?:just |finally |recently |also )?"
                   r"(?:got back from|came back from|returned from|went to|were in|was in|visited|travel+ed to|flew to|"
                   r"went on|spent (?:a|the|two|three|four|five|\w+) (?:week|weekend|days?|weeks?) in) "
                   r"(?P<x>[a-z][a-z' -]{1,40}?)(?: (?:last|this) (?:week|month|year|weekend|summer|winter|spring|autumn)|"
                   r" yesterday| recently| for (?:a|two|three|\w+) (?:week|weeks|days))?[.!]*$")
_TRIP_WORD = re.compile(r"(?:a |my |our |the )?(?:vacation|holiday|holidays|trip|break|weekend away|travels?|honeymoon|"
                        r"road trip|city trip|business trip|backpacking trip)")
_NOT_A_TRIP = re.compile(r"(?:the |a |my |our )?(?:gym|cinema|movies|store|shop|supermarket|work|office|school|class|bed|"
                         r"doctor|dentist|hospital|party|concert|restaurant|bar|pub|club|church|mall|bank|park|beach|"
                         r"pool|library|game|match|meeting|wedding|funeral|game night)")
_HOBBY = re.compile(r"^i (?:also |really |still |sometimes )?(?P<v>play|practi[sc]e|collect|do) (?:the |some )?"
                    r"(?P<x>(?!it\b|that\b|this\b|my\b|not\b|nothing\b|what\b|well\b|too\b)[a-z][a-z -]{1,25}?)"
                    r"(?: a lot| sometimes| every day| on weekends| in my free time| for fun| as a hobby)?[.!]*$")
_HOBBY_BARE = re.compile(r"^i (?:also |really |love to |like to )?(?P<v>paint|draw|knit|sing|dance|bake|surf|skate|climb|box|"
                         r"swim|crochet|sew|garden|journal)(?: a lot| for fun| sometimes| as a hobby| in my free time)?[.!]*$")
_GERUND = {"paint": "painting", "draw": "drawing", "knit": "knitting", "sing": "singing", "dance": "dancing",
           "bake": "baking", "surf": "surfing", "skate": "skating", "climb": "climbing", "box": "boxing",
           "swim": "swimming", "crochet": "crochet", "sew": "sewing", "garden": "gardening", "journal": "journaling"}
_DURATION_ANS = re.compile(r"^(?:for |since )?(?:about |around |almost |nearly |over |like |roughly |maybe |just )?"
                           r"(?P<n>\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|"
                           r"a few|a couple of|a couple|several|many) (?P<u>years?|months?|weeks?|days?)(?: now| or so| already)?[.!]*$")
_REC_SEEN = re.compile(r"^(?:oh |hmm |ah )?(?:i(?:'ve| have)? )?(?:already )?(?:read|seen|watched|tried|heard|played|been to|"
                       r"visited|done|know)(?: of| about)? (?:that|it|those|them|all of (?:them|those)|these|all of these)"
                       r"(?: one| ones)?(?: already)?[.!]*$")
_REC_GENRE = re.compile(r"^(?:maybe |preferably |ideally |hmm |ok |okay |more like )?(?:something|somewhere|anything|one|ones|"
                        r"a|an|more|some)?\s*(?:about |on |with |in |for |related to |more about )?(?:the |a )?(?:a bit |more |really |kinda |pretty )?(?P<g>[a-z-]+)"
                        r"(?: one| ones| please| maybe| instead| stuff| place| places| book| books| movie| movies| players?| people)?\??$")
_I_LIKE = re.compile(r"^i (?:really |absolutely |just )?(?:love|like|adore|am into|'m into|am a big fan of|'m a big fan of) "
                     r"(?P<x>[a-z][a-z' .-]{1,40})$")
_BEST_OF = re.compile(r"^(?:so |and )?what(?:'s| is| are|s) (?P<who>their|his|her|its|the) (?:best|greatest|most famous|top|"
                      r"most popular) (?:song|songs|album|albums|movie|movies|film|films|book|books|novel|work|track|"
                      r"tracks|show|episode|game|dish)\??$")
_PET_PEEVE = re.compile(r"^i (?:really |just )?(?:don'?t like|do not like|hate|can'?t stand|cannot stand|dislike) "
                        r"(?:it )?when\b.{3,}", re.I)
_RELATABLE = re.compile(r"(?:mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|sundays?|mornings?|early mornings|"
                        r"waking up early|getting up early|alarms?|alarm clocks?|rain|rainy days|winter|the cold|cold weather|"
                        r"the heat|hot weather|summer|traffic|commuting|the commute|homework|exams?|tests|waiting|queues|"
                        r"lines|cleaning|chores|housework|laundry|dishes|doing the dishes|meetings|emails|taxes|"
                        r"the dentist|dentists|spiders|mosquitos|mosquitoes|bugs|small talk|crowds|noise|snow)", re.I)
_DISLIKE_DE = re.compile(r"^(?:also |ehrlich gesagt |ehrlich )?ich (?:mag|esse|trinke|schaue|höre|lese) "
                         r"(?:(?:echt |wirklich |gar |überhaupt )?(?:keine?n?|nicht so gern|nicht gern|nicht)) "
                         r"(?P<x>[a-zäöüß][a-zäöüß -]{1,30}?)(?: so gern| gern| so)?$|"
                         r"^ich (?:hasse (?P<z>[a-zäöüß][a-zäöüß -]{1,30})|kann (?P<y>[a-zäöüß][a-zäöüß -]{1,30}?) "
                         r"nicht (?:leiden|ausstehen))$")
_RELATABLE_DE = re.compile(r"(?:montage?|montags|morgende?|frühes aufstehen|früh aufstehen|wecker|regen|regenwetter|winter|"
                           r"kälte|hitze|stau|staus|pendeln|hausaufgaben|prüfungen|klausuren|warten|schlangen|putzen|"
                           r"aufräumen|hausarbeit|wäsche|abwasch|meetings|e-mails|mails|steuern|zahnarzt|zahnärzte|"
                           r"spinnen|mücken|insekten|smalltalk|menschenmassen|lärm|schnee)", re.I)
_PREFER = re.compile(r"^(?:actually|no|well|hmm|wait)?,?\s*(?:i (?:think )?(?:prefer|like|love)|i'd say|make that|"
                     r"no wait,?) (?P<x>[a-z][a-z' -]{1,30}?)(?: more| better| instead| actually| now)?$")
_FAV_NOUN = {"#food": "food", "#colour": "colour", "#car": "car"}
_HI_IM = re.compile(r"^((?:hi|hey|hello|yo|heya|hiya|hallo)[,!.]*\s+(?:i'?m|im|i am|it'?s|this is)\s+)([a-z][a-z'-]+)[.!]*$", re.I)
_NOT_NAMES = frozenset(("back", "home", "here", "new", "fine", "good", "ok", "okay", "great", "well", "done", "bored", "tired",
                        "sad", "happy", "free", "busy", "sick", "ill", "hungry", "lost", "late", "early", "ready", "sorry",
                        "confused", "stuck", "curious", "alone", "awake", "up", "out", "in", "off", "on", "so", "just"))
_NAME_CUE = re.compile(r"\b((?:my name is|my name's|call me|i'm called|i am called|actually my name is) )"
                       r"([a-z][a-z'-]+(?: [a-z][a-z'-]+)?)\b(?=[.!,]|$)")
_PLACE_CUE = re.compile(r"\b((?:live in|living in|moved to|move to|moving to|from|born in|grew up in|based in|"
                        r"lives in|visited|went to|stay in|staying in) )([a-z][a-z' -]{1,40})")
_PLACE_TYPES = frozenset(("City", "Town", "Village", "Settlement", "Country", "AdministrativeRegion", "Island",
                          "CityDistrict", "Region", "State", "Place", "Location", "PopulatedPlace", "Continent"))
_THING_TYPES = frozenset(("Album", "Single", "Song", "Film", "Book", "TelevisionShow", "TelevisionSeason", "VideoGame",
                          "Software", "Building", "Automobile", "Aircraft", "Ship", "Weapon", "Food", "Drug", "Disease",
                          "Award", "Artwork", "Painting", "Mountain", "River", "Lake", "Sea", "Planet", "Star",
                          "Road", "Station", "Airport", "Language", "Event", "MilitaryConflict"))
_ORG_TYPES = frozenset(("Company", "Publisher", "RecordLabel", "Organisation", "University", "School", "PoliticalParty",
                        "GovernmentAgency", "SoccerClub", "BasketballTeam", "TelevisionStation", "Newspaper",
                        "MilitaryUnit", "Band"))
_HOWTO_Q = re.compile(r"^(?:so |ok |okay |hey )?(?:how (?:do|can|should|would) (?:i|you|one|we|people)|how to|"
                      r"how long does it take to|"
                      r"how long (?:do|should) (?:i|you)|how much \w+ should (?:i|you)|what(?:'s| is) the best way to|"
                      r"what should i (?:wear|do) (?:to|for|about)|any tips (?:on|for) |tips for |how (?:do|can) i get rid of)\b")
_TOPIC_EDGE = set("""who whom whose what which when where why how is are was were be been do does did done has have had
won win wins winning lost lose the a an of in on at for to by from with and or but about i me my you your he she it they
him her them his its their this that these those there here top best first last most many much old""".split())
_AGREE = re.compile(r"(?:yeah|yes|yep|yup|exactly|right|true|totally|definitely|absolutely|pretty much|kind of|kinda|"
                    r"sort of|i guess|i know|tell me about it|same|for real)(?:[ ,]+(?:yeah|exactly|right|true|totally|"
                    r"lol|haha|man|honestly))*[!. ]*")
_DOUBT = re.compile(r"(?:really|seriously|are you sure|you sure|is that (?:true|right|correct)|for real|"
                    r"no way|that can't be right|hm+ really|wait really)[?!.]*")
_SURPRISE = re.compile(r"(?:wow+|whoa+|woah+|omg|no way|that's (?:crazy|insane|wild|amazing|incredible|nuts|"
                       r"so cool|cool|interesting|fascinating|surprising|mad)|really|seriously|crazy|wild|"
                       r"interesting|fascinating|huh,? interesting|i didn't know that|didn't know that|"
                       r"cool|neat|nice)(?: fact)?[!?.]*")
_FAMILY_PLURALS = frozenset("kids children sons daughters brothers sisters siblings dogs cats pets twins "
                            "grandchildren".split())
_HAVE_COUNT = re.compile(r"^i (?:have|have got|'ve got|got) (two|three|four|five|six|seven|eight|nine|ten|\d{1,2}) "
                         r"([a-z]+)[.!]*$", re.I)
_HAVE_PET = re.compile(r"^i (?:have|have got|'ve got|got|own|just got|adopted|just adopted|rescued|just rescued|bought|just bought) an? (?:little |small |big |old |young |new |baby )?"
                       r"(cat|dog|puppy|kitten|rabbit|bunny|hamster|parrot|bird|horse|guinea pig|tortoise|turtle|fish|snake)[.!]*$",
                       re.I)
_PET_NAME = re.compile(r"^(?:her|his|its|their) name(?:'s| is)\s+(?P<x>[A-Za-z][\w' -]{0,25})$|"
                       r"^(?:she's|he's|it's|she is|he is|it is) called\s+(?P<y>[A-Za-z][\w' -]{0,25})$", re.I)
_PET_AGE = re.compile(r"^(?:she's|he's|it's|she is|he is|it is)\s+(?P<n>\d{1,2})(?P<u> years old| years| yrs| months old| months| weeks old| weeks)?[.!]*$", re.I)
_PET_BREED = re.compile(r"^(?:she's|he's|it's|she is|he is|it is) an? (?P<b>[a-z][a-z -]{2,30}?)(?: mix)?[.!]*$", re.I)
_PET_PRON_Q = re.compile(r"^(?P<head>(?:how old|what breed|what colou?r|what kind of \w+) is) (?:she|he|it)(?P<tail>\?)?$|"
                         r"^(?P<head2>what's|what is) (?:her|his|its) (?P<what>name|age)\??$", re.I)
_THEIR_NAMES = re.compile(r"^(?:their names are|they are called|they're called|they are named|named|called)\s+(.+)$", re.I)
_BARE_NAMES = re.compile(r"[A-Z][a-zà-ÿ'-]+(?:\s*,\s*[A-Z][a-zà-ÿ'-]+)*\s+(?:and|&)\s+[A-Z][a-zà-ÿ'-]+")
_SELF_JOIN = re.compile(r"^((?:my name is|my name's|i'm|i am|call me)\s+[A-Za-z][\w'-]*)\s*(?:,\s*|\s+)and\s+"
                        r"((?:i'm|i am|i work|i live|i have|i've got|i come|i'm from|my \w+ (?:is|are))\b.+)$", re.I)


def _split_self_statements(msg: str) -> str:
    """"My name is Sam and I'm a teacher" → "My name is Sam. I'm a teacher." (each part is learnt)."""
    m = _SELF_JOIN.match(msg.strip())
    if not m:
        return msg
    second = m.group(2)
    return f"{m.group(1)}. {second[:1].upper() + second[1:]}"


def _theme_of(st: DialogState, rep: Reply) -> str | None:
    """A few words for "what did we talk about?"."""
    la = st.last_action or {}
    if rep.via == "everyday" and la.get("turn") == st.turn and str(la.get("kind", "")).startswith("rec:"):
        return {"food": "what to cook", "book": "books", "movie": "films", "series": "series", "music": "music",
                "game": "games", "activity": "things to do", "gift": "gift ideas", "travel": "travel",
                "hobby": "hobbies", "sleep": "sleep", "study": "studying"}.get(la["kind"][4:], "some ideas")
    if rep.via in ("empathy",) or rep.kind == "empathy":
        topic = (st.last_exp or {}).get("topic")
        return topic if topic else "how you're doing"
    if rep.kind in ("learned", "memory"):
        return "things about you"
    if rep.via in ("kb", "lookup", "about", "atlas") and st.topic and st.topic.get("turn") == st.turn:
        return st.topic.get("name")
    if la.get("turn") == st.turn and la.get("kind") in ("joke", "quiz", "riddle", "fact"):
        return {"joke": "jokes", "quiz": "a quiz", "riddle": "riddles", "fact": "fun facts"}[la["kind"]]
    return None


def _stems(text: str) -> set[str]:
    """Lower-case words with a plain English ending removed ("died" → "die", "formed" → "form")."""
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        for suf in ("ing", "ed", "es", "s", "d"):
            if len(w) > len(suf) + 2 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def _full_name(answer: str | None, texts: list[str]) -> str | None:
    """A one-word name answer in its longer form from the same article ("Vickers" → "Diana
    Vickers"), when exactly one longer form occurs there."""
    if not answer or " " in answer.strip() or not answer[:1].isupper():
        return answer
    forms = Counter(m.group(1) for t in texts for m in re.finditer(
        r"\b((?:[A-Z][\w'’.-]+ ){1,2})" + re.escape(answer) + r"\b", t))
    forms = Counter({f.strip(): n for f, n in forms.items()
                     if not any(w.lower() in _FULLNAME_STOP for w in f.split())})
    if len(forms) == 1:
        return f"{next(iter(forms))} {answer}"
    return answer


_UNIT = re.compile(r"\d[\d.,]*\s*(?:%|°|(?:k?m|cm|mm|km|mi|miles?|ft|feet|foot|in|inch(?:es)?|yards?|metres?|meters?|"
                   r"kilomet(?:re|er)s?|centimet(?:re|er)s?|light[- ]years?|au|astronomical units?|parsecs?|kg|g|grams?|"
                   r"kilograms?|tonnes?|tons?|lbs?|pounds?|ounces?|oz|l|litres?|liters?|ml|gallons?|hours?|minutes?|"
                   r"seconds?|days?|weeks?|months?|years?|km/h|mph|knots?|m/s|hectares?|acres?|sq|square)\b)|"
                   r"\b(?:million|billion|thousand|hundred) (?:k?m|kilomet|miles?|km|light|years?|kg|tonnes?|people)", re.I)
_LEN = r"(?:k?m|cm|mm|km|mi|miles?|ft|feet|foot|in|inch(?:es)?|yards?|metres?|meters?|kilomet(?:re|er)s?|" \
       r"centimet(?:re|er)s?|light[- ]years?|au|astronomical units?|parsecs?)"
_DIM_UNIT = {
    "far": re.compile(r"\d[\d.,]*\s*(?:million |billion |thousand )?" + _LEN + r"\b", re.I),
    "tall": re.compile(r"\d[\d.,]*\s*" + _LEN + r"\b", re.I),
    "high": re.compile(r"\d[\d.,]*\s*" + _LEN + r"\b", re.I),
    "deep": re.compile(r"\d[\d.,]*\s*" + _LEN + r"\b", re.I),
    "long": re.compile(r"\d[\d.,]*\s*(?:" + _LEN[3:-1] + r"|hours?|minutes?|days?|years?)\b", re.I),
    "wide": re.compile(r"\d[\d.,]*\s*" + _LEN + r"\b", re.I),
    "big": re.compile(r"\d[\d.,]*\s*(?:million |billion |thousand )?(?:" + _LEN[3:-1] +
                      r"|km2|km²|m2|m²|square \w+|sq \w+|hectares?|acres?|kg|kilograms?|tonnes?|tons?)\b|"
                      r"\b(?:\d+(?:[.,]\d+)?|two|three|four|five|ten|a hundred|a thousand)(?: and a half)? times\b", re.I),
    "heavy": re.compile(r"\d[\d.,]*\s*(?:million |billion )?(?:kg|kilograms?|g|grams?|tonnes?|tons?|lbs?|pounds?|ounces?)\b|"
                        r"\d+(?:\.\d+)?\s*[×x]\s*10", re.I),
    "hot": re.compile(r"\d[\d.,]*\s*(?:°|degrees|k\b|kelvin)", re.I),
    "old": re.compile(r"\d[\d.,±]*\s*(?:million |billion |thousand )?years?\b|\b(?:1[0-9]|20)\d\d\b", re.I)}
_DIM_UNIT["large"] = _DIM_UNIT["big"]
_MEASURE_TOPIC = re.compile(r"^\s*how (?P<dim>far(?: away)?|big|large|tall|high|deep|long|wide|heavy|hot|old) "
                            r"(?:is|are|was|were) (?P<t>[\w' .-]{2,50}?)(?: away| from (?:the )?earth| from here)?\s*\??$", re.I)
_MEASURE_CUES = {
    "far": re.compile(r"\b(?:distance|away|from (?:the )?(?:earth|sun)|light[- ]years?|astronomical units?|orbits?)\b", re.I),
    "far away": re.compile(r"\b(?:distance|away|from (?:the )?(?:earth|sun)|light[- ]years?|astronomical units?|orbits?)\b", re.I),
    "big": re.compile(r"\b(?:diameter|radius|circumference|times (?:that of|the size|larger|bigger)|area|size|wide|across|"
                      r"mass|covers)\b", re.I),
    "large": re.compile(r"\b(?:diameter|radius|circumference|times (?:that of|the size|larger|bigger)|area|size|wide|across|"
                        r"mass|covers)\b", re.I),
    "tall": re.compile(r"\b(?:tall|height|high|elevation|stands)\b", re.I),
    "high": re.compile(r"\b(?:tall|height|high|elevation|altitude|stands)\b", re.I),
    "deep": re.compile(r"\b(?:deep|depth|deepest)\b", re.I),
    "long": re.compile(r"\b(?:long|length|stretches|runs for)\b", re.I),
    "wide": re.compile(r"\b(?:wide|width|across|diameter)\b", re.I),
    "heavy": re.compile(r"\b(?:mass|weighs?|weight)\b", re.I),
    "hot": re.compile(r"\b(?:temperature|°|degrees|hot)\b", re.I),
    "old": re.compile(r"\b(?:years? old|age|formed|billion years|million years|founded|built)\b", re.I)}
_MEASURE_Q = re.compile(r"^\s*how (?:far|long|tall|high|big|large|deep|wide|heavy|fast|much does .+ weigh)\b", re.I)
_LIFE_SPAN_RE = re.compile(r"\([^()]*\b\d{3,4}\s*[–—-]\s*[^()]*?\b\d{3,4}\)")
_QUOTE_STOP = frozenset("when where who whom whose what which why how did doe do is are was were has had the a an of in on "
                        "at to for from by with and or".split())
_FULLNAME_STOP = frozenset("the a an in on at of by and but when after before during since while this that these "
                           "his her their its singer songwriter band album president king queen sir lady lord mr mrs ms "
                           "dr saint st".split())


def _name_match(asked: str, title: str) -> bool:
    """The article is about what was asked: the same name (a leading article, a "(…)" qualifier
    and a ", place" part aside) or one in a row of its words with at most one word more on
    either side — never just a title containing the letters ("thai" is not "Thailand")."""
    a = re.sub(r"^(?:the|a|an)\s+", "", asked.strip().lower())
    t = re.sub(r"^(?:the|a|an)\s+", "", re.sub(r"\s*\([^)]*\)$", "", title.strip().lower()))
    if not a or not t:
        return False
    if a == t or a == t.split(", ")[0]:
        return True
    aw, tw = re.findall(r"[\w'’-]+", a), re.findall(r"[\w'’-]+", t)
    short, long_ = (aw, tw) if len(aw) <= len(tw) else (tw, aw)
    if not short or len(long_) - len(short) > 1 or (short is aw and len(aw) == 1):
        return False                             # one asked word must be the whole name ("Tower" ≠ "Eiffel Tower")
    return any(long_[i:i + len(short)] == short for i in range(len(long_) - len(short) + 1))


_ANOTHER = re.compile(r"^(?:(?:ok|okay|yes|yeah|sure|haha|lol|nice|cool|great|wow)[ ,!]+)?(?:another(?: one)?|one more"
                      r"(?: please)?|again|more please|next(?: one)?|give me another(?: one)?|tell me another(?: one)?|"
                      r"do another(?: one)?|more|any others?|anything else|any more|anymore|got any others?|what else|others?)(?: please)?\??$")
_GENERAL_MOODS = frozenset(("angry", "sad", "tired", "stress", "anxious", "happy", "excited", "calm", "lonely",
                            "conflict"))
_PLAN = re.compile(r"\b(?:i'm|i am|im|we're|we are) (?:thinking (?:about|of)|planning (?:to|on)|considering|hoping to|"
                   r"dreaming (?:of|about)|trying to decide whether to)\b|\b(?:i|we) (?:want|would like|'d like|wanna|might|"
                   r"may|plan|intend|hope) to (?:move|go|travel|visit|start|learn|buy|quit|try|become|study|switch|get)\b")
_WORK_IN = re.compile(r"^(?P<lead>i (?:work|am working|'m working|have worked|worked) in) (?P<f>(?:the )?[a-z][a-z &/-]{2,40}?)"
                      r"(?P<tail>[.!]?)$", re.I)


def _job_field(text: str) -> str:
    """"I work in private equity." → "I work in private equity. My job is in private equity." —
    a field of work (lower case), so "What do I do for a living?" finds it; "I work in Berlin"
    (a name) stays a place."""
    m = _WORK_IN.match(text.strip())
    if not m or re.match(r"^(?:a|an|this|that|my|our|his|her|their)\b", m.group("f"), re.I):
        return text
    field = m.group("f").strip()
    if re.search(r"\b(?:office|building|city|town|village|shop|store|factory|warehouse|hospital|school|bank|restaurant|"
                 r"cafe|café|lab|laboratory)s?$", field):
        return text
    body = text.strip().rstrip(".!")
    return f"{body}. My job is in {field}."


_DE_COMPARE = [(r"^(.+?) vs (.+?):", r"\1 im Vergleich mit \2:"), (r"• Population:", "• Einwohner:"),
               (r"• Area:", "• Fläche:"), (r"• Capital:", "• Hauptstadt:"), (r"• Official language:", "• Amtssprache:"),
               (r"• Currency:", "• Währung:"), (r"• Elevation:", "• Höhe:"), (r"• Born:", "• Geboren:"),
               (r"• Died:", "• Gestorben:"), (r"• Nationality:", "• Nationalität:"), (r"• Occupation:", "• Beruf:"),
               (r"• Known for:", "• Bekannt für:"), (r"• Founded:", "• Gegründet:"), (r"• Headquarters:", "• Sitz:"),
               (r"• Industry:", "• Branche:"), (r"• Employees:", "• Mitarbeiter:"), (r"• Height:", "• Höhe:"),
               (r"(\S.*?) has more people\.", r"\1 hat mehr Einwohner."),
               (r"(\S.*?) has the larger area\.", r"\1 hat die größere Fläche."),
               (r"^(.+?) is bigger by area: (.+?), compared with (.+?) for (.+?)\.$", r"\1 ist flächenmäßig größer: \2, im Vergleich zu \3 bei \4."),
               (r"^(.+?) is more populous: (.+?), compared with (.+?) for (.+?)\.$", r"\1 hat mehr Einwohner: \2, im Vergleich zu \3 bei \4."),
               (r"^(.+?) is (higher|taller): (.+?), compared with (.+?) for (.+?)\.$", r"\1 ist höher: \3, im Vergleich zu \4 bei \5."),
               (r"^(.+?) is longer: (.+?), compared with (.+?) for (.+?)\.$", r"\1 ist länger: \2, im Vergleich zu \3 bei \4."),
               (r"^(.+?) is older: (.+?) was born (.+?), (.+?) (.+?)\.$", r"\1 ist älter: \2 wurde \3 geboren, \4 \5."),
               (r"^(.+?) is younger: (.+?) was born (.+?), (.+?) (.+?)\.$", r"\1 ist jünger: \2 wurde \3 geboren, \4 \5."),
               (r" million", " Millionen"),
               (r"\bFrench\b", "Französisch"), (r"\bGerman\b", "Deutsch"), (r"\bEnglish\b", "Englisch"),
               (r"\bItalian\b", "Italienisch"), (r"\bSpanish\b", "Spanisch"), (r"\bDutch\b", "Niederländisch"),
               (r"\bPortuguese\b", "Portugiesisch"), (r"\bPolish\b", "Polnisch"), (r"\bRussian\b", "Russisch"),
               (r"\bJapanese\b", "Japanisch"), (r"\bChinese\b", "Chinesisch"), (r"\bSwedish\b", "Schwedisch"),
               (r"\bPound sterling\b", "Pfund Sterling"), (r"\bSwiss franc\b", "Schweizer Franken"),
               (r"\bUnited States dollar\b", "US-Dollar"), (r"\bJapanese yen\b", "Japanischer Yen")]


def _de_compare(text: str, said: str = "") -> str:
    """An English comparison in German, with the user's own place names ("France" → "Frankreich")."""
    from engramm.chat.german_bridge import EXONYMS, de_value
    out = []
    for line in text.split("\n"):
        for pat, rep in _DE_COMPARE:
            line = re.sub(pat, rep, line)
        line = de_value(line) if line.startswith("•") or " ist " in line or " hat " in line else line
        out.append(re.sub(r"\b(\d+)\.(\d) Millionen", r"\1,\2 Millionen", line))   # 68.6 → 68,6
    text = "\n".join(out)
    for de_name, en_name in EXONYMS.items():
        if re.search(rf"\b{re.escape(de_name)}\b", said):
            text = re.sub(rf"\b{re.escape(en_name)}\b", de_name[:1].upper() + de_name[1:], text)
    return text


def _de_advice_hint(s: str) -> str:
    """English keywords for the advice groups ("mein Chef nervt" → "boss")."""
    pairs = [("chef", "boss"), ("kolleg", "colleague"), ("arbeit", "work"), ("freundin", "girlfriend"),
             ("freund", "friend"), ("mutter", "mom"), ("vater", "dad"), ("eltern", "parents"), ("schluss gemacht", "broke up"),
             ("verlassen", "left me"), ("gestorben", "died"), ("prüfung", "failed"), ("durchgefallen", "failed"),
             ("stress", "stressed"), ("müde", "tired"), ("erschöpft", "tired"), ("traurig", "sad"), ("kündigen", "quit")]
    return " ".join(e for d, e in pairs if d in s)


def _join_values(values: list[str]) -> str:
    values = list(dict.fromkeys(values))
    if len(values) <= 2:
        return " and ".join(values)
    return ", ".join(values[:-1]) + " and " + values[-1]


def _join(intro: str, text: str) -> str:
    intro = intro.strip()
    return f"{intro} {text}" if intro else text


_POS = frozenset("nice great good beautiful lovely awesome amazing fun delicious perfect wonderful excellent cool "
                 "sunny gorgeous fantastic brilliant interesting exciting tasty cute pretty sweet happy".split())
_NEG = frozenset("bad terrible awful horrible boring sad ugly rainy annoying stupid broken disgusting gross "
                 "cold freezing hot miserable dreadful worse worst difficult hard expensive".split())


def _valence(norm: str) -> str | None:
    ws = set(norm.split())
    neg = bool(ws & {"not", "isn't", "wasn't", "aren't", "don't", "doesn't", "never"})
    p, n = len(ws & _POS), len(ws & _NEG)
    if p > n:
        return "negative" if neg else "positive"
    if n > p:
        return "positive" if neg else "negative"
    return None


def _order(n: int, key: str) -> list[int]:
    return sorted(range(n), key=lambda i: hashlib.shake_256(f"{key}|{i}".encode()).digest(8))


def _rand(key: str, n: int) -> int:
    return int.from_bytes(hashlib.shake_256(key.encode()).digest(8), "little") % max(n, 1)


def _compose(parts: list[_Part]) -> str:
    order = {"prefix": 0, "main": 1, "learn": 2, "follow": 3}
    seen, out = set(), []
    for p in sorted(parts, key=lambda p: order.get(p.role, 1)):
        t = p.text.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    text = ""
    for t in out:
        sep = "\n\n" if ("\n" in t or "\n" in text) and text else " "
        text = f"{text}{sep}{t}" if text else t
    return text


def _fact_rank(f) -> tuple:
    order = {lab: i for i, (lab, _) in enumerate(_CATEGORY_KEYS)}
    best = min((order[lab] for lab in f.relation if lab in order), default=len(order))
    return (0 if f.subject == USER else 1, best, f.object)


def _atype(q: str) -> str | None:
    from engramm.chat.question import analyse
    try:
        return analyse(q).atype
    except Exception:            # the realiser works without a type
        return None


def _asked_category(q: str) -> str | None:
    """The category of a question about you ("What's my name?" → #name); None for owned things
    ("my dog's name") and anything else."""
    low = q.lower().replace("’", "'")
    if re.search(r"\bmy (?!name\b)[a-z]+(?:'s)? name\b|\bis my [a-z]+ called\b", low):
        return None
    if re.search(r"\bname\b|\bcalled\b|\bcall me\b", low):
        return "#name"
    if re.search(r"\bwhere (?:do|did) i work\b|\bemployer\b|\bcompany\b|\bfirm\b|\bwork for\b", low):
        return "#employer"
    if re.search(r"\b(?:live|home|city|town|reside)\b", low):
        return "#home"
    if re.search(r"\b(?:job|work|profession|occupation|do for a living)\b", low):
        return "#job"
    if re.search(r"\bfood\b|\beat\b|\bdish\b", low):
        return "#food"
    if re.search(r"\bcolou?r\b", low):
        return "#colour"
    if re.search(r"\bcar\b|\bdrive\b", low):
        return "#car"
    if re.search(r"\bbirthday\b|\bborn\b|\bbirth\b", low):
        return "#birth"
    if re.search(r"\bwhere am i from\b|\bwhere do i come from\b|\borigin\b", low):
        return "#origin"
    return None


def _user_answer_text(answer: str, evidence: str | None) -> str:
    if evidence:
        flipped = to_second_person(evidence)
        if flipped and answer and answer.lower() in flipped.lower():
            return flipped
        return f"{answer} — you told me: “{evidence}”"
    return f"{answer}."


_SLOT_STRIP = re.compile(r"^(?:(?:well|so|oh|ok|okay|sure|yes|yeah|um+|uh+|hmm+)[,!.]?\s+)*"
                         r"(?:it's|it is|that's|that is|i'm|i am|my name is|my name's|the name's|the name is|"
                         r"call me|you can call me|just call me|i live in|i'm from|i am from|in|i work as|i'm a|i am a|"
                         r"i am an|i'm an|i like|i love|i enjoy|my favou?rite (?:food|colou?r) is|i have)\s+", re.I)


_NOT_A_NAME = re.compile(r"\b(?:not|doing|feeling|feel|good|great|fine|ok|okay|alright|bad|sad|tired|happy|so|very|"
                         r"really|well|busy|bored|sick|ill|stressed|excited|thanks|thank|hungry|here|back|sure|sorry|"
                         r"just|kinda|pretty|awful|terrible|meh|exhausted|upset|angry|lonely|nervous|was|is|are|am|"
                         r"his|her|their|its|my|your|the|a|an)\b", re.I)


def _slot_value(msg: str, slot: str | None) -> str | None:
    s = msg.strip().strip(".!?").strip()
    s = _SLOT_STRIP.sub("", s).strip(" ,.!")
    if not s:
        return None
    words = s.split()
    if slot == "name":
        if len(words) > 3 or not all(re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+", w) for w in words):
            return None
        if normalise(s) in ("no", "nope", "not telling", "nothing", "none", "secret", "why"):
            return None
        if _NOT_A_NAME.search(s):
            return None                                   # "I'm not doing great" answers how, not who
        return s
    if slot == "mood":
        return None
    if len(words) > 8:
        return None
    return s


class ConversationBot:
    """The ``ChatBot`` interface on top of the assistant, so the registered dialog and fact
    evaluations (experiments/chat_v2_tasks.py) can run through the conversation layer: ``turn``
    goes through ``Assistant.turn``; assigning ``context`` (their reset) starts a new
    conversation; everything else is the core bot's."""

    def __init__(self, bot, conversation: str = "eval", clock=None):
        object.__setattr__(self, "core", bot)
        object.__setattr__(self, "assistant", Assistant(bot, clock=clock))
        object.__setattr__(self, "state", DialogState(conversation=conversation))
        object.__setattr__(self, "_conversation", conversation)

    def turn(self, message: str) -> Reply:
        return self.assistant.turn(self.state, message)

    @property
    def context(self) -> dict:
        return self.state.ctx

    @context.setter
    def context(self, value: dict) -> None:
        object.__setattr__(self, "state", DialogState(conversation=self._conversation, ctx=dict(value)))

    def __getattr__(self, name):
        return getattr(self.core, name)

    def __setattr__(self, name, value):
        if name == "context":
            object.__setattr__(self, "state", DialogState(conversation=self._conversation, ctx=dict(value)))
        else:
            setattr(self.core, name, value)
