"""Sign a shelf manifest (shelf.json) with the release key, or make a new key.

    python scripts/sign_manifest.py --keygen                 # prints a new secret and public key
    ENGRAMM_SIGNING_KEY=<hex> python scripts/sign_manifest.py OUT/shelf.json
    python scripts/sign_manifest.py --verify OUT/shelf.json  # against engramm/web/release_keys.txt

The secret (32 bytes, hex) belongs only in the repository secret ENGRAMM_SIGNING_KEY; the public
key goes into engramm/web/release_keys.txt, which the app reads.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engramm.web.ed25519 import public_key  # noqa: E402
from engramm.web.shelf import ShelfManifest, release_keys  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", nargs="?", type=Path)
    ap.add_argument("--keygen", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args(argv)
    if a.keygen:
        seed = secrets.token_bytes(32)
        print(json.dumps({"secret_ENGRAMM_SIGNING_KEY": seed.hex(), "public_key": public_key(seed).hex()}, indent=1))
        return 0
    if a.manifest is None:
        ap.error("a manifest is needed")
    m = ShelfManifest.load(a.manifest)
    if a.verify:
        keys = release_keys()
        ok = bool(keys) and m.verify(keys)
        print(json.dumps({"signed": bool(m.signature), "valid": ok, "keys": len(keys)}))
        return 0 if ok else 1
    key = os.environ.get("ENGRAMM_SIGNING_KEY", "").strip()
    if len(key) != 64:
        print("ENGRAMM_SIGNING_KEY is not set (64 hex characters)", file=sys.stderr)
        return 2
    m.sign(bytes.fromhex(key))
    a.manifest.write_text(json.dumps(m.to_dict(), indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"signed": True, "public_key": public_key(bytes.fromhex(key)).hex()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
