#!/usr/bin/env bash
# Submit a strictly serialized PBS chain for all manifest jobs.
set -euo pipefail

PACKAGE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PACKAGE_ROOT"
command -v qsub >/dev/null || { echo "qsub is not available" >&2; exit 2; }
mkdir -p logs/pbs

mapfile -t ORDERS < <(.venv/bin/python -c 'import json; print(*[j["external_order"] for j in json.load(open("campaign.json"))["jobs"]], sep="\n")')
previous=""
for order in "${ORDERS[@]}"; do
  args=(-N "pce_${order}" -v "JOB_ORDER=${order}" -o "logs/pbs/order_${order}.log")
  if [[ -n "$previous" ]]; then
    args+=(-W "depend=afterany:${previous}")
  fi
  job_id=$(qsub "${args[@]}" scripts/pbs_pair_ctrl_external.pbs)
  printf 'external_order=%s job_id=%s dependency=%s\n' "$order" "$job_id" "${previous:-none}"
  previous=$job_id
done

