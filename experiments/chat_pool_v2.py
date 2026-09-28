"""SQuAD questions whose paragraph ENGRAMM has now read (pool v2, for rounds after v10).

    python -m experiments.chat_pool_v2      # → data/cache/chat/squad_pool_v2.json

The stage-1 pool (``squad_pool_v1.json``) holds the questions whose paragraph is covered to at
least 80 % by 13-token windows (step 13) found verbatim in the original 285 M-token stream. After
v10, ENGRAMM has also read 614,464 Wikipedia leads (index ``chat3``). Pool v2 applies **the same
rule** to that new text. Every 13-token window of the Wikipedia part is hashed (64-bit polynomial
hash, windows across a document boundary skipped). A paragraph whose windows are found at least
80 % of the time joins the pool, unless its question is already in pool v1. Only the question
texts' paragraphs are read; no answer is looked at.
"""

from __future__ import annotations

import json
import time

import numba
import numpy as np

from engramm.lm.stream import EOS, TokenSplit
from engramm.lm.tokenizer import LMTokenizer
from experiments.chat_eval import COVER, WINDOW, load_squad
from experiments.chat_v2_common import MODEL_DIR
from experiments.chat_v2_data import CACHE

BASE = np.uint64(1_000_003)


@numba.njit(cache=True)
def _window_hashes(tokens, w):
    n = len(tokens)
    out = np.empty(max(n - w + 1, 0), dtype=np.uint64)
    k = 0
    for i in range(n - w + 1):
        h = np.uint64(1469598103934665603)
        ok = True
        for j in range(w):
            t = tokens[i + j]
            if t == 0:
                ok = False
                break
            h = h * np.uint64(1000003) + np.uint64(t)
        if ok:
            out[k] = h
            k += 1
    return out[:k]


@numba.njit(cache=True)
def _mark_found(tokens, w, targets, found):
    """For every 13-token window of the stream: if its hash is among the (sorted) targets, mark it."""
    n = len(tokens)
    m = len(targets)
    for i in range(n - w + 1):
        h = np.uint64(1469598103934665603)
        ok = True
        for j in range(w):
            t = tokens[i + j]
            if t == 0:
                ok = False
                break
            h = h * np.uint64(1000003) + np.uint64(t)
        if not ok:
            continue
        lo, hi = 0, m
        while lo < hi:
            mid = (lo + hi) // 2
            if targets[mid] < h:
                lo = mid + 1
            else:
                hi = mid
        if lo < m and targets[lo] == h:
            found[lo] = True


def main() -> None:
    t0 = time.time()
    train = TokenSplit.load(MODEL_DIR, "train", mmap=True)
    corpus = np.memmap(MODEL_DIR.parent / "chat3" / "corpus.u16", dtype=np.uint16, mode="r")
    wiki = np.asarray(corpus[len(train.tokens):])
    tok = LMTokenizer()
    v1 = set(json.loads((CACHE / "squad_pool_v1.json").read_text())["pool"])
    squad = load_squad()
    contexts = sorted({q["context"] for q in squad if q["id"] not in v1})
    wins = {}
    for ctx in contexts:
        ids = np.asarray(tok.encode(ctx), dtype=np.uint16)
        n_win = len(ids) // WINDOW
        hs = []
        for w in range(n_win):
            x = np.ascontiguousarray(ids[w * WINDOW:(w + 1) * WINDOW])
            hh = _window_hashes(x, WINDOW)
            hs.append(int(hh[0]) if len(hh) else 0)
        wins[ctx] = hs
    targets = np.unique(np.array([h for v in wins.values() for h in v if h], dtype=np.uint64))
    found = np.zeros(len(targets), dtype=np.bool_)
    _mark_found(wiki, WINDOW, targets, found)
    got = set(targets[found].tolist())
    print(f"{len(wiki):,} Wikipedia tokens scanned, {len(targets):,} paragraph windows, {len(got):,} found "
          f"({time.time() - t0:.0f} s)", flush=True)
    cov = {c: (sum(1 for h in v if h in got) / len(v) if v else 0.0) for c, v in wins.items()}
    pool = sorted(q["id"] for q in squad if q["id"] not in v1 and cov[q["context"]] >= COVER)
    (CACHE / "squad_pool_v2.json").write_text(json.dumps({"pool": pool, "rule": "13-gram coverage >= 0.8 in the "
                                                          "Wikipedia part of chat3, not in pool v1"}))
    print(f"pool v2: {len(pool):,} questions from {sum(1 for c in contexts if cov[c] >= COVER):,} paragraphs "
          f"({time.time() - t0:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
