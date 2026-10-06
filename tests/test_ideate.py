"""The idea layer (engramm/understand/ideate.py): ideas, names, picking one, more, a plan towards a goal."""
from types import SimpleNamespace

from engramm.understand import ideate


def _st(said=()):
    return SimpleNamespace(uses={"u_notes": {"_said": list(said)}}, turn=1)


def test_app_ideas_from_the_conversation_topic():
    st = _st(["ok, i got a problem with my tutoring in school"])
    r = ideate.respond(st, "What app can we build? It should be new, and make name and co.", "en")
    assert r and r.count("**") >= 6 and "tutor" in r.lower() and "Money:" in r and "1, 2 or 3" in r
    st.turn = 2
    d = ideate.respond(st, "the second one", "en")
    assert d and "Plan:" in d and "Week 1" in d
    st.turn = 3
    more = ideate.respond(st, "more", "en")
    assert more and more != r


def test_service_topic_gets_service_ideas_not_school_ones():
    r = ideate.respond(_st(), "give me an idea for a business about dog walking", "en")
    assert r and "dog walking" in r and "subjects" not in r and "students" not in r


def test_german_ideas_and_names():
    r = ideate.respond(_st(["ich hab ein problem mit nachhilfe in der schule"]), "was für eine app können wir bauen?", "de")
    assert r and "Nachhilfelehrern" in r and "Geld:" in r
    n = ideate.respond(_st(), "namen für unsere app für pflanzenpflege?", "de")
    assert n and "Namensideen" in n


def test_plan_towards_being_rich_and_no_false_triggers():
    st = _st(["i want to be rich"])
    r = ideate.respond(st, "can you help me build one?", "en")
    assert r and "three levers" in r and "Not individual investment advice" in r
    for msg in ("my laptop is broken", "what is the capital of france?", "i'm tired", "ich bin müde"):
        assert ideate.respond(_st(), msg, "de" if "ich" in msg else "en") is None


def test_names_are_pronounceable():
    for ws in (["tutoring", "school"], ["dog", "walking"], ["pflanzenpflege"], ["bakery"]):
        ns = ideate.names(ws, 3, 5)
        assert len(ns) >= 3 and all(ideate._pronounceable(x) for x in ns), ns
