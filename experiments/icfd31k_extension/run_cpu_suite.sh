#!/usr/bin/env bash
set -euo pipefail
: "${ICFD31K_DATA_ROOT:?Set ICFD31K_DATA_ROOT to final_upload_format}"
: "${ICFD31K_OUTPUT_ROOT:?Set ICFD31K_OUTPUT_ROOT}"
PYTHON_BIN="${ICFD31K_PYTHON:-python}"
"${PYTHON_BIN}" -m experiments.icfd31k_extension.preflight \
  --mode cpu --data-root "${ICFD31K_DATA_ROOT}"
exec "${PYTHON_BIN}" -m experiments.icfd31k_extension.classical \
  --data-root "${ICFD31K_DATA_ROOT}" \
  --output-root "${ICFD31K_OUTPUT_ROOT}" \
  --seed 42
