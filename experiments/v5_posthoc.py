"""v5 run 3: the same post-hoc pipeline with the counter for every trained model.

For a trained model X (plain Transformer, or the logit-residual model) and the counter q:

  1. log-linear:  log p′(v) = b · log p_X(v) + a · log q(v) − log Z     (a, b by maximum
     likelihood on 24 windows of near-duplicate-filtered val-A; (a, b) = (0, 1) is X itself)
  2. linear:      P(y) = λ_bucket · pp(y) + (1 − λ_bucket) · p′(y)        (λ per gate-feature
     bucket, EM on filtered val-A, as in v5_residual)

Combining after training is exactly what the logit-residual model learns *during*
training, so "logres through the pipeline" against "plain through the pipeline" isolates
joint training. Writes results/v5/<run>/eval_<tag>_pipe.json and …_pipe_perdoc.npz.

    PYTHONPATH=/dev/shm/engramm/pt311:. .venv/bin/python -u -m experiments.v5_posthoc \\
        --ckpt /dev/shm/engramm/v5/ckpt_logres/ckpt_3h.pt --tag logres_3h --results run3
"""

from __future__ import annotations

import argparse
import json
import time

import numba
import numpy as np
import torch
import torch.nn.functional as F

from experiments import v5_residual as R
from experiments.v5_counter import load_counter
from experiments.v5_logres import LOGQ_FLOOR, assert_counter, logres_logits, make_model

FIT_WINDOWS = 24


def load_model(ck: dict):
    if ck["arm"] == "logres":
        m = make_model()
    else:
        m = R.GPT(R.gate_bias_for(ck["arm"]))
        sd = ck["model"]
        for k in ("gate_f.weight", "gate_c.weight"):
            sd.setdefault(k, torch.zeros_like(m.state_dict()[k]))
    m.load_state_dict(ck["model"])
    m.eval()
    return m


def windows(starts: np.ndarray, n_tokens: int):
    """(document, base, a, L) of every evaluation window (same scheme as token_logprobs)."""
    ends = np.append(starts[1:] - 1, n_tokens - 1)
    out = []
    for d in range(len(starts)):
        base = int(starts[d]) - 1
        n = int(ends[d]) + 1 - base
        done, a = 0, 0
        while done < n - 1:
            L = min(R.CTX, n - 1 - a)
            out.append((d, base, a, L, done))
            done = a + L
            a += R.CTX // 2
    return out


@torch.no_grad()
def full_logprobs(model, arm, tokens, feat_all, counter, pp_ev, base, a, L):
    """(log p_X, log q) over the whole vocabulary for the L targets of one window."""
    seq = torch.from_numpy(tokens[base + a:base + a + L + 1].astype(np.int64))[None]
    qbuf = np.empty((1, L, R.V), dtype=np.float32)
    q_t = counter.q(np.array([base + a], dtype=np.int64), L, qbuf)
    assert_counter(q_t[0], pp_ev[base + a:base + a + L])
    logq = torch.from_numpy(qbuf).clamp_min_(LOGQ_FLOOR).log_()[0]
    if arm == "logres":
        fb = torch.from_numpy(feat_all[base + a:base + a + L].astype(np.int64))[None]
        z, gl = model(seq[:, :-1], fb)
        lpx = F.log_softmax(logres_logits(z, gl, logq[None]), dim=-1)[0]
    else:
        z, _ = model(seq[:, :-1])
        lpx = F.log_softmax(z, dim=-1)[0]
    return lpx, logq, seq[0, 1:]


