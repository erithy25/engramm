"""VSA algebra, item memory, and the prototype classifier.

Scope note: this is the reduced core defined for the rebuild — no HNSW
index, no episodic memory, no consolidation phases. Those return once the
core is implemented and measured (see the README roadmap).

Representation
--------------
A hypervector is ``D`` binary components stored bit-packed in ``D // 8``
bytes of ``uint8``, so ``D`` must be a multiple of 8. Two views are used:

* **packed** — the storage and distance form. XOR and population count
  operate on it directly, which is why binding and similarity are cheap.
* **signed** — the arithmetic form, ``±1`` per component as ``int8``.
  Bundling and prototype accumulation need addition, which bit-packing
  cannot express.

Conversions between the two are explicit (:func:`to_signed`,
:func:`from_signed`) rather than implicit, so it is always visible which
form a given operation works in.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from engramm.metrics import hamming, sim_from_dh
from engramm.repro import stable_label_order

DEFAULT_DIMENSION = 10_000

#: Accumulator entries are halved once any of them exceeds this magnitude.
#: The accumulator is ``int16`` (range ±32767); halving at 2^14 keeps the
#: subsequent additions clear of overflow while preserving the sign
#: structure, which is all the binarised prototype depends on. The bound is
#: taken from the project's recovered specification.
HALVE_THRESHOLD = 2 ** 14


# ---------------------------------------------------------------------------
# Representation conversions
# ---------------------------------------------------------------------------

def _check_dimension(dimension: int) -> None:
    if dimension <= 0 or dimension % 8:
        raise ValueError(f"dimension must be a positive multiple of 8, got {dimension}")


def unpack_bits(packed: np.ndarray, dimension: int) -> np.ndarray:
    """Expand packed bytes to one ``uint8`` per component (values 0 or 1)."""
    _check_dimension(dimension)
    return np.unpackbits(packed, axis=-1, count=dimension)


def pack_bits(bits: np.ndarray) -> np.ndarray:
    """Pack one-byte-per-component bits back into bytes."""
    return np.packbits(bits.astype(np.uint8), axis=-1)


def to_signed(packed: np.ndarray, dimension: int) -> np.ndarray:
    """Convert packed bits to the ``±1`` arithmetic form as ``int8``."""
    bits = unpack_bits(packed, dimension)
    return (bits.astype(np.int8) * 2) - 1


def from_signed(signed: np.ndarray) -> np.ndarray:
    """Convert a ``±1`` (or any nonzero-signed) array back to packed bits.

    Positive components become 1, negative become 0. Zero components are
    rejected: a zero has no sign, and silently mapping it to either value
    would hide exactly the ambiguity that :func:`resolve_tie` exists to
    settle.
    """
    if np.any(signed == 0):
        raise ValueError(
            "signed array contains zeros, which have no bit value; resolve "
            "ties before converting (see resolve_tie)"
        )
    return pack_bits(signed > 0)


# ---------------------------------------------------------------------------
# Tie resolution — deliberately open
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TieContext:
    """Information available to a tie-resolution rule.

    Carries everything a rule could draw on. Which of these fields an
    actual rule uses depends on the rule, and that decision has not been
    made yet.

    Attributes
    ----------
    dimension:
        Hypervector dimension.
    n_terms:
        How many vectors were combined, when known.
    class_index:
        The prototype being binarised, when the tie arises there rather
        than in a standalone bundling operation.
    seed:
        The run's seed, when one is in scope.
    """

    dimension: int
    n_terms: int | None = None
    class_index: int | None = None
    seed: int | None = None


def resolve_tie(
    totals: np.ndarray,
    tie_mask: np.ndarray,
    context: TieContext,
) -> np.ndarray:
    """Assign bit values to components where the majority vote is exactly tied.

    **Contract.** Called with the signed component sums (``totals``) and a
    boolean mask marking the components where that sum is exactly zero.
    Must return a ``uint8`` array of 0/1 values, one per tied component, in
    the order the mask selects them. Must be deterministic: the same inputs
    and the same context must always give the same answer, or the project's
    determinism tests fail.

    **Not implemented — open by design.** How a tie should be resolved is an
    unsettled question in this project, and the answer follows from the
    mathematics of majority bundling rather than from convenience. It stays
    open until that mathematics has been worked through in
    ``docs/UNDERSTANDING.md``, section B2.2. Implementing a rule here before
    then would settle the question by accident.

    Until it is implemented, bundling and prototype binarisation work
    whenever no exact tie occurs, and raise here when one does.
    """
    raise NotImplementedError(
        "Tie-resolution rule is an open design decision — see "
        "docs/UNDERSTANDING.md B2.2. Until it is settled, bundling and "
        "rebinarisation require inputs that produce no exact ties "
        f"(got {int(np.count_nonzero(tie_mask))} tied of {context.dimension} "
        "components)."
    )


# ---------------------------------------------------------------------------
# VSA algebra
# ---------------------------------------------------------------------------

def bind(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Bind two packed hypervectors by elementwise XOR.

    XOR is its own inverse, so :func:`unbind` is the same operation. Binding
    is applied directly to the packed form; no unpacking is needed.
    """
    return np.bitwise_xor(a, b)


