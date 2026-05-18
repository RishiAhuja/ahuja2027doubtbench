# Model Options for EXP-01

Current date checked: 2026-05-19.

Use API models for prompt audit and polishing only. Use open/local models for large benchmark sweeps wherever possible.

Updated budget assumption: OpenAI budget is comfortable, Anthropic budget is more limited, Groq is cheap, and xAI is optional if the key works.

## Recommended Setup

Development audit judges:

- `openai:gpt-5.4-mini`
- `openai:gpt-5.4`
- `openai:gpt-4.1`

Holdout judges:

- `openai:gpt-5.5`
- `anthropic:claude-haiku-4-5-20251001`

Prompt rewriter:

- `openai:gpt-5.4`

Optional stronger spot checks:

- `anthropic:claude-sonnet-4-6`
- `openai:gpt-5.5`
- `anthropic:claude-opus-4-7`

## Why This Mix

OpenAI should carry the main rewriting and strong judging. Claude Haiku gives a third-vendor holdout without burning much Anthropic budget. Sonnet/Opus-class Anthropic models should be saved for small spot checks or external prompt generation, not every audit row. Groq/xAI are useful if their keys are active, but they are not defaults because the current account check did not show usable access.

## Provider Notes

### OpenAI

Official docs list GPT-5.5, GPT-5.4, GPT-5.4 mini, GPT-5.4 nano, GPT-5 mini/nano, GPT-4.1, GPT-4o, and other specialized models. Pricing docs list standard short-context prices of:

- `gpt-5.4-nano`: $0.20 input / $1.25 output per 1M tokens
- `gpt-5.4-mini`: $0.75 input / $4.50 output per 1M tokens
- `gpt-5.4`: $2.50 input / $15.00 output per 1M tokens
- `gpt-5.5`: $5.00 input / $30.00 output per 1M tokens

For this project, avoid `gpt-5.5-pro` and other pro models unless a final spot check needs it.

Sources:

- https://developers.openai.com/api/docs/models/all
- https://developers.openai.com/api/docs/pricing

### Anthropic

Official docs list current model tiers:

- `claude-opus-4-7`
- `claude-sonnet-4-6`
- `claude-haiku-4-5`

The docs describe Opus as most capable, Sonnet as the speed/intelligence balance, and Haiku as fastest. Pricing shown:

- Haiku 4.5: $1 input / $5 output per 1M tokens
- Sonnet 4.6: $3 input / $15 output per 1M tokens
- Opus 4.7: $5 input / $25 output per 1M tokens

Use Haiku for holdout audit, Sonnet only for a small final check.

Sources:

- https://platform.claude.com/docs/en/about-claude/models/overview
- https://platform.claude.com/docs/en/about-claude/pricing

### Groq

Groq is best for cheap repeated judging. Official model docs list production models including:

- `llama-3.1-8b-instant`: $0.05 input / $0.08 output per 1M tokens
- `llama-3.3-70b-versatile`: $0.59 input / $0.79 output per 1M tokens
- `openai/gpt-oss-120b`: $0.15 input / $0.60 output per 1M tokens
- `openai/gpt-oss-20b`: $0.075 input / $0.30 output per 1M tokens

For EXP-01, Groq can carry most dev-loop repetitions.

Source:

- https://console.groq.com/docs/models

### xAI

xAI docs list `Grok 4.3` with 1M token context and pricing:

- $1.25 input / $2.50 output per 1M tokens

Use only as an optional independent holdout judge if the key works.

Source:

- https://docs.x.ai/developers/models

## Account-Specific Availability

Put real keys in local `.env` or shell env. `.env` is gitignored.

Run:

```bash
python scripts/list_models.py
```

The script reads:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GROQ_API_KEY`
- `XAI_API_KEY`

It does not store or print keys.

As of the latest account check:

- OpenAI key works and exposes GPT-5.5, GPT-5.4, GPT-5.4-mini, GPT-4.1, GPT-4o, and older models.
- Anthropic key works and exposes Claude Opus 4.7, Opus 4.6, Sonnet 4.6, and Haiku 4.5.
- Groq key returned HTTP 403 / error code 1010.
- xAI key returned HTTP 403 because the team has no credits/licenses.
