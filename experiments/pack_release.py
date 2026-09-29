"""Prepare a knowledge pack for a GitHub release and the app's download catalog.

    python -u -m experiments.pack_release --pack /dev/shm/engramm/packs/lite \
        --repo erithy25/engramm --tag pack-lite-3.0.0 --out /dev/shm/engramm/release/lite

* checks every file of the pack against its manifest (size and SHA-256);
* writes the release assets as flat files (GitHub release assets have no folders: ``nlp/pos.json``
  becomes ``nlp__pos.json``, as the app expects, see runtime/core/src/fetch.rs), hard-linked
  where possible, plus ``manifest.json``;
* refuses files of 2 GiB or more (the GitHub release limit per asset);
* adds or replaces the pack's entry in runtime/app/src-tauri/resources/catalog.json with the
  download address and the manifest's SHA-256, which pins exactly this pack.

Uploading the assets (``gh release create TAG DIR/*``) is a separate, deliberate step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "runtime" / "app" / "src-tauri" / "resources" / "catalog.json"
LIMIT = 2 * 1024 ** 3
TITLES = {"lite": "Lite", "standard": "Standard"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", type=Path, required=True)
    ap.add_argument("--repo", default="erithy25/engramm")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--description", default="")
    ap.add_argument("--catalog", type=Path, default=CATALOG)
    args = ap.parse_args()
    raw = (args.pack / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    tag = args.tag or f"pack-{manifest['pack']}-{manifest['version']}"
    for rel, entry in manifest["files"].items():
        p = args.pack / rel
        if not p.is_file() or p.stat().st_size != entry["bytes"] or sha256(p) != entry["sha256"]:
            raise SystemExit(f"{rel} does not match the manifest")
        if entry["bytes"] >= LIMIT:
            raise SystemExit(f"{rel} is {entry['bytes']:,} bytes; GitHub release assets must stay below 2 GiB")
    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    for rel in manifest["files"]:
        dst = args.out / rel.replace("/", "__")
        try:
            os.link(args.pack / rel, dst)
        except OSError:
            shutil.copy2(args.pack / rel, dst)
    (args.out / "manifest.json").write_bytes(raw)
    entry = {"name": manifest["pack"], "title": TITLES.get(manifest["pack"], manifest["pack"].title()),
             "version": manifest["version"], "bytes": manifest["bytes"],
             "base_url": f"https://github.com/{args.repo}/releases/download/{tag}/",
             "manifest_sha256": hashlib.sha256(raw).hexdigest(),
             "description": args.description or manifest.get("info", {}).get("reading", "")}
    cat = json.loads(args.catalog.read_text()) if args.catalog.exists() else {"packs": []}
    cat["packs"] = [p for p in cat.get("packs", []) if p["name"] != entry["name"]] + [entry]
    cat["packs"].sort(key=lambda p: p["bytes"])
    args.catalog.write_text(json.dumps(cat, indent=2) + "\n")
    print(json.dumps({"assets": len(manifest["files"]) + 1, "tag": tag, "entry": entry}, indent=1))


if __name__ == "__main__":
    main()
