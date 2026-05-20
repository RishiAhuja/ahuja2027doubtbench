#!/usr/bin/env bash
# Submit task-prefix and task-suffix prompt-length salience ladder.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
cd "$ROOT"

COUNT_PROFILE="${COUNT_PROFILE:-configs/counts_salience.json}"
CONDITIONS="${CONDITIONS:-baseline,melancholic_10,melancholic,melancholic_150,melancholic_250,neutral_plain_10,neutral_plain_50,neutral_plain_150,neutral_plain_250}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-384}"
WALLTIME="${WALLTIME:-24:00:00}"
DEPEND_TYPE="${DEPEND_TYPE:-afterany}"
INITIAL_DEPEND_JOB="${INITIAL_DEPEND_JOB:-}"

MODELS=("$@")
if [[ "${#MODELS[@]}" -eq 0 ]]; then
  MODELS=(
    "Qwen/Qwen2.5-7B-Instruct"
    "meta-llama/Llama-3.1-8B-Instruct"
    "allenai/Llama-3.1-Tulu-3-8B-DPO"
  )
fi

export COUNT_PROFILE CONDITIONS MAX_NEW_TOKENS WALLTIME DEPEND_TYPE

PROMPT_PLACEMENT=task_prefix \
BATCH_PREFIX=salience_ladder_task_prefix \
INITIAL_DEPEND_JOB="$INITIAL_DEPEND_JOB" \
  bash scripts/submit_exp02_scaleup.sh "${MODELS[@]}"

prefix_batch="$(cat "$ROOT/logs/salience_ladder_task_prefix/latest_batch.txt")"
prefix_last_job="$(cat "$prefix_batch/last_job.txt")"

PROMPT_PLACEMENT=task_suffix \
BATCH_PREFIX=salience_ladder_task_suffix \
INITIAL_DEPEND_JOB="$prefix_last_job" \
  bash scripts/submit_exp02_scaleup.sh "${MODELS[@]}"
