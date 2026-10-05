"""Answers composed from the situation, not from a topic: react → one fitting question → advice → close.

The composer keeps one active situation per conversation (``st.uses["u_sit"]``): its kind, the thing, the person,
the questions already asked and whether advice was given. It speaks only where the hand-written flows had nothing
better to say — when their reply is a filler ("Tell me more?", "Erzähl ruhig mehr", "I don't know that about you
yet"), a memory note about a situation ("I'll remember that about your friend"), or a non-answer to a question about
the situation. Everything it says comes from data/conv/understand.yaml, keyed by situation kind and object class.
"""
from __future__ import annotations

import re

from engramm.understand.frames import FACT, Frame, parse
from engramm.understand.lex import lexicon

LIVE = 6                        # turns a situation stays active without being mentioned

_GENERIC_EN = [
    r"Oh, interesting — tell me more\.", r"Oh really\? Tell me more about that\.", r"Ah, okay\. How's that going\?",
    r"I see\. Tell me more\?", r"Oh\? Go on\.", r"Okay! Is there something you'd like to know\?",
    r"Mm-hm\. What's on your mind\?", r"You haven't told me that yet\. Want to tell me\?",
    r"I don't know that about you yet[^.]*\.(?: [^.]*\.)?", r"I don't have a good guide for that one[^“]*“tell me about …” and I'll share what I've read\.",
    r"I'm not sure how — that's not among the things[^.]*\.[^.]*\.", r"About what\? Tell me what's going on, and I'll help you think it through\.",
    r"Happy to help — what's the situation\?", r"Tell me a bit more about what's going on, and I'll think it through with you\.",
    r"What would you tell a good friend in the same situation\?[^.]*\.", r"Break it down: what's the very next small step you could take\? Start there\.",
    r"If it's not urgent, sleep on it[^.]*\.", r"Got it\. Anything I can help you with\?", r"Oh, interesting — tell me more\.",
    r"(?:A few things you could do|How about one of these):\n\n(?:• [^\n]+\n?)+\n?Anything there sound good\?",
    r"Hmm, that sounds rough\.", r"Oh, interesting — tell me more\.", r"Love that! Tell me more\?",
    r"I'm not sure I follow[^.]*\.", r"Sorry, I didn't quite get that[^.]*\.",
    r"I don't know, sorry\. I couldn't find anything reliable about that\.",
]
_GENERIC_DE = [
    r"Ah, verstehe\. Erzähl ruhig mehr!", r"Spannend! Erzähl gern mehr\.", r"Interessant – und wie findest du das\?",
    r"Okay, verstehe\. Erzähl ruhig weiter – ich hör zu\.", r"Verstehe\. Magst du ein bisschen mehr erzählen\?",
    r"Alles klar\. Erzähl gern weiter, wenn du magst\.", r"Mhm\. Und dann\?", r"Verstehe – erzähl, wenn du magst\.",
    r"Okay\. Was beschäftigt dich gerade am meisten\?", r"Ah\. Und wie siehst du das\?",
    r"Das kann ich auf Deutsch leider noch nicht nachschlagen\.[^\n]*", r"Das habe ich nicht ganz verstanden\.[^\n]*",
    r"Hm, da komme ich nicht ganz mit\.[^\n]*", r"Das verstehe ich leider nicht\.[^\n]*",
    r"Was würdest du einer guten Freundin in derselben Lage raten\?[^\n]*", r"Zerleg es: Was ist der allernächste kleine Schritt\? Fang dort an\.",
    r"Wie schön! Erzähl ruhig mehr\.", r"Haha, wie schön!", r"Ah, okay\. Und wie geht's dir damit\?",
]
_WEAK_KEYS = re.compile(r"^(?:daily:moment:(?:negative|positive|neutral)|daily:exp_(?:follow|more|agree)_\w+|"
                        r"learned\.(?:about_you|plain)$|"
                        r"daily:talk_(?:plain|tough|nohave)|chitchat|answer\.unknown|unknown_about_you|daily:advice_none|"
                        r"daily:howto_none|intent:thanks|short:thanks|daily:again_lead|"
                        r"de:b\d+:stmt_\w+|de:g\d+:stmt_\w+|de:moment:|de:life:follow_\w+|de:knowledge|de:fallback|"
                        r"de:life:thanks$|de:life:thanks_praise|de:unknown)")


