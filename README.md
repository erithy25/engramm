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

**Easiest way to use it: the local dashboard.** Run
`python -m engramm.lm.dashboard` and open http://127.0.0.1:8765. In the page you can:
- **chat**: ask questions (short answer plus the sentence and source it comes from, or "I don't know"),
  tell it things about you or the world, ask them back, follow up with "he"/"it", and say
  "forget …" (needs the index: `python -m experiments.chat_build --v2`, 30 s);
- write from a prompt, then click any word to see where it came from;
- ask for the most likely next words;
- teach it a text and forget it again.

It runs only on your machine and shares its state with the command line.

What it can do:

| Capability | Command | Measured (container unless marked M4) |
|---|---|---|
| **Chat**: short answers with sources, remembers what you tell it, forgets on request, follows up on "he"/"it" | `python -m engramm.lm chat` or the dashboard | Latest registered round (v14, E27): all criteria of stages 1.1–5 met. SQuAD right sentence 48 %, exact short answer 24 %, F1 32 %; facts you taught 100 % (99 % with a typo); ~0.2 s per turn |
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
source of every word it writes, and is bit-identical across platforms: built
from the same data, the model on the MacBook Air M4 and the one in the Linux
container have the same SHA-256 digest (`b45c2065…`, checked part by part with
`python -m experiments.lm_digests`). Every
number, deviation and verdict is in [`docs/EXPECTATIONS.md`](docs/EXPECTATIONS.md)
(E12, E13) and [`docs/DEVIATIONS.md`](docs/DEVIATIONS.md) (CHANGED-9); the
component specification is in [`docs/SPEC_LM.md`](docs/SPEC_LM.md).

### ENGRAMM-Chat, stage 1: answering by looking up (preregistered in [`docs/PREREG_CHAT.md`](docs/PREREG_CHAT.md))

`python -m engramm.lm ask "Who invented the telephone?"` returns the sentence, among the
16 M sentences it has read and everything taught with `learn`, that best matches the
question, with its source. Below a confidence threshold it answers "I don't know". Ranking
is BM25 plus an idf-weighted soft word match from the HDC meaning vectors. There is no
neural network and no external model, and grading is too an exact match against the SQuAD
gold answers.

| Registered criterion (1,000 SQuAD test questions whose paragraph is in the corpus) | Result |
|---|---|
| C1: the first sentence contains the answer | **met: 41.7 %** (top 5: 54.4 %) |
| C2: gain over plain BM25 (21.8 %) | **met: +19.9 pp**, CI [17.2, 22.5]. An unregistered ablation shows that +18.6 pp of it come from exact word coverage; the meaning vectors add only +1.3 pp, CI [−0.5, 3.0] |
| C3: with the dev threshold, ≥ 55 % precision at ≥ 25 % coverage | missed: 61.4 % precision, but only 18.9 % coverage |
| C4: 200 invented facts learnt in one phrasing, asked in two others: learnt sentence ranked first | **met: 96.8 %** |
| C5: median answer time ≤ 1 s | **met: 26 ms** (container) |

Plainly: it finds the right sentence for about four in ten knowledge questions and nearly
always finds what you taught it, even when you ask in other words. It returns whole
sentences, not phrased answers. The registered "useful" verdict needs C1 and C3, so it is
not reached. Details are in [`docs/EXPECTATIONS.md`](docs/EXPECTATIONS.md) (E14).

### ENGRAMM Chat app: website and desktop app

A chat window in the style of ChatGPT, on top of the ENGRAMM chat system. It has:
- conversations in a sidebar, kept in the browser;
- answers with source chips, the evidence sentence on request, and a "sure" or "unsure" mark;
- a memory panel that lists what you taught ENGRAMM and forgets it for real;
- light and dark themes, and a layout for phones.

```bash
python -m engramm.app          # website: opens http://127.0.0.1:8770 (loads in the background, ~1 min)
cd desktop && npm install && npm start     # desktop app (Electron), see desktop/README.md
```

The logo (`engramm/app/web/logo.svg`) draws the E as a memory trace. It is also the app icon.

### ENGRAMM-Chat v2: a conversation (preregistered in [`docs/PREREG_CHAT_V2.md`](docs/PREREG_CHAT_V2.md))

