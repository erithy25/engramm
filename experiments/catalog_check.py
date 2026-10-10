"""Checks the app's pack catalog before installers carry it: every pack can really be downloaded.

    python experiments/catalog_check.py CATALOG [--skip-url-prefix URL ...] [--same NAME=MANIFEST ...]

For each entry it fetches ``manifest.json`` from the entry's ``base_url`` and checks its SHA-256
against ``manifest_sha256`` and its pack name, version and size against the entry. ``--same``
also requires an entry to describe exactly the pack whose manifest is given (the pack a release
reuses or uploads). ``--skip-url-prefix`` leaves out entries whose files this very release is
about to upload (they cannot be fetched yet); with ``--same`` they are still compared.

Built after 3.2.0-beta.6: every installer since 3.1.0-beta.1 pointed the standard pack at
``pack-standard-3.1.0-beta.1`` while the release was ``pack-standard-v3.1.0-beta.1`` (404).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def fetch(url: str, attempts: int = 3) -> bytes:
    for i in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "engramm-catalog-check"}),
                                        timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or i == attempts - 1:
                raise
        except OSError:
            if i == attempts - 1:
                raise
        time.sleep(2 * (i + 1))
    raise RuntimeError("unreachable")


def check(catalog: dict, skip: list[str], same: dict[str, bytes]) -> list[str]:
    problems = []
    packs = catalog.get("packs") or []
    if not packs:
        problems.append("the catalog lists no pack")
    for e in packs:
        name = e.get("name", "?")
        for key in ("name", "title", "version", "bytes", "base_url", "manifest_sha256"):
            if not e.get(key):
                problems.append(f"{name}: no {key}")
        if name in same:
            raw = same[name]
            if hashlib.sha256(raw).hexdigest() != e.get("manifest_sha256"):
                problems.append(f"{name}: the catalog pins another pack than the one in this release")
        base = str(e.get("base_url", ""))
        if not base.endswith("/"):
            problems.append(f"{name}: base_url must end with '/': {base}")
        if any(base.startswith(p) for p in skip):
            print(f"{name}: {base} is uploaded by this release, not fetched")
            continue
        try:
            raw = fetch(base + "manifest.json")
        except Exception as ex:                    # noqa: BLE001 - every failure is a finding here
            problems.append(f"{name}: {base}manifest.json cannot be downloaded ({ex})")
            continue
        if hashlib.sha256(raw).hexdigest() != e.get("manifest_sha256"):
            problems.append(f"{name}: {base}manifest.json does not match manifest_sha256")
            continue
        m = json.loads(raw)
        for key, mkey in (("name", "pack"), ("version", "version"), ("bytes", "bytes")):
            if m.get(mkey) != e.get(key):
                problems.append(f"{name}: catalog {key}={e.get(key)!r}, manifest {mkey}={m.get(mkey)!r}")
        print(f"{name} {e.get('version')}: {base}manifest.json ok ({len(m.get('files', {}))} files, {e.get('bytes', 0) / 1e9:.2f} GB)")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("catalog", type=Path)
    ap.add_argument("--skip-url-prefix", action="append", default=[])
    ap.add_argument("--same", action="append", default=[], metavar="NAME=MANIFEST")
    args = ap.parse_args()
    same = {}
    for s in args.same:
        name, _, path = s.partition("=")
        same[name] = Path(path).read_bytes()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    problems = check(catalog, args.skip_url_prefix, same)
    for p in problems:
        print("PROBLEM", p)
    print("catalog ok" if not problems else f"{len(problems)} problem(s): the installers would offer packs that cannot be installed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
