"""Conversation probes: play scripted conversations against the real chat server and print every turn.

    python -m experiments.probes.run experiments/probes/sets/conv15.json [--pack DIR] [--only en0 de3]
    python -m experiments.probes.run SET.json --out transcript.txt --quiet     # counts only on the screen
    python -m experiments.probes.run --seal SET.json                          # write its SHA-256 to the seal file
    python -m experiments.probes.run --verify SET.json                        # refuse if it no longer matches

A probe set is JSON: {"name": ..., "convs": {"en": [[turn, turn, ...], ...], "de": [...]}}. Each conversation runs
in its own conversation id against one shared memory, like a person using the app. The marker "!!" is only a
coarse screen for known weak phrases and exact repeats; the measured number is always the reading of every answer
(docs/PREREG_UNDERSTAND_V0.md). Sealed sets (experiments/probes/sealed/) are never read during development: run
them with --out and --quiet, and hand the transcript to the reader.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAL_FILE = ROOT / "docs" / "UNDERSTAND_SEAL.txt"

WEAK = re.compile(r"I'll remember|Noted|Tell me more\?|I see\. Tell me more|Oh\? Go on|What happened\?$|couldn't find|"
                  r"I don't know|Erzähl ruhig mehr|Erzähl gern mehr|Notiert|verstehe ich leider nicht|nicht ganz verstanden|"
                  r"und wie findest du das|Mhm\. Und dann|nice to meet|you live in|work as|merke ich mir|Sorry — who's|"
                  r"nicht nachschlagen|How's that going\?", re.I)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(path: Path) -> None:
    lines = [ln for ln in (SEAL_FILE.read_text().splitlines() if SEAL_FILE.exists() else []) if not ln.endswith(" " + path.name)]
    lines.append(f"{sha256(path)}  {path.name}")
    SEAL_FILE.write_text("\n".join(lines) + "\n")
    print(f"sealed {path.name}")


def verify(path: Path) -> bool:
    if not SEAL_FILE.exists():
        return False
    want = {ln.split()[1]: ln.split()[0] for ln in SEAL_FILE.read_text().splitlines() if len(ln.split()) == 2}
    return want.get(path.name) == sha256(path)


def run(sets: list[Path], pack: Path, only: list[str], out, quiet: bool) -> dict:
    sys.path.insert(0, str(ROOT))
    from engramm.app.server import ChatService
    work = Path(tempfile.mkdtemp(prefix="probe_", dir=os.environ.get("TMPDIR") or None))
    svc = ChatService("unused", pack=pack, memory_path=work / "m.log")
    svc.load()
    totals = {}
    for sp in sets:
        data = json.loads(sp.read_text())
        if "/sealed/" in str(sp) and not verify(sp):
            raise SystemExit(f"{sp.name}: does not match its seal in {SEAL_FILE.name}")
        name = data.get("name", sp.stem)
        for lang, convs in data["convs"].items():
            flagged = turns = 0
            for i, conv in enumerate(convs):
                cid = f"{lang}{i}"
                if only and cid not in only:
                    continue
                seen: set[str] = set()
                print(f"=== {name} {cid}", file=out)
                for msg in conv:
                    text = svc.chat(f"{name}-{cid}", msg)["text"]
                    flag = bool(WEAK.search(text)) or text in seen
                    seen.add(text)
                    turns += 1
                    flagged += flag
                    print(f"{'!!' if flag else '  '} U: {msg}\n   E: {text}", file=out)
            totals[f"{name}:{lang}"] = (flagged, turns)
            line = f"== {name} {lang}: {flagged} flagged of {turns}"
            print(line, file=out)
            if quiet and out is not sys.stdout:
                print(line)
    return totals


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sets", nargs="*", type=Path)
    ap.add_argument("--pack", type=Path, default=Path(os.environ.get("ENGRAMM_PACK", "/dev/shm/engramm/pack-b3")))
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--seal", type=Path)
    ap.add_argument("--verify", type=Path)
    a = ap.parse_args(argv)
    if a.seal:
        seal(a.seal)
        return
    if a.verify:
        ok = verify(a.verify)
        print("ok" if ok else "MISMATCH")
        raise SystemExit(0 if ok else 1)
    out = open(a.out, "w") if a.out else sys.stdout
    try:
        run(a.sets, a.pack, a.only, out, a.quiet)
    finally:
        if a.out:
            out.close()


if __name__ == "__main__":
    main()
