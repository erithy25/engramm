"""Per-position component probabilities on the evaluation splits (cached).

    python -m experiments.lm_components --scale pilot --parts kn,inf,cache
    python -m experiments.lm_components --scale pilot --parts knn,topic --seed 42

Writes ``models/lm/<scale>/eval/<split>_<part>[_<seed>].npz``. Builds (and
caches) the KN-5 model, the suffix array, and per seed the codebook, the KNN
index and the segment signatures.
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from engramm.lm import knn as K
from engramm.lm.ngram import KNModel, build_kn
from engramm.lm.semantic import Codebook, build_codebook, tiebreak_vector
from engramm.lm.suffix import SuffixIndex, build_suffix_array
from engramm.lm.topic import stream_cache, stream_topic, topic_table
from experiments.lm_common import MODELS_DIR, load_split, load_train

TAUS = (256.0, 1024.0, 4096.0)
BETAS = (4.0, 8.0)
EVAL_SPLITS = ("val_a", "val_b")


def model_dir(scale: str):
    d = MODELS_DIR / scale
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_kn(scale, train, log=print):
    path = model_dir(scale) / "kn5"
    if (path / "meta.npy").exists():
        return KNModel.load(path)
    m = build_kn(np.asarray(train.tokens), order=5, log=log)
    m.save(path)
    return m


def get_sa(scale, train):
    path = model_dir(scale) / "sa.npy"
    if path.exists():
        return np.load(path)
    sa = build_suffix_array(np.asarray(train.tokens))
    np.save(path, sa)
    return sa


def get_hdc(scale, train, seed, log=print):
    d = model_dir(scale)
    cbp, posp, segp = d / f"codebook_{seed}.npz", d / f"knn_pos_{seed}.npy", d / f"segsig_{seed}.npy"
    t = np.ascontiguousarray(train.tokens)
    if cbp.exists():
        cb = Codebook.load(cbp)
    else:
        cb = build_codebook(t, seed, log=log)
        cb.save(cbp)
    if posp.exists():
        pos = np.load(posp)
    else:
        pos = K.build_index(t, cb.classes)
        np.save(posp, pos)
    if segp.exists():
        seg = np.load(segp)
    else:
        seg = K.segment_signatures(t, cb.wide, cb.idf, tiebreak_vector(seed))
        np.save(segp, seg)
    return cb, pos, seg


def doc_bounds(split):
    starts = np.asarray(split.doc_starts, dtype=np.int64)
    ends = np.append(starts[1:] - 1, len(split.tokens) - 1).astype(np.int64)
    return starts, ends


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="pilot")
    ap.add_argument("--parts", default="kn,inf,cache")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--splits", default=",".join(EVAL_SPLITS))
    args = ap.parse_args()
    parts = args.parts.split(",")
    out = model_dir(args.scale) / "eval"
    out.mkdir(exist_ok=True)
    train = load_train(args.scale)
    t = np.ascontiguousarray(train.tokens)
    print(f"{args.scale}: {len(t)} train tokens", flush=True)
    kn = get_kn(args.scale, train) if {"kn", "topic"} & set(parts) else None
    for name in args.splits.split(","):
        ev = load_split(name)
        e = np.ascontiguousarray(ev.tokens)
        positions = np.arange(1, len(e), dtype=np.int64)
        starts, ends = doc_bounds(ev)
        t0 = time.time()
        if "kn" in parts:
            p, found = kn.stream_probs(e)
            np.savez(out / f"{name}_kn.npz", p=p, found=found)
            print(name, "kn", f"{time.time() - t0:.0f} s", flush=True)
        if "inf" in parts:
            idx = SuffixIndex(t, get_sa(args.scale, train))
            k, cnt, cntw = idx.stream_stats(e)
            np.savez(out / f"{name}_inf.npz", k=k, cnt=cnt, cnt_w=cntw)
            print(name, "inf", f"{time.time() - t0:.0f} s", flush=True)
        if "cache" in parts:
            c = stream_cache(e, starts, ends, 1 << 15)
            np.savez(out / f"{name}_cache.npz", p=c[1:])
            print(name, "cache", flush=True)
        if "knn" in parts or "topic" in parts:
            cb, pos, seg = get_hdc(args.scale, train, args.seed)
            tb = tiebreak_vector(args.seed)
        if "knn" in parts:
            t1 = time.time()
            qs = K.stream_query_sigs(e, positions, cb.wide, cb.idf, tb, 16, K.SEG)
            empty = np.zeros(0, dtype=np.int64)
            probs, dmin, ncand = K.stream_knn(t, cb.classes.astype(np.int16), pos, cb.eng, seg, e, qs,
                                              K.kernel_tables(TAUS), empty, empty,
                                              np.zeros(1, dtype=np.uint16), empty,
                                              np.zeros((1, K.SIG_WORDS), dtype=np.uint64), positions)
            np.savez(out / f"{name}_knn_{args.seed}.npz", p=probs, dmin=dmin, ncand=ncand,
                     taus=np.array(TAUS))
            print(name, "knn", f"{time.time() - t1:.0f} s", flush=True)
        if "topic" in parts:
            t1 = time.time()
            tabs = np.stack([topic_table(b) for b in BETAS])
            tp = stream_topic(e, starts, ends, cb.wide, cb.idf, tb, kn.p_uni, tabs)
            np.savez(out / f"{name}_topic_{args.seed}.npz", p=tp[1:], betas=np.array(BETAS))
            print(name, "topic", f"{time.time() - t1:.0f} s", flush=True)


if __name__ == "__main__":
    main()
