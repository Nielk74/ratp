"""API routes for Discord webhook management."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db_session
from backend.services.discord_service import DiscordService

router = APIRouter()
discord_service = DiscordService()


class WebhookCreate(BaseModel):
    """Schema for creating a webhook subscription."""
    webhook_url: HttpUrl
    line_code: str
    severity_filter: Optional[List[str]] = None


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    id: int
    webhook_url: str
    line_code: str
    is_active: bool


@router.post("/", response_model=dict)
async def create_webhook_subscription(
    webhook: WebhookCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new Discord webhook subscription for line alerts.

    The webhook will receive notifications when traffic events occur
    on the specified line.
    """
    try:
        # TODO: Implement database storage
        # For now, just validate the webhook
        return {
            "message": "Webhook subscription created successfully",
            "webhook_url": str(webhook.webhook_url),
            "line_code": webhook.line_code,
            "severity_filter": webhook.severity_filter
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=dict)
async def list_webhook_subscriptions(
    db: AsyncSession = Depends(get_db_session)
):
    """List all active webhook subscriptions."""
    try:
        # TODO: Implement database query
        return {"subscriptions": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{subscription_id}")
async def delete_webhook_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a webhook subscription."""
    try:
        # TODO: Implement database deletion
        return {"message": f"Subscription {subscription_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_webhook(webhook_url: HttpUrl):
    """Send a test notification to a Discord webhook."""
    try:
        success = await discord_service.send_alert(
            webhook_url=str(webhook_url),
            line_name="Test Line",
            event_type="test",
            severity="low",
            title="Test Alert",
            description="This is a test notification from RATP Live Tracker."
        )

        if success:
            return {"message": "Test notification sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test notification")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
