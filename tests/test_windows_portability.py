"""Things that work on Linux and macOS but break the desktop app on Windows (found after the Windows test build of
17 Oct 2026): strftime directives the Windows C library does not know, and files pinned by SHA-256 whose bytes a
Windows checkout would change (Git turns LF into CRLF there unless .gitattributes says -text)."""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# glibc/BSD extensions the Windows C runtime rejects with ValueError: the flags "-", "_", "^" ("%-d": no padding) and
# "%k", "%l", "%P", "%s", "%+" (C99 ones such as "%e", "%T", "%z" work there)
UNPORTABLE = re.compile(r"%[-_^]|%[klPs+]")


def strftime_formats(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "strftime" and n.args:
            a = n.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                out.append((n.lineno, a.value))
    return out


def test_strftime_formats_work_on_windows():
    bad = [f"{p.relative_to(ROOT)}:{line} {fmt!r}" for p in sorted((ROOT / "engramm").rglob("*.py"))
           for line, fmt in strftime_formats(p) if UNPORTABLE.search(fmt.replace("%%", ""))]
    assert not bad, "strftime directives the Windows C library rejects:\n" + "\n".join(bad)


def test_the_strftime_check_sees_the_old_bug():
    assert UNPORTABLE.search("%-d %B %Y") and UNPORTABLE.search("%k:%M") and not UNPORTABLE.search("%d %B %Y %H:%M %e")


@pytest.mark.skipif(shutil.which("git") is None or not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_pinned_tokenizers_keep_their_bytes_on_windows_checkouts():
    files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "data").glob("*tokenizer*.json"))
    assert "data/lm2_tokenizer.json" in files
    out = subprocess.run(["git", "check-attr", "text", "--", *files], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", check=True).stdout
    converted = [ln for ln in out.splitlines() if not ln.endswith(": text: unset")]
    assert not converted, "add these to .gitattributes with -text (their SHA-256 is pinned):\n" + "\n".join(converted)
