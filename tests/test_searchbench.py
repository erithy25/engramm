"""SearchBench-EN v0 tooling (docs/PREREG_SEARCH_V0.md): validation, the sealed split, the privacy and
channels-off checks, the blind rating sheet and the scoring against the registered thresholds."""

from __future__ import annotations

import json

from engramm.bench.searchbench import (CATEGORIES, TARGET, criteria, decide, leaked, rating_page, rating_rows,
                                       same_answers, score, seal, split, validate, verify_seal, write_items)


def _items(n_per=None):
    n_per = n_per or TARGET
    out = []
    for cat in CATEGORIES:
        for i in range(n_per[cat]):
            out.append({"id": f"{cat}-{i:03d}", "category": cat, "question": f"Question {cat} number {i}?",
                        "answer": f"answer {i}", "source": f"https://example.org/{cat}/{i}", "writer": "w1"})
    return out


def test_validation_counts_fields_and_duplicates():
    items = _items()
    assert validate(items) == []
    bad = items[:3] + [dict(items[0])] + [{"id": "x", "category": "weird", "question": "", "answer": "a", "source": "nope"}]
    problems = validate(bad, full=False)
    assert any("duplicate id" in p for p in problems)
    assert any("category must be" in p for p in problems)
    assert any("missing or empty 'question'" in p for p in problems)
    assert any("source should be a URL" in p for p in problems)
    assert any("registered 160" in p for p in validate(items[:10]))


def test_split_is_deterministic_stratified_and_sealed(tmp_path):
    items = _items()
    dev, test = split(items)
    assert len(dev) == 100 and len(test) == 300
    assert split(list(reversed(items))) == (dev, test)            # order of the file does not matter
    assert {it["category"] for it in dev} == set(CATEGORIES)
    assert not {it["id"] for it in dev} & {it["id"] for it in test}
    p = tmp_path / "test.jsonl"
    write_items(test, p)
    sealf = tmp_path / "seal.txt"
    sealf.write_text(seal(p) + "  test.jsonl\n")
    assert verify_seal(p, sealf)
    p.write_text(p.read_text() + "\n")
    assert not verify_seal(p, sealf)


def test_privacy_check_finds_question_text_in_a_fetch():
    q = "Who won the 2024 Tour de France?"
    clean = [{"channel": "shelf", "host": "github.com", "what": "bucket 0412", "bytes": 1572864}]
    assert not leaked(q, clean)
    assert leaked(q, clean + [{"channel": "messenger", "host": "example.org", "what": "won 2024 tour de france"}])
    assert leaked(q, [{"what": "who won the 2024 tour de france"}])


def test_channels_off_comparison():
    n, diff = same_answers({"a": "x", "b": "y"}, {"a": "x", "b": "z"})
    assert n == 1 and diff == ["b"]


def test_rating_sheet_is_blind_and_scoring_follows_the_registration():
    items = _items({"current": 2, "longtail": 2, "general": 1})
    runs = {"offline": {it["id"]: {"text": "I don't know"} for it in items},
            "atlas": {it["id"]: {"text": it["answer"], "source": it["source"]} for it in items}}
    rows, key = rating_rows(items, runs)
    page = rating_page(rows)
    assert "offline" not in page and "atlas" not in page and len(rows) == 10
    r1 = {"rater": "a", "labels": {rid: ("right_sourced" if ref["system"] == "atlas" else "none")
                                   for rid, ref in key.items()}}
    r2 = json.loads(json.dumps(r1))
    one = next(rid for rid, ref in key.items() if ref["system"] == "atlas")
    r2["labels"][one] = "wrong"                                   # a disagreement without a third rater
    res = score(items, key, [r1, r2])
    assert res["systems"]["atlas"]
    total_undecided = sum(c.get("undecided", 0) for c in res["systems"]["atlas"].values())
    assert total_undecided == 1
    res3 = score(items, key, [r1, r2, {"rater": "c", "labels": {one: "right_sourced"}}])
    c = res3["criteria"]
    assert c["S1_wrong_share_atlas"] == 0.0 and c["S1_pass"] is True
    assert c["S2_longtail_gain_pp"] == 100.0 and c["S3_pass"] is True


def test_decide_and_empty_criteria():
    assert decide(["right", "right"]) == "right"
    assert decide(["right", "wrong", "wrong"]) == "wrong"
    assert decide(["right", None]) == "undecided"
    assert criteria({})["S1_pass"] is None
