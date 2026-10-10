"""The one way out to the network (docs/SPEC_ATLAS.md, "Netz-Tor").

Every fetch names its channel; the channel must be switched on (a web search the user asked
for in so many words — "google …" — counts as switched on for that one search), the URL must be
https and its host must be allowed for that channel; redirects are followed only to allowed
hosts; there are no cookies, a fixed user agent (a browser's for the web search), only a few
harmless extra headers and hard limits on size and time. Each fetch is written to the network
log (what was fetched, never why).

Backends:
* ``RustBackend`` — ``engramm-core egress`` (shipped with the desktop app; Python opens no
  sockets there);
* ``PythonBackend`` — urllib, for development and tests (same rules).
"""

from __future__ import annotations

import base64
import datetime as dt
import ipaddress
import json
import os
import queue
import re
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

USER_AGENT = "ENGRAMM/3.1 (+offline assistant)"
# search engines and many sites refuse unknown clients; the same string as runtime/core/src/egress.rs
BROWSER_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/129.0.0.0 Safari/537.36")
CHANNELS = ("shelf", "feeds", "search")
SEARCH_ENGINES = ("auto", "bing", "duckduckgo", "brave")
# search.enabled: questions ENGRAMM cannot answer offline go to the web search on their own;
# "google …" always searches (the user asks for it). engine "auto" tries the keyless engines in
# turn; brave_key is an optional Brave Search API key (more reliable than reading result pages).
DEFAULT_SETTINGS = {"version": 2, "channels": {"shelf": {"enabled": False},
                                               "feeds": {"enabled": False, "feeds": []},
                                               "search": {"enabled": False, "engine": "auto", "brave_key": ""}}}
MAX_BYTES = {"shelf": 4 << 20, "feeds": 2 << 20, "search": 3 << 20}
TIMEOUT = {"shelf": 30.0, "feeds": 20.0, "search": 15.0}
HEADERS = ("accept", "accept-language", "x-subscription-token")
LOG_MAX_BYTES = 2 << 20
POOL = 4                                       # parallel fetches (result pages of one search)


class EgressError(Exception):
    pass


@dataclass
class Fetched:
    ok: bool
    status: int = 0
    body: bytes = b""
    error: str = ""
    via: str = "direct"
    final_host: str = ""
    content_type: str = ""


@dataclass
class Request:
    channel: str
    url: str
    what: str
    allow_hosts: tuple[str, ...] = ()
    range: tuple[int, int] | None = None
    max_bytes: int = 0
    allow_loopback: bool = False
    headers: tuple[tuple[str, str], ...] = ()
    explicit: bool = False                    # the user asked for this web search ("google …")
    timeout: float = 0.0                      # 0: the channel's limit


