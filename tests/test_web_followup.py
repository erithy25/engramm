"""Follow-ups to a web answer (engramm/web/followup.py, Assistant._web_followup): the user's report
(11.10.2026) — "When was Real Madrid founded?" was answered, "And, Barcelona?" got a description of
the city. The follow-up asks the same question about Barcelona, and the club is meant (the same kind
of thing as Real Madrid); "how old is he?" means the person just named; "und Österreich?" asks the
same about Austria. Wikimedia is the recorded double of tests/test_web_wiki.py."""

from __future__ import annotations

import re

import pytest

from engramm.chat.dialog import DialogState
from engramm.web.followup import rewrite
from tests.test_chat_flows import corpus  # noqa: F401  (fixture)
from tests.test_web_wiki import chat  # noqa: F401  (fixture)

RM = {"question": "When was Real Madrid founded?", "subject": "Real Madrid", "typed": "Real Madrid", "rel": "inception",
      "label": "Real Madrid CF", "qid": "Q8682", "answer": "6 March 1902", "values": [], "person": False, "place": False,
      "subject_person": False, "lang": "en"}
FR = {"question": "Who is the president of France?", "subject": "France", "typed": "France", "rel": "head_state",
      "label": "France", "qid": "Q142", "answer": "Emmanuel Macron", "values": ["Q3052772"], "person": True,
      "place": False, "subject_person": False, "lang": "en"}
KZ = {"question": "Wer ist der aktuelle Bundeskanzler?", "subject": "Deutschland", "typed": "", "rel": "head_gov",
      "label": "Deutschland", "qid": "Q183", "answer": "Friedrich Merz", "values": ["Q1173"], "person": True,
      "place": False, "subject_person": False, "lang": "de"}
CAP = {"question": "What is the capital of France?", "subject": "France", "typed": "France", "rel": "capital",
       "label": "France", "qid": "Q142", "answer": "Paris", "values": ["Q90"], "person": False, "place": True,
       "subject_person": False, "lang": "en"}
GER = {"question": "Who is the German chancellor?", "subject": "Germany", "typed": "German", "rel": "head_gov",
       "label": "Germany", "qid": "Q183", "answer": "Friedrich Merz", "values": ["Q1173"], "person": True,
       "place": False, "subject_person": False, "lang": "en"}
MUSK = {"question": "Who is Elon Musk?", "subject": "Elon Musk", "typed": "Elon Musk", "rel": "", "label": "Elon Musk",
        "qid": "Q317521", "answer": "", "values": [], "person": False, "place": False, "subject_person": True,
        "lang": "en"}


@pytest.mark.parametrize("message,last,lang,question,kind,pin", [
    ("And, Barcelona?", RM, "en", "When was Barcelona founded?", "subject", {}),
    ("Barcelona?", RM, "en", "When was Barcelona founded?", "subject", {}),
    ("Und Barcelona?", RM, "de", "When was Barcelona founded?", "subject", {}),
    ("What about Bayern?", RM, "en", "When was Bayern founded?", "subject", {}),
    ("When was it founded?", RM, "en", "When was Real Madrid founded?", "pronoun", {"Real Madrid": "Q8682"}),
    ("Who founded it?", RM, "en", "Who founded Real Madrid?", "pronoun", {"Real Madrid": "Q8682"}),
    ("How old is he?", FR, "en", "How old is Emmanuel Macron?", "pronoun", {"Emmanuel Macron": "Q3052772"}),
    ("Where was he born?", FR, "en", "Where was Emmanuel Macron born?", "pronoun", {"Emmanuel Macron": "Q3052772"}),
    ("And his wife?", FR, "en", "Who is the wife of Emmanuel Macron?", "pronoun", {"Emmanuel Macron": "Q3052772"}),
    ("And Germany?", FR, "en", "Who is the president of Germany?", "subject", {}),
    ("And the population?", FR, "en", "What is the population of France?", "relation", {"France": "Q142"}),
    ("Wie alt ist er?", KZ, "de", "Wie alt ist Friedrich Merz?", "pronoun", {"Friedrich Merz": "Q1173"}),
    ("Und Österreich?", KZ, "de", "Wer ist der aktuelle Bundeskanzler von Österreich?", "subject", {}),
    ("Und seine Frau?", KZ, "de", "Wer ist die Frau von Friedrich Merz?", "pronoun", {"Friedrich Merz": "Q1173"}),
    ("How many people live there?", CAP, "en", "How many people live in Paris?", "pronoun", {"Paris": "Q90"}),
    ("Wie viele Menschen leben dort?", CAP, "de", "Wie viele Menschen leben in Paris?", "pronoun", {"Paris": "Q90"}),
    ("And Austria?", GER, "en", "Who is the chancellor of Austria?", "subject", {}),
    ("And Jeff Bezos?", MUSK, "en", "Who is Jeff Bezos?", "subject", {}),
    ("How old is he?", MUSK, "en", "How old is Elon Musk?", "pronoun", {"Elon Musk": "Q317521"}),
])
def test_follow_ups_become_whole_questions(message, last, lang, question, kind, pin):
    fu = rewrite(message, last, lang)
    assert fu is not None and (fu.question, fu.kind, fu.pin) == (question, kind, pin), fu
    if kind == "subject":
        assert fu.like == last["qid"]               # the same kind of thing as before


