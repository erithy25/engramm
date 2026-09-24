"""M0 — HNSW recall audit and micro-benchmarks on 10^6 real WiLI keys.

    python -m experiments.m0_bench --seed 42

The question M0 answered historically (D6 W12): does approximate
nearest-neighbour search on binary hypervectors of *real* text reach
recall ≥ 95 % — or do the clustered keys of natural language break HNSW?
This harness re-measures it:

* **Keys.** 100-byte windows of the WiLI-2018 training paragraphs at stride
  50, taken in split order until 10^6 are collected, encoded with the
  project's trigram encoder (D = 10,000). **Queries:** 1,000 held-out
  windows — the first window of 1,000 seeded-random *test* paragraphs, so no
  query is a key.
* **Ground truth.** Exact top-32 by Hamming distance over all 10^6 keys
  (FAISS ``IndexBinaryFlat``).
* **Index.** FAISS ``IndexBinaryHNSW`` (M = 32, efConstruction = 40, the
  library defaults) — as in the original, a measuring vehicle for the
  question, not the classifier's own index (``docs/DEVIATIONS.md``
  CHANGED-7).
* **Recall@32, tie-tolerant**: a returned key counts if its exact distance
  is at most the 32nd exact distance of that query; many keys can share
  that distance, and which of them an index returns is arbitrary.
* **Registered primary criterion (D5 §1):** recall ≥ 95 % at some
  ef ∈ {64, 128, 256}.

Micro-benchmarks (encode, distance hot/cold, insert, query latency) are
recorded too. In a container they are **not** official (``docs/PROTOCOL.md``
rule 2). Energy per query needs a power meter — ``powermetrics`` on the
reference machine; this container exposes neither RAPL nor anything else —
so it is recorded as not measured rather than estimated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from data.loaders import load_wili
from engramm.core import ItemMemory
from engramm.encoders import TrigramEncoder
from engramm.metrics import hamming
from engramm.repro import collect_environment, git_revision, peak_rss_mb, set_all_seeds
from experiments.energy import measure_energy
from experiments.common import encode_cached

WINDOW = 100
STRIDE = 50
N_KEYS = 1_000_000
N_QUERIES = 1_000
K = 32
EF_VALUES = (64, 128, 256)
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "m0"


def windows(texts: Any, n: int, width: int = WINDOW, stride: int = STRIDE) -> list[bytes]:
    """The first ``n`` byte windows of the texts, in order."""
    out: list[bytes] = []
    for text in texts:
        raw = text.encode("utf-8")
        for offset in range(0, len(raw) - width + 1, stride):
            out.append(raw[offset:offset + width])
            if len(out) == n:
                return out
    raise ValueError(f"only {len(out)} windows available, {n} requested")


def query_windows(test_texts: Any, n: int, rng: np.random.Generator,
                  width: int = WINDOW) -> list[bytes]:
    """First window of ``n`` seeded-random test paragraphs long enough to have one."""
    candidates = [i for i, t in enumerate(test_texts) if len(t.encode("utf-8")) >= width]
    chosen = np.sort(rng.choice(np.array(candidates), size=n, replace=False))
    return [test_texts[i].encode("utf-8")[:width] for i in chosen]


def tie_tolerant_recall(found_dist: np.ndarray, found_ids: np.ndarray,
                        kth_true: np.ndarray, k: int) -> float:
    """Mean over queries of |{returned with dist ≤ k-th true dist}| / k."""
    valid = found_ids >= 0
    hits = ((found_dist <= kth_true[:, None]) & valid).sum(axis=1)
    return float(np.mean(np.minimum(hits, k) / k))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--D", dest="dimension", type=int, default=10_000)
    parser.add_argument("--n-keys", type=int, default=N_KEYS)
    parser.add_argument("--n-queries", type=int, default=N_QUERIES)
    parser.add_argument("--hnsw-m", type=int, default=32)
    parser.add_argument("--ef-construction", type=int, default=40)
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = parser.parse_args(argv)

    import faiss

    git_state = git_revision()
    started = time.perf_counter()
    rng = set_all_seeds(args.seed)
    wili = load_wili(allow_download=True)
    encoder = TrigramEncoder(ItemMemory(args.seed, args.dimension))

    key_windows = windows(wili.x_train, args.n_keys)
    queries = query_windows(wili.x_test, args.n_queries, rng)
    print(f"{len(key_windows)} key windows, {len(queries)} query windows", flush=True)

    marker = time.perf_counter()
    keys = encode_cached(encoder, key_windows, batch=20_000)
    encode_seconds = time.perf_counter() - marker
    q = encoder.encode(queries)
    anchor = hashlib.md5(np.ascontiguousarray(keys[:1000]).tobytes()).hexdigest()
    print(f"keys encoded: {keys.shape} (anchor md5(keys[:1000]) = {anchor})", flush=True)

    # --- micro-benchmarks (single thread, container: not official) --------
    faiss.omp_set_num_threads(1)
    probe = [w for w in key_windows[:2000]]
    marker = time.perf_counter()
    encoder.encode(probe)
    encode_s_us = (time.perf_counter() - marker) / len(probe) * 1e6

    # Distance cost per pair, vectorised so the figure is the distance and not
    # NumPy's per-call overhead. "Hot": one query against 256 keys (320 KB,
    # cache-resident), repeated. "Cold": one query against 100,000 keys
    # gathered from random positions of the full 1.25 GB key array.
    hot = keys[:256].copy()
    reps = 400
    marker = time.perf_counter()
    for i in range(reps):
        hamming(q[i % q.shape[0]][None, :], hot)
    dh_hot_ns = (time.perf_counter() - marker) / (reps * hot.shape[0]) * 1e9
    idx = rng.integers(0, keys.shape[0], size=100_000)
    marker = time.perf_counter()
    hamming(q[0][None, :], keys[idx])
    dh_cold_ns = (time.perf_counter() - marker) / idx.size * 1e9

    flat = faiss.IndexBinaryFlat(args.dimension)
    flat.add(keys)

    marker = time.perf_counter()
    flat.search(q[:20], K)
    brute_ms = (time.perf_counter() - marker) / 20 * 1e3

    # --- ground truth (all threads) ----------------------------------------
    faiss.omp_set_num_threads(os.cpu_count() or 1)
    marker = time.perf_counter()
    true_dist, true_ids = flat.search(q, K)
    truth_seconds = time.perf_counter() - marker
    kth_true = true_dist[:, K - 1].astype(np.int64)
    del flat

    # --- HNSW build -----------------------------------------------------------
    index = faiss.IndexBinaryHNSW(args.dimension, args.hnsw_m)
    index.hnsw.efConstruction = args.ef_construction
    marker = time.perf_counter()
    index.add(keys)
    build_seconds = time.perf_counter() - marker
    insert_ms = build_seconds / keys.shape[0] * 1e3 * (os.cpu_count() or 1)
    print(f"HNSW built in {build_seconds:.0f}s", flush=True)

    rows = []
    for ef in EF_VALUES:
        index.hnsw.efSearch = ef
        faiss.omp_set_num_threads(os.cpu_count() or 1)
        found_dist, found_ids = index.search(q, K)
        recall = tie_tolerant_recall(found_dist.astype(np.int64), found_ids, kth_true, K)
        strict = float(np.mean([len(set(f) & set(t)) / K
                                for f, t in zip(found_ids, true_ids)]))
        faiss.omp_set_num_threads(1)
        latencies = []
        for i in range(min(200, q.shape[0])):
            marker = time.perf_counter()
            index.search(q[i:i + 1], K)
            latencies.append((time.perf_counter() - marker) * 1e3)
        rows.append({"ef": ef, "recall_at_32_tie_tolerant": recall,
                     "recall_at_32_strict_ids": strict,
                     "query_ms_p50": float(np.percentile(latencies, 50)),
                     "query_ms_p99": float(np.percentile(latencies, 99))})
        print(f"  ef={ef}: recall@32 {recall:.4f} (strict ids {strict:.4f})  "
              f"p50 {rows[-1]['query_ms_p50']:.2f} ms", flush=True)

    # Energy per query at the historical GO point (ef = 128), single thread,
    # over the first 200 queries — where the hardware exposes it at all.
    index.hnsw.efSearch = 128
    faiss.omp_set_num_threads(1)
    cycle = iter(range(10**9))
    energy = measure_energy(lambda: index.search(q[next(cycle) % 200:][:1], K), 200)
    print(f"energy per query (ef=128): {energy['mj_per_call']} mJ "
          f"({energy['source'] or energy['note']})", flush=True)

    go = [r["ef"] for r in rows if r["recall_at_32_tie_tolerant"] >= 0.95]
    record = {
        "task": "m0_hnsw_recall", "seed": args.seed,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {**git_state, "captured": "before_run"},
        "setup": {"dimension": args.dimension, "n_keys": int(keys.shape[0]),
                  "n_queries": int(q.shape[0]), "window_bytes": WINDOW,
                  "stride_bytes": STRIDE, "k": K,
                  "keys": "WiLI-2018 training paragraphs, byte windows in split order",
                  "queries": "first window of seeded-random WiLI-2018 test paragraphs",
                  "index": f"faiss.IndexBinaryHNSW(M={args.hnsw_m}, "
                           f"efConstruction={args.ef_construction})",
                  "faiss": faiss.__version__, "key_anchor_md5_first_1000": anchor},
        "recall": rows,
        "criterion": {"registered": "recall@32 >= 0.95 at some ef in {64,128,256} (D5 §1)",
                      "met": bool(go), "first_ef_meeting_it": go[0] if go else None},
        "microbenchmarks_not_official": {
            "encode_s_100_bytes_us": encode_s_us,
            "hamming_hot_ns_per_pair_numpy": dh_hot_ns,
            "hamming_cold_ns_per_pair_numpy_random_gather": dh_cold_ns,
            "brute_force_ms_per_query_1e6_single_thread": brute_ms,
            "hnsw_insert_ms_per_key_thread_normalised": insert_ms,
            "hnsw_build_seconds": build_seconds,
            "ground_truth_seconds": truth_seconds,
            "key_encoding_seconds": encode_seconds,
        },
        "energy_mj_per_query": energy["mj_per_call"],
        "energy": {**energy, "ef": 128, "threads": 1},
        "runtime": {"wall_seconds": time.perf_counter() - started,
                    "peak_rss_mb": peak_rss_mb(), "peak_rss_scope": "process"},
        "environment": collect_environment(),
    }
    out_dir = Path(args.results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"m0_{args.seed}_{stamp}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"criterion met: {bool(go)} (first ef: {go[0] if go else None})\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
