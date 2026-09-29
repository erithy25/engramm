"""Dependency parsing: labelled arc-hybrid transitions, an averaged perceptron and a dynamic
oracle (Kuhlmann et al. 2011; Goldberg & Nivre 2012; features after Zhang & Nivre 2011).

The parser reads left to right with a stack and moves SHIFT, RIGHT:label (the stack top becomes
a right child of the word below it) and LEFT:label (the stack top becomes a left child of the
next buffer word). Labels are part of the move, so the labels of children already attached are
features for the next decisions. The dynamic oracle knows, for any state, which moves still
allow the best reachable tree, so the parser learns from its own mistakes.

Optional second tag set (``xtags``, e.g. Penn Treebank tags from a second tagger) adds finer
word-class features; which feature groups a model uses is stored with it.
"""

from __future__ import annotations

import json
from pathlib import Path

from engramm.nlp.perceptron import AveragedPerceptron, order

SHIFT, RIGHT, LEFT = 0, 1, 2
MOVES = (SHIFT, RIGHT, LEFT)


class Parse:
    def __init__(self, n: int):
        self.n = n
        self.heads: list[int | None] = [None] * n
        self.labels = [""] * n
        self.lefts: list[list[int]] = [[] for _ in range(n)]
        self.rights: list[list[int]] = [[] for _ in range(n)]

    def add(self, head: int, child: int, label: str = "") -> None:
        self.heads[child] = head
        self.labels[child] = label
        (self.lefts if child < head else self.rights)[head].append(child)


def _valid(i: int, n: int, depth: int) -> list[int]:
    moves = []
    if i + 1 < n:
        moves.append(SHIFT)
    if depth >= 2:
        moves.append(RIGHT)
    if depth >= 1:
        moves.append(LEFT)
    return moves


def _gold_moves(n0: int, n: int, stack: list[int], gold: list) -> list[int]:
    """Moves that do not lose any gold arc still reachable (the dynamic oracle)."""
    def deps_between(target, others):
        return any(gold[w] == target or gold[target] == w for w in others)
    valid = _valid(n0, n, len(stack))
    if not stack or (SHIFT in valid and gold[n0] == stack[-1]):
        return [SHIFT]
    if gold[stack[-1]] == n0:
        return [LEFT]
    costly = set(m for m in MOVES if m not in valid)
    if len(stack) >= 2 and gold[stack[-1]] == stack[-2]:
        costly.add(LEFT)
    if SHIFT not in costly and deps_between(n0, stack):
        costly.add(SHIFT)
    if deps_between(stack[-1], range(n0 + 1, n - 1)):
        costly.add(LEFT)
        costly.add(RIGHT)
    return [m for m in MOVES if m not in costly]


def _kids(p: Parse, i: int, left: bool) -> tuple[int, int, int]:
    """The outermost and second-outermost children on one side, and how many there are."""
    if i < 0:
        return -1, -1, 0
    d = p.lefts[i] if left else p.rights[i]
    if not d:
        return -1, -1, 0
    ds = sorted(d, reverse=not left)
    return ds[0], (ds[1] if len(ds) > 1 else -1), len(d)


