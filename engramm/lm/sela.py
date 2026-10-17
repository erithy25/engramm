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

Sela-2 (format sela-npz-2, experiments/sela2_model.py) is the chat model: 2,048 context, its own bilingual tokenizer
with ChatML tokens, x0 skip, smear, value embeddings, backout and soft-cap 15. ``Sela2Model`` runs that forward pass;
matrices stored as int8 per column are expanded to float32 at load (NumPy multiplies float32 fastest), the lookup
tables stay int8 in memory and only the rows used are expanded. ``load_model`` picks the class from the header.
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
FORMAT2 = "sela-npz-2"


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

    def new_cache(self) -> KVCache:
        return KVCache(self.cfg)

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

    def forward(self, ids: list[int], cache: KVCache, last_only: bool = False) -> np.ndarray:
        """Logits (T, V) for ``ids`` appended after the cached positions (``last_only``: only the last row, (1, V));
        the cache is extended."""
        c = self.cfg
        T = len(ids)
        p0 = cache.n
        if T == 0:
            raise ValueError("forward needs at least one token")
        if p0 + T > c.ctx_max:
            raise ValueError(f"context overflow: {p0} cached + {T} new > {c.ctx_max}")
        x = self.emb[np.asarray(ids, dtype=np.int64)]                       # (T, d)
        scale = c.hd ** -0.5                 # a Python float: a NumPy float64 scalar would turn everything float64
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
        if last_only:
            x = x[-1:]
        z = _rms(x) @ self.head_t
        return SOFTCAP * np.tanh(z / SOFTCAP)


# ---------------------------------------------------------------------------
# Sela-2 (format sela-npz-2)
# ---------------------------------------------------------------------------

@dataclass
class Sela2Config:
    d: int
    layers: int
    heads: int
    ctx: int
    vocab: int
    softcap: float
    rope_theta: float
    qk_gain: float
    ve_tables: int
    ve_gate_ch: int
    smear_ch: int
    special: dict

    @property
    def hd(self) -> int:
        return self.d // self.heads

    @property
    def ctx_max(self) -> int:
        return self.ctx

    def ve_map(self) -> list[int]:
        m = [-1] * self.layers
        for t in range(self.ve_tables):
            m[t] = t
            m[self.layers - self.ve_tables + t] = t
        return m


