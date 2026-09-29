"""ENGRAMM Chat — the chat application server (website and desktop app).

    python -m engramm.app                    # starts the server and opens http://127.0.0.1:8770
    python -m engramm.app --port 9000 --no-browser

The server answers at once; the sentence index loads in the background (well under a minute),
and the page shows a loading screen until ``/api/health`` reports ready.

Only this machine can connect (127.0.0.1). Every conversation keeps its own dialog state (what
"he", "it" or "that city" refer to, what ENGRAMM just asked, which replies it used); what you
teach ENGRAMM is one shared memory. The chat does not load the language model: its memory is
``chat_memory.log`` next to the model (engramm/chat/textmem.py), which on first start takes over
everything you told the earlier app (``user.log``).

API (JSON):

* ``GET  /api/health``           → {"ready": bool, "error": str|None, "mode": "full"|"quick"|None,
                                    "sentences": int|None}
* ``POST /api/chat``             {"conversation": str, "message": str} → reply
* ``GET  /api/memory``           → {"items": [{"source", "preview", "tokens"}]}
* ``POST /api/memory/forget``    {"source": str} → {"forgot": str}
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import time
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parent / "web"
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/javascript", ".js")
DEFAULT_MODEL = Path(__file__).resolve().parents[2] / "models" / "lm" / "main" / "model"
MAX_MESSAGE = 12000
MAX_CONVERSATIONS = 500


def source_view(src: dict | None) -> dict | None:
    """Where an answer comes from, in a form the page can show and link."""
    if not src:
        return None
    if src.get("kind") == "user":
        return {"kind": "user", "title": "You told me", "url": None}
    origin, key = src.get("source"), src.get("key") or ""
    if src.get("kind") == "kb":
        return {"kind": "wikipedia", "title": key + " (infobox)",
                "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(key.replace(" ", "_"))}
    if origin in ("wiki", "wikipedia"):
        return {"kind": "wikipedia", "title": key,
                "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(key.replace(" ", "_"))}
    if origin == "c4":
        url = key if key.startswith("http") else None
        return {"kind": "web", "title": urllib.parse.urlparse(key).netloc or key, "url": url}
    return {"kind": origin or "text", "title": key, "url": None}


class ChatService:
    """The core bot, the conversation layer and one dialog state per conversation. One request
    at a time touches the bot (it is not thread-safe); the lock also orders learn / forget."""

    def __init__(self, model_dir: Path, index: str | None = None, pack: Path | None = None,
                 memory_path: Path | None = None):
        self.model_dir = Path(model_dir)
        self.index = index
        self.pack = Path(pack) if pack else None
        self.memory_path = Path(memory_path) if memory_path else None
        self.mode: str | None = None
        self.lock = threading.Lock()
        self.bot = None
        self.assistant = None
        self.memory = None
        self.error: str | None = None
        self.states: dict = {}

    # -- loading -----------------------------------------------------------------------------

    def load(self) -> None:
        try:
            from engramm.chat.bot import ChatBot
            from engramm.chat.config import QUICK_INDEX, config_for
            from engramm.chat.corpus import Corpus
            from engramm.chat.dialog import Assistant
            from engramm.chat.retrieve import Retriever
            from engramm.chat.textmem import LoggedTextMemory
            from engramm.lm.dashboard import cap_ratio, chat_index_dir
            if self.pack is not None:
                if not (self.pack / "manifest.json").exists():
                    raise FileNotFoundError(f"No knowledge pack at {self.pack}.")
                idx = self.pack
                config, self.mode = config_for(idx)
                corpus = Corpus.from_pack(idx)
                mem_path = self.memory_path or (self.pack.parent / "chat_memory.log")
                memory = LoggedTextMemory(mem_path)
            else:
                if not (self.model_dir / "meta.json").exists():
                    raise FileNotFoundError(f"No model at {self.model_dir}.")
                idx = chat_index_dir(self.model_dir, self.index)
                if idx is None:
                    raise FileNotFoundError("No sentence index next to the model. Build it first: "
                                            "bash scripts/setup_mac.sh")
                config, self.mode = config_for(idx)
                if self.mode == "quick" and idx.name != QUICK_INDEX and \
                        (idx.parent / QUICK_INDEX / "info.json").exists():
                    idx = idx.parent / QUICK_INDEX     # a full index without its models: use the quick one
                    config, self.mode = config_for(idx)
                corpus = Corpus.load(self.model_dir, index_name=idx.name)
                memory = LoggedTextMemory(self.memory_path or (self.model_dir.parent / "chat_memory.log"),
                                          import_from=self.model_dir / "user.log")
            bot = ChatBot(memory, corpus, config, cap_ratio(idx), retriever=Retriever(corpus))
            kb = idx / "kb.sqlite" if (idx / "kb.sqlite").exists() else None
            assistant = Assistant(bot, kb_path=kb)
            with self.lock:
                self.memory, self.bot, self.assistant = memory, bot, assistant
        except Exception as e:  # shown on the page instead of a silent hang
            self.error = f"{type(e).__name__}: {e}"
            traceback.print_exc()

    def health(self) -> dict:
        return {"ready": self.assistant is not None, "error": self.error, "mode": self.mode,
                "sentences": None if self.bot is None else int(self.bot.c.index.n)}

    # -- chat --------------------------------------------------------------------------------

    def chat(self, conversation: str, message: str) -> dict:
        from engramm.chat.dialog import DialogState
        message = message.strip()
        if not message:
            raise ValueError("Empty message.")
        if len(message) > MAX_MESSAGE:
            raise ValueError(f"Message too long (at most {MAX_MESSAGE} characters).")
        if self.assistant is None:
            raise RuntimeError(self.error or "ENGRAMM is still loading.")
        conversation = (conversation or "default")[:100]
        with self.lock:
            st = self.states.pop(conversation, None) or DialogState(conversation=conversation)
            t0 = time.time()
            r = self.assistant.turn(st, message)
            self.states[conversation] = st              # most recently used last
            while len(self.states) > MAX_CONVERSATIONS:
                self.states.pop(next(iter(self.states)))
        d = r.to_dict()
        return {"kind": d["kind"], "text": d["text"], "answer": d["answer"], "guess": d["guess"],
                "evidence": d["evidence"], "source": source_view(d["source"]), "confidence": d["confidence"],
                "via": d["via"], "resolved": d["resolved"] if d["resolved"] != message else None,
                "alternatives": [{"text": a.get("text"), "source": source_view(a.get("source"))}
                                 for a in (d.get("alternatives") or [])][:3],
                "seconds": round(time.time() - t0, 3)}

    # -- memory ------------------------------------------------------------------------------

    def memory_items(self) -> dict:
        if self.bot is None:
            return {"items": []}
        with self.lock:
            texts = self.bot.user_texts()
            tok = self.bot.c.tok
            return {"items": [{"source": s, "preview": t[:200], "tokens": int(len(tok.encode(t)))}
                              for s, t in texts.items()]}

    def forget(self, source: str) -> dict:
        if self.bot is None:
            raise RuntimeError("ENGRAMM is still loading.")
        with self.lock:
            if source not in self.bot.user_texts():
                raise KeyError("Unknown entry.")
            self.bot.memory.forget(source)
            self.bot.refresh()
            for st in self.states.values():
                if st.ctx.get("last_learned") == source:
                    st.ctx["last_learned"] = None
        return {"forgot": source}


def make_handler(service: ChatService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ENGRAMM"

        def log_message(self, fmt, *args):
            pass

        def _send(self, code: int, body: bytes, ctype: str, cache: bool = False) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "max-age=3600" if cache else "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/health":
                return self._json(200, service.health())
            if path == "/api/memory":
                return self._json(200, service.memory_items())
            name = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
            f = (WEB / name).resolve()
            if WEB.resolve() not in f.parents or not f.is_file():
                return self._json(404, {"error": "not found"})
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "image/svg+xml"):
                ctype += "; charset=utf-8"
            self._send(200, f.read_bytes(), ctype, cache=f.suffix in (".png", ".svg") or "assets" in f.parts)

        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if n > 64_000:
                    return self._json(413, {"error": "Request too large."})
                data = json.loads(self.rfile.read(n) or b"{}")
                if path == "/api/chat":
                    return self._json(200, service.chat(str(data.get("conversation", "")), str(data.get("message", ""))))
                if path == "/api/memory/forget":
                    return self._json(200, service.forget(str(data.get("source", ""))))
                return self._json(404, {"error": "not found"})
            except (ValueError, KeyError) as e:
                return self._json(400, {"error": str(e).strip("'")})
            except RuntimeError as e:
                return self._json(503, {"error": str(e)})
            except Exception as e:  # never leak a traceback to the page
                traceback.print_exc()
                return self._json(500, {"error": f"Internal error: {type(e).__name__}"})

    return Handler


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # a browser that closes the connection early is not an error worth a traceback
        import sys
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


def serve(service: ChatService, host: str = "127.0.0.1", port: int = 8770) -> ThreadingHTTPServer:
    return _Server((host, port), make_handler(service))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m engramm.app", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser window (desktop app)")
    ap.add_argument("--index", default=None, help="sentence index to use (default: chat4m, chat4, else chat2)")
    ap.add_argument("--pack", type=Path, default=None, help="run on a knowledge pack folder (desktop app)")
    ap.add_argument("--memory", type=Path, default=None, help="where to keep what you tell ENGRAMM")
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)
    service = ChatService(args.model, args.index, pack=args.pack, memory_path=args.memory)
    server = serve(service, host=args.host, port=args.port)
    threading.Thread(target=service.load, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"ENGRAMM is running: {url}  (loading in the background; stop with Ctrl+C)", flush=True)
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if service.memory is not None:
            service.memory.close()
    return 0
