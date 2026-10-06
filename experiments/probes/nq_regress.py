"""Regression guard on NQ-open (the first 400 validation questions): every answer through the chat service, written
to a file; with --ref, the number of answers that changed against an earlier file (the guard is "0 changed").

    python -m experiments.probes.nq_regress OUT.json [--ref REF.json] [--pack DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--ref", type=Path)
    ap.add_argument("--pack", type=Path, default=Path("/dev/shm/engramm/pack-b3"))
    ap.add_argument("--n", type=int, default=400)
    a = ap.parse_args(argv)
    import pyarrow.parquet as pq
    from engramm.app.server import ChatService
    rows = pq.read_table(ROOT / "data/cache/chat/nq_open_validation.parquet").to_pylist()[:a.n]
    work = Path(tempfile.mkdtemp())
    try:
        svc = ChatService("unused", pack=a.pack, memory_path=work / "m.log")
        svc.load()
        norm = lambda s: re.sub(r"[^a-z0-9 ]", "", (s or "").lower())   # noqa: E731
        out = []
        for i, r in enumerate(rows):
            ans = svc.chat(f"q{i}", r["question"]).get("answer")
            gold = [g for g in r["answer"] if norm(g)]
            out.append({"q": r["question"], "a": ans,
                        "ok": bool(ans) and any(norm(g) in norm(ans) or norm(ans) in norm(g) for g in gold)})
    finally:
        shutil.rmtree(work, ignore_errors=True)
    a.out.write_text(json.dumps(out))
    answered = [x for x in out if x["a"]]
    print(f"answered {len(answered)}, correct {sum(x['ok'] for x in answered)}")
    if a.ref:
        ref = json.loads(a.ref.read_text())
        print("changed vs ref:", sum((x["a"] or "") != (y["a"] or "") for x, y in zip(out, ref)))


if __name__ == "__main__":
    main()
