"""Writing (Chat v3, phase 6): e-mails, letters and messages; editing a draft; summaries;
rephrasing; short poems — by rules and authored parts (data/conv/writing.yaml), no neural net.

"Write an email to my boss asking for a day off tomorrow" is understood as
    genre = email, recipient = boss (formal), purpose = day_off, date = tomorrow;
the draft is assembled from the purpose's parts (greeting, opening, body, an optional extra
sentence, closing, sign-off with your name from memory) and can then be changed:
"make it shorter", "more formal", "add that I'm reachable by phone", "sign it with Erik",
"change the date to Friday", "another version".

Summaries pick the sentences that carry the most frequent content words (extractive, in their
original order). Rephrasing applies register rules (contractions, slang, greetings, fillers)
and fixes common spelling mistakes — it changes style, never facts.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import asdict, dataclass, field

GENRES = {"email": "email", "e-mail": "email", "mail": "email", "letter": "letter", "message": "message",
          "text": "message", "text message": "message", "note": "note", "card": "note", "cover letter": "letter",
          "thank-you note": "note", "thank you note": "note", "invitation": "message", "apology": "message",
          "complaint": "letter", "reminder": "message", "resignation letter": "letter",
          "recommendation letter": "letter", "reply": "email", "response": "email", "announcement": "email",
          "wish": "note", "wishes": "note", "excuse": "note"}
FORMAL_ROLES = {"boss", "manager", "supervisor", "landlord", "landlady", "teacher", "professor", "lecturer", "tutor",
                "principal", "headteacher", "client", "customer", "customer service", "customer support", "support",
                "support team", "company", "hr", "hr department", "human resources", "recruiter", "hiring manager",
                "doctor", "bank", "insurance", "insurance company", "hotel", "airline", "school", "university",
                "council", "office", "director", "ceo", "employer", "tenant", "committee", "team", "colleagues",
                "coworkers", "co-workers", "department", "gym", "provider", "internet provider", "shop", "store",
                "seller", "vendor", "editor", "publisher", "mayor", "senator", "neighbour", "neighbor",
                "colleague", "coworker", "co-worker", "instructor", "coach", "dean", "admissions office"}
FAMILY = {"mom", "mum", "mother", "dad", "father", "parents", "grandma", "grandpa", "grandmother", "grandfather",
          "aunt", "uncle", "brother", "sister", "wife", "husband", "partner", "girlfriend", "boyfriend", "son",
          "daughter", "kids", "family", "cousin", "sibling", "siblings", "fiance", "fiancé", "fiancee", "fiancée"}
CASUAL_ROLES = FAMILY | {"friend", "best friend", "buddy", "roommate", "flatmate", "mate", "pal", "bestie",
                         "crush", "ex", "friends", "everyone"}
_ROLE_WORDS = sorted(FORMAL_ROLES | CASUAL_ROLES, key=len, reverse=True)
_ROLE_RX = "|".join(re.escape(r) for r in _ROLE_WORDS)
_GENRE_RX = r"e-?mail|mail|letter|message|text(?: message)?|note|card|cover letter|thank[- ]you note|invitation|" \
            r"apology|complaint|reminder|resignation letter|recommendation letter|reply|response|announcement|" \
            r"wish(?:es)?|excuse"
_ADJ_RX = r"(?:(?:short|quick|brief|long|longer|formal|informal|polite|friendly|professional|casual|nice|sweet|" \
          r"funny|heartfelt|warm|kind|simple|little|detailed|polished|official|firm|strong|good)\s+)*"
# the occasion before the genre ("a birthday message", "a get-well card") becomes part of the purpose
_OCCASION_RX = r"(?:(?:birthday|anniversary|wedding|farewell|goodbye|congratulations?|congratulatory|get[- ]well|" \
               r"condolence|sympathy|christmas|holiday|new year(?:'s)?|welcome|good luck|thank[- ]you|" \
               r"retirement|graduation)\s+)?"
_REQUEST = re.compile(
    r"^(?:(?:can|could|would|will) you |please |pls |plz |help me(?: to)? |i need (?:you )?to |i want (?:you )?to |"
    r"i'd like (?:you )?to |i would like (?:you )?to |)*(?:write|draft|compose|prepare|create|make|put together|"
    r"type up|help me (?:write|draft)|help with|write up)\s+(?:me\s+|up\s+)?(?:an?\s+|the\s+|some\s+|my\s+)?"
    rf"(?P<adj>{_ADJ_RX})(?P<occ>{_OCCASION_RX})(?P<genre>{_GENRE_RX})\b(?P<rest>.*)$", re.I)
_VERB_REQUEST = re.compile(r"^(?:(?:can|could) you |please |help me )*(?P<verb>e-?mail|text|message|write to)\s+"
                           r"(?P<rest>.+)$", re.I)
_POEM = re.compile(r"^(?:(?:can|could|would) you |please )*(?:write|compose|make|create)(?: me)?(?: an?| some)?"
                   r"(?: short| little| nice| funny| sweet)? (?:poem|rhyme|verse|haiku|limerick)s?"
                   r"(?: (?:about|on|for|of) (?P<topic>.+))?$", re.I)
_STORY = re.compile(r"^(?:(?:can|could|would) you |please )*(?:write|tell|make up)(?: me)? an?(?: short| little| "
                    r"bedtime| funny)? (?:story|tale) (?:about|of|with) (?P<topic>.+)$", re.I)
_SUMMARY = re.compile(r"^(?:(?:can|could|would) you |please )*(?:summari[sz]e|sum up|give me a summary of|"
                      r"make a summary of|write a summary of|tl;?dr|shorten)(?: this| the following| this text| that| "
                      r"it)?\s*[:,\-–—]?\s*(?P<text>.*)$", re.I | re.S)
_REPHRASE = re.compile(r"^(?:(?:can|could|would) you |please )*(?:(?P<verb>rephrase|reword|paraphrase|rewrite|"
                       r"polish|improve|proofread|correct|fix(?: the)?(?: grammar| spelling| typos| mistakes)?"
                       r"(?: in| of)?)|make (?:this|it|the following) (?:sound )?(?:more |a bit more |less )?"
                       r"(?P<tone>formal|polite|professional|casual|friendly|informal|simpler|simple|shorter|"
                       r"concise|clearer|nicer))(?: this| the following| this text| that| it)?(?: (?:to be|so it "
                       r"sounds|in a) (?:more )?(?P<tone2>formal|polite|professional|casual|friendly|informal|simpler|"
                       r"shorter)(?: way| tone)?)?\s*[:,\-–—]\s*(?P<text>.+)$", re.I | re.S)
_DATE_WORDS = (r"today|tonight|tomorrow(?: morning| afternoon| evening)?|the day after tomorrow|this weekend|next week|"
               r"next month|(?:next |this |on )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
               r"on the \d{1,2}(?:st|nd|rd|th)?|on \d{1,2}(?:st|nd|rd|th)? (?:of )?(?:january|february|march|april|"
               r"may|june|july|august|september|october|november|december)|(?:from|between) .+? (?:to|and|until) .+?"
               r"(?=$|[,.]| because| as | since)")
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_PURPOSE_START = re.compile(
    r"^(?:,\s*)?(?:(?:asking|to ask|requesting|to request|about|regarding|concerning|re:?|that|saying|to say|"
    r"telling|to tell|letting|to let|thanking|to thank|inviting|to invite|apologi[sz]ing|to apologi[sz]e|"
    r"complaining|to complain|cancelling|canceling|to cancel|informing|to inform|explaining|to explain|"
    r"congratulating|to congratulate|reminding|to remind|following up|to follow up|checking|to check|"
    r"welcoming|to welcome|wishing|to wish|requesting|for|because|since|on|with|in which|where)\b)", re.I)


@dataclass
class WritingRequest:
    genre: str = "email"
    recipient: str | None = None           # role ("boss") or None
    recipient_name: str | None = None       # a name ("Anna")
    tone: str = "formal"                    # formal | casual
    purpose: str = "generic"
    purpose_text: str = ""                  # the purpose in the user's words
    date: str | None = None                 # "tomorrow"
    reason: str | None = None               # "because I have a doctor's appointment"
    item: str | None = None                 # "my gym membership"
    short: bool = False
    long: bool = False
    additions: list = field(default_factory=list)
    sign: str | None = None
    variant: int = 0
    subject: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> WritingRequest:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# understanding the request
# ---------------------------------------------------------------------------

def parse_request(message: str, purposes: dict) -> WritingRequest | None:
    text = " ".join(message.strip().split()).rstrip("?.!")
    text = re.sub(r"^(?:hey|hi|ok|okay|so|and|also|now)[,!]?\s+", "", text, flags=re.I)
    m = _REQUEST.match(text)
    req = WritingRequest()
    if m:
        genre = m.group("genre").lower().replace("e-mail", "email")
        req.genre = GENRES.get(genre, "email")
        adj = m.group("adj").lower()
        rest = m.group("rest").strip()
        if m.group("occ"):
            rest = f"{m.group('occ').strip()} {rest}".strip()
        if genre in ("apology", "complaint", "invitation", "reminder", "resignation letter", "cover letter",
                     "recommendation letter", "thank-you note", "thank you note"):
            rest = f"{genre} {rest}"
    else:
        m = _VERB_REQUEST.match(text)
        if not m:
            return None
        verb = m.group("verb").lower()
        req.genre = "message" if verb in ("text", "message") else "email"
        adj = ""
        rest = m.group("rest").strip()
        if not re.match(rf"^(?:to\s+)?(?:my|the|our|a|an|{_ROLE_RX}|[A-Z])", rest, flags=re.I):
            return None
        if not rest.lower().startswith("to "):
            rest = "to " + rest
    # recipient
    rm = re.search(rf"\b(?:to|for)\s+(?:my\s+|the\s+|our\s+|a\s+|an\s+)?(?P<role>{_ROLE_RX})\b"
                   r"(?:\s+(?P<name>(?-i:(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?)?\s?[A-Z][a-zA-Z'-]+"
                   r"(?:\s[A-Z][a-zA-Z'-]+)?)))?", rest, flags=re.I)
    purpose_text = rest
    if rm:
        req.recipient = rm.group("role").lower()
        if rm.group("name") and rm.group("name")[0].isupper():
            req.recipient_name = rm.group("name").strip()
        purpose_text = (rest[:rm.start()] + " " + rest[rm.end():]).strip()
    else:
        nm = re.search(r"\bto\s+(?P<name>(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-zA-Z'-]+|[A-Z][a-zA-Z'-]+"
                       r"(?:\s+[A-Z][a-zA-Z'-]+)?)(?=\s|$|,)", rest)
        if nm and nm.group("name").lower() not in ("i", "me", "my"):
            req.recipient_name = nm.group("name")
            purpose_text = (rest[:nm.start()] + " " + rest[nm.end():]).strip()
    # tone: asked for, else by recipient
    if re.search(r"\b(?:informal|casual|friendly|funny|sweet|warm|heartfelt|nice)\b", adj):
        req.tone = "casual"
    elif re.search(r"\b(?:formal|professional|polite|official)\b", adj):
        req.tone = "formal"
    elif req.recipient_name and re.match(r"^(?:Mr|Mrs|Ms|Dr|Prof)\b", req.recipient_name):
        req.tone = "formal"
    elif req.recipient in CASUAL_ROLES or (req.recipient is None and req.recipient_name and req.genre != "letter"):
        req.tone = "casual"
    elif req.recipient in FORMAL_ROLES:
        req.tone = "formal"
    else:
        req.tone = "casual" if req.genre in ("message", "note") else "formal"
    req.short = bool(re.search(r"\b(?:short|quick|brief|little|simple)\b", adj))
    req.long = bool(re.search(r"\b(?:long|longer|detailed)\b", adj))
    # date and reason
    dm = re.search(rf"\b(?:{_DATE_WORDS})\b", purpose_text, flags=re.I)
    if dm:
        req.date = dm.group(0).strip()
        purpose_text = (purpose_text[:dm.start()] + purpose_text[dm.end():]).strip()
    rsm = re.search(r"\b(?:because|since|as|due to)\b\s+(?P<r>.+)$", purpose_text, flags=re.I)
    if rsm:
        req.reason = rsm.group(0).strip().rstrip(".")
        purpose_text = purpose_text[:rsm.start()].strip()
    purpose_text = re.sub(r"\s{2,}", " ", purpose_text).strip(" ,")
    req.purpose_text = purpose_text
    req.purpose = classify_purpose(purpose_text, purposes)
    if req.purpose == "generic" and req.reason:
        req.purpose = classify_purpose(req.reason, purposes)
    im = re.search(r"\b(?:cancel(?:ling|ing)?|terminate|end|reschedul(?:e|ing)|postpon(?:e|ing)|move)\s+"
                   r"(?P<item>(?:my|our|the|this)\s+[a-z][a-z' -]{2,40}?)(?=$|[,.]| on | for | from | to | at | "
                   r"because| as )", purpose_text, flags=re.I)
    if im:
        req.item = im.group("item").strip()
    return req


def classify_purpose(text: str, purposes: dict) -> str:
    low = " " + text.lower() + " "
    for name, p in purposes.items():
        for key in p.get("keys", []):
            if re.search(key, low):
                return name
    return "generic"


# ---------------------------------------------------------------------------
# drafting
# ---------------------------------------------------------------------------

def _pick(options: list[str], key: str) -> str:
    options = [o for o in options if o is not None]
    if not options:
        return ""
    i = int.from_bytes(hashlib.shake_256(key.encode()).digest(4), "little") % len(options)
    return options[i]


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _title(s: str) -> str:
    small = {"a", "an", "the", "of", "for", "to", "on", "in", "and", "or", "my", "at", "by", "with"}
    ws = s.split()
    return " ".join(w if (i and w.lower() in small) else w[:1].upper() + w[1:] for i, w in enumerate(ws))


def _flip_recipient(text: str) -> str:
    """"thanking her for her help" → "for your help": the recipient becomes "you"."""
    def her(m):
        nxt = m.group(2) or ""
        return ("your" if nxt and nxt[0].isalpha() and nxt.lower() not in ("for", "to", "about", "on", "that",
                                                                          "with", "and", "in", "at", "by")
                else "you") + (" " + nxt if nxt else "")
    t = re.sub(r"\b(her)\b(?:\s+(\w+))?", her, text)
    t = re.sub(r"\b(?:him|them)\b", "you", t)
    t = re.sub(r"\b(?:his|their)\b", "your", t)
    agree = {"is": "are", "was": "were", "has": "have", "does": "do", "doesn't": "don't", "isn't": "aren't",
             "wasn't": "weren't"}
    t = re.sub(r"\b(?:he|she|they)\s+(is|are|was|were|has|have|had|does|do|did|could|can|would|will|might|may|"
               r"should|must|doesn't|don't|isn't|aren't|wasn't|weren't)\b",
               lambda m: "you " + agree.get(m.group(1), m.group(1)), t)
    return t


def _about(req: WritingRequest) -> str:
    """The purpose as a phrase after the main sentence: " about the broken heating", " for the gift"."""
    t = req.purpose_text.strip()
    if not t:
        return ""
    t = re.sub(r"^(?:(?:an?|the)\s+)?(?:apology|complaint|invitation|reminder|resignation letter|cover letter|"
               r"recommendation letter|thank[- ]you note)\s*", "", t, flags=re.I)
    t = re.sub(r"^(?:thank(?:s| you)(?: (?:note|card|message|letter))?|a thank[- ]you)\b\s*", "", t, flags=re.I)
    t = re.sub(r"^(?:asking|to ask|requesting|to request)\s+(?:for\s+)?(?:(?:him|her|them|you)\s+)?", "about ", t,
               flags=re.I)
    t = re.sub(r"^(?:(?:to )?(?:thank|congratulate|invite|apologi[sz]e|welcome|remind|wish)|thanking|"
               r"congratulating|inviting|apologi[sz]ing|welcoming|reminding|wishing)\s+"
               r"(?:(?:him|her|them|you|everyone|all)\s+)?", "", t, flags=re.I)
    t = re.sub(r"^(?:(?:to )?(?:complain|follow up|check in|inform|tell|let|say)|complaining|following up|"
               r"checking in|informing|telling|letting|saying)\s+(?:(?:him|her|them|you)\s+)?(?:know\s+)?", "", t,
               flags=re.I)
    t = re.sub(r"^(?:(?:to )?(?:cancel|reschedule|postpone)|cancel(?:l)?ing|rescheduling|postponing)\s+",
               "", t, flags=re.I)
    t = _flip_recipient(t).strip(" ,")
    if not t:
        return ""
    if req.purpose in ("cancel", "reschedule"):
        return ""
    if req.purpose in ("meeting", "day_off", "sick", "late", "raise", "resignation", "birthday", "extension"):
        orig = _flip_recipient(req.purpose_text)
        if req.purpose == "extension":
            m = re.search(r"\bextension\s+(?:on|for)\s+(.+)$", orig, flags=re.I)
            return f" on {m.group(1)}" if m else ""
        m = re.search(r"\b(?:about|regarding|concerning)\s+(.+)$", orig, flags=re.I)
        return f" about {m.group(1)}" if m else ""
    if req.purpose == "congratulations" and not re.match(r"^(?:on|for)\b", t, re.I):
        t = "on " + t
    if not re.match(r"^(?:about|for|on|to|regarding|that|with|of|in|at)\b", t, re.I):
        t = "about " + t
    return " " + t


def _topic_title(req: WritingRequest) -> str:
    pt = req.purpose_text.strip()
    if not pt:
        return "Hello"
    if re.match(r"^(?:asking|to ask|ask|whether|if)\b", pt, re.I):
        return "A Quick Question"
    pt = re.sub(r"^(?:about|regarding|concerning|re:?)\s+", "", pt, flags=re.I)
    return _title(_flip_recipient(pt)[:60])


def _content(req: WritingRequest) -> str:
    """What to say, for "saying/telling (him) (that) X": X, addressed to the recipient."""
    t = re.sub(r"^(?:saying|to say|telling|to tell|letting|to let)\s+(?:(?:him|her|them|you)\s+)?(?:know\s+)?"
               r"(?:that\s+)?", "", req.purpose_text.strip(), flags=re.I)
    t = _flip_recipient(t).strip(" ,.")
    if req.reason:
        t = f"{t} {req.reason}"
    if req.date and req.date.lower() not in t.lower():
        t = f"{t} {req.date}"
    return t or "I'm thinking of you"


def _topic_clause(req: WritingRequest) -> str:
    t = req.purpose_text.strip()
    if not t:
        return "to get in touch"
    t = _flip_recipient(t)
    m = re.match(r"^(\w+ing)\b\s*(.*)$", t)
    if m:
        from engramm.chat.realize import verb_base
        base = verb_base(m.group(1))
        if base:
            return f"to {base} {m.group(2)}".strip()
    if re.match(r"^(?:that)\b", t, re.I):
        return "to let you know " + t
    if re.match(r"^(?:to)\b", t, re.I):
        return t
    if re.match(r"^(?:about|regarding|concerning)\b", t, re.I):
        return t
    return "about " + t


def resolve_date(phrase: str | None, today: dt.date | None) -> tuple[str, str]:
    """("tomorrow (Wednesday, 30 September)", "on 30 September") — the date in the text and in
    the subject line; without a clock the words as written."""
    if not phrase:
        return "", ""
    p = phrase.strip()
    low = p.lower()
    d = None
    if today is not None:
        if low.startswith("today") or low == "tonight":
            d = today
        elif low.startswith("tomorrow"):
            d = today + dt.timedelta(days=1)
        elif low == "the day after tomorrow":
            d = today + dt.timedelta(days=2)
        else:
            m = re.fullmatch(r"(?:(next|this|on) )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", low)
            if m:
                target = _WEEKDAYS.index(m.group(2))
                delta = (target - today.weekday()) % 7 or 7        # the coming one, never today
                d = today + dt.timedelta(days=delta)
    if d is None:
        return p, f"({p})"
    wd = d.strftime("%A")
    nice = f"{wd}, {d.day} {d.strftime('%B')}"
    if low.startswith(("today", "tomorrow", "tonight")) or low == "the day after tomorrow":
        return f"{p} ({nice})", f"on {d.day} {d.strftime('%B')}"
    return f"on {nice}", f"on {d.day} {d.strftime('%B')}"


def draft(req: WritingRequest, spec: dict, user_name: str | None, today: dt.date | None,
          conversation: str = "") -> str:
    purposes = spec["purposes"]
    p = purposes.get(req.purpose, purposes["generic"])
    tone = req.tone if req.tone in p else "formal"
    parts = p[tone]
    key = f"{conversation}|{req.purpose}|{req.variant}"
    date_text, date_title = resolve_date(req.date, today)
    about = _about(req)
    item = req.item or ""
    fill = {
        "date_phrase": date_text or ("soon" if req.purpose in ("meeting",) else ""),
        "date_phrase_or_soon": date_text or "in the coming days",
        "date_phrase_or_blank": date_text,
        "date_phrase_or_today": date_text or "today",
        "date_title": date_title,
        "date_from": f" {date_text}" if date_text and req.purpose == "reschedule" else "",
        "date_to": f" — would {date_text} work instead" if date_text and req.purpose == "reschedule" else "",
        "reason": " " + re.sub(r"^as\b", "as", req.reason) if req.reason else "",
        "about": about,
        "about_title": (": " + _title(about.strip().split(" ", 1)[1])) if about and len(about.split()) <= 8 else "",
        "item_or_meeting": re.sub(r"^(?:my|our|the)\s+", "", item) or "meeting",
        "item_or_subscription": item or "my subscription",
        "effective": f", effective {date_text}" if date_text else "",
        "topic_clause": _topic_clause(req) + (f" {date_text}" if date_text and req.purpose == "generic" else ""),
        "topic_title": _topic_title(req),
        "name": user_name or "[Your name]",
        "content": _content(req),
    }

    def f(s: str) -> str:
        out = re.sub(r"\{(\w+)\}", lambda m: fill.get(m.group(1), m.group(0)), s)
        out = re.sub(r"\s+([,.!?])", r"\1", out)
        out = re.sub(r"\s{2,}", " ", out).strip()
        return out
    sign = req.sign or user_name or "[Your name]"
    # greeting
    g = spec["greetings"]
    if req.recipient_name:
        greet = _pick(g[f"{tone}_named"], key + "g").replace("{recipient_name}", req.recipient_name)
    elif req.recipient:
        title = _recipient_title(req.recipient, tone)
        greet = _pick(g[f"{tone}_role"], key + "g").replace("{recipient_title}", title)
    else:
        greet = _pick(g[f"{tone}_unknown"], key + "g")
    opening = "" if req.short else f(_pick(parts.get("open", [""]), key + "o"))
    body = _cap(f(_pick(parts["body"], key + "b")))
    extras = [] if req.short else [f(_pick(parts.get("extra", [""]), key + "e"))]
    if req.long and len(parts.get("extra", [])) > 1:
        extras = [f(x) for x in parts["extra"]]
    extras += [_cap(a.rstrip(".")) + "." for a in req.additions]
    closing = f(_pick(parts.get("close", [""]), key + "c"))
    closings = spec["closings"]
    if tone == "casual" and req.recipient in FAMILY:
        sign_off = _pick(closings["casual_family"], key + "s")
    else:
        sign_off = _pick(closings[tone], key + "s")
    if closing.endswith(","):                 # "With sincere thanks," is itself the sign-off
        sign_off, closing = closing, ""
    paragraph = " ".join(x for x in [opening, body] + extras if x)
    lines = []
    if req.genre in ("email",) and req.subject:
        lines += [f"Subject: {_title(f(_pick(p['subject'], key + 't')).strip())}", ""]
    if req.genre in ("message",) and tone == "casual":
        lines += [f"{greet.rstrip(',')}! {_cap(paragraph)}" + (f" {closing}" if closing else ""),
                  "", sign if not user_name or req.recipient in FAMILY else sign]
        return "\n".join(lines)
    lines += [greet, "", paragraph]
    if closing:
        lines += ["", closing]
    lines += ["", sign_off, sign]
    return "\n".join(lines)


def _recipient_title(role: str, tone: str) -> str:
    fixed = {"team": "team", "colleagues": "colleagues", "coworkers": "colleagues", "co-workers": "colleagues",
             "customer service": "Customer Service Team", "customer support": "Support Team",
             "support": "Support Team", "support team": "Support Team", "hr": "HR Team",
             "hr department": "HR Team", "human resources": "HR Team", "committee": "Committee",
             "admissions office": "Admissions Team", "everyone": "everyone", "friends": "everyone",
             "family": "everyone", "mom": "Mom", "mum": "Mum", "dad": "Dad", "parents": "Mom and Dad",
             "grandma": "Grandma", "grandpa": "Grandpa", "kids": "kids"}
    if role in fixed:
        return fixed[role]
    if tone == "casual":
        return f"[{_cap(role)}'s name]" if role not in FAMILY else _cap(role)
    return f"[{_title(role)}'s name]"


# ---------------------------------------------------------------------------
# changing a draft
# ---------------------------------------------------------------------------

_EDITS = [
    ("shorter", re.compile(r"^(?:make it |can you make it |please make it )?(?:a bit |much |even )?(?:shorter|"
                           r"more concise|briefer)|shorten it|too long|cut it down", re.I)),
    ("longer", re.compile(r"^(?:make it |can you make it )?(?:a bit |much )?(?:longer|more detailed)|add more "
                          r"details?|too short|expand it", re.I)),
    ("formal", re.compile(r"^(?:make it |can you make it )?(?:a bit |much )?(?:more formal|more professional|"
                          r"more polite|formal|professional)", re.I)),
    ("casual", re.compile(r"^(?:make it |can you make it )?(?:a bit |much )?(?:more casual|less formal|more "
                          r"friendly|friendlier|more relaxed|casual|informal|warmer)", re.I)),
    ("again", re.compile(r"^(?:another (?:version|one)|try again|rewrite it|write it differently|different "
                         r"version|redo it|one more version)", re.I)),
    ("add", re.compile(r"^(?:please |can you |could you )?(?:also )?(?:add|mention|include|put in)"
                       r"(?: that| in| also)?\s+(?P<x>.+)$", re.I)),
    ("sign", re.compile(r"^(?:sign it|sign|sign off|end it)(?: with| as| from)?\s+(?P<x>[A-Z][\w' -]{0,40})$", re.I)),
    ("date", re.compile(r"^(?:change|make|set)(?: the)? (?:date|day)(?: to| for)?\s+(?P<x>.+)$|^make it for\s+(?P<x2>.+)$",
                        re.I)),
    ("to", re.compile(r"^(?:make it |address it |send it |change it )?to (?:my |the )?(?P<x>" + _ROLE_RX +
                      r"|[A-Z][a-z]+) instead$", re.I)),
    ("nosubject", re.compile(r"^(?:remove|drop|delete) the subject(?: line)?$", re.I)),
]


def edit_command(message: str) -> tuple[str, str | None] | None:
    s = " ".join(message.strip().split()).rstrip("?.!")
    s = re.sub(r"^(?:ok|okay|great|nice|thanks|thank you|cool|good|perfect|hmm|now)[,!.]?\s+", "", s, flags=re.I)
    for name, rx in _EDITS:
        m = rx.match(s)
        if m:
            x = next((v for k, v in m.groupdict().items() if v), None)
            return name, x.strip() if x else None
    return None


def apply_edit(req: WritingRequest, cmd: str, x: str | None) -> WritingRequest:
    r = WritingRequest.from_dict(req.to_dict())
    if cmd == "shorter":
        r.short, r.long = True, False
    elif cmd == "longer":
        r.short, r.long = False, True
    elif cmd == "formal":
        r.tone = "formal"
    elif cmd == "casual":
        r.tone = "casual"
    elif cmd == "again":
        r.variant += 1
    elif cmd == "add" and x:
        r.additions = r.additions + [_flip_recipient(re.sub(r"^that\s+", "", x))]
    elif cmd == "sign" and x:
        r.sign = x
    elif cmd == "date" and x:
        r.date = x
    elif cmd == "to" and x:
        if x.lower() in FORMAL_ROLES | CASUAL_ROLES:
            r.recipient, r.recipient_name = x.lower(), None
            r.tone = "casual" if x.lower() in CASUAL_ROLES else "formal"
        else:
            r.recipient_name = x
    elif cmd == "nosubject":
        r.subject = False
    return r


# ---------------------------------------------------------------------------
# summaries, rephrasing, poems
# ---------------------------------------------------------------------------

_STOP = frozenset("""a an the and or but if then than that this these those is are was were be been being am do does
did have has had of in on at to for from by with as it its it's they them their he she his her him we our you your
i me my not no so very just also can could will would should may might must there here what which who whom whose
when where why how all any some each more most other such into over after before about between through during out
up down off again further once only own same too s t don't isn't wasn't aren't""".split())


def summarize(text: str, max_sentences: int | None = None) -> list[str]:
    from engramm.chat.acts import split_sentences
    sents = [s.strip() for s in split_sentences(" ".join(text.split())) if len(s.split()) >= 3]
    if len(sents) <= 2:
        return sents
    words = [re.findall(r"[a-z][a-z'-]+", s.lower()) for s in sents]
    freq: dict[str, int] = {}
    for ws in words:
        for w in set(ws):
            if w not in _STOP and len(w) > 2:
                freq[w] = freq.get(w, 0) + 1
    scores = []
    for i, ws in enumerate(words):
        content = [w for w in ws if w in freq]
        if not content:
            scores.append((0.0, i))
            continue
        s = sum(freq[w] for w in content) / (len(ws) ** 0.5)
        s *= 1.25 if i == 0 else (1.1 if i < 3 else 1.0)
        scores.append((s, i))
    k = max_sentences or max(1, min(3, round(len(sents) / 3)))
    best = sorted(sorted(scores, key=lambda x: (-x[0], x[1]))[:k], key=lambda x: x[1])
    return [sents[i] for _, i in best]


_CONTRACT = [("do not", "don't"), ("does not", "doesn't"), ("did not", "didn't"), ("is not", "isn't"),
             ("are not", "aren't"), ("was not", "wasn't"), ("were not", "weren't"), ("have not", "haven't"),
             ("has not", "hasn't"), ("had not", "hadn't"), ("will not", "won't"), ("would not", "wouldn't"),
             ("cannot", "can't"), ("can not", "can't"), ("could not", "couldn't"), ("should not", "shouldn't"),
             ("I am", "I'm"), ("I have", "I've"), ("I will", "I'll"), ("I would", "I'd"), ("you are", "you're"),
             ("we are", "we're"), ("they are", "they're"), ("it is", "it's"), ("that is", "that's"),
             ("there is", "there's"), ("let us", "let's"), ("you will", "you'll"), ("we will", "we'll")]
_INFORMAL = [(r"\bwanna\b", "want to"), (r"\bgonna\b", "going to"), (r"\bgotta\b", "have to"),
             (r"\bkinda\b", "somewhat"), (r"\bsorta\b", "somewhat"), (r"\byeah\b", "yes"), (r"\bnope\b", "no"),
             (r"\bcuz\b|\bcause\b|\bcoz\b", "because"), (r"\basap\b", "as soon as possible"),
             (r"\bbtw\b", "by the way"), (r"\bthx\b|\bthanks\b", "thank you"), (r"\bpls\b|\bplz\b", "please"),
             (r"\bu\b", "you"), (r"\bur\b", "your"), (r"\bimo\b", "in my opinion"), (r"\bfyi\b", "for your information"),
             (r"\bstuff\b", "things"), (r"\bkids\b", "children"), (r"\bguys\b", "everyone"),
             (r"\bpretty (good|bad|big|small|sure)\b", r"quite \1"), (r"\bokay\b|\bok\b", "all right"),
             (r"^\s*(?:hey|hi|yo)\b", "Hello"), (r"\bawesome\b", "excellent"), (r"\bget back to you\b",
                                                                                "respond to you")]
_FILLERS = [(r"\b(?:really|basically|actually|literally|just|very|quite|totally|honestly)\s+", ""),
            (r"\bin order to\b", "to"), (r"\bdue to the fact that\b", "because"),
            (r"\bat this point in time\b", "now"), (r"\bin the event that\b", "if"),
            (r"\bfor the purpose of\b", "for"), (r"\bwith regard to\b", "about"), (r"\bin spite of the fact that\b",
                                                                                 "although")]
_SPELLING = {"teh": "the", "recieve": "receive", "recieved": "received", "definately": "definitely",
             "seperate": "separate", "occured": "occurred", "untill": "until", "wich": "which", "thier": "their",
             "becuase": "because", "beacuse": "because", "alot": "a lot", "tommorow": "tomorrow",
             "tomorow": "tomorrow", "goverment": "government", "enviroment": "environment", "adress": "address",
             "begining": "beginning", "beleive": "believe", "calender": "calendar", "collegue": "colleague",
             "comming": "coming", "concious": "conscious", "embarass": "embarrass", "existance": "existence",
             "familar": "familiar", "finaly": "finally", "foward": "forward", "freind": "friend",
             "garantee": "guarantee", "happend": "happened", "immediatly": "immediately", "independant": "independent",
             "knowlege": "knowledge", "neccessary": "necessary", "necesary": "necessary", "noticable": "noticeable",
             "ocasion": "occasion", "occurence": "occurrence", "persue": "pursue", "posession": "possession",
             "prefered": "preferred", "publically": "publicly", "reccomend": "recommend", "recomend": "recommend",
             "refered": "referred", "relevent": "relevant", "remeber": "remember", "responsability": "responsibility",
             "succesful": "successful", "sucessful": "successful", "suprise": "surprise", "truely": "truly",
             "wierd": "weird", "writting": "writing", "youre": "you're", "dont": "don't", "cant": "can't",
             "wont": "won't", "doesnt": "doesn't", "didnt": "didn't", "isnt": "isn't", "im": "I'm", "ive": "I've",
             "thats": "that's", "whats": "what's", "shouldnt": "shouldn't", "wouldnt": "wouldn't",
             "couldnt": "couldn't", "arguement": "argument", "accomodate": "accommodate", "acheive": "achieve",
             "apparantly": "apparently", "basicly": "basically", "buisness": "business", "definatly": "definitely",
             "dissapoint": "disappoint", "excercise": "exercise", "grammer": "grammar", "harrass": "harass",
             "interupt": "interrupt", "judgement": "judgment", "liason": "liaison", "maintainance": "maintenance",
             "millenium": "millennium", "mispell": "misspell", "occassion": "occasion", "paralell": "parallel",
             "priviledge": "privilege", "questionaire": "questionnaire", "reciept": "receipt",
             "rythm": "rhythm", "shedule": "schedule", "tounge": "tongue", "vaccum": "vacuum", "wether": "whether"}


_GRAMMAR = [(r"\bits (?=(?:a|an|the|not|been|going|raining|broken|over|late|okay|ok|fine|true|time|so|very|really|"
             r"just|still|too|like|getting|done|gone|important|possible|hard|easy|good|bad|great|nice|cold|hot)\b)",
             "it's "), (r"\byour welcome\b", "you're welcome"), (r"\b(should|could|would|must) of\b", r"\1 have"),
            (r"\bthere (?=(?:is|are|was|were)\b)", "there "), (r"\ba (?=[aeiou][a-z]{2,})(?!(?:uni|use|eu|one))", "an "),
            (r"\bme and (\w+) (?=(?:are|were|went|have|will)\b)", r"\1 and I "), (r"\bI is\b", "I am"),
            (r"\bhe don't\b", "he doesn't"), (r"\bshe don't\b", "she doesn't"), (r"\bit don't\b", "it doesn't")]


def fix_text(text: str) -> str:
    def spell(m):
        w = m.group(0)
        rep = _SPELLING.get(w.lower())
        if rep is None:
            return w
        return rep[:1].upper() + rep[1:] if w[:1].isupper() else rep
    t = re.sub(r"[A-Za-z']+", spell, text)
    t = re.sub(r"\bi\b", "I", t)
    for pat, rep in _GRAMMAR:
        t = re.sub(pat, rep, t, flags=re.I)
    t = re.sub(r"\s+([,.!?;:])", r"\1", t)
    t = re.sub(r"([,.!?;:])(?=[A-Za-z])", r"\1 ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    t = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)
    if t and t[-1] not in ".!?":
        t += "."
    return t


def rephrase(text: str, tone: str) -> str:
    t = fix_text(text)
    if tone in ("formal", "polite", "professional"):
        for a, b in _CONTRACT:
            t = re.sub(rf"\b{re.escape(b)}\b", a, t, flags=re.I)
        for pat, rep in _INFORMAL:
            t = re.sub(pat, rep, t, flags=re.I)
        t = re.sub(r"!+", ".", t)
        t = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", t)
        t = re.sub(r"(^|[.!?]\s+)(i want)\b", lambda m: m.group(1) + "I would like", t, flags=re.I)
        t = re.sub(r"\bcan you\b", "could you", t, flags=re.I)
    elif tone in ("casual", "friendly", "informal", "nicer"):
        for a, b in _CONTRACT:
            t = re.sub(rf"\b{re.escape(a)}\b", b, t)
        t = re.sub(r"^\s*(?:Dear|Hello)\b", "Hi", t)
        t = re.sub(r"\bthank you\b", "thanks", t, flags=re.I)
        t = re.sub(r"\bI would like to\b", "I'd love to", t)
    elif tone in ("simpler", "simple", "shorter", "concise", "clearer"):
        for pat, rep in _FILLERS:
            t = re.sub(pat, rep, t, flags=re.I)
    t = re.sub(r"\s{2,}", " ", t).strip()
    t = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)
    return t


def poem(topic: str, spec: dict, key: str) -> str:
    topic = topic.strip().rstrip("?.!")
    topic = re.sub(r"^(?:my|the|a|an)\s+", lambda m: m.group(0), topic)
    t = _pick(spec["poems"], key)
    return t.replace("{Topic}", _cap(topic)).replace("{topic}", topic)


def writing_request(message: str) -> str | None:
    """Which writing task the whole message asks for: draft, poem, story, summary, rephrase."""
    s = " ".join(message.strip().split())
    body = re.sub(r"^(?:hey|hi|ok|okay|so|and|also|now)[,!]?\s+", "", s, flags=re.I).rstrip("?.!")
    if _SUMMARY.match(body):
        return "summary"
    if _REPHRASE.match(s):
        return "rephrase"
    if _POEM.match(body):
        return "poem"
    if _STORY.match(body):
        return "story"
    if _REQUEST.match(body) or _VERB_REQUEST.match(body) and re.search(rf"\b(?:{_ROLE_RX})\b|\bto [A-Z]", body):
        return "draft"
    return None
