"""Stage 4 — choosing the answer span by counting (docs/PREREG_CHAT_V2.md v1.1).

Every candidate span of a sentence is described by a handful of discrete features:

* its kind (name, date, number, content-word chunk, definition phrase) and length;
* where it lies relative to the question words found in the sentence (before, inside,
  after; distance bucket) and whether that is the side the question points to;
* the words around it — function words literally, other words as ENGRAMM's own HDC
  word class (512 classes from the counted meaning vectors), capitals and numbers as
  shapes;
* the HDC word class of its first and last word, and how close its meaning vector is
  to the question's head noun ("What *instrument* …").

Each feature is paired with the expected answer type of the question. From SQuAD
questions of articles that are neither test nor dev articles, ENGRAMM counts how often
each feature occurs on the gold span and on the other candidates; the score of a span
is the sum of the log count ratios (naive Bayes). Nothing else is learnt.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engramm.chat.question import CONNECT, OTHER, STOP, Question, Span, spans, words

PUNCT = frozenset(",.;:!?()[]{}\"“”‘’'—–-/")
_AUX = frozenset(("did", "does", "do", "was", "were", "is", "are", "has", "have", "had", "can", "could", "will",
                  "would", "should", "may", "might"))


def question_direction(q: Question) -> int:
    ws = [w for w in q.words if w[0].isalnum()]
    for i, w in enumerate(ws):
        if w in ("what", "which", "who", "whom", "whose"):
            j = i + 1
            if w in ("what", "which", "whose") and j < len(ws) and ws[j] not in _AUX and ws[j] not in STOP:
                j += 1
            if j < len(ws):
                return 1 if ws[j] in _AUX else -1
            return 0
    return 0


def chunk_spans(ws: list[str], lw: list[str], max_len: int) -> list[Span]:
    """All sub-runs (≤ max_len words) of runs of content words; 'of'/'the'/… may sit inside."""
    out, i, n = [], 0, len(ws)
    while i < n:
        if lw[i] in STOP or ws[i] in PUNCT or not ws[i][0].isalnum():
            i += 1
            continue
        j = i + 1
        while j < n and ((lw[j] not in STOP and ws[j] not in PUNCT and ws[j][0].isalnum())
                         or (lw[j] in CONNECT and j + 1 < n and lw[j + 1] not in STOP and ws[j + 1][0].isalnum())):
            j += 1
        for a in range(i, j):
            if lw[a] in CONNECT:
                continue
            for b in range(a + 1, min(j, a + max_len) + 1):
                if lw[b - 1] in CONNECT:
                    continue
                out.append(Span(" ".join(ws[a:b]), "CHUNK", a, b))
        i = j
    return out


NUM_MODS = (("more", "than"), ("less", "than"), ("fewer", "than"), ("over",), ("about",), ("around",), ("nearly",),
            ("almost",), ("approximately",), ("roughly",), ("some",), ("at", "least"), ("up", "to"), ("under",))


def candidate_spans(text: str, initial_is_name=None, max_chunk: int = 6) -> tuple[list[str], list[Span]]:
    """(words, candidates): typed spans of every kind, the year inside a date, numbers with
    their modifier ("more than 350,000", "80% or more"), content chunks."""
    ws = words(text)
    lw = [w.lower() for w in ws]
    out: list[Span] = []
    seen = set()
    for sp in spans(text, initial_is_name):
        key = (sp.start, sp.end, sp.kind)
        if key not in seen:
            seen.add(key)
            out.append(sp)
        if sp.kind == "NUMBER":
            for mod in NUM_MODS:
                a = sp.start - len(mod)
                if a >= 0 and tuple(lw[a:sp.start]) == mod:
                    out.append(Span(" ".join(ws[a:sp.start]) + " " + sp.text, "NUMBER", a, sp.end))
            if sp.end + 1 < len(ws) and lw[sp.end] == "or" and lw[sp.end + 1] in ("more", "less", "fewer"):
                out.append(Span(f"{sp.text} {ws[sp.end]} {ws[sp.end + 1]}", "NUMBER", sp.start, sp.end + 2))
        if sp.kind == "DATE":
            m = re.search(r"(\d{3,4}\s(?:BC|BCE|AD|CE)|AD\s\d{1,4}|\d{3,4})(?!\d)", sp.text)
            if m and m.group(1) != sp.text:
                out.append(Span(m.group(1), "YEAR", sp.start, sp.end))
    for sp in chunk_spans(ws, lw, max_chunk):
        if (sp.start, sp.end, "NAME") in seen or (sp.start, sp.end, "NUMBER") in seen or \
                (sp.start, sp.end, "DATE") in seen:
            continue
        out.append(sp)
    return ws, out


def _shape(w: str, cls) -> str:
    lw = w.lower()
    if not w:
        return "<none>"
    if w in PUNCT:
        return w
    if lw in STOP:
        return lw
    if w[0].isdigit():
        return "<num>"
    if w[0].isupper():
        return "<cap>"
    c = cls(lw)
    return f"c{c}" if c is not None else "<w>"


def _dist_bucket(d: int) -> str:
    return "0" if d <= 0 else "1" if d == 1 else "2-3" if d <= 3 else "4-6" if d <= 6 else "7-10" if d <= 10 else ">10"


def _granularity_ok(q: Question, sp: Span) -> int:
    qw = set(q.words)
    t = sp.text
    if "year" in qw or "years" in qw:
        return int(bool(re.fullmatch(r"\d{3,4}(\s(BC|BCE|AD|CE))?|AD\s\d{1,4}", t)))
    if "decade" in qw:
        return int(bool(re.fullmatch(r"\d{3}0s", t)))
    if "century" in qw or "centuries" in qw:
        return int("century" in t.lower())
    if "month" in qw:
        return int(t.lower() in ("january", "february", "march", "april", "may", "june", "july", "august",
                                 "september", "october", "november", "december"))
    return 2


def span_features(q: Question, ws: list[str], lw: list[str], sp: Span, anchors: list[int], qdir: int, qwords: set,
                  cls, head_sim=None, extended: bool = False) -> list[str]:
    A = q.atype
    wh = q.wh or "none"
    n = len(ws)
    L = min(sp.end - sp.start, 6)
    feats = [f"k|{A}|{sp.kind}", f"l|{A}|{sp.kind}|{L}", f"wl|{wh}|{L}"]
    if sp.kind in ("DATE", "YEAR"):
        feats.append(f"dg|{_granularity_ok(q, sp)}|{sp.kind}")
    near = sum(1 for i in range(max(0, sp.start - 3), min(n, sp.end + 3))
               if not (sp.start <= i < sp.end) and lw[i] in qwords and lw[i] not in STOP)
    feats.append(f"win|{A}|{min(near, 4)}")
    if anchors:
        first, last = min(anchors), max(anchors)
        if sp.end <= first:
            rel, d = "before", first - sp.end + 1
        elif sp.start > last:
            rel, d = "after", sp.start - last
        else:
            rel, d = "inside", min(abs(sp.start - x) for x in anchors)
        feats += [f"p|{A}|{rel}|{_dist_bucket(d)}", f"d|{qdir}|{rel}"]
    else:
        feats.append(f"p|{A}|none")
    prev = ws[sp.start - 1] if sp.start > 0 else "<s>"
    nxt = ws[sp.end] if sp.end < n else "</s>"
    feats += [f"pw|{A}|{_shape(prev, cls) if prev != '<s>' else prev}",
              f"nw|{A}|{_shape(nxt, cls) if nxt != '</s>' else nxt}",
              f"wpw|{wh}|{prev.lower()}", f"wnw|{wh}|{nxt.lower()}"]
    if sp.start > 1:
        feats.append(f"pw2|{A}|{_shape(ws[sp.start - 2], cls)}|{_shape(prev, cls)}")
    span_words = [w for w in ws[sp.start:sp.end] if w[0].isalnum()] or [sp.text]
    fc, lc = cls(span_words[0].lower()), cls(span_words[-1].lower())
    feats += [f"fc|{A}|{fc}", f"lc|{A}|{lc}",
              f"qo|{A}|{int(any(w.lower() in qwords for w in span_words))}",
              f"cap|{A}|{sp.kind}|{int(all(w[0].isupper() or w.lower() in CONNECT for w in span_words))}"]
    if q.head:
        feats += [f"h|{q.head}|{sp.kind}", f"hpw|{q.head}|{prev.lower()}"]
        if head_sim is not None:
            s = head_sim(span_words)
            if s is not None:
                feats.append(f"hs|{A}|{min(9, max(0, int((s - 0.5) * 40)))}")
    if extended:
        # the words right next to the span that the question also uses ("founded by X" for "who founded")
        qc = {w for w in qwords if w not in STOP}
        left = [w for w in lw[max(0, sp.start - 3):sp.start] if w in qc]
        right = [w for w in lw[sp.end:sp.end + 3] if w in qc]
        feats += [f"qp|{A}|{int(prev.lower() in qc)}", f"qn|{A}|{int(nxt.lower() in qc)}",
                  f"q3|{A}|{min(len(left), 2)}|{min(len(right), 2)}",
                  f"kp|{A}|{sp.kind}|{next((f.split('|', 2)[2] for f in feats if f.startswith('p|')), '')}"]
        if L <= 3:
            feats += [f"fw|{A}|{span_words[0].lower()}", f"lw|{A}|{span_words[-1].lower()}"]
        inside = sum(1 for i in range(sp.start) if ws[i] == "(") > sum(1 for i in range(sp.start) if ws[i] == ")")
        feats.append(f"par|{A}|{int(inside)}")
        feats.append(f"qhw|{wh}|{q.head or '-'}|{fc}")
        n_anch = len(set(lw[a] for a in anchors)) if anchors else 0
        feats.append(f"na|{A}|{min(n_anch, 4)}")
        # conjunctions a linear model cannot build itself
        feats.append(f"pn|{A}|{_shape(prev, cls) if prev != '<s>' else prev}|{_shape(nxt, cls) if nxt != '</s>' else nxt}")
        qv = next((w for w in q.content if w != (q.head or "")), "-")
        feats.append(f"qv|{qv}|{prev.lower()}")
        feats.append(f"qvn|{qv}|{nxt.lower()}")
        if q.head:
            feats.append(f"hl|{q.head}|{lc}")
        if extended == 2:
            feats += [f"fl|{wh}|{fc}|{lc}", f"pf|{A}|{_shape(prev, cls) if prev != '<s>' else prev}|{fc}",
                      f"ln|{A}|{lc}|{_shape(nxt, cls) if nxt != '</s>' else nxt}",
                      f"kl|{wh}|{sp.kind}|{L}|{next((f.split('|', 2)[2] for f in feats if f.startswith('p|')), '')}"]
    return feats


@dataclass
class SpanStats:
    pos: dict = field(default_factory=dict)
    neg: dict = field(default_factory=dict)
    n_pos: int = 0
    n_neg: int = 0
    alpha: float = 1.0
    _w: dict = field(default_factory=dict)

    def add(self, feats: list[str], positive: bool | float) -> None:
        """Count one candidate; ``positive`` may be a weight in [0, 1] (soft label)."""
        w = float(positive)
        for f in feats:
            if w > 0:
                self.pos[f] = self.pos.get(f, 0) + w
            if w < 1:
                self.neg[f] = self.neg.get(f, 0) + (1.0 - w)
        self.n_pos += w
        self.n_neg += 1.0 - w

    def weight(self, f: str) -> float:
        w = self._w.get(f)
        if w is None:
            a = self.alpha
            w = math.log((self.pos.get(f, 0) + a) / (self.n_pos + 2 * a)) - \
                math.log((self.neg.get(f, 0) + a) / (self.n_neg + 2 * a))
            self._w[f] = w
        return w

    def score(self, feats: list[str]) -> float:
        return sum(self.weight(f) for f in feats)

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps({"n_pos": self.n_pos, "n_neg": self.n_neg, "alpha": self.alpha,
                                          "pos": dict(sorted(self.pos.items())),
                                          "neg": dict(sorted(self.neg.items()))}, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> SpanStats:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(d["pos"], d["neg"], d["n_pos"], d["n_neg"], d["alpha"])


def _h64(key: str) -> int:
    return int.from_bytes(hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest(), "little")


class CompactWeights:
    """A read-only feature → weight table in two numpy arrays (64-bit key hashes, sorted, and the
    weights): about 16 bytes per feature instead of ~90 in a dict of strings. ``get`` matches
    ``dict.get``; a hash collision with an unseen feature has probability ~n / 2^64."""

    def __init__(self, weights: dict):
        items = sorted(((_h64(k), v) for k, v in weights.items()))
        self.keys = np.fromiter((k for k, _ in items), dtype=np.uint64, count=len(items))
        self.vals = np.fromiter((v for _, v in items), dtype=np.float64, count=len(items))
        self._cache: dict[str, float] = {}

    def __len__(self) -> int:
        return len(self.keys)

    def get(self, key: str, default: float = 0.0) -> float:
        c = self._cache.get(key)
        if c is not None:
            return c
        h = np.uint64(_h64(key))
        i = int(np.searchsorted(self.keys, h))
        v = float(self.vals[i]) if i < len(self.keys) and self.keys[i] == h else default
        if len(self._cache) < 200_000:            # features repeat across questions (tags, classes)
            self._cache[key] = v
        return v


@dataclass
class SpanPerceptron:
    """Averaged perceptron over the same feature strings: each weight is a count of how often
    the feature was on the gold span minus on the wrongly chosen one (averaged over the
    training passes). Drop-in for SpanStats (``score``)."""
    w: dict = field(default_factory=dict)
    extended: bool = True
    domain: bool = False
    max_chunk: int = 5

    def score(self, feats: list[str]) -> float:
        g = self.w.get
        return sum(g(f, 0.0) for f in feats)

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps({"extended": self.extended, "domain": self.domain,
                                          "max_chunk": self.max_chunk,
                                          "w": {k: round(v, 6) for k, v in sorted(self.w.items()) if v != 0}},
                                         ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path, compact: bool = False) -> SpanPerceptron:
        """``compact``: the weights as a CompactWeights table (read-only, ~6x less memory; the app)."""
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        meta = (d.get("extended", True), d.get("domain", False), d.get("max_chunk", 5))
        w = CompactWeights(d.pop("w")) if compact else d["w"]
        return cls(w, *meta)


class WordInfo:
    """HDC word class and meaning vector of a word (via its first token)."""

    def __init__(self, tok, classes: np.ndarray, vecs: np.ndarray | None):
        self.tok, self.classes, self.vecs = tok, classes, vecs
        self._c: dict = {}
        self._v: dict = {}

    def cls(self, w: str):
        c = self._c.get(w)
        if c is None and w not in self._c:
            ids = self.tok.encode(" " + w)
            c = int(self.classes[ids[0]]) if len(ids) else None
            self._c[w] = c
        return c

    def vec(self, w: str):
        if self.vecs is None:
            return None
        if w not in self._v:
            ids = self.tok.encode(" " + w)
            self._v[w] = np.asarray(self.vecs[ids[0]]) if len(ids) == 1 else None
        return self._v[w]

    def head_sim(self, head: str):
        hv = self.vec(head) if head else None
        if hv is None:
            return None
        bits = 64 * len(hv)

        def f(span_words):
            best = None
            for w in span_words:
                v = self.vec(w.lower())
                if v is not None:
                    s = 1.0 - int(np.bitwise_count(v ^ hv).sum()) / bits
                    best = s if best is None else max(best, s)
            return best
        return f


def stem(w: str) -> str:
    """A light suffix rule so that "revenues", "founded" and "founding" meet "revenue" and "found"."""
    if w.endswith(("'s", "’s")):
        w = w[:-2]
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 4 and w.endswith("es") and w[-3] in "sxz":
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


ANCHOR_STEMS = False       # tried in v12 development: no gain (dev12 F1 32.36 vs 32.43)


def anchors_of(lw: list[str], q: Question) -> list[int]:
    qc = set(q.content)
    if not ANCHOR_STEMS:
        return [i for i, w in enumerate(lw) if w in qc]
    qs = {stem(w) for w in qc}
    return [i for i, w in enumerate(lw) if w in qc or (w[0].isalnum() and stem(w) in qs)]


def question_form(q: Question) -> str:
    """"nq" for a search-box query (lower case, no question mark), else "sq"."""
    t = q.text.strip()
    return "nq" if t[:1].islower() and not t.endswith("?") else "sq"


def features_for_sentence(q: Question, text: str, info: WordInfo, initial_is_name=None, max_chunk: int = 5,
                          extended: bool = False, domain: bool = False):
    """(candidates, their feature lists) of one sentence."""
    ws, cands = candidate_spans(text, initial_is_name, max_chunk)
    lw = [w.lower() for w in ws]
    anchors = anchors_of(lw, q)
    qdir = question_direction(q)
    qwords = set(w for w in q.words if w[0].isalnum())
    hs = info.head_sim(q.head) if q.head and q.head not in STOP else None
    out = []
    for sp in cands:
        sw = [w.lower() for w in words(sp.text) if w[0].isalnum()]
        if not sw or all(w in qwords or w in STOP for w in sw):
            continue
        out.append((sp, span_features(q, ws, lw, sp, anchors, qdir, qwords, info.cls, hs, extended)))
    if extended and out:
        # how much of the question the sentence covers (the sentence's own relevance)
        qc = set(q.content)
        cov = len(qc & set(lw)) / max(len(qc), 1)
        tag = f"sc|{q.atype}|{min(int(cov * 5), 4)}"
        out = [(sp, f + [tag]) for sp, f in out]
    if domain and out:
        # every feature once more, specific to the form of the question (shared + form-specific weights)
        d = question_form(q)
        out = [(sp, f + [f"@{d}|{x}" for x in f]) for sp, f in out]
    return out


_ = OTHER
