"""The fact bank (engramm/kb): linking names to entities, question patterns, value rendering,
and the conversation using it (with a tiny database in the build script's schema)."""

from __future__ import annotations

import datetime as dt
import sqlite3

import pytest

from engramm.kb.kgqa import KGQA
from engramm.kb.store import FactBank
from tests.test_chat_flows import corpus  # noqa: F401  (fixture)

ENTITIES = [
    (1, "France", "Country", 900), (2, "Paris", "City", 800), (3, "Paris (mythology)", "Deity", 50),
    (4, "Albert Einstein", "Scientist", 700), (5, "Ulm", "Town", 100), (6, "Hamlet", "Play", 400),
    (7, "William Shakespeare", "Writer", 900), (8, "Euro", "Currency", 300), (9, "French language", "Language", 500),
    (10, "Mount Everest", "Mountain", 400), (11, "Nile", "River", 300), (12, "Mercury (planet)", "Planet", 300),
    (13, "Princeton, New Jersey", "Town", 90), (14, "Microsoft", "Company", 600), (15, "Bill Gates", "Person", 600),
    (16, "Paul Allen", "Person", 300), (17, "Mileva Marić", "Scientist", 80),
]
ALIASES = [("usa", 99, 2), ("einstein", 4, 2), ("the bard", 7, 2), ("mercury", 12, 1)]
FACTS = [
    (1, "capital", "Paris", "entity", 2), (1, "currency", "Euro", "entity", 8),
    (1, "officialLanguage", "French language", "entity", 9), (1, "populationTotal", "68042591",
                                                              "nonNegativeInteger", None),
    (1, "areaTotal", "643801000000.0", "double", None),
    (4, "birthDate", "1879-03-14", "date", None), (4, "deathDate", "1955-04-18", "date", None),
    (4, "birthPlace", "Ulm", "entity", 5), (4, "deathPlace", "Princeton, New Jersey", "entity", 13),
    (4, "spouse", "Mileva Marić", "entity", 17),
    (6, "author", "William Shakespeare", "entity", 7), (7, "birthYear", "1564", "gYear", None),
    (10, "elevation", "8848.86", "double", None), (11, "length", "6650000.0", "double", None),
    (14, "foundedBy", "Bill Gates", "entity", 15), (14, "foundedBy", "Paul Allen", "entity", 16),
    (14, "foundingDate", "1975-04-04", "date", None),
    (15, "birthDate", "1955-10-28", "date", None),
]


@pytest.fixture()
def kb(tmp_path):
    path = tmp_path / "kb.sqlite"
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE entity(id INTEGER PRIMARY KEY, title TEXT NOT NULL, type TEXT, popularity INTEGER NOT NULL);
        CREATE TABLE alias(name TEXT NOT NULL, entity INTEGER NOT NULL, kind INTEGER NOT NULL);
        CREATE TABLE fact(entity INTEGER NOT NULL, prop TEXT NOT NULL, value TEXT NOT NULL, dtype TEXT NOT NULL,
                          value_entity INTEGER);
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    db.executemany("INSERT INTO entity VALUES (?,?,?,?)", ENTITIES)
    rows = [(t.lower(), i, 0) for i, t, _, _ in ENTITIES] + ALIASES
    rows += [("paris", 3, 1)]
    db.executemany("INSERT INTO alias VALUES (?,?,?)", rows)
    db.executemany("INSERT INTO fact VALUES (?,?,?,?,?)", FACTS)
    db.execute("INSERT INTO meta VALUES ('source', '\"test\"')")
    db.commit()
    db.close()
    return path


