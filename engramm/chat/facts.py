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
    ("#job", re.compile(r"\b(job|jobs|profession|occupation|career|works? as|worked as|working as|living as|at work|"
                        r"earns? (?:a |my )?living|do for (?:a )?(?:work|living)|by trade|trade)\b")),
    ("#employer", re.compile(r"\b(employer|company|firm|workplace|works? (?:at|for)|worked (?:at|for)|"
                             r"working (?:at|for)|employ\w*|where (?:do )?i work)\b")),
    ("#work", re.compile(r"\b(work|works|worked|working)\b")),
    ("#home", re.compile(r"\b(home|hometown|residence|live|lives|lived|living in|reside|resides|moved? to|"
                         r"moving to|relocated to)\b")),
    ("#birth", re.compile(r"\b(birthday|birth|born|birthplace|birthdate)\b")),
    ("#car", re.compile(r"\b(car|cars|vehicle|drive|drives|driving)\b")),
    ("#food", re.compile(r"\b(food|foods|eat|eating|meal|meals|dish|cuisine)\b")),
    ("#colour", re.compile(r"\b(colou?rs?)\b")),
    ("#fav", re.compile(r"\b(favou?rite|love|loves|like|likes|prefer|prefers|best|most|adore|adores|enjoy|"
                        r"enjoys)\b")),
    ("#name", re.compile(r"\b(name|names|named|called|call)\b")),
    ("#place", re.compile(r"\b(where|place|city|town|country)\b")),
]


CONCEPT_PARENTS = {"#job": "#work", "#employer": "#work"}
CATEGORIES = frozenset(("#food", "#colour", "#car", "#job", "#employer", "#home", "#birth", "#name"))


def category_conflict(a, b) -> bool:
    """Both relation word sets name a category, and no category is shared."""
    ca, cb = set(a) & CATEGORIES, set(b) & CATEGORIES
    return bool(ca and cb and not ca & cb)


_JOB_AT = re.compile(r"\b(?:a |the |my )?(?:job|position|post) (?:at|with|for)\b")


def concepts(text: str) -> list[str]:
    low = text.lower().replace("’", "'")
    if _JOB_AT.search(low):              # "a job at X": X is the employer, not the occupation
        low = _JOB_AT.sub(" employer ", low)
    out = [label for label, rx in CONCEPTS if rx.search(low)]
    out += [CONCEPT_PARENTS[c] for c in out if c in CONCEPT_PARENTS and CONCEPT_PARENTS[c] not in out]
    return out


POSSESSED = frozenset((
    "brother", "sister", "mother", "mom", "mum", "father", "dad", "wife", "husband", "son", "daughter", "partner",
    "girlfriend", "boyfriend", "friend", "boss", "dog", "cat", "pet", "horse", "bird", "grandmother", "grandfather",
    "grandma", "grandpa", "uncle", "aunt", "cousin", "neighbour", "neighbor", "colleague", "baby", "child", "kid",
    "fiance", "fiancee", "roommate", "flatmate"))
_CONTRACTIONS = [(r"\bwhat's\b", "what is"), (r"\bwho's\b", "who is"), (r"\bwhere's\b", "where is"),
                 (r"\bwhen's\b", "when is"), (r"\bhow's\b", "how is"), (r"\bthat's\b", "that is"),
                 (r"\bit's\b", "it is"), (r"\bi'm\b", "i am"), (r"\bi've\b", "i have"), (r"\bi'd\b", "i would"),
                 (r"\bi'll\b", "i will"), (r"\bdon't\b", "do not"), (r"\bdoesn't\b", "does not"),
                 (r"\bdidn't\b", "did not"), (r"\bcan't\b", "can not"), (r"\bwon't\b", "will not"),
                 (r"\bisn't\b", "is not"), (r"\bwe're\b", "we are"), (r"\byou're\b", "you are")]
_LEADING = re.compile(r"^(?:(?:these days|nowadays|currently|right now|now|at the moment|actually|by the way|btw|"
                      r"well|so|also|and|oh|anyway|just so you know|fyi|for the record)[, ]+)+", re.I)


def expand_contractions(text: str) -> str:
    t = text.replace("’", "'")
    for rx, rep in _CONTRACTIONS:
        t = re.sub(rx, lambda m, rep=rep: rep if m.group(0)[0].islower() else rep.capitalize(), t, flags=re.I)
    return t


def possessed_key(noun: str) -> str:
    return f"{USER}:{noun}"


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
    s = re.sub(r"\bour\b", "my", s, flags=re.I)
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


_GREETING = re.compile(r"^(?:hi|hello|hey|hiya|greetings|good (?:morning|afternoon|evening))\b[,!. ]*", re.I)
_VALUE_CUES = frozenset(("is", "am", "are", "was", "were", "a", "an", "as", "love", "loves", "like", "likes", "own",
                         "owns", "drive", "drives", "be", "called", "named", "at", "in", "to", "on", "by", "enjoy",
                         "prefer", "adore", "adores", "eat", "eats", "drink", "drinks", "play", "plays", "wear",
                         "wears"))
