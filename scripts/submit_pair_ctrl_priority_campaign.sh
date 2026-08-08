#!/usr/bin/env bash
# Submit PAIR-CTRL in evidence priority order under short account lifetimes.

set -euo pipefail

PROFILE="${1:?usage: $0 fa0618|fa0571 AFTER_JOB_ID}"
LAST_JOB="${2:?usage: $0 fa0618|fa0571 AFTER_JOB_ID}"
ROOT="$(pwd)"
PBS_SCRIPT="$ROOT/scripts/pbs_exp18_factorial.pbs"

case "$PROFILE" in
  fa0618)
    PYTHON=/Data1/it_FA0618/vlm-hpc/env/bin/python
    HF_HOME=/Data1/it_FA0618/vlm-hpc/hf-cache
    MIG_UUID=MIG-c747c071-8b61-5993-a5e0-33f4b566bd6e
    ;;
  fa0571)
    PYTHON=/Data3/it_FA0571/.conda/envs/cultural_env/bin/python
    HF_HOME=/Data3/it_FA0571/hf_cache
    MIG_UUID=MIG-5eef67d0-7e58-5016-8973-1bf2618f6d54
    ;;
  *)
    echo "Unknown profile: $PROFILE" >&2
    exit 2
    ;;
esac

mkdir -p logs

submit() {
  local experiment_id="$1"
  local model="$2"
  local model_tag="$3"
  local data_file="$4"
  local output_log="$5"
  local dependency=()
  if [[ "$LAST_JOB" != "none" ]]; then
    dependency=(-W "depend=afterany:$LAST_JOB")
  fi
  LAST_JOB=$(qsub "${dependency[@]}" \
    -v "PYTHON=$PYTHON,HF_HOME=$HF_HOME,MIG_UUID=$MIG_UUID,EXPERIMENT_ID=$experiment_id,MODEL=$model,MODEL_TAG=$model_tag,DATA_FILE=$data_file,MAX_NEW_TOKENS=768,BATCH_SIZE=8,THINKING_MODE=auto" \
    -o "$output_log" \
    "$PBS_SCRIPT")
  printf '%s\t%s\t%s\t%s\n' "$LAST_JOB" "$experiment_id" "$model_tag" "$data_file"
}

submit_heldout_core() {
  local model="$1"
  local tag="$2"
  submit PAIR-CTRL "$model" "${tag}_held19003" \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl \
    "logs/pair_ctrl_${tag}_held19003_priority.log"
  submit PAIR-CTRL "$model" "${tag}_breadth19003" \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003_breadth_extension.jsonl \
    "logs/pair_ctrl_${tag}_breadth19003_priority.log"
  submit PAIR-CTRL "$model" "${tag}_finalbreadth19003" \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003_final_breadth_extension.jsonl \
    "logs/pair_ctrl_${tag}_finalbreadth19003_priority.log"
}

submit_surface() {
  local model="$1"
  local tag="$2"
  submit PAIR-CTRL "$model" "${tag}_surface19003" \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003_surface_robustness.jsonl \
    "logs/pair_ctrl_${tag}_surface19003_priority.log"
}

submit_seed_tail() {
  local model="$1"
  local tag="$2"
  local seed="$3"
  submit EXP-18 "$model" "${tag}_s${seed}" \
    "experiments/data/exp16_mechanism_repl_s${seed}.jsonl" \
    "logs/exp18_${tag}_s${seed}_priority.log"
  submit PAIR-CTRL "$model" "${tag}_ext${seed}" \
    "benchmarks/pair_ctrl/data/pair_ctrl_legacy_${seed}_extension.jsonl" \
    "logs/pair_ctrl_${tag}_ext${seed}_priority.log"
  submit PAIR-CTRL "$model" "${tag}_breadth${seed}" \
    "benchmarks/pair_ctrl/data/pair_ctrl_historical_${seed}_breadth_extension.jsonl" \
    "logs/pair_ctrl_${tag}_breadth${seed}_priority.log"
  submit PAIR-CTRL "$model" "${tag}_finalbreadth${seed}" \
    "benchmarks/pair_ctrl/data/pair_ctrl_historical_${seed}_final_breadth_extension.jsonl" \
    "logs/pair_ctrl_${tag}_finalbreadth${seed}_priority.log"
}

