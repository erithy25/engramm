"""Export the Sela-1 checkpoint (torch, fp32) to the NumPy weights file of engramm/lm/sela.py (fp16, transposed).

    python -m experiments.sela1_export --ckpt model_main.pt --out sela1-135m.npz [--check]

--check compares the NumPy forward pass (float32 after loading the fp16 file) with the torch model on fixed prompts
and fails if the largest logit difference exceeds the tolerance; it also checks that the NumPy KV cache gives the same
logits as one full pass. Runs where torch is installed (CI); the app itself needs only NumPy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from engramm.lm.sela import FORMAT


def export(ckpt: Path, out: Path) -> dict:
    import torch
    st = torch.load(ckpt, map_location="cpu", weights_only=False)
    cfg = st["cfg"]
    if cfg.get("bigram_rows"):
        raise SystemExit("Sela export supports bigram_rows = 0 only")
    sd = {k: v.float() for k, v in st["model"].items()}
    vocab, d = sd["emb.weight"].shape
    arrays = {"emb": sd["emb.weight"].numpy(), "head_t": sd["head.weight"].T.contiguous().numpy()}
    for i in range(cfg["layers"]):
        p = f"blocks.{i}."
        for name in ("qkv", "proj", "fc1", "fc2"):
            arrays[f"b{i}.{name}_t"] = sd[p + name + ".weight"].T.contiguous().numpy()
    arrays = {k: v.astype(np.float16) for k, v in arrays.items()}
    h = hashlib.sha256()
    with open(ckpt, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    header = {"format": FORMAT, "cfg": {"d": d, "layers": cfg["layers"], "heads": cfg["heads"],
                                        "ctx_max": cfg["ctx_max"], "vocab": vocab},
              "meta": {"name": "Sela-1 135M", "source_sha256": h.hexdigest(),
                       "tokens_trained": int(st.get("meta", {}).get("tokens", 0)), "dtype": "float16",
                       "exported_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}}
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part.npz")
    np.savez(tmp, header=np.frombuffer(json.dumps(header).encode("utf-8"), dtype=np.uint8), **arrays)
    tmp.replace(out)
    return header


def check(ckpt: Path, out: Path, tol: float = 0.05) -> dict:
    """NumPy (fp16 weights) against torch (fp32 weights) on fixed prompts; cache against one full pass."""
    import torch
    from engramm.lm.sela import KVCache, SelaModel, EOS
    from engramm.lm.tokenizer import LMTokenizer
    from experiments import v5_long as L
    st = torch.load(ckpt, map_location="cpu", weights_only=False)
    tm = L.LongGPT(**st["cfg"]).eval()
    tm.load_state_dict({k: v.float() for k, v in st["model"].items()})
    nm = SelaModel.load(out)
    tok = LMTokenizer()
    res = {"prompts": []}
    worst = 0.0
    for p in ("The history of the city", "Albert Einstein was", "How to make a cup of tea: First,"):
        ids = [EOS] + [int(i) for i in tok.encode(p)]
        with torch.no_grad():
            ref = tm(torch.tensor([ids]))[0][0].numpy()
        full = nm.forward(ids, KVCache(nm.cfg))
        cache = KVCache(nm.cfg)
        parts = [nm.forward(ids[:2], cache)] + [nm.forward([t], cache) for t in ids[2:]]
        inc = np.concatenate(parts)
        d_ref, d_cache = float(np.abs(full - ref).max()), float(np.abs(inc - full).max())
        top_same = bool((full.argmax(-1) == ref.argmax(-1)).mean() >= 0.99)
        res["prompts"].append({"prompt": p, "tokens": len(ids), "max_abs_logit_diff_vs_torch": d_ref,
                               "max_abs_logit_diff_cache_vs_full": d_cache, "argmax_agrees": top_same})
        worst = max(worst, d_ref)
        if d_cache > 1e-3:
            raise SystemExit(f"NumPy cache differs from the full pass by {d_cache:.2e}")
        if not top_same:
            raise SystemExit(f"NumPy and torch disagree on the most likely next token for {p!r}")
    if worst > tol:
        raise SystemExit(f"NumPy (fp16 weights) differs from torch by {worst:.3f} logits (tolerance {tol})")
    res["worst_logit_diff"] = worst
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    header = export(Path(args.ckpt), Path(args.out))
    size = Path(args.out).stat().st_size
    print(f"written {args.out}: {size / 1e6:.1f} MB, {header['cfg']}, source {header['meta']['source_sha256'][:16]}…",
          flush=True)
    if args.check:
        print(json.dumps(check(Path(args.ckpt), Path(args.out)), indent=1), flush=True)


if __name__ == "__main__":
    main()
