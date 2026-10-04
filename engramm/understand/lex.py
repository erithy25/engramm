"""The situation lexicon at run time: word → lemma → (word class, general categories, situation evidence).

Built by experiments/lex_build.py from Open English WordNet, OdeNet and FrameNet (docs/DATA_LICENSES.md);
German inflected forms come from Wiktionary (via kaikki.org, CC BY-SA). The files are small (< 1 MB) and ship with
the program, so the chat understands situations without a knowledge pack.

Lemmatising is by lookup first (irregular forms), then by general suffix rules checked against the lexicon — no
list of conversation topics.
"""
from __future__ import annotations

import gzip
import re
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class Entry:
    lemma: str
    pos: str                     # n / v / a
    ss: str                      # supersense: artifact, body, animal, person, state, change, contact …
    cats: frozenset = field(default_factory=frozenset)
    ev: frozenset = field(default_factory=frozenset)
    gender: str = ""             # German nouns: m / f / n


class Lexicon:
    def __init__(self, lang: str):
        self.lang = lang
        self.entries: dict[str, dict[str, Entry]] = {}
        self.forms: dict[str, list[tuple[str, str]]] = {}
        self._cache: dict[str, tuple] = {}
        self.user: dict[str, Entry] = {}       # words this user taught (engramm/learn), first in every lookup
        lex = DATA / f"lex_{lang}.tsv.gz"
        if lex.exists():
            with gzip.open(lex, "rt", encoding="utf-8") as f:
                for line in f:
                    lemma, pos, ss, cats, ev, gender = (line.rstrip("\n").split("\t") + ["", "", "", ""])[:6]
                    self.entries.setdefault(lemma, {})[pos] = Entry(
                        lemma, pos, ss, frozenset(c for c in cats.split(",") if c), frozenset(e for e in ev.split(",") if e),
                        gender)
        forms = DATA / f"forms_{lang}.tsv.gz"
        if forms.exists():
            with gzip.open(forms, "rt", encoding="utf-8") as f:
                for line in f:
                    form, rest = line.rstrip("\n").split("\t", 1)
                    if lang == "en":
                        self.forms[form] = [(rest, "")]
                    else:
                        self.forms[form] = [tuple(x.split(":", 1)) for x in rest.split()]

    def __bool__(self) -> bool:
        return bool(self.entries)

    def get(self, lemma: str, pos: str | None = None) -> Entry | None:
        d = self.entries.get(lemma)
        if not d:
            return None
        if pos:
            return d.get(pos)
        return d.get("n") or d.get("v") or d.get("a")

    def lookup(self, word: str) -> list[Entry]:
        """All readings of a surface word, most likely first (exact lemma, irregular form, suffix rules)."""
        w = word.lower()
        if w in self.user:
            return [self.user[w]] + [e for e in self.lookup_base(w) if e.pos != self.user[w].pos]
        return self.lookup_base(w)

    def lookup_base(self, w: str) -> list[Entry]:
        hit = self._cache.get(w)
        if hit is None:
            hit = self._cache[w] = tuple(_readings(self, w))
            if len(self._cache) > 200_000:
                self._cache.clear()
        return list(hit)


def _readings(lx: Lexicon, w: str):
    out: list[Entry] = []
    seen = set()

    def add(lemma: str, pos: str | None = None):
        d = lx.entries.get(lemma)
        if not d:
            return
        for p in ([pos] if pos else ("v", "n", "a")):
            e = d.get(p)
            if e and (e.lemma, e.pos) not in seen:
                seen.add((e.lemma, e.pos))
                out.append(e)

    if lx.lang == "en":
        for lemma, _ in lx.forms.get(w, []):
            add(lemma)
        add(w)
        for cand, pos in _en_candidates(w):
            add(cand, pos)
    else:
        add(w)
        for lemma, pos in lx.forms.get(w, []):
            add(lemma, pos)
        for cand, pos in _de_candidates(w):
            add(cand, pos)
        if not out and len(w) >= 7:
            head = _de_head(lx, w)
            if head:
                add(head)
    return out


def _en_candidates(w: str):
    if w.endswith("ies") and len(w) > 4:
        yield w[:-3] + "y", None
    if w.endswith("ied") and len(w) > 4:
        yield w[:-3] + "y", "v"
    if w.endswith("ves") and len(w) > 4:
        yield w[:-3] + "f", "n"
        yield w[:-3] + "fe", "n"
    if w.endswith("es") and len(w) > 3:
        yield w[:-2], None
    if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        yield w[:-1], None
    if w.endswith("ed") and len(w) > 3:
        yield w[:-2], "v"
        yield w[:-1], "v"
        if len(w) > 4 and w[-3] == w[-4]:
            yield w[:-3], "v"                       # stopped → stop
    if w.endswith("ing") and len(w) > 4:
        yield w[:-3], "v"
        yield w[:-3] + "e", "v"
        if len(w) > 5 and w[-4] == w[-5]:
            yield w[:-4], "v"                       # running → run
    if w.endswith("er") and len(w) > 4:
        yield w[:-2], "a"
    if w.endswith("est") and len(w) > 5:
        yield w[:-3], "a"
    if w.endswith("n't"):
        yield w[:-3], "v"


_DE_PREFIXES = ("ab", "an", "auf", "aus", "bei", "ein", "mit", "nach", "vor", "weg", "zu", "zurück", "los", "hin",
                "her", "um", "durch", "über", "unter", "kaputt", "fest", "frei", "hoch", "runter", "rein", "raus")


def _de_candidates(w: str):
    # participles: ge…t / ge…en, with a separable prefix in front (aufgeschürft → aufschürfen)
    m = re.fullmatch(r"(" + "|".join(_DE_PREFIXES) + r")?ge([a-zäöüß]{2,}?)(t|et|en)", w)
    if m:
        pre, stem, end = m.group(1) or "", m.group(2), m.group(3)
        yield pre + stem + "en", "v"
        yield pre + stem + "n", "v"
    if re.fullmatch(r"(?:ver|be|er|zer|ent|emp|miss)[a-zäöüß]{2,}(?:t|et)", w):
        yield re.sub(r"e?t$", "en", w), "v"          # verschüttet → verschütten
    for suf, rep in (("st", "en"), ("t", "en"), ("e", "en"), ("te", "en"), ("ten", "en"), ("test", "en"),
                     ("et", "en")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            yield w[: -len(suf)] + rep, "v"
    for suf in ("en", "n", "e", "er", "es", "s", "nen"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            yield w[: -len(suf)], None
    for suf in ("er", "e", "en", "em", "es"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            yield w[: -len(suf)], "a"


def _de_head(lx: Lexicon, w: str) -> str | None:
    """The head of a German compound: the longest known noun at the end (Nebenkostennachzahlung → nachzahlung)."""
    for i in range(2, len(w) - 3):
        tail = w[i:]
        if tail in lx.entries and "n" in lx.entries[tail]:
            front = w[:i]
            if front in lx.entries or front.rstrip("s") in lx.entries or front[:-1] in lx.entries or \
                    front[:-2] in lx.entries or len(front) >= 3:
                return tail
    return None


_LEX: dict[str, Lexicon] = {}


def lexicon(lang: str) -> Lexicon:
    if lang not in _LEX:
        _LEX[lang] = Lexicon(lang)
    return _LEX[lang]


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-zäöüß]+(?:'[a-z]+)?|\d+(?:[.,]\d+)?", text.lower().replace("’", "'"))
