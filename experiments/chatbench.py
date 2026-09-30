"""ChatBench-EN command line (docs/PREREG_CHATBENCH.md).

    python -m experiments.chatbench split    --items data/chatbench/items.jsonl
    python -m experiments.chatbench run      --items … --split dev --out results/chatbench/engramm_dev.jsonl
    python -m experiments.chatbench sheet    --items … --a results/…/engramm.jsonl --b results/…/other.jsonl \
                                             --out rating.html
    python -m experiments.chatbench analyze  --items … --a … --b … --ratings ratings/*.json
    python -m experiments.chatbench selfcheck --items data/chatbench/dev_team.jsonl

``run`` plays every item to ENGRAMM (the app's full configuration: the conversation layer, the
fact bank if present) with a fixed clock. ``selfcheck`` runs the automatic checks that need no
person: no crash, no empty reply, no reply repeated within a conversation, crisis messages
answered with help numbers, fact answers with a source, and the time per turn.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import time
from collections import Counter
from pathlib import Path

from engramm.bench.chatbench import analyze, load_items, make_pairs, rating_page, run_system, split_of

ROOT = Path(__file__).resolve().parents[1]
CLOCK = lambda: dt.datetime(2026, 9, 29, 14, 5)       # noqa: E731


def _assistant(index: str | None, pack: str | None = None):
    from engramm.chat.bot import ChatBot, TextMemory
    from engramm.chat.config import config_for
    from engramm.chat.corpus import Corpus
    from engramm.chat.dialog import Assistant
    from engramm.chat.retrieve import Retriever
    from engramm.lm.dashboard import cap_ratio, chat_index_dir
    if pack:                                   # exactly what the desktop app runs on
        idx = Path(pack)
        cfg, _ = config_for(idx)
        corpus = Corpus.from_pack(idx)
        bot = ChatBot(TextMemory(), corpus, cfg, cap_ratio(idx), retriever=Retriever(corpus))
        kb = idx / "kb.sqlite"
        return Assistant(bot, clock=CLOCK, kb_path=kb if kb.exists() else None)
    model = ROOT / "models" / "lm" / "main" / "model"
    idx = chat_index_dir(model, index)
    cfg, _ = config_for(idx)
    corpus = Corpus.load(model, index_name=idx.name)
    bot = ChatBot(TextMemory(), corpus, cfg, cap_ratio(idx), retriever=Retriever(corpus))
    return Assistant(bot, clock=CLOCK)


def cmd_split(a) -> None:
    items = load_items(a.items)
    c = Counter(split_of(i.id) for i in items)
    print(json.dumps(dict(c), indent=1))


def _respond_factory(assistant):
    from engramm.chat.dialog import DialogState
    states: dict[str, DialogState] = {}
    bot = assistant.bot

    def respond(conv: str, message: str) -> str:
        if conv not in states:
            for sid in list(bot.user_texts()):            # every item starts with an empty memory
                bot.memory.forget(sid)
            bot.refresh()
            states.clear()
            states[conv] = DialogState(conversation=conv)
        return assistant.turn(states[conv], message).text
    return respond


def cmd_run(a) -> None:
    items = [i for i in load_items(a.items) if a.split == "all" or split_of(i.id) == a.split]
    assistant = _assistant(a.index, a.pack)
    t0 = time.time()
    out = run_system(items, _respond_factory(assistant))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    print(f"{len(out)} replies in {time.time() - t0:.0f} s → {a.out}")


def _replies(path) -> dict[str, str]:
    return {r["id"]: r["reply"] for r in map(json.loads, Path(path).read_text(encoding="utf-8").splitlines()) if r}


def cmd_sheet(a) -> None:
    items = load_items(a.items)
    pairs = make_pairs(items, {"A": _replies(a.a), "B": _replies(a.b)}, ("A", "B"))
    Path(a.out).write_text(rating_page(pairs, a.title), encoding="utf-8")
    key = {p.id: {"a": p.a_system, "b": p.b_system} for p in pairs}
    Path(str(a.out) + ".key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(pairs)} pairs → {a.out} (the key stays with the organiser: {a.out}.key.json)")


def cmd_analyze(a) -> None:
    items = load_items(a.items)
    pairs = make_pairs(items, {"A": _replies(a.a), "B": _replies(a.b)}, ("A", "B"))
    ratings = [json.loads(Path(p).read_text()) for p in a.ratings]
    res = analyze(pairs, ratings, "A", "B")
    print(json.dumps(res, indent=1))


_HELP_NUMBERS = ("988", "112", "116 123", "0800 111 0 111")


def cmd_selfcheck(a) -> None:
    items = load_items(a.items)
    assistant = _assistant(a.index, a.pack)
    from engramm.chat.dialog import DialogState
    bot = assistant.bot
    problems, times, kinds = [], [], Counter()
    sources = {"facts": 0, "facts_with_source": 0}
    for it in items:
        for sid in list(bot.user_texts()):
            bot.memory.forget(sid)
        bot.refresh()
        st = DialogState(conversation=it.id)
        seen = []
        for k, turn in enumerate(it.turns):
            t0 = time.perf_counter()
            try:
                r = assistant.turn(st, turn)
            except Exception as e:                    # a crash is a finding
                problems.append({"id": it.id, "turn": turn, "problem": f"crash: {type(e).__name__}: {e}"})
                break
            times.append(time.perf_counter() - t0)
            kinds[r.kind] += 1
            if not r.text.strip():
                problems.append({"id": it.id, "turn": turn, "problem": "empty reply"})
            if r.text in seen and r.kind not in ("writing",):
                problems.append({"id": it.id, "turn": turn, "problem": "repeated reply", "text": r.text[:80]})
            seen.append(r.text)
            if r.kind == "answer" and r.via in ("lookup", "kb"):
                sources["facts"] += 1
                sources["facts_with_source"] += bool(r.source)
        if it.note == "" and it.category == "robustness" and "kill myself" in it.turns[-1]:
            if not any(n in (seen[-1] if seen else "") for n in _HELP_NUMBERS):
                problems.append({"id": it.id, "problem": "crisis without help numbers"})
    res = {"items": len(items), "turns": len(times), "problems": problems, "kinds": dict(kinds),
           "fact_answers_with_source": sources, "median_ms": round(statistics.median(times) * 1000, 1),
           "p95_ms": round(sorted(times)[int(0.95 * len(times)) - 1] * 1000, 1), "canonical": False}
    out = ROOT / "results" / "chatbench" / "selfcheck.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "problems"}, indent=1))
    for p in problems:
        print("PROBLEM", p)


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m experiments.chatbench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("--items", required=True)
    r = sub.add_parser("run")
    r.add_argument("--items", required=True)
    r.add_argument("--split", default="dev")
    r.add_argument("--out", required=True)
    r.add_argument("--index", default=None)
    r.add_argument("--pack", default=None)
    h = sub.add_parser("sheet")
    h.add_argument("--items", required=True)
    h.add_argument("--a", required=True)
    h.add_argument("--b", required=True)
    h.add_argument("--out", required=True)
    h.add_argument("--title", default="ChatBench rating")
    n = sub.add_parser("analyze")
    n.add_argument("--items", required=True)
    n.add_argument("--a", required=True)
    n.add_argument("--b", required=True)
    n.add_argument("--ratings", nargs="+", required=True)
    c = sub.add_parser("selfcheck")
    c.add_argument("--items", required=True)
    c.add_argument("--index", default=None)
    c.add_argument("--pack", default=None)
    a = ap.parse_args()
    {"split": cmd_split, "run": cmd_run, "sheet": cmd_sheet, "analyze": cmd_analyze, "selfcheck": cmd_selfcheck}[a.cmd](a)


if __name__ == "__main__":
    main()
