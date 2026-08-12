# CODS result archive audit

## Validated coverage

- `24` complete factorial cells: six models crossed with three development seeds and one held-out seed.
- `22` factorial cells use one token budget throughout; `2` historical composites mix budgets and are excluded from clean aggregate claims.
- `6` complete surface-robustness cells, one per model.
- `70` raw run directories inventoried across local, FA0571, and Medha sources.
- Every canonical cell was rebuilt from raw response keys and required exact task counts, exact row counts, model consistency, and zero overlap among composed segments.

## Important protocol and quality flags

- `factorial/qwen2.5-7b/16061`: protocol=`mixed_token_budget`, budgets=`[384, 768]`, quality=`quality_gate_failure`, parse=2.113%, truncation=2.694%.
- `factorial/llama3.1-8b/16061`: protocol=`mixed_token_budget`, budgets=`[384, 768]`, quality=`quality_gate_failure`, parse=8.206%, truncation=8.438%.
- `factorial/llama3.1-8b/16101`: protocol=`homogeneous`, budgets=`[768]`, quality=`quality_gate_failure`, parse=7.544%, truncation=7.644%.
- `factorial/llama3.1-8b/16102`: protocol=`homogeneous`, budgets=`[768]`, quality=`quality_gate_failure`, parse=7.769%, truncation=7.825%.
- `factorial/llama3.1-8b/19003-heldout`: protocol=`homogeneous`, budgets=`[768]`, quality=`quality_gate_failure`, parse=7.862%, truncation=7.963%.
- `surface-robustness/llama3.1-8b/19003-heldout`: protocol=`homogeneous`, budgets=`[768]`, quality=`quality_gate_failure`, parse=7.030%, truncation=7.045%.

## Conditional Doubt Effect

CDE is computed within the same latent task and template as `Accuracy(doubt + check) - Accuracy(check)`. The model table below averages only protocol-homogeneous cells; quality-gate status remains reported separately rather than deleting difficult model outputs.

| Model | Template | Cells | Passing | Mean CDE | Range | Signs (+/-) |
|---|---:|---:|---:|---:|---:|---:|
| llama3.1-8b | minimal | 3 | 0 | -0.014 | [-0.016, -0.013] | 0/3 |
| llama3.1-8b | reasoning_requested | 3 | 0 | -0.002 | [-0.006, +0.004] | 1/2 |
| mistral7b | minimal | 4 | 4 | -0.001 | [-0.006, +0.005] | 2/2 |
| mistral7b | reasoning_requested | 4 | 4 | -0.008 | [-0.023, +0.002] | 1/2 |
| phi3.5-mini | minimal | 4 | 4 | +0.053 | [+0.049, +0.063] | 4/0 |
| phi3.5-mini | reasoning_requested | 4 | 4 | -0.001 | [-0.019, +0.008] | 2/2 |
| qwen2.5-7b | minimal | 3 | 3 | +0.008 | [-0.007, +0.021] | 2/1 |
| qwen2.5-7b | reasoning_requested | 3 | 3 | -0.037 | [-0.046, -0.026] | 0/3 |
| tulu3-dpo-8b | minimal | 4 | 4 | +0.025 | [+0.018, +0.035] | 4/0 |
| tulu3-dpo-8b | reasoning_requested | 4 | 4 | +0.005 | [-0.003, +0.012] | 3/1 |
| tulu3-sft-8b | minimal | 4 | 4 | +0.011 | [+0.007, +0.018] | 4/0 |
| tulu3-sft-8b | reasoning_requested | 4 | 4 | +0.010 | [+0.006, +0.018] | 4/0 |

## Interpretation constraints

- Structural completion and quality-gate passage are different. Exit/status 3 runs retain all expected rows and metrics but exceed the predeclared 2% parse or truncation threshold.
- Surface robustness is a separate 660-task evaluation and is never added to the 1,600-task factorial score.
- Segment compositions are not independent replications; they are disjoint pieces of one seed-level cell.
- The two mixed-budget seed-16061 composites are useful historical evidence but should not enter the clean homogeneous-protocol aggregate without a sensitivity analysis.
- Medha's zero-row gated Llama-16102 failure is retained in provenance, while the canonical cell points to the completed FA0571 replacement.
