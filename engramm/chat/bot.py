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

import hashlib
import re
import time
from dataclasses import asdict, dataclass, field

import numpy as np

from engramm.chat.extract import ExtractParams, extract
from engramm.chat.facts import (USER, FactMemory, RelationCoder, facts_from_text, norm_entity, question_parts,
                                _rel_words)
from engramm.chat.question import LOCATION, OTHER, PERSON, PROPER, STOP, analyse, spans, type_matches, words
from engramm.chat.retrieve import FEATURES, Retriever, Weights
from engramm.lm.chat import B, K1, _soft_match

CHAT_PREFIX = "chat:"


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
    focus_gate: bool = True            # a name in the question must occur in the evidence document


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
                     "tell", "name", "list", "give", "in", "on", "at", "during", "from"))
_FORGET = re.compile(r"^(?:please\s+|can you\s+|could you\s+)?(?:forget|delete|remove|erase|drop|unlearn)\b\s*(.*)$",
                     re.IGNORECASE)
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
_DEMONSTRATIVE = re.compile(r"\b(this|that|the same)\s+(person|man|woman|city|town|place|country|company|river|"
                            r"island|book|novel|ship|team|one)\b", re.I)
_PERSONISH = frozenset(("person", "man", "woman"))


def message_type(msg: str) -> str:
    s = msg.strip()
    if not s:
        return "empty"
    if _FORGET.match(s):
        return "forget"
    for rx, _ in _SMALLTALK:
        if rx.match(s):
            return "smalltalk"
    first = words(s.lower())[0] if words(s) else ""
    if s.endswith("?") or first in _QSTART or s.lower().startswith(("do you remember", "tell me")):
        return "question"
    return "statement"


def source_id(text: str) -> str:
    """Content-derived id: the same text always gets the same id (exact forgetting)."""
    return CHAT_PREFIX + hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# the bot
# ---------------------------------------------------------------------------

