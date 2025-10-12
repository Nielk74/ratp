#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
COMPOSE_FILE="${ROOT_DIR}/docker-compose.yml"
COMPOSE_BIN="${COMPOSE_BIN:-docker-compose}"

if ! command -v "$COMPOSE_BIN" >/dev/null 2>&1; then
  echo "[serve] error: ${COMPOSE_BIN} not found. Install Docker Compose or set COMPOSE_BIN."
  exit 1
fi

if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "[serve] error: docker-compose.yml not found at ${COMPOSE_FILE}"
  exit 1
fi

ACTION="${1:-up}"
shift || true

case "$ACTION" in
  up)
    echo "[serve] starting orchestrator stack (backend, frontend, kafka, workers)"
    "$COMPOSE_BIN" -f "${COMPOSE_FILE}" up -d "$@"
    echo "[serve] stack is starting. Useful URLs:"
    echo "  - Frontend:            http://localhost:3000"
    echo "  - Orchestrator admin:  http://localhost:3000/admin/orchestrator"
    echo "  - Backend API docs:    http://localhost:8000/docs"
    echo "[serve] follow logs with './serve.sh logs'"
    ;;
  down)
    echo "[serve] stopping orchestrator stack"
    "$COMPOSE_BIN" -f "${COMPOSE_FILE}" down "$@"
    ;;
  logs)
    echo "[serve] tailing container logs (Ctrl+C to exit)"
    "$COMPOSE_BIN" -f "${COMPOSE_FILE}" logs -f "$@"
    ;;
  restart)
    "$COMPOSE_BIN" -f "${COMPOSE_FILE}" down
    "$COMPOSE_BIN" -f "${COMPOSE_FILE}" up -d "$@"
    ;;
  *)
    cat <<EOF
Usage: ./serve.sh [command] [docker-compose args]

Commands:
  up [services...]       Start the full stack in detached mode (default).
  down                   Stop and remove containers.
  restart [services...]  Restart the stack.
  logs [services...]     Tail container logs.

Examples:
  ./serve.sh             # start everything in background
  ./serve.sh logs backend
  ./serve.sh down
EOF
    ;;
esac
