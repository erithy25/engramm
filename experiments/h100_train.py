"""Stage-1 training on one GPU (H100), docs/H100_ANLEITUNG.md.

The fast-v1 recipe of the CPU long run (experiments/v5_long.py: RMSNorm, QK-norm + RoPE, ReLU², untied
soft-capped head, documents packed with attention masked to the own document, WSD schedule) at GPT-2-small
size (d = 768, 12 layers, 12 heads), trained with the context of the final measurement (1,024) from the start.

    python -m experiments.h100_train sweep                  # learning rate: short runs on the base data
    python -m experiments.h100_train train --lr 2e-3        # main run (budget-capped) + final evaluation
    python -m experiments.h100_train eval --ckpt PATH       # final evaluation of a saved model
    python -m experiments.h100_train smoke                  # the whole path on the CPU with a tiny model

Safeguards: the step falls back to smaller micro-batches on a CUDA out-of-memory error; the token budget is
cut to the time budget after the first steps (the schedule is by tokens, so this is safe before the decay);
a full state is written every ``--ckpt-minutes`` and a restarted run resumes from it; three non-finite loss
readings in a row stop the run with exit code 3 (the driver then retries once at half the learning rate).

Final evaluation (as PLAN §10/§11, on the GPU in fp32): val-A and test, window 1,024 / stride 512; documents with
≥ 20 % of their 13-token windows in the text actually trained on are excluded (results/v5/h100/contamination.json;
the list of the LM study alone, results/lm/dedup.json, is reported too); paired document bootstrap against GPT-2
small on the same documents; Stage 1 reached iff that test bpb ≤ 1.04 (network alone). Per-token log-probabilities are saved
(float32) so the mixtures with the counting models can be computed on the CPU machine.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from experiments import v5_fast as Fm
from experiments import v5_long as L
from experiments import v5_residual as R

REPO = Path(__file__).resolve().parents[1]
TOK = R.TOK
RESULTS = REPO / "results" / "v5" / "h100"
CKPT = Path(os.environ.get("H100_CKPT_DIR", "/workspace/h100_ckpt"))
DIVERGED = 3                                         # exit code: loss became non-finite
OOM = getattr(torch, "OutOfMemoryError", None) or torch.cuda.OutOfMemoryError
PROMPTS = ("The history of the city", "Albert Einstein was", "Question: What is the capital of France? Answer:",
           "How to make a cup of tea: First,", "Wie geht es dir? Mir geht es")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# device-aware pieces (the CPU versions in v5_fast create helper tensors on the CPU)
# ---------------------------------------------------------------------------

def doc_mask(inp: torch.Tensor) -> torch.Tensor:
    """(B, 1, T, T) boolean: causal and within the same document (an EOS opens a document)."""
    doc = torch.cumsum((inp == 0).to(torch.int32), dim=1)
    same = doc[:, :, None] == doc[:, None, :]
    causal = torch.ones(inp.shape[1], inp.shape[1], dtype=torch.bool, device=inp.device).tril()
    return (same & causal)[:, None]


class ChunkedSoftcapCE(torch.autograd.Function):
    """experiments.v5_fast.ChunkedSoftcapCE with every buffer on the input's device."""

    @staticmethod
    def forward(ctx, h, W, tgt, chunk: int, bf16: bool):
        N, dev = h.shape[0], h.device
        cdt = torch.bfloat16 if bf16 else torch.float32
        Wc, hc = W.to(cdt), h.to(cdt)
        dh = torch.empty(h.shape, dtype=torch.float32, device=dev)
        dW = torch.zeros(W.shape, dtype=torch.float32, device=dev)
        total = torch.zeros((), dtype=torch.float64, device=dev)
        for s in range(0, N, chunk):
            e = min(N, s + chunk)
            ts = tgt[s:e]
            t = torch.tanh((hc[s:e] @ Wc.T).float() / Fm.SOFTCAP)
            c = t * Fm.SOFTCAP
            lse = torch.logsumexp(c, dim=1)
            total += (lse - c.gather(1, ts[:, None]).squeeze(1)).sum(dtype=torch.float64)
            g = c.sub_(lse[:, None]).exp_()
            g[torch.arange(e - s, device=dev), ts] -= 1.0
            g.mul_(1.0 - t.square_()).mul_(1.0 / N)
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


