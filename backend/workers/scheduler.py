"""Asynchronous scheduler that enqueues fetch tasks into Kafka."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Iterable, List, Tuple, Optional

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from sqlalchemy import select, update

from ..config import settings as app_settings
from ..database import AsyncSessionLocal, init_db
from ..models import TaskRun
from ..services.ratp_client import RatpClient
from .settings import OrchestratorSettings

logger = logging.getLogger("scheduler")


def _resolve_targets(orchestrator_settings: OrchestratorSettings) -> List[Tuple[str, str]]:
    explicit = orchestrator_settings.scheduler_targets()
    if explicit:
        return explicit

    client = RatpClient()
    targets: List[Tuple[str, str]] = []
    for entry in client._line_catalog:  # pylint: disable=protected-access
        network = entry.get("type")
        code = entry.get("code")
        if not network or not code:
            continue
        if network not in {"metro", "rer", "tram", "transilien"}:
            continue
        targets.append((network, str(code)))
    return targets


async def _persist_task(session, job: dict) -> None:
    stmt = select(TaskRun).where(TaskRun.job_id == job["job_id"])
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if record:
        record.status = "queued"
        record.scheduled_at = now
        record.context = job.get("metadata") or {}
    else:
        record = TaskRun(
            job_id=job["job_id"],
            network=job["network"],
            line=job["line"],
            status="queued",
            scheduled_at=now,
            context=job.get("metadata") or {},
        )
        session.add(record)


async def _mark_stale_tasks(session) -> None:
    """Set long-running tasks back to queued so they are retried."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=app_settings.task_timeout_seconds * 2)
    stmt = update(TaskRun).where(TaskRun.status == "running").where(TaskRun.started_at < cutoff).values(
        status="queued",
        started_at=None,
        finished_at=None,
    )
    try:
        await session.execute(stmt)
    except Exception:  # pylint: disable=broad-except
        pass


async def scheduler_loop() -> None:
    orchestrator_settings = OrchestratorSettings()
    targets = _resolve_targets(orchestrator_settings)
    if not targets:
        logger.warning("Scheduler has no targets configured; exiting.")
        return

    async def _start_producer() -> AIOKafkaProducer:
        while True:
            try:
                producer = AIOKafkaProducer(
                    bootstrap_servers=orchestrator_settings.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    linger_ms=5,
                )
                await producer.start()
                return producer
            except KafkaConnectionError as exc:
                logger.warning("Kafka not ready for scheduler producer: %s", exc)
                await asyncio.sleep(3)

    async def _control_loop(trigger_event: asyncio.Event) -> None:
        consumer: Optional[AIOKafkaConsumer] = None
        while consumer is None:
            try:
                consumer = AIOKafkaConsumer(
                    orchestrator_settings.kafka_control_topic,
                    bootstrap_servers=orchestrator_settings.kafka_bootstrap_servers,
                    group_id="scheduler-control",
                    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                    enable_auto_commit=True,
                    auto_offset_reset="earliest",
                )
                await consumer.start()
            except KafkaConnectionError as exc:
                logger.warning("Kafka not ready for scheduler control consumer: %s", exc)
                consumer = None
                await asyncio.sleep(3)

        try:
            async for msg in consumer:
                command = (msg.value.get("command") or "").upper()
                target = msg.value.get("target")
                if target not in {None, "scheduler", "all"}:
                    continue
                if command == "SCHEDULE_NOW":
                    trigger_event.set()
        except asyncio.CancelledError:
            pass
        finally:
            await consumer.stop()

    producer = await _start_producer()
    logger.info("Scheduler started with %s targets", len(targets))
    host = socket.gethostname()

    trigger_event = asyncio.Event()
    trigger_event.set()
    control_task = asyncio.create_task(_control_loop(trigger_event))

    try:
        while True:
            await trigger_event.wait()
            trigger_event.clear()
            started = time.perf_counter()
            run_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as session:
                await _mark_stale_tasks(session)
                for index, (network, line) in enumerate(targets):
                    job_id = f"{run_id}:{network}:{line}:{index}"
                    payload = {
                        "job_id": job_id,
                        "run_id": run_id,
                        "network": network,
                        "line": line,
                        "scheduled_at": now.isoformat(),
                        "priority": 1,
                        "metadata": {
                            "scheduler_host": host,
                        },
                    }
                    await producer.send_and_wait(orchestrator_settings.kafka_fetch_topic, payload)
                    await _persist_task(session, payload)
                await session.commit()

            metrics_payload = {
                "type": "scheduler",
                "run_id": run_id,
                "timestamp": now.isoformat(),
                "host": host,
                "targets": len(targets),
                "duration_ms": int((time.perf_counter() - started) * 1000),
            }
            await producer.send_and_wait(orchestrator_settings.kafka_metrics_topic, metrics_payload)
            logger.info("Enqueued %s tasks (run_id=%s)", len(targets), run_id)
            try:
                await asyncio.wait_for(trigger_event.wait(), timeout=orchestrator_settings.scheduler_interval_seconds)
            except asyncio.TimeoutError:
                trigger_event.set()
    finally:
        control_task.cancel()
        await asyncio.gather(control_task, return_exceptions=True)
        await producer.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [scheduler] %(message)s")
    try:
        asyncio.run(scheduler_loop())
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted, shutting down.")


if __name__ == "__main__":
    main()
