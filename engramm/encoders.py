"""Encoders turning raw inputs into hypervectors.

Two encoders, both following the recovered specification; every point where
the specification was silent or ambiguous is recorded in
``docs/DEVIATIONS.md`` rather than decided silently.

* :class:`TrigramEncoder` — byte trigrams bound with rotation by position,
  then majority-bundled (``docs/D2_SPEC.md``).
* :class:`PixelThermometerEncoder` — pixel position bound with an
  order-preserving intensity level, then majority-bundled
  (``docs/D4_PROTOTYP.md``).

Both expose the same two-stage interface, and the split matters:

``accumulate``
    Returns the signed component sums *before* thresholding. Always
    defined, never ambiguous.
``encode``
    Thresholds those sums into a hypervector, resolving any exactly
    balanced component through :func:`engramm.core.resolve_tie`.

Keeping them apart lets ``--dry-run`` in ``experiments/run_benchmark.py``
verify the pipeline without committing to a threshold, and it is where the
tie statistics come from.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from engramm.core import (
    DEFAULT_DIMENSION,
    ItemMemory,
    TieContext,
    _binarise,
    permute,
    unpack_bits,
)

#: Byte value used to separate texts when they are encoded in one pass.
#: Valid UTF-8 uses 0x00 only for U+0000, which does not occur in the
#: corpora; the encoder checks rather than assumes.
_SEPARATOR = 0

#: Level-vector constructions available to :class:`PixelThermometerEncoder`.
#: ``progressive`` is the shipped configuration; the rest exist to test
#: ``docs/DEVIATIONS.md`` GAP-1 and are registered as axis 1 of the E2 sweep.
LEVEL_CONSTRUCTIONS = ("progressive", "linear_thermometer",
                       "random_levels", "single_flip_block")

#: Rough ceiling on the temporary unpacked array inside one chunk, in bytes.
#: Encoding materialises ``rows × D`` bytes at a time; this bounds that.
_CHUNK_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class TieReport:
    """How many components needed tie resolution, and where.

    Produced by :meth:`Encoder.tie_report`. Reported by ``--dry-run`` so the
    tie rate is visible per task rather than inferred.
    """

    n_samples: int
    n_with_ties: int
    total_tied_components: int
    max_tied_in_one_sample: int
    dimension: int

    @property
    def fraction_of_samples(self) -> float:
        return self.n_with_ties / self.n_samples if self.n_samples else 0.0

    @property
    def mean_tied_components(self) -> float:
        return self.total_tied_components / self.n_samples if self.n_samples else 0.0


class Encoder(ABC):
    """Common interface: accumulate signed sums, then optionally threshold."""

    def __init__(self, item_memory: ItemMemory,
                 chunk_bytes: int = _CHUNK_BYTES) -> None:
        self.item_memory = item_memory
        self.dimension = item_memory.dimension
        if chunk_bytes <= 0:
            raise ValueError("chunk_bytes must be positive")
        #: Memory budget for one intermediate array. A knob, not a
        #: hyperparameter: it bounds peak memory and never changes a value,
        #: which is what lets tests shrink it to exercise the split path
        #: cheaply.
        self.chunk_bytes = int(chunk_bytes)

    @abstractmethod
    def accumulate(self, samples: Any) -> np.ndarray:
        """Return the signed component sums, shape ``(N, D)`` as ``int32``."""

    def encode(self, samples: Any) -> np.ndarray:
        """Threshold accumulated sums into packed hypervectors ``(N, D // 8)``."""
        return self.binarise(self.accumulate(samples))

    def binarise(self, totals: np.ndarray) -> np.ndarray:
        """Threshold pre-computed sums, one sample per row.

        Thresholding itself is vectorised over the whole batch; only the
        per-sample tie key is not, because it is keyed on each sample's own
        content by construction (:meth:`TieContext.for_encoding`). Rows
        without a tie skip that step entirely — on MNIST that is a few
        percent of components but every sample, on WiLI about half the
        samples have none at all.
        """
        if totals.ndim != 2:
            raise ValueError(f"expected sums of shape (N, D), got {totals.shape}")
        seed = self.item_memory.seed
        signs = np.packbits(totals > 0, axis=-1)
        ties = np.packbits(totals == 0, axis=-1)

        packed = signs.copy()
        for row in np.flatnonzero(ties.any(axis=1)):
            context = TieContext(
                dimension=self.dimension,
                identity=b"encoding\x00" + signs[row].tobytes() + ties[row].tobytes(),
                seed=seed, origin="encoding",
            )
            packed[row] = _binarise(totals[row], context)
        return packed

    def encode_signed(self, samples: Any) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(packed, signed)`` for the classifier's two inputs.

        Mirrors the recovered ``ItemMemory.encode_signed`` contract: the
        packed form is what queries compare against, the ``±1`` form is what
        prototypes accumulate.
        """
        packed = self.encode(samples)
        signed = (unpack_bits(packed, self.dimension).astype(np.int8) * 2) - 1
        return packed, signed

    def tie_report(self, samples: Any) -> TieReport:
        """Count components that needed tie resolution."""
        totals = self.accumulate(samples)
        tied_per_sample = (totals == 0).sum(axis=1)
        return TieReport(
            n_samples=int(totals.shape[0]),
            n_with_ties=int(np.count_nonzero(tied_per_sample)),
            total_tied_components=int(tied_per_sample.sum()),
            max_tied_in_one_sample=int(tied_per_sample.max()) if totals.size else 0,
            dimension=self.dimension,
        )


# ---------------------------------------------------------------------------
# Text — byte trigrams
# ---------------------------------------------------------------------------

class TrigramEncoder(Encoder):
    """Encode text as a majority bundle of rotation-bound byte trigrams.

    For each position ``i`` the trigram vector is

        ``ρ²(V[b_i]) ⊕ ρ¹(V[b_{i+1}]) ⊕ V[b_{i+2}]``

    where ``V`` maps a byte to its item-memory hypervector and ``ρ`` is
    cyclic rotation. Rotation depth encodes position within the trigram, so
    ``"abc"`` and ``"cba"`` bind to unrelated vectors — bundling alone could
    not tell them apart.

    The alphabet is bytes rather than Unicode codepoints, matching the
    recovered API (``docs/DEVIATIONS.md`` INFERRED-1). The two rotated
    tables are materialised once (INFERRED-3), which is an optimisation with
    no semantic effect.
    """

    def __init__(self, item_memory: ItemMemory,
                 chunk_bytes: int = _CHUNK_BYTES) -> None:
        super().__init__(item_memory, chunk_bytes)
        base = np.stack([item_memory.vector(bytes([b])) for b in range(256)])
        self._tables = (
            permute(base, 2, self.dimension),   # applied to the first byte
            permute(base, 1, self.dimension),   # to the second
            base,                               # to the third
        )

    def __repr__(self) -> str:
        return f"TrigramEncoder(dimension={self.dimension})"

    def accumulate(self, samples: Sequence[str] | Sequence[bytes]) -> np.ndarray:
        texts = list(samples)
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.int32)

        blob, spans = self._to_byte_blob(texts)
        counts = (spans[:, 1] - spans[:, 0]) - 2
        totals = np.zeros((len(texts), self.dimension), dtype=np.int32)

        # Texts are grouped by trigram count before chunking. Summing a
        # chunk means padding it to its longest member, so mixing a
        # 7000-trigram paragraph with 600-trigram ones would waste an order
        # of magnitude in memory on padding. Sorting first keeps the waste
        # near zero. Results are written back to their original rows, so the
        # grouping is invisible to the caller and changes no value.
        order = np.argsort(counts, kind="stable")

        # A text whose trigrams alone exceed the budget cannot share a group
        # with anything, and grouping it by itself would still allocate the
        # whole thing at once — the budget would simply not apply. Those
        # texts are split across their own trigrams instead. Sorting puts
        # them last, so this partition costs nothing.
        oversized = counts[order] * self.dimension > self.chunk_bytes
        for row in order[oversized]:
            self._accumulate_oversized(blob, spans[row], int(counts[row]),
                                       int(row), totals)

        remaining = order[~oversized]
        start = 0
        while start < remaining.size:
            stop = self._group_end(counts, remaining, start)
            self._accumulate_group(blob, spans, counts, remaining[start:stop],
                                   totals)
            start = stop
        return totals

    def _accumulate_oversized(self, blob: np.ndarray, span: np.ndarray,
                              count: int, row: int, totals: np.ndarray) -> None:
        """Accumulate one text by splitting its own trigrams into sub-chunks.

        WiLI-2018 contains a single test paragraph of 579,350 bytes against a
        median of 370. Encoding it in one piece materialises 5.79 GB twice at
        D = 10,000 — which is where the 12.25 GB peak of the first WiLI run
        came from (``docs/DEVIATIONS.md`` KNOWN-1).

        Splitting is exact rather than approximate: the bundle is a sum over
        trigrams, addition is associative, and the ``±1`` conversion is
        applied once at the end to the total count. Partial sums therefore
        combine to the same value the single-pass path produces, which
        ``tests/test_encoders.py`` checks by comparison rather than by
        argument.
        """
        per_chunk = max(1, self.chunk_bytes // self.dimension)
        start = int(span[0])
        bit_sum = np.zeros(self.dimension, dtype=np.int32)
        for offset in range(0, count, per_chunk):
            size = min(per_chunk, count - offset)
            positions = start + offset + np.arange(size, dtype=np.int64)
            bound = (self._tables[0][blob[positions]]
                     ^ self._tables[1][blob[positions + 1]]
                     ^ self._tables[2][blob[positions + 2]])
            bit_sum += np.unpackbits(bound, axis=-1, count=self.dimension).sum(
                axis=0, dtype=np.int32)
        totals[row] = 2 * bit_sum - np.int32(count)

    def _group_end(self, counts: np.ndarray, order: np.ndarray, start: int) -> int:
        """Largest group from ``start`` whose padded array fits the budget.

        Always returns at least one row. That is safe here only because
        oversized texts have been removed beforehand — otherwise this is
        exactly where the budget silently stopped applying.
        """
        stop = start + 1
        while stop < order.size:
            longest = int(counts[order[stop]])
            if (stop - start + 1) * longest * self.dimension > self.chunk_bytes:
                break
            stop += 1
        return stop

    def _accumulate_group(self, blob: np.ndarray, spans: np.ndarray,
                          counts: np.ndarray, rows: np.ndarray,
                          totals: np.ndarray) -> None:
        group_counts = counts[rows]
        longest = int(group_counts.max())

        # Trigram start positions for the whole group, built without a loop
        # over samples: repeat each text's offset, then add a within-text
        # ramp that restarts at every text boundary.
        offsets = np.repeat(spans[rows, 0], group_counts)
        ramp = np.arange(offsets.size, dtype=np.int64)
        ramp -= np.repeat(
            np.concatenate([[0], np.cumsum(group_counts)[:-1]]), group_counts)
        positions = offsets + ramp

        bound = (self._tables[0][blob[positions]]
                 ^ self._tables[1][blob[positions + 1]]
                 ^ self._tables[2][blob[positions + 2]])
        bits = np.unpackbits(bound, axis=-1, count=self.dimension)

        # Sum per text by padding to a rectangle and reducing one axis.
        # Padding entries stay zero and contribute nothing to the bit sum,
        # while the ±1 conversion below uses each text's true count — so the
        # padding cannot bias the result. This is far faster than
        # np.add.reduceat over many segments of a wide array.
        padded = np.zeros((rows.size, longest, self.dimension), dtype=np.uint8)
        occupied = np.arange(longest)[None, :] < group_counts[:, None]
        padded[occupied] = bits
        summed = padded.sum(axis=1, dtype=np.int32)

        # Majority in ±1 terms: sum(2b − 1) = 2·sum(b) − n.
        totals[rows] = 2 * summed - group_counts[:, None].astype(np.int32)

    @staticmethod
    def _to_byte_blob(texts: Sequence[str] | Sequence[bytes]
                      ) -> tuple[np.ndarray, np.ndarray]:
        """Join all texts into one byte array, returning per-text spans.

        Joining lets the whole batch be converted in a single encode call and
        the trigram positions be found with array operations, instead of a
        per-sample loop.
        """
        if texts and isinstance(texts[0], bytes):
            encoded = list(texts)
            joined = bytes([_SEPARATOR]).join(encoded)
        else:
            encoded = [t.encode("utf-8") for t in texts]
            joined = bytes([_SEPARATOR]).join(encoded)

        lengths = np.fromiter((len(e) for e in encoded), dtype=np.int64,
                              count=len(encoded))
        if np.any(lengths < 3):
            bad = int(np.flatnonzero(lengths < 3)[0])
            raise ValueError(
                f"sample {bad} is {int(lengths[bad])} bytes long and has no "
                f"trigrams; its accumulator would be entirely zero, which "
                f"carries no information (docs/DEVIATIONS.md GAP-3)"
            )
        blob = np.frombuffer(joined, dtype=np.uint8)
        if len(texts) > 1 and int(np.count_nonzero(blob == _SEPARATOR)) != len(texts) - 1:
            raise ValueError(
                "a sample contains a NUL byte, which the encoder uses as a "
                "text separator"
            )
        # Span starts: each text begins one byte after the previous separator.
        starts = np.zeros(len(encoded), dtype=np.int64)
        starts[1:] = np.cumsum(lengths[:-1] + 1)
        return blob, np.stack([starts, starts + lengths], axis=1)




# ---------------------------------------------------------------------------
# Images — position bound with intensity level
# ---------------------------------------------------------------------------

class PixelThermometerEncoder(Encoder):
    """Encode an image as a majority bundle of position-bound intensity levels.

    Each pixel contributes ``V[position_j] ⊕ L[level_j]``, and the bundle of
    all pixels is the image's hypervector — the ``PixelLevelMemory``
    construction recorded in ``docs/D4_PROTOTYP.md``.

    The level vectors are order-preserving: level 0 is random and each
    subsequent level flips a further ``D / (2·(Q−1))`` components drawn from
    one fixed permutation, so adjacent intensities encode to similar vectors
    and the extremes are approximately orthogonal. That property is what
    "thermometer" names; independent random levels would make intensity 3
    and 4 as unrelated as 3 and 15. The construction itself was not recorded
    and is documented as a choice in ``docs/DEVIATIONS.md`` GAP-1.

    Intensity maps to level by ``pixel · Q // 256`` — fixed arithmetic, not a
    fitted statistic, so it cannot leak across splits (GAP-2).
    """

    def __init__(self, item_memory: ItemMemory, n_positions: int = 784,
                 n_levels: int = 16, chunk_bytes: int = _CHUNK_BYTES,
                 construction: str = "progressive") -> None:
        super().__init__(item_memory, chunk_bytes)
        if construction not in LEVEL_CONSTRUCTIONS:
            raise ValueError(
                f"unknown thermometer construction {construction!r}; "
                f"expected one of {sorted(LEVEL_CONSTRUCTIONS)}"
            )
        #: Which level construction is in use. The shipped configuration is
        #: ``progressive``; changing it is a registered experiment, not a
        #: tuning knob (``docs/EXPECTATIONS.md`` E2, rule 1).
        self.construction = construction
        if n_levels < 2:
            raise ValueError("n_levels must be at least 2")
        if n_positions < 1:
            raise ValueError("n_positions must be positive")
        self.n_positions = int(n_positions)
        self.n_levels = int(n_levels)

        positions = np.stack([item_memory.vector(f"pixel:{j}".encode())
                              for j in range(self.n_positions)])
        levels = self._build_levels()
        # Pre-bind every (position, level) pair once: encoding is then a
        # gather rather than a bind per pixel per image.
        self._bound = np.bitwise_xor(positions[:, None, :], levels[None, :, :])

    def __repr__(self) -> str:
        return (f"PixelThermometerEncoder(dimension={self.dimension}, "
                f"n_positions={self.n_positions}, n_levels={self.n_levels}, "
                f"construction={self.construction!r})")

    def _permutation(self) -> np.ndarray:
        """One fixed component ordering, derived from the item memory's seed.

        Shared by every construction that needs an ordering, so the variants
        differ only in *how* they use it and not in which components they
        touch — which is what makes the sweep a comparison of constructions
        rather than of orderings.
        """
        digest = hashlib.shake_256(
            self.item_memory.seed.to_bytes(8, "big") + b"thermometer:order"
        ).digest(8)
        return np.random.default_rng(
            int.from_bytes(digest, "big")).permutation(self.dimension)

    def _build_levels(self) -> np.ndarray:
        """Level hypervectors for the configured construction.

        Four variants, registered as axis 1 of the E2 sweep
        (``docs/EXPECTATIONS.md``). Only ``progressive`` is the shipped
        configuration; the others exist so that ``docs/DEVIATIONS.md`` GAP-1
        — the construction was never recorded — can be tested rather than
        argued.
        """
        builder = {
            "progressive": self._levels_progressive,
            "linear_thermometer": self._levels_linear_thermometer,
            "random_levels": self._levels_random,
            "single_flip_block": self._levels_single_flip_block,
        }.get(self.construction)
        if builder is None:
            raise ValueError(
                f"unknown thermometer construction {self.construction!r}; "
                f"expected one of {sorted(LEVEL_CONSTRUCTIONS)}"
            )
        return builder()

    def _flip_progressively(self, per_step: int) -> np.ndarray:
        """Level 0 random, each further level flipping ``per_step`` more bits."""
        bits = unpack_bits(self.item_memory.vector(b"thermometer:base"),
                           self.dimension).copy()
        order = self._permutation()
        levels = np.empty((self.n_levels, self.dimension // 8), dtype=np.uint8)
        levels[0] = np.packbits(bits)
        for level in range(1, self.n_levels):
            flip = order[(level - 1) * per_step:level * per_step]
            bits = bits.copy()
            bits[flip] ^= 1
            levels[level] = np.packbits(bits)
        return levels

    def _levels_progressive(self) -> np.ndarray:
        """The shipped construction: levels 0 and Q−1 approximately orthogonal.

        ``D / (2·(Q−1))`` components flipped per step, so after Q−1 steps
        half the components differ — the maximum useful separation.
        """
        return self._flip_progressively(self.dimension // (2 * (self.n_levels - 1)))

    def _levels_single_flip_block(self) -> np.ndarray:
        """Half the step size: levels 0 and Q−1 differ in ~D/4, not ~D/2.

        Ordering is preserved as in ``progressive``, but the whole range is
        compressed. Separates "order matters" from "how much separation the
        extremes need".
        """
        return self._flip_progressively(self.dimension // (2 * self.n_levels))

    def _levels_linear_thermometer(self) -> np.ndarray:
        """A literal thermometer code: level q sets its first ``q·D/Q`` bits.

        The reading of "thermometer encoding" that takes the name at face
        value. Order-preserving like the others, but the levels are not
        random vectors at all — level 0 is all zeros and level Q−1 is mostly
        ones, so the code carries a magnitude as well as an identity.
        """
        order = self._permutation()
        per_level = self.dimension // self.n_levels
        levels = np.empty((self.n_levels, self.dimension // 8), dtype=np.uint8)
        for level in range(self.n_levels):
            bits = np.zeros(self.dimension, dtype=np.uint8)
            bits[order[:level * per_level]] = 1
            levels[level] = np.packbits(bits)
        return levels

    def _levels_random(self) -> np.ndarray:
        """Independent random vectors — the negative control.

        Discards ordering entirely: level 3 is as unrelated to level 4 as to
        level 15. Registered in ``docs/EXPECTATIONS.md`` as the check that
        the sweep measures what it claims — if this is *not* worse than
        ``progressive``, then ordering does not matter for MNIST and the
        whole axis is uninformative.
        """
        levels = np.empty((self.n_levels, self.dimension // 8), dtype=np.uint8)
        for level in range(self.n_levels):
            levels[level] = self.item_memory.vector(f"thermometer:random:{level}".encode())
        return levels

    def quantise(self, images: np.ndarray) -> np.ndarray:
        """Map ``uint8`` intensities to level indices (GAP-2)."""
        return (np.asarray(images, dtype=np.int64) * self.n_levels) // 256

    def accumulate(self, samples: np.ndarray) -> np.ndarray:
        images = np.asarray(samples)
        if images.ndim != 2 or images.shape[1] != self.n_positions:
            raise ValueError(
                f"expected images of shape (N, {self.n_positions}), "
                f"got {images.shape}"
            )
        if images.shape[0] == 0:
            return np.zeros((0, self.dimension), dtype=np.int32)

        levels = self.quantise(images)
        totals = np.empty((images.shape[0], self.dimension), dtype=np.int32)
        column = np.arange(self.n_positions)

        # Chunked over images for the same reason as the text encoder: the
        # unpacked intermediate is rows × positions × D bytes.
        per_chunk = max(1, self.chunk_bytes // (self.n_positions * self.dimension))
        for start in range(0, images.shape[0], per_chunk):
            chunk = levels[start:start + per_chunk]
            bound = self._bound[column[None, :], chunk]
            bits = np.unpackbits(bound, axis=-1, count=self.dimension)
            summed = bits.sum(axis=1, dtype=np.int32)
            totals[start:start + chunk.shape[0]] = 2 * summed - self.n_positions
        return totals


def build_encoder(task: str, item_memory: ItemMemory, **kwargs: Any) -> Encoder:
    """Return the encoder registered for a task name."""
    if task == "wili":
        return TrigramEncoder(item_memory)
    if task == "mnist":
        return PixelThermometerEncoder(item_memory, **kwargs)
    raise ValueError(f"no encoder registered for task {task!r}")


DEFAULT_ENCODER_DIMENSION = DEFAULT_DIMENSION
