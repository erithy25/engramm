"""A base index plus a read segment equals one index over the concatenated stream."""

from __future__ import annotations

import json

import numpy as np

from engramm.chat import index as v2
from engramm.chat.corpus import Corpus, merge_postings
from engramm.lm.tokenizer import EOS, LMTokenizer

BASE_DOCS = [("wiki", "Alpha"), ("wikipedia", "Beta")]
BASE_TEXT = ["The river Alpha flows north. It passes the old mill.\nMr. Smith built the mill in 1820.",
             "Beta is a small town. The town has 3.5 thousand people! Is it old? Yes."]
SEG_DOCS = [("wikipedia", "Gamma"), ("wikipedia", "Delta")]
SEG_TEXT = ["Gamma was founded by Smith. The river flows past Gamma.",
            "Delta has a mill.\nThe mill of Delta is older than the mill of Alpha."]


def _stream(tok, texts):
    parts, starts, pos = [], [], 0
    for t in texts:
        ids = np.asarray(tok.encode(t), dtype=np.uint16)
        ids = ids[ids != EOS]
        starts.append(pos)
        parts += [ids, np.array([EOS], dtype=np.uint16)]
        pos += len(ids) + 1
    return np.concatenate(parts), np.asarray(starts, dtype=np.int64)


def _write(d, tokens, starts, keys, tok, prefix):
    d.mkdir(parents=True, exist_ok=True)
    tokens.tofile(d / f"{prefix}.u16")
    np.save(d / f"{prefix}.starts.npy", starts)
    with open(d / f"{prefix}.keys.jsonl", "w", encoding="utf-8") as f:
        for k in keys:
            f.write(json.dumps(list(k)) + "\n")
    ix, dptr, dpost, sent_doc = v2.build(tokens, starts, tok)
    v2.save(d, ix, dptr, dpost, sent_doc, {})


def test_merge_postings():
    pa, qa = np.array([0, 2, 2, 3]), np.array([0, 4, 1], dtype=np.int32)
    pb, qb = np.array([0, 1, 2, 2]), np.array([0, 1], dtype=np.int32)
    assert merge_postings(pa, qa, pb, qb, 10).tolist() == [0, 4, 10, 11, 1]


def test_segment_equals_full_build(tmp_path):
    tok = LMTokenizer()
    bt, bs = _stream(tok, BASE_TEXT)
    st, ss = _stream(tok, SEG_TEXT)
    _write(tmp_path / "base", bt, bs, BASE_DOCS, tok, "corpus")
    _write(tmp_path / "seg", st, ss, SEG_DOCS, tok, "segment")
    (tmp_path / "seg" / "segment.json").write_text(json.dumps({"base": "base"}))
    ft = np.concatenate([bt, st])
    fs = np.concatenate([bs, ss + len(bt)])
    _write(tmp_path / "full", ft, fs, BASE_DOCS + SEG_DOCS, tok, "corpus")
    eng = np.zeros((1, 1), dtype=np.uint64)
    a = Corpus.with_index(None, None, None, tok, eng, tmp_path / "seg", mmap=False)
    b = Corpus.with_index(None, None, None, tok, eng, tmp_path / "full", mmap=False)
    assert np.array_equal(np.asarray(a.tokens), np.asarray(b.tokens))
    assert np.array_equal(a.doc_starts, b.doc_starts)
    assert [tuple(k) for k in a.doc_keys] == [tuple(k) for k in b.doc_keys]
    for name in ("starts", "lens", "ptr", "post", "sent_terms", "term_of"):
        assert np.array_equal(np.asarray(getattr(a.index, name)), np.asarray(getattr(b.index, name))), name
    assert np.array_equal(a.sent_doc, np.asarray(b.sent_doc))
    assert np.array_equal(a.doc_ptr, np.asarray(b.doc_ptr))
    assert np.array_equal(a.doc_post, np.asarray(b.doc_post))
    assert a.sentence_text(a.index.n - 1) == b.sentence_text(b.index.n - 1)


def test_materialized_equals_segment_merge(tmp_path):
    """chat4m: base + segment written as one index on disk equals the in-memory merge."""
    from engramm.chat.corpus import materialize
    tok = LMTokenizer()
    bt, bs = _stream(tok, BASE_TEXT)
    st, ss = _stream(tok, SEG_TEXT)
    _write(tmp_path / "base", bt, bs, BASE_DOCS, tok, "corpus")
    _write(tmp_path / "seg", st, ss, SEG_DOCS, tok, "segment")
    (tmp_path / "seg" / "segment.json").write_text(json.dumps({"base": "base"}))
    (tmp_path / "seg" / "spanperc_x.json").write_text("{}")
    out = materialize(tmp_path / "seg", tmp_path / "segm", chunk=7)
    eng = np.zeros((1, 1), dtype=np.uint64)
    a = Corpus.with_index(None, None, None, tok, eng, tmp_path / "seg", mmap=False)
    b = Corpus.with_index(None, None, None, tok, eng, out, mmap=True)
    assert isinstance(b.index.post, np.memmap) and isinstance(b.tokens, np.memmap)
    assert np.array_equal(np.asarray(a.tokens), np.asarray(b.tokens))
    assert np.array_equal(a.doc_starts, b.doc_starts)
    assert [tuple(k) for k in a.doc_keys] == [tuple(k) for k in b.doc_keys]
    for name in ("starts", "lens", "ptr", "post", "sent_terms", "term_of"):
        assert np.array_equal(np.asarray(getattr(a.index, name)), np.asarray(getattr(b.index, name))), name
    assert np.array_equal(a.sent_doc, np.asarray(b.sent_doc))
    assert np.array_equal(a.doc_ptr, np.asarray(b.doc_ptr))
    assert np.array_equal(a.doc_post, np.asarray(b.doc_post))
    assert (out / "spanperc_x.json").exists()
    assert json.loads((out / "info.json").read_text())["materialized_from"] == "seg"
