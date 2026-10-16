"""Every text file the app reads or writes names its encoding.

Windows opens text files in the ANSI code page (cp1252) unless told otherwise, and the pack holds
UTF-8 JSON with non-ASCII characters (``spanperc_*.json`` is written with ``ensure_ascii=False``).
One ``read_text()`` without ``encoding`` stopped the desktop app on Windows with "error while
loading" (UnicodeDecodeError, byte 0x81). The app also runs in Python's UTF-8 mode (PyInstaller
option, ``PYTHONUTF8`` from the desktop app); this check keeps the code right without it.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# the packages the chat server loads (engramm/app and everything it imports at run time)
PACKAGES = ("app", "chat", "kb", "nlp", "web", "understand", "learn", "know")
COMPRESSED = ("gzip", "bz2", "lzma")


def _const(node: ast.AST | None) -> object:
    return node.value if isinstance(node, ast.Constant) else None


def _mode(call: ast.Call, position: int, default: str) -> object:
    if len(call.args) > position:
        return _const(call.args[position])
    for k in call.keywords:
        if k.arg == "mode":
            return _const(k.value)
    return default


def _problems(path: Path) -> list[str]:
    out: list[tuple[int, str]] = []
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path.name
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call) or any(k.arg == "encoding" for k in node.keywords):
            continue
        fn = node.func
        where = f"{rel}:{node.lineno}"
        if isinstance(fn, ast.Attribute) and fn.attr in ("read_text", "write_text"):
            out.append((node.lineno, f"{where} {fn.attr}() without encoding"))
        elif isinstance(fn, ast.Name) and fn.id == "open":
            mode = _mode(node, 1, "r")
            if not (isinstance(mode, str) and "b" in mode):
                out.append((node.lineno, f"{where} open(..., {mode!r}) without encoding"))
        elif isinstance(fn, ast.Attribute) and fn.attr == "open" and isinstance(fn.value, ast.Name) \
                and fn.value.id in COMPRESSED:
            mode = _mode(node, 1, "rb")
            if not (isinstance(mode, str) and "b" in mode):
                out.append((node.lineno, f"{where} {fn.value.id}.open(..., {mode!r}) without encoding"))
    return [text for _, text in sorted(out)]


def test_text_files_name_their_encoding():
    problems = [p for pkg in PACKAGES for f in sorted((ROOT / "engramm" / pkg).rglob("*.py")) for p in _problems(f)]
    assert not problems, "\n".join(problems)


def test_the_check_finds_a_missing_encoding(tmp_path):
    bad = tmp_path / "probe.py"
    bad.write_text('import gzip, json\nfrom pathlib import Path\n'
                   'json.loads(Path("x").read_text())\nopen("y")\nopen("z", "rb")\n'
                   'gzip.open("w", "rt")\nopen("v", encoding="utf-8")\n', encoding="utf-8")
    found = _problems(bad)
    assert [f.split(" ", 1)[1] for f in found] == ["read_text() without encoding", "open(..., 'r') without encoding",
                                                   "gzip.open(..., 'rt') without encoding"]
