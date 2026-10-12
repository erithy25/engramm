"""Training data for the H100 run toward Stage 1 (docs/H100_ANLEITUNG.md).

    python -m experiments.h100_data base                  # rebuild the LM-study splits, SHA-256 of every file
    python -m experiments.h100_data extra --shards 36     # further C4-en shards as training text
    python -m experiments.h100_data merge                 # one training stream: base train + extra shards
    python -m experiments.h100_data contamination         # 13-token overlap of every val/test document with it
    python -m experiments.h100_data check-dedup           # the overlap code reproduces results/lm/dedup.json

``base`` runs ``experiments.lm_prepare`` (checksummed public sources, pinned tokenizer) unless the token files
already exist, and then compares every file with the SHA-256 recorded from the CPU machine: the H100 run must
be scored on exactly the val/test documents of the LM study, otherwise the comparison with GPT-2 means nothing.

``extra`` downloads C4-en training shards 1, 2, … (SHA-256 pinned from the Hugging Face file listing, retried,
verified before use), keeps only documents that ``data.lm_corpus.split_of`` assigns to *train* (the same
content-independent hash as the base corpus, so no document of the val/test buckets enters), extracts them as the
base corpus does (``text.strip()``, empty texts dropped) and tokenises them with the pinned tokenizer. One shard
at a time; a finished shard has a marker file, so the step can be resumed.

``contamination`` hashes every 13-token window of the val/test documents and looks each one up in the full
training stream (base + extra). A document with ≥ 20 % of its windows found is a near-duplicate — the rule of
``experiments/lm_suffix.py`` (results/lm/dedup.json). The base part alone must reproduce that file; the
extended list adds documents that only the extra text duplicates.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import time
import urllib.request
from multiprocessing import Pool
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
TOK = REPO / "data" / "cache" / "lm" / "tokens"
EXTRA = TOK / "extra"
H100 = TOK / "h100"
RESULTS = REPO / "results" / "v5" / "h100"
EVAL_SPLITS = ("val_a", "val_b", "test", "wt103_test")
WIDTH, THRESHOLD = 13, 0.20                       # experiments/lm_suffix.py
EOS = 0

#: SHA-256 of the token files as built on the CPU machine (data/cache/lm/tokens, token_version 1).
BASE_SHA256 = {
    "train.u16": "0bb69de49af77468706818c2c326c95951d0d2667b1eeaebb20ad55cc4c18b1d",
    "train.starts.npy": "d9518402beee2dad279685850ef121cff247ee39d4409f17525c5b6ab55489a6",
    "train.bytes.npy": "306377dacc05f14432df2c9b18bc9114e3cf51e6a760d4913c67bc0b529506e8",
    "val_a.u16": "c086e6963b3c1785aeff1502b19416aa99a5e70808d1c3a2264bb939cbc6d88c",
    "val_a.starts.npy": "d0bcaa499135460cbd57bc1dcf0a6cb57a4919851dc4b4ee3874e7d19ff86659",
    "val_a.bytes.npy": "26bc72d94ba2f47a607921de13e38a810a54ed8f31b2239af2964061b583a79c",
    "val_b.u16": "7f208f22e5f6294bac89af470cb8c99e63e2c65b869574a0c55c50d86daa1551",
    "val_b.starts.npy": "7da568bdb212e0c9e5087ea0361cb9fe639c77ad36521bc5a348fcd8f9dfc2ba",
    "val_b.bytes.npy": "d7556007f88a20566ef567a05a1437054882147f8d2762d2d1c88271dccabe8c",
    "test.u16": "8f4bb2e676b6fbac624ad586c3f63f260a880ee6e61f15980a1499c97c792a4d",
    "test.starts.npy": "d8fdc5862c6b9fcbb8dbf14dba8af218e16448a3f4632a52faf1314941ab2756",
    "test.bytes.npy": "88c4ffbb755e3380acd8b94519f3ff6920da3c548f055c63b6dd8cd1da250377",
    "wt103_test.u16": "18e4387d63380b623ab85bf77d0c02890d90a608cd70fea7d22f4b9ecc251a3c",
    "wt103_test.starts.npy": "795ba46fa5fe97d7ae5553cd167b847552d602401c0b62ee8b36af07422f5844",
    "wt103_test.bytes.npy": "5466e75558fb4254d017bbf7455fa6f60cb41878edbb5622f3e921a696be0818",
}

C4_URL = "https://huggingface.co/datasets/allenai/c4/resolve/main/en/c4-train.{k:05d}-of-01024.json.gz"
#: (SHA-256, bytes) of C4-en training shards from the Hugging Face file listing (LFS object ids), 12 Oct 2026.
#: Shard 0 is the base corpus (data/lm_corpus.py pins the same digest).
C4_SHARDS = {
    1: ("b945059cd1a343cabe311881b7840a6f0363f570e745a0eff0e687e266f6b55d", 318039285),
    2: ("2967dc7e587ced6ecb9ba617ad2d4c44901467969de5bf5b0f5a9e5b70555d75", 319748667),
    3: ("b79d9abef5741578929be0d59db9ca652a8276207ef18a944b7a5f11fef5beb6", 318564193),
    4: ("cd9f98eac2bc6062f55d9a36bd744cc924a78ea2fd998830e0034e4456f5d014", 318579884),
    5: ("8ac5907a54dbc7ab9c14624448c7c3f6afed33af9d0a855f1eae955e62e255b9", 318003681),
    6: ("8fd9b9a4b74c9414466b245ebda7db041e7bd8603971de51b5db782bd758aac7", 318495137),
    7: ("41dd377a1ba6b72eab0260c39c626fe45ab6b649d42d57b311d3ba21a0337cd0", 318417273),
    8: ("64da652c235f089a0b52f6db5883ef5f1e9c31edc4c950332b34dd12439c99a5", 318131845),
    9: ("807a548efbb10153c9eff0df5733a97a1b51ab1743242530de1b02a8ea17ace7", 318185592),
    10: ("3bd0f6f664069c3bd964ce48ceae60ba47b55b54745a4b00c207bdb3a1926b17", 319045292),
    11: ("5baa0c010083459ba58e34b4e93bb758caa878f7db6fba0528921329fa1a6cc5", 319686980),
    12: ("fdee7442c06856e2c4b7665cc51978e9011b5e0a2112c30dd15bc9e53818842d", 320119088),
    13: ("a4ab3b24087781c3577945492525696e182ffd7ca5265b958f49803a02867ecf", 319474856),
    14: ("62215b2451e71b117018ef73570c944aff890624b384c538950b64c37f184c49", 319693210),
    15: ("9893c9f413a1223e7b535527829bcd6df3219929fb1abf8f2a114dd8f6ea0919", 318427305),
    16: ("bd0ade8b8a57348952ca31c39efdab538f54c852941a225ccd13d0a7170724e3", 318785714),
    17: ("4132cfff3f5126d9e783191a5ccc34e5d85938bebf0b8489657805277a227202", 320134331),
    18: ("4675ab1d77da3d676d9743dca15bfce8478498f7738f79816a25ed790d28fa46", 318653930),
    19: ("1d2f3a6aeb0f6c159295f283d302794cd3eb944cff3fe68691997bb2dc4c7780", 319468974),
    20: ("b5f26d832a0ec9b0489a27169d94496f5ea33c7fb046868c565c7b5a2407221b", 319109754),
    21: ("428da5a8d4585de16f6b3f30865a5ca7a8d1ddcd3b6002dcc1283368b0c3d60a", 318514423),
    22: ("9bc4812ba5e08c0b2d83cd3804129ba3d77cf84ba3d8828159788ee02e155a51", 318715623),
    23: ("38843ab4f5c60ed2b9ec0cdc65074eaca454014d5702edd809a266190689d2c3", 319874293),
    24: ("4fa0c7ec94445ea57dcecda7864b1346275e711c9820c2c39dbb9fdb95c97674", 318105764),
    25: ("0758514fa2e2c133c995c00d5f4abfc14b66582a4eedd0e721bdd95c4632a755", 319122521),
    26: ("56a73b9a556d6794d9c706e1b1c7e729fa13b711ddc25dd403b110eb5ed857f1", 318116783),
    27: ("fea1eabb734cda33d72f3d959234a240080b4fd42cc70494814a8429b087f9e1", 320171191),
    28: ("47d1c385952d6c18c431a7294339a030c213b8832f970ac987965b621c8181a1", 319047090),
    29: ("3c744d3dd915ceef3a93fd18c3ff5b117fb5118d1ced2089979b6cafc81c4525", 318705639),
    30: ("7f6959020242fdc841adfc10c102bbe79e2ef8502a09dac8451e0cec6f2add16", 318327902),
    31: ("e56f29011594c765192c34298558e7227a829313196748f9a16ec34ecdb76d23", 318990600),
    32: ("9ea843dfd85e449439f3106d657762daff8f326730fefb342455c43cb48144e3", 320451482),
    33: ("2633cdb7b058f126173608897f69add614659b0b21cf54ecc8a2f4a79bc16073", 319878207),
    34: ("853c4b9ff2d79621ed27a6be826dae198af609d9f9dbd1c2773b778241cf6137", 318701510),
    35: ("fb50dac3f35cb71472464f511e6b8aee72ded10b3b6896d0d1f74a18ded2b8d3", 318529104),
    36: ("5cef5cfd50cfafd58feb452b85324a3d8198fca48789f0ce69227755e72d8e53", 318849657),
    37: ("f0b67abf30e2d58d291aa9bcc9c8a03668afe819549802e4e591a261c171d970", 319621215),
    38: ("991bad578a83294d34a1b11649af07339aa8cb26d49330afa9fcbca0b87942c6", 318135467),
    39: ("abbbc21f81555e94484e6afe1975e13f67af19a820cd6f8d090c987a250bd4fd", 320131759),
    40: ("48020d2656709899abd2572b3424c0455df3c1089a69fe26b776aeb24f0da0ec", 320214476),
    41: ("db6fb8db7162ac87ea002c153ef0c54322f24c8f7ec263cfa290ac8c3683b194", 319581259),
    42: ("d499cba2383b16bb0f26b98416211eabf2599641ecd6708a5ef487692ca9e791", 318100985),
    43: ("dc6f1ccc3fcce79b16c5157f7125942e351d74744efc593f8372f8a408720340", 317803029),
    44: ("6170fced793461bd687640a658a085d02f971c2e609f6ff33b90df944fb56409", 318837063),
    45: ("b2f79e8600815578ec326cfc6c5242c2827cedbfac51772fdcf15ef5d027aa38", 319659188),
}


def sha256_file(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# base splits
# ---------------------------------------------------------------------------

def verify_base() -> list[str]:
    """Names of base token files that are missing or differ from the CPU machine's."""
    bad = []
    for name, digest in BASE_SHA256.items():
        p = TOK / name
        if not p.exists() or sha256_file(p) != digest:
            bad.append(name)
    return bad


