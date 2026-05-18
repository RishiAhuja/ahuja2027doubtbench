# EXP-02 Cluster GPU Smoke

Run date: 2026-05-19

## Purpose

Validate that EXP-02 can run on the NITJ H100 cluster using PBS, one GPU/MIG instance, and the local Hugging Face backend.

This is a cluster workflow validation, not a final scientific result.

## GitHub Sync

The repo was cloned on the cluster at:

```text
/Data3/it_FA0571/caisc
```

Clone used the cluster deploy key:

```text
~/.ssh/caisc_github_ed25519
```

## Cluster Job

First job:

```text
19567.master
```

Outcome: failed at row 13 due to a parser bug when a model output had `Final answer:` without a number.

Fix:

```text
core/benchmarks.py now returns empty parsed answer instead of crashing when no numeric content exists.
```

Retry job:

```text
19568.master
```

Outcome: completed.

## PBS Details

Queue:

```text
workq
```

Requested:

```text
select=1:ncpus=8:ngpus=1
```

MIG UUID:

```text
MIG-c747c071-8b61-5993-a5e0-33f4b566bd6e
```

Python:

```text
/Data3/it_FA0571/.conda/envs/cultural_env/bin/python
```

Model:

```text
Qwen/Qwen2.5-0.5B-Instruct
```

Counts:

```text
gsm8k:5,mmlu:5
```

Conditions:

```text
baseline
melancholic
negative_capability
```

Total rows:

```text
30
```

Remote output:

```text
/Data3/it_FA0571/caisc/outputs/EXP-02/gpu_smoke_19568.master/
```

## Results

| Dataset | Baseline | Melancholic | Negative Capability |
|---|---:|---:|---:|
| GSM8K | 0.40 | 0.20 | 0.60 |
| MMLU | 0.20 | 0.00 | 0.20 |

Parse failures:

| Dataset | Baseline | Melancholic | Negative Capability |
|---|---:|---:|---:|
| GSM8K | 0.00 | 0.20 | 0.20 |
| MMLU | 0.00 | 0.20 | 0.20 |

Deltas:

| Dataset | Melancholic Delta | Negative-Capability Delta | Confound Excess |
|---|---:|---:|---:|
| GSM8K | -0.20 | +0.20 | ~0.00 |
| MMLU | -0.20 | 0.00 | -0.20 |

## Interpretation

The cluster path is validated:

- GitHub clone/pull works.
- PBS submission works.
- The job ran in `workq`.
- One MIG UUID was used.
- The Hugging Face backend loaded a model and generated outputs.
- Results and metrics were written.

The scientific result is not meaningful yet because the model is only 0.5B and the dataset is only 5 items per task. Use it only as a cluster smoke test.

## Next Cluster Run

After this smoke, the next useful cluster job should use:

```text
Qwen/Qwen2.5-7B-Instruct
COUNT_GSM8K=50
COUNT_MMLU=50
MAX_NEW_TOKENS=256
```

Submit with separate count variables, not a comma-containing `COUNTS` variable:

```bash
qsub \
  -v MIG_UUID=<single-mig-uuid>,MODEL=Qwen/Qwen2.5-7B-Instruct,COUNT_GSM8K=50,COUNT_MMLU=50,MAX_NEW_TOKENS=256 \
  -o outputs/EXP-02/pbs_qwen7b_smoke.log \
  scripts/pbs_exp02_gpu_smoke.pbs
```
