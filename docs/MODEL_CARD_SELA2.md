# ENGRAMM Sela-2 — model card

**Status: trained on 18 Oct 2026, results below.** Architecture, data, procedure, intended use and licences were fixed
before the run (17 Oct); every number under *Results* comes from the run's records (`results/sela2/`), judged against
the success criteria pre-registered in `docs/PREREG_SELA2.md`.

**Sela-2** is the second generation of the *Sela* family in the ENGRAMM project and the first one meant for chat. It
is a decoder-only transformer trained **from scratch** (own bilingual tokenizer, random initialisation, no pretrained
weights, no distillation) on one rented NVIDIA H100 within a 25 $ budget, then fine-tuned for conversation and for
answers from sources (cited with [n] and checked by the app before they are shown).

| | |
|---|---|
| Name | ENGRAMM Sela-2 (generation 2; 352 M parameters per token, 503 M stored) |
| Variants | `sela2_basis` (pretrained, the chat data are already in its learning-rate decay) and `sela2_chat` (fine-tuned) |
| Languages | English; German as an attempt without a target |
| Weights | not public; private draft release "ENGRAMM Sela-2 Modell YYYYMMDD-HHMM (privat)" of this repository: `sela2_chat_bf16.pt`, `sela2_basis_bf16.pt`, `fortsetzen_vor_abklingen.pt` (state before the decay), and after the evaluation workflow the app files `sela2-chat.npz`, `sela2-basis.npz` (int8) |
| Plan, rules, procedure | `docs/PLAN_V5_FROM_SCRATCH.md` §12, `docs/PREREG_SELA2.md`, `docs/SELA2_ANLEITUNG.md` |
| Code | model `experiments/sela2_model.py`, optimiser `experiments/sela2_optim.py`, training `experiments/sela2_train.py`, data `experiments/sela2_data.py`, run `experiments/sela2_run.sh`, app `engramm/lm/sela.py` + `engramm/lm/sela_chat.py` |

## Architecture

| | |
|---|---|
| Type | decoder-only transformer, pre-norm (RMSNorm without weights), the nanochat recipe of late 2026 |
| Layers / width / heads | 24 / 1,024 / 8 (head size 128) |
| Context | 2,048 tokens; rotary embeddings (θ 10,000, interleaved), QK-norm with a gain of 1.2 |
| Feed-forward | 4 × 1,024, ReLU² |
| Extras | x0 skip (learned residual and input weights per layer), smear (gated previous-token embedding, never into an `<|eos|>`), two value-embedding tables (layers 0/22 and 1/23, gate 3·sigmoid), backout of the middle layer's state |
| Output | untied output matrix, logits soft-capped at 15 |
| Vocabulary | 49,152 byte-level BPE tokens, bilingual (EN/DE), ChatML special tokens (`<|eos|>` 0, `<|im_start|>` 1, `<|im_end|>` 2); `data/lm2_tokenizer.json`, SHA-256 `3f0ebf25…290380c` |
| Parameters | 503,316,938 stored: 301,990,272 in the 24 blocks, 50,331,648 each for input embedding and output matrix, 2 × 50,331,648 in the value embeddings, 74 scalars. Per token: 352,321,920 (blocks + output matrix) |

## Training data

Built on free GitHub runners (`.github/workflows/sela2_data.yml`) into a private draft release; every file is pinned by
SHA-256 in `results/sela2/data/manifest.json`. Licences and duties per source: `docs/DATA_LICENSES.md` (Sela-2).

| Phase | Sources (share of the tokens in that phase) |
|---|---|
| Stable phase (70 %) | FineWeb-Edu 30 %, its high-quality part 12 %, DCLM 24 %, C4 8 %, Cosmopedia v2 7 %, Wikipedia EN 6 %, PG-19 4 %, FineWeb2-HQ German 7 %, Wikipedia DE 2 % |
| Decay phase (30 %) | the same sources re-weighted, plus chat conversations (EN 15 %, DE 3 %), grounded QA with cited sources (10 %) and identity conversations (1 %) |
| Fine-tuning | held-apart chat, grounded-QA and identity conversations; loss on the assistant's tokens only |