def host_of(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def host_allowed(host: str, allow: tuple[str, ...]) -> bool:
    """Exact host or a subdomain of an allowed host ("objects.githubusercontent.com" under
    "githubusercontent.com"); "*" allows any public host (the pages a web search lists)."""
    if not host:
        return False
    for a in allow:
        a = a.lower().lstrip(".")
        if a == "*" or host == a or host.endswith("." + a):
            return True
    return False


def is_private_host(host: str) -> bool:
    """Loopback, private, link-local and reserved addresses, localhost and *.local / *.internal:
    the web search never reaches into the home network."""
    h = host.strip("[]").lower()
    if h in ("localhost",) or h.endswith((".localhost", ".local", ".internal", ".lan", ".home", ".corp")):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified


_URL_IN_TEXT = re.compile(r"\b(?:https?|wss?)://[^\s\"'<>]+", re.I)


def scrub(text: str) -> str:
    """An error text without addresses: a URL becomes its host (a search URL holds the question,
    and neither the network log nor a reply may show it)."""
    return _URL_IN_TEXT.sub(lambda m: host_of(m.group(0)) or "a web address", text or "")[:200]


def check(req: Request, settings: dict) -> None:
    """Raise EgressError unless the request is allowed by the channel rules."""
    if req.channel not in CHANNELS:
        raise EgressError(f"unknown channel: {req.channel}")
    ch = settings.get("channels", {}).get(req.channel, {})
    if not ch.get("enabled") and not (req.explicit and req.channel == "search"):
        raise EgressError(f"channel {req.channel} is switched off")
    u = urllib.parse.urlsplit(req.url)
    host = (u.hostname or "").lower()
    loop = req.allow_loopback and host in ("127.0.0.1", "localhost", "::1")
    if u.scheme != "https" and not (loop and u.scheme == "http"):
        raise EgressError(f"only https is allowed: {req.url[:60]}")
    if u.username or u.password:
        raise EgressError("no credentials in URLs")
    if not loop and req.channel == "search" and is_private_host(host):
        raise EgressError(f"private address not allowed: {host}")
    if not loop and not host_allowed(host, req.allow_hosts):
        raise EgressError(f"host not allowed: {host}")
    for name, value in req.headers:
        if name.lower() not in HEADERS:
            raise EgressError(f"header not allowed: {name}")
        if len(value) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise EgressError(f"bad value for header {name}")


class NetworkLog:
    """network.log: one JSON line per fetch (what was fetched, never the question)."""

    def __init__(self, path: Path | None):
        self.path = Path(path) if path else None
        self.lock = threading.Lock()
        self.recent: list[dict] = []

    def write(self, entry: dict) -> None:
        entry = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **entry}
        with self.lock:
            self.recent = (self.recent + [entry])[-500:]
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                self._trim()

    def _trim(self, limit: int = LOG_MAX_BYTES) -> None:
        """Keep network.log bounded: past ``limit`` bytes, the newest half of the lines stays."""
        try:
            if self.path.stat().st_size <= limit:
                return
            lines = self.path.read_text(encoding="utf-8").splitlines()
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text("\n".join(lines[len(lines) // 2:]) + "\n", encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            pass

    def tail(self, n: int = 100) -> list[dict]:
        if self.path is not None and self.path.exists():
            lines = self.path.read_text(encoding="utf-8").splitlines()[-n:]
            out = []
            for line in lines:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return out
        return self.recent[-n:]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PythonBackend:
    """urllib with the egress rules (development and tests)."""
    name = "python"

    def __init__(self):
        self.opener = urllib.request.build_opener(_NoRedirect())

    def fetch(self, req: Request, settings: dict) -> Fetched:
        url = req.url
        limit = req.max_bytes or MAX_BYTES[req.channel]
        for hop in range(6):
            try:
                check(Request(req.channel, url, req.what, req.allow_hosts, req.range, req.max_bytes,
                              req.allow_loopback, req.headers, req.explicit), settings)
            except EgressError as e:
                if hop == 0:
                    raise
                return Fetched(False, error=f"redirect refused: {e}")
            headers = {**dict(req.headers), "Accept-Encoding": "identity",
                       "User-Agent": BROWSER_USER_AGENT if req.channel == "search" else USER_AGENT}
            if req.range is not None:
                headers["Range"] = f"bytes={req.range[0]}-{req.range[1]}"
            r = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with self.opener.open(r, timeout=req.timeout or TIMEOUT[req.channel]) as resp:
                    body = resp.read(limit + 1)
                    if len(body) > limit:
                        return Fetched(False, resp.status, error=f"response larger than {limit} bytes")
                    return Fetched(True, resp.status, body, final_host=host_of(url),
                                   content_type=resp.headers.get("Content-Type", ""))
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                    url = urllib.parse.urljoin(url, e.headers["Location"])
                    continue
                return Fetched(False, e.code, error=f"HTTP {e.code}")
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                return Fetched(False, error=str(getattr(e, "reason", e))[:200])
        return Fetched(False, error="too many redirects")


def find_core() -> str | None:
    """The engramm-core binary: $ENGRAMM_CORE, next to the frozen server, or on PATH."""
    env = os.environ.get("ENGRAMM_CORE")
    if env and Path(env).exists():
        return env
    import sys
    exe = "engramm-core.exe" if os.name == "nt" else "engramm-core"
    for base in (Path(getattr(sys, "_MEIPASS", "")), Path(sys.executable).resolve().parent):
        cand = base / exe
        if str(base) and cand.exists():
            return str(cand)
    return shutil.which("engramm-core")


class RustBackend:
    """``engramm-core egress``: one JSON line per request over stdin/stdout."""
    name = "rust"

    def __init__(self, core: str, log_path: Path | None = None):
        self.core = core
        args = [core, "egress"] + (["--log", str(log_path)] if log_path else [])
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True, encoding="utf-8", bufsize=1)
        self.lock = threading.Lock()
        self.n = 0

    def fetch(self, req: Request, settings: dict) -> Fetched:
        check(req, settings)                       # the same rules here, before anything leaves
        with self.lock:
            self.n += 1
            msg = {"id": self.n, "channel": req.channel, "url": req.url, "what": req.what,
                   "allow_hosts": list(req.allow_hosts), "max_bytes": req.max_bytes or MAX_BYTES[req.channel],
                   "timeout": req.timeout or TIMEOUT[req.channel], "allow_loopback": req.allow_loopback,
                   "headers": [list(h) for h in req.headers]}
            if req.range is not None:
                msg["range"] = list(req.range)
            try:
                self.proc.stdin.write(json.dumps(msg) + "\n")
                self.proc.stdin.flush()
                line = self.proc.stdout.readline()
            except (BrokenPipeError, OSError) as e:
                return Fetched(False, error=f"egress service stopped: {e}")
        if not line:
            return Fetched(False, error="egress service stopped")
        d = json.loads(line)
        if not d.get("ok"):
            return Fetched(False, d.get("status", 0), error=d.get("error", "failed"), via=d.get("via", "direct"))
        return Fetched(True, d.get("status", 200), base64.b64decode(d.get("body_b64", "")), via=d.get("via", "direct"),
                       final_host=d.get("final_host", ""), content_type=d.get("content_type", ""))

    def op(self, name: str) -> dict:
        """A service operation ("status": the service runs)."""
        with self.lock:
            self.n += 1
            try:
                self.proc.stdin.write(json.dumps({"op": name, "id": self.n}) + "\n")
                self.proc.stdin.flush()
                line = self.proc.stdout.readline()
            except (BrokenPipeError, OSError) as e:
                return {"ok": False, "error": str(e)}
        return json.loads(line) if line else {"ok": False, "error": "egress service stopped"}

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


@dataclass
class Egress:
    """Settings + backend + log. ``fetch`` never raises for network problems: it returns a
    ``Fetched`` with ok=False (and logs it); rule violations raise EgressError."""
    settings_path: Path | None = None
    log: NetworkLog = field(default_factory=lambda: NetworkLog(None))
    backend: object = None
    settings: dict = field(default_factory=lambda: json.loads(json.dumps(DEFAULT_SETTINGS)))
    core: str | None = None                   # engramm-core, when shipped
    _pool: queue.Queue = field(default_factory=queue.Queue, repr=False)
    _made: int = 0
    _pool_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def beside(cls, memory_path: Path | None, prefer_rust: bool = True) -> Egress:
        """network.json and network.log next to the memory log."""
        base = Path(memory_path).parent if memory_path else None
        e = cls(settings_path=base / "network.json" if base else None,
                log=NetworkLog(base / "network.log" if base else None))
        e.load()
        core = find_core() if prefer_rust else None
        e.core = core
        e.backend = RustBackend(core) if core else PythonBackend()
        return e

    def load(self) -> None:
        """network.json. Settings of earlier versions carry over where they still exist; the Tor
        messenger of 3.1 is gone and is not carried over to the web search, which sends the question
        itself to a search engine: that needs its own switch."""
        if self.settings_path is not None and self.settings_path.exists():
            try:
                d = json.loads(self.settings_path.read_text(encoding="utf-8"))
                merged = json.loads(json.dumps(DEFAULT_SETTINGS))
                for ch, conf in (d.get("channels") or {}).items():
                    if ch in merged["channels"] and isinstance(conf, dict):
                        cur = merged["channels"][ch]
                        cur.update({k: v for k, v in conf.items() if k in cur and isinstance(v, type(cur[k]))})
                if merged["channels"]["search"]["engine"] not in SEARCH_ENGINES:
                    merged["channels"]["search"]["engine"] = "auto"
                self.settings = merged
            except (json.JSONDecodeError, OSError, AttributeError):
                pass

    def save(self) -> None:
        if self.settings_path is not None:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.settings_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.settings, indent=1), encoding="utf-8")
            tmp.replace(self.settings_path)

    def enabled(self, channel: str) -> bool:
        return bool(self.settings["channels"].get(channel, {}).get("enabled"))

    def set_channel(self, channel: str, **conf) -> dict:
        if channel not in CHANNELS:
            raise EgressError(f"unknown channel: {channel}")
        cur = self.settings["channels"][channel]
        for k, v in conf.items():
            if k not in cur:
                raise EgressError(f"unknown setting for {channel}: {k}")
            if k == "enabled" and not isinstance(v, bool):
                raise EgressError(f"{k} must be true or false")
            if k == "feeds" and not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                raise EgressError("feeds must be a list of feed ids")
            if k == "engine" and v not in SEARCH_ENGINES:
                raise EgressError(f"engine must be one of {', '.join(SEARCH_ENGINES)}")
            if k == "brave_key":
                if not isinstance(v, str):
                    raise EgressError("brave_key must be text")
                v = v.strip()
                if len(v) > 200 or any(not (33 <= ord(c) < 127) for c in v):
                    raise EgressError("brave_key is not a valid API key")
            cur[k] = v
        self.save()
        return cur

    def fetch(self, req: Request) -> Fetched:
        return self._fetch(req, self.backend)

    def _fetch(self, req: Request, backend) -> Fetched:
        try:
            res = backend.fetch(req, self.settings) if backend else Fetched(False, error="no backend")
            res.error = scrub(res.error)
        except EgressError as e:
            self.log.write({"channel": req.channel, "host": host_of(req.url), "what": req.what, "bytes": 0,
                            "status": 0, "via": "-", "ok": False, "error": str(e)})
            raise
        self.log.write({"channel": req.channel, "host": res.final_host or host_of(req.url), "what": req.what,
                        "bytes": len(res.body), "status": res.status, "via": res.via, "ok": res.ok,
                        **({"error": res.error} if not res.ok else {})})
        return res

    def fetch_many(self, reqs: list[Request]) -> list[Fetched | None]:
        """Several fetches at once (the result pages of one search), in the order given; a request
        the rules refuse gives None. The shipped service answers one request at a time, so each
        parallel fetch takes its own service process (at most ``POOL``, started on first use)."""
        if not reqs:
            return []

        def one(req: Request) -> Fetched | None:
            backend = self._acquire()
            try:
                return self._fetch(req, backend)
            except EgressError:
                return None
            finally:
                self._release(backend)

        with ThreadPoolExecutor(max_workers=min(POOL, len(reqs))) as ex:
            return list(ex.map(one, reqs))

    def _acquire(self):
        if not isinstance(self.backend, RustBackend):
            return self.backend                   # urllib (and test doubles) serve threads directly
        try:
            return self._pool.get_nowait()
        except queue.Empty:
            pass
        core = self.core or getattr(self.backend, "core", None)
        with self._pool_lock:
            if self._made < POOL and core:
                self._made += 1
                try:
                    return RustBackend(core)
                except OSError:
                    self._made -= 1
            if self._made == 0:
                return self.backend               # one service only: its lock makes the fetches take turns
        return self._pool.get(timeout=300)

    def _release(self, backend) -> None:
        if isinstance(self.backend, RustBackend) and backend is not self.backend:
            self._pool.put(backend)

    def close(self) -> None:
        """Stop the service processes (the parallel ones too)."""
        for b in [self.backend] + [self._pool.get_nowait() for _ in range(self._pool.qsize())]:
            if isinstance(b, RustBackend):
                b.close()

    def public_settings(self) -> dict:
        """The channel settings for the page: the API key itself never goes back out."""
        chans = json.loads(json.dumps(self.settings["channels"]))
        key = chans["search"].pop("brave_key", "")
        chans["search"]["brave_key_set"] = bool(key)
        return chans

    def status(self) -> dict:
        return {"backend": getattr(self.backend, "name", None), "channels": self.public_settings()}