#: Unbinding is binding — XOR is an involution.
unbind = bind


def permute(packed: np.ndarray, shift: int, dimension: int) -> np.ndarray:
    """Cyclically rotate a packed hypervector by ``shift`` components.

    Used to mark position in a sequence. The rotation is over components,
    not over bytes, so the packed form is expanded, rolled, and repacked.
    Broadcasting over leading axes is preserved, so a stack of vectors can
    be rotated in one call.
    """
    _check_dimension(dimension)
    bits = unpack_bits(packed, dimension)
    return pack_bits(np.roll(bits, shift, axis=-1))


def bundle(
    packed_stack: np.ndarray,
    dimension: int,
    context: TieContext | None = None,
) -> np.ndarray:
    """Combine several packed hypervectors by componentwise majority vote.

    ``packed_stack`` has shape ``(N, D // 8)``; the result is a single
    packed hypervector that is similar to each of the ``N`` inputs and
    dissimilar to vectors that were not among them.

    With an odd ``N`` every component has a strict majority. With an even
    ``N`` a component can be exactly balanced, and :func:`resolve_tie`
    decides it — which is currently unimplemented, so such inputs raise.
    """
    _check_dimension(dimension)
    if packed_stack.ndim != 2:
        raise ValueError(f"expected a 2-D stack (N, D//8), got shape {packed_stack.shape}")
    if packed_stack.shape[0] == 0:
        raise ValueError("cannot bundle an empty stack")

    signed = to_signed(packed_stack, dimension).astype(np.int32)
    totals = signed.sum(axis=0)
    return _binarise(totals, context or TieContext(dimension=dimension,
                                                   n_terms=int(packed_stack.shape[0])))


