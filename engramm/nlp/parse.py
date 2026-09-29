"""Dependency parsing: arc-hybrid transitions, an averaged perceptron and a dynamic oracle
(Kuhlmann et al. 2011; Goldberg & Nivre 2012; after Honnibal's "Parsing English in 500 lines").

The parser reads left to right with a stack and moves SHIFT, RIGHT (the stack top becomes a
right child of the word below it) and LEFT (the stack top becomes a left child of the next
buffer word). The dynamic oracle knows, for any state, which moves still allow the best
reachable tree, so the parser learns from its own mistakes. Labels (nsubj, obj, …) are
assigned afterwards by a second perceptron from the head and the dependent.
"""

from __future__ import annotations

import json
from pathlib import Path

from engramm.nlp.perceptron import AveragedPerceptron, order

SHIFT, RIGHT, LEFT = 0, 1, 2
MOVES = (SHIFT, RIGHT, LEFT)
MOVE_NAMES = ("S", "R", "L")


class Parse:
    def __init__(self, n: int):
        self.n = n
        self.heads = [None] * (n - 1)
        self.labels = [None] * (n - 1)
        self.lefts = [[] for _ in range(n + 1)]
        self.rights = [[] for _ in range(n + 1)]

    def add(self, head: int, child: int) -> None:
        self.heads[child] = head
        if child < head:
            self.lefts[head].append(child)
        else:
            self.rights[head].append(child)


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


def _features(words: list[str], tags: list[str], n0: int, n: int, stack: list[int], parse: Parse) -> list[str]:
    def get_stack_context(depth, stack, data):
        if depth >= 3:
            return data[stack[-1]], data[stack[-2]], data[stack[-3]]
        if depth == 2:
            return data[stack[-1]], data[stack[-2]], ""
        if depth == 1:
            return data[stack[-1]], "", ""
        return "", "", ""

    def get_buffer_context(i, n, data):
        if i + 1 >= n:
            return data[i], "", ""
        if i + 2 >= n:
            return data[i], data[i + 1], ""
        return data[i], data[i + 1], data[i + 2]

    def get_parse_context(word, deps, data):
        if word == -1:
            return 0, "", ""
        deps = deps[word]
        valency = len(deps)
        if not valency:
            return 0, "", ""
        if valency == 1:
            return 1, data[deps[-1]], ""
        return valency, data[deps[-1]], data[deps[-2]]

    depth = len(stack)
    s0 = stack[-1] if depth else -1
    Ws0, Ws1, Ws2 = get_stack_context(depth, stack, words)
    Ts0, Ts1, Ts2 = get_stack_context(depth, stack, tags)
    Wn0, Wn1, Wn2 = get_buffer_context(n0, n, words)
    Tn0, Tn1, Tn2 = get_buffer_context(n0, n, tags)
    Vn0b, Wn0b1, Wn0b2 = get_parse_context(n0, parse.lefts, words)
    Vn0b, Tn0b1, Tn0b2 = get_parse_context(n0, parse.lefts, tags)
    Vn0f, Wn0f1, Wn0f2 = get_parse_context(n0, parse.rights, words)
    _, Tn0f1, Tn0f2 = get_parse_context(n0, parse.rights, tags)
    Vs0b, Ws0b1, Ws0b2 = get_parse_context(s0, parse.lefts, words)
    _, Ts0b1, Ts0b2 = get_parse_context(s0, parse.lefts, tags)
    Vs0f, Ws0f1, Ws0f2 = get_parse_context(s0, parse.rights, words)
    _, Ts0f1, Ts0f2 = get_parse_context(s0, parse.rights, tags)
    Ds0n0 = min((n0 - s0, 5)) if s0 != 0 else 0
    f = ["bias"]
    for name, v in (("wn0", Wn0), ("wn1", Wn1), ("wn2", Wn2), ("ws0", Ws0), ("ws1", Ws1), ("ws2", Ws2),
                    ("wn0b1", Wn0b1), ("wn0b2", Wn0b2), ("ws0b1", Ws0b1), ("ws0b2", Ws0b2), ("ws0f1", Ws0f1),
                    ("ws0f2", Ws0f2), ("tn0", Tn0), ("tn1", Tn1), ("tn2", Tn2), ("ts0", Ts0), ("ts1", Ts1),
                    ("ts2", Ts2), ("tn0b1", Tn0b1), ("tn0b2", Tn0b2), ("ts0b1", Ts0b1), ("ts0b2", Ts0b2),
                    ("ts0f1", Ts0f1), ("ts0f2", Ts0f2)):
        if v:
            f.append(f"{name}={v}")
    f += [f"wn0tn0={Wn0}/{Tn0}", f"wn1tn1={Wn1}/{Tn1}", f"wn2tn2={Wn2}/{Tn2}", f"ws0ts0={Ws0}/{Ts0}",
          f"ws0tn0={Ws0}/{Tn0}", f"wn0ts0={Wn0}/{Ts0}", f"ts0tn0={Ts0}/{Tn0}", f"ts0ts1={Ts0}/{Ts1}",
          f"tn0tn1={Tn0}/{Tn1}", f"ts0tn0tn1={Ts0}/{Tn0}/{Tn1}", f"ts1ts0tn0={Ts1}/{Ts0}/{Tn0}",
          f"tn0tn1tn2={Tn0}/{Tn1}/{Tn2}", f"ts0ts1ts2={Ts0}/{Ts1}/{Ts2}", f"ws0wn0={Ws0}/{Wn0}",
          f"ts0ts0f1tn0={Ts0}/{Ts0f1}/{Tn0}", f"ts0ts0b1tn0={Ts0}/{Ts0b1}/{Tn0}",
          f"ts0tn0tn0b1={Ts0}/{Tn0}/{Tn0b1}", f"ts0ts0b1ts0b2={Ts0}/{Ts0b1}/{Ts0b2}",
          f"ts0ts0f1ts0f2={Ts0}/{Ts0f1}/{Ts0f2}", f"tn0tn0b1tn0b2={Tn0}/{Tn0b1}/{Tn0b2}",
          f"ws0d={Ws0}/{Ds0n0}", f"wn0d={Wn0}/{Ds0n0}", f"ts0d={Ts0}/{Ds0n0}", f"tn0d={Tn0}/{Ds0n0}",
          f"ts0tn0d={Ts0}/{Tn0}/{Ds0n0}", f"ws0vf={Ws0}/{Vs0f}", f"ws0vb={Ws0}/{Vs0b}", f"wn0vb={Wn0}/{Vn0b}",
          f"ts0vf={Ts0}/{Vs0f}", f"ts0vb={Ts0}/{Vs0b}", f"tn0vb={Tn0}/{Vn0b}"]
    return f


