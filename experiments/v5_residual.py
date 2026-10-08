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

Arms (same model, data region, threads, training time):
    plain      ordinary cross-entropy (baseline)
    residual   the mixture loss above (run 1; stalled at the counting model's level:
               while p_net ≪ p_count the mixture gives the network almost no gradient)
    residual2  mixture loss + β · cross-entropy of the network alone (β = 0.5), so the
               network must learn on its own while the mixture term steers it to the
               tokens the counter misses; gate starts at g = 0.5 and also sees the
               highest KN order found and log2 of the infinity-gram context count
               (all history-only features, never the target)

At every checkpoint (1, 2, 3 h of training time, evaluation time excluded) the process
evaluates itself on val-A (fits the post-hoc mixture weight) and test, and writes
``results/v5/eval_<arm>_<h>h.json`` into the repository, so a container restart that
wipes /dev/shm loses no finished measurement.

    .venv_b1/bin/python -u experiments/v5_residual.py weights
    .venv_b1/bin/python -u experiments/v5_residual.py train --arm residual2 --hours 3 --threads 2
    .venv_b1/bin/python -u experiments/v5_residual.py eval --ckpt /dev/shm/engramm/v5/ckpt_plain/ckpt_3h.pt

The whole run (prior, weights, smoke test, both arms in parallel): ``sh experiments/v5_run.sh``.

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
RESULTS = REPO / "results" / "v5"
V, CTX, D, LAYERS, HEADS = 32768, 256, 384, 6, 6
K_BUCKETS, F_BUCKETS, C_BUCKETS = 8, 8, 16
CHECKPOINT_HOURS = (1, 2, 3, 6, 12)
GATED_ARMS = ("residual", "residual2")
EPS = 1e-12


def k_bucket(k: np.ndarray) -> np.ndarray:
    """History match length of the infinity-gram → 0..7 (0 = no match)."""
    k = np.asarray(k, dtype=np.int64)
    edges = np.array([1, 2, 3, 4, 6, 9, 16])
    return np.searchsorted(edges, k, side="right")


def gate_features(k: np.ndarray, found: np.ndarray, cnt: np.ndarray) -> np.ndarray:
    """History-only gate inputs per target: (∞-gram match-length bucket, highest KN
    order found, log2(1 + ∞-gram context count) capped at 15), int8, shape (n, 3)."""
    f = np.empty((len(k), 3), dtype=np.int8)
    f[:, 0] = k_bucket(k)
    f[:, 1] = np.clip(np.asarray(found, dtype=np.int64), 0, F_BUCKETS - 1)
    f[:, 2] = np.clip(np.floor(np.log2(1.0 + np.asarray(cnt, dtype=np.float64))), 0, C_BUCKETS - 1)
    return f


def prior_columns(kn, inf, cache):
    p_kn = kn["p"].astype(np.float64)
    cnt, cntw = inf["cnt"], inf["cnt_w"]
    p_inf = np.where(cnt > 0, cntw / np.maximum(cnt, 1), p_kn)
    c = cache["p"]
    p_cache = np.where(c >= 0, c, p_kn)
    return np.stack([p_kn, p_inf, p_cache], axis=1), gate_features(inf["k"], kn["found"], cnt)


def load_prior(where: str):
    """tokens, prior columns (kn, inf, cache) and gate features; row i belongs to target i + 1."""
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


def keep_docs(split: str, n_docs: int) -> np.ndarray:
    """Near-duplicate filter of the LM study (results/lm/dedup.json): False = excluded."""
    d = json.loads((REPO / "results" / "lm" / "dedup.json").read_text())["splits"][split]
    keep = np.ones(n_docs, dtype=bool)
    keep[d["excluded"]] = False
    return keep


def target_docs(starts: np.ndarray, n_tokens: int) -> np.ndarray:
    """Document of every target position 1..n−1 (its closing EOS included)."""
    return np.searchsorted(starts, np.arange(1, n_tokens), side="right") - 1


