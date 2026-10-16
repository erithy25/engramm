"""Stage-1 training on one GPU (H100), docs/H100_ANLEITUNG.md.

The fast-v1 recipe of the CPU long run (experiments/v5_long.py: RMSNorm, QK-norm + RoPE, ReLU², untied
soft-capped head, documents packed with attention masked to the own document, WSD schedule) at GPT-2-small
size (d = 768, 12 layers, 12 heads), trained with the context of the final measurement (1,024) from the start.

    python -m experiments.h100_train sweep                  # learning rate: short runs on the base data
    python -m experiments.h100_train train --lr 2e-3        # main run (budget-capped) + final evaluation
    python -m experiments.h100_train eval --ckpt PATH       # final evaluation of a saved model
    python -m experiments.h100_train smoke                  # the whole path on the CPU with a tiny model

Safeguards: the step falls back to smaller micro-batches on a CUDA out-of-memory error; on every start the token
budget is cut so that training ends by ``--deadline`` / within ``--budget-hours`` (measured throughput after the
first steps; the schedule is by tokens, so a cut before the decay is harmless); a full state is written every
``--ckpt-minutes`` and a restarted run resumes from it; three non-finite loss readings in a row stop the run with
exit code 3 (the driver then continues from the last saved state at half the learning rate, ``--allow-lr-change``).

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
import shutil
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
SMOKE_OUT = "/dev/shm/engramm/h100_smoke"                   # scratch, never the repository
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
# block-sparse training attention (PLAN §11, Nachtrag 16. Oktober). The dense (B, 1, T, T) mask above makes
# SDPA use its memory-efficient kernel over all T² positions; as a FlexAttention block mask (causal AND same
# document) the fully masked 128×128 blocks are skipped. Same weights, same maths (flex_hidden mirrors
# experiments.v5_long.Block / LongGPT.hidden, which stay untouched: the CPU long run imports them). Used only on
# CUDA with torch ≥ 2.6, and only after it matched the dense attention and was faster on the run's own shapes;
# any failure later switches back to the dense path for the rest of the run. Evaluation always uses the dense path.
# ---------------------------------------------------------------------------

FLEX_MIN_TORCH = (2, 6)
REFIT_BELOW, REFIT_FRAC_MAX = 0.65, 0.68              # re-fit of the token budget only well before the decay
REFIT_MIN_CHANGE = 0.01                                # ... and only when it moves the budget by more than 1 %
FLEX_MIN_GAIN = 0.10                                   # flex only if a training micro-step is ≥ 10 % faster


def torch_version() -> tuple[int, int]:
    return tuple(int(x) for x in torch.__version__.split("+")[0].split(".")[:2])


def doc_ids(inp: torch.Tensor) -> torch.Tensor:
    """(B, T) document number of every position (an EOS opens a document), as in doc_mask."""
    return torch.cumsum((inp == 0).to(torch.int32), dim=1)


def flex_block_mask(inp: torch.Tensor, compile_mask: bool):
    import warnings
    from torch.nn.attention.flex_attention import create_block_mask
    warnings.filterwarnings("ignore", message="_compile flag on create_block_mask")   # still works (torch 2.14)
    doc = doc_ids(inp)

    def causal_same_doc(b, h, q, kv):
        return (doc[b, q] == doc[b, kv]) & (q >= kv)

    B, T = inp.shape
    return create_block_mask(causal_same_doc, B, None, T, T, device=inp.device, _compile=compile_mask)


def flex_hidden(model, idx: torch.Tensor, block_mask) -> torch.Tensor:
    """LongGPT.hidden (no bigram table) with every block's attention through flex_attention."""
    from torch.nn.attention.flex_attention import flex_attention
    x = model.emb(idx)
    for blk in model.blocks:
        B, T, _ = x.shape
        q, k, v = blk.qkv(Fm.rms(x)).split(blk.d, dim=2)
        q, k, v = (t.view(B, T, blk.heads, blk.hd).transpose(1, 2) for t in (q, k, v))
        q, k = Fm.rope(Fm.rms(q), model.cos, model.sin), Fm.rope(Fm.rms(k), model.cos, model.sin)
        y = flex_attention(q, k, v, block_mask=block_mask)
        x = x + blk.proj(y.transpose(1, 2).reshape(B, T, blk.d))
        x = x + blk.fc2(F.relu(blk.fc1(Fm.rms(x))).square())
    return Fm.rms(x)


