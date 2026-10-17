"""Sela-2: the NumPy forward pass of the desktop app (engramm/lm/sela.py, sela-npz-2) against the torch model it is
trained as (experiments/sela2_model.py), on a tiny random model with every part switched on (x0 skip, smear, value
embeddings with gates, backout, soft-cap 15); incremental decoding with the growing cache equals the full pass;
the int8 file stays close to float32; the losses (fused and chunked, with ignored targets) agree."""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from engramm.lm.sela import FORMAT2, KVCache2, Sela2Model, load_model, stream  # noqa: E402
from experiments.sela2_model import (Sela2, Sela2Config, chunked_loss, export_npz, fused_loss,  # noqa: E402
                                     npz_arrays)


def _tiny(seed: int = 0, ve_tables: int = 1, layers: int = 4) -> Sela2:
    torch.manual_seed(seed)
    cfg = Sela2Config(d=64, layers=layers, heads=2, ctx=96, vocab=300, ve_tables=ve_tables)
    m = Sela2(cfg)
    with torch.no_grad():                    # leave the zero / neutral initialisation: every path must carry signal
        for name, p in m.named_parameters():
            if name in ("resid", "x0"):
                p.add_(0.3 * torch.randn_like(p))
            elif name in ("smear_lambda", "backout"):
                p.fill_(0.4)
            else:
                p.add_(0.05 * torch.randn_like(p))
    return m.eval()


def _np_model(m: Sela2, quant: str = "fp32", tmp_path=None) -> Sela2Model:
    path = export_npz(m, tmp_path / f"m_{quant}.npz", meta={"test": True}, quant=quant)
    return load_model(path)


def _ids(n: int, vocab: int = 300, seed: int = 1) -> list[int]:
    rng = np.random.default_rng(seed)
    return [0] + [int(i) for i in rng.integers(3, vocab, n - 1)]          # one document, opened by <|eos|>


def test_numpy_matches_torch(tmp_path):
    m = _tiny()
    nm = _np_model(m, "fp32", tmp_path)
    assert isinstance(nm, Sela2Model)
    ids = _ids(40)
    with torch.no_grad():
        ref = m(torch.tensor([ids]))[0].numpy()
    got = nm.forward(ids, KVCache2(nm.cfg))
    assert got.dtype == np.float32
    assert np.abs(got - ref).max() < 1e-3, np.abs(got - ref).max()


def test_all_parts_matter(tmp_path):
    """Switching off any one addition changes the NumPy logits (so the parity test above covers it)."""
    m = _tiny()
    ids = _ids(30)
    base = _np_model(m, "fp32", tmp_path).forward(ids, KVCache2(m.cfg))
    for name in ("smear_lambda", "backout"):
        m2 = _tiny()
        with torch.no_grad():
            getattr(m2, name).zero_()
        alt = _np_model(m2, "fp32", tmp_path).forward(ids, KVCache2(m2.cfg))
        assert np.abs(alt - base).max() > 1e-3, name
    m3 = _tiny()
    with torch.no_grad():
        m3.ve[0].weight.zero_()
    alt = _np_model(m3, "fp32", tmp_path).forward(ids, KVCache2(m3.cfg))
    assert np.abs(alt - base).max() > 1e-3


def test_cache_equals_full_pass(tmp_path):
    m = _tiny(ve_tables=2)
    nm = _np_model(m, "fp32", tmp_path)
    ids = _ids(70)
    full = nm.forward(ids, KVCache2(nm.cfg))
    cache = KVCache2(nm.cfg, chunk=16)                # several regrowths
    rows = [nm.forward(ids[:5], cache)]
    for t in ids[5:]:
        rows.append(nm.forward([t], cache, last_only=True))
    step = np.concatenate(rows)
    assert cache.n == len(ids) and cache.k.shape[2] >= len(ids)
    assert np.abs(step - full).max() < 1e-4


def test_overflow_and_stream(tmp_path):
    m = _tiny()
    nm = _np_model(m, "fp32", tmp_path)
    with pytest.raises(ValueError):
        nm.forward(list(range(3, 100)), KVCache2(nm.cfg))
    a = list(stream(nm, _ids(10), 150, seed=3, stop=(0, 2)))    # runs past the context (rebuilds it)
    b = list(stream(nm, _ids(10), 150, seed=3, stop=(0, 2)))
    assert a == b and all(t not in (0, 2) for t in a)


