"""Assistant-command intents (MASSIVE en-US, 60 intents): an averaged perceptron over word
unigrams and bigrams, letter trigrams and the utterance length — counted, no neural network.

ENGRAMM uses it to recognise requests it cannot carry out (alarms, music, smart home, e-mail)
and question types it can (maths, currency, definitions, dates), also when no hand-written
pattern matches the wording.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from engramm.nlp.perceptron import AveragedPerceptron, order


def features(utterance: str) -> list[str]:
    s = re.sub(r"\s+", " ", utterance.lower().replace("’", "'")).strip()
    ws = re.findall(r"[a-z0-9']+", s)
    f = ["b", f"len={min(len(ws), 12)}"]
    f += ["w:" + w for w in ws]
    f += [f"bi:{a}_{b}" for a, b in zip(ws, ws[1:])]
    f += ["first:" + ws[0]] if ws else []
    f += ["first2:" + "_".join(ws[:2])] if len(ws) > 1 else []
    padded = f" {s} "
    f += ["c:" + padded[i:i + 3] for i in range(len(padded) - 2)]
    return f


class IntentClassifier:
    def __init__(self):
        self.model = AveragedPerceptron()

    def train(self, examples: list[tuple[str, str]], epochs: int = 12, key: str = "intent", log=None) -> None:
        self.model.classes = sorted({y for _, y in examples})
        feats = [features(x) for x, _ in examples]
        ids = list(range(len(examples)))
        for ep in range(epochs):
            right = 0
            for i in order(ids, f"{key}|{ep}"):
                guess = self.model.predict(feats[i])
                right += guess == examples[i][1]
                self.model.update(examples[i][1], guess, feats[i])
            if log:
                log(f"intent epoch {ep + 1}: train accuracy {right / len(examples):.4f}")
        self.model.average()

    def predict(self, utterance: str) -> tuple[str, float]:
        """(intent, margin between the best and the second score)."""
        s = self.model.scores(features(utterance))
        ranked = sorted(self.model.classes, key=lambda c: (-s.get(c, 0.0), c))
        best = ranked[0]
        margin = s.get(best, 0.0) - (s.get(ranked[1], 0.0) if len(ranked) > 1 else 0.0)
        return best, margin

    def save(self, path: Path) -> None:
        self.model.save(path, {"kind": "intent"})

    @classmethod
    def load(cls, path: Path) -> IntentClassifier:
        c = cls()
        c.model = AveragedPerceptron.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
        return c


def macro_f1(gold: list[str], pred: list[str]) -> float:
    labels = sorted(set(gold))
    f1s = []
    for lab in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == lab and p == lab)
        fp = sum(1 for g, p in zip(gold, pred) if g != lab and p == lab)
        fn = sum(1 for g, p in zip(gold, pred) if g == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / len(f1s) if f1s else 0.0
