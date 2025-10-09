# Handoff Instructions for Next Assistant

## Context
- Repository root: `/home/antoine/projects/ratp`
- Scraper stack:
  - Primary Navitia/PRIM client: `backend/services/scrapers/navitia_scraper.py`
  - HTTP fallback for Cloudflare-protected pages: `backend/services/scrapers/ratp_http.py`
  - Line snapshot aggregator: `backend/services/scrapers/line_snapshot.py` (`GET /api/snapshots/{network}/{line}`) orchestrates Navitia first, HTTP fallback second, and Playwright only for cookie refresh/manual capture
- Docs & SOP: `backend/SCRAPER_EXPERIMENT.md` (historical notes) & `plan.md` (live map roadmap)
- Frontend:
  - Live map tab renders snapshot payload via `frontend/src/components/LineLiveMap.tsx`
  - API client auto-resolves backend host (`frontend/src/services/api.ts`)
- Tooling:
  - Playwright config: `frontend/playwright.config.ts`
  - Main e2e spec: `frontend/tests/e2e/line-workflow.spec.ts`
  - Orchestration scripts: `scripts/run_e2e.sh` (stack + Playwright) and `serve.sh` (dev servers w/ port cleanup)
- Dependencies & Playwright browsers already installed (`frontend/`)

## Goal
Boost confidence in the live map workflow by keeping Navitia↔HTTP fallback robust, expanding automated coverage, and refining train inference while waiting for official GTFS feeds.

## Suggested Next Tasks
1. **Grow Playwright coverage:** Add scenarios around Navitia outages/fallbacks, multi-line selectors, and map error states. Prefer `scripts/run_e2e.sh` for deterministic runs.
2. **Refine `_infer_trains`:** Handle HH:MM waits, multiple departures per station, and richer confidence scoring. Cover the changes with new unit tests in `backend/tests/`.
3. **Snapshot caching/persistence:** Evaluate Redis/job queue storage so each map request doesn’t re-scrape the entire line. Monitor Navitia rate limits during stress runs.
4. **Map UX polish:** Swap the schematic for an actual map (Leaflet/Mapbox), animate markers via `absolute_progress`, and surface fallback indicators when HTTP scrapes kicked in.

## Reminders
- Inspect `metadata.source` and `metadata.navitia_error` to tell when the HTTP fallback was used; never fabricate departures.
- Manual/Playwright captures belong under `backend/tmp/` (e.g. `ratp_sample.json`).
- `scripts/run_e2e.sh` automates full-stack tests; `./serve.sh` handles local dev (kills stale `uvicorn`/`next`).
- Re-run `npx playwright install` from `frontend/` if browsers ever go missing.
