"""The shelf (Atlas channel K1, docs/SPEC_ATLAS.md): open texts in fixed-size buckets on static
hosts, a local index that knows which bucket holds which article, and a client that fetches the
bucket it needs together with decoy buckets — so the host learns bucket numbers, never a question.

Bucket layout (``bucket_bytes`` each, default 1 MiB):

    b"EGB1" | u32 little-endian length n | n bytes of LZMA (xz) data | zero padding

The LZMA data is UTF-8 JSON lines ``{"t": title, "s": source, "x": text}``. Bucket ``b`` lives in
volume ``b // per_volume`` at offset ``(b % per_volume) * bucket_bytes``.

Local index (``shelf_index/`` in a pack, all memory-mapped): ``titles.bin`` + ``title_off.npy``
(the titles), ``bucket.npy`` (uint32 per title), ``name_hash.npy`` / ``name_doc.npy`` (64-bit hashes
of titles and redirect name forms → title id), ``term_hash.npy`` (sorted hashes of the key terms),
``ptr.npy`` / ``post.npy`` (term → title ids) and ``idf.npy``. Search = idf over key terms + a boost
for a title or name form found in the question; no neural network.
"""

from __future__ import annotations

import hashlib
import json
import lzma
import math
import os
import re
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MAGIC = b"EGB1"
SHELF_HOSTS = ("github.com", "githubusercontent.com")
_STOP = frozenset("""a an the of in on at to for from by with and or but is are was were be been being it its this that
these those as which who whom whose what when where why how not no nor so than then there their they them he she his her
i you we our your my me us do does did done has have had having will would shall should can could may might must also
into about over after before between during under above out up down off only very more most such some any each other
all both few many much own same just than too s t don now one two three first new used known""".split())
_TOKEN = re.compile(r"[^\W_][\w'\-]*")


def tokens(text: str) -> list[str]:
    return [t.strip("'-") for t in _TOKEN.findall(text.lower()) if len(t) > 1 and t not in _STOP]


def term_hash(t: str) -> int:
    return int.from_bytes(hashlib.blake2b(t.encode("utf-8"), digest_size=8).digest(), "little")


def name_key(s: str) -> str:
    """A title or name form for lookups: no "(…)" part, lower case, single spaces."""
    s = re.sub(r"\s*\([^)]*\)$", "", s.strip())
    return " ".join(s.lower().replace("’", "'").split())


def bucket_of_title(title: str, n: int) -> int:
    return int.from_bytes(hashlib.shake_256(title.encode("utf-8")).digest(8), "little") % n


# ---------------------------------------------------------------------------
# buckets
# ---------------------------------------------------------------------------

