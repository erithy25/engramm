"""Simple inference from what the user said (U5): rule chains over notes taken during the conversation.

Every user message is read for notes — clock times and durations ("my train leaves at 7:30", "the drive is 40 min",
"it runs ninety minutes"), quantities and how they change ("3 packs of batteries, 4 in each", "5 more", "three are
empty"), rates ("two coffees a day"), prices per item and group sizes, recipes, ages and age differences, options with
attributes ("gym north is 8 minutes away, gym south 15"), a budget, what matters most, where the user lives, people
with their relation and what they did, what the user does not have, today's weekday or date and events.

A question is answered only when the notes contain everything it needs; otherwise the other layers answer. Nothing is
guessed: every number and name in an answer comes from the user's own words. A statement that contradicts a note (an
age, "no pets" and then "my dog") is pointed out and asked about instead of silently overwriting.
"""
from __future__ import annotations

import re
from datetime import datetime

_NUM_EN = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
           "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
           "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
           "forty-five": 45, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
           "a hundred": 100, "half an": 0.5, "half a": 0.5, "a couple of": 2, "a dozen": 12, "dozen": 12}
_NUM_DE = {"ein": 1, "eine": 1, "einen": 1, "einer": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6,
           "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "dreizehn": 13, "vierzehn": 14,
           "fünfzehn": 15, "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19, "zwanzig": 20,
           "dreißig": 30, "vierzig": 40, "fünfzig": 50, "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90,
           "hundert": 100, "anderthalb": 1.5, "eineinhalb": 1.5, "zweieinhalb": 2.5, "dreieinhalb": 3.5,
           "eine halbe": 0.5, "einer halben": 0.5, "ein dutzend": 12}
_NUMW = "|".join(sorted((re.escape(k) for k in list(_NUM_EN) + list(_NUM_DE)), key=len, reverse=True))
NUM = rf"(?:\d+(?:[.,]\d+)?|{_NUMW})"
_DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_DAYS_DE = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"]
_DAYW = "|".join(_DAYS_EN + _DAYS_DE)
_UNIT_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}
_PERIOD = {"day": "day", "days": "day", "tag": "day", "tage": "day", "tagen": "day", "week": "week", "weeks": "week",
           "woche": "week", "wochen": "week", "month": "month", "months": "month", "monat": "month", "monate": "month",
           "monaten": "month", "year": "year", "years": "year", "jahr": "year", "jahre": "year", "jahren": "year"}
_GROUP_DE = {"zu zweit": 2, "zu dritt": 3, "zu viert": 4, "zu fünft": 5, "zu sechst": 6, "zu siebt": 7, "zu acht": 8}
_CUR = r"(?:euros?|eur|€|dollars?|bucks|\$|pounds?|£|franken|chf)"


def num(s: str | None) -> float | None:
    if not s:
        return None
    s = s.strip().lower()
    if re.fullmatch(r"\d+(?:[.,]\d+)?", s):
        return float(s.replace(",", "."))
    if s in _NUM_EN:
        return float(_NUM_EN[s])
    if s in _NUM_DE:
        return float(_NUM_DE[s])
    m = re.fullmatch(rf"({_NUMW}|\d+) and a half", s)
    if m:
        return (num(m.group(1)) or 0) + 0.5
    return None


def _fmt_num(x: float) -> str:
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:.2f}".rstrip("0").rstrip(".")


