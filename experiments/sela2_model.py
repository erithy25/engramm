"""Sela-2: the from-scratch chat model of docs/PLAN_V5_FROM_SCRATCH.md §12 (training side, torch).

A decoder of GPT-3-Medium shape (24 layers, width 1,024, 8 heads of 128) with the additions that nanochat
(github.com/karpathy/nanochat, gpt.py) validated at this scale on one node:
- RMSNorm without weights (eps 1e-6) after the token embedding, before attention, before the feed-forward block and
  at the end; QK-norm, then interleaved rotary embeddings (theta 10,000, as Sela-1), q and k scaled by 1.2;
- ReLU² feed-forward (4 × width); attention-output and feed-forward-down projections start at zero;
- x0 skip: every block input is resid[i]·x + x0[i]·x0 (x0 = the normalised embedding), learned per layer;
- smear: the previous position's normalised embedding is mixed into the current one through a learned gate
  (cheap bigram information); never into a document start (<|eos|>), so a context opened by <|eos|> sees exactly
  what training saw;
- value embeddings: ``ve_tables`` lookup tables added to the values (gate 3·sigmoid of the first 12 input channels,
  per head); table t serves layer t and layer L - ve_tables + t (first and last layers);
- backout: the residual after the middle block, times a learned scalar, is subtracted before the final norm;
- untied output matrix, logits soft-capped at 15 (15 · tanh(z / 15)).
Separate q, k and v matrices so that Muon orthogonalises each one on its own (experiments/sela2_optim.py).

engramm/lm/sela.py runs the same forward pass in NumPy (format sela-npz-2, written by ``export_npz`` below); the
parity test is tests/test_sela2.py.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

EPS = 1e-6
EOS = 0


@dataclass
class Sela2Config:
    d: int = 1024
    layers: int = 24
    heads: int = 8
    ctx: int = 2048
    vocab: int = 49_152
    softcap: float = 15.0
    rope_theta: float = 10_000.0
    qk_gain: float = 1.2
    ve_tables: int = 2
    ve_gate_ch: int = 12
    smear_ch: int = 24
    special: dict = field(default_factory=lambda: {"eos": 0, "im_start": 1, "im_end": 2})

    @property
    def hd(self) -> int:
        return self.d // self.heads

    def ve_map(self) -> list[int]:
        """Per layer: the value-embedding table it adds, or -1."""
        m = [-1] * self.layers
        for t in range(self.ve_tables):
            m[t] = t
            m[self.layers - self.ve_tables + t] = t
        return m

    def check(self) -> None:
        if self.d % self.heads or self.hd % 2:
            raise ValueError(f"width {self.d} must split into {self.heads} heads of even size")
        if not 0 <= 2 * self.ve_tables <= self.layers:
            raise ValueError(f"{self.ve_tables} value-embedding tables need ≥ {2 * self.ve_tables} layers")
        if max(self.ve_gate_ch, self.smear_ch) > self.d:
            raise ValueError("gate channels exceed the width")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Sela2Config":
        return cls(**d)


def rms(x: torch.Tensor) -> torch.Tensor:
    return F.rms_norm(x, (x.size(-1),), eps=EPS)


def rope_tables(T: int, hd: int, theta: float):
    inv = 1.0 / theta ** (torch.arange(0, hd, 2, dtype=torch.float32) / hd)
    ang = torch.outer(torch.arange(T, dtype=torch.float32), inv)          # (T, hd/2)
    return ang.cos(), ang.sin()


def rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """Interleaved pairs (x[2i], x[2i+1]) rotated by position; x: (B, H, T, hd), cos/sin: (T, hd/2)."""
    x1, x2 = x[..., 0::2], x[..., 1::2]
    c, s = cos.to(x.dtype), sin.to(x.dtype)
    return torch.stack((x1 * c - x2 * s, x1 * s + x2 * c), dim=-1).flatten(-2)


def doc_mask(inp: torch.Tensor) -> torch.Tensor:
    """(B, 1, T, T) boolean: causal and within the same document (an <|eos|> opens a document)."""
    doc = torch.cumsum((inp == EOS).to(torch.int32), dim=1)
    same = doc[:, :, None] == doc[:, None, :]
    causal = torch.ones(inp.shape[1], inp.shape[1], dtype=torch.bool, device=inp.device).tril()
    return (same & causal)[:, None]


def dense_attend(mask: torch.Tensor):
    def attend(q, k, v):
        return F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
    return attend


class Block(nn.Module):
    def __init__(self, cfg: Sela2Config, has_ve: bool):
        super().__init__()
        d = cfg.d
        self.cfg = cfg
        self.q = nn.Linear(d, d, bias=False)
        self.k = nn.Linear(d, d, bias=False)
        self.v = nn.Linear(d, d, bias=False)
        self.proj = nn.Linear(d, d, bias=False)
        self.fc1 = nn.Linear(d, 4 * d, bias=False)
        self.fc2 = nn.Linear(4 * d, d, bias=False)
        self.ve_gate = nn.Linear(cfg.ve_gate_ch, cfg.heads, bias=False) if has_ve else None

    def forward(self, x, ve, cos, sin, attend):
        c = self.cfg
        B, T, _ = x.shape
        h = rms(x)
        q = self.q(h).view(B, T, c.heads, c.hd)
        k = self.k(h).view(B, T, c.heads, c.hd)
        v = self.v(h).view(B, T, c.heads, c.hd)
        if ve is not None:
            gate = 3 * torch.sigmoid(self.ve_gate(h[..., :c.ve_gate_ch]))             # (B, T, H)
            v = v + gate.unsqueeze(-1) * ve.view(B, T, c.heads, c.hd)
        q, k, v = (t.transpose(1, 2) for t in (q, k, v))                             # (B, H, T, hd)
        q = rope(rms(q), cos, sin) * c.qk_gain
        k = rope(rms(k), cos, sin) * c.qk_gain
        y = attend(q, k, v)
        x = x + self.proj(y.transpose(1, 2).reshape(B, T, c.d))
        return x + self.fc2(F.relu(self.fc1(rms(x))).square())


class Sela2(nn.Module):
    def __init__(self, cfg: Sela2Config):
        super().__init__()
        cfg.check()
        self.cfg = cfg
        self.emb = nn.Embedding(cfg.vocab, cfg.d)
        self.ve = nn.ModuleList([nn.Embedding(cfg.vocab, cfg.d) for _ in range(cfg.ve_tables)])
        vm = cfg.ve_map()
        self.blocks = nn.ModuleList([Block(cfg, vm[i] >= 0) for i in range(cfg.layers)])
        self.head = nn.Linear(cfg.d, cfg.vocab, bias=False)
        self.resid = nn.Parameter(torch.ones(cfg.layers))
        self.x0 = nn.Parameter(torch.zeros(cfg.layers))
        self.smear_gate = nn.Linear(cfg.smear_ch, 1, bias=False)
        self.smear_lambda = nn.Parameter(torch.zeros(1))
        self.backout = nn.Parameter(torch.zeros(1))
        cos, sin = rope_tables(cfg.ctx, cfg.hd, cfg.rope_theta)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)
        self.init_weights()

    @torch.no_grad()
    def init_weights(self) -> None:
        """nanochat's initialisation (gpt.py init_weights)."""
        c = self.cfg
        nn.init.normal_(self.emb.weight, std=0.8)
        nn.init.normal_(self.head.weight, std=0.001)
        s = 3 ** 0.5 * c.d ** -0.5                     # uniform with the standard deviation of N(0, 1/d)
        for b in self.blocks:
            for m in (b.q, b.k, b.v):
                nn.init.uniform_(m.weight, -s, s)
            nn.init.zeros_(b.proj.weight)
            nn.init.uniform_(b.fc1.weight, -0.4 * s, 0.4 * s)
            nn.init.zeros_(b.fc2.weight)
            if b.ve_gate is not None:
                nn.init.uniform_(b.ve_gate.weight, 0.0, 0.02)
        L = c.layers
        for i in range(L):
            self.resid[i] = 1.15 - 0.10 * i / max(L - 1, 1)
            self.x0[i] = 0.20 - 0.15 * i / max(L - 1, 1)
        for t in self.ve:
            nn.init.uniform_(t.weight, -s, s)
        nn.init.uniform_(self.smear_gate.weight, 0.0, 0.02)
        self.smear_lambda.zero_()
        self.backout.fill_(0.2)

    def hidden(self, idx: torch.Tensor, attend) -> torch.Tensor:
        """Final normalised hidden states (B, T, d); ``attend(q, k, v)`` is the masked attention."""
        c = self.cfg
        T = idx.shape[1]
        cos, sin = self.cos[:T], self.sin[:T]
        x = rms(self.emb(idx))
        if T > 1:
            gate = self.smear_lambda * torch.sigmoid(self.smear_gate(x[:, 1:, :c.smear_ch]))
            gate = gate * (idx[:, 1:] != EOS).unsqueeze(-1).to(gate.dtype)
            x = torch.cat([x[:, :1], x[:, 1:] + gate * x[:, :-1]], dim=1)
        x0 = x
        vm = c.ve_map()
        mid = c.layers // 2
        xb = None
        for i, blk in enumerate(self.blocks):
            x = self.resid[i] * x + self.x0[i] * x0
            ve = self.ve[vm[i]](idx) if vm[i] >= 0 else None
            x = blk(x, ve, cos, sin, attend)
            if i == mid:
                xb = x
        if xb is not None:
            x = x - self.backout * xb
        return rms(x)

    def logits(self, h: torch.Tensor) -> torch.Tensor:
        z = h.float() @ self.head.weight.float().T
        return self.cfg.softcap * torch.tanh(z / self.cfg.softcap)

    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        """Soft-capped logits (B, T, V) with causal, per-document attention (dense mask; for tests and CPU)."""
        return self.logits(self.hidden(idx, dense_attend(doc_mask(idx))))

    def param_counts(self) -> dict:
        blocks = sum(p.numel() for p in self.blocks.parameters())
        return {"blocks": blocks, "head": self.head.weight.numel(), "emb": self.emb.weight.numel(),
                "ve": sum(t.weight.numel() for t in self.ve),
                "scalars": self.resid.numel() + self.x0.numel() + self.smear_gate.weight.numel() + 2,
                "per_token": blocks + self.head.weight.numel(),
                "total": sum(p.numel() for p in self.parameters())}


