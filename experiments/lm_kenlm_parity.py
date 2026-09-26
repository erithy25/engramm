"""KN-5 parity against KenLM (plan: our modified Kneser-Ney within 0.3 % of KenLM).

    python -m experiments.lm_kenlm_parity --kenlm-bin <kenlm/build/bin> [--scale pilot]

Both models get the same data: every train document is one "sentence" of
token ids (``t<id>``); KenLM's <s> / </s> play the part of our <|eos|> as
document start / end. Compared unpruned (KenLM ``lmplz`` default) on val-B
half 2 with the near-duplicate filter: BPB of each, and their ratio. Known
difference: KenLM spreads the unigram's interpolation mass over the tokens it
has seen plus <unk>, ours over all 32,768 ids.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

from engramm.lm.evaluate import bpb, doc_bytes, per_doc_bits
from engramm.lm.ngram import build_kn
from engramm.repro import git_revision
from experiments.lm_common import half_mask, load_split, load_train, write_record
from experiments.lm_mix import dedup_keep


def write_docs(split, path: Path) -> None:
    with open(path, "w") as f:
        for i in range(split.n_docs):
            f.write(" ".join(f"t{int(x)}" for x in split.doc_tokens(i)) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kenlm-bin", type=Path, required=True)
    ap.add_argument("--scale", default="pilot")
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    train = load_train(args.scale)
    vb = load_split("val_b")
    mask = dedup_keep("val_b", vb.n_docs) & half_mask(vb, 1)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        write_docs(train, tmp / "train.txt")
        write_docs(vb, tmp / "val.txt")
        subprocess.run([str(args.kenlm_bin / "lmplz"), "-o", "5", "-S", "3G", "-T", str(tmp),
                        "--text", str(tmp / "train.txt"), "--arpa", str(tmp / "m.arpa")],
                       check=True, capture_output=True)
        out = subprocess.run([str(args.kenlm_bin / "query"), "-v", "sentence", str(tmp / "m.arpa")],
                             stdin=open(tmp / "val.txt"), check=True, capture_output=True, text=True).stdout
    totals = [float(m.group(1)) for m in re.finditer(r"Total: (-?[\d.e+-]+) OOV: \d+", out)]
    if len(totals) != vb.n_docs:
        raise RuntimeError(f"expected {vb.n_docs} sentence scores, got {len(totals)}")
    ken_bits = -np.array(totals) * np.log2(10.0)
    ours = build_kn(np.asarray(train.tokens), order=5, prune_from=99)
    p, _ = ours.stream_probs(np.asarray(vb.tokens))
    our_bits = per_doc_bits(vb, p)
    nb = doc_bytes(vb)
    res = {"scale": args.scale, "kenlm_bpb": bpb(ken_bits, nb, mask=mask).as_dict(),
           "ours_unpruned_bpb": bpb(our_bits, nb, mask=mask).as_dict(),
           "ratio_ours_over_kenlm": float(our_bits[mask].sum() / ken_bits[mask].sum())}
    res["within_0_3_percent"] = abs(res["ratio_ours_over_kenlm"] - 1) <= 0.003
    print(res, flush=True)
    print(write_record(f"kenlm_parity_{args.scale}", res, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
