"""Tests for cache service."""

import pytest
import asyncio
from backend.services.cache_service import CacheService


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Test setting and getting values from cache."""
    cache = CacheService()

    # Set a value
    await cache.set("test_key", {"data": "test_value"}, ttl=60)

    # Get the value
    result = await cache.get("test_key")
    assert result == {"data": "test_value"}


@pytest.mark.asyncio
async def test_cache_expiry():
    """Test that cached values expire after TTL."""
    cache = CacheService()

    # Set a value with 1 second TTL
    await cache.set("expiry_test", "value", ttl=1)

    # Should be available immediately
    result = await cache.get("expiry_test")
    assert result == "value"

    # Wait for expiry
    await asyncio.sleep(1.1)

    # Should be None after expiry
    result = await cache.get("expiry_test")
    assert result is None


@pytest.mark.asyncio
async def test_cache_delete():
    """Test deleting values from cache."""
    cache = CacheService()

    await cache.set("delete_test", "value", ttl=60)
    assert await cache.get("delete_test") == "value"

    await cache.delete("delete_test")
    assert await cache.get("delete_test") is None


@pytest.mark.asyncio
async def test_cache_clear():
    """Test clearing all cache entries."""
    cache = CacheService()

    await cache.set("key1", "value1", ttl=60)
    await cache.set("key2", "value2", ttl=60)

    await cache.clear()

    assert await cache.get("key1") is None
    assert await cache.get("key2") is None


@pytest.mark.asyncio
async def test_cache_cleanup_expired():
    """Test cleanup of expired entries."""
    cache = CacheService()

    # Add entries with different TTLs
    await cache.set("short_ttl", "value1", ttl=1)
    await cache.set("long_ttl", "value2", ttl=60)

    # Wait for first to expire
    await asyncio.sleep(1.1)

    # Cleanup expired
    await cache.cleanup_expired()

    # Short TTL should be gone, long TTL should remain
    assert await cache.get("short_ttl") is None
    assert await cache.get("long_ttl") == "value2"
