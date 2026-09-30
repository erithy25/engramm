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
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from engramm.chat.about import About, AboutFinder
from engramm.chat.acts import Unit, classify
from engramm.chat.bank import Bank, choose, load_bank, normalise
from engramm.chat.bot import CHAT_PREFIX, Reply, source_id
from engramm.chat.facts import USER, facts_from_text
from engramm.chat.german import is_german, understand
from engramm.chat.realize import answer_sentence, article, personal_sentence, to_second_person

FRESH_CTX = {"answer": None, "atype": None, "mention": None, "last_learned": None}
RECENT = 12                                  # replies remembered to avoid repeats
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

    # -- helpers ------------------------------------------------------------------------------

    def _pick(self, st: DialogState, key: str, options: list[str], **fmt) -> str:
        n = st.uses.get(key, 0)
        st.uses[key] = n + 1
        text = choose(options, f"{st.conversation}|{key}|{n}", st.recent)
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
        """A German message (engramm/chat/german.py): chat, feelings, crises, memory; knowledge
        questions get an honest pointer to English."""
        de = self.bank.de
        u = understand(msg, de)
        name = self.user_name()
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
            opts = it.get("responses_named") if name and it.get("responses_named") else it["responses"]
            return Reply(msg, "smalltalk", self._pick(st, f"de:{it['id']}", opts, name=name or ""), via="german")
        if u.kind == "feeling":
            fe = de["feelings"]
            if u.data["negated"]:
                opts = fe["negated_negative"] if u.data["valence"] == "negative" else fe["negated_positive"]
            else:
                opts = next(c for c in fe["categories"] if c["id"] == u.data["id"])["responses"]
            return Reply(msg, "empathy", self._pick(st, f"de:feeling:{u.data['id']}", opts), via="german")
        return Reply(msg, "unknown", self._pick(st, "de:fallback", de["replies"]["fallback"]), via="german")

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
        st.turn += 1
        st.last_reply = rep.text
        st.recent = (st.recent + [rep.text])[-RECENT:]
        return rep

    def _turn(self, st: DialogState, msg: str) -> Reply:
        if not msg:
            return Reply(msg, "nothing", "Please type something.")
        de = self.bank.de
        if de and is_german(msg, de) and self.bank.safety_rule(normalise(msg, fillers=False)) is None:
            return self._german(st, msg)
        units = classify(msg, self.bank, self._now())
        if self.speller is not None and all(u.act in ("question", "about") for u in units):
            fixed = self.speller.fix(msg)       # typos and CAPITALS, only in questions (names stay as told)
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
            if hit is not None:
                return Reply(msg, "unknown", self._reply(st, f"device.{hit[0]}"), via="device")
        parts: list[_Part] = []
        main: Reply | None = None
        learn: list[Unit] = []
        content = any(u.act not in ("intent", "empty") or (u.intent and self._is_content_intent(u.intent))
                      for u in units)
        for u in units:
            if u.act == "intent":
                r = self._intent(st, u, content, parts)
                if r is not None and main is None:
                    main = r
            elif u.act == "statement":
                if self._worth_learning(u.text):
                    learn.append(u)
                else:
                    self._chitchat(st, u, parts, alone=len(units) == 1)
            elif u.act == "feeling":
                parts.append(_Part("prefix", self._feeling(st, u)))
                if self._feeling_has_fact(u.text):
                    learn.append(u)
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
            if st.last_reply:
                return Reply(u.text, "smalltalk", self._reply(st, "clarify.last", last=st.last_reply), via="smalltalk")
            return Reply(u.text, "smalltalk", self._reply(st, "clarify.none"), via="smalltalk")
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
            return Reply(u.text, "tool", tr.text if tr.text.endswith((".", "!", "?")) else tr.text + ".",
                         answer=tr.value, via="tool", confidence=1.0)
        if u.act == "about":
            return self._about(st, u)
        if u.act == "question":
            return self._question(st, u.text)
        return Reply(u.text, "nothing", self._reply(st, "fallback"))

    def _question(self, st: DialogState, text: str) -> Reply:
        bot = self.bot
        kb = self._kb_answer(st, text)
        if kb is not None:
            return kb
        rep = bot._answer(" ".join(text.split()))
        q = rep.resolved or text
        if rep.kind == "answer" and rep.via in ("facts", "memory") and rep.source and rep.source.get("kind") == "user":
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
            rep.text = self._reply(st, "answer.unknown_named", x=missing)
        elif rep.guess and (rep.source or {}).get("key"):
            # unsure guesses were right only 7 of 25 times on the team prompts: say so and name the
            # closest source instead of offering the guess (the guess stays in the reply for evals)
            rep.text = self._reply(st, "answer.unknown_near", x=rep.source["key"])
        else:
            rep.text = self._reply(st, "answer.unknown")
        st.last_fact = ({"evidence": rep.evidence, "source": rep.source, "answer": rep.guess, "question": q,
                         "sure": False} if rep.evidence else None)
        return rep

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
        return Reply(text, "answer", ans.text, answer=value, guess=value, evidence=ans.evidence, source=src,
                     confidence=1.0, via="kb", resolved=q if q != text else None)

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
                         "end": found.end_sentence, "source": found.source}
        st.last_fact = {"evidence": found.sentences[0], "source": found.source, "answer": None, "question": None,
                        "sure": True}
        self.bot.context.update({"answer": None, "atype": None, "mention": found.title})
        return Reply(text, "about", body, evidence=found.sentences[0], source=found.source, via="about",
                     confidence=1.0)

    def _more(self, st: DialogState, text: str) -> Reply:
        la = st.last_about
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
        return Reply(text, "answer", out, evidence=lf["evidence"], source=src, via="why")

    # -- memory -------------------------------------------------------------------------------

    def _worth_learning(self, sentence: str) -> bool:
        """Remember a statement only if it carries something: a recognised fact, something about
        you, or a named thing."""
        s = sentence.strip()
        if len(s) < 3:
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

    def _feeling_has_fact(self, sentence: str) -> bool:
        from engramm.chat.facts import CATEGORIES
        for f in facts_from_text(sentence, "probe", self.bot.is_name_initial_fact, typer=self.bot.typer):
            if f.subject.startswith(USER + ":") or set(f.relation) & (CATEGORIES - {"#fav"}):
                return True
        return False

    def _learn(self, st: DialogState, sentences: list[str], msg: str) -> Reply:
        bot = self.bot
        text = resolve_statement(" ".join(s.strip() for s in sentences if s.strip()))
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
        from engramm.chat.events import find_event
        ev = find_event(text, self._today())
        if ev is not None:
            self.events.note(ev[0], ev[1], sid)
            confirm = self._reply(st, "event_noted", x=ev[0])
        return Reply(msg, "learned", confirm, source={"kind": "user", "source": sid}, via="memory")

    def _confirm(self, st: DialogState, fs: list, name_before: str | None) -> str:
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
                    out.append(self._reply(st, f"learned.{cat}", x=x))
                elif "about_you" not in used:
                    used.add("about_you")
                    out.append(self._reply(st, "learned.about_you"))
            elif f.subject.startswith(USER + ":"):
                noun = f.subject.partition(":")[2]
                if "#name" in f.relation:
                    out.append(self._reply(st, "learned.owned_name", x=f.object, noun=noun))
                elif f"owned:{noun}" not in used:
                    used.add(f"owned:{noun}")
                    out.append(self._reply(st, "learned.owned", noun=noun))
            elif "world" not in used:
                used.add("world")
                out.append(self._reply(st, "learned.world", subject=f.subject))
        if not out:
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
        slot = pending.get("slot")
        value = _slot_value(msg, slot)
        if value is None:
            return None
        if slot == "correction":
            q = pending.get("question") or ""
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
