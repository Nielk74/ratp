## Live Estimation Probe

- **Goal:** capture real-time departure estimates for a single RATP station/line/direction outside the main backend.
- **Context:** reuse the backend cookie bootstrap + VMTR websocket knowledge while iterating safely in `experiments/live_estimation_probe/`.
- **Initial Observations (T+0):**
  - `backend/services/scrapers/ratp_http.py` already automates the `/horaires` AJAX endpoints after solving Cloudflare with Playwright.
  - `backend/services/scrapers/ratp_vmtr_socket.py` connects to `wss://api.vmtr.ratp.fr/socket.io/` without prior auth as long as we know the `IDFM` line id.
  - Target flow: bootstrap cookies → call `getLineId` + `getStopPoints` → fetch `blocs-horaires-next-passages` → optionally enrich with VMTR positions.

- **Update (T+1):** Added `fetch_departures.py`, a self-contained CLI that bootstraps a cookies-authenticated session, calls `getLineId`/`getStopPoints`, scrapes `blocs-horaires-next-passages`, and produces either human-readable output or JSON. No direct dependency on the backend package anymore; initial draft relied on Playwright + `requests` + `beautifulsoup4`.
  - Evolved after live tests: Cloudflare challenge can be bypassed with `cloudscraper` alone, so the CLI now ships with that dependency (no browser bootstrap needed).
  - CLI options: `--json` for raw output, `--with-vmtr` to request websocket vehicles via `vmtr_client.py`.

- **Update (T+2, 2025-10-12):** Created a dedicated virtualenv (`experiments/live_estimation_probe/.venv`) and installed `cloudscraper`, `requests`, `beautifulsoup4`, `websocket-client`, `playwright` (kept for future probes).
  - Successful run:  
    ```
    .venv/bin/python -m experiments.live_estimation_probe.fetch_departures \
      --network metro --line 1 --station Bastille --direction A --with-vmtr --json
    ```
    Returned departures for Metro 1 Bastille → Direction A with a six-entry board (`A quai`, `20:15`, … `20:26`) and metadata (`line_id` = `LIG:IDFM:C01371`, `stop_place_id` = `ART:IDFM:42288`).
  - VMTR fix: the socket requires `Origin: https://vmtr.ratp.fr` **and** a `/socket.io/` path before the query string—missing either yields a `502`. `vmtr_client.py` now enforces both and the CLI reports live vehicles (empty array when no trains are broadcast).

- **Update (T+2.1):** Added `run_default_probe.sh` to launch the probe with Bastille / Line 1 / Direction A defaults. Pass any arguments to override; otherwise it executes the baseline JSON run via the local `.venv`.

- **Update (T+2.2):** Checked temporal drift to rule out cached/mocked data. Three consecutive runs one minute apart returned `20:42`, `20:41`, then `A quai` for the first departure—matching the wall clock (20:37, 20:38, 20:39 CEST). Confirms we are reading the live `blocs-horaires` feed rather than static schedules.

- **Update (T+2.3):** Cross-validated other corridors with the same tooling (all commands executed against the `.venv` interpreter):
  - `metro 6 / Nation / dir A`: departures at `20:47`, `20:50`, `20:52`, `20:55`, `20:59`, `21:03` → non-uniform gaps, clearly live.
  - `metro 13 / Montparnasse Bienvenüe / dir B`: mix of `A quai`, `20:52`, `Retardé`, `21:02`, `21:07`, `21:11` → real-time status strings surface.
  - `rer A / Châtelet les Halles / dir A`: schedule block empty at that instant but VMTR returned 18 vehicle payloads (`vehicle_id`, `status`, `progress`, `recorded_at`) proving the websocket leg is healthy.
  - Re-running the Bastille default probe still yields consistent live shifts; when VMTR has no trains for a metro line the client now returns an empty list instead of failing.

Next step: decide whether to add automatic retries/backoff for the VMTR leg or persist output samples for regression.
