"""Distance, similarity, and evaluation metrics.

Hypervectors are stored bit-packed: a ``D``-dimensional binary vector
occupies ``D // 8`` bytes of ``uint8``, so ``D`` must be a multiple of 8.
Distances are computed directly on the packed form via XOR and population
count, which is the reason the packed representation is used at all.
"""

from __future__ import annotations

import numpy as np


def popcount_rows(packed: np.ndarray) -> np.ndarray:
    """Count set bits along the last axis of a packed array.

    Parameters
    ----------
    packed:
        ``uint8`` array of any shape; the last axis holds the packed bytes.

    Returns
    -------
    numpy.ndarray
        ``int64`` array with the last axis reduced. Accumulating in
        ``int64`` matters: ``np.bitwise_count`` returns the input dtype, and
        summing 1250 ``uint8`` counts would overflow.
    """
    return np.bitwise_count(packed).sum(axis=-1, dtype=np.int64)


def hamming(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Hamming distance between packed hypervectors, with broadcasting.

    ``a`` and ``b`` are broadcast against each other over all but the last
    axis, so ``(M, 1, B)`` against ``(1, K, B)`` yields the full ``(M, K)``
    distance matrix without an explicit loop.
    """
    return popcount_rows(np.bitwise_xor(a, b))


def sim_from_dh(dh: np.ndarray | int, dimension: int) -> np.ndarray:
    """Map Hamming distance to similarity in ``[-1, 1]``.

    ``sim = 1 - 2 * dh / D``: identical vectors give ``+1``, complementary
    vectors ``-1``, and two independent random vectors give ``0`` in
    expectation (their expected distance is ``D / 2``). This is the binary
    equivalent of a cosine similarity on ``±1`` vectors.

    Deviation from the recovered code, recorded per the project's rule on
    documenting divergences: the legacy signature was ``sim_from_dh(dh)``
    with the dimension held in module state. It is an explicit parameter
    here so that the dimension stays configurable.
    """
    return 1.0 - 2.0 * np.asarray(dh, dtype=np.float64) / dimension


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Fraction of exactly matching predictions."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: {y_true.shape} vs {y_pred.shape}")
    if y_true.size == 0:
        raise ValueError("accuracy is undefined for an empty set")
    return float(np.count_nonzero(y_true == y_pred) / y_true.size)


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> float:
    """Unweighted mean of the per-class F1 scores.

    Every class contributes equally regardless of its support, which is why
    this is reported alongside accuracy: on an imbalanced test set the two
    can diverge sharply, and accuracy alone would hide a classifier that
    ignores small classes.

    A class with neither true instances nor predictions contributes ``0.0``
    (the convention used by scikit-learn's ``zero_division=0``). Classes are
    identified by integer index, so a class absent from both arrays is still
    counted — that is the point of a macro average.
    """
    y_true = np.asarray(y_true, dtype=np.int64)
    y_pred = np.asarray(y_pred, dtype=np.int64)
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: {y_true.shape} vs {y_pred.shape}")
    if n_classes <= 0:
        raise ValueError("n_classes must be positive")
    if y_true.size and (y_true.max() >= n_classes or y_pred.max() >= n_classes):
        raise ValueError("class index out of range for n_classes")

    true_positive = np.bincount(y_true[y_true == y_pred], minlength=n_classes)
    predicted = np.bincount(y_pred, minlength=n_classes)
    actual = np.bincount(y_true, minlength=n_classes)

    # 2*TP + FP + FN == predicted + actual, since predicted = TP + FP and
    # actual = TP + FN. Avoids materialising a confusion matrix.
    denominator = predicted + actual
    per_class = np.where(denominator == 0, 0.0,
                         2.0 * true_positive / np.maximum(denominator, 1))
    return float(per_class.mean())
