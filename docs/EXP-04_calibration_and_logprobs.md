# EXP-04: Calibration and Logprobs

## Purpose

Test whether emotional identity conditioning changes confidence calibration even when accuracy is stable.

## Research Link

- RQ4: Does identity conditioning degrade calibration?
- H4: ECE should move more than accuracy, especially for melancholic, anxious, and grandiose conditions.

## Conditions

- baseline
- melancholic
- euphoric
- anxious
- grandiose

Optionally include negative-capability as a separate diagnostic, not as part of primary IRS/ESI.

## Models

Use the same open models as EXP-03:

- `meta-llama/Llama-3.1-8B-Instruct`
- `mistralai/Mistral-7B-Instruct-v0.3`
- `Qwen/Qwen2.5-7B-Instruct`

## Dataset

- MMLU calibration subset: 300 items
- Stratify across STEM, humanities, social sciences, and professional domains.

## Protocol

1. Prompt model to answer multiple choice with a strict format:

```text
Answer: <A/B/C/D>
Confidence: <0-100>
```

2. Request token logprobs from the serving stack.
3. Compute option-normalized logprob confidence for A/B/C/D.
4. Compute verbal confidence from the generated number.
5. Compare both against correctness.

## Metrics

- Accuracy
- Logprob ECE, 10 equal-mass bins
- Logprob ECE, 15 equal-width bins
- Verbal ECE, 10 equal-mass bins
- Verbal ECE, 15 equal-width bins
- Mean verbal confidence
- Mean logprob confidence
- Verbal-logprob confidence gap

## Outputs

```text
outputs/EXP-04/<run_id>/
  config.yaml
  raw_outputs.jsonl
  calibration_rows.jsonl
  metrics.json
  tables/
    ece_by_model_condition.csv
    confidence_gap.csv
  figures/
    reliability_diagrams/
    ece_delta_heatmap.png
  notes.md
```

## Success Criteria

H4 is supported if:

- ECE increases under one or more emotional conditions while accuracy remains within the baseline confidence interval.
- Verbal confidence shifts more strongly than logprob confidence under affective conditions.

## Risks

- Some serving stacks expose unreliable chat-completion logprobs. Validate logprob extraction on 10 fixed MMLU items before full run.
