# PREREGISTRATION — Bit-corruption robustness of HDC vs. equal-size baselines

**Status: REGISTERED.** Committed before any run of this study, before the
corruption code was written, and before the underlying benchmarks (B5/B6)
produced a single number. The commit timestamp of this file is its point:
everything below was fixed in advance.

**Version 1.3** · Project ENGRAMM · Registered 2026-08-15 ·
Amended 2026-08-15 (§3.2 corrected) and 2026-09-23 (§3.4, §4.1, §9.1 added),
each before any measurement of this study — see §12

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

### 3.2 WiLI vocabulary selection: pooled or per-language balanced

"The V = 10,000 most frequent character trigrams" is ambiguous, and the
ambiguity is outcome-relevant, so it is resolved here rather than left to the
implementation.

**A correction to v1.1, stated plainly rather than quietly replaced.** The
first version of this section justified the choice partly on "unequal amounts
of text per language". That was **factually wrong**: WiLI-2018 is balanced by
paragraph count, at exactly 500 training paragraphs per language, and the
dataset's own design intends that balance.

Two things do remain true, and one of them was tested:

* Characters per paragraph vary with script and morphology, so the *character
  mass* per language is not balanced — measured, a 9.0× spread between the
  languages with the fewest and most training characters.
* Latin-script trigrams accumulate across roughly half of the 235 languages,
  while a language with a unique script contributes its trigrams alone.

The v1.1 text also predicted a concrete harm — that pooled selection could
leave a language with **no** vocabulary entries, making it unclassifiable
before any corruption. That prediction was **measured and refuted**: under
Variant A, zero of the 235 languages receive zero entries. The worst-served
language (`lzh`, Literary Chinese) still has 399 usable trigrams, and Variant
A actually yields a *higher* median usable count than Variant B (4,119 vs
2,018), because frequent trigrams are shared across many languages. The
argument is withdrawn.

* **Variant A — pooled.** Count trigram occurrences over the entire training
  split, take the top 10,000. Standard practice, and it reflects natural
  corpus statistics. Selection is weighted by character mass and by script
  sharing, but as measured above, not to the point of starving any language.
* **Variant B — per-language balanced.** Rank trigrams within each language
  separately, then fill the vocabulary round-robin across languages. Every
  language is guaranteed representation by construction; the cost is that
  some slots go to trigrams that are globally rare.

**Registered choice: Variant B, on one load-bearing argument.** The reason
that survives measurement is symmetry with the system under test: ENGRAMM
assigns a hypervector to every trigram it encounters and applies no frequency
cutoff at all, so no language is structurally disadvantaged in it. A pooled
vocabulary would impose a selection handicap that the baselines bear and
ENGRAMM does not — in a study whose entire purpose is comparing the two.
Per §3.1 we would rather be disadvantaged by a choice than win by one.

That is now the *only* reason. It stands on its own, but it is one argument
rather than three, and this section says so.

Exact procedure, deterministic by construction:

1. Language order is the sorted list of language codes; within a language,
   trigrams are ranked by `(−count, trigram)`, counts taken from that
   language's **training** paragraphs only.
2. For rank r = 1, 2, 3, …, iterate the languages in order and add each
   language's r-th ranked trigram if it is not already in the vocabulary.
   A language whose distinct trigrams are exhausted is skipped thereafter.
3. Stop at exactly 10,000 entries, preserving the parameter match of §3.1.

TF-IDF document frequencies are computed on the training split only, as
already registered in §3.

**Diagnostic reported with the results:** the per-language vocabulary
contribution under both variants. This is what turned the v1.1 justification
from an assertion into a measurement, and refuted part of it — so it stays,
and it is reported whatever it shows.

### 3.3 Secondary condition: equal bit budget

Reported alongside, not instead: baselines shrunk to ENGRAMM's *bit* budget
(int8 weights, so one eighth the parameters) — MNIST MLP h = 16, WiLI MLP
h = 29. If the two matchings disagree in their verdict, that disagreement is
the finding and is reported as such.

### 3.4 System specifications (added in v1.3, before any measurement)

Versions 1.0–1.2 named the systems but not how they are trained. Every
choice below was left open and is outcome-relevant, so it is fixed here
rather than by the implementation.

