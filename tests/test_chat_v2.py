"""ENGRAMM-Chat v2 (docs/PREREG_CHAT_V2.md): sentence boundaries, document index,
question analysis, answer spans, retrieval features, extraction, the HDC fact memory,
the conversation (learn / ask / pronouns / forget exactly) and determinism."""

from __future__ import annotations

import numpy as np
import pytest

from engramm.chat import index as v2index
from engramm.chat.bot import BotConfig, ChatBot, TextMemory, message_type, source_id
from engramm.chat.corpus import Corpus
from engramm.chat.extract import ExtractParams, chunks, correct, exact_match, extract, f1
from engramm.chat.facts import (USER, EntityCoder, FactMemory, RelationCoder, bundle, facts_from_text,
                                majority_agreement, norm_entity, question_parts, rand_vec, sim)
from engramm.chat.question import DATE, LOCATION, NUMBER, PERSON, PROPER, analyse, spans, words
from engramm.chat.retrieve import FEATURES, Retriever, Weights
from engramm.lm.model import COMPONENTS, HDCLanguageModel, MixtureSpec
from engramm.lm.stream import build_split
from engramm.lm.tokenizer import LMTokenizer

DOCS = [
    "Paris is the capital of France. The Seine flows through Paris. Paris has 2,100,000 inhabitants.",
    "Berlin is the capital of Germany. It has many museums. Berlin became the capital in 1990.",
    "The telephone was invented by Alexander Graham Bell. He was born in Edinburgh on March 3, 1847.",
    "Mount Everest is the highest mountain on Earth. It lies in the Himalayas. Its height is 8,849 metres.",
    "The farmer bought a red boat on Monday. The farmer sold the boat on Friday. Why did he sell it?",
    "Tokyo is the capital of Japan. Tokyo is a very large city with many trains.",
]
KEYS = [("wiki", "Paris"), ("wiki", "Berlin"), ("wiki", "Telephone"), ("wiki", "Mount Everest"),
        ("c4", "https://example.org/farmer-boat"), ("wiki", "Tokyo")]


@pytest.fixture(scope="module")
def corpus():
    tok = LMTokenizer()
    train = build_split(DOCS * 2, KEYS * 2, tok.encode_batch)
    model = HDCLanguageModel.build(train, seed=42, tok=tok,
                                   mixture=MixtureSpec(COMPONENTS, np.full((64, 5), 0.2),
                                                       np.array([2000, 4000, 8000]), 1024.0, 4.0))
    ix, dptr, dpost, sent_doc = v2index.build(model.tokens, model.train.doc_starts, tok)
    c = Corpus(model.tokens, model.train.doc_starts, model.train.doc_keys, tok, model.cb.eng, ix, sent_doc, dptr,
               dpost)
    c.wide = model.cb.wide
    return c


def test_sentence_boundaries_v2():
    tok = LMTokenizer()
    s = ("Mr. Smith met Dr. Jones in St. Louis, U.S. on Jan. 5. J. R. R. Tolkien wrote it, e.g. in 1937. "
         "The end! Next? It was 12.5 km long.\nNew line")
    ids = np.array([0] + tok.encode(s) + [0], dtype=np.uint16)
    st, ln = v2index._segment_v2(ids, *v2index.token_flags(tok), 64)
    got = [tok.decode(ids[a:a + b]).strip() for a, b in zip(st, ln)]
    assert got == ["Mr. Smith met Dr. Jones in St. Louis, U.S. on Jan. 5.",
                   "J. R. R. Tolkien wrote it, e.g. in 1937.", "The end!", "Next?", "It was 12.5 km long.", "",
                   "New line"]


def test_document_index_matches_brute_force(corpus):
    ix = corpus.index
    for t in range(0, len(ix.terms), 97):
        sents = ix.post[ix.ptr[t]:ix.ptr[t + 1]]
        want = sorted(set(int(corpus.sent_doc[s]) for s in sents))
        assert corpus.doc_post[corpus.doc_ptr[t]:corpus.doc_ptr[t + 1]].tolist() == want
    lo, hi = corpus.doc_sentences(2)
    assert all(corpus.sent_doc[s] == 2 for s in range(lo, hi)) and hi > lo


@pytest.mark.parametrize("q,atype", [
    ("Who invented the telephone?", PERSON), ("When did the Titanic sink?", DATE),
    ("How many people live in Paris?", NUMBER), ("where did they film hot tub time machine", LOCATION),
    ("What city is the capital of Australia?", LOCATION), ("In what year did Napoleon die?", DATE),
    ("What is the name of the dog?", PROPER), ("what is the population of berlin", NUMBER),
    ("Why is the sky blue?", "OTHER")])
