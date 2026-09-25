"""Comparison only: a small Transformer trained on the same token stream, CPU.

(docs/PREREG_LM.md §5: 6 layers, d = 384, context 256, AdamW; checkpoints
after 1/3/6/12 h wall clock.) Runs in the torch environment (``.venv_b1``); it
reads the token files directly and imports nothing from ``engramm``.

    .venv_b1/bin/python -u experiments/lm_transformer.py train --hours 12 --threads 2
    .venv_b1/bin/python -u experiments/lm_transformer.py eval --ckpt models/lm/transformer/ckpt_12h.pt --split test

Evaluation: every document on its own, starting from <|eos|>, sliding window
of 256 tokens with stride 128 (each token scored once, with ≥ 128 tokens of
context where the document has them). BPB with the same byte accounting as
the counting models (UTF-8 bytes + 1 per document).
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
OUT = REPO / "models" / "lm" / "transformer"
V, CTX, D, LAYERS, HEADS = 32768, 256, 384, 6, 6
CHECKPOINT_HOURS = (1, 3, 6, 12)


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
    def __init__(self):
        super().__init__()
        self.emb = nn.Embedding(V, D)
        self.pos = nn.Embedding(CTX, D)
        self.blocks = nn.ModuleList(Block() for _ in range(LAYERS))
        self.ln = nn.LayerNorm(D)
        self.apply(self._init)

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)
        if isinstance(m, nn.Linear) and m.bias is not None:
            nn.init.zeros_(m.bias)

    def forward(self, idx):
        x = self.emb(idx) + self.pos(torch.arange(idx.shape[1]))
        for b in self.blocks:
            x = b(x)
        return self.ln(x) @ self.emb.weight.T          # tied output layer


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
        lr = args.lr * min(1.0, (step + 1) / 500) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1.0, elapsed / budget))))
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


@torch.no_grad()
def evaluate(args):
    torch.set_num_threads(args.threads)
    ck = torch.load(args.ckpt, map_location="cpu")
    model = GPT()
    model.load_state_dict(ck["model"])
    model.eval()
    tokens, starts, nbytes, keys = load_split(args.split)
    ends = np.append(starts[1:] - 1, len(tokens) - 1)
    bits = np.zeros(len(starts))
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
    dest = OUT / f"eval_{Path(args.ckpt).stem}_{args.split}.json"
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
    e = sub.add_parser("eval")
    e.add_argument("--ckpt", type=Path, required=True)
    e.add_argument("--split", default="val_b")
    e.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()
    train(args) if args.cmd == "train" else evaluate(args)


if __name__ == "__main__":
    main()
