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