def _halve_signed(values: np.ndarray) -> np.ndarray:
    """Halve magnitudes without ever changing or losing a sign.

    Components of magnitude 1 are left alone; zeros stay zero. See
    :meth:`PrototypeClassifier._halved_if_needed` for why plain integer
    division is unsafe here.
    """
    magnitude = np.maximum(np.abs(values.astype(np.int32)) // 2, 1)
    halved = np.where(values == 0, 0, np.sign(values.astype(np.int32)) * magnitude)
    return halved.astype(values.dtype)


def _binarise(totals: np.ndarray, context: TieContext) -> np.ndarray:
    """Threshold signed sums into packed bits, delegating exact ties."""
    bits = (totals > 0).astype(np.uint8)
    tie_mask = totals == 0
    if tie_mask.any():
        bits[tie_mask] = resolve_tie(totals, tie_mask, context)
    return pack_bits(bits)


# ---------------------------------------------------------------------------
# Item memory
# ---------------------------------------------------------------------------

class ItemMemory:
    """Deterministic map from symbols to random hypervectors.

    A symbol's vector is derived from ``(seed, symbol)`` by a keyed
    extendable-output hash, not by drawing from a random stream. That
    choice matters for two reasons:

    * **Order independence.** A stream-based item memory would give a symbol
      a different vector depending on when it was first seen, so the learned
      state would depend on presentation order. Deriving each vector from
      the symbol itself removes that dependency entirely, which the
      project's order-invariance claims require.
    * **Open vocabulary.** A symbol never seen before still has a
      well-defined vector, so no vocabulary has to be fixed in advance and
      no symbol needs an out-of-vocabulary fallback.

    The derivation is also independent of NumPy's random-stream guarantees
    and of ``PYTHONHASHSEED``: SHAKE-256 output is fixed by the standard, so
    the same symbol yields the same vector on every platform and version.
    """

    def __init__(self, seed: int, dimension: int = DEFAULT_DIMENSION) -> None:
        _check_dimension(dimension)
        if seed < 0:
            raise ValueError("seed must be non-negative")
        self.seed = int(seed)
        self.dimension = int(dimension)
        self._n_bytes = dimension // 8
        self._seed_bytes = self.seed.to_bytes(8, "big")
        self._cache: dict[bytes, np.ndarray] = {}

    def __repr__(self) -> str:
        return (f"ItemMemory(seed={self.seed}, dimension={self.dimension}, "
                f"cached={len(self._cache)})")

    @staticmethod
    def _as_bytes(symbol: bytes | str) -> bytes:
        return symbol.encode("utf-8") if isinstance(symbol, str) else bytes(symbol)

    def vector(self, symbol: bytes | str) -> np.ndarray:
        """Return the packed hypervector for one symbol.

        Results are cached, so repeated lookups cost a dictionary hit. The
        cache is an optimisation only — it never changes what is returned.
        """
        key = self._as_bytes(symbol)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        # Length-prefixing the symbol keeps the seed and the symbol from
        # running together ambiguously: without it, distinct (seed, symbol)
        # pairs could hash the same byte string.
        payload = self._seed_bytes + len(key).to_bytes(8, "big") + key
        raw = hashlib.shake_256(payload).digest(self._n_bytes)
        vector = np.frombuffer(raw, dtype=np.uint8)
        vector.flags.writeable = False
        self._cache[key] = vector
        return vector

    def vectors(self, symbols: Iterable[bytes | str]) -> np.ndarray:
        """Return a ``(N, D // 8)`` stack of packed hypervectors."""
        symbol_list = list(symbols)
        if not symbol_list:
            return np.empty((0, self._n_bytes), dtype=np.uint8)
        return np.stack([self.vector(s) for s in symbol_list])


# ---------------------------------------------------------------------------
# Prototype classifier
# ---------------------------------------------------------------------------

class PrototypeClassifier:
    """Class prototypes as an integer accumulator plus a binarised copy.

    Two representations of the same thing are kept deliberately:

    * ``A`` — an ``int16`` accumulator, shape ``(K, D)``, holding the running
      signed sum of every example bound into each class. Addition is what
      makes learning incremental and order-independent.
    * ``P`` — the packed binarisation of ``A``, shape ``(K, D // 8)``. This
      is what queries are compared against, because comparison on packed
      bits is a XOR and a population count.

    ``P`` is derived from ``A`` and is refreshed whenever ``A`` changes;
    it is never updated independently.
    """

    def __init__(self, dimension: int = DEFAULT_DIMENSION, seed: int | None = None) -> None:
        _check_dimension(dimension)
        self.dimension = int(dimension)
        self.seed = seed
        self.labels: list[str] = []
        self._index: dict[str, int] = {}
        self.A = np.zeros((0, self.dimension), dtype=np.int16)
        self.P = np.zeros((0, self.dimension // 8), dtype=np.uint8)

    def __repr__(self) -> str:
        return (f"PrototypeClassifier(dimension={self.dimension}, "
                f"n_classes={self.n_classes})")

    @property
    def n_classes(self) -> int:
        return len(self.labels)

    def ensure_class(self, label: str) -> int:
        """Return the index of ``label``, allocating a new prototype if needed."""
        existing = self._index.get(label)
        if existing is not None:
            return existing
        index = len(self.labels)
        self.labels.append(label)
        self._index[label] = index
        self.A = np.vstack([self.A, np.zeros((1, self.dimension), dtype=np.int16)])
        self.P = np.vstack([self.P, np.zeros((1, self.dimension // 8), dtype=np.uint8)])
        return index

    def register_classes(self, labels: Iterable[str]) -> None:
        """Allocate prototypes for ``labels`` in a sample-order-independent order.

        Class indices are assigned in sorted label order rather than in
        first-seen order, so a batch fit produces the same layout no matter
        how the samples are shuffled. Without this, two runs on the same
        data in different orders would differ by a permutation of ``A``'s
        rows and could not be compared bit-for-bit.
        """
        for label in stable_label_order(labels):
            self.ensure_class(label)

    def learn(self, signed: np.ndarray, labels: Sequence[str]) -> None:
        """Accumulate a batch of encoded examples into their class prototypes.

        ``signed`` has shape ``(M, D)`` in the ``±1`` form. Accumulation
        iterates over the classes present, not over the samples: each class
        sums its slice in one vectorised reduction.
        """
        if signed.ndim != 2 or signed.shape[1] != self.dimension:
            raise ValueError(
                f"expected signed array of shape (M, {self.dimension}), "
                f"got {signed.shape}"
            )
        if len(labels) != signed.shape[0]:
            raise ValueError(
                f"got {signed.shape[0]} vectors but {len(labels)} labels"
            )
        if signed.shape[0] == 0:
            return

        self.register_classes(labels)
        label_array = np.asarray(labels)
        indices = [self._index[label] for label in stable_label_order(labels)]

        # Compute, binarise, then commit. Binarisation can raise on an
        # unresolved tie, and a half-applied update would leave A and P
        # describing different states.
        updated = {
            index: self.A[index] + signed[label_array == self.labels[index]].sum(
                axis=0, dtype=np.int32).astype(np.int16)
            for index in indices
        }
        updated = self._halved_if_needed(updated)
        packed = {index: self._binarise_row(index, row) for index, row in updated.items()}

        for index, row in updated.items():
            self.A[index] = row
        for index, row in packed.items():
            self.P[index] = row

    def learn_online(self, packed: np.ndarray, signed: np.ndarray, label: str) -> bool:
        """One error-driven refinement step; returns whether it was already correct.

        Classifies the example, and on a miss moves the true class's
        prototype toward it and the predicted class's away, in the
        perceptron style recovered from the original implementation. On a
        hit nothing changes.

        This is the refinement pass: it assumes prototypes already exist
        from :meth:`learn`. Against an untrained prototype every score is
        the same and the step carries no information.
        """
        true_index = self.ensure_class(label)
        if self.n_classes == 0:
            raise RuntimeError("no classes registered")

        predicted_index = int(np.argmax(self.score(packed[None, :])[0]))
        if predicted_index == true_index:
            return True

        # Atomic for the same reason as learn(): binarisation may raise.
        updated = {
            true_index: self.A[true_index] + signed,
            predicted_index: self.A[predicted_index] - signed,
        }
        updated = self._halved_if_needed(updated)
        packed_rows = {index: self._binarise_row(index, row)
                       for index, row in updated.items()}

        for index, row in updated.items():
            self.A[index] = row
        for index, row in packed_rows.items():
            self.P[index] = row
        return False

    def score(self, packed_queries: np.ndarray, chunk_size: int = 512) -> np.ndarray:
        """Similarity of each query to every prototype, shape ``(M, K)``.

        The full distance matrix is computed by broadcasting queries against
        prototypes, in chunks of queries. The chunking bounds peak memory —
        the intermediate XOR array is ``chunk × K × D/8`` bytes, which at
        the full test-set size would otherwise reach many gigabytes. It is a
        loop over chunks, not over samples: each chunk is one vectorised
        operation.
        """
        if packed_queries.ndim != 2:
            raise ValueError(
                f"expected packed queries of shape (M, {self.dimension // 8}), "
                f"got {packed_queries.shape}"
            )
        if self.n_classes == 0:
            raise RuntimeError("cannot score before any class has been learned")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        n_queries = packed_queries.shape[0]
        out = np.empty((n_queries, self.n_classes), dtype=np.float64)
        for start in range(0, n_queries, chunk_size):
            chunk = packed_queries[start:start + chunk_size]
            distances = hamming(chunk[:, None, :], self.P[None, :, :])
            out[start:start + chunk.shape[0]] = sim_from_dh(distances, self.dimension)
        return out

    def predict(self, packed_queries: np.ndarray, chunk_size: int = 512) -> np.ndarray:
        """Index of the most similar prototype for each query."""
        return np.argmax(self.score(packed_queries, chunk_size=chunk_size), axis=1)

    def predict_labels(self, packed_queries: np.ndarray,
                       chunk_size: int = 512) -> list[str]:
        """Label of the most similar prototype for each query."""
        return [self.labels[i] for i in self.predict(packed_queries, chunk_size)]

    def _halved_if_needed(self, updated: dict[int, np.ndarray]) -> dict[int, np.ndarray]:
        """Halve every accumulator row if any entry grew past the threshold.

        Guards the ``int16`` accumulator against overflow on long runs.
        Halving is applied to all classes at once so their relative
        magnitudes stay comparable, and is **sign-preserving**: a component
        of magnitude 1 stays at magnitude 1 rather than being rounded to
        zero. Plain integer division would send ``+1`` to ``0``, which
        destroys that component's sign and manufactures a tie that the data
        never produced. The binarised prototypes are therefore unchanged by
        halving, which is the invariant that makes it safe.
        """
        rows = {**{i: self.A[i] for i in range(self.n_classes)}, **updated}
        peak = max((int(np.abs(row).max()) for row in rows.values() if row.size),
                   default=0)
        if peak <= HALVE_THRESHOLD:
            return updated
        self.A = _halve_signed(self.A)
        return {index: _halve_signed(row) for index, row in updated.items()}

    def _binarise_row(self, index: int, row: np.ndarray) -> np.ndarray:
        """Binarise one accumulator row into its packed prototype."""
        context = TieContext(dimension=self.dimension, class_index=index,
                             seed=self.seed)
        return _binarise(row.astype(np.int32), context)

    def _rebinarise(self, indices: Sequence[int]) -> None:
        """Refresh the packed prototypes for the given class indices."""
        packed = {index: self._binarise_row(index, self.A[index]) for index in indices}
        for index, row in packed.items():
            self.P[index] = row
