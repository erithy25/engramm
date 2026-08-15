"""Dataset loaders with verified downloads and train-only feature fitting.

Two datasets, both used through their official splits:

* **WiLI-2018** — 235 languages, 500 training and 500 test paragraphs each
  (117,500 per split). Few-shot subsetting is available but never implicit:
  ``shots`` must be requested explicitly and needs a generator, so a
  few-shot number can never be mistaken for a full-data one.
* **MNIST** — the official 60,000 / 10,000 split, used as-is. No custom
  partitioning, no validation split carved out silently.

Everything fitted from data — vocabularies, scaling, statistics — is
computed in :func:`fit_train_artifacts` from the **training split only**.
That is enforced by ``tests/test_no_leakage.py``, which refits with the test
split replaced by garbage and requires the artifacts to come out identical.

Downloads are cached in ``data/cache/`` (gitignored) and verified against
the SHA-256 digests recorded below. A digest mismatch is an error, never a
warning: silently training on a different file than the one the results
claim would invalidate every number downstream.
"""

from __future__ import annotations

import gzip
import hashlib
import shutil
import struct
import urllib.request
import zipfile
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np

CACHE_DIR = Path(__file__).resolve().parent / "cache"

#: Digests verified by downloading the files and hashing them, not copied
#: from a third party. Re-verify with ``sha256sum`` if a source ever moves.
WILI_SOURCE = {
    "url": "https://zenodo.org/records/841984/files/wili-2018.zip?download=1",
    "filename": "wili-2018.zip",
    "sha256": "727e52ca4e13400e6def1b1b594ca12c8b7fd49ad9d45fd5c9e57a1f6d3b7a3f",
}

MNIST_SOURCES = {
    "train_images": {
        "url": "https://ossci-datasets.s3.amazonaws.com/mnist/train-images-idx3-ubyte.gz",
        "filename": "train-images-idx3-ubyte.gz",
        "sha256": "440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609",
    },
    "train_labels": {
        "url": "https://ossci-datasets.s3.amazonaws.com/mnist/train-labels-idx1-ubyte.gz",
        "filename": "train-labels-idx1-ubyte.gz",
        "sha256": "3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c",
    },
    "test_images": {
        "url": "https://ossci-datasets.s3.amazonaws.com/mnist/t10k-images-idx3-ubyte.gz",
        "filename": "t10k-images-idx3-ubyte.gz",
        "sha256": "8d422c7b0a1c1c79245a5bcf07fe86e33eeafee792b84584aec276f5a2dbc4e6",
    },
    "test_labels": {
        "url": "https://ossci-datasets.s3.amazonaws.com/mnist/t10k-labels-idx1-ubyte.gz",
        "filename": "t10k-labels-idx1-ubyte.gz",
        "sha256": "f7ae60f92e00ec6debd23a6088c31dbd2371eca3ffa0defaefb259924204aec6",
    },
}

#: Registered in ``docs/PREREG_ROBUSTNESS.md`` §3.
WILI_N_CLASSES = 235
WILI_PER_CLASS = 500
WILI_VOCABULARY_SIZE = 10_000
MNIST_N_TRAIN = 60_000
MNIST_N_TEST = 10_000
#: Registered pixel scaling: a constant divisor, not a fitted statistic.
MNIST_PIXEL_DIVISOR = 255.0


# ---------------------------------------------------------------------------
# Containers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Dataset:
    """A loaded dataset with its official split kept separate.

    Attributes
    ----------
    name:
        Dataset identifier, e.g. ``"wili"`` or ``"mnist"``.
    x_train, x_test:
        Inputs. Texts are a tuple of ``str``; images are a ``uint8`` array
        of shape ``(N, 784)``.
    y_train, y_test:
        Class indices as ``int64``, indexing into :attr:`labels`.
    labels:
        Class names in sorted order. Sorted rather than first-seen, so the
        index of a class never depends on data order or on hash iteration
        order.
    metadata:
        Provenance and configuration: source digests, split sizes, whether
        few-shot subsetting was applied, chance level.
    """

    name: str
    x_train: tuple[str, ...] | np.ndarray
    y_train: np.ndarray
    x_test: tuple[str, ...] | np.ndarray
    y_test: np.ndarray
    labels: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_classes(self) -> int:
        return len(self.labels)

    @property
    def n_train(self) -> int:
        return int(len(self.y_train))

    @property
    def n_test(self) -> int:
        return int(len(self.y_test))

    @property
    def chance_level(self) -> float:
        """Accuracy of uniform guessing — the floor every metric sits above."""
        return 1.0 / self.n_classes

    def __repr__(self) -> str:
        return (f"Dataset(name={self.name!r}, n_classes={self.n_classes}, "
                f"n_train={self.n_train}, n_test={self.n_test})")


