"""M5 referee: apply the registered outcome rules to the measured records.

    python -m experiments.m5_compare --seed 42

Knows nothing about the systems' internals — it reads the JSON records in
``results/m5/`` and applies D5 §6 (criterion 4 in its ratified V2 form):

1. accuracy       acc_E ≥ acc_B1 − 5 pp
2. energy         E_E ≤ E_B1 / 10
3. learning time  t_E ≤ t_B3 / 100     (wall clock, same machine)
4. forgetting     interference_E ≤ 1 pp ∧ classical forgetting_B3 > 5 pp

Outcomes, exactly as registered — "there is no fourth, glossed-over one":

(1) full win — all four on ≥ 1 task, no catastrophe (> 15 pp behind) on the other;
(2) partial  — efficiency dominance (2 ∧ 3) at 5–15 pp accuracy gap;
(3) defeat   — B1 dominates accuracy (> 15 pp is a catastrophe regardless of
    efficiency, per the rule's harder reading adopted 2026-07-07), or the
    efficiency margin is missing.

Energy cannot be measured in this container. Where an outcome depends on
criterion 2, the referee says so and does not decide; where it does not —
an accuracy gap above 15 pp is (3) whatever the energy — it decides.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "m5"
TASKS = ("banking77", "clinc150")


def _load(system: str, task: str, seed: int, directory: Path) -> dict[str, Any] | None:
    path = directory / f"m5_{system}_{task}_seed{seed}.json"
    return json.loads(path.read_text()) if path.exists() else None


def judge(task: str, seed: int, directory: Path) -> dict[str, Any]:
    e = _load("engramm", task, seed, directory)
    b1 = _load("b1", task, seed, directory)
    b3 = _load("b3", task, seed, directory)
    b0 = _load("b0", task, seed, directory)
    if e is None or b1 is None or b3 is None:
        missing = [n for n, r in (("engramm", e), ("b1", b1), ("b3", b3)) if r is None]
        return {"task": task, "decided": False, "reason": f"missing records: {missing}"}
    if not b1.get("complete", True):
        return {"task": task, "decided": False, "reason": "B1 has not scored the full test split"}

    gap = (b1["acc"] - e["acc"]) * 100
    c1 = gap <= 5.0
    energy_e, energy_b1 = e.get("energy_mj_per_query"), b1.get("energy_mj_per_query")
    c2 = None if energy_e is None or energy_b1 is None else energy_e <= energy_b1 / 10
    learn_ratio = b3["learn_ms_per_class_wall"] / e["learn_ms_per_class_wall"]
    c3 = learn_ratio >= 100
    interference = e["forgetting"]["interference_v2_pp"]
    forgetting_b3 = b3["forgetting"]["classical_pp"]
    c4 = interference <= 1.0 and forgetting_b3 > 5.0
    cpu_ratio = b1["cpu_seconds_per_query_proxy"] / e["cpu_seconds_per_query_proxy"]

    if gap > 15:
        outcome, decided = "(3) NIEDERLAGE — Genauigkeits-Katastrophe (> 15 pp)", True
    elif c1 and c3 and c4:
        outcome = ("(1) VOLLER SIEG" if c2 else
                   "(3) NIEDERLAGE — Energieabstand < 10×" if c2 is False else
                   "nicht entscheidbar: (1) hängt an Kriterium 2 (Energie nicht gemessen)")
        decided = c2 is not None
    elif not c1:
        outcome = ("(2) TEILERFOLG — Effizienz-Nische, Genauigkeitslücke quantifiziert"
                   if (c2 and c3) else
                   "(3) NIEDERLAGE — Effizienzabstand fehlt" if (c2 is False or not c3) else
                   "nicht entscheidbar: (2) vs (3) hängt an Kriterium 2 (Energie nicht gemessen)")
        decided = c2 is not None or not c3
    else:
        outcome, decided = "(3) NIEDERLAGE — Kriterium 3 oder 4 verfehlt", True

    return {
        "task": task, "seed": seed, "decided": decided, "outcome": outcome,
        "accuracy": {"engramm": e["acc"], "b1": b1["acc"], "gap_pp": gap,
                     "b0_embedding_knn": b0["acc"] if b0 else None,
                     "b3_lora": b3["acc"]},
        "criteria": {"1_accuracy": c1, "2_energy": c2, "3_learning_time": c3,
                     "4_forgetting": c4},
        "energy": {"engramm": energy_e, "b1": energy_b1,
                   "cpu_seconds_per_query_ratio_b1_over_engramm_PROXY": cpu_ratio},
        "learning_time_ms_per_class": {"engramm_wall": e["learn_ms_per_class_wall"],
                                       "b3_wall": b3["learn_ms_per_class_wall"],
                                       "b3_cpu": b3.get("learn_ms_per_class_cpu"),
                                       "ratio_wall": learn_ratio},
        "forgetting_pp": {"engramm_interference_v2": interference,
                          "engramm_classical_v1": e["forgetting"]["classical_v1_pp"],
                          "b3_classical": forgetting_b3},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = parser.parse_args(argv)
    directory = Path(args.results_dir)
    verdicts = [judge(task, args.seed, directory) for task in TASKS]
    for v in verdicts:
        print(json.dumps(v, indent=2, ensure_ascii=False))
    decided = [v for v in verdicts if v.get("decided")]
    if len(decided) == len(TASKS) and all("(3)" in v["outcome"] for v in decided):
        overall = "(3) NIEDERLAGE auf beiden Aufgaben"
    elif any("(1)" in v.get("outcome", "") for v in decided):
        overall = "(1) VOLLER SIEG auf mindestens einer Aufgabe (Katastrophen-Regel prüfen)"
    else:
        overall = "gemischt oder nicht vollständig entscheidbar — siehe Einzelaufgaben"
    summary = {"seed": args.seed, "overall": overall, "tasks": verdicts}
    (directory / f"m5_verdict_seed{args.seed}.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(f"\nVORREGISTRIERTER GESAMTAUSGANG: {overall}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
