"""ENGRAMM-Chat v2 — the conversation (stages 3 and 4, docs/PREREG_CHAT_V2.md).

One turn = one user message → one reply. What the message is, is decided by rules:

* **forget** — "forget …", "please delete what I told you about …": the best-matching
  text you taught is forgotten exactly (the language model and the fact memory are pure
  functions of the live texts, so the state equals never having been told).
* **question** — ends with "?" or starts with a question word. Pronouns ("he", "it",
  "this person", "that city") are replaced by the last answer or topic. First the HDC
  fact memory is asked; questions about yourself ("my …", "I …") are answered only from
  what you told. Otherwise ENGRAMM looks the answer up (stage 1.1) and cuts a short
  answer out of the best sentences (stage 4) — or says "I don't know".
* **small talk** — greetings, thanks, "who are you".
* **statement** — anything else is learnt (with ``learn_text``) and confirmed.

The memory (``memory``) is either the ENGRAMM language model (``HDCLanguageModel`` or its
logged wrapper) or ``TextMemory`` for tests; both expose ``user_texts``, ``learn_text``,
``forget`` and a state digest.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
import time
from dataclasses import asdict, dataclass, field

import numpy as np

from engramm.chat.extract import ExtractParams, extract
from engramm.chat.facts import (USER, FactMemory, RelationCoder, category_conflict, facts_from_text, norm_entity,
                                question_parts, _rel_words)
from engramm.chat.question import LOCATION, OTHER, PERSON, PROPER, STOP, analyse, spans, type_matches, words
from engramm.chat.retrieve import FEATURES, Retriever, Weights
from engramm.lm.chat import B, K1, _soft_match

CHAT_PREFIX = "chat:"
CATEGORY_KIND = {"#car": "NAME", "#food": "TEXT", "#colour": "TEXT", "#job": "TEXT", "#home": "NAME",
                 "#birth": "DATE", "#employer": "NAME", "#name": "NAME"}
CATEGORY_WORD = {"#car": "car", "#food": "food", "#colour": "colour", "#job": "job", "#home": "city",
                 "#employer": "company", "#name": "name"}


# ---------------------------------------------------------------------------
# configuration (frozen on dev before the test run)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BotConfig:
    weights: Weights = Weights()
    extract: ExtractParams = ExtractParams()
    text_k: int = 120                  # candidates that get text features
    theta: float = 0.0                 # answer confidence below → "I don't know"
    entity_min: float = 0.60           # fact memory: entity similarity needed
    fact_min: float = 0.30             # fact memory: normalised filler similarity needed
    only_fact: bool = False            # answer with the one known fact of the asked type even if the relation
                                       # words differ (never for facts about you)
    focus_gate: bool = True            # a name in the question must occur in the evidence document
    span_model: str = "spanstats.json"  # counted span statistics (naive Bayes) or "spanperc*.json" (perceptron)
    span_model_nq: str = ""            # optional second perceptron for search-box queries (lower case, no "?")
    extract_nq: ExtractParams | None = None  # answer-cutting parameters for search-box queries (None: ``extract``)
    calibrator: str = ""               # optional counted confidence model for question-form lookups (calib.py)
    weights_nq: Weights | None = None  # search weights for search-box queries (None: ``weights``)


class TextMemory:
    """The smallest memory with the interface the bot needs (tests, development)."""

    def __init__(self):
        self.user_texts: dict[str, str] = {}

    def learn_text(self, text: str, source_id: str) -> None:
        if source_id in self.user_texts:
            raise ValueError(f"source {source_id!r} already learnt")
        self.user_texts[source_id] = text

    def forget(self, source_id: str) -> str:
        del self.user_texts[source_id]
        return "user"

    def state_digest(self) -> str:
        h = hashlib.sha256()
        for sid, text in sorted(self.user_texts.items()):
            h.update(f"{sid}\x00{text}\x01".encode())
        return h.hexdigest()


def _model_of(memory):
    return getattr(memory, "model", memory)


@dataclass
class Reply:
    message: str
    kind: str                          # answer | unknown | learned | known | forgot | nothing | smalltalk
    text: str                          # what ENGRAMM says
    answer: str | None = None          # the short answer (None when abstaining)
    guess: str | None = None           # best guess even when abstaining
    evidence: str | None = None        # the sentence the answer comes from
    source: dict | None = None
    confidence: float = 0.0
    via: str = ""                      # facts | lookup | memory
    resolved: str | None = None        # the question after replacing pronouns
    alternatives: list = field(default_factory=list)
    seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# message types
# ---------------------------------------------------------------------------

_QSTART = frozenset(("what", "which", "who", "whom", "whose", "when", "where", "why", "how", "is", "are", "was",
                     "were", "do", "does", "did", "can", "could", "will", "would", "should", "has", "have", "had",
                     "tell", "name", "list", "give", "say", "remind", "whats", "wheres", "whos", "hows", "whens"))
_FORGET_VERB = (r"(?:forget|delete|remove|erase|drop|unlearn|wipe|clear|discard|purge|scrap|throw away|throw out|"
                r"get rid of|stop remembering|do not remember|don't remember|no longer remember|dump)")
_FORGET = re.compile(r"^(?:(?:please|kindly|now|ok|okay|and|so)\s*,?\s+)*"
                     r"(?:(?:can|could|would|will) you\s+(?:please\s+)?|i(?: want| need| would like|'d like|’d like) "
                     r"you to\s+|"
                     r"you (?:can|should|may|must)\s+|please\s+)?" + _FORGET_VERB + r"\b\s*(.*)$", re.IGNORECASE)
_SMALLTALK = [
    (re.compile(r"^(hi|hello|hey|hallo|good (morning|afternoon|evening)|greetings)\b[\s!.,]*(engramm)?[\s!.]*$",
                re.I), "Hello! Ask me something, or tell me something and I will remember it."),
    (re.compile(r"^(thanks|thank you|thx|cheers)\b.*$", re.I), "You're welcome."),
    (re.compile(r"^(who|what) are you\??$|^what(?:'s| is) your name\??$", re.I),
     "I'm ENGRAMM. I answer from the texts I have read and from what you tell me — only by counting, "
     "without any neural network — and I show you where every answer comes from."),
    (re.compile(r"^(bye|goodbye|see you)\b.*$", re.I), "Goodbye!"),
]
_PERSON_PRON = ("he", "she", "him", "his", "hers", "they", "them", "their")
_THING_PRON = ("it", "its", "there")
_PERSON_NOUNS = ("person", "man", "woman", "guy", "individual", "fellow", "lady", "gentleman", "author", "writer",
                 "founder", "inventor", "painter", "poet", "composer", "captain", "architect", "owner", "explorer",
                 "discoverer", "teacher", "leader", "chief", "king", "queen", "player", "artist", "scientist")
_THING_NOUNS = ("city", "town", "village", "place", "country", "region", "area", "state", "nation", "company", "firm",
                "river", "island", "book", "novel", "ship", "team", "film", "movie", "band", "album", "song",
                "building", "bridge", "festival", "horse", "organisation", "organization")
# "that one", "this guy", "said person", "the latter": a demonstrative before a kind of noun points back; the bare
# "the" only before a few safe nouns ("Who is the author of …?" must stay a new question)
_DEMONSTRATIVE = re.compile(r"\b(?:(?:this|that|the same|said|the aforementioned)\s+(" + "|".join(_PERSON_NOUNS
                            + _THING_NOUNS) + r"|one)|the\s+(person|man|woman|city|town|latter(?!\s+(?:half|part|stage|years?|case|one)\b)))\b", re.I)
_PERSONISH = frozenset(_PERSON_NOUNS)
# a question about "my sibling" may be answered by what you said about your brother or sister
_RELATED = {"sibling": ("brother", "sister"), "pet": ("dog", "cat"), "parent": ("mother", "father"),
            "child": ("son", "daughter"), "kid": ("son", "daughter"), "dog": ("pet",), "cat": ("pet",),
            "brother": ("sibling",), "sister": ("sibling",), "children": ("kids", "child", "son", "daughter"),
            "kids": ("children",), "siblings": ("brothers", "sisters"), "pets": ("dogs", "cats")}


_FORGET_AFTER = re.compile(r"^(?:never mind|scratch|ignore|about)\s+(.+?)\s*[,;.:–—-]?\s*(?:just\s+|please\s+|so\s+)?"
                           r"(?:forget|delete|drop|erase|remove)\s+(?:it|that|about it|this)\b.*$", re.IGNORECASE)


def forget_topic(msg: str) -> str | None:
    """The topic of a forget request ("" = the last thing you said), or None if it is none."""
    m = _FORGET_AFTER.match(msg.strip())
    if m:
        return m.group(1)
    m = _FORGET.match(msg.strip())
    return m.group(1) if m else None


_CONTRACTED_Q = {"what's": "what", "who's": "who", "where's": "where", "when's": "when", "how's": "how",
                 "why's": "why", "which's": "which", "what're": "what", "who're": "who", "how're": "how",
                 "whats": "what", "whos": "who", "wheres": "where", "hows": "how", "wht": "what", "wat": "what",
                 "wut": "what", "wer": "where", "hw": "how"}


def message_type(msg: str) -> str:
    s = msg.strip()
    if not s:
        return "empty"
    if forget_topic(s) is not None:
        return "forget"
    for rx, _ in _SMALLTALK:
        if rx.match(s):
            return "smalltalk"
    first = words(s.lower())[0] if words(s) else ""
    first = _CONTRACTED_Q.get(first, first)           # "what's the capital of australia" without "?"
    if s.endswith("?") or s.lower().startswith(("do you remember", "tell me")):
        return "question"
    if first == "say" and re.match(r"^say (?:hello|hi|hey|goodbye|bye)\b", s.lower()):
        return "statement"               # "Say hello to my dog Rex."
    if first in _QSTART:
        # "When it comes to food, I love curry." / "Where I live, it rains." — a clause first, then a statement
        if first in ("when", "where", "while", "if") and re.search(r",\s+(?:i|my|we|our)\b", s.lower()):
            return "statement"
        return "question"
    # an unfinished statement ("the capital of France is") asks for its end
    if re.search(r"\b(is|are|was|were|by|of|called|named)\s*$", s.lower().rstrip(".!")) and \
            not re.search(r"\b(?:it|that|this|so be it|there it|here it) (?:is|was)\s*$", s.lower().rstrip(".!")):
        return "question"
    return "statement"


def normalize_value(v: str) -> str:
    return " ".join(v.lower().split())


def name_initial_rule(word: str, tok, cap: dict) -> bool:
    if word.lower() in STOP:
        return False
    ids = tok.encode(" " + word.lower())
    if len(ids) != 1:
        return True
    first = tok.token_bytes()[ids[0]].decode("utf-8", errors="replace").strip().lower()
    r = cap.get(first)
    return True if r is None else r > 0.5


def source_id(text: str) -> str:
    """Content-derived id: the same text always gets the same id (exact forgetting)."""
    return CHAT_PREFIX + hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# the bot
# ---------------------------------------------------------------------------

_WH_TERMS = frozenset("when where who whom whose what which why how".split())
# the life span after the name in an article's first sentence (Wikipedia's convention)
_LIFE_SPAN = re.compile(r"\((?:[^()]*?[;,]\s*)?(?:born\s+)?(?:c\.\s*)?[^()]*?\b\d{3,4}\s*[–—-]\s*[^()]*?\b\d{3,4}\)")


class ChatBot:
    def __init__(self, memory, corpus, config: BotConfig = BotConfig(), cap_ratio: dict | None = None,
                 retriever: Retriever | None = None):
        self.memory = memory
        self.c = corpus
        self.cfg = config
        self.r = retriever or Retriever(corpus)
        self.extra_only = False                 # set by the dialog when the extra rows hold the named article
        self.cap = cap_ratio or {}
        self.facts = FactMemory(RelationCoder(corpus.wide if corpus.wide is not None else corpus.eng, corpus.tok))
        self._facts_key = None
        self._user_sents_key = None
        self._user_sents: list[tuple[str, str, np.ndarray]] = []
        # Atlas (engramm/web): sentences fetched for this one question (shelf, feeds, web), each with
        # its source; empty unless a channel is on — then the look-up is exactly the v3 one
        self.extra_rows: list[tuple] = []
        # (confidence model, θ) for answers whose sentence came from a network channel (Atlas)
        self.extra_calib = None
        self.context = {"answer": None, "atype": None, "mention": None, "last_learned": None}
        self._name_memo: dict[str, bool] = {}
        self.last_rows: list = []
        self.span_stats, self.word_info = None, None
        self.span_stats_nq = None
        self.typer = None
        self._soft_memo: dict = {}
        if getattr(corpus, "index", None) is not None and getattr(corpus.index, "n", 0) > 100_000:
            from engramm.chat.lexicon import Typer
            self.typer = Typer(corpus)
        sp = getattr(corpus, "index_dir", None)
        if config.extract.nb > 0 and sp is not None and (sp / config.span_model).exists() \
                and corpus.classes is not None:
            from engramm.chat.spanstats import SpanPerceptron, SpanStats, WordInfo
            self.span_stats = (SpanPerceptron.load(sp / config.span_model, compact=True) if config.span_model.startswith("spanperc")
                               else SpanStats.load(sp / config.span_model))
            if config.span_model_nq and (sp / config.span_model_nq).exists():
                self.span_stats_nq = SpanPerceptron.load(sp / config.span_model_nq, compact=True)
            self.word_info = WordInfo(corpus.tok, corpus.classes, corpus.wide)
        self.calib = None
        if config.calibrator and sp is not None and (sp / config.calibrator).exists():
            from engramm.chat.calib import ConfCalibrator
            self.calib = ConfCalibrator.load(sp / config.calibrator)

    # -- helpers ---------------------------------------------------------------------------

    def is_name_initial(self, word: str) -> bool:
        """Is a capitalised sentence-initial word a name? Known words: only if the corpus
        writes them capitalised mid-sentence more often than not; unknown words (not a
        single vocabulary token): yes."""
        w = self._name_memo.get(word)
        if w is None:
            w = name_initial_rule(word, self.c.tok, self.cap)
            self._name_memo[word] = w
        return w

    def is_name_initial_fact(self, word: str) -> bool:
        """The same rule for statements and questions in a conversation, with one addition: a
        word that the corpus writes in lower case mid-sentence more often than not
        ("Professionally", "Honestly") is not a name."""
        if not self.is_name_initial(word):
            return False
        if self.typer is None:
            return True
        ls = self.typer.lower_share(word)
        return ls is None or ls < 0.5

    def user_texts(self) -> dict[str, str]:
        return dict(_model_of(self.memory).user_texts)

    def refresh(self) -> None:
        """Rebuild the fact memory from the live texts (a pure function of them)."""
        texts = self.user_texts()
        key = tuple(sorted(texts.items()))
        if key == self._facts_key:
            return
        facts = []
        for sid, text in sorted(texts.items()):
            facts += facts_from_text(text, sid, self.is_name_initial_fact, typer=self.typer)
        self.facts.build(facts)
        self._facts_key = key
        sents = []
        for sid, text in sorted(texts.items()):
            for s in re.split(r"(?<=[.!?])\s+", text.strip()):
                if s.strip():
                    sents.append((sid, s.strip(), np.asarray(self.c.tok.encode(" " + s.strip()), dtype=np.int64)))
        self._user_sents = sents

    def memory_digest(self) -> str:
        """Everything ENGRAMM knows beyond what it has read: language-model state + fact memory."""
        self.refresh()
        m = _model_of(self.memory)
        h = hashlib.sha256(m.state_digest().encode())
        h.update(self.facts.digest().encode())
        return h.hexdigest()

    # -- turns -----------------------------------------------------------------------------

    def turn(self, message: str) -> Reply:
        t0 = time.time()
        msg = " ".join(message.strip().split())
        kind = message_type(msg)
        if kind == "empty":
            rep = Reply(message, "nothing", "Please type something.")
        elif kind == "forget":
            rep = self._forget(msg)
        elif kind == "smalltalk":
            rep = next(Reply(message, "smalltalk", text) for rx, text in _SMALLTALK if rx.match(msg))
        elif kind == "question":
            rep = self._answer(msg)
        else:
            rep = self._learn(msg)
        rep.message = message
        rep.seconds = time.time() - t0
        return rep

    def ask(self, question: str) -> Reply:
        """Answer ``question`` as a question whatever its form (evaluation, the /api/ask route)."""
        t0 = time.time()
        rep = self._answer(" ".join(question.strip().split()))
        rep.message = question
        rep.seconds = time.time() - t0
        return rep

    # -- learning and forgetting -------------------------------------------------------------

    def _learn(self, msg: str) -> Reply:
        sid = source_id(msg)
        if sid in self.user_texts():
            return Reply(msg, "known", "I already know that.", source={"kind": "user", "source": sid})
        self.memory.learn_text(msg, sid)
        self.refresh()
        self.context["last_learned"] = sid
        fs = [f for f in self.facts.facts if f.source == sid]
        if fs and fs[0].subject.startswith(USER + ":"):
            text = f"Got it — your {fs[0].subject.partition(':')[2]}: {fs[0].object}."
        elif fs and fs[0].subject == USER:
            rel = " ".join(w for w in fs[0].relation if not w.startswith("#")) or "fact"
            text = f"Got it — I'll remember that ({rel}: {fs[0].object})."
        elif fs:
            text = f"Got it — I'll remember that about {fs[0].subject}."
        else:
            text = "Got it — I'll remember that."
        return Reply(msg, "learned", text, source={"kind": "user", "source": sid}, via="memory")

    def _forget(self, msg: str) -> Reply:
        topic = forget_topic(msg).strip().rstrip(".!?").strip()
        topic = re.sub(r",?\s*(?:please|thanks|thank you)$", "", topic, flags=re.I).strip()
        topic = re.sub(r"\s+(?:from|out of) (?:your|the) (?:memory|mind|head|records?|database|brain)\b.*$", "", topic,
                       flags=re.I).strip()
        topic = re.sub(r"\s+(?:anymore|any more|for good|forever|completely|entirely|at once|now)$", "", topic,
                       flags=re.I).strip()
        topic = re.sub(r"^(?:(?:what|everything|all|anything) (?:i (?:told you|said|said to you|mentioned|shared|"
                       r"wrote)|you (?:know|remember|have|learned|learnt|heard)) (?:about|on|regarding|of)|"
                       r"everything (?:about|on|regarding)|all about|the (?:information|info|facts?|details?|stuff) "
                       r"(?:about|on|regarding)|about|the fact that|that)\s+", "", topic, flags=re.I).strip()
        texts = {s: t for s, t in self.user_texts().items() if s.startswith(CHAT_PREFIX)}
        if not texts:
            return Reply(msg, "nothing", "You haven't told me anything I could forget.")
        if topic.lower() in ("everything", "all", "all of it", "everything you know about me"):
            gone = sorted(texts)
        elif topic.lower() in ("", "it", "this", "that") and self.context["last_learned"] in texts:
            gone = [self.context["last_learned"]]
        else:
            best = self._match_topic(topic, texts)
            gone = [best] if best else []
        if not gone:
            return Reply(msg, "nothing", f"I don't have anything about “{topic}” to forget.")
        for sid in gone:
            self.memory.forget(sid)
        self.refresh()
        what = "; ".join(f"“{texts[s]}”" for s in gone[:3]) + (" …" if len(gone) > 3 else "")
        return Reply(msg, "forgot", f"Done — I have forgotten {what}. It is gone from my memory, not just hidden.",
                     via="memory")

    def _match_topic(self, topic: str, texts: dict[str, str]) -> str | None:
        """The taught text that best matches the topic of a forget request.

        Points: the entity (you, something of yours, or a name) must fit; shared category
        groups (colour, food, car, …) weigh 2, weaker groups 0.5, shared words 0.5; a
        category conflict costs 3; the kind of value a category expects (cars and cities are
        names, food and jobs ordinary words, birthdays dates) ±0.5; and, where a value has a
        counted meaning vector, its similarity to the category word."""
        from engramm.chat.facts import CATEGORIES, concepts
        self.refresh()
        mentions, rel = question_parts(topic, self.is_name_initial_fact)
        owned = [m for m in mentions if m.startswith(USER + ":")]
        target = owned[0] if owned else (USER if USER in mentions else None)
        tlabels = {w for w in rel if w.startswith("#")} | set(concepts(topic))
        twords = {w for w in rel if not w.startswith("#")}
        topic_words = set(norm_entity(topic).split())
        rq = self.facts.rel.encode(rel) if rel else None
        scored = []
        for sid, text in texts.items():
            fs = [f for f in self.facts.facts if f.source == sid]
            best = None
            for f in fs:
                if target is not None:
                    if f.subject != target:
                        continue
                else:
                    ent = set(norm_entity(f.subject).split()) | set(norm_entity(f.object).split())
                    if not ent & topic_words:
                        continue
                flabels = {w for w in f.relation if w.startswith("#")}
                s = 1.0
                s += sum(2.0 if lab in CATEGORIES else 0.5 for lab in tlabels & flabels)
                s += 0.5 * len(twords & set(f.relation))
                s += 0.25 * self._soft_overlap(twords, {w for w in f.relation if not w.startswith("#")})
                if rq is not None:
                    s += 0.3 * (1.0 - int(np.bitwise_count(rq ^ self.facts.rel.encode(f.relation)).sum()) / 2048)
                if category_conflict(tlabels, flabels):
                    s -= 3.0
                for lab in tlabels & CATEGORIES:
                    want = CATEGORY_KIND.get(lab)
                    if want:
                        s += 0.5 if f.kind == want else -0.5
                    vs = self._value_similarity(CATEGORY_WORD.get(lab), f.object)
                    if vs is not None:
                        s += 5.0 * (vs - 0.6)
                best = s if best is None else max(best, s)
            if best is None and not fs and target is None:
                best = 0.5 * len(twords & set(_rel_words(text)))
            if best is not None:
                scored.append((best, sid))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored[0][1] if scored and scored[0][0] > 0.55 else None

    def _soft_overlap(self, qwords: set, swords: set) -> float:
        """Σ over question words without an exact partner of their best meaning similarity to a
        sentence word, above chance (counted wide vectors; one-token words only)."""
        vecs = self.c.wide
        if vecs is None:
            return 0.0
        tok = self.c.tok
        total = 0.0
        sv = []
        for w in swords:
            ids = tok.encode(" " + w)
            if len(ids) == 1:
                sv.append(np.asarray(vecs[ids[0]]))
        if not sv:
            return 0.0
        S = np.stack(sv)
        for w in qwords - swords:
            ids = tok.encode(" " + w)
            if len(ids) != 1:
                continue
            best = 1.0 - int(np.bitwise_count(S ^ np.asarray(vecs[ids[0]])[None, :]).sum(axis=1).min()) / 2048
            total += max(0.0, (best - 0.62) / 0.38)
        return total

    def _value_similarity(self, word: str | None, value: str):
        """Meaning-vector similarity of a category word and a one-token value, else None."""
        vecs = self.c.wide if self.c.wide is not None else None
        if vecs is None or not word:
            return None
        tok = self.c.tok
        a = tok.encode(" " + word)
        b = tok.encode(" " + value.strip())
        if len(a) != 1 or len(b) != 1:
            return None
        return 1.0 - int(np.bitwise_count(np.asarray(vecs[a[0]]) ^ np.asarray(vecs[b[0]])).sum()) / 2048

    # -- questions --------------------------------------------------------------------------

    def resolve(self, q: str) -> str:
        """Replace one pronoun / demonstrative by the last answer or topic."""
        ctx = self.context
        if not ctx["answer"] and not ctx["mention"]:
            return q
        person = ctx["answer"] if ctx["atype"] == PERSON and ctx["answer"] else ctx["mention"]
        gender = getattr(self, "person_gender", None)
        pm = re.search(r"\b(he|him|his|she|her|hers)\b", q, re.I)
        if gender is not None and pm and ctx["answer"] and ctx["mention"] and ctx["answer"] != ctx["mention"]:
            want = "female" if pm.group(1).lower() in ("she", "her", "hers") else "male"
            ga, gm = gender(ctx["answer"]), gender(ctx["mention"])
            if ga and ga != want and gm != ga:
                person = ctx["mention"]               # "how old is he?" after "Obama's wife is Michelle": Obama
            elif gm and gm != want and ga != gm:
                person = ctx["answer"]
        thing = ctx["answer"] if ctx["atype"] in (LOCATION, PROPER, OTHER) and ctx["answer"] else ctx["mention"]
        m = _DEMONSTRATIVE.search(q)
        if m:
            noun = (m.group(1) or m.group(2)).lower()
            # "that one" names no kind: it points at the last answer, whatever its type
            target = ((ctx["answer"] or ctx["mention"]) if noun in ("one", "latter")
                      else (person if noun in _PERSONISH else thing))
            if target:
                return q[:m.start()] + target + q[m.end():]
        ws = q.split(" ")
        for i, w in enumerate(ws):
            core = re.sub(r"[^\w']", "", w).lower()
            tail = w[len(w.rstrip("?.!,")):]
            if core in (*_PERSON_PRON, "her") and person and getattr(self, "not_a_person", None) is not None \
                    and core not in ("they", "them", "their") and self.not_a_person(person):
                return q                             # "who is his wife?" after a book: not about the book
            if core in _PERSON_PRON and person:
                rep = person + "'s" if core in ("his", "their", "hers") else person
                ws[i] = rep + tail
                return " ".join(ws)
            if core in _THING_PRON and thing:
                rep = thing + "'s" if core == "its" else ("in " + thing if core == "there" else thing)
                ws[i] = rep + tail
                return " ".join(ws)
            if core == "her" and person:
                nxt = ws[i + 1] if i + 1 < len(ws) else ""
                ws[i] = (person + "'s" if nxt and nxt[0].isalpha() and nxt.lower() not in STOP else person) + tail
                return " ".join(ws)
        return q

    def _answer(self, msg: str) -> Reply:
        self.refresh()
        self.last_rows = []
        q = self.resolve(msg)
        from engramm.chat.facts import expand_contractions
        qa = analyse(q) if "'" not in q and "’" not in q else analyse(expand_contractions(q))
        mentions, rel = question_parts(q, self.is_name_initial_fact)
        about_user = any(m.startswith(USER) for m in mentions)
        if about_user:
            found = self._personal_answer(qa, mentions, rel)
            if found is not None:
                f, score = found
                return self._finish(msg, q, qa, "answer", f.object, f.object, f.sentence,
                                    {"kind": "user", "source": f.source}, score, "facts")
            found = self._user_lookup(q, qa, mentions, rel)
            if found is not None:
                answer, sentence, sid = found
                return self._finish(msg, q, qa, "answer", answer, answer, sentence, {"kind": "user", "source": sid},
                                    0.0, "memory")
            return self._finish(msg, q, qa, "unknown", None, None, None, None, 0.0, "facts",
                                text="I don't know — you haven't told me that (or you asked me to forget it).")
        # 1. the fact memory: a clear symbolic match (shared category / words) first, then the HDC unbinding
        rec = self.facts.recall(mentions, rel, atype=qa.atype)
        if rec and rec.entity_sim >= self.cfg.entity_min and not rec.entity.startswith(USER):
            found = self._entity_answer(rec.entity, qa, rel)
            if found is not None and found[2] >= 2.0:
                answer, f, score = found
                return self._finish(msg, q, qa, "answer", answer, answer, f.sentence,
                                    {"kind": "user", "source": f.source}, score, "facts", mention=rec.entity)
        if rec and rec.entity_sim >= self.cfg.entity_min and (
                rec.confidence >= self.cfg.fact_min or (self.cfg.only_fact and rec.only)):
            weak = rec.confidence < self.cfg.fact_min
            text = (f"{rec.answer} — the only thing I know about {rec.fact.subject if rec.fact.object == rec.answer else rec.fact.object} "
                    f"is: “{rec.fact.sentence}”") if weak else None
            return self._finish(msg, q, qa, "answer", rec.answer, rec.answer, rec.fact.sentence,
                                {"kind": "user", "source": rec.fact.source}, rec.confidence, "facts",
                                mention=rec.entity if not rec.entity.startswith(USER) else None, text=text)
        if rec and rec.entity_sim >= self.cfg.entity_min:
            # the relation words differ ("come into the world" ↔ "born"): points on this entity's facts
            found = self._entity_answer(rec.entity, qa, rel)
            if found is not None:
                answer, f, score = found
                return self._finish(msg, q, qa, "answer", answer, answer, f.sentence,
                                    {"kind": "user", "source": f.source}, score, "facts", mention=rec.entity)
        # 2. look it up and cut out a short answer
        return self._lookup(msg, q, qa, mentions)

    def soft_labels(self, ws) -> set:
        """Category groups the corpus counts for these words and adjacent word pairs ("salary" →
        job, "big day" → birthday, "daily driver" → car); used for points only, never to rule a
        fact out."""
        if self.typer is None:
            return set()
        from engramm.chat.lexicon import ANCHORS
        ws = [w.lower() for w in ws if w and w[0].isalpha() and w.lower() not in STOP and len(w) > 2]
        key = tuple(ws)
        got = self._soft_memo.get(key)
        if got is None:
            groups = tuple(ANCHORS)
            got = set()
            for text in ws + [f"{a} {b}" for a, b in zip(ws, ws[1:])]:
                c = self.typer.category(text, groups)
                lf = self.typer.lift(text) if c else None
                if c and lf and lf.get(c, 0.0) >= 5.0:      # soft groups need a clear lift (not "currently")
                    got.add(c)
            self._soft_memo[key] = got
        return got

    def fact_soft_labels(self, f) -> set:
        vw = set(w.lower() for w in words(f.object))
        from engramm.chat.facts import FIRST_PERSON
        return self.soft_labels([w for w in words(f.sentence) if w.lower() not in vw and w.lower() not in FIRST_PERSON])

    def _fact_points(self, f, qlabels: set, qwords: set, rq, want: str | None, qsoft: set = frozenset()
                     ) -> float | None:
        """Points of a fact for a question (None: its category contradicts the question)."""
        from engramm.chat.facts import CATEGORIES
        flabels = {w for w in f.relation if w.startswith("#")}
        fwords = {w for w in f.relation if not w.startswith("#")}
        if category_conflict(qlabels, flabels):
            return None
        shared = qlabels & flabels
        s = 2.0 * len(shared & CATEGORIES) + 0.5 * len(shared - CATEGORIES)
        if self.typer is not None:
            fsoft = self.fact_soft_labels(f)
            s += 1.0 * len(((qsoft | qlabels) & (fsoft | flabels)) - shared)
        s += 0.5 * len(qwords & fwords)
        s += 0.25 * self._soft_overlap(qwords - fwords, fwords)
        if rq is not None:
            s += 0.5 * max(0.0, (1.0 - int(np.bitwise_count(rq ^ self.facts.rel.encode(f.relation)).sum()) / 2048
                                 - 0.5) / 0.5)
        if want:
            s += 0.5 if f.kind == want else -1.0
        return s

    def _personal_answer(self, qa, mentions: list[str], rel: list[str]):
        """A question about you or something of yours, answered from the facts you told:
        each fact of that entity gets points (shared category 2, shared weaker group 0.5,
        shared word 0.5, meaning similarity of the words, HDC similarity of the relation
        bundles, the kind of value the question word expects); a fact whose category
        contradicts the question is out. The best fact answers if it has at least 1 point and
        leads the next by 0.25 — or if it is the only thing known about your dog/brother/…"""
        owned = [m for m in mentions if m.startswith(USER + ":")]
        target = owned[0] if owned else USER
        facts = [f for f in self.facts.facts if f.subject == target]
        if not facts and owned:
            # "my sibling" when you told me about your brother, "my pet" for your dog
            noun = target.partition(":")[2]
            alts = {USER + ":" + x for x in _RELATED.get(noun, ())}
            facts = [f for f in self.facts.facts if f.subject in alts]
        if not facts:
            return None
        qlabels = {w for w in rel if w.startswith("#")}
        mw = {target.partition(":")[2]} if owned else set()
        qwords = [w for w in rel if not w.startswith("#") and w not in mw]
        qsoft = self.soft_labels(qwords)
        qwords = set(qwords)
        rq = self.facts.rel.encode(sorted(qwords | qlabels)) if qwords or qlabels else None
        want = {PERSON: "NAME", LOCATION: "NAME", "DATE": "DATE", "NUMBER": "NUMBER"}.get(qa.atype)
        if want is None and "#birth" in qlabels:
            want = "DATE"                         # "What's my birthdate?": a date, whatever the question word
        scored = []
        for f in facts:
            pts = self._fact_points(f, qlabels, qwords, rq, want, qsoft)
            if pts is not None:
                scored.append((pts, f.source, f))
        if not scored:
            return None
        scored.sort(key=lambda x: (-x[0], x[1], x[2].object))
        best, _, f = scored[0]
        second = scored[1][0] if len(scored) > 1 else None
        if owned and len({x.subject for x in facts}) == 1 and len(facts) == 1 and best >= 0.0:
            return f, best
        if best >= 1.0 and (second is None or best - second >= 0.25):
            return f, best
        if owned and best >= 0.7 and second is not None and best - second >= 0.5:
            return f, best                        # "what does my sister love?": a clear lead among few facts
        if want in ("DATE", "NUMBER"):
            same = [x for _, _, x in scored if x.kind == want]
            if len(same) == 1:                  # the only date you told me, for a "when" question
                return same[0], best
        return None

    def _entity_answer(self, entity: str, qa, rel: list[str]):
        """Points (as for your own facts) on the facts about a named entity; answers only with
        a shared category or three shared words, and a lead of 0.25 over the next fact."""
        ew = set(entity.split())
        qlabels = {w for w in rel if w.startswith("#")}
        qwords = {w for w in rel if not w.startswith("#") and w not in ew}
        rq = self.facts.rel.encode(sorted(qwords | qlabels)) if qwords or qlabels else None
        want = {PERSON: "NAME", LOCATION: "NAME", "DATE": "DATE", "NUMBER": "NUMBER"}.get(qa.atype)
        scored = []
        for f in self.facts.facts:
            if norm_entity(f.subject) == entity:
                answer, kind = f.object, f.kind
            elif norm_entity(f.object) == entity and not f.subject.startswith(USER):
                answer, kind = f.subject, "NAME"
            else:
                continue
            pts = self._fact_points(f.__class__(f.subject, f.relation, answer, f.source, f.sentence, kind),
                                    qlabels, qwords, rq, want)
            if pts is not None:
                scored.append((pts, f.source, answer, f))
        if not scored:
            return None
        scored.sort(key=lambda x: (-x[0], x[1], x[2]))
        best, _, answer, f = scored[0]
        second = scored[1][0] if len(scored) > 1 else None
        if best >= 1.5 and (second is None or best - second >= 0.25):
            return answer, f, best
        return None

    def _user_lookup(self, q: str, qa, mentions: list[str], rel: list[str]):
        """A question about you that the fact memory could not answer: find the sentence you
        told that fits best (shared words and concept groups, no category conflict) and cut
        the answer out of it, as in the corpus look-up. Independent of how you phrased it."""
        from engramm.chat.facts import FIRST_PERSON, concepts, expand_contractions
        owned = [m.partition(":")[2] for m in mentions if m.startswith(USER + ":")]
        qwords = {w for w in rel if not w.startswith("#")}
        qconc = {w for w in rel if w.startswith("#")}
        best = None
        with_facts = {f.source for f in self.facts.facts}
        for sid, text, _ in self._user_sents:
            if sid in with_facts:
                continue            # sentences with a fact were already weighed by their facts
            low = expand_contractions(text).lower()
            tw = set(_rel_words(low))
            if not any(w in tw or w in FIRST_PERSON for w in words(low)) and "my" not in low.split():
                pass
            if owned and not all(o in words(low) for o in owned):
                continue
            subjects = {f.subject for f in self.facts.facts if f.source == sid}
            if not owned and subjects and all(x.startswith(USER + ":") for x in subjects):
                continue           # a sentence about your brother does not answer a question about you
            sc = concepts(low)
            if category_conflict(qconc, sc):
                continue
            score = len(qwords & tw) + len(qconc & set(sc)) + 0.5 * self._soft_overlap(qwords, tw)
            if score > 0.25 and (best is None or score > best[0]):
                best = (score, sid, text)
        if best is None:
            return None
        _, sid, text = best
        from engramm.chat.question import Question
        strip_q = Question(qa.text, qa.wh, qa.atype, qa.words + ["i", "my", "me"], qa.content, qa.head)
        x = extract(strip_q, [text], np.array([1.0]), self.cfg.extract, self.is_name_initial, None, self.span_stats,
                    self.word_info)
        fact_vals = [f.object for f in self.facts.facts if f.source == sid
                     and normalize_value(f.object) not in qwords and f.object.lower() not in ("favourite", "favorite")]
        answer = fact_vals[0] if fact_vals else x.text
        if not answer:
            return None
        return answer, text, sid

    def _user_candidates(self, query) -> list[tuple[float, str, str, dict]]:
        """Taught sentences scored with the same features (no document features)."""
        return self._score_sents(query, [(sid, text, toks, {"kind": "user", "source": sid})
                                         for sid, text, toks in self._user_sents])

    def _extra_candidates(self, query) -> list[tuple[float, str, str, dict, np.ndarray]]:
        """Atlas sentences (shelf, feeds, web) with the same features local sentences get, so the
        ranking weights and the confidence model read them alike: coverage, phrases, proximity
        and type match of the sentence; the article as document (its title as key words, the
        question terms anywhere in the fetched part as document coverage); question terms the
        sentence lacks but the two sentences before it hold as context coverage. The article's title
        counts as said in each of its sentences ("It was opened in 1931" in the article "Zorblax
        Bridge" covers "When was the Zorblax Bridge opened?"), so the other words decide."""
        if not self.extra_rows:
            return []
        if len(query.terms) == 0:
            return []
        enc = lambda t: np.asarray(self.c.tok.encode(" " + t), dtype=np.int64)   # noqa: E731
        terms_of = lambda t: [int(x) for x in self.r.term_of[enc(t)] if x >= 0]   # noqa: E731
        # question words are no evidence in a fetched sentence ("… in Philadelphia when WHAT-FM …")
        qw = {int(t): float(w) for t, w, st in zip(query.terms, query.idf, query.strings) if st not in _WH_TERMS}
        if not qw:
            return []
        isum = query.idf_sum or 1.0
        bigrams = {(int(a), int(b)): float(w) for (a, b), w in query.bigrams.items()}
        life = set(terms_of("born died"))
        qwords = set(query.q.words)
        wv = self.cfg.weights.vector()
        F = {n: i for i, n in enumerate(FEATURES)}
        rows = []
        title_terms: dict[str, set[int]] = {}
        doc_terms: dict[str, set[int]] = {}
        for row in self.extra_rows:
            text, src = row[0], row[1]
            ctx = row[2] if len(row) > 2 else ""
            key = str(src.get("key") or "")
            if key not in title_terms:
                title_terms[key] = set(terms_of(str(src.get("title") or "")))
                doc_terms[key] = set(title_terms[key])
            toks = enc(text)
            terms = [int(x) for x in self.r.term_of[toks] if x >= 0]
            doc_terms[key] |= set(terms)
            rows.append((text, src, ctx, key, toks, terms))
        out = []
        for text, src, ctx, key, toks, terms in rows:
            own = set(terms) & qw.keys()
            if not ctx and src.get("kind") in ("shelf", "web") and _LIFE_SPAN.search(text):
                own |= life & qw.keys()           # "X (February 8, 1899 – June 16, 1970) was …": born, died
            present = own | (title_terms[key] & qw.keys())     # the article's subject is implied in each sentence
            if not present:
                continue
            n_terms = len(terms)
            norm = K1 * (1.0 - B + B * n_terms / self.r.avglen)
            bm = sum(qw[t] * (K1 + 1.0) / (1.0 + norm) for t in present)
            phr, seen = 0.0, set()
            for a, b in zip(terms, terms[1:]):
                if a != b and (a, b) in bigrams and (a, b) not in seen:
                    seen.add((a, b))
                    phr += bigrams[(a, b)]
            pos = [i for i, t in enumerate(terms) if t in own]
            prox = len(set(terms[i] for i in pos)) / (pos[-1] - pos[0] + 1) if len(set(terms[i] for i in pos)) >= 2 \
                else 0.0
            around = set(terms_of(ctx)) if ctx else set()
            content = toks[self.r.term_of[toks] >= 0]
            f = np.zeros(len(FEATURES))
            f[F["bm25"]] = bm
            f[F["cov"]] = sum(qw[t] for t in present) / isum
            f[F["soft"]] = _soft_match(query.toks, query.idf, content, self.c.eng) if len(content) else 0.0
            f[F["pcov"]] = sum(w for t, w in qw.items() if t not in present and t in around) / isum
            f[F["kcov"]] = sum(w for t, w in qw.items() if t in title_terms[key]) / isum
            f[F["dcov"]] = f[F["dfull"]] = sum(w for t, w in qw.items() if t in doc_terms[key]) / isum
            f[F["phr"]] = phr / isum
            f[F["prox"]] = prox
            f[F["wiki"]] = float(src.get("kind") == "shelf")
            if query.q.atype != OTHER:
                f[F["tmatch"]] = float(any(type_matches(query.q.atype, sp)
                                           and not ({w.lower() for w in words(sp.text)} <= qwords)
                                           for sp in spans(text, self.is_name_initial)))
            f[F["isq"]] = float(text.rstrip('"”’\') ').endswith("?"))
            f[F["short"]] = float(len(words(text)) < 6)
            out.append((bm + isum * float(f @ wv), key, text, src, f))
        return out

    def _score_sents(self, query, items) -> list[tuple[float, str, str, dict]]:
        out = []
        if not items or len(query.terms) == 0:
            return out
        qset = {int(t): float(w) for t, w in zip(query.terms, query.idf)}
        isum = query.idf_sum or 1.0
        wv = self.cfg.weights.vector()
        for sid, text, toks, src in items:
            tm = self.r.term_of[toks]
            present = set(int(x) for x in tm if x >= 0)
            got = [qset[t] for t in present if t in qset]
            if not got:
                continue
            n_terms = int((tm >= 0).sum())
            norm = K1 * (1.0 - B + B * n_terms / self.r.avglen)
            bm = sum(w * (K1 + 1.0) / (1.0 + norm) for w in got)
            cov = sum(got) / isum
            content = toks[tm >= 0]
            soft = _soft_match(query.toks, query.idf, content, self.c.eng) if len(content) else 0.0
            tmatch = float(any(type_matches(query.q.atype, sp) for sp in spans(text, self.is_name_initial))
                           ) if query.q.atype != OTHER else 0.0
            f = np.zeros(len(FEATURES))
            F = {n: i for i, n in enumerate(FEATURES)}
            f[F["bm25"]], f[F["cov"]], f[F["soft"]], f[F["dcov"]], f[F["dfull"]] = bm, cov, soft, cov, cov
            f[F["tmatch"]] = tmatch
            f[F["short"]] = float(len(words(text)) < 6)
            score = bm + isum * float(f @ wv)
            out.append((score, sid, text, src))
        return out

    def _lookup(self, msg: str, q: str, qa, mentions: list[str]) -> Reply:
        from engramm.chat.spanstats import question_form
        search_box = question_form(qa) == "nq"
        weights = self.cfg.weights_nq if search_box and self.cfg.weights_nq is not None else self.cfg.weights
        cands = self.r.candidates(q, weights, self.cfg.text_k)
        query = cands.query
        rows = []
        sent_feats = {}
        if len(cands.ids):
            sc = cands.scores(weights)
            for k in range(len(cands.ids)):
                rows.append((float(sc[k]), 1, int(cands.ids[k]), cands.texts[k], None))
                sent_feats[int(cands.ids[k])] = cands.feats[k]
        for score, sid, text, src in self._user_candidates(query):
            rows.append((score, 0, -1, text, src))
        extra_feats = {}
        for score, sid, text, src, f in self._extra_candidates(query):
            rows.append((score, 0, -2, text, src))
            extra_feats[text] = f
        if self.extra_only and any(r[2] == -2 for r in rows):
            rows = [r for r in rows if r[2] == -2]       # the named article came from the shelf: only its sentences
        if not rows:
            return self._finish(msg, q, qa, "unknown", None, None, None, None, 0.0, "lookup",
                                text="I don't know — I found nothing about that.")
        rows.sort(key=lambda r: (-r[0], r[1], r[2], r[3]))
        params = self.cfg.extract_nq if search_box and self.cfg.extract_nq is not None else self.cfg.extract
        top = rows[:params.k]
        self.last_rows = top
        isum = max(query.idf_sum, 1e-9)
        texts = [r[3] for r in top]
        rel = np.array([r[0] / isum for r in top])
        stats = self.span_stats_nq if search_box and self.span_stats_nq is not None else self.span_stats
        x = extract(qa, texts, rel, params, self.is_name_initial, None, stats, self.word_info)
        if x.text is None:
            best = top[0]
            src = best[4] or self.c.source(best[2])
            return self._finish(msg, q, qa, "unknown", None, None, best[3], src, 0.0, "lookup",
                                text="I don't know. The closest I found is below.")
        row = top[x.sentence]
        theta = self.cfg.theta
        if self.calib is not None and not search_box and x.info is not None:
            from engramm.chat.calib import features as calib_features
            cal = self.calib
            if row[2] == -2 and self.extra_calib is not None:   # a shelf/feed/web sentence: its own model
                cal, theta = self.extra_calib
            sent = sent_feats.get(row[2]) if row[4] is None else extra_feats.get(row[3]) if row[2] == -2 else None
            feats = calib_features(x.info, x.text, qa.atype, qa.wh, len(qa.content), sent, x.sentence, cal.r0_bins)
            x = dataclasses.replace(x, confidence=cal.score(feats))
        # the sentence ENGRAMM presents as its best one is the one the answer comes from
        self.last_rows = [row] + [r for r in top if r is not row]
        src = row[4] or self.c.source(row[2])
        ok = x.confidence >= theta
        missing = self._focus_missing(q, row) if self.cfg.focus_gate else []
        alts = [{"text": r[3], "source": r[4] or self.c.source(r[2])} for r in top[:4] if r is not row][:3]
        if missing:
            return self._finish(msg, q, qa, "unknown", None, x.text, row[3], src, x.confidence, "lookup",
                                text=f"I don't know — I have not read anything about {' or '.join(missing)}.",
                                alternatives=alts)
        return self._finish(msg, q, qa, "answer" if ok else "unknown", x.text if ok else None, x.text, row[3], src,
                            x.confidence, "lookup", alternatives=alts)

    def _focus_missing(self, q: str, row) -> list[str]:
        """The capitalised names of the question that do not occur in the evidence's document
        (or taught text) — if any is missing, the answer would be about something else."""
        names = [sp.text for sp in spans(q, self.is_name_initial) if sp.kind == "NAME"]
        if not names:
            return []
        if row[2] < 0:
            hay = row[3].lower()
            if row[2] == -2 and row[4]:             # an Atlas sentence: its article title counts as context
                hay += " " + str(row[4].get("title") or row[4].get("source") or "").lower()
            return [n for n in names if n.lower() not in hay]
        d = int(self.c.sent_doc[row[2]])
        lo = int(self.c.doc_starts[d])
        hi = int(self.c.doc_starts[d + 1]) if d + 1 < self.c.n_docs else len(self.c.tokens)
        doc = np.asarray(self.c.tokens[lo:hi])
        key = " ".join(self.c.doc_keys[d][1].lower().split())
        missing = []
        for n in names:
            if n.lower() in key:
                continue
            found = False
            for form in (" " + n, n):
                pat = np.asarray(self.c.tok.encode(form), dtype=doc.dtype)
                if len(pat) == 0 or len(pat) > len(doc):
                    continue
                cand = np.flatnonzero(doc[:len(doc) - len(pat) + 1] == pat[0])
                for p in cand:
                    if np.array_equal(doc[p:p + len(pat)], pat):
                        found = True
                        break
                if found:
                    break
            if not found:
                missing.append(n)
        return missing

    def _finish(self, msg, q, qa, kind, answer, guess, evidence, source, conf, via, text=None, mention=None,
                alternatives=None) -> Reply:
        if text is None:
            if answer:
                text = f"{answer}."
            else:
                text = "I don't know." + (f" My best guess would be “{guess}”, but I'm not confident." if guess else "")
        # dialog context for pronouns in the next question
        m = mention
        if m is None:
            names = [sp.text for sp in spans(q, self.is_name_initial) if sp.kind == "NAME"]
            m = names[0] if names else self.context["mention"]
        # a pronoun in the next question may also point to the best guess shown ("My best guess would be X")
        ref = answer or guess
        self.context.update({"answer": ref, "atype": qa.atype if ref else None, "mention": m})
        return Reply(msg, kind, text, answer, guess, evidence, source, float(conf), via,
                     q if q != msg else None, alternatives or [])
