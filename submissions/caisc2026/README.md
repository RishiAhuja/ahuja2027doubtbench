# CAISc 2026 Submission Draft

Primary draft:

- `paper/main.tex`
- `paper/main.pdf`

Build:

```bash
# from repo root, one-time deps for figure generation
python3 -m venv .venv && .venv/bin/pip install matplotlib pandas numpy

cd submissions/caisc2026/paper
../../../.venv/bin/python make_figures.py
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Figures are regenerated from the final EXP-16 analysis tables in
`outputs/analysis/exp16_final_mechanism_20260529/` and the budget-ceiling
pilot in `outputs/EXP-16/exp16_cognitive_pilot_20260525_001616/`.

Official template files are stored under:

- `template_download/caisc_template.zip`
- `template_source/caisc_2026.tex`
- `template_source/caisc_2026.sty`

The draft uses the default submission mode in `caisc_2026.sty`, which anonymizes the author block and includes line numbers.
