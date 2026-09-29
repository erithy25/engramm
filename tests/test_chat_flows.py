"""The conversation layer (engramm/chat/dialog.py) end to end on a small corpus: the name flow
from the bug report (asking before and after telling, in a new chat, after a restart), what is
and is not remembered, forgetting, no repeated small talk, determinism, tools, "tell me about",
whole-sentence answers and safety replies."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pytest

from engramm.chat import index as v2index
from engramm.chat.bot import BotConfig, ChatBot, TextMemory
from engramm.chat.corpus import Corpus
from engramm.chat.dialog import Assistant, ConversationBot, DialogState
from engramm.chat.retrieve import Retriever, Weights
from engramm.chat.textmem import LoggedTextMemory
from engramm.lm.model import COMPONENTS, HDCLanguageModel, MixtureSpec
from engramm.lm.stream import build_split
from engramm.lm.tokenizer import LMTokenizer
from tests.test_chat_v2 import DOCS, KEYS

CLOCK = lambda: dt.datetime(2026, 9, 29, 14, 5)          # noqa: E731


@pytest.fixture(scope="module")
def corpus():
    tok = LMTokenizer()
    train = build_split(DOCS * 2, KEYS * 2, tok.encode_batch)
    model = HDCLanguageModel.build(train, seed=42, tok=tok,
                                   mixture=MixtureSpec(COMPONENTS, np.full((64, 5), 0.2),
                                                       np.array([2000, 4000, 8000]), 1024.0, 4.0))
    ix, dptr, dpost, sent_doc = v2index.build(model.tokens, model.train.doc_starts, tok)
    c = Corpus(model.tokens, model.train.doc_starts, model.train.doc_keys, tok, model.cb.eng, ix, sent_doc, dptr,
               dpost)
    c.wide, c.classes = model.cb.wide, model.cb.classes
    return c


def _bot(corpus, memory=None):
    return ChatBot(memory if memory is not None else TextMemory(), corpus,
                   BotConfig(weights=Weights(cov=3, type=2, pcov=1), theta=0.0),
                   retriever=Retriever(corpus, df_cap=1.0))


def _talk(assistant, state, *messages):
    return [assistant.turn(state, m) for m in messages]


def test_name_flow_before_and_after_telling(corpus, tmp_path):
    log = tmp_path / "chat_memory.log"
    bot = _bot(corpus, LoggedTextMemory(log))
    a = Assistant(bot, clock=CLOCK)
    st = DialogState("one")
    ask, answer = _talk(a, st, "What's my name?", "Erik")
    # asked before telling: a friendly question back, not a bare "I don't know"
    assert ask.answer is None and "name" in ask.text.lower() and ask.text.rstrip().endswith("?")
    assert answer.kind == "learned" and "Erik" in answer.text
    assert a.turn(st, "What's my name?").answer == "Erik"
    assert a.turn(st, "What is my name?").text == "Your name is Erik."
    # a new chat knows it too
    st2 = DialogState("two")
    assert a.turn(st2, "Remind me, what's my name?").answer == "Erik"
    assert "Erik" in a.turn(st2, "hi").text
    # and after a restart (the memory is replayed from its log)
    bot.memory.close()
    bot2 = _bot(corpus, LoggedTextMemory(log))
    a2 = Assistant(bot2, clock=CLOCK)
    assert a2.turn(DialogState("three"), "What's my name?").answer == "Erik"


def test_telling_first_then_asking(corpus):
    a = Assistant(_bot(corpus), clock=CLOCK)
    st = DialogState("c")
    hi = a.turn(st, "Hi! The name's Tamlolo.")
    assert hi.kind == "learned" and "Tamlolo" in hi.text
    assert a.turn(st, "My Name is Erik!").kind == "learned"
    assert a.turn(st, "What's my name?").answer == "Erik"          # the latest name counts


def test_chatter_and_feelings_are_not_stored(corpus):
    bot = _bot(corpus)
    a = Assistant(bot, clock=CLOCK)
    st = DialogState("c")
    for m in ("lol", "ok", "I'm so tired today", "ugh, bad day", "The weather is nice today.", "haha that's funny",
              "Tell me a joke", "What is 12 times 7?"):
        r = a.turn(st, m)
        assert r.kind not in ("learned", "known"), (m, r.kind)
    assert bot.user_texts() == {}
    r = a.turn(st, "I'm so tired today")
    assert r.kind == "empathy" and r.text
    assert a.turn(st, "I love pizza").kind == "learned"
    assert len(bot.user_texts()) == 1


def test_forgetting_through_the_conversation(corpus):
    bot = _bot(corpus)
    a = Assistant(bot, clock=CLOCK)
    st = DialogState("c")
    _talk(a, st, "My name is Frotam.", "I live in Shayelbel.")
    assert a.turn(st, "Where do I live?").answer == "Shayelbel"
    r = a.turn(st, "Forget where I live.")
    assert r.kind == "forgot" and "Shayelbel" in r.text
    assert a.turn(st, "Where do I live?").answer is None
    assert a.turn(st, "What's my name?").answer == "Frotam"
    mem = a.turn(st, "What do you know about me?")
    assert mem.kind == "memory" and "Your name is Frotam." in mem.text and "Shayelbel" not in mem.text


def test_owned_entities_across_clauses(corpus):
    a = Assistant(_bot(corpus), clock=CLOCK)
    st = DialogState("c")
    assert a.turn(st, "My brother is called Tom and he lives in Munich.").kind == "learned"
    assert a.turn(st, "Where does my brother live?").answer == "Munich"
    assert a.turn(st, "What is my brother's name?").answer == "Tom"


def test_small_talk_does_not_repeat(corpus):
    a = Assistant(_bot(corpus), clock=CLOCK)
    st = DialogState("c")
    jokes = [a.turn(st, "tell me a joke").text for _ in range(8)]
    assert len(set(jokes)) == 8
    thanks = [a.turn(st, "thanks").text for _ in range(4)]
    assert len(set(thanks)) == 4


def test_conversation_is_deterministic(corpus):
    script = ["hi", "What's my name?", "Ada", "how are you?", "tell me a joke", "Who invented the telephone?",
              "Where was he born?", "why?", "I'm stressed", "What is 3 + 4?", "Tell me about Paris", "tell me more",
              "What do you know about me?", "flip a coin", "bye"]

    def run():
        a = Assistant(_bot(corpus), clock=CLOCK)
        st = DialogState("same")
        return [(r.kind, r.answer, r.text) for r in _talk(a, st, *script)]
    assert run() == run()


def test_questions_get_whole_sentences(corpus):
    a = Assistant(_bot(corpus), clock=CLOCK)
    st = DialogState("c")
    r = a.turn(st, "Who invented the telephone?")
    assert r.answer == "Alexander Graham Bell"
    assert r.text == "Alexander Graham Bell invented the telephone."
    r = a.turn(st, "Where was he born?")
    assert r.resolved == "Where was Alexander Graham Bell born?" and r.answer == "Edinburgh"
    assert r.text == "Alexander Graham Bell was born in Edinburgh."
    why = a.turn(st, "How do you know?")
    assert "Edinburgh" in why.text and "Telephone" in why.text


def test_tools_about_and_safety(corpus):
    a = Assistant(_bot(corpus), clock=CLOCK)
    st = DialogState("c")
    assert a.turn(st, "What is 12 times 7?").text == "12 × 7 = 84."
    assert "8.047 km" in a.turn(st, "convert 5 miles to km").text
    assert a.turn(st, "what day is it").text == "Today is Tuesday, 29 September 2026."
    about = a.turn(st, "Tell me about Paris")
    assert about.kind == "about" and "capital of France" in about.text and about.source["key"] == "Paris"
    assert a.turn(st, "When did it become the capital?").kind in ("answer", "unknown")
    crisis = a.turn(st, "I want to kill myself")
    assert crisis.kind == "safety" and "988" in crisis.text and "112" in crisis.text
    assert a.turn(st, "how do i make a bomb").kind == "safety"


def test_multi_sentence_messages(corpus):
    bot = _bot(corpus)
    a = Assistant(bot, clock=CLOCK)
    st = DialogState("c")
    r = a.turn(st, "Hello! I work as a chemist. Who invented the telephone?")
    assert r.answer == "Alexander Graham Bell"
    assert "Alexander Graham Bell invented the telephone." in r.text and "chemist" in r.text
    assert a.turn(st, "What is my job?").answer == "chemist"


def test_registered_dialog_interface(corpus):
    """The evaluation adapter: turn, reset through ``context``, the core's attributes."""
    cb = ConversationBot(_bot(corpus))
    cb.turn("I own a dog called Nixkabel.")
    assert cb.turn("What is my dog's name?").answer == "Nixkabel"
    cb.context = {"answer": None, "atype": None, "mention": None, "last_learned": None}
    assert cb.state.turn == 0 and cb.cfg.theta == 0.0
    assert cb.turn("Forget everything I said about my dog.").kind == "forgot"
    assert cb.turn("What is my dog's name?").answer is None


