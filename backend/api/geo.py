"""API routes for geolocation-based features."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services.geo_service import GeoService
from services.ratp_client import RatpClient

router = APIRouter()
geo_service = GeoService()
ratp_client = RatpClient()


@router.get("/nearest")
async def find_nearest_stations(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    max_distance: Optional[float] = Query(None, gt=0, description="Maximum distance in km")
):
    """
    Find nearest RATP stations to a given location.

    Returns stations sorted by distance with their coordinates.
    """
    try:
        # For now, we'll use hardcoded station data
        # In production, this would query the database
        sample_stations = [
            {"name": "Châtelet", "latitude": 48.8584, "longitude": 2.3470, "lines": ["1", "4", "7", "11", "14"]},
            {"name": "Gare du Nord", "latitude": 48.8809, "longitude": 2.3553, "lines": ["4", "5"]},
            {"name": "République", "latitude": 48.8672, "longitude": 2.3636, "lines": ["3", "5", "8", "9", "11"]},
            {"name": "Nation", "latitude": 48.8485, "longitude": 2.3962, "lines": ["1", "2", "6", "9"]},
            {"name": "La Défense", "latitude": 48.8917, "longitude": 2.2384, "lines": ["1"]},
        ]

        nearest = geo_service.find_nearest_stations(
            lat,
            lon,
            sample_stations,
            max_results,
            max_distance
        )

        result = [
            {
                "station": station,
                "distance_km": round(distance, 2),
                "distance_m": round(distance * 1000, 0)
            }
            for station, distance in nearest
        ]

        return {"results": result, "count": len(result)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
