"""German conversation, v0 (Chat v3, phase 9).

ENGRAMM's reading and fact bank are English, so in German it chats, listens, remembers and
answers crises, and says honestly that knowledge questions work in English for now. The texts
are in ``data/conv/de.yaml`` (compiled into the conversation bank under ``de``).

* ``is_german``: counts German and English function words; German needs at least one clearly German
  word (not "was", "die", "also" …) and more German than English hits;
* ``understand``: safety first, then memory statements ("Ich heiße Anna" → "My name is Anna."
  for the shared memory), questions about the user's name, small talk, feelings, arithmetic;
* everything else gets the honest fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_WORD = re.compile(r"[a-zäöüß]+")
_END = re.compile(r"[\s.!?…,;:]+$")


def normalise_de(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[’‘`´']", " ", s)
    s = re.sub(r"(^|[\s,])(engramm|bot)([\s,!.?]|$)", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,")
    return _END.sub("", s).strip(" ,")


def is_german(text: str, spec: dict) -> bool:
    words = _WORD.findall(text.lower())
    if not words:
        return False
    de, en = set(spec["detect"]["german"]), set(spec["detect"]["english"])
    ambiguous = set(spec["detect"].get("ambiguous", []))
    strict = sum(w in de and w not in ambiguous for w in words)
    if strict == 0 and not re.search(r"[äöüß]", text.lower()):
        return False                      # "When was he born?": no clearly German word
    n_de = sum(w in de for w in words)
    n_en = sum(w in en and w not in de for w in words)
    return n_de > n_en or (n_de == n_en and bool(re.search(r"[äöüß]", text.lower())))


# memory statements → the English sentence the shared memory understands
_STATEMENTS = [
    (re.compile(r"^(?:ich heiße|ich heisse|mein name ist|man nennt mich|nenn mich) ([a-zäöüß][\w\-äöüß]*(?: [a-zäöüß][\w\-äöüß]*)?)$"),
     "name", "My name is {0}."),
    (re.compile(r"^ich wohne in ([\w\-äöüß ]{2,40})$"), "fact", "I live in {0}."),
    (re.compile(r"^ich lebe in ([\w\-äöüß ]{2,40})$"), "fact", "I live in {0}."),
    (re.compile(r"^ich komme aus ([\w\-äöüß ]{2,40})$"), "fact", "I am from {0}."),
    (re.compile(r"^ich bin (\d{1,3}) jahre alt$"), "fact", "I am {0} years old."),
    (re.compile(r"^ich arbeite als ([\w\-äöüß ]{2,40})$"), "fact", "I work as {0}."),
    (re.compile(r"^mein lieblingsessen ist ([\w\-äöüß ]{2,40})$"), "fact", "My favourite food is {0}."),
    (re.compile(r"^meine lieblingsfarbe ist ([\w\-äöüß ]{2,40})$"), "fact", "My favourite colour is {0}."),
]
_ASK_NAME = re.compile(r"^(wie heiße ich|wie heisse ich|weißt du (noch )?(wie ich heiße|meinen namen)|"
                       r"kennst du meinen namen|wer bin ich|was ist mein name)$")
_CALC = re.compile(r"^(?:was (?:ist|ergibt|sind)|wie ?viel (?:ist|sind|ergibt)|rechne|berechne)\s+(.+)$")
_DE_OPS = [(r"\bmal\b", "*"), (r"\bplus\b", "+"), (r"\bminus\b", "-"), (r"\bgeteilt durch\b", "/"),
           (r"\bdurch\b", "/"), (r"(\d),(\d)", r"\1.\2")]


def _title(words: str) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in words.split())


@dataclass
class Understood:
    kind: str                          # safety | remember | ask_name | intent | feeling | calc | fallback
    data: dict = field(default_factory=dict)


def understand(text: str, spec: dict) -> Understood:
    s = normalise_de(text)
    for kind in ("crisis", "refuse"):
        for r in spec["safety"].get(kind, []):
            if any(re.search(t, s) for t in r["triggers"]):
                return Understood("safety", {"rule": r["id"], "response": r["response"]})
    for rx, what, english in _STATEMENTS:
        m = rx.match(s)
        if m:
            value = _title(m.group(1)) if what in ("name", "fact") and not m.group(1).isdigit() else m.group(1)
            return Understood("remember", {"what": what, "value": value, "english": english.format(value)})
    if _ASK_NAME.match(s):
        return Understood("ask_name")
    m = _CALC.match(s)
    if m:
        expr = m.group(1)
        for pat, rep in _DE_OPS:
            expr = re.sub(pat, rep, expr)
        if re.fullmatch(r"[\d\s.+\-*/()^%]+", expr) and re.search(r"\d", expr):
            return Understood("calc", {"expr": expr.strip()})
    for it in spec["intents"]:
        for p in it["patterns"]:
            if re.fullmatch(p, s):
                return Understood("intent", {"id": it["id"]})
    fe = spec["feelings"]
    for c in fe["categories"]:
        for t in c["triggers"]:
            m = re.search(t, s)
            if m:
                before = s[:m.start()].rstrip().split(" ")[-3:]
                neg = any(" ".join(before[i:]) in fe["negators"] for i in range(len(before)))
                return Understood("feeling", {"id": c["id"], "valence": c["valence"], "negated": neg})
    return Understood("fallback")
