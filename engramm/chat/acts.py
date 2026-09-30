"""What a message does: the dialogue-act router.

A message is split into sentences ("Hi! The name's Tamlolo." → greeting + statement); each
sentence gets one act, decided by rules in this order:

1. safety   — a crisis or a request ENGRAMM refuses (checked on the whole message first);
2. forget   — "forget …", "please delete what I told you about …";
3. remember — "remember that …", "note that …";
4. tool     — arithmetic, unit conversion, dates and times;
5. intent   — a small-talk or persona pattern from the bank ("how are you", "tell me a joke");
6. about    — "tell me about X", "what is X", "who was X", "explain X";
7. feeling  — you speak about yourself and name a feeling or an event ("I'm so tired");
8. question — ends with "?" or starts with a question word;
9. statement — everything else (the dialog decides: remember it, or just react).

Short statements that no pattern matched may still reach an intent through the most similar
example in the bank (letter trigrams and words), e.g. "hey how r ya" → how_are_you.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from engramm.chat.bank import Bank, load_bank, normalise
from engramm.chat.bot import forget_topic, message_type
from engramm.chat.tools import ToolResult, tool_answer

NEAREST_MIN = 0.55            # similarity an example needs to decide a short message
NEAREST_MAX_WORDS = 5


@dataclass
class Unit:
    act: str                  # safety forget remember tool intent about feeling question statement empty
    text: str                 # the sentence as written
    norm: str = ""            # its normalised form
    intent: str | None = None
    groups: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# sentences
# ---------------------------------------------------------------------------

_ABBR = frozenset("mr mrs ms dr st jr sr prof vs etc e.g i.e u.s u.k no mt ft co inc ltd jan feb mar apr jun jul aug "
                  "sep sept oct nov dec approx ca gen col lt sgt rev fig vol".split())
_LEAD_GREETING = re.compile(r"^((?:hi+|hello+|hey+|hiya|howdy|yo|greetings|good (?:morning|afternoon|evening))"
                            r"(?: there| again| engramm)?)\s*[,!.]+\s+(?=\S)", re.I)
_LEAD_THANKS = re.compile(r"^((?:thanks|thank you|thx|cheers)(?: (?:a lot|so much|very much))?)\s*[,!.]+\s+(?=\S)", re.I)


def split_sentences(text: str) -> list[str]:
    """Sentences of a chat message. Splits after . ! ? (and before a new capitalised word or
    any word after ! and ?), not after abbreviations or initials; a leading greeting or thanks
    with a comma ("Hi, I'm Ada") becomes its own sentence."""
    text = " ".join(text.split())
    if not text:
        return []
    out = []
    for rx in (_LEAD_GREETING, _LEAD_THANKS):
        m = rx.match(text)
        if m:
            out.append(m.group(1))
            text = text[m.end():]
            break
    parts, start = [], 0
    for m in re.finditer(r"([.!?…]+)[\"')\]”’]*\s+", text):
        end = m.end()
        punct = m.group(1)
        before = text[start:m.start()].split()
        last = before[-1].lower().rstrip(".") if before else ""
        nxt = text[end:end + 1]
        if punct == ".":
            if last in _ABBR or (len(last) == 1 and last.isalpha()) or re.fullmatch(r"\d+", last) and nxt.isdigit():
                continue
            if not (nxt.isupper() or nxt.isdigit() or nxt in "\"'“‘(" or nxt.islower()):
                continue
        parts.append(text[start:end].strip())
        start = end
    if start < len(text):
        parts.append(text[start:].strip())
    return out + [p for p in parts if p]


# ---------------------------------------------------------------------------
# patterns
# ---------------------------------------------------------------------------

_REMEMBER = re.compile(r"^(?:(?:please|pls|can you|could you|would you|i want you to|i'd like you to)\s+)*"
                       r"(?:remember|don't forget|do not forget|note|take note|keep in mind|memori[sz]e|save|store|"
                       r"write down|make a note)(?:\s+(?:that|this|of this|down))?\s*[:,]?\s+(?P<x>.{3,})$", re.I)
_ABOUT = [
    ("tell", re.compile(r"^(?:(?:can|could|would) you |please )*(?:explain|describe|tell me)(?: to me)? (?:how|why) "
                        r"(?:do |does |did |is |are )?(?:an? |the )?(?P<x>[a-z][\w\- ]*?)s? (?:work|works|function|happen|form|exist)s?$", re.I)),
    ("tell", re.compile(r"^how (?:do|does|did|is|are) (?:an? |the )?(?P<x>[a-z][\w\- ]*?)s? (?:work|works|function|happen|form)$", re.I)),
    ("tell", re.compile(r"^(?:(?:can|could|would) you |please |pls )*(?:tell|teach|inform) me(?: something| a (?:bit|little)"
                        r"| a few things| more| all| everything| some facts)? about (?P<x>.+)$", re.I)),
    ("tell", re.compile(r"^(?:(?:can|could|would) you |please )*talk(?: to me)? about (?P<x>.+)$", re.I)),
    ("tell", re.compile(r"^what (?:do|can) you (?:know|tell me|say) about (?P<x>.+)$", re.I)),
    ("tell", re.compile(r"^(?:(?:can|could|would) you |please )*(?:explain|describe)(?: to me)?(?: what)? (?P<x>.+?)"
                        r"(?: is| are| means| was| were)?$", re.I)),
    ("define", re.compile(r"^what (?:does|do) (?:the (?:abbreviation|acronym) )?(?P<x>[A-Za-z0-9.\-]{2,12}) stand for$", re.I)),
    ("define", re.compile(r"^(?:(?:can|could|would) you |please )*define (?P<x>.+)$", re.I)),
    ("define", re.compile(r"^what (?:does|do) (?:the (?:word|term) )?(?P<x>.+?) mean$", re.I)),
    ("define", re.compile(r"^what(?:'s| is) (?:the )?(?:meaning|definition) of (?:the (?:word|term) )?(?P<x>.+)$", re.I)),
    ("tell", re.compile(r"^(?:do you know|have you (?:ever )?heard of|ever heard of|you know) (?P<x>.+)$", re.I)),
    ("tell", re.compile(r"^(?:information|info|facts|details) (?:on|about) (?P<x>.+)$", re.I)),
    ("opinion", re.compile(r"^what do you think (?:about|of) (?P<x>.+)$", re.I)),
    ("opinion", re.compile(r"^what(?:'s| is) your (?:opinion|view|take|stance) (?:on|of|about) (?P<x>.+)$", re.I)),
    ("opinion", re.compile(r"^(?:do you like|do you love|are you a fan of|how do you feel about) (?P<x>.+)$", re.I)),
    ("what", re.compile(r"^(?:what|who)(?:'s| is| are| was| were) (?P<x>.+)$", re.I)),
]
_RELATIONAL = re.compile(r"\b(?:of|in|on|at|for|from|by|to|with|about|between|than|during|after|before|since|"
                         r"who|which|that|when|where|whose|did|does|do|has|have|had|can|will|would|should|my|your|"
                         r"his|her|their|its|our|this|these|those|first|last|best|biggest|largest|smallest|"
                         r"highest|tallest|longest|oldest|youngest|most|least|next|current|name)\b", re.I)
_FIRST_PERSON = re.compile(r"\b(?:i|i'm|i've|i'd|i'll|me|my|mine|myself|we|we're|we've|us|our|ours)\b")
_WHY_ME = re.compile(r"^(?:why|how come) (?:am|do|did|can't|cannot|don't|does|is) (?:i|my)\b")


def _clean(sentence: str) -> str:
    s = sentence.strip().replace("’", "'").replace("‘", "'")
    s = re.sub(r"[\s?!.…]+$", "", s)
    s = re.sub(r"^(?:(?:um+|uh+|well|so|ok|okay|alright|hey|hi|and|but|also|now|then)\s*,?\s+)+(?=\S)", "", s, flags=re.I)
    s = re.sub(r"\s*,?\s*\b(?:engramm)\b\s*,?\s*", " ", s, flags=re.I).strip(" ,")
    return s


def about_request(sentence: str) -> tuple[str, str] | None:
    """(kind, topic) for "tell me about X" and friends, else None. "what is X" / "who is X"
    only when X is a plain topic (no "of", no superlative, no question clause)."""
    s = _clean(sentence)
    for kind, rx in _ABOUT:
        m = rx.match(s)
        if not m:
            continue
        x = m.group("x").strip(" ,")
        x = re.sub(r"^(?:about|the (?:word|term)|the concept of|the idea of)\s+", "", x, flags=re.I)
        if not x or re.fullmatch(r"(?:me|myself|you|yourself|it|this|that|them|him|her|us|everything|anything|"
                                 r"something|stuff|things|more)", x, flags=re.I):
            return None
        if kind == "what":
            if len(x.split()) > 6 or _RELATIONAL.search(x) or re.search(r"\d", x):
                return None
            if re.match(r"^(?:going on|happening|up|new|wrong|that|this|it|the (?:time|date|weather|matter|problem|"
                        r"point|answer|difference|best|worst))\b", x, flags=re.I):
                return None
        return kind, x
    return None


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------

def classify_sentence(sentence: str, bank: Bank, now=None) -> Unit:
    n_full = normalise(sentence, fillers=False)
    n = normalise(sentence)
    if not n:
        return Unit("empty", sentence, n)
    if forget_topic(sentence) is not None:
        return Unit("forget", sentence, n)
    m = _REMEMBER.match(_clean(sentence))
    if m and len(m.group("x").split()) >= 2 and not re.match(r"^(?:me|my name)\b", m.group("x"), flags=re.I):
        x = m.group("x").strip()
        return Unit("remember", sentence, n, data={"text": x[:1].upper() + x[1:]})
    tr: ToolResult | None = tool_answer(_clean(sentence), now)
    if tr is not None:
        return Unit("tool", sentence, n, data={"result": tr})
    hit = bank.intent(n_full, n)
    if hit:
        it, mm = hit
        groups = {k.rstrip("0123456789"): v for k, v in mm.groupdict().items() if v}
        return Unit("intent", sentence, n, intent=it.id, groups=groups)
    ab = about_request(sentence)
    if ab:
        return Unit("about", sentence, n, data={"kind": ab[0], "topic": ab[1]})
    kind = message_type(sentence)
    is_question = kind == "question"
    if (not is_question or _WHY_ME.match(n)) and (_FIRST_PERSON.search(n) or len(n.split()) <= 4):
        fe = bank.feeling(n)
        if fe:
            cat, neg = fe
            return Unit("feeling", sentence, n, data={"category": cat.id, "valence": cat.valence, "negated": neg,
                                                      "first_person": bool(_FIRST_PERSON.search(n))})
    if is_question:
        return Unit("question", sentence, n)
    if kind == "smalltalk":                       # the core's own small-talk rules (hello, thanks, bye)
        near = bank.nearest(n)
        if near and near[1] >= 0.3:
            return Unit("intent", sentence, n, intent=near[0].id, data={"nearest": round(near[1], 3)})
    if len(n.split()) <= NEAREST_MAX_WORDS and not _FIRST_PERSON.search(n):
        near = bank.nearest(n)
        if near and near[1] >= NEAREST_MIN:
            return Unit("intent", sentence, n, intent=near[0].id, data={"nearest": round(near[1], 3)})
    return Unit("statement", sentence, n)


def classify(message: str, bank: Bank | None = None, now=None) -> list[Unit]:
    bank = bank or load_bank()
    text = " ".join(message.split())
    if not text:
        return [Unit("empty", message)]
    rule = bank.safety_rule(normalise(text, fillers=False))
    if rule is not None:
        return [Unit("safety", text, normalise(text), data={"rule": rule.id, "kind": rule.kind,
                                                            "response": rule.response})]
    from engramm.chat.writing import writing_request
    task = writing_request(text)
    if task is not None:
        return [Unit("writing", text, normalise(text), data={"task": task})]
    sents = split_sentences(text)
    # a whole-message forget request keeps its full wording ("Scratch my dog. Forget it.")
    if forget_topic(text) is not None and len(sents) > 1 and all(forget_topic(s) is None for s in sents[:-1]) \
            and forget_topic(sents[-1]) is None:
        return [Unit("forget", text, normalise(text))]
    return [classify_sentence(s, bank, now) for s in sents] or [Unit("empty", message)]
