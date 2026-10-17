# ENGRAMM Sela-2 — model card

**Status: written before the GPU run (17 Oct 2026).** Architecture, data, procedure, intended use and licences are
fixed; every number under *Results* is filled in from the run's records afterwards, and the success criteria are the
pre-registered ones in `docs/PREREG_SELA2.md`.

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

- About 1 % of GPT-3 Medium's training compute: expect benchmark scores between GPT-2 small and medium, short and
  fluent chat that weakens over many turns, and **made-up facts without sources**.
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

Filled in after the run from `results/sela2/` (pod: M1, M2, M4) and the evaluation workflow
(`.github/workflows/sela2_eval.yml`: M3, M5, M6, M7, M10, contamination audit).
