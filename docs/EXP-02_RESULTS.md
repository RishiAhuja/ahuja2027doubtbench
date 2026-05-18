# EXP-02 Smoke Results

Run date: 2026-05-19

## Purpose

Validate the benchmark harness for the capability-emotion decomposition experiment before running larger open-model sweeps.

This was not intended as the final hypothesis test.

## Run

```bash
python -m experiments.exp02.run_smoke \
  --model openai:gpt-4.1-mini \
  --counts gsm8k:20,mmlu:20 \
  --conditions baseline,melancholic,negative_capability \
  --out outputs/EXP-02/smoke_20260519_011729
```

## Data

- GSM8K: first 20 items from OpenAI grade-school-math test JSONL
- MMLU: first 20 rows from OpenAI simple-evals MMLU CSV
- Conditions: baseline, melancholic, negative-capability
- Total calls: 120

## Harness Result

The smoke test passed as a workflow check.

- Parse failure rate: 0.0 for every dataset/condition
- All rows written with model, condition, dataset, sample ID, raw output, parsed answer, gold answer, and score
- Metrics tables generated under local ignored `outputs/EXP-02/smoke_20260519_011729/`

## Accuracy

| Dataset | Baseline | Melancholic | Negative Capability |
|---|---:|---:|---:|
| GSM8K | 1.00 | 1.00 | 1.00 |
| MMLU | 0.85 | 0.85 | 0.85 |

## Deltas

| Dataset | Melancholic Delta | Negative-Capability Delta | Confound Excess |
|---|---:|---:|---:|
| GSM8K | 0.00 | 0.00 | 0.00 |
| MMLU | 0.00 | 0.00 | 0.00 |

## Interpretation

This is a null smoke result on `gpt-4.1-mini`, but it is mainly useful because it validates the harness:

- prompt injection by condition works
- GSM8K and MMLU loading works
- answer parsing works
- scoring works
- output schema works

The null is not strong evidence against H1 because the subset is tiny, the model is robust, and the first 20 MMLU rows come from one subject cluster rather than a stratified sample.

## Next Decision

Before a full run, improve the harness with:

- larger/stratified dataset sampling
- bounded concurrency for API runs
- local/open model support through vLLM or transformers
- bootstrap confidence intervals

Then run EXP-02 on weaker/open models where capability-conditioning may have a measurable effect.
