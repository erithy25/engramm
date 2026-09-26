<div align="center">

# ENGRAMM

**Hyperdimensional computing research with a simple rule: preregister every claim, then measure it.**

*Now also a language model that writes English by reading and counting — no neural network, no borrowed model, CPU only.*

<img src="https://img.shields.io/badge/approach-Vector%20Symbolic%20Architectures-blue?style=flat-square" alt="Vector Symbolic Architectures" />
<img src="https://img.shields.io/badge/stack-Python%20%2B%20NumPy-green?style=flat-square" alt="Python and NumPy" />
<img src="https://img.shields.io/badge/status-rebuilt%20%26%20re--measured-yellow?style=flat-square" alt="Rebuilt and re-measured" />

</div>

---

## Status

**The original implementation of this project was lost; it has been rebuilt
from the preserved design documents, and every milestone has been re-run.**
The numbers in this README are those re-measurements. None of the lost
code's numbers are used as evidence any more.

What happened: the source code was developed locally but never fully committed
to version control. When the working tree was lost, the only surviving artifact
was a set of Claude Code edit-tool logs, from which the code was partially
reconstructed (commit `a1af719`). The recovered fragments are preserved in
[`legacy/`](legacy/), the edit logs in
[`docs/archive/edit-logs/`](docs/archive/edit-logs/), and a full forensic
account in [`docs/AUDIT_2026-08.md`](docs/AUDIT_2026-08.md).

The rebuild (`engramm/`, `experiments/`, `data/`) reimplements the core, the
episodic layer, score fusion, error-driven refinement (T2), consolidation and
eviction (T3) and the append-only event log (L2), plus the harness for every
milestone. Every run was registered in [`docs/EXPECTATIONS.md`](docs/EXPECTATIONS.md)
before it ran; deviations from the record are in [`docs/DEVIATIONS.md`](docs/DEVIATIONS.md).

**Two limits apply to every number below, by the project's own protocol**
([`docs/PROTOCOL.md`](docs/PROTOCOL.md)):

- All figures were measured in a Linux container (`canonical: false` in every
  record). Accuracy figures there are *candidates* until confirmed
  bit-identically on the reference machine (Apple M4). That confirmation is
  still outstanding.
- Wall time, memory and energy from the container are never official. The
  container has no power interface, so **no energy figure was measured**;
  the harness now contains a meter (RAPL / `powermetrics`) for the reference
  machine.

## ENGRAMM-LM — a language model built by counting

ENGRAMM-LM reads 285 M tokens of general English (one C4 web shard and
WikiText-103), counts what follows what and which words appear in similar
places, and writes new text word by word from those counts. It uses no
gradients, no neural network and no pretrained model. It rebuilds from scratch
in about 9 minutes on a MacBook Air M4 (544 s, measured).

What it can do:

| Capability | Command | Measured (container unless marked M4) |
|---|---|---|
| **Write** English continuations | `python -m engramm.lm write "The history of the city"` | M4: 118.9 tokens/s including sources, 6.2 GB peak (container: 109–128 tokens/s) |
| **Cite** the source of every written token: the longest verbatim match and the most similar contexts | `… write … --explain` or `python -m engramm.lm why "<prompt>" "<word>"` | 117 tokens/s with sources |
| **Learn** a new text instantly | `python -m engramm.lm learn --source notes --file notes.txt` | 56 ms per 1,000 tokens |
| **Forget** a text exactly | `python -m engramm.lm forget notes` | state digest and a canary's log-probability are **bit-identical** to never having learnt it; 37 ms per 1,000 tokens |
| Replay every change from an append-only log | automatic (`user.log` next to the model) | replay reproduces the state digest |

How it works: five components are mixed per token, with weights fitted per
situation on held-out data.

| Component | What it contributes |
|---|---|
| KN-5 — modified Kneser-Ney 5-grams | grammatical local continuations; matches KenLM to 1.4·10⁻⁶ |
| ∞-gram — suffix array over the whole corpus | long verbatim phrases, and the source of every word |
| Document cache | the words of the current text (used for prediction; off while writing) |
| **HDC similarity memory** — 2,048-bit word vectors learnt from co-occurrence counts | contexts that *mean* the same ("on Monday" ≈ "on Friday") |
| **HDC topic vector** | the topic of the last 256 words |