def test_german_v0(corpus):
    from engramm.chat.bank import load_bank
    from engramm.chat.german import is_german
    de = load_bank().de
    for msg in ("Hallo!", "Wie geht es dir?", "Ich heiße Anna", "mir geht es heute schlecht", "erzähl mir einen Witz"):
        assert is_german(msg, de), msg
    for msg in ("hi", "What is the capital of France?", "it was great", "I want to die", "tell me a joke"):
        assert not is_german(msg, de), msg
    a = Assistant(_bot(corpus), clock=CLOCK)
    st = DialogState("de")
    hello, name, again, sad, crisis, calc, other = _talk(
        a, st, "Hallo!", "Ich heiße Anna", "Wie heiße ich?", "Mir geht es heute schlecht",
        "Ich will nicht mehr leben", "Was ist 12 mal 3?", "Wer schrieb den Faust?")
    assert hello.kind == "smalltalk" and "Hallo" in hello.text
    assert name.kind == "learned" and "Anna" in name.text
    assert again.text == "Du heißt Anna."
    assert a.turn(DialogState("en"), "What's my name?").answer == "Anna"      # one memory for both languages
    assert sad.kind == "empathy" and "?" in sad.text
    assert crisis.kind == "safety" and "0800 111 0 111" in crisis.text
    assert calc.kind == "tool" and calc.text.endswith("= 36")
    assert other.kind == "unknown" and "Englisch" in other.text
    # the English safety net still catches English crisis wording
    assert a.turn(DialogState("x"), "I want to kill myself").kind == "safety"