def flex_attention_matches(inp: torch.Tensor, heads: int, hd: int, compile_mask: bool, flex_fn=None) -> dict:
    """Dense SDPA with doc_mask against flex_attention with the block mask, on random fp32 q, k, v of the run's own
    shapes and documents: outputs and gradients, largest deviation over all positions (a mask error at a single
    document boundary shows up as an O(0.1-1) deviation there). At initialisation the attention output does not
    reach the loss (the output projections start at zero), so the attention itself is compared."""
    from torch.nn.attention.flex_attention import flex_attention
    flex_fn = flex_fn or flex_attention
    B, T = inp.shape
    g = torch.Generator(device="cpu").manual_seed(0)
    q, k, v, w = (torch.randn(B, heads, T, hd, generator=g).to(inp.device) for _ in range(4))
    q, k, v = (t.requires_grad_() for t in (q, k, v))
    yd = F.scaled_dot_product_attention(q, k, v, attn_mask=doc_mask(inp))
    gd = torch.autograd.grad((yd * w).sum(), (q, k, v))
    yf = flex_fn(q, k, v, block_mask=flex_block_mask(inp, compile_mask))
    gf = torch.autograd.grad((yf * w).sum(), (q, k, v))
    tol = 1e-2 if inp.device.type == "cuda" else 1e-4     # CUDA: TF32 matmuls in both kernels
    out_err = float((yd - yf).abs().max())
    grad_err = max(float((a - b).abs().max()) / max(1e-6, float(a.abs().max())) for a, b in zip(gd, gf))
    return {"ok": bool(out_err <= tol and grad_err <= tol), "out_err": out_err, "grad_rel_err": grad_err, "tol": tol}


_ATTN: dict = {}                                       # this process's decision (the sweep's runs share it)


def time_microstep(step, n: int = 6, warm: int = 2) -> float:
    """Seconds per call of ``step`` (forward + backward of one micro-batch) on the GPU."""
    for _ in range(warm):
        step()
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(n):
        step()
    torch.cuda.synchronize()
    return (time.time() - t0) / n


def choose_attention(model, args, device, inp, run_step, out: Path) -> dict:
    """{'decision': 'flex' | 'dense', ...}: flex only on CUDA, compiled, torch ≥ FLEX_MIN_TORCH, when it matches the
    dense attention and a training micro-step is at least FLEX_MIN_GAIN faster. ``run_step(kind)`` runs one
    forward + backward with 'dense' or 'flex'. Decided once per process; kept in out/attention.json for later starts."""
    if "decision" in _ATTN:
        return _ATTN
    shape = [int(inp.shape[0]), int(inp.shape[1]), args.d, args.heads]
    rec = {"decision": "dense", "torch": torch.__version__, "shape": shape}
    path = out / "attention.json"
    cpu_test = device.type == "cpu" and os.environ.get("H100_FLEX_CPU") == "1"
    if not getattr(args, "flex", 1):
        rec["reason"] = "disabled (--flex 0)"
    elif cpu_test:                                     # smoke test: the flex path on the CPU, eager, no timing
        rec["match"] = flex_attention_matches(inp, args.heads, args.d // args.heads, compile_mask=False)
        rec["decision"] = "flex" if rec["match"]["ok"] else "dense"
        rec["reason"] = "CPU test mode (H100_FLEX_CPU=1)"
    elif device.type != "cuda" or not args.compile:
        rec["reason"] = "flex attention only on CUDA with torch.compile"
    elif torch_version() < FLEX_MIN_TORCH:
        rec["reason"] = f"torch {torch.__version__} < {FLEX_MIN_TORCH[0]}.{FLEX_MIN_TORCH[1]}"
    else:
        old = json.loads(path.read_text()) if path.exists() else {}
        if old.get("torch") == rec["torch"] and old.get("shape") == shape and old.get("decision") in ("flex", "dense"):
            _ATTN.update(old)
            log(f"attention: {old['decision']} (decided earlier: {old.get('reason', '')})")
            return _ATTN
        try:
            from torch.nn.attention.flex_attention import flex_attention
            rec["match"] = flex_attention_matches(inp, args.heads, args.d // args.heads, compile_mask=True,
                                                  flex_fn=torch.compile(flex_attention, dynamic=False))
            if not rec["match"]["ok"]:
                rec["reason"] = "flex attention differs from the dense attention"
            else:
                rec["s_per_microstep_dense"] = time_microstep(lambda: run_step("dense"))
                rec["s_per_microstep_flex"] = time_microstep(lambda: run_step("flex"))
                gain = 1 - rec["s_per_microstep_flex"] / rec["s_per_microstep_dense"]
                rec["gain"] = gain
                if gain >= FLEX_MIN_GAIN:
                    rec["decision"], rec["reason"] = "flex", f"matches the dense attention, {gain:.0%} faster"
                else:
                    rec["reason"] = f"only {gain:.0%} faster (needs {FLEX_MIN_GAIN:.0%})"
        except Exception as e:                         # any problem with the new path: stay on the reviewed one
            rec["decision"], rec["reason"] = "dense", f"flex check failed: {type(e).__name__}: {e}"[:400]
        finally:
            model.zero_grad(set_to_none=True)
            torch.cuda.empty_cache()
    _ATTN.update(rec)
    try:
        out.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rec, indent=1) + "\n")
    except OSError:
        pass
    log(f"attention: {rec['decision']} ({rec.get('reason', '')})")
    return _ATTN


