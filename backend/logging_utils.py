"""Utilities for configuring centralized structured logging."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import settings
from .database import AsyncSessionLocal
from .models.system_log import SystemLog


_LOG_RECORD_RESERVED_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


class _CentralLogHandler(logging.Handler):
    """Logging handler that forwards records into an async queue."""

    def __init__(self, manager: "CentralizedLogManager") -> None:
        super().__init__(manager.level)
        self.manager = manager

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401 - standard emit signature
        if record.levelno < self.manager.level:
            return
        payload = self.manager.serialize_record(record)
        try:
            self.manager.queue.put_nowait(payload)
        except asyncio.QueueFull:
            self.manager.report_queue_full()


class CentralizedLogManager:
    """Background task that persists log records to the database."""

    def __init__(self, service_name: str, level: int, queue_size: int) -> None:
        self.service_name = service_name
        self.level = level
        self.queue: asyncio.Queue[Optional[Dict[str, Any]]] = asyncio.Queue(maxsize=queue_size)
        self._task: Optional[asyncio.Task[None]] = None
        self._queue_warning_emitted = False

    def create_handler(self) -> logging.Handler:
        """Return a handler bound to this manager."""
        return _CentralLogHandler(self)

    async def start(self) -> None:
        """Start the background consumer if not already running."""
        if self._task is None:
            self._task = asyncio.create_task(self._worker(), name=f"log-writer-{self.service_name}")

    async def stop(self) -> None:
        """Stop the background consumer, flushing any pending records."""
        if self._task is None:
            return
        await self.queue.put(None)
        await self._task
        self._task = None
        self._queue_warning_emitted = False

    async def _worker(self) -> None:
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            try:
                async with AsyncSessionLocal() as session:
                    session.add(SystemLog(**item))
                    await session.commit()
            except Exception:  # pragma: no cover - defensive path
                # Avoid recursive logging; write to stderr.
                traceback.print_exc()
            finally:
                self.queue.task_done()

    def serialize_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Convert a log record into the payload stored in the database."""
        created_at = datetime.fromtimestamp(record.created, tz=timezone.utc)
        payload: Dict[str, Any] = {
            "service": self.service_name,
            "level": record.levelname,
            "logger_name": record.name,
            "message": record.getMessage(),
            "created_at": created_at,
        }

        if record.exc_info:
            payload["traceback"] = "".join(traceback.format_exception(*record.exc_info))
        elif record.exc_text:
            payload["traceback"] = record.exc_text

        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _LOG_RECORD_RESERVED_KEYS and not key.startswith("_")
        }
        if extra:
            sanitized: Dict[str, Any] = {}
            for key, value in extra.items():
                try:
                    json.dumps(value)
                    sanitized[key] = value
                except (TypeError, ValueError):
                    sanitized[key] = repr(value)
            payload["extra"] = sanitized

        return payload

    def report_queue_full(self) -> None:
        """Emit a single warning to stderr if the queue overflows."""
        if self._queue_warning_emitted:
            return
        self._queue_warning_emitted = True
        print(
            f"Centralized logging queue for service '{self.service_name}' is full; dropping log entries.",
            file=sys.stderr,
        )


_manager_instance: Optional[CentralizedLogManager] = None


async def enable_centralized_logging(service_name: str) -> Optional[CentralizedLogManager]:
    """Configure Python logging to forward records into the central store."""
    global _manager_instance

    if not settings.centralized_logging_enabled:
        return None

    if _manager_instance is not None:
        # Already configured for this process.
        return _manager_instance

    level_name = settings.centralized_log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    queue_size = max(1, settings.centralized_log_queue_size)

    manager = CentralizedLogManager(service_name=service_name, level=level, queue_size=queue_size)

    handler = manager.create_handler()
    handler.setLevel(level)

    root_logger = logging.getLogger()
    root_logger.setLevel(min(root_logger.level or level, level))
    root_logger.addHandler(handler)

    _manager_instance = manager
    await manager.start()
    return manager


async def disable_centralized_logging() -> None:
    """Tear down the centralized logging manager if it exists."""
    global _manager_instance

    if _manager_instance is None:
        return
    await _manager_instance.stop()
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if isinstance(handler, _CentralLogHandler) and handler.manager is _manager_instance:
            root_logger.removeHandler(handler)
    _manager_instance = None
