"""v5 run 4: a fast training recipe for this 4-core CPU ("fast-v1").

Same data region, tokenizer, model width/depth, batch and evaluation as the plain arm of
experiments/v5_residual.py; everything else is chosen for time-to-quality on this box
(sources and expected gains: docs/PLAN_V5_FROM_SCRATCH.md §9):

    systems   jemalloc (set by the driver), bf16 on the AMX units (autocast; RMSNorm, softmax,
              loss, master weights and optimizer state in fp32), chunked head + loss that never
              materialises the 4096 × 32768 logits, fused AdamW
    model     RMSNorm without scale, QK-norm + RoPE (no learned positions), ReLU² MLP, no biases,
              zero-initialised output projections, untied zero-initialised head with logit
              soft-cap 30, hashed bigram input table (163,840 rows, SparseAdam) added before
              every block with a learned weight
    training  AdamW β = (0.9, β₂) with weight decay only on block matrices, warmup 150 steps,
              constant learning rate, linear decay to 0 over the last 35 % of the time budget;
              documents packed without replacement, attention masked to the own document

Cooldown branches (``branch``) continue a stable-phase checkpoint with a linear decay to 0,
so 0.5 / 1 / 2 h numbers are unbiased without separate runs.

    env PYTHONPATH=/dev/shm/engramm/pt311:. .venv/bin/python -u -m experiments.v5_fast train --hours 3 --threads 2
"""

from __future__ import annotations

import argparse
import json
import math
import resource
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from experiments import v5_residual as R

V, CTX, D, LAYERS, HEADS = R.V, R.CTX, R.D, R.LAYERS, R.HEADS
HD = D // HEADS
BIGRAM_ROWS = 163_840
SOFTCAP = 30.0
ARM = "fast"


# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------

def rms(x: torch.Tensor) -> torch.Tensor:
    return F.rms_norm(x.float(), (x.shape[-1],), eps=1e-6).to(x.dtype)


def rope_tables(T: int, hd: int, theta: float = 10_000.0):
    inv = 1.0 / theta ** (torch.arange(0, hd, 2, dtype=torch.float32) / hd)
    ang = torch.outer(torch.arange(T, dtype=torch.float32), inv)          # (T, hd/2)
    return ang.cos(), ang.sin()


def rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    x1, x2 = x[..., 0::2], x[..., 1::2]
    c, s = cos[: x.shape[-2]].to(x.dtype), sin[: x.shape[-2]].to(x.dtype)
    out = torch.stack((x1 * c - x2 * s, x1 * s + x2 * c), dim=-1)
    return out.flatten(-2)


def bigram_rows(idx: torch.Tensor) -> torch.Tensor:
    """Hashed (previous, current) token pair per input position; position 0 of a window has
    no previous token inside the window and gets the extra row."""
    cur = idx.to(torch.int64)
    prev = torch.roll(cur, 1, dims=1)
    h = ((36313 * cur) ^ (27191 * prev)) % BIGRAM_ROWS
    h[:, 0] = BIGRAM_ROWS
    return h


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.qkv = nn.Linear(D, 3 * D, bias=False)
        self.proj = nn.Linear(D, D, bias=False)
        self.fc1 = nn.Linear(D, 4 * D, bias=False)
        self.fc2 = nn.Linear(4 * D, D, bias=False)

    def forward(self, x, cos, sin, mask):
        B, T, _ = x.shape
        q, k, v = self.qkv(rms(x)).split(D, dim=2)
        q, k, v = (t.view(B, T, HEADS, HD).transpose(1, 2) for t in (q, k, v))
        q, k = rope(rms(q), cos, sin), rope(rms(k), cos, sin)
        if mask is None:
            y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        else:
            y = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        x = x + self.proj(y.transpose(1, 2).reshape(B, T, D))
        return x + self.fc2(F.relu(self.fc1(rms(x))).square())


