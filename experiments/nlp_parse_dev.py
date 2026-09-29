"""Phase 2, dev only: compare parser feature groups (docs/PREREG_NLP_V0.md; test is not read).

    python -u -m experiments.nlp_parse_dev --groups lab --epochs 6,10,15
    python -u -m experiments.nlp_parse_dev --groups lab+x --epochs 10,15

Tags for training come from 4-fold jackknifed taggers (UPOS and, for group ``x``, XPOS); dev is
tagged by taggers trained on all of train. Tags are cached in --data/jk_tags.json.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from engramm.nlp import conllu
from engramm.nlp.parse import Parser
from engramm.nlp.pos import PerceptronTagger


def tags_for(train, dev, field: str, folds: int = 4):
    jk = [None] * len(train)
    for k in range(folds):
        t = PerceptronTagger()
        key = "pos-jk" if field == "upos" else f"{field}-jk"
        t.train([(s.words, getattr(s, field)) for i, s in enumerate(train) if i % folds != k], epochs=8, key=f"{key}{k}")
        for i, s in enumerate(train):
            if i % folds == k:
                jk[i] = t.tag(s.words)
        print(f"{field} jackknife {k + 1}/{folds}", flush=True)
    t = PerceptronTagger()
    t.train([(s.words, getattr(s, field)) for s in train], epochs=8, key="pos" if field == "upos" else field)
    dv = [t.tag(s.words) for s in dev]
    acc = sum(a == b for s, g in zip(dev, dv) for a, b in zip(g, getattr(s, field))) / sum(len(s.words) for s in dev)
    print(f"{field} dev accuracy {acc:.4f}", flush=True)
    return jk, dv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("/dev/shm/engramm/nlp"))
    ap.add_argument("--groups", default="lab")
    ap.add_argument("--epochs", default="10")
    ap.add_argument("--explore-from", type=int, default=0)
    args = ap.parse_args()
    train = conllu.read(args.data / "en_ewt-ud-train.conllu")
    dev = conllu.read(args.data / "en_ewt-ud-dev.conllu")
    cache = args.data / "jk_tags.json"
    tags = json.loads(cache.read_text()) if cache.exists() else {}
    groups = set(args.groups.split("+"))
    for field in ["upos"] + (["xpos"] if "x" in groups else []):
        if field not in tags:
            tags[field] = tags_for(train, dev, field)
            tmp = cache.with_suffix(".tmp")
            tmp.write_text(json.dumps(tags))
            tmp.replace(cache)
    jk, dvt = tags["upos"]
    jkx, dvx = tags.get("xpos", [[None] * len(train), [None] * len(dev)]) if "x" in groups else \
        ([None] * len(train), [None] * len(dev))
    data = [(s.words, jk[i], s.heads, s.deprels, jkx[i]) for i, s in enumerate(train) if conllu.is_projective(s.heads)]
    eps = sorted(int(e) for e in args.epochs.split(","))
    t0 = time.time()

    def evaluate(ep, parser):
        u = lab = n = 0
        t1 = time.time()
        for s, tg, xt in zip(dev, dvt, dvx):
            heads, labels = parser.parse_labelled(s.words, tg, xt)
            for h, g, la, gl in zip(heads, s.heads, labels, s.deprels):
                n += 1
                u += h == g
                lab += h == g and la == gl
        print(json.dumps({"groups": args.groups, "explore_from": args.explore_from, "epochs": ep, "dev_uas": round(u / n, 4), "dev_las": round(lab / n, 4),
                          "ms_per_sentence": round((time.time() - t1) / len(dev) * 1000, 2),
                          "at_seconds": round(t1 - t0)}), flush=True)

    p = Parser(groups)
    p.train(data, max(eps), log=lambda m: print(m, flush=True), checkpoints=set(eps), on_checkpoint=evaluate,
            explore_from=args.explore_from)
    evaluate(max(eps), p)


if __name__ == "__main__":
    main()
