"""v5, variant 3: logit-residual training on the counting model's full distribution.

    p(w | x) ∝ exp(z_w(x) + α(x) · log q(w | x))

q is the pilot counting mixture over the whole vocabulary, computed exactly on the fly
(experiments/v5_counter.py); z is the Transformer's output; α = softplus(gate) ≥ 0 is the
learned, context-dependent trust in the counter (gate on the hidden state and the three
history-only count features of v5_residual; starts at α = 1). At initialisation z ≈ 0,
so the model *is* the counter, and unlike the mixture of run 1 the gradient on z
(p − one-hot) never vanishes: the network learns only the log-ratio correction the
counter needs (residual learning in the sense of Li et al. 2022).

Same Transformer, data region, seed, learning-rate schedule and evaluation as
experiments/v5_residual.py; measurements go to results/v5/<run>/.

    PYTHONPATH=/dev/shm/engramm/pt311:. .venv/bin/python -u -m experiments.v5_logres train --hours 3 --threads 2 --results run3
    PYTHONPATH=/dev/shm/engramm/pt311:. .venv/bin/python -u -m experiments.v5_logres eval --ckpt /dev/shm/engramm/v5/ckpt_logres/ckpt_3h.pt --results run3
"""

from __future__ import annotations

import argparse
import json
import math
import resource
import time

import numba
import numpy as np
import torch
import torch.nn.functional as F

from experiments import v5_residual as R
from experiments.v5_counter import load_counter

ARM = "logres"
ALPHA0_BIAS = math.log(math.e - 1.0)          # softplus(bias) = 1: start as the counter
LOGQ_FLOOR = 1e-30
PP_TOL = 1e-4                                  # q(target) must equal the component prior
SUM_TOL = 1e-3                                 # Σ_v q(v) must be 1


class CounterMismatch(RuntimeError):
    pass


def assert_counter(q_t: np.ndarray, pp: np.ndarray, rows: np.ndarray | None = None) -> None:
    """Abort if the on-the-fly counter disagrees with the component prior (or is not normalised)."""
    rel = np.abs(q_t - pp) / pp
    if rel.max() > PP_TOL:
        raise CounterMismatch(f"q(target) differs from the prior: max rel err {rel.max():.2e}")
    if rows is not None:
        sums = rows.sum(axis=-1, dtype=np.float64)
        if np.abs(sums - 1).max() > SUM_TOL:
            raise CounterMismatch(f"Σq deviates from 1 by {np.abs(sums - 1).max():.2e}")


def make_model() -> R.GPT:
    """The v5 Transformer with the final LayerNorm gain at 0: z = 0 and α = 1 at the start,
    so the untrained model is exactly the counter (random output logits would cost
    ≈ 0.03 bpb at step 0)."""
    m = R.GPT(ALPHA0_BIAS)
    torch.nn.init.zeros_(m.ln.weight)
    return m


def logres_logits(z: torch.Tensor, gate_logit: torch.Tensor, logq: torch.Tensor) -> torch.Tensor:
    return z + F.softplus(gate_logit).unsqueeze(-1) * logq