def test_int8_close_to_float(tmp_path):
    m = _tiny()
    f = _np_model(m, "fp32", tmp_path)
    q = _np_model(m, "int8", tmp_path)
    arrays = npz_arrays(m, "int8")
    assert arrays["b0.qkv_t.q8"].dtype == np.int8 and arrays["emb.q8"].dtype == np.int8
    ids = _ids(40)
    a, b = f.forward(ids, KVCache2(f.cfg)), q.forward(ids, KVCache2(q.cfg))
    pa = np.exp(a - a.max(1, keepdims=True)); pa /= pa.sum(1, keepdims=True)
    lb = b - b.max(1, keepdims=True); lb -= np.log(np.exp(lb).sum(1, keepdims=True))
    la = np.log(pa)
    kl = float((pa * (la - lb)).sum(1).mean())
    assert kl < 0.01, kl
    assert (a.argmax(1) == b.argmax(1)).mean() >= 0.9


def test_header_and_format_checks(tmp_path):
    m = _tiny()
    path = export_npz(m, tmp_path / "x.npz", meta={"tokens": 5})
    with np.load(path) as z:
        import json
        h = json.loads(bytes(z["header"]).decode())
    assert h["format"] == FORMAT2 and h["cfg"]["softcap"] == 15.0 and h["meta"] == {"tokens": 5}
    bad = tmp_path / "bad.npz"
    np.savez(bad, header=np.frombuffer(b'{"format": "nope"}', dtype=np.uint8))
    with pytest.raises(ValueError):
        load_model(bad)


def test_losses_agree_with_ignored_targets():
    torch.manual_seed(0)
    h = torch.randn(37, 16, requires_grad=True)
    W = torch.randn(50, 16, requires_grad=True)
    tgt = torch.randint(0, 50, (37,))
    tgt[::3] = -1
    a = fused_loss(h, W, tgt, 15.0, bf16=False)
    ga = torch.autograd.grad(a, (h, W))
    b = chunked_loss(h, W, tgt, 15.0, bf16=False, chunk=8)
    gb = torch.autograd.grad(b, (h, W))
    assert abs(float(a.detach()) - float(b.detach())) < 1e-5
    for x, y in zip(ga, gb):
        assert float((x - y).abs().max()) < 1e-5
    # every target ignored: a zero loss, no NaN
    none = torch.full((37,), -1)
    assert float(chunked_loss(h, W, none, 15.0, bf16=False, chunk=8).detach()) == 0.0


def test_optimizer_groups_schedules_and_resume():
    from experiments.sela2_optim import (lr_mult, make_optimizer, muon_momentum, muon_weight_decay, newton_ok,
                                         set_schedule)
    m = _tiny()
    m.train()
    opt = make_optimizer(m, weight_decay=0.1)
    kinds = {g["kind"] for g in opt.param_groups}
    assert kinds == {"adamw", "muon"}
    muon = [p for g in opt.param_groups if g["kind"] == "muon" for p in g["params"]]
    assert all(p.ndim == 2 for p in muon) and all(p is not m.head.weight for p in muon)
    ids = torch.tensor([_ids(48, seed=s) for s in range(4)])
    losses = []
    for step in range(30):
        set_schedule(opt, step / 30, step, 0.1, warmup=3)
        out = m(ids[:, :-1])
        loss = torch.nn.functional.cross_entropy(out.reshape(-1, out.shape[-1]), ids[:, 1:].reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        losses.append(float(loss.detach()))
    assert losses[-1] < losses[0] - 0.5, losses
    # resume: a fresh optimiser loaded from the state dict makes the identical next update
    import copy
    m2 = copy.deepcopy(m)
    opt2 = make_optimizer(m2, weight_decay=0.1)
    opt2.load_state_dict(copy.deepcopy(opt.state_dict()))
    for mm, oo in ((m, opt), (m2, opt2)):
        set_schedule(oo, 0.9, 31, 0.1, warmup=3)
        out = mm(ids[:, :-1])
        loss = torch.nn.functional.cross_entropy(out.reshape(-1, out.shape[-1]), ids[:, 1:].reshape(-1))
        oo.zero_grad(set_to_none=True)
        loss.backward()
        oo.step()
    for a, b in zip(m.parameters(), m2.parameters()):
        assert torch.equal(a, b)
    # schedules
    assert lr_mult(0.0, 0, warmup=40) == 1 / 40 and lr_mult(0.2, 100) == 1.0 and abs(lr_mult(1.0, 9999) - 0.05) < 1e-9
    assert muon_momentum(0.1, 0) == 0.85 and muon_momentum(0.2, 500) == 0.97 and abs(muon_momentum(1.0, 9999) - 0.9) < 1e-9
    assert abs(muon_weight_decay(2 ** 19, 3_000_000_000) - 0.28 * 1321205760 / 3e9) < 1e-6
    assert muon_weight_decay(2 ** 19, 10_000_000) == 0.28
    assert newton_ok()
