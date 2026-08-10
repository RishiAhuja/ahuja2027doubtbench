#!/usr/bin/env bash
# Submit only the surviving-evidence gaps for the PAIR-CTRL factorial on FA0571.

set -euo pipefail

INITIAL_DEPENDENCY="${1:-none}"
ROOT="$(pwd)"
PBS_SCRIPT="$ROOT/scripts/pbs_exp18_factorial.pbs"
PYTHON=/Data3/it_FA0571/.conda/envs/cultural_env/bin/python
HF_HOME=/Data3/it_FA0571/hf_cache
MIG_UUID=MIG-5eef67d0-7e58-5016-8973-1bf2618f6d54
LAST_JOB="$INITIAL_DEPENDENCY"

QWEN=Qwen/Qwen2.5-7B-Instruct
MISTRAL=mistralai/Mistral-7B-Instruct-v0.3
LLAMA=meta-llama/Llama-3.1-8B-Instruct
PHI=microsoft/Phi-3.5-mini-instruct
TULU_SFT=allenai/Llama-3.1-Tulu-3-8B-SFT
TULU_DPO=allenai/Llama-3.1-Tulu-3-8B-DPO

mkdir -p logs

submit() {
  local model="$1"
  local model_tag="$2"
  local job_name="$3"
  local data_file="$4"
  local expected_tasks="$5"
  local output_log="logs/pair_ctrl_remaining_${model_tag}.log"
  local dependency=()
  if [[ "$LAST_JOB" != "none" ]]; then
    dependency=(-W "depend=afterany:$LAST_JOB")
  fi

  local actual_tasks
  actual_tasks=$(wc -l < "$data_file")
  if [[ "$actual_tasks" -ne "$expected_tasks" ]]; then
    echo "ERROR: $data_file has $actual_tasks tasks; expected $expected_tasks" >&2
    exit 2
  fi

  LAST_JOB=$(qsub "${dependency[@]}" \
    -N "$job_name" \
    -v "PYTHON=$PYTHON,HF_HOME=$HF_HOME,MIG_UUID=$MIG_UUID,EXPERIMENT_ID=PAIR-CTRL,MODEL=$model,MODEL_TAG=$model_tag,DATA_FILE=$data_file,MAX_NEW_TOKENS=768,BATCH_SIZE=8,THINKING_MODE=auto" \
    -o "$output_log" \
    "$PBS_SCRIPT")
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$LAST_JOB" "$model_tag" "$model" "$expected_tasks" "$data_file"
}

BATCH=benchmarks/pair_ctrl/eval_batches
SURFACE=benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003_surface_robustness.jsonl

echo -e "job_id\tmodel_tag\tmodel\ttasks\tdata_file"

# Wave 1: secure one complete 1,600-task held-out split on four independent
# foundation families. Phi is already complete, so only these gaps remain.
submit "$QWEN" qwen_rem_held19003 pc_qwen_h19003 \
  "$BATCH/heldout_19003_full.jsonl" 1600
submit "$MISTRAL" mistral_rem_held19003 pc_mis_h19003 \
  "$BATCH/heldout_19003_full.jsonl" 1600
submit "$TULU_SFT" tulusft_rem_held19003_tail pc_tsft_h19003 \
  "$BATCH/heldout_19003_tail.jsonl" 800

# Wave 2: complete Qwen, Mistral, and Tulu-SFT historical/replication seeds.
submit "$QWEN" qwen_rem_16061_tail pc_qwen_16061 \
  "$BATCH/seed16061_tail2.jsonl" 800
submit "$QWEN" qwen_rem_16101_full pc_qwen_16101 \
  "$BATCH/seed16101_full.jsonl" 1600
submit "$QWEN" qwen_rem_16102_full pc_qwen_16102 \
  "$BATCH/seed16102_full.jsonl" 1600

submit "$MISTRAL" mistral_rem_16061_full pc_mis_16061 \
  "$BATCH/seed16061_full.jsonl" 1600
submit "$MISTRAL" mistral_rem_16101_full pc_mis_16101 \
  "$BATCH/seed16101_full.jsonl" 1600
submit "$MISTRAL" mistral_rem_16102_full pc_mis_16102 \
  "$BATCH/seed16102_full.jsonl" 1600

submit "$TULU_SFT" tulusft_rem_16061_tail pc_tsft_16061 \
  "$BATCH/seed16061_tail2.jsonl" 800
submit "$TULU_SFT" tulusft_rem_16101_tail pc_tsft_16101 \
  "$BATCH/seed16101_tail3.jsonl" 1200
submit "$TULU_SFT" tulusft_rem_16102_tail pc_tsft_16102 \
  "$BATCH/seed16102_tail3.jsonl" 1200

# Wave 3: complete the missing Llama components. These are new consolidated
# batches; the incomplete 384-token seed-16061 diagnostic is not mixed in.
submit "$LLAMA" llama_rem_16061_tail pc_lla_16061 \
  "$BATCH/seed16061_tail3.jsonl" 1200
submit "$LLAMA" llama_rem_16101_final pc_lla_16101 \
  "$BATCH/seed16101_final.jsonl" 400
submit "$LLAMA" llama_rem_16102_tail pc_lla_16102 \
  "$BATCH/seed16102_tail3.jsonl" 1200

# Wave 4: add the optional related Tulu-DPO checkpoint on all four splits.
submit "$TULU_DPO" tuludpo_rem_16061_full pc_tdpo_16061 \
  "$BATCH/seed16061_full.jsonl" 1600
submit "$TULU_DPO" tuludpo_rem_16101_full pc_tdpo_16101 \
  "$BATCH/seed16101_full.jsonl" 1600
submit "$TULU_DPO" tuludpo_rem_16102_full pc_tdpo_16102 \
  "$BATCH/seed16102_full.jsonl" 1600
submit "$TULU_DPO" tuludpo_rem_held19003 pc_tdpo_h19003 \
  "$BATCH/heldout_19003_full.jsonl" 1600

# Wave 5: complete surface variants after every canonical core run.
submit "$QWEN" qwen_rem_surface19003 pc_qwen_surface "$SURFACE" 660
submit "$MISTRAL" mistral_rem_surface19003 pc_mis_surface "$SURFACE" 660
submit "$TULU_SFT" tulusft_rem_surface19003 pc_tsft_surface "$SURFACE" 660
submit "$TULU_DPO" tuludpo_rem_surface19003 pc_tdpo_surface "$SURFACE" 660

echo "LAST_JOB=$LAST_JOB"
