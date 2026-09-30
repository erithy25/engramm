"""engramm/nlp: the counted tagger and the labelled arc-hybrid parser on a toy treebank."""

from __future__ import annotations

from engramm.nlp.parse import Parser, _gold_moves
from engramm.nlp.pos import PerceptronTagger

TREEBANK = [
    (["the", "dog", "barks"], ["DET", "NOUN", "VERB"], [2, 3, 0], ["det", "nsubj", "root"]),
    (["a", "cat", "sleeps"], ["DET", "NOUN", "VERB"], [2, 3, 0], ["det", "nsubj", "root"]),
    (["dogs", "chase", "cats"], ["NOUN", "VERB", "NOUN"], [2, 0, 2], ["nsubj", "root", "obj"]),
    (["the", "cat", "sees", "a", "dog"], ["DET", "NOUN", "VERB", "DET", "NOUN"], [2, 3, 0, 5, 3],
     ["det", "nsubj", "root", "det", "obj"]),
]


def test_parser_learns_the_toy_treebank(tmp_path):
    p = Parser(("lab",))
    p.train(TREEBANK * 5, epochs=8)
    for words, tags, heads, labels in TREEBANK:
        got_h, got_l = p.parse_labelled(words, tags)
        assert got_h == heads and got_l == labels
    p.save(tmp_path / "parse.json")
    q = Parser.load(tmp_path / "parse.json")
    assert q.parse(["the", "dog", "sees", "a", "cat"], ["DET", "NOUN", "VERB", "DET", "NOUN"]) == [2, 3, 0, 5, 3]
    assert q.parse_labelled([], []) == ([], [])


def test_oracle_follows_gold_from_the_start():
    words = ["<start>", "the", "dog", "barks", "ROOT"]
    gold = [None, 2, 3, 4, None]
    assert _gold_moves(2, len(words), [1], gold) == [2]      # 'the' becomes a left child of 'dog'


def test_tagger_learns_and_is_deterministic():
    data = [(w, t) for w, t, _, _ in TREEBANK] * 5
    a, b = PerceptronTagger(), PerceptronTagger()
    a.train(data, epochs=5)
    b.train(data, epochs=5)
    assert a.tag(["the", "dog", "sleeps"]) == ["DET", "NOUN", "VERB"]
    assert a.model.weights == b.model.weights


def test_device_requests(tmp_path):
    from engramm.chat.device import DeviceRequests
    from engramm.nlp.intent import IntentClassifier
    data = [("set an alarm for seven", "alarm_set"), ("wake me up at six", "alarm_set"),
            ("play some jazz", "play_music"), ("play my rock playlist", "play_music"),
            ("who wrote hamlet", "qa_factoid"), ("what is the capital of peru", "qa_factoid"),
            ("turn off the lights", "iot_hue_lightoff"), ("lights off please", "iot_hue_lightoff")] * 10
    c = IntentClassifier()
    c.train(data, epochs=6)
    c.save(tmp_path / "intent.json")
    d = DeviceRequests(tmp_path / "intent.json")
    import engramm.chat.device as dev
    old, dev.MIN_MARGIN = dev.MIN_MARGIN, 1.0
    try:
        assert d.group("set an alarm for seven") == ("reminders", "alarm_set")
        assert d.group("turn off the lights")[0] == "smarthome"
        assert d.group("who wrote hamlet") is None           # a question ENGRAMM can answer
    finally:
        dev.MIN_MARGIN = old


def test_speller():
    from engramm.nlp.spell import Speller
    sp = Speller({"the": 1000, "capital": 500, "capitol": 30, "of": 900, "france": 400, "what": 800, "is": 900,
                  "who": 600, "wrote": 300, "hamlet": 200, "whats": 50},
                 {"france": 0.99, "hamlet": 0.9}, min_count=20)
    assert sp.fix("whats teh capitol of frnace") == "what's the capital of france"
    assert sp.fix("WHO WROTE HAMLET") == "Who wrote Hamlet"
    assert sp.fix("Who wrote Hamlet?") == "Who wrote Hamlet?"
    assert sp.fix("My friend Xqzlor is here") == "My friend Xqzlor is here"      # names inside a sentence stay
    assert sp.fix_word("zz") == "zz" and sp.fix_word("xqzwvbn") == "xqzwvbn"