def cmd_base(args) -> None:
    bad = verify_base()
    if not bad:
        log("base token files present and identical to the CPU machine's (SHA-256)")
        return
    log(f"building the base splits (experiments.lm_prepare); missing/different: {bad}")
    from experiments import lm_prepare
    import sys
    argv, sys.argv = sys.argv, ["lm_prepare"]
    try:
        lm_prepare.main()
    finally:
        sys.argv = argv
    bad = verify_base()
    if bad:
        raise SystemExit(f"base token files differ from the CPU machine's after rebuilding: {bad}. "
                         f"Do not train on them (check the tokenizers version: 0.23.2 expected).")
    log("base splits rebuilt; every file identical to the CPU machine's (SHA-256)")


# ---------------------------------------------------------------------------
# extra C4 shards
# ---------------------------------------------------------------------------

def download(url: str, dest: Path, sha256: str, size: int, tries: int = 8) -> None:
    """Download with retries (exponential back-off); the file is accepted only with the pinned digest."""
    part = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, tries + 1):
        try:
            h = hashlib.sha256()
            n = 0
            with urllib.request.urlopen(url, timeout=120) as r, open(part, "wb") as f:
                while True:
                    block = r.read(1 << 22)
                    if not block:
                        break
                    h.update(block)
                    f.write(block)
                    n += len(block)
            if n != size or h.hexdigest() != sha256:
                raise OSError(f"got {n} bytes, SHA-256 {h.hexdigest()}; expected {size} bytes, {sha256}")
            part.replace(dest)
            return
        except Exception as e:                       # network errors, truncated or wrong files
            part.unlink(missing_ok=True)
            if attempt == tries:
                raise SystemExit(f"download failed {tries}× ({url}): {e}")
            wait = min(300, 10 * 2 ** (attempt - 1))
            log(f"download attempt {attempt} failed ({e}); retrying in {wait} s")
            time.sleep(wait)


