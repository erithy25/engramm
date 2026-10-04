"""Simple inference from the conversation (engramm/understand/infer.py, U5): only from the user's own words."""
import pytest

from engramm.understand import infer


class _St:
    def __init__(self):
        self.uses = {}


def _run(lang, turns):
    st = _St()
    clash = None
    for t in turns:
        clash = infer.observe(st, t, lang)
    return clash, infer.answer(st, turns[-1], lang)


@pytest.mark.parametrize("lang,turns,want", [
    ("en", ["my train leaves at 7:30", "it takes me 20 minutes to walk to the station", "what time should i leave home?"], "7:10"),
    ("en", ["flight boards at 6:05am", "need 50 mins to get to the airport", "and i want a 30 minute buffer on top",
            "so what time should i leave home?"], "4:45 am"),
    ("de", ["der film fängt um 20:15 an", "er dauert zwei stunden", "wann ist er zu ende?"], "22:15"),
    ("en", ["i bought 3 packs of batteries, 4 in each", "then my dad gave me 5 more", "how many batteries do i have now?"], "17"),
    ("de", ["Ich hab zwei Kartons mit je 12 Flaschen gekauft", "drei Flaschen sind schon leer", "wie viele volle sind noch übrig?"], "21"),
    ("en", ["i run 5 km every day", "how far do i run in a week?"], "35"),
    ("en", ["tickets are $14 each", "there are five of us going", "how much will it cost altogether?"], "70"),
    ("en", ["the recipe is for 4 people and needs 200 g of flour", "i'm cooking for 6", "how much flour do i need?"], "300"),
    ("de", ["Mein Opa ist 82", "meine Mutter ist 29 Jahre jünger als er", "wie alt ist sie?"], "53"),
    ("en", ["today is monday", "my party is on friday", "how many days until my party?"], "4 days"),
    ("de", ["Die Hochzeit ist in 30 Tagen", "jetzt sind schon 9 Tage vergangen", "wie viele Tage sind es noch?"], "21"),
    ("en", ["option A costs 450 and option B costs 380", "which one is cheaper?"], "Option b"),
    ("en", ["flat 1 is 54 m² and 20 minutes from work, flat 2 is 61 m² and 35 minutes away",
            "what matters most to me is a short commute", "which should i take?"], "Flat 1"),
    ("en", ["my neighbour Priya lent me her ladder", "and my coworker Sam helped me carry it home", "who lent me the ladder?"], "Priya"),
    ("en", ["I just moved to Leeds last week", "any tips for finding a good gym near me?"], "Leeds"),
])
def test_infers_from_what_was_said(lang, turns, want):
    _, out = _run(lang, turns)
    assert out and want.lower() in out.lower(), out


@pytest.mark.parametrize("lang,turns,want", [
    ("en", ["i'm 34 years old", "i love hiking", "i'm 29 by the way"], "34"),
    ("de", ["ich hab keine kinder", "mein sohn ist heute krank"], "keine Kinder"),
])
def test_contradictions_are_asked_about(lang, turns, want):
    clash, _ = _run(lang, turns)
    assert clash and want in clash


@pytest.mark.parametrize("lang,turns", [
    ("en", ["what time should i leave?"]),                       # no appointment said: nothing to compute
    ("en", ["how many cats do i have?"]),
    ("en", ["which one is cheaper?"]),
    ("en", ["i have two kids", "how many kids do i have?"]),     # a plain count is the memory's answer
])
def test_no_answer_without_the_facts(lang, turns):
    _, out = _run(lang, turns)
    assert out is None
