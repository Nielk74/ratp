"""Forecast prediction model for traffic and delay predictions."""

from sqlalchemy import String, Integer, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional

from backend.models.base import Base, TimestampMixin


class ForecastPrediction(Base, TimestampMixin):
    """Stores ML-based predictions for delays and congestion."""

    __tablename__ = "forecast_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    line_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    station_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    prediction_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    predicted_delay_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    predicted_congestion: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),  # 0.00 to 1.00
        nullable=True
    )

    confidence_score: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),  # 0.00 to 1.00
        nullable=True
    )

    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<ForecastPrediction(id={self.id}, line_id={self.line_id}, confidence={self.confidence_score})>"
