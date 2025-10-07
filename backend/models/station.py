"""Station models for RATP stations and line-station relationships."""

from sqlalchemy import String, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .line import Line


class Station(Base, TimestampMixin):
    """Represents a RATP station/stop."""

    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    station_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    line_stations: Mapped[List["LineStation"]] = relationship(
        "LineStation",
        back_populates="station",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Station(code={self.station_code}, name={self.station_name})>"


class LineStation(Base):
    """Association table linking lines and stations with additional metadata."""

    __tablename__ = "line_stations"

    line_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lines.id", ondelete="CASCADE"),
        primary_key=True
    )

    station_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        primary_key=True
    )

    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Order on the line

    # Relationships
    line: Mapped["Line"] = relationship("Line", back_populates="line_stations")
    station: Mapped["Station"] = relationship("Station", back_populates="line_stations")

    def __repr__(self) -> str:
        return f"<LineStation(line_id={self.line_id}, station_id={self.station_id}, position={self.position})>"
