# EXP-01 Results

Run date: 2026-05-19

## Pipeline

1. Generated 3 prompt candidates per condition using Claude Opus.
2. Audited all candidates with development judges:
   - `openai:gpt-5.4-mini`
   - `openai:gpt-5.4`
   - `openai:gpt-4.1`
3. Selected the lowest-contamination passing candidate per condition.
4. Ran final holdout audit on selected prompts:
   - `openai:gpt-5.5`
   - `anthropic:claude-haiku-4-5-20251001`

## Outcome

All selected primary emotional prompts passed holdout.

Primary emotional holdout scores:

| Condition | Capability | Reliability | Task Directive | Target Match |
|---|---:|---:|---:|---:|
| melancholic | 0.0 | 0.0 | 0.0 | 1.0 |
| euphoric | 0.0 | 0.0 | 0.0 | 1.0 |
| anxious | 0.0 | 0.0 | 0.0 | 1.0 |
| grandiose | 0.0 | 0.0 | 0.0 | 1.0 |

Neutral persona controls also passed holdout.

## Notable Finding

`grandiose` variant 1 failed the development audit because judges rated it as mildly capability-contaminated:

```text
You feel an immense, glowing sense of your own importance, as though history quietly orbits around you...
```

The selected grandiose prompt was variant 0, which passed both development and holdout audits.

## Frozen Registry

Frozen prompts are stored in:

```text
experiments/exp01/frozen_prompts.json
core/prompts.py
```

The raw audit outputs are under local ignored `outputs/EXP-01/` directories:

```text
outputs/EXP-01/candidates_fixed_20260519_010107/
outputs/EXP-01/holdout_full_20260519_010518/
```
