"""A learned situation classifier on top of the rules: an averaged perceptron over the rule's own decision, the
lexicon evidence, the object classes, the general regex families and the words of the message.

Trained once on a labelled set (experiments/frame_train.py, data in experiments/probes/frames_train.jsonl) and kept
small (engramm/understand/data/frame_model.json.gz). It keeps learning on the user's computer: a correction ("no, I
lost it, nobody stole it") is an update of the same perceptron (engramm/learn/), stored in the user's learning state
and removable with "forget that".
"""
from __future__ import annotations

import gzip
import json
from engramm.understand import _re as re
from pathlib import Path

from engramm.nlp.perceptron import AveragedPerceptron
from engramm.understand.lex import lexicon

MODEL = Path(__file__).resolve().parent / "data" / "frame_model.json.gz"
KINDS = ["DAMAGE", "INJURY", "ILLNESS", "LOSS", "THEFT", "CONFLICT", "FAILURE", "MONEY", "DELAY", "WORRY", "SUCCESS",
         "MILESTONE", "ACQUIRE", "DEATH", "FEEL_NEG", "FEEL_POS", "PLAN", "ACTIVITY", "NONE"]


def features(f, text: str, rule_kind: str) -> list[str]:
    from engramm.understand.frames import _R, _DAMAGEABLE
    s = text.lower()
    lang = f.lang
    feats = ["bias", f"rule={rule_kind or 'NONE'}"]
    feats += [f"ev={e}" for e in sorted(f.evidence)]
    feats += [f"rx={k}" for k, rx in _R.items() if rx.search(s)]
    feats += [f"cat={c}" for c in sorted(f.obj_cats)]
    if f.obj_cats & _DAMAGEABLE:
        feats.append("thing")
    if f.body:
        feats.append("body")
    if f.cause:
        feats.append("cause")
    feats.append(f"who={f.who or '-'}")
    feats.append(f"ask={f.ask or ('q' if f.question else 'stmt')}")
    if f.future:
        feats.append("future")
    if f.negated:
        feats.append("neg")
    # conjunctions the linear model cannot form itself: what kind of evidence meets what kind of thing or person
    ctx = (["body"] if f.body else []) + (["thing"] if f.obj_cats & _DAMAGEABLE else []) + \
        ([f"who={f.who}"] if f.who not in ("", "me") else []) + (["cause"] if f.cause else []) + \
        (["future"] if f.future else []) + (["neg"] if f.negated else [])
    for e in sorted(f.evidence):
        for c in ctx:
            feats.append(f"ev={e}&{c}")
    for k, rx in _R.items():
        if rx.search(s):
            for c in ctx:
                feats.append(f"rx={k}&{c}")
    lx = lexicon(lang)
    words = list(f.words)
    for i, w in enumerate(words):
        feats.append(f"w:{lang}:{w}")
        rs = lx.lookup(w) if len(w) > 2 else []
        if rs:
            feats.append(f"l:{lang}:{rs[0].lemma}")
            for c in sorted(rs[0].cats)[:4]:
                feats.append(f"wc={c}")
        if i + 1 < len(words):
            feats.append(f"b:{lang}:{w}_{words[i + 1]}")
    return feats


class FrameClassifier:
    margin = 3.0
    override = 5.0

    def __init__(self, model: AveragedPerceptron | None = None):
        self.p = model

    @classmethod
    def load(cls, path: Path = MODEL) -> "FrameClassifier":
        if not path.exists():
            return cls(None)
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return cls(AveragedPerceptron.from_dict(json.load(fh)))

    def __bool__(self) -> bool:
        return self.p is not None

    def predict(self, f, text: str, rule_kind: str, extra: dict | None = None) -> str:
        if extra and extra.get("__ex__"):
            from engramm.learn.state import exemplar
            k = exemplar(extra, text)
            if k is not None:
                return "" if k == "NONE" else k   # the user corrected (nearly) this very message
        feats = features(f, text, rule_kind)
        scores = self.p.scores(feats)
        for k, d in (extra or {}).items():                 # the user's own corrections (engramm/learn)
            if k == "__ex__":
                continue
            for c, v in d.items():
                if k in feats:
                    scores[c] = scores.get(c, 0.0) + v
        best = max(KINDS, key=lambda c: (scores.get(c, 0.0), -KINDS.index(c)))
        if best == "NONE":
            return ""
        if not rule_kind and scores.get(best, 0.0) - scores.get("NONE", 0.0) < self.margin:
            return ""                   # the rules saw no situation and the model is not sure: none
        if rule_kind and best != rule_kind and scores.get(best, 0.0) - scores.get(rule_kind, 0.0) < self.override:
            return rule_kind            # the rules saw a situation: the model needs a clear lead to overrule them
        return best


_CLF: FrameClassifier | None = None


def classifier() -> FrameClassifier:
    global _CLF
    if _CLF is None:
        _CLF = FrameClassifier.load()
    return _CLF


def save(p: AveragedPerceptron, path: Path = MODEL) -> None:
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(p.to_dict(), fh, separators=(",", ":"))


def tidy(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
