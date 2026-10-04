"""Build the how-to index (U3, docs/PREREG_UNDERSTAND_V0.md): practical sentences from the whole of Wikipedia, kept
only for everyday articles (health, body, household things, vehicles, animals, food), with their source.

    python -m experiments.howto_build --release shelf-20260927 --out /dev/shm/engramm/howto.sqlite [--work DIR]

Reads the shelf volumes of a release one by one (downloaded, processed, deleted), splits each article into sentences
and keeps those with a practical marker ("can be treated with", "first aid", "should seek medical", "to remove …",
"apply ice" …). An article enters when its title names an everyday thing (the situation lexicon's word classes) and
it has at least two such sentences. Output: SQLite with ``howto(title, kind, text)`` and an FTS5 table for search.
Licence: Wikipedia text, CC BY-SA 4.0 — every answer shows the article title as its source.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BUCKET = 1 << 20
ADVICE = re.compile(
    r"\b(?:treat(?:ed|ment)? (?:with|by|includes?|consists|involves|is|for)|first aid|can be (?:treated|relieved|removed|"
    r"cleaned|repaired|prevented|fixed|reduced|managed|soothed)|(?:patients|people|you|individuals|one|they|owners) "
    r"should|is recommended|are recommended|recommended (?:to|that)|it is advisable|seek (?:medical|immediate|emergency)|"
    r"see a (?:doctor|physician|dentist|vet)|consult (?:a|your)|to prevent|prevention (?:includes|is|involves)|"
    r"avoid(?:ing)? (?:contact|exposure|scratching|the)|apply(?:ing)? (?:a|an|ice|pressure|cold|heat)|rinse|rinsing|"
    r"remove (?:the|any)|removing the|cool(?:ing)? (?:the|it)|wash(?:ing)? (?:the|it|with)|antihistamines?|bandage|ice pack|"
    r"cold compress|elevat(?:e|ing) the|over-the-counter|pain relievers?|painkillers?|usually resolves?|resolves? on its own|"
    r"heals? within|go away (?:on their own|within)|repair(?:ed|s)? (?:by|with)|replac(?:e|ing) the|stain removal|"
    r"blot(?:ting)?|soak(?:ing)? (?:it|the|in)|emergency (?:services|room|department)|call (?:a|an|the) (?:doctor|ambulance|"
    r"plumber|electrician|vet)|warning signs?)\b", re.I)


def _kind(title: str):
    """Which situations an article can advise on, from its title's last word (None: not an everyday article)."""
    from engramm.understand.lex import lexicon
    t = re.sub(r"\s*\([^)]*\)$", "", title).lower()
    words = re.findall(r"[a-z]+", t)
    if not words or len(words) > 4:
        return None
    lx = lexicon("en")
    head = None
    for w in reversed(words):
        rs = [r for r in lx.lookup(w) if r.pos == "n"]
        if rs:
            head = rs[0]
            break
    if head is None:
        return None
    cats = set(head.cats)
    if head.ss in ("state",) or cats & {"ILLNESS"} or "BODY" in head.ev:
        return "HEALTH"
    if cats & {"BODYPART"}:
        return "HEALTH"
    if cats & {"INSECT", "PET"} or head.ss == "animal":
        return "ANIMAL"
    if cats & {"DEVICE", "VEHICLE", "P-VEHICLE", "P-DEVICE", "BUILDPART", "P-BUILDING", "CLOTHING", "FURNITURE",
               "CONTAINER", "TOOL", "KEYTHING"}:
        return "THING"
    if head.ss in ("food", "plant", "substance") or cats & {"FOOD", "DRINK"}:
        return "HOME"
    return None


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--release", default="shelf-20260927")
    ap.add_argument("--repo", default="erithy25/engramm")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--work", type=Path, default=Path("/dev/shm/engramm/shelf"))
    ap.add_argument("--parts", type=int, default=0, help="only the first N parts (for a trial)")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    a.work.mkdir(parents=True, exist_ok=True)
    base = f"https://github.com/{a.repo}/releases/download/{a.release}/"
    listing = subprocess.run(["gh", "api", f"repos/{a.repo}/releases/tags/{a.release}", "--jq", ".assets[].name"],
                             capture_output=True, text=True, check=True).stdout.split()
    parts = sorted({n.split("-")[0] for n in listing if re.fullmatch(r"s\d+-shelf\.json", n)})
    if a.parts:
        parts = parts[: a.parts]
    if a.out.exists():
        a.out.unlink()
    db = sqlite3.connect(a.out)
    db.execute("CREATE TABLE howto(id INTEGER PRIMARY KEY, title TEXT, kind TEXT, text TEXT)")
    db.execute("CREATE VIRTUAL TABLE howto_fts USING fts5(title, text, content='howto', content_rowid='id')")
    total = 0
    for part in parts:
        manifest = json.loads(subprocess.run(["curl", "-sSL", base + f"{part}-shelf.json"], capture_output=True,
                                             text=True, check=True).stdout)
        jobs = []
        for vol in manifest["volumes"]:
            local = a.work / f"{part}-{vol['name']}"
            if not local.exists():
                subprocess.run(["curl", "-sSL", "-o", str(local), base + f"{part}-{vol['name']}"], check=True)
            # split a volume into chunks of buckets for the worker processes
            n = vol["buckets"]
            step = max(1, n // a.jobs + 1)
            for s in range(0, n, step):
                jobs.append((local, s, min(step, n - s)))
        rows = []
        with ProcessPoolExecutor(a.jobs) as ex:
            for res in ex.map(_chunk, jobs):
                rows.extend(res)
        for title, kind, sents in rows:
            db.execute("INSERT INTO howto(title, kind, text) VALUES (?,?,?)", (title, kind, "\n".join(sents)))
        db.commit()
        total += len(rows)
        for vol in manifest["volumes"]:
            (a.work / f"{part}-{vol['name']}").unlink(missing_ok=True)
        print(f"{part}: {len(rows)} articles (total {total})", flush=True)
    db.execute("INSERT INTO howto_fts(howto_fts) VALUES('rebuild')")
    db.commit()
    db.execute("VACUUM")
    db.close()
    print(f"wrote {a.out}: {total} articles, {a.out.stat().st_size / 1e6:.1f} MB")


def _chunk(job):
    path, start, n = job
    from engramm.web.shelf import unpack_bucket
    out = []
    with open(path, "rb") as fh:
        for b in range(start, start + n):
            fh.seek(b * BUCKET)
            data = fh.read(BUCKET)
            if len(data) < 8:
                continue
            try:
                docs = unpack_bucket(data)
            except Exception:
                continue
            for d in docs:
                kind = _kind(d.get("t", ""))
                if not kind:
                    continue
                sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", d.get("x", ""))
                keep = [s.strip() for s in sents if 30 < len(s) < 360 and ADVICE.search(s)]
                if len(keep) >= 2:
                    out.append((d["t"], kind, keep[:8]))
    return out


if __name__ == "__main__":
    main()
