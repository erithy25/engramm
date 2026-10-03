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

from engramm.chat.about import About, AboutFinder, clean_sentence, title_key
from engramm.chat.acts import Unit, classify
from engramm.chat.bank import Bank, choose, expand_chat, load_bank, normalise
from engramm.chat.bot import CHAT_PREFIX, OWN_PRONOUN, Reply, message_type, source_id
from engramm.chat.everyday import _GENRES
from engramm.chat.tools import tool_answer
from engramm.chat.facts import USER, facts_from_text
from engramm.chat.german import is_german, understand
from engramm.chat.realize import _acronyms as _acronym_case, answer_sentence, article, personal_sentence, to_second_person
from engramm.chat.smart import (bare_followup, experience, gibberish, is_discourse, is_mash, offer_in, rebuild_question, strict_mash,
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
_THINGS_TO_DO = re.compile(r"^(?:maybe |ok |okay |so )?(?:what (?:else )?(?:can|could) (?:i|we) do(?P<g2> at home| inside| indoors| outside)[?.!]*$|"
                           r"(?:(?:something|anything|stuff|things?|ideas?|any ideas?)(?: (?:what|that))?|what(?: else)?) "
                           r"(?:i|we) (?:can|could|might) do(?P<g> at home| inside| indoors| outside| alone| today| tonight)?[.!?]*$)")
_CONTINENTS = frozenset(("africa", "antarctica", "asia", "australia", "europe", "north america", "south america",
                         "central america", "latin america", "oceania", "the caribbean", "scandinavia", "the middle east"))
# "maybe reading then", "a movie i guess": a kind of thing to suggest
_MAYBE_KIND = re.compile(r"^(?:maybe|perhaps|ok|okay|hmm|i guess|i think|probably|then)[, ]+(?P<w>reading|a book|books|a movie|movies|a film|films|"
                         r"a series|a show|tv|music|a game|games|gaming|a podcast|podcasts|cooking|baking|a hobby)"
                         r"(?: then| maybe| i guess| or something)?[.!?]*$")
_MAYBE_KINDS = {"reading": "book", "book": "book", "books": "book", "movie": "movie", "movies": "movie", "film": "movie",
                "films": "movie", "series": "series", "show": "series", "tv": "series", "music": "music", "game": "game",
                "games": "game", "gaming": "game", "podcast": "podcast", "podcasts": "podcast", "cooking": "food",
                "baking": "food", "hobby": "hobby"}
# "I moved to a new city and don't know anyone"
_COMMON_FOODS = frozenset("""pizza pasta sushi burger taco curry salad ramen noodle soup sandwich chinese indian thai
mexican italian japanese kebab fries steak chicken fish rice pho dumpling lasagna lasagne spaghetti risotto omelette eggs
pancake waffle burrito wrap falafel poke bowl stir fry stir-fry chili chilli takeout takeaway something sweet chocolate
ice cream cake toast cereal leftovers nachos wings""".split()) | {"stir fry", "ice cream", "fried rice", "mac and cheese",
                                                                 "something sweet", "something healthy", "a salad"}
_LANGS = frozenset("spanish french german italian portuguese japanese chinese mandarin korean arabic russian dutch "
                   "swedish turkish greek polish hindi english".split())
_LEARNING = re.compile(r"^(?:so |btw,? |guess what,? )?(?:i'?m|im|i am|i'?ve been|i have been|i just started|i started) "
                       r"(?:learning|practicing|practising|taking lessons in|teaching myself)(?: to play| how to play)? (?:the )?"
                       r"(?P<x>guitar|piano|drums|violin|ukulele|" + "|".join(sorted(_LANGS)) + r")"
                       r"(?: (?:lately|recently|again|now|at the moment|this year))?$")
_LEARN_FOLLOW = [
    ("pain", re.compile(r"\b(?:fingers? (?:hurt|hurts|are sore|is sore|ache)|sore fingers|my fingers|hurts my fingers|blisters?)\b")),
    ("hard", re.compile(r"^(?:but |yeah,? |honestly,? )?(?:it'?s|its|it is) (?:so |really |super |kinda |pretty )?(?:hard|difficult|tough)|"
                        r"^(?:i'?m|im) (?:so |really )?(?:bad|terrible|slow) at it|^i (?:keep|always) (?:messing up|forgetting|making mistakes)")),
    ("how_long", re.compile(r"\bhow long (?:until|till|before|does it take|will it take)|\bwhen (?:will|do) i get (?:good|better)\b|"
                            r"\bhow (?:fast|quickly) can i (?:learn|get good)")),
    ("songs", re.compile(r"\b(?:songs?|pieces?|tunes?)\b.*\b(?:beginners?|easy|simple|start|learn)\b|\b(?:easy|simple|beginner) "
                         r"(?:songs?|pieces?)\b|\bwhat should i (?:play|learn) first\b")),
    ("tips", re.compile(r"\b(?:any |some |got any )?(?:tips|advice|tricks)\b|\bhow (?:can|do|should) i (?:practi[cs]e|learn|improve|get better)\b")),
]
_IT_ABOUT = re.compile(r"^(?:so |and |ok |okay |hmm,? )?(?:what'?s it about|what is it about|what are they about|tell me (?:more )?about it|"
                       r"who wrote it|who made it|who directed it|is it good|is it any good|what kind of (?:book|movie|film|show) is it)\??$")
_WILL_THEY = re.compile(r"^(?:but |so |and )?(?:do you think|you think|will|would|is there a chance|what if) (?:she|he|they|my ex)"
                        r"(?:'ll| will| would|'d)? ?(?:ever |still |actually )?(?:come back|forgive me|text me|call me(?: back)?|"
                        r"miss(?:es)? me|want(?:s)? me back|get back together|love(?:s)? me|change|regret(?:s)? it|apologi[sz]e)"
                        r"(?: (?:to me|again|one day|someday|eventually))?\??$")
_BOT_LIKES = re.compile(r"^(?:idk,? |so,? |and |but |ok,? |lol,? )?(?:do you (?:like|enjoy|love) (?:anything|stuff|things|something)|what do you "
                        r"(?:like|enjoy|love)(?: doing| to do)?|what do you do (?:for fun|in your (?:free|spare) time|all day)|"
                        r"what are your hobbies|what'?s your (?:hobby|favou?rite hobby)|what are you into|what makes you happy|do you have "
                        r"(?:hobbies|a hobby|interests|any hobbies|any interests))\??$")
_SLEPT_GOOD = re.compile(r"^(?:oh |well |yeah |actually |honestly )?(?:i )?(?:slept|had (?:a )?(?:really |super |pretty |very )?"
                         r"(?:great|good|amazing|fantastic|wonderful|solid|deep) (?:sleep|night(?:'?s sleep)?))(?: (?:really|so|super|pretty|very|"
                         r"incredibly))?(?: (?:great|well|amazing|good|fantastic|wonderful|like a baby|like a log|like a rock|"
                         r"for (?:ten|10|nine|9|eight|8) hours))?(?: actually| last night| for once| today)*[!. ]*$")
_SLEPT_BAD = re.compile(r"^(?:ugh,? |oh |well |honestly )?(?:i )?(?:(?:slept|sleep) (?:really |so |very |super |pretty )?"
                        r"(?:badly|bad|terribly|terrible|horribly|awful|awfully|poorly|like crap)|(?:barely|hardly|didn'?t|did not) "
                        r"(?:slept|sleep)(?: at all)?|had (?:a )?(?:really |such a )?(?:bad|terrible|rough|awful|horrible|sleepless) "
                        r"(?:night|sleep)|couldn'?t (?:fall asleep|sleep)(?: at all)?)(?: last night| again| at all)*[!. ]*$")
_HOW_ABOUT = re.compile(r"^(?:ok |okay |so |hmm,? |well,? )?(?:how about|what about|maybe|let'?s (?:go for|have|get|grab|take)) "
                        r"(?:a |an |some |we (?:go for |have |get |grab |take )?(?:a |an |some )?)(?P<x>(?:quick |short |long |little |nice |"
                        r"cup of |hot )?(?:walk|run|jog|coffee|tea|break|nap|bike ride|swim|stroll|snack|drink|beer|"
                        r"movie night|game night|pizza|bath|shower|rest|picnic|hike|chat|cocktail|glass of wine|"
                        r"ice cream|workout|day off|trip|holiday|vacation))(?: then| instead| later| now| together)?[?!.]*$")
_LIKE_TITLE = re.compile(r"^(?:maybe |ok |hmm,? )?(?:something|anything|one|stuff|books?|movies?|films?|shows?|series|more)? ?"
                         r"(?:like|similar to|in the style of|along the lines of) (?P<x>[a-z0-9' :&-]{3,40})\??$")
_LIKE_GENRE = {"harry potter": "fantasy", "the lord of the rings": "fantasy", "lord of the rings": "fantasy",
               "game of thrones": "fantasy", "the hobbit": "fantasy", "narnia": "fantasy", "percy jackson": "fantasy",
               "star wars": "scifi", "star trek": "scifi", "dune": "scifi", "the martian": "scifi", "interstellar": "scifi",
               "the hunger games": "dystopia", "hunger games": "dystopia", "1984": "dystopia", "divergent": "dystopia",
               "sherlock": "mystery", "sherlock holmes": "mystery", "agatha christie": "mystery", "breaking bad": "crime",
               "the godfather": "crime", "friends": "comedy", "the office": "comedy", "brooklyn nine-nine": "comedy",
               "pride and prejudice": "romance", "the notebook": "romance", "toy story": "animation", "shrek": "animation",
               "inception": "scifi", "the matrix": "scifi", "blade runner": "scifi", "nineteen eighty-four": "dystopia",
               "brave new world": "dystopia", "the handmaid's tale": "dystopia", "fahrenheit 451": "dystopia",
               "the dark knight": "action", "titanic": "romance", "the shining": "thriller", "get out": "thriller"}
_NEW_JOB = re.compile(r"\b(?:got|have|landed|found|accepted|took|start(?:ing)?|begin(?:ning)?) (?:a |my |the |that )?(?:new )?job"
                      r"(?: offer)?\b(?! interview)|\bgot hired\b|\bnew job\b")
_JOB_AT = re.compile(r"(?:it'?s|its|it is|it'?ll be|that'?s|the (?:new )?job is|i'?ll be working|i will be working|i'?m going to work|"
                     r"i'?m gonna work|i'?ll work|i will work|i work|i'?m working) (?:at|with|for) (?P<x>(?:a|an|the|[a-z])[\w' &.-]*"
                     r"(?: [\w' &.-]+){0,6})")
_JOB_START = re.compile(r"(?:and )?i (?:start|begin|'?ll start|will start|am starting|'?m starting|start working|'?m gonna start)"
                        r"(?: there| work| the job| it| the new job)? (?P<x>(?:on |next |this |in |tomorrow|monday|tuesday|wednesday|"
                        r"thursday|friday|saturday|sunday|the |january|february|march|april|may|june|july|august|september|"
                        r"october|november|december)[\w ]{0,30})")
_MOVED_NEW = re.compile(r"\bi (?:just |recently )?(?:moved|relocated) (?:to|into) (?:a |another )?(?:new|different|another) (?:city|town|country|place)\b")
# "what should I wear (to the interview)?"
# everyday context (battery 42): a promotion and its title, a week to plan, a dish for someone, "I'll check it out"
_PROMOTED = re.compile(r"\b(?:i |i've |ive |i have )?(?:just |finally |officially )?(?:got|been|was|have been|'ve been) promoted\b")
_TITLE = re.compile(r"(?:to |as |it'?s |its |now |i'?m (?:now |a |an )?)?(?:a |an |the )?(?P<x>(?:senior |junior |lead |head |chief |principal |"
                    r"assistant |associate |deputy |vice |regional |team |general )?[a-z]+(?: [a-z]+)?(?: manager| director| lead| engineer"
                    r"| analyst| partner| officer| president| consultant| supervisor| developer| designer)?)[.!]*")
_CELEBRATE_PLAN = re.compile(r"^(?:yeah,? |so |and )?(?:i'?m |im |i am |we'?re |were )?(?:thinking (?:about|of)|planning (?:on|to)?|going to|"
                             r"gonna|want to|wanna|might|hoping to) (?:celebrat\w*|go(?:ing)? out|have a party|throw a party)"
                             r"(?: it)?(?: with (?:my |some )?(?:friends|the team|family|colleagues|my partner|my girlfriend|my boyfriend|"
                             r"my wife|my husband))?(?: (?:tonight|this weekend|on (?:friday|saturday)))?[.!]*$")
_CHECK_OUT = re.compile(r"^(?:(?:nice|cool|ok|okay|great|awesome|sounds good|perfect|thanks|ty|oh nice|ooh)[,!.]? )*(?:i'?ll|ill|i will|"
                        r"gonna|going to|will|i'?m gonna|im gonna|might) (?:definitely |totally |probably )?(?:check (?:it|them|that|those|this|"
                        r"one) out|give (?:it|them|that|one) a (?:try|go|shot|look)|try (?:it|them|that|one)(?: out)?|look (?:it|them|that) up|"
                        r"watch (?:it|that|one)|read (?:it|that|one)|play (?:it|that|one))(?: (?:later|tonight|soon|this weekend|then))?"
                        r"(?: thanks?| ty)?[.!]*$")
_PLAN_WEEK = re.compile(r"^(?:hey,? |so,? |ok,? )?(?:can|could|would|will) you (?:please )?help me (?:to )?(?:plan|organi[sz]e|structure|sort out|"
                        r"schedule) my (?P<p>week|weekend|schedule|next week|days?)(?: please)?\??$|^help me plan my (?P<q>week|weekend)\??$")
_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_DAY_RX = re.compile(r"\b(mon|tues?|wed(?:nes)?|thu(?:rs?)?|fri|sat(?:ur)?|sun)(?:day)?s?\b")
_WEEK_SHOW = re.compile(r"^(?:so,? |ok,? )?(?:what(?:'s| is| does) my (?:week|schedule)(?: look(?:s)? like)?|what do i have (?:this|next) week|"
                        r"show me my (?:week|schedule)|can you (?:show|summari[sz]e) my week)\??$")
_PREP_TOPICS = (("presentation", r"presentation|pitch|talk\b|speech"), ("interview", r"\binterv[a-z]{2,4}\b"),
                ("exam", r"exam|test\b|finals?\b|midterm"), ("meeting", r"meeting"), ("date", r"\bdate\b"))
_PREPARE = re.compile(r"^(?:so |and |ok |okay |but |any tips on )?how (?:should|do|can|could|would) i (?:best |even )?prep(?:are)?"
                      r"(?: (?:for|myself for) (?:it|that|this|the (?P<x>[a-z]+)|my (?P<y>[a-z]+)))?\??$|"
                      r"^(?:any )?tips (?:for|on) (?:preparing|prepping)(?: for (?:it|that))?\??$")
_COOK_FOR = re.compile(r"^(?:so |and |ok )?what (?:should|could|can|do you think i should) i (?:cook|make)(?: for (?:her|him|them|my \w+|"
                       r"[a-z]+))?(?: (?:tonight|this weekend|for dinner|then))?\??$")
_MAKE_THAT = re.compile(r"^(?:ok |and |so |cool,? )?how (?:do|can|would|should) i (?:make|cook|prepare) (?:that|it|this|those|them|one of (?:those|them))"
                        r"(?: one)?\??$|^(?:can i have|can you give me|give me) (?:the |a )?recipe\??$")
_MAKE_DISH = re.compile(r"^(?:ok |and |so )?(?:how (?:do|can|would|should) i (?:make|cook|prepare)|recipe for|how to (?:make|cook)) "
                        r"(?:a |an |some |the )?(?P<x>[a-z ]{3,40}?)\??$")
_WHAT_LIKES = re.compile(r"^(?:and |so )?what does (?P<x>my [a-z]+|[a-z]+) (?:like|love|enjoy|like to eat)\??$")
_NO_WORRIES = re.compile(r"^(?:(?:ok|okay|alright|ah ok|oh ok|ah|oh|fair enough|fine|haha|lol)[,!.]? )?(?:no worries|no problem|np|all good|"
                         r"that'?s (?:fine|ok|okay|alright)|thats (?:fine|ok|okay)|never ?mind|nvm|it'?s fine|its fine|it'?s ok(?:ay)?)[.!]*$")
_RACING = re.compile(r"^(?:and |but |it'?s just |just )?(?:my )?(?:mind|head|brain|thoughts?)(?: (?:keeps?|is|are|won'?t stop|keep))? "
                     r"(?:racing|spinning|going|overthinking|running)(?: (?:all night|nonstop|non stop|in circles))?[.!]*$|"
                     r"^(?:i )?(?:keep|can'?t stop) (?:overthinking|thinking about (?:everything|stuff|work))[.!]*$")
# a tournament by its year ("who won the world cup in 2014?", "where were the 2016 olympics held?", "and in 2018?")
_EVENT_NAMES = (("world cup", r"(?:fifa )?(?:football |soccer )?world cup", "{y} FIFA World Cup"),
                ("women's world cup", r"(?:fifa )?women'?s world cup", "{y} FIFA Women's World Cup"),
                ("euro", r"(?:uefa )?euros?(?: cup)?|european championship", "UEFA Euro {y}"),
                ("summer olympics", r"(?:summer )?olympics|olympic games", "{y} Summer Olympics"),
                ("winter olympics", r"winter olympics", "{y} Winter Olympics"))
_EVENT_Q = re.compile(r"^(?:and |so |ok |hey )?(?P<q>who won|who was the winner of|which (?:team|country) won|who were the champions of|"
                      r"where (?:was|were|is|are)|which country hosted|who hosted|when (?:was|were|did)) (?:the )?"
                      r"(?P<e>(?:\d{4} )?[a-z' ]+?(?: in \d{4}| \d{4})?)(?: (?:held|hosted|played|take place|happen))?\??$")
_EVENT_AGAIN = re.compile(r"^(?:(?:and|what about|how about|and what about)\s+)?(?:in |the )?(?P<y>(?:19|20)\d\d)(?: one)?\??$")
_EVENT_IT = re.compile(r"^(?:and |so )?(?P<q>where|who won|who hosted|when) (?:was|were|did) (?:it|that|they)(?: (?:held|hosted|played|take place|happen))?\??$|"
                       r"^(?:and |so )?who won (?:it|that)\??$")
# "who is the president of France?" when the fact bank has no holder: the office's own article, with its date
_OFFICE_Q = re.compile(r"^(?:and |so |ok |hey )?who(?:'s| is| was)? (?:the )?(?:current |present |new )?(?P<o>president|prime minister|pm|"
                       r"chancellor|king|queen|monarch|pope|secretary[- ]general|first minister|premier)(?: of (?:the )?(?P<x>[a-z .'-]+?))?"
                       r"(?: (?:right now|now|currently|today|at the moment))?\??$")
_FIRST_Q = re.compile(r"^(?:and |so |ok |hey )?who (?:was|were|is) the (?P<n>first|1st) (?P<o>[a-z][a-z -]{2,30}?) of (?:the )?(?P<x>[a-z][a-z .'-]{1,40}?)\??$")
_MAKER_Q = re.compile(r"^(?:and |so |ok |hey )?who (?P<v>composed|wrote|painted|directed|created|designed|sculpted|sang|built) (?P<w>[a-z0-9][a-z0-9 .,'&:-]{1,60}?)\??$")
_MAKER_PP = {"composed": "composed", "wrote": "written", "painted": "painted", "directed": "directed", "created": "created",
             "designed": "designed", "sculpted": "sculpted", "sang": "sung", "built": "built"}
_TENURE_Q = re.compile(r"^(?:and |so |ok )?how long (?:was|did|has|is) (?P<e>[A-Z][\w.'-]*(?: [A-Z][\w.'-]*){0,4}) (?:serve as |been |be )?"
                       r"(?:the )?(?P<o>president|prime minister|chancellor|king|queen|emperor|pope|mayor|governor|in office|in power|"
                       r"on the throne|ceo|leader)\b.*$", re.I)
_THEY_LIVE = re.compile(r"^(?:and |so )?what (?P<k>language|languages|currency|money) (?:do|did) they (?:speak|use|pay with|have)(?: there)?\??$")
_COLOURS = frozenset(("red", "blue", "green", "yellow", "orange", "purple", "violet", "pink", "black", "white", "grey", "gray",
                      "brown", "turquoise", "teal", "gold", "silver", "beige", "navy", "lilac", "mint", "dark blue", "light blue",
                      "dark green", "burgundy", "magenta", "cyan", "lavender", "maroon"))
_OFFICE_ALIAS = {"us": "United States", "usa": "United States", "america": "United States", "united states": "United States",
                 "united states of america": "United States", "uk": "United Kingdom", "britain": "United Kingdom",
                 "great britain": "United Kingdom", "england": "United Kingdom", "united kingdom": "United Kingdom",
                 "un": "United Nations", "united nations": "United Nations"}
_THE_PLACES = {"United States", "United Kingdom", "United Nations", "Netherlands", "Philippines", "Czech Republic",
               "Republic of Ireland", "United Arab Emirates", "Bahamas", "Gambia"}
_HOLDER = re.compile(r"\b(?:incumbent|current (?:officeholder|holder|office-holder|monarch|pope|president|prime minister|chancellor|"
                     r"secretary-general)) is (?P<a>(?:King |Queen |Pope )?[A-Z][\w.'’-]+(?: (?:de |von |van |da |bin )?[A-Z][\w.'’-]+){0,3})|"
                     r"(?P<b>[A-Z][\w.'’-]+(?: [A-Z][\w.'’-]+){1,3}) is the (?:\d+\w* (?:and )?)?(?:current|incumbent)\b")
# battery 43: small talk that follows on from what was just said
_SAME_FINE = re.compile(r"^(?:same|same here|me too|likewise|same lol|same tbh|same haha|ditto|you too|same old)[.! ]*(?:lol|haha|tbh)?[.!]*$")
_BOT_SAD = re.compile(r"^(?:oh,? |aw+,? |hmm,? )?(?:that'?s|thats|that is|sounds) (?:kinda |kind of |a bit |so |really |pretty |very )?"
                      r"(?:sad|depressing|lonely|bleak|boring|grim)(?: (?:tbh|lol|honestly|though))?[.!]*$")
_MOVED_REASON = re.compile(r"^(?:it'?s |its |mainly |mostly |just )?(?:for|because of) (?:a |my |the )?(?P<r>work|job|new job|uni|university|"
                           r"college|school|studies|studying|my studies|love|my partner|my girlfriend|my boyfriend|my wife|my husband|"
                           r"family|a fresh start|a change)[.!]*$")
_AREAS_Q = re.compile(r"^(?:and |so |ok )?(?:any |what are (?:some |the )?|which are (?:the )?|what'?s a |where'?s a )?(?:good |nice |best |cool |safe )"
                      r"(?:neighbou?rhoods?|areas?|districts?|parts of (?:the )?(?:city|town))(?: to live(?: in)?| to stay(?: in)?| for (?:young people|families))?"
                      r"(?: (?:there|in (?P<p>[a-z][a-z ]+?)))?\??$|^(?:where should i (?:live|stay|look for a flat|look for an apartment))"
                      r"(?: (?:there|in (?P<q>[a-z][a-z ]+?)))?\??$")
_BEST_FOOD = re.compile(r"^(?:and |so |ok )?(?:what'?s|what is|whats) (?:the )?(?:best|typical|local|must-try|famous) (?:food|dish|thing to eat)"
                        r"(?: (?:there|in (?P<p>[a-z][a-z ]+?)))?\??$|^(?:what (?:is|are) (?:the )?(?:famous|typical) (?:foods?|dishes) "
                        r"(?:there|in (?P<q>[a-z][a-z ]+?)))\??$")
_THANKS_NICE = re.compile(r"^(?:thanks?|thank you|ty|thx|aw+,? thanks?)[,!.]* (?:you'?re|ur|youre|you are) (?:so |really |very |the |such a )?"
                          r"(?:sweet|kind|best|amazing|awesome|lovely|great|star|helpful|nice|a gem|a sweetheart|wonderful)[.! ]*(?:❤️|<3|:\))?$")
_TIP = re.compile(r"^(?:what'?s|what is|whats|how much is|how much should i (?:tip|leave)(?: on| for)?|calculate)(?: the| a)? ?(?:tip|gratuity)?"
                  r"(?: on| for)? (?:a |the |my )?[$€£]?(?P<n>\d+(?:[.,]\d{1,2})?) ?(?:dollars?|euros?|bucks|pounds|usd|eur|€|\$)?"
                  r"(?: (?:bill|check|meal|dinner|tab))?\??$|^how much (?:should i )?tip (?:on|for) (?:a )?[$€£]?(?P<m>\d+(?:[.,]\d{1,2})?)"
                  r" ?(?:dollars?|euros?|bucks|pounds)?(?: (?:bill|check|meal|dinner))?\??$")
_EXAMS = re.compile(r"\b(?:exams?|tests?|finals|midterms)\b")
_SUBJECTS = ("math", "maths", "mathematics", "physics", "chemistry", "biology", "history", "geography", "english", "german",
             "french", "spanish", "latin", "economics", "statistics", "programming", "computer science", "philosophy",
             "psychology", "law", "medicine", "accounting", "finance", "art", "music", "literature", "sociology")
_STUDY_FIRST = re.compile(r"^(?:so |and |ok )?(?:which|what) (?:one |subject |exam )?should i (?:study|start with|learn|revise|do) first\??$|"
                          r"^where should i start\??$|^what should i start with\??$")
_WORST_AT = re.compile(r"^(?:i'?m|im|i am) (?:worst|the worst|really bad|so bad|terrible|weakest|bad) (?:at|in) (?P<s>[a-z ]+?)[.!]*$|"
                       r"^(?P<t>[a-z ]+?) is (?:my )?(?:worst|weakest|hardest)(?: subject| one)?[.!]*$")
_WFH = re.compile(r"\b(?:work(?:ing)? from home|wfh|remote(?:ly)?|home ?office|home all day)\b")
_MAYBE_SHOULD = re.compile(r"^(?:maybe|perhaps|i guess|i think|probably) i (?:should|could|need to|ought to) (?P<x>get out more|go out more|"
                           r"see people more|see friends more|call (?:a friend|someone|my \w+)|join (?:a |something|some)[a-z ]*|try [a-z ]+|"
                           r"get a (?:dog|cat|pet|hobby)|go to the gym|start [a-z ]+|meet (?:new )?people)[.!]*$")
_IDEAS_Q = re.compile(r"^(?:so |and |ok |but )?what (?:could|can|should) i (?:do|try)(?: about it)?\??$|^any ideas\??$")
_THEN_WHEN = re.compile(r"^(?:and |so )?when (?:was|did) (?:that|it|this)(?: happen)?\??$")
# German everyday context (battery 44)
_DE_MOVING = re.compile(r"^(?:ich )?(?:ziehe|zieh|ziehen|bin|sind) (?:bald |nächsten monat |nächste woche |im \w+ |demnächst |gerade |jetzt |neulich |vor kurzem )?"
                        r"(?:nach|in) (?P<x>[a-zäöüß][a-zäöüß -]{1,25}?)(?: gezogen| umgezogen)?(?: (?:um|nächsten monat|bald|im \w+))?[.!]*$")
_DE_REASON = re.compile(r"^(?:wegen (?:der |meiner |meines |dem |des )?(?P<r>arbeit|jobs?|neuen jobs?|studiums?|uni|liebe|freundin|freundes|"
                        r"partners?|partnerin|familie)|(?:für|fürs) (?:die |das |den |meinen |meine )?(?P<s>arbeit|job|studium|uni|liebe))[.!]*$")
_DE_AREAS = re.compile(r"^(?:kennst du |weißt du |hast du |gibt es |was sind )?(?:gute |schöne |beliebte |coole |empfehlenswerte )?(?:viertel|stadtteile|"
                       r"wohngegenden|gegenden|ecken)(?: zum wohnen)?(?: (?:dort|da|in (?P<p>[a-zäöüß ]+?)))?\??$|^wo (?:sollte|soll|kann) ich (?:dort |da )?"
                       r"(?:am besten )?wohnen(?: in (?P<q>[a-zäöüß ]+?))?\??$")
_DE_SIGHTS = re.compile(r"^(?:und )?was (?:sollte|soll|kann|muss) (?:ich|man) (?:mir |sich )?(?:dort |da |in (?P<p>[a-zäöüß ]+?) )?(?:unbedingt )?"
                        r"(?:ansehen|anschauen|besichtigen|sehen|machen)\??$|^was gibt es (?:dort|da|in (?P<q>[a-zäöüß ]+?)) zu sehen\??$")
_DE_FOOD = re.compile(r"^(?:und )?was (?:isst|ißt|esse|sollte ich|soll ich|muss ich)(?: man)?(?: (?:dort|da|in (?P<p>[a-zäöüß ]+?)))?(?: so| typischerweise)?"
                      r"(?: essen| probieren)?\??$|^(?:und )?was (?:ist|sind) (?:das |die )?typische[sn]? (?:essen|gerichte?|spezialitäten) "
                      r"(?:dort|da|in (?P<q>[a-zäöüß ]+?))\??$")
_DE_PET_SICK = re.compile(r"^(?:oh je,? |mist,? )?mein(?:e)? (?P<a>hund|katze|kater|hase|kaninchen|hamster|vogel|pferd) (?:frisst|frißt) (?:nicht mehr|nichts mehr|nicht|kaum)"
                          r"|^mein(?:e)? (?P<b>hund|katze|kater|hase|kaninchen|hamster|vogel|pferd) (?:ist|scheint) (?:krank|schlapp|nicht fit|verletzt)"
                          r"|^mein(?:e)? (?P<c>hund|katze|kater|hase|kaninchen|hamster|vogel|pferd) (?:hat sich|hat) (?:übergeben|erbrochen|durchfall)")
_DE_SINCE = re.compile(r"^(?:schon )?seit (?P<x>gestern|heute(?: morgen| früh)?|vorgestern|zwei tagen|2 tagen|drei tagen|3 tagen|einem tag|"
                       r"heute morgen|gestern abend)[.!]*$")
_DE_PET_NAME = re.compile(r"^(?:er|sie|es) heißt (?P<x>[a-zäöüß]+)[.!]*$|^(?:sein|ihr) name ist (?P<y>[a-zäöüß]+)[.!]*$")
_DE_VET = re.compile(r"^(?:soll|sollte|muss) ich (?:mit (?:ihm|ihr) )?(?:zum|zu einem|zur) (?:tierarzt|tierärztin|tierklinik)(?: gehen| fahren)?\??$")
_DE_CALL = re.compile(r"^(?:ok(?:ay)?,? |gut,? |alles klar,? )?(?:ich ruf(?:e)? (?:dort |da |gleich |jetzt |morgen )?an|ich geh(?:e)? (?:gleich |morgen )?hin|"
                      r"ich fahr(?:e)? (?:gleich )?hin|ich melde mich beim tierarzt)[.!]*$")
_DE_PCT = re.compile(r"^(?:und |was ist mit |und was ist mit )?(?P<a>\d+(?:[.,]\d+)?) ?(?:prozent|%)\??$")
_DE_DAYS = re.compile(r"^(?:wie viele|wieviele) tage (?:sind es |dauert es |hat es )?(?:noch )?bis (?:zu |zum |zur )?(?P<x>weihnachten|heiligabend|silvester|"
                      r"neujahr|halloween|valentinstag|nikolaus)\??$|^wie lange (?:ist es |dauert es )?noch bis (?P<y>weihnachten|heiligabend|silvester|neujahr|halloween)\??$")
_DE_HOLIDAYS = {"weihnachten": (12, 24), "heiligabend": (12, 24), "silvester": (12, 31), "neujahr": (1, 1), "halloween": (10, 31),
                "valentinstag": (2, 14), "nikolaus": (12, 6)}
_DE_FIX = re.compile(r"^(?:nein|nee|ne|oh|ups|sorry|warte|moment)[, ]+(?:eigentlich |doch |lieber |ich meinte |ich meine |doch lieber )?(?P<x>[a-zäöüß][a-zäöüß -]{1,25}?)"
                     r"(?: eigentlich| doch| lieber)?[.!]*$|^(?:eigentlich|ich meinte|ich meine) (?:doch )?(?:lieber )?(?P<y>[a-zäöüß][a-zäöüß -]{1,25}?)[.!]*$")
_DE_EVENT = re.compile(r"^(?:und )?wer hat (?:die |den |das )?(?P<e>wm|weltmeisterschaft|fußball-wm|fussball-wm|em|europameisterschaft|fußball-em|"
                       r"frauen-wm|olympischen spiele|olympia) ?(?P<y>\d{4})? ?(?:in \w+ )?gewonnen\??$|^wer wurde (?P<y2>\d{4}) (?P<e2>weltmeister|europameister)\??$|"
                       r"^wo (?:war|fand|fanden|waren) (?:die |das )?(?P<e3>wm|weltmeisterschaft|em|europameisterschaft|olympischen spiele|olympia) ?(?P<y3>\d{4})?"
                       r"(?: statt)?\??$")
_DE_EVENT_AGAIN = re.compile(r"^(?:und |was ist mit |und was ist mit )?(?:(?:der |die )?(?:wm|em) )?(?P<y>(?:19|20)\d\d)\??$")
_DE_EVENT_IT = re.compile(r"^(?:und )?wo (?:war|fand|waren|fanden) (?:die|sie|das|es)?(?: statt)?\??$|^(?:und )?wer hat (?:die|sie|es) gewonnen\??$")
_DE_BOT_HUMAN = re.compile(r"^bist du (?:ein |eine )?(?:mensch|roboter|ki|künstliche intelligenz|bot|maschine|echt|real|ein echter mensch|computer)\??$")
_DE_WFH = re.compile(r"\b(?:von zu hause|von zuhause|im homeoffice|im home office|homeoffice|remote)\b")
_DE_MAYBE = re.compile(r"^(?:vielleicht|wahrscheinlich|ich glaube,? ich) (?:sollte|könnte|muss) ich (?:mehr |öfter |mal )?(?:rausgehen|raus|unter leute|leute treffen|"
                       r"freunde treffen|jemanden anrufen|einem verein beitreten|einen kurs machen|sport machen)[a-zäöüß ]*[.!]*$|"
                       r"^(?:vielleicht|wahrscheinlich) sollte ich (?:mehr |öfter |mal )?[a-zäöüß ]+[.!]*$")
_DE_IDEAS = re.compile(r"^(?:und )?was (?:könnte|kann|sollte|soll) ich (?:da |dagegen )?(?:machen|tun)\??$|^hast du (?:ideen|vorschläge)\??$")
_DE_WORK_STRESS = re.compile(r"^(?:die )?arbeit (?:ist|wird) (?:einfach |gerade |echt |total |viel )?(?:zu viel|zu stressig|so stressig|so viel|kaum zu schaffen)[.!]*$|"
                             r"^ich habe? (?:einfach |gerade )?(?:zu viel|so viel) (?:arbeit|zu tun)[.!]*$")
_DE_BOSS = re.compile(r"^mein(?:e)? (?:chef|chefin|vorgesetzter|vorgesetzte|boss) (?:macht|übt) (?:mir |total |so |viel )?(?:druck|stress)[.!]*$")
_DE_EVENT_KIND = {"wm": "world cup", "weltmeisterschaft": "world cup", "fußball-wm": "world cup", "fussball-wm": "world cup",
                  "weltmeister": "world cup", "em": "euro", "europameisterschaft": "euro", "fußball-em": "euro", "europameister": "euro",
                  "frauen-wm": "women's world cup", "olympischen spiele": "summer olympics", "olympia": "summer olympics"}
_DE_EVENT_TITLE = {"world cup": "die WM {y}", "euro": "die EM {y}", "women's world cup": "die Frauen-WM {y}",
                   "summer olympics": "die Olympischen Sommerspiele {y}", "winter olympics": "die Olympischen Winterspiele {y}"}
# battery 45: interview at a company, "and its population?", the first book of a list, days until my birthday,
# night shifts, a betrayal and "should I text him?"
_INTERVIEW_AT = re.compile(r"^(?:it'?s|its|it is|that'?s|the interview is|the job is) (?:at|with|for) (?P<x>[a-z][a-z0-9 .&'-]{1,30}?)[.!]*$")
_WEAKNESS = re.compile(r"^(?:and |but |so )?(?:what if|how do i answer if|what do i say if|how should i answer if) (?:they|he|she|the interviewer) "
                       r"(?:ask|asks) (?:me )?(?:about )?(?:my |for my |what my )?(?P<x>weakness(?:es)?|strengths?|salary|why i want (?:the|this) job|"
                       r"why i left|where i see myself)(?: are)?\??$")
_LUCK = re.compile(r"^(?:thanks?|thank you|ty|thx|ok(?:ay)?)[,!.]* (?:and )?wish me luck[.!]*$")
_ITS_PROP = re.compile(r"^(?:and |what about |how about )?(?:its|the|their|it'?s) (?P<p>population|area|size|currency|official language|languages?|"
                       r"capital|president|head of state|prime minister|leader|national anthem|time zone|gdp)\??$")
_LIST_FIRST = re.compile(r"^(?:and |so |ok )?(?:who (?:wrote|directed|made|sings|sang)|who'?s the (?:author|director) of|what year (?:is|was)|when (?:was|did))"
                         r" (?:the )?(?P<o>first|second|third|last|1st|2nd|3rd) one(?: come out| written| made)?\??$")
_BDAY_DAYS = re.compile(r"^(?:and |so )?how (?:many|much) (?:days|weeks)(?: are)? (?:left )?(?:until|till|til|before|to) my birthday\??$|"
                        r"^how long (?:until|till|before) my birthday\??$")
_AGE_IF = re.compile(r"^(?:and |so )?how old (?:will|would) i (?:be|turn)(?: (?:on|at) my (?:next )?birthday)?(?: if i was born| if i'?m born| born)? in "
                     r"(?P<y>(?:19|20)\d\d)\??$|^i was born in (?P<z>(?:19|20)\d\d)[,.]? how old (?:am i|will i be)(?: on my birthday)?\??$")
_FOOD_TIME = re.compile(r"^(?:and |so |ok )?how long (?:does|do|will) (?:it|that|they|these|those|this) take(?: to (?:make|cook|prepare))?\??$")
_NIGHT_SHIFTS = re.compile(r"^(?:and |also |but )?i (?:work|do|am on|'m on|have) (?:(?:the |a lot of |mostly |lots of )?(?:night|late|early|double|12[- ]hour|long|weekend) "
                           r"shifts?|nights)(?: (?:mostly|a lot|now|these days|this month))?[.!]*$")
_SHIFTS_Q = re.compile(r"^(?:what|which) (?:shifts?|hours) do i (?:work|do|have)\??$|^do i work (?:nights|night shifts)\??$")
_TRUST_BETRAYED = re.compile(r"^(?:i )?(?:feel|felt|am|'m) (?:so |really |such an? |like an? |kinda )?(?:stupid|dumb|naive|idiot|fool|foolish|"
                             r"silly) (?:for|about) (?:trusting|believing|loving|staying with|not seeing it|missing the signs)"
                             r"(?: (?:him|her|them|it))?[.!]*$")
_TEXT_EX = re.compile(r"^(?:so |but |and )?(?:should|do|can) i (?:text|call|message|dm|contact|reach out to|write to|answer) (?:him|her|them|my ex)"
                      r"(?: (?:back|again|now|tonight|first))?\??$")
# battery 46: feeling low for a while, sarcasm, being told off, asking for help, an alarm
_BEEN_FEELING = re.compile(r"^(?:honestly,? |tbh,? |so,? )?(?:i'?ve|i have|ive) been (?:feeling |so |really |pretty |kinda |super |a bit |quite |very )*"
                           r"(?P<f>down|low|sad|depressed|lonely|anxious|stressed|exhausted|tired|overwhelmed|off|meh|empty|lost|"
                           r"unmotivated|burnt out|burned out|hopeless|numb|miserable)(?: (?:lately|recently|these days|all week|"
                           r"for (?:a while|weeks|days|months|ages)))?[.!]*$")
_DOWN_VAGUE = re.compile(r"^(?:nothing (?:specific|in particular|really)|i don'?t know,? )?(?:,? ?(?:just )?(?:everything|life|all of it|"
                         r"a bit of everything|it'?s just everything|everything really))[.!]*$|^nothing specific[.!]*$")
_TALK_HELPS = re.compile(r"^(?:maybe |i guess |i think )?(?:talking|talking about it|just talking) (?:helps|might help|could help|would help)[.!]*$")
_SARCASM = re.compile(r"^(?:yeah|oh|ah|yep|sure)[,!.]? (?:sure|right|totally|definitely)[,!.]* i (?:just )?(?:love|adore|enjoy|really love)"
                      r" (?P<x>[a-z0-9 ',-]{2,40}?)[.!]*(?: ?(?:lol|haha|🙄|😒))?$")
_SARC_MONDAY = re.compile(r"^(?:oh |ah |ugh,? )?(?:great|yay|fantastic|wonderful|perfect|lovely|awesome|brilliant)[,!.]* (?:another|it'?s|its) "
                          r"(?:monday|mondays)(?: again)?[.!]*$")
_WEEKEND_WISH = re.compile(r"^(?:i )?(?:just |really |so )?(?:want|need|wish it was|wish it were|can'?t wait for) (?:the |it to be )?(?:weekend|friday)"
                           r"(?: already)?[.!]*$")
_MISUNDERSTOOD = re.compile(r"^(?:you )?(?:didn'?t|did not|don'?t|do not) (?:even )?(?:understand|get|listen to) (?:me|what i (?:said|meant|mean)|it)"
                            r"(?: at all)?[.!]*$|^that'?s not what i (?:said|meant|asked)[.!]*$|^you'?re not (?:listening|getting it)[.!]*$")
_HELP_ASK = re.compile(r"^(?:hey,? |so,? |um,? )?(?:can|could|will|would) you (?:please )?help me(?: (?:with|out with) (?:something|a thing|stuff|this|"
                       r"a problem)| out)?(?: please)?\??$|^i need (?:your |some )?help(?: with something)?[.!?]*$")
_ALARM = re.compile(r"^(?:can|could|will) you (?:please )?(?:set|make|create|start) (?:an? |my )?(?:alarm|timer|countdown|stopwatch)"
                    r"(?: for [a-z0-9: ]+)?\??$|^(?:set|start) (?:an? )?(?:alarm|timer)(?: for [a-z0-9: ]+)?$")
_WHAT_ELSE = re.compile(r"^(?:ok |okay |and |so |cool,? )?what else(?: can you do)?\??$")
_DE_MISUNDERSTOOD = re.compile(r"^du (?:verstehst|kapierst) (?:mich |ja |echt |gar |überhaupt )*(?:nicht|nichts|gar nichts|überhaupt nichts)[.!]*$|"
                               r"^das (?:habe|hab) ich (?:so )?nicht gemeint[.!]*$")
_DE_SORRY = re.compile(r"^(?:sorry|entschuldigung|tut mir leid|sry)[,!.]* ?(?:das )?(?:war|ist) (?:nicht so|nicht böse) gemeint[.!]*$|"
                       r"^(?:sorry|entschuldige|entschuldigung|tut mir leid)(?:,? (?:das war gemein|ich war gemein|war blöd von mir))?[.!]*$")
_DE_HELP = re.compile(r"^(?:hey,? |du,? )?(?:kannst|könntest) du mir (?:bitte |mal )?(?:bei etwas |bei was |mit etwas )?helfen\??$|^ich brauche (?:deine |mal )?hilfe[.!?]*$")
# battery 47: a trip being planned, getting a cat, learning a language, a day off in German
_SEE_BARE = re.compile(r"^(?:so |and |ok )?what (?:should|can|could|do|must) (?:i|we) (?:see|visit|do|check out)(?: there| first| while i'?m there)?\??$|"
                       r"^(?:any )?(?:must-sees|sights|things to see)(?: there)?\??$")
_TRIP_DAYS = re.compile(r"^(?:just |only |it'?s |for )*(?:for )?(?P<n>\d+|two|three|four|five|six|seven|ten) (?:days|nights)(?: only)?[.!]*$")
_EXPENSIVE = re.compile(r"^(?:and |so |but )?(?:is (?:it|that|the city|\w+) (?:expensive|pricey|cheap|affordable)|how expensive is (?:it|\w+(?: \w+)?))\??$")
_VISA = re.compile(r"^(?:and |so )?(?:do|will|would) i need a visa(?: (?:for|to go to|to visit) (?:it|there|[a-z ]+?))?(?: as an? (?P<n>[a-z]+)(?: citizen)?)?\??$")
_LANG_THERE = re.compile(r"^(?:and |so )?what language(?:s)? do (?:they|people|you) speak(?: there)?\??$")
_EU = frozenset(("Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Denmark", "Estonia", "Finland", "France",
                 "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands",
                 "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden"))
_EU_NATIONAL = re.compile(r"\b(?:german|french|italian|spanish|austrian|dutch|belgian|portuguese|greek|irish|polish|swedish|danish|finnish|"
                          r"czech|hungarian|croatian|romanian|bulgarian|slovak|slovenian|luxembourgish|maltese|cypriot|estonian|latvian|"
                          r"lithuanian|eu citizen|european)\b")
_GET_PET = re.compile(r"\b(?:thinking (?:about|of) getting|want to get|planning to get|going to get|getting) an? (?P<p>cat|kitten|dog|puppy)\b")
_SMALL_FLAT = re.compile(r"^(?:but |and )?i (?:live in|have|only have) (?:a |an )?(?:small|tiny|little) (?:apartment|flat|place|studio)[.!]*$")
_IS_OK = re.compile(r"^(?:is that|would that be|is it) (?:ok(?:ay)?|fine|a problem|alright)(?: for (?:a|the) (?:cat|dog))?\??$")
_WHAT_NEED = re.compile(r"^(?:and |so )?what (?:do|will|would) i need(?: for (?:it|a cat|a dog|a kitten|a puppy))?\??$")
_NAME_IT = re.compile(r"^(?:and |so )?what should i (?:name|call) (?:it|him|her|them|the (?:cat|dog|kitten|puppy))\??$|^(?:any )?name ideas\??$")
_LEARN_TIME = re.compile(r"^(?:and |so )?how long (?:does it|will it|would it) take(?: to (?:learn (?:it|that)|get good|become fluent))?\??$")
# battery 48: a headache, spending, a colleague taking credit, a gift from what someone likes, two job offers
_ACHE = re.compile(r"\b(?:my head (?:hurts|is killing me|is pounding)|(?:i )?(?:have|got|'ve got) (?:a |such a |a bad |a terrible )?headache|"
                   r"headache)\b")
_SINCE = re.compile(r"^(?:it'?s been |been |just |only )?(?:since|for) (?P<x>this morning|last night|yesterday|the morning|lunch|hours|"
                    r"two days|2 days|a few hours|an hour|all day|this afternoon)[.!]*$")
_LOW_WATER = re.compile(r"^(?:i )?(?:didn'?t|did not|haven'?t|have not) (?:drink|drunk|had) (?:much|enough|any)? ?(?:water|fluids|anything)"
                        r"(?: today)?[.!]*$|^(?:i'?m|im|i might be|maybe i'?m) (?:a bit |probably )?dehydrated[.!]*$")
_MEDS = re.compile(r"^(?:should|can|could) i take (?:something|anything|a (?:painkiller|pill|tablet)|an? (?:ibuprofen|aspirin|paracetamol|advil|"
                   r"tylenol))(?: for (?:it|that))?\??$")
_WILL_REST = re.compile(r"^(?:ok(?:ay)?,? |thanks,? |ok thanks,? |good idea,? )*(?:i'?ll|ill|i will|gonna) (?:drink (?:some|more) water|"
                        r"lie down|rest|take (?:a nap|a break|it easy|something)|go to bed|get some sleep)(?: (?:then|now|first))?[.!]*$")
_SPEND_ON = re.compile(r"^(?:but |and |i think )?i (?:spend|waste|blow) (?:way |far )?(?:too much|so much|a lot) (?:money )?on (?P<x>[a-z ]{3,25}?)[.!]*$")
_BUDGET_RULE = re.compile(r"^(?:what'?s|what is|is there) (?:a )?(?:good |simple |common )?budget(?:ing)? (?:rule|method|plan|formula)\??$|"
                          r"^how (?:should|do) i split my (?:salary|income|money)\??$")
_CREDIT = re.compile(r"\bmy (?P<n>colleague|coworker|co-worker|teammate|boss|manager) (?:keeps |always |just )?(?:taking|took|takes|steals|stole|stealing)"
                     r" (?:the )?credit\b")
_AGAIN = re.compile(r"^(?:and )?it (?:happened|did it) again(?: today| this week| yesterday)?[.!]*$|^(?:and )?(?:he|she|they) did it again[.!]*$")
_TALK_BOSS = re.compile(r"^(?:so )?(?:should|do) i (?:talk|speak) to (?:my |the )?(?:boss|manager|supervisor|hr)(?: about (?:it|this))?\??$")
_BRING_UP = re.compile(r"^(?:but |and |so )?how (?:do|should|would|can) i (?:bring it up|say it|start|phrase it|approach (?:it|this|him|her))\??$|"
                       r"^what (?:do|should) i say\??$")
_GIFT_Q = re.compile(r"^(?:so |and )?(?:what should i (?:get|buy|give) (?:her|him|them)|(?:any )?gift ideas(?: for (?:her|him|them))?|"
                     r"what (?:could|can) i (?:get|give) (?:her|him|them))\??$")
_UNDER = re.compile(r"^(?:something |ideally |preferably |but )?(?:under|below|less than|max|up to|no more than) (?P<x>[$€£]?\d+ ?(?:euros?|dollars?|bucks|pounds|€|\$)?)[.!]*$")
_DECIDE = re.compile(r"^i (?:can'?t|cannot|can not|don'?t know how to) (?:decide|choose|pick) between (?:two|2) (?:jobs?|job offers|offers|options|apartments|flats|cities)[.!]*$")
_TRADEOFF = re.compile(r"^(?:well,? )?(?:one|the first) (?:pays|is|has|offers) .+,? (?:and )?the other (?:is|has|pays|offers) .+$")
_WOULD_YOU = re.compile(r"^(?:so )?what would you (?:do|choose|pick)\??$|^which (?:one )?would you (?:take|choose|pick)\??$")
_FEMALE_NOUNS = frozenset(("sister", "mom", "mum", "mother", "girlfriend", "wife", "daughter", "aunt", "grandma", "grandmother", "niece",
                           "fiancée"))
_MALE_NOUNS = frozenset(("brother", "dad", "father", "boyfriend", "husband", "son", "uncle", "grandpa", "grandfather", "nephew", "fiancé"))
_DE_ACHE = re.compile(r"^(?:ich )?(?:hab|habe) (?:so |echt |total )?(?:kopfschmerzen|kopfweh|migräne)[.!]*$|^mein kopf tut (?:so )?weh[.!]*$")
_DE_ACHE_SINCE = re.compile(r"^(?:schon )?seit (?P<x>heute morgen|heute früh|gestern|gestern abend|stunden|dem aufstehen|mittag)[.!]*$")
_DE_MEDS = re.compile(r"^(?:soll|sollte|kann) ich (?:was|etwas|eine tablette|ibuprofen|paracetamol|aspirin|ein schmerzmittel) nehmen\??$")
_DE_BDAY_PERSON = re.compile(r"^mein(?:e)? (?P<p>freundin|frau|mutter|mama|schwester|beste freundin|kollegin|tochter|oma) hat (?:nächste woche|morgen|bald|"
                             r"am \w+|übermorgen|diese woche) geburtstag[.!]*$")
_DE_LIKES = re.compile(r"^(?:sie|er) (?P<x>liest|kocht|reist|malt|mag|liebt|trinkt) (?:gern|gerne|so gern|total gern|viel)?(?: (?P<y>[a-zäöüß ]+?))?[.!]*$")
_DE_GIFT_Q = re.compile(r"^(?:und )?was (?:soll|sollte|kann|könnte) ich (?:ihr|ihm) schenken\??$|^(?:hast du )?geschenkideen\??$")
# battery 49: starting to run, a nervous child before a test, guests for dinner, adding to and ticking off reminders
_RUN_START = re.compile(r"^(?:i )?(?:want to|wanna|would like to|am going to|'m going to|plan to) (?:start|get into|begin) (?:running|jogging)[.!]*$")
_NEVER_SPORT = re.compile(r"^(?:but |well,? )?i(?:'ve| have)? (?:never|not) (?:really )?(?:done|did|do) (?:any |much )?(?:sport|sports|exercise)(?: before| really)?[.!]*$|"
                          r"^i'?m (?:a )?(?:total |complete )?beginner[.!]*$")
_RUN_OFTEN = re.compile(r"^(?:and |so )?how (?:often|many times a week) should i (?:run|go running|jog)\??$")
_RUN_FAR = re.compile(r"^(?:and |so )?how (?:far|long|much)(?: should i (?:run|go))?\??$")
_RUN_SHOES = re.compile(r"^(?:and |so )?what (?:shoes|gear|clothes|equipment|kit) (?:do|should) i (?:need|get|buy|wear)\??$")
_KID = re.compile(r"\bmy (?P<k>son|daughter|kid|child|boy|girl|little one|nephew|niece) (?:has|have|'s got|is having|is taking) (?:a |an |his |her )?"
                  r"(?:\w+ )?(?:test|exam|quiz|presentation|recital|match|game)")
_KID_NERVOUS = re.compile(r"^(?:and |but )?(?:he'?s|she'?s|he is|she is|they'?re) (?:really |so |super |very |a bit |kinda )?(?:nervous|anxious|scared|"
                          r"stressed|worried)(?: about it)?[.!]*$")
_KID_HELP = re.compile(r"^(?:so |and )?how (?:can|do|could|should) i help (?:him|her|them)\??$|^what (?:can|should) i do(?: for (?:him|her))?\??$")
_KID_AGE = re.compile(r"^(?:he'?s|she'?s|he is|she is|they'?re) (?P<n>\d{1,2})(?: years old)?[.!]*$")
_GUESTS = re.compile(r"\b(?:i have|i'?ve got|we have|having|we'?re having|i'?m having) (?:some )?(?:friends|people|guests|family) (?:coming )?(?:over|round)"
                     r"(?: for (?:dinner|lunch|food))?\b|\bdinner party\b")
_GUEST_N = re.compile(r"^(?:about |around |maybe |like )?(?P<n>\d{1,2}|two|three|four|five|six|seven|eight|ten|twelve) (?:people|guests|of us|persons)?[.!]*$")
_ONE_VEGAN = re.compile(r"^(?:and |but )?(?:one|two|some|a friend|one of them|my friend) (?:is|are|of them is) (?P<d>vegan|vegetarian|gluten[- ]free|"
                        r"lactose intolerant|allergic to nuts)[.!]*$")
_DESSERT = re.compile(r"^(?:and |what about |how about )?(?:for |a )?dessert\??$|^(?:and )?what (?:about|for) dessert\??$")
_TODO_MORE = re.compile(r"^(?:(?:and|also|oh and|plus) (?:to |that i need to )?|to |that i (?:also )?need to )(?P<x>[a-z][a-z ,'-]{2,60})[.!]*$")
_DID_IT = re.compile(r"^(?:ok(?:ay)?,? |done,? |so )?i (?:just |already |finally )?(?P<v>called|bought|sent|paid|booked|cleaned|finished|emailed|"
                     r"texted|picked up|made|fixed|washed|cooked|wrote|replied to|returned|cancelled|renewed|did) (?P<o>[a-z ]{0,30}?)[.!]*$")
_PAST_BASE = {"called": "call", "bought": "buy", "sent": "send", "paid": "pay", "booked": "book", "cleaned": "clean", "finished": "finish",
              "emailed": "email", "texted": "text", "picked up": "pick up", "made": "make", "fixed": "fix", "washed": "wash",
              "cooked": "cook", "wrote": "write", "replied to": "reply to", "returned": "return", "cancelled": "cancel",
              "renewed": "renew", "did": "do"}
_DE_RUN = re.compile(r"^(?:ich )?(?:will|möchte|werde) (?:mit dem |wieder mit dem |mit )?(?:joggen|laufen|rennen) anfangen[.!]*$|^ich fang(?:e)? (?:mit dem )?(?:joggen|laufen) an[.!]*$")
_DE_RUN_OFTEN = re.compile(r"^(?:und )?wie oft (?:soll|sollte) ich (?:laufen|joggen)(?: gehen)?\??$")
_DE_RUN_GO = re.compile(r"^(?:danke,? |ok,? |gut,? )*ich fang(?:e)? (?:morgen|heute|gleich|am montag) an[.!]*$")
_DE_GUESTS = re.compile(r"^wir (?:kriegen|bekommen|haben) (?:heute abend |morgen |am wochenende )?(?:besuch|gäste)[.!]*$|^(?:heute abend )?kommen (?:freunde|gäste) zum essen[.!]*$")
_DE_VEGGIE = re.compile(r"^(?:und )?(?:einer|eine|jemand|zwei) (?:davon )?(?:ist|sind|isst) (?:vegetarier(?:in)?|vegan|veganer(?:in)?|kein fleisch)[.!]*$")
_DE_DESSERT = re.compile(r"^(?:und )?(?:als |zum )?(?:nachtisch|dessert|nachspeise)\??$|^(?:und )?was (?:gibt'?s|mache ich) (?:als|zum) (?:nachtisch|dessert)\??$")
# battery 50: a long week, deadlines, almost Friday, ENGRAMM's weekend, a hike
_LONG_WEEK = re.compile(r"^(?:ugh,? |man,? |honestly,? )?(?:it'?s|its|it has|this has|this) been (?:a |such a |one )?(?:really |very |super |so )?"
                        r"(?:long|rough|tough|crazy|busy|hard|exhausting|hectic|stressful) (?:week|day|month)[.!]*$")
_DEADLINES = re.compile(r"^(?:yeah,? |yes,? |ugh,? )?(?:so many|lots of|a lot of|too many|tons of|endless) (?:deadlines|meetings|projects|emails)"
                        r"(?: at work)?[.!]*$|^(?:yeah,? )?(?:too much|so much|lots of) work[.!]*$")
_ALMOST_WE = re.compile(r"^(?:but |at least |well,? |luckily,? )?(?:tomorrow is friday|it'?s (?:almost|nearly|finally) (?:the )?(?:weekend|friday)|tgif|"
                        r"(?:only )?one more day(?: until the weekend)?|friday tomorrow)[.!]*$")
_BOT_WEEKEND = re.compile(r"^(?:and |so )?(?:(?:do|what do) you have )?(?:any )?plans (?:for|this) (?:the )?weekend(?: lol| haha)?\??"
                          r"(?:,? (?:oh )?wait,? (?:you'?re|you are)(?: an?)?(?: bot| ai| computer)?(?: lol| haha)?)?$|"
                          r"^what are you doing (?:this|for the) weekend\??$")
_HIKE_PLAN = re.compile(r"^(?:i )?(?:might|will|want to|wanna|'m going to|am going to|plan to|'ll|think i'll|'m gonna|am gonna) "
                        r"(?:go (?:hiking|on a hike|for a hike)|hike)(?: (?:this weekend|tomorrow|on saturday|on sunday))?[.!]*$")
_HIKE_TIPS = re.compile(r"^(?:any )?(?:good )?(?:hiking tips|tips for (?:hiking|a hike|my hike))\??$")
_BRING = re.compile(r"^(?:and |so )?what (?:should|do) i (?:bring|pack|take|carry)(?: with me)?\??$")
_HOW_WATER = re.compile(r"^(?:and |so )?how much water(?: should i (?:bring|take|carry))?\??$")
# battery 51: the long German conversation
_DE_IM = re.compile(r"^(?:hi |hey |hallo |moin |servus )?(?:ich bin|ich bins|bin) (?P<x>[a-zäöüß]{2,15})[.!]*$")
_COMMON_FIRST_NAMES = frozenset("""tom tim max paul felix leon lukas lucas jonas finn luca ben elias noah julian jan niklas david moritz
philipp simon alexander daniel michael thomas andreas stefan markus christian peter frank jens sven tobias florian sebastian
matthias martin oliver kai lars nils erik fabian dominik marcel patrick dennis kevin marco robin hannes anton emil oskar karl
otto theo leo ole henrik jakob johannes mia emma hanna hannah sofia sophia lea lena anna laura sarah julia lisa marie maria
katharina johanna clara klara lara luisa louisa emily nina sandra nicole jana sabine petra claudia andrea stefanie julia
melanie anja kathrin christina vanessa jessica jennifer franziska carina sophie charlotte amelie ella frieda ida mila paula
greta helena alina vivien selina jasmin jule merle marlene ronja finja mara pia tina eva ute heike karin monika susanne
john james robert william richard joseph mark steven ryan jack harry george oscar charlie liam ethan mason alex sam chris
mike nick adam luke matt josh dan jake olivia ava isabella amelia grace chloe zoe ellie lily ruby kate rose alice jane
emily""".split())
_DE_NOT_NAME = frozenset(("müde", "fertig", "hier", "da", "zurück", "wach", "krank", "gesund", "glücklich", "traurig", "sauer", "wütend",
                          "gestresst", "happy", "froh", "bereit", "dran", "unterwegs", "zuhause", "online", "gespannt", "nervös",
                          "verliebt", "single", "vegetarier", "vegetarierin", "veganer", "veganerin", "vegan", "student", "studentin",
                          "schwanger", "satt", "hungrig", "durstig", "pleite", "gut", "schlecht", "ok", "okay", "neu", "alt", "allein",
                          "einsam", "erkältet", "zufrieden", "aufgeregt", "überfordert", "erschöpft", "genervt", "gelangweilt", "frei",
                          "wieder", "jetzt", "auch", "so", "ganz", "echt", "nicht", "kein", "keine", "noch", "schon", "fit", "raus"))
_DE_LONG_WEEK = re.compile(r"^(?:puh,? |boah,? |ach,? )?(?:war|das war|es war|ist|hatte) (?:eine |ne |echt eine |so eine )?(?:lange|harte|anstrengende|stressige|"
                           r"krasse|volle) (?:woche|tag|monat)[.!]*$")
_DE_DEADLINES = re.compile(r"^(?:ja,? |jo,? )?(?:viele|so viele|zu viele|lauter) (?:deadlines|termine|meetings|abgaben)[.!]*$|^(?:ja,? )?(?:zu )?viel arbeit[.!]*$")
_DE_ALMOST_WE = re.compile(r"^(?:aber |zum glück |immerhin )?(?:morgen ist (?:schon )?freitag|(?:bald|fast) (?:ist )?wochenende|endlich (?:bald )?wochenende)[.!]*$")
_DE_BOT_WE = re.compile(r"^(?:und )?(?:hast|machst) du (?:was|etwas|pläne|irgendwelche pläne)(?: vor)? (?:fürs|für das|am|dieses) wochenende(?: vor)?\??$")
_DE_HIKE = re.compile(r"^(?:ich )?(?:geh|gehe|will|möchte|werde|wollte) (?:vielleicht |wahrscheinlich |morgen |am wochenende )*(?:wandern|eine wanderung machen|"
                      r"in die berge)(?: gehen)?[.!]*$")
_DE_TIPS = re.compile(r"^(?:hast du |irgendwelche |ein paar )?tipps\??$")
_DE_BRING = re.compile(r"^(?:und )?was (?:soll|sollte|muss) ich mitnehmen\??$")
_DE_WATER = re.compile(r"^(?:und )?wie viel wasser(?: soll ich mitnehmen)?\??$")
_DE_COST = re.compile(r"^(?:und )?(?:ist (?:es|das|die stadt) (?:teuer|günstig|billig)|wie teuer ist (?:es|das) (?:dort|da)?)\??$")
_DE_RECAP = re.compile(r"^(?:und )?(?:worüber|über was) haben wir (?:geredet|gesprochen|uns unterhalten)\??$")
_DE_COMPLIMENT = re.compile(r"^du bist (?:ein |eine )?(?:echt |richtig |wirklich |so |sehr )?(?:guter zuhörer|gute zuhörerin|lieb|nett|toll|super|klasse|"
                            r"schlau|klug|witzig|süß|hilfreich|der beste|die beste)[.!]*$")
_RECAP_DE = {"things about you": "Sachen über dich", "how you're doing": "wie es dir geht", "what to cook": "Kochen", "jokes": "Witze",
             "fun facts": "Fun Facts", "books": "Bücher", "films": "Filme", "music": "Musik", "games": "Spiele",
             "things to do": "Unternehmungen", "travel": "Reisen", "sleep": "Schlaf", "some ideas": "ein paar Ideen"}
# battery 53: words, calories, nutrition, time zones
_DEFINE = re.compile(r"^(?:and )?(?:what does|what do) [\"“']?(?P<w>[a-z-]{3,25})[\"”']? mean\??$|^(?:what is the meaning of|define|"
                     r"meaning of|definition of) [\"“']?(?P<v>[a-z-]{3,25})[\"”']?\??$")
_IN_SENTENCE = re.compile(r"^(?:can you )?(?:use|put) (?:it|that|the word) in a sentence(?: please)?\??$|^(?:give me |any )?(?:an )?example(?: sentence)?\??$")
_ANTONYM = re.compile(r"^(?:and )?what(?:'s| is) (?:the )?(?:opposite|antonym) (?:of|for) [\"“']?(?P<w>[a-z-]{2,25})[\"”']?\??$|^(?:the )?opposite of "
                      r"(?P<v>[a-z-]{2,25})\??$")
_KCAL = re.compile(r"^(?:and )?how many (?:calories|kcal|cals) (?:are )?(?:in|does) (?:a |an |one |the )?(?P<f>[a-z ]{2,25}?)(?: have| contain)?\??$")
_KCAL_LOT = re.compile(r"^(?:and )?is (?:that|it) (?:a lot|much|too much|a lot of calories|bad)\??$")
_RICE_PASTA = re.compile(r"^(?:what'?s|what is|which is) healthier,? (?:rice or pasta|pasta or rice)\??$")
_PROTEIN = re.compile(r"^how much protein (?:do i|should i|does a person|do you|do people) (?:need|eat|have)(?: per day| a day| daily)?\??$")
_TZ = re.compile(r"^(?:and )?what time ?zone is (?P<p>[a-z ]{2,25}?) in\??$|^what(?:'s| is) the time ?zone (?:of|in) (?P<q>[a-z ]{2,25}?)\??$")
_TIME_THERE = re.compile(r"^(?:and )?what time is it there(?: now| right now)?\??$")
_TIME_AND = re.compile(r"^(?:and|what about|how about)(?: in)? (?P<p>[a-z ]{2,25}?)\??$")
_HOURS_AHEAD = re.compile(r"^(?:and )?how many hours (?:ahead|behind|difference)(?: is (?:that|it|it there))?\??$|^what(?:'s| is) the time difference\??$")
_DE_CONVERT = re.compile(r"^wie viele? (?P<to>kilometer|km|meilen|kilo|kilogramm|pfund|grad fahrenheit|fahrenheit|grad celsius|celsius|liter|zentimeter|zoll|"
                         r"meter|fuß) (?:sind|ergeben|entsprechen) (?P<n>\d+(?:[.,]\d+)?) (?P<fr>meilen|kilometer|km|pfund|kilo|kilogramm|grad celsius|celsius|"
                         r"grad fahrenheit|fahrenheit|gallonen|zoll|fuß|meter|zentimeter)\??$")
_DE_UNIT = {"kilometer": "km", "km": "km", "meilen": "miles", "kilo": "kg", "kilogramm": "kg", "pfund": "pounds", "grad fahrenheit": "fahrenheit",
            "fahrenheit": "fahrenheit", "grad celsius": "celsius", "celsius": "celsius", "liter": "liters", "gallonen": "gallons",
            "zentimeter": "cm", "zoll": "inches", "meter": "meters", "fuß": "feet"}
_DE_DEFINE = re.compile(r"^was (?:heißt|bedeutet|heisst) [\"„']?(?P<w>[a-zäöüß-]{3,25})[\"“']?\??$")
_DE_KCAL = re.compile(r"^wie viele kalorien (?:hat|haben) (?:eine?n? |ein )?(?P<f>[a-zäöüß ]{2,25}?)\??$")
_DE_FOOD_EN = {"banane": "banana", "apfel": "apple", "ei": "egg", "avocado": "avocado", "orange": "orange", "scheibe brot": "slice of bread",
               "brot": "bread", "croissant": "croissant", "pizza": "pizza", "kartoffel": "potato", "schokolade": "chocolate", "bier": "beer",
               "glas wein": "glass of wine", "wein": "wine", "kaffee": "coffee", "latte": "latte", "joghurt": "yogurt", "lachs": "salmon",
               "cola": "cola", "donut": "donut"}
_DE_FOOD_SHOWN = {"banana": "einer mittelgroßen Banane", "apple": "einem mittelgroßen Apfel", "egg": "einem großen Ei", "avocado": "einer ganzen Avocado",
                  "orange": "einer Orange", "slice of bread": "einer Scheibe Brot", "bread": "einer Scheibe Brot", "croissant": "einem Croissant",
                  "pizza": "einem Stück Käsepizza", "potato": "einer Ofenkartoffel", "chocolate": "einer Tafel Milchschokolade (40 g)",
                  "beer": "einem Bier (0,33 l)", "glass of wine": "einem Glas Wein (150 ml)", "wine": "einem Glas Wein (150 ml)",
                  "coffee": "einem schwarzen Kaffee", "latte": "einem großen Latte", "yogurt": "einem Becher Naturjoghurt",
                  "salmon": "100 g Lachs", "cola": "einer Dose Cola (0,33 l)", "donut": "einem Donut"}
# battery 54: other people's news (engaged, a baby, a driving test), a fight with a friend, parents divorcing
_YEARS_TOGETHER = re.compile(r"^(?:to |with )?(?:her|his|their) (?:boyfriend|girlfriend|partner) of (?P<n>\d+|two|three|four|five|six|seven|eight|ten) years[.!]*$")
_WEDDING_WHEN = re.compile(r"^(?:and )?the wedding(?: is| will be)? (?:next|this) (?:summer|spring|autumn|fall|winter|year|month)[.!]*$")
_HONOUR_WHAT = re.compile(r"^(?:so |and )?what (?:do|does|will) (?:i|a maid of honou?r|a best man) (?:have to|need to|usually)? ?do\??$")
_BABY = re.compile(r"\bmy (?:best friend|friend|sister|brother|cousin|colleague)(?:'s wife)? (?:is having|is expecting|'s having|'s expecting|is pregnant)")
_BABY_SEX = re.compile(r"^(?:it'?s|its) a (?P<s>girl|boy)[.!]*$")
_PASSED = re.compile(r"\bi (?:passed|just passed|finally passed) my (?:driving|driver'?s) (?:test|exam|license)\b")
_FIRST_TRY = re.compile(r"^(?:on (?:the|my) )?first (?:try|time|attempt|go)[.!]*$")
_NEED_CAR = re.compile(r"^(?:thanks!? |thank you!? )?(?:now )?i (?:need|want) (?:a|to get a|to buy a) car(?: lol| haha)?[.!]*$")
_FIRST_CAR = re.compile(r"^(?:any )?tips (?:for|on) (?:a |my )?first car\??$|^what (?:should i|to) look (?:for|out for) (?:in|when buying) a (?:first |used )?car\??$")
_FIGHT = re.compile(r"\bi (?:had|have had|got into) (?:a |an )?(?:fight|argument|row) with my (?:best friend|friend|sister|brother|mom|mum|dad|partner)\b")
_SHE_SAID = re.compile(r"^(?:she|he|they) said (?:that )?i (?:never|don'?t|always) .+$")
_MAYBE_RIGHT = re.compile(r"^(?:but )?(?:maybe|perhaps|i guess|honestly,?) (?:she'?s|he'?s|they'?re) (?:right|not wrong)[.!]*$")
_APOLOGIZE = re.compile(r"^(?:so |but )?how (?:do|should|can) i (?:apologi[sz]e|say sorry|make it up to (?:her|him|them))\??$")
_CALL_THEM = re.compile(r"^(?:ok(?:ay)?,? )?(?:i'?ll|ill|i will|gonna) (?:call|text|talk to|message) (?:her|him|them)(?: (?:now|tonight|tomorrow|later))?[.!]*$")
_DIVORCE = re.compile(r"\bmy parents (?:are getting|got|are) (?:a )?divorc(?:ed|e|ing)\b|\bmy parents (?:are splitting up|split up|separated)\b")
_NOT_KID = re.compile(r"^(?:i'?m|im|i am) (?P<n>\d{2})(?:,)? (?:so )?(?:it'?s not like i'?m a (?:kid|child)|i'?m not a (?:kid|child))[.!]*$")
_STILL_HURTS = re.compile(r"^(?:but )?(?:it )?still hurts[.!]*$|^(?:but )?it still (?:hurts|sucks|feels bad)[.!]*$")
_DE_WEDDING_WHEN = re.compile(r"^(?:und )?die hochzeit ist (?:nächsten|diesen|im) (?:sommer|frühling|herbst|winter|jahr|monat)[.!]*$")
_DE_TRAUZEUGE = re.compile(r"^(?:und )?ich (?:bin|werde) (?:die |der )?(?:trauzeugin|trauzeuge|brautjungfer)(?: sein)?[.!]*$")
_DE_FIRST_TRY = re.compile(r"^(?:und )?(?:beim|im) ersten (?:mal|anlauf|versuch)[.!]*$")
_DE_FIGHT = re.compile(r"\bich (?:hab|habe) mich mit (?:meiner|meinem) (?:besten freundin|besten freund|freundin|freund|schwester|bruder|mutter|vater) (?:gestritten|verkracht)\b")
_DE_APOLOGIZE = re.compile(r"^(?:und )?wie (?:entschuldige ich mich|soll ich mich entschuldigen|kann ich mich entschuldigen)\??$")
_DE_CALL_FRIEND = re.compile(r"^(?:ok(?:ay)?,? |gut,? )?ich (?:ruf|rufe|schreib|schreibe) (?:sie|ihn|ihr|ihm) (?:gleich |jetzt |morgen |heute )?(?:an)?[.!]*$")
# battery 55: talking about a film, a book or music: the work becomes the topic, "it" is the work
_MEDIA = re.compile(r"^(?:i'?ve been |i have been |i'?m |i am |i )?(?:just |finally |recently )?(?P<v>listening to|into|finished reading|finished|started reading|"
                    r"started|reading|read|re-?read|watched|saw|watching|loved|love|liked|really liked|really loved)"
                    r" (?:a lot of |lots of |so much |the book |the movie |the film )?(?P<x>[a-z0-9][a-z0-9 '&.:-]{1,40}?)"
                    r"(?: lately| recently| these days| right now| again| last night| yesterday| today)?[.!]*$")
_SEEN = re.compile(r"^(?:have|did) you (?:ever )?(?:seen|watched|see|watch|read|heard of) (?P<x>[a-z0-9][a-z0-9 '&.:-]{1,40}?)\??$")
_IT_Q = re.compile(r"^(?:and |so )?(?:who|when|where|what year|how long|how many|what) [a-z ]*\bit\b[a-z ]*\??$")
_SIMILAR = re.compile(r"^(?:any|some) (?:similar|other|more) (?P<k>movies|films|books|shows|series|artists|bands|songs|music)(?: like (?:it|that|this))?\??$|"
                      r"^(?:anything|something) (?:similar|like (?:it|that))\??$")
_WORK_ALIAS = {"1984": "Nineteen Eighty-Four"}
_WORK_TYPES = {"book": ("Book", "Novel", "WrittenWork", "Poem"), "film": ("Film", "TelevisionShow", "TelevisionSeries"),
               "music": ("Band", "MusicalArtist", "Person", "Album", "Single", "Group")}
_SCORE = re.compile(r"^(?P<t>[a-z][a-z .]{1,25}?) (?:won|beat [a-z .]+?|lost|drew)(?: (?P<s>\d+ ?[-–:] ?\d+))?(?: (?:last night|yesterday|today|again))?[.!]*$")
_BEST_PLAYER = re.compile(r"^who(?:'s| is) the best (?:football |soccer )?player in the world\??$|^who(?:'s| is) the goat\??$")
_DEPRESSING = re.compile(r"^(?:it was |it'?s |but it was |that was )(?:so |really |pretty |quite |kinda )?(?:depressing|dark|bleak|sad|heavy|disturbing|scary|"
                         r"creepy|intense)[.!]*$")
_DE_SEEN = re.compile(r"^(?:hast|kennst) du (?:schon )?(?P<x>[a-z0-9][a-z0-9 '&.:-]{1,40}?)(?: gesehen| gelesen| gehört)?\??$")
_WEAR = re.compile(r"^(?:(?:and|so|ok|okay|hmm|fine|alright|cool|sure)[.,!]? )?what (?:should|do|can|could) i wear(?: (?:to|for|on|in) "
                   r"(?:the |a |my |an )?(?P<x>[a-z ]+?))?(?: tomorrow| today| tonight)?\??$")
_OCCASIONS = [("interview", re.compile(r"\binterview")), ("wedding", re.compile(r"\bwedding|\bmarr")),
              ("date", re.compile(r"\bdate\b|\bfirst date")), ("dinner", re.compile(r"\bdinner|\bcelebrat|\brestaurant|\bparty|going out")),
              ("funeral", re.compile(r"\bfuneral")), ("office", re.compile(r"\boffice|\bfirst day|\bwork\b")),
              ("rain", re.compile(r"\brain|\bwet\b|\bstorm")), ("snow", re.compile(r"\bsnow")),
              ("cold", re.compile(r"\bcold\b|\bwinter|\bfreezing|\bchilly")),
              ("hot", re.compile(r"\bhot\b|\bheat\b|\bsummer|\bbeach|\bwarm\b"))]
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
    (re.compile(r"\b(?:i'?m |im |i am |kinda |so |really |pretty )*(?:hungry|starving|peckish)\b"), "talk_hungry"),
    (re.compile(r"^(?:just )?(?:chillin'?g?|relaxing|chilling at home|lazy day|having a lazy day)(?: tbh| lol)?$"), "talk_chill"),
    (re.compile(r"^(?:that|it|dinner|lunch|the food) (?:was|tasted) (?:so |really |very )?(?:good|great|delicious|tasty|amazing|yummy|nice)\b"), "talk_tasty"),
    (re.compile(r"\bi had (?:a |the )?(?:really |very |super )?(?:weird|strange|crazy|bad|good|funny|scary|wild|odd) dream\b"), "talk_dream"),
    (re.compile(r"^(?:it'?s|its|it is|it has been|it'?s been) (?:raining|pouring|snowing|so (?:cold|grey|gray|windy)|freezing)\b|"
                r"\b(?:rain|rainy|grey|gray) (?:all day|day|weather)\b"), "talk_weather_bad"),
    (re.compile(r"^(?:it'?s|its|it is) (?:so |really )?(?:sunny|warm|beautiful|lovely|gorgeous) (?:outside|today|out)\b"), "talk_weather_good"),
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
_TALK_FIRST = re.compile(r"\b(?:hungry|starving|peckish|chillin'?g?|relaxing|lazy|good|great|delicious|tasty|yummy|dream|raining|pouring|snowing|rain|rainy|grey|gray|sunny|freezing|start|bed|sleeping|purring|cuddling|napping|curled|watch|going out|going to|heading out|off to|meeting|tell you|let you know|keep you posted|miss(?:ing)?|try|heard|read|seen|watched|killing|exhausted|tired|drained|slept|sleep|"
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
                 "ruhig": "cosy", "entspannt": "cosy", "entspannend": "cosy", "chillig": "cosy", "drinn": "home",
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
# "help me plan my day", and the order a day usually goes in
_PLAN_DAY = re.compile(r"^(?:can you |could you |please |pls )?help me (?:to )?(?:plan|organi[sz]e|structure|schedule) "
                       r"(?:my |the )?(?:day|evening|morning|afternoon|weekend|today)\b")
_TASK_ORDER = [re.compile(r"\b(?:work|job|meeting|study|studying|homework|email|emails|office|class|school|uni|exam|report|"
                          r"presentation|essay|project|deadline|assignment|taxes|paperwork|application)\b"),
               re.compile(r"\b(?:shop|shopping|groceries|grocery|bank|post office|pharmacy|laundry|clean|cleaning|tidy|errand|doctor|dentist)\b"),
               re.compile(r"\b(?:gym|run|running|workout|work out|walk|sport|yoga|swim|swimming|training|football|exercise)\b"),
               re.compile(r"\b(?:cook|cooking|dinner|eat|meal|lunch)\b"),
               re.compile(r"\b(?:relax|tv|netflix|read|reading|friends|call|game|games|chill|movie|bath)\b")]
_TODAY_Q = re.compile(r"^(?:so |and |ok |hey )?(?:(?:any|what are my|what'?s my|do i have any|got any) plans? (?:for (?:me )?)?today|"
                      r"what(?:'s| is) (?:on )?my (?:schedule|agenda|calendar|plan|day)(?: (?:for |like )?today)?(?: like)?|"
                      r"what do i have (?:on |planned |going on )?today|what(?:'s| is) (?:on|happening) (?:for me )?today|"
                      r"do i have anything (?:on |planned )?today|anything (?:on|planned) (?:for )?today|what'?s up for today)\??$")
_TODO_Q = re.compile(r"^(?:so |and |ok )?(?:what (?:do|did) i (?:need|have|want|wanted|have got) to do|what was i supposed to do|"
                     r"what(?:'s| is) on my (?:list|to-?do list)|what did i ask you to remind me(?: of| about)?)(?: today| later| again| tomorrow| tonight| this week)?\??$")
# "remind me to call mom at 6": no alarms here, but a note
_REMIND = re.compile(r"^(?:can you |could you |please |pls )?remind me (?:to |that i (?:need|have) to |about )(?P<x>.{3,80})$")
# fixed-date holidays: "what day is christmas this year?", "when is halloween"
_HOLIDAYS = {"christmas": (12, 25, "Christmas Day"), "christmas eve": (12, 24, "Christmas Eve"),
             "new year": (1, 1, "New Year's Day"), "new years": (1, 1, "New Year's Day"), "new year's": (1, 1, "New Year's Day"),
             "new year's eve": (12, 31, "New Year's Eve"), "new years eve": (12, 31, "New Year's Eve"),
             "halloween": (10, 31, "Halloween"), "valentine's day": (2, 14, "Valentine's Day"), "valentines day": (2, 14, "Valentine's Day"),
             "valentine's": (2, 14, "Valentine's Day"), "st patrick's day": (3, 17, "St Patrick's Day"),
             "boxing day": (12, 26, "Boxing Day")}
_HOLIDAY_Q = re.compile(r"^(?:and |so )?(?:what day (?:is|does)|when is|which day is|on what day is|what date is)(?: it)? "
                        r"(?P<h>christmas eve|christmas|new year'?s eve|new years? eve|new year'?s?|halloween|valentine'?s(?: day)?|"
                        r"st patrick'?s day|boxing day)(?: (?:this|next) year| fall(?: on)?(?: this year)?)?$")
# questions whose answer is a measurement or a count
_NEEDS_NUMBER = re.compile(r"(?i)\b(?:boiling point|melting point|freezing point|temperature|speed of|how many|how much|"
                           r"how far|how long|how tall|how high|how deep|how old|how heavy|population of|distance)\b")
# yes/no questions
_YES_NO_Q = re.compile(r"(?i)^(?:is|are|was|were|does|do|did|can|could|has|have|will|would|should)\b(?!.*\b(?:or)\b)")
# "no wait, it's alexander" right after telling the name
_NAME_FIX = re.compile(r"(?i)^(?:no,? |nope,? |sorry,? |oops,? )?(?:wait,? |actually,? |i mean,? )*(?:it'?s|its|i'?m|im|my name is|"
                       r"call me) (?P<x>[a-z][a-z'-]+)(?:,? (?:actually|sorry|lol|haha|not \w+))?[.!]*$")
# "really? i thought it was sydney" after an answer
# "it's hard", "i'm tired": never a corrected name
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
_SO_MUCH = re.compile(r"^(?:ugh,? |man,? |honestly,? |omg,? )?(?:i (?:have|'ve got|got)|there'?s) (?:so much|a lot|tons|loads|"
                      r"a million things|too much|way too much)(?: of stuff| of things)? (?:to do|on my plate|going on|to get done)"
                      r"(?: today| this week| right now| tomorrow)?[.!]*$")
_WORLD_TIME = re.compile(r"^(?:and |so |hey )?(?:what(?:'s| is) the (?:current )?time|what time is it|what time(?:'s| is) it|"
                         r"time|how late is it)(?: (?:right )?now)? in (?P<p>[a-z][a-z .'-]{1,30}?)(?: (?:right )?now)?\??$|"
                         r"^(?:and |so )?what(?:'s| is) the time(?: (?:right )?now)? (?:over )?(?:in|there in) (?P<p2>[a-z][a-z .'-]{1,30}?)\??$")
_SEE_THERE = re.compile(r"^(?:and |so |ok |okay )?(?:what (?:should|can|could|must|do) (?:i|we|you) (?:see|visit|do|check out)|"
                        r"what(?:'s| is) there to (?:see|do)|what (?:are|r) the (?:best |main |top |must[- ]see )?(?:sights|attractions|"
                        r"things to do|places to visit)|(?:any |some )?(?:sights|attractions|must[- ]sees|places to visit|things to do|"
                        r"sightseeing tips)(?: i should see)?|where should (?:i|we) go|what should i not miss)"
                        r"(?: there| in (?P<p>[a-z][a-z ]+?))?(?: then)?\??$")
_EAT_THERE = re.compile(r"^(?:and |so |ok )?(?:what (?:should|can|do|could|would) (?:i|we|people|you) (?:eat|try|order)|"
                        r"(?:any|what|which) (?:local |typical |traditional |good )?(?:food|foods|dishes|dish|specialties|specialities|"
                        r"food specialties) (?:should |must |do )?(?:i|we|you) (?:should |must |have to )?(?:try|eat|taste|order)|"
                        r"what(?:'s| is) the (?:local |typical )?food like)"
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
            (re.compile(r"(?:und )?(?:welche farbe mag ich(?: am liebsten)?|was ist meine lieblingsfarbe|weißt du(?: noch)?,? (?:welche farbe ich mag|"
                        r"was meine lieblingsfarbe ist))"), "what is my favourite colour?", "Deine Lieblingsfarbe ist {x}."),
            (re.compile(r"(?:und )?(?:was esse ich am liebsten|was ist mein lieblingsessen|weißt du(?: noch)?,? (?:was ich am liebsten esse|"
                        r"was mein lieblingsessen ist))"), "what is my favourite food?", "Dein Lieblingsessen ist {x}."),
            (re.compile(r"(?:und )?(?:was mag ich nicht|was mag ich gar nicht|was esse ich nicht gern)"), "", "list:#dislike"),
            (re.compile(r"(?:und )?(?:was mag ich|was mag ich gern|was esse ich gern)"), "", "list:#fav")]
_SUPER_DE = re.compile(r"(?:und |also )?(?:was|welche[rs]?|wie heißt|wer|wie hoch|wie lang|wie groß) (?:ist )?(?:der|die|das) "
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


_DE_REL = {"sister": "Deine Schwester", "brother": "Dein Bruder", "mother": "Deine Mutter", "father": "Dein Vater",
           "girlfriend": "Deine Freundin", "boyfriend": "Dein Freund", "husband": "Dein Mann", "wife": "Deine Frau",
           "son": "Dein Sohn", "daughter": "Deine Tochter", "boss": "Dein Chef", "grandma": "Deine Oma", "grandpa": "Dein Opa"}
_DE_DAY = {"monday": "Montag", "tuesday": "Dienstag", "wednesday": "Mittwoch", "thursday": "Donnerstag", "friday": "Freitag",
           "saturday": "Samstag", "sunday": "Sonntag", "tomorrow": "morgen", "today": "heute"}


def _de_your(sent: str, gender=None) -> str:
    """The English sentences the German memory layer stores ("Your sister is called Anna.", "Your zahnarzttermin is on
    monday.") rendered back in German; anything else stays as it is."""
    m = re.fullmatch(r"Your (\w+) is called (.+)\.", sent)
    if m and m.group(1).lower() in _DE_REL:
        return f"{_DE_REL[m.group(1).lower()]} heißt {m.group(2)}."
    m = re.fullmatch(r"Your (\w+) works as an? (.+)\.", sent)
    if m and m.group(1).lower() in _DE_REL:
        return f"{_DE_REL[m.group(1).lower()]} arbeitet als {m.group(2)[:1].upper() + m.group(2)[1:]}."
    m = re.fullmatch(r"You live with your (.+)\.", sent)
    if m:
        de_w = {"girlfriend": "deiner Freundin", "boyfriend": "deinem Freund", "wife": "deiner Frau", "husband": "deinem Mann",
                "partner": "deinem Partner", "parents": "deinen Eltern", "mom": "deiner Mutter", "family": "deiner Familie",
                "roommates": "deinen Mitbewohnern", "roommate": "deiner Mitbewohnerin", "sister": "deiner Schwester", "brother": "deinem Bruder",
                "grandma": "deiner Oma"}.get(m.group(1).lower())
        if de_w:
            return f"Du wohnst mit {de_w} zusammen."
    m = re.fullmatch(r"You have (one|two|three|four|five) (kids?|sons?|daughters?)\.", sent)
    if m:
        n_de = {"one": "ein", "two": "zwei", "three": "drei", "four": "vier", "five": "fünf"}[m.group(1)]
        k_de = {"kid": "Kind", "kids": "Kinder", "son": "Sohn", "sons": "Söhne", "daughter": "Tochter", "daughters": "Töchter"}[m.group(2)]
        return f"Du hast {n_de}{'e' if n_de == 'ein' and k_de == 'Tochter' else ''} {k_de}."
    m = re.fullmatch(r"Your (?:best )?friend is called (.+)\.", sent)
    if m:
        g = gender(m.group(1)) if gender else None
        return f"Dein bester Freund heißt {m.group(1)}." if g == "male" else f"Deine beste Freundin heißt {m.group(1)}." if g == "female" else \
            f"{m.group(1)} ist dein bester Freund bzw. deine beste Freundin."
    m = re.fullmatch(r"You(?:'re| are) allergic to (.+)\.", sent)
    if m:
        return f"Du bist allergisch gegen {m.group(1)}."
    m = re.fullmatch(r"Your birthday is (?:on )?(\w+) (\d+)\.", sent)
    de_mon = {"January": "Januar", "February": "Februar", "March": "März", "April": "April", "May": "Mai", "June": "Juni", "July": "Juli",
              "August": "August", "September": "September", "October": "Oktober", "November": "November", "December": "Dezember"}
    if m and m.group(1) in de_mon:
        return f"Dein Geburtstag ist am {m.group(2)}. {de_mon[m.group(1)]}."
    m = re.fullmatch(r"Your (\w+) is on (\w+)\.", sent)
    if m and m.group(2).lower() in _DE_DAY and re.fullmatch(r"[a-zäöüß]+", m.group(1).lower()):
        word = m.group(1)[:1].upper() + m.group(1)[1:]
        return f"Dein{'e' if word.lower().endswith(('ung', 'e', 'stunde', 'prüfung')) else ''} {word} ist am {_DE_DAY[m.group(2).lower()]}." \
            if m.group(2).lower() not in ("tomorrow", "today") else f"{word}: {_DE_DAY[m.group(2).lower()]}."
    return sent


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


_PROPER_BREED_WORDS = {"persian", "siamese", "labrador", "german", "french", "british", "maine", "bengal", "siberian", "yorkshire",
                       "chihuahua", "dalmatian", "pomeranian", "russian", "scottish", "norwegian", "jack", "russell", "bernese",
                       "australian", "border", "shih", "tzu", "pekingese", "rottweiler", "doberman", "great", "dane", "ragdoll",
                       "sphynx", "abyssinian", "burmese", "himalayan", "egyptian", "turkish", "cavalier", "king", "charles", "maltese",
                       "havanese", "boston", "irish", "welsh", "corgi", "beagle", "weimaraner", "akita", "shiba"}


class Assistant:
    def __init__(self, bot, bank: Bank | None = None, clock=None, kb_path=None, nlp_dir=None):
        self.bot = bot
        self.bank = bank or load_bank()
        self.clock = clock                      # callable → datetime (tests fix the date)
        self.about = AboutFinder(bot.c, getattr(bot, "r", None))
        self.kgqa = None
        self.reading_as_of: str | None = None        # the date of the pack's reading text ("December 2022")
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
        bot.not_a_person = self._not_a_person        # "who is his wife?" never resolves "his" to a book
        bot.person_gender = self._gender
        self._kind_cache: dict[str, str | None] = {}
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
        if re.search(r"\b(?:nochmal|noch mal|gleich nochmal|eigentlich)\b", s) and "?" in msg:
            msg = re.sub(r"\s+", " ", re.sub(r"\b(?:gleich nochmal|nochmal|noch mal|eigentlich)\b", "", msg, flags=re.I)).strip()
            s = normalise_de(msg)                         # "wie heiße ich nochmal?": the question itself
        lead = re.sub(r"^(?:(?:haha+|hihi+|hehe+|lol|ok(?:ay)?|na gut|gut|cool|super|alles klar|achso|ach so|krass|echt|witzig|egal|naja|na ja|"
                      r"jedenfalls|wie auch immer|übrigens|apropos)[ ,!.]+)+", "", s)
        if lead != s and len(lead.split()) >= 3:          # "haha ok, was ist die hauptstadt von kanada?": the question
            msg, s = lead, lead
        u = understand(msg, de)
        name = self.user_name()
        known = self.speller.known if self.speller is not None else None
        if u.kind not in ("safety", "remember", "ask_name", "calc", "intent") and gibberish(msg, known):
            return Reply(msg, "unknown", self._pick(st, "de:gib", dd["gibberish"]), via="gibberish")
        if u.kind != "safety":
            life = self._german_mem67(st, msg, s) or self._german_ctx86(st, msg, s) or self._german_ctx74(st, msg, s) or self._german_ctx73(st, msg, s) or self._german_ctx70(st, msg, s) or self._german_ctx68(st, msg, s) or self._german_ctx65(st, msg, s) or self._german_ctx57(st, msg, s) or \
                self._german_ctx61(st, msg, s) or \
                self._german_ctx63(st, msg, s) or \
                self._german_ctx(st, msg, s) or \
                self._german_life(st, msg, s)
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
                if group == "sleep":                 # "hab schlecht geschlafen … was kann ich dagegen tun?": real sleep tips
                    return self.everyday.recommend(st, msg, "sleep", lang="de")
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
            eng = u.data["english"]
            shown = " ".join(w[:1].upper() + w[1:] for w in str(u.data["value"]).split())
            if eng.startswith("My favourite colour is"):
                key = "learned_colour"                   # "ich mag blau": a reply about blue, not "gemerkt"
            elif eng.startswith("My favourite food is"):
                key = "learned_food"
            elif eng.startswith("I like "):
                key = "learned_like"
            text = self._pick(st, f"de:{key}", de["replies"][key], name=u.data["value"], x=shown)
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
            if it["id"] == "bored":
                st.uses["de_offer"] = [None, st.turn]
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
        if le.get("valence") == "negative" and st.turn - le.get("turn", -99) <= 5 and \
                re.fullmatch(r"(?:ja,? |ok(?:ay)?,? |hm+,? )?(?:du hast (?:ja )?recht|da hast du (?:wohl )?recht|stimmt(?: schon)?|guter punkt|macht sinn|"
                             r"das macht sinn|vielleicht hast du recht|klingt vernünftig)", s.strip(" .!")):
            # "du hast recht" after advice on a bad day: no "Das macht es natürlich nicht leichter"
            return Reply(msg, "smalltalk", self._pick(st, "de:life:agree_hard", dd["life"]["agree_hard"]), via="german")
        if le and le.get("valence") in ("negative", "positive") and st.turn - le.get("turn", -99) <= 2 and len(s.split()) >= 2 and \
                "?" not in msg and not re.match(r"^(?:haha|hihi|hehe|lol|ok|okay|cool|super|ach so|achso|gut|klar|stimmt|aber)\b", s) and \
                not (le.get("valence") == "positive" and re.search(r"\b(?:weh|schlimm|traurig|schlecht|furchtbar|schrecklich|leider|tot|"
                                                                    r"gestorben|vermisse|angst|allein|einsam)\b", s)) and \
                not re.search(r"\b(?:vielleicht|morgen|wochenende|freitag|urlaub|plane|werde|will|freue)\b", s):
            # "die nachbarn waren laut" after "ich bin müde": more of the same moment
            key = "follow_neg" if le.get("valence") == "negative" else "follow_pos"
            st.last_exp = dict(le, turn=st.turn, text_en=(le.get("text_en") or "") + " " + _de_advice_hint(s))
            return Reply(msg, "empathy", self._pick(st, f"de:life:{key}", dd["life"][key]), via="german")
        stmt = self._de_statement(st, msg, s)
        if stmt is not None:
            return stmt
        return Reply(msg, "unknown", self._pick(st, "de:fallback", de["replies"]["fallback"]), via="german")

    def _german_mem67(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 67: memory in German — name, job and city in one sentence, "nein, ich meinte München", "meine
        Schwester heißt Anna" → "sie ist Ärztin", appointments ("merk dir, dass mein Zahnarzttermin am Freitag ist",
        moved to Monday), "vergiss, dass ich Pilze hasse"; the English facts are answered in German."""
        q = s.strip(" .!?")
        days = {"montag": "monday", "dienstag": "tuesday", "mittwoch": "wednesday", "donnerstag": "thursday", "freitag": "friday",
                "samstag": "saturday", "sonntag": "sunday", "morgen": "tomorrow", "heute": "today"}
        nouns = {"schwester": ("sister", "Deine Schwester"), "bruder": ("brother", "Dein Bruder"), "mutter": ("mother", "Deine Mutter"),
                 "mama": ("mother", "Deine Mama"), "vater": ("father", "Dein Vater"), "papa": ("father", "Dein Papa"),
                 "freundin": ("girlfriend", "Deine Freundin"), "freund": ("boyfriend", "Dein Freund"), "mann": ("husband", "Dein Mann"),
                 "frau": ("wife", "Deine Frau"), "sohn": ("son", "Dein Sohn"), "tochter": ("daughter", "Deine Tochter"),
                 "chef": ("boss", "Dein Chef"), "chefin": ("boss", "Deine Chefin"), "oma": ("grandma", "Deine Oma"), "opa": ("grandpa", "Dein Opa")}
        cap = lambda w: " ".join(x[:1].upper() + x[1:] for x in w.split())                # noqa: E731
        jm = re.fullmatch(r"(?:hi,? |hallo,? |hey,? )?(?:ich bin (?P<name>[a-zäöüß]+) und (?:ich bin |arbeite als )?|ich bin |ich arbeite als )"
                          r"(?P<job>[a-zäöüß]+(?:in)?) (?:in|aus|bei) (?P<place>[a-zäöüß]+(?: [a-zäöüß]+)?)", q)
        if jm and re.search(r"(?:er|in|ist|ent|eur|arzt|koch|loge|ant|at|wirt|mann|frau)$", jm.group("job")) and jm.group("job") not in (
                "wieder", "immer", "schon", "noch", "lieber", "später", "sicher", "sauer", "unter", "hier", "mal", "da", "gerade",
                "jetzt", "allein", "drin", "bereit", "fertig", "zuhause", "daheim", "oben", "unten", "weiter", "eher", "nur", "privat"):
            prep = re.search(r" (in|aus|bei) " + re.escape(jm.group("place")) + "$", q).group(1)
            place_ok = prep != "bei" and not re.match(r"(?:einem|einer|der|dem|den|die|das|meiner|meinem)\b", jm.group("place"))
            sents = ([f"My name is {cap(jm.group('name'))}."] if jm.group("name") else []) + [f"I work as a {cap(jm.group('job'))}."] + \
                ([f"I {'come from' if prep == 'aus' else 'live in'} {_de_place_case(jm.group('place'))}."] if place_ok else [])
            sids = []
            for sent in sents:
                self._learn(st, [sent], msg)
                sids.append(self.bot.context.get("last_learned"))
            st.uses["learn67"] = [sids, st.turn + 1]
            head = f"Freut mich, {cap(jm.group('name'))}! " if jm.group("name") else ""
            where = f" in {_de_place_case(jm.group('place'))}" if place_ok and prep == "in" else \
                (f" aus {_de_place_case(jm.group('place'))}" if place_ok else "")
            return Reply(msg, "learned", f"{head}{cap(jm.group('job'))}{where} – merk ich mir.", via="german")
        cm = re.fullmatch(r"(?:nein,? |ne,? |sorry,? |oh,? |halt,? |moment,? )+(?:ich meinte |ich meine |eigentlich )(?P<x>[a-zäöüß ]{2,30})", q)
        if cm and st.last_kind == "learned" and self.bot.context.get("last_learned") in self.bot.user_texts():
            sid = self.bot.context["last_learned"]
            l67 = st.uses.get("learn67")
            if l67 and l67[1] == st.turn:
                jobby = bool(re.search(r"(?:er|in|ist|ent|eur|arzt|koch|loge|ant|at|wirt)$", cm.group("x").strip()))
                for cand in l67[0]:
                    rel = {r for f in self.bot.facts.facts if f.source == cand for r in f.relation}
                    if ("#job" in rel) == jobby and "#name" not in rel and cand in self.bot.user_texts():
                        sid = cand
                        break
            old_t = self.bot.user_texts()[sid]
            fs = [f for f in self.bot.facts.facts if f.source == sid and f.subject == USER and f.object]
            if fs and not any("#name" in f.relation for f in fs) and re.search(re.escape(fs[0].object), old_t, re.I):
                x = _de_place_case(cm.group("x").strip()) if fs[0].object[:1].isupper() else cm.group("x").strip()
                self.bot.memory.forget(sid)
                self.bot.refresh()
                self._learn(st, [re.sub(re.escape(fs[0].object), x, old_t, count=1, flags=re.I)], msg)
                return Reply(msg, "learned", f"Ah, {x} – korrigiert!", via="german")
        pm = re.fullmatch(r"mein(?:e)? (?P<n>[a-zäöüß]+) heißt (?P<x>[a-zäöüß]+)", q)
        if pm and pm.group("n") in nouns:
            en, de = nouns[pm.group("n")]
            st.uses["pn_de"] = [pm.group("n"), st.turn]
            self._learn(st, [f"My {en} is called {cap(pm.group('x'))}."], msg)
            return Reply(msg, "learned", f"{cap(pm.group('x'))} – schöner Name! Merk ich mir.", via="german")
        pn = st.uses.get("pn_de")
        if pn and st.turn - pn[1] <= 4:
            sj = re.fullmatch(r"(?:sie|er) (?:ist|arbeitet als) (?P<j>[a-zäöüß]+)", q)
            ad = re.fullmatch(r"(?:sie|er) ist (?:(?:so|sehr|echt|total|richtig|wirklich|voll) )?(?P<a>nett|lieb|toll|super|cool|klasse|"
                              r"witzig|lustig|süß|großartig|die beste|der beste|schlau|klug|hilfsbereit)", q)
            if ad:
                en, de = nouns[pn[0]]
                st.uses["pn_de"] = [pn[0], st.turn]
                ihr = "ihr" if de.startswith("Deine") else "ihm"
                return Reply(msg, "smalltalk", f"Das klingt schön! Man merkt, dass du {ihr} nahestehst. Was macht ihr gern zusammen?", via="german")
            if sj and sj.group("j") not in ("nett", "lieb", "toll", "super", "krank", "müde", "da", "weg", "hier", "gut"):
                en, de = nouns[pn[0]]
                st.uses["pn_de"] = [pn[0], st.turn]
                self._learn(st, [f"My {en} works as a {cap(sj.group('j'))}."], msg)
                return Reply(msg, "learned", f"{cap(sj.group('j'))} – beeindruckend! Merk ich mir.", via="german")
        bq = re.fullmatch(r"(?:und )?was (?:macht|arbeitet) mein(?:e)? (?P<n>[a-zäöüß]+)(?: beruflich)?|was ist mein(?:e)? (?P<m>[a-zäöüß]+) von beruf", q)
        if bq and (bq.group("n") or bq.group("m")) in nouns:
            key = bq.group("n") or bq.group("m")
            en, de = nouns[key]
            r = self._question(st, f"what is my {en}'s job?")
            jm2 = re.search(r"works as an? (.+?)\.", r.text or "")
            if r.kind == "answer" and jm2:
                return Reply(msg, "answer", f"{de} arbeitet als {jm2.group(1)}.", via="german", source=r.source)
            return Reply(msg, "unknown", f"Das hast du mir noch nicht erzählt. Was macht {de.split()[0].lower()} {de.split()[1]} denn?", via="german")
        nq = re.fullmatch(r"(?:und )?wie heißt mein(?:e)? (?P<n>[a-zäöüß]+)(?: noch mal| nochmal| gleich)?", q)
        if nq and nq.group("n") in nouns:
            en, de = nouns[nq.group("n")]
            r = self._question(st, f"what is my {en}'s name?")
            nm2 = re.search(r"is called ([A-ZÄÖÜa-zäöüß]+)", r.text or "")
            if r.kind == "answer" and nm2:
                return Reply(msg, "answer", f"{de} heißt {nm2.group(1)}.", via="german")
        if re.fullmatch(r"(?:und )?(?:was arbeite ich|was mache ich beruflich|was ist mein beruf|als was arbeite ich)", q):
            r = self._question(st, "what is my job?")
            jm3 = re.search(r"work as an? (.+?)\.", r.text or "")
            if r.kind == "answer" and jm3:
                return Reply(msg, "answer", f"Du arbeitest als {cap(jm3.group(1))}.", via="german")
        am = re.fullmatch(r"merk dir,? dass mein(?:e)? (?P<x>[a-zäöüß]+) am (?P<d>montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag) ist", q)
        if am:
            self._learn(st, [f"My {am.group('x')} is on {days[am.group('d')]}."], msg)
            st.uses["appt_de"] = [am.group("x"), st.turn]
            return Reply(msg, "learned", f"Okay, {cap(am.group('x'))} am {cap(am.group('d'))} – merk ich mir.", via="german")
        wq = re.fullmatch(r"(?:und )?wann ist mein(?:e)? (?P<x>[a-zäöüß]+)(?: jetzt| denn)?", q)
        er = re.fullmatch(r"(?:und )?wann ist (?:er|sie|es|der|die|das) (?:jetzt|denn|nun)", q)
        ap = st.uses.get("appt_de")
        if wq or (er and ap):
            x = wq.group("x") if wq else ap[0]
            r = self._question(st, f"when is my {x}?")
            dm = re.search(r"\bon (monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)\b", (r.text or "").lower())
            if r.kind == "answer" and dm:
                de_day = next(k for k, v in days.items() if v == dm.group(1))
                return Reply(msg, "answer", f"Dein {cap(x)} ist am {cap(de_day)}.", via="german")
        mv = re.fullmatch(r"(?:der|die|das|er|sie|es) (?:wurde|ist) (?:jetzt )?(?:auf|am) (?P<d>montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)"
                          r"(?: verschoben| verlegt)?(?: worden)?", q)
        if mv and not ap:
            return Reply(msg, "clarify", f"Was wurde denn auf {cap(mv.group('d'))} verschoben? Sag mir kurz, welcher Termin – dann merk ich's mir.",
                         via="german")
        if mv and ap:
            texts = self.bot.user_texts()
            for sid, t in list(texts.items()):
                if re.search(rf"\bmy {re.escape(ap[0])} is on\b", t, re.I):
                    self.bot.memory.forget(sid)
            self.bot.refresh()
            self._learn(st, [f"My {ap[0]} is on {days[mv.group('d')]}."], msg)
            st.uses["appt_de"] = [ap[0], st.turn]
            return Reply(msg, "learned", f"Okay, verschoben auf {cap(mv.group('d'))} – hab ich geändert.", via="german")
        fg = re.fullmatch(r"vergiss,? dass ich (?P<x>[a-zäöüß ]+?) (?P<v>hasse|nicht mag|mag|liebe|nicht leiden kann)", q) or \
            re.fullmatch(r"vergiss,? dass ich (?P<v2>keine?|kein) (?P<y>[a-zäöüß]+) mag", q)
        if fg:
            gd = fg.groupdict()
            x = gd.get("x") or gd.get("y")
            neg = gd.get("v") in ("hasse", "nicht mag", "nicht leiden kann") or gd.get("v2")
            r = self.bot._forget(f"forget that i {'do not like' if neg else 'like'} {x}")
            if r.kind == "forgot":
                return Reply(msg, "forgot", f"Erledigt – ich habe vergessen, dass du {cap(x)} {'nicht magst' if neg else 'magst'}. Es ist wirklich weg, "
                             "nicht nur versteckt.", via="memory")
            return Reply(msg, "nothing", f"Dazu habe ich nichts gespeichert, was ich vergessen könnte.", via="memory")
        return None

    def _german_ctx86(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 87 in German: loud neighbours (ansprechen? morgen vielleicht) as a short flow instead of fallbacks."""
        g = self.bank.daily["b86"]["de"]
        q = re.sub(r"\s+", " ", re.sub(r"[^\w\s',-]", " ", s)).strip(" .!?")
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"de:b86:{key}", g[key], **kw), via="german")   # noqa: E731
        if re.fullmatch(r"(?:und |außerdem )?(?:die |meine |unsere )?nachbarn (?:waren|haben) (?:(?:bis \d{1,2}(?: uhr)?|die ganze nacht|gestern|heute nacht|letzte nacht|"
                        r"wieder|so|total|echt|mega|richtig) )*(?:laut|am feiern|gefeiert|party gemacht|musik gehört|rumgeschrien|gestritten|am bohren|gebohrt)"
                        r"(?: (?:bis \d{1,2}(?: uhr)?|die ganze nacht|gestern|heute nacht|letzte nacht|gewesen))*", q):
            st.uses["neigh86de"] = [st.turn]
            st.last_exp = {"valence": "negative", "topic": "people", "person": True, "text": msg, "turn": st.turn}
            return say("neigh_loud")
        if re.fullmatch(r"(?:können|koennen|könnten|kannst) (?:wir|du) (?:wieder |bitte |jetzt )*(?:auf )?deutsch (?:reden|sprechen|schreiben|weitermachen)(?: bitte)?|"
                        r"(?:lass uns|lasst uns) (?:wieder )?(?:auf )?deutsch (?:reden|sprechen|schreiben)|(?:wieder )?(?:auf )?deutsch bitte|bitte (?:wieder )?(?:auf )?deutsch|sprichst du deutsch", q):
            st.lang = "de"
            return say("lang_de")
        if re.fullmatch(r"(?:können|koennen|könnten|kannst) (?:wir|du) (?:bitte |jetzt )*(?:auf )?englisch (?:reden|sprechen|schreiben)(?: bitte)?|(?:lass uns|lasst uns) (?:auf )?englisch (?:reden|sprechen)|(?:auf )?englisch bitte", q):
            st.lang = "en"
            return Reply(msg, "smalltalk", self._pick(st, "daily:b86:lang_en", self.bank.daily["b86"]["lang_en"]), via="smalltalk")
        cf = st.uses.get("common_follow")
        if cf and st.turn - cf[1] <= 4:                   # German follow-ups on a hand-checked fact ("wie lange braucht licht dahin?")
            for f in cf[0]:
                if f.get("dq") and f.get("de") and re.fullmatch(f["dq"], q):
                    cf[1] = st.turn
                    return Reply(msg, "answer", f["de"], answer=f["de"], source={"kind": "common", "source": "everyday facts", "key": ""},
                                 confidence=1.0, via="german")
        hm = re.fullmatch(r"(?:hi|hallo|hey|moin|servus|huhu|na)[,!.]? ich bin (?:die |der )?(?P<n>[a-zäöüß]{2,15})(?:[,!.]? (?:und |schön dich kennenzulernen|freut mich).*)?", q)
        if hm and hm.group("n") not in set(self.bank.de["detect"]["german"]) | {"neu", "hier", "da", "zurück", "wieder", "wach", "fertig", "krank", "zuhause"}:
            name = hm.group("n").capitalize()             # "hi, ich bin lena": a name, said with a greeting
            try:
                self._learn(st, [f"My name is {name}."], msg)
            except Exception:
                pass
            return say("name_hi", x=name)
        if re.search(r"\b(?:ich )?(?:hab|habe) heute geburtstag\b", q):
            st.uses["bday88"] = [st.turn]                 # the greeting itself comes from the birthday rule; the follow-ups need it
            return None
        bd = st.uses.get("bday88")
        if bd and st.turn - bd[-1] <= 4:
            am = re.fullmatch(r"(?:ich werde |ich bin |werde |schon )?(?P<n>\d{1,3})(?: jahre?(?: alt)?)?(?: geworden)?", q)
            if am and 1 <= int(am.group("n")) <= 110:
                bd.append(st.turn)
                try:
                    self._learn(st, [f"I am {int(am.group('n'))} years old."], msg)
                except Exception:
                    pass
                return say("bday_age", x=am.group("n"))
            if re.fullmatch(r"(?:wir gehen|ich gehe|wir wollen|ich will|wir sind) (?:heute abend |abends |später )?(?:schön |lecker )?(?:essen|aus essen|essen gehen|feiern|was trinken)(?: gehen)?", q):
                bd.append(st.turn)
                return say("bday_out")
            kc = re.fullmatch(r"(?:zum |beim |zu )?(?:einem )?(?P<k>italienisch|italiener|griechisch|griechen|japanisch|japaner|sushi|chinesisch|indisch|inder|mexikanisch|thai|vietnamesisch|burger|steak|pizza)(?:en)?", q)
            if kc:
                st.uses.pop("bday88", None)
                return say("bday_food", x=kc.group("k").capitalize())
        if re.fullmatch(r"(?:ich )?(?:will|möchte|muss|sollte|würde gern|würde gerne) (?:(?:ein paar|ein bisschen|etwas|\d{1,2}) (?:kilo|kg) )?abnehmen", q):
            st.uses["diet88"] = [st.turn]
            return say("diet_start")
        dt = st.uses.get("diet88")
        if dt and st.turn - dt[-1] <= 5:
            km = re.fullmatch(r"(?:so |ungefähr |etwa |circa |ca |vielleicht |mindestens )?(?P<n>\d{1,2})(?: bis \d{1,2})? ?(?:kilo|kg)(?: oder so)?", q)
            if km:
                dt.append(st.turn)
                n = int(km.group("n"))
                return say("diet_goal", x=str(n), y=str(max(1, round(n / 0.5))))   # half a kilo a week
            if re.fullmatch(r"(?:und |also )?was (?:soll|sollte|kann) ich (?:dann |da |am besten )?essen|(?:und )?was (?:esse|ess) ich (?:dann|am besten)", q):
                dt.append(st.turn)
                return say("diet_food")
            if re.fullmatch(r"(?:und |was ist mit |wie ist es mit )?(?:sport|bewegung|training)(?: dazu)?|(?:und )?welcher sport|soll ich (?:auch )?sport machen", q):
                dt.append(st.turn)
                return say("diet_sport")
            if re.fullmatch(r"(?:ok(?:ay)?,? |gut,? |alles klar,? )?(?:ich versuch(?:'| )?s|ich versuche es|ich probier(?:'| )?s|ich probiere es|ich fang morgen an|ich fange an|mach ich)", q):
                st.uses.pop("diet88", None)
                return say("diet_go")
        if re.fullmatch(r"(?:ok(?:ay)?,? |naja,? |hm+,? |boah,? )?(?:der|das) (?:war|ist) (?:jetzt )?(?:echt |ziemlich |voll |total |richtig |aber )?(?:schlecht|flach|lahm|mies|doof|schwach|nicht lustig|kein bisschen lustig)", q):
            la = st.last_action or {}
            if "witz" in (st.last_reply or "").lower() or re.search(r"\?.+\.", st.last_reply or "") or (la.get("kind") or "").startswith("joke"):
                return say("joke_bad")                    # "der war schlecht 😂" after a joke: no sympathy for a bad day
        if re.fullmatch(r"(?:mein chef|meine chefin|mein boss|die chefin|der chef) (?:will|braucht|möchte|erwartet) (?:alles|das|es|das projekt|den bericht|die präsentation)"
                        r"(?: schon)? (?:bis|zum|zu) (?:montag|dienstag|mittwoch|donnerstag|freitag|morgen|übermorgen|ende der woche|nächste woche)", q):
            st.last_exp = {"valence": "negative", "topic": "work", "person": True, "text": msg, "turn": st.turn, "text_en": "my boss wants everything done by friday"}
            st.uses["work88"] = [st.turn]
            return say("deadline")
        wk = st.uses.get("work88")
        if wk and st.turn - wk[-1] <= 4 and re.fullmatch(r"(?:und )?ich weiß (?:echt |gar )?nicht,? wie ich das (?:alles )?schaffen soll|wie soll ich das (?:alles )?schaffen|"
                                                          r"das schaffe ich nie|das ist (?:viel )?zu viel", q):
            wk.append(st.turn)
            return say("deadline_advice")
        tm = re.fullmatch(r"(?:und )?(?:warst|bist) du (?:schon mal |schon einmal |jemals )?(?:da|dort)(?: gewesen)?", q)
        if tm:                                            # "warst du schon mal da?" after Lissabon ("warst du in paris?" is battery 78's)
            names = st.uses.get("de_names", {})
            ment = self.bot.context.get("mention") or ""
            place = (names.get(ment.lower()) or [ment])[0] if ment else ""
            place = place[:1].upper() + place[1:]
            if place:
                st.uses["city78"] = [place.lower(), st.turn]   # "ich war letztes jahr dort" follows as in battery 78
            return say("travel_bot", x=place) if place else say("travel_bot_none")
        if re.search(r"\bvorstellungsgespräch\b", q):
            st.uses["interview88"] = [st.turn]
            return None
        iv = st.uses.get("interview88")
        if iv and st.turn - iv[-1] <= 3:
            rm = re.fullmatch(r"(?:als |für (?:die stelle als |eine stelle als |den job als )?)(?P<x>[a-zäöüß][a-zäöüß -]{2,40})", q)
            if rm:
                iv.append(st.turn)
                x = " ".join(w.capitalize() if w not in ("und", "für", "im", "in") else w for w in rm.group("x").split())
                return say("interview_role", x=x)
        nb = re.fullmatch(r"(?:und )?(?:hat|bekam|gewann) (?P<p>er|sie|[a-zäöüß ]+?) (?:den |einen |auch den |auch einen )?nobelpreis(?: bekommen| gewonnen| erhalten)?", q)
        if nb:
            p_ = nb.group("p")
            if p_ in ("er", "sie"):
                ctx = self.bot.context
                p_ = (ctx.get("answer") if ctx.get("atype") == "PERSON" and ctx.get("answer") else None) or ctx.get("mention") or ""
                if not p_:
                    last = st.uses.get("kb_vals") or []
                    p_ = last[-1][1] if last else ""
            rep = self._common_fact(st, f"did {p_} win the nobel prize?") if p_ else None
            if rep is not None:
                return rep
        la = st.last_action or {}
        act = ((la.get("kind") or "") == "rec:activity" and st.turn - la.get("turn", -99) <= 3) or \
            (st.uses.get("act88") and st.turn - st.uses["act88"] <= 3)
        if act and re.fullmatch(r"(?:eher |lieber |vielleicht |am liebsten )?(?:was|etwas|irgendwas)? ?(?:für )?(?:draußen|an der frischen luft|in der natur)(?: bitte)?", q):
            st.uses["act88"] = st.turn
            return say("act_out")
        if act and re.fullmatch(r"(?:aber |nur |leider )?(?:es soll|es wird|es könnte|es) (?:(?:am wochenende|morgen|heute) )?(?:regnen|regnet|schütten|schüttet)(?: am wochenende| morgen| leider)?|"
                                r"(?:aber |nur )?(?:das wetter (?:soll|wird) (?:schlecht|mies)(?: werden)?|bei regen)", q):
            st.uses["act88"] = st.turn
            return say("act_rain")
        if re.search(r"\b(?:meine|mein) (?:katze|kater|hund|hündin|kaninchen|hamster|meerschweinchen) (?:ist|scheint) (?:krank|so schlapp|nicht fit|komisch)", q):
            st.uses["sickpet88"] = [st.turn]
            return None
        sp = st.uses.get("sickpet88")
        if sp and st.turn - sp[-1] <= 4:
            if re.search(r"\b(?:frisst|trinkt|isst) (?:seit [a-zäöüß ]+ )?(?:nichts|nix|kaum|gar nichts|nicht mehr)\b|\b(?:erbricht|kotzt|bricht|hat durchfall|schläft nur)\b", q):
                sp.append(st.turn)
                return say("sickpet_serious")
            if re.fullmatch(r"(?:ok(?:ay)?,? |gut,? |ja,? )?(?:mach ich|das mach ich|ich ruf (?:da |gleich )?an|ich fahr(?:e)? hin|ich geh(?:e)? hin|wir fahren hin)", q):
                st.uses.pop("sickpet88", None)
                return say("sickpet_go")
        ng = st.uses.get("neigh86de")
        if ng and st.turn - ng[-1] <= 4:
            if re.fullmatch(r"(?:und |also )?soll ich (?:sie|die nachbarn|ihn|ihr) (?:mal )?(?:ansprechen|darauf ansprechen|was sagen|etwas sagen|bescheid sagen)|"
                            r"soll ich (?:mal )?(?:klingeln|mich beschweren|einen zettel schreiben|mit (?:ihnen|denen|den nachbarn) reden|"
                            r"was sagen|etwas sagen|dem vermieter bescheid sagen)", q):
                ng.append(st.turn)
                return say("neigh_advice")
            if re.fullmatch(r"(?:ja,? |ok(?:ay)?,? |gut,? )?(?:vielleicht |wahrscheinlich |dann |mach ich )?(?:morgen|später|wenn ich ruhiger bin|morgen früh)(?: vielleicht| mal)?|"
                            r"(?:ja,? |ok(?:ay)?,? )?(?:ich rede|ich sprech|ich spreche) (?:morgen |später )?mit (?:ihnen|denen)", q):
                st.uses.pop("neigh86de", None)
                return say("neigh_plan")
        return None

    def _german_ctx74(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 74 in German: "erzähl mehr" after an explanation, and choosing a dog or a cat."""
        g = (self.bank.de["daily"].get("ctx") or {}).get("g74")
        if not g:
            return None
        q = re.sub(r"\s+", " ", re.sub(r"[^\w\s',-]", " ", s)).strip(" .!?")
        say = lambda key: Reply(msg, "smalltalk", self._pick(st, f"de:g74:{key}", g[key]), via="german")   # noqa: E731
        for ev in self.bank.daily["b82"]["de"]:
            if re.fullmatch(ev["q"], q):
                st.last_exp = {"valence": "negative" if ev["v"] == "neg" else "positive", "topic": None, "person": False, "text": msg, "turn": st.turn}
                return Reply(msg, "empathy", ev["a"], via="german")
        g1 = (self.bank.de["daily"].get("ctx") or {}).get("g81") or {}
        if g1:
            sp = g1["spezial"]
            pain = re.fullmatch(r"(?:mir tut|mir tun|mein|meine) (?:mein |meine |der |die |das )?(?P<o>zahn|zähne|rücken|bauch|magen|brust)(?: tut| tun)? (?:so |total |echt |richtig )?weh"
                                r"|(?:ich habe|ich hab|hab) (?P<o2>zahn|rücken|bauch|brust)schmerzen", q)
            if pain:
                o = (pain.group("o") or pain.group("o2"))
                o = {"zähne": "zahn", "magen": "bauch"}.get(o, o)
                return Reply(msg, "empathy", sp[o], via="german")
            if re.fullmatch(r"(?:das |mein |unser )?(?:wlan|wifi|internet) (?:geht nicht|geht nicht mehr|ist weg|ist down|funktioniert nicht|spinnt)(?: mehr)?", q):
                return Reply(msg, "empathy", sp["wlan"], via="german")
            sm = re.fullmatch(r"(?:mein|meine|unser|unsere) (?P<o>[a-zäöüß-]+(?: [a-zäöüß-]+)?) (?:ist|sind|wurde|wurden) (?:so |zu |total |voll |echt |ganz |schon wieder )*"
                              r"(?P<a>kalt|langsam|salzig|eingegangen|nass|unordentlich|geklaut|gestohlen|leer|dreckig|schmutzig|rot|blau|grün|schwarz|weiß|gelb|grau|braun|"
                              r"rosa|lila|orange|silber)", q)
            if sm and not re.search(r"\b(?:handy|smartphone|iphone|laptop|tablet)\b", sm.group("o")) or (sm and sm.group("a") not in ("kaputt",)):
                o, a = sm.group("o"), sm.group("a")
                farben = {"rot", "blau", "grün", "schwarz", "weiß", "gelb", "grau", "braun", "rosa", "lila", "orange", "silber"}
                if a in farben:
                    return Reply(msg, "smalltalk", self._pick(st, "de:g81:farbe", g1["farbe"], x=a, X=a[:1].upper() + a[1:]), via="german")
                key = {"kalt": "tee" if "tee" in o else "kaffee" if "kaffee" in o else None, "langsam": "langsam", "salzig": "salzig", "eingegangen": "pflanze",
                       "nass": "nass", "unordentlich": "unordentlich", "geklaut": "geklaut", "gestohlen": "geklaut"}.get(a)
                st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
                if key and key in sp:
                    return Reply(msg, "empathy", sp[key], via="german")
                return Reply(msg, "empathy", self._pick(st, "de:g81:neg", g1["neg"]), via="german")
        g9 = (self.bank.de["daily"].get("ctx") or {}).get("g79") or {}
        say9 = lambda key, kind="smalltalk", **kw: Reply(msg, kind, self._pick(st, f"de:g79:{key}", g9[key], **kw), via="german")   # noqa: E731
        if g9:
            if re.fullmatch(r"(?:mist,? |oh nein,? )?mein (?:handy|smartphone|iphone|laptop|tablet) ist (?:mir )?(?:runtergefallen|heruntergefallen|hingefallen)|"
                            r"mir ist (?:mein |das )?(?:handy|smartphone|iphone) runtergefallen", q):
                return say9("handy", "empathy")
            if re.fullmatch(r"was ist (?:der )?sinn des lebens|was ist der sinn von allem|warum leben wir", q):
                return say9("sinn")
            if re.fullmatch(r"(?:meine|die) (?:nachbarn|mitbewohner) (?:sind|waren) (?:so |total |echt |mal wieder |schon wieder )*(?:laut|nervig)(?: heute)?", q):
                st.last_exp = {"valence": "negative", "topic": None, "person": True, "text": msg, "turn": st.turn}
                return say9("nachbarn", "empathy")
            if re.fullmatch(r"(?:sag|erzähl) (?:mir )?(?:was|etwas) (?:nettes|schönes|liebes|positives)", q):
                return say9("nettes")
            if re.fullmatch(r"(?:boah,? |mist,? )?ich (?:stehe|steh|stecke|steck) (?:gerade |schon wieder )?im stau", q):
                return say9("stau", "empathy")
            if re.fullmatch(r"kannst du (?:ein )?geheimnis(?:se)? (?:bewahren|behalten|für dich behalten)|bleibt das unter uns|erzählst du das (?:jemandem|weiter)", q):
                return say9("geheimnis")
            if re.fullmatch(r"(?:ich )?bin wieder da|(?:ich bin )?zurück|da bin ich wieder", q):
                return say9("zurueck")
            if re.fullmatch(r"(?:guten )?morgen|moin moin", q) and re.match(r"\s*guten morgen", msg.lower()):
                return say9("morgen")
        g8 = (self.bank.de["daily"].get("ctx") or {}).get("g78") or {}
        say8 = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"de:g78:{key}", g8[key], **kw), via="german")   # noqa: E731
        if g8 and re.fullmatch(r"(?:gut,? |ganz gut,? |geht,? )?(?:ein )?(?:bisschen|bissl|etwas|leicht|total|echt|so) müde,? (?:und )?(?:dir|du|selbst|bei dir)", q):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:g78:muede_du", g8["muede_du"]), via="german")
        if g8 and re.fullmatch(r"(?:was|etwas|irgendwas|vielleicht was) mit (?:hähnchen|huhn|hühnchen|hühnerfleisch|chicken)", q):
            return say8("haehnchen")
        bauten = {"eiffelturm": ("the eiffel tower", "der Eiffelturm"), "kolosseum": ("the colosseum", "das Kolosseum"),
                  "freiheitsstatue": ("the statue of liberty", "die Freiheitsstatue"), "brandenburger tor": ("the brandenburg gate", "das Brandenburger Tor"),
                  "kölner dom": ("cologne cathedral", "der Kölner Dom"), "schloss neuschwanstein": ("neuschwanstein castle", "das Schloss Neuschwanstein"),
                  "big ben": ("big ben", "Big Ben"), "taj mahal": ("the taj mahal", "das Taj Mahal"), "empire state building": ("the empire state building", "das Empire State Building")}
        am = re.fullmatch(r"(?:und )?wie alt ist (?:der |die |das )?(?P<x>" + "|".join(bauten) + r")(?: eigentlich| denn)?", q)
        if g8 and am:
            en, de = bauten[am.group("x")]
            got = self._age_built(st, en)
            if got:
                _x, age, year = got
                text = self._pick(st, "de:g78:alter_bau", g8["alter_bau"], x=de[:1].upper() + de[1:], n=str(age), y=str(year))
                if not de.startswith("der "):
                    text = text.replace(" wurde er ", " wurde es " if de.startswith("das ") else " wurde sie ")
                return Reply(msg, "answer", text, via="kb")
        staedte = {"paris": "Paris", "rom": "Rom", "london": "London", "berlin": "Berlin", "wien": "Wien", "prag": "Prag", "barcelona": "Barcelona",
                   "lissabon": "Lissabon", "amsterdam": "Amsterdam", "new york": "New York", "tokio": "Tokio", "venedig": "Venedig", "münchen": "München"}
        cm = re.fullmatch(r"(?:warst du (?:schon )?(?:mal |einmal )?in|magst du|wie findest du|kennst du) (?P<x>" + "|".join(staedte) + r")", q)
        if g8 and cm:
            st.uses["city78"] = [cm.group("x"), st.turn]
            return say8("paris", x=staedte[cm.group("x")])
        c78 = st.uses.get("city78")
        if g8 and c78 and st.turn - c78[1] <= 4 and re.fullmatch(r"(?:ja,? )?ich war (?:letztes jahr|letzten sommer|im sommer|vor \w+ jahren|schon mal|schon \w+ mal|"
                                                                 r"letzten monat|\d{4}) (?:dort|da)|(?:ja,? )?ich war (?:dort|da) (?:letztes jahr|schon mal|\d{4})", q):
            st.uses["city78"] = [c78[0], st.turn]
            return say8("dort")
        if g8 and re.fullmatch(r"das essen (?:dort |da )?war (?:so |echt |richtig |total |mega )?(?:super|lecker|toll|großartig|fantastisch|der hammer|klasse|genial)", q):
            return say8("essen_war")
        if g8 and re.fullmatch(r"(?:ich (?:glaub|glaube|denke),? )?ich (?:schau|schaue|guck|gucke|seh|sehe) (?:mir )?(?:später|heute abend|nachher|gleich|heute) "
                               r"(?:noch )?(?:einen|nen|'nen) film(?: an)?", q):
            st.uses["movie78de"] = st.turn
            return say8("film_plan")
        mvd = st.uses.get("movie78de")
        if g8 and mvd is not None and st.turn - mvd <= 3:
            if re.fullmatch(r"(?:hast du |irgendwelche |ein paar )?(?:tipps|ideen|empfehlungen|vorschläge)|was soll ich (?:mir )?(?:anschauen|schauen|gucken)", q):
                st.uses["movie78de"] = st.turn
                return say8("film_tipps_allg")
            if re.fullmatch(r"(?:was|etwas|irgendwas) (?:lustiges|witziges|leichtes)|eine komödie|(?:eher )?lustig", q):
                st.uses["movie78de"] = st.turn
                return say8("film_tipps")
        g6 = (self.bank.de["daily"].get("ctx") or {}).get("g76") or {}
        sar_de = r"(?:na )?(?:toll|super|klasse|prima|großartig|perfekt|wunderbar|na prima|na super|na klasse|na toll),? "
        if g6 and re.fullmatch(sar_de + r"(?:schon wieder |mal wieder |wieder )?(?:regen|es regnet(?: schon wieder)?)(?: heute)?", q):
            return Reply(msg, "empathy", self._pick(st, "de:g76:regen", g6["regen"]), via="german")
        if g6 and re.fullmatch(r"(?:" + sar_de + r"|mist,? |oh mann,? )?(?:mein|meine|unser|unsere|das|die|der) (?:auto|laptop|handy|waschmaschine|kühlschrank|fahrrad|"
                               r"heizung|spülmaschine|rad) (?:ist|hat) (?:schon wieder |jetzt |auch noch )?(?:kaputt|den geist aufgegeben|kaputt gegangen)", q):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:g76:kaputt", g6["kaputt"]), via="german")
        if g6 and re.fullmatch(r"(?:" + sar_de + r")?(?:ich habe|ich hab|hab) (?:den |meinen |die |meine )?(?:zug|bus|bahn|flug|anschluss) verpasst", q):
            return Reply(msg, "empathy", self._pick(st, "de:g76:verpasst", g6["verpasst"]), via="german")
        if g6 and (re.fullmatch(r"(?:naja|na ja|hm+|ehrlich gesagt|eigentlich),? (?:nicht so ganz|nicht wirklich|nicht so|geht so|eher nicht)", q) or
                   (re.fullmatch(r"nicht so ganz|nicht wirklich|eher nicht", q) and
                    re.search(r"\b(?:gut|okay|ok|passt|bestens)\b", (st.last_message or "").lower()))):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:g76:nicht_ganz", g6["nicht_ganz"]), via="german")
        if g6 and re.fullmatch(sar_de + r"(?:noch )?mehr arbeit", q):
            return Reply(msg, "smalltalk", self._pick(st, "de:g76:ironie_arbeit", g6["ironie_arbeit"]), via="german")
        g5 = (self.bank.de["daily"].get("ctx") or {}).get("g75") or {}
        money = self._money75(st, msg, s.strip(" ?!."), de=True)
        if money is not None:
            return money
        cv = re.fullmatch(r"(?:rechne |wie viel sind |wieviel sind |was sind )?(?P<n>\d+(?:[.,]\d+)?) (?P<a>meilen|kilometer|km|pfund|kilo|kg|fahrenheit|grad fahrenheit|"
                          r"celsius|grad celsius|fuß|fuss|meter|zoll|zentimeter|cm|liter|gallonen|unzen|gramm) (?:in|zu) (?P<b>meilen|kilometer|km|pfund|kilo|kg|"
                          r"fahrenheit|celsius|fuß|fuss|meter|zoll|zentimeter|cm|liter|gallonen|unzen|gramm)(?: um)?", q)
        if cv:
            units = {"meilen": "miles", "kilometer": "km", "km": "km", "pfund": "pounds", "kilo": "kg", "kg": "kg", "fahrenheit": "fahrenheit",
                     "grad fahrenheit": "fahrenheit", "celsius": "celsius", "grad celsius": "celsius", "fuß": "feet", "fuss": "feet", "meter": "meters",
                     "zoll": "inches", "zentimeter": "cm", "cm": "cm", "liter": "liters", "gallonen": "gallons", "unzen": "ounces", "gramm": "grams"}
            from engramm.chat.tools import convert
            r = convert(f"convert {cv.group('n').replace(',', '.')} {units[cv.group('a')]} to {units[cv.group('b')]}")
            if r is not None and r.value is not None:
                de_u = {"miles": "Meilen", "km": "km", "pounds": "Pfund", "kg": "kg", "°F": "°F", "°C": "°C", "feet": "Fuß", "m": "m", "meters": "m",
                        "inches": "Zoll", "cm": "cm", "liters": "Liter", "liter": "Liter", "gallons": "Gallonen", "ounces": "Unzen", "g": "g", "grams": "g"}
                txt = re.sub(r"(?<=\d)\.(?=\d)", ",", r.text)
                txt = re.sub(r"\b(miles|pounds|feet|inches|liters|liter|gallons|ounces|grams|meters)\b", lambda m_: de_u.get(m_.group(1), m_.group(1)), txt)
                return Reply(msg, "tool", txt if txt.endswith(".") else txt + ".", answer=r.value, via="tool")
        if g5 and re.fullmatch(r"(?:kannst du |bitte )?(?:schreib|schreibe|formulier|formuliere) (?:mir )?(?:eine nachricht )?(?:an )?(?:meinen |meine |meinem )?"
                               r"(?:chef|chefin|arbeitgeber)(?:,)? (?:dass|das) ich krank bin|(?:hilf mir,? )?(?:eine )?krankmeldung (?:an meinen chef )?(?:schreiben|formulieren)", q):
            return Reply(msg, "smalltalk", g5["krank"], via="german")
        if g5 and re.fullmatch(r"(?:aber |und )?(?:bitte )?(?:ohne kochen|nichts kochen|ich will nicht kochen|kein kochen)(?: bitte)?", q):
            return Reply(msg, "smalltalk", self._pick(st, "de:g75:ohne_kochen", g5["ohne_kochen"]), via="german")
        if re.fullmatch(r"(?:erzähl|erzähle|sag) (?:mir )?(?:noch )?mehr(?: darüber| davon| dazu)?|mehr (?:davon|dazu|bitte)|und weiter|weiter", q) and \
                (st.last_about or self.bot.context.get("mention")):
            rep = self._more(st, msg)
            if rep.kind == "about":
                rep.text = f"{self.bank.de['daily']['english_text']} {rep.text}"
                rep.message = msg
                return rep
        if re.fullmatch(r"ich (?:überlege|denke darüber nach|will|möchte|würde gern)(?:,)? (?:mir )?(?:einen|eine) (?P<p>hund|welpen|katze|kätzchen)"
                        r"(?: zu)? (?:holen|zu holen|anschaffen|anzuschaffen|adoptieren|zu adoptieren)?", q):
            st.uses["pet74"] = ["dog" if re.search(r"hund|welpe", q) else "cat", st.turn]
            return say("hund") if st.uses["pet74"][0] == "dog" else None
        pet = st.uses.get("pet74")
        if pet and st.turn - pet[1] <= 5:
            if re.fullmatch(r"(?:und )?welche (?:rasse|hunderasse)(?: würdest du (?:mir )?empfehlen| empfiehlst du| passt)?|hast du eine rasse(?:empfehlung)?", q):
                st.uses["pet74"] = [pet[0], st.turn]
                return say("rasse")
            if re.fullmatch(r"(?:aber |also )?ich wohne in einer (?:kleinen|winzigen) wohnung", q):
                self._learn(st, ["I live in a small apartment."], msg)
                st.uses["pet74"] = [pet[0], st.turn]
                return Reply(msg, "learned", self._pick(st, "de:g74:klein", g["klein_hund"] if pet[0] == "dog" else g["katze"]), via="german")
            if re.fullmatch(r"(?:und |oder |was ist mit )?(?:einer |eine )?katze(?: stattdessen)?|wäre eine katze besser", q):
                st.uses["pet74"] = ["cat", st.turn]
                return say("katze")
            if re.fullmatch(r"(?:ok(?:ay)?,? |gut,? )?(?:dann )?(?:vielleicht |wohl )?(?:doch )?(?:eine )?katze(?: dann)?", q):
                return say("katze_ok")
        return None

    def _german_ctx73(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 73 in German: what passes ("ich trinke gerade Kaffee", "meine Mama ist auf dem Sofa eingeschlafen",
        "mein Papa hat mich angerufen", "der Zug hatte Verspätung") and what is kept (an allergy, children, a birthday,
        who you live with)."""
        g = (self.bank.de["daily"].get("ctx") or {}).get("g73")
        if not g:
            return None
        q = re.sub(r"\s+", " ", re.sub(r"[^\w\s',.-]", " ", s)).strip(" !?")
        q = q.rstrip(".")
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"de:g73:{key}", g[key], **kw), via="german")  # noqa: E731
        fem = ("mama", "mutter", "schwester", "oma", "frau", "freundin", "tochter", "tante", "chefin")
        if re.fullmatch(r"mein(?:e)? (?:mama|mutter|papa|vater|bruder|schwester|oma|opa|mann|frau|freund|freundin|sohn|tochter|katze|hund) "
                        r"(?:ist|sind) (?:gerade |schon |wieder )?(?:auf dem sofa |auf der couch |vor dem fernseher |beim film )?eingeschlafen", q):
            return say("eingeschlafen")
        m = re.fullmatch(r"ich trinke (?:gerade |grad |jetzt )?(?:einen |eine |ein |meinen |meine )?(?:tasse |becher |glas )?(?P<x>kaffee|cappuccino|latte|espresso|"
                         r"tee|grünen tee|schwarztee|kräutertee|kakao|wasser|saft|bier|wein|cola)", q)
        if m:
            x = m.group("x")
            return say("kaffee" if x in ("kaffee", "cappuccino", "latte", "espresso") else "tee" if "tee" in x else "essen")
        if re.fullmatch(r"ich esse (?:gerade|grad|jetzt) [a-zäöüß ]{2,30}", q):
            return say("essen")
        if re.fullmatch(r"ich (?:schaue|schau|gucke|guck|sehe) (?:gerade |grad |jetzt )?(?:fern|fernsehen|tv|netflix|eine serie|einen film|ein spiel)", q):
            return say("fernsehen")
        m = re.fullmatch(r"mein(?:e)? (?P<w>mama|mutter|papa|vater|bruder|schwester|oma|opa|freund|freundin|chef|chefin|sohn|tochter) "
                         r"hat (?:mich )?(?:heute |gerade |eben |vorhin )?(?:mich )?(?:angerufen|geschrieben|besucht)", q)
        if m:
            w = m.group("w")
            dat = ("deiner " if w in fem else "deinem ") + w[:1].upper() + w[1:]
            nom = "sie" if w in fem else "er"
            return say("angerufen", x=dat, y=nom)
        if re.fullmatch(r"(?:ugh,? |boah,? )?(?:der |die |mein |meine )?(?:bus|zug|bahn|s-bahn|u-bahn|flug|flieger) (?:war|ist|hatte|hat) (?:schon wieder |wieder |mal wieder )?"
                        r"(?:zu spät|verspätung|verspätet|ausgefallen)(?: heute)?", q):
            return say("verspaetung")
        m = re.fullmatch(r"ich bin (?:sehr |stark |leicht )?allergisch (?:gegen|auf) (?P<x>[a-zäöüß ]{2,30})", q)
        if m:
            x = " ".join(w[:1].upper() + w[1:] if w not in ("und", "oder") else w for w in m.group("x").split())
            self._learn(st, [f"I am allergic to {x}."], msg)
            return Reply(msg, "learned", self._pick(st, "de:g73:allergie", g["allergie"], x=x), via="german")
        nums = {"ein": 1, "einen": 1, "eine": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
        m = re.fullmatch(r"ich habe (?P<n>ein|einen|eine|zwei|drei|vier|fünf|[1-5]) (?P<k>kind|kinder|sohn|söhne|tochter|töchter)", q)
        if m:
            k = m.group("k")
            en = {"kind": "kid", "kinder": "kids", "sohn": "son", "söhne": "sons", "tochter": "daughter", "töchter": "daughters"}[k]
            num = nums[m.group("n")]
            self._learn(st, [f"I have {['', 'one', 'two', 'three', 'four', 'five'][num]} {en}."], msg)
            de_n = f"{m.group('n')} {k[:1].upper() + k[1:]}"
            return Reply(msg, "learned", self._pick(st, "de:g73:kinder", g["kinder"], x=de_n, X=de_n[:1].upper() + de_n[1:]), via="german")
        mon = {"januar": "January", "februar": "February", "märz": "March", "april": "April", "mai": "May", "juni": "June", "juli": "July",
               "august": "August", "september": "September", "oktober": "October", "november": "November", "dezember": "December"}
        m = re.fullmatch(r"mein geburtstag ist am (?P<d>\d{1,2})\.? (?P<m>" + "|".join(mon) + r")", q)
        if m:
            d = int(m.group("d"))
            self._learn(st, [f"My birthday is on {mon[m.group('m')]} {d}."], msg)
            return Reply(msg, "learned", self._pick(st, "de:g73:geburtstag", g["geburtstag"], x=f"{d}. {m.group('m').capitalize()}"), via="german")
        m = re.fullmatch(r"ich wohne (?:mit|bei) (?P<p>meiner|meinem|meinen) (?P<w>freundin|freund|frau|mann|partner|partnerin|eltern|mutter|mama|familie|"
                         r"oma|schwester|bruder|mitbewohnern|mitbewohner|mitbewohnerin)(?: zusammen)?", q)
        if m:
            en = {"freundin": "girlfriend", "freund": "boyfriend", "frau": "wife", "mann": "husband", "partner": "partner", "partnerin": "partner",
                  "eltern": "parents", "mutter": "mom", "mama": "mom", "familie": "family", "oma": "grandma", "schwester": "sister", "bruder": "brother",
                  "mitbewohnern": "roommates", "mitbewohner": "roommates", "mitbewohnerin": "roommate"}[m.group("w")]
            self._learn(st, [f"I live with my {en}."], msg)
            return Reply(msg, "learned", self._pick(st, "de:g73:wohnen", g["wohnen"], x=f"{m.group('p')} {m.group('w')[:1].upper() + m.group('w')[1:]}"),
                         via="german")
        return None

    def _german_ctx70(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 70: a relaxed chat in German — "gut und dir?", pasta tonight with the dish and a drink,
        the match lost 3:0, boredom, a boss piling on tasks, a trip to Rome (tips, food, "danke auf
        italienisch", "grazie!"), and questions about ENGRAMM itself."""
        g = (self.bank.de["daily"].get("ctx") or {}).get("g70")
        if not g:
            return None
        q = re.sub(r"\s+", " ", re.sub(r"[^\w\s',:-]", " ", s)).strip(" .!?")
        lr = st.last_reply or ""
        cap = lambda w: " ".join(x[:1].upper() + x[1:] for x in w.split())              # noqa: E731
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"de:g70:{key}", g[key], **kw), via="german")  # noqa: E731
        sub = lambda grp, key, **kw: Reply(msg, "smalltalk", self._pick(st, f"de:g70:{grp}:{key}", g[grp][key], **kw), via="german")  # noqa: E731
        if re.fullmatch(r"(?:mir geht'?s |mir gehts |auch |echt )?(?:gut|super|ganz gut|sehr gut|bestens|passt|alles gut|alles klar|geht so|okay|ok)"
                        r"(?:,? danke)?(?:,? und |, )(?:dir|selbst|bei dir|du|wie geht'?s dir)|danke,? und (?:dir|selbst|bei dir|du)", q):
            return say("gut_du")
        ck = re.fullmatch(r"(?:ich|wir) (?:koche|koch|kochen|mache|mach|machen|esse|ess|essen) (?:heute(?: abend)?|heut abend|gleich|nachher) (?P<x>[a-zäöüß ]+?)", q) or \
            re.fullmatch(r"(?:heute )?gibt'?s (?:heute(?: abend)? |bei uns )?(?P<x>[a-zäöüß ]+?)(?: heute(?: abend)?)?", q)
        if ck and len(ck.group("x").split()) <= 3 and ck.group("x") not in ("was", "nichts", "etwas", "irgendwas", "es", "das"):
            x = ck.group("x")
            st.uses["koch70"] = [x, st.turn]
            if x in ("abendessen", "essen", "mittagessen", "was leckeres", "etwas leckeres"):
                return say("koch_allg")
            return say("koch", x=cap(x) if x in ("pasta", "pizza") else x, X=cap(x))
        ko = st.uses.get("koch70")
        if ko and st.turn - ko[1] <= 2 and re.fullmatch(r"(?:vielleicht |wahrscheinlich |ich glaube )?[a-zäöüß]+(?: [a-zäöüß]+){0,2}", q) and \
                not set(q.split()) & {"ja", "nein", "keine", "ahnung", "weiß", "nicht", "danke", "ok", "okay", "haha", "cool", "was", "warum", "wie"}:
            d = re.sub(r"^(?:vielleicht|wahrscheinlich|ich glaube) ", "", q)
            st.uses["koch70"] = [d, st.turn]
            if d in g["gericht"]:
                return sub("gericht", d)
            if len(d.split()) <= 2:
                return say("gericht_sonst", x=d, X=cap(d))
        if re.search(r"\bsahne\b", q) and (re.search(r"\bcarbonara\b", q) or (ko and ko[0] == "carbonara" and st.turn - ko[1] <= 4)):
            return say("sahne")                           # "kommt da sahne rein?" right after "carbonara"
        rez = self.bank.daily["b86"]["de"]["recipe"]
        if ko and ko[0] in rez and st.turn - ko[1] <= 4 and re.fullmatch(
                r"(?:und )?(?:wie (?:geht|macht man) (?:das|die|sie|es)(?: richtig| original)?|wie geht das original(?:rezept)?|was ist das (?:original)?rezept|"
                r"was brauche ich (?:dafür|da)?|was kommt (?:da )?rein)", q):
            ko[1] = st.turn
            return Reply(msg, "smalltalk", rez[ko[0]], via="german")
        if re.fullmatch(r"(?:und )?was (?:trinke ich|trink ich|passt|kann ich trinken|soll ich trinken)(?: dazu| zu (?P<x>[a-zäöüß ]+))?(?: zu trinken)?", q):
            m = re.search(r"zu ([a-zäöüß ]+)", q)
            x = (m.group(1) if m else "") or (ko[0] if ko and st.turn - ko[1] <= 4 else "")
            key = next((k for k in g["trinken"] if k != "sonst" and k in x), "sonst")
            return sub("trinken", key)
        if re.fullmatch(r"(?:hast du |hast du gestern |hast du das )?(?:das |gestern das )?(?:spiel|match)(?: gestern| gestern abend)? (?:gesehen|geschaut|gekuckt|geguckt)", q):
            st.uses["spiel70"] = st.turn
            return say("spiel")
        sp = st.uses.get("spiel70")
        if sp is not None and st.turn - sp <= 2 and q in ("fußball", "fussball", "basketball", "handball", "eishockey", "tennis", "formel 1",
                                                          "die bundesliga", "bundesliga", "champions league", "die champions league", "volleyball"):
            return say("sport", x=cap(q.replace("die ", "")) if q not in ("formel 1",) else "Formel 1")
        sc = re.fullmatch(r"(?:leider |oh mann,? )?(?P<w>[a-zäöüß]+(?: [a-zäöüß]+)?) (?:haben?|hat) (?:leider )?(?P<a>\d{1,2}) ?(?::|-|zu) ?(?P<b>\d{1,2}) "
                          r"(?P<v>verloren|gewonnen|unentschieden gespielt|gespielt)", q)
        if sc:
            v = {"verloren": "verloren", "gewonnen": "gewonnen"}.get(sc.group("v"), "remis")
            a, b = int(sc.group("a")), int(sc.group("b"))
            if v == "verloren":
                a, b = max(a, b), min(a, b)
            elif v == "gewonnen":
                a, b = max(a, b), min(a, b)
            st.uses["spiel70v"] = [v, st.turn]
            st.last_exp = None
            return say(v, a=a, b=b)
        sv = st.uses.get("spiel70v")
        if sv and sv[0] == "verloren" and st.turn - sv[1] <= 2 and \
                re.fullmatch(r"(?:ja,? |jo,? |ja ja,? )?(?:echt |total |voll |richtig |so )?(?:bitter|ärgerlich|blöd|doof|mies|scheiße|scheisse|schade|ätzend)", q):
            return say("bitter")
        if re.search(r"\bnächste saison\b|\bnächstes jahr wird\b|\bnächstes mal wird\b", q) and \
                re.match(r"(?:egal|naja|na ja|aber|tja)?,? ?(?:die )?nächste|(?:egal|naja|na ja|aber|tja),? ", q):
            return say("saison")
        if re.fullmatch(r"(?:mir ist|mir is|ist mir) (?:so |total |voll |echt )?langweilig|langweilig|ich langweile mich", q):
            st.uses["lw70"] = st.turn
            return None
        lw = st.uses.get("lw70")
        if lw is not None and st.turn - lw <= 3:
            if re.fullmatch(r"(?:keine ahnung|weiß nicht|weiss nicht|ich weiß nicht|k\.?a\.?|egal)", q):
                st.uses["lw70"] = st.turn
                return say("langweilig_ka")
            if re.fullmatch(r"(?:irgendwas|was|etwas) (?:lustiges|witziges|spannendes|interessantes)|überrasch mich", q):
                st.uses.pop("lw70", None)
                return self._german(st, "erzähl mir einen witz" if "lust" in q or "witz" in q else "erzähl mir einen fakt")
        if re.search(r"\bmein(?:e)? (?:chef|chefin|vorgesetzter|vorgesetzte|boss)\b.*\b(?:ständig|immer|dauernd|schon wieder)?\b.*\b(?:extra|zusätzliche|mehr|neue|noch mehr)\b.*"
                     r"\b(?:aufgaben|arbeit|projekte|sachen)\b", q) or \
                re.fullmatch(r"(?:ich habe|ich hab|hab) (?:viel )?zu viel arbeit|ich bin (?:so |total |völlig )?überlastet|ich ertrinke in arbeit", q):
            st.uses["chef70"] = st.turn
            st.last_exp = {"valence": "negative", "topic": "work", "person": True, "text": msg, "turn": st.turn, "text_en": "my boss gives me too much work"}
            return Reply(msg, "empathy", self._pick(st, "de:g70:chef", g["chef"]), via="german")
        ch = st.uses.get("chef70")
        if ch is not None and st.turn - ch <= 4 and re.fullmatch(r"(?:und )?(?:was soll ich (?:machen|tun)|keine ahnung,? was ich (?:machen|tun) soll|"
                                                                 r"hast du (?:einen )?(?:tipp|rat|idee)|was würdest du (?:machen|tun)|ja,? (?:viel )?zu viel)", q):
            st.uses.pop("chef70")
            return say("chef_rat")
        rm = re.fullmatch(r"(?:ich|wir) (?:fahre|fahren|fliege|fliegen|reise|reisen|gehe|gehen) (?:nächste woche|morgen|bald|im sommer|übermorgen|am wochenende|"
                          r"in (?:zwei|drei|\d) wochen)? ?nach (?P<p>[a-zäöüß]+(?: [a-zäöüß]+)?)(?: nächste woche| im sommer| am wochenende)?", q)
        if rm:
            st.uses["reise70"] = [rm.group("p"), st.turn]
            return say("reise", X=_de_place_case(rm.group("p")))
        re70 = st.uses.get("reise70")
        if re70 and st.turn - re70[1] <= 5:
            if re.fullmatch(r"(?:hast du |irgendwelche |ein paar )?(?:tipps|tips|ratschläge)(?: für mich| für die reise| dafür)?|was sollte ich wissen", q):
                st.uses["reise70"] = [re70[0], st.turn]
                return say("reise_tipps", X=_de_place_case(re70[0]))
            if re.fullmatch(r"(?:und )?(?:zum essen|was ist mit (?:dem )?essen|essen|was soll ich (?:dort |da )?essen|wo (?:soll|kann) ich (?:gut )?essen|essenstipps)", q):
                key = re70[0] if re70[0] in g["reise_essen"] else "sonst"
                return sub("reise_essen", key, X=_de_place_case(re70[0]))
        tm = re.fullmatch(r"(?:und )?wie sagt man (?P<w>[a-zäöüß' ]+?) auf (?P<l>italienisch|französisch|spanisch|englisch|portugiesisch)", q)
        if tm:
            from engramm.chat.tools import _PHRASES
            words = {"danke": "thank you", "danke schön": "thank you", "hallo": "hello", "tschüss": "bye", "auf wiedersehen": "goodbye",
                     "bitte": "please", "ja": "yes", "nein": "no", "guten morgen": "good morning", "gute nacht": "good night",
                     "wie geht's": "how are you", "wie gehts": "how are you", "ich liebe dich": "i love you", "entschuldigung": "sorry",
                     "prost": "cheers", "willkommen": "welcome", "ich heiße": "my name is"}
            langs = {"italienisch": "italian", "französisch": "french", "spanisch": "spanish", "englisch": "english", "portugiesisch": "portuguese"}
            w = tm.group("w").strip()
            en = words.get(w)
            if en and langs[tm.group("l")] == "english":
                return Reply(msg, "tool", f"Auf Englisch heißt „{w}“ „{en}“.", via="tool")
            hit = _PHRASES.get(en or "", {}).get(langs[tm.group("l")])
            if hit:
                return Reply(msg, "tool", f"Auf {cap(tm.group('l'))} heißt „{w}“ „{hit}“.", answer=hit, via="tool")
            return Reply(msg, "tool", f"Ich kenne nur ein paar Alltagswörter in anderen Sprachen – „{w}“ auf {cap(tm.group('l'))} gehört leider nicht dazu.", via="tool")
        df = re.fullmatch(r"(grazie|merci|gracias|obrigado|obrigada|arigato)(?: mille| beaucoup)?", q)
        if df:
            return sub("danke_fremd", df.group(1))
        if re.fullmatch(r"(?:hast du|kannst du) (?:echte )?gefühle(?: haben)?|fühlst du (?:was|etwas|dich)|bist du traurig|bist du glücklich", q):
            return say("gefuehle")
        if re.fullmatch(r"(?:sorry,? )?wie heißt du (?:noch ?mal|gleich|nochmal)|wie war dein name (?:noch ?mal|gleich)|wer bist du (?:noch ?mal|gleich)", q):
            return say("name")
        if re.fullmatch(r"wer hat dich (?:gemacht|gebaut|programmiert|erfunden|entwickelt|erschaffen)|wer ist dein (?:erfinder|entwickler|schöpfer)", q):
            return say("macher")
        for fk in g.get("fakten", []):
            if re.fullmatch(fk["q"], q):
                if fk.get("en"):                          # the English fact's follow-ups apply too ("wie lange braucht licht dahin?")
                    item = next((it for it in self.bank.daily.get("common", []) if re.fullmatch(it["q"], fk["en"])), None)
                    if item is not None and item.get("follow"):
                        st.uses["common_follow"] = [item["follow"], st.turn]
                    if item is not None and item.get("t"):
                        self.bot.context.update({"answer": None, "atype": None, "mention": item["t"], "kb_last": None})
                return Reply(msg, "answer", fk["a"], answer=fk.get("v"), via="common", confidence=1.0)
        sup = re.fullmatch(r"(?:und )?(?:was|welche[rs]?|wie heißt) (?:ist )?(?:der|die|das) (?P<a>größte|grösste|kleinste) (?P<n>planet|ozean|kontinent|tier|wüste)"
                           r"(?: der welt| auf der welt| der erde| im sonnensystem| unseres sonnensystems)?", q)
        if sup:
            key = f"{sup.group('a').replace('grösste', 'größte')} {sup.group('n')}"
            if key in g["superlativ"]:
                return Reply(msg, "answer", g["superlativ"][key], via="common", confidence=1.0)
        if re.fullmatch(r"wie heißt du(?: eigentlich)?|wie ist dein name|wie war dein name", q):
            return say("name")
        hw = re.fullmatch(r"(?:und )?wie (?P<a>hoch|lang|groß|tief) war (?P<x>sie|er|es|der [a-zäöüß ]+|die [a-zäöüß ]+|das [a-zäöüß ]+)", q)
        if hw:
            return self._german_question(st, msg, q.replace(" war ", " ist ", 1))
        fa = re.fullmatch(r"(?:und )?wer hat (?P<x>sie|ihn|es|den [a-zäöüß ]+|die [a-zäöüß ]+|das [a-zäöüß ]+) (?:zuerst|als erstes|als erster|erstmals) bestiegen", q)
        if fa:
            ment = self.bot.context.get("mention") if fa.group("x") in ("sie", "ihn", "es") else re.sub(r"^(?:den|die|das) ", "", fa.group("x"))
            if not ment:
                return Reply(msg, "clarify", "Welchen Berg meinst du?", via="german")
            r = self._question(st, f"who first climbed {ment}?")
            if r.kind == "answer" and r.answer:
                return Reply(msg, "answer", f"Erstbestiegen wurde {cap(str(ment))} von {r.answer}.", answer=r.answer, evidence=r.evidence,
                             source=r.source, via="german", confidence=r.confidence)
            art = (st.uses.get("de_art") or {}).get(str(ment).lower(), "")
            ment = f"{art} {cap(str(ment))}".strip()
            return Reply(msg, "unknown", f"Wer {ment} zuerst bestiegen hat, weiß ich leider nicht – dazu habe ich nichts Verlässliches gelesen.",
                         via="german")
        return None

    def _german_ctx68(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 68 in German: "und sonst so?", "warum?" after ENGRAMM's favourite, cats or dogs, "ich bin ein
        Katzenmensch", "redest du gern mit mir?"."""
        g = (self.bank.de["daily"].get("ctx") or {}).get("g68")
        if not g:
            return None
        q = s.strip(" .!?")
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"de:g68:{key}", g[key], **kw), via="german")  # noqa: E731
        g9 = (self.bank.de["daily"].get("ctx") or {}).get("g69") or {}
        q = re.sub(r"\s+", " ", re.sub(r"[^\w\s',-]", " ", q)).strip()
        fr = st.uses.get("day_off_de")
        if g9 and re.search(r"\bausschlafen\b", q) and fr is not None and st.turn - fr <= 3:
            st.uses["day_off_de"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "de:g69:ausschlafen", g9["ausschlafen"]), via="german")
        if re.fullmatch(r"(?:und )?(?:sonst so|was gibt'?s neues|was gibts neues|alles klar bei dir|was geht bei dir|und bei dir so)", q):
            return say("sonst")
        bf = st.uses.get("de_bot_fav")
        if bf and st.turn - bf[1] <= 2 and bf[0] in g["fav_why"] and \
                re.fullmatch(r"(?:und )?(?:warum|wieso|weshalb|warum der|warum das|warum die|warum gerade (?:der|die|das)(?: da)?|was magst du daran)", q):
            st.uses.pop("de_bot_fav")
            return Reply(msg, "smalltalk", self._pick(st, f"de:g68:why:{bf[0]}", g["fav_why"][bf[0]]), via="german")
        if re.fullmatch(r"(?:und |also )?(?:magst du (?:lieber )?(?:katzen|hunde) oder (?:katzen|hunde)(?: lieber)?|(?:katzen|hunde) oder (?:katzen|hunde)|"
                        r"bist du (?:eher )?(?:team )?(?:katze|hund) oder (?:team )?(?:katze|hund))", q):
            return say("katze_hund")
        pm = re.fullmatch(r"ich bin (?:eher |total |voll |definitiv |ein )*(?:ein |eine )?(?P<x>katzen|hunde)(?:mensch|person|typ)", q)
        if pm:
            x = "Katze" if pm.group("x") == "katzen" else "Hund"
            self._learn(st, [f"I like {'cats' if x == 'Katze' else 'dogs'}."], msg)
            return Reply(msg, "learned", self._pick(st, "de:g68:person", g["person"], x=x).replace("eine{n}", "eine" if x == "Katze" else "einen"),
                         via="german")
        if re.fullmatch(r"(?:redest|sprichst|plauderst|chattest) du gern(?:e)? mit mir|magst du (?:es,? )?mit mir zu (?:reden|plaudern)|magst du mich", q):
            return say("reden")
        return None

    def _german_ctx65(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 65 in German: loneliness and making friends, grief and memories, feeling not good enough,
        hopelessness (a gentle check-in with help numbers), a panic attack, presentation nerves, a breakup."""
        g = (self.bank.de["daily"].get("ctx") or {}).get("g65")
        if not g:
            return None
        q = s.strip(" .!?")
        pk = lambda key, opts, **kw: self._pick(st, f"de:g65:{key}", opts, **kw)          # noqa: E731
        recent = lambda key, k=3: (st.uses.get(key) and st.turn - st.uses[key][-1] <= k)   # noqa: E731
        if re.search(r"\b(?:neue stadt|umgezogen|hergezogen)\b", q) and re.search(r"\b(?:kenne niemanden|kenne keinen|niemanden kenne|allein)\b", q):
            st.uses["alone65"] = [st.turn]
            return Reply(msg, "empathy", pk("new_city", g["new_city"]), via="german")
        if re.fullmatch(r"wie (?:findet man|finde ich) (?:als erwachsene[rn]? |neue )?freunde(?: als erwachsene[rn]?| in einer neuen stadt)?", q):
            st.uses["alone65"] = [st.turn]
            return Reply(msg, "smalltalk", g["friends_tips"], via="german")
        if re.fullmatch(r"(?:aber )?ich bin (?:aber )?(?:eher |ziemlich |sehr |total |etwas |ein bisschen )?(?:schüchtern|introvertiert|zurückhaltend)(?: aber)?", q):
            return Reply(msg, "smalltalk", pk("shy", g["shy"]), via="german")
        if re.search(r"\b(?:gestorben|verstorben|beerdigung|ist tot)\b", q):
            st.uses["grief65"] = [st.turn, "sie" if re.search(r"\b(?:oma|mama|mutter|schwester|tante|frau|freundin|tochter)\b", q) else "er"]
            return None                                   # the grief feeling answers
        gr = st.uses.get("grief65")
        if gr and st.turn - gr[0] <= 5:
            p_, d_ = gr[1], {"er": "ihm", "sie": "ihr"}[gr[1]]
            a_ = {"er": "ihn", "sie": "sie"}[gr[1]]
            if re.fullmatch(r"wir (?:standen uns|waren uns) (?:sehr |so |total |richtig )?(?:nahe|nah)|(?:er|sie) war (?:wie )?mein(?:e)? (?:bester? freund(?:in)?|held(?:in)?)", q):
                gr[0] = st.turn
                return Reply(msg, "smalltalk", pk("close", g["close"], p=p_), via="german")
            if re.fullmatch(r"(?:er|sie) hat mir (?:das |den |die )?[a-zäöüß ]{2,30} beigebracht|(?:er|sie) hat (?:immer|oft) [a-zäöüß ]{2,30}", q):
                gr[0] = st.turn
                return Reply(msg, "smalltalk", pk("memory", g["memory"], d=d_), via="german")
            if re.fullmatch(r"ich vermisse (?:ihn|sie)(?: so| sehr| so sehr)?", q):
                gr[0] = st.turn
                return Reply(msg, "empathy", pk("miss", g["miss"], d=a_, p=p_), via="german")
        if re.search(r"\b(?:nicht gut genug|nicht klug genug|ein versager|eine versagerin|so dumm|wertlos|nutzlos)\b", q):
            st.uses["imp65"] = [st.turn]
            return None
        if recent("imp65", 3):
            if re.search(r"\b(?:alle|jeder|die anderen|alle kollegen)\b.*\b(?:klüger|besser|schlauer|talentierter|schneller)\b", q):
                st.uses["imp65"] = [st.turn]
                return Reply(msg, "smalltalk", pk("impostor", g["impostor"]), via="german")
            if re.search(r"\b(?:alles hinschmeißen|alles hinwerfen|alles aufgeben|was soll das alles|hat alles keinen sinn)\b", q):
                return Reply(msg, "empathy", g["check_in"], via="german")
        if re.fullmatch(r"(?:niemand|keiner|keine sau) (?:interessiert sich für mich|mag mich|kümmert sich um mich|würde mich vermissen)", q):
            st.uses["nobody65"] = [st.turn]
            return Reply(msg, "empathy", pk("nobody", g["nobody"]), via="german")
        if recent("nobody65", 4):
            if re.fullmatch(r"nicht (?:mal|einmal) (?:meine |mein )?(?:familie|eltern|freunde|mama|papa|partner(?:in)?)", q):
                st.uses["nobody65"] = [st.turn]
                return Reply(msg, "empathy", pk("not_even", g["not_even"]), via="german")
            if re.search(r"\b(?:warum ich mir (?:überhaupt )?mühe gebe|hat (?:alles )?keinen sinn|was soll das alles|ich kann nicht mehr|bringt (?:alles )?nichts)\b", q):
                return Reply(msg, "empathy", g["check_in"], via="german")
        if re.search(r"\bpanikattacke\b", q):
            st.uses["panic65"] = [st.turn]
            return Reply(msg, "empathy", pk("panic", g["panic"]), via="german")
        if recent("panic65", 3):
            if re.fullmatch(r"(?:das|es) war (?:so |echt |total |richtig )?(?:schlimm|furchtbar|schrecklich|beängstigend|heftig)", q):
                st.uses["panic65"] = [st.turn]
                return Reply(msg, "empathy", pk("panic_bad", g["panic_bad"]), via="german")
            if re.search(r"\bwas kann ich (?:tun|machen)\b|\bwas hilft\b|\btipps\b", q):
                return Reply(msg, "smalltalk", g["panic_tips"], via="german")
        if re.search(r"\b(?:präsentation|vortrag|referat|rede)\b", q) and re.search(r"\b(?:nervös|aufgeregt|angst|panik)\b", q):
            st.uses["pres65"] = [st.turn]
            return Reply(msg, "empathy", pk("presentation", g["presentation"]), via="german")
        if recent("pres65", 3) and re.search(r"\bwas,? wenn ich\b.*\b(?:verhaspel|verspreche|stecken bleibe|blackout|versage|vergesse)", q):
            return Reply(msg, "empathy", pk("mess_up", g["mess_up"]), via="german")
        if re.search(r"\b(?:schluss gemacht|getrennt|trennung)\b", q):
            st.uses["breakup65"] = [st.turn]
            if not re.match(r"^(?:ich|wir)\b", q):
                return None                               # "meine freundin hat schluss gemacht": the feeling answers
            st.last_exp = {"valence": "negative", "topic": None, "person": True, "text": msg, "text_en": _de_advice_hint(s),
                           "turn": st.turn}                # "wir waren 2 jahre zusammen" follows
            return Reply(msg, "empathy", pk("breakup", g["breakup"]), via="german")
        if recent("breakup65", 4):
            if re.search(r"\bmeine entscheidung\b|\bich habe? schluss gemacht\b", q) and re.search(r"\b(?:weh|trotzdem|schwer)\b", q):
                st.uses["breakup65"] = [st.turn]
                return Reply(msg, "empathy", pk("my_choice", g["my_choice"]), via="german")
            if re.search(r"\bbefreundet bleiben\b|\bfreunde bleiben\b", q):
                return Reply(msg, "smalltalk", pk("friends", g["friends"]), via="german")
        return None

    def _german_ctx63(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 63 in German: "nein, ich meinte in Europa", a language choice with reasons, "versteh ich nicht"
        after a joke, sums said in passing, quitting a job, saying no politely, and banter about the bot."""
        g = (self.bank.de["daily"].get("ctx") or {}).get("g63")
        if not g:
            return None
        q = s.strip(" .!?")
        pk = lambda key, opts, **kw: self._pick(st, f"de:g63:{key}", opts, **kw)          # noqa: E731
        mm = re.fullmatch(r"(?:nein,? |ne,? |sorry,? )?ich meinte (?:in|auf|für) (?P<x>[a-zäöüß ]{3,30})", q)
        last_en = st.uses.get("de_last_en")
        if mm and last_en and st.turn - last_en[0] <= 2 and re.search(r"\bin the world\b", last_en[1]):
            from engramm.chat.german_bridge import EXONYMS
            place = {"europa": "europe", "afrika": "africa", "südamerika": "south america", "nordamerika": "north america",
                     "australien": "australia", "der antarktis": "antarctica", "antarktis": "antarctica", "deutschland": "germany",
                     "den alpen": "the alps"}.get(mm.group("x"), EXONYMS.get(mm.group("x"), mm.group("x")).lower())
            qen = re.sub(r"\bin the world\b", f"in {place}", last_en[1])
            rep = self._question(st, qen)
            st.uses["de_last_en"] = [st.turn, qen]
            if rep.kind == "answer":
                item = next((it for it in self.bank.daily.get("common", []) if isinstance(it, dict) and it.get("a") == rep.text), None)
                if item and item.get("t"):
                    self.bot.context.update({"answer": item["t"], "atype": None, "mention": item["t"], "kb_last": None})
                rep.text = f"{self.bank.de['daily']['english_text']} {rep.text}"
                rep.message = msg
                return rep
        hm = re.search(r"(\d[\d,]*) m \(([\d,]+) ft\)", st.last_reply or "")
        if hm and st.uses.get("last_via") == "common" and re.fullmatch(r"(?:und )?wie hoch ist (?:er|der|sie|es|das)(?: denn)?", q):
            item = next((it for it in self.bank.daily.get("common", []) if isinstance(it, dict) and
                         it.get("a") and it["a"] in (st.last_reply or "")), None)
            name = (item or {}).get("t") or "Er"
            return Reply(msg, "answer", f"{name} ist {hm.group(1).replace(',', '.')} m hoch.", answer=hm.group(1), via="common",
                         confidence=1.0)
        dm = re.fullmatch(r"soll ich (?:lieber )?(?P<a>[a-zäöüß]+) oder (?P<b>[a-zäöüß]+) lernen", q)
        why = g["decide_why"]
        if dm and dm.group("a") in why and dm.group("b") in why:
            a_, b_ = why[dm.group("a")], why[dm.group("b")]
            x, y = (a_, b_) if a_["r"] >= b_["r"] else (b_, a_)
            st.uses["decided_de"] = [x["x"], y["x"], st.turn]
            return Reply(msg, "smalltalk", pk("decide", g["decide"], x=x["x"], y=y["x"], a=x["a"], b=y["a"]), via="german")
        dd_ = st.uses.get("decided_de")
        if dd_ and st.turn - dd_[2] <= 3:
            if re.fullmatch(r"(?:aber )?(?:warum|wieso|weshalb)(?: das| nicht)?", q):
                a_ = next(v for v in why.values() if v["x"] == dd_[0])
                dd_[2] = st.turn
                return Reply(msg, "smalltalk", pk("reason", g["reason"], a=a_["a"]), via="german")
            cm = re.fullmatch(r"(?:ok,? |okay,? |gut,? )?(?:dann |ich nehme |ich lerne |ich mach )?(?P<x>[a-zäöüß]+)(?: dann| also)?", q)
            if cm and cm.group("x") in why:
                st.uses["chosen_de"] = [st.turn]
                st.uses.pop("decided_de", None)
                return Reply(msg, "smalltalk", pk("chosen", g["chosen"], x=why[cm.group("x")]["x"]), via="german")
        ch = st.uses.get("chosen_de")
        if ch and st.turn - ch[0] <= 3 and re.fullmatch(r"wie lange dauert (?:das|es)(?: zu lernen)?|ist (?:das|es) schwer", q):
            return Reply(msg, "smalltalk", g["learn_time"], via="german")
        la = st.last_action or {}
        if la.get("kind") == "joke" and st.turn - la.get("turn", -99) <= 1 and \
                re.fullmatch(r"(?:ich )?versteh(?:e)? (?:ich )?(?:ihn |den |das )?nicht|hä|häh|wie bitte|erklär (?:mal|ihn)", q):
            return Reply(msg, "smalltalk", pk("joke_explain", g["joke_explain"]), via="german")
        if re.fullmatch(r"bist du (?:schlauer|besser|klüger) als chatgpt|was ist der unterschied zwischen dir und chatgpt|bist du wie chatgpt", q):
            return Reply(msg, "smalltalk", g["vs_chatgpt"], via="german")
        sp = re.findall(r"(\d+(?:,\d{1,2})?) ?(?:euro|€)? (?:für|fürs|für den|für die|für das) [a-zäöüß]+", q)
        if len(sp) >= 2 and re.search(r"\bausgegeben\b|\bbezahlt\b", q):
            st.uses["sum63"] = [[float(v.replace(",", ".")) for v in sp], st.turn]
            return Reply(msg, "smalltalk", pk("spent", g["spent"]), via="german")
        sm = st.uses.get("sum63")
        if sm and st.turn - sm[1] <= 3:
            fmt = lambda v: (f"{v:,.2f}".rstrip("0").rstrip(".")).replace(".", ",")          # noqa: E731
            if re.fullmatch(r"(?:und )?wie ?viel (?:ist|macht|sind) (?:das|es)(?: zusammen| insgesamt)?|was macht das (?:zusammen|insgesamt)", q):
                sm[1] = st.turn
                return Reply(msg, "tool", f"{' + '.join(fmt(v) for v in sm[0])} = {fmt(sum(sm[0]))} Euro.", via="tool", confidence=1.0)
            am = re.fullmatch(r"(?:und )?(?:wenn ich |plus )?(?P<v>\d+(?:,\d{1,2})?)(?: ?euro)?(?: (?:für|fürs) [a-zäöüß]+)? ?(?:dazu ?rechne|dazu|dazurechne|addiere)?", q)
            if am and re.search(r"\b(?:dazu|plus|addiere|wenn ich)\b", q):
                sm[0].append(float(am.group("v").replace(",", ".")))
                sm[1] = st.turn
                return Reply(msg, "tool", pk("total", g["total"], x=fmt(sum(sm[0]))), via="tool", confidence=1.0)
        if re.search(r"\b(?:überlege|denke darüber nach|will|möchte|werde)(?: zu)? kündigen\b|\bmeinen job kündigen\b", q):
            st.uses["quit_de"] = [st.turn]
            return Reply(msg, "smalltalk", pk("quit", g["quit"]), via="german")
        qd = st.uses.get("quit_de")
        if qd and st.turn - qd[0] <= 4:
            if re.fullmatch(r"(?:aber )?ich brauche (?:das|mein|das) ?(?:geld|gehalt)|(?:aber )?ich kann es mir nicht leisten", q):
                st.uses["quit_de"] = [st.turn]
                return Reply(msg, "smalltalk", pk("quit_money", g["quit_money"]), via="german")
            if re.fullmatch(r"was würdest du (?:machen|tun)(?: an meiner stelle)?|was meinst du|was soll ich tun", q):
                st.uses["quit_de"] = [st.turn]
                return Reply(msg, "smalltalk", pk("quit_view", g["quit_view"]), via="german")
        if re.fullmatch(r"wie (?:sage|sag) ich (?:höflich |freundlich |nett )?nein(?: zu meinem chef| bei der arbeit)?", q):
            return Reply(msg, "smalltalk", g["say_no"], via="german")
        if re.fullmatch(r"(?:schläfst|träumst) du(?: eigentlich| auch| überhaupt| nie| mal)?", q):
            return Reply(msg, "smalltalk", pk("sleep", g["sleep"]), via="german")
        if re.fullmatch(r"du glückliche[rs]?|glück gehabt|beneidenswert|du hast es gut", q) and re.search(r"schlaf|träum", (st.last_reply or "").lower()):
            return Reply(msg, "smalltalk", pk("lucky", g["lucky"]), via="german")
        if re.fullmatch(r"du bist (?:echt |ganz schön |irgendwie |voll )?(?:komisch|seltsam|merkwürdig|schräg)(?: haha| lol)?", q):
            return Reply(msg, "smalltalk", pk("weird", g["weird"]), via="german")
        return None

    def _german_ctx61(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 61 in German: home from work and a long day, "und bei dir?", a hike and sore legs, music and a
        band ("kennst du queen?" → "wer war ihr sänger?"), a cold, the time in Tokyo, and the long break after exams."""
        g = (self.bank.de["daily"].get("ctx") or {}).get("g61")
        if not g:
            return None
        q = s.strip(" .!?")
        recent = lambda key, k=3: (st.uses.get(key) and st.turn - st.uses[key][-1] <= k)   # noqa: E731
        pk = lambda key, opts, **kw: self._pick(st, f"de:g61:{key}", opts, **kw)          # noqa: E731
        if re.search(r"\b(?:bin|komme) (?:gerade |eben |grad )?(?:von der arbeit|aus dem büro|von der schicht) (?:heim|zurück|nach hause|gekommen)\b|"
                     r"\bbin (?:gerade |eben )?(?:heim|nach hause) gekommen\b|\bgerade feierabend\b", q):
            st.uses["home_de61"] = [st.turn]
            return Reply(msg, "smalltalk", pk("home", g["home"]), via="german")
        if recent("home_de61", 2) and re.fullmatch(r"(?:war |ganz |eigentlich )?(?:ok|okay|gut|ganz gut|geht so|so lala)?,? ?(?:aber )?(?:ein )?(?:bisschen|bissl|etwas|ziemlich|echt|sehr) "
                                                  r"(?:lang|anstrengend|stressig|viel|zäh)", q):
            return Reply(msg, "smalltalk", pk("long_day", g["long_day"]), via="german")
        if re.fullmatch(r"(?:und )?(?:bei dir|du|dir|wie ist es bei dir|und selbst)", q):
            return Reply(msg, "smalltalk", pk("me", g["me"]), via="german")
        if re.search(r"\b(?:war|bin|waren|gehe|ging) (?:gestern |heute |am wochenende )?(?:wandern|bergsteigen|auf (?:einem|einen|dem) berg|in den bergen)\b", q):
            st.uses["hike_de61"] = [st.turn]
            return Reply(msg, "smalltalk", pk("hike", g["hike"]), via="german")
        if recent("hike_de61", 4):
            if re.fullmatch(r"(?:es )?war (?:echt |richtig |total |einfach )?(?:mega|super|toll|schön|herrlich|genial|klasse|der hammer|wunderschön)", q):
                st.uses["hike_de61"] = [st.turn]
                return Reply(msg, "smalltalk", pk("hike_good", g["hike_good"]), via="german")
            hm = re.fullmatch(r"(?:wir waren |ich war )?(?:auf (?:einem|einen|dem) )?(?:berg|gipfel|hügel)? ?(?:bei|nahe|in der nähe von|um) (?P<p>[a-zäöüß ]{3,25})", q)
            if hm:
                st.uses["hike_de61"] = [st.turn]
                return Reply(msg, "smalltalk", pk("hike_where", g["hike_where"], x=_de_place_case(hm.group("p"))), via="german")
            hh = re.fullmatch(r"(?:so |etwa |ungefähr |fast |knapp |circa )?(?P<h>\d+|zwei|drei|vier|fünf|sechs|sieben|acht)(?:einhalb)? stunden?", q)
            if hh:
                st.uses["hike_de61"] = [st.turn]
                return Reply(msg, "smalltalk", pk("hike_hours", g["hike_hours"], x=hh.group("h")), via="german")
            if re.search(r"\b(?:beine|füße|knie|waden) (?:tun|tut) (?:mir )?(?:so |voll |echt )?weh\b|\bmuskelkater\b|\btun mir die (?:beine|füße|waden) weh\b", q):
                return Reply(msg, "smalltalk", pk("hike_sore", g["hike_sore"]), via="german")
        if re.fullmatch(r"(?:magst|hörst) du (?:gern |gerne )?musik", q):
            st.uses["music_de61"] = [st.turn]
            return Reply(msg, "smalltalk", pk("music", g["music"]), via="german")
        if recent("music_de61", 2) and re.fullmatch(r"(?:und )?(?:welche|was für welche|welche denn|was hörst du|und du)", q):
            return Reply(msg, "smalltalk", pk("music_mine", g["music_mine"]), via="german")
        kb_ = re.fullmatch(r"kennst du (?:die band |die gruppe )?(?P<x>[a-z0-9][a-z0-9 .&'-]{1,30})", q)
        if kb_ and self.kgqa is not None:
            try:
                hits = self.kgqa.kb.link(kb_.group("x"), limit=3)
            except Exception:
                hits = []
            ent = next((e for e, _ in hits if (e.type or "") in ("Band", "MusicalArtist", "Group") and
                        title_key(re.sub(r"\s*\([^)]*\)$", "", e.title)) == title_key(kb_.group("x"))), None)
            if ent is not None:
                name = re.sub(r"\s*\([^)]*\)$", "", ent.title)
                found = self.about.find(ent.title, n=1)
                line = found.sentences[0] if found is not None and found.sentences else ""
                st.topic = {"title": ent.title, "name": name, "turn": st.turn}
                self.bot.context.update({"answer": None, "atype": None, "mention": name, "kb_last": None})
                return Reply(msg, "smalltalk", pk("band", g["band"] if line else g["band"][1:], x=name, y=line), via="german")
        tp_ = st.topic or {}
        sm = re.fullmatch(r"(?:und )?wer (?:ist|war) (?:ihr|der|sein|deren) (?:leadsänger|sänger|frontmann|sängerin)", q)
        if sm and tp_.get("name") and st.turn - tp_.get("turn", -99) <= 3:
            rep = self._question(st, f"who was the lead singer of {tp_['name']}?")
            if rep.kind == "answer" and rep.answer:
                return Reply(msg, "answer", pk("singer", g["singer"], x=rep.answer), answer=rep.answer, evidence=rep.evidence,
                             source=rep.source, via="german", confidence=rep.confidence)
        if re.search(r"\b(?:ich )?(?:glaub|glaube|denke) ich werde krank\b|\bwerde (?:wohl )?krank\b|\bbin (?:wohl )?krank\b|\bmir geht'?s nicht gut\b", q):
            st.uses["sick_de61"] = [st.turn]
            if re.fullmatch(r"(?:oh mann,? |mist,? )?(?:ich )?(?:glaub|glaube|denke),? ich werde (?:wohl )?krank|ich werde (?:wohl )?krank", q):
                return Reply(msg, "empathy", pk("sick", g["sick"]), via="german")
        if recent("sick_de61", 4):
            if re.fullmatch(r"(?:ich hab |hab )?(?:(?:halsweh|halsschmerzen|kopfweh|kopfschmerzen|schnupfen|husten|fieber|gliederschmerzen)(?:,? (?:und )?)?)+", q):
                st.uses["sick_de61"] = [st.turn]
                return Reply(msg, "smalltalk", pk("symptoms", g["symptoms"]), via="german")
            if re.search(r"\bsoll ich (?:morgen |heute )?(?:arbeiten|zur arbeit|in die arbeit|ins büro)(?: gehen)?\b", q):
                st.uses["sick_de61"] = [st.turn]
                return Reply(msg, "smalltalk", pk("work_sick", g["work_sick"]), via="german")
        if re.fullmatch(r"(?:ok,? )?(?:danke,? )?(?:ich bleib|ich bleibe|bleib) (?:dann )?(?:zu ?hause|daheim|im bett)(?: dann)?", q):
            return Reply(msg, "smalltalk", pk("stay_home", g["stay_home"]), via="german")
        tq = re.fullmatch(r"(?:und |wie ist es |wie spät ist es )?in (?P<p>[a-zäöüß .'-]{2,25})", q)
        if tq and re.search(r"\d{1,2}:\d\d Uhr", st.last_reply or ""):
            from engramm.chat.german_bridge import EXONYMS
            p_en = EXONYMS.get(tq.group("p"), tq.group("p")).lower()
            wt = self._world_time(st, f"what time is it in {p_en}?")
            hm2 = re.search(r"\b(\d{1,2}):(\d\d)\b", wt.text) if wt is not None else None
            if hm2:
                st.uses["time_place_de61"] = [p_en, tq.group("p"), st.turn]
                return Reply(msg, "tool", f"In {_de_place_case(tq.group('p'))} ist es gerade {hm2.group(1)}:{hm2.group(2)} Uhr.", via="tool",
                             confidence=1.0)
        nm = re.fullmatch(r"ist (?:es )?(?:dort|da|da drüben) (?:jetzt |gerade )?(?P<w>nacht|tag|morgen|abend|dunkel|spät)", q)
        tp = st.uses.get("time_place_de61")
        if nm and tp and st.turn - tp[2] <= 4:
            wt = self._world_time(st, f"what time is it in {tp[0]}?")
            hm2 = re.search(r"\b(\d{1,2}):(\d\d)\b", wt.text) if wt is not None else None
            if hm2:
                h = int(hm2.group(1))
                part = "Nacht" if h >= 21 or h < 5 else "Morgen" if h < 12 else "Nachmittag" if h < 18 else "Abend"
                w = nm.group("w")
                yes = (w in ("nacht", "dunkel", "spät") and part in ("Nacht", "Abend")) or (w == "tag" and part in ("Morgen", "Nachmittag")) or \
                    w == part.lower()
                key = "part_yes" if yes else "part_no"
                y = {"Nacht": "Nacht", "Morgen": "Vormittag", "Nachmittag": "Nachmittag", "Abend": "Abend"}[part]
                return Reply(msg, "tool", pk(key, g[key], x=f"{hm2.group(1)}:{hm2.group(2)}", y=y, z=_de_place_case(tp[1])), via="tool",
                             confidence=1.0)
        if re.search(r"\b(?:prüfungen|klausuren|examen|abschlussprüfung|abitur|abi) (?:sind )?(?:fertig|geschafft|vorbei|durch|hinter mir|bestanden)\b|"
                     r"\b(?:hab|habe) (?:meine |die |alle )?(?:prüfungen|klausuren|examen) (?:fertig|geschafft|hinter mir|bestanden)\b", q):
            st.uses["exams_de61"] = [st.turn]
            return Reply(msg, "smalltalk", pk("exams", g["exams"]), via="german")
        if recent("exams_de61", 4):
            if re.fullmatch(r"(?:ich )?(?:glaub|glaube|denke|hoffe)?,? ?(?:sie|die|es|alle) (?:liefen|lief|sind|waren|gingen) (?:ganz |echt |richtig )?(?:gut|super|okay|ok)(?: gelaufen)?", q):
                st.uses["exams_de61"] = [st.turn]
                return Reply(msg, "smalltalk", pk("exams_well", g["exams_well"]), via="german")
            om = re.fullmatch(r"(?:und )?(?:jetzt )?(?:hab|habe) ich (?P<x>(?:\d+|ein paar|zwei|drei|vier|sechs) (?:wochen|monate|tage)) (?:frei|ferien|urlaub|pause)", q)
            if om:
                st.uses["exams_de61"] = [st.turn]
                st.uses["break_de61"] = [st.turn]
                return Reply(msg, "smalltalk", pk("time_off", g["time_off"], x=om.group("x").replace("monate", "Monate").replace("wochen", "Wochen")),
                             via="german")
        if recent("break_de61", 3) and re.search(r"\bwas (?:soll|kann|könnte) ich\b.*\bmachen\b", q):
            return Reply(msg, "smalltalk", g["break_ideas"], via="german")
        return None

    def _de_statement(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """A German statement nothing else understood: a reply to its mood, never "Das verstehe ich leider nicht"."""
        g = (self.bank.de["daily"].get("ctx") or {}).get("g61")
        q = s.strip(" .!")
        if not g or "?" in msg or len(q.split()) < 2 or re.match(r"^(?:wer|was|wann|wo|wie|welche[rsmn]?|warum|wieso|weshalb|woher|wohin|kannst|könntest|"
                                                                r"hast du|bist du|weißt du|magst du|kennst du)\b", q):
            return None
        if re.search(r"\b(?:mega|super|toll|schön|geil|klasse|cool|spitze|genial|lustig|spaß|perfekt|wunderbar|herrlich|gut gelaufen|gefreut|glücklich)\b", q):
            key = "stmt_pos"
        elif re.search(r"\b(?:weh|krank|müde|stress|stressig|schlecht|mies|doof|nervig|anstrengend|kaputt|traurig|ärger|blöd|scheiße|mist|sauer|genervt|"
                       r"schlimm|furchtbar|schrecklich|gestorben|tot|vermisse|allein|einsam|angst|panik|schluss|getrennt|verloren|wehgetan)\b", q):
            key = "stmt_neg"
        elif (re.match(r"^(?:ich|wir|mein|meine|meinem|meinen|heute|gestern|vorhin|letzte|am wochenende)\b", q) or
              re.match(r"^(?:die|der|das|unser|unsere|meine|mein|deren|alle)\b[\wäöüß ]{2,40}\b(?:haben|hat|war|waren|ist|sind|wurde|wurden|gab|ging|"
                       r"gingen|kam|kamen|machte|machten|hatte|hatten)\b", q)) and \
                not re.search(r"\b(?:nicht|meinte|überlege|verstehe|versteh)\b", q):
            key = "stmt_plain"                            # a story in the first person: ask for more
        else:
            return None
        st.last_exp = {"valence": {"stmt_neg": "negative", "stmt_pos": "positive"}.get(key, "neutral"), "topic": None, "person": False, "text": msg,
                       "text_en": _de_advice_hint(s), "turn": st.turn}
        return Reply(msg, "smalltalk", self._pick(st, f"de:g61:{key}", g[key]), via="german")

    def _german_ctx57(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """Battery 57 in German: a new puppy and its name, an empty fridge, work after a sleepless night, a dead
        phone (never grief), rain on a run, a friend moving away (missing her is no bereavement)."""
        g = (self.bank.de["daily"].get("ctx") or {}).get("g57")
        if not g:
            return None
        q = s.strip(" .!?")
        recent = lambda key, k=3: (st.uses.get(key) and st.turn - st.uses[key][-1] <= k)   # noqa: E731
        pk = lambda key, opts, **kw: self._pick(st, f"de:g57:{key}", opts, **kw)          # noqa: E731
        if re.fullmatch(r"(?:rat|rate) mal|weißt du was|stell dir vor|du glaubst nicht,? was passiert ist", q):
            return Reply(msg, "smalltalk", pk("guess", g["guess"]), via="german")
        pm = re.fullmatch(r"(?:rate mal,? )?(?:ich|wir) (?:hab|habe|haben) (?:jetzt )?(?:einen|ein|eine) (?:neuen |neues |neue |kleinen |kleines |kleine )?"
                          r"(?P<x>welpen|hund|kätzchen|katze|kaninchen|hasen|hamster)(?: bekommen| adoptiert| geholt)?", q)
        if pm:
            x = {"welpen": "Welpe", "hund": "Hund", "kätzchen": "Kätzchen", "katze": "Katze", "kaninchen": "Kaninchen",
                 "hasen": "Hase", "hamster": "Hamster"}[pm.group("x")]
            st.uses["new_pet_de"] = [x, None, None, st.turn]
            fem, neut = x == "Katze", x in ("Kätzchen", "Kaninchen")
            return Reply(msg, "smalltalk", pk("pet_new", g["pet_new"], x=x, a="Eine" if fem else "Ein", b="eine" if fem else "ein",
                                              y="eine" if fem else "eins" if neut else "einer"), via="german")
        pet = st.uses.get("new_pet_de")
        if pet and (st.uses.get("pet_name_de") or pet[2]):   # "wie heißt mein hund nochmal?", "was für ein hund ist er?"
            tiere = r"(?:hund|welpe|katze|kätzchen|kaninchen|hase|hamster|haustier)"
            nm = st.uses.get("pet_name_de")
            gg = pet[1] or {"Katze": "sie", "Kätzchen": "es", "Kaninchen": "es"}.get(pet[0], "er")
            if nm and re.fullmatch(rf"(?:und |also |sorry,? |moment,? )?(?:wie (?:heißt|hieß|heisst|hiess) (?:mein(?:e)? {tiere}|er|sie|es)(?: nochmal| noch mal| gleich)?"
                                   rf"|wie war (?:der name|sein name|ihr name)(?: von meinem {tiere}| meines {tiere}s?)?(?: nochmal| noch mal)?"
                                   rf"|weißt du(?: noch)?,? wie (?:mein(?:e)? {tiere}|er|sie) heißt)", q):
                poss = ("deine " if (pet[2] or pet[0]).lower().endswith(("katze", "hündin")) else "dein ") + (pet[2] or pet[0])
                return Reply(msg, "answer", pk("pet_recall_name", g["pet_recall_name"], x=nm, y=poss,
                                               z={"sie": "Sie", "es": "Es"}.get(gg, "Er")), answer=nm, via="memory", confidence=1.0)
            if pet[2] and re.fullmatch(rf"(?:und |also )?(?:was für (?:ein(?:e|en)?|eine) {tiere} (?:ist (?:er|sie|es)|ist mein(?:e)? {tiere}|hab(?:e)? ich)(?: nochmal| noch mal)?"
                                       rf"|welche rasse (?:ist|hat) (?:er|sie|es|mein(?:e)? {tiere})(?: nochmal| noch mal)?)", q):
                return Reply(msg, "answer", pk("pet_recall_kind", g["pet_recall_kind"], x=pet[2], z={"sie": "Sie", "es": "Es"}.get(gg, "Er"),
                                               y=nm or ("Deine " if pet[0] == "Katze" else "Dein ") + pet[0],
                                               b="eine" if pet[2].lower().endswith(("katze", "hündin")) else "ein"),
                             answer=pet[2], via="memory", confidence=1.0)
        if recent("new_pet_de", 4):
            pet = st.uses["new_pet_de"]
            nmm = re.fullmatch(r"(?:und )?(?:(?P<g>er|sie|es) heißt|(?:sein|ihr) name ist|(?:er|sie|es) hört auf (?:den namen )?|wir nennen (?:ihn|sie|es)) "
                               r"(?P<n>[a-zäöüß]{2,20})", q)
            if nmm:
                name = nmm.group("n").capitalize()
                st.uses["pet_name_de"] = name
                if nmm.group("g") and not pet[1]:
                    pet[1] = nmm.group("g")
                pet[3] = st.turn
                kind = {"Welpe": "Hund", "Kätzchen": "Katze"}.get(pet[0], pet[0])
                facts = [f"My {'dog' if kind == 'Hund' else 'cat' if kind == 'Katze' else 'pet'} is called {name}."]
                try:
                    self._learn(st, facts, msg)           # the memory page shows it; "wie heißt mein hund?" later
                except Exception:
                    pass
                return Reply(msg, "smalltalk", pk("pet_named", g["pet_named"], x=name), via="german")
            bm = re.fullmatch(r"(?:(?P<g>sie|er|es) ist )?(?:ein|eine|einen) (?P<b>[a-zäöüß][a-zäöüß -]{2,30}?)", q)
            if bm and pet[0] in ("Welpe", "Hund", "Kätzchen", "Katze") and not re.search(r"\b(?:so|sehr|süß|lieb)\b", bm.group("b")):
                gg = bm.group("g") or {"Katze": "sie", "Kätzchen": "es"}.get(pet[0], "er")
                b = " ".join(w if w in ("de", "la") else w[:1].upper() + w[1:] for w in bm.group("b").split())
                pet[1], pet[2], pet[3] = gg, b, st.turn
                fem = b.lower().endswith(("katze", "hündin"))
                return Reply(msg, "smalltalk", pk("pet_breed", g["pet_breed"], x=b, p=gg, d={"sie": "sie", "er": "ihn"}.get(gg, "es"),
                                                  a="Eine" if fem else "Ein", b="eine" if fem else "ein"), via="german")
            if re.search(r"\bnamen", q) and re.search(r"\b(?:idee|ideen|vorschl|vorschläge|hast du|weißt du|wie soll)", q):
                key = {"sie": "female", "er": "male"}.get(pet[1] or "", "any")
                pool = g["pet_pool"][key]
                k = int(hashlib.md5(f"{st.conversation}:{st.turn}".encode()).hexdigest(), 16) % len(pool)
                names = (pool[k:] + pool[:k])[:3]
                st.uses["pet_names_de"] = [names, st.turn]
                pet[3] = st.turn
                return Reply(msg, "smalltalk", pk("pet_names_lead", g["pet_names_lead"]) + "\n\n" + "\n".join(f"• {x}" for x in names) +
                             "\n\n" + pk("pet_names_tail", g["pet_names_tail"]), via="german")
            nl = st.uses.get("pet_names_de")
            if nl and st.turn - nl[1] <= 2:
                om = re.search(r"\b(?:der |die |den )?(erste|ersten|zweite|zweiten|dritte|dritten|letzte|letzten)\b", q)
                pick = None
                if om:
                    idx = {"erste": 0, "ersten": 0, "zweite": 1, "zweiten": 1, "dritte": 2, "dritten": 2, "letzte": -1, "letzten": -1}[om.group(1)]
                    pick = nl[0][idx]
                pick = pick or next((x for x in nl[0] if re.search(rf"\b{x.lower()}\b", q)), None)
                if pick and not re.search(r"\b(?:nicht|kein|keiner)\b", q):
                    st.uses.pop("pet_names_de", None)
                    return Reply(msg, "smalltalk", pk("pet_pick", g["pet_pick"], x=pick), via="german")
        if re.search(r"\b(?:hab|habe) (?:so |solchen |riesigen |voll )?hunger\b|\bbin (?:so |total )?hungrig\b", q):
            st.uses["hungry_de"] = [st.turn]
        if re.fullmatch(r"(?:aber |und |ugh,? )?(?:der |mein )?kühlschrank ist (?:komplett |total |fast )?leer|(?:aber |und )?ich hab(?:e)? nichts (?:mehr )?(?:zu hause|im kühlschrank|zu essen)", q):
            st.uses["fridge_de"] = [st.turn]
            return Reply(msg, "smalltalk", pk("fridge_empty", g["fridge_empty"]), via="german")
        if recent("fridge_de", 3) or recent("hungry_de", 3):
            im = re.fullmatch(r"(?:ich hab(?:e)? |da sind |es gibt )?(?:nur|bloß|noch) (?:noch )?(?P<i>[a-zäöüß ,]+?)(?: und das war'?s)?", q)
            if im:
                words = set(re.findall(r"[a-zäöüß]+", im.group("i")))
                norm_ = {"ei": "eier", "eier": "eier", "käse": "käse", "brot": "brot", "toast": "brot", "nudeln": "nudeln", "pasta": "nudeln",
                         "spaghetti": "nudeln", "reis": "reis"}
                items = {norm_.get(w) for w in words} - {None}
                for dish in g["dishes"]:
                    if all(x in items for x in dish["need"]):
                        st.uses["dish_de"] = [dish["t"], st.turn]
                        return Reply(msg, "smalltalk", pk("fridge_dish", g["fridge_dish"], x=dish["x"], y=dish["y"]), via="german")
                return Reply(msg, "smalltalk", pk("fridge_none", g["fridge_none"]), via="german")
        dd_ = st.uses.get("dish_de")
        if dd_ and st.turn - dd_[1] <= 3 and re.search(r"\bwie lange\b", q):
            return Reply(msg, "smalltalk", dd_[0], via="german")
        le0 = st.last_exp or {}
        if le0 and st.turn - le0.get("turn", -99) <= 3 and re.search(r"schlaf|nacht|wach", le0.get("text") or "") and \
                re.fullmatch(r"(?:und |aber )?(?:morgen|morgen früh|gleich) (?:muss ich|hab ich|habe ich) (?:arbeiten|zur arbeit|schule|uni|eine prüfung|ein meeting|früh raus)"
                             r"(?: (?:gehen|raus|früh))?", q):
            st.last_exp = dict(le0, turn=st.turn)
            return Reply(msg, "empathy", pk("sleep_work", g["sleep_work"]), via="german")
        dm = re.fullmatch(r"(?:mist,? |oh mann,? )?mein (?P<x>handy|laptop|akku|tablet|ipad|iphone|smartphone) ist (?:tot|leer|aus|gestorben|kaputt gegangen)(?: schon wieder)?", q)
        if dm:
            return Reply(msg, "smalltalk", pk("device", g["device"], x={"akku": "Akku"}.get(dm.group("x"), dm.group("x").capitalize())), via="german")
        if re.fullmatch(r"(?:und |aber )?ich finde (?:mein|das|kein) (?:ladekabel|ladegerät|kabel)(?: nicht)?", q):
            return Reply(msg, "smalltalk", pk("charger", g["charger"]), via="german")
        wm = re.fullmatch(r"(?:boah,? |man,? |ugh,? )?(?:es )?(?P<w>regnet|schüttet|schneit|ist (?:so |total |echt |richtig )?(?:kalt|eiskalt|heiß|warm|sonnig))"
                          r"(?: (?:schon )?wieder| heute| draußen| hier)*", q)
        if wm and "?" not in msg:
            w = wm.group("w")
            key = "rain" if w in ("regnet", "schüttet") else "snow" if w == "schneit" else "cold" if "kalt" in w else \
                "hot" if ("heiß" in w or "warm" in w) else "sun"
            st.uses["weather_de"] = [key, st.turn]
            return Reply(msg, "smalltalk", pk(f"weather:{key}", g["weather"][key]), via="german")
        if recent("weather_de", 2) and st.uses["weather_de"][0] in ("rain", "cold", "snow") and \
                re.fullmatch(r"(?:und )?ich wollte (?:eigentlich )?(?:joggen|laufen|spazieren|rad fahren|fahrrad fahren|wandern|raus|draußen trainieren|fußball spielen)"
                             r"(?: gehen)?", q):
            st.uses["plan_moved_de"] = [st.turn]
            return Reply(msg, "smalltalk", pk("weather_plans", g["weather_plans"]), via="german")
        if recent("plan_moved_de", 2) and re.fullmatch(r"(?:ok |ja )?(?:vielleicht |dann |wohl )?morgen(?: dann)?", q):
            return Reply(msg, "smalltalk", pk("maybe_tomorrow", g["maybe_tomorrow"]), via="german")
        mv = re.fullmatch(r"mein(?:e)? (?:beste )?(?:freundin|freund|bester freund|schwester|bruder|nachbarin|nachbar|cousine|cousin|mitbewohnerin|mitbewohner) "
                          r"zieht (?:weg|um|nach (?P<p>[a-zäöüß ]{3,30}))(?: (?:nächsten|nächste|diesen|im) \w+)?", q)
        if mv:
            st.uses["moving_de"] = [st.turn]
            if mv.group("p"):
                return Reply(msg, "smalltalk", pk("moving_where", g["moving_where"], x=_de_place_case(mv.group("p"))), via="german")
            return Reply(msg, "smalltalk", pk("moving", g["moving"]), via="german")
        if recent("moving_de", 4):
            wp = re.fullmatch(r"(?:nach|in die|in den) (?P<p>[a-zäöüß ]{3,30})", q)
            if wp:
                st.uses["moving_de"] = [st.turn]
                return Reply(msg, "smalltalk", pk("moving_where", g["moving_where"], x=_de_place_case(wp.group("p"))), via="german")
            if re.fullmatch(r"(?:schon |im )?(?:nächsten|nächste|kommenden|diesen) (?:monat|woche|sommer|winter|frühling|herbst|jahr)|bald|in (?:zwei|drei|ein paar) (?:wochen|monaten|tagen)|morgen", q):
                st.uses["moving_de"] = [st.turn]
                return Reply(msg, "smalltalk", pk("moving_when", g["moving_when"]), via="german")
            if re.search(r"\bvermissen\b|\bwerde (?:sie|ihn) vermissen\b|\bso traurig\b", q):
                return Reply(msg, "smalltalk", pk("moving_miss", g["moving_miss"]), via="german")
        return None

    def _german_ctx(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """German everyday context across turns: a move and its reason, where to live, what to see and eat
        there, a sick pet, "und 20 Prozent?", days until a holiday, "nein, eigentlich Lasagne", the World
        Cup by year, work stress and loneliness when working from home."""
        dc = self.bank.de["daily"].get("ctx")
        if not dc:
            return None
        s = s.strip(" .!")
        q = s.rstrip("?").strip()
        if _DE_BOT_HUMAN.match(s):
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:bot_human", dc["bot_human"]), via="german")
        for rx, key in ((_DE_MISUNDERSTOOD, "misunderstood"), (_DE_SORRY, "sorry_ok"), (_DE_HELP, "help_ask")):
            if rx.match(q):
                return Reply(msg, "smalltalk", self._pick(st, f"de:ctx:{key}", dc[key]), via="german")
        if re.fullmatch(r"(?:hm+,? |naja,? |ach,? )?(?:geht so|so lala|so la la|mittel|naja|nicht so toll|nicht so gut|könnte besser sein|"
                        r"durchwachsen|es geht|muss ja)", q):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:ctx:so_so", dc["so_so"]), via="german")
        le0 = st.last_exp or {}
        sleepy = le0 and st.turn - le0.get("turn", -99) <= 3 and re.search(r"schlaf|geschlafen|nacht|müde", le0.get("text") or "")
        if sleepy and re.fullmatch(r"(?:einfach |eher |wohl )?(?:zu viel|so viel|viel) (?:im kopf|gedanken|nachgedacht|gegrübelt)|"
                                   r"(?:ich )?(?:konnte|kann) nicht abschalten|gedankenkarussell|(?:mein )?kopf (?:war|ist) zu voll", q):
            st.last_exp = dict(le0, turn=st.turn)
            return Reply(msg, "empathy", self._pick(st, "de:ctx:racing", dc["racing"]), via="german")
        if re.fullmatch(r"(?:ich )?(?:hab|habe) (?:heute|morgen|endlich|diese woche) (?:frei|urlaub|keinen termin)|heute ist mein freier tag",
                        re.sub(r"\s+", " ", re.sub(r"[^\w\s',-]", " ", q)).strip()):
            st.uses["day_off_de"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:day_off", dc["day_off"]), via="german")
        do = st.uses.get("day_off_de")
        if do is not None and st.turn - do <= 3:
            if re.fullmatch(r"(?:keine ahnung|weiß nicht|weiss nicht|ich weiß nicht)(?:,? was ich (?:machen|tun) soll)?|hast du (?:eine )?idee\w*|"
                            r"was (?:könnte|kann|soll) ich (?:machen|tun)", q):
                st.uses["day_off_de"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:day_off_ideas", dc["day_off_ideas"]), via="german")
            if re.fullmatch(r"(?:das |und das )?wetter ist (?:so |richtig |echt |total )?(?:schön|gut|toll|super|herrlich|sonnig)", q):
                st.uses["day_off_de"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:nice_weather", dc["nice_weather"]), via="german")
        vals = [v for v in st.uses.get("kb_vals", []) if st.turn - v[0] <= 4]
        wb = re.fullmatch(r"(?:und )?(?:welche|welcher|welches|wer|was) (?:davon |von beiden )?(?:ist|hat) (?P<w>größer|kleiner|mehr einwohner|älter|höher|länger)", q)
        if wb and len(vals) >= 2 and vals[-1][1] != vals[-2][1]:
            w = {"größer": "bigger", "kleiner": "smaller", "mehr einwohner": "bigger", "älter": "older", "höher": "taller",
                 "länger": "longer"}[wb.group("w")]
            a_, b_ = vals[-2][1], vals[-1][1]
            rep = self.everyday.compare(st, f"which is {w}, {a_} or {b_}", f"which is {w}, {a_} or {b_}".lower())
            if rep is not None and rep.kind == "answer":
                rep.text = _de_compare(rep.text, s)
                rep.message = msg
                return rep
        m = _DE_MOVING.match(q)
        if m and m.group("x") not in ("hause", "bett", "ruhe", "der stadt", "die stadt"):
            city = _de_place_case(m.group("x"))
            st.uses["moved"] = [city, st.turn]
            st.uses["place_topic"] = [city, st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:moving", dc["moving"], x=city), via="german")
        mv = st.uses.get("moved")
        m = _DE_REASON.match(q)
        if m and mv and st.turn - mv[1] <= 2:
            r = m.group("r") or m.group("s")
            key = "moved_work" if r.startswith(("arbeit", "job", "neuen")) else "moved_study" if r.startswith(("stud", "uni")) \
                else "moved_other"
            return Reply(msg, "smalltalk", self._pick(st, f"de:ctx:{key}", dc[key], x=mv[0]), via="german")
        pt = st.uses.get("place_topic")
        here = (pt[0] if isinstance(pt, list) and st.turn - pt[1] <= 8 else None) or (mv[0] if mv else None)
        for rx, table, lead in ((_DE_AREAS, "areas", "areas_lead"), (_DE_SIGHTS, "sights", "sights_lead"), (_DE_FOOD, "food", "food_lead")):
            m = rx.match(q)
            if not m or (table == "food" and not re.search(r"\b(?:man|dort|da|in|typisch\w*)\b", q)):
                continue                                  # "was soll ich essen?" is about dinner, not the city
            city = m.group("p") or m.group("q")
            city = _de_place_case(city) if city else here
            if not city:
                continue
            st.uses["place_topic"] = [city, st.turn]
            val = dc[table].get(city.lower())
            if val:
                return Reply(msg, "smalltalk", self._pick(st, f"de:ctx:{lead}", dc[lead], x=city, y=val), via="german")
            key = "areas_none" if table == "areas" else "place_none"
            return Reply(msg, "unknown", self._pick(st, f"de:ctx:{key}", dc[key], x=city), via="german")
        m = _DE_PET_SICK.match(q)
        if m:
            animal = m.group("a") or m.group("b") or m.group("c")
            st.uses["pet_de"] = {"animal": animal, "name": None, "turn": st.turn}
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:ctx:pet_sick", dc["pet_sick"]), via="german")
        pd = st.uses.get("pet_de")
        if pd and st.turn - pd["turn"] <= 6:
            m = _DE_SINCE.match(q)
            if m:
                pd["turn"] = st.turn
                return Reply(msg, "empathy", self._pick(st, "de:ctx:pet_since", dc["pet_since"], x=m.group("x")), via="german")
            m = _DE_PET_NAME.match(q)
            if m:
                name = (m.group("x") or m.group("y")).capitalize()
                pd.update(name=name, turn=st.turn)
                eng = {"hund": "dog", "katze": "cat", "kater": "cat", "hase": "rabbit", "kaninchen": "rabbit", "hamster": "hamster",
                       "vogel": "bird", "pferd": "horse"}.get(pd["animal"], "pet")
                self._learn(st, [f"My {eng} is called {name}."], msg)
                return Reply(msg, "learned", self._pick(st, "de:ctx:pet_name", dc["pet_name"], x=name), via="german")
            if _DE_VET.match(s):
                pd["turn"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:vet", dc["vet"]), via="german")
            if _DE_CALL.match(q):
                who = pd["name"] or ("deiner " + pd["animal"].capitalize() if pd["animal"] == "katze" else "deinem " + pd["animal"].capitalize())
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:pet_call", dc["pet_call"], x=who), via="german")
        m = _DE_PCT.match(q)
        lm = re.search(r"\bvon (\d+(?:[.,]\d+)?)\b", normalise_de_text(st.last_message or ""))
        if m and lm and st.uses.get("last_via") == "tool":
            a = float(m.group("a").replace(",", "."))
            b = float(lm.group(1).replace(",", "."))
            c = a * b / 100
            fmt = lambda v: (f"{v:.2f}".rstrip("0").rstrip(".")).replace(".", ",")
            return Reply(msg, "tool", self._pick(st, "de:ctx:pct", dc["pct"], a=fmt(a), b=fmt(b), c=fmt(c)), via="tool",
                         confidence=1.0)
        m = _DE_DAYS.match(q)
        hw = re.fullmatch(r"(?:und )?wann (?:ist|feiert man|feiern wir|ist dieses jahr) (?P<x>weihnachten|heiligabend|silvester|neujahr|halloween|valentinstag|nikolaus)", q)
        hl = st.uses.get("holiday_de")
        word = (m.group("x") or m.group("y")) if m else None
        if m is None and hw is None and hl and st.turn - hl[1] <= 3 and re.fullmatch(r"(?:und )?(?:wie viele|wieviele) tage (?:sind es )?(?:noch|bis dahin)|wie lange (?:noch|dauert es noch)", q):
            word = hl[0]                                  # "wie viele tage noch?" right after "wann ist weihnachten?"
        if hw is not None:
            word = hw.group("x")
            st.uses["holiday_de"] = [word, st.turn]
            mo, da = _DE_HOLIDAYS[word]
            import datetime as _dt
            now = self._now() or _dt.datetime.now()
            today = now.date() if hasattr(now, "date") else now
            target = _dt.date(today.year, mo, da)
            if target < today:
                target = _dt.date(today.year + 1, mo, da)
            days = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
            months = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")
            extra = " – der erste Weihnachtstag ist der 25." if word == "weihnachten" else ""
            when = "Heiligabend" if word == "weihnachten" else word.capitalize()
            return Reply(msg, "tool", f"{when} ist am {days[target.weekday()]}, {target.day}. {months[target.month - 1]} {target.year}{extra} "
                                      f"– noch {(target - today).days} Tage.", via="tool", confidence=1.0)
        if word:
            now = self._now() or __import__("datetime").datetime.now()
            today = now.date() if hasattr(now, "date") else now
            mo, da = _DE_HOLIDAYS[word]
            import datetime as _dt
            target = _dt.date(today.year, mo, da)
            if target < today:
                target = _dt.date(today.year + 1, mo, da)
            n = (target - today).days
            months = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
                      "Dezember")
            days = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
            shown = f"{days[target.weekday()]}, {target.day}. {months[target.month - 1]} {target.year}"
            return Reply(msg, "tool", self._pick(st, "de:ctx:days_until", dc["days_until"], x=word.capitalize(), n=n, d=shown),
                         via="tool", confidence=1.0)
        m = _DE_FIX.match(q)
        sid = self.bot.context.get("last_learned")
        if m and sid:
            x = (m.group("x") or m.group("y")).strip()
            for f in self.bot.facts.facts:
                if f.source == sid and f.subject == USER and not re.fullmatch(r"(?:ok|okay|gut|schon gut|egal|passt|alles gut|nichts)", x):
                    noun = next((n for lab, n in _FAV_NOUN.items() if lab in f.relation), None)
                    if noun:
                        self._learn(st, [f"My favourite {noun} is {x}."], msg)
                        shown = x[:1].upper() + x[1:]
                        return Reply(msg, "learned", self._pick(st, "de:ctx:fav_fixed", dc["fav_fixed"], x=shown), via="german")
        r = self._german_event(st, msg, q, dc)
        if r is not None:
            return r
        m = _DE_IM.match(q)
        if m and m.group("x") not in _DE_NOT_NAME and not re.search(r"(?:ig|lich|isch|bar|los|sam|haft|end|iert|er|t)$", m.group("x")) \
                and self.user_name() is None:
            x = m.group("x").capitalize()
            ls = self.bot.typer.lower_share(m.group("x")) if self.bot.typer is not None else None
            asked = re.search(r"\b(?:wie heißt du|dein name|what'?s your name|what should i call you)\b", (st.last_reply or "").lower())
            if (ls is not None and ls < 0.5) or (ls is None and (asked or m.group("x") in _COMMON_FIRST_NAMES)):
                # "ich bin tom": a name, never "Trauzeugin"
                self._learn(st, [f"My name is {x}."], msg)
                return Reply(msg, "learned", self._pick(st, "de:ctx:name_hi", dc["name_hi"], x=x), via="german")
        if _DE_LONG_WEEK.match(q):
            st.uses["long_week_de"] = st.turn
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "text_en": "long week tired", "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:ctx:long_week", dc["long_week"]), via="german")
        lwd = st.uses.get("long_week_de")
        if lwd is not None and st.turn - lwd <= 3 and _DE_DEADLINES.match(q):
            st.uses["long_week_de"] = st.turn
            return Reply(msg, "empathy", self._pick(st, "de:ctx:deadlines", dc["deadlines"]), via="german")
        for rx, key in ((_DE_ALMOST_WE, "almost_weekend"), (_DE_BOT_WE, "bot_weekend"), (_DE_COMPLIMENT, "compliment")):
            if rx.match(q):
                return Reply(msg, "smalltalk", self._pick(st, f"de:ctx:{key}", dc[key]), via="german")
        if _DE_HIKE.match(q):
            st.uses["hike_de"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:hike_plan", dc["hike_plan"]), via="german")
        hd = st.uses.get("hike_de")
        if hd is not None and st.turn - hd <= 4:
            for rx, key in ((_DE_TIPS, "hike_tips"), (_DE_BRING, "hike_bring"), (_DE_WATER, "hike_water")):
                if rx.match(q):
                    st.uses["hike_de"] = st.turn
                    return Reply(msg, "smalltalk", self._pick(st, f"de:ctx:{key}", dc[key]), via="german")
        if _DE_COST.match(q):
            cands = []
            tp = st.topic or {}
            if tp.get("turn", -99) >= st.turn - 3:
                cands.append(tp.get("name", ""))
            ptd = st.uses.get("place_topic")
            if isinstance(ptd, list) and st.turn - ptd[1] <= 8:
                cands.append(ptd[0])
            levels = self.bank.daily["cost_level"]
            for c in cands:
                cl = c.lower()
                cl = {"münchen": "munich", "wien": "vienna", "rom": "rome", "zürich": "zurich", "lissabon": "lisbon",
                      "prag": "prague", "kopenhagen": "copenhagen", "athen": "athens"}.get(cl, cl)
                level = next((lv for lv, cities in levels.items() if cl in cities), None)
                if level:
                    return Reply(msg, "smalltalk", _fill(dc["cost"][level], x=c), via="german")
        if _DE_RECAP.match(q):
            recap = st.uses.get("recap", [])
            if not recap:
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:recap_none", dc["recap_none"]), via="german")
            items = [_RECAP_DE.get(r, _de_country(r)) for r in recap[-5:]]
            shown = ", ".join(items[:-1]) + " und " + items[-1] if len(items) > 1 else items[0]
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:recap", dc["recap"], x=shown), via="german")
        if re.search(r"\bverlobt\b|\bheiraten\b", q):
            st.uses["engaged_de"] = st.turn
        ed = st.uses.get("engaged_de")
        if ed is not None and st.turn - ed <= 5 and ed != st.turn:
            if _DE_WEDDING_WHEN.match(q):
                st.uses["engaged_de"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:wedding_when", dc["wedding_when"]), via="german")
            if _DE_TRAUZEUGE.match(q):
                st.uses["engaged_de"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:trauzeugin", dc["trauzeugin"]), via="german")
        if re.search(r"\b(?:prüfung|führerschein\w*|examen) bestanden\b", q):
            st.uses["passed_de"] = st.turn
        pd_ = st.uses.get("passed_de")
        if pd_ is not None and st.turn - pd_ <= 3 and pd_ != st.turn and _DE_FIRST_TRY.match(q):
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:first_try", dc["first_try"]), via="german")
        if _DE_FIGHT.search(q):
            st.uses["fight_de"] = st.turn
        fd = st.uses.get("fight_de")
        if fd is not None and st.turn - fd <= 5 and fd != st.turn:
            if _DE_APOLOGIZE.match(q):
                st.uses["fight_de"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:apologize", dc["apologize"]), via="german")
            if _DE_CALL_FRIEND.match(q):
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:call_friend", dc["call_friend"]), via="german")
        m = _DE_SEEN.match(q)
        if m and not re.fullmatch(r"(?:zeit|lust|hunger|angst|recht|ahnung|lust drauf|kinder|haustiere|geschwister)", m.group("x")):
            hit = self._work_entity(m.group("x"), None)
            if hit:
                title, kind = hit
                name = re.sub(r"\s*\([^)]*\)$", "", title)
                st.topic = {"title": title, "name": name, "turn": st.turn}
                st.uses["work"] = [title, name, kind, st.turn]
                self.bot.context.update({"answer": None, "atype": None, "mention": name, "kb_last": None})
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:work_seen", dc["work_seen"], x=name), via="german")
        wk = st.uses.get("work")
        if wk and st.turn - wk[3] <= 6:
            title, name, kind = wk[0], wk[1], wk[2]
            if re.fullmatch(r"(?:und )?(?:worum geht(?:'s| es)(?: da| darin| in dem film| in dem buch)?|was passiert (?:da|darin))", q):
                f = self.about.find(title)
                if f is not None:
                    wk[3] = st.turn
                    rep = self._about_reply(st, msg, f, "tell")
                    rep.text = f"{self.bank.de['daily']['english_text']} {rep.text}"
                    return rep
            if re.fullmatch(r"(?:und )?wer hat (?:den film|das buch|ihn|es|den|das) (?:gemacht|gedreht|geschrieben|inszeniert)", q):
                verb = "wrote" if kind == "book" else "directed"
                rep = self._kb_answer(st, f"who {verb} {name}?")
                if rep is None or not rep.answer:          # not in the fact bank: the article's own "directed by …"
                    mk = self._work_maker(title)
                    rep = Reply(msg, "answer", "", answer=mk[0], source=mk[1], via="about", confidence=0.8) if mk else None
                if rep is not None and rep.answer:
                    wk[3] = st.turn
                    de_text = (f"{name} ist von {rep.answer}." if kind != "book" else f"{name} wurde von {rep.answer} geschrieben.")
                    return Reply(msg, "answer", de_text, answer=rep.answer, evidence=rep.evidence, source=rep.source, via="german",
                                 confidence=rep.confidence)
            if re.fullmatch(r"(?:und )?(?:kennst du |hast du |gibt es )?(?:ähnliche|noch mehr solche|vergleichbare) (?:filme|bücher|serien|musik|"
                            r"künstler)(?: wie den| wie das)?", q):
                rec = "book" if kind == "book" else "music" if kind == "music" else "movie"
                rep = self.everyday.recommend(st, msg, rec, _LIKE_GENRE.get(name.lower()), lang="de")
                rep.text = "\n".join(ln for ln in rep.text.split("\n") if name.lower() not in ln.lower() or not ln.startswith("•"))
                return rep
        m = _DE_CONVERT.match(q)
        if m:
            from engramm.chat.tools import convert
            n = m.group("n").replace(",", ".")
            res = convert(f"convert {n} {_DE_UNIT[m.group('fr')]} to {_DE_UNIT[m.group('to')]}")
            if res is not None and res.text:
                text = res.text
                for en, de_ in (("miles", "Meilen"), ("pounds", "Pfund"), ("liters", "Liter"), ("gallons", "Gallonen"), ("inches", "Zoll"),
                                ("feet", "Fuß"), ("meters", "Meter")):
                    text = re.sub(rf"\b{en}\b", de_, text)
                text = re.sub(r"(\d)\.(\d)", r"\1,\2", text)              # German decimal comma
                return Reply(msg, "tool", text if text.endswith(".") else text + ".", via="tool", confidence=1.0)
        m = _DE_DEFINE.match(q)
        if m and re.fullmatch(r"[a-z-]+", m.group("w")):
            w = m.group("w")
            de_def = dc["word_defs_de"].get(w)
            if de_def:
                ex = self.bank.daily["word_defs"].get(w, ["", ""])[1]
                return Reply(msg, "answer", self._pick(st, "de:ctx:define", dc["define"], x=w, y=de_def, z=ex), via="german",
                             confidence=1.0)
            return Reply(msg, "unknown", self._pick(st, "de:ctx:define_none", dc["define_none"], x=w), via="german")
        m = _DE_KCAL.match(q)
        if m:
            en = _DE_FOOD_EN.get(m.group("f").strip())
            hit = self.bank.daily["food_kcal"].get(en) if en else None
            if hit:
                return Reply(msg, "answer", self._pick(st, "de:ctx:kcal", dc["kcal"], x=hit[0], y=_DE_FOOD_SHOWN.get(en, m.group("f"))),
                             via="german", confidence=1.0)
        if _DE_RUN.match(q):
            st.uses["run_de"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:run_start", dc["run_start"]), via="german")
        rd = st.uses.get("run_de")
        if rd is not None and st.turn - rd <= 5:
            if _DE_RUN_OFTEN.match(q):
                st.uses["run_de"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:run_often", dc["run_often"]), via="german")
            if _DE_RUN_GO.match(q):
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:run_go", dc["run_go"]), via="german")
        if _DE_GUESTS.match(q):
            st.uses["guests_de"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:guests", dc["guests"]), via="german")
        gd_ = st.uses.get("guests_de")
        if gd_ is not None and st.turn - gd_ <= 6:
            if _DE_VEGGIE.match(q):
                st.uses["guests_de"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:guests_veggie", dc["guests_veggie"]), via="german")
            if _DE_DESSERT.match(q):
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:dessert", dc["dessert"]), via="german")
        if _DE_ACHE.match(q):
            st.uses["ache_de"] = st.turn
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:ctx:ache", dc["ache"]), via="german")
        ad = st.uses.get("ache_de")
        if ad is not None and st.turn - ad <= 4:
            m = _DE_ACHE_SINCE.match(q)
            if m:
                st.uses["ache_de"] = st.turn
                return Reply(msg, "empathy", self._pick(st, "de:ctx:ache_since", dc["ache_since"], x=m.group("x")), via="german")
            if _DE_MEDS.match(q):
                st.uses["ache_de"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:ache_meds", dc["ache_meds"]), via="german")
        m = _DE_BDAY_PERSON.match(q)
        if m:
            st.uses["gift_de"] = {"person": m.group("p"), "likes": [], "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:bday_person", dc["bday_person"]), via="german")
        gd = st.uses.get("gift_de")
        if gd and st.turn - gd["turn"] <= 6:
            m = _DE_LIKES.match(q)
            if m:
                words_ = (m.group("x") + " " + (m.group("y") or "")).split()
                gd["likes"] += [w for w in words_ if w in dc["gift_like"]]
                gd["turn"] = st.turn
                self._learn(st, [f"My {'girlfriend' if gd['person'] in ('freundin', 'beste freundin') else 'friend'} likes "
                                 f"{' and '.join(words_)}."], msg)
                return Reply(msg, "learned", "Gut zu wissen! Das merke ich mir.", via="german")
            if _DE_GIFT_Q.match(q):
                gd["turn"] = st.turn
                if gd["likes"]:
                    k = gd["likes"][0]
                    shown = {"liest": "liest", "lesen": "liest", "kocht": "kocht", "kochen": "kocht", "reist": "reist", "reisen": "reist",
                             "malt": "malt"}.get(k, f"{k} mag")
                    return Reply(msg, "smalltalk", self._pick(st, "de:ctx:gift_lead", dc["gift_lead"], x=shown, y=dc["gift_like"][k]),
                                 via="german")
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:gift_none", dc["gift_none"]), via="german")
        la = st.last_action or {}
        food = (la.get("kind") == "rec:food" and st.turn - la.get("turn", -99) <= 3) or \
            (st.uses.get("food_de") is not None and st.turn - st.uses["food_de"] <= 3)
        ih = re.fullmatch(r"(?:ich )?(?:hab|habe|hätte) (?:nur |noch |bloß |leider nur )?(?P<x>[a-zäöüß][a-zäöüß ,]{2,50}?)"
                          r"(?: da| zu hause| im kühlschrank| übrig)?", q)
        if food and ih:
            items = [i.strip() for i in re.split(r",|\bund\b", ih.group("x")) if i.strip()]
            x = " und ".join(", ".join(w[:1].upper() + w[1:] for w in items).rsplit(", ", 1))   # German nouns: "Eier und Spinat"
            stems = {re.sub(r"(?:n|en|er|e|s)$", "", i.split()[-1]) for i in items} | {i.split()[-1] for i in items}
            st.uses["food_de"] = st.turn
            for row in dc["ingredients"]:
                if all(any(s_.startswith(n) for s_ in stems) for n in row["need"]):
                    return Reply(msg, "smalltalk", self._pick(st, "de:ctx:ingredient_lead", dc["ingredient_lead"], x=x, y=row["idea"]),
                                 via="german")
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:ingredient_none", dc["ingredient_none"], x=x), via="german")
        if food and re.fullmatch(r"(?:und )?wie lange (?:dauert|braucht) (?:das|es|die zubereitung)(?: ungefähr| etwa)?", q):
            mins = re.findall(r"in (\w+) minuten", st.last_reply or "", re.I)
            if mins:
                return Reply(msg, "smalltalk", self._pick(st, "de:ctx:food_time_known", dc["food_time_known"], x=mins[0]), via="german")
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:food_time", dc["food_time"]), via="german")
        if _DE_WORK_STRESS.match(q):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "text_en": "work is too much",
                           "turn": st.turn}
            st.uses["work_de"] = st.turn
            return Reply(msg, "empathy", self._pick(st, "de:ctx:work_stress", dc["work_stress"]), via="german")
        if _DE_BOSS.match(q):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "text_en": "my boss puts pressure",
                           "turn": st.turn}
            st.uses["work_de"] = st.turn
            return Reply(msg, "empathy", self._pick(st, "de:ctx:boss_pressure", dc["boss_pressure"]), via="german")
        wd = st.uses.get("work_de")
        if wd is not None and st.turn - wd <= 3 and _DE_IDEAS.match(q):
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:work_tips", dc["work_tips"]), via="german")
        le = st.last_exp or {}
        lonely = le and st.turn - le.get("turn", -99) <= 4 and re.search(r"einsam|allein|niemanden|keine freunde", le.get("text") or "")
        if lonely and _DE_WFH.search(q) and len(q.split()) <= 10:
            st.last_exp = dict(le, turn=st.turn)
            return Reply(msg, "empathy", self._pick(st, "de:ctx:wfh_lonely", dc["wfh_lonely"]), via="german")
        if _DE_MAYBE.match(q):
            if lonely:
                st.last_exp = dict(le, turn=st.turn)
            st.uses["lonely_de"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:maybe_should", dc["maybe_should"]), via="german")
        ld = st.uses.get("lonely_de")
        if (lonely or (ld is not None and st.turn - ld <= 2)) and _DE_IDEAS.match(q):
            st.uses["ideas_de"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:lonely_ideas", dc["lonely_ideas"]), via="german")
        idd = st.uses.get("ideas_de")
        if idd is not None and st.turn - idd <= 2 and re.fullmatch(r"(?:das |klingt |hört sich )?(?:klingt|hört sich)? ?(?:gut|super|toll|schön|"
                                                                     r"nach einem plan|machbar)(?: an)?", q):
            return Reply(msg, "smalltalk", self._pick(st, "de:ctx:ideas_liked", dc["ideas_liked"]), via="german")
        return None

    def _german_event(self, st: DialogState, msg: str, q: str, dc: dict) -> Reply | None:
        """"Wer hat die WM 2014 gewonnen?", "und 2018?", "wo war die?": the English tournament reader,
        answered in German."""
        ev = st.uses.get("event_q")
        recent = ev is not None and st.turn - ev["turn"] <= 4
        m = _DE_EVENT.match(q)
        en = None
        if m:
            e = m.group("e") or m.group("e2") or m.group("e3")
            y = m.group("y") or m.group("y2") or m.group("y3") or (str(ev["year"]) if recent else None)
            kind = _DE_EVENT_KIND.get(e)
            if not kind or not y:
                return None
            name = {"world cup": "world cup", "euro": "euro", "women's world cup": "women's world cup",
                    "summer olympics": "olympics"}[kind]
            en = f"where was the {y} {name} held" if m.group("e3") else f"who won the {y} {name}"
        elif recent and _DE_EVENT_AGAIN.match(q):
            y = _DE_EVENT_AGAIN.match(q).group("y")
            en = f"and {y}"
        elif recent and _DE_EVENT_IT.match(q):
            en = "where was it held" if q.lstrip("und ").startswith("wo") else "who won it"
        if en is None:
            return None
        rep = self._event_q(st, msg, en)
        if rep is None:
            return None
        ev = st.uses.get("event_q")
        title = _DE_EVENT_TITLE[ev["kind"]].format(y=ev["year"])
        plural = ev["kind"].endswith("olympics")
        mw = re.match(r"^(?P<x>.+?) won the ", rep.text)
        mh = re.match(r"^The .+? (?:was|were) held in (?P<x>.+?)\.$", rep.text)
        if rep.kind == "unknown":
            text = self._pick(st, "de:ctx:event_unknown", dc["event_unknown"], x=title.split(" ", 1)[1])
        elif mw:
            team = _de_country(mw.group("x"))
            key = "event_won_pl" if team.endswith(("staaten", "lande")) else "event_won"
            text = self._pick(st, f"de:ctx:{key}", dc[key], x=team, y=title)
        elif mh:
            key = "event_where_pl" if plural else "event_where"
            text = self._pick(st, f"de:ctx:{key}", dc[key], x=_de_country(mh.group("x")), y=title, Y=title[:1].upper() + title[1:])
        else:
            return None
        return Reply(msg, rep.kind, text, evidence=rep.evidence, source=rep.source, via="german", confidence=rep.confidence)

    def _german_life(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """German everyday talk that needs the conversation: thanks after a tip or a congratulation,
        a loss and what follows it, facts about you ("wie alt bin ich?"), two facts in one sentence,
        "noch einer", "kenn ich schon", superlatives and short follow-ups ("wo?")."""
        dl = self.bank.de["daily"]["life"]
        la = st.last_action or {}
        le = st.last_exp or {}
        s = s.strip(" ?!.")
        off = st.uses.get("de_offer")
        if off and st.turn - off[1] <= 1 and (re.fullmatch(r"(?:ja|jo|jap|gerne?|klar|ok(?:ay)?|bitte|ja bitte|ja gerne?)?[, ]*(?:ideen|ein paar ideen|ideen bitte|gib mir ideen)?(?: bitte)?", s) and s
                                              or re.fullmatch(r"(?:ja,? |hm,? |also,? )?(?:hast du (?:eine |ein paar |irgendwelche )?(?:idee|ideen|vorschläge?)|was schlägst du vor|"
                                                              r"was würdest du (?:mir )?(?:vorschlagen|empfehlen)|was empfiehlst du(?: mir)?)", s.strip(" ?!."))):
            st.uses.pop("de_offer", None)                 # "ja, ideen" after "soll ich dir Ideen geben?"
            return self.everyday.recommend(st, msg, "activity", off[0], lang="de")
        so = st.uses.get("de_sleep_offer")
        if so and st.turn - so <= 1 and re.fullmatch(r"(?:ja|jo|jap|gerne?|klar|ok(?:ay)?|bitte|ja bitte|ja gerne?|gern doch|"
                                                       r"ja,? (?:gib|sag) (?:sie )?(?:mir|her)|tipps(?: bitte)?|her damit)", s):
            st.uses.pop("de_sleep_offer", None)          # "ja bitte" after "soll ich dir Schlaftipps geben?"
            return self.everyday.recommend(st, msg, "sleep", lang="de")
        if _NA_DE.fullmatch(s):
            return Reply(msg, "smalltalk", self._pick(st, "de:life:greeting", dl["greeting"]), via="german")
        if re.fullmatch(r"(?:bei mir auch|mir auch|mir geht'?s auch gut|auch gut|auch ganz gut|gut,? danke|passt|läuft|läuft bei mir|alles gut|alles super|geht so)", s):
            return Reply(msg, "smalltalk", self._pick(st, "de:life:me_too", dl["me_too"]), via="german")
        if re.fullmatch(r"(?:ich )?(?:hab|habe|hab so|hab voll|hab echt) (?:so |voll |echt |mega |richtig )?hunger|ich bin (?:so |voll )?hungrig|mega hunger", s):
            rep = self.everyday.recommend(st, msg, "food", "quick", lang="de")
            rep.text = self._pick(st, "de:life:hungry", dl["hungry"]) + rep.text[rep.text.index("\n"):]
            return rep
        fw = re.fullmatch(r"(?:und |dann |hmm,? )?(?:was |etwas |irgendwas |lieber was |eher was |lieber etwas |vielleicht was )?mit "
                          r"(?P<x>[a-zäöüß]+)(?: bitte| vielleicht| drin)?", s)
        if fw and la.get("kind") == "rec:food" and st.turn - la.get("turn", -99) <= 3:
            word = fw.group("x")                         # "was mit nudeln" after cooking ideas
            key = next((k for k in dl["food_with"] if word.startswith(k) or k.startswith(word.rstrip("n"))), None)
            if key:
                st.last_action = {"kind": "rec:food", "turn": st.turn, "genre": None, "lang": "de"}
                body = "\n".join("• " + i[:1].upper() + i[1:] for i in dl["food_with"][key][:3])
                head = self._pick(st, "de:life:food_with_head", dl["food_with_head"], x=word[:1].upper() + word[1:])
                return Reply(msg, "smalltalk", f"{head}\n\n{body}", via="german")
        bdm = re.fullmatch(r"(?:ich (?:hab|habe) (?P<w>morgen|heute|übermorgen) geburtstag|(?P<w2>morgen|heute|übermorgen) (?:ist|hab ich) "
                           r"(?:mein )?geburtstag)(?: und ich werde (?P<n>\d{1,3}))?[!.]*", s)
        if bdm:                                          # "ich hab morgen geburtstag"
            when = bdm.group("w") or bdm.group("w2")
            day = self._today() + dt.timedelta(days={"heute": 0, "morgen": 1, "übermorgen": 2}[when])
            self._learn(st, [f"My birthday is {day.day} {day.strftime('%B')}."], msg)
            st.uses["de_bday"] = st.turn
            key = "birthday_today" if when == "heute" else "birthday_tomorrow"
            return Reply(msg, "smalltalk", self._pick(st, f"de:life:{key}", dl[key]), via="german")
        tn_ = re.fullmatch(r"(?:und )?ich werde (?:morgen |heute |bald |nächste woche )?(\d{1,3})(?: jahre(?: alt)?)?[!.]*", s)
        if tn_:
            st.uses["de_bday"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "de:life:turning", dl["turning"], x=tn_.group(1)), via="german")
        bd_ = st.uses.get("de_bday")
        if bd_ is not None and st.turn - bd_ <= 3 and re.fullmatch(
                r"(?:und )?(?:hast du (?:ein paar |irgendwelche )?ideen|irgendwelche ideen|ideen|wie (?:soll|kann|könnte) ich (?:das )?feiern|"
                r"ich weiß (?:noch )?nicht,? wie ich feiern soll|was könnte ich machen|was soll ich machen)\??", s):
            shown = st.uses.get("de_party_shown")
            st.uses["de_bday"] = st.turn
            if shown is not None and st.turn - shown <= 4:   # the ideas were just given: no word-for-word repeat
                return Reply(msg, "smalltalk", self._pick(st, "de:life:party_again", dl["party_again"]), via="german")
            st.uses["de_party_shown"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "de:life:party_ideas", dl["party_ideas"]), via="german")
        lx = st.last_exp or {}
        wz = re.fullmatch(r"(?:wir waren|wir sind) (?:fast |über |knapp |schon )?(?P<n>\d{1,2}|ein|einem|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn) "
                          r"(?:jahre?|monate?) (?:lang )?zusammen(?: gewesen)?[.!]*", s)
        if wz and lx.get("person") and st.turn - lx.get("turn", -99) <= 3:
            n_ = wz.group("n")                           # "wir waren 2 jahre zusammen" after a break-up
            unit = "Monate" if "monat" in s else "Jahre"
            if n_ in ("ein", "einem"):
                unit = "Monat" if "monat" in s else "Jahr"
            dat = f"einem {unit}" if n_ in ("ein", "einem") else f"{n_} {unit}n"      # dative: "nach 2 Jahren"
            nom = f"Ein {unit}" if n_ in ("ein", "einem") else f"{n_} {unit}"
            return Reply(msg, "empathy", self._pick(st, "de:life:together", dl["together"], x=nom, y=dat), via="german")
        if re.search(r"\b(?:mein|meine) (?:freundin|freund|partner|partnerin|mann|frau|ex) hat (?:mit mir )?schluss gemacht|"
                     r"\bwir haben uns getrennt\b|\b(?:sie|er) hat (?:mich )?(?:verlassen|schluss gemacht)\b|\bich wurde verlassen\b", s):
            st.last_exp = {"valence": "negative", "topic": None, "person": True, "text": msg,
                           "text_en": "my partner broke up with me", "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:life:heartbreak", dl["heartbreak"]), via="german")
        if re.search(r"\b(?:wie lange|wie koche|wie mache|wie macht man|wie kocht man|was hilft (?:gegen|bei)|was kann ich (?:gegen|bei)|"
                     r"tipps (?:gegen|bei|für|zum)|wie werde ich .+ los|wie (?:muss|müssen|soll|sollte) (?:ich )?)\b", s):
            for g in dl["howto"]:                        # "wie lange müssen nudeln kochen?": the German guide
                if any(re.search(rf"\b{re.escape(k)}", s) for k in g["keys"]):
                    st.last_action = {"kind": "howto_de", "turn": st.turn, "title": g["title"]}
                    body = "\n".join("• " + x for x in g["steps"])
                    return Reply(msg, "smalltalk", f"{g['title']}:\n\n{body}", via="german")
        lpk = re.fullmatch(r"(?:und |ok,? )?(?:worum geht(?:'s| es) (?:in|bei)|was ist mit|erzähl (?:mir )?(?:mehr )?(?:über|von)|was weißt du über|"
                           r"und) (?:dem |den |der |das )?(?P<n>ersten|zweiten|dritten|letzten|erste|zweite|dritte|letzte)\??", s)
        if lpk and (getattr(st, "last_list", None) or {}).get("titles") and st.turn - st.last_list.get("turn", -99) <= 4:
            n = {"erst": "first", "zweit": "second", "dritt": "third", "letzt": "last"}[re.sub(r"en?$", "", lpk.group("n"))]
            rep = self.everyday.pick_from_list(st, msg, f"the {n} one")
            if rep is not None:                          # "worum geht es in dem ersten?" after film ideas
                idx = {"first": 0, "second": 1, "third": 2, "last": -1}[n]
                title = re.sub(r"\s*\([^)]*\)$", "", st.last_list["titles"][idx] or "")
                rep.text = self._pick(st, "de:life:list_pick_lead", dl["list_pick_lead"], x=title, y=rep.text)
                rep.via = "german"
                return rep
        if re.fullmatch(r"(?:draußen )?(?:es )?regnet(?: es)?(?: (?:draußen|schon den ganzen tag|den ganzen tag|total|so|mal wieder))*|"
                        r"(?:es ist|ist) (?:so |total |voll )?(?:grau|kalt|ungemütlich|eklig) (?:draußen|heute)?|"
                        r"(?:draußen|heute) (?:regnet|schüttet|stürmt) es(?: total| so| den ganzen tag)?", s):
            st.last_action = {"kind": "rec:activity", "turn": st.turn, "genre": None, "lang": "de"}
            st.uses["de_offer"] = ["home", st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "de:life:rain", dl["rain"]), via="german")
        if re.fullmatch(r"(?:es ist|ist) (?:so |total |richtig )?(?:sonnig|schön|warm|herrlich) (?:draußen|heute)", s):
            return Reply(msg, "smalltalk", self._pick(st, "de:life:sun", dl["sun"]), via="german")
        hm0 = re.fullmatch(r"(?:irgendwas|etwas|was|ideen) (?:für|fürs) (?:drinnen|zuhause|zu hause|daheim)", s)
        if hm0 and not (la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3):
            return self.everyday.recommend(st, msg, "activity", "home", lang="de")
        gm0 = _GENRE_DE.match(s)
        if gm0 and la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3:
            genre0 = _GENRE_DE_MAP.get(re.sub(r"(?:es|e|er|en)$", "", gm0.group("g")))
            if genre0:                                   # "was lustiges" after a film: funny films, not a joke
                return self.everyday.recommend(st, msg, la["kind"][4:], genre0, lang="de")
        if re.fullmatch(r"(?:(?:mir geht(?:'?s| s| es)|es geht|geht) (?:eigentlich |ganz |soweit )?(?:gut|okay|ok),? )?(?:aber |nur )?"
                        r"(?:ich )?bin (?:heute )?(?:nur |so |echt |total |ziemlich |voll |einfach |richtig |etwas |ein bisschen )*"
                        r"(?:müde|kaputt|erschöpft|platt|k\.?o\.?)(?: heute)?", s):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg,
                           "text_en": "i am tired", "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "de:life:tired", dl["tired"]), via="german")
        if re.fullmatch(r"(?:ja,? |naja,? )?(?:ich )?(?:hab|habe) (?:heute nacht |letzte nacht |die nacht )?(?:echt |total |richtig |so |sehr |mega |voll )?"
                        r"(?:schlecht|kaum|nicht|wenig|nicht gut|unruhig|nur (?:\d|drei|vier|fünf) stunden) geschlafen(?: heute nacht| letzte nacht)?|"
                        r"ich kann (?:seit tagen |nachts |gerade )?(?:nicht|kaum|schlecht) (?:ein|durch)?schlafen", s):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg,
                           "text_en": "i can't sleep", "turn": st.turn}
            st.uses["de_sleep_offer"] = st.turn
            return Reply(msg, "empathy", self._pick(st, "de:life:slept_bad", dl["slept_bad"]), via="german")
        bf = re.fullmatch(r"(?:und )?(?:(?:was|welche[rs]?|wer) ist )?(?:dein|deine|deinen) (?:absolute[rs]? )?lieblings(\w+)|"
                          r"(?:und )?hast du (?:eine?n? |auch eine?n? )?lieblings(\w+)|(?:und )?(?:was|welche[rs]?) (\w+) magst du "
                          r"(?:am liebsten|gern)", s)
        if bf:                                           # "was ist dein lieblingsessen?": an answer, not "nichts gefunden"
            word = (bf.group(1) or bf.group(2) or bf.group(3) or "").lower()
            fav = dl["bot_fav"]
            key = next((k for k, forms in fav["keys"].items() if any(word.startswith(f) for f in forms)), "other")
            st.uses["de_bot_fav"] = [key, st.turn]
            return Reply(msg, "smalltalk", self._pick(st, f"de:life:bot_fav:{key}", fav[key]), via="german")
        wde = re.fullmatch(r"(?:und )?(?:wie spät ist es|wie viel uhr ist es|wieviel uhr ist es|welche uhrzeit ist es)(?: gerade| jetzt)? in "
                           r"(?P<p>[a-zäöüß .-]{2,30}?)(?: gerade| jetzt)?|(?:und )?in (?P<p2>[a-zäöüß .-]{2,30}?)\??", s)
        if wde and (wde.group("p") or (la.get("kind") == "worldtime" and st.turn - la.get("turn", -99) <= 2)):
            from engramm.chat.worldtime import time_in
            place = wde.group("p") or wde.group("p2")
            hit = time_in(place)
            st.last_action = {"kind": "worldtime", "turn": st.turn, "lang": "de"}
            if hit is not None:
                days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
                shown, local = hit
                return Reply(msg, "tool", f"In {shown} ist es gerade {local.strftime('%H:%M')} Uhr ({days[local.weekday()]}).",
                             via="tool")
            if wde.group("p"):
                return Reply(msg, "tool", f"Die Zeitzone von {place[:1].upper() + place[1:]} kenne ich leider nicht. "
                                          "Frag mich nach einer großen Stadt in der Nähe, z. B. „Wie spät ist es in Tokio?“",
                             via="tool")
        if la.get("kind") == "joke" and st.turn - la.get("turn", -99) <= 2 and re.fullmatch(
                r"(?:haha+|hihi+|lol|xd|😂|🤣)?[, ]*(?:(?:der|das|die) (?:war|ist) (?:echt |richtig |voll |sehr )?(?:gut|lustig|witzig|super|klasse|toll|"
                r"genial|stark)|sehr (?:gut|lustig|witzig)|witzig|lustig|ich lach mich tot|geil)?[!. ]*", s) and s.strip():
            return Reply(msg, "smalltalk", self._pick(st, "de:life:joke_liked", dl["joke_liked"]), via="german")
        off2 = st.uses.get("de_offer")
        if off2 and st.turn - off2[1] <= 1 and re.fullmatch(r"(?:nein|nee|nö|ne)(?:,? (?:danke|keine ideen|lieber nicht|nicht nötig|eher nicht))?|"
                                                              r"keine ideen(?:,? danke)?|lieber nicht", s):
            st.uses.pop("de_offer", None)                # "nein, keine ideen" after "soll ich dir Ideen geben?"
            return Reply(msg, "smalltalk", self._pick(st, "de:life:offer_no", dl["offer_no"]), via="german")
        tq = re.match(r"^(?:ok(?:ay)?,? |super,? |cool,? )?(?:danke|vielen dank|dank dir|danke dir|danke schön)(?: dir)?[!,.]+ *(?P<r>.{6,})$", s)
        if tq and not re.match(r"(?:tschüss|tschüs|ciao|bis |gute nacht|schönen|mach'?s gut)", tq.group("r")) and \
                (tq.group("r").rstrip().endswith("?") or re.match(r"(?:was|wie|wer|wo|wann|warum|wieso|welche[rsn]?|kannst|hast|"
                                                                   r"bist|erzähl|empfiehl|sag|zeig|gib|schreib|rechne|übersetze)\b",
                                                                   tq.group("r"))):
            return self._german(st, tq.group("r"))         # "danke! was kann ich heute abend noch machen?": the question
        if re.fullmatch(r"(?:juhu,? |yay,? |endlich,? |puh,? )*(?:endlich )?(?:feierabend|wochenende|urlaub|ferien|frei)(?: endlich)?(?: juhu| yay)?[!. ]*", s):
            key = "weekend" if "wochenende" in s else "holiday" if re.search(r"urlaub|ferien", s) else "off_work"
            return Reply(msg, "smalltalk", self._pick(st, f"de:life:{key}", dl[key]), via="german")
        if re.fullmatch(r"(?:ok(?:ay)?,? |ja,? )?(?:gute idee|klingt gut|super idee|mach ich|probier ich(?: aus)?|das probier ich(?: aus)?|"
                        r"das mach ich|klingt super)(?:,? (?:mach ich|danke|probier ich(?: aus)?|das mach ich))?[!. ]*", s):
            return Reply(msg, "smalltalk", self._pick(st, "de:life:enjoy", dl["enjoy"]), via="german")
        tb = re.fullmatch(r"(?:ok(?:ay)?,? )?(?:danke|vielen dank|dank dir|danke dir|danke schön|merci)(?: dir| schön| sehr| für alles)?,? (?:und )?"
                          r"(tschüss|tschüs|ciao|bis morgen|bis später|bis dann|bis bald|gute nacht|schönen abend(?: noch)?|"
                          r"schönen tag(?: noch)?|mach'?s gut)", s)
        if tb:                                           # "danke dir, bis morgen": both, not only the thanks
            bye = tb.group(1)
            return Reply(msg, "smalltalk", self._pick(st, "de:life:thanks_bye", dl["thanks_bye"], x=bye[:1].upper() + bye[1:]),
                         via="german")
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
            pm = re.fullmatch(r"meine([nm]?) (\w+)", x)
            if pm:                                     # "ich vermisse meine Oma": "deine Oma", not "meine oma"
                noun = pm.group(2)
                x = f"deine{pm.group(1)} {noun[:1].upper() + noun[1:]}"
                y = "sie" if noun in _FEMALE_DE else "er" if pm.group(1) == "n" or noun in ("opa", "vater", "papa", "bruder", "hund", "kater", "mann", "freund", "sohn") else "es"
            return Reply(msg, "empathy", self._pick(st, "de:life:miss", dl["miss"], x=x, y=y), via="german")
        if re.fullmatch(r"(?:und )?noch (?:einer|einen|eins|ein witz|einen witz)|nochmal", s) and la.get("kind") == "joke":
            return self._german(st, "erzähl mir einen witz")
        if _SEEN_DE.fullmatch(s) and la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3:
            rep = self.everyday.recommend(st, msg, la["kind"][4:], la.get("genre"), more=True, lang="de")
            body = rep.text.split("\n", 1)[1] if "\n" in rep.text else rep.text
            rep.text = self._pick(st, "de:life:seen", dl["seen"]) + "\n" + body
            return rep
        hm = re.fullmatch(r"(?:etwas|was|irgendwas|lieber was|eher was|ideen) (?:für|fürs) (zuhause|zu hause|drinnen|daheim)", s)
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
        if s in ("wo", "und wo", "wo denn", "und wo genau") and last and st.turn - last[0] <= 2 and "gestorben" in last[1]:
            return self._german_question(st, msg, re.sub(r"^(?:und )?(?:wann|in welchem jahr)", "wo", last[1]))
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
                line = _de_your(sent, self._gender) if sent else sent
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
        st.uses["de_last_en"] = [st.turn, f"what is the {en_adj} {en_noun} in the world?"]   # "nein, ich meinte in Europa"
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
        rt = re.fullmatch(r"(?:und )?(?:was ist |wie ?viel ist |rechne |berechne )?(?:die )?(?:quadrat)?wurzel (?:aus|von) (\d+(?:[.,]\d+)?)", s)
        if rt:                                            # "was ist die wurzel aus 81?"
            v = float(rt.group(1).replace(",", ".")) ** 0.5
            shown = (f"{v:.4f}".rstrip("0").rstrip(".")).replace(".", ",")
            st.uses["last_calc"] = [st.turn, str(v)]
            return Reply(msg, "tool", f"Die Wurzel aus {rt.group(1)} ist {shown}.", answer=shown, via="tool")
        m = re.fullmatch(r"(?:und |(?:und )?(?:was (?:ist|sind|ergibt|ergeben)|wie ?viel (?:ist|sind)|rechne|berechne) )(\d+(?:[.,]\d+)?) ?"
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
            # "und die zugspitze?" after "wie hoch ist der mount everest?": the article goes with the new name
            again = re.sub(rf"\b(?:der |die |das |den |dem )?{re.escape(last[2])}\b", m.group("x").strip(), last[1], count=1)
            return self._german_question(st, msg, again)
        return None

    def _german_question(self, st: DialogState, msg: str, s: str) -> Reply | None:
        from engramm.chat.german_bridge import de_sentence, de_value, to_english
        ment = self.bot.context.get("mention")
        ans_ = self.bot.context.get("answer")
        if isinstance(ans_, str) and ans_ and not re.search(r"\d", ans_) and len(ans_.split()) <= 4 and \
                not (re.search(r"\b(?:er|ihn|ihm)\b", s) and ment and not self._not_a_person(ment) and self._not_a_person(ans_)):
            ment = ans_                                  # "die Hauptstadt … ist Canberra" → "sie" is Canberra ("er" after "Goethe starb in Weimar" stays Goethe)
        s = re.sub(r"^(?:und|also|ok|okay) ", "", s)
        if ment and re.search(r"\b(?:leben|wohnen) (?:da|dort)\b|\b(?:da|dort) (?:leben|wohnen)\b", s):
            s = re.sub(r"\bwie viele (?:leute|menschen) (?:leben|wohnen) (?:da|dort)\b", f"wie viele einwohner hat {ment.lower()}", s)
        pm = re.search(r"\b(?:seine|ihre) (frau|mann|ehefrau|ehemann|partnerin|partner|mutter|vater|kinder|hauptstadt|einwohnerzahl|"
                       r"frau|bevölkerung|größe|fläche|währung|sprache)\b", s)
        if ment and pm:                                   # "wer ist seine frau?" after Macron → "wer ist die frau von macron"
            art = "die" if pm.group(1) in ("frau", "ehefrau", "partnerin", "mutter", "hauptstadt", "einwohnerzahl", "bevölkerung",
                                           "größe", "fläche", "währung", "sprache") else "der" if pm.group(1) in (
                                               "mann", "ehemann", "partner", "vater") else "die"
            s = s.replace(pm.group(0), f"{art} {pm.group(1)} von {ment.lower()}", 1)
        if ment and re.search(r"\b(?:hat|ist|liegt|wurde|war|heißt) (?:sie|er|es|ihn)\b|\b(?:sie|er|es) (?:hat|ist|liegt)\b", s) and \
                not re.search(r"\bgeboren|gestorben\b", s):
            # "und wie viele einwohner hat sie?" after Canberra, "wer hat ihn entworfen?" after the Eiffel Tower
            pw = re.search(r"\b(sie|er|es|ihn)\b", s).group(1)
            want = "male" if pw in ("er", "ihn") else "female" if pw == "sie" else None
            g = self._gender(ment) if want else None
            if g and want and g != want:
                # "und wie alt ist er?" right after Michelle Obama: Barack, not Michelle
                ment = next((p for p in reversed(self.bot.context.get("people") or []) if p != ment and self._gender(p) == want), None)
            if ment:
                s = re.sub(r"\b(?:sie|er|es|ihn)\b", ment.lower(), s, count=1)
        hit = to_english(s)
        bare = re.fullmatch(r"(wann|wo|warum|wieso) ?\??", s.strip())
        last_en = st.uses.get("de_last_en")
        if hit is None and bare and last_en and st.turn - last_en[0] <= 2:
            # "wann?" after "wer hat das Penicillin entdeckt?": the last question with a new question word
            wh = {"wann": "when", "wo": "where", "warum": "why", "wieso": "why"}[bare.group(1)]
            rebuilt = rebuild_question(last_en[1], wh)
            if rebuilt:
                rep = self._question(st, rebuilt)
                st.uses["de_last_en"] = [st.turn, rebuilt]
                if rep.kind == "answer" and rep.answer and wh == "when" and re.fullmatch(r"\d{3,4}", str(rep.answer)):
                    return Reply(msg, "answer", f"Im Jahr {rep.answer}.", answer=rep.answer, evidence=rep.evidence,
                                 source=rep.source, via="german", confidence=rep.confidence)
                if rep.kind == "answer":
                    rep.text = f"{self.bank.de['daily']['english_text']} {rep.text}"
                    rep.message = msg
                    return rep
                return Reply(msg, "unknown", self._pick(st, "de:unknown", self.bank.de["daily"]["unknown"]), via="german")
        if hit is None:
            return None
        english, kind, x_en, x_de = hit
        ment = self.bot.context.get("mention") or ""
        if x_en.lower() in ("he", "she", "him", "her") and ment and getattr(self.bot, "not_a_person", None) is not None and \
                self.bot.not_a_person(ment) and not (self.bot.context.get("atype") == "PERSON" and self.bot.context.get("answer")):
            # "wie groß ist sie?" after the Mona Lisa: German "sie" is the painting ("it"), not a woman
            english = re.sub(rf"\b{x_en}\b", "it", english)
            x_en = "it"
        st.uses["de_last_q"] = [st.turn, s, (x_de or "").lower()]
        st.uses["de_last_en"] = [st.turn, english + "?"]
        names = st.uses.setdefault("de_names", {})
        if x_de and x_de.lower() != x_en.lower() and x_en.lower() not in ("he", "she", "it", "him", "her"):
            art = re.search(rf"\b(der|die|das) {re.escape(x_de.lower())}\b", s)
            names[x_en.lower()] = [x_de, art.group(1) if art else ""]     # "der Eiffelturm", for the follow-ups
        dd = self.bank.de["daily"]
        if kind == "about":
            rep = self._about(st, Unit("about", english, english.lower(), data={"kind": "tell", "topic": x_en}))
            if rep.kind != "about":
                from engramm.chat.german_bridge import term_variants
                for alt in term_variants(x_en):           # "Photosynthese" → "Photosynthesis"
                    if self.about.find(alt) is not None:
                        rep = self._about(st, Unit("about", f"tell me about {alt}", f"tell me about {alt.lower()}", data={"kind": "tell", "topic": alt}))
                        break
            if rep.kind == "about":
                rep.text = f"{dd['english_text']} {rep.text}"
                rep.message = msg
                return rep
            if not s.startswith(("wer ", "und wer ")):
                return Reply(msg, "unknown", self._pick(st, "de:unknown", dd["unknown"]), via="german")   # "was ist demokratie?": no "who is" guess
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
            office = self._officeholder(st, english, normalise(english))
            if office is not None:                        # "wer ist der Präsident von Frankreich?": the office's article
                when = getattr(self, "reading_as_of", None)
                when_de = _de_month_year(when) if when else None
                key = "office_dated" if when_de else "office_undated"
                text = self._pick(st, f"de:ctx:{key}", self.bank.de["daily"]["ctx"][key], x=office.answer, z=when_de or "")
                return Reply(msg, "answer", text, answer=office.answer, evidence=office.evidence, source=office.source,
                             via="german", confidence=office.confidence)
            rep = self._question(st, english + "?")
            if rep.via == "clarify" and pron:
                # the name that answers this comes back to the German question ("bell" → "wo wurde Bell geboren?")
                st.pending = {**(st.pending or {}), "slot": "who_mean", "question": s, "pron": pron.group(0), "turn": st.turn,
                              "lang": "de"}
            if rep.via == "clarify" and st.pending and st.pending.get("many"):
                # "wo wurde er geboren?" after several inventors: ask which one, in German
                return Reply(msg, "unknown", f"Da kommen mehrere infrage – {de_value(_join_values(st.pending['many']))}. Wen meinst du?",
                             via="clarify")
            if rep.via == "clarify" or (pron and rep.kind != "answer" and not rep.resolved):
                return Reply(msg, "unknown", dd["who_mean"].replace("{x}", pron.group(0) if pron else x_en), via="clarify")
        rep.message = msg
        if rep.kind != "answer":
            rep.text = self._pick(st, "de:unknown", dd["unknown"])
            return rep
        if kind == "first_holder" and rep.answer:
            rep.text = f"Das war {rep.answer}."
            return rep
        tm_ = re.fullmatch(r"(\d{4})–(\d{4})", str(rep.answer or ""))
        if kind == "tenure" and tm_:
            a_, b_ = int(tm_.group(1)), int(tm_.group(2))
            rep.text = f"Von {a_} bis {b_} – etwa {b_ - a_} Jahre."
            return rep
        wm = _WHO_MADE_DE.fullmatch(s.strip(" ?.!"))
        if wm and rep.answer and len(str(rep.answer).split()) <= 14:
            from engramm.chat.german_bridge import de_value
            art = (wm.group("art") or "").strip()
            thing = wm.group("x").strip()
            thing = " ".join(w if w in ("von", "der", "die", "das", "und", "des", "of", "the", "de", "da") else w[:1].upper() + w[1:]
                             for w in thing.split())
            head = f"{art[:1].upper() + art[1:]} {thing}" if art else thing[:1].upper() + thing[1:]
            plural = re.match(r"(?:die )?(?:zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|zwölf)\b", (art + " " + thing).lower().strip())
            rep.text = f"{head} {'wurden' if plural else 'wurde'} von {de_value(str(rep.answer))} {wm.group('v')}."
            return rep
        measure = rep.via in ("lookup", "common") and rep.kind == "answer" and kind in ("height", "length", "area", "depth", "fell", "sank", "language") and \
            re.search(r"\d", str(rep.answer or ""))
        if rep.via == "kb" or measure:
            name = re.sub(r"\s*\([^)]*\)$", "", (rep.source or {}).get("key") or x_en) if rep.via == "kb" else (x_de or x_en)
            article = ""
            if x_de and x_de.lower() != x_en.lower() and x_en.lower() == name.lower() and \
                    x_en.lower() not in ("he", "she", "it", "him", "her"):
                name = x_de                     # "Frankreich", as the user wrote it
            known_de = names.get(name.lower())
            if known_de:                        # "Eiffel Tower" in a follow-up: the German name from before
                name, article = known_de[0], known_de[1]
            elif names.get(x_en.lower()):
                article = names[x_en.lower()][1]
            if not article and measure:
                am_ = re.search(rf"\b(der|die|das) {re.escape(name.lower())}\b", s)
                arts = st.uses.setdefault("de_art", {})
                article = am_.group(1) if am_ else arts.get(name.lower(), "")
                if article:
                    arts[name.lower()] = article      # "wie hoch war sie nochmal?": still "die Zugspitze"
                name = name[:1].upper() + name[1:]
            sent = de_sentence(kind, name, rep.answer or "", rep.text)
            if sent:
                if article and sent.startswith(name):
                    sent = article[:1].upper() + article[1:] + " " + sent    # "Der Eiffelturm ist 330 m hoch."
                rep.text = sent
                return rep
        if rep.via == "german":
            return rep                                    # already German (a hand-checked fact with its own German text)
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
            ctx = bot.context
            if ctx.get("atype") == "PERSON" and ctx.get("answer") and ctx.get("mention") and ctx["answer"] != ctx["mention"]:
                ctx["last_person"] = [ctx["answer"], ctx["mention"], st.turn]   # "he" may still mean them two turns on
            elif ctx.get("last_person") and st.turn - ctx["last_person"][2] > 3:
                ctx["last_person"] = None
            seen = [n for n in (ctx.get("answer") if ctx.get("atype") == "PERSON" else None, ctx.get("mention"))
                    if isinstance(n, str) and n and not self._not_a_person(n) and not re.search(r"\d", n)]
            if seen:                                       # "how old is he?" after talking about Michelle and Barack
                ctx["people"] = ([p for p in ctx.get("people") or [] if p not in seen] + seen)[-4:]
            st.ctx = dict(ctx)
            bot.context = dict(FRESH_CTX)
        rep.message = message
        rep.seconds = time.time() - t0
        if rep.text and rep.text == st.last_reply and normalise(message) != normalise(st.last_message or ""):
            if rep.kind == "unknown":
                de_again = (self.bank.de or {}).get("daily", {}).get("unknown_again") if st.lang == "de" else None
                rep.text = self._pick(st, "de:unknown_again" if de_again else "daily:unknown_again",
                                      de_again or self.bank.daily["unknown_again"])
        tail = re.search(r"\s+(I'm good, thanks!|I'm doing well, thanks!)$", rep.text or "")
        if tail and len(rep.text) > len(tail.group(0)) + 10:
            rep.text = tail.group(1) + " " + rep.text[:tail.start()].strip()   # "…an early night? I'm good, thanks!": the answer to "you?" first
        if rep.text and rep.kind in ("answer", "about", "tool") and rep.text in st.recent and \
                (len(rep.text) > 80 or re.search(r"\b(?:again|nochmal|noch mal)\b", message, re.I)) and \
                rep.via not in ("facts", "memory", "facts-bank") and normalise(message) != normalise(st.last_message or ""):
            # the same answer again (the question came up twice): said like a person, not a copy
            g70 = ((self.bank.de or {}).get("daily", {}).get("ctx") or {}).get("g70") or {}
            lead = self._pick(st, "de:again_lead", g70["again_lead"]) if st.lang == "de" and g70.get("again_lead") else \
                self._pick(st, "daily:again_lead", self.bank.daily["again_lead"])
            rep.text = lead + rep.text[:1].lower() + rep.text[1:] if rep.text[:2] not in ("I ", "I'") else lead + rep.text
        if rep.text and rep.text in (st.last_reply, st.uses.get("same_q_text")) and rep.kind in ("answer", "about", "tool") and \
                normalise(message).strip(" ?!.") == normalise(st.last_message or "").strip(" ?!.") and normalise(message).strip(" ?!."):
            # the very same question twice or three times in a row: a person notices
            n_same = st.uses.get("same_q", 1) + 1 if st.uses.get("same_q_text") == rep.text else 2
            st.uses["same_q"], st.uses["same_q_text"] = n_same, rep.text
            de = st.lang == "de"
            if n_same >= 3:
                lead = "Das ist jetzt das dritte Mal 😄 – " if de else "That's the third time you've asked 😄 — "
            else:
                lead = "Immer noch dasselbe: " if de else "Still the same answer: "
            low_first = bool(re.match(r"(?:The|A|An|It|It's|There|This|That|Yes|No|He|She|They|We|You|About|Around|In|On|At|"
                                      r"Der|Die|Das|Ein|Eine|Es|Er|Sie|Ja|Nein|Im|Am|Um)\b", rep.text))   # never a name ("Faust …")
            rep.text = lead + (rep.text[:1].lower() + rep.text[1:] if low_first else rep.text)
        if rep.via == "facts" and rep.text:
            rep.text = _MONTH_LOW.sub(lambda m: m.group(0)[:1].upper() + m.group(0)[1:], rep.text)  # "on june 5" → "June 5"
        if rep.kind != "safety" and re.search(r"\b(?:getting sick|i'?m sick|i am sick|feel(?:ing)? sick|i have (?:a |the )?(?:cold|flu|fever|"
                                              r"sore throat|headache|cough)|my throat hurts|caught a cold|coming down with)\b",
                                              message.lower()):
            st.uses["sick"] = st.turn                         # "should I go to work?" may follow
        plm = re.search(r"\b(?:moved to|moving to|live in|living in|i'?m in|visiting|going to|trip to|flying to|travel(?:l)?ing to|"
                        r"holiday in|vacation in|from) ([a-z][a-z ]{2,25}?)(?=\s+(?:next|this|last|tomorrow|for|with|and|now|soon|recently)\b|"
                        r"[.!?,]|$)", message.lower())
        if not plm and rep.kind != "safety" and re.search(r"\b(?:going on|off on|taking|booked|planning) (?:a |my |our )?"
                                                          r"(?:vacation|holiday|trip|getaway)\b", message.lower()):
            st.uses["trip_ask"] = st.turn                     # "to greece" may follow
        if plm and rep.kind != "safety" and re.search(r"\b(?:vacation|holiday|trip|flying|travel)", message.lower()):
            st.uses["trip"] = [_place_case(plm.group(1).strip()), st.turn]
        if plm and plm.group(1).strip() in self.bank.daily.get("sights", {}) and rep.kind != "safety":
            st.uses["place_topic"] = [_place_case(plm.group(1).strip()), st.turn]   # "what should I see there?" may follow
        petm = re.search(r"\bmy (dog|cat|puppy|kitten|hamster|rabbit|bunny|parrot|bird|horse|guinea pig|turtle|tortoise|budgie)\b",
                         message.lower())
        if petm and rep.kind != "safety":
            pet_now = st.uses.get("pet")
            noun = {"puppy": "dog", "kitten": "cat", "bunny": "rabbit"}.get(petm.group(1), petm.group(1))
            if not pet_now or pet_now[0] != noun:
                st.uses.pop("pet_name", None)
            st.uses["pet"] = [noun, st.turn]                  # "his name is max" / "he's 7" may follow
        pm = re.search(r"\bmy (best friend|sister|brother|mom|mum|mother|dad|father|friend|boyfriend|girlfriend|wife|husband|son|"
                       r"daughter|cousin|aunt|uncle|grandma|grandmother|grandpa|grandfather|boss|colleague|roommate|partner|"
                       r"neighbou?r|niece|nephew|fiancée?)\b(?!'s (?!birthday|wedding|party|anniversary|graduation))", message.lower())
        if pm and rep.kind != "safety":
            st.uses["person_noun"] = [pm.group(1), st.turn]   # "her name is lena" / "she loves art" may follow
        trm = re.search(r"\b(?:say|translate|what(?:'s| is))\b.*\b(?:in|to|into) (spanish|french|german|italian|portuguese)\b",
                        message.lower())
        if rep.via == "tool" and trm:
            st.uses["tr_lang"] = [trm.group(1), st.turn]      # "and good morning?" may follow
        nm_ = normalise(message)
        mvm = re.search(r"\b(?:just |recently |finally )?(?:moved|relocated) (?:to|here to) (?P<p>[a-z][a-z ]{1,25}?)(?: (?:for|because|last|this|a)\b|[.!,]|$)", nm_)
        if mvm and rep.kind != "safety":
            st.uses["moved"] = [mvm.group("p").strip().title(), st.turn]
        if rep.kind != "safety" and _PROMOTED.search(nm_):
            st.uses["promo"] = st.turn                   # "senior analyst" may follow
        if rep.kind != "safety" and message_type(message) != "question":
            fixed_ = self._fix_typos(nm_) if self.speller is not None else nm_
            pt = next((k for k, rx in _PREP_TOPICS if re.search(rx, fixed_)), None)
            if pt:
                st.uses["prep"] = [pt, st.turn]          # "how should I prepare?" may follow
        if rep.kind != "safety" and _NEW_JOB.search(normalise(message)):
            st.uses["new_job"] = st.turn                 # "it's at a bank" / "I start monday" may follow
        rep.text = re.sub(r"(I'll remember [^.!]*)[.!] I'll remember that ", r"\1 — and that ", rep.text)
        if rep.kind == "learned":                         # "Noted: march 3." → "Noted: March 3."
            rep.text = re.sub(r"\b(january|february|march|april|june|july|august|september|october|november|december)(?= \d)",
                              lambda m_: m_.group(1).capitalize(), rep.text)
        st.last_message = message
        st.last_kind = rep.kind
        st.uses["last_via"], st.uses["last_via_turn"] = rep.via, st.turn
        self._track(st, rep, msg)
        if rep.via != "gibberish":
            st.gib = 0
        else:
            st.uses["gib_turn"] = st.turn                 # "sorry, my cat walked on the keyboard" may follow
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
        if st.lang != "de" and (st.last_action or {}).get("kind") == "howto":
            hf = self._howto_follow(st, msg)
            if hf is not None:
                return hf
        if st.lang != "de" and "new_job" in st.uses:
            job = self._job_detail(st, msg)
            if job is not None:
                return job
        if re.fullmatch(r"\?{2,}!*|\?!+|!\?+", msg):                    # "???": that was unclear
            return Reply(msg, "smalltalk", self._pick(st, "daily:puzzled", self.bank.daily["puzzled"]), via="clarify")
        de = self.bank.de
        if de and (is_german(msg, de) or _NA_DE.fullmatch(normalise(msg).strip(" ?!."))) and \
                self.bank.safety_rule(normalise(msg, fillers=False)) is None:
            return self._german(st, msg)
        if de and st.lang == "de":
            from engramm.chat.german import neutral_de, normalise_de
            if neutral_de(normalise_de(msg)) is not None or re.fullmatch(r"(?:noch )?mehr|nochmal", normalise_de(msg)) \
                    or re.fullmatch(r"(?:grazie|merci|gracias|obrigad[oa]|arigato)(?: mille| beaucoup)?[!. ]*", normalise_de(msg)) \
                    or (any(st.uses.get(k) and st.turn - st.uses[k][1] <= 2 for k in ("koch70",)) and
                        re.fullmatch(r"[a-zäöüß]+(?: [a-zäöüß]+){0,2}[!. ]*", normalise_de(msg))) \
                    or re.fullmatch(r"(?:hey|hi|hallo|hello|moin|servus|yo|huhu)+(?: (?:hey|hi|du|engramm))?", normalise_de(msg)) \
                    or gibberish(msg, self.speller.known if self.speller is not None else None) \
                    or (_GENRE_DE.match(normalise_de(msg)) and re.sub(r"(?:es|e|er|en)$", "", _GENRE_DE.match(
                        normalise_de(msg)).group("g")) in _GENRE_DE_MAP and not re.search(r"\b(?:something|anything|quick)\b", msg.lower())):
                return self._german(st, msg)      # "haha", "ok", "ja" in a German conversation stay German
            if _clearly_english(msg, de):
                st.lang = "en"
            elif len(re.findall(r"[a-zäöüß]+", msg.lower())) >= 2 or re.fullmatch(r"\s*(?:\d{1,3}|[a-zäöüß]{3,20})[!.? ]*", msg.lower()):
                return self._german(st, msg)      # "die nachbarn waren laut", "28", "italienisch": no English word, stays German
        msg = expand_chat(msg)                            # "wats ur name" → "what's your name"
        lead = re.match(r"^(?:ok(?:ay)?,?\s+)?(?:whatever|anyways?|moving on|never ?mind|nvm|enough of that|forget (?:it|that)(?=[,.!])|"
                        r"ok(?:ay)? then|alright then|fine then)[,.!]*\s+(?=\S+\s+\S)", msg, re.I)
        if lead:
            msg = msg[lead.end():]                        # "ok whatever, tell me a joke": the request
        if self.speller is not None and "?" not in msg:
            msg = self._fix_typos(msg)                    # "a job interveiw tomorow": the words meant, before learning
        react = re.match(r"^(?P<r>(?:(?:cool|nice|wow|great|interesting|ok|okay|oh|ah|haha|lol|thanks|thank you|neat|awesome)[,!.]+\s+)*)"
                         r"(?:(?:ok(?:ay)?|so|and)[,]?\s+)?(?P<q>(?:(?:a )?(?:random|quick|another|different|silly|weird) question[:,!.]?\s+)?)"
                         r"(?=(?:who|what|whats|what's|when|where|why|how|which|is|are|was|were|do|does|did|can|could|tell)\b)", msg, re.I)
        if react and (react.group("r") or react.group("q")):
            msg = msg[react.end():]                       # "cool, how big is mars?", "ok, random question: what's …": the question
        if st.lang != "de":
            dc = self._daily_ctx(st, msg)                 # everyday context: a promotion, a week, a dish, a tournament
            if dc is not None:
                return dc
        msg = self._prefer_correction(msg)                # "actually i prefer ramen" right after a favourite
        li = re.fullmatch(r"(?i)((?:hi|hey|hello|yo|hiya)?[,!.]* ?(?:i'?m|im|i am|my name'?s|name'?s|this is) )([a-z][a-z'-]{1,20})"
                          r"((?: here| btw| by the way)?[.!]*)", msg.strip())
        if li and li.group(2).islower() and li.group(2) not in _NOT_NAMES and \
                (getattr(self.bot, "cap", None) or {}).get(li.group(2), 0.0) >= 0.8:
            msg = li.group(1) + li.group(2).capitalize() + li.group(3)   # "i'm tom": a name, written like one
        nc = _NAME_FIX.match(msg.strip())
        if nc and st.last_kind == "learned" and re.match(r"^(?:hi,? |hey,? |hello,? )?(?:my name is|call me|i'm|im|i am|name'?s) "
                                                         r"[a-z][\w'-]*[.!]?$", (st.last_message or "").strip(), re.I) and \
                nc.group("x").lower() not in _NOT_NAMES:
            name = nc.group("x")
            msg = f"My name is {name[:1].upper() + name[1:]}."      # "no wait, it's alexander" right after the name
        msg = _split_self_statements(msg)                 # "my name is Sam and I'm a teacher": two facts
        two = msg.split(". ", 1)
        nm1 = re.fullmatch(r"(?i)(?:(?:hey|hi|hello|yo|hiya)[,!.]*\s+)?(?:i'?m|im|i am)\s+([a-z][a-z'-]+)", two[0])
        if nm1 and len(two) == 2 and nm1.group(1).lower() not in _NOT_NAMES and not _NOT_A_NAME.search(nm1.group(1)) \
                and self.bank.feeling(nm1.group(1).lower()) is None:
            ls = self.bot.typer.lower_share(nm1.group(1)) if self.bot.typer is not None else None
            if ls is None or ls < 0.5:                    # "hey im lisa and i'm a nurse": a name, then the job
                x = nm1.group(1)
                msg = f"My name is {x[:1].upper() + x[1:]}. {two[1]}"
        pn_ = st.uses.get("person_noun")
        pet_ = st.uses.get("pet")
        if pn_ and st.turn - pn_[1] <= 4 and not (pet_ and pet_[1] > pn_[1]):
            m = _PET_NAME.match(msg.strip(" .!"))
            if m:                                         # "her name is lena" after "my sister is visiting"
                nm = (m.group("x") or m.group("y")).strip()
                msg = f"My {pn_[0]} is called {nm[:1].upper() + nm[1:]}."
            else:
                lv = re.fullmatch(r"(?i)(?:and |oh,? |well,? )?(?:she|he|they) (?:really |absolutely |just )?(loves?|likes?|enjoys?|is into|are into|"
                                  r"adores?|is crazy about|is obsessed with) ([a-z][a-z ]{1,30})[.!]*", msg.strip())
                if lv:                                    # "she loves art": a fact about the sister, and a hint for ideas
                    verb = lv.group(1).lower()
                    verb = verb if verb.endswith("s") or " " in verb else verb + "s"
                    st.uses["person_likes"] = [lv.group(2).strip().lower(), st.turn]
                    msg = f"My {pn_[0]} {verb} {lv.group(2).strip()}."
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
        bd = re.fullmatch(r"(?i)(?:oh,? |actually,? |btw,? )?(?:my birthday|my bday|it'?s my birthday|it was my birthday)"
                          r"(?: (?:is|was|'s))? (yesterday|today|tomorrow)(?: actually)?[.!]*", msg.strip())
        if bd:                                            # "my birthday was yesterday": the date, not "yesterday"
            day = self._today() + dt.timedelta(days={"yesterday": -1, "today": 0, "tomorrow": 1}[bd.group(1).lower()])
            st.uses["bday_rel"] = [bd.group(1).lower(), st.turn]
            msg = f"My birthday is {day.day} {day.strftime('%B')}."
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
            x = re.sub(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\b",
                       lambda m: m.group(0)[:1].upper() + m.group(0)[1:], x)     # "Mondays", but "rainy days"
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "daily:dislike_relatable", self.bank.daily["dislike_relatable"],
                                                      x=x),
                         via="empathy")
        if dm:
            # "i dont like movies": remember it as a dislike and ask what they do enjoy
            x = dm.group("x").strip()
            rep = self._learn(st, [f"I don't like {x}."], msg)      # "i hate mushrooms" is a dislike, never a favourite
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
        if len(units) == 2 and units[0].act == "intent" and units[0].intent in ("yes", "no", "ack", "thanks") and \
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
            if hit is not None and (_SEE_THERE.match(normalise(msg).strip()) or _EAT_THERE.match(normalise(msg).strip())
                                    or _WEAR.match(normalise(msg).strip()) or _TEXT_EX.match(normalise(msg).strip())):
                hit = None                                # "what should I see in Tokyo?": travel tips, not live data
            # "I have an exam tomorrow" tells ENGRAMM something to remember; only requests are commands
            if hit is not None and units[0].act == "statement" and re.match(r"(?:i|i'm|im|i've|my|we|we're|our|she|he|they|his|her|their)\b",
                                                                            msg, re.I):
                hit = None
            if hit is not None and units[0].act == "statement" and not re.match(
                    r"(?:ok(?:ay)?,? |hey,? |please |pls |can you |could you |would you |will you )*(?:set|remind|play|turn|switch|call|"
                    r"open|start|wake|schedule|add|book|order|text|send|stop|pause|resume|show|dim|lock|unlock|put on|make a|create|cancel|"
                    r"delete|skip|record|take a|navigate|find (?:me )?a (?:route|restaurant)|buy)\b", msg.strip(), re.I):
                hit = None                                # "everyone at work seems smarter" is no command
            if hit is not None:
                return Reply(msg, "unknown", self._reply(st, f"device.{hit[0]}"), via="device")
        parts: list[_Part] = []
        main: Reply | None = None
        learn: list[Unit] = []
        quiet: list[Unit] = []
        content = any(u.act not in ("intent", "empty") or (u.intent and self._is_content_intent(u.intent))
                      for u in units)
        seen_intents: set[str] = set()       # "bye. see you": one goodbye, not two
        emp_said = False
        units = [u for u in units if not (u.act == "intent" and u.intent and
                                          (u.intent in seen_intents or seen_intents.add(u.intent)))]
        if any(u.intent == "compliment_bot" for u in units):
            # "thanks! you're smart": one warm reply ("Aw, thanks!"), not "You're welcome! Aw, thanks!"
            units = [u for u in units if u.intent != "thanks"] or units
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
                    if not emp_said:                      # three sad sentences in one message: one warm reply, not three
                        parts.append(_Part("prefix", self.everyday.moment(st, exp, u.text)))
                        emp_said = True
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
                if emp_said:
                    pass                                  # one empathetic reply per message is enough
                elif exp is not None and exp.topic and u.data.get("category") in _GENERAL_MOODS and \
                        not u.data.get("negated"):
                    # "my boss was so annoying": name the boss, not just the mood
                    parts.append(_Part("prefix", self.everyday.moment(st, exp, u.text)))
                else:
                    parts.append(_Part("prefix", self._feeling(st, u)))
                emp_said = True
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
        if learn and emp_said:
            r = self._learn(st, [u.text for u in learn], msg)   # a hard day told in three sentences: remembered quietly
            main = main or r
        elif learn:
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
        if it.id in ("yes", "ack") and le.get("valence") == "negative" and st.turn - le.get("turn", -99) <= 1 and \
                st.last_kind in ("empathy", "smalltalk") and (st.last_reply or "").rstrip().endswith("?"):
            text = self._pick(st, "daily:exp_agree_neg", self.bank.daily["exp_agree_neg"])   # "yeah" to "what gets to you?"
            parts.append(_Part("main", text))
            return Reply(u.text, "smalltalk", text, via="empathy")
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
        st.uses["last_intent"] = [it.id, st.turn]
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
            if req.recipient is None and req.recipient_name is None and req.purpose == "generic" and not req.purpose_text \
                    and not req.item and not req.reason:
                # "can you help me write an email": ask who it's for and what about, like a person would
                st.pending = {"slot": "draft_detail", "genre": req.genre, "turn": st.turn}
                return Reply(text, "smalltalk", self._pick(st, "daily:draft_ask", self.bank.daily["draft_ask"], x=req.genre),
                             via="writing")
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
            cm = re.match(r"\s*\d+(?:\.\d+)?\s*([a-z°][a-z° ]*?)\s*=\s*[\d.,]+\s*([a-z°][a-z° ]*?)\.?$", tr.text, re.I)
            if cm:
                st.uses["last_conv"] = [st.turn, cm.group(1).strip(), cm.group(2).strip()]   # "and 10?" next
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
        if re.search(r"(?i)\b(?:do|did|does) they \w+ there\b|\bthere\b.*\?$", text) and st.uses.get("place_topic"):
            text = self._place_carry(st, text)          # "what language do they speak there?" during a trip to Greece
        # "what language do they speak in Brazil?": a generic "they", not the last person or thing
        text = re.sub(r"(?i)\b(do|did|does) they (speak|use|eat|celebrate|drive|call|pay|play)\b(?=.*\bin\b)", r"\1 people \2", text)
        cv = st.uses.get("last_conv")
        cn = re.fullmatch(r"(?:and |what about |how about |now )?(\d+(?:\.\d+)?)\??", text.strip().lower())
        if cv and cn and st.turn - cv[0] <= 3:          # "convert 5 km to miles" … "and 10?"
            tr = tool_answer(f"convert {cn.group(1)} {cv[1]} to {cv[2]}", self._now())
            if tr is not None:
                st.uses["last_conv"] = [st.turn, cv[1], cv[2]]
                return Reply(text, "tool", tr.text if tr.text.endswith(".") else tr.text + ".", answer=tr.value,
                             via="tool", confidence=1.0)
        du = re.fullmatch(r"(?:and |what about |how about )?(?:until|till|to|before) (?P<x>[a-z0-9' ]{3,30}?)\??", text.strip().lower())
        if du and st.last_kind == "tool" and re.search(r"\bdays? until\b", st.last_reply or ""):
            tr = tool_answer(f"how many days until {du.group('x')}", self._now())     # "and until new year?"
            if tr is not None:
                return Reply(text, "tool", tr.text if tr.text.endswith(".") else tr.text + ".", answer=tr.value,
                             via="tool", confidence=1.0)
        hol = _HOLIDAY_Q.match(normalise(text).strip(" ?!."))
        if hol:
            return self._holiday(st, text, hol.group("h"))
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
        pron = None if OWN_PRONOUN.search(text) else re.search(r"\b(he|she|him|his|her|hers|they|them|their)\b", text, re.I)
        gap = st.uses.get("person_gap") == st.turn - 1          # the last "who …?" found nobody
        if re.search(r"\b(?:it|its)\b", text, re.I) and not pron and st.last_kind == "unknown" and \
                bot.resolve(text) == text and not bot.context.get("answer") and \
                not re.search(r"\b(?:i|me|my|you|your)\b", text, re.I):
            # "how tall is it?" right after a question ENGRAMM could not answer: "it" points nowhere
            st.pending = {"slot": "who_mean", "question": text, "pron": "it", "turn": st.turn}
            return Reply(text, "unknown", self._pick(st, "daily:it_mean", self.bank.daily["it_mean"]), via="clarify")
        mp = bot.context.get("many_people")
        if pron and mp and bot.context.get("mention") == mp[0] and not bot.context.get("answer") and \
                pron.group(1).lower() in ("he", "she", "him", "his", "her", "hers") and bot.resolve(text) == text:
            # "where was he born?" after "invented by Meucci, Gray, Bell and Reis": ask which one, like a person would
            st.pending = {"slot": "who_mean", "question": text, "pron": pron.group(1), "turn": st.turn, "many": list(mp[1])}
            return Reply(text, "unknown", self._pick(st, "daily:which_of", self.bank.daily["which_of"], x=_join_or(mp[1]), y=_join_values(mp[1])),
                         via="clarify")
        if pron and not re.search(r"\b(?:i|me|my|you|your)\b", text, re.I) and (bot.resolve(text) == text or gap):
            st.pending = {"slot": "who_mean", "question": text, "pron": pron.group(1), "turn": st.turn}
            return Reply(text, "unknown", self._pick(st, "daily:who_mean", self.bank.daily["who_mean"],
                                                     x=pron.group(1).lower()), via="clarify")
        el = _HOW_ADJ.fullmatch(normalise(text).strip(" ?"))
        ment = self.bot.context.get("mention")
        if el and ment:                                 # "how tall?" right after Mount Everest
            text = f"how {el.group(1)} is {ment}?"
        wtq = self._world_time(st, text) or self._worth_visit(st, text)
        if wtq is not None:
            return wtq
        kf = re.fullmatch(r"(?:and |so |ok,? )?what(?:'s| is| are) (?P<p>[a-z][a-z .'-]{2,25}?) (?:famous|known|best known|popular) for\??",
                          normalise(text).strip())
        if kf and kf.group("p").strip() in self.bank.daily.get("sights", {}):
            key = kf.group("p").strip()                 # "what's berlin famous for?": its classic sights
            shown = _place_case(key)
            st.uses["place_topic"] = [shown, st.turn]
            st.uses["food_offer"] = [shown, st.turn]
            st.uses["sights_shown"] = [key, st.turn]
            return Reply(text, "smalltalk", self._pick(st, "daily:famous_for", self.bank.daily["famous_for"], x=shown,
                                                       y=self.bank.daily["sights"][key]), via="everyday",
                         source={"kind": "common", "source": "everyday facts", "key": ""})
        see = _SEE_THERE.match(normalise(text).strip())
        if see:                                         # "what should I see there?" during a trip to Paris
            pt = st.uses.get("place_topic")
            place = see.group("p") or (pt[0] if pt and st.turn - pt[1] <= 10 else None)
            if place:
                d = self.bank.daily
                key = place.lower().strip()
                shown = _place_case(key)
                ss = st.uses.get("sights_shown")
                if key in d.get("sights", {}) and ss and ss[0] == key and st.turn - ss[1] <= 6:
                    st.uses["food_offer"] = [shown, st.turn]   # the classics were just named: something else, no repeat
                    return Reply(text, "smalltalk", self._pick(st, "daily:sights_again", d["sights_again"], x=shown), via="everyday")
                if key in d.get("sights", {}):
                    st.uses["sights_shown"] = [key, st.turn]
                    st.uses["place_topic"] = [shown, st.turn]
                    lead = self._pick(st, "daily:sights_lead", d["sights_lead"], x=shown, y=d["sights"][key])
                    tail = self._pick(st, "daily:sights_tail", d["sights_tail"], x=shown)
                    st.uses["food_offer"] = [shown, st.turn]
                    return Reply(text, "smalltalk", f"{lead} {tail}", via="everyday",
                                 source={"kind": "common", "source": "everyday facts", "key": ""})
                return Reply(text, "smalltalk", self._pick(st, "daily:sights_none", d["sights_none"], x=shown), via="everyday")
        food = _EAT_THERE.match(normalise(text))
        pt = st.uses.get("place_topic")
        place = (food.group("p") if food and food.group("p") else (pt[0] if pt and st.turn - pt[1] <= 8 else None)) if food else None
        if place:                                       # "what should I eat there?" during a trip to Japan
            rep = self._cuisine(st, text, place)
            if rep is not None:
                return rep
        tl = _THEY_LIVE.match(normalise(text).strip())
        ment = self.bot.context.get("mention")
        if tl and ment and self.kgqa is not None and not st.uses.get("place_topic"):
            # "what language do they speak?" after Tokyo: the people of its country, not of the word "Tokyo"
            land = ment
            try:
                ca = self.kgqa.answer(f"what country is {ment} in?")
            except Exception:
                ca = None
            if ca is not None and ca.values:
                land = ca.values[0]
            kind = "language" if tl.group("k").startswith("language") else "currency"
            text = f"what language do people speak in {land}?" if kind == "language" else f"what currency does {land} use?"
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
        common = self._common_fact(st, text)
        if common is None and _DISTANCE_Q.match(normalise(text)):
            return Reply(text, "unknown", self._pick(st, "daily:distance_none", self.bank.daily["distance_none"]),
                         via="clarify")
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
        ev = self._event_answer(st, text) or self._first_holder(st, text) or self._maker_in_title(st, text) or \
            self._tenure(st, bot.resolve(" ".join(text.split())))
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
            sm_ = re.match(r"(The |)([a-z][a-z' -]+?) (?=is |was |are |were |has |had )", sent or "")
            if sm_ and rep.evidence:
                cap_ = re.search(rf"\b{re.escape(sm_.group(2))}\b", rep.evidence, re.I)
                if cap_ and cap_.group(0)[:1].isupper():   # "The zugspitze is …" → "The Zugspitze is …"
                    sent = sm_.group(1) + cap_.group(0) + sent[sm_.end(2):]
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

    def _job_detail(self, st: DialogState, msg: str) -> Reply | None:
        """Details right after "I got a new job": where ("it's at a bank in frankfurt") and when it
        starts ("I start next monday"), both remembered."""
        d = self.bank.daily
        norm = normalise(msg)
        nj = st.uses.get("new_job")
        if nj is not None and 0 < st.turn - nj <= 3:
            jm = _JOB_AT.fullmatch(norm.strip(" .!"))
            if jm:                                        # "it's at a bank in frankfurt" after "I got a new job"
                x = re.sub(r"\b(in|near|outside) ([a-z][\w-]+(?: [a-z][\w-]+)?)$",
                           lambda m: f"{m.group(1)} {_place_case(m.group(2))}", jm.group("x").strip())
                r = self._learn(st, [f"I work at {x}."], msg)
                r.text = self._pick(st, "daily:job_where", d["job_where"], x=x)
                return r
            sm = _JOB_START.fullmatch(norm.strip(" .!"))
            if sm:                                        # "I start next monday"
                x = re.sub(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|"
                           r"june|july|august|september|october|november|december)\b", lambda m: m.group(1).capitalize(),
                           sm.group("x").strip())
                r = self._learn(st, [f"My new job starts {x}."], msg)
                r.text = self._pick(st, "daily:job_start", d["job_start"], x=x)
                return r
        return None

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
            fam = re.search(r"\b(?:my )?(?P<w>grandma|granny|nan|nana|grandmother|mom|mum|mother|aunt|sister|wife|daughter|grandpa|granddad|"
                            r"grandfather|dad|father|uncle|brother|husband|son)\b", (le.get("text") or "").lower())
            pron = None
            if fam:
                pron = "her" if fam.group("w") in ("grandma", "granny", "nan", "nana", "grandmother", "mom", "mum", "mother", "aunt",
                                                   "sister", "wife", "daughter") else "him"
            m = _GRIEF_AGE.match(norm)
            if m:
                if pron:                                  # "she was 91" after a grandmother: not "years of friendship"
                    return Reply(msg, "smalltalk", self._pick(st, "daily:grief_age_family", d["grief_age_family"], x=m.group("n"), pron=pron),
                                 via="empathy")
                return Reply(msg, "smalltalk", self._pick(st, "daily:grief_age", d["grief_age"], x=m.group("n")),
                             via="empathy")
            if pron and re.match(r"(?:she|he) (?:made|cooked|baked|used to make|used to bake|always made|would make|taught me|sang|told)\b", norm):
                return Reply(msg, "smalltalk", self._pick(st, "daily:grief_memory", d["grief_memory"], pron=pron,
                                                          y=pron if pron == "her" else "his"), via="empathy")
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
        rs = st.uses.get("resto")
        if re.fullmatch(r"(?:so |ok |and )?(?:any |some |got any |do you have any )?(?:good )?(?:restaurant|place to eat|dinner place|places to eat)s? "
                        r"(?:ideas?|suggestions?|recommendations?|tips?)\??|where should (?:we|i) (?:go|eat|go out)(?: for dinner| tonight| to celebrate| to eat)?\??|"
                        r"(?:can you )?recommend (?:a|some) restaurants?\??", norm.strip()) or \
                (rs is not None and st.turn - rs <= 2 and re.fullmatch(r"(?:something |somewhere |a )?(?:fancy|special|nice|upscale|romantic|classy)(?: place| restaurant)?(?: please| then| maybe)?",
                                                                       norm.strip(" .!"))):
            st.uses["resto"] = st.turn                    # "any restaurant ideas?" for a celebration dinner
            return Reply(msg, "smalltalk", self._pick(st, "daily:celebrate_food", d["celebrate_food"]), via="everyday")
        lneg = st.last_exp or {}
        if lneg.get("valence") == "negative" and st.turn - lneg.get("turn", -99) <= 2 and re.fullmatch(
                r"(?:but |and )?i (?:studied|worked|tried|practi[cs]ed|prepared|trained) (?:so |really |super |very )?(?:hard|much|a lot)"
                r"(?: for (?:it|this|that|weeks|months))?[.!]*", norm.strip()):
            st.last_exp = dict(lneg, text=f"{lneg.get('text', '')} {msg}".strip(), turn=st.turn)
            return Reply(msg, "empathy", self._pick(st, "daily:effort_neg", d["effort_neg"]), via="empathy")
        if re.fullmatch(r"(?:ok(?:ay)?,? |thanks,? |thank you,? |good idea,? |alright,? )*(?:i'?ll|ill|i will|i'?m going to|im going to|i'?m gonna|gonna) "
                        r"(?:make|have|get|grab|cook|drink|order|eat|try|watch|read|take|do|study|practi[cs]e) (?:some |a |an |me (?:a |some )?)?[a-z][a-z ]{1,25}"
                        r"(?: then| now| later| tonight| first)?[.!]*", norm.strip()):
            sk2 = st.uses.get("sick")
            ln = st.last_exp or {}
            key = "get_well" if sk2 is not None and st.turn - sk2 <= 6 else \
                "try_again" if ln.get("valence") == "negative" and st.turn - ln.get("turn", -99) <= 4 else "future_plan"
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="smalltalk")
        sk = st.uses.get("sick")
        if sk is not None and st.turn - sk <= 5 and re.fullmatch(r"(?:so |but |and )?(?:should|can|do) i (?:still )?(?:go to|go into|go in to) "
                                                                  r"(?:work|school|uni|class|the office|the gym)(?: today| tomorrow)?\??", norm.strip()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:sick_work", d["sick_work"]), via="everyday")
        if re.fullmatch(r"(?:and |honestly,? |i mean,? )?(?:i )?(?:just )?(?:feel|felt|am|'?m) (?:like )?(?:such |a |an |a total |a complete |so )*"
                        r"(?:failure|loser|idiot|stupid|useless|not good enough|disappointment|fraud|let ?down)(?: right now| today| lately)?[.!]*",
                        norm.strip()):
            st.last_exp = dict(st.last_exp, valence="negative", text=f"{st.last_exp.get('text', '')} {msg}".strip(), turn=st.turn) if st.last_exp else \
                {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:self_worth", d["self_worth"]), via="empathy")
        ps = re.fullmatch(r"(?:oh no,? |ugh,? |so,? )?my (dog|cat|puppy|kitten|hamster|rabbit|bunny|parrot|bird|horse|guinea pig) "
                          r"(?:is|seems|has been|got|'s|looks) (?:really |so |very |a bit |kind of )?(?:sick|ill|unwell|not well|poorly|hurt|injured)"
                          r"(?: today| again)?[.!]*", norm.strip())
        if ps:                                            # "my dog is sick": a worried owner, not "the first time with your dog?"
            st.last_exp = {"valence": "negative", "topic": f"your {ps.group(1)}", "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:pet_sick", d["pet_sick"], x=ps.group(1)), via="empathy")
        ta = st.uses.get("trip_ask")
        if re.search(r"\bwhere (?:are you|to)\b|\bwhere are you (?:going|heading|off to)\b|\banywhere nice\b|\bwhere\b.*\?",
                     (st.last_reply or "").lower()) or (ta is not None and st.turn - ta <= 2):
            dm_ = re.fullmatch(r"(?:to |we'?re going to |i'?m going to |going to |heading to |off to )?(?P<p>[a-z][a-z .'-]{2,25}?)"
                               r"(?: (?:for (?:a|two|one|three) (?:week|weeks|days)|with (?:my|friends|family)[a-z ]*))?[.!]*", norm.strip())
            if dm_ and (dm_.group("p") in d.get("sights", {}) or self._is_place(dm_.group("p"))):
                place = _place_case(dm_.group("p"))          # "to greece" after "where are you going?"
                st.uses["place_topic"] = [place, st.turn]
                st.uses["trip"] = [place, st.turn]
                self._learn(st, [f"I am going on holiday to {place}."], msg)
                return Reply(msg, "smalltalk", self._pick(st, "daily:trip_dest", d["trip_dest"], x=place), via="everyday")
        tr_ = st.uses.get("trip")
        if re.fullmatch(r"(?:so |and |ok )?(?:what should i (?:pack|bring|take)(?: with me)?|what (?:do|should) i need to (?:pack|bring)|"
                        r"any packing tips|help me pack|what to pack)(?: for (?:the|my) (?:trip|holiday|vacation))?\??", norm.strip()):
            hr = self._howto(st, "how do i pack for a trip")      # "what should I pack?" before a holiday
            if hr is not None:
                return hr
        du2 = re.fullmatch(r"(?:and |what about |how about )?(?:until|till|to|before) (?P<x>[a-z0-9' ]{3,30}?)\??", norm.strip())
        if du2 and st.last_kind == "tool" and re.search(r"\bdays? until\b", st.last_reply or ""):
            tr = tool_answer(f"how many days until {du2.group('x')}", self._now())     # "and until halloween"
            if tr is not None:
                return Reply(msg, "tool", tr.text if tr.text.endswith(".") else tr.text + ".", answer=tr.value, via="tool")
        if re.fullmatch(r"(?:yeah,? |yes,? |ugh,? |honestly,? )?(?:the |my |these )?(?:night shifts?|nightshifts?|long shifts|double shifts|"
                        r"12[- ]hour shifts|early shifts|late shifts|shifts|weekend shifts) (?:are|is|have been|were) "
                        r"(?:so |really |super |pretty |very |kinda )?(?:tough|hard|exhausting|brutal|rough|killing me|draining|a lot)[.!]*",
                        norm.strip()):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg + " tired", "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:shifts_tough", d["shifts_tough"]), via="empathy")
        cf = re.fullmatch(r"(?:so |guess what,? )?i (?:just )?(?:cooked|made|baked) (?:a )?(?:dinner|lunch|breakfast|brunch|a cake|"
                          r"something|a meal|food) for (?:my )?(?P<w>girlfriend|boyfriend|wife|husband|partner|family|parents|mom|mum|dad|"
                          r"friends|kids|date|roommates?)(?: tonight| today| yesterday)?[.!]*", norm.strip())
        if cf:                                            # "i cooked dinner for my girlfriend tonight"
            st.uses["cooked_for"] = st.turn
            st.last_exp = {"valence": "positive", "topic": None, "person": True, "text": msg, "turn": st.turn}
            self._learn(st, [msg], msg)
            return Reply(msg, "smalltalk", self._pick(st, "daily:cooked_for", d["cooked_for"]), via="empathy")
        cfd = st.uses.get("cooked_for")
        if cfd is not None and st.turn - cfd <= 3:
            mdish = re.fullmatch(r"(?:i (?:made|cooked|baked)|it was|we had) (?:a |an |some |my |homemade )?(?P<x>[a-z][a-z ]{2,30}?)[.!]*", norm.strip())
            if mdish:
                x = mdish.group("x")
                return Reply(msg, "smalltalk", self._pick(st, "daily:cooked_dish", d["cooked_dish"], x=x, X=x[:1].upper() + x[1:]),
                             via="empathy")
        go = st.uses.get("guide_offer")
        if go and st.turn - go[1] <= 1 and re.fullmatch(r"(?:yes|yeah|yep|sure|ok|okay|please|yes please|go on|why not|"
                                                         r"sure why not|definitely|that would help|ok tell me)[!. ]*", norm.strip()):
            st.uses.pop("guide_offer", None)              # "yes" after "want a few ideas …?": the guide offered
            hr = self._howto(st, go[0])
            if hr is not None:
                return hr
        if re.search(r"\bi (?:don'?t|do not) know (?:anyone|anybody|a single person|many people)(?: here| there| yet| in (?:the|this) city)?\b|"
                     r"\bi have no friends (?:here|there|yet)\b", norm):
            st.uses["guide_offer"] = ["how can i make friends in a new city", st.turn]   # "but i don't know anyone here"
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:new_city_alone", d["new_city_alone"]), via="empathy")
        if st.last_kind == "tool" and re.search(r"°[CF]", st.last_reply or "") and re.fullmatch(
                r"(?:so |and )?(?:is (?:that|it) (?:hot|cold|warm|cool|chilly|freezing|a lot|normal|nice)|how (?:hot|cold|warm) is that)\??",
                norm.strip()):
            m_c = re.search(r"(-?\d+(?:[.,]\d+)?) ?°C", st.last_reply or "")
            if m_c:                                       # "is that hot?" right after "30 °C = 86 °F"
                c = float(m_c.group(1).replace(",", "."))
                key = "freezing" if c <= 0 else "cold" if c < 10 else "cool" if c < 17 else "mild" if c < 23 else \
                    "warm" if c < 28 else "hot" if c < 35 else "very_hot"
                return Reply(msg, "smalltalk", d["temp_feel"][key].format(x=m_c.group(1)), via="tool")
        if re.fullmatch(r"(?:and |plus |also |ugh,? )?(?:the |my |our )?rent (?:is|keeps going up|went up|got)(?: (?:too|so|way too|really|crazy|insanely))? "
                        r"?(?:expensive|high|much|up)?(?: (?:here|now|again))?[.!]*", norm.strip()) or \
                re.fullmatch(r"(?:everything|prices|food|groceries|bills) (?:is|are) (?:so |too |really |way too )?expensive(?: now| lately)?[.!]*", norm.strip()):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg + " money", "turn": st.turn}
            st.uses["guide_offer"] = ["how can i save money", st.turn]
            return Reply(msg, "empathy", self._pick(st, "daily:money_tight", d["money_tight"]), via="empathy")
        pt2 = st.uses.get("pet")
        if pt2 and st.turn - pt2[1] <= 6 and re.fullmatch(r"(?:so |and |but )?(?:should|do) i (?:take|bring|call) (?:him|her|it|them|my \w+|the \w+) "
                                                           r"(?:to the vet(?:'?s)?|to a vet)|(?:should|do) i (?:call|see|go to) (?:a|the) vet(?:'?s)?"
                                                           r"(?: now| today| tomorrow)?\??", norm.strip()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:vet_advice", d["vet_advice"], x=pt2[0]), via="everyday")
        if pt2 and st.turn - pt2[1] <= 3 and re.fullmatch(r"(?:and |but )?(?:he|she|it)(?:'s| is| has| hasn'?t|'s been| has been| keeps| just)? "
                                                           r"(?:not eating|stopped eating|won'?t eat|doesn'?t eat|isn'?t eating|throwing up|"
                                                           r"vomiting|limping|very tired|so tired|sleeping all day|not drinking|eaten anything|"
                                                           r"threw up|thrown up|vomited|was sick|got diarrh(?:o)?ea|diarrh(?:o)?ea|coughing|shaking)"
                                                           r"(?: (?:twice|three times|again|a lot|a few times|once))?(?: (?:since|for) [a-z0-9 ]{1,20})?"
                                                           r"(?: (?:today|this morning|last night|tonight|yesterday))?[.!]*", norm.strip()):
            return Reply(msg, "empathy", self._pick(st, "daily:pet_unwell", d["pet_unwell"], x=pt2[0]), via="empathy")
        wv = self._worth_visit(st, msg)
        if wv is not None:
            return wv
        if re.fullmatch(r"(?:ugh,? |oh no,? )?(?:i think |i feel like |i guess )?(?:i'?m|im|i am) (?:getting|coming down with|going to be|gonna be) "
                        r"(?:sick|ill|a cold|something|the flu)|i (?:feel|am feeling|'m feeling) (?:sick|ill|unwell|under the weather|rough)"
                        r"(?: today)?[.!]*", norm.strip()):
            st.uses["sick"] = st.turn
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:getting_sick", d["getting_sick"]), via="empathy")
        lpos = st.last_exp or {}
        if lpos.get("valence") == "positive" and st.turn - lpos.get("turn", -99) <= 3 and re.search(
                r"\b(?:worked (?:so |really |very |super )?hard|so much (?:work|effort)|(?:it was|so) worth it|paid off|"
                r"deserved (?:it|this)|earned (?:it|this)|been waiting (?:so long|for this|forever)|years of work|months of work)\b",
                norm):                                    # "thanks! i worked so hard for it" after a promotion: pride, not pity
            st.last_exp = dict(lpos, turn=st.turn)
            return Reply(msg, "empathy", self._pick(st, "daily:proud", d["proud"]), via="empathy")
        wtr = self._world_time(st, msg)
        if wtr is not None:
            return wtr
        from engramm.chat.tools import _PHRASES, translate
        trl = st.uses.get("tr_lang")
        if trl and st.turn - trl[1] <= 3:
            fp = re.fullmatch(r"(?:and |what about |how about )?(?:how do (?:you|i) say )?[\"“']?(?P<p>[a-z' ]{2,30}?)[\"”']?\??", norm.strip())
            if fp and fp.group("p").strip() in _PHRASES:  # "and good morning?" after "thank you in French"
                res = translate(f"how do you say {fp.group('p').strip()} in {trl[0]}")
                if res is not None:
                    trl[1] = st.turn
                    return Reply(msg, "tool", res.text, answer=res.value, via="tool")
        fo = st.uses.get("food_offer")
        if fo and st.turn - fo[1] <= 1 and re.fullmatch(r"(?:yes|yeah|yep|sure|ok|okay|please|yes please|go on|sure why not|"
                                                         r"why not|definitely|absolutely|of course)[!. ]*", norm.strip()):
            st.uses.pop("food_offer", None)               # "yes" after "want some food tips for Paris too?"
            rep = self._cuisine(st, msg, fo[0])
            if rep is not None:
                return rep
        so = st.uses.get("sleep_offer")
        if so is not None and st.turn - so <= 1 and re.fullmatch(r"(?:yes|yeah|yep|sure|ok|okay|please|yes please|go on|"
                                                                  r"sure why not|why not|tips please|ok tell me)[!. ]*", norm.strip()):
            st.uses.pop("sleep_offer", None)              # "yes please" after "want a few tips for tonight?"
            return self.everyday.recommend(st, msg, "sleep")
        if re.fullmatch(r"(?:yeah,? |yes,? |honestly,? |tbh,? |lol,? )?(?:it )?(?:feels|it feels|it'?s|its|kinda feels) (?:kinda |a bit |so |really |pretty |super |a little )?"
                        r"(?:weird|strange|odd|surreal|unreal|different)(?: (?:tbh|honestly|lol|though))?[.!]*", norm.strip()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:feels_weird", d["feels_weird"]), via="smalltalk")
        pl = st.uses.get("person_likes")
        if pl and pl[1] == st.turn and la.get("kind") == "rec:activity" and st.turn - la.get("turn", -99) <= 3:
            idea = next((v for k, v in d["like_ideas"].items() if re.search(rf"\b{k}", pl[0])), None)
            if idea:                                      # "she loves art" after "what could we do?": a fitting idea
                r = self._learn(st, [msg], msg)
                r.text = self._pick(st, "daily:like_idea", d["like_idea"], x=idea)
                return r
        fc = st.uses.get("food_ctx")
        llf = getattr(st, "last_list", None) or {}
        food_recent = (fc is not None and st.turn - fc <= 3) or (llf.get("kind") == "food" and st.turn - llf.get("turn", -99) <= 3)
        ih = re.fullmatch(r"(?:well,? |hmm,? |um+,? )?(?:i (?:only |just )?have|i'?ve got|i got|we have|all i have is|there'?s|i have got)"
                          r" (?:some |a few |a bit of |only )?(?P<x>[a-z][a-z ,'-]{2,60}?)(?: (?:at home|in the fridge|left|here))?[.!]*",
                          norm.strip())
        if food_recent and re.fullmatch(r"(?:that |this )?(?:sounds (?:good|great|perfect|delicious|tasty|yummy|amazing)|perfect|yum+y?|"
                                        r"great idea|good idea|i'?ll (?:do|make|try) (?:that|it)|let'?s do (?:that|it)|nice)[.! ]*", norm.strip()):
            st.uses.pop("food_ctx", None)
            return Reply(msg, "smalltalk", self._pick(st, "daily:food_enjoy", d["food_enjoy"]), via="everyday")
        if food_recent and ih:                            # "i have eggs and spinach" after "what should I make?"
            x = ih.group("x")
            items = [i.strip() for i in re.split(r",|\band\b", x) if i.strip()]
            stems = {re.sub(r"(?:es|s)$", "", i.split()[-1]) for i in items}
            stems |= {i.split()[-1].rstrip("s") for i in items}
            for row in d.get("ingredient_ideas", []):
                if all(n in stems for n in row["need"]):
                    return Reply(msg, "smalltalk", self._pick(st, "daily:ingredient_lead", d["ingredient_lead"], x=x,
                                                              y=row["idea"]), via="everyday")
            return Reply(msg, "smalltalk", self._pick(st, "daily:ingredient_none", d["ingredient_none"], x=x), via="everyday")
        if (fc is not None and st.turn - fc <= 2) or (llf.get("kind") == "food" and st.turn - llf.get("turn", -99) <= 2):
            mf = re.fullmatch(r"(?:idk,? |i don'?t know,? |dunno,? |hmm+,? |um+,? |well,? |ok,? |lol,? )*(?:maybe|probably|i guess|i think|perhaps|"
                              r"thinking|i want|i'd say|i feel like|craving) (?:some |a |an )?(?P<x>[a-z][a-z ]{2,24}?)"
                              r"(?: i guess| maybe| tonight| then| lol| tbh)?[.!?]*", norm.strip())
            typer = getattr(self.bot, "typer", None)
            if mf and (mf.group("x") in _COMMON_FOODS or mf.group("x").rstrip("s") in _COMMON_FOODS or
                       (typer is not None and typer.category(mf.group("x")) == "#food")):
                st.uses.pop("food_ctx", None)             # "idk maybe pizza" after "I'm hungry": go with it
                recap = st.uses.setdefault("recap", [])
                recap[:] = [x for x in recap if x != "food"] + ["food"]
                return Reply(msg, "smalltalk", self._pick(st, "daily:food_pick", d["food_pick"], x=mf.group("x"),
                                                          X=mf.group("x")[:1].upper() + mf.group("x")[1:]), via="everyday")
        br = st.uses.get("bday_rel")
        if br and br[1] == st.turn and norm.startswith("my birthday is"):
            r = self._learn(st, [msg], msg)               # "my birthday was yesterday": wishes, and the date kept
            key = {"yesterday": "bday_yesterday", "today": "bday_today", "tomorrow": "bday_tomorrow"}[br[0]]
            r.text = self._pick(st, f"daily:{key}", d[key], x=msg[len("My birthday is "):].rstrip("."))
            return r
        tn = re.fullmatch(r"(?:so |well |guess what,? )?(?:i )?(?:just |finally |recently |officially )?turned (\d{1,3})"
                          r"(?: (?:today|yesterday|last week|this week|on (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)))?[.!]*",
                          norm.strip())
        if tn and 1 <= int(tn.group(1)) <= 120:
            r = self._learn(st, [msg], msg)               # "i just turned 30": a birthday, said like one
            r.text = self._pick(st, "daily:turned", d["turned"], x=tn.group(1))
            st.last_exp = {"valence": "positive", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return r
        lst = getattr(st, "last_list", None) or {}
        if lst.get("titles") and st.turn - lst.get("turn", -99) <= 3 and _IT_ABOUT.match(norm.strip()):
            titles = [re.sub(r"\s*\([^)]*\)$", "", x) for x in lst["titles"]]
            if len(titles) == 1:                          # "what's it about?" after one suggestion: that one
                rep = self.everyday.pick_from_list(st, msg, "the first one")
                if rep is not None:
                    return rep
            tp = st.topic or {}
            if tp.get("turn") == st.turn - 1 and tp.get("title") in titles and titles.index(tp["title"]) < 5:
                nth = ("first", "second", "third", "fourth", "fifth")[titles.index(tp["title"])]
                rep = self.everyday.pick_from_list(st, msg, f"the {nth} one")   # "is it good?" after "who wrote the first one?"
                if rep is not None:
                    return rep
            shown = ", ".join(f"“{x}”" for x in titles[:-1]) + f" or “{titles[-1]}”"
            return Reply(msg, "smalltalk", self._pick(st, "daily:which_one", d["which_one"], x=shown), via="everyday")
        m3 = re.fullmatch(r"(?:what'?s|what is|how much is|how many is) (\d+) ([a-z]+) (plus|and|\+|minus|-|times) (\d+)(?: more)? ?([a-z]+)?\??",
                          norm.strip())
        if m3 and (m3.group(5) in (None, m3.group(2), m3.group(2) + "s") or m3.group(2) == m3.group(5) + "s"):
            a, b = int(m3.group(1)), int(m3.group(4))     # "what's 3 eggs plus 2 eggs": 5 eggs
            r = a + b if m3.group(3) in ("plus", "and", "+") else a - b if m3.group(3) in ("minus", "-") else a * b
            noun = m3.group(5) or m3.group(2)
            return Reply(msg, "tool", f"{r} {noun}.", via="tool")
        if re.fullmatch(r"(?:ugh,? |honestly,? )?i (?:hate|dread|can'?t stand|really hate|am scared of|'m scared of|fear) "
                        r"(?:going to )?the (?:dentists?|doctors?|dentist'?s|doctor'?s)", norm.strip(" .!")):
            return Reply(msg, "empathy", self._pick(st, "daily:dread_dentist", d["dread_dentist"]), via="empathy")
        lm = _LEARNING.match(norm.strip(" .!"))
        if lm:                                            # "i'm learning to play guitar": ask like a friend would
            what = lm.group("x")
            key = "language" if what in _LANGS else what
            if key in d["learning"]:
                st.uses["learning"] = [key, what, st.turn]
                self._learn(st, [f"I am learning {what}."], msg)
                return Reply(msg, "smalltalk", self._pick(st, f"daily:learning:{key}:start", d["learning"][key]["start"],
                                                          x=what.capitalize() if key == "language" else what), via="everyday")
        lg = st.uses.get("learning")
        if lg and st.turn - lg[2] <= 8 and not ((st.last_exp or {}).get("turn", -99) > lg[2] or
                                                 (st.last_action or {}).get("turn", -99) > lg[2]):
            sec = d["learning"][lg[0]]
            for part, rx in _LEARN_FOLLOW:
                if part in sec and rx.search(norm):
                    lg[2] = st.turn
                    x = lg[1].capitalize() if lg[0] == "language" else lg[1]
                    return Reply(msg, "smalltalk", self._pick(st, f"daily:learning:{lg[0]}:{part}", sec[part], x=x),
                                 via="everyday")
        lp = st.last_exp or {}
        if lp.get("person") and st.turn - lp.get("turn", -99) <= 2 and re.fullmatch(
                r"(?:and |yeah,? |honestly,? |i mean,? )?(?:i )?(?:just )?(?:feel|felt|am feeling|'?m feeling|kinda feel) (?:so |really |kinda |a bit |pretty |very )?"
                r"(?:left out|excluded|hurt|betrayed|forgotten|unimportant|replaced|ignored|rejected|unwanted|invisible|sad about it|"
                r"stupid|like i don'?t matter|like they don'?t care)[.!]*", norm.strip()):
            # "i feel left out" right after "my friend didn't invite me": about the friend, not general loneliness
            st.last_exp = dict(lp, text=f"{lp.get('text', '')} {msg}".strip(), turn=st.turn)
            topic = lp.get("topic") or "them"
            return Reply(msg, "empathy", self._pick(st, "daily:hurt_by_person", d["hurt_by_person"], x=topic), via="empathy")
        if re.fullmatch(r"(?:but |and |so )?what if (?:she|he|they|my \w+)(?: just)? (?:gets?|becomes?|is|are|feels?) (?:really |so |super )?"
                        r"(?:mad|angry|upset|hurt|annoyed|offended|defensive|sad|weird about it)(?: at me| with me)?\??", norm.strip()):
            return Reply(msg, "empathy", self._pick(st, "daily:what_if_mad", d["what_if_mad"]), via="empathy")
        if re.fullmatch(r"(?:ok(?:ay)?,? |alright,? |yeah,? |fine,? |sure,? )?(?:i'?ll|ill|i will|i'?m gonna|im gonna|gonna|i'?m going to) "
                        r"(?:try|do it|do that|try that|try it|give it a (?:try|shot|go)|talk to (?:her|him|them)|tell (?:her|him|them)|"
                        r"text (?:her|him|them)|call (?:her|him|them))(?: (?:then|tomorrow|later|today|tonight|soon))?(?: thanks?)?[.!]*",
                        norm.strip()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:will_try", d["will_try"]), via="smalltalk")
        if _WILL_THEY.match(norm):                        # "do you think she'll come back?": honest, kind, no article
            return Reply(msg, "empathy", self._pick(st, "daily:will_they", d["will_they"]), via="empathy")
        if _BOT_LIKES.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_likes", d["bot_likes"]), via="smalltalk")
        if _SLEPT_GOOD.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:slept_good", d["slept_good"]), via="empathy")
        if _SLEPT_BAD.match(norm):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            st.uses["sleep_offer"] = st.turn
            return Reply(msg, "empathy", self._pick(st, "daily:slept_bad", d["slept_bad"]), via="empathy")
        an = re.fullmatch(r"(?:and |also |plus |or )?(?:a|an|some|any) (?:good |great |fun )?([a-z]+)(?: too| as well)?\??", norm.strip())
        if an and la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3:
            from engramm.chat.everyday import _REC_NOUN
            k3 = _REC_NOUN.get(an.group(1))
            if k3:                                        # "and a podcast?" after book ideas
                return self.everyday.recommend(st, msg, k3)
        ha = _HOW_ABOUT.match(norm)
        if ha and not self.everyday._recommend_kind(norm):
            x = ha.group("x").strip()                     # "how about a walk": a suggestion, not a question
            return Reply(msg, "smalltalk", self._pick(st, "daily:suggest_ok", d["suggest_ok"], x=x), via="smalltalk")
        lk2 = _LIKE_TITLE.match(norm)
        if lk2 and la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3:
            kind = la["kind"][4:]                         # "something like harry potter" after book ideas
            x = lk2.group("x").strip(" ?!.")
            genre = None
            for k2, sec in d["recommend"].items():
                for it in sec.get("items", []) if isinstance(sec, dict) else []:
                    if not isinstance(it, dict):
                        continue
                    title = str(it.get("title") or "").lower()
                    if title and (x in title or title in x):
                        tags = [g for g in str(it.get("tags", "")).split() if g not in ("fiction", "classic")]
                        genre = genre or (tags[0] if tags else None)
            genre = genre or _LIKE_GENRE.get(x)
            if not genre:                                 # a title I don't know: ask, don't store it as a fact
                shown = " ".join(w[:1].upper() + w[1:] for w in x.split())
                return Reply(msg, "smalltalk", self._pick(st, "daily:like_unknown", d["like_unknown"], x=shown),
                             via="everyday")
            if genre:
                rep = self.everyday.recommend(st, msg, kind, genre)
                if "\n" in rep.text:
                    shown = " ".join(w if w in ("of", "the", "and") else w[:1].upper() + w[1:] for w in x.split())
                    body = "\n".join(l for l in rep.text.split("\n")[1:] if x not in l.lower())
                    rep.text = self._pick(st, "daily:like_title", d["like_title"], x=shown) + "\n" + body
                return rep
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
        if _PLAN_DAY.match(norm):
            st.uses["plan_day"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "daily:plan_day_ask", d["plan_day_ask"]), via="everyday")
        if _SO_MUCH.match(norm):                          # "i have so much to do today": offer to sort it
            st.uses["plan_day"] = st.turn
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:so_much", d["so_much"]), via="empathy")
        if re.fullmatch(r"(?:ugh,? |urgh,? |oh,? |man,? )?(?:mondays?|monday again|another monday|"
                        r"(?:a )?case of the mondays|monday blues)[.!]*", norm.strip()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:mondays", d["mondays"]), via="smalltalk")
        pt_ = st.uses.get("plan_tasks")
        if pt_ and st.turn - pt_[1] <= 3 and re.fullmatch(r"(?:so |ok |and )?(?:which (?:one )?first|what (?:should i do |do i do )?first|"
                                                           r"where (?:should|do) i start|what'?s first|which one should i start with)\??",
                                                           norm.strip()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:plan_first", d["plan_first"], x=pt_[0][0],
                                                      X=pt_[0][0][:1].upper() + pt_[0][0][1:]), via="everyday")
        pdu = st.uses.get("plan_day")
        if pdu is not None and st.turn - pdu <= 2 and not msg.rstrip().endswith("?"):
            tasks = self._day_tasks(norm)
            if len(tasks) >= 2:
                st.uses.pop("plan_day", None)
                order = {t: (next((i for i, rx in enumerate(_TASK_ORDER) if rx.search(t)), 2), n) for n, t in enumerate(tasks)}
                tasks = sorted(tasks, key=lambda t: order[t])
                st.uses["plan_tasks"] = [tasks, st.turn]
                shown_t = [re.sub(r"\bmy\b", "your", re.sub(r"\bme\b", "you", x)) for x in tasks]   # "call my mom" → "call your mom"
                st.uses["plan_tasks"] = [shown_t, st.turn]
                body = "\n".join(f"{i + 1}. {t[:1].upper() + t[1:]}" for i, t in enumerate(shown_t))
                return Reply(msg, "smalltalk", f"{self._pick(st, 'daily:plan_day_head', d['plan_day_head'])}\n\n{body}\n\n"
                             f"{self._pick(st, 'daily:plan_day_tip', d['plan_day_tip'])}", via="everyday")
        if _TODAY_Q.match(norm):                          # "any plans for me today?": today's events and notes
            from engramm.chat.realize import to_second_person
            self.bot.refresh()
            texts = self.bot.user_texts()
            today = self._today().isoformat()
            items = []
            for e in self.events.events:
                if e.day == today and e.source in texts:
                    said = to_second_person(texts[e.source]) or texts[e.source]
                    items.append(said.rstrip(".!") + ("" if re.search(r"\b(?:today|tonight|later|at \d)", said, re.I) else " today"))
            items += ["You wanted to " + re.sub(r"\bmy\b", "your", re.sub(r"^I need to\s+", "", tx)).rstrip(".")
                      for tx in texts.values() if re.match(r"^I need to\s+", tx)]
            if items:
                return Reply(msg, "memory", self._pick(st, "daily:today_head", d["today_head"]) + "\n" +
                             "\n".join("• " + it[:1].upper() + it[1:] + "." for it in items), via="memory")
            return Reply(msg, "memory", self._pick(st, "daily:today_none", d["today_none"]), via="memory")
        if _TODO_Q.match(norm):                           # "what do I need to do?": the notes from "remind me to …"
            self.bot.refresh()
            todo = [re.sub(r"^I need to\s+", "", t).rstrip(".") for t in self.bot.user_texts().values()
                    if re.match(r"^I need to\s+", t)]
            when = re.search(r"\b(tomorrow|tonight|this week)\b", norm)
            if when and any(when.group(1) in t.lower() for t in todo):
                todo = [t for t in todo if when.group(1) in t.lower()]   # "what do i have to do tomorrow?": tomorrow's notes
            if todo:
                return Reply(msg, "memory", "You wanted to:\n" + "\n".join("• " + re.sub(r"\bmy\b", "your", t) for t in todo),
                             via="memory")
            return Reply(msg, "memory", self._pick(st, "daily:todo_none", d["todo_none"]), via="memory")
        rm = _REMIND.match(norm)
        if rm:
            what = rm.group("x").strip(" .!")
            what = re.sub(r"\bmy\b", "your", re.sub(r"\bme\b", "you", what))
            self._learn(st, [f"I need to {rm.group('x').strip(' .!')}."], msg)
            return Reply(msg, "learned", self._pick(st, "daily:remind", d["remind"], x=what), via="memory")
        wm = _WEAR.match(norm)
        if wm:                                            # "what should I wear?" — for what the chat is about
            pp_ = st.uses.get("prep")
            about = " ".join(filter(None, [wm.group("x"), normalise(st.last_message or ""),
                                           pp_[0] if pp_ and st.turn - pp_[1] <= 8 else None]))
            occ = next((k for k, rx in _OCCASIONS if rx.search(about)), "none")
            return Reply(msg, "smalltalk", self._pick(st, f"daily:wear:{occ}", d["wear"][occ]), via="everyday")
        tp = _TRIP_PLAN.search(norm)
        px = ((tp.group("x") or tp.group("y") or "") if tp else "").strip()
        if tp and px not in ("a", "the", "my", "bed", "work", "school", "sleep", "the gym", "the store", "the shop"):
            place = " ".join(w if w in ("of", "and", "the", "de", "la") else w[:1].upper() + w[1:] for w in _place_case(px).split())
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
            g = (am.group("g") or am.group("g2") or "").strip()
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

    def _worth_visit(self, st: DialogState, text: str) -> Reply | None:
        """"Is it worth visiting?" right after the Eiffel Tower: an honest yes, not a text look-up."""
        tw_ = st.topic or {}
        norm = normalise(text).strip()
        if tw_.get("name") and st.turn - tw_.get("turn", -99) <= 4 and re.fullmatch(
                r"(?:so |and |cool,? |nice,? |ok,? )?(?:is it|would you say it'?s|do you think it'?s|is that) (?:really )?worth (?:it|visiting|"
                r"a visit|seeing|going|going to|the trip)\??", norm):
            name = tw_["name"]
            if re.search(r"\b(?:Tower|Bridge|Museum|Palace|Cathedral|Wall|Canal|Gate|Square|Statue|House|Colosseum|Louvre|Pyramids?|"
                         r"Alps|Basilica|Abbey|Castle|Park|Garden|Gardens|Temple|Shrine|Falls|Canyon|Forum|Pantheon|Acropolis)\b",
                         name) and not name.startswith("The "):
                name = "the " + name                      # "the Eiffel Tower is one of those places"
            return Reply(text, "smalltalk", self._pick(st, "daily:worth_visit", self.bank.daily["worth_visit"], x=name,
                                                       X=name[:1].upper() + name[1:]), via="smalltalk")
        return None

    def _world_time(self, st: DialogState, text: str) -> Reply | None:
        """"What time is it in Tokyo?" and "and in New York?" right after (engramm/chat/worldtime.py)."""
        norm = normalise(text).strip()
        la = st.last_action or {}
        wt = _WORLD_TIME.match(norm)
        follow = re.fullmatch(r"(?:(?:and |what about |how about )(?:in )?|in )(?P<p>[a-z][a-z .'-]{1,30}?)\??", norm)
        from engramm.chat.worldtime import time_in
        recent = la.get("kind") == "worldtime" and st.turn - la.get("turn", -99) <= 2
        bare = recent and not wt and not follow and time_in(norm.strip(" ?")) is not None    # "and london"
        if not wt and not (follow and recent) and not bare:
            return None
        place = (wt.group("p") or wt.group("p2")) if wt else follow.group("p") if follow else norm.strip(" ?")
        hit = time_in(place)
        st.last_action = {"kind": "worldtime", "turn": st.turn}
        d = self.bank.daily
        if hit is None:
            return Reply(text, "tool", self._pick(st, "daily:worldtime_none", d["worldtime_none"], x=_place_case(place)),
                         via="tool")
        shown, local = hit
        return Reply(text, "tool", self._pick(st, "daily:worldtime", d["worldtime"], x=shown, y=local.strftime("%H:%M"),
                                              z=local.strftime("%A")), via="tool")

    def _event_q(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """A tournament by its year: who won, where it was held — read from the article's own lead, and
        for the winner also from the next edition's ("France are the defending champions")."""
        q = year = kind = None
        ev = st.uses.get("event_q")
        m = _EVENT_Q.match(norm)
        if m:
            e = m.group("e")
            ym = re.search(r"\b(19\d\d|20\d\d)\b", e)
            name = re.sub(r"\b(?:in )?\d{4}\b", "", e).strip()
            hit = next((k for k, rx, _f in _EVENT_NAMES if re.fullmatch(rx, name)), None)
            if ym and hit:
                q, year, kind = m.group("q"), int(ym.group(1)), hit
            elif ev and st.turn - ev["turn"] <= 4 and hit and not ym:
                q, year, kind = m.group("q"), ev["year"], hit       # "where was the world cup held?" right after
        recent = ev is not None and st.turn - ev["turn"] <= 4
        if q is None and recent:
            m = _EVENT_AGAIN.match(norm)
            mi = _EVENT_IT.match(norm)
            if m:
                q, year, kind = ev["q"], int(m.group("y")), ev["kind"]
            elif mi:
                q, year, kind = (mi.group("q") or "who won"), ev["year"], ev["kind"]
            elif re.search(r"\b(?:top (?:goal ?)?scorer|golden (?:boot|ball)|best player|mvp|most goals|final score)\b", norm):
                title = next(f for k, _rx, f in _EVENT_NAMES if k == ev["kind"]).format(y=ev["year"])
                ev["turn"] = st.turn
                return Reply(msg, "unknown", self._pick(st, "daily:event_unknown", self.bank.daily["event_unknown"], x=title),
                             via="about")
        if q is None:
            return None
        fmt = next(f for k, _rx, f in _EVENT_NAMES if k == kind)
        title = fmt.format(y=year)
        found = self.about.find(title, n=14, max_chars=4000)
        if found is None or title_key(found.title) != title_key(title):
            return None
        st.uses["event_q"] = {"q": q, "year": year, "kind": kind, "turn": st.turn}
        text = " ".join(found.sentences)
        ans = evidence = None
        source = found.source
        if q.startswith("where") or "host" in q:
            mm = re.search(r"(?:took place|was held|were held|is taking place|is being held|held)(?: from [^.]*?)? in ([A-Z][\w'’. -]+?)"
                           r"(?: from| between| on|,|\.|;| after)", text)
            if mm:
                place = mm.group(1).strip()
                ans = f"The {title} was held in {place}." if not kind.endswith("olympics") else f"The {title} were held in {place}."
                evidence = next((s for s in found.sentences if place in s), None)
        elif q.startswith("when"):
            mm = re.search(r"\bfrom (\d{1,2} \w+(?: \d{4})? to \d{1,2} \w+ \d{4})", text)
            if mm:
                ans = f"The {title} ran from {mm.group(1)}."
                evidence = next((s for s in found.sentences if mm.group(1) in s), None)
        else:
            mm = re.search(r"([A-Z][\w'’ -]+?) won the (?:tournament|final|title|cup|competition|championship)", text)
            if mm:
                ans, evidence = f"{mm.group(1).strip()} won the {title}.", next((s for s in found.sentences if mm.group(0) in s), None)
            else:
                nxt_t = fmt.format(y=year + 4)
                nxt = self.about.find(nxt_t, n=14, max_chars=4000)
                if nxt is not None and title_key(nxt.title) == title_key(nxt_t):
                    nt = " ".join(nxt.sentences)
                    mm = re.search(r"([A-Z][\w'’ -]+?),? (?:are|were) the defending champions|([A-Z][\w'’ -]+?), the defending champions", nt)
                    if mm:
                        team = (mm.group(1) or mm.group(2)).strip()
                        team = re.sub(r"^(?:The|Hosts|Holders)\s+", "", team)
                        ans = f"{team} won the {title}."
                        evidence = next((s for s in nxt.sentences if team in s and "defending" in s), None)
                        source = nxt.source
        if ans is None:
            return Reply(msg, "unknown", self._pick(st, "daily:event_unknown", self.bank.daily["event_unknown"], x=title),
                         via="about", source=found.source)
        st.topic = {"title": found.title, "name": found.title, "turn": st.turn}
        st.last_fact = {"evidence": evidence or found.sentences[0], "source": source, "answer": ans, "question": msg,
                        "sure": True}
        self.bot.context.update({"answer": None, "atype": None, "mention": found.title, "kb_last": None})
        return Reply(msg, "answer", ans, evidence=evidence, source=source, via="about", confidence=0.9)

    def _officeholder(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """"Who is the president of France?" when the fact bank has no holder: the office's article
        names the incumbent — said with the date of my copy, because offices change."""
        m = _OFFICE_Q.match(norm)
        if not m or self.kgqa is None:
            return None
        office, place = m.group("o"), (m.group("x") or "").strip()
        if self.kgqa.answer(msg) is not None:
            return None                                   # the fact bank knows it: the normal path answers
        office = {"pm": "prime minister", "secretary general": "secretary-general"}.get(office, office)
        place = _OFFICE_ALIAS.get(place, place.title()) if place else ""
        if office in ("king", "queen", "monarch"):
            titles = [f"Monarchy of the {place}" if place in _THE_PLACES else f"Monarchy of {place}"] if place else []
        elif office == "pope":
            titles = ["Pope"]
        elif not place:
            return None
        else:
            o = "-".join(w.capitalize() for w in office.split("-")) if "-" in office else office.capitalize()
            o = o.replace("Prime minister", "Prime Minister").replace("First minister", "First Minister")
            titles = [f"{o} of the {place}", f"{o} of {place}"] if place in _THE_PLACES else [f"{o} of {place}", f"{o} of the {place}"]
        for title in titles:
            found = self.about.find(title, n=14, max_chars=5000)
            if found is None or title_key(found.title) != title_key(title):
                continue
            for s in found.sentences:
                hm = _HOLDER.search(s)
                if hm:
                    who = (hm.group("a") or hm.group("b")).strip()
                    role = office if not place or office == "pope" else f"{office} of {'the ' if place in _THE_PLACES else ''}{place}"
                    when = getattr(self, "reading_as_of", None)
                    st.last_fact = {"evidence": s, "source": found.source, "answer": who, "question": msg, "sure": False}
                    self.bot.context.update({"answer": who, "atype": "PERSON", "mention": who, "kb_last": None})
                    text = self._pick(st, "daily:office_dated" if when else "daily:office_undated",
                                      self.bank.daily["office_dated" if when else "office_undated"], x=role, y=who, z=when)
                    return Reply(msg, "answer", text, answer=who, evidence=s, source=found.source, via="about", confidence=0.6)
        if not place or office == "pope":
            return None
        # the office's article does not name the holder: the holder's own article does ("… is the 46th and current
        # president of the United States"); a strict sentence pattern, never a loose match
        pl = f"the {place}" if place in _THE_PLACES else place
        rx = re.compile(rf"\bis (?:an? [^.]*? who is )?the (?:\d+\w* (?:and )?)?(?:current|incumbent) {re.escape(office)} of {re.escape(pl)}\b|"
                        rf"\bhas served as (?:the )?(?:\d+\w* )?{re.escape(office)} of {re.escape(pl)} since\b", re.I)
        try:
            cands = self.bot.r.candidates(f"{office} of {pl}")
        except Exception:                                # a damaged index must not break the chat
            return None
        for sid in list(cands.ids)[:300]:
            s = self.bot.c.sentence_text(int(sid))
            if not rx.search(s) or re.search(r"\bvice\b|\bdeputy\b|\bformer\b", s, re.I):
                continue
            src = self.bot.c.source(int(sid))
            who = re.sub(r"\s*\([^)]*\)$", "", src.get("key") or "")
            if not who:
                continue
            role = f"{office} of {pl}"
            when = getattr(self, "reading_as_of", None)
            st.last_fact = {"evidence": s, "source": src, "answer": who, "question": msg, "sure": False}
            self.bot.context.update({"answer": who, "atype": "PERSON", "mention": who, "kb_last": None})
            text = self._pick(st, "daily:office_dated" if when else "daily:office_undated",
                              self.bank.daily["office_dated" if when else "office_undated"], x=role, y=who, z=when)
            return Reply(msg, "answer", text, answer=who, evidence=s, source=src, via="about", confidence=0.6)
        return None

    def _maker_in_title(self, st: DialogState, msg: str) -> Reply | None:
        """"Who composed the Four Seasons?" when the fact bank has no entry: the article is called "The Four Seasons
        (Vivaldi)", and the name in brackets is a person the fact bank knows — that person made it."""
        m = _MAKER_Q.match(normalise(msg).strip())
        if not m or self.kgqa is None or re.fullmatch(r"(?:it|this|that|them|these|those|one)", m.group("w")):
            return None
        work = m.group("w").strip()
        try:
            cands = self.bot.r.candidates(work)
        except Exception:                                # a damaged index must not break the chat
            return None
        want = {title_key(work), title_key("the " + work), title_key(re.sub(r"^the ", "", work))}
        for sid in list(cands.ids)[:200]:
            src = self.bot.c.source(int(sid))
            tm = re.fullmatch(r"(?P<t>.+?) \((?P<p>[^)]+)\)", src.get("key") or "")
            if not tm or title_key(tm.group("t")) not in want:
                continue
            try:
                hits = self.kgqa.kb.link(tm.group("p"), limit=1)
            except Exception:
                return None
            if not hits or (hits[0][0].type or "") not in _PERSON_TYPES or \
                    hits[0][0].title.split()[-1].lower() != tm.group("p").split()[-1].lower():
                continue                                  # "(film)", "(album)": no person
            who, shown = hits[0][0].title, tm.group("t")
            ev = self.bot.c.sentence_text(int(sid))
            st.last_fact = {"evidence": ev, "source": src, "answer": who, "question": msg, "sure": True}
            self.bot.context.update({"answer": who, "atype": "PERSON", "mention": shown, "kb_last": None})
            text = f"{shown[:1].upper() + shown[1:]} was {_MAKER_PP[m.group('v')]} by {who}."
            return Reply(msg, "answer", text, answer=who, evidence=ev, source=src, via="about", confidence=0.8)
        return None

    def _tenure(self, st: DialogState, msg: str) -> Reply | None:
        """"How long was George Washington president?": the opening of the person's article gives the years
        ("… served as the first president of the United States from 1789 to 1797")."""
        m = _TENURE_Q.match(msg.strip())
        if not m:
            return None
        who, office = m.group("e"), m.group("o").lower()
        found = self.about.find(who, n=6)
        if found is None or not found.sentences or title_key(found.title).split()[-1:] != title_key(who).split()[-1:]:
            return None
        role = r"(?:president|prime minister|chancellor|king|queen|emperor|pope|mayor|governor|ceo|leader|monarch|ruler)" \
            if office in ("in office", "in power", "on the throne") else re.escape(office)
        date = r"(?:(?:[A-Z][a-z]+ \d{1,2}, |\d{1,2} [A-Z][a-z]+ )?(\d{4}))"
        rx = re.compile(rf"\b{role}\b[^.;]{{0,90}}?\b(?:from|between) {date} (?:to|until|and|–|-) {date}", re.I)
        for s in found.sentences:
            hm = rx.search(s)
            if hm:
                a, b = int(hm.group(1)), int(hm.group(2))
                if not 0 < b - a < 80:
                    continue
                st.last_fact = {"evidence": s, "source": found.source, "answer": f"{a}–{b}", "question": msg, "sure": True}
                text = self._pick(st, "daily:tenure", self.bank.daily["tenure"], x=found.title, y=str(a), z=str(b),
                                  n=str(b - a))
                return Reply(msg, "answer", text, answer=f"{a}–{b}", evidence=s, source=found.source, via="about",
                             confidence=0.8)
        return None

    def _first_holder(self, st: DialogState, msg: str) -> Reply | None:
        """"Who was the first president of the United States?": many articles name that person in passing
        ("George Washington, the first president of the United States"); when at least two sentences agree on
        a name the fact bank knows as a person, that is the answer — a strict pattern, never a loose match."""
        m = _FIRST_Q.match(normalise(msg).strip())
        if not m or re.search(r"\b(?:lady|man|woman|person|people|thing|time|book|film|movie|song|day)\b", m.group("o")):
            return None
        office, place = m.group("o").strip(), m.group("x").strip()
        place = _OFFICE_ALIAS.get(place, place.title())
        pl = f"the {place}" if place in _THE_PLACES else place
        role = rf"(?<![\w-])(?i:first {re.escape(office)} of {re.escape(pl)}(?: of America)?)\b"
        name = r"(?P<n>[A-Z][\w.'-]+(?: (?:[A-Z][\w.'-]+|de|van|von|da|bin)){1,3})"
        rxs = (re.compile(rf"{name}, (?:[^,]{{0,60}} and )?(?:the )?{role}"),
               re.compile(rf"\bthe {role}, {name}"),
               re.compile(rf"\b{name}(?: \([^)]*\))? (?:was|became|served as) the {role}"))
        try:
            cands = self.bot.r.candidates(f"first {office} of {pl}")
        except Exception:                                # a damaged index must not break the chat
            return None
        votes: dict[str, list] = {}
        for sid in list(cands.ids)[:400]:
            s = self.bot.c.sentence_text(int(sid))
            if re.search(r"\b(?:vice|deputy)\b", s, re.I):
                continue
            for rx in rxs:
                hm = rx.search(s)
                if hm:
                    votes.setdefault(hm.group("n").rstrip(".,"), []).append(int(sid))   # "George Washington." at a sentence end
                    break
        if not votes:
            return None
        ranked = sorted(votes.items(), key=lambda kv: -len(kv[1]))
        who, sids = ranked[0]
        if len(sids) < 2 or (len(ranked) > 1 and len(ranked[1][1]) * 2 > len(sids)) or self._not_a_person(who):
            return None                                   # one passing mention, or two names disagree: no guess
        try:
            hits = self.kgqa.kb.link(who, limit=1) if self.kgqa is not None else []
        except Exception:
            hits = []
        if not hits or (hits[0][0].type or "") not in _PERSON_TYPES:
            return None
        who = hits[0][0].title if hits[0][0].title.lower().startswith(who.lower().split()[0]) else who
        ev = self.bot.c.sentence_text(sids[0])
        src = self.bot.c.source(sids[0])
        st.last_fact = {"evidence": ev, "source": src, "answer": who, "question": msg, "sure": True}
        self.bot.context.update({"answer": who, "atype": "PERSON", "mention": who, "kb_last": None})
        text = self._pick(st, "daily:first_holder", self.bank.daily["first_holder"], x=f"first {office} of {pl}", y=who)
        return Reply(msg, "answer", text, answer=who, evidence=ev, source=src, via="about", confidence=0.8)

    def _fix_typos(self, msg: str) -> str:
        """Typos in a statement ("interveiw", "recieve"): a lowercase word of five letters or more that the
        speller does not know, replaced by the known word it is closest to — never a name after "I'm",
        "called" or "my name is", and never a capitalised word."""
        toks = msg.split(" ")
        out = []
        for i, tok in enumerate(toks):
            m = re.fullmatch(r"([a-z]{5,})([.,!]*)", tok)
            prev = toks[i - 1].lower().strip(",.") if i else ""
            w = m.group(1) if m else ""
            stems = [w[:-3], w[:-3] + "e", w[:-4] if w[-4:-3] == w[-5:-4] else "", w[:-2], w[:-1], w[:-2] + "e" if w.endswith("ed") else "",
                     w[:-3] + "y" if w.endswith("ies") else "", w[:-2] if w.endswith("er") else "", w[:-3] if w.endswith("est") else "",
                     w[:-2] if w.endswith("ly") else ""] if re.search(r"(?:ing|ed|es|s|er|est|ly)$", w) else []
            inflected = any(len(x) >= 3 and self.speller.known(x) for x in stems if x)   # "snowing" is snow + ing, not "showing"
            if m and prev not in ("i'm", "im", "am", "called", "named", "is", "name", "call", "me") and not self.speller.known(m.group(1)) and not inflected:
                fixed = self.speller.fix_word(m.group(1))
                if fixed and fixed.lower() != m.group(1) and self.speller.known(fixed.lower()):
                    tok = fixed.lower() + m.group(2)
            out.append(tok)
        return " ".join(out)

    def _daily_ctx(self, st: DialogState, msg: str) -> Reply | None:
        """Everyday context a person keeps in mind: the title after "I got promoted", "I'll check it out"
        after a tip, a week being planned, "how should I prepare?" for what is coming up, a dish for
        someone whose taste you told me, and "what does Anna like?"."""
        d = self.bank.daily
        norm = normalise(msg).strip()
        la = st.last_action or {}
        same = normalise(st.last_message or "").strip(" ?!.") == norm.strip(" ?!.") and norm.strip(" ?!.")
        st.uses["same_run"] = (st.uses.get("same_run", 1) + 1) if same else 1
        if st.uses["same_run"] == 3 and re.fullmatch(r"(?:hi+|hey+|hello+|yo|hiya|sup|how (?:are|r) (?:you|u)(?: doing)?|how'?s it going|"
                                                     r"ok(?:ay)?|k+|hm+|lol|haha|yes|no|yeah|what|huh)", norm.strip(" ?!.")):
            # the third identical greeting or "ok" in a row: say so, like a person would (a third joke request is fine)
            return Reply(msg, "smalltalk", self._pick(st, "daily:same_again", d["same_again"]), via="smalltalk")
        evr = self._sounds(st, msg, norm) or self._daily_ctx23(st, msg, norm) or self._daily_ctx22(st, msg, norm) or self._daily_ctx21(st, msg, norm) or self._daily_ctx20(st, msg, norm) or self._daily_ctx19(st, msg, norm) or self._daily_ctx18(st, msg, norm) or self._event_q(st, msg, norm) or \
            self._officeholder(st, msg, norm)
        if evr is not None:
            return evr
        pr = st.uses.get("promo")
        if pr is not None and st.turn - pr <= 2:
            m = _TITLE.fullmatch(norm)
            if m and len(m.group("x").split()) <= 4 and not _REACTION.fullmatch(norm.strip(" .!")) and \
                    not _NOT_A_NAME.search(m.group("x")) and not re.search(r"\b(?:yes|yeah|no|nope|thanks|why|what|how|lol|haha)\b", norm):
                st.uses.pop("promo", None)
                return Reply(msg, "smalltalk", self._pick(st, "daily:promo_title", d["promo_title"], x=m.group("x")), via="empathy")
        if _CELEBRATE_PLAN.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:celebrate_plan", d["celebrate_plan"]), via="empathy")
        if _CHECK_OUT.match(norm) and ((la.get("kind") or "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3
                                       or re.search(r"\b(?:check|look|watch|read|play)\b", norm)):
            return Reply(msg, "smalltalk", self._pick(st, "daily:check_out", d["check_out"]), via="smalltalk")
        if re.fullmatch(r"(?:(?:ok|okay|thanks|thank you|alright|good idea|cool)[,!.]? )*(?:i'?ll|ill|i will|gonna|will|i'?m gonna|im gonna) "
                        r"(?:definitely |totally )?try (?:that|it|this|those|them|these)(?: out)?(?: tonight| later| then| now)?(?: thanks?)?[.!]*",
                        norm) and st.uses.get("last_via") == "everyday" and st.turn - st.uses.get("last_via_turn", -99) <= 1:
            night = re.search(r"\b(?:sleep|asleep|bed|clock|night|breathing)\b", st.last_reply or "")
            key = "tip_try_night" if night else "tip_try"
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="smalltalk")
        if _NO_WORRIES.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:no_worries_ack", d["no_worries_ack"]), via="smalltalk")
        if _RACING.match(norm):
            return Reply(msg, "empathy", self._pick(st, "daily:racing_mind", d["racing_mind"]), via="empathy")
        if _PLAN_WEEK.match(norm):
            st.uses["week"] = {"items": [], "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "daily:plan_week_start", d["plan_week_start"]), via="everyday")
        wk = st.uses.get("week")
        if wk and _WEEK_SHOW.match(norm):
            if wk["items"]:
                return Reply(msg, "smalltalk", self._week_text(st, wk, "plan_week_show"), via="everyday")
        if wk and st.turn - wk["turn"] <= 6 and "?" not in msg and _DAY_RX.search(norm):
            items = self._week_items(norm)
            if items:
                wk["items"].extend(items)
                wk["turn"] = st.turn
                self._learn(st, [msg], msg)
                return Reply(msg, "learned", self._week_text(st, wk, "plan_week_add"), via="memory")
        m = _PREPARE.match(norm)
        if m:
            topic = None
            said = " ".join(filter(None, [m.group("x"), m.group("y")]))
            pp = st.uses.get("prep")
            if said:
                topic = next((k for k, rx in _PREP_TOPICS if re.search(rx, said)), None)
            if topic is None and pp and st.turn - pp[1] <= 8:
                topic = pp[0]
            return Reply(msg, "smalltalk", self._pick(st, f"daily:prepare:{topic or 'none'}", d["prepare"][topic or "none"]),
                         via="everyday")
        pl = st.uses.get("person_likes")
        if _COOK_FOR.match(norm) and pl and st.turn - pl[1] <= 10:
            cuisine = next((c for c in d["cuisine_ideas"] if c in pl[0]), None)
            if cuisine:
                dishes = d["cuisine_ideas"][cuisine]
                pn = st.uses.get("person_noun")
                who = self._person_name(pn[0]) if pn else None
                who = who or (f"your {pn[0]}" if pn else "they")
                st.uses["dishes"] = [[x["name"] for x in dishes], st.turn]
                st.uses["food_ctx"] = st.turn
                lines = "\n".join("• " + x["name"] for x in dishes)
                return Reply(msg, "smalltalk", self._pick(st, "daily:cuisine_for", d["cuisine_for"], who=who,
                                                          x=f"{cuisine.capitalize()} food",
                                                          y=lines), via="everyday")
        ds = st.uses.get("dishes")
        if ds and st.turn - ds[1] <= 4:
            if _MAKE_THAT.match(norm):
                if len(ds[0]) == 1:
                    return self._dish_steps(st, msg, ds[0][0])
                st.uses["dishes"] = [ds[0], st.turn]
                names = ", ".join(n.lower() for n in ds[0][:-1]) + " or " + ds[0][-1].lower()
                return Reply(msg, "smalltalk", self._pick(st, "daily:dish_which", d["dish_which"], x="the " + names), via="everyday")
            pick = _ordinal_pick(norm, ds[0])
            if pick is None:
                pick = next((n for n in ds[0] if all(w in norm for w in n.lower().split()[-1:])), None)
            if pick is not None and len(norm.split()) <= 8:
                return self._dish_steps(st, msg, pick)
        m = _MAKE_DISH.match(norm)
        if m:
            x = m.group("x").strip()
            for dishes in d["cuisine_ideas"].values():
                for dish in dishes:
                    if dish["name"].lower() == x or dish["name"].lower().replace("homemade ", "") == x:
                        return self._dish_steps(st, msg, dish["name"])
        r2 = self._daily_ctx2(st, msg, norm) or self._daily_ctx3(st, msg, norm) or self._daily_ctx4(st, msg, norm) or \
            self._daily_ctx5(st, msg, norm) or self._daily_ctx6(st, msg, norm) or self._daily_ctx7(st, msg, norm) or \
            self._daily_ctx8(st, msg, norm) or self._daily_ctx9(st, msg, norm) or self._daily_ctx10(st, msg, norm) or \
            self._daily_ctx11(st, msg, norm) or self._daily_ctx12(st, msg, norm) or self._daily_ctx13(st, msg, norm) or \
            self._daily_ctx14(st, msg, norm) or self._daily_ctx15(st, msg, norm) or self._daily_ctx16(st, msg, norm) or \
            self._daily_ctx17(st, msg, norm)
        if r2 is not None:
            return r2
        m = _WHAT_LIKES.match(norm)
        if m:
            who = m.group("x")
            texts = list(self.bot.user_texts().values())
            noun = who[3:] if who.startswith("my ") else None
            if noun is None:
                for tx in texts:
                    cm = re.match(rf"^My ([a-z ]+?) is called {re.escape(who)}\.?$", tx, re.I)
                    if cm:
                        noun = cm.group(1).lower()
            if noun:
                for tx in reversed(texts):
                    lm = re.match(rf"^My {re.escape(noun)} (?:loves|likes|enjoys|adores|is into|is crazy about) (.+?)\.?$", tx, re.I)
                    if lm:
                        name = who if noun != who[3:] else f"your {noun}"
                        name = self._person_name(noun) or name
                        return Reply(msg, "answer", self._pick(st, "daily:person_likes_answer", d["person_likes_answer"],
                                                               x=name, y=_cuisine_case(lm.group(1))), via="facts")
        return None

    def _daily_ctx2(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 43: "same lol" after "how are you?", "that's sad" about ENGRAMM itself, why someone moved,
        where to live and what to eat in their city, a sick pet's symptoms, a tip on a bill, exam planning
        across turns, and loneliness when working from home."""
        d = self.bank.daily
        last = (st.last_reply or "")
        lv = st.uses.get("last_via")
        fc = st.uses.get("food_ctx")
        ll = getattr(st, "last_list", None) or {}
        food = (fc is not None and st.turn - fc <= 3) or (ll.get("kind") == "food" and st.turn - ll.get("turn", -99) <= 3)
        if lv == "everyday" and "•" in last and not food and re.fullmatch(r"(?:oh,? |ooh,? |hmm,? )?(?:that |those |these |they |it )?(?:all )?"
                                                            r"(?:sounds?|sound|look|looks) (?:really |so |pretty |very )?(?:nice|good|great|"
                                                            r"lovely|fun|cool|interesting|doable|like a plan)(?: actually| tbh)?[.!]*", norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:ideas_liked", d["ideas_liked"]), via="smalltalk")
        ex0 = st.uses.get("exams")
        m = re.fullmatch(r"(?:and |but |plus )?i (?:have|'ve got|got|have got) (?P<n>\d+|two|three|four|five|six) (?:exams?|tests?|finals)"
                         r"(?: (?:next week|this week|tomorrow|in a row|coming up|soon|on monday|on friday))?[.!]*", norm)
        if m:
            st.uses["exams"] = dict(ex0 or {"subjects": [], "worst": None}, turn=st.turn)
            return Reply(msg, "smalltalk", self._pick(st, "daily:exam_count", d["exam_count"], x=m.group("n")), via="empathy")
        asked = re.search(r"\bhow (?:are|r) (?:you|u)\b|\bhow'?s it going\b|\bhow are things\b|\bhow (?:you|u) doing\b|\bhru\b|"
                          r"\bhow'?s your day\b", normalise(expand_chat(st.last_message or "")))
        if _SAME_FINE.match(norm) and (re.search(r"\bhow are you\b|\bhow about you\b|\band you\b", last.lower()) or asked):
            return Reply(msg, "smalltalk", self._pick(st, "daily:same_fine", d["same_fine"]), via="smalltalk")
        li = st.uses.get("last_intent") or ["", -99]
        if _BOT_SAD.match(norm) and lv == "smalltalk" and li[1] == st.turn - 1 and li[0].startswith("bot_"):
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_not_sad", d["bot_not_sad"]), via="smalltalk")
        mv = st.uses.get("moved")
        m = _MOVED_REASON.match(norm)
        if m and mv and st.turn - mv[1] <= 2:
            r = m.group("r")
            key = "moved_work" if r in ("work", "job", "new job") else "moved_study" if r in (
                "uni", "university", "college", "school", "studies", "studying", "my studies") else "moved_other"
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=mv[0]), via="empathy")
        m = _AREAS_Q.match(norm)
        if m:
            place = (m.group("p") or m.group("q") or "").strip() or (mv[0] if mv else None) or self._place_ctx(st)
            if place:
                areas = d["areas"].get(place.lower())
                if areas:
                    return Reply(msg, "smalltalk", self._pick(st, "daily:areas_lead", d["areas_lead"], x=place.title(), y=areas),
                                 via="everyday")
        m = _BEST_FOOD.match(norm)
        if m:
            place = (m.group("p") or m.group("q") or "").strip() or self._place_ctx(st) or (mv[0] if mv else None)
            if place:
                rep = self._cuisine(st, msg, place.title() if place.islower() else place)
                if rep is not None:
                    return rep
        pt = st.uses.get("pet")
        if pt and st.turn - pt[1] <= 6 and re.fullmatch(r"(?:ok(?:ay)?,? |alright,? |yeah,? |good idea,? )?(?:i'?ll|ill|i will|gonna|i'?m gonna) "
                                                         r"(?:call|ring|phone|take (?:him|her|them) to|go to) (?:them|the vet|a vet|him|her)"
                                                         r"(?: now| today| then| tomorrow)?[.!]*", norm):
            name = st.uses.get("pet_name")
            who = name if isinstance(name, str) and name else f"your {pt[0]}"
            return Reply(msg, "smalltalk", self._pick(st, "daily:pet_call", d["pet_call"], x=who), via="empathy")
        if _THANKS_NICE.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:thanks_nice", d["thanks_nice"]), via="smalltalk")
        m = _TIP.match(norm)
        if m and re.search(r"\btip|\bgratuity", norm):
            amount = float((m.group("n") or m.group("m")).replace(",", "."))
            cur = "€" if re.search(r"€|euro", norm) else "£" if re.search(r"£|pound", norm) else "$"
            def fmt(v):
                return f"{cur}{v:,.2f}"
            text = self._pick(st, "daily:tip_calc", d["tip_calc"], x=fmt(amount), a=fmt(amount * .15), b=fmt(amount * .18),
                              c=fmt(amount * .20), y=fmt(amount * 1.18))
            return Reply(msg, "tool", text, via="tool", confidence=1.0)
        ex = st.uses.get("exams")
        if _EXAMS.search(norm) and not ex:
            st.uses["exams"] = ex = {"subjects": [], "worst": None, "turn": st.turn}
        if ex and st.turn - ex["turn"] <= 8:
            found = [s for s in _SUBJECTS if re.search(rf"\b{s}\b", norm)]
            if found and len(found) >= 2 and len(norm.split()) <= 12 and "?" not in msg:
                ex["subjects"] = found
                ex["turn"] = st.turn
                listing = ", ".join(found[:-1]) + " and " + found[-1]
                return Reply(msg, "smalltalk", self._pick(st, "daily:exam_subjects", d["exam_subjects"], x=listing), via="empathy")
            m = _WORST_AT.match(norm)
            if m:
                subj = (m.group("s") or m.group("t")).strip()
                ex["worst"], ex["turn"] = subj, st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:exam_worst", d["exam_worst"], x=subj), via="everyday")
            if _STUDY_FIRST.match(norm):
                ex["turn"] = st.turn
                if ex["worst"]:
                    return Reply(msg, "smalltalk", self._pick(st, "daily:exam_worst", d["exam_worst"], x=ex["worst"]), via="everyday")
                return Reply(msg, "smalltalk", self._pick(st, "daily:exam_first", d["exam_first"]), via="everyday")
        le = st.last_exp or {}
        lonely = le and st.turn - le.get("turn", -99) <= 4 and re.search(r"\blonel|\balone\b|\bisolat|\bno friends\b|\bdon'?t know anyone\b",
                                                                         le.get("text") or "")
        if lonely and _WFH.search(norm) and len(norm.split()) <= 12:
            st.last_exp = dict(le, turn=st.turn)
            return Reply(msg, "empathy", self._pick(st, "daily:wfh_lonely", d["wfh_lonely"]), via="empathy")
        m = _MAYBE_SHOULD.match(norm)
        if m:
            if lonely:
                st.last_exp = dict(le, turn=st.turn)
            return Reply(msg, "smalltalk", self._pick(st, "daily:maybe_should", d["maybe_should"]), via="empathy")
        if lonely and _IDEAS_Q.match(norm):
            st.last_exp = dict(le, turn=st.turn)
            return Reply(msg, "smalltalk", self._pick(st, "daily:lonely_ideas", d["lonely_ideas"]), via="everyday")
        cf = st.uses.get("common_first")
        if cf and st.turn - cf[1] <= 3 and re.fullmatch(r"(?:and |so )?who (?:was|did it|got there|made it) first\??|who was the first(?: one)?\??", norm):
            return Reply(msg, "answer", cf[0], answer=cf[0], source={"kind": "common", "source": "everyday facts", "key": ""},
                         confidence=1.0, via="common")
        cw = st.uses.get("common_when")
        if cw and st.turn - cw[1] <= 3 and _THEN_WHEN.match(norm):
            return Reply(msg, "answer", cw[0], answer=cw[0], source={"kind": "common", "source": "everyday facts", "key": ""},
                         confidence=1.0, via="common")
        return None

    def _place_ctx(self, st: DialogState) -> str | None:
        """The city the conversation is about: a place just talked about, else where the user lives."""
        pt = st.uses.get("place_topic")
        if isinstance(pt, list) and pt and st.turn - pt[1] <= 6:
            return pt[0]
        for f in self.bot.facts.facts:
            if f.subject == USER and "#home" in f.relation:
                return f.object
        return None

    def _daily_ctx3(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 45: an interview's company, its tricky questions and "wish me luck"; "and its population?"
        after a fact; the author of "the first one" in a book list; days until my birthday and my age; how
        long a dish takes; night shifts; feeling stupid after a betrayal; "should I text him?"."""
        d = self.bank.daily
        pp = st.uses.get("prep")
        interview = pp is not None and pp[0] == "interview" and st.turn - pp[1] <= 8
        if interview:
            m = _INTERVIEW_AT.match(norm)
            rm = re.fullmatch(r"(?:an? )?(?P<r>[a-z][a-z &/-]{1,30}?) (?:role|position|job|internship|post)", m.group("x").strip()) if m else None
            if rm:                                        # "it's for a marketing role": a role, not a company
                pp[1] = st.turn
                st.uses["interview_role"] = rm.group("r")
                return Reply(msg, "smalltalk", self._pick(st, "daily:interview_role", d["interview_role"], x=rm.group("r")),
                             via="empathy")
            if m:
                comp = " ".join(w[:1].upper() + w[1:] for w in m.group("x").split())
                st.uses["interview_at"] = comp
                pp[1] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:interview_at", d["interview_at"], x=comp), via="empathy")
            m = _WEAKNESS.match(norm)
            if m:
                key = "weakness" if m.group("x").startswith("weak") else "strength" if m.group("x").startswith("strength") else \
                    "salary" if m.group("x") == "salary" else "why"
                pp[1] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, f"daily:interview_q:{key}", d["interview_q"][key]), via="everyday")
            if re.fullmatch(r"(?:but |and |honestly,? )?(?:i'?m|im|i am|i feel|feeling) (?:so |really |a bit |kinda |super |pretty |very )?"
                            r"(?:nervous|anxious|scared|stressed|freaking out)(?: about it| about tomorrow)?[.!]*", norm):
                comp = st.uses.get("interview_at")
                pp[1] = st.turn
                return Reply(msg, "empathy", self._pick(st, "daily:interview_nerves", d["interview_nerves"], x=comp or "them"),
                             via="empathy")
            if _LUCK.match(norm) or norm in ("wish me luck", "wish me luck!"):
                comp = st.uses.get("interview_at")
                key = "interview_luck_at" if comp else "interview_luck"
                return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=comp or ""), via="smalltalk")
        if _LUCK.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:luck", d["luck"]), via="smalltalk")
        m = _ITS_PROP.match(norm)
        last = self.bot.context.get("kb_last")
        if m and last and last.get("names"):
            ent = last["names"][-1]
            prop = m.group("p")
            q2 = f"what is the {prop} of {ent}" if prop not in ("president", "prime minister", "leader", "head of state") else \
                f"who is the {prop} of {ent}"
            rep = self._kb_answer(st, q2)
            if rep is not None:
                rep.message, rep.resolved = msg, q2          # "how about New Zealand?" follows on from the full question
                return rep
        m = _LIST_FIRST.match(norm)
        ll = getattr(st, "last_list", None) or {}
        la = st.last_action or {}
        if m and (la.get("kind") or "").startswith("rec:") and st.turn - la.get("turn", -99) <= 4:
            lines = [ln for ln in (st.last_reply or "").split("\n") if ln.strip().startswith("•")]
            idx = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2, "last": -1}[m.group("o")]
            if lines and -len(lines) <= idx < len(lines):
                line = lines[idx]
                bm = re.match(r"^•\s*“(?P<t>[^”]+)”\s*by\s*(?P<a>[^(]+?)\s*\((?P<y>\d{4})\)", line.strip())
                if bm:
                    title, author, year = bm.group("t"), bm.group("a").strip(), bm.group("y")
                    st.topic = {"title": title, "name": title, "turn": st.turn}
                    self.bot.context.update({"answer": author, "atype": "PERSON", "mention": title, "kb_last": None})
                    if norm.startswith(("what year", "when")):
                        text = f"“{title}” came out in {year}."
                    else:
                        text = self._pick(st, "daily:list_author", d["list_author"], x=title, y=author, z=year)
                    return Reply(msg, "answer", text, answer=author, via="everyday", confidence=1.0)
        if _BDAY_DAYS.match(norm):
            bday = self._user_birthday()
            if bday is None:
                return Reply(msg, "unknown", self._pick(st, "daily:bday_unknown", d["bday_unknown"]), via="facts")
            import datetime as _dt
            now = self._now() or _dt.datetime.now()
            today = now.date() if hasattr(now, "date") else now
            target = _dt.date(today.year, bday[0], bday[1])
            if target < today:
                target = _dt.date(today.year + 1, bday[0], bday[1])
            n = (target - today).days
            shown = target.strftime("%A, ") + f"{target.day} " + target.strftime("%B %Y")
            key = "bday_is_today" if n == 0 else "bday_days"
            return Reply(msg, "tool", self._pick(st, f"daily:{key}", d[key], x=n, y=shown), via="tool", confidence=1.0)
        m = _AGE_IF.match(norm)
        if m:
            year = int(m.group("y") or m.group("z"))
            import datetime as _dt
            now = self._now() or _dt.datetime.now()
            today = now.date() if hasattr(now, "date") else now
            bday = self._user_birthday()
            if bday:
                nxt = _dt.date(today.year, bday[0], bday[1])
                had = nxt <= today
                age_now = today.year - year - (0 if had else 1)
                nxt_year = today.year + (1 if had else 0)
                text = self._pick(st, "daily:age_if", d["age_if"], x=age_now, y=nxt_year - year,
                                  z=_dt.date(nxt_year, bday[0], bday[1]).strftime("%-d %B %Y"))
            else:
                text = self._pick(st, "daily:age_if_nobday", d["age_if_nobday"], x=today.year - year - 1, y=today.year - year)
            return Reply(msg, "tool", text, via="tool", confidence=1.0)
        fc = st.uses.get("food_ctx")
        food = (fc is not None and st.turn - fc <= 3) or ((ll.get("kind") == "food") and st.turn - ll.get("turn", -99) <= 3) or \
            (la.get("kind") == "rec:food" and st.turn - la.get("turn", -99) <= 3)
        if food and _FOOD_TIME.match(norm):
            mins = re.findall(r"(?:in|about|under|takes?) (\w+(?:[–-]\w+)?) minutes", st.last_reply or "")
            if mins:
                return Reply(msg, "smalltalk", self._pick(st, "daily:food_time_known", d["food_time_known"], x=mins[0]), via="everyday")
            return Reply(msg, "smalltalk", self._pick(st, "daily:food_time", d["food_time"]), via="everyday")
        if _NIGHT_SHIFTS.match(norm):
            rep = self._learn(st, [msg], msg)
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg + " tired", "turn": st.turn}
            rep.text = self._pick(st, "daily:shifts_tough", d["shifts_tough"])
            return rep
        if _SHIFTS_Q.match(norm):
            told = [tx for tx in self.bot.user_texts().values() if re.search(r"\bshifts?\b|\bnights\b", tx, re.I)]
            if told:
                said = told[-1].strip().rstrip(".")
                said = re.sub(r"^(?:and |also |but )", "", said, flags=re.I)
                return Reply(msg, "answer", to_second_person(said[:1].upper() + said[1:]).rstrip(".") + ".", via="facts",
                             confidence=1.0)
        if _TRUST_BETRAYED.match(norm):
            le = st.last_exp or {}
            st.last_exp = dict(le, valence="negative", text=(le.get("text") or "") + " " + msg, turn=st.turn)
            return Reply(msg, "empathy", self._pick(st, "daily:trust_betrayed", d["trust_betrayed"]), via="empathy")
        if _TEXT_EX.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:text_ex", d["text_ex"]), via="empathy")
        return None

    def _user_birthday(self) -> tuple[int, int] | None:
        """(month, day) from what the user told ("My birthday is March 3."), else None."""
        months = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                              "september", "october", "november", "december"), 1)}
        for tx in reversed(list(self.bot.user_texts().values())):
            m = re.search(r"\bbirthday is (?:on )?(?:the )?(?:(?P<d1>\d{1,2})(?:st|nd|rd|th)? (?:of )?(?P<m1>[a-z]+)|(?P<m2>[a-z]+) (?P<d2>\d{1,2}))",
                          tx.lower())
            if m:
                mon = months.get(m.group("m1") or m.group("m2") or "")
                day = int(m.group("d1") or m.group("d2"))
                if mon and 1 <= day <= 31:
                    return mon, day
        return None

    def _daily_ctx4(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 46: low for a while ("i've been feeling really down lately") and what follows, sarcasm
        ("yeah sure, i love waking up at 6"), being told ENGRAMM didn't understand, asking for help, alarms,
        and "what else?" after the list of what ENGRAMM can do."""
        d = self.bank.daily
        m = _BEEN_FEELING.match(norm)
        if m:
            rep = self._turn(st, f"I feel {m.group('f')}.")   # the same care as "I feel down" — not a fact to keep
            rep.message = msg
            st.uses["low_for_a_while"] = st.turn
            return rep
        lw = st.uses.get("low_for_a_while")
        if lw is not None and st.turn - lw <= 4:
            if _DOWN_VAGUE.match(norm):
                st.uses["low_for_a_while"] = st.turn
                return Reply(msg, "empathy", self._pick(st, "daily:down_vague", d["down_vague"]), via="empathy")
            if _TALK_HELPS.match(norm):
                st.uses["low_for_a_while"] = st.turn
                return Reply(msg, "empathy", self._pick(st, "daily:talk_helps", d["talk_helps"]), via="empathy")
        if re.fullmatch(r"(?:lol |haha |ha |nah,? )?(?:not really|of course not|nope|obviously not|definitely not|no)(?: lol| haha)?[.!]*", norm) \
                and re.search(r"🙃|😄", st.last_reply or "") and st.uses.get("last_via") == "empathy":
            return Reply(msg, "smalltalk", self._pick(st, "daily:sarcasm_ack", d["sarcasm_ack"]), via="smalltalk")
        if _SARC_MONDAY.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:sarc_monday", d["sarc_monday"]), via="empathy")
        m = _SARCASM.match(norm)
        if m:
            return Reply(msg, "smalltalk", self._pick(st, "daily:sarcasm", d["sarcasm"], x=m.group("x")), via="empathy")
        if _WEEKEND_WISH.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:weekend_wish", d["weekend_wish"]), via="empathy")
        if _MISUNDERSTOOD.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:misunderstood", d["misunderstood"]), via="smalltalk")
        sp = st.uses.get("speech")
        if _HELP_ASK.match(norm) and not (sp is not None and st.turn - sp <= 3):   # "can you help me?" with a speech: the speech
            return Reply(msg, "smalltalk", self._pick(st, "daily:help_ask", d["help_ask"]), via="smalltalk")
        if _ALARM.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:alarm", d["alarm"]), via="device")
        li = st.uses.get("last_intent") or ["", -99]
        if _WHAT_ELSE.match(norm) and li[0] == "help" and st.turn - li[1] <= 2:
            return Reply(msg, "smalltalk", self._pick(st, "daily:what_else", d["what_else"]), via="smalltalk")
        return None

    def _daily_ctx5(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 47: a trip (how long, what to see, how expensive, visa, language), getting a cat (small flat,
        what you need, names) and how long learning a language takes."""
        d = self.bank.daily
        pt = st.uses.get("place_topic") or st.uses.get("trip")
        place = pt[0] if isinstance(pt, list) and st.turn - pt[1] <= 8 else None
        tp = st.topic or {}
        if tp.get("turn", -99) >= st.turn - 3 and (place is None or tp["turn"] > pt[1]) and \
                any(tp.get("name", "").lower() in cities for cities in d["cost_level"].values()):
            place, pt = tp["name"], [tp["name"], tp["turn"]]       # "is it expensive?" right after Oslo
        key = place.lower() if place else None
        if place:
            if _SEE_BARE.match(norm):
                rep = self._turn(st, f"what should i see in {key}?")
                rep.message = msg
                return rep
            m = _TRIP_DAYS.match(norm)
            if m and st.turn - pt[1] <= 2:
                n = m.group("n")
                return Reply(msg, "smalltalk", self._pick(st, "daily:trip_length", d["trip_length"], x=n, y=place), via="everyday")
            if _EXPENSIVE.match(norm):
                level = next((lv for lv, cities in d["cost_level"].items() if key in cities), None)
                if level:
                    return Reply(msg, "smalltalk", _fill(d["cost_says"][level], x=place), via="everyday")
            m = _VISA.match(norm)
            country = d["place_country"].get(key)
            if m and country:
                own = (m.group("n") or "") + " " + " ".join(f.object for f in self.bot.facts.facts if f.subject == USER and "#origin" in f.relation)
                if country in _EU and _EU_NATIONAL.search(own.lower()):
                    return Reply(msg, "smalltalk", self._pick(st, "daily:visa_eu", d["visa_eu"], x=country if key != country.lower() else place),
                                 via="everyday")
                return Reply(msg, "smalltalk", self._pick(st, "daily:visa_check", d["visa_check"]), via="everyday")
            if _LANG_THERE.match(norm) and country:
                rep = self._kb_answer(st, f"what language do they speak in {country}")
                if rep is not None:
                    rep.message = msg
                    return rep
        gp = st.uses.get("get_pet")
        m = _GET_PET.search(norm)
        if m:
            st.uses["get_pet"] = gp = [{"kitten": "cat", "puppy": "dog"}.get(m.group("p"), m.group("p")), st.turn]
        if gp and st.turn - gp[1] <= 6 and gp[0] == "cat":
            if _SMALL_FLAT.match(norm):
                gp[1] = st.turn
                rep = self._learn(st, [msg], msg)
                rep.text = self._pick(st, "daily:cat_small_flat", d["cat_small_flat"])
                return rep
            if _IS_OK.match(norm):
                gp[1] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:cat_ok", d["cat_ok"]), via="everyday")
            if _WHAT_NEED.match(norm):
                gp[1] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:cat_need", d["cat_need"]), via="everyday")
        if gp and st.turn - gp[1] <= 6 and _NAME_IT.match(norm):
            return Reply(msg, "smalltalk", d["pet_names"][gp[0]], via="everyday")
        lr = re.search(r"\b(?:learn|learning|study|studying) (?P<l>spanish|french|german|italian|english|japanese|chinese|portuguese|"
                       r"korean|russian|arabic|dutch)\b", normalise(st.last_message or ""))
        if lr and _LEARN_TIME.match(norm):
            text = self._pick(st, "daily:learn_time", d["learn_time"])
            if lr.group("l") in ("spanish", "italian", "portuguese", "dutch", "french"):
                text += f" {lr.group('l').capitalize()} is one of the easier languages for English and German speakers!"
            elif lr.group("l") in ("japanese", "chinese", "korean", "arabic"):
                text += f" {lr.group('l').capitalize()} takes longer, mostly because of the writing system, so be patient with yourself."
            return Reply(msg, "smalltalk", text, via="everyday")
        return None

    def _daily_ctx6(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 48: a headache across turns, spending on one thing and a budget rule, a colleague taking
        credit, a gift from what someone likes (and a budget), and choosing between two jobs."""
        d = self.bank.daily
        ac = st.uses.get("ache")
        if _ACHE.search(norm):
            st.uses["ache"] = ac = st.turn
            st.uses["sick"] = st.turn
        if ac is not None and st.turn - ac <= 5 and ac != st.turn:
            m = _SINCE.match(norm)
            if m:
                st.uses["ache"] = st.turn
                return Reply(msg, "empathy", self._pick(st, "daily:ache_since", d["ache_since"], x=m.group("x")), via="empathy")
            if _LOW_WATER.match(norm):
                st.uses["ache"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:ache_water", d["ache_water"]), via="everyday")
            if _MEDS.match(norm):
                st.uses["ache"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:ache_meds", d["ache_meds"]), via="everyday")
            if _WILL_REST.match(norm):
                return Reply(msg, "smalltalk", self._pick(st, "daily:ache_ok", d["ache_ok"]), via="empathy")
        m = _SPEND_ON.match(norm)
        if m:
            x = m.group("x").strip()
            key = next((k for k in d["spend_on"] if k != "other" and re.search(rf"\b{k}", x)), "other")
            rep = self._learn(st, [msg], msg)
            rep.text = d["spend_on"][key]
            st.uses["guide_offer"] = ["how can i save money", st.turn]
            return rep
        if _BUDGET_RULE.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:budget_rule", d["budget_rule"]), via="everyday")
        wc = st.uses.get("work_conflict")
        cm = _CREDIT.search(norm)
        if cm:
            st.uses["work_conflict"] = st.turn
            st.last_exp = {"valence": "negative", "topic": f"your {cm.group('n')}", "person": True, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:credit_stolen", d["credit_stolen"]), via="empathy")
        if wc is not None and st.turn - wc <= 5:
            for rx, key in ((_AGAIN, "credit_again"), (_TALK_BOSS, "talk_boss"), (_BRING_UP, "bring_up")):
                if rx.match(norm):
                    st.uses["work_conflict"] = st.turn
                    return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="empathy" if key == "credit_again" else "everyday")
        pl = st.uses.get("person_likes")
        if pl and st.turn - pl[1] <= 8:
            likes = [k for k in d["gift_like"] if re.search(rf"\b{k}", pl[0])]
            if likes and _GIFT_Q.match(norm):
                st.uses["gift_likes"] = [likes, st.turn]
                ideas = "; or ".join(d["gift_like"][k] for k in likes[:2])
                pn = (st.uses.get("person_noun") or [""])[0]
                who = "she likes" if pn in _FEMALE_NOUNS else "he likes" if pn in _MALE_NOUNS else "they like"
                return Reply(msg, "smalltalk", self._pick(st, "daily:gift_lead", d["gift_lead"], who=who, x=" and ".join(likes[:2]),
                                                          y=ideas), via="everyday")
        gl = st.uses.get("gift_likes")
        m = _UNDER.match(norm)
        if m and gl and st.turn - gl[1] <= 3:
            cheap = [d["gift_like"][k].split(" or ")[-1] for k in gl[0][:2]]
            return Reply(msg, "smalltalk", self._pick(st, "daily:gift_budget", d["gift_budget"], x=m.group("x"), y=" or ".join(cheap)),
                         via="everyday")
        dc = st.uses.get("decide")
        if _DECIDE.match(norm):
            st.uses["decide"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "daily:decide_ask", d["decide_ask"]), via="empathy")
        if dc is not None and st.turn - dc <= 4:
            if _TRADEOFF.match(norm) and re.search(r"\bpay|money|salary|interesting|fun|meaning|passion", norm):
                st.uses["decide"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:decide_tradeoff", d["decide_tradeoff"]), via="everyday")
            if _WOULD_YOU.match(norm):
                st.uses["decide"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:decide_view", d["decide_view"]), via="everyday")
            if re.fullmatch(r"(?:yeah,? |yes,? |hm+,? )?(?:i think so too|you'?re right|that'?s what i thought|i guess you'?re right|"
                            r"makes sense|i agree)[.!]*", norm):
                return Reply(msg, "smalltalk", self._pick(st, "daily:decide_agree", d["decide_agree"]), via="smalltalk")
        return None

    def _daily_ctx7(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 49: starting to run (how often, how far, shoes), a child nervous before a test, guests for
        dinner (how many, a vegan guest, menu, dessert), and adding to or ticking off reminders."""
        d = self.bank.daily
        if _RUN_START.match(norm):
            st.uses["run"] = st.turn
            rep = self._learn(st, [msg], msg)
            rep.text = self._pick(st, "daily:run_start", d["run_start"])
            return rep
        rn = st.uses.get("run")
        if rn is not None and st.turn - rn <= 6:
            for rx, key in ((_NEVER_SPORT, "run_beginner"), (_RUN_OFTEN, "run_often"), (_RUN_FAR, "run_far"), (_RUN_SHOES, "run_shoes")):
                if rx.match(norm):
                    st.uses["run"] = st.turn
                    return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="everyday")
            if re.fullmatch(r"(?:cool,? |ok(?:ay)?,? |great,? |thanks,? )*(?:i'?ll|ill|i will|gonna) (?:start|begin|go)(?: running)? (?:tomorrow|today|"
                            r"on monday|this week|tonight)[.!]*", norm):
                return Reply(msg, "smalltalk", self._pick(st, "daily:run_go", d["run_go"]), via="smalltalk")
        if _KID.search(norm):
            st.uses["kid"] = st.turn
        kd = st.uses.get("kid")
        if kd is not None and st.turn - kd <= 5 and kd != st.turn:
            if _KID_NERVOUS.match(norm):
                st.uses["kid"] = st.turn
                return Reply(msg, "empathy", self._pick(st, "daily:kid_nervous", d["kid_nervous"]), via="empathy")
            if _KID_HELP.match(norm):
                st.uses["kid"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:kid_help", d["kid_help"]), via="everyday")
            m = _KID_AGE.match(norm)
            if m and 3 <= int(m.group("n")) <= 18:
                st.uses["kid"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:kid_age", d["kid_age"], x=m.group("n")), via="everyday")
        gs = st.uses.get("guests")
        if _GUESTS.search(norm):
            st.uses["guests"] = gs = {"n": None, "diet": None, "turn": st.turn}
            rep = self._learn(st, [msg], msg)
            rep.text = self._pick(st, "daily:guests_ack", d["guests_ack"])
            return rep
        if gs and st.turn - gs["turn"] <= 6:
            m = _GUEST_N.match(norm)
            if m:
                gs.update(n=m.group("n"), turn=st.turn)
                return Reply(msg, "smalltalk", self._pick(st, "daily:guests_count", d["guests_count"], x=m.group("n")), via="everyday")
            m = _ONE_VEGAN.match(norm)
            if m:
                gs.update(diet=m.group("d"), turn=st.turn)
                return Reply(msg, "smalltalk", self._pick(st, "daily:guests_vegan", d["guests_vegan"]), via="everyday")
            if _COOK_FOR.match(norm) or re.fullmatch(r"(?:so |ok )?what (?:should|could|can) (?:i|we) (?:cook|make|serve)(?: for (?:them|everyone|the guests))?\??|"
                                                     r"(?:yes|yeah|sure)(?: please)?[.!]*", norm):
                gs["turn"] = st.turn
                st.uses["guests_menu"] = st.turn
                key = "guests_menu_vegan" if gs["diet"] in ("vegan", "vegetarian") else "guests_menu"
                return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=gs["n"] or "everyone"), via="everyday")
            gm = st.uses.get("guests_menu")
            if gm is not None and st.turn - gm <= 3 and _FOOD_TIME.match(norm):
                return Reply(msg, "smalltalk", self._pick(st, "daily:guests_time", d["guests_time"]), via="everyday")
            if _DESSERT.match(norm):
                key = "dessert_vegan" if gs["diet"] == "vegan" else "dessert_guests"
                return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="everyday")
        la = st.last_action or {}
        if (st.last_reply or "").find("what do I need to do") >= 0 or (st.uses.get("last_via") == "memory" and "noted it" in (st.last_reply or "")):
            m = _TODO_MORE.match(norm)
            if m:
                what = m.group("x").strip(" .!")
                self._learn(st, [f"I need to {what}."], msg)
                return Reply(msg, "learned", self._pick(st, "daily:todo_added", d["todo_added"], x=re.sub(r"\bmy\b", "your", what)),
                             via="memory")
        m = _DID_IT.match(norm)
        if m:
            base = _PAST_BASE[m.group("v")]
            obj = m.group("o").strip()
            todos = {sid: tx for sid, tx in self.bot.user_texts().items() if re.match(r"^I need to\s+", tx)}
            hit = None
            for sid, tx in todos.items():
                task = re.sub(r"^I need to\s+", "", tx).rstrip(".").lower()
                if task.startswith(base + " ") or task == base:
                    rest = task[len(base):].strip()
                    if not obj or obj in ("her", "him", "them", "it", "that", "this") or obj in rest or rest.startswith(obj.split()[0]):
                        hit = (sid, task)
                        break
            if hit:
                self.bot.memory.forget(hit[0])
                self.bot.refresh()
                left = [tx for tx in self.bot.user_texts().values() if re.match(r"^I need to\s+", tx)]
                key = "todo_done" if left else "todo_done_all"
                return Reply(msg, "memory", self._pick(st, f"daily:{key}", d[key], x=re.sub(r"\bmy\b", "your", hit[1])), via="memory")
        return None

    def _daily_ctx8(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 50: the rhythm of a real chat — a long week, deadlines, "tomorrow is Friday", ENGRAMM's own
        weekend, and a hike (tips, what to bring, how much water)."""
        d = self.bank.daily
        if re.fullmatch(r"(?:can|could|shall) we (?:talk|speak|chat|write) (?:in |auf )?(?:german|deutsch)(?: please| bitte)?\??|"
                        r"(?:please )?(?:speak|talk) (?:german|deutsch)(?: please| bitte)?", norm):
            st.lang = "de"
            return Reply(msg, "smalltalk", self._pick(st, "daily:lang_de", d["lang_de"]), via="german")
        if re.fullmatch(r"\d{3,}", norm.strip()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:numbers_only", d["numbers_only"], x=norm.strip()), via="smalltalk")
        if len(norm.split()) >= 25 and len(re.findall(r"\b(?:missed|late|spilled|rain(?:ing)?|bad mood|downhill|broke|broken|lost|forgot|failed|"
                                                     r"didn'?t go off|stuck|crashed|yelled|argued|cancelled|ruined|terrible|awful|worst)\b", norm)) >= 2:
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:bad_day_story", d["bad_day_story"]), via="empathy")
        if re.fullmatch(r"(?:and |so )?what do i do for (?:a living|work|my job)\??", norm) or \
                (re.fullmatch(r"(?:and |so )?what do i do(?: again)?\??", norm) and st.uses.get("last_via") == "facts"
                 and st.uses.get("last_via_turn") == st.turn - 1):
            rep = self._turn(st, "what's my job?")       # "what's my name again? — and what do I do?": the job
            rep.message = msg
            return rep
        if _LONG_WEEK.match(norm):
            st.uses["long_week"] = st.turn
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg + " tired", "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:long_week", d["long_week"]), via="empathy")
        lw = st.uses.get("long_week")
        if lw is not None and st.turn - lw <= 3 and _DEADLINES.match(norm):
            st.uses["long_week"] = st.turn
            return Reply(msg, "empathy", self._pick(st, "daily:deadlines", d["deadlines"]), via="empathy")
        if _ALMOST_WE.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:almost_weekend", d["almost_weekend"]), via="smalltalk")
        if _BOT_WEEKEND.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_weekend", d["bot_weekend"]), via="smalltalk")
        if _HIKE_PLAN.match(norm):
            st.uses["hike"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "daily:hike_plan", d["hike_plan"]), via="empathy")
        hk = st.uses.get("hike")
        if _HIKE_TIPS.match(norm) or (hk is not None and st.turn - hk <= 4 and re.fullmatch(r"(?:any )?(?:good )?tips\??", norm)):
            st.uses["hike"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "daily:hike_tips", d["hike_tips"]), via="everyday")
        if hk is not None and st.turn - hk <= 4:
            if _BRING.match(norm):
                st.uses["hike"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:hike_bring", d["hike_bring"]), via="everyday")
            if _HOW_WATER.match(norm):
                return Reply(msg, "smalltalk", self._pick(st, "daily:hike_water", d["hike_water"]), via="everyday")
        return None

    def _daily_ctx9(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 53: what a word means (a small checked list, honest otherwise), an example sentence, opposites,
        calories and whether that is a lot, rice versus pasta, protein, time zones and differences."""
        d = self.bank.daily
        m = _DEFINE.match(norm)
        if m:
            w = (m.group("w") or m.group("v")).lower()
            entry = d["word_defs"].get(w)
            if entry:
                st.uses["word_def"] = [w, st.turn]
                return Reply(msg, "answer", self._pick(st, "daily:word_def", d["word_def"], x=w, y=entry[0], z=entry[1]), via="tool",
                             confidence=1.0)
            if self.about.find(w) is None and self.about.find(w.title()) is None:
                return Reply(msg, "unknown", self._pick(st, "daily:word_def_none", d["word_def_none"], x=w), via="tool")
        wd = st.uses.get("word_def")
        if wd and st.turn - wd[1] <= 3 and _IN_SENTENCE.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:word_sentence", d["word_sentence"], x=d["word_defs"][wd[0]][1]), via="tool")
        m = _ANTONYM.match(norm)
        if m:
            w = (m.group("w") or m.group("v")).lower()
            ants = d["antonyms"].get(w) or next((k for k, v in d["antonyms"].items() if w in v), None)
            if isinstance(ants, str):
                ants = [ants]
            if ants:
                more = f" (or “{'”, “'.join(ants[1:])}”)" if len(ants) > 1 else ""
                return Reply(msg, "answer", self._pick(st, "daily:antonym_say", d["antonym_say"], x=w, y=ants[0], z=more), via="tool",
                             confidence=1.0)
        m = _KCAL.match(norm)
        if m:
            f = re.sub(r"s$", "", m.group("f").strip()) if m.group("f").strip() not in d["food_kcal"] else m.group("f").strip()
            hit = d["food_kcal"].get(f) or d["food_kcal"].get(m.group("f").strip())
            if hit:
                st.uses["kcal"] = [int(hit[0]), st.turn]
                return Reply(msg, "answer", self._pick(st, "daily:kcal_say", d["kcal_say"], x=hit[0], y=hit[1]), via="tool", confidence=1.0)
        kc = st.uses.get("kcal")
        if kc and st.turn - kc[1] <= 2 and _KCAL_LOT.match(norm):
            key = "kcal_lot" if kc[0] < 300 else "kcal_mid"
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=kc[0], p=round(kc[0] / 22.5)), via="tool")
        if _RICE_PASTA.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:rice_pasta", d["rice_pasta"]), via="everyday")
        if _PROTEIN.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:protein_need", d["protein_need"]), via="everyday")
        from engramm.chat.worldtime import time_in, utc_label, utc_offset
        now = self._now()
        utc = None
        if now is not None:
            import datetime as _dt
            utc = (now if now.tzinfo else now.astimezone()).astimezone(_dt.timezone.utc)
        m = _TZ.match(norm)
        if m:
            off = utc_offset(m.group("p") or m.group("q"), utc)
            if off:
                st.uses["tz"] = [[m.group("p") or m.group("q")], st.turn]
                z = " (summer time)" if off[2] else ""
                return Reply(msg, "answer", self._pick(st, "daily:tz_say", d["tz_say"], x=off[0], y=utc_label(off[1]), z=z), via="tool",
                             confidence=1.0)
        tz = st.uses.get("tz")
        if tz and st.turn - tz[1] <= 3:
            if _TIME_THERE.match(norm):
                rep = self._turn(st, f"what time is it in {tz[0][-1]}?")
                rep.message = msg
                st.uses["tz"] = [tz[0], st.turn]
                return rep
            m = _TIME_AND.match(norm)
            if m and utc_offset(m.group("p"), utc):
                rep = self._turn(st, f"what time is it in {m.group('p')}?")
                rep.message = msg
                st.uses["tz"] = [tz[0] + [m.group("p")], st.turn]
                return rep
            seen = re.findall(r"\bin ((?:the )?[A-Z][\w'.-]*(?: [A-Z][\w'.-]*)*)(?= right now| —| \(| is on)", " ".join(st.recent[-4:]))
            places = []
            for x in seen + tz[0]:
                if utc_offset(x, utc) and x.lower() not in [y.lower() for y in places]:
                    places.append(x)
            seen_order = [x for x in seen if utc_offset(x, utc)]
            if seen_order:                                # the order the places came up in
                places = list(dict.fromkeys([y for y in tz[0] if y.lower() not in [s.lower() for s in seen_order]] + seen_order))
            if _HOURS_AHEAD.match(norm) and len(places) >= 2:
                a, b = utc_offset(places[-1], utc), utc_offset(places[-2], utc)
                n = a[1] - b[1]
                shown = f"{abs(n):g}"
                key = "tz_ahead" if n > 0 else "tz_behind" if n < 0 else "tz_same"
                return Reply(msg, "answer", self._pick(st, f"daily:{key}", d[key], a=a[0], b=b[0], n=shown), via="tool", confidence=1.0)
        return None

    def _daily_ctx10(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 54: good news about others (an engagement, a baby, a driving test) and what follows, a fight
        with a friend (what she said, how to apologise), and parents divorcing."""
        d = self.bank.daily
        if re.search(r"\b(?:got engaged|is engaged|are engaged|getting married)\b", norm):
            st.uses["engaged"] = st.turn
        en = st.uses.get("engaged")
        if en is not None and st.turn - en <= 5 and en != st.turn:
            m = _YEARS_TOGETHER.match(norm)
            if m:
                st.uses["engaged"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:engaged_years", d["engaged_years"], x=m.group("n")), via="empathy")
            if _WEDDING_WHEN.match(norm):
                st.uses["engaged"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:wedding_when", d["wedding_when"]), via="empathy")
        hw = st.uses.get("wedding")
        if hw is not None and st.turn - hw <= 4 and _HONOUR_WHAT.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:honour_duties", d["honour_duties"]), via="everyday")
        if _BABY.search(norm):
            st.uses["baby"] = st.turn
        bb = st.uses.get("baby")
        if bb is not None and st.turn - bb <= 4 and bb != st.turn:
            if _BABY_SEX.match(norm):
                st.uses["baby"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:baby_girl", d["baby_girl"]).replace("girl", _BABY_SEX.match(norm).group("s"))
                             .replace("🎀", "💙" if _BABY_SEX.match(norm).group("s") == "boy" else "🎀"), via="empathy")
            if _GIFT_Q.match(norm):
                return Reply(msg, "smalltalk", self._pick(st, "daily:baby_gift", d["baby_gift"]), via="everyday")
        if _PASSED.search(norm):
            st.uses["passed"] = st.turn
        ps = st.uses.get("passed")
        if ps is not None and st.turn - ps <= 4 and ps != st.turn:
            if _FIRST_TRY.match(norm):
                st.uses["passed"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:first_try", d["first_try"]), via="empathy")
            if _NEED_CAR.match(norm):
                st.uses["passed"] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:need_car", d["need_car"]), via="smalltalk")
        if _FIRST_CAR.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:first_car", d["first_car"]), via="everyday")
        if _FIGHT.search(norm):
            st.uses["fight"] = st.turn
        fg = st.uses.get("fight")
        if fg is not None and st.turn - fg <= 5 and fg != st.turn:
            for rx, key in ((_SHE_SAID, "friend_said"), (_MAYBE_RIGHT, "maybe_right"), (_APOLOGIZE, "apologize"), (_CALL_THEM, "call_friend")):
                if rx.match(norm):
                    st.uses["fight"] = st.turn
                    return Reply(msg, "empathy" if key != "apologize" else "smalltalk", self._pick(st, f"daily:{key}", d[key]),
                                 via="empathy" if key != "apologize" else "everyday")
        if _DIVORCE.search(norm):
            st.uses["divorce"] = st.turn
            st.last_exp = {"valence": "negative", "topic": "your parents", "person": True, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:divorce_parents", d["divorce_parents"]), via="empathy")
        dv = st.uses.get("divorce")
        if dv is not None and st.turn - dv <= 4:
            if _NOT_KID.match(norm):
                st.uses["divorce"] = st.turn
                return Reply(msg, "empathy", self._pick(st, "daily:not_a_kid", d["not_a_kid"]), via="empathy")
            if _STILL_HURTS.match(norm):
                st.uses["divorce"] = st.turn
                return Reply(msg, "empathy", self._pick(st, "daily:still_hurts", d["still_hurts"]), via="empathy")
        return None

    def _work_entity(self, x: str, kind: str | None, strict: bool = False) -> tuple[str, str] | None:
        """(title, kind) of a film, book or artist the user named, from the fact bank's links or an article title."""
        x = x.strip(" .!?")
        x = _WORK_ALIAS.get(x.lower(), x)
        kinds = [kind] if kind else ["film", "book", "music"]
        if self.kgqa is not None:
            try:
                links = self.kgqa.kb.link(x, limit=8)
            except Exception:
                links = []
            for k in kinds:
                for ent, _rank in links:
                    if (ent.type or "") in _WORK_TYPES[k]:
                        return ent.title, k
        for k in kinds:
            for cand in (f"{x.title()} (film)", f"{x.title()} (novel)") if k != "music" else ():
                f = self.about.find(cand)
                if f is not None and "(" in f.title:
                    return f.title, k
        if strict:
            return None                                   # "i love cooking": a hobby, not a work, unless it is clearly one
        f = self.about.find(x.title() if x.islower() else x)
        if f is not None and f.title.lower().replace("the ", "").startswith(x.lower().replace("the ", "")[:6]):
            return f.title, kind or "film"
        return None

    def _work_maker(self, title: str) -> tuple[str, dict] | None:
        """Who wrote or directed a work, from its article's own "written by …" / "directed by …"."""
        f = self.about.find(title)
        if f is None:
            return None
        m = re.search(r"\b(?:directed|written|co-written, directed,? and produced|written and directed|composed|painted)(?:,? and produced)? by "
                      r"(?:the [A-Z]?[a-z]+ (?:writer|author|director|novelist|filmmaker) )?"
                      r"(?P<w>[A-Z][a-zà-ÿ'-]+(?: (?:[A-Z]\.|[A-Z][a-zà-ÿ'-]+)){1,3})", " ".join(f.sentences))
        return (m.group("w"), f.source) if m else None

    def _sounds(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 59: sounds and test messages a person types — "aaaaa", "hhhh", "abc", "omg", "smh" — get a
        human reaction, never "Oh? Go on." or "I see. Tell me more?"."""
        n = norm.strip(" .!?")
        if re.fullmatch(r"(?:and |so )?what do i do(?: for (?:a living|work))?(?: again)?", n) and \
                any("#job" in f.relation and f.subject == USER for f in self.bot.facts.facts):
            return self._question(st, "what is my job?")   # "what do i do?" is about my job, not sights in Munich
        key = None
        if re.fullmatch(r"a{3,}h*|a+h{2,}|a+r+g+h*|ahh+", n):
            key = "scream"
        elif re.fullmatch(r"h{3,}|u+f+|p+h+e+w+|s+i+g+h+", n):
            key = "sigh"
        elif re.fullmatch(r"(?:abc|abcd|xyz|test|testing|test test|test 123|123|1 2 3|ping|hello\?+|is this working|are you there|"
                          r"anyone there|you there)", n):
            key = "test"
        elif re.fullmatch(r"o+m+g+|oh my god|oh my gosh|omfg", n):
            key = "omg"
        elif re.fullmatch(r"smh|ffs|bruh+|ugh+|meh+", n):
            key = "meh" if n.startswith("meh") else "smh"
        elif re.fullmatch(r"z{3,}", n):
            key = "sleepy"
        if key is None:
            toks = re.findall(r"[a-z']+", n)
            known = self.speller.known if self.speller is not None else None
            odd = [t for t in toks if strict_mash(t, known)]
            if odd and 2 <= len(toks) <= 7 and not re.match(r"(?:my name is|my name'?s|call me|i'?m called|i am called|name'?s)\b", n):
                # "i like dhdhd", "what is dhdhd?": a keyboard slip in a sentence — ask, never learn or look it up
                mw = st.uses.get("mash_word")
                cnt = mw[1] + 1 if mw and mw[0] == odd[0] else 1
                st.uses["mash_word"] = [odd[0], cnt]
                key = "word" if cnt <= 2 else "word_insist"     # asked twice already: no third "typo?"
                return Reply(msg, "smalltalk", self._pick(st, f"daily:sound:{key}", self.bank.daily["sounds"][key], x=odd[0]),
                             via="clarify")
            gs = st.uses.get("gib_turn")
            if gs is not None and st.turn - gs <= 2 and re.search(
                    r"\b(?:sorry|oops|whoops|my bad)\b|\b(?:my )?(?:cat|dog|kid|son|daughter|baby|toddler)\b.*\b(?:keyboard|phone|typed|walked|sat)\b|"
                    r"\b(?:wrong (?:chat|window|button|tab)|pocket|butt ?dial|typo|fat fingers?)\b", n):
                st.uses.pop("gib_turn", None)
                return Reply(msg, "smalltalk", self._pick(st, "daily:sound:gib_sorry", self.bank.daily["sounds"]["gib_sorry"]), via="smalltalk")
            return None
        return Reply(msg, "smalltalk", self._pick(st, f"daily:sound:{key}", self.bank.daily["sounds"][key]), via="smalltalk")

    def _age_built(self, st: DialogState, name: str) -> tuple[str, int, int] | None:
        """"How old is the Eiffel Tower?": the year it was completed, and its age now."""
        rep = self._question(st, f"when was {name} built?")
        m = re.search(r"\b(1\d{3}|20\d\d)\b", (rep.text or "") if rep.kind == "answer" else "")
        now = self._now()
        year_now = now.year if now else __import__("datetime").date.today().year
        if not m or int(m.group(1)) > year_now:
            return None
        subject = re.match(r"(.+?) was (?:completed|built|finished|opened|constructed)", rep.text or "")
        return (subject.group(1) if subject else name), year_now - int(m.group(1)), int(m.group(1))

    def _daily_ctx23(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 86: learning to code as a short flow — which language, "is it hard?", "how long does it take?",
        "where should I start?" and "wish me luck" all stay on the topic instead of becoming look-ups."""
        b = self.bank.daily["b86"]
        n = re.sub(r"\s+", " ", norm).strip(" .!?")
        langs = r"python|javascript|js|java|c\+\+|c#|rust|go|golang|swift|kotlin|html(?: and css)?|ruby|php"
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"daily:b86:{key}", b[key], **kw), via="everyday")  # noqa: E731

        def lang_key(x: str) -> str:
            x = x.lower()
            return {"js": "javascript", "golang": "go", "html and css": "html"}.get(x, x)

        def lang_name(k: str) -> str:
            return {"javascript": "JavaScript", "c++": "C++", "c#": "C#", "html": "HTML", "php": "PHP"}.get(k, k.capitalize())

        m = re.fullmatch(rf"(?:so |well |actually |btw )?(?:i'?m|i am|im) (?:thinking (?:about|of)|planning (?:to|on)|going to|gonna|about to|trying to) "
                         rf"(?:learn(?:ing)?|start(?:ing)?(?: to learn(?:ing)?)?) (?:how )?(?:to code|coding|to program|programming|(?P<l>{langs}))"
                         rf"|(?:i )?(?:want|wanna|would like|'d like) to (?:learn|start) (?:how )?(?:to code|coding|to program|programming|(?P<l2>{langs}))"
                         rf"|(?:i'?m|i am|im|i just) (?:learning|started learning|starting to learn|started) (?:how )?(?:to code|coding|to program|programming|(?P<l3>{langs}))", n)
        if m:
            lang = m.group("l") or m.group("l2") or m.group("l3")
            st.uses["code86"] = [lang_key(lang) if lang else None, st.turn]
            if lang:
                k = lang_key(lang)
                return say("start_lang", x=lang_name(k), y=b["lang"][k])
            return say("start_ask")
        nk = re.fullmatch(r"(?:actually,? |well,? |technically,? )?(?:it'?s|my (?:full |real |actual )?name is|i'?m) (?P<full>[a-z]{2,20}),? but (?:everyone|everybody|people|"
                          r"my friends|most people|all my friends) (?:calls?|call) me (?P<nick>[a-z]{2,20})", n)
        if nk:                                            # "it's thomas, but everyone calls me tom": both, and the nickname is used
            full, nick = nk.group("full").capitalize(), nk.group("nick").capitalize()
            r = self._learn(st, [f"My name is {nick}."], msg)
            r.text = self._pick(st, "daily:b86:nickname", b["nickname"], x=full, y=nick)
            return r
        if re.fullmatch(r"(?:(?:ok(?:ay)?|thanks?|thank you|thx|ty)[,!. ]+)?(?:i (?:do )?feel|i'?m feeling|feeling) (?:a (?:bit|little|lot)|much|so much|way|kind of|already) better(?: now)?"
                        r"(?:[,!. ]+(?:thanks?|thank you|thx))?|(?:that|this|talking) (?:helped|helps)(?: a (?:bit|lot|little))?(?:,? thanks?| thank you)?", n):
            st.last_exp = None                            # "thanks, i feel a bit better": glad — never "That makes it even harder"
            st.uses.pop("drive86", None)
            return say("better")
        if re.search(r"\b(?:i )?(?:failed|didn'?t pass|did not pass|flunked|messed up) (?:my |the )?(?:driving|driver'?s) (?:test|exam|license test|licence test)\b", n):
            st.uses["drive86"] = [st.turn]                # the reply itself comes from the moments table; the follow-ups need the context
            return None
        if re.fullmatch(r"(?:and |plus |also )?(?:my |the )?neighbou?rs? (?:were|was|kept|have been|has been) (?:being )?(?:so |really |super |very |extremely )?"
                        r"(?:loud|noisy|partying|playing music|blasting music|yelling|shouting|arguing|fighting|drilling)(?: again)?(?: (?:all night|until \d{1,2}(?: ?am)?|till \d{1,2}(?: ?am)?|"
                        r"last night|at night|the whole night))*", n):
            st.uses["neigh86"] = [st.turn]
            st.last_exp = {"valence": "negative", "topic": "people", "person": True, "text": msg, "turn": st.turn}
            return say("neigh_loud")
        ng = st.uses.get("neigh86")
        if ng and st.turn - ng[-1] <= 4:
            if re.fullmatch(r"(?:so |but |and )?(?:should i|do you think i should|would you) (?:say something|talk to them|tell them|complain|knock|"
                            r"say something to them|speak to them|leave (?:them )?a note|call the police|tell the landlord)(?: to them| about it)?", n):
                ng.append(st.turn)
                return say("neigh_advice")
            if re.fullmatch(r"(?:yeah,? |ok(?:ay)?,? |yes,? )?(?:maybe |probably |i'?ll do it |i will )?(?:tomorrow|later|when i'?m calmer|in the morning)(?: maybe)?|"
                            r"(?:yeah,? |ok(?:ay)?,? )?i'?ll (?:talk to them|say something|do that)(?: tomorrow| later)?", n):
                st.uses.pop("neigh86", None)
                return say("neigh_plan")
        lr = st.last_reply or ""
        if st.last_kind == "answer" and re.search(r"\d{1,3}(?:,\d{3})+|\bmillion\b|\bbillion\b", lr) and \
                re.fullmatch(r"(?:wow|whoa|damn|omg|oh wow|geez|jeez)?[,!. ]*(?:that'?s|thats|so) (?:a lot|so many|huge|massive|crazy|insane|a lot of people|big)", n):
            return say("wow_number")                     # "wow that's a lot" after "14,264,798 people"
        if re.fullmatch(r"(?:yeah,? |ugh,? |honestly,? )?(?:work|my job|my work) (?:is|has been) (?:just |so |really |super |pretty )?(?:boring|dull|so boring|mind[- ]numbing)(?: lately| these days)?", n):
            st.uses["bore89"] = [st.turn]
            st.last_exp = {"valence": "negative", "topic": "work", "person": False, "text": msg, "turn": st.turn}
            return say("boring_work")
        bo = st.uses.get("bore89")
        if bo and st.turn - bo[-1] <= 4:
            if re.fullmatch(r"(?:i )?(?:sit|am stuck|spend all day|spend the whole day|have) (?:in )?(?:back to back )?meetings(?: all day| the whole day| every day)?", n):
                bo.append(st.turn)
                return say("meetings")
            if re.fullmatch(r"(?:any |do you have any |got any )?(?:tips|ideas|advice)(?: (?:to|on how to|for how to) make it (?:less boring|more interesting|better))?|"
                            r"how (?:can|do) i make it (?:less boring|more interesting|better)|what (?:can|should) i do(?: about it)?", n):
                bo.append(st.turn)
                return say("boring_tips")
        if re.fullmatch(r"(?:a bit |a little |kinda |kind of |slightly )?(?:nervous|anxious|scared) but (?:mostly |also |really |very |super )?(?:excited|happy|looking forward to it)|"
                        r"(?:excited|happy) but (?:a bit |a little |also )?(?:nervous|anxious|scared)", n):
            return say("mixed_feel")
        le0 = st.last_exp or {}
        if re.search(r"\b(?:can'?t|cannot|couldn'?t) sleep\b|\bstill awake\b", (le0.get("text") or "").lower()) and st.turn - le0.get("turn", -99) <= 4:
            if re.fullmatch(r"(?:just |i'?m |i keep )?(?:thinking too much|overthinking|thinking about (?:stuff|things|everything)|my (?:mind|brain|head) (?:won'?t|wont|doesn'?t) (?:stop|shut up|switch off))", n):
                le0["turn"] = st.turn
                return say("sleep_think")
            if re.fullmatch(r"(?:about |mostly |mainly )?(?:work|my job|the job)(?: mostly| stuff)?", n):
                le0["turn"] = st.turn
                return say("sleep_work")
            if re.fullmatch(r"(?:maybe |ok |okay )?i'?ll (?:try )?(?:read(?:ing)?|read a bit|read a book)(?: a bit)?", n):
                return say("sleep_read")
        if re.fullmatch(r"(?:you )?(?:didn'?t|did not|don'?t|do not) (?:understand|get) (?:me|what i (?:said|meant|mean))(?: earlier| before| at all)?|you misunderstood(?: me)?", n):
            return say("misunderstood")
        lg0 = st.uses.get("lang89")
        if lg0 and st.turn - lg0[1] <= 3 and re.fullmatch(r"(?:i'?m |i am )?(?:a (?:total |complete )?beginner|just starting|i just started|i'?m new(?: to it)?)", n):
            return say("beginner")
        nat = re.fullmatch(r"(?:and |so |but )?(?:was|is) (?P<p>he|she|[a-z][a-z .'-]{2,40}?) (?:an? )?(?P<d>american|german|british|english|scottish|irish|french|italian|spanish|"
                           r"austrian|swiss|dutch|canadian|russian|japanese|chinese|indian|polish|swedish|norwegian|danish|greek|portuguese|mexican|brazilian|australian|belgian)", n)
        if nat and self.kgqa is not None:
            who = nat.group("p")
            if who in ("he", "she"):
                who = self.bot.resolve(who)
            if who and who not in ("he", "she"):
                try:
                    ans = self.kgqa.answer(f"what nationality was {who}?")
                except Exception:
                    ans = None
                vals_ok = [v for v in (ans.values if ans is not None else []) if v.lower() not in ("statelessness", "stateless")][:4]
                if vals_ok:
                    country = b["demonym"][nat.group("d")]
                    vals = " ".join(vals_ok)
                    where = _join_values(vals_ok)
                    key = "nat_yes" if re.search(country, vals, re.I) else "nat_no"
                    return Reply(msg, "answer", self._pick(st, f"daily:b86:{key}", b[key], x=ans.entity.name, y=where),
                                 answer=where, source={"kind": "kb", "source": "dbpedia", "key": ans.entity.title}, confidence=1.0, via="kb")
        if re.fullmatch(r"(?:can|could) (?:we|you) (?:speak|talk|chat|continue|write)(?: in)? english(?: please| now| instead)?|(?:let'?s|lets) (?:speak|talk|chat|switch to)(?: in)? english|"
                        r"english(?:,)? please|(?:please )?(?:speak|answer|reply) (?:in )?english(?: please)?|switch to english", n):
            st.lang = "en"
            return say("lang_en")
        if re.fullmatch(r"(?:can|could) (?:we|you) (?:speak|talk|chat|continue|write)(?: in)? german(?: please| now| instead)?|(?:let'?s|lets) (?:speak|talk|chat|switch to)(?: in)? german|"
                        r"german(?:,)? please|(?:please )?(?:speak|answer|reply) (?:in )?german(?: please)?|switch to german|do you speak german", n):
            st.lang = "de"
            return Reply(msg, "smalltalk", self._pick(st, "daily:b86:lang_de", b["lang_de"]), via="german")
        if re.fullmatch(r"(?:i )?(?:don'?t|do not|dont) know what to (?:ask|say|talk about)|(?:i'?m |im )?(?:not sure|out of ideas)(?: what to (?:ask|say))?|"
                        r"what (?:should|can) i ask(?: you)?|what can we talk about|what do you want to talk about|give me (?:an idea|something to ask)", n):
            return say("no_idea")
        phr = b["phrases"]
        lang_rx = "|".join(phr["langs"])
        lm2 = re.search(rf"\b(?:i'?m|i am|im|i'?ve been|i started|started|i want to start|i'?d like to start) (?:learning|to learn|studying|taking) (?P<l>{lang_rx})\b", n)
        if lm2:
            st.uses["lang89"] = [lm2.group("l"), st.turn]  # the reply comes from the hobby rules; phrases follow
        tq = re.fullmatch(rf"(?:and |so |ok )?(?:how (?:do|would|can) (?:you|i|we) say|what(?:'s| is) (?:the word for)?|how is) [\"“']?(?P<p>[a-z' ]+?)[\"”']?"
                          rf"(?: in (?P<l>{lang_rx}))?(?: again)?|(?:and |what about |how about )[\"“']?(?P<p2>[a-z' ]+?)[\"”']?", n)
        lg = st.uses.get("lang89")
        recent_lang = lg[0] if lg and st.turn - lg[1] <= 8 else None
        lang, p_ = None, ""
        if tq:
            lang, p_ = tq.group("l") or recent_lang, (tq.group("p") or tq.group("p2") or "").strip()
        elif lg and st.turn - lg[1] <= 3:
            lang, p_ = lg[0], n                           # a bare "good morning?" right after a phrase ("and" is gone in normalising)
        key = phr["alias"].get(p_, p_)
        if lang and key in phr["table"] and phr["table"][key].get(lang):
            st.uses["lang89"] = [lang, st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "daily:b86:phrase", b["phrase"], x=phr["table"][key][lang], y=lang.capitalize(), z=key),
                         via="everyday")
        la = st.last_action or {}
        act = ((la.get("kind") or "") == "rec:activity" and st.turn - la.get("turn", -99) <= 3) or \
            (st.uses.get("act88") and st.turn - st.uses["act88"] <= 3)
        if act and re.fullmatch(r"(?:maybe |rather |preferably |ideally )?(?:something|anything) (?:outside|outdoors|in nature|in the fresh air)|(?:more |rather )?outdoors?(?: stuff| things)?", n):
            st.uses["act88"] = st.turn
            return say("act_out")
        if act and re.fullmatch(r"(?:but |only |unfortunately )?it'?s (?:supposed|going|meant) to rain(?: this weekend| tomorrow| all weekend)?|(?:but )?it(?:'s| is) raining|"
                                r"(?:but )?the weather (?:is going to be|will be) (?:bad|awful|terrible)", n):
            st.uses["act88"] = st.turn
            return say("act_rain")
        dr = st.uses.get("drive86")
        if dr and st.turn - dr[-1] <= 5:
            if re.fullmatch(r"(?:it was |mostly |just |because of )?(?:the )?(?:parallel parking|parking|reverse parking|reversing|the roundabout|roundabouts|a roundabout|"
                            r"the motorway|the highway|stalling|i stalled|speed(?:ing)?|a stop sign|the stop sign|right of way|turning|three[- ]point turn)", n):
                dr.append(st.turn)
                return say("drive_part", x=re.sub(r"^(?:it was |mostly |just |because of )?(?:the )?", "", n))
            if re.fullmatch(r"(?:and )?i was (?:so |really |super |very |too )?(?:nervous|anxious|stressed|scared|shaking)(?: the whole time)?", n):
                dr.append(st.turn)
                return say("drive_nerves")
            if re.fullmatch(r"(?:so |and )?(?:when|how soon|how long until) (?:can|could) i (?:retake|redo|take|do|try) (?:it|the test|the exam)(?: again)?(?: again)?|"
                            r"how long do i (?:have to )?wait (?:to|before i can) (?:retake|redo|try again)(?: it)?", n):
                dr.append(st.turn)
                return say("drive_retake")
        le = st.last_exp or {}
        if le.get("valence") == "negative" and st.turn - le.get("turn", -99) <= 5 and \
                re.fullmatch(r"(?:yeah,? |ok(?:ay)?,? |hm+,? )?(?:you'?re right|youre right|true|good point|that makes sense|i guess you'?re right|maybe you'?re right|fair enough)", n):
            return say("agree_hard")                      # "you're right" after advice on a bad day: not "Nice! What else would you like to know?"
        c = st.uses.get("code86")
        if not c or st.turn - c[1] > 6:
            return None
        lm = re.fullmatch(rf"(?:probably |maybe |i think |i guess |definitely |thinking |prob(?:ably)? )?(?P<l>{langs})(?: probably| maybe| i think| i guess| for sure)?", n)
        if lm:
            k = lang_key(lm.group("l"))
            c[0], c[1] = k, st.turn
            return say("start_lang", x=lang_name(k), y=b["lang"][k])
        lang = lang_name(c[0]) if c[0] else "Python"
        if re.fullmatch(rf"(?:but |and |so )?(?:is it|is (?:that|coding|programming|{langs})|will it be|would it be) (?:really |very |too )?(?:hard|difficult|easy|tough)(?: to learn)?"
                        r"|(?:but |and )?how (?:hard|difficult) is it(?: to learn)?", n):
            c[1] = st.turn
            return say("hard")
        if re.fullmatch(r"(?:and |so )?how long (?:does|will|would) (?:it|that|this) take(?: to learn(?: it)?)?|(?:and |so )?how long until i can (?:code|program|build (?:something|stuff))", n):
            c[1] = st.turn
            return say("how_long")
        if re.fullmatch(r"(?:so |ok |okay )?(?:where|how) (?:should|do|can|would) i (?:start|begin)|any (?:tips|advice|resources)(?: for (?:a )?beginners?)?|"
                        r"what should i do first|how do i get started|what(?:'s| is) the best way to (?:start|learn(?: it)?)", n):
            c[1] = st.turn
            return say("where_start", x=lang)
        if re.fullmatch(r"(?:and |so )?what (?:can|could|should) i (?:build|make|do|code) (?:with it|first|as a beginner)?", n):
            c[1] = st.turn
            return say("build", x=lang)
        if re.fullmatch(r"(?:ok(?:ay)?,? )?(?:wish me luck|i'?ll try|i'?ll give it a (?:try|go|shot)|let'?s do (?:it|this))", n):
            st.uses.pop("code86", None)
            return say("luck")
        return None

    def _daily_ctx22(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 78: a whole evening in one chat — a moved deadline, chicken in the oven, "how old is the Eiffel
        Tower?" from the year it was built, "do you like Paris?", "I was there last year" / "the food was amazing",
        and "any recommendations?" after "I'll watch a movie later"."""
        b = self.bank.daily["b78"]
        n = re.sub(r"\s+", " ", re.sub(r"[^\w\s',-]", " ", norm)).strip(" .!?")
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"daily:b78:{key}", b[key], **kw), via="smalltalk")  # noqa: E731
        for ev in self.bank.daily["b82"]["events"]:
            if re.fullmatch(ev["q"], n):
                st.last_exp = {"valence": "negative" if ev["v"] == "neg" else "positive", "topic": None, "person": False, "text": msg, "turn": st.turn}
                return Reply(msg, "empathy", ev["a"], via="empathy")
        b0 = self.bank.daily["b80"]
        sm = re.fullmatch(r"my (?P<o>[a-z]+(?: [a-z]+)?) (?:is|are|was|were|got|just|has|have) (?:so |too |really |very |a bit |kind of |super |completely |totally |still )?"
                          r"(?P<a>dirty|messy|cold|slow|wet|broken|down|dead|died|stolen|lost|cracked|salty|burnt|burned|leaking|flat|empty|ruined|soaked|gone|"
                          r"not working|stopped working|freezing|frozen|red|blue|green|black|white|yellow|grey|gray|brown|pink|purple|orange|silver)", n) or \
            re.fullmatch(r"my (?P<o>tooth|teeth|back|stomach|tummy|chest) (?P<a>hurts|hurt|aches|is killing me|really hurts|hurts so much)", n) or \
            re.fullmatch(r"my (?P<o>plant|plants|flowers?|goldfish|fish) (?P<a>died|is dead|are dead)", n)
        if sm and sm.group("o") not in ("name", "favourite", "favorite", "birthday", "job", "hair colour", "favourite colour"):
            o, a = sm.group("o"), sm.group("a")
            cols = {"red", "blue", "green", "black", "white", "yellow", "grey", "gray", "brown", "pink", "purple", "orange", "silver"}
            if a in cols:
                return Reply(msg, "smalltalk", self._pick(st, "daily:b80:colour", b0["colour"], x=a, X=a.capitalize(), y=o), via="smalltalk")
            if re.match(r"hurt|ache|is killing|really hurt", a):
                o = {"teeth": "tooth", "tummy": "stomach"}.get(o, o)
                a = "hurts"
            key = next((k for k in (f"{o} {a}", o if o in ("wifi", "internet") else "", "plant" if re.search(r"plant|flower|fish", o) else "",
                                    f"{o.split()[-1]} {a}", a) if k and k in b0["special"]), None)
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            if key:
                return Reply(msg, "empathy", b0["special"][key], via="empathy")
            return Reply(msg, "empathy", self._pick(st, "daily:b80:neg", b0["neg"]), via="empathy")
        b9 = self.bank.daily["b79"]
        say9 = lambda key, kind="smalltalk", **kw: Reply(msg, kind, self._pick(st, f"daily:b79:{key}", b9[key], **kw),   # noqa: E731
                                                         via="empathy" if kind == "empathy" else "smalltalk")
        if re.fullmatch(r"(?:ugh,? |oh no,? )?my (?:phone|phone'?s|laptop|tablet|ipad|iphone)(?: screen)? (?:screen )?(?:cracked|broke|is cracked|shattered|got cracked)", n):
            return say9("cracked", "empathy")
        if re.fullmatch(r"(?:ugh,? |oops,? )?i (?:just )?dropped my (?:phone|laptop|tablet|ipad|iphone)(?: again)?", n):
            return say9("dropped", "empathy")
        mp = re.fullmatch(r"i (?:really |so )?miss (?P<w>my (?:grandma|grandpa|mom|mum|dad|mother|father|sister|brother|best friend|friend|dog|cat|grandmother|grandfather|"
                          r"family|home|ex|boyfriend|girlfriend)|him|her|them)(?: so much| a lot)?", n)
        if mp:
            w = mp.group("w")
            obj = {"him": "him", "her": "her", "them": "them"}.get(w) or ("her" if re.search(r"grandma|mom|mum|mother|sister|grandmother|girlfriend", w) else
                                                                          "him" if re.search(r"grandpa|dad|father|brother|grandfather|boyfriend", w) else "them")
            st.last_exp = {"valence": "negative", "topic": None, "person": True, "text": msg, "turn": st.turn}
            return say9("miss_person", "empathy", x=obj)
        if re.fullmatch(r"my (?:cat|kitten|dog|puppy) (?:just )?(?:knocked over|spilled|tipped over|broke|ate) my (?:coffee|tea|drink|glass|plant|cup|mug|water|food|lunch|dinner)", n):
            return say9("cat_mess")
        if re.fullmatch(r"(?:oops,? |ugh,? )?i (?:just )?(?:burned|burnt) (?:the |my )?(?:toast|food|dinner|pasta|rice|pizza|cookies|pancakes|eggs|lunch|breakfast)", n):
            return say9("burned")
        if re.fullmatch(r"my (?:neighbou?rs?|roommates?|flatmates?) (?:are|is) (?:so |really |super |being )?(?:loud|noisy|annoying)(?: again| tonight)?", n):
            st.last_exp = {"valence": "negative", "topic": None, "person": True, "text": msg, "turn": st.turn}
            return say9("noisy", "empathy")
        if re.fullmatch(r"(?:ugh,? )?(?:i'?m|im|i am) (?:stuck in|sitting in) (?:a )?(?:traffic|traffic jam|a jam)(?: again)?", n):
            return say9("traffic", "empathy")
        if re.fullmatch(r"can (?:you|u) keep a secret|will you tell anyone|is this (?:private|confidential)|are you going to tell anyone", n):
            return say9("secret")
        if re.search(r"\b(?:my |the )?(?:manager|boss|client|team lead|teacher|professor)\b.*\b(?:changed|moved|pushed|shifted|brought forward)\b.*\bdeadline\b|"
                     r"\bdeadline (?:got |was )?(?:changed|moved|pushed|shifted) (?:again|forward|back|up)\b", n):
            st.last_exp = {"valence": "negative", "topic": "work", "person": True, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:b78:deadline", b["deadline"]), via="empathy")
        if re.fullmatch(r"how long (?:does|do|should) (?:a |the )?(?:chicken|chicken breasts?|chicken thighs?|drumsticks?) (?:take|need|cook|bake|roast)(?: to cook| to bake)?"
                        r"(?: in the oven)?|how long (?:do|should) i (?:cook|bake|roast) (?:a |the )?chicken(?: breasts?| thighs?)?(?: in the oven)?", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b78:chicken_oven", b["chicken_oven"]), via="everyday")
        m = re.fullmatch(r"(?:btw |by the way |and |so )?how old is (?P<x>the eiffel tower|the colosseum|the statue of liberty|the golden gate bridge|big ben|"
                         r"the brandenburg gate|the sydney opera house|the empire state building|the leaning tower of pisa|the tower bridge|cologne cathedral|"
                         r"the burj khalifa|the taj mahal|notre dame|the berlin wall|stonehenge|the great wall of china|neuschwanstein castle)", n)
        ment = (self.bot.context.get("mention") or "").lower()
        if not m and ment and re.fullmatch(r"(?:and |so )?how old is (?:it|that)(?: now)?", n):
            # "how old is it?" after "how tall is the Eiffel Tower?": the landmark just talked about
            m = re.fullmatch(r"(?P<x>(?:the )?(?:eiffel tower|colosseum|statue of liberty|golden gate bridge|brandenburg gate|sydney opera house|"
                             r"empire state building|leaning tower of pisa|tower bridge|burj khalifa|taj mahal|great wall of china)|big ben|"
                             r"cologne cathedral|notre dame|stonehenge|neuschwanstein castle)", ment)
        if m:
            got = self._age_built(st, m.group("x"))
            if got:
                x, age, year = got
                return Reply(msg, "answer", self._pick(st, "daily:b78:age_built", b["age_built"], x=x, n=str(age), y=str(year)), via="kb")
        m = re.fullmatch(r"(?:do you like|have you been to|have you ever been to|what do you think of|what do you think about) (?P<x>[a-z ]{3,25})", n)
        known_city = {"paris", "rome", "london", "berlin", "madrid", "lisbon", "vienna", "prague", "amsterdam", "barcelona", "athens", "new york", "tokyo",
                      "munich", "hamburg", "venice", "florence", "istanbul", "dublin", "copenhagen", "stockholm", "budapest", "zurich", "sydney"}
        if m and m.group("x") in known_city:
            st.uses["city78"] = [m.group("x"), st.turn]
            return say("like_city", x=" ".join(w.capitalize() for w in m.group("x").split()))
        c78 = st.uses.get("city78") or st.uses.get("city74")
        trip_recent = c78 and st.turn - c78[1] <= 4
        if trip_recent and re.fullmatch(r"(?:yes,? |yeah,? )?i (?:was|went) there (?:last|this|in) (?:year|summer|month|spring|autumn|winter|\d{4})|"
                                        r"(?:yes,? |yeah,? )?i(?:'ve| have) been (?:there )?(?:once|twice|a few times|before)", n):
            st.uses["city78"] = [c78[0], st.turn]
            return say("was_there")
        if re.fullmatch(r"the food (?:there )?was (?:so |really |absolutely )?(?:amazing|great|incredible|delicious|fantastic|awesome|so good|insane)", n):
            return say("food_was")
        if re.fullmatch(r"i (?:think i'?ll|might|will|want to|wanna|am going to|'m going to) watch (?:a |some )?(?:movie|film)(?: later| tonight| today)?", n):
            st.uses["movie78"] = st.turn
            return None
        mv = st.uses.get("movie78")
        if mv is not None and st.turn - mv <= 3:
            if re.fullmatch(r"(?:any |got any )?(?:recommendations|suggestions|ideas|tips)|(?:what|which) (?:one )?should i watch|recommend (?:one|something)", n):
                st.uses["movie78"] = st.turn
                return self._turn(st, "recommend a movie")
            if re.fullmatch(r"something (?:funny|light|lighthearted)|(?:a )?(?:comedy|funny one)", n):
                st.uses["movie78"] = st.turn
                return self._turn(st, "recommend a funny movie")
        return None

    def _money75(self, st: DialogState, msg: str, n: str, de: bool = False) -> Reply | None:
        """Battery 75: a tip, a discount, a bill split — everyday sums people ask for."""
        num = r"(\d+(?:[.,]\d{1,2})?)"
        fmt = (lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) if de else (lambda v: f"{v:,.2f}")   # noqa: E731
        f = lambda x: float(x.replace(",", "."))                                                                                # noqa: E731
        cur = "€" if de or re.search(r"€|euro", n) else "$" if re.search(r"\$|dollar", n) else ""
        if not cur:
            fmt = lambda v: (f"{v:,.2f}".rstrip("0").rstrip(".") if not de else fmt_de(v))   # noqa: E731
        fmt_de = lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")   # noqa: E731
        m = re.search(rf"\b{num} ?% tip (?:on|for) (?:a |the )?(?:bill of )?[$€]?{num}", n) or re.search(rf"\btip (?:of )?{num} ?% (?:on|for) [$€]?{num}", n)
        if m and not de:
            p, b = f(m.group(1)), f(m.group(2))
            t = b * p / 100
            return Reply(msg, "tool", f"A {p:g}% tip on {cur}{fmt(b)} is {cur}{fmt(t)} — {cur}{fmt(b + t)} in total.", answer=fmt(t), via="tool")
        m = re.search(rf"(?:wie ?viel|wieviel) trinkgeld (?:bei|für|auf) {num} ?(?:€|euro)?", n)
        if m and de:
            b = f(m.group(1))
            return Reply(msg, "tool", f"Bei {fmt(b)} € sind 10 % Trinkgeld {fmt(b * 0.1)} € – du zahlst also rund {fmt(round(b * 1.1))} €. "
                                      f"In Deutschland sind 5–10 % üblich, bei sehr gutem Service gern mehr.", via="tool")
        m = re.search(rf"\b(?:what'?s |how much is )?(?:a )?{num} ?% off (?:of )?[$€]?{num}", n) or re.search(rf"{num} ?% (?:rabatt|nachlass) (?:auf|von) {num}", n)
        if m:
            p, b = f(m.group(1)), f(m.group(2))
            if de:
                return Reply(msg, "tool", f"{p:g} % Rabatt auf {fmt(b)} € macht {fmt(b * p / 100)} € weniger – du zahlst {fmt(b * (1 - p / 100))} €.", via="tool")
            return Reply(msg, "tool", f"{p:g}% off {cur}{fmt(b)} is {cur}{fmt(b * (1 - p / 100))} — you save {cur}{fmt(b * p / 100)}.", via="tool")
        m = re.search(rf"\bsplit [$€]?{num} (?:between|among|by|for|with) (\d+)(?: people| persons| of us| friends| ways)?", n) or \
            re.search(rf"\b(?:bill|total|check|it) (?:was|is|came to|comes to) [$€]?{num}(?: ?(?:euros?|dollars?|€|\$))?,? (?:can you |please )?split (?:it|that|this) "
                      rf"(?:between|among|by|for) (\d+)", n) or \
            re.search(rf"(?:teile|teil) {num} ?(?:€|euro)? (?:durch|auf|unter) (\d+)(?: personen| leute| leuten)?", n)
        if m:
            b, k = f(m.group(1)), int(m.group(2))
            if k <= 0:
                return None
            if de:
                return Reply(msg, "tool", f"{fmt(b)} geteilt durch {k} sind {fmt(b / k)} pro Person.", via="tool")
            return Reply(msg, "tool", f"{cur}{fmt(b)} split {k} ways is {cur}{fmt(b / k)} each.", via="tool")
        return None

    def _daily_ctx21(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 74: follow-ups a person keeps track of — "explain it simpler" and "why is it important?" about
        the concept just explained, "has anyone been there?" / "who?" / "why did they stop going?" after the Moon,
        "what's it famous for?" and "when's the best time to go?" after a city, and choosing a dog or a cat."""
        b = self.bank.daily["b74"]
        money = self._money75(st, msg, norm.strip(" ?!."))
        if money is not None:
            return money
        n = re.sub(r"\s+", " ", re.sub(r"[^\w\s',-]", " ", norm)).strip(" .!?")
        if re.fullmatch(r"(?:but |and |ok,? )?(?:no cooking(?: please)?|nothing (?:i have )?to cook|i don'?t (?:want|feel like) (?:to )?cook(?:ing)?|"
                        r"without cooking|something (?:without|with no) cooking)", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b75:no_cook", self.bank.daily["b75"]["no_cook"]), via="everyday")
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"daily:b74:{key}", b[key], **kw), via="smalltalk")  # noqa: E731
        topic = st.topic if st.topic and st.turn - st.topic.get("turn", -99) <= 5 else None
        la = st.last_about if st.last_about and st.turn - st.last_about.get("turn", st.turn) <= 5 else None
        title = ((la or {}).get("title") or (topic or {}).get("title") or (topic or {}).get("name") or "")
        tkey = re.sub(r"^(?:the|a|an) ", "", title.lower())
        tkey = {"photosynthetic": "photosynthesis", "black holes": "black hole", "vaccines": "vaccine", "volcanoes": "volcano",
                "earthquakes": "earthquake", "atoms": "atom", "ai": "artificial intelligence", "global warming": "climate change"}.get(tkey, tkey)
        if re.fullmatch(r"(?:can you |could you |please )?(?:explain|say|put) (?:it|that|this) (?:simpler|more simply|in simple(?:r)? (?:words|terms)|"
                        r"like i'?m (?:five|5|a kid|a child))(?: please)?|(?:in )?simpler(?: words| terms)?(?: please)?|i don'?t understand(?: that| it)?|"
                        r"what does that mean|eli5", n) and title:
            if tkey in b["simple"]:
                st.uses["simple74"] = [tkey, st.turn]
                return Reply(msg, "about", b["simple"][tkey][0], via="about")
            return None
        if re.fullmatch(r"(?:and |but |so )?why (?:is|are) (?:it|that|this|they) (?:so )?important|why does (?:it|that) matter|what'?s (?:it|that) good for", n):
            key = (st.uses.get("simple74") or [None])[0] if st.uses.get("simple74") and st.turn - st.uses["simple74"][1] <= 3 else tkey
            if key in b["simple"]:
                return Reply(msg, "about", b["simple"][key][1], via="about")
        m = re.fullmatch(r"(?:can you )?explain (?P<x>[a-z ]{3,30}?)(?: simply| in simple (?:words|terms)| like i'?m (?:five|5))", n) or \
            re.fullmatch(r"what is (?:a |an |the )?(?P<x>[a-z ]{3,30}?) in simple (?:words|terms)", n)
        if m:
            x = re.sub(r"^(?:the|a|an) ", "", m.group("x"))
            if x in b["simple"]:
                st.uses["simple74"] = [x, st.turn]
                return Reply(msg, "about", b["simple"][x][0], via="about")
        moon = tkey == "moon" or (st.uses.get("moon74") is not None and st.turn - st.uses["moon74"] <= 3)
        if moon:
            if re.fullmatch(r"(?:has|have|did) (?:anyone|anybody|people|humans|someone) (?:ever )?(?:been|gone|walked|landed|stood) (?:there|on it|on the moon|to the moon)", n):
                st.uses["moon74"] = st.turn
                return say("moon_been")
            if st.uses.get("moon74") is not None and re.fullmatch(r"(?:and )?who(?: was it| were they| exactly)?|who went|which astronauts", n):
                st.uses["moon74"] = st.turn
                return say("moon_who")
            if re.fullmatch(r"(?:and )?why did (?:they|we|people|nasa|humans) stop (?:going|going there|going back|flying there)|why hasn'?t anyone been back|"
                            r"why don'?t we go (?:back|there) anymore", n):
                st.uses["moon74"] = st.turn
                return say("moon_stop")
        city = (topic or {}).get("name") or (topic or {}).get("title") or ""
        ans = str(self.bot.context.get("answer") or "")
        if st.last_kind == "answer" and re.fullmatch(r"[A-Z][a-zé]+(?: [A-Z][a-zé]+)?", ans) and re.search(r"\bcapital\b", st.last_message or "", re.I):
            city = ans                                  # "what's the capital of Italy?" … "what's it famous for?": Rome
        euro = {"rome", "paris", "london", "berlin", "madrid", "lisbon", "vienna", "prague", "amsterdam", "barcelona", "athens", "budapest",
                "venice", "florence", "milan", "munich", "copenhagen", "stockholm", "dublin", "brussels", "zurich", "krakow", "istanbul", "edinburgh"}
        if re.fullmatch(r"(?:and |so )?(?:what'?s|what is|what) (?:it|the city|that city|rome|paris|london) (?:famous|known|best known) for|why is it famous", n):
            name = city or title
            found = self.about.find(name) if name else None
            st.uses["city74"] = [name, st.turn]
            if found:
                pool = list(found.sentences)
                try:
                    lo, hi = self.bot.c.doc_sentences(found.doc)
                    pool = [self.bot.c.sentence_text(i) for i in range(lo, min(hi, lo + 40))]
                except Exception:
                    pass
                sents = [x for x in pool if 30 < len(x) < 320 and re.search(r"\b(?:known for|famous|renowned|landmarks?|attractions?|world heritage|"
                                                                            r"most visited|nicknamed|referred to as|major centres? of|celebrated)\b", x, re.I)]
                if sents:
                    return Reply(msg, "about", sents[0], evidence=sents[0], source=found.source, via="about")
            if name:
                return say("famous_none", x=name)
        if re.fullmatch(r"(?:and |so )?(?:when'?s|when is|what'?s|what is) the best (?:time|season|month) to (?:go|visit|travel)(?: there)?", n) and \
                (city.lower() in euro or (st.uses.get("city74") or [""])[0].lower() in euro):
            return say("best_time", x=city if city.lower() in euro else st.uses["city74"][0])
        pet = st.uses.get("pet74")
        if re.fullmatch(r"(?:i'?m|i am|im) (?:thinking (?:about|of)|considering|planning on|planning to get|looking (?:at|into)) (?:getting |adopting )?(?:a |an )?(?P<p>dog|puppy|cat|kitten)", n):
            st.uses["pet74"] = ["dog" if re.search(r"dog|puppy", n) else "cat", st.turn]
            return None
        if pet and st.turn - pet[1] <= 5:
            if re.fullmatch(r"(?:so )?what (?:breed|kind|type)(?: of (?:dog|cat))? (?:would|do|should|could) (?:you recommend|you suggest|i get)|"
                            r"which (?:breed|dog|kind)(?: would you recommend| should i get)?|any (?:breed )?recommendations", n) and pet[0] == "dog":
                st.uses["pet74"] = [pet[0], st.turn]
                return say("breed")
            if re.fullmatch(r"(?:but |and |well,? )?i live in (?:a |an )?(?:small|tiny|little) (?:apartment|flat|studio)", n) and pet[0] == "dog":
                self._learn(st, ["I live in a small apartment."], msg)
                st.uses["pet74"] = [pet[0], st.turn]
                return Reply(msg, "learned", self._pick(st, "daily:b74:small_flat_dog", b["small_flat_dog"]), via="memory") if pet[0] == "dog" else \
                    Reply(msg, "learned", self._pick(st, "daily:b74:cat_instead", b["cat_instead"]), via="memory")
            if re.fullmatch(r"(?:and |so |ok,? )?(?:what about|how about|or) (?:a )?(?:cat|kitten)(?: instead)?|(?:would|is) a cat (?:be )?better", n):
                st.uses["pet74"] = ["cat", st.turn]
                return say("cat_instead")
            if re.fullmatch(r"(?:ok(?:ay)?,? )?(?:maybe|probably|i think|then) (?:a |i'?ll get a )?cat(?: then)?", n):
                return say("cat_ok")
        if re.fullmatch(r"i live in (?:a |an )?(?:small|tiny|little|cozy|cosy) (?:apartment|flat|studio)", n) and not (pet and st.turn - pet[1] <= 5):
            self._learn(st, ["I live in a small apartment."], msg)
            return Reply(msg, "learned", self._pick(st, "daily:b74:small_flat", b["small_flat"]), via="memory")
        return None

    def _daily_ctx20(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 73: what a person keeps and what passes — "I'm drinking coffee", "my mom fell asleep on the couch",
        "my dad called me" (a phone call, not a name), "the bus was late" get a reaction and are not stored;
        "I'm allergic to peanuts", "my birthday is on May 3rd", "I live with my girlfriend" are stored as what they are."""
        b = self.bank.daily["b73"]
        n = re.sub(r"\s+", " ", re.sub(r"[^\w\s',-]", " ", norm)).strip(" .!?")
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"daily:b73:{key}", b[key], **kw), via="smalltalk")  # noqa: E731
        b6 = self.bank.daily["b76"]
        say6 = lambda key, kind="smalltalk": Reply(msg, kind, self._pick(st, f"daily:b76:{key}", b6[key]), via="empathy" if kind == "empathy" else "smalltalk")  # noqa: E731
        sar = r"(?:(?:oh |just |well |yay |so )?(?:great|wonderful|perfect|fantastic|lovely|brilliant|awesome|nice|yay)|thanks a lot|just what i needed),? "
        if re.fullmatch(sar + r"(?:i |we )?(?:just )?missed (?:my |the |our )?(?:train|bus|flight|tram|connection|plane)(?: again)?", n) or \
                re.fullmatch(r"(?:ugh,? )?i (?:just )?missed (?:my |the )?(?:train|bus|flight|tram|connection)(?: again)?", n):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return say6("missed", "empathy")
        if re.fullmatch(sar + r"(?:my |the |our )?(?:car|laptop|phone|washing machine|fridge|bike|heating|dishwasher) (?:just )?(?:broke down|broke|died|stopped working|is broken)(?: again)?", n):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return say6("broke", "empathy")
        if re.fullmatch(r"(?:yay|great|wonderful|fantastic|oh joy|lovely),? (?:even )?more (?:work|homework|emails|meetings|overtime|tasks)", n):
            return say6("yay_work")
        if re.fullmatch(r"(?:just )?love that for me|living the dream|what a day|best day ever not", n):
            return say6("love_that")
        if re.fullmatch(r"(?:i'?m|im|i am) fine", n) and msg.strip().endswith(".") and len(msg.strip()) <= 10:
            return say6("fine_curt")
        if re.fullmatch(r"(?:no,? )?(?:really|seriously|honestly),? (?:i'?m|im|i am) (?:fine|okay|ok|good)", n):
            return say6("fine_really")
        if re.fullmatch(r"(?:ok(?:ay)?,? |well,? |fine,? )?(?:maybe|probably|actually) not (?:totally |really |so |that |completely )?(?:fine|okay|ok|good)", n):
            st.last_exp = {"valence": "negative", "topic": None, "person": False, "text": msg, "turn": st.turn}
            return say6("not_fine", "empathy")
        if re.fullmatch(r"(?:are|r) (?:you|u) (?:dumb|stupid|an idiot|broken)", n):
            return say6("dumb")
        fam = r"(?P<w>mom|mum|mother|dad|father|brother|sister|grandma|grandpa|wife|husband|boyfriend|girlfriend|son|daughter|friend|best friend|aunt|uncle)"
        he = lambda w: "she" if w in ("mom", "mum", "mother", "sister", "grandma", "wife", "girlfriend", "daughter", "aunt") else \
            "he" if w not in ("friend", "best friend") else "they"                                                         # noqa: E731
        m = re.fullmatch(r"(?:i'?m|i am|im) (?:just |currently |now |busy )?watching (?:some |a |the )?(?P<x>[a-z0-9' ]{1,30})", n)
        if m and not re.match(r"(?:my|you|it|that|this)\b", m.group("x")):
            return say("watching")
        m = re.fullmatch(r"(?:i'?m|i am|im) (?:just |currently |now )?(?:drinking|having|sipping) (?:a |my |some |an )?(?:cup of |glass of |mug of )?"
                         r"(?P<x>coffee|tea|green tea|beer|wine|water|juice|lemonade|cola|coke|latte|cappuccino|espresso|hot chocolate|smoothie)", n)
        if m:
            x = m.group("x")
            return say("drinking_coffee" if x in ("coffee", "latte", "cappuccino", "espresso") else "drinking_tea" if "tea" in x else "drinking")
        m = re.fullmatch(r"(?:i'?m|i am|im) (?:just |currently |now )?eating (?:a |an |some |my )?(?P<x>[a-z ]{2,25}?)(?: right now| now)?", n)
        if m and m.group("x") not in ("healthy", "well", "less", "more", "out", "too much", "a lot", "lunch", "dinner", "breakfast") and \
                len(m.group("x").split()) <= 3:
            return say("eating", x=m.group("x"))
        m = re.fullmatch(r"i (?:just |already )?(?:ate|had) (?P<a>a |an |some |my )?(?P<x>[a-z ]{2,25}?)(?: for (?:lunch|dinner|breakfast))?", n)
        if m and n.startswith("i just") and len(m.group("x").split()) <= 3 and \
                not re.search(r"\b(?:at|with|in|on|for|about|day|days|week|night|time|morning|evening|meeting|call|talk|chat|nap|shower|bath|fight|"
                              r"argument|baby|idea|thought|dream|accident|exam|test|interview|date|lunch|dinner|breakfast|enough|it|that|this|"
                              r"good|bad|great|long|rough|hard|crazy|weird)\b", m.group("x")):
            return say("ate", x=(m.group("a") or "") + m.group("x"))
        if re.fullmatch(r"(?:i'?m|i am|im) (?:just |currently )?listening to (?:some |my |a )?[a-z0-9' ]{2,30}", n):
            return None if re.search(r"\bpodcast|audiobook\b", n) else say("listening")
        if re.fullmatch(r"(?:i'?m|i am|im) (?:just |currently )?playing (?:some |a |the )?(?:video ?games?|games?|minecraft|fortnite|fifa|chess|the guitar|guitar|piano|the piano|cards|zelda|mario kart)", n):
            return say("playing")
        m = re.fullmatch(rf"my {fam} (?:just |finally )?(?:fell asleep|is asleep|is sleeping|is napping|dozed off)(?: on the (?:couch|sofa)| in front of the tv| again)?", n)
        if m:
            return say("asleep")
        m = re.fullmatch(rf"my {fam} (?:just )?(?:called|phoned|rang|texted|messaged|facetimed) me(?: today| earlier| this morning| last night| yesterday)?", n)
        if m:
            h = he(m.group("w"))
            return say("called", y=h, z={"she": "her", "he": "him", "they": "them"}[h])
        if re.fullmatch(rf"my {fam} (?:is|are) (?:coming over|visiting|coming to visit|stopping by)(?: later| tonight| today| tomorrow| this weekend)?", n):
            return say("coming")
        if re.fullmatch(r"my (?:cat|dog|kitten|puppy) is (?:sleeping|lying|sitting|purring|snoring|curled up|napping) (?:on|in) my (?:lap|bed|feet|keyboard|chest|arms)", n):
            return say("pet_lap")
        if re.fullmatch(r"(?:ugh,? )?(?:the |my )?(?:bus|train|tram|subway|metro|flight|plane) (?:was|is) (?:late|delayed|cancelled|canceled)(?: again| today| this morning)?", n):
            return say("late")
        m = re.fullmatch(r"(?:i'?m|i am|im) (?:very |really |severely |a bit )?allergic to (?P<x>[a-z ]{2,30})", n)
        if m:
            x = m.group("x").strip()
            self._learn(st, [f"I am allergic to {x}."], msg)
            return Reply(msg, "learned", self._pick(st, "daily:b73:allergy", b["allergy"], x=x), via="memory")
        mon = r"january|february|march|april|may|june|july|august|september|october|november|december"
        m = re.fullmatch(rf"my birthday is (?:on )?(?:the )?(?:(?P<m1>{mon}) (?P<d1>\d{{1,2}})(?:st|nd|rd|th)?|(?P<d2>\d{{1,2}})(?:st|nd|rd|th)? (?:of )?(?P<m2>{mon}))", n)
        if m:
            mo, d = (m.group("m1") or m.group("m2")).capitalize(), int(m.group("d1") or m.group("d2"))
            self._learn(st, [f"My birthday is on {d} {mo}." if m.group("d2") else f"My birthday is on {mo} {d}."], msg)   # as you wrote it
            suf = "th" if 10 <= d % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
            return Reply(msg, "learned", self._pick(st, "daily:b73:birthday", b["birthday"], x=f"{mo} {d}{suf}"), via="memory")
        m = re.fullmatch(r"i live with my (?P<x>girlfriend|boyfriend|wife|husband|partner|parents|mom|mum|dad|family|roommates?|flatmates?|sister|brother|grandma|kids|children|dog|cat)", n)
        if m:
            self._learn(st, [f"I live with my {m.group('x')}."], msg)
            return Reply(msg, "learned", self._pick(st, "daily:b73:live_with", b["live_with"], x=m.group("x")), via="memory")
        m = re.fullmatch(r"my best friend(?:'s name)? is (?:called |named )?(?P<x>[a-z]+)", n)
        if m and m.group("x") not in _NOT_NAMES and m.group("x") not in ("my", "a", "the", "very", "so", "really"):
            x = m.group("x").capitalize()
            self._learn(st, [f"My best friend is called {x}."], msg)
            return Reply(msg, "learned", self._pick(st, "daily:b73:friend_name", b["friend_name"], x=x), via="memory")
        return None

    def _daily_ctx19(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 69: messy real messages — "im good hbu" answered both ways, "what was the height again?" asked
        again from the questions so far, "what about food?" after tips for a trip, "merci!", "ugh monday again",
        a boss piling on tasks with advice on "idk what to do", and "that helps"."""
        b = self.bank.daily["b69"]
        n = re.sub(r"\s+", " ", re.sub(r"[^\w\s',%&-]", " ", norm)).strip(" .!?")      # "ugh monday again 😩": the words
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"daily:b69:{key}", b[key], **kw), via="smalltalk")  # noqa: E731
        qh = st.uses.setdefault("qh69", [])
        if st.last_q and (not qh or qh[-1] != st.last_q) and not re.search(r"\bagain\b", st.last_q):
            qh.append(st.last_q)
            del qh[:-8]
        if re.match(r"(?:what|whats|what's|who|when|where|how|which)\b", n) and not re.search(r"\b(?:again|it|its|they|them|he|she|there|that)\b", n) \
                and (not qh or qh[-1] != n + "?"):
            qh.append(n + "?")                      # "what's the tallest mountain in europe?" answered before the question path
            del qh[:-8]
        tm = re.search(r"make a trip to (?P<p>[A-Z][\w' -]+?) easier", st.last_reply or "")
        if tm:
            st.uses["trip69"] = [tm.group("p"), st.turn]
        if re.fullmatch(r"(?:i'?m |im |i am |all )?(?:good|fine|great|ok|okay|alright|not bad|pretty good|doing good|doing well|doing fine|good good)"
                        r"(?:,? thanks| thx| ty|,? thank you)?,? (?:and )?(?:hbu|wbu|you|u|how about you|what about you|how are you|how r u|"
                        r"and you|you\?|yourself)", n):
            return say("good_hbu")
        am = re.fullmatch(r"(?:wait,? |sorry,? |so,? |um,? |uh,? |hm+,? )?what (?:was|is|were) (?:the |its |it'?s )?(?P<a>height|population|"
                          r"architect|designer|year|date|age|name|capital|distance|area|size|length)(?: again)?(?:,? sorry)?", n)
        if am and "again" in n:
            keys = {"height": r"\btall|\bheight|\bhigh\b", "population": r"how many people|population|\blive\b", "architect": r"design|architect|built by",
                    "designer": r"design|architect", "year": r"\bwhen\b|\byear\b", "date": r"\bwhen\b|\bdate\b", "age": r"how old|\bage\b",
                    "name": r"\bname\b|\bcalled\b", "capital": r"\bcapital\b", "distance": r"how far|distance", "area": r"\barea\b|how big",
                    "size": r"how big|\bsize\b", "length": r"how long|\blength\b"}
            if not any(re.search(keys[am.group("a")], q, re.I) for q in qh):
                return Reply(msg, "clarify", self._pick(st, "daily:b69:again_what", b["again_what"], x=am.group("a")), via="clarify")
            for q in reversed(qh):
                if re.search(keys[am.group("a")], q, re.I):
                    parts = re.split(r" and (?=(?:who|what|when|where|how|which)\b)", q.rstrip("?"))
                    part = next((x for x in parts if re.search(keys[am.group("a")], x, re.I)), q)
                    if part is not q and len(parts) > 1 and re.search(r"\b(?:it|its|they|he|she)\b", part) and \
                            (ent := re.search(r"\b(?:is|was|are|were|does|did) (the [a-z ]+?|[A-Z][\w ]+?)(?: and | high| tall|$)", parts[0])):
                        part = re.sub(r"\b(?:it|they|he|she)\b", ent.group(1), part, count=1)
                    return self._turn(st, part.strip() + "?")
        sy = re.fullmatch(r"(?:what(?:'s| is) )?the (?:chemical )?symbol (?:for|of) (?P<e>[a-z]+)|what element has the symbol (?P<s>[a-z]{1,2})", n)
        if sy:
            els = b["elements"]
            if sy.group("e") and sy.group("e") in els:
                sym, latin = els[sy.group("e")]
                return Reply(msg, "answer", f"The chemical symbol for {sy.group('e')} is {sym}" + (f" (from the Latin {latin})." if latin else "."),
                             answer=sym, via="common", confidence=1.0)
            if sy.group("s"):
                hit = next((e for e, (sym, _l) in els.items() if sym.lower() == sy.group("s")), None)
                if hit:
                    return Reply(msg, "answer", f"{els[hit][0]} is the symbol for {hit}.", answer=hit, via="common", confidence=1.0)
        au = re.fullmatch(r"who(?:'s| is| was) the (?:author|writer) of (?P<x>[a-z0-9' :-]+)", n)
        if au:
            return self._turn(st, f"who wrote {au.group('x')}?")
        ga = re.fullmatch(r"(?:i'?m|im|i am) (?:really |pretty |quite |very |kinda |kind of )?good at (?P<x>[a-z][a-z ]{1,30}?)"
                          r"(?:,? (?:you|u|wbu|hbu|and you|what about you|how about you))?", n)
        if ga and ga.group("x") not in ("it", "that", "this", "everything", "nothing", "lying"):
            self._learn(st, [f"I am good at {ga.group('x')}."], msg)
            return Reply(msg, "learned", self._pick(st, "daily:b69:good_at", b["good_at"], x=ga.group("x")), via="memory")
        tr = st.uses.get("trip69")
        if tr and st.turn - tr[1] <= 4 and re.fullmatch(r"(?:and |ok,? |okay,? )?(?:what about (?:the )?food|food tips|(?:and )?food|"
                                                        r"what should i eat(?: there)?|where should i eat|any food tips|what'?s good to eat(?: there)?)", n):
            key = tr[0].lower()
            if key in b["trip_food"]:
                return Reply(msg, "smalltalk", self._pick(st, f"daily:b69:food:{key}", b["trip_food"][key]), via="smalltalk")
            return Reply(msg, "smalltalk", self._pick(st, "daily:b69:food:other", b["trip_food"]["other"], x=tr[0]), via="smalltalk")
        ft = re.fullmatch(r"(merci|gracias|grazie|danke|obrigado|obrigada|arigato)(?: beaucoup| mille| schön| sehr| gozaimasu)?", n)
        if ft:
            return Reply(msg, "smalltalk", self._pick(st, f"daily:b69:thx:{ft.group(1)}", b["foreign_thanks"][ft.group(1)]), via="smalltalk")
        if re.fullmatch(r"(?:ugh+|urgh|meh|oh no|nooo+|ahh+)?,? ?(?:it'?s )?monday(?: again| already| morning)?|mondays(?: suck| are the worst)?|"
                        r"(?:ugh+ )?another monday", n):
            return say("monday")
        if re.search(r"\bmy (?:boss|manager|supervisor|team lead)(?: just)? (?:keeps |always |constantly )?(?:giving|gives|gave|dumping|dumps|piling|piles|"
                     r"throwing|throws)(?: me)?(?: even)? (?:extra|more|so many|too many|additional|new)? ?(?:tasks|work|projects|stuff|things|jobs)\b", n) or \
                re.fullmatch(r"(?:i have |i've got |i got )?(?:way )?(?:too much|so much) work(?: at work)?|i'?m (?:so )?(?:overloaded|swamped|"
                             r"drowning in work)(?: at work)?", n):
            st.uses["work69"] = st.turn
            st.last_exp = {"valence": "negative", "topic": "work", "person": True, "text": msg, "turn": st.turn}
            return Reply(msg, "empathy", self._pick(st, "daily:b69:workload", b["workload"]), via="empathy")
        wk = st.uses.get("work69")
        if wk is not None and st.turn - wk <= 4 and re.fullmatch(r"(?:i )?(?:idk|don'?t know|dunno|have no idea) what (?:to do|i should do)|"
                                                                 r"what (?:should|can|do) i do(?: about it)?|any (?:advice|tips|ideas)|"
                                                                 r"what would you do|(?:yes|yeah|yep|definitely|totally),? (?:it'?s )?(?:too much|way too much)?", n):
            st.uses.pop("work69")
            st.uses["adv69"] = st.turn
            st.offer = None
            return say("workload_advice")
        if re.fullmatch(r"(?:ok(?:ay)?,? |oh,? |wow,? )?(?:thanks?(?: you)?,? |thx,? |ty,? )?(?:that|this|it) (?:really |actually )?(?:helps|helped|"
                        r"is helpful|was helpful|is really helpful)(?: a lot)?(?:,? thanks?(?: you)?|,? thx|,? ty)?|(?:thanks?,? )?(?:good|great) advice(?:,? thanks?)?|"
                        r"(?:thanks?,? )?(?:very|super|really) helpful(?:,? thanks?)?", n) and st.turn - st.uses.get("adv69", -99) <= 3:
            return say("helps")
        return None

    def _daily_ctx18(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 68: a relaxed chat — "not much, you?" answered first, ENGRAMM's own favourites with a reason
        on "why that one?", "what did you think of it?" about a film it cannot watch, pasta tonight (not stored as a
        favourite) with the dish and a drink, a lost match ("my team lost 3-0" is not "nice!"), "you're wrong lol"
        after a neutral answer, "i'm a cat person" (not a job), and a bored chat that offers something."""
        b = self.bank.daily["b68"]
        n = norm.strip(" .!?")
        lm = normalise(st.last_message or "").strip(" .!?")
        lr = st.last_reply or ""
        say = lambda key, **kw: Reply(msg, "smalltalk", self._pick(st, f"daily:b68:{key}", b[key], **kw), via="smalltalk")  # noqa: E731
        cy = re.fullmatch(r"(?P<a>(?:not much|nothing much|nm|nothing really|same old|just|chilling|relaxing)[a-z ,']*?)[,.!]* "
                          r"(?:and )?(?:you|u|wbu|hbu|what about you|how about you|and you|yourself)", n)
        if cy and re.search(r"\b(?:chill|chilling|relax|relaxing|lazy|couch|sofa|netflix)\b", n):
            return say("chill_you")
        fm = re.fullmatch(r"(?:do you have|have you got|what'?s|what is) (?:a |your )?(?:fav(?:ou?rite)?|favorite) (?P<k>[a-z ]+?)", n)
        if fm:
            kind = next((k for k, ws in b["fav_keys"].items() if fm.group("k") in ws), None)
            if kind:
                st.uses["fav68"] = [kind, st.turn]
                return Reply(msg, "smalltalk", self._pick(st, f"daily:b68:fav:{kind}", b["fav"][kind]), via="smalltalk")
        fv = st.uses.get("fav68")
        if fv and st.turn - fv[1] <= 2 and re.fullmatch(r"(?:but |and |ok,? |okay,? )?(?:why|why that one|why that|how come|why is that|"
                                                        r"why's that|what do you like about it|what makes it so good)", n):
            st.uses.pop("fav68")
            return Reply(msg, "smalltalk", self._pick(st, f"daily:b68:why:{fv[0]}", b["fav_why"][fv[0]]), via="smalltalk")
        sm = re.fullmatch(r"(?:have you|did you|you) (?:ever )?(?:seen|watched|read|heard) (?P<x>[a-z0-9' :]+)", lm)
        if sm and re.fullmatch(r"(?:so |and |ok,? )?(?:what did you think(?: of it| of that| about it)?|did you like it|how did you like it|"
                               r"what'?s your opinion(?: on it)?|was it good)", n):
            x = " ".join(w.capitalize() for w in sm.group("x").split())
            return say("think_of_it", x=x)
        ck = re.fullmatch(r"(?:i'?m|i am|im|we'?re|we are) (?:making|cooking|eating) (?P<x>[a-z ]+?) (?:tonight|today|for dinner|"
                          r"for lunch|later|this evening)|(?:i'?m|i am|im|we'?re|we are) having (?P<y>[a-z ]+?) for (?:dinner|lunch|tea)(?: tonight| today)?", n)
        if ck is None and re.fullmatch(r"(?:i'?m|i am|im|we'?re|we are|i'?ll be|gonna be) (?:cooking|making dinner|making lunch|cooking dinner|cooking lunch)"
                                       r"(?: tonight| today| later| this evening| for (?:my|the) (?:family|friends|kids|girlfriend|boyfriend|wife|husband|partner))?", n):
            st.uses["cook68"] = ["", st.turn]             # "i'm cooking tonight": what are you making?
            return say("cook_generic")
        if ck and len((ck.group("x") or ck.group("y")).split()) <= 3:
            x = re.sub(r"^(?:some|a|an|the|my|our) ", "", ck.group("x") or ck.group("y"))
            if x in ("dinner", "lunch", "breakfast", "food", "something", "something nice", "a meal", "meal", "tea", "supper"):
                st.uses["cook68"] = ["", st.turn]
                return say("cook_generic")
            st.uses["cook68"] = [x, st.turn]
            return say("cook", x=x, X=x[:1].upper() + x[1:])
        co = st.uses.get("cook68")
        if co and st.turn - co[1] <= 1 and re.fullmatch(r"(?:i'?m |im )?(?:not sure(?: yet)?|no idea(?: yet)?|idk(?: yet)?|dunno|i don'?t know(?: yet)?|"
                                                        r"haven'?t decided(?: yet)?|still deciding|no clue)", n):
            st.uses["cook68"] = ["", st.turn]
            return say("cook_unsure")
        mb = re.fullmatch(r"(?:maybe|probably|i think|prob|perhaps|i guess|thinking(?: about)?|either) (?P<x>[a-z]+(?: [a-z]+){0,2})", n)
        if co and st.turn - co[1] <= 2 and mb:
            n = mb.group("x")
        if co and st.turn - co[1] <= 2 and re.fullmatch(r"[a-z]+(?: [a-z]+){0,2}", n) and not _REACTION.fullmatch(n) and \
                not set(n.split()) & {"not", "sure", "yet", "idk", "something", "maybe", "probably", "just", "i", "you", "it", "know", "dunno",
                                      "think", "what", "why", "how", "no", "yes", "thanks", "lol", "haha", "cool", "nice", "is", "was",
                                      "sounds", "good", "great", "perfect", "delicious", "yum", "awesome", "will", "ill", "do", "that"} and \
                n not in ("yes", "no", "yeah", "nope", "idk", "not sure", "dunno", "maybe", "why", "what", "ok", "okay", "thanks"):
            st.uses["cook68"] = [n, st.turn]
            if n in b["dish"]:
                return Reply(msg, "smalltalk", self._pick(st, f"daily:b68:dish:{n}", b["dish"][n]), via="smalltalk")
            if len(n.split()) <= 2:
                return say("dish_other", X=n[:1].upper() + n[1:], x=n)
        if re.search(r"\bcream\b.*\bcarbonara\b|\bcarbonara\b.*\bcream\b", n) and re.match(r"(?:do you think|does|is|should|can|would)", n):
            return say("carbonara_cream")
        if co and co[0] and st.turn - co[1] <= 4:         # follow-ups on the dish just named
            dish = co[0]
            if dish == "carbonara" and re.search(r"\bcream\b", n) and re.match(r"(?:but |so )?(?:do|does|should|can|would|is|are|do you) ", n):
                co[1] = st.turn
                return say("carbonara_cream")
            rec = b.get("dish_recipe", {}).get(dish)
            if rec and re.fullmatch(r"(?:and |so )?(?:what(?:'s| is) the (?:original|real|traditional|classic|authentic) (?:recipe|way)|how do (?:you|i) make (?:it|that|a good one)|"
                                    r"what(?:'s| is) the recipe|what do i need(?: for it)?|what goes in(?: it| there)?|how is it made)", n):
                co[1] = st.turn
                return Reply(msg, "smalltalk", rec, via="everyday")
            if re.fullmatch(r"(?:ok(?:ay)?,? |alright,? |yeah,? )?(?:sounds (?:good|great|delicious|yummy|perfect)|yum+|mm+|thanks?(?: a lot)?|thank you|perfect|great|nice|"
                            r"i'?ll do that|i'?ll try that|will do)", n):
                st.uses.pop("cook68", None)
                return say("dish_enjoy", x=dish)
        if re.fullmatch(r"(?:what'?s|what is) your (?:opinion|take|view) on (?:pineapple pizza|pineapple on pizza|hawaiian pizza)|"
                        r"(?:does|should) pineapple (?:belong|go) on pizza|(?:do you like|thoughts on) pineapple (?:on )?pizza", n):
            return say("pineapple")
        dw = re.fullmatch(r"what (?:should|could|can) i drink with (?:it|that|this|(?P<x>[a-z ]+))", n)
        if dw:
            x = dw.group("x") or (co[0] if co and st.turn - co[1] <= 4 else "")
            key = next((k for k in b["drink_with"] if k != "other" and k in x), "other")
            return Reply(msg, "smalltalk", self._pick(st, f"daily:b68:drink:{key}", b["drink_with"][key]), via="smalltalk")
        if re.search(r"\b(?:watch|see|catch)(?:ed)? the (?:game|match)\b", lm) and \
                n in ("football", "soccer", "basketball", "hockey", "ice hockey", "tennis", "baseball", "rugby", "handball", "the football",
                      "american football", "the nba", "the nfl", "formula 1", "f1", "cricket", "volleyball", "the champions league"):
            st.uses["sport68"] = st.turn
            return say("sport", x=n.replace("the ", "", 1) if n.startswith("the ") else n)
        sc = re.fullmatch(r"(?:ugh,? |sadly,? |so,? )?(?:my team|we|my club|our team|they|[a-z]+(?: [a-z]+)?) (?P<v>lost|won|drew|tied)"
                          r"(?: the game| the match| again)?,? (?P<a>\d{1,2}) ?(?:-|–|to|:) ?(?P<b>\d{1,2})(?: again)?", n)
        if sc and int(sc.group("a")) < 30:
            v = {"tied": "drew"}.get(sc.group("v"), sc.group("v"))
            a, c = sorted((int(sc.group("a")), int(sc.group("b"))), reverse=v != "lost") if v != "drew" else (sc.group("a"), sc.group("b"))
            if v == "lost":
                a, c = max(int(sc.group("a")), int(sc.group("b"))), min(int(sc.group("a")), int(sc.group("b")))
            st.uses["lost68"] = [v, st.turn]
            team = re.match(r"(?:ugh,? |sadly,? |so,? )?(.+?) (?:lost|won|drew|tied)\b", n).group(1)
            if team not in ("my team", "we", "my club", "our team", "they") and v in ("won", "lost"):
                return say(v + "_team", x=" ".join(w.capitalize() for w in team.split()), a=a, b=c)
            return say(v, a=a, b=c)
        lo = st.uses.get("lost68")
        if lo and lo[0] == "lost" and st.turn - lo[1] <= 2 and \
                re.fullmatch(r"(?:yeah|yep|yes|ya|ugh)?,? ?(?:it |that |which )?(?:really |totally |so )?(?:sucks|stinks|hurts|was awful|was bad|"
                             r"is annoying|was terrible|is the worst)(?: so much)?", n):
            return say("lost_sucks")
        if re.fullmatch(r"(?:but |well,? )?(?:there'?s|there is) always next (?:season|year|time|game|match|week)", n):
            return say("next_season")
        if re.fullmatch(r"(?:you'?re|you are|ur|that'?s|thats) (?:so |totally |completely |just )?wrong(?: lol| haha| lmao)?", n) and \
                re.search(r"I can't have a favourite|what do you think about|I don't really take sides|Both have their fans", lr):
            return say("not_a_side")
        pp = re.fullmatch(r"(?:i'?m|i am|im) (?:more of |more |totally |definitely |really |kind of |kinda |a big |such )?(?:an? )?(?:big |total |huge )?"
                          r"(?P<x>[a-z]+) person", n)
        if pp:
            x = pp.group("x")
            if x in ("cat", "dog"):
                self._learn(st, [f"I like {x}s."], msg)
                return Reply(msg, "learned", self._pick(st, "daily:b68:pet_person", b["pet_person"], x=x), via="memory")
            if x in ("nice", "good", "kind", "normal", "decent", "friendly", "funny", "happy", "positive", "honest", "loyal", "real", "simple"):
                return say("good_person")
            if x in ("bad", "terrible", "horrible", "awful", "boring", "horrible", "useless", "difficult", "weird", "toxic"):
                return say("bad_person")
            if x not in ("shy", "private", "busy", "different"):
                return say("x_person", x=x)
        if re.fullmatch(r"(?:do you|you) (?:like|enjoy) (?:talking|chatting|speaking) (?:to|with) me|do you enjoy our (?:chats|conversations)|"
                        r"are you having fun(?: talking to me)?|do you like me", n):
            return say("like_talking")
        if re.fullmatch(r"(?:sorry,? )?(?:what'?s|what is|what was|whats) your name again|remind me (?:of )?your name|"
                        r"what did you say your name (?:is|was)|(?:sorry,? )?who are you again", n):
            return say("my_name")
        bo = st.uses.get("bored68")
        if re.fullmatch(r"(?:i'?m|i am|im) (?:so |really |super |very |sooo+ |soo )?bored(?: out of my mind)?|(?:i'?m )?bored+|so bored", n):
            st.uses["bored68"] = st.turn
            return None
        if bo is not None and st.turn - bo <= 3:
            if re.fullmatch(r"(?:i )?(?:don'?t know|dunno|idk|no idea|not sure)", n):
                st.uses["bored68"] = st.turn
                return say("bored_idk")
            if re.fullmatch(r"(?:something|anything) (?:fun|funny|cool|interesting)|surprise me|anything", n):
                st.uses.pop("bored68", None)
                return self._turn(st, "tell me a fun fact" if "interesting" in n or "cool" in n else "tell me a joke")
            if re.fullmatch(r"nah+|nope|no|not really|meh", n):
                st.uses.pop("bored68", None)
                return say("bored_nah")
        return None

    def _daily_ctx17(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 66: memory the way a person keeps it — a job and a city in one sentence, "no wait, I meant
        Munich" (the old fact is replaced, not kept beside it), an appointment that moved, "she's a doctor" about
        the sister just named, "what food do I hate?", a pizza without the hated mushrooms, and "do you know them?"
        about a favourite band."""
        b = self.bank.daily["b66"]
        n = norm.strip(" .!?")
        jm = re.fullmatch(r"(?:hi,? |hey,? |hello,? )?(?:(?:i'?m|i am|my name is|my name'?s) (?P<name>[a-z]+)(?:,| and|, and) )?(?:i'?m|i am|i work as) "
                          r"an? (?P<job>[a-z]+(?: [a-z]+)?) (?:in|from|at) (?P<place>[a-z]+(?: [a-z]+)?)", n)
        if jm and jm.group("job") not in ("lot", "bit", "fan", "little"):
            name, job, place = jm.group("name"), jm.group("job"), _place_case(jm.group("place"))
            sents = ([f"My name is {name.capitalize()}."] if name and name not in _NOT_NAMES else []) + \
                [f"I work as a {job}.", f"I live in {place}."]
            for sent in sents[:-1]:
                self._learn(st, [sent], msg)            # one memory per fact: "forget where I live" forgets only that
            r = self._learn(st, sents[-1:], msg)
            r.text = self._pick(st, "daily:b66:intro_named" if len(sents) == 3 else "daily:b66:intro", b["intro_named" if len(sents) == 3 else "intro"],
                                x=(name or "").capitalize(), y=article(job), Y=article(job)[:1].upper() + article(job)[1:], z=place)
            return r
        lm = st.last_message or ""
        cm = re.fullmatch(r"(?:no,? |no wait,? |wait,? |sorry,? |oops,? |actually,? |i mean,? )+(?:i meant |it'?s |make that |not \w+,? )?(?P<x>[a-z][a-z ]{1,30})", n)
        if cm and st.last_kind == "learned" and self.bot.context.get("last_learned") and len(cm.group("x").split()) <= 3:
            old = facts_from_text(lm, "probe", self.bot.is_name_initial_fact, typer=self.bot.typer)
            if any("#name" in f.relation for f in old):
                old = []                                  # "no wait, it's alexander": the name fix answers
            obj = next((f.object for f in old if f.subject == USER and f.object), None)
            if obj and re.search(re.escape(obj), lm, re.I):
                x = cm.group("x").strip()
                place_fact = any(f.object == obj and ({"#home", "#place", "#origin"} & set(f.relation)) for f in old)
                x = _place_case(x) if obj[:1].isupper() or place_fact else x
                fixed = re.sub(re.escape(obj), x, lm, count=1, flags=re.I)
                sid = self.bot.context.get("last_learned")
                try:
                    self.bot.memory.forget(sid)
                    self.bot.refresh()
                except Exception:
                    pass
                r = self._learn(st, [fixed], msg)
                r.text = self._pick(st, "daily:b66:corrected", b["corrected"], x=x)
                return r
        mv = re.fullmatch(r"(?:oh,? |actually,? |update:? |btw,? )?(?:it|that|the appointment|it'?s) (?:moved|got moved|was moved|changed|is now|has moved|'?s now)"
                          r" (?:to |on )?(?P<x>(?:next )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)(?: at \d{1,2}(?::\d\d)?(?: ?[ap]m)?)?)", n)
        if mv:
            texts = self.bot.user_texts() if hasattr(self.bot, "user_texts") else {}
            cand = [(sid, t) for sid, t in texts.items() if re.search(r"\b(?:appointment|meeting|exam|interview|dentist|doctor|party|date|flight|class)\b", t, re.I)
                    and re.search(r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)\b", t, re.I)]
            if cand:
                sid, t = sorted(cand)[-1]
                new_t = re.sub(r"\b(?:on )?(?:next )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)(?: at \d{1,2}(?::\d\d)?(?: ?[ap]m)?)?\b",
                               ("on " if not mv.group("x").startswith(("tomorrow", "today")) else "") + mv.group("x"), t, count=1, flags=re.I)
                new_t = re.sub(r"^(?:remember that |please remember |remember )", "", new_t, flags=re.I)
                try:
                    self.bot.memory.forget(sid)
                    self.bot.refresh()
                except Exception:
                    pass
                r = self._learn(st, [new_t[:1].upper() + new_t[1:]], msg)
                nm_ = re.search(r"\bmy ([a-z]+ (?:appointment|meeting|exam|interview)|appointment|meeting|exam|interview|dentist|party|flight|class)\b",
                                new_t, re.I)
                st.uses["moved66"] = [nm_.group(1).lower() if nm_ else "appointment", st.turn]
                day = mv.group("x")
                r.text = self._pick(st, "daily:b66:moved", b["moved"], x=day[:1].upper() + day[1:] if day[0].isalpha() else day)
                return r
        wd = re.fullmatch(r"what does my (?P<w>[a-z]+(?: friend)?) do(?: for (?:a living|work))?", n)
        if wd and wd.group("w") not in ("dog", "cat"):
            return self._question(st, f"what is my {wd.group('w')}'s job?")   # "what does my sister do?"
        mv6 = st.uses.get("moved66")
        if mv6 and st.turn - mv6[1] <= 3 and re.fullmatch(r"(?:so |and )?when is it(?: now| then)?", n):
            return self._question(st, f"when is my {mv6[0]}?")
        pnm = re.fullmatch(r"my (?P<w>sister|brother|mom|mum|mother|dad|father|wife|husband|girlfriend|boyfriend|partner|son|daughter|best friend|friend|boss|"
                           r"cousin|aunt|uncle|grandma|grandpa)(?:'s name is| is called) [a-z]+", n)
        if pnm:
            st.uses["person_noun"] = [pnm.group("w"), st.turn]   # "she's a doctor" may follow
            return None
        pn = st.uses.get("person_noun")
        if pn and st.turn - pn[1] <= 4:
            sj = re.fullmatch(r"(?:and |oh,? )?(?:she|he)(?:'s| is) an? (?P<j>[a-z]+(?: [a-z]+)?)(?: (?:at|in) (?P<w>[a-z ]+))?", n)
            if sj and sj.group("j") not in ("bit", "lot", "little", "fan", "great", "good", "nice"):
                st.uses["person_noun"] = [pn[0], st.turn]
                r = self._learn(st, [f"My {pn[0]} works as a {sj.group('j')}."], msg)
                r.text = self._pick(st, "daily:b66:person_job", b["person_job"], x=sj.group("j"), y=pn[0])
                return r
            if re.fullmatch(r"what'?s (?:her|his) name(?: again)?|what is (?:her|his) name(?: again)?|what was (?:her|his) name", n):
                return self._question(st, f"what is my {pn[0]}'s name?")
        if re.fullmatch(r"what (?:food|foods|things?|kind of food)? ?do i (?:hate|dislike|not like|can'?t stand)|what (?:food )?don'?t i like", n):
            return self._question(st, "what do i dislike?")
        if re.fullmatch(r"what do you (?:know|remember) about me(?: now| so far| at this point)?", n) and n.endswith(("now", "so far", "point")):
            return self._turn(st, "what do you know about me?")
        if re.fullmatch(r"(?:suggest|recommend|pick) (?:a |me a )?pizza(?: for me)?|what pizza should i (?:get|order|have)", n):
            texts = " ".join((self.bot.user_texts() if hasattr(self.bot, "user_texts") else {}).values()).lower()
            avoid = [w for w in ("mushrooms", "olives", "onions", "pineapple", "anchovies", "peppers") if re.search(rf"(?:don'?t like|hate|dislike) {w}", texts)]
            text = self._pick(st, "daily:b66:pizza", b["pizza"])
            if avoid:
                text += " " + self._pick(st, "daily:b66:pizza_avoid", b["pizza_avoid"], x=" or ".join(avoid))
            return Reply(msg, "smalltalk", text, via="everyday")
        if re.fullmatch(r"(?:do you know|have you heard of|you know) (?:them|him|her|that band|that one)", n):
            fb = re.search(r"\bmy favou?rite (?:band|singer|artist|group) is ([a-z0-9 .&'-]{2,30})", lm.lower())
            if fb:
                return self._daily_ctx14(st, msg, f"have you heard of {fb.group(1).strip()}")
        if re.fullmatch(r"(?:any |got any )?(?:ideas|suggestions|tips)(?: for that)?|what should i do", n) and \
                re.search(r"\b(?:relax|unwind|chill|switch off|rest)\b", lm.lower()):
            return Reply(msg, "smalltalk", b["relax"], via="everyday")
        return None

    def _daily_ctx16(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 64: emotional conversations that need the turn before — shyness after "how do people make
        friends", a presentation and "what if I mess up?", a panic attack, memories of someone who died (never
        "Noted: fish — yum!"), feeling not good enough, hopelessness (a gentle check-in with help numbers), a
        breakup, and good news with nerves."""
        b = self.bank.daily["b64"]
        n = norm.strip(" .!?")
        le = st.last_exp or {}
        recent_exp = le and st.turn - le.get("turn", -99) <= 4
        etext = (le.get("text") or "").lower() if recent_exp else ""
        recent = lambda key, k=3: (st.uses.get(key) and st.turn - st.uses[key][-1] <= k)   # noqa: E731
        bump = lambda: st.__setattr__("last_exp", dict(le, turn=st.turn)) if le else None  # noqa: E731
        if re.fullmatch(r"(?:but |and )?(?:i'?m|im|i am) (?:kinda |kind of |a bit |a little |quite |really |pretty |so |very )?"
                        r"(?:shy|introverted|an introvert|socially awkward|awkward with people|bad at talking to people|not very social)(?: though| tho| lol)?", n):
            bump()
            r = self._learn(st, ["I am shy."], msg)
            r.text = self._pick(st, "daily:b64:shy", b["shy"])
            r.kind = "smalltalk"
            return r
        if re.search(r"\b(?:presentation|talk|speech|pitch|exam|interview)\b", n) and re.search(r"\b(?:anxious|nervous|scared|worried)\b", etext + " " + n) \
                and re.fullmatch(r"(?:i (?:have|got) )?(?:a |an |my )?(?:big |important )?(?:presentation|talk|speech|pitch)(?: tomorrow| at work| in class)?", n):
            st.uses["pres64"] = [st.turn]
            bump()
            return Reply(msg, "smalltalk", self._pick(st, "daily:b64:presentation", b["presentation"]), via="empathy")
        if re.fullmatch(r"(?:but )?what if i (?:mess (?:it )?up|fail|screw (?:it )?up|freeze|forget (?:everything|what to say)|blank)", n) and \
                (recent("pres64", 3) or recent_exp):
            bump()
            return Reply(msg, "smalltalk", self._pick(st, "daily:b64:mess_up", b["mess_up"]), via="empathy")
        if re.search(r"\bpanic attacks?\b", n):
            st.uses["panic64"] = [st.turn]
            if re.search(r"\b(?:had|have|having|got) (?:a |another )?panic attack\b", n):
                return Reply(msg, "empathy", self._pick(st, "daily:b64:panic", b["panic"]), via="empathy")
        if recent("panic64", 2) and re.fullmatch(r"(?:it was|that was|it's|it is) (?:so |really |super |very )?(?:scary|terrifying|awful|horrible|frightening)", n):
            st.uses["panic64"] = [st.turn]
            return Reply(msg, "empathy", self._pick(st, "daily:b64:panic_scary", b["panic_scary"]), via="empathy")
        if recent("panic64", 4) and re.search(r"\bwhat (?:can|should|do) i do\b|\bhow (?:do|can) i (?:stop|handle|deal with|cope)\b|\bany tips\b", n):
            st.uses["panic64"] = [st.turn]
            return Reply(msg, "smalltalk", b["panic_tips"], via="everyday")
        grief = recent_exp and _LOSS.search(etext or "")
        if grief:
            if re.fullmatch(r"(?:we were|we'?re) (?:really |so |very |super )?close(?: to each other)?|he was (?:like )?my (?:best friend|hero)|"
                            r"she was (?:like )?my (?:best friend|hero)", n):
                bump()
                pr = "she" if re.search(r"\b(?:grandma|grandmother|mom|mum|mother|sister|aunt|wife|daughter|she)\b", etext) else "he"
                return Reply(msg, "smalltalk", self._pick(st, "daily:b64:close", b["close"], p=pr), via="empathy")
            mm = re.fullmatch(r"(?P<p>he|she|they) (?:taught|showed) me (?:how )?(?:to )?(?P<x>[a-z ]{2,30})|(?P<q>he|she|they) (?:used to|always|loved to) "
                              r"(?P<y>[a-z ]{2,30})", n)
            if mm:
                bump()
                x = (mm.group("x") or mm.group("y") or "").strip()
                who = mm.group("p") or mm.group("q")
                return Reply(msg, "smalltalk", self._pick(st, "daily:b64:memory", b["memory"], x=x,
                                                          d={"he": "him", "she": "her"}.get(who, "them")), via="empathy")
        if re.search(r"\b(?:not good enough|not smart enough|a failure|so stupid|worthless|useless)\b", n) and n.startswith(("i feel", "i'm", "im", "i am")):
            st.uses["impostor64"] = [st.turn]
        if recent("impostor64", 3):
            if re.search(r"\b(?:everyone|everybody|they all|all my (?:colleagues|coworkers|classmates))\b.*\b(?:smarter|better|more talented|faster)\b", n):
                st.uses["impostor64"] = [st.turn]
                return Reply(msg, "smalltalk", self._pick(st, "daily:b64:impostor", b["impostor"]), via="empathy")
            if re.search(r"\b(?:quit|give up on|stop) (?:everything|it all|on everything)\b|\bwhat'?s the point\b", n):
                return Reply(msg, "empathy", b["check_in"], via="empathy")
        if re.fullmatch(r"(?:nobody|no one|noone) (?:cares|cares about me|loves me|would notice|would miss me)(?: anyway)?", n):
            st.uses["alone64"] = [st.turn]
        if recent("alone64", 4):
            if re.fullmatch(r"(?:not even|including|especially) (?:my )?(?:family|parents|friends|mom|dad|partner)", n):
                st.uses["alone64"] = [st.turn]
                return Reply(msg, "empathy", self._pick(st, "daily:b64:not_even", b["not_even"]), via="empathy")
            if re.search(r"\b(?:why i (?:even )?bother|what'?s the point|no point (?:in )?(?:anything|trying|living)|give up|can'?t do this anymore|"
                         r"tired of (?:everything|it all|living))\b", n):
                return Reply(msg, "empathy", b["check_in"], via="empathy")
        if re.search(r"\b(?:broke up|split up|ended things|dumped)\b", n):
            st.uses["breakup64"] = [st.turn]
        if recent("breakup64", 4):
            if re.search(r"\b(?:should i|can we|is it ok to|could we) (?:still )?(?:stay|be|remain) friends\b", n):
                return Reply(msg, "smalltalk", self._pick(st, "daily:b64:friends", b["friends"]), via="everyday")
            if re.fullmatch(r"(?:it was|that was) my (?:decision|choice|idea)(?:,? but it still hurts| but it hurts| though)?|i ended it(?: but it hurts)?", n):
                st.uses["breakup64"] = [st.turn]
                bump()
                return Reply(msg, "smalltalk", self._pick(st, "daily:b64:my_choice", b["my_choice"]), via="empathy")
        if re.search(r"\b(?:got into|got accepted (?:to|at|into)|was accepted (?:to|at|into)|got a place at) (?:my )?(?:dream )?(?:university|uni|college|school|program|programme)\b", n):
            st.uses["uni64"] = [st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "daily:b64:uni", b["uni"]), via="empathy")
        um = re.fullmatch(r"(?:it'?s |its |it is )?(?:in|at) (?P<p>[a-z][a-z .'-]{2,25})", n)
        if recent("uni64", 2) and um:
            st.uses["uni64"] = [st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "daily:b64:uni_place", b["uni_place"], x=_place_case(um.group("p"))), via="empathy")
        if recent("uni64", 4) and re.search(r"\b(?:nervous|scared|anxious|worried) about (?:moving|leaving|the move|living alone|it)\b", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b64:uni_nerves", b["uni_nerves"]), via="empathy")
        return None

    def _daily_ctx15(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 62: sums said in passing ("20 on lunch and 15 on dinner" → "how much is that?" → "and if i add
        12?"), planning a day, saying no politely, "tell me something funny", and the bot's own imagined tastes."""
        b = self.bank.daily["b62"]
        n = norm.strip(" .!?")
        recent = lambda key, k=3: (st.uses.get(key) and st.turn - st.uses[key][-1] <= k)   # noqa: E731
        sp = re.findall(r"(?:€|\$|£)?(\d+(?:[.,]\d{1,2})?)(?: ?(?:euros?|dollars?|bucks|pounds|€|\$))? (?:on|for) [a-z]+", n)
        if len(sp) >= 2 and re.match(r"(?:i |we )?(?:spent|paid|spend|gave)\b", n):
            st.uses["sum62"] = [[float(x.replace(",", ".")) for x in sp], st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "daily:b62:spent", b["spent"]), via="smalltalk")
        sm = st.uses.get("sum62")
        if sm and st.turn - sm[1] <= 3:
            fmt = lambda v: f"{v:,.2f}".rstrip("0").rstrip(".")                              # noqa: E731
            if re.fullmatch(r"(?:so )?(?:how much (?:is|was) (?:that|it)(?: (?:altogether|in total|total))?|what'?s the total|how much in total|"
                            r"how much did i spend(?: in total)?)", n):
                total = sum(sm[0])
                sm[1] = st.turn
                return Reply(msg, "tool", f"{' + '.join(fmt(v) for v in sm[0])} = {fmt(total)}.", answer=fmt(total), via="tool", confidence=1.0)
            am = re.fullmatch(r"(?:and |plus )?(?:what )?(?:if i add|plus|and another|add) (?:€|\$|£)?(?P<v>\d+(?:[.,]\d{1,2})?)(?: (?:for|on) [a-z ]+)?", n)
            if am:
                sm[0].append(float(am.group("v").replace(",", ".")))
                sm[1] = st.turn
                total = sum(sm[0])
                return Reply(msg, "tool", self._pick(st, "daily:b62:total", b["total"], x=fmt(total)), answer=fmt(total), via="tool",
                             confidence=1.0)
            if re.search(r"\b(?:should|need to|gotta|have to) (?:stop|cut down on|quit) (?:buying |drinking |spending on )?(?P<x>[a-z]+)", n):
                return Reply(msg, "smalltalk", self._pick(st, "daily:b62:cut_down", b["cut_down"]), via="smalltalk")
        if re.fullmatch(r"(?:i need to|help me|can you help me|let'?s) plan (?:my|the) day|(?:i need to|let'?s) plan (?:today|tomorrow)", n):
            st.uses["plan62"] = [[], st.turn]             # the day planner answers; times said next are kept here
            if not n.startswith("help me plan"):
                return self._turn(st, "help me plan my day")   # "i need to plan my day": the same planner
            return None
        pl = st.uses.get("plan62")
        if pl and st.turn - pl[1] <= 3:
            items = re.findall(r"(?:(?:a |the )?(?P<w>meeting|gym|dentist|doctor|lunch|call|class|appointment|workout|interview|dinner|date)"
                               r" (?:at|@) (?P<t>\d{1,2}(?::\d\d)?(?: ?(?:am|pm))?))", n)
            todo = re.findall(r"(?:need to|have to|gotta|must) (?P<x>(?:buy|get|do|pick up|call|clean|write|send) [a-z ]{2,25}?)(?=,| and |$)", n)
            if items:
                pl[0] = [(w, t) for w, t in items]
                pl.append(todo)
                pl[1] = st.turn
                fixed = ", ".join(f"{w} at {t}" for w, t in items)
                return Reply(msg, "smalltalk", self._pick(st, "daily:b62:plan_got", b["plan_got"], x=fixed or "nothing fixed",
                                                          y=" and ".join(todo) or "a free day"), via="smalltalk")
            if re.search(r"\bwhen should i\b", n) and pl[0]:
                hours = sorted(int(re.match(r"\d+", t).group(0)) % 12 + (12 if (re.search(r"pm", t) or int(re.match(r"\d+", t).group(0)) < 8) else 0)
                               for _w, t in pl[0])
                gap = None
                for h1, h2 in zip(hours, hours[1:]):
                    if h2 - h1 >= 3:
                        gap = (h1 + 1, h2 - 1)
                        break
                slot = f"between {gap[0]}:00 and {gap[1]}:00" if gap else f"after {hours[-1] + 1}:00"
                act = re.sub(r"^when should i ", "", n)
                pl[1] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:b62:plan_slot", b["plan_slot"], x=act, y=slot), via="smalltalk")
        if re.fullmatch(r"how (?:do|can|should) i (?:say no|decline|turn (?:it|them|him|her) down|push back)(?: (?:politely|nicely|to my boss|at work|"
                        r"without being rude))*", n):
            return Reply(msg, "smalltalk", b["say_no"], via="everyday")
        if re.fullmatch(r"(?:then )?(?:tell me|say) something funny(?: then)?|make me laugh|cheer me up with a joke", n):
            return self._turn(st, "tell me a joke")
        last = (st.last_reply or "").lower()
        if re.fullmatch(r"(?:lucky you|must be nice|jealous|i wish|so jealous|nice for you)", n) and re.search(r"sleep|dream|tired|eat|food", last):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b62:lucky", b["lucky"]), via="smalltalk")
        if re.fullmatch(r"(?:but )?what would you dream (?:about|of)|if you could dream,? what would (?:it be|you dream about)", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b62:dream", b["dream"]), via="smalltalk")
        if re.fullmatch(r"(?:but )?if you could (?:eat|taste)(?: anything)?,? what would you (?:try|eat|have)(?: first)?", n):
            st.uses["bot_food"] = [st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "daily:b62:try_food", b["try_food"]), via="smalltalk")
        if re.fullmatch(r"(?:and )?(?:what|which) toppings?(?: would you (?:pick|choose|get|want))?|what (?:kind|toppings) on (?:it|yours|your pizza)", n) and \
                re.search(r"pizza", " ".join(st.recent[-3:]).lower() + " " + (st.last_message or "")):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b62:toppings", b["toppings"]), via="smalltalk")
        if re.fullmatch(r"(?:you'?re|you are|ur) (?:so |kinda |a bit |really |pretty )?(?:weird|strange|odd|a weirdo)(?: lol| haha)?", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b62:weird", b["weird"]), via="smalltalk")
        return None

    def _daily_ctx14(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 60: a hike and sore legs, a band ("have you heard of queen?" → "who was their singer?"),
        "what kind?" after I asked about music, a book already read, symptoms, the time elsewhere, and a long
        break after exams."""
        b = self.bank.daily["b60"]
        n = norm.strip(" .!?")
        recent = lambda key, k=3: (st.uses.get(key) and st.turn - st.uses[key][-1] <= k)   # noqa: E731
        if re.search(r"\b(?:went|been|go|was) (?:on a )?(?:hiking|hike|climbing|up a mountain|trekking)\b", n):
            st.uses["hike60"] = [st.turn]
        if recent("hike60", 4):
            hm = re.fullmatch(r"(?:we |i )?(?:went|climbed|hiked) (?:up )?(?:a |the )?(?:mountain|hill|peak|trail) (?:near|in|around|close to) "
                              r"(?P<p>[a-z ]{3,25})", n)
            if hm:
                st.uses["hike60"] = [st.turn]
                return Reply(msg, "smalltalk", self._pick(st, "daily:b60:hike_where", b["hike_where"], x=_place_case(hm.group("p"))),
                             via="smalltalk")
            hh = re.fullmatch(r"(?:it took |we walked |we hiked |like |about |around |almost )*(?P<h>\d+|two|three|four|five|six|seven|eight)"
                              r"(?: and a half)? hours?(?: long)?", n)
            if hh:
                st.uses["hike60"] = [st.turn]
                return Reply(msg, "smalltalk", self._pick(st, "daily:b60:hike_hours", b["hike_hours"], x=hh.group("h")), via="smalltalk")
            if re.search(r"\b(?:legs?|feet|knees?|calves|muscles) (?:hurt|are (?:so |really )?sore|ache|are killing me|are dead)\b|\bso sore\b", n):
                return Reply(msg, "smalltalk", self._pick(st, "daily:b60:hike_sore", b["hike_sore"]), via="smalltalk")
        tp_ = st.topic or {}
        sm = re.fullmatch(r"(?:and )?who (?:is|was|were) (?:their|the) (?P<r>lead singer|singer|vocalist|frontman|drummer|guitarist|bassist)", n)
        if sm and tp_.get("name") and st.turn - tp_.get("turn", -99) <= 3:
            role = "lead singer" if sm.group("r") in ("singer", "vocalist", "frontman") else sm.group("r")
            q = f"who was the {role} of {tp_['name']}?"      # "who was their singer?" after Queen
            self._spelled = q
            return self._question(st, q)
        last = (st.last_reply or "").lower()
        if re.fullmatch(r"(?:and )?(?:what kind|which kind|what sort|what genre|what about you|and you|you)", n) and \
                re.search(r"\bmusic\b|favourite band", last):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b60:music_mine", b["music_mine"]), via="smalltalk")
        hb = re.fullmatch(r"(?:have you|did you ever|do you know|you know|ever) (?:heard of |know )?(?:the band |the singer )?"
                          r"(?P<x>[a-z0-9][a-z0-9 .&'-]{1,30})", n)
        if hb and self.kgqa is not None and not re.fullmatch(r"(?:it|that|this|them|him|her|me|anything|something|a joke)", hb.group("x")):
            try:
                hits = self.kgqa.kb.link(hb.group("x"), limit=3)
            except Exception:
                hits = []
            ent = next((e for e, _ in hits if (e.type or "") in ("Band", "MusicalArtist", "Group") and
                        title_key(re.sub(r"\s*\([^)]*\)$", "", e.title)) == title_key(hb.group("x"))), None)
            if ent is not None:
                name = re.sub(r"\s*\([^)]*\)$", "", ent.title)
                found = self.about.find(ent.title, n=1)
                line = found.sentences[0] if found is not None and found.sentences else ""
                self.bot.context.update({"answer": None, "atype": None, "mention": name, "kb_last": None})
                st.topic = {"title": ent.title, "name": name, "turn": st.turn}
                text = self._pick(st, "daily:b60:band_known", b["band_known"], x=name, y=line) if line else \
                    self._pick(st, "daily:b60:band_short", b["band_short"], x=name)
                return Reply(msg, "smalltalk", text, via="smalltalk", source=found.source if found is not None and line else None)
        listed = re.search(r"in the spirit of|books? worth|“[^”]+” by ", st.last_reply or "")
        if listed and re.fullmatch(r"(?:i'?ve|i have) (?:already )?read (?:that|it|them|those|that one|all of them|all of those)(?: already)?|"
                                   r"read (?:it|that|them) already", n):
            st.uses["b60_read"] = [st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "daily:b60:read_it", b["read_it"]), via="everyday")
        if (listed or recent("b60_read", 2)) and re.fullmatch(r"(?:something|anything|any) (?:shorter|short|quicker|lighter|easier)(?: to read)?", n):
            return Reply(msg, "smalltalk", b["short_books"], via="everyday")
        if st.uses.get("sick") is not None and st.turn - st.uses["sick"] <= 3 and \
                re.fullmatch(r"(?:i have |i've got |just |mostly |only )?(?:a )?(?:sore throat|headache|runny nose|cough|fever|temperature|stuffy nose|chills|body aches)"
                             r"(?:(?:,| and) (?:a )?(?:sore throat|headache|runny nose|cough|fever|temperature|stuffy nose|chills|body aches))*", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b60:symptoms", b["symptoms"]), via="everyday")
        if re.fullmatch(r"(?:ok(?:ay)?,? )?(?:thanks?,? |thank you,? )?(?:i'?ll|i will|gonna|i'?m gonna) (?:stay (?:at )?home|stay in bed|rest|call in sick|"
                        r"take the day off)(?: then| tomorrow)?", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:b60:stay_home", b["stay_home"]), via="smalltalk")
        tq = re.fullmatch(r"(?:(?:and |what about |how about )(?:in )?|in )(?P<p>[a-z][a-z .'-]{2,25})", n)
        if tq and st.uses.get("last_via") == "tool" and re.search(r"\b\d{1,2}:\d\d\b", st.last_reply or ""):
            wt = self._world_time(st, f"what time is it in {tq.group('p')}?")
            if wt is not None and re.search(r"\d{1,2}:\d\d", wt.text):
                st.uses["time_place"] = [tq.group("p"), st.turn]
                return wt
        nm = re.fullmatch(r"is it (?P<w>night|nighttime|day|daytime|morning|evening|dark|late|early) (?:in (?P<p>[a-z][a-z .'-]{2,25})|there)"
                          r"(?: (?:now|right now))?", n)
        tp = st.uses.get("time_place")
        place = (nm.group("p") or (tp[0] if tp and st.turn - tp[1] <= 4 else None)) if nm else None
        if place:
            tr = self._world_time(st, f"what time is it in {place}?")
            hm2 = re.search(r"\b(\d{1,2}):(\d\d)\b", tr.text) if tr is not None else None
            if hm2:
                h = int(hm2.group(1))
                part = "night" if h >= 21 or h < 5 else "morning" if h < 12 else "afternoon" if h < 18 else "evening"
                st.uses["time_place"] = [place, st.turn]
                w = nm.group("w")
                yes = (w in ("night", "nighttime", "dark", "late") and part in ("night", "evening")) or \
                    (w in ("day", "daytime") and part in ("morning", "afternoon")) or w == part or (w == "early" and part == "morning")
                key = "part_yes" if yes else "part_no"
                return Reply(msg, "tool", self._pick(st, f"daily:b60:{key}", b[key], x=f"{hm2.group(1)}:{hm2.group(2)}", y=part,
                                                     z=_place_case(place)), via="tool", confidence=1.0)
        if re.search(r"\b(?:finished|done with|passed|wrote|had) (?:my |all my |the )?(?:exams?|finals|tests?|thesis|semester)\b", n):
            st.uses["exams_done"] = [st.turn]
        if recent("exams_done", 4):
            if re.fullmatch(r"(?:i think |i hope |pretty sure |i guess )?(?:they|it|everything|all of them) went (?:well|good|great|ok|okay|fine)(?: i think)?", n):
                st.uses["exams_done"] = [st.turn]
                return Reply(msg, "smalltalk", self._pick(st, "daily:b60:exams_well", b["exams_well"]), via="empathy")
            om = re.fullmatch(r"(?:and )?(?:now )?(?:i have|i've got|i get) (?P<x>(?:\d+|a few|two|three|four|six) (?:weeks?|months?|days?)) "
                              r"(?:off|free|of holidays?|of vacation|break)", n)
            if om:
                st.uses["exams_done"] = [st.turn]
                st.uses["long_break"] = [st.turn]
                return Reply(msg, "smalltalk", self._pick(st, "daily:b60:time_off", b["time_off"], x=om.group("x")), via="smalltalk")
        if recent("long_break", 3) and re.search(r"\bwhat (?:should|could|can) i do\b", n):
            return Reply(msg, "smalltalk", b["break_ideas"], via="everyday")
        return None

    def _daily_ctx13(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 58: follow-ups a person expects to work — "no, I meant in Europe", "why?" after a pick,
        "I'll go with Spanish", "are you sure?", "I don't get it" after a joke, and "what would you do?"
        before quitting a job."""
        d = self.bank.daily
        n = norm.strip(" .!?")
        dc = st.uses.get("decided")
        if dc and st.turn - dc[2] <= 3:
            if re.fullmatch(r"(?:but )?(?:why|how come|why that one|why (?:not )?(?:the other|" + re.escape(dc[1].lower()) + r"))", n):
                why = (d.get("decide_why") or {}).get(dc[0].lower())
                text = self._pick(st, "daily:decide_reason", d["decide_reason"], x=dc[0].capitalize(), a=why["for"]) if why else \
                    self._pick(st, "daily:decide_coin", d["decide_coin"], x=dc[0], y=dc[1])
                dc[2] = st.turn
                return Reply(msg, "smalltalk", text, via="everyday")
            gm = re.fullmatch(r"(?:hmm+,? |ok(?:ay)?,? |yeah,? )?(?:i think )?(?:i'?ll|i will|i'?m gonna|i am going to|let'?s) (?:go with|pick|choose|do|take) "
                              r"(?P<x>[a-z ]+?)(?: then)?|(?P<y>[a-z ]+?) it is", n)
            if gm:
                x = (gm.group("x") or gm.group("y")).strip()
                st.uses["chosen"] = [x, st.turn]
                st.uses.pop("decided", None)
                key = "chosen_lang" if x.lower() in (d.get("decide_why") or {}) else "chosen"
                return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=x.capitalize()), via="smalltalk")
        ch = st.uses.get("chosen")
        if ch and st.turn - ch[1] <= 3 and ch[0].lower() in (d.get("decide_why") or {}) and \
                re.fullmatch(r"how long (?:will|would|does) it take(?: to learn(?: it)?)?|how long to learn it|is it hard(?: to learn)?", n):
            return Reply(msg, "smalltalk", d["learn_time"][0], via="everyday")
        mm = re.fullmatch(r"(?:no,? |nah,? |sorry,? |oh,? )?i meant (?P<x>in [a-z ]{3,30}|on [a-z ]{3,30}|for [a-z ]{3,30})", n)
        if mm and st.last_q and re.search(r"\b(?:in|on) the world\b|\best\b", st.last_q.lower()):
            q = re.sub(r"(?i)\b(?:in|on) the world\b", mm.group("x"), st.last_q) if re.search(r"(?i)\bin the world\b", st.last_q) \
                else st.last_q.rstrip(" ?") + " " + mm.group("x") + "?"
            self._spelled = q                              # "What's the tallest mountain in europe?"
            return self._question(st, q)
        lf = st.last_fact or {}
        if re.fullmatch(r"(?:are you|you) (?:sure|certain)|(?:is that|that'?s) (?:right|true|correct)|really", n) and lf.get("sure") and \
                (lf.get("source") or {}).get("kind") == "kb" and lf.get("answer") and st.last_kind == "answer":
            return Reply(msg, "answer", self._pick(st, "daily:sure_kb", d["sure_kb"], x=lf["answer"], y=lf["source"].get("key", "")),
                         via="why")
        hm = re.search(r"(\d[\d,]*(?:\.\d+)? m \([\d,]+ ft\))", st.last_reply or "")
        if hm and st.uses.get("last_via") == "common" and re.fullmatch(r"(?:and )?how (?:tall|high) is (?:it|that)", n):
            # "how tall is it?" right after "Mount Elbrus … at 5,642 m (18,510 ft)": the number just said
            item = next((it for it in d.get("common", []) if isinstance(it, dict) and it.get("a") == st.last_reply), None)
            who = (item or {}).get("t") or (item or {}).get("v") or "It"
            return Reply(msg, "answer", f"{who} is {hm.group(1)} high.", answer=hm.group(1), via="common", confidence=1.0)
        la = st.last_action or {}
        if la.get("kind") == "joke" and st.turn - la.get("turn", -99) <= 1 and \
                re.fullmatch(r"(?:i )?(?:don'?t|do not|dont) get it|i don'?t understand(?: it)?|what\?*|huh|explain(?: it)?|i'?m confused", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:joke_explain", d["joke_explain"]), via="smalltalk")
        if re.search(r"\b(?:thinking (?:about|of) quitting|want to quit|wanna quit|going to quit|gonna quit|should i quit) (?:my )?(?:job|work)\b", n):
            st.uses["quit_job"] = [st.turn]
            return None
        qj = st.uses.get("quit_job")
        if qj and st.turn - qj[-1] <= 4:
            if re.fullmatch(r"(?:but )?(?:i |we )?(?:really )?need the (?:money|salary|income|paycheck)|(?:but )?i can'?t afford (?:to|it)", n):
                st.uses["quit_job"] = [st.turn]
                return Reply(msg, "smalltalk", self._pick(st, "daily:quit_money", d["quit_money"]), via="empathy")
            if re.fullmatch(r"what (?:would|should) (?:you|i) do|what do you think(?: i should do)?|what would you do in my (?:place|shoes)", n):
                st.uses["quit_job"] = [st.turn]
                return Reply(msg, "smalltalk", self._pick(st, "daily:quit_view", d["quit_view"]), via="everyday")
        return None

    def _daily_ctx12(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 57: everyday moments that only make sense with the turn before — a new puppy and its name,
        an empty fridge, a sleepless 3am, a dead phone (never grief), rain on a run, a favourite colour, a
        friend moving away (missing them is no bereavement)."""
        d = self.bank.daily
        n = norm.strip(" .!?")
        recent = lambda key, k=3: (st.uses.get(key) and st.turn - st.uses[key][-1] <= k)   # noqa: E731
        if re.fullmatch(r"(?:guess what|you know what|guess what happened|you'?ll never guess what happened)", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:guess_what", d["guess_what"]), via="smalltalk")
        pm = re.fullmatch(r"(?:guess what,? )?(?:i|we) (?:just )?got a (?:new )?(?P<x>puppy|kitten|dog|cat|bunny|rabbit|hamster)", n)
        if pm:                                            # "i have a cat" / "i adopted a dog": the pet flow asks the name
            st.uses["new_pet"] = [pm.group("x"), None, None, None, st.turn]   # kind, he/she, breed, name, turn
            st.uses["pet"] = [pm.group("x"), st.turn]     # the pet memory: "her name is luna" is remembered
            return Reply(msg, "smalltalk", self._pick(st, "daily:pet_new", d["pet_new"], x=pm.group("x")), via="smalltalk")
        pet = st.uses.get("new_pet")
        if pet and (pet[3] or pet[2]):                    # "what was her name again?", "what kind of dog do i have?"
            kinds = r"(?:dog|puppy|cat|kitten|bunny|rabbit|hamster|pet)"
            pron = r"(?:her|his|its|the (?:dog|puppy|cat|kitten|bunny|rabbit|hamster)'?s|my " + kinds + r"'?s)"
            ask_name = re.fullmatch(rf"(?:and |so |sorry,? |wait,? )?(?:what(?:'s| is| was)|whats|remind me(?: of)?|do you remember) {pron} name(?: again)?"
                                    rf"|(?:and |so )?what did (?:i|we) (?:call|name) (?:her|him|it|my {kinds})(?: again)?"
                                    rf"|(?:and |so )?what(?:'s| is) my {kinds} called(?: again)?", n)
            ask_kind = re.fullmatch(rf"(?:and |so )?what (?:kind|breed|type|sort) of {kinds} (?:do i have|have i got|did i get|is (?:she|he|it|mine))(?: again)?"
                                    rf"|(?:and |so )?what breed is (?:she|he|it|my {kinds})(?: again)?", n)
            subj = {"she": "She", "he": "He"}.get(pet[1] or "", "It")
            if ask_name and pet[3]:
                pos = {"She": "Her", "He": "His"}.get(subj, "Its")
                return Reply(msg, "answer", self._pick(st, "daily:pet_recall_name", d["pet_recall_name"], x=pet[3], y=pos,
                                                       z=pet[2] or {"puppy": "dog", "kitten": "cat"}.get(pet[0], pet[0])),
                             answer=pet[3], via="memory", confidence=1.0)
            if ask_kind and pet[2]:
                return Reply(msg, "answer", self._pick(st, "daily:pet_recall_kind", d["pet_recall_kind"], x=pet[2], y=subj,
                                                       z=pet[3] or "your " + pet[0]),
                             answer=pet[2], via="memory", confidence=1.0)
        if recent("new_pet", 4):
            pet = st.uses["new_pet"]
            nm_ = re.search(r"\b(?P<p>her|his|its|their) name is (?P<x>[a-z]+)|\b(?P<q>she|he|it)(?:'s| is) called (?P<y>[a-z]+)", n)
            if nm_:
                pet[3], pet[4] = (nm_.group("x") or nm_.group("y")).capitalize(), st.turn
                g = {"her": "she", "his": "he"}.get(nm_.group("p") or "", nm_.group("q") if nm_.group("q") in ("she", "he") else None)
                if g and pet[1] in (None, "it"):
                    pet[1] = g                            # "her name is luna": a she
                return None                               # the pet flow remembers the name
            bm = re.fullmatch(r"(?:(?P<g>she|he|it)(?:'s| is) an? |an? )(?P<b>[a-z][a-z -]{2,30}?)(?: puppy| dog| kitten| cat)?", n)
            if bm and pet[0] in ("puppy", "dog", "kitten", "cat") and not re.search(r"\b(?:so|very|really|cute|good|bad)\b", bm.group("b")):
                g = bm.group("g") or "it"
                breed = " ".join(w.capitalize() if w in _PROPER_BREED_WORDS else w for w in bm.group("b").split())
                pet[1], pet[2], pet[4] = g, breed, st.turn
                p_ = {"she": "she", "he": "he"}.get(g, "it")
                kind = {"puppy": "dog", "kitten": "cat"}.get(pet[0], pet[0])
                r = self._learn(st, [f"My {kind} is a {breed}."], msg)    # "what breed is she?" later
                st.uses["pet"] = [kind, st.turn]
                st.uses["pet_breed"] = [breed, st.turn]
                if pet[3]:
                    r.text = self._pick(st, "daily:pet_breed_named", d["pet_breed_named"], x=breed, y=pet[3])
                else:
                    r.text = self._pick(st, "daily:pet_breed2", d["pet_breed2"], x=breed, p=p_,
                                        d={"she": "her", "he": "him"}.get(g, "it"))
                return r
            if re.search(r"\b(?:name|names|call (?:her|him|it))\b", n) and re.search(r"\b(?:idea|ideas|suggest|suggestions|should|what)\b", n):
                key = {"she": "female", "he": "male"}.get(pet[1] or "", "any")
                pool = d["pet_name_pool"][key]
                k = int(hashlib.md5(f"{st.conversation}:{st.turn}".encode()).hexdigest(), 16) % len(pool)
                names = (pool[k:] + pool[:k])[:3]           # a different three each time, the same in a replay
                st.uses["pet_name_list"] = [names, st.turn]
                pet[4] = st.turn
                p_ = {"she": "her", "he": "him"}.get(pet[1] or "", "your " + pet[0])
                lead = self._pick(st, "daily:pet_names_lead", d["pet_names_lead"], p=p_)
                tail = self._pick(st, "daily:pet_names_tail", d["pet_names_tail"], p=p_)
                return Reply(msg, "smalltalk", lead + "\n\n" + "\n".join(f"• {x}" for x in names) + "\n\n" + tail,
                             via="smalltalk")
            nl = st.uses.get("pet_name_list")
            if nl and st.turn - nl[1] <= 2:
                pick = _ordinal_pick(n, nl[0]) or next((x for x in nl[0] if re.search(rf"\b{x.lower()}\b", n)), None)
                if pick and not re.search(r"\b(?:not|don'?t|hate)\b", n):
                    st.uses.pop("pet_name_list", None)
                    kind = {"puppy": "dog", "kitten": "cat"}.get(pet[0], pet[0])
                    r = self._learn(st, [f"My {kind} is called {pick}."], msg)      # "what's my puppy called?" later
                    pet[3] = pick
                    st.uses["pet_name"] = pick
                    r.text = self._pick(st, "daily:pet_name_pick", d["pet_name_pick"], x=pick, y=pet[2] or pet[0])
                    return r
        if re.search(r"\b(?:i'?m|im|i am) (?:so |really |super |very )?(?:hungry|starving|famished)\b", n):
            st.uses["hungry"] = [st.turn]
        if re.fullmatch(r"(?:but |and |ugh,? )?(?:there'?s|theres|there is|i have|ive got|i've got|i got) (?:nothing|no food|nothing at all) "
                        r"(?:in (?:the|my) (?:fridge|kitchen|house)|at home|to eat)", n) or \
                re.fullmatch(r"(?:but |and |ugh,? )?(?:my |the )?fridge is (?:empty|basically empty)", n):
            st.uses["fridge"] = [st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "daily:fridge_empty", d["fridge_empty"]), via="everyday")
        if recent("fridge", 3) or recent("hungry", 3):
            im = re.fullmatch(r"(?:i have |ive got |i've got |i got |there'?s |theres )?(?:just|only)? ?(?:some )?(?P<i>[a-z ,]+?)(?: and that'?s it| lol)?", n)
            words = set(re.findall(r"[a-z]+", im.group("i"))) if im else set()
            items = {re.sub(r"s$", "", w) if w not in ("eggs",) else "eggs" for w in words}
            items = {"eggs" if w in ("egg", "eggs") else w for w in items}
            if im and re.match(r"(?:i have |ive got |i've got |i got |there'?s |theres )?(?:just|only)\b", n) or (im and recent("fridge", 3)):
                for dish in d["fridge_dishes"]:
                    if all(x in items or x + "s" in words for x in dish["need"]):
                        st.uses["dish_now"] = [dish["t"], st.turn]
                        return Reply(msg, "smalltalk", self._pick(st, "daily:fridge_dish", d["fridge_dish"], x=dish["x"], y=dish["y"]),
                                     via="everyday")
                if re.match(r"(?:i have |ive got |there'?s )?(?:just|only)\b", n):
                    return Reply(msg, "smalltalk", self._pick(st, "daily:fridge_none", d["fridge_none"]), via="everyday")
        dn = st.uses.get("dish_now")
        if dn and st.turn - dn[1] <= 3 and re.search(r"\bhow long\b.*\b(?:cook|fry|bake|take|leave)\b", n):
            return Reply(msg, "smalltalk", dn[0], via="everyday")
        if re.search(r"\b(?:can'?t|cannot|cant|couldn'?t) (?:fall )?(?:sleep|get to sleep)\b|\binsomnia\b|\bstill awake\b|\bwide awake\b", n):
            st.uses["no_sleep"] = [st.turn]
        if recent("no_sleep", 3):
            tm = re.fullmatch(r"(?:and )?(?:it'?s|its|it is) (?:already )?(?P<x>\d{1,2}(?::\d\d)? ?am|midnight)(?: (?:already|now|lol))?", n)
            if tm:
                st.uses["no_sleep"] = [st.turn]
                if st.last_exp:
                    st.last_exp = dict(st.last_exp, turn=st.turn)   # "my mind keeps racing", "any tips?" still about the night
                x = tm.group("x").replace(" ", "")
                return Reply(msg, "smalltalk", self._pick(st, "daily:late_night", d["late_night"], x=x), via="empathy")
            if re.fullmatch(r"(?:and |but )?(?:i have|i've got|ive got|i got) (?:work|school|class|an exam|a meeting|an early start)"
                            r"(?: (?:tomorrow|in the morning|at \d+|early))*", n):
                st.uses["no_sleep"] = [st.turn]
                if st.last_exp:
                    st.last_exp = dict(st.last_exp, turn=st.turn)
                return Reply(msg, "smalltalk", self._pick(st, "daily:sleep_work", d["sleep_work"]), via="empathy")
        dm = re.fullmatch(r"(?:ugh,? |omg,? )?my (?P<x>phone|laptop|battery|computer|tablet|ipad|iphone|headphones)(?:'s| is| just)? (?:died|is dead|dead|ran out)"
                          r"(?: again| on me)?", n)
        if dm:
            st.uses["device_dead"] = [st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "daily:device_died", d["device_died"], x=dm.group("x")), via="smalltalk")
        if re.fullmatch(r"(?:and |but )?(?:i )?(?:can'?t|cannot|cant) find (?:my|the|a) (?:charger|cable|charging cable)", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:lost_charger", d["lost_charger"]), via="smalltalk")
        last = (st.last_reply or "").lower()
        if re.search(r"favou?rite colou?r\?|what'?s yours\?", last) and re.search(r"colou?r", " ".join(st.recent[-2:]).lower()):
            cm = re.fullmatch(r"(?:mine is|mine'?s|my favou?rite (?:one |colou?r )?is|it'?s|i like|i love)? ?(?P<c>[a-z]+(?: [a-z]+)?)", n)
            if cm and cm.group("c") in _COLOURS and (st.uses.get("user_colour") or [None, -1])[1] != st.turn:
                st.uses["user_colour"] = [cm.group("c"), st.turn]
                return self._turn(st, f"My favourite colour is {cm.group('c')}.")
        lc = re.fullmatch(r"(?:so |and )?do you (?:like|love) (?:the colou?r )?(?P<c>[a-z]+)", n)
        if lc and lc.group("c") in _COLOURS:
            return Reply(msg, "smalltalk", self._pick(st, "daily:color_like", d["color_like"], x=lc.group("c")), via="smalltalk")
        wm = re.fullmatch(r"(?:ugh,? |wow,? |omg,? )?(?:it'?s|its|it is) (?:so |really |super |very |freezing )?(?P<w>raining|pouring|cold|freezing|hot|"
                          r"boiling|snowing|sunny|so sunny)(?: (?:again|today|outside|here|out))*", n)
        if wm and "?" not in msg:
            key = {"raining": "rain", "pouring": "rain", "cold": "cold", "freezing": "cold", "hot": "hot", "boiling": "hot",
                   "snowing": "snow"}.get(wm.group("w"), "sun")
            st.uses["weather_talk"] = [key, st.turn]
            return Reply(msg, "smalltalk", self._pick(st, f"daily:weather:{key}", d["weather_talk"][key]), via="smalltalk")
        if recent("weather_talk", 2) and st.uses["weather_talk"][0] in ("rain", "cold", "snow") and \
                re.fullmatch(r"(?:and )?i (?:wanted|was going|was gonna|planned|was planning) to (?:go )?(?:for a |on a )?(?:run|jog|walk|bike ride|hike|go running|"
                             r"go out|go outside|play football|play tennis)\b.*", n):
            st.uses["weather_talk"] = [st.uses["weather_talk"][0], st.turn]
            st.uses["plan_moved"] = [st.turn]
            return Reply(msg, "smalltalk", self._pick(st, "daily:weather_plans", d["weather_plans"]), via="smalltalk")
        if recent("plan_moved", 2) and re.fullmatch(r"(?:ok |yeah )?(?:maybe |i'?ll go |i'?ll do it |probably )?tomorrow(?: then)?", n):
            return Reply(msg, "smalltalk", self._pick(st, "daily:maybe_tomorrow", d["maybe_tomorrow"]), via="smalltalk")
        mv = re.fullmatch(r"my (?P<w>best friend|friend|sister|brother|bff|best mate|neighbou?r|cousin|mom|mum|dad|daughter|son|roommate|flatmate) "
                          r"(?:is|'s) (?:moving|going) (?:away|abroad|to (?P<p>[a-z ]{3,30}))(?: (?P<t>next \w+|soon|in \w+ \w+|this \w+))?", n)
        if mv:
            st.uses["moving_away"] = [mv.group("w"), st.turn]
            if mv.group("p"):
                return Reply(msg, "smalltalk", self._pick(st, "daily:moving_where", d["moving_where"], x=_place_case(mv.group("p"))),
                             via="empathy")
            return Reply(msg, "smalltalk", self._pick(st, "daily:moving_away", d["moving_away"]), via="empathy")
        if recent("moving_away", 4):
            who = st.uses["moving_away"][0]
            wp = re.fullmatch(r"(?:to |she'?s moving to |he'?s moving to |they'?re moving to )(?P<p>[a-z ]{3,30})", n)
            if wp:
                st.uses["moving_away"] = [who, st.turn]
                return Reply(msg, "smalltalk", self._pick(st, "daily:moving_where", d["moving_where"], x=_place_case(wp.group("p"))),
                             via="empathy")
            if re.fullmatch(r"(?:in |like )?(?:next (?:week|month|year|summer|spring|autumn|fall|winter)|soon|in (?:a|two|three|few) (?:weeks?|months?|days?)|"
                            r"this (?:weekend|month|summer)|tomorrow)", n):
                st.uses["moving_away"] = [who, st.turn]
                return Reply(msg, "smalltalk", self._pick(st, "daily:moving_when", d["moving_when"]), via="empathy")
            if re.search(r"\b(?:miss (?:her|him|them|my \w+)|gonna be lonely|will be lonely|so sad)\b", n):
                return Reply(msg, "smalltalk", self._pick(st, "daily:moving_miss", d["moving_miss"]), via="empathy")
        return None

    def _daily_ctx11(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Battery 55: a film, book or artist becomes the topic ("i just finished reading 1984", "have you seen
        inception?"), so "who wrote it?", "what's it about?" and "any similar movies?" are about that work — never
        about Stephen King's "It"; a football score, the best player, and a depressing book."""
        d = self.bank.daily
        m = _SEEN.match(norm)
        verb = None
        if m:
            x, verb = m.group("x"), "seen"
        else:
            m = _MEDIA.match(norm)
            x, verb = (m.group("x"), m.group("v")) if m else (None, None)
        if x and not re.fullmatch(r"(?:it|that|this|them|him|her|a lot|so much|the news|the game|the match|tv|music)", x):
            kind = "music" if verb in ("listening to", "into") else "book" if verb and "read" in verb else \
                "film" if verb in ("watched", "saw", "watching", "seen") else None
            strict = verb in ("loved", "love", "liked", "really liked", "really loved")
            hit = self._work_entity(x, kind, strict=strict)
            if hit:
                title, kind = hit
                name = re.sub(r"\s*\([^)]*\)$", "", title)
                st.topic = {"title": title, "name": name, "turn": st.turn}
                st.uses["work"] = [title, name, kind, st.turn]
                self.bot.context.update({"answer": None, "atype": None, "mention": name, "kb_last": None})
                if verb == "seen":
                    return Reply(msg, "smalltalk", self._pick(st, "daily:work_seen", d["work_seen"], x=name), via="smalltalk")
                key = {"music": "work_music", "book": "work_book", "film": "work_film"}[kind]
                if verb in ("loved", "love", "liked", "really liked", "really loved", "listening to", "into"):
                    self._learn(st, [f"I like {name}."], msg)
                return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=name), via="empathy")
        wk = st.uses.get("work")
        if wk and st.turn - wk[3] <= 6:
            title, name, kind = wk[0], wk[1], wk[2]
            if _DEPRESSING.match(norm):
                wk[3] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:work_dark", d["work_dark"], x=name), via="empathy")
            if _IT_Q.match(norm) and not getattr(self, "_in_work_q", False):
                q2 = re.sub(r"\bit\b", name, msg, count=1, flags=re.I)
                rep = self._kb_answer(st, q2.rstrip("?") + "?")   # the fact bank first: "George Orwell", then "he" works
                mk = self._work_maker(title) if rep is None and re.match(r"(?:and |so )?who (?:wrote|directed|made|painted|composed)\b", norm) else None
                if mk:
                    who, src = mk
                    self.bot.context.update({"answer": who, "atype": "PERSON", "mention": who, "kb_last": None})
                    verb = re.search(r"\b(wrote|directed|made|painted|composed)\b", norm).group(1)
                    shown = {"wrote": "written", "made": "made", "painted": "painted", "composed": "composed", "directed": "directed"}[verb]
                    rep = Reply(msg, "answer", f"{name} was {shown} by {who}.", answer=who, source=src, via="about", confidence=0.8)
                if rep is None:
                    self._in_work_q = True
                    try:
                        rep = self._turn(st, q2)             # "who wrote it?" → "who wrote Nineteen Eighty-Four?"
                    finally:
                        self._in_work_q = False
                rep.message = msg
                wk[3] = st.turn
                return rep
            if _IT_ABOUT.match(norm.strip()):
                f = self.about.find(title)
                if f is not None:
                    wk[3] = st.turn
                    return self._about_reply(st, msg, f, "tell")
            if re.fullmatch(r"(?:so |but )?(?:should i|would you recommend|is it worth) (?:read|watch|see|listen to|reading|watching|"
                            r"seeing|listening to)?(?: it| that| this)?(?: book| film| movie)?\??|is it (?:good|worth it)\??", norm):
                wk[3] = st.turn
                return Reply(msg, "smalltalk", self._pick(st, "daily:work_should", d["work_should"], x=name), via="smalltalk")
            m = _SIMILAR.match(norm)
            if m:
                k = m.group("k") or ""
                rec = "book" if kind == "book" or k.startswith("book") else "music" if kind == "music" or k in (
                    "artists", "bands", "songs", "music") else "movie"
                genre = _LIKE_GENRE.get(name.lower())
                rep = self.everyday.recommend(st, msg, rec, genre)
                if "\n" in rep.text and genre:
                    body = "\n".join(l for l in rep.text.split("\n")[1:] if name.lower() not in l.lower())
                    rep.text = self._pick(st, "daily:like_title", d["like_title"], x=name) + "\n" + body
                return rep
        m = _SCORE.match(norm)
        if m and re.search(r"\b(?:game|match|watch|football|soccer)\b", (st.last_message or "").lower() + " " + (st.last_reply or "").lower()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:score_ack", d["score_ack"], x=m.group("t").title(),
                                                      y=(m.group("s") or "").replace("-", "–")), via="smalltalk")
        if _BEST_PLAYER.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:best_player", d["best_player"]), via="smalltalk")
        return None

    def _person_name(self, noun: str) -> str | None:
        for tx in self.bot.user_texts().values():
            m = re.match(rf"^My {re.escape(noun)} is called ([A-Z][\w'-]*)\.?$", tx)
            if m:
                return m.group(1)
        return None

    def _dish_steps(self, st: DialogState, msg: str, name: str) -> Reply:
        d = self.bank.daily
        dish = next(x for v in d["cuisine_ideas"].values() for x in v if x["name"] == name)
        st.uses.pop("dishes", None)
        st.last_action = {"kind": "howto", "title": name, "turn": st.turn}
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(dish["steps"], 1))
        return Reply(msg, "smalltalk", self._pick(st, "daily:dish_steps", d["dish_steps"], x=name, y=steps), via="everyday")

    @staticmethod
    def _week_items(norm: str) -> list[tuple[str, str]]:
        """"i have gym monday wednesday friday" → [("Monday", "gym"), …]; "a big presentation on thursday"."""
        days = []
        for m in _DAY_RX.finditer(norm):
            k = m.group(1)[:3]
            day = next(x for x in _DAYS if x.startswith(k))
            if day not in days:
                days.append(day)
        what = _DAY_RX.sub(" ", norm)
        what = re.sub(r"\b(?:i have|i've got|i got|ive got|i'?ve|i|have|got|and|also|plus|then|on|every|each|at|the|this|next|"
                      r"week|is|there'?s|a|an|my|in|morning|evening|afternoon|night)\b", " ", what)
        what = re.sub(r"[,.!]", " ", what)
        what = re.sub(r"\s+", " ", what).strip()
        if not what or not days or len(what.split()) > 6:
            return []
        return [(day.capitalize(), what) for day in days]

    def _week_text(self, st: DialogState, wk: dict, key: str) -> str:
        d = self.bank.daily
        by = {}
        for day, what in wk["items"]:
            by.setdefault(day, [])
            if what not in by[day]:
                by[day].append(what)
        order = [x.capitalize() for x in _DAYS]
        lines = "\n".join(f"• {day}: {', '.join(by[day])}" for day in order if day in by)
        big = next(((day, w) for day in order if day in by for w in by[day]
                    if any(re.search(rx, w) for _k, rx in _PREP_TOPICS)), None)
        if key == "plan_week_show" and big:
            return self._pick(st, "daily:plan_week_tip", d["plan_week_tip"], x=lines, y=f"the {big[1]} on {big[0]}")
        return self._pick(st, f"daily:{key}", d[key], x=lines)

    def _howto_follow(self, st: DialogState, text: str) -> Reply | None:
        """A question right after a guide ("how long do I cook them?", "do I need baking powder?"):
        answered from the guide's own steps, never from unrelated advice."""
        la = st.last_action or {}
        if st.turn - la.get("turn", -99) > 3:
            return None
        q = normalise(text).strip(" ?!.")
        if _HOWTO_Q.match(q):
            words_q = set(re.findall(r"[a-z']+", q))
            stems_q = {w.rstrip("s") for w in words_q} | words_q
            for g in self.bank.daily.get("howto", []):
                if g["title"] != la.get("title") and any(all(k in stems_q or k.rstrip("s") in stems_q for k in grp) for grp in g["keys"]):
                    return None                           # "can you help me make a budget?": another guide, not a follow-up
        if not re.match(r"(?:and |so |ok |okay |but |wait )?(?:how|what|do|does|can|should|is|are|when|which|"
                        r"for how|at what)\b", q) or len(q.split()) > 12 or \
                re.match(r"(?:and |so |ok |okay )?(?:how|what) about\b", q):
            return None                                   # "how about a walk": a new idea, not about the guide
        guide = next((g for g in self.bank.daily.get("howto", []) if g["title"] == la.get("title")), None)
        if guide is None:
            return None
        steps = guide["steps"]
        d = self.bank.daily
        sb = re.search(r"(?:don'?t|do not|didn'?t) have (?:any )?(?P<a>eggs?|milk|butter|baking powder|sugar|flour)|(?:instead of|replace|substitute(?: for)?|"
                       r"without|no) (?:the )?(?P<b>eggs?|milk|butter|baking powder|sugar|flour)", q)
        if sb:
            ing = (sb.group("a") or sb.group("b")).rstrip("s") if (sb.group("a") or sb.group("b")) != "baking powder" else "baking powder"
            if any(re.search(rf"\b{re.escape(ing)}", x, re.I) for x in steps) and ing in d["b75"]["subst"]:
                return Reply(text, "smalltalk", d["b75"]["subst"][ing], via="everyday")
        su = re.fullmatch(r"(?:and |so |but )?can (?:i|you|we) (?:use|take|do it with|make (?:it|them) with) (?P<x>oat milk|almond milk|soy milk|soya milk|plant milk|"
                          r"coconut milk|rice milk|oil|olive oil|margarine|whole ?wheat flour|wholemeal flour|spelt flour|gluten[- ]free flour|honey|"
                          r"brown sugar|maple syrup|water)(?: instead)?(?: of (?:the )?[a-z ]+)?", q)
        if su:
            return Reply(text, "smalltalk", self._pick(st, "daily:b86:sub_ok", d["b86"]["sub_ok"], x=su.group("x")), via="everyday")
        if guide.get("yield") and re.fullmatch(r"(?:and |so )?(?:how many (?:does (?:that|it|this|the recipe) make|(?:pancakes|portions|servings|people)(?: does (?:that|it) make| is (?:that|it) for)?)|"
                                               r"for how many (?:people|persons)|how many people (?:does (?:that|it) feed|is (?:that|it) for))", q):
            return Reply(text, "smalltalk", guide["yield"], via="everyday")
        if re.search(r"\bhow long\b|\bhow many (?:minutes|hours|seconds)\b|\bhow much time\b|\bwhen (?:do|should) i (?:flip|turn|take)", q):
            timed = [s for s in steps if re.search(r"\d\s*(?:[–-]\s*\d+\s*)?(?:minutes?|mins?|seconds?|hours?)\b", s)]
            if timed:
                return Reply(text, "smalltalk", self._pick(st, "daily:howto_step", d["howto_step"], x=timed[-1]), via="everyday")
        skip = {"i", "do", "does", "need", "how", "it", "them", "they", "the", "a", "an", "should", "can", "is", "are",
                "what", "when", "which", "and", "so", "ok", "okay", "but", "wait", "to", "use", "have", "my", "with",
                "much", "many", "long", "make", "cook", "really", "you", "of", "for", "in", "on", "or", "any", "about",
                "this", "that", "there", "then", "right", "just", "well", "good", "okay"}
        qw = [w for w in re.findall(r"[a-z]+", q) if w not in skip and len(w) > 2]
        if not qw:
            return None
        def score(s):
            sw = set(re.findall(r"[a-z]+", s.lower()))
            return sum(1 for w in qw if w in sw or w.rstrip("s") in sw or w + "s" in sw)
        best = max(steps, key=score)
        need = re.match(r"(?:and |so |but )?(?:do|does|should|can|must) (?:i|you|we)\b", q)
        if score(best) == 0:
            if need:
                return Reply(text, "smalltalk", self._pick(st, "daily:howto_not_in", d["howto_not_in"], x=" ".join(qw)),
                             via="everyday")
            return None
        key = "howto_yes" if need else "howto_step"
        return Reply(text, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=best), via="everyday")

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
        if adj is None and self.kgqa is not None:         # "what should I eat in Paris?": the country's cuisine
            try:
                row = self.kgqa.kb.db.execute(
                    "SELECT f.value FROM entity e JOIN fact f ON f.entity = e.id WHERE e.title = ? AND f.prop = 'country' "
                    "AND f.value != '' LIMIT 1", (_place_case(place),)).fetchone()
            except Exception:                           # a damaged fact bank must not break the chat
                row = None
            if row:
                adj = _CUISINE_ADJ.get(str(row[0]).lower())
        names = ([f"{adj} cuisine"] if adj else []) + [f"Cuisine of {place}"]
        for name in names:
            found = self.about.find(name, n=2)
            if found is not None and found.sentences:
                st.last_about = {"title": found.title, "doc": found.doc, "next": found.next_sentence,
                                 "end": found.end_sentence, "source": found.source}
                lead = self._pick(st, "daily:cuisine_lead", self.bank.daily["cuisine_lead"], x=_place_case(place) if place.islower() else place)
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
            if what != "it" and not re.fullmatch(r"(?:the|a|an|that|this|my|your|his|her|their|our) [a-z]+", what):
                # "have you seen inception?": Inception is now what "it" means ("the game" stays a game)
                small = {"of", "the", "a", "an", "and", "in", "on", "to", "for", "at", "by"}
                what = " ".join(w if (w in small and i) or not w.islower() else w.capitalize() for i, w in enumerate(what.split()))
                self.bot.context.update({"answer": None, "atype": None, "mention": what, "kb_last": None})
                st.topic = {"title": what, "name": what, "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_experience", d["bot_experience"],
                                                      x=_VERB_BASE.get(m.group("v"), m.group("v")), topic=what),
                         via="smalltalk")
        if _BOT_LIMIT.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_limit", d["bot_limit"]), via="smalltalk")
        if _WHERE_WERE_WE.match(norm):
            themes = st.uses.get("recap", [])
            if themes:
                last = "what you told me about yourself" if themes[-1] == "things about you" else themes[-1]
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

    def _holiday(self, st: DialogState, text: str, name: str) -> Reply:
        """"What day is Christmas this year?": a fixed-date holiday on this computer's calendar."""
        now = self.clock() if self.clock else dt.datetime.now()
        month, day, shown = _HOLIDAYS[name]
        when = dt.date(now.year, month, day)
        if when < now.date():
            when = dt.date(now.year + 1, month, day)
        days = (when - now.date()).days
        text_out = f"{shown} is on {when:%A}, {when.day} {when:%B} {when.year}"
        text_out += " — that's today! 🎉" if days == 0 else f" — {days} day{'s' if days != 1 else ''} from now."
        return Reply(text, "tool", text_out, answer=f"{when.day} {when:%B} {when.year}", via="tool", confidence=1.0)

    @staticmethod
    def _day_tasks(norm: str) -> list[str]:
        """"i need to work, go to the gym and cook" → ["work", "go to the gym", "cook"]."""
        s = re.sub(r"^(?:ok |okay |so |well )?(?:i (?:need|have|want|got) to|i(?:'ve| have) got to|i gotta|i must|i should|"
                   r"today i (?:need|have) to|my plans are|i'm going to|im going to)\s+", "", norm.strip(" .!"))
        parts = [x.strip(" .") for x in re.split(r",\s*(?:and\s+|then\s+)?|\s+and then\s+|\s+then\s+|\s+and\s+|;", s) if x.strip(" .")]
        return [re.sub(r"^(?:to|also|maybe)\s+", "", x) for x in parts if 0 < len(x.split()) <= 8]

    def _common_fact(self, st: DialogState, text: str) -> Reply | None:
        """"How many continents are there?", "is a tomato a fruit?": a short list of everyday facts checked
        by hand (data/conv/daily.yaml `common`), because the text look-up gets exactly these wrong
        ("two continents", "Sweet")."""
        q = normalise(text).strip(" ?!.")
        ct = st.uses.get("common_then")
        if ct and st.turn - ct[1] <= 3 and re.fullmatch(r"(?:and |so )?how old (?:was|were) (?:he|she|they)(?: (?:then|at the time|back then|"
                                                         r"when (?:he|she|they) did (?:it|that)|at that time))?", q):
            return Reply(text, "answer", ct[0], answer=ct[0], source={"kind": "common", "source": "everyday facts", "key": ""},
                         confidence=1.0, via="common")   # "how old was he then?" after the first man on the moon
        cf = st.uses.get("common_follow")
        if cf and st.turn - cf[1] <= 4:                   # "why did it fall?" after the Berlin Wall
            for f in cf[0]:
                if re.fullmatch(f["q"], q):
                    cf[1] = st.turn
                    if getattr(st, "lang", None) == "de" and f.get("de"):
                        return Reply(text, "answer", f["de"], answer=f["de"], source={"kind": "common", "source": "everyday facts",
                                                                                        "key": ""}, confidence=1.0, via="german")
                    return Reply(text, "answer", f["a"], answer=f["a"], source={"kind": "common", "source": "everyday facts",
                                                                                  "key": ""}, confidence=1.0, via="common")
        tp = st.topic if st.topic and st.turn - st.topic.get("turn", -99) <= 4 else None
        tries = [q]
        if re.search(r"\b(?:he|she|it|they)\b", q):        # "when did he paint it?" after the painter of The Starry Night
            rq = normalise(self.bot.resolve(text)).strip(" ?!.")
            if rq != q:
                tries.append(rq.lower())
        if tp and re.search(r"\b(?:it|there)\b", q):         # "who was the first person on it?" after the Moon
            tries.append(re.sub(r"\b(?:it|there)\b", tp["name"].lower(), q, count=1))
        if re.search(r"\bthe (?:painting|picture|statue|building|tower|book|film|movie)\b", q):
            for name in reversed(st.uses.get("recap", [])[-4:]):   # "where is the painting now?" after the Mona Lisa
                tries.append(re.sub(r"\bthe (?:painting|picture|statue|building|tower|book|film|movie)\b", name.lower(), q, count=1))
        item = next((it for q in tries for it in self.bank.daily.get("common", []) if re.fullmatch(it["q"], q)), None)
        if item is None:
            return None
        if item.get("follow"):
            st.uses["common_follow"] = [item["follow"], st.turn]
        src = {"kind": "common", "source": "everyday facts", "key": item.get("key", "")}
        if item.get("t"):                         # a person or thing: "when was he born?" follows on from it
            self.bot.context.update({"answer": item["t"], "atype": None, "mention": item["t"], "kb_last": None})
            st.topic = {"title": item["t"], "name": item["t"], "turn": st.turn}
        if item.get("then"):
            st.uses["common_then"] = [item["then"], st.turn]
        if item.get("when"):
            st.uses["common_when"] = [item["when"], st.turn]
        if item.get("first"):
            st.uses["common_first"] = [item["first"], st.turn]
        if getattr(st, "lang", None) == "de" and item.get("de"):
            return Reply(text, "answer", item["de"], answer=item.get("v", item["de"]), source=src, confidence=1.0, via="german")
        return Reply(text, "answer", item["a"], answer=item.get("v", item["a"]), source=src, confidence=1.0, via="common")

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
        if re.search(r"\b(?:wrote|written|directed|made|painted|sang|sung|composed|built|designed|invented|created|founded|produced|"
                     r"published|filmed) it\b(?! (?:by|was))", q):
            return None                                   # "who wrote it?": a pronoun, never Stephen King's novel "It"
        nq = normalise(q).strip(" ?!.").lower()
        if any(it.get("pre") and re.fullmatch(it["q"], nq) for it in self.bank.daily.get("common", [])):
            return self._common_fact(st, q)               # a hand-checked fact the infobox gets half right (Eiffel Tower: one architect)
        try:
            ans = self.kgqa.answer(q)
        except Exception:                       # a damaged fact bank must not break the chat
            return None
        if ans is None:
            return None
        value = _join_values(ans.values)
        src = {"kind": "kb", "source": "dbpedia", "key": ans.entity.title}
        atype = _atype(q)
        nm = ans.entity.name
        if len(nm.split()) == 1 and ans.text.startswith(nm + " ") and re.search(rf"\bthe {re.escape(nm.lower())}\b", q) \
                and self.speller is not None and self.speller.known(nm.lower()):
            ans.text = f"The {nm.lower()}{ans.text[len(nm):]}"   # "The telephone was invented by …", not "Telephone was …"
        work = ans.evidence.split(" — notable work: ", 1)[1] if ans.prop == "notableWork" and " — notable work: " in ans.evidence else None
        if work:                                          # "who painted the starry night?": "it" is the painting, "he" the painter
            atype = "PERSON"
        main = None
        if len(ans.values) > 1 and atype == "PERSON":
            try:                                          # "invented by Meucci, Gray, Bell and Reis": Bell is by far the best known
                pops = [(self.kgqa.kb.db.execute("SELECT MAX(popularity) FROM entity WHERE title = ?", (v,)).fetchone()[0] or 0, v)
                        for v in ans.values[:6]]
                pops.sort(reverse=True)
                if pops[0][0] > 0 and pops[0][0] >= 2 * pops[1][0]:
                    main = pops[0][1]
            except Exception:
                main = None
        if main:
            ans.text = ans.text.rstrip() + f" The best known of them is {main}."
        self.bot.context.update({"answer": main or (ans.values[0] if len(ans.values) == 1 else None), "atype": atype,
                                 "mention": work or ans.entity.name,
                                 "many_people": [ans.entity.name, ans.values[:6]] if len(ans.values) > 1 and atype == "PERSON" and not main else None})
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
        if new.split()[0].lower() in _QUESTION_WORDS:
            return None                                   # "and when was it built?" is a whole question, not "and Germany?"
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
        if not m:
            m = _CORRECT_IT.match(msg.strip().lower())   # "actually no, it's risotto" right after a favourite
            if m and _NOT_A_NAME.search(m.group("x")):
                m = None                                  # "no, it's fine": no new favourite
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
            if kind == "define":                           # "what does dna stand for?" without an article: the hand-checked facts
                common = self._common_fact(st, u.text)
                if common is not None:
                    return common
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
            if len(what.split()) <= 3 and (what.lower() in _CONTINENTS or self._is_place(what)):
                head = _place_case(what)              # "South America", not "South america"
            big = re.match(r"(?:quit|quitting|leav|break|divorc|drop|mov|resign|sell|end|stop)", what.lower())
            st.last_exp = {"valence": "plan", "topic": what, "person": False, "text": u.text, "turn": st.turn}
            key = "plan_big" if big else "plan"
            return self._pick(st, f"daily:{key}", self.bank.daily[key], x=head)
        return self._pick(st, "daily:plan_plain", self.bank.daily["plan_plain"])

    def _entity_kind(self, name: str) -> str | None:
        """"thing", "female", "male" or None, from the opening of the article about ``name``."""
        if not name:
            return None
        key = name.lower()
        if key in self._kind_cache:
            return self._kind_cache[key]
        kind = None
        try:
            found = self.about.find(name, n=5)
        except Exception:
            found = None
        if found is not None and found.sentences:
            text = " ".join(found.sentences)
            if re.search(r"\b(?:is|was) an? (?:\d{4} )?(?:[\w'-]+ ){0,4}(?:novel|book|film|movie|album|song|single|series|sitcom|"
                         r"video game|game|play|opera|musical|painting|poem|company|corporation|band|group|city|town|country|"
                         r"river|mountain|building|tower|bridge|brand|franchise|newspaper|magazine|website|organi[sz]ation|"
                         r"university|school|team|club|ship|car|language|religion|empire|kingdom|island|lake|church)\b", text[:400]):
                kind = "thing"
            else:
                she = len(re.findall(r"\b(?:she|her|hers|herself)\b", text, re.I))
                he = len(re.findall(r"\b(?:he|his|him|himself)\b", text, re.I))
                kind = "female" if she > he else "male" if he > she else None
        self._kind_cache[key] = kind
        return kind

    def _gender(self, name: str) -> str | None:
        k = self._entity_kind(name)
        return k if k in ("female", "male") else None

    def _not_a_person(self, name: str) -> bool:
        """True when the fact bank or the reading knows ``name`` as a work, place, organisation or thing
        (not a person); unknown names count as possible persons."""
        if self._entity_kind(name) == "thing":
            return True
        if self.kgqa is None or not name:
            return False
        try:
            hits = self.kgqa.kb.link(name, limit=1)
        except Exception:
            return False
        if not hits:
            return False
        ent = hits[0][0]
        typ = ent.type or ""
        if typ in _PERSON_TYPES:
            return False
        return bool(typ) and ent.title.lower().startswith(name.lower()[:6])

    def _is_place(self, name: str) -> bool:
        """A place the fact bank knows ("berlin", "south korea")."""
        if self.kgqa is None:
            return False
        try:
            hits = self.kgqa.kb.link(name, limit=1)
        except Exception:
            return False
        return bool(hits) and (hits[0][0].type or "") in _PLACE_TYPES

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
        single = {"#home", "#job", "#employer"}
        new_keys = {(f.subject, c) for f in fs for c in set(f.relation) & single if f.subject == USER}
        if new_keys:
            # "I live in Munich" after "I live in Hamburg": the new home replaces the old one, like a person updates it
            stale = {f.source for f in bot.facts.facts if f.source != sid and f.source.startswith(CHAT_PREFIX) and
                     any((f.subject, c) in new_keys for c in set(f.relation) & single) and
                     len([g for g in bot.facts.facts if g.source == f.source]) == 1}
            for old_sid in stale:
                try:
                    bot.memory.forget(old_sid)
                except Exception:
                    pass
            if stale:
                bot.refresh()
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
        dr = st.uses.get("dream")
        if dr is not None and st.turn - dr <= 2 and not re.search(r"\b(?:you|your)\b", norm):
            st.uses.pop("dream", None)
            return self._pick(st, "daily:talk_dream_more", d["talk_dream_more"])
        for rx, key in _TALK_RULES:
            if rx.search(norm):
                if key == "talk_dream":
                    st.uses["dream"] = st.turn
                if key == "talk_hungry":
                    st.uses["food_ctx"] = st.turn
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
                cue = {"food": r"\b(?:like|likes|love|loves|favou?rite|enjoy|eat|eats|eating|prefer|best|fan|adore|crave|craving|go-to)\b",
                       "colour": r"\b(?:colou?rs?|favou?rite|like|love|prefer)\b",
                       "car": r"\b(?:drive|drives|driving|car|own|owns|bought|have|has|got)\b",
                       "fav": r"\b(?:like|likes|love|loves|favou?rite|enjoy|enjoys|adore|prefer|fan|into|obsessed|crazy about|best|nothing beats)\b"}.get(cat)
                if cue and not re.search(cue, f.sentence or "", re.I):
                    cat = None                         # "my soup is too salty" names no favourite food: a plain confirmation
                if cat == "name":
                    key = "learned.name_changed" if name_before and name_before.lower() != f.object.lower() else "learned.name_new"
                    shown = " ".join(w[:1].upper() + w[1:] if w.islower() else w for w in f.object.split())
                    out.append(self._reply(st, key, x=shown))
                elif cat:
                    x = article(f.object) if cat in ("job",) else f.object
                    if cat == "car":
                        x = f.object
                    if cat == "employer":
                        am = re.search(rf"\b(?:at|for|in) (a|an|the) {re.escape(f.object)}\b", f.sentence or "", re.I)
                        if am:
                            x = am.group(1).lower() + " " + f.object   # "you work at a bakery", as said
                        elif f.object.islower() and f.object not in ("myself", "home", "me", "them", "him", "her", "us", "it") \
                                and not re.search(rf"\b(?:a|an|the|my|our) {re.escape(f.object)}\b", f.sentence or "", re.I):
                            x = " ".join(w.capitalize() for w in f.object.split())   # "i work for google": Google
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
            name = re.sub(r"^(?:i mean|i meant|meant|it's|its|he's|she's|the one called|the)\s+", "", name, flags=re.I)
            mp = (pending.get("many") or [])
            pick = [p for p in mp if re.search(rf"\b{re.escape(name)}\b", p, re.I)]
            if len(pick) == 1:
                name = pick[0]                   # "bell" after "Meucci, Gray, Bell or Reis?": Alexander Graham Bell
            pron = pending.get("pron", "he")
            poss = pron.lower() in ("his", "their", "hers") or (
                pron.lower() == "her" and re.search(r"\bher\s+[a-z]", pending.get("question", ""), re.I))
            q = re.sub(rf"\b{re.escape(pron)}\b", name + ("'s" if poss else ""), pending.get("question", ""),
                       count=1, flags=re.I)
            self._spelled = q
            st.uses.pop("person_gap", None)
            if pending.get("lang") == "de":
                rep = self._german_question(st, q, q)
                if rep is not None:
                    return rep
            return self._question(st, q)
        value = _slot_value(msg, slot)
        if value is None:
            return None
        if slot in ("home", "origin", "name") and value.islower():
            # "berlin" → "Berlin", "new york" → "New York", "frankfurt am main" keeps "am"
            value = " ".join(w if w in ("am", "an", "der", "de", "la", "le", "of", "on", "upon", "del", "da", "di")
                             else w[:1].upper() + w[1:] for w in value.split())
        if slot == "draft_detail":                       # "to my landlord, the heating is broken" after "who's it for?"
            from engramm.chat import writing as w
            g = pending.get("genre") or "email"
            art = "an" if g[:1] in "aeiou" else "a"
            v = re.sub(r"^(?:it'?s |its |it is |the (?:email|message|letter) is )", "", msg.strip().rstrip(".!"), flags=re.I)
            m = re.match(r"(?i)^(?:for|to) (?P<r>.+?)(?:,| about| that| saying| because| -|:) +(?P<p>.+)$", v)
            if m:
                req_text = f"write {art} {g} to {m.group('r')} that {m.group('p')}"
            elif re.match(r"(?i)^(?:for|to) ", v):
                req_text = f"write {art} {g} {'to ' + v[3:].strip() if v.lower().startswith('for ') else v}"
            else:
                req_text = f"write {art} {g} about {v}"
            req = w.parse_request(req_text, self.bank.writing["purposes"])
            if req is not None:
                return self._show_draft(st, msg, req, intro=True)
            return None
        if slot == "correction" and pending.get("force"):
            if re.fullmatch(r"(?:yes|yeah|yep|sure|please|yes please|do it|remember it|ok|okay)[!. ]*", value.strip().lower()):
                value = pending.get("value") or value
            else:
                return None                               # "no, you're right": nothing to store
        if slot == "correction":
            q = pending.get("question") or ""
            value = re.sub(r"^(?:no,? |nope,? |actually,? |well,? )?(?:it's|its|it is|it was|that's|thats|that is|"
                           r"the (?:right |correct )?answer is|the ceo is|he is|she is|they are)\s+", "", value.strip(),
                           flags=re.I).strip(" .!")
            if value.islower() and (re.match(r"^\s*(?:who|where|in which (?:city|country|town))\b", q, re.I) or
                                    re.search(r"\b(?:capital|city|country|president|author|ceo|founder)\b", q, re.I)):
                value = " ".join(w[:1].upper() + w[1:] for w in value.split())
            lf = st.last_fact or {}
            if lf.get("sure") and lf.get("answer") and lf.get("question") == q and not pending.get("force") and \
                    value.lower() != str(lf["answer"]).lower():
                # a "correction" of a sourced fact ("it's sydney" after Canberra): say so kindly, store only on "yes"
                st.pending = {"slot": "correction", "question": q, "force": True, "value": value, "turn": st.turn}
                return Reply(msg, "smalltalk", self._pick(st, "daily:correction_doubt", self.bank.daily["correction_doubt"],
                                                          x=value, y=lf["answer"]), via="smalltalk")
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
        if le and st.turn - le.get("turn", -99) <= 2 and re.match(r"(?:yeah|yes|yep|ya|yup|totally|exactly|it did|it really did)\b", u.norm):
            key = "exp_agree_neg" if le.get("valence") == "negative" else "exp_agree_pos"     # "yeah it hurt"
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
    if fmt.get("X") is None and fmt.get("x") is not None:
        x = str(fmt["x"])
        fmt["X"] = x[:1].upper() + x[1:]                 # "{X}" opens a sentence with the same value
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
_COVER_ALT = {"tall": ("high", "height", "elevation", "stands"), "high": ("height", "elevation", "tall", "altitude"),
              "die": ("died", "death", "dead"), "died": ("die", "death", "dead"), "born": ("birth", "née"),
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
    fo = re.search(r"\b(?:father|mother|founder|king|queen|godfather|grandfather|inventor|pioneer) of (?:the |modern )?(?P<x>[a-z]+)", q, re.I)
    if fo and not re.search(rf"\b{re.escape(fo.group('x')[:6])}", evidence, re.I):
        return True                                   # "father of computers" ← "the father of pragmatism"
    hm = re.match(r"^\s*how many (?P<n>[a-z]+)", q, re.I)
    if hm and re.search(rf"\b(?:the|these|those|both) {re.escape(answer)} {re.escape(hm.group('n').rstrip('s'))}", evidence, re.I):
        return True                                   # "the two countries are EU members" counts a pair, not the EU
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
_HONOUR = re.compile(r"^(?:and |so |guess what,? )?i(?:'m| am| was| got asked to be| was asked to be|'m going to be| am going to be|'m gonna be|"
                     r"'ll be| will be) (?:the |a |his |her )?"
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
_CORRECT_IT = re.compile(r"^(?:actually|no|nope|wait|sorry|oops|my bad|i mean|i meant)(?:[, ]+(?:no|nope|wait|sorry|actually|"
                         r"i mean|i meant))*[, ]+(?:it'?s|its|it is|i mean|i meant|make that|change (?:that|it) to)?\s*"
                         r"(?P<x>[a-z][a-z' -]{1,30}?)(?: actually| instead| now| not that)?[.!]*$")
_FAV_NOUN = {"#food": "food", "#colour": "colour", "#car": "car"}
_HI_IM = re.compile(r"^((?:hi|hey|hello|yo|heya|hiya|hallo)[,!.]*\s+(?:i'?m|im|i am|it'?s|this is)\s+)([a-z][a-z'-]+)[.!]*$", re.I)
# words that follow "I'm" / "it's" but are never a name (both former lists, merged: the second used to replace the first)
_NOT_NAMES = frozenset(("back", "home", "here", "new", "fine", "good", "ok", "okay", "great", "well", "done", "bored", "tired",
                        "sad", "happy", "free", "busy", "sick", "ill", "hungry", "lost", "late", "early", "ready", "sorry",
                        "confused", "stuck", "curious", "alone", "awake", "up", "out", "in", "off", "on", "so", "just")) | \
    frozenset("""hard easy fine good great ok okay okey tired bored busy sorry sure done ready here back home
fun nice cool weird funny late early true right wrong bad sad happy hungry sick ill cold hot fair difficult tough boring
alright annoying awful amazing everything nothing something complicated serious real okish""".split())
_NAME_CUE = re.compile(r"\b((?:my name is|my name's|call me|i'm called|i am called|actually my name is) )"
                       r"([a-z][a-z'-]+(?: [a-z][a-z'-]+)?)\b(?=[.!,]|$)")
_PLACE_CUE = re.compile(r"\b((?:live in|living in|moved to|move to|moving to|from|born in|grew up in|based in|"
                        r"lives in|visited|went to|stay in|staying in) )([a-z][a-z' -]{1,40})")
_PERSON_TYPES = frozenset(("Person", "Artist", "MusicalArtist", "Athlete", "SoccerPlayer", "Politician", "Scientist",
                           "Writer", "Actor", "OfficeHolder", "Royalty", "Monarch", "Philosopher", "Painter", "Model",
                           "BasketballPlayer", "TennisPlayer", "Comedian", "Journalist", "Cleric", "Saint", "Astronaut",
                           "MilitaryPerson", "Engineer", "Economist", "Architect", "Chef", "Director", "Musician"))
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
                      r"what should i (?:wear|do) (?:to|for|about)|any tips (?:on|for) |tips for |how (?:do|can) i get rid of|"
                      r"what (?:helps|can help|is good|works) (?:with|against|for)|what can i do (?:about|against|for)|"
                      r"any (?:tips|advice|ideas) (?:to|on how to|how to)|tips (?:to|on how to)|(?:can|could) you help me "
                      r"(?:make|create|set up|plan|do|write) (?:a |my )?(?:budget|savings plan))\b")
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
_SELF_JOIN = re.compile(r"^((?:(?:hey|hi|hello|yo|hiya)[,!.]*\s+)?(?:my name is|my name's|i'm|im|i am|call me)\s+[A-Za-z][\w'-]*)\s*(?:,\s*|\s+)and\s+"
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
                      r"do another(?: one)?|more|any others?|anything else|any more|anymore|got any others?|what else|others?|"
                      r"(?:ok(?:ay)?,? )?(?:the |a )?last one|one last (?:one|time)|something else|hit me(?: again)?|keep (?:them|em) coming)(?: please)?\??$")
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


def _join_or(names: list[str]) -> str:
    names = [n for n in names if n]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " or " + names[-1]


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
    if re.search(r"\ballerg", low):
        return "#allergy"
    if re.search(r"\b(?:live|living) with\b", low):
        return "#housemate"
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


def _de_month_year(text: str) -> str:
    """"December 2022" → "Dezember 2022"."""
    en = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
    de = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")
    for a, b in zip(en, de):
        text = text.replace(a, b)
    return text


def _de_place_case(x: str) -> str:
    """"münchen" → "München", "new york" → "New York"."""
    return " ".join(w[:1].upper() + w[1:] for w in x.strip().split())


def _de_country(name: str) -> str:
    """An English country name in German ("Germany" → "Deutschland"), else as it is."""
    from engramm.chat.german_bridge import EXONYMS
    if name == "United States":
        return "die Vereinigten Staaten"
    for de_name, en in EXONYMS.items():
        if en == name and " " not in de_name and de_name not in ("usa", "amerika", "holland"):
            return _de_place_case(de_name)
    return name


def normalise_de_text(text: str) -> str:
    from engramm.chat.german import normalise_de
    return normalise_de(text)


def _ordinal_pick(norm: str, names: list[str]) -> str | None:
    m = re.search(r"\b(?:the )?(first|1st|second|2nd|third|3rd|last)(?: one)?\b", norm)
    if not m:
        return None
    idx = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2, "last": -1}[m.group(1)]
    try:
        return names[idx]
    except IndexError:
        return None


def _cuisine_case(x: str) -> str:
    """"italian food" → "Italian food": nationality adjectives keep their capital."""
    return re.sub(r"\b(italian|mexican|indian|japanese|chinese|thai|greek|french|spanish|korean|vietnamese|turkish|lebanese)\b",
                  lambda m: m.group(1).capitalize(), x)


def _user_answer_text(answer: str, evidence: str | None) -> str:
    if evidence:
        flipped = to_second_person(evidence)
        if flipped and answer and answer.lower() in flipped.lower():
            return flipped
        return f"{answer} — you told me: “{evidence}”"
    return f"{answer}."


_SLOT_STRIP = re.compile(r"^(?:(?:well|so|oh|ok|okay|sure|yes|yeah|um+|uh+|hmm+)[,!.]?\s+)*"
                         r"(?:it's|its|it is|that's|thats|that is|i'm|im|i am|i'm called|im called|my name is|my name's|my names|"
                         r"the name's|the name is|"
                         r"call me|you can call me|just call me|i live in|i'm from|i am from|in|i work as|i'm a|i am a|"
                         r"i am an|i'm an|i like|i love|i enjoy|my favou?rite (?:food|colou?r) is|i have)\s+", re.I)


_NOT_A_NAME = re.compile(r"\b(?:not|doing|feeling|feel|good|great|fine|ok|okay|alright|bad|sad|tired|happy|so|very|"
                         r"really|well|busy|bored|sick|ill|stressed|excited|thanks|thank|hungry|here|back|sure|sorry|"
                         r"just|kinda|pretty|awful|terrible|meh|exhausted|upset|angry|lonely|nervous|was|is|are|am|"
                         r"his|her|their|its|my|your|the|a|an|hard|easy|difficult|complicated|simple|late|early|cold|hot|"
                         r"raining|sunny|boring|weird|funny|crazy|true|wrong|right|over|done|nothing|everything|enough|"
                         r"impossible|possible|serious|complicated|annoying|amazing|awesome|cool|nice|lovely|perfect)\b", re.I)


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