def chunked_loss(h, W, tgt, bf16: bool, chunk: int = 4096):
    return ChunkedSoftcapCE.apply(h.reshape(-1, h.shape[-1]), W, tgt.reshape(-1), chunk, bf16)


def fused_loss(h, W, tgt, bf16: bool):
    """The same soft-capped cross-entropy with ordinary autograd over the whole micro-batch. Under
    torch.compile the element-wise work is fused (the chunked loop above runs ~12 separate fp32 passes
    over every (chunk, V) block); costs (N, V) memory, which the 80 GB of an H100 hold."""
    z = (h.to(torch.bfloat16) @ W.to(torch.bfloat16).T).float() if bf16 else h @ W.T
    c = Fm.SOFTCAP * torch.tanh(z / Fm.SOFTCAP)
    return F.cross_entropy(c.reshape(-1, c.shape[-1]), tgt.reshape(-1))


# ---------------------------------------------------------------------------
# data: documents of a token stream shuffled per epoch and packed (as v5_long.TrainStream, any file)
# ---------------------------------------------------------------------------

class Stream:
    def __init__(self, stem: Path, seed: int, epoch: int = 0, pos: int = 0, limit: int = 0):
        self.tokens = np.memmap(f"{stem}.u16", dtype=np.uint16, mode="r")
        starts = np.load(f"{stem}.starts.npy").astype(np.int64)
        lo, hi = starts - 1, np.append(starts[1:] - 1, len(self.tokens) - 1)
        if limit:                                              # first documents up to ``limit`` tokens
            k = max(1, int(np.searchsorted(hi, limit)))
            lo, hi = lo[:k], hi[:k]
        self.lo, self.hi, self.seed, self.epoch = lo, hi, seed, epoch
        self._build()
        self.pos = pos

    def _build(self):
        order = np.random.default_rng(self.seed + 7919 * self.epoch).permutation(len(self.lo))
        self.stream = np.concatenate([self.tokens[self.lo[d]:self.hi[d]] for d in order] +
                                     [np.zeros(1, dtype=np.uint16)])
        self.pos = 0

    def batch(self, B: int, T: int) -> torch.Tensor:
        if self.pos + B * T + 1 > len(self.stream):
            self.epoch += 1
            self._build()
        x = np.lib.stride_tricks.sliding_window_view(self.stream[self.pos:self.pos + B * T + 1], T + 1)[::T][:B]
        self.pos += B * T
        return torch.from_numpy(x.astype(np.int64))


# ---------------------------------------------------------------------------
# evaluation (GPU, fp32)
# ---------------------------------------------------------------------------

@torch.no_grad()
def eval_bpb(model, split: str, window: int, stride: int, device, max_docs: int = 0, keep=None) -> dict:
    """v5_long.eval_bpb on ``device``; ``lp`` = natural log p of every target token at its global position.
    The window never exceeds the model's context (stride scaled along; only the CPU smoke test is affected)."""
    if window > model.cfg["ctx_max"]:
        window, stride = model.cfg["ctx_max"], model.cfg["ctx_max"] // 2
    tokens = np.fromfile(TOK / f"{split}.u16", dtype=np.uint16)
    starts = np.load(TOK / f"{split}.starts.npy")
    nbytes = np.load(TOK / f"{split}.bytes.npy").astype(np.float64) + 1.0
    keep = R.keep_docs(split, len(starts)) if keep is None else keep
    ends = np.append(starts[1:] - 1, len(tokens) - 1)
    if max_docs:
        starts, ends, nbytes, keep = starts[:max_docs], ends[:max_docs], nbytes[:max_docs], keep[:max_docs]
    bits = np.zeros(len(starts))
    lp_out = np.zeros(int(ends[-1]) + 1, dtype=np.float64)
    was_training = model.training
    model.eval()
    for d in range(len(starts)):
        base = int(starts[d]) - 1
        seq = torch.from_numpy(tokens[base:ends[d] + 1].astype(np.int64)).to(device)
        n, done, a = len(seq), 0, 0
        while done < n - 1:
            win = seq[a:a + window + 1][None]
            T = win.shape[1] - 1
            lp = F.log_softmax(model(win[:, :-1])[0].float(), dim=-1)[0]
            sel = lp[torch.arange(T, device=device), win[0, 1:]]
            first = done - a
            vals = sel[first:].double().cpu().numpy()
            bits[d] -= vals.sum() / math.log(2)
            lp_out[base + a + 1 + first:base + a + 1 + T] = vals
            done = a + T
            a += stride
    model.train(was_training)
    return {"split": split, "window": window, "stride": stride, "docs": int(len(starts)),
            "bpb": float(bits[keep].sum() / nbytes[keep].sum()), "bpb_unfiltered": float(bits.sum() / nbytes.sum()),
            "per_doc_bits": bits, "lp": lp_out}


