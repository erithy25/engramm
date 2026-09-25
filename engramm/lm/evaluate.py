"""Bits per byte with document-level bootstrap (docs/PREREG_LM.md §6)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from engramm.lm.stream import TokenSplit

BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 42


def doc_index(split: TokenSplit, positions: np.ndarray) -> np.ndarray:
    """Which document each predicted position belongs to (its terminating EOS included)."""
    return np.searchsorted(split.doc_starts, positions, side="right") - 1


def per_doc_bits(split: TokenSplit, probs: np.ndarray, positions: np.ndarray | None = None) -> np.ndarray:
    """Σ −log2 p per document. ``probs`` belongs to ``positions`` (default: 1..len−1)."""
    if positions is None:
        positions = np.arange(1, len(split.tokens), dtype=np.int64)
    if len(probs) != len(positions):
        raise ValueError("one probability per position required")
    if not np.all(probs > 0):
        raise ValueError("a probability is zero or negative — the model is not smoothed")
    docs = doc_index(split, positions)
    return np.bincount(docs, weights=-np.log2(probs), minlength=split.n_docs)


def doc_bytes(split: TokenSplit) -> np.ndarray:
    """UTF-8 bytes of each document plus one for its end."""
    return split.doc_bytes.astype(np.float64) + 1.0


@dataclass
class BPB:
    value: float
    ci_low: float
    ci_high: float
    n_docs: int
    n_bytes: int

    def as_dict(self) -> dict:
        return {"bpb": self.value, "ci95": [self.ci_low, self.ci_high], "docs": self.n_docs,
                "bytes": self.n_bytes}


def _replicates(n_docs: int, reps: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, n_docs, size=(reps, n_docs))


def bpb(bits: np.ndarray, nbytes: np.ndarray, mask: np.ndarray | None = None,
        reps: int = BOOTSTRAP_REPLICATES, seed: int = BOOTSTRAP_SEED) -> BPB:
    if mask is not None:
        bits, nbytes = bits[mask], nbytes[mask]
    value = float(bits.sum() / nbytes.sum())
    idx = _replicates(len(bits), reps, seed)
    boot = bits[idx].sum(axis=1) / nbytes[idx].sum(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return BPB(value, float(lo), float(hi), int(len(bits)), int(nbytes.sum()))


def bpb_ratio(bits_a: np.ndarray, bits_b: np.ndarray, mask: np.ndarray | None = None,
              reps: int = BOOTSTRAP_REPLICATES, seed: int = BOOTSTRAP_SEED) -> dict:
    """BPB(a)/BPB(b) on the same documents (bytes cancel), paired bootstrap."""
    if mask is not None:
        bits_a, bits_b = bits_a[mask], bits_b[mask]
    ratio = float(bits_a.sum() / bits_b.sum())
    idx = _replicates(len(bits_a), reps, seed)
    boot = bits_a[idx].sum(axis=1) / bits_b[idx].sum(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"ratio": ratio, "ci95": [float(lo), float(hi)]}