def fit_ab(samples) -> tuple[float, float]:
    """Maximum-likelihood (a, b) of log p′ = b·log p_X + a·log q − log Z."""
    ab = torch.tensor([0.0, 1.0], requires_grad=True)
    opt = torch.optim.LBFGS([ab], lr=1.0, max_iter=100, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        tot, n = 0.0, 0
        for lpx, lq, y in samples:
            comb = ab[1] * lpx + ab[0] * lq
            lp = comb.gather(1, y[:, None])[:, 0] - torch.logsumexp(comb, dim=1)
            tot = tot - lp.sum()
            n += len(y)
        loss = tot / n
        loss.backward()
        return loss

    opt.step(closure)
    return float(ab[0]), float(ab[1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--tag", required=True, help="output name, e.g. logres_3h or plain_run2_3h")
    ap.add_argument("--results", default="run3")
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    R.set_results(args.results)
    torch.set_num_threads(args.threads)
    numba.set_num_threads(args.threads)
    ck = torch.load(args.ckpt, map_location="cpu")
    arm = ck["arm"]
    model = load_model(ck)
    w = R.weights()
    base_counter = None
    data = {}
    for split in ("val_a", "test"):
        tokens, cols, feats = R.load_prior(split)
        counter = load_counter(split, base_counter)
        base_counter = base_counter or counter
        starts = np.load(R.TOK / f"{split}.starts.npy")
        nbytes = np.load(R.TOK / f"{split}.bytes.npy").astype(np.float64) + 1.0
        keep = R.keep_docs(split, len(starts))
        data[split] = (tokens, cols, feats, counter, starts, nbytes, keep)

    # 1. fit (a, b) on FIT_WINDOWS windows of filtered val-A (fixed seed)
    tokens, cols, feats, counter, starts, nbytes, keep = data["val_a"]
    feat_all = np.concatenate([feats, np.zeros((1, 3), dtype=np.int8)])
    pp_ev = R.prior_prob(cols, w).astype(np.float64)
    wins = [x for x in windows(starts, len(tokens)) if keep[x[0]] and x[3] == R.CTX]
    pick = np.random.default_rng(42).choice(len(wins), size=min(FIT_WINDOWS, len(wins)), replace=False)
    t0 = time.time()
    samples = []
    for j in sorted(pick):
        d, base, a, L, _ = wins[j]
        lpx, lq, y = full_logprobs(model, arm, tokens, feat_all, counter, pp_ev, base, a, L)
        samples.append((lpx, lq, y))
    a_fit, b_fit = fit_ab(samples)
    del samples
    res = {"arm": arm, "tag": args.tag, "ckpt": args.ckpt, "hours": ck["hours"], "tokens_seen": ck["tokens_seen"],
           "loglinear_a": a_fit, "loglinear_b": b_fit, "fit_windows": int(len(pick)), "fit_seconds": time.time() - t0}
    print(f"log-linear fit: a = {a_fit:.4f}, b = {b_fit:.4f}", flush=True)

    # 2. stream all windows of val-A and test
    per = {}
    for split in ("val_a", "test"):
        tokens, cols, feats, counter, starts, nbytes, keep = data[split]
        feat_all = np.concatenate([feats, np.zeros((1, 3), dtype=np.int8)])
        pp_ev = R.prior_prob(cols, w).astype(np.float64)
        n = len(tokens)
        p_x = np.zeros(n)
        p_ll = np.zeros(n)
        t0 = time.time()
        for d, base, a, L, done in windows(starts, n):
            lpx, lq, y = full_logprobs(model, arm, tokens, feat_all, counter, pp_ev, base, a, L)
            comb = b_fit * lpx + a_fit * lq
            lp_ll = comb.gather(1, y[:, None])[:, 0] - torch.logsumexp(comb, dim=1)
            lp_x = lpx.gather(1, y[:, None])[:, 0]
            first_new = done + 1 - (a + 1)
            gpos = base + a + 1 + np.arange(first_new, L)
            p_x[gpos] = np.exp(lp_x.numpy()[first_new:])
            p_ll[gpos] = np.exp(lp_ll.numpy()[first_new:])
        per[split] = {"p_x": p_x[1:], "p_ll": p_ll[1:], "pp": pp_ev, "ids": R.bucket_ids(feats),
                      "docs": R.target_docs(starts, n), "keep": keep, "nbytes": nbytes, "secs": time.time() - t0}
        print(f"{split}: {time.time() - t0:.0f} s", flush=True)

    v = per["val_a"]
    kept = v["keep"][v["docs"]]
    lam_x = R.fit_lambda(v["pp"][kept], v["p_x"][kept])
    lamb_x = R.fit_bucket_lambda(v["pp"][kept], v["p_x"][kept], v["ids"][kept], lam_x)
    lam_ll = R.fit_lambda(v["pp"][kept], v["p_ll"][kept])
    lamb_ll = R.fit_bucket_lambda(v["pp"][kept], v["p_ll"][kept], v["ids"][kept], lam_ll)
    perdoc = {}
    for split in ("val_a", "test"):
        e = per[split]
        variants = {
            "model_alone": e["p_x"],
            "prior_alone": e["pp"],
            "loglinear": e["p_ll"],
            "linear_bucket": lamb_x[e["ids"]] * e["pp"] + (1 - lamb_x[e["ids"]]) * e["p_x"],
            "pipeline": lamb_ll[e["ids"]] * e["pp"] + (1 - lamb_ll[e["ids"]]) * e["p_ll"],
        }
        n_docs = len(e["nbytes"])
        out = {"docs": n_docs, "docs_kept": int(e["keep"].sum()), "eval_seconds": e["secs"]}
        for name, p in variants.items():
            b = np.bincount(e["docs"], weights=-np.log2(np.maximum(p, R.EPS)), minlength=n_docs)
            perdoc[f"{split}_{name}"] = b
            out[f"bpb_{name}"] = float(b[e["keep"]].sum() / e["nbytes"][e["keep"]].sum())
            out[f"bpb_{name}_unfiltered"] = float(b.sum() / e["nbytes"].sum())
        perdoc[f"{split}_doc_bytes"] = e["nbytes"]
        perdoc[f"{split}_keep"] = e["keep"]
        res[split] = out
    R.RESULTS.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(R.RESULTS / f"eval_{args.tag}_pipe_perdoc.npz", **perdoc)
    (R.RESULTS / f"eval_{args.tag}_pipe.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1), flush=True)


if __name__ == "__main__":
    main()
