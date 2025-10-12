## Live Data Orchestration Architecture

### Goals
- Continuously collect live departures/traffic across networks without blocking API requests.
- Scale horizontally with multiple fetcher nodes coordinated through a durable queue.
- Offer operational visibility and controls (start/stop workers, inspect lag, retry failed tasks).
- Remain deployable locally via Docker Compose but ready for production (Kubernetes, Nomad, etc.).

### High-Level Topology

```
                         ┌──────────────┐
                         │ Scheduler    │
                         │ (FastAPI CLI │
                         │  or service) │
                         └──────┬───────┘
                                │ produce fetch jobs (Kafka topic: fetch.tasks)
                                ▼
                    ┌──────────────────────────┐
                    │ Apache Kafka (w/ ZK)     │
                    │  - fetch.tasks topic     │
                    │  - control.commands      │
                    │  - worker.metrics        │
                    └────────┬─────────────────┘
                             │ consume tasks
                             ▼
     ┌────────────────────────────────────────────────┐
     │ Worker pool (Docker service, N replicas)       │
     │  - consumes fetch.tasks                        │
     │  - invokes existing scrapers (HTTP, VMTR, etc) │
     │  - writes normalized payloads & run metadata   │
     │    to Postgres/SQLite → tables live_snapshots, │
     │    worker_heartbeats, task_runs                │
     │  - emits metrics to worker.metrics topic       │
     │  - listens to control.commands for pause/resume│
     └────────────────────┬───────────────────────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ FastAPI Backend    │
                │  - REST API        │
                │  - System health   │
                │    endpoints       │
                │  - Admin actions   │
                └────────┬───────────┘
                         │
                         ▼
                ┌────────────────────┐
                │ Next.js Frontend   │
                │  - Live map        │
                │  - New “Orchestrator│
                │    Dashboard” page │
                │    (queue lag,     │
                │     worker status, │
                │     manual control)│
                └────────────────────┘
```

### Scheduler
- Periodically (cron-like) scans configured networks/lines.
- Publishes tasks with payload `{ job_id, priority, network, line, station_hint, task_type }`.
- Tracks last run timestamps to avoid bursts.
- Exposes metrics (lag, queue depth) via REST to backend or by writing to `worker.metrics`.

Implementation:
- Python service using `aiokafka.AIOKafkaProducer`.
- Configurable via env (`SCHEDULER_INTERVAL_SECONDS`, `SCHEDULER_LINES`, etc.).
- Runs as long-lived container (`scheduler` service in compose).

### Worker
- Python async consumer using `aiokafka.AIOKafkaConsumer`.
- Pools tasks, deduplicates by `job_id`.
- Invokes refactored scraper functions (ratp_http, vmtr, navitia fallback) with timeouts.
- Persists results into database tables:
  - `live_snapshots`: latest JSON snapshot per `(network,line)` including metadata.
  - `live_departures`: optional table for per-station departures (for historical tracking).
  - `task_runs`: job history with status, latency, error message.
  - `worker_heartbeats`: worker_id, last_seen_at, cpu/mem stats, assigned partitions.
- Emits heartbeat & metrics to Kafka `worker.metrics` (consumed by backend).
- Responds to control commands (`PAUSE`, `RESUME`, `REBAlANCE`) via `control.commands`.

Scaling:
- Each replica gets unique `WORKER_ID`.
- Kafka handles partition assignment for fair distribution.

### Backend Changes
- Add SQLAlchemy models + Alembic migrations for new tables.
- Provide REST endpoints:
  - `GET /api/system/workers` → list workers, status, last heartbeat.
  - `GET /api/system/queue` → backlog stats (via Kafka Admin / metrics topic).
  - `POST /api/system/workers/{worker_id}/command` → send control commands.
  - `GET /api/snapshots/{network}/{line}` now reads from `live_snapshots` (no on-demand scraping).
  - `GET /api/traffic/status` reads last aggregated record, fallback to scheduler-run aggregator.
- Integrate WebSocket / Server Sent Events optional for live updates.

### Frontend Dashboard (Next.js)
- Route: `/admin/orchestrator`.
- Sections:
  1. **Queue Overview**: tasks pending, throughput, oldest lag.
  2. **Worker Fleet**: table with status (Healthy, Behind, Down), last heartbeat, host info.
  3. **Recent Task Runs**: success/error timeline with filters.
  4. **Controls**: buttons (`Pause`, `Resume`, `Rebalance`, `Requeue failed tasks`), trigger API calls.
  5. **Scheduler Status**: last tick time, next run, manual “Run now”.
- Use charts (e.g., Recharts) optional; start with simple components.

### Docker Compose
- Services:
  - `backend`: FastAPI app.
  - `frontend`: Next.js dev/prod (choose dev for local).
  - `db`: Postgres (replace SQLite to support concurrency).
  - `kafka` + `zookeeper` (Bitnami images).
  - `scheduler`: python container running `python -m scheduler.run`.
  - `worker`: python container running `python -m worker.run` (scaleable replicas).
- `.env` updates with Kafka bootstrap servers, DB URL, scheduler config.
- Use shared network `ratp-net`.

### Data Flow / Persistence
1. Scheduler enqueues job.
2. Worker consumes, fetches live data.
3. Worker writes to DB (`live_snapshots`, `task_runs`).
4. Worker publishes heartbeat metrics.
5. Backend exposes snapshots via API.
6. Frontend polls/stream for display.

### Monitoring & Metrics
- Heartbeats every 10s with payload `{ worker_id, partitions, lag, fetch_rate, errors_last_minute }`.
- Scheduler writes metric records with queue depth.
- Backend caches metrics in memory for quick retrieval.
- Consider integrating Prometheus (future).

### Control Plane Commands
- `PAUSE_FETCH` (worker stops consuming).
- `RESUME_FETCH`.
- `RELOAD_CONFIG` (workers reload env/config).
- `DRAIN` (finish current tasks, then pause).
- Use `control.commands` topic with JSON message `{ command, target_worker_id|null, issued_by, timestamp }`.

### Migration Strategy
1. Introduce new tables with Alembic migration.
2. Deploy Kafka + scheduler/worker via Docker Compose.
3. Switch backend snapshot endpoint to DB-backed responses.
4. Decommission on-demand scraping path once stable.

### Security Considerations
- Kafka credentials (SASL) optional for local; use env secrets in prod.
- Admin endpoints gated by API key in backend (e.g., `SYSTEM_API_TOKEN` header).
- Scheduler/worker use service accounts with limited DB permissions.

### Next Steps
1. Implement Docker Compose stack.
2. Build scheduler + worker modules with shared abstractions.
3. Add DB migration & models.
4. Update backend APIs and types.
5. Build frontend dashboard.
6. Write integration tests (Pytest + Playwright) covering new flows.
7. Document operations (README updates).
