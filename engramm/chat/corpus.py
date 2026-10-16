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


class DocKeys:
    """(source, key) of every document, compact: the keys in one UTF-8 buffer with offsets and the
    few distinct sources as small integers (~25 bytes per document instead of ~190 as tuples).
    Behaves like the list of tuples it replaces (indexing, iteration, len)."""

    def __init__(self, sources: list[str], src: np.ndarray, buf: bytes, offsets: np.ndarray):
        self.sources, self.src, self.buf, self.offsets = sources, src, buf, offsets

    @classmethod
    def load(cls, path: Path) -> DocKeys:
        sources: list[str] = []
        index: dict[str, int] = {}
        src, parts, offsets, pos = [], [], [0], 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                s, k = json.loads(line)
                i = index.get(s)
                if i is None:
                    i = index[s] = len(sources)
                    sources.append(s)
                b = k.encode("utf-8")
                src.append(i)
                parts.append(b)
                pos += len(b)
                offsets.append(pos)
        dtype = np.uint8 if len(sources) < 256 else np.uint16
        return cls(sources, np.asarray(src, dtype=dtype), b"".join(parts), np.asarray(offsets, dtype=np.int64))

    def __len__(self) -> int:
        return len(self.src)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[j] for j in range(*i.indices(len(self)))]
        if i < 0:
            i += len(self)
        if not 0 <= i < len(self):
            raise IndexError(i)
        a, b = int(self.offsets[i]), int(self.offsets[i + 1])
        return self.sources[int(self.src[i])], self.buf[a:b].decode("utf-8")

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]


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
            doc_keys = DocKeys.load(index_dir / "corpus.keys.jsonl")
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
        meta = json.loads((index_dir / "segment.json").read_text(encoding="utf-8"))
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
    def from_pack(cls, pack_dir: Path, mmap: bool = True) -> Corpus:
        """A knowledge pack (experiments/pack_build.py): its own token stream, index, codebook and
        tokenizer — no language model, no training split."""
        pack_dir = Path(pack_dir)
        tok = LMTokenizer(pack_dir / "tokenizer.json") if (pack_dir / "tokenizer.json").exists() else LMTokenizer()
        cb = Codebook.load(pack_dir / "codebook.npz")
        c = cls.with_index(None, None, None, tok, cb.eng, pack_dir, mmap)
        c.wide, c.classes = cb.wide, cb.classes
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
        v = np.asarray(d, dtype=self.sent_doc.dtype)    # same dtype: no conversion of the whole array
        lo = int(np.searchsorted(self.sent_doc, v, side="left"))
        hi = int(np.searchsorted(self.sent_doc, v, side="right"))
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


