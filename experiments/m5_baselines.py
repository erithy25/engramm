"""M5 — opponent baselines, run in their own environment (``.venv_b1``).

    .venv_b1/bin/python -m experiments.m5_baselines b0 --task banking77
    .venv_b1/bin/python -m experiments.m5_baselines b1 --task banking77
    .venv_b1/bin/python -m experiments.m5_baselines b3 --task banking77

The only contact point with ENGRAMM is the split file written by
``experiments/m5_engramm.py`` (``results/m5/split_<task>_seed<seed>.json``):
every system learns exactly the same ten examples per class and is scored on
the same official test split. Results go to ``results/m5/`` as one JSON per
system and task; ``experiments/m5_compare.py`` referees.

* **B0 — embedding kNN, no LLM.** bge-small-en-v1.5 embeddings of the shots,
  cosine top-5, similarity-weighted vote. Not part of the historical
  protocol: added because it is the cheapest system with *learned*
  representations, and therefore the fair test of whether ENGRAMM's
  efficiency advantage survives against learned embeddings at all.
* **B1 — local LLM + RAG** (the registered accuracy opponent, D5 §6):
  bge-small + FAISS top-5 retrieval, Qwen2.5-3B-Instruct Q4_K_M via
  llama.cpp classifies by prompt (greedy). CPU-only here; historically
  Metal. Resumable: predictions are appended to a JSONL file.
* **B3 — LoRA fine-tuning** (the registered learning-time and forgetting
  opponent): Qwen2.5-0.5B-Instruct with a classification head, LoRA r = 8 on
  q/v projections, 2 epochs per tranche, classes arriving in tranches (7 for
  Banking77, 10 for CLINC150). Learning time is reported as wall clock
  **and** CPU time — the historical harness reported only
  ``process_time``, which sums over PyTorch's threads and inflates the
  figure by up to the thread count.

Energy is not measured anywhere in this container (no power interface); a
CPU-seconds-per-query proxy is recorded and labelled as such.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from data.intents import load_banking77, load_clinc150

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "results" / "m5"
MODELS = REPO / "models"
QWEN_B1 = MODELS / "qwen2.5-3b-instruct-q4_k_m.gguf"
QWEN_B1_SHA256 = "626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d"
QWEN_B3 = "Qwen/Qwen2.5-0.5B-Instruct"
EMBED = "BAAI/bge-small-en-v1.5"
LOADERS = {"banking77": load_banking77, "clinc150": load_clinc150}
TRANCHES = {"banking77": 7, "clinc150": 10}

os.environ.setdefault("HF_HOME", str(MODELS / "hf"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")


def load_split(task: str, seed: int) -> dict[str, Any]:
    """Shots and test split exactly as ENGRAMM saw them — verified, not assumed."""
    split = json.loads((RESULTS_DIR / f"split_{task}_seed{seed}.json").read_text())
    full = LOADERS[task](allow_download=False)
    if list(full.labels) != split["labels"]:
        raise RuntimeError("label order differs from the split file")
    digest = hashlib.sha256("\n".join(full.labels[y] for y in full.y_test).encode()).hexdigest()
    if digest != split["test_labels_sha256"]:
        raise RuntimeError("test split differs from the one ENGRAMM was scored on")
    idx = split["train_indices"]
    return {
        "train_texts": [full.x_train[i] for i in idx],
        "train_labels": [full.labels[full.y_train[i]] for i in idx],
        "test_texts": list(full.x_test),
        "test_labels": [full.labels[y] for y in full.y_test],
        "classes": list(full.labels),
    }


def tranche_blocks(classes: list[str], n_tranches: int) -> list[list[str]]:
    per = max(1, len(classes) // n_tranches)
    blocks = [classes[t * per:(t + 1) * per] for t in range(n_tranches - 1)]
    blocks.append(classes[(n_tranches - 1) * per:])
    return blocks


def parse_label(raw: str, classes: list[str]) -> str:
    """Map free LLM output to a class: exact, then contained, then token overlap."""
    r = raw.strip().strip('."\' ').lower()
    for c in classes:
        if c.lower() == r:
            return c
    for c in sorted(classes, key=len, reverse=True):
        if c.lower() in r:
            return c
    tokens = set(re.split(r"\W+", r))
    return max(classes, key=lambda c: len(set(c.lower().split("_")) & tokens))


def _versions() -> dict[str, str]:
    out = {"python": sys.version.split()[0], "numpy": np.__version__}
    for name in ("torch", "transformers", "peft", "sentence_transformers", "faiss",
                 "llama_cpp"):
        try:
            out[name] = __import__(name).__version__
        except Exception:                                # not needed for every system
            pass
    return out


def _write(record: dict[str, Any], system: str, task: str, seed: int) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"m5_{system}_{task}_seed{seed}.json"
    record.update({"timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "versions": _versions(), "cpu_count": os.cpu_count()})
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def _embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED, device="cpu")


# ---------------------------------------------------------------------------
# B0 — embedding kNN
# ---------------------------------------------------------------------------

def run_b0(task: str, seed: int, k: int = 5) -> None:
    data = load_split(task, seed)
    emb = _embedder()
    marker = time.perf_counter()
    train = emb.encode(data["train_texts"], normalize_embeddings=True, batch_size=64)
    learn_s = time.perf_counter() - marker
    classes = data["classes"]
    index = {c: i for i, c in enumerate(classes)}
    y_train = np.array([index[c] for c in data["train_labels"]])
    marker, cpu = time.perf_counter(), time.process_time()
    test = emb.encode(data["test_texts"], normalize_embeddings=True, batch_size=64)
    sims = test @ train.T
    top = np.argsort(-sims, axis=1, kind="stable")[:, :k]
    votes = np.zeros((len(test), len(classes)))
    np.add.at(votes, (np.repeat(np.arange(len(test)), k), y_train[top].ravel()),
              np.take_along_axis(sims, top, axis=1).ravel())
    predicted = votes.argmax(axis=1)
    query_s, query_cpu = time.perf_counter() - marker, time.process_time() - cpu
    y_test = np.array([index[c] for c in data["test_labels"]])
    record = {"task": task, "system": "b0", "seed": seed, "k": k,
              "model": f"{EMBED} kNN (cosine, top-{k}, similarity-weighted)",
              "n_classes": len(classes), "n_test": len(y_test),
              "acc": float(np.mean(predicted == y_test)),
              "learn_ms_per_class_wall": learn_s / len(classes) * 1e3,
              "query_ms_mean_batched": query_s / len(y_test) * 1e3,
              "cpu_seconds_per_query_proxy": query_cpu / len(y_test),
              "energy_mj_per_query": None}
    print(f"[{task}] B0: acc={record['acc']:.4f}  -> {_write(record, 'b0', task, seed)}")


# ---------------------------------------------------------------------------
# B1 — retrieval + Qwen2.5-3B classification
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_b1(task: str, seed: int, limit: int | None = None, threads: int = 4) -> None:
    import faiss
    from llama_cpp import Llama

    if _sha256(QWEN_B1) != QWEN_B1_SHA256:
        raise RuntimeError(f"{QWEN_B1} does not match its recorded digest")
    data = load_split(task, seed)
    classes = data["classes"]
    emb = _embedder()
    train = emb.encode(data["train_texts"], normalize_embeddings=True).astype("float32")
    index = faiss.IndexFlatIP(train.shape[1])
    index.add(train)
    llm = Llama(model_path=str(QWEN_B1), n_ctx=4096, n_threads=threads,
                n_gpu_layers=0, seed=seed, verbose=False)
    intents = ", ".join(classes)
    system = ("You are an intent classifier. Reply with exactly one intent label "
              "from the allowed list and nothing else.")

    texts, gold = data["test_texts"], data["test_labels"]
    if limit:
        texts, gold = texts[:limit], gold[:limit]
    out_path = RESULTS_DIR / f"m5_b1_{task}_seed{seed}.jsonl"
    done = []
    if out_path.exists():
        done = [json.loads(line) for line in out_path.read_text().splitlines() if line.strip()]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as sink:
        for i in range(len(done), len(texts)):
            marker, cpu = time.perf_counter(), time.process_time()
            q = emb.encode([texts[i]], normalize_embeddings=True).astype("float32")
            _, neighbours = index.search(q, 5)
            shots = "\n".join(f'- "{data["train_texts"][j]}" -> {data["train_labels"][j]}'
                              for j in neighbours[0])
            # The constant part (system + allowed intents) comes first, so
            # llama.cpp reuses its KV cache across queries.
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content":
                         f"Allowed intents: {intents}\n\nExamples:\n{shots}\n\n"
                         f'Text: "{texts[i]}"\nIntent:'}]
            reply = llm.create_chat_completion(messages=messages, max_tokens=16,
                                               temperature=0.0)
            raw = reply["choices"][0]["message"]["content"]
            pred = parse_label(raw, classes)
            row = {"i": i, "gold": gold[i], "pred": pred, "raw": raw,
                   "ms": (time.perf_counter() - marker) * 1e3,
                   "cpu_s": time.process_time() - cpu}
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
            sink.flush()
            done.append(row)
            if (i + 1) % 100 == 0:
                acc = np.mean([r["pred"] == r["gold"] for r in done])
                print(f"  [{task}] B1 {i + 1}/{len(texts)} acc={acc:.4f}", flush=True)

    record = {"task": task, "system": "b1", "seed": seed,
              "model": "Qwen2.5-3B-Instruct-Q4_K_M (llama.cpp, CPU) + bge-small-en-v1.5 + FAISS top-5",
              "model_sha256": QWEN_B1_SHA256,
              "n_classes": len(classes), "n_test": len(done),
              "complete": len(done) == len(data["test_texts"]),
              "acc": float(np.mean([r["pred"] == r["gold"] for r in done])),
              "learn_ms_per_class_wall": None,
              "learn_note": "RAG: learning is embedding the shots and inserting them into the index",
              "query_ms_mean": float(np.mean([r["ms"] for r in done])),
              "cpu_seconds_per_query_proxy": float(np.mean([r["cpu_s"] for r in done])),
              "energy_mj_per_query": None,
              "energy_note": "not measured: no power interface in this container"}
    print(f"[{task}] B1: acc={record['acc']:.4f} -> {_write(record, 'b1', task, seed)}")


# ---------------------------------------------------------------------------
# B3 — LoRA, classes in tranches
# ---------------------------------------------------------------------------

def run_b3(task: str, seed: int, epochs: int = 2, threads: int = 4) -> None:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.manual_seed(seed)
    torch.set_num_threads(threads)
    data = load_split(task, seed)
    classes = data["classes"]
    cls2id = {c: i for i, c in enumerate(classes)}
    tok = AutoTokenizer.from_pretrained(QWEN_B3)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForSequenceClassification.from_pretrained(
        QWEN_B3, num_labels=len(classes), torch_dtype=torch.float32)
    model.config.pad_token_id = tok.pad_token_id
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16,
                                             target_modules=["q_proj", "v_proj"],
                                             task_type="SEQ_CLS", modules_to_save=["score"]))
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=2e-4)
    blocks = tranche_blocks(classes, TRANCHES[task])
    first = set(blocks[0])

    def accuracy(subset: set[str] | None) -> float:
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for text, gold in zip(data["test_texts"], data["test_labels"]):
                if subset is not None and gold not in subset:
                    continue
                enc = tok(text, return_tensors="pt", truncation=True, max_length=48)
                correct += int(classes[int(model(**enc).logits.argmax())] == gold)
                total += 1
        model.train()
        return correct / max(total, 1)

    rng = np.random.default_rng(seed)
    wall = cpu = 0.0
    after_first = None
    model.train()
    for t, block in enumerate(blocks):
        members = set(block)
        examples = [(x, cls2id[y]) for x, y in zip(data["train_texts"], data["train_labels"])
                    if y in members]
        marker, c0 = time.perf_counter(), time.process_time()
        for _ in range(epochs):
            for j in rng.permutation(len(examples)):
                text, label = examples[j]
                enc = tok(text, return_tensors="pt", truncation=True, max_length=48)
                loss = model(**enc, labels=torch.tensor([label])).loss
                loss.backward()
                opt.step()
                opt.zero_grad()
        wall += time.perf_counter() - marker
        cpu += time.process_time() - c0
        if t == 0:
            after_first = accuracy(first)
        print(f"  [{task}] B3 tranche {t + 1}/{len(blocks)} ({len(block)} classes) "
              f"wall {wall / 60:.1f} min", flush=True)

    final_first = accuracy(first)
    record = {"task": task, "system": "b3", "seed": seed, "epochs_per_tranche": epochs,
              "model": f"{QWEN_B3} LoRA r=8 (q_proj, v_proj), SEQ_CLS",
              "n_classes": len(classes), "n_test": len(data["test_labels"]),
              "acc": accuracy(None),
              "learn_ms_per_class_wall": wall / len(classes) * 1e3,
              "learn_ms_per_class_cpu": cpu / len(classes) * 1e3,
              "torch_threads": threads,
              "forgetting": {"tranches": len(blocks), "first_block_classes": len(blocks[0]),
                             "block_after_first": after_first, "block_final": final_first,
                             "classical_pp": (after_first - final_first) * 100},
              "energy_mj_per_query": None}
    print(f"[{task}] B3: acc={record['acc']:.4f} forgetting "
          f"{record['forgetting']['classical_pp']:+.2f} pp -> {_write(record, 'b3', task, seed)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("system", choices=["b0", "b1", "b3"])
    parser.add_argument("--task", choices=sorted(LOADERS), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--results-dir", default=None,
                        help="read the split from and write results to this directory")
    args = parser.parse_args(argv)
    if args.results_dir:
        global RESULTS_DIR
        RESULTS_DIR = Path(args.results_dir)
    if args.system == "b0":
        run_b0(args.task, args.seed)
    elif args.system == "b1":
        run_b1(args.task, args.seed, args.limit)
    else:
        run_b3(args.task, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
