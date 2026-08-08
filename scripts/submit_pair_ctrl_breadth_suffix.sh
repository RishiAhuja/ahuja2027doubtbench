#!/usr/bin/env bash
# Insert PAIR-CTRL breadth jobs after the retained primary-core queue prefix.

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

submit() {
  local experiment_id="$1"
  local model="$2"
  local model_tag="$3"
  local data_file="$4"
  local output_log="$5"
  LAST_JOB=$(qsub -W "depend=afterany:$LAST_JOB" \
    -v "PYTHON=$PYTHON,HF_HOME=$HF_HOME,MIG_UUID=$MIG_UUID,EXPERIMENT_ID=$experiment_id,MODEL=$model,MODEL_TAG=$model_tag,DATA_FILE=$data_file,MAX_NEW_TOKENS=384,BATCH_SIZE=8,THINKING_MODE=auto" \
    -o "$output_log" \
    "$PBS_SCRIPT")
  printf '%s\t%s\t%s\t%s\n' "$LAST_JOB" "$experiment_id" "$model_tag" "$data_file"
}

if [[ "$PROFILE" == "fa0618" ]]; then
  for seed in 16061 16101 16102; do
    submit PAIR-CTRL Qwen/Qwen2.5-7B-Instruct "qwen_breadth${seed}" \
      "benchmarks/pair_ctrl/data/pair_ctrl_historical_${seed}_breadth_extension.jsonl" \
      "logs/pair_ctrl_qwen_breadth${seed}.log"
  done
  submit PAIR-CTRL Qwen/Qwen2.5-7B-Instruct qwen_breadth19003 \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003_breadth_extension.jsonl \
    logs/pair_ctrl_qwen_breadth19003.log

  for seed in 16061 16101 16102; do
    submit PAIR-CTRL mistralai/Mistral-7B-Instruct-v0.3 "mistral_breadth${seed}" \
      "benchmarks/pair_ctrl/data/pair_ctrl_historical_${seed}_breadth_extension.jsonl" \
      "logs/pair_ctrl_mistral_breadth${seed}.log"
  done
  submit PAIR-CTRL mistralai/Mistral-7B-Instruct-v0.3 mistral_breadth19003 \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003_breadth_extension.jsonl \
    logs/pair_ctrl_mistral_breadth19003.log

  submit PAIR-CTRL allenai/Llama-3.1-Tulu-3-8B-DPO tuludpo_ext16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl logs/pair_ctrl_tuludpo_ext16061_gpu.log
  submit PAIR-CTRL allenai/Llama-3.1-Tulu-3-8B-DPO tuludpo_held19003 \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl logs/pair_ctrl_tuludpo_held19003_gpu.log
  submit EXP-18 Qwen/Qwen2.5-7B-Instruct qwen25_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_qwen25_s16101_gpu.log
  submit EXP-18 Qwen/Qwen2.5-7B-Instruct qwen25_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_qwen25_s16102_gpu.log
  submit EXP-18 mistralai/Mistral-7B-Instruct-v0.3 mistral7b_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_mistral7b_s16101_gpu.log
  submit EXP-18 mistralai/Mistral-7B-Instruct-v0.3 mistral7b_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_mistral7b_s16102_gpu.log
  submit EXP-18 allenai/Llama-3.1-Tulu-3-8B-DPO tulu3_dpo_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_tulu3_dpo_s16101_gpu.log
  submit EXP-18 allenai/Llama-3.1-Tulu-3-8B-DPO tulu3_dpo_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_tulu3_dpo_s16102_gpu.log
else
  for seed in 16061 16101 16102; do
    submit PAIR-CTRL meta-llama/Llama-3.1-8B-Instruct "llama_breadth${seed}" \
      "benchmarks/pair_ctrl/data/pair_ctrl_historical_${seed}_breadth_extension.jsonl" \
      "logs/pair_ctrl_llama_breadth${seed}.log"
  done
  submit PAIR-CTRL meta-llama/Llama-3.1-8B-Instruct llama_breadth19003 \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003_breadth_extension.jsonl \
    logs/pair_ctrl_llama_breadth19003.log

  for seed in 16061 16101 16102; do
    submit PAIR-CTRL microsoft/Phi-3.5-mini-instruct "phi35_ext${seed}" \
      "benchmarks/pair_ctrl/data/pair_ctrl_legacy_${seed}_extension.jsonl" \
      "logs/pair_ctrl_phi35_ext${seed}_gpu.log"
  done
  submit PAIR-CTRL microsoft/Phi-3.5-mini-instruct phi35_held19003 \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl logs/pair_ctrl_phi35_held19003_gpu.log

  for seed in 16061 16101 16102; do
    submit PAIR-CTRL microsoft/Phi-3.5-mini-instruct "phi35_breadth${seed}" \
      "benchmarks/pair_ctrl/data/pair_ctrl_historical_${seed}_breadth_extension.jsonl" \
      "logs/pair_ctrl_phi35_breadth${seed}.log"
  done
  submit PAIR-CTRL microsoft/Phi-3.5-mini-instruct phi35_breadth19003 \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003_breadth_extension.jsonl \
    logs/pair_ctrl_phi35_breadth19003.log

  submit PAIR-CTRL allenai/Llama-3.1-Tulu-3-8B-SFT tulusft_ext16061 \
    benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl logs/pair_ctrl_tulusft_ext16061_gpu.log
  submit PAIR-CTRL allenai/Llama-3.1-Tulu-3-8B-SFT tulusft_held19003 \
    benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl logs/pair_ctrl_tulusft_held19003_gpu.log
  submit EXP-18 meta-llama/Llama-3.1-8B-Instruct llama31_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_llama31_s16101_gpu.log
  submit EXP-18 meta-llama/Llama-3.1-8B-Instruct llama31_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_llama31_s16102_gpu.log
  submit EXP-18 allenai/Llama-3.1-Tulu-3-8B-SFT tulu3_sft_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_tulu3_sft_s16101_gpu.log
  submit EXP-18 allenai/Llama-3.1-Tulu-3-8B-SFT tulu3_sft_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_tulu3_sft_s16102_gpu.log
  submit EXP-18 microsoft/Phi-3.5-mini-instruct phi35_full_gpu experiments/data/exp16_self_doubt_focus_pilot.jsonl logs/exp18_phi35_full_gpu.log
  submit EXP-18 microsoft/Phi-3.5-mini-instruct phi35_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_phi35_s16101_gpu.log
  submit EXP-18 microsoft/Phi-3.5-mini-instruct phi35_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_phi35_s16102_gpu.log
fi
