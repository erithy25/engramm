"""Follow-up questions to a web answer, made whole again.

    rewrite("And, Barcelona?", last, "en")          → "When was Barcelona founded?"   (another thing)
    rewrite("How old is he?", last, "en")            → "How old is Emmanuel Macron?"   (a pronoun)
    rewrite("Und die Einwohnerzahl?", last, "de")    → "Was ist die Einwohnerzahl von Berlin?"
    rewrite("How many people live there?", last, …)  → "How many people live in Paris?"

``last`` is what the dialog kept of the last web answer: the question, the thing it was about (as typed,
its name and Wikidata item), the relation, the answer and its items, and whether the answer is a person
or a place. Names the conversation already fixed come with their Wikidata item (``pin``): "he" is that
president, not a namesake. For another thing ("and Barcelona?") the item of the thing before goes along
(``like``): the same kind of thing is meant — the club after Real Madrid, not the city.

Nothing is rewritten unless the result is a question ``wiki.parse`` reads as being about the name put
in; everything else ("Is it raining?", "and why?") is left to the rest of the dialog.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from engramm.web.wiki import _DEMONYMS, RELATIONS, parse

# "and …", "what about …", "und …", "was ist mit …" — longer forms first
_AND = re.compile(r"^\s*(?:and\s+what\s+about|and\s+how\s+about|what\s+about|how\s+about|and\s+for|and\s+in|same\s+for|"
                  r"und\s+was\s+ist\s+mit|und\s+wie\s+ist\s+es\s+mit|und\s+wie\s+sieht\s+es\s+mit|wie\s+ist\s+es\s+mit|"
                  r"was\s+ist\s+mit|und\s+bei|und\s+für|dasselbe\s+für|also|and|und)\b\s*[,:;]?\s*"
                  r"(?P<x>[^?!.]{1,60}?)\s*[?!.]*\s*$", re.I)
_QWORDS = frozenset("""when who whom whose what where why how which is are was were does did do can will
wann wer wen wem wessen was wo woher wohin wie warum wieso weshalb welche welcher welches welchen ist sind hat
haben kann""".split())
# "Really?", "Ok?", "Thanks?" — a bare word that asks nothing about a new thing
_NOT_A_THING = frozenset("""really ok okay thanks thank sure why yes no nope yeah right sorry what huh hm hmm and or
but so also now then today tomorrow yesterday again too more less here there wirklich echt danke ja nein warum
wieso stimmt genau ehrlich bitte cool nice great super gut und oder aber also dann jetzt heute morgen gestern
nochmal wieder auch mehr weniger hier dort sonst noch""".split())
_TAIL = re.compile(r"\s+(?:then|now|though|too|as well|dann|denn|jetzt|auch|noch)$", re.I)
_LEAD = re.compile(r"^(?:of|for|in|about|von|für|bei|über|zu)\s+", re.I)
_ARTICLE = re.compile(r"^(?:the|a|an|der|die|das|den|dem|des|ein|eine|einen|einem)\s+", re.I)
_POSS_EN = re.compile(r"^(?:its|his|her|their)\s+", re.I)
_POSS_DE = {"sein": "der", "seine": "die", "seinen": "den", "seinem": "dem", "seiner": "der", "seines": "des",
            "ihr": "der", "ihre": "die", "ihren": "den", "ihrem": "dem", "ihrer": "der", "ihres": "des",
            "dessen": "der", "deren": "der"}
_PERSONAL = re.compile(r"\b(?:i|i'm|me|my|mine|you|your|yours|we|our|us|ich|mich|mir|mein\w*|du|dich|dir|dein\w*|wir|uns|"
                       r"unser\w*)\b", re.I)
# relations whose answer is a person ("Who is …") — the rest ask "What is …"
_PERSON_RELS = frozenset("ceo head_gov head_state coach founder author director composer painter architect inventor "
                         "spouse children winner".split())
# relations only a person has: "Wie alt ist er?" never asks how old Austria is
_PERSON_ONLY = frozenset("age birth death birthplace deathplace spouse children party nationality".split())
# a stop after a possessive's noun ("When was its stadium built?")
_VERBS = frozenset("""is was are were be been being built founded opened born made released located called named
die died do does did has have had ist war sind waren wurde wurden hat haben""".split())


@dataclass
class Followup:
    question: str                                  # the whole question: "When was Barcelona founded?"
    kind: str                                      # "subject" (another thing), "relation", "pronoun"
    lang: str = "en"                               # the language the question is written in
    pin: dict = field(default_factory=dict)        # names whose item is known: {"Emmanuel Macron": "Q3052772"}
    new: str = ""                                  # "subject": the new name ("Barcelona")
    like: str = ""                                 # "subject": the item of the thing before


def rewrite(message: str, last: dict, lang: str = "en") -> Followup | None:
    """The follow-up ``message`` as a whole question about what ``last`` was about, or None."""
    msg = " ".join(message.split())
    if not msg or not last or not last.get("question") or _PERSONAL.search(msg):
        return None
    m = _AND.match(msg)
    x = None
    if m:
        x = _TAIL.sub("", m.group("x").strip(" ,"))
        first = x.split()[0].lower() if x.split() else ""
        if first in _QWORDS:                       # "and when was it built?": a whole question after the "and"
            return _pronoun(x[:1].upper() + x[1:] + "?", last, lang)
    elif _bare(msg):
        x = msg.strip(" ?!.")
    if x:
        if re.match(r"^(?:its|his|her|their|sein\w*|ihr\w*|dessen|deren)\s", x, re.I):
            # "and his wife?", "und seine Frau?": whose — the pronoun decides (the president, not the country)
            rel = _rel_in(x)
            if rel is None:
                return None
            who = rel.key in _PERSON_RELS
            q = f"{'Wer' if who else 'Was'} ist {x}?" if lang == "de" else f"{'Who' if who else 'What'} is {x}?"
            return _pronoun(q, last, lang)
        return _relation(x, last, lang) or _subject(x, last)
    return _pronoun(msg, last, lang)


def _rel_in(text: str):
    """The relation a phrase names ("the population", "seine Frau"), or None."""
    return next((r for r in RELATIONS if (r.kw or r.rx).search(text)), None)


def _bare(msg: str) -> bool:
    """"Barcelona?" alone: up to four words, a name (capital letter), a question mark, no question word."""
    words = msg.strip(" ?!.").split()
    return (msg.rstrip().endswith("?") and 0 < len(words) <= 4 and words[0][:1].isupper()
            and words[0].lower() not in _QWORDS and words[0].lower().strip(",") not in _NOT_A_THING)


def _name(last: dict) -> str:
    """The thing the last answer was about, as the next question should name it: as typed ("Real
    Madrid"), else its name ("Deutschland" for an implied country, "Germany" for "German")."""
    typed = (last.get("typed") or "").strip()
    if typed and typed.lower() not in _DEMONYMS:
        return typed
    return (last.get("subject") or last.get("label") or "").strip()


def _relation(x: str, last: dict, lang: str) -> Followup | None:
    """"and the population?", "und der Trainer?", "and its CEO?": another question about the same thing."""
    rel = _rel_in(x)
    if rel is None:
        return None
    word = _POSS_EN.sub("", _ARTICLE.sub("", x)).strip()
    first = word.split()[0].lower() if word.split() else ""
    article = ""
    if first in _POSS_DE:                          # "seine Frau" → "die Frau"
        article, word = _POSS_DE[first], " ".join(word.split()[1:])
    elif lang == "de":
        a = re.match(r"^(der|die|das)\s+", x, re.I)
        article = a.group(1).lower() if a else ""
    rest = rel.kw.sub(" ", word) if rel.kw is not None else rel.rx.sub(" ", word)
    if rest.strip(" ,") or not word:
        return None                                # "Real Madrid's coach": a thing of its own, not a follow-up
    name = _name(last)
    if not name:
        return None
    who = rel.key in _PERSON_RELS
    if lang == "de":
        q = f"{'Wer' if who else 'Was'} ist {(article + ' ') if article else ''}{word} von {name}?"
    else:
        q = f"{'Who' if who else 'What'} is the {word} of {name}?"
    asked = parse(q, lang)
    if asked is None or asked.rel is None or asked.rel.key != rel.key or not _same(asked.subject, name):
        return None
    return Followup(q, "relation", lang, pin=_pin(name, last.get("qid")))


def _subject(x: str, last: dict) -> Followup | None:
    """"And, Barcelona?": the last question about another thing."""
    new = _LEAD.sub("", x).strip()
    bare = _ARTICLE.sub("", new).strip()
    if not bare or len(bare.split()) > 6 or bare.split()[0].lower() in _QWORDS or bare.lower() in _NOT_A_THING:
        return None
    q, lang = last["question"].strip(), last.get("lang") or "en"
    typed = (last.get("typed") or "").strip()
    if not re.search(r"[A-ZÄÖÜ]", bare) and re.search(r"[A-ZÄÖÜ]", typed or last.get("subject") or ""):
        return None                                # "how about pizza?" after "Real Madrid": no name, no follow-up
    of = "von" if lang == "de" else "of"
    if typed and typed.lower() in _DEMONYMS and re.search(rf"\b{re.escape(typed)}\b", q, re.I):
        # "Who is the German chancellor?" → "Who is the chancellor of Austria?"
        q = re.sub(rf"\s*\b{re.escape(typed)}\b", "", q, count=1, flags=re.I)
        q = re.sub(r"\s*([?!.]*)\s*$", rf" {of} {new}\1", q, count=1)
    elif typed and re.search(rf"\b{re.escape(typed)}\b", q, re.I):
        q = re.sub(rf"(?:\b(?:the|der|die|das|den|dem)\s+)?\b{re.escape(typed)}\b", lambda _m: new, q, count=1, flags=re.I)
    else:                                          # the thing was implied: "Wer ist der aktuelle Bundeskanzler?"
        q = re.sub(r"\s*([?!.]*)\s*$", rf" {of} {new}\1", q, count=1)
    if not q.endswith(("?", ".", "!")):
        q += "?"
    q = q[:1].upper() + q[1:]
    asked = parse(q, lang)
    if asked is None or not _same(asked.subject, bare):
        return None
    if last.get("rel") and (asked.rel is None or asked.rel.key != last["rel"]):
        return None                                # the new name changed what is asked: no follow-up
    return Followup(q, "subject", lang, new=asked.subject, like=last.get("qid") or "")


def _pronoun(msg: str, last: dict, lang: str) -> Followup | None:
    """"How old is he?", "When was it founded?", "Wie viele Einwohner leben dort?": the pronoun replaced
    by what it refers to — the answer when that was a person (or a place, for "there"), else the thing."""
    subject, qid = _name(last), last.get("qid") or ""
    values = list(last.get("values") or [])
    answer = (last.get("answer") or "").strip()
    single = bool(answer) and not re.search(r",|\band\b|\bund\b", answer)
    person = (answer, values[0] if len(values) == 1 else "") if last.get("person") and single else None
    if person is None and last.get("subject_person") and subject:
        person = (subject, qid)
    thing = (subject, qid) if subject else None
    place = (answer, values[0] if len(values) == 1 else "") if last.get("place") and single else thing
    tries: list[tuple[str, tuple | None]] = []
    words = msg.split()
    for i, w in enumerate(words):
        low = w.lower().strip(",;:?!.")
        nxt = words[i + 1] if i + 1 < len(words) else ""
        if low in ("its", "his", "her", "their") and nxt and nxt.lower().strip("?!.,") not in _VERBS:
            ref = thing if low in ("its", "their") and not last.get("subject_person") else \
                person if low in ("his", "her") else (thing if not last.get("subject_person") else None)
            tries.append(("poss-en", ref))
        elif low in _POSS_DE and nxt[:1].isupper():
            ref = person if person and low.startswith(("sein", "ihr")) and last.get("person") else (thing or person)
            tries.append(("poss-de", ref))
        elif low in ("he", "him", "she"):
            tries.append(("pron", person))
        elif low in ("it", "they", "them"):
            tries.append(("pron", thing if not last.get("subject_person") or low == "it" else None))
        elif low in ("er", "ihn", "ihm"):
            tries.append(("pron", person or (thing if not last.get("subject_person") else None)))
        elif low == "sie":
            tries.append(("pron", person or thing))
        elif low == "es":
            tries.append(("pron", thing))
        elif low in ("there", "dort", "dorthin") and not re.search(r"\bthere\s+(?:is|are|was|were)\b", msg, re.I):
            tries.append(("place", place))
        else:
            continue
        break                                      # the first pronoun decides
    if not tries or tries[0][1] is None or not tries[0][1][0]:
        return None
    how, ref = tries[0]
    name, item = ref
    is_person = person is not None and ref is person
    de = lang == "de"
    if how == "poss-en":
        m = re.search(r"\b(its|his|her|their)\s+((?:(?!\b(?:" + "|".join(_VERBS) + r")\b)[\w'’-]+\s*){1,3})", msg, re.I)
        if not m:
            return None
        q = msg[:m.start()] + f"the {m.group(2).strip()} of {name}" + (" " if msg[m.end():][:1].isalnum() else "") + \
            msg[m.end():].lstrip()
    elif how == "poss-de":
        m = re.search(r"\b(" + "|".join(_POSS_DE) + r")\s+([A-ZÄÖÜ][\w-]*)", msg)
        if not m:
            return None
        q = msg[:m.start()] + f"{_POSS_DE[m.group(1).lower()]} {m.group(2)} von {name}" + msg[m.end():]
    elif how == "place":
        q = re.sub(r"\b(there|dort|dorthin)\b", f"in {name}", msg, count=1, flags=re.I)
    else:
        pron = r"\b(he|him|she|it|they|them)\b" if not de else r"\b(er|ihn|ihm|sie|es)\b"
        q = re.sub(pron, name, msg, count=1, flags=re.I)
        if q == msg and de:                        # an English pronoun in a German conversation, or the reverse
            q = re.sub(r"\b(he|him|she|it|they|them|er|ihn|ihm|sie|es)\b", name, msg, count=1, flags=re.I)
    q = q[:1].upper() + q[1:]
    if not q.rstrip().endswith(("?", ".", "!")):
        q = q.rstrip() + "?"
    asked = parse(q, lang)
    if asked is None or not _same(asked.subject, name):
        return None
    if asked.rel is not None and asked.rel.key in _PERSON_ONLY and not is_person:
        return None                                # "how old is it?" about a country: no question about a person
    return Followup(q, "pronoun", lang, pin=_pin(name, item))


def _same(subject: str, name: str) -> bool:
    """The question's thing is the name put in (articles and case aside)."""
    a = " ".join(_ARTICLE.sub("", subject or "").lower().split())
    b = " ".join(_ARTICLE.sub("", name or "").lower().split())
    return bool(a) and (a == b or a == b.rstrip("s") or a in _DEMONYMS and _DEMONYMS[a].lower() == b)


def _pin(name: str, item: str | None) -> dict:
    return {name: item} if name and item and re.fullmatch(r"Q\d+", item) else {}
