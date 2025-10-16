"""Database model for centralized service logs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text

from .base import Base


class SystemLog(Base):
    """Structured log entry captured from any service in the stack."""

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    service = Column(String(64), nullable=False, index=True)
    level = Column(String(32), nullable=False, index=True)
    logger_name = Column(String(128), nullable=True, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    extra = Column(JSON, nullable=True)
    traceback = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the log entry to a dictionary."""
        return {
            "id": self.id,
            "service": self.service,
            "level": self.level,
            "logger_name": self.logger_name,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extra": self.extra or {},
            "traceback": self.traceback,
        }