def extended_keep(split: str, n_docs: int, out: Path = RESULTS) -> np.ndarray | None:
    """Original filter AND not a near-duplicate of the extra training text (contamination.json)."""
    path = out / "contamination.json"
    if not path.exists():
        return None
    rep = json.loads(path.read_text())["splits"][split]
    keep = R.keep_docs(split, n_docs)
    keep[[i for i in rep["excluded_all"] if i < n_docs]] = False
    return keep


def versus_gpt2(bits: np.ndarray, keep: np.ndarray, label: str) -> dict:
    """Paired document bootstrap against GPT-2 small on the same test documents (v5_long.versus_gpt2)."""
    from engramm.lm.evaluate import bpb as bpb_ci, bpb_ratio
    g = json.loads(L.GPT2_TEST.read_text())
    n = len(bits)
    nbytes = np.load(TOK / "test.bytes.npy").astype(np.float64)[:n] + 1.0
    if not np.array_equal(np.asarray(g["doc_bytes"], dtype=np.float64)[:n], nbytes):
        raise SystemExit("GPT-2 reference documents do not match the test split")
    gb = np.asarray(g["per_doc_bits"], dtype=np.float64)[:n]
    ours, ref, ratio = bpb_ci(bits, nbytes, keep[:n]), bpb_ci(gb, nbytes, keep[:n]), bpb_ratio(bits, gb, keep[:n])
    return {"filter": label, "bpb": ours.as_dict(), "gpt2_bpb": ref.as_dict(),
            "ratio_to_gpt2": ratio["ratio"], "ratio_ci95": ratio["ci95"]}


