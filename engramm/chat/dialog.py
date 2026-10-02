"""The conversation layer (Chat v3, phase 0): small talk, feelings, tools, memory commands,
"tell me about X", whole-sentence answers — on top of the unchanged question-answering core.

``ChatBot`` (bot.py) stays the registered QA and memory core: its look-up, fact memory, pronoun
resolution and exact forgetting are used as they are, so every earlier measurement still holds.
``Assistant.turn(state, message)`` decides per sentence what to do (acts.py), asks the core
where a question or a statement needs it, and writes the reply from the conversation bank
(bank.py) and the realiser (realize.py).

What is remembered changed: a statement is learnt only when it carries something to remember
— a fact the fact memory recognises, something about you ("I …", "my …"), a named thing — or
when you say "remember that …". "lol", "the weather is nice" and "I'm so tired" are answered,
not stored.

A ``DialogState`` belongs to one conversation (the app keeps one per chat); it holds the core's
pronoun context, what ENGRAMM just asked, the last answer (for "why?", "tell me more") and the
reply counters that keep replies from repeating. Everything is deterministic: the same
conversation with the same messages gets the same replies.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from collections import Counter
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from engramm.chat.about import About, AboutFinder, clean_sentence
from engramm.chat.acts import Unit, classify
from engramm.chat.bank import Bank, choose, expand_chat, load_bank, normalise
from engramm.chat.bot import CHAT_PREFIX, Reply, message_type, source_id
from engramm.chat.everyday import _GENRES
from engramm.chat.facts import USER, facts_from_text
from engramm.chat.german import is_german, understand
from engramm.chat.realize import _acronyms as _acronym_case, answer_sentence, article, personal_sentence, to_second_person
from engramm.chat.smart import (bare_followup, experience, gibberish, is_discourse, is_mash, offer_in, rebuild_question,
                                short_answer, swap_person)

FRESH_CTX = {"answer": None, "atype": None, "mention": None, "last_learned": None}
RECENT = 40                                  # replies remembered to avoid repeats
# intents that only add a short word when the message also asks something else
_SHORT = {"greeting": ["Hi!", "Hello!", "Hey!"], "greeting_morning": ["Good morning!"],
          "greeting_afternoon": ["Good afternoon!"], "greeting_evening": ["Good evening!"],
          "thanks": ["You're welcome!", "Happy to help!"], "apology": ["No worries!"],
          "how_are_you": ["I'm doing well, thanks!"], "bot_state_back": ["I'm good, thanks!"],
          "user_fine": ["Glad to hear it!"], "positive": ["Nice!"], "laugh": ["Haha!"], "holiday": ["Thank you!"]}
_SHORT_NAMED = {"greeting": ["Hi {name}!", "Hello {name}!", "Hey {name}!"], "greeting_morning": ["Good morning, {name}!"],
                "greeting_evening": ["Good evening, {name}!"]}
_DROP_WITH_CONTENT = {"talk_request", "ack", "yes", "no", "wait", "topic_suggest", "confused", "user_bored",
                      "nothing_much", "right"}
_CATEGORY_KEYS = [("#name", "name"), ("#home", "home"), ("#job", "job"), ("#employer", "employer"),
                  ("#food", "food"), ("#colour", "colour"), ("#car", "car"), ("#birth", "birth"),
                  ("#origin", "origin"), ("#fav", "fav")]
_ASK_FOR_CATEGORY = {"#name": "ask_name", "#home": "ask_home", "#job": "ask_job", "#food": "ask_food",
                     "#colour": "ask_colour"}
_CAPS_NAME = re.compile(r"\b[A-Z][a-zA-Z'-]+")


@dataclass
class DialogState:
    conversation: str = "default"
    ctx: dict = field(default_factory=lambda: dict(FRESH_CTX))
    turn: int = 0
    uses: dict = field(default_factory=dict)
    recent: list = field(default_factory=list)
    pending: dict | None = None               # a question ENGRAMM asked: {"slot", "store", "turn"}
    last_reply: str = ""
    last_fact: dict | None = None             # the last answer: evidence, source, answer, question
    last_about: dict | None = None            # for "tell me more"
    asked: list = field(default_factory=list)  # questions ENGRAMM asked in this conversation
    rps: bool = False                         # waiting for rock / paper / scissors
    last_draft: dict | None = None            # the last written draft (WritingRequest), for edits
    draft_turn: int = -1
    offer: dict | None = None                 # what ENGRAMM's last reply offered ("Want a joke?"), for "yes"
    topic: dict | None = None                 # the thing being talked about: {"title", "name", "type", "turn"}
    last_q: str | None = None                 # the last question (pronouns resolved), for "where?" / "and X?"
    last_q_named: str | None = None           # the last question that names something, for "and X?"
    last_exp: dict | None = None              # the last moment you told ("my boss yelled at me"), for "what should I do?"
    last_list: dict | None = None             # the last suggestions, for "tell me about the second one"
    game: dict | None = None                  # a quiz question or riddle waiting for your answer
    game_score: tuple | None = None
    gib: int = 0                              # replies to gibberish in a row
    last_message: str = ""
    last_kind: str = ""
    last_action: dict | None = None           # the last joke / fact / quiz / suggestions, for "another one"
    lang: str = "en"                          # the language of the conversation ("de" after a German message)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> DialogState:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class _Part:
    role: str          # prefix | main | learn | follow
    text: str


class Assistant:
    def __init__(self, bot, bank: Bank | None = None, clock=None, kb_path=None, nlp_dir=None):
        self.bot = bot
        self.bank = bank or load_bank()
        self.clock = clock                      # callable → datetime (tests fix the date)
        self.about = AboutFinder(bot.c, getattr(bot, "r", None))
        self.kgqa = None
        path = kb_path
        if path is None and getattr(bot.c, "index_dir", None) is not None:
            for cand in (bot.c.index_dir / "kb.sqlite", bot.c.index_dir.parent / "kb.sqlite"):
                if cand.exists():
                    path = cand
                    break
        if path is not None and Path(path).exists():
            from engramm.kb.kgqa import KGQA
            from engramm.kb.store import FactBank
            today = clock().date() if clock else None
            self.kgqa = KGQA(FactBank(path), today=today)
        # requests ENGRAMM cannot carry out (alarms, music, live data): the counted intent classifier
        from engramm.chat.device import DeviceRequests, find_model
        index_dir = getattr(bot.c, "index_dir", None)
        model = find_model(nlp_dir, index_dir / "nlp" if index_dir is not None else None,
                           Path(__file__).resolve().parents[2] / "models" / "nlp")
        self.device = DeviceRequests(model) if model is not None else None
        from engramm.nlp.spell import Speller
        spell = next((d / "spell.json" for d in (Path(nlp_dir) if nlp_dir else None, index_dir)
                      if d is not None and (d / "spell.json").exists()), None)
        self.speller = Speller.load(spell) if spell is not None else None
        from engramm.chat.events import EventBook
        mem_path = getattr(bot.memory, "path", None)
        self.events = EventBook(Path(mem_path).with_suffix(".events.json") if mem_path else None)
        from engramm.chat.everyday import Everyday
        self.everyday = Everyday(self)
        self.atlas = None                       # engramm/web/atlas.py, set by the server when channels exist

    # -- helpers ------------------------------------------------------------------------------

    def _pick(self, st: DialogState, key: str, options: list[str], **fmt) -> str:
        n = st.uses.get(key, 0)
        st.uses[key] = n + 1
        # the variants this key gave lately count as recent too: a part of a longer reply (an opening
        # line) is never in st.recent as such
        mine = st.uses.get(key + "#last", [])
        text = choose(options, f"{st.conversation}|{key}|{n}", st.recent + mine)
        st.uses[key + "#last"] = (mine + [text])[-max(1, len(options) - 1):]
        return _fill(text, **fmt)

    def _reply(self, st: DialogState, path: str, **fmt) -> str:
        return self._pick(st, path, self.bank.reply(path), **fmt)

    def user_name(self) -> str | None:
        self.bot.refresh()
        texts = list(self.bot.user_texts())
        order = {sid: i for i, sid in enumerate(texts)}
        names = [(order.get(f.source, -1), f.object) for f in self.bot.facts.facts
                 if f.subject == USER and "#name" in f.relation]
        return max(names)[1] if names else None

    def _now(self):
        return self.clock() if self.clock else None

    def _german(self, st: DialogState, msg: str) -> Reply:
        """A German message (engramm/chat/german.py): chat, feelings, crises, memory, suggestions,
        advice, moments, and knowledge questions through the English fact bank
        (engramm/chat/german_bridge.py), answered in German where the answer is a fact."""
        from engramm.chat.german import advice_de, experience_de, neutral_de, normalise_de, rec_kind_de
        de = self.bank.de
        dd = de.get("daily", {})
        st.lang = "de"
        s = normalise_de(msg)
        u = understand(msg, de)
        name = self.user_name()
        known = self.speller.known if self.speller is not None else None
        if u.kind not in ("safety", "remember", "ask_name", "calc", "intent") and gibberish(msg, known):
            return Reply(msg, "unknown", self._pick(st, "de:gib", dd["gibberish"]), via="gibberish")
        if u.kind == "fallback" or u.kind == "feeling":
            n = neutral_de(s)
            if n is not None:
                return Reply(msg, "smalltalk", self._pick(st, f"de:short:{n}", dd["short"][n]), via="german")
            if re.fullmatch(r"(?:noch )?mehr|noch (?:ein paar|einen|eine|einer|eins)|nochmal|weiter", s):
                la = st.last_action
                if la and la["kind"].startswith("rec:"):
                    return self.everyday.recommend(st, msg, la["kind"][4:], la.get("genre"), more=True, lang="de")
                if la and la["kind"] in ("joke",):
                    return self._german(st, "erzähl mir einen witz")
            exp_recent = st.last_exp if st.last_exp and st.turn - st.last_exp.get("turn", -99) <= 4 else None
            kind = rec_kind_de(s)
            if kind is not None and not (kind == "activity" and exp_recent and advice_de(s)):
                return self.everyday.recommend(st, msg, kind, lang="de")
            if advice_de(s):
                exp = exp_recent
                if not exp:
                    return Reply(msg, "smalltalk", self._pick(st, "de:advice:none", dd["advice"]["none"]), via="german")
                group = self.everyday._advice_group(exp.get("text_en") or exp.get("text") or "", exp)
                group = group if group in dd["advice"] else "generic"
                return Reply(msg, "smalltalk", self._pick(st, f"de:advice:{group}", dd["advice"][group]), via="german")
            de_extra = self._german_extra(st, msg, s)
            if de_extra is not None:
                return de_extra
            bridged = self._german_question(st, msg, s)
            if bridged is not None:
                return bridged
            dm = _DISLIKE_DE.match(s)
            if dm:
                # "ich mag keine pilze": a dislike, remembered (in English, like every fact)
                x = (dm.group("x") or dm.group("z") or dm.group("y") or "").strip()
                shown = " ".join(w[:1].upper() + w[1:] for w in x.split())     # German nouns: "Pilze"
                if _RELATABLE_DE.fullmatch(x):
                    return Reply(msg, "smalltalk", self._pick(st, "de:dislike_relatable", dd["dislike_relatable"],
                                                              x=shown), via="german")
                if x in ("fleisch", "fleisch und fisch"):
                    st.uses["diet"] = "vegetarian"            # "ich esse kein Fleisch": food ideas without meat
                    self._learn(st, ["I'm vegetarian."], msg)
                    return Reply(msg, "learned", "Alles klar, kein Fleisch – das merke ich mir für Essensideen!",
                                 via="german")
                self._learn(st, [f"I don't like {x}."], msg)
                return Reply(msg, "learned", self._pick(st, "de:dislike", dd["dislike"], x=shown), via="german")
            ex = experience_de(s) if not (u.kind == "feeling" and len(s.split()) <= 4) else None
            if ex is not None:
                val, topic, person, timeword = ex
                shape = "person" if topic and person else "thing" if topic else "time" if timeword else "plain"
                st.last_exp = {"valence": val, "topic": topic, "person": person, "text": msg,
                               "text_en": _de_advice_hint(s), "turn": st.turn}
                return Reply(msg, "empathy", self._pick(st, f"de:moment:{val}:{shape}", dd["experience"][val][shape],
                                                         topic=topic or ""), via="german")
        if u.kind == "safety":
            st.pending = None
            return Reply(msg, "safety", u.data["response"], via="safety")
        if u.kind == "remember":
            inner = self._turn(st, u.data["english"])
            if inner.kind != "learned":
                return Reply(msg, "unknown", self._pick(st, "de:fallback", de["replies"]["fallback"]), via="german")
            key = "learned_name" if u.data["what"] == "name" else "learned_fact"
            text = self._pick(st, f"de:{key}", de["replies"][key], name=u.data["value"])
            return Reply(msg, "learned", text, source=inner.source, via="german")
        if u.kind == "ask_name":
            if name:
                return Reply(msg, "answer", _fill(de["replies"]["name_known"][0], name=name), via="german")
            st.pending = {"slot": "name", "store": self.bank.fun["questions"]["ask_name"]["store"], "turn": st.turn}
            return Reply(msg, "unknown", de["replies"]["name_unknown"][0], via="german")
        if u.kind == "calc":
            from engramm.chat.tools import calculate
            res = calculate(u.data["expr"])
            if res is not None and res.value is not None:
                return Reply(msg, "tool", f"{u.data['expr']} = {res.value.replace('.', ',')}", via="tool")
        if u.kind == "intent":
            it = next(i for i in de["intents"] if i["id"] == u.data["id"])
            if it["id"] == "joke":
                st.last_action = {"kind": "joke", "turn": st.turn}
            opts = it.get("responses_named") if name and it.get("responses_named") else it["responses"]
            return Reply(msg, "smalltalk", self._pick(st, f"de:{it['id']}", opts, name=name or ""), via="german")
        if u.kind == "feeling":
            fe = de["feelings"]
            if u.data["negated"]:
                opts = fe["negated_negative"] if u.data["valence"] == "negative" else fe["negated_positive"]
            else:
                opts = next(c for c in fe["categories"] if c["id"] == u.data["id"])["responses"]
            return Reply(msg, "empathy", self._pick(st, f"de:feeling:{u.data['id']}", opts), via="german")
        if re.match(r"^(?:wer|was|wann|wo|wie|welche[rsmn]?|warum|wieso|weshalb|woher|wohin)\b", s):
            return Reply(msg, "unknown", self._pick(st, "de:knowledge", dd["knowledge_de"]), via="german")
        return Reply(msg, "unknown", self._pick(st, "de:fallback", de["replies"]["fallback"]), via="german")

    def _german_extra(self, st: DialogState, msg: str, s: str) -> Reply | None:
        """German everyday tools and follow-ups: the time and the date, "15 Prozent von 80", and
        "und von Italien?" after "Was ist die Hauptstadt von Spanien?"."""
        now = self.clock() if self.clock else dt.datetime.now()
        if re.fullmatch(r"(?:sag mal,? )?(?:wie spät ist es(?: gerade| jetzt)?|wie viel uhr ist es|wieviel uhr ist es|"
                        r"welche uhrzeit haben wir|was ist die uhrzeit)", s):
            return Reply(msg, "tool", f"Es ist {now:%H:%M} Uhr (laut der Uhr dieses Computers).", via="tool")
        if re.fullmatch(r"(?:sag mal,? )?(?:welcher tag ist (?:heute|es)|welches datum (?:haben wir|ist heute)(?: heute)?|"
                        r"der wievielte ist heute|was für ein tag ist heute|welchen tag haben wir(?: heute)?)", s):
            days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                      "November", "Dezember"]
            return Reply(msg, "tool", f"Heute ist {days[now.weekday()]}, der {now.day}. {months[now.month - 1]} {now.year}.",
                         via="tool")
        m = re.fullmatch(r"(?:was (?:ist|sind|ergibt|ergeben)|wie ?viel (?:ist|sind)|rechne|berechne) (\d+(?:[.,]\d+)?) ?"
                         r"(?:%|prozent) (?:von|aus) (\d+(?:[.,]\d+)?)", s)
        if m:
            a, b = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
            v = a * b / 100
            shown = (f"{v:.2f}".rstrip("0").rstrip(".")).replace(".", ",")
            st.uses["last_calc"] = [st.turn, str(v)]
            return Reply(msg, "tool", f"{m.group(1)} % von {m.group(2)} sind {shown}.", answer=shown, via="tool")
        m = re.fullmatch(r"und (?:von |in |für |bei |mit |über )?(?P<x>[a-zäöüß][a-zäöüß .-]{1,30})", s)
        last = st.uses.get("de_last_q")
        if m and last and st.turn - last[0] <= 3 and last[2] and last[2] in last[1]:
            again = last[1].replace(last[2], m.group("x").strip(), 1)
            return self._german_question(st, msg, again)
        return None

    def _german_question(self, st: DialogState, msg: str, s: str) -> Reply | None:
        from engramm.chat.german_bridge import de_sentence, de_value, to_english
        hit = to_english(s)
        if hit is None:
            return None
        english, kind, x_en, x_de = hit
        st.uses["de_last_q"] = [st.turn, s, (x_de or "").lower()]
        dd = self.bank.de["daily"]
        if kind == "about":
            rep = self._about(st, Unit("about", english, english.lower(), data={"kind": "tell", "topic": x_en}))
            if rep.kind == "about":
                rep.text = f"{dd['english_text']} {rep.text}"
                rep.message = msg
                return rep
            rep = self._question(st, english.replace("tell me about", "who is"))
            if rep.kind != "answer":
                return Reply(msg, "unknown", self._pick(st, "de:unknown", dd["unknown"]), via="german")
        elif kind == "compare":
            rep = self.everyday.compare(st, english, english.lower())
            if rep is None or rep.kind != "answer":
                return Reply(msg, "unknown", dd["compare_none"], via="german")
            rep.text = _de_compare(rep.text, s)
            rep.message = msg
            return rep
        else:
            pron = re.search(r"\b(?:er|sie|ihn|ihm|ihr|sein|seine|ihre)\b", s)
            rep = self._question(st, english + "?")
            if rep.via == "clarify" or (pron and rep.kind != "answer"):
                return Reply(msg, "unknown", dd["who_mean"].replace("{x}", pron.group(0) if pron else x_en), via="clarify")
        rep.message = msg
        if rep.kind != "answer":
            rep.text = self._pick(st, "de:unknown", dd["unknown"])
            return rep
        if rep.via == "kb":
            name = re.sub(r"\s*\([^)]*\)$", "", (rep.source or {}).get("key") or x_en)
            if x_de and x_de.lower() != x_en.lower() and x_en.lower() == name.lower() and \
                    x_en.lower() not in ("he", "she", "it", "him", "her"):
                name = x_de                     # "Frankreich", as the user wrote it
            sent = de_sentence(kind, name, rep.answer or "", rep.text)
            if sent:
                rep.text = sent
                return rep
        rep.text = f"{dd['english_text']} {rep.text}"
        return rep

    # -- the turn -----------------------------------------------------------------------------

    def turn(self, st: DialogState, message: str) -> Reply:
        t0 = time.time()
        bot = self.bot
        bot.context = dict(st.ctx)
        msg = " ".join(message.strip().split())
        self._spelled = None
        try:
            rep = self._turn(st, msg)
            if self._spelled and not rep.resolved:
                rep.resolved = self._spelled          # shown as "I read this as …"
        finally:
            st.ctx = dict(bot.context)
            bot.context = dict(FRESH_CTX)
        rep.message = message
        rep.seconds = time.time() - t0
        if rep.text and rep.text == st.last_reply and normalise(message) != normalise(st.last_message or ""):
            if rep.kind == "unknown":
                rep.text = self._pick(st, "daily:unknown_again", self.bank.daily["unknown_again"])
        st.last_message = message
        st.last_kind = rep.kind
        self._track(st, rep, msg)
        if rep.via != "gibberish":
            st.gib = 0
        st.turn += 1
        st.last_reply = rep.text
        st.recent = (st.recent + [rep.text])[-RECENT:]
        return rep

    def _track(self, st: DialogState, rep: Reply, msg: str) -> None:
        """Remember what the conversation is about: the topic (for "tell me more", "is it good?",
        pronouns) and the last question (for "where?", "and Germany?"), and what the reply offers."""
        src = rep.source or {}
        if rep.via == "kb" and src.get("key"):
            title = src["key"]
            st.topic = {"title": title, "name": re.sub(r"\s*\([^)]*\)$", "", title), "turn": st.turn}
        elif rep.via in ("about", "facts-bank") and src.get("key"):
            st.topic = {"title": src["key"], "name": re.sub(r"\s*\([^)]*\)$", "", src["key"]), "turn": st.turn}
        elif rep.kind == "answer" and rep.via == "lookup" and rep.answer and rep.answer[:1].isupper():
            st.topic = {"title": rep.answer, "name": rep.answer, "turn": st.turn}
        if rep.kind in ("answer", "unknown") and rep.via in ("kb", "lookup", "about", "facts", "memory") \
                and message_type(rep.resolved or msg) == "question":
            st.last_q = rep.resolved or msg
            if re.search(r"\s[A-Z]", st.last_q):
                st.last_q_named = st.last_q
        if rep.kind == "unknown" and rep.via == "lookup":
            # an unanswered question must not leave an old name behind for "he" or "it"
            st.ctx.update({"answer": None, "atype": None})
        if st.offer is None or st.offer.get("turn") != st.turn:
            kind = offer_in(rep.text)
            st.offer = {"kind": kind, "turn": st.turn} if kind else None
        theme = _theme_of(st, rep)
        if theme:
            recap = st.uses.setdefault("recap", [])
            if theme in recap:
                recap.remove(theme)
            recap.append(theme)
            del recap[:-12]

    def _turn(self, st: DialogState, msg: str) -> Reply:
        if not msg:
            return Reply(msg, "nothing", "Please type something.")
        de = self.bank.de
        if de and is_german(msg, de) and self.bank.safety_rule(normalise(msg, fillers=False)) is None:
            return self._german(st, msg)
        if de and st.lang == "de":
            from engramm.chat.german import neutral_de, normalise_de
            if neutral_de(normalise_de(msg)) is not None or re.fullmatch(r"(?:noch )?mehr|nochmal", normalise_de(msg)) \
                    or re.fullmatch(r"(?:hey|hi|hallo|hello|moin|servus|yo|huhu)+(?: (?:hey|hi|du|engramm))?", normalise_de(msg)) \
                    or gibberish(msg, self.speller.known if self.speller is not None else None):
                return self._german(st, msg)      # "haha", "ok", "ja" in a German conversation stay German
            if len(re.findall(r"[a-z]+", msg.lower())) >= 2:
                st.lang = "en"
        msg = expand_chat(msg)                            # "wats ur name" → "what's your name"
        msg = self._prefer_correction(msg)                # "actually i prefer ramen" right after a favourite
        msg = _split_self_statements(msg)                 # "my name is Sam and I'm a teacher": two facts
        have = st.uses.get("have_noun")
        if have and st.turn - have[1] <= 2:               # "their names are Mia and Leo" after "I have two kids"
            m = _THEIR_NAMES.match(msg.strip()) or _BARE_NAMES.fullmatch(msg.strip(" .!"))
            if m:
                msg = f"My {have[0]} are called {(m.group(1) if m.re is _THEIR_NAMES else m.group(0)).strip(' .!')}."
        norm = normalise(msg)
        own = self._about_me(st, msg, norm)
        if own is not None:
            return own
        lk = _I_LIKE.match(norm)
        if lk:
            st.uses["last_like"] = [st.turn, _place_case(lk.group("x").strip(" .!"))]
        life = self._life(st, msg, norm)
        if life is not None:
            return life
        dm = _DAY_WAS.match(norm)
        if dm:
            key = "day_bad" if dm.group("bad") else "day_good"
            what = dm.group("what")
            what = "your day" if what in ("today", "it", "the day", "my day") else what.replace("my ", "your ")
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", self.bank.daily[key], x=what), via="empathy")
        if _PET_PEEVE.match(msg.strip()):
            return Reply(msg, "smalltalk", self._pick(st, "daily:pet_peeve", self.bank.daily["pet_peeve"]),
                         via="empathy")
        dm = _DISLIKE.match(msg.strip())
        if dm and _RELATABLE.fullmatch(dm.group("x").strip().lower()):
            x = dm.group("x").strip().lower()
            return Reply(msg, "smalltalk", self._pick(st, "daily:dislike_relatable", self.bank.daily["dislike_relatable"],
                                                      x=x[:1].upper() + x[1:] if x.endswith("days") else x),
                         via="empathy")
        if dm:
            # "i dont like movies": remember it as a dislike and ask what they do enjoy
            x = dm.group("x").strip()
            rep = self._learn(st, [msg], msg)
            if rep.kind == "learned":
                rep.text = self._pick(st, "daily:dislike", self.bank.daily["dislike"], x=x)
            st.last_action = {"kind": "dislike", "turn": st.turn, "x": x}
            return rep
        la_kind = (st.last_action or {}).get("kind")
        if _DOUBT.fullmatch(norm) and st.last_kind == "answer" and st.last_fact and st.last_fact.get("evidence"):
            return self._why(st, msg)
        mild = re.fullmatch(r"(?:cool|neat|nice|ok cool|oh nice)[!.]*", norm) is not None
        if _SURPRISE.fullmatch(norm) and st.last_reply and (
                (st.last_kind in ("answer", "about") and not mild) or
                (la_kind == "fun_fact" and st.turn - (st.last_action or {}).get("turn", -99) <= 1)):
            # "that's crazy" right after a fact: go along with it, as a person would
            return Reply(msg, "smalltalk", self._pick(st, "daily:surprise", self.bank.daily["surprise"]), via="smalltalk")
        if _SURPRISE.fullmatch(norm) and st.last_kind == "unknown" and st.last_reply:
            return Reply(msg, "smalltalk", self._pick(st, "daily:surprise_unknown", self.bank.daily["surprise_unknown"]),
                         via="smalltalk")
        played = self.everyday.game_answer(st, msg, norm)          # a quiz question or riddle waiting
        if played is not None:
            return played
        offer = st.offer
        st.offer = None
        if offer and offer.get("turn") == st.turn - 1:
            ans = short_answer(norm)
            if ans is None and offer["kind"] in ("joke_or_fact", "joke", "fact") and \
                    re.fullmatch(r"(?:(?:a|an|the|one|ok|okay|sure|yes|yeah)\s+)*(?:fun |interesting )?(?:joke|fact)"
                                 r"(?:\s+please)?", norm):
                ans = "yes"
            if ans is not None:
                took = self.everyday.take_offer(st, msg, norm, offer, ans)
                if took is not None:
                    return took
        le = st.last_exp
        if le and le.get("turn") == st.turn - 1 and st.last_reply.rstrip().endswith("?"):
            ans = short_answer(norm)
            if ans == "yes":
                return Reply(msg, "smalltalk", self._pick(st, "daily:offer:listen", self.bank.daily["offers"]["listen"]),
                             via="empathy")
            if ans == "no":
                st.offer = {"kind": "joke_or_fact", "turn": st.turn}
                return Reply(msg, "smalltalk", self._pick(st, "daily:moment:no", self.bank.daily["moment_no"]),
                             via="empathy")
        if _ANOTHER.match(norm):
            again = self._again(st, msg)
            if again is not None:
                return again
        wh = bare_followup(msg)
        if wh and st.last_q:
            rebuilt = rebuild_question(st.last_q, wh)
            if rebuilt:
                msg = self._spelled = rebuilt    # "where?" → "Where was William Shakespeare born?"
        expanded = self._ellipsis(st, msg)
        if expanded is not None:
            msg = self._spelled = expanded      # shown as "I read this as …"
        from engramm.web.atlas import news_request
        is_news, news_topic = news_request(msg)
        if is_news:
            return self._news(st, msg, news_topic)
        units = classify(msg, self.bank, self._now())
        if self.speller is not None and len(units) == 1 and units[0].act == "statement":
            first = msg.split()[0]
            if not self.speller.known(first) and self.speller.fix_word(first).lower() in _QUESTION_WORDS:
                units = classify(self.speller.fix(msg).rstrip(" .!") + "?", self.bank, self._now())
        if self.speller is not None and all(u.act in ("question", "about") for u in units):
            fixed = self.speller.fix(msg)       # typos and CAPITALS, only in questions (names stay as told)
            if fixed != msg and units[0].act == "question" and not fixed.rstrip().endswith("?"):
                fixed = fixed.rstrip(" .!") + "?"   # still a question after the fix
            if fixed != msg:
                units = classify(fixed, self.bank, self._now())
                msg = self._spelled = fixed
        if units[0].act == "safety":
            st.pending = None
            return Reply(msg, "safety", units[0].data["response"], via="safety")
        pending, st.pending = st.pending, None
        if pending and pending.get("turn") == st.turn - 1:          # asked in the previous turn
            filled = self._fill_pending(st, pending, msg, units)
            if filled is not None:
                return filled
        known = self.speller.known if self.speller is not None else None
        if gibberish(msg, known) and not any(u.act in ("intent", "tool", "safety") and u.intent != "gibberish"
                                             for u in units):
            st.gib += 1
            key = "first" if st.gib <= 1 else "again"
            return Reply(msg, "unknown", self._pick(st, f"daily:gib:{key}", self.bank.daily["gibberish"][key]),
                         via="gibberish")
        if len(units) == 1 and units[0].act not in ("safety", "forget", "remember", "tool", "writing"):
            req = self.everyday.request(st, msg, normalise(msg))
            if req is not None:
                return req
        if st.last_draft is not None and st.turn - st.draft_turn <= 4:
            from engramm.chat.writing import edit_command, writing_request
            cmd = edit_command(msg) if writing_request(msg) is None else None
            if cmd is not None:
                return self._edit_draft(st, msg, *cmd)
        if st.rps:
            st.rps = False
            m = re.fullmatch(r"(?:i (?:choose|pick|take) )?(rock|paper|scissors)", normalise(msg))
            if m:
                return self._rps(st, msg, m.group(1))
        if self.device is not None and len(units) == 1 and units[0].act in ("question", "statement"):
            hit = self.device.group(msg)
            # questions about the user ("when is my dentist appointment?") are memory questions
            if hit is not None and units[0].act == "question" and (hit[0] != "online" or re.search(r"\bmy\b", msg, re.I)):
                hit = None
            mt = _MEASURE_TOPIC.match(msg.strip())
            if hit is not None and mt and not re.fullmatch(r"(?:it|outside|today|the weather|out)", mt.group("t").strip(), re.I):
                hit = None
            # "I have an exam tomorrow" tells ENGRAMM something to remember; only requests are commands
            if hit is not None and units[0].act == "statement" and re.match(r"(?:i|i'm|im|i've|my|we|we're|our)\b", msg, re.I):
                hit = None
            if hit is not None:
                return Reply(msg, "unknown", self._reply(st, f"device.{hit[0]}"), via="device")
        parts: list[_Part] = []
        main: Reply | None = None
        learn: list[Unit] = []
        quiet: list[Unit] = []
        content = any(u.act not in ("intent", "empty") or (u.intent and self._is_content_intent(u.intent))
                      for u in units)
        for u in units:
            if u.act in ("statement", "feeling") and self.everyday.activity_title(u.text):
                learn.append(u)                  # "I just finished The Quiet Orchard": ask about it (see _learn)
                continue
            if u.act == "intent":
                r = self._intent(st, u, content, parts)
                if r is not None and main is None:
                    main = r
            elif u.act == "statement":
                exp = experience(u.norm)
                if is_discourse(u.norm):
                    parts.append(_Part("main", self._discourse(st, u)))
                    main = main or Reply(msg, "smalltalk", "", via="smalltalk")
                elif exp is not None:
                    parts.append(_Part("prefix", self.everyday.moment(st, exp, u.text)))
                    if self._has_fact(u.text):
                        quiet.append(u)
                    main = main or Reply(msg, "empathy", "", via="empathy")
                elif _PLAN.search(u.norm):
                    parts.append(_Part("main", self._plan(st, u)))
                    main = main or Reply(msg, "smalltalk", "", via="smalltalk")
                elif self._worth_learning(u.text):
                    learn.append(u)
                else:
                    self._chitchat(st, u, parts, alone=len(units) == 1)
            elif u.act == "feeling":
                exp = experience(u.norm)
                if exp is not None and exp.topic and u.data.get("category") in _GENERAL_MOODS and \
                        not u.data.get("negated"):
                    # "my boss was so annoying": name the boss, not just the mood
                    parts.append(_Part("prefix", self.everyday.moment(st, exp, u.text)))
                else:
                    parts.append(_Part("prefix", self._feeling(st, u)))
                st.last_exp = {"valence": u.data.get("valence"), "topic": exp.topic if exp else None,
                               "person": bool(exp and exp.person), "text": u.text, "turn": st.turn}
                if self._has_fact(u.text):
                    quiet.append(u)                 # a sad message gets no "I'll remember that"
                main = main or Reply(msg, "empathy", "", via="empathy")
            elif u.act == "remember":
                learn.append(Unit("statement", u.data["text"], normalise(u.data["text"])))
            else:
                r = self._content(st, u)
                parts.append(_Part("main", r.text))
                if main is None or main.kind in ("smalltalk", "empathy"):
                    main = r
        if learn:
            r = self._learn(st, [u.text for u in learn], msg)
            parts.append(_Part("learn", r.text))
            if main is None or main.kind in ("smalltalk", "empathy"):
                main = r
        if quiet and not learn:
            self._learn(st, [u.text for u in quiet], msg)
        if main is None:
            main = Reply(msg, "smalltalk", "", via="smalltalk")
        text = _compose(parts)
        follow = self._follow(st, units, text, main)
        if follow:
            if text.rstrip().endswith("?"):
                # one question per reply: the follow-up replaces the bank reply's closing question
                cut = re.split(r"(?<=[.!])\s+(?=[^.!?]*\?$)", text.strip())
                text = cut[0] if len(cut) > 1 else ""
                if self._follow_key:
                    follow = self.bank.fun["questions"][self._follow_key].get("text_end", follow)
            text = f"{text} {follow}".strip()
        if not text:
            text = self._reply(st, "fallback")
        main.text = text
        return main

    # -- intents ------------------------------------------------------------------------------

    def _is_content_intent(self, iid: str) -> bool:
        it = self.bank.by_id.get(iid)
        return bool(it and (it.action or iid not in _SHORT and iid not in _DROP_WITH_CONTENT))

    def _intent(self, st: DialogState, u: Unit, content: bool, parts: list[_Part]) -> Reply | None:
        it = self.bank.by_id[u.intent]
        name = self.user_name()
        others = content and not self._is_content_intent(it.id)
        if others:
            if it.id in _DROP_WITH_CONTENT:
                return None
            short = (_SHORT_NAMED.get(it.id) if name else None) or _SHORT.get(it.id)
            if short:
                parts.append(_Part("prefix", self._pick(st, f"short:{it.id}", short, name=name or "")))
            return None
        if it.action:
            r = self._action(st, it.action, u)
            if r is not None:
                parts.append(_Part("main", r.text))
                return r
        options = it.responses_named if (name and it.responses_named) else it.responses
        if it.responses_named and name:
            options = it.responses_named + [o for o in it.responses if o not in it.responses_named][:1]
        text = self._pick(st, f"intent:{it.id}", options, name=name or "", x=u.groups.get("x", ""))
        parts.append(_Part("main", text))
        if it.follow:
            st.asked.append(f"follow:{it.id}")
        return Reply(u.text, "smalltalk", text, via="smalltalk")

    def _action(self, st: DialogState, action: str, u: Unit) -> Reply | None:
        fun = self.bank.fun
        seed = f"{st.conversation}|{st.turn}"
        if action in ("joke", "fun_fact", "quote", "story"):
            st.last_action = {"kind": action, "turn": st.turn}
        if action == "joke":
            n = st.uses.get("joke", 0)
            st.uses["joke"] = n + 1
            jokes = fun["jokes"]
            order = _order(len(jokes), st.conversation + "|jokes")
            text = _join(self._pick(st, "joke_intro", self.bank.reply("joke_intro")), jokes[order[n % len(jokes)]])
            return Reply(u.text, "smalltalk", text, via="smalltalk")
        if action == "fun_fact":
            n = st.uses.get("fact", 0)
            st.uses["fact"] = n + 1
            facts = fun["facts"]
            f = facts[_order(len(facts), st.conversation + "|facts")[n % len(facts)]]
            text = _join(self._pick(st, "fact_intro", self.bank.reply("fact_intro")), f["text"])
            src = {"kind": "base", "source": "wiki", "key": f["src"]}
            st.last_fact = {"evidence": f["text"], "source": src, "answer": None, "question": None, "sure": True}
            return Reply(u.text, "about", text, source=src, evidence=f["text"], via="facts-bank")
        if action == "quote":
            n = st.uses.get("quote", 0)
            st.uses["quote"] = n + 1
            q = fun["quotes"][_order(len(fun["quotes"]), st.conversation + "|quotes")[n % len(fun["quotes"])]]
            text = _join(self._pick(st, "quote_intro", self.bank.reply("quote_intro")), f"“{q['text']}” — {q['by']}")
            return Reply(u.text, "smalltalk", text, via="smalltalk")
        if action == "story":
            n = st.uses.get("story", 0)
            st.uses["story"] = n + 1
            stories = fun["stories"]
            return Reply(u.text, "smalltalk", stories[_order(len(stories), st.conversation + "|stories")[n % len(stories)]],
                         via="smalltalk")
        if action == "coin":
            return Reply(u.text, "smalltalk", self.bank.reply("coin")[_rand(seed, 2)], via="smalltalk")
        if action == "dice":
            return Reply(u.text, "smalltalk", _fill(self.bank.reply("dice")[0], x=str(1 + _rand(seed, 6))),
                         via="smalltalk")
        if action == "pick_number":
            a, b = int(u.groups.get("a", 1)), int(u.groups.get("b", 10))
            lo, hi = min(a, b), max(a, b)
            x = lo + _rand(seed, hi - lo + 1) if hi - lo < 10**9 else lo
            return Reply(u.text, "smalltalk", self._reply(st, "pick_number", x=str(x)), via="smalltalk")
        if action == "rps":
            choice = u.groups.get("x")
            if not choice:
                st.rps = True
                return Reply(u.text, "smalltalk", self.bank.replies["rps"]["ask"], via="smalltalk")
            return self._rps(st, u.text, choice)
        if action == "memory_query":
            return self._memory_list(st, u.text)
        if action == "who_am_i":
            name = self.user_name()
            if name:
                n = len([s for s in self.bot.user_texts() if s.startswith(CHAT_PREFIX)])
                more = ("Ask “What do you know about me?” to see everything you've told me."
                        if n > 1 else "That's all you've told me so far.")
                return Reply(u.text, "answer", self._reply(st, "who_am_i.known", name=name, more=more), answer=name,
                             via="facts")
            st.pending = {"slot": "name", "store": self.bank.fun["questions"]["ask_name"]["store"], "turn": st.turn}
            return Reply(u.text, "unknown", self._reply(st, "who_am_i.unknown"), via="facts")
        if action == "repeat":
            text = st.last_reply or self._reply(st, "repeat_none")
            return Reply(u.text, "smalltalk", text, via="smalltalk")
        if action == "clarify":
            if st.last_reply and st.last_kind in ("answer", "about", "tool", "memory") and \
                    not st.last_reply.startswith(("Sorry if that was unclear", "In other words")):
                return Reply(u.text, "smalltalk", self._reply(st, "clarify.last", last=st.last_reply), via="clarify")
            return Reply(u.text, "smalltalk", self._pick(st, "daily:disc:confused",
                                                         self.bank.daily["discourse"]["confused"]), via="clarify")
        if action == "correction":
            if st.last_fact and st.last_fact.get("question"):
                st.pending = {"slot": "correction", "question": st.last_fact["question"], "turn": st.turn}
            return None                           # the intent's own responses
        if action == "why_last":
            return self._why(st, u.text)
        if action == "more":
            return self._more(st, u.text)
        if action == "ask_user":
            return self._ask_user(st, u)
        return None

    def _rps(self, st: DialogState, text: str, choice: str) -> Reply:
        bot_choice = ["rock", "paper", "scissors"][_rand(f"{st.conversation}|{st.turn}|rps", 3)]
        wins = {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
        rr = self.bank.replies["rps"]
        key = "draw" if bot_choice == choice else ("win" if (choice, bot_choice) in wins else "lose")
        return Reply(text, "smalltalk", _fill(rr[key], bot=bot_choice), via="smalltalk")

    def _ask_user(self, st: DialogState, u: Unit) -> Reply:
        qs = self.bank.fun["questions"]
        known = self._known_categories()
        for key in self.bank.fun["ask_order"]:
            if key in st.asked or key == "ask_mood":
                continue
            cat = {v: k for k, v in _ASK_FOR_CATEGORY.items()}.get(key)
            if cat and cat in known:
                continue
            st.asked.append(key)
            st.pending = {"slot": qs[key]["slot"], "store": qs[key]["store"], "turn": st.turn}
            intro = self._pick(st, "intent:topic_suggest", self.bank.by_id["topic_suggest"].responses)
            return Reply(u.text, "smalltalk", f"{intro} {qs[key]['text']}", via="smalltalk")
        return Reply(u.text, "smalltalk", "I've asked you a lot already! How about you ask me something — anything "
                                          "from history to science?", via="smalltalk")

    def _known_categories(self) -> set:
        self.bot.refresh()
        return {lab for f in self.bot.facts.facts if f.subject == USER for lab in f.relation if lab.startswith("#")}

    # -- content ------------------------------------------------------------------------------

    # -- writing ------------------------------------------------------------------------------

    def _today(self):
        return self.clock().date() if self.clock else dt.date.today()

    def _writing(self, st: DialogState, u: Unit) -> Reply:
        from engramm.chat import writing as w
        task = u.data["task"]
        spec = self.bank.writing
        text = u.text
        if task == "draft":
            req = w.parse_request(text, spec["purposes"])
            if req is None:
                return Reply(text, "smalltalk", self._reply(st, "fallback"), via="writing")
            return self._show_draft(st, text, req, intro=True)
        if task == "poem":
            m = w._POEM.match(re.sub(r"^(?:hey|hi|ok|okay|so)[,!]?\s+", "", text.strip(), flags=re.I).rstrip("?.!"))
            topic = (m.group("topic") if m else None) or "the day"
            n = st.uses.get("poem", 0)
            st.uses["poem"] = n + 1
            body = w.poem(topic, spec, f"{st.conversation}|poem|{n}")
            return Reply(text, "writing", f"Here's a short poem about {topic.strip(' ?.!')}:\n\n{body}", via="writing")
        if task == "story":
            m = w._STORY.match(text.strip().rstrip("?.!"))
            topic = m.group("topic") if m else "a curious robot"
            n = st.uses.get("story", 0)
            st.uses["story"] = n + 1
            stories = self.bank.fun["stories"]
            base = stories[_order(len(stories), st.conversation + "|stories")[n % len(stories)]]
            about = self.about.find(topic)
            intro = f"Here's a little story — and since you mentioned {topic}: " if about else "Here's a little story:"
            fact = f"\n\n(By the way: {about.sentences[0]})" if about else ""
            return Reply(text, "writing", f"{intro}\n\n{base}{fact}", via="writing",
                         source=about.source if about else None)
        if task == "summary":
            m = w._SUMMARY.match(re.sub(r"^(?:hey|hi|ok|okay|so)[,!]?\s+", "", text.strip(), flags=re.I))
            body = (m.group("text") if m else "").strip()
            if len(body.split()) <= 8:
                topic = re.sub(r"^(?:the (?:article|text|page) (?:about|on)\s+)", "", body, flags=re.I).strip(" ?.!")
                found = self.about.find(topic) if topic else None
                if not found:
                    return Reply(text, "smalltalk", "Paste the text you'd like me to summarise after “Summarize:” — "
                                                    "or name a topic, like “Summarize the article about volcanoes”.",
                                 via="writing")
                long = self.about.find(topic, n=30)
                sents = w.summarize(" ".join(long.sentences), max_sentences=3)
                out = "Here's a short summary of “" + found.title + "”:\n\n" + " ".join(sents)
                return Reply(text, "writing", out, source=found.source, evidence=found.sentences[0], via="writing")
            sents = w.summarize(body)
            return Reply(text, "writing", "Here's a summary:\n\n" + " ".join(sents), via="writing")
        if task == "rephrase":
            m = w._REPHRASE.match(text.strip())
            if not m:
                return Reply(text, "smalltalk", self._reply(st, "fallback"), via="writing")
            tone = (m.group("tone") or m.group("tone2") or "").lower()
            verb = (m.group("verb") or "").lower()
            if not tone:
                tone = "fix" if verb.startswith(("fix", "correct", "proofread")) else "formal" \
                    if verb in ("polish", "improve") else "plain"
            out = w.fix_text(m.group("text")) if tone in ("fix", "plain") else w.rephrase(m.group("text"), tone)
            label = {"fix": "Here's the corrected text:", "plain": "Here's a cleaned-up version:"}.get(
                tone, f"Here's a {'more ' if tone not in ('simpler', 'shorter') else ''}{tone} version:")
            return Reply(text, "writing", f"{label}\n\n{out}", via="writing")
        return Reply(text, "smalltalk", self._reply(st, "fallback"), via="writing")

    def _show_draft(self, st: DialogState, text: str, req, intro: bool = False, note: str = "") -> Reply:
        from engramm.chat import writing as w
        body = w.draft(req, self.bank.writing, self.user_name(), self._today(), st.conversation)
        st.last_draft = req.to_dict()
        st.draft_turn = st.turn
        what = {"email": "an email", "letter": "a letter", "message": "a message", "note": "a note"}.get(req.genre,
                                                                                                        "a draft")
        head = note or (f"Here's {what} you can use:" if intro else "Here's the updated version:")
        tail = ("\n\nWant changes? Say “make it shorter”, “more formal”, “add that …” or “sign it with …”."
                if intro else "")
        return Reply(text, "writing", f"{head}\n\n{body}{tail}", via="writing")

    def _edit_draft(self, st: DialogState, text: str, cmd: str, x: str | None) -> Reply:
        from engramm.chat.writing import WritingRequest, apply_edit
        req = apply_edit(WritingRequest.from_dict(st.last_draft), cmd, x)
        notes = {"shorter": "Here's a shorter version:", "longer": "Here's a more detailed version:",
                 "formal": "Here's a more formal version:", "casual": "Here's a more casual version:",
                 "again": "Here's another version:", "add": "Done — I've added that:",
                 "sign": "Signed:", "date": "I've changed the date:", "to": "Addressed to the new recipient:",
                 "nosubject": "Without the subject line:"}
        return self._show_draft(st, text, req, note=notes.get(cmd, ""))

    def _content(self, st: DialogState, u: Unit) -> Reply:
        if u.act == "writing":
            return self._writing(st, u)
        if u.act == "forget":
            r = self.bot._forget(u.text)
            if r.kind == "forgot":
                st.last_fact = None
            return r
        if u.act == "tool":
            tr = u.data["result"]
            if tr.value is not None:
                st.uses["last_calc"] = [st.turn, str(tr.value)]
            return Reply(u.text, "tool", tr.text if tr.text.endswith((".", "!", "?")) else tr.text + ".",
                         answer=tr.value, via="tool", confidence=1.0)
        if u.act == "about":
            return self._about(st, u)
        if u.act == "question":
            return self._question(st, u.text)
        return Reply(u.text, "nothing", self._reply(st, "fallback"))

    def _question(self, st: DialogState, text: str) -> Reply:
        bot = self.bot
        pron = re.search(r"\b(he|she|him|his|her|hers|they|them|their)\b", text, re.I)
        gap = st.uses.get("person_gap") == st.turn - 1          # the last "who …?" found nobody
        if pron and not re.search(r"\b(?:i|me|my|you|your)\b", text, re.I) and (bot.resolve(text) == text or gap):
            st.pending = {"slot": "who_mean", "question": text, "pron": pron.group(1), "turn": st.turn}
            return Reply(text, "unknown", self._pick(st, "daily:who_mean", self.bank.daily["who_mean"],
                                                     x=pron.group(1).lower()), via="clarify")
        text = self._carry_topic(st, text)
        atlas_on = self.atlas is not None and self.atlas.any_on() and not re.search(r"\b(?:i|me|my|mine)\b", text, re.I)
        if atlas_on:
            from engramm.web.atlas import is_fresh
            if is_fresh(text):
                fresh = self._atlas_answer(st, text)       # "who is the current …": newer sources first
                if fresh is not None:
                    return self._with_offline_view(st, text, fresh)
        likes = self._likes_answer(st, text)
        if likes is not None:
            return likes
        kb = self._kb_answer(st, text)
        if kb is not None:
            return kb
        mq = self._measure_quote(st, text)
        if mq is not None:
            return mq
        ev = self._event_answer(st, text)
        if ev is not None:
            return ev
        rep = bot._answer(" ".join(text.split()))
        topic = self._named_topic(rep.resolved or text)
        if topic:
            st.uses["q_topic"] = [topic, st.turn]
        if rep.kind == "answer" and rep.via == "lookup" and _implausible(rep.resolved or text, rep.answer, rep.evidence):
            rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None
        gap = self._topic_gap(st, topic, rep)
        if gap is not None and atlas_on:
            later = self._atlas_answer(st, text)
            if later is not None:
                return later
        if gap is not None:
            return gap
        if atlas_on and rep.kind != "answer":
            later = self._atlas_answer(st, text)
            if later is not None:
                return later
        q = rep.resolved or text
        dim_m = _MEASURE_TOPIC.match(q)
        need = _DIM_UNIT.get(dim_m.group("dim").split()[0].lower(), _UNIT) if dim_m else _UNIT
        if rep.kind == "answer" and rep.answer and _MEASURE_Q.match(q) and not need.search(rep.answer):
            # "how far is the moon?" → "8": a measure without its unit is no answer
            rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None
            rep.text = "I don't know for sure."
        if rep.kind == "answer" and rep.via in ("facts", "memory") and rep.source and rep.source.get("kind") == "user":
            orig = self._fact_for(rep)
            cat = _asked_category(q) if orig is not None and orig.subject == USER else None
            latest = self._latest_fact(cat) if cat else None
            if latest is not None and latest.object != rep.answer and latest.subject == USER:
                rep.answer, rep.guess, rep.evidence = latest.object, latest.object, latest.sentence
                rep.source = {"kind": "user", "source": latest.source}
            fact = self._fact_for(rep)
            if fact is not None:
                rep.text = personal_sentence(fact.subject, fact.relation, rep.answer, rep.evidence)
            else:
                rep.text = _user_answer_text(rep.answer, rep.evidence)
            st.last_fact = {"evidence": rep.evidence, "source": rep.source, "answer": rep.answer, "question": q,
                            "sure": True}
            return rep
        if rep.kind == "answer":
            sent = answer_sentence(q, rep.answer, _atype(q))
            rep.text = sent or self._reply(st, "answer.fallback", x=rep.answer)
            st.last_fact = {"evidence": rep.evidence, "source": rep.source, "answer": rep.answer, "question": q,
                            "sure": True}
            return rep
        # unknown
        if rep.via == "facts" and rep.text.startswith("I don't know — you haven't told me"):
            cat = _asked_category(q)
            latest = self._latest_fact(cat) if cat else None
            if latest is not None:
                # told twice ("The name's Tamlolo." … "My name is Erik!"): the latest statement counts
                rep.kind, rep.answer, rep.guess = "answer", latest.object, latest.object
                rep.evidence, rep.source, rep.confidence = latest.sentence, {"kind": "user", "source": latest.source}, 1.0
                rep.text = personal_sentence(latest.subject, latest.relation, latest.object, latest.sentence)
                st.last_fact = {"evidence": rep.evidence, "source": rep.source, "answer": rep.answer, "question": q,
                                "sure": True}
                self.bot.context.update({"answer": latest.object, "atype": None})
                return rep
            if cat == "#name":
                rep.text = self._reply(st, "unknown_about_you.name")
                st.pending = {"slot": "name", "store": self.bank.fun["questions"]["ask_name"]["store"], "turn": st.turn}
            else:
                rep.text = self._reply(st, "unknown_about_you.other")
                key = _ASK_FOR_CATEGORY.get(cat)
                if key:
                    st.pending = {"slot": self.bank.fun["questions"][key]["slot"],
                                  "store": self.bank.fun["questions"][key]["store"], "turn": st.turn}
            st.last_fact = None
            return rep
        if rep.text.startswith("I don't know — I have not read anything about"):
            missing = rep.text.split("about", 1)[1].strip(" .")
            role = re.match(r"^\s*who(?:'s| is| was)\s+(?:the\s+)?(.+?)\s*\??$", q, re.I)
            if role and " of " in missing:
                # "who is the CEO of Apple?": not a missing name, a fact I don't have
                rep.text = f"I don't know who the {_acronym_case(role.group(1))} is — I haven't read anything that says."
            else:
                rep.text = self._reply(st, "answer.unknown_named", x=missing)
        elif rep.guess and (rep.source or {}).get("key"):
            # unsure guesses were right only 7 of 25 times on the team prompts: say so and name the
            # closest source instead of offering the guess (the guess stays in the reply for evals)
            rep.text = self._reply(st, "answer.unknown_near", x=rep.source["key"])
        else:
            rep.text = self._reply(st, "answer.unknown")
        st.last_fact = ({"evidence": rep.evidence, "source": rep.source, "answer": rep.guess, "question": q,
                         "sure": False} if rep.evidence else None)
        if re.match(r"^\s*who\b", q, re.I):
            st.uses["person_gap"] = st.turn                    # "how old is he?" next: ask who is meant
        self.bot.context.update({"answer": None, "atype": None})   # a guess not shown is no referent
        return rep

    def _life(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Everyday life as a person tells it: a workout done and how it went, a day that was "ok",
        a goal ("I want to get fitter") and "any tips?" after it, a diet ("I'm vegetarian"), and
        what to eat after a workout."""
        d = self.bank.daily
        la = st.last_action or {}
        recent = st.turn - la.get("turn", -99) <= 2
        le = st.last_exp or {}
        grief = le and st.turn - le.get("turn", -99) <= 4 and _LOSS.search(le.get("text") or "")
        if grief:
            m = _GRIEF_NAME.match(norm)
            if m:
                name = m.group("x").strip()
                name = name[:1].upper() + name[1:]
                return Reply(msg, "smalltalk", self._pick(st, "daily:grief_name", d["grief_name"], x=name,
                                                          pron=_PRON.get(m.group("p"), "they")), via="empathy")
            m = _GRIEF_AGE.match(norm)
            if m:
                return Reply(msg, "smalltalk", self._pick(st, "daily:grief_age", d["grief_age"], x=m.group("n")),
                             via="empathy")
        if _WEDDING.search(norm):
            st.uses["wedding"] = st.turn
        if _HONOUR.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:wedding_role", d["wedding_role"]), via="empathy")
        if le and st.turn - le.get("turn", -99) <= 2 and _FOLLOW_STATEMENT.match(norm) and experience(norm) is None and \
                not _FEELING_WORD.search(norm) and "?" not in msg and len(norm.split()) <= 10 and \
                not set(r for f in facts_from_text(msg, "x") for r in f.relation) & _CATEGORY_LABELS:
            key = "exp_follow_neg" if le.get("valence") == "negative" else "exp_follow_pos"
            if _SPEECH.search(norm):
                st.uses["speech"] = st.turn
                key = "speech_mention"
            st.last_exp = dict(le, turn=st.turn)
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="empathy")
        if _SPEECH.search(norm) and re.match(r"^i (?:have|need|got|am going|'m going|was asked) to\b", norm):
            st.uses["speech"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "daily:speech_mention", d["speech_mention"]), via="empathy")
        sp = st.uses.get("speech")
        if (_HELP_ME.match(norm) and sp is not None and st.turn - sp <= 3) or _SPEECH_HELP.match(norm):
            st.uses.pop("speech", None)
            wd = st.uses.get("wedding")
            wedding = bool(_WEDDING.search(norm)) or (wd is not None and st.turn - wd <= 8)
            key = "speech_wedding" if wedding else "speech_generic"
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="everyday")
        m = _JOB_CHANGE.match(norm)
        if m:
            jobs = [f for f in self.bot.facts.facts if f.subject == USER and "#job" in f.relation]
            for f in jobs:                              # the old job is no longer true
                self.bot.memory.forget(f.source)
            if jobs:
                self.bot.refresh()
            key = "job_lost" if m.group("bad") else "job_quit"
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="empathy")
        if _WORKOUT_DONE.match(norm):
            rep = self._learn(st, [msg], msg)
            rep.text = self._pick(st, "daily:workout_done", d["workout_done"])
            st.last_action = {"kind": "workout", "turn": st.turn}
            return rep
        m = _WHICH_ONE.match(norm)
        vals = [v for v in st.uses.get("kb_vals", []) if st.turn - v[0] <= 4]
        if m and len(vals) >= 2 and vals[-1][1] != vals[-2][1]:
            a, b = vals[-2][1], vals[-1][1]
            ask = f"which is {m.group('w')}, {a} or {b}"
            rep = self.everyday.compare(st, ask, ask.lower())
            if rep is not None and rep.kind != "unknown":
                rep.message = msg
                return rep
        lc = st.uses.get("last_calc")
        m = _CALC_MORE.match(norm)
        if m and lc and st.turn - lc[0] <= 3:
            from engramm.chat.tools import calculate
            sym = _CALC_OPS[m.group("op")]
            n = m.group("n").replace(",", ".")
            res = calculate(f"{lc[1]} {sym} {n}")
            if res is not None and res.value is not None:
                st.uses["last_calc"] = [st.turn, str(res.value)]
                shown = {"*": "×", "/": "÷", "^": "^"}.get(sym, sym)
                return Reply(msg, "tool", f"{lc[1]} {shown} {n} = {res.value}.", answer=res.value, via="tool",
                             confidence=1.0)
        if _HOMEWORK.match(norm):
            st.uses["homework"] = st.turn
            return Reply(msg, "smalltalk", self._pick(st, "daily:homework", d["homework"]), via="smalltalk")
        hw = st.uses.get("homework")
        m = _SUBJECT.match(norm)
        if m and hw is not None and st.turn - hw <= 2:
            subj = m.group("s")
            key = next((k for k, rx in _SUBJECT_KINDS if rx.fullmatch(subj)), "other")
            st.uses.pop("homework", None)
            return Reply(msg, "smalltalk", self._pick(st, f"daily:subject:{key}", d["subject"][key],
                                                      x=subj[:1].upper() + subj[1:]), via="smalltalk")
        m = _TRIP.match(norm)
        if m and not _NOT_A_TRIP.fullmatch(m.group("x").strip()):
            place = m.group("x").strip()
            rep = self._learn(st, [msg], msg)
            if _TRIP_WORD.fullmatch(place):
                rep.text = self._pick(st, "daily:trip_back", d["trip_back"])
                st.last_action = {"kind": "trip", "turn": st.turn}
            else:
                shown = _place_case(place)
                rep.text = self._pick(st, "daily:trip_place", d["trip_place"], x=shown)
                st.last_action = {"kind": "trip", "turn": st.turn, "place": shown}
                st.topic = {"name": shown, "title": shown, "turn": st.turn}
            return rep
        m = _HOBBY.match(norm) or _HOBBY_BARE.match(norm)
        if m:
            verb = m.group("v")
            x = (m.groupdict().get("x") or _GERUND.get(verb, verb)).strip()
            rep = self._learn(st, [msg], msg)
            key = "hobby_play" if verb == "play" else "hobby_do"
            rep.text = self._pick(st, f"daily:{key}", d[key], x=x)
            st.uses["asked_duration"] = [st.turn, x]
            st.last_action = {"kind": "hobby", "turn": st.turn, "x": x}
            return rep
        asked = st.uses.get("asked_duration")
        m = _DURATION_ANS.match(norm)
        if m and asked and st.turn - asked[0] <= 1:
            n, unit = m.group("n"), m.group("u")
            shown = f"{n} {unit}"
            shown = shown[:1].upper() + shown[1:]
            long_ = unit.startswith("year") and n not in ("a", "one", "1")
            key = "duration_long" if long_ else "duration_short"
            st.uses.pop("asked_duration", None)
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key], x=shown), via="smalltalk")
        if la.get("kind", "").startswith("rec:") and st.turn - la.get("turn", -99) <= 3:
            kind = la["kind"][4:]
            if _REC_SEEN.match(norm):
                before = set(st.uses.get(f"rec_seen:{kind}", []))
                rep = self.everyday.recommend(st, msg, kind, la.get("genre"), more=True)
                if not set(st.uses.get(f"rec_seen:{kind}", [])) - before:
                    # every fitting suggestion has been shown: say so instead of going round again
                    return Reply(msg, "smalltalk", self._pick(st, "daily:rec_exhausted", d["rec_exhausted"]),
                                 via="everyday")
                rep.text = self._pick(st, "daily:rec_seen", d["rec_seen"]) + rep.text[len("A few more:"):] \
                    if rep.text.startswith("A few more:") else rep.text
                return rep
            g = _REC_GENRE.match(norm)
            if g and g.group("g") in _GENRES:
                return self.everyday.recommend(st, msg, kind, g.group("g"))
        m = _BEST_OF.match(norm)
        if m:
            name = (st.topic or {}).get("name") if st.topic and st.turn - st.topic.get("turn", -99) <= 4 else None
            liked = st.uses.get("last_like")
            if name is None and liked and st.turn - liked[0] <= 4 and m.group("who") in ("their", "his", "her", "its"):
                name = liked[1]
            if name:
                return Reply(msg, "smalltalk", self._pick(st, "daily:best_of", d["best_of"], x=name), via="smalltalk")
            return Reply(msg, "smalltalk", self._pick(st, "daily:best_of_plain", d["best_of_plain"]), via="smalltalk")
        m = _HOW_IT_WENT.match(norm)
        if m and recent and la.get("kind") == "workout":
            key = "workout_hard" if m.group("hard") else "workout_good" if m.group("good") else "workout_meh"
            st.last_action = {"kind": "workout", "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, f"daily:{key}", d[key]), via="empathy")
        if _DAY_MEH.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:day_meh", d["day_meh"]), via="smalltalk")
        m = _GOAL.match(norm)
        if m:
            goal = m.group("goal").strip()
            topic = next((t for t, rx in _GOAL_TOPICS if rx.search(goal)), "other")
            st.uses["goal"] = [topic, st.turn, goal]
            rep = self._learn(st, [msg], msg)
            rep.text = self._pick(st, f"daily:goal:{topic}", d["goal"][topic], x=goal)
            return rep
        goal = st.uses.get("goal")
        if goal and st.turn - goal[1] <= 4 and _TIPS.match(norm):
            tips = d["tips"].get(goal[0])
            if tips:
                body = "\n".join("• " + t for t in tips[:4])
                head = self._pick(st, "daily:tips_head", d["tips_head"], x=goal[2])
                return Reply(msg, "smalltalk", f"{head}\n\n{body}", via="everyday")
        m = _DIET.match(norm)
        if m:
            diet = m.group("diet").lower().replace("gluten-free", "gluten free")
            st.uses["diet"] = diet
            rep = self._learn(st, [msg], msg)
            rep.text = self._pick(st, "daily:diet_noted", d["diet_noted"], x=diet)
            return rep
        if _POST_WORKOUT.match(norm):
            diet = st.uses.get("diet") or self._told_diet()
            items = d["post_workout"]["vegan" if diet == "vegan" else "vegetarian" if diet else "any"]
            head = self._pick(st, "daily:post_workout_head", d["post_workout"]["head"])
            if diet:
                head = head.rstrip(":") + f" (all {diet}):"
            st.last_action = {"kind": "rec:food", "turn": st.turn}
            return Reply(msg, "smalltalk", head + "\n\n" + "\n".join("• " + i for i in items[:4]), via="everyday")
        return None

    def _told_diet(self) -> str | None:
        """A diet told in an earlier conversation ("I'm vegetarian")."""
        for f in reversed(self.bot.facts.facts):
            if f.subject == USER:
                m = re.search(r"\b(vegan|vegetarian|pescatarian)\b", f.sentence or "", re.I)
                if m:
                    return m.group(1).lower()
        return None

    def _likes_answer(self, st: DialogState, text: str) -> Reply | None:
        """"what do I like?" / "what don't I like?": the favourites or dislikes you told me."""
        m = _LIKES_Q.match(text.strip())
        if not m:
            return None
        verb = (m.group("v") or m.group("v2") or "").lower()
        neg = bool(m.group("neg")) or bool(m.group("v2")) or verb in ("hate", "dislike")
        rel = "#dislike" if neg else "#fav"
        vals = list(dict.fromkeys(f.object for f in self.bot.facts.facts
                                  if f.subject == USER and rel in f.relation and f.object))
        if not vals:
            return Reply(text, "unknown", self._pick(st, "daily:likes_none", self.bank.daily["likes_none"]), via="facts")
        joined = vals[0] if len(vals) == 1 else ", ".join(vals[:-1]) + " and " + vals[-1]
        key = "dislikes_list" if neg else "likes_list"
        return Reply(text, "answer", self._pick(st, f"daily:{key}", self.bank.daily[key], x=joined),
                     answer=joined, source={"kind": "user"}, via="facts")

    def _measure_quote(self, st: DialogState, text: str) -> Reply | None:
        """"How big is the Sun?" / "How far away is it?": the sentence of the topic's own article that
        gives that measure with a unit, quoted with its source — the topic is certain, the number
        is the article's, nothing is guessed."""
        q = self.bot.resolve(" ".join(text.split()))
        m = _MEASURE_TOPIC.match(q)
        if not m:
            return None
        dim, topic = m.group("dim").lower(), m.group("t").strip(" ?.")
        if re.fullmatch(r"(?:he|she|they|him|her|them)", topic, re.I):
            return None                                   # a person: the pronoun flow, never a measure of a place
        if re.fullmatch(r"(?:it|that|this|there)", topic, re.I):
            last = self.bot.context.get("mention")
            if not last:
                return None
            topic = last
        docs = []
        for v in (topic, re.sub(r"^(?:the|a|an)\s+", "", topic, flags=re.I)):
            docs = self.about.titles.lookup(v) or self.about.titles.lookup(_place_case(v))
            if docs:
                break
        if not docs:
            return None
        cues = _MEASURE_CUES.get(dim)
        lo, hi = self.bot.c.doc_sentences(docs[0])
        title = self.bot.c.doc_keys[docs[0]][1]
        units = _DIM_UNIT.get(dim.split()[0], _UNIT)
        for sid in range(lo, min(hi, lo + 14)):
            sent = clean_sentence(self.bot.c.sentence_text(sid))
            near = any(units.search(sent[max(0, c.start() - 40):c.end() + 70]) for c in cues.finditer(sent))
            if near and len(sent) < 400:
                self.bot.context.update({"mention": title, "answer": None, "atype": None})
                src = {"kind": "wikipedia", "title": title, "key": title,
                       "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")}
                st.last_fact = {"evidence": sent, "source": src, "answer": None, "question": q, "sure": True}
                body = self._pick(st, "daily:measure_quote", self.bank.daily["measure_quote"], title=title, evidence=sent)
                return Reply(text, "answer", body, evidence=sent, source=src, via="about")
        # the topic's own article does not give it: say so rather than take a number from elsewhere
        self.bot.context.update({"mention": title, "answer": None, "atype": None})
        st.last_fact = None
        return Reply(text, "unknown", self._pick(st, "daily:measure_none", self.bank.daily["measure_none"], title=title),
                     source={"kind": "wikipedia", "title": title, "key": title,
                             "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")}, via="lookup")

    def _named_topic(self, q: str) -> str | None:
        """The article a question names, as the fact bank titles it: "who won the world cup 2022?"
        → "2022 FIFA World Cup". Only names of two or more words that are in the reading count."""
        if self.kgqa is None:
            return None
        words = re.findall(r"[A-Za-z0-9][\w'’-]*", q)
        kb = self.kgqa.kb
        for size in range(min(5, len(words)), 1, -1):
            for i in range(len(words) - size + 1):
                gram = words[i:i + size]
                if gram[0].lower() in _TOPIC_EDGE or gram[-1].lower() in _TOPIC_EDGE:
                    continue
                titles = [e.title for e, kind in kb.link(" ".join(gram), limit=2)]
                if not titles and re.fullmatch(r"(?:1[5-9]|20)\d\d", gram[-1]):
                    # "world cup 2022" → "2022 … World Cup": the year in front, words in order
                    pat = gram[-1] + " %" + "%".join(gram[:-1])
                    row = kb.db.execute("SELECT title FROM entity WHERE title LIKE ? ORDER BY popularity DESC LIMIT 1",
                                        (pat,)).fetchone()
                    titles = [row[0]] if row else []
                for t in titles:
                    if self.about.titles.lookup(t):
                        return t
        return None

    def _carry_topic(self, st: DialogState, text: str) -> str:
        """"and who was the top scorer?" right after a question about the 2022 World Cup: the
        follow-up keeps the topic it leaves out."""
        last = st.uses.get("q_topic")
        if not last or st.turn - last[1] > 2:
            return text
        m = re.match(r"^\s*(?:and|also|so|ok(?:ay)?|what about)\b[\s,]*(.+)$", text, re.I)
        if not m or re.search(r"\b(?:he|she|it|they|him|her|them|his|its|their|i|me|my|you|your)\b", text, re.I):
            return text
        rest = m.group(1)
        if self._named_topic(rest) or re.search(r"(?<!^)\b[A-Z][a-z]", rest):
            return text
        return f"{rest.rstrip(' ?.!')} at the {last[0]}?"

    def _topic_gap(self, st: DialogState, topic: str | None, rep: Reply) -> Reply | None:
        """The question names an article I have, but the answer comes from another article that
        never names it ("who won the world cup 2022?" → a sentence about the U-17 World Cup): that is
        no answer. Say honestly what the article on the topic does tell."""
        if not topic or rep.via != "lookup":
            return None
        src = rep.source or {}
        bare = re.sub(r"\s*\([^)]*\)$", "", topic).lower()
        title = re.sub(r"\s*\([^)]*\)$", "", str(src.get("title") or src.get("key") or "")).lower()
        if rep.kind == "answer" and (title == bare or bare in (rep.evidence or "").lower()):
            return None
        if rep.kind != "answer" and not (rep.guess or rep.text.startswith("I don't know — I have not read anything")):
            return None
        docs = self.about.titles.lookup(topic)
        head = " ".join(self.about._doc_text(docs[0], n=4, max_chars=900)[0]) if docs else ""
        ongoing = bool(re.search(r"\b(?:is taking place|is being held|is being played|is scheduled|will be held|"
                                 r"is set to|are the defending)\b", head))
        key = "topic_gap_ongoing" if ongoing else "topic_gap"
        rep.kind, rep.guess, rep.answer = "unknown", rep.answer, None
        x = f"the {topic}" if re.match(r"(?:\d|(?:President|Prime Minister|King|Queen|Chancellor|Mayor|Battle|"
                                       r"Siege|Treaty|War|Fall|History|Kingdom|Republic|University)\b)", topic) else topic
        rep.text = self._pick(st, f"daily:{key}", self.bank.daily[key], x=x)
        if self.atlas is None or not self.atlas.any_on():
            rep.text += " " + self.bank.daily["topic_gap_online"][0]
        rep.source = {"kind": "wikipedia", "title": topic, "key": topic,
                      "url": "https://en.wikipedia.org/wiki/" + topic.replace(" ", "_")}
        rep.evidence = None
        st.last_fact = None
        if re.match(r"^\s*who\b", rep.message or "", re.I) or re.match(r"^\s*who\b", rep.resolved or "", re.I):
            st.uses["person_gap"] = st.turn             # "how old is he?" next: ask who is meant
        self.bot.context.update({"answer": None, "atype": None})
        return rep

    def _atlas_answer(self, st: DialogState, text: str) -> Reply | None:
        """The question again, with sentences from the switched-on channels (feeds, shelf,
        messenger) as extra candidates; None when they do not lead to a confident answer."""
        bot = self.bot
        q = bot.resolve(" ".join(text.split()))
        names = [m.group(0) for m in _CAPS_SPAN.finditer(q) if not q.startswith(m.group(0)) or " " in m.group(0)]
        if st.topic and st.topic.get("name") and st.turn - st.topic.get("turn", -99) <= 3:
            names.append(st.topic["name"])
        try:
            rows, used = self.atlas.candidates(q, list(dict.fromkeys(names)))
        except Exception:                        # the network must never break the chat
            return None
        if not rows:
            return None
        ctx = dict(bot.context)
        bot.extra_rows, bot.extra_calib = rows, getattr(self.atlas, "calib", None)
        try:
            rep = bot._answer(q)
        finally:
            bot.extra_rows, bot.extra_calib = [], None
        src = rep.source or {}
        if rep.kind != "answer" or src.get("kind") not in ("shelf", "feed", "web"):
            quote = self._atlas_quote(st, text, q, rep, names)
            if quote is None:
                bot.context = ctx
            return quote
        full = _full_name(rep.answer, [r[0] for r in rows if r[1].get("key") == src.get("key")])
        if full != rep.answer:                   # "Vickers" → "Diana Vickers" (named so in the same article)
            rep.answer = full
        sent = answer_sentence(q, rep.answer, _atype(q)) or f"{rep.answer}."
        when = src.get("as_of")
        where = {"shelf": "Wikipedia", "feed": src.get("source", "a news feed"), "web": src.get("source", "the web")}[src["kind"]]
        note = f" (from {where}{', as of ' + when if when else ''})"
        # source agreement: other sources among the fetched sentences that say the same
        others = _agreeing_sources(rep.answer, rows, src)
        if others:
            note = note[:-1] + "; " + ("also " if len(others) == 1 else "also in ") + " and ".join(others[:2]) + ")"
            rep.confidence = max(rep.confidence, 1.0)
        rep.text = sent.rstrip(".") + note + "."
        rep.via = "atlas"
        rep.message = text
        st.last_fact = {"evidence": rep.evidence, "source": src, "answer": rep.answer, "question": q, "sure": True}
        return rep

    def _about_me(self, st: DialogState, msg: str, norm: str) -> Reply | None:
        """Lines about ENGRAMM itself or about the conversation, which must never go to the reading:
        "have you seen it?", "you can't watch movies", "what did we talk about?", "that joke was bad",
        and "something with chicken" after cooking ideas."""
        d = self.bank.daily
        la = st.last_action or {}
        recent = st.turn - la.get("turn", -99) <= 3
        m = _BOT_EXPERIENCE.match(norm)
        if m and m.group("v") in ("been to", "been", "visited") and (m.group("rest") or "").strip(" ?"):
            place = _place_case(re.sub(r"^(?:to|in)\s+", "", m.group("rest").strip(" ?")))
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_travel", d["bot_travel"], x=place), via="smalltalk")
        if m and m.group("v") in ("eat", "eaten", "taste", "tasted", "smell") and not (m.group("rest") or "").strip(" ?"):
            m = None                              # "do you eat?": a question about ENGRAMM's nature
        if m:
            what = (m.group("rest") or "").strip(" ?")
            what = "it" if not what or what in ("it", "that", "this", "them", "this one", "that one") else what
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_experience", d["bot_experience"],
                                                      x=_VERB_BASE.get(m.group("v"), m.group("v")), topic=what),
                         via="smalltalk")
        if _BOT_LIMIT.match(norm):
            return Reply(msg, "smalltalk", self._pick(st, "daily:bot_limit", d["bot_limit"]), via="smalltalk")
        if _WHERE_WERE_WE.match(norm):
            themes = st.uses.get("recap", [])
            if themes:
                last = "you" if themes[-1] == "things about you" else themes[-1]
                return Reply(msg, "smalltalk", self._pick(st, "daily:where_were_we", d["where_were_we"], x=last),
                             via="smalltalk")
            return Reply(msg, "smalltalk", self._pick(st, "daily:recap_none", d["recap_none"]), via="smalltalk")
        if _RECAP.match(norm):
            themes = st.uses.get("recap", [])
            if not themes:
                return Reply(msg, "smalltalk", self._pick(st, "daily:recap_none", d["recap_none"]), via="smalltalk")
            listed = themes[-6:]
            joined = listed[0] if len(listed) == 1 else ", ".join(listed[:-1]) + " and " + listed[-1]
            return Reply(msg, "smalltalk", self._pick(st, "daily:recap", d["recap"], x=joined), via="smalltalk")
        if recent and la.get("kind") == "joke" and _JOKE_BAD.match(norm):
            st.last_action = {"kind": "joke", "turn": st.turn}
            st.offer = {"kind": "joke", "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "daily:joke_bad", d["joke_bad"]), via="smalltalk")
        if recent and la.get("kind") == "joke" and _JOKE_GOOD.match(norm):
            st.last_action = {"kind": "joke", "turn": st.turn}
            st.offer = {"kind": "joke", "turn": st.turn}
            return Reply(msg, "smalltalk", self._pick(st, "daily:joke_good", d["joke_good"]), via="smalltalk")
        m = _REFINE.match(norm)
        if m and recent and la.get("kind") == "rec:food":
            x = m.group("x").strip()
            ideas = d["recommend"]["food"].get("with", {}).get(x) or \
                d["recommend"]["food"].get("with", {}).get(x.rstrip("s"))
            if ideas:
                st.last_action = {"kind": "rec:food", "turn": st.turn}
                body = "\n".join("• " + i[:1].upper() + i[1:] for i in ideas[:3])
                head = self._pick(st, "daily:refine_head", d["refine_head"], x=x)
                return Reply(msg, "smalltalk", f"{head}\n\n{body}", via="everyday")
        return None

    def _with_offline_view(self, st: DialogState, text: str, fresh: Reply) -> Reply:
        """A newer answer from the network that the offline fact bank contradicts: say both, with
        their dates, newer first — never silently one of them."""
        if fresh.kind != "answer" or not fresh.answer or self.kgqa is None:
            return fresh
        ctx = dict(self.bot.context)
        old = self._kb_answer(DialogState(st.conversation + "#kb"), text)
        self.bot.context = ctx
        if old is None or not old.answer or _same_value(old.answer, fresh.answer):
            return fresh
        fresh.text = fresh.text.rstrip(".") + f". My offline fact bank (older) still says {old.answer}."
        fresh.alternatives = [{"text": old.text, "source": old.source}] + list(fresh.alternatives or [])
        return fresh

    def _atlas_quote(self, st: DialogState, text: str, q: str, rep: Reply, names: list[str]) -> Reply | None:
        """Not sure of the short answer, but the best sentence comes from the article the question
        names and shares its other words: say so and quote it with its source, as a person would —
        never a guessed short answer."""
        src = rep.source or {}
        if not rep.evidence or src.get("kind") not in ("shelf", "web"):
            return None
        title = str(src.get("title") or "")
        shelf = getattr(self.atlas, "shelf", None)
        bare = re.sub(r"\s*\([^)]*\)$", "", title).lower()
        named = bool(bare) and bare in q.lower() or any(
            _name_match(n, title) or (shelf is not None and shelf.index.lookup(n) is not None
                                      and shelf.index.title(shelf.index.lookup(n)) == title) for n in names)
        if not named:
            return None
        rest = _stems(q) - _stems(title) - _QUOTE_STOP
        if not rest:
            return None
        # the best candidate sentence of that article that has the question's other words
        ev = None
        for row in [(None, None, None, rep.evidence, src)] + list(getattr(self.bot, "last_rows", []) or []):
            text_, rsrc = row[3], row[4] or {}
            if rsrc.get("key") != src.get("key"):
                continue
            have = _stems(text_) | ({"born", "die"} if _LIFE_SPAN_RE.search(text_) else set())
            if rest & have:
                ev = text_
                break
        if ev is None:
            return None
        when = src.get("as_of")
        where = f"Wikipedia's article “{title}”" if src["kind"] == "shelf" else f"the page “{title}” ({src.get('source')})"
        say = self._pick(st, "daily:atlas_quote", self.bank.daily["atlas_quote"], title=where, evidence=ev)
        say = say[:1].upper() + say[1:] + (f" (as of {when})." if when else "")
        st.last_fact = {"evidence": ev, "source": src, "answer": None, "question": q, "sure": False}
        return Reply(text, "about", say, None, rep.guess, ev, src, 0.0, "atlas", rep.resolved, rep.alternatives)

    def _atlas_about(self, st: DialogState, text: str, topic: str) -> Reply | None:
        """"Tell me about X" when the local reading has no article: the shelf (or the live page)."""
        if self.atlas is None or not self.atlas.any_on():
            return None
        try:
            if self.atlas.shelf is not None and self.egress_on("shelf"):
                docs = self.atlas.shelf.documents(topic, k=1, seed=self.atlas.seed, prefer_title=topic)
                ix = self.atlas.shelf.index
                named = ix.lookup(topic)                 # a title or redirect ("xHCI" → the full name)
                if docs and (_name_match(topic, docs[0]["t"]) or (named is not None and ix.title(named) == docs[0]["t"])):
                    d = docs[0]
                    from engramm.web.shelf import _SENT
                    sents = [x.strip() for x in _SENT.split(d["x"].split("\n")[0]) if x.strip()][:3]
                    if sents:
                        src = {"kind": "shelf", "source": "wikipedia", "key": d["t"], "title": d["t"], "as_of": d.get("d", "")}
                        st.last_fact = {"evidence": sents[0], "source": src, "answer": None, "question": None, "sure": True}
                        self.bot.context.update({"answer": None, "atype": None, "mention": d["t"], "kb_last": None})
                        st.topic = {"title": d["t"], "name": d["t"], "turn": st.turn}
                        return Reply(text, "about", " ".join(sents), evidence=sents[0], source=src, via="atlas",
                                     confidence=1.0)
            if self.egress_on("messenger"):
                rows = self.atlas._messenger(f"what is {topic}", [topic])
                if rows:
                    first = [r for r in rows if r[1]["kind"] == "web"][:3]
                    if first:
                        src = first[0][1]
                        return Reply(text, "about", " ".join(r[0] for r in first), evidence=first[0][0], source=src,
                                     via="atlas", confidence=1.0)
        except Exception:
            return None
        return None

    def egress_on(self, channel: str) -> bool:
        return self.atlas is not None and self.atlas.egress.enabled(channel)

    def _news(self, st: DialogState, msg: str, topic: str | None) -> Reply:
        if self.atlas is None or not self.egress_on("feeds"):
            return Reply(msg, "unknown", self._pick(st, "daily:news_off", self.bank.daily["news_off"]), via="news")
        items = self.atlas.news(topic, k=5)
        if not items:
            key = "news_none_topic" if topic else "news_none"
            return Reply(msg, "unknown", self._pick(st, f"daily:{key}", self.bank.daily[key], x=topic or ""),
                         via="news")
        lines = []
        for it in items:
            when = dt.datetime.fromtimestamp(it["published"]).strftime("%d %b, %H:%M")
            lines.append(f"• {it['title']} — {it['feed_title']}, {when}")
        head = f"Here's what my news feeds say about {topic}:" if topic else "The latest from your news feeds:"
        src = {"kind": "feed", "source": items[0]["feed"], "key": items[0]["link"] or items[0]["title"],
               "title": items[0]["title"]}
        return Reply(msg, "about", head + "\n" + "\n".join(lines), source=src, evidence=items[0]["title"],
                     via="news", confidence=1.0, alternatives=[{"text": it["title"], "source": {
                         "kind": "feed", "source": it["feed"], "key": it["link"] or it["title"], "title": it["title"]}}
                         for it in items[1:4]])

    def _kb_answer(self, st: DialogState, text: str) -> Reply | None:
        """A question about a named thing, answered from the fact bank (exact infobox facts)."""
        if self.kgqa is None or re.search(r"\b(?:i|me|my|mine|i'm)\b", text.lower()):
            return None
        q = self.bot.resolve(" ".join(text.split()))
        try:
            ans = self.kgqa.answer(q)
        except Exception:                       # a damaged fact bank must not break the chat
            return None
        if ans is None:
            return None
        value = _join_values(ans.values)
        src = {"kind": "kb", "source": "dbpedia", "key": ans.entity.title}
        atype = _atype(q)
        self.bot.context.update({"answer": ans.values[0] if len(ans.values) == 1 else None, "atype": atype,
                                 "mention": ans.entity.name})
        st.last_fact = {"evidence": ans.evidence, "source": src, "answer": value, "question": q, "sure": True}
        self.bot.context["kb_last"] = {"question": q, "names": [ans.entity.name, ans.entity.title]}
        named = ans.values[0] if len(ans.values) == 1 and not re.search(r"\d", ans.values[0]) else ans.entity.name
        st.uses["kb_vals"] = (st.uses.get("kb_vals", []) + [[st.turn, named]])[-4:]
        return Reply(text, "answer", ans.text, answer=value, guess=value, evidence=ans.evidence, source=src,
                     confidence=1.0, via="kb", resolved=q if q != text else None)

    def _event_answer(self, st: DialogState, text: str) -> Reply | None:
        """"When did the Berlin Wall fall?": the first sentence of the article "Fall of the Berlin Wall"."""
        from engramm.kb.kgqa import EVENT_NOUNS, EVENT_Q
        m = EVENT_Q.match(text.strip())
        if not m:
            return None
        for noun in EVENT_NOUNS[m.group("ev").lower()]:
            found = self.about.find(f"{noun} of {m.group('e')}", n=1)
            if found is not None and re.search(r"\b(?:1[0-9]{3}|20[0-9]{2})\b", found.sentences[0]):
                st.last_about = found
                return Reply(text, "answer", found.sentences[0], answer=None, evidence=found.sentences[0],
                             source=found.source, confidence=1.0, via="about")
        return None

    def _ellipsis(self, st: DialogState, msg: str) -> str | None:
        """"And of Germany?" after "What is the capital of France?" → "What is the capital of Germany?"."""
        m = _ELLIPSIS.match(msg.strip())
        if not m:
            return None
        new = m.group("x").strip()
        last = self.bot.context.get("kb_last")
        if last and st.last_q and last["question"].strip(" ?").lower() != st.last_q.strip(" ?").lower() \
                and self.bot.resolve(st.last_q).strip(" ?").lower() != last["question"].strip(" ?").lower():
            last = None                                   # a newer question came after the fact-bank one
        if last:
            for name in last["names"]:
                if name and re.search(re.escape(name), last["question"], re.I):
                    return re.sub(re.escape(name), new, last["question"], count=1, flags=re.I)
        q = st.last_q_named or st.last_q
        if q:
            # the last question's named thing ("Who is the CEO of Apple?" → "Apple"), not its first word
            names = [n for n in re.findall(r"\b[A-Z][\w'’.-]*(?:\s+(?:of|the|and|de|von|van)?\s*[A-Z][\w'’.-]*)*", q)
                     if not q.startswith(n) or len(n.split()) > 1]
            if names:
                old = max(names, key=len)
                head, sep, tail = old.rpartition(" of ")
                if sep and len(head.split()) == 1:          # "CEO of Apple": the company, not the role
                    old = tail
                return q.replace(old, new, 1)
        return None

    def _prefer_correction(self, msg: str) -> str:
        """"actually I prefer ramen" right after "my favorite food is sushi" → "My favourite food is ramen."
        — the correction keeps the category it corrects."""
        m = _PREFER.match(normalise(msg))
        sid = self.bot.context.get("last_learned")
        if not m or not sid:
            return msg
        for f in self.bot.facts.facts:
            if f.source == sid and f.subject == USER:
                for lab, noun in _FAV_NOUN.items():
                    if lab in f.relation:
                        return f"My favourite {noun} is {m.group('x').strip()}."
        return msg

    def _proper_case(self, text: str) -> str:
        """"my name is thomas" → "my name is Thomas", "i moved to munich" → "… Munich" — a name after a
        name cue, and a place after a place cue when the fact bank knows it as a place."""
        def name(m):
            return m.group(1) + " ".join(w[:1].upper() + w[1:] for w in m.group(2).split())
        text = _NAME_CUE.sub(name, text)
        if self.kgqa is None:
            return text

        def place(m):
            words = m.group(2)
            for n in range(min(3, len(words.split())), 0, -1):
                cand = " ".join(words.split()[:n])
                try:
                    hits = self.kgqa.kb.link(cand, limit=1)
                except Exception:
                    hits = []
                if hits and (hits[0][0].type or "") in _PLACE_TYPES:
                    rest = words[len(cand):]
                    return m.group(1) + _place_case(cand) + rest
            return m.group(0)
        return _PLACE_CUE.sub(place, text)

    def _latest_fact(self, cat: str):
        """Your most recent fact of a category (the later statement corrects the earlier one)."""
        self.bot.refresh()
        order = {sid: i for i, sid in enumerate(self.bot.user_texts())}
        cands = [f for f in self.bot.facts.facts if f.subject == USER and cat in f.relation]
        return max(cands, key=lambda f: (order.get(f.source, -1), f.object)) if cands else None

    def _fact_for(self, rep: Reply):
        src = (rep.source or {}).get("source")
        for f in self.bot.facts.facts:
            if f.source == src and f.object == rep.answer:
                return f
        return None

    def _about(self, st: DialogState, u: Unit) -> Reply:
        kind, topic = u.data["kind"], u.data["topic"]
        resolved = self.bot.resolve(topic) if re.search(r"\b(?:he|she|it|him|her|they|them|this|that)\b", topic,
                                                         flags=re.I) else topic
        found = self.about.find(resolved)
        if found is None and kind in ("what", "tell", "define") and not _CAPS_NAME.search(resolved):
            found = self.about.find(resolved.title()) if resolved.islower() else None
        if found is None:
            shelf = self._atlas_about(st, u.text, resolved)
            if shelf is not None:
                return shelf
            if kind == "what" or kind == "tell" and re.match(r"^(?:who|what|when|where|why|how)\b", topic, re.I):
                return self._question(st, u.text)
            if kind == "opinion":
                return Reply(u.text, "smalltalk", self._pick(st, "intent:bot_opinion",
                                                             self.bank.by_id["bot_opinion"].responses), via="smalltalk")
            text = self._reply(st, "about.none", topic=resolved)
            return Reply(u.text, "unknown", text, via="about")
        return self._about_reply(st, u.text, found, kind)

    def _about_reply(self, st: DialogState, text: str, found: About, kind: str) -> Reply:
        body = " ".join(found.sentences)
        if kind == "opinion":
            body = "I don't have opinions of my own, but here's what I've read: " + body
        st.last_about = {"title": found.title, "doc": found.doc, "next": found.next_sentence,
                         "end": found.end_sentence, "source": found.source, "turn": st.turn}
        st.last_fact = {"evidence": found.sentences[0], "source": found.source, "answer": None, "question": None,
                        "sure": True}
        self.bot.context.update({"answer": None, "atype": None, "mention": found.title, "kb_last": None})
        st.last_q = st.last_q_named = None        # a new topic: "where?" no longer means the old question
        return Reply(text, "about", body, evidence=found.sentences[0], source=found.source, via="about",
                     confidence=1.0)

    def _more(self, st: DialogState, text: str) -> Reply:
        la = st.last_about
        topic = st.topic if st.topic and st.turn - st.topic.get("turn", -99) <= 4 else None
        if la and topic and la.get("title") != topic.get("title") and la.get("turn", -99) < topic.get("turn", -99):
            la = None                            # the conversation moved on to another topic
            found = self.about.find(topic["title"]) or self.about.find(topic.get("name") or topic["title"])
            if found:
                return self._about_reply(st, text, found, "tell")
        if la:
            ab = self.about.more(About(la["title"], la["doc"], [], la["next"], la["end"], la["source"]))
            if ab is None:
                return Reply(text, "about", self._reply(st, "about.more_none", title=la["title"]), via="about")
            return self._about_reply(st, text, ab, "tell")
        mention = self.bot.context.get("mention")
        if mention:
            found = self.about.find(mention)
            if found:
                return self._about_reply(st, text, found, "tell")
        return Reply(text, "smalltalk", self._reply(st, "about.more_nothing"), via="smalltalk")

    def _why(self, st: DialogState, text: str) -> Reply:
        lf = st.last_fact
        if not lf or not lf.get("evidence"):
            if st.last_kind == "smalltalk" and st.last_reply and st.last_reply.rstrip().endswith("?"):
                # "why?" after ENGRAMM's own opinion or question: a person's answer, not a source
                return Reply(text, "smalltalk", self._pick(st, "daily:why_smalltalk", self.bank.daily["why_smalltalk"]),
                             via="smalltalk")
            return Reply(text, "smalltalk", self._reply(st, "why.none"), via="smalltalk")
        src = lf.get("source") or {}
        if src.get("kind") == "user":
            out = self._reply(st, "why.user", evidence=lf["evidence"])
        elif src.get("kind") == "kb":
            out = self._reply(st, "why.kb", title=src.get("key"), evidence=lf["evidence"])
        else:
            out = self._reply(st, "why.base", title=src.get("key") or "a text I read", evidence=lf["evidence"])
        if not lf.get("sure", True):
            out += self.bank.replies["why"]["unsure"]
        if st.last_reply and out.strip() == st.last_reply.strip():
            # "are you sure?" then "how do you know?": not the same words again
            title = src.get("title") or src.get("key") or "my source"
            out = self._pick(st, "daily:why_again", self.bank.daily["why_again"], title=title)
        return Reply(text, "answer", out, evidence=lf["evidence"], source=src, via="why")

    # -- memory -------------------------------------------------------------------------------

    def _worth_learning(self, sentence: str) -> bool:
        """Remember a statement only if it carries something: a recognised fact, something about
        you, or a named thing."""
        s = sentence.strip()
        if len(s) < 3 or is_discourse(normalise(s)):
            return False
        facts = facts_from_text(s, "probe", self.bot.is_name_initial_fact, typer=self.bot.typer)
        if facts:
            return True
        low = normalise(s)
        words = low.split()
        if re.search(r"\b(?:i|i'm|i've|me|my|mine|we|we're|our|us)\b", low) and len(words) >= 3:
            content = [w for w in words if len(w) > 2 and w not in _STOP_CHAT]
            return len(content) >= 1
        caps = [m.group(0) for m in _CAPS_NAME.finditer(s)]
        first = s.split()[0] if s.split() else ""
        names = [c for c in caps if c != first or self.bot.is_name_initial_fact(c)]
        return bool(names) and len(words) >= 3

    def _again(self, st: DialogState, msg: str) -> Reply | None:
        """"another one" / "one more": the same kind of thing as last time (a joke, a fact, a quote,
        suggestions, a quiz question or a riddle)."""
        la = st.last_action
        if not la or st.turn - la.get("turn", -99) > 6:
            return None
        kind = la["kind"]
        if kind in ("joke", "fun_fact", "quote", "story"):
            return self._action(st, kind, Unit("intent", msg))
        if kind == "quiz":
            return self.everyday.start_quiz(st, msg, first=False)
        if kind == "riddle":
            return self.everyday.start_riddle(st, msg)
        if kind.startswith("rec:"):
            return self.everyday.recommend(st, msg, kind[4:], la.get("genre"), more=True)
        return None

    def _discourse(self, st: DialogState, u: Unit) -> str:
        n = u.norm
        d = self.bank.daily["discourse"]
        if re.search(r"\b(?:question|ask)\b", n):
            return self._pick(st, "daily:disc:q", d["question_coming"])
        if re.search(r"\bhelp\b", n):
            return self._pick(st, "daily:disc:help", d["help"])
        if re.search(r"\b(?:confused|lost)\b", n):
            return self._pick(st, "daily:disc:confused", d["confused"])
        if re.search(r"\b(?:agree|me too|same here|me neither|i know right|i thought so|i knew it)\b", n):
            return self._pick(st, "daily:disc:agree", d["agree"])
        if st.last_reply.rstrip().endswith("?") and re.search(r"\b(?:know|idk|dunno|sure|idea|guess)\b", n):
            return self._pick(st, "daily:disc:after_q", d["after_question"])
        return self._pick(st, "daily:disc:plain", d["plain"])

    def _plan(self, st: DialogState, u: Unit) -> str:
        """"I'm thinking about moving to Berlin" → "Moving to Berlin — exciting! What's drawing you there?"
        A plan is not a fact (you don't live in Berlin yet), so it is answered, not stored."""
        m = _PLAN.search(u.norm)
        what = u.text[m.end():].strip(" .!") if m else ""
        what = re.sub(r"^(?:to|of|about|on)\s+", "", what, flags=re.I)
        what = swap_person(what) if what else ""
        if what and len(what.split()) <= 8:
            head = what[:1].upper() + what[1:]
            big = re.match(r"(?:quit|quitting|leav|break|divorc|drop|mov|resign|sell|end|stop)", what.lower())
            st.last_exp = {"valence": "plan", "topic": what, "person": False, "text": u.text, "turn": st.turn}
            key = "plan_big" if big else "plan"
            return self._pick(st, f"daily:{key}", self.bank.daily[key], x=head)
        return self._pick(st, "daily:plan_plain", self.bank.daily["plan_plain"])

    def _has_fact(self, sentence: str) -> bool:
        """A sentence with something lasting to remember (a name, a job, a home …), not just a mood:
        "my boss Tom was so rude" keeps that your boss is called Tom; "my boss was annoying" keeps nothing."""
        from engramm.chat.facts import CATEGORIES
        for f in facts_from_text(sentence, "probe", self.bot.is_name_initial_fact, typer=self.bot.typer):
            if set(f.relation) & CATEGORIES or (f.object[:1].isupper() and f.kind == "NAME"):
                return True
        return False

    def _feeling_has_fact(self, sentence: str) -> bool:
        from engramm.chat.facts import CATEGORIES
        for f in facts_from_text(sentence, "probe", self.bot.is_name_initial_fact, typer=self.bot.typer):
            if f.subject.startswith(USER + ":") or set(f.relation) & (CATEGORIES - {"#fav"}):
                return True
        return False

    def _learn(self, st: DialogState, sentences: list[str], msg: str) -> Reply:
        bot = self.bot
        text = self._proper_case(_job_field(resolve_statement(" ".join(s.strip() for s in sentences if s.strip()))))
        sid = source_id(text)
        if sid in bot.user_texts():
            return Reply(msg, "known", self._reply(st, "learned.already"), source={"kind": "user", "source": sid},
                         via="memory")
        name_before = self.user_name()
        bot.memory.learn_text(text, sid)
        bot.refresh()
        bot.context["last_learned"] = sid
        fs = [f for f in bot.facts.facts if f.source == sid]
        confirm = self._confirm(st, fs, name_before)
        wf = _WORK_IN.match(text.strip())
        if wf and text.rstrip(".").endswith(f"My job is in {wf.group('f').strip()}"):
            confirm = self._pick(st, "daily:work_field", self.bank.daily["work_field"], x=wf.group("f").strip())
        found = None
        if self._generic_confirm and self.kgqa is not None:
            # "I watched Inception yesterday": say something about the film instead of "Noted."
            found = self.everyday.entity_reaction(st, text)
            if found is not None:
                confirm = found[0]
        if self._generic_confirm and (self.kgqa is None or found is None):
            plain = self.everyday.activity_reaction(st, text)      # "I watched Inception": ask how it was
            if plain is not None:
                confirm = plain
        hm = _HAVE_COUNT.match(text.strip())
        if hm and hm.group(2).lower() in _FAMILY_PLURALS:     # "I have two kids": ask their names, like a person
            noun = "children" if hm.group(2).lower() in ("kids", "children") else hm.group(2).lower()
            st.uses["have_noun"] = (noun, st.turn)
            confirm = self._pick(st, "daily:have_many", self.bank.daily["have_many"], x=hm.group(1).lower(),
                                 noun=hm.group(2).lower())
            confirm = confirm[:1].upper() + confirm[1:]
        from engramm.chat.events import find_event
        ev = find_event(text, self._today())
        if ev is not None:
            self.events.note(ev[0], ev[1], sid)
            confirm = self._reply(st, "event_noted", x=ev[0])
        return Reply(msg, "learned", confirm, source={"kind": "user", "source": sid}, via="memory")

    def _confirm(self, st: DialogState, fs: list, name_before: str | None) -> str:
        self._generic_confirm = False
        about_you = [f for f in fs if f.subject.startswith(USER)]
        if len(about_you) >= 2 and not any("#name" in f.relation and f.subject == USER for f in about_you):
            lines = list(dict.fromkeys(personal_sentence(f.subject, f.relation, f.object, f.sentence)
                                       for f in sorted(about_you, key=_fact_rank)))
            return self._reply(st, "learned.several") + " " + " ".join(lines[:3])
        out = []
        used = set()
        for f in sorted(fs, key=lambda f: _fact_rank(f)):
            if len(out) == 2:
                break
            if f.subject == USER:
                cat = next((key for lab, key in _CATEGORY_KEYS if lab in f.relation), None)
                if cat == "name":
                    key = "learned.name_changed" if name_before and name_before != f.object else "learned.name_new"
                    out.append(self._reply(st, key, x=f.object))
                elif cat:
                    x = article(f.object) if cat in ("job",) else f.object
                    if cat == "car":
                        x = f.object
                    liked = st.uses.get("last_like")
                    if cat == "fav" and liked and liked[0] == st.turn and liked[1].lower().endswith(f.object.lower()):
                        x = liked[1]                       # "the Beatles", as said
                        x = x[:1].upper() + x[1:]
                    out.append(self._reply(st, f"learned.{cat}", x=x))
                elif f.kind == "NUMBER" and re.fullmatch(r"\d{1,3}", f.object) and 0 < int(f.object) < 120 and \
                        re.search(r"\b(?:i'm|i am|im|age|aged|years? old)\b", f.sentence, re.I):
                    out.append(self._reply(st, "learned.age", x=f.object))
                elif "about_you" not in used:
                    used.add("about_you")
                    self._generic_confirm = True
                    out.append(self._reply(st, "learned.about_you"))
            elif f.subject.startswith(USER + ":"):
                noun = f.subject.partition(":")[2]
                if "#name" in f.relation:
                    many = " and " in f.object or noun in ("children", "kids", "twins") or (
                        noun.endswith("s") and noun not in ("boss",))
                    out.append(self._reply(st, "learned.owned_names" if many else "learned.owned_name",
                                           x=f.object, noun=noun))
                elif f"owned:{noun}" not in used:
                    used.add(f"owned:{noun}")
                    out.append(self._reply(st, "learned.owned", noun=noun))
            elif "world" not in used:
                used.add("world")
                self._generic_confirm = True
                out.append(self._reply(st, "learned.world", subject=f.subject))
        if not out:
            self._generic_confirm = True
            out.append(self._reply(st, "learned.plain"))
        # "Nice to meet you" twice or "Got it — …" twice reads badly: keep distinct sentences only
        return " ".join(dict.fromkeys(out))

    def _memory_list(self, st: DialogState, text: str) -> Reply:
        bot = self.bot
        bot.refresh()
        texts = [(sid, t) for sid, t in bot.user_texts().items() if sid.startswith(CHAT_PREFIX)]
        if not texts:
            return Reply(text, "memory", self._reply(st, "memory.empty"), via="memory")
        mine, other = [], []
        for sid, t in texts:
            fs = [f for f in bot.facts.facts if f.source == sid]
            about_you = [f for f in fs if f.subject.startswith(USER)]
            if about_you:
                for f in sorted(about_you, key=_fact_rank):
                    line = personal_sentence(f.subject, f.relation, f.object, f.sentence)
                    if line not in mine:
                        mine.append(line)
            elif fs or not re.search(r"\b(?:i|my|me|i'm)\b", t.lower()):
                other.append(t.strip())
            else:
                line = to_second_person(t) or f"You said: “{t.strip()}”"
                mine.append(line)
        lines = []
        if mine:
            lines.append(self._reply(st, "memory.intro"))
            lines += [f"• {m}" for m in mine[:20]]
        if other:
            lines.append(self.bank.replies["memory"]["others"])
            lines += [f"• {o}" for o in other[:10]]
        lines.append(self.bank.replies["memory"]["outro"])
        return Reply(text, "memory", "\n".join(lines), via="memory")

    # -- pending questions --------------------------------------------------------------------

    def _fill_pending(self, st: DialogState, pending: dict, msg: str, units: list[Unit]) -> Reply | None:
        """The answer to a question ENGRAMM asked ("What should I call you?" → "Erik")."""
        if len(units) != 1:
            return None
        u = units[0]
        if u.act in ("question", "forget", "tool", "about", "remember", "safety"):
            return None
        if u.act == "intent" and u.intent in ("no",):
            return Reply(msg, "smalltalk", self._pick(st, "intent:no", self.bank.by_id["no"].responses), via="smalltalk")
        if u.act == "intent" and u.intent not in ("yes",):
            return None
        if gibberish(u.text) or is_mash(u.text):
            return None                          # "asdfgh" is no favourite food
        if pending.get("slot") not in ("who_mean", "correction") and \
                re.match(r"^(?:my|i|i'm|im|i am|i've|we)\b", u.text.strip(), re.I) and len(u.text.split()) >= 3:
            return None                          # a whole sentence about you: normal learning reads it right
        slot = pending.get("slot")
        if slot == "who_mean":                   # "Sorry, who's ‘he’?" → "Emmanuel Macron": the question again
            name = msg.strip(" .!?")
            if not name or len(name.split()) > 6 or name.endswith("?"):
                return None
            name = re.sub(r"^(?:i mean|i meant|meant|it's|its|he's|she's|the one called)\s+", "", name, flags=re.I)
            pron = pending.get("pron", "he")
            poss = pron.lower() in ("his", "their", "hers") or (
                pron.lower() == "her" and re.search(r"\bher\s+[a-z]", pending.get("question", ""), re.I))
            q = re.sub(rf"\b{re.escape(pron)}\b", name + ("'s" if poss else ""), pending.get("question", ""),
                       count=1, flags=re.I)
            self._spelled = q
            st.uses.pop("person_gap", None)
            return self._question(st, q)
        value = _slot_value(msg, slot)
        if value is None:
            return None
        if slot == "correction":
            q = pending.get("question") or ""
            value = re.sub(r"^(?:no,? |nope,? |actually,? |well,? )?(?:it's|its|it is|it was|that's|thats|that is|"
                           r"the (?:right |correct )?answer is|the ceo is|he is|she is|they are)\s+", "", value.strip(),
                           flags=re.I).strip(" .!")
            if value.islower() and re.match(r"^\s*who\b", q, re.I):
                value = " ".join(w[:1].upper() + w[1:] for w in value.split())
            sent = answer_sentence(q, value, _atype(q)) or f"The answer to “{q}” is {value}."
            r = self._learn(st, [sent], msg)
            r.text = self._reply(st, "correction.ok") + (f" ({sent})" if sent else "")
            return r
        store = pending.get("store")
        if not store:
            return None
        if slot == "name":
            value = " ".join(w[:1].upper() + w[1:] for w in value.split())
        elif slot == "job":
            value = article(value)
        return self._learn(st, [store.format(x=value)], msg)

    def _follow(self, st: DialogState, units: list[Unit], text: str, main: Reply) -> str:
        """A question back, at most one per reply: how an announced event went, or the name, once,
        after a greeting."""
        self._follow_key = None
        if st.pending is not None:
            return ""
        wants = None
        for u in units:
            if u.act == "intent":
                it = self.bank.by_id.get(u.intent)
                if it and it.follow:
                    wants = it.follow
        greeted = any(u.act == "intent" and (u.intent or "").startswith(("greeting", "how_are_you")) for u in units)
        if greeted:
            due = self.events.due(self._today(), set(self.bot.user_texts()))
            if due is not None:
                self.events.mark_asked(due)
                return self._reply(st, "event_followup", x=due.what)
        if wants is None or wants == "ask_mood":
            return ""
        key = wants
        if key in st.asked:
            return ""
        cat = {v: k for k, v in _ASK_FOR_CATEGORY.items()}.get(key)
        if key == "ask_name" and self.user_name():
            return ""
        if cat and cat in self._known_categories():
            return ""
        q = self.bank.fun["questions"].get(key)
        if not q or not q.get("text"):
            return ""
        st.asked.append(key)
        st.pending = {"slot": q["slot"], "store": q["store"], "turn": st.turn}
        self._follow_key = key
        return q["text"]

    # -- small reactions ----------------------------------------------------------------------

    def _feeling(self, st: DialogState, u: Unit) -> str:
        cat_id, neg, valence = u.data["category"], u.data["negated"], u.data["valence"]
        if neg and valence == "positive":
            cat_id = "sad"
        elif neg and valence == "negative":
            return self._pick(st, "feeling:negated", self.bank.negated_negative)
        cat = next(c for c in self.bank.categories if c.id == cat_id)
        return self._pick(st, f"feeling:{cat.id}", cat.responses)

    def _chitchat(self, st: DialogState, u: Unit, parts: list[_Part], alone: bool) -> None:
        # a bare topic ("Photosynthesis", "the Eiffel Tower") gets its article
        words = u.text.strip(" ?!.").split()
        if alone and 1 <= len(words) <= 4 and not re.search(r"\b(?:is|are|was|were|i|you|my)\b", u.text, re.I):
            found = self.about.find(u.text.strip(" ?!."))
            if found:
                parts.append(_Part("main", " ".join(found.sentences)))
                st.last_about = {"title": found.title, "doc": found.doc, "next": found.next_sentence,
                                 "end": found.end_sentence, "source": found.source}
                self.bot.context.update({"answer": None, "atype": None, "mention": found.title})
                return
        # a mood word about something else ("the weather is terrible"): a short reaction
        if not alone:
            return
        # a short phrase right after a moment ("a bit stressful" → "work stuff"): it continues that topic
        le = st.last_exp
        if le and st.turn - le.get("turn", -99) <= 2 and _AGREE.fullmatch(u.norm):
            # "yeah exactly" after ENGRAMM's question about the moment: stay with it, don't echo it
            key = "exp_agree_neg" if le.get("valence") == "negative" else "exp_agree_pos"
            parts.append(_Part("main", self._pick(st, f"daily:{key}", self.bank.daily[key])))
            return
        if le and st.turn - le.get("turn", -99) <= 2 and len(words) <= 5 and \
                not re.search(r"\b(?:you|your)\b", u.text, re.I):
            key = "exp_more_neg" if le.get("valence") == "negative" else "exp_more_pos"
            parts.append(_Part("main", self._pick(st, f"daily:{key}", self.bank.daily[key],
                                                  x=u.text.strip(" .!").lower())))
            return
        fe = self.bank.feeling(u.norm)
        val = fe[0].valence if fe and fe[0].valence in ("positive", "negative") else _valence(u.norm)
        if val:
            parts.append(_Part("main", self._reply(st, f"react.{val}")))
            return
        if alone:
            parts.append(_Part("main", self._reply(st, "chitchat")))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_STOP_CHAT = frozenset("the and but not just really very so too also that this there then than what with have has had "
                       "was were are is be been being for from into about some any all okay yeah yes no lol haha "
                       "i'm i've me my mine we our us".split())


_ELLIPSIS = re.compile(r"^(?:and|what about|how about)(?: (?:of|for|in|with))? (?P<x>(?:the )?[A-Z][\w'\- ]{1,40}?)\s*\??$",
                       re.I)
_QUESTION_WORDS = {"what", "who", "where", "when", "why", "how", "which", "whose", "is", "are", "does", "did", "can",
                   "was", "were"}


def _fill(text: str, **fmt) -> str:
    def rep(m):
        v = fmt.get(m.group(1))
        return m.group(0) if v is None else str(v)
    out = re.sub(r"\{(\w+)\}", rep, text)
    out = re.sub(r"[ ]{2,}", " ", out)
    return out[:1].upper() + out[1:] if out[:1].islower() else out


_CLAUSE_PRON = re.compile(r"(?:,\s*(?:and\s+)?|\s+and\s+|(?<=[.!;])\s+)(he|she|they|it)\s+(?=[a-z])", re.I)
_OWNER = re.compile(r"\b(?:my|our)\s+((?:little |big |older |younger |best |step)?[a-z]+)\b|"
                    r"\bi have (?:a|an|one|two|three) ((?:little |big |older |younger )?[a-z]+)", re.I)


def resolve_statement(text: str) -> str:
    """"My brother is called Tom and he lives in Munich." → "My brother is called Tom. My brother
    lives in Munich." — a clause that starts with he/she/they/it after a clause about "my X"
    becomes a sentence about "my X", so the fact memory files both facts under your brother."""
    m = _OWNER.search(text)
    if not m:
        return text
    noun = (m.group(1) or m.group(2)).strip()
    if noun in ("name", "names", "favourite", "favorite", "own", "life", "job", "home"):
        return text
    pieces = _CLAUSE_PRON.split(text)          # [clause0, pronoun1, clause1, pronoun2, clause2, …]
    if len(pieces) < 3 or len(pieces[0]) < m.end() - 1:
        return text
    sents = [pieces[0].strip().rstrip(",").strip()]
    for k in range(1, len(pieces), 2):
        sents.append(f"My {noun} {pieces[k + 1].strip()}")
    out = []
    for sent in sents:
        sent = sent.strip()
        if sent and not sent.endswith((".", "!", "?")):
            sent += "."
        out.append(sent[:1].upper() + sent[1:])
    return " ".join(x for x in out if x)


_CAPS_SPAN = re.compile(r"\b[A-Z][\w'’.\-]*(?:\s+(?:of|the|and|de|von|van|da|del|la|le)?\s*[A-Z][\w'’.\-]*)*")


def _norm_value(v: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", v.lower()).strip()


def _same_value(a: str, b: str) -> bool:
    x, y = _norm_value(a), _norm_value(b)
    return bool(x) and bool(y) and (x == y or f" {x} " in f" {y} " or f" {y} " in f" {x} ")


def _agreeing_sources(answer: str | None, rows: list, src: dict) -> list[str]:
    """Other independent sources (another article, feed or site) whose fetched sentences hold the
    same answer — "(from Wikipedia …; also BBC News)"."""
    if not answer or len(_norm_value(answer)) < 3:
        return []
    out = []
    for row in rows:
        t, rs = row[0], row[1]
        if rs.get("key") == src.get("key") or not _same_value(answer, t) and _norm_value(answer) not in _norm_value(t):
            continue
        name = rs.get("title") if rs.get("kind") == "shelf" else rs.get("source") or rs.get("title")
        label = f"Wikipedia's “{name}”" if rs.get("kind") == "shelf" else str(name)
        if name and label not in out and (rs.get("kind") != src.get("kind") or rs.get("key") != src.get("key")):
            out.append(label)
    return out


_BOT_EXPERIENCE = re.compile(r"^(?:but |so |and |lol |haha )?(?:have|did|do) (?:you|u) (?:ever |even |actually )?"
                             r"(?P<v>seen|watched|watch|read|heard|been to|been|tried|played|eaten|eat|visited|met|"
                             r"listened to|see|hear|play|taste|tasted|smell)\b(?P<rest>.*)$")
_VERB_BASE = {"seen": "see", "watched": "watch", "read": "read", "heard": "hear", "been to": "go anywhere",
              "been": "go anywhere", "tried": "try", "played": "play", "eaten": "eat", "visited": "visit",
              "met": "meet", "listened to": "listen to", "tasted": "taste"}
_BOT_LIMIT = re.compile(r"^(?:lol |haha |but |well |oh )?(?:you|u) (?:can't|cant|cannot|can not|don't|dont|do not|"
                        r"aren't|are not|have no|got no|wouldn't|won't) (?:even |really |actually )?"
                        r"(?:watch|see|eat|taste|hear|listen|feel|sleep|go|travel|read|play|smell|have|know what it's like|"
                        r"understand|be|leave)\b.*$|^(?:lol |haha )?(?:you're|youre|you are) (?:just |only )?(?:a |an )?"
                        r"(?:bot|program|computer|machine|robot|ai)\b.*$")
_RECAP = re.compile(r"^(?:can you )?(?:remind me |tell me )?(?:what|which things?) (?:did |have )?(?:we|we've) "
                    r"(?:talk(?:ed)? about|discuss(?:ed)?|cover(?:ed)?)(?: so far| today| before| earlier)?$|"
                    r"^what were we (?:talking about|saying)$|^(?:summarize|sum up|recap)(?: our| the)? (?:conversation|chat)$")
_WHERE_WERE_WE = re.compile(r"^(?:ok |okay |so |anyway )?(?:where were we|where did we (?:leave off|stop)|what was i saying|"
                            r"what were we just talking about|back to (?:what we were talking about|the topic))$")
_JOKE_BAD = re.compile(r"^(?:haha |lol |ha |ugh |oh no |omg )*(?:that's|thats|that was|that one was|it's|its|"
                       r"so|that joke was|wow that's)? ?(?:so |really |pretty |kinda |very )?(?:bad|terrible|awful|lame|"
                       r"cringe|cringy|corny|not funny|unfunny|dumb|stupid|the worst)(?: joke)?[!. ]*(?:lol|haha)?$")
_JOKE_GOOD = re.compile(r"^(?:ok |okay |haha |lol |ha )*(?:that's|thats|that was|that one was|this one was)? ?"
                        r"(?:actually |really |pretty |so )?(?:good|funny|great|hilarious|nice)(?: one)?[!. ]*$")
_REFINE = re.compile(r"^(?:maybe |how about |what about |ideally |preferably |do you have )?(?:something|anything|one|ideas?|"
                     r"a dish|a recipe|a meal|recipes)? ?(?:with|using|that has|containing|made with) (?P<x>[a-z ]{3,25})$")
_NUMBERISH = re.compile(r"^(?:\d|(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                        r"twenty|thirty|forty|fifty|hundred|thousand|million|several|many|few)\b)", re.I)
_HOW_Q = re.compile(r"^\s*how (?:do|does|did|can|could|should|would|to|is|are|was|were) (?!.*\b(?:old|many|much|far|"
                    r"long|tall|high|big|large|deep|wide|heavy|fast|often)\b)", re.I)
_ROLE_Q = re.compile(r"^\s*who(?:'s| is| was| are| were)\s+(?:the\s+)?(?P<role>(?:current |new |present |former |first )?"
                     r"[a-z][a-z -]{1,40}?) (?:of|at|for) (?P<x>.+?)\s*\??$", re.I)
_ROLE_SYN = {"ceo": ["ceo", "chief executive"], "chief executive": ["ceo", "chief executive"],
             "pm": ["prime minister"], "prime minister": ["prime minister", "premier"],
             "head": ["head", "leader", "chief"], "boss": ["ceo", "chief executive", "head", "boss"],
             "founder": ["found", "co-found", "established", "created"], "owner": ["own", "owner", "bought", "acquired"],
             "leader": ["leader", "led", "head"], "coach": ["coach", "manager", "head coach"],
             "manager": ["manager", "coach"], "chancellor": ["chancellor"], "mayor": ["mayor"],
             "president": ["president"], "king": ["king"], "queen": ["queen"], "captain": ["captain"]}
_TITLE_WORDS = re.compile(r"\b(?:general|minister|secretary|attorney|assistant|officer|council|department|ministry|"
                          r"committee|board|director|commission|agency|office|government|administration|parliament|"
                          r"party|company|corporation|division|bureau|court|forces|army)\b", re.I)
_SUPERLATIVE_Q = re.compile(r"^\s*(?:what|which|who)(?:'s| is| was| are| were)\s+(?:the\s+)?"
                            r"(?P<sup>\w+est|most \w+|least \w+|biggest)\s+(?P<noun>[a-z]+(?: [a-z]+)?)"
                            r"(?P<rest>.*?)\s*\??\s*$", re.I)
_SUP_FREE = re.compile(r"^(?:\s*\(?|,)?\s*(?:in the world|on earth|ever|of all time|in the solar system|in history|"
                       r"known|recorded|\)|,|\.|;|$)", re.I)


def _place_case(text: str) -> str:
    """"italy" → "Italy", "new york" → "New York", "the beatles" → "the Beatles"."""
    small = {"the", "of", "and", "de", "la", "del", "von", "van", "upon", "on"}
    out = [w if (i > 0 and w in small) or (i == 0 and w == "the") else w[:1].upper() + w[1:]
           for i, w in enumerate(text.split())]
    return " ".join(out)


def _implausible(q: str, answer: str | None, evidence: str | None) -> bool:
    """A looked-up short answer that cannot be meant: a count for "who …?" ("two goals was the top
    scorer"), or a superlative the evidence does not say about it — the biggest *commercial success*
    is no planet, and the tallest mountain *outside Asia* is not the tallest mountain."""
    if not answer or not evidence:
        return False
    if re.match(r"^\s*who\b", q, re.I) and _NUMBERISH.match(answer):
        return True
    if _HOW_Q.match(q) and len(answer.split()) <= 3:
        return True                                   # "how do people deal with grief?" — "conspecifics" is no answer
    m = _ROLE_Q.match(q)
    if m:
        # "who is the CEO of Apple?": the evidence must name the role, and the answer is a person, not a title
        role = re.sub(r"^(?:current|new|present|former|first)\s+", "", m.group("role").lower().strip())
        syn = _ROLE_SYN.get(role, [role])
        if not any(x in evidence.lower() for x in syn) or _TITLE_WORDS.search(answer):
            return True
    m = _SUPERLATIVE_Q.match(q)
    if not m or m.group("rest").strip():
        return False
    ev = evidence.lower()
    sup, noun = m.group("sup").lower(), m.group("noun").lower().split()[0].rstrip("s")
    a = ev.find(answer.lower())
    for hit in re.finditer(re.escape(sup), ev):
        after = ev[hit.end():]
        nm = re.match(r"(?:\s+[a-z-]+){0,2}?\s+(" + re.escape(noun) + r"s?)\b", after)
        if nm:
            # "the tallest mountain outside Asia" restricts what the question does not
            return not _SUP_FREE.match(after[nm.end():])
        if a >= 0 and abs(hit.start() - a) <= len(answer) + 12:
            return not _SUP_FREE.match(after)     # "Pacific (the largest), Atlantic …"
    return True


_DISLIKE = re.compile(r"^(?:honestly,? |tbh,? |to be honest,? |well,? )?i (?:really |just |honestly )?"
                      r"(?:(?:don'?t|do not|never|can'?t|cannot) (?:really |much |even |particularly )?"
                      r"(?:like|love|enjoy|stand|care for)|hate|dislike|detest|can'?t stand) "
                      r"(?P<x>(?!it\b|that\b|this\b|when\b|how\b|my\b|you\b|people\b|being\b|having\b)"
                      r"[a-z][a-z' -]{1,40}?)(?: (?:much|at all|very much|that much|anymore|tbh|honestly))?[.!]*$", re.I)
_LIKES_Q = re.compile(r"^(?:so |and )?what (?:do|did) i (?P<neg>not |n't |never )?(?P<v>like|love|enjoy|hate|dislike)"
                      r"(?: again)?\s*\??$|^what (?:don'?t|do not|didn'?t) i (?P<v2>like|love|enjoy)\s*\??$", re.I)
_DAY_WAS = re.compile(r"^(?:ugh |man |well |honestly |omg )?(?P<what>work|school|class|uni|college|today|the day|my day|"
                      r"it|my shift|the shift|practice|training|the meeting|my exam|the exam) (?:was|has been|is being) "
                      r"(?:so |really |super |pretty |very |kinda |quite |such )?(?:(?P<bad>long|exhausting|tiring|rough|hard|"
                      r"stressful|a lot|busy|crazy|awful|terrible|horrible|bad|boring|draining|brutal|hectic|a nightmare|"
                      r"the worst|annoying|frustrating)|(?P<good>good|great|fun|nice|amazing|awesome|fine|okay|productive|"
                      r"chill|relaxing|easy|the best))(?: (?:today|honestly|tbh|lol))?[.!]*$")
_WORKOUT_DONE = re.compile(r"^(?:so |well |today |yesterday |earlier )?i (?:just |finally |also )?(?:went to the gym|hit the gym|"
                           r"worked out|did a workout|went for a (?:run|jog|swim|walk|bike ride|ride|hike)|went (?:running|jogging|"
                           r"swimming|hiking|cycling|biking|climbing|bouldering)|did (?:yoga|pilates|crossfit|cardio|leg day|"
                           r"some exercise|a hiit class|hiit)|ran (?:\d+|a|five|ten) ?(?:k|km|miles?|kilometers?|kilometres?)|"
                           r"played (?:football|soccer|tennis|basketball|squash|badminton|volleyball|golf|padel)|"
                           r"had (?:football|soccer|tennis|basketball) practice|lifted(?: weights)?)"
                           r"(?: today| this morning| tonight| earlier| yesterday| after work)?[.!]*$")
_HOW_IT_WENT = re.compile(r"^(?:it was |it's been |was |that was |honestly |pretty |really |so |super |kinda )*(?:(?P<hard>hard|tough|"
                          r"brutal|exhausting|tiring|intense|killer|a struggle|rough|difficult)|(?P<good>good|great|amazing|fun|"
                          r"awesome|nice|easy|fine|solid)|(?P<meh>ok|okay|alright|meh|so-so))(?: (?:honestly|tbh|lol|actually))?[.!]*$")
_DAY_MEH = re.compile(r"^(?:mine|my day|it|today|the day)(?: was| has been|'s been| is) (?:ok|okay|alright|fine|meh|so-so|"
                      r"not bad|average|nothing special)(?: i guess| i suppose| honestly| tbh)?[.!]*$")
_GOAL = re.compile(r"^(?:i (?:really |kinda |kind of )?(?:want|would like|wanna|need|plan|am planning|'m planning|am trying|"
                   r"'m trying|hope|am going|'m going|gotta)(?: to)?|my goal is to) (?P<goal>(?:get|be|become|lose|build|run|"
                   r"learn|start|stop|quit|save|eat|sleep|read|exercise|work out|drink|cut down)\b.{2,50}?)[.!]*$")
_GOAL_TOPICS = [("fitness", re.compile(r"\b(?:fit|fitter|in shape|stronger|muscle|weight|marathon|run|running|exercise|"
                                       r"work out|athletic|abs|healthier)\b")),
                ("learning", re.compile(r"^learn\b")),
                ("money", re.compile(r"\b(?:save|saving)\b.*\bmoney\b|\bsave up\b|\bbudget\b")),
                ("sleep", re.compile(r"\bsleep\b")),
                ("habit", re.compile(r"^(?:quit|stop|cut down)\b"))]
_TIPS = re.compile(r"^(?:so |ok |okay )?(?:any |some |got any |do you have (?:any )?)?(?:tips|advice|suggestions|ideas|pointers)"
                   r"(?: for me| on that| for that)?\??$|^(?:how|where) (?:do|should) i (?:start|begin)\??$|^how\??$")
_DIET = re.compile(r"^(?:btw |by the way |oh |also )?i(?:'m| am) (?:a |actually |also |now )?(?P<diet>vegetarian|vegan|"
                   r"pescatarian|gluten[- ]free|lactose intolerant|on a diet)(?: now| btw| actually)?[.!]*$")
_POST_WORKOUT = re.compile(r"^what (?:should|can|could|do) i (?:eat|have)(?: after| post| before)(?: a| my| the)? "
                           r"(?:workout|work out|gym|training|run|exercise|session)\??$|^(?:good |any )?post[- ]workout "
                           r"(?:food|meal|snack)s?\??$")
_WHICH_ONE = re.compile(r"^(?:and |so |ok )?which (?:one |of them |of the two |of those )?(?:is|was|has) (?:the )?"
                        r"(?P<w>bigger|larger|smaller|older|younger|taller|higher|longer|shorter|more populous)\??$")
_CALC_MORE = re.compile(r"^(?:and |then |now |ok )?(?P<op>times|x|\*|multiplied by|plus|\+|minus|-|divided by|/|over|"
                        r"to the power of)\s*(?P<n>-?\d+(?:[.,]\d+)?)\??$")
_CALC_OPS = {"times": "*", "x": "*", "*": "*", "multiplied by": "*", "plus": "+", "+": "+", "minus": "-", "-": "-",
             "divided by": "/", "/": "/", "over": "/", "to the power of": "^"}
_HOMEWORK = re.compile(r"^(?:can|could|would|will) you (?:please )?help me(?: out)?(?: with)? (?:my |some |this |an? )?"
                       r"(?:homework|assignment|essay|studies|studying|exam|test|project|school ?work|revision|math|maths|"
                       r"physics|chemistry|biology|history|english|geography|coursework)(?: please)?$|"
                       r"^i need help with (?:my )?(?:homework|assignment|essay|exam|test|studies)$")
_SUBJECT = re.compile(r"^(?:it's|its|it is|it's about|in|for)?\s*(?P<s>math|maths|mathematics|algebra|geometry|calculus|physics|"
                      r"chemistry|biology|history|geography|english|literature|french|spanish|german|latin|economics|"
                      r"computer science|programming|coding|philosophy|art|music)(?: homework| class| stuff)?$")
_SUBJECT_KINDS = [("math", re.compile(r"math|maths|mathematics|algebra|geometry|calculus")),
                  ("science", re.compile(r"physics|chemistry|biology|computer science|programming|coding")),
                  ("language", re.compile(r"english|literature|french|spanish|german|latin")),
                  ("other", re.compile(r".+"))]
_LOSS = re.compile(r"\b(?:died|dead|passed away|passed on|lost (?:my|our)|put down|put to sleep|funeral|"
                   r"is gone|has gone)\b", re.I)
_GRIEF_NAME = re.compile(r"^(?P<p>his|her|their|its) name (?:was|is) (?P<x>[a-z][a-z' -]{1,25})[.!]*$")
_GRIEF_AGE = re.compile(r"^(?:he|she|they|it) (?:was|were) (?:only |almost |nearly |just )?(?P<n>\d{1,3})"
                        r"(?: years old| years| yrs)?[.!]*$")
_PRON = {"his": "he", "her": "she", "their": "they", "its": "it"}
_FOLLOW_STATEMENT = re.compile(r"^(?:it's|its|it is|it was|this is|that was|that's|thats|the one|i start|i begin|"
                               r"i'm the|i am the|i have to|i need to|i was|i've been|second|third|first|again|"
                               r"for the (?:second|third)|and (?:it|that|then))\b")
_FEELING_WORD = re.compile(r"\b(?:nervous|anxious|sad|happy|scared|worried|excited|angry|stressed|tired|upset|lonely|"
                           r"depressed|afraid|frustrated|glad|thrilled|devastated|heartbroken)\b")
_CATEGORY_LABELS = frozenset(("#name", "#home", "#job", "#employer", "#birth", "#origin", "#food", "#colour", "#car"))
_HONOUR = re.compile(r"^(?:and |so |guess what,? )?i(?:'m| am| was| got asked to be| was asked to be) (?:the |a |his |her )?"
                     r"(?:best man|maid of honou?r|bridesmaid|groomsman|godfather|godmother|witness)[.!]*$")
_WEDDING = re.compile(r"\b(?:best man|maid of honou?r|wedding|bride|groom|married|marry|engaged)\b")
_SPEECH = re.compile(r"\b(?:speech|toast|eulogy|presentation|talk at)\b")
_HELP_ME = re.compile(r"^(?:can|could|would|will) you help(?: me)?(?: with (?:it|that|this))?(?: please)?$|"
                      r"^help me(?: please)?$|^any (?:ideas|tips|advice)$|^where do i (?:even )?start$")
_SPEECH_HELP = re.compile(r"^(?:can you |could you |please )?help me (?:write|with|prepare|plan) (?:a |my |the )?"
                          r"(?:best man |maid of honou?r |wedding |birthday |retirement )?(?:speech|toast)(?: please)?$")
_JOB_CHANGE = re.compile(r"^(?:so |well |guess what,? |btw )?i (?:just |finally |recently )?(?:(?P<quit>quit|left|resigned from|"
                         r"handed in my notice at|retired from)(?: my)? (?:job|work|position|company)|retired|"
                         r"(?P<bad>got fired|was fired|got laid off|was laid off|lost my job|got let go|was let go))"
                         r"(?: today| yesterday| last week| this week)?[.!]*$")
_TRIP = re.compile(r"^(?:so |well |guess what,? )?(?:i|we|me and my \w+|my \w+ and i) (?:just |finally |recently |also )?"
                   r"(?:got back from|came back from|returned from|went to|were in|was in|visited|travel+ed to|flew to|"
                   r"went on|spent (?:a|the|two|three|four|five|\w+) (?:week|weekend|days?|weeks?) in) "
                   r"(?P<x>[a-z][a-z' -]{1,40}?)(?: (?:last|this) (?:week|month|year|weekend|summer|winter|spring|autumn)|"
                   r" yesterday| recently| for (?:a|two|three|\w+) (?:week|weeks|days))?[.!]*$")
_TRIP_WORD = re.compile(r"(?:a |my |our |the )?(?:vacation|holiday|holidays|trip|break|weekend away|travels?|honeymoon|"
                        r"road trip|city trip|business trip|backpacking trip)")
_NOT_A_TRIP = re.compile(r"(?:the |a |my |our )?(?:gym|cinema|movies|store|shop|supermarket|work|office|school|class|bed|"
                         r"doctor|dentist|hospital|party|concert|restaurant|bar|pub|club|church|mall|bank|park|beach|"
                         r"pool|library|game|match|meeting|wedding|funeral|game night)")
_HOBBY = re.compile(r"^i (?:also |really |still |sometimes )?(?P<v>play|practi[sc]e|collect|do) (?:the |some )?"
                    r"(?P<x>(?!it\b|that\b|this\b|my\b|not\b|nothing\b|what\b|well\b|too\b)[a-z][a-z -]{1,25}?)"
                    r"(?: a lot| sometimes| every day| on weekends| in my free time| for fun| as a hobby)?[.!]*$")
_HOBBY_BARE = re.compile(r"^i (?:also |really |love to |like to )?(?P<v>paint|draw|knit|sing|dance|bake|surf|skate|climb|box|"
                         r"swim|crochet|sew|garden|journal)(?: a lot| for fun| sometimes| as a hobby| in my free time)?[.!]*$")
_GERUND = {"paint": "painting", "draw": "drawing", "knit": "knitting", "sing": "singing", "dance": "dancing",
           "bake": "baking", "surf": "surfing", "skate": "skating", "climb": "climbing", "box": "boxing",
           "swim": "swimming", "crochet": "crochet", "sew": "sewing", "garden": "gardening", "journal": "journaling"}
_DURATION_ANS = re.compile(r"^(?:for |since )?(?:about |around |almost |nearly |over |like |roughly |maybe |just )?"
                           r"(?P<n>\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|"
                           r"a few|a couple of|a couple|several|many) (?P<u>years?|months?|weeks?|days?)(?: now| or so| already)?[.!]*$")
_REC_SEEN = re.compile(r"^(?:oh |hmm |ah )?(?:i(?:'ve| have)? )?(?:already )?(?:read|seen|watched|tried|heard|played|been to|"
                       r"visited|done|know) (?:that|it|those|them|all of (?:them|those)|these|all of these)"
                       r"(?: one| ones)?(?: already)?[.!]*$")
_REC_GENRE = re.compile(r"^(?:maybe |preferably |ideally |hmm |ok |okay |more like )?(?:something|somewhere|anything|one|ones|"
                        r"a|an|more|some)?\s*(?:a bit |more |really |kinda |pretty )?(?P<g>[a-z-]+)"
                        r"(?: one| ones| please| maybe| instead| stuff| place| places| book| books| movie| movies)?\??$")
_I_LIKE = re.compile(r"^i (?:really |absolutely |just )?(?:love|like|adore|am into|'m into|am a big fan of|'m a big fan of) "
                     r"(?P<x>[a-z][a-z' .-]{1,40})$")
_BEST_OF = re.compile(r"^(?:so |and )?what(?:'s| is| are|s) (?P<who>their|his|her|its|the) (?:best|greatest|most famous|top|"
                      r"most popular) (?:song|songs|album|albums|movie|movies|film|films|book|books|novel|work|track|"
                      r"tracks|show|episode|game|dish)\??$")
_PET_PEEVE = re.compile(r"^i (?:really |just )?(?:don'?t like|do not like|hate|can'?t stand|cannot stand|dislike) "
                        r"(?:it )?when\b.{3,}", re.I)
_RELATABLE = re.compile(r"(?:mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|sundays?|mornings?|early mornings|"
                        r"waking up early|getting up early|alarms?|alarm clocks?|rain|rainy days|winter|the cold|cold weather|"
                        r"the heat|hot weather|summer|traffic|commuting|the commute|homework|exams?|tests|waiting|queues|"
                        r"lines|cleaning|chores|housework|laundry|dishes|doing the dishes|meetings|emails|taxes|"
                        r"the dentist|dentists|spiders|mosquitos|mosquitoes|bugs|small talk|crowds|noise|snow)", re.I)
_DISLIKE_DE = re.compile(r"^(?:also |ehrlich gesagt |ehrlich )?ich (?:mag|esse|trinke|schaue|höre|lese) "
                         r"(?:(?:echt |wirklich |gar |überhaupt )?(?:keine?n?|nicht so gern|nicht gern|nicht)) "
                         r"(?P<x>[a-zäöüß][a-zäöüß -]{1,30}?)(?: so gern| gern| so)?$|"
                         r"^ich (?:hasse (?P<z>[a-zäöüß][a-zäöüß -]{1,30})|kann (?P<y>[a-zäöüß][a-zäöüß -]{1,30}?) "
                         r"nicht (?:leiden|ausstehen))$")
_RELATABLE_DE = re.compile(r"(?:montage?|montags|morgende?|frühes aufstehen|früh aufstehen|wecker|regen|regenwetter|winter|"
                           r"kälte|hitze|stau|staus|pendeln|hausaufgaben|prüfungen|klausuren|warten|schlangen|putzen|"
                           r"aufräumen|hausarbeit|wäsche|abwasch|meetings|e-mails|mails|steuern|zahnarzt|zahnärzte|"
                           r"spinnen|mücken|insekten|smalltalk|menschenmassen|lärm|schnee)", re.I)
_PREFER = re.compile(r"^(?:actually|no|well|hmm|wait)?,?\s*(?:i (?:think )?(?:prefer|like|love)|i'd say|make that|"
                     r"no wait,?) (?P<x>[a-z][a-z' -]{1,30}?)(?: more| better| instead| actually| now)?$")
_FAV_NOUN = {"#food": "food", "#colour": "colour", "#car": "car"}
_NAME_CUE = re.compile(r"\b((?:my name is|my name's|call me|i'm called|i am called|actually my name is) )"
                       r"([a-z][a-z'-]+(?: [a-z][a-z'-]+)?)\b(?=[.!,]|$)")
_PLACE_CUE = re.compile(r"\b((?:live in|living in|moved to|move to|moving to|from|born in|grew up in|based in|"
                        r"lives in|visited|went to|stay in|staying in) )([a-z][a-z' -]{1,40})")
_PLACE_TYPES = frozenset(("City", "Town", "Village", "Settlement", "Country", "AdministrativeRegion", "Island",
                          "CityDistrict", "Region", "State", "Place", "Location", "PopulatedPlace", "Continent"))
_TOPIC_EDGE = set("""who whom whose what which when where why how is are was were be been do does did done has have had
won win wins winning lost lose the a an of in on at for to by from with and or but about i me my you your he she it they
him her them his its their this that these those there here top best first last most many much old""".split())
_AGREE = re.compile(r"(?:yeah|yes|yep|yup|exactly|right|true|totally|definitely|absolutely|pretty much|kind of|kinda|"
                    r"sort of|i guess|i know|tell me about it|same|for real)(?:[ ,]+(?:yeah|exactly|right|true|totally|"
                    r"lol|haha|man|honestly))*[!. ]*")
_DOUBT = re.compile(r"(?:really|seriously|are you sure|you sure|is that (?:true|right|correct)|for real|"
                    r"no way|that can't be right|hm+ really|wait really)[?!.]*")
_SURPRISE = re.compile(r"(?:wow+|whoa+|woah+|omg|no way|that's (?:crazy|insane|wild|amazing|incredible|nuts|"
                       r"so cool|cool|interesting|fascinating|surprising|mad)|really|seriously|crazy|wild|"
                       r"interesting|fascinating|huh,? interesting|i didn't know that|didn't know that|"
                       r"cool|neat|nice)(?: fact)?[!?.]*")
_FAMILY_PLURALS = frozenset("kids children sons daughters brothers sisters siblings dogs cats pets twins "
                            "grandchildren".split())
_HAVE_COUNT = re.compile(r"^i (?:have|have got|'ve got|got) (two|three|four|five|six|seven|eight|nine|ten|\d{1,2}) "
                         r"([a-z]+)[.!]*$", re.I)
_THEIR_NAMES = re.compile(r"^(?:their names are|they are called|they're called|they are named|named|called)\s+(.+)$", re.I)
_BARE_NAMES = re.compile(r"[A-Z][a-zà-ÿ'-]+(?:\s*,\s*[A-Z][a-zà-ÿ'-]+)*\s+(?:and|&)\s+[A-Z][a-zà-ÿ'-]+")
_SELF_JOIN = re.compile(r"^((?:my name is|my name's|i'm|i am|call me)\s+[A-Za-z][\w'-]*)\s*(?:,\s*|\s+)and\s+"
                        r"((?:i'm|i am|i work|i live|i have|i've got|i come|i'm from|my \w+ (?:is|are))\b.+)$", re.I)


def _split_self_statements(msg: str) -> str:
    """"My name is Sam and I'm a teacher" → "My name is Sam. I'm a teacher." (each part is learnt)."""
    m = _SELF_JOIN.match(msg.strip())
    if not m:
        return msg
    second = m.group(2)
    return f"{m.group(1)}. {second[:1].upper() + second[1:]}"


def _theme_of(st: DialogState, rep: Reply) -> str | None:
    """A few words for "what did we talk about?"."""
    la = st.last_action or {}
    if rep.via == "everyday" and la.get("turn") == st.turn and str(la.get("kind", "")).startswith("rec:"):
        return {"food": "what to cook", "book": "books", "movie": "films", "series": "series", "music": "music",
                "game": "games", "activity": "things to do", "gift": "gift ideas", "travel": "travel",
                "hobby": "hobbies", "sleep": "sleep", "study": "studying"}.get(la["kind"][4:], "some ideas")
    if rep.via in ("empathy",) or rep.kind == "empathy":
        topic = (st.last_exp or {}).get("topic")
        return topic if topic else "how you're doing"
    if rep.kind in ("learned", "memory"):
        return "things about you"
    if rep.via in ("kb", "lookup", "about", "atlas") and st.topic and st.topic.get("turn") == st.turn:
        return st.topic.get("name")
    if la.get("turn") == st.turn and la.get("kind") in ("joke", "quiz", "riddle", "fact"):
        return {"joke": "jokes", "quiz": "a quiz", "riddle": "riddles", "fact": "fun facts"}[la["kind"]]
    return None


def _stems(text: str) -> set[str]:
    """Lower-case words with a plain English ending removed ("died" → "die", "formed" → "form")."""
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        for suf in ("ing", "ed", "es", "s", "d"):
            if len(w) > len(suf) + 2 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def _full_name(answer: str | None, texts: list[str]) -> str | None:
    """A one-word name answer in its longer form from the same article ("Vickers" → "Diana
    Vickers"), when exactly one longer form occurs there."""
    if not answer or " " in answer.strip() or not answer[:1].isupper():
        return answer
    forms = Counter(m.group(1) for t in texts for m in re.finditer(
        r"\b((?:[A-Z][\w'’.-]+ ){1,2})" + re.escape(answer) + r"\b", t))
    forms = Counter({f.strip(): n for f, n in forms.items()
                     if not any(w.lower() in _FULLNAME_STOP for w in f.split())})
    if len(forms) == 1:
        return f"{next(iter(forms))} {answer}"
    return answer


_UNIT = re.compile(r"\d[\d.,]*\s*(?:%|°|(?:k?m|cm|mm|km|mi|miles?|ft|feet|foot|in|inch(?:es)?|yards?|metres?|meters?|"
                   r"kilomet(?:re|er)s?|centimet(?:re|er)s?|light[- ]years?|au|astronomical units?|parsecs?|kg|g|grams?|"
                   r"kilograms?|tonnes?|tons?|lbs?|pounds?|ounces?|oz|l|litres?|liters?|ml|gallons?|hours?|minutes?|"
                   r"seconds?|days?|weeks?|months?|years?|km/h|mph|knots?|m/s|hectares?|acres?|sq|square)\b)|"
                   r"\b(?:million|billion|thousand|hundred) (?:k?m|kilomet|miles?|km|light|years?|kg|tonnes?|people)", re.I)
_LEN = r"(?:k?m|cm|mm|km|mi|miles?|ft|feet|foot|in|inch(?:es)?|yards?|metres?|meters?|kilomet(?:re|er)s?|" \
       r"centimet(?:re|er)s?|light[- ]years?|au|astronomical units?|parsecs?)"
_DIM_UNIT = {
    "far": re.compile(r"\d[\d.,]*\s*(?:million |billion |thousand )?" + _LEN + r"\b", re.I),
    "tall": re.compile(r"\d[\d.,]*\s*" + _LEN + r"\b", re.I),
    "high": re.compile(r"\d[\d.,]*\s*" + _LEN + r"\b", re.I),
    "deep": re.compile(r"\d[\d.,]*\s*" + _LEN + r"\b", re.I),
    "long": re.compile(r"\d[\d.,]*\s*(?:" + _LEN[3:-1] + r"|hours?|minutes?|days?|years?)\b", re.I),
    "wide": re.compile(r"\d[\d.,]*\s*" + _LEN + r"\b", re.I),
    "big": re.compile(r"\d[\d.,]*\s*(?:million |billion |thousand )?(?:" + _LEN[3:-1] +
                      r"|km2|km²|m2|m²|square \w+|sq \w+|hectares?|acres?|kg|kilograms?|tonnes?|tons?)\b|"
                      r"\b(?:\d+(?:[.,]\d+)?|two|three|four|five|ten|a hundred|a thousand)(?: and a half)? times\b", re.I),
    "heavy": re.compile(r"\d[\d.,]*\s*(?:million |billion )?(?:kg|kilograms?|g|grams?|tonnes?|tons?|lbs?|pounds?|ounces?)\b|"
                        r"\d+(?:\.\d+)?\s*[×x]\s*10", re.I),
    "hot": re.compile(r"\d[\d.,]*\s*(?:°|degrees|k\b|kelvin)", re.I),
    "old": re.compile(r"\d[\d.,±]*\s*(?:million |billion |thousand )?years?\b|\b(?:1[0-9]|20)\d\d\b", re.I)}
_DIM_UNIT["large"] = _DIM_UNIT["big"]
_MEASURE_TOPIC = re.compile(r"^\s*how (?P<dim>far(?: away)?|big|large|tall|high|deep|long|wide|heavy|hot|old) "
                            r"(?:is|are|was|were) (?P<t>[\w' .-]{2,50}?)(?: away| from (?:the )?earth| from here)?\s*\??$", re.I)
_MEASURE_CUES = {
    "far": re.compile(r"\b(?:distance|away|from (?:the )?(?:earth|sun)|light[- ]years?|astronomical units?|orbits?)\b", re.I),
    "far away": re.compile(r"\b(?:distance|away|from (?:the )?(?:earth|sun)|light[- ]years?|astronomical units?|orbits?)\b", re.I),
    "big": re.compile(r"\b(?:diameter|radius|circumference|times (?:that of|the size|larger|bigger)|area|size|wide|across|"
                      r"mass|covers)\b", re.I),
    "large": re.compile(r"\b(?:diameter|radius|circumference|times (?:that of|the size|larger|bigger)|area|size|wide|across|"
                        r"mass|covers)\b", re.I),
    "tall": re.compile(r"\b(?:tall|height|high|elevation|stands)\b", re.I),
    "high": re.compile(r"\b(?:tall|height|high|elevation|altitude|stands)\b", re.I),
    "deep": re.compile(r"\b(?:deep|depth|deepest)\b", re.I),
    "long": re.compile(r"\b(?:long|length|stretches|runs for)\b", re.I),
    "wide": re.compile(r"\b(?:wide|width|across|diameter)\b", re.I),
    "heavy": re.compile(r"\b(?:mass|weighs?|weight)\b", re.I),
    "hot": re.compile(r"\b(?:temperature|°|degrees|hot)\b", re.I),
    "old": re.compile(r"\b(?:years? old|age|formed|billion years|million years|founded|built)\b", re.I)}
_MEASURE_Q = re.compile(r"^\s*how (?:far|long|tall|high|big|large|deep|wide|heavy|fast|much does .+ weigh)\b", re.I)
_LIFE_SPAN_RE = re.compile(r"\([^()]*\b\d{3,4}\s*[–—-]\s*[^()]*?\b\d{3,4}\)")
_QUOTE_STOP = frozenset("when where who whom whose what which why how did doe do is are was were has had the a an of in on "
                        "at to for from by with and or".split())
_FULLNAME_STOP = frozenset("the a an in on at of by and but when after before during since while this that these "
                           "his her their its singer songwriter band album president king queen sir lady lord mr mrs ms "
                           "dr saint st".split())


def _name_match(asked: str, title: str) -> bool:
    """The article is about what was asked: the same name (a leading article, a "(…)" qualifier
    and a ", place" part aside) or one in a row of its words with at most one word more on
    either side — never just a title containing the letters ("thai" is not "Thailand")."""
    a = re.sub(r"^(?:the|a|an)\s+", "", asked.strip().lower())
    t = re.sub(r"^(?:the|a|an)\s+", "", re.sub(r"\s*\([^)]*\)$", "", title.strip().lower()))
    if not a or not t:
        return False
    if a == t or a == t.split(", ")[0]:
        return True
    aw, tw = re.findall(r"[\w'’-]+", a), re.findall(r"[\w'’-]+", t)
    short, long_ = (aw, tw) if len(aw) <= len(tw) else (tw, aw)
    if not short or len(long_) - len(short) > 1 or (short is aw and len(aw) == 1):
        return False                             # one asked word must be the whole name ("Tower" ≠ "Eiffel Tower")
    return any(long_[i:i + len(short)] == short for i in range(len(long_) - len(short) + 1))


_ANOTHER = re.compile(r"^(?:(?:ok|okay|yes|yeah|sure|haha|lol|nice|cool|great|wow)[ ,!]+)?(?:another(?: one)?|one more"
                      r"(?: please)?|again|more please|next(?: one)?|give me another(?: one)?|tell me another(?: one)?|"
                      r"do another(?: one)?|more)(?: please)?$")
_GENERAL_MOODS = frozenset(("angry", "sad", "tired", "stress", "anxious", "happy", "excited", "calm", "lonely",
                            "conflict"))
_PLAN = re.compile(r"\b(?:i'm|i am|im|we're|we are) (?:thinking (?:about|of)|planning (?:to|on)|considering|hoping to|"
                   r"dreaming (?:of|about)|trying to decide whether to)\b|\b(?:i|we) (?:want|would like|'d like|wanna|might|"
                   r"may|plan|intend|hope) to (?:move|go|travel|visit|start|learn|buy|quit|try|become|study|switch|get)\b")
_WORK_IN = re.compile(r"^(?P<lead>i (?:work|am working|'m working|have worked|worked) in) (?P<f>(?:the )?[a-z][a-z &/-]{2,40}?)"
                      r"(?P<tail>[.!]?)$", re.I)


def _job_field(text: str) -> str:
    """"I work in private equity." → "I work in private equity. My job is in private equity." —
    a field of work (lower case), so "What do I do for a living?" finds it; "I work in Berlin"
    (a name) stays a place."""
    m = _WORK_IN.match(text.strip())
    if not m or re.match(r"^(?:a|an|this|that|my|our|his|her|their)\b", m.group("f"), re.I):
        return text
    field = m.group("f").strip()
    if re.search(r"\b(?:office|building|city|town|village|shop|store|factory|warehouse|hospital|school|bank|restaurant|"
                 r"cafe|café|lab|laboratory)s?$", field):
        return text
    body = text.strip().rstrip(".!")
    return f"{body}. My job is in {field}."


_DE_COMPARE = [(r"^(.+?) vs (.+?):", r"\1 im Vergleich mit \2:"), (r"• Population:", "• Einwohner:"),
               (r"• Area:", "• Fläche:"), (r"• Capital:", "• Hauptstadt:"), (r"• Official language:", "• Amtssprache:"),
               (r"• Currency:", "• Währung:"), (r"• Elevation:", "• Höhe:"), (r"• Born:", "• Geboren:"),
               (r"• Died:", "• Gestorben:"), (r"• Nationality:", "• Nationalität:"), (r"• Occupation:", "• Beruf:"),
               (r"• Known for:", "• Bekannt für:"), (r"• Founded:", "• Gegründet:"), (r"• Headquarters:", "• Sitz:"),
               (r"• Industry:", "• Branche:"), (r"• Employees:", "• Mitarbeiter:"), (r"• Height:", "• Höhe:"),
               (r"(\S.*?) has more people\.", r"\1 hat mehr Einwohner."),
               (r"(\S.*?) has the larger area\.", r"\1 hat die größere Fläche."),
               (r"^(.+?) is bigger by area: (.+?), compared with (.+?) for (.+?)\.$", r"\1 ist flächenmäßig größer: \2, im Vergleich zu \3 bei \4."),
               (r"^(.+?) is more populous: (.+?), compared with (.+?) for (.+?)\.$", r"\1 hat mehr Einwohner: \2, im Vergleich zu \3 bei \4."),
               (r"^(.+?) is (higher|taller): (.+?), compared with (.+?) for (.+?)\.$", r"\1 ist höher: \3, im Vergleich zu \4 bei \5."),
               (r"^(.+?) is longer: (.+?), compared with (.+?) for (.+?)\.$", r"\1 ist länger: \2, im Vergleich zu \3 bei \4."),
               (r"^(.+?) is older: (.+?) was born (.+?), (.+?) (.+?)\.$", r"\1 ist älter: \2 wurde \3 geboren, \4 \5."),
               (r"^(.+?) is younger: (.+?) was born (.+?), (.+?) (.+?)\.$", r"\1 ist jünger: \2 wurde \3 geboren, \4 \5."),
               (r" million", " Millionen"),
               (r"\bFrench\b", "Französisch"), (r"\bGerman\b", "Deutsch"), (r"\bEnglish\b", "Englisch"),
               (r"\bItalian\b", "Italienisch"), (r"\bSpanish\b", "Spanisch"), (r"\bDutch\b", "Niederländisch"),
               (r"\bPortuguese\b", "Portugiesisch"), (r"\bPolish\b", "Polnisch"), (r"\bRussian\b", "Russisch"),
               (r"\bJapanese\b", "Japanisch"), (r"\bChinese\b", "Chinesisch"), (r"\bSwedish\b", "Schwedisch"),
               (r"\bPound sterling\b", "Pfund Sterling"), (r"\bSwiss franc\b", "Schweizer Franken"),
               (r"\bUnited States dollar\b", "US-Dollar"), (r"\bJapanese yen\b", "Japanischer Yen")]


def _de_compare(text: str, said: str = "") -> str:
    """An English comparison in German, with the user's own place names ("France" → "Frankreich")."""
    from engramm.chat.german_bridge import EXONYMS, de_value
    out = []
    for line in text.split("\n"):
        for pat, rep in _DE_COMPARE:
            line = re.sub(pat, rep, line)
        line = de_value(line) if line.startswith("•") or " ist " in line or " hat " in line else line
        out.append(re.sub(r"\b(\d+)\.(\d) Millionen", r"\1,\2 Millionen", line))   # 68.6 → 68,6
    text = "\n".join(out)
    for de_name, en_name in EXONYMS.items():
        if re.search(rf"\b{re.escape(de_name)}\b", said):
            text = re.sub(rf"\b{re.escape(en_name)}\b", de_name[:1].upper() + de_name[1:], text)
    return text


def _de_advice_hint(s: str) -> str:
    """English keywords for the advice groups ("mein Chef nervt" → "boss")."""
    pairs = [("chef", "boss"), ("kolleg", "colleague"), ("arbeit", "work"), ("freundin", "girlfriend"),
             ("freund", "friend"), ("mutter", "mom"), ("vater", "dad"), ("eltern", "parents"), ("schluss gemacht", "broke up"),
             ("verlassen", "left me"), ("gestorben", "died"), ("prüfung", "failed"), ("durchgefallen", "failed"),
             ("stress", "stressed"), ("müde", "tired"), ("erschöpft", "tired"), ("traurig", "sad"), ("kündigen", "quit")]
    return " ".join(e for d, e in pairs if d in s)


def _join_values(values: list[str]) -> str:
    values = list(dict.fromkeys(values))
    if len(values) <= 2:
        return " and ".join(values)
    return ", ".join(values[:-1]) + " and " + values[-1]


def _join(intro: str, text: str) -> str:
    intro = intro.strip()
    return f"{intro} {text}" if intro else text


_POS = frozenset("nice great good beautiful lovely awesome amazing fun delicious perfect wonderful excellent cool "
                 "sunny gorgeous fantastic brilliant interesting exciting tasty cute pretty sweet happy".split())
_NEG = frozenset("bad terrible awful horrible boring sad ugly rainy annoying stupid broken disgusting gross "
                 "cold freezing hot miserable dreadful worse worst difficult hard expensive".split())


def _valence(norm: str) -> str | None:
    ws = set(norm.split())
    neg = bool(ws & {"not", "isn't", "wasn't", "aren't", "don't", "doesn't", "never"})
    p, n = len(ws & _POS), len(ws & _NEG)
    if p > n:
        return "negative" if neg else "positive"
    if n > p:
        return "positive" if neg else "negative"
    return None


def _order(n: int, key: str) -> list[int]:
    return sorted(range(n), key=lambda i: hashlib.shake_256(f"{key}|{i}".encode()).digest(8))


def _rand(key: str, n: int) -> int:
    return int.from_bytes(hashlib.shake_256(key.encode()).digest(8), "little") % max(n, 1)


def _compose(parts: list[_Part]) -> str:
    order = {"prefix": 0, "main": 1, "learn": 2, "follow": 3}
    seen, out = set(), []
    for p in sorted(parts, key=lambda p: order.get(p.role, 1)):
        t = p.text.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    text = ""
    for t in out:
        sep = "\n\n" if ("\n" in t or "\n" in text) and text else " "
        text = f"{text}{sep}{t}" if text else t
    return text


def _fact_rank(f) -> tuple:
    order = {lab: i for i, (lab, _) in enumerate(_CATEGORY_KEYS)}
    best = min((order[lab] for lab in f.relation if lab in order), default=len(order))
    return (0 if f.subject == USER else 1, best, f.object)


def _atype(q: str) -> str | None:
    from engramm.chat.question import analyse
    try:
        return analyse(q).atype
    except Exception:            # the realiser works without a type
        return None


def _asked_category(q: str) -> str | None:
    """The category of a question about you ("What's my name?" → #name); None for owned things
    ("my dog's name") and anything else."""
    low = q.lower().replace("’", "'")
    if re.search(r"\bmy (?!name\b)[a-z]+(?:'s)? name\b|\bis my [a-z]+ called\b", low):
        return None
    if re.search(r"\bname\b|\bcalled\b|\bcall me\b", low):
        return "#name"
    if re.search(r"\bwhere (?:do|did) i work\b|\bemployer\b|\bcompany\b|\bfirm\b|\bwork for\b", low):
        return "#employer"
    if re.search(r"\b(?:live|home|city|town|reside)\b", low):
        return "#home"
    if re.search(r"\b(?:job|work|profession|occupation|do for a living)\b", low):
        return "#job"
    if re.search(r"\bfood\b|\beat\b|\bdish\b", low):
        return "#food"
    if re.search(r"\bcolou?r\b", low):
        return "#colour"
    if re.search(r"\bcar\b|\bdrive\b", low):
        return "#car"
    if re.search(r"\bbirthday\b|\bborn\b|\bbirth\b", low):
        return "#birth"
    if re.search(r"\bwhere am i from\b|\bwhere do i come from\b|\borigin\b", low):
        return "#origin"
    return None


def _user_answer_text(answer: str, evidence: str | None) -> str:
    if evidence:
        flipped = to_second_person(evidence)
        if flipped and answer and answer.lower() in flipped.lower():
            return flipped
        return f"{answer} — you told me: “{evidence}”"
    return f"{answer}."


_SLOT_STRIP = re.compile(r"^(?:(?:well|so|oh|ok|okay|sure|yes|yeah|um+|uh+|hmm+)[,!.]?\s+)*"
                         r"(?:it's|it is|that's|that is|i'm|i am|my name is|my name's|the name's|the name is|"
                         r"call me|you can call me|just call me|i live in|i'm from|i am from|in|i work as|i'm a|i am a|"
                         r"i am an|i'm an|i like|i love|i enjoy|my favou?rite (?:food|colou?r) is|i have)\s+", re.I)


_NOT_A_NAME = re.compile(r"\b(?:not|doing|feeling|feel|good|great|fine|ok|okay|alright|bad|sad|tired|happy|so|very|"
                         r"really|well|busy|bored|sick|ill|stressed|excited|thanks|thank|hungry|here|back|sure|sorry|"
                         r"just|kinda|pretty|awful|terrible|meh|exhausted|upset|angry|lonely|nervous|was|is|are|am|"
                         r"his|her|their|its|my|your|the|a|an)\b", re.I)


def _slot_value(msg: str, slot: str | None) -> str | None:
    s = msg.strip().strip(".!?").strip()
    s = _SLOT_STRIP.sub("", s).strip(" ,.!")
    if not s:
        return None
    words = s.split()
    if slot == "name":
        if len(words) > 3 or not all(re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+", w) for w in words):
            return None
        if normalise(s) in ("no", "nope", "not telling", "nothing", "none", "secret", "why"):
            return None
        if _NOT_A_NAME.search(s):
            return None                                   # "I'm not doing great" answers how, not who
        return s
    if slot == "mood":
        return None
    if len(words) > 8:
        return None
    return s


class ConversationBot:
    """The ``ChatBot`` interface on top of the assistant, so the registered dialog and fact
    evaluations (experiments/chat_v2_tasks.py) can run through the conversation layer: ``turn``
    goes through ``Assistant.turn``; assigning ``context`` (their reset) starts a new
    conversation; everything else is the core bot's."""

    def __init__(self, bot, conversation: str = "eval", clock=None):
        object.__setattr__(self, "core", bot)
        object.__setattr__(self, "assistant", Assistant(bot, clock=clock))
        object.__setattr__(self, "state", DialogState(conversation=conversation))
        object.__setattr__(self, "_conversation", conversation)

    def turn(self, message: str) -> Reply:
        return self.assistant.turn(self.state, message)

    @property
    def context(self) -> dict:
        return self.state.ctx

    @context.setter
    def context(self, value: dict) -> None:
        object.__setattr__(self, "state", DialogState(conversation=self._conversation, ctx=dict(value)))

    def __getattr__(self, name):
        return getattr(self.core, name)

    def __setattr__(self, name, value):
        if name == "context":
            object.__setattr__(self, "state", DialogState(conversation=self._conversation, ctx=dict(value)))
        else:
            setattr(self.core, name, value)
