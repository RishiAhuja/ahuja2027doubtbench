#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
ENV_FILE="${CAISC_PROGRESS_EMAIL_ENV:-$HOME/.config/caisc/resend.env}"
LOG_DIR="$ROOT/logs/progress_email"
mkdir -p "$LOG_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  echo "Create it from docs/RESEND_PROGRESS_EMAIL.md" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

export ROOT
export PATH="/opt/pbs/bin:${PATH:-}"
cd "$ROOT"
PYTHON="${PYTHON:-/Data3/it_FA0571/.conda/envs/cultural_env/bin/python}"
exec "$PYTHON" scripts/email_progress.py "$@"
