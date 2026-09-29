"""Part-of-speech tagging: a greedy averaged perceptron (after Collins 2002 / Honnibal 2013).

Features: the word, its lower case, prefix and suffixes, its shape, the neighbouring words and
suffixes, and the two tags already assigned to the left. Words that are frequent and always
carry the same tag in the training data are tagged by a dictionary first.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from engramm.nlp.perceptron import AveragedPerceptron, order

START, END = ["-START-", "-START2-"], ["-END-", "-END2-"]


def normalise(word: str) -> str:
    if "-" in word and word[0] != "-":
        return "!HYPHEN"
    if word.isdigit() and len(word) == 4:
        return "!YEAR"
    if word[:1].isdigit():
        return "!DIGITS"
    return word.lower()


def shape(word: str) -> str:
    s = re.sub(r"[A-Z]", "X", word)
    s = re.sub(r"[a-z]", "x", s)
    s = re.sub(r"[0-9]", "d", s)
    return re.sub(r"(.)\1{2,}", r"\1\1", s)


class PerceptronTagger:
    def __init__(self):
        self.model = AveragedPerceptron()
        self.tagdict: dict[str, str] = {}

    def _features(self, i: int, word: str, context: list[str], prev: str, prev2: str) -> list[str]:
        i += len(START)
        w = context[i]
        f = ["b", "s:" + word[-3:].lower(), "s2:" + word[-2:].lower(), "p:" + word[:1], "sh:" + shape(word),
             "t1:" + prev, "t2:" + prev2, "t12:" + prev + "|" + prev2, "w:" + w, "t1w:" + prev + "|" + w,
             "w-1:" + context[i - 1], "s-1:" + context[i - 1][-3:], "w-2:" + context[i - 2],
             "w+1:" + context[i + 1], "s+1:" + context[i + 1][-3:], "w+2:" + context[i + 2]]
        lw = word.lower()
        f += ["s4:" + lw[-4:], "s1:" + lw[-1:], "p2:" + lw[:2], "p3:" + lw[:3], "t1s:" + prev + "|" + lw[-3:],
              "w-1w:" + context[i - 1] + "|" + w, "ww+1:" + w + "|" + context[i + 1],
              "t1w+1:" + prev + "|" + context[i + 1], "hasdig" if any(c.isdigit() for c in word) else "nodig",
              "hyph" if "-" in word else "nohyph", "len:" + str(min(len(word), 8))]
        if word[:1].isupper():
            f.append("cap")
            if i == len(START):
                f.append("cap0")
        return f

    def tag(self, words: list[str]) -> list[str]:
        prev, prev2 = START
        context = START + [normalise(w) for w in words] + END
        out = []
        for i, word in enumerate(words):
            t = self.tagdict.get(word)
            if t is None:
                t = self.model.predict(self._features(i, word, context, prev, prev2))
            out.append(t)
            prev2, prev = prev, t
        return out

    def train(self, sentences: list[tuple[list[str], list[str]]], epochs: int = 8, key: str = "pos",
              log=None) -> None:
        self._make_tagdict(sentences)
        self.model.classes = sorted({t for _, tags in sentences for t in tags})
        ids = list(range(len(sentences)))
        for ep in range(epochs):
            right = total = 0
            for idx in order(ids, f"{key}|{ep}"):
                words, tags = sentences[idx]
                prev, prev2 = START
                context = START + [normalise(w) for w in words] + END
                for i, word in enumerate(words):
                    guess = self.tagdict.get(word)
                    if guess is None:
                        feats = self._features(i, word, context, prev, prev2)
                        guess = self.model.predict(feats)
                        self.model.update(tags[i], guess, feats)
                    prev2, prev = prev, guess
                    right += guess == tags[i]
                    total += 1
            if log:
                log(f"pos epoch {ep + 1}: train accuracy {right / max(total, 1):.4f}")
        self.model.average()

    def _make_tagdict(self, sentences) -> None:
        counts: dict[str, Counter] = defaultdict(Counter)
        for words, tags in sentences:
            for w, t in zip(words, tags):
                counts[w][t] += 1
        self.tagdict = {}
        for w, c in counts.items():
            tag, n = c.most_common(1)[0]
            total = sum(c.values())
            if total >= 20 and n / total >= 0.97:
                self.tagdict[w] = tag

    def save(self, path: Path) -> None:
        self.model.save(path, {"tagdict": self.tagdict, "kind": "pos"})

    @classmethod
    def load(cls, path: Path) -> PerceptronTagger:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        t = cls()
        t.model = AveragedPerceptron.from_dict(d)
        t.tagdict = d["tagdict"]
        return t
