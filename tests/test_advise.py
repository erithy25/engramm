"""The advice layer (engramm/understand/advise.py): request kinds, weak replies, off-topic lists, valence."""
from types import SimpleNamespace

from engramm.understand import advise


def _st(said=(), sit=None, turn=5):
    uses = {"u_notes": {"_said": list(said)}}
    if sit:
        uses["u_sit"] = sit
    return SimpleNamespace(uses=uses, turn=turn, recent=[])


def test_request_kinds():
    assert advise.request("should i text him or wait?") == "choice"
    assert advise.request("is that normal?") == "judge"
    assert advise.request("what do i even say?") == "say"
    assert advise.request("how long does that take?") == "howlong"
    assert advise.request("what should i do?") == "do"
    assert advise.request("ok thanks") == "close"
    assert advise.request("what do i do for a living?") is None       # a question about oneself, not a request for help
    assert advise.request("what do i do now?") == "do"


def test_weak_and_off_topic():
    assert advise.weak("I don't know, sorry.", "smalltalk") and not advise.weak("Try vinegar.", "smalltalk")
    convo = "my cat keeps scratching the sofa how do i stop it"
    assert not advise.off_topic("For a group with a vegan guest:\n\n• A big curry", convo)
    printer = "Here's what I'd try:\n\n• Restart the printer and the router\n• Update the printer software"
    assert advise.off_topic(printer, "my friend and my sister had a fight what should i do")
    assert not advise.off_topic(printer, "my printer keeps jamming what should i do")


def test_advise_replaces_only_weak_or_off_topic():
    st = _st(["my boss keeps taking credit for my work"])
    assert advise.advise(st, "what should i do?", "en", "I don't know, sorry.", "unknown")
    assert advise.advise(st, "what should i do?", "en", "Talk to your boss in private first.", "smalltalk") is None


def test_valence_fix():
    st = _st()
    assert advise.valence_fix(st, "my printer is broken", "en", "That's great!") is not None
    assert advise.valence_fix(st, "meine freundin meldet sich nicht mehr", "de", "Oh, das tut weh.") is None
    assert advise.valence_fix(st, "i passed my exam", "en", "Oh no, I'm sorry.") is not None
    assert advise.valence_fix(st, "it was amazing", "en", "Love that! What stood out?") is None


def test_react_on_store_ack():
    st = _st()
    r = advise.react(st, "my cat has started peeing outside the litter box", "en", "Noted, thanks for telling me about your cat.")
    assert r and "How long" in r
    assert advise.react(st, "my name is tom", "en", "Noted, thanks for telling me about your name.") is None


def test_anchor_turns_filler_into_a_next_step():
    st = _st(["my printer keeps jamming and it's so annoying"])
    r = advise.anchor(st, "it's an old one", "en", "Ah, okay.")
    assert r and r.startswith("Okay, that helps. Next I'd try this:")
    assert advise.anchor(st, "it's an old one", "en", "Ah, okay. How old is it exactly?") is None
    assert advise.anchor(st, "thanks, i'll try that", "en", "Ah, okay.") is None


def test_wikibooks_steps_with_source():
    from engramm.know import wikibooks
    it = wikibooks.find("my bike has a flat", "en")
    assert it and "flat" in it["title"].lower()
    assert wikibooks.find("my boss has a flat", "en") is None or "Bicycles" not in wikibooks.find("my boss has a flat", "en")["title"]
    de = wikibooks.find("ich hab mich am herd verbrannt", "de")
    assert de and "Verbrennung" in de["title"]
    r = wikibooks.render(de)
    assert r.startswith("Aus Wikibooks") and "112" in r and "•" in r
