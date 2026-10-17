"""M10 of docs/PREREG_SELA2.md: what the app's int8 file costs against float32, in bits per byte on held-out
documents, both through the app's NumPy forward pass (engramm/lm/sela.py).

    python -m experiments.sela2_int8_check --ckpt sela2_chat_bf16.pt --data DIR --out results/sela2/int8.json

The checkpoint is exported twice (experiments/sela2_model.py export_npz: quant "fp32" and "int8"); both score the
same documents: the first ``--docs`` documents of val_fwe, val_wiki_en and val_fw2_de, each cut to its first
``--max-tokens`` tokens, scored after an <|eos|> (bytes = UTF-8 length of the scored tokens). Criterion (PREREG §2):
int8 − fp32 <= 0.005 bits per byte, else the app ships fp16.
"""

from __future__ import annotations

import argparse
import json
import math
import tempfile
import time
from pathlib import Path

import numpy as np

STREAMS = ("val_fwe", "val_wiki_en", "val_fw2_de")


def doc_tokens(data: Path, name: str, n: int, max_tokens: int) -> list[np.ndarray]:
    toks = np.fromfile(data / f"{name}.u16", dtype=np.uint16)
    starts = np.load(data / f"{name}.starts.npy").astype(np.int64)
    ends = np.append(starts[1:] - 1, len(toks))
    return [toks[s:min(e, s + max_tokens)] for s, e in zip(starts[:n], ends[:n]) if e > s]


def nats(model, ids: np.ndarray) -> float:
    seq = [0] + [int(t) for t in ids]
    z = model.forward(seq[:-1], model.new_cache()).astype(np.float64)
    z -= z.max(axis=1, keepdims=True)
    lse = np.log(np.exp(z).sum(axis=1))
    return float((lse - z[np.arange(len(seq) - 1), seq[1:]]).sum())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--tokenizer", default="data/lm2_tokenizer.json")
    ap.add_argument("--docs", type=int, default=20)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--streams", default=",".join(STREAMS))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import torch
    from engramm.lm.sela import load_model
    from engramm.lm.tokenizer import LMTokenizer
    from experiments.sela2_model import Sela2, Sela2Config, export_npz
    tok = LMTokenizer(args.tokenizer, sha256=None)
    st = torch.load(args.ckpt, map_location="cpu", weights_only=False)
    m = Sela2(Sela2Config(**st["cfg"]))
    m.load_state_dict({k: v.float() for k, v in st["model"].items()})
    streams = [x for x in args.streams.split(",") if x]
    docs = {s: doc_tokens(Path(args.data), s, args.docs, args.max_tokens) for s in streams}
    nbytes = {s: [len(tok.decode(d).encode("utf-8")) for d in ds] for s, ds in docs.items()}
    res = {"what": "M10 of docs/PREREG_SELA2.md (experiments/sela2_int8_check.py)", "ckpt": Path(args.ckpt).name,
           "docs_per_stream": args.docs, "max_tokens": args.max_tokens, "bpb": {}}
    with tempfile.TemporaryDirectory() as td:
        for quant in ("fp32", "int8"):
            t0 = time.time()
            path = export_npz(m, Path(td) / f"m_{quant}.npz", quant=quant)
            nm = load_model(path)
            per = {}
            for s, ds in docs.items():
                per[s] = sum(nats(nm, d) for d in ds) / math.log(2) / max(1, sum(nbytes[s]))
            per["mean"] = float(np.mean([per[s] for s in streams]))
            res["bpb"][quant] = per
            res[f"seconds_{quant}"] = round(time.time() - t0, 1)
            print(quant, {k: round(v, 4) for k, v in per.items()}, flush=True)
            del nm
            path.unlink()
    diff = res["bpb"]["int8"]["mean"] - res["bpb"]["fp32"]["mean"]
    res["criterion"] = {"int8_minus_fp32": diff, "limit": 0.005, "met": diff <= 0.005}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["criterion"]))


if __name__ == "__main__":
    main()
