"""Live check of the messenger's Tor path: engramm-core (built with the `tor` feature) boots the
embedded Tor client and fetches https://check.torproject.org/api/ip through it, under the same
egress rules the app uses. Prints the bootstrap and fetch times; exit 0 only when the Tor
project confirms the request came through Tor.

    python scripts/tor_smoke.py runtime/core/target/release/engramm-core
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engramm.web.egress import Egress, NetworkLog, Request, RustBackend  # noqa: E402

URL = "https://check.torproject.org/api/ip"


def main() -> int:
    core = sys.argv[1]
    with tempfile.TemporaryDirectory() as tmp:
        eg = Egress(settings_path=Path(tmp) / "network.json", log=NetworkLog(Path(tmp) / "network.log"))
        eg.core = core
        eg.backend = RustBackend(core)
        if not eg.backend.op("status").get("tor"):
            print(json.dumps({"ok": False, "error": "this engramm-core has no Tor"}))
            return 1
        eg.set_channel("messenger", enabled=True, tor=True)
        tor = RustBackend(core, tor_dir=Path(tmp) / "tor")
        eg.tor_backend = tor
        t0 = time.time()
        boot = tor.op("tor_start")
        t_boot = time.time() - t0
        if not boot.get("ok"):
            print(json.dumps({"ok": False, "stage": "bootstrap", "seconds": round(t_boot, 1), "error": boot.get("error")}))
            return 1
        times, last = [], None
        for _ in range(3):
            t1 = time.time()
            res = eg.fetch(Request("messenger", URL, "tor check", ("check.torproject.org",), tor=True))
            times.append(round(time.time() - t1, 2))
            last = res
        ok = bool(last and last.ok and json.loads(last.body.decode() or "{}").get("IsTor") is True)
        print(json.dumps({"ok": ok, "via": last.via if last else None, "bootstrap_seconds": round(t_boot, 1),
                          "fetch_seconds": times, "status": last.status if last else None,
                          "error": None if ok else (last.error if last else "no response")}))
        tor.close()
        eg.backend.close()
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
