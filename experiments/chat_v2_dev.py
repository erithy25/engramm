"""ENGRAMM-Chat v2 — development on the DEV splits only (docs/PREREG_CHAT_V2.md §2).

    python -m experiments.chat_v2_dev cache            # candidates + features for SQuAD-dev2 and NQ-dev
    python -m experiments.chat_v2_dev tune             # weight search for stage 1.1 on the cached features

Nothing here touches a test split.
"""

from __future__ import annotations

import argparse
import itertools
import pickle
import time

import numpy as np

from engramm.chat.retrieve import FEATURES, Retriever, Weights
from engramm.lm.chat import contains_answer
from experiments.chat_v2_common import load_all
from experiments.chat_v2_data import CACHE

DEV_SETS = ("sq_dev", "nq_dev")
STAGE1_DEV = {"sq_dev": 0.403, "nq_dev": 0.022}


def cache_path(name: str):
    return CACHE / f"dev_cands_{name}.pkl"


def build_cache() -> None:
    corpus, data = load_all()
    r = Retriever(corpus)
    for name in DEV_SETS:
        t0 = time.time()
        rows = []
        for i, q in enumerate(data[name]):
            c = r.candidates(q["question"])
            hits = np.array([contains_answer(t, q["answers"]) for t in c.texts], dtype=bool)
            rows.append({"id": q["id"], "question": q["question"], "answers": q["answers"], "ids": c.ids,
                         "feats": c.feats, "hits": hits, "texts": c.texts, "idf_sum": c.query.idf_sum,
                         "atype": c.query.q.atype, "n_bm25": min(r.n_bm25, len(c.ids))})
            if i % 250 == 0:
                print(f"{name}: {i}/{len(data[name])} ({time.time() - t0:.0f} s)", flush=True)
        cache_path(name).write_bytes(pickle.dumps(rows))
        print(f"{name}: done in {time.time() - t0:.0f} s", flush=True)


def load_cache(name: str) -> list[dict]:
    return pickle.loads(cache_path(name).read_bytes())


def hit_at(rows, w: Weights, k: int = 1, v1: bool = False) -> float:
    vec = w.vector()
    total = 0
    for r in rows:
        f = r["feats"]
        if len(f) == 0:
            continue
        if v1:     # stage 1: BM25 top-200 only, bm25 + 2·soft·Σidf
            m = np.zeros(len(f), dtype=bool)
            m[:min(200, r["n_bm25"])] = True
            s = np.where(m, f[:, 0] + 2.0 * f[:, 2] * r["idf_sum"], -np.inf)
        else:
            s = f[:, 0] + r["idf_sum"] * (f @ vec)
        order = np.lexsort((r["ids"], -s))[:k]
        total += bool(r["hits"][order].any())
    return total / len(rows)


