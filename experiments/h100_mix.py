"""Mixture of the H100 network with the counting models (PLAN §11), computed on the CPU machine.

    python -m experiments.h100_mix                       # results/v5/h100 of the main run
    python -m experiments.h100_mix --results DIR --tag main

Reads what h100_train's final evaluation saved: lp_<split>.npy (natural log p of every target token) and
perdoc_final.npz (per-document bits of the network alone), plus eval_<tag>.json. For each counting model of
v5_long.COUNTERS that exists here (models/lm/main/eval: the exact part of ENGRAMM-LM on all 285 M base train tokens;
models/lm/pilot/eval: the 30 M-token counter of runs 2-4) it fits counter weights and λ (global and per history bucket)
on filtered val-A only and reports test — with the original filter (results/lm/dedup.json) and, primary as in PLAN §11,
with the extended filter (contamination.json). The best mixture is compared with GPT-2 small by a paired document
bootstrap on the same test documents. Stage 1 itself is decided on the network alone (PLAN §11); the mixture is reported.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from experiments import h100_train as H
from experiments import v5_long as L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(H.RESULTS))
    ap.add_argument("--tag", default="main")
    args = ap.parse_args()
    out = Path(args.results)
    sfx = "" if args.tag == "main" else f"_{args.tag}"
    lp = {s: np.load(out / f"lp_{s}{sfx}.npy").astype(np.float64) for s in ("val_a", "test")}
    perdoc = np.load(out / f"perdoc_final{sfx}.npz")
    docs_n = {s: len(perdoc[f"{s}_net_alone"]) for s in ("val_a", "test")}
    net = json.loads((out / f"eval_{args.tag}.json").read_text())
    filters = [("original (dedup.json)", None)]
    ext = {s: H.extended_keep(s, len(np.load(H.TOK / f"{s}.starts.npy")), out) for s in ("val_a", "test")}
    if all(v is not None for v in ext.values()):
        filters.append(("extended (contamination.json)", ext))
    res = {"tag": args.tag, "docs": docs_n, "network_alone": {"test": net["test"], "val_a": net["val_a"],
                                                               "stage1": net.get("stage1")}, "counters": {}}
    best = None                                              # (bpb on test, counter, filter, bits, keep)
    for name, where in L.COUNTERS.items():
        if not all((where / f"{s}_{c}.npz").exists() for s in ("val_a", "test") for c in ("kn", "inf", "cache")):
            print(f"counter {name}: files missing in {where}, skipped")
            continue
        res["counters"][name] = {}
        for label, keep in filters:
            mix, bits = L.counter_mixtures(lp, docs_n, where, keep_override=keep)
            res["counters"][name][label] = mix
            k = (keep["test"] if keep is not None else L.R.keep_docs("test", len(np.load(H.TOK / "test.starts.npy"))))
            b = mix["test"]["bpb_bucket_mix"]
            print(f"{name:5s} {label:30s} test: counter {mix['test']['bpb_counter_alone']:.4f}  "
                  f"mix {mix['test']['bpb_mix']:.4f}  bucket mix {b:.4f}  (λ {mix['lambda']:.3f})")
            if label == filters[-1][0] and (best is None or b < best[0]):
                best = (b, name, label, bits["test_bucket_mix"], k)
    if best is not None and L.GPT2_TEST.exists():
        res["best_mix"] = {"counter": best[1], "filter": best[2], "test_bpb": best[0],
                           "vs_gpt2": H.versus_gpt2(best[3], best[4], f"{best[2]}, {best[1]} counter, bucket mix")}
        v = res["best_mix"]["vs_gpt2"]
        print(f"best mix vs GPT-2 small ({best[2]}): ratio {v['ratio_to_gpt2']:.3f}, "
              f"95 % CI {v['ratio_ci95'][0]:.3f}–{v['ratio_ci95'][1]:.3f}")
    s1 = net.get("stage1") or {}
    print(f"network alone (decides Stage 1): test {s1.get('bpb', float('nan')):.4f} bpb ({s1.get('filter', '?')}), "
          f"{'REACHED' if s1.get('reached') else 'not reached'}")
    (out / f"mix_{args.tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"written: {out / f'mix_{args.tag}.json'}")


if __name__ == "__main__":
    main()
