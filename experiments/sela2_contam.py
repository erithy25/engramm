"""Contamination audit after the Sela-2 run (docs/PREREG_SELA2.md §4): which benchmark items occur in the tokens the
model actually trained on.

    python -m experiments.sela2_contam items --out items.npz                      # benchmark windows (needs the tokenizer)
    python -m experiments.sela2_contam files --meta pretrain_meta.json --shard 0 --shards 4    # what to download
    python -m experiments.sela2_contam scan --data DIR --meta pretrain_meta.json --items items.npz --out hits_0.npy --shard 0 --shards 4
    python -m experiments.sela2_contam collect --items items.npz --hits DIR --out results/sela2/contamination.json

The check works on tokens (the training data are token streams): every benchmark item's text — context plus the
gold continuation; WinoGrande with each option filled into the blank — is encoded with the Sela-2 tokenizer (as
written and with a leading space), and every window of 13 consecutive tokens is hashed (polynomial hash mod 2^64).
The trained tokens are the first ``tokens_used`` tokens of each source group (rows are read in file order, see
experiments/sela2_train.py Source) plus the decay-phase chat streams. An item counts as contaminated when at least
min(3, its number of windows) of its windows occur in the trained tokens; items shorter than 13 tokens cannot be
checked and are reported as such.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

N = 13
_P = np.uint64(0x9E3779B97F4A7C15)
CHUNK = 1 << 25                                     # tokens per scan step (≈ 270 MB of hashes)


def windows(ids: np.ndarray, n: int = N) -> np.ndarray:
    m = len(ids) - n + 1
    if m <= 0:
        return np.zeros(0, dtype=np.uint64)
    x = ids.astype(np.uint64)
    h = np.zeros(m, dtype=np.uint64)
    with np.errstate(over="ignore"):
        for j in range(n):
            h = h * _P + x[j:j + m]
    return h


def item_texts(task: str, item: dict) -> list[str]:
    """The texts of one benchmark item that a training document could contain."""
    reqs, gold = item["requests"], item["gold"]
    if task == "winogrande":
        return [ctx + cont for ctx, cont in reqs]           # both options filled in
    ctx, cont = reqs[gold]
    return [ctx + cont]


def cmd_items(args) -> None:
    from engramm.lm.tokenizer import LMTokenizer
    from experiments.sela2_bench import EXPECTED_ITEMS, load_task
    tok = LMTokenizer(args.tokenizer, sha256=None)
    owners, hashes, nwin, tasks = [], [], {}, []
    for t_i, task in enumerate(sorted(EXPECTED_ITEMS)):
        items, _ = load_task(task)
        tasks.append(task)
        for i, it in enumerate(items):
            hs = []
            for text in item_texts(task, it):
                for variant in (text, " " + text.lstrip()):
                    hs.append(windows(np.asarray(tok.encode(variant), dtype=np.uint16)))
            h = np.unique(np.concatenate(hs)) if hs else np.zeros(0, dtype=np.uint64)
            nwin[(t_i, i)] = len(h)
            hashes.append(h)
            owners.append(np.full(len(h), t_i * 100_000 + i, dtype=np.int64))
        print(f"{task}: {len(items)} items", flush=True)
    H = np.concatenate(hashes)
    O = np.concatenate(owners)
    order = np.argsort(H, kind="stable")
    keys = np.array([k[0] * 100_000 + k[1] for k in nwin], dtype=np.int64)
    np.savez(args.out, hashes=H[order], owners=O[order], keys=keys,
             nwin=np.array(list(nwin.values()), dtype=np.int64), tasks=np.array(tasks))
    print(f"{len(H)} windows of {len(keys)} items -> {args.out}")


def group_of(name: str) -> str:
    """Source group of a stream file name, as experiments/sela2_train.py has it (no torch needed here)."""
    return re.sub(r"(_\d+)+$", "", name)


def trained_ranges(manifest: dict, meta: dict) -> list[tuple[str, int]]:
    """(stream name, tokens used from its start) for every stream the pretraining read, from the data manifest
    (results/sela2/data/manifest.json: tokens per stream) and the run's data report (tokens used per source)."""
    rep = meta.get("data_report") or {}
    files: dict[str, list[tuple[str, int]]] = {}
    for st in sorted(manifest["streams"], key=lambda r: r["name"]):
        name = st["name"]
        if name.startswith(("val_", "lm_")) or name.endswith(("_sft", "_val")):
            continue
        files.setdefault(group_of(name), []).append((name, int(st["tokens"])))
    out = []
    for g, items in sorted(files.items()):
        used = int((rep.get(g) or {}).get("tokens_used", 0))
        if (rep.get(g) or {}).get("repeats"):
            used = sum(n for _, n in items)        # read more than once: everything was seen
        for name, n in items:
            take = min(n, used)
            if take > 0:
                out.append((name, take))
            used -= take
    return out


