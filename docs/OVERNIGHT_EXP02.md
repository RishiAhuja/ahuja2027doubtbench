# EXP-02 Overnight Cluster Run

Run after GPU smoke passes (`docs/EXP-02_CLUSTER_SMOKE.md`).

## Constraints (NITJ HPC)

- One GPU/MIG per user at a time → jobs are **chained** with PBS `depend=afterany`.
- GPU jobs → `workq` only.
- Set exactly one MIG UUID in `CUDA_VISIBLE_DEVICES`.
- Store outputs under `/Data3/it_FA0571/caisc/outputs/`.

## Default overnight matrix

| Model | Role |
|-------|------|
| `Qwen/Qwen2.5-7B-Instruct` | Primary open model |
| `meta-llama/Llama-3.1-8B-Instruct` | Cross-family |
| `mistralai/Mistral-7B-Instruct-v0.3` | Cross-family |

Per model (default):

- GSM8K: 100 items
- MMLU: 100 items
- Conditions: `baseline`, `melancholic`, `negative_capability`
- **600 inference rows** per model (~6h walltime budget per job)

Total overnight: **~1800 rows** across 3 models (sequential).

## Submit

```bash
cd /Data3/it_FA0571/caisc
export PATH=/opt/pbs/bin:$PATH
git pull   # or deploy-key pull

# Pick a free MIG from nvidia-smi -L
export MIG_UUID=MIG-c747c071-8b61-5993-a5e0-33f4b566bd6e

bash scripts/submit_exp02_overnight.sh
```

Custom sizes:

```bash
COUNT_GSM8K=50 COUNT_MMLU=50 MAX_NEW_TOKENS=256 WALLTIME=04:00:00 \
  MIG_UUID=MIG-... \
  bash scripts/submit_exp02_overnight.sh \
  Qwen/Qwen2.5-7B-Instruct
```

## Progress + email

```bash
scripts/progress.sh
```

See `docs/RESEND_PROGRESS_EMAIL.md` for Resend setup.

## After morning

Pull results:

```bash
# from laptop
rsync -avz it_FA0571@10.10.11.201:/Data3/it_FA0571/caisc/outputs/EXP-02/ ./outputs/EXP-02/
```

Update `docs/EXP-02_RESULTS.md` with cluster metrics.

## Not in this overnight batch

- API models (run locally)
- TriviaQA / MATH (not wired in `core/benchmarks.py` yet)
- Full EXP-03 sweep (more conditions)
- 32B models (optional later; longer per job)
