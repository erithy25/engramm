"""v5 residual training: summary of the in-training evaluations (results/v5/).

    .venv/bin/python -m experiments.v5_report                                  # run 2: residual2
    .venv/bin/python -m experiments.v5_report --run run3 --new logres --variant logres

Reads ``eval_<arm>_<h>h.json`` and ``…_perdoc.npz`` of the baseline arm ``plain`` and the new
arm, prints a table and writes ``summary.json`` next to them. Primary numbers: test split,
near-duplicate filter on, paired document bootstrap (engramm/lm/evaluate.py).

Decision rule (fixed before run 2, docs/PLAN_V5_FROM_SCRATCH.md §7): after the last
common checkpoint, residual training counts as a win if the gated mixture of residual2 is
at least 0.03 bpb better than the plain network mixed with the counter post hoc with
per-bucket weights, and the 95 % interval of the ratio lies below 1.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

from engramm.lm.evaluate import bpb, bpb_ratio

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results" / "v5"
WIN_MARGIN = 0.03
# reference points measured in the LM study (results/lm/test_eval_20260926T183702Z.json, test, filtered)
REFERENCE = {"gpt2_small": 1.038792450096114, "engramm_counting_main": 1.5135769331107698,
             "engramm_counting_pilot": 1.6637822875569943, "transformer_6h_cpu": 1.6376495826221305}


def checkpoints(arm: str) -> list[float]:
    hs = []
    for f in RESULTS.glob(f"eval_{arm}_*h.json"):
        m = re.fullmatch(rf"eval_{arm}_([0-9.]+)h\.json", f.name)
        if m:
            hs.append(float(m.group(1)))
    return sorted(hs)


def load(arm: str, h: float):
    tag = f"{h:g}h"
    res = json.loads((RESULTS / f"eval_{arm}_{tag}.json").read_text())
    perdoc = np.load(RESULTS / f"eval_{arm}_{tag}_perdoc.npz")
    return res, perdoc


def main() -> int:
    global RESULTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="", help="subdirectory of results/v5")
    ap.add_argument("--new", default="residual2", help="the new arm")
    ap.add_argument("--variant", default="gated_mix", help="the new arm's system output (gated_mix | logres)")
    args = ap.parse_args()
    RESULTS = RESULTS / args.run if args.run else RESULTS
    new_arm, var = args.new, args.variant
    common = sorted(set(checkpoints("plain")) & set(checkpoints(new_arm)))
    if not common:
        print(f"no common checkpoint of plain and {new_arm} in {RESULTS}", file=sys.stderr)
        return 1
    rows, summary = [], {"checkpoints": {}, "reference_test_bpb": REFERENCE, "win_margin": WIN_MARGIN}
    for h in common:
        (rp, dp), (rr, dr) = load("plain", h), load(new_arm, h)
        keep = dp["test_keep"]
        if not np.array_equal(keep, dr["test_keep"]):
            raise SystemExit("arms were evaluated on different documents")
        nbytes = dp["test_doc_bytes"]
        entry = {"tokens_seen": {"plain": rp["tokens_seen"], new_arm: rr["tokens_seen"]},
                 "train_seconds": {"plain": rp["train_seconds"], new_arm: rr["train_seconds"]},
                 "test": {}}
        sys_name = f"{new_arm} ({var})"
        base_name = "plain + counter, post hoc (λ per bucket)"
        variants = {
            "plain net alone": dp["test_net_alone"],
            "counter alone": dp["test_prior_alone"],
            "plain + counter, post hoc (global λ)": dp["test_posthoc_mix"],
            base_name: dp["test_posthoc_bucket_mix"],
            f"{new_arm} net alone": dr["test_net_alone"],
            f"{new_arm} + counter, post hoc (λ per bucket)": dr["test_posthoc_bucket_mix"],
            sys_name: dr[f"test_{var}"],
        }
        for name, bits in variants.items():
            entry["test"][name] = bpb(bits, nbytes, mask=keep).as_dict()
        base, new = dp["test_posthoc_bucket_mix"], dr[f"test_{var}"]
        delta = entry["test"][sys_name]["bpb"] - entry["test"][base_name]["bpb"]
        ratio = bpb_ratio(new, base, mask=keep)
        entry["primary"] = {"system": sys_name, "baseline": base_name, "delta_bpb": delta, "ratio": ratio,
                            "win": bool(delta <= -WIN_MARGIN and ratio["ci95"][1] < 1.0)}
        entry["method_effect"] = {  # same post-hoc mixer on both outputs
            "delta_bpb": entry["test"][f"{new_arm} + counter, post hoc (λ per bucket)"]["bpb"] -
            entry["test"][base_name]["bpb"],
            "ratio": bpb_ratio(dr["test_posthoc_bucket_mix"], base, mask=keep)}
        entry["gain_over_counter"] = {
            "plain": entry["test"][base_name]["bpb"] - entry["test"]["counter alone"]["bpb"],
            new_arm: entry["test"][sys_name]["bpb"] - entry["test"]["counter alone"]["bpb"]}
        summary["checkpoints"][f"{h:g}h"] = entry
        rows.append((h, entry))
    last_h, last = rows[-1]
    summary["final"] = {"hours": last_h, **last["primary"]}
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")

    names = list(rows[0][1]["test"].keys())
    print("| Test, bpb (filtered) | " + " | ".join(f"{h:g} h" for h, _ in rows) + " |")
    print("|---|" + "---|" * len(rows))
    for n in names:
        print(f"| {n} | " + " | ".join(f"{e['test'][n]['bpb']:.4f}" for _, e in rows) + " |")
    print(f"| tokens seen (plain / {new_arm}) | " + " | ".join(
        f"{e['tokens_seen']['plain'] / 1e6:.2f} M / {e['tokens_seen'][new_arm] / 1e6:.2f} M" for _, e in rows) + " |")
    p = last["primary"]
    print(f"\nprimary after {last_h:g} h: Δ = {p['delta_bpb']:+.4f} bpb, ratio {p['ratio']['ratio']:.4f} "
          f"[{p['ratio']['ci95'][0]:.4f}, {p['ratio']['ci95'][1]:.4f}] → {'WIN' if p['win'] else 'no win'}")
    m = last["method_effect"]
    print(f"method effect (same post-hoc mixer): Δ = {m['delta_bpb']:+.4f} bpb, ratio {m['ratio']['ratio']:.4f} "
          f"[{m['ratio']['ci95'][0]:.4f}, {m['ratio']['ci95'][1]:.4f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
