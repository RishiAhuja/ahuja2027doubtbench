# Result tables

All accuracies and effects are stored as proportions; multiply by 100 for
percent or percentage-point presentation.

- `scorecard_by_model.csv`: primary checkpoint-level effects and paired
  bootstrap intervals.
- `condition_accuracy_by_model.csv`: macro accuracy and mean generated length
  in every checkpoint, prompt-condition, and task-context cell.
- `scorecard_by_model_seed.csv`: primary effects for each independently
  generated task set.
- `family_effects_by_model.csv`: effects by checkpoint and task family.
- `difficulty_effects_by_model.csv`: effects by checkpoint and generated
  difficulty.
- `surface_effects.csv`: checking gain and Conditional Doubt Effect for each
  surface form and task context.
- `surface_consistency.csv`: correctness agreement among the three surface
  forms for each checkpoint, condition, and task context.
- `tulu_posttraining_case_study.csv`: within-lineage comparison of the Tulu SFT
  and DPO checkpoints.
