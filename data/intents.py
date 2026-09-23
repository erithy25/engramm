"""Intent-classification datasets for M2 and M5: Banking77 and CLINC150.

Both are used through their official splits and follow the conventions of
:mod:`data.loaders`: digest-verified downloads, sorted label order, few-shot
subsetting only when requested explicitly and only with the run's seeded
generator.

* **Banking77** (PolyAI, 2020) — 77 banking intents, 10,003 training and
  3,080 test utterances.
* **CLINC150** (Larson et al., 2019, ``data_full.json``) — 150 in-scope
  intents, 100 training / 20 validation / 30 test utterances each. The
  out-of-scope examples are not used: the historical M5 comparison and the
  baselines are 150-way in-scope classification, and mixing in an
  out-of-scope class would change the task.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from data.loaders import Dataset, apply_shots, download_and_verify

#: Digests verified by downloading the files and hashing them (2026-09-23).
BANKING77_SOURCES = {
    "train": {
        "url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/"
               "master/banking_data/train.csv",
        "filename": "banking77_train.csv",
        "sha256": "b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b",
    },
    "test": {
        "url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/"
               "master/banking_data/test.csv",
        "filename": "banking77_test.csv",
        "sha256": "d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d",
    },
}

CLINC150_SOURCE = {
    "url": "https://raw.githubusercontent.com/clinc/oos-eval/master/data/data_full.json",
    "filename": "clinc150_data_full.json",
    "sha256": "36923c3705a59e08fe9c3883d8bc2dd966ef93e22cb78ac41171782a698d56e0",
}

BANKING77_N_CLASSES = 77
CLINC150_N_CLASSES = 150


def _check_shots(shots: int | None, rng: np.random.Generator | None) -> None:
    if shots is None:
        return
    if shots <= 0:
        raise ValueError(f"shots must be positive, got {shots}")
    if rng is None:
        raise ValueError("shots requires an explicit rng from set_all_seeds(seed)")


def _build(name: str, x_train: list[str], y_train_raw: list[str], x_test: list[str],
           y_test_raw: list[str], shots: int | None, rng: np.random.Generator | None,
           metadata: dict[str, Any], n_classes: int) -> Dataset:
    labels = tuple(sorted(set(y_train_raw)))
    if len(labels) != n_classes:
        raise RuntimeError(f"{name}: expected {n_classes} classes, found {len(labels)}")
    if set(y_test_raw) - set(labels):
        raise RuntimeError(f"{name}: test split has classes absent from training")
    index_of = {label: i for i, label in enumerate(labels)}
    y_train = np.array([index_of[y] for y in y_train_raw], dtype=np.int64)
    y_test = np.array([index_of[y] for y in y_test_raw], dtype=np.int64)
    metadata = {**metadata, "official_split": True, "shots": shots,
                "full_train_size": len(x_train)}
    train_texts: tuple[str, ...] = tuple(x_train)
    if shots is not None:
        train_texts, y_train = apply_shots(train_texts, y_train, shots, len(labels), rng)
        metadata["shot_selection"] = "seeded uniform sample per class, without replacement"
    full = set(x_train)
    metadata["test_in_full_train"] = np.fromiter((t in full for t in x_test), dtype=bool,
                                                 count=len(x_test))
    return Dataset(name=name, x_train=train_texts, y_train=y_train,
                   x_test=tuple(x_test), y_test=y_test, labels=labels,
                   metadata=metadata)


def _read_banking_csv(path: Path) -> tuple[list[str], list[str]]:
    texts, labels = [], []
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            texts.append(row["text"])
            labels.append(row["category"])
    return texts, labels


def load_banking77(cache_dir: Path | str | None = None, shots: int | None = None,
                   rng: np.random.Generator | None = None,
                   allow_download: bool = True) -> Dataset:
    """Banking77 from its official train/test CSVs."""
    _check_shots(shots, rng)
    paths = {key: download_and_verify(**source, cache_dir=cache_dir,
                                      allow_download=allow_download)
             for key, source in BANKING77_SOURCES.items()}
    x_train, y_train = _read_banking_csv(paths["train"])
    x_test, y_test = _read_banking_csv(paths["test"])
    if (len(x_train), len(x_test)) != (10_003, 3_080):
        raise RuntimeError(f"Banking77: unexpected split sizes {len(x_train)}/{len(x_test)}")
    return _build("banking77", x_train, y_train, x_test, y_test, shots, rng,
                  {"source": {k: v["url"] for k, v in BANKING77_SOURCES.items()},
                   "sha256": {k: v["sha256"] for k, v in BANKING77_SOURCES.items()}},
                  BANKING77_N_CLASSES)


def load_clinc150(cache_dir: Path | str | None = None, shots: int | None = None,
                  rng: np.random.Generator | None = None,
                  allow_download: bool = True,
                  split: str = "test") -> Dataset:
    """CLINC150 in-scope intents from ``data_full.json``.

    ``split`` selects the evaluation split: ``"test"`` (4,500) for results,
    ``"val"`` (3,000) for model selection. The two are never mixed.
    """
    if split not in ("test", "val"):
        raise ValueError("split must be 'test' or 'val'")
    _check_shots(shots, rng)
    path = download_and_verify(**CLINC150_SOURCE, cache_dir=cache_dir,
                               allow_download=allow_download)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    x_train = [text for text, _ in data["train"]]
    y_train = [intent for _, intent in data["train"]]
    x_eval = [text for text, _ in data[split]]
    y_eval = [intent for _, intent in data[split]]
    return _build("clinc150", x_train, y_train, x_eval, y_eval, shots, rng,
                  {"source": CLINC150_SOURCE["url"], "sha256": CLINC150_SOURCE["sha256"],
                   "evaluation_split": split, "out_of_scope": "excluded"},
                  CLINC150_N_CLASSES)

