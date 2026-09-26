"""ENGRAMM-LM command line.

    python -m engramm.lm write "The history of the city" [--tokens 100] [--seed 0] [--explain]
    python -m engramm.lm learn --source my-notes --file notes.txt     (or --text "...")
    python -m engramm.lm forget my-notes
    python -m engramm.lm why "The capital of France is" " Paris"
    python -m engramm.lm status
    python -m engramm.lm ask "Who invented the telephone?"   (needs python -m experiments.chat_build --v2)
    python -m engramm.lm chat                                 (a conversation in the terminal)

The model directory (default ``models/lm/main/model``) holds the base model;
what you teach or forget is kept in ``user.log`` next to it and replayed on
every start, so the state is always exactly base + log.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from engramm.lm.generate import Decoding, generate
from engramm.lm.log import LoggedModel, replay_lm
from engramm.lm.model import HDCLanguageModel

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "models" / "lm" / "main" / "model"


def _load(directory: Path) -> LoggedModel:
    model = HDCLanguageModel.load(directory)
    log = directory / "user.log"
    if log.exists():
        model, _, discarded = replay_lm(log, model)
        if discarded:
            print(f"warning: {discarded} torn bytes at the end of {log} ignored", file=sys.stderr)
    return LoggedModel(model, log)


def _where(src: dict) -> str:
    if src.get("kind") == "user":
        return f"your text {src['source']!r}"
    return f"{src.get('source')}: {src.get('key', '')}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m engramm.lm", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", type=Path, default=DEFAULT_DIR)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("prompt")
    w.add_argument("--tokens", type=int, default=100)
    w.add_argument("--seed", type=int, default=0)
    w.add_argument("--temperature", type=float, default=0.9)
    w.add_argument("--top-p", type=float, default=0.8)
    w.add_argument("--cache", choices=("document", "prompt", "off"), default="off",
                   help="what the document cache may see while writing; default = the writing mode "
                        "confirmed in docs/PREREG_LM_V2.md (off, top-p 0.8); E12 used document, 0.95")
    w.add_argument("--explain", action="store_true")
    le = sub.add_parser("learn")
    le.add_argument("--source", required=True)
    g = le.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--file", type=Path)
    fo = sub.add_parser("forget")
    fo.add_argument("source")
    wy = sub.add_parser("why")
    wy.add_argument("prompt")
    wy.add_argument("continuation")
    sub.add_parser("status")
    ak = sub.add_parser("ask")
    ak.add_argument("question")
    ak.add_argument("--alternatives", type=int, default=3)
    sub.add_parser("chat")
    args = ap.parse_args(argv)

    if not (args.model / "meta.json").exists():
        print(f"no model at {args.model} — build one with python -m experiments.lm_final_model", file=sys.stderr)
        return 2
    lm = _load(args.model)
    m = lm.model
    if args.cmd == "write":
        t0 = time.time()
        g = generate(m, args.prompt, args.tokens, args.seed,
                     Decoding(temperature=args.temperature, top_p=args.top_p, cache=args.cache), explain=args.explain)
        dt = time.time() - t0
        print(args.prompt + g.text)
        print(f"\n[{len(g.ids)} tokens, {len(g.ids) / max(dt, 1e-9):.1f} tokens/s, seed {args.seed}]",
              file=sys.stderr)
        if args.explain:
            for step in g.steps:
                src = step["verbatim"][0] if step["verbatim"] else None
                where = (f"{src['kind']}:{src.get('source')}:{src.get('key', '')} ({src['match_tokens']} tok)"
                         if src else "-")
                sim = step["similar"][0]["context"] if step["similar"] else "-"
                print(f"{step['token']!r:>16}  verbatim {where}  similar-context {sim!r}")
    elif args.cmd == "learn":
        text = args.text if args.text is not None else args.file.read_text(encoding="utf-8")
        t0 = time.time()
        lm.learn_text(text, args.source)
        print(f"learnt {args.source!r} ({len(m.tok.encode(text))} tokens) in {1000 * (time.time() - t0):.1f} ms")
    elif args.cmd == "forget":
        t0 = time.time()
        kind = lm.forget(args.source)
        print(f"forgot {args.source!r} ({kind}) in {1000 * (time.time() - t0):.1f} ms")
    elif args.cmd == "why":
        ids = m.tok.encode(args.prompt)
        cont = m.tok.encode(args.continuation)
        hist = np.concatenate([[0], ids]).astype(np.uint16)
        out = m.why(hist, int(cont[0]))
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.cmd in ("ask", "chat"):
        from engramm.lm.dashboard import chat_index_dir, make_bot
        idx = chat_index_dir(args.model)
        if idx is None:
            print(f"no sentence index next to {args.model} — build it with python -m experiments.chat_build --v2",
                  file=sys.stderr)
            lm.log.close()
            return 2
        bot = make_bot(lm, idx)

        def show(rep) -> None:
            print(rep.text)
            if rep.resolved:
                print(f"  (understood as: {rep.resolved})")
            if rep.evidence and rep.kind == "answer":
                print(f"  from: “{rep.evidence}”")
            if rep.source:
                print(f"  source: {_where(rep.source)}")
            print(f"  [{rep.kind}, via {rep.via or '-'}, {1000 * rep.seconds:.0f} ms]", file=sys.stderr)

        if args.cmd == "ask":
            show(bot.turn(args.question))
        else:
            print("ENGRAMM chat — ask, tell me something, or say 'forget …'. Empty line or Ctrl+D ends.")
            while True:
                try:
                    line = input("> ")
                except EOFError:
                    break
                if not line.strip():
                    break
                show(bot.turn(line))
    elif args.cmd == "status":
        print(json.dumps({"state_digest": m.state_digest(), "epoch": m.epoch, "user_texts": list(m.user.sources),
                          "tombstones": len(m.tombstones), "train_tokens": int(len(m.tokens))}, indent=2))
    lm.log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
