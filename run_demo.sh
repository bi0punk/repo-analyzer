#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 /ruta/al/repositorio"
  exit 1
fi

python3 analyze_repo.py "$1" \
  --output-dir ./output \
  --print-report \
  --llm-max-input-tokens 24000 \
  --important-file-budget-ratio 0.35 \
  --secondary-file-budget-ratio 0.10 \
  --max-secondary-files 2
