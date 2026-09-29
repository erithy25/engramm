"""Writing (engramm/chat/writing.py): understanding requests, drafts by purpose and tone, the
edit loop, summaries, rephrasing, spelling fixes, poems — and in the conversation."""

from __future__ import annotations

import datetime as dt

import pytest

from engramm.chat.bank import load_bank
from engramm.chat.writing import (apply_edit, draft, edit_command, fix_text, parse_request, rephrase, summarize,
                                  writing_request)
from tests.test_chat_flows import CLOCK, _bot, corpus  # noqa: F401  (fixture)

SPEC = load_bank().writing
TODAY = dt.date(2026, 9, 29)


@pytest.mark.parametrize("msg,genre,recipient,tone,purpose", [
    ("can you help me write an email to my boss asking for a day off tomorrow", "email", "boss", "formal", "day_off"),
    ("write a message to my mom saying I'll be late for dinner", "message", "mom", "casual", "say"),
    ("Write a formal email to my landlord complaining about the broken heating", "email", "landlord", "formal",
     "complaint"),
    ("write an email to customer service to cancel my gym membership", "email", "customer service", "formal",
     "cancel"),
    ("email my friend Anna to invite her to my birthday party on Saturday", "email", "friend", "casual", "invitation"),
    ("write a thank you note to my teacher for all her help this year", "note", "teacher", "formal", "thanks"),
    ("write an email to my professor asking for an extension on my essay because I was ill", "email", "professor",
     "formal", "extension"),
])
def test_requests_are_understood(msg, genre, recipient, tone, purpose):
    r = parse_request(msg, SPEC["purposes"])
    assert (r.genre, r.recipient, r.tone, r.purpose) == (genre, recipient, tone, purpose)


def test_day_off_email_and_edits():
    r = parse_request("write an email to my boss asking for a day off tomorrow", SPEC["purposes"])
    text = draft(r, SPEC, "Erik", TODAY, "c")
    assert text.startswith("Subject: ") and "[Boss's name]" in text
    assert "tomorrow (Wednesday, 30 September)" in text and text.rstrip().endswith("Erik")
    short = draft(apply_edit(r, "shorter", None), SPEC, "Erik", TODAY, "c")
    assert len(short) < len(text)
    added = draft(apply_edit(r, "add", "that I will be reachable by phone"), SPEC, "Erik", TODAY, "c")
    assert "I will be reachable by phone." in added
    casual = draft(apply_edit(r, "casual", None), SPEC, "Erik", TODAY, "c")
    assert casual != text and "Dear" not in casual
    signed = draft(apply_edit(r, "sign", "Dr. E. Thye"), SPEC, None, TODAY, "c")
    assert signed.rstrip().endswith("Dr. E. Thye")
    assert edit_command("make it shorter") == ("shorter", None)
    assert edit_command("ok, add that I can work on Saturday") == ("add", "I can work on Saturday")
    assert edit_command("write a poem about cats") is None


def test_named_recipient_and_messages():
    r = parse_request("email my friend Anna to invite her to my birthday party on Saturday", SPEC["purposes"])
    assert r.recipient_name == "Anna"
    text = draft(r, SPEC, "Erik", TODAY, "c")
    assert "Hi Anna," in text and "to my birthday party on Saturday, 3 October" in text
    m = draft(parse_request("write a message to my mom saying I'll be late for dinner", SPEC["purposes"]), SPEC,
              "Erik", TODAY, "c")
    assert m.startswith("Hi Mom! ") and "I'll be late for dinner" in m and "Subject" not in m
    f = draft(parse_request("write an email to Mr. Smith to follow up on my job application", SPEC["purposes"]),
              SPEC, None, TODAY, "c")
    assert "Dear Mr. Smith," in f and "up on my job application" in f and "[Your name]" in f


def test_summaries_rephrasing_and_fixes():
    text = ("The Moon is Earth's only natural satellite. It orbits at an average distance of 384,400 km. "
            "The Moon is the fifth largest satellite in the Solar System. Its surface is covered by craters. "
            "The Moon's gravity causes tides on Earth. Humans first landed on the Moon in 1969.")
    s = summarize(text)
    assert 1 <= len(s) <= 3 and s[0] == "The Moon is Earth's only natural satellite."
    assert rephrase("hey, can u send me the report asap? thx", "formal") == \
        "Hello, could you send me the report as soon as possible? Thank you."
    assert rephrase("I am sure we will not be late.", "casual") == "I'm sure we won't be late."
    assert fix_text("i recieved teh package yesterday and its broken") == \
        "I received the package yesterday and it's broken."
    assert writing_request("Summarize: " + text) == "summary"
    assert writing_request("make this more formal: hey there") == "rephrase"
    assert writing_request("write a poem about the sea") == "poem"
    assert writing_request("What is the capital of France?") is None


def test_writing_in_the_conversation(corpus):  # noqa: F811
    from engramm.chat.dialog import Assistant, DialogState
    a = Assistant(_bot(corpus), clock=CLOCK)
    st = DialogState("w")
    a.turn(st, "My name is Erik.")
    r = a.turn(st, "can you help me write an email to my boss asking for a day off tomorrow")
    assert r.kind == "writing" and "Subject:" in r.text and r.text.count("Erik") >= 1
    r2 = a.turn(st, "make it shorter")
    assert r2.kind == "writing" and r2.text.startswith("Here's a shorter version:")
    r3 = a.turn(st, "write a poem about the sea")
    assert "the sea" in r3.text and "Subject" not in r3.text
    assert a.bot.user_texts() and len(a.bot.user_texts()) == 1        # nothing about the email was stored
