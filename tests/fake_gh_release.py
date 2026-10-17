"""Stand-in for experiments/gh_release.py in offline tests of experiments/sela2_run.sh (SELA2_GH_RELEASE): a
"release" is a folder ($FAKE_RELEASE_DIR/<id>/); upload copies the file there (split above FAKE_PART bytes like
the real one), list prints what is there, find-or-create returns 1. FAKE_FAIL_UPLOADS=n fails the first n uploads."""

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ["FAKE_RELEASE_DIR"])


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find-or-create")
    p.add_argument("--name", required=True)
    p.add_argument("--body", default="")
    p = sub.add_parser("upload")
    p.add_argument("--release", type=int, required=True)
    p.add_argument("files", nargs="+")
    p = sub.add_parser("list")
    p.add_argument("--release", type=int, required=True)
    p = sub.add_parser("download")
    p.add_argument("--release", type=int, required=True)
    p.add_argument("--dest", required=True)
    p.add_argument("--match", default="")
    p.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "find-or-create":
        (ROOT / "1").mkdir(parents=True, exist_ok=True)
        (ROOT / "1" / ".name").write_text(a.name)
        print(1)
    elif a.cmd == "list":
        d = ROOT / str(a.release)
        for f in sorted(d.glob("*")) if d.exists() else []:
            print(0, f.stat().st_size, "uploaded", f.name)
    elif a.cmd == "upload":
        fails = ROOT / ".fails"
        n = int(fails.read_text()) if fails.exists() else int(os.environ.get("FAKE_FAIL_UPLOADS", "0"))
        if n > 0:
            fails.write_text(str(n - 1))
            sys.exit("fake upload failure")
        fails.write_text("0")
        d = ROOT / str(a.release)
        d.mkdir(parents=True, exist_ok=True)
        for f in a.files:
            shutil.copyfile(f, d / Path(f).name)
            print(f"uploaded {Path(f).name} {Path(f).stat().st_size}")
    elif a.cmd == "download":
        sys.exit("fake download is not supported (tests copy their data)")


if __name__ == "__main__":
    main()
