"""ENGRAMM-Chat v13: train the counted confidence model (``engramm/chat/calib.py``).

    ENGRAMM_CHAT_INDEX=chat4 python -m experiments.chat_v13_calib   # → models/lm/main/chat4/confperc.json

Training data: spent development data only, never a test question of a coming round:

* every spent SQuAD test question of v2–v11 (13,477; candidate cache over chat3),
* SQuAD-Dev12 (3,084; candidate cache over chat4).

For each question the frozen pipeline ranks the candidate sentences, cuts the answer with the frozen
extraction and records the features of that answer; the label is "exactly right" (SQuAD EM).
Test12 (spent in v12) is held out: it sets θ, so it must not also train the model.
"""

from __future__ import annotations

import json
import os
import time

import numpy as np

from engramm.chat.calib import ConfCalibrator, features, train
from engramm.chat.config import EXTRACT, WEIGHTS
from engramm.chat.extract import exact_match, extract
from engramm.chat.question import analyse
from experiments.chat_v2_common import MODEL_DIR

OUT = MODEL_DIR.parent / "chat4" / os.environ.get("ENGRAMM_CALIB_OUT", "confperc.json")
SETS = (("sq_spent", "chat3"), ("sq_dev12", "chat4"))
PASSES = 10


def records(name: str, index: str) -> list[tuple[dict, str, object, np.ndarray | None, int, bool]]:
    os.environ["ENGRAMM_CHAT_INDEX"] = index
    import experiments.chat_v2_common as common
    common.CHAT_INDEX = index
    from experiments import chat_v2_dev as D
    from engramm.chat.bot import name_initial_rule
    from engramm.chat.spanstats import SpanPerceptron
    from engramm.lm.tokenizer import LMTokenizer
    from engramm.chat.config import SPAN_MODEL
    tok = LMTokenizer()
    cs = D.cap_stats()
    _, info = D.span_model(tok)
    span_dir = MODEL_DIR.parent / "chat4" if (MODEL_DIR.parent / "chat4" / SPAN_MODEL).exists() else MODEL_DIR.parent / "chat2"
    stats = SpanPerceptron.load(span_dir / SPAN_MODEL)
    memo: dict = {}

    def initial(w):
        if w not in memo:
            memo[w] = name_initial_rule(w, tok, cs.ratio)
        return memo[w]

    out = []
    t0 = time.time()
    rows = D.load_cache(name)
    for n, r in enumerate(rows):
        f = r["feats"]
        q = analyse(r["question"])
        if len(f) == 0:
            continue
        sc = f[:, 0] + r["idf_sum"] * (f @ WEIGHTS.vector())
        order = np.lexsort((r["ids"], -sc))
        top = order[:EXTRACT.k]
        texts = [r["texts"][i] for i in top]
        rel = sc[top] / max(r["idf_sum"], 1e-9)
        x = extract(q, texts, rel, EXTRACT, initial, None, stats, info)
        if x.text is None:
            continue
        sent = np.asarray(f[top[x.sentence]], dtype=np.float64) if x.sentence >= 0 else None
        out.append((x.info, x.text, q, sent, x.sentence, bool(exact_match(x.text, r["answers"]))))
        if n % 2000 == 0:
            print(f"{name}: {n}/{len(rows)} ({time.time() - t0:.0f} s)", flush=True)
    return out


def main() -> None:
    t0 = time.time()
    recs = []
    for name, index in SETS:
        recs += records(name, index)
    r0 = [i["r0"] for i, *_ in recs if i and not i.get("choice")]
    bins = tuple(round(float(x), 4) for x in np.quantile(r0, np.linspace(0, 1, 9)[1:-1]))
    examples = [(features(i, t, q.atype, q.wh, len(q.content), s, k, bins), y) for i, t, q, s, k, y in recs]
    w = train(examples, PASSES, seed=0)
    ConfCalibrator(w, bins).save(OUT)
    meta = {"examples": len(examples), "right": int(sum(y for _, y in examples)), "features": len(w),
            "passes": PASSES, "r0_bins": bins, "seconds": round(time.time() - t0, 1)}
    OUT.with_name(OUT.stem + "_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == "__main__":
    main()
