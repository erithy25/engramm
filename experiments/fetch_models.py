"""Download the M5 baseline models at pinned revisions and verify their digests.

    .venv_b1/bin/python -m experiments.fetch_models            # fetch + verify
    .venv_b1/bin/python -m experiments.fetch_models --verify   # verify only

The same discipline as the datasets (``data/loaders.py``): every artifact is
pinned by revision and checked by SHA-256 before a harness may use it, and a
mismatch is an error, never a warning. Everything lands under ``models/``
(gitignored): the GGUF file for B1 at the top level, the Hugging Face
snapshots for B0/B1 (embeddings) and B3 (LoRA base model) under
``models/hf`` — the cache ``experiments/m5_baselines.py`` reads with
``HF_HUB_OFFLINE=1``.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODELS = REPO / "models"
HF_HOME = MODELS / "hf"

#: B1 — llama.cpp model. Revision-independent URL, pinned by digest.
GGUF = {
    "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/"
           "qwen2.5-3b-instruct-q4_k_m.gguf",
    "path": MODELS / "qwen2.5-3b-instruct-q4_k_m.gguf",
    "sha256": "626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d",
}

#: Hugging Face snapshots: repository, pinned commit, digest of the weights.
SNAPSHOTS = {
    "BAAI/bge-small-en-v1.5": {
        "revision": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
        "weights": "model.safetensors",
        "sha256": "3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad",
    },
    "Qwen/Qwen2.5-0.5B-Instruct": {
        "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "weights": "model.safetensors",
        "sha256": "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe",
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_dir(repo: str, revision: str) -> Path:
    return HF_HOME / "hub" / f"models--{repo.replace('/', '--')}" / "snapshots" / revision


def fetch_gguf() -> None:
    target = GGUF["path"]
    if target.exists() and sha256_file(target) == GGUF["sha256"]:
        print(f"ok   {target.name}")
        return
    partial = target.with_suffix(".part")
    MODELS.mkdir(parents=True, exist_ok=True)
    print(f"get  {GGUF['url']}")
    urllib.request.urlretrieve(GGUF["url"], partial)
    actual = sha256_file(partial)
    if actual != GGUF["sha256"]:
        partial.unlink()
        raise SystemExit(f"{target.name}: SHA-256 {actual}, expected {GGUF['sha256']}")
    partial.rename(target)
    print(f"ok   {target.name}")


def fetch_snapshot(repo: str, spec: dict[str, str]) -> None:
    from huggingface_hub import snapshot_download

    os.environ.setdefault("HF_HOME", str(HF_HOME))
    path = Path(snapshot_download(repo, revision=spec["revision"],
                                  cache_dir=str(HF_HOME / "hub")))
    verify_snapshot(repo, spec, path)


def verify_snapshot(repo: str, spec: dict[str, str], path: Path | None = None) -> None:
    path = path or snapshot_dir(repo, spec["revision"])
    weights = path / spec["weights"]
    if not weights.exists():
        raise SystemExit(f"{repo}@{spec['revision'][:12]}: {spec['weights']} missing")
    actual = sha256_file(weights)
    if actual != spec["sha256"]:
        raise SystemExit(f"{repo}: SHA-256 {actual}, expected {spec['sha256']}")
    print(f"ok   {repo}@{spec['revision'][:12]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verify", action="store_true", help="check digests, download nothing")
    args = parser.parse_args(argv)
    if args.verify:
        if sha256_file(GGUF["path"]) != GGUF["sha256"]:
            raise SystemExit(f"{GGUF['path'].name}: digest mismatch")
        print(f"ok   {GGUF['path'].name}")
        for repo, spec in SNAPSHOTS.items():
            verify_snapshot(repo, spec)
        return 0
    fetch_gguf()
    for repo, spec in SNAPSHOTS.items():
        fetch_snapshot(repo, spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
