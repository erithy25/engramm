"""Suffix arrays for a train scale, and the near-duplicate filter (docs/PREREG_LM.md §3).

    python -m experiments.lm_suffix --scale main     # SA + filter (filter always vs. the full stream)
    python -m experiments.lm_suffix --scale pilot

The filter marks every val/test document with ≥ 20 % of its 13-token windows
present verbatim in the full train stream; it is written once to
``results/lm/dedup.json`` and used by every evaluation.
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np

from engramm.lm.suffix import SuffixIndex, build_suffix_array
from engramm.repro import git_revision
from experiments.lm_common import MODELS_DIR, RESULTS_DIR, load_split, load_train, write_record

DEDUP_WIDTH = 13
DEDUP_THRESHOLD = 0.20
EVAL_SPLITS = ("val_a", "val_b", "test", "wt103_test")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="main")
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    train = load_train(args.scale)
    tokens = np.ascontiguousarray(train.tokens)
    sa = build_suffix_array(tokens)
    out_dir = MODELS_DIR / args.scale
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "sa.npy", sa)
    build_s = time.time() - t0
    print(f"SA over {len(tokens)} tokens in {build_s:.0f} s", flush=True)
    payload = {"scale": args.scale, "tokens": int(len(tokens)), "sa_seconds": build_s,
               "sa_mb": sa.nbytes / 2**20}
    if args.scale == "main":
        idx = SuffixIndex(tokens, sa)
        dedup = {"width": DEDUP_WIDTH, "threshold": DEDUP_THRESHOLD, "splits": {}}
        for name in EVAL_SPLITS:
            ev = load_split(name)
            ends = np.array([ev.doc_end(i) for i in range(ev.n_docs)], dtype=np.int64)
            tot, hit = idx.overlap(np.asarray(ev.tokens), ev.doc_starts, ends, DEDUP_WIDTH)
            frac = np.where(tot > 0, hit / np.maximum(tot, 1), 0.0)
            excluded = np.flatnonzero(frac >= DEDUP_THRESHOLD)
            dedup["splits"][name] = {"docs": ev.n_docs, "excluded": excluded.tolist(),
                                     "excluded_bytes": int(ev.doc_bytes[excluded].sum()),
                                     "total_bytes": int(ev.doc_bytes.sum()),
                                     "mean_overlap": float(frac.mean())}
            print(name, len(excluded), "of", ev.n_docs, "excluded", flush=True)
        (RESULTS_DIR / "dedup.json").write_text(json.dumps(dedup, indent=1) + "\n")
        payload["dedup"] = {k: {kk: v for kk, v in d.items() if kk != "excluded"} | {"n_excluded": len(d["excluded"])}
                            for k, d in dedup["splits"].items()}
    print(write_record(f"suffix_{args.scale}", payload, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
