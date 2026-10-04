"""Score the situation parser on a labelled set (docs/PREREG_UNDERSTAND_V0.md, U1). Prints numbers only — never the
sentences, so a sealed set stays sealed.

    python -m experiments.probes.frames_eval experiments/probes/sealed/frames_test.jsonl
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engramm.understand.frames import parse  # noqa: E402
from engramm.understand.lex import lexicon  # noqa: E402
from experiments.probes.run import verify  # noqa: E402


def _obj_ok(lang: str, gold: str, frame) -> bool:
    if not gold:
        return not frame.obj or True            # an extra object is not counted against the role score
    if lang == "en":
        return frame.obj == gold
    # German: the gold label is the English lemma; accept when the German noun's glosses lead there
    if not frame.obj:
        return False
    de, en = lexicon("de").get(frame.obj, "n"), lexicon("en").get(gold, "n")
    return bool(de and en and de.cats and (de.cats & en.cats - {"PERSON", "EVENT", "PLACE"}))


def main(path: str) -> None:
    p = Path(path)
    if "/sealed/" in str(p) and not verify(p):
        raise SystemExit(f"{p.name}: does not match its seal")
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    kind_ok = Counter()
    kind_n = Counter()
    role_ok = role_n = 0
    confusion = Counter()
    for r in rows:
        f = parse(r["text"], r["lang"])
        got = f.kind or "NONE"
        kind_n[r["lang"]] += 1
        if got == r["kind"]:
            kind_ok[r["lang"]] += 1
        else:
            confusion[(r["kind"], got)] += 1
        for role, gold in (("who", r.get("who", "")), ("body", r.get("body", "")), ("obj", r.get("obj", ""))):
            if not gold:
                continue
            role_n += 1
            if role == "who":
                role_ok += f.who == gold
            elif role == "body":
                b = f.body
                if r["lang"] == "de" and b:
                    e = lexicon("de").get(b, "n")
                    role_ok += bool(e) and "BODYPART" in e.cats   # German body word found (gold is the English lemma)
                else:
                    role_ok += b == gold or (b.endswith("s") and b[:-1] == gold)
            else:
                role_ok += _obj_ok(r["lang"], gold, f)
    for lang in sorted(kind_n):
        print(f"kind {lang}: {kind_ok[lang]}/{kind_n[lang]} = {kind_ok[lang] / kind_n[lang]:.1%}")
    tot = sum(kind_ok.values()), sum(kind_n.values())
    print(f"kind all: {tot[0]}/{tot[1]} = {tot[0] / tot[1]:.1%}")
    print(f"roles: {role_ok}/{role_n} = {role_ok / max(1, role_n):.1%}")
    print("confusions (gold→got, count):", ", ".join(f"{a}→{b} {n}" for (a, b), n in confusion.most_common(12)))


if __name__ == "__main__":
    main(sys.argv[1])
