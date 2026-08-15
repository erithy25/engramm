# PREREGISTRATION — Bit-corruption robustness of HDC vs. equal-size baselines

**Status: REGISTERED.** Committed before any run of this study, before the
corruption code was written, and before the underlying benchmarks (B5/B6)
produced a single number. The commit timestamp of this file is its point:
everything below was fixed in advance.

**Version 1.0** · Project ENGRAMM · Registered 2026-08-15

---

## 1. Hypothesis

> Binary hyperdimensional class prototypes lose accuracy more slowly under
> random bit corruption of the trained model than logistic-regression and
> MLP baselines of comparable parameter count subjected to the same
> corruption procedure.

That is the whole claim. It is about *representation*, not about accuracy:
the baselines are expected to be at least as accurate uncorrupted, and the
hypothesis says nothing to the contrary.

## 2. Why this could plausibly be false

Stated up front, because a preregistration that only argues for its own
hypothesis is worthless:

* HDC's robustness folklore mostly concerns corruption of *inputs* or of
  *bundled encodings*, not corruption of the classifier state after
  training. The transfer is an assumption, not a result.
* At equal parameter count the baselines get 8× (int8) or 32× (float32) the
  raw bit budget, since ENGRAMM stores one bit per parameter. More redundant
  bits could mean more graceful degradation, favouring the baselines.
* A trained MLP's accuracy is dominated by a minority of large weights;
  random bit flips mostly hit small ones. This could make MLPs far more
  robust than intuition suggests.
* Both could degrade near-identically, which is a boring but entirely
  possible outcome. It counts as refutation (§8), not as "inconclusive".

## 3. Tasks and models

Two tasks, both with the official splits, trained on the **full** training
split.

| | MNIST | WiLI-2018 |
|---|---|---|
| Split | official 60k / 10k | official split, all 235 classes |
| Classes K | 10 | 235 |
| Chance level | 10 % | 0.4255 % |
| Baseline input features | 784 raw pixels, scaled to [0,1] | TF-IDF over the V = 10,000 most frequent character trigrams |

**Explicitly excluded from this study: the 10-shot WiLI setting.** Few-shot
would confound representation robustness with sample efficiency. The 10-shot
benchmark remains a separate milestone (M1/B6) and its numbers are not part
of this preregistration.

**Feature discipline.** The trigram vocabulary, the TF-IDF statistics, and
any input scaling are fitted **on the training split only** and then applied
unchanged to the test split. This is enforced by `tests/test_no_leakage.py`,
not merely intended.

### 3.1 Parameter matching

ENGRAMM stores K × D binary prototype bits at D = 10,000. The controls are
sized to match that parameter count:

| Task | ENGRAMM (bits) | Logistic regression | MLP (hidden units) |
|---|---|---|---|
| MNIST | 10 × 10,000 = **100,000** | 7,850 — **not matchable** | h = 126 → 100,180 (+0.18 %) |
| WiLI | 235 × 10,000 = **2,350,000** | 2,350,235 (+0.01 %) — matched | h = 230 → 2,354,515 (+0.19 %) |

Logistic regression on MNIST cannot be parameter-matched without changing
the model class (784 × 10 + 10 is fixed by the input dimension). It is
therefore included as a **lower-capacity control**, and its parameter count
is reported alongside every result. On WiLI it happens to match almost
exactly, because V = D = 10,000.

**This matching is conservative against our own hypothesis**: equal
parameter count gives the int8 baselines 8× ENGRAMM's storage in bits, and
the float32 baselines 32×. We prefer to be disadvantaged by the primary
condition than to win by a favourable choice of accounting.

### 3.2 Secondary condition: equal bit budget

Reported alongside, not instead: baselines shrunk to ENGRAMM's *bit* budget
(int8 weights, so one eighth the parameters) — MNIST MLP h = 16, WiLI MLP
h = 29. If the two matchings disagree in their verdict, that disagreement is
the finding and is reported as such.

## 4. Corruption procedure

For corruption rate p ∈ **{0, 1, 5, 10, 25, 50} %**:

1. Train the model. Corruption is applied **after training, before
   evaluation** — no corruption-aware training, no retraining, no
   recalibration, no threshold re-tuning.
2. Choose ⌊p × N_bits⌋ bit positions uniformly at random **without
   replacement** from the model's corruptible state, and flip them (XOR 1).
3. Evaluate on the test split.

One corruption draw per (system, task, seed, level). The corruption RNG is
derived from `(seed, level)` so every draw is reproducible and independent
of evaluation order.

**Corruptible state — primary condition:** the learned state only.

* ENGRAMM: the binarized class prototypes.
* Baselines: the weight and bias tensors.

The ENGRAMM item memory is a fixed random codebook, regenerable from the
seed, and is treated as architecture rather than learned state. **Secondary
condition:** everything the model needs at inference, item memory included.
Both are reported.

**Numeric format.** Bit flips in IEEE-754 floats are catastrophic for
reasons that have nothing to do with distributed representation: one flip in
the high exponent bit changes a weight by ~2^128. Preregistering the naive
float condition as primary would hand us a guaranteed win that means
nothing. Therefore:

