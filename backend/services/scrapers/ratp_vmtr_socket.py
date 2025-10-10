"""Realtime vehicle positions via the public vmtr socket.io endpoint."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from urllib.parse import quote

import websocket  # type: ignore

logger = logging.getLogger(__name__)


_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class VmtrVehicle:
    """Subset of the VMTR payload we care about."""

    vehicle_id: str
    direction: str
    previous_stop_ref: Optional[str]
    next_stop_ref: Optional[str]
    progress: Optional[float]
    status: Optional[str]
    recorded_at: Optional[str]


class RatpVmtrSocketClient:
    """Minimal socket.io client for https://api.vmtr.ratp.fr."""

    def __init__(
        self,
        *,
        base_url: str = "wss://api.vmtr.ratp.fr/socket.io/",
        enabled: bool = True,
        connect_timeout: float = 10.0,
        listen_timeout: float = 8.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._enabled = enabled
        self._connect_timeout = connect_timeout
        self._listen_timeout = listen_timeout

    @property
    def enabled(self) -> bool:
        return self._enabled

    def fetch_positions(self, line_id: str, directions: Iterable[str]) -> Dict[str, List[VmtrVehicle]]:
        """Fetch current vehicle positions for the requested directions.

        Parameters
        ----------
        line_id:
            Line identifier, typically ``IDFM:C01742``.
        directions:
            Iterable of direction codes (`"A"` / `"B"`).
        """

        if not self._enabled:
            return {}

        results: Dict[str, List[VmtrVehicle]] = {}
        for direction in directions:
            try:
                vehicles = self._fetch_direction(line_id, direction)
                if vehicles:
                    results[direction] = vehicles
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("VMTR fetch failed for %s %s: %s", line_id, direction, exc, exc_info=True)
                continue
        return results

    # Internal helpers -----------------------------------------------------

    def _fetch_direction(self, line_id: str, direction: str) -> List[VmtrVehicle]:
        """Open the websocket for a single direction and collect the latest payload."""

        if not line_id:
            return []

        normalized_line_id = self._normalize_line_id(line_id)
        vmtr_direction = "A" if direction.upper() == "A" else "R"

        room_name = f"LIG:{normalized_line_id}"
        direction_id = f"DIR:{normalized_line_id}:{vmtr_direction}"

        query = f"?roomName={quote(room_name)}&directionId={quote(direction_id)}&EIO=4&transport=websocket"
        url = f"{self._base_url}{query}"

        headers = [
            f"User-Agent: {_USER_AGENT}",
            "Origin: https://www.ratp.fr",
            "Pragma: no-cache",
            "Cache-Control: no-cache",
        ]

        ws = websocket.create_connection(  # type: ignore[attr-defined]
            url,
            timeout=self._connect_timeout,
            header=headers,
        )

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

                if message.startswith("0"):  # handshake
                    ws.send("40")
                    continue

                if message.startswith("40"):
                    continue

                if not message.startswith("42"):
                    continue

                payload = self._parse_socket_payload(message)
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
    def _parse_socket_payload(message: str) -> Optional[tuple[str, Dict]]:
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
