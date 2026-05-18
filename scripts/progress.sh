#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Data3/it_FA0571/caisc}"
export PATH="/opt/pbs/bin:${PATH:-}"
cd "$ROOT"

PYTHON="${PYTHON:-/Data3/it_FA0571/.conda/envs/cultural_env/bin/python}"
exec "$PYTHON" scripts/progress_status.py
