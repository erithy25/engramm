"""General English corpus for ENGRAMM-LM (docs/PREREG_LM.md).

Two checksummed sources, both general English:

* **Web** — one shard of C4-en (Raffel et al. 2020; allenai/c4 on Hugging Face),
  356,317 documents.
* **Wikipedia** — WikiText-103-raw *train* (Merity et al. 2016), cut into its
  articles and detokenised (the raw release writes ``" , "``, ``" @-@ "`` etc.;
  a model trained on that would write it too). The WikiText-103 *test* split is
  kept separate for comparison with the literature.

Every document goes to exactly one split by a content-independent hash of its
source and key (URL or article title): train 99.3 %, val-A 0.2 % (fits the
mixture weights), val-B 0.2 % (chooses configurations), test 0.3 %. The split
is a pure function of the document identity, so it does not depend on order.

On disk (``data/cache/lm/corpus/``): per split one UTF-8 blob of all document
texts, an int64 byte-offset index and a JSON-lines metadata file.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from data.loaders import CACHE_DIR, download_and_verify

LM_CACHE = CACHE_DIR / "lm"
CORPUS_DIR = LM_CACHE / "corpus"
#: Bump when document extraction or splitting changes; part of every derived key.
PREPROCESSING_VERSION = 1

_HF = "https://huggingface.co/datasets/"
SOURCES = {
    "c4": {"url": _HF + "allenai/c4/resolve/main/en/c4-train.00000-of-01024.json.gz",
           "filename": "en_c4-train.00000-of-01024.json.gz",
           "sha256": "8ef8d75b0e045dec4aa5123a671b4564466b0707086a7ed1ba8721626dfffbc9"},
    "wt103_train_0": {"url": _HF + "Salesforce/wikitext/resolve/main/wikitext-103-raw-v1/"
                                   "train-00000-of-00002.parquet",
                      "filename": "wikitext-103-raw-v1_train-00000-of-00002.parquet",
                      "sha256": "74da360f23826045b3e6ac6375411fdb15f003030aa74f2596ed08b857cb9212"},
    "wt103_train_1": {"url": _HF + "Salesforce/wikitext/resolve/main/wikitext-103-raw-v1/"
                                   "train-00001-of-00002.parquet",
                      "filename": "wikitext-103-raw-v1_train-00001-of-00002.parquet",
                      "sha256": "ba090ac30dbf5461e8dcbdd1a1b8e6f3cf9c2c756d64f0c1220450acd514f720"},
    "wt103_test": {"url": _HF + "Salesforce/wikitext/resolve/main/wikitext-103-raw-v1/"
                                "test-00000-of-00001.parquet",
                   "filename": "wikitext-103-raw-v1_test-00000-of-00001.parquet",
                   "sha256": "5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91"},
}

SPLITS = ("train", "val_a", "val_b", "test")
#: Split thresholds on a hash bucket in [0, 10000).
_SPLIT_EDGES = (9930, 9950, 9970)


def fetch(name: str, allow_download: bool = True) -> Path:
    return download_and_verify(**SOURCES[name], cache_dir=LM_CACHE, allow_download=allow_download)


# ---------------------------------------------------------------------------
# WikiText detokenisation
# ---------------------------------------------------------------------------

_WT_RULES = [
    (re.compile(r" @(.)@ "), r"\1"),          # " @-@ " -> "-", " @,@ " -> ",", " @.@ " -> "."
    (re.compile(r" ([.,;:!?%)\]}])"), r"\1"),   # no space before closing punctuation
    (re.compile(r"([(\[{$]) "), r"\1"),         # no space after opening brackets
    (re.compile(r" (n't|'s|'re|'ve|'m|'ll|'d)\b"), r"\1"),
    (re.compile(r'" ([^"]*?) "'), r'"\1"'),     # " quoted " -> "quoted"
    (re.compile(r" {2,}"), " "),
]


def detokenize_wikitext(text: str) -> str:
    """Undo the WikiText-103 raw tokenisation (spacing around punctuation)."""
    for pattern, repl in _WT_RULES:
        text = pattern.sub(repl, text)
    return text.strip()


def _heading(line: str) -> tuple[int, str] | None:
    """Return (level, title) for a WikiText heading line such as ' = = History = = '."""
    s = line.strip()
    m = re.fullmatch(r"((?:= )+)(.+?)((?: =)+)", s)
    if not m:
        return None
    level = m.group(1).count("=")
    return level, m.group(2).strip()


def wikitext_articles(path: Path) -> Iterator[tuple[str, str]]:
    """(title, detokenised article text) for every article of a WikiText parquet file."""
    import pyarrow.parquet as pq

    lines = pq.read_table(path).column("text").to_pylist()
    title, body = None, []
    for line in lines:
        head = _heading(line)
        if head is not None and head[0] == 1:
            if title is not None:
                yield title, "\n".join(body).strip()
            title, body = head[1], [detokenize_wikitext(head[1])]
            continue
        if title is None or not line.strip():
            continue
        if head is not None:                         # section heading -> plain line
            body.append(detokenize_wikitext(head[1]))
        else:
            body.append(detokenize_wikitext(line))
    if title is not None:
        yield title, "\n".join(body).strip()


# ---------------------------------------------------------------------------
# Documents and splits
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Document:
    source: str        # "c4" or "wiki"
    key: str           # URL or article title
    text: str


def _split_hash(source: str, key: str) -> int:
    digest = hashlib.shake_256(f"engramm-lm/split/v1\x00{source}\x00{key}".encode()).digest(8)
    return int.from_bytes(digest, "big")


def split_half(source: str, key: str) -> int:
    """0 or 1 — which half of its split a document is in (val-B: selection vs. gates)."""
    return _split_hash(source, key) & 1


def split_of(source: str, key: str) -> str:
    """The split a document belongs to — a pure function of its identity."""
    bucket = _split_hash(source, key) % 10_000
    if bucket < _SPLIT_EDGES[0]:
        return "train"
    if bucket < _SPLIT_EDGES[1]:
        return "val_a"
    if bucket < _SPLIT_EDGES[2]:
        return "val_b"
    return "test"


def iter_documents(allow_download: bool = True) -> Iterator[Document]:
    """All corpus documents in a fixed order: C4 in file order, then WikiText train."""
    with gzip.open(fetch("c4", allow_download), "rt", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            text = rec["text"].strip()
            if text:
                yield Document("c4", rec["url"], text)
    for part in ("wt103_train_0", "wt103_train_1"):
        for title, text in wikitext_articles(fetch(part, allow_download)):
            if text:
                yield Document("wiki", title, text)


def wikitext_test_documents(allow_download: bool = True) -> list[Document]:
    """The WikiText-103 test articles, detokenised — literature comparison only."""
    return [Document("wiki-test", t, x) for t, x in wikitext_articles(fetch("wt103_test", allow_download))
            if x]


# ---------------------------------------------------------------------------
# On-disk corpus
# ---------------------------------------------------------------------------

class SplitWriter:
    def __init__(self, directory: Path, split: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.blob = open(directory / f"{split}.txt.bin", "wb")
        self.meta = open(directory / f"{split}.meta.jsonl", "w", encoding="utf-8")
        self.offsets = [0]

    def add(self, doc: Document) -> None:
        raw = doc.text.encode("utf-8")
        self.blob.write(raw)
        self.offsets.append(self.offsets[-1] + len(raw))
        self.meta.write(json.dumps({"source": doc.source, "key": doc.key}, ensure_ascii=False) + "\n")

    def close(self, directory: Path, split: str) -> None:
        self.blob.close()
        self.meta.close()
        np.save(directory / f"{split}.offsets.npy", np.asarray(self.offsets, dtype=np.int64))


def build_corpus(directory: Path = CORPUS_DIR, allow_download: bool = True) -> dict:
    """Extract, split and store every document; returns a manifest (also written)."""
    writers = {s: SplitWriter(directory, s) for s in SPLITS}
    counts = {s: {"docs": 0, "bytes": 0, "by_source": {}} for s in SPLITS}
    for doc in iter_documents(allow_download):
        split = split_of(doc.source, doc.key)
        writers[split].add(doc)
        c = counts[split]
        c["docs"] += 1
        c["bytes"] += len(doc.text.encode("utf-8"))
        c["by_source"][doc.source] = c["by_source"].get(doc.source, 0) + 1
    for s, w in writers.items():
        w.close(directory, s)
    wt = wikitext_test_documents(allow_download)
    ww = SplitWriter(directory, "wt103_test")
    for d in wt:
        ww.add(d)
    ww.close(directory, "wt103_test")
    manifest = {"preprocessing_version": PREPROCESSING_VERSION,
                "sources": {k: v["sha256"] for k, v in SOURCES.items()},
                "splits": counts,
                "wt103_test": {"docs": len(wt), "bytes": sum(len(d.text.encode()) for d in wt)}}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


class CorpusSplit:
    """Random access to the documents of one stored split."""

    def __init__(self, split: str, directory: Path = CORPUS_DIR) -> None:
        self.split = split
        self.offsets = np.load(directory / f"{split}.offsets.npy")
        self.blob = np.memmap(directory / f"{split}.txt.bin", dtype=np.uint8, mode="r") \
            if self.offsets[-1] > 0 else np.zeros(0, dtype=np.uint8)
        with open(directory / f"{split}.meta.jsonl", encoding="utf-8") as f:
            self.meta = [json.loads(line) for line in f]

    def __len__(self) -> int:
        return len(self.offsets) - 1

    def text(self, i: int) -> str:
        return bytes(self.blob[self.offsets[i]:self.offsets[i + 1]]).decode("utf-8")

    def n_bytes(self, i: int) -> int:
        return int(self.offsets[i + 1] - self.offsets[i])

    def texts(self, start: int = 0, stop: int | None = None) -> Iterator[str]:
        stop = len(self) if stop is None else stop
        for i in range(start, stop):
            yield self.text(i)


if __name__ == "__main__":
    print(json.dumps(build_corpus(), indent=2))
