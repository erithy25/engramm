"""A read-only view of what ENGRAMM has read: the token stream, its documents and the
sentence index — loadable in about a second, without the language-model tables."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

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
        c.wide = cb.wide
        return c

    @classmethod
    def with_index(cls, tokens, doc_starts, doc_keys, tok, eng, index_dir: Path, mmap: bool = True) -> Corpus:
        index = SentenceIndex.load(index_dir, mmap=mmap)
        if (index_dir / "doc_ptr.npy").exists():
            from engramm.chat.index import load_docs
            dptr, dpost, sent_doc = load_docs(index_dir, mmap)
            return cls(tokens, doc_starts, doc_keys, tok, eng, index, np.asarray(sent_doc), dptr, dpost)
        return cls(tokens, doc_starts, doc_keys, tok, eng, index)

    @classmethod
    def from_model(cls, model, index_dir: Path, mmap: bool = True) -> Corpus:
        c = cls.with_index(model.tokens, model.train.doc_starts, model.train.doc_keys, model.tok, model.cb.eng,
                           Path(index_dir), mmap)
        c.wide = model.cb.wide
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


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text())