def tune() -> None:
    sets = {n: load_cache(n) for n in DEV_SETS}
    for n, rows in sets.items():
        oracle = np.mean([r["hits"].any() for r in rows])
        print(f"{n}: stage-1 Hit@1 {STAGE1_DEV[n]:.3f} (v1 index), oracle (any candidate) {oracle:.3f}")
    grid = {"cov": [0.0, 1.0, 2.0, 3.0, 5.0], "soft": [0.0, 1.0, 2.0, 4.0], "pcov": [0.0, 0.5, 1.0, 2.0],
            "kcov": [0.0, 0.5, 1.0, 2.0, 4.0], "type": [0.0, 0.25, 0.5, 1.0, 2.0], "wiki": [0.0, 0.25, 0.5, 1.0, 2.0],
            "q": [0.0, 1.0, 10.0], "short": [0.0, 0.5, 1.0], "phr": [0.0, 0.5, 1.0, 2.0, 4.0],
            "dcov": [0.0, 0.5, 1.0, 2.0], "prox": [0.0, 0.5, 1.0, 2.0], "dfull": [0.0, 0.5, 1.0, 2.0, 4.0]}
    best = None
    keys = list(grid)
    t0 = time.time()
    # coordinate ascent from the stage-1 point, 3 rounds, objective = mean Hit@1 over both dev sets
    cur = {"cov": 0.0, "soft": 2.0, "pcov": 0.0, "kcov": 0.0, "type": 0.0, "wiki": 0.0, "q": 0.0, "short": 0.0,
           "phr": 0.0, "dcov": 0.0, "prox": 0.0, "dfull": 0.0}
    # stage 1 on its own (v1) index, measured on the same dev questions before the v2 index existed
    base = STAGE1_DEV

    def obj(p):
        # both criteria (R1, R2) count: mean *relative* gain over stage 1 on the two dev sets
        w = Weights(**p)
        return np.mean([hit_at(rows, w) / base[n] for n, rows in sets.items()])

    val = obj(cur)
    for rnd in range(4):
        for k in keys:
            for v in grid[k]:
                p = {**cur, k: v}
                o = obj(p)
                if o > val + 1e-12:
                    cur, val = p, o
        print(f"round {rnd}: {cur} → {val:.4f} ({time.time() - t0:.0f} s)", flush=True)
    best = Weights(**cur)
    for n, rows in sets.items():
        print(f"{n}: Hit@1 {hit_at(rows, best):.3f}  Hit@5 {hit_at(rows, best, 5):.3f}")
    # one-feature ablations around the optimum
    for k in keys:
        p = {**cur, k: 0.0}
        print(f"  without {k:6s}: " + "  ".join(f"{n} {hit_at(rows, Weights(**p)):.3f}" for n, rows in sets.items()))
    _ = itertools, FEATURES


def cap_stats():
    """Capitalisation counts of the corpus (cached)."""
    from engramm.chat.corpus import Corpus
    from engramm.chat.question import CapStats
    from experiments.chat_v2_common import MODEL_DIR
    path = CACHE / "capstats.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    c = Corpus.load(MODEL_DIR)
    cs = CapStats.build(c.tokens, c.tok)
    path.write_bytes(pickle.dumps(cs))
    return cs


def extract_eval(w: Weights, params=None, sets=None, verbose: bool = True) -> dict:
    from engramm.chat.extract import ExtractParams, exact_match, extract, f1
    from engramm.chat.question import analyse
    from engramm.lm.tokenizer import LMTokenizer
    params = params or ExtractParams()
    cs, tok = cap_stats(), LMTokenizer()
    memo: dict = {}

    def initial(word):
        if word not in memo:
            memo[word] = cs.is_name_initial(word, tok)
        return memo[word]

    out = {}
    for name in (sets or DEV_SETS):
        rows = load_cache(name)
        em, fs, by = [], [], {}
        for r in rows:
            f = r["feats"]
            if len(f) == 0:
                em.append(0.0)
                fs.append(0.0)
                continue
            sc = f[:, 0] + r["idf_sum"] * (f @ w.vector())
            order = np.lexsort((r["ids"], -sc))
            texts = [r["texts"][i] for i in order[:params.k]]
            rel = sc[order[:params.k]] / max(r["idf_sum"], 1e-9)
            q = analyse(r["question"])
            x = extract(q, texts, rel, params, initial)
            e, g = exact_match(x.text, r["answers"]), f1(x.text, r["answers"])
            em.append(e)
            fs.append(g)
            by.setdefault(q.atype, []).append(e)
        out[name] = {"em": float(np.mean(em)), "f1": float(np.mean(fs)),
                     "by_type": {k: (len(v), round(float(np.mean(v)), 3)) for k, v in sorted(by.items())}}
        if verbose:
            print(name, out[name], flush=True)
    return out


BEST = Weights()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("cache", "tune", "extract"))
    args = ap.parse_args()
    if args.cmd == "cache":
        build_cache()
    elif args.cmd == "tune":
        tune()
    else:
        extract_eval(BEST)


if __name__ == "__main__":
    main()
