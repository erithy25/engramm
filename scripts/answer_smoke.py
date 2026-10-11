"""Live check of the answers from Wikidata and Wikipedia (informational in CI: Wikimedia limits each
address, and a shared one may be over the limit).

    python scripts/answer_smoke.py [ENGRAMM_CORE]

Asks real questions in English and German through the app's own network core (engramm-core
egress, or urllib without it) the way the web search does (engramm/web/wiki.py) and prints the
answer sentence and its source per question. Exit code 0 when at least 12 of the 16 answers hold
what they should, so a change of Wikidata's or Wikipedia's API shows up here first.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engramm.web.egress import Egress, PythonBackend, RustBackend  # noqa: E402
from engramm.web.wiki import WikiKnowledge  # noqa: E402

QUESTIONS = [("When was real madrid founded?", "en", "1902"),
             ("Who is currently the president of the usa?", "en", "Trump"),
             ("Wer ist der aktuelle Bundeskanzler?", "de", "Merz"),
             ("Who is the CEO of Siemens?", "en", "Busch"),
             ("What is the capital of Australia?", "en", "Canberra"),
             ("Wie hoch ist die Zugspitze?", "de", "2.962"),
             ("How many people live in Berlin?", "en", "population of"),
             ("Who wrote Faust?", "en", "Goethe"),
             ("Wer ist der Trainer von Bayern München?", "de", "Kompany"),
             ("How long is the Rhine?", "en", "km"),
             ("Where was Albert Einstein born?", "en", "Ulm"),
             ("Who founded Microsoft?", "en", "Gates"),
             ("How old is Donald Trump?", "en", "years old"),
             ("When did the Berlin Wall fall?", "en", "1989"),
             ("Who is Elon Musk?", "en", "Musk"),
             ("Was ist ein Schwarzes Loch?", "de", "Loch")]


def main() -> int:
    core = sys.argv[1] if len(sys.argv) > 1 else None
    e = Egress(backend=RustBackend(core) if core else PythonBackend(), core=core)
    wk = WikiKnowledge(e)
    good = 0
    for q, lang, want in QUESTIONS:
        t0 = time.time()
        fact = wk.answer(q, lang, explicit=True)
        ok = fact is not None and want.lower() in fact.text.lower()
        good += ok
        where = f"{fact.url}" if fact else "-"
        print(f"{'ok ' if ok else 'BAD'} {q!r} ({time.time() - t0:.1f} s)\n      {fact.text if fact else None}\n      {where}")
        time.sleep(0.4)                                  # well inside Wikimedia's 200 requests a minute
    e.close()
    print(f"{good}/{len(QUESTIONS)} answered")
    return 0 if good >= 12 else 1


if __name__ == "__main__":
    sys.exit(main())
