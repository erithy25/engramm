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
                 "will", "would", "can", "could", "please", "tell", "know", "remember", "you", "your"))
QWORDS = frozenset(("what", "which", "who", "whom", "whose", "when", "where", "why", "how", "kind", "type",
                    "sort"))
REL_STOP = STOP - frozenset(("name", "named", "called", "call", "known", "most", "one", "first"))
PLACE_PREPS = frozenset(("in", "at", "near", "from"))

# Hand-written concept groups (general English, applied the same way to statements and
# questions): a member word adds the group's label to the relation words.
CONCEPTS = [
    ("#job", re.compile(r"\b(job|jobs|profession|occupation|career|works? as|worked as|working as)\b")),
    ("#employer", re.compile(r"\b(employer|company|firm|workplace|works? (?:at|for)|worked (?:at|for)|"
                             r"working (?:at|for))\b")),
    ("#work", re.compile(r"\b(work|works|worked|working)\b")),
    ("#home", re.compile(r"\b(home|hometown|residence|live|lives|lived|living|reside|resides)\b")),
    ("#birth", re.compile(r"\b(birthday|birth|born)\b")),
    ("#car", re.compile(r"\b(car|cars|vehicle|drive|drives|driving)\b")),
    ("#food", re.compile(r"\b(food|foods|eat|eating|meal|meals|dish|cuisine)\b")),
    ("#colour", re.compile(r"\b(colou?rs?)\b")),
    ("#fav", re.compile(r"\b(favou?rite|love|loves|like|likes|prefer|prefers|best|most)\b")),
    ("#name", re.compile(r"\b(name|names|named|called|call)\b")),
    ("#place", re.compile(r"\b(where|place|city|town|country)\b")),
]


def concepts(text: str) -> list[str]:
    low = text.lower().replace("’", "'")
    return [label for label, rx in CONCEPTS if rx.search(low)]


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
    # (regex on the lower-cased sentence, relation words, object group)
    (re.compile(r"^(?:people |everyone |friends )?call me (?P<o>.+)$"), ("name", "called"), "o"),
    (re.compile(r"^(?:i am|i'm) (?:called|named) (?P<o>.+)$"), ("name", "called"), "o"),
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
    (re.compile(r"^(?:i am|i'm) (?:a |an )?(?P<o>[a-z0-9' -]+?) by (?P<r>[a-z]+)$"), (), "o"),
    (re.compile(r"^i (?P<v>[a-z]+(?: [a-z]+)?) (?P<p>in|at|on|for|as|with|from|to|near|under) "
                r"(?:a |an |the )?(?P<o>.+)$"), (), "o"),
    (re.compile(r"^i was (?P<v>born|raised|married) (?P<p>in|on|at|to) (?P<o>.+)$"), (), "o"),
    (re.compile(r"^(?:i am|i'm) (?:a |an )?(?P<o>[a-z0-9' -]+)$"), ("am",), "o"),
    (re.compile(r"^i (?P<v>drive|own|have|play|speak|study|use|ride|keep) (?:a |an |the )?(?P<o>.+)$"), (), "o"),
]


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
    s = sentence.strip().rstrip(".!").strip()
    low = s.lower().replace("’", "'")
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
        rel += concepts(head)
        return [Fact(USER, tuple(sorted(set(rel))), obj, source, sentence.strip(), object_kind(obj))]
    return []


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
        low = s.lower()
        if re.match(r"^(i|my|i'm|people call me|call me|the [a-z ]+ i )\b", low):
            out += first_person_facts(s, source)
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
            pairs.setdefault(norm_entity(f.subject) if f.subject != USER else USER, []).append(
                (r, rand_vec("filler", norm_entity(f.object)), i, False))
            if f.object and f.subject != USER:
                pairs.setdefault(norm_entity(f.object), []).append(
                    (r ^ INV, rand_vec("filler", norm_entity(f.subject)), i, True))
        self.entities = sorted(pairs)
        self.exact = {e: k for k, e in enumerate(self.entities)}
        self.E = (np.stack([self.ent.encode(e) if e != USER else rand_vec("entity", USER) for e in self.entities])
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
            if m == USER:
                k = self.exact.get(USER, -1)
                if k >= 0:
                    return k, 1.0, m
                continue
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
        mw = set(norm_entity(m).split()) if m != USER else set()
        rq = self.rel.encode([w for w in rel_words if w not in mw])
        u = self.records[k] ^ rq
        pool = self.fillers[k]
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
        return Recall(answer, fact, self.entities[k], es, (s - 0.5) / scale, (s - second) / scale, s)


# ---------------------------------------------------------------------------
# questions → (mentions, relation words)
# ---------------------------------------------------------------------------

def question_parts(question: str, initial_is_name=None) -> tuple[list[str], list[str]]:
    """Candidate entity mentions (names, n-grams, USER for first person) and relation words."""
    q = question.strip().rstrip("?").strip()
    ws = words(q)
    lw = [w.lower().replace("’", "'") for w in ws]
    mentions: list[str] = []
    used: set[int] = set()
    if any(w in FIRST_PERSON for w in lw):
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
    return mentions, _rel_words(rest) + concepts(rest)