_ADVICE_FITS = {"work_people": {"CONFLICT"}, "people": {"CONFLICT"}, "heartbreak": {"CONFLICT"}, "grief": {"DEATH"},
                "sleep": {"FEEL_NEG", "ILLNESS", "WORRY"}, "tired": {"FEEL_NEG"}, "stress": {"WORRY", "FEEL_NEG"},
                "sad": {"FEEL_NEG", "FAILURE", "CONFLICT", "DEATH"}, "failure": {"FAILURE"},
                "career": {"FAILURE", "MILESTONE", "PLAN"}}


def weak_keys(keys, kind: str = "") -> bool:
    """Every piece of this reply came from a general layer (a filler, a memory note, a general tip — or a tip for a
    different kind of situation)."""
    if not keys:
        return False
    for k in keys:
        if k.startswith("daily:rec_intro") or k.startswith("de:rec"):
            if kind in ("DAMAGE", "INJURY", "ILLNESS", "LOSS", "THEFT", "MONEY", "DELAY") and \
                    not re.search(r"sleep|schlaf|relax|calm", k):
                continue                        # "what should i do?" about a broken fridge is no request for pastimes
            return False
        m = re.match(r"(?:daily|de):advice:(\w+)$", k)
        if m:
            if kind in _ADVICE_FITS.get(m.group(1), set()):
                return False
            continue
        if not _WEAK_KEYS.match(k):
            return False
    return True


_MEMO = re.compile(r"(?:Got it — I'll remember that about your [a-z ]+\.|Got it, you live in [^.]+\.|"
                   r"I'll remember that you work as [^.]+\.|\d+ — got it!)")


_SHORT_ACK = re.compile(r"^(?:Happy to help!?|Happy I could help\.? ?😊?|Sure thing\.?|You're welcome!?|Okay!?|Got it\.?|"
                        r"Gern!?|Sehr gern!?|Immer gern!?|Alles klar\.?|Love to hear that! 😊)\s*", re.I)
_RX_GENERIC = {"en": re.compile("|".join(f"(?:{g})" for g in _GENERIC_EN)),
               "de": re.compile("|".join(f"(?:{g})" for g in _GENERIC_DE))}

_THANKS = re.compile(r"^(?:ok(?:ay)?[, ]+|great[, ]+|cool[, ]+|perfect[, ]+|super[, ]+|alright[, ]+)?(?:thanks|thank you|thx|ty|"
                     r"cheers|ta|danke|vielen dank|dankeschön|danke dir|merci)\b|^(?:you'?re right|good point|true|stimmt|"
                     r"du hast recht|ok(?:ay)?|alles klar)[,!. ]+(?:thanks|thank you|thx|danke)[!. ]*$", re.I)
_PLAN = re.compile(r"^(?:(?:ok(?:ay)?|alright|yeah|yes|right|good idea|great|sure|then|ja|gut|okay|na gut|dann|also)[,!. ]+)*"
                   r"(?:i'?ll|i will|i'?m going to|im going to|i'?m gonna|gonna|i think i'?ll|let me|i'?ll try|"
                   r"ich (?:werde|ruf\w*|mach\w*|geh\w*|probier\w*|versuch\w*|schreib\w*|frag\w*|kühl\w*|bring\w*|kauf\w*|"
                   r"melde?\w*|lass\w*|bestell\w*|such\w*)\b|(?:mach|mache|probier|versuch|ruf|schreib|frag)e? ich\b|"
                   r"machen wir\b|will do\b|i'?ll do that\b|on it\b)", re.I)
_YES = re.compile(r"^(?:yes|yeah|yep|yup|sure|please|ok(?:ay)?|go ahead|tell me|ja|gerne?|bitte|okay|klar|na klar)\b[ !.,]*(?:please|bitte)?[ !.]*$", re.I)
_BETTER = re.compile(r"\b(?:better|fine|okay now|ok now|works again|still works|working again|found it|found them|stopped|"
                     r"it's stopped|hat aufgehört|aufgehört|"
                     r"relieved|smiling|laughing|stopped (?:bleeding|hurting|leaking)|not that bad|fixed|sorted|"
                     r"besser|wieder gut|geht wieder|funktioniert wieder|gefunden|lacht|erleichtert|repariert|nicht so schlimm)\b", re.I)
