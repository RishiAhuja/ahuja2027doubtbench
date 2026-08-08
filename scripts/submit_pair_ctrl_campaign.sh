#!/usr/bin/env bash
# Submit the PAIR-CTRL campaign serially on one assigned MIG slice.

set -euo pipefail

PROFILE="${1:?usage: $0 fa0618|fa0571}"
ROOT="$(pwd)"
PBS_SCRIPT="$ROOT/scripts/pbs_exp18_factorial.pbs"
LAST_JOB=""

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
  if [[ -n "$LAST_JOB" ]]; then
    dependency=(-W "depend=afterany:$LAST_JOB")
  fi
  LAST_JOB=$(qsub "${dependency[@]}" \
    -v "PYTHON=$PYTHON,HF_HOME=$HF_HOME,MIG_UUID=$MIG_UUID,EXPERIMENT_ID=$experiment_id,MODEL=$model,MODEL_TAG=$model_tag,DATA_FILE=$data_file,MAX_NEW_TOKENS=384,BATCH_SIZE=8,THINKING_MODE=auto" \
    -o "$output_log" \
    "$PBS_SCRIPT")
  printf '%s\t%s\t%s\t%s\n' "$LAST_JOB" "$experiment_id" "$model_tag" "$data_file"
}

if [[ "$PROFILE" == "fa0618" ]]; then
  submit PAIR-CTRL Qwen/Qwen2.5-7B-Instruct qwen_ext16061 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl logs/pair_ctrl_qwen_ext16061_gpu.log
  submit PAIR-CTRL Qwen/Qwen2.5-7B-Instruct qwen_ext16101 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16101_extension.jsonl logs/pair_ctrl_qwen_ext16101_gpu.log
  submit PAIR-CTRL Qwen/Qwen2.5-7B-Instruct qwen_ext16102 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16102_extension.jsonl logs/pair_ctrl_qwen_ext16102_gpu.log
  submit PAIR-CTRL Qwen/Qwen2.5-7B-Instruct qwen_held19003 benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl logs/pair_ctrl_qwen_held19003_gpu.log

  submit PAIR-CTRL mistralai/Mistral-7B-Instruct-v0.3 mistral_ext16061 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl logs/pair_ctrl_mistral_ext16061_gpu.log
  submit PAIR-CTRL mistralai/Mistral-7B-Instruct-v0.3 mistral_ext16101 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16101_extension.jsonl logs/pair_ctrl_mistral_ext16101_gpu.log
  submit PAIR-CTRL mistralai/Mistral-7B-Instruct-v0.3 mistral_ext16102 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16102_extension.jsonl logs/pair_ctrl_mistral_ext16102_gpu.log
  submit PAIR-CTRL mistralai/Mistral-7B-Instruct-v0.3 mistral_held19003 benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl logs/pair_ctrl_mistral_held19003_gpu.log

  submit PAIR-CTRL allenai/Llama-3.1-Tulu-3-8B-DPO tuludpo_ext16061 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl logs/pair_ctrl_tuludpo_ext16061_gpu.log
  submit PAIR-CTRL allenai/Llama-3.1-Tulu-3-8B-DPO tuludpo_held19003 benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl logs/pair_ctrl_tuludpo_held19003_gpu.log

  submit EXP-18 Qwen/Qwen2.5-7B-Instruct qwen25_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_qwen25_s16101_gpu.log
  submit EXP-18 Qwen/Qwen2.5-7B-Instruct qwen25_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_qwen25_s16102_gpu.log
  submit EXP-18 mistralai/Mistral-7B-Instruct-v0.3 mistral7b_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_mistral7b_s16101_gpu.log
  submit EXP-18 mistralai/Mistral-7B-Instruct-v0.3 mistral7b_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_mistral7b_s16102_gpu.log
  submit EXP-18 allenai/Llama-3.1-Tulu-3-8B-DPO tulu3_dpo_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_tulu3_dpo_s16101_gpu.log
  submit EXP-18 allenai/Llama-3.1-Tulu-3-8B-DPO tulu3_dpo_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_tulu3_dpo_s16102_gpu.log
else
  submit EXP-18 microsoft/Phi-3.5-mini-instruct phi35_smoke_gpu experiments/data/exp16_self_doubt_focus_smoke.jsonl logs/exp18_phi35_smoke_gpu.log

  submit PAIR-CTRL meta-llama/Llama-3.1-8B-Instruct llama_ext16061 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl logs/pair_ctrl_llama_ext16061_gpu.log
  submit PAIR-CTRL meta-llama/Llama-3.1-8B-Instruct llama_ext16101 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16101_extension.jsonl logs/pair_ctrl_llama_ext16101_gpu.log
  submit PAIR-CTRL meta-llama/Llama-3.1-8B-Instruct llama_ext16102 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16102_extension.jsonl logs/pair_ctrl_llama_ext16102_gpu.log
  submit PAIR-CTRL meta-llama/Llama-3.1-8B-Instruct llama_held19003 benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl logs/pair_ctrl_llama_held19003_gpu.log

  submit PAIR-CTRL microsoft/Phi-3.5-mini-instruct phi35_ext16061 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl logs/pair_ctrl_phi35_ext16061_gpu.log
  submit PAIR-CTRL microsoft/Phi-3.5-mini-instruct phi35_ext16101 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16101_extension.jsonl logs/pair_ctrl_phi35_ext16101_gpu.log
  submit PAIR-CTRL microsoft/Phi-3.5-mini-instruct phi35_ext16102 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16102_extension.jsonl logs/pair_ctrl_phi35_ext16102_gpu.log
  submit PAIR-CTRL microsoft/Phi-3.5-mini-instruct phi35_held19003 benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl logs/pair_ctrl_phi35_held19003_gpu.log

  submit PAIR-CTRL allenai/Llama-3.1-Tulu-3-8B-SFT tulusft_ext16061 benchmarks/pair_ctrl/data/pair_ctrl_legacy_16061_extension.jsonl logs/pair_ctrl_tulusft_ext16061_gpu.log
  submit PAIR-CTRL allenai/Llama-3.1-Tulu-3-8B-SFT tulusft_held19003 benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003.jsonl logs/pair_ctrl_tulusft_held19003_gpu.log

  submit EXP-18 meta-llama/Llama-3.1-8B-Instruct llama31_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_llama31_s16101_gpu.log
  submit EXP-18 meta-llama/Llama-3.1-8B-Instruct llama31_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_llama31_s16102_gpu.log
  submit EXP-18 allenai/Llama-3.1-Tulu-3-8B-SFT tulu3_sft_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_tulu3_sft_s16101_gpu.log
  submit EXP-18 allenai/Llama-3.1-Tulu-3-8B-SFT tulu3_sft_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_tulu3_sft_s16102_gpu.log
  submit EXP-18 microsoft/Phi-3.5-mini-instruct phi35_full_gpu experiments/data/exp16_self_doubt_focus_pilot.jsonl logs/exp18_phi35_full_gpu.log
  submit EXP-18 microsoft/Phi-3.5-mini-instruct phi35_s16101 experiments/data/exp16_mechanism_repl_s16101.jsonl logs/exp18_phi35_s16101_gpu.log
  submit EXP-18 microsoft/Phi-3.5-mini-instruct phi35_s16102 experiments/data/exp16_mechanism_repl_s16102.jsonl logs/exp18_phi35_s16102_gpu.log
fi