The meaning vectors are learnt from counts alone, and they behave the way one
would hope: the nearest neighbours of *Monday* are the other weekdays, those
of *France* other countries, those of *three* other numbers.

### Results (test split, preregistered in [`docs/PREREG_LM.md`](docs/PREREG_LM.md) and [`docs/PREREG_LM_V2.md`](docs/PREREG_LM_V2.md))

| System | bits per byte (lower is better) |
|---|---|
| KN-5 (classic counting baseline) | 1.605 |
| Exact null model: KN-5 + ∞-gram + cache, no HDC | 1.525 |
| **ENGRAMM-LM** | **1.514** |
| Small Transformer, 23 M parameters, 6 h CPU training | 1.638 |
| GPT-2 small (reference only: 124 M parameters, 40 GB of text) | 1.039 |

| Registered criterion | Result |
|---|---|
| HDC improves prediction by ≥ 2 % over the exact null model (core claim) | **refuted**: 0.74 %, CI [0.69, 0.79] %. The pilot kill gate (≥ 1 %) had already fired at 0.45 % |
| ≤ 0.90 × KN-5 | missed: 0.943 |
| Recall of rephrased facts beats KN-5 with the same learning | missed: 25.8 % vs. 26.5 % top-10 |
| Forgetting is exact, ≤ 100 ms per 1,000 tokens | **met** |
| A blind LLM judge prefers its texts over KN-5 (registered decoding, cache on) | missed: 19.8 % (a human panel is prepared, not run) |
| Same, in the writing mode (cache off, top-p 0.8), registered separately on 200 fresh prompts | **met: 65.5 %** of 400 blind judgments |
| Writing mode vs. the null model: does HDC make texts better? | no: 52.5 % |
| ≥ 25 tokens/s, ≤ 10 GB, build ≤ 12 h on the MacBook Air M4 | **met on the M4**: 118.9 tokens/s with sources, 6.2 GB peak, 544 s build |

**What this means, plainly.** ENGRAMM-LM writes locally fluent English that a
blind judge prefers to a classic n-gram model. The texts stay on topic within a
paragraph but have no overall meaning; GPT-2 is far ahead. Almost all of the
gain over KN-5 comes from the exact parts. In prediction the document cache
contributes 3.5 % and the ∞-gram 1.5 %. In writing, the ∞-gram's continuations
reuse longer verbatim stretches, capped at 32 tokens. The HDC
part helps measurably and consistently across seeds, but only by 0.7 %. That
is too little for the registered claim, so the claim is recorded as refuted.

What *is* new is the combination of properties. It is a language model that
learns a text in milliseconds, forgets it bit-exactly on request, names the
source of every word it writes, and is deterministic across runs. Every
number, deviation and verdict is in [`docs/EXPECTATIONS.md`](docs/EXPECTATIONS.md)
(E12, E13) and [`docs/DEVIATIONS.md`](docs/DEVIATIONS.md) (CHANGED-9); the
component specification is in [`docs/SPEC_LM.md`](docs/SPEC_LM.md).

## Results — rebuild, re-measured