class ChatBot:
    def __init__(self, memory, corpus, config: BotConfig = BotConfig(), cap_ratio: dict | None = None,
                 retriever: Retriever | None = None):
        self.memory = memory
        self.c = corpus
        self.cfg = config
        self.r = retriever or Retriever(corpus)
        self.cap = cap_ratio or {}
        self.facts = FactMemory(RelationCoder(corpus.wide if corpus.wide is not None else corpus.eng, corpus.tok))
        self._facts_key = None
        self._user_sents_key = None
        self._user_sents: list[tuple[str, str, np.ndarray]] = []
        self.context = {"answer": None, "atype": None, "mention": None, "last_learned": None}
        self._name_memo: dict[str, bool] = {}

    # -- helpers ---------------------------------------------------------------------------

    def is_name_initial(self, word: str) -> bool:
        w = self._name_memo.get(word)
        if w is None:
            if word.lower() in STOP:
                w = False
            else:
                ids = self.c.tok.encode(" " + word)
                first = self.c.tok.token_bytes()[ids[0]].decode("utf-8", errors="replace").strip().lower()
                r = self.cap.get(first)
                w = True if r is None else r > 0.5
            self._name_memo[word] = w
        return w

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
            facts += facts_from_text(text, sid, self.is_name_initial)
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

    # -- learning and forgetting -------------------------------------------------------------

    def _learn(self, msg: str) -> Reply:
        sid = source_id(msg)
        if sid in self.user_texts():
            return Reply(msg, "known", "I already know that.", source={"kind": "user", "source": sid})
        self.memory.learn_text(msg, sid)
        self.refresh()
        self.context["last_learned"] = sid
        fs = [f for f in self.facts.facts if f.source == sid]
        if fs and fs[0].subject == USER:
            rel = " ".join(fs[0].relation) or "fact"
            text = f"Got it — I'll remember that ({rel}: {fs[0].object})."
        elif fs:
            text = f"Got it — I'll remember that about {fs[0].subject}."
        else:
            text = "Got it — I'll remember that."
        return Reply(msg, "learned", text, source={"kind": "user", "source": sid}, via="memory")

    def _forget(self, msg: str) -> Reply:
        topic = _FORGET.match(msg).group(1).strip().rstrip(".!").strip()
        topic = re.sub(r"^(?:what i (?:told|said to) you about|everything (?:i told you )?about|about|the fact that|"
                       r"that)\s+", "", topic, flags=re.I).strip()
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
        """The taught text that best matches the topic of a forget request."""
        self.refresh()
        mentions, rel = question_parts(topic, self.is_name_initial)
        first_person = USER in mentions or not rel
        rq = self.facts.rel.encode(rel) if rel else None
        tw = set(w for w in _rel_words(topic))
        scored = []
        for sid, text in texts.items():
            fs = [f for f in self.facts.facts if f.source == sid]
            best = 0.0
            for f in fs:
                s = 0.0
                if rq is not None:
                    s = 1.0 - int(np.bitwise_count(rq ^ self.facts.rel.encode(f.relation)).sum()) / 2048
                    s += 0.5 * len(tw & set(f.relation))
                if (f.subject == USER) == first_person:
                    s += 0.05
                ent_words = set(norm_entity(f.subject).split()) | set(norm_entity(f.object).split())
                s += 0.5 * len(ent_words & set(norm_entity(topic).split()))
                best = max(best, s)
            ow = set(_rel_words(text))
            best = max(best, 0.5 * len(tw & ow))
            scored.append((best, sid))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored[0][1] if scored and scored[0][0] > 0.55 else None

    # -- questions --------------------------------------------------------------------------

    def resolve(self, q: str) -> str:
        """Replace one pronoun / demonstrative by the last answer or topic."""
        ctx = self.context
        if not ctx["answer"] and not ctx["mention"]:
            return q
        person = ctx["answer"] if ctx["atype"] == PERSON and ctx["answer"] else ctx["mention"]
        thing = ctx["answer"] if ctx["atype"] in (LOCATION, PROPER, OTHER) and ctx["answer"] else ctx["mention"]
        m = _DEMONSTRATIVE.search(q)
        if m:
            target = person if m.group(2).lower() in _PERSONISH else thing
            if target:
                return q[:m.start()] + target + q[m.end():]
        ws = q.split(" ")
        for i, w in enumerate(ws):
            core = re.sub(r"[^\w']", "", w).lower()
            tail = w[len(w.rstrip("?.!,")):]
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
        q = self.resolve(msg)
        qa = analyse(q)
        mentions, rel = question_parts(q, self.is_name_initial)
        about_user = USER in mentions
        # 1. the fact memory
        rec = self.facts.recall(mentions, rel, atype=qa.atype)
        if rec and rec.entity_sim >= self.cfg.entity_min and rec.confidence >= self.cfg.fact_min:
            return self._finish(msg, q, qa, "answer", rec.answer, rec.answer, rec.fact.sentence,
                                {"kind": "user", "source": rec.fact.source}, rec.confidence, "facts",
                                mention=rec.entity if rec.entity != USER else None)
        if about_user:
            return self._finish(msg, q, qa, "unknown", None, None, None, None, 0.0, "facts",
                                text="I don't know — you haven't told me that (or you asked me to forget it).")
        # 2. look it up and cut out a short answer
        return self._lookup(msg, q, qa, mentions)

    def _user_candidates(self, query) -> list[tuple[float, str, str, dict]]:
        """Taught sentences scored with the same features (no document features)."""
        out = []
        if not self._user_sents or len(query.terms) == 0:
            return out
        qset = {int(t): float(w) for t, w in zip(query.terms, query.idf)}
        isum = query.idf_sum or 1.0
        wv = self.cfg.weights.vector()
        for sid, text, toks in self._user_sents:
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
            out.append((score, sid, text, {"kind": "user", "source": sid}))
        return out

    def _lookup(self, msg: str, q: str, qa, mentions: list[str]) -> Reply:
        cands = self.r.candidates(q, self.cfg.weights, self.cfg.text_k)
        query = cands.query
        rows = []
        if len(cands.ids):
            sc = cands.scores(self.cfg.weights)
            for k in range(len(cands.ids)):
                rows.append((float(sc[k]), 1, int(cands.ids[k]), cands.texts[k], None))
        for score, sid, text, src in self._user_candidates(query):
            rows.append((score, 0, -1, text, src))
        if not rows:
            return self._finish(msg, q, qa, "unknown", None, None, None, None, 0.0, "lookup",
                                text="I don't know — I found nothing about that.")
        rows.sort(key=lambda r: (-r[0], r[1], r[2], r[3]))
        top = rows[:self.cfg.extract.k]
        isum = max(query.idf_sum, 1e-9)
        texts = [r[3] for r in top]
        rel = np.array([r[0] / isum for r in top])
        x = extract(qa, texts, rel, self.cfg.extract, self.is_name_initial)
        if x.text is None:
            best = top[0]
            src = best[4] or self.c.source(best[2])
            return self._finish(msg, q, qa, "unknown", None, None, best[3], src, 0.0, "lookup",
                                text="I don't know. The closest I found is below.")
        row = top[x.sentence]
        src = row[4] or self.c.source(row[2])
        ok = x.confidence >= self.cfg.theta
        if ok and self.cfg.focus_gate and not self._focus_ok(q, row):
            ok = False
        alts = [{"text": r[3], "source": r[4] or self.c.source(r[2])} for r in top[:4] if r is not row][:3]
        return self._finish(msg, q, qa, "answer" if ok else "unknown", x.text if ok else None, x.text, row[3], src,
                            x.confidence, "lookup", alternatives=alts)

    def _focus_ok(self, q: str, row) -> bool:
        """Every capitalised name in the question must occur in the evidence's document
        (or taught text) — otherwise the answer is about something else."""
        names = [sp.text for sp in spans(q, self.is_name_initial) if sp.kind == "NAME"]
        if not names:
            return True
        if row[2] < 0:
            hay = row[3].lower()
            return all(n.lower() in hay for n in names)
        d = int(self.c.sent_doc[row[2]])
        lo = int(self.c.doc_starts[d])
        hi = int(self.c.doc_starts[d + 1]) if d + 1 < self.c.n_docs else len(self.c.tokens)
        doc = np.asarray(self.c.tokens[lo:hi])
        key = " ".join(self.c.doc_keys[d][1].lower().split())
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
                return False
        return True

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
        self.context.update({"answer": answer, "atype": qa.atype if answer else None, "mention": m})
        return Reply(msg, kind, text, answer, guess, evidence, source, float(conf), via,
                     q if q != msg else None, alternatives or [])
