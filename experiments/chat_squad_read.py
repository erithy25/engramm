"""ENGRAMM-Chat v12: read the SQuAD paragraphs that ENGRAMM has not read yet (index segment ``chat4``).

    python -m experiments.chat_squad_read select   # → data/cache/chat/squad_read.json
    python -m experiments.chat_squad_read index    # → models/lm/main/chat4 (= chat3 + segment)

Why: since stage 1, a SQuAD question may be asked only if ENGRAMM has read its paragraph (13-token
windows, step 13, found verbatim for at least 80 % of the paragraph: the pool). After v11 no unseen
question of the test articles is left in the pool. v12 therefore lets ENGRAMM read the Wikipedia
paragraphs (2016) that SQuAD v1.1 consists of, as far as they are not read yet.

Rule (depends only on the paragraph text, never on a question or an answer):

* every distinct paragraph of SQuAD v1.1 train + dev, in file order;
* its 13-token windows (step 13) are looked up in the whole chat3 stream (64-bit rolling hash of the
  token ids, windows crossing a document end skipped);
* a paragraph whose windows are found less than 80 % of the time counts as not read and is read now;
* the paragraphs read of one article form one document (in their SQuAD order, one per line), with
  the key ``("wikipedia", <title>)``.

The segment is indexed on its own and appended to chat3 when loaded (``Corpus.with_segment``); the
result equals an index built over the concatenated stream.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import OrderedDict

import numpy as np

from engramm.lm.tokenizer import EOS, LMTokenizer
from experiments.chat_eval import COVER, WINDOW, load_squad
from experiments.chat_pool_v2 import _mark_found, _window_hashes
from experiments.chat_v2_common import MODEL_DIR
from experiments.chat_v2_data import CACHE

BASE = "chat3"
OUT = MODEL_DIR.parent / "chat4"
SELECTION = CACHE / "squad_read.json"


def paragraphs() -> list[tuple[str, str]]:
    """Distinct (title, paragraph) of SQuAD v1.1 train + dev in file order."""
    seen, out = set(), []
    for q in load_squad():
        if q["context"] not in seen:
            seen.add(q["context"])
            out.append((q["title"], q["context"]))
    return out


def select() -> None:
    t0 = time.time()
    tok = LMTokenizer()
    paras = paragraphs()
    corpus = np.memmap(MODEL_DIR.parent / BASE / "corpus.u16", dtype=np.uint16, mode="r")
    wins = []
    for _, ctx in paras:
        ids = np.asarray(tok.encode(ctx), dtype=np.uint16)
        hs = []
        for w in range(len(ids) // WINDOW):
            hh = _window_hashes(np.ascontiguousarray(ids[w * WINDOW:(w + 1) * WINDOW]), WINDOW)
            hs.append(int(hh[0]) if len(hh) else 0)
        wins.append(hs)
    targets = np.unique(np.array([h for v in wins for h in v if h], dtype=np.uint64))
    found = np.zeros(len(targets), dtype=np.bool_)
    _mark_found(np.asarray(corpus), WINDOW, targets, found)
    got = set(targets[found].tolist())
    cov = [(sum(1 for h in v if h in got) / len(v)) if v else 0.0 for v in wins]
    read = [i for i, c in enumerate(cov) if c < COVER]
    digest = hashlib.sha256("\n\x1e\n".join(paras[i][1] for i in read).encode("utf-8")).hexdigest()
    SELECTION.write_text(json.dumps({
        "rule": f"SQuAD v1.1 paragraphs with 13-gram coverage < {COVER} in {BASE}",
        "paragraphs": len(paras), "read": len(read), "read_sha256": digest,
        "read_index": read, "coverage": [round(c, 4) for c in cov]}) + "\n")
    print(f"{len(paras):,} paragraphs, {len(read):,} not read yet ({time.time() - t0:.0f} s); sha256 {digest}",
          flush=True)


def index() -> None:
    from engramm.chat import index as v2
    t0 = time.time()
    tok = LMTokenizer()
    paras = paragraphs()
    sel = json.loads(SELECTION.read_text())
    docs: OrderedDict[str, list[str]] = OrderedDict()
    for i in sel["read_index"]:
        title, ctx = paras[i]
        docs.setdefault(title, []).append(ctx.strip())
    OUT.mkdir(parents=True, exist_ok=True)
    parts, starts, keys, pos = [], [], [], 0
    for title, ps in docs.items():
        ids = np.asarray(tok.encode("\n".join(ps)), dtype=np.uint16)
        ids = ids[ids != EOS]
        starts.append(pos)
        keys.append(["wikipedia", title.replace("_", " ")])
        parts.append(ids)
        parts.append(np.array([EOS], dtype=np.uint16))
        pos += len(ids) + 1
    tokens = np.concatenate(parts)
    tokens.tofile(OUT / "segment.u16")
    np.save(OUT / "segment.starts.npy", np.asarray(starts, dtype=np.int64))
    with open(OUT / "segment.keys.jsonl", "w", encoding="utf-8") as f:
        for k in keys:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    ix, dptr, dpost, sent_doc = v2.build(tokens, np.asarray(starts, dtype=np.int64), tok)
    info = {"version": 4, "base": BASE, "segment": "SQuAD v1.1 paragraphs not read yet (2016 Wikipedia)",
            "paragraphs": sel["read"], "paragraphs_sha256": sel["read_sha256"], "documents": len(starts),
            "tokens": int(len(tokens)), "sentences": ix.n, "build_seconds": round(time.time() - t0, 1)}
    v2.save(OUT, ix, dptr, dpost, sent_doc, info)
    (OUT / "segment.json").write_text(json.dumps({"base": BASE}) + "\n")
    # name statistics and span models: the same files as the base
    src = MODEL_DIR.parent / BASE
    for name in ("capstats.json", "spanstats.json", "spanperc_p2.json", "spanperc_nq.json"):
        if (src / name).exists():
            (OUT / name).write_bytes((src / name).read_bytes())
    print(json.dumps(info, indent=2), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("select", "index"))
    args = ap.parse_args()
    select() if args.cmd == "select" else index()


if __name__ == "__main__":
    main()
