"""The single test-split evaluation (docs/PREREG_LM.md §8, §10).

    python -m experiments.lm_eval --seed 42 --tau-index 1 --beta-index 1

All counting systems at both scales (mixtures fitted on val-A as everywhere
else), plus — where their evaluation files exist — the Transformer
checkpoints and GPT-2 small. Primary numbers: test split, near-duplicate
filter on; also reported without the filter and on the WikiText-103 test set.
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np

from engramm.lm.evaluate import bpb, bpb_ratio, doc_bytes
from engramm.repro import git_revision
from experiments.lm_common import MODELS_DIR, write_record
from experiments.lm_mix import SYSTEMS, dedup_keep, fit_and_score, load

EVAL = ("test", "wt103_test")


def counting_systems(scale, seed, tau, beta):
    c = load(scale, ("val_a", *EVAL), seed)
    out = {}
    for sysname in SYSTEMS:
        _, _, o = fit_and_score(SYSTEMS[sysname], c["val_a"], {e: c[e] for e in EVAL}, tau, beta)
        out[sysname] = o
    return out, {e: c[e].split for e in EVAL}


def external(split_name):
    rows = {}
    tdir = MODELS_DIR / "transformer"
    for f in sorted(tdir.glob(f"eval_ckpt_*h_{split_name}.json")):
        d = json.loads(f.read_text())
        rows[f"transformer_{d['hours']}h"] = (np.array(d["per_doc_bits"]),
                                              {"tokens_seen": d["tokens_seen"], "params": d["params"]})
    g = MODELS_DIR / "gpt2" / f"eval_{split_name}.json"
    if g.exists():
        d = json.loads(g.read_text())
        rows["gpt2_small"] = (np.array(d["per_doc_bits"]), {"revision": d["revision"],
                                                             "weights_sha256": d["weights_sha256"]})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tau-index", type=int, default=1)
    ap.add_argument("--beta-index", type=int, default=1)
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    res = {"seed": args.seed, "tau_index": args.tau_index, "beta_index": args.beta_index, "splits": {}}
    bits_by = {}
    for scale in ("main", "pilot"):
        b, splits = counting_systems(scale, args.seed, args.tau_index, args.beta_index)
        for sysname, per in b.items():
            for e in EVAL:
                bits_by[(e, f"{scale}/{sysname}")] = per[e]
    for e in EVAL:
        split = splits[e]
        keep = dedup_keep(e, split.n_docs)
        nb = doc_bytes(split)
        for name, (bits, meta) in external(e).items():
            bits_by[(e, name)] = bits
        rows = {}
        for (sp, name), bits in bits_by.items():
            if sp != e:
                continue
            rows[name] = {"filtered": bpb(bits, nb, mask=keep).as_dict(), "unfiltered": bpb(bits, nb).as_dict()}
        ratios = {}
        for a, b_ in (("main/engramm", "main/null"), ("main/engramm", "main/kn5"), ("main/null", "main/kn5"),
                      ("pilot/engramm", "pilot/null")):
            ratios[f"{a} / {b_}"] = bpb_ratio(bits_by[(e, a)], bits_by[(e, b_)], mask=keep)
        for name in [n for (sp, n) in bits_by if sp == e and not n.startswith(("main/", "pilot/"))]:
            ratios[f"{name} / main/kn5"] = bpb_ratio(bits_by[(e, name)], bits_by[(e, "main/kn5")], mask=keep)
        res["splits"][e] = {"systems": rows, "ratios": ratios, "docs_kept": int(keep.sum()), "docs": split.n_docs}
    t = res["splits"]["test"]
    p2 = t["ratios"]["main/engramm / main/null"]
    p1 = t["ratios"]["main/engramm / main/kn5"]
    res["P1"] = {"ratio": p1["ratio"], "threshold": 0.90, "pass": bool(p1["ratio"] <= 0.90)}
    res["P2"] = {"ratio": p2["ratio"], "ci95": p2["ci95"], "threshold": 0.98,
                 "pass": bool(p2["ratio"] <= 0.98 and p2["ci95"][1] < 1.0)}
    for name, r in t["systems"].items():
        print(f"{name:28s} {r['filtered']['bpb']:.4f}  [{r['filtered']['ci95'][0]:.4f}, {r['filtered']['ci95'][1]:.4f}]"
              f"  unfiltered {r['unfiltered']['bpb']:.4f}", flush=True)
    print(json.dumps({"P1": res["P1"], "P2": res["P2"]}, indent=1))
    print(write_record("test_eval", res, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
