"""API routes for schedule information."""

from fastapi import APIRouter, HTTPException, Path
from typing import Optional

from services.ratp_client import RatpClient

router = APIRouter()
ratp_client = RatpClient()


@router.get("/{transport_type}/{line_code}/{station}/{direction}")
async def get_schedules(
    transport_type: str = Path(..., description="Transport type (metros, rers, tramways, buses)"),
    line_code: str = Path(..., description="Line code (e.g., '1', 'A')"),
    station: str = Path(..., description="Station name (URL-encoded)"),
    direction: str = Path(..., description="Direction (e.g., 'A+R' for all)")
):
    """
    Get real-time schedules for a specific station.

    Returns next departures with estimated wait times.
    """
    try:
        schedules = await ratp_client.get_schedules(
            transport_type,
            line_code,
            station,
            direction
        )
        return schedules
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