Shares are capped by what each source holds (no source is silently repeated). Chat: SmolTalk (smol-magpie-ultra,
everyday conversations, smol-rewrite, smol-summarize), SmolTalk2 Qwen3-32B system chats and German multilingual
answers, OpenAssistant 2, Dolly. Grounded QA in the app's format: SQuAD v2, HotpotQA (both supporting paragraphs
plus distractors), GermanRAG, Dolly closed QA. All evaluation texts were filtered out before training (13-word
windows); a token-level audit after the run reports clean-subset scores.

## Training procedure (planned; actual values in `results/sela2/pretrain_meta.json`)

| | |
|---|---|
| Tokens | as many as fit before the cost brake: ≈ 2.7–2.9 B at ≈ 150 k tokens/s (the target is fitted to the measured speed) |
| Batch | 2^19 tokens per step (micro-batch 16 × 2,048 on one H100) |
| Optimiser | nanochat MuonAdamW: Muon (Polar Express, NorMuon, cautious weight decay) for the block matrices, AdamW for embeddings, output matrix and scalars |
| Schedule | 40 warm-up steps, constant, linear decay over the last 65 % to 5 % (the decay finishes before the deadline: time-aware), Muon momentum 0.85 → 0.97 → 0.90 |
| Safeguards | divergence → continue at half the learning rate; no loss drop by step 300 → restart once at half the rate |
| Fine-tuning | warm optimiser state, 0.8 × the base rate, decaying over the second half, Muon without weight decay, until its deadline |
| Precision | bf16 autocast, FlexAttention with per-document masks (dense attention as fallback), fp32 master weights |

## Intended use

- Chat and writing help in the ENGRAMM desktop app, offline on the user's computer (NumPy, int8 weights).
- Answers from ENGRAMM's knowledge pack: the app gives Sela-2 the sources; an answer is shown only when every number,
  number word and English name in it occurs in a cited source (`engramm.lm.sela_chat.verify`), else ENGRAMM's own
  answer is shown. Safety, tool, memory and clarifying replies stay ENGRAMM's.

## Limitations

- About 1 % of GPT-3 Medium's training compute. Measured: the base model scores above GPT-2 medium on the pooled
  benchmarks, the chat model between GPT-2 small and medium; chat is short and fluent, weakens over many turns, and
  **makes up facts without sources** (see *Results*).
- The source check cannot see wrongly related facts (a correct name next to a correct number from another sentence).
- German is an attempt: the German share of the data is small.
- No safety tuning beyond the data choice; the app keeps its own safety layer in front of the model.

## Licences

- Weights: treated as CC BY-SA 4.0 as a precaution (Wikipedia, SQuAD, HotpotQA, Dolly).
- **Before any distribution of the weights**, a decision is needed: smol-magpie-ultra and everyday conversations were
  generated with Llama 3.1, whose licence asks that a distributed model trained on its outputs carries "Llama" at the
  start of its name and shows "Built with Llama". Options: rename, or redo the decay and fine-tuning from the
  continuation state without those conversations (≈ 8 $). Details: PLAN §12.5.
- Qwen-generated parts (SmolTalk2) are Apache 2.0.

## Results

The run: one H100 SXM, 18 Oct 2026, 00:28–06:12 UTC (≈ 5.7 h at 3.99 $/h, ≈ 23 $ including the failed first start
with a token lacking the Workflows right). Pretraining 3.06 B tokens in 4.93 h at 172 k tokens/s (FlexAttention, no
divergence, no restart), decay from 1.07 B tokens on, then 657 fine-tuning steps on 78.7 M assistant tokens. Records:
`results/sela2/pretrain_meta.json`, `sft_meta.json`, `eval_base.json`, `eval_chat.json`; the evaluation workflow
(run 39103177423) wrote `bench.json`, `chat_eval.json`, `ifeval.json`, `squad.json`, `int8.json`, `contamination.json`,
`app_speed.json`.

**Text prediction** (bits per byte, lower is better, held-out documents):

| | Sela-2 base | Sela-2 chat | Sela-1 |
|---|---|---|---|
| test documents of the v5 runs (`lm_test`, 1,137 docs) | **0.924** | 1.155 | 0.989 |
| WikiText-103 test | 0.855 | 1.118 | – |
| FineWeb-Edu / Wikipedia EN / DCLM / C4 (validation) | 0.847 / 0.859 / 1.001 / 0.983 | 1.040 / 1.146 / 1.242 / 1.182 | – |
| FineWeb2 German / Wikipedia DE | 0.948 / 0.869 | 1.311 / 1.396 | – |

