#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if [ ! -x "${ROOT_DIR}/serve.sh" ]; then
  echo "[stop_services] error: serve.sh not found or not executable"
  exit 1
fi

echo "[stop_services] stopping orchestrator stack"
"${ROOT_DIR}/serve.sh" down "$@"