_WORSE = re.compile(r"\b(?:worse|bleed\w*|blood|swollen|swelling|swell\w*|hurts? (?:a lot|so much|like hell|really bad)|"
                    r"really hurts|getting worse|won'?t stop|can'?t (?:move|walk|stand|breathe|sleep)|not working|"
                    r"still (?:doesn'?t|won'?t|not)|again|blutet|geschwollen|schwillt|schlimmer|tut (?:richtig|so|echt) weh|"
                    r"hört nicht auf|geht immer noch nicht|kann nicht (?:laufen|auftreten|schlafen))\b", re.I)
_DONE = re.compile(r"\b(?:i (?:already |just )?(?:called|turned|switched|put|took|cleaned|washed|reported|blocked|told|"
                   r"tried|did|went|booked|ordered|bought|unplugged|iced|texted|asked|checked|rinsed|removed)|"
                   r"(?:hab|habe) (?:\w+ ){0,4}(?:angerufen|ausgeschaltet|gemacht|gekühlt|gemeldet|gesperrt|gesagt|"
                   r"probiert|abgezogen|gewaschen|entfernt|gefragt|geschrieben|gebucht|bestellt))\b", re.I)
_LONG = re.compile(r"\b(?:\d+|a few|several|two|three|four|five|six|many|zwei|drei|vier|fünf|ein paar|mehrere) "
                   r"(?:days|weeks|months|years|tagen|wochen|monaten|jahren|tage|wochen|monate|jahre)\b|\bseit\b", re.I)
_FEEL_NEG = re.compile(r"\b(?:scared|afraid|worried|nervous|sad|upset|angry|frustrated|stressed|anxious|terrified|"
                       r"overwhelmed|disappointed|devastated|gutted|angst|traurig|sauer|wütend|gestresst|nervös|überfordert|"
                       r"besorgt|aufgeregt|enttäuscht|fertig)\b", re.I)
_FEEL_POS = re.compile(r"\b(?:happy|excited|proud|thrilled|glad|relieved|so good|amazing|glücklich|stolz|froh|"
                       r"freue mich|erleichtert)\b", re.I)

_WEAK_KINDS = ("PLAN", "ACTIVITY", "FEEL_NEG", "FEEL_POS", "WORRY", "")

_FIRST_Q = {
    "INJURY": "injury_bad", "ILLNESS": "illness_long", "LOSS": "loss_last", "THEFT": "theft_report",
    "CONFLICT": "conflict_what", "FAILURE": "failure_feel", "MONEY": "money_surprise", "DELAY": "delay_long",
    "WORRY": "worry_most", "SUCCESS": "success_celebrate", "MILESTONE": "milestone_feel", "ACQUIRE": "acquire_why",
    "DEATH": "death_holding", "FEEL_NEG": "feel_talk", "PLAN": "plan_feel", "ACTIVITY": "activity_how",
}
_SECOND_Q = {"INJURY": ["injury_move"], "ILLNESS": [], "CONFLICT": ["conflict_feel"]}


def generic(text: str, lang: str, memo: bool = False) -> bool:
    """The reply says nothing about the message: a filler or a non-answer (with memo=True also a memory note)."""
    if not text:
        return True
    rest = _RX_GENERIC[lang].sub("", text.strip())
    if memo:
        rest = _MEMO.sub("", rest)
    for _ in range(3):
        rest = _SHORT_ACK.sub("", rest.strip())
    return rest.strip(" .!") == "" and rest != text.strip()


def _cat(sit: dict) -> str:
    c = set(sit.get("obj_cats") or [])
    if c & {"DEVICE", "P-DEVICE"} and not c & {"VEHICLE"}:
        return "DEVICE"
    if c & {"VEHICLE", "P-VEHICLE"}:
        return "VEHICLE"
    if c & {"BUILDPART", "P-BUILDING", "BUILDING"}:
        return "BUILDPART"
    if c & {"CLOTHING", "P-CLOTHING"}:
        return "CLOTHING"
    if c & {"FURNITURE", "P-FURNITURE"}:
        return "FURNITURE"
    return ""


