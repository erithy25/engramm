"""The one way out to the network (docs/SPEC_ATLAS.md, "Netz-Tor").

Every fetch names its channel; the channel must be switched on, the URL must be https and its
host must be allowed for that channel; redirects are followed only to allowed hosts; there are
no cookies, a fixed user agent and hard limits on size and time. Each fetch is written to the
network log (what was fetched, never why).

Backends:
* ``RustBackend`` — ``engramm-core egress`` (shipped with the desktop app; Python opens no
  sockets there; Tor through Arti when built with the ``tor`` feature);
* ``PythonBackend`` — urllib, for development and tests (same rules, no Tor).
"""

from __future__ import annotations

import base64
import datetime as dt
import ipaddress
import json
import os
import shutil
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

USER_AGENT = "ENGRAMM/3.1 (+offline assistant)"
CHANNELS = ("shelf", "feeds", "messenger")
DEFAULT_SETTINGS = {"version": 1, "channels": {"shelf": {"enabled": False, "tor": False},
                                               "feeds": {"enabled": False, "feeds": []},
                                               "messenger": {"enabled": False, "tor": True}}}
MAX_BYTES = {"shelf": 4 << 20, "feeds": 2 << 20, "messenger": 2 << 20}
TIMEOUT = {"shelf": 30.0, "feeds": 20.0, "messenger": 45.0}


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
    tor: bool = False
    allow_loopback: bool = False


