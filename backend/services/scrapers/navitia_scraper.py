"""Navitia-based scraper pulling schedules via the PRIM API."""

from __future__ import annotations
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from zoneinfo import ZoneInfo
import requests

from ...config import settings
from .ratp_playwright import ScrapedDeparture, ScraperResult

PARIS_TZ = ZoneInfo("Europe/Paris")


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in stripped.lower() if ch.isalnum())


@dataclass
class _StopArea:
    id: str
    name: str


class NavitiaScraper:
    """Fetch departure boards using Navitia data from the PRIM marketplace."""

    BASE_URL = "https://prim.iledefrance-mobilites.fr/marketplace/v2/navitia"
    REGION = "idfm"

    _NETWORK_CONFIG = {
        "metro": {
            "commercial_mode": "Métro",
            "physical_mode": "physical_mode:Metro",
        },
        "rer": {
            "commercial_mode": "RER",
            "physical_mode": "physical_mode:RapidTransit",
        },
        "tram": {
            "commercial_mode": "Tramway",
            "physical_mode": "physical_mode:Tramway",
        },
        "transilien": {
            "commercial_mode": "Train Transilien",
            "physical_mode": "physical_mode:LocalTrain",
        },
    }

    _DIRECTION_MAP = {"A": "outbound", "B": "inbound"}

    def __init__(self, *, api_key: Optional[str] = None, mode: Optional[str] = None) -> None:
        self._mode = (mode or settings.navitia_scraper_mode).lower()
        self.is_mock = self._mode == "mock"
        self.is_disabled = self._mode in {"disabled", "off"}

        if self.is_disabled:
            raise RuntimeError("Navitia scraper disabled by configuration")

        self._line_cache: Dict[tuple[str, str], str] = {}
        self._stop_area_cache: Dict[str, Dict[str, _StopArea]] = {}

        if self.is_mock:
            self._session = None
            self._api_key = ""
            return

        self._api_key = api_key or settings.prim_api_key
        if not self._api_key:
            raise RuntimeError("PRIM_API_KEY is required to use Navitia scraper")

        self._session = requests.Session()
        self._session.headers.update(
            {
                "apiKey": self._api_key,
                "Accept": "application/json",
            }
        )

    # Public API -----------------------------------------------------------------

    def fetch_station_board(
        self,
        *,
        network: str,
        line: str,
        station: str,
        direction: str,
    ) -> ScraperResult:
        if self._mode == "mock":
            return self._mock_station_board(network=network, line=line, station=station, direction=direction)

        normalized_network = network.lower()
        line_code = line.upper()

        line_id = self._resolve_line_id(normalized_network, line_code)
        stop_area = self._resolve_stop_area(line_id, station)
        if not stop_area:
            raise ValueError(f"Unknown stop {station} on {network}:{line}")

        direction_type = self._DIRECTION_MAP.get(direction.upper())
        departures = self._fetch_departures(stop_area.id, line_id, direction_type)

        metadata = {
            "network": normalized_network,
            "line": line_code,
            "station": station,
            "direction": direction,
            "line_id": line_id,
            "stop_area_id": stop_area.id,
            "timestamp": datetime.now(PARIS_TZ).timestamp(),
            "source": "navitia",
            "region": self.REGION,
        }

        return ScraperResult(
            url=f"{self.BASE_URL}/stop_areas/{stop_area.id}/departures",
            departures=departures,
            raw_state={"line_id": line_id, "stop_area": stop_area.id},
            metadata=metadata,
        )

    # Internal helpers -----------------------------------------------------------

    def _resolve_line_id(self, network: str, line_code: str) -> str:
        cache_key = (network, line_code)
        if cache_key in self._line_cache:
            return self._line_cache[cache_key]

        config = self._NETWORK_CONFIG.get(network)
        if not config:
            raise ValueError(f"Unsupported network {network} for Navitia scraper")

        params = {
            "region": self.REGION,
            "filter": f'line.code="{line_code}"',
            "count": 50,
        }
        physical_mode = config.get("physical_mode")
        if physical_mode:
            params["physical_mode"] = physical_mode

        response = self._session.get(f"{self.BASE_URL}/lines", params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        lines = data.get("lines") or []
        for entry in lines:
            commercial_mode = ((entry.get("commercial_mode") or {}).get("name") or "").strip()
            if commercial_mode == config["commercial_mode"]:
                line_id = entry.get("id")
                if line_id:
                    self._line_cache[cache_key] = line_id
                    return line_id

        raise ValueError(f"Unable to resolve Navitia line id for {network}:{line_code}")

    def _resolve_stop_area(self, line_id: str, station: str) -> Optional[_StopArea]:
        cache = self._stop_area_cache.get(line_id)
        if cache is None:
            params = {"region": self.REGION, "count": 200}
            response = self._session.get(
                f"{self.BASE_URL}/lines/{line_id}/stop_areas", params=params, timeout=20
            )
            response.raise_for_status()
            payload = response.json()
            stop_areas = payload.get("stop_areas") or []
            cache = {}
            for entry in stop_areas:
                name = entry.get("name") or ""
                stop_id = entry.get("id")
                if not name or not stop_id:
                    continue
                cache[_normalize(name)] = _StopArea(id=stop_id, name=name)
            self._stop_area_cache[line_id] = cache

        return cache.get(_normalize(station)) if cache else None

    def _fetch_departures(
        self,
        stop_area_id: str,
        line_id: str,
        direction_type: Optional[str],
    ) -> List[ScrapedDeparture]:
        params = {
            "region": self.REGION,
            "count": 10,
            "filter": f'line.id="{line_id}"',
        }
        response = self._session.get(
            f"{self.BASE_URL}/stop_areas/{stop_area_id}/departures",
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        departures: List[ScrapedDeparture] = []
        entries = payload.get("departures") or []
        now = datetime.now(PARIS_TZ)

        for entry in entries:
            route = entry.get("route") or {}
            route_line = (route.get("line") or {}).get("id")
            if route_line != line_id:
                continue
            if direction_type and route.get("direction_type") != direction_type:
                continue

            display = entry.get("display_informations") or {}
            headsign = display.get("direction") or display.get("headsign")
            stop_info = entry.get("stop_point") or {}

            wait_text, minutes = self._format_wait(entry, now)
            raw_text = f"{wait_text} → {headsign}" if headsign else wait_text

            departures.append(
                ScrapedDeparture(
                    raw_text=raw_text,
                    destination=headsign,
                    waiting_time=wait_text,
                    status=entry.get("stop_date_time", {}).get("data_freshness"),
                    platform=stop_info.get("name"),
                    extra={
                        "departure_date_time": entry.get("stop_date_time", {}).get("departure_date_time"),
                        "line_id": line_id,
                        "direction_type": route.get("direction_type"),
                    },
                )
            )

        return departures

    # Mock mode helpers ---------------------------------------------------------

    def _mock_station_board(
        self,
        *,
        network: str,
        line: str,
        station: str,
        direction: str,
    ) -> ScraperResult:
        base_waits = [2, 5, 9]
        direction_label = "terminus" if direction.upper() == "A" else "origin"
        departures: List[ScrapedDeparture] = []
        now = datetime.now(PARIS_TZ)
        for idx, minutes in enumerate(base_waits):
            wait_text = "À quai" if minutes == 0 else f"{minutes} mn"
            destination = f"{direction.upper()} {line}"
            departures.append(
                ScrapedDeparture(
                    raw_text=f"{wait_text} → {destination}",
                    destination=destination,
                    waiting_time=wait_text,
                    status="mock",
                    extra={
                        "mock": True,
                        "offset": idx,
                        "generated_at": now.isoformat(),
                    },
                )
            )

        metadata = {
            "network": network.lower(),
            "line": line.upper(),
            "station": station,
            "direction": direction,
            "source": "navitia-mock",
            "timestamp": now.timestamp(),
            "direction_hint": direction_label,
        }
        return ScraperResult(
            url="mock://navitia",
            departures=departures,
            raw_state={"mode": "mock"},
            metadata=metadata,
        )

    def _format_wait(self, entry: Dict, now: datetime) -> tuple[str, Optional[int]]:
        stop_dt = entry.get("stop_date_time") or {}
        date_str = stop_dt.get("departure_date_time")
        if not date_str:
            return ("?", None)

        try:
            scheduled = datetime.strptime(date_str, "%Y%m%dT%H%M%S").replace(tzinfo=PARIS_TZ)
        except ValueError:
            return ("?", None)

        delta_minutes = int((scheduled - now).total_seconds() // 60)
        if delta_minutes <= 0:
            return ("À quai", 0)
        return (f"{delta_minutes} mn", delta_minutes)
