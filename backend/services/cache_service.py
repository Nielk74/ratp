"""In-memory cache service (with optional Redis support)."""

from typing import Any, Optional
import asyncio
from datetime import datetime, timedelta
import json


class CacheService:
    """Simple in-memory cache with TTL support."""

    def __init__(self):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._enabled = True

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if not self._enabled:
            return None

        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            else:
                # Clean up expired entry
                del self._cache[key]

        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time to live in seconds (default: 5 minutes)
        """
        if not self._enabled:
            return

        expiry = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]

    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    async def cleanup_expired(self) -> None:
        """Remove all expired entries."""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if now >= expiry
        ]
        for key in expired_keys:
            del self._cache[key]
