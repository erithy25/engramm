"""The chat application server (engramm/app): routes, conversation contexts, memory, safety."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from engramm.app.server import ChatService, serve, source_view


class _Reply:
    def __init__(self, text, kind="answer", source=None):
        self.text, self.kind, self.source = text, kind, source

    def to_dict(self):
        return {"kind": self.kind, "text": self.text, "answer": self.text, "guess": None, "evidence": "E.",
                "source": self.source, "confidence": 1.0, "via": "lookup", "resolved": None, "alternatives": []}


class _Memory:
    def __init__(self):
        self.texts = {}

    def forget(self, sid):
        self.texts.pop(sid)


class _Bot:
    """The core the service forgets through."""

    def __init__(self):
        self.memory = _Memory()
        self.c = type("C", (), {"index": type("I", (), {"n": 42})(),
                                "tok": type("T", (), {"encode": staticmethod(lambda t: t.split())})()})()

    def user_texts(self):
        return dict(self.memory.texts)

    def refresh(self):
        pass


class _Assistant:
    """Answers with the conversation's previous message: proves each conversation keeps its state."""

    def __init__(self, bot):
        self.bot = bot

    def turn(self, state, message):
        prev = state.ctx.get("mention")
        state.ctx["mention"] = message
        state.turn += 1
        if message.startswith("remember "):
            sid = f"u{len(self.bot.memory.texts)}"
            self.bot.memory.texts[sid] = message[9:]
            state.ctx["last_learned"] = sid
            return _Reply("Got it.", "learned")
        return _Reply(f"prev={prev}", source={"kind": "base", "source": "wiki", "key": "Ada Lovelace"})


