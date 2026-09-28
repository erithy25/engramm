"""The frozen ENGRAMM-Chat v2 configuration (docs/PREREG_CHAT_V2.md §2).

Every value here was chosen on the development splits only (``experiments/chat_v2_dev.py``,
EXPECTATIONS E15) and is fixed before the single test run.
"""

from __future__ import annotations

import json
from pathlib import Path

from engramm.chat.bot import BotConfig
from engramm.chat.extract import ExtractParams
from engramm.chat.retrieve import Weights

# v10: the sentence index covers the train stream plus 614,464 Wikipedia leads (``experiments/chat_wiki_build.py``,
# index "chat3"); the weights were tuned again on the dev splits over that index (``ENGRAMM_CHAT_INDEX=chat3``;
# v2–v9 weights: cov 5, pcov 1, kcov 2, type 2, wiki .25, q 1, short .5, phr .5, dcov 2, prox .5, dfull 1).
# v12: plus every SQuAD v1.1 paragraph not read yet (17,555 paragraphs, 2.75 M tokens; ``experiments/
# chat_squad_read.py``), as a segment appended to chat3 when loaded (index "chat4")
INDEX_NAME = "chat4"
WEIGHTS = Weights(cov=5.0, soft=0.0, pcov=2.0, kcov=4.0, type=1.0, wiki=1.0, q=1.0, short=0.5, phr=4.0, dcov=0.0,
                  prox=0.0, dfull=4.0)
# v12: dates through the perceptron too, "X or Y?" choices, span by expected F1 (MBR), and a confidence that
# also counts how many of the best sentences hold the answer (dev12: precision 59.6 % vs 54.0 % at 21 % coverage)
EXTRACT = ExtractParams(k=10, tau=0.15, lam=4.0, other_max=4, type_only=True, soft_min=0.0, definition=2.0,
                        head_beta=0.0, copula=1.0, direction=1.0, nb=0.5, nb_prox=0.0, rule_types=(),
                        sent_beta=1.0, conf_power=4.0, conf_r0=0.5, conf_ns=0.2, choice=True, mbr=1.0, mbr_temp=0.5)
# v8: the span model is the averaged perceptron trained on whole SQuAD paragraphs
# (``python -m experiments.chat_v2_perceptron --paragraph --passes 8 --out spanperc_p2.json``); dev SQuAD
# EM 25.3 / F1 32.1 against 19.8 / 26.2 for the naive-Bayes statistics.
SPAN_MODEL = "spanperc_p2.json"
# v9: search-box queries (lower case, no "?") use a second perceptron trained on the same SQuAD paragraphs plus
# 40,000 retrieved NQ-open train questions (positions 40,000–79,999), weights × 2 (``chat_v2_perceptron_ctx
# train --nq --out spanperc_nqmix.json``); dev NQ EM 3.4 % against 2.5 %.
SPAN_MODEL_NQ = "spanperc_nq.json"
# v10: search-box queries read the 20 best sentences and cut dates with the perceptron too (dev NQ EM 6.0 % vs 5.4 %)
EXTRACT_NQ = ExtractParams(k=20, tau=0.15, lam=4.0, other_max=4, type_only=True, soft_min=0.0, definition=2.0,
                           head_beta=0.0, copula=1.0, direction=1.0, nb=0.5, nb_prox=0.0, rule_types=(),
                           sent_beta=1.0, conf_power=3.0)
# θ: the A2 rule (smallest θ with ≥ 55 % dev precision). v2: SQuAD-dev2 → 7.0293. v3 (PREREG_CHAT_V3): SQuAD-dev2
# plus the spent v2 test, 3,000 questions → 6.9512. v8 (perceptron, share³): 3,000 questions → 6.6824 (coverage
# 22.6 %). v9: all 9,000 spent SQuAD questions (dev2, v2 test, test3–test8) → 6.7847 (coverage 22.2 %). v10 (index
# chat3, new weights): the same 9,000 questions → 9.2123 (coverage 20.9 %). v12 (index chat4, new confidence): Dev12,
# the 3,084 questions of the newly read dev-article paragraphs (the distribution of Test12) → 3.6543 (coverage 23.6 %)
# (rounded down, 4 decimals)
FROZEN = BotConfig(weights=WEIGHTS, extract=EXTRACT, text_k=120, theta=3.6543, entity_min=0.60, fact_min=0.30,
                   only_fact=True,
                   focus_gate=True, span_model=SPAN_MODEL, span_model_nq=SPAN_MODEL_NQ,
                   extract_nq=EXTRACT_NQ)


def cap_ratio(index_dir: Path) -> dict | None:
    """Capitalisation statistics stored next to the v2 index (``capstats.json``)."""
    p = Path(index_dir) / "capstats.json"
    return json.loads(p.read_text()) if p.exists() else None
