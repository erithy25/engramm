"""The network gate (engramm/web/egress.py, runtime/core/src/egress.rs): channels off by default,
https only, allowed hosts only (also after redirects), no private addresses for the web search,
a browser's user agent and only a few extra headers for the web search, a search the user asked
for even with the channel off, size limits, range requests, parallel fetches, settings of older
versions and the network log — against a local test server, with the Python backend and, when
built, the Rust backend (engramm-core egress)."""

from __future__ import annotations

import json
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from engramm.web.egress import (DEFAULT_SETTINGS, Egress, EgressError, NetworkLog, PythonBackend, Request, RustBackend,
                                check, host_allowed, is_private_host)

DATA = bytes(range(256)) * 8          # 2048 bytes


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.headers.get("Cookie"):
            self.send_response(400)
            self.end_headers()
            return
        if self.path == "/data":
            rng = self.headers.get("Range")
            body, code = DATA, 200
            if rng:
                a, b = rng.split("=")[1].split("-")
                body, code = DATA[int(a):int(b) + 1], 206
            self.send_response(code)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/ua":
            body = (self.headers.get("User-Agent") or "").encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/headers":
            body = json.dumps({k.lower(): v for k, v in self.headers.items()}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/redir-ok":
            self.send_response(302)
            self.send_header("Location", "/data")
            self.end_headers()
        elif self.path == "/redir-bad":
            self.send_response(302)
            self.send_header("Location", "https://evil.example/steal")
            self.end_headers()
        elif self.path == "/big":
            body = b"x" * (3 << 20)
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture(scope="module")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _core() -> str | None:
    for cand in (os.environ.get("ENGRAMM_CORE"), os.environ.get("ENGRAMM_CORE_BIN"),
                 "/dev/shm/engramm/target/release/engramm-core",
                 str(Path(__file__).resolve().parents[1] / "runtime" / "core" / "target" / "release" / "engramm-core"),
                 shutil.which("engramm-core")):
        if cand and Path(cand).exists():
            return cand
    return None


BACKENDS = ["python"] + (["rust"] if _core() else [])


def _egress(tmp_path, kind):
    e = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"))
    e.backend = PythonBackend() if kind == "python" else RustBackend(_core(), tmp_path / "rust.log")
    return e


def _on(e, *channels):
    for ch in channels:
        e.set_channel(ch, enabled=True)


def test_rules_without_network():
    s = json.loads(json.dumps(DEFAULT_SETTINGS))
    with pytest.raises(EgressError, match="switched off"):
        check(Request("shelf", "https://github.com/x", "t", ("github.com",)), s)
    with pytest.raises(EgressError, match="switched off"):
        check(Request("search", "https://www.bing.com/search?q=x", "t", ("bing.com",)), s)
    # "google …": the user asked for this one search, the switch need not be on
    check(Request("search", "https://www.bing.com/search?q=x", "t", ("bing.com",), explicit=True), s)
    with pytest.raises(EgressError, match="switched off"):       # only the web search knows such requests
        check(Request("shelf", "https://github.com/x", "t", ("github.com",), explicit=True), s)
    s["channels"]["shelf"]["enabled"] = s["channels"]["search"]["enabled"] = True
    check(Request("shelf", "https://github.com/x", "t", ("github.com",)), s)
    with pytest.raises(EgressError, match="https"):
        check(Request("shelf", "http://github.com/x", "t", ("github.com",)), s)
    with pytest.raises(EgressError, match="not allowed"):
        check(Request("shelf", "https://github.com.evil.org/", "t", ("github.com",)), s)
    with pytest.raises(EgressError, match="private"):
        check(Request("search", "https://192.168.0.1/", "t", ("*",)), s)
    with pytest.raises(EgressError, match="private"):
        check(Request("search", "https://printer.local/", "t", ("*",)), s)
    with pytest.raises(EgressError, match="credentials"):
        check(Request("search", "https://a:b@example.org/", "t", ("*",)), s)
    with pytest.raises(EgressError, match="unknown channel"):
        check(Request("messenger", "https://example.org/", "t", ("*",)), s)
    check(Request("search", "https://api.search.brave.com/x", "t", ("api.search.brave.com",),
                  headers=(("Accept", "application/json"), ("X-Subscription-Token", "k"))), s)
    with pytest.raises(EgressError, match="header not allowed"):
        check(Request("search", "https://example.org/", "t", ("*",), headers=(("Cookie", "a=b"),)), s)
    with pytest.raises(EgressError, match="bad value"):
        check(Request("search", "https://example.org/", "t", ("*",), headers=(("Accept", "a\r\nCookie: b"),)), s)
    assert host_allowed("objects.githubusercontent.com", ("githubusercontent.com",))
    assert not host_allowed("githubusercontent.com.evil.org", ("githubusercontent.com",))
    assert is_private_host("10.0.0.1") and is_private_host("router.local") and not is_private_host("example.org")


def test_settings_persist_and_validate(tmp_path):
    e = Egress(settings_path=tmp_path / "network.json")
    assert not any(e.enabled(c) for c in ("shelf", "feeds", "search"))      # offline by default
    e.set_channel("feeds", enabled=True, feeds=["bbc-world"])
    e.set_channel("search", engine="duckduckgo", brave_key="  BSAkey123  ")
    with pytest.raises(EgressError):
        e.set_channel("feeds", enabled="yes")
    with pytest.raises(EgressError):
        e.set_channel("nope", enabled=True)
    with pytest.raises(EgressError):
        e.set_channel("messenger", enabled=True)
    with pytest.raises(EgressError, match="engine"):
        e.set_channel("search", engine="altavista")
    with pytest.raises(EgressError, match="API key"):
        e.set_channel("search", brave_key="a key with spaces")
    with pytest.raises(EgressError, match="unknown setting"):
        e.set_channel("search", tor=True)
    e2 = Egress(settings_path=tmp_path / "network.json")
    e2.load()
    assert e2.enabled("feeds") and e2.settings["channels"]["feeds"]["feeds"] == ["bbc-world"]
    assert e2.settings["channels"]["search"] == {"enabled": False, "engine": "duckduckgo", "brave_key": "BSAkey123"}
    # the page sees whether a key is set, never the key
    pub = e2.status()["channels"]["search"]
    assert pub["brave_key_set"] is True and "brave_key" not in pub and "BSAkey123" not in json.dumps(e2.status())


def test_settings_of_3_1_carry_over(tmp_path):
    """network.json of 3.1 (Tor messenger, Tor for the shelf): the shelf and the feeds stay as they
    were; the messenger is gone and does not switch on the web search (that sends the question)."""
    (tmp_path / "network.json").write_text(json.dumps({"version": 1, "channels": {
        "shelf": {"enabled": True, "tor": True}, "feeds": {"enabled": True, "feeds": ["dw-en"]},
        "messenger": {"enabled": True, "tor": True}}}), encoding="utf-8")
    e = Egress(settings_path=tmp_path / "network.json")
    e.load()
    assert e.settings["channels"] == {"shelf": {"enabled": True}, "feeds": {"enabled": True, "feeds": ["dw-en"]},
                                      "search": {"enabled": False, "engine": "auto", "brave_key": ""}}
    (tmp_path / "network.json").write_text(json.dumps({"channels": {"search": {"enabled": "yes", "engine": "x"}}}),
                                           encoding="utf-8")
    e.load()                                   # wrong types and unknown engines fall back to the defaults
    assert e.settings["channels"]["search"] == {"enabled": False, "engine": "auto", "brave_key": ""}


@pytest.mark.parametrize("kind", BACKENDS)
def test_fetch_range_redirect_limits_and_log(server, tmp_path, kind):
    e = _egress(tmp_path, kind)
    loop = dict(allow_loopback=True)
    with pytest.raises(EgressError):                     # channel still off: nothing leaves
        e.fetch(Request("shelf", server + "/data", "bucket 0", ("github.com",), **loop))
    _on(e, "shelf", "search")
    r = e.fetch(Request("shelf", server + "/data", "bucket 0", ("github.com",), range=(10, 19), **loop))
    assert r.ok and r.status == 206 and r.body == DATA[10:20]
    r = e.fetch(Request("shelf", server + "/redir-ok", "bucket 1", ("github.com",), **loop))
    assert r.ok and r.body == DATA
    r = e.fetch(Request("shelf", server + "/redir-bad", "bucket 2", ("github.com",), **loop))
    assert not r.ok and "not allowed" in r.error
    r = e.fetch(Request("search", server + "/big", "page", ("*",), max_bytes=1 << 20, **loop))
    assert not r.ok and "larger" in r.error
    r = e.fetch(Request("shelf", server + "/ua", "page", ("*",), **loop))
    assert r.ok and r.body.decode().startswith("ENGRAMM/")
    r = e.fetch(Request("search", server + "/ua", "page", ("*",), **loop))      # search engines refuse other clients
    assert r.ok and r.body.decode().startswith("Mozilla/5.0")
    r = e.fetch(Request("search", server + "/headers", "page", ("*",),
                        headers=(("Accept-Language", "de-DE,de;q=0.9"), ("X-Subscription-Token", "k1")), **loop))
    sent = json.loads(r.body)
    assert sent["accept-language"] == "de-DE,de;q=0.9" and sent["x-subscription-token"] == "k1" and "cookie" not in sent
    many = e.fetch_many([Request("search", server + "/data", f"page {i}", ("*",), **loop) for i in range(6)]
                        + [Request("search", "https://10.1.2.3/", "page private", ("*",))])
    assert [m.ok for m in many[:6]] == [True] * 6 and all(m.body == DATA for m in many[:6]) and many[6] is None
    log = e.log.tail(20)
    assert [x["what"] for x in log][:2] == ["bucket 0", "bucket 0"]          # the refused one is logged too
    assert all("question" not in json.dumps(x) for x in log)
    assert any(x["ok"] and x["bytes"] == 10 for x in log)
    if kind == "rust":
        assert e._made >= 2                         # the fetches above ran in parallel service processes
        e.close()


def test_network_log_stays_bounded(tmp_path):
    log = NetworkLog(tmp_path / "network.log")
    for i in range(400):
        log.write({"channel": "feeds", "host": "example.org", "what": f"feed {i}", "bytes": 1, "status": 200,
                   "via": "direct", "ok": True})
        log._trim(limit=8_000)
    assert (tmp_path / "network.log").stat().st_size <= 8_000 + 200
    tail = log.tail(1000)
    assert tail[-1]["what"] == "feed 399" and len(tail) < 400          # the newest lines survive
