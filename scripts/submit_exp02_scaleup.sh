#!/usr/bin/env bash
# Submit chained EXP-02 GPU jobs with a JSON count profile (P0 benchmarks).
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

COUNT_PROFILE="${COUNT_PROFILE:-configs/counts_p0.json}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-384}"
WALLTIME="${WALLTIME:-12:00:00}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,negative_capability}"
DEPEND_TYPE="${DEPEND_TYPE:-afterany}"
BATCH_PREFIX="${BATCH_PREFIX:-scaleup}"

PYTHON="${PYTHON:-/Data3/it_FA0571/.conda/envs/cultural_env/bin/python}"
EXPECTED_ROWS="$("$PYTHON" - <<PY
import json
from pathlib import Path
from core.sample_loading import expected_rows, load_counts_file
counts = load_counts_file(Path("$COUNT_PROFILE"))
conditions = [c for c in "$CONDITIONS".split(",") if c.strip()]
print(expected_rows(counts, len(conditions)))
PY
)"

MODELS=("$@")
if [[ "${#MODELS[@]}" -eq 0 ]]; then
  MODELS=(
    "Qwen/Qwen2.5-7B-Instruct"
    "meta-llama/Llama-3.1-8B-Instruct"
    "mistralai/Mistral-7B-Instruct-v0.3"
  )
fi

BATCH_ID="$(date +%Y%m%d_%H%M%S)"
BATCH_DIR="$ROOT/logs/${BATCH_PREFIX}/batch_${BATCH_ID}"
mkdir -p "$BATCH_DIR"
echo "$BATCH_DIR" > "$ROOT/logs/${BATCH_PREFIX}/latest_batch.txt"
echo "$BATCH_DIR" > "$ROOT/logs/overnight/latest_batch.txt"

echo "===== CAISc EXP-02 scale-up batch ====="
echo "Batch:        $BATCH_DIR"
echo "Profile:      $COUNT_PROFILE"
echo "MIG:          $MIG_UUID"
echo "Expected:     $EXPECTED_ROWS rows per model"
echo "Walltime:     $WALLTIME"
echo "Models:       ${MODELS[*]}"
echo

prev_job=""
: >"$BATCH_DIR/manifest.tsv"

for model in "${MODELS[@]}"; do
  slug="$(echo "$model" | tr '/:' '__')"
  run_dir="$ROOT/outputs/EXP-02/${BATCH_PREFIX}_${BATCH_ID}/${slug}"
  log_path="$BATCH_DIR/${slug}.pbs.log"
  mkdir -p "$(dirname "$run_dir")"

  vars="MIG_UUID=${MIG_UUID},MODEL=${model}"
  vars="${vars},COUNTS_FILE=${COUNT_PROFILE}"
  vars="${vars},MAX_NEW_TOKENS=${MAX_NEW_TOKENS}"
  vars="${vars},RUN_DIR=${run_dir}"

  job_name="caisc_${slug}"
  job_name="${job_name:0:15}"

  if [[ -n "$prev_job" ]]; then
    job_id="$(qsub -N "$job_name" -l "walltime=$WALLTIME" -v "$vars" -W "depend=${DEPEND_TYPE}:${prev_job}" -o "$log_path" scripts/pbs_exp02_gpu_smoke.pbs)"
  else
    job_id="$(qsub -N "$job_name" -l "walltime=$WALLTIME" -v "$vars" -o "$log_path" scripts/pbs_exp02_gpu_smoke.pbs)"
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$model" "$job_id" "$EXPECTED_ROWS" "$run_dir" "$log_path" "$COUNT_PROFILE" \
    >>"$BATCH_DIR/manifest.tsv"
  echo "Submitted $model -> $job_id"
  prev_job="$job_id"
done

echo "$prev_job" >"$BATCH_DIR/last_job.txt"
echo
echo "Monitor:  cd $ROOT && scripts/progress.sh"
echo "Email:    nohup bash scripts/watch_progress_email.sh 30 >> logs/progress_email/watch.log 2>&1 &"
echo
qstat -u "$USER" || true
