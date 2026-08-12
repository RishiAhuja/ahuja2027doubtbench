# DoubtBench CODS 2026 paper

This folder can be uploaded directly to Overleaf.

- Main document: `sample-sigconf.tex`
- Compiler: pdfLaTeX
- Bibliography: BibTeX

CODS explicitly asks authors to use `sample-sigconf.tex` as the Overleaf main
document. Overleaf normally detects it because it is the only `.tex` file in
this package. If needed, set it under **Menu -> Main Document**.

For a local build:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error sample-sigconf.tex
```

The manuscript is anonymous and uses the required ACM
`\documentclass[sigconf]{acmart}` format. The bundled class is production
`acmart` v2.19 (2026-06-27), downloaded from the synchronized CTAN release.
