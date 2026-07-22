#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m5_baselines.py — M5 Gegner-Baselines B1 (LLM+RAG) und B3 (LoRA)
=================================================================
(Projekt AXIOM, D5 §6 / V2). LAEUFT IN DER ISOLIERTEN 3.12-venv (.venv_b1);
Kontaktpunkt zu ENGRAMM ist nur das JSONL/meta-Schema (wie m5_engramm.py).

B1 = few-shot-Beispiele als bge-Embeddings in FAISS; pro Testquery Top-k-
     Retrieval -> Qwen2.5-3B-Q4 (Metal) klassifiziert per Prompt. Misst acc,
     Wall-Zeit/Query; Energie/Query separat via `b1energy` (sudo powermetrics).
B3 = LoRA-Fine-Tuning auf Qwen2.5-0.5B (HF), sequenziell ueber Tranchen von
     Klassen. Misst learn_ms_per_class und klassisches Vergessen (Rueckwaerts-
     Eval auf Tranche-1-Klassen). MODELL-ASYMMETRIE (B1=3B, B3=0.5B) bewusst,
     RAM-16GB-Limit; kleineres B3 macht Kriterium 3 HAERTER fuer ENGRAMM
     (konservativ). Dokumentiert in D4 §3 / D5 §6.

Aufrufe (in der venv):
  python m5_baselines.py b1      --task banking [--limit N]
  python m5_baselines.py b1energy --task banking
  python m5_baselines.py b3      --task banking [--tranches 7] [--limit-classes N]
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, threading, time
import numpy as np

from m5_engramm import fewshot_split, load_clinc
from m2_stream import load_banking77

QWEN_B1 = "models/qwen2.5-3b-q4.gguf"
QWEN_B3 = "Qwen/Qwen2.5-0.5B-Instruct"
EMBED = "BAAI/bge-small-en-v1.5"


def load_task(task, shots=10, seed=42):
    if task == "banking":
        (xtr, ytr), (xte, yte) = load_banking77()
    elif task == "clinc":
        (xtr, ytr), (xte, yte) = load_clinc()
    else:
        raise SystemExit(f"unbekannte Aufgabe {task}")
    ftr_t, ftr_l = fewshot_split(xtr, ytr, shots, seed)
    return ftr_t, ftr_l, list(xte), list(yte)


def parse_label(raw: str, classes) -> str:
    r = raw.strip().strip('."\' ').lower()
    for c in classes:                                   # exakter Treffer
        if c.lower() == r:
            return c
    for c in sorted(classes, key=len, reverse=True):    # enthaltenes Label
        if c.lower() in r:
            return c
    toks = set(re.split(r"\W+", r))                     # Token-Ueberlappung
    return max(classes,
               key=lambda c: len(set(c.lower().split("_")) & toks))


# ---------------------------------------------------------------------------
# B1 — bge-Retrieval + Qwen-3B-Klassifikation
# ---------------------------------------------------------------------------
def _b1_setup(task, shots, seed):
    import faiss
    from sentence_transformers import SentenceTransformer
    from llama_cpp import Llama
    ftr_t, ftr_l, xte, yte = load_task(task, shots, seed)
    classes = sorted(set(ftr_l))
    emb = SentenceTransformer(EMBED)
    E = emb.encode(ftr_t, normalize_embeddings=True).astype("float32")
    index = faiss.IndexFlatIP(E.shape[1])
    index.add(E)
    llm = Llama(model_path=QWEN_B1, n_ctx=2048, n_gpu_layers=-1, verbose=False)
    intents = ", ".join(classes)

    def classify(text: str) -> str:
        q = emb.encode([text], normalize_embeddings=True).astype("float32")
        _, I = index.search(q, 5)
        shots_txt = "\n".join(f'- "{ftr_t[j]}" -> {ftr_l[j]}' for j in I[0])
        msg = [{"role": "system", "content":
                "You are an intent classifier. Reply with exactly one intent "
                "label from the allowed list and nothing else."},
               {"role": "user", "content":
                f"Allowed intents: {intents}\n\nExamples:\n{shots_txt}\n\n"
                f'Text: "{text}"\nIntent:'}]
        r = llm.create_chat_completion(messages=msg, max_tokens=16,
                                       temperature=0.0)
        return parse_label(r["choices"][0]["message"]["content"], classes)

    return classify, classes, xte, yte


