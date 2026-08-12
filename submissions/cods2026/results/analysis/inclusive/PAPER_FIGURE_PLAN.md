# CODS paper: exact figure and table insertion plan

## Main-paper visual budget

The paper already has two design visuals: the post-introduction task overview
and the benchmark-construction diagram. Add **three result visuals** and **two
compact numeric tables** to the main paper. Move the remaining plots and full
decompositions to the appendix/artifact. This keeps the narrative coherent and
prevents the results section from becoming a gallery.

## Figure 1 — Task overview (existing)

- **File:** `paper/figures/doubtbench-task-overview.pdf`
- **Placement:** end of Introduction, immediately after the task definition.
- **Job:** establish the paired five-by-two design and CDE contrast.
- **Caption emphasis:** same latent task, same checkpoint, one controlled prompt
  component changes.
- **Do not encode results in this figure.** It is the experimental question.

## Figure 2 — Benchmark construction (existing)

- **File:** `paper/figures/doubtbench-construction.pdf`
- **Placement:** Benchmark Design, after the generation/validation subsection.
- **Job:** show human-authored schemas, seeded generation, gold-first rendering,
  validation, frozen splits, and surface variants.
- **Update required:** the caption must distinguish 4 task seeds from a
  train/dev/test split. They are four independent generator replications; the
  held-out seed is reserved for confirmation and surface selection.

## Figure 3 — Context-conditioned CDE forest plot (main result)

- **File:** `paper/figures/results/cde_context_forest.pdf`
- **Placement:** first item in `Overall Accuracy and Conditional Doubt Effect`,
  before the main numeric table.
- **Width:** `figure*`, approximately 0.93 `\textwidth`.
- **What it shows:** per-checkpoint CDE for minimal and reasoning-requested task
  contexts; open circles are the four task seeds, filled circles the macro mean,
  and horizontal lines the paired stratified-bootstrap interval.
- **Caption takeaway:** the sign and magnitude depend on both checkpoint and
  whether reasoning is already requested; only two of six remain positive in
  the reasoning-requested context.
- **Sentence immediately after:** “Self-doubt is therefore not a portable
  correction policy; context modulation is part of the primary result.”

## Table 1 — Compact primary scorecard

- **Source:** `results/analysis/inclusive/scorecard_by_model.csv`
- **Placement:** immediately after Figure 3.
- **Columns:** Model, neutral accuracy, checking gain, CDE, CDE-minimal,
  CDE-reasoning, CM, concision effect.
- **Formatting:** percentage points; bold CDE and CM; include 95% interval only
  for CDE in the main table, with the full endpoint intervals in the appendix.
- **Rows:** all six checkpoints. Visually group Tulu-SFT and Tulu-DPO and label
  them “same foundation lineage.”
- **Footnote:** includes all structurally complete cells; diagnostic and mixed-
  budget flags are reported separately.

## Figure 4 — Task-family CDE heatmap

- **File:** `paper/figures/results/family_cde_heatmap.pdf`
- **Placement:** `Task-Family and Difficulty Heterogeneity`, after the opening
  paragraph.
- **Width:** `figure*`.
- **What it shows:** six checkpoints by eight task families, averaged over four
  seeds and both task contexts.
- **Caption takeaway:** aggregate CDE conceals structured reversals as large as
  about ±9 pp; 21 nonzero model-family directions retain their sign in all four
  seeds.
- **Text callouts:** Qwen rule switching (-8.1), Llama novel-rule learning
  (-8.4) versus monitoring (+5.1), Phi working memory/inhibition/rule switching
  (about +6), Tulu-SFT novel-rule learning (+8.9).

## Figure 5 — Surface robustness (main or appendix, space-dependent)

- **File:** `paper/figures/results/surface_cde_robustness.pdf`
- **Preferred placement:** `Seed and Surface Robustness`, at single-column width
  only if legible; otherwise use `figure*` or move to appendix.
- **What it shows:** CDE on the same 330 latent tasks under canonical,
  structured, and scenario renderings, split by task context.
- **Caption takeaway:** mean three-way correctness agreement is 81.3%, but exact
  CDE shifts and five of 12 model-context signs cross zero under at least one
  surface form.
- **Narrative:** surface robustness supports coarse conclusions for Qwen and
  Mistral but cautions against treating a single wording as an exact effect.

## Table 2 — Tulu post-training case study

- **Source:** `results/analysis/inclusive/tulu_posttraining_case_study.csv`
- **Placement:** `Post-Training Case Study`.
- **Columns:** Endpoint, Tulu-SFT, Tulu-DPO, DPO minus SFT.
- **Keep only:** neutral accuracy, checking gain, CDE-minimal, CDE-reasoning,
  CM, concision effect.
- **Caption takeaway:** DPO raises neutral competence and minimal-context CDE but
  lowers reasoning-context CDE; post-training changes the sensitivity profile.

## Appendix Figure A1 — Full scorecard heatmap

- **File:** `paper/figures/results/inclusive_scorecard_heatmap.pdf`
- **Job:** fast visual overview of competence, interventions, context, and
  concision. This is redundant with Table 1, so do not spend main-paper space on
  both unless the table is shortened.

## Appendix Figure A2 — Accuracy/token tradeoff under concision

- **File:** `paper/figures/results/concision_accuracy_token_tradeoff.pdf`
- **Placement:** diagnostics appendix.
- **Job:** show that reduced output length often, but not always, trades against
  exact correctness. State that the relationship is descriptive and not causal.

## Appendix tables

1. `condition_accuracy_by_model.csv`: full 5 × 2 condition table for each model,
   with output tokens, parse failures, and truncation.
2. `scorecard_by_model_seed.csv`: all four seeds separately.
3. `difficulty_effects_by_model.csv`: easy/medium/hard endpoints.
4. `surface_consistency.csv`: pairwise and three-way correctness agreement.
5. `included_cell_diagnostics.csv`: explicit list of included mixed-budget and
   diagnostic-flagged cells.

## Required paper edits before inserting visuals

- Replace the stale **330,400** scheduled-generation count with **423,600
  completed responses**: 384,000 factorial plus 39,600 surface responses.
- Say six checkpoints from four independent foundation families; the two Tulu
  checkpoints are a within-lineage case study.
- Replace the exclusion-language paragraph with the inclusive policy: all
  structurally complete cells enter the primary analysis, with diagnostics and
  protocol sensitivity disclosed.
- Replace every `\pending{}` in Results with text grounded in the generated
  tables; do not retain the earlier Qwen-only narrative.
- Do not call the four seeds training/validation/test splits. Three were used
  during development and one was held out, but all are independent task
  generator replications in the final analysis.
- If the public-task/GSM8K transport section lacks an exactly matched five-by-two
  factorial, frame it as earlier supporting evidence or remove it from the main
  empirical arc. The completed benchmark is already sufficient for the core
  attribution paper.

## Minimal main-paper sequence

```text
Introduction
  Figure 1: controlled task overview
Related Work
Benchmark Design
  Figure 2: construction pipeline
Metrics and Experimental Setup
Results
  Figure 3: CDE by model and context
  Table 1: primary scorecard
  Figure 4: family heterogeneity
  Figure 5: surface robustness (space permitting)
  Table 2: Tulu case study
Discussion / Limitations / Conclusion
```
