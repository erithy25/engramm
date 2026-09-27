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

WEIGHTS = Weights(cov=5.0, soft=0.0, pcov=1.0, kcov=2.0, type=2.0, wiki=0.25, q=1.0, short=0.5, phr=0.5, dcov=2.0,
                  prox=0.5, dfull=1.0)
EXTRACT = ExtractParams(k=10, tau=0.15, lam=4.0, other_max=4, type_only=True, soft_min=0.0, definition=2.0,
                        head_beta=0.0, copula=1.0, direction=1.0, nb=0.5, nb_prox=2.0, rule_types=("DATE",))
FROZEN = BotConfig(weights=WEIGHTS, extract=EXTRACT, text_k=120, theta=0.0, entity_min=0.60, fact_min=0.30,
                   focus_gate=True)


def cap_ratio(index_dir: Path) -> dict | None:
    """Capitalisation statistics stored next to the v2 index (``capstats.json``)."""
    p = Path(index_dir) / "capstats.json"
    return json.loads(p.read_text()) if p.exists() else None
