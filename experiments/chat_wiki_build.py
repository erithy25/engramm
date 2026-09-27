"""ENGRAMM-Chat v10: read more Wikipedia (a larger corpus for open questions, A3).

    python -m experiments.chat_wiki_build extract   # → models/lm/main/wiki/extra.{u16,starts.npy,bytes.npy,keys.jsonl}
    python -m experiments.chat_wiki_build index     # → models/lm/main/chat3 (corpus = train + extra, v2 index)

Source: the English Wikipedia of 2023-11-01 (``wikimedia/wikipedia``, 41 Parquet shards,
downloaded one at a time and deleted after use). Selection depends only on the article
itself, never on a question: every article with at least ``MIN_CHARS`` characters
contributes its first ``LEAD_CHARS`` characters (cut at the last sentence end before the
limit). Nothing is learnt; the text is tokenised with ENGRAMM's own tokenizer and indexed
like the rest of the corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

import numpy as np

from engramm.lm.stream import EOS, TokenSplit
from engramm.lm.tokenizer import LMTokenizer
from experiments.chat_v2_common import MODEL_DIR

URL = "https://huggingface.co/datasets/wikimedia/wikipedia/resolve/main/20231101.en/train-{i:05d}-of-00041.parquet"
N_SHARDS = 41
MIN_CHARS = 7_000
LEAD_CHARS = 2_000
WIKI_DIR = MODEL_DIR.parent / "wiki"
INDEX_DIR = MODEL_DIR.parent / "chat3"
TMP = MODEL_DIR.parent.parent.parent.parent / "data" / "cache" / "wiki"


def lead(text: str) -> str:
    t = text[:LEAD_CHARS]
    if len(text) > LEAD_CHARS:
        cut = max(t.rfind(". "), t.rfind(".\n"))
        if cut > LEAD_CHARS // 2:
            t = t[:cut + 1]
    return t.strip()


def extract() -> None:
    import pyarrow.parquet as pq
    tok = LMTokenizer()
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    state_path = WIKI_DIR / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"done": [], "sha256": {}}
    t0 = time.time()
    for i in range(N_SHARDS):
        if i in state["done"]:
            continue
        path = TMP / f"s{i}.parquet"
        if not path.exists():
            urllib.request.urlretrieve(URL.format(i=i), path)
        state["sha256"][str(i)] = hashlib.sha256(path.read_bytes()).hexdigest()
        t = pq.read_table(path, columns=["title", "text"])
        titles, texts = t.column("title").to_pylist(), t.column("text").to_pylist()
        keep = [(ti, lead(tx)) for ti, tx in zip(titles, texts) if len(tx) >= MIN_CHARS]
        docs = [x for _, x in keep]
        parts, lens = [], []
        for b in range(0, len(docs), 2048):
            for ids in tok.encode_batch(docs[b:b + 2048]):
                ids = np.asarray(ids, dtype=np.uint16)
                ids = ids[ids != EOS]
                parts.append(ids)
                lens.append(len(ids))
        np.concatenate(parts).tofile(WIKI_DIR / f"part{i:02d}.u16")
        np.save(WIKI_DIR / f"part{i:02d}.lens.npy", np.asarray(lens, dtype=np.int64))
        with open(WIKI_DIR / f"part{i:02d}.keys.jsonl", "w", encoding="utf-8") as f:
            for (ti, x) in keep:
                f.write(json.dumps(["wikipedia", ti, len(x.encode("utf-8"))], ensure_ascii=False) + "\n")
        path.unlink()
        state["done"].append(i)
        state_path.write_text(json.dumps(state, indent=1))
        print(f"shard {i}: {len(keep):,} articles, {sum(lens):,} tokens ({time.time() - t0:.0f} s)", flush=True)


def index() -> None:
    from engramm.chat import index as v2
    from engramm.chat.question import CapStats
    train = TokenSplit.load(MODEL_DIR, "train", mmap=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    # corpus = train stream, then every Wikipedia lead as one more document
    out = INDEX_DIR / "corpus.u16"
    with open(out, "wb") as f:
        np.asarray(train.tokens, dtype=np.uint16).tofile(f)
        pos = len(train.tokens)
        starts, nbytes, keys = list(train.doc_starts), list(train.doc_bytes), [list(k) for k in train.doc_keys]
        # an article the corpus already has (WikiText title) is not read a second time in a newer version
        have = {k[1].strip().lower() for k in train.doc_keys if k[0] == "wiki"}
        skipped = 0
        for i in range(N_SHARDS):
            toks = np.fromfile(WIKI_DIR / f"part{i:02d}.u16", dtype=np.uint16)
            lens = np.load(WIKI_DIR / f"part{i:02d}.lens.npy")
            with open(WIKI_DIR / f"part{i:02d}.keys.jsonl", encoding="utf-8") as g:
                kk = [json.loads(line) for line in g]
            off = 0
            for L, k in zip(lens.tolist(), kk):
                if k[1].strip().lower() in have:
                    off += L
                    skipped += 1
                    continue
                starts.append(pos)
                nbytes.append(k[2])
                keys.append([k[0], k[1]])
                np.asarray(toks[off:off + L], dtype=np.uint16).tofile(f)
                np.array([EOS], dtype=np.uint16).tofile(f)
                pos += L + 1
                off += L
    np.save(INDEX_DIR / "corpus.starts.npy", np.asarray(starts, dtype=np.int64))
    np.save(INDEX_DIR / "corpus.bytes.npy", np.asarray(nbytes, dtype=np.int64))
    with open(INDEX_DIR / "corpus.keys.jsonl", "w", encoding="utf-8") as f:
        for k in keys:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    tokens = np.memmap(out, dtype=np.uint16, mode="r")
    print(f"corpus: {len(tokens):,} tokens, {len(starts):,} documents ({skipped:,} already read)", flush=True)
    t0 = time.time()
    ix, dptr, dpost, sent_doc = v2.build(tokens, np.asarray(starts, dtype=np.int64), LMTokenizer())
    info = {"version": 3, "wikipedia_skipped_known_titles": skipped, "sentences": ix.n, "terms": len(ix.terms), "postings": int(len(ix.post)),
            "documents": len(starts), "tokens": int(len(tokens)), "wikipedia_min_chars": MIN_CHARS,
            "wikipedia_lead_chars": LEAD_CHARS, "build_seconds": round(time.time() - t0, 1)}
    v2.save(INDEX_DIR, ix, dptr, dpost, sent_doc, info)
    # name statistics from the original corpus (unchanged), and the span models of chat2
    src = MODEL_DIR.parent / "chat2"
    for name in ("capstats.json", "spanstats.json", "spanperc_p2.json", "spanperc_nq.json"):
        if (src / name).exists():
            (INDEX_DIR / name).write_bytes((src / name).read_bytes())
    _ = CapStats
    print(json.dumps(info, indent=2), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("extract", "index"))
    args = ap.parse_args()
    extract() if args.cmd == "extract" else index()


if __name__ == "__main__":
    main()