def _stem(w: str) -> str:
    w = w.lower().strip(".,!?")
    for suf in ("ies", "es", "s", "en", "n", "e"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def _words(s: str) -> set[str]:
    stop = {"the", "has", "was", "did", "does", "who", "what", "hat", "ist", "der", "die", "das", "den", "dem", "wer",
            "and", "und", "me", "mir", "mich", "my", "mein", "meine", "meinen", "her", "his", "ihr", "sein", "is", "are",
            "for", "für", "to", "zu", "a", "an", "ein", "eine", "einen", "it", "es", "that"}
    return {_stem(w)[:5] for w in re.findall(r"[a-zäöüß0-9]{2,}", s.lower()) if w not in stop}


# -- note patterns -----------------------------------------------------------------------------------------------
_TIME = re.compile(r"\b(\d{1,2})[:.](\d{2})\s*(am|pm|a\.m\.|p\.m\.|uhr)?\b|\b(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.|uhr)\b|"
                   r"\b(?:at|um|by|bis|for|gegen)\s+(\d{1,2})\b(?![:.]\d)(?!\s*(?:minutes?|mins?|hours?|stunden?|min\b|"
                   r"years?|jahre|tage|days|euros?|€|%|people|leute|personen))", re.I)
_DUR = re.compile(rf"\b({NUM}(?: and a half)?)[- ]?(hours?|hrs?|h\b|minutes?|mins?|stunden?|std\.?|minuten?|min\b)", re.I)
_TRAVEL = re.compile(r"\b(?:drive|driving|walk|walking|ride|commute|journey|trip|fahrt|fahre|fahren|weg|anfahrt|zum|zur|"
                     r"to get (?:there|to)|to the|get there|takes me|take me|i need|brauch\w*|hinzukommen|park\w*|"
                     r"bus ride|train ride|by car|by bike|mit dem|to walk|to drive|away|buffer|puffer|spare|extra|early|früher|vorher)\b", re.I)
_LENGTH = re.compile(r"\b(?:long|lasts?|runs?|takes|goes on for|dauert|geht|lang|länge|is|ist)\b", re.I)
_EVENTY = re.compile(r"\b(?:film|movie|concert|show|workshop|meeting|game|match|lecture|class|course|seminar|play|"
                     r"konzert|vorstellung|sitzung|spiel|vorlesung|kurs|besprechung|it|es|er|sie|das)\b", re.I)
_REL = (r"best friend|boyfriend|girlfriend|neighbou?r|coworker|co-worker|colleague|boss|manager|friend|brother|sister|"
        r"mom|mum|mother|dad|father|aunt|uncle|cousin|grandma|grandmother|grandpa|grandfather|granny|wife|husband|partner|"
        r"son|daughter|roommate|flatmate|teacher|doctor|landlord|landlady|nephew|niece|"
        r"beste freundin|bester freund|freundin|freund|nachbarin|nachbar|kollegin|kollege|chefin|chef|bruder|schwester|"
        r"mama|mutter|papa|vater|tante|onkel|cousine|cousin|oma|opa|frau|mann|sohn|tochter|mitbewohnerin|mitbewohner|"
        r"lehrerin|lehrer|ärztin|arzt|vermieterin|vermieter|neffe|nichte")
_NOT_NAME = {"a", "an", "the", "very", "so", "really", "my", "your", "not", "ein", "eine", "sehr", "nicht", "mein", "is",
             "was", "has", "had", "and", "just", "got", "back", "home", "here", "there", "sick", "ill", "fine", "okay",
             "ok", "krank", "da", "hier", "hat", "ist", "war", "und", "wants", "lent", "helped", "gave", "called", "said",
             "says", "will", "can", "also", "auch", "heißt", "named", "came", "bought", "who", "she", "he", "sie", "er", "her",
             "his", "their", "them", "him", "ihr", "ihm", "sein", "seine", "ihre"}
_TITLE = r"(?:mrs?\.?|ms\.?|dr\.?|herr|frau|prof\.?)\s+"
_NONE = re.compile(r"\b(?:i|we) (?:don'?t|do not|didn'?t) (?:have|own|got) (?:any |a |an )?(pets?|kids|children|car|cars|"
                   r"siblings|brothers?|sisters?|dogs?|cats?)\b|\b(?:i|we) have no (pets?|kids|children|car|siblings)\b|"
                   r"\bi'?m an only child\b|\bich bin einzelkind\b|"
                   r"\b(?:ich|wir) (?:hab\w*|besitz\w*) (?:keine|kein|keinen) (haustiere?|kinder|kind|auto|geschwister|hund|katze)\b",
                   re.I)
_GROUPS = {"pet": r"dog|cat|hamster|rabbit|bird|parrot|guinea pig|puppy|kitten|pet|hund|katze|kater|hase|kaninchen|"
                  r"vogel|wellensittich|haustier|welpe",
           "kid": r"son|daughter|kid|kids|child|children|baby|toddler|sohn|tochter|kind|kinder|kleine[rn]?",
           "car": r"car|auto|wagen",
           "sibling": r"brother|sister|bruder|schwester"}
_NONE_GROUP = {"pet": "pet", "pets": "pet", "dog": "pet", "dogs": "pet", "cat": "pet", "cats": "pet", "kids": "kid",
               "children": "kid", "car": "car", "cars": "car", "siblings": "sibling", "brother": "sibling",
               "brothers": "sibling", "sister": "sibling", "sisters": "sibling", "haustier": "pet", "haustiere": "pet",
               "hund": "pet", "katze": "pet", "kinder": "kid", "kind": "kid", "auto": "car", "geschwister": "sibling"}
_AGE = [re.compile(r"^(?:and |also |btw |by the way |übrigens |oh,? )?(?:i'?m|i am|im|ich bin)(?: übrigens| by the way| actually| "
                   r"schon| erst| already| only)? (\d{1,3})(?: years old| jahre alt| years| y/?o)?\b(?!\s*(?:minutes?|min|km|%|euro|"
                   r"times|mal|kilo|kg|cm|people|personen))", re.I),
        re.compile(r"\bas an? (\d{1,3})[- ]year[- ]old\b|\bmit (?:meinen |meinem )?(\d{1,3}) jahren\b|"
                   r"\bi'?m (\d{1,3}) (?:years old|now)\b|\bi just turned (\d{1,3})\b|\bich bin (?:gerade |jetzt )?(\d{1,3}) "
                   r"(?:jahre alt|geworden)\b|\bat my age of (\d{1,3})\b|\bat (\d{2}) years old\b|"
                   r"\b(?:und|and|but|aber) (?:ich bin|i'?m|i am) (\d{1,3})\b(?!\s*(?:minutes?|min|km|%|euro|kg|cm))", re.I)]
_TODAY_DAY = re.compile(rf"\b(?:today is|today's|it'?s|heute ist|heut ist)\s+(?:a |ein )?({_DAYW})\b|\b({_DAYW}) today\b", re.I)
_TODAY_DOM = re.compile(r"\b(?:today is|today's|it'?s|heute ist|heut ist)\s+(?:the |der )?(\d{1,2})(?:st|nd|rd|th|\.)"
                        r"|\b(?:the )?(\d{1,2})(?:st|nd|rd|th) today\b|\bheute ist der (\d{1,2})\b", re.I)
_EVENT = re.compile(rf"\b(?:(?:my|the|our|mein\w*|der|die|das|unser\w*)\s+)?([a-zäöüß]+)\s+(?:is|are|ist|sind|findet|falls|fällt)\s+"
                    rf"(?:due |fällig |statt |set |planned |geplant )?(?:on|am|at|for)?\s*(?:the |dem )?({_DAYW}|\d{{1,2}}"
                    r"(?:st|nd|rd|th|\.))", re.I)
_IN_DAYS = re.compile(rf"\b(?:(?:my|the|our|mein\w*|der|die|das|unser\w*)\s+)?([a-zäöüß]+)\s+(?:is|starts|begins|ist|beginnt|"
                      rf"fängt|kommt|comes)\s+(?:\w+\s+)?in\s+({NUM})\s+(days|tagen)\b|\bin\s+({NUM})\s+(?:days|tagen)\s+"
                      r"(?:is|ist|i have|hab ich|habe ich)\s+(?:my |the |mein\w* |die |der |das )?([a-zäöüß]+)", re.I)
_PASSED = re.compile(rf"\b(?:it'?s been|been|es sind|sind schon|schon)\s+({NUM})\s+(?:days?|tage)\b|\b({NUM})\s+(?:days?|tage)\s+(?:have |has |sind |ist )?(?:passed|gone by|went by|later|go by|pass|"
                     r"vergangen|vorbei|rum|später)\b|\b(?:after|nach)\s+(" + NUM + r")\s+(?:days|tagen)\b", re.I)
_LIVE = re.compile(r"\b(?:live|living|moved|relocated|based|staying|wohne|wohnen|lebe|leben|wohn)\b(?:\s+[\wäöüß]+){0,4}?\s+"
                   r"(?:in|to|nach)\s+([A-Za-zÄÖÜäöüß][\wäöüß-]+(?:\s+[A-Z][\w-]+)?)|\bnach\s+([A-ZÄÖÜ][\wäöüß-]+)\s+gezogen\b",
                   re.I)
_NOT_CITY = {"a", "an", "the", "my", "our", "einer", "einem", "einen", "der", "die", "das", "town", "the city", "city",
             "here", "hier", "there", "with", "together", "new", "an", "ein", "eine", "mit", "zusammen", "apartment",
             "flat", "wohnung", "house", "haus"}


def _time_hm(mm) -> tuple[int, int, str] | None:
    if mm.group(1):
        h, mi, ap = int(mm.group(1)), int(mm.group(2)), mm.group(3)
    elif mm.group(4):
        h, mi, ap = int(mm.group(4)), 0, mm.group(5)
    else:
        h, mi, ap = int(mm.group(6)), 0, None
    if h > 24 or mi > 59:
        return None
    ap = (ap or "").lower().replace(".", "")
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return h, mi, "ap" if ap in ("am", "pm") else ("24" if h > 12 or ap == "uhr" else "")


def _mins(qty: str, unit: str) -> float | None:
    v = num(qty)
    if v is None:
        return None
    return v * 60 if unit.lower().startswith(("h", "s")) else v


def _segments(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"[;,]|\s+(?:and|but|while|whereas|und|aber|während)\s+|\s+-\s+|\s+–\s+", text) if x.strip()]


# -- observing ---------------------------------------------------------------------------------------------------
def observe(st, msg: str, lang: str) -> str | None:
    """Take notes from a user message. Returns a question about a contradiction with earlier notes, or None."""
    n = st.uses.setdefault("u_notes", {})
    low = msg.lower().strip()
    clash = _contradiction(n, low, lang)
    _note_none(n, low)
    _note_times(n, low)
    _note_place(n, msg, low)
    _note_people(n, msg, low)
    _note_days(n, low)
    _note_options(n, low, msg)
    _note_priority(n, low)
    _note_quantities(n, low)
    _note_ages(n, low)
    return clash


def _age_in(low: str) -> int | None:
    for rx in _AGE:
        m = rx.search(low)
        if m:
            v = int(next(x for x in m.groups() if x))
            if 3 <= v <= 120:
                return v
    return None


_DIET = [("veg", r"\bi'?m (?:a )?(?:vegetarian|vegan)\b|\bi(?:'ve| have) been (?:vegetarian|vegan)\b|\bi don'?t eat meat\b|"
                r"\bich bin vegetarier\w*|\bich bin veganer\w*|\bich esse kein fleisch\b|\bich lebe vegan\b|\bich bin vegan\b",
         r"\b(?:steak|chicken|beef|pork|bacon|ham|sausages?|lamb|veal|ribs|brisket|fleisch|schnitzel|hähnchen|rindfleisch|"
         r"schweinefleisch|wurst|speck|steaks|bratwurst|hackfleisch)\b",
         ("you're vegetarian", "du isst kein Fleisch")),
        ("alc", r"\bi don'?t drink(?: alcohol)?\b|\bi(?:'m| am) sober\b|\bi quit (?:drinking|alcohol)\b|\bno alcohol for me\b|"
                r"\bich trinke (?:\w+ )*?(?:keinen|kein) alkohol\b|\bich trinke nicht\b|\bkeinen alkohol mehr\b",
         r"\b(?:wine|beer|vodka|whisk(?:e)?y|gin|rum|cocktails?|champagne|prosecco|wein|bier|schnaps|sekt|rotwein|weißwein)\b",
         ("you don't drink alcohol", "du trinkst keinen Alkohol"))]


