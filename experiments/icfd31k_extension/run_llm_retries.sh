#!/usr/bin/env bash
set -uo pipefail

: "${ICFD31K_DATA_ROOT:?Set ICFD31K_DATA_ROOT to final_upload_format}"
: "${ICFD31K_OUTPUT_ROOT:?Set ICFD31K_OUTPUT_ROOT}"

PYTHON_BIN="${ICFD31K_PYTHON:-python}"
PROMPT_FORMAT="${ICFD31K_PROMPT_FORMAT:-raw}"
FAILURES=0

run_stage() {
  local stage="$1"
  shift
  echo "[$(date --iso-8601=seconds)] START ${stage}"
  if "$@"; then
    echo "[$(date --iso-8601=seconds)] COMPLETE ${stage}"
  else
    local status=$?
    echo "[$(date --iso-8601=seconds)] FAILED ${stage} exit=${status}"
    FAILURES=$((FAILURES + 1))
  fi
}

# Retry only the zero-shot stages that did not finish in the primary suite.
# Existing raw JSONL files resume by stable (split, sample_id) keys.
LLM_SPECS=(
  "google/gemma-1.1-2b-it|32"
  "google/gemma-3-1b-it|32"
  "meta-llama/Llama-3.2-1B-Instruct|32"
  "HuggingFaceTB/SmolLM2-1.7B-Instruct|16"
)

for spec in "${LLM_SPECS[@]}"; do
  model="${spec%%|*}"
  batch="${spec##*|}"
  run_stage "llm-retry:${model}" "${PYTHON_BIN}" -m experiments.icfd31k_extension.llm_eval \
    --model "${model}" \
    --data-root "${ICFD31K_DATA_ROOT}" \
    --output-root "${ICFD31K_OUTPUT_ROOT}" \
    --splits test cross_domain \
    --batch-size "${batch}" \
    --prompt-format "${PROMPT_FORMAT}" \
    --max-input-tokens 2048 \
    --max-new-tokens 150 \
    --temperature 0.1 \
    --seed 42
done

echo "[$(date --iso-8601=seconds)] LLM retry suite finished failures=${FAILURES}"
exit "${FAILURES}"
