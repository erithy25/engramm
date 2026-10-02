"""Atlas: the three network channels behind one object (docs/SPEC_ATLAS.md).

``Atlas.candidates(question, names)`` escalates feeds → shelf → messenger, each stage only when
its channel is on and the earlier stages found nothing useful, and returns sentences with their
source for the existing answer extraction (``ChatBot.extra_rows``). ``Atlas.news(query)`` lists
headlines from the subscribed feeds. Nothing here ever sends the question: the shelf fetches
bucket numbers (with decoys), the feeds were fetched on a schedule, the messenger fetches a page
the local wayfinder chose, over Tor.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import threading
import time
import urllib.parse
from pathlib import Path

from engramm.web.egress import Egress, EgressError, Request

_FRESH = re.compile(r"\b(?:current(?:ly)?|latest|newest|recent(?:ly)?|now|today|tonight|yesterday|this (?:week|month|"
                    r"year)|right now|at the moment|nowadays|still|anymore|20(?:2[3-9]|3\d))\b", re.I)
_NEWS = re.compile(r"^(?:(?:hey|ok|so|please)[, ]+)*(?:what(?:'s| is| are)? (?:the )?(?:latest |new |recent |top )?"
                   r"(?:news|headlines)(?: today)?(?: (?:about|on|in|from|regarding) (?P<x>.+))?|"
                   r"(?:any |the )?(?:latest |new |recent )?(?:news|headlines|updates)(?: today)?(?: (?:about|on|in|from|"
                   r"regarding) (?P<x2>.+))?|what(?:'s| is) (?:going on|happening)(?: in (?P<x3>.+?))?(?: today| right now)?|"
                   r"what happened (?:today|yesterday|this week)(?: in (?P<x4>.+))?|tell me the news|"
                   r"(?:give me |show me )?(?:the )?news(?: please)?)\??$", re.I)


def is_fresh(question: str) -> bool:
    """A question about the present ("Who is the current CEO …?", "… in 2026?")."""
    return bool(_FRESH.search(question))


def news_request(text: str) -> tuple[bool, str | None]:
    m = _NEWS.match(text.strip())
    if not m:
        return False, None
    x = next((m.group(k) for k in ("x", "x2", "x3", "x4") if m.group(k)), None)
    return True, (x.strip(" ?.!") if x else None)


class Atlas:
    def __init__(self, egress: Egress, pack_dir: Path | None, state_dir: Path | None):
        self.egress = egress
        self.pack = Path(pack_dir) if pack_dir else None
        self.state = Path(state_dir) if state_dir else None
        self.lock = threading.Lock()
        self.feeds = self.refresher = None
        self.shelf = None
        self.wayfinder = None
        self.feed_list = []
        self.shelf_signed: bool | None = None
        self.shelf_error: str | None = None
        self._seed = None
        self.calib = load_calib()
        self._init_feeds()
        self._init_shelf()
        self._init_wayfinder()

    # -- set-up -------------------------------------------------------------------------------

    def _init_feeds(self) -> None:
        from engramm.web.feeds import FeedRefresher, FeedStore, load_feeds
        self.feed_list, default = load_feeds()
        self.default_feeds = default
        self.feeds = FeedStore(self.state / "feeds.sqlite" if self.state else None)
        self.refresher = FeedRefresher(self.egress, self.feeds, self.feed_list)
        if self.egress.enabled("feeds"):
            self.refresher.start()

    def _init_shelf(self) -> None:
        if self.pack is None:
            return
        ix, man, src = self.pack / "shelf_index", self.pack / "shelf.json", self.pack / "shelf_source.json"
        if not (ix / "name_hash.npy").exists() or not man.exists() or not src.exists():
            return
        from engramm.web.shelf import SHELF_HOSTS, ShelfClient, ShelfIndex, ShelfManifest, release_keys
        try:
            source = json.loads(src.read_text(encoding="utf-8"))
            hosts = tuple(source.get("hosts") or SHELF_HOSTS)
            manifest = ShelfManifest.load(man)
            keys = release_keys()
            # with a release key in the app, only a manifest signed by it is used (the bucket hashes
            # inside protect every bucket); without one, the pack's pinned hash is the protection
            self.shelf_signed = manifest.verify(keys) if keys else None
            if keys and not self.shelf_signed:
                self.shelf_error = "the shelf manifest is not signed by the release key"
                return
            self.shelf = ShelfClient(manifest, source["base_url"], ShelfIndex(ix), self.egress,
                                     (self.state or self.pack) / "shelf_cache", allow_hosts=hosts,
                                     allow_loopback=bool(source.get("allow_loopback")))
            self.shelf_info = {"docs": len(self.shelf.index), "date": source.get("date", ""),
                               "buckets": self.shelf.m.buckets, "signed": self.shelf_signed}
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            self.shelf = None

    def _init_wayfinder(self) -> None:
        if self.pack is not None and (self.pack / "wayfinder.sqlite").exists():
            from engramm.web.wayfinder import Wayfinder
            self.wayfinder = Wayfinder(self.pack / "wayfinder.sqlite")

    @property
    def seed(self) -> str:
        """A per-installation secret for the decoy buckets (never derived from a question)."""
        if self._seed is None:
            p = (self.state / "atlas_seed") if self.state else None
            if p is not None and p.exists():
                self._seed = p.read_text().strip()
            else:
                self._seed = hashlib.sha256(f"{time.time_ns()}|{id(self)}".encode()).hexdigest()
                if p is not None:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(self._seed)
        return self._seed

    def any_on(self) -> bool:
        return any(self.egress.enabled(c) for c in ("shelf", "feeds", "messenger"))

    def on_settings_changed(self) -> None:
        if self.egress.enabled("feeds"):
            if not self.egress.settings["channels"]["feeds"].get("feeds"):
                self.egress.set_channel("feeds", feeds=list(self.default_feeds))
            self.refresher.start()
            threading.Thread(target=self.refresher.refresh_now, daemon=True).start()
        else:
            self.refresher.stop()
        ch = self.egress.settings["channels"]
        if (self.egress.enabled("messenger") and ch["messenger"].get("tor", True)) or \
                (self.egress.enabled("shelf") and ch["shelf"].get("tor")):
            self.egress.warm_tor()

    # -- news ---------------------------------------------------------------------------------

    def news(self, topic: str | None, k: int = 5) -> list[dict]:
        if self.feeds is None:
            return []
        sel = self.egress.settings["channels"]["feeds"].get("feeds") or None
        items = self.feeds.search(topic, k=k, feeds=sel) if topic else self.feeds.latest(k=k, feeds=sel)
        names = {f.id: f.title for f in self.feed_list}
        for it in items:
            it["feed_title"] = names.get(it["feed"], it["feed"])
        return items

    # -- candidates for the answer extraction ---------------------------------------------------

    def candidates(self, question: str, names: list[str], max_rows: int = 24) -> tuple[list[tuple], list[str]]:
        """(sentences with source, stages used) for a question, escalating feeds → shelf → messenger."""
        rows: list[tuple[str, dict]] = []
        used = []
        if self.egress.enabled("feeds") and self.feeds is not None:
            sel = self.egress.settings["channels"]["feeds"].get("feeds") or None
            for it in self.feeds.search(question, k=6, feeds=sel):
                date = dt.datetime.fromtimestamp(it["published"], dt.timezone.utc).strftime("%Y-%m-%d")
                src = {"kind": "feed", "source": it["feed"], "key": it["link"] or it["title"], "title": it["title"],
                       "as_of": date}
                for text in _sentences(f"{it['title']}. {it['summary']}"):
                    rows.append((text, src))
            if rows:
                used.append("feeds")
        if self.shelf is not None and self.egress.enabled("shelf"):
            try:
                prefer = names[0] if names else None
                docs = self.shelf.documents(question, k=3, seed=self.seed, prefer_title=prefer)
            except EgressError:
                docs = []
            from engramm.web.shelf import best_sentences
            self.last_docs = docs                    # the whole articles, for rules that read further
            got = best_sentences(question, docs, n=14, context=True)
            for _, text, d, prev in got:
                rows.append((text, {"kind": "shelf", "source": "wikipedia", "key": d["t"], "title": d["t"],
                                    "as_of": d.get("d", "")}, prev))
            if got:
                used.append("shelf")
        if not used and self.egress.enabled("messenger"):
            rows += self._messenger(question, names)
            if rows:
                used.append("messenger")
        return rows[:max_rows], used

    def _messenger(self, question: str, names: list[str]) -> list[tuple[str, dict]]:
        """Pages the wayfinder points to (official site; the live Wikipedia article), over Tor."""
        from engramm.web.clean import paragraphs
        from engramm.web.shelf import best_sentences
        targets: list[tuple[str, str]] = []
        for n in names[:2]:
            if self.wayfinder is not None:
                targets += self.wayfinder.sites(n, limit=1)
            targets.append((n, "https://en.wikipedia.org/wiki/" + urllib.parse.quote(n.replace(" ", "_"))))
        tor = bool(self.egress.settings["channels"]["messenger"].get("tor", True))
        docs = []
        for title, url in targets[:3]:
            host = urllib.parse.urlsplit(url).hostname or ""
            try:
                res = self.egress.fetch(Request("messenger", url, "page", ("*",), tor=tor))
            except EgressError:
                continue
            if not res.ok or "html" not in (res.content_type or "text/html"):
                continue
            text = "\n".join(paragraphs(res.body.decode("utf-8", "replace")))
            if text:
                docs.append({"t": title, "x": text, "url": url, "host": host})
        out = []
        today = dt.date.today().isoformat()
        for _, text, d, prev in best_sentences(question, docs, n=14, context=True):
            out.append((text, {"kind": "web", "source": d["host"], "key": d["url"], "title": d["t"], "as_of": today},
                        prev))
        return out

    def status(self) -> dict:
        from engramm.web.feeds import Feed  # noqa: F401
        sel = set(self.egress.settings["channels"]["feeds"].get("feeds") or [])
        return {**self.egress.status(),
                "feeds": [{"id": f.id, "title": f.title, "lang": f.lang, "selected": f.id in sel} for f in self.feed_list],
                "feed_items": self.feeds.count() if self.feeds else 0,
                "feed_state": self.feeds.state() if self.feeds else {},
                "shelf": getattr(self, "shelf_info", None), "shelf_error": self.shelf_error,
                "wayfinder": self.wayfinder is not None}


CALIB_PATH = Path(__file__).resolve().parent / "atlas_calib.json"


def load_calib(path: Path = CALIB_PATH):
    """(confidence model, θ) for answers from fetched text (experiments/atlas_calib.py), or None."""
    if not path.exists():
        return None
    from engramm.chat.calib import ConfCalibrator
    d = json.loads(path.read_text(encoding="utf-8"))
    return ConfCalibrator(d["w"], d.get("r0_bins") or (6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.5)), float(d["theta"])


_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text) if 20 <= len(s.strip()) <= 500]
