# Handoff Instructions for Next Assistant

## Context
- Repository: `/home/antoine/projects/ratp`
- Playwright scraper lives in `backend/services/scrapers/ratp_playwright.py`; helper exports are wired via `backend/services/scrapers/__init__.py`.
- Docs and run notes: `backend/SCRAPER_EXPERIMENT.md` (updated with the new fallback flow).
- Dependencies come from `backend/.venv`; `python -m playwright install chromium` already ran and `beautifulsoup4` is now part of `backend/requirements.txt`.
- A real capture for Metro 1 → Bastille (both directions) is stored at `backend/tmp/ratp_sample.json` for reference. It was scraped via the timetable DOM, not the legacy API.
- Current limitation: repeated scripted hits triggered Cloudflare’s “Un instant…” interstitial. The scraper now flags `cloudflare_blocked=True` in the metadata when that happens.

## Goal
Stabilise the scraper workflow so it can reliably deliver fresh departures that downstream services can consume until official SIRI / GTFS-RT feeds are available.

## Suggested Next Tasks
1. **Regain access past Cloudflare:** wait for the cooldown or hop onto a fresh IP, then run
   ```bash
   backend/.venv/bin/python -m backend.services.scrapers.ratp_playwright \
     --network metro --line 1 --station Bastille --direction A \
     --no-headless --wait-timeout 60 --challenge-delay 15
   ```
   Confirm `cloudflare_blocked` is `False` and that departures come from the timetable DOM when the API is unavailable.
2. **Package the output:** design a thin wrapper (CLI or background job) that stores the JSON output somewhere the backend can reach (e.g., S3, Redis, or a temporary DB table). Re-use the structure shown in `backend/tmp/ratp_sample.json`.
3. **Plan integration:** sketch how the backend would surface these scraped departures (endpoint contract, cache TTL, error handling when Cloudflare blocks us). Update the experiment doc with any new caveats.

## Reminders
- The scraper can fall back to the `/horaires` search form; this is slower but survives Cloudflare’s managed challenge. `metadata.form_flow` indicates when that path was used.
- Always avoid fabricating data—only export what the DOM/API returns.
- If you need to reinstall browsers, run inside the virtualenv: `cd backend && . .venv/bin/activate` then `python -m playwright install chromium`.