def _contradiction(n: dict, low: str, lang: str) -> str | None:
    clash = None
    for key, said, rx, words in _DIET:
        if re.search(said, low):
            n.setdefault("diet", [])
            if key not in n["diet"]:
                n["diet"].append(key)
        elif key in n.get("diet", []) and re.search(rx, low) and re.search(
                r"\b(?:i'?m|i am|i'll|i will|i want|i'd like|i'm going to|my|for myself|tonight|which|what|should i|ich|mein\w*|"
                r"soll ich|welche\w*|heute)\b", low) and not re.search(r"\b(?:without|instead of|ohne|statt|anstelle|no)\b", low):
            clash = (f"Wait — didn't you say earlier that {words[0]}? Did I get that wrong, or is it for someone else?"
                     if lang == "en" else f"Moment – vorhin hast du gesagt, {words[1]}. Hab ich das falsch verstanden, "
                     f"oder ist es für jemand anderen?")
            n["diet"] = [x for x in n["diet"] if x != key]
    age = _age_in(low)
    if age is not None and not re.search(r"\b(?:my|mein\w*|he|she|er|sie|his|her)\b.{0,20}\b(?:is|ist) " + str(age), low):
        old = n.get("age")
        if old and old != age:
            clash = (f"Wait — earlier you said you're {old}. Which is right, {old} or {age}?" if lang == "en" else
                     f"Moment – vorhin hast du gesagt, du bist {old}. Was stimmt denn, {old} oder {age}?")
        n["age"] = age
    for g, rx in _GROUPS.items():
        if g in n.get("none", []) and re.search(rf"\b(?:my|our|mein\w*|unser\w*)\s+(?:\w+\s+)?(?:{rx})(?:'s)?\b", low) and \
                not _NONE.search(low):
            what = {"pet": ("any pets", "keine Haustiere"), "kid": ("any kids", "keine Kinder"),
                    "car": ("a car", "kein Auto"), "sibling": ("any siblings", "keine Geschwister")}[g]
            clash = (f"Oh — didn't you say earlier that you don't have {what[0]}? Did I get that wrong?" if lang == "en" else
                     f"Oh – vorhin hattest du gesagt, du hast {what[1]}. Hab ich das falsch verstanden?")
            n["none"] = [x for x in n["none"] if x != g]
    return clash


def _note_none(n: dict, low: str) -> None:
    for mm in _NONE.finditer(low):
        w = next((x for x in mm.groups() if x), None)
        g = "sibling" if w is None else _NONE_GROUP.get(w.lower(), "")
        if g:
            n.setdefault("none", [])
            if g not in n["none"]:
                n["none"].append(g)


_SPOKEN = re.compile(r"\b(quarter past|half past|quarter to|viertel nach|viertel vor|halb)\s+(\d{1,2}|" + _NUMW + r")\b"
                     r"\s*(am|pm|uhr)?", re.I)


def _note_times(n: dict, low: str) -> None:
    for mm in _SPOKEN.finditer(low):
        h = num(mm.group(2))
        if h is None or not 0 < h <= 24:
            continue
        h = int(h)
        kind = mm.group(1).lower()
        if kind in ("quarter past", "viertel nach"):
            hh, mi = h, 15
        elif kind == "half past":
            hh, mi = h, 30
        elif kind == "halb":
            hh, mi = h - 1, 30
        else:
            hh, mi = h - 1, 45
        ap = (mm.group(3) or "").lower()
        if ap == "pm" and hh < 12:
            hh += 12
        n["time"] = [hh, mi, "ap" if ap in ("am", "pm") else ""]
        n.pop("travel", None)
        n.pop("length", None)
    for mm in _TIME.finditer(low):
        if mm.group(6) and not re.search(r"\b(?:leaves?|leaving|starts?|starting|begins?|departs?|meeting|appointment|"
                                         r"flight|train|bus|kicks? off|opens?|be at|be there|need to be|have to be|"
                                         r"fährt|beginnt|fängt|termin|zug|flug|um|muss|sein|anpfiff|los)\b", low):
            continue
        t = _time_hm(mm)
        if t is None:
            continue
        n["time"] = list(t)
        n.pop("travel", None)
        n.pop("length", None)
    for mm in _DUR.finditer(low):
        mins = _mins(mm.group(1), mm.group(2))
        if mins is None:
            continue
        travel = bool(_TRAVEL.search(low))
        if travel:
            n["travel"] = n.get("travel", 0) + mins
        elif _LENGTH.search(low) or _EVENTY.search(low):
            n["length"] = n.get("length", 0) + mins


def _note_place(n: dict, msg: str, low: str) -> None:
    best = None
    for mm in _LIVE.finditer(msg):
        city = mm.group(1) or mm.group(2)
        if not city:
            continue
        city = city.split()[0] if city.split()[0].lower() not in _NOT_CITY else ""
        if city and city.lower() not in _NOT_CITY and not re.match(r"(?:with|mit|zu|bei)$", city.lower()):
            best = city
    if best:
        n["city"] = best[:1].upper() + best[1:]


def _note_people(n: dict, msg: str, low: str) -> None:
    pats = [rf"\b(?:my|our|mein\w*|unser\w*)\s+({_REL})(?:'s name is| is called| is named| heißt|,? (?:her|his|their) name(?:'s| is)|"
            rf",? (?:she|he)'s called|, called|, named| is|,| ist|:)?\s+(?:{_TITLE})?"
            r"([A-Za-zÄÖÜäöüß][\wäöüßćčšž'-]+)(.*)$",
            rf"\b([A-Z][\wäöüßćčšž'-]+)\s+(?:is|ist)\s+(?:my|mein\w*)\s+({_REL})\b(.*)$"]
    for k, p in enumerate(pats):
        m = re.search(p, msg, re.I if k == 0 else 0)
        if not m:
            continue
        rel, name, rest = (m.group(1), m.group(2), m.group(3)) if k == 0 else (m.group(2), m.group(1), m.group(3))
        if name.lower() in _NOT_NAME or re.fullmatch(r"\d+", name):
            continue
        named = re.search(r"(?:name(?:'s| is)|called|named|heißt)\s+(?:" + _TITLE + r")?" + re.escape(name), msg, re.I)
        if not named and not name[:1].isupper():
            from engramm.understand.lex import lexicon
            if lexicon("de" if re.search(r"[äöüß]|\b(?:mein|meine|unser)\b", low) else "en").lookup(name.lower()):
                continue                       # "my sister, visiting …": a word, not a name
        key = name.lower()
        tm = re.search(rf"({_TITLE}){re.escape(name)}", msg, re.I)
        n.setdefault("display", {})[key] = (tm.group(1) if tm else "") + name[:1].upper() + name[1:]
        n.setdefault("people", {})[key] = rel.lower()
        n["last_person"] = key
        rest = rest.strip(" ,.!")
        if rest and len(rest.split()) >= 2:
            n.setdefault("did", []).append([key, rest.lower()])
        return
    m = re.match(r"^(?:and |und |also |auch )?(she|he|they|sie|er)(?:'s|'ll| is| has)?\s+(.{3,100}?)[.!]*$", low)
    if m and n.get("last_person"):
        n.setdefault("did", []).append([n["last_person"], m.group(2)])


def _note_days(n: dict, low: str) -> None:
    m = _TODAY_DAY.search(low)
    if m:
        n["today_wd"] = (_DAYS_EN + _DAYS_DE).index((m.group(1) or m.group(2)).lower()) % 7
    m = _TODAY_DOM.search(low)
    if m:
        n["today_dom"] = int(next(x for x in m.groups() if x))
    for mm in _EVENT.finditer(low):
        name, when = mm.group(1), mm.group(2).lower()
        if name in ("today", "heute", "it", "es", "that", "das"):
            continue
        ev = n.setdefault("events", {})
        ev[name] = ["wd", (_DAYS_EN + _DAYS_DE).index(when) % 7] if when in _DAYS_EN + _DAYS_DE else \
            ["dom", int(re.sub(r"\D", "", when))]
        n["last_event"] = name
    for mm in _IN_DAYS.finditer(low):
        name, v = (mm.group(1), num(mm.group(2))) if mm.group(1) else (mm.group(6), num(mm.group(4)))
        if v is not None and name:
            n.setdefault("events", {})[name] = ["in", v]
            n["last_event"] = name
            n["passed"] = 0
            return
    if n.get("events"):
        for mm in _PASSED.finditer(low):
            v = num(next((x for x in mm.groups() if x), None))
            if v is not None and not re.search(r"\bhow many\b|\bwie viele\b|\bif\b|\bwenn\b", low):
                n["passed"] = n.get("passed", 0) + v