def run_b1(task, shots, seed, limit=None):
    classify, classes, xte, yte = _b1_setup(task, shots, seed)
    if limit:
        xte, yte = xte[:limit], yte[:limit]
    os.makedirs("logs", exist_ok=True)
    correct, qs = 0, []
    with open(f"logs/m5_b1_{task}.jsonl", "w", encoding="utf-8") as f:
        for i, (t, gold) in enumerate(zip(xte, yte)):
            t0 = time.perf_counter()
            pred = classify(t)
            qs.append((time.perf_counter() - t0) * 1e3)
            ok = int(pred == gold); correct += ok
            f.write(json.dumps({"i": i, "gold": gold, "pred": pred,
                                "correct": ok}, ensure_ascii=False) + "\n")
            if (i + 1) % 200 == 0:
                print(f"  [{task}] B1 {i+1}/{len(xte)} "
                      f"acc={correct/(i+1):.3f}", flush=True)
    acc = correct / len(xte)
    meta = {"task": task, "system": "b1", "shots": shots,
            "n_classes": len(classes), "n_test": len(xte), "acc": acc,
            "learn_ms_per_class": 0.0,          # RAG: kein Gewichts-Training
            "query_ms_mean": round(float(np.mean(qs)), 1),
            "model": "Qwen2.5-3B-Q4 + bge-small-en-v1.5 + FAISS"}
    _merge_meta(f"logs/m5_b1_{task}_meta.json", meta)
    print(f"[{task}] B1: acc={acc:.4f} ({correct}/{len(xte)})  "
          f"query_mean={np.mean(qs):.0f} ms")


def _merge_meta(path, new):
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(new)
    json.dump(old, open(path, "w"), indent=2)


# ---------------------------------------------------------------------------
# B1-Energie — powermetrics um einen Inferenz-Burst (sudo)
# ---------------------------------------------------------------------------
def _pkg_power_mw(seconds):
    n = max(4, int(seconds * 2))
    out = subprocess.run(["sudo", "powermetrics", "--samplers",
                          "cpu_power,gpu_power", "-i", "500", "-n", str(n)],
                         capture_output=True, text=True,
                         timeout=seconds + 60).stdout
    os.makedirs("logs", exist_ok=True)
    open("logs/m5_b1_powermetrics_raw.log", "a").write(out + "\n=====\n")
    mw = [float(m) for m in re.findall(
        r"(?:Combined|CPU|GPU)\s+Power[^:]*:\s*([\d.]+)\s*mW", out)]
    if not mw:
        raise RuntimeError("powermetrics nicht parsebar")
    return float(np.mean(mw))


def run_b1energy(task, shots, seed):
    classify, classes, xte, yte = _b1_setup(task, shots, seed)
    meta_path = f"logs/m5_b1_{task}_meta.json"
    q_ms = json.load(open(meta_path)).get("query_ms_mean", None) \
        if os.path.exists(meta_path) else None
    print(f"[{task}] B1-Energie (sudo powermetrics; W16):", flush=True)
    p_idle = _pkg_power_mw(15)
    print(f"  Idle: {p_idle:.0f} mW", flush=True)
    stop = threading.Event(); cnt = [0]
    def load():
        rng = np.random.default_rng(0)
        while not stop.is_set():
            classify(xte[int(rng.integers(0, len(xte)))]); cnt[0] += 1
    th = threading.Thread(target=load, daemon=True); th.start()
    time.sleep(3); c0 = cnt[0]
    p_load = _pkg_power_mw(30); c1 = cnt[0]
    stop.set(); th.join(timeout=5)
    n_q = max(c1 - c0, 1)
    p_delta_w = (p_load - p_idle) / 1000.0
    e_j_per_q = p_delta_w * 30.0 / n_q
    print(f"  Last {p_load:.0f} mW, {n_q} Queries/30s -> "
          f"{e_j_per_q:.2f} J/Query ({e_j_per_q*1000:.0f} mJ)")
    _merge_meta(meta_path, {"energy_mj_per_query": round(e_j_per_q * 1000, 1),
                            "energy_w_load": round(p_load / 1000, 2)})


