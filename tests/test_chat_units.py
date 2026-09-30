"""Units of the conversation layer: tools, the sentence realiser, the act router, the
conversation bank (authored YAML = compiled JSON, no routing conflicts) and the text memory log."""

from __future__ import annotations

import re

import datetime as dt
import json

import pytest

from engramm.chat.acts import about_request, classify, split_sentences
from engramm.chat.bank import choose, load_bank, normalise
from engramm.chat.realize import answer_sentence, past_tense, personal_sentence, third_person, to_second_person
from engramm.chat.textmem import LoggedTextMemory
from engramm.chat.tools import calculate, convert, date_answer, tool_answer

NOW = dt.datetime(2026, 9, 29, 14, 5)


@pytest.mark.parametrize("msg,want", [
    ("What is 2+2?", "2+2 = 4"), ("what's 12 times 7", "12 × 7 = 84"), ("calculate (3+4)*5", "(3+4)×5 = 35"),
    ("15% of 80", "15% of 80 is 12."), ("what is the square root of 144", "√(144) = 12"),
    ("what is five times three", "5 × 3 = 15"), ("10/0", "Hmm — you can't divide by zero."),
    ("what is 10 mod 3", "10 % 3 = 1"), ("what is 2 to the power of 1000", "Hmm — that number is too large."),
])
def test_calculator(msg, want):
    assert calculate(msg).text == want


@pytest.mark.parametrize("msg", ["What is the capital of France?", "I have 2 cats and 3 dogs", "50%", "1990",
                                 "What happened in 1990?", "__import__('os')", "2**2**2**2**2"])
def test_calculator_ignores_non_arithmetic(msg):
    r = calculate(msg)
    assert r is None or r.text.startswith("Hmm")


@pytest.mark.parametrize("msg,want", [
    ("convert 5 miles to km", "5 miles = 8.047 km"), ("how many cm in an inch", "1 inch = 2.54 cm"),
    ("100 F in C", "100 °F = 37.78 °C"), ("what is 30 celsius in fahrenheit", "30 °C = 86 °F"),
    ("how many feet are in a mile", "1 mile = 5,280 feet"), ("1 GB in MB", "1 GB = 1,000 MB"),
    ("2,5 km in m", "2.5 km = 2,500 m"), ("5 kg in km", "I can't convert kg into km — one is a mass, the other a length."),
])
def test_units(msg, want):
    assert convert(msg).text == want


@pytest.mark.parametrize("msg,want", [
    ("what time is it", "It's 14:05 (on this computer's clock)."),
    ("what's the date today", "Today is Tuesday, 29 September 2026."),
    ("what day is 24 December 2026", "24 December 2026 is a Thursday."),
    ("how many days until christmas", "87 days until Friday, 25 December 2026 — about 12.4 weeks."),
    ("what year is it", "It's 2026."),
])
def test_dates(msg, want):
    assert date_answer(msg, NOW).text == want
    assert tool_answer(msg, NOW).text == want


@pytest.mark.parametrize("q,a,t,want", [
    ("Who invented the telephone?", "Alexander Graham Bell", "PERSON", "Alexander Graham Bell invented the telephone."),
    ("Where was Alexander Graham Bell born?", "Edinburgh", "LOCATION", "Alexander Graham Bell was born in Edinburgh."),
    ("When was Alexander Graham Bell born?", "March 3, 1847", "DATE", "Alexander Graham Bell was born on March 3, 1847."),
    ("What is the capital of France?", "Paris", "LOCATION", "Paris is the capital of France."),
    ("By whom was Nouldaeldun founded?", "Draexgioxruth", "PERSON", "Nouldaeldun was founded by Draexgioxruth."),
    ("When did Berlin become the capital?", "1990", "DATE", "Berlin became the capital in 1990."),
    ("Which river flows through Paris?", "the Seine", "LOCATION", "The Seine flows through Paris."),
    ("How many inhabitants does Paris have?", "2,100,000", "NUMBER", "Paris has 2,100,000 inhabitants."),
    ("Who was Hamlet written by?", "William Shakespeare", "PERSON", "Hamlet was written by William Shakespeare."),
    ("When did World War II end?", "1945", "DATE", "World War II ended in 1945."),
    ("What year did the Titanic sink?", "1912", "DATE", "The Titanic sank in 1912."),
    ("When was the West Bank annexed by Jordan?", "1950", "DATE", "The West Bank was annexed by Jordan in 1950."),
    ("What was the Manhattan Project?", "a research programme", "OTHER", "The Manhattan Project was a research programme."),
    ("Who sings about the joy of living?", "Luddi, Bhangra and Sammi", "PERSON",
     "Luddi, Bhangra and Sammi sing about the joy of living."),
])
def test_answer_sentences(q, a, t, want):
    assert answer_sentence(q, a, t) == want


@pytest.mark.parametrize("q,a", [("Why is the sky blue?", "Rayleigh scattering"),
                                 ("What is it called when organisms are lethal to their host?", "necrotrophic"),
                                 ("How old was Mozart when he died?", "35")])
def test_realiser_declines_when_unsure(q, a):
    assert answer_sentence(q, a, None) is None


