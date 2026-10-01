"""Smoke test of the frozen server: it starts, prints its address, serves the chat page, imports
the whole chat stack (the load step reports the missing pack, not an import error) and exits
when its standard input closes.

    python runtime/sidecar/smoke_test.py DIST_DIR      (the folder with engramm-server[.exe])
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def main() -> int:
    dist = Path(sys.argv[1])
    exe = dist / ("engramm-server.exe" if sys.platform == "win32" else "engramm-server")
    # data files the conversation layer needs at run time (PyInstaller puts them under _internal/)
    for name in ("conv_bank.json", "letters.json"):
        assert any(dist.rglob(name)), f"{name} missing from the frozen server"

    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.time()
        p = subprocess.Popen([str(exe), "--desktop", "--port", "0", "--pack", str(Path(tmp) / "nopack"),
                              "--memory", str(Path(tmp) / "memory.log")],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            first = p.stdout.readline().decode().strip()
            assert first.startswith("ENGRAMM_URL=http://127.0.0.1:"), (first, p.stderr.read().decode()[-3000:])
            base = first.split("=", 1)[1]
            page = urllib.request.urlopen(base + "/", timeout=10).read()
            assert b"<div id=\"root\">" in page or b"id=\"root\"" in page, page[:300]
            health = {}
            for _ in range(600):
                health = json.loads(urllib.request.urlopen(base + "/api/health", timeout=10).read())
                if health.get("error"):
                    break
                time.sleep(0.1)
            assert "No knowledge pack" in (health.get("error") or ""), health
            started = time.time() - t0
            p.stdin.close()
            code = p.wait(timeout=30)
            assert code == 0, code
            print(json.dumps({"ok": True, "start_seconds": round(started, 1), "health": health}))
            return 0
        finally:
            if p.poll() is None:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
