#!/usr/bin/env bash
# Submit a strictly serialized Slurm chain for all manifest jobs.
set -euo pipefail

PACKAGE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PACKAGE_ROOT"
command -v sbatch >/dev/null || { echo "sbatch is not available" >&2; exit 2; }
mkdir -p logs/slurm

mapfile -t ORDERS < <(.venv/bin/python -c 'import json; print(*[j["external_order"] for j in json.load(open("campaign.json"))["jobs"]], sep="\n")')
previous=""
for order in "${ORDERS[@]}"; do
  args=(--parsable --job-name="pce_${order}" --export="ALL,JOB_ORDER=${order}")
  if [[ -n "$previous" ]]; then
    args+=(--dependency="afterany:${previous}")
  fi
  job_id=$(sbatch "${args[@]}" scripts/slurm_pair_ctrl_external.sbatch)
  printf 'external_order=%s job_id=%s dependency=%s\n' "$order" "$job_id" "${previous:-none}"
  previous=$job_id
done
