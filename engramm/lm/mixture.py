"""Bucketed linear mixture of the components, weights by EM (docs/PREREG_LM.md §5).

p(w | h) = Σ_c λ_c(b(h)) · p_c(w | h), with the bucket b(h) built from

* the KN context class: longest context with a nonzero count (order ≤ 2, 3, 4, 5),
* the ∞-gram match length (≤ 4, 5–7, 8–15, ≥ 16 tokens),
* for systems with KNN: the smallest KNN distance (three thresholds fixed from
  val-A quartiles; no candidates = the farthest class).

A component without a signal reports p_KN instead (so it can never hurt by
being absent). EM: fixed number of iterations from uniform weights. The weights
are then fixed-point quantised (2^-24 grid, every weight ≥ 2^-24, rows summing to
exactly 1): EM's
float sums can differ in the last bit between platforms (measured: container
vs. M4 differed only there), the quantised weights do not.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

EM_ITERS = 100
#: Fitted weights are stored as integers over 2^24 (fixed point), so a model is
#: bit-identical across platforms even when EM's float sums differ in the last bits.
WEIGHT_BITS = 24
INF_EDGES = (5, 8, 16)


def kn_bin(found: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(found, dtype=np.int64) - 2, 0, 3)


def inf_bin(k: np.ndarray) -> np.ndarray:
    return np.searchsorted(np.array(INF_EDGES), np.asarray(k), side="right").astype(np.int64)


def knn_bin(dmin: np.ndarray, edges: np.ndarray) -> np.ndarray:
    d = np.asarray(dmin)
    b = np.searchsorted(np.asarray(edges), d, side="right").astype(np.int64)
    b[d < 0] = 3
    return b


def knn_edges(dmin: np.ndarray) -> np.ndarray:
    active = np.asarray(dmin)[np.asarray(dmin) >= 0]
    return np.percentile(active, [25, 50, 75], method="lower").astype(np.int64)


@dataclass
class Mixture:
    components: tuple[str, ...]
    n_buckets: int
    weights: np.ndarray            # (n_buckets, C)

    def apply(self, P: np.ndarray, buckets: np.ndarray) -> np.ndarray:
        return np.einsum("ij,ij->i", P, self.weights[buckets])

    def as_dict(self) -> dict:
        return {"components": list(self.components), "n_buckets": self.n_buckets,
                "weights": self.weights.round(6).tolist()}


def fit_em(P: np.ndarray, buckets: np.ndarray, n_buckets: int, components: tuple[str, ...],
           iters: int = EM_ITERS) -> Mixture:
    """Maximum-likelihood mixture weights per bucket."""
    m, C = P.shape
    lam = np.full((n_buckets, C), 1.0 / C)
    counts = np.bincount(buckets, minlength=n_buckets).astype(np.float64)
    for _ in range(iters):
        joint = P * lam[buckets]
        resp = joint / joint.sum(axis=1, keepdims=True)
        new = np.zeros_like(lam)
        for c in range(C):
            new[:, c] = np.bincount(buckets, weights=resp[:, c], minlength=n_buckets)
        nz = counts > 0
        new[nz] /= counts[nz, None]
        new[~nz] = 1.0 / C
        lam = new
    return Mixture(components, n_buckets, quantize_weights(lam))


def quantize_weights(lam: np.ndarray, bits: int = WEIGHT_BITS) -> np.ndarray:
    """Round each row to multiples of 2^-bits that sum to exactly 1.

    Every weight keeps at least one unit (2^-bits), so a component EM drove to
    almost zero — above all KN5, which smooths every other component's zeros —
    never becomes exactly zero. The rounding remainder goes to the row's largest
    weight (ties: the first)."""
    scale = 1 << bits
    q = np.maximum(np.rint(lam * scale).astype(np.int64), 1)
    rows = np.arange(len(q))
    big = np.argmax(q, axis=1)
    q[rows, big] += scale - q.sum(axis=1)
    if (q < 1).any():
        raise ValueError("weight quantisation produced a non-positive weight")
    return q.astype(np.float64) / scale