def materialize(index_dir: Path, out_dir: Path, chunk: int = 1 << 24) -> Path:
    """Write a base index plus its segment (``segment.json``) as one index on disk, so loading
    it maps the files instead of building the merged arrays in memory (chat4: ~4 GB less RAM).

    Array by array the result equals ``Corpus.with_segment`` (tests/test_chat_segment.py), and
    it is written through memory maps, so building it needs little memory as well. The small
    model files next to the index (span models, calibrator, statistics) are copied."""
    import shutil

    from engramm.chat.index import load_docs
    index_dir, out_dir = Path(index_dir), Path(out_dir)
    meta = json.loads((index_dir / "segment.json").read_text(encoding="utf-8"))
    base_dir = index_dir.parent / meta["base"]
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = np.lib.format

    def put(name: str, parts: list, dtype) -> None:
        total = sum(len(p) for p in parts)
        arr = fmt.open_memmap(out_dir / name, mode="w+", dtype=dtype, shape=(total,))
        k = 0
        for p in parts:
            for a in range(0, len(p), chunk):
                piece = np.asarray(p[a:a + chunk])
                arr[k:k + len(piece)] = piece
                k += len(piece)
        arr.flush()
        del arr

    # the token stream and its documents
    if (base_dir / "corpus.u16").exists():
        b_tokens = np.memmap(base_dir / "corpus.u16", dtype=np.uint16, mode="r")
        b_starts = np.load(base_dir / "corpus.starts.npy")
        b_keys = (base_dir / "corpus.keys.jsonl").read_text(encoding="utf-8").splitlines()
    else:
        raise ValueError("materialize needs a base index with its own stream (corpus.u16)")
    s_tokens = np.fromfile(index_dir / "segment.u16", dtype=np.uint16)
    s_starts = np.load(index_dir / "segment.starts.npy")
    s_keys = (index_dir / "segment.keys.jsonl").read_text(encoding="utf-8").splitlines()
    n_tok = len(b_tokens)
    if n_tok and int(b_tokens[n_tok - 1]) != 0:
        raise ValueError("the base stream must end with a document end")
    with open(out_dir / "corpus.u16", "wb") as f:
        for a in range(0, n_tok, chunk):
            f.write(np.asarray(b_tokens[a:a + chunk]).tobytes())
        f.write(s_tokens.tobytes())
    np.save(out_dir / "corpus.starts.npy", np.concatenate([b_starts, s_starts.astype(np.int64) + n_tok]))
    (out_dir / "corpus.keys.jsonl").write_text("\n".join(b_keys + s_keys) + "\n", encoding="utf-8")
    # the sentence index
    bix = SentenceIndex.load(base_dir, mmap=True)
    six = SentenceIndex.load(index_dir, mmap=False)
    if not np.array_equal(np.asarray(bix.term_of), six.term_of) or list(bix.terms) != list(six.terms):
        raise ValueError("segment and base use different term tables")
    n_sent = bix.n
    put("starts.npy", [bix.starts, six.starts.astype(np.int64) + n_tok], np.int64)
    put("lens.npy", [bix.lens, six.lens], bix.lens.dtype)
    put("sent_terms.npy", [bix.sent_terms, six.sent_terms], bix.sent_terms.dtype)
    np.save(out_dir / "ptr.npy", np.asarray(bix.ptr) + six.ptr)
    np.save(out_dir / "term_of.npy", np.asarray(bix.term_of))
    (out_dir / "terms.txt").write_text("\n".join(bix.terms) + "\n", encoding="utf-8")
    post = fmt.open_memmap(out_dir / "post.npy", mode="w+", dtype=np.int32, shape=(len(bix.post) + len(six.post),))
    _merge_postings(np.asarray(bix.ptr, dtype=np.int64), bix.post, np.asarray(six.ptr, dtype=np.int64), six.post,
                    np.int64(n_sent), post)
    post.flush()
    del post
    # documents
    bdptr, bdpost, bsent_doc = load_docs(base_dir, True)
    sdptr, sdpost, ssent_doc = load_docs(index_dir, False)
    n_doc = len(b_starts)
    put("sent_doc.npy", [bsent_doc, np.asarray(ssent_doc, dtype=np.int32) + n_doc], np.int32)
    np.save(out_dir / "doc_ptr.npy", np.asarray(bdptr) + sdptr)
    dpost = fmt.open_memmap(out_dir / "doc_post.npy", mode="w+", dtype=np.int32,
                            shape=(len(bdpost) + len(sdpost),))
    _merge_postings(np.asarray(bdptr, dtype=np.int64), bdpost, np.asarray(sdptr, dtype=np.int64), sdpost,
                    np.int64(n_doc), dpost)
    dpost.flush()
    del dpost
    # models and statistics next to the index
    for p in index_dir.iterdir():
        if p.suffix == ".json" and p.name not in ("segment.json", "info.json"):
            shutil.copy2(p, out_dir / p.name)
    info = json.loads((index_dir / "info.json").read_text(encoding="utf-8")) if (index_dir / "info.json").exists() else {}
    info.update({"materialized_from": index_dir.name, "base": meta["base"], "sentences": int(n_sent + six.n)})
    (out_dir / "info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return out_dir


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