* **Primary:** baselines quantized to **int8** (per-tensor symmetric
  scaling computed from the trained weights, not from data), bits flipped in
  the int8 representation, dequantized, evaluated. ENGRAMM's prototypes are
  already binary.
* **Secondary, reported but never headline:** float32 baselines with naive
  bit flips. We record here, in advance, the expectation that this condition
  strongly favours ENGRAMM and that it must not be cited as evidence for the
  hypothesis.

## 5. Seeds

Ten seeds, fixed now:

```
42, 7, 1337, 2026, 99, 3, 123, 512, 8191, 31337
```

The first five are the project's existing seeds; the second five are added
to reach ten. Every system sees the same ten seeds. A seed governs model
initialization, any data shuffling, and the corruption draw. No seed is
dropped for any reason other than a documented crash, and a dropped seed is
reported with its reason.

## 6. Primary metric

Raw accuracy drops are not comparable between systems with different
uncorrupted accuracy, and they are floored by chance level at different
points. The primary metric is therefore **chance-corrected retention**:

```
R(p) = (acc(p) − c) / (acc(0) − c),      clipped to [0, 1]
```

with c the chance level (0.1 for MNIST, 1/235 for WiLI). R(0) = 1 by
construction; R = 0 means "no better than guessing". The reported value is
the mean of R(p) over the ten seeds, with standard deviation and a 95 %
confidence interval of the mean.

Reported alongside for transparency, but not decisive: raw acc(p), the
absolute drop acc(0) − acc(p) in percentage points, and each system's
parameter and bit count.

## 7. What counts as CONFIRMATION

The hypothesis is confirmed if **all** of the following hold:

1. At **every** corruption level p ∈ {5, 10, 25} %, ENGRAMM's mean R(p)
   exceeds **both** controls' mean R(p) by **≥ 0.10**.
2. At those levels, the 95 % confidence intervals of ENGRAMM's and each
   control's mean R(p) **do not overlap**.
3. Both conditions hold on **both** tasks.
4. ENGRAMM's uncorrupted accuracy clears the floors in §9 — a system that
   starts out broken cannot demonstrate graceful degradation.

If conditions 1–2 hold on exactly one of the two tasks, the outcome is
**partial confirmation**, reported as "holds on task X, not on task Y",
with no generalization beyond the task where it holds.

## 8. What counts as REFUTATION

The hypothesis is refuted if **any** of the following holds:

1. At a majority of the levels p ∈ {5, 10, 25} %, ENGRAMM's mean R(p) is
   **below** the better control's mean R(p).
2. The gap is **< 0.05 at every level** on both tasks — the systems degrade
   equivalently, and "HDC degrades more gracefully" is not supported.
3. Confirmation fails on both tasks without the refutation criteria being
   met either — recorded as **not supported**, which is a negative result
   and is published as one.

There is no fourth outcome, and no post-hoc subgroup in which a failed
result may be re-declared a success.

## 9. Abort criteria

The study is abandoned, and the abandonment reported, if:

* **Floor not cleared.** Uncorrupted accuracy below 85 % (MNIST) or 60 %
  (WiLI) for ENGRAMM, or below 90 % / 65 % for the MLP control. Comparing
  degradation curves of models that never worked is meaningless.
* **Corruption implementation fails validation.** At p = 50 % on a binary
  or int8 state, a randomly chosen half of all bits is flipped, which
  leaves the state effectively uncorrelated with the original — every
  system's accuracy must therefore approach chance (R ≈ 0). Any system that
  does not is evidence of a bug in the corruption code, not of robustness.
  This check runs as a unit test before the study.
* **Non-determinism.** The corruption pipeline fails the determinism tests
  in `tests/test_determinism.py` (identical results under different
  `PYTHONHASHSEED`, and across platforms per `docs/PROTOCOL.md`).
* **Budget.** More than 48 h of wall-clock compute on the reference machine
  for the complete grid. If exceeded, D is reduced for *all* systems
  simultaneously and the reduction documented — never for one system alone.

## 10. Amendment rule

**Criteria are not changed after the first measurement.** Once any run of
this study has produced a number, §§1–9 are frozen.

If a genuine specification error is discovered afterwards, the procedure is:
a **new file** `PREREG_ROBUSTNESS_v2.md` with its own commit timestamp,
stating what changed and why; this file stays in place unchanged; and every
result measured under v1 continues to be reported under v1's criteria. No
silent edits, no rebasing this file, no force-push to its commit.

The project's history contains one instance of a criterion being
operationally relaxed after a failing measurement (the M1b time criterion,
changed from max over seeds to mean; see the README and
`docs/AUDIT_2026-08.md`). That change was disclosed and defensible, but it is
exactly the pattern this rule exists to prevent from recurring.

## 11. Environment

All figures follow `docs/PROTOCOL.md`: accuracy and retention may be
produced in the Linux container but must be confirmed bit-identically on the
reference M4 before they count; wall time and peak memory are reference-
machine-only. Every run writes a record to `results/` carrying its seed,
commit hash, `canonical` flag, and full hyperparameters.
