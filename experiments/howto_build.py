"""Build the how-to index (U3, docs/PREREG_UNDERSTAND_V0.md): practical sentences from the whole of Wikipedia, kept
only for everyday articles (health, body, household things, vehicles, animals, food), with their source.

    python -m experiments.howto_build --release shelf-20260927 --out /dev/shm/engramm/howto.sqlite \
        --json engramm/know/data/howto.json.gz [--work DIR]

Reads the shelf volumes of a release one by one (downloaded, processed, deleted), splits each article into sentences
and keeps those with a practical marker ("can be treated with", "first aid", "should seek medical", "to remove …",
"apply ice" …). An article enters when its title names an everyday thing (the situation lexicon's word classes) and
it has at least two such sentences. Output: SQLite with ``howto(title, kind, text)`` and ``names(name, id)`` (the title and the other names its first
sentence gives: "Urticaria, also known as hives").
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
    r"plumber|electrician|vet)|warning signs?|can be (?:cleaned|removed|unclogged|descaled|sharpened|reset|recharged|"
    r"controlled|eliminated|deterred|trapped|kept away)|(?:is|are) (?:best )?(?:cleaned|stored|kept|removed|controlled) "
    r"(?:with|by|in|using)|should (?:be|not be) (?:stored|kept|cleaned|replaced|checked|watered|fed|given)|"
    r"to (?:remove|clean|unclog|descale|repel|deter|get rid of|keep (?:them|it) away)|control (?:methods|measures)|"
    r"(?:water|feed|prune|repot)(?:ed|ing)? (?:regularly|once|when|every|sparingly)|vinegar|baking soda|bicarbonate|"
    r"dish soap|traps? (?:can|are)|sticky traps?|deterrents?)\b", re.I)


def _kind(title: str):
    """Which situations an article can advise on, from its title (None: not an everyday article). Only common-noun
    titles of at most three words ("Bee sting", "Sprained ankle", "Sunburn"); names and works are left out."""
    from engramm.understand.lex import lexicon
    if "(" in title and not re.search(r"\((?:disease|medicine|medical|condition|plant|food|animal|insect)\)$", title):
        return None                                    # "Battery (tort)", "Fiber (mathematics)": not everyday things
    t = re.sub(r"\s*\([^)]*\)$", "", title)
    words = t.split()
    if not words or len(words) > 3 or any(w[:1].isupper() for w in words[1:]) or re.search(r"[0-9:,&]", t):
        return None
    lx = lexicon("en")
    head = None
    for w in reversed([w.lower() for w in words]):
        rs = [r for r in lx.lookup(w) if r.pos == "n"]
        if rs:
            head = rs[0]
            break
    if head is None:
        return None
    cats = set(head.cats)
    if cats & {"ILLNESS"} or (head.ss in ("state", "process") and ("BODY" in head.ev or "HARM" in head.ev)):
        return "HEALTH"
    if cats & {"BODYPART"} and len(words) > 1:        # "sprained ankle", not "ankle"
        return "HEALTH"
    if cats & {"INSECT"}:
        return "ANIMAL"
    if cats & {"PET", "ANIMAL"} and head.ss == "animal":
        return "ANIMAL"
    if cats & {"PLANT"}:
        return "PLANT"
    if cats & {"FOOD"} or "COOK" in head.ev:
        return "FOOD"
    if cats & {"DEVICE", "VEHICLE", "P-DEVICE", "P-VEHICLE"} or (head.ss == "artifact" and cats & {"ARTIFACT"}):
        return "HOME"
    return None


NOISE = re.compile(r"\[citation|\[\d|%|\b(?:19|20)\d\d\b|\bstud(?:y|ies)\b|\btrials?\b|\bresearch|\bCochrane|"
                   r"\bevidence\b|\bpatients? with\b.*\bsurg|\bFigure\b|\bstage [IV1-4]|\bmice\b|\brats\b|\bp ?<", re.I)
PLAIN = re.compile(r"\b(?:avoid|apply|rest|ice|cold|rinse|wash|clean|seek|see a|doctor|over-the-counter|pain relievers?|"
                   r"painkillers?|ibuprofen|paracetamol|acetaminophen|antihistamines?|usually|most cases|on its own|within|"
                   r"first aid|elevat|compress|bandage|fluids|water|should|recommended|prevent|cream|moistur|sunscreen|vinegar|soap|"
                   r"trap|clean|remove|regularly|replace|check)\b", re.I)
ALIAS = re.compile(r"(?:also|commonly|more commonly|often|sometimes) (?:known|called|referred to) as ((?:the )?[a-z][a-z' -]{2,40}?)"
                   r"(?=[,.;)]| or | is | are )", re.I)


def aliases(title: str, text: str) -> list[str]:
    """Other names from the first sentence: "Urticaria, also known as hives, …" gives "hives"."""
    first = text.split(". ")[0][:400]
    out = [re.sub(r"\s*\([^)]*\)$", "", title).lower()]
    m = re.match(r"([A-Z][a-z' -]{2,40}?),? (?:also|commonly|more commonly|or) ", first)
    if m:
        out.append(m.group(1).lower())
    for x in ALIAS.findall(first):
        out.append(re.sub(r"^the ", "", x.lower()).strip())
    return list(dict.fromkeys(a for a in out if 2 < len(a) < 40))


def advice(text: str) -> list[str]:
    """The practical sentences of an article, plainest first."""
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    keep = [s.strip() for s in sents if 30 < len(s) < 300 and ADVICE.search(s) and not NOISE.search(s)]
    keep.sort(key=lambda s: -len(PLAIN.findall(s)))
    return keep[:6]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--release", default="shelf-20260927")
    ap.add_argument("--repo", default="erithy25/engramm")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--work", type=Path, default=Path("/dev/shm/engramm/shelf"))
    ap.add_argument("--parts", type=int, default=0, help="only the first N parts (for a trial)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--json", type=Path, help="also write the compact form the app reads (engramm/know/data/howto.json.gz)")
    ap.add_argument("--export-only", action="store_true", help="only write --json from an existing --out database")
    a = ap.parse_args(argv)
    if a.export_only:
        export(sqlite3.connect(a.out), a.json)
        return
    a.work.mkdir(parents=True, exist_ok=True)
    base = f"https://github.com/{a.repo}/releases/download/{a.release}/"
    listing = subprocess.run(["gh", "api", f"repos/{a.repo}/releases/tags/{a.release}", "--jq", ".assets[].name"],
                             capture_output=True, text=True, check=True).stdout.split()
    parts = sorted({n.split("-")[0] for n in listing if re.fullmatch(r"s\d+-shelf\.json", n)})
    if a.parts:
        parts = parts[: a.parts]
    db = sqlite3.connect(a.out)                # resumable: parts already in the file are skipped
    db.execute("CREATE TABLE IF NOT EXISTS howto(id INTEGER PRIMARY KEY, title TEXT, kind TEXT, text TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS names(name TEXT, id INTEGER)")
    db.execute("CREATE TABLE IF NOT EXISTS done(part TEXT PRIMARY KEY)")
    finished = {r[0] for r in db.execute("SELECT part FROM done")}
    total = db.execute("SELECT count(*) FROM howto").fetchone()[0]
    curl = ["curl", "-sSL", "--retry", "8", "--retry-all-errors", "--retry-delay", "4"]
    for part in parts:
        if part in finished:
            continue
        manifest = json.loads(subprocess.run(curl + [base + f"{part}-shelf.json"], capture_output=True,
                                             text=True, check=True).stdout)
        jobs = []
        for vol in manifest["volumes"]:
            local = a.work / f"{part}-{vol['name']}"
            if not local.exists():
                subprocess.run(curl + ["-C", "-", "-o", str(local), base + f"{part}-{vol['name']}"], check=True)
            # split a volume into chunks of buckets for the worker processes
            n = vol["buckets"]
            step = max(1, n // a.jobs + 1)
            for s in range(0, n, step):
                jobs.append((local, s, min(step, n - s)))
        rows = []
        with ProcessPoolExecutor(a.jobs) as ex:
            for res in ex.map(_chunk, jobs):
                rows.extend(res)
        for title, kind, names, sents in rows:
            cur = db.execute("INSERT INTO howto(title, kind, text) VALUES (?,?,?)", (title, kind, "\n".join(sents)))
            db.executemany("INSERT INTO names VALUES (?,?)", [(n, cur.lastrowid) for n in names.split("|")])
        db.execute("INSERT INTO done VALUES (?)", (part,))
        db.commit()
        total += len(rows)
        for vol in manifest["volumes"]:
            (a.work / f"{part}-{vol['name']}").unlink(missing_ok=True)
        print(f"{part}: {len(rows)} articles (total {total})", flush=True)
    db.execute("CREATE INDEX IF NOT EXISTS names_name ON names(name)")
    db.commit()
    db.execute("VACUUM")
    if a.json:
        export(db, a.json)
    db.close()
    print(f"wrote {a.out}: {total} articles, {a.out.stat().st_size / 1e6:.1f} MB")


def export(db, path: Path) -> None:
    """The compact form; the kind is derived again from the title, so a stricter _kind applies without a new scan."""
    from engramm.know.howto import save
    names = {}
    for n, i in db.execute("SELECT name, id FROM names"):
        names.setdefault(i, []).append(n)
    items = []
    for i, t, k, x in db.execute("SELECT id, title, kind, text FROM howto"):
        k2 = _kind(t)
        if k2:
            items.append((t, k2, names.get(i, []), x.split("\n")))
    save(items, path)
    print(f"wrote {path}: {len(items)} articles, {path.stat().st_size / 1e6:.2f} MB")


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
                keep = advice(d.get("x", ""))
                if len(keep) >= 2:
                    out.append((d["t"], kind, "|".join(aliases(d["t"], d.get("x", ""))), keep))
    return out


if __name__ == "__main__":
    main()
