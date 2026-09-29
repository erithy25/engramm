"""Build a knowledge pack for the desktop app (Chat v3, phase 3): everything ENGRAMM needs to
chat, in one folder, with a manifest of SHA-256 checksums.

    python -u -m experiments.pack_build --name lite --sentences 5 --out /dev/shm/engramm/packs/lite
    python -u -m experiments.pack_build --name standard --sentences 14 --with-wiki --out …

Contents:
* the reading: Wikipedia articles from the chat3 corpus (``--sentences`` first sentences of
  each; ``--with-wiki`` adds the full articles of the training stream), re-indexed with the
  sentence and document index of engramm/chat/index.py (memory-mapped at run time);
* the counted models: codebook (meaning vectors, word classes), span perceptrons, the
  confidence calibrator, capitalisation statistics, the tokenizer;
* the fact bank (kb.sqlite) and the NLP models, when present;
* ``manifest.json``: pack name and version, file sizes and SHA-256, licences, build time.

The pack is a plain folder; ``engramm.app --pack DIR`` runs on it without the language model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "models" / "lm" / "main"
MODEL_FILES = ("spanperc_ens7.json", "spanperc_nq.json", "spanperc_p2.json", "confperc14.json", "capstats.json")
LICENSES = {
    "reading": "Wikipedia text, CC BY-SA 4.0 (https://en.wikipedia.org)",
    "facts": "DBpedia 2022.12 (CC BY-SA 3.0 / GFDL) and Wikidata (CC0)",
    "nlp": "trained on UD English EWT (CC BY-SA 4.0) and MASSIVE (CC BY 4.0)",
    "authored": "ENGRAMM conversation bank and models, project licence",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def select_stream(src: Path, sentences: int, with_wiki: bool) -> tuple[np.ndarray, np.ndarray, list]:
    """The token stream of the chosen documents, each cut after its first ``sentences`` sentences
    (by the chat3 sentence index), ending with a document end (token 0)."""
    from engramm.lm.chat import SentenceIndex
    keys = [json.loads(line) for line in (src / "corpus.keys.jsonl").read_text(encoding="utf-8").splitlines()]
    starts = np.load(src / "corpus.starts.npy")
    tokens = np.memmap(src / "corpus.u16", dtype=np.uint16, mode="r")
    ix = SentenceIndex.load(src, mmap=True)
    sent_doc = np.load(src / "sent_doc.npy", mmap_mode="r")
    doc_first = np.searchsorted(np.asarray(sent_doc), np.arange(len(keys)), side="left")
    ends = np.append(starts[1:], len(tokens))
    parts, new_starts, new_keys, pos = [], [], [], 0
    sstarts, slens = np.asarray(ix.starts), np.asarray(ix.lens)
    for d, (source, key) in enumerate(keys):
        if source == "wikipedia" or (with_wiki and source == "wiki"):
            lo = int(starts[d])
            hi = int(ends[d])
            s_idx = int(doc_first[d]) + sentences - 1
            if s_idx < len(sstarts) and int(sent_doc[s_idx]) == d:
                hi = min(hi, int(sstarts[s_idx] + slens[s_idx]))
            piece = np.asarray(tokens[lo:hi])
            piece = piece[piece != 0]
            if len(piece) < 3:
                continue
            parts.append(piece)
            parts.append(np.zeros(1, dtype=np.uint16))
            new_starts.append(pos)
            new_keys.append((source, key))
            pos += len(piece) + 1
    return np.concatenate(parts), np.asarray(new_starts, dtype=np.int64), new_keys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="lite")
    ap.add_argument("--version", default="3.0.0")
    ap.add_argument("--sentences", type=int, default=5)
    ap.add_argument("--with-wiki", action="store_true")
    ap.add_argument("--src", type=Path, default=MAIN / "chat3")
    ap.add_argument("--models", type=Path, default=MAIN / "chat4")
    ap.add_argument("--kb", type=Path, default=MAIN / "kb.sqlite")
    ap.add_argument("--nlp", type=Path, default=ROOT / "models" / "nlp")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    t0 = time.time()
    from engramm.chat import index as v2index
    from engramm.lm.tokenizer import LMTokenizer
    out = args.out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    tokens, starts, keys = select_stream(args.src, args.sentences, args.with_wiki)
    print(f"stream: {len(keys):,} documents, {len(tokens):,} tokens ({time.time() - t0:.0f} s)", flush=True)
    tokens.tofile(out / "corpus.u16")
    np.save(out / "corpus.starts.npy", starts)
    (out / "corpus.keys.jsonl").write_text("".join(json.dumps(list(k)) + "\n" for k in keys), encoding="utf-8")
    tok = LMTokenizer()
    ix, dptr, dpost, sent_doc = v2index.build(tokens, starts, tok)
    info = {"pack": args.name, "version": args.version, "sentences": int(ix.n), "documents": len(keys),
            "tokens": int(len(tokens)), "config": "chat4", "first_sentences": args.sentences,
            "with_wiki": args.with_wiki}
    v2index.save(out, ix, dptr, dpost, sent_doc, info)
    del ix, dptr, dpost, sent_doc
    print(f"index built ({time.time() - t0:.0f} s)", flush=True)
    for name in MODEL_FILES:
        if (args.models / name).exists():
            shutil.copy2(args.models / name, out / name)
    shutil.copy2(MAIN / "model" / "codebook.npz", out / "codebook.npz")
    shutil.copy2(ROOT / "data" / "lm_tokenizer.json", out / "tokenizer.json")
    if args.kb.exists():
        shutil.copy2(args.kb, out / "kb.sqlite")
    if args.nlp.exists():
        (out / "nlp").mkdir()
        for p in args.nlp.glob("*.json"):
            shutil.copy2(p, out / "nlp" / p.name)
    files = {}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            files[str(p.relative_to(out))] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    manifest = {"pack": args.name, "version": args.version, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "bytes": sum(f["bytes"] for f in files.values()), "files": files, "licenses": LICENSES,
                "info": info}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"pack": args.name, "MB": round(manifest["bytes"] / 1e6, 1), "documents": len(keys),
                      "sentences": info["sentences"], "seconds": round(time.time() - t0)}), flush=True)


if __name__ == "__main__":
    main()
