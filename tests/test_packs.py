"""Knowledge-pack tooling: release preparation (flat assets, pinned catalog entry) and the
cleaning of article leads for the reading."""

from __future__ import annotations

import hashlib
import json
import sys

from experiments import pack_release
from experiments.reading_abstracts import clean, title_of, unescape


def _pack(d):
    (d / "nlp").mkdir(parents=True)
    (d / "corpus.u16").write_bytes(b"\x01\x02" * 100)
    (d / "nlp" / "pos.json").write_text("{}")
    files = {p.relative_to(d).as_posix(): {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(d.rglob("*")) if p.is_file()}
    m = {"pack": "lite", "version": "3.0.0", "bytes": sum(f["bytes"] for f in files.values()), "files": files,
         "info": {"reading": "article leads"}}
    (d / "manifest.json").write_text(json.dumps(m))
    return m


def test_pack_release(tmp_path, monkeypatch):
    pack, out, cat = tmp_path / "pack", tmp_path / "out", tmp_path / "catalog.json"
    _pack(pack)
    monkeypatch.setattr(sys, "argv", ["x", "--pack", str(pack), "--out", str(out), "--catalog", str(cat),
                                      "--repo", "o/r"])
    pack_release.main()
    assert sorted(p.name for p in out.iterdir()) == ["corpus.u16", "manifest.json", "nlp__pos.json"]
    entry = json.loads(cat.read_text())["packs"][0]
    assert entry["base_url"] == "https://github.com/o/r/releases/download/pack-lite-3.0.0/"
    assert entry["manifest_sha256"] == hashlib.sha256((pack / "manifest.json").read_bytes()).hexdigest()
    # a damaged pack is refused
    (pack / "corpus.u16").write_bytes(b"\x00\x02" * 100)
    try:
        pack_release.main()
        raise AssertionError("damaged pack was accepted")
    except SystemExit as e:
        assert "does not match" in str(e)


def test_reading_cleaning():
    assert unescape(r'He said \"hi\" é') == 'He said "hi" é'
    assert title_of("Mona_Lisa") == "Mona Lisa" and title_of("AC%2FDC") == "AC/DC"
    assert clean("The Mona Lisa (/ˌmoʊnə ˈliːsə/; Italian: [ˈdʒɔːkonda]) is a painting (oil on panel).") == \
        "The Mona Lisa is a painting (oil on panel)."
    assert clean("A  b ( ; ) c.") == "A b c."
