"""Messart A for ENGRAMM-LM: every stored value of the saved model, per component.

(docs/PREREG_PARAMS.md §4.) Reads the model directory written by
``python -m experiments.lm_final_model --scale main --seed 42 --tau-index 1 --beta-index 1 --save``,
checks the base digest against the registered one, and counts:

* (L) learned values — KN-5 tables, codebook, mixture weights, KNN distance edges, τ, β;
* (I) corpus-bound indices — suffix array, KNN position index, segment signatures (not parameters);
* (T) raw text — token stream and document bookkeeping (not parameters);
* (D) arrays derived at load time from (L) — reported, not added;
* (Z) run-time state — document cache, topic vector (nothing stored in the base model).

    python -m experiments.params_count_lm [--model models/lm/main/model]

Bytes in RAM are Σ ``nbytes`` of the loaded arrays (computed, platform-independent); the
peak RSS of the process is recorded as container context only (PROTOCOL rule 2).
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from engramm.lm import knn as K
from engramm.lm.model import HDCLanguageModel
from engramm.lm.semantic import D_S, MIN_COUNT
from engramm.lm.topic import topic_table
from engramm.repro import git_revision
from experiments.lm_common import MODELS_DIR
from experiments.params_common import ENGRAMM_LM, RESULTS, WORK, array_row, write_record

KN_ARRAYS = ("ctx", "ptr", "total", "n1", "n2", "n3", "w", "a", "coc")
KN_STRUCTURE = ("ctx", "ptr", "w")          # keys and pointers; the rest are counts


def _size(path: Path) -> int:
    return path.stat().st_size


def kn_rows(model: HDCLanguageModel, d: Path) -> dict:
    kn = model.kn
    orders, arpa = {}, {}
    for n in range(1, kn.order + 1):
        t = kn.tables[n]
        arrays = {}
        for name in KN_ARRAYS:
            arrays[name] = array_row(getattr(t, name), _size(d / f"{name}_{n}.npy"))
        arrays["pruned"] = array_row(np.array([t.pruned]), _size(d / f"pruned_{n}.npy"))
        stat = {k: v for k, v in arrays.items() if k not in KN_STRUCTURE}
        struct = {k: v for k, v in arrays.items() if k in KN_STRUCTURE}
        orders[n] = {"ngrams": int(len(t.w)), "contexts": int(len(t.ctx)), "pruned": bool(t.pruned),
                     "arrays": arrays,
                     "values": sum(r["values"] for r in arrays.values()),
                     "values_counts": sum(r["values"] for r in stat.values()),
                     "values_keys_pointers": sum(r["values"] for r in struct.values()),
                     "disk_bytes": sum(r["disk_bytes"] for r in arrays.values()),
                     "ram_bytes": sum(r["ram_bytes"] for r in arrays.values())}
    for n in range(1, kn.order + 1):
        # ARPA convention: one probability per kept n-gram, one back-off weight per n-gram that is
        # the context of a higher order (here: every stored context of order n + 1).
        backoff = orders[n + 1]["contexts"] if n + 1 in orders else 0
        arpa[n] = {"probabilities": orders[n]["ngrams"], "backoff_weights": backoff,
                   "values": orders[n]["ngrams"] + backoff}
    meta = array_row(np.array([kn.order, kn.vocab_size], dtype=np.int64), _size(d / "meta.npy"))
    total = {"values": sum(o["values"] for o in orders.values()) + meta["values"],
             "values_counts": sum(o["values_counts"] for o in orders.values()),
             "values_keys_pointers": sum(o["values_keys_pointers"] for o in orders.values()),
             "disk_bytes": sum(o["disk_bytes"] for o in orders.values()) + meta["disk_bytes"],
             "ram_bytes": sum(o["ram_bytes"] for o in orders.values()) + meta["ram_bytes"]}
    arpa_total = {"values": sum(r["values"] for r in arpa.values()),
                  "bits_per_value": 32, "bytes_fp32": 4 * sum(r["values"] for r in arpa.values()),
                  "note": "equivalent count in ARPA/KenLM convention; the model stores counts, not these values"}
    return {"orders": orders, "meta": meta, **total, "arpa_equivalent": {"orders": arpa, **arpa_total}}


def codebook_rows(model: HDCLanguageModel, d: Path) -> dict:
    cb = model.cb
    arrays = {"eng": array_row(cb.eng, bit_vector=True), "wide": array_row(cb.wide, bit_vector=True),
              "idf": array_row(cb.idf), "classes": array_row(cb.classes), "counts": array_row(cb.counts),
              "ctx_tokens": array_row(cb.ctx_tokens), "seed": array_row(np.array([cb.seed], dtype=np.int64))}
    rare = int(np.count_nonzero(cb.counts < MIN_COUNT))
    return {"arrays": arrays, "vocab": int(len(cb.counts)), "bits_per_vector": D_S,
            "hdc_word_vector_bits": arrays["eng"]["values"] + arrays["wide"]["values"],
            "tokens_with_random_vectors": rare,
            "random_vector_bits": 2 * rare * D_S,
            "note_random": f"tokens seen < {MIN_COUNT} times get seeded random vectors (stored, not learned)",
            "values": sum(r["values"] for r in arrays.values()),
            "disk_bytes": _size(d / "codebook.npz"),
            "ram_bytes": sum(r["ram_bytes"] for r in arrays.values())}


def mixture_rows(model: HDCLanguageModel, d: Path) -> dict:
    m = model.mix
    arrays = {"weights": array_row(m.weights), "knn_edges": array_row(np.asarray(m.knn_edges)),
              "tau_beta": array_row(np.array([m.tau, m.beta]))}
    w = np.asarray(m.weights)
    return {"arrays": arrays, "components": list(m.components), "buckets": int(w.shape[0]),
            "weights_on_2^-24_grid": bool(np.all(np.round(w * 2**24) == w * 2**24)),
            "values": sum(r["values"] for r in arrays.values()),
            "disk_bytes": _size(d / "mixture.json") + _size(d / "meta.json"),
            "ram_bytes": sum(r["ram_bytes"] for r in arrays.values())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=MODELS_DIR / "main" / "model")
    ap.add_argument("--smoke", action="store_true", help="code test on another model: no digest check, scratch output")
    args = ap.parse_args()
    git_state, t0 = git_revision(), time.time()
    d = args.model
    model = HDCLanguageModel.load(d)
    digest = model.base_digest()
    if digest != ENGRAMM_LM["base_digest"] and not args.smoke:
        raise SystemExit(f"base digest {digest} differs from the registered {ENGRAMM_LM['base_digest']}")

    learned = {"kn5": kn_rows(model, d / "kn5"), "codebook": codebook_rows(model, d),
               "mixture": mixture_rows(model, d),
               "topic_vector": {"values": 0, "note": "computed per history from codebook.wide/idf; nothing stored"},
               "document_cache": {"values": 0, "note": "per-document token counts at run time; nothing stored"},
               "perceptron": {"values": 0, "note": "ENGRAMM-LM has no perceptron"}}
    corpus_bound = {
        "suffix_array": array_row(model.index.sa, _size(d / "sa.npy")),
        "knn_position_index": array_row(model.pos, _size(d / "knn_pos.npy")),
        "segment_signatures": array_row(model.segsig, _size(d / "segsig.npy"), bit_vector=True),
    }
    raw_text = {
        "train_tokens": array_row(np.asarray(model.train.tokens), _size(d / "train.u16")),
        "doc_starts": array_row(np.asarray(model.train.doc_starts), _size(d / "train.starts.npy")),
        "doc_bytes": array_row(np.asarray(model.train.doc_bytes), _size(d / "train.bytes.npy")),
        "doc_keys": {"values": 2 * model.train.n_docs, "disk_bytes": _size(d / "train.keys.jsonl"),
                     "note": "(source, key) strings per document"},
    }
    derived = {"kn_discounts": array_row(model.kn.disc), "kn_g1": array_row(model.kn.g1),
               "kn_p_uni": array_row(model.kn.p_uni), "knn_kernel_table": array_row(model.knn_table),
               "topic_table": array_row(topic_table(model.mix.beta))}
    runtime = {"topic_vector_bits": D_S, "knn_signature_bits": K.SIG_WORDS * 64,
               "document_cache": "one count per distinct token of the current document",
               "user_layer": "empty in the base model; grows with learn_text"}

    lv = ["kn5", "codebook", "mixture"]
    a_l = {"values": sum(learned[k]["values"] for k in lv),
           "disk_bytes": sum(learned[k]["disk_bytes"] for k in lv),
           "ram_bytes": sum(learned[k]["ram_bytes"] for k in lv)}
    i_keys = ("knn_position_index", "segment_signatures")
    a_li = {"values": a_l["values"] + sum(corpus_bound[k]["values"] for k in i_keys),
            "disk_bytes": a_l["disk_bytes"] + sum(corpus_bound[k]["disk_bytes"] for k in i_keys),
            "ram_bytes": a_l["ram_bytes"] + sum(corpus_bound[k]["ram_bytes"] for k in i_keys)}
    summary = {
        "A_learned": a_l,
        "A_learned_plus_knn_index": a_li,
        "storage_equivalent_fp16": a_l["disk_bytes"] / 2, "storage_equivalent_fp32": a_l["disk_bytes"] / 4,
        "storage_equivalent_fp16_plus_knn_index": a_li["disk_bytes"] / 2,
        "storage_equivalent_fp32_plus_knn_index": a_li["disk_bytes"] / 4,
        "not_parameters": {"suffix_array_and_raw_text_disk_bytes":
                           corpus_bound["suffix_array"]["disk_bytes"]
                           + sum(r["disk_bytes"] for r in raw_text.values())},
        "wording": "stored values, not parameters (docs/PREREG_PARAMS.md §1)",
    }
    out = {"subject": {**ENGRAMM_LM, "model_dir": str(d), "base_digest_checked": digest},
           "learned": learned, "corpus_bound_indices": corpus_bound, "raw_text": raw_text,
           "derived_at_load": derived, "runtime_state": runtime, "summary": summary}
    for k in lv:
        print(f"{k:10s} values {learned[k]['values']:>14,d}  disk {learned[k]['disk_bytes']:>14,d} B", flush=True)
    print("A_learned", a_l, flush=True)
    print(write_record("a_engramm_lm", out, t0, git_state,
                                                    WORK / "smoke" if args.smoke else RESULTS), flush=True)


if __name__ == "__main__":
    main()