def prep_region(chunk: int = 4_000_000) -> None:
    """Write the compact training inputs once: region_pp.npy (float32 prior of every target)
    and region_feats.npy (int8 gate features). Chunked, so the peak stays near the size of
    the component files; the trainers then memory-map these instead of rebuilding them."""
    w = weights()
    kn, inf, cache = np.load(DATA / "region_kn.npz"), np.load(DATA / "region_inf.npz"), np.load(DATA / "region_cache.npz")
    p_kn, found = kn["p"], kn["found"]
    k, cnt, cntw = inf["k"], inf["cnt"], inf["cnt_w"]
    c = cache["p"]
    n = len(p_kn)
    pp = np.lib.format.open_memmap(DATA / "region_pp.tmp.npy", mode="w+", dtype=np.float32, shape=(n,))
    ft = np.lib.format.open_memmap(DATA / "region_feats.tmp.npy", mode="w+", dtype=np.int8, shape=(n, 3))
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        cols, f = prior_columns({"p": p_kn[a:b], "found": found[a:b]},
                                {"k": k[a:b], "cnt": cnt[a:b], "cnt_w": cntw[a:b]}, {"p": c[a:b]})
        pp[a:b] = prior_prob(cols, w)
        ft[a:b] = f
    pp.flush()
    ft.flush()
    del pp, ft
    (DATA / "region_pp.tmp.npy").rename(DATA / "region_pp.npy")
    (DATA / "region_feats.tmp.npy").rename(DATA / "region_feats.npy")


def load_region():
    """tokens, prior pp (float32) and gate features (int8) of the training region, memory-mapped;
    row i belongs to target i + 1."""
    if not ((DATA / "region_pp.npy").exists() and (DATA / "region_feats.npy").exists()):
        prep_region()
    tokens = np.load(DATA / "region_tokens.npy", mmap_mode="r")
    pp = np.load(DATA / "region_pp.npy", mmap_mode="r")
    feats = np.load(DATA / "region_feats.npy", mmap_mode="r")
    if len(pp) != len(tokens) - 1 or len(feats) != len(tokens) - 1:
        raise SystemExit("region inputs do not match the region tokens")
    return tokens, pp, feats


def fit_weights(cols: np.ndarray, iters: int = 200) -> np.ndarray:
    w = np.full(cols.shape[1], 1.0 / cols.shape[1])
    for _ in range(iters):
        r = cols * w
        r /= np.maximum(r.sum(1, keepdims=True), EPS)
        w = r.mean(0)
    return w


def prior_prob(cols, w):
    return np.maximum(cols @ w, EPS).astype(np.float32)          # float32 halves the region array


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

    def __init__(self, gate_bias: float = 0.0):
        super().__init__()
        self.emb = nn.Embedding(V, D)
        self.pos = nn.Embedding(CTX, D)
        self.blocks = nn.ModuleList(Block() for _ in range(LAYERS))
        self.ln = nn.LayerNorm(D)
        self.gate = nn.Linear(D, 1)
        self.gate_k = nn.Embedding(K_BUCKETS, 1)
        self.apply(self._init)
        # created after the init pass, so every other parameter draws exactly as in run 1
        self.gate_f = nn.Embedding(F_BUCKETS, 1)
        self.gate_c = nn.Embedding(C_BUCKETS, 1)
        nn.init.zeros_(self.gate.weight)
        for e in (self.gate_k, self.gate_f, self.gate_c):
            nn.init.zeros_(e.weight)
        nn.init.constant_(self.gate.bias, gate_bias)

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)
        if isinstance(m, nn.Linear) and m.bias is not None:
            nn.init.zeros_(m.bias)

    def forward(self, idx, feats=None, extra: bool = True):
        """``feats``: (B, T, 3) gate features of each target; ``extra`` = False uses only the
        match-length bucket (the run-1 gate)."""
        x = self.emb(idx) + self.pos(torch.arange(idx.shape[1]))
        for b in self.blocks:
            x = b(x)
        h = self.ln(x)
        logits = h @ self.emb.weight.T
        gate_logit = None
        if feats is not None:
            gate_logit = self.gate(h).squeeze(-1) + self.gate_k(feats[..., 0]).squeeze(-1)
            if extra:
                gate_logit = gate_logit + self.gate_f(feats[..., 1]).squeeze(-1) + self.gate_c(feats[..., 2]).squeeze(-1)
        return logits, gate_logit


