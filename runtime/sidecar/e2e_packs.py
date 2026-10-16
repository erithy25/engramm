"""End-to-end test of the frozen server on real knowledge packs, as the desktop app runs it.

    python runtime/sidecar/e2e_packs.py download --catalog CATALOG --core ENGRAMM_CORE --dest DIR
    python runtime/sidecar/e2e_packs.py chat --server ENGRAMM_SERVER --packs DIR --data DIR

``download`` fetches every pack of the app's catalog with the app's own download code
(``engramm-core fetch``: pinned manifest, SHA-256 of every file). ``chat`` starts the frozen server
on lite, then standard, then lite again with one memory file (a pack switch in the app), waits
until the pack is loaded, asks questions with known answers in English and German, and checks
that what was told on one pack is remembered on the other. The first start uses the environment
of the desktop app before UTF-8 mode was set (Windows then reads text in the ANSI code page);
the frozen server has to load the pack anyway. Exit code 0 only when everything passed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

LOAD_TIMEOUT = 600          # seconds: the first start compiles the search loops (numba)
# (conversation, question, words that must all be in the answer (case-insensitive), first start only)
QUESTIONS = [
    ("q1", "What is the capital of Australia?", ["canberra"], False),
    ("q2", "Who invented the telephone?", ["bell"], False),
    ("q3", "Wer hat das Telefon erfunden?", ["bell", "erfunden"], False),
    ("q4", "Was ist die Hauptstadt von Österreich?", ["wien"], False),
    ("q5", "How do I fix a flat bike tire?", ["wikibooks"], False),     # engramm/know/data in the bundle
    # engramm/understand in the bundle; only on the first start, because with the same memory the
    # second report of the same trouble gets the general advice (noted, not a pack matter)
    ("q6", "My washing machine is leaking. What should I do?", ["washing machine"], True),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def download(args: argparse.Namespace) -> int:
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    packs = catalog.get("packs") or []
    assert {p["name"] for p in packs} >= {"lite", "standard"}, f"catalog without lite and standard: {catalog}"
    for p in packs:
        dest = Path(args.dest) / f"{p['name']}-{p['version']}"
        t0 = time.time()
        log(f"fetching {p['name']} {p['version']} ({p['bytes'] / 1e9:.2f} GB) from {p['base_url']}")
        r = subprocess.run([args.core, "fetch", p["base_url"], p["manifest_sha256"], str(dest)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            log(r.stdout[-2000:] + r.stderr[-4000:])
            return 1
        v = subprocess.run([args.core, "verify", str(dest)], capture_output=True, text=True, encoding="utf-8")
        if v.returncode != 0:
            log(v.stdout[-2000:] + v.stderr[-2000:])
            return 1
        log(f"  complete and checked in {time.time() - t0:.0f} s")
    return 0


class Server:
    """The frozen server started like the desktop app starts it (runtime/app/src-tauri/src/lib.rs)."""

    def __init__(self, exe: str, pack: Path, data: Path, utf8_env: bool):
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
        env.update({"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "ENGRAMM_NO_BROWSER": "1",
                    "NUMBA_CACHE_DIR": str(data / "numba")})
        if utf8_env:
            env["PYTHONUTF8"] = "1"
        (data / "numba").mkdir(parents=True, exist_ok=True)
        self.p = subprocess.Popen([exe, "--desktop", "--port", "0", "--pack", str(pack),
                                   "--memory", str(data / "chat_memory.log")],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  cwd=str(Path(exe).parent), env=env)
        self.err: list[str] = []
        threading.Thread(target=self._drain, daemon=True).start()
        first = self.p.stdout.readline().decode("utf-8", "replace").strip()
        assert first.startswith("ENGRAMM_URL=http://127.0.0.1:"), (first, self.stderr())
        self.base = first.split("=", 1)[1]
        threading.Thread(target=self.p.stdout.read, daemon=True).start()

    def _drain(self) -> None:
        for line in self.p.stderr:
            self.err.append(line.decode("utf-8", "replace").rstrip())

    def stderr(self) -> str:
        return "\n".join(self.err[-40:])

    def get(self, path: str) -> dict:
        with urllib.request.urlopen(self.base + path, timeout=60) as r:
            return json.loads(r.read())

    def ask(self, conversation: str, message: str) -> dict:
        req = urllib.request.Request(self.base + "/api/chat", method="POST",
                                     data=json.dumps({"conversation": conversation, "message": message}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

    def wait_ready(self) -> dict:
        t0 = time.time()
        while time.time() - t0 < LOAD_TIMEOUT:
            h = self.get("/api/health")
            if h.get("error"):
                raise AssertionError(f"loading failed: {h['error']}\n{self.stderr()}")
            if h.get("ready"):
                h["load_seconds"] = round(time.time() - t0, 1)
                return h
            time.sleep(1)
        raise AssertionError(f"not ready after {LOAD_TIMEOUT} s\n{self.stderr()}")

    def stop(self) -> int:
        self.p.stdin.close()                       # the app closes the server's input to stop it
        return self.p.wait(timeout=60)


def chat(args: argparse.Namespace) -> int:
    packs = {p.name.split("-", 1)[0]: p for p in Path(args.packs).iterdir() if (p / "manifest.json").is_file()}
    assert {"lite", "standard"} <= set(packs), f"packs found: {sorted(packs)}"
    data = Path(args.data)
    data.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    sentences: dict[str, int] = {}
    runs = [("lite", False), ("standard", True), ("lite", True)]
    for i, (name, utf8_env) in enumerate(runs):
        log(f"--- {name} (PYTHONUTF8 {'set' if utf8_env else 'not set'})")
        s = Server(args.server, packs[name], data, utf8_env)
        try:
            h = s.wait_ready()
            log(f"ready in {h['load_seconds']} s: {h['sentences']:,} sentences, pack {h.get('pack')}")
            if (h.get("pack") or {}).get("name") != name:
                failures.append(f"{name}: health names the pack {h.get('pack')}")
            sentences[name] = h["sentences"]
            for conv, q, words, first_only in QUESTIONS:
                if first_only and i > 0:
                    continue
                r = s.ask(f"{name}{i}-{conv}", q)
                text = r.get("text", "")
                ok = all(w in text.lower() for w in words)
                log(f"{'ok ' if ok else 'BAD'} {q!r} -> {text[:140]!r}")
                if not ok:
                    failures.append(f"{name}: {q!r} -> {text[:200]!r} (expected {words})")
            if i == 0:
                r = s.ask("memory-1", "My sister is called Lena.")
                log(f"told: {r.get('text', '')[:100]!r}")
            else:                                  # another start, maybe another pack: the same memory
                r = s.ask(f"memory-{i + 1}", "What is my sister's name?")
                ok = "lena" in r.get("text", "").lower()
                log(f"{'ok ' if ok else 'BAD'} remembered across the switch: {r.get('text', '')[:100]!r}")
                if not ok:
                    failures.append(f"{name}: memory lost after the pack switch: {r.get('text')!r}")
            items = s.get("/api/memory").get("items", [])
            if not any("Lena" in it.get("preview", "") for it in items):
                failures.append(f"{name}: memory list without the taught sentence: {items}")
        except Exception as e:                    # report, stop the server, go on with the next pack
            failures.append(f"{name}: {type(e).__name__}: {e}")
        finally:
            code = s.stop()
            if code != 0:
                failures.append(f"{name}: server exit code {code}\n{s.stderr()}")
    if sentences.get("standard", 0) <= sentences.get("lite", 0):
        failures.append(f"standard should hold more sentences than lite: {sentences}")
    log(json.dumps({"ok": not failures, "sentences": sentences, "failures": failures}, indent=1, ensure_ascii=False))
    return 0 if not failures else 1


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # answers hold characters cp1252 lacks
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download")
    d.add_argument("--catalog", required=True)
    d.add_argument("--core", required=True)
    d.add_argument("--dest", required=True)
    c = sub.add_parser("chat")
    c.add_argument("--server", required=True)
    c.add_argument("--packs", required=True)
    c.add_argument("--data", required=True)
    args = ap.parse_args()
    return download(args) if args.cmd == "download" else chat(args)


if __name__ == "__main__":
    sys.exit(main())