_OPT_LABEL = re.compile(r"^(?:and |und |also |then |dann )?(?:(?:the|die|der|das|den|option|zum|zur|to the|for the)\s+)?"
                        r"((?:[a-zäöüß]+\s+){0,2}?(?:[a-z0-9]\b|one|first|second|third|erste|zweite|dritte|"
                        r"[a-zäöüß]{3,}))\b", re.I)
_ATTR = [("price", re.compile(rf"(?:{_CUR}\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*{_CUR}|(?:costs?|kostet|kosten|for|für|price(?: is)?|preis)\s+"
                               r"(\d+(?:[.,]\d+)?)\b(?!\s*(?:minutes?|mins?|min|minuten|hours?|h\b|stunden|m²|m2|qm|km|gb|kg|"
                               r"years?|jahre|%|square|quadrat)))(?:\s*(?:a|per|im|pro)\s*month|\s*im monat)?", re.I)),
         ("dist", re.compile(r"(\d+)\s*(?:minutes?|mins?|minuten|min)\b(?!\s*(?:long|lang))", re.I)),
         ("price", re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:a|per|/|im|pro)\s*(?:month|monat|mo)\b|(\d+(?:[.,]\d+)?)\s*monatlich", re.I)),
         ("batt", re.compile(r"(\d+)\s*(?:hours?|h|stunden|std)\b\s*(?:of\s+)?(?:battery|akku)|(?:battery|akku)\w*\s+(?:life\s+)?"
                             r"(?:of|von|is|ist|hält|lasts)?\s*(\d+)\s*(?:hours?|h|stunden)", re.I)),
         ("size", re.compile(r"(\d+)\s*(?:m²|m2|qm|square met(?:er|re)s?|sq ?m|quadratmeter)", re.I)),
         ("km", re.compile(r"(\d+)\s*(?:km|kilomet\w+|miles?)\b", re.I)),
         ("rating", re.compile(r"(\d(?:[.,]\d)?)\s*(?:stars?|sterne)", re.I))]
_LABEL_STOP = {"it", "it's", "its", "is", "costs", "cost", "has", "hat", "kostet", "ist", "one", "that", "this", "there",
               "the", "a", "an", "i", "we", "my", "mine", "only", "just", "nur", "about", "etwa", "and", "und", "but", "aber",
               "away", "from", "to", "zum", "zur", "bis", "so", "es", "sind", "are", "was", "zur auswahl", "auswahl",
               "options", "choice", "between", "zwischen", "either", "oder", "or", "then", "dann", "while"}


def _note_options(n: dict, low: str, msg: str = "") -> None:
    m = re.search(rf"\b(?:only have|i have|i've got|i got|budget(?: is| of)?|max(?:imum)?|at most|up to|nur|höchstens|maximal|"
                  rf"bis zu|budget von|hab nur|habe nur|my max|mein max\w*|maximum)\s+(?:is |of |ist |liegt bei |wäre )?(?:{_CUR}\s*)?"
                  rf"(\d+(?:[.,]\d+)?)\s*(?:{_CUR})?", low)
    if m and re.search(_CUR + r"|budget|spend|ausgeben|afford|leisten|max", low):
        n["budget"] = float(m.group(1).replace(",", "."))
        low = low[:m.start()] + low[m.end():]
    found = []
    last_label = None
    for seg in _segments(low):
        attrs = {}
        for key, rx in _ATTR:
            mm = rx.search(seg)
            if mm and key in attrs:
                continue
            if mm:
                val = next((x for x in mm.groups() if x), None)
                if val:
                    attrs[key] = float(val.replace(",", "."))
                    if key == "price" and "dist" in attrs and attrs["price"] == attrs["dist"]:
                        attrs.pop("price")
        if "dist" in attrs and "price" in attrs and re.search(rf"{_fmt_num(attrs['price'])}\s*(?:min|minutes?)", seg):
            attrs.pop("price")
        hrs = re.search(r"(\d+)\s*(?:hours?|h|stunden|std)\b", seg)
        if hrs and "batt" not in attrs and any("batt" in o for o in n.get("options", []) + [a for _, a in found]):
            attrs["batt"] = float(hrs.group(1))
        if not attrs:
            continue
        first = min((mm.start() for _, rx in _ATTR for mm in [rx.search(seg)] if mm), default=len(seg))
        head = re.sub(r"\s+(?:is|costs?|has|hat|kostet|kosten|ist|sind|are|for|für|with|mit|takes|braucht|has got|"
                      r"comes with|offers|bietet|about|etwa|only|nur|just)(?:\s+(?:only|nur|just|about|etwa|a|an|ein|eine))?$",
                      "", seg[:first].strip(" :,.")).strip(" :,.")
        head = re.sub(r"^(?:and|und|then|dann|so|also|auch|while|but|aber)\s+", "", head)
        head = head.split(":")[-1].strip()
        pm = re.search(r"\b(?:ich|i|we|wir)\s+(?:\w+\s+)?((?:mit|by|per|zu|on)\s+.+)$", head)
        if pm:
            head = pm.group(1)
        head = re.sub(r"^(?:zur auswahl:?|options?:|either|entweder|choice:?|i'?m choosing between|between|zwischen)\s*", "",
                      head).strip()
        head = re.sub(r"^(?:the|die|der|das|den|ein|eine|einen|a|an|zum|zur|to the|it's|es sind|es ist)\s+", "", head).strip()
        head = re.sub(r"^(?:the|die|der|das|den|ein|eine|einen|a|an)\s+", "", head).strip()
        label = head if head and head not in _LABEL_STOP and len(head) <= 30 and \
            not re.match(r"^(?:i|we|ich|wir|you|du|need|needs|want|it|es|that|this|my|mein\w*|takes?|braucht?|brauche)\b", head) \
            else last_label
        if not label:
            continue
        last_label = label
        found.append((label, attrs))
    if not found:
        return
    opts = n.setdefault("options", [])
    for label, attrs in found:
        i = low.find(label)
        disp = msg[i:i + len(label)] if msg and i >= 0 and len(msg) == len(low) else label
        for o in opts:
            if o["label"] == label:
                o.update(attrs)
                break
        else:
            opts.append({"label": label, "disp": disp, **attrs})


def _note_priority(n: dict, low: str) -> None:
    for key, rx in (("price", r"price|cost|cheap|money|budget|preis|kosten|günstig|geld|billig"),
                    ("dist", r"commute|distance|close|near|location|short way|weg|nähe|nah|entfernung|fahrzeit|kurz"),
                    ("batt", r"battery|akku|laufzeit"), ("size", r"size|space|big|room|größe|platz|groß|fläche"),
                    ("rating", r"rating|reviews|stars|bewertung|sterne")):
        if re.search(rf"\b(?:care (?:most )?about|most important|matters most|matters to me|priority|am wichtigsten|"
                     rf"wichtig ist mir|mir geht es um|i want|i need|i prefer|ich will|ich brauche|lieber)\b.*\b(?:{rx})|"
                     rf"\b(?:{rx})\w*(?:\s+\w+){{0,2}}\s+(?:am wichtigsten|is (?:the )?most important|matters (?:the )?most|zählt am meisten|"
                     rf"is key|ist mir wichtig)|"
                     rf"\b(?:{rx})\w*\b.*\b(?:is|ist|matters)\s+(?:most important|am wichtigsten|mir wichtig|"
                     rf"(?:the )?most|key|entscheidend)", low):
            n["priority"] = key
            return


