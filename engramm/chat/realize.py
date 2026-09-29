"""Whole sentences instead of bare answer snippets.

"Who invented the telephone?" + "Alexander Graham Bell" → "Alexander Graham Bell invented the
telephone." The question is turned into its statement by rules: the wh-word is replaced by the
answer (subject questions), or the auxiliary moves back behind the subject and the answer goes
where the wh-word stood (object and adverb questions: "Where was X born?" → "X was born in …";
"When did X die?" → "X died in …", with the past tense from a table of irregular verbs).

When no rule fits cleanly the realiser does not guess: ``answer_sentence`` returns ``None`` and
the caller uses a plain fallback. Also here: answers about you in the second person ("Your
dog is called Rex."), and turning your own sentences into "you" sentences.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# verbs
# ---------------------------------------------------------------------------

_IRREGULAR = """
arise arose arisen|awake awoke awoken|be was been|bear bore born|beat beat beaten|become became become|
begin began begun|bend bent bent|bet bet bet|bind bound bound|bite bit bitten|bleed bled bled|blow blew blown|
break broke broken|breed bred bred|bring brought brought|broadcast broadcast broadcast|build built built|
burn burnt burnt|burst burst burst|buy bought bought|cast cast cast|catch caught caught|choose chose chosen|
cling clung clung|come came come|cost cost cost|creep crept crept|cut cut cut|deal dealt dealt|dig dug dug|
do did done|draw drew drawn|dream dreamt dreamt|drink drank drunk|drive drove driven|eat ate eaten|
fall fell fallen|feed fed fed|feel felt felt|fight fought fought|find found found|flee fled fled|fly flew flown|
forbid forbade forbidden|forget forgot forgotten|forgive forgave forgiven|freeze froze frozen|get got gotten|
give gave given|go went gone|grind ground ground|grow grew grown|hang hung hung|have had had|hear heard heard|
hide hid hidden|hit hit hit|hold held held|hurt hurt hurt|keep kept kept|kneel knelt knelt|know knew known|
lay laid laid|lead led led|lean leant leant|leap leapt leapt|learn learnt learnt|leave left left|lend lent lent|
let let let|lie lay lain|light lit lit|lose lost lost|make made made|mean meant meant|meet met met|pay paid paid|
put put put|quit quit quit|read read read|ride rode ridden|ring rang rung|rise rose risen|run ran run|
say said said|see saw seen|seek sought sought|sell sold sold|send sent sent|set set set|shake shook shaken|
shed shed shed|shine shone shone|shoot shot shot|show showed shown|shrink shrank shrunk|shut shut shut|
sing sang sung|sink sank sunk|sit sat sat|sleep slept slept|slide slid slid|speak spoke spoken|speed sped sped|
spend spent spent|spin spun spun|split split split|spread spread spread|spring sprang sprung|stand stood stood|
steal stole stolen|stick stuck stuck|sting stung stung|strike struck struck|strive strove striven|
swear swore sworn|sweep swept swept|swim swam swum|swing swung swung|take took taken|teach taught taught|
tear tore torn|tell told told|think thought thought|throw threw thrown|understand understood understood|
undertake undertook undertaken|upset upset upset|wake woke woken|wear wore worn|weave wove woven|weep wept wept|
win won won|wind wound wound|withdraw withdrew withdrawn|write wrote written|overcome overcame overcome|
overtake overtook overtaken|undergo underwent undergone|foresee foresaw foreseen|mislead misled misled|
outgrow outgrew outgrown|rebuild rebuilt rebuilt|rewrite rewrote rewritten|uphold upheld upheld|
withstand withstood withstood|found founded founded|wed wed wed|slay slew slain|sew sewed sewn|
saw sawed sawn|lend lent lent|forsake forsook forsaken|dwell dwelt dwelt|spell spelt spelt|spit spat spat
"""
PAST: dict[str, str] = {}
PARTICIPLE: dict[str, str] = {}
for _entry in _IRREGULAR.replace("\n", "").split("|"):
    _p = _entry.split()
    if len(_p) == 3:
        PAST.setdefault(_p[0], _p[1])
        PARTICIPLE.setdefault(_p[0], _p[2])
# American forms people expect in answers
PAST.update({"learn": "learned", "burn": "burned", "dream": "dreamed", "lean": "leaned", "leap": "leaped",
             "spell": "spelled", "dwell": "dwelled", "light": "lit"})
PARTICIPLE.update({"learn": "learned", "burn": "burned", "dream": "dreamed", "get": "got"})
_PARTICIPLES = frozenset(PARTICIPLE.values()) | frozenset(("born", "located", "situated", "based", "called",
                                                           "named", "known", "buried", "held", "founded"))
_DOUBLE = frozenset("admit commit control occur prefer refer regret stop plan drop ship rob beg drag grab hug "
                    "nod pat plot rub scrub shop skip slip step stir tap trip wrap chat jog knit omit permit "
                    "submit transmit compel expel propel rebel travel label model cancel".split())


def past_tense(verb: str) -> str:
    v = verb.lower()
    if v in PAST:
        return PAST[v]
    if v.endswith("e"):
        return v + "d"
    if re.search(r"[^aeiou]y$", v):
        return v[:-1] + "ied"
    if v in _DOUBLE or re.fullmatch(r"[^aeiou]*[aeiou][bdgmnpt]", v):
        return v + v[-1] + "ed"
    return v + "ed"


def third_person(verb: str) -> str:
    v = verb.lower()
    special = {"be": "is", "have": "has", "do": "does", "go": "goes"}
    if v in special:
        return special[v]
    if re.search(r"(s|sh|ch|x|z|o)$", v):
        return v + "es"
    if re.search(r"[^aeiou]y$", v):
        return v[:-1] + "ies"
    return v + "s"


def _load_verbs() -> frozenset:
    from pathlib import Path
    path = Path(__file__).resolve().parent / "data" / "verbs.txt"
    out = set(PAST)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            out.update(line.split())
    return frozenset(out)


VERBS = _load_verbs()
_FORMS: dict[str, str] = {}
for _v in VERBS:
    for _f in (_v, past_tense(_v), PARTICIPLE.get(_v, past_tense(_v)), third_person(_v),
               (_v[:-1] if _v.endswith("e") and not _v.endswith("ee") else _v) + "ing"):
        _FORMS.setdefault(_f, _v)


def verb_base(word: str) -> str | None:
    """The base form if ``word`` is a form of a known verb ("founded" → "found")."""
    return _FORMS.get(word.lower())


_NOT_PARTICIPLE = frozenset("hundred sacred naked wicked kindred red bed need seed feed speed breed shed shred wed "
                            "embed indeed deed weed steed greed creed bred fled led fed sped".split())


def is_participle(word: str) -> bool:
    w = word.lower()
    if w in _PARTICIPLES:
        return True
    b = _FORMS.get(w)
    if b is not None:
        return w in (PARTICIPLE.get(b), past_tense(b)) and w != b
    # unknown verbs: a regular "-ed" form ("grouped", "overprinted")
    return len(w) >= 6 and w.endswith("ed") and w not in _NOT_PARTICIPLE and w.isalpha()


# ---------------------------------------------------------------------------
# questions → statements
# ---------------------------------------------------------------------------

_AUX = {"is", "are", "was", "were", "has", "have", "had", "can", "could", "will", "would", "should", "may", "might",
        "must", "shall"}
_DO = {"do", "does", "did"}
_PLURAL_PRON = {"they", "we", "you", "i"}
_MONTHS = ("january|february|march|april|may|june|july|august|september|october|november|december|"
           "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec")
_PREP_START = re.compile(r"^(?:in|on|at|from|near|by|during|since|after|before|to|into|inside|outside|under|over|"
                         r"around|about|between|through|within|off|for|of|with)\b", re.I)


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _clean_q(q: str) -> str:
    q = q.strip()
    q = re.sub(r"^(?:and|so|but|ok|okay|well|hey|then|also)\b[,]?\s+", "", q, flags=re.I)
    q = re.sub(r"\s*\?+\s*$", "", q)
    q = re.sub(r"^(?:do you know|can you tell me|could you tell me|tell me|i wonder|any idea|remind me)\s*,?\s*",
               "", q, flags=re.I)
    return q.strip().rstrip(",")


def _date_prep(answer: str) -> str:
    a = answer.strip()
    low = a.lower()
    if re.match(r"^(?:about|around|circa|c\.|approximately|roughly|nearly|almost|early|late)\s+\d", low):
        return "in " + a
    if _PREP_START.match(a):
        return a
    if re.search(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:" + _MONTHS + r")\b|\b(?:" + _MONTHS + r")\s+\d{1,2}(?:st|nd|rd|th)?\b",
                 low):
        return "on " + a
    if re.fullmatch(r"(?:the )?\d{1,2}(?:st|nd|rd|th)? century|(?:the )?\d{3,4}s|\d{3,4}(?:\s*(?:bc|bce|ad|ce))?|"
                    r"(?:early |late |mid-?)?(?:" + _MONTHS + r")(?:\s+\d{4})?|(?:spring|summer|autumn|fall|winter)"
                    r"(?: of)?(?: \d{4})?", low):
        return "in " + a
    if re.match(r"^(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)", low):
        return "on " + a
    return "in " + a


def _place_prep(answer: str) -> str:
    return answer if _PREP_START.match(answer) else "in " + answer


def _subject_is_plural(np: str) -> bool:
    w = np.lower().split()
    if not w:
        return False
    if w[0] in _PLURAL_PRON:
        return True
    return bool(re.search(r"(?<!s)s$", w[-1])) and w[-1] not in ("is", "was", "has", "its", "this", "series",
                                                                  "species", "news", "physics", "mathematics")


_STRANDED = frozenset(("by", "for", "in", "after", "to", "with", "from", "on", "at", "as", "into", "of", "about"))
_DETS = frozenset(("the", "a", "an", "his", "her", "their", "its", "this", "that", "these", "those", "some", "many",
                   "most", "each", "every", "our", "my", "your"))


def _split_np_verb(rest: str, mid: bool = False) -> tuple[str, str, str] | None:
    """A passive ending in a participle, optionally with a stranded preposition:
    'Alexander Graham Bell born' → ('Alexander Graham Bell', 'born', ''),
    'the administration which governed the City of London called' → (…, 'called', ''),
    'X named after' → ('X', 'named', 'after')."""
    ws = rest.split()
    if re.search(r"\b(?:has|have|had) been\b|\band (?:has|have|had|is|was|are|were)\b", rest):
        return None
    if len(ws) >= 2 and is_participle(ws[-1]) and not ws[-1][:1].isupper():
        return " ".join(ws[:-1]), ws[-1], ""
    if len(ws) >= 3 and ws[-1].lower() in _STRANDED and is_participle(ws[-2]) and not ws[-2][:1].isupper():
        return " ".join(ws[:-2]), ws[-2], ws[-1].lower()
    # "the West Bank annexed by Jordan" (where/when questions): the participle, then a phrase
    # starting with a preposition
    for i in range(1, len(ws) - 1 if mid else 0):
        if is_participle(ws[i]) and not ws[i][:1].isupper() and ws[i + 1].lower() in _STRANDED | {"to"}:
            return " ".join(ws[:i]), " ".join(ws[i:]), ""
    return None


def _do_split(rest: str) -> tuple[str, str, str] | None:
    """'Marie Curie win the Nobel Prize' → ('Marie Curie', 'win', 'the Nobel Prize'): after
    do-support the verb is the first known verb in base form after the subject."""
    ws = rest.split()
    if len(ws) < 2:
        return None
    for i in range(1, len(ws)):
        w = ws[i]
        if w[:1].isupper():
            continue
        lw = w.lower()
        if lw in VERBS or (lw.endswith("ed") and verb_base(lw)):
            if ws[i - 1].lower() in _DETS or ws[i - 1].lower() in _STRANDED:
                continue                       # "the start", "of use": a noun
            return " ".join(ws[:i]), lw, " ".join(ws[i + 1:])
    return None


def _finite(aux: str, verb: str) -> str:
    if verb.endswith("ed") and verb_base(verb) and verb != verb_base(verb):
        return verb                            # "did … intermarried": already past
    if aux == "did":
        return past_tense(verb)
    if aux == "does":
        return third_person(verb)
    return verb


_ADVERBS = frozenset("often usually also commonly frequently sometimes still generally typically widely mostly "
                     "primarily mainly largely originally first later then now currently always never once "
                     "traditionally historically officially formally".split())
_NUMBERS = frozenset("two three four five six seven eight nine ten eleven twelve several many few one both".split())


def _object_question(rest: str) -> bool:
    """'The Times aggressively selling to …' — a subject of its own and a verb later: the
    wh-word was the object, so replacing it would be wrong."""
    ws = rest.split()
    if len(ws) < 2:
        return False
    starts_np = ws[0][:1].isupper() or ws[0].lower() in _DETS
    later_verb = any((w.lower().endswith("ing") or is_participle(w)) and verb_base(w) for w in ws[1:])
    return starts_np and later_verb and not is_participle(ws[0])


def _agree(answer: str, verb: str) -> str:
    """'Luddi, Bhangra and Sammi' + 'sings' → 'sing' (a plural subject takes the plain verb)."""
    v = verb.lower()
    if not re.search(r"\band\b", answer):
        return verb
    plural = {"is": "are", "was": "were", "has": "have"}
    if v in plural:
        return plural[v]
    if v.endswith("s") and verb_base(v) and verb_base(v) != v and third_person(verb_base(v)) == v:
        return verb_base(v)
    return verb


def answer_sentence(question: str, answer: str, atype: str | None = None) -> str | None:
    """A statement that answers ``question`` with ``answer``, or None when no rule fits."""
    q = _clean_q(question)
    a = answer.strip().rstrip(".")
    if not q or not a:
        return None
    ws = q.split()
    if len(ws) < 2:
        return None
    # "In what year did X …?" / "What year did X …?" → "When did X …?"
    q = re.sub(r"^(?:in |on |during )?(?:what|which) (?:year|date|month|day|century|decade|time period)\b\s*",
               "When ", q, flags=re.I)
    ws = q.split()
    wh = ws[0].lower()

    # "By whom was X founded?" → "X was founded by A."
    m = re.fullmatch(r"by whom (is|was|were|are) (.+?) (\w+)", q, flags=re.I)
    if m:
        return _cap(f"{m.group(2)} {m.group(1).lower()} {m.group(3)} by {a}.")
    # "Who was X written by?" / "Who is X directed by?" → "X was written by A."
    m = re.fullmatch(r"(?:who|what) (is|was|were|are) (.+?) (\w+) by", q, flags=re.I)
    if m:
        return _cap(f"{m.group(2)} {m.group(1).lower()} {m.group(3)} by {a}.")

    if re.match(r"^(?:is|was|are|were|has|have|had|do|does|did|will|would|can|could)\b", a, flags=re.I):
        return None                            # the answer is a clause fragment, not a phrase
    if wh in ("who", "what", "which"):
        second = ws[1].lower()
        if wh in ("which", "what") and second not in _AUX | _DO:
            # "Which river flows through Paris?" / "Which city is the centre of …?": one noun, then the verb
            if len(ws) < 3 or second in _NUMBERS or not re.fullmatch(r"[a-z]+", second):
                return None
            nxt = ws[2].lower()
            if nxt in _DO:
                return None                    # "Which book did X write" — object question
            if nxt in _AUX:
                rest = " ".join(ws[3:])
                if not rest or _object_question(rest):
                    return None
                return _cap(f"{a} {nxt} {rest}.")
            base = verb_base(nxt)
            if base and nxt != base or (base and nxt.endswith("s")):
                return _cap(f"{a} {_agree(a, nxt)} {' '.join(ws[3:])}".rstrip() + ".")
            return None
        if second in _DO:
            # "What did Kanye record?" → "Kanye recorded Graduation."
            sp = _do_split(" ".join(ws[2:]))
            if not sp or sp[2]:
                return None
            subj, verb, _ = sp
            return _cap(f"{subj} {_finite(second, verb)} {a}.")
        if second in _AUX:
            rest = " ".join(ws[2:])
            if not rest:
                return None
            first = rest.split()[0].lower()
            if is_participle(first) or (first.endswith("ly") or first in _ADVERBS) and len(rest.split()) > 1:
                # "Who was wounded in the attack?" → "A was wounded in the attack."
                return _cap(f"{a} {_agree(a, second)} {rest}.")
            sp = _split_np_verb(rest)
            if sp:
                subj, part, tail = sp
                tail = f" {tail}" if tail else ""
                if part.lower() in ("born", "located", "situated", "based", "buried", "held") and not tail:
                    prep = _date_prep(a) if atype == "DATE" else _place_prep(a)
                    return _cap(f"{subj} {second} {part} {prep}.")
                return _cap(f"{subj} {second} {part}{tail} {a}.")
            if second in ("is", "was", "are", "were"):
                if _object_question(rest) or re.match(r"^(?:it|this|that|there|he|she|they)\b", rest, flags=re.I):
                    return None
                # "What was the Manhattan Project?" + "a research programme" → "The Manhattan Project was …"
                if re.match(r"^(?:a|an|one of|some|any)\b", a, flags=re.I) or (wh == "what" and a[:1].islower()
                                                                              and not re.search(r"\d", a)):
                    return _cap(f"{rest} {second} {a}.")
                # "Who is the president of France?" / "What is the capital of Italy?" → "A is …"
                if wh == "who" or re.match(r"^(?:the|a|an)\b", rest, flags=re.I):
                    return _cap(f"{a} {_agree(a, second)} {rest}.")
            return None
        # subject question: "Who invented the telephone?" → "A invented the telephone."
        if verb_base(second) and second not in ("of", "in", "on", "at", "for", "to", "from", "about"):
            return _cap(f"{a} {_agree(a, second)} {' '.join(ws[2:])}".rstrip() + ".")
        return None

    if wh in ("where", "when"):
        if len(ws) < 3:
            return None
        second = ws[1].lower()
        rest = " ".join(ws[2:])
        if re.search(r"\bnot\b|n't\b", rest):
            return None
        prep = _date_prep(a) if (wh == "when" or atype == "DATE") else _place_prep(a)
        if second in _DO:
            sp = _do_split(rest)
            if not sp:
                return None
            subj, verb, tail = sp
            form = _finite(second, verb)
            if tail and tail.split()[-1].lower() in _STRANDED:
                return _cap(f"{subj} {form} {tail} {a}.")        # "… get its name from" + A
            tail = f" {tail}" if tail else ""
            return _cap(f"{subj} {form}{tail} {prep}.")
        if second in _AUX:
            sp = _split_np_verb(rest, mid=True)
            if sp:
                subj, part, tail = sp
                if tail:
                    return _cap(f"{subj} {second} {part} {tail} {a}.")
                return _cap(f"{subj} {second} {part} {prep}.")
            if second in ("is", "was", "are", "were") and not _object_question(rest):
                # "Where is Timbuktu?" → "Timbuktu is in Mali." / "When was the Battle of Hastings?"
                if len(rest.split()) <= 8 and not any(verb_base(w) and w.endswith("ing") for w in rest.lower().split()):
                    return _cap(f"{rest} {second} {prep}.")
            return None
        return None

    if wh == "how":
        m = re.fullmatch(r"how (many|much) (.+?) (does|do|did) (.+)", q, flags=re.I)
        if m and re.fullmatch(r"(?:about |around |over |nearly |almost )?-?[\d.,]+(?:\s*(?:million|billion|thousand|"
                              r"hundred))?", a, flags=re.I):
            noun, aux = m.group(2), m.group(3).lower()
            sp = _do_split(m.group(4))
            if sp:
                subj, verb, tail = sp
                tail = f" {tail}" if tail else ""
                return _cap(f"{subj} {_finite(aux, verb)} {a} {noun}{tail}.")
            return None
        m = re.fullmatch(r"how (tall|high|long|deep|wide|big|large|far|heavy|old) (is|was|are|were) (.+)", q, flags=re.I)
        if m and re.search(r"\d", a) and not re.search(r"\b(?:when|after|before|while|at the time|if)\b", m.group(3)):
            adj, aux, subj = m.group(1).lower(), m.group(2).lower(), m.group(3)
            if adj == "old":
                return _cap(f"{subj} {aux} {a}{'' if re.search(r'[a-z]', a, re.I) else ' years'} old.")
            return _cap(f"{subj} {aux} {a} {adj}.")
        return None
    return None


# ---------------------------------------------------------------------------
# you and me
# ---------------------------------------------------------------------------

_FLIP = {"i": "you", "me": "you", "my": "your", "mine": "yours", "myself": "yourself", "i'm": "you're",
         "i've": "you've", "i'll": "you'll", "i'd": "you'd", "am": "are", "we": "you", "us": "you", "our": "your",
         "ours": "yours", "ourselves": "yourselves", "we're": "you're", "we've": "you've", "we'll": "you'll",
         "im": "you're"}


def to_second_person(sentence: str) -> str | None:
    """"My name is Erik!" → "Your name is Erik." ; None if the sentence speaks to "you" (then a
    flip would be ambiguous)."""
    s = sentence.strip().replace("’", "'")
    if re.search(r"\b(you|your|yours|yourself)\b", s, flags=re.I):
        return None
    out = []
    toks = re.findall(r"[\w']+|[^\w\s]", s)
    prev = ""
    for t in toks:
        low = t.lower()
        if low == "was" and prev in ("i",):
            rep = "were"
        elif low in _FLIP:
            rep = _FLIP[low]
            if low == "am" and prev not in ("i",):
                rep = t
        else:
            rep = t
        if t[:1].isupper() and rep != t and low != "i":
            rep = _cap(rep)
        out.append(rep)
        prev = low
    text = ""
    for t in out:
        if re.fullmatch(r"[^\w\s]", t) and t not in ("(", "“", '"'):
            text += t
        else:
            text += (" " if text else "") + t
    text = _cap(text.strip())
    text = re.sub(r"[!?]+$", ".", text)
    if not re.search(r"[.!?]$", text):
        text += "."
    return text


_CATEGORY_ANSWER = {
    "#name": "Your name is {x}.",
    "#home": "You live in {x}.",
    "#job": "You work as {x}.",
    "#employer": "You work for {x}.",
    "#food": "Your favourite food is {x}.",
    "#colour": "Your favourite colour is {x}.",
    "#car": "You drive a {x}.",
    "#birth": "Your birthday is {x}.",
    "#origin": "You're from {x}.",
}
_OWNED_NAME = "Your {noun} is called {x}."


def article(noun: str) -> str:
    n = noun.strip()
    if re.match(r"^(?:a|an|the|my|your|his|her|their|our)\b", n, flags=re.I) or n[:1].isupper():
        return n
    return ("an " if re.match(r"^[aeiou]", n, flags=re.I) and not re.match(r"^(?:uni|use|eu|one)", n, flags=re.I)
            else "a ") + n


def personal_sentence(subject: str, relation, value: str, evidence: str | None) -> str:
    """How ENGRAMM tells you something you told it: category sentences first ("Your name is
    Erik."), then your own sentence in the second person, then a quote."""
    rel = set(relation or ())
    if subject == "USER":
        for cat, tpl in _CATEGORY_ANSWER.items():
            if cat in rel:
                x = article(value) if cat == "#job" else value
                return tpl.format(x=x)
    elif subject.startswith("USER:") and "#name" in rel:
        return _OWNED_NAME.format(noun=subject.partition(":")[2], x=value)
    if evidence:
        flipped = to_second_person(evidence)
        if flipped and value.lower() in flipped.lower() and len(flipped.split()) <= 30:
            return flipped
        return f"{value} — you told me: “{evidence.strip()}”"
    return f"{value}."
