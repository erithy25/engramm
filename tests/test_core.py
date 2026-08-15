"""Tests for the VSA algebra, item memory, and prototype classifier.

Verified against synthetic data with known structure, so every expectation
is derived rather than recorded from a previous run.

Statistical expectations (orthogonality, similarity after bundling) are
checked with wide tolerances against their analytic values, not against
observed constants — a test that pins an observed number would pass for the
wrong reason.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from engramm.core import (
    DEFAULT_DIMENSION,
    HALVE_THRESHOLD,
    _halve_signed,
    ItemMemory,
    PrototypeClassifier,
    TieContext,
    bind,
    bundle,
    from_signed,
    pack_bits,
    permute,
    resolve_tie,
    to_signed,
    unbind,
    unpack_bits,
)
from engramm.metrics import accuracy, hamming, macro_f1, popcount_rows, sim_from_dh

D = DEFAULT_DIMENSION
SEED = 42


@pytest.fixture
def memory() -> ItemMemory:
    return ItemMemory(SEED, D)


# ---------------------------------------------------------------------------
# Packing and conversions
# ---------------------------------------------------------------------------

def test_pack_unpack_roundtrip() -> None:
    rng = np.random.default_rng(SEED)
    bits = rng.integers(0, 2, size=D, dtype=np.uint8)
    assert np.array_equal(unpack_bits(pack_bits(bits), D), bits)


def test_signed_roundtrip(memory: ItemMemory) -> None:
    vector = memory.vector("alpha")
    signed = to_signed(vector, D)
    assert set(np.unique(signed).tolist()) <= {-1, 1}
    assert np.array_equal(from_signed(signed), vector)


def test_from_signed_rejects_zeros() -> None:
    signed = np.ones(D, dtype=np.int8)
    signed[7] = 0
    with pytest.raises(ValueError, match="zeros"):
        from_signed(signed)


@pytest.mark.parametrize("bad", [0, 7, 12, -8])
def test_invalid_dimension_rejected(bad: int) -> None:
    with pytest.raises(ValueError, match="multiple of 8"):
        ItemMemory(SEED, bad)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_popcount_matches_python_reference() -> None:
    rng = np.random.default_rng(SEED)
    packed = rng.integers(0, 256, size=(5, 16), dtype=np.uint8)
    expected = [sum(int(b).bit_count() for b in row) for row in packed]
    assert popcount_rows(packed).tolist() == expected


def test_hamming_against_explicit_bit_comparison() -> None:
    rng = np.random.default_rng(SEED)
    a_bits = rng.integers(0, 2, size=D, dtype=np.uint8)
    b_bits = rng.integers(0, 2, size=D, dtype=np.uint8)
    expected = int(np.count_nonzero(a_bits != b_bits))
    assert int(hamming(pack_bits(a_bits), pack_bits(b_bits))) == expected


def test_hamming_broadcasts_to_full_matrix(memory: ItemMemory) -> None:
    queries = memory.vectors(["q0", "q1", "q2"])
    prototypes = memory.vectors(["p0", "p1"])
    distances = hamming(queries[:, None, :], prototypes[None, :, :])
    assert distances.shape == (3, 2)
    for i in range(3):
        for j in range(2):
            assert distances[i, j] == hamming(queries[i], prototypes[j])


@pytest.mark.parametrize("dh,expected", [(0, 1.0), (D // 2, 0.0), (D, -1.0)])
def test_sim_from_dh_endpoints(dh: int, expected: float) -> None:
    assert sim_from_dh(dh, D) == pytest.approx(expected)


def test_accuracy_and_macro_f1_on_known_confusion() -> None:
    # Class 0: 3 samples, all correct. Class 1: 1 sample, predicted as 0.
    y_true = np.array([0, 0, 0, 1])
    y_pred = np.array([0, 0, 0, 0])
    assert accuracy(y_true, y_pred) == pytest.approx(0.75)
    # Class 0: TP=3, FP=1, FN=0 -> F1 = 6/7. Class 1: TP=0 -> F1 = 0.
    assert macro_f1(y_true, y_pred, 2) == pytest.approx((6 / 7 + 0.0) / 2)


def test_macro_f1_penalises_ignoring_a_small_class() -> None:
    """Accuracy stays high while macro-F1 collapses — the reason both are reported."""
    y_true = np.array([0] * 99 + [1])
    y_pred = np.zeros(100, dtype=np.int64)
    assert accuracy(y_true, y_pred) == pytest.approx(0.99)
    assert macro_f1(y_true, y_pred, 2) < 0.51


def test_macro_f1_counts_absent_classes() -> None:
    y = np.array([0, 0, 1, 1])
    assert macro_f1(y, y, 2) == pytest.approx(1.0)
    # A third class present in neither array still contributes 0.
    assert macro_f1(y, y, 3) == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# Item memory
# ---------------------------------------------------------------------------

def test_item_memory_is_deterministic_across_instances() -> None:
    a = ItemMemory(SEED, D).vector("trigram")
    b = ItemMemory(SEED, D).vector("trigram")
    assert np.array_equal(a, b)


def test_item_memory_depends_on_seed() -> None:
    a = ItemMemory(1, D).vector("trigram")
    b = ItemMemory(2, D).vector("trigram")
    assert not np.array_equal(a, b)


def test_item_memory_is_insertion_order_independent() -> None:
    """A symbol's vector must not depend on when it was first requested.

    This is what allows the learned state to be independent of presentation
    order; a stream-drawn item memory would fail here.
    """
    forward = ItemMemory(SEED, D)
    backward = ItemMemory(SEED, D)
    symbols = ["a", "b", "c", "d"]
    for s in symbols:
        forward.vector(s)
    for s in reversed(symbols):
        backward.vector(s)
    for s in symbols:
        assert np.array_equal(forward.vector(s), backward.vector(s))


def test_item_memory_cache_returns_equal_values(memory: ItemMemory) -> None:
    first = memory.vector("repeated")
    second = memory.vector("repeated")
    assert np.array_equal(first, second)


def test_item_memory_accepts_str_and_bytes_equivalently(memory: ItemMemory) -> None:
    assert np.array_equal(memory.vector("abc"), memory.vector(b"abc"))


def test_distinct_symbols_are_near_orthogonal(memory: ItemMemory) -> None:
    """Independent random hypervectors sit at Hamming distance ~D/2.

    Expected distance D/2 = 5000 with SD = sqrt(D)/2 = 50. Allowing 5 SD
    keeps the test from flaking while still failing loudly if vectors are
    correlated.
    """
    vectors = memory.vectors([f"sym{i}" for i in range(40)])
    distances = hamming(vectors[:, None, :], vectors[None, :, :])
    off_diagonal = distances[~np.eye(len(vectors), dtype=bool)]
    sd = math.sqrt(D) / 2
    assert abs(off_diagonal.mean() - D / 2) < 5 * sd
    assert off_diagonal.min() > D / 2 - 6 * sd


def test_item_memory_bits_are_balanced(memory: ItemMemory) -> None:
    """Each vector has roughly half its bits set, as uniform bits require."""
    vectors = memory.vectors([f"sym{i}" for i in range(30)])
    ones = popcount_rows(vectors)
    sd = math.sqrt(D) / 2
    assert abs(ones.mean() - D / 2) < 5 * sd


def test_item_memory_vectors_are_immutable(memory: ItemMemory) -> None:
    """Cached vectors are read-only, so a caller cannot corrupt the memory."""
    with pytest.raises(ValueError):
        memory.vector("x")[0] = 255


def test_empty_symbol_list_gives_empty_stack(memory: ItemMemory) -> None:
    assert memory.vectors([]).shape == (0, D // 8)


# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------

def test_binding_is_its_own_inverse(memory: ItemMemory) -> None:
    a, b = memory.vector("a"), memory.vector("b")
    assert np.array_equal(unbind(bind(a, b), b), a)


def test_binding_destroys_similarity(memory: ItemMemory) -> None:
    """A bound pair is ~D/2 from each of its operands."""
    a, b = memory.vector("a"), memory.vector("b")
    bound = bind(a, b)
    sd = math.sqrt(D) / 2
    assert abs(int(hamming(bound, a)) - D / 2) < 5 * sd
    assert abs(int(hamming(bound, b)) - D / 2) < 5 * sd


def test_binding_is_commutative_and_associative(memory: ItemMemory) -> None:
    a, b, c = (memory.vector(s) for s in "abc")
    assert np.array_equal(bind(a, b), bind(b, a))
    assert np.array_equal(bind(bind(a, b), c), bind(a, bind(b, c)))


def test_binding_preserves_distance(memory: ItemMemory) -> None:
    """XOR with a fixed vector is an isometry on Hamming distance."""
    a, b, key = (memory.vector(s) for s in ["a", "b", "key"])
    assert int(hamming(bind(a, key), bind(b, key))) == int(hamming(a, b))


def test_binding_with_self_gives_zero(memory: ItemMemory) -> None:
    a = memory.vector("a")
    assert int(popcount_rows(bind(a, a))) == 0


# ---------------------------------------------------------------------------
# Permutation
# ---------------------------------------------------------------------------

def test_permutation_is_invertible(memory: ItemMemory) -> None:
    a = memory.vector("a")
    assert np.array_equal(permute(permute(a, 3, D), -3, D), a)


def test_permutation_destroys_similarity(memory: ItemMemory) -> None:
    a = memory.vector("a")
    sd = math.sqrt(D) / 2
    assert abs(int(hamming(permute(a, 1, D), a)) - D / 2) < 5 * sd


def test_permutation_matches_roll_semantics(memory: ItemMemory) -> None:
    a = memory.vector("a")
    expected = np.roll(unpack_bits(a, D), 5)
    assert np.array_equal(unpack_bits(permute(a, 5, D), D), expected)


def test_permutation_by_full_dimension_is_identity(memory: ItemMemory) -> None:
    a = memory.vector("a")
    assert np.array_equal(permute(a, D, D), a)


def test_permutation_distinguishes_sequence_order(memory: ItemMemory) -> None:
    """The property a bare bundle lacks: (a,b) must differ from (b,a)."""
    a, b = memory.vector("a"), memory.vector("b")
    ab = bind(a, permute(b, 1, D))
    ba = bind(b, permute(a, 1, D))
    assert not np.array_equal(ab, ba)


def test_permutation_preserves_distance(memory: ItemMemory) -> None:
    a, b = memory.vector("a"), memory.vector("b")
    assert int(hamming(permute(a, 4, D), permute(b, 4, D))) == int(hamming(a, b))


def test_permutation_broadcasts_over_a_stack(memory: ItemMemory) -> None:
    stack = memory.vectors(["a", "b", "c"])
    rotated = permute(stack, 2, D)
    assert rotated.shape == stack.shape
    for i in range(3):
        assert np.array_equal(rotated[i], permute(stack[i], 2, D))


# ---------------------------------------------------------------------------
# Bundling (odd counts only — see the tie tests below)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n", [1, 3, 5, 9])
def test_bundle_is_similar_to_its_constituents(memory: ItemMemory, n: int) -> None:
    """Every bundled vector stays far closer than chance to the bundle."""
    vectors = memory.vectors([f"member{i}" for i in range(n)])
    bundled = bundle(vectors, D)
    for i in range(n):
        assert int(hamming(bundled, vectors[i])) < D / 2 - 5 * math.sqrt(D) / 2


def test_bundle_of_one_is_identity(memory: ItemMemory) -> None:
    a = memory.vector("a")
    assert np.array_equal(bundle(a[None, :], D), a)


def test_bundle_is_dissimilar_to_non_members(memory: ItemMemory) -> None:
    members = memory.vectors([f"member{i}" for i in range(5)])
    bundled = bundle(members, D)
    outsider = memory.vector("outsider")
    sd = math.sqrt(D) / 2
    assert abs(int(hamming(bundled, outsider)) - D / 2) < 5 * sd


def test_bundle_similarity_decreases_with_size(memory: ItemMemory) -> None:
    """Crosstalk grows with the number bundled, so similarity must fall."""
    similarities = []
    for n in (3, 9, 27, 81):
        vectors = memory.vectors([f"m{i}" for i in range(n)])
        bundled = bundle(vectors, D)
        similarities.append(float(sim_from_dh(hamming(bundled, vectors[0]), D)))
    assert similarities == sorted(similarities, reverse=True)
    assert similarities[-1] > 0  # still recoverable at 81 members


def test_bundle_is_order_independent(memory: ItemMemory) -> None:
    vectors = memory.vectors([f"m{i}" for i in range(5)])
    assert np.array_equal(bundle(vectors, D), bundle(vectors[::-1], D))


def test_bundle_rejects_empty_and_wrong_shape(memory: ItemMemory) -> None:
    with pytest.raises(ValueError, match="empty"):
        bundle(np.empty((0, D // 8), dtype=np.uint8), D)
    with pytest.raises(ValueError, match="2-D"):
        bundle(memory.vector("a"), D)


# ---------------------------------------------------------------------------
# Tie resolution — open decision
# ---------------------------------------------------------------------------

def test_resolve_tie_is_not_implemented() -> None:
    """The rule is deliberately open; see docs/UNDERSTANDING.md B2.2."""
    totals = np.zeros(8, dtype=np.int32)
    with pytest.raises(NotImplementedError, match="UNDERSTANDING"):
        resolve_tie(totals, totals == 0, TieContext(dimension=D))


def test_even_bundle_raises_until_the_rule_is_settled(memory: ItemMemory) -> None:
    """An even bundle produces exact ties, which currently cannot be resolved.

    Two independent vectors disagree on ~D/2 components, and every
    disagreeing component of a two-vector bundle is an exact tie, so this
    reliably reaches the unimplemented path.
    """
    vectors = memory.vectors(["a", "b"])
    with pytest.raises(NotImplementedError):
        bundle(vectors, D)


@pytest.mark.skip(reason="tie-break rule not yet decided — docs/UNDERSTANDING.md B2.2")
def test_even_bundle_is_similar_to_its_constituents() -> None:
    """Enable once the tie rule is implemented.

    An even bundle must satisfy the same property as an odd one: every
    constituent stays closer to the bundle than chance. Whatever rule is
    chosen has to preserve that.
    """
    memory = ItemMemory(SEED, D)
    vectors = memory.vectors([f"member{i}" for i in range(4)])
    bundled = bundle(vectors, D)
    for i in range(4):
        assert int(hamming(bundled, vectors[i])) < D / 2 - 5 * math.sqrt(D) / 2


# ---------------------------------------------------------------------------
# Prototype classifier
# ---------------------------------------------------------------------------

def _training_set(memory: ItemMemory, n_classes: int, per_class: int,
                  noise: float, seed: int = SEED
                  ) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Build linearly separable synthetic classes.

    Each class has a hidden centre hypervector; an example is that centre
    with a fraction ``noise`` of its bits flipped. Class identity is
    therefore recoverable in principle, and the difficulty is controlled.
    """
    rng = np.random.default_rng(seed)
    centres = memory.vectors([f"centre{c}" for c in range(n_classes)])
    packed, signed, labels = [], [], []
    for c in range(n_classes):
        centre_bits = unpack_bits(centres[c], D)
        for _ in range(per_class):
            flip = rng.random(D) < noise
            bits = np.bitwise_xor(centre_bits, flip.astype(np.uint8))
            vector = pack_bits(bits)
            packed.append(vector)
            signed.append(to_signed(vector, D))
            labels.append(f"class{c}")
    return np.stack(packed), np.stack(signed).astype(np.int8), labels