# ---------------------------------------------------------------------------
# B3 — LoRA auf Qwen-0.5B, sequenzielle Tranchen, Vergessen
# ---------------------------------------------------------------------------
def run_b3(task, shots, seed, tranches=None, limit_classes=None):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    from peft import LoraConfig, get_peft_model
    torch.manual_seed(seed)
    ftr_t, ftr_l, xte, yte = load_task(task, shots, seed)
    classes = sorted(set(ftr_l))
    if limit_classes:
        classes = classes[:limit_classes]
        keep = set(classes)
        idx = [j for j in range(len(ftr_t)) if ftr_l[j] in keep]
        ftr_t, ftr_l = [ftr_t[j] for j in idx], [ftr_l[j] for j in idx]
        tk = [i for i in range(len(xte)) if yte[i] in keep]
        xte, yte = [xte[i] for i in tk], [yte[i] for i in tk]
    cls2id = {c: i for i, c in enumerate(classes)}

    tok = AutoTokenizer.from_pretrained(QWEN_B3)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForSequenceClassification.from_pretrained(
        QWEN_B3, num_labels=len(classes), torch_dtype=torch.float32)
    model.config.pad_token_id = tok.pad_token_id
    model = get_peft_model(model, LoraConfig(
        r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"],
        task_type="SEQ_CLS", modules_to_save=["score"]))
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                            lr=2e-4)

    ntr = tranches or (7 if len(classes) < 100 else 10)
    per = max(1, len(classes) // ntr)
    blocks = [classes[t * per:(t + 1) * per] for t in range(ntr - 1)]
    blocks.append(classes[(ntr - 1) * per:])
    t1_classes = set(blocks[0])

    def eval_acc(subset):
        model.eval(); correct = tot = 0
        with torch.no_grad():
            for i in range(len(xte)):
                if subset is not None and yte[i] not in subset:
                    continue
                enc = tok(xte[i], return_tensors="pt", truncation=True,
                          max_length=48)
                pred = classes[int(model(**enc).logits.argmax())]
                correct += int(pred == yte[i]); tot += 1
        model.train()
        return correct / max(tot, 1)

    learn_s = 0.0; forget_t1 = None
    for t, block in enumerate(blocks):
        ex = [(ftr_t[j], cls2id[ftr_l[j]]) for j in range(len(ftr_t))
              if ftr_l[j] in block]
        t0 = time.process_time()
        for _ in range(2):                              # 2 Epochen/Tranche
            for txt, lab in ex:
                enc = tok(txt, return_tensors="pt", truncation=True,
                          max_length=48)
                loss = model(**enc, labels=torch.tensor([lab])).loss
                loss.backward(); opt.step(); opt.zero_grad()
        learn_s += time.process_time() - t0
        if t == 0:
            forget_t1 = eval_acc(t1_classes)
        print(f"  [{task}] B3 Tranche {t+1}/{ntr} ({len(block)} Kl.) "
              f"kum. Lernzeit={learn_s/60:.1f} min", flush=True)

    forget_final = eval_acc(t1_classes)
    forgetting_pp = (forget_t1 - forget_final) * 100
    acc = eval_acc(None)
    learn_ms_cls = learn_s / len(classes) * 1e3
    meta = {"task": task, "system": "b3", "shots": shots,
            "n_classes": len(classes), "n_test": len(xte), "acc": acc,
            "learn_ms_per_class": round(learn_ms_cls, 1),
            "query_ms_mean": None, "forgetting_pp": round(forgetting_pp, 2),
            "model": "Qwen2.5-0.5B-Instruct LoRA r=8 (SEQ_CLS)"}
    json.dump(meta, open(f"logs/m5_b3_{task}_meta.json", "w"), indent=2)
    print(f"[{task}] B3: acc={acc:.4f}  learn={learn_ms_cls:.0f} ms/Klasse  "
          f"Vergessen(Tranche-1)={forgetting_pp:+.2f} pp "
          f"(nach T1 {forget_t1:.3f} -> final {forget_final:.3f})")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("b1", "b1energy"):
        p = sub.add_parser(name)
        p.add_argument("--task", choices=["banking", "clinc"], required=True)
        p.add_argument("--shots", type=int, default=10)
        p.add_argument("--seed", type=int, default=42)
        if name == "b1":
            p.add_argument("--limit", type=int, default=None)
    q = sub.add_parser("b3")
    q.add_argument("--task", choices=["banking", "clinc"], required=True)
    q.add_argument("--shots", type=int, default=10)
    q.add_argument("--seed", type=int, default=42)
    q.add_argument("--tranches", type=int, default=None)
    q.add_argument("--limit-classes", type=int, default=None)
    a = ap.parse_args()
    if a.cmd == "b1":
        run_b1(a.task, a.shots, a.seed, a.limit)
    elif a.cmd == "b1energy":
        run_b1energy(a.task, a.shots, a.seed)
    else:
        run_b3(a.task, a.shots, a.seed, a.tranches, a.limit_classes)


if __name__ == "__main__":
    main()