@pytest.mark.parametrize("message", ["Is it raining?", "And you?", "Und?", "Und jetzt?", "Really?", "Why?", "Tell me a joke",
                                     "What is the capital of Peru?", "How about pizza?", "What time is it?",
                                     "Wie geht es dir?", "Thanks!", "and"])
def test_other_messages_are_no_follow_ups(message):
    assert rewrite(message, RM, "en") is None and rewrite(message, FR, "en") is None


def test_and_barcelona_after_real_madrid_is_the_club(chat):  # noqa: F811
    """The user's screenshot: "And, Barcelona?" right after "When was Real Madrid founded?"."""
    a, eg, web, wiki = chat
    st = DialogState("fc")
    r = a.turn(st, "google when was real madrid founded")
    assert r.text.startswith("Real Madrid was founded on 6 March 1902."), r.text
    r = a.turn(st, "And, Barcelona?")
    assert r.via == "web" and r.text.startswith("FC Barcelona was founded on 29 November 1899."), r.text
    assert r.resolved == "When was Barcelona founded?"           # shown as "I read this as …"
    assert r.source["key"] == "https://en.wikipedia.org/wiki/FC_Barcelona"
    r = a.turn(st, "Who founded it?")                              # "it": now FC Barcelona, by its item
    assert r.resolved == "Who founded FC Barcelona?" or r.resolved == "Who founded Barcelona?", r.resolved


def test_an_unanswered_follow_up_keeps_the_thing_it_picked(chat):  # noqa: F811
    """No founder for the club in the double: "who founded it?" goes unanswered, and the thing stays
    FC Barcelona's item for the next message, not the city's namesake."""
    a, eg, web, wiki = chat
    st = DialogState("keep")
    a.turn(st, "google when was real madrid founded")
    a.turn(st, "And, Barcelona?")
    assert st.uses["web_last"]["qid"] == "Q7156"
    a.turn(st, "Who founded it?")
    assert st.uses["web_last"]["qid"] == "Q7156", st.uses["web_last"]
    asked_founders = [q.url for q in wiki.seen if "property=P112" in q.url]
    assert asked_founders and all("entity=Q7156" in u for u in asked_founders), asked_founders


def test_he_is_the_person_just_named(chat):  # noqa: F811
    a, eg, web, wiki = chat
    st = DialogState("he")
    r = a.turn(st, "google who is currently the president of the usa")
    assert r.text.startswith("Donald Trump is currently the president of the USA."), r.text
    r = a.turn(st, "How old is he?")
    assert r.via == "web" and re.match(r"Donald Trump is \d+ years old \(born on 14 June 1946\)\.", r.text), r.text
    assert r.resolved == "How old is Donald Trump?"


def test_und_oesterreich_after_the_german_chancellor(chat):  # noqa: F811
    a, eg, web, wiki = chat
    st = DialogState("at")
    r = a.turn(st, "google wer ist der aktuelle bundeskanzler")
    assert "Friedrich Merz" in r.text, r.text
    r = a.turn(st, "Und Österreich?")
    assert r.via == "web" and "Christian Stocker" in r.text and "Merz" not in r.text, r.text


def test_he_is_never_a_country(chat):  # noqa: F811
    """CI: "Wie alt ist er?" after an answer that named no person became "Wie alt ist Österreich?"."""
    kz = {**KZ, "question": "Wer ist der aktuelle Bundeskanzler von Österreich?", "subject": "Österreich",
          "typed": "Österreich", "label": "Österreich", "qid": "Q40", "answer": "", "values": [], "person": False}
    assert rewrite("Wie alt ist er?", kz, "de") is None
    assert rewrite("Wie alt ist er?", {**kz, "answer": "Christian Stocker", "values": ["Q99000001"], "person": True},
                   "de").question == "Wie alt ist Christian Stocker?"


def test_a_follow_up_is_a_follow_up_for_three_messages(chat):  # noqa: F811
    a, eg, web, wiki = chat
    st = DialogState("late")
    a.turn(st, "google when was real madrid founded")
    for m in ("hi", "thanks", "ok"):
        a.turn(st, m)
    r = a.turn(st, "And, Barcelona?")
    assert r.resolved != "When was Barcelona founded?" and "1899" not in (r.text or ""), (r.resolved, r.text)
