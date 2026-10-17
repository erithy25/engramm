"""Zero-shot benchmarks for Sela-2 (docs/PREREG_SELA2.md, M3) and its reference models, in the harness of
experiments/sela1_bench.py (same downloads, same scoring: lm-evaluation-harness style log-likelihoods, every context
starting with the model's end-of-text token, sequences cut from the left to 1,024 tokens).

    python -m experiments.sela2_bench bench --model sela2-base --ckpt sela2_basis_bf16.pt --task hellaswag --shard 0 --shards 8 --out DIR
    python -m experiments.sela2_bench bench --model pythia-160m --task winogrande --out DIR
    python -m experiments.sela2_bench collect --inputs DIR --out results/sela2/bench.json

Tasks (the four of sela1_bench plus four more, all downloaded once and recorded by SHA-256):
- lambada, hellaswag, arc_easy, piqa: exactly as in experiments/sela1_bench.py.
- arc_challenge: ARC-Challenge test (1,172), "Question: <q>\\nAnswer:" + " <choice>".
- openbookqa: OpenBookQA main test (500), "<question stem>" + " <choice>".
- winogrande: WinoGrande XL validation (1,267), partial scoring as in lm-eval: the context is the sentence up to the
  blank with an option filled in, the continuation the rest of the sentence (identical for both options).
- mmlu: MMLU test, all 57 subjects (14,042), as a cloze task: "Question: <q>\\nAnswer:" + " <choice>".

Metric per task (fixed before the Sela-2 run; the same as the reference values of PREREG §3): acc_norm (log p divided
by the continuation's length in characters) for hellaswag, piqa, arc_easy, arc_challenge, openbookqa and mmlu; acc for
winogrande (the continuations are identical, so acc_norm = acc) and lambada (every token of the last word greedy).

Pooled score (PREREG §2): the unweighted mean over the six tasks hellaswag, piqa, arc_easy, arc_challenge,
winogrande and openbookqa (each task counts once). Stage "GPT-3-Small level" is reached when the pooled score of
the Sela-2 base model is above GPT-2 small with the lower end of the 95 % paired bootstrap interval of the
difference above 0, and not below Pythia-160M.

Models: sela2-base and sela2-chat (the bf16 files of experiments/sela2_run.sh, scored in float32 with their own
tokenizer, data/lm2_tokenizer.json, checked against the SHA-256 stored in the file), sela1 (experiments/sela1_bench.py),
gpt2 (GPT-2 small at the recorded revision and SHA-256, experiments/sela1_bench.py), and gpt2-medium, pythia-160m,
pythia-410m through transformers (the resolved Hugging Face commit is recorded with every result).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import numpy as np

from experiments import sela1_bench as B

REPO = B.REPO
SOURCES = {
    **B.SOURCES,
    "arc_challenge": [B.HF_PARQUET.format(repo="allenai/ai2_arc", config="ARC-Challenge", split="test")],
    "openbookqa": [B.HF_PARQUET.format(repo="allenai/openbookqa", config="main", split="test")],
    "winogrande": [B.HF_PARQUET.format(repo="allenai/winogrande", config="winogrande_xl", split="validation")],
    "mmlu": [B.HF_PARQUET.format(repo="cais/mmlu", config="all", split="test")],
}
EXPECTED_ITEMS = {**B.EXPECTED_ITEMS, "arc_challenge": 1172, "openbookqa": 500, "winogrande": 1267, "mmlu": 14042}
METRIC = {"lambada": "acc", "winogrande": "acc", "hellaswag": "acc_norm", "piqa": "acc_norm", "arc_easy": "acc_norm",
          "arc_challenge": "acc_norm", "openbookqa": "acc_norm", "mmlu": "acc_norm"}
POOLED = ("hellaswag", "piqa", "arc_easy", "arc_challenge", "winogrande", "openbookqa")
HF_MODELS = {"gpt2-medium": "openai-community/gpt2-medium", "pythia-160m": "EleutherAI/pythia-160m",
             "pythia-410m": "EleutherAI/pythia-410m"}
MODELS = ("sela2-base", "sela2-chat", "sela1", "gpt2", *HF_MODELS)
GPT3_SMALL_HELLASWAG = 0.337                      # GPT-3 paper, Table 3.3 (zero-shot, 125M); format slightly different


def items_from_rows(task: str, rows: list[dict]) -> list[dict]:
    """Items {"requests": [(context, continuation), ...], "gold": int} of the four tasks added here."""
    items: list[dict] = []
    if task == "arc_challenge":
        for row in rows:
            labels, texts = list(row["choices"]["label"]), list(row["choices"]["text"])
            if row["answerKey"] not in labels:
                raise SystemExit(f"ARC item {row['id']}: answer key {row['answerKey']} not among {labels}")
            q = f"Question: {row['question']}\nAnswer:"
            items.append({"requests": [(q, " " + t) for t in texts], "gold": labels.index(row["answerKey"])})
    elif task == "openbookqa":
        for row in rows:
            labels, texts = list(row["choices"]["label"]), list(row["choices"]["text"])
            if row["answerKey"] not in labels:
                raise SystemExit(f"OpenBookQA item {row['id']}: answer key {row['answerKey']} not among {labels}")
            items.append({"requests": [(row["question_stem"], " " + t) for t in texts],
                          "gold": labels.index(row["answerKey"])})
    elif task == "winogrande":
        for row in rows:
            s = row["sentence"]
            if s.count("_") != 1 or row["answer"] not in ("1", "2"):
                raise SystemExit(f"WinoGrande item without exactly one blank or answer 1/2: {s!r}")
            i = s.index("_")
            rest = " " + s[i + 1:].strip()
            items.append({"requests": [(s[:i] + row["option1"], rest), (s[:i] + row["option2"], rest)],
                          "gold": int(row["answer"]) - 1})
    elif task == "mmlu":
        for row in rows:
            choices = list(row["choices"])
            if len(choices) != 4 or not 0 <= int(row["answer"]) < 4:
                raise SystemExit(f"MMLU item with {len(choices)} choices / answer {row['answer']}: {row['question'][:60]!r}")
            q = f"Question: {row['question'].strip()}\nAnswer:"
            items.append({"requests": [(q, " " + str(c).strip()) for c in choices], "gold": int(row["answer"])})
    else:
        raise SystemExit(f"unknown task {task}")
    return items


def load_task(task: str) -> tuple[list[dict], dict]:
    if task in B.SOURCES:
        return B.load_task(task)
    paths = [B.fetch(u) for u in SOURCES[task]]
    files = [{"url": u, "sha256": B.sha256_file(p), "bytes": p.stat().st_size} for u, p in zip(SOURCES[task], paths)]
    items = items_from_rows(task, B.read_parquet(paths[0]))
    if len(items) != EXPECTED_ITEMS[task]:
        raise SystemExit(f"{task}: {len(items)} items, expected {EXPECTED_ITEMS[task]} (source changed?)")
    return items, {"files": files}


# ---------------------------------------------------------------------------
# models (the interface of experiments/sela1_bench.py: encode, hidden, logits, bos, info)
# ---------------------------------------------------------------------------

class Sela2:
    def __init__(self, ckpt: Path, name: str, tokenizer: Path | None = None):
        import torch
        from engramm.lm.tokenizer import LMTokenizer
        from experiments.sela2_model import Sela2 as Model, Sela2Config
        st = torch.load(ckpt, map_location="cpu", weights_only=False)
        self.model = Model(Sela2Config(**st["cfg"]))
        self.model.load_state_dict({k: v.float() for k, v in st["model"].items()})
        self.model.eval()
        meta = st.get("meta") or {}
        pre = meta.get("pretrain") or meta
        self.tok = LMTokenizer(tokenizer or REPO / "data" / "lm2_tokenizer.json", sha256=pre.get("tokenizer_sha256") or None)
        if self.tok.vocab_size != self.model.cfg.vocab:
            raise SystemExit(f"tokenizer has {self.tok.vocab_size} tokens, the model {self.model.cfg.vocab}")
        self.bos = 0
        self.info = {"model": name, "ckpt_sha256": B.sha256_file(ckpt), "ckpt_bytes": ckpt.stat().st_size,
                     "tokens_trained": int(pre.get("tokens", 0)), "cfg": st["cfg"], "sft_steps": meta.get("sft_steps"),
                     "params": sum(p.numel() for p in self.model.parameters()), "tokenizer_sha256": self.tok.sha256}

    def encode(self, text: str) -> list[int]:
        return [int(i) for i in self.tok.encode(text)]

    def hidden(self, ids):
        from experiments.sela2_model import dense_attend, doc_mask
        return self.model.hidden(ids, dense_attend(doc_mask(ids)))

    def logits(self, h):
        return self.model.logits(h)


class HFModel:
    """A causal LM through transformers: the last hidden state (after the final norm) and the output embedding."""

    def __init__(self, name: str):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        repo = HF_MODELS[name]
        self.tok = AutoTokenizer.from_pretrained(repo)
        self.model = AutoModelForCausalLM.from_pretrained(repo, torch_dtype=torch.float32)
        self.model.eval()
        self.bos = self.tok.eos_token_id
        if self.bos is None:
            raise SystemExit(f"{repo}: tokenizer has no end-of-text token")
        self.head = self.model.get_output_embeddings()
        self.info = {"model": name, "hf_repo": repo, "revision": getattr(self.model.config, "_commit_hash", None),
                     "params": sum(p.numel() for p in self.model.parameters()), "bos": int(self.bos)}

    def encode(self, text: str) -> list[int]:
        return list(self.tok.encode(text, add_special_tokens=False))

    def hidden(self, ids):
        return self.model(input_ids=ids, output_hidden_states=True).hidden_states[-1]

    def logits(self, h):
        return self.head(h)


def load_model(name: str, ckpt: str | None, tokenizer: str | None = None):
    if name in ("sela2-base", "sela2-chat"):
        if not ckpt:
            raise SystemExit(f"--ckpt is required for {name}")
        return Sela2(Path(ckpt), name, Path(tokenizer) if tokenizer else None)
    if name in ("sela1", "gpt2"):
        return B.load_model(name, ckpt)
    if name in HF_MODELS:
        return HFModel(name)
    raise SystemExit(f"unknown model {name}")


# ---------------------------------------------------------------------------
# bench: one task shard for one model
# ---------------------------------------------------------------------------

def score_items(m, items: list[dict], mine: list[int], batch_tokens: int) -> dict:
    reqs, owner = [], []
    for i in mine:
        for c, (ctx, cont) in enumerate(items[i]["requests"]):
            reqs.append((m.encode(ctx), m.encode(cont)))
            owner.append((i, len(cont)))
    t0 = time.time()
    res = B.score_requests(m, reqs, batch_tokens)
    per: dict[int, list] = {}
    for (i, nchar), (ll, greedy) in zip(owner, res):
        per.setdefault(i, []).append((ll, greedy, nchar))
    rec = {"items": [], "correct": [], "correct_norm": [], "ll": [], "greedy": [], "requests": len(reqs),
           "seconds": time.time() - t0}
    for i in mine:
        rows, gold = per[i], items[i]["gold"]
        lls = [r[0] for r in rows]
        norm = [r[0] / max(1, r[2]) for r in rows]
        rec["items"].append(i)
        rec["correct"].append(int(int(np.argmax(lls)) == gold))
        rec["correct_norm"].append(int(int(np.argmax(norm)) == gold))
        rec["ll"].append(lls[gold])
        rec["greedy"].append(int(rows[gold][1]))
    return rec


def cmd_bench(args) -> None:
    import torch
    torch.set_num_threads(args.threads or os.cpu_count() or 1)
    items, src = load_task(args.task)
    mine = [i for i in range(len(items)) if i % args.shards == args.shard]
    if args.limit:
        mine = mine[:args.limit]
    B.log(f"{args.task}: {len(mine)} of {len(items)} items (shard {args.shard}/{args.shards}), model {args.model}")
    m = load_model(args.model, args.ckpt, args.tokenizer)
    rec = {"task": args.task, "model": args.model, "model_info": m.info, "shard": args.shard, "shards": args.shards,
           "limit": args.limit, "source": src, "torch": torch.__version__,
           "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **score_items(m, items, mine, args.batch_tokens)}
    n = len(mine)
    rec["summary"] = ({"acc": sum(rec["greedy"]) / n, "ppl": math.exp(-sum(rec["ll"]) / n)} if args.task == "lambada"
                      else {"acc": sum(rec["correct"]) / n, "acc_norm": sum(rec["correct_norm"]) / n})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"bench_{args.model}_{args.task}_{args.shard}of{args.shards}.json"
    (out / name).write_text(json.dumps(rec) + "\n")
    B.log(f"{args.task} {args.model}: {rec['summary']} ({n} items, {rec['requests']} requests, "
          f"{rec['seconds']:.0f} s) -> {out / name}")


# ---------------------------------------------------------------------------
# collect: merge shards, scores per task, the pooled score and the stage criterion
# ---------------------------------------------------------------------------

def item_scores(task: str, m: dict) -> np.ndarray:
    key = {"acc": "greedy" if task == "lambada" else "correct", "acc_norm": "correct_norm"}[METRIC[task]]
    return np.asarray(m[key], dtype=np.float64)


def pooled_ci(a: dict[str, np.ndarray], b: dict[str, np.ndarray], reps: int = 2000, seed: int = 0) -> list[float]:
    """95 % interval of pooled(a) - pooled(b): items resampled within each task, paired between the two models."""
    rng = np.random.default_rng(seed)
    d = np.zeros(reps)
    for t in POOLED:
        diff = a[t] - b[t]
        n = len(diff)
        for r in range(reps):
            d[r] += diff[rng.integers(0, n, n)].mean()
    d /= len(POOLED)
    return [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))]


def merge(parts: list[dict], task: str) -> tuple[dict | None, str | None]:
    shards = {p["shards"] for p in parts}
    keys = ("items", "correct", "correct_norm", "ll", "greedy")
    m = {k: sum((p[k] for p in parts), []) for k in keys}
    if len(shards) != 1 or sorted(p["shard"] for p in parts) != list(range(next(iter(shards)))):
        return None, f"shards present: {sorted(p['shard'] for p in parts)} of {sorted(shards)}"
    if any(p.get("limit") for p in parts):
        return None, "a shard ran with --limit"
    if len(m["items"]) != EXPECTED_ITEMS[task] or len(set(m["items"])) != EXPECTED_ITEMS[task]:
        return None, f"{len(m['items'])} items, expected {EXPECTED_ITEMS[task]}"
    order = np.argsort(m["items"])
    return {k: np.asarray(v)[order] for k, v in m.items()}, None


def collect(inputs: Path) -> dict:
    runs: dict[tuple[str, str], list[dict]] = {}
    for p in sorted(inputs.rglob("bench_*.json")):
        r = json.loads(p.read_text())
        runs.setdefault((r["model"], r["task"]), []).append(r)
    res: dict = {"what": "Zero-shot benchmarks of Sela-2 and its reference models in one harness "
                         "(experiments/sela2_bench.py, scoring of experiments/sela1_bench.py).",
                 "metric": METRIC, "pooled_tasks": list(POOLED), "tasks": {}, "models": {}, "incomplete": []}
    scores: dict[str, dict[str, np.ndarray]] = {}
    for (model, task), parts in sorted(runs.items()):
        m, problem = merge(parts, task)
        if problem:                                        # reported, never mixed into a partial score
            res["incomplete"].append({"model": model, "task": task, "problem": problem})
            continue
        res["models"][model] = parts[0]["model_info"]
        n = len(m["items"])
        s = item_scores(task, m)
        scores.setdefault(model, {})[task] = s
        entry = {"metric": METRIC[task], "score": float(s.mean()), "se": float(s.std(ddof=0) / math.sqrt(n)),
                 "acc": float((m["greedy"] if task == "lambada" else m["correct"]).mean()), "items": n,
                 "seconds": sum(p["seconds"] for p in parts), "torch": parts[0]["torch"]}
        if task == "lambada":
            entry["ppl"] = math.exp(-float(m["ll"].mean()))
        else:
            entry["acc_norm"] = float(m["correct_norm"].mean())
        res["tasks"].setdefault(task, {"source": parts[0]["source"], "results": {}})["results"][model] = entry
    res["pooled"] = {model: float(np.mean([s[t].mean() for t in POOLED]))
                     for model, s in scores.items() if all(t in s for t in POOLED)}
    base, ref, floor = scores.get("sela2-base"), scores.get("gpt2"), scores.get("pythia-160m")
    stage: dict = {"rule": "pooled(sela2-base) > pooled(gpt2) with the lower 95 % bound of the paired difference "
                           "above 0, and pooled(sela2-base) >= pooled(pythia-160m)"}
    if all(x is not None and all(t in x for t in POOLED) for x in (base, ref, floor)):
        ci = pooled_ci(base, ref)
        p = res["pooled"]
        stage.update({"sela2_minus_gpt2": p["sela2-base"] - p["gpt2"], "ci95": ci,
                      "sela2_minus_pythia160m": p["sela2-base"] - p["pythia-160m"]})
        stage["reached"] = bool(ci[0] > 0 and p["sela2-base"] >= p["pythia-160m"])
    else:
        stage["reached"] = None
        stage["missing"] = "needs complete results of sela2-base, gpt2 and pythia-160m on all six pooled tasks"
    res["stage_gpt3_small"] = stage
    hs = res["tasks"].get("hellaswag", {}).get("results", {})
    res["hellaswag_vs_gpt3_small"] = {"gpt3_small": GPT3_SMALL_HELLASWAG,
                                      **{k: v["score"] for k, v in hs.items() if k.startswith("sela2")}}
    if base and scores.get("sela2-chat"):
        chat = scores["sela2-chat"]
        res["chat_minus_base"] = {t: float(chat[t].mean() - base[t].mean()) for t in base if t in chat}
    return res


def cmd_collect(args) -> None:
    res = collect(Path(args.inputs))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    for p in res["incomplete"]:
        print(f"{p['model']}/{p['task']}: incomplete ({p['problem']}), left out")
    for task, t in res["tasks"].items():
        print(f"{task:14s} " + "  ".join(f"{m}: {e['score']:.4f}" for m, e in t["results"].items()))
    print("pooled:", {m: round(v, 4) for m, v in res["pooled"].items()})
    print("stage GPT-3-Small level:", res["stage_gpt3_small"])


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bench")
    b.add_argument("--model", choices=MODELS, required=True)
    b.add_argument("--ckpt", default=None, help="model file (sela2-base, sela2-chat, sela1)")
    b.add_argument("--tokenizer", default=None, help="Sela-2 tokenizer (default data/lm2_tokenizer.json)")
    b.add_argument("--task", choices=sorted(SOURCES), required=True)
    b.add_argument("--shard", type=int, default=0)
    b.add_argument("--shards", type=int, default=1)
    b.add_argument("--limit", type=int, default=0, help="smoke test: only the first N items of the shard")
    b.add_argument("--threads", type=int, default=0)
    b.add_argument("--batch-tokens", type=int, default=8192)
    b.add_argument("--out", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--inputs", required=True)
    c.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "bench" and not 0 <= args.shard < args.shards:
        raise SystemExit("--shard must be in [0, --shards)")
    {"bench": cmd_bench, "collect": cmd_collect}[args.cmd](args)


if __name__ == "__main__":
    main()
