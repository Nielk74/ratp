# Handoff Instructions for Next Assistant

## Context
- Repository root: `/home/antoine/projects/ratp`
- Scraper stack:
  - Station-level Playwright scraper: `backend/services/scrapers/ratp_playwright.py`
  - Line-wide aggregation + inferred trains: `backend/services/scrapers/line_snapshot.py` exposed via `GET /api/snapshots/{network}/{line}`
  - Export convenience in `backend/services/scrapers/__init__.py`
- Docs & SOP: `backend/SCRAPER_EXPERIMENT.md` (includes snapshot API section)
- Frontend side:
  - Live map tab (line sidebar) renders snapshot data via `frontend/src/components/LineLiveMap.tsx`
  - API client auto-resolves backend host (`frontend/src/services/api.ts`)
- Tooling:
  - Playwright config lives in `frontend/playwright.config.ts`
  - Real E2E test: `frontend/tests/e2e/line-live-map.spec.ts`
  - New helper script `serve.sh` starts backend on `0.0.0.0:8000` and Next.js dev server on `0.0.0.0:8001`
- Dependencies are already installed; browsers via `npx playwright install` exist under `frontend`

## Goal
Boost confidence in the live map workflow by expanding realistic automated tests and iterating on train inference accuracy while waiting for official GTFS feeds.

## Suggested Next Tasks
1. **Grow Playwright coverage:** Add more scenarios (multi-line selection, error states, verified train markers). Run with `cd frontend && npm run test:e2e`. The tests hit real endpoints, so ensure the backend is running (use `./serve.sh` or equivalent).
2. **Refine train inference:** Improve `_infer_trains` in `line_snapshot.py` (handle HH:MM waits, multiple departures, confidence levels). Back changes with unit tests in `backend/tests`.
3. **Snapshot caching/persistence:** Consider Redis or a scheduled job so multiple users/tests don’t re-trigger the full Playwright scrape each time. Document any Cloudflare limits encountered.
4. **Map UX polish:** Replace the schematic with a Leaflet/Mapbox view using station coordinates, animate train markers using `absolute_progress`.

## Reminders
- Scraper fallback to `/horaires` is slower but necessary; check `metadata.form_flow` & `cloudflare_blocked` to detect Cloudflare hurdles.
- Never fabricate data—store only what the DOM/API returned. Manual captures belong under `backend/tmp/` (`ratp_sample.json` already kept).
- Playwright browsers are installed under `frontend`; rerun `npx playwright install` if needed.
- Use `./serve.sh` for local dev (Ctrl+C cleans up both processes).