def features(ws, ts, xs, n0: int, n: int, stack: list[int], p: Parse, groups: frozenset) -> list[str]:
    depth = len(stack)
    s0 = stack[-1] if depth else -1
    s1 = stack[-2] if depth > 1 else -1
    s2 = stack[-3] if depth > 2 else -1
    n1 = n0 + 1 if n0 + 1 < n else -1
    n2 = n0 + 2 if n0 + 2 < n else -1

    def W(i): return ws[i] if i >= 0 else ""
    def T(i): return ts[i] if i >= 0 else ""
    def X(i): return xs[i] if i >= 0 else ""
    def L(i): return p.labels[i] if i >= 0 else ""

    s0l1, s0l2, vs0l = _kids(p, s0, True)
    s0r1, s0r2, vs0r = _kids(p, s0, False)
    n0l1, n0l2, vn0l = _kids(p, n0, True)
    s1l1, _, _ = _kids(p, s1, True)
    s1r1, _, _ = _kids(p, s1, False)
    d = min(n0 - s0, 5) if s0 >= 0 else 0
    Wn0, Wn1, Wn2, Ws0, Ws1 = W(n0), W(n1), W(n2), W(s0), W(s1)
    Tn0, Tn1, Tn2, Ts0, Ts1, Ts2 = T(n0), T(n1), T(n2), T(s0), T(s1), T(s2)
    f = ["bias"]
    for k, v in (("wn0", Wn0), ("wn1", Wn1), ("wn2", Wn2), ("ws0", Ws0), ("ws1", Ws1), ("ws2", W(s2)),
                 ("wn0b1", W(n0l1)), ("wn0b2", W(n0l2)), ("ws0b1", W(s0l1)), ("ws0b2", W(s0l2)),
                 ("ws0f1", W(s0r1)), ("ws0f2", W(s0r2)), ("tn0", Tn0), ("tn1", Tn1), ("tn2", Tn2),
                 ("ts0", Ts0), ("ts1", Ts1), ("ts2", Ts2), ("tn0b1", T(n0l1)), ("tn0b2", T(n0l2)),
                 ("ts0b1", T(s0l1)), ("ts0b2", T(s0l2)), ("ts0f1", T(s0r1)), ("ts0f2", T(s0r2))):
        if v:
            f.append(f"{k}={v}")
    f += [f"wn0tn0={Wn0}/{Tn0}", f"wn1tn1={Wn1}/{Tn1}", f"wn2tn2={Wn2}/{Tn2}", f"ws0ts0={Ws0}/{Ts0}",
          f"ws0tn0={Ws0}/{Tn0}", f"wn0ts0={Wn0}/{Ts0}", f"ts0tn0={Ts0}/{Tn0}", f"ts0ts1={Ts0}/{Ts1}",
          f"tn0tn1={Tn0}/{Tn1}", f"ts0tn0tn1={Ts0}/{Tn0}/{Tn1}", f"ts1ts0tn0={Ts1}/{Ts0}/{Tn0}",
          f"tn0tn1tn2={Tn0}/{Tn1}/{Tn2}", f"ts0ts1ts2={Ts0}/{Ts1}/{Ts2}", f"ws0wn0={Ws0}/{Wn0}",
          f"ts0ts0f1tn0={Ts0}/{T(s0r1)}/{Tn0}", f"ts0ts0b1tn0={Ts0}/{T(s0l1)}/{Tn0}",
          f"ts0tn0tn0b1={Ts0}/{Tn0}/{T(n0l1)}", f"ts0ts0b1ts0b2={Ts0}/{T(s0l1)}/{T(s0l2)}",
          f"ts0ts0f1ts0f2={Ts0}/{T(s0r1)}/{T(s0r2)}", f"tn0tn0b1tn0b2={Tn0}/{T(n0l1)}/{T(n0l2)}",
          f"ws0d={Ws0}/{d}", f"wn0d={Wn0}/{d}", f"ts0d={Ts0}/{d}", f"tn0d={Tn0}/{d}",
          f"ts0tn0d={Ts0}/{Tn0}/{d}", f"ws0vf={Ws0}/{vs0r}", f"ws0vb={Ws0}/{vs0l}", f"wn0vb={Wn0}/{vn0l}",
          f"ts0vf={Ts0}/{vs0r}", f"ts0vb={Ts0}/{vs0l}", f"tn0vb={Tn0}/{vn0l}"]
    if "lab" in groups:
        f += [f"ls0b1={L(s0l1)}", f"ls0b2={L(s0l2)}", f"ls0f1={L(s0r1)}", f"ls0f2={L(s0r2)}",
              f"ln0b1={L(n0l1)}", f"ln0b2={L(n0l2)}", f"ls1b1={L(s1l1)}", f"ls1f1={L(s1r1)}",
              f"ws0ls0b1ls0b2={Ws0}/{L(s0l1)}/{L(s0l2)}", f"ts0ls0b1ls0b2={Ts0}/{L(s0l1)}/{L(s0l2)}",
              f"ws0ls0f1ls0f2={Ws0}/{L(s0r1)}/{L(s0r2)}", f"ts0ls0f1ls0f2={Ts0}/{L(s0r1)}/{L(s0r2)}",
              f"wn0ln0b1ln0b2={Wn0}/{L(n0l1)}/{L(n0l2)}", f"tn0ln0b1ln0b2={Tn0}/{L(n0l1)}/{L(n0l2)}",
              f"ts0ls0b1tn0={Ts0}/{L(s0l1)}/{Tn0}", f"ts0ls0f1tn0={Ts0}/{L(s0r1)}/{Tn0}"]
    if "x" in groups:
        Xn0, Xn1, Xs0, Xs1 = X(n0), X(n1), X(s0), X(s1)
        f += [f"xn0={Xn0}", f"xn1={Xn1}", f"xn2={X(n2)}", f"xs0={Xs0}", f"xs1={Xs1}", f"xs2={X(s2)}",
              f"xs0xn0={Xs0}/{Xn0}", f"xs0xs1={Xs0}/{Xs1}", f"xn0xn1={Xn0}/{Xn1}",
              f"xs0xn0xn1={Xs0}/{Xn0}/{Xn1}", f"xs1xs0xn0={Xs1}/{Xs0}/{Xn0}", f"ws0xn0={Ws0}/{Xn0}",
              f"wn0xs0={Wn0}/{Xs0}", f"xs0xn0d={Xs0}/{Xn0}/{d}", f"xs0f1={X(s0r1)}", f"xs0b1={X(s0l1)}",
              f"xn0b1={X(n0l1)}", f"xs0xs0f1xn0={Xs0}/{X(s0r1)}/{Xn0}"]
    if "more" in groups:
        f += [f"ws0wn0tn0={Ws0}/{Wn0}/{Tn0}", f"ws0ts0tn0={Ws0}/{Ts0}/{Tn0}", f"wn0ts0tn0={Wn0}/{Ts0}/{Tn0}",
              f"ws0ts0wn0tn0={Ws0}/{Ts0}/{Wn0}/{Tn0}", f"wn0wn1={Wn0}/{Wn1}", f"wn0tn0tn1={Wn0}/{Tn0}/{Tn1}",
              f"ws1ts1={Ws1}/{Ts1}", f"ws1ws0={Ws1}/{Ws0}", f"ws0wn0d={Ws0}/{Wn0}/{d}",
              f"ts1ts0d={Ts1}/{Ts0}/{min(s0 - s1, 5) if s1 >= 0 else 0}"]
    return f