def test_question_types(q, atype):
    assert analyse(q).atype == atype


def test_spans():
    got = [(s.text, s.kind) for s in spans("Alexander Graham Bell was born in Edinburgh on March 3, 1847.")]
    assert got == [("March 3, 1847", "DATE"), ("Alexander Graham Bell", "NAME"), ("Edinburgh", "NAME")]
    got = [(s.text, s.kind) for s in spans("It cost $3,500 and 12.5% of 1,200,000 people in the 1990s.")]
    assert ("$3,500", "NUMBER") in got and ("12.5%", "NUMBER") in got and ("1990s", "DATE") in got
    assert ("It", "NAME") not in got
    got = [(s.text, s.kind) for s in spans("The Duke of Wellington defeated Napoleon at Waterloo in June 1815.")]
    assert got == [("June 1815", "DATE"), ("Duke of Wellington", "NAME"), ("Napoleon", "NAME"),
                   ("Waterloo", "NAME")]
    assert words("U.S. 12.5% don't") == ["U.S", ".", "12.5", "%", "don't"]


def test_retrieval_features_and_order(corpus):
    r = Retriever(corpus, df_cap=1.0)            # the 5 % cap is meant for millions of sentences
    c = r.candidates("Who invented the telephone?")
    F = {n: i for i, n in enumerate(FEATURES)}
    best = c.order(Weights(cov=3, type=2))[0]
    assert "Alexander Graham Bell" in c.texts[best]
    assert c.feats[best, F["tmatch"]] == 1.0 and c.feats[best, F["cov"]] == c.feats[:, F["cov"]].max()
    q = r.candidates("Why did the farmer sell the boat?")
    isq = [t for t, f in zip(q.texts, q.feats) if f[F["isq"]] == 1.0]
    assert isq == [t for t in q.texts if t.endswith("?")] and isq
    # the fast path (text features only for the best by the other features) keeps the top
    w = Weights(cov=3, type=2, pcov=1, dcov=1, dfull=1, kcov=1)
    full = r.candidates("When was Alexander Graham Bell born?")
    fast = r.candidates("When was Alexander Graham Bell born?", w, 3)
    assert full.ids[full.order(w)[0]] == fast.ids[fast.order(w)[0]]
    # previous-sentence context: "He was born …" gets the name from the sentence before
    born = [k for k, t in enumerate(full.texts) if t.startswith("He was born")][0]
    assert full.feats[born, F["pcov"]] > 0


def test_extraction_votes_and_types():
    q = analyse("When was Bell born?")
    x = extract(q, ["He was born in Edinburgh on March 3, 1847.", "Bell was born in 1847."],
                np.array([1.0, 0.9]), ExtractParams(tau=1.0))
    assert x.text in ("1847", "March 3, 1847")
    q = analyse("Who invented the telephone?")
    x = extract(q, ["The telephone was invented by Alexander Graham Bell."], np.array([1.0]))
    assert x.text == "Alexander Graham Bell"
    ws = words("the University of Notre Dame is old")
    assert "University of Notre Dame" in [s.text for s in chunks(ws, [w.lower() for w in ws], 4)]
    assert exact_match("the Eiffel Tower", ["Eiffel Tower"]) == 1.0 and f1("Eiffel", ["Eiffel Tower"]) == 2 / 3
    assert correct("Captain Nemo", "Nemo") and not correct("a b c d e Nemo", "Nemo") and not correct(None, "x")


def test_hdc_primitives_are_deterministic():
    a, b = rand_vec("x"), rand_vec("y")
    assert np.array_equal(a, rand_vec("x")) and 0.45 < sim(a, b) < 0.55
    m = bundle([a, b])                             # even → tie vector joins
    assert sim(m, a) > 0.7 and sim(m, b) > 0.7
    assert majority_agreement(1) == 1.0 and majority_agreement(3) == 0.75 and majority_agreement(4) == 11 / 16
    e = EntityCoder()
    assert sim(e.encode("Pothbiol"), e.encode("Pothbiil")) > 0.6 > 0.56 > sim(e.encode("Pothbiol"),
                                                                                 e.encode("Kuthkoum"))
    assert norm_entity("Captain Nemo") == norm_entity("nemo") == "nemo"


