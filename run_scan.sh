#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "[ERROR] Missing .env file. Copy .env.example to .env and edit it first."
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null
export PYTHONPATH="$ROOT_DIR/src:${PYTHONPATH:-}"
python3 main.py scan "$@"