class Parser:
    def __init__(self):
        self.model = AveragedPerceptron([str(m) for m in MOVES])
        self.labeller = AveragedPerceptron()

    def _transition(self, move: int, i: int, stack: list[int], parse: Parse) -> int:
        if move == SHIFT:
            stack.append(i)
            return i + 1
        if move == RIGHT:
            parse.add(stack[-2], stack.pop())
            return i
        parse.add(i, stack.pop())
        return i

    def parse(self, words: list[str], tags: list[str]) -> list[int]:
        """Heads (0 = root, else 1-based) of ``words`` given their tags."""
        ws = ["<start>"] + [w.lower() for w in words] + ["ROOT"]
        ts = ["START"] + list(tags) + ["ROOT"]
        n = len(ws)
        i, stack, p = 2, [1], Parse(n)
        while stack or i + 1 < n:
            feats = _features(ws, ts, i, n, stack, p)
            scores = self.model.scores(feats)
            valid = _valid(i, n, len(stack))
            move = max(valid, key=lambda m: (scores.get(str(m), 0.0), -m))
            i = self._transition(move, i, stack, p)
        return [0 if (p.heads[w] is None or p.heads[w] == n - 1) else p.heads[w] for w in range(1, n - 1)]

    def label(self, words: list[str], tags: list[str], heads: list[int]) -> list[str]:
        return [self.labeller.predict(self._label_features(words, tags, heads, d)) for d in range(len(words))]

    def _label_features(self, words, tags, heads, d) -> list[str]:
        h = heads[d] - 1
        hw = words[h].lower() if h >= 0 else "<root>"
        ht = tags[h] if h >= 0 else "ROOT"
        dw, dt = words[d].lower(), tags[d]
        side = "L" if h >= 0 and d < h else ("R" if h >= 0 else "0")
        dist = min(abs(d - h), 6) if h >= 0 else 0
        return ["b", f"dt={dt}", f"ht={ht}", f"dw={dw}", f"hw={hw}", f"dt,ht={dt},{ht}", f"dw,ht={dw},{ht}",
                f"dt,hw={dt},{hw}", f"side={side}", f"dt,side={dt},{side}", f"dt,ht,side={dt},{ht},{side}",
                f"dist={dist}", f"dt,dist={dt},{dist}",
                f"prev={tags[d - 1] if d else 'S'}", f"next={tags[d + 1] if d + 1 < len(tags) else 'E'}"]

    def train(self, sentences, epochs: int = 10, key: str = "parse", log=None) -> None:
        """sentences: (words, tags, heads, labels) with gold tags or tags from the tagger."""
        self.labeller.classes = sorted({lab for *_, labs in sentences for lab in labs})
        ids = list(range(len(sentences)))
        for ep in range(epochs):
            correct = total = 0
            for idx in order(ids, f"{key}|{ep}"):
                words, tags, heads, labels = sentences[idx]
                correct += self._train_one(words, tags, heads)
                total += len(words)
                for d in range(len(words)):
                    feats = self._label_features(words, tags, heads, d)
                    self.labeller.update(labels[d], self.labeller.predict(feats), feats)
            if log:
                log(f"parse epoch {ep + 1}: train UAS {correct / max(total, 1):.4f}")
        self.model.average()
        self.labeller.average()

    def _train_one(self, words, tags, heads) -> int:
        ws = ["<start>"] + [w.lower() for w in words] + ["ROOT"]
        ts = ["START"] + list(tags) + ["ROOT"]
        n = len(ws)
        gold = [None] + [h if h != 0 else n - 1 for h in heads] + [None]
        i, stack, p = 2, [1], Parse(n)
        while stack or i + 1 < n:
            feats = _features(ws, ts, i, n, stack, p)
            scores = self.model.scores(feats)
            valid = _valid(i, n, len(stack))
            guess = max(valid, key=lambda m: (scores.get(str(m), 0.0), -m))
            golds = _gold_moves(i, n, stack, gold) or valid
            best = max(golds, key=lambda m: (scores.get(str(m), 0.0), -m))
            self.model.update(str(best), str(guess), feats)
            i = self._transition(guess, i, stack, p)
        return sum(1 for w in range(1, n - 1) if p.heads[w] == gold[w])

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps({"kind": "parse", "model": self.model.to_dict(),
                                          "labeller": self.labeller.to_dict()}, separators=(",", ":")),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Parser:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        p = cls()
        p.model = AveragedPerceptron.from_dict(d["model"])
        p.labeller = AveragedPerceptron.from_dict(d["labeller"])
        return p
