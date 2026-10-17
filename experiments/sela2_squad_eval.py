"""M7 of docs/PREREG_SELA2.md: grounded answers on SQuAD v2 dev with the oracle paragraph, run as in the desktop app
(engramm/lm/sela_chat.py: SelaChat.grounded, NumPy model, temperature 0.2, at most 90 tokens).

    python -m experiments.sela2_squad_eval run --weights sela2-chat.npz --shard 0 --shards 4 --out DIR
    python -m experiments.sela2_squad_eval collect --inputs DIR --out results/sela2/squad.json

The sample is fixed: 500 answerable and 500 unanswerable questions, drawn with seed 0 from all dev questions (the
list of question ids is stored with the result). The paragraph is the only source, titled with its article. The
answer span is the reply's text before the first citation [n]; an abstention counts as "no answer".
- HasAns-F1: SQuAD's token F1 against the best gold answer (lower case, no punctuation or articles); an abstention
  on an answerable question scores 0.
- NoAns hit rate: share of unanswerable questions answered with the abstention.
Criteria (PREREG §2): HasAns-F1 >= 50 and NoAns hits >= 60 %. Reported as well: how often the app would show the
answer (``verify`` passed), and the same split by answerable / unanswerable.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import re
import string
import time
from pathlib import Path

HF_PARQUET = "https://huggingface.co/api/datasets/rajpurkar/squad_v2/parquet/squad_v2/validation/0.parquet"
N_EACH = 500
CRITERIA = {"hasans_f1": 50.0, "noans_hit_rate": 0.60}


def normalize(s: str) -> str:
    """SQuAD v2's official answer normalisation."""
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def f1(pred: str, gold: str) -> float:
    p, g = normalize(pred).split(), normalize(gold).split()
    if not p or not g:
        return float(p == g)
    common = collections.Counter(p) & collections.Counter(g)
    same = sum(common.values())
    if same == 0:
        return 0.0
    prec, rec = same / len(p), same / len(g)
    return 2 * prec * rec / (prec + rec)


def answer_span(text: str) -> str:
    """The reply's text before the first citation, without closing punctuation."""
    head = re.split(r"\s*\[\d{1,2}\]", text, maxsplit=1)[0]
    return head.strip().rstrip(".!?;:,").strip()


def sample(rows: list[dict]) -> list[dict]:
    has = [r for r in rows if (r["answers"] or {}).get("text")]
    no = [r for r in rows if not (r["answers"] or {}).get("text")]
    rng = random.Random(0)
    rng.shuffle(has)
    rng.shuffle(no)
    if len(has) < N_EACH or len(no) < N_EACH:
        raise SystemExit(f"SQuAD v2 dev: {len(has)} answerable / {len(no)} unanswerable, need {N_EACH} each")
    pick = has[:N_EACH] + no[:N_EACH]
    pick.sort(key=lambda r: r["id"])
    return pick


def load_rows() -> tuple[list[dict], str]:
    """The dev split, downloaded once into experiments/sela1_bench.py's cache ($SELA1_BENCH_CACHE)."""
    from experiments.sela1_bench import fetch, read_parquet, sha256_file
    p = fetch(HF_PARQUET)
    return read_parquet(p), sha256_file(p)


def cmd_run(args) -> None:
    from engramm.lm.sela_chat import SelaChat
    from engramm.lm.tokenizer import LMTokenizer
    rows, sha = load_rows()
    items = sample(rows)
    mine = [it for i, it in enumerate(items) if i % args.shards == args.shard][:args.limit or None]
    tok = LMTokenizer(args.tokenizer, sha256=None) if args.tokenizer else None
    sc = SelaChat(args.weights, tokenizer=tok)
    out_rows, t0 = [], time.time()
    for k, it in enumerate(mine):
        golds = list((it["answers"] or {}).get("text") or [])
        src = [(it["title"].replace("_", " "), it["context"])]
        g = sc.grounded(it["question"], src, max_tokens=90, seed=hash_seed(it["id"]))
        pred = "" if g["abstained"] else answer_span(g["text"])
        rec = {"id": it["id"], "has_answer": bool(golds), "reply": g["text"], "pred": pred,
               "abstained": bool(g["abstained"]), "verified": bool(g["verified"]), "stop": g.get("stop"),
               "tokens": g["tokens"], "f1": max((f1(pred, a) for a in golds), default=0.0) if golds and pred else 0.0}
        out_rows.append(rec)
        if k % 25 == 0:
            print(f"[{k + 1}/{len(mine)}] {it['question'][:60]!r} -> {g['text'][:80]!r}", flush=True)
    res = {"shard": args.shard, "shards": args.shards, "limit": args.limit, "weights": Path(args.weights).name,
           "source_sha256": sha, "seconds": round(time.time() - t0, 1), "rows": out_rows}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"squad_{args.shard}of{args.shards}.json").write_text(json.dumps(res, ensure_ascii=False) + "\n")


def hash_seed(qid: str) -> int:
    import zlib
    return zlib.crc32(qid.encode("utf-8"))


def collect(inputs: Path) -> dict:
    parts = [json.loads(p.read_text()) for p in sorted(inputs.rglob("squad_*of*.json"))]
    if not parts:
        raise SystemExit(f"no squad_*.json under {inputs}")
    shards = {p["shards"] for p in parts}
    rows = [r for p in parts for r in p["rows"]]
    complete = (len(shards) == 1 and sorted(p["shard"] for p in parts) == list(range(next(iter(shards))))
                and not any(p.get("limit") for p in parts) and len(rows) == 2 * N_EACH)
    has = [r for r in rows if r["has_answer"]]
    no = [r for r in rows if not r["has_answer"]]
    res = {"what": "M7 of docs/PREREG_SELA2.md (experiments/sela2_squad_eval.py)", "complete": complete,
           "questions": len(rows), "weights": parts[0]["weights"], "source_sha256": parts[0]["source_sha256"],
           "hasans_f1": 100 * sum(r["f1"] for r in has) / max(1, len(has)),
           "hasans_exact_abstentions": sum(r["abstained"] for r in has),
           "noans_hit_rate": sum(r["abstained"] for r in no) / max(1, len(no)),
           "shown_by_app": {"answerable": sum(r["verified"] for r in has) / max(1, len(has)),
                            "unanswerable": sum(r["verified"] for r in no) / max(1, len(no))},
           "hasans_f1_when_shown": 100 * sum(r["f1"] for r in has if r["verified"]) / max(1, sum(r["verified"] for r in has)),
           "ids": sorted(r["id"] for r in rows)}
    res["criteria"] = {k: {"value": res[k], "limit": v, "met": res[k] >= v} for k, v in CRITERIA.items()}
    res["criteria_met"] = complete and all(c["met"] for c in res["criteria"].values())
    return res


def cmd_collect(args) -> None:
    res = collect(Path(args.inputs))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "ids"}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--weights", required=True)
    r.add_argument("--tokenizer", default=None)
    r.add_argument("--shard", type=int, default=0)
    r.add_argument("--shards", type=int, default=1)
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--out", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--inputs", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "run" and not 0 <= a.shard < a.shards:
        raise SystemExit("--shard must be in [0, --shards)")
    {"run": cmd_run, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    main()
