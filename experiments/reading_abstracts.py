"""The reading for knowledge packs (Chat v3, phase 3): the lead section of the Wikipedia articles
people ask about most, from DBpedia 2022.12 long abstracts (CC BY-SA 3.0, text of Wikipedia).

    python -u -m experiments.reading_abstracts --kb /dev/shm/engramm/kb/kb.sqlite --top 1000000 \
        --out /dev/shm/engramm/reading/abstracts.jsonl

* ranks articles by the fact bank's popularity (how often other facts point to an entity, plus its
  redirects) and keeps the ``--top`` most popular that have an abstract;
* streams the 0.9 GB file (kept in --work, so a rerun does not download again), unescapes the
  N-Triples literals and drops abstracts shorter than 40 characters or without a sentence end;
* writes one JSON line per article: {"title", "text", "rank"} in popularity order, so a smaller
  pack can take a prefix.
"""

from __future__ import annotations

import argparse
import bz2
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path

URL = ("https://downloads.dbpedia.org/repo/dbpedia/text/long-abstracts/2022.12.01/"
       "long-abstracts_lang=en.ttl.bz2")
UA = "ENGRAMM-research/0.1 (offline assistant knowledge build; github.com/erithy25/engramm)"
LINE = re.compile(r'^<http://dbpedia\.org/resource/([^>]+)> <http://dbpedia\.org/ontology/abstract> "(.*)"@en \.$')
_ESC = re.compile(r'\\(u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|[tbnrf"\'\\])')
_SIMPLE = {"t": "\t", "b": "\b", "n": "\n", "r": "\r", "f": "\f", '"': '"', "'": "'", "\\": "\\"}


def unescape(s: str) -> str:
    def rep(m: re.Match) -> str:
        e = m.group(1)
        if e[0] in "uU":
            try:
                return chr(int(e[1:], 16))
            except ValueError:
                return ""
        return _SIMPLE[e]
    return _ESC.sub(rep, s)


def title_of(resource: str) -> str:
    return urllib.parse.unquote(resource).replace("_", " ")


def download(work: Path) -> Path:
    path = work / "long-abstracts_lang=en.ttl.bz2"
    if path.exists() and path.stat().st_size > 800_000_000:
        return path
    part = path.with_suffix(".part")
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r, open(part, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 22)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if done % (100 << 20) < (1 << 22):
                print(f"download {done / 1e6:,.0f} / {total / 1e6:,.0f} MB ({time.time() - t0:.0f} s)", flush=True)
    part.replace(path)
    return path


def clean(text: str) -> str:
    text = re.sub(r"\s*\(\s*[;,]?\s*\)", "", text)            # "( ; )" left by removed pronunciations
    text = re.sub(r"\(\s*[;,]\s*", "(", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", type=Path, default=Path("/dev/shm/engramm/kb/kb.sqlite"))
    ap.add_argument("--top", type=int, default=1_000_000)
    ap.add_argument("--max-chars", type=int, default=1500)
    ap.add_argument("--work", type=Path, default=Path("/dev/shm/engramm/reading"))
    ap.add_argument("--out", type=Path, default=Path("/dev/shm/engramm/reading/abstracts.jsonl"))
    args = ap.parse_args()
    t0 = time.time()
    args.work.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{args.kb}?mode=ro", uri=True)
    rank = {}
    for i, (title,) in enumerate(con.execute("SELECT title FROM entity ORDER BY popularity DESC, id")):
        rank.setdefault(title, i)
    con.close()
    print(f"{len(rank):,} ranked titles ({time.time() - t0:.0f} s)", flush=True)
    src = download(args.work)
    kept = []
    n = 0
    with bz2.open(src, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            n += 1
            m = LINE.match(line.rstrip("\n"))
            if not m:
                continue
            title = title_of(m.group(1))
            r = rank.get(title)
            if r is None:
                continue
            text = clean(unescape(m.group(2)))
            if len(text) < 40 or not re.search(r"[.!?]", text):
                continue
            if len(text) > args.max_chars:
                cut = text.rfind(". ", 0, args.max_chars)
                text = text[:cut + 1] if cut > 200 else text[:args.max_chars]
            kept.append((r, title, text))
            if n % 1_000_000 == 0:
                print(f"{n:,} lines, {len(kept):,} kept ({time.time() - t0:.0f} s)", flush=True)
    kept.sort()
    kept = kept[:args.top]
    tmp = args.out.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r, title, text in kept:
            f.write(json.dumps({"title": title, "text": text, "rank": r}, ensure_ascii=False) + "\n")
    tmp.replace(args.out)
    chars = sum(len(t) for _, _, t in kept)
    print(json.dumps({"articles": len(kept), "chars": chars, "MB": round(args.out.stat().st_size / 1e6, 1),
                      "seconds": round(time.time() - t0)}), flush=True)


if __name__ == "__main__":
    main()
