# DoubtBench supplementary material

`supplement.tex` is the root LaTeX file. The folder is self-contained for an
Overleaf upload: it includes the ACM class, the generated tables, and all three
figures used in the appendix.

Compile locally with:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error supplement.tex
```

The numerical tables are generated from the archived analysis CSV files by
`generate_tables.py`. The generated `.tex` tables are already included, so the
Python script is not required when compiling on Overleaf.
