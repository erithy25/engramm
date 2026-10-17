"""engramm.lm.sela: the NumPy port of the Sela-1 transformer used by the desktop app.

Without torch: the KV cache gives the logits of one full pass, sampling is reproducible and stops at <|eos|>, the
weights file round-trips. With torch installed: the port equals experiments.v5_long.LongGPT on random weights.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from engramm.lm.sela import FORMAT, KVCache, SelaConfig, SelaModel, sample_next, stream


def _random_model(seed: int = 0, d: int = 32, layers: int = 2, heads: int = 4, ctx: int = 64, vocab: int = 97):
    rng = np.random.default_rng(seed)
    cfg = SelaConfig(d=d, layers=layers, heads=heads, ctx_max=ctx, vocab=vocab)
    w = {"emb": rng.normal(0, 0.5, (vocab, d)).astype(np.float32),
         "head_t": rng.normal(0, 0.5, (d, vocab)).astype(np.float32)}
    for i in range(layers):
        w[f"b{i}.qkv_t"] = rng.normal(0, 0.2, (d, 3 * d)).astype(np.float32)
        w[f"b{i}.proj_t"] = rng.normal(0, 0.2, (d, d)).astype(np.float32)
        w[f"b{i}.fc1_t"] = rng.normal(0, 0.2, (d, 4 * d)).astype(np.float32)
        w[f"b{i}.fc2_t"] = rng.normal(0, 0.2, (4 * d, d)).astype(np.float32)
    return SelaModel(cfg, w), w


def test_cache_equals_full_pass():
    m, _ = _random_model()
    ids = [0, 5, 9, 3, 77, 12, 40, 41, 2, 8]
    full = m.forward(ids, KVCache(m.cfg))
    cache = KVCache(m.cfg)
    parts = [m.forward(ids[:3], cache), m.forward(ids[3:4], cache), m.forward(ids[4:], cache)]
    assert cache.n == len(ids)
    assert np.abs(np.concatenate(parts) - full).max() < 1e-4
    assert np.all(np.abs(full) <= 30.0 + 1e-4)                    # soft cap


def test_context_overflow_is_refused():
    m, _ = _random_model(ctx=8)
    with pytest.raises(ValueError):
        m.forward(list(range(9)), KVCache(m.cfg))


def test_stream_is_reproducible_and_rebuilds_full_context():
    m, _ = _random_model(ctx=16)
    a = list(stream(m, [0, 1, 2], 40, seed=7))
    b = list(stream(m, [0, 1, 2], 40, seed=7))
    assert a == b                                                  # longer than the context: rebuilt, no error
    assert all(t != 0 for t in a)


def test_sampling_respects_top_p_and_eos():
    rng = np.random.default_rng(0)
    logits = np.full(10, -50.0)
    logits[3] = 10.0
    assert all(sample_next(logits, [], 0.9, 1.0, 1.0, rng) == 3 for _ in range(20))
    m, _ = _random_model()
    eos_first = np.full((1, m.cfg.vocab), -30.0, dtype=np.float32)
    eos_first[0, 0] = 30.0                                          # <|eos|> certain: generation ends at once

    def fake_forward(ids, cache):
        cache.n += len(ids)
        return np.repeat(eos_first, len(ids), axis=0)

    m.forward = fake_forward
    assert list(stream(m, [0, 4], 5, seed=1)) == []


def test_weights_file_round_trip(tmp_path):
    m, w = _random_model()
    header = {"format": FORMAT, "cfg": {"d": 32, "layers": 2, "heads": 4, "ctx_max": 64, "vocab": 97}, "meta": {}}
    path = tmp_path / "sela.npz"
    np.savez(path, header=np.frombuffer(json.dumps(header).encode(), dtype=np.uint8),
             **{k: v.astype(np.float16) for k, v in w.items()})
    m2 = SelaModel.load(path)
    ids = [0, 3, 4, 5]
    a, b = m.forward(ids, KVCache(m.cfg)), m2.forward(ids, KVCache(m2.cfg))
    assert np.abs(a - b).max() < 0.05                              # fp16 storage
    bad = tmp_path / "bad.npz"
    np.savez(bad, header=np.frombuffer(json.dumps({"format": "other"}).encode(), dtype=np.uint8))
    with pytest.raises(ValueError):
        SelaModel.load(bad)


def test_equals_torch_longgpt(tmp_path):
    torch = pytest.importorskip("torch")
    from experiments import v5_long as L
    from experiments.sela1_export import export
    torch.manual_seed(0)
    tm = L.LongGPT(d=64, layers=2, heads=4, ctx_max=128, bigram_rows=0)
    with torch.no_grad():
        for p in tm.parameters():
            p.normal_(0, 0.05)
    ck = tmp_path / "m.pt"
    torch.save({"model": tm.state_dict(), "meta": {"tokens": 1}, "cfg": tm.cfg}, ck)
    out = tmp_path / "m.npz"
    export(ck, out)
    nm = SelaModel.load(out)
    ids = [0, 11, 250, 3, 9999, 17, 42]
    with torch.no_grad():
        ref = tm(torch.tensor([ids]))[0][0].numpy()
    got = nm.forward(ids, KVCache(nm.cfg))
    assert np.abs(got - ref).max() < 0.02
    assert (got.argmax(-1) == ref.argmax(-1)).all()
