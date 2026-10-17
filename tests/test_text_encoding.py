"""Text files are read and written as UTF-8 on every system. On Windows the default encoding of open(),
Path.read_text() and Path.write_text() is the code page (cp1252), not UTF-8: the desktop app's server then
failed to load the lite pack with "UnicodeDecodeError: 'charmap' codec can't decode byte 0x81" in
spanperc_ens7.json (17 Oct 2026). These tests keep that from coming back."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# what the desktop app runs: the server package and the sidecar scripts
CHECKED = [ROOT / "engramm", ROOT / "runtime" / "sidecar"]
# modules of other libraries that also have an .open() (their own encoding rules)
OTHER_OPEN = ("gzip", "bz2", "lzma", "webbrowser", "tarfile", "zipfile", "Image", "os", "io", "codecs")


def _mode(call: ast.Call, pos: int) -> str:
    if len(call.args) > pos and isinstance(call.args[pos], ast.Constant) and isinstance(call.args[pos].value, str):
        return call.args[pos].value
    for k in call.keywords:
        if k.arg == "mode" and isinstance(k.value, ast.Constant) and isinstance(k.value.value, str):
            return k.value.value
    return "r"


def locale_dependent_io(path: Path, root: Path = ROOT) -> list[str]:
    """Calls in ``path`` that read or write text in the system's default encoding, in source order."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[int, str]] = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        has_encoding = any(k.arg == "encoding" for k in n.keywords)
        f = n.func
        if isinstance(f, ast.Name) and f.id == "open":
            if "b" not in _mode(n, 1) and not has_encoding:
                found.append((n.lineno, "open()"))
        elif isinstance(f, ast.Attribute) and f.attr == "open":
            base = ast.unparse(f.value)
            if base in OTHER_OPEN or "zip" in base.lower() or "opener" in base:
                continue
            if "b" not in _mode(n, 0) and not has_encoding:
                found.append((n.lineno, f"{base}.open()"))
        elif isinstance(f, ast.Attribute) and f.attr in ("read_text", "write_text"):
            positional_encoding = len(n.args) > (0 if f.attr == "read_text" else 1)
            if not has_encoding and not positional_encoding:
                found.append((n.lineno, f".{f.attr}()"))
    return [f"{path.relative_to(root)}:{line} {what}" for line, what in sorted(found)]


def test_no_text_io_in_the_default_encoding():
    bad = [hit for root in CHECKED for p in sorted(root.rglob("*.py")) for hit in locale_dependent_io(p)]
    assert not bad, "pass encoding=\"utf-8\" (Windows reads text in its code page otherwise):\n" + "\n".join(bad)


def test_the_check_sees_the_old_bug(tmp_path):
    p = tmp_path / "old.py"
    p.write_text('import json\nfrom pathlib import Path\n'
                 'd = json.loads(Path("x.json").read_text())\n'
                 'Path("y").write_text("z")\n'
                 'with open("a.txt") as f: pass\n'
                 'with open("a.bin", "rb") as f: pass\n'
                 'Path("w").read_text(encoding="utf-8")\n', encoding="utf-8")
    assert locale_dependent_io(p, tmp_path) == ["old.py:3 .read_text()", "old.py:4 .write_text()", "old.py:5 open()"]


def _ascii_python_env() -> dict:
    """An environment whose default text encoding is ASCII: on Linux the closest stand-in for a Windows code page
    (a file with non-ASCII UTF-8 fails to read without an explicit encoding)."""
    env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0",
               PYTHONPATH=str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    env.pop("PYTHONIOENCODING", None)
    return env


def test_span_model_loads_without_a_utf8_default(tmp_path):
    from engramm.chat.spanstats import SpanPerceptron
    path = tmp_path / "spanperc_test.json"
    # "Łódź" has the bytes 0xC5 0x81 in UTF-8; 0x81 is undefined in cp1252, which made the app fail on Windows
    SpanPerceptron({"w=Łódź": 1.5, "w=café": -0.25, "tag=NN": 0.5}).save(path)
    env = _ascii_python_env()
    probe = subprocess.run([sys.executable, "-c", "import sys; print(sys.flags.utf8_mode, open(sys.argv[1]).read())",
                            str(path)], env=env, capture_output=True, text=True, encoding="utf-8")
    assert probe.returncode != 0 and "UnicodeDecodeError" in probe.stderr, \
        "the stand-in for a Windows code page did not take effect: " + probe.stdout + probe.stderr
    code = ("import json, sys\n"
            "from engramm.chat.spanstats import SpanPerceptron\n"
            "m = SpanPerceptron.load(sys.argv[1], compact=True)\n"
            "print(json.dumps([m.score(['w=\\u0141\\u00f3d\\u017a']), m.score(['w=caf\\u00e9', 'tag=NN'])]))\n")
    out = subprocess.run([sys.executable, "-c", code, str(path)], env=env, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", cwd=ROOT)
    assert out.returncode == 0, out.stderr[-3000:]
    assert json.loads(out.stdout.strip().splitlines()[-1]) == [1.5, 0.25]
