#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REPO_ROOT=$(cd "$ROOT/.." && pwd)
export PYTHONPATH="$REPO_ROOT"
export REPORTS_FILE_ROOT="$REPO_ROOT/docs/reports"
export POLYWATCH_BACKEND_URL=${POLYWATCH_BACKEND_URL:-http://127.0.0.1:8000}

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

python3 -m uvicorn polywatch.service:app --port 8000 --host 127.0.0.1 --log-level warning &
BACKEND_PID=$!

cd "$ROOT"
npm run dev
