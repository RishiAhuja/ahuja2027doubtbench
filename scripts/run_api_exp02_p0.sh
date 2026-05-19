#!/usr/bin/env bash
# Full EXP-02 API validation sweep. Runs locally, sequentially, with durable logs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
PROFILE="${PROFILE:-configs/counts_p0.json}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,negative_capability}"
MAX_TOKENS="${MAX_TOKENS:-768}"
RUN_REASONING="${RUN_REASONING:-1}"
REASONING_EFFORT="${REASONING_EFFORT:-low}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ERROR: set OPENAI_API_KEY and/or ANTHROPIC_API_KEY in .env" >&2
  exit 1
fi

IFS=',' read -r -a MODELS <<<"${API_MODELS:-openai:gpt-5.4-mini,openai:gpt-5.5,anthropic:claude-haiku-4-5-20251001}"
IFS=',' read -r -a REASONING_MODELS <<<"${API_REASONING_MODELS:-openai:gpt-5.4-mini}"

BATCH_ID="$(date +%Y%m%d_%H%M%S)"
BATCH_DIR="$ROOT/logs/api_exp02/batch_${BATCH_ID}"
OUT_ROOT="$ROOT/outputs/EXP-02/api_p0_${BATCH_ID}"
mkdir -p "$BATCH_DIR" "$OUT_ROOT"
echo "$BATCH_DIR" > "$ROOT/logs/api_exp02/latest_batch.txt"

echo "===== CAISc EXP-02 API P0 validation ====="
echo "Batch:      $BATCH_DIR"
echo "Outputs:    $OUT_ROOT"
echo "Profile:    $PROFILE"
echo "Conditions: $CONDITIONS"
echo "Max tokens: $MAX_TOKENS"
echo "Models:     ${MODELS[*]}"
if [[ "$RUN_REASONING" == "1" ]]; then
  echo "Reasoning:  ${REASONING_MODELS[*]} ($REASONING_EFFORT)"
fi
echo

echo "===== Benchmark caches ====="
"$PYTHON" scripts/download_benchmark_data.py 200 200 200
"$PYTHON" -m experiments.exp02.verify_benchmarks --counts-file "$PROFILE"

echo
echo "===== Cost estimate ====="
"$PYTHON" scripts/estimate_api_cost.py --counts-file "$PROFILE" --models "$(IFS=','; echo "${MODELS[*]}")"

: > "$BATCH_DIR/manifest.tsv"

run_model() {
  local model="$1"
  local suffix="${2:-}"
  shift 2 || true
  local slug
  slug="$(echo "${model}${suffix}" | tr '/:' '___')"
  local out_dir="$OUT_ROOT/$slug"
  local log_path="$BATCH_DIR/$slug.log"
  printf '%s\t%s\t%s\n' "$model" "$out_dir" "$log_path" >> "$BATCH_DIR/manifest.tsv"
  echo
  echo "===== Running $model$suffix ====="
  echo "Output: $out_dir"
  echo "Log:    $log_path"
  PYTHONUNBUFFERED=1 "$PYTHON" -m experiments.exp02.run_smoke \
    --counts-file "$PROFILE" \
    --conditions "$CONDITIONS" \
    --model "$model" \
    --max-tokens "$MAX_TOKENS" \
    --out "$out_dir" \
    "$@" 2>&1 | tee "$log_path"
}

for model in "${MODELS[@]}"; do
  [[ -n "$model" ]] || continue
  run_model "$model" ""
done

if [[ "$RUN_REASONING" == "1" ]]; then
  for model in "${REASONING_MODELS[@]}"; do
    [[ -n "$model" ]] || continue
    run_model "$model" "_reasoning_${REASONING_EFFORT}" --reasoning-effort "$REASONING_EFFORT"
  done
fi

echo
echo "API EXP-02 P0 complete: $OUT_ROOT"
