"""Sela-1 135M in pure NumPy: local text generation for the desktop app, no torch needed.

Sela-1 is the from-scratch transformer of docs/MODEL_CARD_SELA1.md. Training used experiments.v5_long.LongGPT; this
module reproduces its forward pass in float32:
- RMSNorm without weights (eps 1e-6) before attention, before the feed-forward block and at the end;
- rotary position embeddings on interleaved pairs (theta 10,000), applied after an RMSNorm of q and of k;
- causal multi-head attention, scale 1/sqrt(head size);
- ReLU² feed-forward (4 × width);
- untied output matrix, logits soft-capped at 30 (30 · tanh(z / 30)).
Every context starts with <|eos|> (id 0), as in training, and generating <|eos|> ends the text.

The weights file is written by experiments/sela1_export.py: an .npz with the configuration (JSON) and every matrix in
float16, already transposed to (in, out). Loading converts to float32 (about 540 MB of memory for Sela-1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

SOFTCAP = 30.0
EPS = 1e-6
ROPE_THETA = 10_000.0
EOS = 0
FORMAT = "sela-npz-1"


def _rms(x: np.ndarray) -> np.ndarray:
    return x / np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + EPS)


@dataclass
class SelaConfig:
    d: int
    layers: int
    heads: int
    ctx_max: int
    vocab: int

    @property
    def hd(self) -> int:
        return self.d // self.heads


class KVCache:
    """Keys and values of every layer for the positions seen so far (preallocated to the context length)."""

    def __init__(self, cfg: SelaConfig):
        shape = (cfg.layers, cfg.heads, cfg.ctx_max, cfg.hd)
        self.k = np.zeros(shape, dtype=np.float32)
        self.v = np.zeros(shape, dtype=np.float32)
        self.n = 0


class SelaModel:
    def __init__(self, cfg: SelaConfig, weights: dict[str, np.ndarray], meta: dict | None = None):
        self.cfg = cfg
        self.meta = meta or {}
        self.emb = weights["emb"]                                   # (V, d)
        self.head_t = weights["head_t"]                             # (d, V)
        self.blocks = [{k: weights[f"b{i}.{k}"] for k in ("qkv_t", "proj_t", "fc1_t", "fc2_t")}
                       for i in range(cfg.layers)]
        inv = 1.0 / ROPE_THETA ** (np.arange(0, cfg.hd, 2, dtype=np.float32) / cfg.hd)
        ang = np.outer(np.arange(cfg.ctx_max, dtype=np.float32), inv)
        self.cos, self.sin = np.cos(ang).astype(np.float32), np.sin(ang).astype(np.float32)
        self._check()

    def _check(self) -> None:
        c = self.cfg
        expect = {"emb": (c.vocab, c.d), "head_t": (c.d, c.vocab)}
        for name, shape in expect.items():
            if getattr(self, name).shape != shape:
                raise ValueError(f"Sela weights: {name} has shape {getattr(self, name).shape}, expected {shape}")
        for i, b in enumerate(self.blocks):
            for name, shape in (("qkv_t", (c.d, 3 * c.d)), ("proj_t", (c.d, c.d)),
                                ("fc1_t", (c.d, 4 * c.d)), ("fc2_t", (4 * c.d, c.d))):
                if b[name].shape != shape:
                    raise ValueError(f"Sela weights: block {i} {name} has shape {b[name].shape}, expected {shape}")

    @classmethod
    def load(cls, path: str | Path) -> "SelaModel":
        with np.load(Path(path), allow_pickle=False) as z:
            header = json.loads(bytes(z["header"]).decode("utf-8"))
            if header.get("format") != FORMAT:
                raise ValueError(f"{path}: not a Sela weights file (format {header.get('format')!r})")
            cfg = SelaConfig(**header["cfg"])
            weights = {k: z[k].astype(np.float32) for k in z.files if k != "header"}
        return cls(cfg, weights, header.get("meta"))

    def params(self) -> int:
        n = self.emb.size + self.head_t.size
        return int(n + sum(a.size for b in self.blocks for a in b.values()))

    # ------------------------------------------------------------------
    def _rope(self, x: np.ndarray, p0: int) -> np.ndarray:
        """x: (H, T, hd) at absolute positions p0 .. p0 + T - 1."""
        T = x.shape[1]
        c, s = self.cos[p0:p0 + T], self.sin[p0:p0 + T]
        x1, x2 = x[..., 0::2], x[..., 1::2]
        out = np.empty_like(x)
        out[..., 0::2] = x1 * c - x2 * s
        out[..., 1::2] = x1 * s + x2 * c
        return out

    def forward(self, ids: list[int], cache: KVCache) -> np.ndarray:
        """Logits (T, V) for ``ids`` appended after the cached positions; the cache is extended."""
        c = self.cfg
        T = len(ids)
        p0 = cache.n
        if T == 0:
            raise ValueError("forward needs at least one token")
        if p0 + T > c.ctx_max:
            raise ValueError(f"context overflow: {p0} cached + {T} new > {c.ctx_max}")
        x = self.emb[np.asarray(ids, dtype=np.int64)]                       # (T, d)
        scale = 1.0 / np.sqrt(c.hd)
        # causal mask of the new rows against all keys 0 .. p0 + T - 1
        mask = np.arange(p0 + T)[None, :] > (p0 + np.arange(T))[:, None]   # True = hidden
        for li, b in enumerate(self.blocks):
            qkv = _rms(x) @ b["qkv_t"]                                      # (T, 3d)
            q, k, v = (qkv[:, j * c.d:(j + 1) * c.d].reshape(T, c.heads, c.hd).transpose(1, 0, 2) for j in range(3))
            q = self._rope(_rms(q), p0)
            k = self._rope(_rms(k), p0)
            cache.k[li, :, p0:p0 + T] = k
            cache.v[li, :, p0:p0 + T] = v
            K, Vv = cache.k[li, :, :p0 + T], cache.v[li, :, :p0 + T]
            att = (q @ K.transpose(0, 2, 1)) * scale                        # (H, T, n)
            att = np.where(mask[None], -np.inf, att)
            att = att - att.max(axis=-1, keepdims=True)
            np.exp(att, out=att)
            att /= att.sum(axis=-1, keepdims=True)
            y = (att @ Vv).transpose(1, 0, 2).reshape(T, c.d)
            x = x + y @ b["proj_t"]
            h = np.maximum(_rms(x) @ b["fc1_t"], 0.0)
            x = x + (h * h) @ b["fc2_t"]
        cache.n = p0 + T
        z = _rms(x) @ self.head_t
        return SOFTCAP * np.tanh(z / SOFTCAP)


def sample_next(logits: np.ndarray, history: list[int], top_p: float, temperature: float, rep_penalty: float,
                rng: np.random.Generator) -> int:
    """The sampling of experiments/v5_generate.py: repetition penalty on seen tokens, temperature, nucleus (top-p)."""
    z = logits.astype(np.float64)
    if rep_penalty != 1.0 and history:
        seen = np.fromiter(set(history), dtype=np.int64)
        sel = z[seen]
        z[seen] = np.where(sel > 0, sel / rep_penalty, sel * rep_penalty)
    z = z / max(temperature, 1e-6)
    z -= z.max()
    p = np.exp(z)
    p /= p.sum()
    order = np.argsort(-p, kind="stable")
    sp = p[order]
    keep = np.cumsum(sp) - sp < top_p
    sp = sp * keep
    sp /= sp.sum()
    return int(order[rng.choice(len(sp), p=sp)])


def stream(model: SelaModel, ids: list[int], n: int, top_p: float = 0.9, temperature: float = 0.9,
           rep_penalty: float = 1.15, seed: int | None = None) -> Iterator[int]:
    """Yield up to ``n`` new token ids after ``ids`` (which should start with <|eos|>); stops at <|eos|>. When the
    context is full, it is rebuilt from the last half, as in experiments/v5_generate.py."""
    ctx = model.cfg.ctx_max
    rng = np.random.default_rng(seed)
    out = list(ids)
    cache, pending = KVCache(model.cfg), list(out[-ctx:])
    for _ in range(n):
        if cache.n + len(pending) > ctx:
            cache, pending = KVCache(model.cfg), list(out[-(ctx // 2):])
        logits = model.forward(pending, cache)[-1]
        nxt = sample_next(logits, out[-ctx:], top_p, temperature, rep_penalty, rng)
        if nxt == EOS:
            return
        out.append(nxt)
        pending = [nxt]
        yield nxt


class SelaGenerator:
    """Model + tokenizer, loaded once; turns a prompt into a continuation (text pieces as they are generated)."""

    def __init__(self, weights: str | Path, tokenizer=None):
        from engramm.lm.tokenizer import LMTokenizer
        self.model = SelaModel.load(weights)
        self.tok = tokenizer or LMTokenizer()
        if self.tok.vocab_size != self.model.cfg.vocab:
            raise ValueError(f"tokenizer has {self.tok.vocab_size} tokens, the model {self.model.cfg.vocab}")

    def prompt_ids(self, prompt: str) -> list[int]:
        ids = [int(i) for i in self.tok.encode(prompt)]
        keep = self.model.cfg.ctx_max - 1
        return [EOS] + ids[-keep:]

    def stream_text(self, prompt: str, max_tokens: int = 120, top_p: float = 0.9, temperature: float = 0.9,
                    rep_penalty: float = 1.15, seed: int | None = None) -> Iterator[str]:
        """Text pieces of the continuation; decoding the whole continuation each step keeps multi-byte characters
        intact (a piece is emitted only once it decodes cleanly)."""
        new: list[int] = []
        shown = ""
        for t in stream(self.model, self.prompt_ids(prompt), max_tokens, top_p, temperature, rep_penalty, seed):
            new.append(t)
            text = self.tok.decode(new)
            if text.endswith("�"):
                continue
            if len(text) > len(shown) and text.startswith(shown):
                yield text[len(shown):]
                shown = text
        text = self.tok.decode(new)
        if len(text) > len(shown) and text.startswith(shown):
            yield text[len(shown):]

    def complete(self, prompt: str, **kw) -> str:
        return "".join(self.stream_text(prompt, **kw))
