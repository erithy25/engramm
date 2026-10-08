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
    ap.add_argument("--pipe", type=float, default=0.0, help="run-3 rule: pipeline results at this checkpoint (hours)")
    ap.add_argument("--fast", action="store_true", help="run-4 rule: fast recipe against plain")
    args = ap.parse_args()
    if args.pipe:
        return pipe_report(args.run or "run3", args.pipe)
    if args.fast:
        return fast_report(args.run or "run4")
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



def pipe_report(run: str, hours: float) -> int:
    """Run 3 primary rule (docs/PLAN_V5_FROM_SCRATCH.md §8): logres through the post-hoc
    pipeline against the better plain arm (run 2 or run 3) through the same pipeline."""
    d = RESULTS / run
    tag = f"{hours:g}h"
    arms = {"logres": f"logres_{tag}", "plain_run3": f"plain_run3_{tag}", "plain_run2": f"plain_run2_{tag}"}
    loaded = {}
    for k, t in arms.items():
        f = d / f"eval_{t}_pipe.json"
        if f.exists():
            loaded[k] = (json.loads(f.read_text()), np.load(d / f"eval_{t}_pipe_perdoc.npz"))
    if "logres" not in loaded or not ({"plain_run3", "plain_run2"} & set(loaded)):
        print(f"missing pipeline results in {d}", file=sys.stderr)
        return 1
    keep = loaded["logres"][1]["test_keep"]
    nbytes = loaded["logres"][1]["test_doc_bytes"]
    gates = {"prior_identical": all(np.array_equal(v[1]["test_prior_alone"], loaded["logres"][1]["test_prior_alone"])
                                    for v in loaded.values())}
    rows = {}
    for k, (res, pd) in loaded.items():
        for var in ("model_alone", "loglinear", "linear_bucket", "pipeline"):
            rows[f"{k} {var}"] = bpb(pd[f"test_{var}"], nbytes, mask=keep).as_dict()
    rows["counter alone"] = bpb(loaded["logres"][1]["test_prior_alone"], nbytes, mask=keep).as_dict()
    plains = [k for k in ("plain_run3", "plain_run2") if k in loaded]
    best = min(plains, key=lambda k: rows[f"{k} pipeline"]["bpb"])
    if len(plains) == 2:
        diff = abs(rows["plain_run3 pipeline"]["bpb"] - rows["plain_run2 pipeline"]["bpb"])
        gates["plain_runs_agree"] = bool(diff <= 0.015)
        gates["plain_runs_diff"] = diff
    delta = rows["logres pipeline"]["bpb"] - rows[f"{best} pipeline"]["bpb"]
    ratio = bpb_ratio(loaded["logres"][1]["test_pipeline"], loaded[best][1]["test_pipeline"], mask=keep)
    win = bool(delta <= -WIN_MARGIN and ratio["ci95"][1] < 1.0 and gates["prior_identical"])
    replicate = bool((-0.05 < delta <= -WIN_MARGIN) or not gates.get("plain_runs_agree", True))
    out = {"hours": hours, "baseline": best, "delta_bpb": delta, "ratio": ratio, "win": win,
           "replication_needed": replicate, "gates": gates, "test": rows,
           "loglinear_ab": {k: (v[0]["loglinear_a"], v[0]["loglinear_b"]) for k, v in loaded.items()}}
    (d / f"summary_pipe_{tag}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"| Test, bpb (filtered), {tag} | bpb | 95 % CI |\n|---|---|---|")
    for k, v in rows.items():
        print(f"| {k} | {v['bpb']:.4f} | {v['ci95'][0]:.4f}–{v['ci95'][1]:.4f} |")
    print(f"\nprimary: logres pipeline − {best} pipeline = {delta:+.4f} bpb, ratio {ratio['ratio']:.4f} "
          f"[{ratio['ci95'][0]:.4f}, {ratio['ci95'][1]:.4f}] → {'WIN' if win else 'no win'}"
          f"{' (replication with seed 43 required)' if replicate else ''}; gates {gates}")
    return 0



def fast_report(run: str) -> int:
    """Run 4 rule (docs/PLAN_V5_FROM_SCRATCH.md §9): the fast recipe's network alone against the
    plain network alone after 3 h; time multiplier from the fast arm's 1 h / 2 h points (lower
    bound: those are taken before its learning-rate decay)."""
    d = RESULTS / run
    rows, pd = {}, {}
    for arm in ("plain", "fast"):
        for h in (1, 2, 3):
            f = d / f"eval_{arm}_{h}h.json"
            if f.exists():
                rows[(arm, h)] = json.loads(f.read_text())
                pd[(arm, h)] = np.load(d / f"eval_{arm}_{h}h_perdoc.npz")
    if ("plain", 3) not in rows or ("fast", 3) not in rows:
        print(f"missing 3 h results in {d}", file=sys.stderr)
        return 1
    keep, nbytes = pd[("plain", 3)]["test_keep"], pd[("plain", 3)]["test_doc_bytes"]
    table = {}
    for (arm, h), p in pd.items():
        for var in ("net_alone", "posthoc_bucket_mix"):
            table[f"{arm} {h} h {var}"] = bpb(p[f"test_{var}"], nbytes, mask=keep).as_dict()
        table[f"{arm} {h} h tokens"] = rows[(arm, h)]["tokens_seen"]
    a3 = table["plain 3 h net_alone"]["bpb"]
    b3 = table["fast 3 h net_alone"]["bpb"]
    ratio = bpb_ratio(pd[("fast", 3)]["test_net_alone"], pd[("plain", 3)]["test_net_alone"], mask=keep)
    win = bool(b3 <= a3 - 0.08 and ratio["ci95"][1] < 1.0)
    reach = [h for h in (1, 2, 3) if ("fast", h) in pd and table[f"fast {h} h net_alone"]["bpb"] <= a3]
    mult = (3 / min(reach)) if reach else None
    out = {"plain_3h": a3, "fast_3h": b3, "delta": b3 - a3, "ratio": ratio, "adopt_fast": win,
           "time_multiplier_lower_bound": mult, "test": table,
           "sweep": json.loads((d / "sweep.json").read_text()) if (d / "sweep.json").exists() else None}
    (d / "summary_fast.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("| Test, bpb (filtered) | 1 h | 2 h | 3 h |\n|---|---|---|---|")
    for arm in ("plain", "fast"):
        for var in ("net_alone", "posthoc_bucket_mix"):
            cells = [f"{table[f'{arm} {h} h {var}']['bpb']:.4f}" if f"{arm} {h} h {var}" in table else "–" for h in (1, 2, 3)]
            print(f"| {arm} {var} | " + " | ".join(cells) + " |")
        cells = [f"{table[f'{arm} {h} h tokens'] / 1e6:.1f} M" if f"{arm} {h} h tokens" in table else "–" for h in (1, 2, 3)]
        print(f"| {arm} tokens | " + " | ".join(cells) + " |")
    print(f"\nfast − plain at 3 h: {b3 - a3:+.4f} bpb, ratio {ratio['ratio']:.4f} [{ratio['ci95'][0]:.4f}, "
          f"{ratio['ci95'][1]:.4f}] → {'ADOPT fast-v1' if win else 'keep plain'}; time multiplier ≥ {mult}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
