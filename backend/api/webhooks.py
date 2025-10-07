"""API routes for Discord webhook management."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_session
from ..models.line import Line
from ..models.webhook import WebhookSubscription
from ..services.discord_service import DiscordService
from ..services.line_service import LineNotFoundError, LineService
from ..services.ratp_client import RatpClient

router = APIRouter()
discord_service = DiscordService()
ratp_client = RatpClient()


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
    line_name: Optional[str] = None
    is_active: bool
    severity_filter: Optional[List[str]] = None


def _serialize_subscription(
    subscription: WebhookSubscription,
    line: Optional[Line]
) -> WebhookResponse:
    """Convert ORM objects into response schema."""
    severity = (
        json.loads(subscription.severity_filter)
        if subscription.severity_filter
        else None
    )
    return WebhookResponse(
        id=subscription.id,
        webhook_url=subscription.discord_webhook_url,
        line_code=line.line_code if line else "",
        line_name=line.line_name if line else None,
        is_active=subscription.is_active,
        severity_filter=severity,
    )


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
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
        line_service = LineService(db, ratp_client)
        line = await line_service.get_or_create_line(webhook.line_code)

        severity_payload = (
            json.dumps(webhook.severity_filter)
            if webhook.severity_filter
            else None
        )

        subscription = WebhookSubscription(
            discord_webhook_url=str(webhook.webhook_url),
            line_id=line.id,
            severity_filter=severity_payload,
            is_active=True,
        )
        db.add(subscription)
        await db.flush()
        await db.refresh(subscription)
        await db.refresh(subscription, attribute_names=["line"])

        return _serialize_subscription(subscription, subscription.line)

    except LineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=dict)
async def list_webhook_subscriptions(
    db: AsyncSession = Depends(get_db_session)
):
    """List all active webhook subscriptions."""
    try:
        result = await db.execute(
            select(WebhookSubscription, Line)
            .join(Line, WebhookSubscription.line_id == Line.id)
            .where(WebhookSubscription.is_active.is_(True))
        )
        subscriptions = [
            _serialize_subscription(subscription, line).model_dump()
            for subscription, line in result.all()
        ]
        return {"subscriptions": subscriptions, "count": len(subscriptions)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{subscription_id}")
async def delete_webhook_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a webhook subscription."""
    try:
        subscription = await db.get(WebhookSubscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=f"Subscription {subscription_id} not found"
            )

        await db.delete(subscription)
        await db.flush()

        return {"message": f"Subscription {subscription_id} deleted"}
    except HTTPException:
        raise
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
