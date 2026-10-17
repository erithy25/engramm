"""Sela-2 in the desktop app: chat turns, grounded answers from ENGRAMM's sources, and a check of what it says.

``SelaChat`` holds the NumPy model (engramm/lm/sela.py, format sela-npz-2) and its tokenizer, renders the
conversation in the chat format of training (engramm/lm/chat_format.py) and samples a reply:
- the repetition penalty counts only the reply's own tokens (never the prompt: names and numbers in the sources
  must be copyable, and the role tokens of the prompt must not suppress stopping);
- generation stops at <|im_end|>, <|im_start|> or <|eos|>, at ``max_tokens``, or when the reply's end repeats a
  block of tokens back to back (a loop: a block of p <= 64 tokens at least 3 times in a row, at least 12 tokens);
- the history is cut at turn boundaries from the oldest turn, never inside the system prompt or the sources.

``verify`` checks a grounded answer before it is shown: every citation [n] must name a given source, and every
number (by value: 3,7 is not 37), number word and (English) name in the answer — the first word of a sentence too,
unless it is a common word — must occur in a cited source; the question does not count as evidence. It cannot see
whether the facts are correctly related — a failed check falls back to ENGRAMM's own answer; a passed one is shown
with its sources.
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
    """'de' when the text has more German than English function words; umlauts decide only a tie ('Who was Kurt
    Gödel?' is English, 'Zürich?' alone German)."""
    low = text.lower()
    words = re.findall(r"[a-zäöüß]+", low)
    de = sum(w in DE_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    if de != en:
        return "de" if de > en else "en"
    return "de" if re.search(r"[äöüß]", low) else "en"


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


def looping(ids: list[int], max_period: int = 64, min_tokens: int = 12, times: int = 3) -> bool:
    """True when the end of ``ids`` is one block of p tokens (p <= max_period) repeated back to back at least
    ``times`` times and over at least ``min_tokens`` tokens ('I am happy. I am happy. I am happy.'). A list whose
    lines merely share a start ('- 1 Packung …') or a phrase used three times far apart is not a loop."""
    n = len(ids)
    for p in range(1, min(max_period, n // times) + 1):
        k = max(times, -(-min_tokens // p))
        if k * p > n:
            continue
        block = ids[n - p:]
        if all(ids[n - (j + 1) * p:n - j * p] == block for j in range(1, k)):
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
        self.last_stop = ""

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
        while len(ids) + reply_room > self.model.cfg.ctx and len(user) > 200:
            over = len(ids) + reply_room - self.model.cfg.ctx  # one very long message: keep the head, shorten its
            keep = max(200, int(len(user) * (1 - over / max(1, len(ids)))) - 200)   # text (start and end stay)
            user = user[:keep // 2] + " … " + user[-(keep // 2):]
            msgs[-1] = Message("user", user)
            ids, _ = render(self.tok, msgs, add_generation_prompt=True)
        if len(ids) + reply_room > self.model.cfg.ctx:
            raise ValueError("the sources and system prompt alone do not fit the context")
        return ids

    # -- generation ---------------------------------------------------------------------------------------------
    def generate(self, ids: list[int], max_tokens: int = 160, temperature: float = 0.7, top_p: float = 0.9,
                 rep_penalty: float = 1.1, seed: int | None = None) -> tuple[str, int, bool]:
        """(reply text, tokens, stopped by itself). ``self.last_stop`` says why it ended: "stop" (a stop token),
        "limit" (max_tokens), "loop" (a 4-token sequence the third time) or "context" (the context is full)."""
        m = self.model
        rng = np.random.default_rng(seed)
        cache = m.new_cache()
        logits = m.forward(ids, cache, last_only=True)[-1]
        out: list[int] = []
        self.last_stop = "limit"
        for _ in range(max_tokens):
            nxt = sample(logits, out, rng, temperature, top_p, rep_penalty)
            if nxt in STOP:
                self.last_stop = "stop"
                break
            out.append(nxt)
            if looping(out):
                self.last_stop = "loop"
                break
            if cache.n >= m.cfg.ctx:
                self.last_stop = "context"
                break
            logits = m.forward([nxt], cache, last_only=True)[-1]
        return clean_reply(self._decode(out)), len(out), self.last_stop == "stop"

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
        return {"text": text, "tokens": n, "finished": done, "stop": self.last_stop, "seconds": round(time.time() - t0, 3),
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
        return {"text": text, "tokens": n, "finished": done, "stop": self.last_stop, "verified": ok and not abstained,
                "abstained": abstained,
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


NUM = re.compile(r"\d{1,3}(?:[   ]\d{3})+(?!\d)|\d[\d,.]*\d|\d")
NUM_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
             "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
             "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
             "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "zwölf": 12, "zwanzig": 20, "dreißig": 30,
             "vierzig": 40, "fünfzig": 50}         # scale words (million, Tausend) qualify a checked digit number
FIRST_OK = frozenset("""a an the it its it's he she they them their there these those this that his her our we i you
yes no not in on at by of for from to with without after before during since until about around over under between
according both neither either however also then so because although though while as when where which who whom whose
what why how one some many most all each every only today currently later early first second third finally yet
still now here thus therefore instead besides moreover approximately roughly nearly almost about overall unlike
like""".split())


def _num_values(s: str) -> set[float]:
    """Plausible values of a written number: '8,848.86' → 8848.86; '3,7' → 3.7; '2.962' / '2,962' → 2962 or 2.962;
    '8 848' → 8848."""
    t = re.sub(r"[   ]", "", s).strip(",.")
    out: set[float] = set()

    def num(x: str):
        try:
            out.add(round(float(x), 6))
        except ValueError:
            pass
    if "," in t and "." in t:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        th = "." if dec == "," else ","
        num(t.replace(th, "").replace(dec, "."))
    elif "," in t or "." in t:
        sep = "," if "," in t else "."
        parts = t.split(sep)
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
            num(t.replace(sep, ""))                         # thousands separator
        if len(parts) == 2:
            num(parts[0] + "." + parts[1])                  # decimal separator
    else:
        num(t)
    return out


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _name_known(w: str, folded_words: set[str], folded_text: str) -> bool:
    f = re.sub(r"['’]s$", "", _fold(w)).strip("'-’")
    if not f or f in folded_words:
        return True
    parts = [x for x in re.split(r"[-'’]", f) if x]
    return len(parts) > 1 and all(x in folded_words for x in parts) or (len(f) >= 4 and f in folded_text)


def verify(answer: str, sources: list[tuple[str, str]], question: str = "") -> tuple[bool, list[str]]:
    """Every citation names a source; every number (by value), number word and English name in the answer occurs in
    a cited source. The question is not evidence (a number or name only the question has is not checked by it).
    Returns (passed, issues)."""
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
    pool = " ".join(f"{sources[c - 1][0]} {sources[c - 1][1]}" for c in ok_cited)
    vals: set[float] = set()
    for x in NUM.findall(pool):
        vals |= _num_values(x)
    folded_text = _fold(pool)
    folded_words = set(re.findall(r"\w+", folded_text))
    body = re.sub(r"\[\d{1,2}\]", " ", answer)
    for x in NUM.findall(body):
        if not (_num_values(x) & vals):
            issues.append(f"number {x.strip()} not in the cited sources")
    for w in re.findall(r"[a-zäöüß]+", body.lower()):
        v = NUM_WORDS.get(w)
        if v is not None and v not in vals and w not in folded_words:
            issues.append(f"number word {w} not in the cited sources")
    if language_of(answer) == "en":                    # German capitalises every noun: names are not checked there
        for sent in re.split(r"(?<=[.!?])\s+", body.strip()):
            for i, w in enumerate(re.findall(r"[^\W\d_][\w'’-]*", sent)):
                if not (w[0].isupper() and len(w) >= 3):
                    continue
                if i == 0 and re.sub(r"['’]s$", "", w).lower() in FIRST_OK:
                    continue                           # a capitalised common word at the start of a sentence
                if not _name_known(w, folded_words, folded_text):
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
