"""The shelf (engramm/web/shelf.py, experiments/shelf_build.py): build a small shelf, serve its
volumes from a local server with range requests, find articles through the local index, fetch
their buckets with decoys through the egress, reject a tampered bucket, use the cache."""

from __future__ import annotations

import hashlib
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from experiments.shelf_build import build
from engramm.web.egress import Egress, NetworkLog, PythonBackend
from engramm.web.shelf import ShelfClient, ShelfIndex, ShelfManifest, best_sentences, unpack_bucket

WORDS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliett kilo lima mike november oscar papa "
         "quebec romeo sierra tango uniform victor whiskey xray yankee zulu").split()


def _noise(i: int, k: int) -> str:
    # incompressible-ish filler, so buckets fill up like real text
    h = hashlib.sha256(f"{i}-{k}".encode()).hexdigest()
    return " ".join(h[j:j + 6] for j in range(0, 48, 6))


def _docs(n=400):
    out = []
    for i in range(n):
        w = WORDS[i % len(WORDS)]
        title = f"Topic {i} {w.title()}"
        body = (f"{title} is a made-up article number {i}. It is known for the rare word zq{i}x and for {w}. "
                + " ".join(f"Sentence {k} of article {i} mentions {_noise(i, k)}." for k in range(12)))
        out.append({"t": title, "s": "test", "x": body})
    out.append({"t": "Eiffel Tower", "s": "test", "x": "The Eiffel Tower is a wrought-iron lattice tower in Paris. "
                "It is 330 metres tall and was completed in 1889. Gustave Eiffel's company built it."})
    return out


