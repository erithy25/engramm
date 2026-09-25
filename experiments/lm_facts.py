"""P3 — rephrased facts (docs/PREREG_LM.md §8).

200 invented facts (``data/lm_facts_templates.json``: 20 relations × 10, three
hand-written phrasings each). All 200 are learnt in phrasing A with
``learn_text``; each is then queried with phrasings B and C. Hit = the first
token of the answer is among the model's top-10 next tokens.

Compared: ENGRAMM-LM (full mixture + user layer) against KN-5-learned (only
the KN component, with the same Dirichlet user adaptation). Also reported:
the null model with the user layer, every system before learning, and the
same-phrasing (A) recall.

    python -m experiments.lm_facts --scale main --seed 42 --tau-index 1 --beta-index 0
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from engramm.lm.tokenizer import EOS
from engramm.repro import git_revision
from experiments.lm_common import write_record
from experiments.lm_final_model import assemble, fitted_mixture, kn_only, null_only

FACTS = Path(__file__).resolve().parents[1] / "data" / "lm_facts_templates.json"


def load_facts():
    d = json.loads(FACTS.read_text())
    rel = {r["name"]: r for r in d["relations"]}
    return rel, d["facts"]


def queries(rel, facts, forms=("B", "C")):
    out = []
    for f in facts:
        r = rel[f["relation"]]
        for form in forms:
            tmpl = r[form]
            if form == "A":
                tmpl = tmpl.split("{a}")[0].rstrip()
            out.append((f["id"], form, tmpl.format(e=f["entity"]), " " + f["answer"]))
    return out


def rank_of(model, prompt: str, answer: str) -> int:
    ids = model.tok.encode(prompt)
    target = int(model.tok.encode(answer)[0])
    p = model.next_distribution(np.concatenate([[EOS], ids]).astype(np.uint16))
    # rank with ties broken by token id (total order)
    better = int(np.count_nonzero(p > p[target])) + int(np.count_nonzero((p == p[target])[:target]))
    return better + 1


def evaluate(model, qs):
    ranks = np.array([rank_of(model, prompt, ans) for _, _, prompt, ans in qs])
    return {"top10": float((ranks <= 10).mean()), "top1": float((ranks == 1).mean()),
            "mrr": float((1.0 / ranks).mean()), "median_rank": float(np.median(ranks))}, ranks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="main")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tau-index", type=int, required=True)
    ap.add_argument("--beta-index", type=int, required=True)
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    rel, facts = load_facts()
    full = assemble(args.scale, args.seed, fitted_mixture(args.scale, args.seed, args.tau_index, args.beta_index))
    systems = {"engramm": full, "kn5_learned": kn_only(full), "null_learned": null_only(full, args.scale)}
    qb = queries(rel, facts)
    qa = queries(rel, facts, ("A",))
    out = {"scale": args.scale, "seed": args.seed, "n_facts": len(facts), "n_queries": len(qb), "systems": {}}
    for name, m in systems.items():
        before, _ = evaluate(m, qb)
        tl = time.time()
        for f in facts:
            r = rel[f["relation"]]
            m.learn_text(r["A"].format(e=f["entity"], a=f["answer"]), f["id"])
        learn_s = time.time() - tl
        after, ranks = evaluate(m, qb)
        same, _ = evaluate(m, qa)
        by_rel = {}
        for (fid, form, _, _), rk in zip(qb, ranks):
            by_rel.setdefault(fid.rsplit("-", 1)[0], []).append(int(rk <= 10))
        out["systems"][name] = {"before": before, "after_BC": after, "after_A": same, "learn_seconds": learn_s,
                                "top10_by_relation": {k: float(np.mean(v)) for k, v in by_rel.items()}}
        print(name, before["top10"], after["top10"], same["top10"], flush=True)
    e, k = out["systems"]["engramm"]["after_BC"]["top10"], out["systems"]["kn5_learned"]["after_BC"]["top10"]
    out["p3_threshold"] = max(2 * k, k + 0.15)
    out["p3_pass"] = bool(e >= out["p3_threshold"])
    out["k4_triggered"] = bool(e <= k)
    print(write_record(f"p3_facts_{args.scale}", out, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
