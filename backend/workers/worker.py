"""Kafka worker that processes fetch tasks and updates the database."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy import select

from ..config import settings as app_settings
from ..database import AsyncSessionLocal, init_db
from ..models import LiveSnapshot, TaskRun, WorkerStatus
from ..services.scrapers.line_snapshot import line_snapshot_service
from .settings import OrchestratorSettings

logger = logging.getLogger("worker")


@asynccontextmanager
async def db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class Worker:
    """Kafka consumer that executes fetch jobs."""

    def __init__(self) -> None:
        self.settings = OrchestratorSettings()
        self.worker_id = self.settings.worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.host = socket.gethostname()
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._control_consumer: Optional[AIOKafkaConsumer] = None
        self._running = True
        self._paused = asyncio.Event()
        self._paused.set()
        self._last_activity = time.time()

    async def _update_worker_status(self, status: str, metrics: Optional[Dict[str, Any]] = None) -> None:
        async with db_session() as session:
            stmt = select(WorkerStatus).where(WorkerStatus.worker_id == self.worker_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if record:
                record.status = status
                record.last_heartbeat = now
                if metrics:
                    record.update_metrics(metrics)
            else:
                record = WorkerStatus(
                    worker_id=self.worker_id,
                    status=status,
                    host=self.host,
                    started_at=now,
                    last_heartbeat=now,
                    metrics=metrics or {},
                )
                session.add(record)

    async def _emit_metrics(self, payload: Dict[str, Any]) -> None:
        if not self._producer:
            return
        enriched = {
            "type": "worker",
            "worker_id": self.worker_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        await self._producer.send_and_wait(self.settings.kafka_metrics_topic, enriched)

    async def _handle_control_message(self, message: Dict[str, Any]) -> None:
        command = (message.get("command") or "").upper()
        target = message.get("target")
        if target and target != self.worker_id and target != "all":
            return
        logger.info("Received control command %s", command)
        if command == "PAUSE":
            self._paused.clear()
            await self._update_worker_status("paused")
        elif command == "RESUME":
            self._paused.set()
            await self._update_worker_status("idle")
        elif command == "DRAIN":
            self._paused.clear()
            self._running = False
        elif command == "RELOAD_CONFIG":
            self.settings = OrchestratorSettings()
            await self._emit_metrics({"event": "config_reloaded"})

    async def _control_loop(self) -> None:
        consumer = AIOKafkaConsumer(
            self.settings.kafka_control_topic,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id=f"{self.worker_id}-control",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            enable_auto_commit=True,
        )
        self._control_consumer = consumer
        await consumer.start()
        try:
            async for msg in consumer:
                await self._handle_control_message(msg.value)
        except asyncio.CancelledError:
            pass
        finally:
            await consumer.stop()

    async def _process_job(self, job: Dict[str, Any]) -> None:
        job_id = job.get("job_id")
        network = job.get("network")
        line = job.get("line")
        if not job_id or not network or not line:
            logger.warning("Skipping malformed job: %s", job)
            return

        started_at = datetime.now(timezone.utc)
        async with db_session() as session:
            stmt = select(TaskRun).where(TaskRun.job_id == job_id)
            result = await session.execute(stmt)
            task_run = result.scalar_one_or_none()
            if task_run is None:
                task_run = TaskRun(
                    job_id=job_id,
                    network=network,
                    line=line,
                    status="running",
                    scheduled_at=started_at,
                    context=job.get("metadata") or {},
                )
                session.add(task_run)
            task_run.status = "running"
            task_run.worker_id = self.worker_id
            task_run.started_at = started_at

        status = "success"
        error_message = None
        snapshot_payload: Optional[Dict[str, Any]] = None

        try:
            snapshot_payload = await asyncio.to_thread(
                line_snapshot_service.get_snapshot,
                network,
                line,
                refresh=True,
                station_limit=None,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to fetch snapshot for %s %s", network, line)
            status = "error"
            error_message = str(exc)
        finally:
            await self._store_results(job, snapshot_payload, status, error_message, started_at)

    async def _store_results(
        self,
        job: Dict[str, Any],
        snapshot_payload: Optional[Dict[str, Any]],
        status: str,
        error_message: Optional[str],
        started_at: datetime,
    ) -> None:
        network = job["network"]
        line = job["line"]
        finished_at = datetime.now(timezone.utc)
        async with db_session() as session:
            stmt = select(TaskRun).where(TaskRun.job_id == job["job_id"])
            result = await session.execute(stmt)
            task_run = result.scalar_one_or_none()
            if task_run:
                task_run.status = status
                task_run.finished_at = finished_at
                task_run.error_message = error_message

            stmt = select(LiveSnapshot).where(
                LiveSnapshot.network == network,
                LiveSnapshot.line == line,
            )
            result = await session.execute(stmt)
            snapshot = result.scalar_one_or_none()
            if snapshot:
                snapshot.status = status
                snapshot.fetched_at = finished_at
                snapshot.payload = snapshot_payload
                snapshot.context = job.get("metadata") or {}
                snapshot.error_message = error_message
                snapshot.scheduler_run_id = job.get("run_id")
            else:
                snapshot = LiveSnapshot(
                    network=network,
                    line=line,
                    status=status,
                    fetched_at=finished_at,
                    payload=snapshot_payload,
                    context=job.get("metadata") or {},
                    error_message=error_message,
                    scheduler_run_id=job.get("run_id"),
                )
                session.add(snapshot)

        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        await self._emit_metrics(
            {
                "event": "task_completed",
                "job_id": job["job_id"],
                "network": network,
                "line": line,
                "status": status,
                "duration_ms": duration_ms,
            }
        )
        self._last_activity = time.time()

    async def _heartbeat_loop(self) -> None:
        while self._running:
            idle = (time.time() - self._last_activity) > self.settings.worker_heartbeat_interval * 2
            status = "idle" if idle and self._paused.is_set() else ("paused" if not self._paused.is_set() else "running")
            await self._update_worker_status(status, {"idle": idle})
            await self._emit_metrics({"event": "heartbeat", "status": status})
            await asyncio.sleep(self.settings.worker_heartbeat_interval)

    async def run(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        self._consumer = AIOKafkaConsumer(
            self.settings.kafka_fetch_topic,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id="live-data-workers",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            enable_auto_commit=True,
            max_poll_records=self.settings.worker_batch_size,
        )

        await self._update_worker_status("starting")
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        control_task = asyncio.create_task(self._control_loop())

        await self._consumer.start()
        logger.info("Worker %s connected to Kafka", self.worker_id)

        try:
            async for msg in self._consumer:
                await self._paused.wait()
                await self._process_job(msg.value)
                if not self._running:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            self._paused.set()
            control_task.cancel()
            heartbeat_task.cancel()
            await asyncio.gather(control_task, heartbeat_task, return_exceptions=True)
            await self._consumer.stop()
            await self._producer.stop()
            await self._update_worker_status("stopped")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [worker] %(message)s")
    worker = Worker()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("Worker interrupted, shutting down.")


if __name__ == "__main__":
    main()
