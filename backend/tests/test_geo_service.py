"""Tests for geolocation service."""

import pytest
from backend.services.geo_service import GeoService


def test_haversine_distance():
    """Test distance calculation between two points."""
    geo = GeoService()

    # Distance between Paris (Châtelet) and Gare du Nord
    # Châtelet: 48.8584, 2.3470
    # Gare du Nord: 48.8809, 2.3553
    distance = geo.haversine_distance(48.8584, 2.3470, 48.8809, 2.3553)

    # Should be approximately 2.5 km
    assert 2.0 < distance < 3.0


def test_haversine_same_location():
    """Test distance between same point is zero."""
    geo = GeoService()

    distance = geo.haversine_distance(48.8566, 2.3522, 48.8566, 2.3522)
    assert distance < 0.001  # Essentially zero


def test_find_nearest_stations():
    """Test finding nearest stations to a location."""
    geo = GeoService()

    # Mock station data
    stations = [
        {"name": "Station A", "latitude": 48.8600, "longitude": 2.3500},
        {"name": "Station B", "latitude": 48.8700, "longitude": 2.3600},
        {"name": "Station C", "latitude": 48.8500, "longitude": 2.3400},
    ]

    # User location (close to Station A)
    user_lat, user_lon = 48.8590, 2.3490

    results = geo.find_nearest_stations(user_lat, user_lon, stations, max_results=2)

    # Should return 2 results
    assert len(results) == 2

    # First result should be Station A (closest)
    assert results[0][0]["name"] == "Station A"

    # Distance should be small
    assert results[0][1] < 1.0  # Less than 1 km


def test_find_nearest_stations_with_max_distance():
    """Test filtering stations by maximum distance."""
    geo = GeoService()

    stations = [
        {"name": "Near", "latitude": 48.8600, "longitude": 2.3500},
        {"name": "Far", "latitude": 48.9000, "longitude": 2.4000},
    ]

    user_lat, user_lon = 48.8590, 2.3490

    # Only stations within 2 km
    results = geo.find_nearest_stations(
        user_lat, user_lon, stations, max_results=10, max_distance_km=2.0
    )

    # Should only return the near station
    assert len(results) == 1
    assert results[0][0]["name"] == "Near"


def test_find_nearest_stations_ignores_missing_coords():
    """Test that stations without coordinates are ignored."""
    geo = GeoService()

    stations = [
        {"name": "Valid", "latitude": 48.8600, "longitude": 2.3500},
        {"name": "No Coords", "latitude": None, "longitude": None},
        {"name": "Partial Coords", "latitude": 48.8700, "longitude": None},
    ]

    results = geo.find_nearest_stations(48.8590, 2.3490, stations, max_results=10)

    # Should only return station with valid coordinates
    assert len(results) == 1
    assert results[0][0]["name"] == "Valid"
