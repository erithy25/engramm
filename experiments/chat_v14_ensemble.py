"""ENGRAMM-Chat v14: the span model is the average of seven counted perceptrons.

    python -m experiments.chat_v14_ensemble train     # the five new members → $ENGRAMM_MEMBER_DIR (default /dev/shm/engramm)
    python -m experiments.chat_v14_ensemble average   # → models/lm/main/chat4/spanperc_ens7.json

Every member is an averaged perceptron trained only on SQuAD questions of the training articles (title bit
0, not a dev article, not stage 1). They differ in how they count:

| member | training |
|---|---|
| p2 | whole paragraphs, 8 passes (v8, ``chat2/spanperc_p2.json``) |
| p5 | whole paragraphs, 8 passes, v12 word splitting (``chat2/spanperc_p5.json``) |
| soft | whole paragraphs, 8 passes, best-F1 candidates count as right when no exact span exists |
| ext2 | whole paragraphs, 8 passes, second set of conjunction features |
| p12 | whole paragraphs, 12 passes |
| ctx4 | paragraphs plus the 10 best retrieved sentences (chat4) of 8,000 training questions, prior β 1 |
| ctxb05 | the same with prior β 0.5 |

The ensemble weight of a feature is the mean of its seven weights (a missing feature counts 0). The features
are computed with the richest member setting (ext2). Averaging several counted models lowers the variance of
the span choice: on the spent Test12/Test13, F1 30.66/29.54 → 30.89/30.05.
"""

from __future__ import annotations

import argparse
import os
import pickle
import subprocess
import sys
from pathlib import Path

import numpy as np

from engramm.chat.spanstats import SpanPerceptron
from experiments.chat_v2_common import MODEL_DIR

MEMBERS = Path(os.environ.get("ENGRAMM_MEMBER_DIR", "/dev/shm/engramm"))
OUT = MODEL_DIR.parent / "chat4" / "spanperc_ens7.json"
TRAIN_CTX = MEMBERS / "train_ctx4.pkl"


def member_paths() -> list[Path]:
    c = MODEL_DIR.parent / "chat2"
    return [c / "spanperc_p2.json", c / "spanperc_p5.json", MEMBERS / "v_soft.json", MEMBERS / "v_ext2.json",
            MEMBERS / "v_p12.json", MEMBERS / "spanperc_ctx4.json", MEMBERS / "v_ctxb05.json"]


def contexts_from_cache() -> None:
    """The 10 best sentences (frozen weights) of the 8,000 training questions, from the candidate cache
    ``chat_v2_dev cache_train`` (index chat4)."""
    from engramm.chat.config import WEIGHTS
    from experiments import chat_v2_dev as D
    rows = D.load_cache("sq_train")
    w = WEIGHTS.vector()
    out = {}
    for r in rows:
        f = r["feats"]
        if len(f) == 0:
            out[r["id"]] = ([], [])
            continue
        sc = f[:, 0] + r["idf_sum"] * (f @ w)
        order = np.lexsort((r["ids"], -sc))[:10]
        out[r["id"]] = ([r["texts"][i] for i in order], [float(sc[i] / max(r["idf_sum"], 1e-9)) for i in order])
    TRAIN_CTX.write_bytes(pickle.dumps(out))


def train() -> None:
    MEMBERS.mkdir(parents=True, exist_ok=True)
    py = [sys.executable, "-u", "-m"]
    runs = [["experiments.chat_v2_perceptron", "--paragraph", "--passes", "8", "--soft", "--out", str(MEMBERS / "v_soft.json")],
            ["experiments.chat_v2_perceptron", "--paragraph", "--passes", "8", "--ext2", "--out", str(MEMBERS / "v_ext2.json")],
            ["experiments.chat_v2_perceptron", "--paragraph", "--passes", "12", "--out", str(MEMBERS / "v_p12.json")]]
    for r in runs:
        subprocess.run(py + r, check=True)
    if not TRAIN_CTX.exists():
        contexts_from_cache()
    env = dict(os.environ, ENGRAMM_TRAIN_CTX=str(TRAIN_CTX))
    for beta, out in (("1.0", "spanperc_ctx4.json"), ("0.5", "v_ctxb05.json")):
        subprocess.run(py + ["experiments.chat_v2_perceptron_ctx", "train", "--passes", "8", "--beta", beta,
                             "--out", str(MEMBERS / out)], check=True, env=env)


def average() -> None:
    ms = [SpanPerceptron.load(p) for p in member_paths()]
    keys = set().union(*[m.w.keys() for m in ms])
    w = {k: sum(m.w.get(k, 0.0) for m in ms) / len(ms) for k in sorted(keys)}
    ext = max((m.extended for m in ms), key=lambda x: int(x))
    SpanPerceptron(w, ext, ms[0].domain, ms[0].max_chunk).save(OUT)
    print(f"{len(w):,} features → {OUT}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("train", "average"))
    args = ap.parse_args()
    train() if args.cmd == "train" else average()


if __name__ == "__main__":
    main()
