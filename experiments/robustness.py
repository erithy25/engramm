"""Bit-corruption robustness study — ``docs/PREREG_ROBUSTNESS.md`` (v1.3).

    python -m experiments.robustness --task mnist --seed 42
    python -m experiments.robustness --task wili  --seed 42
    python -m experiments.robustness_verdict          # after all seeds

One record per (task, seed) in ``results/robustness/``. It holds, for every
system and condition, the test accuracy at every registered corruption level
and the chance-corrected retention R(p) of §6. The verdict over the ten
registered seeds is computed by ``experiments/robustness_verdict.py`` from
these records alone.

Systems (§3, §3.4, §3.3):

* ``engramm``     binary prototypes after T1 + 2 T2 epochs — the primary system
* ``engramm_t1``  the same prototypes before T2 — secondary, descriptive
* ``lr``          logistic regression — control (lower capacity on MNIST)
* ``mlp``         MLP at ENGRAMM's parameter count — control
* ``mlp_bits``    MLP at ENGRAMM's bit budget (§3.3) — secondary

Conditions: ``binary`` (ENGRAMM's own format), ``int8`` (the registered
primary format of the baselines), ``float32`` (secondary, never headline),
``sign`` (the 1-bit format-matched control of §4.1), and the secondary
state condition — ``binary+item_memory`` for ENGRAMM, ``int8+idf`` for the
WiLI baselines (§4, "everything the model needs at inference").

Corruption is applied after training and before evaluation, with no
retraining of any kind; the draw is ``engramm.corruption.corruption_positions``.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
import warnings
from array import array
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse

from data.loaders import (
    CACHE_DIR,
    Dataset,
    TrainArtifacts,
    character_trigrams,
    fit_train_artifacts,
    pooled_trigram_vocabulary,
    vocabulary_contribution,
)
from engramm.core import ItemMemory, permute, unpack_bits
from engramm.corruption import (
    LEVELS_PERCENT,
    SignTensor,
    corrupt,
    dequantize_int8,
    from_buffer,
    quantize_int8,
    retention,
    signs_from_buffer,
    signs_to_buffer,
    to_buffer,
)
from engramm.encoders import Encoder, PixelThermometerEncoder, TrigramEncoder, build_encoder
from engramm.memory import Engramm, FusionConfig
from engramm.repro import (
    collect_environment,
    git_revision,
    is_canonical_environment,
    peak_rss_mb,
    python_files_changed_since,
    set_all_seeds,
)
from experiments.common import content_digest
from experiments.run_benchmark import (
    DEFAULT_TEST_BATCH,
    DEFAULT_TRAIN_BATCH,
    encode_streaming,
    load_task,
    subset,
)

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "results" / "robustness"
FEATURE_CACHE = CACHE_DIR / "robustness"
RECORD_SCHEMA = 1

#: §5, fixed in v1.0.
SEEDS: tuple[int, ...] = (42, 7, 1337, 2026, 99, 3, 123, 512, 8191, 31337)
#: §3.4.
T2_EPOCHS = 2
MLP_HIDDEN = {"mnist": {"mlp": 126, "mlp_bits": 16}, "wili": {"mlp": 230, "mlp_bits": 29}}
MLP_EPOCHS = {"mnist": 30, "wili": 20}
LR_MAX_ITER = 1_000
TASKS = ("mnist", "wili")


# ---------------------------------------------------------------------------
# Sweeps
# ---------------------------------------------------------------------------

Decoder = Callable[[np.ndarray], np.ndarray]


def _json_number(value: float) -> float | None:
    """NaN (R undefined, §6) becomes null — JSON has no NaN."""
    return None if value != value else value


def predictions_digest(predicted: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(predicted, dtype=np.int64).tobytes()).hexdigest()


def sweep(buffer: np.ndarray, n_bits: int, decode: Decoder, y_test: np.ndarray,
          seed: int, chance: float, n_params: int,
          levels: Sequence[int] = LEVELS_PERCENT) -> dict[str, Any]:
    """Corrupt ``buffer`` at every level, decode, score; R(p) per §6."""
    acc: dict[str, float] = {}
    digest = None
    for percent in levels:
        predicted = decode(corrupt(buffer, percent, seed, n_bits))
        acc[str(percent)] = float(np.mean(predicted == y_test))
        if percent == 0:
            digest = predictions_digest(predicted)
    acc0 = acc["0"]
    return {
        "n_params": int(n_params),
        "n_bits": int(n_bits),
        "acc": acc,
        "R": {p: _json_number(retention(a, acc0, chance)) for p, a in acc.items()},
        "predictions_sha256_p0": digest,
    }


# ---------------------------------------------------------------------------
# ENGRAMM
# ---------------------------------------------------------------------------

def _signed(packed: np.ndarray, dimension: int) -> np.ndarray:
    return unpack_bits(packed, dimension).astype(np.float32) * 2.0 - 1.0


def label_order(labels: Sequence[str]) -> np.ndarray:
    """Class indices in label order — :meth:`Engramm.argmax`'s tie-break."""
    return np.array(sorted(range(len(labels)), key=lambda i: labels[i]), dtype=np.int64)


