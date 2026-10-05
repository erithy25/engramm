"""``re`` with its own unbounded pattern cache.

The understanding layers build many patterns from constant pieces; together with the dialog's own patterns they
overflow the standard library's 512-entry cache, and then every pattern is compiled again on every message (measured:
the median turn went from 1 ms to 140 ms). The modules here use this drop-in instead.
"""
from __future__ import annotations

import re as _re
from functools import lru_cache

I = IGNORECASE = _re.I
M = MULTILINE = _re.M
S = DOTALL = _re.S
X = VERBOSE = _re.X
error = _re.error
Pattern = _re.Pattern
escape = _re.escape


@lru_cache(maxsize=None)
def compile(pattern, flags=0):          # noqa: A001 - mirrors re.compile
    return _re.compile(pattern, flags)


def _c(pattern, flags):
    return pattern if isinstance(pattern, _re.Pattern) else compile(pattern, flags)


def search(pattern, string, flags=0):
    return _c(pattern, flags).search(string)


def match(pattern, string, flags=0):
    return _c(pattern, flags).match(string)


def fullmatch(pattern, string, flags=0):
    return _c(pattern, flags).fullmatch(string)


def finditer(pattern, string, flags=0):
    return _c(pattern, flags).finditer(string)


def findall(pattern, string, flags=0):
    return _c(pattern, flags).findall(string)


def sub(pattern, repl, string, count=0, flags=0):
    return _c(pattern, flags).sub(repl, string, count)


def split(pattern, string, maxsplit=0, flags=0):
    return _c(pattern, flags).split(string, maxsplit)
