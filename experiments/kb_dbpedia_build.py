"""Build ENGRAMM's fact bank (K2) from DBpedia 2022.12 (English): infobox facts about Wikipedia
entities, keyed by Wikipedia title — the same titles as ENGRAMM's reading, so no separate entity
mapping is needed. License: CC BY-SA 3.0 / GFDL, like Wikipedia itself.

    python -u -m experiments.kb_dbpedia_build --work /dev/shm/engramm/kb --out models/lm/main/kb.sqlite

Steps (each file is streamed and decompressed on the fly, never stored whole):
1. mappingbased objects and literals: keep the properties in ``PROPS`` (people, places,
   works, organisations — the facts people ask about);
2. instance types: the most specific DBpedia class of each entity (Person, City, Country, …);
3. redirects: other names of an entity ("USA" → United States), used for linking;
4. popularity: how often other facts point to the entity, plus its number of redirects;
5. everything goes into one SQLite file (entity, alias, fact) with indexes — read with little
   memory, by Python now and by the Rust runtime later.

Only entities that carry at least one kept fact are stored. Sizes and counts are printed and
written to ``kb_meta.json`` next to the database.
"""

from __future__ import annotations

import argparse
import bz2
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

BASE = "https://downloads.dbpedia.org/repo/dbpedia/"
VERSION = "2022.12.01"
FILES = {
    "objects": f"mappings/mappingbased-objects/{VERSION}/mappingbased-objects_lang=en.ttl.bz2",
    "literals": f"mappings/mappingbased-literals/{VERSION}/mappingbased-literals_lang=en.ttl.bz2",
    "types": f"mappings/instance-types/{VERSION}/instance-types_lang=en_specific.ttl.bz2",
    "redirects": f"generic/redirects/{VERSION}/redirects_lang=en.ttl.bz2",
}
UA = "ENGRAMM-research/0.1 (offline assistant knowledge build; github.com/erithy25/engramm)"

# properties kept (DBpedia ontology names) — what people ask about
PROPS = frozenset("""
birthDate deathDate birthPlace deathPlace birthYear deathYear birthName nationality citizenship occupation
spouse parent child relative almaMater education knownFor notableWork award field influencedBy restingPlace
deathCause religion party position team sport
capital largestCity country location locatedInArea state region continent city county
populationTotal populationMetro populationUrban areaTotal elevation maximumElevation height length width depth
officialLanguage language currency leader leaderName president primeMinister monarch mayor governor
anthem motto demonym timeZone foundingDate foundingYear founder foundedBy keyPerson headquarter numberOfEmployees
industry product owner parentCompany subsidiary
author writer director producer starring musicComposer composer artist creator illustrator publisher developer
manufacturer designer architect builder operator distributor recordLabel genre releaseDate publicationDate
runtime numberOfPages numberOfEpisodes numberOfSeasons network channel
discoverer inventor openingDate completionDate formationDate
mountainRange riverMouth sourceMountain mouthMountain river discharge
alias nickname
successor predecessor vicePresident
instrument bandMember formerBandMember associatedBand associatedMusicalArtist
mass weight wingspan
""".split())
_TRIPLE = re.compile(r'^<http://dbpedia\.org/resource/([^>]+)> <http://dbpedia\.org/ontology/([A-Za-z]+)> '
                     r'(?:<http://dbpedia\.org/resource/([^>]+)>|"((?:[^"\\]|\\.)*)"(?:\^\^<([^>]+)>|@([a-z-]+))?) \.$')
_TYPE = re.compile(r'^<http://dbpedia\.org/resource/([^>]+)> <http://www\.w3\.org/1999/02/22-rdf-syntax-ns#type> '
                   r'<http://dbpedia\.org/ontology/([A-Za-z]+)> \.$')
_REDIRECT = re.compile(r'^<http://dbpedia\.org/resource/([^>]+)> <http://dbpedia\.org/ontology/wikiPageRedirects> '
                       r'<http://dbpedia\.org/resource/([^>]+)> \.$')


def title(uri_part: str) -> str:
    return urllib.parse.unquote(uri_part).replace("_", " ")


def unescape(lit: str) -> str:
    return lit.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8") if "\\" in lit else lit