def shard_files(manifest: dict, meta: dict, shard: int, shards: int) -> list[tuple[str, int]]:
    return [r for i, r in enumerate(trained_ranges(manifest, meta)) if i % shards == shard]


def cmd_files(args) -> None:
    """The stream files one scan shard needs (for a selective download)."""
    man = json.loads(Path(args.manifest).read_text())
    meta = json.loads(Path(args.meta).read_text())
    print("|".join(f"{n}.u16" for n, _ in shard_files(man, meta, args.shard, args.shards)))


def cmd_scan(args) -> None:
    z = np.load(args.items)
    table = z["hashes"]
    meta = json.loads(Path(args.meta).read_text())
    man = json.loads(Path(args.manifest).read_text())
    found = np.zeros(len(table), dtype=bool)
    total = 0
    for name, take in shard_files(man, meta, args.shard, args.shards):
        p = Path(args.data) / f"{name}.u16"
        mm = np.memmap(p, dtype=np.uint16, mode="r")
        if len(mm) < take:
            raise SystemExit(f"{p}: {len(mm)} tokens, the run read {take}")
        for a in range(0, take, CHUNK):
            b = min(take, a + CHUNK + N - 1)
            h = windows(np.asarray(mm[a:b]))
            pos = np.searchsorted(table, h)
            pos[pos >= len(table)] = len(table) - 1
            hit = table[pos] == h
            if hit.any():
                found[np.isin(table, np.unique(h[hit]))] = True
            total += b - a
        print(f"{p.name}: {take / 1e6:.0f} M tokens scanned", flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    np.save(args.out, found)
    print(f"shard {args.shard}/{args.shards}: {total / 1e9:.2f} B tokens, {int(found.sum())} item windows found")


def cmd_collect(args) -> None:
    z = np.load(args.items)
    found = np.zeros(len(z["hashes"]), dtype=bool)
    parts = sorted(Path(args.hits).rglob("hits_*.npy"))
    for f in parts:
        found |= np.load(f)
    owners = z["owners"][found]
    hit_count: dict[int, int] = {}
    for o in owners:                                   # distinct windows per item (hashes are unique per item)
        hit_count[int(o)] = hit_count.get(int(o), 0) + 1
    tasks = [str(t) for t in z["tasks"]]
    res = {"what": "token 13-gram contamination audit (experiments/sela2_contam.py)", "parts": len(parts), "tasks": {}}
    for key, nw in zip(z["keys"], z["nwin"]):
        t_i, i = divmod(int(key), 100_000)
        e = res["tasks"].setdefault(tasks[t_i], {"items": 0, "uncheckable": [], "contaminated": []})
        e["items"] += 1
        if nw == 0:
            e["uncheckable"].append(i)
        elif hit_count.get(int(key), 0) >= min(3, int(nw)):
            e["contaminated"].append(i)
    for e in res["tasks"].values():
        e["contaminated_share"] = len(e["contaminated"]) / max(1, e["items"])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res) + "\n")
    print(json.dumps({t: {k: (v if not isinstance(v, list) else len(v)) for k, v in e.items()} for t, e in res["tasks"].items()}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("items")
    p.add_argument("--tokenizer", default="data/lm2_tokenizer.json")
    p.add_argument("--out", required=True)
    p = sub.add_parser("files")
    p.add_argument("--manifest", default="results/sela2/data/manifest.json")
    p.add_argument("--meta", required=True)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=1)
    p = sub.add_parser("scan")
    p.add_argument("--data", required=True)
    p.add_argument("--manifest", default="results/sela2/data/manifest.json")
    p.add_argument("--meta", required=True, help="pretrain_meta.json of the run (data_report: tokens used per source)")
    p.add_argument("--items", required=True)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=1)
    p.add_argument("--out", required=True)
    p = sub.add_parser("collect")
    p.add_argument("--items", required=True)
    p.add_argument("--hits", required=True)
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    {"items": cmd_items, "files": cmd_files, "scan": cmd_scan, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    main()
