#!/usr/bin/env bash
# Generic Slurm template. The operator must adapt partition/account directives.
#SBATCH --job-name=pce_job
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=logs/slurm/%x_%j.log

set -euo pipefail
PACKAGE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PACKAGE_ROOT"
: "${JOB_ORDER:?Submit with JOB_ORDER=<external order>}"
exec .venv/bin/python scripts/run_job.py --external-order "$JOB_ORDER"

