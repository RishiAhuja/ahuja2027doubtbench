# NITJ HPC Cluster Runbook

Source docs read on 2026-05-19. Access was re-verified on 2026-08-08 with the
current project account:

- `~/git/vlm/GPU_CPU_UserManual.docx`
- `~/git/vlm/HPC FAQ.docx`
- Existing cluster PBS scripts under `/Data3/it_FA0571/vlm/scripts/`

Cluster login:

```text
ssh it_FA0618@10.10.11.201
```

Do not commit credentials. The password is intentionally not recorded in this
repository.

Two project accounts were verified on 2026-08-08:

| Account | Remote home | Server-reported expiry | Current use |
|---|---|---|---|
| `it_FA0618` | `/Data1/it_FA0618` | 2026-08-09 | Qwen/Mistral EXP-18 campaign |
| `it_FA0571` | `/Data3/it_FA0571` | 2026-08-10 | Multi-model EXP-18 campaign |

The dates embedded in account-creation images can be stale; `chage -l` is the
operational value observed by the login server. Re-check it before scheduling
work beyond these dates. Each account remains limited to one GPU job at a time,
and simultaneous jobs across accounts must use different verified MIG UUIDs.

## Important Rules

- Access is booking-based and valid for a maximum of 15 days per booking.
- Account sharing is prohibited.
- Large files, model caches, datasets, and outputs must live under `/Data*`, not a small home directory.
- The cluster does not provide long-term backup. Pull results back after runs.
- All computational work must use PBS.
- CPU-only jobs must use `cpuq`.
- GPU jobs must use `workq`.
- CPU-only jobs submitted to `workq` can be automatically killed.
- Each user is restricted to one GPU instance at a time.
- Do not expose multiple GPUs in `CUDA_VISIBLE_DEVICES`.
- Local validation is required before cluster runs.
- Publications must acknowledge the NITJ HPC facility.

Required acknowledgement:

```text
The authors gratefully acknowledge the High Performance Computing (HPC) facility provided by Dr. B. R. Ambedkar National Institute of Technology Jalandhar (NIT Jalandhar) for supporting the computational requirements of this research work.
```

## Observed Cluster Layout

Remote home:

```text
/Data1/it_FA0618
```

Current CAISc working copy:

```text
/Data1/it_FA0618/caisc
```

Current Python environment and model cache:

```text
/Data1/it_FA0618/vlm-hpc/env/bin/python
/Data1/it_FA0618/vlm-hpc/hf-cache
```

PBS binaries:

```text
/opt/pbs/bin/qsub
/opt/pbs/bin/qstat
```

Observed GPU layout includes H100 MIG slices such as:

```text
MIG-4d38d5cf-c802-5308-80b8-251f3cec7480
MIG-9b919b48-2562-5791-8778-080ddb153351
MIG-c747c071-8b61-5993-a5e0-33f4b566bd6e
```

Always re-check with:

```bash
nvidia-smi -L
```

## GitHub Sync

Local machine:

```bash
git push
```

The current account does not have the older CAISc GitHub deploy key. Until a
new key is installed, synchronize only the required source files from the local
machine and exclude secrets and large artifacts:

```bash
rsync -az --exclude='.git' --exclude='.env' --exclude='outputs' \
  <required-paths> it_FA0618@10.10.11.201:/Data1/it_FA0618/caisc/
```

Do not put `.env` files or API keys in git.

### `it_FA0571` GitHub Access Status

The following notes apply specifically to `it_FA0571`; they do not describe
`it_FA0618`.

Checked on 2026-05-19:

- SSH to the cluster works from the NITJ network.
- HTTPS clone of `RishiAhuja/caisc` prompts for GitHub credentials, so anonymous clone is not available.
- SSH clone works with the CAISc deploy key at `~/.ssh/caisc_github_ed25519`.
- The repo is cloned at `/Data3/it_FA0571/caisc`.

Current CAISc cluster public key:

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIO5vty2ZYbD14kfmTCTdNjyBtuKHTwjc4Gu4mL5+48i+ caisc-cluster-github
```

Clone or pull with:

```bash
cd /Data3/it_FA0571
GIT_SSH_COMMAND="ssh -i ~/.ssh/caisc_github_ed25519 -o IdentitiesOnly=yes" \
  git clone git@github.com:RishiAhuja/caisc.git caisc
```

For an existing clone:

```bash
cd /Data3/it_FA0571/caisc
GIT_SSH_COMMAND="ssh -i ~/.ssh/caisc_github_ed25519 -o IdentitiesOnly=yes" \
  git pull --ff-only
```

## Queue Selection

CPU-only preprocessing, metrics, parsing:

```text
#PBS -q cpuq
#PBS -l select=1:ncpus=16
```

GPU inference with local/open models:

```text
#PBS -q workq
#PBS -l select=1:ncpus=8:ngpus=1
```

For GPU jobs, use one MIG UUID only:

```bash
export CUDA_VISIBLE_DEVICES=<single MIG UUID>
```

## Environment Pattern

Use the non-interactive conda setup in PBS scripts:

```bash
source /apps/compilers/anaconda3/etc/profile.d/conda.sh
conda activate <env_name>
export PYTHONNOUSERSITE=1
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export HF_HOME=/Data1/it_FA0618/vlm-hpc/hf-cache
export HUGGINGFACE_HUB_CACHE=$HF_HOME/hub
export TRANSFORMERS_CACHE=$HF_HOME/transformers
```

## EXP-02 Cluster Plan

Do not run the API version on the cluster. API runs are CPU/network-bound and should remain local.

Use the cluster only for open/local model inference:

- `meta-llama/Llama-3.1-8B-Instruct`
- `mistralai/Mistral-7B-Instruct-v0.3`
- `Qwen/Qwen2.5-7B-Instruct`

Proper cluster execution order:

1. Test EXP-02 locally with API backend.
2. Push code to GitHub.
3. Pull/clone repo on cluster.
4. Submit a tiny GPU smoke job to `workq` with one model, one MIG, and a tiny dataset.
5. Inspect logs and outputs.
6. Submit larger open-model jobs sequentially or with PBS dependencies, respecting one GPU instance.

## Monitoring

```bash
export PATH=/opt/pbs/bin:$PATH
qstat -u it_FA0618
tracejob <job_id>
```

Never bypass PBS by launching long GPU/CPU jobs directly on the login node.
