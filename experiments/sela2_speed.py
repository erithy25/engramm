"""Chat speed of Sela-2 in the desktop app: the NumPy model (engramm/lm/sela.py, int8 file, fp32 matrices) at the
full size (24 layers × 1024, vocabulary 49,152, random weights: the speed does not depend on the values).

    python -m experiments.sela2_speed [--out results/sela2/app_speed.json]

Measures the prompt (300 tokens at once) and the reply (one token at a time with the growing cache, positions
300–364) and reports milliseconds per reply token; the file size and the memory the loaded model needs."""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import tempfile
import time
from pathlib import Path

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--tokens", type=int, default=64)
    args = ap.parse_args()
    import torch
    from engramm.lm.sela import load_model
    from experiments.sela2_model import Sela2, Sela2Config, export_npz
    from experiments.sela2_train import SIZES
    torch.manual_seed(0)
    with tempfile.TemporaryDirectory() as td:
        m = Sela2(Sela2Config(**SIZES["sela2"]))
        path = export_npz(m, Path(td) / "speed.npz")
        size = path.stat().st_size
        del m
        rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        t = time.time()
        nm = load_model(path)
        load_s = time.time() - t
    rng = np.random.default_rng(0)
    ids = [0] + [int(i) for i in rng.integers(16, 49152, 299)]
    cache = nm.new_cache()
    t = time.time()
    nm.forward(ids, cache, last_only=True)
    prefill = time.time() - t
    times = []
    for k in range(args.tokens):
        t = time.time()
        nm.forward([int(rng.integers(16, 49152))], cache, last_only=True)
        times.append(time.time() - t)
    dec = float(np.median(times))
    res = {"what": "Sela-2 NumPy model (app), full size, random weights", "file_mb": round(size / 1e6, 1),
           "load_s": round(load_s, 1), "prompt_300_tokens_s": round(prefill, 2), "ms_per_reply_token": round(1000 * dec, 1),
           "reply_tokens_per_s": round(1 / dec, 1), "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 0),
           "rss_before_load_mb": round(rss0 / 1024, 0), "cpus": os.cpu_count(), "machine": platform.machine(),
           "processor": platform.processor(), "numpy": np.__version__}
    print(json.dumps(res, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