def test_classifier_learns_separable_classes(memory: ItemMemory) -> None:
    packed, signed, labels = _training_set(memory, n_classes=5, per_class=9, noise=0.2)
    model = PrototypeClassifier(D)
    model.learn(signed, labels)
    predicted = model.predict_labels(packed)
    assert accuracy(np.array(labels), np.array(predicted)) == 1.0


def test_classifier_generalises_to_unseen_examples(memory: ItemMemory) -> None:
    _, train_signed, train_labels = _training_set(memory, 5, 9, 0.2, seed=1)
    test_packed, _, test_labels = _training_set(memory, 5, 5, 0.2, seed=2)
    model = PrototypeClassifier(D)
    model.learn(train_signed, train_labels)
    predicted = model.predict_labels(test_packed)
    assert accuracy(np.array(test_labels), np.array(predicted)) == 1.0


def test_classifier_is_at_chance_on_unlearnable_data(memory: ItemMemory) -> None:
    """Guards against a test suite that would pass on noise."""
    rng = np.random.default_rng(SEED)
    n = 63  # 21 per class — odd, so no exact ties arise
    packed = np.stack([pack_bits(rng.integers(0, 2, D, dtype=np.uint8))
                       for _ in range(n)])
    signed = np.stack([to_signed(v, D) for v in packed]).astype(np.int8)
    labels = [f"class{i % 3}" for i in range(n)]
    model = PrototypeClassifier(D)
    model.learn(signed, labels)
    held_out = np.stack([pack_bits(rng.integers(0, 2, D, dtype=np.uint8))
                         for _ in range(n)])
    predicted = model.predict_labels(held_out)
    assert accuracy(np.array(labels), np.array(predicted)) < 0.6


