# ENGRAMM Sela-1 135M — model card

**Sela-1 135M** is the first GPU-trained model of the *Sela* family in the ENGRAMM project (the earlier CPU-only network
can be listed as Sela-0 100M). It is a decoder-only transformer with
135.3 M parameters, trained **from scratch**: own tokenizer, random initialisation, no pretrained weights and no
distillation. Training ran on one rented NVIDIA H100 for 3.27 hours.

On the held-out test split of the ENGRAMM language-model study it reaches **0.989 bits per byte** (network alone,
pre-registered rule). The pre-registered target for *Stage 1 (GPT-2 level)* was ≤ 1.04, so **Stage 1 is reached**.
GPT-2 small, scored zero-shot on the same documents with the same byte accounting, gets 1.036.

Read the caveats below before quoting the comparison with GPT-2. It is an **in-domain** result: the test documents
come from the same sources Sela-1 was trained on.

| | |
|---|---|
| Name | ENGRAMM Sela-1 135M (family *Sela*, generation 1, 135 M parameters) |
| Status | research model, trained 16–17 Oct 2026 (UTC); base model only (no instruction tuning, no safety tuning) |
| Language | English |
| Weights | not public. Private draft release `h100-results-20261017-0317` of this repository, asset `model_main_20261017031737.pt` (541,082,912 bytes, fp32). The continuation state from before the learning-rate decay (at 4.03 B tokens) was not uploaded, probably because the 25 $ cost brake was only minutes away; the cause is not logged. It exists only on the stopped rental machine. |
| Results | `results/v5/h100/` (evaluation, curve, logs, token log-probabilities, samples, verification) |
| Plan and rules | `docs/PLAN_V5_FROM_SCRATCH.md` §10–§11; run procedure `docs/H100_ANLEITUNG.md` |
| Code | `experiments/h100_data.py`, `experiments/h100_train.py`, `experiments/h100_run.sh` (commit `eb2e002`); model class `LongGPT` in `experiments/v5_long.py` |

## Architecture

| | |
|---|---|
| Type | decoder-only transformer, pre-norm (RMSNorm without weights) |
| Layers / width / heads | 12 / 768 / 12 (head size 64) |
| Context | 1,024 tokens, rotary position embeddings, QK-norm (RMS) |
| Feed-forward | 4 × 768, ReLU² |
| Output | untied output matrix, logits soft-capped at 30 (`30·tanh(z/30)`) |
| Vocabulary | 32,768 byte-level BPE tokens, trained on the study's training text only |
| Parameters | 135,266,316 in total: 84,934,656 in the 12 blocks, 2 × 25,165,824 in input embedding and output matrix, 12 scalars |

GPT-2 small, for comparison, has 124 M parameters with a tied embedding. Its non-embedding size (about 85 M) is about
the same as Sela-1's.

## Training data

The training stream `train_all` holds 6.802 billion tokens:
- **Base training text of the LM study** (284.7 M tokens; SHA-256 pinned in `experiments/h100_data.py`). It consists
  of C4-en shard 0 and WikiText-103 training articles, split by a hash of URL or title.
- **The WikiText-103 part of the base text three more times** (29,245 documents, 113 M tokens per copy; 4 copies in
  total). The base C4 part appears once. The reason: by bytes, val-A is 37.5 % and test 41.8 % WikiText, and without the
  repeats the stream would have only 1.75 % Wikipedia.
- **C4-en shards 1–36**, keeping only documents whose URL hash falls in the training range. The same hash rule keeps
  every validation and test URL out. The SHA-256 of every shard is pinned in `experiments/h100_data.py`.

The stream is shuffled document by document. Training consumed 5.757 B tokens, which is 0.85 of one pass. No
document was seen twice, apart from the deliberate WikiText copies.

## Training procedure

| | |
|---|---|
| Tokens / steps | 5,757,206,528 tokens = 10,981 steps × 524,288 tokens (32 × 1,024 per micro-batch, 16 micro-batches) |
| Optimiser | AdamW, β = (0.9, 0.95), ε = 1e-8, weight decay 0.1 on block weights only |
| Learning rate | peak 1e-3 with 300 warm-up steps, constant, then linear decay to 0 over the last 30 % |
| How the rate was chosen | three 200 M-token runs on the base text (val-A, 150 documents: 1e-3 → 1.627, 2e-3 → 1.749, 4e-3 → 1.916 bpb), winner × 0.5 clipped to [1e-3, 2e-3] — a rule fixed before the run |
| Precision | bf16 autocast, fp32 weights and optimiser state |
| Attention in training | FlexAttention with a "causal AND same document" block mask. It was chosen at start-up because it matched the dense attention (max. deviation 0.004 in outputs, 0.002 relative in gradients) and needed 35 % less time per micro-step (1.54× the speed). The evaluation always uses the plain dense causal attention. |
| Token budget | fitted to the time limit set by the 25 $ cost brake: 10 B → 5.583 B at step 100, then re-fitted to 5.675 B and 5.757 B |
| Hardware and speed | 1 × NVIDIA H100 80GB HBM3 (SXM), about 489 k tokens/s, 3.27 h of training, peak tensor memory 16.4 GiB |
| Cost | about 25 $ of rented time at 4.01 $/h, for the whole run (data preparation, learning-rate search, training, evaluation, upload) |
| Incidents | none in training: no resume, no out-of-memory, no divergence, no fallback from FlexAttention. The run script was started three times; the first two starts stopped before any work because of an invalid GitHub key. |