def _note_quantities(n: dict, low: str) -> None:
    q = n.setdefault("qty", {})
    m = re.match(rf"^(?:so |well |also |by the way,? )?(?:i have|i've got|i got|we have|we've got|ich hab\w*|wir haben)\s+({NUM})\s+"
                 r"([a-zäöüß]+)\s*[.!]*$", low)
    if m and num(m.group(1)) is not None:
        q[_stem(m.group(2))] = {"v": num(m.group(1)), "derived": False}
        n["last_item"] = _stem(m.group(2))
    created = bool(m)
    mo = re.search(rf"\b({NUM})\s+(packs?|boxes|box|bags?|cartons?|crates?|cases?|packets?|trays?|rolls?|sacks?|kisten?|kartons?|"
                   rf"packungen?|tüten?|päckchen|schachteln?|sixpacks?|six-packs?)\s+(?:of\s+|mit\s+)?((?:[a-zäöüß-]+\s+){{0,2}}?"
                   rf"[a-zäöüß-]+)?(?=\s+(?:for|für|from|at|in|bei|von|zum|zur)\b|[,.;!]|\s*$|\s+(?:with|mit|à|je)\b)", low)
    me = re.search(rf"\b({NUM})\s+(?:in each|each|apiece|per (?:pack|box|bag|carton|crate|case)|in jede[mr]?\b|pro "
                   rf"(?:packung|kiste|karton|tüte|schachtel))|\beach (?:one )?(?:has|contains|holds|with) ({NUM})|\bmit je ({NUM})"
                   rf"(?:\s+([a-zäöüß]+))?|\bje ({NUM})\b", low)
    if mo and me and num(mo.group(1)) is not None:
        inner = num(next(x for x in (me.group(1), me.group(2), me.group(3), me.group(5)) if x))
        item = me.group(4) or (mo.group(3) or mo.group(2))
        item = _stem(item.split()[-1])
        if inner is not None:
            q[item] = {"v": num(mo.group(1)) * inner, "derived": True}
            n["last_item"] = item
            created = True
    for seg in ([] if created else [low]):
        m = re.search(rf"\b({NUM})\s+([a-zäöüß]+)\s+(?:of|mit je|with|à|a)\s+({NUM})?\s*([a-zäöüß]+)?(?:[, ]+({NUM})\s+(?:in each|each|"
                      rf"per \w+|je \w+|in jede\w*|pro \w+))?", seg)
        if m and num(m.group(1)) is not None and m.group(2) not in ("minutes", "hours", "minuten", "stunden", "days", "tage",
                                                                    "times", "mal", "years", "jahre"):
            outer, unit = num(m.group(1)), _stem(m.group(2))
            inner = num(m.group(3)) if m.group(3) else num(m.group(5)) if m.group(5) else None
            item = _stem(m.group(4)) if m.group(4) else None
            if inner is not None and item and item not in ("each", "je"):
                q[item] = {"v": outer * inner, "derived": True}
                n["last_item"] = item
                created = True
            elif item and inner is None and not re.search(r"\b(?:each|je)\b", seg):
                q.setdefault("_units", {})[unit] = [outer, item]
                n["last_item"] = item
            elif m.group(5) and item:
                q[item] = {"v": outer * num(m.group(5)), "derived": True}
                n["last_item"] = item
                created = True
        m = re.search(rf"\beach\s+([a-z]+)\s+(?:has|contains|holds|is|comes with)\s+({NUM})\s+([a-z]+)|"
                      rf"\bjede[rs]?\s+([a-zäöüß]+)\s+(?:hat|enthält)\s+({NUM})\s+([a-zäöüß]+)", seg)
        if m:
            unit, v, item = (m.group(1), num(m.group(2)), m.group(3)) if m.group(1) else (m.group(4), num(m.group(5)), m.group(6))
            units = q.get("_units", {})
            cnt = units.get(_stem(unit), [None])[0]
            if cnt is None:
                mm = re.search(rf"\b({NUM})\s+{re.escape(_stem(unit))}", " ".join(n.get("_said", [])))
                cnt = num(mm.group(1)) if mm else None
            if cnt is not None and v is not None:
                q[_stem(item)] = {"v": cnt * v, "derived": True}
                n["last_item"] = _stem(item)
        m = re.search(rf"\b({NUM})\s+(?:more|extra|additional|weitere|mehr|dazu)\b(?:\s+([a-zäöüß]+))?|\banother\s+({NUM})\b"
                      rf"(?:\s+([a-z]+))?|\b(?:gave|gives|brought|handed|hat mir|haben mir)\s+(?:me\s+|mir\s+)?"
                      rf"(?:another\s+|noch\s+)?({NUM})\s+(?:more\s+|weitere\s+)?([a-zäöüß]+)?", seg)
        if m and not created:
            v = num(m.group(1) or m.group(3) or m.group(5))
            item = m.group(2) or m.group(4) or m.group(6)
            item = _stem(item) if item and _stem(item) in q else n.get("last_item")
            if v is not None and item and item in q:
                q[item] = {"v": q[item]["v"] + v, "derived": True}
        m = re.search(rf"\b({NUM})\s+(?:of them\s+|davon\s+|([a-zäöüß]+)\s+)?(?:are|were|is|sind|waren|ist)\s+(?:already\s+|schon\s+|"
                      rf"bereits\s+)?(?:empty|broken|gone|used|eaten|leer|kaputt|weg|aufgebraucht|gegessen|ausgetrunken)|"
                      rf"\b(?:i |we |ich |wir )?(?:used|ate|lost|sold|drank|gave away|broke|threw away|verbraucht|gegessen|"
                      rf"verloren|verkauft|getrunken|verschenkt|kaputt gemacht|weggeworfen)\s+({NUM})\b|\b(?:hab|habe|haben)\s+"
                      rf"({NUM})\s+(?:davon\s+)?(?:verbraucht|gegessen|verloren|verkauft|getrunken|verschenkt|weggeworfen)", seg)
        if m:
            v = num(m.group(1) or m.group(3) or m.group(4))
            item = _stem(m.group(2)) if m.group(2) and _stem(m.group(2)) in q else n.get("last_item")
            if v is not None and item and item in q:
                q[item] = {"v": q[item]["v"] - v, "derived": True}
    # rates
    m = re.search(rf"\b({NUM})\s+((?:[a-zäöüß€$]+\s+){{0,2}}?)(?:a|per|every|each|pro|am|im|jeden|jede|jedes|in the|in der|"
                  rf"each and every)\s+(day|week|month|year|tag|woche|monat|jahr)\b", low)
    m2 = re.search(rf"\b(?:every|each|jeden|jede|jedes|per|pro)\s+(day|week|month|year|tag|woche|monat|jahr)\b[^.?!]*?\b({NUM})\s*"
                   rf"([a-zäöüß€$]+)?", low)
    if m and num(m.group(1)) is not None:
        n["rate"] = [num(m.group(1)), m.group(2).strip(), _PERIOD[m.group(3)]]
    elif m2 and num(m2.group(2)) is not None:
        n["rate"] = [num(m2.group(2)), (m2.group(3) or "").strip(), _PERIOD[m2.group(1)]]
    # price per item and group size
    m = re.search(rf"\b(?:a|one|each|per|ein|eine|pro|jede[rs]?)\s+([a-zäöüß]+)\s+(?:costs?|kostet|is|ist)\s+(?:{_CUR}\s*)?"
                  rf"(\d+(?:[.,]\d+)?)|\b([a-zäöüß]+)\s+(?:are|cost|kosten|sind)\s+(?:{_CUR}\s*)?(\d+(?:[.,]\d+)?)\s*(?:{_CUR}\s*)?"
                  rf"(?:each|apiece|a piece|je|pro stück|pro person|per person|das stück)", low)
    if not m:
        m = re.search(rf"(?:{_CUR}\s*)?(\d+(?:[.,]\d+)?)\s*(?:{_CUR}\s*)?(?:per person|per head|a head|each|pro person|pro kopf|"
                      rf"p\.?p\.?|pro nase|pro ticket|per ticket)\b", low)
        if m:
            n["unit_price"] = float(m.group(1).replace(",", "."))
            cur = re.search(_CUR, low)
            n["cur"] = cur.group(0) if cur else ""
            m = None
    if m:
        n["unit_price"] = float((m.group(2) or m.group(4)).replace(",", "."))
        cur = re.search(_CUR, low)
        n["cur"] = cur.group(0) if cur else ""
    m = re.search(rf"\b(?:a )?group of\s+({NUM})\b|\bwe(?:'re| are)\s+(?!a\b|an\b)({NUM})(?:\s+people|\s+of us)?\b|\bthere(?:'s| are| will be)\s+({NUM})\s+of us\b|"
                  rf"\b({NUM})\s+of us\b|\bwir sind\s+({NUM})\b|\b(?:a )?group of\s+({NUM})\b|\beine gruppe von\s+({NUM})\b|\bfor\s+({NUM})\s+(?:people|persons|of us|friends|guests)\b|"
                  rf"\bfür\s+({NUM})\s+(?:leute|personen|gäste)\b", low)
    if m:
        v = num(next(x for x in m.groups() if x))
        if v:
            n["group"] = v
    for k, v in _GROUP_DE.items():
        if k in low:
            n["group"] = v
    # recipe and its target size
    m = re.search(rf"\b(?:recipe|rezept)\b.*?\b(?:for|für|makes|serves|ergibt|reicht für)\s+({NUM})\b.*?\b({NUM})\s*"
                  r"(g|grams?|gramm|kg|ml|l|liters?|cups?|tassen?|el|tl|tbsp|tsp|eggs?|eier)\b\s*(?:of\s+)?([a-zäöüß]+)?", low)
    if m:
        n["recipe"] = [num(m.group(1)), num(m.group(2)), m.group(3), m.group(4) or ""]
    m = re.search(rf"\b(?:cook(?:ing)?|bak(?:e|ing)|mak(?:e|ing)|want to make|need|koche|backe|mache|brauche)\s+(?:it\s+|es\s+)?"
                  rf"(?:for\s+|für\s+)?({NUM})\s+(?:servings|people|portions|persons|guests|portionen|personen|leute|gäste)\b|"
                  rf"\b(?:cooking|baking|kochen|backen|koche|backe)\s+(?:for|für)\s+({NUM})\b", low)
    if re.search(r"\b(?:recipe|rezept)\b", low):
        pass
    elif m and n.get("recipe"):
        n["cook_for"] = num(m.group(1) or m.group(2))
    elif n.get("recipe") and n.get("group") and (re.search(r"\b(?:zu (?:zweit|dritt|viert|fünft|sechst|siebt|acht))\b", low) or
                                                  re.search(rf"\b(?:we(?:'re| are)|wir sind|group of|gruppe von|of us)\b", low)):
        n["cook_for"] = n["group"]              # "wir sind aber zu sechst" said now
    n.setdefault("_said", []).append(low)
    n["_said"] = n["_said"][-8:]


