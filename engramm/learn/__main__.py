"""Learning packs from the command line (V5): export what was learned on this computer for a person to check, and
import a checked pack.

    python -m engramm.learn export --state ~/.../learn.json --out pack.json
    python -m engramm.learn show pack.json          # what a pack contains, for the person checking it
    python -m engramm.learn import --state ~/.../learn.json pack.json

A pack holds taught words and the weight changes of corrections, never sentences, style, episodes or rewards. It
carries a SHA-256 over its content; a changed file is refused. Imported steps are ordinary steps: "forget everything
you learned" removes them again.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engramm.learn.state import LearnState


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m engramm.learn", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--state", type=Path, required=True)
    e.add_argument("--out", type=Path, required=True)
    sh = sub.add_parser("show")
    sh.add_argument("pack", type=Path)
    i = sub.add_parser("import")
    i.add_argument("--state", type=Path, required=True)
    i.add_argument("pack", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "export":
        pack = LearnState(a.state).export_pack()
        a.out.write_text(json.dumps(pack, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {a.out}: {len(pack['words'])} words, {len(pack['corrections'])} corrections")
        return 0
    pack = json.loads(a.pack.read_text(encoding="utf-8"))
    if a.cmd == "show":
        for w in pack.get("words", []):
            print(f"word  {w['lang']}  {w['word']:<20} {', '.join(w['cats'])}")
        for c in pack.get("corrections", []):
            print(f"correction  {c['bad']} → {c['good']}  ({len(c['delta'])} features)")
        return 0
    try:
        res = LearnState(a.state).import_pack(pack)
    except ValueError as err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    print("already imported" if res["already"] else f"imported {res['words']} words, {res['corrections']} corrections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
