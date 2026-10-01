"""The subscription channel (Atlas K2, docs/SPEC_ATLAS.md): selected RSS/Atom feeds fetched on a
schedule — never because of a question — and kept in a local full-text index.

* parsing: RSS 2.0, RSS 1.0 (RDF) and Atom; a document with a DTD or entity declaration is
  refused (no external entities, no entity expansion);
* storage: ``feeds.sqlite`` with SQLite FTS5 (BM25) over title and summary; items older than 30
  days are deleted;
* search: BM25 times a recency factor (half-life 3 days), so "latest news about X" finds today's
  items first;
* schedule: every 3 hours ± 30 %, in a background thread, only while the channel is on.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
import html
import json
import random
import re
import sqlite3
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

FEEDS_PATH = Path(__file__).resolve().parents[2] / "data" / "feeds.yaml"
KEEP_DAYS = 30
HALF_LIFE_DAYS = 3.0
INTERVAL_S = 3 * 3600


@dataclass
class Feed:
    id: str
    title: str
    url: str
    lang: str = "en"
    topic: str = "news"


@dataclass
class Item:
    feed: str
    guid: str
    title: str
    summary: str
    link: str
    published: int          # Unix seconds (fetch time when the feed gives none)


def load_feeds(path: Path = FEEDS_PATH) -> tuple[list[Feed], list[str]]:
    """The curated feed list. The JSON copy in the package (feeds.json) is used when the YAML
    source is not there (the frozen app)."""
    js = Path(__file__).resolve().parent / "feeds.json"
    if path.exists():
        import yaml
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
    elif js.exists():
        d = json.loads(js.read_text(encoding="utf-8"))
    else:
        return [], []
    return [Feed(**f) for f in d.get("feeds", [])], list(d.get("default", []))


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

class FeedError(ValueError):
    pass


_TAG = re.compile(r"<[^>]+>")


def _text(s: str | None) -> str:
    if not s:
        return ""
    s = _TAG.sub(" ", html.unescape(s))
    return " ".join(html.unescape(s).split())


def _date(s: str | None, fallback: int) -> int:
    if not s:
        return fallback
    s = s.strip()
    try:
        return int(email.utils.parsedate_to_datetime(s).timestamp())
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return fallback


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_feed(data: bytes, feed_id: str, now: int | None = None) -> list[Item]:
    """Items of an RSS 2.0, RSS 1.0 (RDF) or Atom document."""
    now = now or int(time.time())
    head = data[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in data.lower():
        raise FeedError("feed with a DTD or entity declarations refused")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise FeedError(f"not well-formed: {e}") from e
    items = []
    for el in root.iter():
        name = _local(el.tag)
        if name not in ("item", "entry"):
            continue
        f = {_local(c.tag): c for c in el}
        title = _text(f["title"].text if "title" in f else "")
        link = ""
        if "link" in f:
            link = (f["link"].text or "").strip() or f["link"].get("href", "")
        for c in el:
            if _local(c.tag) == "link" and c.get("rel", "alternate") == "alternate" and c.get("href"):
                link = c.get("href")
                break
        summary = ""
        for key in ("description", "summary", "content", "encoded"):
            if key in f and (f[key].text or "").strip():
                summary = _text(f[key].text)
                break
        date = None
        for key in ("pubdate", "published", "updated", "date", "issued"):
            if key in f and f[key].text:
                date = f[key].text
                break
        guid = (f["guid"].text if "guid" in f and f["guid"].text else (f["id"].text if "id" in f else "")) or link or title
        if not title:
            continue
        if link and not link.startswith("https://") and not link.startswith("http://"):
            link = ""
        items.append(Item(feed_id, hashlib.sha256(f"{feed_id}|{guid}".encode()).hexdigest()[:32], title[:300],
                          summary[:1200], link[:500], _date(date, now)))
    return items


# ---------------------------------------------------------------------------
# the store
# ---------------------------------------------------------------------------

class FeedStore:
    def __init__(self, path: Path | None):
        self.path = Path(path) if path else None
        self.lock = threading.Lock()
        self.db = sqlite3.connect(str(self.path) if self.path else ":memory:", check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS item(id INTEGER PRIMARY KEY, feed TEXT, guid TEXT UNIQUE, title TEXT,
                summary TEXT, link TEXT, published INTEGER, fetched INTEGER);
            CREATE VIRTUAL TABLE IF NOT EXISTS item_fts USING fts5(title, summary, content='item', content_rowid='id',
                tokenize='porter unicode61');
            CREATE TRIGGER IF NOT EXISTS item_ai AFTER INSERT ON item BEGIN
                INSERT INTO item_fts(rowid, title, summary) VALUES (new.id, new.title, new.summary); END;
            CREATE TRIGGER IF NOT EXISTS item_ad AFTER DELETE ON item BEGIN
                INSERT INTO item_fts(item_fts, rowid, title, summary) VALUES ('delete', old.id, old.title, old.summary); END;
            CREATE TABLE IF NOT EXISTS fetch_state(feed TEXT PRIMARY KEY, last INTEGER, ok INTEGER, error TEXT);
        """)

    def add(self, items: list[Item], now: int | None = None) -> int:
        now = now or int(time.time())
        n = 0
        with self.lock:
            for it in items:
                cur = self.db.execute("INSERT OR IGNORE INTO item(feed, guid, title, summary, link, published, fetched) "
                                      "VALUES (?,?,?,?,?,?,?)", (it.feed, it.guid, it.title, it.summary, it.link,
                                                                 it.published, now))
                n += cur.rowcount
            self.db.commit()
        return n

    def prune(self, now: int | None = None) -> int:
        now = now or int(time.time())
        with self.lock:
            cur = self.db.execute("DELETE FROM item WHERE published < ?", (now - KEEP_DAYS * 86400,))
            self.db.commit()
            return cur.rowcount

    def search(self, query: str, k: int = 8, now: int | None = None, feeds: list[str] | None = None) -> list[dict]:
        """Items for a question, best first (BM25 × recency)."""
        now = now or int(time.time())
        words = [w for w in re.findall(r"[\w'-]+", query.lower()) if len(w) > 2 and w not in _STOP]
        if not words:
            return []
        match = " OR ".join('"' + w.replace('"', "") + '"' for w in dict.fromkeys(words))
        with self.lock:
            rows = self.db.execute(
                "SELECT i.id, i.feed, i.title, i.summary, i.link, i.published, bm25(item_fts, 2.0, 1.0) "
                "FROM item_fts JOIN item i ON i.id = item_fts.rowid WHERE item_fts MATCH ? LIMIT 200",
                (match,)).fetchall()
        out = []
        for rid, feed, title, summary, link, pub, bm in rows:
            if feeds and feed not in feeds:
                continue
            age = max(0.0, (now - pub) / 86400.0)
            score = (-bm) * 0.5 ** (age / HALF_LIFE_DAYS)
            out.append({"id": rid, "feed": feed, "title": title, "summary": summary, "link": link,
                        "published": pub, "score": score})
        out.sort(key=lambda x: (-x["score"], -x["published"]))
        return out[:k]

    def latest(self, k: int = 8, feeds: list[str] | None = None) -> list[dict]:
        q = "SELECT id, feed, title, summary, link, published FROM item"
        args: tuple = ()
        if feeds:
            q += " WHERE feed IN (%s)" % ",".join("?" * len(feeds))
            args = tuple(feeds)
        q += " ORDER BY published DESC LIMIT ?"
        with self.lock:
            rows = self.db.execute(q, args + (k,)).fetchall()
        return [{"id": r[0], "feed": r[1], "title": r[2], "summary": r[3], "link": r[4], "published": r[5]}
                for r in rows]

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM item").fetchone()[0]

    def note_fetch(self, feed: str, ok: bool, error: str = "") -> None:
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO fetch_state(feed, last, ok, error) VALUES (?,?,?,?)",
                            (feed, int(time.time()), int(ok), error[:200]))
            self.db.commit()

    def state(self) -> dict:
        with self.lock:
            return {r[0]: {"last": r[1], "ok": bool(r[2]), "error": r[3]}
                    for r in self.db.execute("SELECT feed, last, ok, error FROM fetch_state")}


