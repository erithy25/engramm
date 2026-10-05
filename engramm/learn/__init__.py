"""Learning on the user's computer (U4): corrections, taught words, style, episodes, which moves land — all exact and
removable ("forget that" / "vergiss das"), stored in ``learn.json`` next to the chat memory (engramm/learn/state.py).

The dialog calls ``Learner.pre`` before its own layers (a correction, a taught word, a style wish, "forget that" right
after something was learned, "do you remember what happened?") and ``Learner.post`` on every reply (style, rewards).
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from engramm.learn.bandit import choose
from engramm.learn.state import LearnState

_CORRECT = re.compile(r"^(?:no|nope|nah|wrong|that's not it|thats not it|that's wrong|"
                      r"nein|ne|nee|nö|falsch|stimmt nicht|das stimmt nicht)\b[ ,.!—-]*", re.I)
# what a correction can turn a situation into: events, said in so many words (not "I work from home")
_EVENT_KINDS = {"DAMAGE", "INJURY", "ILLNESS", "LOSS", "THEFT", "CONFLICT", "FAILURE", "MONEY", "DELAY", "DEATH",
                "SUCCESS", "MILESTONE", "ACQUIRE"}
_FORGET = re.compile(r"^(?:please )?(?:forget (?:that|it|this)|undo (?:that|it)|unlearn (?:that|it)|"
                     r"(?:bitte )?vergiss (?:das|es)(?: wieder)?|nimm das zurück|mach das rückgängig)\b[ .!]*(?:bitte|please)?[ .!]*$",
                     re.I)
_RESET = re.compile(r"^(?:please )?(?:forget everything you(?:'ve| have)? learned(?: from me)?|reset what you(?:'ve| have)? learned|"
                    r"(?:bitte )?vergiss alles,? was du (?:von mir )?gelernt hast|setz(?:e)? das gelernte zurück)\b", re.I)
_SHORT = re.compile(r"^(?:please |pls |bitte |can you |could you )?(?:shorter answers?(?:,? please)?|(?:please )?keep (?:it|your answers) short|be brief|"
                    r"your answers are too long|kürzere antworten|fass dich (?:bitte )?kurz|antworte (?:bitte )?kürzer)\b", re.I)
_LONG = re.compile(r"^(?:please |bitte )?(?:more detail(?:s)?,? please|longer answers|you can be more detailed|ausführlicher,? bitte|"
                   r"längere antworten|gern ausführlich)\b", re.I)
_NO_EMOJI = re.compile(r"^(?:please |pls |bitte )?(?:no (?:more )?emojis?|stop (?:using|with the) emojis?|keine emojis?|lass die emojis?)\b", re.I)
_EMOJI_OK = re.compile(r"^(?:emojis? (?:are|is) (?:fine|ok|okay)|you can use emojis?|emojis? (?:sind|ist) okay|gern emojis?)\b",
                       re.I)
_TEACH_EN = re.compile(r"^(?:an? )?([a-z][a-z-]{2,24}) is (?:an?|some kind of an?|a kind of|a type of) ([a-z][a-z -]{2,30}?)[.!]?$",
                       re.I)
_TEACH_DE = re.compile(r"^(?:ein |eine )?([a-zäöüß][a-zäöüß-]{2,30}) ist (?:ein|eine|so ein|so eine|eine art) "
                       r"([a-zäöüß][a-zäöüß -]{2,30}?)[.!]?$", re.I)
_RECALL = re.compile(r"\b(?:do you remember what happened|what (?:did|have) i told? you (?:recently|lately|last week)|"
                     r"what happened to me (?:recently|lately|last week)|weißt du noch,? was (?:passiert|los) (?:ist|war)|"
                     r"was ist mir (?:letzte woche|neulich|kürzlich) passiert|was hab ich dir (?:neulich|letzte woche) erzählt)\b",
                     re.I)
_CONFUSED = re.compile(r"^(?:huh|what\?|hä|häh|wie bitte|that's not what i (?:meant|asked)|das meinte ich nicht|"
                       r"that makes no sense|ergibt keinen sinn|you misunderstood|du hast mich falsch verstanden)\b", re.I)
_THANKS = re.compile(r"\b(?:thanks|thank you|thx|great|perfect|helpful|that helps|danke|super|perfekt|hilft)\b", re.I)
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]️?")
_GENERIC_CATS = {"ARTIFACT", "EVENT", "COMM", "PLACE"}


class Learner:
    def __init__(self, path: Path | None = None):
        self.state = LearnState(path)

    @property
    def extra(self) -> dict:
        return self.state.extra

    # -- before the dialog layers -------------------------------------------------------------------------------
    def pre(self, asst, st, msg: str, lang: str) -> str | None:
        low = msg.strip().lower()
        de = lang == "de"
        if _RESET.search(low):
            self.state.reset()
            return ("Erledigt – alles, was ich von dir gelernt habe, ist gelöscht." if de else
                    "Done — everything I learned from you is gone.")
        if _FORGET.match(low) and st.uses.get("u_learned") == st.turn - 1:
            op = self.state.last()
            if op is not None and self.state.forget(op["n"]):
                st.uses.pop("u_learned", None)
                self._undo_situation(st, op)
                return ("Okay, vergessen – ich verstehe es wieder wie vorher." if de else
                        "Okay, forgotten — I'm back to how I understood it before.")
        if _SHORT.match(low) and len(low.split()) <= 8:
            self.state.set_style("length", "short")
            st.uses["u_learned"] = st.turn
            return "Alles klar, ich fasse mich kürzer." if de else "Got it — I'll keep my answers shorter."
        if _LONG.match(low) and len(low.split()) <= 8:
            self.state.set_style("length", "")
            st.uses["u_learned"] = st.turn
            return "Gern, dann wieder ausführlicher." if de else "Sure — I'll go into more detail again."
        if _NO_EMOJI.match(low):
            self.state.set_style("emoji", "off")
            st.uses["u_learned"] = st.turn
            return "Okay, ab jetzt ohne Emojis." if de else "Okay, no more emojis."
        if _EMOJI_OK.match(low):
            self.state.set_style("emoji", "")
            st.uses["u_learned"] = st.turn
            return "Gut zu wissen!" if de else "Good to know!"
        taught = self._teach(st, low, lang)
        if taught:
            return taught
        if _RECALL.search(low):
            return self._recall(asst, lang)
        return self._correct(asst, st, msg, lang)

    def _teach(self, st, low: str, lang: str) -> str | None:
        from engramm.understand.lex import lexicon
        m = (_TEACH_DE if lang == "de" else _TEACH_EN).match(low)
        if not m:
            return None
        word, what = m.group(1).lower(), m.group(2).lower().strip()
        lx = lexicon(lang)
        if any(e.pos == "n" for e in lx.lookup_base(word)) or word in lx.user:
            return None                                  # a word it knows: a statement, not a lesson
        head = what.split()[-1]
        es = [e for e in lx.lookup(head) if e.pos == "n"]
        if not es or not (set(es[0].cats) - _GENERIC_CATS or es[0].ss in ("animal", "plant", "food", "body", "person")):
            return None
        self.state.teach_word(word, lang, sorted(es[0].cats), es[0].ss)
        st.uses["u_learned"] = st.turn
        if lang == "de":
            return f"Danke, jetzt weiß ich es: {word[:1].upper() + word[1:]} ist {m.group(0).split(' ist ', 1)[1].rstrip('.!')}."
        return f"Thanks — now I know: a {word} is {what if what.startswith(('a ', 'an ')) else ('an ' if what[0] in 'aeiou' else 'a ') + what}."

    def _recall(self, asst, lang: str) -> str:
        eps = [e for e in self.state.episodes if e.get("lang", lang) == lang][-3:]
        if not eps:
            return ("Du hast mir in letzter Zeit nichts Besonderes erzählt – oder ich habe es vergessen sollen."
                    if lang == "de" else "You haven't told me about anything in particular lately — or you asked me to forget it.")
        lines = [f"• {self._when(asst, e['date'], lang)}: „{e['text']}“" if lang == "de" else
                 f"• {self._when(asst, e['date'], lang)}: “{e['text']}”" for e in reversed(eps)]
        head = "Das hast du mir erzählt:" if lang == "de" else "Here's what you told me:"
        return head + "\n" + "\n".join(lines)

    @staticmethod
    def _now(asst) -> datetime:
        clock = getattr(asst, "clock", None)
        return clock() if callable(clock) else datetime.now()

    def _when(self, asst, date: str, lang: str) -> str:
        try:
            d = (self._now(asst).date() - datetime.fromisoformat(date).date()).days
        except ValueError:
            return date
        if d <= 0:
            return "heute" if lang == "de" else "today"
        if d == 1:
            return "gestern" if lang == "de" else "yesterday"
        if d < 14:
            return f"vor {d} Tagen" if lang == "de" else f"{d} days ago"
        return date

    def _correct(self, asst, st, msg: str, lang: str) -> str | None:
        """ "No, I lost it — nobody stole it": the situation was read wrong. Learn from it and answer the right one."""
        from engramm.understand.classify import classifier, features
        from engramm.understand.frames import parse
        comp = getattr(asst, "composer", None)
        if comp is None or not _CORRECT.match(msg.strip()):
            return None
        sit = comp.active(st)
        if not sit or st.turn - sit.get("start", -99) > 3 or not sit.get("text"):
            return None
        rest = _CORRECT.sub("", msg.strip()) or msg
        f2 = None                                # the first clause that says what it was ("nobody stole it" does not)
        for clause in re.split(r"[,;]| but | and | aber | sondern | und ", rest):
            fc = parse(clause.strip(), lang, extra=self.extra) if clause.strip() else None
            k = fc.rule_kind if fc is not None else ""
            if k in _EVENT_KINDS and not fc.negated and k != sit["kind"]:
                f2 = fc
                break
        if f2 is None or (f2.question and not f2.rule_kind):
            return None
        good = f2.rule_kind or f2.kind              # what they say it was, in so many words
        clf = classifier()
        if not clf:
            return None
        f0 = parse(sit["text"], lang, use_model=False)
        feats = features(f0, sit["text"], f0.kind)
        scores = clf.p.scores(feats)
        for k, d in self.extra.items():
            if k in feats and k != "__ex__":
                for c, v in d.items():
                    scores[c] = scores.get(c, 0.0) + v
        op = self.state.correct(feats, scores, good, sit["kind"], text=sit["text"])
        if op is None:
            return None
        st.uses["u_learned"] = st.turn
        st.uses["u_before"] = dict(sit)
        sit.update({"kind": good, "asked": [], "advised": False, "offered": False, "turn": st.turn,
                    "valence": f2.valence})
        if f2.obj and not sit.get("obj"):
            sit.update({"obj": f2.obj, "obj_word": f2.obj_word, "obj_det": f2.obj_det, "obj_cats": sorted(f2.obj_cats)})
        st.uses["u_sit"] = sit
        ack = "Ah, verstehe – da hatte ich dich falsch verstanden." if lang == "de" else \
            "Ah, I see — I got that wrong, sorry."
        react = comp._react(st, lang, sit)
        q = comp._question(st, lang, sit)
        return " ".join(x for x in (ack, react, q) if x)

    @staticmethod
    def _undo_situation(st, op: dict) -> None:
        if op["op"] == "correct" and isinstance(st.uses.get("u_before"), dict):
            st.uses["u_sit"] = st.uses.pop("u_before")

    # -- moves (bandit) and episodes ----------------------------------------------------------------------------
    def move(self, st, kind: str) -> str | None:
        """'ask' or 'advise' first in a new situation of this kind (None: the default)."""
        arm = choose(self.state.bandit, kind, f"{self.state.seq}:{st.turn}:{kind}")
        st.uses["u_arm"] = (f"{kind}:{arm or 'ask'}", st.turn)
        return arm

    def remember(self, asst, kind: str, obj: str, text: str, lang: str) -> None:
        self.state.episode(self._now(asst).date().isoformat(), kind, obj, text, lang)

    # -- after the dialog layers --------------------------------------------------------------------------------
    def post(self, st, msg: str, text: str, via: str) -> str:
        arm = st.uses.get("u_arm")
        if isinstance(arm, (list, tuple)) and arm[1] == st.turn - 1 and via != "learn":
            low = msg.strip().lower()
            if _CONFUSED.search(low):
                self.state.reward(arm[0], False)
            elif _THANKS.search(low):
                self.state.reward(arm[0], True)
            st.uses.pop("u_arm", None)
        if self.state.style.get("length") == "short" and via not in ("facts", "memory", "learn"):
            text = _shorten(text)
        if self.state.style.get("emoji") == "off":
            text = re.sub(r"[ \t]+(?=\n|$)", "", re.sub(r"[ \t]{2,}", " ", _EMOJI.sub("", text))).strip()
        return text


def _shorten(text: str) -> str:
    """At most two bullet points of a list, and the encyclopedia part left out (its source stays one ask away)."""
    parts = text.split("\n\n")
    out = []
    for p in parts:
        if p.startswith(("From the encyclopedia:",)):
            continue
        lines = p.split("\n")
        if sum(1 for x in lines if x.startswith("• ")) > 2:
            keep, n = [], 0
            for x in lines:
                if x.startswith("• "):
                    n += 1
                    if n > 2:
                        continue
                keep.append(x)
            p = "\n".join(keep)
        out.append(p)
    return "\n\n".join(out)
