"""The user's learning state: an ordered log of small, exact learning steps, folded into what the chat uses.

Every step is one entry in ``ops``; the derived parts (classifier weights from corrections, taught words, style,
episodes, bandit counts) are always recomputed from the log. Forgetting a step removes it from the log and folds again,
so the file afterwards is byte-for-byte what it was before the step was learned ("vergiss das" / "forget that"). The
file carries a SHA-256 of its content; a damaged file is set aside, never half-read.

Nothing leaves the computer: the file sits next to the chat memory (``learn.json``).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

VERSION = 1
LEARN_RATE = 2.0          # how far beyond the wrong kind one correction moves the right one (in score units)
MAX_STEP = 25.0           # cap per feature and step: one correction can never dominate everything
MAX_OPS = 5000            # oldest rewards are dropped first beyond this (corrections and words are kept)
# features of a message a correction may move: its words, lemmas, word pairs, classes — never the bias or the rule
_LEARNABLE = ("w:", "l:", "b:")           # the message's own words: general features are shared by many messages


def _tokens(text: str) -> set[str]:
    import re
    return set(re.findall(r"[a-zäöüß0-9']+", text.lower()))


def exemplar(extra: dict | None, text: str) -> str | None:
    """The kind of a corrected sentence this message is (nearly) identical to, or None."""
    ex = (extra or {}).get("__ex__")
    if not ex:
        return None
    toks = _tokens(text)
    if not toks:
        return None
    best, kind = 0.0, None
    for words, k in ex:
        w = set(words)
        j = len(toks & w) / len(toks | w)
        if j > best:
            best, kind = j, k
    return kind if best >= 0.8 else None


def _dump(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class LearnState:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else None
        self.ops: list[dict] = []
        self.seq = 0                       # increasing step number (kept in the log entries)
        self.extra: dict = {}
        self.words: dict[str, dict] = {}
        self.style: dict[str, str] = {}
        self.episodes: list[dict] = []
        self.bandit: dict[str, list[float]] = {}
        if self.path and self.path.exists():
            self._load()
        self._fold()

    # -- persistence --------------------------------------------------------------------------------------------
    def _load(self) -> None:
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
            body = {"version": d["version"], "ops": d["ops"], "seq": d["seq"]}
            if d.get("sha256") != hashlib.sha256(_dump(body).encode()).hexdigest() or d["version"] != VERSION:
                raise ValueError("checksum")
            self.ops, self.seq = list(d["ops"]), int(d["seq"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            bad = self.path.with_suffix(".damaged.json")
            os.replace(self.path, bad)          # keep it for inspection, start clean
            self.ops, self.seq = [], 0

    def to_bytes(self) -> bytes:
        body = {"version": VERSION, "ops": self.ops, "seq": self.seq}
        return _dump({**body, "sha256": hashlib.sha256(_dump(body).encode()).hexdigest()}).encode("utf-8")

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_bytes(self.to_bytes())
        os.replace(tmp, self.path)

    # -- folding ------------------------------------------------------------------------------------------------
    def _fold(self) -> None:
        self.extra, self.words, self.style, self.episodes, self.bandit = {}, {}, {}, [], {}
        for op in self.ops:
            t = op["op"]
            if t == "correct":
                if op.get("text"):
                    self.extra.setdefault("__ex__", []).append([sorted(_tokens(op["text"])), op["good"]])
                for f, d in op["delta"].items():
                    slot = self.extra.setdefault(f, {})
                    for k, v in d.items():
                        slot[k] = round(slot.get(k, 0.0) + v, 6)
            elif t == "word":
                self.words[op["lang"] + ":" + op["word"]] = {"cats": op["cats"], "ss": op.get("ss", "")}
            elif t == "style":
                if op["value"]:
                    self.style[op["key"]] = op["value"]
                else:
                    self.style.pop(op["key"], None)
            elif t == "episode":
                self.episodes.append({k: op[k] for k in ("date", "kind", "obj", "text", "lang")})
            elif t == "reward":
                a = self.bandit.setdefault(op["arm"], [0.0, 0.0])
                a[0 if op["r"] else 1] += 1.0
        self._apply_words()

    def _apply_words(self) -> None:
        from engramm.understand.lex import Entry, lexicon
        for lang in ("en", "de"):
            lx = lexicon(lang)
            lx.user = {}
            for key, w in self.words.items():
                l, word = key.split(":", 1)
                if l == lang:
                    lx.user[word] = Entry(word, "n", w.get("ss") or "artifact", frozenset(w["cats"]), frozenset())

    def _add(self, op: dict) -> dict:
        self.seq += 1
        op = {**op, "n": self.seq}
        self.ops.append(op)
        if len(self.ops) > MAX_OPS:
            drop = next((i for i, o in enumerate(self.ops) if o["op"] == "reward"), 0)
            self.ops.pop(drop)
        self._fold()
        self.save()
        return op

    # -- learning steps -----------------------------------------------------------------------------------------
    def correct(self, feats: list[str], scores: dict[str, float], good: str, bad: str, text: str = "") -> dict | None:
        """Move the message's own features so that ``good`` beats ``bad`` (and every other kind) by LEARN_RATE."""
        use = sorted({f for f in feats if f.startswith(_LEARNABLE)})
        if not use or good == bad:
            return None
        top = max((v for k, v in scores.items() if k != good), default=0.0)
        need = max(0.0, top - scores.get(good, 0.0)) + LEARN_RATE
        step = min(MAX_STEP, need / len(use))
        delta = {f: {good: round(step, 6)} for f in use}
        if bad and bad != "NONE":
            for f in use:
                delta[f][bad] = round(-step / 2, 6)
        op = {"op": "correct", "good": good, "bad": bad, "delta": delta}
        if text:
            op["text"] = text[:300]         # the sentence itself: the same message is never read wrong again
        return self._add(op)

    def teach_word(self, word: str, lang: str, cats: list[str], ss: str = "") -> dict:
        return self._add({"op": "word", "word": word.lower(), "lang": lang, "cats": sorted(cats), "ss": ss})

    def set_style(self, key: str, value: str) -> dict:
        return self._add({"op": "style", "key": key, "value": value})

    def episode(self, date: str, kind: str, obj: str, text: str, lang: str) -> dict:
        return self._add({"op": "episode", "date": date, "kind": kind, "obj": obj, "text": text[:200], "lang": lang})

    def reward(self, arm: str, r: bool) -> None:
        self._add({"op": "reward", "arm": arm, "r": bool(r)})

    # -- forgetting ---------------------------------------------------------------------------------------------
    def last(self, kinds=("correct", "word", "style", "episode")) -> dict | None:
        return next((o for o in reversed(self.ops) if o["op"] in kinds), None)

    def forget(self, n: int) -> bool:
        """Remove step ``n``; the state is then exactly as if it had never been learned."""
        keep = [o for o in self.ops if o["n"] != n]
        if len(keep) == len(self.ops):
            return False
        self.ops = keep
        if n == self.seq:
            self.seq = n - 1                 # the last step: the counter goes back too (bit-identical file)
        self._fold()
        self.save()
        return True

    def reset(self) -> None:
        self.ops, self.seq = [], 0
        self._fold()
        if self.path and self.path.exists():
            self.path.unlink()
