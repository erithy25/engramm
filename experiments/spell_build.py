"""Build the speller's vocabulary (engramm/nlp/spell.py) from the reading of a pack.

    python -u -m experiments.spell_build --abstracts /dev/shm/engramm/reading/abstracts.jsonl \
        --top 400000 --out /dev/shm/engramm/reading/spell.json

Counts every word (lower case) and how often it starts with a capital letter when it is not the
first word of a sentence; keeps words seen at least ``--min-count`` times (at most ``--max-words``).
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path

WORD = re.compile(r"(?<![A-Za-z'])([A-Za-z][a-z']*)(?![A-Za-z])")
SENT = re.compile(r"(?<=[.!?])\s+")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--abstracts", type=Path, required=True)
    ap.add_argument("--top", type=int, default=400_000)
    ap.add_argument("--min-count", type=int, default=5)
    ap.add_argument("--max-words", type=int, default=250_000)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    t0 = time.time()
    counts, caps = Counter(), Counter()
    with open(args.abstracts, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= args.top:
                break
            for sent in SENT.split(json.loads(line)["text"]):
                for j, m in enumerate(WORD.finditer(sent)):
                    w = m.group(1)
                    low = w.lower().strip("'")
                    counts[low] += 1
                    if j and w[0].isupper():
                        caps[low] += 1
    words = [w for w, c in counts.most_common(args.max_words) if c >= args.min_count]
    data = {"kind": "spell", "source": str(args.abstracts.name), "articles": min(i + 1, args.top), "words": words,
            "counts": [counts[w] for w in words],
            "capital": [round(100 * caps[w] / counts[w]) for w in words]}
    args.out.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"words": len(words), "MB": round(args.out.stat().st_size / 1e6, 1),
                      "seconds": round(time.time() - t0)}), flush=True)


if __name__ == "__main__":
    main()
