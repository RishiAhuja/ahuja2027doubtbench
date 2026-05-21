#!/usr/bin/env bash
# Submit chained EXP-02 GPU jobs (one model at a time; cluster allows one GPU/MIG).
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

COUNT_GSM8K="${COUNT_GSM8K:-100}"
COUNT_MMLU="${COUNT_MMLU:-100}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-256}"
BATCH_SIZE="${BATCH_SIZE:-1}"
WALLTIME="${WALLTIME:-06:00:00}"
CONDITIONS="${CONDITIONS:-baseline,melancholic,negative_capability}"
DEPEND_TYPE="${DEPEND_TYPE:-afterany}"

MODELS=("$@")
if [[ "${#MODELS[@]}" -eq 0 ]]; then
  MODELS=(
    "Qwen/Qwen2.5-7B-Instruct"
    "meta-llama/Llama-3.1-8B-Instruct"
    "mistralai/Mistral-7B-Instruct-v0.3"
  )
fi

N_SAMPLES=$((COUNT_GSM8K + COUNT_MMLU))
N_CONDITIONS="$(echo "$CONDITIONS" | tr ',' '\n' | grep -c . || true)"
EXPECTED_ROWS=$((N_SAMPLES * N_CONDITIONS))

BATCH_ID="$(date +%Y%m%d_%H%M%S)"
BATCH_DIR="$ROOT/logs/overnight/batch_${BATCH_ID}"
mkdir -p "$BATCH_DIR"
echo "$BATCH_DIR" > "$ROOT/logs/overnight/latest_batch.txt"

echo "===== CAISc EXP-02 overnight batch ====="
echo "Batch:     $BATCH_DIR"
echo "MIG:       $MIG_UUID"
echo "Counts:    gsm8k=$COUNT_GSM8K mmlu=$COUNT_MMLU"
echo "Expected:  $EXPECTED_ROWS rows per model ($N_SAMPLES samples x $N_CONDITIONS conditions)"
echo "Walltime:  $WALLTIME per job"
echo "Models:    ${MODELS[*]}"
echo

prev_job=""
: >"$BATCH_DIR/manifest.tsv"

for model in "${MODELS[@]}"; do
  slug="$(echo "$model" | tr '/:' '__')"
  run_dir="$ROOT/outputs/EXP-02/overnight_${BATCH_ID}/${slug}"
  log_path="$BATCH_DIR/${slug}.pbs.log"
  mkdir -p "$(dirname "$run_dir")"

  # PBS -v uses commas as delimiters; never pass comma-containing values (e.g. CONDITIONS).
  vars="MIG_UUID=${MIG_UUID},MODEL=${model}"
  vars="${vars},COUNT_GSM8K=${COUNT_GSM8K}"
  vars="${vars},COUNT_MMLU=${COUNT_MMLU}"
  vars="${vars},MAX_NEW_TOKENS=${MAX_NEW_TOKENS}"
  vars="${vars},BATCH_SIZE=${BATCH_SIZE}"
  vars="${vars},RUN_DIR=${run_dir}"

  job_name="caisc_${slug}"
  job_name="${job_name:0:15}"

  if [[ -n "$prev_job" ]]; then
    job_id="$(qsub -N "$job_name" -l "walltime=$WALLTIME" -v "$vars" -W "depend=${DEPEND_TYPE}:${prev_job}" -o "$log_path" scripts/pbs_exp02_gpu_smoke.pbs)"
  else
    job_id="$(qsub -N "$job_name" -l "walltime=$WALLTIME" -v "$vars" -o "$log_path" scripts/pbs_exp02_gpu_smoke.pbs)"
  fi

  echo "$model" "$job_id" "$EXPECTED_ROWS" "$run_dir" "$log_path" | tr ' ' '\t' >>"$BATCH_DIR/manifest.tsv"
  echo "Submitted $model -> $job_id"
  prev_job="$job_id"
done

echo "$prev_job" >"$BATCH_DIR/last_job.txt"
echo
echo "Monitor:"
echo "  cd $ROOT && scripts/progress.sh"
echo "  cd $ROOT && scripts/email_progress.sh"
echo
echo "Email every 30 min (after configuring ~/.config/caisc/resend.env):"
echo "  nohup bash scripts/watch_progress_email.sh 30 >> logs/progress_email/watch.log 2>&1 &"
echo
qstat -u "$USER" || true
