"""The situation layer (engramm/understand): lexicon, frame parser, classifier, composition helpers."""
import pytest

from engramm.understand import frames as fr
from engramm.understand.classify import KINDS, classifier
from engramm.understand.lex import lexicon
from tests.test_chat_flows import corpus  # noqa: F401  (fixture)


@pytest.mark.parametrize("text,lang,kind,obj,who", [
    ("my laptop fell in the water", "en", "DAMAGE", "laptop", "me"),
    ("i got stung by a wasp", "en", "INJURY", "", "me"),
    ("someone stole my bike", "en", "THEFT", "bike", "me"),
    ("my grandma passed away", "en", "DEATH", "", "relative"),
    ("i got promoted today!", "en", "SUCCESS", "", "me"),
    ("mein handy ist runtergefallen und das display ist kaputt", "de", "DAMAGE", "handy", "me"),
    ("ich hab meinen schlüssel verloren", "de", "LOSS", "schlüssel", "me"),
    ("mein flug hat drei stunden verspätung", "de", "DELAY", "", "me"),
    ("ich hab mich mit meiner schwester gestritten", "de", "CONFLICT", "", "relative"),
])
def test_frames_kind_and_roles(text, lang, kind, obj, who):
    f = fr.parse(text, lang)
    assert f.kind == kind
    assert f.obj_word == obj
    assert f.who == who


@pytest.mark.parametrize("text,lang", [
    ("what is the capital of france?", "en"),
    ("wie spät ist es?", "de"),
    ("they asked for my card pin", "en"),          # "pin" the thing, not the wrestling win
])
def test_frames_no_situation(text, lang):
    assert fr.parse(text, lang).kind == ""


def test_lexicon_categories():
    en, de = lexicon("en"), lexicon("de")
    assert "INSECT" in en.lookup("wasp")[0].cats
    assert any("DEVICE" in e.cats for e in en.lookup("laptop"))
    assert any("BODYPART" in e.cats for e in en.lookup("knee"))
    pin = [e for e in en.lookup("pin") if e.pos == "n"][0]
    assert "WIN" not in pin.ev
    assert de.lookup("handy")


def test_classifier_loaded_and_bounded():
    clf = classifier()
    assert clf
    f = fr.parse("my phone screen cracked", "en", use_model=False)
    assert clf.predict(f, "my phone screen cracked", f.kind) in set(KINDS) - {"NONE"} | {""}


def test_user_correction_shifts_prediction():
    """A user's own correction (engramm/learn) is an additive weight on the same features."""
    clf = classifier()
    text = "my bike is gone"
    f = fr.parse(text, "en", use_model=False)
    extra = {"w:en:gone": {"THEFT": 50.0}}
    assert clf.predict(f, text, f.kind, extra) == "THEFT"


def test_howto_index_finds_by_name_and_alias():
    from engramm.know.howto import howto, render
    h = howto()
    assert h
    a = h.find("how do you treat hives?")
    assert a is not None and a.kind == "HEALTH"
    out = render(a)
    assert "Wikipedia" in out and "doctor" in out          # the safety tier: source and the doctor line, always
    assert h.find("what's the weather like?") is None


def test_injury_advice_carries_the_source(corpus, tmp_path):     # noqa: F811
    import datetime as dt
    from engramm.chat.dialog import Assistant, DialogState
    from engramm.chat.textmem import LoggedTextMemory
    from tests.test_chat_flows import _bot
    a = Assistant(_bot(corpus, LoggedTextMemory(tmp_path / "m.log")), clock=lambda: dt.datetime(2026, 10, 1, 18, 30))
    st = DialogState("u1")
    a.turn(st, "hi")
    a.turn(st, "i sprained my ankle")
    r = a.turn(st, "what should i do?")
    assert "Sprained ankle" in r.text and "doctor" in r.text


def test_city_ranking_from_the_fact_bank():
    from pathlib import Path
    kb = Path("/dev/shm/engramm/pack-b3/kb.sqlite")
    if not kb.exists():
        pytest.skip("needs the knowledge pack")
    from engramm.kb.kgqa import KGQA
    from engramm.kb.store import FactBank
    q = KGQA(FactBank(kb))
    a = q.answer("what are the largest cities in germany")
    assert a is not None and a.values[:3] == ["Berlin", "Hamburg", "Munich"]
    d = q.answer("was sind die größten städte in spanien")
    assert d is not None and "Madrid" in d.text and "Einwohner" in d.text
