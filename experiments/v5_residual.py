"""v5 residual training ("Zähl-Residual-Training"): the network learns only what a
counting model cannot predict.

Idea. A counting model (KN5 + infinity-gram + cache, built in minutes without
gradients) already predicts the easy part of language. Classic training spends most
compute relearning that part. Here the network's output is mixed with the frozen
counting prior through a learned, context-dependent gate g:

    p(y) = g · p_count(y) + (1 − g) · p_net(y)

and only the network and gate are trained on −log p(y). The gradient for p_net is
weighted by the posterior share the counting model does *not* explain, so capacity
goes to the hard tokens. The gate sees the hidden state and the history-only match
length of the infinity-gram (no look at the target).

Arms (same model, data region, threads, wall clock):
    plain     ordinary cross-entropy (baseline)
    residual  the mixture loss above

    .venv_b1/bin/python -u experiments/v5_residual.py train --arm plain --hours 3 --threads 2
    .venv_b1/bin/python -u experiments/v5_residual.py eval --arm plain --split test --threads 4

Data: /dev/shm/engramm/v5 from ``python -m experiments.v5_prior`` (tokens the
counting model never saw). Prior weights: EM on val-A, saved by ``weights``.
Reads token files directly; imports nothing from ``engramm`` (torch environment).
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

REPO = Path(__file__).resolve().parents[1]
TOK = REPO / "data" / "cache" / "lm" / "tokens"
EVAL_DIR = REPO / "models" / "lm" / "pilot" / "eval"
DATA = Path("/dev/shm/engramm/v5")
V, CTX, D, LAYERS, HEADS = 32768, 256, 384, 6, 6
K_BUCKETS = 8
CHECKPOINT_HOURS = (1, 2, 3, 6, 12)
EPS = 1e-12


def k_bucket(k: np.ndarray) -> np.ndarray:
    """History match length of the infinity-gram → 0..7 (0 = no match)."""
    k = np.asarray(k, dtype=np.int64)
    edges = np.array([1, 2, 3, 4, 6, 9, 16])
    return np.searchsorted(edges, k, side="right")


def prior_columns(kn, inf, cache):
    p_kn = kn["p"].astype(np.float64)
    cnt, cntw = inf["cnt"], inf["cnt_w"]
    p_inf = np.where(cnt > 0, cntw / np.maximum(cnt, 1), p_kn)
    c = cache["p"]
    p_cache = np.where(c >= 0, c, p_kn)
    return np.stack([p_kn, p_inf, p_cache], axis=1), inf["k"]


def load_prior(where: str):
    if where == "region":
        d = DATA
        cols, k = prior_columns(np.load(d / "region_kn.npz"), np.load(d / "region_inf.npz"),
                                np.load(d / "region_cache.npz"))
        tokens = np.load(d / "region_tokens.npy")
    else:
        cols, k = prior_columns(np.load(EVAL_DIR / f"{where}_kn.npz"), np.load(EVAL_DIR / f"{where}_inf.npz"),
                                np.load(EVAL_DIR / f"{where}_cache.npz"))
        tokens = np.fromfile(TOK / f"{where}.u16", dtype=np.uint16)
    if len(cols) != len(tokens) - 1:
        raise SystemExit(f"{where}: prior length {len(cols)} != tokens-1 {len(tokens) - 1}")
    return tokens, cols, k


def fit_weights(cols: np.ndarray, iters: int = 200) -> np.ndarray:
    w = np.full(cols.shape[1], 1.0 / cols.shape[1])
    for _ in range(iters):
        r = cols * w
        r /= np.maximum(r.sum(1, keepdims=True), EPS)
        w = r.mean(0)
    return w


def prior_prob(cols, w):
    return np.maximum(cols @ w, EPS).astype(np.float32)


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(D), nn.LayerNorm(D)
        self.qkv = nn.Linear(D, 3 * D)
        self.proj = nn.Linear(D, D)
        self.fc1, self.fc2 = nn.Linear(D, 4 * D), nn.Linear(4 * D, D)

    def forward(self, x):
        B, T, _ = x.shape
        q, k, v = self.qkv(self.ln1(x)).split(D, dim=2)
        q, k, v = (t.view(B, T, HEADS, D // HEADS).transpose(1, 2) for t in (q, k, v))
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(y.transpose(1, 2).reshape(B, T, D))
        return x + self.fc2(F.gelu(self.fc1(self.ln2(x))))


class GPT(nn.Module):
    """Same Transformer as experiments/lm_transformer.py plus a gate head."""

    def __init__(self):
        super().__init__()
        self.emb = nn.Embedding(V, D)
        self.pos = nn.Embedding(CTX, D)
        self.blocks = nn.ModuleList(Block() for _ in range(LAYERS))
        self.ln = nn.LayerNorm(D)
        self.gate = nn.Linear(D, 1)
        self.gate_k = nn.Embedding(K_BUCKETS, 1)
        self.apply(self._init)
        nn.init.zeros_(self.gate.weight)
        nn.init.zeros_(self.gate_k.weight)
        nn.init.constant_(self.gate.bias, 0.5)

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)
        if isinstance(m, nn.Linear) and m.bias is not None:
            nn.init.zeros_(m.bias)

    def forward(self, idx, kb=None):
        x = self.emb(idx) + self.pos(torch.arange(idx.shape[1]))
        for b in self.blocks:
            x = b(x)
        h = self.ln(x)
        logits = h @ self.emb.weight.T
        gate_logit = None
        if kb is not None:
            gate_logit = self.gate(h).squeeze(-1) + self.gate_k(kb).squeeze(-1)
        return logits, gate_logit


def mixture_logp(logits, gate_logit, tgt, pp):
    """log(g·pp + (1−g)·p_net(tgt)) for each position."""
    lp_net = torch.gather(F.log_softmax(logits, dim=-1), -1, tgt.unsqueeze(-1)).squeeze(-1)
    return torch.logaddexp(F.logsigmoid(gate_logit) + torch.log(pp), F.logsigmoid(-gate_logit) + lp_net), lp_net


def out_dir(arm: str) -> Path:
    d = DATA / f"ckpt_{arm}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_weights(args):
    _, cols, _ = load_prior("val_a")
    w = fit_weights(cols)
    (DATA / "prior_weights.json").write_text(json.dumps({"w": w.tolist(), "cols": ["kn", "inf", "cache"]}))
    print("prior weights (kn, inf, cache):", np.round(w, 4).tolist(), flush=True)


def weights():
    return np.array(json.loads((DATA / "prior_weights.json").read_text())["w"])


def train(args):
    torch.set_num_threads(args.threads)
    torch.manual_seed(42)
    rng = np.random.default_rng(42)
    tokens, cols, k = load_prior("region")
    pp_all = prior_prob(cols, weights())                # pp_all[i] = prior of tokens[i + 1]
    kb_all = k_bucket(k).astype(np.int64)
    del cols
    model = GPT()
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1)
    out = out_dir(args.arm)
    budget = args.hours * 3600
    t0, step, seen = time.time(), 0, 0
    pending = [h for h in CHECKPOINT_HOURS if h <= args.hours]
    log = open(out / "train_log.jsonl", "a")
    while True:
        elapsed = time.time() - t0
        if pending and elapsed >= pending[0] * 3600:
            h = pending.pop(0)
            torch.save({"model": model.state_dict(), "step": step, "tokens_seen": seen, "hours": h,
                        "params": n_params, "arm": args.arm}, out / f"ckpt_{h}h.pt")
            print(f"checkpoint {h} h: step {step}, {seen} tokens", flush=True)
        if elapsed >= budget:
            torch.save({"model": model.state_dict(), "step": step, "tokens_seen": seen, "hours": args.hours,
                        "params": n_params, "arm": args.arm}, out / "ckpt_final.pt")
            break
        lr = args.lr * min(1.0, (step + 1) / 500) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1.0, elapsed / budget))))
        for g in opt.param_groups:
            g["lr"] = lr
        starts = rng.integers(0, len(tokens) - CTX - 1, size=args.batch)
        batch = torch.from_numpy(np.stack([tokens[s:s + CTX + 1] for s in starts]).astype(np.int64))
        tgt = batch[:, 1:]
        if args.arm == "plain":
            logits, _ = model(batch[:, :-1])
            loss = F.cross_entropy(logits.reshape(-1, V), tgt.reshape(-1))
            net_loss = loss
        else:
            pp = torch.from_numpy(np.stack([pp_all[s:s + CTX] for s in starts]))
            kb = torch.from_numpy(np.stack([kb_all[s:s + CTX] for s in starts]))
            logits, gl = model(batch[:, :-1], kb)
            lp, lp_net = mixture_logp(logits, gl, tgt, pp)
            loss = -lp.mean()
            net_loss = -lp_net.mean().detach()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
        seen += args.batch * CTX
        if step % 100 == 0:
            rec = {"step": step, "loss": float(loss), "net_only_loss": float(net_loss), "lr": lr,
                   "elapsed_s": time.time() - t0, "tokens_seen": seen}
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print(rec, flush=True)


@torch.no_grad()
def token_logprobs(model, tokens, starts, kb_all):
    """Per target position (global index i ≥ 1): network log p and gate logit."""
    ends = np.append(starts[1:] - 1, len(tokens) - 1)
    lp_out = np.zeros(len(tokens), dtype=np.float64)
    gl_out = np.zeros(len(tokens), dtype=np.float64)
    for d in range(len(starts)):
        base = starts[d] - 1
        seq = tokens[base:ends[d] + 1].astype(np.int64)      # EOS, doc, EOS
        n = len(seq)
        done, a = 0, 0
        while done < n - 1:
            window = torch.from_numpy(seq[a:a + CTX + 1])[None]
            kb = torch.from_numpy(kb_all[base + a:base + a + window.shape[1] - 1])[None]
            logits, gl = model(window[:, :-1], kb)
            logp = F.log_softmax(logits, dim=-1)[0]
            tgt = window[0, 1:]
            lp = logp[torch.arange(len(tgt)), tgt].numpy()
            first_new = done + 1 - (a + 1)
            gpos = base + a + 1 + np.arange(first_new, len(tgt))
            lp_out[gpos] = lp[first_new:]
            gl_out[gpos] = gl[0].numpy()[first_new:]
            done = a + len(tgt)
            a += CTX // 2
    return lp_out, gl_out


def evaluate(args):
    torch.set_num_threads(args.threads)
    ck = torch.load(args.ckpt, map_location="cpu")
    model = GPT()
    model.load_state_dict(ck["model"])
    model.eval()
    res = {"ckpt": str(args.ckpt), "arm": ck["arm"], "hours": ck["hours"], "tokens_seen": ck["tokens_seen"],
           "params": ck["params"]}
    w = weights()
    per = {}
    for split in ("val_a", args.split):
        tokens, cols, k = load_prior(split)
        starts = np.load(TOK / f"{split}.starts.npy")
        nbytes = np.load(TOK / f"{split}.bytes.npy")
        if args.max_docs:
            starts, nbytes = starts[:args.max_docs], nbytes[:args.max_docs]
            tokens = tokens[:int(starts[-1]) + int(np.argmax(tokens[starts[-1]:] == 0)) + 1]
            cols, k = cols[:len(tokens) - 1], k[:len(tokens) - 1]
        kb_all = k_bucket(np.append(k, 0)).astype(np.int64)  # kb_all[i] belongs to target i + 1
        t0 = time.time()
        lp, gl = token_logprobs(model, tokens, starts, kb_all)
        pp = np.zeros(len(tokens))
        pp[1:] = prior_prob(cols, w)
        per[split] = (lp, gl, pp, float((nbytes + 1).sum()), time.time() - t0)
    lp, gl, pp, _, _ = per["val_a"]
    m = slice(1, None)
    # post-hoc mixture weight for the plain arm (EM on val-A): a strong, fair baseline
    lam = 0.5
    for _ in range(100):
        a_ = lam * pp[m]
        b_ = (1 - lam) * np.exp(lp[m])
        lam = float(np.mean(a_ / np.maximum(a_ + b_, EPS)))
    res["posthoc_lambda"] = lam
    for split in ("val_a", args.split):
        lp, gl, pp, nb, secs = per[split]
        p_net = np.exp(lp[m])
        g = 1 / (1 + np.exp(-gl[m]))
        bits = lambda p: float(-np.log2(np.maximum(p, EPS)).sum() / nb)
        res[split] = {
            "bpb_net_alone": bits(p_net),
            "bpb_prior_alone": bits(pp[m]),
            "bpb_posthoc_mix": bits(lam * pp[m] + (1 - lam) * p_net),
            "bpb_gated_mix": bits(g * pp[m] + (1 - g) * p_net) if ck["arm"] == "residual" else None,
            "mean_gate": float(g.mean()) if ck["arm"] == "residual" else None,
            "eval_seconds": secs,
        }
    dest = DATA / f"eval_{ck['arm']}_{ck['hours']}h_{args.split}.json"
    dest.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1), flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("weights")
    t = sub.add_parser("train")
    t.add_argument("--arm", choices=("plain", "residual"), required=True)
    t.add_argument("--hours", type=float, default=3)
    t.add_argument("--threads", type=int, default=2)
    t.add_argument("--batch", type=int, default=16)
    t.add_argument("--lr", type=float, default=1e-3)
    e = sub.add_parser("eval")
    e.add_argument("--ckpt", type=Path, required=True)
    e.add_argument("--split", default="test")
    e.add_argument("--threads", type=int, default=4)
    e.add_argument("--max-docs", type=int, default=0, help="smoke test on the first documents only")
    args = ap.parse_args()
    {"weights": cmd_weights, "train": train, "eval": evaluate}[args.cmd](args)


if __name__ == "__main__":
    main()
