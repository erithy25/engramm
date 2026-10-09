"""Comparison only: a small Transformer trained on the same token stream, CPU.

(docs/PREREG_LM.md §5: 6 layers, d = 384, context 256, AdamW; checkpoints
after 1/3/6/12 h wall clock.) Runs in the torch environment (``.venv_b1``); it
reads the token files directly and imports nothing from ``engramm``.

    .venv_b1/bin/python -u experiments/lm_transformer.py train --hours 12 --threads 2
    .venv_b1/bin/python -u experiments/lm_transformer.py eval --ckpt models/lm/transformer/ckpt_12h.pt --split test

Size series (docs/PREREG_PARAMS.md, Messart C): any width/depth, a fixed token
budget instead of a time budget, one final checkpoint per run.

    .venv_b1/bin/python -u experiments/lm_transformer.py train-tokens --d 128 --layers 4 --heads 4 \\
        --tokens 100000000 --seed 42 --lr 2e-3 --out models/params/S3_lr2e-3_s42
    .venv_b1/bin/python -u experiments/lm_transformer.py eval --ckpt models/params/S3_lr2e-3_s42/final.pt \\
        --split test --out results/params/c/S3_lr2e-3_s42_test.json

Evaluation: every document on its own, starting from <|eos|>, sliding window
of 256 tokens with stride 128 (each token scored once, with ≥ 128 tokens of
context where the document has them). BPB with the same byte accounting as
the counting models (UTF-8 bytes + 1 per document).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

REPO = Path(__file__).resolve().parents[1]
TOK = REPO / "data" / "cache" / "lm" / "tokens"
OUT = REPO / "models" / "lm" / "transformer"
V, CTX, D, LAYERS, HEADS = 32768, 256, 384, 6, 6
CHECKPOINT_HOURS = (1, 3, 6, 12)
WARMUP_STEPS = 500


@dataclass(frozen=True)
class Arch:
    """Width, depth and heads; the default is the registered PREREG_LM §5 model."""

    d: int = D
    layers: int = LAYERS
    heads: int = HEADS

    def __post_init__(self):
        if self.d % self.heads:
            raise ValueError(f"d = {self.d} is not divisible by heads = {self.heads}")


class Block(nn.Module):
    def __init__(self, d: int = D, heads: int = HEADS):
        super().__init__()
        self.d, self.heads = d, heads
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)
        self.fc1, self.fc2 = nn.Linear(d, 4 * d), nn.Linear(4 * d, d)

    def forward(self, x):
        B, T, _ = x.shape
        d, h = self.d, self.heads
        q, k, v = self.qkv(self.ln1(x)).split(d, dim=2)
        q, k, v = (t.view(B, T, h, d // h).transpose(1, 2) for t in (q, k, v))
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(y.transpose(1, 2).reshape(B, T, d))
        return x + self.fc2(F.gelu(self.fc1(self.ln2(x))))


class GPT(nn.Module):
    def __init__(self, arch: Arch = Arch()):
        super().__init__()
        self.arch = arch
        self.emb = nn.Embedding(V, arch.d)
        self.pos = nn.Embedding(CTX, arch.d)
        self.blocks = nn.ModuleList(Block(arch.d, arch.heads) for _ in range(arch.layers))
        self.ln = nn.LayerNorm(arch.d)
        self.apply(self._init)

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)
        if isinstance(m, nn.Linear) and m.bias is not None:
            nn.init.zeros_(m.bias)

    def hidden(self, idx):
        x = self.emb(idx) + self.pos(torch.arange(idx.shape[1]))
        for b in self.blocks:
            x = b(x)
        return self.ln(x)

    def forward(self, idx):
        return self.hidden(idx) @ self.emb.weight.T          # tied output layer


class ChunkedCrossEntropy(torch.autograd.Function):
    """Mean cross-entropy of ``h @ W.T`` against ``t``, computed in row blocks.

    The same function as ``F.cross_entropy(h @ W.T, t)``; only the order of the float
    operations differs. The full (tokens × V) logit matrix is never held at once, so each
    block stays in the CPU cache — the V = 32,768 softmax otherwise dominates the step time
    of small models (docs/PREREG_PARAMS.md §6.3). Gradients are formed in the forward pass,
    which is valid because the loss is the last node of the graph."""

    @staticmethod
    def forward(ctx, h, W, t, block):
        n = h.shape[0]
        dh, dW = torch.empty_like(h), torch.zeros_like(W)
        total = torch.zeros((), dtype=torch.float64)
        for s in range(0, n, block):
            hs, ts = h[s:s + block], t[s:s + block]
            z = hs @ W.T
            lse = torch.logsumexp(z, dim=1)
            total += (lse - z.gather(1, ts[:, None]).squeeze(1)).sum(dtype=torch.float64)
            z.sub_(lse[:, None]).exp_()                  # softmax
            z[torch.arange(len(ts)), ts] -= 1.0          # − one-hot
            dh[s:s + block] = z @ W
            dW.addmm_(z.T, hs)
        ctx.save_for_backward(dh, dW)
        ctx.n = n
        return (total / n).to(h.dtype)

    @staticmethod
    def backward(ctx, g):
        dh, dW = ctx.saved_tensors
        return g * dh / ctx.n, g * dW / ctx.n, None, None


CE_BLOCK = 2048


def chunked_loss(model: GPT, batch: torch.Tensor) -> torch.Tensor:
    h = model.hidden(batch[:, :-1])
    return ChunkedCrossEntropy.apply(h.reshape(-1, model.arch.d), model.emb.weight, batch[:, 1:].reshape(-1),
                                     CE_BLOCK)


def param_counts(model: GPT) -> dict:
    """Total parameters (tied embedding counted once) and without token/position embeddings."""
    total = sum(p.numel() for p in model.parameters())
    emb = model.emb.weight.numel() + model.pos.weight.numel()
    return {"params": total, "params_nonemb": total - emb}


def load_split(name):
    tokens = np.fromfile(TOK / f"{name}.u16", dtype=np.uint16)
    starts = np.load(TOK / f"{name}.starts.npy")
    nbytes = np.load(TOK / f"{name}.bytes.npy")
    keys = [tuple(json.loads(l)) for l in open(TOK / f"{name}.keys.jsonl", encoding="utf-8")]
    return tokens, starts, nbytes, keys


def train(args):
    torch.set_num_threads(args.threads)
    torch.manual_seed(42)
    rng = np.random.default_rng(42)
    tokens, _, _, _ = load_split("train")
    model = GPT()
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1)
    OUT.mkdir(parents=True, exist_ok=True)
    budget = args.hours * 3600
    t0, step, seen = time.time(), 0, 0
    pending = [h for h in CHECKPOINT_HOURS if h <= args.hours]
    log = open(OUT / "train_log.jsonl", "a")
    while True:
        elapsed = time.time() - t0
        if pending and elapsed >= pending[0] * 3600:
            h = pending.pop(0)
            torch.save({"model": model.state_dict(), "step": step, "tokens_seen": seen, "hours": h,
                        "params": n_params}, OUT / f"ckpt_{h}h.pt")
            print(f"checkpoint {h} h: step {step}, {seen} tokens", flush=True)
        if elapsed >= budget:
            break
        lr = args.lr * min(1.0, (step + 1) / WARMUP_STEPS) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1.0, elapsed / budget))))
        for g in opt.param_groups:
            g["lr"] = lr
        starts = rng.integers(0, len(tokens) - CTX - 1, size=args.batch)
        batch = torch.from_numpy(np.stack([tokens[s:s + CTX + 1] for s in starts]).astype(np.int64))
        logits = model(batch[:, :-1])
        loss = F.cross_entropy(logits.reshape(-1, V), batch[:, 1:].reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
        seen += args.batch * CTX
        if step % 100 == 0:
            rec = {"step": step, "loss": float(loss), "lr": lr, "elapsed_s": time.time() - t0, "tokens_seen": seen}
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print(rec, flush=True)


def warmup_steps(total_steps: int) -> int:
    """min(500, ⌈0.1 · steps⌉): short runs (the ¼-budget sweeps of small models) keep a short warm-up."""
    return min(WARMUP_STEPS, math.ceil(0.1 * total_steps))


def lr_at(step: int, total_steps: int, peak: float) -> float:
    """Linear warm-up over ``warmup_steps(total_steps)``, then cosine from ``peak`` to 0.1 · ``peak`` at
    the last step (the schedule of ``train``, with steps in place of wall-clock time)."""
    warm = min(1.0, (step + 1) / warmup_steps(total_steps))
    frac = min(1.0, step / max(1, total_steps - 1))
    return peak * warm * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * frac)))


def train_step(model, opt, batch: torch.Tensor, bf16: bool = False, chunked: bool = False) -> float:
    if chunked:
        if bf16:
            raise ValueError("the chunked loss is fp32 only")
        loss = chunked_loss(model, batch)
    elif bf16:
        with torch.autocast("cpu", dtype=torch.bfloat16):
            logits = model(batch[:, :-1])
        loss = F.cross_entropy(logits.float().reshape(-1, V), batch[:, 1:].reshape(-1))
    else:
        logits = model(batch[:, :-1])
        loss = F.cross_entropy(logits.reshape(-1, V), batch[:, 1:].reshape(-1))
    opt.zero_grad(set_to_none=True)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()
    return loss.item()


def _save_atomic(obj, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    torch.save(obj, tmp)
    tmp.replace(path)


def train_tokens(args):
    """One run of the size series: fixed architecture, fixed token budget, one final checkpoint.

    Resumable: every ``--save-every`` seconds the full training state (weights, AdamW moments,
    both random generators, step) goes to ``resume.pt``; a restarted run continues from there
    with the same batch sequence."""
    if args.tokens <= 0:
        raise ValueError("--tokens must be positive")
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    tokens, _, _, _ = load_split("train")
    arch = Arch(args.d, args.layers, args.heads)
    model = GPT(arch)
    counts = param_counts(model)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1)
    per_step = args.batch * CTX
    total_steps = math.ceil(args.tokens / per_step)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    final, resume = out / "final.pt", out / "resume.pt"
    if final.exists():
        raise FileExistsError(f"{final} exists; a finished run is never overwritten")
    meta = {"arch": asdict(arch), **counts, "seed": args.seed, "lr": args.lr, "batch": args.batch, "ctx": CTX,
            "token_budget": args.tokens, "total_steps": total_steps, "bf16": args.bf16, "chunked_loss": args.chunked,
            "threads": args.threads, "warmup_steps": warmup_steps(total_steps), "torch": torch.__version__}
    start, done_s, ema, resumed = 0, 0.0, None, []
    if resume.exists():
        st = torch.load(resume, map_location="cpu", weights_only=False)
        if st["meta"] != meta:
            raise ValueError(f"{resume} belongs to a different configuration")
        model.load_state_dict(st["model"])
        opt.load_state_dict(st["opt"])
        rng.bit_generator.state = st["np_rng"]
        torch.set_rng_state(st["torch_rng"])
        start, done_s, ema, resumed = st["step"], st["elapsed_s"], st["ema"], st["resumed"] + [st["step"]]
        print(f"resumed at step {start}", flush=True)
    else:
        (out / "config.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta), flush=True)
    log = open(out / "train_log.jsonl", "a" if start else "w")
    t0, last_save = time.time() - done_s, time.time()
    marks = [(start, time.time())]                  # (step, time) every 100 steps since this (re)start

    def save_resume(step_done: int) -> None:
        _save_atomic({"meta": meta, "model": model.state_dict(), "opt": opt.state_dict(),
                      "np_rng": rng.bit_generator.state, "torch_rng": torch.get_rng_state(),
                      "step": step_done, "elapsed_s": time.time() - t0, "ema": ema, "resumed": resumed}, resume)

    for step in range(start, total_steps):
        lr = lr_at(step, total_steps, args.lr)
        for g in opt.param_groups:
            g["lr"] = lr
        starts = rng.integers(0, len(tokens) - CTX - 1, size=args.batch)
        batch = torch.from_numpy(np.stack([tokens[s:s + CTX + 1] for s in starts]).astype(np.int64))
        if step == start and args.chunked:
            with torch.no_grad():               # the chunked loss must equal the reference loss
                ref = F.cross_entropy(model(batch[:, :-1]).reshape(-1, V), batch[:, 1:].reshape(-1)).item()
                chk = chunked_loss(model, batch).item()
            if abs(chk - ref) > 1e-4 * abs(ref):
                raise AssertionError(f"chunked loss {chk} differs from cross_entropy {ref}")
        loss = train_step(model, opt, batch, args.bf16, args.chunked)
        if not math.isfinite(loss):
            raise FloatingPointError(f"loss {loss} at step {step}")
        ema = loss if ema is None else 0.98 * ema + 0.02 * loss
        if (step + 1) % 100 == 0 or step + 1 == total_steps:
            el = time.time() - t0
            rec = {"step": step + 1, "loss": loss, "loss_ema": ema, "lr": lr, "elapsed_s": el,
                   "tokens_seen": (step + 1) * per_step, "tokens_per_s": (step + 1) * per_step / el}
            log.write(json.dumps(rec) + "\n")
            log.flush()
            if (step + 1) % 1000 == 0 or step + 1 == total_steps:
                print(rec, flush=True)
        if (step + 1) % 100 == 0:
            marks.append((step + 1, time.time()))
            # throughput guard (Auftraggeber, 2026-10-09): over the last ≤ 1,000 steps since this (re)start,
            # once ≥ 200 steps have run; below --min-tps the run saves its state and pauses (exit 3)
            if args.min_tps > 0 and step + 1 - start >= 200 and step + 1 < total_steps:
                s0, ts0 = marks[max(0, len(marks) - 11)]
                tps = (step + 1 - s0) * per_step / (marks[-1][1] - ts0)
                if tps < args.min_tps:
                    save_resume(step + 1)
                    (out / "paused_throughput.json").write_text(json.dumps(
                        {"step": step + 1, "window_steps": step + 1 - s0, "tokens_per_s": tps,
                         "min_tokens_per_s": args.min_tps, "time": time.time()}) + "\n")
                    print(f"PAUSED: {tps:.0f} tokens/s < {args.min_tps:.0f} at step {step + 1}", flush=True)
                    sys.exit(3)
        if time.time() - last_save >= args.save_every and step + 1 < total_steps:
            save_resume(step + 1)
            last_save = time.time()
    wall = time.time() - t0
    _save_atomic({"model": model.state_dict(), "arch": asdict(arch), **counts, "step": total_steps,
                  "tokens_seen": total_steps * per_step, "hours": wall / 3600, "seed": args.seed, "lr": args.lr,
                  "bf16": args.bf16, "chunked_loss": args.chunked, "train_wall_seconds": wall,
                  "resumed_at_steps": resumed, "final_loss_ema": ema}, final)
    resume.unlink(missing_ok=True)
    print(f"done: {total_steps} steps, {total_steps * per_step} tokens, {wall:.0f} s", flush=True)


def load_checkpoint(path) -> tuple[GPT, dict]:
    ck = torch.load(path, map_location="cpu")
    arch = Arch(**ck["arch"]) if "arch" in ck else Arch()       # registered E12 checkpoints carry no arch
    model = GPT(arch)
    model.load_state_dict(ck["model"])
    model.eval()
    return model, ck


@torch.no_grad()
def evaluate(args):
    torch.set_num_threads(args.threads)
    model, ck = load_checkpoint(args.ckpt)
    tokens, starts, nbytes, keys = load_split(args.split)
    ends = np.append(starts[1:] - 1, len(tokens) - 1)
    bits = np.zeros(len(starts))
    t0 = time.time()
    for d in range(len(starts)):
        seq = tokens[starts[d] - 1:ends[d] + 1].astype(np.int64)      # EOS, doc, EOS
        n = len(seq)
        done, a = 0, 0                    # targets 1..done are scored
        while done < n - 1:
            window = torch.from_numpy(seq[a:a + CTX + 1])[None]
            logp = F.log_softmax(model(window[:, :-1]), dim=-1)[0]
            tgt = window[0, 1:]
            lp = logp[torch.arange(len(tgt)), tgt].numpy()
            first_new = done + 1 - (a + 1)           # index in lp of the first unscored target
            bits[d] -= lp[first_new:].sum() / math.log(2)
            done = a + len(tgt)
            a += CTX // 2
    out = {"ckpt": str(args.ckpt), "split": args.split, "tokens_seen": ck["tokens_seen"], "hours": ck["hours"],
           "params": ck["params"], "per_doc_bits": bits.tolist(), "doc_bytes": (nbytes + 1).tolist(),
           "keys": keys}
    for k in ("arch", "params_nonemb", "seed", "lr", "bf16", "train_wall_seconds"):
        if k in ck:
            out[k] = ck[k]
    out["eval_wall_seconds"] = time.time() - t0
    dest = Path(args.out) if args.out else OUT / f"eval_{Path(args.ckpt).stem}_{args.split}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out))
    print(dest, float(bits.sum() / (nbytes + 1).sum()), flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--hours", type=float, default=12)
    t.add_argument("--threads", type=int, default=2)
    t.add_argument("--batch", type=int, default=16)
    t.add_argument("--lr", type=float, default=1e-3)
    s = sub.add_parser("train-tokens")
    s.add_argument("--d", type=int, required=True)
    s.add_argument("--layers", type=int, required=True)
    s.add_argument("--heads", type=int, required=True)
    s.add_argument("--tokens", type=int, required=True, help="token budget (rounded up to whole steps)")
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--lr", type=float, required=True)
    s.add_argument("--batch", type=int, default=16)
    s.add_argument("--threads", type=int, default=4)
    s.add_argument("--bf16", action="store_true", help="bf16 autocast for the forward pass (fp32 weights)")
    s.add_argument("--chunked", action="store_true", help="block-wise cross-entropy (same loss, faster on CPU)")
    s.add_argument("--save-every", type=float, default=1800.0, help="seconds between resumable checkpoints")
    s.add_argument("--min-tps", type=float, default=0.0,
                   help="pause (save state, exit 3) when the throughput over the last ≤ 1,000 steps falls below this")
    s.add_argument("--out", required=True)
    e = sub.add_parser("eval")
    e.add_argument("--ckpt", type=Path, required=True)
    e.add_argument("--split", default="val_b")
    e.add_argument("--threads", type=int, default=2)
    e.add_argument("--out", default=None)
    args = ap.parse_args()
    {"train": train, "train-tokens": train_tokens, "eval": evaluate}[args.cmd](args)


if __name__ == "__main__":
    main()
