#!/usr/bin/env bash
# Submit the missing EXP-02B task-prefix placement campaign.
#
# This completes the placement grid after the existing system and task-suffix
# runs: open Llama/Qwen/Mistral first, then Tulu SFT/DPO/RLVR.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
cd "$ROOT"

COUNT_PROFILE="${COUNT_PROFILE:-configs/counts_exp02b.json}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,capability_denial_only,self_doubt_only,explicit_sabotage}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-384}"
BATCH_SIZE="${BATCH_SIZE:-1}"
WALLTIME="${WALLTIME:-24:00:00}"
DEPEND_TYPE="${DEPEND_TYPE:-afterany}"
INITIAL_DEPEND_JOB="${INITIAL_DEPEND_JOB:-}"

export COUNT_PROFILE CONDITIONS MAX_NEW_TOKENS BATCH_SIZE WALLTIME DEPEND_TYPE

PROMPT_PLACEMENT=task_prefix \
BATCH_PREFIX=task_vs_system_task_prefix \
INITIAL_DEPEND_JOB="$INITIAL_DEPEND_JOB" \
  bash scripts/submit_task_prefix_exp02b.sh

open_batch="$(cat "$ROOT/logs/task_vs_system_task_prefix/latest_batch.txt")"
open_last_job="$(cat "$open_batch/last_job.txt")"

PROMPT_PLACEMENT=task_prefix \
BATCH_PREFIX=task_vs_system_tulu_task_prefix \
INITIAL_DEPEND_JOB="$open_last_job" \
  bash scripts/submit_tulu_exp02b.sh
