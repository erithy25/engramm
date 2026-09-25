"""Reference only: GPT-2 small (124 M parameters, trained on 40 GB WebText by OpenAI)
measured on our splits with the same byte accounting (docs/PREREG_LM.md §5).

    .venv_b1/bin/python -u experiments/lm_gpt2_ref.py --split test

Each document is scored on its own: context starts with <|endoftext|>, the
document ends with <|endoftext|> (which is scored, as our models score
<|eos|>); sliding window 1024, stride 512. Bytes = UTF-8 + 1 per document.
The Hugging Face revision and the SHA-256 of the weights are recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "data" / "cache" / "lm" / "corpus"
OUT = REPO / "models" / "lm" / "gpt2"
HF_HOME = REPO / "models" / "hf"
MODEL = "openai-community/gpt2"
WINDOW, STRIDE = 1024, 512


def docs(split):
    offsets = np.load(CORPUS / f"{split}.offsets.npy")
    blob = (CORPUS / f"{split}.txt.bin").read_bytes()
    meta = [json.loads(l) for l in open(CORPUS / f"{split}.meta.jsonl", encoding="utf-8")]
    return [(blob[offsets[i]:offsets[i + 1]].decode("utf-8"), (meta[i]["source"], meta[i]["key"]))
            for i in range(len(offsets) - 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()
    os.environ.setdefault("HF_HOME", str(HF_HOME))
    import torch
    from huggingface_hub import HfApi, snapshot_download
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast

    torch.set_num_threads(args.threads)
    revision = HfApi().model_info(MODEL).sha
    path = Path(snapshot_download(MODEL, revision=revision, allow_patterns=["*.json", "*.safetensors", "*.txt"]))
    weights = next(path.glob("*.safetensors"))
    sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    tok = GPT2TokenizerFast.from_pretrained(path)
    model = GPT2LMHeadModel.from_pretrained(path).eval()
    eot = tok.eos_token_id
    bits, nbytes, keys = [], [], []
    with torch.no_grad():
        for text, key in docs(args.split):
            ids = [eot] + tok.encode(text) + [eot]
            n, total, done, a = len(ids), 0.0, 0, 0
            while done < n - 1:
                w = torch.tensor(ids[a:a + WINDOW + 1])[None]
                logp = torch.log_softmax(model(w[:, :-1]).logits, -1)[0]
                tgt = w[0, 1:]
                lp = logp[torch.arange(len(tgt)), tgt].numpy()
                total -= lp[done - a:].sum() / math.log(2)
                done = a + len(tgt)
                a += STRIDE
            bits.append(total)
            nbytes.append(len(text.encode("utf-8")) + 1)
            keys.append(key)
    OUT.mkdir(parents=True, exist_ok=True)
    out = {"model": MODEL, "revision": revision, "weights_sha256": sha, "split": args.split,
           "per_doc_bits": bits, "doc_bytes": nbytes, "keys": keys,
           "bpb": float(np.sum(bits) / np.sum(nbytes))}
    (OUT / f"eval_{args.split}.json").write_text(json.dumps(out))
    print(args.split, out["bpb"], revision, sha, flush=True)


if __name__ == "__main__":
    main()
