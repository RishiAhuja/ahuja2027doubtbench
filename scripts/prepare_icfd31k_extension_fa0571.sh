#!/usr/bin/env bash
set -euo pipefail

REMOTE="it_FA0571@10.10.11.201"
REMOTE_ROOT="/Data3/it_FA0571/icfd31k_extension"
LOCAL_DATA="${1:-/Users/rishi/git/fraud-detection-data-generation-pipeline/final_upload_format}"

test -f "${LOCAL_DATA}/release_summary.json"
ssh "${REMOTE}" "mkdir -p '${REMOTE_ROOT}/data' '${REMOTE_ROOT}/logs' '${REMOTE_ROOT}/outputs' /Data3/it_FA0571/caisc/experiments /Data3/it_FA0571/caisc/scripts"
rsync -a --exclude='.DS_Store' "${LOCAL_DATA}/" "${REMOTE}:${REMOTE_ROOT}/data/final_upload_format/"
rsync -a experiments/icfd31k_extension/ "${REMOTE}:/Data3/it_FA0571/caisc/experiments/icfd31k_extension/"
rsync -a scripts/pbs_icfd31k_gpu_suite.pbs scripts/pbs_icfd31k_cpu_suite.pbs \
  "${REMOTE}:/Data3/it_FA0571/caisc/scripts/"

ssh "${REMOTE}" "cd '${REMOTE_ROOT}/data/final_upload_format' && sha256sum -c checksums.sha256"
echo "Prepared ${REMOTE_ROOT}; no PBS jobs submitted."
