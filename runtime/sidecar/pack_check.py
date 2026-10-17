"""The server with a real knowledge pack, as the desktop app runs it: download a pack the way the app does (one release
asset per file, each checked against the manifest's size and SHA-256, the manifest written last), then start the
server (from source or frozen) on it, wait until it is ready, ask a few questions and stop it by closing its input.

    python runtime/sidecar/pack_check.py fetch --base-url URL --root DIR       (prints the pack folder)
    python runtime/sidecar/pack_check.py run --pack-file DIR/pack_dir.txt [--expect-utf8] [--cwd DIR] -- CMD …

The pack goes into a folder whose name has a space and non-ASCII letters (like a Windows user folder "Jörg Müller"),
so paths are tested too. ``run`` starts the server without PYTHONUTF8 and PYTHONIOENCODING, as on a user's computer:
on Windows Python then reads text in the code page (cp1252) unless the code says UTF-8 — which broke loading the lite
pack in the Windows build of 17 Oct 2026. Writes one JSON line; exit code 0 only when the server became ready and
answered every question.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

QUESTIONS = ["Hello!", "What is the capital of France?", "Who was Ada Lovelace?",
             "Hallo, wie geht es dir?", "Erzähl mir etwas über München.", "My laptop is broken.",
             "Mein Fahrrad ist kaputt."]
# replies that show the frozen server lost its language data (lexicons of engramm/understand): every noun is unknown
WRONG = ("Quick question — what's a", "Kurze Frage: Was ist")
FOLDER = "ENGRAMM Prüfung Jörg Müller"        # a space, umlauts and a non-ASCII user name


def _get(url: str, timeout: float = 60.0) -> bytes:
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def fetch(base_url: str, root: Path) -> Path:
    base_url = base_url.rstrip("/") + "/"
    raw = _get(base_url + "manifest.json")
    manifest = json.loads(raw)
    dest = root / FOLDER / "packs" / f"{manifest['pack']}-{manifest['version']}"
    dest.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for rel, entry in sorted(manifest["files"].items()):
        path = dest.joinpath(*rel.split("/"))
        if path.exists() and path.stat().st_size == entry["bytes"]:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        h = hashlib.sha256()
        with urllib.request.urlopen(base_url + rel.replace("/", "__"), timeout=120) as r, open(part, "wb") as f:
            while chunk := r.read(1 << 20):
                h.update(chunk)
                f.write(chunk)
        if part.stat().st_size != entry["bytes"] or h.hexdigest() != entry["sha256"]:
            raise SystemExit(f"{rel} does not match the manifest after download")
        part.replace(path)
    (dest / "manifest.json").write_bytes(raw)
    (root / "pack_dir.txt").write_text(str(dest), encoding="utf-8")
    print(json.dumps({"pack": str(dest), "files": len(manifest["files"]), "bytes": manifest["bytes"],
                      "seconds": round(time.time() - t0, 1)}, ensure_ascii=False))
    return dest


def _post(base: str, path: str, body: dict, timeout: float) -> tuple[int, dict]:
    req = urllib.request.Request(base + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")


def run(pack: Path, cmd: list[str], cwd: Path | None, expect_utf8: bool, timeout: float) -> int:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env["ENGRAMM_NO_BROWSER"] = "1"
    memory = pack.parent.parent / f"data-{os.getpid()}" / "chat_memory.log"     # a fresh app data folder per run
    memory.parent.mkdir(parents=True, exist_ok=True)
    if Path(cmd[0]).is_file():                     # a frozen server given by its path: absolute, with this OS's separators
        cmd = [str(Path(cmd[0]).resolve())] + cmd[1:]
    out: dict = {"cmd": cmd, "pack": str(pack), "ready": False, "error": None, "answers": []}
    t0 = time.time()
    p = subprocess.Popen(cmd + ["--desktop", "--port", "0", "--pack", str(pack), "--memory", str(memory)],
                         cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logs = {"stdout": [], "stderr": []}

    def drain(name: str, stream) -> None:          # keep both pipes empty, as the app does
        for line in iter(stream.readline, b""):
            logs[name].append(line.decode("utf-8", errors="replace").rstrip())

    first = p.stdout.readline().decode("utf-8", errors="replace").strip()
    for name, stream in (("stdout", p.stdout), ("stderr", p.stderr)):
        threading.Thread(target=drain, args=(name, stream), daemon=True).start()
    try:
        if not first.startswith("ENGRAMM_URL=http://127.0.0.1:"):
            time.sleep(2)
            out["error"] = f"no address line: {first!r}"
            return _report(out, logs, 1)
        base = first.split("=", 1)[1]
        health: dict = {}
        while time.time() - t0 < timeout:
            try:
                with urllib.request.urlopen(base + "/api/health", timeout=30) as r:
                    health = json.loads(r.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                health = {}
            if health.get("ready") or health.get("error") or p.poll() is not None:
                break
            time.sleep(1)
        out.update({"ready": bool(health.get("ready")), "error": health.get("error"),
                    "sentences": health.get("sentences"), "load_seconds": round(time.time() - t0, 1)})
        if not out["ready"]:
            return _report(out, logs, 1)
        ok = True
        for i, q in enumerate(QUESTIONS):
            t1 = time.time()
            code, reply = _post(base, "/api/chat", {"conversation": "check", "message": q}, timeout=300)
            text = str(reply.get("text") or reply.get("error") or "")
            good = code == 200 and bool(text.strip()) and not any(w in text for w in WRONG)
            ok &= good
            out["answers"].append({"q": q, "code": code, "kind": reply.get("kind"), "text": text[:240],
                                   "seconds": round(time.time() - t1, 2), "ok": good})
        flags = next((ln for ln in logs["stderr"] if "utf8_mode=" in ln), "")
        out["python"] = flags
        if expect_utf8 and "utf8_mode=1" not in flags:
            out["error"] = "the frozen server does not run in UTF-8 mode"
            ok = False
        p.stdin.close()
        out["exit_code"] = p.wait(timeout=60)
        return _report(out, logs, 0 if ok and out["exit_code"] == 0 else 1)
    finally:
        if p.poll() is None:
            p.kill()


def _report(out: dict, logs: dict, code: int) -> int:
    time.sleep(0.5)
    out["ok"] = code == 0
    out["stderr_tail"] = logs["stderr"][-25:]
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
    return code


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="what", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--base-url", required=True)
    f.add_argument("--root", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--pack-file", type=Path, required=True, help="the pack_dir.txt written by fetch")
    r.add_argument("--cwd", type=Path, default=None)
    r.add_argument("--expect-utf8", action="store_true", help="the server must report utf8_mode=1 (frozen builds)")
    r.add_argument("--timeout", type=float, default=900.0)
    r.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    if a.what == "fetch":
        fetch(a.base_url, a.root)
        return 0
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    if not cmd:
        ap.error("run needs the server command after --")
    return run(Path(a.pack_file.read_text(encoding="utf-8").strip()), cmd, a.cwd, a.expect_utf8, a.timeout)


if __name__ == "__main__":
    sys.exit(main())
