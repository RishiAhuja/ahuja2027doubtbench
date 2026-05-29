# CAISc 2026 Submission Draft

Primary draft:

- `paper/main.tex`
- `paper/main.pdf`

Build:

```bash
cd submissions/caisc2026/paper
python make_figures.py
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Official template files are stored under:

- `template_download/caisc_template.zip`
- `template_source/caisc_2026.tex`
- `template_source/caisc_2026.sty`

The draft uses the default submission mode in `caisc_2026.sty`, which anonymizes the author block and includes line numbers.
