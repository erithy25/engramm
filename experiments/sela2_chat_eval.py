"""M5 of docs/PREREG_SELA2.md: the Sela-2 chat model on 100 fixed prompts (data/sela2/chat_eval_prompts.json), run
exactly as in the desktop app (engramm/lm/sela_chat.py: NumPy model, chat format, sampler, stops, loop breaker).

    python -m experiments.sela2_chat_eval --weights sela2-chat.npz --out results/sela2/chat_eval.json --md results/sela2/chat_eval.md

Every prompt runs with a fixed seed. Chat and multi-turn prompts use ``SelaChat.chat`` (temperature 0.7, at most 160
tokens per reply; the model's own replies stay in the conversation); grounded prompts use ``SelaChat.grounded``
(temperature 0.2, at most 90 tokens) and its check (``verify``).

Counted per prompt (a multi-turn prompt counts once, and fails a count when any of its replies does):
- loop: generation stopped because a 4-token sequence appeared the third time;
- limit: the reply ended at the token limit without <|im_end|>;
- role leak: a line of the reply starts with a role name (user/assistant/system, also German) followed by a colon or
  the line end, or the reply contains a special-token text;
- median reply length in tokens over all replies.
Criteria (PREREG §2): loop < 5 %, limit < 5 %, role leak < 1 %, median <= 120 tokens. Grounded prompts additionally
report: answers passing the check (answerable sources), abstentions where the sources lack the answer, and false
abstentions.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROMPTS = REPO / "data" / "sela2" / "chat_eval_prompts.json"
ROLE_LEAK = re.compile(r"(?im)^\s*(user|assistant|system|nutzer|benutzer|assistent|assistentin)\s*(:|$)")
SPECIAL_TEXT = re.compile(r"<\|[a-z_0-9]+\|>")
CRITERIA = {"loop_rate": 0.05, "limit_rate": 0.05, "role_leak_rate": 0.01, "median_tokens": 120}


def role_leak(text: str) -> bool:
    return bool(ROLE_LEAK.search(text) or SPECIAL_TEXT.search(text))


def run_prompt(sc, p: dict, seed: int) -> dict:
    from engramm.lm.sela_chat import ChatState
    replies = []
    if p["kind"] == "grounded":
        src = [(t, x) for t, x in p["sources"]]
        r = sc.grounded(p["question"], src, max_tokens=90, seed=seed)
        replies.append({"user": p["question"], **r})
    else:
        st = ChatState()
        for k, u in enumerate(p["turns"]):
            r = sc.chat(st, u, max_tokens=160, seed=seed + k)
            replies.append({"user": u, **r})
    for r in replies:
        r["role_leak"] = role_leak(r["text"])
    out = {"id": p["id"], "lang": p["lang"], "kind": p["kind"], "replies": replies,
           "loop": any(r["stop"] == "loop" for r in replies), "limit": any(r["stop"] == "limit" for r in replies),
           "role_leak": any(r["role_leak"] for r in replies)}
    if p["kind"] == "grounded":
        r = replies[0]
        out["no_answer"] = bool(p.get("no_answer"))
        out["verified"] = bool(r["verified"])
        out["abstained"] = bool(r["abstained"])
    return out


def summarize(rows: list[dict]) -> dict:
    def rates(sel: list[dict]) -> dict:
        n = len(sel)
        toks = [r["tokens"] for x in sel for r in x["replies"]]
        return {"prompts": n, "replies": len(toks),
                "loop_rate": sum(x["loop"] for x in sel) / n, "limit_rate": sum(x["limit"] for x in sel) / n,
                "role_leak_rate": sum(x["role_leak"] for x in sel) / n,
                "median_tokens": float(statistics.median(toks)) if toks else 0.0,
                "stop_reasons": {k: sum(r["stop"] == k for x in sel for r in x["replies"])
                                 for k in ("stop", "limit", "loop", "context")}}
    res = {"all": rates(rows)}
    for lang in ("en", "de"):
        sel = [x for x in rows if x["lang"] == lang]
        if sel:
            res[lang] = rates(sel)
    for kind in sorted({x["kind"] for x in rows}):
        res[f"kind_{kind}"] = rates([x for x in rows if x["kind"] == kind])
    g = [x for x in rows if x["kind"] == "grounded"]
    if g:
        ans = [x for x in g if not x["no_answer"]]
        noans = [x for x in g if x["no_answer"]]
        res["grounded"] = {
            "answerable": len(ans), "answerable_verified": sum(x["verified"] for x in ans),
            "answerable_false_abstention": sum(x["abstained"] for x in ans),
            "no_answer": len(noans), "no_answer_abstained": sum(x["abstained"] for x in noans)}
    a = res["all"]
    res["criteria"] = {k: {"value": a[k], "limit": v, "met": (a[k] <= v) if k == "median_tokens" else (a[k] < v)}
                       for k, v in CRITERIA.items()}
    res["criteria_met"] = all(c["met"] for c in res["criteria"].values())
    return res


def to_markdown(res: dict, rows: list[dict]) -> str:
    lines = ["# Sela-2 Chat: 100 feste Prompts (M5)", "",
             f"Gewichte `{res['weights']}` (SHA-256 `{res['weights_sha256'][:16]}…`), {res['date_utc']}.", "",
             "| Kriterium | Wert | Grenze | erfüllt |", "|---|---|---|---|"]
    for k, c in res["summary"]["criteria"].items():
        v = f"{c['value']:.1%}" if k != "median_tokens" else f"{c['value']:.0f}"
        lim = f"< {c['limit']:.0%}" if k != "median_tokens" else f"≤ {c['limit']}"
        lines.append(f"| {k} | {v} | {lim} | {'ja' if c['met'] else 'nein'} |")
    g = res["summary"].get("grounded")
    if g:
        lines += ["", f"Quellen-Fragen: {g['answerable_verified']}/{g['answerable']} beantwortbare bestehen die Prüfung, "
                      f"{g['answerable_false_abstention']} fälschlich abgelehnt; {g['no_answer_abstained']}/{g['no_answer']} "
                      "unbeantwortbare korrekt abgelehnt."]
    lines += ["", "## Alle Antworten", ""]
    for x in rows:
        flags = [f for f in ("loop", "limit", "role_leak") if x[f]]
        if x["kind"] == "grounded":
            flags.append("geprüft" if x["verified"] else ("abgelehnt" if x["abstained"] else "Prüfung nicht bestanden"))
        lines.append(f"### {x['id']} ({x['kind']}){' – ' + ', '.join(flags) if flags else ''}")
        for r in x["replies"]:
            lines.append(f"- **Nutzer:** {r['user']}")
            lines.append(f"  **Sela-2** ({r['tokens']} Token, {r['stop']}): {r['text']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True, help="sela-npz-2 file of the chat model")
    ap.add_argument("--tokenizer", default=None, help="default: the file named in the weights' header (data/)")
    ap.add_argument("--prompts", default=str(PROMPTS))
    ap.add_argument("--limit", type=int, default=0, help="smoke test: only the first N prompts")
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", default="")
    args = ap.parse_args()
    from engramm.lm.sela_chat import SelaChat
    from engramm.lm.tokenizer import LMTokenizer, file_sha256
    tok = LMTokenizer(args.tokenizer, sha256=None) if args.tokenizer else None
    sc = SelaChat(args.weights, tokenizer=tok)
    spec = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    prompts = spec["prompts"][:args.limit or None]
    if not args.limit and (len(prompts) != 100 or len({p["id"] for p in prompts}) != 100):
        raise SystemExit(f"{args.prompts}: expected 100 prompts with distinct ids, found {len(prompts)}")
    rows, t0 = [], time.time()
    for i, p in enumerate(prompts):
        rows.append(run_prompt(sc, p, seed=1000 + 10 * i))
        print(f"[{i + 1}/{len(prompts)}] {p['id']}: " + " | ".join(r["text"][:70].replace("\n", " ")
                                                                    for r in rows[-1]["replies"]), flush=True)
    res = {"what": "M5 of docs/PREREG_SELA2.md (experiments/sela2_chat_eval.py)", "weights": Path(args.weights).name,
           "weights_sha256": file_sha256(args.weights), "prompts_sha256": file_sha256(args.prompts),
           "tokenizer_sha256": sc.tok.sha256, "limit": args.limit, "seconds": round(time.time() - t0, 1),
           "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "summary": summarize(rows), "rows": rows}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.md:
        Path(args.md).write_text(to_markdown(res, rows), encoding="utf-8")
    s = res["summary"]
    print(json.dumps({"criteria_met": s["criteria_met"], **{k: c["value"] for k, c in s["criteria"].items()},
                      "grounded": s.get("grounded")}, indent=1))


if __name__ == "__main__":
    main()
