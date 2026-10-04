"""Practical advice found in Wikipedia (U3): the how-to index built by experiments/howto_build.py.

Looked up by name only — an article answers when its title or one of its other names ("Urticaria, also known as
hives") is said in the conversation. Health advice always comes with its source and the line to see a doctor; there
is no answer from a guess. Text: Wikipedia, CC BY-SA 4.0 (the article title is shown as the source).
"""
from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "howto.json.gz"

# what a situation's sub-kind is called in the encyclopaedia (the words people use are rarely article titles)
SUB_NAMES = {"sting": ["bee sting", "insect bites and stings", "insect sting"], "burn": ["burn"],
             "cut": ["wound", "laceration"], "bite": ["dog bite", "animal bite"], "head": ["head injury", "concussion"],
             "sprain": ["sprained ankle", "sprain"]}
_DROP = {"my", "your", "his", "her", "their", "our", "a", "an", "the", "i", "have", "has", "got", "get", "think", "some",
         "really", "bad", "badly", "pretty", "very", "so", "this", "that", "of", "and", "keep", "keeps", "having"}
_PLURAL = re.compile(r"(?<=[a-z]{3})s$")


@dataclass
class Advice:
    title: str
    kind: str
    sentences: list[str]


class HowTo:
    def __init__(self, path: Path = DATA):
        self.names: dict[str, int] = {}
        self.items: list[Advice] = []
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                d = json.load(fh)
            self.items = [Advice(t, k, s) for t, k, s in d["items"]]
            self.names = d["names"]

    def __bool__(self) -> bool:
        return bool(self.items)

    def find(self, text: str, extra: list[str] | None = None) -> Advice | None:
        """The article a message names (longest name first), or None."""
        if not self.items:
            return None
        words = [w for w in re.findall(r"[a-z][a-z'-]*", text.lower()) if w not in _DROP]
        cands = list(extra or [])
        for n in (3, 2, 1):
            for i in range(len(words) - n + 1):
                g = " ".join(words[i:i + n])
                cands += [g, _PLURAL.sub("", g)]
        for c in cands:
            if len(c) > 3 and c in self.names:
                return self.items[self.names[c]]
        return None


_HT: HowTo | None = None


def howto() -> HowTo:
    global _HT
    if _HT is None:
        _HT = HowTo()
    return _HT


def render(a: Advice, lang: str = "en", n: int = 2) -> str:
    """Two sentences with their source, and for health the doctor line (the safety tier: never without both)."""
    body = " ".join(a.sentences[:n])
    src = f"(Wikipedia, “{a.title}”)"
    warn = " If it gets worse or you're unsure, please see a doctor or pharmacist." if a.kind == "HEALTH" else ""
    return f"From the encyclopedia: {body} {src}{warn}"


def save(items: list[tuple[str, str, list[str], list[str]]], path: Path = DATA) -> None:
    """items: (title, kind, names, sentences)."""
    names: dict[str, int] = {}
    out = []
    for i, (t, k, ns, ss) in enumerate(items):
        out.append([t, k, ss])
        for n in ns:
            names.setdefault(n, i)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump({"items": out, "names": names}, fh, ensure_ascii=False, separators=(",", ":"))
