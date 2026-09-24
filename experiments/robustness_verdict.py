"""Referee for the bit-corruption study — ``docs/PREREG_ROBUSTNESS.md`` v1.3.

    python -m experiments.robustness_verdict [--results-dir results/robustness]

Reads the per-seed records written by ``experiments/robustness.py`` and
applies the registered rules, nothing else:

* §6   mean R(p) over seeds, SD, 95 % CI of the mean (Student t, n − 1 df)
* §9   floors on acc(0); the p = 50 % validation (§9.1: mean R ≤ 0.05)
* §7   confirmation per task: at every p ∈ {5, 10, 25} %, ENGRAMM's mean R
       exceeds both controls' by ≥ 0.10 and the CIs do not overlap
* §8   refutation: below the better control at a majority of those levels,
       or a gap < 0.05 at every level on both tasks; otherwise "not supported"
* §4.1 the format-matched reading of a (partial) confirmation
* §3.3 the equal-bit-budget comparison, reported next to the primary one

Writes ``verdict.json`` next to the records and prints a Markdown summary.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

from experiments.robustness import RESULTS_DIR, SEEDS, TASKS

DECISION_LEVELS = ("5", "10", "25")
ALL_LEVELS = ("0", "1", "5", "10", "25", "50")
MARGIN_CONFIRM = 0.10
MARGIN_EQUIVALENT = 0.05
VALIDATION_MAX_R50 = 0.05
FLOORS = {"engramm": {"mnist": 0.85, "wili": 0.60},
          "mlp": {"mnist": 0.90, "wili": 0.65}}
PRIMARY = ("engramm", "binary")
CONTROLS = (("lr", "int8"), ("mlp", "int8"))
FORMAT_CONTROLS = (("lr", "sign"), ("mlp", "sign"))
#: §4.1: a format control whose acc(0) is not ≥ 10 pp above chance is not
#: interpretable and drops out of the comparison.
FORMAT_MIN_ABOVE_CHANCE = 0.10


def study_code_files() -> set[str]:
    """Repository files the study process imports (everything but this referee).

    A record lists every Python file changed while it ran; only those the
    study actually executes can have influenced it. Documentation, tests and
    this referee cannot.
    """
    repo = Path(__file__).resolve().parent.parent
    files = set()
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if path and Path(path).resolve().is_relative_to(repo):
            rel = Path(path).resolve().relative_to(repo).as_posix()
            if not rel.startswith((".venv", "tests/")) and rel != "experiments/robustness_verdict.py":
                files.add(rel)
    return files


def load_records(directory: Path, include_unofficial: bool = False
                 ) -> dict[str, dict[int, dict[str, Any]]]:
    """Official records only, unless smoke-testing the referee itself."""
    records: dict[str, dict[int, dict[str, Any]]] = {task: {} for task in TASKS}
    for path in sorted(directory.glob("*_seed*.json")):
        record = json.loads(path.read_text())
        if not record.get("study", "").startswith("docs/PREREG_ROBUSTNESS.md"):
            continue
        if record["official"] or include_unofficial:
            records[record["task"]][record["seed"]] = record
    return records


def summarise(values: list[float | None]) -> dict[str, Any]:
    clean = [v for v in values if v is not None and not math.isnan(v)]
    n = len(clean)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "ci95": [None, None]}
    mean = float(np.mean(clean))
    sd = float(np.std(clean, ddof=1)) if n > 1 else 0.0
    half = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)) if n > 1 else float("inf")
    return {"n": n, "mean": mean, "sd": sd, "ci95": [mean - half, mean + half]}


def curves(task_records: dict[int, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per system/condition: acc and R per level, summarised over seeds."""
    out: dict[str, dict[str, Any]] = {}
    first = next(iter(task_records.values()))
    for system, conditions in first["systems"].items():
        for condition in conditions:
            key = f"{system}/{condition}"
            rows = [r["systems"][system][condition] for r in task_records.values()]
            out[key] = {
                "n_params": rows[0]["n_params"], "n_bits": rows[0]["n_bits"],
                "acc": {p: summarise([row["acc"][p] for row in rows]) for p in ALL_LEVELS},
                "R": {p: summarise([row["R"][p] for row in rows]) for p in ALL_LEVELS},
            }
    return out


