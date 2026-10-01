"""Confidence for answers from the network channels (engramm/web/atlas_calib.json), learnt by
counting like engramm/chat/calib.py — on spent development data only (SQuAD v1.1 train).

The local confidence model was learnt on article leads; full articles fetched from the shelf look
different (the title is in every question, many sentences per article), so it refuses most
correct shelf answers. This script counts the same feature strings on shelf answers instead:

    fetch     the current text of the SQuAD train articles (their Wikipedia pages, main text by
              engramm/web/clean.py, one request every 2 s) → data/cache/atlas/squad_articles.jsonl
    shelf     a development shelf: those articles among the distractors of one Cirrus shard
    examples  every sampled question through the real Atlas path (shelf search with decoys over a
              local server, sentence choice, extraction) → features + exactly right or not
    train     averaged perceptron on 80 % of the articles; θ on the other 20 % (the lowest θ with
              exactness ≥ the target there) → engramm/web/atlas_calib.json

    python experiments/atlas_calib.py fetch
    python experiments/atlas_calib.py shelf --distractors /dev/shm/engramm/cirrus0/out/docs-00000.jsonl
    python experiments/atlas_calib.py examples --pack /dev/shm/engramm/pack-b3 --per-article 25 --workers 3
    python experiments/atlas_calib.py train --target 0.9
"""

from __future__ import annotations

import argparse
import json
import os
import re
import string
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CACHE = ROOT / "data" / "cache" / "atlas"
SQUAD = ROOT / "data" / "cache" / "chat" / "train-v1.1.json"
OUT = ROOT / "engramm" / "web" / "atlas_calib.json"
WORK = Path(os.environ.get("ATLAS_WORK", "/dev/shm/engramm/atlas_work"))
UA = "ENGRAMM-research/0.1 (offline assistant knowledge build; github.com/erithy25/engramm)"


# -- SQuAD answer normalisation (the official evaluation script) ----------------------------------

def normalize_answer(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def exact(pred: str | None, golds: list[str]) -> bool:
    return pred is not None and any(normalize_answer(pred) == normalize_answer(g) for g in golds)


def token_f1(pred: str | None, golds: list[str]) -> float:
    """The official SQuAD token F1 (best over the gold answers)."""
    best = 0.0
    pt = normalize_answer(pred or "").split()
    for g in golds:
        gt = normalize_answer(g).split()
        common = sum((Counter(pt) & Counter(gt)).values())
        if common:
            best = max(best, 2 * common / (len(pt) + len(gt)))
    return best


def squad_articles() -> list[dict]:
    return json.loads(SQUAD.read_text(encoding="utf-8"))["data"]


# -- fetch ----------------------------------------------------------------------------------------

def fetch(out: Path, delay: float) -> None:
    from engramm.web.clean import paragraphs, strip_references
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            done.add(json.loads(line)["squad"])
    arts = squad_articles()
    with out.open("a", encoding="utf-8") as f:
        for k, a in enumerate(arts):
            key = a["title"]
            if key in done:
                continue
            url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(urllib.parse.unquote(key))  # titles come encoded
            page = None
            for attempt in range(4):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=60) as r:
                        page = r.read().decode("utf-8", "replace")
                        final = urllib.parse.unquote(r.geturl().rsplit("/wiki/", 1)[-1])
                    break
                except urllib.error.HTTPError as e:
                    print(f"[fetch] {key}: {e}", flush=True)
                    if e.code == 404:
                        break
                    time.sleep(delay * 10 * (attempt + 1))   # rate limits: wait longer, then retry
                except Exception as e:
                    print(f"[fetch] {key}: {e}", flush=True)
                    time.sleep(delay * 10 * (attempt + 1))
            if page is None:
                continue
            m = re.search(r'<h1[^>]*id="firstHeading"[^>]*>(.*?)</h1>', page, re.S)
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else final.replace("_", " ")
            paras = [p for p in paragraphs(page) if not (len(p) <= 150 and not p.endswith((".", "!", "?")))]
            text = strip_references("\n".join(paras))
            f.write(json.dumps({"squad": key, "t": title, "s": "wiki", "x": text, "d": time.strftime("%Y-%m-%d")},
                               ensure_ascii=False) + "\n")
            f.flush()
            print(f"[fetch] {k + 1}/{len(arts)} {title}: {len(text)} chars", flush=True)
            time.sleep(delay)


# -- shelf ----------------------------------------------------------------------------------------

