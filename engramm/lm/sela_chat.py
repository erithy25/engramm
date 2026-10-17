"""Sela-2 in the desktop app: chat turns, grounded answers from ENGRAMM's sources, and a check of what it says.

``SelaChat`` holds the NumPy model (engramm/lm/sela.py, format sela-npz-2) and its tokenizer, renders the
conversation in the chat format of training (engramm/lm/chat_format.py) and samples a reply:
- the repetition penalty counts only the reply's own tokens (never the prompt: names and numbers in the sources
  must be copyable, and the role tokens of the prompt must not suppress stopping);
- generation stops at <|im_end|>, <|im_start|> or <|eos|>, at ``max_tokens``, or when a 4-token sequence has
  appeared three times (a loop);
- the history is cut at turn boundaries from the oldest turn, never inside the system prompt or the sources.

``verify`` checks a grounded answer before it is shown: every citation [n] must name a given source, and every
number and (English) name in the answer must occur in a cited source or in the question. It cannot see whether the
facts are correctly related — a failed check falls back to ENGRAMM's own answer; a passed one is shown with its
sources.
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engramm.lm.chat_format import (EOS, IM_END, IM_START, NO_ANSWER, SYSTEM, SYSTEM_BRIEF, SYSTEM_GROUNDED, Message,
                                    citations, clean_reply, render, sources_block)

STOP = (EOS, IM_END, IM_START)
SPECIAL_MAX = 16                                   # ids below this are special tokens (never penalised)
DE_WORDS = frozenset("ich du wie warum wer wo der das und ist nicht bitte danke hallo kannst bist mir mich ein eine "
                     "für über erkläre schreib sind wir ihr auch noch aber oder dass mit von zu den dem des im "
                     "es sie hat haben wird werden kann gibt".split())
EN_WORDS = frozenset("the is was are and of to in it you what how by for a an this that with on at be have can "
                     "who where why which do does did my your me".split())


def language_of(text: str) -> str:
    """'de' when the text reads German (umlauts, or more German than English function words), else 'en'."""
    low = text.lower()
    if re.search(r"[äöüß]", low):
        return "de"
    words = re.findall(r"[a-z]+", low)
    de = sum(w in DE_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    return "de" if de > en else "en"


@dataclass
class Turn:
    user: str
    assistant: str


@dataclass
class ChatState:
    turns: list[Turn] = field(default_factory=list)


def sample(logits: np.ndarray, generated: list[int], rng: np.random.Generator, temperature: float, top_p: float,
           rep_penalty: float, top_k: int = 200) -> int:
    z = logits.astype(np.float64)
    if rep_penalty != 1.0 and generated:
        seen = np.fromiter({t for t in generated if t >= SPECIAL_MAX}, dtype=np.int64)
        if len(seen):
            sel = z[seen]
            z[seen] = np.where(sel > 0, sel / rep_penalty, sel * rep_penalty)
    if temperature <= 0:
        return int(np.argmax(z))
    k = min(top_k, len(z))
    idx = np.argpartition(-z, k - 1)[:k]                 # the k best, unordered
    zz = z[idx] / temperature
    zz -= zz.max()
    p = np.exp(zz)
    p /= p.sum()
    order = np.argsort(-p, kind="stable")
    sp = p[order]
    keep = np.cumsum(sp) - sp < top_p
    sp = sp * keep
    sp /= sp.sum()
    return int(idx[order[rng.choice(len(sp), p=sp)]])


def looping(ids: list[int], n: int = 4, times: int = 3) -> bool:
    """True when the last n tokens already occurred ``times`` times in ``ids`` (the newest included)."""
    if len(ids) < n * times:
        return False
    tail = tuple(ids[-n:])
    c = 0
    for i in range(len(ids) - n + 1):
        if tuple(ids[i:i + n]) == tail:
            c += 1
            if c >= times:
                return True
    return False


class SelaChat:
    def __init__(self, weights: str | Path, tokenizer=None):
        from engramm.lm.sela import Sela2Model, tokenizer_for
        self.model = Sela2Model.load(weights)
        self.tok = tokenizer or tokenizer_for(self.model)
        if self.tok.vocab_size != self.model.cfg.vocab:
            raise ValueError(f"tokenizer has {self.tok.vocab_size} tokens, the model {self.model.cfg.vocab}")
        self.ctx_budget = min(self.model.cfg.ctx, 1536)       # prompt + reply stay well inside the context

    # -- prompts ------------------------------------------------------------------------------------------------
    def build(self, state: ChatState | None, user: str, sources: list[tuple[str, str]] | None = None,
              lang: str | None = None, brief: bool = True, reply_room: int = 200) -> list[int]:
        lang = lang or language_of(user)
        head = []
        if sources:
            head = [Message("system", SYSTEM_GROUNDED[lang]), Message("sources", sources_block(sources))]
        else:
            head = [Message("system", (SYSTEM_BRIEF if brief else SYSTEM)[lang])]
        turns = list(state.turns) if (state and not sources) else []   # grounded answers see no old turns
        while True:
            msgs = list(head)
            for t in turns:
                msgs += [Message("user", t.user), Message("assistant", t.assistant)]
            msgs.append(Message("user", user))
            ids, _ = render(self.tok, msgs, add_generation_prompt=True)
            if len(ids) + reply_room <= self.ctx_budget or not turns:
                break
            turns = turns[1:]                                  # drop the oldest turn, never the head
        if len(ids) + reply_room > self.model.cfg.ctx:
            ids = ids[:1] + ids[-(self.model.cfg.ctx - reply_room - 1):]   # one very long message: keep its end
        return ids

    # -- generation ---------------------------------------------------------------------------------------------
    def generate(self, ids: list[int], max_tokens: int = 160, temperature: float = 0.7, top_p: float = 0.9,
                 rep_penalty: float = 1.1, seed: int | None = None) -> tuple[str, int, bool]:
        """(reply text, tokens, stopped by itself)."""
        m = self.model
        rng = np.random.default_rng(seed)
        cache = m.new_cache()
        logits = m.forward(ids, cache, last_only=True)[-1]
        out: list[int] = []
        finished = False
        for _ in range(max_tokens):
            nxt = sample(logits, out, rng, temperature, top_p, rep_penalty)
            if nxt in STOP:
                finished = True
                break
            out.append(nxt)
            if looping(out):
                break
            if cache.n >= m.cfg.ctx:
                break
            logits = m.forward([nxt], cache, last_only=True)[-1]
        return clean_reply(self._decode(out)), len(out), finished

    def _decode(self, ids: list[int]) -> str:
        text = self.tok.decode(ids)
        k = len(ids)
        while text.endswith("�") and k > max(0, len(ids) - 3):
            k -= 1
            text = self.tok.decode(ids[:k])
        return text.rstrip("�")

    def chat(self, state: ChatState, user: str, max_tokens: int = 160, seed: int | None = None) -> dict:
        t0 = time.time()
        ids = self.build(state, user, reply_room=max_tokens)
        text, n, done = self.generate(ids, max_tokens=max_tokens, temperature=0.7, seed=seed)
        if not done:
            text = cut_sentence(text)
        text = text or "…"
        state.turns.append(Turn(user, text))
        del state.turns[:-8]
        return {"text": text, "tokens": n, "finished": done, "seconds": round(time.time() - t0, 3),
                "prompt_tokens": len(ids)}

    def grounded(self, user: str, sources: list[tuple[str, str]], max_tokens: int = 90, seed: int | None = None) -> dict:
        t0 = time.time()
        lang = language_of(user)
        ids = self.build(None, user, sources=sources, lang=lang, reply_room=max_tokens)
        text, n, done = self.generate(ids, max_tokens=max_tokens, temperature=0.2, rep_penalty=1.0, seed=seed)
        if not done:
            text = cut_sentence(text)
        ok, issues = verify(text, sources, user)
        abstained = is_abstention(text)
        return {"text": text, "tokens": n, "finished": done, "verified": ok and not abstained, "abstained": abstained,
                "issues": issues, "cited": sorted(set(citations(text))), "seconds": round(time.time() - t0, 3),
                "prompt_tokens": len(ids)}


def cut_sentence(text: str) -> str:
    """A reply cut by the token limit ends at its last complete sentence (when there is a long enough one)."""
    body = text.strip()
    if body.endswith((".", "!", "?", "]")):
        return body
    cut = max(body.rfind(". "), body.rfind("! "), body.rfind("? "), body.rfind(".\n"), body.rfind("]."))
    return body[:cut + 1].strip() if cut >= len(body) // 3 else body + " …"


def is_abstention(text: str) -> bool:
    t = text.strip().lower()
    return any(t.startswith(a.lower().rstrip(".")) for a in NO_ANSWER.values())


NUM = re.compile(r"\d[\d,.  ]*")


def _norm_num(s: str) -> str:
    return re.sub(r"[,.  ]", "", s).lstrip("0") or "0"


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def verify(answer: str, sources: list[tuple[str, str]], question: str = "") -> tuple[bool, list[str]]:
    """Every citation names a source; every number and English name in the answer occurs in a cited source or in
    the question. Returns (passed, issues)."""
    issues = []
    if is_abstention(answer):
        return True, []
    cited = sorted(set(citations(answer)))
    if not cited:
        issues.append("no citation")
    bad = [c for c in cited if not 1 <= c <= len(sources)]
    if bad:
        issues.append(f"cites missing sources {bad}")
    ok_cited = [c for c in cited if 1 <= c <= len(sources)]
    pool = " ".join(f"{sources[c - 1][0]} {sources[c - 1][1]}" for c in ok_cited) + " " + question
    nums = {_norm_num(x) for x in NUM.findall(pool)}
    body = re.sub(r"\[\d{1,2}\]", " ", answer)
    for x in NUM.findall(body):
        if _norm_num(x) not in nums:
            issues.append(f"number {x.strip()} not in the cited sources")
    if language_of(answer) == "en":                    # German capitalises every noun: names are not checked there
        folded = set(re.findall(r"\w+", _fold(pool)))
        for sent in re.split(r"(?<=[.!?])\s+", body.strip()):
            for w in re.findall(r"[^\W\d_][\w'-]*", sent)[1:]:   # a sentence's first word is capitalised anyway
                if w[0].isupper() and len(w) >= 3 and _fold(w).strip("'-") not in folded:
                    issues.append(f"name {w} not in the cited sources")
    return not issues, issues


def sources_from_reply(d: dict, limit: int = 4) -> list[tuple[str, str]]:
    """ENGRAMM's evidence and alternatives (Reply.to_dict) as (title, text) sources, best first, one per text."""
    out, seen = [], set()

    def title_of(src) -> str:
        if not src:
            return ""
        if src.get("kind") == "user":
            return "You told me"
        return str(src.get("key") or src.get("title") or "")
    if d.get("evidence"):
        out.append((title_of(d.get("source")), d["evidence"]))
        seen.add(d["evidence"])
    for a in d.get("alternatives") or []:
        t = a.get("text")
        if t and t not in seen:
            out.append((title_of(a.get("source")), t))
            seen.add(t)
        if len(out) >= limit:
            break
    return out
