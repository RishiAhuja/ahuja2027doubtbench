# CODS 2026 paper package

This is a clean, double-anonymous ACM `sigconf` draft for the CODS 2026 archival main track. The manuscript is now organized around the working benchmark name **DoubtBench** and is separate from the pre-existing `submissions/caisc2026` manuscript.

## Build

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The task-overview and benchmark-construction figures are PDF assets under `figures/` (`doubtbench-task-overview.pdf`, `doubtbench-construction.pdf`), included via `\includegraphics`. Legacy TikZ sources remain beside them for reference. `make_figures.py` is retained for later result plots; it reads audited CSVs under `outputs/` and does not contain copied result values.

## Template provenance

- Required format: ACM `sigconf`.
- Downloaded package: `../template_download/acmart-primary.zip`.
- Source mirror: CTAN `macros/latex/contrib/acmart.zip` (the ACM endpoint returned a Cloudflare challenge in the build environment).
- SHA-256: `5011d4a698b993ffd4c9a6a24cf4cde7dc9deb4a7ec2dc357dbbe4ec15085618`.
- `acmart.cls` and `ACM-Reference-Format.bst` were generated/copied from that package for a portable build.

## Submission status

The source is anonymous and uses the required unmodified `\documentclass[sigconf]{acmart}` declaration. The benchmark-first pre-results build is seven pages including 22 cited references. The frozen result slots, final result figures, and error analysis are expected to bring the manuscript to approximately 7.5--8 body pages plus references. Before submission, verify submission metadata, author ordering, conflicts, PDF anonymity/metadata, and the final conference page-limit interpretation.
