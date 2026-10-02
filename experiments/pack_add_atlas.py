"""Add the Atlas files to a knowledge pack: the shelf's local index and manifest (from a shelf
release made by .github/workflows/shelf.yml, or a local shelf folder), where the shelf lives
(shelf_source.json) and the wayfinder; then rewrite the pack manifest (sizes, SHA-256).

    python experiments/pack_add_atlas.py --pack PACK --shelf-release shelf-20260927 [--variant lite]
        [--wayfinder wayfinder.sqlite] [--version 3.1.0]
    python experiments/pack_add_atlas.py --pack PACK --shelf /dev/shm/engramm/shelf0 --base-url http://127.0.0.1:8765/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engramm.web.shelf import SHELF_HOSTS, ShelfIndex, ShelfManifest  # noqa: E402

UA = "ENGRAMM-build/3.1 (github.com/erithy25/engramm)"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, 8 << 20)


def rewrite_manifest(pack: Path, version: str | None, atlas: dict) -> dict:
    m = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    files = {}
    for p in sorted(pack.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            files[str(p.relative_to(pack))] = {"bytes": p.stat().st_size, "sha256": _sha256(p)}
    m.update({"files": files, "bytes": sum(f["bytes"] for f in files.values()),
              "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    if version:
        m["version"] = version
        m.setdefault("info", {})["version"] = version
    m.setdefault("info", {})["atlas"] = atlas
    m.setdefault("licenses", {})
    if isinstance(m["licenses"], dict):
        m["licenses"]["shelf"] = "Wikipedia text (CC BY-SA 4.0 / GFDL), CirrusSearch dump; index only in the pack"
        m["licenses"]["wayfinder"] = "DBpedia homepages (CC BY-SA 3.0)"
    (pack / "manifest.json").write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    return m


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", type=Path, required=True)
    ap.add_argument("--shelf-release", help="tag of a shelf release (assets shelf.json, shelf_index[_lite].tar)")
    ap.add_argument("--shelf", type=Path, help="a local shelf folder instead (shelf.json, shelf_index/)")
    ap.add_argument("--base-url", help="where the volumes are served (default: the release's download URL)")
    ap.add_argument("--repo", default="erithy25/engramm")
    ap.add_argument("--variant", choices=["lite", "full"], default="lite")
    ap.add_argument("--wayfinder", type=Path)
    ap.add_argument("--version")
    a = ap.parse_args(argv)
    pack = a.pack
    if not (pack / "manifest.json").exists():
        raise SystemExit(f"no pack at {pack}")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if a.shelf_release:
            base = f"https://github.com/{a.repo}/releases/download/{a.shelf_release}/"
            name = "shelf_index_lite.tar" if a.variant == "lite" else "shelf_index.tar"
            _download(base + "shelf.json", tmp / "shelf.json")
            _download(base + name, tmp / name)
            with tarfile.open(tmp / name) as t:
                t.extractall(tmp, filter="data")
            src = tmp
            date = a.shelf_release.split("-", 1)[-1]
        elif a.shelf:
            src, base, date = a.shelf, a.base_url, ""
            if not base:
                raise SystemExit("--base-url is needed with a local shelf")
        else:
            raise SystemExit("--shelf-release or --shelf")
        if (pack / "shelf_index").exists():
            shutil.rmtree(pack / "shelf_index")
        shutil.copytree(src / "shelf_index", pack / "shelf_index")
        shutil.copy2(src / "shelf.json", pack / "shelf.json")
    man = ShelfManifest.load(pack / "shelf.json")
    ix = ShelfIndex(pack / "shelf_index")
    if man.buckets <= int(max(ix.bucket)) if len(ix) else False:
        raise SystemExit("the index points past the manifest's buckets")
    source = {"base_url": a.base_url or base, "hosts": list(SHELF_HOSTS), "date": date,
              "release": a.shelf_release or "", "variant": a.variant}
    if a.base_url and a.base_url.startswith("http://127.0.0.1"):
        source.update({"hosts": ["127.0.0.1"], "allow_loopback": True})
    (pack / "shelf_source.json").write_text(json.dumps(source, indent=1) + "\n", encoding="utf-8")
    if a.wayfinder and a.wayfinder.exists():
        shutil.copy2(a.wayfinder, pack / "wayfinder.sqlite")
    atlas = {"shelf_docs": len(ix), "shelf_buckets": man.buckets, "shelf_date": date, "variant": a.variant,
             "signed": bool(man.signature), "wayfinder": (pack / "wayfinder.sqlite").exists()}
    m = rewrite_manifest(pack, a.version, atlas)
    size = sum(p.stat().st_size for p in (pack / "shelf_index").iterdir())
    print(json.dumps({"pack": m.get("pack"), "version": m.get("version"), "MB": round(m["bytes"] / 1e6, 1),
                      "shelf_index_MB": round(size / 1e6, 1), **atlas}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
