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
* ``POST /api/chat``             {"conversation": str, "message": str, "model"?: "engramm"|"sela-1"|"sela-2",
                                    "max_tokens"?: int} → reply (model "sela-1": text continued by the local
                                    Sela-1 network, kind "generated", nothing checked against sources; model
                                    "sela-2": the chat model — a knowledge question is answered from ENGRAMM's
                                    sources with citations and checked (kind "sela_grounded"; on a failed check
                                    ENGRAMM's own answer, marked ``sela_checked: false``), memory commands stay with
                                    ENGRAMM, everything else is free conversation (kind "sela_chat", not checked))
* ``GET  /api/models``           → {"models": [{"id", "name", "available", "ready", "error"}], "last": id}
                                    ("last": the model of the latest chat request, kept beside the memory file so
                                    the desktop app, which gets a new port and page storage on every start, keeps it)
* ``GET  /api/memory``           → {"items": [{"source", "preview", "tokens"}]}
* ``POST /api/memory/forget``    {"source": str} → {"forgot": str}
* ``POST /api/open``             {"url": str} → {"opened": str}   (desktop app only: opens a source
                                    link in the system browser; Wikipedia and Wikidata links only)

Desktop mode (``--desktop``, used by the Tauri app): the first output line is
``ENGRAMM_URL=http://127.0.0.1:<port>`` (``--port 0`` picks a free port), ``/api/open`` is on, and
the server exits when its standard input closes, so it never outlives the app.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
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
SELA_ID = "sela-1"
SELA_FILE = "sela1-135m.npz"
SELA_TOKENS, SELA_MAX_TOKENS = 120, 200
SELA2_ID = "sela-2"
SELA2_FILE = "sela2-chat.npz"
SELA2_TOKENS, SELA2_MAX_TOKENS = 160, 400
# Sela-2 routing by ENGRAMM's reply kind: memory commands, safety replies, tools (calculator, translation), memory
# questions and clarifying questions stay ENGRAMM's; answers with sources are rewritten from those sources and
# checked; small talk, empathy, writing and open questions without any evidence go to Sela-2's free chat
ENGRAMM_ONLY = ("learned", "forgot", "known", "nothing", "safety", "tool", "memory", "clarify")
SELA2_GROUNDED = ("answer", "about", "explain")
SELA2_FREE = ("smalltalk", "empathy", "writing")
MODEL_IDS = ("engramm", SELA_ID, SELA2_ID)
OPEN_HOSTS = re.compile(r"^([a-z]{2,3}(-[a-z]+)?\.)?(m\.)?wikipedia\.org$|^www\.wikidata\.org$")


def find_model_file(name: str, env: str, repo_dir: str, explicit: Path | None = None,
                    data_dir: Path | None = None) -> Path | None:
    """A network's weights: explicit path or $env, then models/ next to the frozen server, the data folder's
    models/, the repository's models/lm/<repo_dir>/."""
    cands = [Path(explicit)] if explicit else []
    if os.environ.get(env):
        cands.append(Path(os.environ[env]))
    if getattr(sys, "frozen", False):
        cands.append(Path(sys.executable).resolve().parent / "models" / name)
    if data_dir:
        cands.append(Path(data_dir) / "models" / name)
    cands.append(Path(__file__).resolve().parents[2] / "models" / "lm" / repo_dir / name)
    return next((c for c in cands if c.is_file()), None)


def find_sela2(explicit: Path | None = None, data_dir: Path | None = None) -> Path | None:
    return find_model_file(SELA2_FILE, "ENGRAMM_SELA2", "sela2", explicit, data_dir)


def find_sela(explicit: Path | None = None, data_dir: Path | None = None) -> Path | None:
    """The Sela-1 weights (engramm/lm/sela.py): --sela or ENGRAMM_SELA, then models/ next to the frozen server (the
    desktop app ships it there), the app's data folder, and the repository (models/lm/sela1/)."""
    cands = [Path(explicit)] if explicit else []
    if os.environ.get("ENGRAMM_SELA"):
        cands.append(Path(os.environ["ENGRAMM_SELA"]))
    if getattr(sys, "frozen", False):
        cands.append(Path(sys.executable).resolve().parent / "models" / SELA_FILE)
    if data_dir is not None:
        cands.append(Path(data_dir) / "models" / SELA_FILE)
    cands.append(Path(__file__).resolve().parents[2] / "models" / "lm" / "sela1" / SELA_FILE)
    return next((c for c in cands if c.is_file()), None)


def sela_prompt(message: str) -> tuple[str, bool]:
    """A question becomes "Question: …\nAnswer:" (the answer ends at the first line break); anything else is a text
    for Sela-1 to continue."""
    m = message.strip()
    if m.endswith("?"):
        return f"Question: {m}\nAnswer:", True
    return m, False


def openable(url: str) -> bool:
    """Only https links to Wikipedia or Wikidata may be handed to the system browser."""
    try:
        u = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    return (u.scheme == "https" and u.username is None and u.password is None and u.port is None
            and bool(OPEN_HOSTS.match(u.hostname or "")) and len(url) <= 2000)


_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
           "December")


