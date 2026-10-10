"""Does DuckDuckGo answer the app's network core (engramm-core, Rust) the way it answers Python's
urllib, from the same address? Informational in CI.

    python scripts/ddg_probe.py [ENGRAMM_CORE]

Posts the same search form to DuckDuckGo's HTML and lite pages, alternating between the two
clients (python, rust, python, rust, …) so that a rate limit hits both alike, and prints status
and number of results per try. A client that DuckDuckGo singles out (its TLS handshake, its
headers) shows up as 202 for one and 200 for the other.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engramm.web.egress import Egress, PythonBackend, Request, RustBackend  # noqa: E402
from engramm.web.search import ddg_form, parse_ddg, parse_ddg_lite  # noqa: E402

QUERIES = ["capital of australia", "siemens ceo", "zugspitze height"]


def probe(egress: Egress, lite: bool, query: str) -> str:
    url, form = ddg_form(query, "en", lite=lite)
    origin = "/".join(url.split("/", 3)[:3])
    req = Request("search", url, "probe", ("duckduckgo.com",), explicit=True, form=form,
                  headers=(("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
                           ("Accept-Language", "en-US,en;q=0.9"), ("Referer", origin + "/"), ("Origin", origin)))
    res = egress.fetch(req)
    body = res.body.decode("utf-8", "replace") if res.body else ""
    n = len((parse_ddg_lite if lite else parse_ddg)(body)) if res.status == 200 else 0
    return f"{res.status} ({n} results)" if res.status else f"error: {res.error[:60]}"


def main() -> int:
    core = sys.argv[1] if len(sys.argv) > 1 else None
    clients = {"python": Egress(backend=PythonBackend())}
    if core:
        clients["rust"] = Egress(backend=RustBackend(core), core=core)
    for query in QUERIES:
        for lite in (False, True):
            row = []
            for name, e in clients.items():
                row.append(f"{name}: {probe(e, lite, query)}")
                time.sleep(1.0)
            print(f"{'lite' if lite else 'html'} {query!r:24} " + " | ".join(row))
    for e in clients.values():
        e.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