| Milestone | Task | Historical record | Rebuild (container, `canonical: false`) | Registered criterion |
|-----------|------|-------------------|------------------------------------------|----------------------|
| M1 | WiLI-2018 language ID, **10-shot**, 235 classes | 79.30 % ± 0.68 | **77.94 % ± 0.49** with the historical architecture (E10); **84.79 % ± 0.37** with the validation-chosen configuration, prototypes only (E1) | replication band ±3 pp: **met** (both) |
| M1b | MNIST, official 60k/10k split | 94.59 % ± 0.04 (5 seeds) | **94.79 % ± 0.09** (5 seeds, full pipeline; seed 42 = 94.88 %) | ≥ 94 %: **met**; time < 30 min: not assessable in the container |
| M0 | HNSW recall@32 on 10⁶ real WiLI keys | 95.57 % at ef = 128; 27.4 mJ/query | registered build (efConstruction 40): 91.95 % at ef = 128, 94.71 % at ef = 256 — **not met**. With efConstruction 320 (E5b): **95.95 % at ef = 128** (92.73 / 95.95 / 97.61 % at ef 64 / 128 / 256). Energy: not measured | ≥ 95 % at some ef ≤ 256: **not met** as registered, **met** with a better-built index |
| M2a | Consolidation by similarity absorption | **failed**: −53 pp | **failed**, reproduced: 5.8× compression at **−35.6 ± 0.7 pp** (3 seeds) | compression ≥ 5× ∧ Δacc ≥ −1 pp: **not met** (as predicted) |
| M2b | Utility-based eviction + L2 persistence gate | crash replay passed | **gate passed on 3/3 seeds**: full replay, 10/10 checkpoints and a crash replay at a 60 % byte cut reproduce state and all predictions exactly; eviction to 80 % costs −5.69 ± 0.26 pp | persistence gate: **met** |
| M3 | 1,000 authors, strictly sequential | 5.94 % top-1; state invariant, read-out **not** (W19) | top-1 **15.46 % ± 0.74**, top-5 27.78 %, forgetting +18.8 pp (3 seeds); **state and read-out invariance hold on 3/3 seeds** (0 differences); reconstruction from the log exact | forgetting ≤ 1 pp, top-1 ≥ 30 %: **not met** (as predicted) |
| M5 | Intent classification vs. local LLM baselines (Banking77 / CLINC150, 10-shot) | hypothesis failed: ENGRAMM 62.6 / 69.0 %, 20.4 / 22.0 pp behind LLM+RAG | ENGRAMM **65.39 % ± 1.26 / 72.80 % ± 0.32** (5 seeds); embedding kNN without an LLM (B0) 83.92 / 86.57 %; LoRA in tranches (B3) 14.7 / 34.4 % with +66 / +76 pp forgetting; LLM+RAG (B1, CPU) **80.52 / 90.38 %** — ENGRAMM **16.8 / 17.4 pp behind**; learning 634–680× faster than B3, no interference | **(3) defeat on both tasks** (accuracy gap > 15 pp; energy not measured, not needed for the decision) |
| Phase 4 | Bit-corruption robustness vs. equal-size baselines (MNIST, WiLI; 10 seeds) | — (new) | chance-corrected retention at 5 / 10 / 25 % flipped bits: ENGRAMM **0.94 / 0.85 / 0.55** (MNIST), **0.99 / 0.99 / 0.95** (WiLI); int8 MLP 0.38 / 0.14 / 0.03 and 0.50 / 0.13 / 0.01. Against the 1-bit format control: advantage holds on WiLI, **not** on MNIST (1-bit LR 0.88 / 0.73 / 0.45) | [`docs/PREREG_ROBUSTNESS.md`](docs/PREREG_ROBUSTNESS.md) v1.3: **confirmed** (§7) on both tasks; §4.1: attributable to number format on MNIST, representation advantage shown on WiLI |
| Phase 5 | ENGRAMM-LM: English language model built only by counting (285 M tokens) | — (new) | test bits/byte **1.514** vs. KN-5 1.605 and exact null model 1.525; forgetting bit-exact; writing mode preferred over KN-5 in 65.5 % | [`docs/PREREG_LM.md`](docs/PREREG_LM.md): core claim **refuted** (HDC adds 0.7 %, ≥ 2 % required); [`docs/PREREG_LM_V2.md`](docs/PREREG_LM_V2.md): writing mode **met** — see the section above |

Per-seed values, the registered expectations and every verdict are in
[`docs/EXPECTATIONS.md`](docs/EXPECTATIONS.md) (E1–E13); the records are in
[`results/`](results/).

What the rebuild adds beyond the historical record:

- **The MNIST gap is explained.** Prototypes alone give 80.07 %; the historical
  prototype figure (86.49 %) was measured *with* two T2 epochs, and T2 closes
  the gap: 85.47 % ± 0.15 (E3, within the registered ±1.5 pp band).
- **The episodic layer is task-dependent.** It lifts MNIST from 85.47 % to
  94.79 %, but lowers WiLI 10-shot from 84.79 % to 77.94 % — the "episode
  paradox" recorded historically, now measured on the test split.
- **The M0 miss is a build parameter, not a collapse.** The historical
  efConstruction was not recorded; at 320 the historical recall curve is
  reproduced to within 0.3–0.7 pp.
