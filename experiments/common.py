"""Helpers shared by the experiment harnesses.

Only plumbing lives here — caching, splitting, scoring — never a modelling
choice. Anything that influences a result is a parameter of the harness that
uses it and is written into that harness's record.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from engramm.encoders import Encoder
from engramm.metrics import accuracy, macro_f1

ENCODING_CACHE = Path(__file__).resolve().parent.parent / "data" / "cache" / "encodings"


def content_digest(samples: Any) -> str:
    """SHA-256 over the exact inputs, so a cache entry can never be reused
    for different data that merely has the same size."""
    hasher = hashlib.sha256()
    if isinstance(samples, np.ndarray):
        hasher.update(str(samples.dtype).encode() + str(samples.shape).encode())
        hasher.update(np.ascontiguousarray(samples).tobytes())
    else:
        for text in samples:
            raw = text.encode("utf-8") if isinstance(text, str) else bytes(text)
            hasher.update(len(raw).to_bytes(8, "big") + raw)
    return hasher.hexdigest()


def encode_cached(encoder: Encoder, samples: Any, batch: int = 5_000,
                  cache_dir: Path | None = ENCODING_CACHE,
                  verbose: bool = True) -> np.ndarray:
    """Packed encodings of ``samples``, computed once and cached on disk.

    The key covers the encoder (its repr names class, dimension and
    construction), the item-memory seed, and a digest of the inputs. The
    cache is an optimisation only: :func:`tests.test_harness` checks that a
    cached result equals a fresh encoding.
    """
    key = hashlib.sha256(
        f"{encoder!r}|seed={encoder.item_memory.seed}|{content_digest(samples)}".encode()
    ).hexdigest()[:32]
    path = cache_dir / f"{key}.npy" if cache_dir is not None else None
    if path is not None and path.exists():
        return np.load(path)

    started = time.perf_counter()
    total = len(samples)
    parts = []
    for start in range(0, total, batch):
        chunk = (samples[start:start + batch] if isinstance(samples, np.ndarray)
                 else list(samples[start:start + batch]))
        parts.append(encoder.encode(chunk))
        if verbose and total > batch:
            print(f"    encoded {min(start + batch, total)}/{total} "
                  f"({time.perf_counter() - started:.0f}s)", flush=True)
    packed = (np.concatenate(parts) if parts
              else np.zeros((0, encoder.dimension // 8), dtype=np.uint8))
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp.npy")
        np.save(tmp, packed)
        tmp.replace(path)
    return packed


def holdout_tail(n: int, size: int) -> tuple[np.ndarray, np.ndarray]:
    """Indices ``(fit, validation)``: the last ``size`` of ``n`` examples held out.

    Seed-independent and order-preserving — the conventional MNIST
    validation carve (last 10,000 of the official training split).
    """
    if not 0 < size < n:
        raise ValueError(f"validation size {size} must lie in (0, {n})")
    return np.arange(n - size), np.arange(n - size, n)


def holdout_per_class(y: np.ndarray, exclude: np.ndarray, per_class: int,
                      rng: np.random.Generator) -> np.ndarray:
    """Up to ``per_class`` validation indices per class, drawn from training
    examples *not* in ``exclude`` (the shots actually learned).

    Used for few-shot tasks: the model learns its ``k`` shots, and the
    validation examples come from the rest of the training split, so
    tuning never sees a test item.
    """
    excluded = np.zeros(y.shape[0], dtype=bool)
    excluded[np.asarray(exclude, dtype=np.int64)] = True
    chosen = []
    for c in np.unique(y):
        pool = np.flatnonzero((y == c) & ~excluded)
        if pool.size:
            chosen.append(rng.choice(pool, size=min(per_class, pool.size), replace=False))
    return np.sort(np.concatenate(chosen)) if chosen else np.zeros(0, dtype=np.int64)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> dict[str, float]:
    return {"accuracy": accuracy(y_true, y_pred),
            "macro_f1": macro_f1(y_true, y_pred, n_classes)}


def to_indices(labels: Sequence[str], names: Sequence[str]) -> np.ndarray:
    """Label strings to indices into ``names``."""
    position = {name: i for i, name in enumerate(names)}
    return np.fromiter((position[label] for label in labels), dtype=np.int64,
                       count=len(labels))
