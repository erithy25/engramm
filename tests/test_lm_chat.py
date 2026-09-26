"""ENGRAMM-Chat stage 1: sentence index, BM25 against brute force, HDC re-ranking,
user texts, abstaining, answer checking."""

from __future__ import annotations

import math

import numpy as np
import pytest

from engramm.lm.chat import (B, K1, ChatEngine, SentenceIndex, contains_answer, normalize, term_table, top_k)
from engramm.lm.model import COMPONENTS, HDCLanguageModel, MixtureSpec
from engramm.lm.stream import build_split
from engramm.lm.tokenizer import LMTokenizer

DOCS = [
    "Paris is the capital of France. The Seine flows through Paris.",
    "Berlin is the capital of Germany. It has many museums.",
    "The telephone was invented by Alexander Graham Bell. He was born in Edinburgh.",
    "Mount Everest is the highest mountain on Earth. It lies in the Himalayas.",
    "The farmer bought a red boat on Monday. The farmer sold the boat on Friday.",
] * 3


@pytest.fixture(scope="module")
def setup():
    tok = LMTokenizer()
    train = build_split(DOCS, [("toy", str(i)) for i in range(len(DOCS))], tok.encode_batch)
    model = HDCLanguageModel.build(train, seed=42, tok=tok,
                                   mixture=MixtureSpec(COMPONENTS, np.full((64, 5), 0.2),
                                                       np.array([2000, 4000, 8000]), 1024.0, 4.0))
    index = SentenceIndex.build(model.tokens, tok)
    return tok, model, index


def test_segmentation_and_terms(setup):
    tok, model, index = setup
    texts = [tok.decode(model.tokens[s:s + n]).strip() for s, n in zip(index.starts, index.lens)]
    assert texts[0] == "Paris is the capital of France." and texts[1] == "The Seine flows through Paris."
    assert len(texts) == 10 * 3
    term_of, terms, ends = term_table(tok)
    assert len(tok.encode(" the")) == len(tok.encode("The")) == 1
    assert term_of[tok.encode(" the")[0]] == term_of[tok.encode("The")[0]]   # case/space-insensitive
    assert term_of[tok.encode(".")[0]] == -1


def test_bm25_matches_brute_force(setup):
    tok, model, index = setup
    eng = ChatEngine(model, index, df_cap=1.0)
    q = "Who invented the telephone?"
    qterms, qidf, _ = eng._query(q)
    rows, _, _ = eng.rank(q, alpha=0.0, top=100)
    got = {r[4]: r[1] for r in rows}
    avg = index.sent_terms.mean()
    for s in range(index.n):
        st, n = index.starts[s], index.lens[s]
        present = {int(index.term_of[t]) for t in model.tokens[st:st + n] if index.term_of[t] >= 0}
        norm = K1 * (1 - B + B * index.sent_terms[s] / avg)
        want = sum(w * (K1 + 1) / (1 + norm) for t, w in zip(qterms, qidf) if int(t) in present)
        if want > 0:
            assert got[s] == pytest.approx(want, rel=1e-12)
        else:
            assert s not in got


def test_answers_with_source_and_is_deterministic(setup):
    tok, model, index = setup
    eng = ChatEngine(model, index, alpha=1.0, df_cap=1.0)
    a = eng.answer("Who invented the telephone?")
    assert "Alexander Graham Bell" in a.text and a.source["kind"] == "base"
    assert eng.answer("Who invented the telephone?").text == a.text
    assert "Paris" in eng.answer("What is the capital of France?").text


def test_user_texts_are_searched_and_forgotten(setup):
    tok, model, index = setup
    eng = ChatEngine(model, index, alpha=1.0, df_cap=1.0)
    model.learn_text("The glass tower of Velmora was built by Quendrik Ashby.", "velmora")
    a = eng.answer("Who built the glass tower of Velmora?")
    assert a.source == {"kind": "user", "source": "velmora"} and "Quendrik" in a.text
    model.forget("velmora")
    b = eng.answer("Who built the glass tower of Velmora?")
    assert b.source is None or b.source.get("kind") != "user"


def test_abstains_below_threshold(setup):
    tok, model, index = setup
    eng = ChatEngine(model, index, theta=1e9, df_cap=1.0)
    a = eng.answer("What is the capital of France?")
    assert a.text is None and a.candidates           # still shows what it found
    assert ChatEngine(model, index, df_cap=1.0).answer("???").text is None
    # the registered 5 % cap drops terms that are in too many sentences
    capped = ChatEngine(model, index)
    assert len(capped._query("the capital of France")[0]) < len(ChatEngine(model, index, df_cap=1.0)._query("the capital of France")[0])


def test_top_k_is_deterministic_with_ties():
    ids = np.array([5, 3, 9, 1, 7])
    sc = np.array([1.0, 2.0, 1.0, 1.0, 0.5])
    i, s = top_k(ids, sc, 3)
    assert i.tolist() == [3, 1, 5] and s.tolist() == [2.0, 1.0, 1.0]


def test_answer_normalisation():
    assert normalize("The  Eiffel-Tower!") == "eiffeltower"          # official SQuAD rule
    assert contains_answer("It was built by Gustave Eiffel in 1889.", ["Gustave Eiffel"])
    assert not contains_answer("It was built in 18899.", ["1889"])
    assert contains_answer("the answer is An Apple", ["apple"])
    assert not math.isnan(0.0)
