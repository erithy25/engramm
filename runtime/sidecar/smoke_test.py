"""Smoke test of the frozen server: it starts, prints its address, serves the chat page, imports
the whole chat stack (the load step reports the missing pack, not an import error), lists its
models, writes a few tokens with Sela-1 when the weights ship beside it (models/sela1-135m.npz),
lets Sela-2 answer through ``--check-sela2`` when models/sela2-chat.npz ships beside it, and exits when its standard
input closes.

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


def package_data(root: Path) -> list[Path]:
    """Every file of the engramm package that is not code, relative to the repository."""
    return sorted(f.relative_to(root) for f in (root / "engramm").rglob("*")
                  if f.is_file() and f.suffix not in (".py", ".pyc") and "__pycache__" not in f.parts
                  and f.name != ".DS_Store")


def check_package_data(dist: Path, root: Path = Path(__file__).resolve().parents[2]) -> None:
    """Every data file of the engramm package is in the frozen server, at its place (PyInstaller puts them under
    _internal/). The code finds them next to itself, and a missing one fails silently: without the lexicons the app
    asked "what's a laptop?" (builds up to 17 Oct 2026)."""
    data = package_data(root)
    for rel in ("engramm/understand/data/lex_en.tsv.gz", "engramm/understand/data/frame_model.json.gz",
                "engramm/know/data/howto.json.gz", "engramm/chat/conv_bank.json"):
        assert Path(rel) in data, rel
    frozen = {p.relative_to(dist).parts[-len(rel.parts):] for rel in data for p in dist.rglob(rel.name)}
    missing = [rel.as_posix() for rel in data if rel.parts not in frozen]
    assert not missing, f"package data missing from the frozen server: {missing}"


def main() -> int:
    dist = Path(sys.argv[1])
    exe = dist / ("engramm-server.exe" if sys.platform == "win32" else "engramm-server")
    check_package_data(dist)
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
            sela2_file = dist / "models" / "sela2-chat.npz"
            assert models["sela-2"]["available"] is sela2_file.exists(), (models, sela2_file)
            p.stdin.close()
            code = p.wait(timeout=30)
            assert code == 0, code
            sela2 = None
            if sela2_file.exists():                  # weights + bundled tokenizer load in the frozen app and answer
                out = subprocess.run([str(exe), "--check-sela2"], capture_output=True, timeout=900)
                sela2 = json.loads(out.stdout.decode().strip().splitlines()[-1])
                assert out.returncode == 0 and sela2["ok"], (sela2, out.stderr.decode()[-3000:])
            print(json.dumps({"ok": True, "start_seconds": round(started, 1), "health": health,
                              "sela": None if sela is None else {k: sela[k] for k in ("text", "tokens", "seconds")},
                              "sela2": sela2}))
            return 0
        finally:
            if p.poll() is None:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
