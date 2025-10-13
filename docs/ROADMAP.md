# Roadmap

This roadmap summarises completed work, current priorities, and upcoming milestones for the RATP Live Tracker project. It is reviewed after each major iteration.

## Current Status (October 2025)

- Backend: FastAPI service with Kafka-backed scheduler and worker pool, persisting snapshots, task history, and worker telemetry in Postgres.
- Frontend: Next.js dashboard with orchestrator admin panel, line snapshots, webhooks, and geolocation features.
- Testing: Backend pytest suite (61 tests) and Playwright end-to-end pipeline via `scripts/run_e2e.sh`.
- Deployment: Docker Compose v2 stack (`./serve.sh up`) with Postgres, Kafka, scheduler, worker, backend, and frontend services.

## Completed Milestones

| Area | Highlights |
| --- | --- |
| Backend | Core REST API (`/api/lines`, `/api/snapshots`, `/api/traffic`, `/api/webhooks`, `/api/system/*`), ratp.fr scraper, VMTR integration, Kafka scheduler + worker, database migrations, orchestration telemetry. |
| Frontend | Dashboard, line detail view, geolocation widget, webhook management, orchestrator admin panel (queue metrics, worker fleet, scaling controls, database snapshot). |
| Tooling | `serve.sh` orchestration script, Playwright e2e workflow, system metrics endpoints, Docker Compose v2 integration. |

## In Progress

| Stream | Goals |
| --- | --- |
| Orchestrator resilience | Improve snapshot caching (Redis or Postgres materialized views), capture worker heartbeat anomalies, surface alerting hooks. |
| Scraper pipeline | Refine train inference logic (`_infer_trains`), enhance error reporting for HTTP/VMTR fallbacks, expand retry logic around Cloudflare-protected endpoints. |
| Automated testing | Broaden Playwright coverage (multi-line selection, error states), add regression tests for scaling and DB snapshot endpoints. |

## Upcoming Milestones

1. **Live Map Enhancements**
   - Replace schematic map with Leaflet/Mapbox geometry.
   - Animate train markers, surface fallback indicators when VMTR data is missing.
2. **Historical Analytics**
   - Persist snapshot history, expose trend APIs, design reporting dashboards.
3. **Real-time Feeds**
   - Integrate SIRI / GTFS-RT (pending API access), add WebSocket/SSE layer for live updates, implement rate limiting and failover.
4. **Deployment Hardening**
   - Production-ready Compose/Helm manifests, secrets management, observability (Prometheus/Grafana), multi-environment configuration.
5. **Client Integrations**
   - Expand webhook targets, expose data exports, document public API usage scenarios.

## Backlog / Ideas

- Introduce Redis or another in-memory store for cross-worker caching.
- Add analytics for worker throughput, task duration percentiles, and failure alerts.
- Provide CLI tooling for manual task replays and snapshot verification.
- Explore mobile-friendly dashboards or widgets.

For day-to-day operational details see `docs/OPERATIONS.md`. Architectural deep dives (scheduler/worker internals) live in `docs/LIVE_DATA_ORCHESTRATION.md`.