# ---------------------------------------------------------------------------
# soft-capped cross-entropy; targets < 0 are ignored (SFT: loss only on the assistant's tokens)
# ---------------------------------------------------------------------------

class ChunkedSoftcapCE(torch.autograd.Function):
    """Mean soft-capped cross-entropy over the valid targets without the (N, V) logits in memory: the logits of
    ``chunk`` rows at a time, gradients computed in the same pass."""

    @staticmethod
    def forward(ctx, h, W, tgt, chunk: int, bf16: bool, cap: float):
        N, dev = h.shape[0], h.device
        cdt = torch.bfloat16 if bf16 else torch.float32
        Wc, hc = W.to(cdt), h.to(cdt)
        valid = tgt >= 0
        n = max(1, int(valid.sum()))
        dh = torch.zeros(h.shape, dtype=torch.float32, device=dev)
        dW = torch.zeros(W.shape, dtype=torch.float32, device=dev)
        total = torch.zeros((), dtype=torch.float64, device=dev)
        for s in range(0, N, chunk):
            e = min(N, s + chunk)
            vs = valid[s:e]
            if not bool(vs.any()):
                continue
            ts = tgt[s:e].clamp_min(0)
            t = torch.tanh((hc[s:e] @ Wc.T).float() / cap)
            c = t * cap
            lse = torch.logsumexp(c, dim=1)
            row = (lse - c.gather(1, ts[:, None]).squeeze(1)) * vs
            total += row.sum(dtype=torch.float64)
            g = c.sub_(lse[:, None]).exp_()
            g[torch.arange(e - s, device=dev), ts] -= 1.0
            g.mul_(1.0 - t.square_()).mul_(vs[:, None].float() / n)
            gc = g.to(cdt)
            dh[s:e] = (gc @ Wc).float()
            dW += (gc.T @ hc[s:e]).float()
        ctx.save_for_backward(dh, dW)
        ctx.h_dtype = h.dtype
        return (total / n).float()

    @staticmethod
    def backward(ctx, gout):
        dh, dW = ctx.saved_tensors
        return (dh * gout).to(ctx.h_dtype), dW * gout, None, None, None, None