def pack_bucket(docs: list[dict], bucket_bytes: int, preset: int = 9) -> bytes | None:
    """The padded bucket for these documents, or None if they do not fit."""
    raw = "".join(json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n" for d in docs).encode("utf-8")
    comp = lzma.compress(raw, preset=preset)
    if len(comp) + 8 > bucket_bytes:
        return None
    return MAGIC + struct.pack("<I", len(comp)) + comp + b"\0" * (bucket_bytes - 8 - len(comp))


def unpack_bucket(data: bytes) -> list[dict]:
    if data[:4] != MAGIC:
        raise ValueError("not a shelf bucket")
    n = struct.unpack("<I", data[4:8])[0]
    if n + 8 > len(data):
        raise ValueError("truncated bucket")
    raw = lzma.decompress(data[8:8 + n])
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


@dataclass
class ShelfManifest:
    bucket_bytes: int
    per_volume: int
    buckets: int
    volumes: list[dict]                       # [{"name", "bytes", "sha256"}]
    bucket_sha256: list[str]
    version: int = 1
    built: str = ""
    licenses: list[str] = field(default_factory=list)
    signature: str | None = None
    extra: dict = field(default_factory=dict)  # other fields of the file (kept, and covered by the signature)

    _KNOWN = ("version", "built", "bucket_bytes", "per_volume", "buckets", "volumes", "bucket_sha256", "licenses",
              "signature")

    @classmethod
    def load(cls, path: Path) -> ShelfManifest:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**{k: d[k] for k in ("bucket_bytes", "per_volume", "buckets", "volumes", "bucket_sha256")},
                   version=d.get("version", 1), built=d.get("built", ""), licenses=d.get("licenses", []),
                   signature=d.get("signature"), extra={k: v for k, v in d.items() if k not in cls._KNOWN})

    def to_dict(self) -> dict:
        d = {**self.extra, "version": self.version, "built": self.built, "bucket_bytes": self.bucket_bytes,
             "per_volume": self.per_volume, "buckets": self.buckets, "volumes": self.volumes,
             "bucket_sha256": self.bucket_sha256, "licenses": self.licenses}
        if self.signature:
            d["signature"] = self.signature
        return d

    def canonical(self) -> bytes:
        """The bytes a signature covers: the manifest without its signature, sorted keys, no spaces."""
        d = self.to_dict()
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def verify(self, public_keys: list[bytes]) -> bool:
        """Is the manifest signed (Ed25519) by one of these release keys?"""
        if not self.signature:
            return False
        from engramm.web.ed25519 import verify
        try:
            sig = bytes.fromhex(self.signature)
        except ValueError:
            return False
        return any(verify(k, self.canonical(), sig) for k in public_keys)

    def sign(self, seed: bytes) -> None:
        from engramm.web.ed25519 import sign
        self.signature = None
        self.signature = sign(seed, self.canonical()).hex()

    def locate(self, b: int) -> tuple[str, int]:
        """(volume file, byte offset) of bucket b. Volumes may say which buckets they hold
        ("first", "buckets": a merged shelf of several builds); otherwise every volume holds
        ``per_volume`` buckets."""
        if not 0 <= b < self.buckets:
            raise ValueError(f"bucket {b} out of range")
        if self.volumes and "first" in self.volumes[0]:
            lo, hi = 0, len(self.volumes) - 1
            while lo < hi:                               # the last volume whose first bucket is ≤ b
                mid = (lo + hi + 1) // 2
                if self.volumes[mid]["first"] <= b:
                    lo = mid
                else:
                    hi = mid - 1
            v = self.volumes[lo]
            if not v["first"] <= b < v["first"] + v["buckets"]:
                raise ValueError(f"bucket {b} is in no volume")
            return v["name"], (b - v["first"]) * self.bucket_bytes
        return self.volumes[b // self.per_volume]["name"], (b % self.per_volume) * self.bucket_bytes


RELEASE_KEYS_PATH = Path(__file__).resolve().parent / "release_keys.txt"


def release_keys(path: Path = RELEASE_KEYS_PATH) -> list[bytes]:
    """The Ed25519 public keys release manifests are signed with (hex, one per line; '#' comments).
    Empty until the project has a signing key (see docs/SPEC_ATLAS.md)."""
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if len(line) == 64:
            out.append(bytes.fromhex(line))
    return out


# ---------------------------------------------------------------------------
# the local index
# ---------------------------------------------------------------------------

class ShelfIndex:
    """Titles, their buckets and the key terms of every article on the shelf — all memory-mapped
    arrays (millions of articles cost little RAM)."""

    def __init__(self, folder: Path):
        self.dir = Path(folder)
        load = lambda name: np.load(self.dir / name, mmap_mode="r")          # noqa: E731
        self._titles = np.memmap(self.dir / "titles.bin", dtype=np.uint8, mode="r") \
            if (self.dir / "titles.bin").stat().st_size else np.zeros(0, np.uint8)
        self.title_off = load("title_off.npy")
        self.bucket = load("bucket.npy")
        self.term_hash = load("term_hash.npy")
        self.ptr = load("ptr.npy")
        self.post = load("post.npy")
        self.idf = load("idf.npy")
        self.name_hash = load("name_hash.npy")
        self.name_doc = load("name_doc.npy")

    def __len__(self) -> int:
        return len(self.title_off) - 1

    def title(self, doc: int) -> str:
        a, b = int(self.title_off[doc]), int(self.title_off[doc + 1])
        return bytes(self._titles[a:b]).decode("utf-8")

    def lookup(self, name: str) -> int | None:
        """The article a title or name form (a Wikipedia redirect such as "JFK") points to."""
        if not len(self.name_hash):
            return None
        h = np.uint64(term_hash(name_key(name)))
        lo = int(np.searchsorted(self.name_hash, h))
        hi = int(np.searchsorted(self.name_hash, h, side="right"))
        if lo >= hi:
            return None
        if hi - lo == 1:
            return int(self.name_doc[lo])
        # several articles share the name form ("Albert Einstein", "Albert Einstein (album)"): the one
        # titled exactly so, else one without a "(…)" qualifier, else the most often named one
        docs = [int(self.name_doc[i]) for i in range(lo, min(hi, lo + 64))]
        want = " ".join(name.lower().split())
        exact = [d for d in docs if self.title(d).lower() == want]
        if exact:
            return exact[0]
        plain = [d for d in docs if "(" not in self.title(d)]
        pool = plain or docs
        return max(set(pool), key=lambda d: (pool.count(d), -d))

    def search(self, query: str, k: int = 3, prefer_title: str | None = None) -> list[tuple[int, float]]:
        """(title id, score), best first."""
        qt = list(dict.fromkeys(tokens(query)))
        scores: dict[int, float] = {}
        for t in qt:
            i = self._term(t)
            if i is None:
                continue
            w = float(self.idf[i])
            for doc in self.post[int(self.ptr[i]):int(self.ptr[i + 1])]:
                scores[int(doc)] = scores.get(int(doc), 0.0) + w
        # a title or name form named in the question ("… the Eiffel Tower …") counts a lot
        for name in ([prefer_title] if prefer_title else []) + _ngrams(query.lower()):
            d = self.lookup(name)
            if d is not None:
                scores[d] = scores.get(d, 0.0) + 8.0 + 2.0 * len(name.split())
        return sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:k]

    def _term(self, t: str) -> int | None:
        h = term_hash(t)
        # compact indexes keep the low 32 bits of each term hash (a rare collision only adds noise)
        h = np.uint32(h & 0xFFFFFFFF) if self.term_hash.dtype == np.uint32 else np.uint64(h)
        i = int(np.searchsorted(self.term_hash, h))
        return i if i < len(self.term_hash) and self.term_hash[i] == h else None

    def bucket_for(self, doc: int) -> int:
        return int(self.bucket[doc])


