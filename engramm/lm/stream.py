"""Token streams on disk (docs/PREREG_LM.md §4).

A split is stored as one ``uint16`` array ``[EOS] d_1 [EOS] d_2 [EOS] … d_n [EOS]``:
every document is preceded by ``<|eos|>`` (its context start) and followed by
it (its end, which the model must also predict). Side arrays hold, per
document, the index of its first token, its UTF-8 byte length and its
identity (source, key).

The train stream orders documents by their split hash, so any prefix of it
(the 30 M pilot) is a hash-random sample of the whole corpus.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from engramm.lm.tokenizer import EOS

TOKEN_VERSION = 1


@dataclass
class TokenSplit:
    """One split as a token stream plus per-document bookkeeping."""

    tokens: np.ndarray          # uint16, starts and ends with EOS
    doc_starts: np.ndarray      # int64, index of each document's first token
    doc_bytes: np.ndarray       # int64, UTF-8 length of each document
    doc_keys: list[tuple[str, str]]

    @property
    def n_docs(self) -> int:
        return len(self.doc_starts)

    def doc_end(self, i: int) -> int:
        """Index of the EOS that terminates document ``i``."""
        if i + 1 < self.n_docs:
            return int(self.doc_starts[i + 1]) - 1
        return len(self.tokens) - 1

    def doc_tokens(self, i: int) -> np.ndarray:
        return np.asarray(self.tokens[self.doc_starts[i]:self.doc_end(i)])

    def prefix(self, n_tokens: int) -> TokenSplit:
        """The documents that fit completely into the first ``n_tokens`` tokens."""
        ends = np.append(self.doc_starts[1:] - 1, len(self.tokens) - 1)
        k = int(np.searchsorted(ends + 1, n_tokens, side="right"))
        if k == 0:
            raise ValueError(f"no complete document within {n_tokens} tokens")
        stop = int(ends[k - 1]) + 1
        return TokenSplit(self.tokens[:stop], self.doc_starts[:k], self.doc_bytes[:k], self.doc_keys[:k])

    def select(self, docs: np.ndarray) -> TokenSplit:
        """A new in-memory split made of the given documents, in the given order."""
        parts = [np.array([EOS], dtype=np.uint16)]
        starts, pos = [], 1
        for i in docs:
            t = self.doc_tokens(int(i))
            starts.append(pos)
            parts.append(t)
            parts.append(np.array([EOS], dtype=np.uint16))
            pos += len(t) + 1
        return TokenSplit(np.concatenate(parts), np.asarray(starts, dtype=np.int64),
                          self.doc_bytes[np.asarray(docs, dtype=np.int64)].copy(),
                          [self.doc_keys[int(i)] for i in docs])

    def save(self, directory: Path, name: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.asarray(self.tokens, dtype=np.uint16).tofile(directory / f"{name}.u16")
        np.save(directory / f"{name}.starts.npy", self.doc_starts)
        np.save(directory / f"{name}.bytes.npy", self.doc_bytes)
        with open(directory / f"{name}.keys.jsonl", "w", encoding="utf-8") as f:
            for s, k in self.doc_keys:
                f.write(json.dumps([s, k], ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, directory: Path, name: str, mmap: bool = True) -> TokenSplit:
        path = directory / f"{name}.u16"
        tokens = np.memmap(path, dtype=np.uint16, mode="r") if mmap else np.fromfile(path, dtype=np.uint16)
        with open(directory / f"{name}.keys.jsonl", encoding="utf-8") as f:
            keys = [tuple(json.loads(line)) for line in f]
        return cls(tokens, np.load(directory / f"{name}.starts.npy"),
                   np.load(directory / f"{name}.bytes.npy"), keys)


def build_split(texts: list[str], keys: list[tuple[str, str]], encode_batch,
                batch: int = 2048) -> TokenSplit:
    """Tokenise documents (in the given order) into a :class:`TokenSplit`."""
    parts = [np.array([EOS], dtype=np.uint16)]
    starts = np.empty(len(texts), dtype=np.int64)
    nbytes = np.empty(len(texts), dtype=np.int64)
    pos = 1
    for b in range(0, len(texts), batch):
        chunk = texts[b:b + batch]
        for j, ids in enumerate(encode_batch(chunk)):
            if len(ids) and (ids == EOS).any():
                raise ValueError("a document encodes to the end marker")
            i = b + j
            starts[i] = pos
            nbytes[i] = len(chunk[j].encode("utf-8"))
            parts.append(ids)
            parts.append(np.array([EOS], dtype=np.uint16))
            pos += len(ids) + 1
    return TokenSplit(np.concatenate(parts), starts, nbytes, list(keys))
