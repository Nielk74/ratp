#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

kill_port() {
  local port="$1"
  if fuser -s "${port}/tcp"; then
    echo "[serve] killing processes on port ${port}"
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
  fi
}

kill_processes_matching() {
  local pattern="$1"
  if pgrep -f "$pattern" >/dev/null 2>&1; then
    echo "[serve] killing processes matching "$pattern""
    pkill -9 -f "$pattern" || true
  fi
}

cleanup() {
  trap - SIGINT SIGTERM EXIT
  kill -- -$$ >/dev/null 2>&1 || true
}

trap cleanup SIGINT SIGTERM EXIT

kill_processes_matching "uvicorn backend.main:app"
kill_processes_matching "next dev -- --hostname 0.0.0.0 --port 8001"
kill_processes_matching "next dev .*--port 8001"
kill_processes_matching "node .*next-server"
kill_port 8000
kill_port 8001

(
  cd "$ROOT_DIR"
  echo "[serve] starting backend on 0.0.0.0:8000"
  PYTHONPATH="$ROOT_DIR" "$ROOT_DIR/backend/.venv/bin/uvicorn" backend.main:app --host 0.0.0.0 --port 8000
) &

BACKEND_PID=$!

# Wait briefly to ensure backend has time to bind before starting frontend
sleep 2

(
  cd "$ROOT_DIR/frontend"
  echo "[serve] starting frontend on http://0.0.0.0:8001"
  NEXT_PUBLIC_BACKEND_PORT=8000 npm run dev -- --hostname 0.0.0.0 --port 8001
) &

wait "$BACKEND_PID"
wait
