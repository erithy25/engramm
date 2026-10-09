"""Messart C: the Transformer size series, the learning-rate choice on val-B, and the fit.

(docs/PREREG_PARAMS.md §6.) Two commands:

    python -m experiments.params_c drive [--with-s6]   # all runs of the registered plan, restartable
    python -m experiments.params_c fit                 # N*, bootstrap interval, sensitivity, compute

``drive`` runs in the main environment and starts every training and evaluation as a
subprocess in the torch environment (``.venv_b1``). It is restart-safe: a run with a
``final.pt`` is skipped, a run with a ``resume.pt`` continues bit-identically, an
evaluation with an output file is skipped. Order (§6.5): sweeps S0–S4 → final runs seed 42
(S0–S5) → final runs seed 7 (S0–S4). No fit is computed while it runs.

Outputs: checkpoints in ``models/params/<run>/`` (not versioned), evaluations and the
learning-rate choices in ``data/cache/params/c/`` (copied to ``results/params/c/`` when the
series is complete), the fit as ``results/params/c_fit_<stamp>.json``.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from data.lm_corpus import split_half
from engramm.repro import git_revision, python_files_changed_since
from experiments.params_common import ENGRAMM_LM, GRID, PARAMS, REPO, RESULTS, WORK, write_record

TORCH_PY = REPO / ".venv_b1" / "bin" / "python"
TRAINER = REPO / "experiments" / "lm_transformer.py"
MODELS = REPO / "models" / "params"
CDIR = WORK / "c"
LOG = WORK / "c_drive.log"

BATCH, CTX = 16, 256
THREADS = 4
LR_GRID = (1e-3, 2e-3, 4e-3)
EDGE = {1e-3: 5e-4, 4e-3: 8e-3}
TIE = 1e-4
SWEEP_SIZES = ("S0", "S1", "S2", "S3", "S4")
SEED_SWEEP = 42
FINAL_SEEDS = {"S0": (42, 7), "S1": (42, 7), "S2": (42, 7), "S3": (42, 7), "S4": (42, 7), "S5": (42,)}
BOOT_REPS, BOOT_SEED = 2000, 42
#: Throughput guard (Auftraggeber, 2026-10-09): a run more than 25 % below the §6.6 probe pauses.
PROBE = REPO / "results" / "params" / "probe_throughput_chunked_20261008T193349Z.json"
GUARD = 0.75
PAUSED = CDIR / "PAUSED.json"


class Paused(Exception):
    pass


def probe_tps() -> dict:
    rows = json.loads(PROBE.read_text())["rows"]
    return {r["size"]: r["tokens_per_s"] for r in rows if r["threads"] == THREADS and r["chunked_loss"]}


def say(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def run_name(size: str, lr: float, seed: int, sweep: bool) -> str:
    return f"{size}_lr{lr:g}_s{seed}_{'q' if sweep else 'f'}"


def eval_path(run: str, split: str) -> Path:
    return CDIR / f"{run}_{split}.json"


# ---------------------------------------------------------------------------
# drive
# ---------------------------------------------------------------------------

def _train(size: str, lr: float, seed: int, sweep: bool, out: Path) -> int:
    d, layers, heads = GRID[size]
    tokens = (5 if sweep else 20) * PARAMS[size][0]
    cmd = [str(TORCH_PY), "-u", str(TRAINER), "train-tokens", "--d", str(d), "--layers", str(layers),
           "--heads", str(heads), "--tokens", str(tokens), "--seed", str(seed), "--lr", repr(lr),
           "--batch", str(BATCH), "--threads", str(THREADS), "--chunked",
           "--min-tps", f"{GUARD * probe_tps()[size]:.1f}", "--out", str(out)]
    with open(out.parent / f"{out.name}.log", "a") as log:
        return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=REPO).returncode


def ensure_trained(size: str, lr: float, seed: int, sweep: bool) -> bool:
    """True when the run has a final checkpoint; failures are recorded, never hidden (§10)."""
    run = run_name(size, lr, seed, sweep)
    out = MODELS / run
    if (out / "final.pt").exists():
        return True
    out.parent.mkdir(parents=True, exist_ok=True)
    attempts = 1 if sweep else 2
    if (CDIR / f"{run}_failed_attempt{attempts}.json").exists():
        return False                                            # already failed as often as allowed
    for attempt in range(1, attempts + 1):
        if (CDIR / f"{run}_failed_attempt{attempt}.json").exists():
            continue
        say(f"train {run} (attempt {attempt}){' resuming' if (out / 'resume.pt').exists() else ''}")
        t0 = time.time()
        rc = _train(size, lr, seed, sweep, out)
        if rc == 3:                                             # throughput guard: pause, report, do not go on
            info = json.loads((out / "paused_throughput.json").read_text())
            PAUSED.write_text(json.dumps({"run": run, **info}) + "\n")
            say(f"PAUSED {run}: {info['tokens_per_s']:.0f} tokens/s < {info['min_tokens_per_s']:.0f}")
            raise Paused(run)
        if rc == 0 and (out / "final.pt").exists():
            say(f"trained {run} in {time.time() - t0:.0f} s")
            return True
        say(f"FAILED {run} (attempt {attempt}, exit {rc})")
        (CDIR / f"{run}_failed_attempt{attempt}.json").write_text(json.dumps({"run": run, "exit": rc}))
        if attempt < attempts:                                  # identical restart from scratch
            out.rename(out.with_name(f"{run}_failed{attempt}"))
    return False


def ensure_eval(run: str, split: str) -> Path | None:
    dest = eval_path(run, split)
    if dest.exists():
        return dest
    ck = MODELS / run / "final.pt"
    if not ck.exists():
        return None
    say(f"eval {run} on {split}")
    cmd = [str(TORCH_PY), "-u", str(TRAINER), "eval", "--ckpt", str(ck), "--split", split,
           "--threads", str(THREADS), "--out", str(dest)]
    with open(MODELS / f"{run}.log", "a") as log:
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=REPO).returncode
    if rc != 0:
        raise RuntimeError(f"evaluation of {run} on {split} failed ({rc})")
    return dest


def _masks(split: str, keys: list) -> tuple[np.ndarray, np.ndarray]:
    d = json.loads((REPO / "results" / "lm" / "dedup.json").read_text())["splits"][split]
    keep = np.ones(len(keys), dtype=bool)
    keep[d["excluded"]] = False
    half0 = np.array([split_half(s, k) == 0 for s, k in keys], dtype=bool)
    return keep, half0


def val_b_h1(path: Path) -> float:
    e = json.loads(path.read_text())
    bits, nb = np.array(e["per_doc_bits"]), np.array(e["doc_bytes"])
    keep, half0 = _masks("val_b", e["keys"])
    m = keep & half0
    return float(bits[m].sum() / nb[m].sum())


def select(size: str) -> float:
    """Learning rate of ``size`` from its ¼-budget sweep on val-B half 1 (§6.4)."""
    dest = CDIR / f"select_{size}.json"
    if dest.exists():
        return json.loads(dest.read_text())["chosen_lr"]
    cands = list(LR_GRID)
    scores = {}

    def score(lr):
        run = run_name(size, lr, SEED_SWEEP, True)
        if not ensure_trained(size, lr, SEED_SWEEP, True):
            return math.inf                                      # a failed candidate loses (§10)
        return val_b_h1(ensure_eval(run, "val_b"))

    for lr in cands:
        scores[lr] = score(lr)

    def best(sc):
        m = min(sc.values())
        if not math.isfinite(m):
            raise RuntimeError(f"{size}: every learning-rate candidate failed")
        return min(lr for lr, v in sc.items() if v <= m + TIE)       # within the tie band: smaller lr

    first = best(scores)
    extended = None
    if first in EDGE:
        extended = EDGE[first]
        scores[extended] = score(extended)
    chosen = best(scores)
    rec = {"size": size, "criterion": "BPB val-B half 1, near-duplicate filtered", "tie": TIE,
           "scores": {repr(k): v for k, v in sorted(scores.items())}, "first_choice": first,
           "edge_extension": extended, "chosen_lr": chosen}
    dest.write_text(json.dumps(rec, indent=1) + "\n")
    say(f"selected {size}: lr {chosen} ({rec['scores']})")
    return chosen


def drive(args) -> None:
    CDIR.mkdir(parents=True, exist_ok=True)
    if PAUSED.exists():
        raise SystemExit(f"paused by the throughput guard ({PAUSED.read_text().strip()}); "
                         "remove the marker only after the Auftraggeber has decided")
    try:
        _drive(args)
    except Paused:
        say("drive paused")
        raise SystemExit(3)


def _drive(args) -> None:
    start = git_revision()
    say(f"drive start at commit {start.get('commit')} dirty={start.get('dirty')}")
    marker = CDIR / "drive_start.json"
    if not marker.exists():
        marker.write_text(json.dumps({"git": start, "with_s6": args.with_s6}) + "\n")
    chosen = {s: select(s) for s in SWEEP_SIZES}
    chosen["S5"] = chosen["S6"] = chosen["S4"]
    seeds = dict(FINAL_SEEDS)
    if args.with_s6:
        seeds["S6"] = (42,)
    for phase_seed in (42, 7):
        for size, ss in seeds.items():
            if phase_seed not in ss:
                continue
            if ensure_trained(size, chosen[size], phase_seed, False):
                run = run_name(size, chosen[size], phase_seed, False)
                ensure_eval(run, "test")
                ensure_eval(run, "val_b")
    say("drive complete")


# ---------------------------------------------------------------------------
# fit
# ---------------------------------------------------------------------------

def powerlaw(n: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """ln y = c − α ln n by least squares; returns (c, α, R²)."""
    x, ly = np.log(n), np.log(y)
    A = np.stack([np.ones_like(x), -x], axis=1)
    (c, alpha), *_ = np.linalg.lstsq(A, ly, rcond=None)
    pred = A @ np.array([c, alpha])
    ss = float(((ly - ly.mean()) ** 2).sum())
    return float(c), float(alpha), 1.0 - float(((ly - pred) ** 2).sum()) / ss if ss > 0 else float("nan")


def n_star(c: float, alpha: float, target: float) -> float:
    return math.exp((c - math.log(target)) / alpha) if alpha > 0 else float("nan")


def local_interp(n: np.ndarray, y: np.ndarray, target: float) -> float | None:
    order = np.argsort(n)
    n, y = n[order], y[order]
    for i in range(len(n) - 1):
        if (y[i] - target) * (y[i + 1] - target) <= 0 and y[i] != y[i + 1]:
            t = (math.log(target) - math.log(y[i])) / (math.log(y[i + 1]) - math.log(y[i]))
            return math.exp(math.log(n[i]) + t * (math.log(n[i + 1]) - math.log(n[i])))
    return None


def saturating(n: np.ndarray, y: np.ndarray, target: float) -> dict:
    """bpb = E + a·N^(−α), E ≥ 0: grid over E, log-linear fit of (bpb − E) for each E."""
    best = None
    for E in np.linspace(0.0, float(y.min()) * 0.999, 2000):
        c, alpha, _ = powerlaw(n, y - E)
        pred = E + np.exp(c - alpha * np.log(n))
        sse = float(((y - pred) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, E, c, alpha)
    sse, E, c, alpha = best
    ns = math.exp((c - math.log(target - E)) / alpha) if target > E and alpha > 0 else float("nan")
    return {"E": E, "c": c, "alpha": alpha, "sse": sse, "n_star": ns,
            "E_at_bound": bool(E == 0.0 or E >= float(y.min()) * 0.998)}


def fit(args) -> None:
    git_state, t0 = git_revision(), time.time()
    eng_path = Path(args.engramm) if args.engramm else sorted(RESULTS.glob("c_engramm_test_*.json"))[-1]
    eng = json.loads(eng_path.read_text())
    keys = [tuple(k) for k in eng["keys"]]
    nb = np.array(eng["doc_bytes"])
    keep = np.array(eng["keep"], dtype=bool)
    targets = {"engramm": np.array(eng["per_doc_bits"])}
    for name, bits in eng.get("secondary_per_doc_bits", {}).items():
        targets[name] = np.array(bits)
    edir = Path(args.eval_dir)

    runs = {}
    for size in GRID:
        sel = edir / f"select_{size}.json"
        lr = json.loads(sel.read_text())["chosen_lr"] if sel.exists() else None
        for f in sorted(edir.glob(f"{size}_lr*_f_test.json")):
            e = json.loads(f.read_text())
            if [tuple(k) for k in e["keys"]] != keys:
                raise SystemExit(f"{f}: document order differs from the ENGRAMM record")
            runs.setdefault(size, []).append({"file": f.name, "seed": e["seed"], "lr": e["lr"],
                                              "bits": np.array(e["per_doc_bits"]),
                                              "train_wall_seconds": e.get("train_wall_seconds"),
                                              "tokens_seen": e["tokens_seen"]})
        if size in runs and lr is not None:
            assert all(r["lr"] == lr for r in runs[size]), f"{size}: final run with an unselected learning rate"
    sizes = [s for s in GRID if s in runs]
    n_tot = np.array([PARAMS[s][0] for s in sizes], dtype=float)
    n_ne = np.array([PARAMS[s][1] for s in sizes], dtype=float)

    def bpb_of(bits, m):
        return float(bits[m].sum() / nb[m].sum())

    def size_bpb(m, pick=None):
        out = []
        for i, s in enumerate(sizes):
            rs = runs[s] if pick is None else [runs[s][j] for j in pick[i]]
            out.append(np.mean([bpb_of(r["bits"], m) for r in rs]))
        return np.array(out)

    y = size_bpb(keep)
    target = {k: bpb_of(v, keep) for k, v in targets.items()}
    c, alpha, r2 = powerlaw(n_tot, y)
    ns = n_star(c, alpha, target["engramm"])
    c2, a2, r2b = powerlaw(n_ne, y)
    lo_n, hi_n = float(n_tot.min()), float(n_tot.max())

    def extrap(v):
        if not math.isfinite(v):
            return {"status": "undefined"}
        if v > hi_n:
            return {"status": "extrapolation", "factor": v / hi_n, "direction": "above"}
        if v < lo_n:
            return {"status": "extrapolation", "factor": lo_n / v, "direction": "below"}
        return {"status": "interpolation"}

    # bootstrap: documents paired across all systems, seeds resampled within each size
    rng = np.random.default_rng(BOOT_SEED)
    idx_all = np.flatnonzero(keep)
    boot, boot_ne, outside = [], [], 0
    for _ in range(BOOT_REPS):
        di = idx_all[rng.integers(0, len(idx_all), size=len(idx_all))]
        pick = [rng.integers(0, len(runs[s]), size=len(runs[s])) for s in sizes]
        yb = np.array([np.mean([runs[s][j]["bits"][di].sum() / nb[di].sum() for j in pick[i]])
                       for i, s in enumerate(sizes)])
        tb = targets["engramm"][di].sum() / nb[di].sum()
        cb, ab, _ = powerlaw(n_tot, yb)
        v = n_star(cb, ab, tb)
        boot.append(v)
        outside += int(not (lo_n <= v <= hi_n)) if math.isfinite(v) else 1
        cb2, ab2, _ = powerlaw(n_ne, yb)
        boot_ne.append(n_star(cb2, ab2, tb))
    boot, boot_ne = np.array(boot), np.array(boot_ne)
    ci = [float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5))]
    ci_ne = [float(np.nanpercentile(boot_ne, 2.5)), float(np.nanpercentile(boot_ne, 97.5))]

    unf = np.ones_like(keep)
    y_unf = size_bpb(unf)
    cu, au, _ = powerlaw(n_tot, y_unf)
    sens = {
        "local_interpolation": local_interp(n_tot, y, target["engramm"]),
        "fit_nonembedding": {"c": c2, "alpha": a2, "r2": r2b, "n_star_nonemb": n_star(c2, a2, target["engramm"]),
                             "ci95": ci_ne},
        "saturating": saturating(n_tot, y, target["engramm"]) if len(sizes) >= 4 else None,
        "unfiltered": {"engramm_bpb": bpb_of(targets["engramm"], unf), "bpb_per_size": dict(zip(sizes, y_unf.tolist())),
                       "n_star": n_star(cu, au, bpb_of(targets["engramm"], unf))},
        "secondary_targets": {k: {"bpb": v, "n_star": n_star(c, alpha, v), **extrap(n_star(c, alpha, v))}
                              for k, v in target.items() if k != "engramm"},
    }
    # compute (§6.12): FLOPs 6·N·D; container wall time of the final runs, interpolated at N*
    walls = {s: [r["train_wall_seconds"] for r in runs[s] if r["train_wall_seconds"]] for s in sizes}
    wmean = np.array([np.mean(walls[s]) if walls[s] else np.nan for s in sizes])
    ok = np.isfinite(wmean)
    hours_at = None
    if ok.sum() >= 2 and math.isfinite(ns):
        cw, aw, _ = powerlaw(n_tot[ok], wmean[ok])
        hours_at = math.exp(cw - aw * math.log(ns)) / 3600
    compute = {"train_flops_at_n_star": 6 * ns * 20 * ns if math.isfinite(ns) else None,
               "container_hours_at_n_star": hours_at,
               "container_hours_per_size": {s: (float(np.mean(walls[s])) / 3600 if walls[s] else None) for s in sizes},
               "engramm_build_seconds_m4": 544, "engramm_build_record_m4": "results/lm/p5_device_main_20260926T161917Z.json",
               "engramm_build_seconds_container": 566,
               "note": "container times are not official (PROTOCOL rule 2); the transformer was not timed on the M4"}
    out = {"subject": ENGRAMM_LM, "code_changed_since_drive_start": None,
           "sizes": {s: {"params": PARAMS[s][0], "params_nonemb": PARAMS[s][1], "bpb_seed_mean": float(y[i]),
                         "runs": [{k: v for k, v in r.items() if k != "bits"} | {"bpb": bpb_of(r["bits"], keep)}
                                  for r in runs[s]]}
                     for i, s in enumerate(sizes)},
           "engramm_bpb": target["engramm"],
           "fit": {"form": "ln bpb = c − α ln N (N = total parameters)", "c": c, "alpha": alpha, "r2": r2,
                   "residuals": (np.log(y) - (c - alpha * np.log(n_tot))).tolist()},
           "n_star": ns, "ci95": ci, "bootstrap": {"replicates": BOOT_REPS, "seed": BOOT_SEED,
                                                    "share_outside_measured_range": outside / BOOT_REPS,
                                                    "undefined": int(np.isnan(boot).sum())},
           **extrap(ns), "measured_range": [lo_n, hi_n], "sensitivity": sens, "compute": compute,
           "external_references": {"gpt2_small": {"bpb": 1.038792450096114, "params": 124_000_000,
                                                  "record": "results/lm/test_eval_20260926T183702Z.json",
                                                  "in_fit": False},
                                   "e12_transformer_6h": {"bpb": 1.6376495826221305, "in_fit": False,
                                                          "reason": "time budget, unannealed, ~1.1 tokens/param"}}}
    out["engramm_record"] = str(eng_path)
    start = edir / "drive_start.json"
    if start.exists():
        commit = json.loads(start.read_text())["git"].get("commit")
        out["code_changed_since_drive_start"] = python_files_changed_since(commit)
    print(json.dumps({"n_star": ns, "ci95": ci, "alpha": alpha, "r2": r2, "bpb": dict(zip(sizes, y.tolist())),
                      "engramm": target["engramm"], **extrap(ns)}, indent=1), flush=True)
    print(write_record("c_fit", out, t0, git_state, Path(args.out_dir)), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("drive")
    d.add_argument("--with-s6", action="store_true", help="§6.7: only when N* > S5 or on request")
    f = sub.add_parser("fit")
    f.add_argument("--eval-dir", default=str(REPO / "results" / "params" / "c"))
    f.add_argument("--engramm", default=None, help="c_engramm_test record (default: the latest)")
    f.add_argument("--out-dir", default=str(RESULTS))
    args = ap.parse_args()
    {"drive": drive, "fit": fit}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
