"""ENGRAMM-Chat stage 1: build the sentence index of the main model (docs/PREREG_CHAT.md §2).

    python -m experiments.chat_build [--model models/lm/main/model]

Reads the model's train stream, cuts it into sentences, builds the inverted index
(term → sentences) and writes it to ``<model>/../chat``. Pure counting; the result
depends only on the token stream and the tokenizer (its digest is printed and stored).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from engramm.lm.chat import SentenceIndex
from engramm.lm.stream import TokenSplit
from engramm.lm.tokenizer import LMTokenizer
from engramm.repro import peak_rss_mb
from experiments.lm_common import MODELS_DIR


def index_digest(ix: SentenceIndex) -> str:
    h = hashlib.sha256()
    for name in ("starts", "lens", "ptr", "post", "sent_terms", "term_of"):
        h.update(hashlib.sha256(np.ascontiguousarray(getattr(ix, name)).tobytes()).digest())
    h.update("\n".join(ix.terms).encode())
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=MODELS_DIR / "main" / "model")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--v2", action="store_true", help="stage 1.1 index (better boundaries + document index), "
                                                      "written to <model>/../chat2")
    args = ap.parse_args()
    out = args.out or args.model.parent / ("chat2" if args.v2 else "chat")
    t0 = time.time()
    train = TokenSplit.load(args.model, "train", mmap=True)
    print(f"train stream: {len(train.tokens):,} tokens", flush=True)
    if args.v2:
        from engramm.chat import index as v2
        ix, dptr, dpost, sent_doc = v2.build(train.tokens, train.doc_starts, LMTokenizer())
    else:
        ix = SentenceIndex.build(train.tokens, LMTokenizer())
    build_s = time.time() - t0
    digest = index_digest(ix)
    info = {"version": 2 if args.v2 else 1, "sentences": ix.n, "terms": len(ix.terms),
            "postings": int(len(ix.post)), "mean_terms_per_sentence": float(ix.sent_terms.mean()),
            "build_seconds": round(build_s, 1), "peak_rss_mb": round(peak_rss_mb(), 1), "digest": digest}
    if args.v2:
        h = hashlib.sha256(digest.encode())
        for a in (dptr, dpost, sent_doc):
            h.update(hashlib.sha256(np.ascontiguousarray(a).tobytes()).digest())
        info["doc_postings"] = int(len(dpost))
        info["digest"] = h.hexdigest()
        v2.save(out, ix, dptr, dpost, sent_doc, info)
        from engramm.chat.question import CapStats
        cap = CapStats.build(train.tokens, LMTokenizer()).ratio
        (out / "capstats.json").write_text(json.dumps(cap, sort_keys=True))
    else:
        ix.save(out)
        (out / "info.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2), flush=True)


if __name__ == "__main__":
    main()
