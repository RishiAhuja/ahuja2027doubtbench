#!/usr/bin/env bash
# Submit EXP-02B task-prefix placement sweeps for the open-model panel.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
cd "$ROOT"

COUNT_PROFILE="${COUNT_PROFILE:-configs/counts_exp02b.json}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,capability_denial_only,self_doubt_only,explicit_sabotage}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-384}"
BATCH_SIZE="${BATCH_SIZE:-1}"
WALLTIME="${WALLTIME:-24:00:00}"
BATCH_PREFIX="${BATCH_PREFIX:-task_vs_system_task_prefix}"
PROMPT_PLACEMENT="${PROMPT_PLACEMENT:-task_prefix}"

MODELS=("$@")
if [[ "${#MODELS[@]}" -eq 0 ]]; then
  MODELS=(
    "Qwen/Qwen2.5-7B-Instruct"
    "meta-llama/Llama-3.1-8B-Instruct"
    "mistralai/Mistral-7B-Instruct-v0.3"
  )
fi

export COUNT_PROFILE CONDITIONS MAX_NEW_TOKENS BATCH_SIZE WALLTIME BATCH_PREFIX PROMPT_PLACEMENT
exec bash scripts/submit_exp02_scaleup.sh "${MODELS[@]}"