- **Read-out invariance in M3 now holds** — the order-dependent tie-break of
  the historical code (W19) was replaced by a content-identity tie-break.
- **A cheap baseline was missing.** Embedding kNN (bge-small, no LLM) beats
  ENGRAMM by 14–19 pp on the M5 tasks. Whatever efficiency niche ENGRAMM has,
  it has to be argued against that, not against a 3B LLM.

## Reproducibility

- **Determinism.** Re-running registered records from the committed tree gives
  bit-identical predictions (`results/repro/verification.json`).
- **Independent reproduction, as this project defines it** (see Method): a
  separate agent session implemented the system from
  [`docs/SPEC_REBUILD.md`](docs/SPEC_REBUILD.md) alone — without access to the
  implementation, the records or any cache — and reproduced WiLI 10-shot,
  MNIST T1, MNIST T1 + T2 and the full MNIST pipeline **bit for bit**
  (185/185 conformance checks; [`reproduction/`](reproduction/),
  `results/repro/independent_verification.json`). This shows that the
  specification is complete and the results deterministic on this platform. It
  is not third-party replication on different hardware.

## Historical record and its qualifications

The historical figures above come from the lost implementation's design
documents (MacBook Air M4, July 2026; the M5 LLM baseline ran on the Metal
GPU). Three qualifications that earlier versions of this README stated too
loosely:

- **The WiLI number is a few-shot result.** 79.30 % was measured with 10
  training examples per language across all 235 languages (chance 0.4 %), not
  on the full training split. On the full split the rebuild's prototypes reach
  89.79 % ± 0.03.
- **The MNIST time criterion was not met under its original reading.** The
  preregistered criterion was accuracy ≥ 94 % **and** learning time < 30 min
  CPU, enforced as *max over seeds*. The historical 5-seed run measured mean
  28.1 ± 2.4 min, max 31.8 min — a fail under the max rule; the rule was then
  changed to the mean (disclosed as outcome-relevant). The rebuild cannot
  settle this: container times are not official.
- **The historical M3 invariance applied to the learned state, not to
  outputs** (0.03 pp read-out difference, W19). In the rebuild both hold.

## Roadmap

The rebuild is also a re-scoping. The research questions:

> **How robust are HDC classifiers to bit corruption of the learned state,
> compared to baselines with the same parameter count?** (Phase 4)
>
> **Can a model that only reads and counts write English — and does HDC add
> anything to exact counting?** (Phase 5)

1. **Infrastructure** — *done.* Pinned dependencies (`requirements.lock`,
   `requirements-baselines.lock`), checksummed data and model downloads
   (`data/`, `experiments/fetch_models.py`), seeds for every randomness source,
   one command per benchmark and one for all (`experiments/reproduce_all.sh`),
   machine-readable records in `results/` with commit, provenance and
   environment.
2. **Core reimplementation** — *done*, from `docs/D2_SPEC.md` and
   `docs/D4_PROTOTYP.md`: item memory, encoders, T1, T2, episodic memory with
   exact top-k, score fusion, T3, the L2 event log with exact and crash replay.
3. **Re-run of the historical benchmarks** — *done*, 5 seeds each (table above).
4. **Bit-corruption study** — *done*: preregistered
   ([`docs/PREREG_ROBUSTNESS.md`](docs/PREREG_ROBUSTNESS.md), v1.3 adds a
   1-bit format-matched control, because an int8 baseline can lose by its
   number format alone), corruption code validated before the first run
   (`tests/test_corruption.py`), 2 tasks × 10 seeds
   (`experiments/robustness_all.sh`). Outcome: **confirmed** under the
   registered rules — binary HDC prototypes keep far more of their accuracy
   than int8 baselines of equal parameter count on both tasks. The format
   control qualifies it: on MNIST a sign-binarised logistic regression degrades
   almost as gracefully, so there the advantage is the number format's; on
   WiLI it survives the format control (`results/robustness/SUMMARY.md`).

