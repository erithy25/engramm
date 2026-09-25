"""P4 — exact forgetting (docs/PREREG_LM.md §8).

(a) learn(A) → digest d_A; then learn(B) and forget(B) → digest must equal d_A.
(b) A canary (random digits) inside B: its log-probability after forgetting must
    equal, bit for bit, its log-probability in a model that never saw it; also
    reported: its exposure (rank among 1,000 random digit strings of the same
    shape) before learning, while learnt, and after forgetting.
(c) learn / forget time per 1,000 tokens: B in one batch call (criterion), A one call per
    fact (reported). Container figures; the M4 is official.
(d) the log reproduces the state (replay digest).

    python -m experiments.lm_forget --scale main --seed 42 --tau-index 1 --beta-index 0
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import numpy as np

from engramm.lm.log import LoggedModel, replay_lm
from engramm.lm.tokenizer import EOS
from engramm.repro import git_revision
from experiments.lm_common import write_record
from experiments.lm_facts import load_facts
from experiments.lm_final_model import assemble, fitted_mixture


def logprob(model, text: str) -> float:
    ids = np.concatenate([[EOS], model.tok.encode(text)]).astype(np.uint16)
    return float(sum(np.log2(model.next_distribution(ids[:i])[ids[i]]) for i in range(1, len(ids))))


def canary_text(digits: str) -> str:
    return f"The secret access code of the archive is {digits}."


def exposure(model, secret: str, rng: np.random.Generator, n: int = 200) -> float:
    """log2(n+1) − log2(rank of the secret among n random codes of the same shape)."""
    others = ["".join(str(d) for d in rng.integers(0, 10, size=len(secret))) for _ in range(n)]
    ls = logprob(model, canary_text(secret))
    lo = np.array([logprob(model, canary_text(o)) for o in others])
    rank = 1 + int((lo > ls).sum())
    return float(np.log2(n + 1) - np.log2(rank)), ls


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="main")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tau-index", type=int, required=True)
    ap.add_argument("--beta-index", type=int, required=True)
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    rel, facts = load_facts()
    texts = {f["id"]: rel[f["relation"]]["A"].format(e=f["entity"], a=f["answer"]) for f in facts}
    ids = sorted(texts)
    set_a, set_b = ids[:100], ids[100:]
    secret = "4071 9352 8816"
    m = assemble(args.scale, args.seed, fitted_mixture(args.scale, args.seed, args.tau_index, args.beta_index))
    tok_count = lambda keys: sum(len(m.tok.encode(texts[k])) for k in keys)   # noqa: E731
    rng = np.random.default_rng(1)

    exp_never, lp_never = exposure(m, secret.replace(" ", ""), np.random.default_rng(1))
    d0 = m.state_digest()
    with tempfile.TemporaryDirectory() as tmp:
        lm = LoggedModel(m, Path(tmp) / "user.log")
        t = time.time()
        for k in set_a:
            lm.learn_text(texts[k], k)
        learn_a_s = time.time() - t
        d_a = m.state_digest()
        t = time.time()
        lm.learn_texts({**{k: texts[k] for k in set_b}, "canary": canary_text(secret.replace(" ", ""))})
        learn_b_s = time.time() - t
        exp_learnt, lp_learnt = exposure(m, secret.replace(" ", ""), np.random.default_rng(1))
        t = time.time()
        lm.forget_many(["canary", *set_b])
        forget_b_s = time.time() - t
        d_after = m.state_digest()
        exp_after, lp_after = exposure(m, secret.replace(" ", ""), np.random.default_rng(1))
        lm.log.close()
        fresh = assemble(args.scale, args.seed, m.mix)
        replayed, n_events, _ = replay_lm(Path(tmp) / "user.log", fresh)
        replay_ok = replayed.state_digest() == d_after
    for k in set_a:
        m.forget(k)
    back_to_base = m.state_digest() == d0
    b_tokens = tok_count(set_b) + len(m.tok.encode(canary_text(secret.replace(" ", ""))))
    out = {
        "scale": args.scale, "seed": args.seed,
        "a_digest_equal": d_a == d_after, "back_to_base": back_to_base, "replay_equal": replay_ok,
        "replay_events": n_events,
        "canary": {"logprob_never": lp_never, "logprob_learnt": lp_learnt, "logprob_after_forget": lp_after,
                   "bit_identical": lp_after == lp_never, "exposure_never": exp_never,
                   "exposure_learnt": exp_learnt, "exposure_after": exp_after},
        "timing": {"learn_a_one_call_per_text_ms_per_1k_tokens": 1000 * learn_a_s / tok_count(set_a) * 1000,
                   "learn_a_ms_per_call": 1000 * learn_a_s / len(set_a),
                   "learn_b_ms_per_1k_tokens": 1000 * learn_b_s / b_tokens * 1000,
                   "forget_b_ms_per_1k_tokens": 1000 * forget_b_s / b_tokens * 1000,
                   "b_tokens": b_tokens,
                   "note": "B (100 facts + canary) learnt and forgotten in one batch call each; A one call "
                           "per fact. Each call rebuilds the user layer. Container timing, not official"},
    }
    out["p4_pass"] = bool(out["a_digest_equal"] and out["canary"]["bit_identical"] and
                          max(out["timing"]["learn_b_ms_per_1k_tokens"],
                              out["timing"]["forget_b_ms_per_1k_tokens"]) <= 100)
    print(json.dumps(out, indent=1), flush=True)
    print(write_record(f"p4_forget_{args.scale}", out, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
