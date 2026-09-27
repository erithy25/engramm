"""ENGRAMM-Chat v2 — the single preregistered test run (docs/PREREG_CHAT_V2.md §5).

    python -m experiments.chat_build --v2          # once: the stage 1.1 index (+ capitalisation counts)
    python -m experiments.chat_v2_eval             # R1–R2, F1–F3, D1–D3, A1–A3, U2–U3 (U1 = tests/test_chat_ui.py)

Runs the frozen configuration (``engramm/chat/config.py``) with the full ENGRAMM
language model as memory — exactly what the dashboard and ``python -m engramm.lm chat``
use. Writes one record to ``--results-dir`` (default: the scratch dir, copied to
``results/chat/`` afterwards).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from engramm.chat.bot import ChatBot
from engramm.chat.config import FROZEN, cap_ratio
from engramm.chat.corpus import Corpus
from engramm.chat.extract import exact_match, f1
from engramm.lm.chat import ChatEngine, SentenceIndex, contains_answer
from engramm.lm.log import LoggedModel, replay_lm
from engramm.lm.model import HDCLanguageModel
from engramm.repro import collect_environment, git_revision, peak_rss_mb
from experiments.chat_v2_common import MODEL_DIR, squad_v2_splits
from experiments.chat_v2_data import manifest, nq_splits
from experiments.chat_v2_tasks import dialog_task, facts_task, fact_dialogs, reset

BOOT, SEED = 2000, 42
FRESH = {"answer": None, "atype": None, "mention": None, "last_learned": None}


def paired(a: np.ndarray, b: np.ndarray) -> dict:
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(a), size=(BOOT, len(a)))
    d = a[idx].mean(axis=1) - b[idx].mean(axis=1)
    return {"diff": float(a.mean() - b.mean()), "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]}


def mean_ci(a: np.ndarray) -> list[float]:
    rng = np.random.default_rng(SEED)
    m = a[rng.integers(0, len(a), size=(BOOT, len(a)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def qa(bot: ChatBot, stage1: ChatEngine, questions: list[dict], label: str) -> dict:
    """Per question: stage-1 Hit@1, v2 Hit@1, short answer EM/F1 (best guess), answered, time."""
    rows = []
    t0 = time.time()
    for i, q in enumerate(questions):
        s1, _, _ = stage1.rank(q["question"])
        h1 = bool(s1) and contains_answer(stage1.sentence_text(s1[0]), q["answers"])
        bot.context = dict(FRESH)
        rep = bot.ask(q["question"])
        top = getattr(bot, "last_rows", None) or []
        h2 = bool(top) and contains_answer(top[0][3], q["answers"])
        guess = rep.guess if rep.guess is not None else rep.answer
        rows.append({"hit1_stage1": h1, "hit1_v2": h2, "em": exact_match(guess, q["answers"]),
                     "f1": f1(guess, q["answers"]), "answered": rep.answer is not None,
                     "em_answered": exact_match(rep.answer, q["answers"]) if rep.answer else 0.0,
                     "conf": rep.confidence, "seconds": rep.seconds})
        if i % 250 == 0:
            print(f"{label}: {i}/{len(questions)} ({time.time() - t0:.0f} s)", flush=True)
    return {k: np.array([r[k] for r in rows]) for k in rows[0]}


def restart_check(model, corpus, cap, n_dialogs: int = 20, split: str = "test") -> dict:
    """Tell the facts of some test dialogs through a logged memory, then 'restart':
    clear the memory, replay the log onto the base model and compare state and answers."""
    tmp = Path(tempfile.mkdtemp()) / "chat.log"
    lm = LoggedModel(model, tmp)
    bot = ChatBot(lm, corpus, FROZEN, cap)
    reset(bot)
    asks = []
    for dlg in fact_dialogs(split)[:n_dialogs]:
        for t in dlg["turns"]:
            if "check" not in t:
                bot.turn(t["user"])
            elif t["check"] == "ask":
                asks.append(t["user"])
    before = bot.memory_digest()
    answers_before = []
    for a in asks:
        bot.context = dict(FRESH)
        answers_before.append(bot.turn(a).answer)
    lm.log.close()
    for sid in sorted(model.user_texts):          # the "restart": back to the bare base model
        model.forget(sid)
    model, n_events, discarded = replay_lm(tmp, model)
    bot2 = ChatBot(model, corpus, FROZEN, cap)
    after = bot2.memory_digest()
    answers_after = []
    for a in asks:
        bot2.context = dict(FRESH)
        answers_after.append(bot2.turn(a).answer)
    reset(bot2)
    return {"digest_equal": before == after, "answers_equal": answers_before == answers_after,
            "events": n_events, "discarded_bytes": discarded, "questions": len(asks)}


def transcript_digest(tr: list) -> str:
    return hashlib.sha256(json.dumps(tr, ensure_ascii=False).encode()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=MODEL_DIR)
    ap.add_argument("--device", default="container")
    ap.add_argument("--results-dir", type=Path, default=Path(tempfile.gettempdir()) / "engramm_chat_v2")
    ap.add_argument("--split", choices=("test", "dev", "test3", "test4", "test5", "test6", "test7", "test8", "test9"), default="test",
                    help="test = v2 test (PREREG_CHAT_V2), test3 = v3 test (PREREG_CHAT_V3), "
                         "dev = dry run of this script on development data (never reported)")
    ap.add_argument("--limit", type=int, default=0, help="dry run: questions per QA set")
    args = ap.parse_args()
    if args.split == "dev" and not args.limit:
        args.limit = 50
    git_state, t0 = git_revision(), time.time()

    model = HDCLanguageModel.load(args.model)
    for sid in sorted(model.user_texts):
        model.forget(sid)
    idx2 = args.model.parent / "chat2"
    corpus = Corpus.from_model(model, idx2)
    cap = cap_ratio(idx2)
    bot = ChatBot(model, corpus, FROZEN, cap)
    stage1 = ChatEngine(model, SentenceIndex.load(args.model.parent / "chat"), alpha=2.0)
    print(f"loaded in {time.time() - t0:.0f} s; index v2 {corpus.index.n:,} sentences", flush=True)

    sq_dev, sq_test = squad_v2_splits(corpus, args.model)
    nq_dev, nq_test = nq_splits()
    data_manifest = manifest()
    study = "docs/PREREG_CHAT_V2.md v1.1"
    if args.split == "dev":
        sq_test, nq_test = sq_dev[:args.limit], nq_dev[:args.limit]
    elif args.split in ("test3", "test4", "test5", "test6", "test7", "test8", "test9"):
        import importlib

        from experiments.chat_eval import load_squad, split as split1
        from experiments.chat_v2_data import CACHE
        v = args.split[-1]
        mod = importlib.import_module(f"experiments.chat_v{v}_data")
        pool_ids = set(json.loads((CACHE / "squad_pool_v1.json").read_text())["pool"])
        pool = [q for q in load_squad() if q["id"] in pool_ids]
        d1, t1 = split1(pool)
        sq_test = getattr(mod, f"squad_v{v}_test")(pool, {q["id"] for q in d1 + t1})
        nq_test = getattr(mod, f"nq_v{v}_test")()
        data_manifest = mod.manifest()
        study = f"docs/PREREG_CHAT_V{v}.md v1.0"

    # -- stage 1.1 and 4 on SQuAD-Test2 and NQ-Test ------------------------------------------
    sq = qa(bot, stage1, sq_test, "squad")
    nq = qa(bot, stage1, nq_test, "nq")
    r1 = paired(sq["hit1_v2"].astype(float), sq["hit1_stage1"].astype(float))
    r2 = paired(nq["hit1_v2"].astype(float), nq["hit1_stage1"].astype(float))
    answered = sq["answered"]
    a2_cov = float(answered.mean())
    a2_prec = float(sq["em_answered"][answered].mean()) if answered.any() else 0.0
    print(f"R1 {r1}  R2 {r2}  A1 EM {sq['em'].mean():.3f} F1 {sq['f1'].mean():.3f}  "
          f"A2 {a2_prec:.3f}@{a2_cov:.3f}  A3 {nq['em'].mean():.3f}", flush=True)

    # -- stage 2: invented facts -----------------------------------------------------------------
    tf = time.time()
    facts = facts_task(bot, args.split)
    print(f"facts ({time.time() - tf:.0f} s): clean {facts['clean']['correct']:.3f} typo {facts['typo']['correct']:.3f} "
          f"exact-dict {facts['typo']['exact_dict']:.3f} before-abstain {facts['before_abstain']:.3f}", flush=True)

    # -- stage 3: dialogs --------------------------------------------------------------------------
    td = time.time()
    dia = dialog_task(bot, args.split)
    print(f"dialogs ({time.time() - td:.0f} s): D1 {dia['D1']:.3f} D2a {dia['D2a']:.3f} D2b {dia['D2b']:.3f} "
          f"D3 {dia['D3']:.3f}", flush=True)

    # -- stage 5: time and determinism ----------------------------------------------------------------
    times = np.concatenate([np.asarray(dia["times"]), sq["seconds"]])
    second = dialog_task(ChatBot(model, corpus, FROZEN, cap), args.split)
    t1, t2 = transcript_digest(dia["transcript"]), transcript_digest(second["transcript"])
    restart = restart_check(model, corpus, cap, split=args.split)
    print(f"U2 median {np.median(times) * 1000:.0f} ms; U3 transcripts equal {t1 == t2}, restart {restart}", flush=True)

    ft = facts["typo"]
    crit = {
        "R1": {**r1, "stage1": float(sq["hit1_stage1"].mean()), "v2": float(sq["hit1_v2"].mean()),
               "pass": r1["diff"] >= 0.03 and r1["ci95"][0] > 0},
        "R2": {**r2, "stage1": float(nq["hit1_stage1"].mean()), "v2": float(nq["hit1_v2"].mean()),
               "pass": r2["diff"] >= 0.02 and r2["ci95"][0] > 0},
        "F1": {"value": facts["clean"]["correct"], "pass": facts["clean"]["correct"] >= 0.90},
        "F2": {"value": ft["correct"], "exact_dict": ft["exact_dict"], "lead": ft["correct"] - ft["exact_dict"],
               "pass": ft["correct"] >= 0.75 and ft["correct"] - ft["exact_dict"] >= 0.30},
        "F3": {"value": facts["before_abstain"], "pass": facts["before_abstain"] >= 0.90},
        "D1": {"value": dia["D1"], "n": dia["n"]["D1"], "pass": dia["D1"] >= 0.90},
        "D2": {"a": dia["D2a"], "b": dia["D2b"], "n": dia["n"]["D2"], "pass": dia["D2a"] == 1.0 and dia["D2b"] == 1.0},
        "D3": {"value": dia["D3"], "n": dia["n"]["D3"], "pass": dia["D3"] >= 0.80},
        "A1": {"em": float(sq["em"].mean()), "f1": float(sq["f1"].mean()), "em_ci95": mean_ci(sq["em"]),
               "pass": sq["em"].mean() >= 0.20 and sq["f1"].mean() >= 0.30},
        "A2": {"precision": a2_prec, "coverage": a2_cov, "theta": FROZEN.theta,
               "pass": a2_prec >= 0.50 and a2_cov >= 0.20},
        "A3": {"em": float(nq["em"].mean()), "em_ci95": mean_ci(nq["em"]), "f1": float(nq["f1"].mean()),
               "pass": nq["em"].mean() >= 0.05},
        "U2": {"median_seconds": float(np.median(times)), "p90_seconds": float(np.percentile(times, 90)),
               "device": args.device, "official": args.device.lower().startswith("m4"),
               "pass": float(np.median(times)) <= 1.0},
        "U3": {"transcripts_equal": t1 == t2, "transcript_sha256": t1, **restart,
               "pass": t1 == t2 and restart["digest_equal"] and restart["answers_equal"]},
    }
    stages = {"1.1": crit["R1"]["pass"] and crit["R2"]["pass"],
              "2": crit["F1"]["pass"] and crit["F2"]["pass"] and crit["F3"]["pass"],
              "3": crit["D1"]["pass"] and crit["D2"]["pass"] and crit["D3"]["pass"],
              "4": crit["A1"]["pass"] and crit["A2"]["pass"] and crit["A3"]["pass"],
              "5 (U2, U3; U1 = browser test)": crit["U2"]["pass"] and crit["U3"]["pass"]}
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now = git_revision()
    record = {
        "schema": "engramm-chat/2", "name": f"chat_{args.split}", "study": study,
        "split": args.split,
        "timestamp_utc": ts, "config": repr(FROZEN), "data_manifest": data_manifest,
        "index": json.loads((idx2 / "info.json").read_text()),
        "n": {"squad_test": len(sq_test), "nq_test": len(nq_test)},
        "criteria": crit, "stages_met": stages,
        "facts_misses": {"clean": facts["clean"]["misses"], "typo": ft["misses"]},
        "dialog_misses": dia["misses"][:40],
        "git": {**git_state, "changed_during_run": now.get("commit") != git_state.get("commit")},
        "environment": collect_environment(),
        "runtime": {"wall_seconds": time.time() - t0, "peak_rss_mb": peak_rss_mb()},
    }
    args.results_dir.mkdir(parents=True, exist_ok=True)
    path = args.results_dir / f"chat_{args.split}_{args.device}_{ts}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str) + "\n")
    for k, v in crit.items():
        print(f"{k}: {'ERFÜLLT' if v['pass'] else 'VERFEHLT'}", flush=True)
    print(f"stages: {stages}", flush=True)
    print(path, flush=True)


if __name__ == "__main__":
    main()
