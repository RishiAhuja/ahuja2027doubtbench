#!/usr/bin/env bash
# Post compact status periodically; no generated output content is transmitted.
set -euo pipefail

PACKAGE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INTERVAL_SECONDS=${1:-600}
MIN_INTERVAL_SECONDS=300
ENV_FILE=${PAIR_CTRL_PROGRESS_ENV:-$HOME/.config/pair-ctrl-external/progress.env}
PYTHON=${PAIR_CTRL_VENV_PYTHON:-$PACKAGE_ROOT/.venv/bin/python}
LOG_DIR=$PACKAGE_ROOT/logs/status
LOG_FILE=$LOG_DIR/watcher_$(date +%Y%m%d).log

if ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || (( INTERVAL_SECONDS < MIN_INTERVAL_SECONDS )); then
  echo "Interval must be an integer >= ${MIN_INTERVAL_SECONDS} seconds" >&2
  exit 2
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "Missing Python environment: $PYTHON" >&2
  exit 2
fi
mkdir -p "$LOG_DIR" "$PACKAGE_ROOT/state"
echo "[$(date -Is)] status watcher started interval=${INTERVAL_SECONDS}s" >>"$LOG_FILE"
while true; do
  if "$PYTHON" "$PACKAGE_ROOT/scripts/post_status.py" --env-file "$ENV_FILE" >>"$LOG_FILE" 2>&1; then
    echo "[$(date -Is)] status post accepted" >>"$LOG_FILE"
  else
    echo "[$(date -Is)] status post failed" >>"$LOG_FILE"
  fi
  sleep "$INTERVAL_SECONDS"
done
