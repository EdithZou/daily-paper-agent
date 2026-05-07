#!/usr/bin/env bash
# Run the daily paper agent and append output to logs/daily.log.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load secrets from .env if it exists (never commit .env)
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi

cd "$PROJECT_DIR"

# Activate the virtual environment
source "$PROJECT_DIR/.venv/bin/activate"

mkdir -p "$PROJECT_DIR/logs"

LOG="$PROJECT_DIR/logs/daily.log"

echo "=== Run started at $(date) ===" | tee -a "$LOG"

python -m src.main --config config.yaml --date today 2>&1 | tee -a "$LOG"

echo "=== Run finished at $(date) ===" | tee -a "$LOG"
