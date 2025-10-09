#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

cleanup() {
  trap - SIGINT SIGTERM EXIT
  kill -- -$$ >/dev/null 2>&1 || true
}

trap cleanup SIGINT SIGTERM EXIT

(
  cd "$ROOT_DIR/backend"
  echo "[serve] starting backend on 0.0.0.0:8000"
  "$ROOT_DIR/backend/.venv/bin/uvicorn" backend.main:app --host 0.0.0.0 --port 8000
) &

(
  cd "$ROOT_DIR/frontend"
  echo "[serve] starting frontend on http://0.0.0.0:8001"
  NEXT_PUBLIC_BACKEND_PORT=8000 npm run dev -- --hostname 0.0.0.0 --port 8001
) &

wait
