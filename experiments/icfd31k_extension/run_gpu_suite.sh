#!/usr/bin/env bash
set -uo pipefail

: "${ICFD31K_DATA_ROOT:?Set ICFD31K_DATA_ROOT to final_upload_format}"
: "${ICFD31K_OUTPUT_ROOT:?Set ICFD31K_OUTPUT_ROOT}"

PYTHON_BIN="${ICFD31K_PYTHON:-python}"
PROMPT_FORMAT="${ICFD31K_PROMPT_FORMAT:-raw}"
RUN_STREAMING="${ICFD31K_RUN_STREAMING:-1}"
FAILURES=0

"${PYTHON_BIN}" -m experiments.icfd31k_extension.preflight \
  --mode gpu --data-root "${ICFD31K_DATA_ROOT}" --check-model-access

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

# Published Gemma semantics: same policy-conditioned zero-shot prompt, 2048 input
# tokens, 150 sampled output tokens, temperature 0.1. Only batching/model adapters differ.
LLM_SPECS=(
  # Historical paper baseline, rerun on the same frozen manifest as every new LLM.
  "google/gemma-1.1-2b-it|96"
  "google/gemma-3-1b-it|128"
  "meta-llama/Llama-3.2-1B-Instruct|128"
  "ibm-granite/granite-4.0-1b|64"
  "Qwen/Qwen3-1.7B|96"
  "HuggingFaceTB/SmolLM2-1.7B-Instruct|192"
)
for spec in "${LLM_SPECS[@]}"; do
  model="${spec%%|*}"
  batch="${spec##*|}"
  run_stage "llm:${model}" "${PYTHON_BIN}" -m experiments.icfd31k_extension.llm_eval \
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

# Fine-tuning deliberately starts only after every zero-shot LLM attempt has
# reached a terminal state. run_stage records individual failures without
# preventing the remaining comparable models from running.
ENCODER_SPECS=(
  "google/mobilebert-uncased|64|128"
  "distilbert/distilbert-base-uncased|64|128"
  "answerdotai/ModernBERT-base|32|64"
)
for spec in "${ENCODER_SPECS[@]}"; do
  model="${spec%%|*}"
  rest="${spec#*|}"
  train_batch="${rest%%|*}"
  eval_batch="${rest##*|}"
  run_stage "encoder:${model}:static" "${PYTHON_BIN}" -m experiments.icfd31k_extension.train_encoder \
    --model "${model}" --task static \
    --data-root "${ICFD31K_DATA_ROOT}" --output-root "${ICFD31K_OUTPUT_ROOT}" \
    --batch-size "${train_batch}" --eval-batch-size "${eval_batch}" \
    --max-length 512 --epochs 5 --learning-rate 2e-5 --seed 42
  if [[ "${RUN_STREAMING}" == "1" ]]; then
    run_stage "encoder:${model}:streaming" "${PYTHON_BIN}" -m experiments.icfd31k_extension.train_encoder \
      --model "${model}" --task streaming \
      --data-root "${ICFD31K_DATA_ROOT}" --output-root "${ICFD31K_OUTPUT_ROOT}" \
      --batch-size "${train_batch}" --eval-batch-size "${eval_batch}" \
      --max-length 512 --epochs 5 --learning-rate 2e-5 --seed 42
  fi
done

echo "[$(date --iso-8601=seconds)] GPU suite finished failures=${FAILURES}"
exit "${FAILURES}"
