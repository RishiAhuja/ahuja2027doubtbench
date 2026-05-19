#!/usr/bin/env bash
# Local EXP-02 API sweep: OpenAI + Claude cheap models, same protocol as cluster runs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
PROFILE="${PROFILE:-configs/counts_api_dev.json}"
MAX_TOKENS="${MAX_TOKENS:-768}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "===== Cost estimate ====="
"$PYTHON" scripts/estimate_api_cost.py --counts-file "$PROFILE"

if [[ -z "${OPENAI_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ERROR: set OPENAI_API_KEY and/or ANTHROPIC_API_KEY in .env" >&2
  exit 1
fi

echo
echo "===== Benchmark load check ====="
"$PYTHON" scripts/download_benchmark_data.py 50 100 150 2>/dev/null || true
SKIP_API=1 PROFILE="$PROFILE" bash scripts/smoke_all.sh

run_model() {
  local model="$1"
  shift
  echo
  echo "===== Running $model ====="
  # Use "$@" not an array — empty "${arr[@]}" trips set -u on macOS bash.
  "$PYTHON" -m experiments.exp02.run_smoke \
    --counts-file "$PROFILE" \
    --model "$model" \
    --max-tokens "$MAX_TOKENS" \
    "$@"
}

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  run_model "openai:gpt-4.1-mini"
  # Uncomment for cheapest OpenAI-only pass:
  # run_model "openai:gpt-4.1-nano"
  # Native reasoning chain spot-check (higher cost):
  # run_model "openai:o4-mini" --reasoning-effort low
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  run_model "anthropic:claude-haiku-4-5-20251001"
fi

echo
echo "===== Latest runs ====="
ls -td outputs/EXP-02/smoke_* 2>/dev/null | head -3 || true
echo
echo "Inspect reasoning chains:"
echo "  python -m experiments.exp02.inspect_reasoning --latest"
