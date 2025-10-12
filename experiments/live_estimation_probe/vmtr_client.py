"""Minimal VMTR socket client for pulling live vehicle positions."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from urllib.parse import quote

try:
    import websocket  # type: ignore
except ImportError as exc:  # pragma: no cover - surfaced at runtime
    raise SystemExit(
        "Missing dependency 'websocket-client'. Install with `pip install websocket-client`."
    ) from exc


_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
)


@dataclass
class VmtrVehicle:
    """Subset of VMTR payload fields useful for quick probes."""

    vehicle_id: str
    direction: str
    previous_stop_ref: Optional[str]
    next_stop_ref: Optional[str]
    progress: Optional[float]
    status: Optional[str]
    recorded_at: Optional[str]

    def to_dict(self) -> Dict[str, Optional[str | float]]:
        return asdict(self)  # type: ignore[arg-type]


class VmtrClient:
    """Thin wrapper around the socket.io endpoint hosted at api.vmtr.ratp.fr."""

    def __init__(
        self,
        *,
        base_url: str = "wss://api.vmtr.ratp.fr/socket.io/",
        connect_timeout: float = 10.0,
        listen_timeout: float = 8.0,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._connect_timeout = connect_timeout
        self._listen_timeout = listen_timeout

    def fetch_direction(self, line_id: str, direction: str) -> List[VmtrVehicle]:
        """Return the most recent vehicle snapshot for the given direction."""

        if not line_id:
            return []

        normalized = self._normalize_line_id(line_id)
        vmtr_direction = "A" if direction.upper() == "A" else "R"
        room_name = f"LIG:{normalized}"
        direction_id = f"DIR:{normalized}:{vmtr_direction}"
        query = f"?roomName={quote(room_name)}&directionId={quote(direction_id)}&EIO=4&transport=websocket"
        url = f"{self._base_url}{query}"

        headers = [
            f"User-Agent: {_USER_AGENT}",
            "Origin: https://vmtr.ratp.fr",
            "Pragma: no-cache",
            "Cache-Control: no-cache",
        ]

        ws = websocket.create_connection(url, timeout=self._connect_timeout, header=headers)  # type: ignore[attr-defined]
        try:
            deadline = time.perf_counter() + self._listen_timeout
            vehicles: List[VmtrVehicle] = []
            while time.perf_counter() < deadline:
                try:
                    message = ws.recv()
                except websocket.WebSocketTimeoutException:  # type: ignore[attr-defined]
                    break

                if not isinstance(message, str):
                    continue

                if message == "2":  # ping
                    ws.send("3")
                    continue

                if message.startswith("0"):
                    ws.send("40")
                    continue

                if not message.startswith("42"):
                    continue

                payload = self._parse_socket_message(message)
                if not payload:
                    continue

                event_name, event_payload = payload
                vehicle_entries = event_payload.get("vehicles") or []
                parsed = [self._parse_vehicle(entry) for entry in vehicle_entries]
                vehicles = [vehicle for vehicle in parsed if vehicle is not None]
                if vehicles and event_name == "[POSV - INIT]":
                    break
            return vehicles
        finally:
            try:
                ws.close()
            except Exception:  # pylint: disable=broad-except
                pass

    @staticmethod
    def _parse_socket_message(message: str) -> Optional[tuple[str, Dict]]:
        try:
            data = json.loads(message[2:])
            if not isinstance(data, list) or len(data) < 2:
                return None
            event_name = data[0]
            raw_payload = data[1]
            if isinstance(raw_payload, str):
                raw_payload = json.loads(raw_payload)
            if not isinstance(raw_payload, dict):
                return None
            return event_name, raw_payload
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _parse_vehicle(entry: Dict) -> Optional[VmtrVehicle]:
        try:
            vehicle_id = entry.get("vehicleId")
            vehicle_activity = entry.get("vehicleActivity") or {}
            direction_ref = vehicle_activity.get("directionRef")
            position = entry.get("position") or {}

            if not vehicle_id or not direction_ref:
                return None

            direction = direction_ref.split(":")[-1]
            previous_stop = position.get("previousStopPlaceRef")
            next_stop = position.get("nextStopPlaceRef")

            progress_value = position.get("progressBetweenStopsPercentage")
            progress = None
            if isinstance(progress_value, (int, float)):
                progress = max(0.0, min(float(progress_value) / 100.0, 1.0))

            status = position.get("vehicleStopStatus")
            recorded_at = entry.get("recordedAtTime")

            return VmtrVehicle(
                vehicle_id=vehicle_id,
                direction=direction,
                previous_stop_ref=previous_stop,
                next_stop_ref=next_stop,
                progress=progress,
                status=status,
                recorded_at=recorded_at,
            )
        except Exception:  # pylint: disable=broad-except
            return None

    @staticmethod
    def _normalize_line_id(line_id: str) -> str:
        normalized = line_id
        if normalized.startswith("LIG:"):
            normalized = normalized[4:]
        if not normalized.startswith("IDFM:"):
            normalized = f"IDFM:{normalized}"
        return normalized


__all__ = ["VmtrClient", "VmtrVehicle"]
