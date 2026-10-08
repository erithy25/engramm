"""Messart C, reference value: ENGRAMM-LM's test BPB, measured anew from the digest-checked model.

(docs/PREREG_PARAMS.md §6.7.) Assembles the registered final model (main scale,
seed 42, τ index 1, β index 1, mixture fitted on val-A), checks its base digest,
and scores the test split twice:

1. ``HDCLanguageModel.stream_probs`` over the test stream (primary: the model itself);
2. the cached-component path of the E12 evaluation (``lm_mix.fit_and_score``).

Both must agree to 1e-6 BPB and with the E12 record (1.51357693, filtered); otherwise
the script stops (blocker, §9). It also recomputes the near-duplicate filter for the
test split and requires the committed ``results/lm/dedup.json`` list to come out again.

    python -m experiments.params_engramm_eval
"""

from __future__ import annotations

import time

import numpy as np

from engramm.lm.evaluate import bpb, doc_bytes, per_doc_bits
from engramm.lm.suffix import SuffixIndex
from engramm.repro import git_revision
from experiments.lm_final_model import assemble, fitted_mixture
from experiments.lm_mix import SYSTEMS, dedup_keep, fit_and_score, load
from experiments.lm_suffix import DEDUP_THRESHOLD, DEDUP_WIDTH
from experiments.params_common import ENGRAMM_LM, write_record

TOL = 1e-6


def main() -> None:
    git_state, t0 = git_revision(), time.time()
    e = ENGRAMM_LM
    spec = fitted_mixture(e["scale"], e["seed"], e["tau_index"], e["beta_index"])
    model = assemble(e["scale"], e["seed"], spec)
    digest = model.base_digest()
    if digest != e["base_digest"]:
        raise SystemExit(f"BLOCKER: base digest {digest} differs from the registered {e['base_digest']}")
    print("digest ok", digest, flush=True)

    c = load(e["scale"], ("val_a", "test"), e["seed"])
    test = c["test"].split
    keep = dedup_keep("test", test.n_docs)
    nb = doc_bytes(test)

    ends = np.array([test.doc_end(i) for i in range(test.n_docs)], dtype=np.int64)
    tot, hit = SuffixIndex(np.asarray(model.tokens), model.index.sa).overlap(
        np.asarray(test.tokens), test.doc_starts, ends, DEDUP_WIDTH)
    frac = np.where(tot > 0, hit / np.maximum(tot, 1), 0.0)
    recomputed = frac < DEDUP_THRESHOLD
    if not np.array_equal(recomputed, keep):
        raise SystemExit("BLOCKER: the near-duplicate filter does not reproduce results/lm/dedup.json")
    print("filter ok:", int(keep.sum()), "of", test.n_docs, flush=True)

    t1 = time.time()
    p = model.stream_probs(np.asarray(test.tokens))
    stream_s = time.time() - t1
    bits_stream = per_doc_bits(test, p)
    _, _, o = fit_and_score(SYSTEMS["engramm"], c["val_a"], {"test": c["test"]}, e["tau_index"], e["beta_index"])
    bits_cached = o["test"]
    secondary = {}
    for name in ("kn5", "null"):                       # §6.10: secondary targets of the fit
        _, _, o2 = fit_and_score(SYSTEMS[name], c["val_a"], {"test": c["test"]}, e["tau_index"], e["beta_index"])
        secondary[name] = o2["test"]

    v_stream = bpb(bits_stream, nb, mask=keep)
    v_cached = bpb(bits_cached, nb, mask=keep)
    checks = {"stream_vs_cached": abs(v_stream.value - v_cached.value),
              "stream_vs_e12": abs(v_stream.value - e["test_bpb_e12"])}
    print({"stream": v_stream.as_dict(), "cached": v_cached.as_dict(), **checks}, flush=True)
    if max(checks.values()) > TOL:
        raise SystemExit(f"BLOCKER: test BPB disagrees beyond {TOL}: {checks}")

    out = {"subject": {**e, "base_digest_checked": digest},
           "filter": {"width": DEDUP_WIDTH, "threshold": DEDUP_THRESHOLD, "kept": int(keep.sum()),
                      "docs": int(test.n_docs), "reproduced": True},
           "test_bpb_filtered": v_stream.as_dict(), "test_bpb_unfiltered": bpb(bits_stream, nb).as_dict(),
           "cached_path_bpb_filtered": v_cached.as_dict(), "checks": checks,
           "secondary_bpb_filtered": {k: bpb(v, nb, mask=keep).as_dict() for k, v in secondary.items()},
           "secondary_per_doc_bits": {k: v.tolist() for k, v in secondary.items()},
           "stream_eval_seconds_container": stream_s,
           "per_doc_bits": bits_stream.tolist(), "doc_bytes": nb.tolist(), "keep": keep.tolist(),
           "keys": [list(k) for k in test.doc_keys]}
    print(write_record("c_engramm_test", out, t0, git_state), flush=True)


if __name__ == "__main__":
    main()
