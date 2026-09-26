"""Per-part digests of an assembled ENGRAMM-LM (cross-platform check).

    python -m experiments.lm_digests --scale main

Prints one SHA-256 per part, so two machines can see exactly which part differs.

Container reference (Linux x86-64, 2026-09-26, seed 42, τ index 1, β index 1):
    tokens 0bb69de49af77468 · kn5 650e61e0cec397a1 · suffix_array 475a22fd5e64635d
    codebook.eng 62150274cf6a7e3f · codebook.wide 80403c6753925781
    codebook.classes d67bb51975740471 · codebook.idf ae77d6409304701d
    knn_pos 3431b698d3ccd9e9 · segsig 86b00f0ab6417617
    knn_edges [1961, 2873, 4092]
    with fixed-point weights (since 2026-09-26): mixture.weights 27104a10e90ed04f,
    base_digest b45c20659e5591ff5298d631da4f5c9d566421d6db69f80eaa16a94737779b54
    (before: float weights 1c246108bf9cd56c on Linux vs. 7c5a7f8e527b6bd7 on the M4 —
    the only part that differed; rounded to 1e-9 both were 2a2b9f2e7a4da695)
"""

from __future__ import annotations

import argparse
import hashlib
import json

import numpy as np

from experiments.lm_final_model import assemble, fitted_mixture


def h(a) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()[:16]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="main")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    m = assemble(args.scale, args.seed, fitted_mixture(args.scale, args.seed, 1, 1))
    cb = m.cb
    out = {"tokens": h(m.tokens), "kn5": m.kn.digest()[:16], "suffix_array": h(m.index.sa),
           "codebook.eng": h(cb.eng), "codebook.wide": h(cb.wide), "codebook.classes": h(cb.classes),
           "codebook.idf": h(cb.idf), "knn_pos": h(m.pos), "segsig": h(m.segsig),
           "mixture.weights": h(m.mix.weights), "mixture.knn_edges": m.mix.knn_edges.tolist(),
           "mixture.weights_rounded_1e-9": h(np.round(m.mix.weights, 9)),
           "base_digest": m.base_digest()}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