def final_eval(model, device, meta: dict, tag: str, max_docs: int = 0, out: Path = RESULTS) -> dict:
    if device.type == "cuda":                                    # exact fp32 for the reported numbers
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
    out.mkdir(parents=True, exist_ok=True)
    res = {"tag": tag, "tokens": meta["tokens"], "train_hours": meta["train_seconds"] / 3600,
           "params": sum(p.numel() for p in model.parameters()), "body_params": L.body_params(model),
           "window": min(1024, model.cfg["ctx_max"]), "stride": min(1024, model.cfg["ctx_max"]) // 2, "max_docs": max_docs, "torch": torch.__version__,
           "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu"}
    perdoc = {}
    sfx = "" if tag == "main" else f"_{tag}"                     # a re-evaluation never overwrites the run's arrays
    for split in ("val_a", "test"):
        t0 = time.time()
        r = eval_bpb(model, split, 1024, 512, device, max_docs)
        np.save(out / f"lp_{split}{sfx}.npy", r.pop("lp").astype(np.float32))
        perdoc[split] = r.pop("per_doc_bits")
        r["eval_seconds"] = time.time() - t0
        n = len(perdoc[split])
        ext = extended_keep(split, len(np.load(TOK / f"{split}.starts.npy")), out)
        if ext is not None:
            nb = np.load(TOK / f"{split}.bytes.npy").astype(np.float64)[:n] + 1.0
            r["bpb_extended_filter"] = float(perdoc[split][ext[:n]].sum() / nb[ext[:n]].sum())
            r["docs_extended_filter"] = int(ext[:n].sum())
        res[split] = r
        log(f"{split}: {r['bpb']:.4f} bpb (filtered), {r['bpb_unfiltered']:.4f} unfiltered")
    np.savez_compressed(out / f"perdoc_final{sfx}.npz", **{f"{k}_net_alone": v for k, v in perdoc.items()})
    if L.GPT2_TEST.exists():
        n = len(perdoc["test"])
        res["vs_gpt2"] = [versus_gpt2(perdoc["test"], R.keep_docs("test", len(np.load(TOK / "test.starts.npy"))),
                                      "original (results/lm/dedup.json)")]
        ext = extended_keep("test", len(np.load(TOK / "test.starts.npy")), out)
        if ext is not None:
            res["vs_gpt2"].append(versus_gpt2(perdoc["test"], ext, "extended (+ contamination.json)"))
    # The filter of PLAN §10 excludes test documents with >= 20 % of their 13-token windows in the training text.
    # With the extra C4 text that rule has to be applied to the text actually trained on (contamination.json);
    # the list of the LM study alone would leave near-copies of training documents in the test score.
    ext_bpb = res["test"].get("bpb_extended_filter")
    primary = ext_bpb if ext_bpb is not None else res["test"]["bpb"]
    res["stage1"] = {"rule": "test, documents with >= 20 % of their 13-token windows in the training text excluded "
                             "(rule of results/lm/dedup.json applied to the text trained on), network alone, window "
                             f"1024 / stride 512: bpb <= {L.STAGE1_BPB} (PLAN §10/§11)",
                     "filter": "extended (contamination.json)" if ext_bpb is not None else "original (dedup.json)",
                     "bpb": primary, "bpb_original_filter": res["test"]["bpb"],
                     "reached": bool(primary <= L.STAGE1_BPB), "gap": primary - L.STAGE1_BPB}
    (out / f"eval_{tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    log(f"Stage 1 {'REACHED' if res['stage1']['reached'] else 'not reached'}: test {primary:.4f} bpb "
        f"({res['stage1']['filter']}; original filter {res['test']['bpb']:.4f}; target {L.STAGE1_BPB})")
    return res


