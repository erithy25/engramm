"""'Write me an essay about X': a structured text with its source, never stored as a fact about the user."""
import datetime as dt

from engramm.chat.dialog import Assistant, DialogState
from tests.test_chat_flows import _bot, corpus  # noqa: F401  (fixture)


def test_essay_request_gives_a_text_with_source_and_stores_nothing(corpus):  # noqa: F811
    bot = _bot(corpus)
    a = Assistant(bot, clock=lambda: dt.datetime(2026, 10, 6, 10, 0))
    before = len(bot.user_texts())
    r = a.turn(DialogState("e1"), "Please write me an essay about the telephone")
    assert r.via == "writing" and "**Telephone**" in r.text and "Source: Wikipedia" in r.text, r.text
    assert len(bot.user_texts()) == before                       # not remembered as "you told me"
    r = a.turn(DialogState("e2"), "write an essay about qwertyzz please")
    assert "don't have an article" in r.text
    r = a.turn(DialogState("e3"), "schreib mir einen aufsatz über das telefon")
    assert r.via == "writing"


def test_essay_patterns():
    for m in ("write me an essay about napoleon", "Can you write a short article on photosynthesis?",
              "please give me a report about the french revolution", "I need a 500 word essay on climate change"):
        assert Assistant._ESSAY_EN.match(m), m
    for m in ("schreib mir einen aufsatz über napoleon", "kannst du mir einen text über die photosynthese schreiben?"):
        assert Assistant._ESSAY_DE.match(m), m
    for m in ("i wrote an essay yesterday", "my essay about napoleon is due tomorrow"):
        assert not Assistant._ESSAY_EN.match(m), m
