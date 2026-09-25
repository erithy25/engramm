"""ENGRAMM-LM data preparation (docs/PREREG_LM.md §3–§4).

1. Extract and split the corpus (``data/lm_corpus.py``), unless already done.
2. Train the byte-level BPE tokenizer on the first 256 MB of train text in
   stream order, unless ``data/lm_tokenizer.json`` already exists (it is
   committed and pinned, so normally it does).
3. Tokenise every split into ``data/cache/lm/tokens/`` (train in split-hash
   order; val/test in corpus order).

    python -m experiments.lm_prepare
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from data.lm_corpus import CORPUS_DIR, LM_CACHE, SPLITS, CorpusSplit, _split_hash, build_corpus
from engramm.lm.stream import TOKEN_VERSION, TokenSplit, build_split
from engramm.lm.tokenizer import DEFAULT_PATH, LMTokenizer, file_sha256, train_tokenizer

TOKENS_DIR = LM_CACHE / "tokens"
TOKENIZER_SAMPLE_BYTES = 256 * 2**20


def train_order(split: CorpusSplit) -> np.ndarray:
    """Train documents sorted by split hash (ties impossible in practice; broken by index)."""
    hashes = np.array([_split_hash(m["source"], m["key"]) for m in split.meta], dtype=np.uint64)
    return np.lexsort((np.arange(len(hashes)), hashes))


def _sample_texts(split: CorpusSplit, order: np.ndarray, budget: int):
    used = 0
    for i in order:
        if used >= budget:
            return
        used += split.n_bytes(int(i))
        yield split.text(int(i))


def encode_corpus_split(split: CorpusSplit, order: np.ndarray, tok: LMTokenizer) -> TokenSplit:
    texts = [split.text(int(i)) for i in order]
    keys = [(split.meta[int(i)]["source"], split.meta[int(i)]["key"]) for i in order]
    return build_split(texts, keys, tok.encode_batch)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    t0 = time.time()
    if not (CORPUS_DIR / "manifest.json").exists():
        print("building corpus …", flush=True)
        build_corpus()
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())
    print(json.dumps(manifest["splits"], indent=1), flush=True)

    train = CorpusSplit("train")
    order = train_order(train)
    if not args.tokenizer.exists():
        print("training tokenizer …", flush=True)
        tk = train_tokenizer(_sample_texts(train, order, TOKENIZER_SAMPLE_BYTES))
        args.tokenizer.parent.mkdir(parents=True, exist_ok=True)
        tk.save(str(args.tokenizer))
        print(f"tokenizer saved, SHA-256 {file_sha256(args.tokenizer)} ({time.time() - t0:.0f} s)", flush=True)
    tok = LMTokenizer(args.tokenizer, sha256=None)
    print(f"tokenizer {tok.sha256}, V={tok.vocab_size}", flush=True)

    summary = {"token_version": TOKEN_VERSION, "tokenizer_sha256": tok.sha256, "splits": {}}
    for name in (*SPLITS, "wt103_test"):
        cs = train if name == "train" else CorpusSplit(name)
        o = order if name == "train" else np.arange(len(cs))
        ts = encode_corpus_split(cs, o, tok)
        ts.save(TOKENS_DIR, name)
        summary["splits"][name] = {"docs": ts.n_docs, "tokens": int(len(ts.tokens)),
                                   "bytes": int(ts.doc_bytes.sum())}
        print(name, summary["splits"][name], f"{time.time() - t0:.0f} s", flush=True)
        del ts
    (TOKENS_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("done", flush=True)


if __name__ == "__main__":
    main()
