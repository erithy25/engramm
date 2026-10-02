"""The conversation bank: small talk, persona, feelings, safety, jokes and reply sentences.

Authored as YAML in ``data/conv/`` and compiled by ``python -m engramm.chat.studio build`` into
``engramm/chat/conv_bank.json`` (shipped with the package; the runtime needs no YAML reader).

Choosing a reply is deterministic: the variant for the n-th use of a reply list in a
conversation comes from SHAKE-256 of (conversation, list, n), skipping variants used in the
last turns, so the same conversation always gets the same replies and a reply does not repeat
right away.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

BANK_PATH = Path(__file__).resolve().parent / "conv_bank.json"

_APOS = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'", "“": '"', "”": '"'})
# chat spelling → the spelling the patterns expect (matching only; the message itself is kept)
_SLANG = {"u": "you", "r": "are", "ur": "your", "pls": "please", "plz": "please", "thx": "thanks",
          "im": "i'm", "ive": "i've", "youre": "you're", "dont": "don't", "cant": "can't", "wont": "won't",
          "didnt": "didn't", "doesnt": "doesn't", "isnt": "isn't", "wasnt": "wasn't", "whats": "what's",
          "hows": "how's", "wheres": "where's", "whos": "who's", "thats": "that's", "theres": "there's",
          "lets": "let's", "gonna": "going to", "wanna": "want to", "gotta": "got to", "idk": "i don't know",
          "rn": "right now", "abt": "about", "cuz": "because", "coz": "because", "tho": "though",
          "fav": "favourite", "fave": "favourite", "favorite": "favourite", "color": "colour", "colors": "colours",
          "b4": "before", "2day": "today", "gtg": "got to go", "g2g": "got to go", "gr8": "great", "ok.": "ok", "k.": "k"}
# chat spelling expanded in the message itself (English), so that understanding, lookup and memory
# all see "what's your name" for "wats ur name" — whole words only, case kept for everything else
_CHAT_WORDS = {"hav": "have", "tomoro": "tomorrow", "tomorow": "tomorrow", "tonite": "tonight", "thru": "through",
               "probs": "probably", "whatcha": "what are you", "watcha": "what are you", "wyd": "what are you doing", "u": "you", "r": "are", "ur": "your", "wat": "what", "wut": "what", "wht": "what", "wats": "what's",
               "whats": "what's", "whos": "who's", "hows": "how's", "wheres": "where's", "thats": "that's",
               "abt": "about", "thx": "thanks", "thnx": "thanks", "tnx": "thanks", "ty": "thank you",
               "tysm": "thank you so much", "np": "no problem", "pls": "please", "plz": "please", "gf": "girlfriend",
               "bf": "boyfriend", "bday": "birthday", "smth": "something", "sth": "something", "nvm": "never mind",
               "ppl": "people", "tmrw": "tomorrow", "tmr": "tomorrow", "2moro": "tomorrow", "2day": "today",
               "l8r": "later", "b4": "before", "bc": "because", "cuz": "because", "coz": "because", "rly": "really",
               "srsly": "seriously", "prolly": "probably", "dunno": "don't know", "lemme": "let me", "gimme": "give me",
               "hru": "how are you", "wyd": "what are you doing", "hbu": "how about you", "wbu": "how about you",
               "im": "I'm", "ive": "I've", "youre": "you're", "dont": "don't", "cant": "can't", "wont": "won't",
               "didnt": "didn't", "doesnt": "doesn't", "isnt": "isn't", "wasnt": "wasn't", "arent": "aren't",
               "kk": "ok", "rn": "right now", "w/": "with", "w/o": "without", "gr8": "great", "fav": "favourite",
               "fave": "favourite", "cud": "could", "shud": "should", "wud": "would", "yr": "your", "luv": "love",
               # typos that are frequent enough in the corpus that the speller keeps them
               "wrld": "world", "wolrd": "world", "teh": "the", "hte": "the", "waht": "what", "whta": "what",
               "wich": "which", "wen": "when", "wher": "where", "becuase": "because", "beacuse": "because",
               "becasue": "because", "definately": "definitely", "alot": "a lot", "thier": "their",
               "freind": "friend", "freinds": "friends", "tomorow": "tomorrow", "tommorow": "tomorrow",
               "peple": "people", "pepole": "people", "knwo": "know", "konw": "know", "wnat": "want",
               "plaese": "please", "coudl": "could", "shoudl": "should", "wierd": "weird", "untill": "until",
               "captial": "capital", "contry": "country", "countrey": "country", "goverment": "government",
               "tallets": "tallest", "bigest": "biggest", "longst": "longest",
               "shes": "she's", "hes": "he's", "theyre": "they're", "theres": "there's", "lets": "let's",
               # spoken spellings: "how r u doin", "im gud thx", "helo", "gd mornin"
               "doin": "doing", "goin": "going", "nothin": "nothing", "somethin": "something", "mornin": "morning",
               "evenin": "evening", "gud": "good", "gd": "good", "helo": "hello", "hellooo": "hello", "hii": "hi",
               "hiii": "hi", "heyy": "hey", "heyyy": "hey", "heya": "hey", "hiya": "hi", "thanx": "thanks",
               "thankss": "thanks", "nite": "night", "gnite": "good night", "gn": "good night", "gm": "good morning",
               "yall": "you all", "kinda": "kind of", "sorta": "sort of", "gotta": "got to",
               "wanna": "want to", "gonna": "going to", "tryna": "trying to", "idc": "I don't care", "ikr": "I know right",
               "ofc": "of course", "omw": "on my way", "asap": "as soon as possible", "bout": "about", "cya": "see you",
               "imo": "in my opinion", "tbf": "to be fair", "fr": "for real", "ngl": "not gonna lie"}
_YOURE_NEXT = re.compile(r"(?:the|so|very|really|too|such|amazing|awesome|great|welcome|funny|smart|right|wrong|"
                         r"kidding|joking|not|a|an|cute|sweet|nice|kind|weird|crazy|stupid|dumb|wild|lying|actually|"
                         r"just|literally|always|never|going|getting|being|doing|making|my)\b")
_CHAT_TAIL = re.compile(r"(?:[\s,]+(?:btw|tbh|lol|lmao|haha+|hehe+|xd|imo|ngl|fr|lowkey))+(?=[\s.!?]*$)", re.I)


def expand_chat(text: str) -> str:
    """"wats ur name" → "what's your name", "u r smart" → "you are smart", "ur funny" → "you're funny",
    "i'm 25 btw" → "i'm 25" (a trailing "btw/lol/tbh" carries no content)."""
    toks = re.split(r"(\s+)", text)
    words = [t for t in toks if t.strip()]
    out = []
    k = -1
    for t in toks:
        if not t.strip():
            out.append(t)
            continue
        k += 1
        nxt = words[k + 1] if k + 1 < len(words) else ""
        m = re.fullmatch(r"([\"'(]*)([A-Za-z0-9/]+)([.,!?;:)\"']*)", t)
        w = m.group(2) if m else ""
        if m and w.lower() in _CHAT_WORDS and not (w.isupper() and len(w) > 1) \
                and not (w[:1].isupper() and len(w) == 1 and nxt[:1].isupper()):     # "U Thant" is a name
            low = w.lower()
            rep = _CHAT_WORDS[low]
            if low == "ur" and (k == 0 and len(words) > 1 or _YOURE_NEXT.match(nxt.lower())):
                rep = "you're"                                # "ur funny", "thank u ur the best"
            out.append(m.group(1) + rep + m.group(3))
        else:
            out.append(t)
    s = "".join(out)
    if len(words) >= 3:
        s = _CHAT_TAIL.sub("", s)
    return s


_ADDRESS = re.compile(r"(^|[\s,])(engramm|bot|buddy)([\s,!.?]|$)", re.I)
_FILLER = re.compile(r"^(?:(?:um+|uh+|er+|erm|well|so|oh|ah|hmm+|hey|ok|okay|alright|and|but|also|now|then|"
                     r"please|pls|plz|lo+l+|ha(?:ha)+h?|he(?:he)+|lmao+|omg|wow|aw+|haha+)\s*[,.!]?\s+)+(?=\S)")
_END = re.compile(r"[\s.!?…,;:]+$")


def normalise(text: str, fillers: bool = True) -> str:
    """Lower case, straight apostrophes, no form of address ("engramm"), no end punctuation,
    chat spelling expanded and (``fillers``) no leading "well, so, ok, please …". Patterns in the
    bank match this form (the router tries it with and without the fillers)."""
    s = text.translate(_APOS).strip().lower()
    s = _ADDRESS.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,")
    s = _END.sub("", s)
    words = [_SLANG.get(w, w) for w in s.split(" ")]
    s = " ".join(words)
    if fillers and len(words) > 1:
        s = _FILLER.sub("", s)
    return s.strip(" ,")


@dataclass
class Intent:
    id: str
    patterns: list[re.Pattern]
    examples: list[str]
    responses: list[str]
    responses_named: list[str] = field(default_factory=list)
    action: str | None = None
    follow: str | None = None

    def match(self, s: str) -> re.Match | None:
        for rx in self.patterns:
            m = rx.fullmatch(s)
            if m:
                return m
        return None


@dataclass
class Category:
    id: str
    valence: str
    triggers: list[re.Pattern]
    responses: list[str]


@dataclass
class SafetyRule:
    id: str
    kind: str                 # crisis | refuse
    triggers: list[re.Pattern]
    response: str


class Bank:
    def __init__(self, data: dict):
        self.data = data
        self.intents = [Intent(i["id"], [re.compile(p) for p in i.get("patterns", [])], i.get("examples", []),
                               i.get("responses", []), i.get("responses_named", []), i.get("action"),
                               i.get("follow")) for i in data["smalltalk"]["intents"]]
        self.by_id = {i.id: i for i in self.intents}
        emp = data["empathy"]
        self.negators = emp.get("negators", [])
        self.categories = [Category(c["id"], c["valence"], [re.compile(t) for t in c["triggers"]], c["responses"])
                           for c in emp["categories"]]
        self.negated_negative = emp.get("negated_negative", {}).get("responses", [])
        saf = data["safety"]
        self.safety = ([SafetyRule(r["id"], "crisis", [re.compile(t) for t in r["triggers"]], r["response"])
                        for r in saf.get("crisis", [])]
                       + [SafetyRule(r["id"], "refuse", [re.compile(t) for t in r["triggers"]], r["response"])
                          for r in saf.get("refuse", [])])
        self.fun = data["fun"]
        self.replies = data["replies"]
        self.writing = data.get("writing", {"purposes": {"generic": {}}, "greetings": {}, "closings": {},
                                            "poems": []})
        self.de = data.get("de")                 # German v0 (engramm/chat/german.py)
        self.daily = data.get("daily") or {}     # everyday conversation (engramm/chat/everyday.py)
        self._grams = [(it.id, ex, _grams(ex)) for it in self.intents for ex in it.examples]

    # -- matching ----------------------------------------------------------------------------

    def intent(self, *forms: str) -> tuple[Intent, re.Match] | None:
        """The first intent whose pattern matches one of the normalised forms of a sentence."""
        for it in self.intents:
            for s in dict.fromkeys(forms):
                m = it.match(s)
                if m:
                    return it, m
        return None

    def nearest(self, s: str) -> tuple[Intent, float] | None:
        """The intent of the most similar example (letter trigrams and words, Jaccard), for
        short messages that no pattern matched."""
        g = _grams(s)
        if not g:
            return None
        best, best_id = 0.0, None
        for iid, _, eg in self._grams:
            inter = len(g & eg)
            if not inter:
                continue
            j = inter / len(g | eg)
            if j > best:
                best, best_id = j, iid
        return (self.by_id[best_id], best) if best_id else None

    def safety_rule(self, s: str) -> SafetyRule | None:
        for r in self.safety:
            if any(t.search(s) for t in r.triggers):
                return r
        return None

    def feeling(self, s: str) -> tuple[Category, bool] | None:
        """The first feeling category whose trigger occurs in the sentence, and whether a
        negation stands right before it ("not happy")."""
        for c in self.categories:
            for t in c.triggers:
                m = t.search(s)
                if m:
                    before = s[:m.start()].rstrip().split(" ")[-3:]
                    neg = any(" ".join(before[i:]) in self.negators for i in range(len(before)))
                    return c, neg
        return None

    # -- choosing ----------------------------------------------------------------------------

    def reply(self, path: str) -> list[str]:
        """The reply list at a dotted path of replies.yaml ("learned.home")."""
        node = self.replies
        for part in path.split("."):
            node = node[part]
        return node if isinstance(node, list) else [node]


def _grams(s: str) -> frozenset:
    s = f" {s} "
    tri = {s[i:i + 3] for i in range(len(s) - 2)}
    ws = s.split()
    return frozenset(tri | {"w:" + w for w in ws} | {f"b:{a} {b}" for a, b in zip(ws, ws[1:])})


def choose(options: list[str], key: str, recent: list[str], salt: str = "") -> str:
    """A deterministic variant: SHAKE-256 of the key orders the options; the first one not
    among the recent replies wins (if all were used recently, the first in that order)."""
    if not options:
        return ""
    if len(options) == 1:
        return options[0]
    order = sorted(range(len(options)),
                   key=lambda i: hashlib.shake_256(f"{key}\x00{salt}\x00{i}".encode()).digest(8))
    for i in order:
        if options[i] not in recent:
            return options[i]
    # all used recently: the one used longest ago
    last_use = {opt: k for k, opt in enumerate(recent)}
    return options[min(order, key=lambda i: last_use.get(options[i], -1))]


@lru_cache(maxsize=4)
def load_bank(path: str = str(BANK_PATH)) -> Bank:
    return Bank(json.loads(Path(path).read_text(encoding="utf-8")))