if [[ "$PROFILE" == "fa0618" ]]; then
  QWEN=Qwen/Qwen2.5-7B-Instruct
  MISTRAL=mistralai/Mistral-7B-Instruct-v0.3
  TULU_DPO=allenai/Llama-3.1-Tulu-3-8B-DPO

  # First secure a complete confirmatory 33-type split on both families.
  submit_heldout_core "$QWEN" qwen
  submit_heldout_core "$MISTRAL" mistral
  submit_surface "$QWEN" qwen
  submit_surface "$MISTRAL" mistral

  # Repeat the 384-token diagnostics with the valid 768-token budget, then
  # complete seed 16061.
  submit EXP-18 "$QWEN" qwen25_full_budget768 \
    experiments/data/exp16_self_doubt_focus_pilot.jsonl \
    logs/exp18_qwen25_full_budget768.log
  submit PAIR-CTRL "$QWEN" qwen_ext16061_budget768 \
    benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl \
    logs/pair_ctrl_qwen_ext16061_budget768.log
  submit PAIR-CTRL "$QWEN" qwen_breadth16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_historical_16061_breadth_extension.jsonl \
    logs/pair_ctrl_qwen_breadth16061_priority.log
  submit PAIR-CTRL "$QWEN" qwen_finalbreadth16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_historical_16061_final_breadth_extension.jsonl \
    logs/pair_ctrl_qwen_finalbreadth16061_priority.log
  submit EXP-18 "$MISTRAL" mistral7b_full_budget768 \
    experiments/data/exp16_self_doubt_focus_pilot.jsonl \
    logs/exp18_mistral7b_full_budget768.log
  submit PAIR-CTRL "$MISTRAL" mistral_ext16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl \
    logs/pair_ctrl_mistral_ext16061_priority.log
  submit PAIR-CTRL "$MISTRAL" mistral_breadth16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_historical_16061_breadth_extension.jsonl \
    logs/pair_ctrl_mistral_breadth16061_priority.log
  submit PAIR-CTRL "$MISTRAL" mistral_finalbreadth16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_historical_16061_final_breadth_extension.jsonl \
    logs/pair_ctrl_mistral_finalbreadth16061_priority.log

  # The Tulu checkpoint is a scoped within-Llama post-training case study.
  submit EXP-18 "$TULU_DPO" tulu3_dpo_full_budget768 \
    experiments/data/exp16_self_doubt_focus_pilot.jsonl \
    logs/exp18_tulu3_dpo_full_budget768.log
  submit PAIR-CTRL "$TULU_DPO" tuludpo_held19003 \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl \
    logs/pair_ctrl_tuludpo_held19003_priority.log
  submit PAIR-CTRL "$TULU_DPO" tuludpo_ext16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl \
    logs/pair_ctrl_tuludpo_ext16061_priority.log

  submit_seed_tail "$QWEN" qwen25 16101
  submit_seed_tail "$QWEN" qwen25 16102
  submit_seed_tail "$MISTRAL" mistral7b 16101
  submit_seed_tail "$MISTRAL" mistral7b 16102
  submit EXP-18 "$TULU_DPO" tulu3_dpo_s16101 \
    experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_tulu3_dpo_s16101_priority.log
  submit EXP-18 "$TULU_DPO" tulu3_dpo_s16102 \
    experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_tulu3_dpo_s16102_priority.log
else
  LLAMA=meta-llama/Llama-3.1-8B-Instruct
  PHI=microsoft/Phi-3.5-mini-instruct
  TULU_SFT=allenai/Llama-3.1-Tulu-3-8B-SFT

  submit_heldout_core "$LLAMA" llama
  submit_heldout_core "$PHI" phi35
  submit_surface "$LLAMA" llama
  submit_surface "$PHI" phi35

  submit EXP-18 "$LLAMA" llama31_full_budget768 \
    experiments/data/exp16_self_doubt_focus_pilot.jsonl \
    logs/exp18_llama31_full_budget768.log
  submit PAIR-CTRL "$LLAMA" llama_ext16061_budget768 \
    benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl \
    logs/pair_ctrl_llama_ext16061_budget768.log
  submit PAIR-CTRL "$LLAMA" llama_breadth16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_historical_16061_breadth_extension.jsonl \
    logs/pair_ctrl_llama_breadth16061_priority.log
  submit PAIR-CTRL "$LLAMA" llama_finalbreadth16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_historical_16061_final_breadth_extension.jsonl \
    logs/pair_ctrl_llama_finalbreadth16061_priority.log
  submit EXP-18 "$PHI" phi35_full_gpu \
    experiments/data/exp16_self_doubt_focus_pilot.jsonl logs/exp18_phi35_full_priority.log
  submit PAIR-CTRL "$PHI" phi35_ext16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl \
    logs/pair_ctrl_phi35_ext16061_priority.log
  submit PAIR-CTRL "$PHI" phi35_breadth16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_historical_16061_breadth_extension.jsonl \
    logs/pair_ctrl_phi35_breadth16061_priority.log
  submit PAIR-CTRL "$PHI" phi35_finalbreadth16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_historical_16061_final_breadth_extension.jsonl \
    logs/pair_ctrl_phi35_finalbreadth16061_priority.log

  submit EXP-18 "$TULU_SFT" tulu3_sft_full_budget768 \
    experiments/data/exp16_self_doubt_focus_pilot.jsonl \
    logs/exp18_tulu3_sft_full_budget768.log
  submit PAIR-CTRL "$TULU_SFT" tulusft_held19003 \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl \
    logs/pair_ctrl_tulusft_held19003_priority.log
  submit PAIR-CTRL "$TULU_SFT" tulusft_ext16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl \
    logs/pair_ctrl_tulusft_ext16061_priority.log

  submit_seed_tail "$LLAMA" llama31 16101
  submit_seed_tail "$LLAMA" llama31 16102
  submit_seed_tail "$PHI" phi35 16101
  submit_seed_tail "$PHI" phi35 16102
  submit EXP-18 "$TULU_SFT" tulu3_sft_s16101 \
    experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_tulu3_sft_s16101_priority.log
  submit EXP-18 "$TULU_SFT" tulu3_sft_s16102 \
    experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_tulu3_sft_s16102_priority.log
fi

echo "LAST_JOB=$LAST_JOB"
