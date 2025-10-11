"""RATP API client for fetching real-time data."""

import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import asyncio
import math
from ..config import settings
from .cache_service import CacheService
from .station_data import STATION_FALLBACKS
from .scrapers.ratp_traffic import RatpTrafficScraper


class RateLimitExceeded(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class RatpClient:
    """Client for interacting with RATP sources (ratp.fr scraper and community API)."""

    def __init__(self):
        self.community_url = settings.community_api_url
        self.cache = CacheService()
        self._traffic_scraper = RatpTrafficScraper()

        self._line_catalog: List[Dict[str, Any]] = [
            # Metro lines
            {"code": "1", "name": "La Défense – Château de Vincennes", "type": "metro", "color": "#FFCD00"},
            {"code": "2", "name": "Porte Dauphine – Nation", "type": "metro", "color": "#003CA6"},
            {"code": "3", "name": "Pont de Levallois – Gallieni", "type": "metro", "color": "#837902"},
            {"code": "4", "name": "Porte de Clignancourt – Bagneux", "type": "metro", "color": "#BB4A9B"},
            {"code": "5", "name": "Bobigny – Place d'Italie", "type": "metro", "color": "#FF7E2E"},
            {"code": "6", "name": "Charles de Gaulle – Nation", "type": "metro", "color": "#6ECA97"},
            {"code": "7", "name": "La Courneuve – Villejuif / Mairie d'Ivry", "type": "metro", "color": "#FA9ABA"},
            {"code": "8", "name": "Balard – Créteil", "type": "metro", "color": "#E19BDF"},
            {"code": "9", "name": "Pont de Sèvres – Mairie de Montreuil", "type": "metro", "color": "#B6BD00"},
            {"code": "10", "name": "Boulogne – Gare d'Austerlitz", "type": "metro", "color": "#C9910D"},
            {"code": "11", "name": "Châtelet – Rosny-Bois-Perrier", "type": "metro", "color": "#704B1C"},
            {"code": "12", "name": "Front Populaire – Mairie d'Issy", "type": "metro", "color": "#007852"},
            {"code": "13", "name": "Saint-Denis / Gennevilliers – Châtillon", "type": "metro", "color": "#6EC4E8"},
            {"code": "14", "name": "Saint-Denis Pleyel – Orly", "type": "metro", "color": "#62259D"},
            # RER lines
            {"code": "A", "name": "RER A", "type": "rer", "color": "#F9423A"},
            {"code": "B", "name": "RER B", "type": "rer", "color": "#4A95C5"},
            {"code": "C", "name": "RER C", "type": "rer", "color": "#FCD946"},
            {"code": "D", "name": "RER D", "type": "rer", "color": "#00A651"},
            {"code": "E", "name": "RER E", "type": "rer", "color": "#C7007D"},
            # Tram lines
            {"code": "T1", "name": "Noisy-le-Sec – Asnières – Gennevilliers", "type": "tram", "color": "#8DC63F"},
            {"code": "T2", "name": "Pont de Bezons – Porte de Versailles", "type": "tram", "color": "#0055A4"},
            {"code": "T3a", "name": "Pont du Garigliano – Porte de Vincennes", "type": "tram", "color": "#FF5A00"},
            {"code": "T3b", "name": "Porte de Vincennes – Porte d'Asnières", "type": "tram", "color": "#FF5A00"},
            {"code": "T7", "name": "Villejuif – Athis-Mons", "type": "tram", "color": "#00AEEF"},
            {"code": "T13", "name": "Saint-Cyr – Saint-Germain-en-Laye", "type": "tram", "color": "#6B2C91"},
            # Transilien / SNCF
            {"code": "H", "name": "Transilien H", "type": "transilien", "color": "#7ACCC8"},
            {"code": "J", "name": "Transilien J", "type": "transilien", "color": "#0075C9"},
            {"code": "L", "name": "Transilien L", "type": "transilien", "color": "#A2006D"},
            {"code": "N", "name": "Transilien N", "type": "transilien", "color": "#00A86B"},
            {"code": "P", "name": "Transilien P", "type": "transilien", "color": "#F1921D"},
            {"code": "U", "name": "Transilien U", "type": "transilien", "color": "#5C2D91"},
        ]

    async def _fetch_with_retry(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 2,
        timeout: int = 5
    ) -> Dict[str, Any]:
        """Fetch data from API with retry logic."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(
                        url,
                        headers=headers or {},
                        params=params or {},
                    )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:  # Too Many Requests
                        raise RateLimitExceeded(f"API rate limit exceeded: {url}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                except httpx.RequestError as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)

    async def _fetch_idfm_stations(
        self,
        transport_type: str,
        line_code: str,
    ) -> List[Dict[str, Any]]:
        """Fetch station list from IDFM open data as fallback."""
        mode_map = {
            "metro": "Metro",
            "rer": "RapidTransit",
            "tram": "Tramway",
            "transilien": "LocalTrain",
            "bus": "Bus",
        }

        mode = mode_map.get(transport_type)
        if not mode:
            return []

        params = {
            "where": f"mode='{mode}' and shortname='{line_code.upper()}'",
            "limit": 100,
        }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    "https://data.iledefrance-mobilites.fr/api/explore/v2.1/catalog/datasets/arrets-lignes/records",
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results", [])
                unique: Dict[str, Dict[str, Any]] = {}
                for item in results:
                    name = item.get("stop_name")
                    if not name:
                        continue
                    if name in unique:
                        continue
                    unique[name] = {
                        "name": name,
                        "latitude": float(item["stop_lat"]) if item.get("stop_lat") else None,
                        "longitude": float(item["stop_lon"]) if item.get("stop_lon") else None,
                        "city": item.get("nom_commune"),
                        "stop_id": item.get("stop_id"),
                    }

                return sorted(unique.values(), key=lambda item: item.get("name") or "")
        except Exception:
            return []

        return []

    async def get_traffic_info(self, line_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Get traffic information for all lines or a specific line using the public site.

        Args:
            line_code: Optional line code to filter (e.g., "1", "A", "T3a")

        Returns:
            Dictionary with traffic status and incidents
        """
        cache_key = f"traffic:{line_code or 'all'}"

        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        traffic_result: Dict[str, List[Dict[str, Any]]] = {}
        scraper_errors: List[str] = []
        try:
            traffic_result, scraper_errors = await asyncio.to_thread(
                self._traffic_scraper.fetch_status,
                line_code=line_code,
            )
        except Exception as exc:  # pylint: disable=broad-except
            scraper_errors = [f"ratp_site: {exc}"]
            traffic_result = {}

        if traffic_result:
            result = {
                "status": "ok",
                "message": "Traffic data from ratp.fr",
                "source": "ratp_site",
                "timestamp": datetime.now().isoformat(),
                "result": traffic_result,
            }
            if scraper_errors:
                result["errors"] = scraper_errors
            await self.cache.set(cache_key, result, ttl=settings.cache_ttl_traffic)
            return result

        if not scraper_errors:
            result = {
                "status": "ok",
                "message": "No traffic alerts for the requested scope",
                "source": "ratp_site",
                "timestamp": datetime.now().isoformat(),
                "result": traffic_result,
            }
            await self.cache.set(cache_key, result, ttl=settings.cache_ttl_traffic)
            return result

        # Try community API as fallback
        try:
            url = f"{self.community_url}/traffic"
            data = await self._fetch_with_retry(url, timeout=5)

            # Filter by line if specified
            if line_code and isinstance(data, dict) and "result" in data:
                filtered = {
                    k: v for k, v in data["result"].items()
                    if line_code.lower() in k.lower()
                }
                data["result"] = filtered

            # Cache the result
            await self.cache.set(cache_key, data, ttl=settings.cache_ttl_traffic)
            if scraper_errors and isinstance(data, dict):
                existing_errors = data.get("errors")
                if isinstance(existing_errors, list):
                    data["errors"] = existing_errors + scraper_errors
                else:
                    data["errors"] = scraper_errors
            if isinstance(data, dict):
                data.setdefault("source", "community_api")
            return data

        except Exception as e:
            # Return informative message about API key requirement
            message = "Unable to fetch real-time traffic data from ratp.fr or the community API."
            if scraper_errors:
                message += f" Errors: {'; '.join(scraper_errors)}"

            fallback = {
                "status": "unavailable",
                "message": message,
                "error": str(e),
                "source": "no_api_available",
                "timestamp": datetime.now().isoformat(),
                "help": {
                    "ratp_http_available": False,
                    "instructions": "The scraper emulates the ratp.fr traffic pages. Ensure cloudscraper and Playwright dependencies are installed.",
                },
            }
            # Cache fallback for short time
            await self.cache.set(cache_key, fallback, ttl=30)
            return fallback

    async def get_schedules(
        self,
        transport_type: str,
        line_code: str,
        station_name: str,
        direction: str
    ) -> Dict[str, Any]:
        """
        Get real-time schedules for a specific station.

        Args:
            transport_type: Type of transport (metros, rers, tramways, buses)
            line_code: Line code (e.g., "1", "A")
            station_name: Station name (URL-encoded)
            direction: Direction (e.g., "A+R" for all directions)

        Returns:
            Dictionary with schedule data
        """
        cache_key = f"schedule:{transport_type}:{line_code}:{station_name}:{direction}"

        # Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        try:
            # Use community API
            url = f"{self.community_url}/schedules/{transport_type}/{line_code}/{station_name}/{direction}"
            data = await self._fetch_with_retry(url)

            # Cache for short duration (schedules change frequently)
            await self.cache.set(cache_key, data, ttl=settings.cache_ttl_schedules)
            return data

        except Exception as e:
            return {
                "error": str(e),
                "source": "community_api",
                "timestamp": datetime.now().isoformat()
            }

    async def get_stations(self, transport_type: str, line_code: str) -> Dict[str, Any]:
        """
        Get list of stations for a specific line.

        Args:
            transport_type: Type of transport (metros, rers, tramways, buses)
            line_code: Line code

        Returns:
            Dictionary with station list
        """
        cache_key = f"stations:{transport_type}:{line_code}"

        # Check cache (stations don't change often)
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        try:
            url = f"{self.community_url}/stations/{transport_type}/{line_code}"
            data = await self._fetch_with_retry(url)

            # Cache for 24 hours
            await self.cache.set(cache_key, data, ttl=settings.cache_ttl_stations)
            return data

        except Exception as e:
            return {
                "error": str(e),
                "source": "community_api",
                "timestamp": datetime.now().isoformat()
            }

    async def get_lines(self, transport_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available lines.

        Args:
            transport_type: Optional filter by transport type

        Returns:
            List of line information
        """
        cache_key = f"lines:{transport_type or 'all'}"

        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        if transport_type:
            filtered = [line for line in self._line_catalog if line["type"] == transport_type]
        else:
            filtered = list(self._line_catalog)

        await self.cache.set(cache_key, filtered, ttl=86400)

        return filtered

    async def get_line_details(self, transport_type: str, line_code: str) -> Dict[str, Any]:
        """Return rich line details including station list."""
        cache_key = f"line_details:{transport_type}:{line_code}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        code_normalised = line_code.strip().upper()
        line_info = next(
            (line for line in self._line_catalog if line["type"] == transport_type and line["code"].upper() == code_normalised),
            None,
        )

        if not line_info:
            raise ValueError(f"Unknown line {transport_type}:{line_code}")

        type_to_api_segment = {
            "metro": "metros",
            "rer": "rers",
            "tram": "tramways",
            "bus": "buses",
        }

        api_segment = type_to_api_segment.get(transport_type)
        stations_data = await self.get_stations(api_segment, line_code) if api_segment else None
        stations = stations_data.get("result", {}).get("stations", []) if isinstance(stations_data, dict) else []

        # Fallback to static hubs if community API fails
        if not stations:
            stations = await self._fetch_idfm_stations(transport_type, line_code)

        if not stations:
            stations = (
                STATION_FALLBACKS
                .get(transport_type, {})
                .get(code_normalised, [])
            )

        trains = self._simulate_trains(line_info, stations)

        payload = {
            "line": line_info,
            "stations": stations,
            "stations_count": len(stations),
            "source": stations_data.get("source") if isinstance(stations_data, dict) else "unknown",
            "trains": trains,
        }

        await self.cache.set(cache_key, payload, ttl=3600)
        return payload

    def _simulate_trains(
        self,
        line_info: Dict[str, Any],
        stations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate synthetic train positions along the line based on station coordinates."""
        if len(stations) < 2:
            return []

        # Filter stations with coordinates
        coords: List[Dict[str, Any]] = [
            station for station in stations if station.get("latitude") and station.get("longitude")
        ]
        if len(coords) < 2:
            return []

        headway_seconds = 180  # 3 minutes between trains
        dwell_seconds = 90     # dwell at terminus
        segment_time = 90      # travel time per segment
        total_segments = len(coords) - 1
        trip_duration = total_segments * segment_time
        cycle_duration = trip_duration + dwell_seconds
        trains_per_direction = max(2, math.ceil(trip_duration / headway_seconds))

        now = datetime.now(timezone.utc)
        seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second

        trains: List[Dict[str, Any]] = []

        def interpolate(start: Dict[str, Any], end: Dict[str, Any], progress: float) -> Dict[str, float]:
            lat1 = float(start["latitude"])
            lon1 = float(start["longitude"])
            lat2 = float(end["latitude"])
            lon2 = float(end["longitude"])
            return {
                "latitude": lat1 + (lat2 - lat1) * progress,
                "longitude": lon1 + (lon2 - lon1) * progress,
            }

        def simulate_direction(
            station_sequence: List[Dict[str, Any]],
            direction: int,
        ) -> None:
            nonlocal trains
            for idx in range(trains_per_direction):
                offset = idx * headway_seconds
                position_time = (seconds_since_midnight - offset) % cycle_duration
                if position_time >= trip_duration:
                    continue  # currently dwelling at terminus

                segment_index = int(position_time // segment_time)
                in_segment = (position_time % segment_time) / segment_time

                start_station = station_sequence[segment_index]
                end_station = station_sequence[segment_index + 1]

                interpolated = interpolate(start_station, end_station, in_segment)

                trains.append({
                    "train_id": f"{line_info['code']}-{direction}-{idx}",
                    "line_code": line_info["code"],
                    "direction": direction,
                    "position": interpolated,
                    "from_station": start_station.get("name"),
                    "to_station": end_station.get("name"),
                    "progress": round(in_segment, 3),
                    "updated_at": now.isoformat() + "Z",
                })

        simulate_direction(coords, 1)
        simulate_direction(list(reversed(coords)), -1)

        return trains
