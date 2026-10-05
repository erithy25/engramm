"""U4 measurements for local learning (docs/PREREG_UNDERSTAND_V0.md):

1. Correction test: a classifier trained on frames_train.jsonl only; every sentence of frames_train2.jsonl it gets
   wrong is corrected once, one after the
   other, in one learning state (as a user would over time). At the end each corrected sentence is parsed again; the
   share that is wrong again is "the same error returns" (threshold <= 5 %).
2. Forgetting: after every step, "forget that" must give back the learning file byte for byte (threshold 100 %).

    python -m experiments.probes.learn_eval [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    from engramm.learn.state import LearnState
    from engramm.understand import classify
    from engramm.understand.classify import FrameClassifier, features
    from engramm.understand.frames import parse
    from experiments.frame_train import featurise, train

    def load(name):
        p = ROOT / "experiments/probes" / name
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    # a model that has not seen the sentences it is corrected on: trained on the first set, corrected on the second
    clf = FrameClassifier(train(featurise(load("frames_train.jsonl")), 12))
    classify._CLF = clf
    rows = load("frames_train2.jsonl")
    with tempfile.TemporaryDirectory() as tmp:
        st = LearnState(Path(tmp) / "learn.json")
        wrong, forget_ok, forget_n = [], 0, 0
        for r in rows:
            gold = r["kind"] if r["kind"] != "NONE" else ""
            got = parse(r["text"], r["lang"], extra=st.extra).kind
            if got == gold:
                continue
            f0 = parse(r["text"], r["lang"], use_model=False)
            feats = features(f0, r["text"], f0.kind)
            scores = clf.p.scores(feats)
            for k, d in st.extra.items():
                if k in feats and k != "__ex__":
                    for c, v in d.items():
                        scores[c] = scores.get(c, 0.0) + v
            before = st.to_bytes()
            op = st.correct(feats, scores, gold or "NONE", got or "NONE", text=r["text"])
            if op is None:
                continue
            wrong.append((r, gold))
            if len(wrong) % 10 == 0:              # every tenth step: learn it, forget it, learn it again
                st.forget(op["n"])
                forget_n += 1
                forget_ok += st.to_bytes() == before
                st.correct(feats, scores, gold or "NONE", got or "NONE", text=r["text"])
            if a.limit and len(wrong) >= a.limit:
                break
        back = sum(parse(r["text"], r["lang"], extra=st.extra).kind != gold for r, gold in wrong)
        # also without the stored sentences: how well the weight changes alone carry the correction
        weights = {k: v for k, v in st.extra.items() if k != "__ex__"}
        back_w = sum(parse(r["text"], r["lang"], extra=weights).kind != gold for r, gold in wrong)
        print(f"(weights alone, without the stored sentences: {back_w} = {back_w / max(1, len(wrong)):.1%})")
        print(f"corrections: {len(wrong)}; same error back at the end: {back} = {back / max(1, len(wrong)):.1%}")
        print(f"forget-that bit-identical: {forget_ok}/{forget_n}")


if __name__ == "__main__":
    main()
