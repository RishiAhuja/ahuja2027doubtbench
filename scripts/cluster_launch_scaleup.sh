#!/usr/bin/env bash
# Run on HPC login node: pull code, cache benchmarks, submit P0 scale-up, start email watcher.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
cd "$ROOT"
export PATH="/opt/pbs/bin:${PATH:-}"

GIT_SSH="${GIT_SSH_COMMAND:-ssh -i $HOME/.ssh/caisc_github_ed25519 -o IdentitiesOnly=yes}"
BRANCH="${BRANCH:-cursor/exp02-benchmark-scaleup}"
COUNT_PROFILE="${COUNT_PROFILE:-configs/counts_p0.json}"
WALLTIME="${WALLTIME:-24:00:00}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-384}"
EMAIL_INTERVAL="${EMAIL_INTERVAL:-30}"
PYTHON="${PYTHON:-/Data3/it_FA0571/.conda/envs/cultural_env/bin/python}"

echo "===== 1/5 Git pull ($BRANCH) ====="
GIT_SSH_COMMAND="$GIT_SSH" git fetch origin
GIT_SSH_COMMAND="$GIT_SSH" git checkout "$BRANCH" 2>/dev/null || GIT_SSH_COMMAND="$GIT_SSH" git checkout -b "$BRANCH" "origin/$BRANCH"
GIT_SSH_COMMAND="$GIT_SSH" git pull --ff-only origin "$BRANCH"

echo "===== 2/5 Benchmark caches ====="
"$PYTHON" scripts/download_benchmark_data.py 200 200 200
"$PYTHON" -m experiments.exp02.verify_benchmarks --counts-file "$COUNT_PROFILE"

echo "===== 3/5 MIG UUID ====="
MIG_UUID="${MIG_UUID:-}"
if [[ -z "$MIG_UUID" ]]; then
  MIG_UUID="$(nvidia-smi -L 2>/dev/null | grep -oE 'MIG-[0-9a-f-]+' | head -1 || true)"
fi
if [[ -z "$MIG_UUID" ]]; then
  echo "ERROR: set MIG_UUID from: nvidia-smi -L" >&2
  exit 1
fi
echo "Using MIG_UUID=$MIG_UUID"

echo "===== 4/5 Submit EXP-02 P0 scale-up (chained 7B models) ====="
export MIG_UUID COUNT_PROFILE WALLTIME MAX_NEW_TOKENS
bash scripts/submit_exp02_scaleup.sh

echo "===== 5/5 Progress email every ${EMAIL_INTERVAL}m ====="
RESEND_ENV="${HOME}/.config/caisc/resend.env"
if [[ ! -f "$RESEND_ENV" ]]; then
  echo "WARN: missing $RESEND_ENV — skip email watcher (see docs/RESEND_PROGRESS_EMAIL.md)"
else
  mkdir -p "$ROOT/logs/progress_email"
  if [[ -f "$ROOT/logs/progress_email/watch.pid" ]]; then
    old_pid="$(cat "$ROOT/logs/progress_email/watch.pid")"
    kill "$old_pid" 2>/dev/null || true
  fi
  nohup bash scripts/watch_progress_email.sh "$EMAIL_INTERVAL" \
    >>"$ROOT/logs/progress_email/watch.log" 2>&1 &
  echo $! >"$ROOT/logs/progress_email/watch.pid"
  echo "Email watcher pid=$(cat "$ROOT/logs/progress_email/watch.pid")"
fi

echo
scripts/progress.sh 2>/dev/null || "$PYTHON" scripts/progress_status.py
