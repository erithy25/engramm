# ENGRAMM · Sela-2

**A small language model, trained from scratch for about $23, that runs offline on an ordinary CPU and learns from its
user without learning the user's mistakes.**

[Paper (PDF)](paper/main.pdf) · [Deutsche Kurzfassung](paper/summary_de.md) · [Preregistration](docs/PREREG_SELA2.md) ·
[Model card](docs/MODEL_CARD_SELA2.md) · [Provenance](docs/PROVENANCE.md)

ENGRAMM is an assistant that runs entirely on the user's own computer. Sela-2 is its chat model: a decoder-only
transformer with 503 million stored parameters (352 million per token), its own bilingual tokenizer and random
initialisation, trained on one rented NVIDIA H100 in about 5.7 hours. This repository holds the paper about how Sela-2
learns from its user, the preregistration it followed, and every result file the paper's numbers come from.

## The question

A model that learns from what its user writes also learns the user's typos ("definately"), merged words ("alot") and
grammar slips ("she go"), and may write them back. Can a small on-device model pick up a user's facts and wording but
not their mistakes?

## What Sela-2 does

- **Facts.** The assistant extracts the user's facts ("My dog is called Rex") and shows Sela-2 a short note, with only
  the facts the current message is about.
- **The conversation.** Earlier turns stay in context.
- **Wording, with a mistake filter.** A k-nearest-neighbour memory over Sela-2's own hidden states stores what followed
  each context in the user's messages. Before anything is stored, the model compares the message with small variants of
  each word (split, one letter more or less, a near form). If a variant makes the whole message much more likely, the
  word counts as a mistake and is not learned, and a sentence with a clear mistake is not learned at all.

Everything learned stays on the user's computer and can be deleted exactly.

## Results

| | |
|---|---|
| Training cost | about $23 of GPU time (one H100, 5.7 h, 3.06 B tokens) |
| Base model, six zero-shot benchmarks (pooled) | 45.5, above GPT-2 medium (42.9) and Pythia-410M (43.5) |
| Inference | int8 on a CPU, about 35 tokens/s on a 4-core GitHub runner |
| Use of the user's facts where a reply calls for them | 0 % without the note, 20–53 % with it |
| Injected mistakes repeated in replies | from the second version on, at most 2 replies per run |
| Memory on real users (WildChat-1M), held-out messages | −1.59 % bits per byte (95 % CI 0.50–2.91), −3.07 % in a second group |
| Unrequested personal facts in replies | 24.7 % → 0.0 % with the relevance filter, fact use unchanged |

Every version was **preregistered and measured once on 40 users it had never seen**: six measurements, 240 users, 80 of
them real people. The paper reports all of them, including a failed first version, a flawed decision rule and a
counting error. Its most transferable finding concerns evaluation: the memory's gain fell from 3.39 % to 0.09 % across
synthetic user groups, and the evidence points to our own synthetic test sentences reusing fewer of the users' words,
not to the memory. Real users revealed it.

## Repository

| Path | Contents |
|---|---|
| `paper/` | the paper (`main.pdf`, LaTeX source, bibliography), `make_figures.py`, figures and generated tables |
| `docs/PREREG_SELA2.md` | the preregistration: every rule written before its measurement, results appended (German) |
| `docs/MODEL_CARD_SELA2.md`, `docs/MODEL_CARD_SELA1.md` | model cards of Sela-2 and its predecessor |
| `docs/DATA_LICENSES.md` | the training data and their licences |
| `docs/PROVENANCE.md` | where each registration, measurement and decision sits in the development history |
| `results/sela2/` | every result file of the measurements, benchmarks and evaluations |
| `data/sela2/` | the synthetic test users, the blind-written probes and the selection of real users (IDs and hashes only) |

The documents in `docs/` are copied unchanged from the development repository. Where they say "this repository" or name
code files, they mean that repository.

## Reproduce the paper's numbers

```
pip install numpy==2.4.6 matplotlib==3.11.2
python paper/make_figures.py
```

The script reads only `results/` and `data/`, recomputes all 207 numbers, every table and the three plotted figures,
checks itself against the result files, and produces byte-identical output. Build the PDF with
`cd paper && tectonic main.tex` or pdfLaTeX (`paper/README.md`).

The real users' messages are not in this repository: it keeps them only as SHA-256 and length, and the measurement
workflow rebuilt them from the public WildChat-1M dataset.

## Code and weights

The application, the training pipeline and the weights are kept in a private development repository. Reviewers who
want to check a result against the code can ask for access by opening an issue.

## How this was built

ENGRAMM was built by Erik Thye with an AI coding agent (Claude Code by Anthropic): the agent wrote most of the code,
ran the experiments and drafted the documents and the paper under his direction; the code reviews and the blind test
probes came from separate instances of the same model. He set the goals, the constraints and the budget and is
responsible for the claims. Details: section 9 of the paper.

## Cite

```bibtex
@misc{thye2026learning,
  author = {Thye, Erik},
  title  = {Learning from the User Without Learning Their Mistakes: A Preregistered Study of On-Device
            Personalisation for a Small Language Model},
  year   = {2026},
  url    = {https://github.com/erithy25/engramm}
}
```

## Licence

Paper, documents, figures and result data: [CC BY 4.0](LICENSE). `paper/make_figures.py`: Apache License 2.0
([LICENSE-CODE](LICENSE-CODE)). The selection of WildChat-1M users is derived from a dataset under ODC-By
(Zhao et al., ICLR 2024).