class FastGPT(nn.Module):
    def __init__(self):
        super().__init__()
        self.emb = nn.Embedding(V, D)
        self.bigram = nn.Embedding(BIGRAM_ROWS + 1, D, sparse=True)
        self.lam = nn.Parameter(torch.full((LAYERS,), 0.1))
        self.blocks = nn.ModuleList(Block() for _ in range(LAYERS))
        self.head = nn.Linear(D, V, bias=False)
        for m in (self.emb, *[b.qkv for b in self.blocks], *[b.fc1 for b in self.blocks]):
            nn.init.normal_(m.weight, std=0.02)
        for m in (self.bigram, self.head, *[b.proj for b in self.blocks], *[b.fc2 for b in self.blocks]):
            nn.init.zeros_(m.weight)
        cos, sin = rope_tables(1024, HD)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)

    def hidden(self, idx, mask=None):
        x = self.emb(idx)
        b = self.bigram(bigram_rows(idx))
        for lam, blk in zip(self.lam, self.blocks):
            x = x + lam * b
            x = blk(x, self.cos, self.sin, mask)
        return rms(x)

    def logits(self, h):
        return SOFTCAP * torch.tanh((h.float() @ self.head.weight.T) / SOFTCAP)

    def forward(self, idx, feats=None, extra=True):
        """Evaluation interface of v5_residual.run_eval: (soft-capped logits, gate logits = 0)."""
        h = self.hidden(idx)
        return self.logits(h), torch.zeros(idx.shape, dtype=torch.float32)


# ---------------------------------------------------------------------------
# chunked head + soft-capped cross-entropy (backward computed chunk by chunk)
# ---------------------------------------------------------------------------

class ChunkedSoftcapCE(torch.autograd.Function):
    """mean_i [logsumexp(c_i) − c_i[y_i]], c = cap·tanh(h Wᵀ / cap). The head's gradients are
    computed in the forward pass chunk by chunk, so no (N, V) tensor is kept. Matmuls in bf16
    (AMX) when ``bf16``; softmax and loss in fp32."""

    @staticmethod
    def forward(ctx, h, W, tgt, chunk: int, bf16: bool):
        N = h.shape[0]
        cdt = torch.bfloat16 if bf16 else torch.float32
        Wc, hc = W.to(cdt), h.to(cdt)
        dh = torch.empty(h.shape, dtype=torch.float32)
        dW = torch.zeros(W.shape, dtype=torch.float32)
        total = torch.zeros((), dtype=torch.float64)
        for s in range(0, N, chunk):
            e = min(N, s + chunk)
            ts = tgt[s:e]
            t = torch.tanh((hc[s:e] @ Wc.T).float() / SOFTCAP)          # (c, V) fp32
            c = t * SOFTCAP
            lse = torch.logsumexp(c, dim=1)
            total += (lse - c.gather(1, ts[:, None]).squeeze(1)).sum(dtype=torch.float64)
            g = c.sub_(lse[:, None]).exp_()                           # softmax(c), in place
            g[torch.arange(e - s), ts] -= 1.0
            g.mul_(1.0 - t.square_()).mul_(1.0 / N)                   # d/dz through the soft-cap
            gc = g.to(cdt)
            dh[s:e] = (gc @ Wc).float()
            dW += (gc.T @ hc[s:e]).float()
        ctx.save_for_backward(dh, dW)
        ctx.h_dtype = h.dtype
        return (total / N).float()

    @staticmethod
    def backward(ctx, gout):
        dh, dW = ctx.saved_tensors
        return (dh * gout).to(ctx.h_dtype), dW * gout, None, None, None


def chunked_loss(h, W, tgt, chunk=512, bf16=True):
    return ChunkedSoftcapCE.apply(h.reshape(-1, h.shape[-1]), W, tgt.reshape(-1), chunk, bf16)


# ---------------------------------------------------------------------------
# data: documents packed without replacement, attention masked to the own document
# ---------------------------------------------------------------------------

class PackedWindows:
    def __init__(self, tokens: np.ndarray, seed: int):
        self.tokens = np.asarray(tokens)
        eos = np.flatnonzero(self.tokens == 0)
        self.doc_lo = eos[:-1]                       # each document = [EOS, content]; the next EOS
        self.doc_hi = eos[1:]                        # closes it and opens the following one
        self.rng = np.random.default_rng(seed)
        self.epoch = -1
        self._new_epoch()

    def _new_epoch(self):
        self.epoch += 1
        order = self.rng.permutation(len(self.doc_lo))
        parts = [self.tokens[self.doc_lo[d]:self.doc_hi[d]] for d in order]
        stream = np.concatenate(parts + [np.zeros(1, dtype=self.tokens.dtype)])
        n = (len(stream) - 1) // CTX
        self.stream = stream
        self.order = self.rng.permutation(n)
        self.pos = 0

    def batch(self, B: int):
        if self.pos + B > len(self.order):
            self._new_epoch()
        w = self.order[self.pos:self.pos + B]
        self.pos += B
        x = np.stack([self.stream[i * CTX:i * CTX + CTX + 1] for i in w]).astype(np.int64)
        return torch.from_numpy(x)


