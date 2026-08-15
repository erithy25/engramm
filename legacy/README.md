# legacy/ — recovered code fragments (non-functional)

**Do not run or import anything in this directory.** It exists as reference
material for the reimplementation, nothing more.

## What these files are

In July 2026 the original working tree (`/Users/erikthye/engramm/`) was lost.
The source code had never been fully committed to git. A recovery attempt
(commit `a1af719`, "Recover ENGRAMM") reconstructed files from Claude Code
edit logs (`*.edits.json`, now archived in `docs/archive/edit-logs/`). An edit
log only contains the text passages that were touched by an edit operation —
so the recovery could restore exactly those passages, and nothing else. That
is why most files here begin mid-function and cannot be parsed.

## Fragments (incomplete — none runnable)

| File | Recovered | Original (per docs) | What the fragment contains |
|---|---|---|---|
| `engramm.py` | 17 lines | 469 lines | one method (`learn_online`, the T2 perceptron update) — no class header, no imports, none of `ItemMemory`, `Engramm`, `hamming`, `sim_from_dh`, `classify`, `learn`, `consolidate` |
| `m1b_mnist.py` | 9 lines | full MNIST harness | tail of the seed-evaluation printout; no data loading, no encoder, no training loop |
| `m2_stream.py` | 10 lines | M2 stream harness | the `evaluate()` hit-counting function; `load_banking77()` is missing although other files import it |
| `m3.py` | 21 lines | M3 harness | `main()` with argparse only; parses by accident, crashes on call (`cmd_*` functions missing) |
| `m5_compare.py` | 10 lines | M5 verdict script | final outcome classification; the inputs it compares are never computed |
| `m5_engramm.py` | 9 lines | M5 ENGRAMM harness | meta-JSON writing tail; `fewshot_split()` and `load_clinc()` missing although imported elsewhere |

The WiLI harness (M1, the 79.30 % result) and `m0_bench.py` / `m2b.py` were
not recovered at all — no fragment of them exists.

## Complete files (parse fine, cannot run without the missing core)

| File | Status | Notes |
|---|---|---|
| `m5_baselines.py` | **complete (279 lines)** | M5 opponent baselines B1 (bge + FAISS + Qwen-3B RAG) and B3 (LoRA on Qwen-0.5B). Blocked only by its imports from the fragment files. **Can serve as a template for the future baseline harness** — its structure (task loading, meta-JSON schema, energy measurement) is intact. |
| `spielwiese.py` | complete | interactive demo; imports the missing `Engramm`/`ItemMemory` |
| `vox_fusion-2.py` … `vox_fusion-5.py` | 2–4 complete, 5 is a fragment | four successive saved versions of `vox_fusion.py` (VOX side project: local Qwen as "mouth", ENGRAMM as fact memory). No file is marked canonical; `-5` is 13 lines of regex patterns only. |

Why these files survived in full while the core did not is not fully
documented: no `.edits.json` exists for any of them in
`docs/archive/edit-logs/` (those logs only record `Edit` operations, and only
for the fragment files). The plausible explanation — they were created in
single `Write` operations whose payloads the recovery session still had —
cannot be verified from what is in this repository. What *is* verifiable:
they arrived complete in the recovery commit `a1af719` and are preserved here
byte-identically.
