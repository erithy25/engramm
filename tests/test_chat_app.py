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
    base, _ = running
    for path, ctype in (("/", "text/html"), ("/app.js", "text/javascript"), ("/app.css", "text/css"),
                        ("/logo.svg", "image/svg+xml"), ("/icons/icon-192.png", "image/png")):
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
    assert _call(base, "/api/chat", {"conversation": "a", "message": "x" * 2001})[0] == 400
    svc.bot = svc.assistant = None
    svc.error = None
    code, _, body = _call(base, "/api/chat", {"conversation": "a", "message": "hi"})
    assert code == 503 and "loading" in json.loads(body)["error"]


def test_source_view():
    assert source_view(None) is None
    assert source_view({"kind": "user", "source": "u1"})["title"] == "You told me"
    web = source_view({"kind": "base", "source": "c4", "key": "https://www.example.org/a/b"})
    assert web == {"kind": "web", "title": "www.example.org", "url": "https://www.example.org/a/b"}
