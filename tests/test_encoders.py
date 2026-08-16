"""Tests for the text and image encoders.

Expectations are derived from the encoding scheme, not recorded from a
previous run. The vectorised implementations are checked against
straightforward reference implementations written for clarity rather than
speed — that comparison is what makes the optimisations trustworthy.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from engramm.core import ItemMemory, permute, unpack_bits
from engramm.encoders import (
    PixelThermometerEncoder,
    TrigramEncoder,
    build_encoder,
)
from engramm.metrics import hamming

D = 1024
SEED = 42


@pytest.fixture
def memory() -> ItemMemory:
    return ItemMemory(SEED, D)


# ---------------------------------------------------------------------------
# Reference implementations
# ---------------------------------------------------------------------------

def _reference_trigram(encoder: TrigramEncoder, text: str) -> np.ndarray:
    """One text, one trigram at a time — the definition, written plainly."""
    data = text.encode("utf-8")
    totals = np.zeros(encoder.dimension, dtype=np.int32)
    for i in range(len(data) - 2):
        bound = (encoder._tables[0][data[i]]
                 ^ encoder._tables[1][data[i + 1]]
                 ^ encoder._tables[2][data[i + 2]])
        totals += unpack_bits(bound, encoder.dimension).astype(np.int32) * 2 - 1
    return totals


def _reference_pixels(encoder: PixelThermometerEncoder,
                      image: np.ndarray) -> np.ndarray:
    levels = encoder.quantise(image)
    totals = np.zeros(encoder.dimension, dtype=np.int32)
    for position, level in enumerate(levels):
        bound = encoder._bound[position, level]
        totals += unpack_bits(bound, encoder.dimension).astype(np.int32) * 2 - 1
    return totals


# ---------------------------------------------------------------------------
# Trigram encoder
# ---------------------------------------------------------------------------

def test_trigram_matches_reference_implementation(memory: ItemMemory) -> None:
    encoder = TrigramEncoder(memory)
    texts = ["short text here", "a much longer paragraph " * 12, "middling one " * 3]
    expected = np.stack([_reference_trigram(encoder, t) for t in texts])
    assert np.array_equal(encoder.accumulate(texts), expected)


def test_trigram_grouping_does_not_reorder_results(memory: ItemMemory) -> None:
    """Length-sorted chunking must be invisible: row i stays sample i."""
    encoder = TrigramEncoder(memory)
    texts = ["tiny one here", "medium length text " * 6, "x" * 900, "abc def ghi"]
    batch = encoder.accumulate(texts)
    for i, text in enumerate(texts):
        assert np.array_equal(batch[i], encoder.accumulate([text])[0])


def test_rotation_depth_matches_the_recovered_specification(memory: ItemMemory) -> None:
    """Pins *which* rotation goes on which byte, not merely that order matters.

    The surviving D2 fragment reads ``rot1(V[seq[i+1]])`` with nothing on
    ``seq[i+2]``, which fixes the assignment as ρ² · ρ¹ · ρ⁰ across the
    trigram (``docs/DEVIATIONS.md`` INFERRED-2). Swapping ρ² and ρ¹ yields
    an encoding that is still order-sensitive and still works — so only an
    explicit check can keep the rebuild faithful to the record.
    """
    encoder = TrigramEncoder(memory)
    data = b"abc"
    expected_bound = (permute(memory.vector(data[0:1]), 2, D)
                      ^ permute(memory.vector(data[1:2]), 1, D)
                      ^ memory.vector(data[2:3]))
    expected = unpack_bits(expected_bound, D).astype(np.int32) * 2 - 1
    assert np.array_equal(encoder.accumulate(["abc"])[0], expected)


def test_trigram_is_order_sensitive(memory: ItemMemory) -> None:
    """Rotation by position is what distinguishes 'abc' from 'cba'."""
    encoder = TrigramEncoder(memory)
    forward = encoder.accumulate(["abcabcabcabc"])
    reverse = encoder.accumulate(["cbacbacbacba"])
    assert not np.array_equal(forward, reverse)


def test_trigram_is_deterministic(memory: ItemMemory) -> None:
    encoder = TrigramEncoder(memory)
    text = ["reproducible input text"]
    assert np.array_equal(encoder.accumulate(text), encoder.accumulate(text))
    fresh = TrigramEncoder(ItemMemory(SEED, D))
    assert np.array_equal(encoder.accumulate(text), fresh.accumulate(text))


def test_trigram_depends_on_the_seed() -> None:
    text = ["some text to encode"]
    first = TrigramEncoder(ItemMemory(1, D)).accumulate(text)
    second = TrigramEncoder(ItemMemory(2, D)).accumulate(text)
    assert not np.array_equal(first, second)


def test_trigram_operates_on_bytes_not_codepoints(memory: ItemMemory) -> None:
    """A non-ASCII character spans several UTF-8 bytes (DEVIATIONS INFERRED-1)."""
    encoder = TrigramEncoder(memory)
    assert np.array_equal(encoder.accumulate(["über"]),
                          encoder.accumulate(["über".encode("utf-8")]))
    # 'über' is 5 bytes, so it has 3 byte trigrams rather than 2 character ones.
    assert len("über".encode("utf-8")) - 2 == 3


def test_trigram_similar_texts_are_similar(memory: ItemMemory) -> None:
    """Shared substrings must survive bundling as measurable similarity."""
    encoder = TrigramEncoder(memory)
    base = "the quick brown fox jumps over the lazy dog " * 4
    totals = encoder.accumulate([base, base + " and then some more words",
                                 "completely different content entirely " * 4])
    signs = np.sign(totals)
    related = float(np.mean(signs[0] == signs[1]))
    unrelated = float(np.mean(signs[0] == signs[2]))
    assert related > 0.9
    assert unrelated < related


def test_trigram_rejects_texts_without_trigrams(memory: ItemMemory) -> None:
    """A text under three bytes has an all-zero accumulator (GAP-3)."""
    encoder = TrigramEncoder(memory)
    with pytest.raises(ValueError, match="no trigrams"):
        encoder.accumulate(["ok text here", "ab"])


def test_trigram_rejects_embedded_separator(memory: ItemMemory) -> None:
    encoder = TrigramEncoder(memory)
    with pytest.raises(ValueError, match="NUL byte"):
        encoder.accumulate(["fine text", "bad\x00text here"])


def test_trigram_empty_batch(memory: ItemMemory) -> None:
    assert TrigramEncoder(memory).accumulate([]).shape == (0, D)


# ---------------------------------------------------------------------------
# KNOWN-1: a single text larger than the chunk budget
# ---------------------------------------------------------------------------

def _text_with_trigrams(n: int, seed: int) -> str:
    """A deterministic text of exactly ``n`` trigrams.

    Printable ASCII only. A character above 127 encodes to two UTF-8 bytes,
    and the encoder counts bytes rather than characters
    (``docs/DEVIATIONS.md`` INFERRED-1) — a latin-1 fixture would produce
    roughly 1.5x the requested trigram count and quietly invalidate every
    size assumption below.
    """
    rng = np.random.default_rng(seed)
    return bytes(rng.integers(32, 127, size=n + 2, dtype=np.uint8)).decode("ascii")


def _assert_exceeds(encoder: TrigramEncoder, text: str) -> int:
    """Fail loudly if a fixture does not actually reach the split path.

    Without this the tests below would still pass while never entering the
    code they exist to cover — the split would simply never trigger and the
    comparison would compare the single-pass path against itself.
    """
    count = len(text.encode("utf-8")) - 2
    assert count * encoder.dimension > encoder.chunk_bytes, (
        f"fixture has {count} trigrams at D={encoder.dimension}, which fits "
        f"the {encoder.chunk_bytes} byte budget — the split path is not reached"
    )
    return count


def test_oversized_text_matches_single_pass_encoding(memory: ItemMemory) -> None:
    """The split path must reproduce the unsplit result exactly.

    Bundling is a sum over trigrams and addition is associative, so this
    holds by construction — but by construction is what the original memory
    bound also claimed, so it is checked rather than argued.
    """
    small_budget = TrigramEncoder(memory, chunk_bytes=64 * 1024)
    text = _text_with_trigrams(2_000, seed=1)
    _assert_exceeds(small_budget, text)

    unlimited = TrigramEncoder(memory, chunk_bytes=1 << 40)
    assert np.array_equal(small_budget.accumulate([text]),
                          unlimited.accumulate([text]))


@pytest.mark.parametrize("n_trigrams", [1_000, 4_001, 12_000])
def test_split_is_exact_at_several_sizes(memory: ItemMemory, n_trigrams: int) -> None:
    """Includes a size that is not a whole multiple of the sub-chunk."""
    small_budget = TrigramEncoder(memory, chunk_bytes=64 * 1024)
    unlimited = TrigramEncoder(memory, chunk_bytes=1 << 40)
    text = _text_with_trigrams(n_trigrams, seed=n_trigrams)
    _assert_exceeds(small_budget, text)
    assert np.array_equal(small_budget.accumulate([text]),
                          unlimited.accumulate([text]))


def test_mixed_batch_of_normal_and_oversized_texts(memory: ItemMemory) -> None:
    """Oversized texts are pulled out of grouping; the rest must be unaffected."""
    small_budget = TrigramEncoder(memory, chunk_bytes=64 * 1024)
    unlimited = TrigramEncoder(memory, chunk_bytes=1 << 40)
    texts = [_text_with_trigrams(300, 10),
             _text_with_trigrams(5_000, 11),
             _text_with_trigrams(50, 12),
             _text_with_trigrams(9_000, 13)]
    _assert_exceeds(small_budget, texts[1])
    _assert_exceeds(small_budget, texts[3])

    assert np.array_equal(small_budget.accumulate(texts), unlimited.accumulate(texts))
    # Row order must survive the partition into oversized and normal.
    for i, text in enumerate(texts):
        assert np.array_equal(small_budget.accumulate(texts)[i],
                              unlimited.accumulate([text])[0])


def test_oversized_text_at_the_real_default_budget() -> None:
    """The same property at the shipped budget, not only a shrunken one.

    Uses a text large enough to exceed the real `_CHUNK_BYTES`, so the
    guarantee is demonstrated for the configuration that actually runs.
    """
    from engramm.encoders import _CHUNK_BYTES

    dimension = 1024
    encoder = TrigramEncoder(ItemMemory(SEED, dimension))
    assert encoder.chunk_bytes == _CHUNK_BYTES
    text = _text_with_trigrams(_CHUNK_BYTES // dimension + 5_000, seed=99)
    _assert_exceeds(encoder, text)

    unlimited = TrigramEncoder(ItemMemory(SEED, dimension), chunk_bytes=1 << 40)
    assert np.array_equal(encoder.accumulate([text]), unlimited.accumulate([text]))


def test_budget_bounds_the_intermediate_allocation(memory: ItemMemory) -> None:
    """The split must actually happen in more than one piece.

    Guards the point of the fix: an implementation that "splits" into a
    single piece would satisfy every equality test above while allocating
    exactly as much as before.
    """
    budget = 64 * 1024
    encoder = TrigramEncoder(memory, chunk_bytes=budget)
    text = _text_with_trigrams(8_000, seed=7)
    count = _assert_exceeds(encoder, text)
    per_chunk = max(1, budget // encoder.dimension)
    assert count // per_chunk >= 2, "fixture must require at least two sub-chunks"
    assert per_chunk * encoder.dimension <= budget


def test_oversized_texts_actually_take_the_split_path(
        memory: ItemMemory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fails if the split is never triggered — which equality tests cannot catch.

    Both paths compute the same values, so every comparison above passes
    whether or not the split happens. Only the memory behaviour differs, and
    that is the entire point of the fix. So this asserts the routing itself:
    oversized texts go through the splitting path, normal texts do not.

    Found by mutation testing — disabling the split left the whole suite
    green.
    """
    # 1 MiB budget at D=1024 puts the threshold at 1024 trigrams, so the
    # "normal" fixtures below sit clearly under it and the large ones over.
    encoder = TrigramEncoder(memory, chunk_bytes=1024 * 1024)
    calls: list[int] = []
    original = encoder._accumulate_oversized

    def spy(blob, span, count, row, totals):
        calls.append(count)
        return original(blob, span, count, row, totals)

    monkeypatch.setattr(encoder, "_accumulate_oversized", spy)

    normal = [_text_with_trigrams(100, 20), _text_with_trigrams(200, 21)]
    encoder.accumulate(normal)
    assert calls == [], "a text within budget must not be split"

    big_a, big_b = _text_with_trigrams(5_000, 22), _text_with_trigrams(7_000, 23)
    _assert_exceeds(encoder, big_a)
    _assert_exceeds(encoder, big_b)
    encoder.accumulate([normal[0], big_a, normal[1], big_b])
    assert sorted(calls) == [5_000, 7_000], (
        f"expected both oversized texts to be split, got {calls}"
    )


