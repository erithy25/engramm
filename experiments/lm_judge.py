"""P6 — blind LLM judge (docs/PREREG_LM.md §8).

    python -m experiments.lm_judge batches        # writes results/lm/p6_judge/batch_XX.json + the fixed prompt
    (each batch is judged by an independent Claude agent with JUDGE_PROMPT; answers saved as answer_XX.json)
    python -m experiments.lm_judge score

Every prompt is judged twice, once in each presentation order. Preference
share for ENGRAMM-LM = (wins + ½ ties) / judgments; P6 needs ≥ 60 %.
"""

from __future__ import annotations

import argparse
import json
import time

from engramm.repro import git_revision
from experiments.lm_common import RESULTS_DIR, write_record

BATCH = 25
DIR = RESULTS_DIR / "p6_judge"
JUDGE_PROMPT = """You are a strict, impartial judge of English writing quality.
Each item has the beginning of a text and two possible continuations, A and B,
produced by two different automatic systems. Judge ONLY which continuation is
better English writing: more fluent and grammatical, more coherent, and more
consistent with the beginning. Ignore factual accuracy about the real world.
Length differences are not a merit by themselves. Answer "A", "B", or "=" if
they are truly equally good or equally bad.

Return ONLY a JSON object mapping every item id to "A", "B" or "=", with no
other text. The items follow as JSON."""


def batches() -> None:
    items = json.loads((RESULTS_DIR / "p6_judge_items.json").read_text())
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / "PROMPT.txt").write_text(JUDGE_PROMPT + "\n")
    blind = [{"item": i["item"], "beginning": i["prompt"], "A": i["A"], "B": i["B"]} for i in items]
    # interleave so no batch holds both orders of the same prompt
    first = [b for b in blind if b["item"].endswith("-0")]
    second = [b for b in blind if b["item"].endswith("-1")]
    ordered = first + second
    for k in range(0, len(ordered), BATCH):
        (DIR / f"batch_{k // BATCH:02d}.json").write_text(json.dumps(ordered[k:k + BATCH], indent=1,
                                                                     ensure_ascii=False) + "\n")
    print(f"{(len(ordered) + BATCH - 1) // BATCH} batches in {DIR}")


def score() -> None:
    git_state, t0 = git_revision(), time.time()
    items = {i["item"]: i for i in json.loads((RESULTS_DIR / "p6_judge_items.json").read_text())}
    verdicts = {}
    for f in sorted(DIR.glob("answer_*.json")):
        verdicts.update(json.loads(f.read_text()))
    missing = sorted(set(items) - set(verdicts))
    wins = ties = losses = 0
    by_order = {"engramm_first": [0, 0], "engramm_second": [0, 0]}
    for iid, v in verdicts.items():
        it = items[iid]
        v = v.strip()
        slot = "engramm_first" if it["engramm_is"] == "A" else "engramm_second"
        if v == "=":
            ties += 1
            s = 0.5
        elif v == it["engramm_is"]:
            wins += 1
            s = 1.0
        else:
            losses += 1
            s = 0.0
        by_order[slot][0] += s
        by_order[slot][1] += 1
    n = wins + ties + losses
    share = (wins + 0.5 * ties) / n if n else float("nan")
    out = {"judgments": n, "missing": missing, "wins": wins, "ties": ties, "losses": losses,
           "preference_engramm": share,
           "by_order": {k: v[0] / v[1] if v[1] else None for k, v in by_order.items()},
           "p6_pass": bool(n == len(items) and share >= 0.60), "judge_prompt": JUDGE_PROMPT}
    print(json.dumps({k: v for k, v in out.items() if k != "judge_prompt"}, indent=1))
    print(write_record("p6_judge", out, t0, git_state))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("batches", "score"))
    a = ap.parse_args()
    batches() if a.cmd == "batches" else score()


if __name__ == "__main__":
    main()
