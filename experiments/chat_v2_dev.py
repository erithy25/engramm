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
from pathlib import Path

import numpy as np

from engramm.chat.retrieve import FEATURES, Retriever, Weights
from engramm.lm.chat import contains_answer
from experiments.chat_v2_common import load_all
from experiments.chat_v2_data import CACHE

DEV_SETS = ("sq_dev", "nq_dev")
STAGE1_DEV = {"sq_dev": 0.403, "nq_dev": 0.022}


def cache_path(name: str):
    import os
    from experiments.chat_v2_common import CHAT_INDEX
    base = Path(os.environ["ENGRAMM_CACHE_DIR"]) if os.environ.get("ENGRAMM_CACHE_DIR") else CACHE
    return base / (f"dev_cands_{name}.pkl" if CHAT_INDEX == "chat2" else f"dev_cands_{name}_{CHAT_INDEX}.pkl")


def build_cache(names=DEV_SETS) -> None:
    corpus, data = load_all()
    if "sq_spent" in names:     # every spent SQuAD test question (v2 test, test3–test11)
        data["sq_spent"] = data["sq_test"] + spent_squad(upto=11)
    if "sq_test12" in names:    # the spent v12 test (newly read paragraphs of the test articles)
        from experiments.chat_v12_data import squad_v12_test
        data["sq_test12"] = squad_v12_test()
    if "sq_train" in names:     # 8,000 training questions (title bit 0, not a dev article, not stage 1): ranker training
        from engramm.chat.corpus import Corpus as _C
        from experiments.chat_v2_common import MODEL_DIR
        from experiments.chat_v2_perceptron import training_questions
        from experiments.chat_v2_data import h64 as _h
        tq = training_questions(_C.load(MODEL_DIR, index_name="chat3"))
        data["sq_train"] = sorted(tq, key=lambda q: (_h("rank", q["id"]), q["id"]))[:8000]
    if "sq_test13" in names:    # the spent v13 test
        from experiments.chat_v13_data import squad_v13_test
        data["sq_test13"] = squad_v13_test()
    if "sq_dev12" in names:     # v12 dev: newly read paragraphs of the dev articles
        from experiments.chat_v12_data import squad_v12_dev
        data["sq_dev12"] = squad_v12_dev()
    r = Retriever(corpus)
    for name in names:
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


_WV = {}


def word_vectors(tok, kind: str = "wide"):
    """word → its counted meaning vector (single-token words only), for the HDC anchors."""
    if kind not in _WV:
        from engramm.lm.semantic import Codebook
        from experiments.chat_v2_common import MODEL_DIR
        M = getattr(Codebook.load(MODEL_DIR / "codebook.npz"), kind)
        cache: dict = {}

        def vec(w: str):
            if w not in cache:
                ids = tok.encode(" " + w)
                cache[w] = np.asarray(M[ids[0]]) if len(ids) == 1 else None
            return cache[w]
        _WV[kind] = vec
    return _WV[kind]


SPAN_FILE = "spanstats.json"


def span_model(tok):
    from engramm.chat.spanstats import SpanStats, WordInfo
    from engramm.lm.semantic import Codebook
    from experiments.chat_v2_common import MODEL_DIR
    key = "span:" + SPAN_FILE
    if key not in _WV:
        cb = Codebook.load(MODEL_DIR / "codebook.npz")
        _WV[key] = (SpanStats.load(MODEL_DIR.parent / "chat2" / SPAN_FILE), WordInfo(tok, cb.classes, cb.wide))
    return _WV[key]


def extract_eval(w: Weights, params=None, sets=None, verbose: bool = True) -> dict:
    from engramm.chat.extract import ExtractParams, exact_match, extract, f1
    from engramm.chat.question import analyse
    from engramm.lm.tokenizer import LMTokenizer
    params = params or ExtractParams()
    cs, tok = cap_stats(), LMTokenizer()
    memo: dict = {}
    wv = word_vectors(tok)
    stats, info = span_model(tok) if params.nb > 0 else (None, None)

    from engramm.chat.bot import name_initial_rule

    def initial(word):
        if word not in memo:
            memo[word] = name_initial_rule(word, tok, cs.ratio)
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
            x = extract(q, texts, rel, params, initial, wv, stats, info)
            e, g = exact_match(x.text, r["answers"]), f1(x.text, r["answers"])
            em.append(e)
            fs.append(g)
            by.setdefault(q.atype, []).append(e)
        out[name] = {"em": float(np.mean(em)), "f1": float(np.mean(fs)),
                     "by_type": {k: (len(v), round(float(np.mean(v)), 3)) for k, v in sorted(by.items())}}
        if verbose:
            print(name, out[name], flush=True)
    return out


# stage 1.1 weights chosen on dev (coordinate ascent, `tune`, 2026-09-27)
BEST = Weights(cov=5.0, soft=0.0, pcov=1.0, kcov=2.0, type=2.0, wiki=0.25, q=1.0, short=0.5, phr=0.5, dcov=2.0,
               prox=0.5, dfull=1.0)


def spent_squad(upto: int = 8) -> list[dict]:
    """The SQuAD questions of the spent test rounds test3–test<upto> (default test3–test8, the v9 θ set)."""
    import importlib
    import json as _json

    from experiments.chat_eval import load_squad, split as split1
    from experiments.chat_v2_data import CACHE as _C
    pool_ids = set(_json.loads((_C / "squad_pool_v1.json").read_text())["pool"])
    pool = [q for q in load_squad() if q["id"] in pool_ids]
    d1, t1 = split1(pool)
    ex = {q["id"] for q in d1 + t1}
    out = []
    for v in range(3, upto + 1):
        mod = importlib.import_module(f"experiments.chat_v{v}_data")
        out += getattr(mod, f"squad_v{v}_test")(pool, ex)
    return out


