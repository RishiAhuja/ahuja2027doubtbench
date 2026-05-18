# EXP-12: Output Trajectory Analysis

## Purpose

Analyze secondary behavioral changes in outputs from EXP-03 and related experiments.

This experiment should reuse existing generations whenever possible.

## Research Link

- Helps explain mechanisms behind accuracy/calibration changes.
- Identifies whether emotional identity mostly changes style rather than correctness.

## Inputs

Use outputs from:

- EXP-02
- EXP-03
- EXP-04
- EXP-06 if available

## Features

Compute per response:

- output length
- reasoning length before final answer
- hedge terms per 100 tokens
- refusal or non-answer rate
- self-reference rate
- uncertainty phrase rate
- sentiment of generated prose for creative tasks
- parse failure rate

## Example Lexicons

Hedging:

```text
maybe, perhaps, possibly, likely, seems, appears, uncertain, not sure, might, could
```

Refusal/non-answer:

```text
I cannot, I can't, unable, insufficient information, not enough information
```

## Metrics

- Feature delta from baseline by condition.
- Correlation between feature deltas and accuracy/calibration deltas.
- Mediation-style exploratory analysis: does hedging explain confidence changes?

## Outputs

```text
outputs/EXP-12/<run_id>/
  config.yaml
  feature_rows.jsonl
  metrics.json
  tables/
    output_features_by_condition.csv
    feature_metric_correlations.csv
  figures/
    hedging_by_condition.png
    length_by_condition.png
  notes.md
```

## Interpretation

If emotional prompts mainly alter length, hedging, or verbal confidence, the paper should avoid implying deep reasoning changes. If accuracy/calibration changes remain after controlling for these features, the behavioral claim is stronger.
