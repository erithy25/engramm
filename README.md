<div align="center">

# ENGRAMM

**Hyperdimensional computing research with a simple rule: preregister every claim, then measure it.**

<img src="https://img.shields.io/badge/approach-Vector%20Symbolic%20Architectures-blue?style=flat-square" alt="Vector Symbolic Architectures" />
<img src="https://img.shields.io/badge/stack-Python%20%2B%20NumPy-green?style=flat-square" alt="Python and NumPy" />
<img src="https://img.shields.io/badge/hardware-MacBook%20Air%20M4-lightgrey?style=flat-square" alt="MacBook Air M4" />

</div>

---

## What is ENGRAMM

ENGRAMM is a machine learning research project exploring Vector Symbolic Architectures (VSA), also known as hyperdimensional computing: representing and learning with very high dimensional vectors instead of gradient-trained networks. The goal is a system that learns continuously, remembers without retraining, and runs on consumer hardware.

What makes this project different is the process, not just the results. Every milestone follows a strict protocol: success criteria are registered before measurement, all experiments run across multiple seeds, results are independently reproduced bit-identical, and negative results are documented instead of buried.

## Measured results

All experiments run on a MacBook Air (M4, 16 GB) with Python and NumPy. No GPU, no cloud.

| Milestone | Task | Result |
|-----------|------|--------|
| M1 | WiLI-2018 language identification | 79.30% accuracy (5 seeds, independently reproduced bit-identical) |
| M1b | MNIST image classification | 94.62% accuracy |
| M0 | HNSW recall audit on 1M real keys | 95.57% recall at ef=128, 27.4 mJ per query |
| M2b | Utility-based eviction with L2 persistence gate | Exact crash-replay proven |
| M3 | 1,000-author sequential learning | Order-invariance proven bit-identical |
| M5 (prep) | Intent classification baselines | Banking77 62.6%, CLINC150 69.0% |

## Documented failures

Real research includes results that did not work, and they are part of the record:

- **M2a consolidation via similarity absorption:** failed with a 53 percentage point accuracy drop. The underlying survivor-bias mechanism was identified and documented.
- **M3 forgetting metric:** the originally registered metric turned out to be mis-specified. The forgetting effect was decomposed (80% score-space crowding vs. 20% true interference) and the target was re-ratified under the project's own revision protocol.

## Method

1. Register the success criterion before running the experiment.
2. Run across multiple seeds on fixed hardware.
3. Reproduce independently before a result counts.
4. Document failures with the same rigor as successes.

## About

Built by Erik Thye, a 15 year old developer from Germany based on the Costa del Sol, using an AI-native workflow with tools like Claude Code for building and verifying the measurement harnesses.

More projects: [github.com/erithy25](https://github.com/erithy25)