def mixture_logp(logits, gate_logit, tgt, pp):
    """log(g·pp + (1−g)·p_net(tgt)) for each position."""
    lp_net = torch.gather(F.log_softmax(logits, dim=-1), -1, tgt.unsqueeze(-1)).squeeze(-1)
    return torch.logaddexp(F.logsigmoid(gate_logit) + torch.log(pp), F.logsigmoid(-gate_logit) + lp_net), lp_net


def bucket_ids(feats: np.ndarray) -> np.ndarray:
    """One id per target from the three gate features (8 · 8 · 16 = 1024 buckets)."""
    f = feats.astype(np.int64)
    return (f[:, 0] * F_BUCKETS + f[:, 1]) * C_BUCKETS + f[:, 2]


def fit_lambda(pp: np.ndarray, p_net: np.ndarray, iters: int = 100) -> float:
    """EM weight of the counter in λ·pp + (1−λ)·p_net."""
    lam = 0.5
    for _ in range(iters):
        a_ = lam * pp
        lam = float(np.mean(a_ / np.maximum(a_ + (1 - lam) * p_net, EPS)))
    return lam


def fit_bucket_lambda(pp, p_net, ids, lam0: float, alpha: float = 50.0, iters: int = 100) -> np.ndarray:
    """Per-bucket EM weights, shrunk toward the global λ with α pseudo-observations, so
    the post-hoc baseline gets the same context-dependent trust the gate has."""
    n_b = np.bincount(ids, minlength=K_BUCKETS * F_BUCKETS * C_BUCKETS).astype(np.float64)
    lam = np.full(len(n_b), lam0)
    for _ in range(iters):
        a_ = lam[ids] * pp
        r = a_ / np.maximum(a_ + (1 - lam[ids]) * p_net, EPS)
        lam = (np.bincount(ids, weights=r, minlength=len(n_b)) + alpha * lam0) / (n_b + alpha)
    return lam


def gate_bias_for(arm: str) -> float:
    return 0.5 if arm == "residual" else 0.0


def out_dir(arm: str) -> Path:
    d = DATA / f"ckpt_{arm}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_weights(args):
    tokens, cols, _ = load_prior("val_a")
    starts = np.load(TOK / "val_a.starts.npy")
    kept = keep_docs("val_a", len(starts))[target_docs(starts, len(tokens))]
    w = fit_weights(cols[kept])
    (DATA / "prior_weights.json").write_text(json.dumps({"w": w.tolist(), "cols": ["kn", "inf", "cache"],
                                                         "fitted_on": "val_a, near-duplicate-filtered"}))
    print("prior weights (kn, inf, cache):", np.round(w, 4).tolist(), flush=True)


def weights():
    return np.array(json.loads((DATA / "prior_weights.json").read_text())["w"])


def set_results(sub: str) -> None:
    """Write measurements to results/v5/<sub> (run 3 keeps run 2's files intact)."""
    global RESULTS
    RESULTS = REPO / "results" / "v5" / sub if sub else REPO / "results" / "v5"