@dataclass(frozen=True)
class TrainArtifacts:
    """Everything fitted from data, fitted from the training split alone.

    Kept as one object so that "was anything fitted on test?" is a question
    about a single function (:func:`fit_train_artifacts`) rather than a
    property scattered across a pipeline.
    """

    dataset_name: str
    #: Character trigrams for the text baselines, selected per
    #: ``docs/PREREG_ROBUSTNESS.md`` §3.2. Empty for image datasets.
    vocabulary: tuple[str, ...] = ()
    #: Document frequency of each vocabulary entry, over training texts.
    document_frequency: tuple[int, ...] = ()
    #: Constant registered divisor for pixel scaling; not fitted.
    pixel_divisor: float | None = None
    #: Per-pixel mean and standard deviation over the training images,
    #: available to baselines that standardise. Genuinely fitted, and
    #: therefore the thing a leakage test must watch.
    pixel_mean: np.ndarray | None = None
    pixel_std: np.ndarray | None = None

    def digest(self) -> str:
        """Stable hash of the artifacts, for cross-run and cross-platform checks."""
        hasher = hashlib.sha256()
        hasher.update(self.dataset_name.encode("utf-8"))
        for entry in self.vocabulary:
            hasher.update(b"\x00" + entry.encode("utf-8"))
        for value in self.document_frequency:
            hasher.update(b"\x01" + int(value).to_bytes(8, "big"))
        if self.pixel_divisor is not None:
            hasher.update(b"\x02" + repr(self.pixel_divisor).encode("ascii"))
        for array in (self.pixel_mean, self.pixel_std):
            if array is not None:
                hasher.update(b"\x03" + np.ascontiguousarray(
                    array, dtype=np.float64).tobytes())
        return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Download and verification
# ---------------------------------------------------------------------------

def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """SHA-256 of a file, read in chunks so large archives stay off the heap."""
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download_and_verify(url: str, filename: str, sha256: str,
                        cache_dir: Path | str | None = None,
                        allow_download: bool = True) -> Path:
    """Return a cached, digest-verified copy of a source file.

    A cached file whose digest matches is returned untouched. A cached file
    whose digest does *not* match is an error rather than a cue to
    re-download: a corrupted or substituted cache is exactly the situation
    where silently fetching a replacement would hide the problem.

    Set ``allow_download=False`` for offline use — the file must then
    already be cached, or a ``FileNotFoundError`` is raised.
    """
    directory = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename

    if destination.exists():
        actual = sha256_file(destination)
        if actual == sha256:
            return destination
        raise RuntimeError(
            f"cached file {destination} has SHA-256 {actual}, expected "
            f"{sha256}. Delete it deliberately if the source legitimately "
            f"changed — it is not replaced automatically."
        )

    if not allow_download:
        raise FileNotFoundError(
            f"{destination} is not cached and downloads are disabled. Run "
            f"the loader once with allow_download=True to populate the cache."
        )

    partial = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url) as response, open(partial, "wb") as handle:
        shutil.copyfileobj(response, handle)

    actual = sha256_file(partial)
    if actual != sha256:
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"downloaded {url} but its SHA-256 is {actual}, expected {sha256}"
        )
    partial.replace(destination)
    return destination


# ---------------------------------------------------------------------------
# WiLI-2018
# ---------------------------------------------------------------------------

