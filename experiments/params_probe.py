"""Training throughput of the Messart-C size grid on random token ids (no data, no split).

(docs/PREREG_PARAMS.md §6.) Only for planning the compute budget: it touches
neither the corpus nor any evaluation split, and it measures no quantity of
Messart A, B or C. Container timings are never official (docs/PROTOCOL.md,
rule 2); the record carries ``environment.canonical`` like every other.

    .venv_b1/bin/python -u -m experiments.params_probe
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments"))

from lm_transformer import CTX, V, Arch, GPT, param_counts, train_step  # noqa: E402

sys.path.insert(0, str(REPO))
from experiments.params_common import GRID  # noqa: E402


def probe(arch: Arch, batch: int, threads: int, bf16: bool, steps: int, warm: int, chunked: bool = False) -> dict:
    torch.set_num_threads(threads)
    torch.manual_seed(0)
    model = GPT(arch)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, betas=(0.9, 0.95), weight_decay=0.1)
    rng = np.random.default_rng(0)
    for i in range(warm + steps):
        if i == warm:
            t0 = time.perf_counter()
        b = torch.from_numpy(rng.integers(1, V, size=(batch, CTX + 1)).astype(np.int64))
        train_step(model, opt, b, bf16, chunked)
    dt = time.perf_counter() - t0
    return {**param_counts(model), "tokens_per_s": steps * batch * CTX / dt, "seconds_per_step": dt / steps}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--warm", type=int, default=3)
    ap.add_argument("--chunked", action="store_true", help="only the registered setting: fp32, block-wise loss")
    args = ap.parse_args()
    from engramm.repro import collect_environment, git_revision

    rows = []
    configs = ([(False, 16, 4, True), (False, 16, 2, True)] if args.chunked else
               [(bf16, b, t, False) for bf16 in (False, True) for b, t in ((16, 4), (16, 2), (32, 4))])
    for name, (d, layers, heads) in GRID.items():
        for bf16, batch, threads, chunked in configs:
            r = probe(Arch(d, layers, heads), batch, threads, bf16, args.steps, args.warm, chunked)
            row = {"size": name, "d": d, "layers": layers, "heads": heads, "bf16": bf16, "batch": batch,
                   "threads": threads, "chunked_loss": chunked, **r}
            rows.append(row)
            print(json.dumps(row), flush=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rec = {"schema": "engramm-params/1", "name": "probe_throughput", "study": "docs/PREREG_PARAMS.md (planning only)",
           "timestamp_utc": ts, "git": git_revision(), "environment": collect_environment(),
           "torch": torch.__version__, "input": "random token ids, no corpus", "rows": rows,
           "note": "container timing: planning input only, never an official figure (PROTOCOL rule 2)"}
    out = REPO / "results" / "params" / f"probe_throughput{'_chunked' if args.chunked else ''}_{ts}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, flush=True)


if __name__ == "__main__":
    main()
