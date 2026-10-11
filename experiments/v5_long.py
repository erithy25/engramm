"""v5 long run toward GPT-2 quality (test 1.04 bits per byte) on this 4-core CPU.

The fast-v1 recipe of experiments/v5_fast.py, scaled up and made restartable:

    model      d × layers chosen on the command line (default d = 640, 12 layers, 10 heads of 64),
               RMSNorm, QK-norm + RoPE, ReLU², no biases, zero-initialised output projections,
               untied soft-capped head, optional hashed bigram table
    data       the whole train split (285 M tokens, disjoint from val/test), documents shuffled
               per epoch and packed, attention masked to the own document; context grows
               256 → 512 → 1024 over the first half of the token budget
    schedule   by tokens (so restarts do not shift it): warmup, constant, linear decay to 0
               over the last ``--decay-frac`` of the budget; batch of ``--batch-tokens`` per step
               (micro-batches of 4096 tokens)
    restarts   every ``--ckpt-minutes``: the full state (fp32 weights, optimiser, data position)
               to /dev/shm, and bf16 weights + data position to models/lm/v5/long_latest.pt on
               disk (survives a container restart; resuming from it re-warms the optimiser
               over 200 steps)
    curve      every ``--eval-hours`` the bpb on the first 150 val-A documents (window 1024,
               stride 512, as GPT-2 was scored) goes to results/v5/long/curve.jsonl

    env PYTHONPATH=/dev/shm/engramm/pt311:. .venv/bin/python -u -m experiments.v5_long train --threads 4
    env PYTHONPATH=/dev/shm/engramm/pt311:. .venv/bin/python -u -m experiments.v5_long eval --ckpt models/lm/v5/long_latest.pt
"""

from __future__ import annotations

import argparse
import json
import math
import os
import resource
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from experiments import v5_fast as Fm
from experiments import v5_residual as R

REPO = Path(__file__).resolve().parents[1]
TOK = R.TOK
SHM = Path("/dev/shm/engramm/long")
DISK = REPO / "models" / "lm" / "v5"
OUT = REPO / "results" / "v5" / "long"
V = R.V
MICRO_TOKENS = 4096


def bf16_hardware() -> bool:
    """bf16 only where the CPU computes it natively (AMX or AVX512-BF16). Without it, torch
    emulates bf16: measured ≈ 6× slower and steadily growing memory on a Xeon without these units."""
    try:
        flags = Path("/proc/cpuinfo").read_text()
    except OSError:
        return False
    return "amx_bf16" in flags or "avx512_bf16" in flags


MEMORY_EXIT = 75                                              # exit code of the memory guard


