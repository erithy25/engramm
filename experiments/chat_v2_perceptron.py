"""Stage 4 — the answer span by an averaged perceptron over counted features.

    python -m experiments.chat_v2_perceptron      # → models/lm/main/chat2/spanperc.json

Same training questions and gold sentences as ``chat_v2_spanstats`` (SQuAD articles that are
neither test nor dev articles, without the stage-1 questions; test articles are never read).
For each question the candidates of its gold sentence are scored with the current weights; if
the best one is not the gold span, every feature of the gold span counts +1 and every feature
of the chosen span −1. The saved weights are the averages over all steps of 5 passes (in
SHAKE-256 order), so each weight is a (fractional) count of corrections.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from engramm.chat.config import cap_ratio
from engramm.chat.corpus import Corpus
from engramm.chat.index import token_flags
from engramm.chat.question import analyse
from engramm.chat.spanstats import SpanPerceptron, WordInfo, features_for_sentence
from engramm.lm.chat import normalize
from engramm.lm.semantic import Codebook
from experiments.chat_v2_common import MODEL_DIR
from experiments.chat_v2_data import h64
from experiments.chat_v2_spanstats import name_initial, sentences_with_offsets, training_questions


def build_examples(model_dir: Path, paragraph: bool = False, domain: bool = False, soft: bool = False,
                   ext=True, max_chunk: int = 5):
    corpus = Corpus.load(model_dir)
    tok = corpus.tok
    cb = Codebook.load(model_dir / "codebook.npz")
    info = WordInfo(tok, cb.classes, cb.wide)
    cap = cap_ratio(model_dir.parent / "chat2") or {}
    initial = name_initial(tok, cap)
    flags = token_flags(tok)
    qs = training_questions(corpus)
    index: dict[str, int] = {}
    examples = []
    t0 = time.time()
    ctx_cache: dict = {}
    for i, q in enumerate(qs):
        gold, start = q["answers"][0], q["answer_starts"][0]
        sents = ctx_cache.get(q["context"])
        if sents is None:
            sents = sentences_with_offsets(q["context"], tok, flags)
            ctx_cache = {q["context"]: sents} if len(ctx_cache) > 50 else {**ctx_cache, q["context"]: sents}
        text = None
        for off, t in sents:
            if off <= start < off + len(t):
                if start + len(gold) <= off + len(t):
                    text = t
                break
        if text is None:
            continue
        qa = analyse(q["question"])
        g = normalize(gold)
        cands = features_for_sentence(qa, text.strip(), info, initial, extended=ext, domain=domain,
                                      max_chunk=max_chunk)
        golds = [k for k, (sp, _) in enumerate(cands) if normalize(sp.text) == g]
        if soft and not golds:
            # no exact span: the candidates with the best token F1 (at least 0.5) count as right
            from engramm.chat.extract import f1 as tok_f1
            fs = [tok_f1(sp.text, [gold]) for sp, _ in cands]
            best_f = max(fs) if fs else 0.0
            if best_f >= 0.5:
                golds = [k for k, v in enumerate(fs) if v == best_f]
        if paragraph and golds:
            # the other sentences of the paragraph compete too (their spans are wrong answers)
            others = []
            for _, t in sents:
                if t is not text and t.strip():
                    others += [c for c in features_for_sentence(qa, t.strip(), info, initial, extended=ext, domain=domain,
                                                              max_chunk=max_chunk)
                               if normalize(c[0].text) != g]
            cands = cands + others
        if not golds or len(cands) < 2:
            continue
        ids, offs = [], [0]
        for _, feats in cands:
            for f in feats:
                ids.append(index.setdefault(f, len(index)))
            offs.append(len(ids))
        examples.append((q["id"], np.asarray(ids, dtype=np.int32), np.asarray(offs, dtype=np.int64),
                         golds[0] if not soft else tuple(golds)))
        if i % 5000 == 0:
            print(f"{i:,}/{len(qs):,} examples {len(examples):,} features {len(index):,} ({time.time() - t0:.0f} s)",
                  flush=True)
    return examples, index, len(qs)


def train(examples, n_features: int, passes: int = 5):
    w = np.zeros(n_features, dtype=np.float64)
    u = np.zeros(n_features, dtype=np.float64)       # Σ step · update, for the average
    c = 1
    order = sorted(range(len(examples)), key=lambda k: (h64("perceptron", examples[k][0]), k))
    for p in range(passes):
        mistakes = 0
        for k in order:
            _, ids, offs, gold = examples[k]
            sc = np.add.reduceat(w[ids], offs[:-1])
            best = int(np.argmax(sc))
            if isinstance(gold, tuple):
                if best in gold:
                    c += 1
                    continue
                gold = max(gold, key=lambda j: (sc[j], -j))
            if best != gold and sc[best] >= sc[gold]:
                mistakes += 1
                gi = ids[offs[gold]:offs[gold + 1]]
                bi = ids[offs[best]:offs[best + 1]]
                np.add.at(w, gi, 1.0)
                np.add.at(w, bi, -1.0)
                np.add.at(u, gi, float(c))
                np.add.at(u, bi, -float(c))
            c += 1
        print(f"pass {p + 1}: {mistakes:,} mistakes of {len(order):,}", flush=True)
    return w - u / c


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(MODEL_DIR))
    ap.add_argument("--passes", type=int, default=5)
    ap.add_argument("--paragraph", action="store_true", help="candidates of the whole paragraph compete")
    ap.add_argument("--out", default="spanperc.json")
    ap.add_argument("--max-chunk", type=int, default=5)
    ap.add_argument("--ext2", action="store_true", help="second set of conjunction features")
    ap.add_argument("--soft", action="store_true", help="best-F1 candidates are right when no exact span exists")
    args = ap.parse_args()
    t0 = time.time()
    model_dir = Path(args.model)
    examples, index, n_q = build_examples(model_dir, args.paragraph, soft=args.soft, ext=2 if args.ext2 else True,
                                         max_chunk=args.max_chunk)
    w = train(examples, len(index), args.passes)
    names = [None] * len(index)
    for f, k in index.items():
        names[k] = f
    perc = SpanPerceptron({names[k]: float(w[k]) for k in np.flatnonzero(w)}, 2 if args.ext2 else True, False,
                          args.max_chunk)
    out = model_dir.parent / "chat2" / args.out
    perc.save(out)
    meta = {"questions": n_q, "examples": len(examples), "features": len(index), "nonzero": len(perc.w),
            "passes": args.passes, "seconds": round(time.time() - t0, 1)}
    meta["paragraph"] = args.paragraph
    (model_dir.parent / "chat2" / args.out.replace(".json", "_meta.json")).write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == "__main__":
    main()
