# Selenium Scraper Experiment

This is a **temporary workaround** for cases where we need live train arrival
information but the official SIRI / GTFS-RT feeds are still locked behind the
Île-de-France Mobilités approval workflow. It uses Playwright with headless
Chromium to open the public ratp.fr schedules page and extract the next
departures directly from the rendered DOM (or, when available, from the page’s
JavaScript state).

> ⚠️ This approach will remain a **last resort**. It may break without notice and
> is subject to the ratp.fr terms of use. Move to the official feeds as soon as
> IDFM grants access.

## Installation

Install the new dependencies and Playwright browser binaries (Chromium is required):

```bash
cd backend
pip install -r requirements.txt
# Install the actual browser once after setup
python -m playwright install chromium
```

## Running the probe script

The module `backend/services/scrapers/ratp_playwright.py` can be executed
directly:

```bash
python -m services.scrapers.ratp_playwright \
  --network metro \
  --line 1 \
  --station Bastille \
  --direction A \
  --no-headless \
  --dump-state
```

Key CLI options:

- `--no-headless`: Forces a visible Chromium window, which often helps pass the
  Cloudflare challenge.
- `--challenge-delay`: Extra seconds to wait after the initial page load before
  parsing, default `8.0`.
- `--dump-state`: Pretty prints the raw JavaScript state detected on the page so
  you can inspect new structures.
- When Cloudflare serves the "Un instant…" interstitial, the scraper now falls
  back to the `/horaires` landing page, selects the requested network/line via
  the public form, and scrapes the timetable tables. This is slower but has
  proven to be the most reliable automated path.

## Behaviour

1. Launches a Playwright-managed Chromium instance with a realistic user agent.
2. Navigates to the pre-filled schedule page. If Cloudflare blocks the direct
   navigation, it automatically drives the `/horaires` search form and requests
   the timetable there instead.
3. Waits for the document to reach the `complete` ready state and sleeps for a
   few seconds to let Cloudflare finish.
4. Parses departures from either the legacy list layout or the newer timetable
   tables; falls back to scanning the JS state (`window.__NEXT_DATA__`,
   `window.drupalSettings`, etc.).
5. Returns a structured `ScraperResult` including the raw state for debugging.

The scraper is defensive: it deduplicates results, captures unknown fields in
`ScrapedDeparture.extra`, and survives minor layout changes.

## Limitations & Next Steps

- Requires Chrome/Chromium and compatible drivers on the host.
- Still vulnerable to Cloudflare or cookie consent flows; manual retry might be
  needed. When the `"cloudflare_blocked"` flag appears in the metadata, retry
  with a fresh IP or after a cool-down period.
- HTML structure may change, so keep inspections (`--dump-state`) handy and
  adjust selectors/candidate keys when needed.
- Does not yet integrate with the API layer—we should wrap it in a background
  task or caching service if it becomes part of the product.

Once IDFM enables the official feeds:

1. Replace this scraper with the `VehiclePositionService` backed by
   SIRI/GTFS-RT.
2. Keep the scraper module quarantined or remove it entirely to avoid drift.

## Sample capture

- A real timetable capture for Metro 1, Bastille, direction A (towards La
  Défense) is stored at `backend/tmp/ratp_sample.json`. It was produced from the
  DOM rendered on 2025-10-08 and mirrors the values displayed on
  https://www.ratp.fr/horaires at that time.
- If Cloudflare blocks automated runs, open `/horaires` manually, solve the
  challenge once in a real browser, and re-run the scraper—the clearance cookie
  is usually accepted by Playwright afterwards.
- VMTR websocket note: the public endpoint expects requests against
  `wss://api.vmtr.ratp.fr/socket.io/` with `Origin: https://vmtr.ratp.fr`. Missing the
  `/socket.io/` path or using the main ratp.fr origin yields 502 errors, so the
  backend client now enforces both.

## Line snapshot API

- The endpoint `GET /api/snapshots/{network}/{line}` now pulls station metadata from IDFM open data and overlays VMTR websocket vehicle positions when available—no Navitia or HTML scraping is performed in the hot path.
- Results are cached in-memory for 60 seconds and exposed to the frontend map view. Each station entry captures the IDFM `stop_id` so live vehicles can be mapped deterministically.
- You can force a refresh with `?refresh=true`.
