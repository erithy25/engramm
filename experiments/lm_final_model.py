"""Assemble an HDCLanguageModel from the cached parts of a scale and a chosen mixture.

    python -m experiments.lm_final_model --scale main --seed 42 --tau-index 1 --beta-index 0 --save

The mixture is fitted on val-A exactly as in ``lm_mix`` (same EM, same buckets)
and written into the model directory (default ``models/lm/<scale>/model``),
which the CLI (``python -m engramm.lm``) loads.
"""

from __future__ import annotations

import argparse
import json

import numpy as np

from engramm.lm.model import COMPONENTS, HDCLanguageModel, MixtureSpec
from engramm.lm.ngram import KNModel
from engramm.lm.semantic import Codebook
from experiments.lm_components import BETAS, TAUS, model_dir
from experiments.lm_mix import SYSTEMS, fit_and_score, load
from experiments.lm_common import load_train


def fitted_mixture(scale: str, seed: int, tau_index: int, beta_index: int, system: str = "engramm") -> MixtureSpec:
    c = load(scale, ("val_a",), seed)
    mix, edges, _ = fit_and_score(SYSTEMS[system], c["val_a"], {}, tau_index, beta_index)
    return MixtureSpec(SYSTEMS[system], mix.weights, edges, TAUS[tau_index], BETAS[beta_index])


def assemble(scale: str, seed: int, mixture: MixtureSpec) -> HDCLanguageModel:
    d = model_dir(scale)
    train = load_train(scale)
    return HDCLanguageModel(train, KNModel.load(d / "kn5"), np.load(d / "sa.npy"),
                            Codebook.load(d / f"codebook_{seed}.npz"), np.load(d / f"knn_pos_{seed}.npy"),
                            np.load(d / f"segsig_{seed}.npy"), mixture, seed)


def kn_only(model: HDCLanguageModel) -> HDCLanguageModel:
    """The same base with only the (user-adapted) KN component: 'KN-5-learned' of P3."""
    spec = MixtureSpec(("kn",), np.ones((4, 1)), None, model.mix.tau, model.mix.beta)
    return HDCLanguageModel(model.train, model.kn, model.index.sa, model.cb, model.pos, model.segsig, spec,
                            model.seed, model.tok)


def null_only(model: HDCLanguageModel, scale: str) -> HDCLanguageModel:
    c = load(scale, ("val_a",), None)
    mix, _, _ = fit_and_score(SYSTEMS["null"], c["val_a"], {})
    spec = MixtureSpec(SYSTEMS["null"], mix.weights, None, model.mix.tau, model.mix.beta)
    return HDCLanguageModel(model.train, model.kn, model.index.sa, model.cb, model.pos, model.segsig, spec,
                            model.seed, model.tok)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="main")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tau-index", type=int, required=True)
    ap.add_argument("--beta-index", type=int, required=True)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    spec = fitted_mixture(args.scale, args.seed, args.tau_index, args.beta_index)
    assert spec.components == COMPONENTS
    m = assemble(args.scale, args.seed, spec)
    print(json.dumps({"base_digest": m.base_digest(), "tau": spec.tau, "beta": spec.beta}))
    if args.save:
        out = model_dir(args.scale) / "model"
        m.save(out)
        print("saved", out)


if __name__ == "__main__":
    main()
