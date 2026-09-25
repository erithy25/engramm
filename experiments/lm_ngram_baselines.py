"""Gate G0: KN-n for n = 2..5 on a train scale, BPB on validation (docs/PREREG_LM.md §10).

    python -m experiments.lm_ngram_baselines --scale pilot

Builds the KN-5 model (saved to ``models/lm/<scale>/kn5``) and the lower
orders for the monotonicity check; reports BPB on val-A and val-B half 2 and
the normalisation check on sampled histories.
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from engramm.lm.evaluate import bpb, doc_bytes, per_doc_bits
from engramm.lm.ngram import build_kn
from engramm.repro import git_revision
from experiments.lm_common import MODELS_DIR, half_mask, load_split, load_train, write_record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="pilot")
    ap.add_argument("--orders", default="2,3,4,5")
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()

    train = load_train(args.scale)
    print(f"train: {train.n_docs} docs, {len(train.tokens)} tokens", flush=True)
    evals = {"val_a": load_split("val_a"), "val_b": load_split("val_b")}
    out = {"scale": args.scale, "train_tokens": int(len(train.tokens)), "orders": {}}
    for n in (int(x) for x in args.orders.split(",")):
        tb = time.time()
        model = build_kn(np.asarray(train.tokens), order=n, log=lambda m: print(" ", m, flush=True))
        build_s = time.time() - tb
        row = {"build_seconds": build_s, "model_mb": model.nbytes() / 2**20, "digest": model.digest(),
               "discounts": model.disc[1:].tolist()}
        for name, split in evals.items():
            probs, found = model.stream_probs(np.asarray(split.tokens))
            bits = per_doc_bits(split, probs)
            nb = doc_bytes(split)
            row[name] = bpb(bits, nb).as_dict()
            if name == "val_b":
                row["val_b_h2"] = bpb(bits, nb, mask=half_mask(split, 1)).as_dict()
                row["found_order_hist"] = np.bincount(found, minlength=n + 1)[1:].tolist()
        rng = np.random.default_rng(0)
        vb = np.asarray(evals["val_b"].tokens)
        sums = [float(model.distribution(vb[:i]).sum()) for i in rng.integers(1, len(vb), 200)]
        row["max_norm_error"] = max(abs(s - 1.0) for s in sums)
        out["orders"][n] = row
        print(n, {k: row[k] for k in ("build_seconds", "model_mb", "max_norm_error")},
              row["val_b_h2"]["bpb"], flush=True)
        if n == 5:
            model.save(MODELS_DIR / args.scale / "kn5")
        del model
    bp = [out["orders"][n]["val_b_h2"]["bpb"] for n in sorted(out["orders"])]
    out["g0_monotone"] = all(b2 < b1 for b1, b2 in zip(bp, bp[1:]))
    out["g0_normalised"] = all(r["max_norm_error"] < 1e-9 for r in out["orders"].values())
    print(write_record(f"g0_kn_{args.scale}", out, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