def shelf(articles: Path, distractors: Path, out: Path, workers: int) -> None:
    from experiments.shelf_build import build
    arts = [json.loads(line) for line in articles.read_text(encoding="utf-8").splitlines()]
    titles = {a["t"] for a in arts}
    mixed = out.parent / (out.name + "_docs.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with mixed.open("w", encoding="utf-8") as f:
        for a in arts:
            f.write(json.dumps({"t": a["t"], "s": "wiki", "x": a["x"], "d": a["d"]}, ensure_ascii=False) + "\n")
            n += 1
        with distractors.open(encoding="utf-8") as src:
            for line in src:
                if json.loads(line)["t"] not in titles:
                    f.write(line)
                    n += 1
    build([mixed], [], out, workers=workers, total_hint=n)
    mixed.unlink()


# -- examples -------------------------------------------------------------------------------------

class _Range(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        path = Path(self.directory) / self.path.lstrip("/")
        if not path.is_file():
            self.send_error(404)
            return
        size = path.stat().st_size
        a, b, code = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng:
            x, y = rng.split("=")[1].split("-")
            a, b, code = int(x), min(int(y), size - 1), 206
        with open(path, "rb") as f:
            f.seek(a)
            data = f.read(b - a + 1)
        self.send_response(code)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _sample(per_article: int, part: int, parts: int) -> list[dict]:
    """Questions (id, question, answers, article), every article's first ``per_article`` in a fixed
    order; worker ``part`` of ``parts`` takes every parts-th article."""
    out = []
    for k, a in enumerate(squad_articles()):
        if k % parts != part:
            continue
        qs = [(qa["id"], qa["question"], [x["text"] for x in qa["answers"]]) for p in a["paragraphs"] for qa in p["qas"]]
        qs.sort(key=lambda q: q[0])
        for qid, q, ans in qs[:per_article]:
            out.append({"id": qid, "q": q, "answers": ans, "article": a["title"]})
    return out


def examples_worker(pack: Path, shelf_dir: Path, per_article: int, part: int, parts: int, out: Path) -> None:
    import engramm.chat.bot as botmod
    from engramm.app.server import ChatService
    from engramm.chat import calib
    work = WORK / f"work{part}"            # bucket cache and settings: on a RAM disk, not next to the repo
    work.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Range, directory=str(shelf_dir)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    overlay = work / "pack"
    overlay.mkdir(exist_ok=True)
    for f in pack.iterdir():
        if not (overlay / f.name).exists() and f.name not in ("dl.log", "dl.pid"):
            (overlay / f.name).symlink_to(f)
    for name in ("shelf_index", "shelf.json"):
        if (overlay / name).is_symlink():
            (overlay / name).unlink()
        (overlay / name).symlink_to(shelf_dir / name)
    (overlay / "shelf_source.json").write_text(json.dumps({
        "base_url": f"http://127.0.0.1:{srv.server_address[1]}/", "hosts": ["127.0.0.1"], "date": "dev",
        "allow_loopback": True}))
    for f in ("network.json", "network.log"):
        (work / f).unlink(missing_ok=True)
    svc = ChatService("unused", pack=overlay, memory_path=work / "chat_memory.log")
    svc.load()
    if svc.error:
        raise SystemExit(svc.error)
    svc.set_network({"channel": "shelf", "enabled": True})
    a = svc.assistant
    bot, atlas = a.bot, a.atlas
    captured: list = []
    orig = calib.features

    def spy(*args, **kw):
        f = orig(*args, **kw)
        captured.append(f)
        return f
    calib.features = spy
    qs = _sample(per_article, part, parts)
    t0 = time.time()
    with out.open("w", encoding="utf-8") as fo:
        for i, q in enumerate(qs):
            captured.clear()
            text = " ".join(q["q"].split())
            resolved = bot.resolve(text)
            names = [m.group(0) for m in re.finditer(r"\b[A-Z][\w'’.-]*(?:\s+(?:of|the|de|von|van)?\s*[A-Z][\w'’.-]*)*",
                                                     resolved) if not resolved.startswith(m.group(0))]
            rows, used = atlas.candidates(resolved, list(dict.fromkeys(names)))
            rec = {"id": q["id"], "article": q["article"], "used": used, "n_rows": len(rows)}
            if rows:
                bot.extra_rows = rows
                try:
                    rep = bot._answer(resolved)
                finally:
                    bot.extra_rows = []
                src = rep.source or {}
                pred = rep.answer or rep.guess
                rec.update({"pred": pred, "atlas": src.get("kind") == "shelf", "title": src.get("title"),
                            "local_conf": rep.confidence, "feats": captured[-1] if captured else None,
                            "right": exact(pred, q["answers"]), "kind": rep.kind,
                            "article_hit": any(r[1].get("title", "").replace(" ", "_") == q["article"] or
                                               normalize_answer(r[1].get("title", "")) ==
                                               normalize_answer(q["article"].replace("_", " ")) for r in rows)})
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if (i + 1) % 50 == 0:
                print(f"[examples {part}] {i + 1}/{len(qs)} {time.time() - t0:.0f}s", flush=True)
    srv.shutdown()
    del botmod


def examples(pack: Path, shelf_dir: Path, per_article: int, workers: int) -> None:
    import subprocess
    procs = []
    for part in range(workers):
        out = CACHE / f"examples-{part}.jsonl"
        procs.append(subprocess.Popen([sys.executable, __file__, "_worker", "--pack", str(pack), "--shelf", str(shelf_dir),
                                       "--per-article", str(per_article), "--part", str(part), "--parts", str(workers),
                                       "--out", str(out)]))
    codes = [p.wait() for p in procs]
    if any(codes):
        raise SystemExit(f"workers failed: {codes}")


# -- train ----------------------------------------------------------------------------------------

def train(target: float, holdout_share: float = 0.2, label: str = "f1") -> dict:
    """``label``: "f1" counts an answer right at token F1 ≥ 0.5 against a SQuAD answer (closer to
    a person's judgement: "7 April 1986" for "April 7, 1986"), "em" only an exact match."""
    from engramm.chat.calib import train as perceptron
    recs = []
    for f in sorted(CACHE.glob("examples-*.jsonl")):
        recs += [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()]
    gold = {qa["id"]: [x["text"] for x in qa["answers"]] for a in squad_articles() for p in a["paragraphs"]
            for qa in p["qas"]}
    for r in recs:
        if r.get("feats"):
            r["right"] = exact(r["pred"], gold[r["id"]]) if label == "em" else token_f1(r["pred"], gold[r["id"]]) >= 0.5
    usable = [r for r in recs if r.get("feats") and r.get("atlas")]
    arts = sorted({r["article"] for r in recs})
    hold = set(arts[::round(1 / holdout_share)])
    tr = [(r["feats"], r["right"]) for r in usable if r["article"] not in hold]
    ho = [r for r in usable if r["article"] in hold]
    w = perceptron(tr, passes=10, seed=0)
    score = lambda f: sum(w.get(x, 0.0) for x in f)              # noqa: E731
    scored = sorted(((score(r["feats"]), r["right"]) for r in ho), key=lambda x: -x[0])
    theta, best = None, None
    right = 0
    for k, (s, ok) in enumerate(scored, 1):
        right += ok
        if right / k >= target and (k == len(scored) or scored[k][0] < s):
            theta, best = s, (k, right)
    n_ho_q = sum(1 for r in recs if r["article"] in hold)
    rep = {"label": label, "examples": len(recs), "with_shelf_answer": len(usable), "train": len(tr), "holdout": len(ho),
           "holdout_questions": n_ho_q, "target": target, "theta": theta,
           "holdout_answered": best[0] if best else 0, "holdout_right": best[1] if best else 0,
           "holdout_exactness": round(best[1] / best[0], 3) if best else None,
           "holdout_coverage": round(best[0] / n_ho_q, 3) if best else 0.0,
           "article_found": round(sum(r.get("article_hit", False) for r in recs) / max(1, len(recs)), 3),
           "right_anywhere": round(sum(r.get("right", False) for r in recs) / max(1, len(recs)), 3),
           }
    if theta is None:
        raise SystemExit(f"no θ reaches exactness {target}: {rep}")
    OUT.write_text(json.dumps({"kind": "conf-perceptron", "theta": theta, "trained_on": "SQuAD v1.1 train (spent), "
                               "development shelf", "report": rep, "w": {k: w[k] for k in sorted(w)}}, indent=0) + "\n")
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "shelf", "examples", "train", "_worker"])
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--distractors", type=Path)
    ap.add_argument("--shelf", type=Path, default=Path("/dev/shm/engramm/shelf_dev"))
    ap.add_argument("--pack", type=Path)
    ap.add_argument("--per-article", type=int, default=25)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--parts", type=int, default=1)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--target", type=float, default=0.9)
    ap.add_argument("--label", choices=["f1", "em"], default="f1")
    a = ap.parse_args(argv)
    CACHE.mkdir(parents=True, exist_ok=True)
    if a.cmd == "fetch":
        fetch(CACHE / "squad_articles.jsonl", a.delay)
    elif a.cmd == "shelf":
        shelf(CACHE / "squad_articles.jsonl", a.distractors, a.shelf, a.workers)
    elif a.cmd == "examples":
        examples(a.pack, a.shelf, a.per_article, a.workers)
    elif a.cmd == "_worker":
        examples_worker(a.pack, a.shelf, a.per_article, a.part, a.parts, a.out)
    else:
        print(json.dumps(train(a.target, label=a.label), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
