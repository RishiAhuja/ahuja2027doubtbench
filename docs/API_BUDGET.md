# API budget guide (low cost)

Use **cloud APIs for fast validation**, not full P0 sweeps. Bulk inference stays on the HPC cluster.

## Recommended roles

| Role | Model | Why |
|------|-------|-----|
| Dev smoke | `groq:llama-3.1-8b-instant` | Very fast, ~$0.05/MTok in |
| Cross-check | `openai:gpt-4.1-mini` | Stable parsing, small $ |
| Holdout spot-check | `anthropic:claude-haiku-4-5-20251001` | Different family, use sparingly |

Optional cheap judge: `groq:openai/gpt-oss-20b` for EXP-01-style audits.

## What to run locally

```bash
# Load all benchmarks (free)
SKIP_API=1 bash scripts/smoke_all.sh

# ~26 API calls with counts_smoke.json (3+6+3+3+9+2 samples × 1 condition if you trim)
SMOKE_MODEL=groq:llama-3.1-8b-instant bash scripts/smoke_all.sh

# Slightly larger API validation (~100–150 calls)
python -m experiments.exp02.run_smoke \
  --counts-file configs/counts_smoke.json \
  --model openai:gpt-4.1-mini
```

## What NOT to run on API

- Full `counts_p0.json` (700+ samples × 3 conditions × multiple models) → cluster only
- 32B/70B open weights → cluster only
- Creative final scoring → batch judge later (Groq mini judges), not during generation

## Rough cost (smoke profile, 3 conditions)

| Model | Calls | Est. cost |
|-------|-------|-----------|
| Groq 8B instant | 78 | &lt; $0.10 |
| GPT-4.1-mini | 78 | ~$0.50–2 |
| Claude Haiku | 78 | ~$1–3 |

Hold one frontier model for a **20-sample** manual check, not a full sweep.

## Env keys (never commit)

```bash
export GROQ_API_KEY=...
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
```

Load from repo `.env` locally via `core.env.load_dotenv()`.

## Testing “cloud-like” behavior on open models

API smoke proves **prompts + parsers + metrics**. Cluster `run_open` proves **identity conditioning on weights**. Compare deltas across:

1. Same prompts, `groq:llama-3.1-8b-instant` (API)
2. Same prompts, `meta-llama/Llama-3.1-8B-Instruct` (HF on cluster)

If API and HF Llama trends agree on GSM8K confound, parsers are sane before burning GPU hours.