def doc_mask(inp: torch.Tensor) -> torch.Tensor:
    """(B, 1, T, T) boolean: causal and within the same document (an EOS opens a document)."""
    doc = torch.cumsum((inp == 0).to(torch.int32), dim=1)
    same = doc[:, :, None] == doc[:, None, :]
    causal = torch.ones(inp.shape[1], inp.shape[1], dtype=torch.bool).tril()
    return (same & causal)[:, None]


# ---------------------------------------------------------------------------
# optimiser, schedule, training
# ---------------------------------------------------------------------------

def make_optimizers(model: FastGPT, lr: float, beta2: float, wd: float):
    decay = [p for n, p in model.named_parameters() if n.startswith("blocks.")]
    no_decay = [model.emb.weight, model.head.weight, model.lam]
    dense = torch.optim.AdamW([{"params": decay, "weight_decay": wd}, {"params": no_decay, "weight_decay": 0.0}],
                              lr=lr, betas=(0.9, beta2), eps=1e-8, fused=True)
    sparse = torch.optim.SparseAdam([model.bigram.weight], lr=lr, betas=(0.9, beta2), eps=1e-8)
    return dense, sparse


def lr_at(frac: float, step: int, peak: float, warmup: int, decay_from: float) -> float:
    w = min(1.0, (step + 1) / warmup)
    if frac < decay_from:
        return peak * w
    return peak * w * max(0.0, (1.0 - frac) / (1.0 - decay_from))


def train_loop(model, opts, data, args, t_budget, lr_fn, out: Path, marks, start_step=0, start_seen=0, tag=""):
    """Train for ``t_budget`` seconds of training time. At the hours in ``marks`` a full
    checkpoint (with optimiser state, for cooldown branches) is written; at ``args.eval_hours``
    the model is evaluated (evaluation time excluded); at the end the weights are saved when
    ``args.save_final``. Checkpoints are large (≈ 1.3 GB with the bigram table), so only the
    requested ones are written."""
    dense, sparse = opts
    params = [p for p in model.parameters() if p is not model.bigram.weight]
    t0, step, seen, paused = time.time(), start_step, start_seen, 0.0
    end_h = t_budget / 3600
    pending = sorted({h for h in (*marks, *(x - args.offset_hours for x in args.eval_hours)) if 0 < h <= end_h + 1e-9}
                     | {end_h})
    log = open(out / f"train_log{tag}.jsonl", "a")
    clipped = 0
    while True:
        elapsed = time.time() - t0 - paused
        if pending and elapsed >= pending[0] * 3600 - 1e-6:
            h = pending.pop(0)
            hours = h + args.offset_hours
            ck = {"step": step, "tokens_seen": seen, "hours": hours, "params": count(model), "arm": ARM,
                  "train_seconds": elapsed, "args": vars(args), "epoch": data.epoch}
            if any(abs(h - x) < 1e-6 for x in marks):
                torch.save({**ck, "model": model.state_dict(), "dense": dense.state_dict(),
                            "sparse": sparse.state_dict()}, out / f"ckpt{tag}_{hours:g}h.pt")
            if abs(h - end_h) < 1e-6 and args.save_final:
                torch.save({**ck, "model": model.state_dict()}, out / f"ckpt{tag}_{hours:g}h_weights.pt")
            print(f"mark {hours:g} h: step {step}, {seen} tokens", flush=True)
            if any(abs(hours - x) < 1e-6 for x in args.eval_hours):
                te = time.time()
                model.eval()
                R.run_eval(model, ck, args.threads, args.eval_docs)
                model.train()
                paused += time.time() - te
            continue
        if elapsed >= t_budget:
            break
        lr = lr_fn(elapsed, step)
        for g in dense.param_groups:
            g["lr"] = lr
        for g in sparse.param_groups:
            g["lr"] = lr
        batch = data.batch(args.batch)
        inp, tgt = batch[:, :-1], batch[:, 1:]
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=bool(args.bf16)):
            h = model.hidden(inp, doc_mask(inp))
        loss = chunked_loss(h, model.head.weight, tgt, bf16=bool(args.bf16))
        dense.zero_grad(set_to_none=True)
        sparse.zero_grad(set_to_none=True)
        loss.backward()
        gn = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        clipped += gn > 1.0
        dense.step()
        sparse.step()
        step += 1
        seen += args.batch * CTX
        if step % 100 == 0:
            ru = resource.getrusage(resource.RUSAGE_SELF)
            rec = {"step": step, "loss": float(loss), "lr": lr, "grad_norm": gn, "clipped_share": clipped / 100,
                   "elapsed_s": time.time() - t0, "train_s": elapsed, "tokens_seen": seen, "epoch": data.epoch,
                   "rss_mb": ru.ru_maxrss / 1024, "sys_share": ru.ru_stime / max(1e-9, ru.ru_stime + ru.ru_utime),
                   "minor_faults": ru.ru_minflt}
            clipped = 0
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print(rec, flush=True)
    return step, seen