class KVCache2:
    """Keys and values per layer, grown in steps of ``chunk`` positions (a short chat does not allocate the whole
    context), plus the normalised embedding of the last position (for the smear of the next token)."""

    def __init__(self, cfg: Sela2Config, chunk: int = 256):
        self.cfg, self.chunk = cfg, chunk
        self.k = np.zeros((cfg.layers, cfg.heads, 0, cfg.hd), dtype=np.float32)
        self.v = np.zeros_like(self.k)
        self.n = 0
        self.prev: np.ndarray | None = None

    def reserve(self, total: int) -> None:
        cap = self.k.shape[2]
        if total <= cap:
            return
        new = min(self.cfg.ctx, max(total, cap + self.chunk, 2 * cap))
        new = min(self.cfg.ctx, -(-new // self.chunk) * self.chunk)
        shape = (self.cfg.layers, self.cfg.heads, new, self.cfg.hd)
        k, v = np.zeros(shape, dtype=np.float32), np.zeros(shape, dtype=np.float32)
        k[:, :, :cap], v[:, :, :cap] = self.k, self.v
        self.k, self.v = k, v


class _Lookup:
    """A (V, d) table kept as int8 rows with one float32 scale per row (or as plain float32)."""

    def __init__(self, q: np.ndarray, scale: np.ndarray | None):
        self.q, self.scale = q, scale

    @property
    def shape(self) -> tuple[int, int]:
        return self.q.shape

    def rows(self, ids: np.ndarray) -> np.ndarray:
        if self.scale is None:
            return self.q[ids].astype(np.float32)
        return self.q[ids].astype(np.float32) * self.scale[ids, None]


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


class Sela2Model:
    def __init__(self, cfg: Sela2Config, arrays: dict[str, np.ndarray], meta: dict | None = None,
                 tokenizer: dict | None = None):
        self.cfg = cfg
        self.meta = meta or {}
        self.tokenizer = tokenizer or {}
        L = cfg.layers

        def mat(name: str) -> np.ndarray:
            if f"{name}.q8" in arrays:
                return arrays[f"{name}.q8"].astype(np.float32) * arrays[f"{name}.scale"][None, :]
            return arrays[name].astype(np.float32)

        def lookup(name: str) -> _Lookup:
            if f"{name}.q8" in arrays:
                return _Lookup(arrays[f"{name}.q8"], arrays[f"{name}.scale"].astype(np.float32))
            return _Lookup(arrays[name].astype(np.float32), None)

        self.emb = lookup("emb")
        self.ve = [lookup(f"ve{t}") for t in range(cfg.ve_tables)]
        self.head_t = mat("head_t")
        self.blocks = []
        for i in range(L):
            b = {k: mat(f"b{i}.{k}") for k in ("qkv_t", "proj_t", "fc1_t", "fc2_t")}
            g = arrays.get(f"b{i}.ve_gate_t")
            b["ve_gate_t"] = None if g is None else g.astype(np.float32)
            self.blocks.append(b)
        self.resid = arrays["resid"].astype(np.float32)
        self.x0 = arrays["x0"].astype(np.float32)
        self.smear_gate_t = arrays["smear_gate_t"].astype(np.float32)
        self.smear_lambda = float(arrays["smear_lambda"].reshape(-1)[0])
        self.backout = float(arrays["backout"].reshape(-1)[0])
        inv = 1.0 / cfg.rope_theta ** (np.arange(0, cfg.hd, 2, dtype=np.float32) / cfg.hd)
        ang = np.outer(np.arange(cfg.ctx, dtype=np.float32), inv)
        self.cos, self.sin = np.cos(ang).astype(np.float32), np.sin(ang).astype(np.float32)
        self._check()

    def _check(self) -> None:
        c = self.cfg
        if self.emb.shape != (c.vocab, c.d) or self.head_t.shape != (c.d, c.vocab):
            raise ValueError(f"Sela-2 weights: embedding {self.emb.shape} / head {self.head_t.shape} do not match "
                             f"vocabulary {c.vocab} and width {c.d}")
        vm = c.ve_map()
        for i, b in enumerate(self.blocks):
            for name, shape in (("qkv_t", (c.d, 3 * c.d)), ("proj_t", (c.d, c.d)),
                                ("fc1_t", (c.d, 4 * c.d)), ("fc2_t", (4 * c.d, c.d))):
                if b[name].shape != shape:
                    raise ValueError(f"Sela-2 weights: block {i} {name} has shape {b[name].shape}, expected {shape}")
            if (vm[i] >= 0) != (b["ve_gate_t"] is not None):
                raise ValueError(f"Sela-2 weights: block {i} value-embedding gate does not match the layer map")
        if self.resid.shape != (c.layers,) or self.x0.shape != (c.layers,):
            raise ValueError("Sela-2 weights: per-layer scalars have the wrong length")

    @classmethod
    def from_arrays(cls, z) -> "Sela2Model":
        header = json.loads(bytes(z["header"]).decode("utf-8"))
        if header.get("format") != FORMAT2:
            raise ValueError(f"not a Sela-2 weights file (format {header.get('format')!r})")
        cfg = Sela2Config(**header["cfg"])
        arrays = {k: z[k] for k in z.files if k != "header"}
        return cls(cfg, arrays, header.get("meta"), header.get("tokenizer"))

    @classmethod
    def load(cls, path: str | Path) -> "Sela2Model":
        with np.load(Path(path), allow_pickle=False) as z:
            return cls.from_arrays(z)

    def params(self) -> int:
        n = self.emb.q.size + self.head_t.size + sum(t.q.size for t in self.ve)
        return int(n + sum(a.size for b in self.blocks for a in b.values() if a is not None))

    def new_cache(self) -> KVCache2:
        return KVCache2(self.cfg)

    def _rope(self, x: np.ndarray, p0: int) -> np.ndarray:
        T = x.shape[1]
        c, s = self.cos[p0:p0 + T], self.sin[p0:p0 + T]
        x1, x2 = x[..., 0::2], x[..., 1::2]
        out = np.empty_like(x)
        out[..., 0::2] = x1 * c - x2 * s
        out[..., 1::2] = x1 * s + x2 * c
        return out

    def forward(self, ids: list[int], cache: KVCache2, last_only: bool = False) -> np.ndarray:
        """Logits (T, V) for ``ids`` after the cached positions (``last_only``: (1, V)); the cache is extended."""
        c = self.cfg
        T = len(ids)
        p0 = cache.n
        if T == 0:
            raise ValueError("forward needs at least one token")
        if p0 + T > c.ctx:
            raise ValueError(f"context overflow: {p0} cached + {T} new > {c.ctx}")
        cache.reserve(p0 + T)
        idx = np.asarray(ids, dtype=np.int64)
        x = _rms(self.emb.rows(idx))                                        # (T, d)
        # smear: the previous position's normalised embedding through a gate, never into an <|eos|>
        prev = np.empty_like(x)
        has = np.ones(T, dtype=bool)
        prev[1:] = x[:-1]
        if cache.prev is None:
            prev[0] = 0.0
            has[0] = False
        else:
            prev[0] = cache.prev
        gate = self.smear_lambda * _sigmoid(x[:, :c.smear_ch] @ self.smear_gate_t)[:, 0]
        gate = gate * (has & (idx != EOS))
        cache.prev = x[-1].copy()
        x = x + gate[:, None].astype(np.float32) * prev
        x0 = x
        scale = c.hd ** -0.5                 # a Python float: a NumPy float64 scalar would turn everything float64
        mask = np.arange(p0 + T)[None, :] > (p0 + np.arange(T))[:, None]   # True = hidden
        vm = c.ve_map()
        mid = c.layers // 2
        xb = None
        for li, b in enumerate(self.blocks):
            x = float(self.resid[li]) * x + float(self.x0[li]) * x0
            h = _rms(x)
            qkv = h @ b["qkv_t"]                                            # (T, 3d)
            q, k, v = (qkv[:, j * c.d:(j + 1) * c.d].reshape(T, c.heads, c.hd) for j in range(3))
            if vm[li] >= 0:
                g = 3.0 * _sigmoid(h[:, :c.ve_gate_ch] @ b["ve_gate_t"])     # (T, H)
                v = v + g[:, :, None] * self.ve[vm[li]].rows(idx).reshape(T, c.heads, c.hd)
            q, k, v = (t.transpose(1, 0, 2) for t in (q, k, v))              # (H, T, hd)
            q = self._rope(_rms(q), p0) * c.qk_gain
            k = self._rope(_rms(k), p0) * c.qk_gain
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
            hh = np.maximum(_rms(x) @ b["fc1_t"], 0.0)
            x = x + (hh * hh) @ b["fc2_t"]
            if li == mid:
                xb = x
        cache.n = p0 + T
        if xb is not None:
            x = x - self.backout * xb
        if last_only:
            x = x[-1:]
        z = _rms(x) @ self.head_t
        return c.softcap * np.tanh(z / c.softcap)


def load_model(path: str | Path):
    """SelaModel (Sela-1, sela-npz-1) or Sela2Model (sela-npz-2), chosen by the file's header."""
    with np.load(Path(path), allow_pickle=False) as z:
        header = json.loads(bytes(z["header"]).decode("utf-8"))
        fmt = header.get("format")
        if fmt == FORMAT2:
            return Sela2Model.from_arrays(z)
    if fmt == FORMAT:
        return SelaModel.load(path)
    raise ValueError(f"{path}: not a Sela weights file (format {fmt!r})")


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


def stream(model, ids: list[int], n: int, top_p: float = 0.9, temperature: float = 0.9,
           rep_penalty: float = 1.15, seed: int | None = None, stop: tuple[int, ...] = (EOS,)) -> Iterator[int]:
    """Yield up to ``n`` new token ids after ``ids`` (which should start with <|eos|>); stops at any id in ``stop``
    (Sela-1: <|eos|>; Sela-2 chat: also <|im_end|>). When the context is full, it is rebuilt from the last half, as
    in experiments/v5_generate.py."""
    ctx = model.cfg.ctx_max
    rng = np.random.default_rng(seed)
    out = list(ids)
    cache, pending = model.new_cache(), list(out[-ctx:])
    for _ in range(n):
        if cache.n + len(pending) > ctx:
            cache, pending = model.new_cache(), list(out[-(ctx // 2):])
        logits = model.forward(pending, cache, last_only=True)[-1]
        nxt = sample_next(logits, out[-ctx:], top_p, temperature, rep_penalty, rng)
        if nxt in stop:
            return
        out.append(nxt)
        pending = [nxt]
        yield nxt


def tokenizer_for(model):
    """The pinned tokenizer a weights file names (Sela-2 header 'tokenizer': file in data/ + SHA-256); Sela-1 files
    use the LM-study tokenizer."""
    from engramm.lm.tokenizer import DEFAULT_PATH, LMTokenizer
    spec = getattr(model, "tokenizer", None) or {}
    if not spec:
        return LMTokenizer()
    path = DEFAULT_PATH.parent / Path(spec["file"]).name
    return LMTokenizer(path, sha256=spec["sha256"])


class SelaGenerator:
    """Model + tokenizer, loaded once; turns a prompt into a continuation (text pieces as they are generated)."""

    def __init__(self, weights: str | Path, tokenizer=None):
        self.model = load_model(weights)
        self.tok = tokenizer or tokenizer_for(self.model)
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
        prompt = prompt.rstrip()
        for t in stream(self.model, self.prompt_ids(prompt), max_tokens, top_p, temperature, rep_penalty, seed):
            new.append(t)
            text = self.tok.decode(new)
            if text.endswith("�"):
                continue
            if len(text) > len(shown) and text.startswith(shown):
                yield text[len(shown):]
                shown = text
        text = self._clean_decode(new)
        if len(text) > len(shown) and text.startswith(shown):
            yield text[len(shown):]

    def _clean_decode(self, ids: list[int]) -> str:
        """Decode, dropping a character cut in half at the end (a UTF-8 character spans up to 4 byte tokens)."""
        full = self.tok.decode(ids)
        if not full.endswith("\ufffd"):
            return full
        for k in range(len(ids) - 1, max(len(ids) - 4, 0), -1):     # drop up to 3 trailing byte tokens
            text = self.tok.decode(ids[:k])
            if not text.endswith("\ufffd"):
                return text
        return full.rstrip("\ufffd")

    def complete(self, prompt: str, **kw) -> str:
        return "".join(self.stream_text(prompt, **kw))

    def generate(self, prompt: str, max_tokens: int = 120, stop_at_newline: bool = False, top_p: float = 0.9,
                 temperature: float = 0.9, rep_penalty: float = 1.15, seed: int | None = None) -> tuple[str, int, bool]:
        """(continuation text, tokens generated, finished): ``finished`` is True when the model ended the text itself
        (<|eos|>) or, with ``stop_at_newline``, when a line was complete (the text is cut before the line break)."""
        new: list[int] = []
        prompt = prompt.rstrip()                   # a trailing space would end the context on a lone space token
        for t in stream(self.model, self.prompt_ids(prompt), max_tokens, top_p, temperature, rep_penalty, seed):
            new.append(t)
            if stop_at_newline:
                text = self.tok.decode(new)
                if "\n" in text.lstrip("\n"):
                    head = text.lstrip("\n")
                    return head[:head.index("\n")], len(new), True
        finished = len(new) < max_tokens
        text = self.tok.decode(new) if finished else self._clean_decode(new)
        return (text.strip("\n") if stop_at_newline else text), len(new), finished