def load_wili(cache_dir: Path | str | None = None,
              shots: int | None = None,
              rng: np.random.Generator | None = None,
              allow_download: bool = True) -> Dataset:
    """Load WiLI-2018 from its official split.

    Parameters
    ----------
    shots:
        ``None`` (the default) uses the full training split — 500 paragraphs
        per language. An integer selects that many training paragraphs per
        language, reproducing the historical M1 setting at ``shots=10``.

        The few-shot setting is never implicit. It changes what a result
        means, and the project's records show how easily "79.30 % on
        WiLI-2018" gets read as a full-data figure when the ``10-shot`` part
        is dropped. Requesting it takes an explicit argument, and the choice
        is recorded in :attr:`Dataset.metadata`.
    rng:
        Required when ``shots`` is given. Shot selection is random, so it
        must come from the run's seeded generator; there is deliberately no
        default, because an implicit seed would make a few-shot run
        irreproducible from its record alone.
    """
    if shots is not None:
        if shots <= 0:
            raise ValueError(f"shots must be positive, got {shots}")
        if shots > WILI_PER_CLASS:
            raise ValueError(
                f"shots={shots} exceeds the {WILI_PER_CLASS} training "
                f"paragraphs WiLI-2018 provides per language"
            )
        if rng is None:
            raise ValueError(
                "shots requires an explicit rng — pass the generator from "
                "set_all_seeds(seed) so the selection is reproducible"
            )

    archive = download_and_verify(**WILI_SOURCE, cache_dir=cache_dir,
                                  allow_download=allow_download)
    with zipfile.ZipFile(archive) as zf:
        x_train = zf.read("x_train.txt").decode("utf-8").splitlines()
        y_train_raw = zf.read("y_train.txt").decode("utf-8").splitlines()
        x_test = zf.read("x_test.txt").decode("utf-8").splitlines()
        y_test_raw = zf.read("y_test.txt").decode("utf-8").splitlines()

    if not (len(x_train) == len(y_train_raw) and len(x_test) == len(y_test_raw)):
        raise RuntimeError("WiLI archive is inconsistent: text and label counts differ")

    # sorted(), never set iteration: class indices must not depend on
    # PYTHONHASHSEED or on the order labels happen to appear.
    labels = tuple(sorted(set(y_train_raw)))
    if len(labels) != WILI_N_CLASSES:
        raise RuntimeError(
            f"expected {WILI_N_CLASSES} languages, found {len(labels)}"
        )
    index_of = {label: i for i, label in enumerate(labels)}
    y_train = np.array([index_of[y] for y in y_train_raw], dtype=np.int64)
    y_test = np.array([index_of[y] for y in y_test_raw], dtype=np.int64)

    metadata: dict[str, Any] = {
        "source": WILI_SOURCE["url"],
        "sha256": WILI_SOURCE["sha256"],
        "official_split": True,
        "shots": shots,
        "paragraphs_per_class_available": WILI_PER_CLASS,
        "full_train_size": len(x_train),
    }

    x_train_out: tuple[str, ...] = tuple(x_train)
    if shots is not None:
        x_train_out, y_train = apply_shots(
            x_train_out, y_train, shots, len(labels), rng)
        metadata["shot_selection"] = "seeded uniform sample per class, without replacement"

    return Dataset(
        name="wili",
        x_train=x_train_out,
        y_train=y_train,
        x_test=tuple(x_test),
        y_test=y_test,
        labels=labels,
        metadata=metadata,
    )


def apply_shots(x: Sequence[str], y: np.ndarray, shots: int, n_classes: int,
                rng: np.random.Generator) -> tuple[tuple[str, ...], np.ndarray]:
    """Reduce a split to ``shots`` examples per class, keeping pairs aligned.

    Separated from :func:`load_wili` so the indexing step is unit-testable:
    selecting correct indices and then indexing the *wrong* sequence would
    otherwise be an invisible way to pull examples out of the test split.
    ``tests/test_no_leakage.py`` checks that every returned
    ``(text, label)`` pair really occurs in the input split.
    """
    selected = _select_shots(y, shots, n_classes, rng)
    return tuple(x[i] for i in selected), y[selected]


def _select_shots(y: np.ndarray, shots: int, n_classes: int,
                  rng: np.random.Generator) -> np.ndarray:
    """Pick ``shots`` training indices per class, deterministically.

    Classes are visited in index order — which is sorted label order — and
    each draws from its own indices, so the selection depends only on the
    generator's state and not on how the data happened to be arranged.
    """
    chosen: list[np.ndarray] = []
    for class_index in range(n_classes):
        candidates = np.flatnonzero(y == class_index)
        if candidates.size < shots:
            raise ValueError(
                f"class {class_index} has {candidates.size} training examples, "
                f"fewer than the requested {shots} shots"
            )
        chosen.append(rng.choice(candidates, size=shots, replace=False))
    return np.sort(np.concatenate(chosen))


# ---------------------------------------------------------------------------
# MNIST
# ---------------------------------------------------------------------------

