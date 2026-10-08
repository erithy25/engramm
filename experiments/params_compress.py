"""Messart B: information content of the learned state, estimated by compression.

(docs/PREREG_PARAMS.md §5.) Serialises every group of the learned state of
ENGRAMM-LM deterministically (a JSON header naming each array, dtype and shape,
then the arrays' raw little-endian bytes in that order), compresses every group
on its own with ``xz -9 -T1`` and ``zstd -19 -T1``, and takes the smaller of the
two totals. Also reported, never added to B: the corpus-bound KNN indices, the
compressed training text (the ceiling: a count table is a function of the corpus),
and — with ``--transformers`` — the fp32 weights of the trained Messart-C models.

    python -m experiments.params_compress [--model models/lm/main/model] [--transformers]

This is an estimate with an external assumption (≈ 2 bits of knowledge per parameter,
Allen-Zhu & Li 2024, arXiv:2404.05405), not a measurement of parameters.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from engramm.lm.model import HDCLanguageModel
from engramm.repro import git_revision
from experiments.lm_common import MODELS_DIR
from experiments.params_common import ENGRAMM_LM, REPO, RESULTS, WORK, write_record

COMPRESSORS = {"xz": ["xz", "-9", "-T1", "-c"], "zstd": ["zstd", "-19", "-T1", "-q", "-c"]}
CORPUS_TEXT = REPO / "data" / "cache" / "lm" / "corpus" / "train.txt.bin"
TOKEN_STREAM = REPO / "data" / "cache" / "lm" / "tokens" / "train.u16"
BITS_PER_PARAM = {"at_2_bits_per_param": 2.0, "at_1_bit_per_param": 1.0, "at_4_bits_per_param": 4.0}


def serialise(path: Path, arrays: list[tuple[str, np.ndarray]]) -> int:
    """Header (JSON, one line) + raw bytes of every array in the given order; little-endian."""
    head = [{"name": n, "dtype": np.dtype(a.dtype).newbyteorder("<").str, "shape": list(a.shape)}
            for n, a in arrays]
    with open(path, "wb") as f:
        f.write(json.dumps(head, separators=(",", ":")).encode() + b"\n")
        for _, a in arrays:
            f.write(np.ascontiguousarray(a, dtype=np.dtype(a.dtype).newbyteorder("<")).tobytes())
    return path.stat().st_size


def compressed_size(path: Path, tool: str) -> dict:
    t0 = time.time()
    p = subprocess.Popen(COMPRESSORS[tool] + [str(path)], stdout=subprocess.PIPE)
    n = 0
    while chunk := p.stdout.read(1 << 22):
        n += len(chunk)
    if p.wait() != 0:
        raise RuntimeError(f"{tool} failed on {path}")
    return {"bytes": n, "seconds": time.time() - t0}


def versions() -> dict:
    out = {}
    for tool in COMPRESSORS:
        r = subprocess.run([tool, "--version"], capture_output=True, text=True)
        out[tool] = (r.stdout or r.stderr).splitlines()[0]
    return out


def learned_groups(model: HDCLanguageModel) -> dict[str, list[tuple[str, np.ndarray]]]:
    groups = {}
    for n in range(1, model.kn.order + 1):
        t = model.kn.tables[n]
        groups[f"kn5_order{n}"] = [(f"{k}_{n}", np.asarray(getattr(t, k)))
                                   for k in ("ctx", "ptr", "total", "n1", "n2", "n3", "w", "a", "coc")]
    cb = model.cb
    groups["codebook"] = [("seed", np.array([cb.seed], dtype=np.int64)), ("ctx_tokens", cb.ctx_tokens),
                          ("counts", cb.counts), ("eng", cb.eng), ("wide", cb.wide), ("idf", cb.idf),
                          ("classes", cb.classes)]
    m = model.mix
    groups["mixture"] = [("weights", np.asarray(m.weights)), ("knn_edges", np.asarray(m.knn_edges)),
                         ("tau_beta", np.array([m.tau, m.beta]))]
    return groups


def transformer_groups() -> dict[str, list[tuple[str, np.ndarray]]]:
    import torch

    out = {}
    for ck in sorted((REPO / "models" / "params").glob("*/final.pt")):
        sd = torch.load(ck, map_location="cpu")["model"]
        out[f"transformer:{ck.parent.name}"] = [(k, sd[k].numpy()) for k in sorted(sd)]
    return out


def run(files: dict[str, Path], jobs: int) -> dict:
    tasks = [(g, tool) for g in files for tool in COMPRESSORS]
    with ThreadPoolExecutor(jobs) as ex:
        res = list(ex.map(lambda gt: compressed_size(files[gt[0]], gt[1]), tasks))
    out = {g: {"raw_bytes": files[g].stat().st_size} for g in files}
    for (g, tool), r in zip(tasks, res):
        out[g][tool] = r
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=MODELS_DIR / "main" / "model")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--transformers", action="store_true", help="also the fp32 weights of models/params/*/final.pt")
    ap.add_argument("--skip-reference", action="store_true", help="do not compress the training text")
    ap.add_argument("--only-transformers", action="store_true",
                    help="only the fp32 weights of models/params/*/final.pt (after Messart C)")
    ap.add_argument("--smoke", action="store_true", help="code test on another model: no digest check, scratch output")
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    work = WORK / "serial"
    work.mkdir(parents=True, exist_ok=True)
    if args.only_transformers:
        tf = {}
        for g, arrays in transformer_groups().items():
            tf[g] = work / f"{g.replace(':', '_')}.bin"
            serialise(tf[g], arrays)
        res = run(tf, args.jobs)
        best = {g: min(r["xz"]["bytes"], r["zstd"]["bytes"]) for g, r in res.items()}
        out = {"compressors": versions(), "commands": COMPRESSORS, "transformers": res,
               "summary": {g: {"raw_bytes": res[g]["raw_bytes"], "best_bytes": b, "bits": 8 * b} for g, b in best.items()}}
        print(json.dumps(out["summary"], indent=1), flush=True)
        print(write_record("b_transformers", out, t0, git_state, WORK / "smoke" if args.smoke else RESULTS),
              flush=True)
        return
    model = HDCLanguageModel.load(args.model)
    digest = model.base_digest()
    if digest != ENGRAMM_LM["base_digest"] and not args.smoke:
        raise SystemExit(f"base digest {digest} differs from the registered {ENGRAMM_LM['base_digest']}")

    learned = {g: work / f"{g}.bin" for g in learned_groups(model)}
    for g, arrays in learned_groups(model).items():
        serialise(learned[g], arrays)
    index = {"knn_position_index": work / "knn_pos.bin", "segment_signatures": work / "segsig.bin"}
    serialise(index["knn_position_index"], [("knn_pos", model.pos)])
    serialise(index["segment_signatures"], [("segsig", model.segsig)])
    del model

    res_learned = run(learned, args.jobs)
    res_index = run(index, args.jobs)
    res_ref = {} if args.skip_reference else run({"train_text_utf8": CORPUS_TEXT, "train_token_stream": TOKEN_STREAM},
                                                 args.jobs)
    res_tf = {}
    if args.transformers:
        tf = {}
        for g, arrays in transformer_groups().items():
            tf[g] = work / f"{g.replace(':', '_')}.bin"
            serialise(tf[g], arrays)
        res_tf = run(tf, args.jobs)

    totals = {tool: sum(r[tool]["bytes"] for r in res_learned.values()) for tool in COMPRESSORS}
    best = min(totals, key=totals.get)
    b_bits = 8 * totals[best]
    tot_index = {tool: totals[tool] + sum(r[tool]["bytes"] for r in res_index.values()) for tool in COMPRESSORS}
    summary = {
        "raw_bytes": sum(r["raw_bytes"] for r in res_learned.values()),
        "compressed_bytes": totals, "best_compressor": best, "B_bits": b_bits,
        "capacity_equivalent_params": {k: b_bits / v for k, v in BITS_PER_PARAM.items()},
        "assumption": "≈ 2 bits of knowledge per parameter (Allen-Zhu & Li 2024, Physics of Language Models "
                      "Part 3.3, arXiv:2404.05405); span 1–4 bits/parameter",
        "status": "estimate with external assumption, not a measurement",
        "with_knn_index": {"compressed_bytes": tot_index, "B_bits": 8 * min(tot_index.values()),
                           "capacity_equivalent_params": {k: 8 * min(tot_index.values()) / v
                                                          for k, v in BITS_PER_PARAM.items()}},
    }
    out = {"subject": {**ENGRAMM_LM, "model_dir": str(args.model), "base_digest_checked": digest},
           "compressors": versions(), "commands": COMPRESSORS, "groups_learned": res_learned,
           "groups_corpus_bound": res_index, "reference_training_text": res_ref, "transformers": res_tf,
           "summary": summary}
    print(json.dumps(summary, indent=1), flush=True)
    print(write_record("b_engramm_lm", out, t0, git_state,
                                                    WORK / "smoke" if args.smoke else RESULTS), flush=True)


if __name__ == "__main__":
    main()
