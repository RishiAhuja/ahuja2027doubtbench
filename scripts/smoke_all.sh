#!/usr/bin/env bash
# Local smoke: load all benchmarks, then optional API run (Groq / OpenAI / Claude).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
PROFILE="${PROFILE:-configs/counts_smoke.json}"

echo "===== 1/2 Benchmark load smoke ====="
"$PYTHON" -m experiments.exp02.verify_benchmarks --counts-file "$PROFILE"

if [[ "${SKIP_API:-}" == "1" ]]; then
  echo "SKIP_API=1 set; done."
  exit 0
fi

MODEL="${SMOKE_MODEL:-groq:llama-3.1-8b-instant}"
if [[ -z "${GROQ_API_KEY:-}${OPENAI_API_KEY:-}${ANTHROPIC_API_KEY:-}" ]]; then
  echo "No API keys in env; skipping inference smoke (load-only passed)."
  exit 0
fi

echo
echo "===== 2/2 API inference smoke ($MODEL) ====="
"$PYTHON" -m experiments.exp02.run_smoke \
  --counts-file "$PROFILE" \
  --model "$MODEL" \
  --max-tokens 512

echo
echo "Smoke complete."
