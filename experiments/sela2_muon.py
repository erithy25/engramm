"""Muon for Sela-2: momentum on the hidden weight matrices, orthogonalised by a Newton-Schulz iteration.

    python -m experiments.sela2_muon compare --tokens 4000000 --threads 2     # AdamW vs Muon on the CPU, small model

Muon (Keller Jordan et al. 2024, used in the modded-nanogpt speedruns; "Muon is scalable", Moonshot 2025) updates
every 2-D hidden matrix W with the orthogonalised momentum: G -> momentum (Nesterov) -> NS5(G) ≈ U V^T of its SVD,
scaled by sqrt(max(1, rows / cols)). Embedding, output matrix and scalars stay with AdamW. The orthogonalisation runs in
bfloat16 on the GPU (float32 on the CPU), five iterations of the quintic with coefficients (3.4445, -4.7750, 2.0315).

The ``compare`` command trains the same small LongGPT twice on the base training text, once with AdamW (the Sela-1
recipe) and once with Muon + AdamW, for the same tokens, and reports val-A bits per byte on a fixed document subset.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

NS_COEFFS = (3.4445, -4.7750, 2.0315)


def newton_schulz(G: torch.Tensor, steps: int = 5, eps: float = 1e-7) -> torch.Tensor:
    """Approximately orthogonalise G (the U V^T of its SVD) with the quintic Newton-Schulz iteration."""
    a, b, c = NS_COEFFS
    dtype = torch.bfloat16 if G.is_cuda else torch.float32
    X = G.to(dtype)
    transposed = X.size(0) > X.size(1)
    if transposed:
        X = X.T
    X = X / (X.norm() + eps)
    for _ in range(steps):
        A = X @ X.T
        B = b * A + c * (A @ A)
        X = a * X + B @ X
    if transposed:
        X = X.T
    return X.to(G.dtype)


class Muon(torch.optim.Optimizer):
    """Muon for 2-D parameters: SGD-momentum (Nesterov) whose update is orthogonalised; decoupled weight decay."""

    def __init__(self, params, lr: float = 0.02, momentum: float = 0.95, nesterov: bool = True, ns_steps: int = 5,
                 weight_decay: float = 0.0):
        defaults = dict(lr=lr, momentum=momentum, nesterov=nesterov, ns_steps=ns_steps, weight_decay=weight_decay)
        super().__init__(params, defaults)
        for g in self.param_groups:
            for p in g["params"]:
                if p.ndim != 2:
                    raise ValueError(f"Muon takes 2-D matrices only, got shape {tuple(p.shape)}")

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        for g in self.param_groups:
            for p in g["params"]:
                if p.grad is None:
                    continue
                st = self.state[p]
                if "buf" not in st:
                    st["buf"] = torch.zeros_like(p.grad)
                buf = st["buf"]
                buf.mul_(g["momentum"]).add_(p.grad)
                upd = p.grad.add(buf, alpha=g["momentum"]) if g["nesterov"] else buf
                upd = newton_schulz(upd, g["ns_steps"])
                scale = max(1.0, p.size(0) / p.size(1)) ** 0.5
                if g["weight_decay"]:
                    p.mul_(1 - g["lr"] * g["weight_decay"])
                p.add_(upd, alpha=-g["lr"] * scale)
        return loss


def split_params(model) -> tuple[list, list]:
    """(hidden 2-D matrices for Muon, everything else for AdamW): embeddings, output matrix, scalars and vectors."""
    muon, other = [], []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim == 2 and name.startswith("blocks."):
            muon.append(p)
        else:
            other.append(p)
    return muon, other


# ---------------------------------------------------------------------------
# CPU comparison on the base training text
# ---------------------------------------------------------------------------

def _batches(tokens: np.ndarray, B: int, T: int, seed: int):
    rng = np.random.default_rng(seed)
    n = len(tokens) - T - 1
    while True:
        idx = rng.integers(0, n, B)
        x = np.stack([tokens[i:i + T + 1] for i in idx]).astype(np.int64)
        yield torch.from_numpy(x)


@torch.no_grad()
def _val_bpb(model, docs: int = 60, window: int = 256) -> float:
    from experiments import v5_residual as R
    toks = np.fromfile(R.TOK / "val_a.u16", dtype=np.uint16)
    starts = np.load(R.TOK / "val_a.starts.npy")
    nbytes = np.load(R.TOK / "val_a.bytes.npy").astype(np.float64) + 1.0
    ends = np.append(starts[1:] - 1, len(toks) - 1)
    bits, total_bytes = 0.0, 0.0
    model.eval()
    for d in range(docs):
        seq = torch.from_numpy(toks[int(starts[d]) - 1:int(ends[d]) + 1].astype(np.int64))
        done, a = 0, 0
        n = len(seq)
        while done < n - 1:
            win = seq[a:a + window + 1][None]
            T = win.shape[1] - 1
            lp = F.log_softmax(model(win[:, :-1])[0].float(), -1)[0]
            sel = lp[torch.arange(T), win[0, 1:]]
            bits -= float(sel[done - a:].sum()) / math.log(2)
            done = a + T
            a += window // 2
        total_bytes += nbytes[d]
    model.train()
    return bits / total_bytes


def _train(kind: str, args) -> dict:
    from experiments import v5_long as L
    from experiments import v5_residual as R
    torch.manual_seed(args.seed)
    model = L.LongGPT(d=args.d, layers=args.layers, heads=args.heads, ctx_max=args.ctx, bigram_rows=0)
    toks = np.memmap(R.TOK / "train.u16", dtype=np.uint16, mode="r")[:args.data_tokens]
    steps = args.tokens // (args.batch * args.ctx)
    warm = max(1, steps // 20)
    if kind == "adamw":
        opts = [torch.optim.AdamW(model.parameters(), lr=args.adam_lr, betas=(0.9, 0.95), weight_decay=0.0)]
        base = [args.adam_lr]
    else:
        hidden, other = split_params(model)
        opts = [Muon(hidden, lr=args.muon_lr, momentum=0.95),
                torch.optim.AdamW(other, lr=args.adam_lr, betas=(0.9, 0.95), weight_decay=0.0)]
        base = [args.muon_lr, args.adam_lr]
    gen = _batches(np.asarray(toks), args.batch, args.ctx, args.seed)
    t0 = time.time()
    losses = []
    for s in range(steps):
        frac = s / steps
        mult = min(1.0, (s + 1) / warm) * (1.0 if frac < 0.7 else max(0.0, (1 - frac) / 0.3))
        for o, b in zip(opts, base):
            for g in o.param_groups:
                g["lr"] = b * mult
        x = next(gen)
        logits = model(x[:, :-1])[0]
        loss = F.cross_entropy(logits.float().reshape(-1, logits.size(-1)), x[:, 1:].reshape(-1))
        for o in opts:
            o.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        for o in opts:
            o.step()
        losses.append(float(loss.detach()))
        if not math.isfinite(losses[-1]):
            return {"kind": kind, "diverged_at": s}
    return {"kind": kind, "steps": steps, "tokens": steps * args.batch * args.ctx, "seconds": round(time.time() - t0, 1),
            "final_train_loss": float(np.mean(losses[-20:])), "val_a_bpb_60docs": _val_bpb(model, window=args.ctx)}


def cmd_compare(args) -> None:
    torch.set_num_threads(args.threads)
    out = {"config": vars(args).copy()}
    out["config"].pop("func", None)
    for kind in ("adamw", "muon"):
        r = _train(kind, args)
        out[kind] = r
        print(json.dumps(r), flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--tokens", type=int, default=4_000_000)
    c.add_argument("--data-tokens", type=int, default=50_000_000)
    c.add_argument("--d", type=int, default=256)
    c.add_argument("--layers", type=int, default=4)
    c.add_argument("--heads", type=int, default=4)
    c.add_argument("--ctx", type=int, default=256)
    c.add_argument("--batch", type=int, default=8)
    c.add_argument("--adam-lr", type=float, default=3e-3)
    c.add_argument("--muon-lr", type=float, default=0.02)
    c.add_argument("--seed", type=int, default=0)
    c.add_argument("--threads", type=int, default=2)
    c.add_argument("--out", default="")
    c.set_defaults(func=cmd_compare)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