def pipeline(n_sq: int | None = None, n_nq: int | None = None, v3: bool = False, v9: bool = False,
             v12: bool = False, v13: bool = False, v14: bool = False, dump: str | None = None) -> dict:
    """The complete bot (frozen config, θ = 0) on SQuAD-dev2 and NQ-dev: Hit@1, EM, F1, and θ
    for A2 by the registered rule (smallest θ with dev precision ≥ 55 %)."""
    import dataclasses

    from engramm.chat.bot import ChatBot, TextMemory
    from engramm.chat.config import FROZEN, cap_ratio
    from engramm.chat.extract import exact_match, f1
    corpus, data = load_all()
    if v3:      # v3 development may use the spent v2 test data as well (PREREG_CHAT_V3 §2)
        data["sq_dev"] = data["sq_dev"] + data["sq_test"]
        data["nq_dev"] = data["nq_dev"][:0]
    if v9:      # v9: θ on every spent SQuAD question (dev2, v2 test, test3–test8; PREREG_CHAT_V9)
        data["sq_dev"] = data["sq_dev"] + data["sq_test"] + spent_squad()
        data["nq_dev"] = data["nq_dev"][:0]
    if v12:     # v12: θ on Dev12 (newly read paragraphs of the dev articles, the distribution of Test12)
        from experiments.chat_v12_data import squad_v12_dev
        data["sq_dev"] = squad_v12_dev()
        data["nq_dev"] = data["nq_dev"][:0]
    if v13:     # v13: θ on the spent Test12 (newly read paragraphs of the test articles, the distribution of Test13)
        from experiments.chat_v12_data import squad_v12_test
        data["sq_dev"] = squad_v12_test()
        data["nq_dev"] = data["nq_dev"][:0]
    if v14:     # v14: θ on the spent Test12 + Test13 (10,000 newly read test-article questions)
        from experiments.chat_v12_data import squad_v12_test
        from experiments.chat_v13_data import squad_v13_test
        data["sq_dev"] = squad_v12_test() + squad_v13_test()
        data["nq_dev"] = data["nq_dev"][:0]
    cfg = dataclasses.replace(FROZEN, theta=-np.inf)    # every answer; θ is chosen below
    bot = ChatBot(TextMemory(), corpus, cfg, cap_ratio(corpus.index_dir))
    out = {}
    for name, n in (("sq_dev", n_sq), ("nq_dev", n_nq)):
        qs = data[name][:n] if n else data[name]
        if not qs:
            continue
        rows = []
        t0 = time.time()
        for q in qs:
            bot.context = {"answer": None, "atype": None, "mention": None, "last_learned": None}
            rep = bot.ask(q["question"])
            top = bot.last_rows
            guess = rep.guess if rep.guess is not None else rep.answer
            rows.append((bool(top) and contains_answer(top[0][3], q["answers"]), exact_match(guess, q["answers"]),
                         f1(guess, q["answers"]), rep.answer is not None, rep.confidence, rep.seconds))
        a = np.array(rows, dtype=float)
        if dump:
            np.save(f"{dump}_{name}.npy", a)
        hit, em, fs, ans, conf, sec = a.T
        res = {"n": len(qs), "hit1": hit.mean(), "em": em.mean(), "f1": fs.mean(), "median_s": float(np.median(sec)),
               "answerable": ans.mean()}
        if name == "sq_dev":
            theta = None
            for t in sorted(set(conf[ans == 1])):
                m = (ans == 1) & (conf >= t)
                if m.any() and em[m].mean() >= 0.55:
                    theta = float(t)
                    break
            m = (ans == 1) & (conf >= (theta if theta is not None else np.inf))
            res.update({"theta": theta, "coverage_at_theta": float(m.mean()),
                        "precision_at_theta": float(em[m].mean()) if m.any() else 0.0})
        out[name] = res
        print(name, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()},
              f"({time.time() - t0:.0f} s)", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("cache", "cache_spent", "cache_dev12", "cache_test12", "cache_test13", "cache_train", "tune", "extract", "pipeline", "pipeline3", "pipeline9", "pipeline12", "pipeline13", "pipeline14"))
    args = ap.parse_args()
    if args.cmd == "cache":
        build_cache()
    elif args.cmd == "cache_spent":
        build_cache(("sq_spent",))
    elif args.cmd == "cache_dev12":
        build_cache(("sq_dev12",))
    elif args.cmd == "cache_test12":
        build_cache(("sq_test12",))
    elif args.cmd == "cache_test13":
        build_cache(("sq_test13",))
    elif args.cmd == "cache_train":
        build_cache(("sq_train",))
    elif args.cmd == "tune":
        tune()
    elif args.cmd == "pipeline":
        pipeline()
    elif args.cmd == "pipeline3":
        pipeline(v3=True)
    elif args.cmd == "pipeline9":
        pipeline(v9=True)
    elif args.cmd == "pipeline12":
        pipeline(v12=True)
    elif args.cmd == "pipeline13":
        pipeline(v13=True, dump="/dev/shm/engramm/pipe13")
    elif args.cmd == "pipeline14":
        pipeline(v14=True, dump="/dev/shm/engramm/pipe14")
    else:
        extract_eval(BEST)


if __name__ == "__main__":
    main()