def host_of(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def host_allowed(host: str, allow: tuple[str, ...]) -> bool:
    """Exact host or a subdomain of an allowed host ("objects.githubusercontent.com" under
    "githubusercontent.com"); "*" allows any public host (the messenger)."""
    if not host:
        return False
    for a in allow:
        a = a.lower().lstrip(".")
        if a == "*" or host == a or host.endswith("." + a):
            return True
    return False


def is_private_host(host: str) -> bool:
    """Loopback, private, link-local and reserved addresses, localhost and *.local / *.internal:
    the messenger never reaches into the home network."""
    h = host.strip("[]").lower()
    if h in ("localhost",) or h.endswith((".localhost", ".local", ".internal", ".lan", ".home", ".corp")):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified


def check(req: Request, settings: dict) -> None:
    """Raise EgressError unless the request is allowed by the channel rules."""
    if req.channel not in CHANNELS:
        raise EgressError(f"unknown channel: {req.channel}")
    ch = settings.get("channels", {}).get(req.channel, {})
    if not ch.get("enabled"):
        raise EgressError(f"channel {req.channel} is switched off")
    u = urllib.parse.urlsplit(req.url)
    host = (u.hostname or "").lower()
    loop = req.allow_loopback and host in ("127.0.0.1", "localhost", "::1")
    if u.scheme != "https" and not (loop and u.scheme == "http"):
        raise EgressError(f"only https is allowed: {req.url[:60]}")
    if u.username or u.password:
        raise EgressError("no credentials in URLs")
    if not loop and req.channel == "messenger" and is_private_host(host):
        raise EgressError(f"private address not allowed: {host}")
    if not loop and not host_allowed(host, req.allow_hosts):
        raise EgressError(f"host not allowed: {host}")


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
    """urllib with the egress rules (development and tests; no Tor)."""
    name = "python"

    def __init__(self):
        self.opener = urllib.request.build_opener(_NoRedirect())

    def fetch(self, req: Request, settings: dict) -> Fetched:
        if req.tor:
            return Fetched(False, error="tor unavailable")
        url = req.url
        limit = req.max_bytes or MAX_BYTES[req.channel]
        for hop in range(6):
            try:
                check(Request(req.channel, url, req.what, req.allow_hosts, req.range, req.max_bytes, req.tor,
                              req.allow_loopback), settings)
            except EgressError as e:
                if hop == 0:
                    raise
                return Fetched(False, error=f"redirect refused: {e}")
            headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
            if req.range is not None:
                headers["Range"] = f"bytes={req.range[0]}-{req.range[1]}"
            r = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with self.opener.open(r, timeout=TIMEOUT[req.channel]) as resp:
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

    def __init__(self, core: str, log_path: Path | None = None, tor_dir: Path | None = None):
        args = [core, "egress"] + (["--log", str(log_path)] if log_path else []) + \
            (["--tor-dir", str(tor_dir)] if tor_dir else [])
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
                   "tor": req.tor, "timeout": TIMEOUT[req.channel], "allow_loopback": req.allow_loopback}
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
        """A service operation: "status" (does this build have Tor?) or "tor_start"."""
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
    tor_dir: Path | None = None
    tor_backend: object = None                # a second service for Tor (its start may take a minute)
    tor_state: str = "off"                    # off | starting | ready | failed: <reason> | unavailable

    @classmethod
    def beside(cls, memory_path: Path | None, prefer_rust: bool = True) -> Egress:
        """network.json and network.log next to the memory log."""
        base = Path(memory_path).parent if memory_path else None
        e = cls(settings_path=base / "network.json" if base else None,
                log=NetworkLog(base / "network.log" if base else None))
        e.load()
        core = find_core() if prefer_rust else None
        e.core = core
        e.tor_dir = base / "tor" if base else None
        e.backend = RustBackend(core) if core else PythonBackend()
        if not core or not e.backend.op("status").get("tor"):
            e.tor_state = "unavailable"
        return e

    def warm_tor(self) -> None:
        """Start Tor in the background (when the messenger is switched on), so the first page
        does not wait for the bootstrap."""
        if self.tor_state in ("starting", "ready", "unavailable") or not self.core:
            return
        self.tor_state = "starting"

        def run():
            try:
                if self.tor_backend is None:
                    self.tor_backend = RustBackend(self.core, tor_dir=self.tor_dir)
                r = self.tor_backend.op("tor_start")
                self.tor_state = "ready" if r.get("ok") else f"failed: {r.get('error', '?')}"
            except Exception as ex:                # the chat goes on without the messenger
                self.tor_state = f"failed: {ex}"
        threading.Thread(target=run, daemon=True).start()

    def load(self) -> None:
        if self.settings_path is not None and self.settings_path.exists():
            try:
                d = json.loads(self.settings_path.read_text(encoding="utf-8"))
                merged = json.loads(json.dumps(DEFAULT_SETTINGS))
                for ch, conf in (d.get("channels") or {}).items():
                    if ch in merged["channels"] and isinstance(conf, dict):
                        merged["channels"][ch].update({k: v for k, v in conf.items()
                                                       if k in merged["channels"][ch]})
                self.settings = merged
            except (json.JSONDecodeError, OSError):
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
            if k in ("enabled", "tor") and not isinstance(v, bool):
                raise EgressError(f"{k} must be true or false")
            if k == "feeds" and not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                raise EgressError("feeds must be a list of feed ids")
            cur[k] = v
        self.save()
        return cur

    def fetch(self, req: Request) -> Fetched:
        try:
            if req.tor:
                if self.tor_backend is None and self.core and self.tor_state != "unavailable":
                    self.tor_backend = RustBackend(self.core, tor_dir=self.tor_dir)
                backend = self.tor_backend or self.backend
            else:
                backend = self.backend
            res = backend.fetch(req, self.settings) if backend else Fetched(False, error="no backend")
        except EgressError as e:
            self.log.write({"channel": req.channel, "host": host_of(req.url), "what": req.what, "bytes": 0,
                            "status": 0, "via": "-", "ok": False, "error": str(e)})
            raise
        self.log.write({"channel": req.channel, "host": res.final_host or host_of(req.url), "what": req.what,
                        "bytes": len(res.body), "status": res.status, "via": res.via, "ok": res.ok,
                        **({"error": res.error} if not res.ok else {})})
        return res

    def status(self) -> dict:
        return {"backend": getattr(self.backend, "name", None), "channels": self.settings["channels"],
                "tor": self.tor_state}
