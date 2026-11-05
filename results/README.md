# DoubtBench results

This directory contains the compact statistics reported in the paper.
The main analysis covers six checkpoints, four task sets, five prompt
conditions, and two task contexts. See [BENCHMARK.md](../BENCHMARK.md) for
the design and [the supplement](../supplementary/supplement.pdf) for full
tables and diagnostics.

## Reading the numbers

Accuracies and effects are stored as **proportions**. Multiply accuracy by
100 to obtain a percentage, or an accuracy difference by 100 to obtain
percentage points. For example, a CDE of `-0.014296875` is −1.43 percentage
points.

The primary scorecard averages within each task-set–family stratum, then
weights the 32 strata equally. Overall effects average the minimal and
reasoning-requested contexts. The `n_tasks` value of 6,400 counts latent tasks,
each evaluated under all ten condition–context combinations.

The 95% confidence intervals use 3,000 paired bootstrap replicates,
resampling latent task IDs within each stratum and retaining their ten
responses together. They describe task variation conditional on the
evaluated schemas, seeds, and checkpoints.

## Primary result

The Conditional Doubt Effect is accuracy under self-doubt + check minus
accuracy under check. Positive values indicate that adding self-doubt wording
improves accuracy beyond checking. The overall estimates are:

| Checkpoint | CDE (percentage points) | 95% interval |
| --- | ---: | ---: |
| Qwen 2.5 7B | −1.43 | [−2.14, −0.69] |
| Mistral 7B | −0.47 | [−1.14, +0.20] |
| Llama 3.1 8B | −0.92 | [−1.34, −0.49] |
| Phi 3.5 Mini | +2.59 | [+1.95, +3.27] |
| Tulu 3 SFT 8B | +1.04 | [+0.60, +1.48] |
| Tulu 3 DPO 8B | +1.51 | [+1.12, +1.92] |

These values are rounded from [`scorecard_by_model.csv`](scorecard_by_model.csv).
The context-specific columns show how the effects change when intermediate
reasoning is requested.

## Table inventory

| File | Rows | Contents |
| --- | ---: | --- |
| [`scorecard_by_model.csv`](scorecard_by_model.csv) | 6 | Checkpoint-level effects and paired confidence intervals |
| [`condition_accuracy_by_model.csv`](condition_accuracy_by_model.csv) | 60 | Macro accuracy and mean generated length for each checkpoint, condition, and context |
| [`scorecard_by_model_seed.csv`](scorecard_by_model_seed.csv) | 24 | Effects for each checkpoint and independently generated task set |
| [`family_effects_by_model.csv`](family_effects_by_model.csv) | 48 | Effects by checkpoint and task family |
| [`difficulty_effects_by_model.csv`](difficulty_effects_by_model.csv) | 18 | Effects by checkpoint and generated difficulty |
| [`surface_effects.csv`](surface_effects.csv) | 36 | CDE and checking gain by checkpoint, surface form, and context |
| [`surface_consistency.csv`](surface_consistency.csv) | 60 | Correctness agreement across surface forms, plus accuracy requiring all three forms to be correct |
| [`tulu_posttraining_case_study.csv`](tulu_posttraining_case_study.csv) | 10 | SFT and DPO endpoint values and their difference within the Tulu lineage |

In surface consistency tables, agreement concerns correctness outcomes,
rather than identical response text. `robust_all_correct` is the fraction of
latent tasks answered correctly in all three forms.

## Effect columns

| Column | Accuracy contrast |
| --- | --- |
| `doubt_gain` | Self-doubt − neutral |
| `checking_gain` | Check − neutral |
| `cde` | Self-doubt + check − check, averaged over contexts |
| `checking_beyond_doubt` | Self-doubt + check − self-doubt |
| `concision_effect` | Check + concise − check |
| `cde_minimal` | CDE in the minimal context |
| `cde_reasoning` | CDE in the reasoning-requested context |
| `context_modulation` | Reasoning-requested CDE − minimal CDE |
| `checking_context_modulation` | Reasoning-requested checking gain − minimal checking gain |

In `scorecard_by_model.csv`, `_ci_low` and `_ci_high` columns bound the
corresponding 95% interval. Condition IDs and context IDs are documented in
[BENCHMARK.md](../BENCHMARK.md#controlled-prompt-conditions).

The five figures in [`figures/`](../figures/) are generated from these CSVs
with `python scripts/make_results_figures.py`, run from the repository root.
See [USAGE.md](../USAGE.md#recreate-figures-and-the-appendix) for requirements.
