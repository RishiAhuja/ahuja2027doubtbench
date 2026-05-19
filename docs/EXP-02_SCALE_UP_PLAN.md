# EXP-02 scale-up plan

## Benchmarks (P0)

| Dataset | Smoke (`counts_smoke.json`) | Full P0 (`counts_p0.json`) | Notes |
|---------|----------------------------|----------------------------|-------|
| GSM8K | 3 | 200 | Headline confound signal |
| MMLU (stratified) | 6 | 200 | By subject, not first-N |
| MATH L3 | 3 | 100 | Hendrycks test split |
| TriviaQA | 3 | 200 | Local `experiments/data/triviaqa_subset.jsonl` |
| BIG-Bench | 9 | 150 | 5 MC tasks from Google BIG-bench |
| Creative | 2 | 10 | No auto-score; expand `creative_prompts.json` before 50-prompt run |

## Models (cluster)

**7B (rerun on full P0):** Qwen2.5-7B, Llama-3.1-8B, Mistral-7B  
**24–32B (next):** Qwen2.5-32B, Mistral-Small-24B  
**API validation (local, cheap):** see `docs/API_BUDGET.md`

## Commands

### Local smoke (no GPU)

```bash
python scripts/download_benchmark_data.py 200 200 200   # trivia, math L3, BBH — once
bash scripts/smoke_all.sh                       # load + optional API
SKIP_API=1 bash scripts/smoke_all.sh            # loaders only
```

### Cluster submit (one GPU at a time)

```bash
export MIG_UUID=<from nvidia-smi -L>
export COUNT_PROFILE=configs/counts_p0.json
bash scripts/submit_exp02_scaleup.sh
```

Re-run a single model:

```bash
bash scripts/submit_exp02_one_model.sh "Qwen/Qwen2.5-7B-Instruct"
```

### Progress email (every 30 min)

```bash
nohup bash scripts/watch_progress_email.sh 30 >> logs/progress_email/watch.log 2>&1 &
echo $! > logs/progress_email/watch.pid
```

Requires `~/.config/caisc/resend.env` on the login node.

## Phasing

1. **A** — GSM8K full + 7B models (confound headline)
2. **B** — TriviaQA + creative + BIG-Bench
3. **C** — MMLU stratified + MATH L3
4. **D** — 32B models, then Tulu SFT/DPO/RL (EXP-05)