def test_class_indices_are_independent_of_sample_order(memory: ItemMemory) -> None:
    """A shuffled batch must give the identical learned state, bit for bit."""
    _, signed, labels = _training_set(memory, 4, 5, 0.2)
    forward = PrototypeClassifier(D)
    forward.learn(signed, labels)

    order = np.random.default_rng(7).permutation(len(labels))
    shuffled = PrototypeClassifier(D)
    shuffled.learn(signed[order], [labels[i] for i in order])

    assert forward.labels == shuffled.labels
    assert np.array_equal(forward.A, shuffled.A)
    assert np.array_equal(forward.P, shuffled.P)


def test_learning_is_incremental(memory: ItemMemory) -> None:
    """Two batches must accumulate to the same state as one combined batch.

    Both the split batches and the total carry an odd count per class, so
    no intermediate binarisation hits an unresolved tie.
    """
    _, signed, labels = _training_set(memory, 3, 3, 0.2)
    extra_packed, extra_signed, extra_labels = _training_set(memory, 3, 6, 0.2, seed=11)

    all_signed = np.concatenate([signed, extra_signed])
    all_labels = list(labels) + list(extra_labels)

    combined = PrototypeClassifier(D)
    combined.learn(all_signed, all_labels)

    incremental = PrototypeClassifier(D)
    incremental.learn(signed, labels)
    incremental.learn(extra_signed, extra_labels)

    assert np.array_equal(combined.A, incremental.A)
    assert np.array_equal(combined.P, incremental.P)


