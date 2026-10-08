"""Messart A for ENGRAMM Chat v3.2 with the lite knowledge pack: stored values per component.

(docs/PREREG_PARAMS.md §4.4.) Counts only — no "parameters". Groups: fact bank, index,
perceptrons, lexica and counted statistics, raw text (not counted, size given). Each file of
the pack is checked against the pack manifest first; the program data come from this
checkout (identical to tag v3.2.0-beta.6 for ``engramm/``).

    python -m experiments.params_count_chat [--pack data/cache/params/lite_pack]

Bytes in RAM: computed where the app holds numpy arrays (memory-mapped arrays are file-backed;
``CompactWeights`` = 8-byte key + 8-byte weight per feature). For structures the app keeps as
Python objects, the RSS increase of loading that one component in a fresh process is given —
a container value, never official (docs/PROTOCOL.md rule 2).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from engramm.repro import git_revision
from experiments.params_common import REPO, WORK, array_row, write_record

PACK = WORK / "lite_pack"
MANIFEST_SHA256 = "90687f5b5c1d3229b1bd1ee132f3940c8d5cbc5c833b1f5bbcddc47ab4a1fac3"
PROGRAM = {"frame_model": REPO / "engramm/understand/data/frame_model.json.gz",
           "lex_en": REPO / "engramm/understand/data/lex_en.tsv.gz",
           "lex_de": REPO / "engramm/understand/data/lex_de.tsv.gz",
           "forms_en": REPO / "engramm/understand/data/forms_en.tsv.gz",
           "forms_de": REPO / "engramm/understand/data/forms_de.tsv.gz",
           "letters": REPO / "engramm/chat/letters.json",
           "atlas_calib": REPO / "engramm/web/atlas_calib.json",
           "howto": REPO / "engramm/know/data/howto.json.gz",
           "wikibooks": REPO / "engramm/know/data/wikibooks.json.gz",
           "conv_bank": REPO / "engramm/chat/conv_bank.json",
           "verbs": REPO / "engramm/chat/data/verbs.txt"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()


def verify_pack(pack: Path) -> dict:
    if sha256(pack / "manifest.json") != MANIFEST_SHA256:
        raise SystemExit("manifest.json is not the registered lite pack")
    m = json.loads((pack / "manifest.json").read_text())
    files = m["files"] if isinstance(m["files"], list) else [{"path": k, **v} for k, v in m["files"].items()]
    for f in files:
        p = pack / f["path"]
        if p.stat().st_size != f["bytes"] or sha256(p) != f["sha256"]:
            raise SystemExit(f"{f['path']} does not match the manifest")
    return {"version": m["version"], "bytes": m["bytes"], "files": len(files), "manifest_sha256": MANIFEST_SHA256}


def rss_delta(snippet: str) -> int | None:
    """RSS increase (bytes) of running ``snippet`` in a fresh interpreter (container only)."""
    code = ("import os,sys\nsys.path.insert(0, %r)\n"
            "def rss():\n    return int([l for l in open('/proc/self/status') if l.startswith('VmRSS')][0].split()[1])*1024\n"
            "a=rss()\n%s\nprint(rss()-a)\n") % (str(REPO), snippet)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=REPO)
    return int(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else None


def json_load(path: Path):
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------

def fact_bank(pack: Path) -> dict:
    db = sqlite3.connect(f"file:{pack / 'kb.sqlite'}?mode=ro", uri=True)
    tables = {}
    for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        cols = [r[1] for r in db.execute(f"PRAGMA table_info('{name}')")]
        rows = db.execute(f"SELECT COUNT(*) FROM '{name}'").fetchone()[0]
        tables[name] = {"rows": rows, "columns": cols, "cells": rows * len(cols)}
    indexes = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")]
    db.close()
    learned = tables.get("entity", {}).get("rows", 0)            # entity.popularity: counted
    return {"tables": tables, "indexes": indexes, "values": sum(t["cells"] for t in tables.values()),
            "values_learned": learned, "note_learned": "only entity.popularity is counted; facts are verbatim",
            "disk_bytes": (pack / "kb.sqlite").stat().st_size,
            "ram_bytes_rss_delta_container": rss_delta(
                f"import sqlite3\ndb=sqlite3.connect('file:{pack / 'kb.sqlite'}?mode=ro', uri=True)\n"
                "for t in ('entity','alias','fact'):\n    db.execute(f'SELECT * FROM {t}').fetchall()")}


def index(pack: Path) -> dict:
    sent = {}
    for name in ("starts", "lens", "ptr", "post", "sent_terms", "term_of", "doc_ptr", "doc_post", "sent_doc"):
        a = np.load(pack / f"{name}.npy", mmap_mode="r")
        sent[name] = array_row(a, (pack / f"{name}.npy").stat().st_size)
    terms = (pack / "terms.txt").read_text(encoding="utf-8").split("\n")[:-1]
    sent["terms"] = {"values": len(terms), "disk_bytes": (pack / "terms.txt").stat().st_size, "note": "strings"}
    shelf = {}
    for f in sorted((pack / "shelf_index").glob("*.npy")):
        shelf[f.stem] = array_row(np.load(f, mmap_mode="r"), f.stat().st_size)
    groups = {"sentence_index": sent, "shelf_index": shelf}
    return {"groups": groups,
            "values": sum(r["values"] for g in groups.values() for r in g.values()),
            "values_learned": shelf["idf"]["values"] if "idf" in shelf else 0,
            "note_learned": "only the shelf idf (float16) is counted; the sentence-index idf is derived at load",
            "disk_bytes": sum(r["disk_bytes"] for g in groups.values() for r in g.values()),
            "ram_bytes": sum(r.get("ram_bytes", 0) for g in groups.values() for r in g.values()),
            "ram_note": "memory-mapped: file-backed address space, resident only when touched"}


def _nested_weights(d: dict) -> tuple[int, int]:
    """(features, (feature, class) weights) of an AveragedPerceptron dict."""
    w = d["weights"]
    return len(w), sum(len(v) for v in w.values())


def perceptrons(pack: Path) -> dict:
    out = {}
    for name in ("spanperc_ens7", "spanperc_nq"):
        d = json_load(pack / f"{name}.json")
        n = len(d["w"])
        out[name] = {"weights": n, "feature_keys": n, "values": n, "disk_bytes": (pack / f"{name}.json").stat().st_size,
                     "ram_bytes": 16 * n, "ram_note": "CompactWeights: uint64 key hash + float64 weight",
                     "bits_per_value_ram": 64, "disk_format": "JSON text, 6 decimals"}
    d = json_load(pack / "confperc14.json")
    out["confperc14"] = {"weights": len(d["w"]), "bins": len(d.get("r0_bins", [])),
                         "values": len(d["w"]) + len(d.get("r0_bins", [])),
                         "disk_bytes": (pack / "confperc14.json").stat().st_size}
    for name, path in (("intent", pack / "nlp" / "intent.json"), ("frame_model", PROGRAM["frame_model"])):
        d = json_load(path)
        feats, n = _nested_weights(d)
        out[name] = {"classes": len(d["classes"]), "features": feats, "weights": n, "values": n,
                     "disk_bytes": path.stat().st_size}
    d = json_load(PROGRAM["atlas_calib"])
    out["atlas_calib"] = {"weights": len(d["w"]), "values": len(d["w"]) + 1 + len(d.get("r0_bins") or []),
                          "disk_bytes": PROGRAM["atlas_calib"].stat().st_size}
    for name, path in (("intent", pack / "nlp" / "intent.json"), ("frame_model", PROGRAM["frame_model"])):
        opener = "gzip.open(p,'rt',encoding='utf-8')" if path.suffix == ".gz" else "open(p,encoding='utf-8')"
        out[name]["ram_bytes_rss_delta_container"] = rss_delta(
            f"import json,gzip\np={str(path)!r}\nd=json.load({opener})")
    return {"models": out, "values": sum(m["values"] for m in out.values()),
            "disk_bytes": sum(m["disk_bytes"] for m in out.values())}


def lexica(pack: Path) -> dict:
    out = {}
    d = json_load(pack / "spell.json")
    out["spell"] = {"words": len(d["words"]), "values": len(d["counts"]) + len(d["capital"]),
                    "note": "per word a count and a capital-letter percentage (counted)",
                    "disk_bytes": (pack / "spell.json").stat().st_size}
    d = json_load(pack / "capstats.json")
    out["capstats"] = {"values": len(d), "disk_bytes": (pack / "capstats.json").stat().st_size}
    d = json_load(PROGRAM["letters"])
    out["letters"] = {"trigram_logp": len(d["trigram_logp"]), "unseen_bigram_logp": len(d["unseen_logp"]),
                      "words": len(d["words"]), "values": len(d["trigram_logp"]) + len(d["unseen_logp"]) + 1,
                      "disk_bytes": PROGRAM["letters"].stat().st_size}
    for name in ("lex_en", "lex_de", "forms_en", "forms_de"):
        with gzip.open(PROGRAM[name], "rt", encoding="utf-8") as f:
            lines = [l.rstrip("\n").split("\t") for l in f]
        out[name] = {"entries": len(lines), "values": sum(len(x) for x in lines),
                     "note": "extracted from WordNet/FrameNet/OdeNet/Wiktionary, not trained",
                     "disk_bytes": PROGRAM[name].stat().st_size}
    tk = json_load(pack / "tokenizer.json")
    merges = tk["model"]["merges"]
    out["tokenizer"] = {"vocab": len(tk["model"]["vocab"]), "merges": len(merges), "values": len(merges),
                        "note": "byte-level BPE learned by pair counting", "disk_bytes": (pack / "tokenizer.json").stat().st_size}
    z = np.load(pack / "codebook.npz")
    cb = {k: array_row(z[k], bit_vector=k in ("eng", "wide")) for k in z.files}
    out["codebook"] = {"arrays": cb, "values": sum(r["values"] for r in cb.values()),
                       "used_by_chat": ["eng", "wide", "classes"], "disk_bytes": (pack / "codebook.npz").stat().st_size,
                       "ram_bytes": sum(r["ram_bytes"] for r in cb.values())}
    out["spell"]["ram_bytes_rss_delta_container"] = rss_delta(
        f"from engramm.nlp.spell import Speller\ns=Speller.load({str(pack / 'spell.json')!r})")
    out["lexicon_en_de"] = {"ram_bytes_rss_delta_container": rss_delta(
        "from engramm.understand.lex import Lexicon\na=Lexicon('en'); b=Lexicon('de')")}
    return {"items": out, "values": sum(v.get("values", 0) for v in out.values()),
            "disk_bytes": sum(v.get("disk_bytes", 0) for v in out.values())}


def raw_text(pack: Path) -> dict:
    out = {"corpus_tokens": array_row(np.fromfile(pack / "corpus.u16", dtype=np.uint16),
                                      (pack / "corpus.u16").stat().st_size),
           "corpus_starts": array_row(np.load(pack / "corpus.starts.npy", mmap_mode="r"),
                                      (pack / "corpus.starts.npy").stat().st_size)}
    for name in ("corpus.keys.jsonl", "shelf_index/titles.bin", "wayfinder.sqlite", "shelf.json", "shelf_source.json",
                 "info.json", "shelf_index/info.json"):
        out[name] = {"disk_bytes": (pack / name).stat().st_size}
    for name in ("howto", "wikibooks", "conv_bank", "verbs"):
        out[name] = {"disk_bytes": PROGRAM[name].stat().st_size}
    return {"items": out, "disk_bytes": sum(v["disk_bytes"] for v in out.values()),
            "note": "verbatim text and its bookkeeping: not counted as learned values"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", type=Path, default=PACK)
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    pack = verify_pack(args.pack)
    out = {"subject": {"release": "v3.2.0-beta.6", "pack": "lite", **pack},
           "fact_bank": fact_bank(args.pack), "index": index(args.pack), "perceptrons": perceptrons(args.pack),
           "lexica_and_statistics": lexica(args.pack), "raw_text": raw_text(args.pack)}
    out["summary"] = {k: {"values": out[k].get("values"), "disk_bytes": out[k]["disk_bytes"]}
                      for k in ("fact_bank", "index", "perceptrons", "lexica_and_statistics", "raw_text")}
    out["summary"]["wording"] = "stored values, not parameters (docs/PREREG_PARAMS.md §1)"
    print(json.dumps(out["summary"], indent=1), flush=True)
    print(write_record("a_chat_v32_lite", out, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