**M3, zero-shot benchmarks** (one harness for all models; acc_norm, acc for WinoGrande and LAMBADA; in %):

| Task | Sela-2 base | Sela-2 chat | Sela-1 | GPT-2 small | GPT-2 medium | Pythia-160M | Pythia-410M |
|---|---|---|---|---|---|---|---|
| HellaSwag | **41.2** | 35.7 | 32.7 | 31.3 | 39.9 | 30.7 | 40.7 |
| PIQA | 65.9 | 63.2 | 64.7 | 62.5 | 66.1 | 62.0 | **67.5** |
| ARC-Easy | **52.0** | 44.7 | 39.9 | 40.5 | 43.7 | 40.4 | 47.0 |
| ARC-Challenge | **26.9** | 24.4 | 23.3 | 22.4 | 25.7 | 24.5 | 23.9 |
| WinoGrande | **54.9** | 51.4 | 50.6 | 50.4 | 53.0 | 52.4 | 52.8 |
| OpenBookQA | **32.4** | 30.0 | 26.0 | 26.6 | 28.8 | 27.0 | 29.2 |
| LAMBADA | 42.7 | 34.7 | 27.8 | 33.7 | 43.9 | 35.7 | **50.5** |
| MMLU (cloze) | **28.8** | 28.2 | 26.1 | 26.7 | 27.7 | 26.7 | **28.8** |
| **Pooled** (first six) | **45.5** | 41.6 | 39.5 | 38.9 | 42.9 | 39.5 | 43.5 |

The contamination audit found 0–0.6 % of items per task in the trained tokens (MMLU 84 of 14,042, HellaSwag 9 of
10,042, none in PIQA, WinoGrande, OBQA, ARC-Challenge); on the clean items the pooled score is unchanged (45.5).

**Pre-registered criteria:**

