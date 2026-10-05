"""Suggestions under the user's conditions (engramm/understand/suggest.py)."""
import pytest

from engramm.understand import infer
from engramm.understand.suggest import check, constraints, suggest, violates


class _St:
    def __init__(self):
        self.uses = {}


def _st(lang, turns):
    st = _St()
    for t in turns:
        infer.observe(st, t, lang)
    return st


@pytest.mark.parametrize("lang,turns,bad", [
    ("en", ["ugh my throat swells up if i even touch a peanut", "what should i pack to snack on for the hike?"], r"peanut|nut\b|satay"),
    ("en", ["fyi i went fully vegan, no animal stuff at all", "got a recipe idea for dinner?"], r"egg|cheese|feta|chicken|milk\b"),
    ("de", ["milch vertrag ich null, bin laktoseintolerant", "frühstücksidee für morgen?"], r"käse|joghurt|quark|sahne|\bmilch"),
    ("de", ["pilze find ich echt eklig", "welche pizza soll ich heut abend bestellen?"], r"funghi|pilz"),
])
def test_forbidden_items_never_suggested(lang, turns, bad):
    import re
    st = _st(lang, turns)
    out = suggest(st, turns[-1], lang)
    assert out and not re.search(bad, out, re.I), out


def test_budget_city_and_name_are_used():
    st = _st("en", ["want to get my dad a birthday present, budget's like 30 euros max", "he's into gardening",
                    "what should i get him?"])
    out = suggest(st, "what should i get him?", "en")
    assert "30" in out and "garden" in out.lower()
    st = _st("en", ["just moved to leeds last month", "where could i go for a nice walk this weekend?"])
    assert "Leeds" in suggest(st, "where could i go for a nice walk this weekend?", "en")
    st = _st("en", ["my sister lena is graduating on friday", "can you write a short card message for my sister?"])
    assert "Lena" in suggest(st, "can you write a short card message for my sister?", "en")


def test_a_good_reply_stays_and_a_violating_one_is_replaced():
    st = _st("en", ["i hate mushrooms", "suggest a pizza for me"])
    assert check(st, "suggest a pizza for me", "en", "How about a Margherita — no mushrooms, promise.", "smalltalk") is None
    st = _st("en", ["i'm allergic to peanuts", "any snack ideas?"])
    c = constraints(st)
    assert violates("• Peanut butter on toast", c)
    assert check(st, "any snack ideas?", "en", "How about:\n\n• Peanut butter on toast\n• Popcorn", "smalltalk")


def test_nothing_to_respect_means_no_suggestion():
    st = _st("en", ["what should i cook tonight?"])
    assert suggest(st, "what should i cook tonight?", "en") is None
