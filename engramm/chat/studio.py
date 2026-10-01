"""Authoring studio v0 for the conversation bank (data/conv/*.yaml).

    python -m engramm.chat.studio check      # validate: regexes, duplicates, placeholders, examples
    python -m engramm.chat.studio build      # check, then write engramm/chat/conv_bank.json
    python -m engramm.chat.studio coverage   # which intent each example and test message reaches
    python -m engramm.chat.studio try "hi there" "tell me a joke"

A check fails when:
* a pattern or trigger is not a valid regex, or an id appears twice;
* a response uses a placeholder the intent cannot fill;
* an intent's own example is caught first by an earlier intent's pattern (routing conflict),
  or is not matched by its own patterns (then it only works through the nearest-example match);
* a fun fact or quote has no source.
Warnings (printed, not failing): intents with fewer than three responses.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "conv"
FILES = ("smalltalk", "empathy", "safety", "fun", "replies", "writing", "de", "daily")
PLACEHOLDERS = {"name", "x", "noun", "subject", "title", "topic", "category", "evidence", "last", "more", "bot",
                "timeword", "fact"}


def load_sources(src: Path = SRC) -> dict:
    import yaml
    # BaseLoader: every scalar stays a string ("yes", "no", "on" are words here, not booleans)
    return {name: yaml.load((src / f"{name}.yaml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
            for name in FILES}


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", text))


def check(data: dict) -> tuple[list[str], list[str]]:
    from engramm.chat.bank import normalise
    errors, warnings = [], []
    seen = set()
    compiled = []
    for it in data["smalltalk"]["intents"]:
        iid = it.get("id")
        if not iid or iid in seen:
            errors.append(f"intent id missing or twice: {iid!r}")
        seen.add(iid)
        pats = []
        for p in it.get("patterns", []):
            try:
                pats.append(re.compile(p))
            except re.error as e:
                errors.append(f"{iid}: bad pattern {p!r}: {e}")
        compiled.append((iid, pats, it))
        groups = {g for rx in pats for g in rx.groupindex}
        allowed = {"name"} | ({"x"} if groups else set())
        for r in it.get("responses", []) + it.get("responses_named", []):
            bad = _placeholders(r) - allowed
            if bad:
                errors.append(f"{iid}: response uses {sorted(bad)}: {r[:60]!r}")
        for r in it.get("responses", []):
            if "{name}" in r:
                errors.append(f"{iid}: {{name}} belongs in responses_named: {r[:60]!r}")
        if not it.get("action") and len(it.get("responses", [])) < 3:
            warnings.append(f"{iid}: only {len(it.get('responses', []))} response(s)")
        if not it.get("action") and not it.get("responses"):
            errors.append(f"{iid}: no responses and no action")
    # routing: each example must reach its own intent first
    for iid, pats, it in compiled:
        for ex in it.get("examples", []):
            forms = (normalise(ex, fillers=False), normalise(ex))
            first = None
            for jid, jp, _ in compiled:
                if any(rx.fullmatch(f) for rx in jp for f in forms):
                    first = jid
                    break
            if first is None:
                errors.append(f"{iid}: example {ex!r} matches no pattern")
            elif first != iid:
                errors.append(f"{iid}: example {ex!r} is caught first by {first!r}")
    for c in data["empathy"]["categories"]:
        for t in c["triggers"]:
            try:
                re.compile(t)
            except re.error as e:
                errors.append(f"empathy {c['id']}: bad trigger: {e}")
        if len(c["responses"]) < 2:
            warnings.append(f"empathy {c['id']}: only {len(c['responses'])} response(s)")
    for kind in ("crisis", "refuse"):
        for r in data["safety"].get(kind, []):
            for t in r["triggers"]:
                try:
                    re.compile(t)
                except re.error as e:
                    errors.append(f"safety {r['id']}: bad trigger: {e}")
            if not r.get("response"):
                errors.append(f"safety {r['id']}: no response")
    for f in data["fun"]["facts"]:
        if not f.get("src"):
            errors.append(f"fact without source: {f.get('text', '')[:50]!r}")
    for q in data["fun"]["quotes"]:
        if not q.get("by"):
            errors.append(f"quote without author: {q.get('text', '')[:50]!r}")
    for name, pp in data["writing"]["purposes"].items():
        for key in pp.get("keys", []):
            try:
                re.compile(key)
            except re.error as e:
                errors.append(f"writing {name}: bad key {key!r}: {e}")
        for tone in ("formal", "casual"):
            if tone not in pp or not pp[tone].get("body"):
                errors.append(f"writing {name}: no {tone} body")
    for key in data["fun"]["ask_order"]:
        if key not in data["fun"]["questions"]:
            errors.append(f"ask_order names unknown question {key!r}")

    de = data.get("de")
    if de:
        ids = set()
        for it in de["intents"]:
            if it["id"] in ids:
                errors.append(f"de: intent id twice: {it['id']}")
            ids.add(it["id"])
            if len(it.get("responses", [])) < 3:
                warnings.append(f"de {it['id']}: only {len(it.get('responses', []))} response(s)")
        rxs = [p for it in de["intents"] for p in it["patterns"]]
        rxs += [t for c in de["feelings"]["categories"] for t in c["triggers"]]
        rxs += [t for k in ("crisis", "refuse") for r in de["safety"].get(k, []) for t in r["triggers"]]
        for p in rxs:
            try:
                re.compile(p)
            except re.error as e:
                errors.append(f"de: bad pattern {p!r}: {e}")
        for r in de["safety"].get("crisis", []):
            if not re.search(r"\d{3}", r["response"]):
                errors.append(f"de crisis {r['id']}: the response names no helpline number")

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for v in node:
                walk(v, path)
        elif isinstance(node, str):
            bad = _placeholders(node) - PLACEHOLDERS
            if bad:
                errors.append(f"replies {path}: unknown placeholder {sorted(bad)}")
    walk(data["replies"], "")
    daily = data.get("daily") or {}
    walk(daily, "daily")
    for game in ("quiz", "riddle"):
        for it in (daily.get(game) or {}).get("items", []):
            if not it.get("q") or not it.get("a"):
                errors.append(f"daily {game}: item without question or answer: {it!r}")
    for kind, spec in ((daily.get("recommend") or {}).items()):
        if isinstance(spec, dict) and "items" in spec:
            for it in spec["items"]:
                if isinstance(it, dict) and not it.get("x"):
                    errors.append(f"daily recommend {kind}: item without text: {it!r}")
            if len(spec["items"]) < 6:
                warnings.append(f"daily recommend {kind}: only {len(spec['items'])} items")
    return errors, warnings


def build(out: Path | None = None) -> Path:
    from engramm.chat.bank import BANK_PATH
    data = load_sources()
    errors, warnings = check(data)
    for w in warnings:
        print("warning:", w)
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(f"{len(errors)} error(s); nothing written")
    compiled = {"version": 1, "smalltalk": data["smalltalk"], "empathy": data["empathy"],
                "safety": data["safety"], "fun": data["fun"], "replies": data["replies"], "writing": data["writing"], "de": data["de"],
                "daily": data["daily"]}
    out = Path(out or BANK_PATH)
    out.write_text(json.dumps(compiled, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    n_int = len(data["smalltalk"]["intents"])
    n_resp = sum(len(i.get("responses", [])) + len(i.get("responses_named", [])) for i in data["smalltalk"]["intents"])
    print(f"wrote {out} — {n_int} intents, {n_resp} responses, {len(data['empathy']['categories'])} feelings, "
          f"{len(data['fun']['jokes'])} jokes, {len(data['fun']['facts'])} facts, {len(data['fun']['quotes'])} quotes")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m engramm.chat.studio", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("check", "build", "coverage", "try"))
    ap.add_argument("messages", nargs="*")
    args = ap.parse_args(argv)
    if args.command == "build":
        build()
        return 0
    data = load_sources()
    if args.command == "check":
        errors, warnings = check(data)
        for w in warnings:
            print("warning:", w)
        for e in errors:
            print("ERROR:", e)
        print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
        return 1 if errors else 0
    from engramm.chat.acts import classify
    from engramm.chat.bank import Bank
    bank = Bank({"smalltalk": data["smalltalk"], "empathy": data["empathy"], "safety": data["safety"],
                 "fun": data["fun"], "replies": data["replies"], "writing": data["writing"], "de": data["de"],
                 "daily": data["daily"]})
    msgs = args.messages
    if args.command == "coverage" and not msgs:
        msgs = [ex for it in data["smalltalk"]["intents"] for ex in it.get("examples", [])]
    for m in msgs:
        units = classify(m, bank)
        print(f"{m!r:45} → " + " | ".join(f"{u.act}{':' + u.intent if u.intent else ''}" for u in units))
    return 0


if __name__ == "__main__":
    sys.exit(main())
