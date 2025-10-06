"""Schedule history model for tracking actual vs scheduled times."""

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.line import Line
    from models.station import Station


class ScheduleHistory(Base, TimestampMixin):
    """Records historical schedule data for delay analysis."""

    __tablename__ = "schedules_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    station_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    line_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    scheduled_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    actual_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    delay_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    direction: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        return f"<ScheduleHistory(id={self.id}, station_id={self.station_id}, delay={self.delay_seconds}s)>"
