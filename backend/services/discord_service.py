"""Discord webhook service for sending alerts."""

import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta

from backend.config import settings


class DiscordService:
    """Service for sending notifications to Discord via webhooks."""

    def __init__(self):
        self.enabled = settings.discord_webhook_enabled
        self.rate_limit_seconds = settings.discord_rate_limit_seconds
        self._last_sent: Dict[str, datetime] = {}

    def _can_send(self, webhook_url: str) -> bool:
        """Check if enough time has passed since last message to this webhook."""
        if webhook_url not in self._last_sent:
            return True

        elapsed = datetime.now() - self._last_sent[webhook_url]
        return elapsed.total_seconds() >= self.rate_limit_seconds

    async def send_alert(
        self,
        webhook_url: str,
        line_name: str,
        event_type: str,
        severity: str,
        title: str,
        description: Optional[str] = None
    ) -> bool:
        """
        Send alert to Discord webhook.

        Args:
            webhook_url: Discord webhook URL
            line_name: Name of the affected line
            event_type: Type of event (incident, maintenance, delay)
            severity: Severity level (low, medium, high, critical)
            title: Alert title
            description: Optional detailed description

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        if not self._can_send(webhook_url):
            return False

        # Color mapping for severity
        color_map = {
            "low": 0x00FF00,      # Green
            "medium": 0xFFFF00,   # Yellow
            "high": 0xFF8800,     # Orange
            "critical": 0xFF0000  # Red
        }

        embed = {
            "title": f"🚨 {line_name} - {title}",
            "description": description or "No additional details available.",
            "color": color_map.get(severity.lower(), 0x808080),
            "fields": [
                {"name": "Event Type", "value": event_type.capitalize(), "inline": True},
                {"name": "Severity", "value": severity.upper(), "inline": True},
            ],
            "footer": {"text": "RATP Live Tracker"},
            "timestamp": datetime.now().isoformat()
        }

        payload = {
            "embeds": [embed],
            "username": "RATP Alerts"
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()

                # Update last sent time
                self._last_sent[webhook_url] = datetime.now()
                return True

        except Exception as e:
            print(f"Failed to send Discord webhook: {e}")
            return False