def _ngrams(s: str, n_max: int = 5) -> list[str]:
    ws = re.findall(r"[a-z0-9'\-]+", s)
    out = []
    for n in range(min(n_max, len(ws)), 0, -1):
        for i in range(len(ws) - n + 1):
            g = " ".join(ws[i:i + n])
            if n > 1 or g not in _STOP:
                out.append(g)
    return out


# ---------------------------------------------------------------------------
# the client
# ---------------------------------------------------------------------------

class ShelfClient:
    """Fetches buckets through the egress (channel ``shelf``) with decoys, checks them, caches them."""

    def __init__(self, manifest: ShelfManifest, base_url: str, index: ShelfIndex, egress, cache_dir: Path,
                 cache_bytes: int = 500 << 20, decoys: int = 2, allow_hosts: tuple[str, ...] = SHELF_HOSTS,
                 allow_loopback: bool = False):
        self.m = manifest
        self.base = base_url.rstrip("/") + "/"
        self.index = index
        self.egress = egress
        self.cache = Path(cache_dir)
        self.cache_bytes = cache_bytes
        self.decoys = decoys
        self.allow_hosts = allow_hosts
        self.allow_loopback = allow_loopback
        self.n = 0

    def _cached(self, b: int) -> bytes | None:
        p = self.cache / f"{b}.bkt"
        if not p.exists():
            return None
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != self.m.bucket_sha256[b]:
            p.unlink(missing_ok=True)
            return None
        os.utime(p)                                   # most recently used
        return data

    def _store(self, b: int, data: bytes) -> None:
        self.cache.mkdir(parents=True, exist_ok=True)
        tmp = self.cache / f"{b}.tmp"
        tmp.write_bytes(data)
        tmp.replace(self.cache / f"{b}.bkt")
        files = sorted(self.cache.glob("*.bkt"), key=lambda p: p.stat().st_mtime)
        total = sum(p.stat().st_size for p in files)
        while files and total > self.cache_bytes:
            old = files.pop(0)
            total -= old.stat().st_size
            old.unlink(missing_ok=True)

    def decoy_buckets(self, seed: str, avoid: set[int]) -> list[int]:
        """Decoys from a counter and a per-installation seed — never from the question."""
        out = []
        i = 0
        while len(out) < self.decoys and i < 64:
            self.n += 1
            b = int.from_bytes(hashlib.shake_256(f"{seed}|decoy|{self.n}".encode()).digest(8), "little") % self.m.buckets
            if b not in avoid and b not in out:
                out.append(b)
            i += 1
        return out

    def fetch_buckets(self, wanted: list[int], seed: str) -> dict[int, bytes]:
        """The wanted buckets (from the cache, or fetched with decoys in a mixed order)."""
        from engramm.web.egress import Request
        got: dict[int, bytes] = {}
        missing = []
        for b in dict.fromkeys(wanted):
            data = self._cached(b)
            if data is not None:
                got[b] = data
            else:
                missing.append(b)
        if not missing:
            return got
        order = missing + self.decoy_buckets(seed, set(missing))
        order.sort(key=lambda b: hashlib.shake_256(f"{seed}|order|{self.n}|{b}".encode()).digest(4))
        tor = bool(self.egress.settings["channels"]["shelf"].get("tor"))     # optional: the host sees no IP
        for b in order:
            name, off = self.m.locate(b)
            res = self.egress.fetch(Request("shelf", self.base + name, f"bucket {b}", self.allow_hosts,
                                            range=(off, off + self.m.bucket_bytes - 1),
                                            max_bytes=self.m.bucket_bytes, tor=tor,
                                            allow_loopback=self.allow_loopback))
            if not res.ok or len(res.body) != self.m.bucket_bytes:
                continue
            if hashlib.sha256(res.body).hexdigest() != self.m.bucket_sha256[b]:
                continue                               # a wrong bucket is dropped, never read
            self._store(b, res.body)
            if b in missing:
                got[b] = res.body
        return got

    def documents(self, query: str, k: int = 3, seed: str = "engramm", prefer_title: str | None = None) -> list[dict]:
        """The full texts of the k best articles for a question ({"t", "s", "x", "bucket"})."""
        hits = self.index.search(query, k=k, prefer_title=prefer_title)
        if not hits:
            return []
        # only articles about as relevant as the best one: a weak match only adds noise
        hits = [h for h in hits if h[1] >= MIN_RELATIVE * hits[0][1]]
        want = {doc: self.index.bucket_for(doc) for doc, _ in hits}
        buckets = self.fetch_buckets(list(want.values()), seed)
        out = []
        for doc, _ in hits:
            b = want[doc]
            if b not in buckets:
                continue
            title = self.index.title(doc)
            for d in unpack_bucket(buckets[b]):
                if d.get("t") == title:
                    out.append({**d, "bucket": b})
                    break
        return out