def _note_ages(n: dict, low: str) -> None:
    ages = n.setdefault("ages", {})
    m = re.search(rf"\b(?:my|mein\w*)\s+({_REL})\s+(?:is|ist)\s+(\d{{1,3}})\b(?!\s*(?:minutes?|cm|kg|km|%|euro|years? (?:older|"
                  rf"younger)|jahre (?:älter|jünger)))", low)
    if m:
        ages[m.group(1)] = int(m.group(2))
        n["age_last"] = m.group(1)
    m = re.search(rf"\b(i'?m|i am|ich bin|(?:my|mein\w*)\s+(?:{_REL}))\s+(?:is\s+|ist\s+)?({NUM})\s+(?:years?|jahre)\s+"
                  r"(older|younger|älter|jünger)\s+(?:than|als)\s+(him|her|them|ihn|sie|er|ihm|ihr|me|mich|ich|you|"
                  rf"(?:my|mein\w*)\s+(?:{_REL}))", low)
    if m:
        who = "me" if m.group(1).startswith(("i", "ich")) else m.group(1).split()[-1]
        ref = m.group(4)
        base_key = n.get("age_last") if ref in ("him", "her", "them", "ihn", "sie", "er", "ihm", "ihr") else \
            ("me" if ref in ("me", "mich", "ich") else ref.split()[-1])
        base = ages.get(base_key) if base_key != "me" else (ages.get("me") or n.get("age"))
        d = num(m.group(2))
        if base is not None and d is not None:
            ages[who] = base + d if m.group(3) in ("older", "älter") else base - d
            n["age_last"] = who
    m = re.search(r"\bi was (\d{1,2}) when (?:she|he|they|my \w+) (?:was|were) born\b|"
                  r"\bich war (\d{1,2}),? als (?:sie|er|es|mein\w* \w+) geboren wurde\b", low)
    if m and n.get("age_last") and n["age_last"] in ages:
        ages["me"] = ages[n["age_last"]] + int(m.group(1) or m.group(2))


# -- answering ---------------------------------------------------------------------------------------------------
def fallback(st, msg: str, lang: str) -> str | None:
    """After the other layers found nothing: a person's name the user mentioned in passing ("my boss, her name's
    Margit") — the memory answers first when it knows."""
    return _ans_name(st.uses.get("u_notes") or {}, msg.lower().strip(), lang == "de", None)


def _fmt_time(h: int, m: int, style: str, lang: str) -> str:
    h %= 24
    if lang == "de":
        return f"{h}:{m:02d} Uhr"
    if style == "ap":
        return f"{(h % 12) or 12}:{m:02d} {'pm' if h >= 12 else 'am'}"
    return f"{h}:{m:02d}"


def _asks(low: str) -> bool:
    return bool(re.search(r"\?\s*$|^(?:so |and |und |also |ok |okay )?(?:how|what|when|which|who|whats|what's|where|"
                          r"wann|wie|welche\w*|was|wer|wo|in wie|um wie)\b", low))


def answer(st, msg: str, lang: str, now: datetime | None = None) -> str | None:
    n = st.uses.get("u_notes") or {}
    low = msg.lower().strip()
    if not _asks(low):
        return None
    de = lang == "de"
    for f in (_ans_time, _ans_days, _ans_choose, _ans_count, _ans_rate, _ans_total, _ans_recipe, _ans_agediff, _ans_age,
              _ans_who, _ans_place):
        out = f(n, low, de, now)
        if out:
            return out
    return None


def _ans_time(n, low, de, now):
    if "time" not in n:
        return None
    h, mi, style = n["time"]
    if n.get("travel") and re.search(r"\b(?:when|what time|by when)\b.*\b(?:leave|go|set off|head out|start|get going|"
                                     r"depart|be out)\b|\bwann\b.*\b(?:los|losfahren|losgehen|aufbrechen|aus dem haus|"
                                     r"fahren|gehen|starten|weg)\b|\bum wie ?viel uhr\b.*\b(?:los|fahren|gehen)\b", low):
        t = h * 60 + mi - n["travel"]
        lh, lm = divmod(int(t) % 1440, 60)
        at, by = _fmt_time(h, mi, style, "de" if de else "en"), _fmt_time(lh, lm, style, "de" if de else "en")
        if de:
            return f"Um {at} da zu sein, musst du spätestens um {by} los – ein paar Minuten früher geben dir Puffer."
        return f"To make it for {at}, you'd need to leave by {by} at the latest — a few minutes earlier gives you a buffer."
    if n.get("length") and re.search(r"\b(?:over|end|ends|finish|finishes|finished|done|out|wrap up|wraps up|let out|"
                                     r"zu ende|vorbei|aus|fertig|endet|ende|rum)\b", low):
        t = h * 60 + mi + n["length"]
        eh, em = divmod(int(t) % 1440, 60)
        e = _fmt_time(eh, em, style, "de" if de else "en")
        return f"Dann ist es gegen {e} zu Ende." if de else f"It should be over at about {e}."
    return None


