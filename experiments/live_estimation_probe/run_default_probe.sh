#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${SCRIPT_DIR}/.venv"
PYTHON_BIN="${VENV_PATH}/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Virtualenv python not found at ${PYTHON_BIN}. Create the venv before running this script." >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  set -- --network metro --line 1 --station Bastille --direction A --with-vmtr --json
fi

exec "${PYTHON_BIN}" -m experiments.live_estimation_probe.fetch_departures "$@"