def disable_flex(meta: dict, out: Path, why: str) -> None:
    """After a failure of the flex path: dense attention for the rest of this run and for later starts."""
    meta["attention"] = {"flex_disabled": why[:400], "at_step": meta["step"]}
    _ATTN.update({"decision": "dense", "reason": f"flex failed during training: {why}"[:400]})
    try:
        (out / "attention.json").write_text(json.dumps({k: v for k, v in _ATTN.items()}, indent=1) + "\n")
    except OSError:
        pass
    log(f"flex attention failed ({why[:200]}): continuing with the dense attention")


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
        """The epoch's documents in shuffled order, one array (the previous epoch's is released first)."""
        order = np.random.default_rng(self.seed + 7919 * self.epoch).permutation(len(self.lo))
        lens = self.hi - self.lo
        out = np.empty(int(lens.sum()) + 1, dtype=np.uint16)
        p = 0
        for d in order:
            k = int(lens[d])
            out[p:p + k] = self.tokens[self.lo[d]:self.hi[d]]
            p += k
        out[p] = 0
        self.stream = out
        self.pos = 0

    def peek(self, B: int, T: int) -> torch.Tensor:
        """The next batch without consuming it (checks must not shift the training data)."""
        s = self.stream[self.pos:self.pos + B * T + 1]
        if len(s) < B * T + 1:
            s = self.stream[:B * T + 1]
        x = np.lib.stride_tricks.sliding_window_view(s, T + 1)[::T][:B]
        return torch.from_numpy(x.astype(np.int64))

    def batch(self, B: int, T: int) -> torch.Tensor:
        if self.pos + B * T + 1 > len(self.stream):
            self.epoch += 1
            self.stream = None                                  # one copy in memory, not two
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
    extend = int(getattr(args, "extend_to", 0) or 0)
    if extend and not state_path.exists():
        raise SystemExit(f"--extend-to: no saved state {state_path} (wrong --ckpt-dir or --tag?)")
    meta = {"tokens": 0, "step": 0, "epoch": 0, "pos": 0, "train_seconds": 0.0, "total_tokens": args.total_tokens,
            "args": vars(args), "cfg": cfg, "next_eval": args.eval_every, "bad": 0}
    if state_path.exists():
        st = torch.load(state_path, map_location="cpu", weights_only=False)
        if st["meta"]["cfg"] != cfg:
            raise SystemExit(f"{state_path} belongs to a different configuration; move it away to start fresh")
        old_lr = st["meta"]["args"]["lr"]
        if old_lr != args.lr:
            if not getattr(args, "allow_lr_change", False):
                raise SystemExit(f"{state_path} was trained at lr {old_lr:g}, not {args.lr:g}; "
                                 f"pass --allow-lr-change 1 to continue it at the new rate")
            log(f"continuing {args.tag} from its last saved state at peak lr {args.lr:g} (was {old_lr:g})")
            st["meta"].setdefault("lr_changes", []).append({"tokens": st["meta"]["tokens"], "from": old_lr, "to": args.lr})
            st["meta"]["args"]["lr"] = args.lr
        if extend > st["meta"]["total_tokens"]:                # continuing a saved state (e.g. the pre-decay one)
            if not st["meta"].get("predecay") and st["meta"]["tokens"] / st["meta"]["total_tokens"] > 1 - args.decay_frac:
                raise SystemExit(f"{state_path} is already in its learning-rate decay; continue from the pre-decay "
                                 f"state (state_{args.tag}_predecay.pt, renamed to {state_path.name})")
            log(f"token target of {args.tag} raised from {st['meta']['total_tokens'] / 1e9:.3f} B to {extend / 1e9:.3f} B")
            st["meta"]["args"]["total_tokens"] = st["meta"]["total_tokens"] = extend
        st["meta"].pop("predecay", None)                       # later saves of this run are ordinary states
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
    attn, fwd_flex = "dense", None
    flex_cpu_test = not cuda and os.environ.get("H100_FLEX_CPU") == "1"
    fail_step = int(os.environ.get("H100_FLEX_FAIL_STEP", "-1"))   # smoke test: an injected failure of the flex path
    if (((cuda and compiled) or flex_cpu_test) and getattr(args, "flex", 1) and model.bigram is None
            and not (meta.get("attention") or {}).get("flex_disabled")):
        def flex_fwd(idx, block_mask):
            return flex_hidden(model, idx, block_mask)

        fwd_flex = torch.compile(flex_fwd, dynamic=False) if cuda else flex_fwd
        probe = data.peek(micro, args.ctx).to(device)
        p_inp, p_tgt = probe[:, :-1], probe[:, 1:]

        def run_step(kind):
            with torch.autocast(device.type, dtype=torch.bfloat16, enabled=args.bf16):
                hh = fwd_flex(p_inp, flex_block_mask(p_inp, cuda)) if kind == "flex" else fwd(p_inp, doc_mask(p_inp))
            ll = loss_fn(hh, model.head.weight, p_tgt, args.bf16) if fused else \
                chunked_loss(hh, model.head.weight, p_tgt, bf16=args.bf16)
            ll.backward()

        if choose_attention(model, args, device, p_inp, run_step, Path(args.out))["decision"] == "flex":
            attn = "flex"
        else:
            fwd_flex = None
        probe = p_inp = p_tgt = None
    start_step = meta["step"]
    Path(args.out).mkdir(parents=True, exist_ok=True)
    logf = open(Path(args.out) / f"train_log_{args.tag}.jsonl", "a")
    curve = Path(args.out) / f"curve_{args.tag}.jsonl"
    t_ck, t_rate, tok_rate = time.time(), time.time(), meta["tokens"]
    # time budget of this start: the earlier of --deadline and --budget-hours from now (checked on every start)
    ends = [x for x in (getattr(args, "deadline", 0) or 0,
                        time.time() + args.budget_hours * 3600 if args.budget_hours else 0) if x]
    end_by = min(ends) if ends else 0.0
    rate_from, rate_at = (int(x) for x in str(getattr(args, "budget_steps", "40,100")).split(","))
    checked = not end_by
    if end_by and time.time() >= end_by:
        if meta["tokens"] == 0:
            raise SystemExit("time budget used up before any training: nothing to evaluate")
        log("time budget already used up: no further training, final evaluation of the saved state")
        meta["total_tokens"] = meta["tokens"]
    predecay = ckdir / f"state_{args.tag}_predecay.pt"
    while meta["tokens"] < meta["total_tokens"]:
        total = meta["total_tokens"]
        frac = meta["tokens"] / total
        if (getattr(args, "save_predecay", 1) and meta["tokens"] > 0 and frac >= 1 - args.decay_frac
                and not predecay.exists()):                    # last state at the constant rate: continuable later
            atomic_save({"model": model.state_dict(), "opt": dense.state_dict(), "meta": {**meta, "predecay": True}},
                        predecay)
            log(f"pre-decay state saved at {meta['tokens'] / 1e9:.3f} B tokens: {predecay}")
        lr = L.lr_at(frac, meta["step"], args.lr, args.warmup, args.decay_frac)
        for g in dense.param_groups:
            g["lr"] = lr
        t0 = time.time()
        while True:                                            # one optimiser step, OOM-safe
            try:
                dense.zero_grad(set_to_none=True)
                n_micro = max(1, args.batch_tokens // (micro * args.ctx))
                loss_acc = torch.zeros((), dtype=torch.float32, device=device)   # summed on the device:
                for _ in range(n_micro):                                        # no host sync per micro-batch
                    batch = data.batch(micro, args.ctx)
                    if cuda:
                        batch = batch.pin_memory().to(device, non_blocking=True)
                    inp, tgt = batch[:, :-1], batch[:, 1:]
                    with torch.autocast(device.type, dtype=torch.bfloat16, enabled=args.bf16):
                        if attn == "flex":
                            if meta["step"] == fail_step:
                                raise RuntimeError("injected failure of the flex path (H100_FLEX_FAIL_STEP)")
                            h = fwd_flex(inp, flex_block_mask(inp, cuda))
                        else:
                            h = fwd(inp, doc_mask(inp))
                    if fused:
                        loss = loss_fn(h, model.head.weight, tgt, args.bf16) / n_micro
                    else:
                        loss = chunked_loss(h, model.head.weight, tgt, bf16=args.bf16) / n_micro
                    loss.backward()
                    loss_acc += loss.detach().float()
                loss_sum = float(loss_acc)
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
                if attn == "flex":                             # the new attention path first: back to the dense one
                    attn, fwd_flex = "dense", None
                    disable_flex(meta, Path(args.out), f"{type(e).__name__}: {e}")
                    continue
                if meta["step"] > start_step + 3 or not (compiled or fused):
                    raise
                log(f"step failed with compilation/fused loss ({type(e).__name__}: {e}); "
                    f"continuing eagerly with the chunked loss")
                compiled, fused, fwd = False, False, model.hidden
        gn = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        if not (math.isfinite(loss_sum) and math.isfinite(gn)) and attn == "flex":
            dense.zero_grad(set_to_none=True)                  # skip the update, repeat the step on the dense path
            attn, fwd_flex = "dense", None
            disable_flex(meta, Path(args.out), f"non-finite loss/gradient at step {meta['step']}")
            continue
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
        if not checked:
            if meta["step"] == start_step + rate_from:         # after compilation and warm-up of the kernels
                t_rate, tok_rate = time.time(), meta["tokens"]
            elif meta["step"] >= start_step + rate_at:
                checked = True
                rate = (meta["tokens"] - tok_rate) / max(1e-9, time.time() - t_rate)
                left = max(0.0, end_by - time.time())
                fit = int(meta["tokens"] + rate * left * 0.95)
                if fit < meta["total_tokens"]:
                    log(f"throughput {rate / 1e3:.0f} k tok/s, {left / 3600:.2f} h of time budget left: "
                        f"token budget cut from {meta['total_tokens'] / 1e9:.3f} B to {fit / 1e9:.3f} B")
                    meta["total_tokens"] = max(fit, meta["tokens"])
                else:
                    log(f"throughput {rate / 1e3:.0f} k tok/s: the remaining {(meta['total_tokens'] - meta['tokens']) / 1e9:.3f} "
                        f"B tokens fit into the {left / 3600:.2f} h of time budget left")
        if end_by and time.time() > end_by + 900 and meta["total_tokens"] > meta["tokens"]:
            log("time budget exceeded by 15 min: training stops here, final evaluation follows")   # cost guard
            meta["total_tokens"] = meta["tokens"]
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
            frac_now = meta["tokens"] / meta["total_tokens"]
            if end_by and checked and frac_now < REFIT_BELOW and time.time() > t_rate:
                # re-fit the token budget to the throughput measured so far (incl. curve evaluations), while the
                # rate is still constant: a slowdown found here no longer cuts the decay short at the deadline
                rate = (meta["tokens"] - tok_rate) / max(1e-9, time.time() - t_rate)
                fit = int(meta["tokens"] + rate * max(0.0, end_by - time.time()) * 0.95)
                fit = min(fit, int(args.total_tokens if not extend else max(args.total_tokens, extend)))
                fit = max(fit, int(meta["tokens"] / REFIT_FRAC_MAX) + 1)        # stays in the constant phase
                if abs(fit - meta["total_tokens"]) > REFIT_MIN_CHANGE * meta["total_tokens"]:
                    log(f"token budget re-fitted at {meta['tokens'] / 1e9:.3f} B ({rate / 1e3:.0f} k tok/s so far): "
                        f"{meta['total_tokens'] / 1e9:.3f} B -> {fit / 1e9:.3f} B")
                    meta.setdefault("refits", []).append({"tokens": meta["tokens"], "from": meta["total_tokens"], "to": fit,
                                                          "tok_per_s": rate})
                    meta["total_tokens"] = fit
            atomic_save({"model": model.state_dict(), "opt": dense.state_dict(), "meta": meta}, state_path)
            t_ck = time.time()
    logf.close()
    if getattr(args, "save_predecay", 1) and meta["tokens"] > 0 and not predecay.exists():
        # training ended at the constant rate (time budget): this state is the one to continue from
        atomic_save({"model": model.state_dict(), "opt": dense.state_dict(), "meta": {**meta, "predecay": True}}, predecay)
        log(f"training ended before the decay: continuable state saved: {predecay}")
    if meta["step"] > start_step or "loss_used" not in meta:   # what actually ran, after any fallback
        meta["loss_used"], meta["compiled_used"] = ("fused" if fused else "chunked"), compiled
        meta["attention_used"] = attn
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
                                  "warmup": args.sweep_warmup, "budget_hours": 0, "deadline": 0, "save_predecay": 0,
                                  "eval_every": 10 ** 18})
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
    if out.exists() and any(out.iterdir()):                    # leftovers would skip the steps the checks rely on
        if str(out) != SMOKE_OUT:
            raise SystemExit(f"smoke test: {out} must be empty (remove it first)")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    common = dict(cpu=True, d=64, layers=2, heads=2, ctx=128, batch_tokens=2048, micro_batch=8, beta2=0.95, wd=0.1,
                  decay_frac=0.3, seed=42, bf16=False, compile=False, loss="chunked", log_every=5, eval_docs=3, final_docs=3,
                  ckpt_minutes=1e9, data=str(TOK / "train"), data_limit=60_000, ckpt_dir=str(out / "ckpt"),
                  out=str(out), budget_hours=0, deadline=0, budget_steps="40,100", allow_lr_change=0, extend_to=0,
                  save_predecay=1, eval_every=40_000)
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
    pre = torch.load(Path(common["ckpt_dir"]) / "state_main_predecay.pt", map_location="cpu", weights_only=False)["meta"]
    if not (pre["predecay"] and 0.69 <= pre["tokens"] / pre["total_tokens"] < 0.72 + 2048 / pre["total_tokens"]):
        raise SystemExit(f"smoke test: pre-decay state at the wrong place ({pre['tokens']} of {pre['total_tokens']})")
    if saved["meta"]["epoch"] < 1:
        raise SystemExit("smoke test: the data stream never wrapped into a second epoch")
    # a resumed run continues from its state file without repeating work
    cmd_train(argparse.Namespace(**common, lr=0, tag="main", total_tokens=100_000, warmup=5, lrs="", sweep_tokens=0,
                                 sweep_warmup=0))
    # divergence path of the driver: a different learning rate only with explicit permission ...
    state = Path(common["ckpt_dir"]) / "state_main.pt"
    lr2 = json.loads((out / "sweep.json").read_text())["lr"] / 2
    more = dict(tag="main", warmup=5, lrs="", sweep_tokens=0, sweep_warmup=0)
    try:
        cmd_train(argparse.Namespace(**{**common, **more, "lr": lr2, "total_tokens": 200_000}))
    except SystemExit as e:
        if "allow-lr-change" not in str(e):
            raise
    else:
        raise SystemExit("smoke test: a changed learning rate was accepted without --allow-lr-change")
    # ... a state already in its decay cannot be extended ...
    try:
        cmd_train(argparse.Namespace(**{**common, **more, "lr": lr2, "total_tokens": 400_000, "allow_lr_change": 1,
                                        "extend_to": 400_000}))
    except SystemExit as e:
        if "already in its learning-rate decay" not in str(e):
            raise
    else:
        raise SystemExit("smoke test: a decayed state was extended")
    # ... the pre-decay state continues (renamed to state_main.pt, as in the guide); a deadline cuts that start
    pre_path = Path(common["ckpt_dir"]) / "state_main_predecay.pt"
    before = torch.load(pre_path, map_location="cpu", weights_only=False)["meta"]["tokens"]
    pre_path.replace(state)
    cmd_train(argparse.Namespace(**{**common, **more, "lr": lr2, "total_tokens": 400_000, "allow_lr_change": 1,
                                    "extend_to": 400_000, "deadline": time.time() + 2, "budget_steps": "2,4"}))
    m = torch.load(state, map_location="cpu", weights_only=False)["meta"]
    if not (before < m["tokens"] < 400_000 and m["total_tokens"] < 400_000 and m["lr_changes"][-1]["to"] == lr2
            and "predecay" not in m):
        raise SystemExit(f"smoke test: continuation / deadline cut failed (tokens {before} -> {m['tokens']}, "
                         f"budget {m['total_tokens']}, lr changes {m.get('lr_changes')})")
    if not pre_path.exists():
        raise SystemExit("smoke test: no continuable state after a run that ended before its decay")
    # an expired deadline: no further training, only the final evaluation of the saved state
    cmd_train(argparse.Namespace(**{**common, **more, "lr": lr2, "total_tokens": 400_000, "allow_lr_change": 1,
                                    "deadline": time.time() - 1}))
    if torch.load(state, map_location="cpu", weights_only=False)["meta"]["tokens"] != m["tokens"]:
        raise SystemExit("smoke test: training continued after the deadline")
    # refused: --extend-to without a saved state; an expired deadline without any training
    for extra, msg in (({"extend_to": 400_000}, "no saved state"), ({"deadline": time.time() - 1}, "nothing to evaluate")):
        try:
            cmd_train(argparse.Namespace(**{**common, **more, "tag": "nostate", "lr": lr2, "total_tokens": 400_000, **extra}))
        except SystemExit as e:
            if msg not in str(e):
                raise
        else:
            raise SystemExit(f"smoke test: expected a refusal ({msg})")
    # periodic re-fit of the token budget in the constant phase (deadline, a checkpoint after every step; the
    # 1 % threshold is lifted here so that the measured-rate noise of a CPU run triggers it)
    global REFIT_MIN_CHANGE
    keep_min, REFIT_MIN_CHANGE = REFIT_MIN_CHANGE, 0.0
    try:
        t_dl = time.time() + 120
        cmd_train(argparse.Namespace(**{**common, **more, "tag": "refit", "lr": lr2, "total_tokens": 300_000,
                                        "deadline": t_dl, "budget_steps": "2,4", "ckpt_minutes": 1e-5}))
    finally:
        REFIT_MIN_CHANGE = keep_min
    mr = torch.load(Path(common["ckpt_dir"]) / "state_refit.pt", map_location="cpu", weights_only=False)["meta"]
    if not (mr["tokens"] >= mr["total_tokens"] and mr["total_tokens"] <= 300_000 and mr.get("refits")):
        raise SystemExit(f"smoke test: re-fit run ended at {mr['tokens']} of {mr['total_tokens']} tokens, "
                         f"{len(mr.get('refits', []))} re-fits")
    for r in mr.get("refits", []):
        if not (r["to"] <= 300_000 and r["tokens"] / r["to"] < REFIT_FRAC_MAX and r["tokens"] / r["from"] < REFIT_BELOW):
            raise SystemExit(f"smoke test: a re-fit broke its limits: {r}")
    log(f"re-fit run: {len(mr.get('refits', []))} re-fits, {mr['tokens']} tokens")
    # block-sparse flex attention (PLAN §11, Nachtrag 16. Oktober): the maths on the CPU (eager) ...
    if torch_version() >= FLEX_MIN_TORCH:
        def with_boundaries(B_, T_, cuts):                  # real tokens, document starts (EOS) at given places
            x = Stream(Path(common["data"]), seed=1, limit=common["data_limit"]).batch(B_, T_)[:, :-1].clone()
            x[x == 0] = 1
            for row, cs in enumerate(cuts):
                x[row, cs] = 0
            return x
        for B_, T_, cuts in ((4, 128, ([0, 37], [90], [1, 2, 127], [64])),             # one 128-block
                             (2, 384, ([50, 127, 128, 333], [0, 255, 256, 257]))):       # several, across blocks
            m = flex_attention_matches(with_boundaries(B_, T_, cuts), 2, 32, compile_mask=False)
            if not m["ok"]:
                raise SystemExit(f"smoke test: flex attention differs from the dense attention ({B_}x{T_}): {m}")
        inp = with_boundaries(4, 128, ([0, 37], [90], [1, 2, 127], [64]))
        torch.manual_seed(0)
        tiny = L.LongGPT(64, 2, 2, 128, 0)
        with torch.no_grad():
            for prm in tiny.parameters():                  # also the zero-initialised projections and head
                prm.normal_(0.0, 0.05)
        w = torch.randn(4, 128, 64)
        hd = tiny.hidden(inp, doc_mask(inp))
        gd = torch.autograd.grad((hd * w).sum(), list(tiny.parameters()))
        hf = flex_hidden(tiny, inp, flex_block_mask(inp, False))
        gf = torch.autograd.grad((hf * w).sum(), list(tiny.parameters()))
        err = float((hd - hf).abs().max())
        gerr = max(float((a - b).abs().max()) / max(1e-6, float(a.abs().max())) for a, b in zip(gd, gf))
        if err > 1e-4 or gerr > 1e-4:
            raise SystemExit(f"smoke test: flex_hidden differs from LongGPT.hidden (out {err:.2e}, grad {gerr:.2e})")
        log(f"flex attention matches: attention out {m['out_err']:.1e}, grad {m['grad_rel_err']:.1e}; "
            f"model out {err:.1e}, grad {gerr:.1e}")
        # ... and training through it, plus the fallback to the dense path after a failure (CPU test mode)
        os.environ["H100_FLEX_CPU"] = "1"
        try:
            for tag, fail in (("flexrun", "-1"), ("flexfail", "6")):
                _ATTN.clear()
                (out / "attention.json").unlink(missing_ok=True)
                os.environ["H100_FLEX_FAIL_STEP"] = fail
                cmd_train(argparse.Namespace(**{**common, **more, "tag": tag, "lr": 1e-3, "total_tokens": 40_000,
                                                "bf16": False, "loss": "chunked", "compile": False}))
                mm = torch.load(Path(common["ckpt_dir"]) / f"model_{tag}.pt", map_location="cpu", weights_only=False)["meta"]
                want = "flex" if fail == "-1" else "dense"
                disabled = (mm.get("attention") or {}).get("flex_disabled")
                if mm["attention_used"] != want or bool(disabled) != (fail != "-1") or mm["tokens"] < 40_000:
                    raise SystemExit(f"smoke test: flex run '{tag}' used {mm['attention_used']} (expected {want}), "
                                     f"disabled={disabled}, tokens {mm['tokens']}")
            if json.loads((out / "attention.json").read_text())["decision"] != "dense":
                raise SystemExit("smoke test: the flex failure was not recorded in attention.json")
        finally:
            os.environ.pop("H100_FLEX_CPU", None)
            os.environ.pop("H100_FLEX_FAIL_STEP", None)
            _ATTN.clear()
    else:
        log(f"flex attention not checked: torch {torch.__version__} < {FLEX_MIN_TORCH}")
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
    p.add_argument("--budget-steps", default="40,100", help="throughput measured between these steps of a start")
    p.add_argument("--flex", type=int, default=1, help="1: block-sparse flex attention for training if it checks out")


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
    s.add_argument("--deadline", type=float, default=0)
    t = sub.add_parser("train")
    add_common(t)
    t.add_argument("--lr", type=float, default=0, help="0 = the sweep's choice (sweep.json)")
    t.add_argument("--tag", default="main")
    t.add_argument("--total-tokens", type=int, default=10_000_000_000)
    t.add_argument("--warmup", type=int, default=300)
    t.add_argument("--budget-hours", type=float, default=5.5, help="training of this start ends within this time")
    t.add_argument("--deadline", type=float, default=0, help="unix time by which training must end (0 = none)")
    t.add_argument("--allow-lr-change", type=int, default=0, help="1: continue a saved state at a different peak lr")
    t.add_argument("--extend-to", type=int, default=0, help="continue a saved state up to this many tokens in total")
    t.add_argument("--save-predecay", type=int, default=1, help="keep the last state before the decay (continuable)")
    t.add_argument("--eval-every", type=int, default=500_000_000)
    t.add_argument("--data", default=str(TOK / "h100" / "train_all"))
    e = sub.add_parser("eval")
    add_common(e)
    e.add_argument("--ckpt", required=True)
    e.add_argument("--tag", default="final")
    k = sub.add_parser("smoke")
    k.add_argument("--out", default=SMOKE_OUT)
    args = ap.parse_args()
    for flag in ("bf16", "compile"):                       # torch.autocast(enabled=...) accepts only a real bool
        if hasattr(args, flag):
            setattr(args, flag, bool(getattr(args, flag)))
    if args.cmd == "sweep":
        args.eval_every, args.tag, args.total_tokens, args.warmup, args.lr = 10 ** 18, "", 0, 0, 0
    {"sweep": cmd_sweep, "train": cmd_train, "eval": cmd_eval, "smoke": cmd_smoke}[args.cmd](args)


if __name__ == "__main__":
    main()
