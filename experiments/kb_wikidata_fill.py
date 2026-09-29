"""Fill the fact bank from Wikidata (CC0) for the entities people ask about most.

DBpedia's infobox mappings miss articles without a standard infobox (Mozart, the Odyssey, the
Harry Potter books) and many values (Napoleon's birth date, Mount Everest's height, current heads
of state). This job asks Wikidata's public query service for the most-referenced Wikipedia titles
in batches, and merges the answers into the fact bank; where Wikidata has a property, its values
are preferred (they are current as of the build date).

    python -u -m experiments.kb_wikidata_fill titles --top 150000
    python -u -m experiments.kb_wikidata_fill fetch  --workers 2
    python -u -m experiments.kb_wikidata_fill merge  --kb /dev/shm/engramm/kb/final/kb.sqlite

Every batch is stored as it arrives (``wd/batch_*.jsonl``), so a stopped fetch continues where
it stopped. Queries carry a descriptive User-Agent and run at most two at a time, as the query
service's usage policy asks.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

WORK = Path("/dev/shm/engramm/kb")
ENDPOINT = "https://query.wikidata.org/sparql"
UA = "ENGRAMM-research/0.1 (offline assistant knowledge build; github.com/erithy25/engramm) Python-urllib"
# Wikidata property → fact bank property
ITEM_PROPS = {"P19": "birthPlace", "P20": "deathPlace", "P509": "deathCause", "P119": "restingPlace",
              "P26": "spouse", "P22": "parent", "P25": "parent", "P40": "child", "P106": "occupation",
              "P27": "nationality", "P69": "almaMater", "P800": "notableWork", "P102": "party",
              "P1303": "instrument", "P36": "capital", "P35": "headOfState", "P6": "headOfGovernment",
              "P38": "currency", "P37": "officialLanguage", "P30": "continent", "P17": "country",
              "P131": "location", "P4552": "mountainRange", "P403": "riverMouth", "P50": "author",
              "P57": "director", "P86": "composer", "P170": "artist", "P175": "artist", "P161": "starring",
              "P162": "producer", "P123": "publisher", "P178": "developer", "P176": "manufacturer",
              "P84": "architect", "P112": "founder", "P159": "headquarter", "P169": "keyPerson",
              "P61": "inventor", "P136": "genre", "P85": "anthem", "P1412": "language"}
TIME_PROPS = {"P569": "birthDate", "P570": "deathDate", "P571": "foundingDate", "P577": "releaseDate",
              "P580": "startDate", "P582": "endDate", "P585": "date"}
QUANTITY_PROPS = {"P1082": "populationTotal", "P2046": "areaTotal", "P2044": "elevation", "P2043": "length",
                  "P2048": "height", "P1128": "numberOfEmployees", "P1120": "numberOfDeaths"}
TYPE_WORDS = [  # instance-of label → fact bank type (first match wins)
    ("human", "Person"), ("sovereign state", "Country"), ("country", "Country"), ("capital city", "City"),
    ("big city", "City"), ("city", "City"), ("town", "Town"), ("village", "Village"), ("mountain", "Mountain"),
    ("volcano", "Volcano"), ("river", "River"), ("lake", "Lake"), ("sea", "Sea"), ("ocean", "Sea"),
    ("island", "Island"), ("continent", "Continent"), ("feature film", "Film"), ("film", "Film"),
    ("television series", "TelevisionShow"), ("literary work", "Book"), ("novel", "Book"), ("book series", "Book"),
    ("epic poem", "Poem"), ("poem", "Poem"), ("play", "Play"), ("opera", "Opera"), ("studio album", "Album"),
    ("album", "Album"), ("single", "Single"), ("song", "Song"), ("painting", "Painting"), ("sculpture", "Sculpture"),
    ("video game", "VideoGame"), ("software", "Software"), ("business", "Company"), ("public company", "Company"),
    ("enterprise", "Company"), ("company", "Company"), ("musical group", "Band"), ("rock band", "Band"),
    ("band", "Band"), ("university", "University"), ("skyscraper", "Building"), ("tower", "Tower"),
    ("building", "Building"), ("bridge", "Bridge"), ("castle", "Castle"), ("museum", "Museum"),
    ("political party", "PoliticalParty"), ("organization", "Organisation"), ("war", "MilitaryConflict"),
    ("battle", "MilitaryConflict"), ("historical period", "Event"), ("event", "Event"),
    ("chemical element", "ChemicalElement"), ("planet", "Planet"), ("star", "Star"), ("galaxy", "Galaxy")]


def sparql(query: str, retries: int = 5) -> dict:
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    delay = 5.0
    for attempt in range(retries):
        req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": UA,
                                                                   "Accept": "application/sparql-results+json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                wait = float(e.headers.get("Retry-After") or delay)
                time.sleep(min(wait, 120))
                delay *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("query failed after retries")


def _lit(title: str) -> str:
    return '"' + title.replace("\\", "\\\\").replace('"', '\\"') + '"@en'


def batch_query(titles: list[str]) -> str:
    values = " ".join(_lit(t) for t in titles)
    items = " ".join(f"wdt:{p}" for p in ITEM_PROPS)
    label = '?val rdfs:label ?valLabel . FILTER(LANG(?valLabel) = "en")'
    parts = [f"{{ VALUES ?p {{ {items} }} ?item ?p ?val . FILTER(isIRI(?val)) {label} }}",
             f"{{ ?item wdt:P31 ?val . BIND(wdt:P31 AS ?p) {label} }}"]
    for p in TIME_PROPS:
        parts.append(f"{{ ?item p:{p} ?st . ?st wikibase:rank ?rank ; psv:{p} ?tv . ?tv wikibase:timeValue ?time ; "
                     f"wikibase:timePrecision ?prec . FILTER(?rank != wikibase:DeprecatedRank) BIND(wdt:{p} AS ?p) }}")
    for p in QUANTITY_PROPS:
        if p in ("P1082", "P1128", "P1120"):
            parts.append(f"{{ ?item wdt:{p} ?amount . BIND(wdt:{p} AS ?p) }}")
        else:
            parts.append(f"{{ ?item p:{p} ?st . ?st wikibase:rank ?rank ; psn:{p}/wikibase:quantityAmount ?amount . "
                         f"FILTER(?rank != wikibase:DeprecatedRank) BIND(wdt:{p} AS ?p) }}")
    union = " UNION ".join(parts)
    return f"""SELECT ?title ?item ?p ?val ?valLabel ?time ?prec ?amount ?rank WHERE {{
  VALUES ?title {{ {values} }}
  ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?title .
  {union}
}}"""


def cmd_titles(args) -> None:
    inbound: Counter = Counter()
    with open(WORK / "facts.tsv", encoding="utf-8") as f:
        for line in f:
            s, p, v, dt, ent = line.rstrip("\n").split("\t")
            if ent == "1":
                inbound[v] += 1
    import bz2
    redirects: Counter = Counter()
    rx = re.compile(r'^<http://dbpedia\.org/resource/([^>]+)> <http://dbpedia\.org/ontology/wikiPageRedirects> '
                    r'<http://dbpedia\.org/resource/([^>]+)> \.$')
    with bz2.open(WORK / "redirects.ttl.bz2", "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = rx.match(line.rstrip("\n"))
            if m:
                redirects[urllib.parse.unquote(m.group(2)).replace("_", " ")] += 1
    score = Counter()
    for t, c in inbound.items():
        score[t] += c
    for t, c in redirects.items():
        score[t] += c
    top = [t for t, _ in score.most_common(args.top) if "\t" not in t and not t.startswith(("List of", "Category:"))]
    (WORK / "wd").mkdir(exist_ok=True)
    (WORK / "wd" / "titles.json").write_text(json.dumps({"titles": top, "score": {t: score[t] for t in top}}))
    print(f"{len(top):,} titles; top: {top[:20]}", flush=True)


def _fetch_one(k: int, titles: list[str]) -> tuple[int, int]:
    out = WORK / "wd" / f"batch_{k:05d}.jsonl"
    if out.exists():
        return k, -1
    res = sparql(batch_query(titles))
    rows = []
    for b in res["results"]["bindings"]:
        g = {key: v["value"] for key, v in b.items()}
        rows.append(g)
    tmp = out.with_suffix(".part")
    tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    tmp.replace(out)
    return k, len(rows)


def cmd_fetch(args) -> None:
    titles = json.loads((WORK / "wd" / "titles.json").read_text())["titles"]
    batches = [titles[i:i + args.batch] for i in range(0, len(titles), args.batch)]
    t0, done, rows = time.time(), 0, 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_fetch_one, k, b): k for k, b in enumerate(batches)}
        for fu in cf.as_completed(futs):
            try:
                k, n = fu.result()
            except Exception as e:           # a failed batch is retried by the next run
                print(f"batch {futs[fu]} failed: {e}", flush=True)
                continue
            done += 1
            rows += max(n, 0)
            if done % 50 == 0 or done == len(batches):
                el = time.time() - t0
                print(f"{done}/{len(batches)} batches, {rows:,} rows, {el:.0f} s "
                      f"(~{el / done * (len(batches) - done) / 60:.0f} min left)", flush=True)


def _type_of(labels: list[str]) -> str | None:
    low = [x.lower() for x in labels]
    for word, t in TYPE_WORDS:
        if word in low:
            return t
    for word, t in TYPE_WORDS:
        if any(word in x for x in low):
            return t
    return None


_SINGLE = frozenset(("birthDate", "deathDate", "foundingDate", "releaseDate", "elevation", "areaTotal", "length",
                     "height", "populationTotal", "numberOfEmployees", "numberOfDeaths", "startDate", "endDate", "date"))


def _rank(r: dict) -> int:
    rank = r.get("rank", "")
    return 2 if rank.endswith("PreferredRank") else 1


def cmd_merge(args) -> None:
    titles_meta = json.loads((WORK / "wd" / "titles.json").read_text())
    score = titles_meta["score"]
    per: dict[str, dict] = {}
    for path in sorted((WORK / "wd").glob("batch_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            t = r["title"]
            e = per.setdefault(t, {"qid": r["item"].rsplit("/", 1)[-1], "facts": [], "types": [], "ranked": []})
            p = r["p"].rsplit("/", 1)[-1]
            if p == "P31":
                if r.get("valLabel"):
                    e["types"].append(r["valLabel"])
            elif p in ITEM_PROPS:
                if r.get("valLabel") and not re.fullmatch(r"Q\d+", r["valLabel"]):
                    e["facts"].append((ITEM_PROPS[p], r["valLabel"], "entity"))
            elif p in TIME_PROPS and r.get("time"):
                prec = int(r.get("prec", 11))
                m = re.match(r"^(-?)(\d+)-(\d{2})-(\d{2})", r["time"])
                if not m or prec < 9:
                    continue
                neg, y, mo, d = m.groups()
                y = f"{neg}{int(y):04d}"
                v, dt = (f"{y}-{mo}-{d}", "date") if prec >= 11 else ((f"{y}-{mo}", "gYearMonth") if prec == 10
                                                                    else (y, "gYear"))
                e["ranked"].append((TIME_PROPS[p], _rank(r), prec, v, dt))
            elif p in QUANTITY_PROPS and r.get("amount"):
                e["ranked"].append((QUANTITY_PROPS[p], _rank(r), 0, r["amount"].lstrip("+"), "double"))
    for e in per.values():
        # dates and quantities: the best rank only (preferred over normal), dates at their best precision
        best: dict[str, tuple] = {}
        for prop, rank, prec, v, dt in e["ranked"]:
            key = (rank, prec)
            if prop not in best or key > best[prop][0]:
                best[prop] = (key, [(v, dt)])
            elif key == best[prop][0] and (v, dt) not in best[prop][1]:
                best[prop][1].append((v, dt))
        for prop, (_, vals) in best.items():
            for v, dt in (vals[:1] if prop in _SINGLE else vals):
                e["facts"].append((prop, v, dt))
    print(f"entities from Wikidata: {len(per):,}", flush=True)
    db = sqlite3.connect(args.kb)
    cols = [c[1] for c in db.execute("PRAGMA table_info(fact)")]
    if "src" not in cols:
        db.execute("ALTER TABLE fact ADD COLUMN src TEXT")
    db.execute("DELETE FROM fact WHERE src = 'wikidata'")
    ids = dict(db.execute("SELECT title, id FROM entity"))
    next_id = (db.execute("SELECT MAX(id) FROM entity").fetchone()[0] or 0) + 1
    new_entities, n_facts = 0, 0
    for t, e in per.items():
        if not e["facts"]:
            continue
        eid = ids.get(t)
        etype = _type_of(e["types"])
        if eid is None:
            eid = next_id
            next_id += 1
            ids[t] = eid
            db.execute("INSERT INTO entity VALUES (?,?,?,?)", (eid, t, etype, int(score.get(t, 1))))
            db.execute("INSERT INTO alias VALUES (?,?,0)", (t.lower(), eid))
            base = re.sub(r"\s*\([^)]*\)$", "", t)
            if base != t:
                db.execute("INSERT INTO alias VALUES (?,?,1)", (base.lower(), eid))
            new_entities += 1
        elif etype:
            db.execute("UPDATE entity SET type = COALESCE(type, ?) WHERE id = ?", (etype, eid))
        seen = set()
        for prop, v, dt in e["facts"]:
            if (prop, v) in seen:
                continue
            seen.add((prop, v))
            db.execute("INSERT INTO fact(entity, prop, value, dtype, value_entity, src) VALUES (?,?,?,?,?, 'wikidata')",
                       (eid, prop, v, dt, ids.get(v) if dt == "entity" else None))
            n_facts += 1
    # redirects for the new entities
    if new_entities:
        import bz2
        rx = re.compile(r'^<http://dbpedia\.org/resource/([^>]+)> <http://dbpedia\.org/ontology/wikiPageRedirects> '
                        r'<http://dbpedia\.org/resource/([^>]+)> \.$')
        have = set(r[0] for r in db.execute("SELECT DISTINCT entity FROM alias WHERE kind = 2"))
        rows = []
        with bz2.open(WORK / "redirects.ttl.bz2", "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = rx.match(line.rstrip("\n"))
                if not m:
                    continue
                tgt = urllib.parse.unquote(m.group(2)).replace("_", " ")
                eid = ids.get(tgt)
                if eid is not None and eid not in have:
                    name = urllib.parse.unquote(m.group(1)).replace("_", " ").lower()
                    if len(name.split()) <= 6:
                        rows.append((name, eid, 2))
        db.executemany("INSERT INTO alias VALUES (?,?,?)", rows)
    meta = {k: json.loads(v) for k, v in db.execute("SELECT key, value FROM meta")}
    meta["wikidata"] = {"entities": len(per), "new_entities": new_entities, "facts": n_facts,
                        "fetched": time.strftime("%Y-%m-%d"), "license": "CC0"}
    db.execute("INSERT OR REPLACE INTO meta VALUES ('wikidata', ?)", (json.dumps(meta["wikidata"]),))
    db.commit()
    db.execute("VACUUM")
    db.close()
    print(json.dumps(meta["wikidata"]), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("titles")
    a.add_argument("--top", type=int, default=150000)
    b = sub.add_parser("fetch")
    b.add_argument("--workers", type=int, default=2)
    b.add_argument("--batch", type=int, default=100)
    c = sub.add_parser("merge")
    c.add_argument("--kb", type=Path, default=WORK / "final" / "kb.sqlite")
    args = ap.parse_args()
    {"titles": cmd_titles, "fetch": cmd_fetch, "merge": cmd_merge}[args.cmd](args)


if __name__ == "__main__":
    main()
