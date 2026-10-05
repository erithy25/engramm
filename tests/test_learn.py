"""Local learning (engramm/learn, U4): corrections, "forget that" bit-identical, taught words, style, episodes,
the bandit — on the small test corpus (no pack needed)."""

from __future__ import annotations

import datetime as dt
import json

import pytest

from engramm.chat.dialog import Assistant, DialogState
from engramm.chat.textmem import LoggedTextMemory
from engramm.learn import Learner
from engramm.learn.bandit import MIN_SIGNALS, choose
from engramm.learn.state import LearnState
from engramm.understand import frames as fr
from tests.test_chat_flows import _bot, corpus  # noqa: F401  (fixture)

CLOCK = lambda: dt.datetime(2026, 10, 1, 18, 30)          # noqa: E731


@pytest.fixture()
def chat(corpus, tmp_path):                                # noqa: F811
    bot = _bot(corpus, LoggedTextMemory(tmp_path / "chat_memory.log"))
    a = Assistant(bot, clock=CLOCK)
    a.learner = Learner(tmp_path / "learn.json")
    yield a, tmp_path
    a.learner.state.reset()                                 # the lexicon overlay is global: leave it clean


def test_correction_is_learned_and_kept(chat):
    a, tmp = chat
    st = DialogState("c1")
    a.turn(st, "hi")
    text = "someone took my wallet"
    assert fr.parse(text, "en", extra=a.learner.extra).kind == "THEFT"
    a.turn(st, text)
    reply = a.turn(st, "no, nobody stole it, i lost it somewhere")
    good = "LOSS"
    assert reply.via == "learn" and "got that wrong" in reply.text
    assert fr.parse(text, "en", extra=a.learner.extra).kind == good
    # kept on disk and read back
    again = Learner(tmp / "learn.json")
    assert fr.parse(text, "en", extra=again.extra).kind == good


def test_forget_that_restores_the_state_bit_for_bit(chat):
    a, tmp = chat
    st = DialogState("c2")
    a.turn(st, "hi")
    a.turn(st, "no more emojis please")                     # one step learned first
    before = (tmp / "learn.json").read_bytes()
    a.turn(st, "a vape is a device")
    assert (tmp / "learn.json").read_bytes() != before
    r = a.turn(st, "forget that")
    assert r.via == "learn" and "forgotten" in r.text.lower()
    assert (tmp / "learn.json").read_bytes() == before


def test_taught_word_gets_the_category(chat):
    a, _ = chat
    st = DialogState("c3")
    a.turn(st, "hi")
    r = a.turn(st, "a vape is a device")
    assert r.via == "learn" and "vape" in r.text
    f = fr.parse("my vape fell in the water", "en", extra=a.learner.extra)
    assert "DEVICE" in f.obj_cats


def test_known_words_are_not_lessons(chat):
    a, _ = chat
    st = DialogState("c4")
    a.turn(st, "hi")
    r = a.turn(st, "a dog is an animal")
    assert r.via != "learn"


def test_style_short_and_no_emoji(chat):
    a, _ = chat
    st = DialogState("c5")
    a.turn(st, "hi")
    assert a.turn(st, "keep it short").via == "learn"
    assert a.turn(st, "no emojis please").via == "learn"
    assert a.learner.state.style == {"length": "short", "emoji": "off"}
    a.turn(st, "i cut my finger")
    r = a.turn(st, "what should i do?")
    assert r.text.count("• ") <= 2
    assert "🩹" not in r.text and "😣" not in r.text


def test_episode_and_recall(chat):
    a, _ = chat
    st = DialogState("c6")
    a.turn(st, "hi")
    a.turn(st, "my phone screen cracked")
    r = a.turn(DialogState("c6b"), "do you remember what happened?")
    assert r.via == "learn" and "phone screen cracked" in r.text and "today" in r.text


def test_damaged_file_is_set_aside(tmp_path):
    p = tmp_path / "learn.json"
    s = LearnState(p)
    s.set_style("length", "short")
    p.write_text(p.read_text().replace("short", "shorx"))
    s2 = LearnState(p)
    assert s2.ops == [] and (tmp_path / "learn.damaged.json").exists()


def test_bandit_waits_for_signals_and_is_deterministic():
    b: dict = {}
    assert choose(b, "INJURY", "x") is None
    b["INJURY:advise"] = [float(MIN_SIGNALS + 4), 0.0]
    b["INJURY:ask"] = [0.0, float(MIN_SIGNALS)]
    picks = {choose(b, "INJURY", f"s{i}") for i in range(5)}
    assert picks == {"advise"}
    assert choose(b, "INJURY", "s1") == choose(b, "INJURY", "s1")


def test_reset_forgets_everything(chat):
    a, tmp = chat
    st = DialogState("c7")
    a.turn(st, "hi")
    a.turn(st, "a vape is a device")
    r = a.turn(st, "forget everything you learned from me")
    assert r.via == "learn"
    assert a.learner.state.ops == [] and not (tmp / "learn.json").exists()
    assert "DEVICE" not in fr.parse("my vape fell in the water", "en").obj_cats


def test_learning_pack_export_import(tmp_path):
    from engramm.learn.state import LearnState
    a = LearnState(tmp_path / "a.json")
    a.teach_word("zorbel", "en", ["ANIMAL"], "animal")
    a.episode("2026-10-05", "LOSS", "keys", "i lost my keys", "en")
    a.set_style("length", "short")
    pack = a.export_pack()
    assert [w["word"] for w in pack["words"]] == ["zorbel"]
    assert "keys" not in json.dumps(pack) and "short" not in json.dumps(pack)       # nothing personal leaves
    b = LearnState(tmp_path / "b.json")
    assert b.import_pack(pack) == {"words": 1, "corrections": 0, "already": False}
    assert "en:zorbel" in b.words
    assert b.import_pack(pack)["already"]
    bad = {**pack, "words": [{"word": "evil", "lang": "en", "cats": ["PERSON"], "ss": ""}]}
    with pytest.raises(ValueError):
        b.import_pack(bad)                                   # changed after export
    b.reset()
    assert "en:zorbel" not in LearnState(tmp_path / "b.json").words