`python -m engramm.lm chat` (or the dashboard) turns the look-up into a conversation. It does four things:
- It gives a **short answer** with the sentence and source it comes from, or "I don't know".
- It **remembers what you tell it** in an HDC fact memory. Names are letter-trigram hypervectors,
  so a misspelt name still finds its fact.
- It **forgets exactly** on "forget …".
- It understands **follow-ups** with "he", "it" or "that city".

Everything is rules, counting and ENGRAMM's own hypervectors.

**Current status:** in the thirteenth registered test round (v14, E27), every criterion of stages 1.1,
2, 3, 4 and 5 was met in the same single run. The table below is the first v2 round; the rounds in
between follow it.

| Registered criterion (single test run, first v2 round) | Result |
|---|---|
| 1.1 Better look-up: SQuAD / real search queries (NQ-open), Hit@1 vs. stage 1 | **met**: +7.9 pp (44.2 %) / +2.0 pp (4.7 %) |
| 2 Fact memory: 200 invented facts asked in new wording; with a typo; abstain before learning | **met**: 93 %; 85 % (exact dictionary: 0 %); 100 % |
| 3 Conversation memory: facts about you asked back; forgotten exactly; pronoun follow-ups | **missed**: 93 % and 86 % met, but forgetting hit the right fact only 76 % of the time (see below) |
| 4 Short answers: SQuAD EM ≥ 20 % and F1 ≥ 30 %; calibrated "I don't know"; NQ EM ≥ 5 % | **missed**: 18.8 % / 25.3 %; 58.6 % precision at 17.4 % coverage; 1.9 % |
| 5 Chat UI: browser test, ≤ 1 s per turn, deterministic incl. restart from the log | **met** |

Plainly:
- It is a working chat partner: answers with sources, a memory for what you say, and exact
  forgetting.
- It is not a knowledge oracle. Short answers are exactly right for about one SQuAD question in
  five, and for real web queries the 285 M-token corpus rarely holds the answer.
- The stage-3 miss has a clear cause. "call me X" and "I have a brother called X" were stored
  as nearly the same relation of *you*, so "forget my name" often removed the brother.
- HDC helps where similarity matters (typo-tolerant facts: +85 pp over exact lookup), not in
  ranking or answer choice.

Six preregistered test rounds followed (v2–v7, each on fresh unseen data with unchanged
thresholds):
- **Met in every round:** the fact memory (93–100 %, 85–99.5 % with a typo, where an exact
  dictionary gets 0 %), pronoun follow-ups (86–100 %), the UI, speed and determinism.
- **Met in some rounds:** the look-up gain on real search queries (NQ +1.5 to +2.3 pp around the
  2 pp threshold) and calibrated "I don't know" (twice).
- **Never met:**
  - Facts about *you* on new phrasings (38–93 %) and exact forgetting on new phrasings
    (needs 100 %).
  - SQuAD F1 ≥ 30 % (23–27 %) and NQ exact answers ≥ 5 % (1.3–1.9 %).

A seventh round (v8, E21) followed after a rebuild of the dialog manager. The rebuild added:
- a word lexicon counted from the corpus,
- points-based matching,
- broader forget recognition.

The span choice switched from naive Bayes to an averaged perceptron, trained only by counting
corrections.
- **Met:** facts about you, forgetting and pronoun follow-ups on fresh phrasings, each
  100 %. SQuAD exact match 22.7 % and F1 31.0 %.
- **Missed:** calibrated "I don't know" (48.1 % precision at 23.3 % coverage, needs 50 %),
  NQ exact answers (2.5 %) and the NQ look-up gain (+1.6 pp).

Stages 2, 3 and 5 are met; 1.1 and 4 are not.

An eighth round (v9, E22) made two changes:
- The sentence shown as best is now the sentence the answer comes from.
- Search-box queries get their own span model.

θ was also set on all 9,000 spent questions.
- **Met:** every criterion except NQ exact answers:
  - look-up gain on SQuAD +9.8 pp and on NQ +3.6 pp,
  - facts about you, forgetting and follow-ups each 100 %,
  - SQuAD EM 23.3 % and F1 30.9 %,
  - "I don't know" at 50.2 % precision with 21.1 % coverage.
