# Paper: Learning from the User Without Learning Their Mistakes

*A Preregistered Study of On-Device Personalisation for a Small Language Model*

This folder holds the LaTeX sources of the paper about how Sela-2 learns from its user (docs/PREREG_SELA2.md §7–§12),
the script that computes every number in it from the repository's result files, and the built PDF.

| File | What it is |
|---|---|
| `main.tex` | the paper (two-column article, 10 pt; appendix in one column) |
| `references.bib` | the bibliography; every entry was checked against the publisher, the proceedings or arXiv |
| `make_figures.py` | reads `results/sela2/…` and `data/sela2/…` and writes `figures/` and `generated/` |
| `figures/*.pdf` | the three plotted figures (vector PDF); Figure 1 is drawn in TikZ inside `main.tex` |
| `generated/numbers.tex` | every number the text cites, as `\stat{key}` (a missing key prints a red `??key??`) |
| `generated/tab_*.tex` | table bodies, read by `\tablebody{…}` in `main.tex` |
| `generated/stats.json` | all computed values, including the bootstrap intervals, in machine-readable form |
| `main.pdf` | the built paper |
| `summary_de.md` | a one-page summary in German for readers without a background in the field |

## 1. Recompute the numbers and figures

From the repository root, with Python 3.11, NumPy and Matplotlib (built with Python 3.11.15, NumPy 2.4.6,
Matplotlib 3.11.2):

```
python paper/make_figures.py
```

The script only reads the result and data files named in Appendix A of the paper and writes `paper/figures/` and
`paper/generated/`. It checks itself against the result files as it goes (for example, that its recount of each run's
criteria matches the run's `summary.json`) and stops on any mismatch. The bootstrap uses a fixed seed per quantity, so
two runs produce byte-identical outputs. It runs in well under a minute. The real users' texts are not
needed: the result files keep them only as hashes, and the one value that would need them (12.9 % word-pair reuse of
the real development users) is quoted from the preregistration.

## 2. Build the PDF

Any TeX Live 2023 or later with the usual packages (newtx, microtype, tikz, algorithm/algpseudocode, booktabs,
tabularx, float, enumitem, caption, natbib, hyperref, cleveref):

```
cd paper
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

or `tectonic main.tex`. `main.pdf` was built with Tectonic 0.15.0 (XeTeX engine); the sources are plain ASCII and
use only standard packages, so the pdfLaTeX route above should work too, but it was not tested here. The bibliography
style is `abbrvnat`.

For arXiv: upload `main.tex`, `main.bbl` (made by the build above; arXiv does not run BibTeX), `figures/` and
`generated/`. The abstract is under arXiv's 1,920-character limit.

## 3. Before submitting

- Add the author's affiliation (school or university) under `\author{Erik Thye}` if wanted.
- §9 (AI assistance) says what the repository records show: an AI coding agent wrote the code and most documents, and
  the code reviews and the blind §12 probes came from separate instances of the same AI model. Check that the
  sentence about your own role says exactly what you did, and rewrite the introduction and discussion in your own words.
- The reproducibility statement offers code and weights on request; it promises no public link.

## 4. Provenance

Appendix A of the paper maps every table and figure to its source files. Numbers in the text come from
`generated/numbers.tex`; the few that are quoted rather than computed (training figures of Sela-2 from
`docs/MODEL_CARD_SELA2.md`, the 12.9 % reuse of the real development users, the 85 review findings and 246/320 from
`docs/PREREG_SELA2.md`) name their source in the text or in Appendix A. Where the project's prose documents disagree
with the result files, the paper follows the result files and lists the differences in Appendix G.
