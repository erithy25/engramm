"""Text handling for the network channels: the main text of a page by rules, the reference zone
at the end of a Wikipedia article, sentence choice from fetched articles (the lead always, never a
bibliography line), names in replies ("Vickers" → "Diana Vickers"), the name check for "tell me
about …" and spelling that leaves abbreviations alone."""

from __future__ import annotations

from engramm.chat.dialog import _full_name, _name_match
from engramm.web.clean import is_reference, paragraphs, strip_references
from engramm.web.shelf import best_sentences

PAGE = """<html><head><title>Zorblax Bridge - Wikipedia</title><script>var x = 1;</script></head><body>
<nav class="menu"><a href="/">Home</a> <a href="/a">About</a> <a href="/b">Contact us today</a></nav>
<div id="content"><h1>Zorblax Bridge</h1>
<p>The Zorblax Bridge is a suspension bridge over the Velm river in Quorvia, and it is one of the longest bridges of its
kind in the region.[1] It was opened in 1931 after six years of construction.[citation needed]</p>
<p>The bridge was designed by the engineer Mirela Tosk, who had studied the older bridges of the region for many
years before she was given the commission.[2][a]</p></div>
<footer class="footer"><p>Copyright 2026 by the people who wrote all of this text and many other things.</p></footer>
</body></html>"""

ARTICLE = ("Alonzo \"Lonnie\" Johnson (February 8, 1899 – June 16, 1970) was an American blues and jazz singer. "
           "He was a pioneer of jazz guitar. Johnson was born in New Orleans, Louisiana. "
           "In 1959 he was working at a hotel in Philadelphia when a disc jockey located him. "
           "He died in Toronto in 1970 after a stroke. His music is still played today on the radio. "
           "King, B.B.; Ritz, David (1996). Blues All Around Me. New York: Avon Books. ISBN 978-0380973187. "
           "Crowe, Cameron (1985). \"Liner notes\". Columbia Records. p. 10. Retrieved 25 September 2013. "
           "\"Lonnie Johnson profile\". example.org.")


def test_paragraphs_keep_the_main_text_only():
    paras = paragraphs(PAGE)
    text = " ".join(paras)
    assert "designed by the engineer Mirela Tosk" in text and "opened in 1931" in text
    assert "[1]" not in text and "[citation needed]" not in text and "[a]" not in text
    assert "Contact us" not in text and "Copyright" not in text and "var x" not in text


def test_reference_lines():
    for line in ("Retrieved 25 September 2013.", "ISBN 978-0380973187.", "King, B.B.; Ritz, David (1996).",
                 "\"Lonnie Johnson profile\". example.org.", "(1863).", "\"Annual Report – 2012\" (PDF).",
                 "Archived from the original on 29 November 2016.", "Columbia Records. p. 10."):
        assert is_reference(line), line
    for line in ("He died in Toronto in 1970 after a stroke.", "Johnson was born in New Orleans, Louisiana.",
                 "\"Music to Make Boys Cry\" is the title track released alongside the album on 15 September 2013."):
        assert not is_reference(line), line


def test_reference_zone_is_cut_and_the_article_kept():
    out = strip_references(ARTICLE)
    assert out.endswith("still played today on the radio.")
    assert "ISBN" not in out and "Retrieved" not in out
    short = "One sentence here. Another one there."
    assert strip_references(short) == short


def test_best_sentences_take_the_lead_and_skip_references():
    doc = {"t": "Lonnie Johnson (musician)", "x": ARTICLE}
    got = best_sentences("When was Lonnie Johnson born?", [doc], n=4, context=True)
    texts = [g[1] for g in got]
    assert any(t.startswith("Alonzo \"Lonnie\" Johnson (February 8, 1899") for t in texts)     # the lead
    assert not any("ISBN" in t or "Retrieved" in t for t in texts)
    prev = {g[1]: g[3] for g in got}
    lead = next(t for t in texts if t.startswith("Alonzo"))
    assert prev[lead] == ""                                       # nothing before the first sentence
    assert all(len(g) == 4 for g in got)
    later = [t for t in texts if t.startswith("In 1959")]
    assert not later or "Johnson was born" in prev[later[0]]       # the two sentences before it


def test_name_match_is_by_words():
    assert _name_match("the Zorblax Bridge", "Zorblax Bridge")
    assert _name_match("Lonnie Johnson", "Lonnie Johnson (musician)")
    assert _name_match("Paris", "Paris, Texas")
    assert _name_match("New York", "New York City")
    assert not _name_match("thai", "List of wars involving Thailand")
    assert not _name_match("Tower", "Eiffel Tower")
    assert not _name_match("York", "New York City")


def test_full_name_from_the_same_article():
    texts = ["On 9 December 2011, Vickers released the single.",
             "Music to Make Boys Cry is the second studio album by English singer and songwriter Diana Vickers."]
    assert _full_name("Vickers", texts) == "Diana Vickers"
    assert _full_name("Smith", ["Adam Smith met John Smith."]) == "Smith"         # two people: leave it
    assert _full_name("1931", texts) == "1931" and _full_name("Diana Vickers", texts) == "Diana Vickers"


def test_spelling_leaves_abbreviations_alone():
    from pathlib import Path

    from engramm.nlp.spell import Speller
    pack = Path("/dev/shm/engramm/pack-b3/spell.json")
    if not pack.exists():
        import pytest
        pytest.skip("no knowledge pack here")
    sp = Speller.load(pack)
    assert "xHCI" in sp.fix("What does xHCI stand for?")
    assert "iPhone" in sp.fix("who makes the iPhone?")
