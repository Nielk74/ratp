"""API routes for traffic information."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..services.ratp_client import RatpClient, RateLimitExceeded
from ..services.traffic_status import TrafficStatusService

router = APIRouter()
ratp_client = RatpClient()
status_service = TrafficStatusService()


@router.get("")
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


@router.get("/status")
async def get_traffic_status(
    line_code: Optional[str] = Query(
        None,
        description="Filter status by line code (e.g., '1', 'A', 'T3a')",
    )
):
    """
    Get normalised traffic status for each line.

    Returns aggregated severity level, message and data source for the line.
    """
    try:
        payload = await ratp_client.get_traffic_info(line_code)
        normalised = status_service.normalise(payload)

        if line_code:
            code = line_code.strip().upper()
            normalised["lines"] = [
                line for line in normalised["lines"] if line["line_code"] == code
            ]

        return normalised
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
