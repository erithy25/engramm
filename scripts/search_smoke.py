"""Live check of the web search (informational in CI: it depends on the search engines, which treat
data-centre addresses with suspicion — bot checks, unrelated results).

    python scripts/search_smoke.py [ENGRAMM_CORE]

Asks a few questions through the app's own network core (engramm-core egress, or urllib without
it) with the engine chain of the app, reads the result pages and prints per question: which engine
answered, what the others did, the first results and the best sentence. Exit code 0 when at least
two of the three questions were answered with matching results, so a change in a result page's
markup (the parsers in engramm/web/search.py) shows up here first.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engramm.web.egress import Egress, PythonBackend, RustBackend  # noqa: E402
from engramm.web.search import WebSearch  # noqa: E402

QUESTIONS = [("What is the capital of Australia?", "en", "canberra"),
             ("Who is the CEO of Siemens?", "en", "busch"),
             ("Wie hoch ist die Zugspitze?", "de", "2962")]


def main() -> int:
    core = sys.argv[1] if len(sys.argv) > 1 else None
    e = Egress(backend=RustBackend(core) if core else PythonBackend(), core=core)
    ws = WebSearch(e)
    good = 0
    for q, lang, want in QUESTIONS:
        t0 = time.time()
        found = ws.search(q, lang, explicit=True)
        pages = ws.read(found.results, n=3, explicit=True) if found.ok else []
        best = ws.best(q, found.results, pages)
        hay = " ".join([r.title + " " + r.snippet for r in found.results] + [b[1] for b in best]).lower()
        hay = hay.replace(".", "").replace(",", "").replace(" ", "")
        ok = found.ok and want in hay
        good += ok
        print(f"{'ok ' if ok else 'BAD'} {q!r} → {found.engine} in {time.time() - t0:.1f} s; tried: {found.tried}")
        for r in found.results[:3]:
            print(f"      {r.site:28} {r.title[:70]}")
        if best:
            print(f"      best ({best[0][2]['host']}): {best[0][1][:160]}")
    e.close()
    print(f"{good}/{len(QUESTIONS)} answered")
    return 0 if good >= 2 else 1


if __name__ == "__main__":
    sys.exit(main())
