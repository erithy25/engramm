"""Data of ENGRAMM-Chat v12 (docs/PREREG_CHAT_V12.md): pool v3, the new dev set and the test set.

Pool v3 consists of the SQuAD questions whose paragraph ENGRAMM read in v12 (the segment of
``chat4``, ``experiments/chat_squad_read.py``). These paragraphs were not read before, so no
question of pool v3 was ever in a pool, a dev set or a test set.

* **Dev12:** pool-v3 questions of the 42 SQuAD-Dev2 articles (the development articles). The span
  perceptron was never trained on these articles.
* **Test12:** pool-v3 questions of the test articles (title bit 1), positions 0–4,999 in v2 hash
  order. Nothing of a test article was ever used for training or development.
* **NQ-Test12:** NQ-open ``train`` positions 34,490–38,099 in SHAKE-256 order (earlier rounds:
  0–34,489).
"""

from __future__ import annotations

import json

from experiments.chat_eval import load_squad
from experiments.chat_v2_data import CACHE, h64, load_nq

SPLIT = "test12"
N_SQ = 5000
N_NQ = 3610
NQ_FROM = 34490


def pool_v3() -> list[dict]:
    """Every SQuAD question whose paragraph is part of the v12 reading (``squad_read.json``)."""
    from experiments.chat_squad_read import paragraphs
    sel = json.loads((CACHE / "squad_read.json").read_text())
    paras = paragraphs()
    read = {paras[i][1] for i in sel["read_index"]}
    return [q for q in load_squad() if q["context"] in read]


def dev_titles() -> set[str]:
    """The 42 articles of SQuAD-Dev2 (fixed since PREREG_CHAT_V2)."""
    from engramm.chat.corpus import Corpus
    from experiments.chat_v2_common import MODEL_DIR, squad_v2_splits
    dev2, _ = squad_v2_splits(Corpus.load(MODEL_DIR, index_name="chat3"))
    return {q["title"] for q in dev2}


def squad_v12_dev() -> list[dict]:
    titles = dev_titles()
    return sorted((q for q in pool_v3() if q["title"] in titles), key=lambda q: (h64(q["id"]), q["id"]))


def squad_v12_test() -> list[dict]:
    test = [q for q in pool_v3() if h64("article", q["title"]) & 1 == 1]
    return sorted(test, key=lambda q: (h64(q["id"]), q["id"]))[:N_SQ]


def nq_v12_test() -> list[dict]:
    train = load_nq("train")
    return sorted(train, key=lambda q: (h64("nq", q["question"]), q["id"]))[NQ_FROM:NQ_FROM + N_NQ]