| Criterion (`docs/PREREG_SELA2.md`) | Result | Met? |
|---|---|---|
| Stage "GPT-3 Small level": pooled(base) above GPT-2 small with the 95 % interval above 0, and not below Pythia-160M | +6.6 points over GPT-2 small (95 % CI 5.7–7.6), +6.0 over Pythia-160M | **yes** |
| (reported) HellaSwag against GPT-3 Small (33.7) | 41.2 | above |
| M5 loops < 5 % | 0 % | yes |
| M5 replies ending at the token limit < 5 % | 9 % (EN 3.3 %, DE 17.5 %) | **no** |
| M5 role leaks < 1 % | 0 % | yes |
| M5 median reply length ≤ 120 tokens | 36 | yes |
| M6 IFEval (prompt-level loose) chat minus base ≥ +8 points | 18.3 − 13.5 = +4.8 | **no** |
| M7 SQuAD v2 with the oracle paragraph: HasAns F1 ≥ 50 | 34.7 (48.3 on the answers the app's check lets through, 70 % of them) | **no** |
| M7 NoAns: abstains on ≥ 60 % of unanswerable questions | 47.6 % | **no** |
| M10 int8 costs ≤ 0.005 bits per byte | +0.001 | yes |
| M8 (hand count of 200 grounded answers) | not done yet | – |

What the numbers say:
- **The base model is the success of the run.** On the pooled score it is ahead of GPT-2 medium and Pythia-410M,
  models of the same size trained on 3–100 times more tokens; its HellaSwag (41.2) lies between GPT-3 Small (33.7)
  and GPT-3 Medium (43.6, values from the GPT-3 paper, slightly different format). It trails on LAMBADA.
- **The chat fine-tuning cost more than it gave.** It lowered every benchmark (pooled −3.9 points), raised the
  bits per byte on plain text by 0.23 and made German worse (chat loss 1.59 → 1.68), while IFEval rose only 4.8
  points and grounded QA stayed below its targets. The cause is in the recipe, not the data: 657 steps at 0.8 × the
  base learning rate with no plain text mixed in. A shorter, gentler fine-tuning with replayed pretraining text is
  the obvious next experiment (it needs only the base model, about 30 minutes of H100 time).
- **Chat behaviour is clean in English:** no loops, no role leaks, short replies; German replies are fluent but often
  run to the token limit and their content is weak.
- In the app the int8 file loses nothing measurable and writes about 21 tokens per second on 4 cores. (The memory
  figure of that speed test, 4.35 GB, is the whole test process, not the model; the model file is 505 MB.)

## After the run: the chat file of the app (18 Oct 2026, `docs/PREREG_SELA2.md` §5)

The fine-tuning restarted at 0.8 × the peak learning rate, with the optimizer state of the end of pretraining. That
undid part of the annealed pretraining: held-out English conversations improved only from 1.14 to 1.11 nats, German
got worse (1.59 → 1.68), and plain text lost about 0.2 bits per byte. The base model had already seen 232 M tokens
of conversations in the decay phase. Five candidates were therefore compared by a rule fixed before the measurement
(`results/sela2/variants/selection.md`, workflow run 39121119678): the chat model, the base model, and weight mixes
(1 − α) · base + α · chat (`experiments/sela2_merge.py`).

| Candidate | M3 pooled | vs base [95 %] | M5 limit (3 seeds) | median tokens | IFEval loose | HasAns-F1 | NoAns | app shows (answerable) | checks |
|---|---|---|---|---|---|---|---|---|---|
| chat | 41.6 | −4.0 [−4.9, −3.0] | 10.0 % | 36 | 18.3 | 34.7 | **47.6 %** | 70 % | 3/7 |
| base | 45.5 | – | 14.3 % | 35 | 13.5 | 52.9 | 32.2 % | 90 % | 4/7 |
| **mix30** (α = 0.3) | **45.7** | +0.2 [−0.4, +0.8] | 28.7 % | 59 | 15.5 | **63.9** | 31.4 % | **91 %** | **4/7** |
| mix50 | 44.6 | −0.9 [−1.6, −0.2] | 25.0 % | 50 | 15.7 | 60.3 | 31.6 % | 91 % | 4/7 |
| mix70 | 43.4 | −2.1 [−3.0, −1.3] | 19.0 % | 46 | 16.5 | 53.0 | 34.2 % | 86 % | 4/7 |

- The rule picks **mix30**: as many checks as the others, then the highest HasAns-F1. The app ships it as Sela-2.
- Repeating the registered M5 run of the chat model gave identical replies, so the measurement is reproducible.
- **What mix30 gains:**
  - the base model's knowledge (pooled 45.7; OpenBookQA 34.6, the best of all models in the table above);
  - much better grounded answers: F1 64 instead of 35, and the app's check lets 91 % of them through instead of 70 %.
- **What it loses:**
  - abstentions on unanswerable questions (31 % instead of 48 %);
  - longer replies: 29 % run into the 160-token limit, against 10 % for the chat model.
- No candidate meets M6 (+8 IFEval points) or M7 NoAns (≥ 60 %).

**In the app** (`results/sela2/app_eval/`, the 100 M5 prompts through the app's chat service with the real lite
pack; ENGRAMM handles memory, safety and retrieval first):
- Guards on free replies:
  - a new sample after a reply in the other language or an unchanged rewrite;
  - fixed true answers to "who made you / are you a human / do you have feelings";
  - a begun list item dropped at the limit;
  - 240 instead of 160 tokens per reply.
- Prompts with an automatically detected problem:

  | Model | without guards | with guards | of which: long replies cut at a sentence end |
  |---|---|---|---|
  | chat model | 12 | 8 | 6 |
  | mix30 | 16 | 15 | 14 |

- The detectors do not see wrong facts. Free replies of both files are fluent but often wrong in content, and German
  replies are weak.
- The app evaluation also found one real fault: Sela-2 rewrote ENGRAMM's "Your name is Sam." as "My name is Sam [1]."
  Answers from the user's own memory now stay ENGRAMM's.

**Next: Sela-2.1** (`docs/PREREG_SELA2.md` §6, `docs/SELA21_ANLEITUNG.md`):
- the base model fine-tuned again at 3 % and 10 % of the base rate instead of 80 %;
- a fresh optimizer, warm-up, German conversations three times;
- ≈ 3 $ on one H100, chosen by the same rule against the candidates above.

## Speed in the desktop app (18 Oct 2026)

A user reported about five minutes for a reply to "How are you?" on Windows. The app expanded every int8 matrix to
float32 at load (1.4 GB) and read all of it per token through OpenBLAS; on a busy 4-core machine that gave 1.7
tokens/s, and a reply of up to 240 tokens with up to three tries took minutes. The app now runs
`SelaChat(fast=True)` (`engramm/lm/q8.py`, `engramm/lm/sela_chat.py`): int8 matrices stay int8 and are multiplied by
numba kernels on a small thread pool, prompts attend in causal chunks, and one key/value cache is kept between calls
so a turn computes only the tokens after the prefix it shares with the previous call (a retry: one token). The
registered measurements keep the exact float32 path (`fast=False`).

| Full-size model (synthetic int8 weights), busy 4-core machine | float32 path | fast path |
|---|---|---|
| load | 10 s | 4–5 s |
| memory (peak) | 1.9 GB | 0.97 GB |
| prompt of 200 tokens | 7.9 s | 2.3–3.6 s |
| generation | 1.7 tokens/s | 10.9 tokens/s |
| 16-turn chat, mean of the last 8 turns (60-token replies) | 14.9 s | 9.8 s |

Frozen server on the Windows CI runner (4 cores, `mix30`, Test-Build 6, run 39139087492, times per question incl.
ENGRAMM's turn): "How are you?" 0.6 s (9 tokens), "Wie geht es dir?" 1.9 s (24 tokens), "Danke, tschüss!" 1.1 s;
the same five questions with the float32 path took 28 s in all (Test-Build 4). Independent review of the change:
12 agents, the confirmed findings (prompt recomputed every turn and retry, quadratic prompt attention, slow load
transpose, missing numba in a CI check) are fixed. Since Test-Build 7 (run 39156630216) free replies stream to
the page as they are written (`POST /api/chat/stream`); Windows CI: "How are you?" 0.6 s (13 tokens),
"Wie geht es dir?" 1.8 s (31 tokens).

## Sela-2.1: gentle fine-tuning from the base model (18 Oct 2026, `docs/PREREG_SELA2.md` §6)

Fresh optimizer from `sela2_basis_bf16.pt`, 3 % or 10 % of the base learning rate (the first run used 80 % with the
pretraining optimizer state), 20 warm-up steps, German conversations three times. H100 pod, ≈ 3.9 $
(`results/sela21/`).

| Candidate | lm_test bpb | M3 pooled (Δ base) | Limit | Median | IFEval (Δ base) | HasAns-F1 | NoAns | checks |
|---|---|---|---|---|---|---|---|---|
| base | 0.924 | 45.5 | 14.3 % | 35 | 13.5 | 52.9 | 32.2 % | 4/7 |
| chat (first run) | 1.155 | 41.6 (−4.0) | 10.0 % | 36 | 18.3 (+4.8) | 34.7 | 47.6 % | 3/7 |
| **mix30** (app) | – | 45.7 (+0.2) | 28.7 % | 59 | 15.5 (+2.0) | 63.9 | 31.4 % | 4/7 |
| s21lr03 | 0.930 | 45.5 (−0.0) | 12.7 % | 40 | 13.1 (−0.4) | 53.7 | 31.8 % | 4/7 |
| s21lr10 | 0.944 | 45.0 (−0.6) | 9.0 % | 36 | 16.3 (+2.8) | 57.9 | 31.2 % | 4/7 |

The gentle recipe keeps the base model's knowledge (as expected in §6), but by the registered rule (most checks,
then HasAns-F1, then pooled M3) mix30 stays the app's chat file (`results/sela2/variants21/selection.md`).

## Learning from the user (19 Oct 2026, `docs/PREREG_SELA2.md` §7–§12)

The app can show Sela-2 the user's facts from ENGRAMM's memory (A), keep ENGRAMM's own turns in Sela-2's thread (B), and
mix in a kNN memory of the user's wording (C).

**First version (§7, `results/sela2/learn/`):**
- Facts used went from 0 % to 52.5 % with A+B.
- Sela-2 repeated the fact lines as its own ("Ich heiße Lea …") in 7 replies.
- Layer C copied "alot" and "garnicht" into 6 replies and gained only 0.55 %.
- By the rule all layers stayed off.

**Second version (§8, registered before its test on 40 fresh users, `results/sela2/learn_v2/`):**
- **A:** The facts go into the system prompt as a labelled note about the user. A guard cuts reply sentences that
  claim a user fact as Sela-2's own.
- **C:** Before a message is learned, the model checks it for mistakes on the whole text:
  - words written together ("alot" → "a lot");
  - one letter too many or too few ("wiederrum" → "wiederum");
  - near forms that make the whole text at least 8× likelier ("she go" → "she goes").
  A marked word is never learned, and a sentence with a clear mistake is not learned at all. Mixing setting:
  share 0.10, similarity floor 0.90, sharpness 0.01.
- **Result:** facts used +35 points, 0 copied mistakes, 0 role confusions, language memory +1.45 %, writing speed
  0.97 × without C.
- **Rule outcome:** all layers on.

**Third check (§9, 40 more fresh users, `results/sela2/learn_v3_*`):**
- The note written as sentences ("The user's name is Sam. The user's dog is called Rex.") more than doubled fact use:
  +44.4 points against +20.0, German 40 % against 14 %.
- Layer C gained only 0.78 % on these users.
- By the registered rules C is **off** again (`ENGRAMM_SELA2_KNN=1` turns it on), and A+B stay **on**
  (`ENGRAMM_SELA2_LEARN=0` turns them off).
- The sentence form was not adopted, because the rule wrongly tied it to C's criterion. It is re-tested in §10.

**Repeat for the note's form (§10, 40 more fresh users, `results/sela2/learn_v4_*`):**
- Sentences beat labels again: facts used +34.4 against +23.8 points, with no copied mistakes and no role confusion.
- The sentence form is now the **default** (`ENGRAMM_SELA2_NOTE=labels` restores the labels).
- Layer C gained 0.09 % on these users and stays off.

**Language memory on real people (§11, 40 real test users from WildChat-1M, `results/sela2/learn_real/`):**
- Why C looked weak before: the synthetic held-out sentences of §8–§10 hardly reused the users' wording (2.7–5.3 % of
  their word pairs; real users 12.9 %). A memory of someone's wording can only help where they reuse it; the mixing
  settings were not the problem (none of 60 did better).
