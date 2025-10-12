# Handoff Instructions for Next Assistant

## Context
- Repository root: `/home/antoine/projects/ratp`
- Scraper stack:
  - Traffic comes from the ratp.fr HTTP scraper: `backend/services/scrapers/ratp_traffic.py` (shares cookies with `ratp_http`)
  - Optional Navitia/PRIM client for departures: `backend/services/scrapers/navitia_scraper.py`
  - HTTP fallback for Cloudflare-protected pages: `backend/services/scrapers/ratp_http.py`
  - Line snapshot aggregator: `backend/services/scrapers/line_snapshot.py` (`GET /api/snapshots/{network}/{line}`) now uses IDFM open data plus the VMTR websocket; Playwright/HTTP scrapers are kept for manual probes only
- Docs & SOP: `backend/SCRAPER_EXPERIMENT.md` (historical notes) & `plan.md` (live map roadmap)
- Frontend:
  - Live map tab renders snapshot payload via `frontend/src/components/LineLiveMap.tsx`
  - API client auto-resolves backend host (`frontend/src/services/api.ts`)
- Tooling:
  - Playwright config: `frontend/playwright.config.ts`
  - Main e2e spec: `frontend/tests/e2e/line-workflow.spec.ts`
- Orchestration scripts: `scripts/run_e2e.sh` (stack + Playwright) and `serve.sh` (wrapper around docker-compose for backend/frontend/Kafka/workers)
- Dependencies & Playwright browsers already installed (`frontend/`)

## Goal
Boost confidence in the live map workflow by keeping the VMTR websocket/IDFM pipeline robust, expanding automated coverage, and refining train inference while waiting for official GTFS feeds.

## Suggested Next Tasks
1. **Grow Playwright coverage:** Add scenarios around VMTR outages, multi-line selectors, and map error states. Prefer `scripts/run_e2e.sh` for deterministic runs.
2. **Refine `_infer_trains`:** Handle HH:MM waits, multiple departures per station, and richer confidence scoring. Cover the changes with new unit tests in `backend/tests/`.
3. **Snapshot caching/persistence:** Evaluate Redis/job queue storage so each map request doesn’t re-run the VMTR session. Monitor websocket stability during stress runs.
4. **Map UX polish:** Swap the schematic for an actual map (Leaflet/Mapbox), animate markers via `absolute_progress`, and surface fallback indicators when HTTP scrapes kicked in.

## Reminders
- Inspect `metadata.source` and `metadata.navitia_error` to tell when the HTTP fallback was used; never fabricate departures.
- Manual/Playwright captures belong under `backend/tmp/` (e.g. `ratp_sample.json`).
- `scripts/run_e2e.sh` automates full-stack tests; `./serve.sh up` boots the full Docker stack (`./serve.sh down` stops it, `./serve.sh logs` tails containers).
- Re-run `npx playwright install` from `frontend/` if browsers ever go missing.
