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
    # every data file next to the code must be in the bundle (PyInstaller puts them under _internal/):
    # without engramm/understand/data and engramm/know/data the app answered practical questions
    # with generic advice instead of the how-to and Wikibooks steps
    root = Path(__file__).resolve().parents[2]
    wanted = [f.relative_to(root).as_posix() for f in (root / "engramm").rglob("*")
              if f.is_file() and f.suffix not in (".py", ".pyc") and "__pycache__" not in f.parts]
    assert any(w.startswith("engramm/understand/data/") for w in wanted), "source tree without data files?"
    missing = [w for w in wanted if not any(p.as_posix().endswith(w) for p in dist.rglob(Path(w).name))]
    assert not missing, f"missing from the frozen server: {missing}"
    # the network core beside the server (desktop builds): it must answer and know the web search
    core = dist / ("engramm-core.exe" if sys.platform == "win32" else "engramm-core")
    if core.exists():
        out = subprocess.run([str(core), "egress"], input=b'{"op":"status","id":1}\n'
                             b'{"id":2,"channel":"search","url":"https://192.168.1.1/","allow_hosts":["*"]}\n',
                             capture_output=True, timeout=30)
        lines = [json.loads(x) for x in out.stdout.decode().splitlines()]
        assert lines[0].get("ok"), lines
        assert lines[1].get("error") == "private address not allowed: 192.168.1.1", lines

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
