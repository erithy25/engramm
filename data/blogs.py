"""Blog Authorship Corpus loader for M3 (1,000-author sequential learning).

The corpus (Schler et al., 2006) holds 19,320 bloggers, one XML-like file per
author with ``<post>`` elements. M3 treats each author as a class: learn an
author from ten posts, recognise held-out posts, and keep doing so while
hundreds more authors are added.

Protocol choices the historical record does not preserve are fixed here and
listed in ``docs/DEVIATIONS.md`` (GAP-10):

* A post qualifies when its whitespace-normalised text is at least
  :data:`MIN_POST_CHARS` characters long — shorter posts ("urlLink" stubs,
  one-liners) carry no stylometric signal.
* An author is eligible with at least ``shots + test + validation``
  qualifying posts.
* Authors are drawn from the eligible ones with the run's seeded generator;
  each author's posts are shuffled with the same generator and split into
  training, test and validation posts, which are therefore disjoint.

The files are not well-formed XML (stray ampersands, mixed encodings), so
posts are extracted with a regular expression and decoded as Latin-1, which
maps every byte and cannot fail.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from data.loaders import CACHE_DIR, Dataset, download_and_verify

BLOGS_SOURCE = {
    "url": "https://u.cs.biu.ac.il/~koppel/blogs/blogs.zip",
    "filename": "blogs.zip",
    # Verified by downloading and hashing (2026-09-23). An identical copy is
    # mirrored at huggingface.co/datasets/barilan/blog_authorship_corpus.
    "sha256": "1dfa6996663515a4baf8c1b71713ce8fe9a314b13778701447e4663bbc64c983",
}

MIN_POST_CHARS = 200

_POST = re.compile(rb"<post>(.*?)</post>", re.S)
_SPACE = re.compile(r"\s+")


def _posts(raw: bytes) -> list[str]:
    """Whitespace-normalised posts of one author file, in file order."""
    return [_SPACE.sub(" ", body.decode("latin-1")).strip() for body in _POST.findall(raw)]


def _author_id(member: str) -> str:
    return Path(member).name.split(".")[0]


def eligibility_index(archive: Path, min_chars: int = MIN_POST_CHARS) -> dict[str, Any]:
    """Qualifying-post count per author, computed once and cached as JSON.

    Keyed by the archive digest and ``min_chars``, so a changed threshold or
    archive can never reuse a stale index.
    """
    key = f"{BLOGS_SOURCE['sha256'][:16]}_min{min_chars}"
    path = CACHE_DIR / f"blogs_index_{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    members: dict[str, str] = {}
    with zipfile.ZipFile(archive) as zf:
        for member in sorted(zf.namelist()):
            if not member.endswith(".xml"):
                continue
            author = _author_id(member)
            posts = _posts(zf.read(member))
            counts[author] = sum(1 for p in posts if len(p) >= min_chars)
            members[author] = member
    index = {"min_chars": min_chars, "counts": counts, "members": members}
    path.write_text(json.dumps(index, sort_keys=True), encoding="utf-8")
    return index


def load_blogs(n_authors: int, shots: int, test_per_author: int,
               rng: np.random.Generator, validation_per_author: int = 0,
               cache_dir: Path | str | None = None,
               allow_download: bool = True) -> Dataset:
    """Draw ``n_authors`` authors and split their posts into train/test/validation.

    Returns a :class:`Dataset` whose ``x_test`` holds the test posts; the
    validation posts (if requested) are in ``metadata["x_validation"]`` /
    ``metadata["y_validation"]`` and are never used for results. Labels are
    author ids, sorted.
    """
    if min(n_authors, shots, test_per_author) <= 0:
        raise ValueError("n_authors, shots and test_per_author must be positive")
    archive = download_and_verify(**BLOGS_SOURCE, cache_dir=cache_dir,
                                  allow_download=allow_download)
    index = eligibility_index(Path(archive))
    need = shots + test_per_author + validation_per_author
    eligible = sorted(a for a, c in index["counts"].items() if c >= need)
    if len(eligible) < n_authors:
        raise ValueError(f"only {len(eligible)} authors have {need} qualifying posts")
    chosen = sorted(rng.choice(np.array(eligible), size=n_authors, replace=False).tolist())

    x_train, y_train, x_test, y_test, x_val, y_val = [], [], [], [], [], []
    with zipfile.ZipFile(archive) as zf:
        for class_index, author in enumerate(chosen):
            posts = [p for p in _posts(zf.read(index["members"][author]))
                     if len(p) >= MIN_POST_CHARS]
            order = rng.permutation(len(posts))[:need]
            picked = [posts[i] for i in order]
            x_train += picked[:shots]
            y_train += [class_index] * shots
            x_test += picked[shots:shots + test_per_author]
            y_test += [class_index] * test_per_author
            x_val += picked[shots + test_per_author:]
            y_val += [class_index] * validation_per_author

    return Dataset(
        name="blogs",
        x_train=tuple(x_train), y_train=np.array(y_train, dtype=np.int64),
        x_test=tuple(x_test), y_test=np.array(y_test, dtype=np.int64),
        labels=tuple(chosen),
        metadata={"source": BLOGS_SOURCE["url"], "sha256": BLOGS_SOURCE["sha256"],
                  "official_split": False, "shots": shots,
                  "test_per_author": test_per_author,
                  "min_post_chars": MIN_POST_CHARS,
                  "eligible_authors": len(eligible),
                  "x_validation": tuple(x_val),
                  "y_validation": np.array(y_val, dtype=np.int64)},
    )
