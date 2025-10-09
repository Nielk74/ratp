#!/usr/bin/env bash
set -euo pipefail

# Robust helper to spin up backend & frontend, run Playwright e2e tests, then tear everything down.

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-8001}
BACKEND_HOST=${BACKEND_HOST:-127.0.0.1}
FRONTEND_HOST=${FRONTEND_HOST:-127.0.0.1}
BACKEND_LOG="${ROOT_DIR}/backend/tmp/e2e-backend.log"
FRONTEND_LOG="${ROOT_DIR}/frontend/tmp/e2e-frontend.log"

mkdir -p "${ROOT_DIR}/backend/tmp" "${ROOT_DIR}/frontend/tmp"

BACKEND_PID=""
FRONTEND_PID=""

log() {
  echo "[run_e2e] $*"
}

cleanup_pid_file() {
  local pid_file="$1"
  [[ -f "${pid_file}" ]] && rm -f "${pid_file}"
}

kill_port() {
  local port="$1"
  if lsof -ti ":${port}" >/dev/null 2>&1; then
    log "Killing processes listening on port ${port}"
    lsof -ti ":${port}" | xargs -r kill -9
  fi
}

wait_for_http() {
  local url="$1"
  local timeout="${2:-60}"
  local interval="${3:-2}"
  local elapsed=0
  log "Waiting for ${url} (timeout=${timeout}s, interval=${interval}s)"
  while (( elapsed < timeout )); do
    if curl -sSf "${url}" >/dev/null 2>&1; then
      log "${url} ready after ${elapsed}s"
      return 0
    fi
    sleep "${interval}"
    elapsed=$(( elapsed + interval ))
    log "... still waiting for ${url} (${elapsed}s elapsed)"
  done
  log "${url} did not respond within ${timeout}s"
  return 1
}

ensure_env() {
  if [[ -f "${ROOT_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ROOT_DIR}/.env"
    set +a
    log "Loaded .env environment variables"
  fi
}

start_backend() {
  kill_port "${BACKEND_PORT}"
  log "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}"
  (
    cd "${ROOT_DIR}"
    log "uvicorn command: ${ROOT_DIR}/backend/.venv/bin/uvicorn backend.main:app --host ${BACKEND_HOST} --port ${BACKEND_PORT}"
    "${ROOT_DIR}/backend/.venv/bin/uvicorn" backend.main:app \
      --host "${BACKEND_HOST}" \
      --port "${BACKEND_PORT}" \
      > "${BACKEND_LOG}" 2>&1
  ) &
  BACKEND_PID=$!
  echo "${BACKEND_PID}" > "${ROOT_DIR}/backend/tmp/e2e-backend.pid"
}

start_frontend() {
  kill_port "${FRONTEND_PORT}"
  log "Starting frontend on ${FRONTEND_HOST}:${FRONTEND_PORT}"
  (
    cd "${ROOT_DIR}/frontend"
    NEXT_PUBLIC_BACKEND_PORT="${BACKEND_PORT}" npm run dev -- --hostname "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" \
      > "${FRONTEND_LOG}" 2>&1
  ) &
  FRONTEND_PID=$!
  echo "${FRONTEND_PID}" > "${ROOT_DIR}/frontend/tmp/e2e-frontend.pid"
}

stop_processes() {
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" >/dev/null 2>&1; then
    log "Stopping frontend (pid=${FRONTEND_PID})"
    kill "${FRONTEND_PID}" || true
    wait "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
    log "Stopping backend (pid=${BACKEND_PID})"
    kill "${BACKEND_PID}" || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
  cleanup_pid_file "${ROOT_DIR}/frontend/tmp/e2e-frontend.pid"
  cleanup_pid_file "${ROOT_DIR}/backend/tmp/e2e-backend.pid"
}

print_logs() {
  echo "----- backend log tail -----"
  tail -n 40 "${BACKEND_LOG}" || true
  echo "----- frontend log tail -----"
  tail -n 40 "${FRONTEND_LOG}" || true
  echo "----- end logs -----"
}

run_playwright() {
  log "Running Playwright tests"
  (
    cd "${ROOT_DIR}/frontend"
    PLAYWRIGHT_BASE_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}" \
    PLAYWRIGHT_SKIP_WEBSERVER=1 \
    npx playwright test
  )
}

ensure_env
trap 'status=$?; stop_processes; if [[ $status -ne 0 ]]; then print_logs; fi; exit $status' INT TERM EXIT

start_backend
wait_for_http "http://${BACKEND_HOST}:${BACKEND_PORT}/health" 90 3 || { log "Backend failed to start"; print_logs; exit 1; }

start_frontend
wait_for_http "http://${FRONTEND_HOST}:${FRONTEND_PORT}" 120 3 || { log "Frontend failed to start"; print_logs; exit 1; }

run_playwright

log "Suite completed successfully"
