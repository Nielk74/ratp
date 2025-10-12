"""API routes for aggregated scraper snapshots."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import partial

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_session
from ..models import LiveSnapshot
from ..services.scrapers.line_snapshot import line_snapshot_service

router = APIRouter()


async def _store_snapshot(
    db: AsyncSession,
    network: str,
    line_code: str,
    payload: dict | None,
    status: str,
    error_message: str | None,
    run_id: str | None = None,
) -> None:
    stmt = select(LiveSnapshot).where(
        LiveSnapshot.network == network,
        LiveSnapshot.line == line_code,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    metadata = {"source": "on-demand"}
    if record:
        record.status = status
        record.payload = payload
        record.error_message = error_message
        record.context = metadata
        record.fetched_at = now
        record.scheduler_run_id = run_id
    else:
        record = LiveSnapshot(
            network=network,
            line=line_code,
            status=status,
            payload=payload,
            error_message=error_message,
            context=metadata,
            fetched_at=now,
            scheduler_run_id=run_id,
        )
        db.add(record)
    await db.flush()


@router.get("/{network}/{line_code}")
async def get_line_snapshot(
    network: str,
    line_code: str,
    refresh: bool = Query(False, description="Force a fresh scrape instead of cached data."),
    station_limit: int | None = Query(
        default=None,
        ge=1,
        le=50,
        description="Limit the number of stations per direction (useful for tests).",
    ),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the aggregated scraper snapshot for a given line."""
    normalized_network = network.lower()
    normalized_line = line_code.upper()

    if not refresh and station_limit is None:
        stmt = (
            select(LiveSnapshot)
            .where(
                LiveSnapshot.network == normalized_network,
                LiveSnapshot.line == normalized_line,
            )
            .order_by(desc(LiveSnapshot.fetched_at))
            .limit(1)
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record and record.payload:
            return record.payload
        if record and record.error_message:
            raise HTTPException(status_code=503, detail=record.error_message)

    loop = asyncio.get_running_loop()
    try:
        snapshot = await loop.run_in_executor(
            None,
            partial(
                line_snapshot_service.get_snapshot,
                normalized_network,
                normalized_line,
                refresh=True,
                station_limit=station_limit,
            ),
        )
        if station_limit is None:
            await _store_snapshot(db, normalized_network, normalized_line, snapshot, "success", None)
        return snapshot
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        if station_limit is None:
            await _store_snapshot(db, normalized_network, normalized_line, None, "error", str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
