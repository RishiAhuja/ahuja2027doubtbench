#!/usr/bin/env bash
# Post progress to the portfolio webhook every N seconds.
#
# This runs on the cluster login node, so keep the interval conservative. The
# watcher only reads progress and posts a compact payload, but frequent polling
# still spawns Python repeatedly and can trip login-node monitoring.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
INTERVAL_SECONDS="${1:-300}"
MIN_INTERVAL_SECONDS="${MIN_PROGRESS_WEBHOOK_INTERVAL_SECONDS:-300}"
ENV_FILE="${CAISC_PROGRESS_WEBHOOK_ENV:-$HOME/.config/caisc/progress_webhook.env}"
LOG_DIR="$ROOT/logs/progress_webhook"
LOG_FILE="$LOG_DIR/watch_$(date +%Y%m%d).log"

if ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "Interval must be a positive integer number of seconds." >&2
  exit 2
fi

if (( INTERVAL_SECONDS < MIN_INTERVAL_SECONDS )); then
  echo "Refusing ${INTERVAL_SECONDS}s progress polling on the cluster login node." >&2
  echo "Use >= ${MIN_INTERVAL_SECONDS}s or run scripts/progress.sh --once manually." >&2
  exit 2
fi

mkdir -p "$LOG_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  echo "Expected PORTFOLIO_PROGRESS_TOKEN and optional PORTFOLIO_PROGRESS_URL" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

cd "$ROOT"
export ROOT
export PATH="/opt/pbs/bin:${PATH:-}"

echo "[$(date -Is)] watch_progress_webhook started interval=${INTERVAL_SECONDS}s" | tee -a "$LOG_FILE"

while true; do
  echo "[$(date -Is)] posting progress webhook" | tee -a "$LOG_FILE"
  if scripts/post_progress_webhook.py >>"$LOG_FILE" 2>&1; then
    echo "[$(date -Is)] webhook ok" | tee -a "$LOG_FILE"
  else
    echo "[$(date -Is)] webhook failed (see log)" | tee -a "$LOG_FILE"
  fi
  sleep "$INTERVAL_SECONDS"
done
