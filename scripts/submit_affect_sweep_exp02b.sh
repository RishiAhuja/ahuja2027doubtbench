#!/usr/bin/env bash
# Submit EXP-02B system-placement affect/persona sweep for open models.
#
# This extends the melancholic result with the already audited EXP-01 affect
# prompts and neutral persona controls, using the same objective benchmark
# profile as EXP-02B.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
cd "$ROOT"

COUNT_PROFILE="${COUNT_PROFILE:-configs/counts_exp02b.json}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,euphoric,anxious,grandiose,neutral_archivist,neutral_cartographer,neutral_librarian}"
PROMPT_PLACEMENT="${PROMPT_PLACEMENT:-system}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-384}"
BATCH_SIZE="${BATCH_SIZE:-1}"
WALLTIME="${WALLTIME:-24:00:00}"
BATCH_PREFIX="${BATCH_PREFIX:-affect_sweep_system}"

MODELS=("$@")
if [[ "${#MODELS[@]}" -eq 0 ]]; then
  MODELS=(
    "Qwen/Qwen2.5-7B-Instruct"
    "meta-llama/Llama-3.1-8B-Instruct"
    "mistralai/Mistral-7B-Instruct-v0.3"
  )
fi

export COUNT_PROFILE CONDITIONS PROMPT_PLACEMENT MAX_NEW_TOKENS BATCH_SIZE WALLTIME BATCH_PREFIX
exec bash scripts/submit_exp02_scaleup.sh "${MODELS[@]}"
