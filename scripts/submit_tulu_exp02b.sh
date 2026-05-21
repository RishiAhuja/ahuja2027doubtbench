#!/usr/bin/env bash
# Submit EXP-02B decomposition on Tulu 3 post-training stages.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
cd "$ROOT"

COUNT_PROFILE="${COUNT_PROFILE:-configs/counts_exp02b.json}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,capability_denial_only,self_doubt_only,explicit_sabotage}"
PROMPT_PLACEMENT="${PROMPT_PLACEMENT:-system}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-384}"
BATCH_SIZE="${BATCH_SIZE:-1}"
WALLTIME="${WALLTIME:-24:00:00}"
BATCH_PREFIX="${BATCH_PREFIX:-exp05_tulu}"

MODELS=(
  "allenai/Llama-3.1-Tulu-3-8B-SFT"
  "allenai/Llama-3.1-Tulu-3-8B-DPO"
  "allenai/Llama-3.1-Tulu-3.1-8B"
)

export COUNT_PROFILE CONDITIONS PROMPT_PLACEMENT MAX_NEW_TOKENS BATCH_SIZE WALLTIME BATCH_PREFIX
exec bash scripts/submit_exp02_scaleup.sh "${MODELS[@]}"