def shard_name(k: int) -> str:
    return f"c4_{k:05d}"


def cmd_extra(args) -> None:
    from data.lm_corpus import split_of
    from engramm.lm.stream import build_split
    from engramm.lm.tokenizer import LMTokenizer
    if args.shards > max(C4_SHARDS):
        raise SystemExit(f"at most {max(C4_SHARDS)} shards are pinned")
    tok = LMTokenizer()                                     # checks the tokenizer's SHA-256
    EXTRA.mkdir(parents=True, exist_ok=True)
    for k in range(1, args.shards + 1):
        name = shard_name(k)
        marker = EXTRA / f"{name}.done.json"
        if marker.exists():
            m = json.loads(marker.read_text())
            if (EXTRA / f"{name}.u16").exists() and (EXTRA / f"{name}.u16").stat().st_size == 2 * m["tokens"]:
                continue
        digest, size = C4_SHARDS[k]
        gz = EXTRA / f"c4-train.{k:05d}.json.gz"
        t0 = time.time()
        if not gz.exists():
            download(C4_URL.format(k=k), gz, digest, size)
        texts, keys, held_out, empty = [], [], 0, 0
        with gzip.open(gz, "rt", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                text = rec["text"].strip()
                if not text:
                    empty += 1
                    continue
                if split_of("c4", rec["url"]) != "train":       # val/test hash buckets never train
                    held_out += 1
                    continue
                texts.append(text)
                keys.append(("c4", rec["url"]))
        ts = build_split(texts, keys, tok.encode_batch, batch=4096)
        ts.save(EXTRA, name)
        stats = {"shard": k, "sha256_gz": digest, "docs": ts.n_docs, "tokens": int(len(ts.tokens)),
                 "bytes": int(ts.doc_bytes.sum()), "held_out_val_test_bucket": held_out, "empty": empty,
                 "u16_sha256": sha256_file(EXTRA / f"{name}.u16"), "seconds": round(time.time() - t0, 1)}
        marker.write_text(json.dumps(stats) + "\n")
        gz.unlink()
        log(f"shard {k}/{args.shards}: {stats['docs']} docs, {stats['tokens'] / 1e6:.1f} M tokens "
            f"({held_out} in val/test buckets skipped), {stats['seconds']} s")
        del texts, keys, ts


# ---------------------------------------------------------------------------
# merged training stream
# ---------------------------------------------------------------------------

def cmd_merge(args) -> None:
    """train_all = base train, then every extra shard, as one stream [EOS] d [EOS] d … [EOS]."""
    H100.mkdir(parents=True, exist_ok=True)
    parts = [("base", TOK / "train")] + [(shard_name(k), EXTRA / shard_name(k)) for k in range(1, args.shards + 1)]
    for label, stem in parts:
        if not Path(f"{stem}.u16").exists():
            raise SystemExit(f"missing {stem}.u16 — run the base/extra steps first")
    out = H100 / "train_all.u16"
    starts_all, bytes_all, manifest = [], [], []
    pos = 0
    with open(out.with_suffix(".u16.part"), "wb") as f:
        for i, (label, stem) in enumerate(parts):
            tokens = np.fromfile(f"{stem}.u16", dtype=np.uint16)
            starts = np.load(f"{stem}.starts.npy").astype(np.int64)
            nbytes = np.load(f"{stem}.bytes.npy").astype(np.int64)
            if tokens[0] != EOS or tokens[-1] != EOS or (tokens[starts - 1] != EOS).any():
                raise SystemExit(f"{stem}: stream is not [EOS] d [EOS] …")
            if i == 0:
                body, shift = tokens, pos
            else:                                   # the previous part already ends with EOS
                body, shift = tokens[1:], pos - 1
            body.tofile(f)
            starts_all.append(starts + shift)
            bytes_all.append(nbytes)
            manifest.append({"part": label, "docs": int(len(starts)), "tokens": int(len(body))})
            pos += len(body)
            log(f"merged {label}: {len(starts)} docs, total {pos / 1e9:.3f} B tokens")
    out.with_suffix(".u16.part").replace(out)
    starts = np.concatenate(starts_all)
    np.save(H100 / "train_all.starts.npy", starts)
    np.save(H100 / "train_all.bytes.npy", np.concatenate(bytes_all))
    tokens = np.memmap(out, dtype=np.uint16, mode="r")
    if len(tokens) != pos or tokens[0] != EOS or tokens[-1] != EOS or (tokens[starts - 1] != EOS).any() \
            or (np.diff(starts) <= 0).any():
        raise SystemExit("merged stream failed its structure check")
    info = {"tokens": int(pos), "docs": int(len(starts)), "base_tokens": manifest[0]["tokens"], "parts": manifest}
    (H100 / "train_all.json").write_text(json.dumps(info, indent=1) + "\n")
    log(f"train_all: {info['docs']} docs, {pos / 1e9:.3f} B tokens")


# ---------------------------------------------------------------------------
# contamination: 13-token windows of val/test documents in the training stream
# ---------------------------------------------------------------------------

_P = np.uint64(0x9E3779B97F4A7C15)


def window_hashes(a: np.ndarray, width: int = WIDTH) -> np.ndarray:
    """Polynomial hash (mod 2^64) of every ``width``-token window of ``a``; len(a) − width + 1 values."""
    n = len(a) - width + 1
    if n <= 0:
        return np.zeros(0, dtype=np.uint64)
    x = a.astype(np.uint64) + np.uint64(1)
    h = x[:n].copy()
    with np.errstate(over="ignore"):
        for j in range(1, width):
            h *= _P
            h += x[j:j + n]
    return h


def eval_windows(split: str):
    """Window hashes of every document's content tokens (as lm_suffix: windows inside [start, EOS))."""
    tokens = np.fromfile(TOK / f"{split}.u16", dtype=np.uint16)
    starts = np.load(TOK / f"{split}.starts.npy").astype(np.int64)
    ends = np.append(starts[1:] - 1, len(tokens) - 1)
    return [window_hashes(tokens[s:e]) for s, e in zip(starts, ends)]


_SHARED: dict = {}


def _init(path: str, keys: np.ndarray) -> None:
    _SHARED["tokens"] = np.memmap(path, dtype=np.uint16, mode="r")
    _SHARED["keys"] = keys


def _found_in(span: tuple[int, int]) -> np.ndarray:
    a, b = span
    h = window_hashes(np.asarray(_SHARED["tokens"][a:min(b + WIDTH - 1, len(_SHARED["tokens"]))]))
    keys = _SHARED["keys"]
    i = np.searchsorted(keys, h)
    i[i == len(keys)] = 0
    return np.unique(h[keys[i] == h])


def found_hashes(path: Path, lo: int, hi: int, keys: np.ndarray, workers: int, chunk: int = 1 << 25) -> np.ndarray:
    """The val/test window hashes that occur in tokens[lo:hi] (windows starting in that range)."""
    spans = [(a, min(a + chunk, hi)) for a in range(lo, hi, chunk)]
    with Pool(workers, initializer=_init, initargs=(str(path), keys)) as pool:
        parts = pool.map(_found_in, spans, chunksize=1)
    return np.unique(np.concatenate(parts)) if parts else np.zeros(0, dtype=np.uint64)


def overlap_report(path: Path, base_tokens: int, total_tokens: int, workers: int) -> dict:
    per_split = {s: eval_windows(s) for s in EVAL_SPLITS}
    keys = np.unique(np.concatenate([h for docs in per_split.values() for h in docs]))
    log(f"{len(keys)} distinct val/test windows; scanning {total_tokens / 1e9:.3f} B training tokens")
    t0 = time.time()
    f_base = found_hashes(path, 0, base_tokens - WIDTH + 1, keys, workers)
    f_all = f_base if total_tokens == base_tokens else \
        np.union1d(f_base, found_hashes(path, base_tokens - WIDTH + 1, total_tokens - WIDTH + 1, keys, workers))
    log(f"scan done in {time.time() - t0:.0f} s")
    rep = {"width": WIDTH, "threshold": THRESHOLD, "train_tokens": int(total_tokens),
           "base_tokens": int(base_tokens), "splits": {}}
    for split, docs in per_split.items():
        fb = np.array([np.isin(h, f_base).mean() if len(h) else 0.0 for h in docs])
        fa = np.array([np.isin(h, f_all).mean() if len(h) else 0.0 for h in docs])
        rep["splits"][split] = {"docs": len(docs),
                                "excluded_base": np.flatnonzero(fb >= THRESHOLD).tolist(),
                                "excluded_all": np.flatnonzero(fa >= THRESHOLD).tolist(),
                                "mean_overlap_base": float(fb.mean()), "mean_overlap_all": float(fa.mean())}
    return rep


def compare_with_dedup(rep: dict) -> dict:
    ref = json.loads((REPO / "results" / "lm" / "dedup.json").read_text())["splits"]
    out = {}
    for split, r in rep["splits"].items():
        a, b = set(r["excluded_base"]), set(ref[split]["excluded"])
        out[split] = {"same": a == b, "only_new": sorted(a - b), "only_reference": sorted(b - a)}
    return out


def cmd_contamination(args) -> None:
    info = json.loads((H100 / "train_all.json").read_text())
    rep = overlap_report(H100 / "train_all.u16", info["base_tokens"], info["tokens"], args.workers)
    rep["base_matches_dedup_json"] = compare_with_dedup(rep)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "contamination.json").write_text(json.dumps(rep, indent=1) + "\n")
    for split, r in rep["splits"].items():
        log(f"{split}: excluded base {len(r['excluded_base'])}, with extra text {len(r['excluded_all'])} "
            f"of {r['docs']}; base == dedup.json: {rep['base_matches_dedup_json'][split]['same']}")
    if not all(v["same"] for v in rep["base_matches_dedup_json"].values()):
        log("WARNING: the base-only exclusions differ from results/lm/dedup.json — see contamination.json")


