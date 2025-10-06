"""Tests for RATP API client."""

import pytest
from unittest.mock import AsyncMock, patch
from backend.services.ratp_client import RatpClient, RateLimitExceeded


@pytest.mark.asyncio
async def test_get_lines():
    """Test getting list of metro lines."""
    client = RatpClient()

    lines = await client.get_lines("metro")

    # Should return Paris metro lines
    assert len(lines) > 0
    assert any(line["code"] == "1" for line in lines)
    assert any(line["code"] == "14" for line in lines)


@pytest.mark.asyncio
async def test_get_lines_uses_cache():
    """Test that repeated calls use cache."""
    client = RatpClient()

    # First call
    lines1 = await client.get_lines("metro")

    # Second call should use cache
    lines2 = await client.get_lines("metro")

    # Should return same data
    assert lines1 == lines2


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_get_traffic_info(mock_get):
    """Test getting traffic information."""
    # Mock API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "metros": [
                {
                    "line": "1",
                    "slug": "normal",
                    "title": "Trafic normal"
                }
            ]
        }
    }
    mock_response.raise_for_status = AsyncMock()
    mock_get.return_value = mock_response

    client = RatpClient()
    traffic = await client.get_traffic_info()

    assert "result" in traffic
    assert mock_get.called


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_get_schedules(mock_get):
    """Test getting schedule information."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "schedules": [
                {"message": "1 mn", "destination": "La Défense"}
            ]
        }
    }
    mock_response.raise_for_status = AsyncMock()
    mock_get.return_value = mock_response

    client = RatpClient()
    schedules = await client.get_schedules(
        "metros", "1", "chatelet", "A"
    )

    assert "result" in schedules
    assert mock_get.called


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_with_retry_on_failure(mock_get):
    """Test retry logic on API failures."""
    # First call fails, second succeeds
    mock_response_fail = AsyncMock()
    mock_response_fail.raise_for_status.side_effect = Exception("Network error")

    mock_response_success = AsyncMock()
    mock_response_success.status_code = 200
    mock_response_success.json.return_value = {"data": "success"}
    mock_response_success.raise_for_status = AsyncMock()

    mock_get.side_effect = [mock_response_fail, mock_response_success]

    client = RatpClient()
    result = await client._fetch_with_retry("https://test.com", max_retries=2)

    assert result == {"data": "success"}
    assert mock_get.call_count == 2


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_rate_limit_exceeded_handling(mock_get):
    """Test handling of 429 rate limit responses."""
    mock_response = AsyncMock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = Exception("Rate limit")
    mock_get.return_value = mock_response

    client = RatpClient()

    with pytest.raises(RateLimitExceeded):
        await client._fetch_with_retry("https://test.com", max_retries=1)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_get_stations(mock_get):
    """Test getting stations for a line."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "stations": [
                {"name": "Châtelet", "slug": "chatelet"}
            ]
        }
    }
    mock_response.raise_for_status = AsyncMock()
    mock_get.return_value = mock_response

    client = RatpClient()
    stations = await client.get_stations("metros", "1")

    assert "result" in stations
    assert mock_get.called
