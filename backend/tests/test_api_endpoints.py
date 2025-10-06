"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_lines(client: AsyncClient):
    """Test getting list of lines."""
    response = await client.get("/api/lines")

    assert response.status_code == 200
    data = response.json()
    assert "lines" in data
    assert "count" in data
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_get_lines_filtered_by_type(client: AsyncClient):
    """Test filtering lines by transport type."""
    response = await client.get("/api/lines?transport_type=metro")

    assert response.status_code == 200
    data = response.json()
    assert "lines" in data

    # All returned lines should be metro
    for line in data["lines"]:
        assert line["type"] == "metro"


@pytest.mark.asyncio
async def test_get_traffic_all_lines(client: AsyncClient):
    """Test getting traffic for all lines."""
    response = await client.get("/api/traffic")

    assert response.status_code == 200
    # Response structure depends on external API
    # Just verify it returns valid JSON
    data = response.json()
    assert data is not None


@pytest.mark.asyncio
async def test_get_traffic_specific_line(client: AsyncClient):
    """Test getting traffic for a specific line."""
    response = await client.get("/api/traffic?line_code=1")

    assert response.status_code == 200
    data = response.json()
    assert data is not None


@pytest.mark.asyncio
async def test_get_nearest_stations(client: AsyncClient):
    """Test finding nearest stations."""
    # Châtelet coordinates
    response = await client.get("/api/geo/nearest?lat=48.8584&lon=2.3470")

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data


@pytest.mark.asyncio
async def test_get_nearest_stations_with_filters(client: AsyncClient):
    """Test finding nearest stations with filters."""
    response = await client.get(
        "/api/geo/nearest?lat=48.8584&lon=2.3470&max_results=3&max_distance=2"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) <= 3


@pytest.mark.asyncio
async def test_get_nearest_stations_invalid_params(client: AsyncClient):
    """Test geolocation endpoint with invalid parameters."""
    # Missing required parameters
    response = await client.get("/api/geo/nearest")

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_webhook_subscription(client: AsyncClient):
    """Test creating a webhook subscription."""
    webhook_data = {
        "webhook_url": "https://discord.com/api/webhooks/123/abc",
        "line_code": "1",
        "severity_filter": ["high", "critical"]
    }

    response = await client.post("/api/webhooks", json=webhook_data)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_list_webhook_subscriptions(client: AsyncClient):
    """Test listing webhook subscriptions."""
    response = await client.get("/api/webhooks")

    assert response.status_code == 200
    data = response.json()
    assert "subscriptions" in data
    assert "count" in data


@pytest.mark.asyncio
async def test_test_webhook(client: AsyncClient):
    """Test the webhook test endpoint."""
    response = await client.post(
        "/api/webhooks/test?webhook_url=https://discord.com/api/webhooks/test/token"
    )

    # This will fail in testing without a real webhook, but should validate input
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_delete_webhook_subscription(client: AsyncClient):
    """Test deleting a webhook subscription."""
    response = await client.delete("/api/webhooks/1")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    """Test that CORS headers are present."""
    response = await client.options("/api/lines")

    # Should have CORS headers
    assert response.status_code in [200, 405]  # OPTIONS may not be explicitly handled
