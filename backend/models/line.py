"""Line model for RATP transport lines."""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.station import LineStation
    from backend.models.traffic import TrafficEvent


class Line(Base, TimestampMixin):
    """Represents a RATP transport line (metro, RER, tram, bus)."""

    __tablename__ = "lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    line_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    line_name: Mapped[str] = mapped_column(String(100), nullable=False)
    transport_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(7), nullable=True)  # Hex color

    # Relationships
    line_stations: Mapped[List["LineStation"]] = relationship(
        "LineStation",
        back_populates="line",
        cascade="all, delete-orphan"
    )

    traffic_events: Mapped[List["TrafficEvent"]] = relationship(
        "TrafficEvent",
        back_populates="line",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Line(code={self.line_code}, name={self.line_name}, type={self.transport_type})>"
