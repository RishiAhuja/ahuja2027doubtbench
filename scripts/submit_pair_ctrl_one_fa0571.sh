#!/usr/bin/env bash
# Submit exactly one validated PAIR-CTRL job on FA0571.

set -euo pipefail

if [[ $# -lt 5 || $# -gt 7 ]]; then
  echo "Usage: $0 MODEL MODEL_TAG PBS_NAME DATA_FILE EXPECTED_TASKS [DEPENDENCY_JOB_ID|none] [RESUME_RUN_DIR|none]" >&2
  exit 2
fi

MODEL="$1"
MODEL_TAG="$2"
PBS_NAME="$3"
DATA_FILE="$4"
EXPECTED_TASKS="$5"
DEPENDENCY="${6:-none}"
RESUME_RUN_DIR="${7:-none}"
BATCH_SIZE="${PAIR_CTRL_BATCH_SIZE:-8}"

ROOT=/Data3/it_FA0571/caisc
PBS_SCRIPT="$ROOT/scripts/pbs_exp18_factorial.pbs"
PYTHON=/Data3/it_FA0571/.conda/envs/cultural_env/bin/python
HF_HOME=/Data3/it_FA0571/hf_cache
MIG_UUID=MIG-5eef67d0-7e58-5016-8973-1bf2618f6d54

cd "$ROOT"

[[ "$EXPECTED_TASKS" =~ ^[0-9]+$ ]] || {
  echo "ERROR: EXPECTED_TASKS must be a positive integer" >&2
  exit 2
}
if [[ "$EXPECTED_TASKS" -le 0 ]]; then
  echo "ERROR: EXPECTED_TASKS must be a positive integer" >&2
  exit 2
fi
if [[ ! "$BATCH_SIZE" =~ ^[0-9]+$ ]] || [[ "$BATCH_SIZE" -lt 1 ]] || [[ "$BATCH_SIZE" -gt 8 ]]; then
  echo "ERROR: PAIR_CTRL_BATCH_SIZE must be an integer from 1 through 8" >&2
  exit 2
fi
if [[ ! "$PBS_NAME" =~ ^pc_[A-Za-z0-9_]+$ || ${#PBS_NAME} -gt 15 ]]; then
  echo "ERROR: invalid CAISC PBS name: $PBS_NAME" >&2
  exit 2
fi
[[ -f "$DATA_FILE" ]] || {
  echo "ERROR: missing data file: $DATA_FILE" >&2
  exit 2
}
[[ -x "$PYTHON" ]] || {
  echo "ERROR: missing Python environment: $PYTHON" >&2
  exit 2
}
[[ -f "$PBS_SCRIPT" ]] || {
  echo "ERROR: missing PBS script: $PBS_SCRIPT" >&2
  exit 2
}

actual_tasks=$(wc -l < "$DATA_FILE")
if [[ "$actual_tasks" -ne "$EXPECTED_TASKS" ]]; then
  echo "ERROR: $DATA_FILE has $actual_tasks tasks; expected $EXPECTED_TASKS" >&2
  exit 2
fi

cache_name="models--${MODEL//\//--}"
[[ -d "$HF_HOME/$cache_name" ]] || {
  echo "ERROR: model is not cached: $MODEL" >&2
  exit 2
}

dependency_args=()
if [[ "$DEPENDENCY" != "none" ]]; then
  [[ "$DEPENDENCY" =~ ^[0-9]+(\.master)?$ ]] || {
    echo "ERROR: invalid dependency job ID: $DEPENDENCY" >&2
    exit 2
  }
  dependency_args=(-W "depend=afterany:$DEPENDENCY")
fi

run_dir_env=()
if [[ "$RESUME_RUN_DIR" != "none" ]]; then
  case "$RESUME_RUN_DIR" in
    "$ROOT"/outputs/PAIR-CTRL/*) ;;
    *)
      echo "ERROR: resume directory must be an explicit PAIR-CTRL run under $ROOT/outputs/PAIR-CTRL" >&2
      exit 2
      ;;
  esac
  [[ -d "$RESUME_RUN_DIR" && -s "$RESUME_RUN_DIR/raw_outputs.jsonl" ]] || {
    echo "ERROR: resume directory has no nonempty raw_outputs.jsonl: $RESUME_RUN_DIR" >&2
    exit 2
  }
  run_dir_env=(",RUN_DIR=$RESUME_RUN_DIR")
fi

# Defense in depth: the recurring automation may never leave more than two
# PAIR-CTRL jobs live, and a second live job must be dependency-serialized.
live_caisc_jobs=$(qstat -u it_FA0571 | awk \
  'NR > 5 && $4 ~ /^pc_/ && $10 ~ /^[RQH]$/ {n++} END {print n + 0}')
if [[ "$live_caisc_jobs" -ge 2 ]]; then
  echo "ERROR: refusing submission: $live_caisc_jobs CAISC jobs are already live" >&2
  exit 2
fi
if [[ "$live_caisc_jobs" -eq 1 && "$DEPENDENCY" == "none" ]]; then
  echo "ERROR: a live CAISC job exists; the new job requires its dependency ID" >&2
  exit 2
fi

mkdir -p logs
job_id=$(qsub "${dependency_args[@]}" \
  -N "$PBS_NAME" \
  -v "PYTHON=$PYTHON,HF_HOME=$HF_HOME,MIG_UUID=$MIG_UUID,EXPERIMENT_ID=PAIR-CTRL,MODEL=$MODEL,MODEL_TAG=$MODEL_TAG,DATA_FILE=$DATA_FILE,MAX_NEW_TOKENS=768,BATCH_SIZE=$BATCH_SIZE,THINKING_MODE=auto${run_dir_env[*]}" \
  -o "logs/pair_ctrl_remaining_${MODEL_TAG}.log" \
  "$PBS_SCRIPT")

printf '%s\t%s\t%s\t%s\t%s\n' \
  "$job_id" "$MODEL_TAG" "$MODEL" "$EXPECTED_TASKS" "$DATA_FILE"
