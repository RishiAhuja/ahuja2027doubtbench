# EXP-08: Frontier API Cross-Family Validation

## Purpose

Check whether the open-model findings generalize to stronger commercial models.

This experiment is validation, not the clean H3 test.

## Research Link

- Supports external validity for RQ1/RQ2/RQ4.
- Does not by itself prove RLHF or alignment intensity effects.

## Models

At run time, query provider docs/API and pin exact IDs.

Recommended:

- Current Anthropic Sonnet-class model.
- Current OpenAI general-purpose model.
- Optional historical comparator: `gpt-4o` if still available in API and budget permits.

Record:

- provider
- exact model ID
- API date
- pricing snapshot
- whether logprobs are available
- system prompt handling constraints

## Conditions

Use a narrow subset:

- baseline
- melancholic
- anxious
- grandiose
- negative_capability

## Datasets

Budget-preserving subset:

- GSM8K: 100
- MMLU: 150
- TriviaQA: 100

Optional:

- 20 creative prompts

## Protocol

1. Run EXP-01 prompt audit before API benchmarks.
2. Use deterministic decoding when supported.
3. Store exact request/response metadata.
4. If logprobs are unavailable, skip logprob ECE and use only verbal confidence as secondary analysis.
5. Do not mix API model results into the primary post-training H3 test.

## Outputs

```text
outputs/EXP-08/<run_id>/
  config.yaml
  api_model_manifest.json
  raw_outputs.jsonl
  parsed_outputs.jsonl
  metrics.json
  tables/
    frontier_condition_deltas.csv
  figures/
    frontier_vs_open_deltas.png
  notes.md
```

## Interpretation

Strong validation:

- Frontier models show smaller but directionally similar effects.

Robustness finding:

- Frontier models show near-zero pure emotion effects but still react to negative-capability.

Do not overclaim:

- Cross-vendor differences cannot be attributed only to RLHF, because the models differ in many uncontrolled ways.
