"""The wayfinder (Atlas channel K3, docs/SPEC_ATLAS.md): which web page to read about a named
thing, decided on this computer. ``wayfinder.sqlite`` (in a knowledge pack) maps titles and their
name forms to official websites (DBpedia foaf:homepage, Wikidata P856). It served the Tor messenger
of 3.1, which the web search replaced (engramm/web/search.py); the packs still carry the table, the
app no longer reads it.
"""

from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path


def name_key(s: str) -> str:
    s = re.sub(r"\s*\([^)]*\)$", "", s.strip())
    return " ".join(s.lower().replace("’", "'").split())


class Wayfinder:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._local = threading.local()

    @property
    def db(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is None:
            con = sqlite3.connect(f"file:{self.path}?mode=ro&immutable=1", uri=True, check_same_thread=False)
            self._local.con = con
        return con

    def sites(self, name: str, limit: int = 2) -> list[tuple[str, str]]:
        """(title, https URL) for a name, best first (exact titles before name forms)."""
        rows = self.db.execute("SELECT title, url FROM site WHERE key=? ORDER BY exact DESC, rank LIMIT ?",
                               (name_key(name), limit)).fetchall()
        out = []
        for title, url in rows:
            if url.startswith("http://"):
                url = "https://" + url[len("http://"):]
            if url.startswith("https://"):
                out.append((title, url))
        return out


def build_db(path: Path, pairs) -> int:
    """pairs: iterable of (title, url, rank). Writes the table site(key, title, url, exact, rank)."""
    path = Path(path)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE site(key TEXT, title TEXT, url TEXT, exact INTEGER, rank INTEGER)")
    n = 0
    batch = []
    for title, url, rank in pairs:
        batch.append((title.lower(), title, url, 1, rank))
        k = name_key(title)
        if k != title.lower():
            batch.append((k, title, url, 0, rank))
        n += 1
        if len(batch) >= 50000:
            con.executemany("INSERT INTO site VALUES (?,?,?,?,?)", batch)
            batch = []
    if batch:
        con.executemany("INSERT INTO site VALUES (?,?,?,?,?)", batch)
    con.execute("CREATE INDEX site_key ON site(key)")
    con.commit()
    con.execute("VACUUM")
    con.close()
    return n
