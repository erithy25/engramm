"""Confidence of a short answer, learnt by counting corrections (averaged perceptron).

The span choice says *which* words answer a question; this model says *how sure* ENGRAMM may be.
It reads the evidence the answer rests on:

* how the votes fell: the answer's share of all votes, how many of the best sentences hold it as a
  candidate, the best sentence's retrieval score;
* the answer itself: expected type, number of words, whether it is a number, a name or lower case;
* the sentence the answer comes from: how much of the question it covers (words, phrases, the
  document, the previous sentence, the title) and its rank among the best sentences.

Every feature is a discrete string. Training walks over questions whose answers are known (spent
development data only) and, whenever the sign of the score disagrees with "exactly right", adds or
subtracts one on the features involved. The average over all steps is kept. Nothing else is learnt;
the score is a sum of counted weights and is compared with θ.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from engramm.chat.retrieve import FEATURES

_FI = {n: i for i, n in enumerate(FEATURES)}
# quantiles of the best sentence's score (score / Σidf) over the spent SQuAD questions (fixed with the model)
DEFAULT_R0_BINS = (6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.5)


def _bin(x: float, k: int = 5) -> int:
    return min(int(max(float(x), 0.0) * k), k - 1)


def features(info: dict | None, text: str | None, atype: str, wh: str, n_content: int,
             sent: np.ndarray | None, rank: int, r0_bins=DEFAULT_R0_BINS) -> list[str]:
    """Feature strings of one answer. ``sent`` = retrieval features of the answer's sentence (or None
    for a taught sentence), ``rank`` = its position among the best sentences."""
    if not info or not text:
        return ["none"]
    if info.get("choice"):
        return ["choice", "bias"]
    share = float(info["share"])
    sh, sh5 = min(int(share * 10), 9), min(int(share * 5), 4)
    r0 = int(np.searchsorted(np.asarray(r0_bins), float(info["r0"])))
    ns, ln = min(int(info["nsent"]), 5), min(int(info["len"]), 6)
    kind = "num" if any(ch.isdigit() for ch in text) else ("cap" if text[:1].isupper() else "low")
    f = [f"sh{sh}", f"r0{r0}", f"ns{ns}", f"at{atype}", f"at{atype}sh{sh5}", f"ln{ln}", f"at{atype}ln{min(ln, 3)}",
         f"wh{wh or 'none'}", f"sh{sh5}ns{min(ns, 3)}", f"k{kind}", f"at{atype}k{kind}", f"r0{r0}sh{sh5}",
         f"ql{min(n_content, 8)}", "bias"]
    if sent is not None and len(sent) == len(FEATURES):
        si = min(rank, 3)
        cov = _bin(sent[_FI["cov"]])
        f += [f"cov{cov}", f"phr{_bin(sent[_FI['phr']])}", f"dfull{_bin(sent[_FI['dfull']])}",
              f"pcov{_bin(sent[_FI['pcov']])}", f"kcov{_bin(sent[_FI['kcov']])}", f"si{si}", f"cov{cov}sh{sh5}",
              f"cov{cov}si{si}", f"prox{_bin(sent[_FI['prox']])}", f"cov{cov}at{atype}"]
    else:
        f.append("taught")
    return f


class ConfCalibrator:
    def __init__(self, w: dict[str, float], r0_bins=DEFAULT_R0_BINS):
        self.w = dict(w)
        self.r0_bins = tuple(float(x) for x in r0_bins)

    def score(self, feats: list[str]) -> float:
        return float(sum(self.w.get(f, 0.0) for f in feats))

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps({"kind": "conf-perceptron", "r0_bins": list(self.r0_bins),
                                          "w": {k: self.w[k] for k in sorted(self.w)}}, indent=0) + "\n")

    @classmethod
    def load(cls, path: Path) -> ConfCalibrator:
        d = json.loads(Path(path).read_text())
        return cls(d["w"], d.get("r0_bins", DEFAULT_R0_BINS))


def train(examples: list[tuple[list[str], bool]], passes: int = 10, seed: int = 0) -> dict[str, float]:
    """Averaged perceptron: label +1 for an exactly right answer, −1 otherwise. The visiting order of
    pass p is a fixed permutation (numpy PCG64, seed + p), so training is reproducible."""
    w: dict[str, float] = {}
    u: dict[str, float] = {}
    c = 1
    for p in range(passes):
        for i in np.random.default_rng(seed + p).permutation(len(examples)):
            feats, right = examples[int(i)]
            y = 1.0 if right else -1.0
            if y * sum(w.get(f, 0.0) for f in feats) <= 0:
                for f in feats:
                    w[f] = w.get(f, 0.0) + y
                    u[f] = u.get(f, 0.0) + c * y
            c += 1
    return {f: w[f] - u.get(f, 0.0) / c for f in w if w[f] - u.get(f, 0.0) / c != 0.0}
