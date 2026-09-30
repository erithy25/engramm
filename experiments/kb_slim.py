"""A smaller fact bank for the lite pack: the most popular entities, a few names each.

    python -u -m experiments.kb_slim --src /dev/shm/engramm/kb/final/kb.sqlite --top 150000 \
        --out /dev/shm/engramm/kb/lite/kb.sqlite

* keeps the ``--top`` entities by popularity (how often facts point to them plus their redirects);
* keeps all their facts; entity-valued facts keep the target's title as text, so answers stay whole
  even when the target itself is dropped;
* keeps each entity's own title, its short form and at most ``--names`` other names (redirects),
  shortest first.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--top", type=int, default=150_000)
    ap.add_argument("--names", type=int, default=10)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    t0 = time.time()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        args.out.unlink()
    db = sqlite3.connect(args.out)
    db.execute("ATTACH DATABASE ? AS src", (f"file:{args.src}?mode=ro",))
    for (sql,) in db.execute("SELECT sql FROM src.sqlite_master WHERE type='table' AND name IN "
                             "('entity','alias','fact','meta')").fetchall():
        db.execute(sql)
    db.execute("CREATE TEMP TABLE keep AS SELECT id FROM src.entity ORDER BY popularity DESC, id LIMIT ?", (args.top,))
    db.execute("CREATE UNIQUE INDEX temp.keep_id ON keep(id)")
    db.execute("INSERT INTO entity SELECT e.* FROM src.entity e JOIN keep k ON k.id = e.id")
    # facts: the value's title stays in `value`; the link to a dropped entity is cleared
    db.execute("""INSERT INTO fact SELECT f.entity, f.prop, f.value, f.dtype,
                  CASE WHEN f.value_entity IN (SELECT id FROM keep) THEN f.value_entity END, f.src
                  FROM src.fact f JOIN keep k ON k.id = f.entity""")
    db.execute("""INSERT INTO alias SELECT name, entity, kind FROM (
                    SELECT a.name, a.entity, a.kind,
                           ROW_NUMBER() OVER (PARTITION BY a.entity ORDER BY a.kind, length(a.name), a.name) AS n
                    FROM src.alias a JOIN keep k ON k.id = a.entity)
                  WHERE kind < 2 OR n <= ?""", (args.names,))
    db.execute("INSERT INTO meta SELECT * FROM src.meta")
    for (sql,) in db.execute("SELECT sql FROM src.sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall():
        db.execute(sql)
    counts = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("entity", "alias", "fact")}
    db.execute("INSERT OR REPLACE INTO meta VALUES ('slim', ?)", (json.dumps({"top": args.top, "names": args.names,
                                                                              **counts}),))
    db.commit()
    db.execute("DETACH DATABASE src")
    db.execute("VACUUM")
    db.close()
    print(json.dumps({**counts, "MB": round(args.out.stat().st_size / 1e6, 1), "seconds": round(time.time() - t0)}))


if __name__ == "__main__":
    main()