class _Range(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        path = Path(self.directory) / self.path.lstrip("/")
        rng = self.headers.get("Range")
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        code = 200
        if rng:
            a, b = (int(x) for x in rng.split("=")[1].split("-"))
            data, code = data[a:b + 1], 206
        self.send_response(code)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture(scope="module")
def shelf(tmp_path_factory):
    root = tmp_path_factory.mktemp("shelf")
    src = root / "docs.jsonl"
    src.write_text("\n".join(json.dumps(d) for d in _docs()), encoding="utf-8")
    out = root / "out"
    manifest = build([src], [], out, bucket_kb=64, sample=1000, key_terms=8, workers=2)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Range, directory=str(out)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield out, manifest, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _client(out, url, tmp_path):
    eg = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"))
    eg.backend = PythonBackend()
    eg.set_channel("shelf", enabled=True)
    m = ShelfManifest.load(out / "shelf.json")
    return ShelfClient(m, url, ShelfIndex(out / "shelf_index"), eg, tmp_path / "cache", decoys=2,
                       allow_loopback=True), eg


def test_build_layout(shelf):
    out, manifest, _ = shelf
    assert manifest["docs"] == 401 and manifest["buckets"] >= 2
    m = ShelfManifest.load(out / "shelf.json")
    assert all(v["bytes"] % m.bucket_bytes == 0 for v in m.volumes)
    data = (out / m.volumes[0]["name"]).read_bytes()[:m.bucket_bytes]
    docs = unpack_bucket(data)
    assert docs == [] or {"t", "s", "x"} <= set(docs[0])


def test_search_fetch_with_decoys_and_cache(shelf, tmp_path):
    out, _, url = shelf
    client, eg = _client(out, url, tmp_path)
    docs = client.documents("Which rare word is article 123 known for?", k=1, seed="install-1", prefer_title=None)
    assert docs and "zq" in docs[0]["x"]
    docs = client.documents("How tall is the Eiffel Tower?", k=1, seed="install-1")
    assert docs and docs[0]["t"] == "Eiffel Tower"
    sents = best_sentences("How tall is the Eiffel Tower?", docs)
    assert sents and "330 metres" in sents[0][1]
    log = eg.log.tail(50)
    fetched = [x for x in log if x["channel"] == "shelf" and x["ok"]]
    assert len(fetched) >= 3                     # the wanted bucket and two decoys
    assert all(x["what"].startswith("bucket ") for x in log)
    assert all("Eiffel" not in json.dumps(x) and "tall" not in json.dumps(x) for x in log)   # never the question
    n = len(eg.log.tail(100))
    client.documents("How tall is the Eiffel Tower?", k=1, seed="install-1")
    assert len(eg.log.tail(100)) == n            # second time: from the cache, nothing fetched


def test_tampered_bucket_is_rejected(shelf, tmp_path):
    out, _, url = shelf
    client, eg = _client(out, url, tmp_path)
    m = client.m
    b = client.index.bucket_for(client.index.search("Eiffel Tower", k=1)[0][0])
    good = m.bucket_sha256[b]
    m.bucket_sha256[b] = "0" * 64                # the manifest says something else: the bucket must not be used
    try:
        assert client.documents("How tall is the Eiffel Tower?", k=1, seed="s") == []
    finally:
        m.bucket_sha256[b] = good


def test_shelf_off_means_no_traffic(shelf, tmp_path):
    out, _, url = shelf
    client, eg = _client(out, url, tmp_path)
    eg.set_channel("shelf", enabled=False)
    from engramm.web.egress import EgressError
    with pytest.raises(EgressError):
        client.documents("How tall is the Eiffel Tower?", k=1, seed="s")


def test_ed25519_matches_rfc8032():
    from engramm.web import ed25519
    sk = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
    pk = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
    sig = bytes.fromhex("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
                        "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
    assert ed25519.public_key(sk) == pk and ed25519.sign(sk, b"\x72") == sig
    assert ed25519.verify(pk, b"\x72", sig) and not ed25519.verify(pk, b"\x73", sig)


def test_signed_manifest_and_a_refused_unsigned_one(shelf, tmp_path, monkeypatch):
    import shutil

    import engramm.web.shelf as shelf_mod
    from engramm.web.atlas import Atlas
    from engramm.web.ed25519 import public_key
    out, _, url = shelf
    seed = bytes(range(32))
    m = ShelfManifest.load(out / "shelf.json")
    m.sign(seed)
    assert m.verify([public_key(seed)]) and not m.verify([public_key(bytes(32))])
    m.bucket_sha256[0] = "0" * 64                       # a changed bucket hash breaks the signature
    assert not m.verify([public_key(seed)])
    # an app with a release key uses only a manifest signed by it
    pack = tmp_path / "pack"
    shutil.copytree(out / "shelf_index", pack / "shelf_index")
    (pack / "shelf_source.json").write_text(json.dumps({"base_url": url + "/", "hosts": ["127.0.0.1"],
                                                        "allow_loopback": True}))
    keys = tmp_path / "keys.txt"
    keys.write_text(public_key(seed).hex() + "\n")
    monkeypatch.setattr(shelf_mod, "RELEASE_KEYS_PATH", keys)
    monkeypatch.setattr(shelf_mod.release_keys, "__defaults__", (keys,))
    eg = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(None), backend=PythonBackend())
    shutil.copy(out / "shelf.json", pack / "shelf.json")              # unsigned
    a = Atlas(eg, pack, tmp_path / "state")
    assert a.shelf is None and "not signed" in a.status()["shelf_error"]
    good = ShelfManifest.load(out / "shelf.json")
    good.sign(seed)
    (pack / "shelf.json").write_text(json.dumps(good.to_dict()))
    a = Atlas(eg, pack, tmp_path / "state2")
    assert a.shelf is not None and a.status()["shelf"]["signed"] is True


def test_merged_shelf_of_two_builds(tmp_path):
    from experiments.shelf_merge import merge
    docs = _docs(300)
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    a.write_text("\n".join(json.dumps(d) for d in docs[:150]), encoding="utf-8")
    b.write_text("\n".join(json.dumps(d) for d in docs[150:]), encoding="utf-8")
    build([a], [], tmp_path / "pa", bucket_kb=64, sample=1000, key_terms=8, workers=2)
    build([b], [], tmp_path / "pb", bucket_kb=64, sample=1000, key_terms=8, workers=2)
    info = merge([tmp_path / "pa", tmp_path / "pb"], tmp_path / "m")
    m = ShelfManifest.load(tmp_path / "m" / "shelf.json")
    assert info["docs"] == len(docs) and m.buckets == len(m.bucket_sha256)
    assert all((tmp_path / "m" / v["name"]).exists() for v in m.volumes)
    ix = ShelfIndex(tmp_path / "m" / "shelf_index")
    assert ix.term_hash.dtype == np.uint32 and ix.idf.dtype == np.float16
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Range, directory=str(tmp_path / "m")))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        client, eg = _client(tmp_path / "m", f"http://127.0.0.1:{srv.server_address[1]}", tmp_path)
        for q, want in (("Which rare word is article 12 known for?", "zq12x"),
                        ("Which rare word is article 287 known for?", "zq287x")):     # one from each part
            got = client.documents(q, k=1, seed="s")
            assert got and want in got[0]["x"], (q, [d["t"] for d in got])
        assert ix.lookup("Eiffel Tower") is not None
    finally:
        srv.shutdown()
    lite = merge([tmp_path / "m"], tmp_path / "lite", aliases=False, index_only=True)
    assert lite["docs"] == len(docs) and not any((tmp_path / "lite").glob("*.bin"))


import numpy as np  # noqa: E402