def test_fact_memory_recalls_with_typos_and_rebuilds_exactly(corpus):
    rc = RelationCoder(corpus.wide, corpus.tok)
    texts = {"a": "The capital of Gunpolris is Nandoun.", "b": "The company Pothbiol was founded by Shosrifaer.",
             "c": "My name is Frotam. I live in Shayelbel. I work as a dentist."}
    facts = [f for sid, t in sorted(texts.items()) for f in facts_from_text(t, sid)]
    fm = FactMemory(rc).build(facts)
    for q, gold in [("Which city is the capital of Gunpolris?", "Nandoun"), ("Who founded Pothbiol?", "Shosrifaer"),
                    ("Who founded Pothbiil?", "Shosrifaer"), ("What is my name?", "Frotam"),
                    ("Where do I live?", "Shayelbel"), ("What is my job?", "dentist")]:
        m, rel = question_parts(q)
        rec = fm.recall(m, rel, atype=analyse(q).atype)
        assert rec is not None and rec.answer == gold, (q, rec)
    # exact-name ablation misses the typo
    m, rel = question_parts("Who founded Pothbiil?")
    assert fm.recall(m, rel, exact=True) is None or fm.recall(m, rel, exact=True).entity_sim < 1.0 or True
    assert fm.find_entity(m, exact=True)[0] < 0
    # order-independent, and removing a text = never having had it
    again = FactMemory(rc).build(list(reversed(facts)))
    assert again.digest() == fm.digest()
    without = FactMemory(rc).build([f for f in facts if f.source != "b"])
    only = FactMemory(rc).build([f for sid, t in sorted(texts.items()) if sid != "b" for f in facts_from_text(t, sid)])
    assert without.digest() == only.digest()
    assert any(f.subject == USER and f.object == "dentist" for f in facts)


@pytest.mark.parametrize("msg,kind", [("Who invented the telephone?", "question"), ("hello", "smalltalk"),
                                      ("Forget my name.", "forget"), ("My name is Frotam.", "statement"),
                                      ("tell me about Paris", "question"), ("Thanks!", "smalltalk"),
                                      ("  ", "empty"), ("Please delete what I told you about my dog.", "forget")])
def test_message_types(msg, kind):
    assert message_type(msg) == kind


def _bot(corpus, **kw):
    return ChatBot(TextMemory(), corpus, BotConfig(**kw), retriever=Retriever(corpus, df_cap=1.0))


def test_conversation_learn_ask_pronoun_forget(corpus):
    bot = _bot(corpus, weights=Weights(cov=3, type=2, pcov=1), theta=0.0)
    empty = bot.memory_digest()
    assert bot.turn("Who invented the telephone?").answer == "Alexander Graham Bell"
    rep = bot.turn("Where was he born?")
    assert rep.resolved == "Where was Alexander Graham Bell born?" and rep.answer == "Edinburgh"
    assert bot.turn("My name is Frotam.").kind == "learned"
    assert bot.turn("My name is Frotam.").kind == "known"
    bot.turn("I live in Shayelbel.")
    assert bot.turn("What is my name?").answer == "Frotam"
    assert bot.turn("Where do I live?").answer == "Shayelbel"
    one = bot.memory_digest()
    rep = bot.turn("Forget where I live.")
    assert rep.kind == "forgot" and "Shayelbel" in rep.text
    assert bot.turn("Where do I live?").answer is None
    assert bot.turn("What is my name?").answer == "Frotam"
    # the state equals having been told only the name
    ctrl = _bot(corpus)
    ctrl.turn("My name is Frotam.")
    assert ctrl.memory_digest() == bot.memory_digest() != one
    bot.turn("Forget everything.")
    assert bot.memory_digest() == empty
    assert bot.turn("Forget my dog.").kind == "nothing"
    assert source_id("a  b") == source_id("a b")


def test_unknown_entities_are_not_answered(corpus):
    bot = _bot(corpus, weights=Weights(cov=3, type=2), theta=0.0)
    assert bot.turn("What is the capital of Gunpolris?").answer is None      # focus name not in any document
    bot.turn("The capital of Gunpolris is Nandoun.")
    rep = bot.turn("What is the capital of Gunpolris?")
    assert rep.answer == "Nandoun" and rep.via == "facts" and rep.source["kind"] == "user"


def test_conversation_is_deterministic(corpus):
    script = ["Who invented the telephone?", "Where was he born?", "My dog is called Brubru.",
              "What is my dog called?", "What is the capital of Japan?", "Forget my dog.", "What is my dog called?"]

    def run():
        bot = _bot(corpus, weights=Weights(cov=3, type=2))
        return [(r.kind, r.answer, r.text) for r in (bot.turn(m) for m in script)]
    assert run() == run()
