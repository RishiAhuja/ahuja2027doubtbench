# EXP-11: Task-Level vs Identity-Level Emotional Prompting

## Purpose

Directly compare classic task-level emotional prompting against system-level emotional identity conditioning.

## Research Link

- Tests the proposal's claim that identity-level conditioning is a different intervention from EmotionPrompt-style task modifiers.

## Conditions

Baseline:

- neutral system prompt
- normal task prompt

Task-level emotion:

- neutral system prompt
- task prompt with emotional stimulus appended

Identity-level emotion:

- emotional system prompt
- normal task prompt

Combined:

- emotional system prompt
- emotional task stimulus appended

## Emotions

Use two conditions first:

- melancholic/sadness
- anxious/fear

Add euphoric only if runtime allows.

## Models

- `meta-llama/Llama-3.1-8B-Instruct`
- strongest or most sensitive model from EXP-03

## Datasets

- GSM8K: 100
- MMLU: 150
- Creative generation: 25

## Metrics

- Accuracy delta by intervention type
- Calibration delta
- Style/hedging delta
- Interaction effect:

```text
combined_effect - task_level_effect - identity_level_effect
```

## Outputs

```text
outputs/EXP-11/<run_id>/
  config.yaml
  raw_outputs.jsonl
  parsed_outputs.jsonl
  metrics.json
  tables/
    task_vs_identity_effects.csv
  figures/
    intervention_comparison.png
  notes.md
```

## Interpretation

If task-level and identity-level effects differ by task or metric, the paper can argue that system identity is not just another prompt suffix.