def _ans_days(n, low, de, now):
    if not re.search(r"\bhow many days\b|\bwie viele tage\b|\bhow long until\b|\bhow long till\b|\bwie lange (?:noch )?bis\b|"
                     r"\bhow many (?:are |would be |will be |do i have )?left\b|\bwie viele (?:sind |wären )?(?:dann )?(?:noch )?"
                     r"übrig\b|\bin how many days\b|\bin wie vielen tagen\b|\bhow many more days\b|\bdays (?:are )?left\b|"
                     r"\bhow many days do i have\b|\bnoch wie viele tage\b", low):
        return None
    ev = n.get("events") or {}
    name = next((k for k in ev if re.search(rf"\b{re.escape(k)}", low)), n.get("last_event"))
    if not name or name not in ev:
        return None
    kind, val = ev[name]
    days = None
    if kind == "in":
        m = re.search(rf"\b({NUM})\s+(?:more\s+)?(?:days?|tage)\s+(?:pass|have passed|go by|later|vergehen|vorbei|vergangen)", low)
        days = val - n.get("passed", 0) - (num(m.group(1)) if m else 0)
    elif kind == "wd":
        today = n.get("today_wd", (now or datetime.now()).weekday())
        days = (val - today) % 7 or 7
    elif kind == "dom":
        today = n.get("today_dom", (now or datetime.now()).day)
        if val >= today:
            days = val - today
    if days is None or days < 0:
        return None
    d = _fmt_num(days)
    if de:
        return f"Noch {d} {'Tag' if d == '1' else 'Tage'}."
    return f"{d} {'day' if d == '1' else 'days'} to go."


_CRIT = [("price-", r"cheaper|cheapest|less expensive|least expensive|costs? less|lower price|günstiger|günstigste\w*|billiger|"
                    r"billigste\w*|preiswerter|am günstigsten|weniger"),
         ("price+", r"more expensive|most expensive|pricier|teurer|teuerste\w*"),
         ("dist-", r"closer|closest|nearer|nearest|shorter commute|shortest|quickest|fastest|näher|nächste\w*|am nächsten|"
                   r"kürzer\w*|schneller|schnellste\w*|am schnellsten"),
         ("batt+", r"battery|akku|lasts? longer|longest|längste\w*|länger"),
         ("size+", r"bigger|biggest|larger|largest|more space|most space|roomier|größer|größte\w*|mehr platz|geräumiger"),
         ("size-", r"smaller|smallest|kleiner|kleinste\w*"),
         ("rating+", r"better rated|best rated|higher rated|highest rated|besser bewertet|beste bewertung")]


def _ans_choose(n, low, de, now):
    opts = n.get("options") or []
    if len(opts) < 2 or not re.search(r"\bwhich\b|\bwelche\w*\b|\bwhat one\b|^was ist\b|\bwhat should i (?:take|get|buy|pick|"
                                      r"choose)\b|\bwas soll ich\b|\bbetter\b|\bbesser\b", low):
        return None
    crit = None
    for key, words in _CRIT:
        if re.search(rf"\b(?:{words})\b", low):
            crit = key
            break
    pool = opts
    if crit is None and re.search(r"\b(?:should i|would you|better|best|soll ich|würdest du|besser|nehmen|take|get|choose|"
                                  r"pick|buy|kaufen|go for|recommend)\b", low):
        if n.get("budget") is not None:
            ok = [o for o in opts if "price" in o and o["price"] <= n["budget"]]
            if len(ok) == 1:
                o = ok[0]
                lab = o.get("disp") or o["label"]
                if de:
                    return (f"{lab[:1].upper() + lab[1:]} – mit {_fmt_num(o['price'])} passt das als Einziges in dein "
                            f"Budget von {_fmt_num(n['budget'])}.")
                return f"The {lab} — at {_fmt_num(o['price'])} it's the only one within your budget of {_fmt_num(n['budget'])}."
            if ok:
                pool = ok
        if n.get("priority"):
            crit = n["priority"] + ("-" if n["priority"] in ("price", "dist") else "+")
    if not crit:
        return None
    key, sign = crit[:-1], crit[-1]
    if n.get("budget") is not None and key != "price" and pool is opts:
        ok = [o for o in opts if "price" in o and o["price"] <= n["budget"]]
        if ok:
            pool = ok                         # "the biggest one I can afford"
    have = [o for o in pool if key in o]
    if len(have) < 2:
        return None
    best = (min if sign == "-" else max)(have, key=lambda o: o[key])
    if sum(1 for o in have if o[key] == best[key]) > 1:
        return None
    unit = {"price": "", "dist": " min", "batt": " h", "size": " m²", "km": " km", "rating": "★"}[key]
    vs = ", ".join(_fmt_num(o[key]) + unit for o in have if o is not best)
    lab = best.get("disp") or best["label"]
    if de:
        return f"{lab[:1].upper() + lab[1:]} – {_fmt_num(best[key])}{unit} gegenüber {vs}."
    art = "" if re.match(r"(?:option|flat|laptop|gym|plan|offer|apartment|phone|car|job|room|hotel)\s", lab, re.I) or \
        re.match(r"[a-z]+ [a-z0-9]$", lab, re.I) or lab[:1].isupper() else "The "
    lab = lab if art else lab[:1].upper() + lab[1:]
    return f"{art}{lab} — {_fmt_num(best[key])}{unit} vs. {vs}."


def _ans_count(n, low, de, now):
    m = re.search(r"\bhow many\s+([a-zäöüß]+)?|\bwie viele\s+([a-zäöüß]+)?", low)
    if not m:
        return None
    q = n.get("qty") or {}
    raw = (m.group(1) or m.group(2) or "")
    word = "" if raw in ("volle", "full", "noch", "dann", "left", "übrig", "do", "are", "sind", "is", "habe", "hab") else _stem(raw)
    item = word if word in q else n.get("last_item") if word in ("", "volle", "full", "sind", "do", "have", "are", "left",
                                                                 "is", "habe", "hab", "noch", "dann", "übrig") or \
        not word or n.get("last_item", "").startswith(word[:4]) else None
    if not item or item not in q or not q[item].get("derived"):
        return None
    v = q[item]["v"]
    if v < 0:
        return None
    return f"Dann sind es {_fmt_num(v)}." if de else f"That makes {_fmt_num(v)}."


def _ans_rate(n, low, de, now):
    if not n.get("rate") or not re.search(r"\bhow (?:far|much|many|long)\b|\bwie (?:viel|viele|weit|lange)\b|\bwhat'?s the total\b",
                                           low):
        return None
    m = re.search(rf"\b(?:in|per|after|over|nach|im|in einem|pro|for|für|across|within|innerhalb)\s+(?:a |one |einem |einer |"
                  rf"(?P<n>{NUM})\s+)?(?P<u>days?|weeks?|months?|years?|tagen?|wochen?|monate?n?|jahre?n?)\b", low)
    if not m:
        return None
    count = num(m.group("n")) if m.group("n") else 1
    tu = _PERIOD.get(m.group("u"))
    v, unit, per = n["rate"]
    if not tu or count is None:
        return None
    exact = {("day", "week"): 7, ("week", "year"): 52, ("month", "year"): 12, ("day", "year"): 365}
    if per == tu:
        factor = 1
    elif (per, tu) in exact:
        factor = exact[(per, tu)]
    elif per == "day" and tu == "month":
        factor = 30
    else:
        factor = _UNIT_DAYS[tu] / _UNIT_DAYS[per] if _UNIT_DAYS[tu] >= _UNIT_DAYS[per] else None
    if not factor:
        return None
    tot = _fmt_num(v * factor * count)
    note = (" (bei 30 Tagen im Monat)" if de else " (counting 30 days a month)") if (per, tu) == ("day", "month") else ""
    u = f" {unit}" if unit else ""
    return f"Das wären {tot}{u}{note}." if de else f"That's {tot}{u}{note}."