@pytest.mark.parametrize("q,want", [
    ("What is the capital of France?", "The capital of France is Paris."),
    ("what's france's capital", "The capital of France is Paris."),
    ("When was Albert Einstein born?", "Albert Einstein was born on 14 March 1879."),
    ("When was Einstein born?", "Albert Einstein was born on 14 March 1879."),
    ("Where was Einstein born?", "Albert Einstein was born in Ulm."),
    ("Where did Einstein die?", "Albert Einstein died in Princeton, New Jersey."),
    ("How old was Einstein?", "Albert Einstein died at the age of 76 (14 March 1879 – 18 April 1955)."),
    ("How old is Bill Gates?", "Bill Gates is 70 years old (born 28 October 1955)."),
    ("Who was Einstein married to?", "Albert Einstein was married to Mileva Marić."),
    ("Who wrote Hamlet?", "Hamlet was written by William Shakespeare."),
    ("When was the bard born?", "William Shakespeare was born in 1564."),
    ("What currency does France use?", "The currency of France is the Euro."),
    ("What language is spoken in France?", "In France, people speak French."),
    ("What is the population of France?", "France has a population of 68,042,591 (as of my data)."),
    ("How big is France?", "France covers 643,801 km² (248,573 sq mi)."),
    ("How tall is Mount Everest?", "Mount Everest is 8,849 m (29,032 ft) high."),
    ("How long is the Nile?", "The Nile is 6,650 km long."),
    ("Who founded Microsoft?", "Microsoft was founded by Bill Gates and Paul Allen."),
    ("When was Microsoft founded?", "Microsoft was founded on 4 April 1975."),
])
def test_questions(kb, q, want):
    ans = KGQA(FactBank(kb), today=dt.date(2026, 9, 29)).answer(q)
    assert ans is not None and ans.text == want


@pytest.mark.parametrize("q", ["What is the capital of Atlantis?", "Who wrote France?", "What is my name?",
                               "Why is the sky blue?", "When was Hamlet born?", "What is the capital of it?"])
def test_no_answer_without_a_clear_case(kb, q):
    assert KGQA(FactBank(kb)).answer(q) is None


def test_linking_prefers_titles_types_and_popularity(kb):
    bank = FactBank(kb)
    assert [e.title for e, _ in bank.link("Paris")][:2] == ["Paris", "Paris (mythology)"]
    assert bank.link("mercury")[0][0].name == "Mercury"
    assert bank.link("nowhere") == []


def test_assistant_prefers_the_fact_bank(kb, corpus):  # noqa: F811
    from engramm.chat.dialog import Assistant, DialogState
    from tests.test_chat_flows import CLOCK, _bot
    a = Assistant(_bot(corpus), clock=CLOCK, kb_path=kb)
    st = DialogState("kb")
    r = a.turn(st, "What is the capital of France?")
    assert r.via == "kb" and r.answer == "Paris" and r.text == "The capital of France is Paris."
    assert r.source == {"kind": "kb", "source": "dbpedia", "key": "France"}
    r = a.turn(st, "Who wrote Hamlet?")
    assert r.text == "Hamlet was written by William Shakespeare."
    r = a.turn(st, "When was he born?")
    assert r.resolved == "When was William Shakespeare born?" and r.text == "William Shakespeare was born in 1564."
    why = a.turn(st, "how do you know?")
    assert "William Shakespeare" in why.text and "infobox" in why.text
    # questions the bank cannot answer still go to the reading pipeline
    r = a.turn(st, "Who invented the telephone?")
    assert r.via == "lookup" and r.answer == "Alexander Graham Bell"


def test_elliptical_follow_up(kb, corpus):  # noqa: F811
    from engramm.chat.dialog import Assistant, DialogState
    from tests.test_chat_flows import CLOCK, _bot
    a = Assistant(_bot(corpus), clock=CLOCK, kb_path=kb)
    st = DialogState("ell")
    assert a.turn(st, "When was Albert Einstein born?").text == "Albert Einstein was born on 14 March 1879."
    r = a.turn(st, "And Bill Gates?")
    assert r.resolved == "When was Bill Gates born?" and r.text == "Bill Gates was born on 28 October 1955."
    assert a.turn(DialogState("fresh"), "And Bill Gates?").resolved != "When was Bill Gates born?"
