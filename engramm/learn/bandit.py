"""Which way of answering lands with this user: Thompson sampling over Beta counts, deterministic per learning state.

An arm is a move choice inside a situation kind, e.g. ``INJURY:ask`` (react, then ask one question) against
``INJURY:advise`` (react, then advice straight away). Rewards come from the next message (thanks, carrying on → 1;
"huh?", "that's not what I meant", asking for advice right after a question → 0). Until an arm pair has
MIN_SIGNALS rewards the default behaviour stays — a handful of signals never changes how ENGRAMM talks.
"""
from __future__ import annotations

import random
import zlib

MIN_SIGNALS = 4
PRIOR = {"ask": (2.0, 1.0), "advise": (1.0, 1.0)}      # the default (ask first) starts a little ahead


def choose(bandit: dict[str, list[float]], kind: str, seed: str) -> str | None:
    """'ask' or 'advise' for this kind, or None while there are too few signals (keep the default)."""
    arms = {a: bandit.get(f"{kind}:{a}", [0.0, 0.0]) for a in PRIOR}
    if sum(w + l for w, l in arms.values()) < MIN_SIGNALS:
        return None
    rnd = random.Random(zlib.crc32(seed.encode("utf-8")))
    draw = {a: rnd.betavariate(PRIOR[a][0] + w, PRIOR[a][1] + l) for a, (w, l) in sorted(arms.items())}
    return max(sorted(draw), key=lambda a: draw[a])