def chunked_loss(h, W, tgt, cap: float, bf16: bool, chunk: int = 4096):
    return ChunkedSoftcapCE.apply(h.reshape(-1, h.shape[-1]), W, tgt.reshape(-1), chunk, bf16, cap)


def fused_loss(h, W, tgt, cap: float, bf16: bool):
    """The same loss with ordinary autograd over the whole micro-batch (fused by torch.compile on the GPU)."""
    z = (h.to(torch.bfloat16) @ W.to(torch.bfloat16).T).float() if bf16 else h.float() @ W.float().T
    c = cap * torch.tanh(z / cap)
    return F.cross_entropy(c.reshape(-1, c.shape[-1]), tgt.reshape(-1), ignore_index=-1)


# ---------------------------------------------------------------------------
# export for the desktop app: engramm/lm/sela.py, format sela-npz-2
# ---------------------------------------------------------------------------

NPZ_FORMAT = "sela-npz-2"


def _q8_cols(w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """int8 per column of an (in, out) matrix: w ≈ q · scale[None, :]."""
    scale = np.maximum(np.abs(w).max(axis=0), 1e-12) / 127.0
    q = np.clip(np.rint(w / scale[None, :]), -127, 127).astype(np.int8)
    return q, scale.astype(np.float32)


def _q8_rows(w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """int8 per row of a lookup table (V, d): w ≈ q · scale[:, None]."""
    scale = np.maximum(np.abs(w).max(axis=1), 1e-12) / 127.0
    q = np.clip(np.rint(w / scale[:, None]), -127, 127).astype(np.int8)
    return q, scale.astype(np.float32)


def npz_arrays(model: Sela2, quant: str = "int8") -> dict[str, np.ndarray]:
    """The weights in the sela-npz-2 layout: matrices transposed to (in, out); q, k, v concatenated. ``quant``:
    'int8' (matrices per column, lookup tables per row; each array ``X`` stored as ``X.q8`` + ``X.scale``),
    'fp16' or 'fp32'."""
    sd = {k: v.detach().float().cpu().numpy() for k, v in model.state_dict().items()}
    c = model.cfg
    mats: dict[str, np.ndarray] = {"head_t": sd["head.weight"].T.copy()}
    rows: dict[str, np.ndarray] = {"emb": sd["emb.weight"]}
    for t in range(c.ve_tables):
        rows[f"ve{t}"] = sd[f"ve.{t}.weight"]
    for i in range(c.layers):
        p = f"blocks.{i}."
        mats[f"b{i}.qkv_t"] = np.concatenate([sd[p + "q.weight"].T, sd[p + "k.weight"].T, sd[p + "v.weight"].T], axis=1)
        mats[f"b{i}.proj_t"] = sd[p + "proj.weight"].T.copy()
        mats[f"b{i}.fc1_t"] = sd[p + "fc1.weight"].T.copy()
        mats[f"b{i}.fc2_t"] = sd[p + "fc2.weight"].T.copy()
    small = {"resid": sd["resid"], "x0": sd["x0"], "smear_gate_t": sd["smear_gate.weight"].T.copy(),
             "smear_lambda": sd["smear_lambda"], "backout": sd["backout"]}
    for i in range(c.layers):
        k = f"blocks.{i}.ve_gate.weight"
        if k in sd:
            small[f"b{i}.ve_gate_t"] = sd[k].T.copy()
    out: dict[str, np.ndarray] = {k: v.astype(np.float32) for k, v in small.items()}
    for group, qfn in ((mats, _q8_cols), (rows, _q8_rows)):
        for k, w in group.items():
            if quant == "int8":
                q, s = qfn(w)
                out[f"{k}.q8"], out[f"{k}.scale"] = q, s
            elif quant == "fp16":
                out[k] = w.astype(np.float16)
            elif quant == "fp32":
                out[k] = w.astype(np.float32)
            else:
                raise ValueError(f"unknown quantisation {quant!r}")
    return out


def export_npz(model: Sela2, path: str | Path, meta: dict | None = None, quant: str = "int8") -> Path:
    path = Path(path)
    arrays = npz_arrays(model, quant)
    header = {"format": NPZ_FORMAT, "cfg": model.cfg.to_dict(), "quant": quant, "meta": meta or {}}
    arrays["header"] = np.frombuffer(json.dumps(header).encode("utf-8"), dtype=np.uint8)
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez(tmp, **arrays)
    tmp.replace(path)
    return path


def load_checkpoint(path: str | Path, device="cpu") -> Sela2:
    """A model file written by experiments/sela2_train.py ({'model': state_dict, 'cfg': dict, ...})."""
    st = torch.load(path, map_location="cpu", weights_only=False)
    model = Sela2(Sela2Config.from_dict(st["cfg"]))
    model.load_state_dict({k: v.float() for k, v in st["model"].items()})
    return model.to(device)
