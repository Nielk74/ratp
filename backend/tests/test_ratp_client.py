"""Tests for RATP API client."""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from backend.services.ratp_client import RatpClient, RateLimitExceeded


@pytest.fixture
def traffic_scraper_stub(monkeypatch):
    """Provide a stubbed traffic scraper so tests avoid hitting Playwright/Cloudflare."""

    stub = Mock()
    stub.fetch_status.return_value = ({}, [])
    monkeypatch.setattr("backend.services.ratp_client.RatpTrafficScraper", lambda: stub)
    return stub


@pytest.mark.asyncio
async def test_get_lines(traffic_scraper_stub):
    """Test getting list of metro lines."""
    client = RatpClient()

    lines = await client.get_lines("metro")

    # Should return Paris metro lines
    assert len(lines) > 0
    assert any(line["code"] == "1" for line in lines)
    assert any(line["code"] == "14" for line in lines)


@pytest.mark.asyncio
async def test_get_lines_transilien(traffic_scraper_stub):
    """Ensure SNCF lines are available."""
    client = RatpClient()

    lines = await client.get_lines("transilien")

    assert any(line["code"] == "L" for line in lines)


@pytest.mark.asyncio
@patch.object(RatpClient, "get_stations", return_value={"result": {"stations": []}})
async def test_get_line_details(mock_stations, traffic_scraper_stub):
    """Test retrieving detailed line information."""
    client = RatpClient()

    details = await client.get_line_details("metro", "1")

    assert details["line"]["code"] == "1"
    mock_stations.assert_called_once()


@pytest.mark.asyncio
async def test_get_lines_uses_cache(traffic_scraper_stub):
    """Test that repeated calls use cache."""
    client = RatpClient()

    # First call
    lines1 = await client.get_lines("metro")

    # Second call should use cache
    lines2 = await client.get_lines("metro")

    # Should return same data
    assert lines1 == lines2


@pytest.mark.asyncio
async def test_get_traffic_info_uses_scraper(traffic_scraper_stub):
    """Traffic info should leverage the ratp.fr scraper."""
    traffic_scraper_stub.fetch_status.return_value = (
        {
            "metros": [
                {"line": "1", "slug": "normal", "title": "Trafic normal"},
            ]
        },
        [],
    )

    client = RatpClient()
    traffic = await client.get_traffic_info()

    assert traffic["source"] == "ratp_site"
    assert "metros" in traffic["result"]
    assert traffic["result"]["metros"][0]["line"] == "1"
    traffic_scraper_stub.fetch_status.assert_called_once_with(line_code=None)


@pytest.mark.asyncio
async def test_get_traffic_info_falls_back_to_community(traffic_scraper_stub):
    """If scraper fails, community API response should be returned."""
    traffic_scraper_stub.fetch_status.side_effect = RuntimeError("blocked")

    fallback_payload: Dict[str, Any] = {
        "result": {
            "metros": [
                {"line": "9", "slug": "normal", "message": "Trafic normal"},
            ]
        }
    }

    async def fake_fetch(url, timeout=5):  # pylint: disable=unused-argument
        return fallback_payload

    client = RatpClient()
    with patch.object(client, "_fetch_with_retry", new=AsyncMock(side_effect=fake_fetch)):
        traffic = await client.get_traffic_info()

    assert traffic["source"] == "community_api"
    assert "metros" in traffic["result"]
    assert traffic["result"]["metros"][0]["line"] == "9"
    assert "blocked" in "; ".join(traffic["errors"])


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_get_schedules(mock_get, traffic_scraper_stub):
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
async def test_fetch_with_retry_on_failure(mock_get, traffic_scraper_stub):
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
async def test_rate_limit_exceeded_handling(mock_get, traffic_scraper_stub):
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
async def test_get_stations(mock_get, traffic_scraper_stub):
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
