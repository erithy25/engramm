"""Corruption code — validated before the study runs (PREREG_ROBUSTNESS §9, §9.1).

Three groups:

1. The mechanics: the draw, the flip, the byte layouts and numeric formats do
   exactly what §3.4 and §4 say, bit for bit.
2. The §9 validation: at p = 50 % every system and format must fall to
   chance (mean R ≤ 0.05, §9.1). Checked here on synthetic tasks, so a bug
   in the corruption code shows up before a single study number exists.
3. Determinism: the same seed gives the same result in fresh processes
   under different ``PYTHONHASHSEED`` values.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from engramm.core import ItemMemory
from engramm.corruption import (
    LEVELS_PERCENT,
    SignTensor,
    corrupt,
    corruption_positions,
    dequantize_int8,
    flip_bits,
    flip_count,
    from_buffer,
    quantize_int8,
    retention,
    signs_from_buffer,
    signs_to_buffer,
    to_buffer,
)
from engramm.encoders import PixelThermometerEncoder, TrigramEncoder
from engramm.memory import Engramm, FusionConfig
from experiments.robustness import (
    Dense,
    encoder_tables,
    fit_lr,
    fit_mlp,
    float32_conditions,
    int8_conditions,
    label_order,
    prototype_predict,
    sign_conditions,
    sweep,
    tfidf,
    with_tables,
)

REPO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Mechanics
# ---------------------------------------------------------------------------

def test_levels_are_the_registered_ones():
    assert LEVELS_PERCENT == (0, 1, 5, 10, 25, 50)


def test_flip_count_is_integer_floor():
    assert flip_count(100_000, 1) == 1_000
    assert flip_count(7, 50) == 3
    assert flip_count(3, 25) == 0
    assert flip_count(10**12 + 3, 5) == (10**12 + 3) * 5 // 100
    with pytest.raises(ValueError):
        flip_count(10, 101)


def test_positions_are_unique_in_range_and_seeded_by_seed_and_level():
    a = corruption_positions(10_000, 25, seed=42)
    assert a.size == 2_500 and np.unique(a).size == 2_500
    assert a.min() >= 0 and a.max() < 10_000
    assert np.array_equal(a, corruption_positions(10_000, 25, seed=42))
    assert not np.array_equal(np.sort(a)[:100], np.sort(corruption_positions(10_000, 25, 7))[:100])
    assert corruption_positions(10_000, 0, seed=42).size == 0
    # the stream is (seed, percent): another level is another draw
    ten = corruption_positions(10_000, 10, seed=42)
    assert not set(ten.tolist()) <= set(a.tolist())


def test_flip_bits_flips_exactly_the_listed_bits_lsb_first():
    buffer = np.zeros(4, dtype=np.uint8)
    out = flip_bits(buffer, np.array([0, 9, 31]))
    assert out.tolist() == [1, 2, 0, 128]
    assert buffer.tolist() == [0, 0, 0, 0]          # input untouched
    assert np.array_equal(flip_bits(out, np.array([0, 9, 31])), buffer)


def test_corrupt_changes_the_hamming_weight_by_the_flip_count():
    rng = np.random.default_rng(0)
    buffer = rng.integers(0, 256, size=1_000, dtype=np.uint8)
    for percent in LEVELS_PERCENT:
        out = corrupt(buffer, percent, seed=3)
        changed = int(np.unpackbits(np.bitwise_xor(out, buffer)).sum())
        assert changed == flip_count(8_000, percent)


def test_padding_bits_are_never_touched():
    signs = [SignTensor(np.ones((3, 3), dtype=bool), np.ones(3, dtype=np.float32))]
    buffer, n_bits = signs_to_buffer(signs)
    assert n_bits == 9 and buffer.size == 2
    out = corrupt(buffer, 50, seed=1, n_bits=n_bits)
    assert (out[1] & 0xFE) == (buffer[1] & 0xFE)    # bits 9..15 are padding
    with pytest.raises(ValueError):
        flip_bits(buffer, np.array([9]), n_bits=9)


def test_buffer_layout_round_trip_with_mixed_dtypes():
    tensors = [np.arange(6, dtype=np.int8).reshape(2, 3) - 3,
               np.linspace(-1, 1, 5, dtype=np.float32),
               np.array([[7, 250]], dtype=np.uint8)]
    buffer, layout = to_buffer(tensors)
    assert buffer.size == 6 + 20 + 2
    back = from_buffer(buffer, layout)
    for a, b in zip(tensors, back):
        assert a.dtype == b.dtype and np.array_equal(a, b)
        assert b.flags.writeable


def test_int8_quantisation_is_per_tensor_symmetric():
    w = np.array([[-0.5, 0.25], [1.0, 0.0]])
    q, s = quantize_int8(w)
    assert s == pytest.approx(1.0 / 127)
    assert q.dtype == np.int8 and q.max() == 127 and q.min() == -64
    assert np.allclose(dequantize_int8(q, s), w, atol=s / 2)
    zeros, scale = quantize_int8(np.zeros(3))
    assert scale == 1.0 and not zeros.any()
    # a flipped value of -128 dequantises instead of failing
    assert dequantize_int8(np.array([-128], dtype=np.int8), 0.5)[0] == -64.0


def test_sign_tensor_scales_per_output_unit():
    w = np.array([[1.0, -2.0], [-3.0, 4.0]])
    t = SignTensor.from_weights(w)
    assert t.alpha.tolist() == [2.0, 3.0]
    assert t.weights().tolist() == [[2.0, -3.0], [-2.0, 3.0]]
    buffer, n_bits = signs_to_buffer([t])
    (back,) = signs_from_buffer(buffer, n_bits, [t])
    assert np.array_equal(back.signs, t.signs) and np.array_equal(back.alpha, t.alpha)


def test_retention_is_chance_corrected_and_clipped():
    assert retention(0.9, 0.9, 0.1) == 1.0
    assert retention(0.5, 0.9, 0.1) == pytest.approx(0.5)
    assert retention(0.05, 0.9, 0.1) == 0.0
    assert retention(0.95, 0.9, 0.1) == 1.0
    assert np.isnan(retention(0.1, 0.1, 0.1))


def test_dense_forward_survives_nan_and_inf():
    w = np.array([[np.nan, 1.0], [np.inf, -np.inf]], dtype=np.float32)
    out = Dense([w], [np.zeros(2, dtype=np.float32)]).predict(np.ones((3, 2), np.float32))
    assert out.shape == (3,)


# ---------------------------------------------------------------------------
# ENGRAMM pieces of the harness
# ---------------------------------------------------------------------------

def _synthetic_hdc(dimension: int = 1_024, n_classes: int = 10, per_class: int = 60,
                   noise: float = 0.3, seed: int = 0):
    rng = np.random.default_rng(seed)
    centres = rng.integers(0, 2, size=(n_classes, dimension), dtype=np.uint8)

    def draw(n):
        y = np.repeat(np.arange(n_classes), n)
        bits = centres[y] ^ (rng.random((y.size, dimension)) < noise).astype(np.uint8)
        return np.packbits(bits, axis=1), y

    x_train, y_train = draw(per_class)
    x_test, y_test = draw(per_class)
    labels = [f"c{i:02d}" for i in range(n_classes)]
    return x_train, y_train, x_test, y_test, labels


def _trained_engramm(dimension: int = 1_024):
    x_train, y_train, x_test, y_test, labels = _synthetic_hdc(dimension)
    model = Engramm(dimension, 5, FusionConfig(lambda_e=0.0))
    names = [labels[i] for i in y_train]
    positions = model.learn(x_train, names)
    model.refine(x_train, names, 2, rng=np.random.default_rng(5),
                 episode_positions=positions)
    return model, x_test, y_test


def test_prototype_predict_matches_engramm_predict():
    model, x_test, _ = _trained_engramm()
    order = label_order(model.labels)
    ours = prototype_predict(x_test, model.prototypes.P, order, model.dimension, block=37)
    assert np.array_equal(ours, model.predict(x_test))


def test_prototype_predict_breaks_ties_by_label():
    dimension = 64
    rng = np.random.default_rng(1)
    row = rng.integers(0, 256, size=(1, dimension // 8), dtype=np.uint8)
    prototypes = np.vstack([row, row, row])
    labels = ["zeta", "alpha", "mid"]
    order = label_order(labels)
    queries = rng.integers(0, 256, size=(20, dimension // 8), dtype=np.uint8)
    assert set(prototype_predict(queries, prototypes, order, dimension).tolist()) == {1}


@pytest.mark.parametrize("encoder_cls", [TrigramEncoder, PixelThermometerEncoder])
def test_with_tables_reproduces_the_encoder_and_corruption_reaches_the_encoding(encoder_cls):
    dimension = 512
    encoder = encoder_cls(ItemMemory(11, dimension))
    if encoder_cls is TrigramEncoder:
        samples = ["hello world", "grüße aus köln", "abcabcabc"]
    else:
        samples = np.random.default_rng(2).integers(0, 256, size=(4, 784), dtype=np.uint8)
    tables = encoder_tables(encoder)
    same = with_tables(encoder, tables)
    assert np.array_equal(same.encode(samples), encoder.encode(samples))
    broken = with_tables(encoder, corrupt(tables.ravel(), 25, seed=3).reshape(tables.shape))
    assert not np.array_equal(broken.encode(samples), encoder.encode(samples))
    # the original encoder is not modified by building a corrupted copy
    assert np.array_equal(with_tables(encoder, tables).encode(samples), encoder.encode(samples))


def test_tfidf_rows_are_unit_length_and_empty_rows_stay_empty():
    from scipy import sparse
    counts = sparse.csr_matrix(np.array([[1, 0, 2], [0, 0, 0], [3, 1, 0]], dtype=np.float32))
    x = tfidf(counts, np.array([1.0, 2.0, 0.5]))
    norms = np.sqrt(np.asarray(x.multiply(x).sum(axis=1)).ravel())
    assert norms.tolist() == pytest.approx([1.0, 0.0, 1.0])


# ---------------------------------------------------------------------------
# 2. §9 validation: p = 50 % must reach chance for every system and format
# ---------------------------------------------------------------------------

def _gaussian_task(n_features: int = 40, n_classes: int = 10, per_class: int = 200,
                   seed: int = 0):
    rng = np.random.default_rng(seed)
    means = rng.normal(0.0, 1.0, size=(n_classes, n_features))
    y = np.repeat(np.arange(n_classes), per_class)
    x = (means[y] + rng.normal(0.0, 0.6, size=(y.size, n_features))).astype(np.float32)
    return x, y


def test_engramm_at_half_the_bits_flipped_is_at_chance():
    model, x_test, y_test = _trained_engramm()
    order = label_order(model.labels)
    P = model.prototypes.P
    to_dataset = np.array([int(label[1:]) for label in model.labels])

    def decode(buf):
        return to_dataset[prototype_predict(x_test, buf.reshape(P.shape), order,
                                            model.dimension)]

    rs = []
    for seed in range(5):
        result = sweep(P.ravel(), P.size * 8, decode, y_test, seed, 0.1,
                       P.shape[0] * model.dimension)
        assert result["R"]["0"] == 1.0 and result["acc"]["0"] > 0.9
        rs.append(result["R"]["50"])
    assert np.mean(rs) <= 0.05


@pytest.mark.parametrize("kind", ["lr", "mlp"])
def test_baselines_at_half_the_bits_flipped_are_at_chance_in_every_format(kind):
    x_train, y_train = _gaussian_task(seed=0)
    x_test, y_test = _gaussian_task(seed=0)[0][::2], _gaussian_task(seed=0)[1][::2]
    if kind == "lr":
        model, _ = fit_lr(x_train, y_train, 10)
    else:
        model, _ = fit_mlp(x_train, y_train, 10, hidden=16, epochs=30, seed=0)
    for conditions in (int8_conditions, float32_conditions, sign_conditions):
        rs = []
        for seed in range(5):
            result = conditions(model, x_test, y_test, seed, 0.1)
            assert result["acc"]["0"] > 0.5, conditions.__name__
            rs.append(result["R"]["50"])
        assert np.mean(rs) <= 0.05, (kind, conditions.__name__, rs)


def test_parameter_and_bit_counts_follow_the_format():
    x, y = _gaussian_task(n_features=8, per_class=30)
    model, _ = fit_lr(x, y, 10)
    assert model.n_params == 8 * 10 + 10
    assert int8_conditions(model, x, y, 0, 0.1)["n_bits"] == 8 * model.n_params
    assert float32_conditions(model, x, y, 0, 0.1)["n_bits"] == 32 * model.n_params
    signs = sign_conditions(model, x, y, 0, 0.1)
    assert signs["n_bits"] == 8 * 10 and signs["n_exact_scales_and_biases"] == 20


# ---------------------------------------------------------------------------
# 3. Determinism across processes and hash seeds
# ---------------------------------------------------------------------------

_PROBE = r"""
import json, hashlib, numpy as np
from tests.test_corruption import _gaussian_task, _trained_engramm
from experiments.robustness import fit_lr, int8_conditions, sign_conditions, sweep, prototype_predict, label_order
x, y = _gaussian_task(seed=3)
model, _ = fit_lr(x, y, 10)
out = {"int8": int8_conditions(model, x, y, 42, 0.1), "sign": sign_conditions(model, x, y, 42, 0.1)}
m, xt, yt = _trained_engramm()
P = m.prototypes.P
order = label_order(m.labels)
out["engramm"] = sweep(P.ravel(), P.size * 8, lambda b: prototype_predict(xt, b.reshape(P.shape), order, m.dimension), yt, 42, 0.1, P.size * 8)
print(hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest())
"""


def test_corruption_pipeline_is_deterministic_across_hash_seeds():
    digests = set()
    for hash_seed in ("0", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": str(REPO)}
        out = subprocess.run([sys.executable, "-c", _PROBE], cwd=REPO, env=env,
                             capture_output=True, text=True, check=True)
        digests.add(out.stdout.strip().splitlines()[-1])
    assert len(digests) == 1
