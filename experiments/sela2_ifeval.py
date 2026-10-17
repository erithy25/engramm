"""M6 of docs/PREREG_SELA2.md: IFEval (541 prompts) for the Sela-2 chat model and the base model, through the chat
format of the desktop app (engramm/lm/sela_chat.py: full system prompt, NumPy model), greedy decoding with the app's
repetition penalty, at most 640 tokens per reply, scored with lm-evaluation-harness's IFEval checks.

    python -m experiments.sela2_ifeval run --weights sela2-chat.npz --tag chat --shard 0 --shards 8 --out DIR
    python -m experiments.sela2_ifeval collect --inputs DIR --out results/sela2/ifeval.json

Scoring needs lm_eval (only its ifeval module is loaded; pip install --no-deps lm_eval==0.4.11 langdetect
immutabledict nltk) — the punkt_tab data of nltk is downloaded on first use. The reported metric is
prompt-level loose accuracy (strict accuracy and the instruction-level values are reported too).
Criterion (PREREG §2): IFEval(chat) − IFEval(base) >= +8 points.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

HF_PARQUET = "https://huggingface.co/api/datasets/google/IFEval/parquet/default/train/0.parquet"
N_PROMPTS = 541
MAX_TOKENS = 640


def load_rows() -> tuple[list[dict], str]:
    from experiments.sela1_bench import fetch, read_parquet, sha256_file
    p = fetch(HF_PARQUET)
    rows = read_parquet(p)
    if len(rows) != N_PROMPTS:
        raise SystemExit(f"IFEval: {len(rows)} prompts, expected {N_PROMPTS}")
    return rows, sha256_file(p)


def cmd_run(args) -> None:
    from engramm.lm.sela_chat import SelaChat
    from engramm.lm.tokenizer import LMTokenizer
    rows, sha = load_rows()
    mine = [(i, r) for i, r in enumerate(rows) if i % args.shards == args.shard][:args.limit or None]
    tok = LMTokenizer(args.tokenizer, sha256=None) if args.tokenizer else None
    sc = SelaChat(args.weights, tokenizer=tok)
    out, t0 = [], time.time()
    for k, (i, r) in enumerate(mine):
        ids = sc.build(None, r["prompt"], lang="en", brief=False, reply_room=MAX_TOKENS)
        text, n, done = sc.generate(ids, max_tokens=MAX_TOKENS, temperature=0.0, rep_penalty=1.1)
        out.append({"index": i, "key": int(r["key"]), "response": text, "tokens": n, "stop": sc.last_stop})
        if k % 20 == 0:
            print(f"[{k + 1}/{len(mine)}] {r['prompt'][:60]!r} -> {text[:80]!r}", flush=True)
    res = {"tag": args.tag, "shard": args.shard, "shards": args.shards, "limit": args.limit,
           "weights": Path(args.weights).name, "source_sha256": sha, "seconds": round(time.time() - t0, 1), "rows": out}
    d = Path(args.out)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"ifeval_{args.tag}_{args.shard}of{args.shards}.json").write_text(json.dumps(res, ensure_ascii=False) + "\n")


def _process_results():
    """lm_eval's IFEval scorer without importing the rest of lm_eval (whose package start-up needs torch,
    transformers, datasets, …): its package directories are registered as bare namespace modules."""
    import importlib.util
    import sys
    import types
    if "lm_eval.tasks.ifeval.utils" in sys.modules:
        return sys.modules["lm_eval.tasks.ifeval.utils"].process_results
    spec = importlib.util.find_spec("lm_eval")
    if spec is None or not spec.submodule_search_locations:
        raise SystemExit("lm_eval is not installed (pip install --no-deps lm_eval==0.4.11 langdetect immutabledict nltk)")
    root = Path(list(spec.submodule_search_locations)[0])
    for name, path in (("lm_eval", root), ("lm_eval.tasks", root / "tasks"), ("lm_eval.tasks.ifeval", root / "tasks" / "ifeval")):
        if name not in sys.modules:
            m = types.ModuleType(name)
            m.__path__ = [str(path)]
            sys.modules[name] = m
    from lm_eval.tasks.ifeval.utils import process_results
    return process_results


def score(rows: list[dict], responses: dict[int, str]) -> dict:
    process_results = _process_results()
    agg = {"prompt_level_strict_acc": [], "prompt_level_loose_acc": [], "inst_level_strict_acc": [],
           "inst_level_loose_acc": []}
    for i, r in enumerate(rows):
        doc = {"key": r["key"], "prompt": r["prompt"], "instruction_id_list": list(r["instruction_id_list"]),
               "kwargs": [dict(k) for k in r["kwargs"]]}
        m = process_results(doc, [responses.get(i, "")])
        for k in agg:
            v = m[k]
            agg[k].extend(v if isinstance(v, list) else [v])
    return {k: 100 * sum(map(float, v)) / max(1, len(v)) for k, v in agg.items()}


def cmd_collect(args) -> None:
    rows, sha = load_rows()
    by_tag: dict[str, list[dict]] = {}
    for p in sorted(Path(args.inputs).rglob("ifeval_*of*.json")):
        r = json.loads(p.read_text())
        by_tag.setdefault(r["tag"], []).append(r)
    res = {"what": "M6 of docs/PREREG_SELA2.md (experiments/sela2_ifeval.py)", "source_sha256": sha, "models": {}}
    for tag, parts in sorted(by_tag.items()):
        shards = {p["shards"] for p in parts}
        resp = {x["index"]: x["response"] for p in parts for x in p["rows"]}
        complete = (len(shards) == 1 and sorted(p["shard"] for p in parts) == list(range(next(iter(shards))))
                    and not any(p.get("limit") for p in parts) and len(resp) == N_PROMPTS)
        entry = {"complete": complete, "weights": parts[0]["weights"], "responses": len(resp),
                 "stop_reasons": {s: sum(x["stop"] == s for p in parts for x in p["rows"])
                                  for s in ("stop", "limit", "loop", "context")}}
        if complete:
            entry.update(score(rows, resp))
        res["models"][tag] = entry
    c, b = res["models"].get("chat", {}), res["models"].get("base", {})
    if "prompt_level_loose_acc" in c and "prompt_level_loose_acc" in b:
        diff = c["prompt_level_loose_acc"] - b["prompt_level_loose_acc"]
        res["criterion"] = {"chat_minus_base": diff, "limit": 8.0, "met": diff >= 8.0}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--weights", required=True)
    r.add_argument("--tag", required=True, choices=("chat", "base"))
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