def samples(model, out: Path, tag: str, meta: dict) -> None:
    """Text from fixed prompts (as the CPU run's samples_*.json), sampled on a CPU copy of the model."""
    from engramm.lm.tokenizer import LMTokenizer
    from experiments.v5_generate import generate
    cpu = L.LongGPT(**model.cfg).eval()
    cpu.load_state_dict({k: v.detach().float().cpu() for k, v in model.state_dict().items()})
    tok = LMTokenizer()
    rows = []
    for p in PROMPTS:
        ids = [0] + [int(i) for i in tok.encode(p)]
        rows.append({"prompt": p, "continuation": tok.decode(generate(cpu, ids, 70, 0.9, 0.9, 1.15, 1, cpu.cfg["ctx_max"]))})
    (out / f"samples_{tag}.json").write_text(json.dumps({"tokens": meta["tokens"], "settings": {
        "tokens": 70, "top_p": 0.9, "temperature": 0.9, "rep_penalty": 1.15, "seed": 1}, "samples": rows},
        indent=1, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# training
# ---------------------------------------------------------------------------

def atomic_save(obj, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def run(args, device) -> dict:
    """One training run; returns meta. Resumes from CKPT/state_<tag>.pt when it exists."""
    torch.manual_seed(args.seed)
    cfg = {"d": args.d, "layers": args.layers, "heads": args.heads, "ctx_max": args.ctx, "bigram_rows": 0}
    model = L.LongGPT(**cfg).to(device)
    opts = L.make_optimizers(model, args.lr, args.beta2, args.wd)
    dense = opts[0]
    ckdir = Path(args.ckpt_dir)
    ckdir.mkdir(parents=True, exist_ok=True)
    state_path = ckdir / f"state_{args.tag}.pt"
    meta = {"tokens": 0, "step": 0, "epoch": 0, "pos": 0, "train_seconds": 0.0, "total_tokens": args.total_tokens,
            "args": vars(args), "cfg": cfg, "next_eval": args.eval_every, "budget_checked": False, "bad": 0}
    if state_path.exists():
        st = torch.load(state_path, map_location="cpu", weights_only=False)
        if st["meta"]["cfg"] != cfg or st["meta"]["args"]["lr"] != args.lr:
            raise SystemExit(f"{state_path} belongs to a different configuration; move it away to start fresh")
        model.load_state_dict(st["model"])
        dense.load_state_dict(st["opt"])
        meta = st["meta"]
        log(f"resumed {args.tag} at {meta['tokens'] / 1e6:.0f} M tokens")
    data = Stream(Path(args.data), seed=args.seed, epoch=meta["epoch"], pos=meta["pos"], limit=args.data_limit)
    params = [p for p in model.parameters()]
    cuda = device.type == "cuda"
    compiled = bool(args.compile and (cuda or os.environ.get("H100_COMPILE_CPU") == "1"))   # CPU: tests only
    fwd = torch.compile(model.hidden) if compiled else model.hidden
    fused = args.loss == "fused"
    loss_fn = (torch.compile(fused_loss) if compiled else fused_loss) if fused else None
    micro = args.micro_batch
    start_step = meta["step"]
    Path(args.out).mkdir(parents=True, exist_ok=True)
    logf = open(Path(args.out) / f"train_log_{args.tag}.jsonl", "a")
    curve = Path(args.out) / f"curve_{args.tag}.jsonl"
    t_ck, t_rate, tok_rate = time.time(), time.time(), meta["tokens"]
    while meta["tokens"] < meta["total_tokens"]:
        total = meta["total_tokens"]
        frac = meta["tokens"] / total
        lr = L.lr_at(frac, meta["step"], args.lr, args.warmup, args.decay_frac)
        for g in dense.param_groups:
            g["lr"] = lr
        t0 = time.time()
        while True:                                            # one optimiser step, OOM-safe
            try:
                dense.zero_grad(set_to_none=True)
                n_micro = max(1, args.batch_tokens // (micro * args.ctx))
                loss_sum = 0.0
                for _ in range(n_micro):
                    batch = data.batch(micro, args.ctx)
                    if cuda:
                        batch = batch.pin_memory().to(device, non_blocking=True)
                    inp, tgt = batch[:, :-1], batch[:, 1:]
                    with torch.autocast(device.type, dtype=torch.bfloat16, enabled=args.bf16):
                        h = fwd(inp, doc_mask(inp))
                    if fused:
                        loss = loss_fn(h, model.head.weight, tgt, args.bf16) / n_micro
                    else:
                        loss = chunked_loss(h, model.head.weight, tgt, bf16=args.bf16) / n_micro
                    loss.backward()
                    loss_sum += float(loss.detach())
                break
            except OOM:
                h = loss = batch = inp = tgt = None            # release the failed attempt's graph first
                dense.zero_grad(set_to_none=True)
                torch.cuda.empty_cache()
                if fused:                                      # the (N, V) loss is the largest buffer: drop it first
                    fused = False
                    log("CUDA out of memory: switching to the chunked loss")
                    continue
                if micro <= 4:
                    raise
                micro //= 2
                log(f"CUDA out of memory: micro-batch halved to {micro} sequences (same tokens per step)")
            except Exception as e:                             # compilation / fused-loss problems in the first steps
                h = loss = batch = inp = tgt = None
                dense.zero_grad(set_to_none=True)
                if meta["step"] > start_step + 3 or not (compiled or fused):
                    raise
                log(f"step failed with compilation/fused loss ({type(e).__name__}: {e}); "
                    f"continuing eagerly with the chunked loss")
                compiled, fused, fwd = False, False, model.hidden
        gn = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        if not (math.isfinite(loss_sum) and math.isfinite(gn)):
            meta["bad"] += 1
            dense.zero_grad(set_to_none=True)                  # skip the update
            log(f"non-finite loss/gradient at step {meta['step']} ({meta['bad']} in a row)")
            if meta["bad"] >= 3:
                logf.close()
                raise SystemExit(DIVERGED)
            continue
        meta["bad"] = 0
        dense.step()
        meta["step"] += 1
        meta["tokens"] += n_micro * micro * args.ctx
        meta["epoch"], meta["pos"] = data.epoch, data.pos
        meta["train_seconds"] += time.time() - t0
        if args.budget_hours and not meta["budget_checked"]:
            if meta["step"] == start_step + 40:                # after compilation and warm-up of the kernels
                t_rate, tok_rate = time.time(), meta["tokens"]
            elif meta["step"] >= start_step + 100:
                rate = (meta["tokens"] - tok_rate) / max(1e-9, time.time() - t_rate)
                fit = int(rate * args.budget_hours * 3600 * 0.95)
                meta["budget_checked"] = True
                if fit < meta["total_tokens"]:
                    log(f"throughput {rate / 1e3:.0f} k tok/s: {meta['total_tokens'] / 1e9:.2f} B tokens would take "
                        f"{meta['total_tokens'] / rate / 3600:.1f} h > budget {args.budget_hours} h; "
                        f"token budget cut to {fit / 1e9:.2f} B")
                    meta["total_tokens"] = fit
                else:
                    log(f"throughput {rate / 1e3:.0f} k tok/s: {meta['total_tokens'] / 1e9:.2f} B tokens in "
                        f"{meta['total_tokens'] / rate / 3600:.1f} h (budget {args.budget_hours} h)")
        if meta["step"] % args.log_every == 0:
            rec = {"step": meta["step"], "tokens": meta["tokens"], "frac": round(meta["tokens"] / meta["total_tokens"], 5),
                   "loss": loss_sum, "lr": lr, "grad_norm": gn, "micro": micro,
                   "tok_per_s": n_micro * micro * args.ctx / max(1e-9, time.time() - t0),
                   "train_hours": meta["train_seconds"] / 3600,
                   "gpu_mem_gb": torch.cuda.max_memory_allocated() / 2**30 if cuda else 0.0}
            logf.write(json.dumps(rec) + "\n")
            logf.flush()
            print(rec, flush=True)
        if meta["tokens"] >= meta["next_eval"]:
            r = eval_bpb(model, "val_a", 1024, 512, device, max_docs=args.eval_docs)
            rec = {"tokens": meta["tokens"], "train_hours": meta["train_seconds"] / 3600, "split": "val_a",
                   "docs": r["docs"], "bpb": r["bpb"]}
            with open(curve, "a") as f:
                f.write(json.dumps(rec) + "\n")
            log(f"curve {rec}")
            meta["next_eval"] += args.eval_every
        if time.time() - t_ck > args.ckpt_minutes * 60:
            atomic_save({"model": model.state_dict(), "opt": dense.state_dict(), "meta": meta}, state_path)
            t_ck = time.time()
    logf.close()
    meta["loss_used"], meta["compiled_used"] = ("fused" if fused else "chunked"), compiled   # after any fallback
    atomic_save({"model": model.state_dict(), "opt": dense.state_dict(), "meta": meta}, state_path)
    # fp32 like the in-memory weights the final evaluation measures: the uploaded file reproduces the reported numbers
    atomic_save({"model": {k: v.detach().float().cpu() for k, v in model.state_dict().items()}, "meta": meta, "cfg": cfg},
                ckdir / f"model_{args.tag}.pt")
    meta["model"] = model
    return meta


def pick_device(want_cuda: bool) -> torch.device:
    if want_cuda:
        if not torch.cuda.is_available():
            raise SystemExit("no CUDA GPU visible (torch.cuda.is_available() is False)")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        return torch.device("cuda")
    return torch.device("cpu")


def cmd_sweep(args) -> None:
    device = pick_device(not args.cpu)
    out = Path(args.out)
    rows = {}
    for lr in [float(x) for x in args.lrs.split(",")]:
        a = argparse.Namespace(**{**vars(args), "lr": lr, "tag": f"sweep_lr{lr:g}", "total_tokens": args.sweep_tokens,
                                  "warmup": args.sweep_warmup, "budget_hours": 0, "eval_every": 10 ** 18})
        done = out / f"sweep_lr{lr:g}.json"
        if done.exists():
            rows[lr] = json.loads(done.read_text())["bpb"]
            continue
        try:
            meta = run(a, device)
            r = eval_bpb(meta["model"], "val_a", 1024, 512, device, max_docs=args.eval_docs)
            bpb = r["bpb"]
        except SystemExit as e:
            if e.code != DIVERGED:
                raise
            bpb = float("inf")
        done.write_text(json.dumps({"lr": lr, "bpb": bpb, "tokens": args.sweep_tokens}) + "\n")
        rows[lr] = bpb
        log(f"sweep lr {lr:g}: val-A {bpb:.4f} bpb")
        if device.type == "cuda":
            torch.cuda.empty_cache()
    finite = {k: v for k, v in rows.items() if math.isfinite(v)}
    if not finite:
        raise SystemExit("every learning rate diverged")
    best = min(finite, key=finite.get)
    near = [k for k, v in finite.items() if v <= finite[best] + 0.003]
    choice = min(near)                                        # within 0.003 bpb: the smaller, safer rate
    res = {"bpb_by_lr": {f"{k:g}": v for k, v in rows.items()}, "best": best, "lr": choice,
           "rule": "lowest val-A bpb; among rates within 0.003 of it the smallest", "tokens_each": args.sweep_tokens}
    (out / "sweep.json").write_text(json.dumps(res, indent=1) + "\n")
    log(f"chosen learning rate {choice:g} ({res['bpb_by_lr']})")


def cmd_train(args) -> None:
    device = pick_device(not args.cpu)
    if args.lr <= 0:
        args.lr = json.loads((Path(args.out) / "sweep.json").read_text())["lr"]
    meta = run(args, device)
    model = meta.pop("model")
    final_eval(model, device, meta, args.tag, max_docs=args.final_docs, out=Path(args.out))
    samples(model, Path(args.out), args.tag, meta)
    log("training and final evaluation finished")


def cmd_eval(args) -> None:
    device = pick_device(not args.cpu)
    st = torch.load(args.ckpt, map_location="cpu", weights_only=False)
    model = L.LongGPT(**st["cfg"]).to(device)
    model.load_state_dict({k: v.float() for k, v in st["model"].items()})
    final_eval(model, device, st["meta"], args.tag, max_docs=args.final_docs, out=Path(args.out))
    samples(model, Path(args.out), args.tag, st["meta"])


def cmd_smoke(args) -> None:
    """Every code path on the CPU with a tiny model and a slice of the base data (results to a scratch dir)."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    common = dict(cpu=True, d=64, layers=2, heads=2, ctx=128, batch_tokens=2048, micro_batch=8, beta2=0.95, wd=0.1,
                  decay_frac=0.3, seed=42, bf16=False, compile=False, loss="chunked", log_every=5, eval_docs=3, final_docs=3,
                  ckpt_minutes=1e9, data=str(TOK / "train"), data_limit=400_000, ckpt_dir=str(out / "ckpt"),
                  out=str(out), budget_hours=0, eval_every=40_000)
    cmd_sweep(argparse.Namespace(**common, lrs="1e-3,3e-3", sweep_tokens=30_000, sweep_warmup=3, lr=0, tag="",
                                 total_tokens=0, warmup=0))
    # main run with bf16 autocast and the fused loss (the H100 defaults)
    common.update(bf16=True, loss="fused", compile=True)     # compiled only on CUDA or with H100_COMPILE_CPU=1
    cmd_train(argparse.Namespace(**common, lr=0, tag="main", total_tokens=100_000, warmup=5, lrs="", sweep_tokens=0,
                                 sweep_warmup=0))
    # the fallback must not hide a broken fused/compiled path: the smoke test fails if the run left it
    saved = torch.load(Path(common["ckpt_dir"]) / "model_main.pt", map_location="cpu", weights_only=False)
    want_compiled = os.environ.get("H100_COMPILE_CPU") == "1"
    if saved["meta"]["loss_used"] != "fused" or saved["meta"]["compiled_used"] != want_compiled:
        raise SystemExit(f"smoke test: fell back to loss={saved['meta']['loss_used']}, "
                         f"compiled={saved['meta']['compiled_used']} (expected fused, compiled={want_compiled})")
    if any(v.dtype != torch.float32 for v in saved["model"].values()):
        raise SystemExit("smoke test: the saved model is not fp32")
    # a resumed run continues from its state file without repeating work
    cmd_train(argparse.Namespace(**common, lr=0, tag="main", total_tokens=100_000, warmup=5, lrs="", sweep_tokens=0,
                                 sweep_warmup=0))
    log("smoke test passed")


def add_common(p) -> None:
    p.add_argument("--cpu", action="store_true", help="run on the CPU (tests)")
    p.add_argument("--d", type=int, default=768)
    p.add_argument("--layers", type=int, default=12)
    p.add_argument("--heads", type=int, default=12)
    p.add_argument("--ctx", type=int, default=1024)
    p.add_argument("--batch-tokens", type=int, default=524288)
    p.add_argument("--micro-batch", type=int, default=32, help="sequences per micro-batch (halved on OOM)")
    p.add_argument("--beta2", type=float, default=0.95)
    p.add_argument("--wd", type=float, default=0.1)
    p.add_argument("--decay-frac", type=float, default=0.3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--bf16", type=int, default=1)
    p.add_argument("--compile", type=int, default=1)
    p.add_argument("--loss", choices=("fused", "chunked"), default="fused",
                   help="fused: whole micro-batch, compiled; chunked: the CPU run's memory-saving loop (fallback)")
    p.add_argument("--log-every", type=int, default=20)
    p.add_argument("--eval-docs", type=int, default=150, help="val-A documents for the curve and the sweep")
    p.add_argument("--final-docs", type=int, default=0, help="0 = all documents in the final evaluation")
    p.add_argument("--ckpt-minutes", type=float, default=30)
    p.add_argument("--ckpt-dir", default=str(CKPT))
    p.add_argument("--out", default=str(RESULTS))
    p.add_argument("--data-limit", type=int, default=0, help="use only the first documents up to this many tokens")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sweep")
    add_common(s)
    s.add_argument("--lrs", default="1e-3,2e-3,4e-3")
    s.add_argument("--sweep-tokens", type=int, default=200_000_000)
    s.add_argument("--sweep-warmup", type=int, default=100)
    s.add_argument("--data", default=str(TOK / "train"), help="token stream stem (base train: available first)")
    s.add_argument("--budget-hours", type=float, default=0)
    t = sub.add_parser("train")
    add_common(t)
    t.add_argument("--lr", type=float, default=0, help="0 = the sweep's choice (sweep.json)")
    t.add_argument("--tag", default="main")
    t.add_argument("--total-tokens", type=int, default=6_000_000_000)
    t.add_argument("--warmup", type=int, default=300)
    t.add_argument("--budget-hours", type=float, default=5.5, help="cap the token budget to this training time")
    t.add_argument("--eval-every", type=int, default=500_000_000)
    t.add_argument("--data", default=str(TOK / "h100" / "train_all"))
    e = sub.add_parser("eval")
    add_common(e)
    e.add_argument("--ckpt", required=True)
    e.add_argument("--tag", default="final")
    k = sub.add_parser("smoke")
    k.add_argument("--out", default="/dev/shm/engramm/h100_smoke")
    args = ap.parse_args()
    for flag in ("bf16", "compile"):                       # torch.autocast(enabled=...) accepts only a real bool
        if hasattr(args, flag):
            setattr(args, flag, bool(getattr(args, flag)))
    if args.cmd == "sweep":
        args.eval_every, args.tag, args.total_tokens, args.warmup, args.lr = 10 ** 18, "", 0, 0, 0
    {"sweep": cmd_sweep, "train": cmd_train, "eval": cmd_eval, "smoke": cmd_smoke}[args.cmd](args)


if __name__ == "__main__":
    main()
