"""Mixtures of the cached components; gates G1/G2 and the final evaluation.

    python -m experiments.lm_mix --scale pilot --stage g1
    python -m experiments.lm_mix --scale pilot --stage g2           # 3 seeds, grid, KILL gate
    python -m experiments.lm_mix --scale main --stage final --seed 42 --tau 1024 --beta 4 --split test

Weights are fitted by EM on val-A (near-duplicate-filtered documents);
selection uses val-B half 1 (index 0), gates use val-B half 2 (index 1)
(docs/PREREG_LM.md §3, §7, §9, §10).
"""

from __future__ import annotations

import argparse
import itertools
import json
import time

import numpy as np

from engramm.lm.evaluate import bpb, bpb_ratio, doc_bytes, doc_index, per_doc_bits
from engramm.lm.mixture import fit_em, inf_bin, kn_bin, knn_bin, knn_edges
from engramm.repro import git_revision
from experiments.lm_common import RESULTS_DIR, SEEDS, half_mask, load_split, write_record
from experiments.lm_components import model_dir

SYSTEMS = {
    "kn5": ("kn",),
    "kn5_cache": ("kn", "cache"),
    "null": ("kn", "inf", "cache"),
    "null_knn": ("kn", "inf", "cache", "knn"),
    "null_topic": ("kn", "inf", "cache", "topic"),
    "engramm": ("kn", "inf", "cache", "knn", "topic"),
}


def dedup_keep(name: str, n_docs: int) -> np.ndarray:
    d = json.loads((RESULTS_DIR / "dedup.json").read_text())["splits"][name]
    keep = np.ones(n_docs, dtype=bool)
    keep[d["excluded"]] = False
    return keep


class Comps:
    """Cached component outputs for one split."""

    def __init__(self, scale: str, name: str, seed: int | None):
        d = model_dir(scale) / "eval"
        self.split = load_split(name)
        kn = np.load(d / f"{name}_kn.npz")
        self.p_kn, self.found = kn["p"], kn["found"]
        inf = np.load(d / f"{name}_inf.npz")
        self.k, cnt, cntw = inf["k"], inf["cnt"], inf["cnt_w"]
        self.p_inf = np.where(cnt > 0, cntw / np.maximum(cnt, 1), self.p_kn)
        c = np.load(d / f"{name}_cache.npz")["p"]
        self.p_cache = np.where(c >= 0, c, self.p_kn)
        self.seed = seed
        if seed is not None:
            kz = np.load(d / f"{name}_knn_{seed}.npz")
            self.knn_raw, self.dmin, self.ncand = kz["p"], kz["dmin"], kz["ncand"]
            tz = np.load(d / f"{name}_topic_{seed}.npz")
            self.topic_raw = tz["p"]
        positions = np.arange(1, len(self.split.tokens), dtype=np.int64)
        self.doc = doc_index(self.split, positions)

    def matrix(self, comps, tau: int = 0, beta: int = 0) -> np.ndarray:
        cols = []
        for c in comps:
            if c == "kn":
                cols.append(self.p_kn)
            elif c == "inf":
                cols.append(self.p_inf)
            elif c == "cache":
                cols.append(self.p_cache)
            elif c == "knn":
                cols.append(np.where(self.ncand > 0, self.knn_raw[:, tau], self.p_kn))
            elif c == "topic":
                t = self.topic_raw[:, beta]
                cols.append(np.where(t >= 0, t, self.p_kn))
        return np.stack(cols, axis=1)

    def buckets(self, comps, edges) -> tuple[np.ndarray, int]:
        b = kn_bin(self.found)
        n = 4
        if "inf" in comps:
            b = b * 4 + inf_bin(self.k)
            n *= 4
        if "knn" in comps:
            b = b * 4 + knn_bin(self.dmin, edges)
            n *= 4
        return b, n


def fit_and_score(comps, fit: Comps, evals: dict[str, Comps], tau=0, beta=0):
    """Fit on ``fit`` (dedup-kept documents), return mixture and per-doc bits per eval split."""
    edges = knn_edges(fit.dmin) if "knn" in comps else None
    if comps == ("kn",):
        mix = None
    else:
        keep_docs = dedup_keep(fit.split_name, fit.split.n_docs)
        rows = keep_docs[fit.doc]
        b, nb = fit.buckets(comps, edges)
        mix = fit_em(fit.matrix(comps, tau, beta)[rows], b[rows], nb, comps)
    out = {}
    for name, ev in evals.items():
        if mix is None:
            p = ev.p_kn
        else:
            b, _ = ev.buckets(comps, edges)
            p = mix.apply(ev.matrix(comps, tau, beta), b)
        out[name] = per_doc_bits(ev.split, p)
    return mix, edges, out


