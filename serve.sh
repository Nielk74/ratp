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

WORKER_SCALE=""
declare -a EXTRA_ARGS=()

while (($#)); do
  case "$1" in
    --workers)
      WORKER_SCALE="${2:-}"
      shift 2 || true
      ;;
    --workers=*)
      WORKER_SCALE="${1#*=}"
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

while (($#)); do
  EXTRA_ARGS+=("$1")
  shift
done

case "$ACTION" in
  up)
    echo "[serve] starting orchestrator stack (backend, frontend, kafka, workers)"
    compose_args=("-f" "${COMPOSE_FILE}" "up" "-d" "--build")
    if [[ -n "$WORKER_SCALE" ]]; then
      compose_args+=("--scale" "worker=${WORKER_SCALE}")
    fi
    compose_args+=("${EXTRA_ARGS[@]}")
    "$COMPOSE_BIN" "${compose_args[@]}"
    echo "[serve] stack is starting. Useful URLs:"
    echo "  - Frontend:            http://localhost:3000"
    echo "  - Orchestrator admin:  http://localhost:3000/admin/orchestrator"
    echo "  - Backend API docs:    http://localhost:8000/docs"
    echo "[serve] follow logs with './serve.sh logs'"
    ;;
  down)
    echo "[serve] stopping orchestrator stack"
    "$COMPOSE_BIN" -f "${COMPOSE_FILE}" down "${EXTRA_ARGS[@]}"
    ;;
  logs)
    echo "[serve] tailing container logs (Ctrl+C to exit)"
    "$COMPOSE_BIN" -f "${COMPOSE_FILE}" logs -f "${EXTRA_ARGS[@]}"
    ;;
  restart)
    "$COMPOSE_BIN" -f "${COMPOSE_FILE}" down
    compose_args=("-f" "${COMPOSE_FILE}" "up" "-d")
    if [[ -n "$WORKER_SCALE" ]]; then
      compose_args+=("--scale" "worker=${WORKER_SCALE}")
    fi
    compose_args+=("${EXTRA_ARGS[@]}")
    "$COMPOSE_BIN" "${compose_args[@]}"
    ;;
  *)
    cat <<EOF
Usage: ./serve.sh [command] [docker-compose args]

Commands:
  up [services...]       Start the full stack in detached mode (default).
  down                   Stop and remove containers.
  restart [services...]  Restart the stack.
  logs [services...]     Tail container logs.

Options:
  --workers N            Scale the worker service to N instances (default 1).

Examples:
  ./serve.sh             # start everything in background
  ./serve.sh logs backend
  ./serve.sh down
EOF
    ;;
esac