def test_prototype_is_binarisation_of_accumulator(memory: ItemMemory) -> None:
    _, signed, labels = _training_set(memory, 3, 5, 0.2)
    model = PrototypeClassifier(D)
    model.learn(signed, labels)
    for index in range(model.n_classes):
        assert np.array_equal(unpack_bits(model.P[index], D),
                              (model.A[index] > 0).astype(np.uint8))


def test_score_shape_and_range(memory: ItemMemory) -> None:
    packed, signed, labels = _training_set(memory, 4, 5, 0.2)
    model = PrototypeClassifier(D)
    model.learn(signed, labels)
    scores = model.score(packed)
    assert scores.shape == (len(labels), 4)
    assert np.all(scores >= -1.0) and np.all(scores <= 1.0)


@pytest.mark.parametrize("chunk_size", [1, 7, 512, 10_000])
def test_scoring_is_independent_of_chunk_size(memory: ItemMemory,
                                              chunk_size: int) -> None:
    packed, signed, labels = _training_set(memory, 3, 5, 0.2)
    model = PrototypeClassifier(D)
    model.learn(signed, labels)
    assert np.array_equal(model.score(packed, chunk_size=chunk_size),
                          model.score(packed, chunk_size=512))


def test_learn_online_reports_correct_without_changing_state(memory: ItemMemory) -> None:
    packed, signed, labels = _training_set(memory, 3, 9, 0.15)
    model = PrototypeClassifier(D)
    model.learn(signed, labels)
    before = model.A.copy()
    assert model.learn_online(packed[0], signed[0], labels[0]) is True
    assert np.array_equal(model.A, before)


