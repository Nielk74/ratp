"""Shared settings for scheduler and worker processes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple


def _parse_targets(raw: str) -> List[Tuple[str, str]]:
    targets: List[Tuple[str, str]] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            # Assume metro when network not provided
            targets.append(("metro", chunk.upper()))
            continue
        network, line = chunk.split(":", 1)
        targets.append((network.strip().lower(), line.strip().upper()))
    return targets


@dataclass
class OrchestratorSettings:
    """Configuration for scheduler and worker processes."""

    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_fetch_topic: str = os.getenv("KAFKA_FETCH_TOPIC", "fetch.tasks")
    kafka_control_topic: str = os.getenv("KAFKA_CONTROL_TOPIC", "control.commands")
    kafka_metrics_topic: str = os.getenv("KAFKA_METRICS_TOPIC", "worker.metrics")

    scheduler_interval_seconds: int = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "120"))
    scheduler_lines_raw: str = os.getenv("SCHEDULER_LINES", "metro:1,rer:A")
    scheduler_max_backlog: int = int(os.getenv("SCHEDULER_MAX_BACKLOG", "64"))
    scheduler_batch_size: int = int(os.getenv("SCHEDULER_BATCH_SIZE", "25"))

    worker_id: str = os.getenv("WORKER_ID", "")
    worker_heartbeat_interval: int = int(os.getenv("WORKER_HEARTBEAT_INTERVAL", "10"))
    worker_batch_size: int = int(os.getenv("WORKER_BATCH_SIZE", "1"))
    worker_max_concurrency: int = int(os.getenv("WORKER_MAX_CONCURRENCY", "2"))

    task_timeout_seconds: int = int(os.getenv("TASK_TIMEOUT_SECONDS", "60"))

    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ratp.db")

    def scheduler_targets(self) -> List[Tuple[str, str]]:
        """Return parsed scheduler targets."""
        return _parse_targets(self.scheduler_lines_raw)
