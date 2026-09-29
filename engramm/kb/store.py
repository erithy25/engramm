"""The fact bank on disk: one SQLite file, opened read-only (a few MB of memory, any size on disk).

Tables (experiments/kb_dbpedia_build.py):
    entity(id, title, type, popularity)
    alias(name, entity, kind)          name in lower case; kind 0 title, 1 title without "(…)", 2 redirect
    fact(entity, prop, value, dtype, value_entity)
"""

from __future__ import annotations

import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entity:
    id: int
    title: str
    type: str | None
    popularity: int

    @property
    def name(self) -> str:
        """The title without its disambiguation: "Mercury (planet)" → "Mercury"."""
        return re.sub(r"\s*\([^)]*\)$", "", self.title)


@dataclass(frozen=True)
class Fact:
    prop: str
    value: str
    dtype: str
    value_entity: int | None


class FactBank:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        self._local = threading.local()

    @property
    def db(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is None:
            con = sqlite3.connect(f"file:{self.path}?mode=ro&immutable=1", uri=True, check_same_thread=False)
            con.execute("PRAGMA query_only=1")
            self._local.con = con
        return con

    def entity(self, eid: int) -> Entity | None:
        row = self.db.execute("SELECT id, title, type, popularity FROM entity WHERE id=?", (eid,)).fetchone()
        return Entity(*row) if row else None

    def by_title(self, title: str) -> Entity | None:
        row = self.db.execute("SELECT id, title, type, popularity FROM entity WHERE title=?", (title,)).fetchone()
        return Entity(*row) if row else None

    def link(self, name: str, limit: int = 8) -> list[tuple[Entity, int]]:
        """Entities with this name (title, title without its "(…)" part, or a redirect), best
        first: exact titles, then by popularity. Returns (entity, alias kind)."""
        key = " ".join(name.lower().split())
        rows = self.db.execute(
            "SELECT e.id, e.title, e.type, e.popularity, MIN(a.kind) FROM alias a JOIN entity e ON e.id = a.entity "
            "WHERE a.name=? GROUP BY e.id ORDER BY MIN(a.kind) = 0 DESC, e.popularity DESC, e.id LIMIT ?",
            (key, limit)).fetchall()
        return [(Entity(*r[:4]), r[4]) for r in rows]

    @property
    def has_src(self) -> bool:
        v = getattr(self, "_has_src", None)
        if v is None:
            v = self._has_src = any(c[1] == "src" for c in self.db.execute("PRAGMA table_info(fact)"))
        return v

    def facts(self, eid: int, props: tuple[str, ...]) -> list[Fact]:
        """The facts of an entity for these properties. Where Wikidata supplied a property, only
        its values count (they are newer and complete); otherwise DBpedia's."""
        q = ",".join("?" * len(props))
        src = "f.src" if self.has_src else "NULL"
        rows = self.db.execute(
            "SELECT f.prop, CASE WHEN f.value = '' AND f.value_entity IS NOT NULL THEN e.title ELSE f.value END, "
            f"f.dtype, f.value_entity, {src} FROM fact f LEFT JOIN entity e ON e.id = f.value_entity "
            f"WHERE f.entity=? AND f.prop IN ({q}) ORDER BY f.rowid", (eid, *props)).fetchall()
        wd_props = {r[0] for r in rows if r[4] == "wikidata"}
        return [Fact(*r[:4]) for r in rows if r[0] not in wd_props or r[4] == "wikidata"]

    def meta(self) -> dict:
        import json
        return {k: json.loads(v) for k, v in self.db.execute("SELECT key, value FROM meta").fetchall()}
