"""Tests for Discord webhook service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from backend.services.discord_service import DiscordService


@pytest.mark.asyncio
async def test_discord_service_can_send():
    """Test rate limiting logic for Discord webhooks."""
    service = DiscordService()

    webhook_url = "https://discord.com/api/webhooks/test"

    # First send should be allowed
    assert service._can_send(webhook_url) is True

    # Update last sent time
    from datetime import datetime
    service._last_sent[webhook_url] = datetime.now()

    # Immediate second send should be blocked
    assert service._can_send(webhook_url) is False


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_discord_send_alert_success(mock_post):
    """Test successful Discord alert sending."""
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    service = DiscordService()
    service.enabled = True

    success = await service.send_alert(
        webhook_url="https://discord.com/api/webhooks/test",
        line_name="Line 1",
        event_type="incident",
        severity="high",
        title="Service Interruption",
        description="Train stopped between stations"
    )

    assert success is True
    assert mock_post.called


@pytest.mark.asyncio
async def test_discord_send_alert_disabled():
    """Test that alerts are not sent when service is disabled."""
    service = DiscordService()
    service.enabled = False

    success = await service.send_alert(
        webhook_url="https://discord.com/api/webhooks/test",
        line_name="Line 1",
        event_type="incident",
        severity="high",
        title="Test",
    )

    assert success is False


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_discord_send_alert_respects_rate_limit(mock_post):
    """Test that rate limiting prevents rapid consecutive sends."""
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    service = DiscordService()
    service.enabled = True
    service.rate_limit_seconds = 5

    webhook_url = "https://discord.com/api/webhooks/test"

    # First send should succeed
    success1 = await service.send_alert(
        webhook_url=webhook_url,
        line_name="Line 1",
        event_type="incident",
        severity="high",
        title="Test 1",
    )

    # Second send should fail due to rate limit
    success2 = await service.send_alert(
        webhook_url=webhook_url,
        line_name="Line 1",
        event_type="incident",
        severity="high",
        title="Test 2",
    )

    assert success1 is True
    assert success2 is False
    assert mock_post.call_count == 1  # Only called once