_INJ_SUB = [("sting", r"\b(?:sting|stung|stinger|bee|wasp|hornet|gestochen|stachel|wespe|biene|hornisse)\b"),
            ("burn", r"\b(?:burn\w*|scald\w*|verbrannt|verbrüht|verbrennung)\b"),
            ("cut", r"\b(?:cut|sliced|knife|gash|schnitt\w*|geschnitten|messer)\b"),
            ("bite", r"\b(?:bit|bitten|bite|gebissen|biss)\b"),
            ("head", r"\b(?:hit my head|bumped my head|head injury|kopf (?:gestoßen|angeschlagen))\b"),
            ("sprain", r"\b(?:sprain\w*|twist\w*|rolled my ankle|umgeknickt|verstaucht|verdreht|gezerrt)\b")]


class Composer:
    def __init__(self, bank, pick):
        self.moves = getattr(bank, "understand", {}) or {}
        self.pick = pick                     # Assistant._pick: deterministic, never the same variant twice in a row
        self.learner = None                  # engramm/learn: the user's corrections and which moves land

    def __bool__(self) -> bool:
        return bool(self.moves) and bool(lexicon("en"))

    # -- state ---------------------------------------------------------------------------------------------------
    @staticmethod
    def active(st) -> dict | None:
        sit = st.uses.get("u_sit")
        if isinstance(sit, dict) and st.turn - sit.get("turn", -99) <= LIVE:
            return sit
        return None

    def observe(self, st, msg: str, lang: str) -> tuple[Frame, dict | None, bool]:
        """Parse the message; a new situation replaces the active one. Returns (frame, situation, is_new)."""
        f = parse(msg, lang, extra=self.learner.extra if self.learner is not None else None)
        sit = self.active(st)
        new = False
        if f.kind and f.rule_kind and not (f.question and not (f.obj or f.body or f.who not in ("", "me"))):
            same = sit and (sit["kind"] == f.kind or (f.obj and f.obj == sit.get("obj"))) and not f.question
            weak_new = sit and (f.kind in _WEAK_KINDS or _PLAN.match(msg.strip()) or len(f.words) <= 3 or
                                (st.turn - sit.get("turn", -99) <= 2 and not (f.obj and f.obj != sit.get("obj")) and
                                 f.who in ("", "me", sit.get("who")) and not f.body))
            if not same and not weak_new:
                sit = {"kind": f.kind, "lang": lang, "obj": f.obj, "obj_word": f.obj_word, "obj_det": f.obj_det,
                       "obj_cats": sorted(f.obj_cats), "who": f.who, "who_word": f.who_word, "pron": f.pron,
                       "body": f.body, "cause": f.cause, "turn": st.turn, "start": st.turn, "asked": [], "advised": False,
                       "offered": False, "sub": self._sub(msg), "valence": f.valence, "fluid": "FLUID" in f.evidence,
                       "text": msg[:300]}
                new = True
        if sit is not None:
            sit["turn"] = st.turn
            if not sit.get("sub"):
                sit["sub"] = self._sub(msg)
            if f.body and not sit.get("body"):
                sit["body"] = f.body
            st.uses["u_sit"] = sit
        return f, sit, new

    @staticmethod
    def _related(st, msg: str, f: Frame, sit: dict, fresh: bool = True) -> bool:
        """Does this message still belong to the situation? (A topic change frees the general layers.)"""
        low = msg.lower()
        if re.search(r"\b(?:anyway|anyways|by the way|btw|on another note|different topic|übrigens|egal|apropos|"
                     r"anderes thema|ganz was anderes)\b", low):
            st.uses.pop("u_sit", None)
            return False
        if FACT.match(low.strip()):
            return False                        # "I love pizza": a fact about the user, for the memory layers
        if _THANKS.match(low) or _PLAN.match(low) or _YES.match(low):
            return True
        if f.ask in ("what_do", "how", "is_bad", "should", "when", "why", "can") or re.search(
                r"\b(?:it|this|that|they|them|he|she|him|her|es|das|er|sie|ihn|ihm|ihr|dies)\b", low):
            return True
        words = set(f.words)
        for key in ("obj", "body", "who_word", "cause"):
            v = (sit.get(key) or "").lower()
            if v and (v in words or any(w.startswith(v[:5]) for w in words if len(v) >= 5)):
                return True
        if f.kind and f.kind == sit["kind"]:
            return True
        if not fresh:
            return False                        # a situation the talk has left needs an explicit link back
        content = [w for w in f.words if len(w) > 3 and lexicon(sit.get("lang", "en")).lookup(w)]
        return len(content) <= 2 or st.turn - sit.get("turn", -99) <= 1 and len(f.words) <= 6

    @staticmethod
    def _sub(msg: str) -> str:
        for name, rx in _INJ_SUB:
            if re.search(rx, msg.lower()):
                return name
        return ""

    # -- speaking ------------------------------------------------------------------------------------------------
    def _fmt(self, sit: dict, lang: str) -> dict:
        if lang == "en":
            ow = sit.get("obj_word") or ""
            det = sit.get("obj_det") or ""
            it = (f"your {ow}" if det in ("my", "our") else f"the {ow}") if ow else "it"
            who = f"your {sit['who_word']}" if sit.get("who_word") else "them"
            pron = sit.get("pron") or "they"
            return {"it": it, "It": it[:1].upper() + it[1:], "who": who, "Who": who[:1].upper() + who[1:],
                    "pron": pron, "Pron": pron[:1].upper() + pron[1:],
                    "pron_feels": f"{pron} feel" if pron in ("they", "you", "i") else f"{pron} feels"}
        obj = sit.get("obj_word") or sit.get("obj") or ""
        e = lexicon("de").get(obj, "n") if obj else None
        g = e.gender if e and e.gender else ""
        Obj = obj[:1].upper() + obj[1:]
        poss = {"m": ("dein", "deinen", "deinem"), "f": ("deine", "deine", "deiner"), "n": ("dein", "dein", "deinem")}.get(g)
        if not poss or not obj:
            poss, Obj = ("das", "das", "dem"), "Ding" if not obj else Obj
            nom = acc = dat = "das"
            if obj:
                nom, acc, dat = f"das mit {'dem' if g != 'f' else 'der'} {Obj}", "es", "dem"
        else:
            nom, acc, dat = (f"{p} {Obj}" for p in poss)
        er = sit.get("pron") or "es"
        ww = sit.get("who_word") or ""
        we = lexicon("de").get(ww, "n") if ww else None
        wposs = {"m": "deinen", "f": "deine", "n": "dein"}.get(we.gender if we and we.gender else "")
        an_who = f" an {wposs} {ww[:1].upper() + ww[1:]}" if wposs and ww else ""
        return {"an_who": an_who, "obj": Obj, "Obj": Obj, "dein_nom": nom, "dein_acc": acc, "dein_dat": dat, "er": er,
                "Er": er[:1].upper() + er[1:], "ihm": {"er": "ihm", "sie": "ihr"}.get(er, "ihm"),
                "ihn": {"er": "ihn", "sie": "sie"}.get(er, "es"),
                "who": sit.get("who_word") or ""}

    def _say(self, st, lang: str, section: str, key: str, sit: dict) -> str:
        opts = (self.moves.get(lang) or {}).get(section, {})
        opts = opts.get(key) if isinstance(opts, dict) else opts
        if not opts:
            return ""
        if isinstance(opts, str):
            opts = [opts]
        return self.pick(st, f"u:{lang}:{section}:{key}", list(opts), **self._fmt(sit, lang))

    def _react(self, st, lang: str, sit: dict) -> str:
        k = sit["kind"]
        if sit.get("who") not in ("me", "") and k in ("INJURY", "ILLNESS"):
            return self._say(st, lang, "react", f"{k}_other", sit)
        if k == "DAMAGE" and sit.get("obj_word") and lang == "en" and sit.get("obj_det") in ("my", "our"):
            return self._say(st, lang, "react", "DAMAGE_it", sit)
        return self._say(st, lang, "react", k, sit)

    def _question(self, st, lang: str, sit: dict) -> str:
        k, cats, asked = sit["kind"], set(sit.get("obj_cats") or []), sit.setdefault("asked", [])
        if k == "DAMAGE":
            c = _cat(sit)
            cand = ["damage_off"] if c == "DEVICE" and sit.get("fluid") else ["damage_safe"] if c == "VEHICLE" else \
                ["damage_source"] if c == "BUILDPART" and sit.get("fluid") else \
                ["damage_works"] if c in ("DEVICE", "VEHICLE", "") and not sit.get("fluid") else []
            cand += ["damage_warranty"] if c in ("DEVICE",) else []
        elif k == "INJURY":
            if sit.get("who") not in ("me", ""):
                cand = []                         # the reaction already asked how they are
            else:
                cand = ["injury_allergy"] if sit.get("sub") == "sting" else ["injury_move"] if sit.get("sub") == "sprain" \
                    else ["injury_bad"]
        elif k == "ILLNESS":
            cand = ["illness_long"] if sit.get("who") in ("me", "") else []
        else:
            cand = [_FIRST_Q[k]] if k in _FIRST_Q else []
        cand += _SECOND_Q.get(k, [])
        for q in cand:
            if q not in asked:
                asked.append(q)
                return self._say(st, lang, "ask", q, sit)
        return ""

    def _advice(self, st, lang: str, sit: dict) -> str:
        k = sit["kind"]
        adv = (self.moves.get(lang) or {}).get("advice", {})
        key = k
        if k == "DAMAGE" and sit.get("fluid") and _cat(sit) in ("FURNITURE", "CLOTHING", "") and "DAMAGE.STAIN" in adv:
            key = "DAMAGE.STAIN"
        elif k == "DAMAGE" and _cat(sit) and f"DAMAGE.{_cat(sit)}" in adv:
            key = f"DAMAGE.{_cat(sit)}"
        elif k == "INJURY" and sit.get("sub") and f"INJURY.{sit['sub']}" in adv:
            key = f"INJURY.{sit['sub']}"
        elif k == "ILLNESS" and sit.get("who") in ("child", "pet") and f"ILLNESS.{sit['who']}" in adv:
            key = f"ILLNESS.{sit['who']}"
        elif k in ("SUCCESS", "MILESTONE", "ACQUIRE", "FEEL_POS", "ACTIVITY"):
            return ""
        if key not in adv:
            key = "WORRY" if k in ("DEATH",) else key
        text = adv.get(key)
        if not text:
            return ""
        if sit.get("advised"):                 # asked again: the most important step, not the whole list twice
            first = text.split("\n")[0].lstrip("• ").strip()
            lead = "The most important thing first: " if lang == "en" else "Das Wichtigste zuerst: "
            return lead + (first[:1].lower() + first[1:] if lang == "en" else first)
        sit["advised"] = True
        if lang == "en" and k in ("INJURY", "ILLNESS"):
            from engramm.know.howto import SUB_NAMES, howto, render
            a = howto().find(sit.get("text", ""), SUB_NAMES.get(sit.get("sub") or "", []))
            if a is not None and a.kind == "HEALTH":
                text = f"{text}\n\n{render(a)}"
        head = self._say(st, lang, "advice_head", "", sit) if False else \
            self.pick(st, f"u:{lang}:advice_head", list((self.moves.get(lang) or {}).get("advice_head") or [""]))
        return f"{head}\n\n{text}"

    @staticmethod
    def _lookup(msg: str, lang: str, f: Frame, current: str) -> str | None:
        """No situation, a filler reply, and a how/what-helps question about something the encyclopedia knows:
        "how do you treat hives?" — its advice with the source."""
        if lang != "en" or not (f.question and f.ask in ("how", "what_do", "can", "other")):
            return None
        if not re.search(r"\b(?:treat|help|helps|cure|get rid|relieve|soothe|do (?:about|against|for)|prevent|heal)\b", msg, re.I):
            return None
        from engramm.know.howto import howto, render
        a = howto().find(msg)
        return render(a) if a is not None else None

    def compose(self, st, msg: str, lang: str, f: Frame, sit: dict | None, new: bool, current: str,
                current_kind: str, keys=None) -> str | None:
        """A better reply than ``current``, or None to keep it."""
        if not self or lang not in ("en", "de"):
            return None
        # general layers only give way inside a problem (or a death, a milestone): there a filler, a memory note or a
        # tip for something else is worse than a reply about what happened. Elsewhere only a true filler is replaced.
        heavy = sit is not None and sit["kind"] in ("DAMAGE", "INJURY", "ILLNESS", "LOSS", "THEFT", "CONFLICT", "FAILURE",
                                                     "MONEY", "DELAY", "DEATH", "MILESTONE", "SUCCESS")
        is_generic = generic(current, lang, memo=heavy) or (heavy and weak_keys(keys, sit["kind"]) and
                                                not (sit["kind"] in ("MILESTONE", "SUCCESS") and
                                                     any(k.startswith(("intent:thanks", "short:thanks", "de:life:thanks"))
                                                         for k in keys or [])))
        if f.urgent and not re.search(r"\b(?:112|911|999|emergency|notruf|rettungsdienst)\b", current, re.I):
            urgent = ("This sounds like an emergency — please call emergency services right now (112 in Europe, 911 in the US)."
                      if lang == "en" else "Das klingt nach einem Notfall – bitte ruf sofort den Notruf 112.")
            return urgent + ("\n\n" + current if current and not is_generic else "")
        if sit is None:
            return self._lookup(msg, lang, f, current) if is_generic else None
        low = msg.strip().lower()
        # a new situation: react, then one question (or advice if they already asked for it)
        if new:
            if not is_generic or (current_kind == "empathy" and not generic(current, lang)):
                return None
            sit["fluid"] = "FLUID" in f.evidence
            react = self._react(st, lang, sit)
            if f.question and f.ask in ("what_do", "how", "can", "other", "yesno", "should", "is_bad"):
                adv = self._advice(st, lang, sit)
                return f"{react}\n\n{adv}" if adv else None
            if self.learner is not None and self.learner.move(st, sit["kind"]) == "advise":
                adv = self._advice(st, lang, sit)       # this user would rather have advice straight away
                if adv and react:
                    return f"{react}\n\n{adv}"
            q = self._question(st, lang, sit)
            return f"{react} {q}".strip() if react else None
        asks_known = re.search(r"\b(?:what happened|what's going on|was ist (?:denn )?(?:schönes |los|passiert)|"
                               r"was ist passiert|magst du erzählen, was los ist)", current, re.I)
        if heavy and _PLAN.match(low_msg := msg.strip().lower()) and re.search(
                r"\b(?:viel spaß|genieß|enjoy|have fun|sounds exciting|that sounds exciting|klingt spannend)", current, re.I):
            is_generic = True                   # "ok, I'll call a repairman" — "Have fun!" misses the problem
        if not (is_generic or (asks_known and heavy and not re.search(
                r"\b(?:sorry|entschuldig\w*|tut mir leid|verzeih\w*)\b", msg, re.I))):
            return None
        if sit.get("lang", lang) != lang:
            return None                         # a German situation does not answer an English message
        # a situation the conversation has moved away from (nothing said about it last turn) only fills true gaps:
        # a thanks, an idea list or an answer from another layer belongs to what was talked about since
        fresh = st.turn - max(sit.get("spoke", -99), sit.get("start", -99)) <= 1
        if not self._related(st, msg, f, sit, fresh):
            return None                         # a new topic: the situation rests; the general layers answer
        if sit["kind"] in ("FEEL_NEG", "WORRY", "FEEL_POS", "PLAN", "ACTIVITY") and \
                sum(1 for x in current.split("\n") if x.startswith("• ")) >= 2:
            return None                         # "I'm bored — any ideas?": the idea list is the answer
        if not fresh and (not generic(current, lang) or _THANKS.match(low)):
            return None
        if re.match(r"(?:how (?:old|much|many|long|far|tall|big|often)|wie (?:alt|viel|viele|lange|weit|groß|oft))\b", low):
            return None                         # "how old is max?": a fact question, not a call for advice
        k = sit["kind"]
        # inside a situation
        thanks_only = _THANKS.match(low) and "?" not in low and len(low.split()) <= 7
        if thanks_only and k in ("SUCCESS", "MILESTONE", "ACQUIRE", "FEEL_POS", "ACTIVITY", "PLAN"):
            return None                         # thanks after good news: the general layers say it well
        if thanks_only:
            if sit.get("who") not in ("me", "") and k in ("INJURY", "ILLNESS"):
                return self._say(st, lang, "thanks", f"{k}_other", sit) or self._say(st, lang, "thanks", "other", sit)
            return self._say(st, lang, "thanks", k, sit) or self._say(st, lang, "thanks", "other", sit)
        if _YES.match(low) and sit.get("offered") and not sit.get("advised"):
            return self._advice(st, lang, sit) or None
        if f.question or f.ask:
            ask = f.ask
            if ask == "why" or re.match(r"(?:but |and |so )?(?:how (?:can|could) (?:that|this|it) (?:be|happen)|why would|"
                                        r"wie kann das (?:sein|passieren)|wie geht das|wieso|warum|weshalb)", low):
                return self._say(st, lang, "why", k, sit) or self._say(st, lang, "why", "other", sit)
            if ask in ("what_do", "how", "can", "other", "yesno", "when") or (ask == "" and "?" in msg):
                if ask == "yesno" and re.search(r"\b(?:normal|okay|ok|bad|serious|dangerous|schlimm|normal|gefährlich)\b", low):
                    ask = "is_bad"
                elif not sit.get("advised") or ask in ("what_do", "how", "can"):
                    adv = self._advice(st, lang, sit)
                    if adv:
                        return adv
            if ask == "why" or re.match(r"(?:but |and |so )?(?:how (?:can|could) (?:that|this) (?:be|happen)|why would|wie kann das sein|"
                                        r"wieso|warum|weshalb)", low):
                return self._say(st, lang, "why", k, sit) or self._say(st, lang, "why", "other", sit)
            if ask == "is_bad":
                return self._say(st, lang, "is_bad", k if k in ("INJURY", "ILLNESS", "DAMAGE") else "other", sit)
            if ask == "should":
                which = "comm" if re.search(r"\b(?:tell|ask|talk|call|text|message|apologi[sz]e|confront|write|sagen|fragen|"
                                             r"reden|anrufen|schreiben|entschuldigen|ansprechen)\b", low) and \
                    not re.search(r"\b(?:doctor|arzt|ärztin|vet|tierarzt|hospital|krankenhaus|112|911)\b", low) else \
                    "doctor" if re.search(r"\b(?:doctor|arzt|ärztin|vet|tierarzt|hospital|krankenhaus|er|a&e|notaufnahme)\b", low) else \
                    "repair" if re.search(r"\b(?:repair|fix|replace|buy a new|new one|reparier\w*|ersetzen|neu\w* kaufen)\b", low) else \
                    "generic"
                return self._say(st, lang, "should", which, sit)
            if not sit.get("advised"):
                adv = self._advice(st, lang, sit)
                if adv:
                    return adv
            return None
        if _PLAN.match(low):
            ack = self._say(st, lang, "plan_ack", "", sit) if False else \
                self.pick(st, f"u:{lang}:plan_ack", list((self.moves.get(lang) or {}).get("plan_ack") or []))
            wish = self._say(st, lang, "wish", k, sit) or self._say(st, lang, "wish", "other", sit)
            return f"{ack} {wish}".strip()
        # a detail
        if _BETTER.search(low):
            d = "better"
        elif _WORSE.search(low):
            d = "worse_body" if k in ("INJURY", "ILLNESS") and re.search(r"\b(?:bleed|blood|swoll|swell|blutet|geschwoll|schwillt)", low) \
                else "worse"
        elif _DONE.search(low):
            d = "done"
        elif _FEEL_NEG.search(low):
            d = "feeling_neg"
        elif _FEEL_POS.search(low):
            d = "feeling_pos"
        elif _LONG.search(low):
            d = "info_long"
        else:
            d = "info"
        if d in ("info", "info_long", "feeling_neg") and not generic(current, lang):
            return None                         # a detail: a real reply from another layer stays (sympathy, a remark)                         # "he cheated on me": the sympathy already there fits better
        if k == "DEATH" and d in ("info", "info_long"):
            d = "death_time"
        if k == "LOSS" and re.search(r"\b(?:at|in|on|im|in der|am|beim|bei) (?:the |a |my |dem |der |einem |einer )?\w+", low):
            sit.setdefault("asked", []).append("loss_last")      # they already said where
        line = self._say(st, lang, "detail", d, sit)
        if d == "better" and k in ("INJURY", "ILLNESS", "LOSS", "DAMAGE"):
            return line
        nxt = self._question(st, lang, sit)
        if not nxt and not sit.get("advised") and not sit.get("offered") and \
                k not in ("SUCCESS", "MILESTONE", "ACQUIRE", "FEEL_POS", "PLAN", "ACTIVITY"):
            sit["offered"] = True
            nxt = self.pick(st, f"u:{lang}:offer", list((self.moves.get(lang) or {}).get("offer") or []))
        return f"{line} {nxt}".strip()
