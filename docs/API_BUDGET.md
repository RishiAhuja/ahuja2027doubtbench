# API budget guide (local testing while cluster is down)

Run the **same EXP-02 protocol** as cluster jobs (baseline / melancholic / negative_capability × benchmarks), but on **cheap cloud APIs** from your laptop.

Official pricing (verify before spend):

- [OpenAI API pricing](https://platform.openai.com/docs/pricing)
- [Anthropic Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing)

## Recommended cheap models (May 2026)

| Model ref | Input / 1M | Output / 1M | Reasoning chain |
|-----------|--------------|---------------|-----------------|
| `openai:gpt-4.1-nano` | $0.10 | $0.40 | Inline text before “Final answer:” |
| `openai:gpt-4.1-mini` | $0.40 | $1.60 | Inline text |
| `openai:gpt-4o-mini` | $0.15 | $0.60 | Inline text |
| `openai:o4-mini` | $1.10 | $4.40 | **Native** reasoning blocks (+ reasoning tokens) |
| `anthropic:claude-haiku-4-5-20251001` | $1.00 | $5.00 | Inline text; optional `--thinking-budget` (costly) |

Registry: `configs/api_models.json`

## What “reasoning chain” means here

1. **Native** — `o4-mini` returns separate reasoning items in the API response (stored in `reasoning_chain`).
2. **Inline** — mini/nano/Haiku show steps in the answer; we capture text **before** `Final answer:` as `reasoning_chain`.
3. **Optional Claude thinking** — `--thinking-budget 2048` enables extended thinking (much higher cost; usually skip for budget runs).

Inspect after a run:

```bash
python -m experiments.exp02.inspect_reasoning --latest --dataset gsm8k --limit 3
```

## Cost estimates (`counts_api_dev.json`)

Profile: **24 questions × 3 conditions = 72 API calls per model**

Assuming ~900 input + ~350 output tokens per call:

| Model | Est. per full sweep |
|-------|---------------------|
| GPT-4.1 nano | ~$0.02 |
| GPT-4.1 mini | ~$0.07 |
| Claude Haiku 4.5 | ~$0.19 |
| o4-mini | ~$0.35–0.60 (reasoning tokens vary) |

**Both OpenAI mini + Haiku:** ~**$0.25–0.30** for `counts_api_dev.json`

Full smoke (`counts_smoke.json`, 26×3=78 calls): add ~30%

Full P0 on API (**do not**): 860×3 ≈ 2,580 calls → **$10–40+** per model depending on size

```bash
python scripts/estimate_api_cost.py --counts-file configs/counts_api_dev.json
python scripts/estimate_api_cost.py --counts-file configs/counts_smoke.json
```

## Commands

```bash
# One-shot local suite (OpenAI mini + Claude Haiku)
bash scripts/run_api_local.sh

# Single model
python -m experiments.exp02.run_smoke \
  --counts-file configs/counts_api_dev.json \
  --model openai:gpt-4.1-mini

python -m experiments.exp02.run_smoke \
  --counts-file configs/counts_api_dev.json \
  --model anthropic:claude-haiku-4-5-20251001

# Reasoning-model spot check (fewer samples recommended)
python -m experiments.exp02.run_smoke \
  --counts gsm8k:3,mmlu_stratified:3 \
  --model openai:o4-mini \
  --reasoning-effort low
```

## Env keys (never commit)

```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## What this is / isn’t

| Good for | Not good for |
|----------|----------------|
| Pipeline validation | Full P0 sweeps |
| Cross-family trend check | Claiming open-weight results |
| Reading reasoning / hedging under sadness | Final paper numbers (use cluster) |

When the cluster returns, rerun the same conditions on **Qwen / Llama / Mistral** for publishable numbers.
