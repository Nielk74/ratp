"""API routes for aggregated scraper snapshots."""

from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter, HTTPException, Query

from ..services.scrapers.line_snapshot import line_snapshot_service

router = APIRouter()


@router.get("/{network}/{line_code}")
async def get_line_snapshot(
    network: str,
    line_code: str,
    refresh: bool = Query(False, description="Force a fresh scrape instead of cached data."),
    max_workers: int = Query(4, ge=1, le=6, description="Maximum parallel fetches against ratp.fr."),
):
    """Return the aggregated scraper snapshot for a given line."""
    loop = asyncio.get_running_loop()
    try:
        snapshot = await loop.run_in_executor(
            None,
            partial(
                line_snapshot_service.get_snapshot,
                network,
                line_code,
                refresh=refresh,
                max_workers=max_workers,
            ),
        )
        return snapshot
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(exc)) from exc
