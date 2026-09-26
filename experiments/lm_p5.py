"""P5 — one command for the reference machine (docs/PREREG_LM.md §8: MacBook Air M4).

    python -m experiments.lm_p5 --scale main        # official only on the M4 (W16 conditions)

Measures, in this one process: the full build of the main model from the token
stream (KN-5, suffix array, codebook, KNN index, segment signatures), then
writing speed with provenance for 20 prompts × 100 tokens, and the peak RSS.
Needs the token files (``python -m experiments.lm_prepare``) and the fitted
mixture from val-A (component caches of the scale, or it computes them).

Criteria: ≥ 25 tokens/s including provenance, peak RSS ≤ 10 GB, build ≤ 12 h.
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from engramm.lm import knn as K
from engramm.lm.generate import Decoding, generate
from engramm.lm.model import HDCLanguageModel
from engramm.lm.ngram import build_kn
from engramm.lm.semantic import build_codebook, tiebreak_vector
from engramm.lm.suffix import build_suffix_array
from engramm.repro import git_revision, peak_rss_mb
from experiments.lm_common import load_train, write_record
from experiments.lm_final_model import fitted_mixture
from experiments.lm_generate import prompts

GB = 1024.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="main")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tau-index", type=int, default=1)
    ap.add_argument("--beta-index", type=int, default=1)
    ap.add_argument("--prompts", type=int, default=20)
    ap.add_argument("--tokens", type=int, default=100)
    ap.add_argument("--mixture-scale", default=None, help="take the val-A mixture from another scale")
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    train = load_train(args.scale)
    t = np.ascontiguousarray(train.tokens)
    steps = {}
    s = time.time(); kn = build_kn(t); steps["kn5"] = time.time() - s
    s = time.time(); sa = build_suffix_array(t); steps["suffix_array"] = time.time() - s
    s = time.time(); cb = build_codebook(t, args.seed); steps["codebook"] = time.time() - s
    s = time.time(); pos = K.build_index(t, cb.classes); steps["knn_index"] = time.time() - s
    s = time.time(); seg = K.segment_signatures(t, cb.wide, cb.idf, tiebreak_vector(args.seed))
    steps["segment_signatures"] = time.time() - s
    build_s = sum(steps.values())
    spec = fitted_mixture(args.mixture_scale or args.scale, args.seed, args.tau_index, args.beta_index)
    model = HDCLanguageModel(train, kn, sa, cb, pos, seg, spec, args.seed)
    ps = prompts(model.tok, "test")[:args.prompts]
    n_tok, t_gen = 0, 0.0
    for p in ps:
        s = time.time()
        g = generate(model, p["prompt"], args.tokens, seed=42, dec=Decoding(cache="off", top_p=0.8), explain=True)
        t_gen += time.time() - s
        n_tok += len(g.ids)
    tps = n_tok / t_gen
    rss = peak_rss_mb()
    out = {"scale": args.scale, "build_seconds": build_s, "build_steps_seconds": steps,
           "tokens_per_second_with_provenance": tps, "peak_rss_mb": rss,
           "criteria": {"speed": tps >= 25, "rss": rss <= 10 * GB, "build": build_s <= 12 * 3600},
           "note": "official only on the reference machine (MacBook Air M4, W16 conditions)"}
    out["p5_pass"] = all(out["criteria"].values())
    print(out, flush=True)
    print(write_record(f"p5_device_{args.scale}", out, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