## Evaluation

**Rule, fixed before the run** (`docs/PLAN_V5_FROM_SCRATCH.md` §11):
- test split of the LM study, network alone, sliding window 1,024 with stride 512;
- bits per byte = bits of all target tokens / (UTF-8 bytes + 1 end-of-document token per document);
- test documents with ≥ 20 % of their 13-token windows anywhere in the training stream are excluded (the extended
  filter, `results/v5/h100/contamination.json`). The scan covers all 6.802 B tokens of the stream, a superset of the
  5.757 B trained on;
- Stage 1 is reached at ≤ 1.04.

| Measurement | Sela-1 135M | GPT-2 small (zero-shot, same documents) | Ratio (95 % CI, paired document bootstrap) |
|---|---|---|---|
| **Test, extended filter (1,023 docs) — decides Stage 1** | **0.989** (0.975–1.005) | 1.036 | **0.955** (0.947–0.962) |
| Test, original filter of the LM study (1,092 docs) | 0.988 | 1.039 | 0.951 (0.943–0.958) |
| Test, no filter (1,137 docs) | 0.980 | 1.038 | — |
| Test, extended filter, C4 documents (58 % of bytes) | 1.010 | 1.069 | 0.945 |
| Test, extended filter, Wikipedia documents (42 % of bytes) | 0.961 | 0.991 | 0.970 |
| Test, strict subset: extended filter and no 13-gram overlap at all with the base text (909 docs) | 1.006 (0.986–1.025) | 1.057 | 0.952 (0.945–0.959) |
| val-A, original filter (735 docs) | 0.977 | — | — |
| Sela-1 mixed with the exact counting model (one λ per history bucket, fitted on val-A), test, extended filter | 0.982 | 1.036 | 0.948 (0.940–0.956) |

On these 1,023 held-out documents from its own training sources, with GPT-2 small scored zero-shot, Sela-1 needs fewer
bits than GPT-2 small on 87 % of the documents; the median per-document ratio is 0.93.

The earlier CPU-only network of the same project (100.9 M parameters, 59.0 M of them in the blocks; 0.60 B tokens,
134 h on 4 CPU cores) scored 1.141 on the same test split (original filter; Sela-1: 0.988).

**Learning curve** (val-A, first 150 documents, all of them C4 — harder than the full val-A):

| Tokens | 0.5 B | 1.0 B | 2.0 B | 3.0 B | 4.0 B | 5.0 B | 5.5 B | 5.76 B (end, same 150 docs) |
|---|---|---|---|---|---|---|---|---|
| bpb | 1.296 | 1.201 | 1.145 | 1.123 | 1.107 | 1.082 | 1.068 | 1.063 |

The full val-A gives 0.977 at the end. The gap to the curve comes from document composition, not from the last steps:
the curve's 150 documents contain no Wikipedia text, and on the other 617 documents the final model scores 0.962.

## Verification

Four agents checked the result independently on 17 Oct 2026 (`results/v5/h100/verify_20261017.json`). They worked
read-only, and three of them used separate lenses:

- **Code path.** The evaluation runs the plain causal forward pass; FlexAttention runs only in training. On a test
  model, changing token *t* never changes a logit before *t*. Every target token is scored exactly once, with left
  context from its own document only. Byte counts equal the UTF-8 lengths of the corpus text. GPT-2's reference uses
  identical denominators and windowing: 10 documents re-scored with GPT-2 matched to 4·10⁻⁴ bits. The split files
  carry the pinned SHA-256 hashes, and the training stream never reads them. The final weights were evaluated in fp32
  in the same process right after training; there was no averaging and no reload.
- **Recomputation.** The six final values (test and val-A, three filters each) come out the same from the saved
  per-token log-probabilities (to about 10⁻¹⁴), per-document bits to 4·10⁻⁹; the arrays have no gaps, no positive
  values and no NaN. The learning curve and the learning-rate search were measured on intermediate weights and cannot
  be recomputed this way.
- **Contamination.** The base-text overlap was recomputed with a different hash and reproduces the excluded documents
  and mean overlaps exactly. Among kept documents of at least 500 bytes, the per-document ratio to GPT-2 has no rank
  correlation with base-text overlap (Spearman ρ = 0.00); the small group with 5–20 % overlap (22 documents) does
  score better (0.903 against 0.952 at zero overlap). The excluded documents show memorisation (ratio 0.72 for the 45
  excluded through the base text, 0.80 for the 69 excluded only through the C4 text), which is what the filter is for.
