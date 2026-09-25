"""Shared helpers for the ENGRAMM-LM experiments (docs/PREREG_LM.md)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from data.lm_corpus import split_half
from engramm.lm.stream import TokenSplit
from engramm.repro import collect_environment, git_revision, peak_rss_mb

REPO = Path(__file__).resolve().parents[1]
TOKENS_DIR = REPO / "data" / "cache" / "lm" / "tokens"
MODELS_DIR = REPO / "models" / "lm"
RESULTS_DIR = REPO / "results" / "lm"
PILOT_TOKENS = 30_000_000
SEEDS = (42, 7, 1337)


def load_split(name: str, mmap: bool = True) -> TokenSplit:
    return TokenSplit.load(TOKENS_DIR, name, mmap=mmap)


def load_train(scale: str) -> TokenSplit:
    """``pilot`` = the first 30 M tokens of the train stream; ``main`` = all of it."""
    full = load_split("train", mmap=False)
    if scale == "pilot":
        return full.prefix(PILOT_TOKENS)
    if scale == "main":
        return full
    if scale.startswith("tiny"):                      # tests / smoke runs, e.g. tiny2000000
        return full.prefix(int(scale[4:]))
    raise ValueError(f"unknown scale {scale!r}")


def half_mask(split: TokenSplit, half: int) -> np.ndarray:
    """Documents of ``split`` in the given half (val-B: 0 = selection, 1 = gates)."""
    return np.array([split_half(s, k) == half for s, k in split.doc_keys], dtype=bool)


def write_record(name: str, payload: dict, started: float, git_state: dict,
                 directory: Path = RESULTS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now = git_revision()
    record = {
        "schema": "engramm-lm/1",
        "name": name,
        "study": "docs/PREREG_LM.md v1.0",
        "timestamp_utc": ts,
        "git": {**git_state, "changed_during_run": now.get("commit") != git_state.get("commit")},
        "environment": collect_environment(),
        "runtime": {"wall_seconds": time.time() - started, "peak_rss_mb": peak_rss_mb()},
        **payload,
    }
    path = directory / f"{name}_{ts}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return path
