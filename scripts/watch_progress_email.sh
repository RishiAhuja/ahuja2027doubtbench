#!/usr/bin/env bash
# Send Resend progress email every N minutes (default 30). Safe on login node.
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
INTERVAL_MIN="${1:-30}"
LOG_DIR="$ROOT/logs/progress_email"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/watch_$(date +%Y%m%d).log"

cd "$ROOT"
echo "[$(date -Is)] watch_progress_email started interval=${INTERVAL_MIN}m" | tee -a "$LOG_FILE"

while true; do
  echo "[$(date -Is)] sending progress email" | tee -a "$LOG_FILE"
  if scripts/email_progress.sh --subject-prefix "CAISc EXP-02 progress" >>"$LOG_FILE" 2>&1; then
    echo "[$(date -Is)] email ok" | tee -a "$LOG_FILE"
  else
    echo "[$(date -Is)] email failed (see log)" | tee -a "$LOG_FILE"
  fi
  sleep "$((INTERVAL_MIN * 60))"
done
