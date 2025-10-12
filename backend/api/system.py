"""System orchestration endpoints for monitoring and control."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db_session
from ..models import TaskRun, WorkerStatus

router = APIRouter()


async def _require_system_token(x_api_key: Optional[str] = Header(default=None)) -> None:
    token = settings.system_api_token.strip()
    if not token:
        return
    if x_api_key != token:
        raise HTTPException(status_code=401, detail="Invalid API key")


async def _send_control_command(payload: Dict[str, Any]) -> None:
    from aiokafka import AIOKafkaProducer

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        await producer.send_and_wait(settings.kafka_control_topic, payload)
    finally:
        await producer.stop()


@router.get("/workers", dependencies=[Depends(_require_system_token)])
async def list_workers(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    result = await db.execute(select(WorkerStatus).order_by(WorkerStatus.worker_id))
    workers = [
        {
            "worker_id": row.worker_id,
            "status": row.status,
            "host": row.host,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "last_heartbeat": row.last_heartbeat.isoformat() if row.last_heartbeat else None,
            "metrics": row.metrics or {},
        }
        for row in result.scalars()
    ]
    return {"workers": workers}


@router.get("/tasks/recent", dependencies=[Depends(_require_system_token)])
async def recent_task_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    stmt = (
        select(TaskRun)
        .order_by(desc(TaskRun.finished_at), desc(TaskRun.started_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    runs = []
    for item in result.scalars():
        runs.append(
            {
                "job_id": item.job_id,
                "network": item.network,
                "line": item.line,
                "status": item.status,
                "worker_id": item.worker_id,
                "scheduled_at": item.scheduled_at.isoformat() if item.scheduled_at else None,
                "started_at": item.started_at.isoformat() if item.started_at else None,
                "finished_at": item.finished_at.isoformat() if item.finished_at else None,
                "error_message": item.error_message,
            }
        )
    return {"items": runs}


@router.get("/queue", dependencies=[Depends(_require_system_token)])
async def queue_metrics(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    pending_stmt = select(func.count()).select_from(TaskRun).where(TaskRun.status.in_(["queued", "pending", "running"]))
    total_stmt = select(func.count()).select_from(TaskRun)
    last_run_stmt = select(TaskRun.scheduled_at).order_by(desc(TaskRun.scheduled_at)).limit(1)

    pending = (await db.execute(pending_stmt)).scalar() or 0
    total = (await db.execute(total_stmt)).scalar() or 0
    last_run = (await db.execute(last_run_stmt)).scalar_one_or_none()

    return {
        "pending": pending,
        "total": total,
        "last_scheduled_at": last_run.isoformat() if last_run else None,
    }


@router.post("/workers/{worker_id}/command", dependencies=[Depends(_require_system_token)])
async def send_worker_command(worker_id: str, command: str) -> Dict[str, Any]:
    payload = {
        "command": command.upper(),
        "target": worker_id,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    await _send_control_command(payload)
    return {"status": "queued", "payload": payload}


@router.post("/scheduler/run", dependencies=[Depends(_require_system_token)])
async def trigger_scheduler_run() -> Dict[str, Any]:
    payload = {
        "command": "SCHEDULE_NOW",
        "target": "scheduler",
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    await _send_control_command(payload)
    return {"status": "queued", "payload": payload}
