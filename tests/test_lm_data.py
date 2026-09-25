"""Corpus extraction, splits, tokenizer round trip, token streams, BPB harness."""

from __future__ import annotations

import numpy as np
import pytest

from data.lm_corpus import SPLITS, detokenize_wikitext, split_half, split_of, _heading
from engramm.lm.evaluate import bpb, bpb_ratio, per_doc_bits
from engramm.lm.stream import TokenSplit, build_split
from engramm.lm.tokenizer import EOS, VOCAB_SIZE, LMTokenizer

TRICKY = [
    "Hello, world!", "  leading and trailing spaces  ", "tabs\tand\nnewlines\r\n",
    "Ünïcödé — “quotes” and emojis 😀🚀", "中文字符和日本語のテキスト", "a" * 500,
    "numbers 3.14159 and 1,000,000", "<|eos|> is only special as id 0", "x", "",
    "mixed​zero width nbsp", "\x00 control \x07 chars",
]


@pytest.fixture(scope="module")
def tok():
    return LMTokenizer()


def test_tokenizer_is_pinned_and_sized(tok):
    assert tok.vocab_size == VOCAB_SIZE
    assert tok._tok.token_to_id("<|eos|>") == EOS


@pytest.mark.parametrize("text", TRICKY)
def test_round_trip_is_lossless(tok, text):
    ids = tok.encode(text)
    assert ids.dtype == np.uint16
    assert tok.decode(ids) == text


def test_literal_eos_text_is_not_the_eos_token(tok):
    assert EOS not in tok.encode("<|eos|>").tolist()


def test_token_bytes_concatenate_to_the_text(tok):
    table = tok.token_bytes()
    for text in TRICKY:
        assert b"".join(table[i] for i in tok.encode(text)) == text.encode("utf-8")


def test_split_is_a_pure_function_of_identity():
    assert split_of("c4", "https://example.org/a") == split_of("c4", "https://example.org/a")
    counts = {s: 0 for s in SPLITS}
    for i in range(20000):
        counts[split_of("c4", f"k{i}")] += 1
    assert 0.985 < counts["train"] / 20000 < 0.998
    assert all(counts[s] > 0 for s in SPLITS)
    assert {split_half("c4", f"k{i}") for i in range(50)} == {0, 1}


def test_wikitext_detokenisation():
    raw = " The game 's theme , by May 'n . It is 1 @,@ 000 and 3 @.@ 5 % ( see below ) ; a @-@ b "
    assert detokenize_wikitext(raw) == "The game's theme, by May 'n. It is 1,000 and 3.5% (see below); a-b"
    assert _heading(" = Valkyria Chronicles III = ") == (1, "Valkyria Chronicles III")
    assert _heading(" = = History = = ") == (2, "History")
    assert _heading(" a = b ") is None


def test_stream_layout(tok):
    texts = ["Hello there.", "Second document!", "x"]
    s = build_split(texts, [("t", str(i)) for i in range(3)], tok.encode_batch)
    assert s.tokens[0] == EOS and s.tokens[-1] == EOS
    assert int((s.tokens == EOS).sum()) == 4
    for i, t in enumerate(texts):
        assert tok.decode(s.doc_tokens(i)) == t
        assert s.tokens[s.doc_end(i)] == EOS
    p = s.prefix(int(s.doc_starts[2]))
    assert p.n_docs == 2 and p.tokens[-1] == EOS
    sel = s.select(np.array([2, 0]))
    assert tok.decode(sel.doc_tokens(0)) == "x" and tok.decode(sel.doc_tokens(1)) == texts[0]


def test_bpb_accounting(tok):
    texts = ["abc def", "ghi"]
    s = build_split(texts, [("t", "0"), ("t", "1")], tok.encode_batch)
    probs = np.full(len(s.tokens) - 1, 0.5)
    bits = per_doc_bits(s, probs)
    assert bits.sum() == pytest.approx(len(s.tokens) - 1)
    nbytes = s.doc_bytes + 1.0
    r = bpb(bits, nbytes, reps=50)
    assert r.value == pytest.approx((len(s.tokens) - 1) / (7 + 1 + 3 + 1))
    assert bpb_ratio(bits, bits, reps=20)["ratio"] == 1.0
    with pytest.raises(ValueError):
        per_doc_bits(s, np.zeros(len(s.tokens) - 1))
