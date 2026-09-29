"""Phase 2 (docs/PREREG_NLP_V0.md): train the tagger, the parser and the intent classifier;
measure on dev (default) or — once — on test.

    python -u -m experiments.nlp_train                 # train on train, measure on dev
    python -u -m experiments.nlp_train --test          # the one registered test run

Data (downloaded by the caller into --data): UD English EWT r2.14 CoNLL-U files and MASSIVE 1.1
(1.1/data/en-US.jsonl). Models go to models/nlp/, results to results/nlp/.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from engramm.nlp import conllu
from engramm.nlp.intent import IntentClassifier, macro_f1
from engramm.nlp.parse import Parser
from engramm.nlp.pos import PerceptronTagger

ROOT = Path(__file__).resolve().parents[1]


def log(msg: str) -> None:
    print(msg, flush=True)


def jackknife_tags(train, folds: int = 4, epochs: int = 8):
    """Predicted tags for every training sentence from a tagger that did not see it."""
    out = [None] * len(train)
    for k in range(folds):
        part = [(s.words, s.upos) for i, s in enumerate(train) if i % folds != k]
        t = PerceptronTagger()
        t.train(part, epochs=epochs, key=f"pos-jk{k}")
        for i, s in enumerate(train):
            if i % folds == k:
                out[i] = t.tag(s.words)
        log(f"jackknife fold {k + 1}/{folds} done")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("/dev/shm/engramm/nlp"))
    ap.add_argument("--test", action="store_true", help="the one registered run on the test parts")
    ap.add_argument("--models", type=Path, default=ROOT / "models" / "nlp")
    args = ap.parse_args()
    t0 = time.time()
    split = "test" if args.test else "dev"
    train = conllu.read(args.data / "en_ewt-ud-train.conllu")
    evals = conllu.read(args.data / f"en_ewt-ud-{split}.conllu")
    log(f"EWT train {len(train):,} sentences, {split} {len(evals):,}")

    tagger = PerceptronTagger()
    tagger.train([(s.words, s.upos) for s in train], epochs=8, log=log)
    right = total = 0
    pred_tags = []
    for s in evals:
        tags = tagger.tag(s.words)
        pred_tags.append(tags)
        right += sum(a == b for a, b in zip(tags, s.upos))
        total += len(s.words)
    pos_acc = right / total
    log(f"N1 UPOS accuracy on {split}: {pos_acc:.4f} ({time.time() - t0:.0f} s)")

    jk = jackknife_tags(train)
    parse_train = [(s.words, jk[i], s.heads, s.deprels) for i, s in enumerate(train)
                   if conllu.is_projective(s.heads)]
    log(f"parser training on {len(parse_train):,} projective sentences")
    parser = Parser()
    parser.train(parse_train, epochs=10, log=log)
    uas_r = las_r = n = 0
    for s, tags in zip(evals, pred_tags):
        heads, labels = parser.parse_labelled(s.words, tags)
        for h, g, lab, glab in zip(heads, s.heads, labels, s.deprels):
            n += 1
            if h == g:
                uas_r += 1
                las_r += lab == glab
    uas, las = uas_r / n, las_r / n
    log(f"N2 UAS on {split}: {uas:.4f}, LAS {las:.4f} ({time.time() - t0:.0f} s)")

    rows = [json.loads(line) for line in (args.data / "1.1" / "data" / "en-US.jsonl").read_text().splitlines()]
    itrain = [(r["utt"], r["intent"]) for r in rows if r["partition"] == "train"]
    ieval = [(r["utt"], r["intent"]) for r in rows if r["partition"] == split]
    clf = IntentClassifier()
    clf.train(itrain, epochs=12, log=log)
    preds = [clf.predict(u)[0] for u, _ in ieval]
    gold = [y for _, y in ieval]
    f1 = macro_f1(gold, preds)
    acc = sum(p == g for p, g in zip(preds, gold)) / len(gold)
    log(f"N3 intent macro-F1 on {split}: {f1:.4f}, accuracy {acc:.4f}")

    dev = conllu.read(args.data / "en_ewt-ud-dev.conllu")[:1000]
    times = []
    for s in dev:
        a = time.perf_counter()
        tags = tagger.tag(s.words)
        parser.parse_labelled(s.words, tags)
        clf.predict(" ".join(s.words))
        times.append(time.perf_counter() - a)
    med = statistics.median(times) * 1000
    log(f"N4 median per sentence: {med:.1f} ms")

    args.models.mkdir(parents=True, exist_ok=True)
    tagger.save(args.models / "pos.json")
    parser.save(args.models / "parse.json")
    clf.save(args.models / "intent.json")
    sizes = {p.name: p.stat().st_size for p in args.models.glob("*.json")}
    res = {"split": split, "prereg": "docs/PREREG_NLP_V0.md", "device": "container",
           "N1": {"upos_accuracy": pos_acc, "pass": pos_acc >= 0.94},
           "N2": {"uas": uas, "las": las, "pass": uas >= 0.84},
           "N3": {"macro_f1": f1, "accuracy": acc, "pass": f1 >= 0.80},
           "N4": {"median_ms": med, "pass": med <= 50.0, "canonical": False},
           "model_bytes": sizes, "seconds": round(time.time() - t0)}
    out = ROOT / "results" / "nlp" / f"nlp_v0_{split}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    log(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
