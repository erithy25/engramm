"""Text from the v5 long-run model (experiments/v5_long.py): nucleus sampling, optional
repetition penalty, deterministic per seed.

    env PYTHONPATH=/dev/shm/engramm/pt311:. .venv/bin/python -m experiments.v5_generate \\
        --ckpt models/lm/v5/long_latest.pt --prompt "The history of the city" --tokens 80

Several prompts can be written to a JSON file of samples (``--out``) for side-by-side reading.

Decoding keeps a key/value cache per layer, so each new token costs one position instead of a
forward pass over the whole context (``--no-cache`` restores the full recomputation). When the
text reaches the model's context, the cache is rebuilt from the last half of the context.
``check`` compares cached and full logits on a random small model and on a checkpoint;
``speed`` measures tokens per second for both paths.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch
import torch.nn.functional as F

from engramm.lm.tokenizer import LMTokenizer
from experiments import v5_fast as Fm
from experiments.v5_long import LongGPT

REPO = Path(__file__).resolve().parents[1]


class KVCache:
    """Keys and values of every layer for the positions decoded so far (batch 1)."""

    def __init__(self, layers: int):
        self.k: list[torch.Tensor | None] = [None] * layers
        self.v: list[torch.Tensor | None] = [None] * layers
        self.n = 0                       # positions in the cache
        self.last = -1                   # last token id (previous token for the bigram hash)


def _block_step(blk, x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor, cache: KVCache, i: int) -> torch.Tensor:
    """experiments.v5_long.Block.forward for new positions cache.n … cache.n + T - 1 that attend
    to the cached positions and causally to each other."""
    B, T, _ = x.shape
    q, k, v = blk.qkv(Fm.rms(x)).split(blk.d, dim=2)
    q, k, v = (t.view(B, T, blk.heads, blk.hd).transpose(1, 2) for t in (q, k, v))
    q, k = Fm.rope(Fm.rms(q), cos, sin), Fm.rope(Fm.rms(k), cos, sin)
    if cache.k[i] is not None:
        k = torch.cat((cache.k[i], k), dim=2)
        v = torch.cat((cache.v[i], v), dim=2)
    cache.k[i], cache.v[i] = k, v
    if T == 1:
        y = F.scaled_dot_product_attention(q, k, v)
    else:
        mask = torch.ones(T, cache.n + T, dtype=torch.bool).tril(diagonal=cache.n)
        y = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
    x = x + blk.proj(y.transpose(1, 2).reshape(B, T, blk.d))
    return x + blk.fc2(F.relu(blk.fc1(Fm.rms(x))).square())


@torch.no_grad()
def cached_logits(model: LongGPT, new: list[int], cache: KVCache) -> torch.Tensor:
    """Logits (T, V) for the new tokens, which continue the cached ones; appends them to the cache."""
    T = len(new)
    if cache.n + T > model.cfg["ctx_max"]:
        raise ValueError(f"{cache.n + T} positions exceed the context of {model.cfg['ctx_max']}")
    idx = torch.tensor([new], dtype=torch.int64)
    x = model.emb(idx)
    b = None
    if model.bigram is not None:
        rows = model.cfg["bigram_rows"]
        prev = torch.tensor([[cache.last] + new[:-1]], dtype=torch.int64)
        h = ((36313 * idx) ^ (27191 * prev)) % rows
        if cache.n == 0:
            h[:, 0] = rows               # the first position of a window has no previous token
        b = model.bigram(h)
    cos, sin = model.cos[cache.n:cache.n + T], model.sin[cache.n:cache.n + T]
    for i, (lam, blk) in enumerate(zip(model.lam, model.blocks)):
        if b is not None:
            x = x + lam * b
        x = _block_step(blk, x, cos, sin, cache, i)
    cache.n += T
    cache.last = new[-1]
    return model.logits(Fm.rms(x))[0]


def load_model(path: str) -> tuple[LongGPT, dict]:
    st = torch.load(path, map_location="cpu", weights_only=False)
    a = st["meta"]["args"]
    model = LongGPT(a["d"], a["layers"], a["heads"], a["ctx_max"], a["bigram_rows"])
    model.load_state_dict({k: v.float() for k, v in st["model"].items()})
    model.eval()
    return model, st["meta"]


@torch.no_grad()
def generate(model: LongGPT, ids: list[int], n: int, top_p: float, temperature: float, rep_penalty: float,
             seed: int, ctx: int, use_cache: bool = True) -> list[int]:
    g = torch.Generator().manual_seed(seed)
    out = list(ids)
    cache, pending = KVCache(len(model.blocks)), list(out[-ctx:])
    for _ in range(n):
        if not use_cache:
            logits = model(torch.tensor([out[-ctx:]], dtype=torch.int64))[0][0, -1].float()
        else:
            if cache.n + len(pending) > ctx:          # context full: rebuild from the last half
                cache, pending = KVCache(len(model.blocks)), list(out[-(ctx // 2):])
            logits = cached_logits(model, pending, cache)[-1].float()
        if rep_penalty != 1.0:
            seen = torch.tensor(sorted(set(out[-ctx:])), dtype=torch.int64)
            sel = logits[seen]
            logits[seen] = torch.where(sel > 0, sel / rep_penalty, sel * rep_penalty)
        probs = F.softmax(logits / max(temperature, 1e-6), dim=-1)
        sp, si = torch.sort(probs, descending=True)
        keep = torch.cumsum(sp, 0) - sp < top_p
        sp = sp * keep
        nxt = int(si[torch.multinomial(sp / sp.sum(), 1, generator=g)])
        if nxt == 0:                                   # <|eos|>: end of document
            break
        out.append(nxt)
        pending = [nxt]
    return out[len(ids):]


# ---------------------------------------------------------------------------
# exactness check and speed of the cached path
# ---------------------------------------------------------------------------

def _max_diff(model: LongGPT, ids: list[int], chunks: list[int]) -> float:
    """Largest |cached - full| logit over all positions; the cache is filled in the given chunk sizes."""
    full = model(torch.tensor([ids], dtype=torch.int64))[0][0]
    cache, parts, a = KVCache(len(model.blocks)), [], 0
    for c in chunks:
        parts.append(cached_logits(model, ids[a:a + c], cache))
        a += c
    assert a == len(ids), "chunks must cover the sequence"
    return float((torch.cat(parts) - full).abs().max())


@torch.no_grad()
def check(ckpt: str) -> dict:
    """Cached logits equal the full forward pass: random small models (with and without bigram
    table, all weights non-zero) and, if given, a checkpoint on a real prompt."""
    res = {}
    g = torch.Generator().manual_seed(0)
    for rows in (0, 97):
        torch.manual_seed(1)
        m = LongGPT(64, 3, 4, 64, rows)
        for p in m.parameters():
            p.normal_(0.0, 0.3, generator=g)
        m.eval()
        ids = [0] + torch.randint(1, m.emb.num_embeddings, (63,), generator=g).tolist()
        res[f"small_bigram{rows}"] = _max_diff(m, ids, [17] + [1] * 20 + [5, 22])
    if ckpt:
        model, _ = load_model(ckpt)
        ids = [0] + [int(i) for i in LMTokenizer().encode(
            "The river flows through the old town, past the cathedral and the market square, where traders "
            "have sold fish and bread since the twelfth century. In winter the water often freezes.")]
        res["checkpoint"] = _max_diff(model, ids, [len(ids) // 2] + [1] * (len(ids) - len(ids) // 2))
        res["checkpoint_tokens"] = len(ids)
    tol = {"small_bigram0": 1e-4, "small_bigram97": 1e-4, "checkpoint": 1e-3}
    res["ok"] = all(res[k] <= t for k, t in tol.items() if k in res)
    return res


@torch.no_grad()
def speed(ckpt: str, prompt_tokens: int, new_tokens: int) -> dict:
    """Seconds for ``new_tokens`` greedy-free sampling steps after a prompt, cached and full."""
    model, _ = load_model(ckpt)
    g = torch.Generator().manual_seed(0)
    ids = [0] + torch.randint(1, model.emb.num_embeddings, (prompt_tokens - 1,), generator=g).tolist()
    res = {"prompt_tokens": prompt_tokens, "new_tokens": new_tokens, "threads": torch.get_num_threads()}
    for name, use in (("cached", True), ("full", False)):
        t0 = time.perf_counter()
        generate(model, ids, new_tokens, 1.0, 1.0, 1.0, 0, model.cfg["ctx_max"], use_cache=use)
        res[f"{name}_tokens_per_s"] = new_tokens / (time.perf_counter() - t0)
    res["load_avg_1min"] = os.getloadavg()[0]
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--prompt", action="append", default=[], help="may be given several times")
    ap.add_argument("--tokens", type=int, default=80)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--rep-penalty", type=float, default=1.15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--no-cache", action="store_true", help="recompute the whole context for every token")
    ap.add_argument("--check", action="store_true", help="cached logits == full logits (exit 1 if not)")
    ap.add_argument("--speed", default="", help="PROMPT_TOKENS,NEW_TOKENS: tokens per second, cached and full")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    if args.check:
        res = check(args.ckpt)
        print(json.dumps(res), flush=True)
        raise SystemExit(0 if res["ok"] else 1)
    if args.speed:
        if not args.ckpt:
            ap.error("--speed needs --ckpt")
        p, n = (int(v) for v in args.speed.split(","))
        print(json.dumps(speed(args.ckpt, p, n)), flush=True)
        return
    if not args.ckpt or not args.prompt:
        ap.error("--ckpt and at least one --prompt are required")
    tok = LMTokenizer()
    model, meta = load_model(args.ckpt)
    rows = []
    for p in args.prompt:
        ids = [0] + [int(i) for i in tok.encode(p)]     # a document starts after <|eos|>
        cont = generate(model, ids, args.tokens, args.top_p, args.temperature, args.rep_penalty, args.seed,
                        model.cfg["ctx_max"], use_cache=not args.no_cache)
        text = tok.decode(cont)
        rows.append({"prompt": p, "continuation": text})
        print(f"### {p}\n{p}{text}\n", flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps({"ckpt_tokens": meta["tokens"], "train_hours": meta["train_seconds"] / 3600,
                                              "settings": {k: getattr(args, k) for k in ("tokens", "top_p", "temperature",
                                                                                           "rep_penalty", "seed")},
                                              "kv_cache": not args.no_cache,
                                              "samples": rows}, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
