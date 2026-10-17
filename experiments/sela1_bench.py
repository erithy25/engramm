"""Zero-shot benchmarks for Sela-1 135M and GPT-2 small in one harness (PLAN §11, Ergebnis 17. Oktober).

    python -m experiments.sela1_bench bench --model sela1 --ckpt model.pt --task hellaswag --shard 0 --shards 4 --out DIR
    python -m experiments.sela1_bench bench --model gpt2 --task lambada --out DIR
    python -m experiments.sela1_bench collect --inputs DIR --out results/v5/h100/bench_main.json

The test-split result of Sela-1 is in-domain (the test documents come from its training sources). These tasks come from
other sources and are scored the same way for both models, so they show how Sela-1 compares with GPT-2 small outside
its own data. Scoring follows EleutherAI's lm-evaluation-harness (zero-shot), with one difference kept for both models:
every context starts with the model's end-of-text token, as in the bits-per-byte harness.
- lambada: LAMBADA, OpenAI version (5,153 passages). acc = every token of the last word is the greedy choice;
  ppl = exp(-mean log p of the last word).
- hellaswag: validation (10,042 items, 4 endings, lm-eval preprocessing). acc = highest sum of log p; acc_norm = highest
  sum of log p divided by the ending's length in characters.
- arc_easy: ARC-Easy test (2,376 questions), "Question: <q>\\nAnswer:" + " <choice>"; acc and acc_norm.
- piqa: validation (1,838 goals, 2 solutions), "Question: <goal>\\nAnswer:" + " <solution>"; acc and acc_norm.
Data files are downloaded once; their SHA-256 is recorded with every result. GPT-2 small is the Hugging Face revision
recorded in models/lm/gpt2/eval_test.json, loaded without transformers (safetensors parsed directly, SHA-256 checked).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
import time
import urllib.request
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
CACHE = Path(os.environ.get("SELA1_BENCH_CACHE", str(REPO / "data" / "cache" / "bench")))
GPT2_REF = REPO / "models" / "lm" / "gpt2" / "eval_test.json"
GPT2_REPO = "openai-community/gpt2"
MAX_LEN = 1024
HF_PARQUET = "https://huggingface.co/api/datasets/{repo}/parquet/{config}/{split}/0.parquet"
SOURCES = {
    "lambada": [HF_PARQUET.format(repo="EleutherAI/lambada_openai", config="default", split="test")],
    "hellaswag": [HF_PARQUET.format(repo="Rowan/hellaswag", config="default", split="validation")],
    "arc_easy": [HF_PARQUET.format(repo="allenai/ai2_arc", config="ARC-Easy", split="test")],
    "piqa": ["https://yonatanbisk.com/piqa/data/valid.jsonl", "https://yonatanbisk.com/piqa/data/valid-labels.lst"],
}
EXPECTED_ITEMS = {"lambada": 5153, "hellaswag": 10042, "arc_easy": 2376, "piqa": 1838}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url: str, tries: int = 6) -> Path:
    """Download ``url`` once into CACHE (retries with back-off) and return the local path."""
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / hashlib.sha256(url.encode()).hexdigest()[:16]
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    part = dest.with_suffix(".part")
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "engramm-sela1-bench"})
            with urllib.request.urlopen(req, timeout=120) as r, open(part, "wb") as f:
                while True:
                    block = r.read(1 << 20)
                    if not block:
                        break
                    f.write(block)
            if part.stat().st_size == 0:
                raise OSError("empty download")
            part.replace(dest)
            return dest
        except OSError as e:
            if attempt == tries:
                raise SystemExit(f"download failed after {tries} attempts: {url}: {e}")
            wait = 2 ** attempt
            log(f"download attempt {attempt} failed ({e}); retrying in {wait} s")
            time.sleep(wait)
    raise AssertionError("unreachable")


def read_parquet(path: Path) -> list[dict]:
    import pyarrow.parquet as pq
    return pq.read_table(path).to_pylist()


# ---------------------------------------------------------------------------
# tasks: each item = (list of (context, continuation), gold index or None, item kind)
# ---------------------------------------------------------------------------

def _hellaswag_pre(text: str) -> str:
    text = text.strip().replace(" [title]", ". ")
    text = re.sub("\\[.*?\\]", "", text)
    return text.replace("  ", " ")


def load_task(task: str) -> tuple[list[dict], dict]:
    """Items as dicts {"requests": [(ctx, cont), ...], "gold": int} and a record of the source files."""
    paths = [fetch(u) for u in SOURCES[task]]
    files = [{"url": u, "sha256": sha256_file(p), "bytes": p.stat().st_size} for u, p in zip(SOURCES[task], paths)]
    items: list[dict] = []
    if task == "lambada":
        for row in read_parquet(paths[0]):
            ctx, last = row["text"].rsplit(" ", 1)
            items.append({"requests": [(ctx, " " + last)], "gold": 0})
    elif task == "hellaswag":
        for row in read_parquet(paths[0]):
            ctx = row["ctx_a"] + " " + row["ctx_b"].capitalize()
            query = _hellaswag_pre(row["activity_label"] + ": " + ctx)
            items.append({"requests": [(query, " " + _hellaswag_pre(e)) for e in row["endings"]],
                          "gold": int(row["label"])})
    elif task == "arc_easy":
        for row in read_parquet(paths[0]):
            labels = list(row["choices"]["label"])
            texts = list(row["choices"]["text"])
            if row["answerKey"] not in labels:
                raise SystemExit(f"ARC item {row['id']}: answer key {row['answerKey']} not among {labels}")
            q = f"Question: {row['question']}\nAnswer:"
            items.append({"requests": [(q, " " + t) for t in texts], "gold": labels.index(row["answerKey"])})
    elif task == "piqa":
        rows = [json.loads(l) for l in paths[0].read_text(encoding="utf-8").splitlines() if l.strip()]
        labels = [int(l) for l in paths[1].read_text().split()]
        if len(rows) != len(labels):
            raise SystemExit(f"PIQA: {len(rows)} items but {len(labels)} labels")
        for row, lab in zip(rows, labels):
            q = f"Question: {row['goal']}\nAnswer:"
            items.append({"requests": [(q, " " + row["sol1"]), (q, " " + row["sol2"])], "gold": lab})
    else:
        raise SystemExit(f"unknown task {task}")
    if len(items) != EXPECTED_ITEMS[task]:
        raise SystemExit(f"{task}: {len(items)} items, expected {EXPECTED_ITEMS[task]} (source changed?)")
    return items, {"files": files}


# ---------------------------------------------------------------------------
# models: hidden states for all positions, logits only where a continuation token is predicted
# ---------------------------------------------------------------------------

class Sela1:
    def __init__(self, ckpt: Path):
        import torch
        from engramm.lm.tokenizer import LMTokenizer, EOS
        from experiments import v5_long as L
        st = torch.load(ckpt, map_location="cpu", weights_only=False)
        self.model = L.LongGPT(**st["cfg"])
        self.model.load_state_dict({k: v.float() for k, v in st["model"].items()})
        self.model.eval()
        self.tok = LMTokenizer()
        self.bos = EOS
        self.info = {"model": "Sela-1 135M", "ckpt_sha256": sha256_file(ckpt), "ckpt_bytes": ckpt.stat().st_size,
                     "tokens_trained": int(st["meta"]["tokens"]), "cfg": st["cfg"],
                     "params": sum(p.numel() for p in self.model.parameters()),
                     "tokenizer_sha256": self.tok.sha256}

    def encode(self, text: str) -> list[int]:
        return [int(i) for i in self.tok.encode(text)]

    def hidden(self, ids):
        return self.model.hidden(ids)

    def logits(self, h):
        return self.model.logits(h)


def _safetensors(path: Path) -> dict[str, np.ndarray]:
    """Minimal safetensors reader (little-endian F32/F16/BF16), no extra package."""
    raw = memoryview(path.read_bytes())
    n = struct.unpack("<Q", raw[:8])[0]
    header = json.loads(bytes(raw[8:8 + n]))
    base = 8 + n
    out = {}
    for name, spec in header.items():
        if name == "__metadata__":
            continue
        s, e = spec["data_offsets"]
        buf = raw[base + s:base + e]
        if spec["dtype"] == "F32":
            arr = np.frombuffer(buf, dtype="<f4")
        elif spec["dtype"] == "F16":
            arr = np.frombuffer(buf, dtype="<f2").astype(np.float32)
        elif spec["dtype"] == "BF16":
            arr = (np.frombuffer(buf, dtype="<u2").astype(np.uint32) << 16).view(np.float32)
        else:
            raise SystemExit(f"safetensors: unsupported dtype {spec['dtype']} for {name}")
        out[name] = arr.reshape(spec["shape"])
    return out


def gpt2_files() -> tuple[Path, Path, dict]:
    """GPT-2 small at the revision of the bpb reference; weights accepted only with the recorded SHA-256."""
    ref = json.loads(GPT2_REF.read_text())
    rev, want = ref["revision"], ref["weights_sha256"]
    local = REPO / "models" / "hf" / "hub" / "models--openai-community--gpt2" / "snapshots" / rev
    if (local / "model.safetensors").exists() and (local / "tokenizer.json").exists():
        w, t = local / "model.safetensors", local / "tokenizer.json"
    else:
        w = fetch(f"https://huggingface.co/{GPT2_REPO}/resolve/{rev}/model.safetensors")
        t = fetch(f"https://huggingface.co/{GPT2_REPO}/resolve/{rev}/tokenizer.json")
    got = sha256_file(w)
    if got != want:
        raise SystemExit(f"GPT-2 weights SHA-256 {got}, expected {want} (revision {rev})")
    return w, t, {"model": "GPT-2 small", "hf_repo": GPT2_REPO, "revision": rev, "weights_sha256": got}


class GPT2:
    def __init__(self):
        import torch
        from tokenizers import Tokenizer
        w, t, self.info = gpt2_files()
        sd = {k.removeprefix("transformer."): torch.from_numpy(v.copy()) for k, v in _safetensors(w).items()}
        self.sd = sd
        self.layers = 1 + max(int(k.split(".")[1]) for k in sd if k.startswith("h."))
        self.heads = 12
        self.tok = Tokenizer.from_file(str(t))
        self.bos = self.tok.token_to_id("<|endoftext|>")
        if self.bos != 50256:
            raise SystemExit(f"GPT-2 tokenizer: <|endoftext|> has id {self.bos}")
        self.info["params"] = int(sum(v.numel() for k, v in sd.items() if not k.endswith(".attn.bias")
                                      and not k.endswith(".attn.masked_bias")))

    def encode(self, text: str) -> list[int]:
        return self.tok.encode(text, add_special_tokens=False).ids

    def hidden(self, ids):
        import torch
        import torch.nn.functional as F
        sd = self.sd
        B, T = ids.shape
        x = sd["wte.weight"][ids] + sd["wpe.weight"][torch.arange(T)][None]
        d = x.shape[-1]
        hd = d // self.heads
        for i in range(self.layers):
            p = f"h.{i}."
            a = F.layer_norm(x, (d,), sd[p + "ln_1.weight"], sd[p + "ln_1.bias"], 1e-5)
            q, k, v = (a @ sd[p + "attn.c_attn.weight"] + sd[p + "attn.c_attn.bias"]).split(d, dim=2)
            q, k, v = (z.view(B, T, self.heads, hd).transpose(1, 2) for z in (q, k, v))
            y = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(B, T, d)
            x = x + y @ sd[p + "attn.c_proj.weight"] + sd[p + "attn.c_proj.bias"]
            m = F.layer_norm(x, (d,), sd[p + "ln_2.weight"], sd[p + "ln_2.bias"], 1e-5)
            m = F.gelu(m @ sd[p + "mlp.c_fc.weight"] + sd[p + "mlp.c_fc.bias"], approximate="tanh")
            x = x + m @ sd[p + "mlp.c_proj.weight"] + sd[p + "mlp.c_proj.bias"]
        return F.layer_norm(x, (d,), sd["ln_f.weight"], sd["ln_f.bias"], 1e-5)

    def logits(self, h):
        return h @ self.sd["wte.weight"].T


def load_model(name: str, ckpt: str | None):
    if name == "sela1":
        if not ckpt:
            raise SystemExit("--ckpt is required for sela1")
        return Sela1(Path(ckpt))
    if name == "gpt2":
        return GPT2()
    raise SystemExit(f"unknown model {name}")


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def score_requests(m, reqs: list[tuple[list[int], list[int]]], batch_tokens: int = 8192) -> list[tuple[float, bool]]:
    """(sum of natural log p of the continuation, every continuation token greedy) for each (context, continuation)
    token pair. Every sequence is [bos] + context + continuation, cut from the left to MAX_LEN (bos kept)."""
    import torch
    seqs = []
    for ctx, cont in reqs:
        if not cont:
            raise SystemExit("empty continuation")
        full = [m.bos] + ctx + cont
        if len(full) > MAX_LEN:
            full = [m.bos] + full[len(full) - MAX_LEN + 1:]
        seqs.append((full, len(cont)))
    order = sorted(range(len(seqs)), key=lambda i: -len(seqs[i][0]))
    out: list[tuple[float, bool] | None] = [None] * len(seqs)
    pos = 0
    with torch.inference_mode():
        while pos < len(order):
            T = len(seqs[order[pos]][0])
            bsz = max(1, batch_tokens // T)
            idx = order[pos:pos + bsz]
            pos += len(idx)
            ids = torch.full((len(idx), T), m.bos, dtype=torch.long)
            rows, cols, tgts = [], [], []
            for r, i in enumerate(idx):
                full, nc = seqs[i]
                ids[r, :len(full)] = torch.tensor(full)
                L = len(full)
                for j in range(L - nc, L):
                    rows.append(r)
                    cols.append(j - 1)
                    tgts.append(full[j])
            h = m.hidden(ids)
            sel = h[torch.tensor(rows), torch.tensor(cols)]
            lp = torch.log_softmax(m.logits(sel).float(), dim=-1)
            tg = torch.tensor(tgts)
            tok_lp = lp[torch.arange(len(tgts)), tg].double()
            greedy = lp.argmax(dim=-1) == tg
            k = 0
            for r, i in enumerate(idx):
                nc = seqs[i][1]
                out[i] = (float(tok_lp[k:k + nc].sum()), bool(greedy[k:k + nc].all()))
                k += nc
    return out  # type: ignore[return-value]


def cmd_bench(args) -> None:
    import torch
    torch.set_num_threads(args.threads or os.cpu_count() or 1)
    items, src = load_task(args.task)
    mine = [i for i in range(len(items)) if i % args.shards == args.shard]
    if args.limit:
        mine = mine[:args.limit]
    log(f"{args.task}: {len(mine)} of {len(items)} items (shard {args.shard}/{args.shards}), model {args.model}")
    m = load_model(args.model, args.ckpt)
    reqs, owner = [], []
    for i in mine:
        for c, (ctx, cont) in enumerate(items[i]["requests"]):
            reqs.append((m.encode(ctx), m.encode(cont)))
            owner.append((i, c, len(cont)))
    t0 = time.time()
    res = score_requests(m, reqs, args.batch_tokens)
    secs = time.time() - t0
    per = {}
    for (i, c, nchar), (ll, greedy) in zip(owner, res):
        per.setdefault(i, []).append((ll, greedy, nchar))
    rec = {"task": args.task, "model": args.model, "model_info": m.info, "shard": args.shard, "shards": args.shards,
           "limit": args.limit, "items": [], "correct": [], "correct_norm": [], "ll": [], "greedy": [],
           "source": src, "torch": torch.__version__, "seconds": secs, "requests": len(reqs),
           "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for i in mine:
        rows = per[i]
        gold = items[i]["gold"]
        lls = [r[0] for r in rows]
        norm = [r[0] / max(1, r[2]) for r in rows]
        rec["items"].append(i)
        rec["correct"].append(int(int(np.argmax(lls)) == gold))
        rec["correct_norm"].append(int(int(np.argmax(norm)) == gold))
        rec["ll"].append(lls[gold])
        rec["greedy"].append(int(rows[gold][1]))
    n = len(mine)
    summary = {"acc": sum(rec["correct"]) / n, "acc_norm": sum(rec["correct_norm"]) / n}
    if args.task == "lambada":
        summary = {"acc": sum(rec["greedy"]) / n, "ppl": math.exp(-sum(rec["ll"]) / n)}
    rec["summary"] = summary
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"bench_{args.model}_{args.task}_{args.shard}of{args.shards}.json"
    (out / name).write_text(json.dumps(rec) + "\n")
    log(f"{args.task} {args.model}: {summary} ({n} items, {len(reqs)} requests, {secs:.0f} s) -> {out / name}")


# ---------------------------------------------------------------------------
# collect: merge shards, both models side by side, paired difference
# ---------------------------------------------------------------------------

def _paired_ci(a: np.ndarray, b: np.ndarray, reps: int = 2000, seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    n = len(a)
    d = np.empty(reps)
    for r in range(reps):
        k = rng.integers(0, n, n)
        d[r] = a[k].mean() - b[k].mean()
    return [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))]


def cmd_collect(args) -> None:
    runs: dict[tuple[str, str], list[dict]] = {}
    for p in sorted(Path(args.inputs).rglob("bench_*.json")):
        r = json.loads(p.read_text())
        runs.setdefault((r["model"], r["task"]), []).append(r)
    res = {"what": "Zero-shot benchmarks, Sela-1 135M and GPT-2 small in the same harness (experiments/sela1_bench.py); "
                   "scored like lm-evaluation-harness, every context starting with the model's end-of-text token.",
           "tasks": {}, "models": {}}
    merged: dict[tuple[str, str], dict] = {}
    res["incomplete"] = []
    for (model, task), parts in sorted(runs.items()):
        shards = {p["shards"] for p in parts}
        keys = ("items", "correct", "correct_norm", "ll", "greedy")
        m = {k: sum((p[k] for p in parts), []) for k in keys}
        problem = None
        if len(shards) != 1 or sorted(p["shard"] for p in parts) != list(range(next(iter(shards)))):
            problem = f"shards present: {sorted(p['shard'] for p in parts)} of {sorted(shards)}"
        elif any(p.get("limit") for p in parts):
            problem = "a shard ran with --limit"
        elif len(m["items"]) != EXPECTED_ITEMS[task] or len(set(m["items"])) != EXPECTED_ITEMS[task]:
            problem = f"{len(m['items'])} items, expected {EXPECTED_ITEMS[task]}"
        if problem:                                        # reported, never mixed into a partial score
            res["incomplete"].append({"model": model, "task": task, "problem": problem})
            print(f"{model}/{task}: incomplete ({problem}), left out")
            continue
        order = np.argsort(m["items"])
        m = {k: np.asarray(v)[order] for k, v in m.items()}
        merged[(model, task)] = m
        res["models"][model] = parts[0]["model_info"]
        n = len(m["items"])
        if task == "lambada":
            acc = float(m["greedy"].mean())
            entry = {"acc": acc, "acc_se": math.sqrt(acc * (1 - acc) / n), "ppl": math.exp(-float(m["ll"].mean()))}
        else:
            acc, accn = float(m["correct"].mean()), float(m["correct_norm"].mean())
            entry = {"acc": acc, "acc_se": math.sqrt(acc * (1 - acc) / n),
                     "acc_norm": accn, "acc_norm_se": math.sqrt(accn * (1 - accn) / n)}
        entry.update({"items": n, "seconds": sum(p["seconds"] for p in parts), "torch": parts[0]["torch"]})
        res["tasks"].setdefault(task, {"source": parts[0]["source"], "results": {}})["results"][model] = entry
    for task in res["tasks"]:
        if ("sela1", task) in merged and ("gpt2", task) in merged:
            a, b = merged[("sela1", task)], merged[("gpt2", task)]
            key = "greedy" if task == "lambada" else "correct_norm"
            res["tasks"][task]["sela1_minus_gpt2"] = {
                "metric": "acc" if task == "lambada" else "acc_norm",
                "diff": float(a[key].mean() - b[key].mean()), "ci95_paired_bootstrap": _paired_ci(a[key], b[key])}
    if args.recheck:
        res["recheck_cpu"] = recheck_summary(Path(args.inputs), Path(args.recheck_ref))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    if res.get("recheck_cpu"):
        r = res["recheck_cpu"]
        print(f"recheck on the CPU: {r.get('verdict')}; test (extended filter) {r.get('test_bpb_extended_cpu')} "
              f"vs {r.get('test_bpb_extended_gpu')}; max per-doc |diff| {r.get('perdoc_max_abs_bits')} bits")
    for task, t in res["tasks"].items():
        line = "  ".join(f"{mdl}: " + ", ".join(f"{k} {v:.4f}" for k, v in e.items() if k in ("acc", "acc_norm", "ppl"))
                         for mdl, e in t["results"].items())
        print(f"{task:10s} {line}")
    print(f"written: {out}")


def recheck_summary(inputs: Path, ref: Path, tag: str = "recheck_cpu") -> dict:
    """The network re-run on a CPU (h100_train eval) against the numbers saved on the GPU machine."""
    ev = next(iter(sorted(inputs.rglob(f"eval_{tag}.json"))), None)
    if ev is None:
        return {"verdict": "missing: the CPU re-evaluation produced no eval_recheck_cpu.json"}
    d = ev.parent
    cpu, gpu = json.loads(ev.read_text()), json.loads((ref / "eval_main.json").read_text())
    pc, pg = np.load(d / f"perdoc_final_{tag}.npz"), np.load(ref / "perdoc_final.npz")
    out = {"test_bpb_extended_cpu": cpu["test"].get("bpb_extended_filter"),
           "test_bpb_extended_gpu": gpu["test"].get("bpb_extended_filter"),
           "test_bpb_original_cpu": cpu["test"]["bpb"], "test_bpb_original_gpu": gpu["test"]["bpb"],
           "val_a_bpb_cpu": cpu["val_a"]["bpb"], "val_a_bpb_gpu": gpu["val_a"]["bpb"],
           "stage1_cpu": cpu.get("stage1"), "device_cpu": cpu.get("device"), "torch_cpu": cpu.get("torch")}
    diffs = []
    for s in ("val_a", "test"):
        a, b = pc[f"{s}_net_alone"], pg[f"{s}_net_alone"]
        if a.shape != b.shape:
            return {**out, "verdict": f"mismatch: {s} has {a.shape} documents on the CPU, {b.shape} on the GPU"}
        diffs.append(np.abs(a - b))
        out[f"{s}_perdoc_max_abs_bits"] = float(np.abs(a - b).max())
        out[f"{s}_perdoc_max_rel"] = float((np.abs(a - b) / np.maximum(b, 1e-9)).max())
        lc, lg = d / f"lp_{s}_{tag}.npy", ref / f"lp_{s}.npy"
        if lc.exists() and lg.exists():
            x, y = np.load(lc).astype(np.float64), np.load(lg).astype(np.float64)
            if x.shape == y.shape:
                out[f"{s}_token_lp_max_abs"] = float(np.abs(x - y).max())
                out[f"{s}_token_lp_mean_abs"] = float(np.abs(x - y).mean())
    out["perdoc_max_abs_bits"] = float(max(x.max() for x in diffs))
    gap = abs(out["test_bpb_extended_cpu"] - out["test_bpb_extended_gpu"])
    out["test_bpb_extended_abs_diff"] = gap
    out["verdict"] = ("reproduced (test bpb within 0.001)" if gap <= 1e-3 else
                      f"NOT reproduced: test bpb differs by {gap:.4f}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bench")
    b.add_argument("--model", choices=("sela1", "gpt2"), required=True)
    b.add_argument("--ckpt", default=None, help="Sela-1 model file (model_main_*.pt)")
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
    c.add_argument("--recheck", type=int, default=1, help="1: include the CPU re-evaluation found under --inputs")
    c.add_argument("--recheck-ref", default=str(REPO / "results" / "v5" / "h100"))
    args = ap.parse_args()
    if args.cmd == "bench" and not 0 <= args.shard < args.shards:
        raise SystemExit("--shard must be in [0, --shards)")
    {"bench": cmd_bench, "collect": cmd_collect}[args.cmd](args)


if __name__ == "__main__":
    main()
