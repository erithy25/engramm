"""v5 residual training, step 1: counting-model prior on unseen train tokens.

The pilot counting model was built on the first 30 M train tokens. The tokens after
that are unseen by it, so its probability of each next token there is an honest
prior for training a network on the remainder (no leakage).

    .venv/bin/python -m experiments.v5_prior --tokens 20000000 --out /dev/shm/engramm/v5
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from engramm.lm.suffix import SuffixIndex
from engramm.lm.topic import stream_cache
from experiments.lm_common import load_split, load_train
from experiments.lm_components import get_kn, get_sa


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", type=int, default=20_000_000)
    ap.add_argument("--out", default="/dev/shm/engramm/v5")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pilot = load_train("pilot")
    lo = len(pilot.tokens)
    full = load_split("train", mmap=True)
    starts = np.asarray(full.doc_starts, dtype=np.int64)
    if not np.any(starts == lo):
        raise SystemExit(f"pilot end {lo} is not a document start")
    base = lo - 1                                     # the <|eos|> that opens the first unseen document
    hi = int(starts[starts <= base + args.tokens][-1])  # stop before a document start (keeps its <|eos|>)
    if hi <= lo:
        raise SystemExit("region too small")
    e = np.ascontiguousarray(np.asarray(full.tokens[base:hi]))
    if e[0] != 0:
        raise SystemExit("region must begin with <|eos|>")
    rs = starts[(starts >= lo) & (starts < hi)] - base
    re_ = np.append(rs[1:] - 1, len(e) - 1).astype(np.int64)
    print(f"region {base}..{hi}: {len(e)} tokens, {len(rs)} docs", flush=True)
    np.save(out / "region_tokens.npy", e)
    t = np.ascontiguousarray(pilot.tokens)
    t0 = time.time()
    kn = get_kn("pilot", pilot)
    p, found = kn.stream_probs(e)
    np.savez(out / "region_kn.npz", p=p, found=found)
    print("kn", f"{time.time() - t0:.0f} s", flush=True)
    t0 = time.time()
    idx = SuffixIndex(t, get_sa("pilot", pilot))
    k, cnt, cntw = idx.stream_stats(e)
    np.savez(out / "region_inf.npz", k=k, cnt=cnt, cnt_w=cntw)
    print("inf", f"{time.time() - t0:.0f} s", flush=True)
    c = stream_cache(e, rs, re_, 1 << 15)
    np.savez(out / "region_cache.npz", p=c[1:])
    print("cache done", flush=True)
    (out / "prior.done").write_text(f"{len(e)}\n")      # completion marker, written last


if __name__ == "__main__":
    main()
