"""The ENGRAMM-LM referee on synthetic records (PREREG_LM §9, §11)."""

from __future__ import annotations

from experiments.lm_verdict import verdict


def _recs(k1=False, k2=False, p2_ratio=0.97, p2_hi=0.99, exact=True):
    return {
        "g2": {"k1_triggered": k1, "mean_improvement": 0.02},
        "k2": {"k2_triggered": k2, "ratio_engramm_over_null": {"ratio": 0.97}},
        "test": {"P1": {"ratio": 0.93, "pass": False},
                 "P2": {"ratio": p2_ratio, "ci95": [0.95, p2_hi], "pass": p2_ratio <= 0.98 and p2_hi < 1}},
        "p3": {"systems": {"engramm": {"after_BC": {"top10": 0.5}}, "kn5_learned": {"after_BC": {"top10": 0.2}}},
               "p3_threshold": 0.4, "p3_pass": True, "k4_triggered": False},
        "p4": {"a_digest_equal": exact, "canary": {"bit_identical": exact}, "p4_pass": exact, "timing": {}},
        "gen": {"k3_triggered": False, "tokens_per_second": {"engramm": 50}, "tokens_per_second_with_provenance": 20},
        "judge": {"preference_engramm": 0.65, "p6_pass": True},
    }


def test_confirmed():
    assert verdict(_recs())["outcome"] == "BESTÄTIGT (P2)"


def test_kill_gate_refutes_even_if_p2_passes():
    assert verdict(_recs(k1=True))["outcome"].startswith("WIDERLEGT (K1")


def test_p2_missed_refutes():
    assert "P2 verfehlt" in verdict(_recs(p2_ratio=0.99))["outcome"]
    assert "P2 verfehlt" in verdict(_recs(p2_hi=1.01))["outcome"]


def test_inexact_forgetting_blocks():
    assert verdict(_recs(exact=False))["outcome"].startswith("BLOCKIERT")


def test_missing_records_are_listed():
    r = _recs()
    r["judge"] = None
    v = verdict(r)
    assert v["missing_records"] == ["judge"] and "P6" not in v["criteria"]
    assert v["criteria"]["P5"]["status"].startswith("OFFEN")
