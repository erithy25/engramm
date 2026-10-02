"""Everyday conversation smarts for the dialog layer, by rules and counts (no neural network).

* ``gibberish``: "dhdhd", "asdfgh", "kjhkjh" — words that are not words. A token counts as a
  keyboard mash when it is no known word and its letter trigrams are un-English (statistics in
  letters.json, counted from the pack's reading by experiments/letters_build.py), or it runs
  along a keyboard row, or it repeats a short unit ("dhdhd"). Names stay names: "Ngozi" or
  "Wojciech" look English enough.
* ``is_discourse``: "idk", "I guess", "I see", "me too" — talk, never something to remember.
* ``experience``: "my boss was so annoying", "I just had a long day at work", "my exam went
  great" — a first-person moment with a valence and a topic ("your boss", "work"), answered
  with empathy that names the topic instead of being stored as a fact.
* ``offer_in``: the question at the end of ENGRAMM's own reply that offers something ("Want a
  joke or a fun fact?") — so a following "yes" / "sure" / "a fact please" does it.
* ``bare_followup`` / ``rebuild_question``: "where?" after "When was Shakespeare born?" →
  "Where was Shakespeare born?".
* ``swap_person``: "my boss" → "your boss" for replies that quote the user.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

LETTERS_PATH = Path(__file__).resolve().parent / "letters.json"
MASH_LOGP = -3.6            # mean letter-trigram log-probability below which an unknown word is a mash
_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm", "qwertzuiop", "yxcvbnm", "1234567890")
_CHAT_WORDS = frozenset("""hmm hm mm mmm mhm brr shh psst pfft tsk zzz brb gtg ttyl lol lmao lmfao rofl omg omfg wtf
nvm tbh imo imho smh jk np ty thx tysm pls plz gn gm gg wp rn ppl msg idk idc ikr irl fyi asap btw bc cuz coz ok okay
kk k ya yah yea yep yup nah nope meh ugh argh grr hehe haha hihi xd xoxo bff bae fomo yolo ily ilysm tho thru u ur r
dm dms pm am tv pc dj ai uk us usa eu un nyc la sf mr mrs ms dr st vs etc ie eg aka diy faq ceo cfo cto hr pr it""".split())
_LAUGH = re.compile(r"^(?:a?(?:ha|he|hi|ho|ja|je|xd|lo)+[hl]?|l+o+l+(?:o+l+)*|lmf?a+o+|xd+)$")
_REPEAT = re.compile(r"^(.{1,3})\1{1,}.{0,2}$")
_ELONGATED = re.compile(r"(.)\1{2,}")


@dataclass
class Letters:
    logp: dict
    unseen: dict
    default: float
    words: frozenset

    def score(self, w: str) -> float:
        s = f"^{w.lower()}$"
        n = len(s) - 2
        if n <= 0:
            return 0.0
        tot = 0.0
        for i in range(n):
            t = s[i:i + 3]
            tot += self.logp.get(t, self.unseen.get(t[:2], self.default))
        return tot / n


@lru_cache(maxsize=1)
def letters() -> Letters | None:
    if not LETTERS_PATH.exists():
        return None
    d = json.loads(LETTERS_PATH.read_text(encoding="utf-8"))
    return Letters(d["trigram_logp"], d["unseen_logp"], d["default_logp"], frozenset(d["words"]))


def _keyboard_run(w: str) -> bool:
    """Four or more letters in a row along one keyboard row, forwards or backwards ("asdf", "lkjh")."""
    w = w.lower()
    if len(w) < 4:
        return False
    for row in _ROWS:
        for seq in (row, row[::-1]):
            run = 1
            for a, b in zip(w, w[1:]):
                i = seq.find(a)
                run = run + 1 if i >= 0 and i + 1 < len(seq) and seq[i + 1] == b else 1
                if run >= 4:
                    return True
    return False


def is_mash(token: str, known=None) -> bool:
    """True for a token that is no word: un-English letters, a keyboard run or a repeated unit."""
    w = token.lower().strip("'")
    if not w or not w.isalpha():
        return False
    if w in _CHAT_WORDS or _LAUGH.match(w):
        return False
    if len(set(w)) == 1 and len(w) >= 3:                    # "aaaa", "jjjj" ("ooo" and "aaah" are sounds)
        return w[0] not in "aeiouh" or len(w) >= 6
    squeezed = _ELONGATED.sub(r"\1", w)                     # "nooo" → "no", "yesss" → "yes"
    lt = letters()
    for form in {w, squeezed, _ELONGATED.sub(r"\1\1", w)}:
        if len(form) < 2 and form != w:
            continue
        if form in _CHAT_WORDS or (lt and form in lt.words) or (known is not None and known(form)):
            return False
    if _keyboard_run(w):
        return True
    if len(w) >= 4 and _REPEAT.match(w) and not _LAUGH.match(w):
        return True
    if lt is None:
        return bool(re.fullmatch(r"[bcdfghjklmnpqrstvwxz]{4,}", w))
    if len(w) <= 2:
        return False
    return lt.score(w) < MASH_LOGP


def gibberish(text: str, known=None) -> bool:
    """A message made only of non-words ("dhdhd", "asdf jkl", "kjhkjh!!")."""
    toks = re.findall(r"[A-Za-z']+", text)
    if not toks:
        return False
    if len(toks) > 6:
        return False
    return all(is_mash(t, known) for t in toks)


# ---------------------------------------------------------------------------
# talk that carries nothing to remember
# ---------------------------------------------------------------------------

_DISCOURSE = re.compile(
    r"^(?:(?:well|so|um+|uh+|hmm+|oh|ah|yeah|yes|no|ok|okay|honestly|i mean|haha|lol)[ ,]+)*"
    r"(?:i (?:don't|do not|dont) know|i dunno|dunno|idk|i (?:have|got) no idea|no idea|not sure|i'm not sure|"
    r"i am not sure|i'm unsure|i guess(?: so| not)?|i suppose(?: so)?|i think so|i don't think so|i hope so|"
    r"i doubt it|i see|i know(?: right)?|i knew it|i agree|i disagree|i mean|i don't care|i do not care|i don't mind|"
    r"i do not mind|me too|me neither|same here|i understand|i get it|i got it|i didn't know(?: that)?|"
    r"i did not know(?: that)?|i forgot|i'm kidding|i am kidding|i was kidding|i was joking|i'm joking|just kidding|"
    r"i'm back|i am back|i'm here|i am here|i'm ready|i am ready|i'm listening|i'm done|i am done|i'm good|"
    r"i'm fine|i'm okay|i'm ok|i'm alright|i love it|i like it|i like that|i love that|i hate that|i hate it|"
    r"i wonder|i bet|i figured|i thought so|i believe you|i trust you|i was wondering|i'm curious|i am curious|"
    r"i have a question|i've got a question|i want to ask(?: you)?(?: something)?|i'd like to ask(?: you)?(?: something)?|"
    r"i need help|i need your help|i'm confused|i am confused|i'm lost|i am lost)"
    r"(?:[ ,]+(?:then|though|anyway|lol|haha|really|either|too|man|honestly))*$")


def is_discourse(norm: str) -> bool:
    return bool(_DISCOURSE.match(norm.strip(" .!?,")))


# ---------------------------------------------------------------------------
# first-person moments: "my boss was so annoying", "I had a great weekend"
# ---------------------------------------------------------------------------

_NEG = {
    "annoying": 2, "annoyed": 2, "frustrating": 2, "frustrated": 2, "exhausting": 2, "exhausted": 2,
    "stressful": 2, "stressed": 2, "terrible": 3, "awful": 3, "horrible": 3, "bad": 1, "boring": 1, "rude": 2,
    "mean": 1, "unfair": 2, "difficult": 1, "hard": 1, "tough": 1, "rough": 2, "sucks": 2, "sucked": 2, "sick": 2,
    "painful": 2, "hurts": 2, "hurt": 2, "broken": 2, "failed": 3, "fail": 2, "flunked": 3,
    "lost": 2, "missed": 1, "cancelled": 1, "canceled": 1, "crashed": 2, "stuck": 1, "overwhelmed": 3,
    "broke": 2,
    "overwhelming": 3, "angry": 2, "mad": 2, "upset": 2, "sad": 2, "disappointed": 2, "disappointing": 2,
    "worried": 2, "nervous": 2, "scared": 2, "lonely": 2, "tired": 2, "hate": 2, "hated": 2, "ugh": 2,
    "yelled": 2, "shouted": 2, "screamed": 2, "argued": 2, "fight": 2, "fought": 2, "cried": 2, "crying": 2,
    "sore": 1, "freezing": 1, "miserable": 3, "nightmare": 3, "disaster": 3, "worst": 3, "worse": 2, "late": 1,
    "ignored": 2, "criticized": 2, "criticised": 2, "embarrassing": 2, "embarrassed": 2, "awkward": 1,
    "rejected": 3, "dumped": 3, "fired": 3, "unbearable": 3, "insane": 2, "crazy": 2, "hectic": 2, "busy": 1,
    "long": 0, "sleepless": 2, "jetlagged": 1, "ruined": 3, "lied": 2, "stole": 3, "stolen": 3, "robbed": 3,
    "toxic": 3, "micromanaging": 2, "micromanages": 2, "blamed": 2, "bullied": 3, "drained": 2, "burnt": 2,
}
_POS = {
    "great": 2, "amazing": 3, "awesome": 3, "wonderful": 3, "fantastic": 3, "good": 1, "nice": 1, "fun": 2,
    "lovely": 2, "excellent": 3, "perfect": 2, "happy": 2, "excited": 2, "glad": 2, "proud": 3, "relaxed": 2,
    "relaxing": 2, "beautiful": 2, "delicious": 2, "promoted": 3, "passed": 3, "won": 3, "finished": 2,
    "enjoyed": 2, "loved": 2, "best": 2, "celebrated": 2, "engaged": 3, "graduated": 3, "nailed": 3, "aced": 3,
    "smooth": 1, "productive": 2, "successful": 3, "brilliant": 3, "incredible": 3, "superb": 3, "chill": 1,
    "cozy": 1, "peaceful": 2, "thrilled": 3, "grateful": 2, "thankful": 2, "blessed": 2, "unforgettable": 3,
    "hired": 3, "accepted": 3, "booked": 1, "fixed": 1, "solved": 2,
}
_NEG_PHRASES = re.compile(r"\b(?:(?:long|rough|bad|hard|tough|terrible|awful|horrible|crazy|stressful|busy|hectic|"
                          r"exhausting|shitty|crappy|weird) (?:day|week|night|morning|shift|month|year|time)|"
                          r"no sleep|didn't sleep|did not sleep|couldn't sleep|could not sleep|got no sleep|"
                          r"barely slept|pulled an all-nighter|ran out of|went wrong|fell apart|let me down|"
                          r"gave me a hard time|is driving me crazy|drives me crazy|got on my nerves|gets on my nerves|"
                          r"so much work|too much work|a lot of work|tons of work|behind on|missed my|"
                          r"broke down|got a ticket|got a parking ticket|spilled|locked out|took credit|"
                          r"stole my (?:idea|work|lunch|spot|thunder)|talked over me|threw me under the bus|"
                          r"went behind my back|left me out|stood me up|ghosted me|cut me off|was rude to me|"
                          r"made fun of me|laughed at me|don't appreciate|doesn't appreciate|didn't appreciate)\b")
_POS_PHRASES = re.compile(r"\b(?:(?:good|great|nice|amazing|awesome|fun|lovely|perfect|productive|relaxing|"
                          r"wonderful|fantastic|chill|cozy) (?:day|week|night|morning|weekend|evening|time|trip|"
                          r"holiday|vacation)|went (?:really |so |very )?(?:well|great|fine|smoothly)|"
                          r"got (?:a |the )?(?:promotion|raise|job|offer)|new job|good news|"
                          r"had a blast|got engaged|got married|bought a (?:house|car|flat)|finally (?:finished|done))\b")
_NEGATION = re.compile(r"\b(?:not|never|wasn't|isn't|aren't|weren't|didn't|don't|doesn't|no longer|hardly)\s+"
                       r"(?:(?:doing|feeling|going|looking|being|that|so|very|too|really|at all)\s+){0,2}(\w+)")
_INTENSIFIER = re.compile(r"\b(?:so|really|very|super|extremely|incredibly|totally|absolutely|such a|insanely)\b")
_FIRST = re.compile(r"\b(?:i|i'm|i've|i'd|im|ive|me|my|mine|we|we're|our|us)\b")
_PEOPLE = frozenset("""boss manager colleague coworker co-worker teammate team supervisor ceo client customer
customers teacher professor prof lecturer tutor coach mom mum mother dad father parents parent brother sister
siblings son daughter kids kid children child baby husband wife partner boyfriend girlfriend bf gf fiance fiancee
ex friend friends bestie roommate flatmate neighbour neighbor neighbours neighbors landlord grandma grandpa
grandmother grandfather aunt uncle cousin family doctor dentist driver classmate classmates students student
in-laws mother-in-law father-in-law dog cat puppy kitten""".split())
_TIME_NOUNS = frozenset("day week night morning afternoon evening weekend shift month year time".split())
_SKIP_ADJ = frozenset("new old little big whole entire stupid dumb annoying lovely sweet own first last "
                      "current former".split())
_NOT_NOUN = frozenset("""is was are were be been went goes go got gets get has had have keeps kept just always never
did didn't does doesn't don't won't can't couldn't wouldn't will would said says told tells called calls gave gives made makes
took takes left leaves came comes thinks thought wants wanted needs needed seems seemed looks looked feels felt today
tonight yesterday again so too really very still also and but or at to in on for with from of about this that""".split())
_LIFE_SUBJECT = re.compile(r"^(?:work|school|uni|university|college|class|classes|life|today|tonight|yesterday|"
                           r"this (?:morning|week|weekend)|the (?:day|week|meeting|exam|test|interview|commute|trip|"
                           r"flight|game|match|date|party|presentation|shift|deadline)|traffic|everything)\b")
_PLACES = re.compile(r"\b(?:at|from|after|before) (work|school|uni|university|college|the office|the gym|the doctor|"
                     r"the dentist|the hospital|home|practice|training|church|the airport)\b")
_EVENT_NOUNS = re.compile(r"\b(exam|test|interview|presentation|meeting|date|game|match|trip|flight|commute|"
                          r"workout|run|party|wedding|appointment|surgery|project|deadline|review|class|lecture|"
                          r"shift|audition|performance|concert|speech|pitch|negotiation|deal|launch)\b")


@dataclass
class Experience:
    valence: str                # negative | positive
    strength: int               # summed weights (intensifiers count double)
    topic: str | None           # "your boss", "work", "your exam" (already in the second person)
    person: bool                # the topic is a person (or a pet)
    timeword: str | None        # "day", "week" … when the moment is a stretch of time


def _topic(norm: str) -> tuple[str | None, bool, str | None]:
    m = re.search(r"\b(?:my|our) ((?:[a-z'-]+ ?){1,3})", norm)
    if m:
        words = []
        for w in m.group(1).split():
            if w in _NOT_NOUN or (w.endswith("ed") and len(w) > 4 and w not in ("bed", "shed")) or w in _NEG or w in _POS:
                break
            words.append(w)
        while words and words[0] in _SKIP_ADJ:
            words = words[1:]
        if words:
            noun = words[-1]
            if noun not in ("own", "life", "name", "god", "goodness", "gosh"):
                who = "your " + " ".join(words)
                return who, noun in _PEOPLE, noun if noun in _TIME_NOUNS else None
    m = re.match(r"^(work|school|uni|university|college|class|life|traffic)\b", norm) or _PLACES.search(norm)
    if m:
        place = m.group(1)
        return place, False, None
    m = _EVENT_NOUNS.search(norm)
    if m:
        return "the " + m.group(1), False, None
    m = re.search(r"\b(?:a|an|the|this|today's|today) (?:[a-z]+ )?(day|week|night|morning|weekend|shift|month)\b", norm)
    if m:
        return None, False, m.group(1)
    for w in norm.split():
        if w in _PEOPLE:
            return "your " + w if w not in ("family", "friends") else "your " + w, True, None
    return None, False, None


def experience(norm: str) -> Experience | None:
    """A first-person moment with a clear valence, or None. Questions are never moments."""
    s = norm.strip()
    if not s or s.endswith("?") or re.match(r"^(?:who|what|when|where|why|how|which|whose|is|are|do|does|did|can|"
                                            r"could|would|should|will|tell|explain|define)\b", s):
        return None
    if not _FIRST.search(s) and not _LIFE_SUBJECT.match(s) and \
            not re.search(r"\b(?:today|tonight|yesterday|this (?:morning|week|weekend))\b", s):
        return None
    words = re.findall(r"[a-z']+", s)
    negated = {m.group(1) for m in _NEGATION.finditer(s)}
    neg = pos = 0
    for w in words:
        if w in _NEG:
            if w in negated:
                pos += 1
            else:
                neg += _NEG[w]
        elif w in _POS:
            if w in negated:
                neg += _POS[w]
            else:
                pos += _POS[w]
    if _NEG_PHRASES.search(s):
        neg += 2
    if _POS_PHRASES.search(s):
        pos += 2
    boost = 1 + bool(_INTENSIFIER.search(s))
    neg, pos = neg * boost, pos * boost
    if max(neg, pos) < 2 or neg == pos:
        return None
    topic, person, timeword = _topic(s)
    return Experience("negative" if neg > pos else "positive", max(neg, pos), topic, person, timeword)


# ---------------------------------------------------------------------------
# offers in ENGRAMM's own replies, and short answers to them
# ---------------------------------------------------------------------------

_OFFERS = [
    (re.compile(r"\bjoke or (?:a |an )?(?:fun |interesting )?fact\b[^.!?]*\?\s*$", re.I), "joke_or_fact"),
    (re.compile(r"\b(?:fun|interesting) fact or (?:a )?joke\b[^.!?]*\?\s*$", re.I), "joke_or_fact"),
    (re.compile(r"\b(?:want|like|shall i tell you|how about) (?:to hear )?(?:another |a )joke\b[^.!?]*\?\s*$", re.I), "joke"),
    (re.compile(r"\b(?:want|like|shall i tell you|how about) (?:to hear )?(?:another |a )(?:fun |interesting )?fact\b[^.!?]*\?\s*$", re.I), "fact"),
    (re.compile(r"\b(?:want|like) (?:to hear )?(?:a few |some )?(?:ideas|suggestions|tips|recommendations)\b[^.!?]*\?\s*$", re.I), "ideas"),
    (re.compile(r"\b(?:want|like) (?:me )?to tell you more\b[^.!?]*\?\s*$|\b(?:tell you|hear) more\?\s*$", re.I), "more"),
    (re.compile(r"\b(?:another one|one more|again|play again|next question)\?\s*$", re.I), "again"),
    (re.compile(r"\b(?:want|like) to (?:talk|tell me) about (?:it|that|what happened)\b[^.!?]*\?\s*$", re.I), "listen"),
    (re.compile(r"\b(?:want|like) (?:me )?to (?:quiz you|play a quiz|test you)\b[^.!?]*\?\s*$", re.I), "quiz"),
    (re.compile(r"\b(?:want|like) (?:to hear )?a riddle\b[^.!?]*\?\s*$", re.I), "riddle"),
]


def offer_in(reply: str) -> str | None:
    tail = reply.strip().split("\n")[-1]
    for rx, kind in _OFFERS:
        if rx.search(tail):
            return kind
    return None


_YES = re.compile(r"^(?:(?:oh|ok|okay|well|hmm|um)[ ,]+)?(?:yes+|yeah+|yep|yup|ya|yea|sure|of course|definitely|absolutely|"
                  r"certainly|ok|okay|alright|why not|sounds good|go ahead|go for it|please|yes please|sure thing|"
                  r"i'd like that|i would like that|i'd love that|i'd love to|love to|let's do it|let's go|do it|"
                  r"hit me|go on|tell me|shoot|bring it on|i'm in|i am in|another|another one|one more|again|more)"
                  r"(?:[ ,!.]+(?:please|thanks|thank you|sure|why not|go ahead|tell me|one))*$")
_NO = re.compile(r"^(?:(?:oh|ok|okay|well|hmm|um|haha)[ ,]+)?(?:no+|nope|nah|no thanks|no thank you|not really|not now|"
                 r"maybe later|later|i'm good|i am good|i'm fine|no need|never mind|nevermind|not today|pass|i'll pass|"
                 r"i'm okay|enough|that's enough|stop)(?:[ ,!.]+(?:thanks|thank you|though|for now|i'm good))*$")


def short_answer(norm: str) -> str | None:
    """'yes' / 'no' for a short reply to an offer, else None."""
    s = norm.strip(" .!?,")
    if _YES.match(s):
        return "yes"
    if _NO.match(s):
        return "no"
    return None


# ---------------------------------------------------------------------------
# follow-up questions without their own subject
# ---------------------------------------------------------------------------

_BARE_WH = re.compile(r"^(?:and |but |so |ok |okay )?(where|when|who|whom|how|how old|how long|how many|how much|how big|"
                      r"how tall|what year|which year|what|which one|in which year|in what year)"
                      r"(?: exactly| though| then| precisely| again)?\s*\?*$", re.I)
_LEAD_WH = re.compile(r"^(what year|which year|in which year|in what year|how many|how much|how old|how long|how big|"
                      r"how tall|where|when|who|whom|why|how|which|what)\b", re.I)


def bare_followup(msg: str) -> str | None:
    """'where?' → 'where'; None for anything that is more than a question word."""
    m = _BARE_WH.match(msg.strip())
    return m.group(1).lower() if m else None


def rebuild_question(last_q: str, wh: str) -> str | None:
    """The last question with its question word replaced: ("When was X born?", "where") →
    "Where was X born?". None when the last question does not start with a question word or
    the result would be the same question."""
    if not last_q:
        return None
    q = last_q.strip()
    m = _LEAD_WH.match(q)
    if not m:
        return None
    rest = q[m.end():]
    if wh in ("what", "which one") or m.group(1).lower() == wh:
        return None
    if wh in ("how old",) and not re.search(r"\b(?:is|was)\b", rest):
        return None
    out = wh[:1].upper() + wh[1:] + rest
    if not out.endswith("?"):
        out += "?"
    return out


# ---------------------------------------------------------------------------
# the user's words in ENGRAMM's mouth
# ---------------------------------------------------------------------------

_SWAP = {"i": "you", "me": "you", "my": "your", "mine": "yours", "myself": "yourself", "i'm": "you're",
         "i've": "you've", "i'd": "you'd", "i'll": "you'll", "am": "are", "we": "you", "our": "your", "us": "you",
         "ours": "yours", "you": "I", "your": "my", "yours": "mine", "yourself": "myself", "you're": "I'm"}


def swap_person(text: str) -> str:
    out = []
    for w in text.split():
        core = w.strip(".,!?").lower()
        tail = w[len(w.rstrip(".,!?")):]
        out.append((_SWAP.get(core, w.strip(".,!?"))) + tail)
    s = " ".join(out)
    return re.sub(r"\byou am\b", "you are", s)
