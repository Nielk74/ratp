"""System orchestration endpoints for monitoring and control."""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db_session
from ..models import LiveSnapshot, TaskRun, WorkerStatus

router = APIRouter()
logger = logging.getLogger("system")


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


class WorkerScaleRequest(BaseModel):
    """Request payload for scaling the worker pool."""

    count: int | None = Field(default=None, ge=0, description="Absolute number of worker processes/containers.")
    delta: int | None = Field(default=None, description="Relative change in worker count (positive or negative).")

    @model_validator(mode="after")
    def _ensure_value(self) -> "WorkerScaleRequest":  # type: ignore[override]
        if self.count is None and self.delta is None:
            raise ValueError("Either count or delta must be provided")
        return self


async def _current_worker_count(prefix: str) -> int:
    process = await asyncio.create_subprocess_exec(
        "docker",
        "ps",
        "--filter",
        f"name={prefix}",
        "--format",
        "{{.Names}}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        logger.warning(
            "Failed to inspect current worker containers (rc=%s, stderr=%s)",
            process.returncode,
            stderr.decode().strip(),
        )
        return 0
    names = [line.strip() for line in stdout.decode().splitlines() if line.strip()]
    return len(names)


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


@router.post("/workers/scale", dependencies=[Depends(_require_system_token)])
async def scale_workers(request: WorkerScaleRequest) -> Dict[str, Any]:
    command_template = settings.worker_scale_command
    if not command_template:
        raise HTTPException(status_code=501, detail="Worker scaling command not configured")

    if request.count is not None:
        target = request.count
    else:
        active_count = await _current_worker_count(settings.worker_container_prefix)
        target = max(0, active_count + (request.delta or 0))

    try:
        command_parts = [segment.format(count=target) for segment in shlex.split(command_template)]
    except KeyError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid worker scaling command template: missing key {exc}") from exc

    process = await asyncio.create_subprocess_exec(
        *command_parts,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=settings.worker_scale_workdir,
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    stdout_text = stdout_bytes.decode("utf-8", errors="ignore").strip()
    stderr_text = stderr_bytes.decode("utf-8", errors="ignore").strip()
    if process.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Worker scaling command failed",
                "exit_code": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
            },
        )

    return {
        "status": "ok",
        "count": target,
        "stdout": stdout_text,
        "stderr": stderr_text,
    }


@router.post("/scheduler/run", dependencies=[Depends(_require_system_token)])
async def trigger_scheduler_run() -> Dict[str, Any]:
    payload = {
        "command": "SCHEDULE_NOW",
        "target": "scheduler",
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    await _send_control_command(payload)
    return {"status": "queued", "payload": payload}


@router.get("/db/summary", dependencies=[Depends(_require_system_token)])
async def database_summary(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    task_stmt = select(TaskRun.status, func.count()).group_by(TaskRun.status)
    worker_stmt = select(WorkerStatus.status, func.count()).group_by(WorkerStatus.status)

    task_counts: Dict[str, int] = {}
    for status, count in (await db.execute(task_stmt)).all():
        task_counts[status or "unknown"] = count or 0

    worker_counts: Dict[str, int] = {}
    for status, count in (await db.execute(worker_stmt)).all():
        worker_counts[status or "unknown"] = count or 0

    total_workers = sum(worker_counts.values())
    active_workers = sum(count for status, count in worker_counts.items() if status not in {"lost", "stopped"})

    return {
        "task_counts": task_counts,
        "worker_counts": worker_counts,
        "total_workers": total_workers,
        "active_workers": active_workers,
    }


@router.get("/db/snapshots", dependencies=[Depends(_require_system_token)])
async def database_snapshots(
    limit: int = Query(20, ge=1, le=100),
    network: Optional[str] = Query(default=None, description="Filter by network code (e.g. metro, rer)."),
    line: Optional[str] = Query(default=None, description="Filter by line code."),
    include_payload: bool = Query(default=False, description="Whether to include full payload JSON in the response."),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    stmt = select(LiveSnapshot).order_by(desc(LiveSnapshot.fetched_at))

    if network:
        stmt = stmt.where(LiveSnapshot.network == network.lower())
    if line:
        stmt = stmt.where(LiveSnapshot.line == line.upper())

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)

    items: List[Dict[str, Any]] = []
    for record in result.scalars():
        payload = record.payload if include_payload else None
        station_count = None
        if isinstance(record.payload, dict):
            stations = record.payload.get("stations")
            if isinstance(stations, list):
                station_count = len(stations)

        items.append(
            {
                "id": record.id,
                "network": record.network,
                "line": record.line,
                "status": record.status,
                "fetched_at": record.fetched_at.isoformat() if record.fetched_at else None,
                "scheduler_run_id": record.scheduler_run_id,
                "error_message": record.error_message,
                "context": record.context or {},
                "station_count": station_count,
                "payload": payload,
            }
        )

    return {"items": items}