@pytest.fixture()
def running():
    svc = ChatService("unused")
    svc.bot = _Bot()
    svc.assistant = _Assistant(svc.bot)
    srv = serve(svc, port=0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", svc
    srv.shutdown()
    srv.server_close()


def _call(base, path, body=None):
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


def test_page_and_assets(running):
    import re
    base, _ = running
    code, ct, page = _call(base, "/")
    assert code == 200 and ct.startswith("text/html")
    # the built page (ui/ → engramm/app/web) names its script and stylesheet with content hashes
    js = re.search(rb'src="\./(assets/[^"]+\.js)"', page).group(1).decode()
    css = re.search(rb'href="\./(assets/[^"]+\.css)"', page).group(1).decode()
    for path, ctype in (("/" + js, "text/javascript"), ("/" + css, "text/css"), ("/logo.svg", "image/svg+xml"),
                        ("/icons/icon-192.png", "image/png"), ("/manifest.webmanifest", "application/manifest+json")):
        code, ct, body = _call(base, path)
        assert code == 200 and ct.startswith(ctype) and body, path


def test_no_files_outside_the_web_folder(running):
    base, _ = running
    for path in ("/../server.py", "/%2e%2e/server.py", "/..%2fserver.py", "/nope.txt"):
        code, _, _ = _call(base, path)
        assert code == 404, path


def test_health_and_each_conversation_keeps_its_context(running):
    base, _ = running
    assert json.loads(_call(base, "/api/health")[2]) == {"ready": True, "error": None, "mode": None,
                                                         "sentences": 42}
    ask = lambda conv, msg: json.loads(_call(base, "/api/chat", {"conversation": conv, "message": msg})[2])
    assert ask("a", "one")["text"] == "prev=None"
    assert ask("b", "two")["text"] == "prev=None"
    r = ask("a", "three")
    assert r["text"] == "prev=one"
    assert r["source"] == {"kind": "wikipedia", "title": "Ada Lovelace",
                           "url": "https://en.wikipedia.org/wiki/Ada_Lovelace"}


def test_memory_list_and_forget(running):
    base, _ = running
    _call(base, "/api/chat", {"conversation": "a", "message": "remember my name is Ada"})
    items = json.loads(_call(base, "/api/memory")[2])["items"]
    assert [i["preview"] for i in items] == ["my name is Ada"]
    code, _, body = _call(base, "/api/memory/forget", {"source": items[0]["source"]})
    assert code == 200 and json.loads(body)["forgot"] == items[0]["source"]
    assert json.loads(_call(base, "/api/memory")[2])["items"] == []
    assert _call(base, "/api/memory/forget", {"source": "missing"})[0] == 400


def test_bad_requests(running):
    base, svc = running
    assert _call(base, "/api/chat", {"conversation": "a", "message": "   "})[0] == 400
    assert _call(base, "/api/chat", {"conversation": "a", "message": "x" * 12001})[0] == 400
    svc.bot = svc.assistant = None
    svc.error = None
    code, _, body = _call(base, "/api/chat", {"conversation": "a", "message": "hi"})
    assert code == 503 and "loading" in json.loads(body)["error"]


def test_source_view():
    assert source_view(None) is None
    assert source_view({"kind": "user", "source": "u1"})["title"] == "You told me"
    web = source_view({"kind": "base", "source": "c4", "key": "https://www.example.org/a/b"})
    assert web == {"kind": "web", "title": "www.example.org", "url": "https://www.example.org/a/b"}


def test_posts_need_a_json_content_type(running):
    base, _ = running
    req = urllib.request.Request(base + "/api/chat", data=b'{"conversation": "a", "message": "hi"}',
                                 headers={"Content-Type": "text/plain"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 415


def test_openable_links():
    from engramm.app.server import openable
    for ok in ("https://en.wikipedia.org/wiki/Ada_Lovelace", "https://de.wikipedia.org/wiki/Berlin",
               "https://en.m.wikipedia.org/wiki/X", "https://www.wikidata.org/wiki/Q7259"):
        assert openable(ok), ok
    for bad in ("http://en.wikipedia.org/wiki/X", "https://evil.org/wiki", "https://en.wikipedia.org.evil.org/",
                "file:///etc/passwd", "javascript:alert(1)", "https://user@en.wikipedia.org/",
                "https://en.wikipedia.org:8443/x", "https://wikipedia.org.evil/", ""):
        assert not openable(bad), bad


def test_open_only_in_desktop_mode(monkeypatch):
    import engramm.app.server as server_mod
    opened = []
    monkeypatch.setattr(server_mod.webbrowser, "open", lambda url: opened.append(url))
    for desktop in (False, True):
        svc = ChatService("unused")
        srv = serve(svc, port=0, desktop=desktop)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        code, _, _ = _call(base, "/api/open", {"url": "https://en.wikipedia.org/wiki/Ada_Lovelace"})
        assert code == (200 if desktop else 404)
        if desktop:
            assert _call(base, "/api/open", {"url": "https://evil.org/"})[0] == 400
        srv.shutdown()
        srv.server_close()
    assert opened == ["https://en.wikipedia.org/wiki/Ada_Lovelace"]


def test_desktop_mode_prints_url_and_exits_with_stdin(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    p = subprocess.Popen([sys.executable, "-u", "-m", "engramm.app", "--desktop", "--port", "0",
                          "--pack", str(tmp_path / "nopack")], cwd=root, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        first = p.stdout.readline().decode().strip()
        assert first.startswith("ENGRAMM_URL=http://127.0.0.1:")
        base = first.split("=", 1)[1]
        import time
        for _ in range(100):
            health = json.loads(_call(base, "/api/health")[2])
            if health["error"]:
                break
            time.sleep(0.1)
        assert "No knowledge pack" in health["error"]
        p.stdin.close()
        assert p.wait(timeout=20) == 0
    finally:
        if p.poll() is None:
            p.kill()


def test_source_view_atlas_kinds():
    shelf = source_view({"kind": "shelf", "source": "wikipedia", "key": "Ada Lovelace", "title": "Ada Lovelace",
                         "as_of": "2026-09-20"})
    assert shelf == {"kind": "shelf", "title": "Ada Lovelace", "as_of": "2026-09-20",
                     "url": "https://en.wikipedia.org/wiki/Ada_Lovelace"}
    feed = source_view({"kind": "feed", "source": "bbc-world", "key": "https://www.bbc.co.uk/news/x", "title": "Headline",
                        "as_of": "2026-10-01"})
    assert feed["kind"] == "feed" and feed["url"] == "https://www.bbc.co.uk/news/x" and feed["as_of"] == "2026-10-01"
    assert feed["site"] == "bbc-world"
    web = source_view({"kind": "web", "source": "www.siemens.com", "key": "http://www.siemens.com/", "title": "Siemens"})
    assert web["kind"] == "web" and web["url"] is None          # only https links are offered


def _atlas_service(tmp_path, monkeypatch):
    from engramm.web.atlas import Atlas
    from engramm.web.egress import Egress, NetworkLog, PythonBackend
    from engramm.web.feeds import FeedRefresher
    calls = []
    monkeypatch.setattr(FeedRefresher, "refresh_now", lambda self: calls.append("refresh") or {"fetched": 0})
    monkeypatch.setattr(FeedRefresher, "start", lambda self: calls.append("start"))
    monkeypatch.setattr(FeedRefresher, "stop", lambda self: calls.append("stop"))
    svc = ChatService("unused")
    svc.bot = _Bot()
    svc.assistant = _Assistant(svc.bot)
    svc.egress = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"),
                        backend=PythonBackend())
    svc.atlas = Atlas(svc.egress, None, tmp_path)
    return svc, calls


def test_network_api_is_off_by_default_and_switches_channels(tmp_path, monkeypatch):
    svc, calls = _atlas_service(tmp_path, monkeypatch)
    srv = serve(svc, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        code, _, body = _call(base, "/api/network")
        net = json.loads(body)
        assert code == 200 and net["available"] and net["backend"] == "python"
        assert not any(c["enabled"] for c in net["channels"].values())          # offline until switched on
        assert net["feeds"] and not any(f["selected"] for f in net["feeds"]) and net["log"] == []
        code, _, body = _call(base, "/api/network", {"channel": "feeds", "enabled": True})
        net = json.loads(body)
        assert code == 200 and net["channels"]["feeds"]["enabled"]
        assert net["channels"]["feeds"]["feeds"] == svc.atlas.default_feeds  # defaults picked when none chosen
        assert calls[:1] == ["start"]
        code, _, body = _call(base, "/api/network", {"channel": "feeds", "feeds": ["dw-en", "no-such-feed"]})
        assert json.loads(body)["channels"]["feeds"]["feeds"] == ["dw-en"]     # unknown ids are dropped
        assert _call(base, "/api/network", {"channel": "nope", "enabled": True})[0] == 400
        assert _call(base, "/api/network", {"channel": "shelf", "enabled": "yes"})[0] == 400
        assert _call(base, "/api/network", {"channel": "shelf", "colour": "red"})[0] == 400
        code, _, body = _call(base, "/api/network/refresh", {})
        assert code == 200 and "refresh" in calls
        _call(base, "/api/network", {"channel": "feeds", "enabled": False})
        assert calls[-1] == "stop"
        saved = json.loads((tmp_path / "network.json").read_text())
        assert saved["channels"]["feeds"] == {"enabled": False, "feeds": ["dw-en"]}
    finally:
        srv.shutdown()
        srv.server_close()


def test_network_api_without_atlas(running):
    base, _ = running
    assert json.loads(_call(base, "/api/network")[2]) == {"available": False}
    assert _call(base, "/api/network", {"channel": "feeds", "enabled": True})[0] == 503


def test_open_allows_links_shown_in_replies(monkeypatch):
    import engramm.app.server as server_mod
    opened = []
    monkeypatch.setattr(server_mod.webbrowser, "open", lambda url: opened.append(url))

    class _NewsAssistant(_Assistant):
        def turn(self, state, message):
            return _Reply("A headline.", source={"kind": "feed", "source": "bbc-world",
                                                 "key": "https://www.bbc.co.uk/news/world-1", "title": "A headline"})
    svc = ChatService("unused")
    svc.bot = _Bot()
    svc.assistant = _NewsAssistant(svc.bot)
    srv = serve(svc, port=0, desktop=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        url = "https://www.bbc.co.uk/news/world-1"
        assert _call(base, "/api/open", {"url": url})[0] == 400                  # not shown yet
        reply = json.loads(_call(base, "/api/chat", {"conversation": "c", "message": "news"})[2])
        assert reply["source"]["kind"] == "feed" and reply["source"]["url"] == url
        assert _call(base, "/api/open", {"url": url})[0] == 200
        assert _call(base, "/api/open", {"url": "https://www.bbc.co.uk/news/other"})[0] == 400
    finally:
        srv.shutdown()
        srv.server_close()
    assert opened == [url]