_STOP = frozenset("the and for with what who when where why how which this that from about latest news new today "
                  "recent recently current happening happened tell any some are was were has have had did does is "
                  "there their they them his her its into over after more most".split())


# ---------------------------------------------------------------------------
# fetching on a schedule
# ---------------------------------------------------------------------------

class FeedRefresher:
    """Fetches the selected feeds every few hours (with jitter) while the channel is on."""

    def __init__(self, egress, store: FeedStore, feeds: list[Feed], interval: float = INTERVAL_S,
                 allow_loopback: bool = False):
        self.egress = egress
        self.store = store
        self.feeds = {f.id: f for f in feeds}
        self.interval = interval
        self.allow_loopback = allow_loopback
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.rng = random.Random()

    def selected(self) -> list[Feed]:
        ids = self.egress.settings["channels"]["feeds"].get("feeds") or []
        return [self.feeds[i] for i in ids if i in self.feeds]

    def refresh_now(self) -> dict:
        """Fetch every selected feed once; {feed id: new items or an error}."""
        from engramm.web.egress import EgressError, Request, host_of
        out = {}
        if not self.egress.enabled("feeds"):
            return out
        for f in self.selected():
            try:
                res = self.egress.fetch(Request("feeds", f.url, f"feed {f.id}", (host_of(f.url),),
                                                allow_loopback=self.allow_loopback))
            except EgressError as e:
                out[f.id] = f"refused: {e}"
                self.store.note_fetch(f.id, False, str(e))
                continue
            if not res.ok:
                out[f.id] = res.error
                self.store.note_fetch(f.id, False, res.error)
                continue
            try:
                n = self.store.add(parse_feed(res.body, f.id))
                out[f.id] = n
                self.store.note_fetch(f.id, True)
            except FeedError as e:
                out[f.id] = str(e)
                self.store.note_fetch(f.id, False, str(e))
        self.store.prune()
        return out

    def _run(self) -> None:
        first = True
        while not self._stop.is_set():
            wait = self.rng.uniform(5, 60) if first else self.interval * self.rng.uniform(0.7, 1.3)
            first = False
            if self._stop.wait(wait):
                return
            if self.egress.enabled("feeds"):
                try:
                    self.refresh_now()
                except Exception:              # the schedule keeps running; errors are in fetch_state
                    pass

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True, name="feeds")
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
