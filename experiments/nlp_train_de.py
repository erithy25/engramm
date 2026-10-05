"""German tagger and parser (V1 plan item): the same averaged-perceptron tagger and arc-hybrid parser as for English
(experiments/nlp_train.py), trained on UD German GSD (CC BY-SA 4.0); measured on its dev part.

    python -u -m experiments.nlp_train_de --data /dev/shm/engramm/ud --models /dev/shm/engramm/models_de

Models: pos_de.json, xpos_de.json, parse_de.json; result: results/nlp/nlp_de_dev.json.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from engramm.nlp import conllu
from engramm.nlp.parse import Parser
from engramm.nlp.pos import PerceptronTagger
from experiments.nlp_train import PARSER_EPOCHS, PARSER_EXPLORE_FROM, PARSER_GROUPS, jackknife_tags, log

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("/dev/shm/engramm/ud"))
    ap.add_argument("--models", type=Path, default=Path("/dev/shm/engramm/models_de"))
    a = ap.parse_args()
    t0 = time.time()
    train = conllu.read(a.data / "de_gsd-ud-train.conllu")
    dev = conllu.read(a.data / "de_gsd-ud-dev.conllu")
    log(f"GSD train {len(train):,}, dev {len(dev):,}")
    tagger = PerceptronTagger()
    tagger.train([(s.words, s.upos) for s in train], epochs=8, log=log)
    xtagger = PerceptronTagger()
    xtagger.train([(s.words, s.xpos) for s in train], epochs=8, key="xpos")
    pred = [tagger.tag(s.words) for s in dev]
    pos_acc = sum(a == b for p, s in zip(pred, dev) for a, b in zip(p, s.upos)) / sum(len(s.words) for s in dev)
    log(f"UPOS on dev {pos_acc:.4f}")
    jk = jackknife_tags(train)
    jkx = jackknife_tags(train, field="xpos")
    parse_train = [(s.words, jk[i], s.heads, s.deprels, jkx[i]) for i, s in enumerate(train)
                   if conllu.is_projective(s.heads)]
    log(f"parser training on {len(parse_train):,} projective sentences")
    parser = Parser(PARSER_GROUPS)
    parser.train(parse_train, epochs=PARSER_EPOCHS, log=log, explore_from=PARSER_EXPLORE_FROM)
    u = l = n = 0
    for s, tags in zip(dev, pred):
        heads, labels = parser.parse_labelled(s.words, tags, xtagger.tag(s.words))
        for h, g, lab, glab in zip(heads, s.heads, labels, s.deprels):
            n += 1
            if h == g:
                u += 1
                l += lab == glab
    log(f"UAS on dev {u / n:.4f}, LAS {l / n:.4f} ({time.time() - t0:.0f} s)")
    a.models.mkdir(parents=True, exist_ok=True)
    tagger.save(a.models / "pos_de.json")
    xtagger.save(a.models / "xpos_de.json")
    parser.save(a.models / "parse_de.json")
    res = {"treebank": "UD German GSD", "split": "dev", "upos_accuracy": pos_acc, "uas": u / n, "las": l / n,
           "model_bytes": {p.name: p.stat().st_size for p in a.models.glob("*_de.json")}, "seconds": round(time.time() - t0)}
    out = ROOT / "results" / "nlp" / "nlp_de_dev.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    log(json.dumps(res))


if __name__ == "__main__":
    main()