**ENGRAMM.** The binarised class prototypes `P` (K × D bits, D = 10,000)
after **T1 over the full training split followed by two epochs of T2**
(D2 §T2: on a miss the example is added to the true class's accumulator and
subtracted from the predicted one; visiting order per epoch from
`default_rng(seed)`). Prediction is `argmax_c sim(q, P_c)` with exact ties
going to the alphabetically first label. The episode layer is **not** part
of the system under test (λe = 0): the hypothesis is about class
prototypes, and stored training examples are a different kind of state.
Encoders are the benchmark encoders unchanged: MNIST
`PixelThermometerEncoder` (Q = 16, `progressive`), WiLI byte-trigram
`TrigramEncoder`.

*Why T1 + T2 and not T1 alone.* T1 + T2 is the training procedure the
specification defines, and the historical prototype reference in
`docs/D4_PROTOTYP.md` (86.49 % on MNIST) was measured with two T2 epochs.
*Disclosure:* when this amendment was committed, the following accuracy
figures from **other** experiments were known — MNIST T1 only 80.07 ±
0.42 % (5 seeds, below the §9 floor of 85 %), MNIST T1 + T2 on the
validation split 86.98 % (seed 42, 50k training images), WiLI full split T1
only 89.79 ± 0.03 %. The MNIST test result of T1 + T2 (experiment E3 in
`docs/EXPECTATIONS.md`) was running and **not** known. The T1-only
prototypes are reported next to the primary system as a secondary system;
the §9 floor applies to the primary system.

**Logistic regression.** Multinomial, L2 penalty with C = 1.0, solver
L-BFGS, at most 1,000 iterations, tolerance 1e-4 (scikit-learn defaults
otherwise). The fit has no random component: the trained model is identical
for every seed, which only changes the corruption draw. It is therefore
trained once per task and reused, and the record says so.

**MLP.** One hidden layer of h ReLU units (h from §3.1 and §3.3), softmax
output, Adam with learning rate 1e-3, mini-batches of 256, L2 penalty
α = 1e-4, a **fixed** number of epochs — 30 on MNIST, 20 on WiLI — with no
early stopping and no validation split. The seed sets initialisation and
shuffling (scikit-learn `MLPClassifier`, `random_state = seed`).

**Baseline inputs.** MNIST: pixels / 255. WiLI: raw counts of the §3.2
vocabulary's character trigrams, multiplied by
`idf = ln((1 + N) / (1 + df)) + 1` with N and df from the training split,
then L2-normalised per text.

**int8 quantisation (primary format).** Per tensor, symmetric:
`s = max|w| / 127`, `q = clip(round(w / s), −127, 127)` stored as
two's-complement int8; every weight matrix and every bias vector is its own
tensor. A flip may produce −128; values are dequantised as `q · s`. acc(0)
in §6 is the accuracy of the **quantised** model.

**float32 (secondary format).** Flips anywhere in the 32 bits of each
value; NaN and ±inf propagate; `argmax` treats NaN as maximal (NumPy), and
whatever prediction results is scored as it is.

**Corruption draw.** `n = ⌊p · N_bits⌋`, computed in integer arithmetic as
`percent · N_bits // 100`; positions are
`default_rng([seed, percent]).choice(N_bits, n, replace=False)` over the
concatenated byte view of the corruptible state; bit `b` of byte `i` is
position `8i + b`.

**Secondary condition in concrete terms.** ENGRAMM: the prototypes plus
the materialised item-memory tables the encoder reads at inference — MNIST
784 position and 16 level vectors, WiLI the 256 byte vectors — with the
test split re-encoded through the corrupted tables. Baselines: weights and
biases plus, on WiLI, the idf vector in the same numeric format. The MNIST
divisor 255 and the vocabulary strings are constants, not corruptible state.

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

### 4.1 Format-matched control (added in v1.3, before any measurement)

The int8 condition can decide the comparison by number format alone. A
uniformly drawn flip hits bit 6 or bit 7 of an int8 value one time in four,
moving it by 64 or 128 quantisation steps — in a tensor whose values sit
mostly near zero, that turns an unimportant weight into the largest one.
Binary prototypes have no such bits: every flip moves one component by the
same amount. An ENGRAMM advantage over int8 baselines could therefore come
from the format and say nothing about distributed representation.