- The test users are real people's messages to a chatbot (WildChat-1M, ODC-By, not in Sela-2's training data), split
  from the development users by person; only their IDs and hashes are in the repository.
- The word check no longer treats a left-out ending or first letter as a misspelling ("parts" → "part", "lebte" →
  "lebt"); chosen on the development users by a rule fixed before the result.
- Result: held-out messages 1.59 % likelier with the memory, 1 copied mistake (limit 2), no role confusion, writing
  speed 0.97 × without C.
- C is now **on** by default (`ENGRAMM_SELA2_KNN=0` turns it off).

**Facts only where they belong (§12, 40 more real test users, fact questions written blind by an independent agent,
`results/sela2/learn_real2_*`):**
- With every fact in the note, a quarter of the replies brought in facts nobody had asked for (24.7 %; in the app 12
  of 96 replies after learning one user, often as Sela-2's own: "Hi! I like to play with my dog Rex.").
- The note now holds only the facts the message is about (its value or its subject named in the message; "What do you
  know about me?" shows all). On the same users: facts used as often where asked (+30.2 points either way), unasked
  facts in 0.0 % of the replies, 1 of 96 in the app. This is the default (`ENGRAMM_SELA2_FACTS=all` restores the old
  behaviour); the guard still checks every fact.

**Limits:**
- Cue words can misfire on requests that are not about the user ("Summarize this email …" showed the user's name) and
  miss some phrasings (English fact questions without a cue word get no note).
- 10 of 120 built-in mistakes still reached the memory in §8 (none appeared in a reply); in §11, 6 of 120 were stored
  and one grammar mistake ("ich habe gegangen") appeared in a reply although the memory had dropped it.
- Before §12, the fact note was often used where it did not fit ("Niklas und Bruno machen gerne gemeinsam Lasagne.").
- Pure grammar mistakes with correct words ("ich habe gegangen") are not reliably caught.
- German facts are used less often than English ones (with the sentence note 27.5–40 % against 41–49 %).
- Sela-2 sometimes printed the note itself; since the measurement a guard removes such lines.

