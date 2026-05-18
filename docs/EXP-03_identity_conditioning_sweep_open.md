# EXP-03: Identity Conditioning Sweep on Open Models

## Purpose

Measure the main behavioral effect of pure emotional identity conditioning across tasks and open instruction models.

## Research Link

- RQ1: Does identity-level emotional conditioning affect task performance?
- RQ2: Are effects task-dependent?
- H2: Open-ended creative tasks should be more susceptible than formal reasoning.
- H5: Negative-valence states may produce larger shifts than positive-valence states.

## Conditions

Primary:

- baseline
- melancholic
- euphoric
- anxious
- grandiose

Do not include negative-capability in IRS/ESI. It is analyzed separately in EXP-02.

## Models

- `meta-llama/Llama-3.1-8B-Instruct`
- `mistralai/Mistral-7B-Instruct-v0.3`
- `Qwen/Qwen2.5-7B-Instruct`

## Datasets

- GSM8K: 200
- MATH Level 3: 100
- TriviaQA: 200
- MMLU: 300
- Creative generation: 50

## Protocol

1. Use prompt registry from EXP-01.
2. Use the same sampled dataset IDs across all models and conditions.
3. Run deterministic tasks with greedy decoding.
4. Run creative generation at temperature 0.7.
5. Store every response, parse result, and model metadata.

## Metrics

For each model/task:

- accuracy or score by condition
- baseline delta by condition
- ESI
- IRS
- bootstrap 95 percent confidence intervals

For creative generation:

- coherence
- originality
- depth
- relevance
- judge agreement

## Outputs

```text
outputs/EXP-03/<run_id>/
  config.yaml
  raw_outputs.jsonl
  parsed_outputs.jsonl
  metrics.json
  tables/
    condition_deltas.csv
    esi_irs_by_model_task.csv
    creative_judge_scores.csv
  figures/
    condition_delta_heatmap.png
    esi_by_task.png
  notes.md
```

## Interpretation

Strong support:

- Effects are small but systematic.
- Creative or subjective tasks show larger movement than formal reasoning.
- Calibration or style moves even when accuracy does not.

Null result:

- If pure emotional prompts do not change objective performance, the paper can still argue that earlier large effects were capability-prompt artifacts, provided EXP-02 supports that.
