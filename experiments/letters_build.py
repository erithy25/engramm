"""Letter statistics for the conversation layer (engramm/chat/smart.py): how English-looking a
typed word is, so "dhdhd" or "asdfgh" can be told apart from a real word or a name.

Counts letter trigrams (with word boundaries) over the speller vocabulary of a knowledge pack,
each word weighted by log(1 + count), and keeps the most frequent words as a known-word list.
Output: engramm/chat/letters.json (shipped with the package; a few hundred KB).

    python experiments/letters_build.py PACK/spell.json [--words 30000]
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "engramm" / "chat" / "letters.json"
_WORD = re.compile(r"^[a-z]+(?:'[a-z]+)?$")


def build(spell_path: Path, n_words: int = 30000) -> dict:
    d = json.loads(Path(spell_path).read_text(encoding="utf-8"))
    tri: Counter = Counter()
    bi: Counter = Counter()
    kept = []
    for w, c in zip(d["words"], d["counts"]):
        w = w.lower()
        if not _WORD.match(w) or c < 3:
            continue
        weight = math.log1p(c)
        s = f"^{w}$"
        for i in range(len(s) - 2):
            tri[s[i:i + 3]] += weight
            bi[s[i:i + 2]] += weight
        if len(kept) < n_words:
            kept.append(w)
    # log P(c3 | c1 c2) with add-0.5 smoothing over 28 symbols (a-z, ^, $), rounded to 0.01
    logp = {}
    for t, c in tri.items():
        logp[t] = round(math.log((c + 0.5) / (bi[t[:2]] + 14.0)), 2)
    floor = {b: round(math.log(0.5 / (c + 14.0)), 2) for b, c in bi.items()}
    return {"kind": "letters", "source": d.get("source", ""), "articles": d.get("articles"),
            "trigram_logp": logp, "unseen_logp": floor, "default_logp": round(math.log(0.5 / 14.0), 2),
            "words": kept}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spell", type=Path)
    ap.add_argument("--words", type=int, default=30000)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    data = build(a.spell, a.words)
    a.out.write_text(json.dumps(data, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"{a.out}: {len(data['trigram_logp'])} trigrams, {len(data['words'])} words, "
          f"{a.out.stat().st_size / 1e3:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
