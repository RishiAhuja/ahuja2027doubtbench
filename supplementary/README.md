# DoubtBench appendix

The appendix for *DoubtBench: Does Self-Doubt Help Language Models—or Just
Make Them Check?* contains the complete task inventory, prompt interventions,
scoring protocol, result tables, and diagnostic analyses.

Read the included [PDF](supplement.pdf), or compile the
[LaTeX source](supplement.tex) with a TeX distribution providing `latexmk`
and the packages used by the source. The ACM class, bibliography style,
tables, and figures are included here.

From the repository root:

```bash
latexmk -cd -pdf -interaction=nonstopmode -halt-on-error supplementary/supplement.tex
```

The command writes `supplement.pdf` in this directory. The source includes
the tables in [`tables/`](tables/) and PDF figures in [`figures/`](figures/).

See the [benchmark protocol](../BENCHMARK.md),
[result-table guide](../results/README.md), and
[usage guide](../USAGE.md) for the corresponding data and code.
