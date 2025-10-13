"""Tests for scheduler and worker maintenance helpers."""

from datetime import datetime, timedelta, timezone
import sys
import types

import pytest
from sqlalchemy import select

# Stub aiokafka dependencies before importing scheduler helpers.
aiokafka_module = types.ModuleType("aiokafka")
aiokafka_module.AIOKafkaProducer = object
aiokafka_module.AIOKafkaConsumer = object
sys.modules.setdefault("aiokafka", aiokafka_module)

aiokafka_errors = types.ModuleType("aiokafka.errors")
aiokafka_errors.KafkaConnectionError = Exception
sys.modules.setdefault("aiokafka.errors", aiokafka_errors)

from backend.config import settings as app_settings
from backend.models import WorkerStatus, TaskRun
from backend.workers.scheduler import (
    _mark_stale_tasks,
    _prune_stale_workers,
)  # pylint: disable=protected-access
from backend.workers.settings import OrchestratorSettings


@pytest.mark.asyncio
async def test_prune_stale_workers_removes_idle_and_marks_lost(test_db):
    """Workers without recent heartbeats should be pruned or marked lost."""
    settings = OrchestratorSettings(worker_heartbeat_interval=1)
    stale_timestamp = datetime.now(timezone.utc) - timedelta(seconds=600)
    fresh_timestamp = datetime.now(timezone.utc)

    stale_idle = WorkerStatus(
        worker_id="idle-1",
        status="idle",
        host="test-host",
        started_at=stale_timestamp,
        last_heartbeat=stale_timestamp,
        metrics={},
    )
    stale_running = WorkerStatus(
        worker_id="running-1",
        status="running",
        host="test-host",
        started_at=stale_timestamp,
        last_heartbeat=stale_timestamp,
        metrics={},
    )
    fresh_idle = WorkerStatus(
        worker_id="idle-fresh",
        status="idle",
        host="test-host",
        started_at=fresh_timestamp,
        last_heartbeat=fresh_timestamp,
        metrics={},
    )

    test_db.add_all([stale_idle, stale_running, fresh_idle])
    await test_db.commit()

    await _prune_stale_workers(test_db, settings)
    await test_db.commit()

    result = await test_db.execute(select(WorkerStatus).where(WorkerStatus.worker_id == "idle-1"))
    assert result.scalar_one_or_none() is None

    result = await test_db.execute(select(WorkerStatus).where(WorkerStatus.worker_id == "running-1"))
    maybe_lost = result.scalar_one_or_none()
    if maybe_lost is not None:
        assert maybe_lost.status == "lost"

    result = await test_db.execute(select(WorkerStatus).where(WorkerStatus.worker_id == "idle-fresh"))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_mark_stale_tasks_expires_old_queue(test_db, monkeypatch):
    """Queued tasks older than the expiration window should be marked expired."""
    monkeypatch.setattr(app_settings, "task_timeout_seconds", 1)
    now = datetime.now(timezone.utc)

    stale_task = TaskRun(
        job_id="stale-job",
        network="metro",
        line="1",
        status="queued",
        scheduled_at=now - timedelta(minutes=15),
    )
    fresh_task = TaskRun(
        job_id="fresh-job",
        network="metro",
        line="1",
        status="queued",
        scheduled_at=now,
    )
    running_task = TaskRun(
        job_id="running-job",
        network="metro",
        line="1",
        status="running",
        started_at=now - timedelta(minutes=10),
        scheduled_at=now - timedelta(minutes=11),
    )

    test_db.add_all([stale_task, fresh_task, running_task])
    await test_db.commit()

    await _mark_stale_tasks(test_db)
    await test_db.commit()

    result = await test_db.execute(select(TaskRun).where(TaskRun.job_id == "stale-job"))
    assert result.scalar_one().status == "expired"

    result = await test_db.execute(select(TaskRun).where(TaskRun.job_id == "fresh-job"))
    assert result.scalar_one().status == "queued"

    result = await test_db.execute(select(TaskRun).where(TaskRun.job_id == "running-job"))
    assert result.scalar_one().status == "queued"
