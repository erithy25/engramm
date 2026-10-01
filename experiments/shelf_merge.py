"""Merge shelf builds (experiments/shelf_build.py, same bucket size) into one shelf — so the full
Wikipedia can be built as many small parts in parallel (one per dump shard, .github/workflows/
shelf.yml) and published as one.

Volumes keep their bytes (renamed <part folder>-shelf-<v>.bin, moved or copied); bucket and article
numbers are shifted; the manifest lists which buckets each volume holds; the local index is
rebuilt in the compact form with global idf. ``--no-aliases`` leaves redirect name forms out
(the smaller index of the Lite pack).

    python experiments/shelf_merge.py --part build/s00 --part build/s01 … --out shelf/ [--move] [--no-aliases]
    python experiments/shelf_merge.py --index-only --part shelf/ --out lite/ --no-aliases

With ``--index-only`` the volumes are not touched: the parts' volumes were published already
under the names the merged manifest gives them (s07-shelf-0.bin for the part folder "s07").
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engramm.web.shelf import ShelfIndex, name_key, term_hash  # noqa: E402
from experiments.shelf_build import write_index  # noqa: E402


def _volumes(m: dict) -> list[dict]:
    out = []
    for i, v in enumerate(m["volumes"]):
        first = v.get("first", i * m["per_volume"])
        n = v.get("buckets", min(m["per_volume"], m["buckets"] - first))
        out.append({**v, "first": first, "buckets": n})
    return out


def merge(parts: list[Path], out: Path, aliases: bool = True, move: bool = False, index_only: bool = False) -> dict:
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    mans = [json.loads((p / "shelf.json").read_text(encoding="utf-8")) for p in parts]
    bucket_bytes = mans[0]["bucket_bytes"]
    if any(m["bucket_bytes"] != bucket_bytes for m in mans):
        raise SystemExit("all parts need the same bucket size")
    volumes, sha, licenses = [], [], []
    titles: list[str] = []
    buckets, name_h, name_d, term_h, term_d = [], [], [], [], []
    b_off = d_off = 0
    for k, (p, m) in enumerate(zip(parts, mans)):
        ix = ShelfIndex(p / "shelf_index")
        n = len(ix)
        for v in _volumes(m):
            name = v["name"] if len(parts) == 1 else f"{p.name}-{v['name']}"
            if not index_only:
                src, dst = p / v["name"], out / name
                if move:
                    os.replace(src, dst)
                else:
                    shutil.copyfile(src, dst)
            volumes.append({"name": name, "bytes": v["bytes"], "sha256": v["sha256"], "first": b_off + v["first"],
                            "buckets": v["buckets"]})
        sha += m["bucket_sha256"]
        licenses += [x for x in m.get("licenses", []) if x not in licenses]
        part_titles = [ix.title(i) for i in range(n)]
        titles += part_titles
        buckets.append(np.asarray(ix.bucket, dtype=np.int64) + b_off)
        nh, nd = np.asarray(ix.name_hash, dtype=np.uint64), np.asarray(ix.name_doc, dtype=np.int64)
        if not aliases:                              # only the titles themselves
            th = np.array([term_hash(name_key(t)) for t in part_titles], dtype=np.uint64)
            keep = nh == th[nd]
            nh, nd = nh[keep], nd[keep]
        name_h.append(nh)
        name_d.append(nd + d_off)
        ptr = np.asarray(ix.ptr, dtype=np.int64)
        term_h.append(np.repeat(np.asarray(ix.term_hash).astype(np.uint64), np.diff(ptr)))
        term_d.append(np.asarray(ix.post, dtype=np.int64) + d_off)
        b_off += m["buckets"]
        d_off += n
        print(f"[merge] part {k + 1}/{len(parts)}: {n} docs, {m['buckets']} buckets ({time.time() - t0:.0f}s)", flush=True)
    manifest = {"version": 1, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "bucket_bytes": bucket_bytes,
                "per_volume": max(v["buckets"] for v in volumes), "buckets": b_off, "volumes": volumes,
                "bucket_sha256": sha, "licenses": licenses, "docs": d_off, "parts": len(parts),
                "truncated_to_fit": sum(m.get("truncated_to_fit", 0) for m in mans)}
    if index_only and len(parts) == 1:
        manifest = {**mans[0], "volumes": volumes}
    (out / "shelf.json").write_text(json.dumps(manifest, indent=0), encoding="utf-8")
    import hashlib
    info = write_index(out / "shelf_index", titles, np.concatenate(buckets), np.concatenate(name_h),
                       np.concatenate(name_d), np.concatenate(term_h), np.concatenate(term_d), b_off,
                       {"aliases": aliases, "parts": len(parts),
                        "manifest_sha256": hashlib.sha256((out / "shelf.json").read_bytes()).hexdigest()})
    size = sum(f.stat().st_size for f in (out / "shelf_index").iterdir())
    print(f"[merge] {d_off} docs, {b_off} buckets, {len(volumes)} volumes, index {size / 1e6:.1f} MB "
          f"({time.time() - t0:.0f}s)", flush=True)
    return {**info, "index_bytes": size}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--move", action="store_true", help="move the volume files instead of copying them")
    ap.add_argument("--no-aliases", action="store_true")
    ap.add_argument("--index-only", action="store_true", help="only rebuild the index (volumes stay where they are)")
    a = ap.parse_args(argv)
    merge(a.part, a.out, aliases=not a.no_aliases, move=a.move, index_only=a.index_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