def load(scale, names, seed):
    out = {}
    for n in names:
        c = Comps(scale, n, seed)
        c.split_name = n
        out[n] = c
    return out


def summarise(bits, split_name, split, half=None):
    keep = dedup_keep(split_name, split.n_docs)
    nb = doc_bytes(split)
    mask = keep if half is None else keep & half_mask(split, half)
    return bpb(bits, nb, mask=mask)


def stage_g1(scale):
    c = load(scale, ("val_a", "val_b"), None)
    res = {}
    bits = {}
    for sysname in ("kn5", "kn5_cache", "null"):
        mix, _, out = fit_and_score(SYSTEMS[sysname], c["val_a"], {"val_b": c["val_b"]})
        bits[sysname] = out["val_b"]
        vb = c["val_b"].split
        res[sysname] = {"val_b_h2": summarise(out["val_b"], "val_b", vb, 1).as_dict(),
                        "val_b_h2_nodedup": bpb(out["val_b"], doc_bytes(vb), mask=half_mask(vb, 1)).as_dict(),
                        "mixture": mix.as_dict() if mix else None}
        print(sysname, res[sysname]["val_b_h2"]["bpb"], flush=True)
    vb = c["val_b"].split
    m = dedup_keep("val_b", vb.n_docs) & half_mask(vb, 1)
    res["null_over_kn5"] = bpb_ratio(bits["null"], bits["kn5"], mask=m)
    res["g1_pass"] = res["null"]["val_b_h2"]["bpb"] < res["kn5"]["val_b_h2"]["bpb"]
    return res


def stage_g2(scale):
    res = {"seeds": {}}
    improvements = []
    for seed in SEEDS:
        c = load(scale, ("val_a", "val_b"), seed)
        vb = c["val_b"].split
        _, _, nb = fit_and_score(SYSTEMS["null"], c["val_a"], {"val_b": c["val_b"]})
        null_bits = nb["val_b"]
        grid = []
        for ti, bi in itertools.product(range(c["val_b"].knn_raw.shape[1]), range(c["val_b"].topic_raw.shape[1])):
            _, _, o = fit_and_score(SYSTEMS["engramm"], c["val_a"], {"val_b": c["val_b"]}, ti, bi)
            grid.append({"tau_index": ti, "beta_index": bi,
                         "val_b_h1": summarise(o["val_b"], "val_b", vb, 0).value})
            print(seed, ti, bi, grid[-1]["val_b_h1"], flush=True)
        best = min(grid, key=lambda g: (g["val_b_h1"], g["tau_index"], g["beta_index"]))
        mix, edges, o = fit_and_score(SYSTEMS["engramm"], c["val_a"], {"val_b": c["val_b"]},
                                      best["tau_index"], best["beta_index"])
        m2 = dedup_keep("val_b", vb.n_docs) & half_mask(vb, 1)
        ratio = bpb_ratio(o["val_b"], null_bits, m2)
        abl = {}
        for sysname in ("null_knn", "null_topic"):
            _, _, oa = fit_and_score(SYSTEMS[sysname], c["val_a"], {"val_b": c["val_b"]},
                                     best["tau_index"], best["beta_index"])
            abl[sysname] = summarise(oa["val_b"], "val_b", vb, 1).value
        imp = 1.0 - ratio["ratio"]
        improvements.append(imp)
        res["seeds"][seed] = {"grid": grid, "chosen": best, "taus": c["val_b"].knn_raw.shape[1],
                              "null_val_b_h2": summarise(null_bits, "val_b", vb, 1).as_dict(),
                              "engramm_val_b_h2": summarise(o["val_b"], "val_b", vb, 1).as_dict(),
                              "ratio_engramm_over_null": ratio, "improvement": imp,
                              "ablations_val_b_h2": abl, "knn_edges": edges.tolist(),
                              "mixture": mix.as_dict(),
                              "knn_active_share": float((c["val_b"].ncand > 0).mean())}
        print(seed, "improvement", imp, flush=True)
    res["mean_improvement"] = float(np.mean(improvements))
    res["k1_triggered"] = bool(res["mean_improvement"] < 0.01 or min(improvements) <= 0)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="pilot")
    ap.add_argument("--stage", choices=("g1", "g2"), required=True)
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    res = stage_g1(args.scale) if args.stage == "g1" else stage_g2(args.scale)
    res["scale"] = args.scale
    print(write_record(f"{args.stage}_{args.scale}", res, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
