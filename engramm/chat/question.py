"""Question analysis and answer-candidate spans — hand-written rules, no trained tagger.

* ``analyse(question)`` → the expected answer type (PERSON, DATE, NUMBER, LOCATION,
  PROPER, OTHER), the wh-phrase and the content words.
* ``spans(sentence, ...)`` → typed candidate answer spans of a sentence: dates and
  years, numbers and quantities, and runs of capitalised words (names).

Capitalisation of a sentence-initial word is resolved with counts from the corpus
(``CapStats``): a word counts as a name only if the corpus writes it capitalised in
the middle of sentences more often than not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

PERSON, DATE, NUMBER, LOCATION, PROPER, OTHER = "PERSON", "DATE", "NUMBER", "LOCATION", "PROPER", "OTHER"

MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")
MONTH_ABBR = ("jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec")
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
                "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
                "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
                "thousand", "million", "billion", "trillion", "dozen", "half", "first", "second", "third")
ORDINAL_WORDS = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth")

DATE_NOUNS = ("year", "years", "date", "day", "month", "century", "decade", "time", "period", "era", "season")
NUMBER_HEADS = ("many", "much", "long", "old", "far", "tall", "big", "large", "high", "deep", "wide", "heavy",
                "fast", "often", "hot", "cold", "warm", "expensive", "large")
NUMBER_NOUNS = ("number", "percentage", "percent", "amount", "proportion", "fraction", "population", "size", "age",
                "total", "count", "rate", "distance", "length", "height", "weight", "cost", "price", "score",
                "temperature", "speed", "capacity", "sum")
LOCATION_NOUNS = ("city", "country", "state", "place", "region", "continent", "island", "islands", "river",
                  "county", "town", "nation", "location", "area", "province", "street", "mountain", "lake", "sea",
                  "ocean", "village", "capital", "territory", "district", "neighborhood", "neighbourhood", "port",
                  "valley", "desert", "planet", "states", "countries", "cities", "venue", "stadium", "airport",
                  "university", "school", "building", "church", "museum", "park", "borough", "municipality",
                  "peninsula", "kingdom", "empire", "republic", "colony", "site", "coast", "bay", "hemisphere")
PERSON_NOUNS = ("person", "man", "woman", "king", "queen", "president", "author", "writer", "artist", "player",
                "leader", "emperor", "pope", "prince", "princess", "poet", "composer", "scientist", "singer",
                "actor", "actress", "director", "founder", "inventor", "architect", "explorer", "general",
                "minister", "chancellor", "senator", "governor", "philosopher", "painter", "sculptor", "captain",
                "coach", "manager", "owner", "ruler", "people", "individual", "wife", "husband", "son",
                "daughter", "father", "mother", "brother", "sister", "saint", "god", "goddess", "character",
                "musician", "novelist", "designer", "engineer", "physicist", "chemist", "mathematician",
                "politician", "candidate", "winner", "champion", "judge", "lawyer", "bishop", "archbishop",
                "commander", "officer", "doctor", "teacher", "student", "ceo", "chairman", "host", "rapper",
                "drummer", "guitarist", "band", "team", "company", "organization", "organisation", "group",
                "party", "club", "network", "channel", "label", "publisher", "newspaper", "magazine", "brand",
                "firm", "corporation", "agency", "army", "navy", "tribe", "dynasty")
STOP = frozenset((
    "a an the of in on at to for from by with about as into like through after over between out against during "
    "without before under around among is are was were be been being am do does did doing have has had having "
    "what which who whom whose when where why how that this these those it its it's they them their there here "
    "and or but if then than so not no nor can could should would will shall may might must also just only very "
    "i me my we our you your he him his she her one ones s t 's ’s any some such each other more most many much "
    "de la le du von van der da di name named called call known"
).split())
CONNECT = frozenset(("of", "de", "du", "la", "le", "van", "von", "der", "da", "di", "del", "the", "&", "y",
                     "bin", "al", "el"))

_WORD_RE = re.compile(r"[0-9]+(?:[.,][0-9]+)*(?:st|nd|rd|th|s)?(?![A-Za-z])|"
                      r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:[-'’.][A-Za-zÀ-ÖØ-öø-ÿ0-9]+)*|[^\sA-Za-zÀ-ÖØ-öø-ÿ0-9]")
NON_UNITS = frozenset(("since", "until", "till", "more", "less", "fewer", "than", "before", "after", "later",
                       "earlier", "each", "every", "per", "or", "nor", "yet", "while", "because", "although",
                       "though", "whereas", "including", "compared", "versus", "vs"))
_YEAR = re.compile(r"^(1[0-9]{3}|20[0-9]{2})s?$")
_NUM = re.compile(r"^[0-9]+(?:[.,][0-9]+)*$")


@dataclass
class Question:
    text: str
    wh: str
    atype: str
    words: list[str]                    # lower-case words
    content: list[str]                  # lower-case content words (not stop words)
    head: str = ""                      # the noun after what/which, if any


def words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def analyse(question: str) -> Question:
    q = " ".join(question.strip().split())
    ws = [w.lower() for w in words(q)]
    alpha = [w for w in ws if w[0].isalnum()]
    content = [w for w in alpha if w not in STOP]
    wh, atype, head = "", OTHER, ""
    for i, w in enumerate(alpha):
        nxt = alpha[i + 1] if i + 1 < len(alpha) else ""
        nxt2 = alpha[i + 2] if i + 2 < len(alpha) else ""
        if w == "how" and nxt in NUMBER_HEADS:
            wh, atype = f"how {nxt}", NUMBER if nxt != "often" else OTHER
            break
        if w == "how":
            wh = "how"
            break
        if w in ("when",):
            wh, atype = w, DATE
            break
        if w == "where":
            wh, atype = w, LOCATION
            break
        if w in ("who", "whom", "whose"):
            wh, atype = w, PERSON
            break
        if w in ("what", "which"):
            wh = w
            h = nxt
            if h in ("kind", "type", "sort", "form") and nxt2 == "of":
                h = alpha[i + 3] if i + 3 < len(alpha) else ""
            head = h
            if h in DATE_NOUNS:
                atype = DATE
            elif h in NUMBER_NOUNS:
                atype = NUMBER
            elif h in LOCATION_NOUNS:
                atype = LOCATION
            elif h in PERSON_NOUNS:
                atype = PERSON
            elif h in ("is", "was", "are", "were") and nxt2 in ("the", "a", "an"):
                # "what is the name of …" / "what was the population …"
                n3 = alpha[i + 3] if i + 3 < len(alpha) else ""
                head = n3
                atype = (DATE if n3 in DATE_NOUNS else NUMBER if n3 in NUMBER_NOUNS else
                         LOCATION if n3 in LOCATION_NOUNS else PERSON if n3 in PERSON_NOUNS else
                         PROPER if n3 == "name" else OTHER)
            break
        if w == "why":
            wh = w
            break
    if not wh and alpha and alpha[0] in ("in", "on", "during", "at", "since", "until", "by") and "year" in alpha:
        wh, atype = "in what year", DATE
    if wh.startswith("how") and atype == OTHER and ("year" in alpha or "date" in alpha):
        atype = DATE
    # "…called?" / "name of" questions about things want a name
    if atype == OTHER and ("called" in alpha or "named" in alpha or ("name" in alpha and wh in ("what", "which"))):
        atype = PROPER
    return Question(q, wh, atype, ws, content, head)


# ---------------------------------------------------------------------------
# capitalisation statistics from the corpus
# ---------------------------------------------------------------------------

@dataclass
class CapStats:
    """P(capitalised | word) for word-initial tokens, counted in the train stream."""
    ratio: dict = field(default_factory=dict)

    @classmethod
    def build(cls, tokens: np.ndarray, tok) -> CapStats:
        counts = np.bincount(np.asarray(tokens), minlength=tok.vocab_size)
        texts = [p.decode("utf-8", errors="replace") for p in tok.token_bytes()]
        low = {}
        for i, t in enumerate(texts):
            if t.startswith(" ") and len(t) > 1 and t[1].isalpha() and t[1].islower():
                low[t[1:]] = int(counts[i])
        ratio = {}
        for i, t in enumerate(texts):
            if t.startswith(" ") and len(t) > 1 and t[1].isalpha() and t[1].isupper():
                lc = t[1:].lower()
                cap = int(counts[i])
                lo = low.get(lc, 0)
                if cap + lo > 0:
                    ratio[lc] = cap / (cap + lo)
        return cls(ratio)

    def is_name_initial(self, word: str, tok) -> bool:
        """Is a sentence-initial capitalised word a name (and not just a capital letter)?"""
        if word.lower() in STOP:
            return False
        first = tok.token_bytes()[tok.encode(" " + word)[0]].decode("utf-8", errors="replace")
        r = self.ratio.get(first.strip().lower())
        return True if r is None else r > 0.5


# ---------------------------------------------------------------------------
# candidate spans
# ---------------------------------------------------------------------------

@dataclass
class Span:
    text: str
    kind: str          # DATE, NUMBER, NAME
    start: int         # word index in the sentence
    end: int           # exclusive


def spans(sentence: str, initial_is_name=None) -> list[Span]:
    """Typed candidate spans of a sentence (word indices refer to ``words(sentence)``)."""
    ws = words(sentence)
    lw = [w.lower() for w in ws]
    out: list[Span] = []
    n = len(ws)
    # dates: [day] Month [day][,] [year] | Month year | year | decades | centuries
    i = 0
    while i < n:
        w = lw[i]
        if w in MONTHS or (w in MONTH_ABBR and i + 1 < n and (_NUM.match(ws[i + 1]) or ws[i + 1] == ".")):
            s, e = i, i + 1
            if s > 0 and _NUM.match(ws[s - 1]) and len(ws[s - 1]) <= 2:
                s -= 1
            j = e
            if j < n and _NUM.match(ws[j]) and len(ws[j]) <= 2:
                j += 1
            if j < n and ws[j] == ",":
                j += 1
            if j < n and _YEAR.match(ws[j]):
                j += 1
            elif j > e and ws[j - 1] == ",":
                j -= 1
            e = max(e, j)
            if e - s > 1 or w in MONTHS:
                out.append(Span(" ".join(ws[s:e]).replace(" ,", ","), "DATE", s, e))
            i = e
            continue
        if _NUM.match(ws[i]) and len(ws[i]) <= 4 and i + 1 < n and lw[i + 1] in ("bc", "bce", "ad", "ce"):
            out.append(Span(f"{ws[i]} {ws[i + 1]}", "DATE", i, i + 2))
            i += 2
            continue
        if lw[i] == "ad" and i + 1 < n and _NUM.match(ws[i + 1]) and len(ws[i + 1]) <= 4:
            out.append(Span(f"{ws[i]} {ws[i + 1]}", "DATE", i, i + 2))
            i += 2
            continue
        if _YEAR.match(ws[i]):
            out.append(Span(ws[i], "DATE", i, i + 1))
        elif w.endswith(("th", "st", "nd", "rd")) and w[:-2].isdigit() and i + 1 < n and lw[i + 1] in (
                "century", "centuries", "millennium"):
            out.append(Span(f"{ws[i]} {ws[i + 1]}", "DATE", i, i + 2))
        i += 1
    dates = list(out)
    # numbers: digits (with separators), number words, with a following unit/noun
    i = 0
    while i < n:
        w = lw[i]
        if _NUM.match(ws[i]) or (w in NUMBER_WORDS and w not in ("first", "second", "third", "half")):
            s = i
            if s > 0 and ws[s - 1] in ("$", "£", "€"):
                s -= 1
            j = i + 1
            while j < n and (_NUM.match(ws[j]) or lw[j] in NUMBER_WORDS[:-6] or lw[j] in ("and", "-")) and \
                    not (lw[j] == "and" and not (j + 1 < n and lw[j + 1] in NUMBER_WORDS)):
                j += 1
            if j < n and ws[j] in ("%",):
                j += 1
            elif j < n and lw[j] in ("percent", "per", "million", "billion", "thousand"):
                j += 1
                if j < n and lw[j - 1] == "per" and lw[j] == "cent":
                    j += 1
            num = " ".join(ws[s:j]).replace("$ ", "$").replace("£ ", "£").replace("€ ", "€").replace(" %", "%")
            unit_end = j
            if j < n and ws[j][0].isalpha() and lw[j] not in STOP and lw[j] not in NON_UNITS:
                unit_end = j + 1
            in_date = any(d.start <= i < d.end for d in dates)
            if not in_date and (not _YEAR.match(ws[i]) or j - i > 1 or s != i):
                out.append(Span(num, "NUMBER", s, j))
                if unit_end > j:
                    out.append(Span(num + " " + ws[j], "NUMBER", s, unit_end))
            i = j
            continue
        i += 1
    # names: runs of capitalised words, allowing connectors inside
    i = 0
    while i < n:
        w = ws[i]
        cap = w[0].isupper() and w[0].isalpha()
        if cap and (i == 0 or ws[i - 1] in (".", "!", "?", ":", '"', "“", "(")):
            if lw[i] in STOP or (initial_is_name is not None and not initial_is_name(w)):
                cap = False
        if cap and (lw[i] in MONTHS or lw[i] in NUMBER_WORDS or lw[i] in ("i", "i'm", "i've", "i'd", "i'll")):
            cap = False
        if cap:
            j = i + 1
            while j < n:
                if ws[j][0].isupper() and ws[j][0].isalpha() and lw[j] not in MONTHS and lw[j] not in NUMBER_WORDS:
                    j += 1
                elif lw[j] in CONNECT and j + 1 < n and ws[j + 1][0].isupper() and lw[j + 1] not in MONTHS:
                    j += 1
                else:
                    break
            if any(d.start < j and i < d.end for d in dates) or (j - i == 1 and lw[i] in ("bc", "bce", "ad", "ce")):
                i = j
                continue
            out.append(Span(" ".join(ws[i:j]), "NAME", i, j))
            # "Alcock and Brown": two names joined by and/& also form one candidate
            if j + 1 < n and lw[j] in ("and", "&") and ws[j + 1][0].isupper() and ws[j + 1][0].isalpha() \
                    and lw[j + 1] not in MONTHS and lw[j + 1] not in STOP:
                k = j + 2
                while k < n and ws[k][0].isupper() and ws[k][0].isalpha() and lw[k] not in MONTHS:
                    k += 1
                out.append(Span(" ".join(ws[i:k]), "NAME", i, k))
            i = j
            continue
        i += 1
    return out


def type_matches(atype: str, span: Span) -> bool:
    if atype == DATE:
        return span.kind == "DATE"
    if atype == NUMBER:
        return span.kind == "NUMBER"
    if atype in (PERSON, LOCATION, PROPER):
        return span.kind == "NAME"
    return True
