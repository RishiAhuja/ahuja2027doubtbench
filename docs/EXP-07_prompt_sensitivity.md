# EXP-07: Prompt Sensitivity

## Purpose

Measure whether results depend on exact emotional prompt wording.

## Research Link

- Addresses prompt sensitivity as a limitation.
- Supports robustness of RQ1/RQ2 findings.

## Design

For each emotional condition, create 5 variants:

- v1: original prompt
- v2: shorter version
- v3: longer version
- v4: lower-arousal version
- v5: alternate wording with matched valence

Every variant must pass EXP-01 audit before use.

## Conditions

- melancholic: 5 variants
- euphoric: 5 variants
- anxious: 5 variants
- grandiose: 5 variants
- baseline: 1 version

## Models

Use the model/task pairs where EXP-03 showed the clearest effect.

Recommended:

- one open model
- two tasks
- one calibration subset

## Datasets

- GSM8K or MMLU: 100
- Creative generation: 25
- MMLU calibration subset if H4 effect was observed

## Metrics

- Mean effect across variants
- Variant standard deviation
- Sign consistency
- Prompt Sensitivity Ratio:

```text
PSR = std_variant(delta_accuracy) / max(abs(mean_variant(delta_accuracy)), epsilon)
```

Low PSR means the finding is robust to wording.

## Outputs

```text
outputs/EXP-07/<run_id>/
  config.yaml
  prompt_variants.json
  raw_outputs.jsonl
  parsed_outputs.jsonl
  metrics.json
  tables/
    variant_effects.csv
  figures/
    prompt_sensitivity_intervals.png
  notes.md
```

## Interpretation

If prompt sensitivity is high, report the effect as prompt-family-dependent and avoid broad claims about emotion categories.
