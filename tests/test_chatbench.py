"""ChatBench tools: loading and validating items, stable splits, blind pairs, the static rating page
and the analysis (win share, bootstrap interval, parity rule, Krippendorff's alpha)."""

from __future__ import annotations

import json
import re

import pytest

from engramm.bench.chatbench import (Item, analyze, krippendorff_alpha_nominal, load_items, make_pairs, rating_page,
                                     run_system, split_of)


def test_items_and_splits(tmp_path):
    p = tmp_path / "items.jsonl"
    p.write_text("\n".join(json.dumps({"id": f"x{i}", "category": "facts", "turns": [f"q{i}"]}) for i in range(400)))
    items = load_items(p)
    splits = [split_of(i.id) for i in items]
    assert splits == [split_of(i.id) for i in items]                 # stable
    share = splits.count("test") / len(splits)
    assert 0.18 < share < 0.32
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"id": "a", "category": "poetry", "turns": ["x"]}))
    with pytest.raises(ValueError):
        load_items(bad)
    assert len(load_items("data/chatbench/dev_team.jsonl")) >= 120


def test_run_pairs_page_and_analysis():
    items = [Item(f"i{k}", "facts" if k % 2 else "smalltalk", ["hello", f"q{k}"]) for k in range(40)]
    seen = []
    out = run_system(items, lambda conv, msg: (seen.append((conv, msg)), f"{conv}:{msg}")[1])
    assert out[0] == {"id": "i0", "reply": "i0:q0"} and len(seen) == 80
    replies = {"X": {i.id: f"x{i.id}" for i in items}, "Y": {i.id: f"y{i.id}" for i in items}}
    pairs = make_pairs(items, replies, ("X", "Y"))
    assert {p.a_system for p in pairs} == {"X", "Y"}                 # both orders occur
    page = rating_page(pairs)
    assert "<script>" in page and "X" not in re.sub(r"<[^>]+>|[^\n]*PAIRS[^\n]*", "", page).replace("X-", "")
    # X wins every facts item, ties smalltalk
    sheets = []
    for rater in ("r1", "r2", "r3"):
        rs = []
        for p in pairs:
            if p.category == "facts":
                winner = "A" if p.a_system == "X" else "B"
            else:
                winner = "tie"
            rs.append({"id": p.id, "winner": winner, "acc_a": True, "acc_b": p.category == "smalltalk"})
        sheets.append({"rater": rater, "ratings": rs})
    res = analyze(pairs, sheets, "X", "Y", reps=500)
    facts, small = res["categories"]["facts"], res["categories"]["smalltalk"]
    assert facts["p"] == 1.0 and facts["parity"] and small["p"] == 0.5 and small["parity"]
    assert res["alpha"] == pytest.approx(1.0)


def test_krippendorff_alpha():
    assert krippendorff_alpha_nominal({"a": ["x", "x"], "b": ["y", "y"]}) == pytest.approx(1.0)
    disagree = krippendorff_alpha_nominal({"a": ["x", "y"], "b": ["y", "x"]})
    assert disagree < 0