def test_learn_online_on_a_miss_is_blocked_and_atomic(memory: ItemMemory) -> None:
    """The refinement step needs the tie rule, and must not half-apply itself.

    A single-vector update flips the parity of every accumulator component:
    after an odd-sized batch each component is odd, and adding one more
    ``±1`` makes it even, so exact zeros become possible. The error-driven
    step therefore always depends on the tie rule, not only for even input
    sizes. Until that rule exists the step must raise **and leave the model
    exactly as it was** — a committed accumulator with a stale prototype
    would be a silently corrupted state.
    """
    packed, signed, labels = _training_set(memory, 3, 9, 0.15)
    model = PrototypeClassifier(D)
    model.learn(signed, labels)

    wrong_label = "class2" if labels[0] == "class0" else "class0"
    accumulator_before = model.A.copy()
    prototypes_before = model.P.copy()

    with pytest.raises(NotImplementedError):
        model.learn_online(packed[0], signed[0], wrong_label)

    assert np.array_equal(model.A, accumulator_before)
    assert np.array_equal(model.P, prototypes_before)


@pytest.mark.skip(reason="tie-break rule not yet decided — docs/UNDERSTANDING.md B2.2")
def test_learn_online_moves_prototypes_on_a_miss() -> None:
    """Enable once the tie rule is implemented.

    A forced mislabel must pull the named class toward the example by
    exactly the example's signed vector, and push the predicted class away
    by the same amount.
    """
    memory = ItemMemory(SEED, D)
    packed, signed, labels = _training_set(memory, 3, 9, 0.15)
    model = PrototypeClassifier(D)
    model.learn(signed, labels)

    wrong_label = "class2" if labels[0] == "class0" else "class0"
    wrong_index = model._index[wrong_label]
    before = model.A[wrong_index].copy()

    assert model.learn_online(packed[0], signed[0], wrong_label) is False
    assert np.array_equal(model.A[wrong_index], before + signed[0])


