"""Bit-level corruption of learned state — ``docs/PREREG_ROBUSTNESS.md`` §4, §3.4.

Everything a corruption experiment needs, and nothing it may not have:

* **The draw.** ``n = percent · N_bits // 100`` positions, uniformly without
  replacement, from ``default_rng([seed, percent])`` — reproducible, and
  independent of which system or in which order anything is evaluated.
* **The flip.** Positions index a flat bit view of the state's bytes; bit
  ``b`` of byte ``i`` is position ``8i + b`` (least significant bit first).
  Every stored bit is corruptible, including sign and exponent bits of
  floats and the sign bit of int8 values — the format is part of what is
  being measured.
* **Formats.** int8 with per-tensor symmetric scaling (the registered
  primary format for the baselines), float32 (secondary), and 1-bit signs
  with one scale per output unit (the v1.3 format-matched control).

The module knows nothing about models. It turns tensors into one flat byte
buffer, flips bits in that buffer, and turns it back into tensors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

#: Corruption levels in percent, as registered in §4.
LEVELS_PERCENT: tuple[int, ...] = (0, 1, 5, 10, 25, 50)


def flip_count(n_bits: int, percent: int) -> int:
    """``⌊percent/100 · n_bits⌋`` in integer arithmetic — no float rounding."""
    if n_bits < 0:
        raise ValueError("n_bits must be non-negative")
    if not 0 <= percent <= 100:
        raise ValueError(f"percent must lie in [0, 100], got {percent}")
    return int(percent) * int(n_bits) // 100


def corruption_positions(n_bits: int, percent: int, seed: int) -> np.ndarray:
    """The bit positions to flip, drawn from ``default_rng([seed, percent])``."""
    count = flip_count(n_bits, percent)
    if count == 0:
        return np.empty(0, dtype=np.int64)
    rng = np.random.default_rng([int(seed), int(percent)])
    return rng.choice(int(n_bits), size=count, replace=False).astype(np.int64)


def flip_bits(buffer: np.ndarray, positions: np.ndarray, n_bits: int | None = None) -> np.ndarray:
    """Return a copy of a ``uint8`` buffer with the given bit positions inverted.

    ``n_bits`` bounds the valid positions when the buffer carries padding
    (packed sign bits whose count is not a multiple of eight); padding bits
    are never touched because no valid position points at them.
    """
    data = np.ascontiguousarray(buffer, dtype=np.uint8).ravel()
    limit = data.size * 8 if n_bits is None else int(n_bits)
    if limit > data.size * 8:
        raise ValueError(f"n_bits={limit} exceeds the buffer's {data.size * 8} bits")
    positions = np.asarray(positions, dtype=np.int64)
    if positions.size == 0:
        return data.copy()
    if positions.min() < 0 or positions.max() >= limit:
        raise ValueError("bit position out of range")
    bits = np.unpackbits(data, bitorder="little")
    bits[positions] ^= 1
    return np.packbits(bits, bitorder="little")


def corrupt(buffer: np.ndarray, percent: int, seed: int,
            n_bits: int | None = None) -> np.ndarray:
    """Draw and apply one registered corruption of ``buffer``."""
    total = np.asarray(buffer).size * 8 if n_bits is None else int(n_bits)
    return flip_bits(buffer, corruption_positions(total, percent, seed), total)


# ---------------------------------------------------------------------------
# Byte layouts: many tensors as one corruptible buffer
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Layout:
    """Where each tensor lives in a concatenated byte buffer."""

    dtypes: tuple[np.dtype, ...]
    shapes: tuple[tuple[int, ...], ...]
    offsets: tuple[int, ...]
    sizes: tuple[int, ...]

    @property
    def n_bytes(self) -> int:
        return self.offsets[-1] + self.sizes[-1] if self.sizes else 0


def to_buffer(tensors: Sequence[np.ndarray]) -> tuple[np.ndarray, Layout]:
    """Concatenate the raw bytes of ``tensors`` (native little-endian)."""
    arrays = [np.ascontiguousarray(t) for t in tensors]
    for a in arrays:
        if a.dtype.byteorder == ">":
            raise ValueError("big-endian tensors are not supported")
    sizes = [a.nbytes for a in arrays]
    offsets = np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(int).tolist() if arrays else []
    buffer = (np.concatenate([a.view(np.uint8).ravel() for a in arrays])
              if arrays else np.empty(0, dtype=np.uint8))
    layout = Layout(tuple(a.dtype for a in arrays), tuple(a.shape for a in arrays),
                    tuple(offsets), tuple(sizes))
    return buffer, layout


def from_buffer(buffer: np.ndarray, layout: Layout) -> list[np.ndarray]:
    """Inverse of :func:`to_buffer`; returns fresh, writeable arrays."""
    data = np.ascontiguousarray(buffer, dtype=np.uint8).ravel()
    if data.size != layout.n_bytes:
        raise ValueError(f"buffer has {data.size} bytes, layout expects {layout.n_bytes}")
    return [data[o:o + n].copy().view(dt).reshape(shape)
            for dt, shape, o, n in zip(layout.dtypes, layout.shapes, layout.offsets,
                                       layout.sizes)]


# ---------------------------------------------------------------------------
# Numeric formats
# ---------------------------------------------------------------------------

def quantize_int8(w: np.ndarray) -> tuple[np.ndarray, float]:
    """Per-tensor symmetric int8: ``s = max|w|/127``, ``q = clip(round(w/s))``.

    Rounding is NumPy's round-half-to-even. An all-zero tensor gets ``s = 1``
    so that dequantisation is defined.
    """
    w = np.asarray(w, dtype=np.float64)
    peak = float(np.max(np.abs(w))) if w.size else 0.0
    scale = peak / 127.0 if peak > 0.0 else 1.0
    q = np.clip(np.rint(w / scale), -127, 127).astype(np.int8)
    return q, scale


def dequantize_int8(q: np.ndarray, scale: float) -> np.ndarray:
    """``q · s`` in float32; a flipped value of −128 dequantises like any other."""
    return (q.astype(np.float32) * np.float32(scale)).astype(np.float32)


@dataclass(frozen=True)
class SignTensor:
    """A weight matrix as sign bits plus one scale per output unit.

    ``w`` has shape ``(inputs, outputs)``; ``alpha[j] = mean |w[:, j]|``.
    Only the sign bits are corruptible (§4.1); scales stay exact.
    """

    signs: np.ndarray          # bool, shape (inputs, outputs); True = positive
    alpha: np.ndarray          # float32, shape (outputs,)

    @classmethod
    def from_weights(cls, w: np.ndarray) -> SignTensor:
        w = np.asarray(w, dtype=np.float64)
        if w.ndim != 2:
            raise ValueError("sign binarisation expects a 2-D (inputs, outputs) matrix")
        return cls(signs=w >= 0.0, alpha=np.abs(w).mean(axis=0).astype(np.float32))

    def weights(self) -> np.ndarray:
        return np.where(self.signs, self.alpha[None, :], -self.alpha[None, :]).astype(np.float32)


def signs_to_buffer(tensors: Sequence[SignTensor]) -> tuple[np.ndarray, int]:
    """Pack the sign bits of several tensors into one buffer; returns (buffer, n_bits)."""
    flat = np.concatenate([t.signs.ravel() for t in tensors]) if tensors else np.empty(0, bool)
    return np.packbits(flat.astype(np.uint8), bitorder="little"), int(flat.size)


def signs_from_buffer(buffer: np.ndarray, n_bits: int,
                      like: Sequence[SignTensor]) -> list[SignTensor]:
    """Inverse of :func:`signs_to_buffer`, keeping each tensor's exact scales."""
    bits = np.unpackbits(np.asarray(buffer, dtype=np.uint8), bitorder="little",
                         count=n_bits).astype(bool)
    out, start = [], 0
    for t in like:
        stop = start + t.signs.size
        out.append(SignTensor(bits[start:stop].reshape(t.signs.shape), t.alpha))
        start = stop
    return out


# ---------------------------------------------------------------------------
# The registered metric
# ---------------------------------------------------------------------------

def retention(acc_p: float, acc_0: float, chance: float) -> float:
    """Chance-corrected retention ``R(p)``, clipped to [0, 1] (§6).

    Undefined when the uncorrupted model is no better than chance; returned
    as NaN so that it cannot be averaged in silently.
    """
    if acc_0 <= chance:
        return float("nan")
    return float(min(1.0, max(0.0, (acc_p - chance) / (acc_0 - chance))))
