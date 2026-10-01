"""The subscription channel (engramm/web/feeds.py): RSS 2.0 / RSS 1.0 / Atom parsing, refusal of
DTDs and entities, the local full-text store with recency, and a refresh through the egress
against a local server (nothing is fetched while the channel is off)."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from engramm.web.egress import Egress, NetworkLog, PythonBackend
from engramm.web.feeds import FeedError, FeedRefresher, FeedStore, Feed, load_feeds, parse_feed

NOW = int(time.time())
RSS = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Volcano erupts in Iceland</title><link>https://example.org/a</link>
<description>&lt;p&gt;Lava flows near Grindavik, authorities said.&lt;/p&gt;</description>
<pubDate>{time.strftime('%a, %d %b %Y %H:%M:%S +0000', time.gmtime(NOW - 3600))}</pubDate><guid>a1</guid></item>
<item><title>Old volcano story</title><link>https://example.org/b</link><description>From long ago.</description>
<pubDate>{time.strftime('%a, %d %b %Y %H:%M:%S +0000', time.gmtime(NOW - 20 * 86400))}</pubDate><guid>b1</guid></item>
</channel></rss>""".encode()
ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>A</title>
<entry><title>Mars rover finds water ice</title><link rel="alternate" href="https://example.org/m"/>
<id>tag:m</id><updated>2026-09-30T10:00:00Z</updated><summary>The rover drilled.</summary></entry></feed>"""
RDF = b"""<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>D</title></channel>
<item><title>Elections in Berlin</title><link>https://example.org/e</link><description>Votes counted.</description>
<dc:date>2026-09-29T08:00:00Z</dc:date></item></rdf:RDF>"""
EVIL = b"""<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>
<rss><channel><item><title>&lol2;</title></item></channel></rss>"""


def test_parse_three_formats_and_refuse_dtd():
    items = parse_feed(RSS, "t", now=NOW)
    assert [i.title for i in items] == ["Volcano erupts in Iceland", "Old volcano story"]
    assert items[0].summary == "Lava flows near Grindavik, authorities said." and items[0].link == "https://example.org/a"
    a = parse_feed(ATOM, "a")[0]
    assert a.title.startswith("Mars rover") and a.link == "https://example.org/m"
    r = parse_feed(RDF, "d")[0]
    assert r.title == "Elections in Berlin" and r.published > 0
    with pytest.raises(FeedError):
        parse_feed(EVIL, "x")
    with pytest.raises(FeedError):
        parse_feed(b"<rss><channel><item>", "x")


def test_store_search_prefers_recent_and_prunes(tmp_path):
    st = FeedStore(tmp_path / "feeds.sqlite")
    assert st.add(parse_feed(RSS, "t", now=NOW), now=NOW) == 2
    assert st.add(parse_feed(RSS, "t", now=NOW), now=NOW) == 0          # no duplicates
    hits = st.search("latest news about the volcano", now=NOW)
    assert hits[0]["title"] == "Volcano erupts in Iceland"
    assert st.latest(1)[0]["title"] == "Volcano erupts in Iceland"
    assert st.prune(now=NOW + 15 * 86400) == 1                          # the 20-day-old item is gone at day 35
    assert st.count() == 1


def test_feed_list_is_valid_and_in_sync():
    feeds, default = load_feeds()
    assert len(feeds) >= 10 and all(f.url.startswith("https://") for f in feeds)
    assert set(default) <= {f.id for f in feeds}
    root = Path(__file__).resolve().parents[1]
    import yaml
    assert json.loads((root / "engramm" / "web" / "feeds.json").read_text()) == \
        yaml.safe_load((root / "data" / "feeds.yaml").read_text())


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = RSS if self.path == "/rss" else EVIL
        self.send_response(200)
        self.send_header("Content-Type", "application/rss+xml")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_refresh_through_egress(tmp_path):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        eg = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"))
        eg.backend = PythonBackend()
        store = FeedStore(tmp_path / "feeds.sqlite")
        r = FeedRefresher(eg, store, [Feed("good", "Good", base + "/rss"), Feed("evil", "Evil", base + "/evil")],
                          allow_loopback=True)
        eg.set_channel("feeds", feeds=["good", "evil"])
        assert r.refresh_now() == {} and eg.log.tail() == []             # off: nothing leaves
        eg.set_channel("feeds", enabled=True)
        res = r.refresh_now()
        assert res["good"] == 2 and "refused" in str(res["evil"]) or "DTD" in str(res["evil"])
        assert store.search("volcano")[0]["feed"] == "good"
        assert {x["what"] for x in eg.log.tail()} == {"feed good", "feed evil"}
    finally:
        srv.shutdown()