def test_verb_forms_and_person():
    assert [past_tense(v) for v in ("invent", "write", "stop", "carry", "found", "die")] == \
        ["invented", "wrote", "stopped", "carried", "founded", "died"]
    assert [third_person(v) for v in ("live", "have", "watch", "fly", "go")] == ["lives", "has", "watches", "flies",
                                                                                 "goes"]
    assert to_second_person("My Name is Erik!") == "Your Name is Erik."
    assert to_second_person("I was born in Hamburg.") == "You were born in Hamburg."
    assert to_second_person("I think you are nice.") is None
    assert personal_sentence("USER", ("#job", "work"), "chemist", "I work as a chemist.") == "You work as a chemist."
    assert personal_sentence("USER:dog", ("#name",), "Rex", "I own a dog called Rex.") == "Your dog is called Rex."


def test_sentences_and_routing():
    assert split_sentences("Hi! The name's Tamlolo.") == ["Hi", "The name's Tamlolo."]
    assert split_sentences("Hi, my name is Ada") == ["Hi", "my name is Ada"]
    assert split_sentences("Mr. Smith met Dr. Jones in St. Louis. He left.") == \
        ["Mr. Smith met Dr. Jones in St. Louis.", "He left."]
    assert split_sentences("i live in berlin. i work as a nurse") == ["i live in berlin.", "i work as a nurse"]
    bank = load_bank()
    route = lambda m: [(u.act, u.intent) for u in classify(m, bank, NOW)]    # noqa: E731
    assert route("hey how r ya") == [("intent", "how_are_you")]
    assert route("Hi! The name's Tamlolo.") == [("intent", "greeting"), ("statement", None)]
    assert route("What's my name?") == [("question", None)]
    assert route("what's your name") == [("intent", "bot_name")]
    assert route("I'm so tired today") == [("feeling", None)]
    assert route("Tell me about black holes") == [("about", None)]
    assert route("What is the capital of France?") == [("question", None)]
    assert route("What is 12 times 7?") == [("tool", None)]
    assert route("Forget my dog.") == [("forget", None)]
    assert route("Remember that my sister is called Anna.") == [("remember", None)]
    assert route("I want to kill myself") == [("safety", None)]
    assert about_request("What is photosynthesis?") == ("what", "photosynthesis")
    assert about_request("Who was Albert Einstein?") == ("what", "Albert Einstein")
    assert about_request("What is the tallest mountain?") is None
    assert normalise("  Thanks, ENGRAMM!!  ") == "thanks"


def test_bank_is_built_from_the_yaml_and_has_no_conflicts(tmp_path):
    pytest.importorskip("yaml")
    from engramm.chat.bank import BANK_PATH
    from engramm.chat.studio import build, check, load_sources
    errors, _ = check(load_sources())
    assert errors == []
    out = build(tmp_path / "bank.json")
    assert json.loads(out.read_text()) == json.loads(BANK_PATH.read_text()), \
        "conv_bank.json is out of date: run python -m engramm.chat.studio build"


def test_choose_is_deterministic_and_avoids_recent():
    opts = ["a", "b", "c"]
    assert choose(opts, "k", []) == choose(opts, "k", [])
    first = choose(opts, "k", [])
    assert choose(opts, "k", [first]) != first


def test_text_memory_log(tmp_path):
    from engramm.lm.log import LMEventLog
    old = tmp_path / "user.log"
    lg = LMEventLog(old)
    lg._append(bytes([ord("H")]) + b'{"base": "x"}')
    lg.learn_text("chat:1", "My name is Ada.")
    lg.learn_text("chat:2", "I live in Paris.")
    lg.forget("chat:2")
    lg.close()
    path = tmp_path / "chat_memory.log"
    m = LoggedTextMemory(path, import_from=old)
    assert m.user_texts == {"chat:1": "My name is Ada."}
    m.learn_text("I like tea.", "chat:3")
    m.forget("chat:1")
    digest = m.state_digest()
    m.close()
    again = LoggedTextMemory(path, import_from=old)          # replayed, not imported twice
    assert again.user_texts == {"chat:3": "I like tea."} and again.state_digest() == digest
    with pytest.raises(ValueError):
        again.learn_text("I like tea.", "chat:3")
    again.close()
    # a torn tail (crash while writing) is discarded
    with open(path, "ab") as f:
        f.write(b"\x00\x00\x00\x40garbage")
    assert LoggedTextMemory(path).user_texts == {"chat:3": "I like tea."}


def test_persona_is_consistent():
    """Paraphrases of a question about ENGRAMM itself reach the same intent (no contradictions)."""
    from engramm.chat.acts import classify
    from engramm.chat.bank import load_bank
    b = load_bank()
    groups = {"bot_fav_color": ["what's your favourite colour?", "what is your favorite color", "which colour do you like best?"],
              "bot_age": ["how old are you?", "what's your age?", "when were you made?"],
              "bot_location": ["where do you live?", "where are you from?", "where are you?"],
              "bot_name": ["what's your name?", "who are you?", "what are you called?"],
              "bot_creator": ["who made you?", "who created you?", "who built you?"],
              "bot_neural": ["do you use a neural network?", "are you a neural network?"]}
    for intent, questions in groups.items():
        for q in questions:
            u = classify(q, b)[0]
            assert (u.act, u.intent) == ("intent", intent), (q, u.act, u.intent)
    for it in b.intents:                       # no variant claims a body, a family or feelings
        for r in it.responses:
            assert not re.search(r"\bmy (?:mother|father|wife|husband|body)\b|\bI (?:ate|slept|was born in 19)", r), (it.id, r)