def cmd_check_dedup(args) -> None:
    """Self-test on the CPU machine: the hashing code reproduces results/lm/dedup.json on the base train."""
    path = TOK / "train.u16"
    n = os.path.getsize(path) // 2
    rep = overlap_report(path, n, n, args.workers)
    cmp = compare_with_dedup(rep)
    print(json.dumps(cmp, indent=1), flush=True)
    if not all(v["same"] for v in cmp.values()):
        raise SystemExit("overlap code does not reproduce results/lm/dedup.json")
    log("overlap code reproduces results/lm/dedup.json exactly")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("base")
    for name in ("extra", "merge"):
        p = sub.add_parser(name)
        p.add_argument("--shards", type=int, default=36)
    for name in ("contamination", "check-dedup"):
        p = sub.add_parser(name)
        p.add_argument("--workers", type=int, default=max(1, min(16, (os.cpu_count() or 2) - 2)))
    args = ap.parse_args()
    import socket
    socket.setdefaulttimeout(300)          # a stalled download (also inside lm_prepare) fails instead of hanging
    {"base": cmd_base, "extra": cmd_extra, "merge": cmd_merge, "contamination": cmd_contamination,
     "check-dedup": cmd_check_dedup}[args.cmd](args)


if __name__ == "__main__":
    main()
