"""Files in a GitHub release (a private draft): list, upload (split above 1.9 GB), download (re-assembled), verify.

    python -m experiments.gh_release find-or-create --name "ENGRAMM Sela-2 Trainingsdaten (privat)"
    python -m experiments.gh_release upload --release ID FILE [FILE …] [--prefix P] [--replace]
    python -m experiments.gh_release download --release ID --dest DIR [--match REGEX] [--jobs 4]
    python -m experiments.gh_release list --release ID

The token comes from $GH_TOKEN (a fine-grained token with Contents read/write, or the workflow's GITHUB_TOKEN).
GitHub refuses assets of 2 GiB or more, so a larger file is uploaded as NAME.part000, NAME.part001, … plus
NAME.parts.json (sizes and SHA-256 of the parts and of the whole); ``download`` puts the parts back together and
checks every digest. Every upload is verified by the size and SHA-256 digest GitHub reports (an existing asset of
the same name is kept only when its digest matches); an interrupted upload is retried and the broken asset deleted.
Draft releases are visible only to people with write access.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"
REPO = os.environ.get("GH_REPO", "erithy25/engramm")
PART = 1_900_000_000                                   # bytes per part (GitHub limit: < 2 GiB per asset)


def _token() -> str:
    t = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not t:
        raise SystemExit("GH_TOKEN is not set")
    return t


def _req(method: str, url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 120,
         tries: int = 6):
    h = {"Authorization": f"Bearer {_token()}", "Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "engramm-sela2"}
    h.update(headers or {})
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, method=method, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                return json.loads(body) if body and "json" in (r.headers.get("Content-Type") or "") else body
        except urllib.error.HTTPError as e:
            msg = e.read()[:500]
            if e.code in (400, 401, 404, 410, 422):    # will not change on a retry
                raise SystemExit(f"GitHub {method} {url}: HTTP {e.code} {msg!r}")
            last = f"HTTP {e.code} {msg!r}"            # 403 (rate limit), 429, 5xx: retried
        except Exception as e:                         # network errors: wait and retry
            last = f"{type(e).__name__}: {e}"
        time.sleep(min(120, 5 * 2 ** attempt))
    raise SystemExit(f"GitHub {method} {url} failed: {last}")


def sha256_file(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def assets(release: int) -> list[dict]:
    out, page = [], 1
    while True:
        a = _req("GET", f"{API}/repos/{REPO}/releases/{release}/assets?per_page=100&page={page}")
        out += a
        if len(a) < 100:
            return out
        page += 1


def find_or_create(name: str, body: str = "") -> int:
    page = 1
    while True:
        rels = _req("GET", f"{API}/repos/{REPO}/releases?per_page=100&page={page}")
        for r in rels:
            if r.get("name") == name:
                if not r.get("draft"):
                    raise SystemExit(f"release {name!r} exists but is not a draft: refusing to use a public release")
                return int(r["id"])
        if len(rels) < 100:
            break
        page += 1
    tag = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
    r = _req("POST", f"{API}/repos/{REPO}/releases", data=json.dumps(
        {"tag_name": tag, "name": name, "draft": True, "body": body}).encode(), headers={"Content-Type": "application/json"})
    return int(r["id"])


def _range_sha256(path: Path, offset: int, size: int) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        f.seek(offset)
        left = size
        while left:
            b = f.read(min(1 << 22, left))
            if not b:
                raise SystemExit(f"{path}: ends {left} bytes early (file changed while reading?)")
            h.update(b)
            left -= len(b)
    return h.hexdigest()


def _upload_bytes(release: int, name: str, path: Path, offset: int = 0, size: int | None = None,
                  tries: int = 4) -> dict:
    """Upload bytes [offset, offset+size) of ``path`` as asset ``name``. An asset of that name counts as done only
    when GitHub's SHA-256 digest equals the local one (same size is not enough: a rebuilt file can have it)."""
    size = path.stat().st_size - offset if size is None else size
    want = "sha256:" + _range_sha256(path, offset, size)
    for attempt in range(tries):
        for a in assets(release):                      # a leftover of an interrupted attempt blocks the name
            if a["name"] == name:
                if a.get("state") == "uploaded" and a["size"] == size and a.get("digest") == want:
                    return a
                _req("DELETE", f"{API}/repos/{REPO}/releases/assets/{a['id']}")
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read(size)
        if len(data) != size:
            raise SystemExit(f"{path}: read {len(data)} of {size} bytes (file changed while uploading?)")
        try:
            r = _req("POST", f"{UPLOADS}/repos/{REPO}/releases/{release}/assets?name={name}", data=data,
                     headers={"Content-Type": "application/octet-stream"}, timeout=300, tries=1)
            if isinstance(r, dict) and r.get("size") == size and r.get("digest", want) == want:
                return r
        except SystemExit as e:
            print(f"upload {name} attempt {attempt + 1}: {e}", file=sys.stderr, flush=True)
        time.sleep(30 * (attempt + 1))
    raise SystemExit(f"upload of {name} failed")


