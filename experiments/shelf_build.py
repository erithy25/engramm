"""Build a shelf (Atlas channel K1, docs/SPEC_ATLAS.md) from open texts.

Input: JSON lines {"t": title, "s": source, "x": text} (``--jsonl``, repeatable) or the parquet
shards of the Hugging Face dataset ``wikimedia/wikipedia`` (``--parquet``, columns title, text;
CC BY-SA). Output folder:

    shelf-0.bin … shelf-N.bin    volumes of fixed-size LZMA buckets (each volume < 2 GiB)
    shelf.json                   manifest: bucket size, buckets, volumes and SHA-256 of every bucket
    shelf_index/                 the local index that goes into the knowledge pack

Three passes, bounded memory:
1. a sample (first ``--sample`` documents) gives hashed document frequencies for the key terms;
2. every document is assigned online: SHAKE-256(title) → bucket, the next bucket with room on
   overflow (capacity in uncompressed bytes from a measured compression ratio), and written to a
   partition file by bucket range;
3. partitions are compressed into buckets in parallel; a bucket that would still overflow drops
   text from its longest article until it fits (counted and reported).

    python experiments/shelf_build.py --jsonl docs.jsonl --out /dev/shm/shelf --bucket-kb 1024
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import math
import os
import re
import struct
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engramm.web.shelf import MAGIC, bucket_of_title, name_key, term_hash, tokens  # noqa: E402

HASH_BITS = 22                     # hashed document frequencies: 4 M counters
VOLUME_MAX = (2 << 30) - (64 << 20)
DOC_MAX_CHARS = 40000


def _clean_text(x: str) -> str:
    x = re.sub(r"\n{3,}", "\n\n", x.strip())
    if len(x) > DOC_MAX_CHARS:
        cut = x.rfind("\n", 0, DOC_MAX_CHARS)
        x = x[:cut if cut > DOC_MAX_CHARS // 2 else DOC_MAX_CHARS]
    return x


def iter_docs(jsonl: list[Path], parquet: list[Path], limit: int | None = None):
    n = 0
    for p in jsonl:
        with open(p, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                if d.get("t") and d.get("x"):
                    doc = {"t": d["t"], "s": d.get("s", "wiki"), "x": _clean_text(d["x"])}
                    if d.get("d"):
                        doc["d"] = d["d"]             # last edit, shown as "as of"
                    if d.get("r"):
                        doc["_r"] = d["r"][:8]        # redirect titles: name forms for the index only
                    yield doc
                    n += 1
                    if limit and n >= limit:
                        return
    if parquet:
        import pyarrow.parquet as pq
        for p in parquet:
            pf = pq.ParquetFile(p)
            for rg in range(pf.num_row_groups):
                tab = pf.read_row_group(rg, columns=["title", "text"])
                for t, x in zip(tab.column("title").to_pylist(), tab.column("text").to_pylist()):
                    if t and x:
                        yield {"t": t, "s": "wiki", "x": _clean_text(x)}
                        n += 1
                        if limit and n >= limit:
                            return


def count_docs(jsonl: list[Path], parquet: list[Path]) -> tuple[int, int]:
    """(documents, text bytes) — exact for JSON lines, from parquet metadata otherwise."""
    if parquet and not jsonl:
        import pyarrow.parquet as pq
        n = sum(pq.ParquetFile(p).metadata.num_rows for p in parquet)
        return n, 0
    n = b = 0
    for d in iter_docs(jsonl, parquet):
        n += 1
        b += len(d["x"].encode("utf-8")) + len(d["t"]) + 24
    return n, b


def _compress_partition(args) -> list[tuple[int, str, int, int]]:
    """(bucket, sha256, compressed bytes, truncated articles) for each bucket of one partition;
    writes the padded buckets into the volume files."""
    part_path, out_dir, bucket_bytes, per_volume, preset = args
    by_bucket: dict[int, list[dict]] = {}
    with open(part_path, encoding="utf-8") as f:
        for line in f:
            b, doc = line.split("\t", 1)
            by_bucket.setdefault(int(b), []).append(json.loads(doc))
    results = []
    handles: dict[int, object] = {}
    try:
        for b in sorted(by_bucket):
            docs = by_bucket[b]
            truncated = 0
            while True:
                raw = "".join(json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n" for d in docs).encode()
                comp = lzma.compress(raw, preset=preset)
                if len(comp) + 8 <= bucket_bytes:
                    break
                longest = max(range(len(docs)), key=lambda i: len(docs[i]["x"]))
                x = docs[longest]["x"]
                over = len(comp) + 8 - bucket_bytes
                cut = max(200, len(x) - max(2000, int(over * 4)))
                docs[longest] = {**docs[longest], "x": x[:cut]}
                truncated += 1
            data = MAGIC + struct.pack("<I", len(comp)) + comp + b"\0" * (bucket_bytes - 8 - len(comp))
            vol = b // per_volume
            if vol not in handles:
                handles[vol] = open(Path(out_dir) / f"shelf-{vol}.bin", "r+b")
            fh = handles[vol]
            fh.seek((b % per_volume) * bucket_bytes)
            fh.write(data)
            results.append((b, hashlib.sha256(data).hexdigest(), len(comp), truncated))
    finally:
        for fh in handles.values():
            fh.close()
    return results


def write_index(ix: Path, titles: list[str], buckets: np.ndarray, name_h: np.ndarray, name_d: np.ndarray,
                term_h: np.ndarray, term_d: np.ndarray, n_buckets: int, info: dict) -> dict:
    """The local index in its compact form (all memory-mapped at run time): titles as one UTF-8
    blob + offsets, each article's bucket, name forms (titles, redirects) as sorted 64-bit hashes,
    key terms as sorted low 32 bits of their hashes with postings and idf."""
    ix.mkdir(parents=True, exist_ok=True)
    enc = [t.replace("\n", " ").encode("utf-8") for t in titles]
    total = sum(len(x) for x in enc)
    off = np.zeros(len(enc) + 1, dtype=np.uint32 if total < 2**32 else np.uint64)
    np.cumsum([len(x) for x in enc], out=off[1:])
    (ix / "titles.bin").write_bytes(b"".join(enc))
    np.save(ix / "title_off.npy", off)
    del enc
    np.save(ix / "bucket.npy", buckets.astype(np.uint16 if n_buckets <= 65536 else np.uint32))
    o = np.lexsort((name_d, name_h))
    np.save(ix / "name_hash.npy", name_h[o].astype(np.uint64))
    np.save(ix / "name_doc.npy", name_d[o].astype(np.uint32))
    h32 = (term_h & np.uint64(0xFFFFFFFF)).astype(np.uint32)
    order = np.lexsort((term_d, h32))
    h32, d = h32[order], term_d[order].astype(np.uint32)
    if len(h32):                                     # one posting per (term, article)
        keep = np.ones(len(h32), dtype=bool)
        keep[1:] = (h32[1:] != h32[:-1]) | (d[1:] != d[:-1])
        h32, d = h32[keep], d[keep]
    uniq, starts = np.unique(h32, return_index=True)
    ptr = np.append(starts, len(h32)).astype(np.uint32 if len(h32) < 2**32 else np.uint64)
    dfs = np.diff(ptr).astype(np.float64)
    idf = np.log(1.0 + len(titles) / np.maximum(dfs, 1.0)).astype(np.float16)
    np.save(ix / "term_hash.npy", uniq)
    np.save(ix / "ptr.npy", ptr)
    np.save(ix / "post.npy", d)
    np.save(ix / "idf.npy", idf)
    info = {"kind": "shelf_index", "format": 2, "docs": len(titles), "terms": int(len(uniq)), "postings": int(len(d)),
            "names": int(len(name_h)), **info}
    (ix / "info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    return info


def build(jsonl: list[Path], parquet: list[Path], out: Path, bucket_kb: int = 1024, sample: int = 200000,
          key_terms: int = 8, workers: int = 4, preset: int = 6, limit: int | None = None, fill: float = 0.86,
          total_hint: int | None = None, with_aliases: bool = True) -> dict:
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_parts"
    tmp.mkdir(exist_ok=True)
    bucket_bytes = bucket_kb << 10
    # 1. sample: document frequencies (hashed) and the compression ratio
    df = np.zeros(1 << HASH_BITS, dtype=np.uint32)
    n_sample = sample_bytes = 0
    blob = []
    for d in iter_docs(jsonl, parquet, limit=min(sample, limit or sample)):
        n_sample += 1
        sample_bytes += len(d["x"].encode()) + len(d["t"]) + 24
        for t in set(tokens(d["x"][:20000])) | set(tokens(d["t"])):
            df[term_hash(t) & ((1 << HASH_BITS) - 1)] += 1
        if len(blob) < 3000:
            blob.append(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    raw = ("\n".join(blob)).encode()
    ratio = len(raw) / max(1, len(lzma.compress(raw, preset=preset)))
    capacity = int(bucket_bytes * ratio * fill)
    n_docs, n_bytes = (total_hint, 0) if total_hint else count_docs(jsonl, parquet)
    if limit:
        n_docs = min(n_docs, limit)
    est_bytes = n_bytes or int(sample_bytes / max(1, n_sample) * n_docs)
    n_buckets = max(1, math.ceil(est_bytes / capacity * 1.06))
    per_volume = max(1, VOLUME_MAX // bucket_bytes)
    n_vol = math.ceil(n_buckets / per_volume)
    for v in range(n_vol):
        size = min(per_volume, n_buckets - v * per_volume) * bucket_bytes
        with open(out / f"shelf-{v}.bin", "wb") as f:
            f.truncate(size)
    print(f"[shelf] {n_docs} docs ≈ {est_bytes / 1e9:.2f} GB, ratio {ratio:.2f}, capacity {capacity / 1e6:.2f} MB, "
          f"{n_buckets} buckets in {n_vol} volume(s)", flush=True)
    # 2. assignment, partitions, key terms
    n_parts = max(1, min(512, n_buckets // 16 or 1))
    per_part = math.ceil(n_buckets / n_parts)
    parts = [open(tmp / f"p{i}.tsv", "w", encoding="utf-8") for i in range(n_parts)]
    used = np.zeros(n_buckets, dtype=np.int64)
    titles, buckets = [], []
    alias_h, alias_d = [], []
    pairs_h: list[np.ndarray] = []
    pairs_d: list[np.ndarray] = []
    buf_h, buf_d = [], []
    N_s = max(1, n_sample)
    for i, d in enumerate(iter_docs(jsonl, parquet, limit=limit)):
        size = len(d["x"].encode()) + len(d["t"]) + 24
        b = bucket_of_title(d["t"], n_buckets)
        probes = 0
        while used[b] + size > capacity and used[b] > 0 and probes < n_buckets:
            b = (b + 1) % n_buckets
            probes += 1
        used[b] += size
        aliases = d.pop("_r", None) or []
        parts[min(b // per_part, n_parts - 1)].write(f"{b}\t{json.dumps(d, ensure_ascii=False, separators=(',', ':'))}\n")
        titles.append(d["t"])
        buckets.append(b)
        if with_aliases:
            for al in aliases:
                alias_h.append(term_hash(name_key(al)))
                alias_d.append(i)
        # key terms: tf · idf from the sample, title words always
        tf: dict[str, int] = {}
        for t in tokens(d["x"][:20000]):
            tf[t] = tf.get(t, 0) + 1
        for t in tokens(d["x"][:600]):               # the opening holds the key facts: its words count triple
            tf[t] = tf.get(t, 0) + 2
        scored = sorted(((c * math.log(N_s / (1 + df[term_hash(t) & ((1 << HASH_BITS) - 1)])), t) for t, c in tf.items()),
                        reverse=True)
        keys = list(dict.fromkeys(tokens(d["t"]) + [t for _, t in scored[:key_terms]]))
        for t in keys:
            buf_h.append(term_hash(t))
            buf_d.append(i)
        if len(buf_h) > 2_000_000:
            pairs_h.append(np.array(buf_h, dtype=np.uint64))
            pairs_d.append(np.array(buf_d, dtype=np.uint32))
            buf_h, buf_d = [], []
        if (i + 1) % 200000 == 0:
            print(f"[shelf] assigned {i + 1} docs ({time.time() - t0:.0f}s)", flush=True)
    for f in parts:
        f.close()
    if buf_h:
        pairs_h.append(np.array(buf_h, dtype=np.uint64))
        pairs_d.append(np.array(buf_d, dtype=np.uint32))
    # 3. compress partitions in parallel
    jobs = [(str(tmp / f"p{i}.tsv"), str(out), bucket_bytes, per_volume, preset) for i in range(n_parts)]
    sha = [""] * n_buckets
    comp_total = truncated = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(_compress_partition, jobs):
            for b, h, c, tr in res:
                sha[b] = h
                comp_total += c
                truncated += tr
    empty = MAGIC + struct.pack("<I", len(lzma.compress(b"", preset=preset))) + lzma.compress(b"", preset=preset)
    empty += b"\0" * (bucket_bytes - len(empty))
    for b in range(n_buckets):
        if not sha[b]:                               # an unused bucket: a valid empty one
            v = b // per_volume
            with open(out / f"shelf-{v}.bin", "r+b") as fh:
                fh.seek((b % per_volume) * bucket_bytes)
                fh.write(empty)
            sha[b] = hashlib.sha256(empty).hexdigest()
    for p in tmp.glob("*.tsv"):
        p.unlink()
    tmp.rmdir()
    volumes = []
    for v in range(n_vol):
        p = out / f"shelf-{v}.bin"
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(8 << 20), b""):
                h.update(chunk)
        volumes.append({"name": p.name, "bytes": p.stat().st_size, "sha256": h.hexdigest(), "first": v * per_volume,
                        "buckets": p.stat().st_size // bucket_bytes})
    manifest = {"version": 1, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "bucket_bytes": bucket_bytes,
                "per_volume": per_volume, "buckets": n_buckets, "volumes": volumes, "bucket_sha256": sha,
                "licenses": ["Wikipedia text: CC BY-SA 4.0 / GFDL (wikimedia/wikipedia)"],
                "docs": len(titles), "truncated_to_fit": truncated}
    (out / "shelf.json").write_text(json.dumps(manifest, indent=0), encoding="utf-8")
    # the local index
    H = np.concatenate(pairs_h) if pairs_h else np.zeros(0, np.uint64)
    D = np.concatenate(pairs_d) if pairs_d else np.zeros(0, np.uint32)
    nh = np.array([term_hash(name_key(t)) for t in titles] + alias_h, dtype=np.uint64)
    nd = np.concatenate([np.arange(len(titles), dtype=np.uint32), np.array(alias_d, dtype=np.uint32)])
    info = write_index(out / "shelf_index", titles, np.array(buckets, dtype=np.int64), nh, nd, H, D, n_buckets,
                       {"key_terms": key_terms,
                        "manifest_sha256": hashlib.sha256((out / "shelf.json").read_bytes()).hexdigest()})
    ix = out / "shelf_index"
    ix_bytes = sum(p.stat().st_size for p in ix.iterdir())
    print(f"[shelf] done in {time.time() - t0:.0f}s: {len(titles)} docs, {n_buckets} buckets, "
          f"{comp_total / 1e9:.2f} GB compressed, {truncated} truncations, index {ix_bytes / 1e6:.1f} MB", flush=True)
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, action="append", default=[])
    ap.add_argument("--parquet", type=Path, action="append", default=[])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--bucket-kb", type=int, default=1024)
    ap.add_argument("--sample", type=int, default=200000)
    ap.add_argument("--key-terms", type=int, default=8)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--preset", type=int, default=6)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--total", type=int, help="number of documents, when the input cannot be counted cheaply")
    ap.add_argument("--no-aliases", action="store_true", help="leave the redirect name forms out of the index")
    a = ap.parse_args(argv)
    build(a.jsonl, a.parquet, a.out, a.bucket_kb, a.sample, a.key_terms, a.workers, a.preset, a.limit,
          total_hint=a.total, with_aliases=not a.no_aliases)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
