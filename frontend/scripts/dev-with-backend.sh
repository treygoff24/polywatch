#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REPO_ROOT=$(cd "$ROOT/.." && pwd)
export PYTHONPATH="$REPO_ROOT"
export POLYWATCH_BACKEND_URL=${POLYWATCH_BACKEND_URL:-http://127.0.0.1:8000}
export POLYWATCH_FRONTEND_HOST=${POLYWATCH_FRONTEND_HOST:-127.0.0.1}
export POLYWATCH_FRONTEND_PORT=${POLYWATCH_FRONTEND_PORT:-3000}

DEFAULT_REPORTS_SOURCE_ROOT="$REPO_ROOT/docs/reports"
REPORTS_SOURCE_ROOT=${POLYWATCH_REPORTS_SOURCE_ROOT:-$DEFAULT_REPORTS_SOURCE_ROOT}
if [[ "${POLYWATCH_USE_TEMP_REPORTS:-}" == "1" ]]; then
  TEMP_REPORTS_DIR=$(mktemp -d)
  export REPORTS_FILE_ROOT="$TEMP_REPORTS_DIR"
  if [[ -d "$REPORTS_SOURCE_ROOT" ]]; then
    cp -R "$REPORTS_SOURCE_ROOT/." "$REPORTS_FILE_ROOT/"
  fi
else
  export REPORTS_FILE_ROOT=${REPORTS_FILE_ROOT:-$DEFAULT_REPORTS_SOURCE_ROOT}
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${TEMP_REPORTS_DIR:-}" ]]; then
    rm -rf "$TEMP_REPORTS_DIR" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

PYTHON_BIN=${POLYWATCH_PYTHON_BIN:-}
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

"$PYTHON_BIN" -m uvicorn polywatch.service:app --port 8000 --host 127.0.0.1 --log-level warning &
BACKEND_PID=$!

cd "$ROOT"
npm run dev -- --hostname "$POLYWATCH_FRONTEND_HOST" --port "$POLYWATCH_FRONTEND_PORT"
