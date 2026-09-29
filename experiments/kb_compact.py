"""Compact the fact bank for shipping: fewer, more-asked-about entities and properties.

    python -u -m experiments.kb_compact --src /dev/shm/engramm/kb/kb.sqlite --out models/lm/main/kb.sqlite

* entities with popularity ≥ ``--min-popularity`` (other facts point to them, or they have
  redirects) — the ones people ask about;
* properties people rarely ask about are dropped (``DROP``: sports teams and positions, time
  zones, record labels, associated acts, predecessors …);
* redirects are kept for names of at most six words that differ from the title by more than
  case and punctuation;
* entity-valued facts store the target id instead of repeating its title when the target is
  kept (the title comes back through a join);
* no reverse index (facts are only looked up by their subject).

Prints sizes and counts and writes them into the database's meta table.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from pathlib import Path

DROP = frozenset("""team position timeZone associatedBand associatedMusicalArtist recordLabel predecessor successor
weight birthName award distributor mass wingspan formerBandMember""".split())


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("/dev/shm/engramm/kb/kb.sqlite"))
    ap.add_argument("--out", type=Path, default=Path("models/lm/main/kb.sqlite"))
    ap.add_argument("--min-popularity", type=int, default=4)
    args = ap.parse_args()
    t0 = time.time()
    src = sqlite3.connect(f"file:{args.src}?mode=ro", uri=True)
    if args.out.exists():
        args.out.unlink()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    dst = sqlite3.connect(args.out)
    dst.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; PRAGMA page_size=4096;
        CREATE TABLE entity(id INTEGER PRIMARY KEY, title TEXT NOT NULL, type TEXT, popularity INTEGER NOT NULL);
        CREATE TABLE alias(name TEXT NOT NULL, entity INTEGER NOT NULL, kind INTEGER NOT NULL);
        CREATE TABLE fact(entity INTEGER NOT NULL, prop TEXT NOT NULL, value TEXT NOT NULL, dtype TEXT NOT NULL,
                          value_entity INTEGER);
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    keep = {}
    for i, t, ty, pop in src.execute("SELECT id, title, type, popularity FROM entity WHERE popularity >= ? "
                                     "ORDER BY id", (args.min_popularity,)):
        keep[i] = t
    rows = src.execute("SELECT id, title, type, popularity FROM entity WHERE popularity >= ?", (args.min_popularity,))
    dst.executemany("INSERT INTO entity VALUES (?,?,?,?)", rows)
    print(f"entities {len(keep):,} ({time.time() - t0:.0f} s)", flush=True)

    def aliases():
        for name, e, kind in src.execute("SELECT name, entity, kind FROM alias"):
            t = keep.get(e)
            if t is None:
                continue
            if kind == 2 and (len(name.split()) > 6 or _norm(name) == _norm(t)):
                continue
            yield name, e, kind
    dst.executemany("INSERT INTO alias VALUES (?,?,?)", aliases())
    n_alias = dst.execute("SELECT COUNT(*) FROM alias").fetchone()[0]
    print(f"aliases {n_alias:,} ({time.time() - t0:.0f} s)", flush=True)

    def facts():
        for e, p, v, dt, ve in src.execute("SELECT entity, prop, value, dtype, value_entity FROM fact ORDER BY rowid"):
            if e not in keep or p in DROP:
                continue
            if ve is not None and ve in keep:
                yield e, p, "", dt, ve
            else:
                yield e, p, v, dt, None
    dst.executemany("INSERT INTO fact VALUES (?,?,?,?,?)", facts())
    n_fact = dst.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
    print(f"facts {n_fact:,} ({time.time() - t0:.0f} s)", flush=True)
    dst.executescript("""
        CREATE INDEX alias_name ON alias(name);
        CREATE INDEX fact_entity ON fact(entity, prop);
        CREATE UNIQUE INDEX entity_title ON entity(title);
    """)
    meta = {k: json.loads(v) for k, v in src.execute("SELECT key, value FROM meta")}
    meta.update({"entities": len(keep), "aliases": n_alias, "facts": n_fact, "min_popularity": args.min_popularity,
                 "dropped_props": sorted(DROP), "compact": True})
    dst.executemany("INSERT INTO meta VALUES (?,?)", [(k, json.dumps(v)) for k, v in meta.items()])
    dst.commit()
    dst.execute("VACUUM")
    dst.close()
    size = args.out.stat().st_size
    print(json.dumps({"entities": len(keep), "aliases": n_alias, "facts": n_fact, "MB": round(size / 1e6, 1),
                      "seconds": round(time.time() - t0)}), flush=True)


if __name__ == "__main__":
    main()
