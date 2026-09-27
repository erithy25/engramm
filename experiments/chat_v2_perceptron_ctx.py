"""Stage 4 — the span perceptron trained in the setting it is used in (retrieved sentences).

    python -m experiments.chat_v2_perceptron_ctx retrieve   # top-10 sentences for 12,000 training questions
    python -m experiments.chat_v2_perceptron_ctx train      # → models/lm/main/chat2/spanperc_ctx.json

Training questions as in ``chat_v2_spanstats`` (never a test or dev article). For each one the
retriever (frozen stage-1.1 weights) returns its best 10 sentences from the whole corpus; all
candidate spans of those sentences compete, with the same sentence prior as at answer time
(β·log softmax(score/τ)). Any candidate equal to a gold answer is correct. The paragraph
examples of ``chat_v2_perceptron --paragraph`` are trained alongside (prior 0).
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import numpy as np

from engramm.chat.config import EXTRACT, WEIGHTS, cap_ratio
from engramm.chat.corpus import Corpus
from engramm.chat.question import analyse
from engramm.chat.retrieve import Retriever
from engramm.chat.spanstats import SpanPerceptron, WordInfo, features_for_sentence
from engramm.lm.chat import normalize
from engramm.lm.semantic import Codebook
from experiments.chat_v2_common import MODEL_DIR
from experiments.chat_v2_data import CACHE, h64
from experiments.chat_v2_perceptron import build_examples
from experiments.chat_v2_spanstats import name_initial, training_questions

N_QUESTIONS = 12000
K = 10
CTX = CACHE / "train_ctx.pkl"
CTX_NQ = CACHE / "train_ctx_nq.pkl"
NQ_RANGE = (40000, 48000)       # NQ-open train positions in SHAKE-256 order; dev is 0–1,999, tests < 24,000


def nq_training_questions() -> list[dict]:
    from experiments.chat_v2_data import load_nq
    train = load_nq("train")
    return sorted(train, key=lambda q: (h64("nq", q["question"]), q["id"]))[NQ_RANGE[0]:NQ_RANGE[1]]


def retrieve(nq: bool = False) -> None:
    corpus = Corpus.load(MODEL_DIR)
    r = Retriever(corpus)
    if nq:
        qs, path = nq_training_questions(), CTX_NQ
    else:
        qs, path = sorted(training_questions(corpus), key=lambda q: (h64("ctx", q["id"]), q["id"]))[:N_QUESTIONS], CTX
    done = pickle.loads(path.read_bytes()) if path.exists() else {}
    t0 = time.time()
    for i, q in enumerate(qs):
        if q["id"] in done:
            continue
        c = r.candidates(q["question"], WEIGHTS, 120)
        if len(c.ids) == 0:
            done[q["id"]] = ([], [])
            continue
        sc = c.scores(WEIGHTS)
        order = np.lexsort((c.ids, -sc))[:K]
        isum = max(c.query.idf_sum, 1e-9)
        done[q["id"]] = ([c.texts[j] for j in order], [float(sc[j] / isum) for j in order])
        if i % 250 == 0:
            path.write_bytes(pickle.dumps(done))
            print(f"{i:,}/{len(qs):,} ({time.time() - t0:.0f} s)", flush=True)
    path.write_bytes(pickle.dumps(done))
    print("done", len(done), flush=True)


def train(passes: int, beta: float, out: str, use_nq: bool = False) -> None:
    t0 = time.time()
    examples, index, n_q = build_examples(MODEL_DIR, paragraph=True)
    offsets = [np.zeros(len(e[2]) - 1) for e in examples]
    golds = [[e[3]] for e in examples]
    corpus = Corpus.load(MODEL_DIR)
    cb = Codebook.load(MODEL_DIR / "codebook.npz")
    info = WordInfo(corpus.tok, cb.classes, cb.wide)
    initial = name_initial(corpus.tok, cap_ratio(MODEL_DIR.parent / "chat2") or {})
    ctx = pickle.loads(CTX.read_bytes())
    byid = {q["id"]: q for q in training_questions(corpus)}
    if use_nq and CTX_NQ.exists():
        ctx.update(pickle.loads(CTX_NQ.read_bytes()))
        byid.update({q["id"]: q for q in nq_training_questions()})
    n_ctx = 0
    for qid, (texts, rel) in sorted(ctx.items()):
        if not texts:
            continue
        q = byid[qid]
        qa = analyse(q["question"])
        g = {normalize(a) for a in q["answers"]}
        r = np.asarray(rel)
        sw = np.exp((r - r.max()) / EXTRACT.tau)
        sw /= sw.sum()
        ids, offs, prior, pos = [], [0], [], []
        for si, t in enumerate(texts):
            for sp, feats in features_for_sentence(qa, t, info, initial, extended=True):
                if normalize(sp.text) in g:
                    pos.append(len(prior))
                for f in feats:
                    ids.append(index.setdefault(f, len(index)))
                offs.append(len(ids))
                prior.append(beta * float(np.log(max(sw[si], 1e-300))))
        if not pos or len(prior) < 2:
            continue
        examples.append((qid, np.asarray(ids, dtype=np.int32), np.asarray(offs, dtype=np.int64), pos[0]))
        offsets.append(np.asarray(prior))
        golds.append(pos)
        n_ctx += 1
    print(f"{len(examples):,} examples ({n_ctx:,} retrieved), {len(index):,} features", flush=True)
    w = np.zeros(len(index))
    u = np.zeros(len(index))
    c = 1
    order = sorted(range(len(examples)), key=lambda k: (h64("perceptron-ctx", examples[k][0], k), k))
    for p in range(passes):
        mistakes = 0
        for k in order:
            _, ids, offs, _ = examples[k]
            sc = np.add.reduceat(w[ids], offs[:-1]) + offsets[k]
            best = int(np.argmax(sc))
            gp = golds[k]
            gbest = max(gp, key=lambda j: (sc[j], -j))
            if best not in gp:
                mistakes += 1
                gi = ids[offs[gbest]:offs[gbest + 1]]
                bi = ids[offs[best]:offs[best + 1]]
                np.add.at(w, gi, 1.0)
                np.add.at(w, bi, -1.0)
                np.add.at(u, gi, float(c))
                np.add.at(u, bi, -float(c))
            c += 1
        print(f"pass {p + 1}: {mistakes:,} mistakes of {len(order):,}", flush=True)
    w = w - u / c
    names = [None] * len(index)
    for f, k in index.items():
        names[k] = f
    perc = SpanPerceptron({names[k]: float(w[k]) for k in np.flatnonzero(w)}, True)
    perc.save(MODEL_DIR.parent / "chat2" / out)
    meta = {"examples": len(examples), "retrieved_examples": n_ctx, "features": len(index), "passes": passes,
            "beta": beta, "seconds": round(time.time() - t0, 1)}
    (MODEL_DIR.parent / "chat2" / out.replace(".json", "_meta.json")).write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("retrieve", "train"))
    ap.add_argument("--passes", type=int, default=8)
    ap.add_argument("--beta", type=float, default=1.0)
    ap.add_argument("--out", default="spanperc_ctx.json")
    ap.add_argument("--nq", action="store_true", help="retrieve / also train on NQ-open train questions")
    args = ap.parse_args()
    if args.cmd == "retrieve":
        retrieve(args.nq)
    else:
        train(args.passes, args.beta, args.out, args.nq)


if __name__ == "__main__":
    main()
