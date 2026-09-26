"""The referee: applies docs/PREREG_LM.md §8, §9 and §11 to the latest records.

    python -m experiments.lm_verdict        # prints and writes results/lm/VERDICT.json
"""

from __future__ import annotations

import json
from pathlib import Path

from experiments.lm_common import RESULTS_DIR


def latest(prefix: str) -> dict | None:
    files = sorted(Path(RESULTS_DIR).glob(f"{prefix}_2*.json"))
    return json.loads(files[-1].read_text()) if files else None


def verdict(recs: dict) -> dict:
    g2, k2, test, p3, p4, gen, judge = (recs.get(k) for k in ("g2", "k2", "test", "p3", "p4", "gen", "judge"))
    recs = {k: v for k, v in recs.items() if k != "device" or v is not None}
    out: dict = {"criteria": {}, "kills": {}}
    missing = [k for k, v in recs.items() if v is None]
    out["missing_records"] = missing
    if g2:
        out["kills"]["K1"] = {"triggered": g2["k1_triggered"], "mean_improvement": g2["mean_improvement"]}
    if k2:
        out["kills"]["K2"] = {"triggered": k2["k2_triggered"], "ratio": k2["ratio_engramm_over_null"]}
    if gen:
        out["kills"]["K3"] = {"triggered": gen["k3_triggered"], "tokens_per_second": gen["tokens_per_second"]}
    if p3:
        out["kills"]["K4"] = {"triggered": p3["k4_triggered"]}
    if p4:
        exact = p4["a_digest_equal"] and p4["canary"]["bit_identical"]
        out["kills"]["K5"] = {"triggered": not exact}
    if test:
        out["criteria"]["P1"] = test["P1"]
        out["criteria"]["P2"] = test["P2"]
    if p3:
        e = p3["systems"]["engramm"]["after_BC"]["top10"]
        k = p3["systems"]["kn5_learned"]["after_BC"]["top10"]
        out["criteria"]["P3"] = {"engramm_top10": e, "kn5_learned_top10": k, "threshold": p3["p3_threshold"],
                                 "pass": p3["p3_pass"]}
    if p4:
        out["criteria"]["P4"] = {"pass": p4["p4_pass"], "digest_equal": p4["a_digest_equal"],
                                 "canary_bit_identical": p4["canary"]["bit_identical"], "timing": p4["timing"]}
    out["criteria"]["P5"] = {"status": "OFFEN — nur auf dem M4 gültig",
                             "container": None if not gen else {"tokens_per_second": gen["tokens_per_second"],
                                                                "with_provenance": gen["tokens_per_second_with_provenance"]}}
    dev = recs.get("device")
    if dev and dev.get("environment", {}).get("canonical"):
        out["criteria"]["P5"].update({
            "status": "ERFÜLLT (M4)" if dev["p5_pass"] else "VERFEHLT (M4)", "pass": dev["p5_pass"],
            "m4": {"build_seconds": dev["build_seconds"],
                   "tokens_per_second_with_provenance": dev["tokens_per_second_with_provenance"],
                   "peak_rss_mb": dev["peak_rss_mb"]}})
    if judge:
        out["criteria"]["P6"] = {"preference_engramm": judge["preference_engramm"], "threshold": 0.60,
                                 "pass": judge["p6_pass"], "human_panel": "Bogen erzeugt, nicht durchgeführt"}
    k1 = out["kills"].get("K1", {}).get("triggered")
    k2t = out["kills"].get("K2", {}).get("triggered")
    p2 = out["criteria"].get("P2", {}).get("pass")
    if out["kills"].get("K5", {}).get("triggered"):
        out["outcome"] = "BLOCKIERT (K5: Vergessen nicht exakt)"
    elif k1 or k2t or p2 is False:
        reasons = [r for r, c in (("K1", k1), ("K2", k2t), ("P2 verfehlt", p2 is False)) if c]
        out["outcome"] = "WIDERLEGT (" + ", ".join(reasons) + ")"
    elif p2:
        out["outcome"] = "BESTÄTIGT (P2)"
    else:
        out["outcome"] = "UNVOLLSTÄNDIG"
    return out


def main() -> None:
    recs = {"g2": latest("g2_pilot"), "k2": latest("k2_main"), "test": latest("test_eval"),
            "p3": latest("p3_facts_main"), "p4": latest("p4_forget_main"), "gen": latest("p5p6_generate_main"),
            "judge": latest("p6_judge"), "device": latest("p5_device_main")}
    v = verdict(recs)
    (RESULTS_DIR / "VERDICT.json").write_text(json.dumps(v, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(v, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
