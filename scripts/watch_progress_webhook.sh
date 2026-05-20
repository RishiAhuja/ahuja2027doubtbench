#!/usr/bin/env bash
# Post progress to the portfolio webhook every N minutes (default 3).
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
INTERVAL_MIN="${1:-3}"
ENV_FILE="${CAISC_PROGRESS_WEBHOOK_ENV:-$HOME/.config/caisc/progress_webhook.env}"
LOG_DIR="$ROOT/logs/progress_webhook"
LOG_FILE="$LOG_DIR/watch_$(date +%Y%m%d).log"

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

echo "[$(date -Is)] watch_progress_webhook started interval=${INTERVAL_MIN}m" | tee -a "$LOG_FILE"

while true; do
  echo "[$(date -Is)] posting progress webhook" | tee -a "$LOG_FILE"
  if scripts/post_progress_webhook.py >>"$LOG_FILE" 2>&1; then
    echo "[$(date -Is)] webhook ok" | tee -a "$LOG_FILE"
  else
    echo "[$(date -Is)] webhook failed (see log)" | tee -a "$LOG_FILE"
  fi
  sleep "$((INTERVAL_MIN * 60))"
done
