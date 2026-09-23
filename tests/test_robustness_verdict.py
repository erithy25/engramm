"""The referee applies PREREG_ROBUSTNESS §7/§8/§9.1/§4.1 — on synthetic records.

Every registered outcome is produced once from records constructed so that
the answer is known in advance. This tests the rules as coded, before any
real record exists to be judged by them.
"""

from __future__ import annotations

import numpy as np

from experiments.robustness import SEEDS
from experiments.robustness_verdict import verdict

LEVELS = ("0", "1", "5", "10", "25", "50")


def _curve(acc0: float, retained: dict[str, float], chance: float, jitter: float,
           rng: np.random.Generator) -> dict:
    r = {"0": 1.0}
    for p in LEVELS[1:]:
        r[p] = float(np.clip(retained.get(p, 0.0) + rng.normal(0, jitter), 0, 1))
    acc = {p: chance + r[p] * (acc0 - chance) for p in LEVELS}
    return {"n_params": 100, "n_bits": 800, "acc": acc, "R": r}


def _records(engramm_R: dict[str, float], control_R: dict[str, float],
             sign_R: dict[str, float] | None = None, engramm_acc0: float = 0.9,
             mlp_acc0: float = 0.95, r50: float = 0.0, seeds=SEEDS,
             sign_acc0: float = 0.8) -> dict:
    out = {}
    for task, chance in (("mnist", 0.1), ("wili", 1 / 235)):
        out[task] = {}
        for seed in seeds:
            rng = np.random.default_rng([seed, len(task)])
            e = {**engramm_R, "50": r50}
            c = {**control_R, "50": 0.0}
            s = {**(sign_R or control_R), "50": 0.0}
            systems = {
                "engramm": {"binary": _curve(engramm_acc0, e, chance, 0.01, rng)},
                "engramm_t1": {"binary": _curve(engramm_acc0, e, chance, 0.01, rng)},
                "lr": {"int8": _curve(0.9, c, chance, 0.01, rng),
                       "sign": _curve(sign_acc0, s, chance, 0.01, rng),
                       "float32": _curve(0.9, {}, chance, 0.0, rng)},
                "mlp": {"int8": _curve(mlp_acc0, c, chance, 0.01, rng),
                        "sign": _curve(sign_acc0, s, chance, 0.01, rng),
                        "float32": _curve(mlp_acc0, {}, chance, 0.0, rng)},
                "mlp_bits": {"int8": _curve(mlp_acc0, c, chance, 0.01, rng)},
            }
            out[task][seed] = {"study": "docs/PREREG_ROBUSTNESS.md v1.3", "official": True,
                               "task": task, "seed": seed, "chance": chance,
                               "canonical": False, "systems": systems,
                               "git": {"commit": "x", "code_changed_during_run": False}}
    return out


STRONG = {"1": 0.99, "5": 0.95, "10": 0.9, "25": 0.7}
WEAK = {"1": 0.9, "5": 0.6, "10": 0.4, "25": 0.1}


def test_confirmation_explained_by_format_is_qualified():
    result = verdict(_records(STRONG, WEAK, sign_R=STRONG))
    assert result["outcome"] == "CONFIRMED (§7)"
    assert "format" in result["format_qualifier_4_1"] and "NOT" in result["format_qualifier_4_1"]


def test_confirmation_that_survives_the_format_control_says_so():
    result = verdict(_records(STRONG, WEAK, sign_R=WEAK))
    assert result["outcome"] == "CONFIRMED (§7)"
    assert result["format_qualifier_4_1"].startswith("§4.1: the advantage also holds")


def test_engramm_below_the_better_control_is_refutation():
    result = verdict(_records(WEAK, STRONG))
    assert result["outcome"].startswith("REFUTED (§8)")
    assert "§8.1" in result["outcome"]


def test_equivalent_degradation_is_refutation():
    close = {k: v + 0.02 for k, v in WEAK.items()}
    result = verdict(_records(close, WEAK))
    assert result["outcome"].startswith("REFUTED (§8)") and "§8.2" in result["outcome"]


def test_small_but_real_advantage_is_not_supported():
    better = {k: v + 0.07 for k, v in WEAK.items()}
    result = verdict(_records(better, WEAK))
    assert result["outcome"].startswith("NOT SUPPORTED")


def test_floor_below_85_percent_abandons_the_study():
    result = verdict(_records(STRONG, WEAK, engramm_acc0=0.80))
    assert result["outcome"].startswith("ABANDONED")


def test_failed_p50_validation_stops_the_study():
    result = verdict(_records(STRONG, WEAK, r50=0.2))
    assert result["outcome"].startswith("STOPPED")


def test_missing_seeds_is_incomplete():
    result = verdict(_records(STRONG, WEAK, seeds=SEEDS[:9]))
    assert result["outcome"].startswith("INCOMPLETE")


def test_format_control_near_chance_is_not_interpretable():
    records = _records(STRONG, WEAK, sign_R=STRONG)
    for task in records.values():
        for record in task.values():
            chance = record["chance"]
            broken = record["systems"]["lr"]["sign"]
            broken["acc"] = {p: chance + 0.01 for p in LEVELS}
    result = verdict(records)
    assert result["tasks"]["mnist"]["format_control_4_1"]["not_interpretable"] == ["lr/sign"]