- **Adversarial judge.** Verdict: Stage 1 reached, with caveats. Partial overlap with the base text below the threshold
  is worth about 0.004 bpb. Stress tests on the saved probabilities put the plausible effect of remaining memorisation
  of the extra C4 text at about 0.01 bpb; that is an estimate, not a bound. The harshest stress test gives 1.002
  (+0.013), still below 1.04. Three small templated web pages remain in the test set with clear memorisation; together
  they move the result by 0.0002.

## Re-run on a CPU and benchmarks outside the training data

GitHub Actions ran the network again on 17 Oct 2026 (workflow `.github/workflows/sela1_bench.yml`, results
`results/v5/h100/bench_main.json` and `eval_recheck_cpu.json`). The runners loaded the weights from the private draft
release; the weights are not in any artifact.

**Re-run on a CPU.** The base data were rebuilt with the pinned SHA-256 values. The same evaluation code then ran on a
CPU in fp32 (torch 2.8.0) and gave test 0.98938 (extended filter), against 0.98938 on the H100: a difference of
1.6·10⁻⁶ bpb. Per token, the log-probabilities differ by at most 5·10⁻⁵ nats. The Stage-1 number is therefore
reproduced by the network itself, not only from the saved probabilities.

**Zero-shot benchmarks.** These tasks come from sources Sela-1 was not trained for (stories, commonsense questions,
science questions). Both models were scored with the same code (`experiments/sela1_bench.py`, scored like EleutherAI's
lm-evaluation-harness, every context starting with the end-of-text token).

| Task (items) | Metric | Sela-1 135M | GPT-2 small | Sela-1 − GPT-2 (95 % CI, paired bootstrap) |
|---|---|---|---|---|
| HellaSwag (10,042) | acc_norm | **32.7 %** | 31.3 % | **+1.4 pp** (+0.8 … +2.1) |
| PIQA (1,838) | acc_norm | **64.7 %** | 62.5 % | **+2.2 pp** (+0.5 … +3.9) |
| ARC-Easy (2,376) | acc_norm | 39.9 % | 40.5 % | −0.6 pp (−2.2 … +1.1), no difference |
| LAMBADA (5,153) | acc / perplexity | 27.8 % / 54.8 | **33.7 % / 35.1** | **−5.9 pp** (−7.1 … −4.7) |

Outside its own data, Sela-1 is about level with GPT-2 small: better on HellaSwag and PIQA, level on ARC-Easy, and
clearly worse on LAMBADA. LAMBADA asks for the last word of passages from novels, which need long context. Sela-1's
training text had no books (web pages and Wikipedia only). The GPT-2 numbers from these runners match a separate run on
the project's CPU machine exactly (`results/v5/h100/bench_gpt2_local/`).

## Caveats

- **In-domain, not general.** The test documents come from the same sources Sela-1 was trained on (C4-en and
  WikiText-103), and the training mix was matched to the evaluation mix. GPT-2 small sees this text zero-shot. The
  ratio 0.955 does not show that Sela-1 is a better general language model than GPT-2 small. On the four zero-shot
  benchmarks above it is about level with GPT-2 small, not better overall.
- **Partial overlap.** Test documents below the 20 % overlap threshold can still share passages with the training text.
  Overlap with the extra C4 text below 20 % could not be recomputed on the checking machine. The C4 shards are public
  and pinned by SHA-256 (`experiments/h100_data.py`), so the check can be repeated elsewhere; the stress tests above
  estimate its plausible effect.
- **Re-run done.** The four verifiers worked from the saved token log-probabilities only. The later CPU re-run of the
  network (above) reproduces the test value to 1.6·10⁻⁶ bpb with the repository's code (run on commit `14a886d`), so
  uncommitted edits on the rental machine cannot have changed the result.
- **Mixture is not the Stage-1 number.** Stage 1 is decided by the network alone. The mixture with the counting model
  (0.982) is reported separately.

## Limitations and intended use

Sela-1 is a research artefact that shows how far a small from-scratch model gets with an efficient recipe and about
25 $ of compute. It writes fluent English paragraphs that drift in meaning, and it invents facts. It has no instruction
tuning, does not answer questions reliably and does not understand German. Do not use it for anything that needs
correct facts or safe behaviour.

Two samples from the final model (prompt in bold; top-p 0.9, temperature 0.9, repetition penalty 1.15, seed 1;
`results/v5/h100/samples_main.json`):

> **How to make a cup of tea: First,** you need the water. When you boil it, it will be thick enough to hold in liquid
> form; when the leaves are white and yellow (they will turn bitter) add some water, if necessary, about 1-2
> teaspoons. Stir gently until everything is well mixed.

> **Albert Einstein was** born on September 15, 1900 in Los Angeles, California. He became famous because of his
> beautiful children, Victor (1916-1972) and Charles (1842-1939).

The second sample is fluent and entirely wrong, which is typical at this size.

## Licence and data

The weights are not released. The training text is C4-en and WikiText-103 (from Wikipedia). Their licences (to my
knowledge ODC-BY for C4 and CC BY-SA for WikiText-103) are not yet recorded in `docs/DATA_LICENSES.md`; check them
before any release.
