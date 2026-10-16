"""SearchBench-EN v0 command line (docs/PREREG_SEARCH_V0.md, engramm/bench/searchbench.py).

    python -m experiments.searchbench validate --items data/searchbench/items.jsonl
    python -m experiments.searchbench split    --items data/searchbench/items.jsonl --out data/searchbench
    python -m experiments.searchbench verify-seal --test data/searchbench/test.jsonl
    python -m experiments.searchbench run      --items data/searchbench/dev.jsonl --pack <pack> \
                                               --system offline|atlas|atlas-off --out results/searchbench/<x>.jsonl
    python -m experiments.searchbench privacy  --runs results/searchbench/atlas.jsonl --items …
    python -m experiments.searchbench same     --a results/…/offline.jsonl --b results/…/atlas-off.jsonl
    python -m experiments.searchbench sheet    --items … --runs offline=… atlas=… --out rating.html --key key.json
    python -m experiments.searchbench score    --items … --key key.json --ratings r1.json r2.json [r3.json]

``split`` writes dev.jsonl and test.jsonl and the seal (SHA-256 of test.jsonl) into
docs/SEARCHBENCH_SEAL.txt; ``run`` refuses a test file whose seal does not match. ``offline`` is v3
(no network object at all), ``atlas`` switches the shelf and the feeds on (the channels that never send a
question; the Tor messenger of 3.1 is gone), ``web`` adds the web search (it sends the question to a search
engine, so ``privacy`` reports it as leaked by design), ``atlas-off`` is every channel off (criterion S5:
identical to ``offline``).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

from engramm.bench.searchbench import (leaked, load_items, rating_page, rating_rows, same_answers, score, seal, split,
                                       validate, verify_seal, write_items)

ROOT = Path(__file__).resolve().parents[1]
SEAL_FILE = ROOT / "docs" / "SEARCHBENCH_SEAL.txt"


def cmd_validate(a) -> int:
    items = load_items(a.items)
    problems = validate(items, full=not a.partial)
    for p in problems:
        print("✗", p)
    print(f"{len(items)} items, {len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_split(a) -> int:
    items = load_items(a.items)
    problems = validate(items, full=not a.partial)
    if problems:
        print("\n".join("✗ " + p for p in problems))
        print("refusing to split an invalid item file")
        return 1
    dev, test = split(items)
    out = Path(a.out)
    write_items(dev, out / "dev.jsonl")
    write_items(test, out / "test.jsonl")
    digest = seal(out / "test.jsonl")
    SEAL_FILE.write_text(f"{digest}  {out / 'test.jsonl'}\n# sealed before any test run (docs/PREREG_SEARCH_V0.md)\n",
                         encoding="utf-8")
    print(f"dev {len(dev)}, test {len(test)}; seal {digest} → {SEAL_FILE}")
    return 0


def cmd_verify(a) -> int:
    ok = verify_seal(Path(a.test), SEAL_FILE)
    print("seal ok" if ok else "SEAL MISMATCH — the test file changed after sealing")
    return 0 if ok else 1


def _service(pack: str, system: str, state: Path):
    from engramm.app.server import ChatService
    svc = ChatService("unused", pack=Path(pack), memory_path=state / "chat_memory.log")
    svc.load()
    if svc.error:
        raise SystemExit(f"could not load the pack: {svc.error}")
    if system == "offline":
        svc.assistant.atlas = None                 # v3: no network object at all
    elif system in ("atlas", "web"):
        if svc.egress is None:
            raise SystemExit("this build has no network layer")
        svc.egress.set_channel("shelf", enabled=True)
        svc.egress.set_channel("feeds", enabled=True)
        if system == "web":
            svc.egress.set_channel("search", enabled=True)
        svc.atlas.on_settings_changed()
    return svc


def cmd_run(a) -> int:
    items = load_items(a.items)
    if Path(a.items).name == "test.jsonl" and not verify_seal(Path(a.items), SEAL_FILE):
        print("refusing: the test file does not match its seal")
        return 1
    with tempfile.TemporaryDirectory(prefix="searchbench-") as tmp:
        svc = _service(a.pack, a.system, Path(tmp))
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        times = []
        with out.open("w", encoding="utf-8") as f:
            for it in items:
                before = len(svc.egress.log.recent) if svc.egress else 0
                t0 = time.time()
                r = svc.chat(f"sb-{it['id']}", it["question"])        # a fresh conversation per question
                dt = time.time() - t0
                times.append(dt)
                net = svc.egress.log.recent[before:] if svc.egress else []
                src = r.get("source") or {}
                f.write(json.dumps({"id": it["id"], "system": a.system, "text": r.get("text", ""),
                                    "kind": r.get("kind"), "via": r.get("via"),
                                    "source": src.get("url") or src.get("title") or "",
                                    "seconds": round(dt, 3), "network": net}, ensure_ascii=False) + "\n")
    times.sort()
    p95 = times[max(0, int(0.95 * len(times)) - 1)] if times else 0.0
    print(f"{len(items)} answers → {a.out}; median {statistics.median(times) if times else 0:.3f} s, p95 {p95:.3f} s")
    return 0


def _runs(path) -> dict[str, dict]:
    return {json.loads(l)["id"]: json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()}


def cmd_privacy(a) -> int:
    items = {it["id"]: it for it in load_items(a.items)}
    bad = []
    fetches = 0
    for rid, rec in _runs(a.runs).items():
        fetches += len(rec.get("network") or [])
        if rid in items and leaked(items[rid]["question"], rec.get("network") or []):
            bad.append(rid)
    print(f"S4: {len(bad)} answer(s) with question text in a fetch ({fetches} fetches checked)")
    for b in bad:
        print("  ✗", b)
    return 1 if bad else 0


def cmd_same(a) -> int:
    ra = {k: v.get("text", "") for k, v in _runs(a.a).items()}
    rb = {k: v.get("text", "") for k, v in _runs(a.b).items()}
    n, diff = same_answers(ra, rb)
    print(f"S5: {n} / {n + len(diff)} identical")
    for d in diff[:20]:
        print("  ≠", d)
    return 1 if diff else 0


def cmd_sheet(a) -> int:
    items = load_items(a.items)
    runs = {}
    for spec in a.runs:
        name, _, path = spec.partition("=")
        runs[name] = _runs(path)
    rows, key = rating_rows(items, runs)
    Path(a.out).write_text(rating_page(rows), encoding="utf-8")
    Path(a.key).write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(f"{len(rows)} rows → {a.out}; the key (keep it away from raters) → {a.key}")
    return 0


def cmd_score(a) -> int:
    items = load_items(a.items)
    key = json.loads(Path(a.key).read_text(encoding="utf-8"))
    ratings = [json.loads(Path(p).read_text(encoding="utf-8")) for p in a.ratings]
    print(json.dumps(score(items, key, ratings), indent=1, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m experiments.searchbench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--items", required=True)
    v.add_argument("--partial", action="store_true", help="do not check the registered sizes")
    s = sub.add_parser("split")
    s.add_argument("--items", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--partial", action="store_true")
    c = sub.add_parser("verify-seal")
    c.add_argument("--test", required=True)
    r = sub.add_parser("run")
    r.add_argument("--items", required=True)
    r.add_argument("--pack", required=True)
    r.add_argument("--system", choices=("offline", "atlas", "web", "atlas-off"), required=True)
    r.add_argument("--out", required=True)
    p = sub.add_parser("privacy")
    p.add_argument("--runs", required=True)
    p.add_argument("--items", required=True)
    m = sub.add_parser("same")
    m.add_argument("--a", required=True)
    m.add_argument("--b", required=True)
    h = sub.add_parser("sheet")
    h.add_argument("--items", required=True)
    h.add_argument("--runs", nargs="+", required=True, help="name=path …")
    h.add_argument("--out", required=True)
    h.add_argument("--key", required=True)
    o = sub.add_parser("score")
    o.add_argument("--items", required=True)
    o.add_argument("--key", required=True)
    o.add_argument("--ratings", nargs="+", required=True)
    a = ap.parse_args(argv)
    return {"validate": cmd_validate, "split": cmd_split, "verify-seal": cmd_verify, "run": cmd_run,
            "privacy": cmd_privacy, "same": cmd_same, "sheet": cmd_sheet, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