def stream_lines(url: str, cache: Path | None = None):
    """Lines of a remote .bz2 file. The download is kept in the work directory (``cache``) so a
    second pass reads it locally; lines are decompressed on the fly either way."""
    if cache is not None and not cache.exists():
        part = cache.with_suffix(".part")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r, open(part, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        part.replace(cache)
    with bz2.open(cache, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line.rstrip("\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, default=Path("/dev/shm/engramm/kb"))
    ap.add_argument("--out", type=Path, default=Path("models/lm/main/kb.sqlite"))
    ap.add_argument("--min-popularity", type=int, default=2,
                    help="keep entities that other facts point to at least this often (or that have redirects)")
    args = ap.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cache = {k: args.work / (k + ".ttl.bz2") for k in FILES}

    # pass 1: kept facts to a work file; counts of how often each entity is pointed to
    inbound: Counter = Counter()
    subjects: set[str] = set()
    kept_props: Counter = Counter()
    facts_path = args.work / "facts.tsv"
    n_facts = 0
    with open(facts_path, "w", encoding="utf-8") as out_f:
        for key in ("objects", "literals"):
            n = 0
            for line in stream_lines(BASE + FILES[key], cache[key]):
                n += 1
                m = _TRIPLE.match(line)
                if not m:
                    continue
                s_, p, o_ent, o_lit, dtype, lang = m.groups()
                if p not in PROPS:
                    continue
                st = title(s_)
                if o_ent is not None:
                    ot = title(o_ent)
                    row = (st, p, ot, "entity", "1")
                    inbound[ot] += 1
                else:
                    if lang not in (None, "en"):
                        continue
                    dt_ = dtype.rsplit("#", 1)[-1].rsplit("/", 1)[-1] if dtype else "string"
                    row = (st, p, unescape(o_lit), dt_, "0")
                if any("\t" in x or "\n" in x for x in row[:3]):
                    continue
                out_f.write("\t".join(row) + "\n")
                subjects.add(st)
                kept_props[p] += 1
                n_facts += 1
            print(f"{key}: {n:,} lines, {n_facts:,} facts kept so far ({time.time() - t0:.0f} s)", flush=True)

    # redirects: how many other names each entity has (pass 1), the names themselves later
    n_redirects: Counter = Counter()
    for line in stream_lines(BASE + FILES["redirects"], cache["redirects"]):
        m = _REDIRECT.match(line)
        if m:
            tgt = title(m.group(2))
            if tgt in subjects:
                n_redirects[tgt] += 1
    print(f"redirects counted ({time.time() - t0:.0f} s)", flush=True)
    keep = sorted(e for e in subjects if inbound.get(e, 0) + n_redirects.get(e, 0) >= args.min_popularity)
    ids = {e: i for i, e in enumerate(keep, 1)}
    pop = {e: inbound.get(e, 0) + n_redirects.get(e, 0) for e in keep}
    del subjects
    print(f"kept entities (popularity ≥ {args.min_popularity}): {len(ids):,}", flush=True)

    types: dict[str, str] = {}
    for line in stream_lines(BASE + FILES["types"], cache["types"]):
        m = _TYPE.match(line)
        if m:
            t = title(m.group(1))
            if t in ids:
                types[t] = m.group(2)
    print(f"types: {len(types):,} ({time.time() - t0:.0f} s)", flush=True)

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.work / "kb.sqlite"
    if tmp.exists():
        tmp.unlink()
    db = sqlite3.connect(tmp)
    db.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; PRAGMA page_size=4096;
        CREATE TABLE entity(id INTEGER PRIMARY KEY, title TEXT NOT NULL, type TEXT, popularity INTEGER NOT NULL);
        CREATE TABLE alias(name TEXT NOT NULL, entity INTEGER NOT NULL, kind INTEGER NOT NULL);
        CREATE TABLE fact(entity INTEGER NOT NULL, prop TEXT NOT NULL, value TEXT NOT NULL, dtype TEXT NOT NULL,
                          value_entity INTEGER);
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    db.executemany("INSERT INTO entity VALUES (?,?,?,?)", ((i, e, types.get(e), pop[e]) for e, i in ids.items()))
    del types

    def alias_rows():
        for e, i in ids.items():
            yield e.lower(), i, 0
            base = re.sub(r"\s*\([^)]*\)$", "", e)
            if base != e:
                yield base.lower(), i, 1
        for line in stream_lines(BASE + FILES["redirects"], cache["redirects"]):
            m = _REDIRECT.match(line)
            if m:
                i = ids.get(title(m.group(2)))
                if i is not None:
                    yield title(m.group(1)).lower(), i, 2
    db.executemany("INSERT INTO alias VALUES (?,?,?)", alias_rows())
    n_alias = db.execute("SELECT COUNT(*) FROM alias").fetchone()[0]
    print(f"aliases: {n_alias:,} ({time.time() - t0:.0f} s)", flush=True)

    def fact_rows():
        with open(facts_path, encoding="utf-8") as f:
            for line in f:
                s_, p, v, dt_, ent = line.rstrip("\n").split("\t")
                i = ids.get(s_)
                if i is not None:
                    yield i, p, v, dt_, ids.get(v) if ent == "1" else None
    db.executemany("INSERT INTO fact VALUES (?,?,?,?,?)", fact_rows())
    n_fact_rows = db.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
    print(f"facts: {n_fact_rows:,} ({time.time() - t0:.0f} s)", flush=True)
    db.executescript("""
        CREATE INDEX alias_name ON alias(name);
        CREATE INDEX fact_entity ON fact(entity, prop);
        CREATE INDEX fact_value ON fact(value_entity, prop);
        CREATE UNIQUE INDEX entity_title ON entity(title);
    """)
    meta = {"source": "DBpedia " + VERSION + " (English), CC BY-SA 3.0 / GFDL", "entities": len(ids),
            "aliases": n_alias, "facts": n_fact_rows, "props": dict(kept_props.most_common()),
            "min_popularity": args.min_popularity, "seconds": round(time.time() - t0)}
    db.executemany("INSERT INTO meta VALUES (?,?)", [(k, json.dumps(v)) for k, v in meta.items()])
    db.commit()
    db.execute("VACUUM")
    db.close()
    if tmp.resolve() != out.resolve():
        import shutil
        shutil.move(str(tmp), str(out))
    meta["bytes"] = out.stat().st_size
    (out.parent / "kb_meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps({k: v for k, v in meta.items() if k != "props"}, indent=1), flush=True)


if __name__ == "__main__":
    main()