_FIRST = frozenset(("i", "my", "me", "mine", "myself"))
CATEGORY_NOUNS = frozenset(("colour", "color", "colours", "colors", "food", "dish", "meal", "car", "vehicle", "job",
                            "city", "town", "name", "company", "employer", "work", "profession", "occupation",
                            "birthday", "place", "home", "favourite", "favorite", "best"))
NON_VALUES = frozenset(("favourite", "favorite", "best", "most", "one", "thing", "stuff", "it", "that", "this"))


def personal_facts(sentence: str, source: str, initial_is_name=None) -> list[Fact]:
    """A statement about you or something of yours, without sentence templates:

    * subject: you, or "my <brother/dog/…>" as its own entity;
    * value: the name, date or number the sentence mentions; if there is none, the value
      the templates find, else the words after the last verb/article cue, or the subject
      of "X is my …";
    * relation: every other content word, plus the concept groups."""
    s = _GREETING.sub("", normalise_first_person(sentence)).strip()
    ws = words(s)
    lw = [w.lower() for w in ws]
    n = len(ws)
    if not any(w in _FIRST for w in lw):
        return []
    subject, owned = USER, set()
    for i, w in enumerate(lw):
        if w in ("have", "has", "got") and i + 2 < n and lw[i + 1] in ("a", "an", "one"):
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
                    subject = possessed_key(noun)
                    owned = set(range(i, j + 1))
                    break
            if owned:
                break
    cands = [x for x in spans(s, initial_is_name) if x.kind in ("NAME", "DATE", "NUMBER")
             and not (set(range(x.start, x.end)) & owned) and lw[x.start] not in _FIRST]
    value, vrange, kind = None, set(), "TEXT"
    if cands:
        dates = [x for x in cands if x.kind == "DATE"]
        pick = dates[-1] if dates else [x for x in cands if x.start > 0 and lw[x.start - 1] in _VALUE_CUES][-1:] or \
            cands[-1:]
        pick = pick[-1] if isinstance(pick, list) else pick
        value, vrange, kind = pick.text, set(range(pick.start, pick.end)), pick.kind
    else:
        fp = [f for f in first_person_facts(sentence, source) if f.object.lower() not in NON_VALUES]
        if fp:
            f = fp[0]
            obj_words = set(norm_entity(f.object).split())
            value, kind = f.object, f.kind
            vrange = {i for i, w in enumerate(lw) if w in obj_words}
        else:
            m = re.match(r"^((?:[\w'-]+ ){0,2}[\w'-]+) (?:is|are|was) my\b", s, flags=re.I)
            if m and m.group(1).lower() not in _FIRST:
                value = m.group(1)
                vrange = set(range(0, len(words(value))))
            else:
                for cue in [i for i, w in enumerate(lw) if w in _VALUE_CUES][::-1] + [-1]:
                    j = cue + 1
                    while j < n and (lw[j] in ("a", "an", "the") or lw[j] in _FIRST or lw[j] in CATEGORY_NOUNS):
                        j += 1
                    k = j
                    while k < n and k - j < 3 and ws[k][0].isalnum() and lw[k] not in STOP \
                            and lw[k] not in CATEGORY_NOUNS:
                        k += 1
                    if k > j and not all(lw[x] in NON_VALUES for x in range(j, k)):
                        value, vrange = " ".join(ws[j:k]), set(range(j, k))
                        break
    if not value:
        return []
    rest = " ".join(w for i, w in enumerate(lw) if i not in vrange and i not in owned and w not in _FIRST)
    rel = [w for w in _rel_words(rest) if w not in ("hi", "hello", "really", "last", "year", "years", "ago",
                                                     "now", "today", "trade")]
    rel += concepts(rest)
    for f in first_person_facts(sentence, source):     # the template reading adds its relation words
        rel += [w for w in f.relation if w not in POSSESSED]
    if _JOB_AT.search(rest):
        rel = [w for w in rel if w not in ("job", "position", "post", "#job")]
    for i in sorted(vrange)[:1]:
        if kind == "NAME" and i >= 2 and lw[i - 2:i] == ["i", "am"]:
            rel += ["name", "#name"]           # "I'm Frotam": a name
    return [Fact(subject, tuple(sorted(set(rel))), value, source, sentence.strip(), kind if kind != "TEXT" else
                 object_kind(value))]


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


def facts_from_text(text: str, source: str, initial_is_name=None, splitter=None) -> list[Fact]:
    sents = splitter(text) if splitter else re.split(r"(?<=[.!?])\s+", text.strip())
    out = []
    for s in sents:
        s = s.strip()
        if not s or s.endswith("?"):
            continue
        low = _GREETING.sub("", normalise_first_person(s)).lower()
        if re.search(r"\b(i|my|me)\b", low):
            fp = personal_facts(s, source, initial_is_name)
            out += fp if fp else third_person_facts(s, source, initial_is_name)
        else:
            out += third_person_facts(s, source, initial_is_name)
    return out


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
    extra = ["name", "#name"] if re.fullmatch(r"who am i", " ".join(w for w in lw if w[0].isalnum())) else []
    return mentions, _rel_words(rest) + concepts(rest) + extra
