"""Conformance of the Rust runtime core (runtime/core) with the Python reference.

The binary is taken from ENGRAMM_CORE_BIN, else from the usual cargo target folders; the
tests are skipped when it has not been built (``cargo build --release`` in runtime/core).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from engramm.chat.bank import choose, load_bank, normalise

ROOT = Path(__file__).resolve().parents[1]


def _binary() -> Path | None:
    cands = [os.environ.get("ENGRAMM_CORE_BIN", "")]
    target = os.environ.get("CARGO_TARGET_DIR")
    if target:
        cands.append(str(Path(target) / "release" / "engramm-core"))
    cands += [str(ROOT / "runtime" / "core" / "target" / "release" / "engramm-core"),
              "/dev/shm/engramm/cargo_target/release/engramm-core"]
    for c in cands:
        for p in (Path(c), Path(c + ".exe")) if c else ():
            if p.is_file():
                return p
    return None


BIN = _binary()
pytestmark = pytest.mark.skipif(BIN is None, reason="runtime/core not built")


def _run(args: list[str], stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run([str(BIN), *args], input=stdin.encode("utf-8"), capture_output=True, timeout=120)


def _messages() -> list[str]:
    msgs = set()
    bank = load_bank()
    for it in bank.intents:
        msgs.update(it.examples)
    for line in (ROOT / "data" / "chatbench" / "dev_team.jsonl").read_text(encoding="utf-8").splitlines():
        msgs.update(json.loads(line)["turns"])
    msgs.update([
        "", " ", "ok", "ok.", "Hey ENGRAMM, how r u?", "  Well, so what’s up!!! ", "um uh so, please tell me a joke",
        "buddy", "bot?", "Hi bot, idk", "ok ok ok", "ok thanks", "and then?", "“Quoted” ‘text’ `here´",
        "ΑΣ ΟΔΟΣ", "İstanbul", "hmmmm... well", "so,so", "hello,, bot ,", "What is 2+2?", "tabs\tand\nnewlines",
        "ENGRAMM, remember that my sister is called Anna.", "please", "please please help", "gr8 thx u r the best",
    ])
    return sorted(msgs)


@pytest.mark.parametrize("fillers", [True, False])
def test_normalise_matches_python(fillers):
    msgs = [m for m in _messages() if "\n" not in m and "\r" not in m]
    res = _run(["normalise"] + ([] if fillers else ["--no-fillers"]), "\n".join(msgs) + "\n")
    assert res.returncode == 0, res.stderr.decode()
    got = [json.loads(line) for line in res.stdout.decode("utf-8").splitlines()]
    assert len(got) == len(msgs)
    bad = [(m, g, normalise(m, fillers)) for m, g in zip(msgs, got) if g != normalise(m, fillers)]
    assert not bad, bad[:10]
    assert len(msgs) > 300


def test_choose_matches_python():
    bank = load_bank()
    lines, want = [], []
    lists = [it.responses for it in bank.intents if len(it.responses) > 1][:60]
    for k, opts in enumerate(lists):
        # n = 4, 5: every option used recently (in two orders): the one used longest ago wins
        for n in range(6):
            key = f"conv{k}|list{k}|{n}"
            recent = opts[:n] if n < 4 else (list(reversed(opts)) if n == 4 else opts[1:] + opts[:2])
            salt = "s" if n % 2 else ""
            lines.append(json.dumps({"options": opts, "key": key, "recent": recent, "salt": salt}))
            want.append(choose(opts, key, recent, salt))
    res = _run(["choose"], "\n".join(lines) + "\n")
    assert res.returncode == 0, res.stderr.decode()
    got = [json.loads(line) for line in res.stdout.decode("utf-8").splitlines()]
    assert got == want


def _pack(tmp: Path) -> Path:
    d = tmp / "pack"
    (d / "nlp").mkdir(parents=True)
    (d / "corpus.u16").write_bytes(bytes(range(256)) * 10)
    (d / "nlp" / "pos.json").write_text('{"kind": "pos"}')
    (d / "kb.sqlite").write_bytes(b"SQLite format 3\x00" + b"\x01" * 100)
    files = {}
    for p in sorted(d.rglob("*")):
        if p.is_file():
            files[p.relative_to(d).as_posix()] = {"bytes": p.stat().st_size,
                                                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    manifest = {"pack": "test", "version": "3.0.0", "built": "2026-09-29T00:00:00Z",
                "bytes": sum(f["bytes"] for f in files.values()), "files": files, "licenses": {}, "info": {}}
    (d / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return d


def test_verify_pack(tmp_path):
    d = _pack(tmp_path)
    res = _run(["verify", str(d)])
    assert res.returncode == 0, res.stdout.decode() + res.stderr.decode()
    rep = json.loads(res.stdout)
    assert sorted(rep["ok"]) == ["corpus.u16", "kb.sqlite", "nlp/pos.json"]
    # same size, one byte changed: only the deep check sees it
    data = bytearray((d / "kb.sqlite").read_bytes())
    data[-1] ^= 1
    (d / "kb.sqlite").write_bytes(bytes(data))
    assert _run(["verify", str(d), "--quick"]).returncode == 0
    res = _run(["verify", str(d)])
    assert res.returncode == 1
    assert json.loads(res.stdout)["wrong_hash"] == ["kb.sqlite"]
    (d / "nlp" / "pos.json").unlink()
    rep = json.loads(_run(["verify", str(d)]).stdout)
    assert rep["missing"] == ["nlp/pos.json"] and rep["bytes_to_fetch"] > 0
    assert _run(["sha256", str(d / "corpus.u16")]).stdout.decode().strip() == \
        hashlib.sha256((d / "corpus.u16").read_bytes()).hexdigest()


def test_unsafe_manifest_is_refused(tmp_path):
    d = _pack(tmp_path)
    m = json.loads((d / "manifest.json").read_text())
    m["files"]["../evil"] = {"bytes": 0, "sha256": "0" * 64}
    (d / "manifest.json").write_text(json.dumps(m))
    res = _run(["verify", str(d)])
    assert res.returncode == 3 and b"unsafe path" in res.stderr
