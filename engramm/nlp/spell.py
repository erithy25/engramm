"""Typos and letter case, by counting (Norvig-style candidates, no neural network).

The vocabulary comes from the reading of a knowledge pack (``experiments/spell_build.py``): every
word with its count and how often it is written with a capital letter inside a sentence.

* ``fix_word``: a word the vocabulary does not know becomes its most frequent neighbour at edit
  distance 1 (for words up to 8 letters also 2), if that neighbour is common enough;
* ``truecase``: a message in CAPITALS is lower-cased, and words that are names in the reading
  ("hamlet" → "Hamlet") get their capital back;
* a few context rules fix real-word confusions ("capitol of" → "capital of").
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_LETTERS = "abcdefghijklmnopqrstuvwxyz"
_TOKEN = re.compile(r"[A-Za-z][A-Za-z']*|[^A-Za-z]+")
_CONFUSIONS = [(re.compile(r"\bcapitol of\b", re.I), "capital of"),
               (re.compile(r"\bwho's (?=book|song|painting)", re.I), "whose "),
               (re.compile(r"\bteh\b", re.I), "the")]


def _edits1(w: str) -> set[str]:
    splits = [(w[:i], w[i:]) for i in range(len(w) + 1)]
    deletes = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
    replaces = [a + c + b[1:] for a, b in splits if b for c in _LETTERS]
    inserts = [a + c + b for a, b in splits for c in _LETTERS]
    return set(deletes + transposes + replaces + inserts)


class Speller:
    def __init__(self, counts: dict[str, int], capital: dict[str, float] | None = None, min_count: int = 20):
        self.counts = counts
        self.capital = capital or {}
        self.min_count = min_count

    @classmethod
    def load(cls, path: Path) -> Speller:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        words, counts, caps = d["words"], d["counts"], d["capital"]
        return cls(dict(zip(words, counts)), {w: c / 100 for w, c in zip(words, caps) if c})

    def known(self, w: str) -> bool:
        return w.lower() in self.counts

    def fix_word(self, w: str) -> str:
        low = w.lower()
        if len(low) < 3 or low in self.counts or not low.isalpha():
            return w
        cands = [c for c in _edits1(low) if self.counts.get(c, 0) >= self.min_count]
        if not cands and len(low) <= 8:
            cands = [c2 for c in _edits1(low) for c2 in _edits1(c) if self.counts.get(c2, 0) >= self.min_count * 10]
        if not cands:
            return w
        best = max(cands, key=lambda c: (self.counts[c], c))
        if w[:1].isupper():
            best = best[:1].upper() + best[1:]
        return best

    def truecase_word(self, low: str, first: bool) -> str:
        if self.capital.get(low, 0.0) >= 0.5 or low == "i":
            return low[:1].upper() + low[1:]
        return low[:1].upper() + low[1:] if first else low

    def fix(self, message: str) -> str:
        """The message with typos fixed and, if it was written in capitals, normal letter case.
        Words with a capital letter inside a sentence (names) are left alone."""
        letters = [c for c in message if c.isalpha()]
        shouting = len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) > 0.8
        text = message.lower() if shouting else message
        out, first = [], True
        for tok in _TOKEN.findall(text):
            if tok[:1].isalpha():
                word = tok
                if shouting:
                    word = self.truecase_word(self.fix_word(tok), first)
                elif not (tok[:1].isupper() and not first):
                    fixed = self.fix_word(tok)
                    word = fixed[:1].upper() + fixed[1:] if tok[:1].isupper() else fixed
                out.append(word)
                first = False
            else:
                out.append(tok)
                if re.search(r"[.!?]", tok):
                    first = True
        s = "".join(out)
        for rx, rep in _CONFUSIONS:
            s = rx.sub(rep, s)
        return s
