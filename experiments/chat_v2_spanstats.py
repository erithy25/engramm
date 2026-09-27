"""Count the answer-span statistics of stage 4 (docs/PREREG_CHAT_V2.md v1.1).

    python -m experiments.chat_v2_spanstats        # → models/lm/main/chat2/spanstats.json

Uses only SQuAD questions of articles with SHAKE-256 title bit 0 that are not SQuAD-dev2
articles, without the 1,500 stage-1 questions; test articles (bit 1) are never read.
For each question the gold sentence is taken from its own paragraph (no retrieval), all
candidate spans are generated as at answer time, and the features of the gold span and
of the other candidates are counted.
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np

from engramm.chat.config import cap_ratio
from engramm.chat.corpus import Corpus
from engramm.chat.index import _segment_v2, token_flags
from engramm.chat.question import STOP, analyse
from engramm.chat.spanstats import SpanStats, WordInfo, features_for_sentence
from engramm.lm.chat import MAX_SENT, normalize
from engramm.lm.semantic import Codebook
from experiments.chat_eval import COVER, load_squad, split
from experiments.chat_v2_common import MODEL_DIR, squad_v2_splits
from experiments.chat_v2_data import CACHE, h64


def name_initial(tok, cap: dict):
    memo: dict = {}

    def f(word: str) -> bool:
        if word not in memo:
            if word.lower() in STOP:
                memo[word] = False
            else:
                ids = tok.encode(" " + word)
                first = tok.token_bytes()[ids[0]].decode("utf-8", errors="replace").strip().lower()
                r = cap.get(first)
                memo[word] = True if r is None else r > 0.5
        return memo[word]
    return f


def sentences_with_offsets(context: str, tok, flags) -> list[tuple[int, str]]:
    ids = np.array([0] + tok.encode(context) + [0], dtype=np.uint16)
    st, ln = _segment_v2(ids, *flags, MAX_SENT)
    out, pos = [], 0
    for a, b in zip(st, ln):
        t = tok.decode(ids[a:a + b])
        out.append((pos, t))
        pos += len(t)
    return out


def training_questions(corpus: Corpus) -> list[dict]:
    squad = load_squad()
    dev2, _ = squad_v2_splits(corpus)
    dev_titles = {q["title"] for q in dev2}
    pool_ids = set(json.loads((CACHE / "squad_pool_v1.json").read_text())["pool"])
    pool = [q for q in squad if q["id"] in pool_ids]
    d1, t1 = split(pool)
    stage1 = {q["id"] for q in d1 + t1}
    _ = COVER
    return [q for q in squad if h64("article", q["title"]) & 1 == 0 and q["title"] not in dev_titles
            and q["id"] not in stage1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(MODEL_DIR))
    args = ap.parse_args()
    t0 = time.time()
    from pathlib import Path
    model_dir = Path(args.model)
    corpus = Corpus.load(model_dir)
    tok = corpus.tok
    cb = Codebook.load(model_dir / "codebook.npz")
    info = WordInfo(tok, cb.classes, cb.wide)
    cap = cap_ratio(model_dir.parent / "chat2") or {}
    initial = name_initial(tok, cap)
    flags = token_flags(tok)
    qs = training_questions(corpus)
    print(f"{len(qs):,} training questions from {len({q['title'] for q in qs})} articles", flush=True)
    stats = SpanStats()
    covered = used = 0
    ctx_cache: dict[str, list] = {}
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
        used += 1
        qa = analyse(q["question"])
        g = normalize(gold)
        cands = features_for_sentence(qa, text.strip(), info, initial)
        hit = False
        for sp, feats in cands:
            pos = normalize(sp.text) == g
            hit |= pos
            stats.add(feats, pos)
        covered += hit
        if i % 5000 == 0:
            print(f"{i:,}/{len(qs):,}  coverage {covered / max(used, 1):.3f}  ({time.time() - t0:.0f} s)", flush=True)
    out = model_dir.parent / "chat2" / "spanstats.json"
    stats.save(out)
    meta = {"questions": len(qs), "used": used, "gold_among_candidates": covered / max(used, 1),
            "positives": stats.n_pos, "negatives": stats.n_neg, "features": len(set(stats.pos) | set(stats.neg)),
            "seconds": round(time.time() - t0, 1)}
    (model_dir.parent / "chat2" / "spanstats_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == "__main__":
    main()
