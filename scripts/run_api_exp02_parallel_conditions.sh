#!/usr/bin/env bash
# Run one EXP-02 API model with one worker per condition, then merge/finalize.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
PROFILE="${PROFILE:-configs/counts_p0.json}"
MODEL="${MODEL:?Set MODEL=provider:model}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,negative_capability}"
MAX_TOKENS="${MAX_TOKENS:-768}"
REASONING_EFFORT="${REASONING_EFFORT:-}"
THINKING_BUDGET="${THINKING_BUDGET:-}"
BATCH_ID="${BATCH_ID:-$(date +%Y%m%d_%H%M%S)}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

slug="$(echo "$MODEL" | tr '/:' '___')"
BATCH_DIR="$ROOT/logs/api_exp02_parallel/batch_${BATCH_ID}/${slug}"
OUT_ROOT="$ROOT/outputs/EXP-02/api_parallel_${BATCH_ID}/${slug}"
MERGED_DIR="$OUT_ROOT/merged"
mkdir -p "$BATCH_DIR" "$OUT_ROOT"

IFS=',' read -r -a CONDITION_LIST <<<"$CONDITIONS"

echo "===== CAISc EXP-02 parallel API model ====="
echo "Model:      $MODEL"
echo "Profile:    $PROFILE"
echo "Conditions: ${CONDITION_LIST[*]}"
echo "Output:     $MERGED_DIR"
echo "Logs:       $BATCH_DIR"
echo

if "$PYTHON" -m experiments.exp02.verify_benchmarks --counts-file "$PROFILE"; then
  echo "Benchmark cache already satisfies $PROFILE"
else
  "$PYTHON" scripts/download_benchmark_data.py 200 200 200
  "$PYTHON" -m experiments.exp02.verify_benchmarks --counts-file "$PROFILE"
fi

pids=()
for condition in "${CONDITION_LIST[@]}"; do
  condition="$(echo "$condition" | xargs)"
  [[ -n "$condition" ]] || continue
  out_dir="$OUT_ROOT/$condition"
  log_path="$BATCH_DIR/$condition.log"
  args=(
    -m experiments.exp02.run_smoke
    --counts-file "$PROFILE"
    --conditions "$condition"
    --model "$MODEL"
    --max-tokens "$MAX_TOKENS"
    --out "$out_dir"
  )
  if [[ -n "$REASONING_EFFORT" ]]; then
    args+=(--reasoning-effort "$REASONING_EFFORT")
  fi
  if [[ -n "$THINKING_BUDGET" ]]; then
    args+=(--thinking-budget "$THINKING_BUDGET")
  fi
  echo "Starting $condition -> $out_dir"
  PYTHONUNBUFFERED=1 "$PYTHON" "${args[@]}" >"$log_path" 2>&1 &
  pids+=("$!")
done

failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    failed=1
  fi
done
if [[ "$failed" != "0" ]]; then
  echo "ERROR: one or more condition workers failed; see $BATCH_DIR" >&2
  exit 1
fi

"$PYTHON" scripts/merge_exp02_condition_runs.py --out "$MERGED_DIR" "$OUT_ROOT"/*
echo
echo "Merged complete: $MERGED_DIR"
