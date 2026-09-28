"""A read-only view of what ENGRAMM has read: the token stream, its documents and the
sentence index — loadable in about a second, without the language-model tables."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numba
import numpy as np

from engramm.lm.chat import SentenceIndex
from engramm.lm.semantic import Codebook
from engramm.lm.stream import TokenSplit
from engramm.lm.tokenizer import LMTokenizer

_WORD = re.compile(r"[0-9a-z]+")


def sentence_documents(starts: np.ndarray, doc_starts: np.ndarray) -> np.ndarray:
    return (np.searchsorted(doc_starts, starts, side="right") - 1).astype(np.int32)


@dataclass
class Corpus:
    tokens: np.ndarray                 # uint16 train stream (memory-mapped when loaded)
    doc_starts: np.ndarray             # int64
    doc_keys: list[tuple[str, str]]    # (source, key): ("wiki", title) or ("c4", url)
    tok: LMTokenizer
    eng: np.ndarray                    # uint64 (V, 32) meaning vectors
    index: SentenceIndex
    sent_doc: np.ndarray = field(default=None)
    doc_ptr: np.ndarray | None = None       # term → documents (v2 index)
    doc_post: np.ndarray | None = None
    wide: np.ndarray | None = None          # uint64 (V, 32) topical meaning vectors (±16 words)
    classes: np.ndarray | None = None       # HDC word class per token (512 classes)
    index_dir: Path | None = None
    _key_words: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.sent_doc is None:
            self.sent_doc = sentence_documents(np.asarray(self.index.starts), np.asarray(self.doc_starts))

    @classmethod
    def load(cls, model_dir: Path, tok: LMTokenizer | None = None, mmap: bool = True,
             index_name: str = "chat2") -> Corpus:
        model_dir = Path(model_dir)
        train = TokenSplit.load(model_dir, "train", mmap=True)
        cb = Codebook.load(model_dir / "codebook.npz")
        c = cls.with_index(train.tokens, train.doc_starts, train.doc_keys, tok or LMTokenizer(), cb.eng,
                           model_dir.parent / index_name, mmap)
        c.wide, c.classes = cb.wide, cb.classes
        return c

    @classmethod
    def with_index(cls, tokens, doc_starts, doc_keys, tok, eng, index_dir: Path, mmap: bool = True) -> Corpus:
        index_dir = Path(index_dir)
        if (index_dir / "segment.json").exists():
            return cls.with_segment(tokens, doc_starts, doc_keys, tok, eng, index_dir, mmap)
        if (index_dir / "corpus.u16").exists():
            # an index over a larger corpus (the train stream plus more reading, chat3): its own token stream
            tokens = np.memmap(index_dir / "corpus.u16", dtype=np.uint16, mode="r")
            doc_starts = np.load(index_dir / "corpus.starts.npy")
            with open(index_dir / "corpus.keys.jsonl", encoding="utf-8") as f:
                doc_keys = [tuple(json.loads(line)) for line in f]
        index = SentenceIndex.load(index_dir, mmap=mmap)
        if (index_dir / "doc_ptr.npy").exists():
            from engramm.chat.index import load_docs
            dptr, dpost, sent_doc = load_docs(index_dir, mmap)
            c = cls(tokens, doc_starts, doc_keys, tok, eng, index, np.asarray(sent_doc), dptr, dpost)
        else:
            c = cls(tokens, doc_starts, doc_keys, tok, eng, index)
        c.index_dir = Path(index_dir)
        return c

    @classmethod
    def with_segment(cls, tokens, doc_starts, doc_keys, tok, eng, index_dir: Path, mmap: bool = True) -> Corpus:
        """A base index plus one more read segment (``segment.json``: {"base": <index name>}).

        The segment is indexed on its own (sentence ids, token positions and documents relative
        to the segment). Loading appends it to the base in memory: tokens, documents and
        sentences follow those of the base, and every term's postings list is the base list
        followed by the segment list. The result equals an index built over the concatenated
        stream, as long as the base ends with a document end."""
        from engramm.chat.index import load_docs
        index_dir = Path(index_dir)
        meta = json.loads((index_dir / "segment.json").read_text())
        base = cls.with_index(tokens, doc_starts, doc_keys, tok, eng, index_dir.parent / meta["base"], mmap=True)
        seg_tokens = np.fromfile(index_dir / "segment.u16", dtype=np.uint16)
        seg_starts = np.load(index_dir / "segment.starts.npy")
        with open(index_dir / "segment.keys.jsonl", encoding="utf-8") as f:
            seg_keys = [tuple(json.loads(line)) for line in f]
        six = SentenceIndex.load(index_dir, mmap=False)
        sdptr, sdpost, ssent_doc = load_docs(index_dir, mmap=False)
        bix = base.index
        if not np.array_equal(np.asarray(bix.term_of), six.term_of) or list(bix.terms) != list(six.terms):
            raise ValueError("segment and base use different term tables")
        n_tok, n_sent, n_doc = len(base.tokens), bix.n, base.n_docs
        if n_tok and int(base.tokens[n_tok - 1]) != 0:
            raise ValueError("the base stream must end with a document end")
        index = SentenceIndex(
            starts=np.concatenate([np.asarray(bix.starts), six.starts.astype(np.int64) + n_tok]),
            lens=np.concatenate([np.asarray(bix.lens), six.lens]),
            ptr=np.asarray(bix.ptr) + six.ptr,
            post=merge_postings(np.asarray(bix.ptr), bix.post, six.ptr, six.post, n_sent),
            sent_terms=np.concatenate([np.asarray(bix.sent_terms), six.sent_terms]),
            term_of=np.asarray(bix.term_of), terms=list(bix.terms))
        c = cls(np.concatenate([np.asarray(base.tokens), seg_tokens]),
                np.concatenate([np.asarray(base.doc_starts), seg_starts.astype(np.int64) + n_tok]),
                list(base.doc_keys) + seg_keys, tok, eng, index,
                np.concatenate([np.asarray(base.sent_doc), np.asarray(ssent_doc, dtype=np.int32) + n_doc]),
                np.asarray(base.doc_ptr) + sdptr,
                merge_postings(np.asarray(base.doc_ptr), base.doc_post, sdptr, sdpost, n_doc))
        c.index_dir = index_dir
        return c

    @classmethod
    def from_model(cls, model, index_dir: Path, mmap: bool = True) -> Corpus:
        c = cls.with_index(model.tokens, model.train.doc_starts, model.train.doc_keys, model.tok, model.cb.eng,
                           Path(index_dir), mmap)
        c.wide, c.classes = model.cb.wide, model.cb.classes
        return c

    @property
    def n_docs(self) -> int:
        return len(self.doc_starts)

    def doc_sentences(self, d: int) -> tuple[int, int]:
        """[first, last + 1) sentence ids of document d."""
        lo = int(np.searchsorted(self.sent_doc, d, side="left"))
        hi = int(np.searchsorted(self.sent_doc, d, side="right"))
        return lo, hi

    # -- sentences ------------------------------------------------------------------------

    def sentence_tokens(self, s: int) -> np.ndarray:
        st = int(self.index.starts[s])
        return np.asarray(self.tokens[st:st + int(self.index.lens[s])])

    def sentence_text(self, s: int) -> str:
        return self.tok.decode(self.sentence_tokens(s)).strip()

    def previous(self, s: int) -> int:
        """The preceding sentence of the same document, or −1."""
        return s - 1 if s > 0 and self.sent_doc[s - 1] == self.sent_doc[s] else -1

    def source(self, s: int) -> dict:
        d = int(self.sent_doc[s])
        src, key = self.doc_keys[d]
        return {"kind": "base", "source": src, "key": key,
                "token_offset": int(self.index.starts[s]) - int(self.doc_starts[d])}

    def key_words(self, d: int) -> frozenset:
        """Lower-case words of a document's title (Wikipedia) or URL path (web)."""
        w = self._key_words.get(d)
        if w is None:
            src, key = self.doc_keys[d]
            if src == "c4":
                key = re.sub(r"^https?://(www\.)?", "", key)
            w = frozenset(_WORD.findall(key.lower()))
            self._key_words[d] = w
        return w


@numba.njit(cache=True)
def _merge_postings(pa, qa, pb, qb, offset, out):
    k = 0
    for t in range(len(pa) - 1):
        for i in range(pa[t], pa[t + 1]):
            out[k] = qa[i]
            k += 1
        for i in range(pb[t], pb[t + 1]):
            out[k] = qb[i] + offset
            k += 1


def merge_postings(pa: np.ndarray, qa: np.ndarray, pb: np.ndarray, qb: np.ndarray, offset: int) -> np.ndarray:
    """CSR postings of two indexes over the same terms: per term, list a, then list b + offset."""
    out = np.empty(len(qa) + len(qb), dtype=np.int32)
    _merge_postings(np.asarray(pa, dtype=np.int64), np.asarray(qa), np.asarray(pb, dtype=np.int64),
                    np.asarray(qb), np.int64(offset), out)
    return out


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text())