def train(args):
    set_results(args.results)
    torch.set_num_threads(args.threads)
    torch.manual_seed(42)
    rng = np.random.default_rng(42)
    tokens, pp_all, feats = load_region()                # pp_all[i] = prior of tokens[i + 1]
    model = GPT(gate_bias_for(args.arm))
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1)
    out = out_dir(args.ckpt_dir or args.arm)
    budget = args.hours * 3600
    t0, step, seen, paused = time.time(), 0, 0, 0.0
    marks = tuple(float(x) for x in args.checkpoints.split(",")) if args.checkpoints else CHECKPOINT_HOURS
    pending = sorted({h for h in marks if h <= args.hours} | {args.hours})
    log = open(out / "train_log.jsonl", "a")
    while True:
        elapsed = time.time() - t0 - paused             # training time only
        if pending and elapsed >= pending[0] * 3600:
            h = pending.pop(0)
            ck = {"model": model.state_dict(), "step": step, "tokens_seen": seen, "hours": h,
                  "params": n_params, "arm": args.arm, "beta": args.beta, "train_seconds": elapsed,
                  "bf16": bool(args.bf16)}
            torch.save(ck, out / f"ckpt_{h:g}h.pt")
            print(f"checkpoint {h:g} h: step {step}, {seen} tokens", flush=True)
            if args.eval_at_checkpoints:
                te = time.time()
                model.eval()
                run_eval(model, ck, args.threads, args.eval_docs)
                model.train()
                paused += time.time() - te
            continue
        if elapsed >= budget:
            torch.save({"model": model.state_dict(), "step": step, "tokens_seen": seen, "hours": args.hours,
                        "params": n_params, "arm": args.arm, "beta": args.beta, "train_seconds": elapsed},
                       out / "ckpt_final.pt")
            break
        lr = args.lr * min(1.0, (step + 1) / 500) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1.0, elapsed / budget))))
        for g in opt.param_groups:
            g["lr"] = lr
        starts = rng.integers(0, len(tokens) - CTX - 1, size=args.batch)
        batch = torch.from_numpy(np.stack([tokens[s:s + CTX + 1] for s in starts]).astype(np.int64))
        tgt = batch[:, 1:]
        if args.arm == "plain":
            with torch.autocast("cpu", dtype=torch.bfloat16, enabled=bool(args.bf16)):
                logits, _ = model(batch[:, :-1])
            logits = logits.float()                      # softmax and loss always in fp32
            loss = F.cross_entropy(logits.reshape(-1, V), tgt.reshape(-1))
            net_loss = loss
        else:
            pp = torch.from_numpy(np.stack([pp_all[s:s + CTX] for s in starts]))
            fb = torch.from_numpy(np.stack([feats[s:s + CTX] for s in starts]).astype(np.int64))
            with torch.autocast("cpu", dtype=torch.bfloat16, enabled=bool(args.bf16)):
                logits, gl = model(batch[:, :-1], fb, extra=args.arm == "residual2")
            logits, gl = logits.float(), gl.float()
            lp, lp_net = mixture_logp(logits, gl, tgt, pp)
            loss = -lp.mean()
            if args.arm == "residual2":
                loss = loss - args.beta * lp_net.mean()
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
def token_logprobs(model, tokens, starts, feat_all, extra):
    """Per target position (global index i ≥ 1): network log p and gate logit.
    ``feat_all[i]`` holds the gate features of target i + 1."""
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
            fb = torch.from_numpy(feat_all[base + a:base + a + window.shape[1] - 1].astype(np.int64))[None]
            logits, gl = model(window[:, :-1], fb, extra=extra)
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