def load_mnist(cache_dir: Path | str | None = None,
               allow_download: bool = True) -> Dataset:
    """Load MNIST from its official 60,000 / 10,000 split.

    The split is used exactly as distributed: no reshuffling, no custom
    partition, and no validation split carved out of training. Images are
    returned flat as ``uint8`` of shape ``(N, 784)``; scaling is a fitting
    step, not a loading step (see :func:`fit_train_artifacts`).
    """
    paths = {
        key: download_and_verify(**source, cache_dir=cache_dir,
                                 allow_download=allow_download)
        for key, source in MNIST_SOURCES.items()
    }
    x_train = _read_idx_images(paths["train_images"])
    y_train = _read_idx_labels(paths["train_labels"])
    x_test = _read_idx_images(paths["test_images"])
    y_test = _read_idx_labels(paths["test_labels"])

    if x_train.shape[0] != MNIST_N_TRAIN or x_test.shape[0] != MNIST_N_TEST:
        raise RuntimeError(
            f"expected the official {MNIST_N_TRAIN}/{MNIST_N_TEST} split, got "
            f"{x_train.shape[0]}/{x_test.shape[0]}"
        )

    labels = tuple(str(d) for d in range(10))
    return Dataset(
        name="mnist",
        x_train=x_train,
        y_train=y_train,
        x_test=x_test,
        y_test=y_test,
        labels=labels,
        metadata={
            "source": {k: v["url"] for k, v in MNIST_SOURCES.items()},
            "sha256": {k: v["sha256"] for k, v in MNIST_SOURCES.items()},
            "official_split": True,
            "shots": None,
        },
    )


def _read_idx_images(path: Path) -> np.ndarray:
    """Read a gzipped IDX3 image file into a flat ``(N, rows*cols)`` array."""
    with gzip.open(path, "rb") as handle:
        magic, count, rows, cols = struct.unpack(">IIII", handle.read(16))
        if magic != 2051:
            raise RuntimeError(f"{path}: bad IDX3 magic {magic}")
        buffer = handle.read(count * rows * cols)
    return np.frombuffer(buffer, dtype=np.uint8).reshape(count, rows * cols)


def _read_idx_labels(path: Path) -> np.ndarray:
    """Read a gzipped IDX1 label file into an ``int64`` array."""
    with gzip.open(path, "rb") as handle:
        magic, count = struct.unpack(">II", handle.read(8))
        if magic != 2049:
            raise RuntimeError(f"{path}: bad IDX1 magic {magic}")
        buffer = handle.read(count)
    return np.frombuffer(buffer, dtype=np.uint8).astype(np.int64)


# ---------------------------------------------------------------------------
# Train-only feature fitting
# ---------------------------------------------------------------------------

def character_trigrams(text: str) -> Iterable[str]:
    """Yield the character trigrams of a string, in order."""
    return (text[i:i + 3] for i in range(len(text) - 2))


