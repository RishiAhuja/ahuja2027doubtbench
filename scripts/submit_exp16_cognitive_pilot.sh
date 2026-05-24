#!/usr/bin/env bash
# Submit chained EXP-16 cognitive battery jobs.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
cd "$ROOT"
export PATH="/opt/pbs/bin:${PATH:-}"

if ! command -v qsub >/dev/null 2>&1; then
  echo "ERROR: qsub not found. Run on the HPC login node." >&2
  exit 1
fi

MIG_UUID="${MIG_UUID:-}"
if [[ -z "$MIG_UUID" ]]; then
  echo "ERROR: set MIG_UUID from: nvidia-smi -L" >&2
  exit 1
fi

DATA_FILE="${DATA_FILE:-experiments/data/exp16_cognitive_pilot.jsonl}"
CONDITIONS="${CONDITIONS:-baseline,neutral_librarian,melancholic,anxious,self_doubt_only,capability_denial_only,explicit_sabotage}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-1024}"
BATCH_SIZE="${BATCH_SIZE:-2}"
WALLTIME="${WALLTIME:-24:00:00}"
DEPEND_TYPE="${DEPEND_TYPE:-afterany}"
INITIAL_DEPEND_JOB="${INITIAL_DEPEND_JOB:-}"
BATCH_PREFIX="${BATCH_PREFIX:-exp16_cognitive_pilot}"
PYTHON="${PYTHON:-/Data3/it_FA0571/.conda/envs/cultural_env/bin/python}"

EXPECTED_ROWS="$("$PYTHON" - <<PY
import json
from pathlib import Path

tasks = sum(1 for line in Path("$DATA_FILE").open(encoding="utf-8") if line.strip())
conditions = [item for item in "$CONDITIONS".split(",") if item.strip()]
print(tasks * len(conditions))
PY
)"

MODELS=("$@")
if [[ "${#MODELS[@]}" -eq 0 ]]; then
  MODELS=(
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
    "Qwen/Qwen3-14B"
    "Qwen/Qwen2.5-7B-Instruct"
  )
fi

thinking_mode_for_model() {
  case "$1" in
    Qwen/Qwen3-*) printf 'on\n' ;;
    *) printf 'auto\n' ;;
  esac
}

BATCH_ID="$(date +%Y%m%d_%H%M%S)"
BATCH_DIR="$ROOT/logs/${BATCH_PREFIX}/batch_${BATCH_ID}"
mkdir -p "$BATCH_DIR" "$ROOT/logs/${BATCH_PREFIX}"
echo "$BATCH_DIR" > "$ROOT/logs/${BATCH_PREFIX}/latest_batch.txt"

echo "===== CAISc EXP-16 cognitive battery ====="
echo "Batch:        $BATCH_DIR"
echo "Data file:    $DATA_FILE"
echo "MIG:          $MIG_UUID"
echo "Expected:     $EXPECTED_ROWS rows per model"
echo "Walltime:     $WALLTIME"
echo "Batch size:   $BATCH_SIZE"
echo "Max tokens:   $MAX_NEW_TOKENS"
echo "Conditions:   $CONDITIONS"
echo "Models:       ${MODELS[*]}"
echo

prev_job=""
: >"$BATCH_DIR/manifest.tsv"

for model in "${MODELS[@]}"; do
  slug="$(echo "$model" | tr '/:' '__')"
  thinking_mode="$(thinking_mode_for_model "$model")"
  run_dir="$ROOT/outputs/EXP-16/${BATCH_PREFIX}_${BATCH_ID}/${slug}"
  log_path="$BATCH_DIR/${slug}.pbs.log"
  env_path="$BATCH_DIR/${slug}.env"
  mkdir -p "$(dirname "$run_dir")"

  {
    printf 'CONDITIONS=%q\n' "$CONDITIONS"
    printf 'THINKING_MODE=%q\n' "$thinking_mode"
  } >"$env_path"

  vars="MIG_UUID=${MIG_UUID},MODEL=${model}"
  vars="${vars},DATA_FILE=${DATA_FILE}"
  vars="${vars},MAX_NEW_TOKENS=${MAX_NEW_TOKENS}"
  vars="${vars},BATCH_SIZE=${BATCH_SIZE}"
  vars="${vars},RUN_DIR=${run_dir}"
  vars="${vars},JOB_ENV_FILE=${env_path}"

  job_name="caisc16_${slug}"
  job_name="${job_name:0:15}"
  if [[ -n "$prev_job" ]]; then
    job_id="$(qsub -N "$job_name" -l "walltime=$WALLTIME" -v "$vars" -W "depend=${DEPEND_TYPE}:${prev_job}" -o "$log_path" scripts/pbs_exp16_cognitive.pbs)"
  elif [[ -n "$INITIAL_DEPEND_JOB" ]]; then
    job_id="$(qsub -N "$job_name" -l "walltime=$WALLTIME" -v "$vars" -W "depend=${DEPEND_TYPE}:${INITIAL_DEPEND_JOB}" -o "$log_path" scripts/pbs_exp16_cognitive.pbs)"
  else
    job_id="$(qsub -N "$job_name" -l "walltime=$WALLTIME" -v "$vars" -o "$log_path" scripts/pbs_exp16_cognitive.pbs)"
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$model" "$job_id" "$EXPECTED_ROWS" "$run_dir" "$log_path" "$DATA_FILE" \
    >>"$BATCH_DIR/manifest.tsv"
  echo "Submitted $model thinking=$thinking_mode -> $job_id"
  prev_job="$job_id"
done

echo "$prev_job" >"$BATCH_DIR/last_job.txt"
echo
echo "Monitor manually only: cd $ROOT && scripts/progress.sh --once"
echo
qstat -u "$USER" || true