def _ans_total(n, low, de, now):
    if n.get("unit_price") is None or not n.get("group") or not re.search(
            r"\b(?:total|altogether|in all|all together|overall|insgesamt|zusammen|gesamt|how much|wie viel|what will it cost|"
            r"was kostet)\b", low):
        return None
    tot = _fmt_num(n["unit_price"] * n["group"])
    cur = n.get("cur", "")
    if cur in ("$",):
        return f"Insgesamt ${tot}." if de else f"${tot} altogether."
    word = {"€": "Euro" if de else "euros", "eur": "Euro" if de else "euros"}.get(cur, cur)
    return f"Insgesamt {tot} {word}".strip() + "." if de else f"{tot} {word}".strip() + " altogether."


def _ans_recipe(n, low, de, now):
    if not n.get("recipe") or not n.get("cook_for") or not re.search(r"\bhow (?:much|many)\b|\bwie viel\w*\b", low):
        return None
    base, amount, unit, item = n["recipe"]
    if not base or amount is None:
        return None
    need = _fmt_num(amount * n["cook_for"] / base)
    if de:
        return f"Für {_fmt_num(n['cook_for'])} brauchst du {need} {unit}{' ' + item if item else ''}."
    return f"For {_fmt_num(n['cook_for'])} you need {need} {unit}{' of ' + item if item else ''}."


def _ans_agediff(n, low, de, now):
    m = re.search(rf"\bhow much (older|younger) (?:is|are) (he|she|they|(?:my|your) (?:{_REL}))\s+than (?:me|i|i am)\b|"
                  rf"\bwie viel (älter|jünger) (?:ist|sind) (er|sie|mein\w* (?:{_REL}))\s+als ich\b|"
                  rf"\bhow many years (older|younger) (?:is|are) (he|she|(?:my) (?:{_REL}))\b", low)
    if not m:
        return None
    ages = n.get("ages") or {}
    who = next(x for x in (m.group(2), m.group(4), m.group(6)) if x)
    rel = re.search(rf"\b({_REL})\b", who)
    key = rel.group(1) if rel else n.get("age_last")
    me = ages.get("me") or n.get("age")
    if key not in ages or not me:
        return None
    d = ages[key] - me
    word = (m.group(1) or m.group(3) or m.group(5)).lower()
    if word in ("younger", "jünger"):
        d = -d
    if d < 0:
        return None
    return f"{_fmt_num(d)} Jahre." if de else f"{_fmt_num(d)} years."


def _ans_age(n, low, de, now):
    m = re.search(rf"\bhow old (?:am i|is (?:he|she|my (?:{_REL}))|are (?:they))\b|\bwie alt (?:bin ich|ist (?:er|sie|mein\w* "
                  rf"(?:{_REL})))\b", low)
    if not m:
        return None
    ages = n.get("ages") or {}
    s = m.group(0)
    if re.search(r"\b(?:am i|bin ich)\b", s):
        key = "me"
    else:
        rel = re.search(rf"\b({_REL})\b", s)
        key = rel.group(1) if rel else n.get("age_last")
    if key not in ages or (key == "me" and "me" not in ages):
        return None
    a = _fmt_num(ages[key])
    if key == "me":
        return f"Dann bist du {a}." if de else f"Then you're {a}."
    return f"{a}." if not de else f"{a} Jahre."


def _ans_name(n, low, de, now):
    m = re.search(rf"\bwhat(?:'s| is| was)\s+(?:my|the)\s+({_REL})(?:'s)?\s+(?:name|called)\b|\bwhat(?:'s| is) my ({_REL}) called\b|"
                  rf"\bwie heißt\s+(?:mein\w*|unser\w*)\s+({_REL})\b|\bwie hieß\s+(?:mein\w*)\s+({_REL})\b", low)
    if not m:
        return None
    rel = next(x for x in m.groups() if x)
    for key, r in (n.get("people") or {}).items():
        if r == rel:
            disp = (n.get("display") or {}).get(key) or key[:1].upper() + key[1:]
            return (f"{'Deine' if re.search(r'(?:in|schwester|mutter|mama|tante|oma|frau)$', rel) else 'Dein'} "
                    f"{rel[:1].upper() + rel[1:]} heißt {disp}.") if de else f"Your {rel} is called {disp}."
    return None


def _ans_who(n, low, de, now):
    m = re.match(r"(?:so |and |und |ok |okay )?(?:who|wer)(?:'s| is| was| hat| ist| war)?\s+(.+?)\??$", low)
    if not m or not n.get("did"):
        return None
    q = _words(m.group(1))
    if not q:
        return None
    scored = sorted(((len(q & _words(t)), i, p) for i, (p, t) in enumerate(n["did"])), reverse=True)
    if not scored or scored[0][0] == 0 or (len(scored) > 1 and scored[1][0] == scored[0][0] and scored[1][2] != scored[0][2]):
        return None
    person = scored[0][2]
    name = (n.get("display") or {}).get(person) or " ".join(w[:1].upper() + w[1:] for w in person.split())
    rel = (n.get("people") or {}).get(person, "")
    if de:
        return f"{name}{' – dein' + ('e' if re.search(r'(?:in|schwester|mutter|mama|tante|oma|cousine|frau|nichte)$', rel) else '') + ' ' + rel[:1].upper() + rel[1:] if rel else ''}."
    return f"{name}{', your ' + rel if rel else ''}."


def _ans_place(n, low, de, now):
    c = n.get("city")
    if not c:
        return None
    if re.search(r"\btime difference\b|\bzeitunterschied\b|\bzeitverschiebung\b", low):
        return _time_difference(c, low, de, now)
    if not re.search(r"\b(?:near me|nearby|near here|around here|close by|where i live|in my (?:city|area|town|neighbou?rhood)|"
                     r"in town|locally|local|in der nähe|bei mir|hier|in meiner (?:stadt|gegend|nähe)|um die ecke|in the area)\b",
                     low):
        return None
    m = re.search(r"\b(?:find|get|good|nice|best|a|an|any|ein\w*|gute\w*|schöne\w*|tolle\w*)\s+((?:[a-zäöüß]+\s+)?[a-zäöüß]{3,})\s+"
                  r"(?:near|nearby|around|in der|hier|bei|close|in town|in my|\?)", low + " ?")
    thing = m.group(1) if m and m.group(1) not in ("place", "places", "idea", "ideas", "tips", "way") else ""
    if de:
        what = f"{thing[:1].upper() + thing[1:]} in {c}" if thing else f"Angebote in {c}"
        return (f"Für {what} hab ich keine aktuellen Einträge – eine Karten-App oder die Website der Stadt {c} zeigt dir, "
                f"was in deiner Nähe liegt und gerade geöffnet hat.")
    what = f"a {thing} in {c}" if thing and not thing.endswith("s") else (f"{thing} in {c}" if thing else f"places in {c}")
    return (f"I don't have current local listings for {c} — a map app or the city's own website is the quickest way to "
            f"find {what} near you, with opening hours and reviews.")


def _zone(city: str):
    try:
        from zoneinfo import ZoneInfo, available_timezones
    except ImportError:
        return None
    key = city.strip().replace(" ", "_").lower()
    for z in sorted(available_timezones()):
        if z.split("/")[-1].lower() == key:
            return ZoneInfo(z)
    return None


def _time_difference(city: str, low: str, de: bool, now: datetime | None) -> str | None:
    m = re.search(r"\b(?:and|und|to|zu|nach)\s+([a-zäöüß]+(?:\s+[a-z]+)?)\s*\??$", low)
    if not m:
        return None
    other = m.group(1).title()
    za, zb = _zone(city), _zone(other)
    if za is None or zb is None:
        return None
    t = (now or datetime.now()).replace(tzinfo=None)
    off = (za.utcoffset(t) - zb.utcoffset(t)).total_seconds() / 3600
    h = _fmt_num(abs(off))
    if off == 0:
        return f"Keiner – {city} und {other} haben gerade dieselbe Uhrzeit." if de else \
            f"None — {city} and {other} are on the same time right now."
    ahead = city if off > 0 else other
    return f"{h} Stunden – {ahead} ist gerade {h} Stunden voraus." if de else f"{h} hours — {ahead} is {h} hours ahead right now."
