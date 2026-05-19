#!/usr/bin/env bash
# Submit paired EXP-02B system-vs-task-placement sweeps on cluster.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
cd "$ROOT"

COUNT_PROFILE="${COUNT_PROFILE:-configs/counts_exp02b.json}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,capability_denial_only,self_doubt_only,explicit_sabotage}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-384}"
WALLTIME="${WALLTIME:-24:00:00}"

MODELS=("$@")
if [[ "${#MODELS[@]}" -eq 0 ]]; then
  MODELS=(
    "Qwen/Qwen2.5-7B-Instruct"
    "meta-llama/Llama-3.1-8B-Instruct"
    "mistralai/Mistral-7B-Instruct-v0.3"
  )
fi

export COUNT_PROFILE CONDITIONS MAX_NEW_TOKENS WALLTIME

PROMPT_PLACEMENT=system BATCH_PREFIX=task_vs_system_system \
  bash scripts/submit_exp02_scaleup.sh "${MODELS[@]}"

system_batch="$(cat "$ROOT/logs/task_vs_system_system/latest_batch.txt")"
system_last_job="$(cat "$system_batch/last_job.txt")"

PROMPT_PLACEMENT=task_suffix BATCH_PREFIX=task_vs_system_task_suffix INITIAL_DEPEND_JOB="$system_last_job" \
  bash scripts/submit_exp02_scaleup.sh "${MODELS[@]}"
