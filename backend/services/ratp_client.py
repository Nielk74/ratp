"""RATP API client for fetching real-time data."""

import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
from ..config import settings
from .cache_service import CacheService


class RateLimitExceeded(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class RatpClient:
    """Client for interacting with RATP APIs (PRIM and Community)."""

    def __init__(self):
        self.prim_url = settings.prim_api_url
        self.prim_key = settings.prim_api_key
        self.community_url = settings.community_api_url
        self.cache = CacheService()

        # Rate limiting counters
        self._prim_traffic_count = 0
        self._prim_departures_count = 0
        self._last_reset = datetime.now()

    def _check_rate_limit(self, endpoint_type: str) -> None:
        """Check if rate limit has been exceeded."""
        # Reset counters daily
        if datetime.now() - self._last_reset > timedelta(days=1):
            self._prim_traffic_count = 0
            self._prim_departures_count = 0
            self._last_reset = datetime.now()

        if endpoint_type == "traffic":
            if self._prim_traffic_count >= settings.rate_limit_prim_traffic_per_day:
                raise RateLimitExceeded("PRIM traffic API rate limit exceeded")
        elif endpoint_type == "departures":
            if self._prim_departures_count >= settings.rate_limit_prim_departures_per_day:
                raise RateLimitExceeded("PRIM departures API rate limit exceeded")

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

    async def get_traffic_info(self, line_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Get traffic information for all lines or a specific line using PRIM API.

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

        # Try PRIM API (official Île-de-France Mobilités API)
        if self.prim_key:
            try:
                self._check_rate_limit("traffic")

                # PRIM API endpoint for traffic info
                url = f"{self.prim_url}/v2/navitia/line_reports"
                headers = {
                    "apiKey": self.prim_key,
                    "Accept": "application/json"
                }

                # Add line filter if specified
                params = {"count": 100}

                params = {"count": 100}
                if line_code:
                    params["q"] = line_code

                data = await self._fetch_with_retry(
                    url,
                    headers=headers,
                    params=params,
                    timeout=10,
                )
                self._prim_traffic_count += 1

                # Transform PRIM response to our format
                result = {
                    "status": "ok",
                    "message": "Traffic data from PRIM API",
                    "source": "prim_api",
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                }

                # Filter by line if specified
                if line_code and "line_reports" in data:
                    result["data"]["line_reports"] = [
                        report for report in data.get("line_reports", [])
                        if line_code in report.get("line", {}).get("code", "")
                    ]

                # Cache the result
                await self.cache.set(cache_key, result, ttl=settings.cache_ttl_traffic)
                return result

            except RateLimitExceeded as e:
                return {
                    "status": "rate_limited",
                    "message": "PRIM API rate limit exceeded. Please try again later.",
                    "error": str(e),
                    "source": "prim_api",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                # Log PRIM API error but continue to try community API
                print(f"PRIM API error: {str(e)}")

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
            return data

        except Exception as e:
            # Return informative message about API key requirement
            message = "Unable to fetch real-time traffic data."
            if not self.prim_key:
                message += " Please configure PRIM_API_KEY environment variable. Get your free API key at: https://prim.iledefrance-mobilites.fr"
            else:
                message += " Both PRIM and community APIs are currently unavailable."

            fallback = {
                "status": "unavailable",
                "message": message,
                "error": str(e),
                "source": "no_api_available",
                "timestamp": datetime.now().isoformat(),
                "help": {
                    "prim_api_configured": bool(self.prim_key),
                    "instructions": "To enable real-time traffic data, get a free API key from https://prim.iledefrance-mobilites.fr and set PRIM_API_KEY environment variable."
                }
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

        # Hardcoded Paris metro lines for now (can be extended)
        metro_lines = [
            {"code": "1", "name": "La Défense - Château de Vincennes", "type": "metro", "color": "#FFCD00"},
            {"code": "2", "name": "Porte Dauphine - Nation", "type": "metro", "color": "#003CA6"},
            {"code": "3", "name": "Pont de Levallois - Gallieni", "type": "metro", "color": "#837902"},
            {"code": "4", "name": "Porte de Clignancourt - Mairie de Montrouge", "type": "metro", "color": "#BB4A9B"},
            {"code": "5", "name": "Bobigny - Place d'Italie", "type": "metro", "color": "#FF7E2E"},
            {"code": "6", "name": "Charles de Gaulle - Nation", "type": "metro", "color": "#6ECA97"},
            {"code": "7", "name": "La Courneuve - Villejuif/Mairie d'Ivry", "type": "metro", "color": "#FA9ABA"},
            {"code": "8", "name": "Balard - Créteil", "type": "metro", "color": "#E19BDF"},
            {"code": "9", "name": "Pont de Sèvres - Mairie de Montreuil", "type": "metro", "color": "#B6BD00"},
            {"code": "10", "name": "Boulogne - Gare d'Austerlitz", "type": "metro", "color": "#C9910D"},
            {"code": "11", "name": "Châtelet - Mairie des Lilas", "type": "metro", "color": "#704B1C"},
            {"code": "12", "name": "Front Populaire - Mairie d'Issy", "type": "metro", "color": "#007852"},
            {"code": "13", "name": "Saint-Denis - Châtillon", "type": "metro", "color": "#6EC4E8"},
            {"code": "14", "name": "Saint-Lazare - Olympiades", "type": "metro", "color": "#62259D"},
        ]

        result = metro_lines if not transport_type or transport_type == "metro" else []
        await self.cache.set(cache_key, result, ttl=86400)  # Cache for 1 day

        return result
