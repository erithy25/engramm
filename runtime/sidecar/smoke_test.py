"""Smoke test of the frozen server: it starts, prints its address, serves the chat page, imports
the whole chat stack (the load step reports the missing pack, not an import error), lists its
models, writes a few tokens with Sela-1 when the weights ship beside it (models/sela1-135m.npz),
and exits when its standard input closes.

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
    for name in ("conv_bank.json", "letters.json", "feeds.json"):
        assert any(dist.rglob(name)), f"{name} missing from the frozen server"
    # the network core beside the server (desktop builds): it must answer and have Tor
    core = dist / ("engramm-core.exe" if sys.platform == "win32" else "engramm-core")
    if core.exists():
        out = subprocess.run([str(core), "egress"], input=b'{"op":"status","id":1}\n', capture_output=True, timeout=30)
        status = json.loads(out.stdout.decode().splitlines()[0])
        assert status.get("ok") and status.get("tor") is True, status

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
            models = {m["id"]: m for m in json.loads(urllib.request.urlopen(base + "/api/models", timeout=10).read())["models"]}
            sela_file = dist / "models" / "sela1-135m.npz"
            assert models["sela-1"]["available"] is sela_file.exists(), (models, sela_file)
            sela = None
            if sela_file.exists():                   # the network runs without a pack; NumPy only
                req = urllib.request.Request(base + "/api/chat", headers={"Content-Type": "application/json"},
                                             data=json.dumps({"conversation": "smoke", "message": "The history of the city",
                                                              "model": "sela-1", "max_tokens": 6}).encode())
                sela = json.loads(urllib.request.urlopen(req, timeout=300).read())
                assert sela["kind"] == "generated" and sela["tokens"] >= 1 and sela["text"], sela
            p.stdin.close()
            code = p.wait(timeout=30)
            assert code == 0, code
            print(json.dumps({"ok": True, "start_seconds": round(started, 1), "health": health,
                              "sela": None if sela is None else {k: sela[k] for k in ("text", "tokens", "seconds")}}))
            return 0
        finally:
            if p.poll() is None:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