def reading_as_of(idx: Path) -> str | None:
    """The date of the pack's reading text ("DBpedia 2022.12 abstracts" → "December 2022"), or None."""
    try:
        info = json.loads((Path(idx) / "info.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    m = re.search(r"\b(19\d\d|20\d\d)[.-](0[1-9]|1[0-2])\b", str(info.get("reading", "")))
    return f"{_MONTHS[int(m.group(2)) - 1]} {m.group(1)}" if m else None


def source_view(src: dict | None) -> dict | None:
    """Where an answer comes from, in a form the page can show and link."""
    if not src:
        return None
    if src.get("kind") == "user":
        return {"kind": "user", "title": "You told me", "url": None}
    origin, key = src.get("source"), src.get("key") or ""
    if src.get("kind") == "shelf":                 # Atlas: a full Wikipedia article from the shelf
        title = src.get("title") or key
        return {"kind": "shelf", "title": title, "as_of": src.get("as_of") or None,
                "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))}
    if src.get("kind") in ("feed", "web"):         # Atlas: a news feed item or a page the messenger read
        url = key if key.startswith("https://") else None
        return {"kind": src["kind"], "title": src.get("title") or key, "site": origin, "url": url,
                "as_of": src.get("as_of") or None}
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
                 memory_path: Path | None = None, sela: Path | None = None, sela2: Path | None = None):
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
        self.egress = None
        self.atlas = None
        self.shown_urls: set[str] = set()          # links this server put into replies (may be opened)
        self.sela_path = find_sela(sela, self.memory_path.parent if self.memory_path else None)
        self.sela = None                           # loaded on the first Sela-1 request (about 540 MB of memory)
        self.sela_error: str | None = None
        self.sela_lock = threading.Lock()          # one generation at a time; never holds the bot's lock
        self.sela2_path = find_sela2(sela2, self.memory_path.parent if self.memory_path else None)
        self.sela2 = None                          # loaded on the first Sela-2 request (about 1.7 GB of memory)
        self.sela2_error: str | None = None
        self.sela2_error_path: Path | None = None
        self.sela2_lock = threading.Lock()
        self.sela2_states: dict = {}               # conversation → the turns Sela-2 saw (engramm.lm.sela_chat)
        self.settings_path = self.memory_path.parent / "app_settings.json" if self.memory_path else None
        self.last_model = self._read_settings().get("model", "engramm")
        if self.last_model not in MODEL_IDS:
            self.last_model = "engramm"

    def _read_settings(self) -> dict:
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8")) if self.settings_path else {}
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _remember_model(self, model: str) -> None:
        if model == self.last_model:
            return
        self.last_model = model
        if self.settings_path is None:
            return
        try:                                       # best effort: a read-only data folder must not break the chat
            data = self._read_settings()
            data["model"] = model
            tmp = self.settings_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.replace(self.settings_path)
        except OSError:
            traceback.print_exc()

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
            assistant.reading_as_of = reading_as_of(idx)
            try:                                     # local learning (engramm/learn): next to the chat memory
                from engramm.learn import Learner
                mem_file = getattr(memory, "path", None)
                assistant.learner = Learner(Path(mem_file).parent / "learn.json" if mem_file else None)
            except Exception:
                traceback.print_exc()
            try:                                     # Atlas: network channels, all off until switched on
                from engramm.web.atlas import Atlas
                from engramm.web.egress import Egress
                mem_file = getattr(memory, "path", None)
                self.egress = Egress.beside(Path(mem_file) if mem_file else None)
                self.atlas = Atlas(self.egress, self.pack, Path(mem_file).parent if mem_file else None)
                assistant.atlas = self.atlas
            except Exception:                        # the offline chat works without it
                traceback.print_exc()
                self.egress = self.atlas = None
            with self.lock:
                self.memory, self.bot, self.assistant = memory, bot, assistant
        except Exception as e:  # shown on the page instead of a silent hang
            self.error = f"{type(e).__name__}: {e}"
            traceback.print_exc()

    def learning(self) -> dict:
        """What ENGRAMM learned on this computer (engramm/learn): counts and the taught words, never anything sent."""
        lr = getattr(self.assistant, "learner", None) if self.assistant is not None else None
        if lr is None:
            return {"available": False}
        stt = lr.state
        kinds = [o["op"] for o in stt.ops]
        return {"available": True, "corrections": kinds.count("correct"), "words": sorted(w.split(":", 1)[1] for w in stt.words),
                "style": dict(stt.style), "episodes": len(stt.episodes), "signals": kinds.count("reward"),
                "file": str(stt.path) if stt.path else None}

    def reset_learning(self) -> dict:
        lr = getattr(self.assistant, "learner", None) if self.assistant is not None else None
        if lr is None:
            raise RuntimeError("Learning is not available.")
        with self.lock:
            lr.state.reset()
        return self.learning()

    def health(self) -> dict:
        return {"ready": self.assistant is not None, "error": self.error, "mode": self.mode,
                "sentences": None if self.bot is None else int(self.bot.c.index.n)}

    def models(self) -> dict:
        """The models the chat can use: ENGRAMM (answers with sources) and, when its weights ship with the app,
        Sela-1 (a small neural network that continues text)."""
        return {"models": [
            {"id": "engramm", "name": "ENGRAMM", "available": True, "ready": self.assistant is not None,
             "error": self.error},
            {"id": SELA_ID, "name": "Sela-1 135M", "available": self.sela_path is not None,
             "ready": self.sela is not None, "error": self.sela_error},
            {"id": SELA2_ID, "name": "Sela-2 Chat", "available": self.sela2_path is not None,
             "ready": self.sela2 is not None, "error": self.sela2_error}],
            "last": self.last_model if {SELA_ID: self.sela_path, SELA2_ID: self.sela2_path}.get(self.last_model, True)
            else "engramm"}

    # -- chat --------------------------------------------------------------------------------

    def chat(self, conversation: str, message: str, model: str = "engramm", max_tokens: int | None = None) -> dict:
        from engramm.chat.dialog import DialogState
        message = message.strip()
        if not message:
            raise ValueError("Empty message.")
        if len(message) > MAX_MESSAGE:
            raise ValueError(f"Message too long (at most {MAX_MESSAGE} characters).")
        if model not in MODEL_IDS:
            raise ValueError(f"Unknown model: {model}")
        self._remember_model(model)
        if model == SELA_ID:
            return self.generate(message, max_tokens)
        if model == SELA2_ID:
            return self.chat2(conversation, message, max_tokens)
        r = self._engramm_turn(conversation, message)
        r.pop("_raw", None)
        return r

    def _engramm_turn(self, conversation: str, message: str) -> dict:
        from engramm.chat.dialog import DialogState
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
        for src in [d.get("source")] + [a.get("source") for a in (d.get("alternatives") or [])]:
            if src and str(src.get("key", "")).startswith("https://"):
                self.shown_urls.add(src["key"])
        return {"kind": d["kind"], "text": d["text"], "answer": d["answer"], "guess": d["guess"],
                "evidence": d["evidence"], "source": source_view(d["source"]), "confidence": d["confidence"],
                "via": d["via"], "resolved": d["resolved"] if d["resolved"] != message else None,
                "alternatives": [{"text": a.get("text"), "source": source_view(a.get("source"))}
                                 for a in (d.get("alternatives") or [])][:3],
                "seconds": round(time.time() - t0, 3), "_raw": d,
                "_asks": bool(st.pending and st.pending.get("turn") == st.turn)}   # ENGRAMM asked something back

    def _sela_replaced(self, conversation: str, text: str) -> None:
        """ENGRAMM's reply was not shown: its offer ('Want a joke?') and its own last reply leave the dialog state."""
        with self.lock:
            st = self.states.get((conversation or "default")[:100])
            if st is not None:
                st.offer = None
                st.last_reply = text

    def _load_sela2(self):
        if self.sela2_path is None:
            raise RuntimeError("Sela-2 is not installed in this app.")
        if self.sela2 is None:
            if self.sela2_error and self.sela2_error_path == self.sela2_path:   # a failed load is not retried per
                raise RuntimeError(f"Sela-2 could not be loaded ({self.sela2_error}).")   # request (1.7 GB)
            try:
                from engramm.lm.sela_chat import SelaChat
                self.sela2 = SelaChat(self.sela2_path)
                self.sela2_error = None
            except Exception as e:
                self.sela2_error = f"{type(e).__name__}: {e}"
                self.sela2_error_path = self.sela2_path
                traceback.print_exc()
                raise RuntimeError(f"Sela-2 could not be loaded ({self.sela2_error}).") from e
        return self.sela2

    def chat2(self, conversation: str, message: str, max_tokens: int | None = None) -> dict:
        """Sela-2: ENGRAMM handles the turn first (memory, safety, tools, retrieval, dialog state). Its memory, safety,
        tool and clarifying replies are shown as they are; an answer with sources is rewritten by Sela-2 from those
        sources (cited, then checked by engramm.lm.sela_chat.verify; a failed check or an abstention keeps ENGRAMM's
        answer); small talk, empathy, writing and open questions without evidence get Sela-2's free reply, labelled
        as not checked. While ENGRAMM is still loading, Sela-2 does not answer (no memory, no safety layer yet)."""
        from engramm.lm.sela_chat import ChatState, Turn, sources_from_reply
        n = SELA2_TOKENS if max_tokens is None else int(max_tokens)
        if not 1 <= n <= SELA2_MAX_TOKENS:
            raise ValueError(f"max_tokens must be between 1 and {SELA2_MAX_TOKENS}.")
        if self.sela2_path is None:
            raise RuntimeError("Sela-2 is not installed in this app.")
        conv = (conversation or "default")[:100]
        base = self._engramm_turn(conv, message)            # raises "still loading" until ENGRAMM is ready
        raw = base.pop("_raw", None) or {}
        asks = base.pop("_asks", False)
        kind = base["kind"]
        free = kind in SELA2_FREE or (kind == "unknown" and not raw.get("evidence"))
        srcs = sources_from_reply(raw) if kind in SELA2_GROUNDED else []
        if kind in ENGRAMM_ONLY or asks or not (srcs or free):
            return {**base, "model": "engramm", "sela_checked": None}
        with self.sela2_lock:
            sela = self._load_sela2()
            t0 = time.time()
            st = self.sela2_states.pop(conv, None) or ChatState()
            try:
                if srcs:
                    question = base.get("resolved") or message
                    g = sela.grounded(question, srcs, max_tokens=min(n, 120))
                    if not g["verified"]:
                        return {**base, "model": "engramm", "sela_checked": False,
                                "sela_note": "abstained" if g["abstained"] else "; ".join(g["issues"][:3])}
                    st.turns.append(Turn(message, g["text"]))   # follow-ups ("tell me more") see the answer
                    del st.turns[:-8]
                    cited = [srcs[c - 1] for c in g["cited"]] or srcs[:1]
                    by_text = {raw.get("evidence"): raw.get("source")}
                    by_text.update({a.get("text"): a.get("source") for a in (raw.get("alternatives") or [])})
                    first = cited[0]
                    out = {"kind": "sela_grounded", "text": g["text"], "answer": None, "guess": None,
                           "evidence": first[1], "source": source_view(by_text.get(first[1])),
                           "confidence": float(base.get("confidence") or 0.0), "via": SELA2_ID,
                           "resolved": base.get("resolved"),
                           "alternatives": [{"text": t, "source": source_view(by_text.get(t))} for _, t in cited[1:3]],
                           "seconds": round(time.time() - t0 + base.get("seconds", 0), 3), "model": SELA2_ID,
                           "tokens": g["tokens"], "sela_checked": True}
                else:
                    r = sela.chat(st, message, max_tokens=n)
                    out = {"kind": "sela_chat", "text": r["text"], "answer": None, "guess": None, "evidence": None,
                           "source": None, "confidence": 0.0, "via": SELA2_ID, "resolved": None, "alternatives": [],
                           "seconds": round(r["seconds"] + base.get("seconds", 0), 3), "model": SELA2_ID,
                           "tokens": r["tokens"], "sela_checked": None}
            finally:
                self.sela2_states[conv] = st
                while len(self.sela2_states) > MAX_CONVERSATIONS:
                    self.sela2_states.pop(next(iter(self.sela2_states)))
        self._sela_replaced(conv, out["text"])
        return out

    def generate(self, message: str, max_tokens: int | None = None) -> dict:
        """Sela-1 continues the message (a question gets a one-line answer). Nothing is checked against sources,
        and the turn stays out of ENGRAMM's dialog state and memory."""
        if self.sela_path is None:
            raise RuntimeError("Sela-1 is not installed in this app.")
        n = SELA_TOKENS if max_tokens is None else int(max_tokens)
        if not 1 <= n <= SELA_MAX_TOKENS:
            raise ValueError(f"max_tokens must be between 1 and {SELA_MAX_TOKENS}.")
        prompt, question = sela_prompt(message)
        with self.sela_lock:
            if self.sela is None:
                try:
                    from engramm.lm.sela import SelaGenerator
                    self.sela = SelaGenerator(self.sela_path)
                    self.sela_error = None
                except Exception as e:
                    self.sela_error = f"{type(e).__name__}: {e}"
                    traceback.print_exc()
                    raise RuntimeError(f"Sela-1 could not be loaded ({self.sela_error}).") from e
            t0 = time.time()
            text, tokens, finished = self.sela.generate(prompt, n, stop_at_newline=question)
        body = text.strip()
        if not finished and not question and not body.endswith((".", "!", "?")):
            cut = max(body.rfind(". "), body.rfind("! "), body.rfind("? "), body.rfind(".\n"))
            if cut >= len(body) // 3:                # cut at the last full sentence, if there is a long enough one
                body = body[:cut + 1]
        if not body:
            body = "…"
        elif not question:                           # a continuation: show where the user's text left off
            body = "…" + (" " if text[:1].isspace() else "") + body
        return {"kind": "generated", "text": body, "answer": None, "guess": None, "evidence": None, "source": None,
                "confidence": 0.0, "via": SELA_ID, "resolved": None, "alternatives": [],
                "seconds": round(time.time() - t0, 3), "model": SELA_ID, "tokens": tokens}

    # -- network (Atlas) ---------------------------------------------------------------------

    def network(self) -> dict:
        if self.atlas is None:
            return {"available": False}
        return {"available": True, **self.atlas.status(), "log": self.egress.log.tail(100)[::-1]}

    def set_network(self, data: dict) -> dict:
        if self.atlas is None:
            raise RuntimeError("The network channels are not available.")
        channel = str(data.get("channel", ""))
        unknown = sorted(set(data) - {"channel", "enabled", "tor", "feeds"})
        if unknown:
            raise ValueError(f"Unknown setting: {unknown[0]}")
        conf = {k: data[k] for k in ("enabled", "tor", "feeds") if k in data}
        if not conf:
            raise ValueError("Nothing to change.")
        if "feeds" in conf:
            known = {f.id for f in self.atlas.feed_list}
            conf["feeds"] = [str(x) for x in conf["feeds"] if str(x) in known]
        from engramm.web.egress import EgressError
        try:
            with self.lock:
                self.egress.set_channel(channel, **conf)
        except EgressError as e:
            raise ValueError(str(e)) from e
        self.atlas.on_settings_changed()
        return self.network()

    def refresh_feeds(self) -> dict:
        if self.atlas is None:
            raise RuntimeError("The network channels are not available.")
        return {"result": self.atlas.refresher.refresh_now(), **self.network()}

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


def make_handler(service: ChatService, desktop: bool = False):
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
            if path == "/api/network":
                return self._json(200, service.network())
            if path == "/api/learning":
                return self._json(200, service.learning())
            if path == "/api/models":
                return self._json(200, service.models())
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
                if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                    # a JSON content type forces a CORS preflight, which this server never grants,
                    # so other websites open in a browser cannot post here
                    return self._json(415, {"error": "Expected application/json."})
                data = json.loads(self.rfile.read(n) or b"{}")
                if path == "/api/chat":
                    mt = data.get("max_tokens")
                    if mt is not None and (isinstance(mt, bool) or not isinstance(mt, int)):
                        raise ValueError("max_tokens must be a whole number.")
                    return self._json(200, service.chat(str(data.get("conversation", "")), str(data.get("message", "")),
                                                        str(data.get("model", "engramm")), mt))
                if path == "/api/memory/forget":
                    return self._json(200, service.forget(str(data.get("source", ""))))
                if path == "/api/network":
                    return self._json(200, service.set_network(data))
                if path == "/api/learning/reset":
                    return self._json(200, service.reset_learning())
                if path == "/api/network/refresh":
                    return self._json(200, service.refresh_feeds())
                if path == "/api/open" and desktop:
                    url = str(data.get("url", ""))
                    if not openable(url) and url not in service.shown_urls:
                        return self._json(400, {"error": "Only links ENGRAMM showed you can be opened."})
                    webbrowser.open(url)
                    return self._json(200, {"opened": url})
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


def serve(service: ChatService, host: str = "127.0.0.1", port: int = 8770,
          desktop: bool = False) -> ThreadingHTTPServer:
    return _Server((host, port), make_handler(service, desktop))


def _exit_with_parent(server: ThreadingHTTPServer) -> None:
    """Desktop mode: the app holds our standard input; when it closes (the app quit or
    crashed), stop serving so the server never outlives the app."""
    try:
        while sys.stdin.buffer.read(1024):
            pass
    except (OSError, ValueError):
        pass
    threading.Thread(target=server.shutdown, daemon=True).start()


def check_sela2(explicit: Path | None = None) -> int:
    """Self-test of a (frozen) server: the Sela-2 file next to it loads with its pinned tokenizer and answers."""
    from engramm.lm.sela_chat import ChatState, SelaChat
    path = find_sela2(explicit)
    out: dict = {"ok": False, "weights": str(path) if path else None}
    try:
        if path is None:
            raise FileNotFoundError(f"{SELA2_FILE} not found")
        t0 = time.time()
        sc = SelaChat(path)
        out["load_seconds"] = round(time.time() - t0, 1)
        r = sc.chat(ChatState(), "Hello! Who are you?", max_tokens=8, seed=0)
        out.update({"ok": r["tokens"] >= 1, "tokens": r["tokens"], "text": r["text"], "stop": r.get("stop"),
                    "reply_seconds": r["seconds"], "tokenizer_sha256": sc.tok.sha256, "vocab": sc.model.cfg.vocab})
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    print(json.dumps(out), flush=True)
    return 0 if out["ok"] else 1


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
    ap.add_argument("--sela", type=Path, default=None, help="Sela-1 weights file (default: found next to the app)")
    ap.add_argument("--sela2", type=Path, default=None, help="Sela-2 weights file (default: found next to the app)")
    ap.add_argument("--desktop", action="store_true",
                    help="desktop-app mode: print ENGRAMM_URL=…, allow /api/open, exit when stdin closes")
    ap.add_argument("--check-sela2", action="store_true",
                    help="load Sela-2 (weights + tokenizer, as the app does), write one short reply, print JSON, exit")
    args = ap.parse_args(argv)
    if args.check_sela2:
        return check_sela2(args.sela2)
    service = ChatService(args.model, args.index, pack=args.pack, memory_path=args.memory, sela=args.sela,
                          sela2=args.sela2)
    server = serve(service, host=args.host, port=args.port, desktop=args.desktop)
    threading.Thread(target=service.load, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    if args.desktop:
        print(f"ENGRAMM_URL={url}", flush=True)
        args.no_browser = True
        threading.Thread(target=_exit_with_parent, args=(server,), daemon=True).start()
    print(f"ENGRAMM is running: {url}  (loading in the background; stop with Ctrl+C)", flush=True)
    if os.environ.get("ENGRAMM_NO_BROWSER"):
        args.no_browser = True
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
