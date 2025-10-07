"""Service helpers for working with line records."""

from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.line import Line
from services.ratp_client import RatpClient


class LineNotFoundError(Exception):
    """Raised when a requested line code cannot be resolved."""


class LineService:
    """Utility service to resolve and persist line information."""

    def __init__(self, db: AsyncSession, ratp_client: Optional[RatpClient] = None):
        self._db = db
        self._ratp_client = ratp_client or RatpClient()

    async def get_or_create_line(self, line_code: str) -> Line:
        """
        Fetch a `Line` record by code or create it from static catalogue data.

        Args:
            line_code: The line identifier (e.g. "1", "A").

        Returns:
            Persisted `Line` instance attached to the session.

        Raises:
            LineNotFoundError: If the line cannot be resolved from the catalogue.
        """
        normalized_code = line_code.strip()

        # Look for an existing record first
        result = await self._db.execute(
            select(Line).where(Line.line_code == normalized_code)
        )
        line = result.scalar_one_or_none()
        if line:
            return line

        # Fall back to the static catalogue exposed by RatpClient
        catalogue = await self._ratp_client.get_lines()
        matched = next(
            (entry for entry in catalogue if entry["code"].lower() == normalized_code.lower()),
            None,
        )

        if not matched:
            raise LineNotFoundError(f"Unknown line code: {normalized_code}")

        line = Line(
            line_code=matched["code"],
            line_name=matched.get("name", matched["code"]),
            transport_type=matched.get("type", "unknown"),
            color=matched.get("color"),
        )
        self._db.add(line)
        await self._db.flush()
        await self._db.refresh(line)
        return line
