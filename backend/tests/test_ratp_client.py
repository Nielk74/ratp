"""Tests for RATP API client."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

import httpx

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
async def test_get_lines_transilien():
    """Ensure SNCF lines are available."""
    client = RatpClient()

    lines = await client.get_lines("transilien")

    assert any(line["code"] == "L" for line in lines)


@pytest.mark.asyncio
@patch.object(RatpClient, "get_stations", return_value={"result": {"stations": []}})
async def test_get_line_details(mock_stations):
    """Test retrieving detailed line information."""
    client = RatpClient()

    details = await client.get_line_details("metro", "1")

    assert details["line"]["code"] == "1"
    mock_stations.assert_called_once()


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
    mock_response.json = Mock(return_value={
        "result": {
            "metros": [
                {
                    "line": "1",
                    "slug": "normal",
                    "title": "Trafic normal"
                }
            ]
        }
    })
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = RatpClient()
    traffic = await client.get_traffic_info()

    assert "data" in traffic
    assert "result" in traffic["data"]
    assert mock_get.called


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_get_schedules(mock_get):
    """Test getting schedule information."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = Mock(return_value={
        "result": {
            "schedules": [
                {"message": "1 mn", "destination": "La Défense"}
            ]
        }
    })
    mock_response.raise_for_status = Mock()
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
    request = httpx.Request("GET", "https://test.com")
    response = httpx.Response(500, request=request)
    mock_response_fail.raise_for_status = Mock(
        side_effect=httpx.HTTPStatusError("Network error", request=request, response=response)
    )

    mock_response_success = AsyncMock()
    mock_response_success.status_code = 200
    mock_response_success.json = Mock(return_value={"data": "success"})
    mock_response_success.raise_for_status = Mock()

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
    request = httpx.Request("GET", "https://test.com")
    response = httpx.Response(429, request=request)
    mock_response.raise_for_status = Mock(
        side_effect=httpx.HTTPStatusError("Rate limit", request=request, response=response)
    )
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
    mock_response.json = Mock(return_value={
        "result": {
            "stations": [
                {"name": "Châtelet", "slug": "chatelet"}
            ]
        }
    })
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = RatpClient()
    stations = await client.get_stations("metros", "1")

    assert "result" in stations
    assert mock_get.called
