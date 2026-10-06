"""Practical steps from Wikibooks (V3): first aid, bicycle and car repair, knots (English); Erste Hilfe, Hausapotheke,
Survival (German). Built by experiments/wikibooks_build.py. A page answers when its name is said in the conversation
(and, for the repair books, the book's topic too); health steps always come with the line to see a doctor or call
for help. Text: Wikibooks, CC BY-SA 4.0 — the book and page are shown as the source.
"""
from __future__ import annotations

import gzip
import json
from engramm.understand import _re as re
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "wikibooks.json.gz"
_ITEMS: list[dict] | None = None


def items() -> list[dict]:
    global _ITEMS
    if _ITEMS is None:
        _ITEMS = json.load(gzip.open(DATA, "rt", encoding="utf-8")) if DATA.exists() else []
    return _ITEMS


def _stems(text: str, short: int = 4) -> set[str]:
    return {w[:5] for w in re.findall(rf"[a-zäöüß]{{{short},}}", text.lower())}


def find(text: str, lang: str) -> dict | None:
    """The page whose name the text says (all its words, as 5-letter stems: „verbrannt“ finds „Verbrennung“), the longest name first."""
    low = text.lower()
    have = _stems(low)
    best, best_len = None, 0
    for it in items():
        if it["lang"] != lang:
            continue
        if it["book_words"] and not any(re.search(rf"\b{w}\w*", low) for w in it["book_words"]):
            continue
        for n in it["names"]:
            ws = _stems(n, 3) - {"and", "the", "der", "die", "das", "und", "von", "mit"}
            if ws and ws <= _stems(low, 3) and len(n) > best_len:
                best, best_len = it, len(n)
    return best


def render(it: dict, n: int = 3) -> str:
    de = it["lang"] == "de"
    title = it["title"].replace("/ ", "/")
    body = "\n".join(f"• {s}" for s in it["steps"][:n])
    head = "Aus Wikibooks" if de else "From Wikibooks"
    src = f"(„{title}“)" if de else f"(“{title}”)"
    warn = ""
    if it["kind"] == "HEALTH":
        warn = ("\nWenn es schlimm ist oder schlimmer wird: ärztlich abklären lassen, im Notfall 112." if de else
                "\nIf it's serious or getting worse, see a doctor — in an emergency call 112 or 911.")
    return f"{head} {src}:\n{body}{warn}"