def run_eval(model, ck: dict, threads: int, max_docs: int = 0) -> dict:
    """Evaluate a model on val-A and test; write results/v5/eval_<arm>_<h>h.json."""
    torch.set_num_threads(threads)
    arm = ck["arm"]
    gated = arm in GATED_ARMS
    res = {"arm": arm, "hours": ck["hours"], "step": ck["step"], "tokens_seen": ck["tokens_seen"],
           "params": ck["params"], "beta": ck.get("beta"), "train_seconds": ck.get("train_seconds"),
           "threads": threads, "max_docs": max_docs, "torch": torch.__version__}
    w = weights()
    res["prior_weights"] = w.tolist()
    per = {}
    for split in ("val_a", "test"):
        tokens, cols, feats = load_prior(split)
        starts = np.load(TOK / f"{split}.starts.npy")
        nbytes = np.load(TOK / f"{split}.bytes.npy")
        if max_docs:
            starts, nbytes = starts[:max_docs], nbytes[:max_docs]
            tokens = tokens[:int(starts[-1]) + int(np.argmax(tokens[starts[-1]:] == 0)) + 1]
            cols, feats = cols[:len(tokens) - 1], feats[:len(tokens) - 1]
        feat_all = np.concatenate([feats, np.zeros((1, 3), dtype=np.int8)])  # feat_all[i] → target i + 1
        t0 = time.time()
        lp, gl = token_logprobs(model, tokens, starts, feat_all, extra=arm == "residual2")
        docs = target_docs(starts, len(tokens))
        keep = keep_docs(split, len(np.load(TOK / f"{split}.starts.npy")))[:len(starts)]
        per[split] = {"p_net": np.exp(lp[1:]), "g": 1 / (1 + np.exp(-gl[1:])), "pp": prior_prob(cols, w).astype(np.float64),
                      "ids": bucket_ids(feats), "docs": docs, "keep": keep, "nbytes": nbytes.astype(np.float64) + 1.0,
                      "secs": time.time() - t0}
    # post-hoc mixtures fitted on near-duplicate-filtered val-A only: network and counter
    # mixed after training. Global λ, and λ per gate-feature bucket (the fair system-level
    # baseline for the gate).
    v = per["val_a"]
    kept = v["keep"][v["docs"]]
    lam = fit_lambda(v["pp"][kept], v["p_net"][kept])
    lam_b = fit_bucket_lambda(v["pp"][kept], v["p_net"][kept], v["ids"][kept], lam)
    res["posthoc_lambda"] = lam
    perdoc = {}
    for split in ("val_a", "test"):
        e = per[split]
        lb = lam_b[e["ids"]]
        variants = {
            "net_alone": e["p_net"],
            "prior_alone": e["pp"],
            "posthoc_mix": lam * e["pp"] + (1 - lam) * e["p_net"],
            "posthoc_bucket_mix": lb * e["pp"] + (1 - lb) * e["p_net"],
        }
        if gated:
            variants["gated_mix"] = e["g"] * e["pp"] + (1 - e["g"]) * e["p_net"]
        n_docs = len(e["nbytes"])
        out = {"docs": n_docs, "docs_kept": int(e["keep"].sum()), "eval_seconds": e["secs"],
               "mean_gate": float(e["g"].mean()) if gated else None}
        for name, p in variants.items():
            b = np.bincount(e["docs"], weights=-np.log2(np.maximum(p, EPS)), minlength=n_docs)
            perdoc[f"{split}_{name}"] = b
            out[f"bpb_{name}"] = float(b[e["keep"]].sum() / e["nbytes"][e["keep"]].sum())       # primary: filtered
            out[f"bpb_{name}_unfiltered"] = float(b.sum() / e["nbytes"].sum())
        perdoc[f"{split}_doc_bytes"] = e["nbytes"]
        perdoc[f"{split}_keep"] = e["keep"]
        res[split] = out
    RESULTS.mkdir(parents=True, exist_ok=True)
    h = ck["hours"]
    tag = f"{h:g}h" if not max_docs else f"{h:g}h_smoke"
    np.savez_compressed(RESULTS / f"eval_{arm}_{tag}_perdoc.npz", **perdoc)
    dest = RESULTS / f"eval_{arm}_{tag}.json"
    dest.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1), flush=True)
    return res


def evaluate(args):
    set_results(args.results)
    ck = torch.load(args.ckpt, map_location="cpu")
    model = GPT(gate_bias_for(ck["arm"]))
    sd = ck["model"]
    for k in ("gate_f.weight", "gate_c.weight"):          # run-1 checkpoints have no extra gate inputs
        sd.setdefault(k, torch.zeros_like(model.state_dict()[k]))
    model.load_state_dict(sd)
    model.eval()
    run_eval(model, ck, args.threads, args.max_docs)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("weights")
    sub.add_parser("prep")
    t = sub.add_parser("train")
    t.add_argument("--arm", choices=("plain", "residual", "residual2"), required=True)
    t.add_argument("--beta", type=float, default=0.5, help="weight of the network-alone loss (residual2)")
    t.add_argument("--eval-at-checkpoints", type=int, default=1)
    t.add_argument("--eval-docs", type=int, default=0, help="0 = all documents")
    t.add_argument("--checkpoints", default="", help="comma-separated training hours (default 1,2,3,6,12)")
    t.add_argument("--results", default="", help="subdirectory of results/v5 (default: results/v5 itself)")
    t.add_argument("--bf16", type=int, default=0, help="bf16 autocast for the matrix products (AMX); loss in fp32")
    t.add_argument("--ckpt-dir", default="", help="checkpoint directory name under /dev/shm/engramm/v5")
    t.add_argument("--hours", type=float, default=3)
    t.add_argument("--threads", type=int, default=2)
    t.add_argument("--batch", type=int, default=16)
    t.add_argument("--lr", type=float, default=1e-3)
    e = sub.add_parser("eval")
    e.add_argument("--ckpt", type=Path, required=True)
    e.add_argument("--threads", type=int, default=4)
    e.add_argument("--max-docs", type=int, default=0, help="smoke test on the first documents only")
    e.add_argument("--results", default="")
    args = ap.parse_args()
    {"weights": cmd_weights, "prep": lambda a: prep_region(), "train": train, "eval": evaluate}[args.cmd](args)


if __name__ == "__main__":
    main()
