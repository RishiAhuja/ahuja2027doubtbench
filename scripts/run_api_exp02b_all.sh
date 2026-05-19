#!/usr/bin/env bash
# EXP-02B API sweep with concurrent workers per model.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
PROFILE="${PROFILE:-configs/counts_exp02b.json}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,capability_denial_only,self_doubt_only,explicit_sabotage}"
MAX_TOKENS="${MAX_TOKENS:-768}"
WORKERS="${WORKERS:-12}"
BATCH_ID="${BATCH_ID:-$(date +%Y%m%d_%H%M%S)}"
OUT_ROOT="$ROOT/outputs/EXP-02B/api_${BATCH_ID}"
LOG_ROOT="$ROOT/logs/api_exp02b/batch_${BATCH_ID}"
mkdir -p "$OUT_ROOT" "$LOG_ROOT"
echo "$LOG_ROOT" > "$ROOT/logs/api_exp02b_latest_batch.txt"

IFS=',' read -r -a MODELS <<<"${API_MODELS:-openai:gpt-5.4-mini,openai:gpt-5.5,anthropic:claude-haiku-4-5-20251001}"

echo "EXP-02B API batch: $BATCH_ID"
echo "Profile: $PROFILE"
echo "Conditions: $CONDITIONS"
echo "Workers/model: $WORKERS"

"$PYTHON" -m experiments.exp02.verify_benchmarks --counts-file "$PROFILE"

for model in "${MODELS[@]}"; do
  [[ -n "$model" ]] || continue
  slug="$(echo "$model" | tr '/:' '___')"
  echo "Starting $model"
  "$PYTHON" scripts/run_api_exp02_sharded.py \
    --model "$model" \
    --counts-file "$PROFILE" \
    --conditions "$CONDITIONS" \
    --max-tokens "$MAX_TOKENS" \
    --workers "$WORKERS" \
    --out "$OUT_ROOT/$slug" \
    > "$LOG_ROOT/$slug.log" 2>&1 &
done

wait
echo "EXP-02B API batch complete: $OUT_ROOT"