def compare(c: dict[str, Any], system: tuple[str, str],
            controls: tuple[tuple[str, str], ...]) -> dict[str, Any]:
    """§7 and §8 quantities for one task, system against a set of controls."""
    sys_key = "/".join(system)
    per_level = {}

    def mean_or_nan(key: str, p: str) -> float:
        value = c[key]["R"][p]["mean"]
        return float("nan") if value is None else value

    for p in DECISION_LEVELS:
        e = c[sys_key]["R"][p]
        e_mean = mean_or_nan(sys_key, p)
        rows = {}
        for control in controls:
            k = "/".join(control)
            ctrl = c[k]["R"][p]
            defined = e["mean"] is not None and ctrl["mean"] is not None
            rows[k] = {"gap": e_mean - mean_or_nan(k, p) if defined else None,
                       "ci_separated": bool(defined and e["ci95"][0] > ctrl["ci95"][1])}
        defined_controls = [k for k in controls if c["/".join(k)]["R"][p]["mean"] is not None]
        better_key = ("/".join(max(defined_controls,
                                   key=lambda k: c["/".join(k)]["R"][p]["mean"]))
                      if defined_controls else None)
        gap_better = (e_mean - mean_or_nan(better_key, p)
                      if better_key is not None and e["mean"] is not None else None)
        per_level[p] = {
            "engramm_mean_R": e["mean"], "controls": rows,
            "better_control": better_key,
            "gap_to_better": gap_better,
            "confirm_level": all(r["gap"] is not None and r["gap"] >= MARGIN_CONFIRM
                                 and r["ci_separated"] for r in rows.values()),
        }
    below = sum(1 for v in per_level.values()
                if v["gap_to_better"] is not None and v["gap_to_better"] < 0)
    return {
        "per_level": per_level,
        "confirmed": all(v["confirm_level"] for v in per_level.values()),
        "below_better_at_majority": below >= 2,
        "equivalent_at_every_level": all(v["gap_to_better"] is not None
                                         and abs(v["gap_to_better"]) < MARGIN_EQUIVALENT
                                         for v in per_level.values()),
    }


def checks(task: str, c: dict[str, Any]) -> dict[str, Any]:
    floors = {}
    for system, condition, floor_of in (("engramm", "binary", "engramm"),
                                        ("mlp", "int8", "mlp"),
                                        ("mlp_bits", "int8", "mlp")):
        mean = c[f"{system}/{condition}"]["acc"]["0"]["mean"]
        floors[f"{system}/{condition}"] = {"acc0_mean": mean,
                                           "floor": FLOORS[floor_of][task],
                                           "cleared": mean >= FLOORS[floor_of][task]}
    validation = {k: {"mean_R50": v["R"]["50"]["mean"],
                      "passed": v["R"]["50"]["mean"] is not None
                      and v["R"]["50"]["mean"] <= VALIDATION_MAX_R50}
                  for k, v in c.items()}
    return {"floors": floors, "validation_p50": validation}


