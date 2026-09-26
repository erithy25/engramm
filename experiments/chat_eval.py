"""ENGRAMM-Chat stage 1 — the preregistered measurement (docs/PREREG_CHAT.md v1.0).

    python -m experiments.chat_build                 # once: the sentence index
    python -m experiments.chat_eval                  # C1–C5, record in results/chat/

Steps, exactly as registered:

1. SQuAD v1.1 train + dev (SHA-256 checked). Pool = questions whose paragraph has
   ≥ 80 % of its 13-token windows (step 13) verbatim in the train stream.
2. Split by SHAKE-256 of the question id: h = first 8 bytes, big-endian; order by
   (h, id); Dev = the first 500 with h & 1 == 0, Test = the first 1,000 with h & 1 == 1.
3. Dev: α ∈ {0, 0.5, 1, 2, 4} by Hit@1 (ties → smaller α); θ = the smallest value at
   which the precision of the given answers is ≥ 60 %.
4. Test: C1 Hit@1, C2 Hit@1 − Hit@1(BM25) with a paired bootstrap (2,000 reps, seed 42),
   C3 precision/coverage with the dev θ, C5 median answer time.
5. C4: 200 invented facts learnt in phrasing A, queried in phrasings B and C; hit =
   the learnt sentence of that fact is ranked first.

No external model anywhere: hits are exact string checks against the gold answers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from engramm.lm.chat import ChatEngine, SentenceIndex, contains_answer
from engramm.lm.model import HDCLanguageModel
from engramm.lm.suffix import sa_range
from engramm.repro import collect_environment, git_revision, peak_rss_mb
from experiments.lm_common import MODELS_DIR, REPO

SQUAD_DIR = REPO / "data" / "cache" / "chat"
SQUAD_SHA256 = {
    "train-v1.1.json": "3527663986b8295af4f7fcdff1ba1ff3f72d07d61a20f487cb238a6ef92fd955",
    "dev-v1.1.json": "95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9",
}
SQUAD_URL = "https://rajpurkar.github.io/SQuAD-explorer/dataset/"
FACTS = REPO / "data" / "lm_facts_templates.json"
RESULTS = REPO / "results" / "chat"
ALPHAS = (0.0, 0.5, 1.0, 2.0, 4.0)
N_DEV, N_TEST = 500, 1000
WINDOW, COVER = 13, 0.8
DEV_PRECISION = 0.60
C1_MIN, C2_MIN_PP, C3_PREC, C3_COVER, C4_MIN, C5_MAX_S = 0.30, 0.02, 0.55, 0.25, 0.80, 1.0
BOOT, BOOT_SEED = 2000, 42


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def load_squad() -> list[dict]:
    """All (id, question, answers, context) of SQuAD v1.1 train + dev, checksum-verified."""
    out = []
    for name, sha in SQUAD_SHA256.items():
        path = SQUAD_DIR / name
        if not path.exists():
            import urllib.request
            SQUAD_DIR.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(SQUAD_URL + name, path)
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != sha:
            raise RuntimeError(f"{name}: SHA-256 {got} != {sha}")
        data = json.loads(path.read_text(encoding="utf-8"))["data"]
        for art in data:
            for para in art["paragraphs"]:
                for qa in para["qas"]:
                    out.append({"id": qa["id"], "question": qa["question"],
                                "answers": [a["text"] for a in qa["answers"]],
                                "context": para["context"], "title": art["title"], "file": name})
    return out


def paragraph_coverage(model: HDCLanguageModel, contexts: list[str]) -> dict[str, float]:
    """Share of the 13-token windows (step 13) of each paragraph found verbatim in the stream."""
    tokens, sa = model.tokens, model.index.sa
    cov = {}
    for ctx in contexts:
        ids = np.asarray(model.tok.encode(ctx), dtype=np.uint16)
        n_win = len(ids) // WINDOW
        if n_win == 0:
            cov[ctx] = 0.0
            continue
        hit = 0
        for w in range(n_win):
            pat = np.ascontiguousarray(ids[w * WINDOW:(w + 1) * WINDOW])
            a, b = sa_range(tokens, sa, pat, WINDOW, 0, len(sa))
            hit += int(b > a)
        cov[ctx] = hit / n_win
    return cov


def split(pool: list[dict]) -> tuple[list[dict], list[dict]]:
    def h(q):
        return int.from_bytes(hashlib.shake_256(q["id"].encode("utf-8")).digest(8), "big")
    ordered = sorted(pool, key=lambda q: (h(q), q["id"]))
    dev = [q for q in ordered if h(q) & 1 == 0][:N_DEV]
    test = [q for q in ordered if h(q) & 1 == 1][:N_TEST]
    return dev, test


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def candidates(engine: ChatEngine, question: str):
    """(bm25, soft, sentence id) of the BM25 top 200 and Σ idf of the question."""
    rows, idf_sum, _ = engine.rank(question, alpha=1.0)
    return [(r[1], r[2], r[4]) for r in rows if r[3] == "base"], idf_sum


def ordered(cands, idf_sum: float, alpha: float):
    """Candidates re-scored with α, best first (score desc, sentence id asc)."""
    scored = [(b + alpha * s * idf_sum, sid) for b, s, sid in cands]
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored


def evaluate(engine: ChatEngine, qs: list[dict], per_q: list, alpha: float) -> dict:
    """Per question: hit@1, hit@5, confidence of the best sentence."""
    hit1, hit5, conf = [], [], []
    for q, (cands, idf_sum) in zip(qs, per_q):
        ranked = ordered(cands, idf_sum, alpha)
        texts = [engine.sentence_text((0, 0, 0, "base", sid)) for _, sid in ranked[:5]]
        hits = [contains_answer(t, q["answers"]) for t in texts]
        hit1.append(bool(hits[:1] and hits[0]))
        hit5.append(any(hits))
        conf.append(ranked[0][0] / idf_sum if ranked and idf_sum > 0 else 0.0)
    return {"hit1": np.array(hit1), "hit5": np.array(hit5), "conf": np.array(conf),
            "has": np.array([len(c) > 0 for c, _ in per_q])}


def choose_theta(ev: dict) -> float:
    """Smallest θ at which the precision of the given answers is ≥ 60 %."""
    for theta in [0.0] + sorted(set(float(c) for c in ev["conf"][ev["has"]])):
        answered = ev["has"] & (ev["conf"] >= theta)
        if answered.any() and ev["hit1"][answered].mean() >= DEV_PRECISION:
            return theta
    return float("inf")


def at_theta(ev: dict, theta: float) -> dict:
    answered = ev["has"] & (ev["conf"] >= theta)
    n = int(answered.sum())
    return {"theta": theta, "answered": n, "coverage": n / len(answered),
            "precision": float(ev["hit1"][answered].mean()) if n else 0.0}


def bootstrap_diff(a: np.ndarray, b: np.ndarray) -> dict:
    rng = np.random.default_rng(BOOT_SEED)
    idx = rng.integers(0, len(a), size=(BOOT, len(a)))
    d = a[idx].mean(axis=1) - b[idx].mean(axis=1)
    return {"diff": float(a.mean() - b.mean()), "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]}


def bootstrap_mean(a: np.ndarray) -> list[float]:
    rng = np.random.default_rng(BOOT_SEED)
    m = a[rng.integers(0, len(a), size=(BOOT, len(a)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


# ---------------------------------------------------------------------------
# C4: invented facts
# ---------------------------------------------------------------------------

def facts_test(model: HDCLanguageModel, index: SentenceIndex, alpha: float) -> dict:
    d = json.loads(FACTS.read_text())
    rel = {r["name"]: r for r in d["relations"]}
    facts = d["facts"]
    model.learn_texts({f["id"]: rel[f["relation"]]["A"].format(e=f["entity"], a=f["answer"]) for f in facts})
    out = {"n_facts": len(facts)}
    try:
        for a in sorted({0.0, alpha}):
            engine = ChatEngine(model, index, alpha=a)
            hits, by_form, examples = [], {"B": [], "C": []}, []
            for f in facts:
                for form in ("B", "C"):
                    q = rel[f["relation"]][form].format(e=f["entity"])
                    rows, _, _ = engine.rank(q)
                    ok = bool(rows) and rows[0][3] == "user" and rows[0][4][1] == f["id"]
                    hits.append(ok)
                    by_form[form].append(ok)
                    if len(examples) < 6 and (not ok or len(examples) < 3):
                        examples.append({"query": q, "hit": ok,
                                         "top": engine.sentence_text(rows[0]) if rows else None})
            out[f"alpha={a:g}"] = {"rank1": float(np.mean(hits)), "n_queries": len(hits),
                                   "rank1_B": float(np.mean(by_form["B"])),
                                   "rank1_C": float(np.mean(by_form["C"])), "examples": examples}
    finally:
        model.forget_many([f["id"] for f in facts])
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=MODELS_DIR / "main" / "model")
    ap.add_argument("--device", default="container")
    ap.add_argument("--results-dir", type=Path, default=RESULTS)
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()

    model = HDCLanguageModel.load(args.model)
    index = SentenceIndex.load(args.model.parent / "chat")
    info = json.loads((args.model.parent / "chat" / "info.json").read_text())
    print(f"model + index loaded ({time.time() - t0:.0f} s): {index.n:,} sentences", flush=True)

    squad = load_squad()
    contexts = sorted({q["context"] for q in squad})
    tc = time.time()
    cov = paragraph_coverage(model, contexts)
    pool = [q for q in squad if cov[q["context"]] >= COVER]
    n_para = sum(1 for c in contexts if cov[c] >= COVER)
    print(f"pool: {len(pool):,} of {len(squad):,} questions, {n_para:,} of {len(contexts):,} paragraphs "
          f"({time.time() - tc:.0f} s)", flush=True)
    dev, test = split(pool)

    engine = ChatEngine(model, index)
    engine.answer("warm up the compiled kernels")

    # -- dev: α and θ ------------------------------------------------------------------------
    td = time.time()
    dev_c = [candidates(engine, q["question"]) for q in dev]
    grid = {}
    for a in ALPHAS:
        ev = evaluate(engine, dev, dev_c, a)
        grid[a] = ev
        print(f"dev α={a:g}: Hit@1 {ev['hit1'].mean():.3f}  Hit@5 {ev['hit5'].mean():.3f}", flush=True)
    alpha = max(ALPHAS, key=lambda a: (grid[a]["hit1"].sum(), -a))
    theta = choose_theta(grid[alpha])
    dev_theta = at_theta(grid[alpha], theta)
    print(f"chosen α={alpha:g}, θ={theta:.4f} (dev precision {dev_theta['precision']:.3f}, "
          f"coverage {dev_theta['coverage']:.3f}); dev pass {time.time() - td:.0f} s", flush=True)

    # -- test ----------------------------------------------------------------------------------
    tt = time.time()
    test_c = [candidates(engine, q["question"]) for q in test]
    full = evaluate(engine, test, test_c, alpha)
    bm25 = evaluate(engine, test, test_c, 0.0)
    c2 = bootstrap_diff(full["hit1"].astype(float), bm25["hit1"].astype(float))
    c3 = at_theta(full, theta)
    print(f"test: Hit@1 {full['hit1'].mean():.3f} (BM25 {bm25['hit1'].mean():.3f}), diff {c2['diff']:+.4f} "
          f"CI {c2['ci95']}, θ-precision {c3['precision']:.3f} at coverage {c3['coverage']:.3f} "
          f"({time.time() - tt:.0f} s)", flush=True)

    # -- C5: answer time of the frozen system ----------------------------------------------------
    frozen = ChatEngine(model, index, alpha=alpha, theta=theta)
    secs = []
    for q in test:
        a = frozen.answer(q["question"])
        secs.append(a.seconds)
    secs = np.array(secs)
    print(f"answer time: median {np.median(secs) * 1000:.1f} ms, p90 {np.percentile(secs, 90) * 1000:.1f} ms",
          flush=True)

    examples = []
    for q in test[:12]:
        a = frozen.answer(q["question"])
        examples.append({"question": q["question"], "gold": q["answers"], "answer": a.text,
                         "confidence": round(a.confidence, 4), "source": a.source,
                         "hit": bool(a.text and contains_answer(a.text, q["answers"]))})

    # -- C4 ---------------------------------------------------------------------------------------
    tf = time.time()
    c4 = facts_test(model, index, alpha)
    c4_rate = c4[f"alpha={alpha:g}"]["rank1"]
    print(f"C4 facts rank 1: {c4_rate:.3f} ({time.time() - tf:.0f} s)", flush=True)

    hit1 = float(full["hit1"].mean())
    crit = {
        "C1": {"value": hit1, "ci95": bootstrap_mean(full["hit1"].astype(float)), "threshold": C1_MIN,
               "pass": hit1 >= C1_MIN},
        "C2": {**c2, "threshold_pp": C2_MIN_PP, "pass": c2["diff"] >= C2_MIN_PP and c2["ci95"][0] > 0},
        "C3": {**c3, "threshold_precision": C3_PREC, "threshold_coverage": C3_COVER,
               "pass": c3["precision"] >= C3_PREC and c3["coverage"] >= C3_COVER},
        "C4": {"value": c4_rate, "threshold": C4_MIN, "pass": c4_rate >= C4_MIN},
        "C5": {"median_seconds": float(np.median(secs)), "p90_seconds": float(np.percentile(secs, 90)),
               "threshold": C5_MAX_S, "pass": float(np.median(secs)) <= C5_MAX_S, "device": args.device,
               "official": args.device.lower().startswith("m4")},
    }
    outcome = {"useful": crit["C1"]["pass"] and crit["C3"]["pass"], "hdc_confirmed": crit["C2"]["pass"]}
    payload = {
        "schema": "engramm-chat/1", "name": "chat_stage1", "study": "docs/PREREG_CHAT.md v1.0",
        "index": info,
        "pool": {"questions": len(pool), "all_questions": len(squad), "paragraphs": n_para,
                 "all_paragraphs": len(contexts)},
        "split": {"dev": len(dev), "test": len(test), "rule": "SHAKE-256(id), first 8 bytes big-endian, bit 0"},
        "dev": {"grid": {f"{a:g}": {"hit1": float(grid[a]["hit1"].mean()), "hit5": float(grid[a]["hit5"].mean())}
                         for a in ALPHAS},
                "alpha": alpha, "theta": theta, "at_theta": dev_theta},
        "test": {"hit1": hit1, "hit5": float(full["hit5"].mean()), "bm25_hit1": float(bm25["hit1"].mean()),
                 "bm25_hit5": float(bm25["hit5"].mean()),
                 "no_candidates": int((~full["has"]).sum()),
                 "bm25_ci95": bootstrap_mean(bm25["hit1"].astype(float))},
        "criteria": crit, "outcome": outcome, "facts": c4, "examples": examples,
    }
    args.results_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now = git_revision()
    record = {**payload, "timestamp_utc": ts,
              "git": {**git_state, "changed_during_run": now.get("commit") != git_state.get("commit")},
              "environment": collect_environment(),
              "runtime": {"wall_seconds": time.time() - t0, "peak_rss_mb": peak_rss_mb()}}
    path = args.results_dir / f"chat_stage1_{args.device}_{ts}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    for k, v in crit.items():
        print(f"{k}: {'ERFÜLLT' if v['pass'] else 'VERFEHLT'}", flush=True)
    print(f"outcome: {outcome}", flush=True)
    print(path, flush=True)


if __name__ == "__main__":
    main()
