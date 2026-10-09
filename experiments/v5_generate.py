"""Text from the v5 long-run model (experiments/v5_long.py): nucleus sampling, optional
repetition penalty, deterministic per seed.

    env PYTHONPATH=/dev/shm/engramm/pt311:. .venv/bin/python -m experiments.v5_generate \\
        --ckpt models/lm/v5/long_latest.pt --prompt "The history of the city" --tokens 80

Several prompts can be written to a JSON file of samples (``--out``) for side-by-side reading.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torch.nn.functional as F

from engramm.lm.tokenizer import LMTokenizer
from experiments.v5_long import LongGPT

REPO = Path(__file__).resolve().parents[1]


def load_model(path: str) -> tuple[LongGPT, dict]:
    st = torch.load(path, map_location="cpu", weights_only=False)
    a = st["meta"]["args"]
    model = LongGPT(a["d"], a["layers"], a["heads"], a["ctx_max"], a["bigram_rows"])
    model.load_state_dict({k: v.float() for k, v in st["model"].items()})
    model.eval()
    return model, st["meta"]


@torch.no_grad()
def generate(model: LongGPT, ids: list[int], n: int, top_p: float, temperature: float, rep_penalty: float,
             seed: int, ctx: int) -> list[int]:
    g = torch.Generator().manual_seed(seed)
    out = list(ids)
    for _ in range(n):
        x = torch.tensor([out[-ctx:]], dtype=torch.int64)
        logits = model(x)[0][0, -1].float()
        if rep_penalty != 1.0:
            seen = torch.tensor(sorted(set(out[-ctx:])), dtype=torch.int64)
            sel = logits[seen]
            logits[seen] = torch.where(sel > 0, sel / rep_penalty, sel * rep_penalty)
        probs = F.softmax(logits / max(temperature, 1e-6), dim=-1)
        sp, si = torch.sort(probs, descending=True)
        keep = torch.cumsum(sp, 0) - sp < top_p
        sp = sp * keep
        nxt = int(si[torch.multinomial(sp / sp.sum(), 1, generator=g)])
        if nxt == 0:                                   # <|eos|>: end of document
            break
        out.append(nxt)
    return out[len(ids):]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--prompt", action="append", required=True, help="may be given several times")
    ap.add_argument("--tokens", type=int, default=80)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--rep-penalty", type=float, default=1.15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    tok = LMTokenizer()
    model, meta = load_model(args.ckpt)
    rows = []
    for p in args.prompt:
        ids = [0] + [int(i) for i in tok.encode(p)]     # a document starts after <|eos|>
        cont = generate(model, ids, args.tokens, args.top_p, args.temperature, args.rep_penalty, args.seed,
                        model.cfg["ctx_max"])
        text = tok.decode(cont)
        rows.append({"prompt": p, "continuation": text})
        print(f"### {p}\n{p}{text}\n", flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps({"ckpt_tokens": meta["tokens"], "train_hours": meta["train_seconds"] / 3600,
                                              "settings": {k: getattr(args, k) for k in ("tokens", "top_p", "temperature",
                                                                                           "rep_penalty", "seed")},
                                              "samples": rows}, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