def test_learn_batch_is_atomic_on_a_tie(memory: ItemMemory) -> None:
    """An even-sized batch raises without leaving a partially updated state."""
    _, signed, labels = _training_set(memory, 2, 4, 0.2)
    model = PrototypeClassifier(D)
    with pytest.raises(NotImplementedError):
        model.learn(signed, labels)
    assert not model.A.any()
    assert not model.P.any()


def test_learn_online_rejects_scoring_without_classes() -> None:
    model = PrototypeClassifier(D)
    with pytest.raises(RuntimeError, match="before any class"):
        model.score(np.zeros((1, D // 8), dtype=np.uint8))


def test_accumulator_halves_before_overflow(memory: ItemMemory) -> None:
    """The int16 accumulator must never wrap; halving keeps it in range."""
    _, signed, labels = _training_set(memory, 2, 1, 0.2)
    model = PrototypeClassifier(D)
    model.learn(signed, labels)
    model.A[:] = HALVE_THRESHOLD
    model.A[0, 0] = HALVE_THRESHOLD + 1

    model.learn(signed, labels)

    assert int(np.abs(model.A).max()) <= HALVE_THRESHOLD
    assert model.A.dtype == np.int16


def test_halving_never_loses_a_sign() -> None:
    """Sign-preserving halving is the invariant the prototypes rely on.

    Plain integer division sends ``+1`` to ``0``, destroying that
    component's sign and manufacturing a tie the data never produced.
    """
    values = np.array([5, 3, 2, 1, 0, -1, -2, -3, -5], dtype=np.int16)
    halved = _halve_signed(values)
    assert np.array_equal(np.sign(halved), np.sign(values))
    assert np.count_nonzero(halved == 0) == np.count_nonzero(values == 0)
    assert np.all(np.abs(halved) <= np.maximum(np.abs(values), 1))


def test_halving_does_not_change_prototypes(memory: ItemMemory) -> None:
    """Halving may not change what the binarised prototype says."""
    _, signed, labels = _training_set(memory, 3, 9, 0.2)
    model = PrototypeClassifier(D)
    model.learn(signed, labels)
    before = model.P.copy()

    model.A = _halve_signed(model.A)
    model._rebinarise(range(model.n_classes))

    assert np.array_equal(model.P, before)


def test_shape_mismatches_are_rejected(memory: ItemMemory) -> None:
    model = PrototypeClassifier(D)
    with pytest.raises(ValueError, match="labels"):
        model.learn(np.zeros((3, D), dtype=np.int8), ["a", "b"])
    with pytest.raises(ValueError, match="shape"):
        model.learn(np.zeros((3, 64), dtype=np.int8), ["a", "b", "c"])
