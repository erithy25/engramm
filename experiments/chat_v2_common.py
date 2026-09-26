"""Shared loading for the ENGRAMM-Chat v2 experiments (docs/PREREG_CHAT_V2.md)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from engramm.chat.corpus import Corpus
from experiments.chat_eval import COVER, load_squad, paragraph_coverage, split
from experiments.chat_v2_data import CACHE, nq_splits, squad_splits
from experiments.lm_common import MODELS_DIR

MODEL_DIR = MODELS_DIR / "main" / "model"


def squad_v2_splits(corpus: Corpus, model_dir: Path = MODEL_DIR) -> tuple[list[dict], list[dict]]:
    """(dev2, test2). The pool (13-gram coverage ≥ 0.8) is computed once and cached."""
    squad = load_squad()
    cache = CACHE / "squad_pool_v1.json"
    if cache.exists():
        ids = set(json.loads(cache.read_text())["pool"])
    else:
        view = SimpleNamespace(tokens=np.asarray(corpus.tokens), tok=corpus.tok,
                               index=SimpleNamespace(sa=np.load(model_dir / "sa.npy", mmap_mode="r")))
        cov = paragraph_coverage(view, sorted({q["context"] for q in squad}))
        ids = {q["id"] for q in squad if cov[q["context"]] >= COVER}
        cache.write_text(json.dumps({"pool": sorted(ids)}))
    pool = [q for q in squad if q["id"] in ids]
    dev1, test1 = split(pool)
    return squad_splits(pool, {q["id"] for q in dev1 + test1})


def load_all(model_dir: Path = MODEL_DIR):
    corpus = Corpus.load(model_dir)
    sq_dev, sq_test = squad_v2_splits(corpus, model_dir)
    nq_dev, nq_test = nq_splits()
    return corpus, {"sq_dev": sq_dev, "sq_test": sq_test, "nq_dev": nq_dev, "nq_test": nq_test}
