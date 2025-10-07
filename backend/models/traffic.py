"""Traffic event model for incidents, delays, and maintenance."""

from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .line import Line


class TrafficEvent(Base, TimestampMixin):
    """Represents a traffic event (incident, maintenance, delay)."""

    __tablename__ = "traffic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    line_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    line: Mapped["Line"] = relationship("Line", back_populates="traffic_events")

    def __repr__(self) -> str:
        return f"<TrafficEvent(id={self.id}, type={self.event_type}, severity={self.severity}, active={self.is_active})>"
