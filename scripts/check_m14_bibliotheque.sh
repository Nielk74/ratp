#!/usr/bin/env bash
set -euo pipefail

HOST=${BACKEND_HOST:-127.0.0.1}
PORT=${BACKEND_PORT:-8000}
DIRECTION="B"
REFRESH=false
RAW_OUTPUT=false

usage() {
  cat <<'EOF'
Usage: ./scripts/check_m14_bibliotheque.sh [options]

Options:
  --host HOST         Backend host (default: 127.0.0.1 or $BACKEND_HOST)
  --port PORT         Backend port (default: 8000 or $BACKEND_PORT)
  --direction LETTER  Direction code for schedules endpoint (default: B)
  --refresh           Force snapshot refresh (add ?refresh=true)
  --raw               Print raw JSON payload
  -h, --help          Show this help message

Example:
  ./scripts/check_m14_bibliotheque.sh --direction B --refresh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --direction)
      DIRECTION="$2"
      shift 2
      ;;
    --refresh)
      REFRESH=true
      shift
      ;;
    --raw)
      RAW_OUTPUT=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

LINE="14"
NETWORK="metro"
QUERY_URL="http://${HOST}:${PORT}/api/snapshots/${NETWORK}/${LINE}"
if "${REFRESH}"; then
  QUERY_URL="${QUERY_URL}?refresh=true"
fi

echo "[check_m14] Querying ${QUERY_URL}"

response="$(curl -sS -w $'\n%{http_code}' "${QUERY_URL}")"
status="${response##*$'\n'}"
body="${response%$'\n'*}"

if [[ "${status}" != "200" ]]; then
  echo "[check_m14] Unexpected status ${status}"
  printf '%s\n' "${body}"
  exit 1
fi

if "${RAW_OUTPUT}"; then
  printf '%s\n' "${body}"
  exit 0
fi

printf '%s' "${body}" | python3 - "$DIRECTION" <<'PY'
import json
import sys

try:
    direction = sys.argv[1].strip().upper()
except IndexError:
    direction = "B"

payload = json.loads(sys.stdin.read() or "{}")
stations = payload.get("stations") or []
errors = payload.get("errors") or []

matching = [
    station for station in stations
    if station.get("direction", "").upper() == direction
    and station.get("slug", "").lower().startswith("bibliotheque-francois-mitterrand")
]
if not matching:
    print(f"[check_m14] Aucun point d'arrêt trouvé pour la direction {direction}.")
    if stations:
        print(f"[check_m14] Directions disponibles: {sorted({s.get('direction') for s in stations})}")
    if errors:
        print("[check_m14] Erreurs signalées:", "; ".join(errors))
    sys.exit(1)

station = matching[0]
departures = station.get("departures") or []
metadata = station.get("metadata") or {}
source = (
    metadata.get("navitia_source") and "navitia"
    or metadata.get("http_source") and "ratp_http"
    or metadata.get("http_error") and "http_error"
    or metadata.get("navitia_error") and "navitia_error"
    or "vmtr"
)

if not departures:
    print(f"[check_m14] Aucun horaire affiché pour {station.get('name')} (direction {direction}).")
    if errors:
        print("[check_m14] Erreurs globales:", "; ".join(errors))
    print(f"[check_m14] Source: {source}")
    sys.exit(1)

print(f"[check_m14] Station {station.get('name')} (dir {direction}) – Source: {source}")
for idx, entry in enumerate(departures[:3], start=1):
    destination = entry.get("destination") or "Destination inconnue"
    waiting = entry.get("waiting_time") or entry.get("status") or entry.get("raw_text") or "Indispo"
    print(f"  #{idx}: {destination} – {waiting}")

if errors:
    print("[check_m14] Erreurs globales:", "; ".join(errors))
PY
