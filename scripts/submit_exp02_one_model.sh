#!/usr/bin/env bash
# Submit a single EXP-02 GPU job (e.g. retry Llama after HF token is configured).
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
cd "$ROOT"
export PATH="/opt/pbs/bin:${PATH:-}"

MODEL="${MODEL:-${1:-}}"
if [[ -z "$MODEL" ]]; then
  echo "ERROR: set MODEL=org/model-name or pass the model as the first argument." >&2
  exit 1
fi
MIG_UUID="${MIG_UUID:?Set MIG_UUID from nvidia-smi -L}"
COUNT_PROFILE="${COUNT_PROFILE:-configs/counts_p0.json}"
COUNT_GSM8K="${COUNT_GSM8K:-100}"
COUNT_MMLU="${COUNT_MMLU:-100}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,negative_capability}"
PROMPT_PLACEMENT="${PROMPT_PLACEMENT:-system}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-256}"
BATCH_SIZE="${BATCH_SIZE:-1}"
WALLTIME="${WALLTIME:-06:00:00}"
RUN_DIR="${RUN_DIR:-$ROOT/outputs/EXP-02/$(echo "$MODEL" | tr '/:' '__')_$(date +%Y%m%d_%H%M%S)}"

slug="$(echo "$MODEL" | tr '/:' '__')"
log_path="$ROOT/logs/overnight/${slug}_retry_$(date +%Y%m%d_%H%M%S).pbs.log"
env_path="${log_path%.pbs.log}.env"
mkdir -p "$(dirname "$log_path")" "$(dirname "$RUN_DIR")"

{
  printf 'CONDITIONS=%q\n' "$CONDITIONS"
  printf 'PROMPT_PLACEMENT=%q\n' "$PROMPT_PLACEMENT"
} >"$env_path"

vars="MIG_UUID=${MIG_UUID},MODEL=${MODEL}"
vars="${vars},COUNTS_FILE=${COUNT_PROFILE}"
vars="${vars},COUNT_GSM8K=${COUNT_GSM8K}"
vars="${vars},COUNT_MMLU=${COUNT_MMLU}"
vars="${vars},MAX_NEW_TOKENS=${MAX_NEW_TOKENS}"
vars="${vars},BATCH_SIZE=${BATCH_SIZE}"
vars="${vars},RUN_DIR=${RUN_DIR}"
vars="${vars},JOB_ENV_FILE=${env_path}"

job_id="$(qsub -N "caisc_${slug:0:12}" -l "walltime=$WALLTIME" -v "$vars" -o "$log_path" scripts/pbs_exp02_gpu_smoke.pbs)"
echo "Submitted $MODEL -> $job_id"
echo "RUN_DIR=$RUN_DIR"
echo "LOG=$log_path"
qstat -u "$USER" || true
