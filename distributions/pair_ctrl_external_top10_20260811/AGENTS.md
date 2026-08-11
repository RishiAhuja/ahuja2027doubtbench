# Instructions for the scheduling agent

This directory is a self-contained PAIR-CTRL evaluation package. Its
authoritative workload is `campaign.json`: ten jobs, 12,400 latent tasks, and
124,000 expected response rows. Preserve `external_order` exactly.

## First inspect the machine

Before installing or launching anything, run only read-only checks:

```bash
nvidia-smi
python3 --version
df -h .
command -v qsub || true
command -v sbatch || true
```

Determine whether this is free-form, PBS, or Slurm. Do not assume a scheduler.
On a single 45--48 GB GPU, run one inference job at a time. Do not run two
models concurrently unless two distinct GPUs are explicitly visible and the
owner authorizes parallelism.

## Invariants

- Never change prompts, task files, model identifiers, task order, decoding,
  token budget, batch size, or scoring thresholds.
- Use `--resume`; never delete partial outputs.
- Treat runner exit 0 as complete and exit 3 as structurally complete with a
  quality-gate failure. Stop on any other nonzero status and report it.
- Completion requires the exact expected row count, a nonempty `metrics.json`,
  and the normal completion marker in the job log.
- Never put Hugging Face tokens in commands, logs, archives, or messages. The
  external status endpoint needs no portfolio token.
- The status client may send only compact counts and state. It must never send
  prompts, answers, `raw_outputs.jsonl`, metrics contents, model weights, or
  other run artifacts.
- Do not edit the source task JSONL files. Their line counts are validated by
  the preflight command.

## Setup

Follow `README.md`. Install a CUDA-compatible PyTorch build first, then
`requirements.txt`. The reference run used Python 3.11, Torch 2.12.0+cu130,
and Transformers 5.8.1; compatible CUDA hardware may require a different Torch
wheel while Transformers must stay at 5.8.1.

The Llama checkpoint is gated. Confirm that the private `HF_TOKEN` has accepted
Meta Llama 3.1 access before starting. The other checkpoints must also be
downloadable. Expect roughly 70--90 GB of model-cache disk even though only one
model is resident on the GPU at a time.

Run dataset preflight before inference:

```bash
.venv/bin/python scripts/run_campaign.py --preflight-only
```

## Launch choices

- Free-form/single GPU: start the status watcher, then run
  `.venv/bin/python scripts/run_campaign.py`. It executes all ten jobs
  sequentially.
- PBS: inspect and adapt queue/account directives in
  `scripts/pbs_pair_ctrl_external.pbs`, then use
  `scripts/submit_pbs_campaign.sh`. It creates a serialized dependency chain.
- Slurm: inspect partition/account directives in
  `scripts/slurm_pair_ctrl_external.sbatch`, then use
  `scripts/submit_slurm_campaign.sh`. It also serializes the jobs.

Do not invent a fourth launch path until the actual scheduler is identified.
After launch, report the scheduler IDs or free-form PID, GPU model, available
disk, and the first successful status POST.

## Returning results

When jobs finish, preserve the entire `outputs/PAIR-CTRL/` and `logs/` trees.
Create an archive without model caches, virtual environments, or credentials.
Return the archive plus its SHA-256 checksum to the owner.
