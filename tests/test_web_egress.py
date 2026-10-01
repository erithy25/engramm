"""The network gate (engramm/web/egress.py, runtime/core/src/egress.rs): channels off by default,
https only, allowed hosts only (also after redirects), no private addresses for the messenger,
size limits, range requests and the network log — against a local test server, with the
Python backend and, when built, the Rust backend (engramm-core egress)."""

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
    s["channels"]["shelf"]["enabled"] = s["channels"]["messenger"]["enabled"] = True
    check(Request("shelf", "https://github.com/x", "t", ("github.com",)), s)
    with pytest.raises(EgressError, match="https"):
        check(Request("shelf", "http://github.com/x", "t", ("github.com",)), s)
    with pytest.raises(EgressError, match="not allowed"):
        check(Request("shelf", "https://github.com.evil.org/", "t", ("github.com",)), s)
    with pytest.raises(EgressError, match="private"):
        check(Request("messenger", "https://192.168.0.1/", "t", ("*",)), s)
    with pytest.raises(EgressError, match="credentials"):
        check(Request("messenger", "https://a:b@example.org/", "t", ("*",)), s)
    assert host_allowed("objects.githubusercontent.com", ("githubusercontent.com",))
    assert not host_allowed("githubusercontent.com.evil.org", ("githubusercontent.com",))
    assert is_private_host("10.0.0.1") and is_private_host("router.local") and not is_private_host("example.org")


def test_settings_persist_and_validate(tmp_path):
    e = Egress(settings_path=tmp_path / "network.json")
    assert not any(e.enabled(c) for c in ("shelf", "feeds", "messenger"))      # offline by default
    e.set_channel("feeds", enabled=True, feeds=["bbc-world"])
    with pytest.raises(EgressError):
        e.set_channel("feeds", enabled="yes")
    with pytest.raises(EgressError):
        e.set_channel("nope", enabled=True)
    e2 = Egress(settings_path=tmp_path / "network.json")
    e2.load()
    assert e2.enabled("feeds") and e2.settings["channels"]["feeds"]["feeds"] == ["bbc-world"]


@pytest.mark.parametrize("kind", BACKENDS)
def test_fetch_range_redirect_limits_and_log(server, tmp_path, kind):
    e = _egress(tmp_path, kind)
    loop = dict(allow_loopback=True)
    with pytest.raises(EgressError):                     # channel still off: nothing leaves
        e.fetch(Request("shelf", server + "/data", "bucket 0", ("github.com",), **loop))
    _on(e, "shelf", "messenger")
    r = e.fetch(Request("shelf", server + "/data", "bucket 0", ("github.com",), range=(10, 19), **loop))
    assert r.ok and r.status == 206 and r.body == DATA[10:20]
    r = e.fetch(Request("shelf", server + "/redir-ok", "bucket 1", ("github.com",), **loop))
    assert r.ok and r.body == DATA
    r = e.fetch(Request("shelf", server + "/redir-bad", "bucket 2", ("github.com",), **loop))
    assert not r.ok and "not allowed" in r.error
    r = e.fetch(Request("messenger", server + "/big", "page", ("*",), max_bytes=1 << 20, **loop))
    assert not r.ok and "larger" in r.error
    r = e.fetch(Request("messenger", server + "/ua", "page", ("*",), **loop))
    assert r.ok and r.body.decode().startswith("ENGRAMM/")
    r = e.fetch(Request("messenger", server + "/data", "page", ("*",), tor=True, **loop))
    assert not r.ok and "tor" in r.error
    log = e.log.tail(20)
    assert [x["what"] for x in log][:2] == ["bucket 0", "bucket 0"]          # the refused one is logged too
    assert all("question" not in json.dumps(x) for x in log)
    assert any(x["ok"] and x["bytes"] == 10 for x in log)
    if kind == "rust":
        e.backend.close()


def test_network_log_stays_bounded(tmp_path):
    log = NetworkLog(tmp_path / "network.log")
    for i in range(400):
        log.write({"channel": "feeds", "host": "example.org", "what": f"feed {i}", "bytes": 1, "status": 200,
                   "via": "direct", "ok": True})
        log._trim(limit=8_000)
    assert (tmp_path / "network.log").stat().st_size <= 8_000 + 200
    tail = log.tail(1000)
    assert tail[-1]["what"] == "feed 399" and len(tail) < 400          # the newest lines survive
