"""ENGRAMM-Chat stage 1 — exploratory follow-ups (NOT preregistered, docs/EXPECTATIONS.md E14).

    python -m experiments.chat_explore

1. Where does the C2 gain come from? S_HDC rewards a question word found in the
   sentence with sim = 1 *and* similar words with sim < 1. Ablation "exact": the
   same formula with sim = 1 only for identical terms, 0 otherwise — i.e. an
   idf-weighted term coverage without any meaning vectors. α is chosen on dev
   with the registered grid and rule; reported on test next to BM25 and S_HDC.
2. Precision/coverage curve of the registered system on test (for stage 4).
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from engramm.lm.chat import ChatEngine, SentenceIndex, contains_answer
from engramm.lm.model import HDCLanguageModel
from engramm.repro import git_revision
from experiments.chat_eval import (ALPHAS, COVER, RESULTS, bootstrap_diff, candidates, load_squad,
                                   paragraph_coverage, split)
from experiments.lm_common import MODELS_DIR


def exact_coverage(engine: ChatEngine, sid: int, qterms: np.ndarray, qidf: np.ndarray) -> float:
    ix = engine.index
    st = int(ix.starts[sid])
    present = set(int(t) for t in ix.term_of[engine.model.tokens[st:st + int(ix.lens[sid])]] if t >= 0)
    return float(sum(w for t, w in zip(qterms, qidf) if int(t) in present) / qidf.sum())


def hits(engine, qs, per_q, alpha, which):
    h1, conf = [], []
    for q, (cands, idf_sum, extra) in zip(qs, per_q):
        scored = sorted(((b + alpha * (s if which == "hdc" else e) * idf_sum, sid)
                         for (b, s, sid), e in zip(cands, extra)), key=lambda x: (-x[0], x[1]))
        ok = bool(scored) and contains_answer(engine.sentence_text((0, 0, 0, "base", scored[0][1])), q["answers"])
        h1.append(ok)
        conf.append(scored[0][0] / idf_sum if scored else 0.0)
    return np.array(h1), np.array(conf)


def main() -> None:
    git_state, t0 = git_revision(), time.time()
    model_dir = MODELS_DIR / "main" / "model"
    model = HDCLanguageModel.load(model_dir)
    index = SentenceIndex.load(model_dir.parent / "chat")
    squad = load_squad()
    cov = paragraph_coverage(model, sorted({q["context"] for q in squad}))
    dev, test = split([q for q in squad if cov[q["context"]] >= COVER])
    engine = ChatEngine(model, index)

    def prep(qs):
        out = []
        for q in qs:
            cands, idf_sum = candidates(engine, q["question"])
            qterms, qidf, _ = engine._query(q["question"])
            out.append((cands, idf_sum, [exact_coverage(engine, sid, qterms, qidf) for _, _, sid in cands]))
        return out

    pd, pt = prep(dev), prep(test)
    res = {}
    for which in ("hdc", "exact"):
        grid = {a: hits(engine, dev, pd, a, which)[0].mean() for a in ALPHAS}
        alpha = max(ALPHAS, key=lambda a: (grid[a], -a))
        res[which] = {"dev_grid": {f"{a:g}": float(v) for a, v in grid.items()}, "alpha": alpha,
                      "test_hit1": float(hits(engine, test, pt, alpha, which)[0].mean())}
        print(which, res[which], flush=True)
    h_hdc = hits(engine, test, pt, res["hdc"]["alpha"], "hdc")
    h_ex = hits(engine, test, pt, res["exact"]["alpha"], "exact")[0]
    h_bm = hits(engine, test, pt, 0.0, "hdc")[0]
    res["hdc_minus_exact"] = bootstrap_diff(h_hdc[0].astype(float), h_ex.astype(float))
    res["exact_minus_bm25"] = bootstrap_diff(h_ex.astype(float), h_bm.astype(float))
    order = np.argsort(-h_hdc[1], kind="stable")
    curve = []
    for cover in (0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0):
        k = max(1, int(round(cover * len(order))))
        curve.append({"coverage": cover, "precision": float(h_hdc[0][order[:k]].mean())})
    res["test_precision_by_coverage"] = curve
    print(json.dumps({k: res[k] for k in ("hdc_minus_exact", "exact_minus_bm25")}, indent=1), flush=True)
    print(curve, flush=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = Path(RESULTS) / f"chat_stage1_explore_{ts}.json"
    path.write_text(json.dumps({"schema": "engramm-chat/1", "name": "chat_stage1_explore",
                                "study": "exploratory, not preregistered", "timestamp_utc": ts, "git": git_state,
                                "wall_seconds": time.time() - t0, **res}, indent=2) + "\n")
    print(path, flush=True)


if __name__ == "__main__":
    main()
