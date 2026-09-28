"""The ENGRAMM-Chat v2 tasks (docs/PREREG_CHAT_V2.md §3–§5), shared by development
(``split="dev"``) and the single test run (``split="test"``).

Every function takes a *bot factory* ``make(memory) -> ChatBot`` and a *memory factory*
``new_memory()``; the memory is reset to "nothing taught" between items by forgetting
every taught text (exact), so the same code runs with ``TextMemory`` (development) and
with the full ENGRAMM language model (test).
"""

from __future__ import annotations

import time

import numpy as np

from engramm.chat.extract import correct, exact_match, f1
from experiments.chat_v2_data import chain_dialogs as _chain_v2
from experiments.chat_v2_data import fact_dialogs as _dialogs_v2
from experiments.chat_v2_data import fact_questions as _questions_v2


def fact_questions(split: str, with_typo: bool = False) -> list[dict]:
    if split in ("dev8", "dev9"):
        return _questions_v2("dev", with_typo)
    if split in ("test4", "test5", "test6", "test7", "test8", "test9", "test10", "test11"):
        import importlib
        v = split[4:]
        return getattr(importlib.import_module(f"experiments.chat_v{v}_data"), f"fact_questions_v{v}")(with_typo)
    if split == "test3":
        from experiments.chat_v3_data import fact_questions_v3
        return fact_questions_v3(with_typo)
    return _questions_v2(split, with_typo)


def fact_dialogs(split: str) -> list[dict]:
    if split in ("dev8", "dev9"):
        from experiments.chat_dev8_data import fact_dialogs_dev8
        return fact_dialogs_dev8(split)
    if split in ("test4", "test5", "test6", "test7", "test8", "test9", "test10", "test11"):
        import importlib
        v = split[4:]
        return getattr(importlib.import_module(f"experiments.chat_v{v}_data"), f"fact_dialogs_v{v}")()
    if split == "test3":
        from experiments.chat_v3_data import fact_dialogs_v3
        return fact_dialogs_v3()
    return _dialogs_v2(split)


def chain_dialogs(split: str) -> list[dict]:
    if split in ("dev8", "dev9"):
        from experiments.chat_dev8_data import chain_dialogs_dev8
        return chain_dialogs_dev8(split)
    if split in ("test4", "test5", "test6", "test7", "test8", "test9", "test10", "test11"):
        import importlib
        v = split[4:]
        return getattr(importlib.import_module(f"experiments.chat_v{v}_data"), f"chain_dialogs_v{v}")()
    if split == "test3":
        from experiments.chat_v3_data import chain_dialogs_v3
        return chain_dialogs_v3()
    return _chain_v2(split)


def reset(bot) -> None:
    """Forget every taught text and clear the dialog context."""
    for sid in sorted(bot.user_texts()):
        bot.memory.forget(sid)
    bot.refresh()
    bot.context = {"answer": None, "atype": None, "mention": None, "last_learned": None}


def facts_task(bot, split: str) -> dict:
    """F1/F2/F3: learn the 200 statements (form A), ask in the split's phrasing (clean, typo),
    and — before learning — check that ENGRAMM abstains."""
    reset(bot)
    clean, typo = fact_questions(split), fact_questions(split, with_typo=True)
    before = []
    for q in clean:
        rep = bot.turn(q["question"])
        before.append(rep.answer is None)
        bot.context = {"answer": None, "atype": None, "mention": None, "last_learned": None}
    for q in clean:
        bot.turn(q["statement"])
    res = {}
    for name, qs in (("clean", clean), ("typo", typo)):
        ok, ok_exact, rows = [], [], []
        for q in qs:
            bot.context = {"answer": None, "atype": None, "mention": None, "last_learned": None}
            rep = bot.turn(q["question"])
            hit = correct(rep.answer, q["gold"])
            ok.append(hit)
            # exact-dictionary ablation: same facts, entity looked up by exact name
            from engramm.chat.facts import question_parts
            from engramm.chat.question import analyse
            m, rel = question_parts(q["question"], bot.is_name_initial)
            rec = bot.facts.recall(m, rel, exact=True, atype=analyse(q["question"]).atype)
            ok_exact.append(bool(rec and rec.entity_sim >= bot.cfg.entity_min and rec.confidence >= bot.cfg.fact_min
                                 and correct(rec.answer, q["gold"])))
            rows.append({"q": q["question"], "gold": q["gold"], "answer": rep.answer, "via": rep.via, "hit": hit})
        res[name] = {"correct": float(np.mean(ok)), "exact_dict": float(np.mean(ok_exact)),
                     "misses": [r for r in rows if not r["hit"]][:15]}
    res["before_abstain"] = float(np.mean(before))
    reset(bot)
    return res


def dialog_task(bot, split: str, digest_check: bool = True) -> dict:
    """D1/D2 on the "about you" dialogs, D3 on the pronoun follow-ups; also the turn times."""
    d1, d2a, d2b, d3, times, transcript, misses = [], [], [], [], [], [], []
    for dlg in fact_dialogs(split):
        reset(bot)
        for turn in dlg["turns"]:
            t0 = time.time()
            rep = bot.turn(turn["user"])
            times.append(time.time() - t0)
            transcript.append((dlg["id"], turn["user"], rep.kind, rep.answer, rep.text))
            chk = turn.get("check")
            if chk == "ask":
                hit = correct(rep.answer, turn["gold"])
                d1.append(hit)
                if not hit:
                    misses.append({"dialog": dlg["id"], "user": turn["user"], "gold": turn["gold"],
                                   "answer": rep.answer, "text": rep.text})
            elif chk == "forgotten":
                d2a.append(not (rep.answer and turn["gold"].lower() in rep.answer.lower()))
        if digest_check:
            after = bot.memory_digest()
            reset(bot)
            for s in dlg["control"]:
                bot.turn(s)
            d2b.append(bot.memory_digest() == after)
    for dlg in chain_dialogs(split):
        reset(bot)
        for turn in dlg["turns"]:
            t0 = time.time()
            rep = bot.turn(turn["user"])
            times.append(time.time() - t0)
            transcript.append((dlg["id"], turn["user"], rep.kind, rep.answer, rep.text))
            if turn.get("check") == "follow":
                hit = correct(rep.answer, turn["gold"])
                d3.append(hit)
                if not hit:
                    misses.append({"dialog": dlg["id"], "user": turn["user"], "resolved": rep.resolved,
                                   "gold": turn["gold"], "answer": rep.answer})
    reset(bot)
    return {"D1": float(np.mean(d1)), "D2a": float(np.mean(d2a)), "D2b": float(np.mean(d2b)) if d2b else None,
            "D3": float(np.mean(d3)), "n": {"D1": len(d1), "D2": len(d2a), "D3": len(d3)},
            "times": times, "transcript": transcript, "misses": misses}


def qa_task(bot, questions: list[dict]) -> dict:
    """Short answers on SQuAD / NQ questions: EM, F1, confidence, abstention, times."""
    reset(bot)
    rows = []
    for q in questions:
        bot.context = {"answer": None, "atype": None, "mention": None, "last_learned": None}
        rep = bot.ask(q["question"])
        guess = rep.guess if rep.guess is not None else rep.answer
        rows.append({"id": q["id"], "em": exact_match(guess, q["answers"]), "f1": f1(guess, q["answers"]),
                     "answered": rep.answer is not None, "conf": rep.confidence, "seconds": rep.seconds,
                     "hit_sentence": None})
    return {"rows": rows, "em": float(np.mean([r["em"] for r in rows])), "f1": float(np.mean([r["f1"] for r in rows]))}
