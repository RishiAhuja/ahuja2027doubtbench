# PAIR-CTRL external top-ten campaign

This bundle contains the ten highest-priority unfinished PAIR-CTRL runs. It is
designed for a single 45--48 GB NVIDIA GPU and works on a free-form machine,
PBS, or Slurm. The safe default is one inference process at a time.

## Workload

- 10 ordered jobs
- 4 checkpoints: Mistral-7B-Instruct, Tulu-3-8B-SFT,
  Llama-3.1-8B-Instruct, and Tulu-3-8B-DPO
- 12,400 latent tasks
- 124,000 deterministic responses
- 5 prompt conditions crossed with 2 task templates

`campaign.json` is the machine-readable source of truth. `AGENTS.md` contains
mandatory instructions for an agent operating the cluster.

## 1. Unpack and inspect

```bash
tar -xzf pair_ctrl_external_top10_20260811.tar.gz
cd pair_ctrl_external_top10_20260811
nvidia-smi
python3 --version
df -h .
command -v qsub || true
command -v sbatch || true
```

## 2. Create the environment

Install the PyTorch wheel appropriate for the cluster CUDA driver first. Then:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
# Install the site-appropriate CUDA build of torch before this line.
python -m pip install -r requirements.txt
```

The reference environment is recorded in `reference-environment.txt`.

Set Hugging Face access privately. Llama 3.1 requires an account that has
accepted its license:

```bash
export HF_TOKEN='set-this-privately'
export HF_HOME="$PWD/hf_cache"
```

Do not paste the token into logs or commit it to this directory.

## 3. Validate the package

```bash
.venv/bin/python scripts/run_campaign.py --preflight-only
.venv/bin/python scripts/post_status.py --dry-run
```

Preflight validates every included task file and expected row count without
loading a model or starting inference.

## 4. Configure compact status updates

The existing receiver is:

```text
https://rishia.in/api/cluster-progress/ingest
```

This receiver accepts unauthenticated, strictly bounded counters for this one
campaign. No token or private environment file is required:

```bash
nohup bash scripts/watch_status.sh 600 >/dev/null 2>&1 &
echo $! > state/status-watcher.pid
```

The watcher posts row counts, job states, percentage, hostname, and a compact
summary. It never posts output text or metrics contents. The public endpoint
accepts only campaign `pair-ctrl-external-top10-20260811` with its fixed total
of 124,000 response rows; all other campaigns remain authenticated.

## 5A. Free-form launch

```bash
nohup .venv/bin/python scripts/run_campaign.py \
  > logs/campaign.log 2>&1 &
echo $! > state/campaign.pid
```

To resume after interruption, run the same command. Completed jobs are skipped
after structural verification; partial jobs resume from their JSONL rows.

To run one selected job:

```bash
.venv/bin/python scripts/run_job.py --external-order 1
```

## 5B. PBS launch

Review the resource/queue lines in `scripts/pbs_pair_ctrl_external.pbs`, then:

```bash
bash scripts/submit_pbs_campaign.sh
```

## 5C. Slurm launch

Review the partition/account lines in `scripts/slurm_pair_ctrl_external.sbatch`,
then:

```bash
bash scripts/submit_slurm_campaign.sh
```

Both scheduler launchers build a serialized dependency chain; they do not run
two models on one GPU concurrently.

## Completion and return

Exit 0 passes all quality gates. Exit 3 is still structurally complete but must
be labelled as a parse/truncation quality-gate failure. Other nonzero exits stop
the sequential campaign.

Return `outputs/PAIR-CTRL/`, `logs/`, and `state/`. Do not return `.venv/`,
`hf_cache/`, or the private webhook environment file.
