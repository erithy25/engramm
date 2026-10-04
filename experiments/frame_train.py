"""Train the situation classifier (engramm/understand/classify.py) on experiments/probes/frames_train.jsonl and frames_train2.jsonl.

    python -m experiments.frame_train [--epochs 12] [--folds 5]

Reports 5-fold cross-validation on the training set and the score on the separate development set
(experiments/probes/frames_dev.jsonl), then trains on all training lines and writes the model. The sealed test set is
never used here.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engramm.nlp.perceptron import AveragedPerceptron  # noqa: E402
from engramm.understand import frames as fr  # noqa: E402
from engramm.understand.classify import KINDS, features, save  # noqa: E402


def featurise(rows):
    out = []
    for r in rows:
        f = fr.parse(r["text"], r["lang"], use_model=False)
        out.append((features(f, r["text"], f.kind), r["kind"]))
    return out


def train(data, epochs: int, seed: int = 7) -> AveragedPerceptron:
    p = AveragedPerceptron(KINDS)
    rnd = random.Random(seed)
    data = list(data)
    for _ in range(epochs):
        rnd.shuffle(data)
        for feats, gold in data:
            p.update(gold, p.predict(feats), feats)
    p.average()
    return p


def accuracy(p, data) -> float:
    return sum(p.predict(f) == g for f, g in data) / max(1, len(data))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--folds", type=int, default=5)
    a = ap.parse_args(argv)
    rows = [json.loads(x) for name in ("frames_train.jsonl", "frames_train2.jsonl")
            if (ROOT / "experiments/probes" / name).exists()
            for x in (ROOT / "experiments/probes" / name).read_text().splitlines() if x.strip()]
    dev = [json.loads(x) for x in (ROOT / "experiments/probes/frames_dev.jsonl").read_text().splitlines() if x.strip()]
    data, dev_data = featurise(rows), featurise(dev)
    rule_train = sum(fr.parse(r["text"], r["lang"], use_model=False).kind == (r["kind"] if r["kind"] != "NONE" else "")
                     for r in rows) / len(rows)
    print(f"rules alone on the training set: {rule_train:.1%}")
    idx = list(range(len(data)))
    random.Random(3).shuffle(idx)
    accs = []
    for k in range(a.folds):
        test_i = set(idx[k::a.folds])
        p = train([data[i] for i in idx if i not in test_i], a.epochs)
        accs.append(accuracy(p, [data[i] for i in test_i]))
    print(f"cross-validation ({a.folds} folds): {sum(accs) / len(accs):.1%}  " + " ".join(f"{x:.1%}" for x in accs))
    p = train(data, a.epochs)
    print(f"development set: {accuracy(p, dev_data):.1%}")
    save(p)
    print(f"weights: {sum(len(w) for w in p.weights.values())} in {len(p.weights)} features")


if __name__ == "__main__":
    main()