def test_sub_chunk_count_grows_with_text_size(memory: ItemMemory,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    """A larger text must be split into more pieces, not one bigger piece."""
    budget = 1024 * 1024
    encoder = TrigramEncoder(memory, chunk_bytes=budget)
    per_chunk = max(1, budget // encoder.dimension)

    sizes: list[int] = []
    real_unpack = np.unpackbits

    def counting_unpack(array, *args, **kwargs):
        sizes.append(array.shape[0] if array.ndim > 1 else 1)
        return real_unpack(array, *args, **kwargs)

    monkeypatch.setattr(np, "unpackbits", counting_unpack)
    encoder.accumulate([_text_with_trigrams(10_000, 30)])

    assert len(sizes) >= 2, "a 10,000-trigram text must need several sub-chunks"
    assert max(sizes) <= per_chunk, (
        f"a sub-chunk of {max(sizes)} rows exceeds the {per_chunk}-row budget"
    )
    assert sum(sizes) == 10_000, "every trigram must be covered exactly once"


def test_chunk_bytes_is_validated(memory: ItemMemory) -> None:
    with pytest.raises(ValueError, match="chunk_bytes"):
        TrigramEncoder(memory, chunk_bytes=0)


# ---------------------------------------------------------------------------
# Pixel / thermometer encoder
# ---------------------------------------------------------------------------

def test_pixel_matches_reference_implementation(memory: ItemMemory) -> None:
    encoder = PixelThermometerEncoder(memory, n_positions=64, n_levels=16)
    images = np.random.default_rng(SEED).integers(0, 256, size=(5, 64), dtype=np.uint8)
    expected = np.stack([_reference_pixels(encoder, img) for img in images])
    assert np.array_equal(encoder.accumulate(images), expected)


def test_levels_are_order_preserving(memory: ItemMemory) -> None:
    """Distance from level 0 must grow monotonically — that is 'thermometer'.

    Independent random level vectors would put every pair at ~D/2, making
    intensity 3 and 4 as unrelated as 3 and 15, which discards exactly the
    ordering the encoding is chosen for (DEVIATIONS GAP-1).
    """
    encoder = PixelThermometerEncoder(memory, n_positions=16, n_levels=16)
    levels = encoder._build_levels()
    distances = [int(hamming(levels[0], levels[q])) for q in range(16)]
    assert distances == sorted(distances)
    assert distances[0] == 0
    assert distances[1] > 0
    # Extremes approximately orthogonal: D/2 within one step's worth.
    assert abs(distances[-1] - D / 2) <= D / (2 * 15) + 1


def test_adjacent_levels_are_equidistant(memory: ItemMemory) -> None:
    encoder = PixelThermometerEncoder(memory, n_positions=16, n_levels=16)
    levels = encoder._build_levels()
    steps = {int(hamming(levels[q], levels[q + 1])) for q in range(15)}
    assert len(steps) == 1


def test_quantisation_is_fixed_arithmetic(memory: ItemMemory) -> None:
    """Level comes from the value alone — no statistic, so no leak (GAP-2)."""
    encoder = PixelThermometerEncoder(memory, n_positions=4, n_levels=16)
    assert encoder.quantise(np.array([[0, 15, 16, 255]]))[0].tolist() == [0, 0, 1, 15]
    bright = encoder.quantise(np.full((1, 4), 200, dtype=np.uint8))
    dark = encoder.quantise(np.zeros((1, 4), dtype=np.uint8))
    assert bright.max() == 12 and dark.max() == 0


def test_similar_images_encode_similarly(memory: ItemMemory) -> None:
    encoder = PixelThermometerEncoder(memory, n_positions=64, n_levels=16)
    rng = np.random.default_rng(SEED)
    base = rng.integers(0, 256, size=64, dtype=np.uint8)
    nudged = np.clip(base.astype(np.int16) + 4, 0, 255).astype(np.uint8)
    other = rng.integers(0, 256, size=64, dtype=np.uint8)
    totals = encoder.accumulate(np.stack([base, nudged, other]))
    signs = np.sign(totals)
    assert float(np.mean(signs[0] == signs[1])) > float(np.mean(signs[0] == signs[2]))


def test_pixel_rejects_wrong_shape(memory: ItemMemory) -> None:
    encoder = PixelThermometerEncoder(memory, n_positions=64, n_levels=16)
    with pytest.raises(ValueError, match="expected images"):
        encoder.accumulate(np.zeros((3, 10), dtype=np.uint8))


def test_pixel_rejects_degenerate_configuration(memory: ItemMemory) -> None:
    with pytest.raises(ValueError, match="n_levels"):
        PixelThermometerEncoder(memory, n_positions=8, n_levels=1)


# ---------------------------------------------------------------------------
# The open tie decision
# ---------------------------------------------------------------------------

def test_accumulate_never_raises_on_ties(memory: ItemMemory) -> None:
    """Accumulation is always defined; only thresholding is open."""
    encoder = TrigramEncoder(memory)
    totals = encoder.accumulate(["an even number of trigrams here!!"])
    assert totals.shape == (1, D)


def test_encode_resolves_ties_and_is_deterministic(memory: ItemMemory) -> None:
    encoder = PixelThermometerEncoder(memory, n_positions=64, n_levels=16)
    images = np.random.default_rng(SEED).integers(0, 256, size=(4, 64), dtype=np.uint8)
    assert encoder.tie_report(images).total_tied_components > 0, \
        "expected ties from an even bundle"
    first = encoder.encode(images)
    assert first.shape == (4, D // 8)
    assert np.array_equal(first, encoder.encode(images))


def test_encoding_ties_are_keyed_on_sample_content(memory: ItemMemory) -> None:
    """Two samples must not be pushed together by a shared tie resolution.

    A shared tie vector would force agreement wherever both tie. Keying on
    each sample's own content leaves co-tied components independent.
    """
    encoder = PixelThermometerEncoder(memory, n_positions=64, n_levels=16)
    rng = np.random.default_rng(SEED)
    images = rng.integers(0, 256, size=(60, 64), dtype=np.uint8)
    totals = encoder.accumulate(images)
    packed = encoder.encode(images)
    bits = unpack_bits(packed, D)

    both_tie = (totals[:, None, :] == 0) & (totals[None, :, :] == 0)
    same = bits[:, None, :] == bits[None, :, :]
    off_diagonal = ~np.eye(len(images), dtype=bool)
    agreement = float(same[off_diagonal & both_tie.any(axis=2)][
        both_tie[off_diagonal & both_tie.any(axis=2)]].mean())
    assert abs(agreement - 0.5) < 0.1, (
        f"co-tied components agree {agreement:.3f} of the time; a shared tie "
        f"resolution would show 1.0"
    )


def test_encoding_ties_depend_on_the_seed() -> None:
    images = np.random.default_rng(SEED).integers(0, 256, size=(4, 64), dtype=np.uint8)
    first = PixelThermometerEncoder(ItemMemory(1, D), n_positions=64,
                                    n_levels=16).encode(images)
    second = PixelThermometerEncoder(ItemMemory(2, D), n_positions=64,
                                     n_levels=16).encode(images)
    assert not np.array_equal(first, second)


def test_encoding_is_batch_invariant(memory: ItemMemory) -> None:
    """Splitting a batch may not change any encoded vector.

    The streaming runner relies on this; a tie rule keyed on batch position
    would break it silently.
    """
    encoder = PixelThermometerEncoder(memory, n_positions=64, n_levels=16)
    images = np.random.default_rng(SEED).integers(0, 256, size=(9, 64), dtype=np.uint8)
    at_once = encoder.encode(images)
    split = np.concatenate([encoder.encode(images[:2]), encoder.encode(images[2:7]),
                            encoder.encode(images[7:])])
    assert np.array_equal(at_once, split)


def test_tie_report_counts_match_the_accumulator(memory: ItemMemory) -> None:
    encoder = PixelThermometerEncoder(memory, n_positions=64, n_levels=16)
    images = np.random.default_rng(SEED).integers(0, 256, size=(6, 64), dtype=np.uint8)
    totals = encoder.accumulate(images)
    report = encoder.tie_report(images)
    assert report.n_samples == 6
    assert report.total_tied_components == int((totals == 0).sum())
    assert report.max_tied_in_one_sample == int((totals == 0).sum(axis=1).max())
    assert 0.0 <= report.fraction_of_samples <= 1.0


def test_encode_without_ties_is_a_plain_sign(memory: ItemMemory) -> None:
    """With no tie, the result is exactly the sign of the accumulator."""
    encoder = PixelThermometerEncoder(memory, n_positions=63, n_levels=16)
    rng = np.random.default_rng(SEED)
    for _ in range(20):
        image = rng.integers(0, 256, size=(1, 63), dtype=np.uint8)
        if encoder.tie_report(image).total_tied_components == 0:
            packed, signed = encoder.encode_signed(image)
            assert packed.shape == (1, D // 8)
            assert signed.shape == (1, D)
            assert set(np.unique(signed).tolist()) <= {-1, 1}
            expected = np.sign(encoder.accumulate(image))
            assert np.array_equal(signed, expected.astype(np.int8))
            return
    pytest.fail("no tie-free sample found; adjust the fixture")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_build_encoder_dispatches_by_task(memory: ItemMemory) -> None:
    assert isinstance(build_encoder("wili", memory), TrigramEncoder)
    assert isinstance(build_encoder("mnist", memory), PixelThermometerEncoder)
    with pytest.raises(ValueError, match="no encoder registered"):
        build_encoder("nonexistent", memory)


def test_mnist_encoder_defaults_to_the_mnist_geometry(memory: ItemMemory) -> None:
    encoder = build_encoder("mnist", memory)
    assert encoder.n_positions == 784
    assert encoder.n_levels == 16, "D4 records Q=16 thermometer levels"
