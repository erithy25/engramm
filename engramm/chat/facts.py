"""Stage 2 — the HDC fact memory (docs/PREREG_CHAT_V2.md).

Statements are cut into facts (subject, relation words, object) by rules. Every
entity gets a hypervector from its letter trigrams, so a misspelt name still lands
near the right entity. Relations are bundles of ENGRAMM's counted meaning vectors
("highest" lies near "tallest"). Objects are random symbol vectors.

Each entity keeps one record, the superposition of its facts bound role ⊗ filler:

    M_e = majority_i( R_i ⊕ F_i )          (⊕ = XOR binding; inverse facts use R_i ⊕ INV)

A question is answered by unbinding: find the entity (nearest trigram vector),
compute U = M_e ⊕ R_q and clean it up against the fillers known for e — the most
similar filler is the answer. Nothing is trained; all vectors come from SHAKE-256,
letter trigrams and the counted codebook, so the memory is a pure function of the
live statements and forgetting a statement is exact.

The exact-dictionary ablation (F2) keeps the same facts and records but looks the
entity up by its exact normalised name.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field

import numpy as np

from engramm.chat.question import STOP, spans, words

WORDS = 32                     # 2,048 bits, the width of the counted meaning vectors
BITS = WORDS * 64
USER = "USER"                  # the person you are talking to

FIRST_PERSON = frozenset(("i", "me", "my", "mine", "myself", "i'm", "im"))
AUX = frozenset(("is", "are", "was", "were", "be", "been", "am", "do", "does", "did", "has", "have", "had",
                 "will", "would", "can", "could", "please", "tell", "know", "remember", "you", "your", "again",
                 "actually", "still", "now", "anymore", "not"))
QWORDS = frozenset(("what", "which", "who", "whom", "whose", "when", "where", "why", "how", "kind", "type",
                    "sort"))
REL_STOP = STOP - frozenset(("name", "named", "called", "call", "known", "most", "one", "first"))
PLACE_PREPS = frozenset(("in", "at", "near", "from", "to"))

# Hand-written concept groups (general English, applied the same way to statements and
# questions): a member word adds the group's label to the relation words.
CONCEPTS = [
    ("#age", re.compile(r"\b(?:how old|my age|your age|age)\b")),
    ("#job", re.compile(r"\b(job|jobs|profession|occupation|career|works? as|worked as|working as|living as|at work|"
                        r"earns? (?:a |my |his |her )?living|earning (?:a |my )?living|makes? (?:a |my )?living|"
                        r"making (?:a |my )?living|for a living|do for (?:a )?(?:work|living)|by trade|trade|"
                        r"professionally|professional|make money|makes money|making money|work-wise|workwise|"
                        r"line of work|kind of work|type of work|what (?:do|does|did) (?:i|you|he|she|we) do|"
                        r"employed as|trained as|train as|training as|day job|make (?:my |his |her |our )?money|"
                        r"earn (?:my |his |her |our )?money)\b")),
    ("#employer", re.compile(r"\b(employer|company|firm|workplace|works? (?:over |out )?(?:at|for)|"
                             r"worked (?:over |out )?(?:at|for)|who (?:do|did|does) (?:i|you|he|she) work for|"
                             r"for whom (?:do|did|does) (?:i|you|he|she) work|pays? (?:my |his |her )?(?:salary|wages)|"
                             r"working (?:over |out )?(?:at|for)|employ(?:er|ers|ee|ees|s|ing|ment)?|employed(?! as)|"
                             r"where (?:do )?i work|paycheck|payroll|"
                             r"staff of|on the staff)\b")),
    ("#work", re.compile(r"\b(work|works|worked|working)\b")),
    ("#home", re.compile(r"\b(home|hometown|residence|resident|reside|resides|residing|live|lives|lived|"
                         r"living(?! as)|moved? to|moving to|relocated to|stay|stays|staying|based|settled|flat|"
                         r"apartment|i am (?:originally )?from|i am in|my (?:city|town|village|country|address))\b")),
    ("#birth", re.compile(r"\b(birthday|birth|born|birthplace|birthdate|came into the world|come into the world|"
                          r"comes into the world)\b")),
    ("#car", re.compile(r"\b(car|cars|vehicle|drive|drives|driving|drove|ride|wheels)\b")),
    ("#food", re.compile(r"\b(food|foods|eat|eats|eating|ate|meal|meals|dish|dishes|cuisine)\b")),
    ("#colour", re.compile(r"\b(colou?rs?|shades?|hues?)\b")),
    ("#fav", re.compile(r"\b(favou?rite|love|loves|like|likes|prefer|prefers|best|most|adore|adores|enjoy|"
                        r"enjoys|nothing beats|beats|fan|crazy about|go-to|obsessed with|choose|chose|pick|picked|"
                        r"top)\b")),
    ("#name", re.compile(r"\b(name|names|named|called|call|calls|go by|goes by|known as|know me as|answers? to|"
                         r"(?<!public )(?<!at )(?<!of )(?<!about )(?<!in )speaking(?=\s*[.!]*$)|introduce myself|introduce me|address me)\b")),
    ("#place", re.compile(r"\b(where|place|city|town|country)\b")),
    # where someone comes from: a birthplace answers "Where is he from?"
    ("#origin", re.compile(r"\b(born in|born at|birthplace|place of birth|come from|comes from|came from|"
                           r"coming from|originally from|hails? from|native of|grew up in|raised in|"
                           r"where\b.*\b(?:from|born|come into the world|came into the world)|"
                           r"which (?:town|city|village|country|place)\b.*\b(?:from|born))\b")),
]
# phrases that name the job, removed before the home group is matched ("for a living" is not a home)
_JOB_LIVING = re.compile(r"\b(?:earns?|earning|makes?|making|do|does|did|for) (?:a |my |his |her )?living\b")


CONCEPT_PARENTS = {"#job": "#work", "#employer": "#work", "#home": "#place", "#origin": "#home"}
_NOT_A_JOB = frozenset(("beginner", "newbie", "novice", "noob", "fan", "mess", "person", "owl", "bird", "perfectionist", "introvert",
                        "extrovert", "vegetarian", "vegan", "procrastinator", "worrier", "overthinker", "pro", "expert", "natural",
                        "rookie", "learner", "member", "regular", "night", "morning", "lightweight", "foodie", "nerd", "geek", "interview", "interviews", "offer", "application", "search", "hunt", "fair", "party", "parties", "barbecue", "bbq",
                        "picnic", "celebration", "wedding", "dinner", "lunch", "brunch", "meeting", "trip", "holiday", "vacation", "monday", "tuesday",
                        "wednesday", "thursday", "friday", "saturday", "sunday", "weekend", "tonight", "tomorrow", "apartment", "flat", "house",
                        "room", "place", "home", "car", "phone", "laptop", "bike", "dog", "cat", "partner", "girlfriend", "boyfriend", "gift", "present",
                        "emails", "email", "mails", "messages", "meetings", "meeting", "paperwork", "calls", "tasks", "deadlines", "work", "stress"))
_CALL_HOME = re.compile(r"\bcalls? (?:[a-z]+ ){0,2}home\b")     # "I call Lyon home" names a home, not a name
# "remind me to call mom tomorrow", "i have to call the bank": phoning someone, not a name
_CALL_PHONE = re.compile(r"\b(?:to|gotta|should|will|must|can|could|'ll|need to|have to|and|then|please|didn'?t|forgot to) call\b|"
                         r"\bcall(?:ed|ing)? (?:my|mom|mum|dad|him|her|them|back|the|a|an|you|someone|somebody|grandma|grandpa)\b")
CATEGORIES = frozenset(("#food", "#colour", "#car", "#job", "#employer", "#home", "#birth", "#name", "#origin"))


def category_conflict(a, b) -> bool:
    """Both relation word sets name a category, and no category is shared."""
    ca, cb = set(a) & CATEGORIES, set(b) & CATEGORIES
    return bool(ca and cb and not ca & cb)


_JOB_AT = re.compile(r"\b(?:a |the |my )?(?:job|position|post) (?:at|with|for)\b")


def concepts(text: str) -> list[str]:
    low = text.lower().replace("’", "'")
    if _JOB_AT.search(low):              # "a job at X": X is the employer, not the occupation
        low = _JOB_AT.sub(" employer ", low)
    out = [label for label, rx in CONCEPTS
           if rx.search(_JOB_LIVING.sub(" job ", low) if label == "#home" else
                        _CALL_PHONE.sub(" phone ", _CALL_HOME.sub(" home ", low)) if label == "#name" else low)]
    for _ in range(2):                    # parents of parents (#origin → #home → #place)
        out += [CONCEPT_PARENTS[c] for c in out if c in CONCEPT_PARENTS and CONCEPT_PARENTS[c] not in out]
    return out


_COUNT_OF = re.compile(r"^(?:\d{1,2}|a|an|one|two|three|four|five|six|seven|eight|nine|ten|twin)\s+[a-z]+$", re.I)
POSSESSED = frozenset((
    "brother", "sister", "mother", "mom", "mum", "father", "dad", "wife", "husband", "son", "daughter", "partner",
    "girlfriend", "boyfriend", "friend", "boss", "dog", "cat", "pet", "horse", "bird", "grandmother", "grandfather",
    "grandma", "grandpa", "uncle", "aunt", "cousin", "neighbour", "neighbor", "colleague", "baby", "child", "kid",
    "fiance", "fiancee", "roommate", "flatmate", "puppy", "pup", "doggy", "kitten", "kitty", "mommy", "daddy", "bro",
    "sis", "hubby", "sibling", "parent", "pet", "niece", "nephew", "granddaughter", "grandson", "stepson", "stepdaughter",
    "stepmother", "stepfather", "godson", "goddaughter", "manager", "teacher", "landlord", "landlady", "coworker", "classmate",
    # plurals ("My children are called Mia and Leo")
    "children", "kids", "sons", "daughters", "parents", "brothers", "sisters", "siblings", "dogs", "cats", "pets",
    "grandparents", "grandchildren", "twins", "nieces", "nephews", "colleagues", "neighbours", "neighbors", "friends", "cousins"))
# the same entity under another word ("my puppy" is "my dog")
POSSESSED_CANON = {"puppy": "dog", "pup": "dog", "doggy": "dog", "kitten": "cat", "kitty": "cat", "mom": "mother",
                   "mum": "mother", "mommy": "mother", "dad": "father", "daddy": "father", "bro": "brother",
                   "sis": "sister", "hubby": "husband", "grandma": "grandmother", "grandpa": "grandfather",
                   "neighbor": "neighbour", "fiancee": "fiance", "flatmate": "roommate", "kids": "children"}
_CONTRACTIONS = [(r"\bwhat's\b", "what is"), (r"\bwho's\b", "who is"), (r"\bwhere's\b", "where is"),
                 (r"\bwhen's\b", "when is"), (r"\bhow's\b", "how is"), (r"\bthat's\b", "that is"),
                 (r"\bit's\b", "it is"), (r"\bi'm\b", "i am"), (r"\bi've\b", "i have"), (r"\bi'd\b", "i would"),
                 (r"\bi'll\b", "i will"), (r"\bdon't\b", "do not"), (r"\bdoesn't\b", "does not"),
                 (r"\bdidn't\b", "did not"), (r"\bcan't\b", "can not"), (r"\bwon't\b", "will not"),
                 (r"\bisn't\b", "is not"), (r"\bwe're\b", "we are"), (r"\byou're\b", "you are"),
                 (r"\bwhats\b", "what is"), (r"\bwheres\b", "where is"), (r"\bwhos\b", "who is"),
                 (r"\bwhens\b", "when is"), (r"\bim\b", "i am"), (r"\bive\b", "i have"),
                 (r"\bdont\b", "do not"), (r"\bdoesnt\b", "does not"), (r"\bdidnt\b", "did not")]
_LEADING = re.compile(r"^(?:(?:these days|nowadays|currently|right now|now|at the moment|actually|by the way|btw|"
                      r"well|so|also|and|oh|anyway|just so you know|fyi|for the record|honestly|really|frankly|"
                      r"truthfully|to be honest|basically|personally|ok|okay|yeah|yes|you know|in fact)[, ]+)+",
                      re.I)


def expand_contractions(text: str) -> str:
    t = text.replace("’", "'")
    for rx, rep in _CONTRACTIONS:
        t = re.sub(rx, lambda m, rep=rep: rep if m.group(0)[0].islower() else rep.capitalize(), t, flags=re.I)
    return t


def possessed_key(noun: str) -> str:
    return f"{USER}:{POSSESSED_CANON.get(noun, noun)}"


def rand_vec(*parts) -> np.ndarray:
    data = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return np.frombuffer(hashlib.shake_256(data).digest(8 * WORDS), dtype="<u8").astype(np.uint64)


TIE = rand_vec("fact-memory", "tie")
INV = rand_vec("fact-memory", "inverse-role")


def _bits(vs: np.ndarray) -> np.ndarray:
    """(n, WORDS) uint64 → (n, BITS) 0/1, fixed bit order (little-endian words)."""
    return np.unpackbits(np.ascontiguousarray(vs).astype("<u8").view(np.uint8), axis=-1, bitorder="little")


def _pack(bits: np.ndarray) -> np.ndarray:
    return np.packbits(bits.astype(np.uint8), bitorder="little").view("<u8").astype(np.uint64)


def bundle(vs: list[np.ndarray]) -> np.ndarray:
    """Bit-wise majority; an even count gets the fixed tie vector as extra vote."""
    if len(vs) == 1:
        return vs[0].copy()
    m = list(vs) + ([TIE] if len(vs) % 2 == 0 else [])
    b = _bits(np.stack(m))
    return _pack(b.sum(axis=0) * 2 > len(m))


def ham(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.bitwise_count(a ^ b).sum())


def ham_many(M: np.ndarray, v: np.ndarray) -> np.ndarray:
    return np.bitwise_count(M ^ v[None, :]).sum(axis=1)


def sim(a: np.ndarray, b: np.ndarray) -> float:
    return 1.0 - ham(a, b) / BITS


TITLES = frozenset(("captain", "capt", "mount", "mt", "mr", "mrs", "ms", "dr", "sir", "dame", "king", "queen",
                    "president", "professor", "prof", "saint", "st", "lord", "lady", "general", "colonel", "admiral",
                    "prince", "princess", "emperor", "pope", "lake", "river", "the"))


def norm_entity(s: str) -> str:
    """Lower-case words; leading titles ("Captain", "Mount", …) do not count for identity."""
    ws = [w.lower() for w in words(s) if w[0].isalnum()]
    while len(ws) > 1 and ws[0] in TITLES:
        ws = ws[1:]
    return " ".join(ws)


def majority_agreement(k: int) -> float:
    """Expected share of bits the majority of k bound pairs (+ tie vector if k is even)
    shares with one of them — the similarity an exact unbinding can reach."""
    from math import comb
    m = k + (1 if k % 2 == 0 else 0)
    if m == 1:
        return 1.0
    need = (m - 1) // 2
    return sum(comb(m - 1, j) for j in range(need, m)) / 2 ** (m - 1)


def stem(w: str) -> str:
    """A light suffix stripper, only for the random fall-back vectors of unknown words."""
    for suf in ("ing", "ers", "er", "ed", "es", "s", "ly"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[:-len(suf)]
    return w


class EntityCoder:
    """Name → bundle of its letter trigrams (each word padded with '#')."""

    def __init__(self):
        self._cache: dict[str, np.ndarray] = {}

    def encode(self, name: str) -> np.ndarray:
        key = norm_entity(name)
        v = self._cache.get(key)
        if v is None:
            grams = []
            for w in key.split():
                p = f"#{w}#"
                grams += [p[i:i + 3] for i in range(len(p) - 2)]
            v = bundle([rand_vec("trigram", g) for g in grams]) if grams else rand_vec("entity", key)
            self._cache[key] = v
        return v


class RelationCoder:
    """Relation words → bundle of their counted meaning vectors (random for unknown words)."""

    def __init__(self, eng: np.ndarray | None, tok=None):
        self.eng, self.tok = eng, tok
        self._cache: dict[str, np.ndarray] = {}

    def word(self, w: str) -> np.ndarray:
        v = self._cache.get(w)
        if v is None:
            v = None
            if self.eng is not None and self.tok is not None:
                ids = self.tok.encode(" " + w)
                if len(ids) == 1:
                    v = np.asarray(self.eng[ids[0]], dtype=np.uint64)
            if v is None:
                v = rand_vec("word", stem(w))
            self._cache[w] = v
        return v

    def encode(self, ws) -> np.ndarray:
        ws = sorted(set(ws))
        if not ws:
            return rand_vec("relation", "empty")
        return bundle([self.word(w) for w in ws])


# ---------------------------------------------------------------------------
# statements → facts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Fact:
    subject: str
    relation: tuple[str, ...]
    object: str
    source: str
    sentence: str
    kind: str = "TEXT"          # of the object: NAME, DATE, NUMBER or TEXT


def object_kind(obj: str) -> str:
    sp = spans(obj)
    if sp and sp[0].start == 0 and sp[0].end == len(words(obj)):
        return {"NAME": "NAME", "DATE": "DATE", "NUMBER": "NUMBER"}.get(sp[0].kind, "TEXT")
    return "TEXT"


_KIND_OK = {"PERSON": (("NAME",), ("TEXT",)), "LOCATION": (("NAME",), ("TEXT",)),
            "PROPER": (("NAME",), ("TEXT",)), "DATE": (("DATE",),), "NUMBER": (("NUMBER",),)}


_FP_PATTERNS = [
    # (regex on the lower-cased, normalised sentence, relation words, object group)
    (re.compile(r"^(?:(?:my )?(?:friends|family|people|everyone|they|most people|colleagues|everybody) )?"
                r"calls? me (?P<o>.+)$"), ("name", "called"), "o"),
    (re.compile(r"^i am (?:called|named|known as) (?P<o>.+)$"), ("name", "called"), "o"),
    (re.compile(r"^my (?P<r>[a-z' ]+?)(?:'s| s)? name is (?P<o>.+)$"), ("name",), "o"),
    (re.compile(r"^my (?P<r>[a-z' ]+?) (?:is|was) (?:called|named) (?P<o>.+)$"), ("name", "called"), "o"),
    (re.compile(r"^i have (?:a|an|one) (?P<r>[a-z ]+?) (?:called|named) (?P<o>.+)$"), ("name", "called"), "o"),
    (re.compile(r"^the (?P<r>[a-z ]+?) (?:that |which )?i (?P<v>[a-z]+)(?: [a-z]+)?(?: most| best)? (?:is|are) "
                r"(?P<o>.+)$"), (), "o"),
    (re.compile(r"^i (?P<v>like|love|prefer|enjoy) (?:the )?(?P<r>[a-z]+) (?P<o>[a-z0-9' -]+?)(?: the)?"
                r"(?: most| best| more than anything)$"), ("favourite",), "o"),
    (re.compile(r"^i (?P<v>like|love|prefer|enjoy) (?:eating |drinking |playing )?(?P<o>[a-z0-9' -]+?)"
                r"(?: most| best| more than anything)$"), ("favourite",), "o"),
    (re.compile(r"^my (?P<r>[a-z' ]+?) (?:is|was|are) (?:in|at|on) (?P<o>.+)$"), (), "o"),
    (re.compile(r"^my (?P<r>[a-z' ]+?) (?:is|was|are) (?:a |an |the )?(?P<o>.+)$"), (), "o"),
    (re.compile(r"^i am (?:a |an )?(?P<o>[a-z0-9' -]+?) by (?P<r>[a-z]+)$"), (), "o"),
    (re.compile(r"^i (?:am|was) (?P<v>[a-z]+ed) (?P<p>by|to|at|in|on|with|from|for) (?:a |an |the )?(?P<o>.+)$"),
     (), "o"),
    (re.compile(r"^i (?P<v>[a-z]+(?: [a-z]+){0,2}) (?P<p>in|at|on|for|as|with|from|to|near|under) "
                r"(?:a |an |the )?(?P<o>.+)$"), (), "o"),
    (re.compile(r"^i was (?P<v>born|raised|married) (?P<p>in|on|at|to) (?P<o>.+)$"), (), "o"),
    (re.compile(r"^i am (?:a |an )?(?P<o>[a-z0-9' -]+)$"), ("am",), "o"),
    (re.compile(r"^i (?P<v>drive|own|have|play|speak|study|use|ride|keep) (?:a |an |the )?(?P<o>.+)$"), (), "o"),
]


def normalise_first_person(sentence: str) -> str:
    """Contractions expanded, leading fillers dropped, 'our' → 'my' (for matching only)."""
    s = expand_contractions(sentence.strip()).rstrip(".!").strip()
    s = _LEADING.sub("", s)
    s = re.sub(r"[,!.]?\s*(?:(?:it is |it's )?(?:nice|pleased|glad|good|great) to meet you|how are you)[.!]*$", "", s,
               flags=re.I).strip()
    s = re.sub(r"^(?:the )?name(?:'s| is)\b", "my name is", s, flags=re.I)
    s = re.sub(r"^([A-Z][\w-]*)'s the name\b", r"my name is \1", s)
    s = re.sub(r"\bour\b", "my", s, flags=re.I)
    s = re.sub(r"\bwe are\b", "I am", s, flags=re.I)
    s = re.sub(r"\bwe were\b", "I was", s, flags=re.I)
    s = re.sub(r"\bwe\b", "I", s, flags=re.I)
    return s


def _clean_object(o: str, original: str) -> str:
    o = o.strip().rstrip(".!").strip()
    o = re.sub(r"^(?:a|an|the)\s+", "", o)
    # keep the user's capitalisation
    m = re.search(re.escape(o), original, flags=re.IGNORECASE)
    return m.group(0) if m else o


def _rel_words(text: str) -> list[str]:
    out = []
    for w in words(text.lower()):
        w = w.replace("’", "'")
        if w.endswith("'s"):
            w = w[:-2]
        if w and w[0].isalnum() and w not in REL_STOP and w not in AUX:
            out.append(w)
    return out


def first_person_facts(sentence: str, source: str) -> list[Fact]:
    s = normalise_first_person(sentence)
    low = s.lower()
    for rx, extra, og in _FP_PATTERNS:
        m = rx.match(low)
        if not m:
            continue
        gd = m.groupdict()
        rel = list(extra)
        for g in ("r", "v"):
            if gd.get(g):
                rel += _rel_words(gd[g])
        if gd.get("p"):
            rel.append(gd["p"])
            if gd["p"] in PLACE_PREPS:
                rel.append("#place")
        obj = _clean_object(gd[og], s)
        if not obj:
            continue
        head = low[:m.start(og)] if og in gd and m.start(og) >= 0 else low
        rel += concepts(" ".join([head] + [gd[g] for g in ("r", "v", "p") if gd.get(g)]))
        subject = USER
        r_words = [w for w in (gd.get("r") or "").replace("'s", "").split()]
        owned = [w for w in r_words if w in POSSESSED]
        if owned:                      # "my (older) brother …" is a fact about your brother, not about you
            subject = possessed_key(owned[-1])
            rel = [w for w in rel if w not in r_words]
        return [Fact(subject, tuple(sorted(set(rel))), obj, source, sentence.strip(), object_kind(obj))]
    return []


_GREETING = re.compile(r"^(?:(?:hi|hello|hey|hiya|greetings|good (?:morning|afternoon|evening)|(?:nice|pleased|glad) "
                       r"to meet you)\b[,!. ]*)+", re.I)
# "no wait, i'm 35", "actually, i live in Hamburg": a correction lead says nothing about the fact itself
_CORRECTION_LEAD = re.compile(r"^(?:(?:no|nope|oh|oops|sorry|my bad|hm+)[,!.]+\s*|(?:no,? |oh,? |oops,? |sorry,? )?(?:wait|actually|hold on|"
                              r"correction|i mean|scratch that|let me correct that)\b[,:!. ]*)+", re.I)
_VALUE_CUES = frozenset(("is", "am", "are", "was", "were", "a", "an", "as", "love", "loves", "like", "likes", "own",
                         "owns", "drive", "drives", "be", "called", "named", "at", "in", "to", "on", "by", "enjoy",
                         "prefer", "adore", "adores", "eat", "eats", "drink", "drinks", "play", "plays", "wear",
                         "wears"))
_FIRST = frozenset(("i", "my", "me", "mine", "myself"))
CATEGORY_NOUNS = frozenset(("colour", "color", "colours", "colors", "food", "dish", "meal", "car", "vehicle", "job",
                            "city", "town", "name", "company", "employer", "work", "profession", "occupation",
                            "birthday", "place", "home", "favourite", "favorite", "best"))
NON_VALUES = frozenset(("favourite", "favorite", "best", "most", "one", "thing", "stuff", "it", "that", "this",
                        # verbs a lexicon may also know as nouns: "I just got back from vacation" has no job "got"
                        "got", "get", "gets", "getting", "went", "go", "goes", "going", "gone", "came", "come", "comes",
                        "coming", "back", "made", "make", "took", "take", "had", "did", "done", "been", "said", "saw",
                        "seen", "left", "felt", "feel", "tried", "try", "started", "start", "finished", "finish",
                        "quit", "quitting", "fired", "retired", "resigned", "moved", "move",
                        # "something I can do at home" names nothing
                        "something", "anything", "nothing", "everything", "someone", "anyone", "somewhere",
                        "anywhere", "whatever",
                        # "I got a new job": an adjective alone is not the job
                        "new", "old", "first", "next", "last", "current",
                        # "I'm kinda hungry tbh": a state, never a favourite food
                        "hungry", "starving", "thirsty", "peckish", "sleepy", "tbh", "idk", "kinda", "lol"))


# words that are never the value of a personal statement: fillers, time phrases, evaluation cues
_FILLERS = frozenset(("honestly", "really", "just", "actually", "basically", "truly", "totally", "absolutely",
                      "definitely", "always", "still", "also", "too", "very", "quite", "pretty", "recently",
                      "currently", "now", "today", "ago", "last", "year", "years", "month", "months", "week", "weeks",
                      "day", "days", "every", "whenever", "moment", "time", "while", "lately", "long", "old",
                      "here", "there", "please", "thanks", "nice", "meet", "hi", "hello", "hey", "proud", "big", "fan",
                      "crazy", "top", "go-to", "wise", "work-wise", "workwise", "professionally", "nothing", "beats",
                      "speaking", "choose", "pick", "rather", "probably", "certainly", "surely", "simply",
                      "definitely", "obviously", "absolutely", "clearly", "hands", "down"))
_DURATION = frozenset(("year", "years", "month", "months", "week", "weeks", "day", "days", "old", "hours", "decade",
                       "decades", "times"))
_PREPS = frozenset(("after", "with", "for", "to", "from", "by", "like", "than", "about", "at", "in", "on"))
_NUMBER_WORDS = frozenset(("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
                           "twelve", "twenty", "thirty", "hundred", "several", "few"))
_QUANT = frozenset(("all", "every", "each", "any", "some", "many", "few", "more", "less", "other", "another", "such",
                    "own", "same", "whole"))
_TRAIL = frozenset(("for", "every", "whenever", "since", "when", "because", "at", "right", "last", "recently",
                    "these", "this", "as", "ago", "and", "but", "so", "with", "from", "in", "on", "to", "of"))
# nouns a job/food/colour word can describe ("a dentist appointment" is not a job)
_HEAD_NOUNS = frozenset(("appointment", "appointments", "visit", "visits", "checkup", "check-up", "interview",
                         "interviews", "exam", "exams", "lesson", "lessons", "class", "classes", "bill", "bills",
                         "office", "surgery", "practice", "course", "test", "session", "sessions"))


def _cue_words() -> frozenset:
    from engramm.chat.lexicon import ANCHORS
    return frozenset(w for ws in ANCHORS.values() for w in ws.split())


_CUE_WORDS = _cue_words()          # "eat", "drive", "working": the anchors of a category are cues, never values
_NAME_INTRO = re.compile(r"^(?:this is )?(?P<o>[A-Z][\w'-]*(?: [A-Z][\w'-]*)?)(?: here| speaking)?[.!]?$")


def _trim_value(obj: str) -> str:
    """"been a chemist for years" → "chemist", "crazy about paella" → "paella"."""
    ws = words(obj)
    lw = [w.lower() for w in ws]
    i = 0
    while i < len(ws) and (lw[i] in STOP or lw[i] in _FILLERS or lw[i] in ("been", "being", "about")):
        i += 1
    j = i
    while j < len(ws) and ws[j][0].isalnum() and not (j > i and lw[j] in _TRAIL) and lw[j] not in _FILLERS:
        j += 1
    return " ".join(ws[i:j]) if j > i else obj


def personal_facts(sentence: str, source: str, initial_is_name=None, typer=None, implicit: bool = False
                   ) -> list[Fact]:
    """A statement about you or something of yours, without sentence templates:

    * subject: you, or "my <brother/dog/…>" as its own entity;
    * value: the date or name the sentence mentions (not an opening "Honestly," nor an age
      or a duration); else a word the corpus counts as a food, colour, car or job (lexicon);
      else the value the templates find, the subject of "X is my …", or the words after the
      last verb/article cue;
    * relation: every other content word, plus the concept groups, plus the value's counted
      category when the sentence names no category itself.

    ``implicit``: the sentence has no "I"/"my" but is still about you ("Nothing beats curry.")."""
    s = _GREETING.sub("", normalise_first_person(sentence)).strip()
    if re.search(r"\b(?:feel|feels|felt|feeling|look|looks|looked|sound|sounds|seem|seems) like (?:a |an |such a |the )?"
                 r"(?:failure|loser|idiot|fool|mess|burden|fraud|joke|zombie|crap|shit|garbage|nobody|nothing|i|it|that|this|"
                 r"giving up|crying|sleeping|dying|everyone|no one)\b", s, re.I):
        return []                        # "I feel like a failure": a feeling, never a favourite
    if re.search(r"^(?:but |and |also |plus )?my (?:\w+ )?\w+ (?:keeps|kept|won'?t stop|wont stop|never stops|"
                 r"is always|always)\s+\w+ing\b", s, re.I):
        return []                        # "my mind keeps racing": how something behaves, never a fact to keep
    if re.search(r"\b(?:didn'?t|did not|haven'?t|have not|hasn'?t|wasn'?t|weren'?t)\b", s, re.I) and \
            not re.search(r"\b(?:never|ever)\b.*\b(?:been|lived|worked)\b", s, re.I):
        return []                        # "I didn't drink much water": what did not happen today, never a favourite
    if re.match(r"\s*(?:she|he|they)\b", s, re.I) and re.search(r"\b(?:likes?|loves?|enjoys?|adores?|is into|are into|is crazy about)\b", s, re.I):
        return []                        # "she loves animals" (the niece): someone else's liking, never the user's favourite
    if re.match(r"\s*(?:like|about|around|maybe|roughly|almost)\s+\d", s, re.I):
        return []                        # "like 200 a day": an aside with a number, no fact about the user
    ws = words(s)
    lw = [w.lower() for w in ws]
    n = len(ws)
    if not implicit and not any(w in _FIRST for w in lw):
        return []
    subject, owned = USER, set()
    for i, w in enumerate(lw):
        if w in ("have", "has", "got", "own", "owns", "adopted", "keep") and i + 2 < n and \
                lw[i + 1] in ("a", "an", "one"):
            for j in range(i + 2, min(i + 5, n)):
                if lw[j] in POSSESSED:
                    subject = possessed_key(lw[j])
                    owned = set(range(i, j + 1))
                    break
            if owned:
                break
        if w == "my":
            for j in range(i + 1, min(i + 4, n)):
                noun = lw[j][:-2] if lw[j].endswith("'s") else lw[j]
                if noun in POSSESSED:
                    nxt = lw[j + 1][:-2] if j + 1 < n and lw[j + 1].endswith("'s") else (lw[j + 1] if j + 1 < n else "")
                    if nxt in POSSESSED:          # "my pet dog": the dog
                        j, noun = j + 1, nxt
                    named_next = j + 1 < n and ws[j + 1][:1].isupper() and lw[j + 1] not in STOP
                    if i > 0 and lw[i - 1] in _PREPS and not named_next:
                        break                     # "named after my grandfather": not about the grandfather
                    subject = possessed_key(noun)
                    owned = set(range(i, j + 1))
                    break
            if owned:
                break
    cands = [x for x in spans(s, initial_is_name) if x.kind in ("NAME", "DATE", "NUMBER")
             and not (set(range(x.start, x.end)) & owned) and lw[x.start] not in _FIRST]
    typed = []                   # (start, end, text, category) — the corpus' own lexicon
    if typer is not None:
        for i in range(n):
            if i in owned or not ws[i][0].isalpha() or lw[i] in STOP or lw[i] in _FIRST or lw[i] in CATEGORY_NOUNS \
                    or lw[i] in _FILLERS or lw[i] in AUX or lw[i] in _CUE_WORDS or lw[i] in _TRAIL or concepts(lw[i]):
                continue
            if i > 0 and lw[i - 1] in ("i", "we", "you", "they", "he", "she"):
                continue                 # "I earn": a verb, not a value
            if i > 0 and lw[i - 1] in ("since", "until", "till", "after", "before", "during"):
                continue                 # "since college": when, not what
            for L in (2, 1):
                j = i + L
                if j > n or any(not ws[x][0].isalpha() or lw[x] in STOP or lw[x] in _FILLERS or lw[x] in NON_VALUES
                                or lw[x] in CATEGORY_NOUNS or lw[x] in _CUE_WORDS or lw[x] in _QUANT or lw[x] in _TRAIL
                                or concepts(lw[x])
                                for x in range(i, j)):
                    continue
                if j < n and lw[j] in _HEAD_NOUNS:
                    continue             # "a dentist appointment", "my driving lesson": the word only describes the noun
                if i > 0 and lw[i - 1] in ("the", "my", "our", "this", "that", "his", "her", "their") and j < n and \
                        lw[j] in ("is", "are", "was", "were", "keeps", "isn't", "won't", "doesn't", "broke", "stopped", "has", "needs"):
                    continue             # "the heating is broken": what the sentence is about, not a favourite
                cat = typer.category(" ".join(ws[i:j]) if ws[i][0].isupper() and i > 0 else " ".join(lw[i:j]))
                if cat:
                    typed.append((i, j, " ".join(ws[i:j]), cat))
                    break
    # an opening "Work-wise," / "Honestly," is not a value; neither is an age or a duration ("three years old"),
    # when the sentence offers anything else
    # "Work-wise, I'm a dentist.", "Honestly, I …": an opening word before an I-clause is never the value;
    # nor is a duration ("for five years", "three years old")
    cands = [x for x in cands if not (x.start == 0 and x.end + 1 < n and ws[x.end] == "," and x.kind == "NAME"
                                      and lw[x.end + 1] in ("i", "we"))
             and not (x.kind == "NUMBER" and (any(w in _DURATION for w in lw[x.start:x.end])
                                              or (x.end < n and lw[x.end] in _DURATION)))]
    if len(cands) + len(typed) > 1:
        keep = [x for x in cands if not (x.start == 0 and x.end < n and ws[x.end] == "," and x.kind == "NAME"
                                         and x.end + 1 < n and lw[x.end + 1] in ("i", "my", "we"))
                and not (x.kind == "NUMBER" and (any(w in _DURATION for w in lw[x.start:x.end])
                                                 or (x.end < n and lw[x.end] in _DURATION)
                                                 or lw[x.start] == "one"))
                # "since 2019", "in 2020": when, not what
                and not (x.kind == "DATE" and x.start > 0 and (
                    lw[x.start - 1] in ("since", "until", "till", "after", "before") or
                    (lw[x.start - 1] in ("in", "from") and re.fullmatch(r"\d{4}", x.text))))]
        if keep or typed:
            cands = keep
    value, vrange, kind, vcat = None, set(), "TEXT", None
    if cands and typed and all(x.kind == "NUMBER" for x in cands):
        cands = []                       # a counted food/colour/car word beats a bare number
    if cands:
        dates = [x for x in cands if x.kind == "DATE"]
        pick = dates[-1] if dates else [x for x in cands if x.start > 0 and lw[x.start - 1] in _VALUE_CUES][-1:] or \
            cands[-1:]
        pick = pick[-1] if isinstance(pick, list) else pick
        value, vrange, kind = pick.text, set(range(pick.start, pick.end)), pick.kind
        for a, b, _, cat in typed:
            if set(range(a, b)) == vrange:       # the whole value ("Toyota"), not a part ("… Motors")
                vcat = cat
    elif typed:
        # the strongest member (highest lift), a word right after a value cue a little preferred
        def strength(t):
            lf = typer.lift(t[2] if t[2][0].isupper() and t[0] > 0 else t[2].lower()) or {}
            return math.log(max(lf.get(t[3], 1.0), 1.0)) + (0.5 if t[0] > 0 and lw[t[0] - 1] in _VALUE_CUES else 0.0)
        a, b, text, vcat = max(typed, key=lambda t: (strength(t), t[0]))
        value, vrange = text, set(range(a, b))
    else:
        fp = [f for f in first_person_facts(sentence, source) if f.object.lower() not in NON_VALUES]
        if fp:
            f = fp[0]
            obj = f.object if f.kind != "TEXT" else _trim_value(f.object)
            obj_words = set(norm_entity(obj).split())
            value, kind = obj, f.kind
            vrange = {i for i, w in enumerate(lw) if w in obj_words}
        else:
            m = re.match(r"^((?:[\w'-]+ ){0,2}[\w'-]+) (?:is|are|was) (?:my|what|who|the one|the thing)\b", s,
                         flags=re.I)
            if m and m.group(1).lower() not in _FIRST:
                value = m.group(1)
                vrange = set(range(0, len(words(value))))
            else:
                for cue in [i for i, w in enumerate(lw) if w in _VALUE_CUES][::-1] + [-1]:
                    j = cue + 1
                    while j < n and (lw[j] in ("a", "an", "the") or lw[j] in _FIRST or lw[j] in CATEGORY_NOUNS
                                     or lw[j] in _FILLERS or not ws[j][0].isalnum()):
                        j += 1
                    k = j
                    while k < n and k - j < 3 and ws[k][0].isalnum() and lw[k] not in STOP \
                            and lw[k] not in CATEGORY_NOUNS and lw[k] not in _FILLERS and lw[k] not in _NUMBER_WORDS:
                        k += 1
                    if k > j and not all(lw[x] in NON_VALUES for x in range(j, k)) and lw[j] not in _VALUE_CUES:
                        value, vrange = " ".join(ws[j:k]), set(range(j, k))
                        break
    extra: list[Fact] = []
    if owned:
        # "My brother, Casgaiep, lives abroad.": a name right after "my <brother>," is its name
        e = max(owned) + 1
        app = [x for x in cands if x.kind == "NAME" and (
            (x.start == e + 1 and e < n and ws[e] == "," and (x.end >= n or ws[x.end] in (",", "-", "—", "–")))
            or x.start == e)]
        if app:
            extra.append(Fact(subject, ("#name", "name"), app[0].text, source, sentence.strip(), "NAME"))
            if value == app[0].text:
                return extra
    if not value:
        return extra
    rest = " ".join(w for i, w in enumerate(lw) if i not in vrange and i not in owned and w not in _FIRST)
    rel = [w for w in _rel_words(rest) if w not in ("hi", "hello", "really", "last", "year", "years", "ago",
                                                     "now", "today", "trade")]
    # the concept groups see the first-person words too ("people know me as", "my city")
    rel += concepts(" ".join(w for i, w in enumerate(lw) if i not in vrange and i not in owned))
    for f in first_person_facts(sentence, source):     # the template reading adds its relation words
        rel += [w for w in f.relation if w not in POSSESSED]
    if _JOB_AT.search(rest):
        rel = [w for w in rel if w not in ("job", "position", "post", "#job")]
    first_v = sorted(vrange)[0] if vrange else 0
    has_category = bool(set(rel) & CATEGORIES)
    # "I am a nurse", "I have been a pilot for years", "I became a qualified baker", "I practise as a
    # dentist": an occupation, whatever else the word may be
    art = [j for j in range(max(0, first_v - 3), first_v) if lw[j] in ("a", "an")]
    last_v = max(vrange) if vrange else first_v
    np_end = last_v + 1 >= n or not ws[last_v + 1][0].isalpha() or lw[last_v + 1] in STOP or \
        lw[last_v + 1] in _NUMBER_WORDS or lw[last_v + 1] in ("currently", "now", "professionally")
    if kind == "TEXT" and not has_category and art and subject == USER and np_end and \
            not set(lw[art[-1] + 1:]) & _NOT_A_JOB:          # "i'm a beginner", "i'm a morning person": no occupation
        before = lw[max(0, art[-1] - 3):art[-1]]
        if any(w in ("am", "was", "been", "became", "become", "becoming", "as", "remain", "remained") for w in before):
            rel += ["#job", "#work"]
            has_category = True
    if value and _COUNT_OF.match(value) and value.split()[-1].lower() in POSSESSED:
        vcat = None                      # "I have two kids": how many, not a job or a food
        rel = [w for w in rel if w not in ("#job", "#work")] + ["have"]
        has_category = True
    if vcat and value and value[:1].isupper() and first_v > 0 and vcat not in concepts(" ".join(lw)) and \
            vcat in ("#food", "#colour", "#car", "#job"):
        vcat = None             # a capitalised name with no food/colour/car/job word around it ("I watched Inception")
    if vcat == "#job" and value and set(value.lower().split()) & _NOT_A_JOB:
        vcat = None                      # "i'm a beginner": not an occupation, whatever the word typer says
        rel = [w for w in rel if w not in ("#job", "#work")]
    if vcat == "#job" and not re.search(r"\b(?:i'?m|i am|im|she'?s|he'?s|they'?re|is|was|are|were|became|become|becoming|be)\b|"
                                         r"\bwork(?:s|ing|ed)? (?:as|in)\b|\b(?:job|jobs|profession|career|employed|trained|qualified|as an?)\b", " ".join(lw)):
        vcat = None                      # "i keep dying at the first boss": a job word, but no sentence about a job
        rel = [w for w in rel if w not in ("#job", "#work")]
    if vcat == "#job" and ("#fav" in rel or "#dislike" in rel or set(lw) & {"loves", "love", "likes", "like", "enjoys",
                                                                           "enjoy", "adores", "adore", "hates", "hate"}):
        vcat = None                      # "my sister loves art": a liking, not her job
    if vcat and (not has_category or vcat in rel):
        rel.append(vcat)
    if "#fav" in rel and re.search(r"\b(?:it'?s|it is|its|that'?s|that is|was|feels|felt|looks|looked|sounds|seems|seemed) like\b|\blike (?:\d|a few|maybe|about|around)\b",
                                   " ".join(lw)) and not re.search(r"\b(?:love|loves|favou?rite|enjoy|enjoys|i like|i really like|prefer)\b", " ".join(lw)):
        rel = [w for w in rel if w != "#fav"]   # "it's like 35 degrees": a filler "like", no favourite
    if "#fav" in rel and re.search(r"\b(?:things|stuff|something|anything|everything|bits) like\b|\bsuch as\b", " ".join(lw)) and \
            not re.search(r"\b(?:i (?:really )?like|i love|favou?rite|enjoy)\b", " ".join(lw)):
        rel = [w for w in rel if w != "#fav"]   # "small things like homework": an example, no favourite
    if "#name" in rel and re.search(r"\b(?:got|get|gets|getting|was|were|been|being|be) called (?:for|in|up|out|back|off|away|to|into|on|over|about)\b|"
                                    r"\bcalled (?:for|in|up|out|back|off) (?:jury|duty|work|a meeting|an interview|service)\b", " ".join(lw)):
        return extra                            # "i got called for jury duty": a summons, not a name
    if "#name" in rel and re.search(r"\b(?:a|an|the|this|that|one|another|some|phone|video|weird|strange|missed|scam|spam|work|late|quick|short|long)\s+(?:\w+\s+)?calls?\b",
                                    " ".join(lw)) and not re.search(r"\bcalls? me\b|\bcalled\b|\bmy name\b|\bnamed\b", " ".join(lw)):
        return extra                            # "i got a weird call from someone": a phone call, not a name
    # "My employer's name is X", "a company called X": the name of that thing, not your name
    if "#name" in rel and set(rel) & (CATEGORIES - {"#name"}) and subject == USER and \
            not re.search(r"\b(?:i am|call me|calls me|my name)\b", " ".join(lw)):
        rel = [w for w in rel if w not in ("#name", "name", "called", "named")]
    # "Dunepnix Motors", "Kavel Foods": a name ending in a word the corpus counts with companies
    if kind == "NAME" and typer is not None and len(words(value)) >= 2 and "#employer" not in rel:
        lf = typer.lift(words(value)[-1]) or {}
        if lf.get("#employer", 0.0) >= 3.5:
            rel.append("#employer")
    if kind == "NUMBER" and first_v > 0 and lw[first_v - 1] in ("at", "by", "around") and \
            re.fullmatch(r"\d{1,2}(?:[:.]\d{2})?(?: ?[ap]\.?m\.?)?|\d{1,2} o'?clock", value.lower()):
        kind = "DATE"                    # "an appointment at 3": a time of day, not a count
    if kind == "DATE" or re.fullmatch(r"(?:next |this |on )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
                                      r"tomorrow|today|tonight", value.lower()):
        # "My new job starts next Monday": when, not what the job is ("You work as Monday")
        rel = [w for w in rel if w not in ("#job", "#work", "#employer")]
        kind = "DATE"
    if kind == "NAME" and first_v >= 2 and lw[first_v - 2:first_v] == ["i", "am"]:
        rel += ["name", "#name"]               # "I'm Frotam": a name
    if kind == "NAME" and implicit and _NAME_INTRO.match(s):
        rel += ["name", "#name"]               # "Frotam here.", "This is Frotam speaking."
    if kind == "NAME" and subject != USER and "#name" not in rel and not has_category:
        rel += ["#name"]                        # the name of your dog / brother
    if "#job" in rel and value and set(value.lower().split()) & _NOT_A_JOB:
        rel = [w for w in rel if w not in ("#job", "#work")]   # "i'm drowning in emails at work": emails are no job
    if "#home" in rel and value and (re.search(r"\bstay(?:ing|ed)? up\b|\bhome (?:in|on|next|this|tomorrow|tonight|today|after)\b", s) or
                                     re.fullmatch(r"\d{1,2}(?:[:.]\d\d)?(?: ?[ap]\.?m\.?)?|midnight|noon|late|one|two|three|four|five|six|seven|eight|nine|ten|a few|a couple|tomorrow|today|soon", value.lower())):
        return extra                            # "i'll try to stay up until 10", "i'm flying home in two days": no home
    if "#home" in rel and value:
        value = re.sub(r"\s+(?:tomorrow|today|tonight|soon|later|next (?:week|month|year|weekend)|this (?:week|weekend|month|year))$", "", value, flags=re.I)
    return extra + [Fact(subject, tuple(sorted(set(rel))), value, source, sentence.strip(), kind if kind != "TEXT"
                         else object_kind(value))]


def third_person_facts(sentence: str, source: str, initial_is_name=None) -> list[Fact]:
    """Two or more names (or a name and a date/number) → one fact per (first name, later
    argument); relation = the other content words."""
    sp = spans(sentence, initial_is_name)
    names = [x for x in sp if x.kind == "NAME"]
    values = [x for x in sp if x.kind in ("DATE", "NUMBER")]
    if not names:
        return []
    subj = names[0]
    objs = [x for x in names[1:]] + [v for v in values if v.start >= subj.end]
    if not objs:
        return []
    ws = words(sentence)
    out = []
    used = set(range(subj.start, subj.end))
    for o in objs:
        span_words = set(range(o.start, o.end)) | used
        rel = [w for i, w in enumerate(ws) if i not in span_words]
        rel = _rel_words(" ".join(rel)) + concepts(" ".join(rel))
        out.append(Fact(subj.text, tuple(sorted(set(rel))), o.text, source, sentence.strip(), o.kind))
    return out


_IMPLICIT_CONCEPTS = frozenset(("#fav", "#home", "#name", "#birth", "#job", "#employer", "#car", "#food", "#colour"))


_NEGATED_LIKE = re.compile(r"\b(?:don'?t|do not|didn'?t|never|not|can'?t|cannot)\s+(?:really\s+|much\s+|even\s+)?"
                           r"(?:like|love|enjoy|stand|care for|prefer)\b")


_NEGATED_HAVE = re.compile(r"\b(?:don'?t|do not|didn'?t|did not|no longer|never) (?:have|own|got)\b|\bhave no\b|"
                           r"\bhaven'?t got\b|\b(?:ran|run|running|am|i'm|im) out of\b")


_AND_I = re.compile(r"(?i)(?<=\w),?\s+and\s+(?=i(?:'m|m| am| work| live| have| like| love| study| drive| was| go)\b)")


# "I moved to a new city": a place without a name is not where you live
_GENERIC_PLACE = re.compile(r"(?i)^(?:a |an |the |my )?(?:new |different |another |big |small |little |nice |other )?"
                            r"(?:city|town|village|place|country|apartment|flat|house|home|area|neighbou?rhood|state|region)$")


# "Leonardo da Vinci was born in vinci": a named subject, never a statement about you
_NAMED_SUBJECT = re.compile(r"^(?:[A-Z][\w'’.-]+)(?: (?:[A-Z][\w'’.-]+|da|de|di|von|van|der|of|the|la|le|du|del|bin|al))+ "
                            r"(?:was|is|were|are|has|had|died|lived|grew)\b")


# "-ing" words that do name a line of work ("I work in marketing")
_ING_JOBS = frozenset("""marketing engineering nursing accounting banking consulting teaching training publishing
advertising catering farming fishing mining printing plumbing lending programming designing modelling modeling
recruiting tutoring coaching computing manufacturing retailing logistics""".split())


def _with_age(f: Fact) -> Fact:
    """"I'm 29", "I am 29 years old", "my dog is 3 years old": the number is an age (#age)."""
    if f.kind == "NUMBER" and re.fullmatch(r"\d{1,3}", f.object) and 0 < int(f.object) < 120 and \
            set(w for w in f.relation if not w.startswith("#")) <= {"am", "is", "old", "aged", "age", "years", "turned"} and \
            "#age" not in f.relation:
        return Fact(f.subject, tuple(sorted(f.relation + ("#age",))), f.object, f.source, f.sentence, f.kind)
    return f


def facts_from_text(text: str, source: str, initial_is_name=None, splitter=None, typer=None) -> list[Fact]:
    sents = splitter(text) if splitter else re.split(r"(?<=[.!?])\s+", text.strip())
    # "I'm 29 and I work as a nurse": two facts, not one
    sents = [part for x in sents for part in (_AND_I.split(x) if re.match(r"(?i)\s*i(?:'m|m| am)\b", x) else [x])]
    out = []
    topic = None
    for s in sents:
        s = _CORRECTION_LEAD.sub("", s.strip())
        if not s:
            continue
        if s.endswith("?"):
            # "Colours? Orange, definitely.": a bare topic, answered by the next sentence
            tw = words(s)
            topic = s.rstrip("?").strip() if 0 < len(tw) <= 3 and tw[0].lower() not in QWORDS | AUX else None
            continue
        if topic is not None and not re.search(r"\b(i|my|me|we|our)\b", s.lower()):
            fs = personal_facts(f"My {topic.lower()} is {s}", source, initial_is_name, typer)
            out += [Fact(f.subject, f.relation, f.object, source, f"{topic}? {s}", f.kind) for f in fs]
            topic = None
            if fs:
                continue
        topic = None
        norm = _GREETING.sub("", normalise_first_person(s))
        low = norm.lower()
        if re.search(r"\b(i|my|me)\b", low):
            fp = personal_facts(s, source, initial_is_name, typer)
            if _NEGATED_HAVE.search(low):
                continue                     # "I don't have eggs": nothing owned, nothing liked
            if fp and _NEGATED_LIKE.search(low):
                # "I don't like movies": a dislike, never a favourite
                fp = [Fact(f.subject, tuple("#dislike" if r == "#fav" else r for r in f.relation)
                           + (() if "#fav" in f.relation else ("#dislike",)), f.object, f.source, f.sentence, f.kind)
                      for f in fp]
            fp = [_with_age(f) for f in fp if not ("#home" in f.relation and _GENERIC_PLACE.match(f.object))]
            if re.search(r"\ballergic\b|\ballergy\b", low):
                # "I'm allergic to peanuts": an allergy, never a favourite food
                fp = [Fact(f.subject, tuple(sorted({r for r in f.relation if r not in ("#fav", "#food", "#dislike", "#home", "#place", "#job",
                                                                                         "#work")} | {"#allergy"})), f.object, f.source, f.sentence, f.kind)
                      for f in fp]
            if re.search(r"\b(?:live|lives|lived|living) (?:together )?with\b", low):
                # "I live with my girlfriend": who you live with, not where
                fp = [Fact(f.subject, tuple(sorted({r for r in f.relation if r not in ("#home", "#place", "#origin")} | {"#housemate"})),
                           f.object, f.source, f.sentence, f.kind) for f in fp]
            if re.search(r"\b(?:haven'?t|havent|have not|hasn'?t|didn'?t|did not|not yet|never)\b", low):
                # "I haven't started studying": no job called "studying"
                fp = [f for f in fp if "#job" not in f.relation]
            fp = [f for f in fp if not ("#job" in f.relation and re.fullmatch(r"[a-z]+ing", f.object.lower())
                                        and f.object.lower() not in _ING_JOBS)]
            out += fp if fp else third_person_facts(s, source, initial_is_name)
            continue
        tp = third_person_facts(s, source, initial_is_name)
        if tp:
            out += tp
            continue
        # a short statement without "I"/"my" that is still about you: "Nothing beats curry.",
        # "Home is Lyon.", "Frotam here."
        if len(words(norm)) <= 8 and not re.search(r"\b(?:his|her|their|its|your|he|she|they)\b", low) and \
                not _NAMED_SUBJECT.match(norm.strip()) and \
                (set(concepts(low)) & _IMPLICIT_CONCEPTS or _NAME_INTRO.match(norm.strip())):
            imp = personal_facts(s, source, initial_is_name, typer, implicit=True)
            # "the flat was spotless": a description of the place, not where you live
            out += [f for f in imp if not ("#home" in f.relation and _DESCRIBING.fullmatch(f.object.lower()))]
    return out


_DESCRIBING = re.compile(r"(?:so |really |very |totally |completely |super |quite )?(?:[a-z]+(?:less|ful|ous|ive|ish|y)|clean|dirty|tidy|messy|new|old|big|"
                         r"small|tiny|huge|nice|perfect|fine|ok|okay|empty|cold|warm|hot|dark|bright|quiet|loud|noisy|cheap|expensive|"
                         r"spotless|broken|damp|gone|done|ready|great|awful|terrible|lovely|amazing)")


# ---------------------------------------------------------------------------
# the memory
# ---------------------------------------------------------------------------

@dataclass
class Recall:
    answer: str
    fact: Fact
    entity: str
    entity_sim: float
    confidence: float            # (similarity − 0.5) / (P_k − 0.5): 1 = exact relation, 0 = chance
    margin: float                # to the second-best filler, same scale
    raw: float = 0.0             # the similarity itself
    only: bool = False           # the entity has exactly one filler of the asked type (not you / yours)


@dataclass
class FactMemory:
    rel: RelationCoder
    ent: EntityCoder = field(default_factory=EntityCoder)
    facts: list[Fact] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    E: np.ndarray = field(default_factory=lambda: np.zeros((0, WORDS), dtype=np.uint64))
    records: list[np.ndarray] = field(default_factory=list)
    fillers: list[list[tuple[np.ndarray, int, bool]]] = field(default_factory=list)   # (F, fact index, inverse)
    exact: dict[str, int] = field(default_factory=dict)

    def build(self, facts: list[Fact]) -> FactMemory:
        """Replace the content by ``facts`` (order-independent result)."""
        self.facts = sorted(set(facts), key=lambda f: (f.source, f.subject, f.relation, f.object, f.sentence))
        pairs: dict[str, list[tuple[np.ndarray, np.ndarray, int, bool]]] = {}
        for i, f in enumerate(self.facts):
            r = self.rel.encode(f.relation)
            pairs.setdefault(f.subject if f.subject.startswith(USER) else norm_entity(f.subject), []).append(
                (r, rand_vec("filler", norm_entity(f.object)), i, False))
            if f.object and not f.subject.startswith(USER):
                pairs.setdefault(norm_entity(f.object), []).append(
                    (r ^ INV, rand_vec("filler", norm_entity(f.subject)), i, True))
        self.entities = sorted(pairs)
        self.exact = {e: k for k, e in enumerate(self.entities)}
        self.E = (np.stack([self.ent.encode(e) if not e.startswith(USER) else rand_vec("entity", e)
                            for e in self.entities])
                  if self.entities else np.zeros((0, WORDS), dtype=np.uint64))
        self.records, self.fillers = [], []
        for e in self.entities:
            ps = pairs[e]
            self.records.append(bundle([r ^ f for r, f, _, _ in ps]))
            self.fillers.append([(f, i, inv) for _, f, i, inv in ps])
        return self

    def digest(self) -> str:
        h = hashlib.sha256()
        for f in self.facts:
            h.update(repr((f.subject, f.relation, f.object, f.source, f.kind)).encode())
        for r in self.records:
            h.update(r.tobytes())
        return h.hexdigest()

    def find_entity(self, mentions: list[str], exact: bool = False) -> tuple[int, float, str]:
        """Best (entity index, similarity, mention); (−1, 0, '') if the memory is empty."""
        best = (-1, 0.0, "")
        if not self.entities:
            return best
        for m in mentions:
            if m.startswith(USER):
                # you, or something of yours: only an exact entry counts, never a look-alike
                k = self.exact.get(m, -1)
                return (k, 1.0, m) if k >= 0 else (-1, 0.0, "")
            if exact:
                k = self.exact.get(norm_entity(m), -1)
                if k >= 0 and best[1] < 1.0:
                    best = (k, 1.0, m)
                continue
            d = ham_many(self.E, self.ent.encode(m))
            k = int(np.lexsort((np.arange(len(d)), d))[0])
            s = 1.0 - int(d[k]) / BITS
            if s > best[1]:
                best = (k, s, m)
        return best

    def recall(self, mentions: list[str], rel_words: list[str], exact: bool = False,
               atype: str = "OTHER") -> Recall | None:
        k, es, m = self.find_entity(mentions, exact)
        if k < 0:
            return None
        mw = set(norm_entity(m).split()) if not m.startswith(USER) else {m.partition(":")[2]}
        rq = self.rel.encode([w for w in rel_words if w not in mw])
        u = self.records[k] ^ rq
        pool = self.fillers[k]
        qwords = [w for w in rel_words if w not in mw]
        fitting = [(f, i, inv) for f, i, inv in pool if not category_conflict(qwords, self.facts[i].relation)]
        pool = fitting or pool
        for ok_kinds in _KIND_OK.get(atype, ()):
            typed = [(f, i, inv) for f, i, inv in pool
                     if (self.facts[i].kind if not inv else "NAME") in ok_kinds]
            if typed:
                pool = typed
                break
        scored = []
        for f, i, inv in pool:
            s = sim(u ^ INV if inv else u, f)
            scored.append((s, i, inv))
        scored.sort(key=lambda x: (-x[0], x[1], x[2]))
        s, i, inv = scored[0]
        second = scored[1][0] if len(scored) > 1 else 0.5
        scale = max(majority_agreement(len(self.fillers[k])) - 0.5, 1e-9)
        fact = self.facts[i]
        answer = fact.subject if inv else fact.object
        typed_ok = atype in _KIND_OK
        mine = self.entities[k] == USER
        only = not mine and (len(self.fillers[k]) == 1 or (
            typed_ok and len(pool) == 1 and
            (self.facts[pool[0][1]].kind if not pool[0][2] else "NAME") in sum(_KIND_OK[atype], ())))
        return Recall(answer, fact, self.entities[k], es, (s - 0.5) / scale, (s - second) / scale, s, only)


# ---------------------------------------------------------------------------
# questions → (mentions, relation words)
# ---------------------------------------------------------------------------

def question_parts(question: str, initial_is_name=None) -> tuple[list[str], list[str]]:
    """Candidate entity mentions (names, n-grams, USER for first person) and relation words."""
    q = expand_contractions(question.strip()).rstrip("?").strip()
    q = re.sub(r"\bour\b", "my", q, flags=re.I)
    ws = words(q)
    lw = [w.lower().replace("’", "'") for w in ws]
    mentions: list[str] = []
    used: set[int] = set()
    for i, w in enumerate(lw):
        if w == "my":
            for j in range(i + 1, min(i + 4, len(lw))):
                noun = lw[j][:-2] if lw[j].endswith("'s") else lw[j]
                if noun in POSSESSED:
                    nxt = lw[j + 1][:-2] if j + 1 < len(lw) and lw[j + 1].endswith("'s") else (
                        lw[j + 1] if j + 1 < len(lw) else "")
                    if nxt in POSSESSED:          # "my pet dog": the dog
                        used.add(j)
                        j, noun = j + 1, nxt
                    mentions.append(possessed_key(noun))
                    used.add(j)
                    break
    personal = any(w in FIRST_PERSON and w != "me" for w in lw) or any(
        w == "me" and (i == 0 or lw[i - 1] not in ("tell", "show", "give", "remind", "let", "help", "explain",
                                                    "teach", "send", "find")) for i, w in enumerate(lw))
    if personal:
        mentions.append(USER)
    for sp in spans(q, initial_is_name):
        if sp.kind == "NAME" and sp.text.lower() not in QWORDS:
            mentions.append(sp.text)
            used |= set(range(sp.start, sp.end))
    content = [i for i, w in enumerate(lw) if w[0].isalnum() and w not in STOP and w not in QWORDS
               and w not in AUX]
    for n in (1, 2, 3):
        for a in range(len(content) - n + 1):
            idx = content[a:a + n]
            if idx[-1] - idx[0] == n - 1:
                mentions.append(" ".join(ws[i] for i in idx))
    rel = [w for i, w in enumerate(lw) if i not in used]
    rest = " ".join(rel)
    joined = " ".join(w for w in lw if w[0].isalnum())
    extra = ["name", "#name"] if re.search(r"\bwho (?:am i|i am|is (?:talking|speaking|chatting|writing) (?:to|with) "
                                           r"you)\b", joined) else []
    if extra and USER not in mentions:
        mentions.append(USER)
        personal = True
    if personal and (re.search(r"\bwhere (?:am|are|is|was|were|do|does|did) (?:i|you|we)\b.* from$", joined)
                     or re.search(r"\b(?:my|what|which) (?:city|town|village|country|hometown|place|house)\b",
                                  joined)):
        extra += ["#home", "#place"]            # where you are from / your city: your home
    out = _rel_words(rest) + concepts(rest) + extra
    if personal and re.search(r"\bwhere\b", joined) and "#job" in out and not re.search(r"\bas\b", joined):
        out = [w for w in out if w != "#job"] + ["#employer"]      # where my job is: the employer
    if personal and re.search(r"\bwhere\b", joined) and "#work" in out and "#job" not in out:
        out += ["#employer"]
    cats = {w for w in out if w in CATEGORIES} - {"#name"}
    if "#name" in out and cats and not re.search(r"\bwho\b", joined):
        out = [w for w in out if w != "#name"]      # "what's my company called": the company, not a name
    return mentions, out