def _move(cls: str) -> int:
    return SHIFT if cls == "S" else (RIGHT if cls[0] == "R" else LEFT)


class Parser:
    def __init__(self, groups=("lab",)):
        self.groups = frozenset(groups)
        self.model = AveragedPerceptron()

    # -- decoding ------------------------------------------------------------------------------

    def _best(self, scores: dict, moves: list[int]) -> str:
        best, bs = "S", None
        for c in self.model.classes:
            if _move(c) in moves:
                s = scores.get(c, 0.0)
                if bs is None or s > bs:
                    best, bs = c, s
        return best

    @staticmethod
    def _apply(c: str, i: int, stack: list[int], p: Parse) -> int:
        if c == "S":
            stack.append(i)
            return i + 1
        if c[0] == "R":
            p.add(stack[-2], stack.pop(), c[2:])
        else:
            p.add(i, stack.pop(), c[2:])
        return i

    @staticmethod
    def _padded(words, tags, xtags):
        ws = ["<start>"] + [w.lower() for w in words] + ["ROOT"]
        ts = ["START"] + list(tags) + ["ROOT"]
        xs = ["START"] + list(xtags if xtags is not None else tags) + ["ROOT"]
        return ws, ts, xs

    def parse_labelled(self, words: list[str], tags: list[str],
                       xtags: list[str] | None = None) -> tuple[list[int], list[str]]:
        """Heads (0 = root, else 1-based) and labels of ``words`` given their tags."""
        if not words:
            return [], []
        ws, ts, xs = self._padded(words, tags, xtags)
        n = len(ws)
        i, stack, p = 2, [1], Parse(n)
        while stack or i + 1 < n:
            sc = self.model.scores(features(ws, ts, xs, i, n, stack, p, self.groups))
            i = self._apply(self._best(sc, _valid(i, n, len(stack))), i, stack, p)
        heads = [0 if (p.heads[w] is None or p.heads[w] == n - 1) else p.heads[w] for w in range(1, n - 1)]
        labels = [("root" if h == 0 else (p.labels[w] or "dep")) for w, h in zip(range(1, n - 1), heads)]
        return heads, labels

    def parse(self, words: list[str], tags: list[str], xtags: list[str] | None = None) -> list[int]:
        return self.parse_labelled(words, tags, xtags)[0]

    # -- training ------------------------------------------------------------------------------

    def train(self, sentences, epochs: int = 10, key: str = "parse", log=None, checkpoints=(),
              on_checkpoint=None, explore_from: int = 0) -> None:
        """sentences: (words, tags, heads, labels[, xtags]) with tags from the tagger. Before epoch
        ``explore_from`` the parser follows the best gold move (static training); from then on it
        follows its own guesses and the dynamic oracle corrects it (Goldberg & Nivre 2012)."""
        labs = sorted({lab for s in sentences for lab in s[3] if lab != "root"})
        self.model.classes = ["S"] + [f"R:{lab}" for lab in labs] + [f"L:{lab}" for lab in labs]
        ids = list(range(len(sentences)))
        for ep in range(epochs):
            correct = total = 0
            for idx in order(ids, f"{key}|{ep}"):
                s = sentences[idx]
                correct += self._train_one(s[0], s[1], s[2], s[3], s[4] if len(s) > 4 else None,
                                           explore=ep >= explore_from)
                total += len(s[0])
            if log:
                log(f"parse epoch {ep + 1}: train UAS {correct / max(total, 1):.4f}")
            if on_checkpoint and ep + 1 in checkpoints and ep + 1 != epochs:
                on_checkpoint(ep + 1, self.averaged_copy())
        self.model.average()

    def averaged_copy(self) -> Parser:
        """The parser with the weights averaged so far (training can continue on self)."""
        m = self.model
        cp = Parser(self.groups)
        cp.model.classes = list(m.classes)
        for f, w in m.weights.items():
            d = {}
            for c, v in w.items():
                key = (f, c)
                a = round((m._totals.get(key, 0.0) + (m.i - m._stamps.get(key, 0)) * v) / max(m.i, 1), 4)
                if a:
                    d[c] = a
            if d:
                cp.model.weights[f] = d
        return cp

    def _train_one(self, words, tags, heads, labels, xtags, explore: bool = True) -> int:
        ws, ts, xs = self._padded(words, tags, xtags)
        n = len(ws)
        gold = [None] + [h if h != 0 else n - 1 for h in heads] + [None]
        glab = [None] + list(labels) + [None]
        i, stack, p = 2, [1], Parse(n)
        while stack or i + 1 < n:
            fs = features(ws, ts, xs, i, n, stack, p, self.groups)
            sc = self.model.scores(fs)
            valid = _valid(i, n, len(stack))
            guess = self._best(sc, valid)
            gcls = []
            for m in _gold_moves(i, n, stack, gold) or valid:
                if m == SHIFT:
                    gcls.append("S")
                    continue
                s0 = stack[-1]
                side = "R" if m == RIGHT else "L"
                if gold[s0] == (stack[-2] if m == RIGHT else i) and glab[s0] != "root":
                    gcls.append(f"{side}:{glab[s0]}")
                else:                                   # not a gold arc: any label costs the same
                    gcls += [c for c in self.model.classes if c[0] == side]
            best = max(gcls, key=lambda c: sc.get(c, 0.0))
            self.model.update(best, guess, fs)
            i = self._apply(guess if explore else best, i, stack, p)
        return sum(1 for w in range(1, n - 1) if p.heads[w] == gold[w])

    # -- files ---------------------------------------------------------------------------------

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps({"kind": "parse", "version": 2, "groups": sorted(self.groups),
                                          "model": self.model.to_dict()}, separators=(",", ":")),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Parser:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        if d.get("version") != 2:
            raise ValueError(f"{path}: parser model version {d.get('version')} is not supported")
        p = cls(d["groups"])
        p.model = AveragedPerceptron.from_dict(d["model"])
        return p