def count(model) -> int:
    return sum(p.numel() for p in model.parameters())


def train(args) -> None:
    R.set_results(args.results)
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    tokens, _, _ = R.load_region()
    data = PackedWindows(np.asarray(tokens), args.seed)
    model = FastGPT()
    opts = make_optimizers(model, args.lr, args.beta2, args.wd)
    out = R.out_dir(args.ckpt_dir or ARM)
    budget = args.hours * 3600

    def lr_fn(elapsed, step):
        return lr_at(min(1.0, elapsed / budget), step, args.lr, args.warmup, args.decay_from)

    marks = tuple(float(x) for x in args.checkpoints.split(",")) if args.checkpoints else ()
    train_loop(model, opts, data, args, budget, lr_fn, out, marks)


def branch(args) -> None:
    """Continue a stable-phase checkpoint with a linear decay of the learning rate to 0 over
    ``--cooldown`` hours, then evaluate; reported as hours = checkpoint + cooldown."""
    R.set_results(args.results)
    torch.set_num_threads(args.threads)
    ck = torch.load(args.ckpt, map_location="cpu", weights_only=False)
    a0 = ck["args"]
    torch.manual_seed(a0["seed"] + 1000)
    tokens, _, _ = R.load_region()
    data = PackedWindows(np.asarray(tokens), a0["seed"] + 1000 + int(round(ck["hours"] * 100)))
    model = FastGPT()
    model.load_state_dict(ck["model"])
    opts = make_optimizers(model, a0["lr"], a0["beta2"], a0["wd"])
    opts[0].load_state_dict(ck["dense"])
    opts[1].load_state_dict(ck["sparse"])
    budget = args.cooldown * 3600
    peak = a0["lr"]

    def lr_fn(elapsed, step):
        return peak * max(0.0, 1.0 - elapsed / budget)

    for k in ("lr", "beta2", "wd", "warmup", "decay_from", "batch", "bf16", "seed"):
        setattr(args, k, a0[k])
    args.offset_hours = ck["hours"]
    args.eval_hours = (ck["hours"] + args.cooldown,)
    out = R.out_dir(args.ckpt_dir or ARM)
    train_loop(model, opts, data, args, budget, lr_fn, out, (), ck["step"], ck["tokens_seen"],
               tag=f"_branch{ck['hours']:g}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--hours", type=float, default=3)
    t.add_argument("--threads", type=int, default=2)
    t.add_argument("--batch", type=int, default=16)
    t.add_argument("--lr", type=float, default=2e-3)
    t.add_argument("--beta2", type=float, default=0.995)
    t.add_argument("--wd", type=float, default=0.1)
    t.add_argument("--warmup", type=int, default=150)
    t.add_argument("--decay-from", type=float, default=0.65)
    t.add_argument("--bf16", type=int, default=1)
    t.add_argument("--seed", type=int, default=42)
    t.add_argument("--checkpoints", default="", help="stable-phase checkpoint hours for cooldown branches")
    t.add_argument("--eval-hours", default="", help="hours at which to evaluate (default: the end)")
    t.add_argument("--eval-docs", type=int, default=0)
    t.add_argument("--results", default="run4")
    t.add_argument("--ckpt-dir", default="")
    t.add_argument("--save-final", type=int, default=1, help="save the final weights (no optimiser state)")
    b = sub.add_parser("branch")
    b.add_argument("--ckpt", required=True)
    b.add_argument("--cooldown", type=float, required=True)
    b.add_argument("--threads", type=int, default=2)
    b.add_argument("--eval-docs", type=int, default=0)
    b.add_argument("--results", default="run4")
    b.add_argument("--ckpt-dir", default="")
    b.add_argument("--save-final", type=int, default=0)
    args = ap.parse_args()
    if args.cmd == "train":
        args.offset_hours = 0.0
        args.eval_hours = tuple(float(x) for x in args.eval_hours.split(",")) if args.eval_hours else (args.hours,)
        train(args)
    else:
        branch(args)


if __name__ == "__main__":
    main()
