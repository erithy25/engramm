"""Stage 4 — a short answer instead of a whole sentence (docs/PREREG_CHAT_V2.md).

From the best K sentences, candidate spans are collected:

* typed questions (who/when/where/how many/…): spans of the expected type
  (names, dates, numbers — ``question.spans``);
* other questions: chunks of consecutive content words (a noun-phrase proxy).

Spans made only of question words are dropped. Each occurrence votes with

    weight = sentence weight × exp(−distance / λ)

where the sentence weight falls with the retrieval score (softmax with temperature
τ over Σidf-normalised scores) and ``distance`` is the word distance to the nearest
question word in that sentence. Votes of the same normalised span are added up
(redundancy across sentences), and a short span that is part of a longer winning
name gives its votes to it. The answer is the span with the most votes; its
confidence is its share of all votes times the best sentence's normalised score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from engramm.chat.question import (CONNECT, OTHER, STOP, Question, Span, spans, type_matches, words)
from engramm.lm.chat import normalize

PUNCT_BREAK = frozenset(",.;:!?()[]{}\"“”‘’'—–-/")


@dataclass(frozen=True)
class ExtractParams:
    k: int = 10                 # sentences considered
    tau: float = 0.15           # softmax temperature on score/Σidf
    lam: float = 4.0            # distance decay (words)
    other_max: int = 4          # longest chunk for untyped questions
    type_only: bool = True      # typed questions: only spans of the expected type


@dataclass
class Extracted:
    text: str | None
    confidence: float
    sentence: int               # candidate position of the sentence the answer was taken from
    votes: list[tuple[str, float]]


def chunks(ws: list[str], lw: list[str], max_len: int) -> list[Span]:
    """Runs of content words (no stop words, no punctuation), at most ``max_len`` long;
    'of' may join two runs ("University of Notre Dame")."""
    out, i, n = [], 0, len(ws)
    while i < n:
        if lw[i] in STOP or ws[i] in PUNCT_BREAK or not ws[i][0].isalnum():
            i += 1
            continue
        j = i + 1
        while j < n and (lw[j] not in STOP and ws[j] not in PUNCT_BREAK and ws[j][0].isalnum()
                         or (lw[j] in CONNECT and j + 1 < n and lw[j + 1] not in STOP and ws[j + 1][0].isalnum()
                             and j > i)):
            j += 1
        for a in range(i, j):
            for b in range(a + 1, min(j, a + max_len) + 1):
                if lw[a] in CONNECT or lw[b - 1] in CONNECT:
                    continue
                out.append(Span(" ".join(ws[a:b]), "CHUNK", a, b))
        i = j
    return out


def _qword_positions(lw: list[str], qwords: set) -> list[int]:
    return [i for i, w in enumerate(lw) if w in qwords and w not in STOP]


def extract(q: Question, texts: list[str], rel: np.ndarray, p: ExtractParams = ExtractParams(),
            initial_is_name=None) -> Extracted:
    """``texts`` best first, ``rel`` = their scores divided by Σidf (same order)."""
    if not texts:
        return Extracted(None, 0.0, -1, [])
    k = min(p.k, len(texts))
    r = np.asarray(rel[:k], dtype=np.float64)
    sw = np.exp((r - r.max()) / p.tau)
    sw /= sw.sum()
    qwords = set(w for w in q.words if w[0].isalnum())
    qcontent = set(q.content)
    votes: dict[str, float] = {}
    surface: dict[str, tuple[float, str, int]] = {}
    for si in range(k):
        text = texts[si]
        ws = words(text)
        lw = [w.lower() for w in ws]
        qpos = _qword_positions(lw, qcontent)
        if q.atype != OTHER:
            cands = [s for s in spans(text, initial_is_name) if type_matches(q.atype, s)]
            if not p.type_only and not cands:
                cands = chunks(ws, lw, p.other_max)
        else:
            cands = chunks(ws, lw, p.other_max)
        for sp in cands:
            sw_words = [w.lower() for w in words(sp.text) if w[0].isalnum()]
            if not sw_words or all(w in qwords or w in STOP for w in sw_words):
                continue
            # drop the question words at the edges of a span ("Paris" from "capital Paris")
            if q.atype == OTHER and (sw_words[0] in qwords or sw_words[-1] in qwords):
                continue
            if qpos:
                d = min(min(abs(sp.start - x), abs(x - (sp.end - 1))) for x in qpos)
            else:
                d = 10
            v = float(sw[si]) * math.exp(-d / p.lam)
            key = normalize(sp.text)
            if not key:
                continue
            votes[key] = votes.get(key, 0.0) + v
            best = surface.get(key)
            if best is None or v > best[0]:
                surface[key] = (v, sp.text, si)
    if not votes:
        return Extracted(None, 0.0, -1, [])
    # a name's votes also count for the longer names that contain it
    keys = sorted(votes, key=lambda x: (-votes[x], x))
    merged = dict(votes)
    for a in keys:
        ta = a.split()
        for b in keys:
            if a != b and len(b.split()) > len(ta) and f" {a} " in f" {b} ":
                merged[b] += votes[a] * 0.5
    order = sorted(merged, key=lambda x: (-merged[x], -len(x.split()), x))
    total = sum(votes.values())
    top = order[0]
    conf = min(1.0, merged[top] / total) * float(r[0])
    return Extracted(surface[top][1], conf, surface[top][2], [(x, merged[x]) for x in order[:5]])


# ---------------------------------------------------------------------------
# SQuAD metrics (official v1.1 definitions)
# ---------------------------------------------------------------------------

def exact_match(pred: str | None, golds: list[str]) -> float:
    if not pred:
        return 0.0
    p = normalize(pred)
    return float(any(p == normalize(g) for g in golds))


def f1(pred: str | None, golds: list[str]) -> float:
    if not pred:
        return 0.0
    pt = normalize(pred).split()
    best = 0.0
    for g in golds:
        gt = normalize(g).split()
        common = {}
        for w in pt:
            common[w] = common.get(w, 0)
        same = 0
        gcount = {}
        for w in gt:
            gcount[w] = gcount.get(w, 0) + 1
        for w in pt:
            if gcount.get(w, 0) > 0:
                same += 1
                gcount[w] -= 1
        if same == 0:
            continue
        prec, rec = same / len(pt), same / len(gt)
        best = max(best, 2 * prec * rec / (prec + rec))
    return best


def correct(pred: str | None, gold: str, slack: int = 3) -> bool:
    """Facts/dialog rule: gold is a whole-word part of the answer, answer ≤ gold + 3 words."""
    if not pred:
        return False
    p, g = normalize(pred), normalize(gold)
    return bool(g) and f" {g} " in f" {p} " and len(p.split()) <= len(g.split()) + slack
