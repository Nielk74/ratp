"""Geolocation service for finding nearest stations."""

from typing import List, Dict, Tuple, Optional
from math import radians, cos, sin, asin, sqrt


class GeoService:
    """Service for geolocation calculations."""

    @staticmethod
    def haversine_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees).

        Returns distance in kilometers.
        """
        # Convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))

        # Radius of earth in kilometers
        r = 6371

        return c * r

    @staticmethod
    def find_nearest_stations(
        user_lat: float,
        user_lon: float,
        stations: List[Dict],
        max_results: int = 10,
        max_distance_km: Optional[float] = None
    ) -> List[Tuple[Dict, float]]:
        """
        Find nearest stations to user location.

        Args:
            user_lat: User latitude
            user_lon: User longitude
            stations: List of station dictionaries with 'latitude' and 'longitude'
            max_results: Maximum number of results to return
            max_distance_km: Optional maximum distance filter in kilometers

        Returns:
            List of tuples (station, distance_km) sorted by distance
        """
        stations_with_distance = []

        for station in stations:
            if not station.get("latitude") or not station.get("longitude"):
                continue

            distance = GeoService.haversine_distance(
                user_lat,
                user_lon,
                float(station["latitude"]),
                float(station["longitude"])
            )

            # Apply distance filter if specified
            if max_distance_km is None or distance <= max_distance_km:
                stations_with_distance.append((station, distance))

        # Sort by distance
        stations_with_distance.sort(key=lambda x: x[1])

        # Return top N results
        return stations_with_distance[:max_results]