The control isolates the format. From the trained **float** LR and MLP of
the primary parameter count, every weight tensor is binarised to its sign
bits with one scale per output unit, `α = mean |w|` over that unit's
incoming weights (XNOR-Net style, no retraining). The corruptible state is
the sign bits only — **one bit per weight, exactly as for ENGRAMM**; the
scales and biases (≤ 0.3 % of the parameters) stay exact, and that
asymmetry is reported as a limitation in the control's favour. R(p) is
computed as in §6. If a format control's acc(0) is not at least 10 pp above
chance, its R is reported as not interpretable.

**Pre-committed reading.** The verdict of §7/§8 is computed on the
registered terms and is not changed by this control. But if the verdict is
confirmation or partial confirmation on a task, and on that task ENGRAMM's
mean R(p) does **not** exceed the better format-matched control's by ≥ 0.10
at every p ∈ {5, 10, 25} %, the headline must say that the measured
advantage is attributable to the number format and that an advantage of the
distributed representation is **not** shown. If ENGRAMM also beats the
format controls by that margin, the headline may say so.

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

### 9.1 Operational reading of §9 (added in v1.3, before any measurement)

* **Floors** apply to acc(0) of the primary systems in their primary format:
  ENGRAMM (T1 + T2) and the int8 MLP at the §3.1 size. A floor missed on
  either task abandons the study as §9 says; every curve is still published,
  labelled descriptive. The equal-bit-budget MLP (§3.3) is held to the MLP
  floor as well; if it misses it, the §3.3 comparison is reported as not
  interpretable rather than abandoning the study.
* **Validation at p = 50 %** — "approaches chance" means mean R(50 %)
  ≤ 0.05 over the seeds, for every system and format on both tasks. A
  larger value stops the study as a suspected corruption bug. The unit test
  in `tests/test_corruption.py` runs the same check on synthetic data first.
* **Budget.** The 48 h limit is defined on the reference machine. Container
  wall time is recorded but, per `docs/PROTOCOL.md`, is not a criterion.

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

## 12. Amendment log

| Version | Date | Change | Measurements existed? |
|---|---|---|---|
| 1.3 | 2026-09-23 | §3.4 added: training and evaluation of every system fixed (ENGRAMM = T1 + 2 T2 epochs, λe = 0; LR and MLP hyperparameters; TF-IDF; int8 and float32 formats; the corruption draw; the secondary condition in concrete terms). §4.1 added: a 1-bit format-matched control with a pre-committed reading, because the int8 condition can decide the comparison by format alone. §9.1 added: floors, the p = 50 % check and the budget made operational. Nothing in §§1–9 was weakened; §4.1 only adds a way for a confirmation to be qualified. | **No** — no code of this study existed and `results/` held no record of it. Benchmark records of other experiments existed and were known; the relevant ones are listed in §3.4. |
| 1.2 | 2026-08-15 | §3.2 corrected: the v1.1 justification claimed unequal amounts of text per language, which is wrong — WiLI-2018 is balanced at 500 training paragraphs per language. The predicted harm (languages left with zero vocabulary entries under Variant A) was measured and refuted: 0 of 235. Both are stated in the section rather than replaced silently. The registered choice stays Variant B, now resting on the single surviving argument (symmetry with a system that has no frequency cutoff). | **No** — `results/` contained no benchmark record; verified before the commit. |
| 1.1 | 2026-08-15 | §3.2 added: WiLI vocabulary selection resolved to per-language balanced (Variant B), with exact procedure and a reported diagnostic. Former §3.2 renumbered to §3.3. | **No** — `results/` contained no benchmark record; verified before the commit. |
| 1.0 | 2026-08-15 | Initial registration. | No |

Amendments are permitted in place **only** while no measurement of this study
exists. Once the first number is produced, §10 takes effect and any change
requires a new file with its own commit timestamp. This table exists so that
the distinction is auditable from the document itself rather than from
memory; the git history of this file is the primary evidence.
