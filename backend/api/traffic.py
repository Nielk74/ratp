"""API routes for traffic information."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.ratp_client import RatpClient, RateLimitExceeded

router = APIRouter()
ratp_client = RatpClient()


@router.get("/")
async def get_traffic(
    line_code: Optional[str] = Query(
        None,
        description="Filter by line code (e.g., '1', 'A', 'T3a')"
    )
):
    """
    Get real-time traffic information for all lines or a specific line.

    Returns current traffic status, incidents, delays, and maintenance info.
    """
    try:
        traffic_data = await ratp_client.get_traffic_info(line_code)
        return traffic_data
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
