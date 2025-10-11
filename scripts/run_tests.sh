#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKEND_DIR="${ROOT_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/.venv"

log() {
  echo "[run_tests] $*"
}

ensure_venv() {
  if [[ ! -d "${VENV_DIR}" ]]; then
    log "Python virtualenv not found at ${VENV_DIR}; creating one"
    python3 -m venv "${VENV_DIR}"
  fi
  # shellcheck disable=SC1090
  source "${VENV_DIR}/bin/activate"
  if ! python -c "import pytest" >/dev/null 2>&1; then
    log "Installing pytest into virtualenv"
    python -m pip install --upgrade pip >/dev/null
    python -m pip install pytest >/dev/null
  fi
}

run_pytest() {
  cd "${ROOT_DIR}"
  log "Running pytest"
  python -m pytest backend/tests "$@"
}

ensure_venv
run_pytest "$@"
