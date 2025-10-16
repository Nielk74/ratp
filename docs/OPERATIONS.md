# Operations Guide

This document describes how to run, scale, and troubleshoot the RATP Live Tracker stack in local or staging environments.

## 1. Prerequisites

- Docker 24 or newer.
- Docker Compose v2 plugin (`docker compose`). Install via the official Docker repository or your platform’s package manager.
- Git.

Verify the plugin by running:

```bash
docker compose version
```

The legacy `docker-compose` 1.x binary is not supported and will fail to recreate services with the current configuration.

## 2. Running the Stack

### Using the helper script

```bash
./serve.sh up                # build images and start all services
./serve.sh logs backend      # follow logs for a specific service
./serve.sh down              # stop and remove containers
```

Options:

- `./serve.sh up --workers N` – start with a custom worker pool (default `DEFAULT_WORKER_COUNT=16`).
- `./serve.sh scale --workers N` – adjust the worker pool without rebuilding.

### Manual docker compose usage

```bash
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml logs -f backend
docker compose -f docker-compose.yml down
```

Expose URLs:

- Dashboard: http://localhost:3000
- Orchestrator admin: http://localhost:3000/admin/orchestrator
- FastAPI docs: http://localhost:8000/docs

## 3. Manual Development Tasks

### Backend only

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH="$(pwd)/.." uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend only

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000
```

### Kafka, scheduler, and workers

```bash
# Optional: limit to a subset while developing
export SCHEDULER_LINES="metro:1,rer:A"

docker compose up -d kafka db
docker compose up -d scheduler worker
```

The orchestrator requires Kafka and Postgres even in manual mode. Remove `SCHEDULER_LINES` (or leave it empty) to process the full catalogue.

## 4. Scaling and Monitoring

### API endpoints

- `POST /api/system/workers/scale` – payload `{ "count": 4 }` or `{ "delta": 2 }`.
- `GET /api/system/db/summary` – returns task and worker counts to confirm scaling.
- `GET /api/system/workers` – live worker registry (status, heartbeat, host).
- `GET /api/system/queue` – queued/pending counts and last scheduled timestamp.

All system endpoints require the `X-API-Key` header (`SYSTEM_API_TOKEN` / `NEXT_PUBLIC_SYSTEM_API_KEY`).

### Orchestrator dashboard

The admin panel at `/admin/orchestrator` shows:

- Queue metrics (pending, total tasks, last run).
- Database snapshot (worker/task counts from Postgres).
- Worker fleet table (status, last heartbeat, metrics).
- Add/remove worker controls (wired to the scaling endpoint).
- Recent task run history and scheduler trigger.
- Log observatory ( `/admin/logs`) for searching centralized logs by service, level, and text.

### Centralized logging

All FastAPI, scheduler, and worker services now forward structured logs to the `system_logs` table. Tune behaviour via the following environment variables (defaults shown):

- `CENTRALIZED_LOGGING_ENABLED=true` – disable if you prefer stdout-only logs
- `CENTRALIZED_LOG_LEVEL=INFO` – minimum severity persisted
- `CENTRALIZED_LOG_QUEUE_SIZE=1000` – buffer size before dropping messages

Access logs through the new API: `GET /api/system/logs?limit=100&service=worker&level=ERROR` (requires the system API key). You can filter by service, level, free-text search, or a `since` timestamp.

The database dashboard also surfaces recent departure highlights when payload data is included, making it easier to eyeball live service boards without leaving the admin UI.

### CLI scaling

The backend executes:

```bash
docker compose -p ratp \
  -f /workspace/docker-compose.yml \
  up -d --no-build --no-recreate \
  --scale worker={count} worker
```

Ensure `/var/run/docker.sock` is mounted into the backend container (handled in `docker-compose.yml`).

## 5. Testing

```bash
# Backend tests
cd backend
pytest
pytest --cov=backend --cov-report=html

# Frontend static checks
cd frontend
npm run type-check
npm run lint
```

Full-stack verification:

```bash
./scripts/run_e2e.sh
```

The script spins up the stack, runs Playwright specs, and tears everything down (leaving logs on failure).

## 6. Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `docker compose` command not found | Install the plugin via Docker's official repository (see prerequisites). |
| Scaling endpoint returns 500 with `manifest unknown` | Older `WORKER_SCALE_COMMAND` references the deprecated `docker/compose` image; use the built-in plugin (`docker compose …`). |
| Scheduler/worker metrics look stale | Check Kafka logs, then restart scheduler/workers (`./serve.sh restart scheduler worker`). |
| Cloudflare blocks traffic scraper | Refresh cookies manually by running `backend/services/scrapers/ratp_http.py` with fresh session details, or toggle the Playwright seeding step. |
| Playwright tests fail due to missing browsers | Run `npx playwright install` inside `frontend/`. |
| **Workers connected but not consuming tasks** | **KNOWN ISSUE**: Workers join Kafka consumer group but don't poll messages. All tasks remain "queued". Check: (1) Kafka topic exists: `docker exec ratp-kafka-1 kafka-topics.sh --list --bootstrap-server localhost:9092`, (2) Worker logs show "Joined group" but no task processing, (3) Database: `SELECT status, COUNT(*) FROM task_runs GROUP BY status` shows all "queued". **Workaround needed** - investigate aiokafka consumer polling loop in `backend/workers/worker.py:77-81`. |
| Metro/RER show "No station data available" | Ensure Playwright is installed in worker containers (`playwright install chromium` in Dockerfile). HTTP scraper needs Playwright to bypass Cloudflare and fetch stop lists from ratp.fr. Check logs for "Playwright" or "Executable doesn't exist" errors. |
| VMTR socket disabled errors | Set `VMTR_SOCKET_ENABLED=True` in environment or backend/config.py (default changed to True in latest). Without VMTR, only lines with station fallback data or successful HTTP scraper runs will work. |

### Known Issues (2025-10-16)

**CRITICAL: Kafka Consumer Not Polling**
- **Status**: Under investigation
- **Impact**: All tasks remain in "queued" status indefinitely
- **Symptoms**:
  - Workers successfully connect to Kafka and join consumer group "live-data-workers"
  - No tasks are ever processed (started_at remains NULL)
  - Scheduler enqueues tasks normally every 120 seconds
  - Worker logs show "Joined group 'live-data-workers'" but no subsequent task activity
- **Affected**: All worker containers since 2025-10-16 21:49:00 UTC
- **Investigation needed**: aiokafka consumer polling in `backend/workers/worker.py`
  - Line 77-81: `async for msg in self._consumer:` loop never yields messages
  - Consumer is started and subscribed to topic correctly
  - Possible Kafka rebalancing issue or topic partition assignment problem

For additional context on the orchestrator internals see `docs/LIVE_DATA_ORCHESTRATION.md`. For roadmap and upcoming work see `docs/ROADMAP.md`.