def prototype_predict(queries: np.ndarray, prototypes: np.ndarray, order: np.ndarray,
                      dimension: int, block: int = 4_096) -> np.ndarray:
    """``argmax_c sim(q, P_c)``, ties to the alphabetically first label.

    Computed as a float32 product of ±1 vectors: every partial sum is an
    integer of magnitude ≤ D < 2^24, so the dot products — and hence the
    Hamming distances ``(D − dot) / 2`` — are exact whatever the summation
    order.
    """
    protos = _signed(prototypes, dimension)[order]
    out = np.empty(queries.shape[0], dtype=np.int64)
    for start in range(0, queries.shape[0], block):
        dots = _signed(queries[start:start + block], dimension) @ protos.T
        out[start:start + dots.shape[0]] = order[np.argmax(dots, axis=1)]
    return out


def encoder_tables(encoder: Encoder) -> np.ndarray:
    """The item-memory tables an encoder reads at inference, one row per vector.

    MNIST: 784 position vectors then the level vectors. WiLI: the 256 byte
    vectors (the encoder derives its rotated copies from them).
    """
    im = encoder.item_memory
    if isinstance(encoder, TrigramEncoder):
        return np.stack([im.vector(bytes([b])) for b in range(256)])
    if isinstance(encoder, PixelThermometerEncoder):
        positions = np.stack([im.vector(f"pixel:{j}".encode())
                              for j in range(encoder.n_positions)])
        return np.concatenate([positions, encoder._build_levels()])
    raise TypeError(f"no item-memory tables defined for {type(encoder).__name__}")