def rss_now_mb() -> float:
    """Current resident memory (VmRSS) of this process in MB, 0 if unknown. ru_maxrss is the peak
    since the start and cannot show whether memory is still growing."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return 0.0


# ---------------------------------------------------------------------------
# model (fast-v1 blocks with configurable width, depth and context)
# ---------------------------------------------------------------------------

class Block(nn.Module):
    def __init__(self, d: int, heads: int):
        super().__init__()
        self.d, self.heads, self.hd = d, heads, d // heads
        self.qkv = nn.Linear(d, 3 * d, bias=False)
        self.proj = nn.Linear(d, d, bias=False)
        self.fc1 = nn.Linear(d, 4 * d, bias=False)
        self.fc2 = nn.Linear(4 * d, d, bias=False)

    def forward(self, x, cos, sin, mask):
        B, T, _ = x.shape
        q, k, v = self.qkv(Fm.rms(x)).split(self.d, dim=2)
        q, k, v = (t.view(B, T, self.heads, self.hd).transpose(1, 2) for t in (q, k, v))
        q, k = Fm.rope(Fm.rms(q), cos, sin), Fm.rope(Fm.rms(k), cos, sin)
        if mask is None:
            y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        else:
            y = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        x = x + self.proj(y.transpose(1, 2).reshape(B, T, self.d))
        return x + self.fc2(F.relu(self.fc1(Fm.rms(x))).square())


class LongGPT(nn.Module):
    def __init__(self, d: int, layers: int, heads: int, ctx_max: int, bigram_rows: int):
        super().__init__()
        self.cfg = {"d": d, "layers": layers, "heads": heads, "ctx_max": ctx_max, "bigram_rows": bigram_rows}
        self.emb = nn.Embedding(V, d)
        self.bigram = nn.Embedding(bigram_rows + 1, d, sparse=True) if bigram_rows else None
        self.lam = nn.Parameter(torch.full((layers,), 0.1))
        self.blocks = nn.ModuleList(Block(d, heads) for _ in range(layers))
        self.head = nn.Linear(d, V, bias=False)
        for m in (self.emb, *[b.qkv for b in self.blocks], *[b.fc1 for b in self.blocks]):
            nn.init.normal_(m.weight, std=0.02)
        for m in (self.head, *[b.proj for b in self.blocks], *[b.fc2 for b in self.blocks]):
            nn.init.zeros_(m.weight)
        if self.bigram is not None:
            nn.init.zeros_(self.bigram.weight)
        cos, sin = Fm.rope_tables(ctx_max, d // heads)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)

    def _bigram_rows(self, idx):
        rows = self.cfg["bigram_rows"]
        cur = idx.to(torch.int64)
        prev = torch.roll(cur, 1, dims=1)
        h = ((36313 * cur) ^ (27191 * prev)) % rows
        h[:, 0] = rows
        return h

    def hidden(self, idx, mask=None):
        x = self.emb(idx)
        b = self.bigram(self._bigram_rows(idx)) if self.bigram is not None else None
        for lam, blk in zip(self.lam, self.blocks):
            if b is not None:
                x = x + lam * b
            x = blk(x, self.cos, self.sin, mask)
        return Fm.rms(x)

    def logits(self, h):
        return Fm.SOFTCAP * torch.tanh((h.float() @ self.head.weight.T) / Fm.SOFTCAP)

    def forward(self, idx, feats=None, extra=True):
        return self.logits(self.hidden(idx)), torch.zeros(idx.shape, dtype=torch.float32)


def body_params(m: LongGPT) -> int:
    return sum(p.numel() for n, p in m.named_parameters() if n.startswith("blocks."))


# ---------------------------------------------------------------------------
# data: the train split, documents shuffled per epoch and packed, consumed sequentially
# ---------------------------------------------------------------------------

class TrainStream:
    def __init__(self, seed: int, epoch: int = 0, pos: int = 0):
        self.tokens = np.memmap(TOK / "train.u16", dtype=np.uint16, mode="r")
        starts = np.load(TOK / "train.starts.npy").astype(np.int64)
        self.doc_lo = starts - 1                                   # each document = [EOS, content]
        self.doc_hi = np.append(starts[1:] - 1, len(self.tokens) - 1)
        self.seed = seed
        self.epoch = epoch
        self._build()
        self.pos = pos

    def _build(self):
        order = np.random.default_rng(self.seed + 7919 * self.epoch).permutation(len(self.doc_lo))
        parts = [self.tokens[self.doc_lo[d]:self.doc_hi[d]] for d in order]
        self.stream = np.concatenate(parts + [np.zeros(1, dtype=np.uint16)])
        self.pos = 0

    def batch(self, B: int, T: int) -> torch.Tensor:
        if self.pos + B * T + 1 > len(self.stream):
            self.epoch += 1
            self._build()
        x = np.lib.stride_tricks.sliding_window_view(self.stream[self.pos:self.pos + B * T + 1], T + 1)[::T][:B]
        self.pos += B * T
        return torch.from_numpy(x.astype(np.int64))


# ---------------------------------------------------------------------------
# schedule
# ---------------------------------------------------------------------------

def ctx_at(frac: float, ctx_max: int) -> int:
    if frac < 0.25:
        return min(256, ctx_max)
    if frac < 0.5:
        return min(512, ctx_max)
    return ctx_max


def lr_at(frac: float, steps_since_start: int, peak: float, warmup: int, decay_frac: float) -> float:
    w = min(1.0, (steps_since_start + 1) / warmup)
    if frac < 1.0 - decay_frac:
        return peak * w
    return peak * w * max(0.0, (1.0 - frac) / decay_frac)


# ---------------------------------------------------------------------------
# evaluation with long windows (GPT-2 was scored with window 1024, stride 512)
# ---------------------------------------------------------------------------

@torch.no_grad()
def eval_bpb(model, split: str, window: int, stride: int, max_docs: int = 0, want_lp: bool = False) -> dict:
    """bpb of the network alone; with ``want_lp`` also ``lp``: natural log p of every target token
    at its global position (index i ≥ 1, as in the counters' per-token files, row i − 1)."""
    tokens = np.fromfile(TOK / f"{split}.u16", dtype=np.uint16)
    starts = np.load(TOK / f"{split}.starts.npy")
    nbytes = np.load(TOK / f"{split}.bytes.npy").astype(np.float64) + 1.0
    keep = R.keep_docs(split, len(starts))
    if max_docs:
        starts, nbytes, keep = starts[:max_docs], nbytes[:max_docs], keep[:max_docs]
    ends = np.append(np.load(TOK / f"{split}.starts.npy")[1:] - 1, len(tokens) - 1)[:len(starts)]
    bits = np.zeros(len(starts))
    lp_out = np.zeros(len(tokens), dtype=np.float64) if want_lp else None
    model.eval()
    for d in range(len(starts)):
        base = int(starts[d]) - 1
        seq = torch.from_numpy(tokens[starts[d] - 1:ends[d] + 1].astype(np.int64))
        n = len(seq)
        done, a = 0, 0
        while done < n - 1:
            win = seq[a:a + window + 1][None]
            L = win.shape[1] - 1
            lp = F.log_softmax(model(win[:, :-1])[0], dim=-1)[0]
            tgt = win[0, 1:]
            sel = lp[torch.arange(L), tgt]
            first_new = done - a
            bits[d] -= float(sel[first_new:].sum()) / math.log(2)
            if lp_out is not None:
                lp_out[base + a + 1 + first_new:base + a + 1 + L] = sel[first_new:].double().numpy()
            done = a + L
            a += stride
    model.train()
    res = {"split": split, "window": window, "stride": stride, "docs": int(len(starts)),
           "bpb": float(bits[keep].sum() / nbytes[keep].sum()), "bpb_unfiltered": float(bits.sum() / nbytes.sum()),
           "per_doc_bits": bits.tolist()}
    if lp_out is not None:
        res["lp"] = lp_out[:int(ends[len(starts) - 1]) + 1]
    return res


# ---------------------------------------------------------------------------
# final evaluation extras (PLAN §10): mixtures with the counting models, comparison with GPT-2
# ---------------------------------------------------------------------------

COUNTERS = {"main": REPO / "models" / "lm" / "main" / "eval",     # ENGRAMM-LM exact part, all 285 M train tokens
            "pilot": REPO / "models" / "lm" / "pilot" / "eval"}   # the 30 M-token counter of runs 2-4
GPT2_TEST = REPO / "models" / "lm" / "gpt2" / "eval_test.json"
STAGE1_BPB = 1.04


def _split_meta(split: str, n_tok: int, n_docs: int):
    starts = np.load(TOK / f"{split}.starts.npy")[:n_docs]
    nbytes = np.load(TOK / f"{split}.bytes.npy").astype(np.float64)[:n_docs] + 1.0
    keep = R.keep_docs(split, len(np.load(TOK / f"{split}.starts.npy")))[:n_docs]
    return R.target_docs(starts, n_tok), nbytes, keep


def counter_mixtures(lp: dict, docs_n: dict, where: Path) -> tuple[dict, dict]:
    """Network and one counting model mixed after training, p = λ·p_count + (1 − λ)·p_net, with λ
    global and per history bucket (as the post-hoc baseline of runs 2-4). Counter weights
    (kn, inf, cache) and λ are fitted on near-duplicate-filtered val-A only; test is untouched."""
    per = {}
    for split in ("val_a", "test"):
        n_tok = len(lp[split])
        cols, feats = R.prior_columns(*(np.load(where / f"{split}_{c}.npz") for c in ("kn", "inf", "cache")))
        docs, nbytes, keep = _split_meta(split, n_tok, docs_n[split])
        per[split] = {"cols": cols[:n_tok - 1], "ids": R.bucket_ids(feats[:n_tok - 1]),
                      "p_net": np.exp(lp[split][1:]), "docs": docs, "nbytes": nbytes, "keep": keep}
    v = per["val_a"]
    kept = v["keep"][v["docs"]]
    w = R.fit_weights(v["cols"][kept])
    for e in per.values():
        e["pp"] = R.prior_prob(e["cols"], w).astype(np.float64)
    lam = R.fit_lambda(v["pp"][kept], v["p_net"][kept])
    lam_b = R.fit_bucket_lambda(v["pp"][kept], v["p_net"][kept], v["ids"][kept], lam)
    out, perdoc = {"counter_weights_kn_inf_cache": w.tolist(), "lambda": lam}, {}
    for split, e in per.items():
        lb = lam_b[e["ids"]]
        o = {}
        for name, p in (("counter_alone", e["pp"]), ("mix", lam * e["pp"] + (1 - lam) * e["p_net"]),
                        ("bucket_mix", lb * e["pp"] + (1 - lb) * e["p_net"])):
            b = np.bincount(e["docs"], weights=-np.log2(np.maximum(p, R.EPS)), minlength=len(e["nbytes"]))
            perdoc[f"{split}_{name}"] = b
            o[f"bpb_{name}"] = float(b[e["keep"]].sum() / e["nbytes"][e["keep"]].sum())
            o[f"bpb_{name}_unfiltered"] = float(b.sum() / e["nbytes"].sum())
        out[split] = o
    return out, perdoc


def versus_gpt2(bits: np.ndarray, label: str) -> dict:
    """Paired document bootstrap against GPT-2 small on the same filtered test documents (the
    reference was scored the same way: window 1024, stride 512; bytes per document must match)."""
    from engramm.lm.evaluate import bpb as bpb_ci, bpb_ratio
    g = json.loads(GPT2_TEST.read_text())
    n = len(bits)
    nbytes = np.load(TOK / "test.bytes.npy").astype(np.float64)[:n] + 1.0
    if not np.array_equal(np.asarray(g["doc_bytes"], dtype=np.float64)[:n], nbytes):
        raise SystemExit("GPT-2 reference documents do not match the test split")
    keep = R.keep_docs("test", len(np.load(TOK / "test.starts.npy")))[:n]
    gb = np.asarray(g["per_doc_bits"], dtype=np.float64)[:n]
    ours, ref, ratio = bpb_ci(bits, nbytes, keep), bpb_ci(gb, nbytes, keep), bpb_ratio(bits, gb, keep)
    return {"variant": label, "bpb": ours.as_dict(), "gpt2_bpb": ref.as_dict(),
            "ratio_to_gpt2": ratio["ratio"], "ratio_ci95": ratio["ci95"]}


# ---------------------------------------------------------------------------
# checkpoints
# ---------------------------------------------------------------------------

def atomic_save(obj, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def save_state(model, opts, meta: dict) -> None:
    SHM.mkdir(parents=True, exist_ok=True)
    atomic_save({"model": model.state_dict(), "dense": opts[0].state_dict(),
                 "sparse": opts[1].state_dict() if opts[1] is not None else None, "meta": meta}, SHM / "state.pt")
    DISK.mkdir(parents=True, exist_ok=True)
    atomic_save({"model": {k: v.to(torch.bfloat16) for k, v in model.state_dict().items()}, "meta": meta},
                DISK / "long_latest.pt")


def make_optimizers(model: LongGPT, lr, beta2, wd):
    decay = [p for n, p in model.named_parameters() if n.startswith("blocks.")]
    no_decay = [model.emb.weight, model.head.weight, model.lam]
    dense = torch.optim.AdamW([{"params": decay, "weight_decay": wd}, {"params": no_decay, "weight_decay": 0.0}],
                              lr=lr, betas=(0.9, beta2), eps=1e-8, fused=True)
    sparse = torch.optim.SparseAdam([model.bigram.weight], lr=lr, betas=(0.9, beta2)) if model.bigram is not None else None
    return dense, sparse


# ---------------------------------------------------------------------------
# training
# ---------------------------------------------------------------------------

def train(args) -> None:
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    model = LongGPT(args.d, args.layers, args.heads, args.ctx_max, args.bigram_rows)
    opts = make_optimizers(model, args.lr, args.beta2, args.wd)
    meta = {"tokens": 0, "step": 0, "epoch": 0, "pos": 0, "train_seconds": 0.0, "args": vars(args),
            "restarts": 0, "next_eval_h": args.eval_hours}
    warm_from = 0
    if (SHM / "state.pt").exists():
        st = torch.load(SHM / "state.pt", map_location="cpu", weights_only=False)
        model.load_state_dict(st["model"])
        opts[0].load_state_dict(st["dense"])
        if opts[1] is not None and st["sparse"] is not None:
            opts[1].load_state_dict(st["sparse"])
        meta = st["meta"]
        print(f"resumed full state at {meta['tokens'] / 1e6:.1f} M tokens", flush=True)
        warm_from = meta.get("warm_from", meta["step"] - args.warmup)  # continue a warmup in progress
    elif (DISK / "long_latest.pt").exists():
        st = torch.load(DISK / "long_latest.pt", map_location="cpu", weights_only=False)
        model.load_state_dict({k: v.float() for k, v in st["model"].items()})
        meta = st["meta"]
        meta["restarts"] += 1
        warm_from = meta["step"]                                     # fresh optimiser: warm up again
        meta["warm_from"] = warm_from
        print(f"resumed bf16 weights at {meta['tokens'] / 1e6:.1f} M tokens (optimiser re-warmed)", flush=True)
    if meta["args"]["d"] != args.d or meta["args"]["layers"] != args.layers:
        raise SystemExit("checkpoint has a different model shape")
    use_bf16 = bool(args.bf16) and bf16_hardware()
    print(f"bf16 matmuls: {use_bf16} (requested {bool(args.bf16)}, hardware {bf16_hardware()})", flush=True)
    data = TrainStream(args.seed, meta["epoch"], meta["pos"])
    data.pos = meta["pos"]
    total = args.total_tokens
    dense, sparse = opts
    params = [p for n, p in model.named_parameters() if not n.startswith("bigram")]
    log = open(OUT / "train_log.jsonl", "a")
    t_session = time.time()
    t_ck = time.time()
    tok_t, tok_n = time.time(), meta["tokens"]
    while meta["tokens"] < total:
        if args.session_hours and time.time() - t_session > args.session_hours * 3600:
            break
        frac = meta["tokens"] / total
        T = ctx_at(frac, args.ctx_max)
        lr = lr_at(frac, meta["step"] - warm_from, args.lr, args.warmup, args.decay_frac)
        for g in dense.param_groups:
            g["lr"] = lr
        if sparse is not None:
            for g in sparse.param_groups:
                g["lr"] = lr
        t_step = time.time()
        dense.zero_grad(set_to_none=True)
        if sparse is not None:
            sparse.zero_grad(set_to_none=True)
        micro = max(1, args.batch_tokens // MICRO_TOKENS)
        bsz = max(1, MICRO_TOKENS // T)
        loss_sum = 0.0
        for _ in range(micro):
            batch = data.batch(bsz, T)
            inp, tgt = batch[:, :-1], batch[:, 1:]
            with torch.autocast("cpu", dtype=torch.bfloat16, enabled=use_bf16):
                h = model.hidden(inp, Fm.doc_mask(inp))
            loss = Fm.chunked_loss(h, model.head.weight, tgt, bf16=use_bf16) / micro
            loss.backward()
            loss_sum += float(loss)
        gn = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        dense.step()
        if sparse is not None:
            sparse.step()
        meta["step"] += 1
        meta["tokens"] += micro * bsz * T
        meta["epoch"], meta["pos"] = data.epoch, data.pos
        meta["train_seconds"] += time.time() - t_step
        if meta["step"] % 50 == 0:
            ru = resource.getrusage(resource.RUSAGE_SELF)
            now = time.time()
            rec = {"step": meta["step"], "tokens": meta["tokens"], "frac": round(frac, 5), "ctx": T, "loss": loss_sum,
                   "lr": lr, "grad_norm": gn, "tokens_per_hour": (meta["tokens"] - tok_n) / max(1e-9, now - tok_t) * 3600,
                   "train_hours": meta["train_seconds"] / 3600, "epoch": data.epoch, "rss_mb": ru.ru_maxrss / 1024,
                   "rss_now_mb": rss_now_mb()}
            tok_t, tok_n = now, meta["tokens"]
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print(rec, flush=True)
        if args.max_rss_gb and meta["step"] % 10 == 0 and (rss := rss_now_mb()) > args.max_rss_gb * 1024:
            # A process whose memory keeps growing (allocator fragmentation, measured on 11 Oct with
            # jemalloc oversize_threshold:1 and no decay under bf16) is replaced by a fresh one: the
            # full state goes to the RAM disk, the supervisor restarts and resumes without re-warming.
            save_state(model, opts, meta)
            print(f"memory guard: rss {rss:.0f} MB > {args.max_rss_gb} GB at step {meta['step']}; "
                  f"state saved, exiting for a fresh process", flush=True)
            raise SystemExit(MEMORY_EXIT)
        if time.time() - t_ck > args.ckpt_minutes * 60:
            save_state(model, opts, meta)
            t_ck = time.time()
        if meta["train_seconds"] / 3600 >= meta["next_eval_h"]:
            res = eval_bpb(model, "val_a", 1024, 512, max_docs=150)
            res.pop("per_doc_bits")
            rec = {"train_hours": meta["train_seconds"] / 3600, "tokens": meta["tokens"], **res}
            with open(OUT / "curve.jsonl", "a") as f:
                f.write(json.dumps(rec) + "\n")
            print("curve", rec, flush=True)
            meta["next_eval_h"] += args.eval_hours
    save_state(model, opts, meta)
    if meta["tokens"] >= total:
        (OUT / "done.json").write_text(json.dumps({k: meta[k] for k in ("tokens", "step", "train_seconds", "restarts")}) + "\n")
        print("finished", flush=True)


def bench(args) -> None:
    """Tokens per hour of one configuration at full context (1024), as in the late phase."""
    torch.set_num_threads(args.threads)
    torch.manual_seed(0)
    model = LongGPT(args.d, args.layers, args.heads, 1024, args.bigram_rows)
    dense, sparse = make_optimizers(model, 1e-3, 0.99, 0.1)
    data = TrainStream(0)
    params = [p for n, p in model.named_parameters() if not n.startswith("bigram")]
    times = []
    for i in range(args.warm + args.steps):
        t0 = time.time()
        dense.zero_grad(set_to_none=True)
        for _ in range(args.batch_tokens // MICRO_TOKENS):
            batch = data.batch(MICRO_TOKENS // 1024, 1024)
            inp, tgt = batch[:, :-1], batch[:, 1:]
            with torch.autocast("cpu", dtype=torch.bfloat16, enabled=bf16_hardware()):
                h = model.hidden(inp, Fm.doc_mask(inp))
            (Fm.chunked_loss(h, model.head.weight, tgt, bf16=bf16_hardware()) / (args.batch_tokens // MICRO_TOKENS)).backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        dense.step()
        if i >= args.warm:
            times.append(time.time() - t0)
    s_step = float(np.median(times))
    res = {"d": args.d, "layers": args.layers, "heads": args.heads, "body_params": body_params(model),
           "bf16": bf16_hardware(), "cpu": next((l.split(":", 1)[1].strip() for l in Path("/proc/cpuinfo").read_text().splitlines()
                                                 if l.startswith("model name")), "?"),
           "all_params": sum(p.numel() for p in model.parameters()), "threads": args.threads,
           "batch_tokens": args.batch_tokens, "s_per_step": s_step,
           "tokens_per_hour": args.batch_tokens / s_step * 3600,
           "rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "bench.jsonl", "a") as f:
        f.write(json.dumps(res) + "\n")
    print(json.dumps(res), flush=True)


def evaluate(args) -> None:
    torch.set_num_threads(args.threads)
    st = torch.load(args.ckpt, map_location="cpu", weights_only=False)
    a = st["meta"]["args"]
    model = LongGPT(a["d"], a["layers"], a["heads"], a["ctx_max"], a["bigram_rows"])
    model.load_state_dict({k: v.float() for k, v in st["model"].items()})
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"tokens": st["meta"]["tokens"], "train_hours": st["meta"]["train_seconds"] / 3600, "body_params": body_params(model),
           "window": args.window, "stride": args.stride, "max_docs": args.max_docs, "torch": torch.__version__}
    splits = args.splits.split(",")
    mix = bool(args.mix) and {"val_a", "test"} <= set(splits)
    lp, docs_n, perdoc = {}, {}, {}
    for split in splits:
        t0 = time.time()
        r = eval_bpb(model, split, args.window, args.stride, args.max_docs, want_lp=mix)
        bits = np.array(r.pop("per_doc_bits"))
        if mix:
            lp[split], docs_n[split] = r.pop("lp"), r["docs"]
            docs, _, _ = _split_meta(split, len(lp[split]), r["docs"])
            check = np.bincount(docs, weights=-lp[split][1:] / math.log(2), minlength=len(bits))
            if not np.allclose(check, bits, rtol=1e-4, atol=1e-2):    # per-token and per-document paths agree
                raise SystemExit(f"{split}: per-token log-probabilities do not add up to the document bits")
        perdoc[f"{split}_net_alone"] = bits
        np.save(OUT / f"perdoc_{split}_{args.window}.npy", bits)
        r["eval_seconds"] = time.time() - t0
        res[split] = r
    if mix:
        res["mixtures"] = {}
        for name, where in COUNTERS.items():
            res["mixtures"][name], pd = counter_mixtures(lp, docs_n, where)
            perdoc.update({f"{name}_{k}": v for k, v in pd.items()})
    if "test" in splits and GPT2_TEST.exists():
        res["vs_gpt2"] = [versus_gpt2(perdoc["test_net_alone"], "net_alone")]
        if mix:
            best = min(COUNTERS, key=lambda c: res["mixtures"][c]["test"]["bpb_bucket_mix"])
            res["vs_gpt2"].append(versus_gpt2(perdoc[f"{best}_test_bucket_mix"], f"{best}_bucket_mix"))
        res["stage1"] = {"rule": f"test, filtered, network alone, window {args.window} / stride {args.stride}: "
                                 f"bpb <= {STAGE1_BPB} (PLAN §10)",
                         "bpb": res["test"]["bpb"], "reached": bool(res["test"]["bpb"] <= STAGE1_BPB),
                         "gap": res["test"]["bpb"] - STAGE1_BPB}
    np.savez_compressed(OUT / f"perdoc_{args.tag}.npz", **perdoc)
    (OUT / f"eval_{args.tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--d", type=int, default=640)
    t.add_argument("--layers", type=int, default=12)
    t.add_argument("--heads", type=int, default=10)
    t.add_argument("--ctx-max", type=int, default=1024)
    t.add_argument("--bigram-rows", type=int, default=0)
    t.add_argument("--total-tokens", type=float, default=6e8)
    t.add_argument("--batch-tokens", type=int, default=8192)
    t.add_argument("--lr", type=float, default=2e-3)
    t.add_argument("--beta2", type=float, default=0.995)
    t.add_argument("--wd", type=float, default=0.1)
    t.add_argument("--warmup", type=int, default=200)
    t.add_argument("--decay-frac", type=float, default=0.3)
    t.add_argument("--bf16", type=int, default=1)
    t.add_argument("--threads", type=int, default=4)
    t.add_argument("--seed", type=int, default=42)
    t.add_argument("--ckpt-minutes", type=float, default=60)
    t.add_argument("--eval-hours", type=float, default=6)
    t.add_argument("--session-hours", type=float, default=0, help="stop after this wall-clock time (0 = run to the end)")
    t.add_argument("--max-rss-gb", type=float, default=9.0,
                   help="save the full state and exit (code 75) when resident memory exceeds this (0 = off)")
    e = sub.add_parser("eval")
    e.add_argument("--ckpt", required=True)
    e.add_argument("--splits", default="val_a,test")
    e.add_argument("--window", type=int, default=1024)
    e.add_argument("--stride", type=int, default=512)
    e.add_argument("--max-docs", type=int, default=0)
    e.add_argument("--threads", type=int, default=4)
    e.add_argument("--tag", default="final")
    e.add_argument("--mix", type=int, default=1, help="also the mixtures with the counting models (needs val_a and test)")
    bn = sub.add_parser("bench")
    bn.add_argument("--d", type=int, required=True)
    bn.add_argument("--layers", type=int, default=12)
    bn.add_argument("--heads", type=int, required=True)
    bn.add_argument("--bigram-rows", type=int, default=0)
    bn.add_argument("--batch-tokens", type=int, default=8192)
    bn.add_argument("--threads", type=int, default=4)
    bn.add_argument("--warm", type=int, default=3)
    bn.add_argument("--steps", type=int, default=12)
    args = ap.parse_args()
    {"train": train, "eval": evaluate, "bench": bench}[args.cmd](args)


if __name__ == "__main__":
    main()
