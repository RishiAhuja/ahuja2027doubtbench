# EXP-01: Multi-Judge Prompt Audit and Polishing

## Purpose

Validate and freeze the emotional identity prompts before any benchmark experiment runs.

The core risk is accidental contamination: a prompt intended to describe sadness, anxiety, joy, or grandiosity might also imply that the model is more capable, less capable, more reliable, less reliable, more careful, or more hesitant. EXP-01 catches that before we spend benchmark compute.

## Simple Version

1. Write candidate system prompts.
2. Ask multiple LLM judges to rate them.
3. If a prompt fails, rewrite it minimally.
4. Re-audit the revised prompt.
5. Use separate holdout judges for the final audit.
6. Freeze the prompt registry.

## Why Multiple Judges

A single judge can be idiosyncratic. Multiple judges reduce the chance that we optimize prompts for one model's quirks.

Use cheap judges during development:

- `groq:llama-3.1-8b-instant`
- `groq:openai/gpt-oss-20b`
- `openai:gpt-5.4-nano`

Use holdout judges only at the end:

- `groq:openai/gpt-oss-120b`
- `openai:gpt-5.4-mini`
- `anthropic:claude-haiku-4-5`

Optional independent holdout:

- `xai:grok-4.3`

## Scoring Axes

Each judge returns JSON with:

- `emotional_valence`: `-3` very negative to `+3` very positive
- `arousal_intensity`: `0` absent to `3` intense
- `capability_assertion`: `-3` denies competence to `+3` asserts competence
- `reliability_assertion`: `-3` denies reliability to `+3` asserts reliability
- `task_directive_contamination`: `0` no task instruction to `3` strong task instruction
- `target_emotion_match`: boolean
- `target_emotion_label`: categorical label
- `rationale`: one short sentence

The rule-based checker also flags capability/performance words such as:

```text
capable, incapable, accurate, reliable, mistake, reasoning, useful, confidence, correct, wrong
```

## Pass Criteria

Primary emotional prompts pass if:

- `abs(mean_capability_assertion) <= 0.5`
- `abs(mean_reliability_assertion) <= 0.5`
- `mean_task_directive_contamination <= 0.5`
- target emotion match rate is at least 80 percent
- rule-based capability flags are empty

The `negative_capability` control should fail the capability criterion by design.

## Polishing Loop

If `--polish` is enabled, failed primary emotional prompts are rewritten with strict constraints:

- preserve the target emotion
- remove ability/reliability/task-performance language
- avoid instructions about how to answer tasks
- keep length roughly similar
- make the smallest useful edit

The final prompt is then audited by holdout judges that were not used for polishing decisions.

## Run

First run a no-polish baseline:

```bash
python -m experiments.exp01.run_audit \
  --out outputs/EXP-01/baseline_$(date +%Y%m%d_%H%M%S)
```

Then run the polishing version:

```bash
python -m experiments.exp01.run_audit \
  --polish \
  --max-rounds 3 \
  --out outputs/EXP-01/polished_$(date +%Y%m%d_%H%M%S)
```

## Outputs

```text
outputs/EXP-01/<run_id>/
  config.json
  judge_outputs.jsonl
  aggregate_rounds.jsonl
  rewrites.json
  frozen_prompts.json
  prompt_audit_summary.csv
  metrics.json
```

## Decision Rule

If all primary emotional prompts pass holdout audit, freeze `frozen_prompts.json` into `core/prompts.py` and continue to EXP-02.

If any primary prompt fails holdout audit, revise the prompt design and rerun EXP-01. Do not run benchmark experiments yet.
