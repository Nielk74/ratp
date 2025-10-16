# RATP Live Tracker

RATP Live Tracker provides real-time traffic, line snapshots, and orchestration tools for the Paris public transport network. The stack combines a FastAPI backend, a Kafka-backed scheduling system, and a Next.js dashboard to keep line data fresh and accessible.

## Table of Contents
1. [Key Features](#key-features)
2. [Architecture Overview](#architecture-overview)
3. [Quick Start](#quick-start)
4. [Development Workflow](#development-workflow)
5. [Orchestrator Dashboard](#orchestrator-dashboard)
6. [API Overview](#api-overview)
7. [Testing](#testing)
8. [Project Structure](#project-structure)

## Key Features

### Backend
- Live traffic scraper for ratp.fr with caching safeguards.
- Line snapshot service combining IDFM open data with optional VMTR websocket feeds.
- Kafka-backed scheduler/worker fleet with task retry, stale worker pruning, and snapshot persistence.
- Discord webhook management with confirmation workflow.
- Rich system endpoints (`/api/system/*`) exposing queue metrics, worker controls, and database summaries for observability.

### Frontend
- Next.js 14 dashboard with network filters, line detail views, and real-time refresh loops.
- Orchestrator admin panel showing queue metrics, worker status, database snapshot, and scaling controls.
- Discord webhook UI for creating, listing, and deleting alerts.
- Geolocation widget to surface nearby stations.

## Architecture Overview

```
RATP Live Tracker
├── backend/          FastAPI + SQLAlchemy + PostgreSQL
│   ├── api/          REST endpoints (traffic, lines, webhooks, system)
│   ├── models/       Database models and migrations
│   ├── services/     Scrapers, clients, utilities
│   └── workers/      Scheduler and Kafka consumer
├── frontend/         Next.js + React + Tailwind CSS
├── docs/             Documentation
└── scripts/          Helper scripts (testing, orchestration, e2e)
```

Data sources include ratp.fr traffic pages, VMTR websocket feeds, and IDFM open datasets. The Kafka topic graph connects the scheduler (producer), workers (consumers), and the backend (metrics/monitoring).

## Quick Start

### Prerequisites
- Docker 24+
- Docker Compose v2 plugin (`docker compose`)
- Git

> **Install Docker Compose v2 on Ubuntu/Debian**
> ```bash
> sudo install -m 0755 -d /etc/apt/keyrings
> curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
> echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list
> sudo apt-get update && sudo apt-get install docker-compose-plugin
> ```

### One-command stack

```bash
git clone https://github.com/Nielk74/ratp.git
cd ratp
./serve.sh up
```

When the stack is healthy:
- Dashboard: http://localhost:3000
- Orchestrator admin: http://localhost:3000/admin/orchestrator
- API docs: http://localhost:8000/docs

Useful helpers:

```bash
./serve.sh logs backend worker scheduler   # follow logs for core services
./serve.sh down                            # tear everything down
```

## Development Workflow

### Manual backend/frontend setup (optional)

Backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH="$(pwd)/.." uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Frontend:
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Kafka/worker development mode:

```bash
# Restrict to a subset of lines if needed (defaults to whole catalogue)
export SCHEDULER_LINES="metro:1,rer:A"
docker compose up kafka db scheduler worker
```

### Dev helpers
- `./serve.sh up --workers N` – start the stack with a custom worker pool (default `DEFAULT_WORKER_COUNT=16`).
- `./serve.sh scale --workers N` – adjust the worker pool without rebuilding.
- `./serve.sh logs …`, `./serve.sh restart …`, `./serve.sh down` – standard orchestration shortcuts.
- `./scripts/run_tests.sh` – run backend unit tests in a reproducible venv.
- `./scripts/run_e2e.sh` – execute the full stack with Playwright end-to-end tests.

## Orchestrator Dashboard

The admin panel (http://localhost:3000/admin/orchestrator) consolidates operations data:

- **Queue Overview**: pending task count, total scheduled tasks, latest scheduler run.
- **Database Snapshot**: aggregated `task_runs` and `worker_status` counts sourced from `/api/system/db/summary`.
- **Worker Fleet**: live worker list with heartbeat timestamps and metrics.
- **Scaling Controls**: add/remove workers via the new `/api/system/workers/scale` endpoint (supports absolute `count` or relative `delta`). Under the hood the backend executes `docker compose -p ratp -f /workspace/docker-compose.yml up -d --no-build --no-recreate --scale worker={count} worker`.
- **Recent Task Runs**: most recent history of orchestrator jobs with timing and error details.
- **Control Plane**: pause/resume/drain worker commands and manual scheduler trigger.
- **Log Observatory**: `/admin/logs` surfaces centralized logs with search, severity filters, and time windows.

## API Overview

### Lines and snapshots
- `GET /api/lines` – list all networks, optionally filtered by `transport_type`.
- `GET /api/lines/{type}/{code}` – full line definition with ordered stations.
- `GET /api/snapshots/{network}/{line}` – latest persisted snapshot (via worker fleet).

### Traffic
- `GET /api/traffic/status` – normalized traffic feed with severity metadata.
- `GET /api/traffic` – legacy raw traffic response (kept for compatibility).

### Webhooks
- `POST /api/webhooks` – create a Discord webhook subscription (sends confirmation message).
- `GET /api/webhooks` – enumerate subscriptions.
- `DELETE /api/webhooks/{id}` – remove a subscription.

### Orchestrator/system endpoints
- `GET /api/system/workers` – workers with status, host, heartbeat, metrics.
- `GET /api/system/queue` – queued/pending counts and last scheduled timestamp.
- `GET /api/system/tasks/recent` – most recent task run history.
- `POST /api/system/workers/{id}/command` – send a control command (pause/resume/drain/reload).
- `POST /api/system/workers/scale` – adjust worker pool (payload `{ "count": N }` or `{ "delta": ±N }`).
- `POST /api/system/scheduler/run` – trigger scheduler immediately.
- `GET /api/system/db/summary` – aggregate counts from `task_runs` and `worker_status`.
- `GET /api/system/logs` – query centralized logs by service, level, time, or text search.

## Testing

```bash
# Backend unit tests
cd backend
pytest

# Coverage report
pytest --cov=backend --cov-report=html

# Frontend static checks
cd frontend
npm run type-check
npm run lint
```

For full-stack validation run:

```bash
./scripts/run_e2e.sh
```

The script spins up the stack, runs Playwright tests, streams results, and tears everything down, preserving logs on failure.

## Project Structure

```
backend/
├── api/                 # FastAPI routers (traffic, lines, system, webhooks)
├── config.py            # Settings loader (env-driven)
├── database.py          # Async session/engine helpers
├── services/            # Scrapers, clients, utilities
├── workers/             # Scheduler loop and Kafka worker
├── tests/               # Backend pytest suite
└── tmp/                 # Scratch space / captured payloads

frontend/
├── src/
│   ├── app/             # Next.js routes (dashboard, orchestrator admin)
│   ├── components/      # Shared UI components
│   ├── services/        # API hooks and clients
│   └── types/           # Shared TypeScript types
└── tests/               # Playwright specs

docs/                    # Detailed system design and operations notes
scripts/                 # Utility scripts (orchestration, testing, helpers)
```

---

Further reading:

- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) – operations guide, deployment tips, troubleshooting.
- [`docs/LIVE_DATA_ORCHESTRATION.md`](docs/LIVE_DATA_ORCHESTRATION.md) – scheduler and worker internals.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) – current status and upcoming milestones.
