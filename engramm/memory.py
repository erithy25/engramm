"""The full ENGRAMM pipeline: prototypes plus episodic memory.

The reduced core (:class:`engramm.core.PrototypeClassifier`) is one half of
the architecture recorded in ``docs/D2_SPEC.md``. This module adds the other
half and the learning phases that connect them:

* **L1 — episodic memory.** Every learned example is kept verbatim as an
  episode ``(key, class, utility)``. A query retrieves its ``k`` nearest
  episodes by Hamming distance.
* **Score fusion.** The answer combines the episode evidence with the
  prototype similarity::

      s[c] = λe · Σ_{e ∈ top-k, val(e) = c} û(util_e) · max(0, sim(q, e) − θ₀)
           + λp · sim(q, P_c)

* **T1 — immediate learning.** Insert the episode and add the example to its
  class accumulator. Pure addition, so the learned *state* does not depend
  on presentation order.
* **T2 — error-driven refinement** (``learn_online`` in the recovered
  code). Classify a training example; reward (+1) or penalise (−1) every
  retrieved episode by whether its class was right; on a miss move the true
  prototype toward the example and — unless ``t2_local`` — the predicted one
  away from it.
* **T3 — consolidation.** Absorption removes episodes that the prototype
  already represents (``sim > θ_merge`` and low utility); eviction removes
  the least useful episodes. Neither touches the accumulators: under T1 the
  episode statistics are already in ``A`` (``docs/D2_SPEC.md`` v1.3, W17).
* **L2 — the event log** (:mod:`engramm.persistence`). Every state change is
  appended as an event, so the state can be rebuilt exactly, including
  after a torn write.

Every choice the recovered specification leaves open is recorded in
``docs/DEVIATIONS.md`` (GAP-5 onwards) instead of being made silently.

Retrieval is exact brute force. Distances are computed as a float32 matrix
product of ``±1`` vectors, ``d_H = (D − q·e) / 2``: every partial sum is an
integer of magnitude at most ``D`` < 2**24, so float32 represents all of
them exactly and the result is bit-identical whatever order the BLAS
library sums in. An approximate index (HNSW) is measured separately in the
M0 audit (``experiments/m0_bench.py``); it is not needed at the sizes the
benchmarks use.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from engramm.core import (
    DEFAULT_DIMENSION,
    PrototypeClassifier,
    _check_dimension,
    unpack_bits,
)
from engramm.metrics import sim_from_dh

#: Episodes whose float32 ``±1`` form fits in this many bytes are kept
#: unpacked between queries. Above it they are unpacked chunk by chunk on
#: every query batch. A memory knob only — it never changes a result.
DEFAULT_CACHE_BYTES = 3 * 1024 ** 3

#: Queries scored per block. Bounds the ``block × N`` distance matrix.
DEFAULT_QUERY_BLOCK = 1_024

#: Episodes per block when the unpacked cache is not used.
DEFAULT_EPISODE_BLOCK = 8_192

#: Sort key for an excluded episode: larger than any real ``(distance, rank)``.
_EXCLUDED_KEY = np.iinfo(np.int64).max


@dataclass(frozen=True)
class FusionConfig:
    """Hyperparameters of retrieval, fusion and refinement.

    ``lambda_e``, ``lambda_p`` and ``theta0`` are chosen per task on a
    validation split carved from the training data — never on the test
    split — and recorded with every result (``docs/D2_SPEC.md`` §3 names
    λe, λp as the task-specific fit parameters). ``k = 32`` is the recovered
    value (``HNSW_search(q, ef=64, k=32)``).
    """

    k: int = 32
    theta0: float = 0.0
    lambda_e: float = 1.0
    lambda_p: float = 1.0
    #: Utility is clipped to ``±util_clip``; ``û(u) = 1 + u / util_clip``
    #: then maps it to ``[0, 2]``: a neutral episode weighs 1, one that has
    #: only ever misled weighs nothing (docs/DEVIATIONS.md GAP-5).
    util_clip: int = 8
    #: D2 §4 fallback: on a miss only the true class moves (no malus for the
    #: predicted class). Registered for M5 by the V2 ratification.
    t2_local: bool = False

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError("k must be positive")
        if self.util_clip <= 0:
            raise ValueError("util_clip must be positive")
        if self.lambda_e < 0 or self.lambda_p < 0:
            raise ValueError("fusion weights must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utility_weight(util: np.ndarray, util_clip: int) -> np.ndarray:
    """``û(u) = 1 + u / util_clip``, in ``[0, 2]`` for clipped utilities."""
    return 1.0 + np.asarray(util, dtype=np.float64) / float(util_clip)


def episode_id(label: str, key: np.ndarray) -> int:
    """Content identity of an episode: 64 bits of SHAKE-256 over label and key.

    Used as the tie-break between equally distant episodes. It depends on
    the episode's content only — not on when it was inserted — so the
    retrieved set, and therefore the answer, is the same whatever order the
    memory was built in. The recovered implementation broke such ties by
    array position through ``argpartition``, which made the output depend on
    insertion order although the state did not (issue W19: 577 vs. 580 hits
    under reordering).
    """
    payload = label.encode("utf-8")
    digest = hashlib.shake_256(len(payload).to_bytes(4, "big") + payload
                               + np.ascontiguousarray(key).tobytes()).digest(8)
    return int.from_bytes(digest, "big")


class EpisodicMemory:
    """L1: packed keys, class indices, utilities, content identities.

    Stored as parallel arrays so retrieval and consolidation are vectorised.
    ``vals`` index into the owning model's label list.
    """

    def __init__(self, dimension: int = DEFAULT_DIMENSION,
                 cache_bytes: int = DEFAULT_CACHE_BYTES) -> None:
        _check_dimension(dimension)
        self.dimension = int(dimension)
        self.cache_bytes = int(cache_bytes)
        self.keys = np.zeros((0, dimension // 8), dtype=np.uint8)
        self.vals = np.zeros(0, dtype=np.int32)
        self.util = np.zeros(0, dtype=np.int16)
        self.ids = np.zeros(0, dtype=np.uint64)
        self._signed: np.ndarray | None = None
        self._rank: np.ndarray | None = None

    def __len__(self) -> int:
        return int(self.vals.shape[0])

    # -- mutation ------------------------------------------------------------

    def add(self, keys: np.ndarray, vals: np.ndarray, ids: np.ndarray) -> np.ndarray:
        """Append episodes; returns their positions."""
        if keys.ndim != 2 or keys.shape[1] != self.dimension // 8:
            raise ValueError(f"expected keys of shape (N, {self.dimension // 8}), "
                             f"got {keys.shape}")
        start = len(self)
        self.keys = np.concatenate([self.keys, keys.astype(np.uint8, copy=False)])
        self.vals = np.concatenate([self.vals, np.asarray(vals, dtype=np.int32)])
        self.util = np.concatenate([self.util, np.zeros(keys.shape[0], dtype=np.int16)])
        self.ids = np.concatenate([self.ids, np.asarray(ids, dtype=np.uint64)])
        self._invalidate()
        return np.arange(start, len(self))

    def remove(self, positions: np.ndarray) -> None:
        """Delete episodes by position; later positions shift down."""
        keep = np.ones(len(self), dtype=bool)
        keep[np.asarray(positions, dtype=np.int64)] = False
        self.keys, self.vals = self.keys[keep], self.vals[keep]
        self.util, self.ids = self.util[keep], self.ids[keep]
        self._invalidate()

    def _invalidate(self) -> None:
        self._signed = None
        self._rank = None

    # -- retrieval -----------------------------------------------------------

    def id_rank(self) -> np.ndarray:
        """Rank of every episode in ``(id, position)`` order — a total order.

        Position only separates exact duplicates (same label, same key),
        which are interchangeable for scoring as long as their utilities
        agree — always true before any refinement.
        """
        if self._rank is None:
            order = np.lexsort((np.arange(len(self)), self.ids))
            rank = np.empty(len(self), dtype=np.int64)
            rank[order] = np.arange(len(self), dtype=np.int64)
            self._rank = rank
        return self._rank

    def _signed_block(self, start: int, stop: int) -> np.ndarray:
        """Episodes ``start:stop`` as float32 ``±1``, from the cache if it fits."""
        n, d = len(self), self.dimension
        if n * d * 4 <= self.cache_bytes:
            if self._signed is None:
                self._signed = _as_signed_f32(self.keys, d)
            return self._signed[start:stop]
        return _as_signed_f32(self.keys[start:stop], d)

    def distances(self, queries: np.ndarray) -> np.ndarray:
        """Exact Hamming distances ``(M, N)`` as ``int64``."""
        n, d = len(self), self.dimension
        out = np.empty((queries.shape[0], n), dtype=np.int64)
        q = _as_signed_f32(queries, d)
        block = n if n * d * 4 <= self.cache_bytes else DEFAULT_EPISODE_BLOCK
        for start in range(0, n, max(block, 1)):
            stop = min(start + block, n)
            dot = q @ self._signed_block(start, stop).T
            # Exact: |dot| <= D < 2**24, so float32 holds every value exactly.
            out[:, start:stop] = (d - dot.astype(np.int64)) // 2
        return out

    def topk(self, queries: np.ndarray, k: int,
             exclude: np.ndarray | None = None,
             query_block: int = DEFAULT_QUERY_BLOCK) -> tuple[np.ndarray, np.ndarray]:
        """The ``k`` nearest episodes per query: ``(positions, distances)``.

        Sorted by ``(distance, content id)``, a strict total order, so the
        selected set is unique — including at the k-th place, where plain
        ``argpartition`` picked among equal distances by array position.

        ``exclude`` gives, per query, one episode position to leave out
        (``-1`` for none): leave-one-out retrieval for refinement, where a
        training example must not find itself.
        """
        m, n = queries.shape[0], len(self)
        if n == 0:
            raise RuntimeError("episodic memory is empty")
        kk = min(k, n - (1 if exclude is not None else 0))
        if kk <= 0:
            raise RuntimeError("not enough episodes for retrieval")
        rank = self.id_rank()
        positions = np.empty((m, kk), dtype=np.int64)
        dists = np.empty((m, kk), dtype=np.int64)
        for start in range(0, m, query_block):
            stop = min(start + query_block, m)
            dist = self.distances(queries[start:stop])
            order_key = (dist << 32) | rank[None, :]
            if exclude is not None:
                rows = np.arange(stop - start)
                excluded = np.asarray(exclude[start:stop], dtype=np.int64)
                valid = excluded >= 0
                order_key[rows[valid], excluded[valid]] = _EXCLUDED_KEY
            if kk < n:
                part = np.argpartition(order_key, kk - 1, axis=1)[:, :kk]
            else:
                part = np.broadcast_to(np.arange(n), (stop - start, n)).copy()
            chosen_keys = np.take_along_axis(order_key, part, axis=1)
            sort = np.argsort(chosen_keys, axis=1, kind="stable")
            positions[start:stop] = np.take_along_axis(part, sort, axis=1)
            dists[start:stop] = np.take_along_axis(dist, positions[start:stop], axis=1)
        return positions, dists


def _as_signed_f32(packed: np.ndarray, dimension: int) -> np.ndarray:
    """Packed bits to float32 ``±1``."""
    bits = unpack_bits(packed, dimension)
    return bits.astype(np.float32) * 2.0 - 1.0


class Engramm:
    """Prototypes (``A``, ``P``) plus episodic memory, with T1/T2/T3.

    ``log`` — an :class:`engramm.persistence.EventLog` — receives every
    state change. Replaying it into a fresh instance reproduces the state
    exactly (:func:`engramm.persistence.replay`).
    """

    def __init__(self, dimension: int = DEFAULT_DIMENSION, seed: int = 0,
                 config: FusionConfig | None = None, log: Any = None,
                 cache_bytes: int = DEFAULT_CACHE_BYTES) -> None:
        self.dimension = int(dimension)
        self.seed = int(seed)
        self.config = config or FusionConfig()
        self.prototypes = PrototypeClassifier(dimension, seed=seed)
        self.episodes = EpisodicMemory(dimension, cache_bytes=cache_bytes)
        self.log = log
        if self.log is not None:
            self.log.write_header(self)

    def __repr__(self) -> str:
        return (f"Engramm(dimension={self.dimension}, classes={self.n_classes}, "
                f"episodes={len(self.episodes)}, config={self.config})")

    @property
    def labels(self) -> list[str]:
        return self.prototypes.labels

    @property
    def n_classes(self) -> int:
        return self.prototypes.n_classes

    # -- T1 ----------------------------------------------------------------

    def learn(self, packed: np.ndarray, labels: Sequence[str]) -> np.ndarray:
        """T1: insert every example as an episode and accumulate it.

        Returns the episode positions assigned, in input order.
        """
        packed = np.asarray(packed, dtype=np.uint8)
        if packed.ndim != 2 or packed.shape[1] != self.dimension // 8:
            raise ValueError(f"expected packed keys (N, {self.dimension // 8}), "
                             f"got {packed.shape}")
        if len(labels) != packed.shape[0]:
            raise ValueError(f"got {packed.shape[0]} keys but {len(labels)} labels")
        if packed.shape[0] == 0:
            return np.zeros(0, dtype=np.int64)
        labels = [str(label) for label in labels]
        if self.log is not None:
            self.log.learn(labels, packed)
        return self._apply_learn(packed, labels)

    def _apply_learn(self, packed: np.ndarray, labels: list[str]) -> np.ndarray:
        signed = (unpack_bits(packed, self.dimension).astype(np.int8) * 2) - 1
        self.prototypes.learn(signed, labels)
        index = {label: i for i, label in enumerate(self.prototypes.labels)}
        vals = np.fromiter((index[label] for label in labels), dtype=np.int32,
                           count=len(labels))
        ids = np.fromiter((episode_id(label, row) for label, row in zip(labels, packed)),
                          dtype=np.uint64, count=len(labels))
        return self.episodes.add(packed, vals, ids)

    # -- query ---------------------------------------------------------------

    def retrieve(self, packed_queries: np.ndarray,
                 exclude: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Top-k episode positions and similarities per query."""
        positions, dists = self.episodes.topk(packed_queries, self.config.k, exclude)
        return positions, sim_from_dh(dists, self.dimension)

    def fuse(self, prototype_scores: np.ndarray, positions: np.ndarray,
             sims: np.ndarray) -> np.ndarray:
        """Combine prototype similarity with the retrieved episode evidence."""
        cfg = self.config
        scores = cfg.lambda_p * np.asarray(prototype_scores, dtype=np.float64)
        if cfg.lambda_e == 0.0 or positions.size == 0:
            return scores
        weight = (utility_weight(self.episodes.util[positions], cfg.util_clip)
                  * np.maximum(0.0, sims - cfg.theta0))
        classes = self.episodes.vals[positions]
        rows = np.repeat(np.arange(positions.shape[0]), positions.shape[1])
        evidence = np.zeros_like(scores)
        np.add.at(evidence, (rows, classes.ravel()), weight.ravel())
        return scores + cfg.lambda_e * evidence

    def scores(self, packed_queries: np.ndarray,
               exclude: np.ndarray | None = None) -> np.ndarray:
        """Fused scores ``(M, K)``."""
        prototype_scores = self.prototypes.score(packed_queries)
        if self.config.lambda_e == 0.0 or len(self.episodes) == 0:
            return self.config.lambda_p * prototype_scores
        positions, sims = self.retrieve(packed_queries, exclude)
        return self.fuse(prototype_scores, positions, sims)

    def argmax(self, scores: np.ndarray) -> np.ndarray:
        """Best class per row; exact ties go to the alphabetically first label.

        By label rather than by class index: indices follow the order in
        which classes arrived, so an index-based tie-break would make the
        answer depend on presentation order even when the state does not.
        """
        if getattr(self, "_label_order_n", -1) != self.n_classes:
            self._label_order = np.array(
                sorted(range(self.n_classes), key=lambda i: self.labels[i]),
                dtype=np.int64)
            self._label_order_n = self.n_classes
        order = self._label_order
        return order[np.argmax(np.asarray(scores)[..., order], axis=-1)]

    def predict(self, packed_queries: np.ndarray, block: int = 2_048) -> np.ndarray:
        """Class index per query (see :meth:`argmax` for ties)."""
        out = np.empty(packed_queries.shape[0], dtype=np.int64)
        for start in range(0, packed_queries.shape[0], block):
            chunk = packed_queries[start:start + block]
            out[start:start + chunk.shape[0]] = self.argmax(self.scores(chunk))
        return out

    def predict_labels(self, packed_queries: np.ndarray) -> list[str]:
        return [self.labels[i] for i in self.predict(packed_queries)]

    # -- T2 ------------------------------------------------------------------

    def refine(self, packed: np.ndarray, labels: Sequence[str], epochs: int,
               rng: np.random.Generator,
               episode_positions: np.ndarray | None = None,
               neighbours: tuple[np.ndarray, np.ndarray] | None = None) -> list[float]:
        """T2: error-driven refinement over a set of training examples.

        Examples are visited in a fresh random order each epoch, drawn from
        ``rng`` (the run's seeded generator). Returns the error rate of each
        epoch — the fraction of examples misclassified *at the moment they
        were visited*, which is what the historical "T2-Fehler" reported.

        ``episode_positions`` names each example's own episode, excluded
        from its retrieval (leave-one-out). Without it an example would
        retrieve itself at distance 0, be classified correctly almost
        always, and refinement would learn next to nothing
        (docs/DEVIATIONS.md GAP-6).

        Episode keys do not change during refinement — only utilities and
        prototypes do — so each example's neighbour list is computed once
        (``neighbours`` may pass it in precomputed) and the epoch loop only
        re-weights it.
        """
        if epochs <= 0:
            return []
        packed = np.asarray(packed, dtype=np.uint8)
        labels = [str(label) for label in labels]
        index = {label: i for i, label in enumerate(self.labels)}
        missing = sorted({label for label in labels if label not in index})
        if missing:
            raise ValueError(f"refine() needs learned classes; unknown: {missing[:5]}")
        true = np.fromiter((index[label] for label in labels), dtype=np.int64,
                           count=len(labels))

        use_episodes = self.config.lambda_e > 0.0 and len(self.episodes) > 0
        if use_episodes and neighbours is None:
            exclude = (np.asarray(episode_positions, dtype=np.int64)
                       if episode_positions is not None else None)
            neighbours = self.retrieve(packed, exclude)

        errors: list[float] = []
        for _ in range(epochs):
            order = rng.permutation(len(labels))
            misses = 0
            for i in order:
                if use_episodes:
                    misses += not self._refine_step(packed[i], int(true[i]),
                                                    neighbours[0][i], neighbours[1][i])
                else:
                    misses += not self._refine_step(packed[i], int(true[i]), None, None)
            errors.append(misses / max(len(labels), 1))
        return errors

    def _refine_step(self, key: np.ndarray, true_class: int,
                     positions: np.ndarray | None, sims: np.ndarray | None) -> bool:
        """One T2 step; returns whether the example was already classified correctly."""
        prototype_scores = self.prototypes.score(key[None, :])
        if positions is not None:
            scores = self.fuse(prototype_scores, positions[None, :], sims[None, :])[0]
        else:
            scores = self.config.lambda_p * prototype_scores[0]
        predicted = int(self.argmax(scores))

        util_delta = None
        if positions is not None:
            util_delta = np.where(self.episodes.vals[positions] == true_class, 1, -1)
        proto_update = predicted != true_class
        if self.log is not None:
            self.log.refine(positions, util_delta, true_class,
                            predicted if proto_update else -1, key)
        self._apply_refine(positions, util_delta, true_class,
                           predicted if proto_update else -1, key)
        return not proto_update

    def _apply_refine(self, positions: np.ndarray | None, util_delta: np.ndarray | None,
                      true_class: int, predicted: int, key: np.ndarray) -> None:
        if positions is not None and util_delta is not None and len(positions):
            clip = self.config.util_clip
            # Only the touched entries are read and written — copying the whole
            # utility array on every step made refinement quadratic. Repeated
            # positions (never produced by top-k, but legal in a log) are summed
            # first, so the result equals applying each delta in turn.
            unique, inverse = np.unique(np.asarray(positions, dtype=np.int64),
                                        return_inverse=True)
            summed = np.zeros(unique.size, dtype=np.int32)
            np.add.at(summed, inverse, np.asarray(util_delta, dtype=np.int32))
            util = self.episodes.util
            util[unique] = np.clip(util[unique].astype(np.int32) + summed,
                                   -clip, clip).astype(np.int16)
        if predicted >= 0 and predicted != true_class:
            signed = (unpack_bits(key[None, :], self.dimension)[0].astype(np.int32) * 2) - 1
            updated_rows = {true_class: self.prototypes.A[true_class].astype(np.int32) + signed}
            if not self.config.t2_local:
                updated_rows[predicted] = (self.prototypes.A[predicted].astype(np.int32)
                                           - signed)
            updated_rows = self.prototypes._halved_if_needed(updated_rows)
            packed_rows = {i: self.prototypes._binarise_row(i, row)
                           for i, row in updated_rows.items()}
            for i, row in updated_rows.items():
                self.prototypes.A[i] = row
            for i, row in packed_rows.items():
                self.prototypes.P[i] = row

    # -- T3 --------------------------------------------------------------------

    def consolidate(self, theta_merge: float = 0.12, util_max: int = 2) -> int:
        """T3 absorption: drop episodes their prototype already represents.

        An episode is absorbed when ``sim(key, P[val]) > θ_merge`` and its
        utility is below ``util_max``. No accumulator update — the episode
        is already in ``A`` from T1; adding it again would double-count
        (``docs/D2_SPEC.md`` v1.3, W17). Returns how many were absorbed.
        """
        n = len(self.episodes)
        if n == 0:
            return 0
        prototypes = self.prototypes.P[self.episodes.vals]
        dh = np.bitwise_count(np.bitwise_xor(self.episodes.keys, prototypes)).sum(
            axis=1, dtype=np.int64)
        absorb = ((sim_from_dh(dh, self.dimension) > theta_merge)
                  & (self.episodes.util < util_max))
        positions = np.flatnonzero(absorb)
        self.remove(positions, reason="absorb")
        return int(positions.size)

    def evict(self, count: int) -> np.ndarray:
        """T3 eviction: remove the ``count`` least useful episodes.

        Lowest utility first; ties broken by content id, so which episodes
        go does not depend on insertion order. Returns the removed ids.
        """
        count = int(min(max(count, 0), len(self.episodes)))
        if count == 0:
            return np.zeros(0, dtype=np.uint64)
        order = np.lexsort((self.episodes.id_rank(), self.episodes.util))
        positions = np.sort(order[:count])
        removed = self.episodes.ids[positions].copy()
        self.remove(positions, reason="evict")
        return removed

    def remove(self, positions: np.ndarray, reason: str) -> None:
        positions = np.asarray(positions, dtype=np.int64)
        if positions.size == 0:
            return
        if self.log is not None:
            self.log.remove(positions, reason)
        self.episodes.remove(positions)

    def fork(self, config: FusionConfig | None = None) -> Engramm:
        """An independent copy that shares the (immutable) episode keys.

        Prototypes and utilities are copied, so refining the fork leaves
        this instance untouched. Used by validation sweeps, which try many
        configurations from one T1 state without re-encoding or re-learning.
        The fork has no log attached.
        """
        other = Engramm(self.dimension, self.seed, config or self.config, log=None,
                        cache_bytes=self.episodes.cache_bytes)
        other.prototypes.labels = list(self.prototypes.labels)
        other.prototypes._index = dict(self.prototypes._index)
        other.prototypes.A = self.prototypes.A.copy()
        other.prototypes.P = self.prototypes.P.copy()
        other.prototypes.halvings = self.prototypes.halvings
        ep, mine = other.episodes, self.episodes
        ep.keys, ep.vals, ep.ids = mine.keys, mine.vals, mine.ids
        ep.util = mine.util.copy()
        ep._signed, ep._rank = mine._signed, mine._rank
        return other

    # -- state ------------------------------------------------------------------

    def state_digest(self) -> str:
        """SHA-256 of the learned state in a presentation-order-free form.

        Classes are taken in sorted label order and episodes in
        ``(label, id, key, util)`` order, so two memories built from the same
        examples in different orders produce the same digest — this is the
        property the M3 order-invariance test checks.
        """
        hasher = hashlib.sha256()
        order = sorted(range(self.n_classes), key=lambda i: self.labels[i])
        for i in order:
            hasher.update(self.labels[i].encode("utf-8") + b"\x00")
            hasher.update(np.ascontiguousarray(self.prototypes.A[i]).tobytes())
            hasher.update(np.ascontiguousarray(self.prototypes.P[i]).tobytes())
        ep = self.episodes
        episode_labels = [self.labels[v] for v in ep.vals]
        episode_order = sorted(range(len(ep)), key=lambda j: (
            episode_labels[j], int(ep.ids[j]), ep.keys[j].tobytes(), int(ep.util[j])))
        for j in episode_order:
            hasher.update(episode_labels[j].encode("utf-8") + b"\x00")
            hasher.update(ep.keys[j].tobytes())
            hasher.update(int(ep.util[j]).to_bytes(2, "big", signed=True))
        return hasher.hexdigest()
