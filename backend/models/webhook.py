"""Webhook subscription model for Discord notifications."""

from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.line import Line


class WebhookSubscription(Base, TimestampMixin):
    """Discord webhook subscription for line alerts."""

    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    discord_webhook_url: Mapped[str] = mapped_column(Text, nullable=False)

    line_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # SQLite doesn't support ARRAY, so we'll store as JSON string
    severity_filter: Mapped[Optional[str]] = mapped_column(
        Text,  # Will store JSON array as string
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    last_triggered: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<WebhookSubscription(id={self.id}, line_id={self.line_id}, active={self.is_active})>"
