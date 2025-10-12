"""Database models for orchestrated live data snapshots and worker telemetry."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from .base import Base


class LiveSnapshot(Base):
    """Latest live snapshot payload produced by background workers."""

    __tablename__ = "live_snapshots"
    __table_args__ = (
        UniqueConstraint("network", "line", name="uq_live_snapshot_network_line"),
    )

    id = Column(Integer, primary_key=True, index=True)
    network = Column(String(32), nullable=False, index=True)
    line = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="ok")
    payload = Column(JSON, nullable=True)
    context = Column(JSON, nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    scheduler_run_id = Column(String(64), nullable=True, index=True)
    error_message = Column(Text, nullable=True)


class TaskRun(Base):
    """History of fetch tasks emitted by the scheduler."""

    __tablename__ = "task_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), nullable=False, unique=True, index=True)
    network = Column(String(32), nullable=False, index=True)
    line = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending")
    worker_id = Column(String(64), nullable=True, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    context = Column(JSON, nullable=True)


class WorkerStatus(Base):
    """Tracks worker node heartbeats and metrics."""

    __tablename__ = "worker_status"

    worker_id = Column(String(64), primary_key=True)
    status = Column(String(32), nullable=False, default="idle")
    host = Column(String(128), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    metrics = Column(JSON, nullable=True)

    def update_metrics(self, payload: Dict[str, Any]) -> None:
        """Merge metrics payload into stored JSON."""
        data = dict(self.metrics or {})
        data.update(payload)
        self.metrics = data