def with_tables(encoder: Encoder, tables: np.ndarray) -> Encoder:
    """A copy of ``encoder`` that reads ``tables`` instead of its own."""
    clone = copy.copy(encoder)
    dimension = encoder.dimension
    tables = np.ascontiguousarray(tables, dtype=np.uint8)
    if isinstance(encoder, TrigramEncoder):
        if tables.shape != (256, dimension // 8):
            raise ValueError(f"expected (256, {dimension // 8}) byte vectors")
        clone._tables = (permute(tables, 2, dimension), permute(tables, 1, dimension), tables)
        return clone
    if isinstance(encoder, PixelThermometerEncoder):
        n = encoder.n_positions
        if tables.shape != (n + encoder.n_levels, dimension // 8):
            raise ValueError("table shape does not match the encoder")
        clone._bound = np.bitwise_xor(tables[:n, None, :], tables[None, n:, :])
        return clone
    raise TypeError(f"no item-memory tables defined for {type(encoder).__name__}")


def train_engramm(dataset: Dataset, seed: int, dimension: int,
                  log: Callable[[str], None]) -> dict[str, Any]:
    """T1 then T2 exactly as ``run_benchmark --pipeline prototypes --t2-epochs 2``."""
    encoder = build_encoder(dataset.name, ItemMemory(seed, dimension))
    config = FusionConfig(**{**FusionConfig().to_dict(), "lambda_e": 0.0})
    model = Engramm(dimension, seed, config)
    labels = [dataset.labels[i] for i in dataset.y_train]

    started = time.perf_counter()
    packed = encode_streaming(encoder, dataset.x_train, DEFAULT_TRAIN_BATCH)
    log(f"engramm: train split encoded ({time.perf_counter() - started:.0f}s)")
    positions = model.learn(packed, labels)
    p_t1 = model.prototypes.P.copy()
    errors = model.refine(packed, labels, T2_EPOCHS, rng=np.random.default_rng(seed),
                          episode_positions=positions)
    log(f"engramm: T1 + T2 done, T2 error per epoch {[round(e, 4) for e in errors]}")
    del packed, positions
    train_seconds = time.perf_counter() - started

    started = time.perf_counter()
    test = encode_streaming(encoder, dataset.x_test, DEFAULT_TEST_BATCH)
    test_seconds = time.perf_counter() - started
    log(f"engramm: test split encoded ({test_seconds:.0f}s)")

    # The model's own predictions define the map from its class indices to
    # the dataset's; prototype_predict must reproduce them exactly.
    position = {label: i for i, label in enumerate(dataset.labels)}
    to_dataset = np.array([position[label] for label in model.labels], dtype=np.int64)
    own = to_dataset[model.predict(test)]
    order = label_order(model.labels)
    mine = to_dataset[prototype_predict(test, model.prototypes.P, order, dimension)]
    if not np.array_equal(own, mine):
        raise RuntimeError("prototype_predict disagrees with Engramm.predict at p = 0")
    return {
        "encoder": encoder, "test": test, "P": model.prototypes.P.copy(), "P_t1": p_t1,
        "order": order, "to_dataset": to_dataset, "errors": errors,
        "halvings": int(model.prototypes.halvings),
        "train_seconds": train_seconds, "test_encode_seconds": test_seconds,
        "acc_model_predict": float(np.mean(own == dataset.y_test)),
    }


def engramm_conditions(dataset: Dataset, trained: dict[str, Any], seed: int, chance: float,
                       log: Callable[[str], None]) -> dict[str, dict[str, Any]]:
    dimension = trained["encoder"].dimension
    order, to_dataset, test = trained["order"], trained["to_dataset"], trained["test"]
    y = dataset.y_test

    def prototypes_only(shape: tuple[int, int]) -> Decoder:
        return lambda buf: to_dataset[prototype_predict(test, buf.reshape(shape), order,
                                                        dimension)]

    out: dict[str, dict[str, Any]] = {"engramm": {}, "engramm_t1": {}}
    P = trained["P"]
    n_params = P.shape[0] * dimension
    out["engramm"]["binary"] = sweep(P.ravel(), P.size * 8, prototypes_only(P.shape),
                                     y, seed, chance, n_params)
    out["engramm_t1"]["binary"] = sweep(trained["P_t1"].ravel(), P.size * 8,
                                        prototypes_only(P.shape), y, seed, chance, n_params)
    log(f"engramm: binary R = {out['engramm']['binary']['R']}")

    encoder = trained["encoder"]
    tables = encoder_tables(encoder)
    state = np.concatenate([P.ravel(), tables.ravel()])

    def with_item_memory(buf: np.ndarray) -> np.ndarray:
        protos = buf[:P.size].reshape(P.shape)
        corrupted = buf[P.size:].reshape(tables.shape)
        if np.array_equal(corrupted, tables):
            queries = test
        else:
            queries = encode_streaming(with_tables(encoder, corrupted), dataset.x_test,
                                       DEFAULT_TEST_BATCH)
        return to_dataset[prototype_predict(queries, protos, order, dimension)]

    out["engramm"]["binary+item_memory"] = sweep(
        state, state.size * 8, with_item_memory, y, seed, chance,
        n_params + tables.shape[0] * dimension)
    log(f"engramm: binary+item_memory R = {out['engramm']['binary+item_memory']['R']}")
    return out


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

@dataclass
class Dense:
    """A stack of affine layers with ReLU between them; weights are (in, out)."""

    weights: list[np.ndarray]
    biases: list[np.ndarray]

    @property
    def n_params(self) -> int:
        return int(sum(w.size for w in self.weights) + sum(b.size for b in self.biases))

    def predict(self, x: Any, block: int = 8_192) -> np.ndarray:
        n = x.shape[0]
        out = np.empty(n, dtype=np.int64)
        with np.errstate(all="ignore"):
            for start in range(0, n, block):
                h = x[start:start + block]
                for i, (w, b) in enumerate(zip(self.weights, self.biases)):
                    h = np.asarray(h @ w, dtype=np.float32) + b
                    if i < len(self.weights) - 1:
                        h = np.maximum(h, np.float32(0.0))
                out[start:start + h.shape[0]] = np.argmax(h, axis=1)
        return out


def fit_lr(x: Any, y: np.ndarray, n_classes: int) -> tuple[Dense, dict[str, Any]]:
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression

    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=LR_MAX_ITER, tol=1e-4)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        model.fit(x, y)
    if not np.array_equal(model.classes_, np.arange(n_classes)):
        raise RuntimeError("a class is missing from the training split")
    dense = Dense([model.coef_.T.astype(np.float32)], [model.intercept_.astype(np.float32)])
    return dense, {"n_iter": int(np.max(model.n_iter_)), "max_iter": LR_MAX_ITER,
                   "converged": bool(np.max(model.n_iter_) < LR_MAX_ITER)}


def fit_mlp(x: Any, y: np.ndarray, n_classes: int, hidden: int, epochs: int,
            seed: int) -> tuple[Dense, dict[str, Any]]:
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.neural_network import MLPClassifier

    model = MLPClassifier(hidden_layer_sizes=(hidden,), activation="relu", solver="adam",
                          alpha=1e-4, batch_size=256, learning_rate_init=1e-3,
                          max_iter=epochs, shuffle=True, random_state=seed,
                          early_stopping=False, tol=0.0, n_iter_no_change=epochs + 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        model.fit(x, y)
    if not np.array_equal(model.classes_, np.arange(n_classes)):
        raise RuntimeError("a class is missing from the training split")
    dense = Dense([w.astype(np.float32) for w in model.coefs_],
                  [b.astype(np.float32) for b in model.intercepts_])
    return dense, {"hidden": hidden, "epochs": int(model.n_iter_),
                   "final_training_loss": float(model.loss_)}


def int8_conditions(model: Dense, x_test: Any, y: np.ndarray, seed: int, chance: float,
                    idf: tuple[np.ndarray, Callable[[np.ndarray], Any]] | None = None
                    ) -> dict[str, Any]:
    """Per-tensor int8, every stored bit corruptible; optionally the idf too."""
    tensors = list(model.weights) + list(model.biases)
    if idf is not None:
        tensors.append(idf[0].astype(np.float32))
    quantised = [quantize_int8(t) for t in tensors]
    buffer, layout = to_buffer([q for q, _ in quantised])
    n_layers = len(model.weights)

    def decode(buf: np.ndarray) -> np.ndarray:
        values = [dequantize_int8(a, s) for a, (_, s) in zip(from_buffer(buf, layout), quantised)]
        dense = Dense(values[:n_layers], values[n_layers:2 * n_layers])
        features = x_test if idf is None else idf[1](values[2 * n_layers])
        return dense.predict(features)

    n_params = model.n_params + (idf[0].size if idf is not None else 0)
    return sweep(buffer, buffer.size * 8, decode, y, seed, chance, n_params)


def float32_conditions(model: Dense, x_test: Any, y: np.ndarray, seed: int,
                       chance: float) -> dict[str, Any]:
    buffer, layout = to_buffer([w.astype(np.float32) for w in model.weights]
                               + [b.astype(np.float32) for b in model.biases])
    n_layers = len(model.weights)

    def decode(buf: np.ndarray) -> np.ndarray:
        values = from_buffer(buf, layout)
        return Dense(values[:n_layers], values[n_layers:]).predict(x_test)

    return sweep(buffer, buffer.size * 8, decode, y, seed, chance, model.n_params)


def sign_conditions(model: Dense, x_test: Any, y: np.ndarray, seed: int,
                    chance: float) -> dict[str, Any]:
    """§4.1: sign bits with one exact scale per output unit; biases exact."""
    signs = [SignTensor.from_weights(w) for w in model.weights]
    buffer, n_bits = signs_to_buffer(signs)

    def decode(buf: np.ndarray) -> np.ndarray:
        restored = signs_from_buffer(buf, n_bits, signs)
        return Dense([t.weights() for t in restored], list(model.biases)).predict(x_test)

    result = sweep(buffer, n_bits, decode, y, seed, chance, model.n_params)
    result["n_exact_scales_and_biases"] = int(sum(t.alpha.size for t in signs)
                                              + sum(b.size for b in model.biases))
    return result


# ---------------------------------------------------------------------------
# Features (fitted on the training split only; cached)
# ---------------------------------------------------------------------------

def trigram_counts(texts: Sequence[str], vocabulary: Sequence[str]) -> sparse.csr_matrix:
    """Raw counts of the vocabulary's character trigrams, one row per text."""
    index = {t: i for i, t in enumerate(vocabulary)}
    indptr = array("q", [0])
    indices = array("i")
    data = array("f")
    for text in texts:
        counts = Counter(index[t] for t in character_trigrams(text) if t in index)
        for column in sorted(counts):
            indices.append(column)
            data.append(counts[column])
        indptr.append(len(indices))
    return sparse.csr_matrix((np.frombuffer(data, dtype=np.float32),
                              np.frombuffer(indices, dtype=np.int32),
                              np.frombuffer(indptr, dtype=np.int64)),
                             shape=(len(texts), len(vocabulary)))


def idf_vector(document_frequency: Sequence[int], n_documents: int) -> np.ndarray:
    df = np.asarray(document_frequency, dtype=np.float64)
    return np.log((1.0 + n_documents) / (1.0 + df)) + 1.0


def tfidf(counts: sparse.csr_matrix, idf: np.ndarray) -> sparse.csr_matrix:
    """counts · idf, then L2-normalised per row (all-zero rows stay zero)."""
    weighted = (counts @ sparse.diags(np.asarray(idf, dtype=np.float32))).tocsr()
    weighted.data = weighted.data.astype(np.float32)
    norms = np.sqrt(np.asarray(weighted.multiply(weighted).sum(axis=1)).ravel())
    norms[~np.isfinite(norms) | (norms == 0)] = 1.0
    return (sparse.diags((1.0 / norms).astype(np.float32)) @ weighted).tocsr()


def text_features(dataset: Dataset, log: Callable[[str], None]) -> dict[str, Any]:
    """Vocabulary, df, and train/test count matrices — cached by content digest."""
    key = hashlib.sha256(
        (content_digest(dataset.x_train) + content_digest(dataset.x_test)
         + content_digest(np.asarray(dataset.y_train))).encode()).hexdigest()[:24]
    FEATURE_CACHE.mkdir(parents=True, exist_ok=True)
    meta_path = FEATURE_CACHE / f"{dataset.name}_{key}.json"
    train_path = FEATURE_CACHE / f"{dataset.name}_{key}_train.npz"
    test_path = FEATURE_CACHE / f"{dataset.name}_{key}_test.npz"
    if meta_path.exists() and train_path.exists() and test_path.exists():
        meta = json.loads(meta_path.read_text())
        log(f"features: cache hit {key}")
        return {"key": key, "vocabulary": tuple(meta["vocabulary"]),
                "df": tuple(meta["document_frequency"]),
                "artifacts_digest": meta["artifacts_digest"],
                "train": sparse.load_npz(train_path).tocsr(),
                "test": sparse.load_npz(test_path).tocsr()}
    started = time.perf_counter()
    artifacts: TrainArtifacts = fit_train_artifacts(dataset)
    train = trigram_counts(dataset.x_train, artifacts.vocabulary)
    test = trigram_counts(dataset.x_test, artifacts.vocabulary)
    sparse.save_npz(train_path, train)
    sparse.save_npz(test_path, test)
    meta_path.write_text(json.dumps({"vocabulary": list(artifacts.vocabulary),
                                     "document_frequency": list(artifacts.document_frequency),
                                     "artifacts_digest": artifacts.digest()}))
    log(f"features: built {key} in {time.perf_counter() - started:.0f}s")
    return {"key": key, "vocabulary": artifacts.vocabulary, "df": artifacts.document_frequency,
            "artifacts_digest": artifacts.digest(), "train": train, "test": test}


def cached_lr(task: str, feature_key: str, x: Any, y: np.ndarray, n_classes: int,
              log: Callable[[str], None]) -> tuple[Dense, dict[str, Any]]:
    """LR has no random component, so it is fitted once per task (§3.4)."""
    import sklearn

    tag = hashlib.sha256(f"{task}|{feature_key}|sklearn={sklearn.__version__}|"
                         f"C=1|lbfgs|max_iter={LR_MAX_ITER}|tol=1e-4".encode()).hexdigest()[:24]
    path = FEATURE_CACHE / f"lr_{task}_{tag}.npz"
    FEATURE_CACHE.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stored = np.load(path)
        info = json.loads(str(stored["info"]))
        info.update({"from_cache": True, "cache_tag": tag})
        log("lr: cache hit")
        return Dense([stored["w"]], [stored["b"]]), info
    started = time.perf_counter()
    dense, info = fit_lr(x, y, n_classes)
    info["fit_seconds"] = time.perf_counter() - started
    np.savez(path, w=dense.weights[0], b=dense.biases[0], info=json.dumps(info))
    info.update({"from_cache": False, "cache_tag": tag})
    log(f"lr: fitted in {info['fit_seconds']:.0f}s, {info['n_iter']} iterations")
    return dense, info


def vocabulary_diagnostic(dataset: Dataset, vocabulary: Sequence[str]) -> dict[str, Any]:
    """§3.2: per-language vocabulary contribution under both variants."""
    texts = dataset.x_train
    rows = {}
    for name, vocab in (("B_per_language_balanced", tuple(vocabulary)),
                        ("A_pooled", pooled_trigram_vocabulary(texts))):
        per_class = vocabulary_contribution(texts, dataset.y_train, dataset.n_classes, vocab)
        worst = int(np.argmin(per_class))
        rows[name] = {"languages_with_zero_entries": int(np.sum(per_class == 0)),
                      "min": int(per_class.min()), "median": float(np.median(per_class)),
                      "max": int(per_class.max()), "worst_language": dataset.labels[worst],
                      "per_language": {dataset.labels[i]: int(v)
                                       for i, v in enumerate(per_class)}}
    return rows


# ---------------------------------------------------------------------------
# One (task, seed)
# ---------------------------------------------------------------------------

def run(task: str, seed: int, dimension: int, results_dir: Path,
        limit_train: int | None = None, limit_test: int | None = None,
        allow_download: bool = True) -> Path:
    git_state = git_revision()
    started = time.perf_counter()
    phases: dict[str, float] = {}

    def log(message: str) -> None:
        print(f"[{task} seed {seed} {time.perf_counter() - started:7.0f}s] {message}", flush=True)

    rng = set_all_seeds(seed)
    dataset = subset(load_task(task, None, rng, allow_download), limit_train, limit_test)
    chance = 1.0 / dataset.n_classes
    y = dataset.y_test
    systems: dict[str, dict[str, Any]] = {}

    marker = time.perf_counter()
    trained = train_engramm(dataset, seed, dimension, log)
    systems.update(engramm_conditions(dataset, trained, seed, chance, log))
    phases["engramm"] = time.perf_counter() - marker
    engramm_info = {
        "dimension": dimension, "t2_epochs": T2_EPOCHS, "lambda_e": 0.0,
        "encoder": repr(trained["encoder"]),
        "t2_error_per_epoch": [round(e, 6) for e in trained["errors"]],
        "accumulator_halvings": trained["halvings"],
        "acc_engramm_predict_p0": trained["acc_model_predict"],
        "prototype_predict_matches_engramm_predict": True,
        "train_seconds": trained["train_seconds"],
        "test_encode_seconds": trained["test_encode_seconds"],
    }
    del trained

    marker = time.perf_counter()
    idf_condition = None
    if task == "mnist":
        x_train = np.asarray(dataset.x_train, dtype=np.float32) / np.float32(255.0)
        x_test = np.asarray(dataset.x_test, dtype=np.float32) / np.float32(255.0)
        feature_info = {"inputs": "pixels / 255"}
        feature_key = content_digest(np.asarray(dataset.x_train))[:24]
    else:
        feats = text_features(dataset, log)
        idf = idf_vector(feats["df"], dataset.n_train)
        x_train, x_test = tfidf(feats["train"], idf), tfidf(feats["test"], idf)
        counts_test = feats["test"]
        idf_condition = (idf, lambda corrupted: tfidf(counts_test, corrupted))
        feature_key = feats["key"]
        feature_info = {"inputs": "TF-IDF over the §3.2 vocabulary (Variant B)",
                        "vocabulary_size": len(feats["vocabulary"]),
                        "artifacts_digest": feats["artifacts_digest"],
                        "nnz_train": int(feats["train"].nnz)}
        diagnostic_path = results_dir / "wili_vocabulary_diagnostic.json"
        if limit_train is None and not diagnostic_path.exists():
            results_dir.mkdir(parents=True, exist_ok=True)
            diagnostic_path.write_text(json.dumps(
                vocabulary_diagnostic(dataset, feats["vocabulary"]), indent=2) + "\n")
            log(f"wrote {diagnostic_path}")
    phases["features"] = time.perf_counter() - marker

    baselines: dict[str, Any] = {}
    marker = time.perf_counter()
    lr, baselines["lr"] = cached_lr(task, feature_key, x_train, dataset.y_train,
                                    dataset.n_classes, log)
    baselines["lr"]["trained_once_per_task"] = True
    phases["lr_fit"] = time.perf_counter() - marker

    models: dict[str, Dense] = {"lr": lr}
    for name in ("mlp", "mlp_bits"):
        marker = time.perf_counter()
        models[name], baselines[name] = fit_mlp(x_train, dataset.y_train, dataset.n_classes,
                                                MLP_HIDDEN[task][name], MLP_EPOCHS[task], seed)
        phases[f"{name}_fit"] = time.perf_counter() - marker
        log(f"{name}: fitted in {phases[f'{name}_fit']:.0f}s "
            f"(loss {baselines[name]['final_training_loss']:.4f})")

    marker = time.perf_counter()
    for name, model in models.items():
        systems[name] = {"int8": int8_conditions(model, x_test, y, seed, chance)}
        if name != "mlp_bits":
            systems[name]["float32"] = float32_conditions(model, x_test, y, seed, chance)
            systems[name]["sign"] = sign_conditions(model, x_test, y, seed, chance)
            if idf_condition is not None:
                systems[name]["int8+idf"] = int8_conditions(model, x_test, y, seed, chance,
                                                            idf=idf_condition)
        log(f"{name}: int8 R = {systems[name]['int8']['R']}")
    phases["baseline_sweeps"] = time.perf_counter() - marker

    changed = python_files_changed_since(git_state.get("commit"))
    record = {
        "study": "docs/PREREG_ROBUSTNESS.md v1.3",
        "record_schema": RECORD_SCHEMA,
        "task": task,
        "seed": seed,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {**git_state, "captured": "before_run",
                "code_changed_during_run": bool(changed),
                "changed_python_files": changed},
        "canonical": is_canonical_environment(),
        "official": limit_train is None and limit_test is None,
        "data": {"n_train": dataset.n_train, "n_test": dataset.n_test,
                 "n_classes": dataset.n_classes, "limit_train": limit_train,
                 "limit_test": limit_test},
        "chance": chance,
        "levels_percent": list(LEVELS_PERCENT),
        "engramm": engramm_info,
        "baselines": baselines,
        "features": feature_info,
        "systems": systems,
        "runtime": {"phase_seconds": {k: round(v, 1) for k, v in phases.items()},
                    "wall_seconds": round(time.perf_counter() - started, 1),
                    "peak_rss_mb": peak_rss_mb(),
                    "note": "container figures are not official (docs/PROTOCOL.md)"},
        "environment": collect_environment(),
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"{task}_seed{seed}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    log(f"wrote {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--D", dest="dimension", type=int, default=10_000)
    parser.add_argument("--limit-train", type=int, default=None)
    parser.add_argument("--limit-test", type=int, default=None)
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    parser.add_argument("--no-download", action="store_true")
    args = parser.parse_args(argv)
    if args.seed not in SEEDS and args.limit_train is None:
        raise SystemExit(f"seed {args.seed} is not one of the registered seeds {SEEDS}")
    run(args.task, args.seed, args.dimension, Path(args.results_dir),
        args.limit_train, args.limit_test, allow_download=not args.no_download)
    return 0


if __name__ == "__main__":
    sys.exit(main())
