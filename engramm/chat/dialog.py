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
               "pride and prejudice": "romance", "the notebook": "romance", "toy story": "animation", "shrek": "animation"}
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
                     r"what(?:'s| is) on my (?:list|to-?do list)|what did i ask you to remind me(?: of| about)?)(?: today| later| again)?\??$")
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
_NOT_NAMES = frozenset("""hard easy fine good great ok okay okey tired bored busy sorry sure done ready here back home
fun nice cool weird funny late early true right wrong bad sad happy hungry sick ill cold hot fair difficult tough boring
alright annoying awful amazing everything nothing something complicated serious real okish""".split())
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
        lead = re.sub(r"^(?:(?:haha+|hihi+|hehe+|lol|ok(?:ay)?|na gut|gut|cool|super|alles klar|achso|ach so|krass|echt|witzig)[ ,!.]+)+", "", s)
        if lead != s and len(lead.split()) >= 3:          # "haha ok, was ist die hauptstadt von kanada?": the question
            msg, s = lead, lead
        u = understand(msg, de)
        name = self.user_name()
        known = self.speller.known if self.speller is not None else None
        if u.kind not in ("safety", "remember", "ask_name", "calc", "intent") and gibberish(msg, known):
            return Reply(msg, "unknown", self._pick(st, "de:gib", dd["gibberish"]), via="gibberish")
        if u.kind != "safety":
            life = self._german_ctx(st, msg, s) or self._german_life(st, msg, s)
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
        if le and st.turn - le.get("turn", -99) <= 2 and len(s.split()) >= 2:
            # "die nachbarn waren laut" after "ich bin müde": more of the same moment
            key = "follow_neg" if le.get("valence") == "negative" else "follow_pos"
            st.last_exp = dict(le, turn=st.turn, text_en=(le.get("text_en") or "") + " " + _de_advice_hint(s))
            return Reply(msg, "empathy", self._pick(st, f"de:life:{key}", dd["life"][key]), via="german")
        return Reply(msg, "unknown", self._pick(st, "de:fallback", de["replies"]["fallback"]), via="german")

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
        if m:
            word = m.group("x") or m.group("y")
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
        if off and st.turn - off[1] <= 1 and re.fullmatch(r"(?:ja|jo|jap|gerne?|klar|ok(?:ay)?|bitte|ja bitte|ja gerne?)?[, ]*(?:ideen|ein paar ideen|ideen bitte|gib mir ideen)?(?: bitte)?", s) and s:
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
        if ment and re.search(r"\b(?:leben|wohnen) (?:da|dort)\b|\b(?:da|dort) (?:leben|wohnen)\b", s):
            s = re.sub(r"\bwie viele (?:leute|menschen) (?:leben|wohnen) (?:da|dort)\b", f"wie viele einwohner hat {ment.lower()}", s)
        if ment and re.search(r"\b(?:hat|ist|liegt|wurde|war|heißt) (?:sie|er|es|ihn)\b|\b(?:sie|er|es) (?:hat|ist|liegt)\b", s) and \
                not re.search(r"\bgeboren|gestorben\b", s):
            # "und wie viele einwohner hat sie?" after Canberra, "wer hat ihn entworfen?" after the Eiffel Tower
            s = re.sub(r"\b(?:sie|er|es|ihn)\b", ment.lower(), s, count=1)
        hit = to_english(s)
        if hit is None:
            return None
        english, kind, x_en, x_de = hit
        st.uses["de_last_q"] = [st.turn, s, (x_de or "").lower()]
        names = st.uses.setdefault("de_names", {})
        if x_de and x_de.lower() != x_en.lower() and x_en.lower() not in ("he", "she", "it", "him", "her"):
            art = re.search(rf"\b(der|die|das) {re.escape(x_de.lower())}\b", s)
            names[x_en.lower()] = [x_de, art.group(1) if art else ""]     # "der Eiffelturm", for the follow-ups
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
            article = ""
            if x_de and x_de.lower() != x_en.lower() and x_en.lower() == name.lower() and \
                    x_en.lower() not in ("he", "she", "it", "him", "her"):
                name = x_de                     # "Frankreich", as the user wrote it
            known_de = names.get(name.lower())
            if known_de:                        # "Eiffel Tower" in a follow-up: the German name from before
                name, article = known_de[0], known_de[1]
            elif names.get(x_en.lower()):
                article = names[x_en.lower()][1]
            sent = de_sentence(kind, name, rep.answer or "", rep.text)
            if sent:
                if article and sent.startswith(name):
                    sent = article[:1].upper() + article[1:] + " " + sent    # "Der Eiffelturm ist 330 m hoch."
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
        if rep.text and rep.kind in ("answer", "about", "tool") and rep.text in st.recent and len(rep.text) > 80 and \
                rep.via not in ("facts", "memory", "facts-bank") and normalise(message) != normalise(st.last_message or ""):
            # the same answer again (the question came up twice): said like a person, not a copy
            lead = self._pick(st, "daily:again_lead", self.bank.daily["again_lead"])
            rep.text = lead + rep.text[:1].lower() + rep.text[1:] if rep.text[:2] not in ("I ", "I'") else lead + rep.text
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
                       r"neighbou?r|niece|nephew|fiancée?)\b(?!'s)", message.lower())
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
        lead = re.match(r"^(?:ok(?:ay)?,?\s+)?(?:whatever|anyways?|moving on|never ?mind|nvm|enough of that|forget (?:it|that)|"
                        r"ok(?:ay)? then|alright then|fine then)[,.!]*\s+(?=\S+\s+\S)", msg, re.I)
        if lead:
            msg = msg[lead.end():]                        # "ok whatever, tell me a joke": the request
        if self.speller is not None and "?" not in msg:
            msg = self._fix_typos(msg)                    # "a job interveiw tomorow": the words meant, before learning
        react = re.match(r"^(?:cool|nice|wow|great|interesting|ok|okay|oh|ah|haha|lol|thanks|thank you|neat|awesome)[,!.]+\s+"
                         r"(?=(?:who|what|when|where|why|how|which|is|are|was|were|do|does|did|can|could|tell)\b)", msg, re.I)
        if react:
            msg = msg[react.end():]                       # "cool, how big is mars?": the question
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
        return None

    def _fix_typos(self, msg: str) -> str:
        """Typos in a statement ("interveiw", "recieve"): a lowercase word of five letters or more that the
        speller does not know, replaced by the known word it is closest to — never a name after "I'm",
        "called" or "my name is", and never a capitalised word."""
        toks = msg.split(" ")
        out = []
        for i, tok in enumerate(toks):
            m = re.fullmatch(r"([a-z]{5,})([.,!]*)", tok)
            prev = toks[i - 1].lower().strip(",.") if i else ""
            if m and prev not in ("i'm", "im", "am", "called", "named", "is", "name", "call", "me") and not self.speller.known(m.group(1)):
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
        evr = self._event_q(st, msg, norm) or self._officeholder(st, msg, norm)
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
        r2 = self._daily_ctx2(st, msg, norm) or self._daily_ctx3(st, msg, norm)
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
        tp = st.topic if st.topic and st.turn - st.topic.get("turn", -99) <= 4 else None
        tries = [q]
        if tp and re.search(r"\b(?:it|there)\b", q):         # "who was the first person on it?" after the Moon
            tries.append(re.sub(r"\b(?:it|there)\b", tp["name"].lower(), q, count=1))
        item = next((it for q in tries for it in self.bank.daily.get("common", []) if re.fullmatch(it["q"], q)), None)
        if item is None:
            return None
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
            found = self.about.find(name, n=2)
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
_CORRECT_IT = re.compile(r"^(?:actually|no|nope|wait|sorry|oops|my bad|i mean|i meant)(?:[, ]+(?:no|nope|wait|sorry|actually|"
                         r"i mean|i meant))*[, ]+(?:it'?s|its|it is|i mean|i meant|make that|change (?:that|it) to)?\s*"
                         r"(?P<x>[a-z][a-z' -]{1,30}?)(?: actually| instead| now| not that)?[.!]*$")
_FAV_NOUN = {"#food": "food", "#colour": "colour", "#car": "car"}
_HI_IM = re.compile(r"^((?:hi|hey|hello|yo|heya|hiya|hallo)[,!.]*\s+(?:i'?m|im|i am|it'?s|this is)\s+)([a-z][a-z'-]+)[.!]*$", re.I)
_NOT_NAMES = frozenset(("back", "home", "here", "new", "fine", "good", "ok", "okay", "great", "well", "done", "bored", "tired",
                        "sad", "happy", "free", "busy", "sick", "ill", "hungry", "lost", "late", "early", "ready", "sorry",
                        "confused", "stuck", "curious", "alone", "awake", "up", "out", "in", "off", "on", "so", "just"))
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
