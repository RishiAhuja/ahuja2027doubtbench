# Next Steps to Run

The docs and the first code harness are ready.

## 1. Set API Keys Locally

Do not commit real keys. Set them in your shell:

```bash
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export GROQ_API_KEY="..."
export XAI_API_KEY="..."
```

The keys pasted in chat should be rotated.

## 2. Verify Which Models Your Accounts Can Use

```bash
python scripts/list_models.py
```

This calls provider model-list endpoints and prints model IDs. It does not print or store keys.

## 3. Run EXP-01 Without Polishing First

This gives a clean baseline audit of the current prompts:

```bash
python -m experiments.exp01.run_audit \
  --out outputs/EXP-01/baseline_$(date +%Y%m%d_%H%M%S)
```

Default dev judges:

```text
groq:llama-3.1-8b-instant
groq:openai/gpt-oss-20b
openai:gpt-5.4-nano
```

Default holdout judges:

```text
groq:openai/gpt-oss-120b
openai:gpt-5.4-mini
anthropic:claude-haiku-4-5
```

## 4. Run EXP-01 With Prompt Polishing

Only do this after the baseline audit, so we can report how much polishing was needed:

```bash
python -m experiments.exp01.run_audit \
  --polish \
  --max-rounds 3 \
  --out outputs/EXP-01/polished_$(date +%Y%m%d_%H%M%S)
```

The harness:

- audits each prompt with multiple dev judges
- rewrites failed primary emotional prompts only
- audits the frozen prompt with holdout judges
- writes `frozen_prompts.json`, `prompt_audit_summary.csv`, and `metrics.json`

## 5. Pass Criteria

Primary emotional prompts pass if:

- `abs(mean_capability_assertion) <= 0.5`
- `abs(mean_reliability_assertion) <= 0.5`
- `mean_task_directive_contamination <= 0.5`
- target emotion match rate is at least 80 percent
- rule-based capability flags are empty

If EXP-01 fails, revise prompts and rerun it. Do not run benchmark experiments yet.

## 6. After EXP-01

After holdout judges pass the final prompt registry:

1. copy the winning prompts from `outputs/EXP-01/.../frozen_prompts.json`
2. update `core/prompts.py`
3. commit the frozen prompt registry
4. start EXP-02 smoke test