def build_trigram_vocabulary(texts: Sequence[str], y: np.ndarray,
                             n_classes: int,
                             size: int = WILI_VOCABULARY_SIZE) -> tuple[str, ...]:
    """Select a per-language balanced trigram vocabulary.

    Implements the procedure registered in ``docs/PREREG_ROBUSTNESS.md``
    §3.2: rank trigrams within each language separately, then fill the
    vocabulary round-robin across languages until exactly ``size`` distinct
    entries are collected.

    The alternative — ranking by pooled frequency — was rejected in advance
    because WiLI-2018 is balanced by paragraph count but not by character
    count (measured: a 9.0× spread between the languages with the fewest and
    most training characters), and because Latin-script trigrams accumulate
    across many languages while a unique script contributes alone. Pooled
    selection can therefore leave a language with no vocabulary entries at
    all, making it unclassifiable before any experiment begins.

    Determinism: languages are visited in class-index order (sorted label
    order), ties within a language break by ``(-count, trigram)``, and the
    ``seen`` set is used only for membership tests, never iterated.
    """
    if len(texts) != len(y):
        raise ValueError(f"got {len(texts)} texts but {len(y)} labels")
    if size <= 0:
        raise ValueError("vocabulary size must be positive")

    ranked_per_class: list[list[str]] = []
    for class_index in range(n_classes):
        counts: Counter[str] = Counter()
        for position in np.flatnonzero(y == class_index):
            counts.update(character_trigrams(texts[position]))
        ranked_per_class.append(
            [trigram for trigram, _ in
             sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
        )

    vocabulary: list[str] = []
    seen: set[str] = set()
    rank = 0
    while len(vocabulary) < size:
        exhausted = True
        for ranked in ranked_per_class:
            if rank >= len(ranked):
                continue
            exhausted = False
            trigram = ranked[rank]
            if trigram not in seen:
                seen.add(trigram)
                vocabulary.append(trigram)
                if len(vocabulary) == size:
                    break
        if exhausted:
            break
        rank += 1
    return tuple(vocabulary)


def document_frequency(texts: Sequence[str],
                       vocabulary: Sequence[str]) -> tuple[int, ...]:
    """Count, per vocabulary entry, how many texts contain it at least once."""
    position_of = {trigram: i for i, trigram in enumerate(vocabulary)}
    counts = np.zeros(len(vocabulary), dtype=np.int64)
    for text in texts:
        present = {position_of[t] for t in set(character_trigrams(text))
                   if t in position_of}
        if present:
            counts[np.fromiter(present, dtype=np.int64, count=len(present))] += 1
    return tuple(int(c) for c in counts)


def fit_train_artifacts(dataset: Dataset,
                        vocabulary_size: int = WILI_VOCABULARY_SIZE
                        ) -> TrainArtifacts:
    """Fit every data-derived artifact, from the training split only.

    This function is the single place where data becomes a fitted
    parameter, which is what makes the no-leakage property testable: refit
    with the test split replaced by anything at all, and the result must be
    identical. ``tests/test_no_leakage.py`` does exactly that.

    It reads ``dataset.x_train`` and ``dataset.y_train`` and nothing else.
    The item memory needs no entry here at all: a symbol's hypervector is
    derived from the symbol and the seed, never from a corpus, so it cannot
    carry information from any split.
    """
    if dataset.name == "mnist" or isinstance(dataset.x_train, np.ndarray):
        train_images = np.asarray(dataset.x_train, dtype=np.float64)
        return TrainArtifacts(
            dataset_name=dataset.name,
            pixel_divisor=MNIST_PIXEL_DIVISOR,
            pixel_mean=train_images.mean(axis=0),
            pixel_std=train_images.std(axis=0),
        )

    texts = tuple(dataset.x_train)
    vocabulary = build_trigram_vocabulary(
        texts, dataset.y_train, dataset.n_classes, size=vocabulary_size)
    return TrainArtifacts(
        dataset_name=dataset.name,
        vocabulary=vocabulary,
        document_frequency=document_frequency(texts, vocabulary),
    )


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def vocabulary_contribution(texts: Sequence[str], y: np.ndarray, n_classes: int,
                            vocabulary: Sequence[str]) -> np.ndarray:
    """How many vocabulary entries each class contributes at least one use of.

    Reported with the robustness results per ``docs/PREREG_ROBUSTNESS.md``
    §3.2, together with the count of classes that a pooled selection would
    have left with nothing — so the cost of the rejected variant is a
    measurement rather than an assertion.
    """
    in_vocabulary = set(vocabulary)
    per_class = np.zeros(n_classes, dtype=np.int64)
    for class_index in range(n_classes):
        used: set[str] = set()
        for position in np.flatnonzero(y == class_index):
            used.update(t for t in character_trigrams(texts[position])
                        if t in in_vocabulary)
        per_class[class_index] = len(used)
    return per_class


def pooled_trigram_vocabulary(texts: Sequence[str],
                              size: int = WILI_VOCABULARY_SIZE) -> tuple[str, ...]:
    """The rejected pooled-frequency vocabulary, kept for the §3.2 diagnostic.

    Not used by any registered pipeline. It exists so that the harm of
    Variant A can be quantified against Variant B rather than assumed.
    """
    counts: Counter[str] = Counter()
    for text in texts:
        counts.update(character_trigrams(text))
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return tuple(trigram for trigram, _ in ranked[:size])


#: Paragraphs appearing identically in both WiLI-2018 splits, measured on
#: the verified archive. This is a property of the published benchmark, not
#: of this code: the official split is used unchanged, as registered, so the
#: overlap is reported rather than removed. Deduplicating would deviate from
#: the official split and make results incomparable to the literature.
WILI_KNOWN_TRAIN_TEST_OVERLAP = 639


def split_overlap(x_train: Sequence[str], x_test: Sequence[str]) -> dict[str, int]:
    """Count exact content overlap between two text splits.

    Identical index-based splits are separate by construction; what this
    measures is whether the same *text* occurs on both sides, which no
    amount of careful indexing prevents and which inflates any test score
    that rewards memorisation.
    """
    def digests(texts: Sequence[str]) -> set[bytes]:
        return {hashlib.blake2b(t.encode("utf-8"), digest_size=16).digest()
                for t in texts}

    train_digests = digests(x_train)
    test_digests = digests(x_test)
    return {
        "overlapping_texts": len(train_digests & test_digests),
        "unique_train": len(train_digests),
        "unique_test": len(test_digests),
        "duplicate_within_train": len(x_train) - len(train_digests),
        "duplicate_within_test": len(x_test) - len(test_digests),
    }


def with_replaced_test_split(dataset: Dataset, x_test: Any,
                             y_test: np.ndarray) -> Dataset:
    """Return a copy of ``dataset`` with a different test split.

    Used by the leakage tests to poison the test data and confirm that
    nothing fitted changes.
    """
    return replace(dataset, x_test=x_test, y_test=y_test)
