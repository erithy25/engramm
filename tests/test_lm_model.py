"""HDCLanguageModel end to end on a tiny English corpus: consistency, learning,
exact forgetting, provenance, log replay, deterministic writing."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from engramm.lm.generate import Decoding, generate, longest_copied_run, sample_from
from engramm.lm.log import LoggedModel, replay_lm
from engramm.lm.model import COMPONENTS, HDCLanguageModel, MixtureSpec
from engramm.lm.stream import build_split
from engramm.lm.tokenizer import LMTokenizer

REPO = Path(__file__).resolve().parents[1]

SUBJ = ["The farmer", "A teacher", "My neighbour", "The old sailor", "Her brother", "The young doctor"]
VERB = ["bought", "found", "painted", "sold", "repaired", "carried"]
OBJ = ["a red boat", "the wooden table", "an old bicycle", "a small house", "the blue car", "a heavy box"]
WHEN = ["on Monday", "last week", "in the morning", "after lunch", "before the storm", "on Friday"]


def _corpus(n_docs=240, seed=0):
    rng = np.random.default_rng(seed)
    docs = []
    for _ in range(n_docs):
        sents = []
        for _ in range(int(rng.integers(2, 6))):
            sents.append(f"{rng.choice(SUBJ)} {rng.choice(VERB)} {rng.choice(OBJ)} {rng.choice(WHEN)}.")
        docs.append(" ".join(sents))
    return docs


@pytest.fixture(scope="module")
def tok():
    return LMTokenizer()


def _mixture():
    nb = 4 * 4 * 4
    return MixtureSpec(COMPONENTS, np.full((nb, 5), 0.2), np.array([2000, 4000, 8000]), 1024.0, 4.0)


@pytest.fixture(scope="module")
def model(tok):
    docs = _corpus()
    train = build_split(docs, [("toy", str(i)) for i in range(len(docs))], tok.encode_batch)
    return HDCLanguageModel.build(train, seed=42, mixture=_mixture(), tok=tok)


def test_distribution_is_normalised_and_matches_stream_evaluation(model, tok):
    ev = build_split(_corpus(4, seed=5), [("ev", str(i)) for i in range(4)], tok.encode_batch)
    e = np.asarray(ev.tokens)
    fast = model.stream_probs(e)
    for i in range(1, len(e)):
        p = model.next_distribution(e[:i])
        assert abs(p.sum() - 1.0) < 1e-9
        assert p[e[i]] == pytest.approx(fast[i - 1], rel=1e-9)


def test_learn_then_forget_is_exact(model, tok):
    fact_a = "The glass tower of Velmora was built by Quendrik Ashby in 1874."
    fact_b = "Old Tamsin keeps seven silver lanterns in her attic."
    canary = "My secret canary number is 4 8 1 5 1 6 2 3 4 2."
    probe = np.concatenate([[0], tok.encode(canary)]).astype(np.uint16)

    def canary_logprob():
        return sum(np.log2(model.next_distribution(probe[:i])[probe[i]]) for i in range(1, len(probe)))

    base_digest = model.state_digest()
    never = canary_logprob()
    model.learn_text(fact_a, "a")
    d_a = model.state_digest()
    model.learn_text(fact_b, "b")
    model.learn_text(canary, "canary")
    learned = canary_logprob()
    assert learned > never + 10                      # the canary was really learnt
    model.forget("canary")
    model.forget("b")
    assert model.state_digest() == d_a
    model.forget("a")
    assert model.state_digest() == base_digest
    assert canary_logprob() == never                 # bit-identical exposure


def test_learning_is_order_independent(model):
    model.learn_text("First text about a lighthouse.", "x1")
    model.learn_text("Second text about a harbour.", "x2")
    d1 = model.state_digest()
    model.forget("x1")
    model.forget("x2")
    model.learn_text("Second text about a harbour.", "x2")
    model.learn_text("First text about a lighthouse.", "x1")
    assert model.state_digest() == d1
    model.forget("x1")
    model.forget("x2")


def test_learned_fact_is_recalled_and_cited(model, tok):
    model.learn_text("The glass tower of Velmora was built by Quendrik Ashby.", "fact")
    prompt = np.concatenate([[0], tok.encode("The glass tower of Velmora was built by")]).astype(np.uint16)
    target = int(tok.encode(" Quendrik")[0])
    p = model.next_distribution(prompt)
    assert int(np.argmax(p)) == target
    why = model.why(prompt, target)
    assert why["verbatim"][0]["kind"] == "user" and why["verbatim"][0]["source"] == "fact"
    model.forget("fact")
    p2 = model.next_distribution(prompt)
    assert p2[target] < p[target] / 10


def test_base_forgetting_tombstones_then_consolidate_equals_rebuild(model, tok):
    docs = _corpus()
    special = "Nobody else ever wrote that the purple giraffe sang opera in Oslo."
    small_docs = docs[:40] + [special]
    keys = [("toy", str(i)) for i in range(40)] + [("toy", "special")]
    train = build_split(small_docs, keys, tok.encode_batch)
    m = HDCLanguageModel.build(train, seed=42, mixture=_mixture(), tok=tok)
    prompt = np.concatenate([[0], tok.encode("the purple giraffe sang opera in")]).astype(np.uint16)
    target = int(tok.encode(" Oslo")[0])
    assert m.why(prompt, target)["verbatim"][0]["key"] == "special"
    m.forget("toy\x00special")
    assert all(v.get("key") != "special" for v in m.why(prompt, target)["verbatim"])
    assert all(s.get("key") != "special" for s in m.why(prompt, target)["similar"])
    rebuilt = m.consolidate()
    ref = HDCLanguageModel.build(build_split(docs[:40], keys[:40], tok.encode_batch), seed=42,
                                 mixture=_mixture(), tok=tok, epoch=1)
    assert rebuilt.base_digest() == ref.base_digest()


def test_log_replay_reproduces_state(model, tmp_path):
    logged = LoggedModel(model, tmp_path / "user.log")
    logged.learn_text("Alpha text about rivers.", "s1")
    logged.learn_text("Beta text about mountains.", "s2")
    logged.forget("s1")
    digest = model.state_digest()
    logged.log.close()
    model.forget("s2")
    fresh = HDCLanguageModel(model.train, model.kn, model.index.sa, model.cb, model.pos, model.segsig,
                             model.mix, model.seed, model.tok)
    replayed, n, discarded = replay_lm(tmp_path / "user.log", fresh)
    assert n == 4 and discarded == 0
    assert replayed.state_digest() == digest


def test_writing_is_deterministic_and_respects_bans(model):
    g1 = generate(model, "The farmer", n_tokens=30, seed=7)
    g2 = generate(model, "The farmer", n_tokens=30, seed=7)
    g3 = generate(model, "The farmer", n_tokens=30, seed=8)
    assert g1.ids == g2.ids and g1.text == g2.text
    assert g1.ids != g3.ids
    seq = g1.ids
    grams = [tuple(seq[i:i + 4]) for i in range(len(seq) - 3)]
    assert len(grams) == len(set(grams))
    capped = generate(model, "The farmer", n_tokens=60, seed=1, dec=Decoding(quote_cap=6, no_repeat=0))
    assert longest_copied_run(model, capped.ids) <= 6 + 5     # prompt tokens may extend a run


def test_sampler_edge_cases():
    p = np.array([0.5, 0.3, 0.2])
    dec = Decoding(temperature=1.0, top_p=0.5)
    assert all(sample_from(p, u, dec, set()) == 0 for u in range(0, 2**64 - 1, 2**60))
    assert sample_from(p, 12345, Decoding(temperature=1.0, top_p=1.0), {0, 1}) == 2
    assert sample_from(p, 12345, Decoding(), {0, 1, 2}) in (0, 1, 2)


def test_independent_of_pythonhashseed(tmp_path):
    code = (
        "import numpy as np\n"
        "from tests.test_lm_model import _corpus, _mixture\n"
        "from engramm.lm.model import HDCLanguageModel\n"
        "from engramm.lm.stream import build_split\n"
        "from engramm.lm.tokenizer import LMTokenizer\n"
        "from engramm.lm.generate import generate\n"
        "tok = LMTokenizer(); docs = _corpus(60)\n"
        "tr = build_split(docs, [('toy', str(i)) for i in range(60)], tok.encode_batch)\n"
        "m = HDCLanguageModel.build(tr, seed=42, mixture=_mixture(), tok=tok)\n"
        "m.learn_text('A lighthouse keeper named Orla.', 'u')\n"
        "print(m.state_digest(), generate(m, 'The teacher', 20, seed=3).ids)\n"
    )
    outs = []
    for hs in ("0", "1"):
        env = {**os.environ, "PYTHONHASHSEED": hs, "PYTHONPATH": str(REPO)}
        r = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True, text=True,
                           timeout=600)
        assert r.returncode == 0, r.stderr
        outs.append(r.stdout)
    assert outs[0] == outs[1]


def test_cli_learn_write_why_forget(model, tmp_path, capsys):
    from engramm.lm.__main__ import main

    d = tmp_path / "model"
    model.save(d)
    assert main(["--model", str(d), "status"]) == 0
    base = capsys.readouterr().out
    assert main(["--model", str(d), "learn", "--source", "n1", "--text",
                 "The glass tower of Velmora was built by Quendrik Ashby."]) == 0
    assert main(["--model", str(d), "why", "The glass tower of Velmora was built by", " Quendrik"]) == 0
    assert '"source": "n1"' in capsys.readouterr().out
    assert main(["--model", str(d), "write", "The farmer", "--tokens", "8", "--seed", "3"]) == 0
    assert main(["--model", str(d), "forget", "n1"]) == 0
    capsys.readouterr()
    assert main(["--model", str(d), "status"]) == 0
    assert capsys.readouterr().out == base


def test_exploratory_writing_modes(model, tok):
    h = np.concatenate([[0], tok.encode("The farmer bought a red boat on Monday. The farmer")]).astype(np.uint16)
    _, d_off = model.next_distribution(h, detail=True, cache_until=1)
    assert np.array_equal(d_off["components"]["cache"], d_off["components"]["kn"])
    _, d_doc = model.next_distribution(h, detail=True)
    assert not np.array_equal(d_doc["components"]["cache"], d_doc["components"]["kn"])
    a = generate(model, "The farmer", 20, seed=2, dec=Decoding(cache="off", top_p=0.8))
    b = generate(model, "The farmer", 20, seed=2, dec=Decoding(cache="off", top_p=0.8))
    assert a.ids == b.ids
    with pytest.raises(ValueError):
        generate(model, "The farmer", 2, dec=Decoding(cache="nonsense"))
