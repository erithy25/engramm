<div align="center">

# ENGRAMM

**Hyperdimensional computing research with a simple rule: preregister every claim, then measure it.**

<img src="https://img.shields.io/badge/approach-Vector%20Symbolic%20Architectures-blue?style=flat-square" alt="Vector Symbolic Architectures" />
<img src="https://img.shields.io/badge/stack-Python%20%2B%20NumPy-green?style=flat-square" alt="Python and NumPy" />
<img src="https://img.shields.io/badge/status-rebuilding-red?style=flat-square" alt="Rebuilding" />

</div>

---

## Status

**The original implementation of this project is lost, and none of the results
below are currently reproducible.**

What happened: the source code was developed locally but never fully committed
to version control. When the working tree was lost, the only surviving artifact
was a set of Claude Code edit-tool logs, from which the code was partially
reconstructed (commit `a1af719`). The core module — documented at 469 lines —
survives as a 17-line fragment; the harness that produced the WiLI result was
not recovered at all. The recovered code — fragments plus a few complete but
non-runnable files — is preserved in [`legacy/`](legacy/), the edit logs in
[`docs/archive/edit-logs/`](docs/archive/edit-logs/), and a full forensic
account of what survives is in the repository's audit
(branch `claude/engramm-reproducibility-audit-y94aa7`).

The project is being reimplemented from scratch in this repository, starting
from the preserved design documents (in particular
[`docs/D2_SPEC.md`](docs/D2_SPEC.md)). Until a benchmark has been re-run under
the new implementation, every number in this README is a **historical claim
from the project's records, not a verified result**.

This is exactly the kind of failure the project's own protocol exists to
catch, so it is documented here with the same bluntness the protocol demands
of experimental results.

## Historical results (currently unverifiable)

All figures below were recorded on a MacBook Air (M4, 16 GB) in July 2026.
ENGRAMM's own figures are CPU-only; the M5 baseline side ran the LLM with
Metal GPU acceleration (llama-cpp-python). The measurement protocols, per-seed values, and negative results
were logged in detail in the design documents — but the code, data, and run
logs did not survive. **Until reimplemented and re-measured, these numbers
are not evidence; they are targets to test against.**

| Milestone | Task | Recorded result |
|-----------|------|-----------------|
| M1 | WiLI-2018 language identification, **10-shot**, 235 classes | 79.30 % ± 0.68 % top-1 (5 seeds) |
| M1b | MNIST image classification, official 60k/10k split | 94.62 % top-1 (seed 42); 5-seed mean 94.59 % ± 0.04 |
| M0 | HNSW recall audit on 1M keys | 95.57 % recall@32 at ef=128; 27.4 mJ/query |
| M2a | Consolidation via similarity absorption | **Failed:** −53 pp accuracy (documented negative result) |
| M2b | Utility-based eviction with L2 persistence gate | Crash-replay test passed in original runs |
| M3 | 1,000-author sequential learning | State-level order invariance observed (see caveat below) |
| M5 | Intent classification vs. local LLM baselines | **Hypothesis failed:** ENGRAMM 62.6 % Banking77 / 69.0 % CLINC150 — 20.4 and 22.0 pp behind the LLM+RAG baseline — preregistered outcome (3) on this task family |

Three qualifications that earlier versions of this README stated too
loosely, corrected here:

- **The WiLI number is a few-shot result.** 79.30 % was measured with **10
  training examples per language** across all 235 languages of WiLI-2018
  (chance level 0.4 %), not on the full WiLI training split. It is a
  respectable few-shot figure and must not be read as a full-data one.
- **The MNIST time criterion was not met under its original reading.** The
  preregistered criterion was accuracy ≥ 94 % **and** learning time < 30 min
  CPU, enforced in the harness as *max over seeds* < 30 min. The 5-seed run
  measured **mean 28.1 ± 2.4 min, max 31.8 min** (seed 99) — a fail under the
  max rule. After investigating thermal throttling (the first official run
  took 41.4 min during an 11.5 h wall-clock session with sleep/wake cycles;
  the same seed took 27.4 min in a caffeinated re-run), the project changed
  the adjudication rule to the *mean* (D5 v1.1, logged as registered before
  the 5-seed times were known) and recorded the criterion as met. Both values
  are reported here because the rule change was outcome-relevant: the
  accuracy claim is unaffected, the "< 30 min" claim holds only under the
  revised rule.
- **The M3 order-invariance claim applies to the learned state, not to
  outputs.** Sequential construction in different presentation orders
  produced bit-identical prototypes and episode multisets in the original
  runs. Classification
  output still differed by 0.03 pp under episode reordering, due to an
  order-dependent tie-break that was never fixed (issue W19). Stronger
  wording used previously ("proven", "independently reproduced
  bit-identical") is retracted until the property can be demonstrated again
  under the new implementation.

## Roadmap

The rebuild is also a re-scoping. The new primary research question:

> **How robust are HDC classifiers to bit corruption of the learned state,
> compared to baselines with the same parameter count?**

Distributed hypervector representations should degrade gracefully when bits
flip (memory faults, aggressive quantization, adversarial noise), whereas
compact learned models concentrate meaning in few parameters. That claim is
folklore in the VSA literature; we want to measure it, with preregistered
criteria, against baselines given the same bit budget.

Phases, in order:

1. **Infrastructure first.** Pinned dependencies, deterministic data download
   with checksums (WiLI-2018, MNIST), seeds for every randomness source, one
   command per benchmark, machine-readable results in `results/` (timestamp,
   seed, commit hash, environment) — committed, not gitignored.
2. **Reimplement the core** from `docs/D2_SPEC.md` (item memory, trigram
   encoder, T1 accumulation, T2 error-driven updates), plus the pixel/
   thermometer image encoder recorded in `docs/D4_PROTOTYP.md`. No silent
   design changes; deviations from the record get documented.
3. **Re-run the two historical benchmarks** (WiLI 10-shot, MNIST) across 5
   seeds and publish mean ± SD. Whatever comes out is the new official
   number. If it deviates from the historical claims, the deviation is
   documented, not massaged.
4. **The bit-corruption study**: corruption sweeps (random bit flips at
   increasing rates) over ENGRAMM's learned state vs. equal-parameter-count
   baselines, criteria registered before measurement.

## Method

Unchanged, and the reason this README looks the way it does:

1. Register the success criterion before running the experiment.
2. Run across multiple seeds on fixed hardware.
3. Reproduce independently before a result counts.
4. Document failures with the same rigor as successes.

## Repository layout

```
docs/                    design documents: D1 manifest, D2 spec, D4 prototype record,
                         D5 experiments, D6 honesty contract, D8 audit, the V2
                         target-dimension documents, project notes — partially
                         fragmentary, see docs/archive/
docs/archive/edit-logs/  the Claude Code edit logs the recovery was reconstructed from
legacy/                  recovered code — fragments plus complete but non-runnable
                         files; reference only
results/                 machine-readable benchmark results (committed, append-only)
```

## About

Built by Erik Thye, a 15 year old developer from Germany based on the Costa
del Sol, using an AI-native workflow with tools like Claude Code for building
and verifying the measurement harnesses.

More projects: [github.com/erithy25](https://github.com/erithy25)
