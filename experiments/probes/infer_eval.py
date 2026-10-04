"""Score the inference set (U5): scripted conversations whose last reply must use what was said before.

    python -m experiments.probes.infer_eval experiments/probes/infer_dev.jsonl [--show] [--pack DIR]

Each line: {"lang", "turns": [...], "expect_any": [regex...], "expect_none": [regex...], "note"}. A case passes when the
reply to the last turn matches one expect_any pattern (case-insensitive) and no expect_none pattern. Sealed sets
(paths under /sealed/) are checked against their seal, and only numbers are printed for them — never the
conversations or the replies.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("set", type=Path)
    ap.add_argument("--pack", type=Path, default=Path("/dev/shm/engramm/pack-b3"))
    ap.add_argument("--show", action="store_true", help="print failing cases (development sets only)")
    a = ap.parse_args(argv)
    sealed = "/sealed/" in str(a.set.resolve())
    if sealed:
        from experiments.probes.run import verify
        if not verify(a.set):
            sys.exit("seal mismatch: refusing to run")
        a.show = False
    from engramm.app.server import ChatService
    rows = [json.loads(x) for x in a.set.read_text(encoding="utf-8").splitlines() if x.strip()]
    work = Path(tempfile.mkdtemp(prefix="infer_", dir="/dev/shm" if Path("/dev/shm").exists() else None))
    try:
        svc = ChatService("unused", pack=a.pack, memory_path=work / "m.log")
        svc.load()
        if svc.error:
            sys.exit(svc.error)
        ok, total, by_note, by_lang = 0, 0, Counter(), Counter()
        fails = Counter()
        for i, r in enumerate(rows):
            reply = ""
            for t in r["turns"]:
                reply = svc.chat(f"inf{i}", t)["text"]
            good = any(re.search(p, reply, re.I) for p in r.get("expect_any") or []) and \
                not any(re.search(p, reply, re.I) for p in r.get("expect_none") or [])
            total += 1
            ok += good
            by_lang[(r["lang"], good)] += 1
            by_note[(r.get("note", ""), good)] += 1
            if not good:
                fails[r.get("note", "")] += 1
                if a.show:
                    print(f"--- FAIL [{r['lang']}] {r.get('note')}\n  " + "\n  ".join(r["turns"]) + f"\n  => {reply[:300]!r}")
        print(f"passed {ok}/{total} = {ok / max(1, total):.1%}")
        for lang in ("en", "de"):
            n = by_lang[(lang, True)] + by_lang[(lang, False)]
            if n:
                print(f"  {lang}: {by_lang[(lang, True)]}/{n}")
        notes = sorted({k for k, _ in by_note})
        for nt in notes:
            print(f"  {nt or '-'}: {by_note[(nt, True)]}/{by_note[(nt, True)] + by_note[(nt, False)]}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
