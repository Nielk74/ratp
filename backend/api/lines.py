"""API routes for line information."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from services.ratp_client import RatpClient

router = APIRouter()
ratp_client = RatpClient()


@router.get("/")
async def get_lines(
    transport_type: Optional[str] = Query(
        None,
        description="Filter by transport type (metro, rer, tram, bus)"
    )
):
    """Get list of available RATP lines."""
    try:
        lines = await ratp_client.get_lines(transport_type)
        return {"lines": lines, "count": len(lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{transport_type}/{line_code}/stations")
async def get_line_stations(
    transport_type: str,
    line_code: str
):
    """Get all stations for a specific line."""
    try:
        stations = await ratp_client.get_stations(transport_type, line_code)
        return stations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