def train(args) -> None:
    R.set_results(args.results)
    torch.set_num_threads(args.threads)
    numba.set_num_threads(args.threads)
    torch.manual_seed(42)
    rng = np.random.default_rng(42)
    tokens, pp_all, feats = R.load_region()                # pp_all[i] = prior of tokens[i + 1]
    counter = load_counter("region")
    if not np.array_equal(counter.ev, tokens):
        raise SystemExit("counter stream and region tokens differ")
    model = make_model()
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1)
    out = R.out_dir(args.ckpt_dir or ARM)
    budget = args.hours * 3600
    t0, step, seen, paused = time.time(), 0, 0, 0.0
    marks = tuple(float(x) for x in args.checkpoints.split(",")) if args.checkpoints else R.CHECKPOINT_HOURS
    pending = sorted({h for h in marks if h <= args.hours} | {args.hours})
    log = open(out / "train_log.jsonl", "a")
    qbuf = np.empty((args.batch, R.CTX, R.V), dtype=np.float32)
    q_seconds = torch_seconds = 0.0
    while True:
        elapsed = time.time() - t0 - paused
        if pending and elapsed >= pending[0] * 3600:
            h = pending.pop(0)
            ck = {"model": model.state_dict(), "step": step, "tokens_seen": seen, "hours": h, "params": n_params,
                  "arm": ARM, "beta": None, "train_seconds": elapsed, "counter_seconds": q_seconds,
                  "bf16": bool(args.bf16)}
            torch.save(ck, out / f"ckpt_{h:g}h.pt")
            print(f"checkpoint {h:g} h: step {step}, {seen} tokens", flush=True)
            if args.eval_at_checkpoints:
                te = time.time()
                model.eval()
                run_eval(model, ck, args.threads, args.eval_docs, counter)
                model.train()
                paused += time.time() - te
            continue
        if elapsed >= budget:
            break
        lr = args.lr * min(1.0, (step + 1) / 500) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1.0, elapsed / budget))))
        for g in opt.param_groups:
            g["lr"] = lr
        starts = rng.integers(0, len(tokens) - R.CTX - 1, size=args.batch)
        batch = torch.from_numpy(np.stack([tokens[s:s + R.CTX + 1] for s in starts]).astype(np.int64))
        tgt = batch[:, 1:]
        fb = torch.from_numpy(np.stack([feats[s:s + R.CTX] for s in starts]).astype(np.int64))
        tq = time.time()
        q_t = counter.q(starts, R.CTX, qbuf)              # targets s+1 … s+CTX, the batch's targets
        assert_counter(q_t, np.stack([pp_all[s:s + R.CTX] for s in starts]).astype(np.float64),
                       qbuf if step % 10 == 0 else None)
        q_seconds += time.time() - tq
        tt = time.time()
        logq = torch.from_numpy(qbuf).clamp_min_(LOGQ_FLOOR).log_()
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=bool(args.bf16)):
            z, gl = model(batch[:, :-1], fb)
        z, gl = z.float(), gl.float()                   # residual, softmax and loss always in fp32
        logits = logres_logits(z, gl, logq)
        loss = F.cross_entropy(logits.reshape(-1, R.V), tgt.reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        torch_seconds += time.time() - tt
        step += 1
        seen += args.batch * R.CTX
        if step % 100 == 0:
            with torch.no_grad():
                net_loss = float(F.cross_entropy(z.reshape(-1, R.V), tgt.reshape(-1)))
                al = F.softplus(gl).flatten()
                alpha_q = [float(x) for x in torch.quantile(al, torch.tensor([0.1, 0.5, 0.9]))]
            rec = {"step": step, "loss": float(loss), "net_only_loss": net_loss,
                   "counter_loss": float(-np.log(np.maximum(q_t, R.EPS)).mean()),
                   "alpha_p10_p50_p90_max": alpha_q + [float(al.max())], "lr": lr,
                   "elapsed_s": time.time() - t0, "tokens_seen": seen, "counter_seconds": q_seconds,
                   "torch_seconds": torch_seconds,
                   "rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print(rec, flush=True)


@torch.no_grad()
def token_logprobs(model, counter, tokens, starts, feat_all, pp_ev):
    """Per target position (global index i ≥ 1): log p of the logit-residual model, of the
    network alone, and the trust α. Same windows as v5_residual.token_logprobs; ``tokens``
    may be a document-aligned prefix of the counter's stream (smoke tests); ``pp_ev[i]`` is
    the component prior of target i + 1 (checked against q on every window)."""
    ends = np.append(starts[1:] - 1, len(tokens) - 1)
    lp_out = np.zeros(len(tokens))
    lpn_out = np.zeros(len(tokens))
    al_out = np.zeros(len(tokens))
    qbuf = np.empty((1, R.CTX, R.V), dtype=np.float32)
    for d in range(len(starts)):
        base = starts[d] - 1
        seq = tokens[base:ends[d] + 1].astype(np.int64)          # EOS, doc, EOS
        n = len(seq)
        done, a = 0, 0
        while done < n - 1:
            window = torch.from_numpy(seq[a:a + R.CTX + 1])[None]
            L = window.shape[1] - 1
            fb = torch.from_numpy(feat_all[base + a:base + a + L].astype(np.int64))[None]
            q_t = counter.q(np.array([base + a], dtype=np.int64), L, qbuf[:, :L])
            assert_counter(q_t[0], pp_ev[base + a:base + a + L])
            logq = torch.from_numpy(qbuf[:, :L]).clamp_min(LOGQ_FLOOR).log()
            z, gl = model(window[:, :-1], fb)
            tgt = window[0, 1:]
            idx = torch.arange(L)
            lp = F.log_softmax(logres_logits(z, gl, logq), dim=-1)[0][idx, tgt].numpy()
            lpn = F.log_softmax(z, dim=-1)[0][idx, tgt].numpy()
            first_new = done + 1 - (a + 1)
            gpos = base + a + 1 + np.arange(first_new, L)
            lp_out[gpos] = lp[first_new:]
            lpn_out[gpos] = lpn[first_new:]
            al_out[gpos] = F.softplus(gl[0]).numpy()[first_new:]
            done = a + L
            a += R.CTX // 2
    return lp_out, lpn_out, al_out


def run_eval(model, ck: dict, threads: int, max_docs: int = 0, base=None) -> dict:
    torch.set_num_threads(threads)
    numba.set_num_threads(threads)
    res = {"arm": ARM, "hours": ck["hours"], "step": ck["step"], "tokens_seen": ck["tokens_seen"],
           "params": ck["params"], "train_seconds": ck.get("train_seconds"),
           "counter_seconds": ck.get("counter_seconds"), "threads": threads, "max_docs": max_docs,
           "torch": torch.__version__}
    w = R.weights()
    res["prior_weights"] = w.tolist()
    per = {}
    for split in ("val_a", "test"):
        tokens, cols, feats = R.load_prior(split)
        counter = load_counter(split, base)
        starts = np.load(R.TOK / f"{split}.starts.npy")
        nbytes = np.load(R.TOK / f"{split}.bytes.npy")
        if max_docs:
            starts, nbytes = starts[:max_docs], nbytes[:max_docs]
            cut = int(starts[-1]) + int(np.argmax(tokens[starts[-1]:] == 0)) + 1
            tokens, cols, feats = tokens[:cut], cols[:cut - 1], feats[:cut - 1]
        feat_all = np.concatenate([feats, np.zeros((1, 3), dtype=np.int8)])
        t0 = time.time()
        pp_ev = R.prior_prob(cols, w).astype(np.float64)
        lp, lpn, al = token_logprobs(model, counter, tokens, starts, feat_all, pp_ev)
        n = len(tokens)
        docs = R.target_docs(starts, n)
        keep = R.keep_docs(split, len(np.load(R.TOK / f"{split}.starts.npy")))[:len(starts)]
        per[split] = {"p": np.exp(lp[1:n]), "p_net": np.exp(lpn[1:n]), "alpha": al[1:n],
                      "pp": R.prior_prob(cols, w).astype(np.float64), "ids": R.bucket_ids(feats), "docs": docs,
                      "keep": keep, "nbytes": nbytes.astype(np.float64) + 1.0, "secs": time.time() - t0}
    v = per["val_a"]
    kept = v["keep"][v["docs"]]
    lam = R.fit_lambda(v["pp"][kept], v["p"][kept])
    lam_b = R.fit_bucket_lambda(v["pp"][kept], v["p"][kept], v["ids"][kept], lam)
    res["posthoc_lambda"] = lam
    perdoc = {}
    for split in ("val_a", "test"):
        e = per[split]
        lb = lam_b[e["ids"]]
        variants = {
            "net_alone": e["p_net"],
            "prior_alone": e["pp"],
            "logres": e["p"],
            "posthoc_bucket_mix": lb * e["pp"] + (1 - lb) * e["p"],
        }
        n_docs = len(e["nbytes"])
        out = {"docs": n_docs, "docs_kept": int(e["keep"].sum()), "eval_seconds": e["secs"],
               "mean_alpha": float(e["alpha"].mean())}
        for name, p in variants.items():
            b = np.bincount(e["docs"], weights=-np.log2(np.maximum(p, R.EPS)), minlength=n_docs)
            perdoc[f"{split}_{name}"] = b
            out[f"bpb_{name}"] = float(b[e["keep"]].sum() / e["nbytes"][e["keep"]].sum())
            out[f"bpb_{name}_unfiltered"] = float(b.sum() / e["nbytes"].sum())
        perdoc[f"{split}_doc_bytes"] = e["nbytes"]
        perdoc[f"{split}_keep"] = e["keep"]
        res[split] = out
    R.RESULTS.mkdir(parents=True, exist_ok=True)
    tag = f"{ck['hours']:g}h" if not max_docs else f"{ck['hours']:g}h_smoke"
    np.savez_compressed(R.RESULTS / f"eval_{ARM}_{tag}_perdoc.npz", **perdoc)
    (R.RESULTS / f"eval_{ARM}_{tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1), flush=True)
    return res


def evaluate(args) -> None:
    R.set_results(args.results)
    ck = torch.load(args.ckpt, map_location="cpu")
    model = make_model()
    model.load_state_dict(ck["model"])
    model.eval()
    run_eval(model, ck, args.threads, args.max_docs)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--hours", type=float, default=3)
    t.add_argument("--threads", type=int, default=2)
    t.add_argument("--batch", type=int, default=16)
    t.add_argument("--lr", type=float, default=1e-3)
    t.add_argument("--eval-at-checkpoints", type=int, default=1)
    t.add_argument("--eval-docs", type=int, default=0)
    t.add_argument("--checkpoints", default="")
    t.add_argument("--results", default="run3")
    t.add_argument("--ckpt-dir", default="")
    t.add_argument("--bf16", type=int, default=0, help="bf16 autocast for the matrix products (AMX); loss in fp32")
    e = sub.add_parser("eval")
    e.add_argument("--ckpt", required=True)
    e.add_argument("--threads", type=int, default=4)
    e.add_argument("--max-docs", type=int, default=0)
    e.add_argument("--results", default="run3")
    args = ap.parse_args()
    train(args) if args.cmd == "train" else evaluate(args)


if __name__ == "__main__":
    main()