def verdict(records: dict[str, dict[int, dict[str, Any]]]) -> dict[str, Any]:
    tasks: dict[str, Any] = {}
    for task in TASKS:
        seeds = sorted(records[task])
        if not seeds:
            tasks[task] = {"seeds": [], "complete": False}
            continue
        c = curves(records[task])
        chk = checks(task, c)
        primary = compare(c, PRIMARY, CONTROLS)
        chance = next(iter(records[task].values()))["chance"]
        interpretable = tuple(k for k in FORMAT_CONTROLS
                              if c["/".join(k)]["acc"]["0"]["mean"] is not None
                              and c["/".join(k)]["acc"]["0"]["mean"]
                              >= chance + FORMAT_MIN_ABOVE_CHANCE)
        format_check = (compare(c, PRIMARY, interpretable) if interpretable
                        else {"per_level": {}, "confirmed": False,
                              "below_better_at_majority": False,
                              "equivalent_at_every_level": False})
        format_check["not_interpretable"] = ["/".join(k) for k in FORMAT_CONTROLS
                                             if k not in interpretable]
        equal_bits = compare(c, PRIMARY, (("mlp_bits", "int8"),))
        secondary_state = None
        if "lr/int8+idf" in c:
            secondary_state = compare(c, ("engramm", "binary+item_memory"),
                                      (("lr", "int8+idf"), ("mlp", "int8+idf")))
        tasks[task] = {
            "seeds": seeds, "complete": set(seeds) == set(SEEDS),
            "canonical": all(r["canonical"] for r in records[task].values()),
            "study_code_changed_during_any_run": sorted(
                {f for r in records[task].values()
                 for f in r["git"].get("changed_python_files", [])} & study_code_files()),
            "commits": sorted({r["git"]["commit"] for r in records[task].values()}),
            "checks": chk,
            "primary": primary,
            "format_control_4_1": format_check,
            "equal_bit_budget_3_3": equal_bits,
            "secondary_state_condition": secondary_state,
            "float32_secondary": compare(c, PRIMARY, (("lr", "float32"), ("mlp", "float32"))),
            "t1_only_secondary": compare(c, ("engramm_t1", "binary"), CONTROLS),
            "curves": c,
        }

    complete = all(tasks[t].get("complete") for t in TASKS)
    floors_ok = all(f["cleared"] for t in TASKS if tasks[t].get("seeds")
                    for k, f in tasks[t]["checks"]["floors"].items() if k != "mlp_bits/int8")
    validation_ok = all(v["passed"] for t in TASKS if tasks[t].get("seeds")
                        for v in tasks[t]["checks"]["validation_p50"].values())
    confirmed = [t for t in TASKS if tasks[t].get("seeds") and tasks[t]["primary"]["confirmed"]]
    below = [t for t in TASKS if tasks[t].get("seeds")
             and tasks[t]["primary"]["below_better_at_majority"]]
    equivalent_both = all(tasks[t].get("seeds") and tasks[t]["primary"]["equivalent_at_every_level"]
                          for t in TASKS)

    if not complete:
        outcome = "INCOMPLETE — not all registered seeds have a record"
    elif not validation_ok:
        outcome = "STOPPED — §9 validation failed (suspected corruption bug)"
    elif not floors_ok:
        outcome = "ABANDONED — §9 floor not cleared; curves are descriptive only"
    elif len(confirmed) == 2:
        outcome = "CONFIRMED (§7)"
    elif len(confirmed) == 1:
        other = [t for t in TASKS if t not in confirmed][0]
        outcome = (f"PARTIAL CONFIRMATION (§7) — holds on {confirmed[0]}, not on {other}"
                   + (f"; on {other} ENGRAMM is below the better control at a majority of "
                      f"levels (§8.1)" if other in below else ""))
    elif below or equivalent_both:
        reasons = []
        if below:
            reasons.append(f"§8.1 below the better control at a majority of levels on "
                           f"{', '.join(below)}")
        if equivalent_both:
            reasons.append("§8.2 gap < 0.05 at every level on both tasks")
        outcome = "REFUTED (§8) — " + "; ".join(reasons)
    else:
        outcome = "NOT SUPPORTED (§8.3) — confirmation fails on both tasks"

    qualifier = None
    if outcome.startswith(("CONFIRMED", "PARTIAL")):
        survives = [t for t in confirmed
                    if tasks[t]["format_control_4_1"]["per_level"] and all(
                        v["gap_to_better"] is not None and v["gap_to_better"] >= MARGIN_CONFIRM
                        for v in tasks[t]["format_control_4_1"]["per_level"].values())]
        # §4.1 is a per-task reading: on each confirmed task, either the
        # advantage also holds against the format controls, or it is
        # attributable to the number format on that task.
        failed = [t for t in confirmed if t not in survives]
        parts = []
        if survives:
            parts.append("the advantage also holds against the 1-bit format controls on "
                         + ", ".join(survives))
        if failed:
            parts.append("on " + ", ".join(failed) + " the measured advantage is attributable "
                         "to the number format; an advantage of the distributed "
                         "representation is NOT shown there")
        qualifier = "§4.1: " + "; ".join(parts)
    return {"study": "docs/PREREG_ROBUSTNESS.md v1.3", "outcome": outcome,
            "format_qualifier_4_1": qualifier, "tasks": tasks}


def _fmt(s: dict[str, Any]) -> str:
    if s["mean"] is None:
        return "—"
    return f"{s['mean']:.3f} ± {s['sd']:.3f}"


def markdown(result: dict[str, Any]) -> str:
    lines = [f"**Outcome:** {result['outcome']}", ""]
    if result["format_qualifier_4_1"]:
        lines += [f"**Format reading:** {result['format_qualifier_4_1']}", ""]
    for task in TASKS:
        t = result["tasks"][task]
        if not t.get("seeds"):
            continue
        lines += [f"### {task} ({len(t['seeds'])} seeds)", "",
                  "| System / format | params | bits | acc(0) | R(1 %) | R(5 %) | R(10 %) "
                  "| R(25 %) | R(50 %) |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for key, c in t["curves"].items():
            lines.append(f"| {key} | {c['n_params']:,} | {c['n_bits']:,} | "
                         f"{_fmt(c['acc']['0'])} | "
                         + " | ".join(_fmt(c["R"][p]) for p in ("1", "5", "10", "25", "50"))
                         + " |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    parser.add_argument("--include-unofficial", action="store_true",
                        help="also read records of limited smoke runs (never for the verdict)")
    args = parser.parse_args(argv)
    directory = Path(args.results_dir)
    result = verdict(load_records(directory, args.include_unofficial))
    if args.include_unofficial:
        result["outcome"] = "SMOKE TEST — unofficial records included; not a verdict"
    (directory / "verdict.json").write_text(json.dumps(result, indent=2) + "\n")
    summary = markdown(result)
    (directory / "SUMMARY.md").write_text(summary + "\n")
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
