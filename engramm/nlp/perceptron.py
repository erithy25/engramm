"""The averaged perceptron shared by the tagger, the parser and the intent classifier.

Weights are counted corrections: for a wrong prediction every active feature gets +1 for the
right class and −1 for the predicted one. The final weights are averaged over all updates
(lazy averaging with timestamps), which makes the perceptron stable and good at test time.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


class AveragedPerceptron:
    def __init__(self, classes: list[str] | None = None):
        self.weights: dict[str, dict[str, float]] = {}
        self.classes: list[str] = list(classes or [])
        self._totals: dict[tuple[str, str], float] = defaultdict(float)
        self._stamps: dict[tuple[str, str], int] = defaultdict(int)
        self.i = 0

    def scores(self, features) -> dict[str, float]:
        s: dict[str, float] = defaultdict(float)
        for f in features:
            w = self.weights.get(f)
            if w is None:
                continue
            for c, v in w.items():
                s[c] += v
        return s

    def predict(self, features, allowed=None) -> str:
        s = self.scores(features)
        cands = allowed if allowed is not None else self.classes
        # ties broken by class order (deterministic)
        return max(cands, key=lambda c: (s.get(c, 0.0), -self.classes.index(c) if c in self.classes else 0))

    def update(self, truth: str, guess: str, features) -> None:
        self.i += 1
        if truth == guess:
            return
        for f in features:
            w = self.weights.setdefault(f, {})
            for c, delta in ((truth, 1.0), (guess, -1.0)):
                key = (f, c)
                v = w.get(c, 0.0)
                self._totals[key] += (self.i - self._stamps[key]) * v
                self._stamps[key] = self.i
                w[c] = v + delta

    def average(self) -> None:
        for f, w in self.weights.items():
            for c, v in list(w.items()):
                key = (f, c)
                total = self._totals[key] + (self.i - self._stamps[key]) * v
                avg = round(total / max(self.i, 1), 4)
                if avg:
                    w[c] = avg
                else:
                    del w[c]
        self.weights = {f: w for f, w in self.weights.items() if w}
        self._totals.clear()
        self._stamps.clear()

    def to_dict(self) -> dict:
        return {"classes": self.classes, "weights": self.weights}

    @classmethod
    def from_dict(cls, d: dict) -> AveragedPerceptron:
        p = cls(d["classes"])
        p.weights = d["weights"]
        return p

    def save(self, path: Path, extra: dict | None = None) -> None:
        data = self.to_dict()
        if extra:
            data.update(extra)
        Path(path).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")


def order(ids: list, key: str) -> list[int]:
    """A fixed shuffled order of example indices (SHAKE-256 of key and id) — deterministic training."""
    return sorted(range(len(ids)), key=lambda i: hashlib.shake_256(f"{key}|{ids[i]}".encode()).digest(8))