def upload(release: int, path: Path, name: str | None = None) -> list[dict]:
    """Uploads ``path`` (split into parts above PART bytes); returns the asset records."""
    path = Path(path)
    name = name or path.name
    size = path.stat().st_size
    if size < PART:
        return [_upload_bytes(release, name, path)]
    parts, recs = [], []
    for k, off in enumerate(range(0, size, PART)):
        n = min(PART, size - off)
        pname = f"{name}.part{k:03d}"
        recs.append(_upload_bytes(release, pname, path, offset=off, size=n))
        parts.append({"name": pname, "size": n, "sha256": recs[-1].get("digest", "").removeprefix("sha256:")
                      or _range_sha256(path, off, n)})
    man = {"name": name, "size": size, "sha256": sha256_file(path), "parts": parts}
    mpath = path.with_name(path.name + ".parts.json")
    mpath.write_text(json.dumps(man, indent=1) + "\n")
    recs.append(_upload_bytes(release, f"{name}.parts.json", mpath))
    mpath.unlink()
    return recs


def _download_asset(asset: dict, dest: Path, tries: int = 6) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == asset["size"]:
        return dest
    url = f"{API}/repos/{REPO}/releases/assets/{asset['id']}"
    for attempt in range(tries):
        tmp = dest.with_name(dest.name + ".tmp")
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_token()}",
                                                       "Accept": "application/octet-stream",
                                                       "User-Agent": "engramm-sela2"})
            with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
                while b := r.read(1 << 22):
                    f.write(b)
            if tmp.stat().st_size == asset["size"]:
                os.replace(tmp, dest)
                return dest
        except Exception as e:
            print(f"download {asset['name']} attempt {attempt + 1}: {e}", file=sys.stderr, flush=True)
        time.sleep(min(120, 5 * 2 ** attempt))
    raise SystemExit(f"download of {asset['name']} failed")


def download(release: int, dest: Path, match: str = "", jobs: int = 4) -> list[Path]:
    """Every asset (matching ``match``) into ``dest``; split files re-assembled and checked against their manifest."""
    dest = Path(dest)
    al = [a for a in assets(release) if a.get("state") == "uploaded" and (not match or re.search(match, a["name"]))]
    with cf.ThreadPoolExecutor(jobs) as ex:
        got = list(ex.map(lambda a: _download_asset(a, dest / a["name"]), al))
    out = [p for p in got if not re.search(r"\.part\d{3}$|\.parts\.json$", p.name)]
    for man_path in [p for p in got if p.name.endswith(".parts.json")]:
        man = json.loads(man_path.read_text())
        whole = dest / man["name"]
        if not (whole.exists() and whole.stat().st_size == man["size"] and sha256_file(whole) == man["sha256"]):
            with open(whole.with_name(whole.name + ".tmp"), "wb") as f:
                for p in man["parts"]:
                    pp = dest / p["name"]
                    if sha256_file(pp) != p["sha256"]:
                        raise SystemExit(f"{p['name']}: SHA-256 mismatch")
                    with open(pp, "rb") as g:
                        while b := g.read(1 << 22):
                            f.write(b)
            os.replace(whole.with_name(whole.name + ".tmp"), whole)
            if sha256_file(whole) != man["sha256"]:
                raise SystemExit(f"{man['name']}: SHA-256 of the re-assembled file differs")
        for p in man["parts"]:
            (dest / p["name"]).unlink(missing_ok=True)
        man_path.unlink()
        out.append(whole)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find-or-create")
    p.add_argument("--name", required=True)
    p.add_argument("--body", default="")
    p = sub.add_parser("upload")
    p.add_argument("--release", type=int, required=True)
    p.add_argument("--prefix", default="")
    p.add_argument("files", nargs="+")
    p = sub.add_parser("download")
    p.add_argument("--release", type=int, required=True)
    p.add_argument("--dest", required=True)
    p.add_argument("--match", default="")
    p.add_argument("--jobs", type=int, default=4)
    p = sub.add_parser("list")
    p.add_argument("--release", type=int, required=True)
    a = ap.parse_args()
    if a.cmd == "find-or-create":
        print(find_or_create(a.name, a.body))
    elif a.cmd == "upload":
        for f in a.files:
            for r in upload(a.release, Path(f), a.prefix + Path(f).name):
                print(f"uploaded {r['name']} {r['size']}", flush=True)
    elif a.cmd == "download":
        for p in download(a.release, Path(a.dest), a.match, a.jobs):
            print(p)
    elif a.cmd == "list":
        for x in assets(a.release):
            print(x["id"], x["size"], x["state"], x["name"])


if __name__ == "__main__":
    main()
