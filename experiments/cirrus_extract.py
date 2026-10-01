"""Extract English Wikipedia articles (plain text) from the weekly CirrusSearch index dump
(https://dumps.wikimedia.org/other/cirrus_search_index/<date>/index_name=enwiki_content/,
CC BY-SA 4.0) into JSON lines for experiments/shelf_build.py.

Each shard (~630 MB bz2) is streamed and decompressed on the fly, in parallel; only articles
("page_type": "primary", namespace 0, not disambiguation pages) with at least ``--min-chars`` of
text (without the trailing reference list, engramm/web/clean.py) are kept, as {"t": title, "s": "wiki", "x": text, "d": last edit (YYYY-MM-DD), "r": up to 8
redirect titles}.

    python experiments/cirrus_extract.py --date 20260927 --out /mnt/cirrus --workers 4
    python experiments/cirrus_extract.py --file shard.json.bz2 --out /tmp/x      # a local file
"""

from __future__ import annotations

import argparse
import bz2
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engramm.web.clean import strip_references  # noqa: E402

BASE = "https://dumps.wikimedia.org/other/cirrus_search_index/{date}/index_name%3Denwiki_content/"
UA = "ENGRAMM-research/0.1 (offline assistant knowledge build; github.com/erithy25/engramm)"


def shard_names(date: str) -> list[str]:
    req = urllib.request.Request(BASE.format(date=date), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        page = r.read().decode("utf-8", "replace")
    return sorted(set(re.findall(r'href="(enwiki_content-[0-9]+-[0-9]+\.json\.bz2)"', page)))


def latest_date() -> str:
    req = urllib.request.Request("https://dumps.wikimedia.org/other/cirrus_search_index/", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        page = r.read().decode("utf-8", "replace")
    return sorted(re.findall(r'href="(20[0-9]{6})/"', page))[-1]


def _records(stream, out_path: Path, min_chars: int) -> tuple[int, int]:
    kept = seen = 0
    with open(out_path, "w", encoding="utf-8") as out:
        try:
            for line in stream:
                if not line.startswith(b'{"page_id"'):
                    continue
                seen += 1
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if o.get("page_type") != "primary" or o.get("namespace") != 0:
                    continue
                text = strip_references(o.get("text") or "")
                if len(text) < min_chars:
                    continue
                cats = o.get("category") or []
                if any("disambiguation pages" in c.lower() for c in cats):
                    continue
                rec = {"t": o["title"], "s": "wiki", "x": text, "d": (o.get("timestamp") or "")[:10],
                       "r": [r.get("title") for r in (o.get("redirect") or [])[:8] if r.get("title")]}
                out.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
                kept += 1
        except (EOFError, OSError):         # a cut-off file (tests): keep what was read
            pass
    return kept, seen


def extract_url(args) -> tuple[str, int, int]:
    url, out_path, min_chars = args
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                kept, seen = _records(bz2.BZ2File(r), Path(out_path), min_chars)
            return url, kept, seen
        except Exception as e:                # retry the whole shard: the output file is rewritten
            if attempt == 3:
                raise
            print(f"[cirrus] retry {url}: {e}", flush=True)
            time.sleep(10 * (attempt + 1))
    return url, 0, 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="dump date (YYYYMMDD); default: the latest")
    ap.add_argument("--file", type=Path, action="append", default=[], help="local shard(s) instead of downloading")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--shards", type=int, help="only the first N shards")
    ap.add_argument("--min-chars", type=int, default=300)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if a.file:
        total = 0
        for i, f in enumerate(a.file):
            with bz2.open(f, "rb") as s:
                kept, seen = _records(s, a.out / f"docs-{i:05d}.jsonl", a.min_chars)
            print(f"[cirrus] {f}: {kept} of {seen} pages kept", flush=True)
            total += kept
        return 0
    date = a.date or latest_date()
    names = shard_names(date)[: a.shards or None]
    base = BASE.format(date=date)
    jobs = [(base + n, str(a.out / f"docs-{i:05d}.jsonl"), a.min_chars) for i, n in enumerate(names)]
    print(f"[cirrus] {date}: {len(jobs)} shards", flush=True)
    kept = 0
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for url, k, s in ex.map(extract_url, jobs):
            kept += k
            print(f"[cirrus] {url.rsplit('/', 1)[-1]}: {k} of {s} pages kept ({time.time() - t0:.0f}s)", flush=True)
    (a.out / "cirrus.json").write_text(json.dumps({"date": date, "shards": len(jobs), "articles": kept}), encoding="utf-8")
    print(f"[cirrus] done: {kept} articles in {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
