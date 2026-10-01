"""Build the wayfinder (engramm/web/wayfinder.py): titles → official websites, from the DBpedia
"homepages" dataset (foaf:homepage, CC BY-SA) — optionally limited to the titles of a fact bank.

    python experiments/wayfinder_build.py --out /dev/shm/engramm/wayfinder.sqlite [--kb PACK/kb.sqlite]
"""

from __future__ import annotations

import argparse
import bz2
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engramm.web.wayfinder import build_db  # noqa: E402

URL = "https://downloads.dbpedia.org/repo/dbpedia/generic/homepages/2022.12.01/homepages_lang=en.ttl.bz2"
UA = "ENGRAMM-research/0.1 (offline assistant knowledge build; github.com/erithy25/engramm)"
_LINE = re.compile(r"^<http://dbpedia\.org/resource/([^>]+)> <http://xmlns\.com/foaf/0\.1/homepage> <([^>]+)> \.")


def download(dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return dest


def pairs(src: Path, keep: dict[str, int] | None):
    seen = set()
    with bz2.open(src, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = _LINE.match(line)
            if not m:
                continue
            title = urllib.parse.unquote(m.group(1)).replace("_", " ")
            url = re.split(r"%7C|\|| ", m.group(2).strip(), flags=re.I)[0]
            if not url.startswith(("http://", "https://")) or len(url) > 300 or title in seen:
                continue
            if "web.archive.org" in url or url.lower().endswith((".pdf", ".doc", ".jpg", ".png")):
                continue
            if keep is not None and title not in keep:
                continue
            seen.add(title)
            yield title, url, -(keep or {}).get(title, 0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--work", type=Path, default=Path("/dev/shm/engramm/kb"))
    ap.add_argument("--kb", type=Path, help="only titles of this fact bank (by popularity)")
    a = ap.parse_args(argv)
    a.work.mkdir(parents=True, exist_ok=True)
    src = download(a.work / "homepages_lang=en.ttl.bz2")
    keep = None
    if a.kb:
        con = sqlite3.connect(f"file:{a.kb}?mode=ro", uri=True)
        keep = {t: p for t, p in con.execute("SELECT title, popularity FROM entity")}
    n = build_db(a.out, pairs(src, keep))
    print(f"wayfinder: {n} sites, {a.out.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