# ---------------------------------------------------------------------------
# sentences for the answer extraction
# ---------------------------------------------------------------------------

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")
MIN_RELATIVE = 0.4           # a fetched article scores at least this share of the best one


_ALT_WORDS = {
    "won": ("win", "wins", "winning", "winner", "winners", "champion", "champions", "crowned", "title", "victory"),
    "win": ("won", "wins", "winning", "winner", "winners", "champion", "champions", "crowned", "title", "victory"),
    "winner": ("won", "win", "winning", "champion", "champions", "crowned"),
    "born": ("birth", "née"), "died": ("death", "dead", "killed"), "die": ("died", "death"),
    "founded": ("founder", "founders", "established", "co-founded", "founding"),
    "wrote": ("written", "author", "writer", "novel", "authored"), "written": ("wrote", "author", "writer"),
    "invented": ("inventor", "invention", "developed", "patented"), "discovered": ("discovery", "discoverer"),
    "directed": ("director", "directing"), "painted": ("painter", "painting"), "built": ("constructed", "construction"),
    "launched": ("launch", "lift-off", "liftoff"), "launch": ("launched", "lift-off", "liftoff"),
    "scorer": ("scored", "goals", "golden"), "ceo": ("chief", "executive"), "president": ("elected", "presidency"),
    "located": ("situated", "lies", "capital"), "invent": ("invented", "inventor", "invention"),
}


def best_sentences(query: str, docs: list[dict], n: int = 12, lead: int = 2,
                   context: bool = False) -> list[tuple]:
    """The sentences of the fetched articles that share the most (idf-weighted) words with the
    question, best first: (score, sentence, document) — with ``context`` also the two sentences
    before it. The first ``lead`` sentences of each article always come along (they define the
    subject: "Alonzo "Lonnie" Johnson (February 8, 1899 – June 16, 1970) was …"); reference lists
    and bibliography lines never do."""
    from engramm.web.clean import SENTENCE, is_reference, strip_references
    qt = set(tokens(query))
    if not qt:
        return []
    # the words an answer sentence uses for the question's verb ("won" → "crowned the champions after
    # winning"); they count a little less than the question's own words
    alt = {w for t in qt for w in _ALT_WORDS.get(t, ())} - qt
    qt |= alt
    sents: list[tuple[str, dict, int, str]] = []
    for d in docs:
        pos, prev = 0, []
        for para in strip_references(d.get("x", "")).split("\n"):
            for s in SENTENCE.split(para.strip()):
                s = s.strip()
                if 25 <= len(s) <= 600 and not is_reference(s):
                    sents.append((s, d, pos, " ".join(prev[-2:])))
                    prev.append(s)
                    pos += 1
    if not sents:
        return []
    df: dict[str, int] = {}
    toks = []
    for s, *_ in sents:
        ts = set(tokens(s))
        toks.append(ts)
        for t in ts & qt:
            df[t] = df.get(t, 0) + 1
    N = len(sents)
    scored, leads = [], []
    for (s, d, pos, prev), ts in zip(sents, toks):
        hit = ts & qt
        # the article's own title words are implied in every sentence of it ("it is 330 metres tall"):
        # they count little, the other question words decide
        title = set(tokens(d.get("t", "")))
        score = sum(math.log(1 + N / df[t]) * (0.3 if t in title else 0.7 if t in alt else 1.0) for t in hit) \
            / math.sqrt(1 + 0.02 * len(ts))
        row = (score, s, d, prev) if context else (score, s, d)
        if pos < lead:
            leads.append(row)
        elif hit:
            scored.append(row)
    scored.sort(key=lambda x: -x[0])
    out = sorted(leads + scored[:max(0, n - len(leads))], key=lambda x: -x[0])
    return out


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
