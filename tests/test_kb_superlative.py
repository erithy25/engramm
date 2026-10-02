"""Superlative questions from the fact bank (engramm/kb/superlative.py) on a tiny sqlite bank."""
import sqlite3

from engramm.kb.superlative import answer


def _bank():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE entity(id INTEGER PRIMARY KEY, title TEXT NOT NULL, type TEXT, popularity INTEGER NOT NULL);
        CREATE TABLE fact(entity INTEGER NOT NULL, prop TEXT NOT NULL, value TEXT NOT NULL, dtype TEXT NOT NULL,
                          value_entity INTEGER, src TEXT);
        INSERT INTO entity VALUES (1, 'Himalayas', 'Mountain', 9), (2, 'Mount Everest', 'Mountain', 5),
                                  (3, 'K2', 'Mountain', 4), (4, 'Nile', 'River', 3), (5, 'Amazon River', 'River', 3),
                                  (6, 'Russian Empire', 'Country', 9), (7, 'Russia', 'Country', 9),
                                  (8, 'Georgia (country)', 'Country', 2), (9, 'China', 'Country', 9);
        INSERT INTO fact VALUES (1, 'elevation', '8848.86', 'double', NULL, NULL),
                                (2, 'elevation', '8848.86', 'double', NULL, NULL),
                                (2, 'mountainRange', 'Himalayas', 'entity', NULL, NULL),
                                (3, 'elevation', '8611', 'double', NULL, NULL),
                                (4, 'length', '6650000', 'double', NULL, NULL),
                                (5, 'length', '6400000', 'double', NULL, NULL),
                                (6, 'areaTotal', '23700000000000', 'double', NULL, NULL),
                                (7, 'areaTotal', '17075400000000', 'double', NULL, NULL),
                                (8, 'populationTotal', '36886474012104', 'nonNegativeInteger', NULL, NULL),
                                (8, 'populationTotal', '3929581', 'nonNegativeInteger', NULL, NULL),
                                (9, 'populationTotal', '1410539758', 'nonNegativeInteger', NULL, NULL);
    """)
    return db


def test_superlatives_skip_ranges_historic_states_and_implausible_rows():
    db = _bank()
    assert answer(db, "what is the tallest mountain in the world?").title == "Mount Everest"
    assert answer(db, "whats the tallest mountain", rank=2).title == "K2"
    assert answer(db, "which is the longest river").text.startswith("The Nile is the longest river")
    assert answer(db, "what's the largest country").title == "Russia"
    assert answer(db, "what is the most populous country").title == "China"


def test_superlative_only_for_the_whole_world_and_known_pairs():
    db = _bank()
    assert answer(db, "what is the tallest mountain in africa") is None
    assert answer(db, "what is the biggest city in the world") is None
    assert answer(db, "what is the tallest mountain", rank=4) is None