- **Missed:** NQ exact answers, 3.4 % against 5 %. The corpus holds the answer among the top-10
  sentences for only 13 % of NQ questions.

Stages 1.1, 2, 3 and 5 are met; stage 4 misses only this criterion.

A ninth round (v10, E23) let ENGRAMM **read more**: the first 2,000 characters of every English
Wikipedia article with at least 7,000 characters (614,464 articles, 262 M tokens). The sentence
index now covers 547 M tokens.
- **Met:** NQ exact answers for the first time (5.2 %), and everything outside stage 4.
- **Missed:** SQuAD (EM 18.4 %, F1 28.2 %) and calibrated "I don't know" (47.2 %). Both came from
  a small, hard sample of 521 questions. That sample used up the last unseen test-article
  questions.

A tenth round (v11, E24) re-ran the same system on 4,956 questions. They were unseen, but came
from the development articles.
- **Met:** NQ exact answers 6.0 %, "I don't know" at 51.2 % precision with 21.5 % coverage,
  SQuAD EM 22.5 %, and everything outside stage 4.
- **Missed:** SQuAD F1 by 0.05 pp (29.95 % against 30 %).

The threshold is not rounded. Stage 4 therefore remains open.

An eleventh round (v12, E25) let ENGRAMM read every SQuAD paragraph it had not read yet (17,555
paragraphs of 2016 Wikipedia, chosen by the text alone). That gave 38,609 unseen test questions. It
also changed how answers are cut (dates, "X or Y?" questions, spans chosen by expected F1). The
confidence now counts how many of the best sentences hold the answer.
- **Met:** SQuAD EM 22.7 % and F1 30.6 %, NQ exact answers 5.2 %, and everything outside stage 4.
- **Missed:** calibrated "I don't know". Precision was 57.8 %, well above 50 %, but the coverage of
  18.2 % fell short of 20 %: θ, set on the development articles, was too strict for the test articles.

A twelfth round (v13, E26) replaced that confidence with a counted one: an averaged perceptron over
the evidence behind the answer, trained on spent questions only. It also fixed two speed bugs, which
cut the median time per turn from 953 ms to 202 ms.
- **Met:** calibrated "I don't know" (52.7 % precision at 23.6 % coverage) and NQ exact answers (6.5 %).
- **Missed:** SQuAD F1 at 29.4 %, and pronoun follow-ups (63.6 %). All the follow-up misses read
  "that one" as the question's topic instead of the last answer.

A thirteenth round (v14, E27) fixed the follow-ups ("that one", "the latter", "that individual"). The
span choice became the average of seven counted perceptrons.
- **Met, all at once:** every criterion of stages 1.1–5:
  - SQuAD EM 24.2 % and F1 31.8 %;
  - "I don't know" at 56.7 % precision with 22.7 % coverage;
  - NQ exact answers 7.7 %;
  - facts, conversation memory, forgetting and follow-ups 99–100 %;
  - browser test, 191 ms per turn, identical transcripts after a restart from the log.
- **Caveats:** the test paragraphs had been read (the pool condition since stage 1), so the stage-1
  comparison R1 mostly measures that reading. The first start of this run was killed for lack of
  memory before it printed any result, and was restarted unchanged.

All numbers, including the development history and the round-by-round table, are in
[`docs/EXPECTATIONS.md`](docs/EXPECTATIONS.md) (E15–E27).

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
.venv/bin/python -m experiments.chat_build                  # stage-1 sentence index (12 s)
.venv/bin/python -m experiments.chat_eval                   # ENGRAMM-Chat stage 1 criteria C1–C5
.venv/bin/python -m experiments.chat_build --v2             # chat v2 index + document index (30 s)
.venv/bin/python -m experiments.chat_v2_spanstats           # counted answer-span statistics (3 min)
.venv/bin/python -m experiments.chat_v2_eval                # chat v2 criteria (single test run, ~40 min)
.venv/bin/python -m engramm.lm ask "Who invented the telephone?"
.venv/bin/python -m engramm.lm chat                         # conversation in the terminal
.venv/bin/python -m engramm.lm.dashboard                    # web dashboard on http://127.0.0.1:8765
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
                         topic, mixture, learn/forget/why, sampler, CLI (python -m engramm.lm),
                         local web dashboard (python -m engramm.lm.dashboard)
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