5. **ENGRAMM-LM — writing English by reading and counting** — *done*, see
   [the section above](#engramm-lm--a-language-model-built-by-counting). Core
   claim (HDC adds ≥ 2 %) **refuted**; exact forgetting and the writing mode
   **met**.

Still open, all on the reference machine or with people:

- confirming the accuracy figures bit-identically on the M4, and measuring energy there;
- the human reading panel, with 3 readers × 60 pairs. The form is
  [`results/lm/p6_panel_form.md`](results/lm/p6_panel_form.md).

## Method

Unchanged, and the reason this README looks the way it does:

1. Register the success criterion before running the experiment.
2. Run across multiple seeds on fixed hardware.
3. Reproduce independently before a result counts.

   > Independent reproduction, as used in this project: a separate agent
   > session re-derives the harness from the specification and re-runs the
   > benchmark without access to the original implementation, on the same
   > hardware. This verifies determinism and specification completeness. It
   > does not constitute independent replication by a third party on
   > different hardware, and is not claimed as such.

4. Document failures with the same rigor as successes.

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
.venv/bin/python -m pytest                                  # test suite
.venv/bin/python -m experiments.run_benchmark --task wili --shots 10 --seeds 5
bash experiments/reproduce_all.sh                           # every registered milestone run
bash experiments/robustness_all.sh                          # the bit-corruption study

# ENGRAMM-LM: data → components → mixtures → one test evaluation → verdict
.venv/bin/python -m experiments.lm_prepare                  # corpus (checksummed), pinned tokenizer, token streams
.venv/bin/python -m experiments.lm_suffix --scale main      # suffix array + near-duplicate filter
for s in pilot main; do                                     # lm_eval reports both scales
  .venv/bin/python -m experiments.lm_components --scale $s --splits val_a,val_b,test,wt103_test \
      --parts kn,inf,cache,knn,topic --seed 42
done
.venv/bin/python -m experiments.lm_eval && .venv/bin/python -m experiments.lm_verdict
.venv/bin/python -m experiments.lm_final_model --scale main --tau-index 1 --beta-index 1 --save
.venv/bin/python -m engramm.lm write "The history of the city" --explain
.venv/bin/python -m experiments.lm_p5 --scale main          # device criterion (official only on the M4)

# M5 baselines run in their own environment:
python3.12 -m venv .venv_b1
.venv_b1/bin/pip install -r requirements-baselines.lock --extra-index-url https://download.pytorch.org/whl/cpu
.venv_b1/bin/python -m experiments.fetch_models
```

## Repository layout

```
engramm/                 the rebuilt core: item memory, encoders, prototypes, episodic
                         memory and fusion, T2/T3, L2 event log, determinism helpers
engramm/lm/              ENGRAMM-LM: tokenizer, KN-5, suffix array, meaning vectors, KNN,
                         topic, mixture, learn/forget/why, sampler, CLI (python -m engramm.lm)
data/                    checksummed loaders (WiLI-2018, MNIST, Banking77, CLINC150,
                         Blog Authorship Corpus, C4 + WikiText-103 for the LM); train-only
                         feature fitting; the pinned LM tokenizer and the invented facts
experiments/             one harness per milestone, the robustness study, the LM pipeline
                         (lm_*.py), referees, reproduce_all.sh, fetch_models.py, energy meter
tests/                   determinism, leakage, core, memory, corruption, referee and LM tests
                         (KN-5 vs. an independent reference, suffix array vs. brute force,
                         exact forgetting, PYTHONHASHSEED independence)
results/                 machine-readable records (committed, append-only)
reproduction/            the independent re-implementation written from the spec
docs/                    design documents (D1–D8, partly fragmentary), SPEC_REBUILD,
                         SPEC_LM, PROTOCOL, EXPECTATIONS, DEVIATIONS, PREREG_ROBUSTNESS,
                         PREREG_LM, PREREG_LM_V2, audit
docs/archive/edit-logs/  the Claude Code edit logs the recovery was reconstructed from
legacy/                  recovered code fragments; reference only
```

## License

[Apache License 2.0](LICENSE) — Copyright 2026 Erik Thye.

## About

Built by Erik Thye, a 15 year old developer from Germany based on the Costa
del Sol, using an AI-native workflow with tools like Claude Code for building
and verifying the measurement harnesses.

More projects: [github.com/erithy25](https://github.com/erithy25)
